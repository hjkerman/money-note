part of 'store.dart';

class AcceptedGeneration {
  AcceptedGeneration._(
      this.id, this.sequence, this.manifest, this.previousId, this._namespace);
  final String? id, previousId;
  final int sequence;
  final ObservationManifest? manifest;
  final String _namespace;
}

// Durable data verification evidence only. It never grants AppState authority.
class PreparedGeneration {
  PreparedGeneration._(this.id, this.expected, this._manifest, this._receipt,
      this._dataVersion, this._owner, this._proof);
  final String id;
  final AcceptedGeneration expected;
  final Uint8List _manifest, _receipt;
  final int _dataVersion;
  final SegmentedClientStore _owner;
  final CompleteGenerationProof _proof;
}

// Connection-local DATA provenance. No ticket, credential or authority result.
// External commits/reopen/errors invalidate it; schema is checked every use.
class _AcceptedSession {
  _AcceptedSession(this.accepted, this.proof, this.dataVersion);
  final AcceptedGeneration accepted;
  final CompleteGenerationProof? proof;
  final int dataVersion;
}

// Verification/connection association only, NEVER publication authorization.
class _CandidateBinding {
  _CandidateBinding(this.base, this.sequence, this.dataVersion);
  final String? base;
  final int sequence, dataVersion;
}

class SegmentedPublication {
  const SegmentedPublication(this.generationId, this.sequence, this.target,
      this.idempotent, this.transactionMicroseconds, this.readbackMicroseconds);
  final String generationId;
  final int sequence;
  final SyncTarget target;
  final bool idempotent;
  final int transactionMicroseconds, readbackMicroseconds;
}

// COMMIT is durable, but return/readback did not complete. Never call this a
// rollback or delete its accepted pins. Recovery resolves the persisted pointer.
class PublicationCommittedException implements Exception {
  const PublicationCommittedException(
      this.generationId, this.sequence, this.cause);
  final String generationId;
  final int sequence;
  final Object
      cause; // Retain the primary failure, never log financial content.
  @override
  String toString() => 'PublicationCommittedException($sequence)';
}

extension SegmentedPublicationStore on SegmentedClientStore {
  _AcceptedSession? _reusableSession() {
    _requirePublication();
    try {
      _requireSchema(_db, acquisition: true, publication: true);
      final session = _acceptedSession;
      if (session != null &&
          session.dataVersion == publicationDataVersion &&
          (session.proof?.hasMatchingDataIdentity ?? true)) {
        // Small durable pointer/receipt checks still run. Reusing graph proof
        // must NOT substitute a cached pointer for the actual storage CAS.
        final actual = _acceptedFromStorage(knownPins: {
          if (session.accepted.id != null) session.accepted.id!,
          if (session.accepted.previousId != null) session.accepted.previousId!
        });
        if (actual.id == session.accepted.id &&
            actual.sequence == session.accepted.sequence &&
            actual.previousId == session.accepted.previousId &&
            session.dataVersion == publicationDataVersion) {
          return session;
        }
      }
      _acceptedSession = null;
      return null;
    } catch (_) {
      _acceptedSession = null;
      rethrow;
    }
  }

  GraphProvenance? acquisitionProvenance(AcceptedGeneration expected) {
    final session = _reusableSession();
    if (session == null ||
        session.accepted.id != expected.id ||
        session.accepted.sequence != expected.sequence ||
        expected._namespace != cache.key) {
      return null;
    }
    return session.proof?.graph.provenance;
  }

  Future<CompleteGenerationProof> verifyPublicationCandidate(
      ObservationManifest manifest, AcceptedGeneration expected,
      {required int verifiedDataVersion}) async {
    cache.verifyTarget(manifest.target);
    if (expected._namespace != cache.key) rejectSegment('BASE_CONTEXT_INVALID');
    final session = _reusableSession();
    if (publicationDataVersion != verifiedDataVersion) {
      rejectSegment('VERIFICATION_STALE');
    }
    final base = session?.proof;
    CompleteGenerationProof proof;
    if (session?.accepted.id == expected.id &&
        session?.accepted.sequence == expected.sequence &&
        base != null) {
      work.add('provenance_reuses');
      proof = await verifyIncrementalGeneration(manifest, base,
          (r) => getVerifiedObject(r) ?? (rejectSegment('OBJECT_MISSING')),
          maxObjects: limits.objectCount, work: work);
    } else {
      final full = await verifyCompleteGeneration(manifest,
          (r) => getVerifiedObject(r) ?? (rejectSegment('OBJECT_MISSING')),
          base: expected.manifest, maxObjects: limits.objectCount, work: work);
      proof = full.withRootAssociation();
    }
    if (publicationDataVersion != verifiedDataVersion) {
      rejectSegment('VERIFICATION_STALE');
    }
    _candidateBindings[proof] =
        _CandidateBinding(expected.id, expected.sequence, verifiedDataVersion);
    return proof;
  }

