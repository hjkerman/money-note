@Timeout(Duration(hours: 2))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../t66f-b02-implementation/verification_profile.dart';
import '../t66f-b03-ic01-p03/timing.dart';

void save(String p, Object? value) => File(
  p,
).writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(value)}\n');

class Loopback extends HttpOverrides {}

IOClient freshHttp(String origin) {
  final native = HttpOverrides.runWithHttpOverrides(
    () => HttpClient(),
    Loopback(),
  )..maxConnectionsPerHost = 1;
  native.badCertificateCallback = (_, host, port) =>
      host == '127.0.0.1' && port == Uri.parse(origin).port;
  return IOClient(native);
}

class BodyResponse extends IOStreamedResponse {
  BodyResponse(this.original, Stream<List<int>> stream)
    : super(
        stream,
        original.statusCode,
        contentLength: original.contentLength,
        request: original.request,
        headers: original.headers,
        isRedirect: original.isRedirect,
        persistentConnection: original.persistentConnection,
        reasonPhrase: original.reasonPhrase,
      );
  final IOStreamedResponse original;
  @override
  Future<Socket> detachSocket() => original.detachSocket();
}

class HttpTimes extends http.BaseClient {
  HttpTimes(this.inner, this.progress);
  IOClient inner;
  final void Function(int) progress;
  int issued = 0,
      done = 0,
      headerUs = 0,
      bodyUs = 0,
      bytes = 0,
      errors = 0,
      failedUs = 0;
  Map<String, int> snap() => {
    'issued': issued,
    'complete_bodies': done,
    'header_us': headerUs,
    'send_to_complete_body_us': bodyUs,
    'response_entity_bytes': bytes,
    'errors': errors,
    'failed_send_us': failedUs,
  };
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final w = Stopwatch()..start();
    issued++;
    if (issued % 128 == 0) progress(issued);
    try {
      final response = await inner.send(request);
      headerUs += w.elapsedMicroseconds;
      final stream = response.stream.transform(
        StreamTransformer<List<int>, List<int>>.fromHandlers(
          handleData: (v, s) {
            bytes += v.length;
            s.add(v);
          },
          handleError: (Object e, StackTrace st, s) {
            errors++;
            s.addError(e, st);
          },
          handleDone: (s) {
            done++;
            bodyUs += w.elapsedMicroseconds;
            s.close();
          },
        ),
      );
      return BodyResponse(response, stream);
    } catch (_) {
      errors++;
      failedUs += w.elapsedMicroseconds;
      rethrow;
    }
  }

  @override
  void close() => inner.close();
}

Map<String, int> diff(Map<String, int> a, Map<String, int> b) => {
  for (final k in {...a.keys, ...b.keys}) k: (a[k] ?? 0) - (b[k] ?? 0),
};
int cpuTicks() {
  final f = File('/proc/self/stat')
      .readAsStringSync()
      .split(') ')
      .last
      .split(' ');
  return int.parse(f[11]) + int.parse(f[12]);
}

Map<String, Object?> accepted(AcceptedGeneration a) => {
  'id': a.id,
  'sequence': a.sequence,
  'previous_id': a.previousId,
  'target': a.manifest?.target.toJson(),
};
Map<String, int> dbState(String path) {
  final db = sqlite3.open(path, mode: OpenMode.readOnly);
  try {
    return {
      'objects': db.select('SELECT count(*) n FROM objects').single['n'] as int,
      'body_bytes':
          db
                  .select('SELECT coalesce(sum(length(body)),0) n FROM objects')
                  .single['n']
              as int,
      'generations':
          db.select('SELECT count(*) n FROM generations').single['n'] as int,
    };
  } finally {
    db.close();
  }
}

