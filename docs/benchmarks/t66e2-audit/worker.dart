// 독립 감사 전용 HTTP 계수·barrier 도구. 제품 source는 변경하지 않는다.
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:crypto/crypto.dart';
import 'package:sqlite3/sqlite3.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

const origin = 'https://independent.synthetic';
dynamic copy(dynamic value) => jsonDecode(jsonEncode(value));
void emit(Map value) => stdout.writeln(jsonEncode(value));
void barrier(String point) {
  emit({'barrier': point});
  stdin.readLineSync();
}

class AuditClient extends http.BaseClient {
  AuditClient(this.fixture, this.plan, this.root);
  Map fixture;
  final String plan, root;
  String token = 'synthetic-audit-only';
  String credential = 'synthetic-audit-only';
  Process? backend;
  StreamIterator<String>? lines;
  Map? targetOracle;
  final trace = <Map>[];
  final nonces = <String, Map>{};
  final retired = <String>{};
  int active = 0,
      maxActive = 0,
      objects = 0,
      manifests = 0,
      releases = 0,
      wireBytes = 0,
      payloadBytes = 0;
  bool injected = false;
  SyncCancellation? cancel;
  Future<void> Function(String, Map?)? hook;
  static Future<AuditClient> live(String root, String repo) async {
    final process = await Process.start('$repo/.venv/bin/python', [
      '$repo/docs/benchmarks/t66e2-audit/audit_backend.py',
    ]);
    process.stderr.drain<void>();
    final lines = StreamIterator(
      process.stdout.transform(utf8.decoder).transform(const LineSplitter()),
    );
    if (!await lines.moveNext()) throw StateError('audit backend startup');
    final first = jsonDecode(lines.current) as Map;
    final client = AuditClient(first['fixture'] as Map, 'live', root)
      ..backend = process
      ..lines = lines
      ..token = first['token'] as String
      ..credential = first['token'] as String;
    return client;
  }

  Future<void> commandTail = Future.value();
  Future<Map> command(Map value) {
    final result = commandTail.then((_) async {
      backend!.stdin.writeln(jsonEncode(value));
      if (!await lines!.moveNext()) throw StateError('audit backend ended');
      return jsonDecode(lines!.current) as Map;
    });
    commandTail = result.then<void>((_) {}, onError: (Object _) {});
    return result;
  }

  Future<void> finish() async {
    if (backend != null) {
      await command({'command': 'exit'});
      await backend!.stdin.close();
      await backend!.exitCode;
      await lines!.cancel();
    }
  }

