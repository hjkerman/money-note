import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_fixture.dart';

// Independent inventory from the audited schema; not read from production helpers.
const requiredTriggers = [
  'object_usage',
  'refs_usage',
  'refs_release',
  'edge_usage',
  'staging_usage',
  'staging_release',
  'root_usage',
  'root_release',
  'progress_usage',
  'progress_release',
  'immutable_body'
];

void main() {
  final golden = ServerGolden();
  late Directory directory;
  SegmentedClientStore? store;
  setUp(() {
    directory = Directory.systemTemp.createTempSync('e1-schema-');
  });
  tearDown(() {
    store?.close();
    store = null;
    directory.deleteSync(recursive: true);
  });
  SegmentedClientStore open({int count = 1, StoreFault? fault}) =>
      store = SegmentedClientStore.open(directory, golden.cache,
          limits: ClientStoreLimits(objectCount: count), fault: fault);
  void seed(SegmentedClientStore s) {
    s.putVerifiedObject(golden.ref('index-empty'), golden.bytes('index-empty'));
    s.createStaging(stageId, golden.manifest, DateTime.utc(2026));
    s.recordStagedObject(stageId, golden.ref('index-empty'));
  }

  void preserved(String path) {
    final direct = sqlite3.open(path);
    try {
      expect(direct.select('SELECT count(*) AS n FROM objects').single['n'], 1);
      expect(direct.select('SELECT hash,body FROM objects').single['hash'],
          golden.ref('index-empty').hash);
      expect(direct.select('SELECT body FROM objects').single['body'],
          golden.bytes('index-empty'));
      expect(direct.select('SELECT objects FROM usage').single['objects'], 1);
      expect(direct.select('SELECT payload FROM usage').single['payload'],
          golden.bytes('index-empty').length);
      expect(direct.select('SELECT count(*) AS n FROM staging').single['n'], 1);
      expect(direct.select('SELECT manifest FROM staging').single['manifest'],
          golden.manifest.bytes);
      expect(
          direct.select('SELECT count(*) AS n FROM staging_roots').single['n'],
          4);
      expect(
          direct
              .select('SELECT count(*) AS n FROM staging_objects')
              .single['n'],
          1);
      expect(direct.select('PRAGMA integrity_check').single.values.first, 'ok');
      expect(direct.select('PRAGMA foreign_key_check'), isEmpty);
      direct.execute('BEGIN IMMEDIATE');
      direct.execute('ROLLBACK');
    } finally {
      direct.close();
    }
  }

  final schemaError = throwsA(isA<SegmentedException>()
      .having((e) => e.code, 'code', 'STORE_SCHEMA_CORRUPT'));
  for (final name in requiredTriggers) {
    for (final damage in [
      'missing-before-open',
      'missing-after-open',
      'no-op-after-open'
    ]) {
      test('required trigger $name $damage rejects before any write', () {
        final s = open();
        seed(s);
        final path = s.path;
        if (damage == 'missing-before-open') s.close();
        final direct = sqlite3.open(path);
        try {
          final sql = direct.select(
              'SELECT sql FROM sqlite_master WHERE name=?',
              [name]).single['sql'] as String;
          direct.execute('DROP TRIGGER $name');
          if (damage == 'no-op-after-open') {
            final header = sql.substring(0, sql.indexOf(' BEGIN'));
            direct.execute('$header BEGIN SELECT 1; END');
          }
          final changed = direct
              .select('SELECT sql FROM sqlite_master WHERE name=?', [name]);
          expect(changed.isEmpty || changed.single['sql'] != sql, isTrue);
        } finally {
          direct.close();
        }
        if (damage == 'missing-before-open') {
          expect(() => open(), schemaError);
        } else {
          expect(
              () => s.putVerifiedObject(
                  golden.ref('raw-root'), golden.bytes('raw-root')),
              schemaError);
          // Previously valid bytes remain readable; damaged schema is NOT repaired.
          expect(s.getVerifiedObject(golden.ref('index-empty'))!.bytes,
              golden.bytes('index-empty'));
          expect(
              s.inspectStoreHealth().issues, contains('STORE_SCHEMA_CORRUPT'));
          s.close();
          expect(() => open(), schemaError);
        }
        preserved(path); // Actual COMMIT oracle, not only a thrown exception.
      });
    }
  }
  for (final definition in [
    'CREATE TRIGGER object_usage AFTER INSERT ON objects BEGIN UPDATE usage SET objects=objects+0,payload=payload+length(NEW.body),metadata=metadata+192; END',
    'CREATE TRIGGER object_usage AFTER INSERT ON objects WHEN 0 BEGIN UPDATE usage SET objects=objects+1,payload=payload+length(NEW.body),metadata=metadata+192; END',
    'CREATE TRIGGER object_usage AFTER DELETE ON objects BEGIN UPDATE usage SET objects=objects+1; END',
    'CREATE TRIGGER object_usage AFTER INSERT ON refs BEGIN UPDATE usage SET objects=objects+1; END'
  ]) {
    test('correct trigger name with weakened definition $definition', () {
      final s = open();
      seed(s);
      final direct = sqlite3.open(s.path);
      direct.execute('DROP TRIGGER object_usage');
      direct.execute(definition);
      direct.close();
      expect(
          () => s.putVerifiedObject(
              golden.ref('raw-root'), golden.bytes('raw-root')),
          schemaError);
      preserved(s.path);
    });
  }
  for (final operation in ['duplicate', 'staging', 'progress', 'cleanup']) {
    test('reused connection rejects damaged schema for $operation', () {
      final s = open();
      seed(s);
      final direct = sqlite3.open(s.path);
      direct.execute('DROP TRIGGER progress_release');
      direct.close();
      expect(() {
        switch (operation) {
          case 'duplicate':
            s.putVerifiedObject(
                golden.ref('index-empty'), golden.bytes('index-empty'));
          case 'staging':
            s.createStaging('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
                golden.manifest, DateTime.utc(2026));
          case 'progress':
            s.recordStagedObject(stageId, golden.ref('index-empty'));
          case 'cleanup':
            s.removeUnreferencedStagingData(stageId);
        }
      }, schemaError);
      preserved(s.path);
    });
  }
  test('write transaction excludes concurrent DDL after schema validation', () {
    late String path;
    var attempted = false;
    final s = open(fault: (point) {
      if (point != 'before_object_insert') return;
      final other = sqlite3.open(path);
      try {
        other.execute('PRAGMA busy_timeout=0');
        expect(
            () => other.execute('DROP TRIGGER object_usage'),
            throwsA(
                isA<SqliteException>().having((e) => e.resultCode, 'busy', 5)));
        attempted = true;
      } finally {
        other.close();
      }
    });
    path = s.path;
    seed(s);
    expect(attempted, isTrue);
    preserved(path);
    // Once the protected transaction ends, DDL can commit. Next write rejects it.
    final direct = sqlite3.open(path);
    direct.execute('DROP TRIGGER object_usage');
    direct.close();
    expect(
        () => s.putVerifiedObject(
            golden.ref('raw-root'), golden.bytes('raw-root')),
        schemaError);
    preserved(path);
  });
  test('rolled-back schema change preserves normal writes and quota rollback',
      () {
    final s = open();
    seed(s);
    final other = sqlite3.open(s.path);
    other.execute('BEGIN IMMEDIATE');
    other.execute('DROP TRIGGER object_usage');
    other.execute('ROLLBACK');
    other.close();
    s.putVerifiedObject(golden.ref('index-empty'), golden.bytes('index-empty'));
    expect(
        () => s.putVerifiedObject(
            golden.ref('raw-root'), golden.bytes('raw-root')),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'LOCAL_STORAGE_BUDGET')));
    preserved(s.path);
    s.close();
    expect(open().inspectStoreHealth().healthy, isTrue);
  });
  test('extra trigger and changed table constraints are not a supported schema',
      () {
    final s = open();
    seed(s);
    final other = sqlite3.open(s.path);
    other.execute(
        'CREATE TRIGGER sqliteXcancel AFTER INSERT ON objects BEGIN UPDATE usage SET objects=0; END');
    expect(
        () => s.putVerifiedObject(
            golden.ref('raw-root'), golden.bytes('raw-root')),
        schemaError);
    other.execute('DROP TRIGGER sqliteXcancel');
    other.execute('ALTER TABLE refs ADD COLUMN unexpected TEXT');
    other.close();
    expect(
        () => s.putVerifiedObject(
            golden.ref('raw-root'), golden.bytes('raw-root')),
        schemaError);
    preserved(s.path);
  });
  test('schema version changes are checked on a reused write connection', () {
    final s = open();
    seed(s);
    final other = sqlite3.open(s.path);
    other.execute('PRAGMA user_version=99');
    other.close();
    expect(
        () => s.putVerifiedObject(
            golden.ref('raw-root'), golden.bytes('raw-root')),
        throwsA(isA<SegmentedException>()
            .having((e) => e.code, 'code', 'UNSUPPORTED_STORAGE_SCHEMA')));
    preserved(s.path);
  });
}
