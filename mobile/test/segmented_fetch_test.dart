import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/local_snapshot_repository.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';
import 'package:money_note_mobile/src/segmented/c1.dart';
import 'package:money_note_mobile/src/segmented/fetch.dart';
import 'package:money_note_mobile/src/segmented/store.dart';
import 'package:money_note_mobile/src/segmented/transport.dart';
import 'package:sqlite3/sqlite3.dart';

import 'support/segmented_e2_fixture.dart';
import 'support/offline_mode_fixtures.dart';

Matcher failure([String? code]) => isA<AcquisitionFailure>()
    .having((e) => e.code, 'sanitized code', code ?? isNotEmpty);

void main() {
  late GenerationFixture fixture;
  late Directory root;
  late SegmentedClientStore store;
  late FixtureTransport transport;
  IncrementalFetcher fetch({FetchLimits limits = const FetchLimits()}) =>
      IncrementalFetcher(store, transport, limits: limits, delay: (_, c) async {
        c.check();
      });
  setUpAll(() async {
    final server = await BackendBridge.start();
    fixture = GenerationFixture(server.fixture);
    await server.dispose();
  });
  setUp(() {
    root = Directory.systemTemp.createTempSync('money-note-e2-');
    store = SegmentedClientStore.open(root, fixture.cache, acquisition: true);
    transport = FixtureTransport(fixture);
  });
  tearDown(() {
    store.close();
    root.deleteSync(recursive: true);
  });

  test('server complete graph: all objects, eleven tables, no internal proof',
      () async {
    final result = await fetch().acquire();
    expect(result.graph.objects.map((r) => r.hash).toSet(),
        fixture.objects.keys.toSet());
    expect(result.graph.tableRows.keys.toSet(), fixture.rows.keys.toSet());
    expect(result.graph.tableRows.length, 11);
    final direct = sqlite3.open(store.path);
    expect(direct.select('SELECT count(*) AS n FROM objects').single['n'],
        fixture.objects.length);
    expect(direct.select('SELECT state FROM acquisition').single['state'],
        'graph_verified');
    expect(
        direct.select(
            "SELECT name FROM sqlite_master WHERE name LIKE '%active%'"),
        isEmpty);
    for (final ref in result.graph.objects) {
      expect(
          direct.select('SELECT body FROM objects WHERE hash=?',
              [ref.hash]).single['body'],
          fixture.objects[ref.hash]);
    }
    direct.close();
    expect(result.manifest.target.syncRoot, fixture.target.syncRoot);
    expect(transport.manifestRequests, 2); // initial + terminal auth/TTL retry
    expect(transport.objectRequests, fixture.objects.length);
  });
  test(
      'identical generation: current metadata but ZERO object payload downloads',
      () async {
    await fetch().acquire();
    final prior = transport.objectRequests;
    final result = await fetch().acquire();
    expect(transport.objectRequests - prior, 0);
    expect(result.metrics.payloadBytes, 0);
    expect(result.metrics.cacheHits, fixture.objects.length);
    expect(result.metrics.manifestRequests, 2);
  });

  for (final field in [
    'protocol',
    'status',
    'observation_id',
    'request_id',
    'validated_at',
    'expires_at',
    'target',
    'inline_objects',
    'extra'
  ]) {
    test('reject invalid observation manifest field $field', () async {
      transport.after = (reply, method, path, body) {
        if (!path.endsWith('/observations') || method != 'POST') return reply;
        final m = jsonDecode(utf8.decode(reply.bytes)) as Map<String, dynamic>;
        if (field == 'protocol') {
          m[field] = 2;
        } else if (field == 'status') {
          m[field] = 'retired';
        } else if (field == 'observation_id') {
          m[field] = 'not-uuid';
        } else if (field == 'request_id') {
          m[field] = syncUuid();
        } else if (field == 'validated_at') {
          m[field] = '2026-13-01T00:00:00Z';
        } else if (field == 'expires_at') {
          m[field] = m['validated_at'];
        } else if (field == 'target') {
          (m[field] as Map)['sync_root'] = '0' * 64;
        } else if (field == 'inline_objects') {
          m[field] = [null];
        } else {
          m[field] = null;
        }
        return SyncReply(reply.status, encodeC1(m));
      };
      await expectLater(fetch().acquire(), throwsA(failure()));
      expect(transport.objectRequests, 0);
      expect(store.listStoredObjectIdentities(), isEmpty);
    });
  }
  for (final change in ['dataset', 'epoch', 'principal']) {
    test('manifest rejects authenticated expected $change mismatch', () async {
      transport.after = (reply, method, path, body) {
        if (!path.endsWith('/observations') || method != 'POST') return reply;
        final m = jsonDecode(utf8.decode(reply.bytes)) as Map<String, dynamic>,
            t = m['target'] as Map<String, dynamic>;
        if (change == 'principal') {
          t['principal_id'] = 2;
        } else {
          (t['ns'] as Map)[change == 'dataset' ? 'dataset_id' : 'epoch'] =
              syncUuid();
        }
        final preimage = Map<String, dynamic>.from(t)..remove('sync_root');
        t['sync_root'] = objectHash('view', encodeC1(preimage));
        return SyncReply(reply.status, encodeC1(m));
      };
      await expectLater(
          fetch().acquire(), throwsA(failure('CACHE_CONTEXT_MISMATCH')));
      expect(transport.objectRequests, 0);
    });
  }
  for (final e in [
    ('AUTH_REQUIRED', 'reauthenticate', 401),
    ('PRINCIPAL_OR_SESSION_CHANGED', 'reauthenticate', 403),
    ('INVALID_REQUEST', 'blocked', 422),
    ('EPOCH_CHANGED', 'full_resync', 409),
    ('STORAGE_FAILED', 'blocked', 500)
  ]) {
    test('protocol error ${e.$1} preserves empty store and recovery action',
        () async {
      transport.before = (method, path, body) async => method == 'POST'
          ? remoteError(e.$1, e.$2, e.$3, body!['request_id'])
          : null;
      try {
        await fetch().acquire();
        fail('must fail');
      } on AcquisitionFailure catch (error) {
        expect(error.code, e.$1);
        expect(error.action, e.$2);
      }
      expect(store.listStoredObjectIdentities(), isEmpty);
    });
  }
  for (final change in [
    'protocol',
    'nonce',
    'observation',
    'hash',
    'type',
    'version',
    'offset',
    'length',
    'truncated',
    'oversized',
    'canonical',
    'extra'
  ]) {
    test('reject malformed/mismatched immutable transfer $change', () async {
      transport.after = (reply, method, path, body) {
        if (!path.endsWith('/objects')) return reply;
        final packet =
                jsonDecode(utf8.decode(reply.bytes)) as Map<String, dynamic>,
            chunk = (packet['chunks'] as List).single as Map;
        if (change == 'protocol') {
          packet['protocol'] = 2;
        } else if (change == 'nonce') {
          packet['request_id'] = syncUuid();
        } else if (change == 'observation') {
          packet['observation_id'] = syncUuid();
        } else if (change == 'hash') {
          (chunk['ref'] as Map)['hash'] = 'f' * 64;
        } else if (change == 'offset') {
          chunk['offset'] = '1';
        } else if (change == 'length') {
          chunk['length'] = (chunk['length'] as int) - 1;
        } else if (change == 'truncated') {
          return SyncReply(200, reply.bytes.sublist(0, reply.bytes.length - 1));
        } else if (change == 'oversized') {
          return SyncReply(200, Uint8List(2 * 1048576));
        } else if (change == 'extra') {
          chunk['extra'] = null;
        } else {
          final bytes = base64Decode(chunk['data_base64'] as String);
          final parsed = jsonDecode(utf8.decode(bytes)) as Map<String, dynamic>;
          if (change == 'type') {
            parsed['kind'] = 'index-root';
          }
          if (change == 'version') {
            parsed['canon'] = 2;
          }
          var corrupt = encodeC1(parsed);
          if (change == 'canonical') {
            corrupt[0] = 32;
          }
          // Preserve length so failure isn't merely base64/length validation.
          final replacement = Uint8List(bytes.length)
            ..setRange(
                0,
                corrupt.length < bytes.length ? corrupt.length : bytes.length,
                corrupt);
          chunk['data_base64'] = base64Encode(replacement);
        }
        return SyncReply(200, encodeC1(packet));
      };
      await expectLater(fetch().acquire(), throwsA(failure()));
      expect(store.listStoredObjectIdentities(), isEmpty);
      final stage = store.listStagingIdentities().single;
      expect(store.acquisitionProgress(stage)!.state, 'interrupted');
    });
  }
  test(
      'partial response is never persisted as verified; retry/resume uses good cache',
      () async {
    final cancel = SyncCancellation();
    transport.before = (method, path, body) async {
      if (path.endsWith('/objects') && transport.objectRequests == 3) {
        cancel.cancel();
      }
      return null;
    };
    String? interrupted;
    try {
      await fetch().acquire(cancellation: cancel);
      fail('must cancel');
    } on AcquisitionFailure catch (error) {
      expect(error.code, 'ACQUISITION_CANCELLED');
      interrupted = error.stagingId;
    }
    final stored = store.listStoredObjectIdentities().length;
    expect(stored, 3);
    store.close();
    store = SegmentedClientStore.open(root, fixture.cache, acquisition: true);
    expect(store.acquisitionProgress(interrupted!)!.state, 'interrupted');
    transport.before = null;
    final result = await fetch().acquire(resumeId: interrupted);
    expect(result.metrics.cacheHits, stored);
    expect(result.graph.objects.length, fixture.objects.length);
  });
  test('same-observation resume validates exact immutable manifest bytes',
      () async {
    transport.releaseSupported = false;
    final cancel = SyncCancellation();
    transport.before = (method, path, body) async {
      if (path.endsWith('/objects')) cancel.cancel();
      return null;
    };
    String? id;
    try {
      await fetch().acquire(cancellation: cancel);
    } on AcquisitionFailure catch (e) {
      id = e.stagingId;
    }
    transport.before = null;
    final result = await fetch().acquire(resumeId: id);
    expect(result.stagingId, id);
  });
  test('terminal manifest mutation cannot become graph_verified', () async {
    transport.after = (reply, method, path, body) {
      if (method != 'POST' ||
          !path.endsWith('/observations') ||
          transport.manifestRequests < 2) {
        return reply;
      }
      final m = jsonDecode(utf8.decode(reply.bytes)) as Map<String, dynamic>;
      m['expires_at'] = m['validated_at'].toString().replaceFirst('00Z', '01Z');
      return SyncReply(200, encodeC1(m));
    };
    await expectLater(fetch().acquire(), throwsA(failure()));
    expect(
        store.acquisitionProgress(store.listStagingIdentities().single)!.state,
        'interrupted');
  });
  for (final phase in ['manifest', 'objects', 'terminal']) {
    test('expiry $phase reacquires a NEW observation; bytes can be reused',
        () async {
      var expired = false;
      transport.before = (method, path, body) async {
        final matches = phase == 'manifest'
            ? path.endsWith('/observations')
            : phase == 'objects'
                ? path.endsWith('/objects')
                : path.endsWith('/observations') &&
                    transport.manifestRequests == 1;
        if (method == 'POST' && matches && !expired) {
          expired = true;
          return remoteError('OBSERVATION_EXPIRED', 'new_observation', 410,
              body!['request_id']);
        }
        return null;
      };
      final result = await fetch().acquire();
      expect(expired, isTrue);
      expect(result.graph.objects.length, fixture.objects.length);
      if (phase == 'terminal') {
        expect(result.metrics.downloadedObjects, fixture.objects.length);
        expect(result.metrics.cacheHits, fixture.objects.length);
      }
    });
  }
  test(
      'missing required descendant never claims complete, reacquisition is bounded',
      () async {
    transport.before = (method, path, body) async => path.endsWith('/objects')
        ? remoteError('OBSERVATION_INCOMPLETE', 'new_observation', 410,
            body!['request_id'])
        : null;
    await expectLater(
        fetch().acquire(), throwsA(failure('OBSERVATION_INCOMPLETE')));
    expect(store.listStagingIdentities().length, 3);
    expect(transport.manifestRequests, 3);
    for (final id in store.listStagingIdentities()) {
      expect(store.acquisitionProgress(id)!.state, 'interrupted');
    }
  });
  for (final reason in ['timeout', 'reset', 'busy']) {
    test('bounded idempotent retry $reason succeeds, nonce/body are unchanged',
        () async {
      var tries = 0;
      final nonces = <String>[];
      transport.before = (method, path, body) async {
        if (method == 'POST' && path.endsWith('/observations') && tries++ < 2) {
          nonces.add(body!['request_id'] as String);
          if (reason == 'busy') {
            return remoteError(
                'ROOT_NOT_READY', 'retry_same', 503, body['request_id'],
                retry: 100);
          }
          rejectSegment(reason == 'timeout'
              ? 'TRANSPORT_TIMEOUT'
              : 'TRANSPORT_UNAVAILABLE');
        }
        return null;
      };
      final result = await fetch().acquire();
      expect(nonces.toSet(), {result.manifest.requestId});
      expect(result.metrics.manifestRequests, 4);
    });
  }
  test('retry exhaustion stops after exactly three calls', () async {
    var calls = 0;
    transport.before = (method, path, body) async {
      calls++;
      rejectSegment('TRANSPORT_TIMEOUT');
    };
    await expectLater(fetch().acquire(), throwsA(failure('TRANSPORT_TIMEOUT')));
    expect(calls, 3);
  });
  test('excessive retry-after cannot create unbounded waiting', () async {
    transport.before = (method, path, body) async => remoteError(
        'LEASE_LIMIT', 'retry_same', 429, body!['request_id'],
        retry: 5001);
    await expectLater(
        fetch().acquire(), throwsA(failure('RETRY_DELAY_BUDGET')));
  });
  test('concurrent coordinators on same store are explicitly rejected',
      () async {
    final entered = Completer<void>(), resume = Completer<void>();
    transport.before = (method, path, body) async {
      if (!entered.isCompleted) {
        entered.complete();
        await resume.future;
      }
      return null;
    };
    final first = fetch().acquire();
    await entered.future;
    await expectLater(fetch().acquire(), throwsA(failure('ACQUISITION_BUSY')));
    resume.complete();
    await first;
  });
  test('sequential fetch budget: max one in flight and no duplicate hashes',
      () async {
    var running = 0, maxRunning = 0;
    transport.before = (method, path, body) async {
      running++;
      if (running > maxRunning) maxRunning = running;
      await Future<void>.delayed(Duration.zero);
      running--;
      return null;
    };
    await fetch().acquire();
    expect(maxRunning, 1);
    expect(transport.requestedHashes.length,
        transport.requestedHashes.toSet().length);
  });
  test('different stores still share the isolate-wide acquisition bound',
      () async {
    final entered = Completer<void>(), resume = Completer<void>();
    transport.before = (method, path, body) async {
      if (!entered.isCompleted) {
        entered.complete();
        await resume.future;
      }
      return null;
    };
    final otherRoot =
        Directory.systemTemp.createTempSync('money-note-e2-other-');
    final other = SegmentedClientStore.open(otherRoot, fixture.cache,
            acquisition: true),
        peer = FixtureTransport(fixture);
    final first = fetch().acquire();
    await entered.future;
    try {
      await expectLater(IncrementalFetcher(other, peer).acquire(),
          throwsA(failure('ACQUISITION_BUSY')));
      expect(peer.manifestRequests, 0);
      expect(other.listStagingIdentities(), isEmpty);
    } finally {
      resume.complete();
      await first;
      other.close();
      otherRoot.deleteSync(recursive: true);
    }
  });
  test('storage-full policy preserves prior verified objects and staging',
      () async {
    store.close();
    store = SegmentedClientStore.open(root, fixture.cache,
        acquisition: true, limits: const ClientStoreLimits(objectCount: 1));
    await expectLater(
        fetch().acquire(), throwsA(failure('GRAPH_OBJECT_BUDGET')));
    final direct = sqlite3.open(store.path);
    expect(direct.select('SELECT count(*) AS n FROM objects').single['n'], 1);
    expect(
        direct.select('SELECT count(*) AS n FROM staging_objects').single['n'],
        1);
    direct.close();
    expect(store.inspectStoreHealth().healthy, isTrue);
  });
  test('cancel before acquisition performs no HTTP or staging write', () async {
    final cancel = SyncCancellation()..cancel();
    await expectLater(fetch().acquire(cancellation: cancel),
        throwsA(failure('ACQUISITION_CANCELLED')));
    expect(transport.bodies, isEmpty);
    expect(store.listStagingIdentities(), isEmpty);
  });
  test('session changes during acquisition: no verified staged result',
      () async {
    transport.before = (method, path, body) async {
      if (path.endsWith('/objects')) transport.authenticated = false;
      return null;
    };
    await expectLater(
        fetch().acquire(), throwsA(failure('AUTHENTICATION_CHANGED')));
    expect(store.listStoredObjectIdentities(), isEmpty);
  });
  for (final limit in ['objects', 'edges', 'depth']) {
    test('graph traversal $limit budget is enforced', () async {
      final limits = FetchLimits(
          graphObjects: limit == 'objects' ? 1 : 100000,
          graphEdges: limit == 'edges' ? 1 : 200000,
          pathDepth: limit == 'depth' ? 1 : 512);
      await expectLater(fetch(limits: limits).acquire(), throwsA(failure()));
      expect(
          store
              .acquisitionProgress(store.listStagingIdentities().single)!
              .state,
          'interrupted');
    });
  }
  test('chunked exact bytes and duplicated retries remain E1-verified',
      () async {
    final result =
        await fetch(limits: const FetchLimits(chunkBytes: 16384)).acquire();
    for (final ref in result.graph.objects) {
      expect(store.getVerifiedObject(ref)!.bytes, fixture.objects[ref.hash]);
    }
    expect(result.metrics.payloadBytes,
        fixture.objects.values.fold<int>(0, (n, b) => n + b.length));
  });
  test('corrupt cached bytes fail closed, never silent cache hit', () async {
    await fetch().acquire();
    final ref = fixture.target.roots['raw']!, direct = sqlite3.open(store.path);
    final trigger = direct
        .select("SELECT sql FROM sqlite_master WHERE name='immutable_body'")
        .single['sql'] as String;
    direct.execute('DROP TRIGGER immutable_body');
    direct.execute('UPDATE objects SET body=? WHERE hash=?',
        [Uint8List(ref.byteLength), ref.hash]);
    direct.execute(trigger);
    direct.close();
    await expectLater(fetch().acquire(), throwsA(failure()));
  });
  test('E1 A02 remains enforced on opt-in v2 writes', () async {
    final direct = sqlite3.open(store.path);
    direct.execute('DROP TRIGGER object_usage');
    direct.close();
    await expectLater(
        fetch().acquire(), throwsA(failure('STORE_SCHEMA_CORRUPT')));
    final inspect = sqlite3.open(store.path);
    expect(inspect.select('SELECT count(*) AS n FROM objects').single['n'], 0);
    inspect.close();
  });
  for (final scenario in [
    'wrong_table',
    'descriptor',
    'duplicate_edge',
    'patricia_prefix',
    'index_count',
    'hot_context',
    'object_version',
    'raw_schema'
  ]) {
    test('hash-valid candidate rejects $scenario independently of hash check',
        () async {
      final kind = scenario == 'hot_context'
          ? 'hot'
          : scenario == 'index_count'
              ? 'index-root'
              : ['duplicate_edge', 'patricia_prefix'].contains(scenario)
                  ? 'index-node'
                  : 'raw-root';
      transport.fixture = mutateGraph(fixture, kind, (b) {
        if (scenario == 'wrong_table') {
          b['tables'][0]['root']['ref'] = b['tables'][1]['root']['ref'];
        }
        if (scenario == 'descriptor') {
          b['tables'][0]['count'] = '2';
          b['tables'][0]['root']['count'] = '2';
        }
        if (scenario == 'duplicate_edge') {
          b['right'] = b['left'];
        }
        if (scenario == 'patricia_prefix') {
          b['prefix'] = '${b['prefix']}0';
        }
        if (scenario == 'index_count') {
          b['count'] = '${int.parse(b['count'] as String) + 1}';
        }
        if (scenario == 'hot_context') {
          (b['context'] as Map)['evaluation_date'] = '2026-10-06';
        }
        if (scenario == 'object_version') {
          b['canon'] = 2;
        }
        if (scenario == 'raw_schema') {
          b['raw_schema'] = '0' * 64;
        }
      });
      await expectLater(fetch().acquire(), throwsA(failure()));
      expect(
          store
              .acquisitionProgress(store.listStagingIdentities().single)!
              .state,
          'interrupted');
    });
  }
  test(
      'generation churn on fresh observation uses ONLY new roots and reuses stable descendants',
      () async {
    await fetch().acquire();
    transport.fixture = mutateGraph(fixture, 'snapshot-leaf', (b) {
      b['rows'][0]['value']['title'] = '합성 수정';
    });
    final changed = await fetch().acquire();
    expect(changed.manifest.target.syncRoot, transport.fixture.target.syncRoot);
    expect(changed.graph.objects.map((r) => r.hash).toSet(),
        transport.fixture.objects.keys.toSet());
    expect(changed.metrics.downloadedObjects, 2); // one leaf + raw root
    expect(changed.metrics.cacheHits, greaterThan(0));
    final previousRaw = changed.manifest.target.roots['raw']!;
    transport.fixture = mutateGraph(transport.fixture, 'hot', (b) {
      b['state']['judgment']['budget']['message'] = '합성 문구 변경';
    });
    final wording = await fetch().acquire();
    expect(wording.manifest.target.roots['raw']!.matches(previousRaw), isTrue);
    expect(wording.manifest.target.syncRoot,
        isNot(changed.manifest.target.syncRoot));
    expect(wording.metrics.downloadedObjects, 1); // same R, genuinely NEW hot
    // Structural F(raw) equality is intentionally not an E2 activation claim.
  });
  test(
      'mixed-generation object bytes are rejected even with valid new manifest',
      () async {
    final changed = mutateGraph(fixture, 'snapshot-leaf', (b) {
      b['rows'][0]['value']['title'] = '합성 변경';
    });
    transport.fixture = changed;
    final wrong = fixture.objects[fixture.target.roots['raw']!.hash]!;
    transport.fixture.objects[changed.target.roots['raw']!.hash] = wrong;
    await expectLater(fetch().acquire(), throwsA(failure()));
    expect(store.listStoredObjectIdentities(), isEmpty);
  });
  test('required root with unknown kind is rejected, not treated as a leaf',
      () async {
    transport.fixture = mutateGraph(fixture, 'raw-root', (b) {
      b['kind'] = 'control';
    });
    await expectLater(
        fetch().acquire(), throwsA(failure('OBJECT_KIND_INVALID')));
  });
  test('release failure never deletes valid cache or prevents graph handoff',
      () async {
    transport.releaseSupported = false;
    final result = await fetch().acquire();
    expect(
        store.acquisitionProgress(result.stagingId)!.state, 'graph_verified');
    expect(store.listStoredObjectIdentities().length, fixture.objects.length);
  });
  test(
      'oversized expected object is rejected BEFORE payload allocation/request',
      () async {
    transport.after = (reply, method, path, body) {
      if (!path.endsWith('/observations') || method != 'POST') return reply;
      final m = jsonDecode(utf8.decode(reply.bytes)) as Map<String, dynamic>,
          t = m['target'] as Map<String, dynamic>;
      (t['raw_ref'] as Map)['bytes'] = '67108865';
      final preimage = Map<String, dynamic>.from(t)..remove('sync_root');
      t['sync_root'] = objectHash('view', encodeC1(preimage));
      return SyncReply(reply.status, encodeC1(m));
    };
    await expectLater(
        fetch().acquire(), throwsA(failure('LOCAL_OBJECT_BUDGET')));
    expect(transport.objectRequests, 0);
  });
  test('large valid singleton uses multiple exact bounded chunks', () async {
    transport.fixture = mutateGraph(fixture, 'snapshot-leaf', (b) {
      b['rows'][0]['value']['title'] = '한' * 400000;
      b['oversized'] = true;
    });
    final result = await fetch().acquire();
    final large =
        result.graph.objects.singleWhere((r) => r.byteLength > 1048576);
    expect(store.getVerifiedObject(large)!.bytes,
        transport.fixture.objects[large.hash]);
    expect(result.metrics.objectRequests,
        greaterThan(result.graph.objects.length));
    for (final body in transport.bodies.where((b) => b.containsKey('items'))) {
      expect(body['items'].single['length'], lessThanOrEqualTo(1048576));
    }
  });
  test('real SQLITE_FULL during E2 cannot advertise incomplete object',
      () async {
    store.close();
    store = SegmentedClientStore.open(root, fixture.cache,
        acquisition: true, limits: const ClientStoreLimits(databasePages: 64));
    transport.fixture = mutateGraph(fixture, 'snapshot-leaf', (b) {
      b['rows'][0]['value']['title'] = 'a' * 1100000;
      b['oversized'] = true;
    });
    await expectLater(
        fetch().acquire(), throwsA(failure('PERSISTENCE_FAILED')));
    final direct = sqlite3.open(store.path);
    expect(direct.select('SELECT count(*) AS n FROM objects').single['n'], 1);
    expect(
        direct.select('SELECT count(*) AS n FROM staging_objects').single['n'],
        1);
    expect(direct.select('PRAGMA integrity_check').single.values.first, 'ok');
    direct.close();
    expect(store.inspectStoreHealth().healthy, isTrue);
  });
  test(
      'acquisition/resume/cleanup leave OfflineBaseline v4 and Snapshot v7 intact',
      () async {
    final offline = OfflineStore(directoryProvider: () async => root);
    await offline.replaceBaseline(baselineFixture());
    final snapshots =
        LocalSnapshotRepository(directoryProvider: () async => root);
    final snapshot =
        File('test/fixtures/valid_snapshot.json').readAsBytesSync();
    await snapshots.save(snapshot);
    final original = {
      for (final file in root
          .listSync(recursive: true)
          .whereType<File>()
          .where((f) => !f.path.contains('/segmented-store-v1/')))
        file.path: file.readAsBytesSync()
    };
    final result = await fetch().acquire();
    await fetch().acquire();
    store.removeUnreferencedStagingData(result.stagingId);
    for (final item in original.entries) {
      expect(File(item.key).readAsBytesSync(), item.value);
    }
    expect((await offline.loadBaseline())!.toJson()['schema_version'], 4);
    expect((await snapshots.list()).length, 1);
    expect(await snapshots.readText((await snapshots.list()).single.filename),
        utf8.decode(snapshot));
  });
  test(
      'empty table and empty Patricia graph closure (NOT financial activation)',
      () async {
    final objects = <String, Uint8List>{};
    Map<String, dynamic> add(Map<String, dynamic> body) {
      final raw = encodeC1(body),
          hash = objectHash(body['kind'] as String, raw);
      objects[hash] = raw;
      return {'hash': hash, 'bytes': '${raw.length}'};
    }

    final raw = decodeC1(fixture.objects[fixture.target.roots['raw']!.hash]!)
        as Map<String, dynamic>;
    for (final table in raw['tables']) {
      final leaf = decodeC1(fixture.objects[table['root']['ref']['hash']]!)
          as Map<String, dynamic>;
      leaf['count'] = '0';
      leaf['min'] = null;
      leaf['max'] = null;
      leaf['rows'] = <dynamic>[];
      leaf['oversized'] = false;
      table['root'] = {
        'ref': add(leaf),
        'height': 0,
        'count': '0',
        'min': null,
        'max': null
      };
      table['count'] = '0';
    }
    final target = fixture.target.toJson()..remove('sync_root');
    target['raw_ref'] = add(raw);
    final index =
        decodeC1(fixture.objects[fixture.target.roots['index']!.hash]!)
            as Map<String, dynamic>;
    final empty = Map<String, dynamic>.from(index)..remove('facts');
    empty['kind'] = 'index-empty';
    empty['count'] = '0';
    index['count'] = '0';
    index['facts'] = add(empty);
    target['index_ref'] = add(index);
    for (final role in ['hot', 'control']) {
      final ref = fixture.target.roots[role]!;
      objects[ref.hash] = fixture.objects[ref.hash]!;
    }
    target['sync_root'] = objectHash('view', encodeC1(target));
    transport.fixture = GenerationFixture({
      'manifest': {...fixture.manifest, 'target': target},
      'objects': [
        for (final e in objects.entries)
          {
            'ref': {'hash': e.key, 'bytes': '${e.value.length}'},
            'data_base64': base64Encode(e.value)
          }
      ],
      'rows': <String, dynamic>{},
      'source': <String, dynamic>{}
    });
    final result = await fetch().acquire();
    expect(result.graph.tableRows.values.toSet(), {'0'});
    expect(result.graph.objects.length, objects.length);
    expect(store.loadStaging(result.stagingId)!.validationState, 'staged');
  });
}
