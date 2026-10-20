@Timeout(Duration(minutes: 4))
library;

import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';

Matcher code(String value) =>
    isA<SegmentedException>().having((e) => e.code, 'code', value);
void main() {
  late GenerationFixture f;
  late int depth;
  setUpAll(() async {
    final b = await BackendBridge.start(history: 16);
    f = GenerationFixture(b.fixture);
    depth = (b.fixture['objects'] as List)
        .map((r) => (r['path'] as List).length)
        .reduce((a, b) => a > b ? a : b);
    await b.dispose();
  });
  for (final delta in [0, -1]) {
    test('independent manifest bytes boundary $delta', () {
      final root = Directory.systemTemp.createTempSync(
            'mn-b02-audit-manifest-',
          ),
          raw = encodeC1(f.manifest);
      final store = SegmentedClientStore.open(
        root,
        f.cache,
        acquisition: true,
        limits: ClientStoreLimits(manifestBytes: raw.length + delta),
      );
      try {
        final call = () => store.createStaging(
          syncUuid(),
          ObservationManifest.fromBytes(raw),
          DateTime.now().toUtc(),
        );
        if (delta == 0)
          call();
        else
          expect(call, throwsA(code('LOCAL_METADATA_BUDGET')));
        expect(store.listStagingIdentities().length, delta == 0 ? 1 : 0);
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
    test('independent aggregate payload boundary $delta', () {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-payload-'),
          a = f.target.roots['control']!,
          b = f.target.roots['index']!,
          maxBytes = a.byteLength + b.byteLength + delta;
      final store = SegmentedClientStore.open(
        root,
        f.cache,
        limits: ClientStoreLimits(
          objectBytes: a.byteLength,
          totalObjectBytes: maxBytes,
        ),
      );
      try {
        store.putVerifiedObject(a, f.objects[a.hash]!);
        final call = () => store.putVerifiedObject(b, f.objects[b.hash]!);
        if (delta == 0)
          call();
        else
          expect(call, throwsA(code('LOCAL_STORAGE_BUDGET')));
        expect(store.getVerifiedObject(a)!.bytes, f.objects[a.hash]);
        expect(store.getVerifiedObject(b) != null, delta == 0);
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
    test('independent graph path boundary $delta', () async {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-depth-'),
          store = SegmentedClientStore.open(root, f.cache, publication: true);
      try {
        final result = IncrementalFetcher(
          store,
          FixtureTransport(f),
          limits: FetchLimits(pathDepth: depth + delta),
        ).acquire();
        if (delta == 0)
          expect((await result).graph.objects.length, f.objects.length);
        else
          await expectLater(
            result,
            throwsA(
              isA<AcquisitionFailure>().having(
                (e) => e.code,
                'code',
                'GRAPH_DEPTH_BUDGET',
              ),
            ),
          );
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  for (final announced in [true, false]) {
    test(
      'independent actual HTTP transport response boundary announced=$announced',
      () async {
        final client = MockClient.streaming(
          (request, body) async => http.StreamedResponse(
            Stream.value(Uint8List.fromList([1, 2, 3, 4])),
            200,
            contentLength: announced ? 4 : null,
          ),
        );
        final transport = AuthenticatedSegmentedTransport(
          client: client,
          origin: syntheticOrigin,
          credential: () => 'synthetic-token',
        );
        try {
          expect(
            (await transport.exchange(
              'POST',
              '/api/sync/v1/observations',
              null,
              SyncCancellation(),
              4,
            )).bytes,
            [1, 2, 3, 4],
          );
          await expectLater(
            transport.exchange(
              'POST',
              '/api/sync/v1/observations',
              null,
              SyncCancellation(),
              3,
            ),
            throwsA(code('RESPONSE_SIZE_EXCEEDED')),
          );
        } finally {
          client.close();
        }
      },
    );
  }
  test('independent existing default limits remain finite and opt-in only', () {
    const limits = FetchLimits(),
        store = ClientStoreLimits(),
        large = FetchLimits.largeGraphVerification();
    expect(
      [limits.graphObjects, limits.graphEdges, store.metadataBytes],
      [100000, 200000, 33554432],
    );
    expect(
      [
        large.graphObjects,
        large.graphEdges,
        large.observations,
        large.attempts,
        large.pathDepth,
      ],
      [500000, 1000000, 3, 3, 512],
    );
    for (final invalid in [
      const FetchLimits(attempts: 4),
      const FetchLimits(observations: 4),
      const FetchLimits(chunkBytes: 1048577),
      const FetchLimits(pathDepth: 513),
      const FetchLimits(retryDelayMilliseconds: 5001),
      const FetchLimits.largeGraphVerification(graphEdges: 1000001),
    ])
      expect(invalid.validate, throwsA(code('FETCH_LIMIT_INVALID')));
  });
}
