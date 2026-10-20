@Timeout(Duration(minutes: 5))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http_api;
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

import '../t66f-b02-implementation/verification_profile.dart';

class _ActualHttp extends HttpOverrides {}

class _ProbeIOClient extends IOClient {
  _ProbeIOClient(super.inner, this.log);
  final File log;
  @override
  Future<IOStreamedResponse> send(http_api.BaseRequest request) async {
    log.writeAsStringSync(
      'SEND ${request.method} ${request.url.path}\n',
      mode: FileMode.append,
    );
    try {
      final r = await super.send(request);
      log.writeAsStringSync('HEADERS ${r.statusCode}\n', mode: FileMode.append);
      return r;
    } catch (error, stack) {
      log.writeAsStringSync(
        'RAW_IO ${error.runtimeType}: $error\n$stack\n',
        mode: FileMode.append,
      );
      rethrow;
    }
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('A01 cached-prefix diagnostic, controlled mock HTTP rejection; NOT full D-E', () async {
    final out = Directory(const String.fromEnvironment('B02_OUT'));
    final raw = jsonDecode(
      File('${out.path}/server/manifest-1.json').readAsStringSync(),
    ) as Map;
    final result =
        jsonDecode(File('${out.path}/result.json').readAsStringSync()) as Map;
    final origin = result['origin'] as String;
    final root = Directory(
      '${out.path}/reuse-client-${DateTime.now().microsecondsSinceEpoch}',
    );
    final copy = await Process.run('cp', [
      '-a',
      '${out.path}/client',
      root.path,
    ]);
    expect(copy.exitCode, 0);
    final context = SecurityContext()
      ..useCertificateChain('${out.path}/server/synthetic-cert.pem')
      ..usePrivateKey('${out.path}/server/synthetic-key.pem');
    final server = await HttpServer.bindSecure(
      InternetAddress.loopbackIPv4,
      Uri.parse(origin).port,
      context,
    );
    var objects = 0, observations = 0;
    server.listen((request) async {
      final bytes = await request.fold<List<int>>(
        [],
        (all, next) => all..addAll(next),
      );
      final body = bytes.isEmpty
          ? <String, dynamic>{}
          : jsonDecode(utf8.decode(bytes)) as Map;
      if (request.method == 'DELETE') {
        request.response.statusCode = 204;
        await request.response.close();
        return;
      }
      request.response.headers.contentType = ContentType.json;
      if (request.uri.path.endsWith('/observations')) {
        observations++;
        final now = DateTime.now().toUtc();
        String stamp(DateTime t) => '${t.toIso8601String().substring(0, 19)}Z';
        request.response.statusCode = 201;
        request.response.add(
          utf8.encode(
            jsonEncode({
              ...raw,
              'request_id': body['request_id'],
              'observation_id': syncUuid(),
              'validated_at': stamp(now),
              'expires_at': stamp(now.add(const Duration(seconds: 900))),
            }),
          ),
        );
      } else {
        objects++;
        request.response.statusCode = 422;
        request.response.add(
          utf8.encode(
            jsonEncode({
              'protocol': 1,
              'request_id': body['request_id'],
              'error': {
                'code': 'INVALID_REQUEST',
                'action': 'blocked',
                'retry_after_ms': null,
                'current_ns': null,
              },
            }),
          ),
        );
      }
      await request.response.close();
    });
    final log = File('${out.path}/reuse-raw-error-v2.log');
    final native = HttpOverrides.runWithHttpOverrides(
      () => HttpClient(),
      _ActualHttp(),
    )..maxConnectionsPerHost = 1;
    native.badCertificateCallback = (_, host, port) =>
        host == '127.0.0.1' && port == Uri.parse(origin).port;
    final client = _ProbeIOClient(native, log);
    final target = SyncTarget.parse(raw['target']);
    final store = SegmentedClientStore.open(
      root,
      CacheNamespace.forTarget(origin, target),
      adapters: true,
      limits: largeVerificationStoreLimits,
    );
    final watch = Stopwatch()..start();
    Object? failure;
    try {
      await runZoned(
        () async {
          final transport = AuthenticatedSegmentedTransport(
            client: client,
            origin: origin,
            credential: () => 'a01-disposable-diagnostic',
          );
          await IncrementalFetcher(
            store,
            transport,
            limits: largeVerificationFetchLimits,
          ).acquire();
        },
        zoneSpecification: ZoneSpecification(
          errorCallback: (self, parent, zone, error, stack) {
            if (error is! SegmentedException &&
                error is! AcquisitionFailure &&
                error is! SyncRemoteException) {
              try {
                log.writeAsStringSync(
                  'RAW_ZONE ${error.runtimeType}: $error\n$stack\n',
                  mode: FileMode.append,
                );
              } catch (_) {}
            }
            return parent.errorCallback(zone, error, stack);
          },
        ),
      );
    } catch (error, stack) {
      failure = error;
      File('${out.path}/reuse-result-v2.json').writeAsStringSync(
        const JsonEncoder.withIndent('  ').convert({
          'label': 'NARROW DIAGNOSTIC, MOCK MANIFEST/422 OVER REAL IOCLIENT; NOT BACKEND D-E',
          'error': error.toString(),
          'stack': stack.toString(),
          'elapsed_us': watch.elapsedMicroseconds,
          'observations': observations,
          'object_requests_reached_server': objects,
          'work': store.work.snapshot(),
          'accepted_id': store.acceptedGeneration().id,
        }),
      );
    } finally {
      store.close();
      client.close();
      await server.close(force: true);
    }
    expect(failure, isNotNull);
  });
}
