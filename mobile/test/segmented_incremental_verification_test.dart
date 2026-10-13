@Timeout(Duration(minutes: 8))
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:money_note_mobile/src/segmented/work.dart';
import 'support/segmented_e2_fixture.dart';

ObservationManifest manifest(GenerationFixture f) =>
    ObservationManifest.fromBytes(encodeC1(f.manifest));

void main() {
  final metrics = <Map<String, Object?>>[];
  tearDownAll(() {
    File('/tmp/money-note-i25-verifier-only.json')
        .writeAsStringSync(const JsonEncoder.withIndent('  ').convert(metrics));
  });
  for (final history in [16, 260, 1000]) {
    test(
        'full oracle vs incremental verifier at N history=$history, stable/small/insert/delete',
        () async {
      final bridge = await BackendBridge.start(history: history);
      var fixture = GenerationFixture(bridge.fixture);
      final bytes = {...fixture.objects};
      VerifiedObject read(ObjectRef ref) => VerifiedObject.verify(
          bytes[ref.hash] ?? (rejectSegment('OBJECT_MISSING')),
          ref,
          fixture.cache);
      var base = await verifyCompleteGeneration(manifest(fixture), read);
      try {
        for (final operation in [
          'identical',
          'mutate',
          'insert_history',
          'delete_history',
          'mutate',
          'identical'
        ]) {
          if (operation != 'identical') {
            await bridge.command({
              'command': operation,
              if (operation.endsWith('history')) 'count': 8
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
            bytes.addAll(fixture.objects);
          }
          final expectedBase = base.manifest,
              oldProof = base,
              work = SegmentedWork();
          var objectReads = 0, verifiedBytes = 0;
          final watch = Stopwatch()..start();
          final actual =
              await verifyIncrementalGeneration(manifest(fixture), base, (ref) {
            objectReads++;
            verifiedBytes += ref.byteLength;
            return read(ref);
          }, work: work);
          watch.stop();
          // Separate full reconstruction: no reuse cache is supplied to oracle.
          final full = await verifyCompleteGeneration(manifest(fixture), read,
              base: expectedBase);
          final a = decodeC1(actual.receipt) as Map,
              b = decodeC1(full.receipt) as Map;
          for (final field in [
            'target',
            'base_sync_root',
            'objects',
            'edges',
            'facts',
            'changed_rows',
            'reused_subtrees'
          ]) {
            expect(encodeC1(a[field]), encodeC1(b[field]), reason: field);
          }
          expect(actual.graph.objects.map((r) => r.hash).toSet(),
              full.graph.objects.map((r) => r.hash).toSet());
          expect(work.snapshot()['full_verifications'] ?? 0, 0);
          if (operation == 'identical') {
            // Header plus the facts-root count: independent of history size.
            expect(work.snapshot()['index_nodes_examined'], 2);
            expect(actual.difference.changes, isEmpty);
            expect(objectReads, lessThanOrEqualTo(10));
          }
          metrics.add({
            'history': history,
            'operation': operation,
            'objects': actual.graph.objects.length,
            'changed_rows': actual.difference.changes.length,
            'object_reads': objectReads,
            'verified_bytes': verifiedBytes,
            'work': work.snapshot(),
            'elapsed_us': watch.elapsedMicroseconds,
            'full_oracle': 'MATCHED',
            'publisher_integration': 'NOT IMPLEMENTED'
          });
          actual.adoptVerifiedData();
          if (oldProof.manifest.target.syncRoot !=
              actual.manifest.target.syncRoot) {
            // An old proof with an empty delta must not reset the catalogue's
            // identity and revive stale data provenance after a later adopt.
            expect(
                oldProof.adoptVerifiedData, throwsA(isA<SegmentedException>()));
            await expectLater(
                verifyIncrementalGeneration(manifest(fixture), oldProof, read),
                throwsA(isA<SegmentedException>()
                    .having((e) => e.code, 'code', 'BASE_PROVENANCE_INVALID')));
          }
          base = actual;
        }
      } finally {
        await bridge.dispose();
      }
    });
  }

  for (final kind in ['index-leaf', 'hot']) {
    test(
        'incremental rejects hash-valid inconsistent $kind with unchanged base',
        () async {
      final bridge = await BackendBridge.start();
      try {
        final fixture = GenerationFixture(bridge.fixture);
        final invalid = mutateGraph(fixture, kind, (body) {
          if (kind == 'index-leaf') {
            body['facts'][0]['value'] = 'invalid';
          } else {
            body['state']['settings']['scheduled_income'] = '123';
          }
        });
        final bytes = {...fixture.objects, ...invalid.objects};
        VerifiedObject read(ObjectRef ref) =>
            VerifiedObject.verify(bytes[ref.hash]!, ref, fixture.cache);
        final base = await verifyCompleteGeneration(manifest(fixture), read);
        await expectLater(
            verifyIncrementalGeneration(manifest(invalid), base, read),
            throwsA(isA<SegmentedException>()));
        await expectLater(
            verifyCompleteGeneration(manifest(invalid), read,
                base: base.manifest),
            throwsA(isA<SegmentedException>()));
      } finally {
        await bridge.dispose();
      }
    });
  }
  test('reused hot-referenced raw bytes still hash-verify on read', () async {
    final bridge = await BackendBridge.start();
    try {
      final fixture = GenerationFixture(bridge.fixture),
          bytes = {...GenerationFixture(bridge.fixture).objects};
      VerifiedObject read(ObjectRef ref) =>
          VerifiedObject.verify(bytes[ref.hash]!, ref, fixture.cache);
      final base = await verifyCompleteGeneration(manifest(fixture), read);
      final leaf = bytes.entries.firstWhere((e) {
        final b = decodeC1(e.value) as Map;
        return b['kind'] == 'snapshot-leaf' && b['table'] == 'ledger_entries';
      });
      bytes[leaf.key] = encodeC1({'corrupt': true});
      await expectLater(
          verifyIncrementalGeneration(manifest(fixture), base, read),
          throwsA(isA<SegmentedException>()));
    } finally {
      await bridge.dispose();
    }
  });
}
