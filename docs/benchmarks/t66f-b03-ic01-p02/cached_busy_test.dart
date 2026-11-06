import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';

void main() {
  test('P02 already-cached SQLITE_BUSY finalizes once, reparses and persists exact rows', () {
    final temp = Directory.systemTemp.createTempSync('mn-p02-cached-busy-');
    final a = sqlite3.open('${temp.path}/db');
    final b = CostDatabase(sqlite3.open('${temp.path}/db'), SqlCosts());
    try {
      a.execute('CREATE TABLE t(a INTEGER)');
      b.execute('INSERT INTO t VALUES(?)', [0]);
      a.execute('BEGIN EXCLUSIVE');
      expect(
        () => b.execute('INSERT INTO t VALUES(?)', [1]),
        throwsA(
          isA<SqliteException>().having((e) => e.resultCode, 'SQLITE_BUSY', 5),
        ),
      );
      expect(b.statementReuse['hits'], 1);
      expect(b.statementReuse['finalized'], 1);
      a.execute('ROLLBACK');
      b.execute('INSERT INTO t VALUES(?)', [2]);
      b.close();
      expect(b.statementReuse['created'], b.statementReuse['finalized']);
      final fresh = sqlite3.open('${temp.path}/db');
      try {
        expect(fresh.select('SELECT a FROM t ORDER BY a').map((r) => r['a']), [
          0,
          2,
        ]);
      } finally {
        fresh.close();
      }
      final process = Process.runSync(
        '${Directory.current.parent.path}/.venv/bin/python',
        [
          '-c',
          "import sqlite3,sys,json; c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True); print(json.dumps([r[0] for r in c.execute('SELECT a FROM t ORDER BY a')])); c.close()",
          '${temp.path}/db',
        ],
      );
      expect(process.exitCode, 0, reason: '${process.stderr}');
      expect(
        '${process.stdout}'.trim(),
        '[0, 2]',
        reason: 'independent fresh-process SQLite durable state',
      );
    } finally {
      a.close();
      b.close();
      temp.deleteSync(recursive: true);
    }
  });
}
