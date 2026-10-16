part of 'store.dart';

// Frozen ownership is a durable DATA obligation, never an installation permit.
// At most the installed legacy B and one prepared replacement per namespace.
class FrozenGeneration {
  FrozenGeneration._(this.id, this.generationId, this.sequence, this.manifest,
      this.binding, this.checksum, this.receiptIdentity, this.installed);
  final String id, generationId, checksum, receiptIdentity;
  final int sequence;
  final ObservationManifest manifest;
  final Map<String, dynamic> binding;
  final bool installed;
  SyncTarget get target => manifest.target;
}

class _FrozenSession {
  _FrozenSession(this.frozen, this.proof, this.version);
  final FrozenGeneration frozen;
  final CompleteGenerationProof proof;
  final int version;
}

extension SegmentedFrozenStore on SegmentedClientStore {
  // Segmented-native installation data reference. NOT legacy B, not frozen
  // lineage, not current request authority. Current/previous protect publication
  // failures; all logical reads still use a native borrowed snapshot.
  AcceptedGeneration? installedGeneration() {
    _requireFrozen();
    final r = _db.select('SELECT * FROM installed WHERE id=1').singleOrNull;
    if (r == null) return null;
    final manifest = _generation(r['generation_id'] as String);
    if (r['sequence'] is! int ||
        (r['sequence'] as int) < 1 ||
        r['checksum'] !=
            _acceptedChecksum(cache.key, r['generation_id'] as String,
                r['previous_id'] as String?, r['sequence'] as int)) {
      rejectSegment('INSTALLATION_METADATA_INVALID');
    }
    if (r['previous_id'] != null) _generation(r['previous_id'] as String);
    return AcceptedGeneration._(r['generation_id'] as String,
        r['sequence'] as int, manifest, r['previous_id'] as String?, cache.key);
  }

  AcceptedGeneration commitInstalledGeneration(AcceptedGeneration expected,
      {required void Function() finalAuthorityFence,
      void Function()? prepareSource}) {
    var committed = false;
    try {
      final result = _transaction(() {
        final accepted = _reusableSession()?.accepted;
        if (accepted?.id != expected.id ||
            accepted?.sequence != expected.sequence ||
            expected._namespace != cache.key) {
          rejectSegment('PUBLICATION_CONFLICT');
        }
        final previous = installedGeneration();
        // E4 source preparation shares this writer lock. All file/fault hooks
        // precede the final source + original AppState fence and native COMMIT.
        if (prepareSource is Future Function() &&
            prepareSource is! Never Function()) {
          rejectSegment('ASYNC_PUBLICATION_FENCE');
        }
        prepareSource?.call();
        if (previous?.id == expected.id) return previous!;
        _db.execute(
            'INSERT INTO installed VALUES(1,?,?,?,?) ON CONFLICT(id) DO UPDATE SET generation_id=excluded.generation_id,previous_id=excluded.previous_id,sequence=excluded.sequence,checksum=excluded.checksum',
            [
              expected.id,
              previous?.id,
              expected.sequence,
              _acceptedChecksum(
                  cache.key, expected.id, previous?.id, expected.sequence)
            ]);
        _fault?.call('after_segmented_install_pointer');
        return installedGeneration()!;
      }, finalFence: finalAuthorityFence, onCommitted: () => committed = true);
      _fault?.call('during_installation_readback');
      final actual = installedGeneration();
      if (actual?.id != result.id || actual?.sequence != result.sequence) {
        rejectSegment('INSTALLATION_METADATA_INVALID');
      }
      final base = _reusableSession();
      if (base?.accepted.id != actual!.id) rejectSegment('VERIFICATION_STALE');
      _installedSession =
          _AcceptedSession(actual, base!.proof, publicationDataVersion);
      return actual;
    } catch (error) {
      _installedSession = null;
      if (committed) {
        throw PublicationCommittedException(
            expected.id!, expected.sequence, error);
      }
      rethrow;
    }
  }