  // Connection-local SQLite counter for commits by OTHER connections. This
  // fences validation freshness, never authorizes an AppState publication.
  int get publicationDataVersion {
    _requirePublication();
    return _db.select('PRAGMA data_version').single.values.first as int;
  }

  void _requirePublication() {
    if (_closed) rejectSegment('STORE_CLOSED');
    if (!publicationEnabled) rejectSegment('PUBLICATION_PROFILE_REQUIRED');
    final profile = _db.select('SELECT * FROM profile');
    if (profile.length != 1 ||
        profile.single['id'] != 1 ||
        profile.single['discriminator'] != SegmentedClientStore.discriminator ||
        profile.single['namespace'] != cache.key ||
        profile.single['validator'] != VerifiedObject.validatorBuild) {
      _acceptedSession = null;
      rejectSegment('STORE_PROFILE_INVALID');
    }
  }

  ObservationManifest _generation(String id,
      {Uint8List? expectedManifest,
      Uint8List? expectedReceipt,
      bool knownPins = false}) {
    final rows = _db.select('SELECT * FROM generations WHERE id=?', [id]);
    if (rows.length != 1) rejectSegment('ACCEPTED_METADATA_INVALID');
    final r = rows.single;
    final bytes = r['manifest'] as Uint8List,
        receipt = r['receipt'] as Uint8List;
    if (bytes.length > limits.manifestBytes ||
        receipt.length > limits.manifestBytes ||
        localChecksum(bytes) != r['manifest_checksum'] ||
        localChecksum(receipt) != r['receipt_checksum'] ||
        (expectedManifest != null && !sameBytes(bytes, expectedManifest)) ||
        (expectedReceipt != null && !sameBytes(receipt, expectedReceipt))) {
      rejectSegment('GENERATION_RECEIPT_INVALID');
    }
    final manifest =
        ObservationManifest.fromBytes(bytes, maxBytes: limits.manifestBytes);
    cache.verifyTarget(manifest.target);
    final evidence = record(decodeC1(receipt), [
      'validator',
      'target',
      'base_sync_root',
      'objects',
      'object_set',
      'edges',
      'facts',
      'changed_rows',
      'reused_subtrees',
      'authority_history'
    ]);
    hashValue(evidence['object_set']);
    if (evidence['base_sync_root'] != null) {
      hashValue(evidence['base_sync_root']);
    }
    u64(evidence['facts']);
    for (final field in ['edges', 'changed_rows', 'reused_subtrees']) {
      if (evidence[field] is! int || (evidence[field] as int) < 0) {
        rejectSegment('GENERATION_RECEIPT_INVALID');
      }
    }
    final history = record(evidence['authority_history'],
        ['owner', 'lineage', 'authentication', 'request']);
    if (history['owner'] != cache.principalId ||
        history.values.any((v) => v is! int || v < 0)) {
      rejectSegment('GENERATION_RECEIPT_INVALID');
    }
    final incremental = evidence['validator'] == 'segmented-e3/2';
    if ((!incremental &&
            evidence['validator'] != CompleteGenerationProof.validator) ||
        !sameBytes(
            encodeC1(evidence['target']), encodeC1(manifest.target.toJson())) ||
        evidence['objects'] != r['object_count'] ||
        r['object_count'] is! int ||
        (r['object_count'] as int) < 4 ||
        (!knownPins &&
            _db.select(
                    incremental
                        ? 'SELECT count(*) AS n FROM generation_roots WHERE generation_id=?'
                        : 'SELECT count(*) AS n FROM generation_objects WHERE generation_id=?',
                    [
                      id
                    ]).single['n'] !=
                (incremental ? 4 : r['object_count'])) ||
        (incremental &&
            evidence['object_set'] !=
                graphAssociation(manifest.target, r['object_count'] as int,
                    evidence['edges'] as int))) {
      rejectSegment('GENERATION_RECEIPT_INVALID');
    }
    for (final ref in manifest.target.roots.values) {
      if (_db.select(
          incremental
              ? 'SELECT 1 FROM generation_roots WHERE generation_id=? AND hash=?'
              : 'SELECT 1 FROM generation_objects WHERE generation_id=? AND hash=?',
          [id, ref.hash]).isEmpty) {
        rejectSegment('GENERATION_PIN_MISSING');
      }
    }
    return manifest;
  }

