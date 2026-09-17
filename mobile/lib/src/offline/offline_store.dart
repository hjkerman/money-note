import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:path_provider/path_provider.dart';

import 'offline_data.dart';

typedef OfflineDirectoryProvider = Future<Directory> Function();

class OfflineStore {
  OfflineStore({
    OfflineDirectoryProvider? directoryProvider,
    DateTime Function()? clock,
  })  : _directoryProvider =
            directoryProvider ?? getApplicationDocumentsDirectory,
        _clock = clock ?? DateTime.now;

  static const _directoryName = 'offline-mode';
  static const _baselineFilename = 'baseline.json';
  static const _stateFilename = 'state.json';
  static const _journalFilename = 'journal.ndjson';

  final OfflineDirectoryProvider _directoryProvider;
  final DateTime Function() _clock;
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
      choice: metadata.reconciliationChoice,
    );
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

class OfflinePersistenceException implements Exception {
  const OfflinePersistenceException(this.message);

  final String message;

  @override
  String toString() => message;
}
