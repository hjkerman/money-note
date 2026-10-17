@Timeout(Duration(hours: 12))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:sqlite3/sqlite3.dart';

import 'cost_harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final evidence = <Map<String, dynamic>>[];
  tearDownAll(() {
    File(const String.fromEnvironment('AUDIT_E4_COST'))
        .writeAsStringSync(jsonEncode(evidence));
  });
  for (final history in [
    const int.fromEnvironment('COST_N', defaultValue: 1000),
  ]) {
    test('FC$history independently observed real D→E work', () async {
      final b = await RealBackend.start(history);
      final h = await RealHarness.create(b);
      final phases = <Map<String, dynamic>>[];
      try {
        Future<Map<String, dynamic>> measure(
          String name,
          Future<void> Function() run,
        ) async {
          await b.stats(reset: true);
          AuditTrace.reset(name);
          final elapsed = Stopwatch()..start();
          await run();
          elapsed.stop();
          final events = AuditTrace.stop();
          final backendCounters = await b.command({'command': 'stats'});
          final wire = (backendCounters['records'] as List)
              .cast<Map<String, dynamic>>();
          int sum(String k) =>
              events.fold(0, (n, e) => n + (e[k] as int? ?? 0));
          final db = sqlite3.open(h.store.path);
          final graphObjects = db
              .select(
                'SELECT object_count FROM generations WHERE id=(SELECT current_id FROM accepted)',
              )
              .single['object_count'];
          db.close();
          final row = <String, dynamic>{
            'phase': name,
            'backend_sql_trace_events':
                backendCounters['backend_sql_trace_events'],
            'backend_sql_trace': backendCounters['backend_sql_trace'],
            'graph_objects': graphObjects,
            'http_requests': wire.length,
            'object_requests': wire
                .where((r) => (r['path'] as String).endsWith('/objects'))
                .length,
            'http_response_bytes': wire.fold<int>(
              0,
              (n, r) => n + (r['response_bytes'] as int),
            ),
            'decoded_payload_bytes': wire.fold<int>(
              0,
              (n, r) => n + (r['decoded_bytes'] as int),
            ),
            'requested_objects': {
              for (final r in wire) ...((r['objects'] as List).cast<String>()),
            }.toList(),
            'sql': events.where((e) => e['sql'] != null).length,
            'rows_returned': sum('rows_returned'),
            'object_bytes': sum('body_bytes_read'),
            'raw_nodes': sum('raw_objects_read'),
            'raw_rows': sum('raw_rows_read'),
            'index_nodes': sum('index_objects_read'),
            'pin_insert': sum('pin_insert'),
            'pin_delete': sum('pin_delete'),
            'pin_update': sum('pin_update'),
            for (final note in [
              'full_verify',
              'frozen_full_recovery',
              'legacy_full_read',
              'lineage_hash',
            ])
              note: events.where((e) => e['note'] == note).length,
            'microseconds': elapsed.elapsedMicroseconds,
            'rss_bytes': ProcessInfo.currentRss,
            'sql_frequencies': <String, int>{
              for (final s
                  in events
                      .where((e) => e['sql'] != null)
                      .map((e) => e['sql'] as String)
                      .toSet())
                s: events.where((e) => e['sql'] == s).length,
            },
          };
          phases.add(row);
          File(const String.fromEnvironment('AUDIT_E4_COST') + '.partial')
              .writeAsStringSync(
                jsonEncode({'history': history, 'phases': phases}),
              );
          return row;
        }

        if (history > 1000) {
          // 검증된 E1 cache 준비는 측정 밖이다. accepted pointer를 만들지 않는다.
          for (final object in b.fixture['objects'] as List) {
            h.store.putVerifiedObject(
              ObjectRef.parse(object['ref']),
              base64Decode(object['data_base64']),
            );
          }
          expect((h.disk()['accepted'] as List).single['current_id'], isNull);
        }
        await measure(
          history > 1000 ? 'verified_cached_initial' : 'cold_native',
          () async {
            await h.state.refreshSegmentedForIsolatedUse(h.store);
          },
        );
        for (var i = 0; i < 23; i++) {
          final identical = await measure('identical_$i', () async {
            await h.state.refreshSegmentedForIsolatedUse(h.store);
          });
          expect(identical['object_requests'], 0);
          expect(identical['full_verify'], 0);
        }
        for (final workload in ['card', 'cash']) {
          for (var i = 0; i < 23; i++) {
            await b.command({
              'command': 'mutate',
              'op': workload == 'cash' ? 'cash' : 'update',
              'title': 'fixed-width-$workload-${i % 2}',
            });
            final changed = await measure('${workload}_$i', () async {
              await h.state.refreshSegmentedForIsolatedUse(h.store);
            });
            expect(changed['full_verify'], 0);
          }
        }
        final frozen = await h.state.installSegmentedLegacyForIsolatedUse(
          h.store,
        );
        Future<void> read() async {
          await h.workspace.readFrozenBaseline(h.store, frozen.frozen.id, 1);
        }

        await read();
        for (var n = 0; n < 23; n++) {
          final r = await measure('repeated_frozen_$n', read);
          for (final key in [
            'raw_nodes',
            'raw_rows',
            'index_nodes',
            'pin_insert',
            'pin_delete',
            'pin_update',
            'full_verify',
            'frozen_full_recovery',
            'lineage_hash',
            'legacy_full_read',
          ]) {
            expect(r[key], 0, reason: '$key repeated Frozen B');
          }
        }
        await b.command({
          'command': 'mutate',
          'title': 'unrelated accepted G2',
        });
        await h.state.refreshSegmentedForIsolatedUse(h.store);
        final after = await measure('frozen_after_native_G2', read);
        expect(after['full_verify'], 0);
        expect(after['raw_nodes'], 0);
        h.reopen();
        await measure('fresh_handle_fallback', read);
        final oracle = await h.inspect();
        evidence.add({'history': history, 'phases': phases, 'oracle': oracle});
      } finally {
        h.dispose();
        await b.dispose();
      }
    });
  }
}