  AcceptedGeneration acceptedGeneration() {
    work.add('accepted_reads');
    final session = _reusableSession();
    if (session != null) return session.accepted;
    return _acceptedFromStorage();
  }

  AcceptedGeneration _acceptedFromStorage({Set<String> knownPins = const {}}) {
    work.add('accepted_metadata_reads');
    _requirePublication();
    _requireSchema(_db, acquisition: true, publication: true);
    final rows = _db.select('SELECT * FROM accepted');
    if (rows.length != 1) rejectSegment('ACCEPTED_METADATA_INVALID');
    final r = rows.single;
    final id = r['current_id'] as String?,
        previous = r['previous_id'] as String?;
    final sequence = r['sequence'];
    if (r['id'] != 1 ||
        sequence is! int ||
        sequence < 0 ||
        ((id == null) != (sequence == 0)) ||
        (id == null && previous != null) ||
        (previous != null && previous == id) ||
        r['checksum'] != _acceptedChecksum(cache.key, id, previous, sequence)) {
      rejectSegment('ACCEPTED_METADATA_INVALID');
    }
    final manifest = id == null
        ? null
        : _generation(uuidValue(id), knownPins: knownPins.contains(id));
    final prior = previous == null
        ? null
        : _generation(uuidValue(previous),
            knownPins: knownPins.contains(previous));
    if (id != null) {
      final receipt = decodeC1(_db.select(
          'SELECT receipt FROM generations WHERE id=?',
          [id]).single['receipt'] as Uint8List) as Map;
      if (receipt['base_sync_root'] != prior?.target.syncRoot) {
        rejectSegment('BASE_PROVENANCE_INVALID');
      }
    }
    return AcceptedGeneration._(id, sequence, manifest, previous, cache.key);
  }

  PreparedGeneration prepareGeneration(String generationId, String stagingId,
      CompleteGenerationProof proof, AcceptedGeneration expected,
      {required int verifiedDataVersion,
      Map<String, int> authorityHistory = const {
        'lineage': 0,
        'authentication': 0,
        'request': 0
      }}) {
    _requirePublication();
    uuidValue(generationId);
    if (expected._namespace != cache.key) rejectSegment('BASE_CONTEXT_INVALID');
    return _transaction<PreparedGeneration>(() {
      if (publicationDataVersion != verifiedDataVersion) {
        rejectSegment('VERIFICATION_STALE');
      }
      final stage = _loadStage(stagingId);
      if (stage == null ||
          !sameBytes(stage.manifest.bytes, proof.manifest.bytes) ||
          acquisitionProgress(stagingId)?.state != 'graph_verified') {
        rejectSegment('STAGING_NOT_VERIFIED');
      }
      final evidence = decodeC1(proof.receipt) as Map<String, dynamic>;
      final incremental = evidence['validator'] == 'segmented-e3/2';
      final binding = _candidateBindings[proof];
      if (incremental &&
          (binding == null ||
              binding.base != expected.id ||
              binding.sequence != expected.sequence ||
              binding.dataVersion != verifiedDataVersion)) {
        rejectSegment('VERIFICATION_CONNECTION_REQUIRED');
      }
      if (evidence['base_sync_root'] != expected.manifest?.target.syncRoot ||
          (!incremental &&
              evidence['validator'] != CompleteGenerationProof.validator)) {
        rejectSegment('BASE_PROVENANCE_INVALID');
      }
      if (proof.receipt.length > limits.manifestBytes) {
        rejectSegment('LOCAL_METADATA_BUDGET');
      }
      // Non-secret provenance, never authority on restart. Only AppState's live
      // original ticket/guard can authorize the later COMMIT.
      final receipt = encodeC1({
        ...evidence,
        'authority_history': {'owner': cache.principalId, ...authorityHistory}
      });
      if (receipt.length > limits.manifestBytes) {
        rejectSegment('LOCAL_METADATA_BUDGET');
      }
      _fault?.call('before_generation_prepare');
      _db.execute('INSERT INTO generations VALUES(?,?,?,?,?,?,?)', [
        generationId,
        proof.manifest.bytes,
        localChecksum(proof.manifest.bytes),
        receipt,
        localChecksum(receipt),
        proof.graph.objects.length,
        DateTime.now().toUtc().toIso8601String()
      ]);
      _fault?.call('after_generation_manifest');
      for (final ref in incremental
          ? proof.manifest.target.roots.values
          : proof.graph.objects) {
        if (_db.select(
                'SELECT bytes FROM refs JOIN objects USING(hash) WHERE hash=?',
                [ref.hash]).singleOrNull?['bytes'] !=
            ref.bytes) {
          rejectSegment('OBJECT_MISSING');
        }
        _db.execute(
            incremental
                ? 'INSERT INTO generation_roots VALUES(?,?)'
                : 'INSERT INTO generation_objects VALUES(?,?)',
            [generationId, ref.hash]);
        work.add('pin_inserts');
      }
      _fault?.call('after_generation_pins');
      _generation(generationId,
          expectedManifest: proof.manifest.bytes, expectedReceipt: receipt);
      return PreparedGeneration._(generationId, expected, proof.manifest.bytes,
          receipt, verifiedDataVersion, this, proof);
    });
  }

