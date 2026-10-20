@Timeout(Duration(minutes: 12))
library;

import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/protocol.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import '../../../mobile/test/support/segmented_e2_fixture.dart';
import '../../../mobile/test/support/segmented_large_transport.dart';
import '../t66f-b02-implementation/verification_profile.dart';
import '../t66f-b02-a01-correction/before_fetch.dart' as old;

Matcher failure(String code) =>
    isA<AcquisitionFailure>().having((e) => e.code, 'code', code);
Matcher local(String code) =>
    isA<SegmentedException>().having((e) => e.code, 'code', code);
List<String> childHashes(Map b) {
  switch (b['kind']) {
    case 'raw-root':
      return [for (final e in b['tables']) e['root']['ref']['hash'] as String];
    case 'snapshot-node':
      return [for (final e in b['children']) e['ref']['hash'] as String];
    case 'index-root':
      return [b['facts']['hash'] as String];
    case 'index-node':
      return [b['left']['hash'] as String, b['right']['hash'] as String];
    default:
      return [];
  }
}

void validatePacket(GenerationFixture f, Map<String, dynamic> b) {
  final items = b['items'] as List;
  expect(items.length, inInclusiveRange(1, 64));
  expect(
    items.fold<int>(0, (n, x) => n + (x['length'] as int)),
    lessThanOrEqualTo(1048576),
  );
  for (final i in items) {
    final path = (i['path'] as List).cast<String>();
    expect(path.length, lessThanOrEqualTo(512));
    expect(f.target.roots.values.any((r) => r.hash == path.first), true);
    for (var j = 1; j < path.length; j++) {
      final body = jsonDecode(utf8.decode(f.objects[path[j - 1]]!)) as Map;
      expect(childHashes(body), contains(path[j]));
    }
  }
}

void durableUnpublished(SegmentedClientStore store) {
  final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
  try {
    expect(
      db.select('SELECT current_id FROM accepted').single['current_id'],
      isNull,
    );
    expect(db.select('PRAGMA foreign_key_check'), isEmpty);
  } finally {
    db.close();
  }
}

