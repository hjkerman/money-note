import 'dart:convert';
import 'dart:io';
import 'dart:isolate';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/offline_mode_fixtures.dart';
import 'support/segmented_fixture.dart';

void main() {
  final golden = ServerGolden();
  late Directory root;
  SegmentedClientStore? store;
  setUp(() {
    root = Directory.systemTemp.createTempSync('money-note-e1-');
  });
  tearDown(() {
    store?.close();
    store = null;
    root.deleteSync(recursive: true);
  });
  SegmentedClientStore open(
          {ClientStoreLimits limits = const ClientStoreLimits(),
          StoreFault? fault}) =>
      store = SegmentedClientStore.open(root, golden.cache,
          limits: limits, fault: fault);
  Database inspect(String path) => sqlite3.open(path);

  test('all server kinds persist exact bytes after restart', () {
    final db = open();
    for (final item in golden.objects) {
      final kind = item['kind'] as String;
      db.putVerifiedObject(golden.ref(kind), golden.bytes(kind));
    }
    final path = db.path;
    db.close();
    final direct = inspect(path);
    expect(direct.select('PRAGMA user_version').single.values.first, 1);
    expect(direct.select('SELECT count(*) AS n FROM objects').single['n'],
        golden.objects.length);
    for (final item in golden.objects) {
      final kind = item['kind'] as String;
      expect(
          direct.select('SELECT body FROM objects WHERE hash=?',
              [golden.ref(kind).hash]).single['body'],
          golden.bytes(kind));
    }
    direct.close();
    final recovered = open();
    for (final item in golden.objects) {
      final kind = item['kind'] as String;
      expect(recovered.getVerifiedObject(golden.ref(kind))!.bytes,
          golden.bytes(kind));
    }
    expect(recovered.inspectStoreHealth().healthy, isTrue);
  });
  test('duplicate writes idempotent, no overwritten object or edge counts', () {
    final db = open();
    for (var i = 0; i < 5; i++) {
      db.putVerifiedObject(golden.ref('raw-root'), golden.bytes('raw-root'));
    }
    final direct = inspect(db.path);
    expect(direct.select('SELECT objects FROM usage').single['objects'], 1);
    expect(direct.select('SELECT count(*) AS n FROM edges').single['n'], 11);
    expect(() => direct.execute('UPDATE objects SET body=?', [Uint8List(1)]),
        throwsA(isA<SqliteException>()));
    direct.close();
  });
  test('conflicting bytes and truncated payload rejected, good data preserved',
      () {
    final db = open(), ref = golden.ref('raw-root');
    db.putVerifiedObject(ref, golden.bytes('raw-root'));
    final changed = golden.bytes('raw-root')..[0] = 0;
    expect(() => db.putVerifiedObject(ref, changed),
        throwsA(isA<SegmentedException>()));
    expect(() => db.putVerifiedObject(ref, golden.bytes('raw-root').sublist(1)),
        throwsA(isA<SegmentedException>()));
    expect(db.getVerifiedObject(ref)!.bytes, golden.bytes('raw-root'));
  });
  for (final corruption in [
    'body',
    'kind',
    'validator',
    'edge',
    'missing_payload'
  ]) {
    test('persisted corruption $corruption fails closed after reopening', () {
      final db = open();
      final ref = golden.ref('raw-root');
      db.putVerifiedObject(ref, golden.bytes('raw-root'));
      final path = db.path;
      db.close();
      final direct = inspect(path);
      direct.execute('DROP TRIGGER immutable_body');
      switch (corruption) {
        case 'body':
          direct.execute('UPDATE objects SET body=?', [
            Uint8List.fromList([123, 125])
          ]);
        case 'kind':
          direct.execute("UPDATE objects SET kind='hot'");
        case 'validator':
          direct.execute("UPDATE objects SET validator='unreviewed'");
        case 'edge':
          direct.execute('DELETE FROM edges WHERE position=0');
        case 'missing_payload':
          direct.execute('DELETE FROM objects');
      }
      direct.close();
      if (['missing_payload', 'body', 'edge'].contains(corruption)) {
        expect(() => open(), throwsA(isA<SegmentedException>()));
        return;
      }
      final recovered = open();
      if (corruption == 'missing_payload') {
        expect(recovered.getVerifiedObject(ref), isNull);
      } else {
        expect(() => recovered.getVerifiedObject(ref),
            throwsA(isA<SegmentedException>()));
        expect(recovered.inspectStoreHealth().healthy, isFalse);
      }
    });
  }
  test('staging progress survives restart but is never accepted/active', () {
    final db = open(), ref = golden.ref('raw-root');
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026, 10, 5));
    expect(() => db.recordStagedObject(stageId, ref),
        throwsA(isA<SegmentedException>()));
    db.putVerifiedObject(ref, golden.bytes('raw-root'));
    db.recordStagedObject(stageId, ref);
    db.close();
    final recovered = open(), stage = recovered.loadStaging(stageId)!;
    expect(stage.objectCount, 1);
    expect(stage.validationState, 'staged');
    expect(stage.manifest.bytes, golden.manifest.bytes);
    final direct = inspect(recovered.path);
    expect(
        direct.select('SELECT count(*) AS n FROM staging_objects').single['n'],
        1);
    expect(
        direct.select(
            "SELECT name FROM sqlite_master WHERE name IN ('accepted','active','generations')"),
        isEmpty);
    // Four expected roots, not a complete graph and not the internal proof root.
    expect(
        direct
            .select('SELECT role FROM staging_roots')
            .map((r) => r['role'])
            .toSet(),
        {'raw', 'index', 'hot', 'control'});
    direct.close();
  });
  test('same local staging ID cannot bind a different manifest', () {
    final db = open();
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026));
    final wire = decodeC1(golden.manifest.bytes) as Map<String, dynamic>;
    wire['request_id'] = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    expect(
        () => db.createStaging(stageId,
            ObservationManifest.fromBytes(encodeC1(wire)), DateTime.utc(2026)),
        throwsA(isA<SegmentedException>()));
    expect(
        db.loadStaging(stageId)!.manifest.requestId, golden.manifest.requestId);
  });
  test('staging identities recover through bounded payload-free pages', () {
    final db = open();
    const second = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    for (final id in [stageId, second]) {
      db.createStaging(id, golden.manifest, DateTime.utc(2026));
    }
    db.close();
    final recovered = open();
    final expected = [stageId, second]..sort();
    final first = recovered.listStagingIdentities(limit: 1);
    expect(first, [expected.first]);
    expect(recovered.listStagingIdentities(afterId: first.single, limit: 1),
        [expected.last]);
    expect(recovered.listStagingIdentities(afterId: expected.last), isEmpty);
    expect(() => recovered.listStagingIdentities(limit: 1025),
        throwsA(isA<SegmentedException>()));
  });
  test('startup rejects corrupted persisted usage counters', () {
    final db = open();
    db.putVerifiedObject(golden.ref('raw-root'), golden.bytes('raw-root'));
    final path = db.path;
    db.close();
    final direct = inspect(path);
    direct.execute('UPDATE usage SET objects=0,payload=0,metadata=0');
    direct.close();
    expect(() => open(), throwsA(isA<SegmentedException>()));
    final fresh = inspect(path);
    expect(fresh.select('SELECT body FROM objects').single['body'],
        golden.bytes('raw-root'));
    fresh.close();
  });
  test('staging corruption detected rather than activated or sanitized', () {
    final db = open();
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026));
    final direct = inspect(db.path);
    direct.execute('UPDATE staging SET manifest=?', [Uint8List(2)]);
    direct.close();
    expect(() => db.loadStaging(stageId), throwsA(isA<SegmentedException>()));
    expect(db.inspectStoreHealth().healthy, isFalse);
  });
  for (final point in [
    'before_object_insert',
    'after_object_insert',
    'after_edges_insert',
    'before_commit'
  ]) {
    test('object failure $point atomically rolls back payload receipt edges',
        () {
      final db = open(fault: (p) {
        if (p == point) {
          throw StateError('synthetic interruption');
        }
      });
      expect(
          () => db.putVerifiedObject(
              golden.ref('raw-root'), golden.bytes('raw-root')),
          throwsStateError);
      final direct = inspect(db.path);
      expect(direct.select('SELECT * FROM objects'), isEmpty);
      expect(direct.select('SELECT * FROM refs'), isEmpty);
      expect(direct.select('SELECT * FROM edges'), isEmpty);
      expect(
          direct
              .select('SELECT objects,payload,metadata FROM usage')
              .single
              .values,
          [0, 0, 0]);
      direct.execute('BEGIN IMMEDIATE');
      direct.execute('ROLLBACK');
      direct.close();
    });
  }
  for (final point in ['after_staging_insert', 'after_progress_insert']) {
    test('metadata failure $point retains previous good data', () {
      var enabled = false;
      final db = open(fault: (p) {
        if (enabled && p == point) {
          throw StateError('synthetic interruption');
        }
      });
      final ref = golden.ref('raw-root');
      db.putVerifiedObject(ref, golden.bytes('raw-root'));
      if (point == 'after_progress_insert') {
        db.createStaging(stageId, golden.manifest, DateTime.utc(2026));
      }
      enabled = true;
      expect(() {
        if (point == 'after_staging_insert') {
          db.createStaging(stageId, golden.manifest, DateTime.utc(2026));
        } else {
          db.recordStagedObject(stageId, ref);
        }
      }, throwsStateError);
      expect(db.getVerifiedObject(ref), isNotNull);
      final direct = inspect(db.path);
      expect(direct.select('SELECT * FROM staging_objects'), isEmpty);
      expect(direct.select('SELECT * FROM staging').length,
          point == 'after_staging_insert' ? 0 : 1);
      direct.close();
    });
  }
  test('lost result after COMMIT is recovered by idempotent retry', () {
    var once = true;
    final db = open(fault: (p) {
      if (p == 'after_commit' && once) {
        once = false;
        throw StateError('lost result');
      }
    });
    final ref = golden.ref('raw-root');
    expect(() => db.putVerifiedObject(ref, golden.bytes('raw-root')),
        throwsStateError);
    db.close();
    expect(open().putVerifiedObject(ref, golden.bytes('raw-root')).bytes,
        golden.bytes('raw-root'));
  });
  test('write error SQLITE_FULL injection retains committed good data', () {
    var full = false;
    final db = open(fault: (p) {
      if (full && p == 'after_object_insert') {
        throw SqliteException(
            extendedResultCode: 13, message: 'synthetic disk full');
      }
    });
    final ref = golden.ref('raw-root');
    db.putVerifiedObject(ref, golden.bytes('raw-root'));
    full = true;
    expect(() => db.putVerifiedObject(golden.ref('hot'), golden.bytes('hot')),
        throwsA(isA<SegmentedException>()));
    expect(db.getVerifiedObject(ref), isNotNull);
    expect(db.getVerifiedObject(golden.ref('hot')), isNull);
    final direct = inspect(db.path);
    direct.execute('BEGIN IMMEDIATE');
    direct.execute('ROLLBACK');
    direct.close();
  });
  test('real SQLite page limit returns FULL without committing partial object',
      () {
    final db = open(limits: const ClientStoreLimits(databasePages: 64));
    final safe = golden.ref('index-empty');
    db.putVerifiedObject(safe, golden.bytes('index-empty'));
    final body = golden.body('snapshot-leaf');
    body['table'] = 'app_labels';
    body['min'] = ['t', 'x'];
    body['max'] = ['t', 'x'];
    body['oversized'] = true;
    body['rows'] = [
      {
        'key': ['t', 'x'],
        'value': {'key': 'x', 'value': 'a' * 400000, 'updated_at': 'synthetic'}
      }
    ];
    final raw = encodeC1(body), ref = refFor('snapshot-leaf', encodeC1(body));
    expect(
        () => db.putVerifiedObject(ref, raw),
        throwsA(isA<SegmentedException>()
            .having((e) => e.storageCode, 'SQLITE_FULL', 13)));
    expect(db.getVerifiedObject(safe), isNotNull);
    expect(db.getVerifiedObject(ref), isNull);
    final direct = inspect(db.path);
    expect(direct.select('SELECT objects FROM usage').single['objects'], 1);
    expect(direct.select('PRAGMA integrity_check').single.values.first, 'ok');
    direct.execute('BEGIN IMMEDIATE');
    direct.execute('ROLLBACK');
    direct.close();
  });
  test('local cleanup never trusts unrelated temporary files', () {
    final db = open(), ref = golden.ref('raw-root');
    final partial = File('${File(db.path).parent.path}/${ref.hash}.part');
    partial.writeAsBytesSync(golden.bytes('raw-root').sublist(0, 10),
        flush: true);
    db.close();
    final recovered = open();
    expect(recovered.containsVerifiedObject(ref), isFalse);
    expect(recovered.listStoredObjectIdentities(), isEmpty);
    expect(recovered.inspectStoreHealth().healthy, isTrue);
    // E1 writes no loose files; unknown files are not ingested or deleted.
    expect(partial.readAsBytesSync().length, 10);
  });
  test('local budgets and staging cleanup recover metadata without object GC',
      () {
    final db = open(limits: const ClientStoreLimits(stagingCount: 1));
    final ref = golden.ref('raw-root');
    db.putVerifiedObject(ref, golden.bytes('raw-root'));
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026));
    db.recordStagedObject(stageId, ref);
    const other = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
    expect(() => db.createStaging(other, golden.manifest, DateTime.utc(2026)),
        throwsA(isA<SegmentedException>()));
    expect(db.removeUnreferencedStagingData(stageId), isTrue);
    expect(db.removeUnreferencedStagingData(stageId), isFalse);
    db.createStaging(other, golden.manifest, DateTime.utc(2026));
    expect(db.getVerifiedObject(ref), isNotNull);
  });
  test('object count and metadata budgets do not damage previous data', () {
    final db = open(limits: const ClientStoreLimits(objectCount: 1));
    db.putVerifiedObject(
        golden.ref('index-empty'), golden.bytes('index-empty'));
    expect(() => db.putVerifiedObject(golden.ref('hot'), golden.bytes('hot')),
        throwsA(isA<SegmentedException>()));
    expect(db.listStoredObjectIdentities().length, 1);
    db.close();
    final limited = open(
        limits:
            const ClientStoreLimits(manifestBytes: 128, metadataBytes: 1024));
    expect(
        () =>
            limited.createStaging(stageId, golden.manifest, DateTime.utc(2026)),
        throwsA(isA<SegmentedException>()));
    expect(limited.getVerifiedObject(golden.ref('index-empty')), isNotNull);
  });
  test('enumeration is keyset paged and missing placeholders are excluded', () {
    final db = open();
    db.putVerifiedObject(golden.ref('raw-root'), golden.bytes('raw-root'));
    db.putVerifiedObject(golden.ref('hot'), golden.bytes('hot'));
    final first = db.listStoredObjectIdentities(limit: 1);
    final second =
        db.listStoredObjectIdentities(limit: 1, afterHash: first.single.hash);
    expect(second.single.hash, isNot(first.single.hash));
    expect(
        db.listStoredObjectIdentities(afterHash: second.single.hash), isEmpty);
    expect(() => db.listStoredObjectIdentities(limit: 1025),
        throwsA(isA<SegmentedException>()));
  });
  test('independent isolates identical/conflicting writes remain atomic',
      () async {
    final db = open();
    final path = root.path,
        fixture =
            File('test/fixtures/segmented_server_golden.json').absolute.path;
    final results = await Future.wait(
        List.generate(8, (i) => concurrentPut(path, fixture, i)));
    expect(results.where((r) => r == 'stored').length, 4,
        reason: results.toString());
    expect(results.where((r) => r.startsWith('rejected:')).length, 4);
    expect(db.listStoredObjectIdentities().length, 1);
    expect(db.inspectStoreHealth().healthy, isTrue);
  });
  test('unsupported storage schema/profile never upgraded silently', () {
    final db = open(), path = db.path;
    db.close();
    final direct = inspect(path);
    direct.execute('PRAGMA user_version=99');
    direct.close();
    expect(() => open(), throwsA(isA<SegmentedException>()));
    final again = inspect(path);
    expect(again.select('PRAGMA user_version').single.values.first, 99);
    again.close();
  });
  test('normal OfflineBaseline v4 B/J Snapshot files unchanged', () async {
    final offline = OfflineStore(directoryProvider: () async => root);
    await offline.replaceBaseline(baselineFixture());
    final snapshots =
        LocalSnapshotRepository(directoryProvider: () async => root);
    final snapshot =
        File('test/fixtures/valid_snapshot.json').readAsBytesSync();
    await snapshots.save(snapshot);
    final original = {
      for (final f in root.listSync(recursive: true).whereType<File>())
        f.path: f.readAsBytesSync()
    };
    final db = open();
    db.putVerifiedObject(golden.ref('hot'), golden.bytes('hot'));
    db.createStaging(stageId, golden.manifest, DateTime.utc(2026));
    db.removeUnreferencedStagingData(stageId);
    for (final e in original.entries) {
      expect(File(e.key).readAsBytesSync(), e.value);
    }
    expect((await offline.loadBaseline())!.toJson()['schema_version'], 4);
    expect((await snapshots.list()).length, 1);
    expect(await snapshots.readText((await snapshots.list()).single.filename),
        utf8.decode(snapshot));
  });
  test('normal startup/read/write code does not import E1', () {
    for (final file in Directory('lib')
        .listSync(recursive: true)
        .whereType<File>()
        .where((f) =>
            f.path.endsWith('.dart') && !f.path.contains('/segmented/'))) {
      expect(file.readAsStringSync(), isNot(contains("import 'segmented/")),
          reason: file.path);
    }
  });
  test(
      'oversized singleton allowed, local size rejection is not protocol incompatibility',
      () {
    final body = golden.body('snapshot-leaf');
    body['table'] = 'app_labels';
    body['min'] = ['t', 'x'];
    body['max'] = ['t', 'x'];
    body['rows'] = [
      {
        'key': ['t', 'x'],
        'value': {'key': 'x', 'value': '', 'updated_at': 'synthetic'}
      }
    ];
    body['oversized'] = false;
    final base = encodeC1(body).length;
    body['rows'][0]['value']['value'] = 'a' * (262144 - base);
    var raw = encodeC1(body);
    expect(raw.length, 262144);
    VerifiedObject.verify(raw, refFor('snapshot-leaf', raw), golden.cache);
    body['rows'][0]['value']['value'] += 'a';
    raw = encodeC1(body);
    expect(
        () => VerifiedObject.verify(
            raw, refFor('snapshot-leaf', raw), golden.cache),
        throwsA(isA<SegmentedException>()));
    body['oversized'] = true;
    raw = encodeC1(body);
    expect(raw.length, 262144);
    VerifiedObject.verify(raw, refFor('snapshot-leaf', raw), golden.cache);
    body['rows'][0]['value']['value'] += 'ab';
    raw = encodeC1(body);
    final ref = refFor('snapshot-leaf', raw), db = open();
    db.putVerifiedObject(ref, raw);
    expect(db.getVerifiedObject(ref)!.bytes, raw);
    expect(
        () => VerifiedObject.verify(raw, ref, golden.cache,
            maxBytes: raw.length - 1),
        throwsA(isA<SegmentedException>()));
  });
}

Future<String> concurrentPut(String path, String fixture, int index) =>
    Isolate.run(() {
      final g = ServerGolden(fixture);
      final raw = g.bytes('raw-root');
      if (index.isOdd) {
        raw[0] = 0;
      }
      // Explicit bounded caller retry of local admission/SQLite contention.
      // No transport retry or scheduler is implemented by E1.
      for (var attempt = 0; attempt < 4; attempt++) {
        SegmentedClientStore? s;
        try {
          s = SegmentedClientStore.open(Directory(path), g.cache);
          s.putVerifiedObject(g.ref('raw-root'), raw);
          return 'stored';
        } on SegmentedException catch (error) {
          if (error.code != 'STORE_BUSY' || attempt == 3) {
            return 'rejected:${error.code}:${error.storageCode}';
          }
          sleep(const Duration(milliseconds: 5));
        } finally {
          s?.close();
        }
      }
      throw StateError('unreachable');
    });
