import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'api_client.dart';
import 'models.dart';
import 'notification_bridge.dart';
import 'offline/offline_data.dart';
import 'offline/offline_projection.dart';
import 'offline/offline_store.dart';

class AppState extends ChangeNotifier {
  AppState(this.api, {OfflineStore? offlineStore})
      : offlineStore = offlineStore ?? OfflineStore() {
    api.onServerUnavailable = _requestOfflinePrompt;
  }

  static const int _maxLocalSnapshots = 30;

  final MoneyNoteApiClient api;
  final OfflineStore offlineStore;
  final NotificationBridge notificationBridge = NotificationBridge();

  bool isBootstrapping = true;
  bool networkUnavailable = false;
  bool isBusy = false;
  String statusMessage = '';
  AuthUser? user;
  Summary? summary;
  CardPaymentStatus? cardPaymentStatus;
  JudgmentState? judgment;
  MonthCloseStatus? monthCloseStatus;
  AppSettings settings = AppSettings(values: const {});
  CardDiscountMonth? ownerDiscountMonth;
  CardDiscountMonth? familyDiscountMonth;
  TransitDiscountProfileStatus? transitDiscountProfile;
  List<LedgerEntry> entries = [];
  List<LedgerEntry> confirmedPlannedEntries = [];
  List<MonthlyPanel> panels = [];
  List<CashFlow> cashFlows = [];
  List<LocalSnapshotInfo> localSnapshots = [];
  NotificationPermissionStatus notificationPermissions =
      const NotificationPermissionStatus.ready();
  NotificationCandidateCounts notificationCandidateCounts =
      const NotificationCandidateCounts.empty();
  ConnectivityMode connectivityMode = ConnectivityMode.online;
  ReconciliationChoice? reconciliationChoice;
  int _lineageGeneration = 0;
  int _refreshRequestGeneration = 0;
  Future<void>? _lineageTail;
  DateTime? lastSuccessfulSyncAt;
  List<OfflineJournalOperation> offlineJournal = const [];
  bool serverFailurePromptPending = false;
  String offlineEntryMessage = '';
  bool usesConservativeCardEstimate = false;
  OfflineBaseline? _offlineBaseline;
  OfflineWorkspaceMetadata _offlineMetadata =
      const OfflineWorkspaceMetadata(mode: ConnectivityMode.online);
  bool _isForegroundRefreshRunning = false;
  int notificationImportOpenGeneration = 0;
  int notificationArchiveOpenGeneration = 0;
  String notificationArchiveSource = 'woori_card';

  bool get isLoggedIn => user != null;
  bool get isPersistenceRecoveryBlocked =>
      connectivityMode == ConnectivityMode.persistenceRecoveryBlocked;

  bool get isOnline => connectivityMode == ConnectivityMode.online;
  bool get isOffline => connectivityMode == ConnectivityMode.offline;
  bool get isReconciliationRequired =>
      connectivityMode == ConnectivityMode.reconciliationRequired;
  bool get isReconciliationFinalizing =>
      connectivityMode == ConnectivityMode.reconciliationFinalizing;
  bool get reconciliationServerChanged => _offlineMetadata.serverChanged;
  bool get reconciliationRecoveryReady =>
      _offlineMetadata.phase == ReconciliationPhase.ready &&
      _offlineMetadata.hasVerifiedRecoveryPoints;
  bool get mobileCommitIsUnknown =>
      _offlineMetadata.serverCommitStatus == ServerCommitStatus.unknown;
  bool get mobileCommitIsCommitted =>
      _offlineMetadata.serverCommitStatus == ServerCommitStatus.committed;
  bool get isServerWinsFinalizing =>
      _offlineMetadata.phase == ReconciliationPhase.serverWinsFinalizing;
  bool get hasOfflineBaseline => _offlineBaseline != null;

  bool? cachedNotificationDiscountDefault(String date, String scope) {
    if (scope != 'owner' && scope != 'family') return null;
    if (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(date) ||
        DateTime.tryParse(date) == null) {
      return null;
    }
    final month = date.substring(0, 7);
    final current =
        scope == 'family' ? familyDiscountMonth : ownerDiscountMonth;
    if (current?.month == month) return current!.isEnabled;
    if (!isOffline) return null;
    final baseline = _offlineBaseline;
    final data = baseline?.authoritativeSnapshot?['data'];
    if (data is! Map) return null;
    final settingsRows = data['app_settings'];
    if (settingsRows is! List) return null;
    final key = 'card_discount_policy:$scope:$month';
    for (final row in settingsRows) {
      if (row is Map && row['key'] == key) {
        final value = row['value'];
        if (value == 'enabled') return true;
        if (value == 'disabled') return false;
        return null;
      }
    }
    final fallback = baseline?.discountPolicyDefaults[scope];
    if (fallback == 'enabled') return true;
    if (fallback == 'disabled') return false;
    return null;
  }

  Future<bool?> notificationDiscountDefault(String date, String scope) async {
    final cached = cachedNotificationDiscountDefault(date, scope);
    if (cached != null || !isOnline) return cached;
    if (!RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(date) ||
        DateTime.tryParse(date) == null) {
      return null;
    }
    return (await api.discountMonth(date.substring(0, 7), scope)).isEnabled;
  }

  bool get canUseOnlineWrites => isOnline && !isBusy;
  bool get canCreateCardExpense => (isOnline || isOffline) && !isBusy;
  bool get canCreateCashFlow => (isOnline || isOffline) && !isBusy;
  bool get canConfirmRecurring => (isOnline || isOffline) && !isBusy;
  bool get financialValuesAreEstimated => !isOnline;
  int get pendingOfflineOperationCount => offlineJournal.length;

  String get financialEstimateLabel =>
      usesConservativeCardEstimate ? '오프라인 보수적 예상값' : '오프라인 예상값';

  bool get hasOutstandingCardPayment =>
      (cardPaymentStatus?.effectiveRemainingTotal ?? 0) > 0;

  String get currentMonth {
    final serverMonth = monthCloseStatus?.calendarMonth ?? '';
    if (serverMonth.length >= 7) return serverMonth.substring(0, 7);
    final entryMonth = entries
        .where((entry) => entry.entryDate != null)
        .map((entry) => entry.entryDate!.substring(0, 7))
        .toList();
    if (entryMonth.isNotEmpty) return entryMonth.last;
    final panelMonth = panels.map((panel) => panel.month).toList();
    if (panelMonth.isNotEmpty) return panelMonth.last;
    final now = DateTime.now();
    return '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}';
  }

  List<LedgerEntry> get expenseEntries {
    final rows =
        entries.where((entry) => entry.entryKind == 'expense').toList();
    rows.sort((a, b) {
      final dateCompare = (b.entryDate ?? '').compareTo(a.entryDate ?? '');
      if (dateCompare != 0) return dateCompare;
      return b.id.compareTo(a.id);
    });
    return rows;
  }

  List<LedgerEntry> get recentEntries => expenseEntries.take(5).toList();

  List<LedgerEntry> get plannedEntries {
    final rows =
        entries.where((entry) => entry.entryKind == 'planned').toList();
    rows.sort((a, b) {
      final dueCompare = (a.dueDay ?? 0).compareTo(b.dueDay ?? 0);
      if (dueCompare != 0) return dueCompare;
      final sortCompare = a.sortOrder.compareTo(b.sortOrder);
      if (sortCompare != 0) return sortCompare;
      return a.id.compareTo(b.id);
    });
    return rows;
  }

  String get serverToday {
    final calendarDate = monthCloseStatus?.calendarDate ?? '';
    if (calendarDate.length >= 10) return calendarDate.substring(0, 10);
    return _localToday();
  }

  List<MonthlyPanel> panelsByType(String panelType) {
    final rows = panels.where((panel) => panel.panelType == panelType).toList();
    rows.sort((a, b) {
      final dateCompare = (a.spentOn ?? '').compareTo(b.spentOn ?? '');
      if (dateCompare != 0) return dateCompare;
      final sortCompare = a.sortOrder.compareTo(b.sortOrder);
      if (sortCompare != 0) return sortCompare;
      return a.id.compareTo(b.id);
    });
    return rows;
  }

  Future<void> bootstrap() async {
    notificationBridge.setLaunchTargetHandler(consumeLaunchTarget);
    await refreshNotificationPermissions(notify: false);
    await api.loadSession();
    final restoredOffline =
        await restorePersistedOfflineWorkspace(notify: false);
    if (restoredOffline) {
      isBootstrapping = false;
      notifyListeners();
      return;
    }

    try {
      await api.health();
      networkUnavailable = false;
      user = await api.me();
      await refresh(notify: false);
      await saveLaunchSnapshot();
      await consumeLaunchTarget(notify: false);
    } on MoneyNoteConnectionException catch (error) {
      statusMessage = error.message;
      _requestOfflinePrompt();
    } on MoneyNoteApiException catch (error) {
      user = null;
      statusMessage = error.message;
    } finally {
      isBootstrapping = false;
      notifyListeners();
    }
  }

