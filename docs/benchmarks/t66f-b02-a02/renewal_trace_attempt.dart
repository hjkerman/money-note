// 조사 전용 VM. 실제 E1/E2와 backend fixture, mock410. Real HTTP 증거 아님.
import 'dart:async';
import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:mirrors';

import 'package:ffi/ffi.dart';
import 'package:sqlite3/sqlite3.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../../../mobile/test/support/segmented_large_transport.dart';
import '../t66f-b02-implementation/verification_profile.dart';

typedef Trace = Int32 Function(
  Uint32,
  Pointer<Void>,
  Pointer<Void>,
  Pointer<Void>,
);

class SqlTrace {
  final Map<String, int> counts = {}, profileNs = {};
  late final NativeCallable<Trace> callback;
  late final int Function(
    Pointer<Void>,
    int,
    Pointer<NativeFunction<Trace>>,
    Pointer<Void>,
  )
  enable;
  final Database db;
  SqlTrace(this.db) {
    final path = File('/proc/self/maps')
        .readAsLinesSync()
        .where((s) => s.contains('libsqlite3') && s.contains('/'))
        .first
        .split(RegExp(r'\s+'))
        .last;
    final lib = DynamicLibrary.open(path);
    final sql = lib
        .lookupFunction<
          Pointer<Utf8> Function(Pointer<Void>),
          Pointer<Utf8> Function(Pointer<Void>)
        >('sqlite3_sql');
    enable = lib
        .lookupFunction<
          Int32 Function(
            Pointer<Void>,
            Uint32,
            Pointer<NativeFunction<Trace>>,
            Pointer<Void>,
          ),
          int Function(
            Pointer<Void>,
            int,
            Pointer<NativeFunction<Trace>>,
            Pointer<Void>,
          )
        >('sqlite3_trace_v2');
    callback = NativeCallable<Trace>.isolateLocal((
      int flag,
      Pointer<Void> context,
      Pointer<Void> p,
      Pointer<Void> x,
    ) {
      final text = sql(p).toDartString();
      final label = text.startsWith('SELECT length(body)')
          ? 'object_size'
          : text.startsWith('SELECT o.*,r.bytes')
          ? 'object_body'
          : text.startsWith('SELECT e.*,r.bytes')
          ? 'object_edges'
          : text.startsWith('SELECT 1 FROM staging_objects')
          ? 'staging_lookup'
          : text.startsWith('SELECT name,sql FROM sqlite_master')
          ? 'schema'
          : text.split(' ').first;
      if (flag == 1) counts.update(label, (n) => n + 1, ifAbsent: () => 1);
      if (flag == 2)
        profileNs.update(
          label,
          (n) => n + x.cast<Uint64>().value.toInt(),
          ifAbsent: () => x.cast<Uint64>().value.toInt(),
        );
      return 0;
    }, exceptionalReturn: 0);
    if (enable(db.handle.cast<Void>(), 3, callback.nativeFunction, nullptr) !=
        0)
      throw StateError('trace registration');
  }
  void close() {
    enable(db.handle.cast<Void>(), 0, nullptr, nullptr);
    callback.close();
  }
}

