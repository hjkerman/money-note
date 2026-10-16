part of 'adapters.dart';

// Explicit opt-in workspace. Never registered by startup. All original B/J
// formats, parsers and writer algorithms remain owned by OfflineStore.
class E4Workspace extends OfflineStore {
  E4Workspace(Directory privateRoot, {void Function(String)? fault})
      : root = Directory('${privateRoot.path}/segmented-e4-workspace'),
        _fault = fault,
        super(
            directoryProvider: () async =>
                Directory('${privateRoot.path}/segmented-e4-workspace'));
  final Directory root;
  final void Function(String)? _fault;
  OfflineBaseline? _cachedB;
  SegmentedClientStore? _cachedStore;
  String? _cachedKey, _cachedFile;
  int fullBaselineReads = 0, lineageVerifications = 0, frozenCacheReuses = 0;
  File get _source => File('${root.path}/e4-source.json');
  File get _baselineFile => File('${root.path}/offline-mode/baseline.json');
  Map<String, dynamic> _readSource() {
    if (_source.lengthSync() > 16384) rejectSegment('LOCAL_METADATA_BUDGET');
    return _sourceRecord(jsonDecode(_source.readAsStringSync()));
  }

  Map<String, dynamic> _sourceRecord(Object? value) {
    if (value is! Map<String, dynamic>) rejectSegment('FROZEN_BINDING_INVALID');
    if (value['storage'] != SegmentedClientStore.discriminator) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    hashValue(value['namespace']);
    if (value['kind'] == 'segmented') {
      if (value['frozen'] != null || value['binding'] != null) {
        rejectSegment('SOURCE_PROVENANCE_INVALID');
      }
      uuidValue(value['generation']);
      if (value['sequence'] is! int ||
          value['sequence'] < 1 ||
          (value['previous_installation'] == null) !=
              (value['previous_sequence'] == null)) {
        rejectSegment('INSTALLATION_METADATA_INVALID');
      }
      if (value['previous_installation'] != null) {
        uuidValue(value['previous_installation']);
        if (value['previous_sequence'] is! int ||
            value['previous_sequence'] < 1) {
          rejectSegment('INSTALLATION_METADATA_INVALID');
        }
      }
      if ((value['legacy_frozen'] == null) !=
          (value['legacy_binding'] == null)) {
        rejectSegment('FROZEN_BINDING_INVALID');
      }
      if (value['legacy_frozen'] != null) {
        uuidValue(value['legacy_frozen']);
        hashValue(value['legacy_binding']);
      }
    } else {
      if (value['kind'] != null) rejectSegment('FROZEN_BINDING_INVALID');
      if (value['legacy_frozen'] != null ||
          value['legacy_binding'] != null ||
          value['generation'] != null ||
          value['sequence'] != null) {
        rejectSegment('SOURCE_PROVENANCE_INVALID');
      }
      uuidValue(value['frozen']);
      hashValue(value['binding']);
      if (value['previous_file'] != null) hashValue(value['previous_file']);
    }
    if (value['previous_source'] != null &&
        value['previous_source'] is! Map<String, dynamic>) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    return value;
  }

  // Ordinary legacy Offline/recovery is NOT a bypass for §31 after this opt-in
  // workspace has installed segmented-origin B. Isolated readers use the
  // explicitly verified method below; no developer flag can open this gate.
  @override
  Future<OfflineBaseline?> loadBaseline() async {
    throw const OfflinePersistenceException(
        'R1_RECOVERY_CONTRACT_REQUIRED: segmented Offline/recovery는 아직 활성화할 수 없습니다.');
  }