  Future<AcceptedGeneration?> recoverInstalledGeneration() async {
    final actual = installedGeneration();
    if (actual == null) return null;
    var reusable = _installedSession;
    if (reusable?.accepted.id == actual.id &&
        reusable?.accepted.sequence == actual.sequence &&
        reusable?.dataVersion == publicationDataVersion &&
        (reusable?.proof?.hasMatchingDataIdentity ?? false)) {
      return actual;
    }
    await recoverAcceptedGeneration();
    reusable = _reusableSession();
    if (reusable?.accepted.id == actual.id) {
      _installedSession =
          _AcceptedSession(actual, reusable!.proof, publicationDataVersion);
      return actual;
    }
    final version = publicationDataVersion;
    final proof = await verifyCompleteGeneration(actual.manifest!,
        (ref) => getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING')),
        maxObjects: limits.objectCount, work: work);
    if (publicationDataVersion != version ||
        installedGeneration()?.id != actual.id) {
      rejectSegment('VERIFICATION_STALE');
    }
    _installedSession = _AcceptedSession(actual, proof, version);
    return actual;
  }

  // Data-only source rollback, not installation authority. Hold the same
  // SQLite writer lock as installation while comparing the recovered pointer
  // and synchronously restoring its still-owned file. Never roll back a
  // newer installed generation after an asynchronous recovery.
  void restoreUncommittedSource(AcceptedGeneration? expected,
      {FrozenGeneration? preparation, required void Function() restoreSource}) {
    _requireFrozen();
    _transaction(() {}, finalFence: () {
      final current = installedGeneration();
      if (current?.id != expected?.id ||
          current?.sequence != expected?.sequence ||
          (expected != null && expected._namespace != cache.key)) {
        rejectSegment('PUBLICATION_CONFLICT');
      }
      if (preparation != null) {
        final owner = _frozen(preparation.id);
        if (owner.installed || owner.checksum != preparation.checksum) {
          rejectSegment('FROZEN_RELEASE_REJECTED');
        }
      }
      if (restoreSource is Future Function() &&
          restoreSource is! Never Function()) {
        rejectSegment('ASYNC_PUBLICATION_FENCE');
      }
      restoreSource();
    });
  }

  T withInstalledRead<T>(
      AcceptedGeneration expected, T Function(AcceptedReadView) read) {
    _requireNoAcceptedReader();
    if (read is Future Function(AcceptedReadView) &&
        read is! Never Function(AcceptedReadView)) {
      rejectSegment('ASYNC_ACCEPTED_READ');
    }
    var begun = false;
    AcceptedReadView? view;
    Object? failure;
    try {
      _db.execute('BEGIN DEFERRED');
      begun = true;
      final actual = installedGeneration(), session = _installedSession;
      if (actual?.id != expected.id ||
          actual?.sequence != expected.sequence ||
          session?.accepted.id != expected.id ||
          session?.dataVersion != publicationDataVersion ||
          !(session?.proof?.hasMatchingDataIdentity ?? false)) {
        rejectSegment('INSTALLED_READ_STALE');
      }
      _readingAccepted = true;
      view = AcceptedReadView._(this, actual!, false);
      final value = read(view);
      if (value is Future) rejectSegment('ASYNC_ACCEPTED_READ');
      return value;
    } catch (error) {
      failure = error;
      _installedSession = null;
      rethrow;
    } finally {
      view?._open = false;
      _readingAccepted = false;
      if (begun) {
        try {
          _db.execute('ROLLBACK');
        } catch (_) {
          _installedSession = null;
          _acceptedSession = null;
          _frozenSessions.clear();
          try {
            _db.close();
          } catch (_) {}
          _closed = true;
          if (failure == null) rejectSegment('READ_RELEASE_FAILED');
        }
      }
    }
  }

  void _requireFrozen() {
    _requirePublication();
    if (!adaptersEnabled) rejectSegment('E4_PROFILE_REQUIRED');
    _requireSchema(_db, acquisition: true, publication: true);
  }

