@Timeout(Duration(minutes: 12))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../t66f-b02-implementation/verification_profile.dart';
import '../t66f-b03-ic01-p03/timing.dart';

final here =
    '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-ic01-p04';
void save(String name, Object value) => File(
  '$here/evidence/$name',
).writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(value)}\n');
int cpu() {
  final fields = File('/proc/self/stat')
      .readAsStringSync()
      .split(') ')
      .last
      .split(' ');
  return int.parse(fields[11]) + int.parse(fields[12]);
}

void main() {
  test(
    'P04 matched late-store E1 component; NOT an authorized HTTP tail',
    () async {
      final plan = jsonDecode(
        File('$here/evidence/clone-plan.json').readAsStringSync(),
      ) as Map;
      final target = SyncTarget.parse((plan['manifest'] as Map)['target']);
      final origin =
          (jsonDecode(
                File('$here/evidence/recovered-synthetic-origin.json')
                    .readAsStringSync(),
              ) as Map)['origin']
              as String;
      final cache = CacheNamespace.forTarget(origin, target);
      final manifest = ObservationManifest.fromBytes(
        utf8.encode(jsonEncode(plan['manifest'])),
      );
      final all = (plan['entries'] as List).cast<Map>();
      const localStage = '22222222-2222-4222-8222-222222222222';
      final records = <Map<String, Object?>>[];
      final enabledEvidence = <int, Map<String, Object?>>{};
      final cases = <Map>[
        ...(plan['clones'] as List).cast<Map>().where(
          (x) => (x['name'] as String).startsWith('smoke'),
        ),
        for (var repeat = 0; repeat < 2; repeat++)
          for (final mode
              in repeat == 0 ? ['A', 'B', 'D', 'C'] : ['C', 'D', 'B', 'A'])
            {
              ...(plan['clones'] as List).cast<Map>().singleWhere(
                (x) => x['name'] == mode,
              ),
              'repeat': repeat,
            },
      ];
      for (final task in cases) {
        final reset = await Process.run(
          '${Directory.current.parent.path}/.venv/bin/python',
          ['$here/reset_clone.py', task['path'] as String],
        );
        expect(reset.exitCode, 0, reason: '${reset.stderr}');
        final beforeProof = jsonDecode(reset.stdout as String) as Map;
        expect(beforeProof['logical'], plan['source_logical']);
        final mode = task['mode'] as String, repeat = task['repeat'] as int;
        final logical = mode == 'B' || mode == 'D';
        final timing = mode == 'C' || mode == 'D';
        final c = LogicalCost(), sql = SqlCosts();
        CostDatabase? costDb;
        TimedDatabase? outer, callback;
        final opening = Stopwatch()..start();
        final store = SegmentedClientStore.open(
          Directory(task['root'] as String),
          cache,
          adapters: true,
          limits: largeVerificationStoreLimits,
          diagnosticDatabaseFactory: (path) {
            expect(path, task['path']);
            Database d = sqlite3.open(path);
            if (timing && logical) d = callback = TimedDatabase(d);
            if (logical) d = costDb = CostDatabase(d, sql);
            if (timing) d = outer = TimedDatabase(d);
            return d;
          },
        );
        final openUs = opening.elapsedMicroseconds;
        // Local E1 storage fixture ONLY. No HTTP/acquire/publication is called;
        // this old manifest is never used as current observation authorization.
        store.createStaging(localStage, manifest, DateTime.utc(2026, 10, 23));
        final beforeSql = outer?.sqlUs, beforeCallbacks = callback?.callbackUs;
        final beforeCalls = outer?.calls;
        final txBefore = store.work.snapshot()['transactions'] ?? 0;
        final cpuBefore = cpu(), rssBefore = ProcessInfo.currentRss;
        final wall = Stopwatch()..start();
        void work() {
          final entries = all.take(task['n'] as int).toList();
          for (var i = 0; i < entries.length; i += 64) {
            store.putVerifiedStagedBatch(
              localStage,
              entries
                  .sublist(i, (i + 64).clamp(0, entries.length))
                  .map(
                    (r) => (
                      ref: ObjectRef.parse({
                        'hash': r['hash'],
                        'bytes': r['bytes'],
                      }),
                      bytes: null,
                    ),
                  )
                  .toList(),
            );
          }
        }

        logical ? c.run(LogicalCostStage.e2, work) : work();
        final elapsed = wall.elapsedMicroseconds, cpuTicks = cpu() - cpuBefore;
        final snapshotClock = Stopwatch()..start();
        final primitive = logical ? c.snapshot() : null;
        final sqlMap = logical ? sql.snapshot() : null;
        final workMap = store.work.snapshot();
        final snapshotUs = snapshotClock.elapsedMicroseconds;
        if (logical && repeat >= 0) {
          final evidence = {
            'primitive': primitive,
            'sql': sqlMap,
            'work': workMap,
          };
          if (enabledEvidence.containsKey(repeat)) {
            expect(evidence, enabledEvidence[repeat]);
          } else {
            enabledEvidence[repeat] = evidence;
          }
        }
        final native = sqlite3.open(store.path, mode: OpenMode.readOnly);
        final rows = native
            .select('SELECT count(*) n,sum(length(body)) bytes FROM objects')
            .single;
        expect(rows['n'], 397146);
        expect(rows['bytes'], 259743775);
        expect(
          native
              .select('SELECT current_id,previous_id,sequence FROM accepted')
              .single
              .values
              .toList(),
          [null, null, 0],
        );
        final links = native.select(
          'SELECT count(*) n,sum(length(CAST(staging_id AS BLOB))+length(CAST(hash AS BLOB))) bytes FROM staging_objects WHERE staging_id=?',
          [localStage],
        ).single;
        expect(links['n'], task['n']);
        expect(links['bytes'], (task['n'] as int) * 100);
        if (logical) {
          expect(
            sqlMap!['e2/staging_objects/INSERT/effective/rows'],
            '${task['n']}',
          );
          expect(
            sqlMap['e2/staging_objects/INSERT/textBytes/committed'],
            '${links['bytes']}',
          );
        }
        native.close();
        final close = Stopwatch()..start();
        store.close();
        c.close();
        final closeUs = close.elapsedMicroseconds;
        if (costDb != null) {
          expect(
            costDb!.statementReuse['created'],
            costDb!.statementReuse['finalized'],
          );
          expect(costDb!.statementReuse['peakLive'], lessThanOrEqualTo(32));
          expect(costDb!.statementReuse['capacityRejections'], 0);
        }
        records.add({
          'name': task['name'],
          'mode': mode,
          'repeat': repeat,
          'n': task['n'],
          'scope': 'E1 local re-staging of ALREADY STORED objects; not missing-object acquisition',
          'logical': logical,
          'extra_timing': timing,
          'wall_us': elapsed,
          'cpu_ticks_100Hz': cpuTicks,
          'open_us': openUs,
          'snapshot_us': snapshotUs,
          'close_us': closeUs,
          'sql_api_us': outer == null ? null : outer!.sqlUs - beforeSql!,
          'sql_api_calls': outer == null ? null : outer!.calls - beforeCalls!,
          'callback_us_lower_bound': callback == null
              ? null
              : callback!.callbackUs - beforeCallbacks!,
          'primitive_status': logical ? 'MEASURED' : 'NOT INSTRUMENTED',
          'primitive': primitive,
          'sql': sqlMap,
          'work': workMap,
          'transactions': (workMap['transactions'] ?? 0) - txBefore,
          'rss_before': rssBefore,
          'rss_after': ProcessInfo.currentRss,
          'process_lifetime_max_rss': ProcessInfo.maxRss,
          'cache_closed': costDb?.statementReuse,
          'collector_closed': c.isClosed,
          'object_count': rows['n'],
          'new_object_downloads': null,
          'http_status': 'NOT RUN',
          'local_new_staging_links': links['n'],
          'local_new_staging_text_bytes': links['bytes'],
          'clone_initial': beforeProof,
        });
        save('component-results.json', records);
      }
      expect(records.length, 10);
    },
  );
}