  // Concrete synchronous entry: this API cannot accept an async transaction
  // body. The only fence is the actual AppState-owned throwing guard closure.
  SegmentedPublication commitPreparedGeneration(PreparedGeneration prepared,
      {required void Function() finalAuthorityFence}) {
    _requirePublication();
    if (!identical(prepared._owner, this)) {
      rejectSegment('PREPARATION_CONNECTION_CHANGED');
    }
    // Dart permits an async closure in a void callback context. Never silently
    // ignore such a Future here; AppState's actual guard is synchronous.
    if (finalAuthorityFence is Future Function()) {
      rejectSegment('ASYNC_PUBLICATION_FENCE');
    }
    final timer = Stopwatch()..start();
    var begun = false, committed = false, sequence = prepared.expected.sequence;
    String publishedId = prepared.id;
    try {
      _db.execute('BEGIN IMMEDIATE');
      work.add('transactions');
      begun = true;
      _requireSchema(_db, acquisition: true, publication: true);
      _fault?.call('after_publication_begin');
      final priorSession = _reusableSession();
      final current = _acceptedFromStorage(knownPins: {
        if (priorSession?.accepted.id != null) priorSession!.accepted.id!,
        if (priorSession?.accepted.previousId != null)
          priorSession!.accepted.previousId!,
      });
      if (prepared.expected._namespace != cache.key ||
          current.id != prepared.expected.id ||
          current.sequence != prepared.expected.sequence) {
        rejectSegment('PUBLICATION_CONFLICT');
      }
      if (publicationDataVersion != prepared._dataVersion) {
        rejectSegment('VERIFICATION_STALE');
      }
      final manifest = _generation(prepared.id,
          expectedManifest: prepared._manifest,
          expectedReceipt: prepared._receipt);
      final same =
          current.manifest?.target.syncRoot == manifest.target.syncRoot;
      if (same) {
        publishedId = current.id!;
      } else {
        if (sequence == 9223372036854775807) {
          rejectSegment('PUBLICATION_SEQUENCE_EXHAUSTED');
        }
        sequence++;
        _db.execute(
            'UPDATE accepted SET current_id=?,previous_id=?,sequence=?,checksum=? WHERE id=1',
            [
              prepared.id,
              current.id,
              sequence,
              _acceptedChecksum(cache.key, prepared.id, current.id, sequence)
            ]);
        work.add('accepted_writes');
      }
      _fault?.call('after_accepted_pointer');
      final usage = _db.select('SELECT * FROM usage WHERE id=1').single;
      if ((usage['metadata'] as int) > limits.metadataBytes ||
          (usage['stages'] as int) > limits.stagingCount) {
        rejectSegment('LOCAL_METADATA_BUDGET');
      }
      if ((usage['objects'] as int) > limits.objectCount ||
          (usage['payload'] as int) > limits.totalObjectBytes) {
        rejectSegment('LOCAL_STORAGE_BUDGET');
      }
      _fault?.call('before_publication_commit');
      // Between the final fence and COMMIT: NO callbacks, hooks, scheduling,
      // notifications or awaits. The private connection has no user UDF hooks.
      finalAuthorityFence();
      _db.execute('COMMIT');
      committed = true;
      begun = false;
      final transactionTime = timer.elapsedMicroseconds;
      _fault?.call('after_publication_commit');
      final readback = Stopwatch()..start();
      _fault?.call('during_publication_readback');
      // Read actual persisted rows, not the old connection-local pointer. Old
      // pins already proved within this unchanged session need no COUNT scan.
      final accepted = _acceptedFromStorage(knownPins: {
        if (priorSession?.accepted.id != null) priorSession!.accepted.id!,
        if (priorSession?.accepted.previousId != null)
          priorSession!.accepted.previousId!,
      });
      if (accepted.id != publishedId ||
          accepted.sequence != sequence ||
          accepted.manifest?.target.syncRoot != manifest.target.syncRoot) {
        rejectSegment('ACCEPTED_READBACK_INVALID');
      }
      // Our own COMMIT does not change this connection's data_version. Never
      // stamp an old proof with a NEW counter from a post-COMMIT external write.
      if (publicationDataVersion != prepared._dataVersion) {
        rejectSegment('VERIFICATION_STALE');
      }
      prepared._proof.adoptVerifiedData();
      _acceptedSession =
          _AcceptedSession(accepted, prepared._proof, prepared._dataVersion);
      return SegmentedPublication(publishedId, sequence, manifest.target, same,
          transactionTime, readback.elapsedMicroseconds);
    } catch (error) {
      _acceptedSession = null;
      if (committed) {
        throw PublicationCommittedException(publishedId, sequence, error);
      }
      if (error is SqliteException) {
        throw SegmentedException(
            error.resultCode == 5 || error.resultCode == 6
                ? 'STORE_BUSY'
                : 'PERSISTENCE_FAILED',
            storageCode: error.extendedResultCode);
      }
      rethrow;
    } finally {
      if (begun) {
        try {
          _db.execute('ROLLBACK');
        } on Object {/* primary failure wins, including a closed connection */}
      }
    }
  }