  FrozenGeneration _frozen(String id) {
    _requireFrozen();
    final row = _db.select(
        'SELECT * FROM frozen WHERE id=?', [uuidValue(id)]).singleOrNull;
    if (row == null) rejectSegment('FROZEN_MISSING');
    final bytes = row['binding'] as Uint8List;
    if (bytes.length > limits.manifestBytes ||
        localChecksum(bytes) != row['checksum']) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    final b = record(decodeC1(bytes), [
      'version',
      'namespace',
      'generation',
      'sequence',
      'legacy_lineage',
      'legacy_fingerprint',
      'snapshot_id',
      'baseline_sha256',
      'synced_at',
      'user',
      'resolved_id'
    ]);
    final generation = row['generation_id'] as String;
    final manifest = _generation(generation);
    final receipt = _db.select(
        'SELECT receipt_checksum FROM generations WHERE id=?',
        [generation]).single['receipt_checksum'];
    if (b['version'] != 1 ||
        b['namespace'] != cache.key ||
        b['generation'] != generation ||
        b['sequence'] is! int ||
        b['sequence'] < 1 ||
        receipt != row['receipt_checksum']) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    for (final key in [
      'legacy_lineage',
      'legacy_fingerprint',
      'snapshot_id',
      'baseline_sha256'
    ]) {
      hashValue(b[key]);
    }
    final u = record(b['user'],
        ['id', 'username', 'display_name', 'share_pin_needs_change']);
    if (u['id'] != cache.principalId ||
        u['username'] is! String ||
        u['display_name'] is! String ||
        u['share_pin_needs_change'] is! bool ||
        b['synced_at'] is! String ||
        DateTime.tryParse(b['synced_at']) == null ||
        (b['resolved_id'] != null && b['resolved_id'] is! String)) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    return FrozenGeneration._(
        id,
        generation,
        b['sequence'],
        manifest,
        _freezeRead(b) as Map<String, dynamic>,
        row['checksum'],
        receipt as String,
        row['state'] == 'installed');
  }

  List<FrozenGeneration> frozenGenerations() {
    _requireFrozen();
    return List.unmodifiable(_db
        .select('SELECT id FROM frozen ORDER BY id')
        .map((r) => _frozen(r['id'] as String)));
  }

  FrozenGeneration prepareFrozenGeneration(AcceptedGeneration accepted,
      CompleteGenerationProof full, Map<String, dynamic> binding,
      {required String frozenId,
      required void Function() finalAuthorityFence}) {
    _requireFrozen();
    final proof = _materializationProofs[full];
    if (proof == null ||
        proof.id != accepted.id ||
        proof.sequence != accepted.sequence ||
        proof.version != publicationDataVersion) {
      rejectSegment('MATERIALIZATION_PROOF_STALE');
    }
    return _transaction(() {
      final actual = _acceptedFromStorage();
      if (actual.id != accepted.id ||
          actual.sequence != accepted.sequence ||
          publicationDataVersion != proof.version) {
        rejectSegment('PUBLICATION_CONFLICT');
      }
      final bytes = encodeC1(binding);
      if (bytes.length > limits.manifestBytes) {
        rejectSegment('LOCAL_METADATA_BUDGET');
      }
      for (final old in frozenGenerations()) {
        if (old.checksum == localChecksum(bytes)) return old;
      }
      if (_db.select('SELECT count(*) AS n FROM frozen').single['n'] as int >=
              2 ||
          _db
              .select("SELECT 1 FROM frozen WHERE state='prepared'")
              .isNotEmpty) {
        rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
      }
      final id = uuidValue(frozenId);
      final receipt = _db.select(
          'SELECT receipt_checksum FROM generations WHERE id=?',
          [accepted.id]).single['receipt_checksum'];
      _fault?.call('before_frozen_prepare');
      _db.execute("INSERT INTO frozen VALUES(?,?,?,?,?, 'prepared')",
          [id, accepted.id, bytes, localChecksum(bytes), receipt]);
      final frozen = _frozen(id);
      _fault?.call('after_frozen_prepare');
      return frozen;
    }, finalFence: finalAuthorityFence);
  }

  // The AppState/workspace owner MUST first verify the exact published legacy
  // B and absence of an active older B/J epoch. Never called by E3 publication.
  FrozenGeneration finishFrozenHandoff(FrozenGeneration expected,
          {required void Function() finalAuthorityFence}) =>
      _transaction(() {
        final current = _frozen(expected.id);
        if (current.checksum != expected.checksum) {
          rejectSegment('FROZEN_BINDING_INVALID');
        }
        if (current.installed) return current;
        // Both changes are in the same native transaction; no hook between.
        _db.execute('DELETE FROM frozen WHERE id!=?', [current.id]);
        _db.execute(
            "UPDATE frozen SET state='installed' WHERE id=?", [current.id]);
        _fault?.call('after_frozen_install');
        // Retained older B is released ONLY by the authorized explicit legacy
        // replacement owner, never merely because accepted changed.
        _frozenSessions.removeWhere((id, _) => id != current.id);
        return _frozen(current.id);
      }, finalFence: finalAuthorityFence);

