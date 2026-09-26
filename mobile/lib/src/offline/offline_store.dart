import 'dart:convert';
import 'dart:async';
import 'dart:io';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:path_provider/path_provider.dart';

import 'offline_data.dart';

typedef OfflineDirectoryProvider = Future<Directory> Function();
typedef MobileRecoveryWriteHook = Future<void> Function();
typedef JournalAppendWriteHook = Future<void> Function();

class OfflineStore {
  OfflineStore({
    OfflineDirectoryProvider? directoryProvider,
    DateTime Function()? clock,
    MobileRecoveryWriteHook? beforeMobileRecoveryWrite,
    JournalAppendWriteHook? beforeJournalAppendWrite,
  })  : _directoryProvider =
            directoryProvider ?? getApplicationDocumentsDirectory,
        _clock = clock ?? DateTime.now,
        _beforeMobileRecoveryWrite = beforeMobileRecoveryWrite,
        _beforeJournalAppendWrite = beforeJournalAppendWrite;

  static const _directoryName = 'offline-mode';
  static const _recoveryDirectoryName = 'recovery';
  static const _baselineFilename = 'baseline.json';
  static const _stateFilename = 'state.json';
  static const _journalFilename = 'journal.ndjson';
  static const _manualPanelRetryFilename = 'manual-panel-retries.json';
  static const _mobileRecoveryKeepCount = 30;

  final OfflineDirectoryProvider _directoryProvider;
  final DateTime Function() _clock;
  final MobileRecoveryWriteHook? _beforeMobileRecoveryWrite;
  final JournalAppendWriteHook? _beforeJournalAppendWrite;
  final Random _random = Random.secure();
  Future<void>? _journalAppendTail;