  bool discardUnacceptedGeneration(String id) => _transaction<bool>(() {
        _requirePublication();
        uuidValue(id);
        if (_db.select(
            'SELECT 1 FROM accepted WHERE current_id=? OR previous_id=?',
            [id, id]).isNotEmpty) {
          return false;
        }
        final pins = _db.select('''SELECT
          (SELECT count(*) FROM generation_objects WHERE generation_id=?)+
          (SELECT count(*) FROM generation_roots WHERE generation_id=?) AS n''',
            [id, id]).single['n'] as int;
        _db.execute('DELETE FROM generations WHERE id=?', [id]);
        work.add('pin_deletes', pins);
        return _db.updatedRows != 0;
      });

  Future<AcceptedGeneration> recoverAcceptedGeneration() async {
    final reusable = _reusableSession();
    if (reusable != null) {
      work.add('recovery_reuses');
      _pruneUnselected(reusable.accepted);
      if (_reusableSession() != null) return reusable.accepted;
    }
    work.add('full_recoveries');
    _acceptedSession = null;
    final version = publicationDataVersion;
    final before = acceptedGeneration();
    CompleteGenerationProof? currentProof;
    for (final id in [before.id, before.previousId]) {
      if (id == null) continue;
      final manifest = _generation(id);
      final proof = await verifyCompleteGeneration(manifest,
          (ref) => getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING')),
          maxObjects: limits.objectCount, work: work);
      work.add('recovery_objects', proof.graph.objects.length);
      if (id == before.id) currentProof = proof;
      final sorted = proof.graph.objects.map((r) => r.toJson()).toList()
        ..sort((a, b) => (a['hash'] as String).compareTo(b['hash'] as String));
      final evidence = decodeC1(_db.select(
          'SELECT receipt FROM generations WHERE id=?',
          [id]).single['receipt'] as Uint8List) as Map;
      final incremental = evidence['validator'] == 'segmented-e3/2';
      final pinned = _db
          .select(
              incremental
                  ? 'WITH RECURSIVE closure(hash) AS (SELECT hash FROM generation_roots WHERE generation_id=? UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash) SELECT r.hash,r.bytes FROM closure JOIN refs r USING(hash) ORDER BY r.hash'
                  : 'SELECT r.hash,r.bytes FROM generation_objects p JOIN refs r USING(hash) WHERE generation_id=? ORDER BY hash',
              [id])
          .map((r) => {'hash': r['hash'], 'bytes': r['bytes']})
          .toList();
      final recomputed = decodeC1(proof.receipt) as Map;
      if (!sameBytes(encodeC1(sorted), encodeC1(pinned)) ||
          evidence['object_set'] !=
              (incremental
                  ? graphAssociation(manifest.target,
                      proof.graph.objects.length, proof.graph.edges)
                  : localChecksum(encodeC1(sorted)))) {
        rejectSegment('GENERATION_PIN_INVALID');
      }
      if (evidence['objects'] != recomputed['objects'] ||
          evidence['edges'] != recomputed['edges'] ||
          evidence['facts'] != recomputed['facts']) {
        rejectSegment('GENERATION_RECEIPT_INVALID');
      }
    }
    final after = acceptedGeneration();
    if (before.id != after.id || before.sequence != after.sequence) {
      rejectSegment('PUBLICATION_CONFLICT');
    }
    if (publicationDataVersion != version) rejectSegment('VERIFICATION_STALE');
    _pruneUnselected(after);
    if (publicationDataVersion != version) rejectSegment('VERIFICATION_STALE');
    _acceptedSession = _AcceptedSession(after, currentProof, version);
    return after;
  }

