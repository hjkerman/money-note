@Timeout(Duration(minutes: 12))
library;

import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:sqlite3/sqlite3.dart';
import 'support/segmented_e2_fixture.dart';

class Attempt {
  Attempt(this.prepared, this.proof, this.stage,
      [this.recoveryMicroseconds = 0]);
  final PreparedGeneration prepared;
  final CompleteGenerationProof proof;
  final VerifiedStagedGeneration stage;
  final int recoveryMicroseconds;
}

Future<Attempt> prepare(
    SegmentedClientStore db, GenerationFixture fixture) async {
  final recovery = Stopwatch()..start();
  final expected = await db.recoverAcceptedGeneration();
  recovery.stop();
  final staged = await IncrementalFetcher(db, FixtureTransport(fixture))
      .acquire(verifiedBase: expected);
  final version = db.publicationDataVersion;
  final proof = await db.verifyPublicationCandidate(staged.manifest, expected,
      verifiedDataVersion: version);
  return Attempt(
      db.prepareGeneration(syncUuid(), staged.stagingId, proof, expected,
          verifiedDataVersion: version),
      proof,
      staged,
      recovery.elapsedMicroseconds);
}

SegmentedPublication commit(SegmentedClientStore db, Attempt a) {
  final result =
      db.commitPreparedGeneration(a.prepared, finalAuthorityFence: () {});
  db.discardUnacceptedGeneration(a.prepared.id);
  return result;
}

// Server fixture is the independent object-set oracle, NOT graph.isComplete.
void inspect(SegmentedClientStore store, GenerationFixture fixture,
    {Map<String, Set<String>>? expectedGraphs}) {
  final db = sqlite3.open(store.path);
  try {
    expect(db.select('PRAGMA foreign_key_check'), isEmpty);
    final p = db.select('SELECT * FROM accepted').single;
    final g = db.select(
        'SELECT * FROM generations WHERE id=?', [p['current_id']]).single;
    final receipt = decodeC1(g['receipt'] as List<int>) as Map;
    expect(receipt['target']['sync_root'], fixture.target.syncRoot);
    expect(receipt['objects'], fixture.objects.length);
    final actual = db.select('''WITH RECURSIVE closure(hash) AS (
      SELECT hash FROM generation_roots WHERE generation_id=?
      UNION SELECT hash FROM generation_objects WHERE generation_id=?
      UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash)
      SELECT hash FROM closure''', [p['current_id'], p['current_id']]);
    expect(actual.map((r) => r['hash']).toSet(), fixture.objects.keys.toSet());
    if (p['previous_id'] != null && expectedGraphs != null) {
      final previous = db.select('SELECT receipt FROM generations WHERE id=?',
          [p['previous_id']]).single;
      final target = (decodeC1(previous['receipt'] as List<int>)
          as Map)['target']['sync_root'];
      final retained = db.select('''WITH RECURSIVE closure(hash) AS (
        SELECT hash FROM generation_roots WHERE generation_id=?
        UNION SELECT hash FROM generation_objects WHERE generation_id=?
        UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash)
        SELECT hash FROM closure''', [p['previous_id'], p['previous_id']]);
      expect(expectedGraphs[target], isNotNull);
      expect(retained.map((r) => r['hash']).toSet(), expectedGraphs[target]);
    }
    expect(
        db.select(
            'SELECT count(*) AS n FROM generation_roots WHERE generation_id=?',
            [p['current_id']]).single['n'],
        4);
    expect(
        db.select('SELECT * FROM generation_objects WHERE generation_id=?',
            [p['current_id']]),
        isEmpty);
  } finally {
    db.close();
  }
}

Future<GenerationFixture> change(BackendBridge bridge, String operation) async {
  await bridge.command(
      {'command': operation, if (operation.endsWith('history')) 'count': 8});
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
  return GenerationFixture(await bridge.command({'command': 'oracle'}));
}