  Map counts() => {
    'object_requests': objects,
    'manifest_requests': manifests,
    'release_requests': releases,
    'payload_bytes': payloadBytes,
    'response_bytes': wireBytes,
    'max_active_sends': maxActive,
  };
  Uint8List remote(String code, String action, int status, String? nonce) =>
      encodeC1({
        'protocol': 1,
        'request_id': nonce,
        'error': {
          'code': code,
          'action': action,
          'retry_after_ms': null,
          'current_ns': null,
        },
      });
  String observationId(String nonce) {
    final h = sha256.convert(utf8.encode(nonce)).toString();
    return '${h.substring(0, 8)}-${h.substring(8, 12)}-4${h.substring(13, 16)}-8${h.substring(17, 20)}-${h.substring(20, 32)}';
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    active++;
    maxActive = active > maxActive ? active : maxActive;
    final path = request.url.path, method = request.method;
    final bodyBytes = await request.finalize().toBytes();
    final body = bodyBytes.isEmpty
        ? null
        : jsonDecode(utf8.decode(bodyBytes)) as Map;
    final isObject = path.endsWith('/objects');
    if (isObject)
      objects++;
    else if (method == 'POST')
      manifests++;
    else
      releases++;
    final entry = <String, dynamic>{
      'method': method,
      'path': path,
      'authorization_matches':
          request.headers['Authorization'] == 'Bearer $token',
      'request': body,
    };
    trace.add(entry);
    var aborted = false;
    if (request is http.AbortableRequest) {
      request.abortTrigger?.then((_) {
        aborted = true;
      });
    }
    await hook?.call(path, body);
    await Future<void>.value();
    if (aborted) {
      entry['aborted_before_dispatch'] = true;
      active--;
      throw http.RequestAbortedException(request.url);
    }
    if (plan == 'cancel-before-response' && isObject && !injected) {
      injected = true;
      cancel!.cancel();
    }
    if (plan == 'credential-switch' && isObject && !injected) {
      injected = true;
      credential = 'changed-synthetic';
    }
    if ((plan == 'retry-reset' || plan == 'retry-exhaust') &&
        method == 'POST' &&
        manifests <= (plan == 'retry-reset' ? 2 : 3)) {
      active--;
      throw http.ClientException('synthetic reset');
    }
    if (plan == 'retry-timeout' && method == 'POST' && manifests <= 2) {
      await (request as http.AbortableRequest).abortTrigger;
      active--;
      throw http.RequestAbortedException(request.url);
    }
    int status = 200;
    Uint8List bytes;
    if (plan.startsWith('live')) {
      final response = await command({
        'command': 'http',
        'method': method,
        'path': path,
        'headers': request.headers,
        'body_base64': base64Encode(bodyBytes),
      });
      status = response['status'] as int;
      bytes = base64Decode(response['body_base64'] as String);
    } else if (plan.startsWith('permanent-') && method == 'POST') {
      final auth = plan == 'permanent-401';
      status = auth ? 401 : 422;
      bytes = remote(
        auth ? 'AUTH_REQUIRED' : 'INVALID_REQUEST',
        auth ? 'reauthenticate' : 'blocked',
        status,
        body!['request_id'] as String,
      );
    } else if (plan == 'retry-503' && method == 'POST' && manifests <= 2) {
      status = 503;
      bytes = remote(
        'ROOT_NOT_READY',
        'retry_same',
        status,
        body!['request_id'] as String,
      );
    } else if ((plan == 'expiry-manifest' && method == 'POST' && !isObject ||
            plan == 'expiry-transfer' && isObject && objects == 3 ||
            plan == 'expiry-terminal' &&
                method == 'POST' &&
                !isObject &&
                manifests == 2) &&
        !injected) {
      injected = true;
      status = 410;
      bytes = remote(
        'OBSERVATION_EXPIRED',
        'new_observation',
        status,
        body!['request_id'] as String,
      );
    } else if (method == 'DELETE') {
      retired.add(path.split('/').last);
      status = 204;
      bytes = Uint8List(0);
    } else if (!isObject) {
      final nonce = body!['request_id'] as String;
      final m = nonces.putIfAbsent(
        nonce,
        () => {
          ...copy(fixture['manifest']) as Map,
          'request_id': nonce,
          'observation_id': observationId(nonce),
        },
      );
      final v = copy(m) as Map;
      switch (plan) {
        case 'manifest-protocol':
          v['protocol'] = true;
        case 'manifest-nonce':
          v['request_id'] = syncUuid();
        case 'manifest-id':
          v['observation_id'] = 'invalid';
        case 'manifest-root':
          v['target']['sync_root'] = '0' * 64;
        case 'manifest-lease':
          v['expires_at'] = v['validated_at'];
        case 'manifest-extra':
          v['extra'] = null;
        case 'manifest-inline':
          v['inline_objects'] = [null];
        case 'terminal-change':
          if (manifests == 2)
            v['expires_at'] =
                (DateTime.parse(v['expires_at'] as String)
                        .subtract(const Duration(seconds: 1)))
                    .toIso8601String()
                    .replaceFirst('.000Z', 'Z');
      }
      status = nonces.length == 1 && manifests == 1 ? 201 : 200;
      bytes = encodeC1(v);
    } else {
      final item = (body!['items'] as List).single as Map;
      final hashes = (item['path'] as List).cast<String>();
      final found = (fixture['objects'] as List)
          .where((o) => o['ref']['hash'] == hashes.last)
          .firstOrNull;
      if (found == null || plan == 'missing-descendant' && objects >= 3) {
        status = 410;
        bytes = remote(
          'OBSERVATION_INCOMPLETE',
          'new_observation',
          status,
          body['request_id'] as String,
        );
      } else {
        final raw = base64Decode(found['data_base64'] as String);
        final offset = int.parse(item['offset'] as String),
            length = item['length'] as int;
        final chunk = <String, dynamic>{
          'ref': copy(found['ref']),
          'offset': item['offset'],
          'length': length,
          'data_base64': base64Encode(raw.sublist(offset, offset + length)),
        };
        final packet = <String, dynamic>{
          'protocol': 1,
          'request_id': body['request_id'],
          'observation_id': path.split('/')[5],
          'chunks': [chunk],
        };
        switch (plan) {
          case 'transfer-protocol':
            packet['protocol'] = 2;
          case 'transfer-nonce':
            packet['request_id'] = syncUuid();
          case 'transfer-observation':
            packet['observation_id'] = syncUuid();
          case 'transfer-ref':
            chunk['ref']['hash'] = 'f' * 64;
          case 'transfer-offset':
            chunk['offset'] = '1';
          case 'transfer-length':
            chunk['length'] = length - 1;
          case 'transfer-base64':
            chunk['data_base64'] = '!' * (4 * ((length + 2) ~/ 3));
          case 'transfer-bitflip':
            final changed = raw.sublist(offset, offset + length);
            final at = utf8.decode(changed).indexOf('"canon":1') + 8;
            if (at < 8) throw StateError('audit canonical mutation');
            changed[at] = 50;
            chunk['data_base64'] = base64Encode(changed);
        }
        bytes = encodeC1(packet);
        if (plan == 'transfer-json-truncated')
          bytes = bytes.sublist(0, bytes.length - 1);
        if (plan == 'transfer-oversized') bytes = Uint8List(2 * 1048576);
      }
    }
    if (status == 200 && isObject && !plan.startsWith('transfer-')) {
      try {
        for (final c in jsonDecode(utf8.decode(bytes))['chunks']) {
          payloadBytes += base64Decode(c['data_base64'] as String).length;
        }
      } catch (_) {}
    }
    entry['status'] = status;
    entry['response_bytes'] = bytes.length;
    wireBytes += bytes.length;
    if (plan == 'crash-manifest' && method == 'POST' && !isObject)
      barrier(plan);
    if (plan == 'crash-return' && method == 'DELETE') barrier(plan);
    Stream<List<int>> stream() async* {
      try {
        if (isObject &&
            (plan == 'cancel-midstream' || plan == 'crash-transfer')) {
          yield bytes.sublist(0, bytes.length ~/ 2);
          if (plan == 'crash-transfer')
            barrier(plan);
          else
            cancel!.cancel();
          yield bytes.sublist(bytes.length ~/ 2);
        } else {
          yield bytes;
        }
      } finally {
        active--;
      }
    }

    return http.StreamedResponse(
      stream(),
      status,
      contentLength:
          bytes.length + (plan == 'http-truncated' && isObject ? 1 : 0),
    );
  }
}

