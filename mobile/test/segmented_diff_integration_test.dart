@Timeout(Duration(minutes: 10))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';

void main() {
  test(
      'independent SQLite oracle: update, split/insert, delete, no-change and publication metrics',
      () async {
    final bridge = await BackendBridge.start(history: 260);
    final root = Directory.systemTemp.createTempSync('money-note-e3-diff-');
    var fixture = GenerationFixture(bridge.fixture);
    final db =
        SegmentedClientStore.open(root, fixture.cache, publication: true);
    final metrics = <Map<String, Object?>>[];
    try {
      for (final operation in [
        'initial',
        'mutate',
        'insert_history',
        'delete_history',
        'unchanged'
      ]) {
        final before = fixture;
        if (operation != 'initial' && operation != 'unchanged') {
          await bridge.command({
            'command': operation,
            if (operation.endsWith('history')) 'count': 260
          });
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
        }
        final base = db.acceptedGeneration(),
            transport = FixtureTransport(fixture);
        final acquired = await IncrementalFetcher(db, transport).acquire();
        final version = db.publicationDataVersion;
        final proof = await verifyCompleteGeneration(
            acquired.manifest, (ref) => db.getVerifiedObject(ref)!,
            base: base.manifest);
        // Independent row-set comparison from the backend's direct SQL source.
        final expected = <String>{};
        for (final table in segmentedTables) {
          final oldRows = {
            if (operation != 'initial')
              for (final r in before.source[table])
                '${r[primaryColumn(table)]}': r
          };
          final newRows = {
            for (final r in fixture.source[table])
              '${r[primaryColumn(table)]}': r
          };
          for (final key in {...oldRows.keys, ...newRows.keys}) {
            if (!sameBytes(encodeC1(oldRows[key]), encodeC1(newRows[key]))) {
              expected.add('$table/$key');
            }
          }
        }
        expect(
            proof.difference.changes
                .map((c) => '${c.table}/${c.key[1]}')
                .toSet(),
            expected);
        if (operation != 'initial') {
          expect(proof.difference.reusedSubtrees, greaterThanOrEqualTo(10));
        }
        if (operation == 'unchanged') {
          expect(proof.difference.changes, isEmpty);
          expect(transport.objectRequests, 0);
        }
        final prepared = db.prepareGeneration(
            syncUuid(), acquired.stagingId, proof, base,
            verifiedDataVersion: version);
        final published =
            db.commitPreparedGeneration(prepared, finalAuthorityFence: () {});
        db.discardUnacceptedGeneration(prepared.id);
        final clock = Stopwatch()..start();
        await db.recoverAcceptedGeneration();
        clock.stop();
        final direct = sqlite3.open(db.path);
        expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
        expect(
            direct.select('SELECT count(*) AS n FROM generations').single['n'],
            lessThanOrEqualTo(2));
        final stored =
            direct.select('SELECT metadata,payload,objects FROM usage').single;
        metrics.add({
          'operation': operation,
          'objects': proof.graph.objects.length,
          'changed_rows': expected.length,
          'reused_subtrees': proof.difference.reusedSubtrees,
          'diff_objects_examined': proof.difference.examinedObjects,
          'object_requests': transport.objectRequests,
          'payload_bytes': transport.payloadBytes,
          'verification_us': proof.verificationMicroseconds,
          'publication_us': published.transactionMicroseconds,
          'readback_us': published.readbackMicroseconds,
          'recovery_us': clock.elapsedMicroseconds,
          'store_metadata_bytes': stored['metadata'],
          'store_payload_bytes': stored['payload']
        });
        direct.close();
      }
      File('/tmp/money-note-e3-measurements.json').writeAsStringSync(
          const JsonEncoder.withIndent('  ').convert(metrics));
    } finally {
      db.close();
      root.deleteSync(recursive: true);
      await bridge.dispose();
    }
  });
}
