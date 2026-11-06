import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';

void main() {
  test('P01 bounded diagnostic classifier and aggregation parts', () {
    const sqls = [
      'SELECT o.*,r.bytes AS size FROM objects o JOIN refs r USING(hash) WHERE hash=?',
      'INSERT INTO objects VALUES(?,?,?,?)',
      '/* comment */ INSERT OR IGNORE INTO staging_objects VALUES(?,?)',
      'BEGIN IMMEDIATE',
      'COMMIT',
      'ROLLBACK TO SAVEPOINT checkpoint_a',
    ];
    final records = <String, Object>{};
    const iterations = 20000;
    for (var repeat = 0; repeat < 6; repeat++) {
      final w = Stopwatch()..start();
      var words = 0;
      for (var i = 0; i < iterations; i++)
        words += costSqlWords(sqls[i % sqls.length]).length;
      expect(words, greaterThan(iterations));
      records['classify_$repeat'] = {
        'wall_us': w.elapsedMicroseconds,
        'calls': iterations,
      };
      final s = SqlCosts();
      w.reset();
      for (var i = 0; i < iterations; i++)
        s.add('e2/objects/INSERT/effective/blobBytes', 67);
      records['add_$repeat'] = {
        'wall_us': w.elapsedMicroseconds,
        'calls': iterations,
      };
      expect(s.values.values.single, BigInt.from(iterations * 67));
      final pending = {for (var i = 0; i < 160; i++) 'key_$i': BigInt.from(i)};
      var size = 0;
      w.reset();
      for (var i = 0; i < iterations; i++)
        size += Map<String, BigInt>.of(pending).length;
      records['pending_copy_$repeat'] = {
        'wall_us': w.elapsedMicroseconds,
        'calls': iterations,
        'keys_per_copy': 160,
      };
      expect(size, iterations * 160);
      final c = LogicalCost();
      w.reset();
      c.run(LogicalCostStage.e2, () {
        for (var i = 0; i < iterations; i++)
          LogicalCost.observe(
            LogicalCostOperation.c1,
            LogicalCostMetric.submittedBytes,
            67,
          );
      });
      records['primitive_observe_$repeat'] = {
        'wall_us': w.elapsedMicroseconds,
        'calls': iterations,
      };
      expect(c.snapshot().values.single, '${iterations * 67}');
      c.close();
    }
    final path =
        '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-ic01-p01/evidence/cost-parts-results.json';
    File(path).writeAsStringSync(
      jsonEncode({
        'schema_version': 1,
        'records': records,
        'max_rss_bytes': ProcessInfo.maxRss,
        'limits': 'isolated diagnostic primitives, not full pipeline cost; first repeat warmup; timings cannot be added to inclusive E1/native callback times',
      }),
    );
  });
}
