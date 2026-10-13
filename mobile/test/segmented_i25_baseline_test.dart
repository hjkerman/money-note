@Timeout(Duration(minutes: 10))
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:sqlite3/sqlite3.dart';
import 'support/segmented_e2_fixture.dart';

// Historical baseline: intentionally calls the original complete verification
// and recovery. Retained as a reference workload, not the optimized E3 path.
void main() {
  test('I25 original work: cold/identical/delta/repeated/reopen/failure retry',
      () async {
    final results = <Map<String, Object?>>[];
    for (final history in [16, 260]) {
      final bridge = await BackendBridge.start(history: history);
      final root =
          Directory.systemTemp.createTempSync('money-note-i25-before-');
      var fixture = GenerationFixture(bridge.fixture);
      var db =
          SegmentedClientStore.open(root, fixture.cache, publication: true);
      Future<void> sample(String label, {bool fail = false}) async {
        final before = db.work.snapshot(), watch = Stopwatch()..start();
        final expected = await db.recoverAcceptedGeneration();
        final acquired =
            await IncrementalFetcher(db, FixtureTransport(fixture)).acquire();
        final version = db.publicationDataVersion;
        final proof = await verifyCompleteGeneration(
            acquired.manifest, (ref) => db.getVerifiedObject(ref)!,
            base: expected.manifest, work: db.work);
        final prepared = db.prepareGeneration(
            syncUuid(), acquired.stagingId, proof, expected,
            verifiedDataVersion: version);
        SegmentedPublication? result;
        if (fail) {
          expect(
              () => db.commitPreparedGeneration(prepared,
                      finalAuthorityFence: () {
                    throw const SegmentedException('BASELINE_ROLLBACK');
                  }),
              throwsA(isA<SegmentedException>()));
        } else {
          result =
              db.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
        }
        db.discardUnacceptedGeneration(prepared.id);
        final elapsed = watch.elapsedMicroseconds;
        final direct = sqlite3.open(db.path);
        final pins = direct
            .select('SELECT count(*) AS n FROM generation_objects')
            .single['n'];
        expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
        direct.close();
        results.add({
          'history': history,
          'scenario': label,
          'objects': proof.graph.objects.length,
          'changed_rows': proof.difference.changes.length,
          'tree_nodes': proof.difference.examinedObjects,
          'reused_subtrees': proof.difference.reusedSubtrees,
          'pin_rows': pins,
          'work': db.work.since(before),
          'elapsed_us': elapsed,
          'critical_us': result?.transactionMicroseconds,
          'correct': true
        });
      }

      try {
        await sample('cold');
        await sample('identical');
        for (var i = 0; i < 3; i++) {
          await bridge.command({'command': 'mutate'});
          final response = await bridge.command({
            'command': 'http',
            'method': 'POST',
            'path': '/api/sync/v1/observations',
            'headers': {
              'Authorization': 'Bearer ${bridge.token}',
              'Content-Type': 'application/json'
            },
            'body_base64': base64Encode(encodeC1({
              'protocol': 1,
              'request_id': syncUuid(),
              'base': null,
              'inline_bytes': 0
            }))
          });
          expect(response['status'], 201);
          fixture =
              GenerationFixture(await bridge.command({'command': 'oracle'}));
          await sample('small_change_$i');
        }
        db.close();
        db = SegmentedClientStore.open(root, fixture.cache, publication: true);
        await sample('reopen');
        await sample('after_reopen');
        await sample('failed', fail: true);
        await sample('retry');
      } finally {
        db.close();
        await bridge.dispose();
        root.deleteSync(recursive: true);
      }
    }
    File('/tmp/money-note-e3-i25-before.json')
        .writeAsStringSync(const JsonEncoder.withIndent('  ').convert(results));
  });
}
