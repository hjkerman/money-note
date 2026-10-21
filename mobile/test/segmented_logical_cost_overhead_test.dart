import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/logical_cost_sqlite.dart';
import 'support/offline_mode_fixtures.dart';

void main() {
  test('bounded paired diagnostic overhead and aggregate memory', () {
    final raw = utf8.encode('{"kind":"hot","text":"한 😀 é"}');
    final expected = objectHash('hot', raw);
    final samples = <String, List<int>>{
      'primitive_off_us': [],
      'primitive_on_us': [],
      'sql_off_us': [],
      'sql_on_us': [],
      'lineage_off_us': [],
      'lineage_on_us': []
    };
    var keys = 0;
    final baseline = baselineFixture(), legacy = OfflineStore();
    final lineage = legacy.recoveryLineageFingerprint(baseline);
    for (var repetition = 0; repetition < 13; repetition++) {
      for (final enabled in repetition.isEven ? [true, false] : [false, true]) {
        final c = LogicalCost();
        final timer = Stopwatch()..start();
        void primitives() {
          for (var i = 0; i < 1000; i++) {
            decodeC1(raw);
            expect(objectHash('hot', raw), expected);
          }
        }

        if (enabled) {
          c.run(LogicalCostStage.calibration, primitives);
        } else {
          primitives();
        }
        final elapsed = timer.elapsedMicroseconds;
        if (repetition >= 3) {
          samples[enabled ? 'primitive_on_us' : 'primitive_off_us']!
              .add(elapsed);
        }
        if (enabled) {
          keys = c.snapshot().length;
          expect(keys, lessThanOrEqualTo(8));
          expect(c.snapshot()['calibration/objectHash/calls'], '1000');
        }
        final native = sqlite3.openInMemory();
        final Database db = enabled ? CostDatabase(native, SqlCosts()) : native;
        db.execute('CREATE TABLE objects(k TEXT PRIMARY KEY,body BLOB)');
        timer.reset();
        c.run(LogicalCostStage.e1, () {
          db.execute('BEGIN');
          for (var i = 0; i < 200; i++) {
            db.execute('INSERT INTO objects VALUES (?,?)', ['$i', raw]);
          }
          db.execute('COMMIT');
        });
        final sqlElapsed = timer.elapsedMicroseconds;
        if (repetition >= 3) {
          samples[enabled ? 'sql_on_us' : 'sql_off_us']!.add(sqlElapsed);
        }
        expect(
            native
                .select('SELECT sum(length(body)) AS n FROM objects')
                .single['n'],
            200 * raw.length);
        db.close();
        timer.reset();
        void lineages() {
          for (var i = 0; i < 100; i++) {
            expect(legacy.recoveryLineageFingerprint(baseline), lineage);
          }
        }

        if (enabled) {
          c.run(LogicalCostStage.recovery, lineages);
        } else {
          lineages();
        }
        if (repetition >= 3) {
          samples[enabled ? 'lineage_on_us' : 'lineage_off_us']!
              .add(timer.elapsedMicroseconds);
        }
      }
    }
    const output = String.fromEnvironment('B03_OVERHEAD');
    if (output.isNotEmpty) {
      File(output).writeAsStringSync(jsonEncode({
        'schema_version': 1,
        'environment': 'HOST 3 warmup + 10 paired/alternating samples',
        'primitive_iterations': 1000,
        'sql_inserts': 200,
        'counter_keys_after_1000_objects': keys,
        'samples': samples,
        'max_process_rss_bytes': ProcessInfo.maxRss,
        'limits':
            '소형 in-memory 오버헤드. 100k lease 적합성·Dart heap·Android·physical I/O proof 아님'
      }));
    }
  });
}
