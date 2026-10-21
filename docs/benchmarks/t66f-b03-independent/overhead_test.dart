import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';

void main() {
  test('independent small and medium paired HOST diagnostic overhead', () {
    final ticksPerSecond = int.parse(
      '${Process.runSync('getconf', ['CLK_TCK']).stdout}'.trim(),
    );
    int cpuTicks() {
      final stat = File('/proc/self/stat').readAsStringSync();
      final fields = stat.substring(stat.lastIndexOf(')') + 2).split(' ');
      return int.parse(fields[11]) + int.parse(fields[12]);
    }

    final results = <String, dynamic>{};
    for (final profile in [
      ('small', 200, 64, 20),
      ('medium', 2000, 4096, 200),
    ]) {
      final raw = utf8.encode('{"kind":"hot","text":"${'x' * profile.$3}"}');
      final samples = <String, List<Map<String, int>>>{'on': [], 'off': []};
      for (var repeat = 0; repeat < 23; repeat++) {
        for (final enabled in repeat.isEven ? [true, false] : [false, true]) {
          final beforeRss = ProcessInfo.currentRss;
          final timer = Stopwatch()..start();
          final c = LogicalCost();
          final initUs = timer.elapsedMicroseconds;
          void primitives() {
            for (var i = 0; i < profile.$2; i++) {
              decodeC1(raw);
              objectHash('hot', raw);
            }
          }

          final primitiveCpuStart = cpuTicks();
          timer.reset();
          if (enabled) {
            c.run(LogicalCostStage.calibration, primitives);
          } else {
            primitives();
          }
          final primitiveUs = timer.elapsedMicroseconds;
          final primitiveCpuTicks = cpuTicks() - primitiveCpuStart;
          final native = sqlite3.openInMemory();
          timer.reset();
          final Database db = enabled
              ? CostDatabase(native, SqlCosts())
              : native;
          final databaseObserverInitUs = timer.elapsedMicroseconds;
          db.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');
          final sqlCpuStart = cpuTicks();
          timer.reset();
          void writes() {
            db.execute('BEGIN');
            for (var i = 0; i < profile.$4; i++) {
              db.execute('INSERT INTO payload VALUES (?,?)', ['$i', raw]);
            }
            db.execute('COMMIT');
          }

          if (enabled) {
            c.run(LogicalCostStage.e1, writes);
          } else {
            writes();
          }
          final sqlUs = timer.elapsedMicroseconds;
          final sqlCpuTicks = cpuTicks() - sqlCpuStart;
          expect(
            native.select('SELECT sum(length(b)) n FROM payload').single['n'],
            profile.$4 * raw.length,
          );
          timer.reset();
          db.close();
          final databaseCloseUs = timer.elapsedMicroseconds;
          timer.reset();
          c.close();
          final closeUs = timer.elapsedMicroseconds;
          if (repeat >= 3) {
            samples[enabled ? 'on' : 'off']!.add({
              'primitive_us': primitiveUs,
              'primitive_cpu_ticks': primitiveCpuTicks,
              'sql_us': sqlUs,
              'sql_cpu_ticks': sqlCpuTicks,
              'init_us': initUs,
              'close_us': closeUs,
              'database_observer_init_us': databaseObserverInitUs,
              'database_close_us': databaseCloseUs,
              'rss_delta_bytes': ProcessInfo.currentRss - beforeRss,
              'keys': c.snapshot().length,
            });
          }
        }
      }
      results[profile.$1] = {
        'iterations': profile.$2,
        'payload_bytes': raw.length,
        'rows': profile.$4,
        'samples': samples,
      };
    }
    File(
      '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-independent/evidence/overhead-independent-flutter-complete.json',
    ).writeAsStringSync(
      jsonEncode({
        'environment': 'HOST 3 warmup + 20 alternating pairs',
        'results': results,
        'maxrss_bytes': ProcessInfo.maxRss,
        'cpu_ticks_per_second': ticksPerSecond,
        'limits': 'CPU는 process 전체의 clock tick 분해능이다. heap allocation 미측정. RSS는 GC/공유 page 영향 포함. 100k나 device 결과가 아니다.',
      }),
    );
  });
}
