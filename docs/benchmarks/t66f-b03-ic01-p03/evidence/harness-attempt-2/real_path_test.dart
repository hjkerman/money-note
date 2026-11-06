@Timeout(Duration(minutes: 110))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../t66f-b02-implementation/verification_profile.dart';
import 'timing.dart';
import 'full_run.dart';

int cpuTicks() {
  final f = File('/proc/self/stat')
      .readAsStringSync()
      .split(') ')
      .last
      .split(' ');
  return int.parse(f[11]) + int.parse(f[12]);
}

void save(String p, Object? v) => File(p)
    .writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(v)}\n');

class PrefixTransport implements SegmentedTransport {
  PrefixTransport(this.inner, this.budget, this.onBoundary, {this.renewAt});
  final SegmentedTransport inner;
  final int budget;
  final int? renewAt;
  final Future<void> Function(bool renewal) onBoundary;
  int successful = 0,
      httpUs = 0,
      entityBytes = 0,
      requestBytes = 0,
      failures = 0;
  final rows = <Map<String, Object?>>[];
  @override
  String get origin => inner.origin;
  @override
  void checkSession() => inner.checkSession();
  @override
  Future<SyncReply> exchange(
    String method,
    String path,
    Uint8List? body,
    SyncCancellation cancel,
    int limit,
  ) async {
    if (path.endsWith('/objects')) {
      if (successful == budget) {
        await onBoundary(false);
        throw const SegmentedException('P03_PREFIX_END');
      }
      if (renewAt != null && successful == renewAt && !renewed) {
        renewed = true;
        await onBoundary(true);
      }
    }
    final w = Stopwatch()..start();
    final reply = await inner.exchange(method, path, body, cancel, limit);
    final elapsed = w.elapsedMicroseconds;
    httpUs += elapsed;
    entityBytes += reply.bytes.length;
    requestBytes += body?.length ?? 0;
    if (path.endsWith('/objects') && reply.status == 200) successful++;
    if (reply.status >= 400) failures++;
    rows.add({
      'method': method,
      'path': path,
      'status': reply.status,
      'http_us': elapsed,
      'response_bytes': reply.bytes.length,
      'request_bytes': body?.length ?? 0,
      'success_packets': successful,
    });
    return reply;
  }