  // Read-only fallback with the SAME journal serial owner; never Offline entry.
  @override
  Future<OfflineReconciliationBundle?> loadReconciliationBundle() async {
    if (_source.existsSync()) {
      throw const OfflinePersistenceException('명시적 frozen 검증이 필요합니다.');
    }
    final baseline = await super.loadBaseline();
    if (baseline == null) return null;
    return OfflineReconciliationBundle(
        baseline: baseline,
        metadata: await loadMetadata(),
        operations: await loadJournal());
  }

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) {
    if (beforePublish is Future Function() &&
        beforePublish is! Never Function()) {
      rejectSegment('ASYNC_PUBLICATION_FENCE');
    }
    _cachedB = null;
    _cachedKey = null;
    return super.replaceBaseline(baseline, beforePublish: () {
      _fault?.call('before_legacy_rename');
      beforePublish?.call();
    });
  }

  Map<String, dynamic> bindingFor(AcceptedGeneration generation,
          OfflineBaseline baseline, String namespace) =>
      {
        'version': 1, 'namespace': namespace, 'generation': generation.id,
        'sequence': generation.sequence,
        'legacy_lineage': recoveryLineageFingerprint(baseline),
        'legacy_fingerprint': baseline.serverStateFingerprint,
        'snapshot_id': baseline.authoritativeSnapshot!['snapshot_id'],
        'baseline_sha256': localChecksum(encodeC1(baseline.toJson())),
        'synced_at': baseline.syncedAt.toUtc().toIso8601String(),
        // Session credentials are intentionally NOT part of any durable binding.
        'user': {
          'id': baseline.user.id,
          'username': baseline.user.username,
          'display_name': baseline.user.displayName,
          'share_pin_needs_change': baseline.user.sharePinNeedsChange
        },
        'resolved_id': baseline.resolvedReconciliationId
      };

  void _writeSource(Map<String, dynamic> value, void Function() guard) {
    if (guard is Future Function() && guard is! Never Function()) {
      rejectSegment('ASYNC_PUBLICATION_FENCE');
    }
    final encoded = jsonEncode(value);
    if (utf8.encode(encoded).length > 16384) {
      rejectSegment('LOCAL_METADATA_BUDGET');
    }
    root.createSync(recursive: true);
    final tmp = File('${_source.path}.prepared');
    try {
      tmp.writeAsStringSync(encoded, flush: true);
      jsonDecode(tmp.readAsStringSync());
      _fault?.call('before_source_rename');
      guard();
      tmp.renameSync(_source.path);
    } finally {
      if (tmp.existsSync()) tmp.deleteSync();
    }
  }

  void prepareLegacySource(FrozenGeneration frozen, void Function() guard) {
    final previous = _baselineFile.existsSync()
        ? localChecksum(_baselineFile.readAsBytesSync())
        : null;
    final old = _source.existsSync() ? _readSource() : null;
    _writeSource({
      'storage': SegmentedClientStore.discriminator,
      'namespace': frozen.binding['namespace'],
      'frozen': frozen.id,
      'binding': frozen.checksum,
      'previous_file': previous,
      'previous_source': old == null
          ? null
          : {...old, 'previous_file': null, 'previous_source': null}
    }, guard);
    _fault?.call('after_source_prepare');
  }

  void requireOnlineHandoffSync() {
    final state = File('${root.path}/offline-mode/state.json');
    final metadata = state.existsSync()
        ? OfflineWorkspaceMetadata.fromJson(
            jsonDecode(state.readAsStringSync()) as Map<String, dynamic>)
        : const OfflineWorkspaceMetadata(mode: ConnectivityMode.online);
    final journal = File('${root.path}/offline-mode/journal.ndjson');
    if (metadata.mode != ConnectivityMode.online ||
        metadata.reconciliationId != null ||
        (journal.existsSync() && journal.lengthSync() != 0)) {
      rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
    }
  }

  Map<String, dynamic> prepareSegmentedSource(SegmentedClientStore store,
      AcceptedGeneration target, void Function() guard) {
    final old = _source.existsSync() ? _readSource() : null;
    final previous = store.installedGeneration();
    _requireSourceOwner(store, old);
    if (target.manifest == null || target.id == null) {
      rejectSegment('INSTALLATION_METADATA_INVALID');
    }
    store.cache.verifyTarget(target.manifest!.target);
    final prepared = <String, dynamic>{
      'storage': SegmentedClientStore.discriminator,
      'kind': 'segmented',
      'namespace': store.cache.key,
      'generation': target.id,
      'sequence': target.sequence,
      'legacy_frozen': old?['legacy_frozen'] ?? old?['frozen'],
      'legacy_binding': old?['legacy_binding'] ?? old?['binding'],
      'previous_installation': previous?.id,
      'previous_sequence': previous?.sequence,
      'previous_source': old == null
          ? null
          : {...old, 'previous_source': null, 'previous_file': null}
    };
    _writeSource(prepared, () {
      guard();
      _requireRecoverySource(old);
      _requireSourceOwner(store, old);
    });
    return Map<String, dynamic>.unmodifiable(prepared);
  }

  // A source is DATA provenance, never an AppState permit. Native installed
  // identity and legacy Frozen-B identity are distinct obligations. A legacy
  // B may have committed before its native installed pointer was finalized.
  FrozenGeneration? _requireSourceOwner(
      SegmentedClientStore store, Map<String, dynamic>? value) {
    final installed = store.installedGeneration();
    final owners = store.frozenGenerations().where((f) => f.installed).toList();
    if (value == null) {
      if (installed != null || owners.isNotEmpty) {
        rejectSegment('SOURCE_PROVENANCE_REQUIRED');
      }
      return null; // Genuine first source, not an invented predecessor.
    }
    final source = _sourceRecord(value);
    if (source['namespace'] != store.cache.key || owners.length > 1) {
      rejectSegment('SOURCE_PROVENANCE_INVALID');
    }
    if (source['kind'] == 'segmented' &&
        (installed?.id != source['generation'] ||
            installed?.sequence != source['sequence'])) {
      rejectSegment('SOURCE_PROVENANCE_INVALID');
    }
    final id = source['legacy_frozen'] ?? source['frozen'];
    final binding = source['legacy_binding'] ?? source['binding'];
    if (owners.isEmpty) {
      if (source['kind'] != 'segmented' || id != null || binding != null) {
        rejectSegment('SOURCE_PROVENANCE_INVALID');
      }
      return null;
    }
    final frozen = owners.single;
    if (id != frozen.id || binding != frozen.checksum) {
      rejectSegment('SOURCE_PROVENANCE_INVALID');
    }
    return frozen; // _frozen also validates namespace/receipt/required root pins.
  }

  Future<void> verifySegmentedInstallationBase(
      SegmentedClientStore store) async {
    final source = _source.existsSync() ? _readSource() : null;
    final frozen = _requireSourceOwner(store, source);
    if (frozen != null) {
      await readFrozenBaseline(store, frozen.id, store.cache.principalId);
    }
    _requireRecoverySource(source);
    _requireSourceOwner(store, source);
  }

  // Called in the installed transaction's final fence and before retirement/UI.
  // The expected source is the exact preparation of THIS original request, not
  // a reconstructed predecessor or cached authorization result.
  void requireNativeInstallationSource(SegmentedClientStore store,
      AcceptedGeneration target, Map<String, dynamic> expected) {
    _requireRecoverySource(expected);
    if (expected['kind'] != 'segmented' ||
        expected['generation'] != target.id ||
        expected['sequence'] != target.sequence) {
      rejectSegment('SOURCE_PROVENANCE_INVALID');
    }
    final frozen = _requireSourceOwner(store, expected);
    final previous = expected['previous_source'];
    if (previous == null) {
      if (expected['previous_installation'] != null || frozen != null) {
        rejectSegment('SOURCE_PROVENANCE_REQUIRED');
      }
    } else {
      final prior = _sourceRecord(previous);
      if (prior['namespace'] != store.cache.key ||
          (prior['kind'] == 'segmented' &&
              (prior['generation'] != expected['previous_installation'] ||
                  prior['sequence'] != expected['previous_sequence'])) ||
          (prior['legacy_frozen'] ?? prior['frozen']) !=
              expected['legacy_frozen'] ||
          (prior['legacy_binding'] ?? prior['binding']) !=
              expected['legacy_binding']) {
        rejectSegment('SOURCE_PROVENANCE_INVALID');
      }
    }
    final installed = store.installedGeneration()!;
    if (expected['previous_installation'] != installed.id &&
        expected['previous_installation'] != installed.previousId) {
      rejectSegment('PUBLICATION_CONFLICT');
    }
    if (frozen != null &&
        (!identical(_cachedStore, store) ||
            _cachedB == null ||
            _cachedKey !=
                '${store.cache.key}:${frozen.id}:${frozen.checksum}:${frozen.receiptIdentity}:${store.publicationDataVersion}' ||
            _cachedFile != _stamp())) {
      rejectSegment('VERIFICATION_STALE');
    }
  }

  void handoffPoint(String point) => _fault?.call(point);

  // Final deletion is synchronous and token/owner/status-specific. The real
  // AppState fence runs AFTER every hook/read and immediately before unlink.
  // A GET, accepted receipt, matching row or sync_root can never call this with
  // an outcomeUnknown marker. The existing durable marker is the receipt.
  void retireConfirmedSync(PendingOnlineWrite pending, void Function() guard) {
    if (guard is Future Function() && guard is! Never Function()) {
      rejectSegment('ASYNC_PUBLICATION_FENCE');
    }
    _fault?.call('before_pending_retire');
    if (pending.status != OnlineWriteStatus.serverCommittedRebuildPending) {
      rejectSegment('PENDING_NOT_CONFIRMED');
    }
    final file =
        File('${root.path}/offline-mode/online-write-${pending.userId}.json');
    if (!file.existsSync() || file.lengthSync() > 16384) {
      rejectSegment('PENDING_IDENTITY_CHANGED');
    }
    final current = PendingOnlineWrite.fromJson(
        jsonDecode(file.readAsStringSync()) as Map<String, dynamic>,
        pending.userId);
    if (current.token != pending.token ||
        current.retryIdentity != pending.retryIdentity ||
        current.status != pending.status) {
      rejectSegment('PENDING_IDENTITY_CHANGED');
    }
    guard();
    file.deleteSync();
  }

  void requirePendingIdentitySync(PendingOnlineWrite? expected, int owner) {
    final file = File('${root.path}/offline-mode/online-write-$owner.json');
    if (!file.existsSync()) {
      if (expected != null) rejectSegment('PENDING_IDENTITY_CHANGED');
      return;
    }
    if (expected == null || file.lengthSync() > 16384) {
      rejectSegment('PENDING_IDENTITY_CHANGED');
    }
    final actual = PendingOnlineWrite.fromJson(
        jsonDecode(file.readAsStringSync()) as Map<String, dynamic>, owner);
    if (actual.token != expected.token ||
        actual.status != expected.status ||
        actual.retryIdentity != expected.retryIdentity) {
      rejectSegment('PENDING_IDENTITY_CHANGED');
    }
  }

  String _stamp() {
    final s = _baselineFile.statSync();
    return '${s.type}:${s.size}:${s.modified.microsecondsSinceEpoch}:${s.changed.microsecondsSinceEpoch}';
  }

  // A data-only recovery owns only the exact durable source it observed,
  // including the local operation UUID/sequence, not merely its sync_root.
  // This check and rename/unlink are synchronous on the owning isolate. Run
  // it AFTER hooks as well as after awaits; never restore a copied old source
  // on behalf of a newer operation. SQLite ownership is fenced separately.
  void _requireRecoverySource(Map<String, dynamic>? expected) {
    if (expected == null
        ? _source.existsSync()
        : !_source.existsSync() ||
            jsonEncode(_readSource()) != jsonEncode(expected)) {
      throw const _SupersededSourceRecovery();
    }
  }

  void _restoreRecoverySource(SegmentedClientStore store,
      Map<String, dynamic> expected, void Function() fence) {
    void check() {
      _requireRecoverySource(expected);
      final previous = expected['previous_source'];
      _requireSourceOwner(
          store, previous == null ? null : Map<String, dynamic>.from(previous));
      fence();
    }

    final previous = expected['previous_source'];
    if (previous != null) {
      _writeSource(Map<String, dynamic>.from(previous), check);
    } else {
      _fault?.call('before_source_rename');
      check();
      _source.deleteSync();
    }
  }

  void _requirePreviousBaseline(Map<String, dynamic> source) {
    final unchanged = source['previous_file'] == null
        ? !_baselineFile.existsSync()
        : _baselineFile.existsSync() &&
            localChecksum(_baselineFile.readAsBytesSync()) ==
                source['previous_file'];
    if (!unchanged) rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
    requireOnlineHandoffSync();
  }

  // A crash after the old source was restored but before SQLite COMMIT can
  // leave an unreferenced preparation. Release only that bounded orphan, under
  // the still-installed source/B owner, never a new or ambiguous legacy B.
  void _discardAbandonedPreparations(SegmentedClientStore store,
      Map<String, dynamic> source, FrozenGeneration installed) {
    final abandoned = store
        .frozenGenerations()
        .where((f) => !f.installed && f.id != installed.id)
        .toList();
    if (abandoned.isEmpty) return;
    final baselineBytes = localChecksum(_baselineFile.readAsBytesSync());
    for (final preparation in abandoned) {
      if (preparation.binding['baseline_sha256'] ==
          installed.binding['baseline_sha256']) {
        rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
      }
      store.discardFrozenPreparation(preparation, finalAuthorityFence: () {
        _requireRecoverySource(source);
        requireOnlineHandoffSync();
        final owner = store
            .frozenGenerations()
            .where((f) => f.id == installed.id && f.installed);
        if (owner.length != 1 ||
            owner.single.checksum != installed.checksum ||
            localChecksum(_baselineFile.readAsBytesSync()) != baselineBytes) {
          rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
        }
      });
    }
  }

  Future<void> _recoverNativePreparations(
      SegmentedClientStore store, Map<String, dynamic> source) async {
    final preparations =
        store.frozenGenerations().where((f) => !f.installed).toList();
    if (preparations.isEmpty) return; // bounded metadata, no legacy scan
    if (source['legacy_frozen'] != null) {
      final frozen =
          await store.recoverFrozenGeneration(source['legacy_frozen']);
      await readFrozenBaseline(store, frozen.id, store.cache.principalId);
      _requireRecoverySource(source);
      if (!frozen.installed) rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
      _discardAbandonedPreparations(store, source, frozen);
      return;
    }
    // A first legacy preparation can also have an installed native predecessor
    // and no frozen B yet. Prove it never replaced B before releasing its pin.
    final previousFile = _baselineFile.existsSync()
        ? localChecksum(_baselineFile.readAsBytesSync())
        : null;
    final baseline = await super.loadBaseline();
    _requireRecoverySource(source);
    for (final preparation in preparations) {
      if (baseline != null &&
          localChecksum(encodeC1(baseline.toJson())) ==
              preparation.binding['baseline_sha256']) {
        rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
      }
      store.discardFrozenPreparation(preparation, finalAuthorityFence: () {
        _requireRecoverySource(source);
        _requirePreviousBaseline({'previous_file': previousFile});
        final installed = store.installedGeneration();
        if (installed?.id != source['generation'] ||
            installed?.sequence != source['sequence']) {
          throw const _SupersededSourceRecovery();
        }
      });
    }
  }

  // Native source readback, NOT a restored ticket. Does not install UI, replay
  // J, retire markers, or enable Offline. Crash recovery may only finalize data
  // association, or discard a provably never-published preparation.
  Future<FrozenGeneration?> recoverLegacyHandoff(
      SegmentedClientStore store) async {
    try {
      return await _recoverLegacyHandoff(store);
    } on _SupersededSourceRecovery {
      // Another operation owns the source now. This is NOT installation
      // success or restored authority; leave its files, lineage and pins alone.
      return null;
    }
  }

  Future<FrozenGeneration?> _recoverLegacyHandoff(
      SegmentedClientStore store) async {
    if (!_source.existsSync()) {
      final all = store.frozenGenerations();
      if (all.any((f) => f.installed) || store.installedGeneration() != null) {
        rejectSegment('FROZEN_BINDING_INVALID');
      }
      final preparations = all.where((f) => !f.installed).toList();
      if (preparations.isEmpty) return null;
      final metadata = await loadMetadata(), journal = await loadJournal();
      if (metadata.mode != ConnectivityMode.online || journal.isNotEmpty) {
        return null;
      }
      final previousFile = _baselineFile.existsSync()
          ? localChecksum(_baselineFile.readAsBytesSync())
          : null;
      final old = await super.loadBaseline();
      _requireRecoverySource(null);
      for (final p in preparations) {
        if (old != null &&
            localChecksum(encodeC1(old.toJson())) ==
                p.binding['baseline_sha256']) {
          rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
        }
        store.discardFrozenPreparation(p, finalAuthorityFence: () {
          _requireRecoverySource(null);
          _requirePreviousBaseline({'previous_file': previousFile});
          if (store.installedGeneration() != null) {
            throw const _SupersededSourceRecovery();
          }
        });
      }
      return null;
    }
    final source = _readSource();
    if (source['storage'] != SegmentedClientStore.discriminator ||
        source['namespace'] != store.cache.key) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    if (source['kind'] == 'segmented') {
      // Missing predecessor is not permission to erase an already installed
      // source. Reject obvious ownership contradictions before full recovery;
      // a committed current source does not need its obsolete rollback hint.
      final current = store.installedGeneration();
      if (current?.id == source['generation'] &&
          current?.sequence == source['sequence']) {
        _requireSourceOwner(store, source);
      } else if (current?.id == source['previous_installation'] &&
          current?.sequence == source['previous_sequence']) {
        final previous = source['previous_source'];
        _requireSourceOwner(store,
            previous == null ? null : Map<String, dynamic>.from(previous));
      } else {
        rejectSegment('INSTALLATION_METADATA_INVALID');
      }
      final installed = await store.recoverInstalledGeneration();
      _requireRecoverySource(source);
      if (installed?.id == source['generation'] &&
          installed?.sequence == source['sequence']) {
        _requireSourceOwner(store, source);
        await _recoverNativePreparations(store, source);
        return null;
      }
      if (installed?.id == source['previous_installation'] &&
          installed?.sequence == source['previous_sequence']) {
        store.restoreUncommittedSource(installed,
            restoreSource: () => _restoreRecoverySource(store, source, () {}));
        return null;
      }
      rejectSegment('INSTALLATION_METADATA_INVALID');
    }
    final matches = store
        .frozenGenerations()
        .where((f) => f.id == source['frozen'])
        .toList();
    if (matches.length != 1 || matches.single.checksum != source['binding']) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    final frozen = matches.single;
    if (frozen.installed &&
        identical(_cachedStore, store) &&
        _cachedB != null) {
      await readFrozenBaseline(store, frozen.id, store.cache.principalId);
      _requireRecoverySource(source);
      _discardAbandonedPreparations(store, source, frozen);
      return frozen;
    }
    final baseline = await super.loadBaseline();
    _requireRecoverySource(source);
    fullBaselineReads++;
    if (baseline != null &&
        localChecksum(encodeC1(baseline.toJson())) ==
            frozen.binding['baseline_sha256']) {
      await readFrozenBaseline(store, frozen.id, store.cache.principalId);
      if (!frozen.installed) {
        final metadata = await loadMetadata(), journal = await loadJournal();
        _requireRecoverySource(source);
        if (metadata.mode != ConnectivityMode.online || journal.isNotEmpty) {
          rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
        }
        return store.finishFrozenHandoff(frozen, finalAuthorityFence: () {
          _requireRecoverySource(source);
          requireOnlineHandoffSync();
          // Data-only recovery: no legacy publication/installation authority.
          if (localChecksum(_baselineFile.readAsBytesSync()) !=
              localChecksum(utf8.encode(jsonEncode(baseline.toJson())))) {
            rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
          }
        });
      }
      _requireRecoverySource(source);
      _discardAbandonedPreparations(store, source, frozen);
      return frozen;
    }
    final unchanged = source['previous_file'] == null
        ? !_baselineFile.existsSync()
        : _baselineFile.existsSync() &&
            localChecksum(_baselineFile.readAsBytesSync()) ==
                source['previous_file'];
    final metadata = await loadMetadata(), journal = await loadJournal();
    _requireRecoverySource(source);
    if (!frozen.installed &&
        unchanged &&
        metadata.mode == ConnectivityMode.online &&
        journal.isEmpty) {
      // BEGIN IMMEDIATE validates/deletes ONLY this prepared SQL owner before
      // its final fence restores the source. No await/hook after the final
      // source/B check and rename/unlink. A missing/installed owner cannot
      // mutate the file first. The old installed pin remains protected.
      var restored = false;
      try {
        store.discardFrozenPreparation(frozen, finalAuthorityFence: () {
          _restoreRecoverySource(
              store, source, () => _requirePreviousBaseline(source));
          restored = true;
        });
      } catch (_) {
        // File replace is not a SQLite transaction. If COMMIT failed after
        // replace, put back THIS preparation only while both durable owners
        // still match. A post-COMMIT error (row gone) is not a rollback.
        if (restored) {
          try {
            final previous = source['previous_source'] == null
                ? null
                : Map<String, dynamic>.from(source['previous_source']);
            _requireRecoverySource(previous);
            final remaining = store.frozenGenerations().where((f) =>
                f.id == frozen.id &&
                f.checksum == frozen.checksum &&
                !f.installed);
            if (remaining.length == 1) {
              store.restoreUncommittedSource(store.installedGeneration(),
                  preparation: remaining.single,
                  restoreSource: () => _writeSource(source, () {
                        _requireRecoverySource(previous);
                        _requirePreviousBaseline(source);
                      }));
            }
          } on Object {/* retain pins and the primary persistence error */}
        }
        rethrow;
      }
      return null;
    }
    rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
  }

  Future<OfflineBaseline> readFrozenBaseline(
      SegmentedClientStore store, String id, int owner) async {
    final frozen = await store.recoverFrozenGeneration(id);
    if (!_source.existsSync()) rejectSegment('FROZEN_BINDING_INVALID');
    final source = _readSource();
    if (source['namespace'] != store.cache.key ||
        (source['legacy_frozen'] ?? source['frozen']) != id ||
        (source['legacy_binding'] ?? source['binding']) != frozen.checksum ||
        source['storage'] != SegmentedClientStore.discriminator) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    if (frozen.target.principalId != owner ||
        store.cache.principalId != owner) {
      rejectSegment('READ_PRINCIPAL_MISMATCH');
    }
    final key =
        '${store.cache.key}:$id:${frozen.checksum}:${frozen.receiptIdentity}:${store.publicationDataVersion}';
    final stamp = _stamp();
    // File stat is only an additional INVALIDATION signal, never the proof of
    // raw integrity. Authority comes from the owned verified immutable graph,
    // durable binding and cached immutable B. Unread bitrot is not promised to
    // be detected immediately; restart/full export revalidates everything.
    if (identical(_cachedStore, store) &&
        _cachedB != null &&
        _cachedKey == key &&
        _cachedFile == stamp) {
      store.withFrozenRead(frozen, (r) {
        r.hot;
        r.control;
      }); // mandatory hash-on-read
      frozenCacheReuses++;
      return _cachedB!;
    }
    final user = AuthUser.fromJson(frozen.binding['user']);
    final bundle =
        store.withFrozenRead(frozen, (r) => materializeLegacyRead(r, user));
    final reconstructed = legacyBaseline(
        bundle, DateTime.parse(frozen.binding['synced_at']),
        resolvedId: frozen.binding['resolved_id']);
    final disk = await super.loadBaseline();
    fullBaselineReads++;
    lineageVerifications++;
    if (disk == null ||
        disk.user.id != owner ||
        recoveryLineageFingerprint(disk) != frozen.binding['legacy_lineage'] ||
        recoveryLineageFingerprint(reconstructed) !=
            frozen.binding['legacy_lineage'] ||
        localChecksum(encodeC1(disk.toJson())) !=
            frozen.binding['baseline_sha256'] ||
        disk.serverStateFingerprint != bundle.envelope.fingerprint ||
        bundle.envelope.snapshot['snapshot_id'] !=
            frozen.binding['snapshot_id']) {
      rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
    }
    if (store.publicationDataVersion.toString() != key.split(':').last ||
        _stamp() != stamp) {
      rejectSegment('VERIFICATION_STALE');
    }
    _cachedB = _immutableBaseline(reconstructed);
    _cachedStore = store;
    _cachedKey = key;
    _cachedFile = stamp;
    return _cachedB!;
  }

  Future<PendingLegacyView?> readPendingForIsolatedUse(
      SegmentedClientStore store, int owner) async {
    final metadata = await loadMetadata();
    if (metadata.mode == ConnectivityMode.online) {
      if ((await loadJournal()).isNotEmpty) {
        rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
      }
      return null;
    }
    if (!_source.existsSync()) return readPendingLegacyView(this, owner);
    final source = _readSource();
    final id = source['legacy_frozen'] ?? source['frozen'];
    if (id is! String ||
        !store.frozenGenerations().any((f) => f.id == id && f.installed)) {
      rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
    }
    return readFrozenPending(store, id, owner);
  }

  Future<PendingLegacyView> readFrozenPending(
      SegmentedClientStore store, String id, int owner) async {
    final baseline = await readFrozenBaseline(store, id, owner);
    final metadata = await loadMetadata();
    final frozen = store.frozenGenerations().singleWhere((f) => f.id == id);
    final operations = await loadJournal();
    if (![ConnectivityMode.offline, ConnectivityMode.reconciliationRequired]
            .contains(metadata.mode) ||
        metadata.baselineLineageFingerprint !=
            frozen.binding['legacy_lineage'] ||
        !isConsistentPersistedLineage(
            metadata: metadata,
            baseline: baseline,
            resolved: false,
            journalIsEmpty: operations.isEmpty,
            baselineFingerprint: frozen.binding['legacy_lineage'])) {
      rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
    }
    return PendingLegacyView._(
        metadata.baselineLineageFingerprint!,
        OfflineReconciliationBundle(
            baseline: baseline,
            metadata: metadata,
            operations: List.unmodifiable(operations)),
        OfflineProjection.from(baseline, operations));
  }
}