  Future<bool> restorePersistedOfflineWorkspace({bool notify = true}) async {
    try {
      final metadata = await offlineStore.loadMetadata();
      _offlineMetadata = metadata;
      connectivityMode = metadata.mode;
      reconciliationChoice = metadata.reconciliationChoice;
      _offlineBaseline = await offlineStore.loadBaseline();
      offlineJournal = await offlineStore.loadJournal();
      lastSuccessfulSyncAt = _offlineBaseline?.syncedAt;
      final baseline = _offlineBaseline;
      final resolved = baseline?.resolvedReconciliationId != null &&
          baseline!.resolvedReconciliationId == metadata.reconciliationId &&
          metadata.mode == ConnectivityMode.reconciliationFinalizing;
      final validFinalizing = switch (metadata.phase) {
        ReconciliationPhase.mobileRequestPending =>
          metadata.reconciliationChoice == ReconciliationChoice.applyToServer &&
              metadata.serverCommitStatus == ServerCommitStatus.unknown,
        ReconciliationPhase.mobileCommitted =>
          metadata.reconciliationChoice == ReconciliationChoice.applyToServer &&
              metadata.serverCommitStatus == ServerCommitStatus.committed,
        ReconciliationPhase.serverWinsFinalizing =>
          metadata.reconciliationChoice ==
                  ReconciliationChoice.discardAndUseServer &&
              metadata.serverCommitStatus == ServerCommitStatus.none,
        _ => false,
      };
      if ((offlineJournal.isNotEmpty &&
              (metadata.mode == ConnectivityMode.online || baseline == null)) ||
          (metadata.mode == ConnectivityMode.reconciliationFinalizing &&
              (metadata.reconciliationId == null || !validFinalizing)) ||
          (metadata.mode == ConnectivityMode.reconciliationRequired &&
              metadata.phase != ReconciliationPhase.none &&
              (metadata.reconciliationChoice == null ||
                  metadata.reconciliationId == null)) ||
          (metadata.baselineLineageFingerprint != null &&
              baseline != null &&
              !resolved &&
              metadata.baselineLineageFingerprint !=
                  offlineStore.recoveryLineageFingerprint(baseline))) {
        throw const OfflinePersistenceException(
          '오프라인 기준 데이터와 journal의 lineage를 확인할 수 없어 복구가 필요합니다.',
        );
      }
    } on OfflinePersistenceException catch (error) {
      const blocked = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.persistenceRecoveryBlocked,
      );
      _offlineMetadata = blocked;
      connectivityMode = blocked.mode;
      reconciliationChoice = null;
      _lineageGeneration += 1;
      offlineEntryMessage = error.message;
      if (notify) notifyListeners();
      return true;
    }

    if (isOnline) {
      if (notify) notifyListeners();
      return false;
    }

