// 감사 전용: 실제 IOClient와 교정 transport를 사용하며 서버는 별도 Python process다.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:http/http.dart' as http;
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

class MeasuredClient extends http.BaseClient {
  MeasuredClient(int limit)
    : inner = IOClient(
        HttpClient()
          ..badCertificateCallback = ((_, __, ___) => true)
          ..maxConnectionsPerHost = limit,
      );
  final IOClient inner;
  String mode = 'valid', token = 'synthetic-only';
  int closeCalls = 0;
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final sentMode = mode;
    request.headers['X-Audit-Mode'] = sentMode;
    final response = await inner.send(request);
    if (sentMode == 'auth') token = '$token-next';
    return response;
  }

  @override
  void close() {
    closeCalls++;
    inner.close();
  }
}

Future<void> main(List<String> args) async {
  final job = jsonDecode(File(args.single).readAsStringSync()) as Map;
  final golden =
      jsonDecode(File(job['golden'] as String).readAsStringSync()) as Map;
  final object = (golden['objects'] as List).cast<Map>().singleWhere(
    (o) => o['kind'] == 'raw-root',
  );
  final manifest = ObservationManifest.fromBytes(
    base64Decode(golden['manifest_base64'] as String),
  );
  final cache = CacheNamespace.forTarget(
    'https://synthetic.invalid',
    manifest.target,
  );
  final client = MeasuredClient(job['limit'] as int);
  Future<Map>? pending;
  Future<Map> exchange(String mode) async {
    client.mode = mode;
    final transport = AuthenticatedSegmentedTransport(
      client: client,
      origin: job['origin'] as String,
      credential: () => client.token,
      timeout: const Duration(seconds: 1),
    );
    final watch = Stopwatch()..start();
    try {
      final reply = await transport.exchange(
        'POST',
        '/api/sync/v1/observations',
        null,
        SyncCancellation(),
        1048576,
      );
      final verified = VerifiedObject.verify(
        reply.bytes,
        ObjectRef.parse(object['ref']),
        cache,
      );
      return {
        'result': 'VERIFIED',
        'kind': verified.kind,
        'bytes': base64Encode(reply.bytes),
        'hash': sha256.convert([
          ...ascii.encode('money-note.sync.v1/raw-root'),
          0,
          ...reply.bytes,
        ]).toString(),
        'milliseconds': watch.elapsedMicroseconds / 1000,
        'client_close_calls': client.closeCalls,
      };
    } on Object catch (error) {
      return {
        'result': error.toString(),
        'milliseconds': watch.elapsedMicroseconds / 1000,
        'client_close_calls': client.closeCalls,
      };
    }
  }

  stdout.writeln(jsonEncode({'ready': true, 'pid': pid}));
  await for (final line
      in stdin.transform(utf8.decoder).transform(const LineSplitter())) {
    final command = jsonDecode(line) as Map;
    final action = command['action'];
    if (action == 'exit') break;
    if (action == 'begin-valid') {
      pending = exchange('hold-valid');
      stdout.writeln(jsonEncode({'started': true}));
    } else if (action == 'finish-valid') {
      stdout.writeln(jsonEncode(await pending!));
    } else {
      stdout.writeln(jsonEncode(await exchange(command['mode'] as String)));
    }
  }
  client.close();
}
