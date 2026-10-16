@Timeout(Duration(minutes: 18))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final evidence = <Map<String, dynamic>>[];
  tearDownAll(() {
    const out = String.fromEnvironment('AUDIT_E4_COST');
    File(out).writeAsStringSync(jsonEncode(evidence));
  });
  for (final history in [7, 256]) {
    test(
      'NC$history independent warm read around rejected native provenance',
      () async {
        final bridge = await BackendBridge.start(history: history);
        final h = await E4Harness.create(bridge, await e4WireOracle());
        final phases = <Map<String, dynamic>>[];
        try {
          await h.workspace.beginOnlineWrite(1);
          final f = (await h.install()).frozen;
          final baseline = h.baselineFile.readAsBytesSync();
          final pending = h.pendingFile.readAsBytesSync();
          final source = File('${h.workspace.root.path}/e4-source.json');
          final db = sqlite3.open(h.store.path);
          late List<Map<String, dynamic>> pins;
          late int objects;
          try {
            pins = db
                .select('SELECT * FROM generation_roots ORDER BY 1,2')
                .map((r) => Map<String, dynamic>.from(r))
                .toList();
            objects =
                db.select('SELECT COUNT(*) AS n FROM objects').single['n']
                    as int;
          } finally {
            db.close();
          }
          Future<Map<String, dynamic>> measure(
            String name,
            Future<void> Function() run,
          ) async {
            AuditTrace.reset(name);
            final watch = Stopwatch()..start();
            await run();
            watch.stop();
            final events = AuditTrace.stop();
            int sum(String key) =>
                events.fold(0, (n, e) => n + (e[key] as int? ?? 0));
            final row = <String, dynamic>{
              'phase': name,
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
              'microseconds': watch.elapsedMicroseconds,
              'rss_bytes': ProcessInfo.currentRss,
            };
            phases.add(row);
            return row;
          }

          Future<void> read() async {
            final b = await h.workspace.readFrozenBaseline(h.store, f.id, 1);
            expect(b.serverStateFingerprint, f.binding['legacy_fingerprint']);
          }

          void warm(Map<String, dynamic> row) {
            for (final field in [
              'raw_nodes',
              'raw_rows',
              'index_nodes',
              'full_verify',
              'frozen_full_recovery',
              'legacy_full_read',
              'lineage_hash',
              'pin_insert',
              'pin_delete',
              'pin_update',
            ]) {
              expect(row[field], 0, reason: '$field ${row['phase']}');
            }
          }

          await read();
          final initial = await measure('warm_legacy', read);
          warm(initial);
          await h.state.refreshSegmentedForIsolatedUse(h.store);
          final native = await measure('warm_native', read);
          warm(native);
          await bridge.command({'command': 'mutate'});
          await h.publish();
          h.workspace.prepareSegmentedSource(
            h.store,
            h.store.acceptedGeneration(),
            () {},
          );
          final valid = source.readAsBytesSync();
          final damaged = jsonDecode(source.readAsStringSync())
            ..['previous_source'] = null;
          source.writeAsStringSync(jsonEncode(damaged), flush: true);
          await measure('missing_required_rejected', () async {
            await expectLater(
              h.state.refreshSegmentedForIsolatedUse(h.store),
              throwsA(
                isA<SegmentedException>().having(
                  (e) => e.code,
                  'code',
                  'SOURCE_PROVENANCE_REQUIRED',
                ),
              ),
            );
          });
          warm(await measure('warm_after_rejected_native', read));
          source.writeAsBytesSync(
            valid,
            flush: true,
          ); // test-owned exact repair.
          await measure('legitimate_native_recovery', () async {
            await h.workspace.recoverLegacyHandoff(h.store);
          });
          warm(await measure('warm_after_recovery', read));
          h.reopen();
          await measure('fresh_handle', () async {
            await E4Workspace(h.root).readFrozenBaseline(h.store, f.id, 1);
          });
          expect(h.baselineFile.readAsBytesSync(), baseline);
          expect(h.pendingFile.readAsBytesSync(), pending);
          final after = sqlite3.open(h.store.path);
          try {
            for (final pin in pins) {
              expect(
                after.select(
                  'SELECT * FROM generation_roots WHERE generation_id=? AND hash=?',
                  [pin['generation_id'], pin['hash']],
                ).single,
                pin,
              );
            }
          } finally {
            after.close();
          }
          evidence.add({
            'history': history,
            'objects': objects,
            'phases': phases,
          });
        } finally {
          h.dispose();
          await bridge.dispose();
        }
      },
    );
  }
}