  // Proven non-installed preparation only. Installed ownership has no public
  // unpin API. Ambiguous file publication MUST preserve this preparation.
  void discardFrozenPreparation(FrozenGeneration expected,
      {required void Function() finalAuthorityFence}) {
    _transaction(() {
      final current = _frozen(expected.id);
      if (current.installed || current.checksum != expected.checksum) {
        rejectSegment('FROZEN_RELEASE_REJECTED');
      }
      _db.execute('DELETE FROM frozen WHERE id=?', [current.id]);
    }, finalFence: finalAuthorityFence);
    _frozenSessions.remove(expected.id);
  }

  _FrozenSession? _reusableFrozen(FrozenGeneration expected) {
    final actual = _frozen(expected.id), cached = _frozenSessions[expected.id];
    if (actual.checksum != expected.checksum ||
        actual.receiptIdentity != expected.receiptIdentity) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    if (cached != null &&
        cached.version == publicationDataVersion &&
        cached.frozen.checksum == actual.checksum &&
        cached.proof.hasMatchingDataIdentity) {
      work.add('frozen_provenance_reuses');
      return cached;
    }
    _frozenSessions.remove(expected.id);
    return null;
  }

  Future<FrozenGeneration> recoverFrozenGeneration(String id) async {
    final frozen = _frozen(id);
    if (_reusableFrozen(frozen) != null) return frozen;
    work.add('frozen_full_recoveries');
    final version = publicationDataVersion;
    final proof = await verifyCompleteGeneration(frozen.manifest,
        (ref) => getVerifiedObject(ref) ?? (rejectSegment('OBJECT_MISSING')),
        maxObjects: limits.objectCount, work: work);
    final receipt = decodeC1(_db.select(
        'SELECT receipt FROM generations WHERE id=?',
        [frozen.generationId]).single['receipt'] as Uint8List) as Map;
    final actual = decodeC1(proof.receipt) as Map;
    if (['objects', 'edges', 'facts'].any((k) => receipt[k] != actual[k])) {
      rejectSegment('GENERATION_RECEIPT_INVALID');
    }
    final pins = _db
        .select(
            receipt['validator'] == 'segmented-e3/2'
                ? 'WITH RECURSIVE closure(hash) AS (SELECT hash FROM generation_roots WHERE generation_id=? UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash) SELECT r.hash,r.bytes FROM closure JOIN refs r USING(hash) ORDER BY r.hash'
                : 'SELECT r.hash,r.bytes FROM generation_objects p JOIN refs r USING(hash) WHERE generation_id=? ORDER BY hash',
            [frozen.generationId])
        .map((r) => {'hash': r['hash'], 'bytes': r['bytes']})
        .toList();
    final objects = proof.graph.objects.map((r) => r.toJson()).toList()
      ..sort((a, b) => (a['hash'] as String).compareTo(b['hash'] as String));
    if (!sameBytes(encodeC1(pins), encodeC1(objects))) {
      rejectSegment('GENERATION_PIN_INVALID');
    }
    if (publicationDataVersion != version ||
        _frozen(id).checksum != frozen.checksum) {
      rejectSegment('VERIFICATION_STALE');
    }
    _frozenSessions[id] = _FrozenSession(frozen, proof, version);
    return frozen;
  }

