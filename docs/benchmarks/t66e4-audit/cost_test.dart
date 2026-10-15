@Timeout(Duration(minutes: 18))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/segmented/audit_trace.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/e4_targeted_fixture.dart';
import '../../../mobile/test/support/segmented_e2_fixture.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final output = <Map<String, dynamic>>[];
  tearDownAll(() {
    const out = String.fromEnvironment('AUDIT_E4_COST');
    File(out).writeAsStringSync(jsonEncode(output));
  });
  for (final size in [5, 512]) {
    test('independent instrumented Frozen-B SQL and full-IO cost history=$size', () async {
      final bridge = await BackendBridge.start(history: size);
      final h = await E4Harness.create(bridge, await e4WireOracle());
      final phases = <Map<String, dynamic>>[];
      try {
        for (final object in bridge.fixture['objects']) {
          h.store.putVerifiedObject(
            ObjectRef.parse(object['ref']),
            base64Decode(object['data_base64']),
          );
        }
        final frozen = (await h.install()).frozen;
        final b = await h.workspace.readFrozenBaseline(h.store, frozen.id, 1);
        await h.workspace.saveMetadata(
          OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
            baselineLineageFingerprint: frozen.binding['legacy_lineage'],
          ),
        );
        for (var n = 0; n < 2; n++) {
          await h.workspace.appendOperation(
            type: OfflineOperationType.createCashFlow,
            payload: {
              'occurred_on': '2026-10-14',
              'title': '독립 계측 e\u0301 😀 $n',
              'amount_value': '+0003.00',
              'is_primary_income': 0,
            },
            baseline: b,
          );
        }
        final fullReader = OfflineStore(
          directoryProvider: () => Future.value(h.workspace.root),
        );
        final expected = (await readPendingLegacyView(fullReader, 1))!;
        var workspace = E4Workspace(h.root);
        Future<Map<String, dynamic>> measure(
          String name, {
          bool storeOnly = false,
          String? expectedError,
        }) async {
          AuditTrace.reset(name);
          final watch = Stopwatch()..start();
          PendingLegacyView? result;
          Object? failure;
          try {
            if (storeOnly) {
              final f = await h.store.recoverFrozenGeneration(frozen.id);
              h.store.withFrozenRead(f, (r) {
                r.hot;
                r.control;
              });
            } else {
              result = await workspace.readFrozenPending(h.store, frozen.id, 1);
            }
          } catch (error) {
            failure = error;
          }
          watch.stop();
          final events = AuditTrace.stop();
          if (expectedError == null) {
            expect(failure, null);
          } else {
            expect(
              failure,
              isA<SegmentedException>().having(
                (e) => e.code,
                'code',
                expectedError,
              ),
            );
          }
          // Independent full legacy reader is outside measured reuse work.
          if (result != null) {
            expect(
              result.bundle.baseline.toJson(),
              expected.bundle.baseline.toJson(),
            );
            expect(
              result.bundle.operations.map((o) => o.toJson()).toList(),
              expected.bundle.operations.map((o) => o.toJson()).toList(),
            );
            expect(
              result.projection!.summary.cashFlowBalance,
              expected.projection!.summary.cashFlowBalance,
            );
          }
          int sum(String key) =>
              events.fold(0, (n, e) => n + (e[key] as int? ?? 0));
          final counters = {
            'name': name,
            'error': failure is SegmentedException ? failure.code : null,
            'elapsed_us': watch.elapsedMicroseconds,
            'sql': events.where((e) => e.containsKey('sql')).length,
            'returned_rows': sum('rows_returned'),
            'body_bytes': sum('body_bytes_read'),
            'raw_rows': sum('raw_rows_read'),
            'raw_nodes': sum('raw_objects_read'),
            'index_nodes': sum('index_objects_read'),
            'pin_insert': sum('pin_insert'),
            'pin_delete': sum('pin_delete'),
            'pin_update': sum('pin_update'),
            'full_verify_calls': events
                .where((e) => e['note'] == 'full_verify')
                .length,
            'frozen_recovery_calls': events
                .where((e) => e['note'] == 'frozen_full_recovery')
                .length,
            'legacy_full_reads': events
                .where((e) => e['note'] == 'legacy_full_read')
                .length,
            'lineage_hashes': events
                .where((e) => e['note'] == 'lineage_hash')
                .length,
            'sql_texts': events
                .where((e) => e.containsKey('sql'))
                .map((e) => e['sql'])
                .toSet()
                .toList(),
            'objects': events
                .expand((e) => (e['object_identities'] as List? ?? []))
                .toSet()
                .toList(),
            'rss_bytes': ProcessInfo.currentRss,
          };
          phases.add(counters);
          return counters;
        }

        // Fresh store AND workspace: real cold proof (not just a fresh B cache).
        h.reopen();
        await measure('cold');
        for (final phase in ['warm1', 'warm2']) {
          final c = await measure(phase);
          for (final key in [
            'raw_rows',
            'raw_nodes',
            'index_nodes',
            'full_verify_calls',
            'frozen_recovery_calls',
            'legacy_full_reads',
            'lineage_hashes',
            'pin_insert',
            'pin_delete',
            'pin_update',
          ]) {
            expect(c[key], 0, reason: '$phase $key');
          }
        }
        await measure('store_only_warm', storeOnly: true);
        await bridge.command({'command': 'mutate'});
        await h.publish();
        final unrelated = await measure('unrelated_accepted');
        expect(unrelated['full_verify_calls'], 0);
        final other = SegmentedClientStore.open(
          h.root,
          h.store.cache,
          adapters: true,
        );
        other.createStaging(
          syncUuid(),
          ObservationManifest.fromBytes(
            encodeC1(GenerationFixture(bridge.fixture).manifest),
          ),
          DateTime.now().toUtc(),
        );
        other.close();
        final invalidated = await measure('external_commit');
        expect(invalidated['full_verify_calls'], 1);
        expect(invalidated['legacy_full_reads'], 1);
        await measure('warm_after_fallback');
        h.reopen();
        workspace = E4Workspace(h.root);
        final fresh = await measure('reopen');
        expect(fresh['full_verify_calls'], 1);
        await measure('warm_after_reopen');
        final injection = sqlite3.open(h.store.path);
        final beforeBytes = h.baselineFile.readAsBytesSync();
        final raw = injection
            .select(
              "SELECT hash,body FROM objects WHERE kind='snapshot-leaf' ORDER BY hash LIMIT 1",
            )
            .single;
        final immutable =
            injection
                    .select(
                      "SELECT sql FROM sqlite_master WHERE name='immutable_body'",
                    )
                    .single['sql']
                as String;
        final oldBody = List<int>.from(raw['body'] as List<int>);
        final canonOffset = utf8.decode(oldBody).indexOf('"canon":1') + 8;
        expect(oldBody[canonOffset], 49);
        final badBody = List<int>.of(oldBody)..[canonOffset] = 50;
        injection.execute('DROP TRIGGER immutable_body');
        injection.execute('UPDATE objects SET body=? WHERE hash=?', [
          badBody,
          raw['hash'],
        ]);
        injection.execute(immutable);
        await measure(
          'corrupt_frozen_object',
          expectedError: 'OBJECT_HASH_INVALID',
        );
        expect(h.baselineFile.readAsBytesSync(), beforeBytes);
        injection.execute('DROP TRIGGER immutable_body');
        injection.execute('UPDATE objects SET body=? WHERE hash=?', [
          oldBody,
          raw['hash'],
        ]);
        injection.execute(immutable);
        await measure('repaired_exact_bytes');
        final pinGuard =
            injection
                    .select(
                      "SELECT sql FROM sqlite_master WHERE name='retained_root_delete'",
                    )
                    .single['sql']
                as String;
        final hot = frozen.target.roots['hot']!.hash;
        injection.execute('DROP TRIGGER retained_root_delete');
        injection.execute(
          'DELETE FROM generation_roots WHERE generation_id=? AND hash=?',
          [frozen.generationId, hot],
        );
        injection.execute(pinGuard);
        await measure(
          'concurrent_missing_pin',
          expectedError: 'GENERATION_RECEIPT_INVALID',
        );
        injection.execute('INSERT INTO generation_roots VALUES(?,?)', [
          frozen.generationId,
          hot,
        ]);
        injection.close();
        await measure('restored_pin');
        final altered =
            jsonDecode(utf8.decode(beforeBytes)) as Map<String, dynamic>;
        altered['synced_at'] = '2021-01-01T00:00:00.000Z';
        h.baselineFile.writeAsStringSync(jsonEncode(altered), flush: true);
        await measure(
          'changed_legacy_lineage',
          expectedError: 'LEGACY_LINEAGE_UNAVAILABLE',
        );
        h.baselineFile.writeAsBytesSync(beforeBytes, flush: true);
        await measure('restored_legacy_bytes');
        final direct = sqlite3.open(h.store.path);
        final pins = direct
            .select(
              'SELECT generation_id,hash FROM generation_roots ORDER BY generation_id,hash',
            )
            .map((r) => Map<String, dynamic>.from(r))
            .toList();
        direct.close();
        final inspect = await Process.run(
          '${Directory.current.parent.path}/.venv/bin/python',
          [
            '${Directory.current.parent.path}/docs/benchmarks/t66e4-audit/state_oracle.py',
            h.store.path,
            h.workspace.root.path,
          ],
        );
        expect(inspect.exitCode, 0, reason: inspect.stderr as String);
        output.add({
          'history': size,
          'required_objects': (bridge.fixture['objects'] as List).length,
          'phases': phases,
          'pins': pins,
          'persisted': jsonDecode(inspect.stdout as String),
        });
      } finally {
        h.dispose();
        await bridge.dispose();
      }
    });
  }
}
