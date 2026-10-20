// Isolated E2 acquisition. Never installs data, publishes authority or touches B/J.
import 'dart:async';
import 'dart:io';
import 'dart:math';
import 'dart:typed_data';

import 'c1.dart';
import 'graph.dart';
import 'object.dart';
import 'protocol.dart';
import 'store.dart';
import 'transport.dart';

String syncUuid() {
  final random = Random.secure();
  final bytes = List<int>.generate(16, (_) => random.nextInt(256));
  bytes[6] = (bytes[6] & 15) | 64;
  bytes[8] = (bytes[8] & 63) | 128;
  final h = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${h.substring(0, 8)}-${h.substring(8, 12)}-${h.substring(12, 16)}-${h.substring(16, 20)}-${h.substring(20)}';
}

class FetchLimits {
  const FetchLimits(
      {this.chunkBytes = 1048576,
      this.attempts = 3,
      this.observations = 3,
      this.graphObjects = 100000,
      this.graphEdges = 200000,
      this.pathDepth = 512,
      this.retryDelayMilliseconds = 5000})
      : _largeGraphVerification = false;
  // Explicit disposable HOST verification only. Never selected by a manifest,
  // capability, startup, or ordinary refresh. E1 must independently admit the
  // same envelope (500k stored objects / 384 MiB logical metadata); its other
  // byte/page/staging guards and every graph/integrity check remain unchanged.
  const FetchLimits.largeGraphVerification(
      {this.graphObjects = 500000, this.graphEdges = 1000000})
      : chunkBytes = 1048576,
        attempts = 3,
        observations = 3,
        pathDepth = 512,
        retryDelayMilliseconds = 5000,
        _largeGraphVerification = true;
  final bool _largeGraphVerification;
  final int chunkBytes,
      attempts,
      observations,
      graphObjects,
      graphEdges,
      pathDepth,
      retryDelayMilliseconds;
  void validate() {
    if (chunkBytes < 1 ||
        chunkBytes > 1048576 ||
        attempts < 1 ||
        attempts > 3 ||
        observations < 1 ||
        observations > 3 ||
        graphObjects < 1 ||
        graphObjects > (_largeGraphVerification ? 500000 : 100000) ||
        graphEdges < 1 ||
        graphEdges > (_largeGraphVerification ? 1000000 : 200000) ||
        pathDepth < 1 ||
        pathDepth > 512 ||
        retryDelayMilliseconds < 0 ||
        retryDelayMilliseconds > 5000) {
      rejectSegment('FETCH_LIMIT_INVALID');
    }
  }
}

class AcquisitionMetrics {
  int manifestRequests = 0,
      objectRequests = 0,
      releaseRequests = 0,
      payloadBytes = 0,
      responseBytes = 0,
      cacheHits = 0,
      cacheMisses = 0,
      downloadedObjects = 0,
      verificationMicroseconds = 0,
      elapsedMicroseconds = 0;
  Map<String, int> toJson() => {
        'manifest_requests': manifestRequests,
        'object_requests': objectRequests,
        'release_requests': releaseRequests,
        'payload_bytes': payloadBytes,
        'response_bytes': responseBytes,
        'cache_hits': cacheHits,
        'cache_misses': cacheMisses,
        'downloaded_objects': downloadedObjects,
        'verification_us': verificationMicroseconds,
        'elapsed_us': elapsedMicroseconds
      };
}

class VerifiedStagedGeneration {
  const VerifiedStagedGeneration(
      this.stagingId, this.manifest, this.graph, this.metrics);
  final String stagingId;
  final ObservationManifest manifest;
  final GraphClosure graph;
  final AcquisitionMetrics metrics;
  // NOT CompleteTargetVerified: E3 must recheck durable closure/F(raw), hot/raw,
  // accepted-base provenance and current owner/auth/mutation/mode at publication.
}

class AcquisitionFailure implements Exception {
  const AcquisitionFailure(this.code, this.action, this.stagingId);
  final String code, action;
  final String? stagingId;
  @override
  String toString() => 'AcquisitionFailure($code,$action)';
}

Future<void> _delay(Duration duration, SyncCancellation cancellation) async {
  final timer = Completer<void>();
  final scheduled = Timer(duration, () => timer.complete());
  final removeCancellation = cancellation.onCancel(() {
    if (!timer.isCompleted) timer.complete();
  });
  try {
    await timer.future;
    cancellation.check();
  } finally {
    scheduled.cancel();
    removeCancellation();
  }
}

