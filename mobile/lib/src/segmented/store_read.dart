part of 'store.dart';

// Data-proof association only. Never AppState/session/installation authority.
class _ReadProofBinding {
  const _ReadProofBinding(this.id, this.sequence, this.version);
  final String id;
  final int sequence, version;
}

extension SegmentedReadStore on SegmentedClientStore {
  // Full materialization is an explicit O(N) boundary (§22/23), not an ordinary
  // hot/read-page operation. Keep the audited complete verifier as its oracle.
  Future<CompleteGenerationProof> verifyAcceptedForMaterialization(
      AcceptedGeneration expected) async {
    final session = _reusableSession();
    if (expected.id == null ||
        session?.accepted.id != expected.id ||
        session?.accepted.sequence != expected.sequence) {
      rejectSegment('ACCEPTED_READ_STALE');
    }
    final version = publicationDataVersion;
    final proof = await verifyCompleteGeneration(expected.manifest!,
        (ref) => getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING')),
        maxObjects: limits.objectCount, work: work);
    if (publicationDataVersion != version ||
        _reusableSession()?.accepted.id != expected.id) {
      rejectSegment('ACCEPTED_READ_STALE');
    }
    _materializationProofs[proof] =
        _ReadProofBinding(expected.id!, expected.sequence, version);
    return proof;
  }

  // A synchronous, bounded logical read; never a long-lived async cursor. The
  // native read transaction pins the SQLite snapshot, including roots/bytes.
  // DELETE-journal writers on OTHER connections may prepare but cannot COMMIT
  // or GC these pages until this scope ends. Same-connection writes fail before
  // BEGIN/ROLLBACK. No durable reader rows/leases or crash-orphan pins are needed.
  T withAcceptedRead<T>(
      AcceptedGeneration expected, T Function(AcceptedReadView view) read,
      {CompleteGenerationProof? materializationProof}) {
    _requirePublication();
    _requireNoAcceptedReader();
    // A synchronously throwing Never-returning closure is also a subtype of
    // Future Function; it must retain its original exception, not be mislabeled.
    if (read is Future Function(AcceptedReadView) &&
        read is! Never Function(AcceptedReadView)) {
      rejectSegment('ASYNC_ACCEPTED_READ');
    }
    if (expected._namespace != cache.key || expected.id == null) {
      rejectSegment('ACCEPTED_READ_UNAVAILABLE');
    }
    AcceptedReadView? view;
    Object? primaryFailure;
    var begun = false;
    try {
      _db.execute('BEGIN DEFERRED');
      begun = true;
      // The pointer SELECT establishes the native snapshot before checking the
      // connection-owned provenance. Never read arbitrary staging as accepted.
      final prior = _acceptedSession;
      final actual = _acceptedFromStorage(knownPins: {
        if (prior?.accepted.id != null) prior!.accepted.id!,
        if (prior?.accepted.previousId != null) prior!.accepted.previousId!,
      });
      final session = _reusableSession();
      if (actual.id != expected.id ||
          actual.sequence != expected.sequence ||
          session?.accepted.id != actual.id ||
          session?.proof == null) {
        rejectSegment('ACCEPTED_READ_STALE');
      }
      final binding = materializationProof == null
          ? null
          : _materializationProofs[materializationProof];
      if (materializationProof != null &&
          (binding == null ||
              binding.id != actual.id ||
              binding.sequence != actual.sequence ||
              binding.version != publicationDataVersion)) {
        rejectSegment('MATERIALIZATION_PROOF_STALE');
      }
      _readingAccepted = true;
      work.add('read_snapshots');
      view = AcceptedReadView._(this, actual, binding != null);
      final result = read(view);
      if (result is Future) rejectSegment('ASYNC_ACCEPTED_READ');
      return result;
    } on SqliteException catch (error) {
      primaryFailure = error;
      _acceptedSession = null;
      throw SegmentedException(error.resultCode == 5 || error.resultCode == 6
          ? 'STORE_BUSY'
          : 'PERSISTENCE_FAILED');
    } catch (error) {
      primaryFailure = error;
      rethrow;
    } finally {
      view?._open = false;
      _readingAccepted = false;
      if (begun) {
        try {
          _db.execute('ROLLBACK');
        } catch (_) {
          _acceptedSession = null;
          // An uncertain release must not leave a reusable occupied connection.
          try {
            _db.close();
          } catch (_) {/* primary outcome wins */}
          _closed = true;
          if (primaryFailure == null) rejectSegment('READ_RELEASE_FAILED');
        }
      }
    }
  }
}

// Borrowed access, valid ONLY during withAcceptedRead's synchronous callback.
// Returned maps are detached immutable copies; no cursor survives this scope.
class AcceptedReadView {
  AcceptedReadView._(this._store, this.generation, this._fullMaterialization,
      [this._frozenId]);
  final SegmentedClientStore _store;
  final AcceptedGeneration generation;
  final bool _fullMaterialization;
  final String? _frozenId;
  bool _open = true;
  SyncTarget get target => generation.manifest!.target;
  bool get hasFullMaterializationProof => _fullMaterialization;
  CompleteStoreHandle get completeStoreHandle =>
      CompleteStoreHandle._(_store, generation, _frozenId);

