import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/logical_cost_sqlite.dart';

void main() {
  test('IC01 read-only CTE never installs write observers', () {
    final native = sqlite3.openInMemory(), costs = SqlCosts();
    final d = CostDatabase(native, costs);
    try {
      d.execute('CREATE TABLE t(k TEXT)');
      d.execute('PRAGMA query_only=ON');
      expect(d.select('WITH x AS (SELECT 1 n) SELECT * FROM x').single['n'], 1);
      expect(costs.values['observer/setupStatements'], isNull);
    } finally {
      d.close();
    }
  });
  test('IC01 multi-statement DML explicitly rejected before any mutation', () {
    final c = LogicalCost(), s = SqlCosts(), native = sqlite3.openInMemory();
    final d = CostDatabase(native, s);
    try {
      d.execute('CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)');
      expect(
          () => c.run(
              LogicalCostStage.e1,
              () => d.execute(
                  "INSERT INTO t VALUES ('a',x'01'); INSERT INTO t VALUES ('a',x'0203');")),
          throwsStateError);
      expect(native.select('SELECT * FROM t'), isEmpty);
      c.run(
          LogicalCostStage.e1,
          () => d.execute(
              "/* ; */ INSERT INTO t VALUES ('semi;--/*',x'0102'); -- trailing comment"));
      expect(native.select('SELECT length(b) n FROM t').single['n'], 2);
      expect(s.values['e1/t/INSERT/blobBytes/committed'], BigInt.two);
    } finally {
      d.close();
    }
  });
  test('IC01 failed native commit retains pending until actual rollback', () {
    final c = LogicalCost(), s = SqlCosts(), native = sqlite3.openInMemory();
    final d = CostDatabase(native, s);
    try {
      d.execute('PRAGMA foreign_keys=ON');
      d.execute('CREATE TABLE p(k TEXT PRIMARY KEY)');
      d.execute(
          'CREATE TABLE child(k TEXT REFERENCES p(k) DEFERRABLE INITIALLY DEFERRED,b BLOB)');
      c.run(LogicalCostStage.e3Commit, () {
        d.execute('BEGIN');
        d.execute("INSERT INTO child VALUES ('missing',x'0102')");
        expect(() => d.execute('COMMIT'), throwsA(isA<SqliteException>()));
        expect(d.autocommit, isFalse);
        expect(
            s.values['e3Commit/child/INSERT/blobBytes/committed'] ??
                BigInt.zero,
            BigInt.zero);
        d.execute('ROLLBACK TRANSACTION');
      });
      expect(native.select('SELECT * FROM child'), isEmpty);
      expect(
          s.values['e3Commit/child/INSERT/blobBytes/rolledBack'], BigInt.two);
    } finally {
      d.close();
    }
  });
  for (final prefix in [
    '-- INSERT ignored\n',
    ' /* DELETE */ ',
    '\n-- x\n/* UPDATE */ '
  ]) {
    test('IC01 leading comment DML $prefix', () {
      final c = LogicalCost(), s = SqlCosts(), native = sqlite3.openInMemory();
      final d = CostDatabase(native, s);
      try {
        d.execute('CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)');
        c.run(LogicalCostStage.e1,
            () => d.execute("${prefix}INSERT INTO t VALUES ('a',x'0102')"));
        expect(native.select('SELECT length(b) n FROM t').single['n'], 2);
        expect(s.values['e1/t/INSERT/blobBytes/committed'], BigInt.two);
      } finally {
        d.close();
      }
    });
  }
  for (final name in ['s', '"S p"', "'s''p'", '`s`', '[s]']) {
    test('IC01 nearest same-name savepoint $name', () {
      final c = LogicalCost(), s = SqlCosts(), native = sqlite3.openInMemory();
      final d = CostDatabase(native, s);
      try {
        d.execute('CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)');
        c.run(LogicalCostStage.e3Commit, () {
          for (final sql in [
            'BEGIN',
            'SAVEPOINT $name',
            "INSERT INTO t VALUES ('a',x'01')",
            'SAVEPOINT $name',
            "INSERT INTO t VALUES ('b',x'0203')",
            'ROLLBACK TRANSACTION TO SAVEPOINT $name',
            'RELEASE SAVEPOINT $name',
            'COMMIT'
          ]) {
            d.execute(sql);
          }
        });
        expect(
            native.select('SELECT k,length(b) n FROM t').single.values.toList(),
            ['a', 1]);
        expect(s.values['e3Commit/t/INSERT/blobBytes/committed'], BigInt.one);
        expect(s.values['e3Commit/t/INSERT/blobBytes/rolledBack'], BigInt.two);
      } finally {
        d.close();
      }
    });
  }
  for (final mode in ['FAIL', 'ABORT', 'ROLLBACK']) {
    for (final explicit in [false, true]) {
      test('IC01 native partial SQL $mode explicit=$explicit', () {
        final c = LogicalCost(),
            s = SqlCosts(),
            native = sqlite3.openInMemory();
        final d = CostDatabase(native, s);
        try {
          d.execute('CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)');
          c.run(LogicalCostStage.e1, () {
            if (explicit) d.execute('BEGIN');
            d.execute("INSERT INTO t VALUES ('prior',x'01')");
            expect(
                () => d.execute(
                    "INSERT OR $mode INTO t VALUES ('a',x'0203'),('prior',x'040506')"),
                throwsA(isA<SqliteException>()));
            if (!d.autocommit) d.execute('COMMIT');
          });
          final expected =
              mode == 'FAIL' ? 3 : (explicit && mode == 'ROLLBACK' ? 0 : 1);
          final total = native
              .select('SELECT coalesce(sum(length(b)),0) n FROM t')
              .single['n'];
          expect(total, expected);
          expect(s.values['e1/t/INSERT/blobBytes/committed'] ?? BigInt.zero,
              BigInt.from(expected));
          expect(s.values['e1/t/INSERT/attempted/blobBytes'], BigInt.from(6));
        } finally {
          d.close();
        }
      });
    }
  }
  test('IC01 owner bound rejects before mutation and cleans rollback', () {
    final s = SqlCosts(), native = sqlite3.openInMemory();
    final d = CostDatabase(native, s);
    try {
      d.execute('CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB)');
      d.execute('BEGIN');
      for (var i = 0; i < CostDatabase.transactionOwnerLimit; i++) {
        final c = LogicalCost();
        c.run(
            LogicalCostStage.e1,
            () => d.execute('INSERT INTO t VALUES (?,?)', [
                  '$i',
                  [1]
                ]));
        c.close();
      }
      final next = LogicalCost();
      expect(
          () => next.run(LogicalCostStage.e1,
              () => d.execute("INSERT INTO t VALUES ('overflow',x'01')")),
          throwsStateError);
      expect(native.select('SELECT count(*) n FROM t').single['n'], 32);
      d.execute('ROLLBACK');
      next.run(LogicalCostStage.e1,
          () => d.execute("INSERT INTO t VALUES ('next',x'0102')"));
      expect(native.select('SELECT length(b) n FROM t').single['n'], 2);
      expect(s.forCollector(next).values['e1/t/INSERT/blobBytes/committed'],
          BigInt.two);
    } finally {
      d.close();
    }
  });
}