class IncrementalFetcher {
  IncrementalFetcher(this.store, this.transport,
      {this.limits = const FetchLimits(),
      Future<void> Function(Duration, SyncCancellation)? delay})
      : _wait = delay ?? _delay,
        _storeKey = File(store.path).resolveSymbolicLinksSync() {
    limits.validate();
    if (!store.acquisitionEnabled) {
      rejectSegment('ACQUISITION_METADATA_REQUIRED');
    }
    if (transport.origin != store.cache.origin) rejectSegment('ORIGIN_INVALID');
  }
  final SegmentedClientStore store;
  final SegmentedTransport transport;
  final String _storeKey;
  final FetchLimits limits;
  final Future<void> Function(Duration, SyncCancellation) _wait;
  // One acquisition per application Dart isolate, with no queued sessions.
  // Other processes still use UUID stages + E1 SQL serialization, never a
  // shared active pointer. One HTTP fetch at a time.
  static final _activeStores = <String>{};

  Future<SyncReply> _request(
      String method,
      String path,
      Uint8List? body,
      String? requestId,
      SyncCancellation cancel,
      AcquisitionMetrics metrics,
      int responseLimit,
      {bool release = false}) async {
    for (var attempt = 0; attempt < limits.attempts; attempt++) {
      cancel.check();
      transport.checkSession();
      int? retryAfter;
      try {
        if (release) {
          metrics.releaseRequests++;
        } else if (path.endsWith('/objects')) {
          metrics.objectRequests++;
        } else {
          metrics.manifestRequests++;
        }
        final reply =
            await transport.exchange(method, path, body, cancel, responseLimit);
        cancel.check();
        transport.checkSession();
        metrics.responseBytes += reply.bytes.length;
        if (reply.status >= 200 && reply.status < 300) return reply;
        final remote = SyncRemoteException.parse(reply, requestId);
        if (remote.action != 'retry_same' || attempt + 1 == limits.attempts) {
          throw remote;
        }
        retryAfter = remote.retryAfter;
      } on SegmentedException catch (error) {
        if (![
              'TRANSPORT_TIMEOUT',
              'TRANSPORT_UNAVAILABLE',
              'RESPONSE_TRUNCATED'
            ].contains(error.code) ||
            attempt + 1 == limits.attempts) {
          rethrow;
        }
      }
      final ms = max([100, 250, 500][attempt], retryAfter ?? 0);
      if (ms > limits.retryDelayMilliseconds) {
        rejectSegment('RETRY_DELAY_BUDGET');
      }
      await _wait(Duration(milliseconds: ms), cancel);
    }
    rejectSegment('RETRY_EXHAUSTED');
  }

  Future<ObservationManifest> _observe(
      String nonce, SyncCancellation cancel, AcquisitionMetrics metrics) async {
    final reply = await _request(
        'POST',
        '/api/sync/v1/observations',
        encodeC1({
          'protocol': 1,
          'request_id': nonce,
          'base': null,
          'inline_bytes': 0
        }),
        nonce,
        cancel,
        metrics,
        store.limits.manifestBytes);
    if (reply.status != 200 && reply.status != 201) {
      rejectSegment('MANIFEST_STATUS_INVALID');
    }
    final manifest = ObservationManifest.fromBytes(reply.bytes,
        maxBytes: store.limits.manifestBytes);
    store.cache.verifyTarget(manifest.target);
    final v = decodeC1(manifest.bytes) as Map;
    if (manifest.requestId != nonce ||
        v['base_sync_root'] != null ||
        v['change_kind'] != 'initial' ||
        (v['inline_objects'] as List).isNotEmpty) {
      rejectSegment('MANIFEST_BINDING_INVALID');
    }
    return manifest;
  }

  Future<bool> release(String id, {AcquisitionMetrics? metrics}) async {
    uuidValue(id);
    // Cleanup is bounded and never changes the integrity/completeness result.
    final cancel = SyncCancellation();
    final timer = Timer(const Duration(seconds: 2), cancel.cancel);
    try {
      final reply = await _request('DELETE', '/api/sync/v1/observations/$id',
          null, null, cancel, metrics ?? AcquisitionMetrics(), 16384,
          release: true);
      return reply.status == 204 && reply.bytes.isEmpty;
    } on Object {
      return false;
    } finally {
      timer.cancel();
    }
  }

