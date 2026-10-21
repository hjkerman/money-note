@Timeout(Duration(minutes: 15))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/adapters.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-phase-b/harness.dart';
import 'support/logical_cost_sqlite.dart';
import 'support/offline_mode_fixtures.dart';

class CostBackend {
  CostBackend(this.process, this.lines, this.initial);
  final Process process;
  final StreamIterator<String> lines;
  final Map<String, dynamic> initial;
  static Future<CostBackend> start(int history) async {
    final root = Directory.current.parent.path;
    final process = await Process.start('$root/.venv/bin/python',
        ['$root/docs/benchmarks/t66f-b03/server.py', '$history']);
    final errors = StringBuffer();
    process.stderr.transform(utf8.decoder).listen(errors.write);
    final lines = StreamIterator(
        process.stdout.transform(utf8.decoder).transform(const LineSplitter()));
    if (!await lines.moveNext().timeout(const Duration(minutes: 3))) {
      throw StateError('B03 synthetic TLS startup: $errors');
    }
    return CostBackend(
        process, lines, jsonDecode(lines.current) as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> command(Map<String, dynamic> value) async {
    process.stdin.writeln(jsonEncode(value));
    if (!await lines.moveNext().timeout(const Duration(minutes: 3))) {
      throw StateError('B03 synthetic TLS ended');
    }
    return jsonDecode(lines.current) as Map<String, dynamic>;
  }

  Future<void> close() async {
    await command({'command': 'exit'});
    await process.stdin.close();
    expect(await process.exitCode.timeout(const Duration(seconds: 30)), 0);
    await lines.cancel();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  for (final n in [9, 260]) {
    test(
        'B03 real TLS D→E calibrated stages, identical, delta and fresh process N=$n',
        () async {
      final backend = await CostBackend.start(n);
      final h = await RealHarness.create(RealBackend.remote(backend.initial));
      final collector = LogicalCost(), sql = SqlCosts();
      final cache = h.store.cache;
      h.store.close();
      h.store = SegmentedClientStore.open(h.root, cache,
          adapters: true,
          diagnosticDatabaseFactory: (p) => CostDatabase(sqlite3.open(p), sql));
      final phases = <String, dynamic>{};
      try {
        Future<void> publish(String name) async {
          final started = Stopwatch()..start();
          final result = await collector.run(LogicalCostStage.e2,
              () => h.state.publishSegmentedForIsolatedUse(h.store));
          phases[name] = {
            'generation': result.generationId,
            'sequence': result.sequence,
            'publication_transaction_microseconds':
                result.transactionMicroseconds,
            'publication_readback_microseconds': result.readbackMicroseconds,
            'microseconds': started.elapsedMicroseconds,
            'existing_work': h.store.work.snapshot(),
            'primitive': collector.snapshot(),
            'sqlite': sql.snapshot(),
            'backend': (await backend.command({'command': 'cost'}))['counters']
          };
        }

        await publish('cold');
        final accepted = h.store.acceptedGeneration();
        expect(accepted.manifest!.target.syncRoot,
            backend.initial['fixture']['manifest']['target']['sync_root']);
        final expected = backend.initial['fixture']['objects'] as List;
        final independent = sqlite3.open(h.store.path);
        for (final item in expected) {
          expect(
              independent.select('SELECT body FROM objects WHERE hash=?',
                  [item['ref']['hash']]).single['body'],
              base64Decode(item['data_base64'] as String));
        }
        expect(independent.select('PRAGMA foreign_key_check'), isEmpty);
        independent.close();
        expect(collector.snapshot().keys.any((k) => k.startsWith('e3Verify/')),
            true);
        expect(collector.snapshot().keys.any((k) => k.startsWith('e3Commit/')),
            true);
        expect(sql.values['e2/objects/INSERT/effective/rows'],
            BigInt.from(expected.length));
        final uniqueBytes = expected.fold<int>(
            0, (sum, item) => sum + int.parse(item['ref']['bytes'] as String));
        expect(sql.values['e2/objects/INSERT/blobBytes/committed'],
            BigInt.from(uniqueBytes));
        final beforeInsert = sql.values['e2/objects/INSERT/effective/rows'];
        await publish('identical');
        expect(h.store.acceptedGeneration().id, accepted.id);
        expect(sql.values['e2/objects/INSERT/effective/rows'], beforeInsert);
        await backend.command({'command': 'mutate', 'op': 'update'});
        await publish('delta');
        final current = h.store.acceptedGeneration();
        expect(current.sequence, accepted.sequence + 1);
        final beforeRead = sql.snapshot();
        collector.run(LogicalCostStage.e4Read, () {
          for (var i = 0; i < 3; i++) {
            h.store.withAcceptedRead(current, (r) {
              expect(r.rows('ledger_entries', limit: 3), isNotEmpty);
              expect(r.hot['state'], isA<Map>());
            });
          }
        });
        expect(
            sql.values.keys.where(
                (k) => k.startsWith('e4Read/') && k.contains('/effective/')),
            isEmpty);
        phases['read'] = {
          'primitive': collector.snapshot(),
          'sqlite': sql.snapshot(),
          'before_sql': beforeRead
        };
        final proof = await collector.run(LogicalCostStage.e4Legacy,
            () => h.store.verifyAcceptedForMaterialization(current));
        collector.run(LogicalCostStage.e4Legacy, () {
          final bundle = h.store.withAcceptedRead(
              current, (r) => materializeLegacyRead(r, baselineFixture().user),
              materializationProof: proof);
          expect(bundle.envelope.fingerprint,
              isNot(current.manifest!.target.syncRoot));
        });
        expect(
            collector
                .snapshot()
                .keys
                .any((k) => k.startsWith('e4Legacy/legacyHash/')),
            true);
        final freshInput = File('${h.root.path}/b03-fresh.json')
          ..writeAsStringSync(jsonEncode({
            'root': h.root.path,
            'origin': backend.initial['origin'],
            'target': current.manifest!.target.toJson()
          }));
        final child = await Process.run('/home/hjkerman/.flutter/bin/dart',
            ['run', 'test/support/logical_cost_reopen.dart', freshInput.path]);
        expect(child.exitCode, 0, reason: '${child.stderr}');
        final fresh = jsonDecode(child.stdout as String) as Map;
        expect(fresh['sync_root'], current.manifest!.target.syncRoot);
        expect(fresh['rows_read'], 3);
        phases['final'] = {
          'primitive': collector.snapshot(),
          'sqlite': sql.snapshot(),
          'backend': (await backend.command({'command': 'cost'}))['counters'],
          'fresh_process': fresh
        };
        const output = String.fromEnvironment('B03_OUTPUT');
        if (output.isNotEmpty) {
          File('$output-n$n.json').writeAsStringSync(jsonEncode({
            'schema_version': 1,
            'instrumentation_version': 't66f-b03/1',
            'run_id': 'b03-small-real-tls-$n',
            'fixture': {
              'history_rows': n,
              'H': null,
              'D': 1,
              'N': (backend.initial['fixture']['source']['ledger_entries']
                      as List)
                  .length,
              'profile': 'original-phase-b-small-not-fixed-H-grid'
            },
            'environment': 'HOST synthetic TLS/SQLite',
            'coverage':
                'SHA256/C1 and SQL row TEXT/BLOB; scalar counts separate; exclusive caller stages',
            'exclusions': [
              'physical I/O',
              'TLS crypto',
              'R1',
              'five-point cost proof'
            ],
            'phases': phases
          }));
        }
      } finally {
        h.dispose();
        await backend.close();
      }
    });
  }
  test(
      'actual concurrent TLS requests have exclusive local scopes and exact aggregate',
      () async {
    final backend = await CostBackend.start(0);
    final clients = <HttpClient>[];
    try {
      Future<Map> observe() async {
        final io = HttpOverrides.runWithHttpOverrides(
            () => HttpClient(), RealHttpOverrides());
        clients.add(io);
        io.badCertificateCallback = (_, host, port) =>
            host == '127.0.0.1' &&
            port == Uri.parse(backend.initial['origin']).port;
        final req = await io.postUrl(
            Uri.parse('${backend.initial['origin']}/api/sync/v1/observations'));
        req.headers.set('Authorization', 'Bearer ${backend.initial['token']}');
        req.headers.set('Content-Type', 'application/json');
        req.headers.set('X-B03-Barrier', 'pair');
        req.write(jsonEncode({
          'protocol': 1,
          'request_id': syncUuid(),
          'base': null,
          'inline_bytes': 0
        }));
        final response = await req.close();
        final raw = await response.transform(utf8.decoder).join();
        expect(response.statusCode, 201, reason: raw);
        expect(response.headers.value('cache-control'), 'no-store');
        return jsonDecode(raw) as Map;
      }

      final inFlight = Future.wait([observe(), observe()]);
      // Ask before awaiting HTTP completion. The diagnostic snapshot must wait
      // for this exact request cohort and its native tails, not return a prefix.
      final measured =
          backend.command({'command': 'cost', 'after_requests': 2});
      final manifests = await inFlight;
      expect(manifests[0]['observation_id'],
          isNot(manifests[1]['observation_id']));
      expect(manifests[0]['target'], manifests[1]['target']);
      final evidence = await measured;
      final samples = (evidence['request_samples'] as List).cast<Map>();
      expect(evidence['request_count'], 2);
      expect(evidence['completed_requests'], 2);
      expect(evidence['measurement_complete'], isTrue);
      expect(evidence['request_sample_capacity'], 16);
      expect(samples.map((s) => s['request']).toSet(), {1, 2});
      final aggregate = (evidence['counters'] as Map).cast<String, String>();
      final expected = <String, BigInt>{};
      for (final sample in samples) {
        expect(sample['status'], 201);
        final counters = (sample['counters'] as Map).cast<String, String>();
        expect(BigInt.parse(counters['observation/sha256/calls']!),
            greaterThan(BigInt.zero));
        for (final e in counters.entries) {
          expect(e.key.startsWith('observation/'), true);
          expected[e.key] =
              (expected[e.key] ?? BigInt.zero) + BigInt.parse(e.value);
        }
      }
      expect({
        for (final e
            in aggregate.entries.where((e) => e.key.startsWith('observation/')))
          e.key: BigInt.parse(e.value)
      }, expected);
      const out = String.fromEnvironment('B03_OUTPUT');
      if (out.isNotEmpty) {
        File('$out-concurrent.json').writeAsStringSync(jsonEncode(evidence));
      }
    } finally {
      for (final c in clients) {
        c.close(force: true);
      }
      await backend.close();
    }
  });
}