  void _pruneUnselected(AcceptedGeneration after) {
    // Original cleanup scope and exclusions, unchanged. No immutable sweep.
    // Prepared-only pin leaks after interrupted operations are reclaimable;
    // current and previous remain pinned. Immutable bytes are never swept here.
    for (final row in _db.select(
        'SELECT id FROM generations WHERE id IS NOT ? AND id IS NOT ?',
        [after.id, after.previousId])) {
      discardUnacceptedGeneration(row['id'] as String);
    }
  }
}

final _publicationDefinitions = <String, String>{
  ..._acquisitionDefinitions,
  for (final match
      in RegExp(r'^CREATE (?:TABLE|INDEX|TRIGGER) (\w+).+$', multiLine: true)
          .allMatches(_publicationSchema))
    match.group(1)!: match.group(0)!.substring(0, match.group(0)!.length - 1)
};

String _acceptedChecksum(
        String namespace, String? current, String? previous, int sequence) =>
    localChecksum(encodeC1({
      'namespace': namespace,
      'current': current,
      'previous': previous,
      'sequence': '$sequence'
    }));

const _publicationSchema = '''
CREATE TABLE generations(id TEXT PRIMARY KEY,manifest BLOB NOT NULL,manifest_checksum TEXT NOT NULL,receipt BLOB NOT NULL,receipt_checksum TEXT NOT NULL,object_count INTEGER NOT NULL CHECK(object_count>=4),created_at TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE generation_objects(generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,hash TEXT NOT NULL REFERENCES objects(hash),PRIMARY KEY(generation_id,hash)) WITHOUT ROWID;
CREATE TABLE accepted(id INTEGER PRIMARY KEY CHECK(id=1),current_id TEXT REFERENCES generations(id),previous_id TEXT REFERENCES generations(id),sequence INTEGER NOT NULL CHECK(sequence>=0),checksum TEXT NOT NULL,CHECK((current_id IS NULL)=(sequence=0)),CHECK(previous_id IS NULL OR current_id IS NOT NULL),CHECK(previous_id IS NULL OR previous_id!=current_id));
INSERT INTO accepted VALUES(1,NULL,NULL,0,'');
UPDATE usage SET metadata=metadata+256 WHERE id=1;
CREATE TRIGGER generation_usage AFTER INSERT ON generations BEGIN UPDATE usage SET metadata=metadata+length(NEW.manifest)+length(NEW.receipt)+512; END;
CREATE TRIGGER generation_release AFTER DELETE ON generations BEGIN UPDATE usage SET metadata=metadata-length(OLD.manifest)-length(OLD.receipt)-512; END;
CREATE TRIGGER generation_pin_usage AFTER INSERT ON generation_objects BEGIN UPDATE usage SET metadata=metadata+128; END;
CREATE TRIGGER generation_pin_release AFTER DELETE ON generation_objects BEGIN UPDATE usage SET metadata=metadata-128; END;
CREATE TRIGGER immutable_generation BEFORE UPDATE ON generations BEGIN SELECT RAISE(ABORT,'immutable generation'); END;
CREATE TRIGGER immutable_pin BEFORE UPDATE ON generation_objects BEGIN SELECT RAISE(ABORT,'immutable pin'); END;
CREATE TRIGGER retained_pin_delete BEFORE DELETE ON generation_objects WHEN EXISTS(SELECT 1 FROM generations WHERE id=OLD.generation_id) BEGIN SELECT RAISE(ABORT,'retained pin'); END;
CREATE TRIGGER retained_generation_delete BEFORE DELETE ON generations WHEN EXISTS(SELECT 1 FROM accepted WHERE current_id=OLD.id OR previous_id=OLD.id) BEGIN SELECT RAISE(ABORT,'retained generation'); END;
CREATE TRIGGER retained_object_delete BEFORE DELETE ON objects WHEN EXISTS(SELECT 1 FROM generation_objects WHERE hash=OLD.hash) BEGIN SELECT RAISE(ABORT,'retained object'); END;
CREATE TRIGGER immutable_ref BEFORE UPDATE ON refs BEGIN SELECT RAISE(ABORT,'immutable reference'); END;
''';