  Future<VerifiedStagedGeneration> acquire(
      {String? resumeId,
      SyncCancellation? cancellation,
      AcceptedGeneration? verifiedBase}) async {
    final cancel = cancellation ?? SyncCancellation();
    if (_activeStores.isNotEmpty || !_activeStores.add(_storeKey)) {
      throw const AcquisitionFailure('ACQUISITION_BUSY', 'retry_same', null);
    }
    final metrics = AcquisitionMetrics(), elapsed = Stopwatch()..start();
    String? stageId;
    ObservationManifest? current;
    // A02 cold continuation: begin. No persistent cursor or default-path change.
    if (limits._largeGraphVerification &&
        verifiedBase?.id == null &&
        resumeId == null &&
        store.publicationEnabled) {
      try {
        return await _acquireContinuousCold(cancel, metrics, elapsed);
      } finally {
        _activeStores.remove(_storeKey);
      }
    }
    // A02 cold continuation: end.
    try {
      cancel.check();
      transport.checkSession();
      StagingSession? resume;
      if (resumeId != null) {
        resume = store.loadStaging(resumeId);
        if (resume == null) rejectSegment('STAGING_MISSING');
      }
      var nonce = resume?.manifest.requestId ?? syncUuid();
      for (var observation = 0;
          observation < limits.observations;
          observation++) {
        try {
          current = await _observe(nonce, cancel, metrics);
          if (resume != null &&
              !sameBytes(resume.manifest.bytes, current.bytes)) {
            rejectSegment('IMMUTABLE_MANIFEST_CHANGED');
          }
          stageId = resume?.id ?? syncUuid();
          store.createStaging(stageId, current, DateTime.now().toUtc());
          store.recordAcquisition(stageId, 'acquiring');
          final observed = current;
          final frontier = limits._largeGraphVerification
              ? _VerificationFrontier(
                  store,
                  stageId,
                  observed,
                  cancel,
                  metrics,
                  limits,
                  transport.checkSession,
                  (nonce, body, responseLimit) => _request(
                      'POST',
                      '/api/sync/v1/observations/${observed.id}/objects',
                      body,
                      nonce,
                      cancel,
                      metrics,
                      responseLimit),
                  cold: verifiedBase?.id == null)
              : null;
          final graph = await verifyAcquisitionGraph(observed.target,
              (edge, path) async {
            if (frontier != null) return frontier.load(edge, path);
            cancel.check();
            transport.checkSession();
            final timing = Stopwatch()..start();
            var object = store.getVerifiedObject(edge.ref);
            metrics.verificationMicroseconds += timing.elapsedMicroseconds;
            if (object != null) {
              metrics.cacheHits++;
            } else {
              metrics.cacheMisses++;
              if (edge.ref.byteLength < 1 ||
                  edge.ref.byteLength > store.limits.objectBytes) {
                rejectSegment('LOCAL_OBJECT_BUDGET');
              }
              final bytes = Uint8List(edge.ref.byteLength);
              for (var offset = 0; offset < bytes.length;) {
                final length = min(limits.chunkBytes, bytes.length - offset),
                    requestId = syncUuid();
                final reply = await _request(
                    'POST',
                    '/api/sync/v1/observations/${observed.id}/objects',
                    encodeC1({
                      'protocol': 1,
                      'request_id': requestId,
                      'items': [
                        {'path': path, 'offset': '$offset', 'length': length}
                      ]
                    }),
                    requestId,
                    cancel,
                    metrics,
                    4 * ((length + 2) ~/ 3) + 16384);
                if (reply.status != 200) {
                  rejectSegment('TRANSFER_STATUS_INVALID');
                }
                final packet = record(
                    decodeC1(reply.bytes, requireCanonical: false),
                    ['protocol', 'request_id', 'observation_id', 'chunks']);
                if (packet['protocol'] != 1 ||
                    packet['protocol'] is! int ||
                    packet['request_id'] != requestId ||
                    packet['observation_id'] != observed.id ||
                    packet['chunks'] is! List ||
                    (packet['chunks'] as List).length != 1) {
                  rejectSegment('TRANSFER_BINDING_INVALID');
                }
                final chunk =
                    ObjectChunk.parse((packet['chunks'] as List).single);
                if (!chunk.ref.matches(edge.ref) ||
                    chunk.offset != '$offset' ||
                    chunk.bytes.length != length) {
                  rejectSegment('CHUNK_BINDING_INVALID');
                }
                bytes.setRange(offset, offset + length, chunk.bytes);
                metrics.payloadBytes += length;
                offset += length;
              }
              cancel.check();
              transport.checkSession();
              timing.reset();
              VerifiedObject.verify(bytes, edge.ref, store.cache,
                  kinds: edge.kinds, maxBytes: store.limits.objectBytes);
              object = store.putVerifiedObject(edge.ref, bytes);
              metrics.verificationMicroseconds += timing.elapsedMicroseconds;
              metrics.downloadedObjects++;
            }
            if (!edge.kinds.contains(object.kind)) {
              rejectSegment('GRAPH_EDGE_INVALID');
            }
            cancel.check();
            transport.checkSession();
            store.recordStagedObject(stageId!, edge.ref);
            return object;
          },
              maxObjects: min(limits.graphObjects, store.limits.objectCount),
              maxEdges: limits.graphEdges,
              maxPath: limits.pathDepth,
              // Only the owning recovered store can supply reusable integrity
              // evidence. Terminal server auth and E3 final authority remain.
              reuse: verifiedBase == null
                  ? null
                  : store.acquisitionProvenance(verifiedBase),
              work: store.work);
          frontier?.finish();
          // The same nonce/body returns the SAME persisted bytes, not regenerated
          // Judgment. Server terminal auth/TTL is authoritative, not phone time.
          final terminal = await _observe(nonce, cancel, metrics);
          if (!sameBytes(observed.bytes, terminal.bytes)) {
            rejectSegment('IMMUTABLE_MANIFEST_CHANGED');
          }
          cancel.check();
          transport.checkSession();
          store.recordAcquisition(stageId, 'graph_verified');
          await release(observed.id, metrics: metrics);
          current = null;
          cancel.check();
          transport.checkSession();
          metrics.elapsedMicroseconds = elapsed.elapsedMicroseconds;
          return VerifiedStagedGeneration(stageId, observed, graph, metrics);
        } on SyncRemoteException catch (error) {
          if (stageId != null) {
            store.recordAcquisition(stageId, 'interrupted',
                errorCode: error.code);
          }
          if (current != null) await release(current.id, metrics: metrics);
          current = null;
          if (error.action != 'new_observation' ||
              observation + 1 == limits.observations) {
            rethrow;
          }
          nonce = syncUuid();
          resume = null;
          stageId = null;
        }
      }
      rejectSegment('OBSERVATION_ATTEMPTS_EXHAUSTED');
    } on Object catch (error) {
      final code = error is SegmentedException
          ? error.code
          : error is SyncRemoteException
              ? error.code
              : 'ACQUISITION_FAILED';
      if (stageId != null) {
        try {
          store.recordAcquisition(stageId, 'interrupted', errorCode: code);
        } on Object {/* original error wins */}
      }
      if (current != null) await release(current.id, metrics: metrics);
      throw AcquisitionFailure(
          code,
          error is SyncRemoteException
              ? error.action
              : [
                  'TRANSPORT_TIMEOUT',
                  'TRANSPORT_UNAVAILABLE',
                  'RESPONSE_TRUNCATED',
                  'STORE_BUSY',
                  'ACQUISITION_CANCELLED'
                ].contains(code)
                  ? 'retry_same'
                  : 'blocked',
          stageId);
    } finally {
      _activeStores.remove(_storeKey);
    }
  }

