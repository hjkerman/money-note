@Timeout(Duration(minutes: 3))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/io_client.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

void main() {
  test('P01 small fixture closes TLS client before original server exit fence', () async {
    final root = Directory.current.parent.path;
    final temp = Directory.systemTemp.createTempSync('mn-p01-cleanup-');
    final p = await Process.start('$root/.venv/bin/python', [
      '$root/docs/benchmarks/t66f-b03-ic01-p01/packet_server.py',
      '1000',
      '${temp.path}/server',
    ]);
    final errors = StringBuffer();
    p.stderr.transform(utf8.decoder).listen(errors.write);
    final lines = StreamIterator(
      p.stdout.transform(utf8.decoder).transform(const LineSplitter()),
    );
    final client = IOClient(
      HttpClient()
        ..badCertificateCallback = ((cert, host, port) => host == '127.0.0.1'),
    );
    Future<Map> command(Map r) async {
      p.stdin.writeln(jsonEncode(r));
      await p.stdin.flush();
      expect(await lines.moveNext().timeout(const Duration(seconds: 20)), true);
      return jsonDecode(lines.current) as Map;
    }

    try {
      expect(await lines.moveNext().timeout(const Duration(minutes: 2)), true);
      final initial = jsonDecode(lines.current) as Map;
      final t = AuthenticatedSegmentedTransport(
        client: client,
        origin: initial['origin'],
        credential: () => initial['token'],
        timeout: const Duration(seconds: 60),
      );
      await command({'command': 'p01_mode', 'enabled': true});
      final reply = await t.exchange(
        'POST',
        '/api/sync/v1/observations',
        encodeC1({
          'protocol': 1,
          'request_id': syncUuid(),
          'base': null,
          'inline_bytes': 0,
        }),
        SyncCancellation(),
        8 * 1048576,
      );
      expect(reply.status, 201);
      final manifest = ObservationManifest.fromBytes(reply.bytes);
      final release = await t.exchange(
        'DELETE',
        '/api/sync/v1/observations/${manifest.id}',
        null,
        SyncCancellation(),
        16384,
      );
      expect(release.status, 204);
      final snapshot = await command({'command': 'p01_snapshot'});
      expect(snapshot['complete'], true);
      expect(snapshot['pending'], 0);
      client.close();
      await command({'command': 'p01_mode', 'enabled': false});
      await command({'command': 'exit'});
      final exit = await p.exitCode.timeout(const Duration(seconds: 30));
      File(
        '$root/docs/benchmarks/t66f-b03-ic01-p01/evidence/cleanup-result.json',
      ).writeAsStringSync(
        jsonEncode({
          'exit': exit,
          'scope': snapshot,
          'stderr': errors.toString(),
          'fixture_n': 1000,
          'client_closed_before_exit': true,
        }),
      );
      expect(exit, 0, reason: errors.toString());
    } finally {
      client.close();
      await p.stdin.close();
      if (await p.exitCode.timeout(
            const Duration(seconds: 2),
            onTimeout: () => -999,
          ) ==
          -999) {
        p.kill();
        await p.exitCode;
      }
      await lines.cancel();
      temp.deleteSync(recursive: true);
    }
  });
}
