import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/logical_cost_sqlite.dart';

void main() {
  Map<String, Object?> workload(int capacity) {
    final c = LogicalCost(), costs = SqlCosts();
    final d = CostDatabase(sqlite3.openInMemory(), costs,
        statementCapacity: capacity);
    d.execute(
        'CREATE TABLE t(k TEXT PRIMARY KEY,b BLOB,x TEXT,n INTEGER,r REAL)');
    c.run(LogicalCostStage.e1, () {
      d.execute('BEGIN');
      d.execute('SAVEPOINT a');
      d.execute(
          '/* INSERT false */ -- UPDATE false\n INSERT INTO t VALUES(?,?,?,?,?)',
          [
            'a',
            Uint8List.fromList([1]),
            '한글😀',
            null,
            1.25
          ]);
      d.execute('SAVEPOINT a');
      d.execute('INSERT INTO t VALUES(?,?,?,?,?)', [
        'b',
        Uint8List.fromList([2, 3]),
        '',
        2,
        null
      ]);
      d.execute('ROLLBACK TO a');
      d.execute('RELEASE a');
      expect(
          () => d.execute('INSERT OR FAIL INTO t(k,b) VALUES(?,?),(?,?)', [
                'c',
                Uint8List.fromList([4, 5]),
                'a',
                Uint8List.fromList([6])
              ]),
          throwsA(isA<SqliteException>()));
      d.execute('INSERT OR IGNORE INTO t(k,b) VALUES(?,?)', [
        'a',
        [9]
      ]);
      d.execute('UPDATE t SET x=? WHERE k=?', ['새 값', 'a']);
      d.execute('COMMIT');
      d.execute('BEGIN');
      d.execute('INSERT INTO t(k,b) VALUES(?,?)', [
        'rolled',
        [7, 8, 9]
      ]);
      d.execute('ROLLBACK');
      // Every call executes; changing binds cannot reuse results or old BLOBs.
      expect(d.select('SELECT k,b,x,n,r FROM t WHERE k=?', ['a']).single['x'],
          '새 값');
      expect(d.select('SELECT k,b,x,n,r FROM t WHERE k=?', ['c']).single['b'],
          [4, 5]);
      expect(d.select('SELECT k FROM t WHERE k=?', ['missing']), isEmpty);
    });
    final rows = [
      for (final r in d.inner.select('SELECT * FROM t ORDER BY k')) r.values
    ];
    final result = <String, Object?>{
      'sql': costs.snapshot(),
      'primitive': c.snapshot(),
      'rows': rows
    };
    d.close();
    expect(d.statementReuse['created'], d.statementReuse['finalized']);
    expect(d.statementReuse['peakLive'], lessThanOrEqualTo(capacity));
    c.close();
    return result;
  }

  test(
      'P02 exact attempted/effective/committed, savepoint, partial FAIL and state equivalence',
      () {
    expect(workload(32), workload(0));
  });

  test('P02 finite LRU evicts/finalizes without changing result or binds', () {
    final d =
        CostDatabase(sqlite3.openInMemory(), SqlCosts(), statementCapacity: 2);
    try {
      for (var i = 0; i < 100; i++) {
        expect(d.select('SELECT ? AS v /* ${i % 3} */', [i]).single['v'], i);
      }
      expect(d.statementReuse['peakLive'], 2);
      expect(d.statementReuse['evictions'], 98);
      expect(d.statementReuse['created'], 100);
      expect(d.statementReuse['finalized'], 98);
    } finally {
      d.close();
    }
    expect(d.statementReuse['finalized'], 100);
    expect(() => d.select('SELECT 1'), throwsStateError);
    d.close(); // Driver-compatible idempotent closure.
  });

  test(
      'P02 handles belong to connection and current async collector, not SQL text/run',
      () async {
    final a = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    final b = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    final c1 = LogicalCost(), c2 = LogicalCost();
    try {
      for (final d in [a, b]) {
        d.execute('CREATE TABLE t(b BLOB)');
      }
      await Future.wait([
        c1.run(LogicalCostStage.e1, () async {
          await Future<void>.value();
          a.execute('INSERT INTO t VALUES(?)', [
            [1]
          ]);
        }),
        c2.run(LogicalCostStage.e3Commit, () async {
          await Future<void>.value();
          b.execute('INSERT INTO t VALUES(?)', [
            [2, 3]
          ]);
        }),
      ]);
      expect(a.costs.values['e1/t/INSERT/blobBytes/committed'], BigInt.one);
      expect(
          b.costs.values['e3Commit/t/INSERT/blobBytes/committed'], BigInt.two);
      expect(a.inner.select('SELECT b FROM t').single['b'], [1]);
      expect(b.inner.select('SELECT b FROM t').single['b'], [2, 3]);
      c1.close();
      c2.close();
      final before = a.costs.snapshot();
      c1.run(
          LogicalCostStage.e1,
          () => a.execute('INSERT INTO t VALUES(?)', [
                [4]
              ]));
      expect(a.costs.snapshot(), before);
    } finally {
      a.close();
      b.close();
    }
  });

  test(
      'P02 failed bind/constraint releases handle; next call reparses and rebinds',
      () {
    final d = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    try {
      d.execute('CREATE TABLE t(k INTEGER PRIMARY KEY,b BLOB)');
      d.execute('INSERT INTO t VALUES(?,?)', [
        1,
        [1]
      ]);
      expect(
          () => d.execute('INSERT INTO t VALUES(?,?)', [
                1,
                [2]
              ]),
          throwsA(isA<SqliteException>()));
      expect(() => d.execute('INSERT INTO t VALUES(?,?)', [2]),
          throwsArgumentError);
      d.execute('INSERT INTO t VALUES(?,?)', [2, null]);
      expect(d.inner.select('SELECT b FROM t ORDER BY k').map((r) => r['b']), [
        [1],
        null
      ]);
      expect(d.statementReuse['finalized'], greaterThanOrEqualTo(2));
    } finally {
      d.close();
    }
    expect(d.statementReuse['created'], d.statementReuse['finalized']);
  });

  test('P02 schema invalidation recompiles original SQL without cached rows',
      () {
    final d = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    try {
      d.execute('CREATE TABLE t(a TEXT)');
      expect(d.select('SELECT * FROM t').columnNames, ['a']);
      d.execute('ALTER TABLE t ADD COLUMN b BLOB');
      expect(d.select('SELECT * FROM t').columnNames, ['a', 'b']);
      d.execute('DROP TABLE t');
      expect(
          () => d.select('SELECT * FROM t'), throwsA(isA<SqliteException>()));
      d.execute('CREATE TABLE t(c INTEGER)');
      expect(d.select('SELECT * FROM t').columnNames, ['c']);
    } finally {
      d.close();
    }
  });

  test('P02 SQLITE_BUSY preserves native error and later execution', () {
    final temp = Directory.systemTemp.createTempSync('mn-p02-lock-');
    final a = sqlite3.open('${temp.path}/db');
    final b = CostDatabase(sqlite3.open('${temp.path}/db'), SqlCosts());
    try {
      a.execute('CREATE TABLE t(a INTEGER)');
      a.execute('BEGIN EXCLUSIVE');
      expect(() => b.execute('INSERT INTO t VALUES(?)', [1]),
          throwsA(isA<SqliteException>()));
      a.execute('ROLLBACK');
      b.execute('INSERT INTO t VALUES(?)', [2]);
      b.close();
      final fresh = sqlite3.open('${temp.path}/db');
      try {
        expect(fresh.select('SELECT a FROM t').single['a'], 2);
      } finally {
        fresh.close();
      }
    } finally {
      a.close();
      b.close();
      temp.deleteSync(recursive: true);
    }
  });

  test('P02 no-parameter multi-DDL retains original sqlite3_exec behavior', () {
    final d = CostDatabase(sqlite3.openInMemory(), SqlCosts());
    try {
      d.execute('CREATE TABLE a(k); CREATE TABLE b(k)');
      expect(
          d.inner
              .select("SELECT name FROM sqlite_master WHERE type='table'")
              .length,
          2);
      expect(
          () => d.execute(
              'INSERT INTO a VALUES(?); INSERT INTO b VALUES(?)', [1, 2]),
          throwsStateError);
    } finally {
      d.close();
    }
  });

  test('P02 reentrant active handle cannot be evicted or closed', () {
    final native = sqlite3.openInMemory();
    final d = CostDatabase(native, SqlCosts(), statementCapacity: 1);
    native.createFunction(
        functionName: 'nested',
        function: (_) {
          expect(() => d.select('SELECT 2'), throwsStateError);
          expect(() => d.close(), throwsStateError);
          return 1;
        });
    try {
      expect(d.select('SELECT nested()').single.values.single, 1);
      expect(d.statementReuse['capacityRejections'], 1);
      expect(d.statementReuse['peakLive'], 1);
    } finally {
      d.close();
    }
    expect(d.statementReuse['created'], d.statementReuse['finalized']);
  });

  test('P02 exact finite capacity and oversized SQL bypass', () {
    final native = sqlite3.openInMemory();
    try {
      expect(() => CostDatabase(native, SqlCosts(), statementCapacity: 33),
          throwsArgumentError);
      expect(() => CostDatabase(native, SqlCosts(), statementCapacity: -1),
          throwsArgumentError);
      final d = CostDatabase(native, SqlCosts(), statementCapacity: 1);
      expect(
          d.select('SELECT ? AS n /* ${'x' * 16384} */', [42]).single['n'], 42);
      expect(d.statementReuse['created'], 0);
      expect(d.select('SELECT ?', [43]).single.values.single, 43);
      expect(d.statementReuse['created'], 1);
      d.close();
      expect(d.statementReuse['finalized'], 1);
    } finally {
      native.close();
    }
  });

  test('P02 cached handle never retains previous run attribution', () {
    final sql = SqlCosts();
    final d = CostDatabase(sqlite3.openInMemory(), sql);
    final first = LogicalCost(), next = LogicalCost();
    try {
      d.execute('CREATE TABLE t(b BLOB)');
      first.run(
          LogicalCostStage.e1,
          () => d.execute('INSERT INTO t VALUES(?)', [
                [1]
              ]));
      first.close();
      final before = sql.snapshot();
      next.run(
          LogicalCostStage.e3Commit,
          () => d.execute('INSERT INTO t VALUES(?)', [
                [2, 3]
              ]));
      expect(sql.snapshot(), before);
      final newer = sql.forCollector(next);
      expect(newer.values['e3Commit/t/INSERT/blobBytes/committed'], BigInt.two);
      expect(d.statementReuse['hits'], greaterThanOrEqualTo(1));
      expect(d.inner.select('SELECT sum(length(b)) n FROM t').single['n'], 3);
      next.close();
    } finally {
      d.close();
    }
  });
}