  // A02 active-call helper: begin.
  Future<VerifiedStagedGeneration> _acquireContinuousCold(
      SyncCancellation cancel,
      AcquisitionMetrics metrics,
      Stopwatch elapsed) async {
    // The opened, schema-validated connection is the integrity lifetime. Own
    // E1 transactions do not change data_version; ANY external commit, close,
    // profile/validator change invalidates this suspended proof. No receipt is
    // persisted or reused on restart. E3 still verifies complete F(raw)/hot/raw
    // and its ORIGINAL AppState authority, independently of this graph proof.
    final dataVersion = store.publicationDataVersion;
    ObservationManifest? current;
    String? stage;
    var observations = 0;
    void guard() {
      cancel.check();
      transport.checkSession();
      if (store.publicationDataVersion != dataVersion) {
        rejectSegment('VERIFICATION_STALE');
      }
    }

    Future<void> observe([SyncRemoteException? error]) async {
      guard();
      if (stage != null && error != null) {
        store.recordAcquisition(stage!, 'interrupted', errorCode: error.code);
      }
      if (current != null) await release(current!.id, metrics: metrics);
      current = null;
      guard();
      while (true) {
        if (observations == limits.observations) {
          if (error != null) throw error;
          rejectSegment('OBSERVATION_ATTEMPTS_EXHAUSTED');
        }
        observations++;
        try {
          final fresh = await _observe(syncUuid(), cancel, metrics);
          guard();
          current = fresh;
          stage = syncUuid();
          store.createStaging(stage!, fresh, DateTime.now().toUtc());
          store.recordAcquisition(stage!, 'acquiring');
          guard();
          return;
        } on SyncRemoteException catch (failure) {
          if (failure.action != 'new_observation') rethrow;
          error = failure;
        }
      }
    }

    try {
      await observe();
      while (true) {
        final target = current!.target;
        final frontier = _VerificationFrontier(
            store,
            stage!,
            current!,
            cancel,
            metrics,
            limits,
            transport.checkSession,
            (nonce, body, responseLimit) => _request(
                'POST',
                '/api/sync/v1/observations/${current!.id}/objects',
                body,
                nonce,
                cancel,
                metrics,
                responseLimit),
            cold: true);
        Future<void> renew(SyncRemoteException error) async {
          if (error.action != 'new_observation') throw error;
          await observe(error);
          // Exact full Target, not just root, revision or content equivalence.
          if (!sameBytes(
              encodeC1(target.toJson()), encodeC1(current!.target.toJson()))) {
            throw const _ColdTargetChanged();
          }
          // Progress links are NOT copied into the fresh observation's stage.
          // Old stages/roots retain durable bytes; completed graph summaries
          // belong only to this still-active verifier, not to server authority.
          frontier.rebind(stage!, current!);
          store.work.add('cold_same_target_continuations');
        }

        try {
          final graph = await verifyAcquisitionGraph(target,
              (edge, path) async {
            while (true) {
              try {
                return await frontier.load(edge, path);
              } on SyncRemoteException catch (error) {
                await renew(error);
                // Retry the WHOLE load. A partially received oversized object
                // buffer unwinds before renewal; chunks never cross leases.
              }
            }
          },
              maxObjects: min(limits.graphObjects, store.limits.objectCount),
              maxEdges: limits.graphEdges,
              maxPath: limits.pathDepth,
              work: store.work);
          frontier.finish();
          while (true) {
            try {
              final terminal =
                  await _observe(current!.requestId, cancel, metrics);
              if (!sameBytes(current!.bytes, terminal.bytes)) {
                rejectSegment('IMMUTABLE_MANIFEST_CHANGED');
              }
              break;
            } on SyncRemoteException catch (error) {
              await renew(error);
            }
          }
          guard();
          store.recordAcquisition(stage!, 'graph_verified');
          final result = current!;
          await release(result.id, metrics: metrics);
          current = null;
          guard();
          metrics.elapsedMicroseconds = elapsed.elapsedMicroseconds;
          return VerifiedStagedGeneration(stage!, result, graph, metrics);
        } on _ColdTargetChanged {
          store.work.add('cold_changed_target_restarts');
          // Fresh manifest/stage already acquired within the SAME 3-attempt
          // budget. Discard the old DFS/seen/frontier and verify new roots.
        }
      }
    } on Object catch (error) {
      final code = error is SegmentedException
          ? error.code
          : error is SyncRemoteException
              ? error.code
              : 'ACQUISITION_FAILED';
      if (stage != null) {
        try {
          store.recordAcquisition(stage!, 'interrupted', errorCode: code);
        } on Object {/* original failure wins; never report partial success */}
      }
      if (current != null) await release(current!.id, metrics: metrics);
      throw AcquisitionFailure(
          code,
          error is SyncRemoteException
              ? error.action
              : [
                  'TRANSPORT_TIMEOUT',
                  'TRANSPORT_UNAVAILABLE',
                  'RESPONSE_TRUNCATED',
                  'STORE_BUSY',
                  'ACQUISITION_CANCELLED'
                ].contains(code)
                  ? 'retry_same'
                  : 'blocked',
          stage);
    }
  }
  // A02 active-call helper: end.
}

