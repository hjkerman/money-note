import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/response_coding_client.dart';
import 'authoritative_bundle_test.dart' show owner;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final root = Platform.environment['P2_N01_FIXTURES'];
  final skip = root == null ? 'requires synthetic fixtures' : false;
  test('default transport rejects wire matrix before successful completion',
      () async {
    HttpOverrides.global = null;
    final results = <Map<String, Object?>>[];
    for (final endpoint in ['bundle', 'snapshot']) {
      final raw = File('$root/376-$endpoint.raw').readAsBytesSync();
      final good = File('$root/376-$endpoint.gzip').readAsBytesSync();
      for (final mode in [
        'gzip',
        'identity',
        'missing-header',
        'unsupported',
        'isize',
        'trailer',
        'crc',
        'magic',
        'middle',
        'extra',
        'members',
        'flags',
        'length',
        'premature',
        'status'
      ]) {
        var data = good.toList();
        String? coding = 'gzip';
        int status = 200;
        if (mode == 'identity') {
          data = raw;
          coding = null;
        }
        if (mode == 'missing-header') coding = null;
        if (mode == 'unsupported') coding = 'br';
        if (mode == 'isize') data[data.length - 1] ^= 1;
        if (mode == 'trailer') data = data.sublist(0, data.length - 8);
        if (mode == 'crc') data[data.length - 8] ^= 1;
        if (mode == 'magic') data[0] = 0;
        if (mode == 'middle') data = data.sublist(0, data.length ~/ 2);
        if (mode == 'extra') data = [...data, 1];
        if (mode == 'members') data = [...data, ...good];
        if (mode == 'flags') data[3] = 2;
        if (mode == 'status') {
          status = 401;
          coding = null;
          data = utf8.encode('{"detail":"authentication required"}');
        }
        final server = await ServerSocket.bind(InternetAddress.loopbackIPv4, 0);
        var gets = 0;
        server.listen((socket) {
          socket.listen((request) async {
            gets++;
            expect(latin1.decode(request).toLowerCase(),
                contains('authorization: bearer synthetic-a01'));
            socket.add(latin1.encode(
                'HTTP/1.1 $status Result\r\nContent-Type: application/json\r\nConnection: close\r\n${coding == null ? '' : 'Content-Encoding: $coding\r\n'}Content-Length: ${data.length + ([
                      'length',
                      'premature'
                    ].contains(mode) ? 20 : 0)}\r\n\r\n'));
            socket.add(data);
            await socket.flush();
            socket.destroy();
          });
        });
        final api =
            MoneyNoteApiClient(baseUrl: 'http://127.0.0.1:${server.port}');
        FlutterSecureStorage.setMockInitialValues(
            {'money_note_session_token': 'synthetic-a01'});
        await api.loadSession();
        Object? error;
        bool exact = false;
        try {
          final bytes = endpoint == 'bundle'
              ? await api.authoritativeStateBytes()
              : (await api.downloadSnapshot()).bytes;
          exact = sha256.convert(bytes) == sha256.convert(raw);
          // Missing metadata is an identity response, never guessed as gzip. JSON
          // consumers reject these bytes; the transport must not auto-detect coding.
          if (mode == 'missing-header')
            expect(() => jsonDecode(utf8.decode(bytes)), throwsA(anything));
        } catch (e) {
          error = e;
        } finally {
          await server.close();
        }
        if (['gzip', 'identity'].contains(mode)) {
          expect(error, isNull, reason: '$endpoint $mode');
          expect(exact, isTrue);
        } else {
          expect(error, isNotNull, reason: '$endpoint $mode');
        }
        expect(gets, 1);
        results.add({
          'endpoint': endpoint,
          'mode': mode,
          'error': error?.runtimeType.toString(),
          'exact': exact,
          'gets': gets
        });
      }
    }
    await File('$root/wire-matrix.json').writeAsString(jsonEncode(results));
  }, skip: skip);
  test(
      'transport failure preserves published baseline UI pending and backup boundary',
      () async {
    HttpOverrides.global = null;
    final raw = File('$root/376-bundle.raw').readAsBytesSync();
    final good = File('$root/376-bundle.gzip').readAsBytesSync();
    final entry =
        (jsonDecode(utf8.decode(raw))['state']['entries'] as List).first;
    var broken = false;
    var posts = 0;
    var gets = 0;
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((req) async {
      if (req.method == 'POST') {
        posts++;
        await req.drain<void>();
        req.response.add(utf8.encode(jsonEncode(entry)));
      } else {
        gets++;
        req.response.headers.set('Content-Encoding', 'gzip');
        req.response.add(broken ? good.sublist(0, good.length - 8) : good);
      }
      await req.response.close();
    });
    final client = IOClient(HttpClient()..autoUncompress = false);
    final api = MoneyNoteApiClient(
        client: client, baseUrl: 'http://127.0.0.1:${server.port}');
    final dir = await Directory.systemTemp.createTemp('coding-state-');
    final store = OfflineStore(directoryProvider: () async => dir);
    final state = AppState(api,
        offlineStore: store,
        connectivityRetryDelay: (_) => Completer<void>().future)
      ..user = owner
      ..isBootstrapping = false;
    try {
      await state.refreshInputArea(notify: false);
      final file = File('${dir.path}/offline-mode/baseline.json');
      final before = await file.readAsBytes();
      final summary = state.summary;
      broken = true;
      expect(
          await state.createExpense(
              usagePlace: 'shop',
              usageItem: 'test',
              amount: 100,
              discountEnabled: true),
          isFalse);
      expect(await file.readAsBytes(), before);
      expect(state.summary, same(summary));
      expect(await store.loadPendingOnlineWrite(owner.id), isNotNull);
      expect(posts, 1);
      expect(gets, 2);
    } finally {
      state.dispose();
      client.close();
      await server.close(force: true);
      await dir.delete(recursive: true);
    }
  }, skip: skip);
  test('cancellation and decoded response headers remain consistent', () async {
    HttpOverrides.global = null;
    final data = File('$root/376-bundle.gzip').readAsBytesSync();
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    server.listen((r) async {
      r.response.headers.set('Content-Encoding', 'gzip');
      r.response.contentLength = data.length;
      r.response.add(data);
      await r.response.close();
    });
    final client = ResponseCodingClient();
    final abort = Completer<void>();
    try {
      final r = await client.get(
          Uri.parse('http://127.0.0.1:${server.port}/api/authoritative-state'));
      expect(r.headers.containsKey('content-encoding'), isFalse);
      expect(r.contentLength, r.bodyBytes.length);
      abort.complete();
      await expectLater(
          client.send(http.AbortableRequest(
              'GET',
              Uri.parse(
                  'http://127.0.0.1:${server.port}/api/authoritative-state'),
              abortTrigger: abort.future)),
          throwsA(anything));
    } finally {
      client.close();
      await server.close(force: true);
    }
  }, skip: skip);
  test('API timeout does not repeat an authoritative GET', () async {
    HttpOverrides.global = null;
    final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
    var gets = 0;
    server.listen((r) {
      gets++;
    });
    final api = MoneyNoteApiClient(baseUrl: 'http://127.0.0.1:${server.port}');
    try {
      await expectLater(api.authoritativeStateBytes(), throwsA(anything));
      expect(gets, 1);
    } finally {
      await server.close(force: true);
    }
  }, skip: skip);
}
