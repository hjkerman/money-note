@Timeout(Duration(minutes: 8))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/api_transport.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:sqlite3/sqlite3.dart';

import '../t66f-phase-b/harness.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test('I10 real TLS quota rejection and same-client E2 recovery', () async {
    final backend = await RealBackend.start(3);
    final h = await RealHarness.create(backend);
    final responseBodies = <Map<String, dynamic>>[];
    final leases = <String>[];
    try {
      final endpoint = Uri.parse('${backend.origin}/api/sync/v1/observations');
      for (var n = 0; n < 4; n++) {
        final response = await h.io.post(
          endpoint,
          headers: {
            'Authorization': 'Bearer ${backend.token}',
            'Content-Type': 'application/json',
          },
          body: jsonEncode({
            'protocol': 1,
            'request_id': syncUuid(),
            'base': null,
            'inline_bytes': 0,
          }),
        );
        expect(response.statusCode, 201);
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        expect(body['target']['principal_id'], 1);
        leases.add(body['observation_id'] as String);
        responseBodies.add({'status': response.statusCode, 'body': body});
      }
      final quotaProbe = await h.io.post(
        endpoint,
        headers: {
          'Authorization': 'Bearer ${backend.token}',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'protocol': 1,
          'request_id': syncUuid(),
          'base': null,
          'inline_bytes': 0,
        }),
      );
      expect(quotaProbe.statusCode, 429);
      final quotaBody = jsonDecode(quotaProbe.body) as Map<String, dynamic>;
      expect(quotaBody['error'], {
        'code': 'LEASE_LIMIT',
        'action': 'retry_same',
        'retry_after_ms': 100,
        'current_ns': null,
      });
      responseBodies.add({'status': quotaProbe.statusCode, 'body': quotaBody});
      final transport = segmentedTransportForApi(h.api);
      final fetcher = IncrementalFetcher(h.store, transport);
      await backend.stats(reset: true);
      Object? rejection;
      try {
        await fetcher.acquire();
      } catch (error) {
        rejection = error;
      }
      expect(
        rejection,
        isA<AcquisitionFailure>().having((e) => e.code, 'code', 'LEASE_LIMIT'),
      );
      final quotaWire = await backend.stats();
      expect(quotaWire.length, 3);
      expect(quotaWire.every((r) => r['status'] == 429), true);
      final before = h.disk();
      final raw = sqlite3.open(h.store.path);
      try {
        expect(raw.select('SELECT count(*) AS n FROM objects').single['n'], 0);
        expect(
          raw.select('SELECT current_id FROM accepted').single['current_id'],
          null,
        );
      } finally {
        raw.close();
      }
      for (final lease in leases) {
        final released = await h.io.delete(
          Uri.parse('$endpoint/$lease'),
          headers: {'Authorization': 'Bearer ${backend.token}'},
        );
        expect(released.statusCode, 204);
      }
      await backend.stats(reset: true);
      final staged = await fetcher.acquire();
      final oracle = await backend.command({'command': 'oracle'});
      final expectedObjects = (oracle['objects'] as List)
          .cast<Map<String, dynamic>>();
      final independent = sqlite3.open(h.store.path);
      try {
        expect(
          independent.select('SELECT count(*) AS n FROM objects').single['n'],
          expectedObjects.length,
        );
        for (final object in expectedObjects) {
          expect(
            independent.select('SELECT body FROM objects WHERE hash=?', [
              object['ref']['hash'],
            ]).single['body'],
            base64Decode(object['data_base64']),
          );
        }
        expect(independent.select('PRAGMA foreign_key_check'), isEmpty);
        expect(
          independent
              .select('SELECT current_id FROM accepted')
              .single['current_id'],
          null,
        );
      } finally {
        independent.close();
      }
      final validWire = await backend.stats();
      expect(
        validWire.any(
          (r) =>
              (r['path'] as String).endsWith('/objects') && r['status'] == 200,
        ),
        true,
      );
      File(const String.fromEnvironment('B01_HTTP_OUTPUT')).writeAsStringSync(
        jsonEncode({
          'id': 'I10',
          'created': responseBodies,
          'quota_wire': quotaWire,
          'quota_error': rejection.toString(),
          'state_after_rejection': before,
          'state_after_verified_acquisition': h.disk(),
          'verified_objects': expectedObjects.length,
          'staging_id': staged.stagingId,
          'valid_wire': validWire,
          'same_client': true,
        }),
      );
    } finally {
      h.dispose();
      await backend.dispose();
    }
  });
}