  T withFrozenRead<T>(
      FrozenGeneration expected, T Function(AcceptedReadView) read) {
    _requireNoAcceptedReader();
    if (read is Future Function(AcceptedReadView) &&
        read is! Never Function(AcceptedReadView)) {
      rejectSegment('ASYNC_ACCEPTED_READ');
    }
    var begun = false;
    AcceptedReadView? view;
    Object? failure;
    try {
      _db.execute('BEGIN DEFERRED');
      begun = true;
      final frozen = _frozen(expected.id);
      if (_reusableFrozen(frozen) == null) {
        rejectSegment('FROZEN_RECOVERY_REQUIRED');
      }
      if (frozen.checksum != expected.checksum) {
        rejectSegment('FROZEN_BINDING_INVALID');
      }
      _readingAccepted = true;
      view = AcceptedReadView._(
          this,
          AcceptedGeneration._(frozen.generationId, frozen.sequence,
              frozen.manifest, null, cache.key),
          true,
          frozen.id);
      final result = read(view);
      if (result is Future) rejectSegment('ASYNC_ACCEPTED_READ');
      return result;
    } catch (e) {
      failure = e;
      _frozenSessions.remove(expected.id);
      rethrow;
    } finally {
      view?._open = false;
      _readingAccepted = false;
      if (begun) {
        try {
          _db.execute('ROLLBACK');
        } catch (_) {
          _frozenSessions.clear();
          _acceptedSession = null;
          try {
            _db.close();
          } catch (_) {}
          _closed = true;
          if (failure == null) rejectSegment('READ_RELEASE_FAILED');
        }
      }
    }
  }
}

final _frozenDefinitions = <String, String>{
  ..._incrementalPublicationDefinitions,
  for (final m in RegExp(
          r'^CREATE (?:UNIQUE )?(?:TABLE|INDEX|TRIGGER) (\w+).+$',
          multiLine: true)
      .allMatches(_frozenSchema))
    m.group(1)!: m.group(0)!.substring(0, m.group(0)!.length - 1)
};

const _frozenSchema = '''
CREATE TABLE installed(id INTEGER PRIMARY KEY CHECK(id=1),generation_id TEXT NOT NULL REFERENCES generations(id),previous_id TEXT REFERENCES generations(id),sequence INTEGER NOT NULL CHECK(sequence>0),checksum TEXT NOT NULL,CHECK(previous_id IS NULL OR previous_id!=generation_id));
CREATE TRIGGER installed_usage AFTER INSERT ON installed BEGIN UPDATE usage SET metadata=metadata+256; END;
CREATE TRIGGER installed_release AFTER DELETE ON installed BEGIN UPDATE usage SET metadata=metadata-256; END;
CREATE TRIGGER retained_installed_generation BEFORE DELETE ON generations WHEN EXISTS(SELECT 1 FROM installed WHERE generation_id=OLD.id OR previous_id=OLD.id) BEGIN SELECT RAISE(ABORT,'installed generation'); END;
CREATE TABLE frozen(id TEXT PRIMARY KEY,generation_id TEXT NOT NULL REFERENCES generations(id) ON DELETE RESTRICT,binding BLOB NOT NULL,checksum TEXT NOT NULL,receipt_checksum TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('prepared','installed'))) WITHOUT ROWID;
CREATE INDEX frozen_generation ON frozen(generation_id);
CREATE UNIQUE INDEX one_installed_frozen ON frozen(state) WHERE state='installed';
CREATE UNIQUE INDEX one_prepared_frozen ON frozen(state) WHERE state='prepared';
CREATE TRIGGER frozen_usage AFTER INSERT ON frozen BEGIN UPDATE usage SET metadata=metadata+length(NEW.binding)+512; END;
CREATE TRIGGER frozen_release AFTER DELETE ON frozen BEGIN UPDATE usage SET metadata=metadata-length(OLD.binding)-512; END;
CREATE TRIGGER immutable_frozen_binding BEFORE UPDATE ON frozen WHEN NEW.id!=OLD.id OR NEW.generation_id!=OLD.generation_id OR NEW.binding!=OLD.binding OR NEW.checksum!=OLD.checksum OR NEW.receipt_checksum!=OLD.receipt_checksum OR OLD.state!='prepared' OR NEW.state!='installed' BEGIN SELECT RAISE(ABORT,'immutable frozen binding'); END;
CREATE TRIGGER frozen_limit BEFORE INSERT ON frozen WHEN (SELECT count(*) FROM frozen)>=2 BEGIN SELECT RAISE(ABORT,'frozen handoff bound'); END;
CREATE TRIGGER retained_frozen_generation BEFORE DELETE ON generations WHEN EXISTS(SELECT 1 FROM frozen WHERE generation_id=OLD.id) BEGIN SELECT RAISE(ABORT,'frozen generation'); END;
''';