class Client {
  Client(
    this.on,
    this.root,
    this.store,
    this.state,
    this.http,
    this.outer,
    this.callback,
    this.sql,
    this.costDb,
  );
  final bool on;
  final Directory root;
  final SegmentedClientStore store;
  final AppState state;
  final HttpTimes http;
  final TimedDatabase outer;
  final TimedDatabase? callback;
  final SqlCosts sql;
  final CostDatabase? costDb;
  static Future<Client> create(
    bool on,
    Map init,
    Directory root,
    void Function(int) progress,
  ) async {
    expect(root.existsSync(), false);
    root.createSync();
    final s = SqlCosts();
    TimedDatabase? outer, cb;
    CostDatabase? costDb;
    final target = SyncTarget.parse(init['fixture']['manifest']['target']);
    final setup = LogicalCost();
    SegmentedClientStore open() => SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(init['origin'], target),
      adapters: true,
      limits: largeVerificationStoreLimits,
      diagnosticDatabaseFactory: (p) {
        final native = sqlite3.open(p);
        if (on) {
          cb = TimedDatabase(native);
          costDb = CostDatabase(cb!, s);
          return outer = TimedDatabase(costDb!);
        }
        return outer = TimedDatabase(native);
      },
    );
    final store = on ? setup.run(LogicalCostStage.setup, open) : open();
    setup.close();
    final native = HttpOverrides.runWithHttpOverrides(
      () => HttpClient(),
      Loopback(),
    )..maxConnectionsPerHost = 1;
    native.badCertificateCallback = (_, host, port) =>
        host == '127.0.0.1' && port == Uri.parse(init['origin']).port;
    final http = HttpTimes(IOClient(native), progress);
    final api = MoneyNoteApiClient(client: http, baseUrl: init['origin']);
    await api.saveSession(init['token']);
    final legacy = OfflineStore(directoryProvider: () async => root);
    await legacy.replaceBaseline(baselineFixture());
    await legacy.beginOnlineWrite(1);
    final state = AppState(api, offlineStore: legacy)
      ..user = baselineFixture().user;
    return Client(on, root, store, state, http, outer!, cb, s, costDb);
  }

  void close() {
    state.dispose();
    store.close();
    http.close();
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('B04 동결 소스 실제 고정 H/D 비용·ON/OFF', () async {
    const n = int.fromEnvironment('B04_N');
    const out = String.fromEnvironment('B04_OUT');
    const scratch = String.fromEnvironment('B04_SCRATCH');
    final tree = Directory.current.parent.path;
    expect([1000, 5000, 10000, 50000], contains(n));
    final output = Directory(out)..createSync(recursive: true);
    FlutterSecureStorage.setMockInitialValues({});
    final process = await Process.start(
      '$tree/.venv/bin/python',
      ['$tree/docs/benchmarks/t66f-b04/server.py', '$n', '$out/server'],
      environment: {
        'B04_TREE': tree,
        'TMPDIR': '$scratch/disposable',
        'PYTHONDONTWRITEBYTECODE': '1',
      },
    );
    final err = File('$out/server.stderr').openWrite();
    process.stderr.listen(err.add);
    final lines = StreamIterator(
      process.stdout.transform(utf8.decoder).transform(const LineSplitter()),
    );
    Future<Map<String, dynamic>> command(Map<String, Object?> v) async {
      process.stdin.writeln(jsonEncode(v));
      await process.stdin.flush();
      expect(await lines.moveNext().timeout(const Duration(minutes: 10)), true);
      return jsonDecode(lines.current) as Map<String, dynamic>;
    }

    final clients = <bool, Client>{};
    final results = <Map<String, Object?>>[];
    String phase = 'startup';
    Object? failure;
    try {
      expect(await lines.moveNext().timeout(const Duration(minutes: 30)), true);
      final init = jsonDecode(lines.current) as Map;
      save('$out/fixture.json', init['fixture']);
      final coldOrder = (n == 1000 || n == 10000)
          ? [false, true]
          : [true, false];
      for (final on in coldOrder) {
        clients[on] = await Client.create(
          on,
          init,
          Directory(
            '$scratch/disposable/${output.path.split('/').last}-${on ? 'on' : 'off'}',
          ),
          (issued) => save('$out/progress.json', {
            'n': n,
            'phase': phase,
            'on': on,
            'http_issued': issued,
            'utc': DateTime.now().toUtc().toIso8601String(),
            'rss': ProcessInfo.currentRss,
          }),
        );
      }
      Future<void> run(String kind, int trial, bool on, Map target) async {
        final label = '$kind-$trial-${on ? 'on' : 'off'}';
        phase = label;
        final h = clients[on]!;
        h.http.inner.close();
        h.http.inner = freshHttp(init['origin']);
        final c = LogicalCost();
        final s = h.sql.forCollector(c);
        final pre = h.store.acceptedGeneration(),
            dbBefore = dbState(h.store.path),
            work = h.store.work.snapshot(),
            ht = h.http.snap();
        final sqlUs = h.outer.sqlUs,
            sqlCalls = h.outer.calls,
            callbackUs = h.callback?.callbackUs ?? 0,
            callbackCalls = h.callback?.callbackCalls ?? 0;
        await command({'command': 'mode', 'on': on, 'label': label});
        final start = DateTime.now().toUtc();
        final ticks = cpuTicks();
        final watch = Stopwatch()..start();
        Map<String, Object?> row = {
          'run_id': 'n$n-$label',
          'N': n,
          'H': {'current_ledger_rows': 105, 'other_authoritative_rows': 35},
          'D': kind == 'cold'
              ? null
              : kind == 'no_change'
              ? 0
              : 1,
          'workload': kind,
          'trial': trial,
          'on': on,
          'fixture_digest': init['fixture']['fixture_sha256'],
          'source_digest': '8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8',
          'start_utc': start.toIso8601String(),
          'accepted_before': accepted(pre),
          'db_before': dbBefore,
          'expected_target': target,
          'status': 'RUNNING',
          'logical_counters': null,
          'sql_counters': null,
          'raw_path': '$out/$label.json',
        };
        save('$out/$label.json', row);
        try {
          Future<SegmentedPublication> publish() =>
              h.state.publishSegmentedForIsolatedUse(
                h.store,
                verificationLimits: largeVerificationFetchLimits,
              );
          final p = on
              ? await c.run(LogicalCostStage.e2, publish)
              : await publish();
          final us = watch.elapsedMicroseconds;
          final cpu = (cpuTicks() - ticks) * 10000;
          final sqlPublication = h.outer.sqlUs - sqlUs,
              cbPublication = (h.callback?.callbackUs ?? 0) - callbackUs;
          final post = h.store.acceptedGeneration();
          expect(post.id, p.generationId);
          expect(post.manifest!.target.toJson(), target);
          if (kind == 'no_change') {
            expect(p.idempotent, true);
            expect(post.id, pre.id);
            expect(post.sequence, pre.sequence);
          } else {
            expect(post.sequence, pre.sequence + 1);
          }
          final readWatch = Stopwatch()..start();
          Map read() => h.store.withAcceptedRead(
            post,
            (r) => {
              'ledger': r.rows(
                'ledger_entries',
                after: TreeKey.parse(['i', '1001'], 'ledger_entries'),
                limit: 1,
              ),
              'cash': r.rows(
                'cash_flows',
                after: TreeKey.parse(['i', '100'], 'cash_flows'),
                limit: 1,
              ),
              'hot_present': r.hot['state'] is Map,
            },
          );
          final values = on ? c.run(LogicalCostStage.e4Read, read) : read();
          final readUs = readWatch.elapsedMicroseconds;
          expect(values['hot_present'], true);
          c.close();
          final backend = await command({'command': 'snapshot'});
          expect(backend['measurement_complete'], true);
          final after = dbState(h.store.path);
          final chunks = (backend['requests'] as List).fold<int>(
            0,
            (s, r) => s + (r['chunks'] as int),
          );
          if (kind == 'cold')
            expect(after['objects'], init['fixture']['graph']['objects']);
          if (kind == 'no_change') {
            expect(chunks, 0);
            expect(after['objects'], dbBefore['objects']);
          }
          row.addAll({
            'status': 'COMPLETED',
            'valid_for_cost_grid': kind != 'cold',
            'valid_for_perturbation': true,
            'end_utc': DateTime.now().toUtc().toIso8601String(),
            'elapsed_us': us,
            'process_cpu_us_tick_10ms': cpu,
            'e4_elapsed_us': readUs,
            'publication_transaction_us': p.transactionMicroseconds,
            'publication_readback_us': p.readbackMicroseconds,
            'e1_sql_api_publication_us': sqlPublication,
            'e1_sql_api_including_e4_us': h.outer.sqlUs - sqlUs,
            'sql_calls': h.outer.calls - sqlCalls,
            'sql_row_callback_publication_us_lower_bound': on
                ? cbPublication
                : null,
            'sql_row_callback_calls': on
                ? (h.callback?.callbackCalls ?? 0) - callbackCalls
                : null,
            'http': diff(h.http.snap(), ht),
            'accepted_after': accepted(post),
            'database_path': h.store.path,
            'db_after': after,
            'new_immutable_objects': after['objects']! - dbBefore['objects']!,
            'canonical_transferred_object_events': chunks,
            'work': h.store.work.since(work),
            'logical_counters': on ? c.snapshot() : null,
            'sql_counters': on ? s.snapshot() : null,
            'collector_closed': c.isClosed,
            'backend': backend,
            'e4_values': values,
            'rss_bytes': ProcessInfo.currentRss,
            'max_rss_bytes': ProcessInfo.maxRss,
            'stage_completion': {
              'E2': true,
              'E1': true,
              'E3': true,
              'E4': true,
            },
            'observation_expired': (backend['requests'] as List).any(
              (r) => r['status'] == 410,
            ),
          });
        } catch (e) {
          c.close();
          row.addAll({
            'status': 'INCOMPLETE',
            'valid_for_cost_grid': false,
            'valid_for_perturbation': false,
            'error': '$e',
            'elapsed_us': watch.elapsedMicroseconds,
            'end_utc': DateTime.now().toUtc().toIso8601String(),
            'collector_closed': c.isClosed,
            'logical_counters': on ? c.snapshot() : null,
            'sql_counters': on ? s.snapshot() : null,
            'db_after': dbState(h.store.path),
            'accepted_after': accepted(h.store.acceptedGeneration()),
            'backend': await command({'command': 'snapshot'}),
          });
          rethrow;
        } finally {
          save('$out/$label.json', row);
          results.add(row);
          save('$out/runs.json', results);
        }
      }

      final initial = Map<String, dynamic>.from(
        init['fixture']['manifest']['target'],
      );
      for (final on in coldOrder) {
        await run('cold', 0, on, initial);
      }
      Map current = initial;
      for (var trial = 0; trial < 3; trial++) {
        for (final kind in ['no_change', 'card', 'cash']) {
          if (kind != 'no_change') {
            final mutation = await command({
              'command': 'mutate',
              'kind': kind,
              'amount': kind == 'card' ? 1001 + trial : -51 - trial,
              'label': '$kind-$trial',
            });
            current = mutation['target'];
          }
          final order = (trial + (n == 5000 || n == 50000 ? 1 : 0)).isEven
              ? [false, true]
              : [true, false];
          for (final on in order) {
            await run(kind, trial, on, current);
          }
        }
      }
      save('$out/backend-final.json', await command({'command': 'finish'}));
      for (final h in clients.values) {
        final d = sqlite3.open(h.store.path, mode: OpenMode.readOnly);
        try {
          expect(d.select('PRAGMA quick_check').single.values.single, 'ok');
          expect(d.select('PRAGMA foreign_key_check'), isEmpty);
        } finally {
          d.close();
        }
      }
    } catch (e) {
      failure = e;
      save('$out/failure.json', {
        'phase': phase,
        'error': '$e',
        'utc': DateTime.now().toUtc().toIso8601String(),
      });
      rethrow;
    } finally {
      for (final h in clients.values) {
        h.close();
      }
      try {
        await command({'command': 'exit'});
        await process.stdin.close();
        expect(await process.exitCode.timeout(const Duration(seconds: 30)), 0);
      } finally {
        await lines.cancel();
        await err.flush();
        await err.close();
      }
      save('$out/summary.json', {
        'N': n,
        'status': failure == null ? 'COMPLETED' : 'INCOMPLETE',
        'completed_runs': results
            .where((r) => r['status'] == 'COMPLETED')
            .length,
        'incomplete_runs': results
            .where((r) => r['status'] != 'COMPLETED')
            .length,
        'run_order': results.map((r) => r['run_id']).toList(),
      });
    }
  });
}
