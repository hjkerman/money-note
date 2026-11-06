@Timeout(Duration(minutes: 18))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/diagnostics/logical_cost.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

void main() {
  test(
    'P01 bounded real 100k D3 TLS packets enabled/disabled same paths',
    () async {
      final root = Directory.current.parent.path;
      final out = Directory('$root/docs/benchmarks/t66f-b03-ic01-p01/evidence');
      final temp = Directory.systemTemp.createTempSync('mn-p01-packet-server-');
      final process = await Process.start('$root/.venv/bin/python', [
        '$root/docs/benchmarks/t66f-b03-ic01-p01/packet_server.py',
        '100000',
        '${temp.path}/server',
      ]);
      final errors = StringBuffer();
      process.stderr.transform(utf8.decoder).listen((s) {
        if (errors.length < 65536) errors.write(s);
      });
      final lines = StreamIterator(
        process.stdout.transform(utf8.decoder).transform(const LineSplitter()),
      );
      IOClient? client;
      Future<Map> command(Map r) async {
        process.stdin.writeln(jsonEncode(r));
        await process.stdin.flush();
        expect(
          await lines.moveNext().timeout(const Duration(seconds: 30)),
          true,
        );
        return jsonDecode(lines.current) as Map;
      }

      try {
        expect(
          await lines.moveNext().timeout(const Duration(minutes: 14)),
          true,
          reason: errors.toString(),
        );
        final initial = jsonDecode(lines.current) as Map;
        expect(initial['fixture']['graph']['objects'], 400532);
        final origin = initial['origin'] as String,
            token = initial['token'] as String;
        client = IOClient(
          HttpClient()
            ..badCertificateCallback = ((cert, host, port) =>
                host == '127.0.0.1'),
        );
        final transport = AuthenticatedSegmentedTransport(
          client: client,
          origin: origin,
          credential: () => token,
          timeout: const Duration(seconds: 60),
        );
        final cancel = SyncCancellation();
        final nonce = syncUuid();
        final observed = await transport.exchange(
          'POST',
          '/api/sync/v1/observations',
          encodeC1({
            'protocol': 1,
            'request_id': nonce,
            'base': null,
            'inline_bytes': 0,
          }),
          cancel,
          8 * 1048576,
        );
        expect(observed.status, 201);
        final manifest = ObservationManifest.fromBytes(observed.bytes);
        final cache = CacheNamespace.forTarget(origin, manifest.target);
        final frontier = <({ObjectRef ref, List<String> path})>[
          (
            ref: manifest.target.roots['index']!,
            path: [manifest.target.roots['index']!.hash],
          ),
        ];
        final packets = <List<({ObjectRef ref, List<String> path})>>[];
        final rawReplies = <List<List<int>>>[];
        final kinds = <String, int>{};
        Future<List<VerifiedObject>> send(
          List<({ObjectRef ref, List<String> path})> packet, {
          bool enabled = false,
          bool discovery = false,
        }) async {
          final c = LogicalCost();
          final nonce = syncUuid();
          final request = encodeC1({
            'protocol': 1,
            'request_id': nonce,
            'items': [
              for (final e in packet)
                {'path': e.path, 'offset': '0', 'length': e.ref.byteLength},
            ],
          });
          final watch = Stopwatch()..start();
          final reply = await transport.exchange(
            'POST',
            '/api/sync/v1/observations/${manifest.id}/objects',
            request,
            cancel,
            3 * 1048576,
          );
          final httpUs = watch.elapsedMicroseconds;
          expect(reply.status, 200);
          List<VerifiedObject> verify() {
            final body = decodeC1(reply.bytes) as Map;
            expect(body['request_id'], nonce);
            expect(body['observation_id'], manifest.id);
            final chunks = (body['chunks'] as List)
                .map(ObjectChunk.parse)
                .toList();
            expect(chunks.length, packet.length);
            return [
              for (var i = 0; i < chunks.length; i++)
                VerifiedObject.verify(chunks[i].bytes, packet[i].ref, cache),
            ];
          }

          final vclock = Stopwatch()..start();
          final values = enabled
              ? c.run(LogicalCostStage.e2, verify)
              : verify();
          final validateUs = vclock.elapsedMicroseconds;
          if (!discovery)
            samples.add({
              'enabled': enabled,
              'packet_objects': packet.length,
              'request_bytes': request.length,
              'response_bytes': reply.bytes.length,
              'decoded_bytes': packet.fold<int>(
                0,
                (n, e) => n + e.ref.byteLength,
              ),
              'path_min': packet
                  .map((e) => e.path.length)
                  .reduce((a, b) => a < b ? a : b),
              'path_max': packet
                  .map((e) => e.path.length)
                  .reduce((a, b) => a > b ? a : b),
              'http_us': httpUs,
              'validation_us': validateUs,
              'primitive': c.snapshot(),
              'rss_bytes': ProcessInfo.currentRss,
            });
          c.close();
          return values;
        }

        for (var n = 0; n < 24 && frontier.isNotEmpty; n++) {
          final packet = <({ObjectRef ref, List<String> path})>[];
          var bytes = 0;
          while (frontier.isNotEmpty &&
              packet.length < 64 &&
              bytes + frontier.last.ref.byteLength <= 1048576) {
            final e = frontier.removeLast();
            packet.add(e);
            bytes += e.ref.byteLength;
          }
          expect(packet, isNotEmpty);
          final values = await send(packet, discovery: true);
          for (var i = 0; i < values.length; i++) {
            kinds.update(values[i].kind, (n) => n + 1, ifAbsent: () => 1);
            for (final child in values[i].children)
              frontier.add((
                ref: child.ref,
                path: [...packet[i].path, child.ref.hash],
              ));
          }
          packets.add(packet);
          rawReplies.add([for (final v in values) v.bytes]);
        }
        final selected = packets
            .asMap()
            .entries
            .where(
              (e) =>
                  e.value.length == 64 &&
                  e.value.any((p) => p.path.length >= 18),
            )
            .map((e) => e.key)
            .toList()
            .reversed
            .take(3)
            .toList();
        expect(selected.length, 3);
        for (var repeat = 0; repeat < 6; repeat++) {
          for (final enabled in repeat.isEven ? [false, true] : [true, false]) {
            await command({'command': 'p01_mode', 'enabled': enabled});
            final before = samples.length;
            for (final i in selected) {
              final values = await send(packets[i], enabled: enabled);
              for (var j = 0; j < values.length; j++)
                expect(values[j].bytes, rawReplies[i][j]);
            }
            if (repeat == 0) samples.removeRange(before, samples.length);
          }
        }
        final snapshot = await command({'command': 'p01_snapshot'});
        expect(snapshot['complete'], true);
        expect(snapshot['pending'], 0);
        expect(snapshot['started'], snapshot['completed']);
        await command({'command': 'p01_mode', 'enabled': false});
        final release = await transport.exchange(
          'DELETE',
          '/api/sync/v1/observations/${manifest.id}',
          null,
          cancel,
          16384,
        );
        expect(release.status, 204);
        File('${out.path}/packet-results.json').writeAsStringSync(
          jsonEncode({
            'schema_version': 1,
            'fixture': initial['fixture']['graph'],
            'manifest_target': manifest.target.toJson(),
            'created_at': manifest.validatedAt.toIso8601String(),
            'expires_at': manifest.expiresAt.toIso8601String(),
            'discovered_objects': kinds.values.fold<int>(0, (a, b) => a + b),
            'discovery_kinds': kinds,
            'samples': samples,
            'backend': snapshot,
            'client_peak_rss': ProcessInfo.maxRss,
            'full_100k_acquisition_attempts': 0,
            'limits': 'actual bounded typed HTTP packets, not full E2 closure/staging/publication; no deliberate expiry/renewal',
          }),
        );
        // Close the owned keep-alive client before joining the TLS worker.
        // The native exit==0 assertion remains strict. The previous failing
        // revision/log is archived; no second 100k preflight is implied.
        client.close();
        await command({'command': 'exit'});
        expect(
          await process.exitCode.timeout(const Duration(seconds: 30)),
          0,
          reason: errors.toString(),
        );
        File('${out.path}/packet-backend-fixture.json').writeAsBytesSync(
          File('${temp.path}/server/backend-fixture.json').readAsBytesSync(),
        );
      } finally {
        client?.close();
        await process.stdin.close();
        // Only this owned disposable child can be terminated.
        if (await process.exitCode.timeout(
              const Duration(seconds: 2),
              onTimeout: () => -999,
            ) ==
            -999) {
          process.kill();
          await process.exitCode.timeout(
            const Duration(seconds: 10),
            onTimeout: () {
              process.kill(ProcessSignal.sigkill);
              return -999;
            },
          );
        }
        await lines.cancel();
        File('${out.path}/packet-server-stderr.log')
            .writeAsStringSync(errors.toString());
        temp.deleteSync(recursive: true);
      }
    },
  );
}

final samples = <Map<String, Object?>>[];