void main() {
  final measurements = <Map<String, Object?>>[];
  tearDownAll(() {
    if (measurements.isEmpty) return;
    File('/tmp/money-note-i25-publication.json').writeAsStringSync(
        const JsonEncoder.withIndent('  ').convert(measurements));
  });
  for (final history in [16, 260, 1000]) {
    test('I25 integrated N=$history: cold/identical/change/restart/rollback',
        () async {
      final bridge = await BackendBridge.start(history: history);
      var fixture = GenerationFixture(bridge.fixture);
      final expectedGraphs = <String, Set<String>>{
        fixture.target.syncRoot: fixture.objects.keys.toSet()
      };
      final root =
          Directory.systemTemp.createTempSync('money-note-i25-publish-');
      var db =
          SegmentedClientStore.open(root, fixture.cache, publication: true);
      try {
        for (final operation in [
          'cold',
          'identical',
          'mutate',
          'insert_history',
          'delete_history',
          'mutate',
          'identical',
          'restart',
          'after_restart',
          'rollback',
          'retry'
        ]) {
          if (['mutate', 'insert_history', 'delete_history']
              .contains(operation)) {
            fixture = await change(bridge, operation);
            expectedGraphs[fixture.target.syncRoot] =
                fixture.objects.keys.toSet();
          }
          if (operation == 'restart') {
            db.close();
            db = SegmentedClientStore.open(root, fixture.cache,
                publication: true);
          }
          final before = db.work.snapshot(), timer = Stopwatch()..start();
          final a = await prepare(db, fixture);
          SegmentedPublication? result;
          if (operation == 'rollback') {
            expect(
                () => db.commitPreparedGeneration(a.prepared,
                        finalAuthorityFence: () {
                      throw const SegmentedException('ROLLBACK');
                    }),
                throwsA(isA<SegmentedException>()));
            db.discardUnacceptedGeneration(a.prepared.id);
          } else {
            result = commit(db, a);
          }
          final elapsed = timer.elapsedMicroseconds,
              work = db.work.since(before);
          // Actual operation counters, not wall-clock-only improvement.
          expect(work['pin_inserts'], 4);
          if (!['cold', 'restart', 'retry'].contains(operation)) {
            expect(work['full_recoveries'] ?? 0, 0);
            expect(work['full_verifications'] ?? 0, 0);
          }
          if (['identical', 'after_restart'].contains(operation)) {
            expect(work['object_reads'], lessThanOrEqualTo(12));
            expect(a.stage.metrics.objectRequests, 0);
          }
          if (operation == 'mutate') {
            expect(work['object_reads'], lessThan(200));
            expect(a.proof.difference.changes.length, 1);
          }
          if (['restart', 'retry'].contains(operation)) {
            expect(work['full_recoveries'], 1);
          }
          // Separate complete oracle outside the measured interval.
          final full = await verifyCompleteGeneration(
              a.proof.manifest, (r) => db.getVerifiedObject(r)!);
          final p = decodeC1(a.proof.receipt) as Map,
              f = decodeC1(full.receipt) as Map;
          for (final key in ['target', 'objects', 'edges', 'facts']) {
            expect(encodeC1(p[key]), encodeC1(f[key]));
          }
          inspect(db, fixture, expectedGraphs: expectedGraphs);
          final direct = sqlite3.open(db.path);
          final rootRows = direct
              .select('SELECT count(*) AS n FROM generation_roots')
              .single['n'];
          expect(rootRows as int, lessThanOrEqualTo(12));
          direct.close();
          final plans = sqlite3.open(db.path);
          final pinPlan = plans
              .select(
                  'EXPLAIN QUERY PLAN SELECT count(*) FROM generation_roots WHERE generation_id=?',
                  [a.prepared.id])
              .map((r) => r['detail'])
              .toList();
          plans.close();
          measurements.add({
            'history': history,
            'scenario': operation,
            'objects': fixture.objects.length,
            'changed_rows': a.proof.difference.changes.length,
            'work': work,
            'object_requests': a.stage.metrics.objectRequests,
            'payload_bytes': a.stage.metrics.payloadBytes,
            'root_pin_rows': rootRows,
            'elapsed_us': elapsed,
            'recovery_us': a.recoveryMicroseconds,
            'verification_us': a.proof.verificationMicroseconds,
            'critical_us': result?.transactionMicroseconds,
            'readback_us': result?.readbackMicroseconds,
            'full_oracle': 'MATCHED',
            'persisted_closure': 'MATCHED',
            'pin_lookup_plan': pinPlan
          });
        }
      } finally {
        db.close();
        await bridge.dispose();
        root.deleteSync(recursive: true);
      }
    });
  }

  test('I25 cross-size work bound uses counters, not just elapsed time', () {
    final small = measurements
        .firstWhere((r) => r['history'] == 260 && r['scenario'] == 'mutate');
    final large = measurements
        .firstWhere((r) => r['history'] == 1000 && r['scenario'] == 'mutate');
    final a = small['work'] as Map<String, int>,
        b = large['work'] as Map<String, int>;
    expect(large['objects'] as int, greaterThan(3 * (small['objects'] as int)));
    expect(b['object_reads']!, lessThanOrEqualTo(a['object_reads']! + 32));
    expect(b['index_nodes_examined']!,
        lessThanOrEqualTo(a['index_nodes_examined']! + 16));
    expect(b['full_recoveries'] ?? 0, 0);
    expect(b['full_verifications'] ?? 0, 0);
    expect(b['pin_inserts'], 4);
    expect(a['pin_inserts'], 4);
    expect(b['hot_raw_rows'], a['hot_raw_rows']);
  });

  group('provenance invalidation', () {
    late GenerationFixture fixture, changed;
    late Directory root;
    late SegmentedClientStore db;
    String? fault;
    void Function(String)? hook;
    setUpAll(() async {
      final bridge = await BackendBridge.start(history: 3);
      fixture = GenerationFixture(bridge.fixture);
      changed = await change(bridge, 'mutate');
      await bridge.dispose();
    });
    setUp(() async {
      fault = null;
      hook = null;
      root = Directory.systemTemp.createTempSync('money-note-i25-invalid-');
      db = SegmentedClientStore.open(root, fixture.cache, publication: true,
          fault: (p) {
        hook?.call(p);
        if (p == fault) throw StateError('injected');
      });
      commit(db, await prepare(db, fixture));
    });
    tearDown(() {
      db.close();
      root.deleteSync(recursive: true);
    });

    test('healthy repeated recovery does not scan accepted graph', () async {
      final before = db.work.snapshot();
      for (var i = 0; i < 5; i++) {
        expect((await db.recoverAcceptedGeneration()).sequence, 1);
      }
      expect(db.work.since(before)['full_recoveries'] ?? 0, 0);
      expect(db.work.since(before)['object_reads'] ?? 0, 0);
      inspect(db, fixture);
    });
    test('new handle independently performs full recovery', () async {
      final other =
          SegmentedClientStore.open(root, fixture.cache, publication: true);
      try {
        await other.recoverAcceptedGeneration();
        expect(other.work.snapshot()['full_recoveries'], 1);
        expect(
            other.work.snapshot()['recovery_objects'], fixture.objects.length);
      } finally {
        other.close();
      }
    });
    test(
        'additive v3 migration preserves legacy receipts, full pins and triggers',
        () async {
      final isolated =
          Directory.systemTemp.createTempSync('money-note-i25-v3-');
      var old =
          SegmentedClientStore.open(isolated, fixture.cache, publication: true);
      try {
        final staged =
            await IncrementalFetcher(old, FixtureTransport(fixture)).acquire();
        final expected = old.acceptedGeneration(),
            version = old.publicationDataVersion;
        final proof = await verifyCompleteGeneration(
            staged.manifest, (r) => old.getVerifiedObject(r)!);
        old.commitPreparedGeneration(
            old.prepareGeneration(syncUuid(), staged.stagingId, proof, expected,
                verifiedDataVersion: version),
            finalAuthorityFence: () {});
        final path = old.path;
        old.close();
        final direct = sqlite3.open(path);
        // Only this newly created disposable fixture. Empty additive table;
        // all original v3 generation/pin rows and protective DDL stay intact.
        expect(direct.select('SELECT * FROM generation_roots'), isEmpty);
        final pinned = direct
            .select('SELECT * FROM generation_objects ORDER BY hash')
            .map((r) => Map<String, Object?>.from(r))
            .toList();
        final receipt = (direct
                .select('SELECT receipt FROM generations')
                .single['receipt'] as List<int>)
            .toList();
        final added = direct.select(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name IN ('generation_root_usage','generation_root_release','immutable_generation_root','retained_root_delete','retained_graph_object_delete','retained_graph_edge_delete','immutable_graph_edge')");
        for (final row in added) {
          direct.execute('DROP TRIGGER ${row['name']}');
        }
        direct.execute('DROP TABLE generation_roots');
        direct.execute('PRAGMA user_version=3');
        final originalDDL = direct
            .select('SELECT name,sql FROM sqlite_master WHERE sql IS NOT NULL')
            .map((r) => Map<String, Object?>.from(r))
            .toList();
        direct.close();
        old = SegmentedClientStore.open(isolated, fixture.cache,
            publication: true);
        expect((await old.recoverAcceptedGeneration()).sequence, 1);
        final fresh = sqlite3.open(old.path);
        expect(fresh.select('PRAGMA user_version').single.values.first, 4);
        expect(
            fresh
                .select('SELECT * FROM generation_objects ORDER BY hash')
                .map((r) => Map<String, Object?>.from(r))
                .toList(),
            pinned);
        expect(
            fresh.select('SELECT receipt FROM generations').single['receipt'],
            receipt);
        for (final row in originalDDL) {
          expect(
              fresh.select('SELECT sql FROM sqlite_master WHERE name=?',
                  [row['name']]).single['sql'],
              row['sql']);
        }
        expect(fresh.select('PRAGMA foreign_key_check'), isEmpty);
        fresh.close();
        expect(old.inspectStoreHealth().healthy, isTrue);
      } finally {
        old.close();
        isolated.deleteSync(recursive: true);
      }
    });
    test('external COMMIT forces complete fallback, then session reuses again',
        () async {
      // A real other-connection COMMIT: SQLite may elide a no-op UPDATE and
      // leave data_version unchanged. Persist distinct, valid staging metadata.
      final other =
          SegmentedClientStore.open(root, fixture.cache, publication: true);
      other.createStaging(
          syncUuid(),
          ObservationManifest.fromBytes(encodeC1(fixture.manifest)),
          DateTime.utc(2026, 10, 13));
      other.close();
      final before = db.work.snapshot();
      await db.recoverAcceptedGeneration();
      expect(db.work.since(before)['full_recoveries'], 1);
      await db.recoverAcceptedGeneration();
      expect(db.work.since(before)['full_recoveries'], 1);
      inspect(db, fixture);
    });
    test(
        'root proof from outside owning store cannot manufacture local closure',
        () async {
      final expected = await db.recoverAcceptedGeneration();
      final staged =
          await IncrementalFetcher(db, FixtureTransport(fixture)).acquire();
      final proof = (await verifyCompleteGeneration(
              staged.manifest, (r) => db.getVerifiedObject(r)!,
              base: expected.manifest))
          .withRootAssociation();
      expect(
          () => db.prepareGeneration(
              syncUuid(), staged.stagingId, proof, expected,
              verifiedDataVersion: db.publicationDataVersion),
          throwsA(isA<SegmentedException>().having(
              (e) => e.code, 'code', 'VERIFICATION_CONNECTION_REQUIRED')));
      inspect(db, fixture);
    });
    for (final mismatch in ['dataset_id', 'epoch', 'principal_id', 'sync']) {
      test('$mismatch cannot reuse accepted data provenance', () async {
        final value =
            decodeC1(encodeC1(fixture.manifest)) as Map<String, dynamic>;
        final target = value['target'] as Map<String, dynamic>;
        if (mismatch == 'principal_id') {
          target['principal_id'] = 2;
        } else if (mismatch == 'sync') {
          target['versions']['sync'] = 2;
        } else {
          target['ns'][mismatch] = syncUuid();
        }
        target.remove('sync_root');
        target['sync_root'] = objectHash('view', encodeC1(target));
        final expected = await db.recoverAcceptedGeneration();
        await expectLater(Future(() async {
          final candidate = ObservationManifest.fromBytes(encodeC1(value));
          await db.verifyPublicationCandidate(candidate, expected,
              verifiedDataVersion: db.publicationDataVersion);
        }), throwsA(isA<SegmentedException>()));
        inspect(db, fixture);
      });
    }
    test(
        'competing root-pin publishers cannot overwrite an accepted newer base',
        () async {
      Future<Attempt> competing() async {
        final expected = db.acceptedGeneration();
        final stage = await IncrementalFetcher(db, FixtureTransport(changed))
            .acquire(verifiedBase: expected);
        final version = db.publicationDataVersion;
        final proof = await db.verifyPublicationCandidate(
            stage.manifest, expected,
            verifiedDataVersion: version);
        return Attempt(
            db.prepareGeneration(syncUuid(), stage.stagingId, proof, expected,
                verifiedDataVersion: version),
            proof,
            stage);
      }

      final first = await competing(), second = await competing();
      commit(db, second);
      expect(
          () => db.commitPreparedGeneration(first.prepared,
              finalAuthorityFence: () {}),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'PUBLICATION_CONFLICT')));
      db.discardUnacceptedGeneration(first.prepared.id);
      inspect(db, changed);
    });
    test(
        'newly reachable missing descendant never completes or changes accepted pins',
        () async {
      final hash = changed.objects.entries
          .firstWhere((e) =>
              !fixture.objects.containsKey(e.key) &&
              (decodeC1(e.value) as Map)['kind'] == 'index-leaf')
          .key;
      final bytes = changed.objects.remove(hash)!;
      try {
        await expectLater(
            prepare(db, changed), throwsA(isA<AcquisitionFailure>()));
        inspect(db, fixture);
      } finally {
        changed.objects[hash] = bytes;
      }
    });
    for (final corrupt in [false, true]) {
      test(
          'external post-COMMIT ${corrupt ? "corruption" : "metadata write"} cannot acquire a new provenance stamp',
          () async {
        final a = await prepare(db, changed);
        hook = (point) {
          if (point != 'after_publication_commit') return;
          hook = null;
          if (!corrupt) {
            final other = SegmentedClientStore.open(root, fixture.cache,
                publication: true);
            other.createStaging(
                syncUuid(),
                ObservationManifest.fromBytes(encodeC1(fixture.manifest)),
                DateTime.utc(2026, 10, 13));
            other.close();
          } else {
            final direct = sqlite3.open(db.path);
            final ddl = direct
                .select(
                    "SELECT sql FROM sqlite_master WHERE name='immutable_body'")
                .single['sql'] as String;
            final hash = changed.objects.entries
                .firstWhere((e) =>
                    !fixture.objects.containsKey(e.key) &&
                    (decodeC1(e.value) as Map)['kind'] == 'index-leaf')
                .key;
            direct.execute('DROP TRIGGER immutable_body');
            direct
                .execute("UPDATE objects SET body=x'00' WHERE hash=?", [hash]);
            direct.execute(ddl);
            direct.close();
          }
        };
        expect(
            () => db.commitPreparedGeneration(a.prepared,
                finalAuthorityFence: () {}),
            throwsA(isA<PublicationCommittedException>().having(
                (e) => (e.cause as SegmentedException).code,
                'cause',
                'VERIFICATION_STALE')));
        final direct = sqlite3.open(db.path);
        expect(
            direct.select('SELECT sequence FROM accepted').single['sequence'],
            2);
        direct.close();
        if (corrupt) {
          await expectLater(db.recoverAcceptedGeneration(),
              throwsA(isA<SegmentedException>()));
        } else {
          final before = db.work.snapshot();
          await db.recoverAcceptedGeneration();
          expect(db.work.since(before)['full_recoveries'], 1);
          inspect(db, changed);
        }
      });
    }
    for (final point in [
      'before_publication_commit',
      'after_publication_commit',
      'during_publication_readback'
    ]) {
      test('$point failure invalidates session; retry recovers complete state',
          () async {
        final a = await prepare(db, fixture);
        fault = point;
        expect(
            () => db.commitPreparedGeneration(a.prepared,
                finalAuthorityFence: () {}),
            throwsA(point == 'before_publication_commit'
                ? isA<StateError>()
                : isA<PublicationCommittedException>()));
        fault = null;
        final before = db.work.snapshot();
        await db.recoverAcceptedGeneration();
        expect(db.work.since(before)['full_recoveries'], 1);
        inspect(db, fixture);
      });
    }
    for (final trigger in [
      'immutable_generation_root',
      'retained_graph_object_delete',
      'retained_graph_edge_delete',
      'immutable_graph_edge',
      'retained_root_delete'
    ]) {
      test('missing $trigger invalidates provenance before new writes',
          () async {
        final direct = sqlite3.open(db.path);
        final count =
            direct.select('SELECT count(*) AS n FROM objects').single['n'];
        direct.execute('DROP TRIGGER $trigger');
        direct.close();
        await expectLater(
            db.recoverAcceptedGeneration(), throwsA(isA<SegmentedException>()));
        final fresh = sqlite3.open(db.path);
        expect(fresh.select('SELECT count(*) AS n FROM objects').single['n'],
            count);
        expect(fresh.select('SELECT sequence FROM accepted').single['sequence'],
            1);
        fresh.close();
      });
    }
    for (final damage in ['receipt', 'object', 'profile', 'pin']) {
      test('external $damage corruption cannot reuse accepted provenance',
          () async {
        final direct = sqlite3.open(db.path);
        if (damage == 'profile') {
          direct.execute("UPDATE profile SET namespace='invalid'");
        } else if (damage == 'receipt' || damage == 'object') {
          final trigger =
              damage == 'receipt' ? 'immutable_generation' : 'immutable_body';
          final ddl = direct.select(
              'SELECT sql FROM sqlite_master WHERE name=?',
              [trigger]).single['sql'] as String;
          direct.execute('DROP TRIGGER $trigger');
          direct.execute(
              damage == 'receipt'
                  ? "UPDATE generations SET receipt=x'00'"
                  : "UPDATE objects SET body=x'00' WHERE hash=?",
              damage == 'receipt'
                  ? []
                  : [
                      fixture.objects.entries
                          .firstWhere((e) =>
                              (decodeC1(e.value) as Map)['kind'] ==
                              'index-leaf')
                          .key
                    ]);
          direct.execute(ddl);
        } else {
          final ddl = direct
              .select(
                  "SELECT sql FROM sqlite_master WHERE name='retained_root_delete'")
              .single['sql'] as String;
          direct.execute('DROP TRIGGER retained_root_delete');
          direct.execute('DELETE FROM generation_roots WHERE hash=?',
              [fixture.target.roots['raw']!.hash]);
          direct.execute(ddl);
        }
        direct.close();
        await expectLater(
            db.recoverAcceptedGeneration(), throwsA(isA<SegmentedException>()));
        final fresh = sqlite3.open(db.path);
        expect(fresh.select('SELECT sequence FROM accepted').single['sequence'],
            1);
        fresh.close();
      });
    }
    test(
        'retained descendants and edges cannot be removed; staging cleanup safe',
        () async {
      for (final stage in db.listStagingIdentities()) {
        db.removeUnreferencedStagingData(stage);
      }
      final direct = sqlite3.open(db.path);
      try {
        for (final hash in fixture.objects.keys) {
          expect(
              () => direct.execute('DELETE FROM objects WHERE hash=?', [hash]),
              throwsA(isA<SqliteException>()));
        }
        expect(() => direct.execute('DELETE FROM edges'),
            throwsA(isA<SqliteException>()));
        expect(() => direct.execute('DELETE FROM generation_roots'),
            throwsA(isA<SqliteException>()));
      } finally {
        direct.close();
      }
      inspect(db, fixture);
    });
  });
}