Future<void> main(List<String> args) async {
  final job = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final root = Directory(job['root'] as String)..createSync(recursive: true);
  final plan = job['plan'] as String;
  final client = plan.startsWith('live')
      ? await AuditClient.live(root.path, job['repo'] as String)
      : AuditClient(
          jsonDecode(File(job['fixture'] as String).readAsStringSync()) as Map,
          plan,
          root.path,
        );
  final baseFixture = job['cache_fixture'] == null
      ? client.fixture
      : jsonDecode(File(job['cache_fixture'] as String).readAsStringSync())
            as Map;
  final target = SyncTarget.parse(baseFixture['manifest']['target']);
  final cache = CacheNamespace.forTarget(origin, target);
  final cancel = SyncCancellation();
  client.cancel = cancel;
  var active = false, acquisitions = 0;
  late SegmentedClientStore store;
  store = SegmentedClientStore.open(
    root,
    cache,
    acquisition: true,
    limits: ClientStoreLimits(
      objectCount: plan == 'storage-count' ? 1 : 100000,
      databasePages: plan == 'storage-full' ? 64 : 262144,
    ),
    fault: (point) {
      if (!active) return;
      if (point == 'after_acquisition_insert') acquisitions++;
      if (plan == 'cancel-progress' && point == 'after_progress_insert')
        cancel.cancel();
      if ((plan == 'crash-before-persist' && point == 'before_object_insert') ||
          (plan == 'crash-after-persist' &&
              point == 'after_commit' &&
              acquisitions == 1 &&
              client.objects == 1) ||
          (plan == 'crash-progress' && point == 'after_progress_insert') ||
          (plan == 'crash-graph-state' &&
              point == 'after_acquisition_insert' &&
              acquisitions == 2))
        barrier(plan);
    },
  );
  final measurements = <Map>[];
  Map value(VerifiedStagedGeneration r) => {
    'ok': true,
    'stage': r.stagingId,
    'target': r.manifest.target.toJson(),
    'manifest': jsonDecode(utf8.decode(r.manifest.bytes)),
    'graph': r.graph.objects.map((v) => v.toJson()).toList(),
    'table_rows': r.graph.tableRows,
    'metrics': r.metrics.toJson(),
    'http': client.counts(),
    'trace_end': client.trace.length,
  };
  Future<Map> acquire({String? resume, SyncCancellation? token}) async {
    try {
      return value(
        await IncrementalFetcher(
          store,
          AuthenticatedSegmentedTransport(
            client: client,
            origin: origin,
            credential: () => client.credential,
            timeout: plan == 'retry-timeout'
                ? const Duration(milliseconds: 20)
                : Duration(seconds: plan.startsWith('live') ? 60 : 15),
          ),
          limits: FetchLimits(
            graphObjects: plan == 'graph-budget' ? 1 : 100000,
            graphEdges: plan == 'edge-budget' ? 1 : 200000,
            pathDepth: plan == 'depth-budget' ? 1 : 512,
            chunkBytes: plan == 'chunked' ? 256 : 1048576,
          ),
          delay: (_, c) async {
            c.check();
          },
        ).acquire(resumeId: resume, cancellation: token ?? cancel),
      );
    } on AcquisitionFailure catch (e) {
      return {
        'ok': false,
        'error': e.code,
        'action': e.action,
        'stage': e.stagingId,
        'http': client.counts(),
        'trace_end': client.trace.length,
      };
    }
  }

  try {
    if (job['seed'] == true ||
        plan == 'corrupt-cache' ||
        plan == 'cache-delete') {
      for (final o in baseFixture['objects'])
        store.putVerifiedObject(
          ObjectRef.parse(o['ref']),
          base64Decode(o['data_base64'] as String),
        );
    }
    if (plan == 'corrupt-cache' ||
        plan == 'cache-delete' ||
        plan == 'schema-trigger') {
      final direct = sqlite3.open(store.path);
      if (plan == 'schema-trigger') {
        direct.execute('DROP TRIGGER acquisition_usage');
      } else {
        final row = direct
            .select(
              "SELECT hash,body FROM objects WHERE kind='snapshot-leaf' LIMIT 1",
            )
            .single;
        if (plan == 'corrupt-cache') {
          final ddl =
              direct
                      .select(
                        "SELECT sql FROM sqlite_master WHERE name='immutable_body'",
                      )
                      .single['sql']
                  as String;
          direct.execute('DROP TRIGGER immutable_body');
          direct.execute(
            'UPDATE objects SET body=zeroblob(length(body)) WHERE hash=?',
            [row['hash']],
          );
          direct.execute(ddl);
        } else {
          direct.execute('DELETE FROM objects WHERE hash=?', [row['hash']]);
          direct.execute(
            'UPDATE usage SET objects=objects-1,payload=payload-?,metadata=metadata-192',
            [(row['body'] as List).length],
          );
        }
      }
      direct.close();
    }
    if (job['extra'] != null) {
      final extra = job['extra'] as Map;
      store.putVerifiedObject(
        ObjectRef.parse(extra['ref']),
        base64Decode(extra['data_base64'] as String),
      );
    }
    if (plan == 'cancel-before') cancel.cancel();
    active = true;
    if (plan == 'live') {
      final cold = await acquire();
      cold['oracle'] = await client.command({'command': 'oracle'});
      measurements.add(cold);
      final identical = await acquire();
      identical['oracle'] = await client.command({'command': 'oracle'});
      measurements.add(identical);
      await client.command({'command': 'mutate'});
      Map? observed;
      client.hook = (path, body) async {
        if (path.endsWith('/objects') && observed == null) {
          observed = await client.command({'command': 'oracle'});
          await client.command({'command': 'mutate'});
        }
      };
      final changed = await acquire();
      changed['oracle'] = observed;
      measurements.add(changed);
      client.hook = null;
      final c = SyncCancellation();
      final before = client.objects;
      client.hook = (path, body) async {
        if (path.endsWith('/objects') && client.objects - before == 3)
          c.cancel();
      };
      final interrupted = await acquire(token: c);
      final inspection = sqlite3.open(store.path);
      interrupted['cached_hashes'] = inspection
          .select('SELECT hash FROM objects')
          .map((r) => r['hash'])
          .toList();
      inspection.dispose();
      measurements.add(interrupted);
      client.hook = null;
      store.close();
      store = SegmentedClientStore.open(root, cache, acquisition: true);
      final resumed = await acquire(resume: interrupted['stage'] as String?);
      resumed['oracle'] = await client.command({'command': 'oracle'});
      measurements.add(resumed);
      emit({
        'measurements': measurements,
        'path': store.path,
        'trace': client.trace,
      });
    } else if (plan.startsWith('live-')) {
      client.hook = (path, body) async {
        final when = plan == 'live-expiry-terminal'
            ? path.endsWith('/observations') && client.manifests == 2
            : path.endsWith('/objects') && client.objects == 3;
        if (when && !client.injected) {
          client.injected = true;
          await client.command(
            plan == 'live-revocation'
                ? {'command': 'revoke'}
                : {'command': 'advance', 'seconds': 900},
          );
        }
      };
      final result = await acquire();
      final oracle = await client.command({'command': 'oracle'});
      emit({
        ...result,
        'oracle': oracle,
        'path': store.path,
        'trace': client.trace,
      });
    } else if (plan == 'concurrent') {
      final entered = Completer<void>(), unblock = Completer<void>();
      client.hook = (path, body) async {
        if (!entered.isCompleted) {
          entered.complete();
          await unblock.future;
        }
      };
      final first = acquire();
      await entered.future;
      final second = await acquire();
      unblock.complete();
      final one = await first;
      client.hook = null;
      emit({
        'first': one,
        'second': second,
        'path': store.path,
        'trace': client.trace,
      });
    } else {
      final result = await acquire(resume: job['resume'] as String?);
      emit({...result, 'path': store.path, 'trace': client.trace});
    }
  } finally {
    store.close();
    await client.finish();
  }
}