void main() {
  late GenerationFixture f, zero;
  setUpAll(() async {
    for (final n in [0, 200]) {
      final bridge = await BackendBridge.start(history: n);
      final value = GenerationFixture(bridge.fixture);
      await bridge.dispose();
      if (n == 0)
        zero = value;
      else
        f = value;
    }
  });
  for (final boundary in [
    'objects_at',
    'objects_over',
    'edges_at',
    'edges_over',
    'default_hard_cap',
    'large_hard_cap',
  ]) {
    test('independent actual E2 graph bound $boundary', () async {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-bound-');
      final store = SegmentedClientStore.open(
            root,
            f.cache,
            publication: true,
            limits: largeVerificationStoreLimits,
          ),
          t = BatchFixtureTransport(f);
      final edgeCount = f.objects.values.fold<int>(
        0,
        (n, raw) => n + childHashes(jsonDecode(utf8.decode(raw)) as Map).length,
      );
      try {
        if (boundary == 'default_hard_cap') {
          expect(
            () => FetchLimits(graphObjects: 100001).validate(),
            throwsA(local('FETCH_LIMIT_INVALID')),
          );
          expect(t.manifestRequests, 0);
          return;
        }
        if (boundary == 'large_hard_cap') {
          expect(
            () =>
                FetchLimits.largeGraphVerification(graphObjects: 500001)
                    .validate(),
            throwsA(local('FETCH_LIMIT_INVALID')),
          );
          expect(t.manifestRequests, 0);
          return;
        }
        final limit = FetchLimits.largeGraphVerification(
          graphObjects: boundary == 'objects_over'
              ? f.objects.length - 1
              : f.objects.length,
          graphEdges: boundary == 'edges_over' ? edgeCount - 1 : edgeCount,
        );
        final operation = IncrementalFetcher(store, t, limits: limit).acquire();
        if (boundary.endsWith('over')) {
          await expectLater(
            operation,
            throwsA(
              failure(
                boundary.startsWith('objects')
                    ? 'GRAPH_OBJECT_BUDGET'
                    : 'GRAPH_EDGE_BUDGET',
              ),
            ),
          );
        } else {
          final result = await operation;
          expect(
            result.graph.objects.map((r) => r.hash).toSet(),
            f.objects.keys.toSet(),
          );
        }
        durableUnpublished(store);
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  for (final budget in [319, 320, 321]) {
    test('independent E1 metadata $budget and rollback', () {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-meta-'),
          ref = zero.target.roots['control']!;
      final store = SegmentedClientStore.open(
        root,
        zero.cache,
        limits: ClientStoreLimits(metadataBytes: budget, manifestBytes: 1),
      );
      try {
        if (budget < 320)
          expect(
            () => store.putVerifiedObject(ref, zero.objects[ref.hash]!),
            throwsA(local('LOCAL_METADATA_BUDGET')),
          );
        else
          store.putVerifiedObject(ref, zero.objects[ref.hash]!);
        final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
        try {
          expect(
            db
                .select('SELECT objects,metadata FROM usage')
                .single
                .values
                .toList(),
            budget < 320 ? [0, 0] : [1, 320],
          );
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
  for (final delta in [0, -1]) {
    test('independent E1 object byte boundary $delta', () {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-size-'),
          ref = zero.target.roots['control']!;
      final store = SegmentedClientStore.open(
        root,
        zero.cache,
        limits: ClientStoreLimits(objectBytes: ref.byteLength + delta),
      );
      try {
        if (delta == 0)
          expect(
            store.putVerifiedObject(ref, zero.objects[ref.hash]!).bytes,
            zero.objects[ref.hash],
          );
        else
          expect(
            () => store.putVerifiedObject(ref, zero.objects[ref.hash]!),
            throwsA(local('LOCAL_OBJECT_BUDGET')),
          );
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  for (final count in [64, 65]) {
    test('independent E1 staged batch entry boundary $count', () {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-batch-');
      final store = SegmentedClientStore.open(
        root,
        zero.cache,
        publication: true,
        limits: largeVerificationStoreLimits,
      );
      final stage = syncUuid(), ref = zero.target.roots['control']!;
      store.createStaging(
        stage,
        ObservationManifest.fromBytes(encodeC1(zero.manifest)),
        DateTime.now().toUtc(),
      );
      try {
        final call = () => store.putVerifiedStagedBatch(stage, [
          for (var i = 0; i < count; i++)
            (ref: ref, bytes: zero.objects[ref.hash]),
        ]);
        if (count == 65)
          expect(call, throwsA(local('LOCAL_BATCH_BUDGET')));
        else
          call();
        final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
        try {
          expect(
            db.select('SELECT count(*) n FROM objects').single['n'],
            count == 64 ? 1 : 0,
          );
        } finally {
          db.close();
        }
        durableUnpublished(store);
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  test('independent staging quota exact and beyond', () {
    final root = Directory.systemTemp.createTempSync('mn-b02-audit-stages-');
    final actual = SegmentedClientStore.open(
      root,
      zero.cache,
      acquisition: true,
      limits: const ClientStoreLimits(stagingCount: 2),
    );
    final manifest = ObservationManifest.fromBytes(encodeC1(zero.manifest));
    try {
      for (var i = 0; i < 2; i++)
        actual.createStaging(syncUuid(), manifest, DateTime.now().toUtc());
      expect(
        () =>
            actual.createStaging(syncUuid(), manifest, DateTime.now().toUtc()),
        throwsA(local('LOCAL_METADATA_BUDGET')),
      );
      expect(actual.listStagingIdentities().length, 2);
    } finally {
      actual.close();
      root.deleteSync(recursive: true);
    }
  });
  test('independent packet comparison same 926-object backend graph', () async {
    final result = <Map<String, Object?>>[];
    for (final before in [true, false]) {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-packets-'),
          store = SegmentedClientStore.open(
            root,
            f.cache,
            publication: true,
            limits: largeVerificationStoreLimits,
          ),
          t = BatchFixtureTransport(f);
      t.before = (m, p, b) async {
        if (p.endsWith('/objects')) validatePacket(f, b!);
        return null;
      };
      try {
        if (before)
          await old.IncrementalFetcher(
            store,
            t,
            limits: const old.FetchLimits.largeGraphVerification(),
          ).acquire();
        else
          await IncrementalFetcher(
            store,
            t,
            limits: largeVerificationFetchLimits,
          ).acquire();
        final db = sqlite3.open(store.path, mode: OpenMode.readOnly);
        try {
          final hashes = <String>{};
          for (final row in db.select('SELECT hash,kind,body FROM objects')) {
            final bytes = row['body'] as Uint8List;
            expect(
              sha256.convert([
                ...utf8.encode('money-note.sync.v1/${row['kind']}'),
                0,
                ...bytes,
              ]).toString(),
              row['hash'],
            );
            hashes.add(row['hash'] as String);
          }
          expect(hashes, f.objects.keys.toSet());
        } finally {
          db.close();
        }
        result.add({
          'before': before,
          'packets': t.objectRequests,
          'unique_objects': t.requestedHashes.toSet().length,
          'payload_bytes': t.payloadBytes,
        });
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    }
    expect(result[0]['packets'], 322);
    expect(result[1]['packets'], 27);
    expect(result[0]['payload_bytes'], result[1]['payload_bytes']);
    File('../docs/benchmarks/t66f-b02-independent/packet-comparison.json')
        .writeAsStringSync(jsonEncode(result));
  });
  for (final mode in [
    'same',
    'changed_raw',
    'expiry_exhausted',
    'cancel',
    'logout',
    'external_commit',
    'bad_manifest',
    'bad_ref',
    'bad_data',
  ]) {
    test('independent renewal/fault $mode with durable state oracle', () async {
      final root = Directory.systemTemp.createTempSync('mn-b02-audit-renew-'),
          store = SegmentedClientStore.open(
            root,
            f.cache,
            publication: true,
            limits: largeVerificationStoreLimits,
          ),
          t = BatchFixtureTransport(f),
          cancel = SyncCancellation();
      var injected = false, packets = 0;
      var current = f;
      t.before = (method, path, body) async {
        if (!path.endsWith('/objects')) return null;
        validatePacket(current, body!);
        packets++;
        if (packets < 8 || injected && mode != 'expiry_exhausted') return null;
        injected = true;
        if (mode == 'same' || mode == 'expiry_exhausted')
          return remoteError(
            'OBSERVATION_EXPIRED',
            'new_observation',
            410,
            body['request_id'],
          );
        if (mode == 'changed_raw') {
          current = mutateGraph(f, 'snapshot-leaf', (b) {
            b['rows'][0]['value']['title'] = '독립 갱신 😀';
          });
          t.fixture = current;
          return remoteError(
            'OBSERVATION_EXPIRED',
            'new_observation',
            410,
            body['request_id'],
          );
        }
        if (mode == 'cancel') cancel.cancel();
        if (mode == 'logout') t.authenticated = false;
        if (mode == 'external_commit') {
          final db = sqlite3.open(store.path);
          try {
            db.execute(
              'PRAGMA user_version=PRAGMA_DUMMY'.replaceAll(
                'PRAGMA_DUMMY',
                '4',
              ),
            );
          } finally {
            db.close();
          }
        }
        return null;
      };
      t.after = (reply, method, path, body) {
        if (mode == 'bad_manifest' && path.endsWith('/observations')) {
          final b = jsonDecode(utf8.decode(reply.bytes)) as Map;
          b['large_profile'] = true;
          return SyncReply(reply.status, encodeC1(b));
        }
        if ((mode == 'bad_ref' || mode == 'bad_data') &&
            path.endsWith('/objects')) {
          final b = jsonDecode(utf8.decode(reply.bytes)) as Map;
          final chunk = b['chunks'][0] as Map;
          if (mode == 'bad_ref')
            chunk['ref']['hash'] = '0' * 64;
          else {
            final raw = base64Decode(chunk['data_base64']);
            final text = utf8
                .decode(raw)
                .replaceFirst('"canon":1', '"canon":2');
            chunk['data_base64'] = base64Encode(utf8.encode(text));
          }
          return SyncReply(reply.status, encodeC1(b));
        }
        return reply;
      };
      try {
        final operation = IncrementalFetcher(
          store,
          t,
          limits: largeVerificationFetchLimits,
        ).acquire(cancellation: cancel);
        if (mode == 'same' || mode == 'changed_raw') {
          final r = await operation;
          expect(
            r.graph.objects.map((x) => x.hash).toSet(),
            current.objects.keys.toSet(),
          );
          expect(
            t.manifestRequests,
            3,
          ); // initial + renewed + same-nonce terminal
          expect(
            store.work.snapshot()[mode == 'same'
                ? 'cold_same_target_continuations'
                : 'cold_changed_target_restarts'],
            1,
          );
        } else {
          final code = {
            'expiry_exhausted': 'OBSERVATION_EXPIRED',
            'cancel': 'ACQUISITION_CANCELLED',
            'logout': 'AUTHENTICATION_CHANGED',
            'external_commit': 'VERIFICATION_STALE',
            'bad_manifest': 'SHAPE_INVALID',
            'bad_ref': 'CHUNK_BINDING_INVALID',
            'bad_data': 'OBJECT_HASH_INVALID',
          }[mode]!;
          await expectLater(operation, throwsA(failure(code)));
          if (mode == 'expiry_exhausted') expect(t.manifestRequests, 3);
        }
        durableUnpublished(store);
      } finally {
        store.close();
        root.deleteSync(recursive: true);
      }
    });
  }
  test('independent request retries remain three and bounded', () async {
    final root = Directory.systemTemp.createTempSync('mn-b02-audit-attempt-'),
        store = SegmentedClientStore.open(root, zero.cache, publication: true),
        t = BatchFixtureTransport(zero);
    var requests = 0;
    final delays = <int>[];
    t.before = (m, p, b) async {
      if (p.endsWith('/observations')) {
        requests++;
        return remoteError(
          'ROOT_NOT_READY',
          'retry_same',
          503,
          b!['request_id'],
        );
      }
      return null;
    };
    try {
      await expectLater(
        IncrementalFetcher(
          store,
          t,
          limits: largeVerificationFetchLimits,
          delay: (d, c) async {
            delays.add(d.inMilliseconds);
            c.check();
          },
        ).acquire(),
        throwsA(failure('ROOT_NOT_READY')),
      );
      expect(requests, 3);
      expect(delays, [100, 250]);
      durableUnpublished(store);
    } finally {
      store.close();
      root.deleteSync(recursive: true);
    }
  });
}