class _SupersededSourceRecovery implements Exception {
  const _SupersededSourceRecovery();
}

class E4LegacyInstallation {
  const E4LegacyInstallation(
      this.publication, this.frozen, this.pendingRemains);
  final SegmentedPublication publication;
  final FrozenGeneration frozen;
  final bool pendingRemains; // outcomeUnknown is NEVER submit success
}

class E4SegmentedInstallation {
  const E4SegmentedInstallation(
      this.publication, this.authority, this.pendingRemains);
  final SegmentedPublication publication;
  final SegmentedAuthority authority;
  final bool pendingRemains;
}

// Post-install failure is NOT a rollback and cannot recreate an acknowledged
// marker. Fresh recovery reads durable complete B and never replays the POST.
class E4InstallationCommittedException implements Exception {
  const E4InstallationCommittedException(this.frozenId, this.cause);
  final String frozenId;
  final Object cause;
  @override
  String toString() => 'E4InstallationCommittedException';
}

OfflineBaseline legacyBaseline(CoherentRefreshBundle bundle, DateTime syncedAt,
    {String? resolvedId}) {
  final c = bundle.candidate, e = bundle.envelope;
  return OfflineBaseline(
      syncedAt: syncedAt,
      user: c.user,
      summary: c.summary,
      cardPaymentStatus: c.cardPaymentStatus,
      judgment: c.judgment,
      monthCloseStatus: c.monthCloseStatus,
      settings: c.settings,
      ownerDiscountMonth: c.ownerDiscountMonth,
      familyDiscountMonth: c.familyDiscountMonth,
      transitDiscountProfile: c.transitDiscountProfile,
      entries: c.entries,
      confirmedPlannedEntries: c.confirmedPlannedEntries,
      panels: c.panels,
      cashFlows: c.cashFlows,
      authoritativeSnapshot: e.snapshot,
      serverStateFingerprint: e.fingerprint,
      discountPolicyDefaults: e.discountPolicyDefaults,
      resolvedReconciliationId: resolvedId);
}

