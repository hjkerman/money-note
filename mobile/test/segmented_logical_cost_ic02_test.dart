import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/logical_cost_sqlite.dart';

BigInt logicalBlob(SqlCosts costs, String operation, String outcome) =>
    BigInt.parse(costs.snapshot()[
            outcome == 'attempted' || outcome == 'effective'
                ? 'e1/payload/$operation/$outcome/blobBytes'
                : 'e1/payload/$operation/blobBytes/$outcome'] ??
        '0');

void main() {
  for (final replace in [false, true]) {
    test(
        'IC02 N01 external DDL=$replace stops incomplete measurement before DML',
        () {
      final scratch = Directory.systemTemp.createTempSync('money-note-ic02-');
      try {
        for (final refreshRead in [false, true]) {
          final run = LogicalCost(), costs = SqlCosts();
          final path = '${scratch.path}/schema-$refreshRead.sqlite';
          final native = sqlite3.open(path), other = sqlite3.open(path);
          final db = CostDatabase(native, costs);
          try {
            run.run(LogicalCostStage.e1, () {
              db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
              db.execute("INSERT INTO payload VALUES('initial',x'01')");
              final String statement;
              if (replace) {
                other.execute('DROP TABLE payload');
                other
                    .execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
                statement = "INSERT INTO payload VALUES('next',x'020304')";
              } else {
                other.execute('ALTER TABLE payload ADD COLUMN extra BLOB');
                statement =
                    "INSERT INTO payload VALUES('next',x'0203',x'040506')";
              }
              if (refreshRead) db.select('SELECT * FROM payload');
              expect(
                  () => db.execute(statement),
                  throwsA(isA<StateError>().having(
                      (e) => e.message,
                      'message',
                      contains(
                          'external schema change; measurement incomplete'))));
              expect(
                  native
                      .select("SELECT count(*) n FROM payload WHERE k='next'")
                      .single['n'],
                  0);
            });
            for (final outcome in ['attempted', 'effective', 'committed']) {
              expect(logicalBlob(costs, 'INSERT', outcome), BigInt.one);
            }
            expect(costs.snapshot()['e1/coverage/externalSchemaChange'], '1');
          } finally {
            other.close();
            db.close();
            run.close();
          }
        }
      } finally {
        scratch.deleteSync(recursive: true);
      }
    });
  }

  test('IC02 N01 failed DDL and new table refresh metadata', () {
    final run = LogicalCost(), costs = SqlCosts();
    final native = sqlite3.openInMemory();
    final db = CostDatabase(native, costs);
    try {
      run.run(LogicalCostStage.e1, () {
        db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
        db.execute("INSERT INTO payload VALUES('initial',x'01')");
        expect(() => db.execute('ALTER TABLE missing ADD COLUMN extra BLOB'),
            throwsA(isA<SqliteException>()));
        db.execute('CREATE TABLE fresh(b BLOB)');
        db.execute("INSERT INTO fresh VALUES(x'0203')");
        db.execute("INSERT INTO payload VALUES('next',x'040506')");
      });
      expect(
          native.select('SELECT sum(length(b)) n FROM payload').single['n'], 4);
      expect(
          native.select('SELECT sum(length(b)) n FROM fresh').single['n'], 2);
      for (final outcome in ['attempted', 'effective', 'committed']) {
        expect(logicalBlob(costs, 'INSERT', outcome), BigInt.from(4));
        final key = outcome == 'committed'
            ? 'e1/fresh/INSERT/blobBytes/committed'
            : 'e1/fresh/INSERT/$outcome/blobBytes';
        expect(costs.snapshot()[key], '2');
      }
    } finally {
      db.close();
      run.close();
    }
  });
  for (final operation in ['alter', 'drop_recreate']) {
    test('IC02 N01 $operation preserves all logical write classes', () {
      final run = LogicalCost();
      final costs = SqlCosts();
      final native = sqlite3.openInMemory();
      final db = CostDatabase(native, costs);
      try {
        db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
        run.run(LogicalCostStage.e1, () {
          db.execute("INSERT INTO payload VALUES('initial',x'01')");
          if (operation == 'alter') {
            db.execute('ALTER TABLE payload ADD COLUMN extra BLOB');
            db.execute("INSERT INTO payload VALUES('next',x'0203',x'040506')");
          } else {
            db.execute('DROP TABLE payload');
            db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
            db.execute("INSERT INTO payload VALUES('next',x'020304')");
          }
        });
        final expected = operation == 'alter' ? BigInt.from(6) : BigInt.from(4);
        final nativeBytes = operation == 'alter'
            ? native
                .select(
                    'SELECT sum(length(b))+sum(COALESCE(length(extra),0)) n FROM payload')
                .single['n'] as int
            : 1 +
                (native
                    .select('SELECT sum(length(b)) n FROM payload')
                    .single['n'] as int);
        expect(nativeBytes, expected.toInt());
        for (final outcome in ['attempted', 'effective', 'committed']) {
          expect(logicalBlob(costs, 'INSERT', outcome), expected);
        }
      } finally {
        db.close();
        run.close();
      }
    });
  }

  test('IC02 N01 refreshed trigger counts update, upsert, and delete', () {
    final run = LogicalCost();
    final costs = SqlCosts();
    final native = sqlite3.openInMemory();
    final db = CostDatabase(native, costs);
    try {
      db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
      run.run(LogicalCostStage.e1, () {
        db.execute("INSERT INTO payload VALUES('initial',x'01')");
        db.execute('ALTER TABLE payload ADD COLUMN extra BLOB');
        db.execute(
            "UPDATE payload SET b=x'0203',extra=x'04' WHERE k='initial'");
        db.execute("INSERT INTO payload VALUES('next',x'05',x'0607') "
            'ON CONFLICT(k) DO UPDATE SET b=excluded.b,extra=excluded.extra');
        db.execute("DELETE FROM payload WHERE k='next'");
      });
      expect(
          native.select('SELECT b,extra FROM payload').single.values.toList(), [
        <int>[2, 3],
        <int>[4]
      ]);
      for (final outcome in ['attempted', 'effective', 'committed']) {
        expect(logicalBlob(costs, 'UPDATE', outcome), BigInt.from(3));
        expect(logicalBlob(costs, 'INSERT', outcome), BigInt.from(4));
      }
      expect(logicalBlob(costs, 'DELETE', 'committed'), BigInt.zero);
    } finally {
      db.close();
      run.close();
    }
  });

  test('IC02 N01 rollback of transactional DDL refreshes old schema', () {
    final run = LogicalCost();
    final costs = SqlCosts();
    final native = sqlite3.openInMemory();
    final db = CostDatabase(native, costs);
    try {
      db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
      run.run(LogicalCostStage.e1, () {
        db.execute('BEGIN');
        db.execute("INSERT INTO payload VALUES('initial',x'01')");
        db.execute('SAVEPOINT schema_change');
        db.execute('ALTER TABLE payload ADD COLUMN extra BLOB');
        db.execute("INSERT INTO payload VALUES('rolled',x'0203',x'04')");
        db.execute('ROLLBACK TO schema_change');
        db.execute('RELEASE schema_change');
        db.execute('COMMIT');
        db.execute("INSERT INTO payload VALUES('next',x'0607')");
      });
      expect(
          native.select('SELECT sum(length(b)) n FROM payload').single['n'], 3);
      expect(logicalBlob(costs, 'INSERT', 'attempted'), BigInt.from(6));
      expect(logicalBlob(costs, 'INSERT', 'effective'), BigInt.from(6));
      expect(logicalBlob(costs, 'INSERT', 'committed'), BigInt.from(3));
      expect(logicalBlob(costs, 'INSERT', 'rolledBack'), BigInt.from(3));
    } finally {
      db.close();
      run.close();
    }
  });

  test('IC02 N01 cached statement is re-prepared across schema replacement',
      () {
    final run = LogicalCost();
    final costs = SqlCosts();
    final native = sqlite3.openInMemory();
    final db = CostDatabase(native, costs);
    try {
      db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
      run.run(LogicalCostStage.e1, () {
        db.execute("INSERT INTO payload VALUES('a',x'01')");
        expect(db.select('SELECT * FROM payload WHERE k=?', ['a']).columnNames,
            ['k', 'b']);
        db.execute('ALTER TABLE payload ADD COLUMN extra BLOB');
        expect(db.select('SELECT * FROM payload WHERE k=?', ['a']).columnNames,
            ['k', 'b', 'extra']);
        db.execute('DROP TABLE payload');
        db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
        db.execute("INSERT INTO payload VALUES('a',x'0203')");
        expect(db.select('SELECT * FROM payload WHERE k=?', ['a']).columnNames,
            ['k', 'b']);
      });
      expect(db.statementReuse['hits'], greaterThanOrEqualTo(1));
      expect(db.statementReuse['peakLive'], lessThanOrEqualTo(32));
      expect(db.statementReuse['created'],
          db.statementReuse['finalized']! + db.statementReuse['peakLive']!);
    } finally {
      db.close();
      run.close();
    }
  });
}
