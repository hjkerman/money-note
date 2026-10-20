// Test-only multi-item fixture. Real TLS integration uses the unchanged backend.
import 'dart:convert';
import 'dart:typed_data';

import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

import 'segmented_e2_fixture.dart';

class BatchFixtureTransport extends FixtureTransport {
  BatchFixtureTransport(super.fixture);
  @override
  Future<SyncReply> exchange(String method, String path, Uint8List? raw,
      SyncCancellation cancellation, int maxResponseBytes) async {
    if (!path.endsWith('/objects')) {
      return super.exchange(method, path, raw, cancellation, maxResponseBytes);
    }
    cancellation.check();
    checkSession();
    final body = decodeC1(raw!) as Map<String, dynamic>;
    bodies.add(body);
    final injected = await before?.call(method, path, body);
    if (injected != null) return injected;
    final items = body['items'] as List;
    if (items.isEmpty ||
        items.length > 64 ||
        items.fold<int>(0, (n, i) => n + (i['length'] as int)) > 1048576) {
      rejectSegment('TEST_BATCH_ENVELOPE');
    }
    objectRequests++;
    final observation = path.split('/')[5],
        nonce = body['request_id'] as String;
    if (retired.contains(observation)) {
      return remoteError('OBSERVATION_EXPIRED', 'new_observation', 410, nonce);
    }
    final chunks = <Map<String, dynamic>>[];
    for (final item in items) {
      final hashes = (item['path'] as List).cast<String>();
      requestedHashes.add(hashes.last);
      final bytes = fixture.objects[hashes.last];
      if (bytes == null) {
        return remoteError(
            'OBSERVATION_INCOMPLETE', 'new_observation', 410, nonce);
      }
      final offset = int.parse(item['offset'] as String),
          length = item['length'] as int;
      payloadBytes += length;
      chunks.add({
        'ref': {'hash': hashes.last, 'bytes': '${bytes.length}'},
        'offset': '$offset',
        'length': length,
        'data_base64': base64Encode(bytes.sublist(offset, offset + length))
      });
    }
    final reply = SyncReply(
        200,
        encodeC1({
          'protocol': 1,
          'request_id': nonce,
          'observation_id': observation,
          'chunks': chunks
        }));
    final result = after?.call(reply, method, path, body) ?? reply;
    if (result.bytes.length > maxResponseBytes) {
      rejectSegment('RESPONSE_SIZE_EXCEEDED');
    }
    return result;
  }
}
