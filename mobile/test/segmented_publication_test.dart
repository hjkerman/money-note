@Timeout(Duration(minutes: 3))
library;

import 'dart:async';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/verification.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';

void main() {
  late GenerationFixture fixture;
  late Directory root;
  SegmentedClientStore? store;
  setUpAll(() async {
    final server = await BackendBridge.start(history: 3);
    fixture = GenerationFixture(server.fixture);
    await server.dispose();
  });
  setUp(() => root = Directory.systemTemp.createTempSync('money-note-e3-'));
  tearDown(() {
    store?.close();
    store = null;
    root.deleteSync(recursive: true);
  });
  SegmentedClientStore open(
          {StoreFault? fault,
          ClientStoreLimits limits = const ClientStoreLimits()}) =>
      store = SegmentedClientStore.open(root, fixture.cache,
          publication: true, fault: fault, limits: limits);
  Future<(PreparedGeneration, CompleteGenerationProof)> prepare(
      SegmentedClientStore db,
      {GenerationFixture? input}) async {
    final expected = db.acceptedGeneration();
    final acquired =
        await IncrementalFetcher(db, FixtureTransport(input ?? fixture))
            .acquire();
    final version = db.publicationDataVersion;
    final proof = await verifyCompleteGeneration(acquired.manifest,
        (ref) => db.getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING')),
        base: expected.manifest);
    return (
      db.prepareGeneration(syncUuid(), acquired.stagingId, proof, expected,
          verifiedDataVersion: version),
      proof
    );
  }

  void inspect(SegmentedClientStore db, int sequence, {String? target}) {
    final direct = sqlite3.open(db.path);
    try {
      final accepted = direct.select('SELECT * FROM accepted').single;
      expect(accepted['sequence'], sequence);
      expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
      expect(direct.select('PRAGMA integrity_check').single.values.first, 'ok');
      if (sequence != 0) {
        final generation = direct.select('SELECT * FROM generations WHERE id=?',
            [accepted['current_id']]).single;
        final receipt = decodeC1(generation['receipt'] as List<int>) as Map;
        expect(receipt['validator'], CompleteGenerationProof.validator);
        expect(
            receipt['target']['sync_root'], target ?? fixture.target.syncRoot);
        final pins = direct.select(
            'SELECT hash FROM generation_objects WHERE generation_id=?',
            [accepted['current_id']]);
        expect(pins.length, generation['object_count']);
        expect(pins.map((r) => r['hash']).toSet(),
            containsAll(fixture.target.roots.values.map((r) => r.hash)));
      }
    } finally {
      direct.close();
    }
  }

  test(
      'server F(raw) independent canonical root; eleven tables; first publication',
      () async {
    final db = open(), item = await prepare(db);
    expect(item.$2.graph.tableRows.length, 11);
    expect(item.$2.difference.changes.length,
        fixture.source.values.fold<int>(0, (n, v) => n + (v as List).length));
    var called = 0;
    final result =
        db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {
      called++;
    });
    expect(called, 1);
    expect(result.sequence, 1);
    inspect(db, 1);
    expect(db.inspectStoreHealth().healthy, isTrue);
  });

  test('same Target publication idempotence and unchanged-subtree reuse',
      () async {
    final db = open(), first = await prepare(db);
    final accepted =
        db.commitPreparedGeneration(first.$1, finalAuthorityFence: () {});
    final next = await prepare(db);
    expect(next.$2.difference.changes, isEmpty);
    expect(next.$2.difference.reusedSubtrees, 11);
    final same =
        db.commitPreparedGeneration(next.$1, finalAuthorityFence: () {});
    expect(same.idempotent, isTrue);
    expect(same.generationId, accepted.generationId);
    expect(db.discardUnacceptedGeneration(next.$1.id), isTrue);
    inspect(db, 1);
  });

  test('competing publishers use expected base AND durable sequence', () async {
    final db = open(), a = await prepare(db), b = await prepare(db);
    db.commitPreparedGeneration(a.$1, finalAuthorityFence: () {});
    expect(
        () => db.commitPreparedGeneration(b.$1, finalAuthorityFence: () {}),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'PUBLICATION_CONFLICT')));
    expect(db.discardUnacceptedGeneration(b.$1.id), isTrue);
    inspect(db, 1);
  });

  test('async void guard cannot bypass the synchronous publication fence',
      () async {
    final db = open(), item = await prepare(db);
    expect(
        () => db.commitPreparedGeneration(item.$1,
            finalAuthorityFence: () async {}),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'ASYNC_PUBLICATION_FENCE')));
    inspect(db, 0);
  });

  for (final point in [
    'after_publication_begin',
    'after_accepted_pointer',
    'before_publication_commit'
  ]) {
    test('rollback at $point leaves no partial accepted publication', () async {
      var inject = false;
      final db = open(fault: (p) {
        if (inject && p == point) throw const SegmentedException('INJECTED');
      });
      final item = await prepare(db);
      inject = true;
      expect(
          () =>
              db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {}),
          throwsA(isA<SegmentedException>()));
      inspect(db, 0);
      expect(db.discardUnacceptedGeneration(item.$1.id), isTrue);
      final direct = sqlite3.open(db.path);
      expect(direct.select('SELECT * FROM generation_objects'), isEmpty);
      direct.close();
    });
  }
  test(
      'final fence AFTER mutating hook and immediately before synchronous commit',
      () async {
    var current = true, mutate = false;
    final events = <String>[];
    final db = open(fault: (p) {
      if (mutate && p == 'before_publication_commit') {
        events.add('hook');
        current = false;
      }
    });
    final item = await prepare(db);
    mutate = true;
    expect(
        () => db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {
              events.add('guard');
              if (!current) throw const SegmentedException('STALE');
            }),
        throwsA(isA<SegmentedException>()));
    expect(events, ['hook', 'guard']);
    inspect(db, 0);
  });
  test(
      'microtask scheduled at final guard cannot interleave before COMMIT/readback',
      () async {
    final db = open(), item = await prepare(db);
    var eventRan = false;
    final r = db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {
      scheduleMicrotask(() {
        eventRan = true;
      });
    });
    expect(eventRan, isFalse);
    expect(r.sequence, 1);
    inspect(db, 1);
    await Future<void>.value();
    expect(eventRan, isTrue);
  });
  for (final point in [
    'after_publication_commit',
    'during_publication_readback'
  ]) {
    test('post-COMMIT $point reports committed failure, never rollback',
        () async {
      var inject = false;
      final db = open(fault: (p) {
        if (inject && p == point) throw StateError('test failure');
      });
      final item = await prepare(db);
      inject = true;
      expect(
          () =>
              db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {}),
          throwsA(isA<PublicationCommittedException>()));
      inspect(db, 1);
      expect(db.discardUnacceptedGeneration(item.$1.id), isFalse);
    });
  }
  test('staging cleanup preserves accepted graph and pins; reopen recovers',
      () async {
    var db = open();
    final item = await prepare(db);
    db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {});
    for (final id in db.listStagingIdentities()) {
      db.removeUnreferencedStagingData(id);
    }
    final direct = sqlite3.open(db.path);
    expect(() => direct.execute('DELETE FROM objects'),
        throwsA(isA<SqliteException>()));
    expect(() => direct.execute('DELETE FROM generation_objects'),
        throwsA(isA<SqliteException>()));
    direct.close();
    db.close();
    db = open();
    final accepted = await db.recoverAcceptedGeneration();
    expect(accepted.sequence, 1);
    inspect(db, 1);
  });
  test('unaccepted prepared pins after interruption reclaimed on recovery',
      () async {
    var db = open();
    await prepare(db);
    db.close();
    db = open();
    expect((await db.recoverAcceptedGeneration()).id, isNull);
    final direct = sqlite3.open(db.path);
    expect(direct.select('SELECT * FROM generations'), isEmpty);
    expect(direct.select('SELECT * FROM generation_objects'), isEmpty);
    direct.close();
  });
  test('SQLITE_BUSY before BEGIN preserves base; no final fence run', () async {
    final db = open(limits: const ClientStoreLimits(busyMilliseconds: 1)),
        item = await prepare(db);
    final direct = sqlite3.open(db.path);
    direct.execute('BEGIN IMMEDIATE');
    var calls = 0;
    expect(
        () => db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {
              calls++;
            }),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'STORE_BUSY')));
    direct.execute('ROLLBACK');
    direct.close();
    expect(calls, 0);
    inspect(db, 0);
  });
  for (final trigger in [
    'generation_usage',
    'immutable_generation',
    'retained_pin_delete',
    'retained_object_delete'
  ]) {
    test('missing E3 integrity trigger $trigger blocks publication', () async {
      final db = open(), item = await prepare(db);
      final direct = sqlite3.open(db.path);
      direct.execute('DROP TRIGGER $trigger');
      direct.close();
      expect(
          () =>
              db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {}),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'STORE_SCHEMA_CORRUPT')));
      inspect(db, 0);
    });
  }
  for (final kind in ['index-leaf', 'hot']) {
    test('hash-valid $kind disagreement rejected independently of E2 closure',
        () async {
      final negative = mutateGraph(fixture, kind, (body) {
        if (kind == 'index-leaf') {
          body['facts'][0]['value'] = 'wrong structural value';
        } else {
          body['state']['settings']['scheduled_income'] = '123';
        }
      });
      final db = open();
      final acquired =
          await IncrementalFetcher(db, FixtureTransport(negative)).acquire();
      expect(
          db.acquisitionProgress(acquired.stagingId)!.state, 'graph_verified');
      await expectLater(
          verifyCompleteGeneration(
              acquired.manifest, (ref) => db.getVerifiedObject(ref)!),
          throwsA(isA<SegmentedException>()));
      inspect(db, 0);
    });
  }
  test('graph_verified flag alone cannot produce CompleteGenerationProof',
      () async {
    final db = open(),
        acquired =
            await IncrementalFetcher(db, FixtureTransport(fixture)).acquire();
    final leaf = fixture.objects.entries.firstWhere(
        (e) => (decodeC1(e.value) as Map)['kind'] == 'snapshot-leaf');
    final direct = sqlite3.open(db.path);
    direct.execute('DELETE FROM staging_objects WHERE hash=?', [leaf.key]);
    direct.execute('DELETE FROM edges WHERE parent=?', [leaf.key]);
    direct.execute('DELETE FROM objects WHERE hash=?', [leaf.key]);
    direct.close();
    expect(db.acquisitionProgress(acquired.stagingId)!.state, 'graph_verified');
    await expectLater(
        verifyCompleteGeneration(
            acquired.manifest,
            (ref) =>
                db.getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING'))),
        throwsA(isA<SegmentedException>()));
    inspect(db, 0);
  });

  test(
      'another connection COMMIT between verification and prepare rejects stale proof',
      () async {
    final db = open(),
        acquired =
            await IncrementalFetcher(db, FixtureTransport(fixture)).acquire();
    final version = db.publicationDataVersion;
    final proof = await verifyCompleteGeneration(
        acquired.manifest, (ref) => db.getVerifiedObject(ref)!);
    final direct = sqlite3.open(db.path);
    direct.execute('INSERT INTO refs VALUES(?,?)', ['a' * 64, '1']);
    direct.close();
    expect(
        () => db.prepareGeneration(
            syncUuid(), acquired.stagingId, proof, db.acceptedGeneration(),
            verifiedDataVersion: version),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'VERIFICATION_STALE')));
    inspect(db, 0);
  });
  test('another connection COMMIT after prepare rejects stale publication',
      () async {
    final db = open(), item = await prepare(db);
    final direct = sqlite3.open(db.path);
    direct.execute('INSERT INTO refs VALUES(?,?)', ['b' * 64, '1']);
    direct.close();
    expect(
        () => db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {}),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'VERIFICATION_STALE')));
    inspect(db, 0);
  });
  test('prepared evidence cannot be reused on another connection after restart',
      () async {
    var db = open();
    final item = await prepare(db);
    db.close();
    db = open();
    expect(
        () => db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {}),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'PREPARATION_CONNECTION_CHANGED')));
    inspect(db, 0);
  });
  test('SQLITE_BUSY at COMMIT rolls back pointer after final fence', () async {
    final db = open(limits: const ClientStoreLimits(busyMilliseconds: 1)),
        item = await prepare(db);
    final reader = sqlite3.open(db.path);
    reader.execute('BEGIN');
    reader.select('SELECT * FROM accepted');
    var guarded = false;
    expect(
        () => db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {
              guarded = true;
            }),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'STORE_BUSY')));
    expect(guarded, isTrue);
    reader.execute('ROLLBACK');
    reader.close();
    inspect(db, 0);
  });
  test(
      'rollback failure on closed native connection never masks original failure',
      () async {
    final db = open(), item = await prepare(db);
    expect(
        () => db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {
              db.close();
              throw const SegmentedException('ORIGINAL_FENCE_FAILURE');
            }),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'ORIGINAL_FENCE_FAILURE')));
    inspect(db, 0);
  });
  test('accepted pointer checksum corruption fails closed on fresh recovery',
      () async {
    var db = open();
    final item = await prepare(db);
    db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {});
    final direct = sqlite3.open(db.path);
    direct.execute("UPDATE accepted SET checksum='corrupt'");
    direct.close();
    db.close();
    db = open();
    await expectLater(
        db.recoverAcceptedGeneration(),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'ACCEPTED_METADATA_INVALID')));
  });
  for (final field in ['edges', 'facts', 'object_set', 'base_sync_root']) {
    test('fresh recovery independently rejects inconsistent receipt $field',
        () async {
      var db = open();
      final item = await prepare(db);
      db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {});
      final direct = sqlite3.open(db.path);
      final sql = direct
          .select(
              "SELECT sql FROM sqlite_master WHERE name='immutable_generation'")
          .single['sql'] as String;
      final original = direct
          .select('SELECT receipt FROM generations')
          .single['receipt'] as List<int>;
      final receipt = decodeC1(original) as Map<String, dynamic>;
      receipt[field] = field == 'edges'
          ? (receipt[field] as int) + 1
          : field == 'facts'
              ? '${BigInt.parse(receipt[field] as String) + BigInt.one}'
              : 'f' * 64;
      final bytes = encodeC1(receipt);
      // Synthetic corruption with the original trigger restored: neither an
      // exception alone nor a self-reported health flag is the oracle.
      direct.execute('DROP TRIGGER immutable_generation');
      direct.execute('UPDATE generations SET receipt=?,receipt_checksum=?',
          [bytes, localChecksum(bytes)]);
      direct.execute('UPDATE usage SET metadata=metadata+?',
          [bytes.length - original.length]);
      direct.execute(sql);
      direct.close();
      db.close();
      db = open();
      await expectLater(
          db.recoverAcceptedGeneration(), throwsA(isA<SegmentedException>()));
      final persisted = sqlite3.open(db.path);
      expect(
          persisted.select('SELECT sequence FROM accepted').single['sequence'],
          1);
      expect(persisted.select('SELECT count(*) AS n FROM objects').single['n'],
          item.$2.graph.objects.length);
      expect(persisted.select('PRAGMA foreign_key_check'), isEmpty);
      persisted.close();
    });
  }
  test('index transition old membership cannot be truncated by a diff budget',
      () async {
    final db = open(), item = await prepare(db);
    expect(
        () => diffRawTrees(
            null, item.$2.manifest.target, (ref) => db.getVerifiedObject(ref)!,
            maxChanges: 0),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'DIFF_BUDGET')));
    inspect(db, 0);
  });
  test(
      'real SQLITE_FULL preparing metadata preserves the previous accepted generation',
      () async {
    var db = open();
    final item = await prepare(db);
    db.commitPreparedGeneration(item.$1, finalAuthorityFence: () {});
    final stage = db.listStagingIdentities().single;
    final direct = sqlite3.open(db.path),
        pages = direct.select('PRAGMA page_count').single.values.first as int;
    direct.close();
    db.close();
    db = open(limits: ClientStoreLimits(databasePages: pages));
    final expected = db.acceptedGeneration(),
        version = db.publicationDataVersion;
    final proof = await verifyCompleteGeneration(
        db.loadStaging(stage)!.manifest, (ref) => db.getVerifiedObject(ref)!,
        base: expected.manifest);
    SegmentedException? failed;
    for (var i = 0; i < 16; i++) {
      try {
        db.prepareGeneration(syncUuid(), stage, proof, expected,
            verifiedDataVersion: version);
      } on SegmentedException catch (e) {
        failed = e;
        break;
      }
    }
    expect(failed, isNotNull);
    expect(failed!.storageCode, 13);
    inspect(db, 1);
    expect((await db.recoverAcceptedGeneration()).sequence, 1);
  });

  for (final point in [
    'before_generation_prepare',
    'after_generation_manifest',
    'after_generation_pins'
  ]) {
    test('preparation failure $point rolls back all receipt and pin rows',
        () async {
      final db = open(fault: (p) {
        if (p == point) throw const SegmentedException('PREPARE_FAILURE');
      });
      await expectLater(
          prepare(db),
          throwsA(isA<SegmentedException>()
              .having((e) => e.code, 'code', 'PREPARE_FAILURE')));
      final direct = sqlite3.open(db.path);
      expect(direct.select('SELECT * FROM generations'), isEmpty);
      expect(direct.select('SELECT * FROM generation_objects'), isEmpty);
      direct.close();
      inspect(db, 0);
    });
  }
}