  VerifiedObject _load(ObjectRef ref) {
    if (!_open) rejectSegment('ACCEPTED_READ_CLOSED');
    _store.work.add('adapter_object_reads');
    return _store.getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING'));
  }

  Map<String, dynamic> get hot => _load(target.roots['hot']!).body;
  Map<String, dynamic> get control => _load(target.roots['control']!).body;

  // Explicit primary-key order, NOT legacy exporter order. Keyset pruning
  // visits only the requested table/path/leaves; no flat-history scan for hot.
  List<Map<String, dynamic>> rows(String table,
      {TreeKey? after, int limit = 256}) {
    if (!segmentedTables.contains(table) || limit < 1 || limit > 256) {
      rejectSegment('READ_QUERY_INVALID');
    }
    if (after != null) TreeKey.parse([after.tag, after.value], table);
    final result = <Map<String, dynamic>>[];
    final root = _load(target.roots['raw']!).body;
    final descriptor = TreeDescriptor.parse(
        (root['tables'] as List).singleWhere((t) => t['name'] == table)['root'],
        table);
    void walk(TreeDescriptor d) {
      if (result.length == limit ||
          d.count == 0 ||
          (after != null && d.maximum!.compareTo(after) <= 0)) {
        return;
      }
      final object = _load(d.ref), body = object.body;
      if (body['table'] != table) rejectSegment('GRAPH_EDGE_INVALID');
      if (object.kind == 'snapshot-leaf') {
        for (final row in body['rows']) {
          final key = TreeKey.parse(row['key'], table);
          if (after == null || key.compareTo(after) > 0) {
            result.add(_freezeRead(row['value']) as Map<String, dynamic>);
            if (result.length == limit) return;
          }
        }
      } else if (object.kind == 'snapshot-node') {
        for (final child in body['children']) {
          walk(TreeDescriptor.parse(child, table));
          if (result.length == limit) return;
        }
      } else {
        rejectSegment('GRAPH_EDGE_INVALID');
      }
    }

    walk(descriptor);
    return List.unmodifiable(result);
  }

  // Only the explicit full-materialization boundary may enumerate all rows.
  Map<String, dynamic> materializationRows({int maxBytes = 26214400}) {
    if (!_fullMaterialization) rejectSegment('MATERIALIZATION_PROOF_REQUIRED');
    final data = <String, dynamic>{};
    var bytes = 0;
    for (final table in segmentedTables) {
      final all = <Map<String, dynamic>>[];
      TreeKey? after;
      while (true) {
        final page = rows(table, after: after);
        for (final row in page) {
          bytes += encodeC1(row).length;
          if (bytes > maxBytes) rejectSegment('LEGACY_MATERIALIZATION_BUDGET');
        }
        all.addAll(page);
        if (page.length < 256) break;
        after = TreeKey.parse([
          table == 'card_payment_deferrals' ||
                  table == 'notification_candidate_registrations' ||
                  table == 'app_settings' ||
                  table == 'app_labels'
              ? 't'
              : 'i',
          page.last[primaryColumn(table)].toString()
        ], table);
      }
      data[table] = all;
    }
    return data;
  }
}

// Data access only, never a publication/installation permit. A logical read
// borrows one synchronous SQLite snapshot; no cursor survives the callback.
class CompleteStoreHandle {
  CompleteStoreHandle._(this._store, this.generation, this._frozenId);
  final SegmentedClientStore _store;
  final AcceptedGeneration generation;
  final String? _frozenId;
  Future<T> read<T>(T Function(AcceptedReadView) action) async {
    if (_frozenId != null) {
      final frozen = await _store.recoverFrozenGeneration(_frozenId);
      if (frozen.generationId != generation.id) {
        rejectSegment('FROZEN_BINDING_INVALID');
      }
      return _store.withFrozenRead(frozen, action);
    }
    final installed = _store.adaptersEnabled
        ? await _store.recoverInstalledGeneration()
        : null;
    if (installed?.id == generation.id) {
      return _store.withInstalledRead(installed!, action);
    }
    final accepted = await _store.recoverAcceptedGeneration();
    if (accepted.id != generation.id) rejectSegment('ACCEPTED_READ_STALE');
    return _store.withAcceptedRead(accepted, action);
  }
}

Object? _freezeRead(Object? value) {
  if (value is Map<String, dynamic>) {
    return Map<String, dynamic>.unmodifiable(
        value.map((k, v) => MapEntry(k, _freezeRead(v))));
  }
  if (value is List) return List<Object?>.unmodifiable(value.map(_freezeRead));
  return value;
}
