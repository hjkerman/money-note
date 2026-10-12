import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

const syntheticOrigin = 'https://e2.synthetic';

// Private pipe to actual isolated ASGI/auth/SQLite. No network listener, normal
// backend startup, real session or application financial data is involved.
class BackendBridge extends http.BaseClient {
  BackendBridge._(this.process, this.lines, this.token, this.fixture);
  final Process process;
  final StreamIterator<String> lines;
  final String token;
  final Map<String, dynamic> fixture;
  Future<void> _tail = Future.value();
  int objectRequests = 0, manifestRequests = 0, payloadBytes = 0;
  Future<void> Function(String path)? before;

  static Future<BackendBridge> start({int history = 0}) async {
    final root = Directory.current.path.endsWith('/mobile')
        ? Directory.current.parent.path
        : Directory.current.path;
    final process = await Process.start('$root/.venv/bin/python',
        ['$root/scripts/benchmarks/t66e2_server.py', '$history']);
    // Drain without printing synthetic payloads/credentials on successful runs.
    final errors = StringBuffer();
    process.stderr.transform(utf8.decoder).listen(errors.write);
    final lines = StreamIterator(
        process.stdout.transform(utf8.decoder).transform(const LineSplitter()));
    if (!await lines.moveNext()) {
      throw StateError('synthetic bridge startup failed: $errors');
    }
    final init = jsonDecode(lines.current) as Map<String, dynamic>;
    return BackendBridge._(process, lines, init['token'] as String,
        init['fixture'] as Map<String, dynamic>);
  }

  Future<Map<String, dynamic>> command(Map<String, dynamic> input) {
    final done = Completer<Map<String, dynamic>>();
    _tail = _tail.then((_) async {
      process.stdin.writeln(jsonEncode(input));
      if (!await lines.moveNext()) throw StateError('synthetic bridge ended');
      return jsonDecode(lines.current) as Map<String, dynamic>;
    }).then(done.complete, onError: done.completeError);
    return done.future;
  }

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    var aborted = false;
    if (request is http.AbortableRequest) {
      request.abortTrigger?.then((_) {
        aborted = true;
      });
    }
    final body = await request.finalize().toBytes();
    final path = request.url.path;
    await before?.call(path);
    if (aborted) throw http.RequestAbortedException(request.url);
    if (path.endsWith('/objects')) objectRequests++;
    if (request.method == 'POST' && path.endsWith('/observations')) {
      manifestRequests++;
    }
    final response = await command({
      'command': 'http',
      'method': request.method,
      'path': path,
      'headers': request.headers,
      'body_base64': base64Encode(body)
    });
    if (aborted) throw http.RequestAbortedException(request.url);
    final bytes = base64Decode(response['body_base64'] as String);
    if (path.endsWith('/objects') && response['status'] == 200) {
      for (final c in (jsonDecode(utf8.decode(bytes)) as Map)['chunks']) {
        payloadBytes += (c['length'] as int);
      }
    }
    return http.StreamedResponse(Stream.value(bytes), response['status'] as int,
        headers: (response['headers'] as Map).cast<String, String>(),
        contentLength: bytes.length);
  }

  Future<void> dispose() async {
    await command({'command': 'exit'});
    await process.stdin.close();
    await process.exitCode;
    await lines.cancel();
  }
}

class GenerationFixture {
  GenerationFixture(Map<String, dynamic> value)
      : manifest = value['manifest'] as Map<String, dynamic>,
        objects = {
          for (final item in value['objects'])
            item['ref']['hash'] as String:
                base64Decode(item['data_base64'] as String)
        },
        rows = value['rows'] as Map<String, dynamic>,
        source = value['source'] as Map<String, dynamic>;
  final Map<String, dynamic> manifest, rows, source;
  final Map<String, Uint8List> objects;
  SyncTarget get target => SyncTarget.parse(manifest['target']);
  CacheNamespace get cache => CacheNamespace.forTarget(syntheticOrigin, target);
}

