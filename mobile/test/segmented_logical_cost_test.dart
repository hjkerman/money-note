import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/authoritative_bundle_validation.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/logical_cost_sqlite.dart';
import 'support/segmented_fixture.dart';

BigInt value(LogicalCost c, String key) =>
    BigInt.parse(c.snapshot()[key] ?? '0');
BigInt sqlValue(SqlCosts c, String key) => c.values[key] ?? BigInt.zero;

void main() {
  for (final raw in [
    <int>[],
    [1],
    [1, 2, 3],
    utf8.encode('한😀e\u0301')
  ]) {
    test('hash sink counts exact framing and repetition: ${raw.length}', () {
      final c = LogicalCost();
      final preimage = [...ascii.encode('money-note.sync.v1/hot'), 0, ...raw];
      c.run(LogicalCostStage.e2, () {
        expect(objectHash('hot', raw), sha256.convert(preimage).toString());
        expect(objectHash('hot', raw), sha256.convert(preimage).toString());
      });
      expect(value(c, 'e2/objectHash/hashInputBytes'),
          BigInt.from(2 * preimage.length));
      expect(value(c, 'e2/objectHash/calls'), BigInt.two);
    });
  }

  test('checksum and explicit legacy hash do not conflate domains', () {
    final c = LogicalCost();
    c.run(LogicalCostStage.e4Legacy, () {
      expect(localChecksum([1, 2]), sha256.convert([1, 2]).toString());
      expect(bundleHash({'x': '한'}),
          sha256.convert(utf8.encode('{"x":"한"}')).toString());
    });
    expect(value(c, 'e4Legacy/checksum/hashInputBytes'), BigInt.two);
    expect(value(c, 'e4Legacy/legacyHash/hashInputBytes'), BigInt.from(11));
  });

  for (final text in ['{}', '[]', '{"한":"😀"}', '1000.0']) {
    test('canonical validation input has literal byte oracle: $text', () {
      final raw = utf8.encode(text), c = LogicalCost();
      c.run(LogicalCostStage.e3Verify, () {
        decodeC1(raw);
        decodeC1(raw);
      });
      expect(
          value(c, 'e3Verify/c1/submittedBytes'), BigInt.from(2 * raw.length));
      expect(
          value(c, 'e3Verify/c1/completedBytes'), BigInt.from(2 * raw.length));
    });
  }

  for (final raw in [
    <int>[255, 1, 2],
    utf8.encode('{ }'),
    utf8.encode('{"x":'),
    utf8.encode('{"x":1,"x":2}')
  ]) {
    test('failed validation counts submitted not unvisited suffix: $raw', () {
      final c = LogicalCost();
      c.run(LogicalCostStage.e2, () {
        expect(() => decodeC1(raw), throwsA(isA<SegmentedException>()));
      });
      expect(value(c, 'e2/c1/failedSubmittedBytes'), BigInt.from(raw.length));
      expect(value(c, 'e2/c1/completedBytes'), BigInt.zero);
    });
  }

  test('noncanonical wire admission uses same actual full span', () {
    final c = LogicalCost();
    c.run(LogicalCostStage.e2,
        () => decodeC1([123, 32, 125], requireCanonical: false));
    expect(value(c, 'e2/c1/completedBytes'), BigInt.from(3));
  });

  test('async yields and cancellation isolate concurrent collectors', () async {
    final a = LogicalCost(), b = LogicalCost(), barrier = Completer<void>();
    final first = a.run(LogicalCostStage.e2, () async {
      localChecksum([1]);
      await barrier.future;
      localChecksum([1, 2]);
      throw StateError('synthetic cancellation');
    });
    final expectedFailure = expectLater(first, throwsStateError);
    await b.run(LogicalCostStage.e3Verify, () async {
      await Future<void>.delayed(Duration.zero);
      localChecksum([1, 2, 3, 4]);
      barrier.complete();
    });
    await expectedFailure;
    expect(value(a, 'e2/checksum/hashInputBytes'), BigInt.from(3));
    expect(value(b, 'e3Verify/checksum/hashInputBytes'), BigInt.from(4));
    expect(LogicalCost.activeStage, isNull);
  });

  test('closed collector ignores stale completion and has bounded fixed keys',
      () {
    final c = LogicalCost();
    c.run(LogicalCostStage.calibration, () {
      for (var i = 0; i < 10000; i++) {
        localChecksum(const []);
      }
      expect(c.snapshot().length, 2);
      c.close();
      localChecksum([1]);
    });
    expect(value(c, 'calibration/checksum/calls'), BigInt.from(10000));
  });

  test('BigInt aggregate does not wrap signed64', () {
    final c = LogicalCost();
    c.run(LogicalCostStage.calibration, () {
      for (var i = 0; i < 3; i++) {
        LogicalCost.observe(LogicalCostOperation.checksum,
            LogicalCostMetric.hashInputBytes, 9223372036854775807);
      }
    });
    expect(value(c, 'calibration/checksum/hashInputBytes'),
        BigInt.parse('27670116110564327421'));
  });

  test('disabled observer changes neither bytes nor validation outcomes', () {
    final before = encodeC1({'x': '한', 'money': '\u001c+0001000.00\u001f'});
    final digest = objectHash('hot', before);
    final c = LogicalCost();
    c.run(LogicalCostStage.e2, () {
      expect(encodeC1(decodeC1(before)), before);
      expect(objectHash('hot', before), digest);
    });
    expect(objectHash('hot', before), digest);
    expect(LogicalCost.activeStage, isNull);
  });

  test('SQLite new/IGNORE/literal/UTF8 write oracle', () {
    final c = LogicalCost(), s = SqlCosts();
    final db = CostDatabase(sqlite3.openInMemory(), s);
    c.run(LogicalCostStage.e1, () {
      db.execute(
          'CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB) WITHOUT ROWID');
      db.execute('BEGIN');
      for (var i = 0; i < 2; i++) {
        db.execute("INSERT OR IGNORE INTO objects VALUES ('한',?)", [
          [1, 2, 3]
        ]);
      }
      expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/committed'), BigInt.zero);
      db.execute('COMMIT');
      expect(
          db
              .select(
                  'SELECT length(CAST(k AS BLOB)) AS n,length(body) AS b FROM objects')
              .single
              .values
              .toList(),
          [3, 3]);
    });
    expect(
        sqlValue(s, 'e1/objects/INSERT/attempted/blobBytes'), BigInt.from(6));
    expect(
        sqlValue(s, 'e1/objects/INSERT/effective/blobBytes'), BigInt.from(3));
    expect(
        sqlValue(s, 'e1/objects/INSERT/textBytes/committed'), BigInt.from(3));
    db.close();
  });

  test('SQLite triggers/update/rollback are actual row operations', () {
    final c = LogicalCost(), s = SqlCosts();
    final db = CostDatabase(sqlite3.openInMemory(), s);
    c.run(LogicalCostStage.e3Prepare, () {
      db.execute('CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)');
      db.execute('CREATE TABLE pins(k TEXT,reason TEXT)');
      db.execute(
          "CREATE TRIGGER pin AFTER INSERT ON objects BEGIN INSERT INTO pins VALUES (NEW.k,'frozen'); END");
      db.execute('BEGIN');
      db.execute("INSERT INTO objects VALUES ('x',x'010203')");
      db.execute("UPDATE objects SET body=x'04050607' WHERE k='x'");
      db.execute("DELETE FROM pins WHERE k='x'");
      db.execute('ROLLBACK');
      expect(db.select('SELECT * FROM objects'), isEmpty);
    });
    expect(sqlValue(s, 'e3Prepare/pins/INSERT/textBytes/rolledBack'),
        BigInt.from(7));
    expect(sqlValue(s, 'e3Prepare/objects/UPDATE/blobBytes/rolledBack'),
        BigInt.from(4));
    expect(sqlValue(s, 'e3Prepare/pins/DELETE/effective/rows'), BigInt.one);
    db.close();
  });

  test('SQLite close does not mislabel uncommitted bytes', () {
    final c = LogicalCost(), s = SqlCosts();
    final db = CostDatabase(sqlite3.openInMemory(), s);
    c.run(LogicalCostStage.e1, () {
      db.execute('CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)');
      db.execute('BEGIN');
      db.execute("INSERT INTO objects VALUES ('x',x'0102')");
      db.close();
    });
    expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/rolledBackOnClose'),
        BigInt.two);
    expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/committed'), BigInt.zero);
  });

  test('actual E1 store duplicate persistence and independent reopened bytes',
      () {
    final golden = ServerGolden(), c = LogicalCost(), s = SqlCosts();
    final root = Directory.systemTemp.createTempSync('mn-b03-e1-');
    final store = SegmentedClientStore.open(root, golden.cache,
        diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), s));
    try {
      c.run(LogicalCostStage.e1, () {
        store.putVerifiedObject(golden.ref('control'), golden.bytes('control'));
        store.putVerifiedObject(golden.ref('control'), golden.bytes('control'));
      });
      final db = sqlite3.open(store.path);
      expect(db.select('SELECT body FROM objects').single['body'],
          golden.bytes('control'));
      expect(db.select('PRAGMA foreign_key_check'), isEmpty);
      db.close();
      expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/committed'),
          BigInt.from(golden.bytes('control').length));
      expect(sqlValue(s, 'e1/objects/INSERT/effective/rows'), BigInt.one);
    } finally {
      store.close();
    }
  });

  test('prepared statements and savepoint rollback have exact outcomes', () {
    final c = LogicalCost(), s = SqlCosts();
    final db = CostDatabase(sqlite3.openInMemory(), s);
    c.run(LogicalCostStage.e1, () {
      db.execute('CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)');
      final insert = db.prepare('INSERT INTO objects VALUES (?,?)');
      db.execute('BEGIN');
      insert.execute([
        'a',
        [1]
      ]);
      db.execute('SAVEPOINT part');
      insert.execute([
        'b',
        [2, 3]
      ]);
      db.execute('ROLLBACK TO part');
      db.execute('RELEASE part');
      expect(
          () => insert.execute([
                'a',
                [4, 5, 6]
              ]),
          throwsA(isA<SqliteException>()));
      db.execute('COMMIT');
      insert.close();
      expect(db.select('SELECT count(*) AS n FROM objects').single['n'], 1);
    });
    expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/committed'), BigInt.one);
    expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/rolledBack'), BigInt.two);
    expect(
        sqlValue(s, 'e1/objects/INSERT/attempted/blobBytes'), BigInt.from(6));
    db.close();
  });

  test('independent SQL scopes retain ownership across one native commit', () {
    final a = LogicalCost(), b = LogicalCost(), s = SqlCosts();
    final db = CostDatabase(sqlite3.openInMemory(), s);
    db.execute('CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)');
    a.run(LogicalCostStage.e1, () {
      db.execute('BEGIN');
      db.execute("INSERT INTO objects VALUES ('a',x'01')");
    });
    b.run(LogicalCostStage.e1,
        () => db.execute("INSERT INTO objects VALUES ('b',x'0203')"));
    a.run(LogicalCostStage.e1, () => db.execute('COMMIT'));
    expect(sqlValue(s.forCollector(a), 'e1/objects/INSERT/blobBytes/committed'),
        BigInt.one);
    expect(sqlValue(s.forCollector(b), 'e1/objects/INSERT/blobBytes/committed'),
        BigInt.two);
    db.close();
  });

  test('actual E1 pre-COMMIT fault records rollback, not durable addition', () {
    final golden = ServerGolden(), c = LogicalCost(), s = SqlCosts();
    final root = Directory.systemTemp.createTempSync('mn-b03-rollback-');
    final store = SegmentedClientStore.open(root, golden.cache,
        fault: (point) {
          if (point == 'before_commit') throw StateError('synthetic');
        },
        diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), s));
    try {
      c.run(
          LogicalCostStage.e1,
          () => expect(
              () => store.putVerifiedObject(
                  golden.ref('control'), golden.bytes('control')),
              throwsStateError));
      final independent = sqlite3.open(store.path);
      expect(independent.select('SELECT * FROM objects'), isEmpty);
      independent.close();
      expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/rolledBack'),
          BigInt.from(golden.bytes('control').length));
      expect(sqlValue(s, 'e1/objects/INSERT/blobBytes/committed'), BigInt.zero);
    } finally {
      store.close();
    }
  });
}