class _ColdTargetChanged implements Exception {
  const _ColdTargetChanged();
}

typedef _FrontierPath = ({TypedObjectReference edge, List<String> path});

// A cursor retains child REFERENCES, not parent payload/decoded financial data.
// Batched depth-first discovery needs at most one 64-parent wave per path level.
class _ColdCursor {
  _ColdCursor(this.path, this.children);
  final List<String> path;
  final List<TypedObjectReference> children;
  int next = 0;
}

bool _strictAncestor(List<String> parent, List<String> path) {
  if (parent.length >= path.length) return false;
  for (var i = 0; i < parent.length; i++) {
    if (parent[i] != path[i]) return false;
  }
  return true;
}

// A bounded list of already authenticated parent-derived paths, NOT a cache or
// another graph verifier. All bytes live in the existing E1 store. Dropped paths
// are rediscovered by the unchanged complete DFS, so lookahead is optional.
// Enabled ONLY by the explicit disposable verification profile.
class _VerificationFrontier {
  _VerificationFrontier(this.store, this.stage, this.manifest, this.cancel,
      this.metrics, this.limits, this.sessionGuard, this.exchange,
      {required this.cold});
  final SegmentedClientStore store;
  String stage;
  ObservationManifest manifest;
  final SyncCancellation cancel;
  final AcquisitionMetrics metrics;
  final FetchLimits limits;
  final bool cold;
  final void Function() sessionGuard;
  final Future<SyncReply> Function(String, Uint8List, int) exchange;
  final _pending = <String, _FrontierPath>{}; // at most 64 paths
  final _progress = <ObjectRef>[]; // at most 64 cached progress links
  int _progressBytes = 0;
  final _cursors = <_ColdCursor>[];
  // Actual DFS ancestors have a different lifetime from prefetched parents.
  // A cache-only walk must retain a path, never all previously visited nodes.
  final _parents = <_ColdCursor>[]; // at most pathDepth
  int _parentPeak = 0;
  int _coldSteps = 0, _coldBytes = 0;

