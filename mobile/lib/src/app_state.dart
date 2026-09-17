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
  DateTime? lastSuccessfulSyncAt;
  List<OfflineJournalOperation> offlineJournal = const [];
  bool serverFailurePromptPending = false;
  String offlineEntryMessage = '';
  bool usesConservativeCardEstimate = false;
  OfflineBaseline? _offlineBaseline;
  bool _isForegroundRefreshRunning = false;
  int notificationImportOpenGeneration = 0;
  int notificationArchiveOpenGeneration = 0;
  String notificationArchiveSource = 'woori_card';

  bool get isLoggedIn => user != null;

  bool get isOnline => connectivityMode == ConnectivityMode.online;
  bool get isOffline => connectivityMode == ConnectivityMode.offline;
  bool get isReconciliationRequired =>
      connectivityMode == ConnectivityMode.reconciliationRequired;
  bool get hasOfflineBaseline => _offlineBaseline != null;
  bool get canUseOnlineWrites => isOnline && !isBusy;
  bool get canCreateCardExpense => (isOnline || isOffline) && !isBusy;
  bool get canCreateCashFlow => (isOnline || isOffline) && !isBusy;
  bool get canConfirmRecurring => (isOnline || isOffline) && !isBusy;
  bool get financialValuesAreEstimated => !isOnline;
  int get pendingOfflineOperationCount => offlineJournal.length;

  String get financialEstimateLabel => usesConservativeCardEstimate
      ? '오프라인 보수적 예상값'
      : '오프라인 예상값';

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
      connectivityMode = metadata.mode;
      reconciliationChoice = metadata.reconciliationChoice;
      _offlineBaseline = await offlineStore.loadBaseline();
      offlineJournal = await offlineStore.loadJournal();
      lastSuccessfulSyncAt = _offlineBaseline?.syncedAt;
    } on OfflinePersistenceException catch (error) {
      connectivityMode = ConnectivityMode.online;
      offlineEntryMessage = error.message;
      if (notify) notifyListeners();
      return false;
    }

    if (isOnline) {
      if (notify) notifyListeners();
      return false;
    }

    final baseline = _offlineBaseline;
    if (baseline == null) {
      connectivityMode = ConnectivityMode.online;
      serverFailurePromptPending = true;
      offlineEntryMessage = '온라인 상태에서 한 번 동기화가 필요합니다.';
      if (notify) notifyListeners();
      return true;
    }
    _restoreOfflineProjection(baseline);
    await checkServerRecovery(notify: false);
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
    await refreshNotificationPermissions(notify: false);
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

    summary = freshSummary;
    cardPaymentStatus = freshCardPaymentStatus;
    judgment = freshJudgment;
    entries = freshEntries;
    confirmedPlannedEntries = freshConfirmedPlannedEntries;
    panels = freshPanels;
    cashFlows = freshCashFlows;
    settings = freshSettings;
    monthCloseStatus = freshMonthCloseStatus;
    ownerDiscountMonth = discountResults[0] as CardDiscountMonth;
    familyDiscountMonth = discountResults[1] as CardDiscountMonth;
    transitDiscountProfile =
        discountResults[2] as TransitDiscountProfileStatus;
    usesConservativeCardEstimate = false;
    await _configureNotificationCards();
    await refreshNotificationInboxState(notify: false);
    await _persistCompleteBaseline();
    if (notify) notifyListeners();
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
    await refreshNotificationPermissions(notify: false);
    await refreshNotificationInboxState(notify: false);
    await _refreshEntriesAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshCashArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    final freshMonthCloseStatus = await api.monthCloseStatus();
    final results = await Future.wait([
      _loadRecentCashFlows(freshMonthCloseStatus),
      api.summary(),
      api.judgment(),
      api.currentPanels(),
    ]);
    cashFlows = results[0] as List<CashFlow>;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    panels = results[3] as List<MonthlyPanel>;
    monthCloseStatus = freshMonthCloseStatus;
    await _persistCompleteBaseline();
    if (notify) notifyListeners();
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
    await refreshNotificationInboxState(notify: false);
    await _refreshEntriesAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshSettlementArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    await _refreshPanelsAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshPanelManagementArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    final freshMonthCloseStatus = await api.monthCloseStatus();
    final results = await Future.wait([
      api.currentPanels(),
      api.summary(),
      api.judgment(),
      _loadRecentCashFlows(freshMonthCloseStatus),
    ]);
    panels = results[0] as List<MonthlyPanel>;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    cashFlows = results[3] as List<CashFlow>;
    monthCloseStatus = freshMonthCloseStatus;
    await _persistCompleteBaseline();
    if (notify) notifyListeners();
  }

  Future<void> refreshPlannedManagementArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    final results = await Future.wait([
      api.currentEntries(),
      api.confirmedPlannedEntries(),
      api.summary(),
      api.judgment(),
    ]);
    entries = results[0] as List<LedgerEntry>;
    confirmedPlannedEntries = results[1] as List<LedgerEntry>;
    summary = results[2] as Summary;
    judgment = results[3] as JudgmentState;
    await _persistCompleteBaseline();
    if (notify) notifyListeners();
  }

  Future<void> refreshSettingsArea({bool notify = true}) async {
    if (!isOnline) {
      await checkServerRecovery(notify: notify);
      return;
    }
    final results = await Future.wait([
      api.settings(),
      api.summary(),
      api.judgment(),
    ]);
    settings = results[0] as AppSettings;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    await _configureNotificationCards();
    await _refreshDiscountMonths();
    await refreshNotificationInboxState(notify: false);
    await _persistCompleteBaseline();
    if (notify) notifyListeners();
  }

  Future<void> _refreshEntriesAndStatus() async {
    final results = await Future.wait([
      api.currentEntries(),
      api.summary(),
      api.currentCardPaymentStatus(),
      api.judgment(),
      api.monthCloseStatus(),
    ]);
    entries = results[0] as List<LedgerEntry>;
    summary = results[1] as Summary;
    cardPaymentStatus = results[2] as CardPaymentStatus;
    judgment = results[3] as JudgmentState;
    monthCloseStatus = results[4] as MonthCloseStatus;
    await _refreshDiscountMonths();
    await _persistCompleteBaseline();
  }

  Future<void> _refreshPanelsAndStatus() async {
    final results = await Future.wait([
      api.currentPanels(),
      api.summary(),
      api.judgment(),
    ]);
    panels = results[0] as List<MonthlyPanel>;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    await _refreshDiscountMonths();
    await _persistCompleteBaseline();
  }

  Future<void> _refreshDiscountMonths() async {
    final month = currentMonth;
    final results = await Future.wait([
      api.discountMonth(month, 'owner'),
      api.discountMonth(month, 'family'),
      api.transitDiscountProfile(month),
    ]);
    ownerDiscountMonth = results[0] as CardDiscountMonth;
    familyDiscountMonth = results[1] as CardDiscountMonth;
    transitDiscountProfile = results[2] as TransitDiscountProfileStatus;
  }

  Future<void> _persistCompleteBaseline() async {
    if (!isOnline) return;
    final currentUser = user;
    final currentSummary = summary;
    final currentCardPaymentStatus = cardPaymentStatus;
    final currentJudgment = judgment;
    final currentMonthCloseStatus = monthCloseStatus;
    final currentOwnerDiscountMonth = ownerDiscountMonth;
    final currentFamilyDiscountMonth = familyDiscountMonth;
    final currentTransitDiscountProfile = transitDiscountProfile;
    if (currentUser == null ||
        currentSummary == null ||
        currentCardPaymentStatus == null ||
        currentJudgment == null ||
        currentMonthCloseStatus == null ||
        currentOwnerDiscountMonth == null ||
        currentFamilyDiscountMonth == null ||
        currentTransitDiscountProfile == null) {
      return;
    }
    final baseline = OfflineBaseline(
      syncedAt: DateTime.now().toUtc(),
      user: currentUser,
      summary: currentSummary,
      cardPaymentStatus: currentCardPaymentStatus,
      judgment: currentJudgment,
      monthCloseStatus: currentMonthCloseStatus,
      settings: settings,
      ownerDiscountMonth: currentOwnerDiscountMonth,
      familyDiscountMonth: currentFamilyDiscountMonth,
      transitDiscountProfile: currentTransitDiscountProfile,
      entries: List.unmodifiable(entries),
      confirmedPlannedEntries: List.unmodifiable(confirmedPlannedEntries),
      panels: List.unmodifiable(panels),
      cashFlows: List.unmodifiable(cashFlows),
    );
    await offlineStore.replaceBaseline(baseline);
    _offlineBaseline = baseline;
    lastSuccessfulSyncAt = baseline.syncedAt;
    offlineEntryMessage = '';
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
    if (isReconciliationRequired) return false;
    try {
      final baseline = await offlineStore.loadBaseline();
      if (baseline == null) {
        offlineEntryMessage = '온라인 상태에서 한 번 동기화가 필요합니다.';
        notifyListeners();
        return false;
      }
      final journal = await offlineStore.loadJournal();
      await offlineStore.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.offline,
      ));
      _offlineBaseline = baseline;
      offlineJournal = journal;
      connectivityMode = ConnectivityMode.offline;
      reconciliationChoice = null;
      serverFailurePromptPending = false;
      networkUnavailable = false;
      offlineEntryMessage = '';
      _restoreOfflineProjection(baseline);
      statusMessage = '오프라인 모드로 전환했습니다.';
      notifyListeners();
      return true;
    } on OfflinePersistenceException catch (error) {
      offlineEntryMessage = error.message;
      notifyListeners();
      return false;
    }
  }

  Future<void> checkServerRecovery({bool notify = true}) async {
    if (isOnline) return;
    try {
      await api.health();
      if (isOffline) {
        await offlineStore.saveMetadata(const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.reconciliationRequired,
        ));
        connectivityMode = ConnectivityMode.reconciliationRequired;
        reconciliationChoice = null;
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

  Future<void> selectReconciliationChoice(
      ReconciliationChoice choice) async {
    if (!isReconciliationRequired) return;
    await offlineStore.saveMetadata(OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationRequired,
      reconciliationChoice: choice,
    ));
    reconciliationChoice = choice;
    statusMessage = choice == ReconciliationChoice.applyToServer
        ? '서버 적용 선택을 저장했습니다. 실제 조정은 Phase 2에서 지원합니다.'
        : '서버 데이터 사용 선택을 저장했습니다. 실제 조정은 Phase 2에서 지원합니다.';
    notifyListeners();
  }

  Future<OfflineReconciliationBundle?> loadReconciliationBundle() {
    return offlineStore.loadReconciliationBundle();
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
    confirmedPlannedEntries =
        List.from(projection.confirmedPlannedEntries);
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
    offlineJournal = List.unmodifiable([...offlineJournal, operation]);
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
    String? spendingCategory,
    String? entryDate,
    String? candidateRegistrationKey,
  }) async {
    return _run(() async {
      final resolvedEntryDate =
          entryDate == null || entryDate.isEmpty ? serverToday : entryDate;
      final normalizedCategory = normalizeSpendingCategory(spendingCategory);
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
            if (candidateRegistrationKey != null)
              'candidate_registration_key': candidateRegistrationKey,
          },
        );
        statusMessage = '오프라인 지출을 기기에 보관했습니다.';
        return;
      }
      _requireOnline('카드 사용 기록');
      final entry = await api.createExpense(
        date: resolvedEntryDate,
        usagePlace: usagePlace,
        usageItem: usageItem,
        amount: amount,
        spendingCategory: normalizedCategory,
        candidateRegistrationKey: candidateRegistrationKey,
      );
      if (candidateRegistrationKey != null) {
        try {
          if (!discountEnabled &&
              !entry.isDiscountIneligible &&
              entry.paymentKey != null) {
            await api.excludeEntryDiscount(entry.paymentKey!);
          }
          await refreshInputArea(notify: false);
          statusMessage = '지출 추가 완료';
        } catch (_) {
          statusMessage = '지출은 저장됐습니다. 화면 갱신 또는 할인 설정을 다시 확인하세요.';
        }
        return;
      }
      if (!discountEnabled &&
          !entry.isDiscountIneligible &&
          entry.paymentKey != null) {
        await api.excludeEntryDiscount(entry.paymentKey!);
      }
      await refreshInputArea(notify: false);
      statusMessage = '지출 추가 완료';
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
      final panel = await api.createPanel(
        month: currentMonth,
        panelType: panelType,
        title: title,
        amount: amount,
        spentOn: panelType == 'fixed' ? null : spentOn ?? _today(),
        candidateRegistrationKey: candidateRegistrationKey,
      );
      if (candidateRegistrationKey != null) {
        try {
          if (!discountEnabled &&
              !panel.isDiscountIneligible &&
              (panelType == 'claim' || panelType == 'family_card')) {
            await api.excludePanelDiscount(panel.id);
          }
          await refreshSettlementArea(notify: false);
          statusMessage = '정산 내역 등록 완료';
        } catch (_) {
          statusMessage = '정산 내역은 저장됐습니다. 화면 갱신 또는 할인 설정을 다시 확인하세요.';
        }
        return;
      }
      if (!discountEnabled &&
          !panel.isDiscountIneligible &&
          (panelType == 'claim' || panelType == 'family_card')) {
        await api.excludePanelDiscount(panel.id);
      }
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
    });
  }

  Future<void> createPlannedEntry({
    required int dueDay,
    required String usagePlace,
    required String usageItem,
    required int amount,
  }) async {
    await _run(() async {
      _requireOnline('정기결제 등록');
      await api.createPlannedEntry(
        dueDay: dueDay,
        usagePlace: usagePlace,
        usageItem: usageItem,
        amount: amount,
      );
      await refreshPlannedManagementArea(notify: false);
      statusMessage = '카드 정기결제 추가 완료';
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

  Future<void> confirmPlannedEntry(
      int entryId, String entryDate, int actualAmount) async {
    await _run(() async {
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
      await refreshPlannedManagementArea(notify: false);
      statusMessage = '카드 정기결제 확인 완료';
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

  Future<void> confirmFixedPanel(
      int panelId, String occurredOn, int actualAmount) async {
    await _run(() async {
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
      await refreshPanelManagementArea(notify: false);
      statusMessage = '현금성 고정지출 확인 완료';
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

  Future<void> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isIncome,
    required bool isPrimaryIncome,
  }) async {
    await _run(() async {
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
        statusMessage = isIncome
            ? '오프라인 현금 입금을 기기에 보관했습니다.'
            : '오프라인 현금 출금을 기기에 보관했습니다.';
        return;
      }
      _requireOnline('현금흐름 기록');
      await api.createCashFlow(
        occurredOn: occurredOn,
        title: title,
        amount: signedAmount,
        isPrimaryIncome: isIncome && isPrimaryIncome,
      );
      await refreshCashArea(notify: false);
      statusMessage = '현금흐름 추가 완료';
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

  Future<bool> _run(Future<void> Function() action) async {
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