// Hash-valid negative graph variants: updates every ancestor and Target hash,
// so failures exercise membership/closure, not just a stale root checksum.
GenerationFixture mutateGraph(GenerationFixture original, String kind,
    void Function(Map<String, dynamic>) edit) {
  final rebuilt = <String, Uint8List>{},
      refs = <String, Map<String, dynamic>>{};
  var edited = false;
  Map<String, dynamic> visit(String hash) {
    if (refs.containsKey(hash)) return refs[hash]!;
    final b = jsonDecode(utf8.decode(original.objects[hash]!))
        as Map<String, dynamic>;
    if (b['kind'] == 'raw-root') {
      for (final entry in b['tables']) {
        entry['root']['ref'] = visit(entry['root']['ref']['hash']);
      }
    } else if (b['kind'] == 'snapshot-node') {
      for (final entry in b['children']) {
        entry['ref'] = visit(entry['ref']['hash']);
      }
    } else if (b['kind'] == 'index-root') {
      b['facts'] = visit(b['facts']['hash']);
    } else if (b['kind'] == 'index-node') {
      b['left'] = visit(b['left']['hash']);
      b['right'] = visit(b['right']['hash']);
    }
    if (b['kind'] == kind && !edited) {
      edit(b);
      edited = true;
    }
    final raw = encodeC1(b),
        ref = {
          'hash': objectHash(b['kind'] as String, raw),
          'bytes': '${raw.length}'
        };
    rebuilt[ref['hash']!] = raw;
    refs[hash] = ref;
    return ref;
  }

  final target = original.target.toJson()..remove('sync_root');
  for (final role in ['raw', 'index', 'hot', 'control']) {
    target['${role}_ref'] = visit(target['${role}_ref']['hash']);
  }
  target['sync_root'] = objectHash('view', encodeC1(target));
  return GenerationFixture({
    'manifest': {...original.manifest, 'target': target},
    'objects': [
      for (final e in rebuilt.entries)
        {
          'ref': {'hash': e.key, 'bytes': '${e.value.length}'},
          'data_base64': base64Encode(e.value)
        }
    ],
    'rows': original.rows,
    'source': original.source
  });
}

SyncReply remoteError(String code, String action, int status, String? nonce,
        {int? retry}) =>
    SyncReply(
        status,
        encodeC1({
          'protocol': 1,
          'request_id': nonce,
          'error': {
            'code': code,
            'action': action,
            'retry_after_ms': retry,
            'current_ns': null
          }
        }));

// Uses independently server-generated complete bytes. Negative mutations are
// explicitly test-only. Expected closure is fixture.objects, not E2 traversal.
class FixtureTransport implements SegmentedTransport {
  FixtureTransport(this.fixture);
  GenerationFixture fixture;
  @override
  String get origin => syntheticOrigin;
  bool authenticated = true, releaseSupported = true;
  final observations = <String, Map<String, dynamic>>{};
  final retired = <String>{};
  int objectRequests = 0, manifestRequests = 0, releases = 0, payloadBytes = 0;
  final requestedHashes = <String>[];
  final bodies = <Map<String, dynamic>>[];
  Future<SyncReply?> Function(String, String, Map<String, dynamic>?)? before;
  SyncReply Function(SyncReply, String, String, Map<String, dynamic>?)? after;
  @override
  void checkSession() {
    if (!authenticated) rejectSegment('AUTHENTICATION_CHANGED');
  }

  @override
  Future<SyncReply> exchange(String method, String path, Uint8List? raw,
      SyncCancellation cancellation, int maxResponseBytes) async {
    cancellation.check();
    checkSession();
    final body = raw == null ? null : decodeC1(raw) as Map<String, dynamic>;
    if (body != null) bodies.add(body);
    final injected = await before?.call(method, path, body);
    if (injected != null) return injected;
    SyncReply reply;
    if (method == 'DELETE') {
      releases++;
      if (!releaseSupported) return SyncReply(404, Uint8List(0));
      retired.add(path.split('/').last);
      return SyncReply(204, Uint8List(0));
    } else if (path.endsWith('/observations')) {
      manifestRequests++;
      final nonce = body!['request_id'] as String;
      final prior = observations[nonce];
      if (prior != null && retired.contains(prior['observation_id'])) {
        return remoteError(
            'OBSERVATION_EXPIRED', 'new_observation', 410, nonce);
      }
      final m = observations.putIfAbsent(
          nonce,
          () => {
                ...fixture.manifest,
                'request_id': nonce,
                'observation_id': syncUuid()
              });
      reply = SyncReply(prior == null ? 201 : 200, encodeC1(m));
    } else {
      objectRequests++;
      final observationId = path.split('/')[5];
      final nonce = body!['request_id'] as String;
      final item = (body['items'] as List).single as Map;
      final hashes = (item['path'] as List).cast<String>();
      requestedHashes.add(hashes.last);
      if (retired.contains(observationId)) {
        return remoteError(
            'OBSERVATION_EXPIRED', 'new_observation', 410, nonce);
      }
      final bytes = fixture.objects[hashes.last];
      if (bytes == null) {
        return remoteError(
            'OBSERVATION_INCOMPLETE', 'new_observation', 410, nonce);
      }
      final offset = int.parse(item['offset'] as String),
          length = item['length'] as int;
      payloadBytes += length;
      reply = SyncReply(
          200,
          encodeC1({
            'protocol': 1,
            'request_id': nonce,
            'observation_id': observationId,
            'chunks': [
              {
                'ref': {'hash': hashes.last, 'bytes': '${bytes.length}'},
                'offset': '$offset',
                'length': length,
                'data_base64':
                    base64Encode(bytes.sublist(offset, offset + length))
              }
            ]
          }));
    }
    final result = after?.call(reply, method, path, body) ?? reply;
    if (result.bytes.length > maxResponseBytes) {
      rejectSegment('RESPONSE_SIZE_EXCEEDED');
    }
    return result;
  }
}
