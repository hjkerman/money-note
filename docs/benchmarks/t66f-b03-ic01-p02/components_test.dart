@Timeout(Duration(minutes: 10))
library;

import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import 'original_sqlite.dart' as before;
import '../t66f-b02-implementation/verification_profile.dart';

final out = Directory(
  '${Directory.current.parent.path}/docs/benchmarks/t66f-b03-ic01-p02/evidence',
);
int cpu() {
  final s = File('/proc/self/stat')
      .readAsStringSync()
      .split(') ')
      .last
      .split(' ');
  return int.parse(s[11]) + int.parse(s[12]);
}

class TimedCosts extends SqlCosts {
  int ticks = 0, calls = 0;
  @override
  void add(String key, [int amount = 1]) {
    final w = Stopwatch()..start();
    super.add(key, amount);
    ticks += w.elapsedTicks;
    calls++;
  }
}

// Test-only timing delegate: native SQL is executed exactly once. Native time
// includes callbacks; callback time includes SqlCosts.add, never sum all three.
class TimedNative implements Database {
  TimedNative(this.inner);
  final Database inner;
  int nativeTicks = 0, statements = 0, callbackTicks = 0, callbacks = 0;
  T measure<T>(T Function() f) {
    final w = Stopwatch()..start();
    try {
      return f();
    } finally {
      nativeTicks += w.elapsedTicks;
      statements++;
    }
  }

  @override
  void execute(String sql, [List<Object?> p = const []]) =>
      measure(() => inner.execute(sql, p));
  @override
  ResultSet select(String sql, [List<Object?> p = const []]) =>
      measure(() => inner.select(sql, p));
  @override
  void createFunction({
    required String functionName,
    required ScalarFunction function,
    AllowedArgumentCount argumentCount = const AllowedArgumentCount.any(),
    bool deterministic = false,
    bool directOnly = true,
    bool subtype = false,
  }) => inner.createFunction(
    functionName: functionName,
    argumentCount: argumentCount,
    deterministic: deterministic,
    directOnly: directOnly,
    subtype: subtype,
    function: (args) {
      final w = Stopwatch()..start();
      try {
        return function(args);
      } finally {
        callbacks++;
        callbackTicks += w.elapsedTicks;
      }
    },
  );
  @override
  void close() => inner.close();
  @override
  bool get autocommit => inner.autocommit;
  @override
  int get updatedRows => inner.updatedRows;
  @override
  int get userVersion => inner.userVersion;
  @override
  set userVersion(int v) => inner.userVersion = v;
  @override
  Pointer<void> get handle => inner.handle;
  @override
  int get lastInsertRowId => inner.lastInsertRowId;
  @override
  DatabaseConfig get config => inner.config;
  @override
  dynamic noSuchMethod(Invocation i) =>
      throw UnsupportedError('P01 timing delegate: ${i.memberName}');
}

