import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/authoritative_bundle.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';

// P2_N01_FIXTURES points to task-owned output of the backend coding benchmark.
// It contains only the preserved synthetic discovery fixtures and helper output.
void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final fixturePath = Platform.environment['P2_N01_FIXTURES'];
  final skip = fixturePath == null ? 'requires synthetic coding benchmark output' : false;
  test('actual IOClient preserves six coded response bodies and Snapshot integrity', () async {
    HttpOverrides.global = null;
    final root = Directory(fixturePath!);
    for (final n in [376, 1000, 10000]) {
      for (final route in ['bundle', 'snapshot']) {
        final raw = File('${root.path}/$n-$route.raw').readAsBytesSync();
        final encoded = File('${root.path}/$n-$route.gzip').readAsBytesSync();
        final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
        var gets = 0;
        server.listen((req) async {
          gets++;
          expect(req.method, 'GET');
          expect(req.uri.path, route == 'bundle' ? '/api/authoritative-state' : '/api/admin/snapshot');
          expect(req.headers.value('accept-encoding'), contains('gzip'));
          req.response.headers.set('Content-Encoding', 'gzip');
          req.response.headers.set('Content-Type', 'application/json');
          req.response.contentLength = encoded.length;
          req.response.add(encoded);
          await req.response.close();
        });
        final client = http.Client();
        final api = MoneyNoteApiClient(client: client, baseUrl: 'http://127.0.0.1:${server.port}');
        final dir = await Directory.systemTemp.createTemp('coding-snapshot-');
        try {
          final bytes = route == 'bundle' ? await api.authoritativeStateBytes() : (await api.downloadSnapshot()).bytes;
          expect(bytes.length, raw.length);
          expect(sha256.convert(bytes), sha256.convert(raw));
          if (route == 'bundle') {
            AuthoritativeBundle.decode(bytes);
          } else {
            final repository = LocalSnapshotRepository(directoryProvider: () async => dir);
            expect(await repository.save(bytes), hasLength(1));
            expect(await repository.list(), hasLength(1));
          }
          expect(gets, 1);
        } finally {
          client.close();
          await server.close(force: true);
          await dir.delete(recursive: true);
        }
      }
    }
  }, skip: skip);

  for (final defect in ['magic', 'truncated-middle', 'truncated-trailer', 'crc']) {
    test('damaged $defect gzip is rejected by transport or content admission', () async {
      HttpOverrides.global = null;
      final admitted = <String>[];
      final observations = <Map<String, Object?>>[];
      for (final route in ['bundle', 'snapshot']) {
        var encoded = File('$fixturePath/376-$route.gzip').readAsBytesSync().toList();
        if (defect == 'magic') encoded[0] = 0;
        if (defect == 'truncated-middle') encoded = encoded.sublist(0, encoded.length ~/ 2);
        if (defect == 'truncated-trailer') encoded = encoded.sublist(0, encoded.length - 8);
        if (defect == 'crc') encoded[encoded.length - 8] ^= 1;
        final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
        server.listen((req) async {
          req.response.headers.set('Content-Encoding', 'gzip');
          req.response.contentLength = encoded.length;
          req.response.add(encoded);
          await req.response.close();
        });
        final client = http.Client();
        final api = MoneyNoteApiClient(client: client, baseUrl: 'http://127.0.0.1:${server.port}');
        final dir = await Directory.systemTemp.createTemp('coding-damaged-');
        try {
          Object? failure;
          bool? originalBytesMatch;
          try {
            final original = File('$fixturePath/376-$route.raw').readAsBytesSync();
            if (route == 'bundle') {
              final bytes = await api.authoritativeStateBytes();
              originalBytesMatch = sha256.convert(bytes) == sha256.convert(original);
              AuthoritativeBundle.decode(bytes);
            } else {
              final repository = LocalSnapshotRepository(directoryProvider: () async => dir);
              final bytes = (await api.downloadSnapshot()).bytes;
              originalBytesMatch = sha256.convert(bytes) == sha256.convert(original);
              await repository.save(bytes);
            }
          } catch (error) {
            failure = error;
          }
          if (failure == null) admitted.add(route);
          observations.add({'route': route, 'rejected': failure != null, 'originalBytesMatch': originalBytesMatch, 'failureType': failure?.runtimeType.toString()});
        } finally {
          client.close();
          await server.close(force: true);
          await dir.delete(recursive: true);
        }
      }
      await File('$fixturePath/damage-$defect.json').writeAsString(jsonEncode(observations));
      expect(admitted, isEmpty, reason: 'Transport AND admission accepted $defect: $admitted');
    }, skip: skip);
  }

  test('valid gzip never bypasses Bundle or Snapshot content admission', () async {
    HttpOverrides.global = null;
    for (final route in ['bundle', 'snapshot']) {
      final raw = File('$fixturePath/376-$route.raw').readAsBytesSync();
      final value = jsonDecode(utf8.decode(raw)) as Map<String, dynamic>;
      final snapshot = route == 'bundle' ? value['snapshot'] : value;
      // Bundle admission verifies the digest. The local backup repository checks
      // the envelope/durable bytes; server restore owns full Snapshot validation.
      snapshot['manifest']['content_sha256'] = route == 'bundle' ? '0' * 64 : 'invalid-digest';
      final encoded = gzip.encode(utf8.encode(jsonEncode(value)));
      final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
      server.listen((req) async {
        req.response.headers.set('Content-Encoding', 'gzip');
        req.response.contentLength = encoded.length;
        req.response.add(encoded);
        await req.response.close();
      });
      final client = http.Client();
      final api = MoneyNoteApiClient(client: client, baseUrl: 'http://127.0.0.1:${server.port}');
      final dir = await Directory.systemTemp.createTemp('coding-reject-');
      try {
        if (route == 'bundle') {
          final bytes = await api.authoritativeStateBytes();
          expect(() => AuthoritativeBundle.decode(bytes), throwsFormatException);
        } else {
          final repository = LocalSnapshotRepository(directoryProvider: () async => dir);
          await repository.save(raw);
          final bytes = (await api.downloadSnapshot()).bytes;
          await expectLater(repository.save(bytes), throwsA(anything));
          expect(await repository.list(), hasLength(1));
        }
      } finally {
        client.close();
        await server.close(force: true);
        await dir.delete(recursive: true);
      }
    }
  }, skip: skip);
}