  bool renewed = false;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('P03 bounded real 100k E2→E1 paired prefixes and authorized expiry renewal', () async {
    final repo = Directory.current.parent.path;
    final out = Directory('$repo/docs/benchmarks/t66f-b03-ic01-p03/evidence');
    final temp = Directory.systemTemp.createTempSync('mn-p03-real-');
    save('${out.path}/disposable-location.json', {
      'root': temp.path,
      'synthetic': true,
      'full_attempts': 0,
    });
    final process = await Process.start('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66f-b03-ic01-p03/server.py',
      '100000',
      '${temp.path}/server',
    ]);
    final errors = File('${out.path}/server-stderr.log').openWrite();
    process.stderr.listen(errors.add);
    final lines = StreamIterator(
      process.stdout.transform(utf8.decoder).transform(const LineSplitter()),
    );
    IOClient? client;
    Future<Map> command(Map r) async {
      process.stdin.writeln(jsonEncode(r));
      await process.stdin.flush();
      if (!await lines.moveNext().timeout(const Duration(seconds: 25)))
        throw StateError('P03 backend closed');
      return jsonDecode(lines.current) as Map;
    }

    final records = <Map<String, Object?>>[];
    try {
      expect(await lines.moveNext().timeout(const Duration(minutes: 30)), true);
      final initial = jsonDecode(lines.current) as Map;
      final fixture = initial['fixture'] as Map;
      final graph = fixture['graph'] as Map;
      expect(graph['objects'], 400532);
      expect(graph['canonical_bytes'], 261543083);
      expect(graph['raw_rows']['ledger_entries'], 100000);
      final history = jsonDecode(
        File(
          '/tmp/mn-b02-independent-100000-z6ux9y53/server/backend-fixture.json',
        ).readAsStringSync(),
      ) as Map;
      for (final key in [
        'objects',
        'canonical_bytes',
        'kinds',
        'kind_bytes',
        'edges',
        'max_depth',
        'max_fanout',
        'largest_object',
        'raw_rows',
        'fact_domains',
        'raw_value_sha256',
      ])
        expect(
          graph[key],
          history['graph'][key],
          reason: 'same original B02 fixture characteristic $key',
        );
      save('${out.path}/fixture.json', {
        'graph': graph,
        'target': fixture['manifest']['target'],
        'historical_target': history['manifest']['target'],
        'comparison': 'same seed, exact raw value digests/type/size/depth/count; new disposable namespace changes identities',
        'root_equal':
            fixture['manifest']['target']['sync_root'] ==
            history['manifest']['target']['sync_root'],
      });
      final origin = initial['origin'] as String,
          token = initial['token'] as String;
      final target = SyncTarget.parse(fixture['manifest']['target']);
      client = IOClient(
        HttpClient()
          ..badCertificateCallback = ((_, host, port) =>
              host == '127.0.0.1' && port == Uri.parse(origin).port),
      );
      final rawTransport = AuthenticatedSegmentedTransport(
        client: client,
        origin: origin,
        credential: () => token,
        timeout: const Duration(seconds: 60),
      );
      // One smaller warmup pair, then exactly three alternating measured pairs.
      final plan = <({String label, bool on, int packets, int? renewal})>[
        (label: 'warm-off', on: false, packets: 24, renewal: null),
        (label: 'warm-on', on: true, packets: 24, renewal: null),
        for (var repeat = 0; repeat < 3; repeat++)
          for (final on in repeat.isEven ? [false, true] : [true, false])
            (
              label: 'prefix-$repeat-${on ? 'on' : 'off'}',
              on: on,
              packets: 160,
              renewal: null,
            ),
        (label: 'renew-off', on: false, packets: 80, renewal: 48),
        (label: 'renew-on', on: true, packets: 80, renewal: 48),
      ];
      for (final p in plan) {
        final label = p.label;
        await command({'command': 'p03_mode', 'enabled': p.on, 'label': label});
        final c = LogicalCost(), sql = SqlCosts();
        CostDatabase? costDb;
        TimedDatabase? timedDb, callbackDb;
        final root = Directory('${temp.path}/$label')..createSync();
        final init = Stopwatch()..start();
        SegmentedClientStore openStore() => SegmentedClientStore.open(
          root,
          CacheNamespace.forTarget(origin, target),
          adapters: true,
          limits: largeVerificationStoreLimits,
          diagnosticDatabaseFactory: (path) {
            callbackDb = TimedDatabase(sqlite3.open(path));
            final Database selected = p.on
                ? (costDb = CostDatabase(callbackDb!, sql))
                : callbackDb!;
            return timedDb = TimedDatabase(selected);
          },
        );
        final store = p.on
            ? c.run(LogicalCostStage.setup, openStore)
            : openStore();
        final initUs = init.elapsedMicroseconds;
        expect(store.acceptedGeneration().id, isNull);
        final snapshots = <Map<String, Object?>>[];
        late PrefixTransport transport;
        late Stopwatch wall;
        Map<String, Object?> snapshot(String boundary) => {
          'boundary': boundary,
          'elapsed_us': wall.elapsedMicroseconds,
          'successful_packets': transport.successful,
          'http_us': transport.httpUs,
          'sql_us': timedDb!.sqlUs,
          'primitive': c.snapshot(),
          'sql': sql.snapshot(),
          'work': store.work.snapshot(),
          'cache': costDb == null
              ? null
              : Map<String, int>.from(costDb!.statementReuse),
          'rss_bytes': ProcessInfo.currentRss,
          'cpu_ticks': cpuTicks(),
        };
        transport = PrefixTransport(rawTransport, p.packets, (renewal) async {
          snapshots.add(
            snapshot(renewal ? 'before-clock-expiry' : 'prefix-end'),
          );
          if (renewal) {
            final t = Stopwatch()..start();
            final reply = await command({'command': 'p03_advance'});
            snapshots.add({
              'clock': reply,
              'command_us': t.elapsedMicroseconds,
            });
          }
        }, renewAt: p.renewal);
        final baselineSql = timedDb!.sqlUs,
            baselineCallback = callbackDb!.callbackUs,
            cpuStart = cpuTicks();
        wall = Stopwatch()..start();
        Object? failure;
        try {
          final fetch = IncrementalFetcher(
            store,
            transport,
            limits: largeVerificationFetchLimits,
          );
          if (p.on) {
            await c.run(LogicalCostStage.e2, () => fetch.acquire());
          } else {
            await fetch.acquire();
          }
        } catch (e) {
          failure = e;
        }
        final wallUs = wall.elapsedMicroseconds;
        final cpu = cpuTicks() - cpuStart;
        expect(failure, isA<AcquisitionFailure>());
        expect((failure as AcquisitionFailure).code, 'P03_PREFIX_END');
        final snapshotClock = Stopwatch()..start();
        final primitive = c.snapshot(),
            sqlSnapshot = sql.snapshot(),
            work = store.work.snapshot();
        final snapshotUs = snapshotClock.elapsedMicroseconds;
        final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
        final summary = db
            .select('SELECT count(*) n,sum(length(body)) bytes FROM objects')
            .single;
        final kinds = db
            .select(
              'SELECT kind,count(*) n,sum(length(body)) bytes,min(length(body)) min_bytes,max(length(body)) max_bytes FROM objects GROUP BY kind',
            )
            .map((r) => Map<String, Object?>.from(r))
            .toList();
        final hashes = db
            .select('SELECT hash FROM objects ORDER BY hash')
            .map((r) => r['hash'])
            .toList();
        final accepted = store.acceptedGeneration().id;
        db.close();
        final objects = summary['n'] as int, payload = summary['bytes'] as int;
        expect(objects, greaterThan(0));
        expect(accepted, isNull);
        if (p.on) {
          expect(
            sql.values['e2/objects/INSERT/effective/rows'],
            BigInt.from(objects),
          );
          for (final key in [
            'attempted/blobBytes',
            'effective/blobBytes',
            'blobBytes/committed',
          ])
            expect(sql.values['e2/objects/INSERT/$key'], BigInt.from(payload));
          final minHash =
              payload +
              kinds.fold<int>(
                0,
                (n, r) =>
                    n +
                    (r['n'] as int) *
                        (ascii
                                .encode('money-note.sync.v1/${r['kind']}')
                                .length +
                            1),
              );
          expect(
            BigInt.parse(primitive['e2/objectHash/hashInputBytes']!),
            greaterThanOrEqualTo(BigInt.from(minHash)),
          );
          expect(
            BigInt.parse(primitive['e2/c1/submittedBytes']!),
            greaterThanOrEqualTo(BigInt.from(payload)),
          );
        } else {
          expect(primitive, isEmpty);
          expect(sqlSnapshot, isEmpty);
        }
        final close = Stopwatch()..start();
        store.close();
        c.close();
        final closeUs = close.elapsedMicroseconds;
        expect(c.isClosed, true);
        if (costDb != null) {
          expect(
            costDb!.statementReuse['created'],
            costDb!.statementReuse['finalized'],
          );
          expect(costDb!.statementReuse['peakLive'], lessThanOrEqualTo(32));
        }
        final backend = await command({'command': 'p03_snapshot'});
        expect(backend['pending'], 0);
        expect(backend['complete'], true);
        final row = <String, Object?>{
          'label': label,
          'enabled': p.on,
          'warmup': label.startsWith('warm'),
          'renewal': p.renewal != null,
          'packet_budget': p.packets,
          'wall_us': wallUs,
          'cpu_ticks': cpu,
          'http_us': transport.httpUs,
          'sql_us': timedDb!.sqlUs - baselineSql,
          'sql_observer_callback_us': p.on
              ? callbackDb!.callbackUs - baselineCallback
              : null,
          'sql_observer_scope':
              'TEMP row callback only, lower bound; inclusive inside SQL wall',
          'residual_e2_us':
              wallUs - transport.httpUs - (timedDb!.sqlUs - baselineSql),
          'collector_store_init_us': initUs,
          'snapshot_us': snapshotUs,
          'close_us': closeUs,
          'objects': objects,
          'reused_objects': 'no new object duplicates; continuation traversal reuse in work map',
          'payload_bytes': payload,
          'response_bytes': transport.entityBytes,
          'request_bytes': transport.requestBytes,
          'http_failures': transport.failures,
          'kinds': kinds,
          'primitive': primitive,
          'sql': sqlSnapshot,
          'work': work,
          'cache_closed': costDb?.statementReuse,
          'snapshots': snapshots,
          'requests': transport.rows,
          'rss_bytes': ProcessInfo.currentRss,
          'process_peak_rss': ProcessInfo.maxRss,
          'accepted': accepted,
          'expected_stop': 'P03_PREFIX_END',
          'complete_executed_counter_scope': true,
        };
        save('${out.path}/$label.json', row);
        save('${out.path}/$label-hashes.json', hashes);
        records.add(row);
        save('${out.path}/prefix-progress.json', {
          'completed': records.length,
          'last': label,
          'full_attempts': 0,
        });
        await command({
          'command': 'p03_mode',
          'enabled': false,
          'label': 'idle',
        });
      }
      final backend = await command({'command': 'p03_snapshot'});
      save('${out.path}/backend-snapshot.json', backend);
      save('${out.path}/prefix-results.json', {
        'records': records,
        'fixture': graph,
        'full_100k_attempts': 0,
        'host_peak_rss': ProcessInfo.maxRss,
      });
      save('${out.path}/prefix-ready.json', {
        'ready': true,
        'full_attempts': 0,
      });
      final decisionFile = File('${out.path}/decision.json');
      final wait = Stopwatch()..start();
      while (!decisionFile.existsSync() &&
          wait.elapsed < const Duration(minutes: 10)) {
        await Future<void>.delayed(const Duration(seconds: 1));
      }
      expect(
        decisionFile.existsSync(),
        true,
        reason: 'finite controller decision required',
      );
      final decision = jsonDecode(decisionFile.readAsStringSync()) as Map;
      Object? fullFailure;
      if (decision['decision'] == 'GO') {
        await command({'command': 'p03_real_clock'});
        await command({
          'command': 'p03_mode',
          'enabled': true,
          'label': 'full',
        });
        try {
          await fullRun(temp, out, initial, client);
        } catch (error) {
          fullFailure = error;
        }
        save(
          '${out.path}/full-backend-snapshot.json',
          await command({'command': 'p03_snapshot'}),
        );
      } else {
        expect(['NO-GO', 'INCONCLUSIVE'], contains(decision['decision']));
      }
      client.close();
      await command({'command': 'exit'});
      expect(await process.exitCode.timeout(const Duration(seconds: 30)), 0);
      if (fullFailure != null) fail('$fullFailure');
    } finally {
      client?.close();
      await process.stdin.close();
      if (await process.exitCode.timeout(
            const Duration(seconds: 2),
            onTimeout: () => -999,
          ) ==
          -999) {
        process.kill();
        await process.exitCode.timeout(
          const Duration(seconds: 10),
          onTimeout: () {
            process.kill(ProcessSignal.sigkill);
            return -999;
          },
        );
      }
      await lines.cancel();
      await errors.close();
      // Keep only this synthetic disposable store/trace for independent reopening.
    }
  });
}
