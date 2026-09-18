import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:path_provider/path_provider.dart';

import 'offline_data.dart';

typedef OfflineDirectoryProvider = Future<Directory> Function();
typedef MobileRecoveryWriteHook = Future<void> Function();

class OfflineStore {
  OfflineStore({
    OfflineDirectoryProvider? directoryProvider,
    DateTime Function()? clock,
    MobileRecoveryWriteHook? beforeMobileRecoveryWrite,
  })  : _directoryProvider =
            directoryProvider ?? getApplicationDocumentsDirectory,
        _clock = clock ?? DateTime.now,
        _beforeMobileRecoveryWrite = beforeMobileRecoveryWrite;

  static const _directoryName = 'offline-mode';
  static const _recoveryDirectoryName = 'recovery';
  static const _baselineFilename = 'baseline.json';
  static const _stateFilename = 'state.json';
  static const _journalFilename = 'journal.ndjson';
  static const _mobileRecoveryKeepCount = 30;

  final OfflineDirectoryProvider _directoryProvider;
  final DateTime Function() _clock;
  final MobileRecoveryWriteHook? _beforeMobileRecoveryWrite;
  final Random _random = Random.secure();

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
    }
  }

  Future<void> replaceBaseline(OfflineBaseline baseline) async {
    await _writeJsonAtomic(await _file(_baselineFilename), baseline.toJson());
  }

  Future<List<OfflineJournalOperation>> loadJournal() async {
    final file = await _file(_journalFilename);
    if (!await file.exists()) return const [];
    final text = await file.readAsString();
    final lines = text.split('\n');
    final operations = <OfflineJournalOperation>[];
    final ids = <String>{};
    var previousSequence = 0;
    for (var index = 0; index < lines.length; index += 1) {
      final line = lines[index].trim();
      if (line.isEmpty) continue;
      try {
        final decoded = jsonDecode(line);
        if (decoded is! Map<String, dynamic>) {
          throw const FormatException('journal row must be an object');
        }
        final operation = OfflineJournalOperation.fromJson(decoded);
        if (operation.sequence <= previousSequence ||
            !ids.add(operation.operationId)) {
          throw const FormatException('journal ordering is invalid');
        }
        previousSequence = operation.sequence;
        operations.add(operation);
      } on FormatException catch (error) {
        final isInterruptedFinalAppend =
            index == lines.length - 1 && !text.endsWith('\n');
        if (isInterruptedFinalAppend) break;
        throw OfflinePersistenceException('오프라인 journal을 읽을 수 없습니다: $error');
      }
    }
    return List.unmodifiable(operations);
  }

  Future<OfflineJournalOperation> appendOperation({
    required OfflineOperationType type,
    required Map<String, dynamic> payload,
  }) async {
    final file = await _file(_journalFilename);
    await _discardInterruptedTail(file);
    _rejectDerivedFinancialValues(payload);
    final operations = await loadJournal();
    final operation = OfflineJournalOperation(
      operationId: _operationId(),
      type: type,
      payload: Map<String, dynamic>.unmodifiable(payload),
      createdAt: _clock().toUtc(),
      sequence: operations.isEmpty ? 1 : operations.last.sequence + 1,
    );
    await file.writeAsString(
      '${jsonEncode(operation.toJson())}\n',
      mode: FileMode.append,
      flush: true,
    );
    return operation;
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

  Future<void> _discardInterruptedTail(File file) async {
    if (!await file.exists()) return;
    final bytes = await file.readAsBytes();
    if (bytes.isEmpty || bytes.last == 0x0a) return;

    final lastNewline = bytes.lastIndexOf(0x0a);
    final journal = await file.open(mode: FileMode.append);
    try {
      await journal.truncate(lastNewline + 1);
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
