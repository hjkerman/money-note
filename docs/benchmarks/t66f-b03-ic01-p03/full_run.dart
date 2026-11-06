// GO 파일이 있을 때만 한 번 호출하는 실제 원 AppState publication 경로.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/logical_cost_sqlite.dart';
import '../../../mobile/test/support/offline_mode_fixtures.dart';
import '../t66f-b02-implementation/verification_profile.dart';
import 'timing.dart';

void _save(String path, Object? value) => File(
  path,
).writeAsStringSync('${const JsonEncoder.withIndent('  ').convert(value)}\n');

class _Sink implements Sink<Digest> {
  Digest? value;
  @override
  void add(Digest d) => value = d;
  @override
  void close() {}
}

Map<String, dynamic> _values(AcceptedReadView view) {
  final result = <String, dynamic>{};
  final oracle = LogicalCost()..close();
  for (final table in segmentedTables) {
    final output = _Sink(), input = sha256.startChunkedConversion(output);
    TreeKey? after;
    var count = 0;
    while (true) {
      final page = view.rows(table, after: after);
      for (final row in page) {
        // Independent financial-value oracle; no product counter uses this hash.
        oracle.run(
          LogicalCostStage.calibration,
          () => input.add(ascii.encode('${sha256.convert(encodeC1(row))}\n')),
        );
        count++;
      }
      if (page.length < 256) break;
      final key = page.last[primaryColumn(table)];
      after = TreeKey.parse([key is int ? 'i' : 't', '$key'], table);
    }
    input.close();
    result[table] = {'count': count, 'sha256': '${output.value}'};
  }
  return result;
}

// Return the original IOStreamedResponse unchanged: abort and native cleanup
// behavior is preserved. These are HEADER timings, not entity completion wall.
class _Http extends http.BaseClient {
  _Http(this.inner, this.progress);
  final http.Client inner;
  final void Function(String reason) progress;
  int issued = 0, headersCompleted = 0, headerUs = 0, failures = 0;
  final List<Map<String, Object?>> observationBoundaries = [];
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final observation =
        request.method == 'POST' && request.url.path.endsWith('/observations');
    issued++;
    if (observation || issued % 128 == 0)
      progress(
        observation ? 'before-observation-request' : 'before-periodic-request',
      );
    final watch = Stopwatch()..start();
    try {
      final response = await inner.send(request);
      headersCompleted++;
      headerUs += watch.elapsedMicroseconds;
      if (response.statusCode >= 400) failures++;
      if (observation)
        observationBoundaries.add({
          'issued': issued,
          'status': response.statusCode,
          'header_us': watch.elapsedMicroseconds,
          'content_length': response.contentLength,
          'at_utc': DateTime.now().toUtc().toIso8601String(),
        });
      return response;
    } catch (_) {
      failures++;
      rethrow;
    }
  }

  @override
  void close() {} // borrowed client; owner closes before backend join.
}