final _incrementalPublicationDefinitions = <String, String>{
  ..._publicationDefinitions,
  for (final match
      in RegExp(r'^CREATE (?:TABLE|INDEX|TRIGGER) (\w+).+$', multiLine: true)
          .allMatches(_incrementalPublicationSchema))
    match.group(1)!: match.group(0)!.substring(0, match.group(0)!.length - 1)
};

// Additive isolated v4 only. All v3 definitions/associations stay intact.
// Expensive recursive reachability is ONLY on explicit maintenance DELETE,
// never ordinary INSERT or publication. Protect edges as well as object rows.
const _incrementalPublicationSchema = '''
CREATE TABLE generation_roots(generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE CASCADE,hash TEXT NOT NULL REFERENCES objects(hash),PRIMARY KEY(generation_id,hash)) WITHOUT ROWID;
CREATE INDEX generation_root_hash ON generation_roots(hash);
CREATE TRIGGER generation_root_usage AFTER INSERT ON generation_roots BEGIN UPDATE usage SET metadata=metadata+128; END;
CREATE TRIGGER generation_root_release AFTER DELETE ON generation_roots BEGIN UPDATE usage SET metadata=metadata-128; END;
CREATE TRIGGER immutable_generation_root BEFORE UPDATE ON generation_roots BEGIN SELECT RAISE(ABORT,'immutable root pin'); END;
CREATE TRIGGER retained_root_delete BEFORE DELETE ON generation_roots WHEN EXISTS(SELECT 1 FROM generations WHERE id=OLD.generation_id) BEGIN SELECT RAISE(ABORT,'retained root pin'); END;
CREATE TRIGGER retained_graph_object_delete BEFORE DELETE ON objects WHEN EXISTS(WITH RECURSIVE retained(hash) AS(SELECT hash FROM generation_roots UNION SELECT e.child FROM edges e JOIN retained r ON e.parent=r.hash) SELECT 1 FROM retained WHERE hash=OLD.hash) BEGIN SELECT RAISE(ABORT,'retained descendant'); END;
CREATE TRIGGER retained_graph_edge_delete BEFORE DELETE ON edges WHEN EXISTS(WITH RECURSIVE retained(hash) AS(SELECT hash FROM generation_roots UNION SELECT e.child FROM edges e JOIN retained r ON e.parent=r.hash) SELECT 1 FROM retained WHERE hash=OLD.parent) BEGIN SELECT RAISE(ABORT,'retained edge'); END;
CREATE TRIGGER immutable_graph_edge BEFORE UPDATE ON edges BEGIN SELECT RAISE(ABORT,'immutable edge'); END;
''';
