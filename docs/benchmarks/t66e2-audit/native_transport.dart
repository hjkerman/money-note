import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:sqlite3/sqlite3.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

late Map job;
SecurityContext context() => SecurityContext()
  ..useCertificateChain(job['cert'] as String)
  ..usePrivateKey(job['key'] as String);

// E2-A01 correction oracle: an unfinished server HttpResponse pauses its parser
// and can remain "active" after the peer closes. Keep that historical counter,
// but independently count this client's actual TCP FD to the synthetic port.
Future<int> clientSocketOwners(int port) async {
  final result = await Process.run('ss', [
    '-Htnp',
    'state',
    'all',
    'dst',
    '127.0.0.1',
    'dport',
    '=',
    ':$port',
  ]).timeout(const Duration(seconds: 2));
  if (result.exitCode != 0) throw StateError('TCP_ORACLE_FAILED');
  return (result.stdout as String)
      .split('\n')
      .where((line) => line.contains('pid=$pid,'))
      .length;
}

Future<Map<String, dynamic>> trial(String mode) async {
  final ctx = context();
  final server = await HttpServer.bindSecure(
    InternetAddress.loopbackIPv4,
    0,
    ctx,
  );
  var token = 'synthetic-original', requests = 0;
  final pending = <HttpResponse>[];
  server.listen((r) async {
    requests++;
    await r.drain<void>();
    if (requests == 1 && mode != 'positive') {
      if (mode == 'auth') token = 'synthetic-new';
      if (mode == 'redirect') {
        r.response.statusCode = 302;
        r.response.headers.set('Location', 'https://other.invalid');
      }
      r.response.bufferOutput = false;
      r.response.contentLength = 1048576;
      pending.add(r.response);
      r.response.add(List.filled(1024, 65));
      try {
        await r.response.flush();
      } catch (_) {}
    } else {
      r.response.write('{}');
      try {
        await r.response.close();
      } catch (_) {}
    }
  });
  final native = HttpClient()
    ..badCertificateCallback = ((_, __, ___) => true)
    ..maxConnectionsPerHost = 1;
  final client = IOClient(native);
  final url = 'https://127.0.0.1:${server.port}';
  Future<String> request() async {
    try {
      final response =
          await AuthenticatedSegmentedTransport(
            client: client,
            origin: url,
            credential: () => token,
            timeout: const Duration(seconds: 1),
          ).exchange(
            'POST',
            '/api/sync/v1/observations',
            utf8.encode('{}'),
            SyncCancellation(),
            mode == 'oversized' ? 2048 : 1048576,
          );
      return 'HTTP_${response.status}';
    } catch (e) {
      return e.toString();
    }
  }

  final first = await request();
  final before = server.connectionsInfo();
  final clientBefore = await clientSocketOwners(server.port);
  final second = await request();
  final after = server.connectionsInfo();
  final clientAfter = await clientSocketOwners(server.port);
  client.close();
  await server.close(force: true);
  return {
    'mode': mode,
    'first': first,
    'second': second,
    'server_requests': requests,
    'active_after_first': before.active,
    'active_after_second': after.active,
    'total_connections': after.total,
    'held_responses': pending.length,
    'client_fd_after_first': clientBefore,
    'client_fd_after_second': clientAfter,
  };
}

Future<void> main(List<String> args) async {
  job = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final results = <Map>[];
  for (final mode in ['positive', 'auth', 'redirect', 'oversized'])
    results.add(await trial(mode));
  results.add(await repeatedAcquisition());
  print(jsonEncode(results));
}

Future<Map<String, dynamic>> repeatedAcquisition() async {
  final server = await HttpServer.bindSecure(
    InternetAddress.loopbackIPv4,
    0,
    context(),
  );
  var requests = 0;
  server.listen((r) async {
    requests++;
    await r.drain<void>();
    r.response.bufferOutput = false;
    r.response.contentLength = 8 * 1048576 + 1;
    r.response.add(List.filled(1024, 65));
    try {
      await r.response.flush();
    } catch (_) {}
  });
  final native = HttpClient()..badCertificateCallback = ((_, __, ___) => true);
  final client = IOClient(native), origin = 'https://127.0.0.1:${server.port}';
  final fixture =
      jsonDecode(File(job['fixture'] as String).readAsStringSync()) as Map;
  final target = SyncTarget.parse(fixture['manifest']['target']);
  final store = SegmentedClientStore.open(
    Directory(job['root'] as String),
    CacheNamespace.forTarget(origin, target),
    acquisition: true,
  );
  final errors = <String>[], active = <int>[], clientActive = <int>[];
  for (var i = 0; i < 6; i++) {
    try {
      await IncrementalFetcher(
        store,
        AuthenticatedSegmentedTransport(
          client: client,
          origin: origin,
          credential: () => 'synthetic-only',
          timeout: const Duration(seconds: 1),
        ),
        limits: const FetchLimits(attempts: 1),
      ).acquire();
      errors.add('UNEXPECTED_SUCCESS');
    } on AcquisitionFailure catch (e) {
      errors.add(e.code);
    }
    active.add(server.connectionsInfo().active);
    clientActive.add(await clientSocketOwners(server.port));
  }
  final path = store.path;
  store.close();
  final inspection = sqlite3.open(path);
  final objects = inspection
      .select('SELECT count(*) AS n FROM objects')
      .single['n'];
  final stages = inspection
      .select('SELECT count(*) AS n FROM staging')
      .single['n'];
  inspection.dispose();
  client.close();
  await server.close(force: true);
  return {
    'mode': 'repeated-acquisition',
    'errors': errors,
    'active_after_each_failure': active,
    'client_fd_after_each_failure': clientActive,
    'server_requests': requests,
    'objects': objects,
    'stages': stages,
    'path': path,
  };
}