  void rebind(String freshStage, ObservationManifest freshManifest) {
    check();
    stage = freshStage;
    manifest = freshManifest;
    _progress.clear();
    _progressBytes = 0;
  }

  Future<void> _cooperate([int bytes = 0]) async {
    check();
    _coldBytes += bytes;
    if (++_coldSteps >= 64 || _coldBytes >= limits.chunkBytes) {
      _coldSteps = _coldBytes = 0;
      await Future<void>.delayed(Duration.zero);
      // Auth/cancel may change during the yield. AppState still checks the
      // ORIGINAL request ticket after acquisition and at synchronous COMMIT.
      check();
    }
  }

  void check() {
    cancel.check();
    sessionGuard();
  }

  void _enqueue(VerifiedObject object, List<String> path) {
    if (cold) {
      if (object.children.isEmpty) return;
      if (_cursors.length >= limits.pathDepth * 64) {
        rejectSegment('GRAPH_DEPTH_BUDGET');
      }
      _cursors.add(_ColdCursor(path, object.children));
      store.work.add('cold_prefetch_cursors_enqueued');
      return;
    }
    for (final child in object.children) {
      if (_pending.length == 64) break;
      if (path.contains(child.ref.hash)) rejectSegment('GRAPH_CYCLE');
      if (path.length >= limits.pathDepth) rejectSegment('GRAPH_DEPTH_BUDGET');
      _pending.putIfAbsent(
          child.ref.hash, () => (edge: child, path: [...path, child.ref.hash]));
    }
  }

  Future<List<ObjectChunk>> _packet(
      List<_FrontierPath> paths, List<int> offsets, List<int> lengths) async {
    check();
    final nonce = syncUuid(), total = lengths.fold<int>(0, (n, l) => n + l);
    final reply = await exchange(
        nonce,
        encodeC1({
          'protocol': 1,
          'request_id': nonce,
          'items': [
            for (var i = 0; i < paths.length; i++)
              {
                'path': paths[i].path,
                'offset': '${offsets[i]}',
                'length': lengths[i]
              }
          ]
        }),
        4 * ((total + 2) ~/ 3) + paths.length * 256 + 1024);
    if (reply.status != 200) rejectSegment('TRANSFER_STATUS_INVALID');
    final packet = record(decodeC1(reply.bytes, requireCanonical: false),
        ['protocol', 'request_id', 'observation_id', 'chunks']);
    if (packet['protocol'] != 1 ||
        packet['protocol'] is! int ||
        packet['request_id'] != nonce ||
        packet['observation_id'] != manifest.id ||
        packet['chunks'] is! List ||
        (packet['chunks'] as List).length != paths.length) {
      rejectSegment('TRANSFER_BINDING_INVALID');
    }
    final chunks = <ObjectChunk>[];
    for (var i = 0; i < paths.length; i++) {
      final chunk = ObjectChunk.parse((packet['chunks'] as List)[i]);
      if (!chunk.ref.matches(paths[i].edge.ref) ||
          chunk.offset != '${offsets[i]}' ||
          chunk.bytes.length != lengths[i]) {
        rejectSegment('CHUNK_BINDING_INVALID');
      }
      chunks.add(chunk);
      metrics.payloadBytes += chunk.bytes.length;
    }
    check();
    return chunks;
  }