Object? _immutableJson(Object? v) => v is Map
    ? Map<String, dynamic>.unmodifiable(
        v.map((k, v) => MapEntry(k as String, _immutableJson(v))))
    : v is List
        ? List.unmodifiable(v.map(_immutableJson))
        : v;
OfflineBaseline _immutableBaseline(OfflineBaseline b) {
  final m = b.monthCloseStatus;
  return OfflineBaseline(
      syncedAt: b.syncedAt,
      user: b.user,
      summary: b.summary,
      cardPaymentStatus: b.cardPaymentStatus,
      judgment: b.judgment,
      monthCloseStatus: MonthCloseStatus(
          calendarDate: m.calendarDate,
          calendarMonth: m.calendarMonth,
          needsClose: m.needsClose,
          isEarlyClose: m.isEarlyClose,
          earlyCloseAvailable: m.earlyCloseAvailable,
          earlyCloseStartDay: m.earlyCloseStartDay,
          canClose: m.canClose,
          oldestOpenMonth: m.oldestOpenMonth,
          lastClosedMonth: m.lastClosedMonth,
          unconfirmedRecurringItems:
              List.unmodifiable(m.unconfirmedRecurringItems),
          cardRecurringConfirmationAvailable:
              m.cardRecurringConfirmationAvailable),
      settings: AppSettings(values: Map.unmodifiable(b.settings.values)),
      ownerDiscountMonth: b.ownerDiscountMonth,
      familyDiscountMonth: b.familyDiscountMonth,
      transitDiscountProfile: b.transitDiscountProfile,
      entries: List.unmodifiable(b.entries),
      confirmedPlannedEntries: List.unmodifiable(b.confirmedPlannedEntries),
      panels: List.unmodifiable(b.panels),
      cashFlows: List.unmodifiable(b.cashFlows),
      authoritativeSnapshot:
          _immutableJson(b.authoritativeSnapshot) as Map<String, dynamic>,
      serverStateFingerprint: b.serverStateFingerprint,
      discountPolicyDefaults: Map.unmodifiable(b.discountPolicyDefaults),
      resolvedReconciliationId: b.resolvedReconciliationId);
}
