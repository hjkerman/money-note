// Controlled investigation-logger fault; product transport delegates unchanged.
import 'dart:io';
import 'dart:typed_data';

import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

class Meter extends http.BaseClient {
  Meter(this.log);
  final IOSink log;
  final inner = MockClient((_) async => http.Response('{}', 200));
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    try {
      final response = await inner.send(request);
      log.writeln('header');
      return response;
    } catch (error) {
      log.writeln('error=$error');
      rethrow;
    }
  }
}

Future<void> main() async {
  final root = Directory.systemTemp.createTempSync('mn-a01-sink-transport-');
  final sink = File('${root.path}/trace').openWrite();
  sink.writeln('before');
  final flushing = sink.flush();
  final t = AuthenticatedSegmentedTransport(
    client: Meter(sink),
    origin: 'https://localhost:54321',
    credential: () => 'synthetic',
  );
  try {
    await t.exchange(
      'POST',
      '/api/sync/v1/observations',
      Uint8List(0),
      SyncCancellation(),
      16384,
    );
    stdout.writeln('MAPPING=UNEXPECTED_SUCCESS');
  } catch (error) {
    stdout.writeln('MAPPING=$error');
  }
  await flushing;
  await sink.close();
}