  Future<void> _fetch(List<_FrontierPath> paths) async {
    if (paths.isEmpty) return;
    final bytes = <Uint8List>[];
    if (paths.length == 1 &&
        paths.single.edge.ref.byteLength > limits.chunkBytes) {
      final p = paths.single, buffer = Uint8List(p.edge.ref.byteLength);
      for (var offset = 0; offset < buffer.length;) {
        final length = min(limits.chunkBytes, buffer.length - offset);
        final chunks = await _packet(paths, [offset], [length]);
        buffer.setRange(offset, offset + length, chunks.single.bytes);
        offset += length;
      }
      bytes.add(buffer);
    } else {
      final chunks = await _packet(paths, List.filled(paths.length, 0),
          paths.map((p) => p.edge.ref.byteLength).toList());
      bytes.addAll(chunks.map((c) => c.bytes));
    }
    final watch = Stopwatch()..start();
    final objects = [
      for (var i = 0; i < paths.length; i++)
        VerifiedObject.verify(bytes[i], paths[i].edge.ref, store.cache,
            kinds: paths[i].edge.kinds, maxBytes: store.limits.objectBytes)
    ];
    check();
    store.putVerifiedStagedBatch(stage, [
      for (var i = 0; i < paths.length; i++)
        (ref: paths[i].edge.ref, bytes: bytes[i])
    ]);
    check();
    metrics.downloadedObjects += objects.length;
    metrics.cacheMisses += objects.length;
    metrics.verificationMicroseconds += watch.elapsedMicroseconds;
    for (var n = 0; n < objects.length; n++) {
      final i = cold ? objects.length - n - 1 : n;
      _enqueue(objects[i], paths[i].path);
    }
  }

  bool _coldProgress(VerifiedObject object) {
    final ref = object.ref;
    if (store.isStagedObject(stage, ref) ||
        _progress.any((p) => p.hash == ref.hash)) {
      return false;
    }
    if (_progress.length == 64 ||
        _progressBytes + ref.byteLength > limits.chunkBytes) {
      _flushProgress();
    }
    _progress.add(ref);
    _progressBytes += ref.byteLength;
    return true;
  }

  Future<void> _coldWave(_FrontierPath required) async {
    final paths = <_FrontierPath>[required];
    var bytes = required.edge.ref.byteLength;
    if (bytes < 1 || bytes > store.limits.objectBytes) {
      rejectSegment('LOCAL_OBJECT_BUDGET');
    }
    while ((_cursors.isNotEmpty || _parents.isNotEmpty) &&
        paths.length < 64 &&
        bytes < limits.chunkBytes) {
      await _cooperate();
      final queue = _cursors.isNotEmpty ? _cursors : _parents;
      final cursor = queue.last;
      if (cursor.next == cursor.children.length) {
        queue.removeLast();
        continue;
      }
      final edge = cursor.children[cursor.next++];
      if (cursor.path.contains(edge.ref.hash)) rejectSegment('GRAPH_CYCLE');
      if (cursor.path.length >= limits.pathDepth) {
        rejectSegment('GRAPH_DEPTH_BUDGET');
      }
      if (paths.any((p) => p.edge.ref.hash == edge.ref.hash) ||
          store.isStagedObject(stage, edge.ref) ||
          _progress.any((p) => p.hash == edge.ref.hash)) {
        continue;
      }
      final size = edge.ref.byteLength;
      if (size < 1 || size > store.limits.objectBytes) {
        rejectSegment('LOCAL_OBJECT_BUDGET');
      }
      final path = [...cursor.path, edge.ref.hash];
      final cached = store.getVerifiedObject(edge.ref);
      if (cached != null) {
        if (!edge.kinds.contains(cached.kind)) {
          rejectSegment('GRAPH_EDGE_INVALID');
        }
        if (_coldProgress(cached)) _enqueue(cached, path);
        await _cooperate(size);
        continue;
      }
      if (bytes + size > limits.chunkBytes) {
        cursor
            .next--; // Keep the verified parent cursor; no lost sibling paths.
        break;
      }
      paths.add((edge: edge, path: path));
      bytes += size;
    }
    await _fetch(paths);
  }