void main() {
  test('P01 actual 100k stratified E1 cold/reuse and validation paired costs', () {
    const source = String.fromEnvironment(
      'P02_SOURCE',
      defaultValue: '/tmp/mn-b02-independent-100000-z6ux9y53',
    );
    const profiling = false;
    final fixture = jsonDecode(
      File('$source/server/backend-fixture.json').readAsStringSync(),
    ) as Map;
    final manifest = ObservationManifest.fromBytes(
      utf8.encode(jsonEncode(fixture['manifest'])),
    );
    final path = Directory('$source/client/segmented-store-v1')
        .listSync()
        .whereType<File>()
        .single
        .path;
    final original = sqlite3.open(path, mode: OpenMode.readOnly);
    final entries = <({ObjectRef ref, List<int>? bytes})>[];
    final sampleKinds = <String, int>{}, fullKinds = <String, Object>{};
    try {
      for (final r in original.select(
        'SELECT kind,count(*) n,sum(length(body)) b,min(length(body)) lo,max(length(body)) hi FROM objects GROUP BY kind',
      )) {
        fullKinds[r['kind'] as String] = {
          'objects': r['n'],
          'bytes': r['b'],
          'minimum': r['lo'],
          'maximum': r['hi'],
        };
      }
      for (final pair in [
        ('index-leaf', 2048),
        ('index-node', 2048),
        ('snapshot-leaf', 4),
        ('snapshot-node', 1),
        ('raw-root', 1),
        ('index-root', 1),
        ('hot', 1),
        ('control', 1),
      ]) {
        final rows = original.select(
          'SELECT hash,body FROM objects WHERE kind=? ORDER BY hash LIMIT ?',
          [pair.$1, pair.$2],
        );
        sampleKinds[pair.$1] = rows.length;
        for (final r in rows) {
          final raw = r['body'] as Uint8List;
          entries.add((
            ref: ObjectRef.parse({'hash': r['hash'], 'bytes': '${raw.length}'}),
            bytes: raw,
          ));
        }
      }
    } finally {
      original.close();
    }
    final bytes = entries.fold<int>(0, (n, e) => n + e.bytes!.length);
    expect(bytes, lessThan(8 * 1048576));
    final cache = CacheNamespace.forTarget(
      'https://p01-synthetic.invalid',
      manifest.target,
    );
    final records = <Map<String, Object?>>[];
    final closedCaches = <Map<String, Object?>>[];
    final oracles = <String, Object>{};
    // 1 warmup + 5 alternating pairs. Diagnostic timing is separately labelled.
    for (var repeat = 0; repeat < 6; repeat++) {
      for (final mode
          in repeat.isEven
              ? ['off', 'original', 'reuse']
              : ['reuse', 'original', 'off']) {
        final enabled = mode != 'off';
        final root = Directory.systemTemp.createTempSync('mn-p01-components-');
        final c = LogicalCost();
        final dynamic sql = mode == 'original' ? before.SqlCosts() : SqlCosts();
        late TimedNative native;
        CostDatabase? diagnostic;
        final store = SegmentedClientStore.open(
          root,
          cache,
          acquisition: true,
          limits: largeVerificationStoreLimits,
          diagnosticDatabaseFactory: (p) {
            native = TimedNative(sqlite3.open(p));
            final Database delegate = native.inner;
            if (mode == 'original') return before.CostDatabase(delegate, sql);
            return enabled
                ? (diagnostic = CostDatabase(delegate, sql))
                : delegate;
          },
        );
        try {
          store.createStaging(
            '12345678-1234-4234-8234-123456789abc',
            manifest,
            DateTime.utc(2026, 10, 22),
          );
          for (final reuse in [false, true]) {
            if (reuse)
              store.createStaging(
                '22345678-1234-4234-8234-123456789abc',
                manifest,
                DateTime.utc(2026, 10, 22),
              );
            final beforeNative = native.nativeTicks,
                beforeCb = native.callbackTicks,
                beforeCalls = native.callbacks;
            final beforeStatements = native.statements,
                beforeAdd = sql is TimedCosts ? sql.ticks : 0,
                beforeAdds = sql is TimedCosts ? sql.calls : 0;
            final beforeTx = store.work.snapshot()['transactions'] ?? 0,
                beforeCpu = cpu();
            final clock = Stopwatch()..start();
            void run() {
              for (var i = 0; i < entries.length; i += 64) {
                final end = (i + 64).clamp(0, entries.length);
                final batch = entries
                    .sublist(i, end)
                    .map((e) => (ref: e.ref, bytes: reuse ? null : e.bytes))
                    .toList();
                expect(
                  batch.fold<int>(0, (n, e) => n + e.ref.byteLength),
                  lessThanOrEqualTo(1048576),
                );
                store.putVerifiedStagedBatch(
                  reuse
                      ? '22345678-1234-4234-8234-123456789abc'
                      : '12345678-1234-4234-8234-123456789abc',
                  batch,
                );
              }
            }

            enabled ? c.run(LogicalCostStage.e2, run) : run();
            final elapsed = clock.elapsedMicroseconds,
                cpuTicks = cpu() - beforeCpu;
            final watch = Stopwatch()..start();
            final snapshot = sql.snapshot();
            if (enabled) {
              final key = '$repeat/$reuse';
              final evidence = {
                'sql': snapshot,
                'primitive': c.snapshot(),
                'work': store.work.snapshot(),
              };
              if (oracles.containsKey(key)) {
                expect(evidence, oracles[key]);
              } else {
                oracles[key] = evidence;
              }
            }
            final snapshotUs = watch.elapsedMicroseconds;
            if (repeat > 0)
              records.add({
                'enabled': enabled,
                'mode': mode,
                'cache': diagnostic == null
                    ? null
                    : Map<String, int>.of(diagnostic!.statementReuse),
                'reuse': reuse,
                'repeat': repeat,
                'wall_us': elapsed,
                'cpu_ticks': cpuTicks,
                'native_ticks': native.nativeTicks - beforeNative,
                'callback_ticks': native.callbackTicks - beforeCb,
                'callback_calls': native.callbacks - beforeCalls,
                'add_ticks': (sql is TimedCosts ? sql.ticks : 0) - beforeAdd,
                'add_calls': (sql is TimedCosts ? sql.calls : 0) - beforeAdds,
                'statements': native.statements - beforeStatements,
                'transactions':
                    (store.work.snapshot()['transactions'] ?? 0) - beforeTx,
                'snapshot_us': snapshotUs,
                'sql': snapshot,
                'primitive': c.snapshot(),
                'work': store.work.snapshot(),
                'rss_bytes': ProcessInfo.currentRss,
              });
          }
          final d = sqlite3.open(store.path, mode: OpenMode.readOnly);
          try {
            final row = d
                .select('SELECT count(*) n,sum(length(body)) b FROM objects')
                .single;
            expect(row['n'], entries.length);
            expect(row['b'], bytes);
            final expected = {for (final e in entries) e.ref.hash: e.bytes};
            for (final stored in d.select('SELECT hash,body FROM objects')) {
              expect(stored['body'], expected[stored['hash']]);
            }
            if (enabled)
              expect(
                sql.values['e2/objects/INSERT/blobBytes/committed'],
                BigInt.from(bytes),
              );
          } finally {
            d.close();
          }
          c.close();
          expect(c.isClosed, true);
        } finally {
          final closeWatch = Stopwatch()..start();
          store.close();
          final closeUs = closeWatch.elapsedMicroseconds;
          if (diagnostic != null) {
            expect(
              diagnostic!.statementReuse['created'],
              diagnostic!.statementReuse['finalized'],
            );
          }
          closedCaches.add({
            'repeat': repeat,
            'mode': mode,
            'close_us': closeUs,
            'cache': diagnostic?.statementReuse,
          });
          root.deleteSync(recursive: true);
        }
      }
    }
    final validation = <Map<String, Object?>>[];
    for (var repeat = 0; repeat < 6; repeat++) {
      for (final enabled in repeat.isEven ? [false, true] : [true, false]) {
        final c = LogicalCost();
        final before = cpu();
        final clock = Stopwatch()..start();
        void verify() {
          for (final e in entries) {
            VerifiedObject.verify(e.bytes!, e.ref, cache);
          }
        }

        enabled ? c.run(LogicalCostStage.e2, verify) : verify();
        if (repeat > 0)
          validation.add({
            'enabled': enabled,
            'repeat': repeat,
            'wall_us': clock.elapsedMicroseconds,
            'cpu_ticks': cpu() - before,
            'primitive': c.snapshot(),
            'rss_bytes': ProcessInfo.currentRss,
          });
        c.close();
      }
    }
    out.createSync(recursive: true);
    File(
      '${out.path}/${const bool.fromEnvironment("P02_FINAL") ? "components-final-data" : "components-no-profiling"}.json',
    ).writeAsStringSync(
      jsonEncode({
        'schema_version': 1,
        'instrumentation_version': 'ic01-p02-cache32-v1',
        'fixture': {
          'source': source,
          'n': 100000,
          'h': null,
          'd': null,
          'original_cold_graph': fixture['graph'],
          'target': manifest.target.toJson(),
          'selection': 'kind/hash bounded subset of retained post-delta synthetic client; not full closure',
        },
        'extra_timing_profilers_enabled': profiling,
        'objects': entries.length,
        'bytes': bytes,
        'sample_kinds': sampleKinds,
        'full_retained_store_kinds': fullKinds,
        'records': records,
        'closed_caches': closedCaches,
        'validation': validation,
        'max_rss_bytes': ProcessInfo.maxRss,
        'stopwatch_frequency': Stopwatch().frequency,
        'cpu_ticks_per_second': 100,
        'profiling_limits': 'E1 timers include original verification/schema/commit. Native time includes callback time; callback time includes add time. Timing wrappers perturb both modes. No full E2 closure/HTTP/E3/E4 or 100k success claim.',
      }),
    );
  });
}
