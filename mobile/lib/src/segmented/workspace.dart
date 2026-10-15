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
    final value = jsonDecode(_source.readAsStringSync());
    if (value is! Map<String, dynamic>) rejectSegment('FROZEN_BINDING_INVALID');
    if (value['storage'] != SegmentedClientStore.discriminator) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    hashValue(value['namespace']);
    if (value['kind'] == 'segmented') {
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
    root.createSync(recursive: true);
    final tmp = File('${_source.path}.prepared');
    try {
      tmp.writeAsStringSync(jsonEncode(value), flush: true);
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

  void prepareSegmentedSource(SegmentedClientStore store,
      AcceptedGeneration target, void Function() guard) {
    final old = _source.existsSync() ? _readSource() : null;
    final previous = store.installedGeneration();
    _writeSource({
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
    }, guard);
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

  // Native source readback, NOT a restored ticket. Does not install UI, replay
  // J, retire markers, or enable Offline. Crash recovery may only finalize data
  // association, or discard a provably never-published preparation.
  Future<FrozenGeneration?> recoverLegacyHandoff(
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
      final old = await super.loadBaseline();
      for (final p in preparations) {
        if (old != null &&
            localChecksum(encodeC1(old.toJson())) ==
                p.binding['baseline_sha256']) {
          rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
        }
        store.discardFrozenPreparation(p, finalAuthorityFence: () {});
      }
      return null;
    }
    final source = _readSource();
    if (source['storage'] != SegmentedClientStore.discriminator ||
        source['namespace'] != store.cache.key) {
      rejectSegment('FROZEN_BINDING_INVALID');
    }
    if (source['kind'] == 'segmented') {
      final installed = await store.recoverInstalledGeneration();
      if (installed?.id == source['generation'] &&
          installed?.sequence == source['sequence']) {
        return null;
      }
      if (installed?.id == source['previous_installation'] &&
          installed?.sequence == source['previous_sequence']) {
        if (source['previous_source'] != null) {
          _writeSource(
              Map<String, dynamic>.from(source['previous_source']), () {});
        } else {
          _source.deleteSync();
        }
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
      return frozen;
    }
    final baseline = await super.loadBaseline();
    fullBaselineReads++;
    if (baseline != null &&
        localChecksum(encodeC1(baseline.toJson())) ==
            frozen.binding['baseline_sha256']) {
      await readFrozenBaseline(store, frozen.id, store.cache.principalId);
      if (!frozen.installed) {
        final metadata = await loadMetadata(), journal = await loadJournal();
        if (metadata.mode != ConnectivityMode.online || journal.isNotEmpty) {
          rejectSegment('FROZEN_HANDOFF_RECOVERY_REQUIRED');
        }
        return store.finishFrozenHandoff(frozen, finalAuthorityFence: () {
          requireOnlineHandoffSync();
          // Data-only recovery: no legacy publication/installation authority.
          if (localChecksum(_baselineFile.readAsBytesSync()) !=
              localChecksum(utf8.encode(jsonEncode(baseline.toJson())))) {
            rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
          }
        });
      }
      return frozen;
    }
    final unchanged = source['previous_file'] == null
        ? !_baselineFile.existsSync()
        : _baselineFile.existsSync() &&
            localChecksum(_baselineFile.readAsBytesSync()) ==
                source['previous_file'];
    final metadata = await loadMetadata(), journal = await loadJournal();
    if (!frozen.installed &&
        unchanged &&
        metadata.mode == ConnectivityMode.online &&
        journal.isEmpty) {
      if (source['previous_source'] != null) {
        _writeSource(
            Map<String, dynamic>.from(source['previous_source']), () {});
      } else {
        _source.deleteSync();
      }
      store.discardFrozenPreparation(frozen, finalAuthorityFence: () {
        if (_baselineFile.existsSync() &&
            localChecksum(_baselineFile.readAsBytesSync()) !=
                source['previous_file']) {
          rejectSegment('LEGACY_LINEAGE_UNAVAILABLE');
        }
      });
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