  Future<VerifiedObject> _loadCold(
      TypedObjectReference edge, List<String> path) async {
    await _cooperate();
    while (_parents.isNotEmpty) {
      final parent = _parents.last.path;
      if (_strictAncestor(parent, path)) {
        break;
      }
      _parents.removeLast(); // The authoritative DFS has left this subtree.
    }
    var object = store.getVerifiedObject(edge.ref);
    if (object == null) {
      await _coldWave((edge: edge, path: path));
      object = store.getVerifiedObject(edge.ref) ??
          (rejectSegment('OBJECT_MISSING'));
    } else {
      metrics.cacheHits++;
    }
    if (!edge.kinds.contains(object.kind)) rejectSegment('GRAPH_EDGE_INVALID');
    _coldProgress(object);
    if (object.children.isNotEmpty) {
      if (_parents.length >= limits.pathDepth) {
        rejectSegment('GRAPH_DEPTH_BUDGET');
      }
      _parents.add(_ColdCursor(path, object.children));
      if (_parents.length > _parentPeak) {
        store.work
            .add('cold_cached_parent_peak_sum', _parents.length - _parentPeak);
        _parentPeak = _parents.length;
      }
    }
    await _cooperate(object.bytes.length);
    return object;
  }

  Future<void> _wave([_FrontierPath? required]) async {
    final paths = <_FrontierPath>[];
    var bytes = 0;
    if (required != null) {
      final size = required.edge.ref.byteLength;
      if (size < 1 || size > store.limits.objectBytes) {
        rejectSegment('LOCAL_OBJECT_BUDGET');
      }
      paths.add(required);
      bytes = size;
      _pending.remove(required.edge.ref.hash);
    }
    for (final key in _pending.keys.toList()) {
      if (paths.length == 64 || bytes >= limits.chunkBytes) break;
      final p = _pending.remove(key)!;
      // An existing object is not recursively expanded by lookahead. The
      // owning graph provenance/DFS alone decides whether it may be reused.
      if (store.getVerifiedObject(p.edge.ref) != null) continue;
      final size = p.edge.ref.byteLength;
      if (size < 1 || size > store.limits.objectBytes) {
        rejectSegment('LOCAL_OBJECT_BUDGET');
      }
      // Oversized children are fetched as singletons only when the DFS needs
      // them. A full pending queue never causes an unbounded allocation.
      if (size > limits.chunkBytes || bytes + size > limits.chunkBytes) {
        continue;
      }
      paths.add(p);
      bytes += size;
    }
    await _fetch(paths);
  }

  Future<VerifiedObject> load(
      TypedObjectReference edge, List<String> path) async {
    if (cold) return _loadCold(edge, path);
    check();
    var object = store.getVerifiedObject(edge.ref);
    if (object == null) {
      await _wave((edge: edge, path: path));
      object = store.getVerifiedObject(edge.ref) ??
          (rejectSegment('OBJECT_MISSING'));
    } else {
      metrics.cacheHits++;
    }
    if (!edge.kinds.contains(object.kind)) rejectSegment('GRAPH_EDGE_INVALID');
    if (!store.isStagedObject(stage, edge.ref)) {
      if (_progress.length == 64 ||
          _progressBytes + edge.ref.byteLength > limits.chunkBytes) {
        _flushProgress();
      }
      _progress.add(edge.ref);
      _progressBytes += edge.ref.byteLength;
      _enqueue(object, path);
    }
    // One bounded wave per logical callback. Complete graph membership/count/
    // F(raw)/hot/raw/authority are still checked by the original pipeline.
    await _wave();
    check();
    return object;
  }

  void _flushProgress() {
    if (_progress.isEmpty) return;
    check();
    store.putVerifiedStagedBatch(
        stage, [for (final ref in _progress) (ref: ref, bytes: null)]);
    _progress.clear();
    _progressBytes = 0;
    check();
  }

  void finish() {
    _flushProgress();
    _pending.clear();
    _cursors.clear();
    _parents.clear();
    check();
  }
}
