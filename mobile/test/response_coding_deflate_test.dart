import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:archive/archive.dart';
import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';

// Test fixture encoder only: non-final stored blocks, then chosen terminator.
List<int> storedWitness(List<int> raw, List<int> terminator) {
  final out = BytesBuilder()..add([31, 139, 8, 0, 0, 0, 0, 0, 0, 3]);
  for (var offset = 0; offset < raw.length; offset += 65535) {
    final end = (offset + 65535 < raw.length) ? offset + 65535 : raw.length;
    final n = end - offset;
    final inverse = n ^ 65535;
    out.add([0, n & 255, n >> 8, inverse & 255, inverse >> 8]);
    out.add(raw.sublist(offset, end));
  }
  out.add(terminator);
  final trailer = ByteData(8)
    ..setUint32(0, getCrc32(raw), Endian.little)
    ..setUint32(4, raw.length, Endian.little);
  out.add(trailer.buffer.asUint8List());
  return out.takeBytes();
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  final root = Platform.environment['P2_N01_FIXTURES'];
  test('reserved BTYPE and absent final block are rejected through actual API',
      () async {
    HttpOverrides.global = null;
    final results = <Map<String, Object?>>[];
    final failures = <String>[];
    for (final endpoint in ['bundle', 'snapshot']) {
      final raw = File('$root/376-$endpoint.raw').readAsBytesSync();
      for (final kind in [
        'valid-final',
        'reserved',
        'missing-final',
        'nonfinal-empty'
      ]) {
        final end = kind == 'valid-final'
            ? [1, 0, 0, 255, 255]
            : kind == 'reserved'
                ? [7]
                : kind == 'nonfinal-empty'
                    ? [0, 0, 0, 255, 255]
                    : <int>[];
        final data = storedWitness(raw, end);
        final input = InputStream(data);
        bool archiveAccept = false;
        bool sdkAccept = false;
        try {
          archiveAccept =
              sha256.convert(GZipDecoder().decodeBuffer(input, verify: true)) ==
                  sha256.convert(raw);
        } catch (_) {}
        try {
          sdkAccept = sha256.convert(gzip.decode(data)) == sha256.convert(raw);
        } catch (_) {}
        if (kind == 'reserved') {
          if (endpoint == 'bundle') {
            // Exact auditor bad.gz, reconstructed without relying on /tmp.
            expect(sha256.convert(data).toString(),
                '4f94389bcc067b4e756cc0e94f65ef8be9f2f8e04116add5fb83da93d0574e5e');
          }
          expect(archiveAccept, isTrue);
          expect(input.position, data.length);
          expect(sdkAccept, isFalse);
        }
        final server = await HttpServer.bind(InternetAddress.loopbackIPv4, 0);
        var count = 0;
        server.listen((r) async {
          count++;
          r.response.headers.set('Content-Encoding', 'gzip');
          r.response.contentLength = data.length;
          r.response.add(data);
          await r.response.close();
        });
        final api =
            MoneyNoteApiClient(baseUrl: 'http://127.0.0.1:${server.port}');
        bool success = false;
        try {
          final bytes = endpoint == 'bundle'
              ? await api.authoritativeStateBytes()
              : (await api.downloadSnapshot()).bytes;
          success = sha256.convert(bytes) == sha256.convert(raw);
        } catch (_) {
        } finally {
          await server.close(force: true);
        }
        expect(count, 1);
        if (success != (kind == 'valid-final')) failures.add('$endpoint:$kind');
        results.add({
          'endpoint': endpoint,
          'kind': kind,
          'archiveAccept': archiveAccept,
          'sdkAccept': sdkAccept,
          'apiSuccess': success,
          'sha256': sha256.convert(data).toString(),
          'requests': count
        });
      }
    }
    await File('$root/r1-witness-results.json')
        .writeAsString(jsonEncode(results));
    expect(failures, isEmpty, reason: 'Malformed DEFLATE accepted: $failures');
  }, skip: root == null ? 'requires synthetic fixtures' : false);
  test('bounded incremental SDK validation cost', () async {
    final rows = <Map<String, Object?>>[];
    final hz = int.parse(Process.runSync('/usr/bin/getconf', ['CLK_TCK'])
        .stdout
        .toString()
        .trim());
    int ticks() {
      final f = File('/proc/self/stat')
          .readAsStringSync()
          .split(')')
          .last
          .trim()
          .split(RegExp(r'\s+'));
      return int.parse(f[11]) + int.parse(f[12]);
    }

    for (final n in [376, 1000, 10000]) {
      for (final route in ['bundle', 'snapshot']) {
        final data = File('$root/$n-$route.gzip').readAsBytesSync();
        final expected = GZipDecoder().decodeBytes(data, verify: true);
        void validate() {
          final sink = ComparisonProbe(expected);
          final input = gzip.decoder.startChunkedConversion(sink);
          input.add(data);
          input.close();
          expect(sink.offset, expected.length);
        }

        for (var i = 0; i < 5; i++) {
          validate();
        }
        final before = ticks();
        final rss = ProcessInfo.currentRss;
        final samples = <int>[];
        for (var i = 0; i < 20; i++) {
          final c = Stopwatch()..start();
          validate();
          c.stop();
          samples.add(c.elapsedMicroseconds);
        }
        rows.add({
          'rows': n,
          'route': route,
          'wallUs': samples,
          'cpuBatchMs': (ticks() - before) * 1000 / hz,
          'rssBefore': rss,
          'rssAfter': ProcessInfo.currentRss,
          'maxRss': ProcessInfo.maxRss
        });
      }
    }
    await File('$root/r1-incremental-resources.json')
        .writeAsString(jsonEncode(rows));
  }, skip: root == null ? 'requires synthetic fixtures' : false);
}

// Benchmark replica of the production streaming comparison; no full output copy.
class ComparisonProbe implements Sink<List<int>> {
  ComparisonProbe(this.expected);
  final List<int> expected;
  int offset = 0;
  @override
  void add(List<int> data) {
    for (final b in data) {
      if (offset >= expected.length || expected[offset++] != b) {
        throw const FormatException('mismatch');
      }
    }
  }

  @override
  void close() {
    if (offset != expected.length) throw const FormatException('incomplete');
  }
}
