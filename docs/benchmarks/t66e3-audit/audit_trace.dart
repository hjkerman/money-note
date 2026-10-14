// 폐기용 source copy에만 연결한다. 제품 counter를 읽지 않는 SQL/row observer다.
import 'dart:convert';
import 'dart:typed_data';

import 'package:sqlite3/sqlite3.dart';

class AuditTrace {
  static bool enabled = false;
  static String phase = '';
  static final events = <Map<String, Object?>>[];
  static void reset(String value) {
    phase = value;
    events.clear();
    enabled = true;
  }

  static List<Map<String, Object?>> stop() {
    enabled = false;
    return List.of(events);
  }
}

class AuditDatabase implements Database {
  AuditDatabase(this.inner);
  final Database inner;
  Stopwatch? transaction;
  @override
  void execute(String sql, [List<Object?> parameters = const []]) {
    final normalized = sql.trim().replaceAll(RegExp(r'\s+'), ' ');
    int roots = 0, objects = 0;
    if (AuditTrace.enabled &&
        normalized.startsWith('DELETE FROM generations')) {
      final rootTable = inner
          .select("SELECT 1 FROM sqlite_master WHERE name='generation_roots'")
          .isNotEmpty;
      roots = rootTable
          ? inner
                    .select(
                      'SELECT count(*) AS n FROM generation_roots WHERE generation_id=?',
                      parameters,
                    )
                    .single['n']
                as int
          : 0;
      objects =
          inner
                  .select(
                    'SELECT count(*) AS n FROM generation_objects WHERE generation_id=?',
                    parameters,
                  )
                  .single['n']
              as int;
    }
    if (normalized == 'BEGIN IMMEDIATE') transaction = Stopwatch()..start();
    inner.execute(sql, parameters);
    if (AuditTrace.enabled) {
      final event = <String, Object?>{
        'phase': AuditTrace.phase,
        'sql': normalized,
        'rows_changed': inner.updatedRows,
      };
      if (normalized.startsWith('INSERT INTO generation_roots'))
        event['pin_insert'] = inner.updatedRows;
      if (normalized.startsWith('INSERT INTO generation_objects'))
        event['pin_insert'] = inner.updatedRows;
      if (normalized.startsWith('DELETE FROM generations')) {
        event['pin_delete'] = roots + objects;
      }
      if (normalized.startsWith('UPDATE generation_roots') ||
          normalized.startsWith('UPDATE generation_objects'))
        event['pin_update'] = inner.updatedRows;
      if (normalized == 'COMMIT' || normalized == 'ROLLBACK') {
        event['transaction_us'] = transaction?.elapsedMicroseconds;
      }
      AuditTrace.events.add(event);
    }
  }

  @override
  ResultSet select(String sql, [List<Object?> parameters = const []]) {
    final result = inner.select(sql, parameters);
    if (AuditTrace.enabled) {
      int bodies = 0, rawRows = 0, rawObjects = 0, indexObjects = 0;
      final identities = <String>[];
      for (final row in result) {
        if (row.keys.contains('body') && row['body'] is Uint8List) {
          final bytes = row['body'] as Uint8List;
          bodies += bytes.length;
          final body = jsonDecode(utf8.decode(bytes)) as Map;
          identities.add(row['hash'] as String);
          if ((body['kind'] as String).startsWith('snapshot-')) rawObjects++;
          if ((body['kind'] as String).startsWith('index-')) indexObjects++;
          if (body['kind'] == 'snapshot-leaf')
            rawRows += (body['rows'] as List).length;
        }
      }
      AuditTrace.events.add({
        'phase': AuditTrace.phase,
        'sql': sql.trim().replaceAll(RegExp(r'\s+'), ' '),
        'rows_returned': result.length,
        'body_bytes_read': bodies,
        'raw_rows_read': rawRows,
        'raw_objects_read': rawObjects,
        'index_objects_read': indexObjects,
        'object_identities': identities,
      });
    }
    return result;
  }

  @override
  int get updatedRows => inner.updatedRows;
  @override
  void close() => inner.close();
  @override
  dynamic noSuchMethod(Invocation invocation) => throw UnsupportedError(
    'audited store used unexpected database API: ${invocation.memberName}',
  );
}