    final baseline = _offlineBaseline;
    if (baseline == null) {
      const blocked = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.persistenceRecoveryBlocked,
      );
      _offlineMetadata = blocked;
      connectivityMode = blocked.mode;
      _lineageGeneration += 1;
      offlineEntryMessage = '오프라인 lineage의 기준 데이터를 찾을 수 없어 복구가 필요합니다.';
      if (notify) notifyListeners();
      return true;
    }
    if (_journalWasResolvedByBaseline(baseline)) {
      _restoreAuthoritativeBaseline(baseline);
    } else {
      _restoreOfflineProjection(baseline);
    }
    await checkServerRecovery(notify: false);
    final persistedChoice = _offlineMetadata.reconciliationChoice;
    if (isReconciliationRequired &&
        _offlineMetadata.phase == ReconciliationPhase.preparing &&
        persistedChoice != null) {
      await _prepareReconciliation(persistedChoice);
    }
    if (notify) notifyListeners();
    return true;
  }

  Future<void> login(String username, String password) async {
    await _run(() async {
      await api.health();
      networkUnavailable = false;
      user = await api.login(username, password);
      await refresh(notify: false);
      await saveLaunchSnapshot();
      await consumeLaunchTarget(notify: false);
      statusMessage = '로그인 완료';
    });
  }

  Future<void> logout() async {
    await _run(() async {
      _requireOnline('로그아웃');
      await api.logout();
      user = null;
      summary = null;
      cardPaymentStatus = null;
      judgment = null;
      monthCloseStatus = null;
      entries = [];
      confirmedPlannedEntries = [];
      panels = [];
      cashFlows = [];
      statusMessage = '로그아웃 완료';
    });
  }

  Future<void> refresh({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<void> _refreshAuthoritativeState({
    bool notify = true,
    bool allowBaselineWhileFinalizing = false,
  }) async {
    if (!_refreshModeAllowed(allowBaselineWhileFinalizing)) {
      throw MoneyNoteApiException(
          '현재 상태에서는 authoritative refresh를 설치할 수 없습니다.');
    }
    final generation = _lineageGeneration;
    final refreshRequest = ++_refreshRequestGeneration;
    await refreshNotificationPermissions(notify: false);

    for (var attempt = 0; attempt < 3; attempt += 1) {
      final before = await _readAuthoritativeBaselineEnvelope();
      final candidate = await _fetchAuthoritativeStateCandidate();
      final after = await _readAuthoritativeBaselineEnvelope();
      if (before.fingerprint != after.fingerprint ||
          before.revision != after.revision ||
          before.evaluationDate != after.evaluationDate ||
          candidate.monthCloseStatus.calendarDate != after.evaluationDate) {
        continue;
      }

      await _withLineageLock(() async {
        if (generation != _lineageGeneration ||
            refreshRequest != _refreshRequestGeneration ||
            !_refreshModeAllowed(allowBaselineWhileFinalizing)) {
          throw MoneyNoteApiException(
            '상태가 변경되어 오래된 authoritative refresh 결과를 폐기했습니다.',
          );
        }
        final baseline = OfflineBaseline(
          syncedAt: DateTime.now().toUtc(),
          authoritativeSnapshot: after.snapshot,
          serverStateFingerprint: after.fingerprint,
          resolvedReconciliationId: isReconciliationFinalizing
              ? _offlineMetadata.reconciliationId
              : null,
          discountPolicyDefaults: after.discountPolicyDefaults,
          user: candidate.user,
          summary: candidate.summary,
          cardPaymentStatus: candidate.cardPaymentStatus,
          judgment: candidate.judgment,
          monthCloseStatus: candidate.monthCloseStatus,
          settings: candidate.settings,
          ownerDiscountMonth: candidate.ownerDiscountMonth,
          familyDiscountMonth: candidate.familyDiscountMonth,
          transitDiscountProfile: candidate.transitDiscountProfile,
          entries: candidate.entries,
          confirmedPlannedEntries: candidate.confirmedPlannedEntries,
          panels: candidate.panels,
          cashFlows: candidate.cashFlows,
        );
        await offlineStore.replaceBaseline(baseline);
        _offlineBaseline = baseline;
        user = candidate.user;
        summary = candidate.summary;
        cardPaymentStatus = candidate.cardPaymentStatus;
        judgment = candidate.judgment;
        entries = candidate.entries;
        confirmedPlannedEntries = candidate.confirmedPlannedEntries;
        panels = candidate.panels;
        cashFlows = candidate.cashFlows;
        settings = candidate.settings;
        monthCloseStatus = candidate.monthCloseStatus;
        ownerDiscountMonth = candidate.ownerDiscountMonth;
        familyDiscountMonth = candidate.familyDiscountMonth;
        transitDiscountProfile = candidate.transitDiscountProfile;
        lastSuccessfulSyncAt = baseline.syncedAt;
        usesConservativeCardEstimate = false;
        offlineEntryMessage = '';
      });
      await _configureNotificationCards();
      await refreshNotificationInboxState(notify: false);
      if (notify) notifyListeners();
      return;
    }

    throw MoneyNoteApiException(
      '동기화 중 서버 데이터가 계속 변경되어 coherent offline baseline을 만들지 못했습니다.',
    );
  }

  bool _refreshModeAllowed(bool allowBaselineWhileFinalizing) =>
      isOnline || (allowBaselineWhileFinalizing && isReconciliationFinalizing);

  Future<_AuthoritativeStateCandidate>
      _fetchAuthoritativeStateCandidate() async {
    final currentUser = user;
    if (currentUser == null) {
      throw MoneyNoteApiException('로그인 사용자 정보가 없습니다.');
    }
    final freshMonthCloseStatus = await api.monthCloseStatus();
    final results = await Future.wait([
      api.summary(),
      api.currentCardPaymentStatus(),
      api.judgment(),
      api.currentEntries(),
      api.confirmedPlannedEntries(),
      api.currentPanels(),
      _loadRecentCashFlows(freshMonthCloseStatus),
      api.settings(),
    ]);
    final freshSummary = results[0] as Summary;
    final freshCardPaymentStatus = results[1] as CardPaymentStatus;
    final freshJudgment = results[2] as JudgmentState;
    final freshEntries = results[3] as List<LedgerEntry>;
    final freshConfirmedPlannedEntries = results[4] as List<LedgerEntry>;
    final freshPanels = results[5] as List<MonthlyPanel>;
    final freshCashFlows = results[6] as List<CashFlow>;
    final freshSettings = results[7] as AppSettings;
    final freshMonth = _monthFor(
      freshMonthCloseStatus,
      freshEntries,
      freshPanels,
    );
    final discountResults = await Future.wait([
      api.discountMonth(freshMonth, 'owner'),
      api.discountMonth(freshMonth, 'family'),
      api.transitDiscountProfile(freshMonth),
    ]);

    return _AuthoritativeStateCandidate(
      user: currentUser,
      summary: freshSummary,
      cardPaymentStatus: freshCardPaymentStatus,
      judgment: freshJudgment,
      entries: List.unmodifiable(freshEntries),
      confirmedPlannedEntries: List.unmodifiable(freshConfirmedPlannedEntries),
      panels: List.unmodifiable(freshPanels),
      cashFlows: List.unmodifiable(freshCashFlows),
      settings: freshSettings,
      monthCloseStatus: freshMonthCloseStatus,
      ownerDiscountMonth: discountResults[0] as CardDiscountMonth,
      familyDiscountMonth: discountResults[1] as CardDiscountMonth,
      transitDiscountProfile:
          discountResults[2] as TransitDiscountProfileStatus,
    );
  }

  Future<_AuthoritativeBaselineEnvelope>
      _readAuthoritativeBaselineEnvelope() async {
    final authoritative = await api.offlineReconciliationBaseline();
    final snapshot = authoritative['snapshot'];
    final fingerprint = authoritative['state_fingerprint'];
    final revision = authoritative['state_revision'];
    final evaluationDate = authoritative['evaluation_date'];
    final rawDefaults = authoritative['discount_policy_defaults'];
    if (snapshot is! Map<String, dynamic> ||
        fingerprint is! String ||
        !RegExp(r'^[0-9a-f]{64}$').hasMatch(fingerprint) ||
        revision is! int ||
        revision < 0 ||
        evaluationDate is! String ||
        DateTime.tryParse(evaluationDate) == null ||
        rawDefaults is! Map ||
        !{'enabled', 'disabled'}.contains(rawDefaults['owner']) ||
        !{'enabled', 'disabled'}.contains(rawDefaults['family'])) {
      throw MoneyNoteApiException('오프라인 기준 Snapshot 응답이 올바르지 않습니다.');
    }
    return _AuthoritativeBaselineEnvelope(
      snapshot: Map<String, dynamic>.unmodifiable(snapshot),
      fingerprint: fingerprint,
      revision: revision,
      evaluationDate: evaluationDate,
      discountPolicyDefaults: Map<String, String>.from(rawDefaults),
    );
  }

  Future<void> resumeFromBackground() async {
    if (!isLoggedIn || isBootstrapping || _isForegroundRefreshRunning) return;
    _isForegroundRefreshRunning = true;
    try {
      if (isOnline) {
        await refresh(notify: false);
        await saveLaunchSnapshot();
        statusMessage = '앱 복귀 동기화 완료';
      } else {
        await checkServerRecovery(notify: false);
        if (isOffline) statusMessage = '오프라인 모드를 유지합니다.';
      }
      await consumeLaunchTarget(notify: false);
    } catch (error) {
      statusMessage =
          error is MoneyNoteApiException ? error.message : error.toString();
    } finally {
      _isForegroundRefreshRunning = false;
      notifyListeners();
    }
  }

  Future<void> refreshInputArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<void> refreshCashArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<List<CashFlow>> _loadRecentCashFlows(MonthCloseStatus status) {
    final serverDate = DateTime.tryParse(status.calendarDate);
    if (serverDate == null) {
      throw MoneyNoteApiException('서버 기준 날짜를 확인할 수 없습니다.');
    }
    final dateFrom = DateTime(serverDate.year, serverDate.month - 1, 1);
    final dateTo = DateTime(serverDate.year, serverDate.month + 1, 0);
    return api.cashFlows(
      dateFrom: _formatDate(dateFrom),
      dateTo: _formatDate(dateTo),
    );
  }

  Future<void> refreshEntriesArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<void> refreshSettlementArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<void> refreshPanelManagementArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<void> refreshPlannedManagementArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  Future<void> refreshSettingsArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshAuthoritativeState(notify: notify);
  }

  String _monthFor(
    MonthCloseStatus status,
    List<LedgerEntry> freshEntries,
    List<MonthlyPanel> freshPanels,
  ) {
    if (status.calendarMonth.length >= 7) {
      return status.calendarMonth.substring(0, 7);
    }
    for (final entry in freshEntries.reversed) {
      final date = entry.entryDate;
      if (date != null && date.length >= 7) return date.substring(0, 7);
    }
    if (freshPanels.isNotEmpty) return freshPanels.last.month;
    return _localToday().substring(0, 7);
  }

  void _requestOfflinePrompt() {
    if (!isOnline) return;
    networkUnavailable = true;
    serverFailurePromptPending = true;
    notifyListeners();
  }

  Future<bool> enterOfflineMode() async {
    if (!isOnline) {
      offlineEntryMessage = '현재 조정 또는 복구 상태에서는 오프라인 모드로 전환할 수 없습니다.';
      notifyListeners();
      return false;
    }
    try {
      return await _withLineageLock(() async {
        if (!isOnline) return false;
        final baseline = await offlineStore.loadBaseline();
        if (baseline == null) {
          offlineEntryMessage = '온라인 상태에서 한 번 동기화가 필요합니다.';
          notifyListeners();
          return false;
        }
        if (!baseline.supportsAtomicReconciliation) {
          offlineEntryMessage = '안전한 오프라인 기준 데이터를 만들려면 온라인에서 다시 동기화하세요.';
          notifyListeners();
          return false;
        }
        final journal = await offlineStore.loadJournal();
        if (journal.isNotEmpty) {
          throw const OfflinePersistenceException(
            '기존 오프라인 기록이 남아 있어 새 epoch를 시작할 수 없습니다.',
          );
        }
        final metadata = OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          baselineLineageFingerprint:
              offlineStore.recoveryLineageFingerprint(baseline),
        );
        await offlineStore.saveMetadata(metadata);
        _offlineMetadata = metadata;
        _offlineBaseline = baseline;
        offlineJournal = journal;
        connectivityMode = ConnectivityMode.offline;
        reconciliationChoice = null;
        _lineageGeneration += 1;
        serverFailurePromptPending = false;
        networkUnavailable = false;
        offlineEntryMessage = '';
        _restoreOfflineProjection(baseline);
        statusMessage = '오프라인 모드로 전환했습니다.';
        notifyListeners();
        return true;
      });
    } on OfflinePersistenceException catch (error) {
      offlineEntryMessage = error.message;
      notifyListeners();
      return false;
    }
  }

  Future<void> checkServerRecovery({bool notify = true}) async {
    if (isPersistenceRecoveryBlocked) {
      statusMessage = '오프라인 저장소 복구가 필요합니다. 앱에서 금융 작업을 진행할 수 없습니다.';
      if (notify) notifyListeners();
      return;
    }
    if (isOnline) return;
    if (isReconciliationFinalizing) {
      await resumeReconciliationFinalization(notify: notify);
      return;
    }
    try {
      await api.health();
      if (isOffline) {
        const metadata = OfflineWorkspaceMetadata(
          mode: ConnectivityMode.reconciliationRequired,
        );
        await _saveOfflineMetadata(metadata);
        statusMessage = '서버 연결이 복구되어 조정이 필요합니다.';
      } else {
        statusMessage = '서버 연결을 확인했습니다. 조정을 완료해야 합니다.';
      }
    } on MoneyNoteConnectionException {
      if (isOffline) statusMessage = '서버에 연결할 수 없어 오프라인 모드를 유지합니다.';
    } catch (error) {
      statusMessage = error.toString();
    }
    if (notify) notifyListeners();
  }

  Future<void> selectReconciliationChoice(ReconciliationChoice choice) async {
    if (isBusy) return;
    isBusy = true;
    notifyListeners();
    try {
      await _prepareReconciliation(choice);
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> _prepareReconciliation(ReconciliationChoice choice) async {
    if (!isReconciliationRequired) return;
    final baseline = _offlineBaseline;
    if (baseline == null) {
      statusMessage = '보존할 오프라인 기준 데이터가 없어 조정을 시작할 수 없습니다.';
      notifyListeners();
      return;
    }
    if (choice == ReconciliationChoice.applyToServer &&
        !baseline.supportsAtomicReconciliation) {
      statusMessage =
          '이 오프라인 작업은 Phase 2 이전 기준으로 시작되어 Mobile Wins를 안전하게 실행할 수 없습니다. Server Wins로 recovery bundle을 보존할 수 있습니다.';
      notifyListeners();
      return;
    }
    final fingerprint = baseline.serverStateFingerprint ??
        offlineStore.recoveryLineageFingerprint(baseline);

    final reconciliationId = _offlineMetadata.reconciliationChoice == choice
        ? _offlineMetadata.reconciliationId ??
            offlineStore.newReconciliationId()
        : offlineStore.newReconciliationId();
    final preparing = OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationRequired,
      reconciliationChoice: choice,
      reconciliationId: reconciliationId,
      phase: ReconciliationPhase.preparing,
    );
    await _saveOfflineMetadata(preparing);
    statusMessage = '조정 전 복구 지점을 준비하고 있습니다.';
    notifyListeners();

    try {
      final serverRecovery = await api.createOfflineServerRecovery(
        reconciliationId: reconciliationId,
        baselineFingerprint: fingerprint,
      );
      final currentFingerprint = serverRecovery['current_server_fingerprint'];
      final serverFilename = serverRecovery['server_artifact_filename'];
      if (currentFingerprint is! String ||
          !RegExp(r'^[0-9a-f]{64}$').hasMatch(currentFingerprint) ||
          serverFilename is! String ||
          serverFilename.isEmpty) {
        throw MoneyNoteApiException('서버 recovery artifact 응답이 올바르지 않습니다.');
      }
      final withServerRecovery = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
        reconciliationChoice: choice,
        reconciliationId: reconciliationId,
        phase: ReconciliationPhase.preparing,
        serverChanged: serverRecovery['server_changed'] == true ||
            !baseline.supportsAtomicReconciliation,
        currentServerFingerprint: currentFingerprint,
        serverArtifactFilename: serverFilename,
      );
      await _saveOfflineMetadata(withServerRecovery);

      final mobileRecovery = await offlineStore.createMobileRecoveryArtifact(
        baseline: baseline,
        operations: offlineJournal,
        metadata: withServerRecovery,
      );
      final ready = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
        reconciliationChoice: choice,
        reconciliationId: reconciliationId,
        phase: ReconciliationPhase.ready,
        serverChanged: withServerRecovery.serverChanged,
        currentServerFingerprint: currentFingerprint,
        serverArtifactFilename: serverFilename,
        mobileArtifactFilename: mobileRecovery.filename,
        mobileArtifactSha256: mobileRecovery.sha256,
      );
      await _saveOfflineMetadata(ready);
      statusMessage = ready.serverChanged
          ? '오프라인 모드 시작 이후 서버 데이터도 변경되었습니다. 최종 실행에는 추가 확인이 필요합니다.'
          : '양쪽 recovery point가 검증되었습니다. 최종 실행 확인이 필요합니다.';
    } catch (error) {
      statusMessage = error is MoneyNoteApiException
          ? error.message
          : 'recovery point 준비에 실패했습니다: $error';
    }
    notifyListeners();
  }

  Future<OfflineReconciliationBundle?> loadReconciliationBundle() {
    return offlineStore.loadReconciliationBundle();
  }

  Future<bool> reconcileMobileWins({
    required String password,
    bool confirmServerChanged = false,
  }) async {
    if (isBusy) return false;
    isBusy = true;
    notifyListeners();
    try {
      return await _reconcileMobileWins(
        password: password,
        confirmServerChanged: confirmServerChanged,
      );
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<bool> _reconcileMobileWins({
    required String password,
    bool confirmServerChanged = false,
  }) async {
    final metadata = _offlineMetadata;
    if (!isReconciliationRequired ||
        metadata.reconciliationChoice != ReconciliationChoice.applyToServer ||
        metadata.phase != ReconciliationPhase.ready ||
        !metadata.hasVerifiedRecoveryPoints) {
      statusMessage = '양쪽 recovery point를 먼저 준비하고 검증해야 합니다.';
      notifyListeners();
      return false;
    }
    if (metadata.serverChanged && !confirmServerChanged) {
      statusMessage = '서버 데이터 변경을 확인한 뒤 Mobile Wins를 다시 실행하세요.';
      notifyListeners();
      return false;
    }
    final baseline = _offlineBaseline;
    if (baseline == null) {
      statusMessage = '오프라인 기준 데이터가 없어 Mobile Wins를 실행할 수 없습니다.';
      notifyListeners();
      return false;
    }
    try {
      final verified = await offlineStore.verifyMobileRecoveryArtifact(
        metadata.mobileArtifactFilename!,
        expectedReconciliationId: metadata.reconciliationId,
        expectedBaseline: baseline,
        expectedOperations: offlineJournal,
      );
      if (verified != metadata.mobileArtifactSha256) {
        statusMessage = 'mobile recovery artifact 검증 결과가 일치하지 않습니다.';
        notifyListeners();
        return false;
      }
    } on OfflinePersistenceException catch (error) {
      statusMessage = error.message;
      notifyListeners();
      return false;
    }
    final pending = OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationFinalizing,
      reconciliationChoice: metadata.reconciliationChoice,
      reconciliationId: metadata.reconciliationId,
      phase: ReconciliationPhase.mobileRequestPending,
      serverCommitStatus: ServerCommitStatus.unknown,
      serverChanged: metadata.serverChanged,
      currentServerFingerprint: metadata.currentServerFingerprint,
      serverArtifactFilename: metadata.serverArtifactFilename,
      mobileArtifactFilename: metadata.mobileArtifactFilename,
      mobileArtifactSha256: metadata.mobileArtifactSha256,
      confirmServerChanged: confirmServerChanged,
    );
    await _saveOfflineMetadata(pending);
    statusMessage = 'Mobile Wins commit 결과를 확인하고 있습니다.';
    notifyListeners();
    return _submitMobileWins(password);
  }

  Future<bool> _submitMobileWins(String password) async {
    final metadata = _offlineMetadata;
    final baseline = _offlineBaseline;
    final reconciliationId = metadata.reconciliationId;
    final baselineFingerprint = baseline?.serverStateFingerprint;
    final snapshot = baseline?.authoritativeSnapshot;
    final currentFingerprint = metadata.currentServerFingerprint;
    final mobileSha = metadata.mobileArtifactSha256;
    if (baseline == null ||
        reconciliationId == null ||
        baselineFingerprint == null ||
        snapshot == null ||
        currentFingerprint == null ||
        mobileSha == null) {
      statusMessage = 'Mobile Wins 복구 정보가 불완전합니다.';
      notifyListeners();
      return false;
    }

    try {
      final result = await api.reconcileOfflineMobileWins(
        reconciliationId: reconciliationId,
        baselineFingerprint: baselineFingerprint,
        baselineSnapshot: snapshot,
        operations:
            offlineJournal.map((operation) => operation.toJson()).toList(),
        mobileArtifactSha256: mobileSha,
        expectedServerFingerprint: currentFingerprint,
        confirmServerChanged: metadata.confirmServerChanged,
        password: password,
      );
      if (result['status'] != 'committed' ||
          result['reconciliation_id'] != reconciliationId) {
        throw MoneyNoteApiException(
          '서버가 committed reconciliation 결과를 반환하지 않았습니다.',
        );
      }
      await _markMobileCommitConfirmed();
      return await _finalizeCommittedMobileWins();
    } on MoneyNoteConnectionException {
      statusMessage =
          '서버 응답을 받지 못했습니다. 동일 reconciliation ID로 commit 여부를 확인합니다.';
      notifyListeners();
      return false;
    } on MoneyNoteApiException catch (error) {
      final conflict = error.code == 'server_state_changed';
      final reportedFingerprint = error.details['current_server_fingerprint'];
      final ready = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
        reconciliationChoice: ReconciliationChoice.applyToServer,
        reconciliationId: reconciliationId,
        phase: ReconciliationPhase.ready,
        serverCommitStatus: ServerCommitStatus.none,
        serverChanged: conflict || metadata.serverChanged,
        currentServerFingerprint: reportedFingerprint is String
            ? reportedFingerprint
            : currentFingerprint,
        serverArtifactFilename: metadata.serverArtifactFilename,
        mobileArtifactFilename: metadata.mobileArtifactFilename,
        mobileArtifactSha256: metadata.mobileArtifactSha256,
      );
      await _saveOfflineMetadata(ready);
      statusMessage = conflict
          ? '오프라인 모드 시작 이후 서버 데이터도 변경되었습니다. 추가 확인 후 다시 실행하세요.'
          : error.message;
      notifyListeners();
      return false;
    }
  }

  Future<bool> reconcileServerWins() async {
    if (isBusy) return false;
    isBusy = true;
    notifyListeners();
    try {
      return await _reconcileServerWins();
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<bool> _reconcileServerWins() async {
    final metadata = _offlineMetadata;
    if (!isReconciliationRequired ||
        metadata.reconciliationChoice !=
            ReconciliationChoice.discardAndUseServer ||
        metadata.phase != ReconciliationPhase.ready ||
        !metadata.hasVerifiedRecoveryPoints) {
      statusMessage = '양쪽 recovery point를 먼저 준비하고 검증해야 합니다.';
      notifyListeners();
      return false;
    }
    final baseline = _offlineBaseline;
    if (baseline == null) {
      statusMessage = '오프라인 기준 데이터가 없어 Server Wins를 실행할 수 없습니다.';
      notifyListeners();
      return false;
    }
    try {
      final verified = await offlineStore.verifyMobileRecoveryArtifact(
        metadata.mobileArtifactFilename!,
        expectedReconciliationId: metadata.reconciliationId,
        expectedBaseline: baseline,
        expectedOperations: offlineJournal,
      );
      if (verified != metadata.mobileArtifactSha256) {
        statusMessage = 'mobile recovery artifact 검증 결과가 일치하지 않습니다.';
        notifyListeners();
        return false;
      }
    } on OfflinePersistenceException catch (error) {
      statusMessage = error.message;
      notifyListeners();
      return false;
    }
    final finalizing = OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationFinalizing,
      reconciliationChoice: metadata.reconciliationChoice,
      reconciliationId: metadata.reconciliationId,
      phase: ReconciliationPhase.serverWinsFinalizing,
      serverChanged: metadata.serverChanged,
      currentServerFingerprint: metadata.currentServerFingerprint,
      serverArtifactFilename: metadata.serverArtifactFilename,
      mobileArtifactFilename: metadata.mobileArtifactFilename,
      mobileArtifactSha256: metadata.mobileArtifactSha256,
    );
    await _saveOfflineMetadata(finalizing);
    return _finalizeServerWins();
  }

  Future<bool> resumeReconciliationFinalization({
    String? password,
    bool notify = true,
  }) async {
    if (isBusy) return false;
    isBusy = true;
    if (notify) notifyListeners();
    try {
      return await _resumeReconciliationFinalization(
        password: password,
        notify: notify,
      );
    } finally {
      isBusy = false;
      if (notify) notifyListeners();
    }
  }

  Future<bool> _resumeReconciliationFinalization({
    String? password,
    bool notify = true,
  }) async {
    if (!isReconciliationFinalizing) return false;
    try {
      await api.health();
      if (_offlineMetadata.phase == ReconciliationPhase.serverWinsFinalizing) {
        return await _finalizeServerWins(notify: notify);
      }
      if (_offlineMetadata.serverCommitStatus == ServerCommitStatus.committed) {
        return await _finalizeCommittedMobileWins(notify: notify);
      }

      final baselineFingerprint = _offlineBaseline?.serverStateFingerprint;
      final reconciliationId = _offlineMetadata.reconciliationId;
      if (baselineFingerprint == null || reconciliationId == null) {
        statusMessage = 'reconciliation status를 확인할 identity가 없습니다.';
        if (notify) notifyListeners();
        return false;
      }
      final status = await api.offlineReconciliationStatus(
        baselineFingerprint: baselineFingerprint,
        reconciliationId: reconciliationId,
      );
      final reconciliation = status['reconciliation'];
      if (reconciliation is Map && reconciliation['status'] == 'committed') {
        await _markMobileCommitConfirmed();
        return await _finalizeCommittedMobileWins(notify: notify);
      }
      if (password != null && password.isNotEmpty) {
        return await _submitMobileWins(password);
      }
      statusMessage =
          '서버 commit은 아직 확인되지 않았습니다. 같은 Mobile Wins를 재시도하려면 비밀번호를 입력하세요.';
    } on MoneyNoteConnectionException {
      statusMessage = '서버 commit 여부 확인을 기다리는 중입니다.';
    } catch (error) {
      statusMessage =
          error is MoneyNoteApiException ? error.message : error.toString();
    }
    if (notify) notifyListeners();
    return false;
  }

  Future<void> _markMobileCommitConfirmed() async {
    final metadata = _offlineMetadata;
    await _saveOfflineMetadata(OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationFinalizing,
      reconciliationChoice: ReconciliationChoice.applyToServer,
      reconciliationId: metadata.reconciliationId,
      phase: ReconciliationPhase.mobileCommitted,
      serverCommitStatus: ServerCommitStatus.committed,
      serverChanged: metadata.serverChanged,
      currentServerFingerprint: metadata.currentServerFingerprint,
      serverArtifactFilename: metadata.serverArtifactFilename,
      mobileArtifactFilename: metadata.mobileArtifactFilename,
      mobileArtifactSha256: metadata.mobileArtifactSha256,
      confirmServerChanged: metadata.confirmServerChanged,
    ));
  }

  Future<bool> _finalizeCommittedMobileWins({bool notify = true}) async {
    try {
      await _refreshAuthoritativeState(
        notify: false,
        allowBaselineWhileFinalizing: true,
      );
      await _completeLocalReconciliation();
      statusMessage = 'Mobile Wins 조정과 최신 상태 동기화를 완료했습니다.';
      if (notify) notifyListeners();
      return true;
    } catch (error) {
      final baseline = _offlineBaseline;
      if (baseline != null) {
        if (_journalWasResolvedByBaseline(baseline)) {
          _restoreAuthoritativeBaseline(baseline);
        } else {
          _restoreOfflineProjection(baseline);
        }
      }
      statusMessage = '서버 반영은 완료되었지만 최신 상태 동기화를 기다리는 중입니다.';
      if (notify) notifyListeners();
      return false;
    }
  }

  Future<bool> _finalizeServerWins({bool notify = true}) async {
    try {
      await _refreshAuthoritativeState(
        notify: false,
        allowBaselineWhileFinalizing: true,
      );
      await _completeLocalReconciliation();
      statusMessage = 'Server Wins 조정과 최신 상태 동기화를 완료했습니다.';
      if (notify) notifyListeners();
      return true;
    } catch (error) {
      final baseline = _offlineBaseline;
      if (baseline != null) {
        if (_journalWasResolvedByBaseline(baseline)) {
          _restoreAuthoritativeBaseline(baseline);
        } else {
          _restoreOfflineProjection(baseline);
        }
      }
      statusMessage = '서버 상태를 가져오지 못해 기존 오프라인 상태를 보존했습니다.';
      if (notify) notifyListeners();
      return false;
    }
  }

  Future<void> _completeLocalReconciliation() async {
    await offlineStore.deleteJournal();
    const online = OfflineWorkspaceMetadata(mode: ConnectivityMode.online);
    await offlineStore.saveMetadata(online);
    _offlineMetadata = online;
    offlineJournal = const [];
    connectivityMode = ConnectivityMode.online;
    reconciliationChoice = null;
    _lineageGeneration += 1;
    networkUnavailable = false;
    serverFailurePromptPending = false;
    usesConservativeCardEstimate = false;
  }

  Future<void> _saveOfflineMetadata(OfflineWorkspaceMetadata metadata) async {
    final lineage = _offlineMetadata.baselineLineageFingerprint ??
        (_offlineBaseline == null
            ? null
            : offlineStore.recoveryLineageFingerprint(_offlineBaseline!));
    final persisted = metadata.mode == ConnectivityMode.online
        ? metadata
        : OfflineWorkspaceMetadata.fromJson({
            ...metadata.toJson(),
            'baseline_lineage_fingerprint': lineage,
          });
    await offlineStore.saveMetadata(persisted);
    _offlineMetadata = persisted;
    connectivityMode = persisted.mode;
    reconciliationChoice = persisted.reconciliationChoice;
    _lineageGeneration += 1;
  }

  bool _journalWasResolvedByBaseline(OfflineBaseline baseline) {
    final resolvedId = baseline.resolvedReconciliationId;
    return resolvedId != null &&
        resolvedId == _offlineMetadata.reconciliationId &&
        (_offlineMetadata.serverCommitStatus == ServerCommitStatus.committed ||
            _offlineMetadata.phase == ReconciliationPhase.serverWinsFinalizing);
  }

  void _restoreAuthoritativeBaseline(OfflineBaseline baseline) {
    user = baseline.user;
    summary = baseline.summary;
    cardPaymentStatus = baseline.cardPaymentStatus;
    judgment = baseline.judgment;
    monthCloseStatus = baseline.monthCloseStatus;
    settings = baseline.settings;
    ownerDiscountMonth = baseline.ownerDiscountMonth;
    familyDiscountMonth = baseline.familyDiscountMonth;
    transitDiscountProfile = baseline.transitDiscountProfile;
    entries = List.from(baseline.entries);
    confirmedPlannedEntries = List.from(baseline.confirmedPlannedEntries);
    panels = List.from(baseline.panels);
    cashFlows = List.from(baseline.cashFlows);
    lastSuccessfulSyncAt = baseline.syncedAt;
    usesConservativeCardEstimate = false;
  }

  void _restoreOfflineProjection(OfflineBaseline baseline) {
    final projection = OfflineProjection.from(baseline, offlineJournal);
    user = baseline.user;
    summary = projection.summary;
    cardPaymentStatus = baseline.cardPaymentStatus;
    judgment = baseline.judgment;
    monthCloseStatus = baseline.monthCloseStatus;
    settings = baseline.settings;
    ownerDiscountMonth = baseline.ownerDiscountMonth;
    familyDiscountMonth = baseline.familyDiscountMonth;
    transitDiscountProfile = baseline.transitDiscountProfile;
    entries = List.from(projection.entries);
    confirmedPlannedEntries = List.from(projection.confirmedPlannedEntries);
    panels = List.from(projection.panels);
    cashFlows = List.from(projection.cashFlows);
    lastSuccessfulSyncAt = baseline.syncedAt;
    usesConservativeCardEstimate = projection.usesConservativeCardEstimate;
  }

  Future<void> _appendOfflineOperation(
    OfflineOperationType type,
    Map<String, dynamic> payload,
  ) async {
    if (!isOffline) {
      throw MoneyNoteApiException('오프라인 기록을 추가할 수 없는 상태입니다.');
    }
    final operation =
        await offlineStore.appendOperation(type: type, payload: payload);
    if (!offlineJournal
        .any((row) => row.operationId == operation.operationId)) {
      offlineJournal = List.unmodifiable([...offlineJournal, operation]);
    }
    final baseline = _offlineBaseline;
    if (baseline == null) {
      throw MoneyNoteApiException('오프라인 기준 데이터가 없습니다.');
    }
    _restoreOfflineProjection(baseline);
  }

  void _requireOnline(String operation) {
    if (isOnline) return;
    if (isReconciliationRequired) {
      throw MoneyNoteApiException('서버 조정을 완료하기 전에는 쓸 수 없습니다.');
    }
    throw MoneyNoteApiException('$operation은 온라인에서만 사용할 수 있습니다.');
  }

  Future<void> refreshNotificationPermissions({bool notify = true}) async {
    notificationPermissions = await notificationBridge.permissionStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshNotificationInboxState({bool notify = true}) async {
    notificationCandidateCounts = await notificationBridge.candidateCounts();
    if (notify) notifyListeners();
  }

  Future<void> consumeLaunchTarget({bool notify = true}) async {
    final target = await notificationBridge.consumeLaunchTarget();
    if (target == 'notification_import') {
      notificationImportOpenGeneration += 1;
    } else if (target?.startsWith('notification_archive:') == true) {
      notificationArchiveSource =
          target!.substring('notification_archive:'.length);
      notificationArchiveOpenGeneration += 1;
    } else {
      return;
    }
    if (notify) notifyListeners();
  }

  Future<void> _configureNotificationCards() async {
    await notificationBridge.configureCards(
      ownerCardLast4: settings.ownerCardLast4,
      familyCardLast4: settings.familyCardLast4,
    );
  }

  Future<void> openNotificationListenerSettings() async {
    await notificationBridge.openSettings();
    await refreshNotificationPermissions();
  }

  Future<void> requestAppNotifications() async {
    await notificationBridge.requestAppNotifications();
    await refreshNotificationPermissions();
  }

  Future<void> openBatteryOptimizationSettings() async {
    await notificationBridge.openBatteryOptimizationSettings();
    await refreshNotificationPermissions();
  }

  Future<bool> createExpense({
    required String usagePlace,
    required String usageItem,
    required int amount,
    required bool discountEnabled,
    int? netAmountOverride,
    String? spendingCategory,
    String? entryDate,
    String? candidateRegistrationKey,
  }) async {
    return _run(() async {
      final resolvedEntryDate =
          entryDate == null || entryDate.isEmpty ? serverToday : entryDate;
      final normalizedCategory = normalizeSpendingCategory(spendingCategory);
      if (netAmountOverride != null &&
          (netAmountOverride < 0 || netAmountOverride > amount)) {
        throw MoneyNoteApiException('실결제액은 0원 이상이고 원금을 초과할 수 없습니다.');
      }
      final discountOverrideAmount =
          netAmountOverride == null ? null : amount - netAmountOverride;
      if (isOffline) {
        final trimmedPlace = usagePlace.trim();
        final trimmedItem = usageItem.trim();
        await _appendOfflineOperation(
          OfflineOperationType.createCardExpense,
          {
            'book_section': 'current',
            'entry_kind': 'expense',
            'entry_date': resolvedEntryDate,
            'title': trimmedItem.isEmpty
                ? trimmedPlace
                : '[$trimmedPlace] $trimmedItem',
            'usage_place': trimmedPlace,
            'usage_item': trimmedItem.isEmpty ? null : trimmedItem,
            'amount_value': amount,
            'spending_category': normalizedCategory,
            'discount_enabled': discountEnabled,
            if (discountOverrideAmount != null)
              'discount_override_amount': discountOverrideAmount,
            if (candidateRegistrationKey != null)
              'candidate_registration_key': candidateRegistrationKey,
          },
        );
        statusMessage = '오프라인 지출을 기기에 보관했습니다.';
        return;
      }
      _requireOnline('카드 사용 기록');
      await api.createExpense(
        date: resolvedEntryDate,
        usagePlace: usagePlace,
        usageItem: usageItem,
        amount: amount,
        discountEnabled: discountEnabled,
        discountOverrideAmount: discountOverrideAmount,
        spendingCategory: normalizedCategory,
        candidateRegistrationKey: candidateRegistrationKey,
      );
      try {
        await refreshInputArea(notify: false);
        statusMessage = '지출 추가 완료';
      } catch (_) {
        statusMessage = '지출은 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
      }
    });
  }

  Future<bool> createPanel({
    required String panelType,
    required String title,
    required int amount,
    bool discountEnabled = true,
    String? spentOn,
    String? candidateRegistrationKey,
  }) async {
    return _run(() async {
      _requireOnline('패널 항목 등록');
      final candidateDate = spentOn?.trim();
      if (candidateRegistrationKey != null &&
          (candidateDate == null ||
              !RegExp(r'^\d{4}-\d{2}-\d{2}$').hasMatch(candidateDate) ||
              DateTime.tryParse(candidateDate) == null)) {
        throw MoneyNoteApiException('알림 후보의 사용일을 확인할 수 없습니다.');
      }
      final panel = await api.createPanel(
        month: candidateRegistrationKey == null
            ? currentMonth
            : candidateDate!.substring(0, 7),
        panelType: panelType,
        title: title,
        amount: amount,
        spentOn: panelType == 'fixed' ? null : spentOn ?? _today(),
        candidateRegistrationKey: candidateRegistrationKey,
        initialDiscountEnabled:
            candidateRegistrationKey == null ? null : discountEnabled,
      );
      if (candidateRegistrationKey != null) {
        try {
          await refreshSettlementArea(notify: false);
          statusMessage = '정산 내역 등록 완료';
        } catch (_) {
          statusMessage = '정산 내역은 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
        }
        return;
      }
      if (!discountEnabled &&
          !panel.isDiscountIneligible &&
          (panelType == 'claim' || panelType == 'family_card')) {
        await api.excludePanelDiscount(panel.id);
      }
      try {
        if (panelType == 'fixed' || panelType == 'frozen') {
          await refreshPanelManagementArea(notify: false);
        } else {
          await refreshSettlementArea(notify: false);
        }
        statusMessage = switch (panelType) {
          'claim' => '청구 추가 완료',
          'family_card' => '가족카드 추가 완료',
          'fixed' => '현금성 고정지출 추가 완료',
          'frozen' => '동결 금액 추가 완료',
          _ => '항목 추가 완료',
        };
      } catch (_) {
        statusMessage = '항목은 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
      }
    });
  }

  Future<bool> createPlannedEntry({
    required int dueDay,
    required String usagePlace,
    required String usageItem,
    required int amount,
  }) async {
    return _run(() async {
      _requireOnline('정기결제 등록');
      await api.createPlannedEntry(
        dueDay: dueDay,
        usagePlace: usagePlace,
        usageItem: usageItem,
        amount: amount,
      );
      try {
        await refreshPlannedManagementArea(notify: false);
        statusMessage = '카드 정기결제 추가 완료';
      } catch (_) {
        statusMessage = '카드 정기결제는 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
      }
    });
  }

  Future<PlannedChargePreview> previewPlannedEntry(
      int entryId, int actualAmount) {
    if (isOffline) {
      return Future.value(PlannedChargePreview(
        amountValue: actualAmount,
        discountPolicy: 'offline_unknown',
        automaticDiscountEligible: false,
        effectiveDiscountAmount: 0,
        effectiveAmountValue: actualAmount,
      ));
    }
    _requireOnline('정기결제 예상 확인');
    return api.previewPlannedEntry(entryId, actualAmount);
  }

  Future<bool> confirmPlannedEntry(
      int entryId, String entryDate, int actualAmount) async {
    return _run(() async {
      if (isOffline) {
        if (!plannedEntries.any((entry) => entry.id == entryId)) {
          throw MoneyNoteApiException('이미 확인했거나 찾을 수 없는 정기결제입니다.');
        }
        if (actualAmount < 0) {
          throw MoneyNoteApiException('카드 정기결제 실제 원금은 0원 이상이어야 합니다.');
        }
        if (!entryDate.startsWith(currentMonth)) {
          throw MoneyNoteApiException('정기결제 등록 날짜는 이번 달 날짜여야 합니다.');
        }
        await _appendOfflineOperation(
          OfflineOperationType.confirmPlannedCardExpense,
          {
            'entry_id': entryId,
            'entry_date': entryDate,
            'actual_amount': actualAmount,
          },
        );
        statusMessage = '오프라인 정기결제 확인을 기기에 보관했습니다.';
        return;
      }
      _requireOnline('정기결제 확인');
      await api.confirmPlannedEntry(entryId, entryDate, actualAmount);
      try {
        await refreshPlannedManagementArea(notify: false);
        statusMessage = '카드 정기결제 확인 완료';
      } catch (_) {
        statusMessage = '정기결제 확인은 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
      }
    });
  }

  Future<void> deletePlannedEntry(int entryId) async {
    await _run(() async {
      _requireOnline('정기결제 삭제');
      await api.deletePlannedEntry(entryId);
      await refreshPlannedManagementArea(notify: false);
      statusMessage = '카드 정기결제 삭제 완료';
    });
  }

  Future<void> excludeExistingEntryDiscount(String entryPaymentKey) async {
    await _run(() async {
      _requireOnline('할인 변경');
      await api.excludeEntryDiscount(entryPaymentKey);
      await refreshEntriesArea(notify: false);
      statusMessage = '할인 제외 완료';
    });
  }

  Future<void> applyDefaultEntryDiscount(String entryPaymentKey) async {
    await _run(() async {
      _requireOnline('할인 변경');
      await api.clearEntryDiscount(entryPaymentKey);
      await refreshEntriesArea(notify: false);
      statusMessage = '할인 적용 완료';
    });
  }

  Future<void> updateEntryNetAmount(LedgerEntry entry, int netAmount) async {
    final paymentKey = entry.paymentKey;
    final amount = entry.amountValue;
    if (paymentKey == null || paymentKey.isEmpty || amount == null) return;
    await _run(() async {
      _requireOnline('실결제액 변경');
      await api.updateEntryDiscount(paymentKey, amount - netAmount);
      await refreshEntriesArea(notify: false);
      statusMessage = '실결제액 수정 완료';
    });
  }

  Future<void> updateExpenseCategory(int entryId, String? category) async {
    await _run(() async {
      _requireOnline('지출 분류 변경');
      await api.updateEntryCategory(
          entryId, normalizeSpendingCategory(category));
      await refreshEntriesArea(notify: false);
      statusMessage = '분류 변경 완료';
    });
  }

  Future<void> deleteExpense(int entryId) async {
    await _run(() async {
      _requireOnline('지출 삭제');
      await api.deleteEntry(entryId);
      await refreshEntriesArea(notify: false);
      statusMessage = '지출 삭제 완료';
    });
  }

  Future<void> deletePanel(int panelId) async {
    await _run(() async {
      _requireOnline('패널 항목 삭제');
      await api.deletePanel(panelId);
      await refreshPanelManagementArea(notify: false);
      statusMessage = '항목 삭제 완료';
    });
  }

  Future<bool> confirmFixedPanel(
      int panelId, String occurredOn, int actualAmount) async {
    return _run(() async {
      if (isOffline) {
        if (actualAmount < 0) {
          throw MoneyNoteApiException('현금성 고정지출 실제 출금액은 0원 이상이어야 합니다.');
        }
        final matching = panels.where((panel) => panel.id == panelId).toList();
        if (matching.length != 1 ||
            matching.single.panelType != 'fixed' ||
            matching.single.confirmedCashFlowId != null) {
          throw MoneyNoteApiException('이미 확인했거나 찾을 수 없는 현금성 고정지출입니다.');
        }
        if (occurredOn.compareTo(_localToday()) > 0) {
          throw MoneyNoteApiException('미래 날짜의 고정지출은 확인할 수 없습니다.');
        }
        await _appendOfflineOperation(
          OfflineOperationType.confirmFixedExpense,
          {
            'panel_id': panelId,
            'occurred_on': occurredOn,
            'actual_amount': actualAmount,
          },
        );
        statusMessage = '오프라인 고정지출 확인을 기기에 보관했습니다.';
        return;
      }
      _requireOnline('현금성 고정지출 확인');
      await api.confirmFixedPanel(panelId, occurredOn, actualAmount);
      try {
        await refreshPanelManagementArea(notify: false);
        statusMessage = '현금성 고정지출 확인 완료';
      } catch (_) {
        statusMessage = '고정지출 확인은 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
      }
    });
  }

  Future<void> cancelFixedPanelConfirmation(int cashFlowId) async {
    await _run(() async {
      _requireOnline('정기지출 확인 취소');
      await api.deleteCashFlow(cashFlowId);
      await refreshPanelManagementArea(notify: false);
      statusMessage = '현금성 고정지출 확인 취소 완료';
    });
  }

  Future<void> excludeExistingPanelDiscount(int panelId) async {
    await _run(() async {
      _requireOnline('패널 할인 변경');
      await api.excludePanelDiscount(panelId);
      await refreshSettlementArea(notify: false);
      statusMessage = '할인 제외 완료';
    });
  }

  Future<void> updatePanelNetAmount(MonthlyPanel panel, int netAmount) async {
    final amount = panel.amountValue;
    if (amount == null) return;
    await _run(() async {
      _requireOnline('패널 실결제액 변경');
      await api.updatePanelDiscount(panel.id, amount - netAmount);
      await refreshSettlementArea(notify: false);
      statusMessage = '실결제액 수정 완료';
    });
  }

  Future<void> applyDefaultPanelDiscount(int panelId) async {
    await _run(() async {
      _requireOnline('패널 할인 변경');
      await api.clearPanelDiscount(panelId);
      await refreshSettlementArea(notify: false);
      statusMessage = '할인 적용 완료';
    });
  }

  Future<void> completePanelType(String panelType) async {
    await _run(() async {
      _requireOnline('정산 일괄 처리');
      await api.completePanelType(panelType);
      await refreshSettlementArea(notify: false);
      statusMessage = panelType == 'claim' ? '청구 처리 완료' : '가족카드 처리 완료';
    });
  }

  Future<void> sharePanel(String panelType) async {
    await SharePlus.instance.share(
      ShareParams(text: api.sharePageUri(panelType).toString()),
    );
  }

  Future<bool> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isIncome,
    required bool isPrimaryIncome,
  }) async {
    return _run(() async {
      final signedAmount = isIncome ? amount : -amount;
      if (isOffline) {
        await _appendOfflineOperation(
          OfflineOperationType.createCashFlow,
          {
            'occurred_on': occurredOn,
            'title': title.trim(),
            'amount_value': signedAmount,
            'is_primary_income': isIncome && isPrimaryIncome ? 1 : 0,
          },
        );
        statusMessage =
            isIncome ? '오프라인 현금 입금을 기기에 보관했습니다.' : '오프라인 현금 출금을 기기에 보관했습니다.';
        return;
      }
      _requireOnline('현금흐름 기록');
      await api.createCashFlow(
        occurredOn: occurredOn,
        title: title,
        amount: signedAmount,
        isPrimaryIncome: isIncome && isPrimaryIncome,
      );
      try {
        await refreshCashArea(notify: false);
        statusMessage = '현금흐름 추가 완료';
      } catch (_) {
        statusMessage = '현금흐름은 저장됐습니다. 최신 화면 동기화는 다시 시도하세요.';
      }
    });
  }

  Future<void> deleteCashFlow(int flowId) async {
    await _run(() async {
      _requireOnline('현금흐름 삭제');
      await api.deleteCashFlow(flowId);
      await refreshCashArea(notify: false);
      statusMessage = '현금흐름 삭제 완료';
    });
  }

  Future<void> saveLaunchSnapshot() async {
    if (!isOnline) return;
    try {
      final snapshot = await api.downloadSnapshot();
      final directory = await _snapshotDirectory();
      final backup = File(
          '${directory.path}/money-note-snapshot-${_timestampForFilename()}.money-note-snapshot.json');
      await backup.writeAsBytes(snapshot.bytes, flush: true);
      await _pruneLocalSnapshots();
      localSnapshots = await listLocalSnapshots();
    } catch (_) {
      // 자동 백업 실패는 앱 실행을 막지 않는다. 상태 화면의 스냅샷 관리에서 다시 확인한다.
    }
  }

  Future<void> shareCurrentSnapshot() async {
    await _run(() async {
      var snapshots = await listLocalSnapshots();
      if (snapshots.isEmpty) {
        await saveLaunchSnapshot();
        snapshots = await listLocalSnapshots();
      }
      if (snapshots.isEmpty) {
        throw MoneyNoteApiException('공유할 스냅샷이 없습니다.');
      }
      snapshots.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
      final current = await _safeSnapshotFile(snapshots.first.filename);
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile(current.path,
                mimeType: 'application/json', name: snapshots.first.filename)
          ],
          text: 'Money-Note 스냅샷 백업',
        ),
      );
      localSnapshots = await listLocalSnapshots();
      statusMessage = '스냅샷 공유 준비 완료';
    });
  }

  Future<void> shareLocalSnapshot(String filename) async {
    await _run(() async {
      final snapshot = await _safeSnapshotFile(filename);
      await SharePlus.instance.share(
        ShareParams(
          files: [
            XFile(snapshot.path,
                mimeType: 'application/json',
                name: 'money-note-snapshot-${_timestampForFilename()}.json')
          ],
          text: 'Money-Note 스냅샷 백업',
        ),
      );
      statusMessage = '스냅샷 공유 준비 완료';
    });
  }

  Future<void> restoreLocalSnapshot({
    required String filename,
    required String password,
  }) async {
    await _run(() async {
      _requireOnline('스냅샷 복원');
      final snapshot = await _safeSnapshotFile(filename);
      await api.restoreSnapshot(
        password: password,
        snapshotText: await snapshot.readAsString(),
      );
      await refresh(notify: false);
      statusMessage = '스냅샷 복원 완료';
    });
  }

  Future<void> deleteLocalSnapshot(String filename) async {
    await _run(() async {
      final snapshot = await _safeSnapshotFile(filename);
      if (await snapshot.exists()) {
        await snapshot.delete();
      }
      localSnapshots = await listLocalSnapshots();
      statusMessage = '스냅샷 삭제 완료';
    });
  }

  Future<void> deleteAllLocalSnapshots() async {
    await _run(() async {
      for (final snapshot in await listLocalSnapshots()) {
        final file = await _safeSnapshotFile(snapshot.filename);
        if (await file.exists()) {
          await file.delete();
        }
      }
      localSnapshots = [];
      statusMessage = '스냅샷 전체 삭제 완료';
    });
  }

  Future<List<LocalSnapshotInfo>> listLocalSnapshots() async {
    final directory = await _snapshotDirectory();
    final items = <LocalSnapshotInfo>[];
    final files = directory
        .listSync()
        .whereType<File>()
        .where((file) => file.path.endsWith('.money-note-snapshot.json'))
        .toList();
    for (final file in files) {
      final stat = await file.stat();
      items.add(LocalSnapshotInfo(
        filename: file.uri.pathSegments.last,
        sizeBytes: stat.size,
        updatedAt: stat.modified,
      ));
    }
    items.sort((a, b) => b.updatedAt.compareTo(a.updatedAt));
    return items;
  }

  Future<void> _pruneLocalSnapshots() async {
    final snapshots = await listLocalSnapshots();
    for (final snapshot in snapshots.skip(_maxLocalSnapshots)) {
      final file = await _safeSnapshotFile(snapshot.filename);
      if (await file.exists()) {
        await file.delete();
      }
    }
  }

  Future<void> closeCurrentMonth({
    required String targetMonth,
    bool allowEarlyClose = false,
    bool allowUnconfirmedRecurring = false,
  }) async {
    await _run(() async {
      _requireOnline('월마감');
      final result = await api.closeCurrentMonth(
        targetMonth: targetMonth,
        allowEarlyClose: allowEarlyClose,
        allowUnconfirmedRecurring: allowUnconfirmedRecurring,
      );
      await refresh(notify: false);
      statusMessage = '월마감 완료: ${result['closed_month'] ?? '마감할 월 없음'}';
    });
  }

  Future<void> updateSetting(String key, String value) async {
    await _run(() async {
      _requireOnline('설정 변경');
      await api.updateSetting(key, value);
      await refreshSettingsArea(notify: false);
      statusMessage = '설정 저장 완료';
    });
  }

  Future<bool> updateTransitDiscountProfile(bool followsOwner) {
    return _run(() async {
      _requireOnline('교통카드 할인 설정');
      transitDiscountProfile = await api.updateTransitDiscountProfile(
        currentMonth,
        followsOwner ? 'owner' : 'none',
      );
      await refreshSettingsArea(notify: false);
      statusMessage = followsOwner
          ? '이번 달부터 교통카드가 본인카드 할인 정책을 따릅니다.'
          : '이번 달부터 교통카드 자동 할인을 적용하지 않습니다.';
    });
  }

  Future<T> _withLineageLock<T>(Future<T> Function() action) async {
    final previous = _lineageTail;
    final completed = Completer<void>();
    final current = completed.future;
    _lineageTail = current;
    if (previous != null) await previous;
    try {
      return await action();
    } finally {
      completed.complete();
      if (identical(_lineageTail, current)) _lineageTail = null;
    }
  }

  Future<bool> _run(Future<void> Function() action) async {
    if (isBusy) {
      statusMessage = '이미 저장 중입니다.';
      notifyListeners();
      return false;
    }
    isBusy = true;
    statusMessage = '';
    notifyListeners();
    try {
      await action();
      return true;
    } catch (error) {
      statusMessage =
          error is MoneyNoteApiException ? error.message : error.toString();
      return false;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  String _today() {
    return serverToday;
  }

  String _localToday() {
    final now = DateTime.now();
    return _formatDate(now);
  }

  String _formatDate(DateTime value) {
    return '${value.year.toString().padLeft(4, '0')}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';
  }

  Future<Directory> _snapshotDirectory() async {
    final base = await getApplicationDocumentsDirectory();
    final directory = Directory('${base.path}/snapshots');
    if (!await directory.exists()) {
      await directory.create(recursive: true);
    }
    return directory;
  }

  Future<File> _safeSnapshotFile(String filename) async {
    final allowed = (await listLocalSnapshots())
        .map((snapshot) => snapshot.filename)
        .toSet();
    if (!allowed.contains(filename)) {
      throw MoneyNoteApiException('알 수 없는 스냅샷 파일입니다.');
    }
    final directory = await _snapshotDirectory();
    return File('${directory.path}/$filename');
  }

  String _timestampForFilename() {
    final now = DateTime.now();
    return '${now.year.toString().padLeft(4, '0')}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}-${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}${now.millisecond.toString().padLeft(3, '0')}';
  }
}

class _AuthoritativeBaselineEnvelope {
  const _AuthoritativeBaselineEnvelope({
    required this.snapshot,
    required this.fingerprint,
    required this.revision,
    required this.evaluationDate,
    required this.discountPolicyDefaults,
  });

  final Map<String, dynamic> snapshot;
  final String fingerprint;
  final int revision;
  final String evaluationDate;
  final Map<String, String> discountPolicyDefaults;
}

class _AuthoritativeStateCandidate {
  const _AuthoritativeStateCandidate({
    required this.user,
    required this.summary,
    required this.cardPaymentStatus,
    required this.judgment,
    required this.monthCloseStatus,
    required this.settings,
    required this.ownerDiscountMonth,
    required this.familyDiscountMonth,
    required this.transitDiscountProfile,
    required this.entries,
    required this.confirmedPlannedEntries,
    required this.panels,
    required this.cashFlows,
  });

  final AuthUser user;
  final Summary summary;
  final CardPaymentStatus cardPaymentStatus;
  final JudgmentState judgment;
  final MonthCloseStatus monthCloseStatus;
  final AppSettings settings;
  final CardDiscountMonth ownerDiscountMonth;
  final CardDiscountMonth familyDiscountMonth;
  final TransitDiscountProfileStatus transitDiscountProfile;
  final List<LedgerEntry> entries;
  final List<LedgerEntry> confirmedPlannedEntries;
  final List<MonthlyPanel> panels;
  final List<CashFlow> cashFlows;
}

class LocalSnapshotInfo {
  LocalSnapshotInfo({
    required this.filename,
    required this.sizeBytes,
    required this.updatedAt,
  });

  final String filename;
  final int sizeBytes;
  final DateTime updatedAt;
}
