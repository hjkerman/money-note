// 독립 감사 전용: 별도 process의 E1 handle을 유지하며 외부 SQLite와 동기화한다.
import 'dart:convert';
import 'dart:io';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

void emit(Map<String, dynamic> value) => stdout.writeln(jsonEncode(value));

void main(List<String> args) {
  final job = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final fixture =
      jsonDecode(File(job['fixture'] as String).readAsStringSync()) as Map;
  final manifest = ObservationManifest.fromBytes(
    base64Decode(fixture['manifest_base64'] as String),
  );
  final cache = CacheNamespace.forTarget(
    'https://reaudit.invalid',
    manifest.target,
  );
  final objects = (fixture['objects'] as List).cast<Map>();
  Map object(String kind) => objects.firstWhere((o) => o['kind'] == kind);
  var pause = '';
  late SegmentedClientStore store;
  var opened = false;
  try {
    store = SegmentedClientStore.open(
      Directory(job['root'] as String),
      cache,
      limits: ClientStoreLimits(
        objectCount: job['count'] as int? ?? 1,
        busyMilliseconds: job['busy_ms'] as int? ?? 50,
      ),
      fault: (point) {
        if (point == pause) {
          emit({'event': 'barrier', 'point': point});
          if (stdin.readLineSync() == 'abort') {
            throw const SegmentedException('AUDIT_ABORT');
          }
        }
      },
    );
    opened = true;
    const id = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    void putKind(String kind) {
      final item = object(kind);
      store.putVerifiedObject(
        ObjectRef.parse(item['ref']),
        base64Decode(item['data_base64'] as String),
      );
    }

    if (job['seed'] != false) {
      putKind('index-empty');
      store.createStaging(id, manifest, DateTime.utc(2026, 10, 12));
      store.recordStagedObject(
        id,
        ObjectRef.parse(object('index-empty')['ref']),
      );
    }
    emit({
      'event': 'opened',
      'path': store.path,
      'sqlite': sqlite3.version.toString(),
    });
    while (true) {
      final line = stdin.readLineSync();
      if (line == null) break;
      final command = jsonDecode(line) as Map;
      pause = command['pause_at'] as String? ?? '';
      try {
        switch (command['action']) {
          case 'put':
            putKind(command['kind'] as String? ?? 'raw-root');
          case 'duplicate':
            putKind('index-empty');
          case 'conflict':
            final item = object('index-empty');
            final raw = base64Decode(item['data_base64'] as String)..[0] = 0;
            store.putVerifiedObject(ObjectRef.parse(item['ref']), raw);
          case 'stage':
            store.createStaging(
              command['id'] as String? ??
                  'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',
              manifest,
              DateTime.utc(2026, 10, 12),
            );
          case 'progress':
            store.recordStagedObject(
              id,
              ObjectRef.parse(object('index-empty')['ref']),
            );
          case 'cleanup':
            store.removeUnreferencedStagingData(id);
          case 'read':
            final item = object(command['kind'] as String? ?? 'index-empty');
            final verified = store.getVerifiedObject(
              ObjectRef.parse(item['ref']),
            );
            emit({
              'ok': true,
              'data_base64': verified == null
                  ? null
                  : base64Encode(verified.bytes),
            });
            continue;
          case 'health':
            final health = store.inspectStoreHealth();
            emit({
              'ok': true,
              'healthy': health.healthy,
              'issues': health.issues,
            });
            continue;
          case 'money':
            final corpus = jsonDecode(
              File(command['corpus'] as String).readAsStringSync(),
            ) as Map;
            final results = <Map<String, dynamic>>[];
            for (final item in corpus['cases'] as List) {
              try {
                final ref = ObjectRef.parse(item['ref']);
                final raw = base64Decode(item['data_base64'] as String);
                final verified = store.putVerifiedObject(ref, raw);
                results.add({
                  'id': item['id'],
                  'accepted': true,
                  'preserved':
                      sameBytes(verified.bytes, raw) &&
                      verified.body['rows'][0]['value']['value'] ==
                          item['value'],
                  'hash': verified.ref.hash,
                });
              } on SegmentedException catch (error) {
                results.add({
                  'id': item['id'],
                  'accepted': false,
                  'error': error.code,
                });
              }
            }
            emit({'ok': true, 'results': results});
            continue;
          case 'benchmark':
            final item = object('index-empty');
            final ref = ObjectRef.parse(item['ref']);
            final raw = base64Decode(item['data_base64'] as String);
            for (var i = 0; i < 20; i++) {
              store.putVerifiedObject(ref, raw);
            }
            final putTimes = <int>[];
            for (var i = 0; i < 200; i++) {
              final timer = Stopwatch()..start();
              store.putVerifiedObject(ref, raw);
              putTimes.add(timer.elapsedMicroseconds);
            }
            final insertTimes = <int>[];
            if (command['corpus'] != null) {
              final corpus = jsonDecode(
                File(command['corpus'] as String).readAsStringSync(),
              ) as Map;
              final seen = <String>{ref.hash};
              for (final item in corpus['cases'] as List) {
                if (item['accepted'] != true ||
                    !seen.add(item['ref']['hash'] as String))
                  continue;
                final nextRef = ObjectRef.parse(item['ref']);
                final bytes = base64Decode(item['data_base64'] as String);
                final timer = Stopwatch()..start();
                store.putVerifiedObject(nextRef, bytes);
                insertTimes.add(timer.elapsedMicroseconds);
                if (insertTimes.length == 200) break;
              }
            }
            final direct = sqlite3.open(store.path);
            final catalog = {
              for (final row in direct.select(
                'SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL',
              ))
                row['name']: row['sql'],
            };
            final baseline = <int>[], checked = <int>[];
            for (var i = 0; i < 400; i++) {
              final timer = Stopwatch()..start();
              direct.execute('BEGIN IMMEDIATE');
              if (i.isOdd) {
                if (direct.select('PRAGMA user_version').single.values.first !=
                    1)
                  throw StateError('version');
                final rows = direct.select(
                  'SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name LIMIT ?',
                  [catalog.length + 1],
                );
                if (rows.length != catalog.length ||
                    rows.any((r) => catalog[r['name']] != r['sql']))
                  throw StateError('catalog');
              }
              direct.execute('ROLLBACK');
              (i.isOdd ? checked : baseline).add(timer.elapsedMicroseconds);
            }
            direct.close();
            emit({
              'ok': true,
              'duplicate_put_us': putTimes,
              'insert_us': insertTimes,
              'begin_rollback_us': baseline,
              'schema_transaction_us': checked,
              'catalog_definitions': catalog.length,
              'schema_queries_per_transaction': 2,
              'sqlite': sqlite3.version.toString(),
            });
            continue;
          case 'close':
            store.close();
            opened = false;
            emit({'ok': true});
            return;
          default:
            throw StateError('unknown audit action');
        }
        emit({'ok': true});
      } on SegmentedException catch (error) {
        emit({
          'ok': false,
          'error': error.code,
          'sqlite_code': error.storageCode,
        });
      } finally {
        pause = '';
      }
    }
  } on SegmentedException catch (error) {
    emit({'ok': false, 'error': error.code});
  } finally {
    if (opened) store.close();
  }
}
