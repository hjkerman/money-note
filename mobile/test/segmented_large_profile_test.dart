@Timeout(Duration(minutes: 5))
library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/graph.dart';
import 'package:money_note_mobile/src/segmented/object.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../docs/benchmarks/t66f-b02-implementation/verification_profile.dart';
import 'support/segmented_e2_fixture.dart';
import 'support/segmented_large_transport.dart';

Matcher segment(String code) =>
    isA<SegmentedException>().having((e) => e.code, 'code', code);

void main() {
  late GenerationFixture fixture;
  setUpAll(() async {
    final bridge = await BackendBridge.start();
    fixture = GenerationFixture(bridge.fixture);
    await bridge.dispose();
  });

  test('B02 default envelope is byte-for-byte policy unchanged', () {
    const f = FetchLimits(), s = ClientStoreLimits();
    expect([
      f.graphObjects,
      f.graphEdges,
      f.pathDepth,
      f.chunkBytes,
      f.attempts,
      f.observations,
      f.retryDelayMilliseconds
    ], [
      100000,
      200000,
      512,
      1048576,
      3,
      3,
      5000
    ]);
    expect([
      s.objectCount,
      s.metadataBytes,
      s.objectBytes,
      s.totalObjectBytes,
      s.manifestBytes,
      s.stagingCount,
      s.databasePages,
      s.busyMilliseconds
    ], [
      100000,
      33554432,
      67108864,
      536870912,
      8388608,
      128,
      262144,
      1000
    ]);
    f.validate();
    s.validate();
  });
  for (final count in [99999, 100000, 100001]) {
    test('B02 default supported object ceiling $count', () {
      void action() => FetchLimits(graphObjects: count).validate();
      if (count > 100000) {
        expect(action, throwsA(segment('FETCH_LIMIT_INVALID')));
      } else {
        action();
      }
    });
  }
  for (final count in [499999, 500000, 500001]) {
    test('B02 explicit large supported object ceiling $count', () {
      void action() =>
          FetchLimits.largeGraphVerification(graphObjects: count).validate();
      if (count > 500000) {
        expect(action, throwsA(segment('FETCH_LIMIT_INVALID')));
      } else {
        action();
      }
    });
  }
  for (final edges in [999999, 1000000, 1000001]) {
    test('B02 explicit large supported edge ceiling $edges', () {
      void action() =>
          FetchLimits.largeGraphVerification(graphEdges: edges).validate();
      if (edges > 1000000) {
        expect(action, throwsA(segment('FETCH_LIMIT_INVALID')));
      } else {
        action();
      }
    });
  }
  test('B02 coordinated finite envelope covers measured graph and stage charge',
      () {
    largeVerificationFetchLimits.validate();
    largeVerificationStoreLimits.validate();
    for (final v in [200331, 400532]) {
      expect(v, lessThan(largeVerificationFetchLimits.graphObjects));
      expect(v - 4, lessThan(largeVerificationFetchLimits.graphEdges));
      // Logical core charges: object192 + ref128 + edge256 + stage128.
      // Two further full stage-link sets are conservative restart headroom.
      expect(v * 704 + 2 * v * 128 + 1024 * 1024,
          lessThan(largeVerificationStoreLimits.metadataBytes));
    }
    expect(largeVerificationStoreLimits.objectCount, 500000);
    expect(largeVerificationStoreLimits.metadataBytes, 402653184);
    expect(const FetchLimits().graphObjects, 100000);
  });

  Future<GraphClosure> graph(int objects, int edges,
          {int depth = 512, GraphProvenance? reuse}) =>
      verifyAcquisitionGraph(
          fixture.target,
          (edge, path) async => VerifiedObject.verify(
              fixture.objects[edge.ref.hash]!, edge.ref, fixture.cache,
              kinds: edge.kinds),
          maxObjects: objects,
          maxEdges: edges,
          maxPath: depth,
          reuse: reuse);

  for (final extra in [-1, 0, 1]) {
    test('B02 real closure object boundary offset $extra, cold and reused',
        () async {
      final full = await graph(500000, 1000000);
      final n = full.objects.length;
      if (extra < 0) {
        await expectLater(
            graph(n + extra, 1000000), throwsA(segment('GRAPH_OBJECT_BUDGET')));
        await expectLater(graph(n + extra, 1000000, reuse: full.provenance),
            throwsA(segment('GRAPH_OBJECT_BUDGET')));
      } else {
        expect((await graph(n + extra, 1000000)).objects.length, n);
        expect(
            (await graph(n + extra, 1000000, reuse: full.provenance))
                .objects
                .length,
            n);
      }
    });
    test('B02 real closure edge boundary offset $extra', () async {
      final full = await graph(500000, 1000000), edgeCount = full.edges;
      if (extra < 0) {
        await expectLater(graph(500000, edgeCount + extra),
            throwsA(segment('GRAPH_EDGE_BUDGET')));
      } else {
        expect((await graph(500000, edgeCount + extra)).edges, edgeCount);
      }
    });
  }
  test('B02 large profile does not relax graph path validation', () async {
    await expectLater(graph(500000, 1000000, depth: 1),
        throwsA(segment('GRAPH_DEPTH_BUDGET')));
  });
  test('B02 typed edge still rejects a correctly hashed wrong kind', () {
    final ref = fixture.target.roots['raw']!;
    expect(
        () => VerifiedObject.verify(
            fixture.objects[ref.hash]!, ref, fixture.cache,
            kinds: {'index-root'}),
        throwsA(segment('OBJECT_KIND_INVALID')));
  });
  test('B02 individual object limit is independent of large graph limit', () {
    final ref = fixture.target.roots['raw']!;
    expect(
        () => VerifiedObject.verify(
            fixture.objects[ref.hash]!, ref, fixture.cache,
            maxBytes: ref.byteLength - 1),
        throwsA(segment('LOCAL_OBJECT_BUDGET')));
  });

  for (final budget in [319, 320, 321]) {
    test(
        'B02 actual E1 metadata transaction at/beyond injected boundary $budget',
        () {
      final root = Directory.systemTemp.createTempSync('mn-b02-metadata-');
      final ref = fixture.target.roots['control']!;
      final store = SegmentedClientStore.open(root, fixture.cache,
          limits: ClientStoreLimits(
              objectCount: 500000, metadataBytes: budget, manifestBytes: 1));
      try {
        if (budget < 320) {
          expect(() => store.putVerifiedObject(ref, fixture.objects[ref.hash]!),
              throwsA(segment('LOCAL_METADATA_BUDGET')));
        } else {
          store.putVerifiedObject(ref, fixture.objects[ref.hash]!);
        }
        final db = sqlite3.open(store.path);
        try {
          expect(db.select('SELECT metadata FROM usage').single['metadata'],
              budget < 320 ? 0 : 320);
          expect(db.select('SELECT count(*) AS n FROM objects').single['n'],
              budget < 320 ? 0 : 1);
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
          db.execute('BEGIN IMMEDIATE');
          db.execute('ROLLBACK');
        } finally {
          db.close();
        }
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }

  for (final scenario in [
    'valid',
    'cancel',
    'hash',
    'missing',
    'type',
    'principal',
    'dataset',
    'epoch',
    'version',
    'storage'
  ]) {
    test(
        'B02 selected large profile preserves $scenario admission and recovery',
        () async {
      final root = Directory.systemTemp.createTempSync('mn-b02-acquire-');
      var store = SegmentedClientStore.open(root, fixture.cache,
          acquisition: true, limits: largeVerificationStoreLimits);
      final t = BatchFixtureTransport(fixture), cancel = SyncCancellation();
      var once = false;
      t.before = (method, path, body) async {
        if (scenario == 'cancel' && path.endsWith('/objects')) cancel.cancel();
        if (scenario == 'missing' && path.endsWith('/objects')) {
          return remoteError('OBSERVATION_INCOMPLETE', 'new_observation', 410,
              body!['request_id']);
        }
        return null;
      };
      t.after = (reply, method, path, body) {
        if (once || method != 'POST') return reply;
        if (['principal', 'dataset', 'epoch', 'version'].contains(scenario) &&
            path.endsWith('/observations')) {
          once = true;
          final m = decodeC1(reply.bytes, requireCanonical: false) as Map;
          final target = m['target'] as Map;
          if (scenario == 'version') {
            m['protocol'] = 9;
          } else if (scenario == 'principal') {
            target['principal_id'] = 2;
          } else {
            (target['ns']
                    as Map)[scenario == 'dataset' ? 'dataset_id' : 'epoch'] =
                syncUuid();
          }
          if (scenario != 'version') {
            final p = Map<String, dynamic>.from(target)..remove('sync_root');
            target['sync_root'] = objectHash('view', encodeC1(p));
          }
          return SyncReply(reply.status, encodeC1(m));
        }
        if (['hash', 'type'].contains(scenario) && path.endsWith('/objects')) {
          once = true;
          final p = decodeC1(reply.bytes, requireCanonical: false) as Map;
          final chunk = (p['chunks'] as List).single as Map;
          if (scenario == 'hash') {
            final parsed =
                decodeC1(base64Decode(chunk['data_base64'] as String)) as Map;
            parsed['canon'] = 2;
            chunk['data_base64'] = base64Encode(encodeC1(parsed));
          } else {
            (chunk['ref'] as Map)['hash'] = '0' * 64;
          }
          return SyncReply(reply.status, encodeC1(p));
        }
        return reply;
      };
      if (scenario == 'storage') {
        store.close();
        store = SegmentedClientStore.open(root, fixture.cache,
            acquisition: true,
            limits: const ClientStoreLimits(
                objectCount: 500000,
                metadataBytes: 384 * 1024 * 1024,
                objectBytes: 1));
      }
      try {
        final action =
            IncrementalFetcher(store, t, limits: largeVerificationFetchLimits)
                .acquire(cancellation: cancel);
        if (scenario == 'valid') {
          final result = await action;
          expect(result.graph.objects.length, fixture.objects.length);
          expect(result.metrics.downloadedObjects, fixture.objects.length);
          expect(result.manifest.target.syncRoot, fixture.target.syncRoot);
          expect(t.requestedHashes.length, fixture.objects.length);
          expect(t.requestedHashes.toSet(), fixture.objects.keys.toSet());
          expect(t.objectRequests, lessThan(fixture.objects.length));
        } else {
          await expectLater(
              action,
              throwsA(scenario == 'hash'
                  ? isA<AcquisitionFailure>()
                      .having((e) => e.code, 'code', 'OBJECT_HASH_INVALID')
                  : isA<AcquisitionFailure>()));
        }
        final path = store.path;
        store.close();
        store = SegmentedClientStore.open(root, fixture.cache,
            acquisition: true, limits: largeVerificationStoreLimits);
        expect(store.inspectStoreHealth().healthy, isTrue);
        final db = sqlite3.open(path);
        try {
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
          expect(
              db.select("SELECT name FROM sqlite_master WHERE name='accepted'"),
              isEmpty);
          if (scenario != 'valid') {
            expect(
                db.select(
                    "SELECT * FROM acquisition WHERE state='graph_verified'"),
                isEmpty);
          }
        } finally {
          db.close();
        }
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  for (final fault in ['order', 'missing', 'hash', 'cancel']) {
    test('B02 multi-item packet $fault cannot partially persist', () async {
      final root = Directory.systemTemp.createTempSync('mn-b02-packet-');
      final store = SegmentedClientStore.open(root, fixture.cache,
          acquisition: true, limits: largeVerificationStoreLimits);
      final transport = BatchFixtureTransport(fixture),
          cancel = SyncCancellation();
      var injected = false;
      transport.after = (reply, method, path, request) {
        if (injected || !path.endsWith('/objects')) return reply;
        final body = decodeC1(reply.bytes, requireCanonical: false) as Map;
        final chunks = body['chunks'] as List;
        if (chunks.length < 2) return reply;
        injected = true;
        if (fault == 'order') body['chunks'] = chunks.reversed.toList();
        if (fault == 'missing') body['chunks'] = chunks.sublist(1);
        if (fault == 'cancel') cancel.cancel();
        if (fault == 'hash') {
          final chunk = chunks.last as Map;
          final object = decodeC1(base64Decode(chunk['data_base64'])) as Map;
          object['canon'] = 2;
          chunk['data_base64'] = base64Encode(encodeC1(object));
        }
        return SyncReply(reply.status, encodeC1(body));
      };
      try {
        await expectLater(
            IncrementalFetcher(store, transport,
                    limits: largeVerificationFetchLimits)
                .acquire(cancellation: cancel),
            throwsA(isA<AcquisitionFailure>()));
        expect(injected, isTrue);
        final db = sqlite3.open(store.path);
        try {
          expect(db.select('SELECT count(*) AS n FROM objects').single['n'], 1);
          expect(
              db
                  .select('SELECT count(*) AS n FROM staging_objects')
                  .single['n'],
              1);
          expect(
              db.select(
                  "SELECT * FROM acquisition WHERE state='graph_verified'"),
              isEmpty);
          expect(db.select('PRAGMA foreign_key_check'), isEmpty);
        } finally {
          db.close();
        }
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  for (final interrupted in [false, true]) {
    test('B02 oversized object chunking cancel=$interrupted', () async {
      final large = mutateGraph(fixture, 'hot', (body) {
        ((body['state'] as Map)['judgment']['budget'] as Map)['message'] =
            '원문 😀${'x' * 1048576}';
      });
      final root = Directory.systemTemp.createTempSync('mn-b02-chunks-');
      final store = SegmentedClientStore.open(root, large.cache,
          acquisition: true, limits: largeVerificationStoreLimits);
      final transport = BatchFixtureTransport(large),
          cancel = SyncCancellation();
      final hot = large.target.roots['hot']!;
      transport.before = (method, path, body) async {
        if (interrupted && path.endsWith('/objects')) {
          final item = (body!['items'] as List).first;
          if ((item['path'] as List).last == hot.hash &&
              item['offset'] != '0') {
            cancel.cancel();
          }
        }
        return null;
      };
      try {
        final future = IncrementalFetcher(store, transport,
                limits: largeVerificationFetchLimits)
            .acquire(cancellation: cancel);
        if (interrupted) {
          await expectLater(future, throwsA(isA<AcquisitionFailure>()));
          expect(store.getVerifiedObject(hot), isNull);
        } else {
          final complete = await future;
          expect(complete.graph.objects.length, large.objects.length);
          expect(store.getVerifiedObject(hot)!.bytes, large.objects[hot.hash]);
          final calls = transport.bodies.where((b) =>
              b['items'] is List &&
              ((b['items'] as List).first['path'] as List).last == hot.hash);
          expect(calls.length, (hot.byteLength + 1048575) ~/ 1048576);
        }
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
}