  Future<OfflineWorkspaceMetadata> loadMetadata() async {
    final file = await _file(_stateFilename);
    if (!await file.exists()) {
      return const OfflineWorkspaceMetadata(mode: ConnectivityMode.online);
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('offline state must be an object');
      }
      return OfflineWorkspaceMetadata.fromJson(decoded);
    } on FormatException catch (error) {
      throw OfflinePersistenceException('오프라인 상태 파일을 읽을 수 없습니다: $error');
    } on FileSystemException catch (error) {
      throw OfflinePersistenceException('오프라인 상태 파일을 읽을 수 없습니다: $error');
    }
  }

  Future<void> saveMetadata(OfflineWorkspaceMetadata metadata) async {
    await _writeJsonAtomic(await _file(_stateFilename), metadata.toJson());
  }

  Future<OfflineBaseline?> loadBaseline() async {
    final file = await _file(_baselineFilename);
    if (!await file.exists()) return null;
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException('offline baseline must be an object');
      }
      return OfflineBaseline.fromJson(decoded);
    } on FormatException catch (error) {
      throw OfflinePersistenceException('오프라인 기준 데이터를 읽을 수 없습니다: $error');
    } on FileSystemException catch (error) {
      throw OfflinePersistenceException('오프라인 기준 데이터를 읽을 수 없습니다: $error');
    }
  }

  Future<void> replaceBaseline(OfflineBaseline baseline) async {
    await _writeJsonAtomic(await _file(_baselineFilename), baseline.toJson());
  }

  Future<String> reserveManualPanelRetryKey(Map<String, dynamic> input,
      {String? preferredKey}) async {
    final file = await _file(_manualPanelRetryFilename);
    final keys = await _loadManualPanelRetryKeys(file);
    final digest =
        sha256.convert(utf8.encode(_canonicalJson(input))).toString();
    final existing = keys[digest];
    if (existing != null) return existing;
    // Keep one unresolved logical create identity even if the form is edited.
    // A changed financial input then conflicts if the first request committed.
    final key = keys.isNotEmpty
        ? keys.values.first
        : preferredKey ?? 'manual-panel-${_operationId()}';
    keys[digest] = key;
    await _writeJsonAtomic(file, {'schema_version': 1, 'keys': keys});
    return key;
  }

  Future<bool> hasPendingManualPanelRetry() async {
    final keys =
        await _loadManualPanelRetryKeys(await _file(_manualPanelRetryFilename));
    return keys.isNotEmpty;
  }

  Future<void> completeManualPanelRetryKey(
      Map<String, dynamic> input, String key) async {
    final file = await _file(_manualPanelRetryFilename);
    final keys = await _loadManualPanelRetryKeys(file);
    final digest =
        sha256.convert(utf8.encode(_canonicalJson(input))).toString();
    if (keys[digest] != key) {
      throw const OfflinePersistenceException(
          '수동 정산 재시도 identity가 변경되어 확인이 필요합니다.');
    }
    keys.removeWhere((_, value) => value == key);
    if (keys.isEmpty) {
      await file.delete();
    } else {
      await _writeJsonAtomic(file, {'schema_version': 1, 'keys': keys});
    }
  }

  Future<Map<String, String>> _loadManualPanelRetryKeys(File file) async {
    if (!await file.exists()) return {};
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic> ||
          decoded['schema_version'] != 1 ||
          decoded['keys'] is! Map) {
        throw const FormatException('manual panel retry state is invalid');
      }
      return Map<String, String>.from(decoded['keys'] as Map);
    } on FormatException catch (error) {
      throw OfflinePersistenceException('수동 정산 재시도 기록을 읽을 수 없습니다: $error');
    } on TypeError catch (error) {
      throw OfflinePersistenceException('수동 정산 재시도 기록을 읽을 수 없습니다: $error');
    } on FileSystemException catch (error) {
      throw OfflinePersistenceException('수동 정산 재시도 기록을 읽을 수 없습니다: $error');
    }
  }

  Future<List<OfflineJournalOperation>> loadJournal() async {
    final pendingAppend = _journalAppendTail;
    if (pendingAppend != null) await pendingAppend;
    return _loadJournalFile(await _file(_journalFilename));
  }

  Future<OfflineJournalOperation> appendOperation({
    required OfflineOperationType type,
    required Map<String, dynamic> payload,
    OfflineBaseline? baseline,
  }) async {
    final previous = _journalAppendTail;
    final completed = Completer<void>();
    final current = completed.future;
    _journalAppendTail = current;
    if (previous != null) await previous;
    try {
      final file = await _file(_journalFilename);
      await _repairJournalTail(file);
      _rejectDerivedFinancialValues(payload);
      final operations = await _loadJournalFile(file);
      final registrationKey = payload['candidate_registration_key'];
      if (registrationKey is String && registrationKey.isNotEmpty) {
        final authoritativeBaseline = baseline ?? await loadBaseline();
        if (authoritativeBaseline != null &&
            _baselineHasRegistration(
                authoritativeBaseline, registrationKey, type, payload)) {
          throw const AlreadyRegisteredInBaselineException();
        }
        for (final existing in operations) {
          if (existing.payload['candidate_registration_key'] !=
              registrationKey) {
            continue;
          }
          if (existing.type == type &&
              _canonicalJson(existing.payload) == _canonicalJson(payload)) {
            return existing;
          }
          throw const OfflinePersistenceException(
            '이미 등록한 알림 후보를 다른 내용이나 등록 대상으로 다시 사용할 수 없습니다.',
          );
        }
      }
      final operation = OfflineJournalOperation(
        operationId: _operationId(),
        type: type,
        payload: Map<String, dynamic>.unmodifiable(payload),
        createdAt: _clock().toUtc(),
        sequence: operations.isEmpty ? 1 : operations.last.sequence + 1,
      );
      await _beforeJournalAppendWrite?.call();
      await file.writeAsString(
        '${jsonEncode(operation.toJson())}\n',
        mode: FileMode.append,
        flush: true,
      );
      return operation;
    } finally {
      completed.complete();
      if (identical(_journalAppendTail, current)) _journalAppendTail = null;
    }
  }

  bool _baselineHasRegistration(OfflineBaseline baseline, String key,
      OfflineOperationType type, Map<String, dynamic> payload) {
    final rows = baseline.authoritativeSnapshot?['data'];
    if (rows is! Map) {
      throw const OfflinePersistenceException(
          '기준 데이터의 알림 등록 identity를 확인할 수 없습니다.');
    }
    final registrations = rows['notification_candidate_registrations'];
    if (registrations is! List) {
      throw const OfflinePersistenceException(
          '기준 데이터의 알림 등록 identity를 확인할 수 없습니다.');
    }
    for (final registration in registrations) {
      if (registration is! Map || registration['registration_key'] != key) {
        continue;
      }
      if (type != OfflineOperationType.createCardExpense ||
          registration['target'] != 'ledger') {
        throw const OfflinePersistenceException(
          '이미 등록한 알림 후보의 등록 대상이 다릅니다.',
        );
      }
      final expected = _ledgerRegistrationFingerprint(payload);
      if (registration['request_fingerprint'] != expected &&
          !(registration['request_fingerprint'] ==
                  _legacyLedgerRegistrationFingerprint(payload) &&
              _matchesStoredBaselineRegistration(
                  rows, registration, payload))) {
        throw const OfflinePersistenceException(
          '이미 등록한 알림 후보의 금융 입력이 현재 요청과 다릅니다.',
        );
      }
      return true;
    }
    return false;
  }

  bool _matchesStoredBaselineRegistration(
      Map rows, Map registration, Map<String, dynamic> payload) {
    final entries = rows['ledger_entries'];
    if (entries is! List) return false;
    for (final entry in entries) {
      if (entry is! Map || entry['id'] != registration['target_id']) continue;
      for (final field in [
        'entry_date',
        'title',
        'usage_place',
        'usage_item',
        'amount_value',
        'spending_category',
      ]) {
        if (entry[field] != payload[field]) return false;
      }
      final requestedOverride = payload['discount_override_amount'];
      if (requestedOverride != null) {
        return entry['discount_override'] == 1 &&
            entry['aux_amount_value'] == requestedOverride;
      }
      if (payload['discount_enabled'] == false) {
        return entry['discount_override'] == 1 &&
            (entry['aux_amount_value'] ?? 0) == 0;
      }
      return entry['discount_override'] == 0;
    }
    return false;
  }

  String _ledgerRegistrationFingerprint(Map<String, dynamic> payload) {
    final override = payload['discount_override_amount'];
    final discount = override != null
        ? ['manual', override]
        : payload['discount_enabled'] == false
            ? ['manual', 0]
            : ['automatic'];
    // Mirrors the server's authoritative-input identity, not its discount engine.
    final values = [
      'ledger',
      payload['book_section'],
      payload['entry_kind'],
      payload['entry_date'],
      null,
      null,
      payload['title'],
      payload['usage_place'],
      payload['usage_item'],
      payload['amount_value'],
      null,
      null,
      null,
      0,
      null,
      null,
      payload['spending_category'],
      null,
      null,
      discount,
    ];
    return sha256.convert(utf8.encode(jsonEncode(values))).toString();
  }

  String _legacyLedgerRegistrationFingerprint(Map<String, dynamic> payload) {
    final values = <Object?>[
      'ledger',
      payload['entry_date'],
      payload['usage_place'],
      payload['usage_item'],
      payload['title'],
      payload['amount_value'],
      payload['spending_category'],
    ];
    if (payload['discount_override_amount'] != null) {
      values.add(payload['discount_override_amount']);
    } else if (payload['discount_enabled'] == false) {
      values.add(false);
    }
    return sha256.convert(utf8.encode(jsonEncode(values))).toString();
  }

  Future<OfflineReconciliationBundle?> loadReconciliationBundle() async {
    final baseline = await loadBaseline();
    if (baseline == null) return null;
    final metadata = await loadMetadata();
    return OfflineReconciliationBundle(
      baseline: baseline,
      operations: await loadJournal(),
      metadata: metadata,
    );
  }

  String recoveryLineageFingerprint(OfflineBaseline baseline) {
    return sha256
        .convert(utf8.encode(_canonicalJson({
          'schema_version': 1,
          'origin': 'mobile-baseline-lineage',
          'baseline': baseline.toJson(),
        })))
        .toString();
  }

  String newReconciliationId() {
    final randomPart = List<int>.generate(16, (_) => _random.nextInt(256))
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    return 'reconcile-${_clock().toUtc().microsecondsSinceEpoch}-$randomPart';
  }

  Future<MobileRecoveryArtifact> createMobileRecoveryArtifact({
    required OfflineBaseline baseline,
    required List<OfflineJournalOperation> operations,
    required OfflineWorkspaceMetadata metadata,
  }) async {
    final reconciliationId = metadata.reconciliationId;
    if (reconciliationId == null || reconciliationId.isEmpty) {
      throw const OfflinePersistenceException(
          'reconciliation identity is missing');
    }
    final directory = await _recoveryDirectory();
    final timestamp = _clock()
        .toUtc()
        .toIso8601String()
        .replaceAll('-', '')
        .replaceAll(':', '')
        .replaceAll('.', '');
    final safeId = reconciliationId.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final target = _uniqueMobileRecoveryTarget(File(
      '${directory.path}/pre_reconcile_mobile-$timestamp-$safeId.money-note-offline-recovery.json',
    ));
    final content = <String, dynamic>{
      'schema_version': 1,
      'origin': 'mobile',
      'created_at': _clock().toUtc().toIso8601String(),
      'reconciliation_id': reconciliationId,
      'baseline': baseline.toJson(),
      'ordered_journal':
          operations.map((operation) => operation.toJson()).toList(),
      'reconciliation_metadata': metadata.toJson(),
    };
    final digest =
        sha256.convert(utf8.encode(_canonicalJson(content))).toString();
    final artifact = <String, dynamic>{
      ...content,
      'manifest': {
        'algorithm': 'sha256',
        'content_sha256': digest,
      },
    };

    await _beforeMobileRecoveryWrite?.call();
    await _writeJsonAtomic(target, artifact);
    final verified = await verifyMobileRecoveryArtifact(target.path);
    await _pruneMobileRecoveryArtifacts();
    return MobileRecoveryArtifact(
      filename: target.uri.pathSegments.last,
      sha256: verified,
    );
  }

  Future<String> verifyMobileRecoveryArtifact(
    String pathOrFilename, {
    String? expectedReconciliationId,
    OfflineBaseline? expectedBaseline,
    List<OfflineJournalOperation>? expectedOperations,
  }) async {
    final file = pathOrFilename.contains(Platform.pathSeparator)
        ? File(pathOrFilename)
        : File('${(await _recoveryDirectory()).path}/$pathOrFilename');
    if (!await file.exists()) {
      throw const OfflinePersistenceException(
          'mobile recovery artifact is missing');
    }
    try {
      final decoded = jsonDecode(await file.readAsString());
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException(
            'mobile recovery artifact must be an object');
      }
      final manifest = decoded['manifest'];
      if (manifest is! Map<String, dynamic> ||
          manifest['algorithm'] != 'sha256' ||
          manifest['content_sha256'] is! String) {
        throw const FormatException('mobile recovery manifest is invalid');
      }
      final content = Map<String, dynamic>.from(decoded)..remove('manifest');
      final actual =
          sha256.convert(utf8.encode(_canonicalJson(content))).toString();
      if (actual != manifest['content_sha256']) {
        throw const FormatException('mobile recovery artifact digest mismatch');
      }
      if (content['schema_version'] != 1 || content['origin'] != 'mobile') {
        throw const FormatException(
            'mobile recovery artifact identity is invalid');
      }
      if (expectedReconciliationId != null &&
          content['reconciliation_id'] != expectedReconciliationId) {
        throw const FormatException(
            'mobile recovery reconciliation identity does not match');
      }
      if (expectedBaseline != null &&
          _canonicalJson(content['baseline']) !=
              _canonicalJson(expectedBaseline.toJson())) {
        throw const FormatException('mobile recovery baseline does not match');
      }
      if (expectedOperations != null &&
          _canonicalJson(content['ordered_journal']) !=
              _canonicalJson(expectedOperations
                  .map((operation) => operation.toJson())
                  .toList())) {
        throw const FormatException('mobile recovery journal does not match');
      }
      return actual;
    } on FormatException catch (error) {
      throw OfflinePersistenceException(
          'mobile recovery artifact verification failed: $error');
    }
  }

  Future<List<File>> listMobileRecoveryArtifacts() async {
    final directory = await _recoveryDirectory();
    final files = await directory
        .list()
        .where((entity) =>
            entity is File &&
            entity.path.endsWith('.money-note-offline-recovery.json'))
        .cast<File>()
        .toList();
    files.sort((left, right) => right.path.compareTo(left.path));
    return files;
  }

  Future<void> deleteJournal() async {
    final file = await _file(_journalFilename);
    if (await file.exists()) await file.delete();
  }

  Future<Directory> _recoveryDirectory() async {
    final base = await _directoryProvider();
    final directory =
        Directory('${base.path}/$_directoryName/$_recoveryDirectoryName');
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  File _uniqueMobileRecoveryTarget(File target) {
    if (!target.existsSync()) return target;
    const suffix = '.money-note-offline-recovery.json';
    final base = target.path.substring(0, target.path.length - suffix.length);
    for (var index = 2; index < 1000; index += 1) {
      final candidate = File('$base-$index$suffix');
      if (!candidate.existsSync()) return candidate;
    }
    throw const OfflinePersistenceException(
      'too many mobile recovery artifacts created at the same timestamp',
    );
  }

  Future<void> _pruneMobileRecoveryArtifacts() async {
    final files = await listMobileRecoveryArtifacts();
    for (final file in files.skip(_mobileRecoveryKeepCount)) {
      await file.delete();
    }
  }

  Future<List<OfflineJournalOperation>> _loadJournalFile(File file) async {
    if (!await file.exists()) return const [];
    try {
      final bytes = await file.readAsBytes();
      final operations = <OfflineJournalOperation>[];
      final ids = <String>{};
      var previousSequence = 0;
      var start = 0;
      for (var index = 0; index <= bytes.length; index += 1) {
        final atEnd = index == bytes.length;
        if (!atEnd && bytes[index] != 0x0a) continue;
        if (index == start) {
          start = index + 1;
          continue;
        }
        final isUnterminatedTail =
            atEnd && bytes.isNotEmpty && bytes.last != 0x0a;
        OfflineJournalOperation operation;
        try {
          operation = _decodeJournalRecord(bytes.sublist(start, index));
        } on FormatException catch (error) {
          if (isUnterminatedTail) break;
          throw OfflinePersistenceException('오프라인 journal을 읽을 수 없습니다: $error');
        }
        if (operation.sequence <= previousSequence ||
            !ids.add(operation.operationId)) {
          throw const OfflinePersistenceException(
              '오프라인 journal 순서 또는 operation id가 올바르지 않습니다.');
        }
        previousSequence = operation.sequence;
        operations.add(operation);
        start = index + 1;
      }
      return List.unmodifiable(operations);
    } on FileSystemException catch (error) {
      throw OfflinePersistenceException('오프라인 journal을 읽을 수 없습니다: $error');
    }
  }

  OfflineJournalOperation _decodeJournalRecord(List<int> bytes) {
    final line = utf8.decode(bytes, allowMalformed: false).trim();
    if (line.isEmpty) throw const FormatException('journal row is empty');
    final decoded = jsonDecode(line);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('journal row must be an object');
    }
    return OfflineJournalOperation.fromJson(decoded);
  }

  Future<void> _repairJournalTail(File file) async {
    if (!await file.exists()) return;
    final bytes = await file.readAsBytes();
    if (bytes.isEmpty || bytes.last == 0x0a) return;

    final lastNewline = bytes.lastIndexOf(0x0a);
    final tail = bytes.sublist(lastNewline + 1);
    var validRecord = false;
    try {
      _decodeJournalRecord(tail);
      validRecord = true;
    } on FormatException {
      // A crash may leave only the final NDJSON record incomplete.
    }
    final journal = await file.open(mode: FileMode.append);
    try {
      if (validRecord) {
        await journal.writeByte(0x0a);
      } else {
        await journal.truncate(lastNewline + 1);
      }
      await journal.flush();
    } finally {
      await journal.close();
    }
  }

  Future<File> _file(String filename) async {
    final base = await _directoryProvider();
    final directory = Directory('${base.path}/$_directoryName');
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return File('${directory.path}/$filename');
  }

  Future<void> _writeJsonAtomic(
      File target, Map<String, dynamic> payload) async {
    final temporary = File(
        '${target.path}.${_clock().microsecondsSinceEpoch}.${_random.nextInt(1 << 32)}.tmp');
    try {
      await temporary.writeAsString(jsonEncode(payload), flush: true);
      // Parse the fully flushed candidate before it can replace the valid file.
      jsonDecode(await temporary.readAsString());
      await temporary.rename(target.path);
    } finally {
      if (await temporary.exists()) {
        await temporary.delete();
      }
    }
  }

  String _operationId() {
    final randomPart = List<int>.generate(16, (_) => _random.nextInt(256))
        .map((value) => value.toRadixString(16).padLeft(2, '0'))
        .join();
    return '${_clock().toUtc().microsecondsSinceEpoch}-$randomPart';
  }

  void _rejectDerivedFinancialValues(Map<String, dynamic> payload) {
    const forbidden = {
      'remaining_liquidity',
      'card_total',
      'cash_flow_balance',
      'effective_discount_amount',
      'effective_amount_value',
      'automatic_discount_amount',
      'current_spending_total',
    };
    if (payload.keys.any(forbidden.contains)) {
      throw ArgumentError('derived financial values cannot be journaled');
    }
  }
}

class MobileRecoveryArtifact {
  const MobileRecoveryArtifact({
    required this.filename,
    required this.sha256,
  });

  final String filename;
  final String sha256;
}

String _canonicalJson(Object? value) => jsonEncode(_canonicalValue(value));

Object? _canonicalValue(Object? value) {
  if (value is Map) {
    final keys = value.keys.map((key) => key.toString()).toList()..sort();
    return <String, Object?>{
      for (final key in keys) key: _canonicalValue(value[key]),
    };
  }
  if (value is List) return value.map(_canonicalValue).toList();
  return value;
}

class OfflinePersistenceException implements Exception {
  const OfflinePersistenceException(this.message);

  final String message;

  @override
  String toString() => message;
}

class AlreadyRegisteredInBaselineException extends OfflinePersistenceException {
  const AlreadyRegisteredInBaselineException()
      : super('이미 서버 기준 데이터에 등록된 알림 후보입니다.');
}