Future<void> fullRun(
  Directory temp,
  Directory out,
  Map initial,
  IOClient client,
) async {
  final marker = File('${out.path}/full-attempt.json');
  expect(marker.existsSync(), false, reason: 'at most one full cold attempt');
  _save(marker.path, {
    'attempt': 1,
    'started_utc': DateTime.now().toUtc().toIso8601String(),
    'status': 'RUNNING',
    'ttl_seconds': 900,
    'max_observations': 3,
    'real_clock': true,
  });
  // ignore: invalid_use_of_visible_for_testing_member
  FlutterSecureStorage.setMockInitialValues({});
  final origin = initial['origin'] as String;
  final target = SyncTarget.parse(initial['fixture']['manifest']['target']);
  final root = Directory('${temp.path}/full-client')..createSync();
  final legacy = OfflineStore(directoryProvider: () async => root);
  await legacy.replaceBaseline(baselineFixture());
  await legacy.beginOnlineWrite(1);
  final protected = <String, String>{
    for (final f in Directory(
      '${root.path}/offline-mode',
    ).listSync().whereType<File>())
      f.path: localChecksum(f.readAsBytesSync()),
  };
  final c = LogicalCost(), s = SqlCosts();
  late CostDatabase costDb;
  late TimedDatabase timedDb, callbackDb;
  final store = c.run(
    LogicalCostStage.setup,
    () => SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(origin, target),
      adapters: true,
      limits: largeVerificationStoreLimits,
      diagnosticDatabaseFactory: (path) {
        callbackDb = TimedDatabase(sqlite3.open(path));
        costDb = CostDatabase(callbackDb, s);
        return timedDb = TimedDatabase(costDb);
      },
    ),
  );
  final native = sqlite3.open(store.path, mode: OpenMode.readOnly);
  expect(native.select('SELECT count(*) n FROM objects').single['n'], 0);
  native.close();
  final watch = Stopwatch()..start();
  late _Http measured;
  var peak = ProcessInfo.currentRss;
  final transitions = <Map<String, Object?>>[];
  void snapshot(String reason) {
    final value = <String, Object?>{
      'reason': reason,
      'utc': DateTime.now().toUtc().toIso8601String(),
      'elapsed_us': watch.elapsedMicroseconds,
      'requests_issued': measured.issued,
      'headers_completed': measured.headersCompleted,
      'request_failures': measured.failures,
      'primitive': c.snapshot(),
      'sql': s.snapshot(),
      'work': store.work.snapshot(),
      'sql_us': timedDb.sqlUs,
      'sql_observer_callback_us': callbackDb.callbackUs,
      'cache': Map<String, int>.from(costDb.statementReuse),
      'rss_bytes': ProcessInfo.currentRss,
      'max_rss_bytes': ProcessInfo.maxRss,
    };
    if (reason.contains('observation')) transitions.add(value);
    _save('${out.path}/full-progress.json', value);
    _save('${out.path}/full-observation-client-boundaries.json', transitions);
  }

  measured = _Http(client, snapshot);
  final api = MoneyNoteApiClient(client: measured, baseUrl: origin);
  await api.saveSession(initial['token'] as String);
  final state = AppState(api, offlineStore: legacy)
    ..user = baselineFixture().user;
  final sampler = Timer.periodic(const Duration(seconds: 1), (_) {
    if (ProcessInfo.currentRss > peak) peak = ProcessInfo.currentRss;
  });
  Object? failure;
  final result = <String, Object?>{
    'attempts': 1,
    'status': 'RUNNING',
    'fixture_objects': 400532,
    'root': target.syncRoot,
    'accepted_before': store.acceptedGeneration().id,
    'protected_before': protected,
    'store_path': store.path,
  };
  try {
    final publication = await c.run(
      LogicalCostStage.e2,
      () => state.publishSegmentedForIsolatedUse(
        store,
        verificationLimits: largeVerificationFetchLimits,
      ),
    );
    result['publication_us'] = watch.elapsedMicroseconds;
    final accepted = store.acceptedGeneration();
    expect(accepted.id, publication.generationId);
    expect(accepted.manifest!.target.syncRoot, target.syncRoot);
    result['e3_snapshot'] = {
      'primitive': c.snapshot(),
      'sql': s.snapshot(),
      'work': store.work.snapshot(),
      'cache': Map<String, int>.from(costDb.statementReuse),
    };
    final read = Stopwatch()..start();
    final values = c.run(
      LogicalCostStage.e4Read,
      () => store.withAcceptedRead(accepted, _values),
    );
    expect(values, initial['fixture']['graph']['raw_value_sha256']);
    result['e4_read_us'] = read.elapsedMicroseconds;
    result['e4_values'] = values;
    result['accepted_after'] = accepted.id;
    result['sequence'] = publication.sequence;
    result['status'] = 'PASS';
  } catch (error, stack) {
    failure = error;
    result['status'] = 'FAIL';
    result['error'] = '$error';
    result['stack'] = '$stack';
    result['accepted_after'] = store.acceptedGeneration().id;
  } finally {
    sampler.cancel();
    snapshot('terminal');
    result['elapsed_us'] = watch.elapsedMicroseconds;
    result['peak_sampled_rss'] = peak;
    result['lifetime_max_rss'] = ProcessInfo.maxRss;
    result['primitive'] = c.snapshot();
    result['sql'] = s.snapshot();
    result['work'] = store.work.snapshot();
    result['sql_us'] = timedDb.sqlUs;
    result['observer_callback_us'] = callbackDb.callbackUs;
    result['request_headers'] = measured.observationBoundaries;
    final d = sqlite3.open(store.path, mode: OpenMode.readOnly);
    result['durable_objects'] = Map<String, Object?>.from(
      d.select('SELECT count(*) n,sum(length(body)) bytes FROM objects').single,
    );
    result['durable_kinds'] = d
        .select(
          'SELECT kind,count(*) n,sum(length(body)) bytes FROM objects GROUP BY kind',
        )
        .map((r) => Map<String, Object?>.from(r))
        .toList();
    d.close();
    final after = <String, String>{
      for (final f in Directory(
        '${root.path}/offline-mode',
      ).listSync().whereType<File>())
        f.path: localChecksum(f.readAsBytesSync()),
    };
    result['protected_after'] = after;
    result['protected_unchanged'] = jsonEncode(protected) == jsonEncode(after);
    store.close();
    c.close();
    result['collector_closed'] = c.isClosed;
    result['cache_closed'] = costDb.statementReuse;
    result['completed_utc'] = DateTime.now().toUtc().toIso8601String();
    _save('${out.path}/full-result.json', result);
    _save(marker.path, {
      'attempt': 1,
      'status': result['status'],
      'completed_utc': result['completed_utc'],
    });
    expect(result['protected_unchanged'], true);
    expect(
      costDb.statementReuse['created'],
      costDb.statementReuse['finalized'],
    );
    expect(costDb.statementReuse['capacityRejections'], 0);
  }
  if (failure != null)
    fail('P03 one full instrumented attempt failed: $failure');
  expect((result['durable_objects'] as Map)['n'], 400532);
  expect((result['durable_objects'] as Map)['bytes'], 261543083);
  expect(s.values['e2/objects/INSERT/effective/rows'], BigInt.from(400532));
  expect(
    s.values['e2/objects/INSERT/blobBytes/committed'],
    BigInt.from(261543083),
  );
}