Map<String, int> diff(Map<String, int> a, Map<String, int> b) => {
  for (final k in {...a.keys, ...b.keys}) k: (a[k] ?? 0) - (b[k] ?? 0),
};
Future<Map<String, dynamic>> run(
  GenerationFixture fixture,
  int n,
  bool renew,
  bool trace,
) async {
  final dir = Directory.systemTemp.createTempSync('mn-a02-renew-'),
      watch = Stopwatch();
  var inserted = 0, commits = 0, commitNs = 0, commitStart = 0;
  final store = SegmentedClientStore.open(
    dir,
    fixture.cache,
    publication: true,
    limits: largeVerificationStoreLimits,
    fault: (p) {
      if (p == 'after_object_insert') inserted++;
      if (p == 'before_commit') commitStart = watch.elapsedMicroseconds;
      if (p == 'after_commit') {
        commits++;
        if (watch.isRunning)
          commitNs += (watch.elapsedMicroseconds - commitStart) * 1000;
      }
    },
  );
  final mirror = reflect(store);
  final lib = mirror.type.owner as LibraryMirror;
  final db =
      mirror.getField(MirrorSystem.getSymbol('_db', lib)).reflectee as Database;
  final meter = trace ? SqlTrace(db) : null,
      transport = BatchFixtureTransport(fixture);
  final manifestStart = <String, int>{},
      snapshot = <String, Map<String, int>>{},
      sqlStart = <String, Map<String, int>>{},
      attempts = <String, Map<String, dynamic>>{};
  var expired = false, requestTotal = 0, requestBytes = 0;
  final hashes = <String>{};
  transport.after = (reply, method, path, body) {
    if (path.endsWith('/observations') && reply.status == 201) {
      final m = jsonDecode(utf8.decode(reply.bytes)) as Map,
          id = m['observation_id'] as String;
      manifestStart[id] = watch.elapsedMicroseconds;
      snapshot[id] = store.work.snapshot();
      sqlStart[id] = {...?meter?.counts};
      attempts[id] = {
        'created_at_us': watch.elapsedMicroseconds,
        'inserted_at_birth': inserted,
      };
    }
    if (path.endsWith('/objects') && reply.status == 200) {
      final packet = jsonDecode(utf8.decode(reply.bytes)) as Map;
      requestTotal++;
      requestBytes += reply.bytes.length;
      for (final x in packet['chunks']) hashes.add(x['ref']['hash'] as String);
    }
    return reply;
  };
  transport.before = (method, path, body) async {
    if (!path.endsWith('/objects')) return null;
    final id = path.split('/')[5], a = attempts[id]!;
    if (!a.containsKey('first_request_us')) {
      a['first_request_us'] = watch.elapsedMicroseconds;
      a['before_first_new_request_us'] =
          watch.elapsedMicroseconds - manifestStart[id]!;
      a['work_before_first_request'] = store.work.since(snapshot[id]!);
      a['sql_before_first_request'] = diff(meter?.counts ?? {}, sqlStart[id]!);
    }
    a['inserted_at_last_request'] = inserted;
    a['last_request_us'] = watch.elapsedMicroseconds;
    if (renew && !expired && inserted >= fixture.objects.length ~/ 2) {
      expired = true;
      a['forced_410_us'] = watch.elapsedMicroseconds;
      a['at_expiry_work'] = store.work.snapshot();
      a['inserted_at_expiry'] = inserted;
      return remoteError(
        'OBSERVATION_EXPIRED',
        'new_observation',
        410,
        body!['request_id'],
      );
    }
    return null;
  };
  watch.start();
  final before = store.work.snapshot();
  try {
    final acquired = await IncrementalFetcher(
      store,
      transport,
      limits: largeVerificationFetchLimits,
    ).acquire();
    final elapsed = watch.elapsedMicroseconds;
    final rows = db
        .select('SELECT hash FROM objects')
        .map((r) => r['hash'])
        .toSet();
    if (rows.length != fixture.objects.length ||
        !rows.containsAll(fixture.objects.keys))
      throw StateError('durable closure mismatch');
    if (db.select('SELECT current_id FROM accepted').single['current_id'] !=
            null ||
        db.select('PRAGMA foreign_key_check').isNotEmpty)
      throw StateError('publication/FK');
    if (renew && attempts.length != 2)
      throw StateError('renewal not exercised');
    return {
      'n': n,
      'reachable_objects': fixture.objects.length,
      'renew': renew,
      'sql_trace': trace,
      'elapsed_us': elapsed,
      'attempts': attempts,
      'store_work': store.work.since(before),
      'metric_verification_us': acquired.metrics.verificationMicroseconds,
      'downloaded': acquired.metrics.downloadedObjects,
      'actual_unique_response_objects': hashes.length,
      'response_entity_bytes': requestBytes,
      'actual_packets': requestTotal,
      'insert_fault_count': inserted,
      'commits': commits,
      'commit_boundary_ns': commitNs,
      'sql': meter?.counts,
      'sql_profile_ns': meter?.profileNs,
      'previous_accepted_preserved': true,
      'process_rss_bytes': ProcessInfo.currentRss,
    };
  } finally {
    meter?.close();
    store.close();
    dir.deleteSync(recursive: true);
  }
}

Future<void> main() async {
  final results = <Map<String, dynamic>>[];
  for (final n in [200, 1000, 4000]) {
    final bridge = await BackendBridge.start(history: n);
    final fixture = GenerationFixture(bridge.fixture);
    await bridge.dispose();
    for (final renew in [false, true])
      for (final traced in [false, true]) {
        results.add(await run(fixture, n, renew, traced));
        File(
          '../docs/benchmarks/t66f-b02-a02/renewal-cost.json',
        ).writeAsStringSync(
          '${const JsonEncoder.withIndent('  ').convert({'scope': '실제 E1/E2, backend fixture + controlled mock410; realTTL불변', 'results': results})}\n',
        );
        stdout.writeln('PASS n=$n renew=$renew trace=$traced');
      }
  }
}
