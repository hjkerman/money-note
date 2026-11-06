import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';

void main() {
  test(
    'IC02 cached bound DML reprepare has exactly three native row events',
    () {
      final states = <List<List<Object?>>>[];
      const statement = 'INSERT INTO payload(k,b) VALUES(?,?)';
      for (final enabled in [false, true]) {
        final run = LogicalCost(), costs = SqlCosts();
        final native = sqlite3.openInMemory();
        final Database db = enabled ? CostDatabase(native, costs) : native;
        try {
          run.run(LogicalCostStage.e1, () {
            db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
            db.execute(statement, [
              'a',
              <int>[49],
            ]);
            db.execute(
              "ALTER TABLE payload ADD COLUMN extra BLOB DEFAULT x'0203'",
            );
            db.execute(statement, [
              'b',
              <int>[52, 53, 54],
            ]);
            db.execute('DROP TABLE payload');
            db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
            db.execute(statement, [
              'c',
              <int>[55, 56],
            ]);
          });
          states.add(
            native
                .select('SELECT k,b FROM payload')
                .map((row) => row.values.toList())
                .toList(),
          );
          if (enabled) {
            // Literal event ledger: 1 + (3 + 2 DEFAULT) + 2 = 8B.
            final snapshot = costs.snapshot();
            expect(snapshot['e1/payload/INSERT/attempted/blobBytes'], '8');
            expect(snapshot['e1/payload/INSERT/effective/blobBytes'], '8');
            expect(snapshot['e1/payload/INSERT/blobBytes/committed'], '8');
            expect(snapshot['e1/payload/INSERT/effective/rows'], '3');
            final observed = db as CostDatabase;
            expect(observed.statementReuse['hits'], 2);
            expect(observed.statementReuse['created'], 1);
          }
        } finally {
          db.close();
          run.close();
        }
      }
      expect(states, [
        [
          [
            'c',
            <int>[55, 56],
          ],
        ],
        [
          [
            'c',
            <int>[55, 56],
          ],
        ],
      ]);
    },
  );
}
