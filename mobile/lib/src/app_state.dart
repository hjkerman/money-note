import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';

import 'api_client.dart';
import 'models.dart';
import 'notification_bridge.dart';

class AppState extends ChangeNotifier {
  AppState(this.api);

  final MoneyNoteApiClient api;
  final NotificationBridge notificationBridge = NotificationBridge();

  bool isBootstrapping = true;
  bool networkUnavailable = false;
  bool isBusy = false;
  String statusMessage = '';
  AuthUser? user;
  Summary? summary;
  JudgmentState? judgment;
  MonthCloseStatus? monthCloseStatus;
  AppSettings settings = AppSettings(values: const {});
  CardDiscountMonth? ownerDiscountMonth;
  CardDiscountMonth? familyDiscountMonth;
  List<LedgerEntry> entries = [];
  List<MonthlyPanel> panels = [];
  List<CashFlow> cashFlows = [];
  List<LocalSnapshotInfo> localSnapshots = [];
  NotificationPermissionStatus notificationPermissions =
      const NotificationPermissionStatus.ready();

  bool get isLoggedIn => user != null;

  String get currentMonth {
    final entryMonth = entries
        .where((entry) => entry.entryDate != null)
        .map((entry) => entry.entryDate!.substring(0, 7))
        .toList();
    if (entryMonth.isNotEmpty) return entryMonth.last;
    final panelMonth = panels.map((panel) => panel.month).toList();
    if (panelMonth.isNotEmpty) return panelMonth.last;
    final serverMonth = monthCloseStatus?.calendarMonth ?? '';
    if (serverMonth.length >= 7) return serverMonth.substring(0, 7);
    final now = DateTime.now();
    return '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}';
  }

  List<LedgerEntry> get expenseEntries {
    final rows =
        entries.where((entry) => entry.entryKind == 'expense').toList();
    rows.sort((a, b) {
      final dateCompare = (b.entryDate ?? '').compareTo(a.entryDate ?? '');
      if (dateCompare != 0) return dateCompare;
      final sortCompare = b.sortOrder.compareTo(a.sortOrder);
      if (sortCompare != 0) return sortCompare;
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

  int panelOriginalTotal(String panelType) {
    return panelsByType(panelType)
        .fold(0, (sum, panel) => sum + (panel.amountValue ?? 0));
  }

  int panelEffectiveTotal(String panelType) {
    return panelsByType(panelType)
        .fold(0, (sum, panel) => sum + panel.effectiveAmount);
  }

  Future<void> bootstrap() async {
    await refreshNotificationPermissions(notify: false);
    try {
      await api.health();
      networkUnavailable = false;
    } catch (_) {
      networkUnavailable = true;
      isBootstrapping = false;
      notifyListeners();
      return;
    }
    await api.loadSession();
    try {
      user = await api.me();
      await refresh();
      await saveLaunchSnapshot();
    } catch (_) {
      user = null;
    } finally {
      isBootstrapping = false;
      notifyListeners();
    }
  }

  Future<void> login(String username, String password) async {
    await _run(() async {
      await api.health();
      networkUnavailable = false;
      user = await api.login(username, password);
      await refresh(notify: false);
      await saveLaunchSnapshot();
      statusMessage = '로그인 완료';
    });
  }

  Future<void> logout() async {
    await _run(() async {
      await api.logout();
      user = null;
      summary = null;
      judgment = null;
      monthCloseStatus = null;
      entries = [];
      panels = [];
      cashFlows = [];
      statusMessage = '로그아웃 완료';
    });
  }

  Future<void> refresh({bool notify = true}) async {
    await refreshNotificationPermissions(notify: false);
    final results = await Future.wait([
      api.summary(),
      api.judgment(),
      api.currentEntries(),
      api.currentPanels(),
      api.cashFlows(),
      api.settings(),
      api.monthCloseStatus(),
    ]);
    summary = results[0] as Summary;
    judgment = results[1] as JudgmentState;
    entries = results[2] as List<LedgerEntry>;
    panels = results[3] as List<MonthlyPanel>;
    cashFlows = results[4] as List<CashFlow>;
    settings = results[5] as AppSettings;
    monthCloseStatus = results[6] as MonthCloseStatus;
    ownerDiscountMonth = await api.discountMonth(currentMonth, 'owner');
    familyDiscountMonth = await api.discountMonth(currentMonth, 'family');
    if (notify) notifyListeners();
  }

  Future<void> refreshInputArea({bool notify = true}) async {
    await refreshNotificationPermissions(notify: false);
    await _refreshEntriesAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshCashArea({bool notify = true}) async {
    final results = await Future.wait([
      api.cashFlows(),
      api.summary(),
      api.judgment(),
    ]);
    cashFlows = results[0] as List<CashFlow>;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    if (notify) notifyListeners();
  }

  Future<void> refreshEntriesArea({bool notify = true}) async {
    await _refreshEntriesAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshSettlementArea({bool notify = true}) async {
    await _refreshPanelsAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshPanelManagementArea({bool notify = true}) async {
    await _refreshPanelsAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshPlannedManagementArea({bool notify = true}) async {
    await _refreshEntriesAndStatus();
    if (notify) notifyListeners();
  }

  Future<void> refreshSettingsArea({bool notify = true}) async {
    final results = await Future.wait([
      api.settings(),
      api.summary(),
      api.judgment(),
    ]);
    settings = results[0] as AppSettings;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    await _refreshDiscountMonths();
    if (notify) notifyListeners();
  }

  Future<void> _refreshEntriesAndStatus() async {
    final results = await Future.wait([
      api.currentEntries(),
      api.summary(),
      api.judgment(),
      api.monthCloseStatus(),
    ]);
    entries = results[0] as List<LedgerEntry>;
    summary = results[1] as Summary;
    judgment = results[2] as JudgmentState;
    monthCloseStatus = results[3] as MonthCloseStatus;
    await _refreshDiscountMonths();
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
  }

  Future<void> _refreshDiscountMonths() async {
    final month = currentMonth;
    final results = await Future.wait([
      api.discountMonth(month, 'owner'),
      api.discountMonth(month, 'family'),
    ]);
    ownerDiscountMonth = results[0];
    familyDiscountMonth = results[1];
  }

  Future<void> refreshNotificationPermissions({bool notify = true}) async {
    notificationPermissions = await notificationBridge.permissionStatus();
    if (notify) notifyListeners();
  }

  Future<void> openNotificationListenerSettings() async {
    await notificationBridge.openSettings();
    await refreshNotificationPermissions();
  }

  Future<void> requestAppNotifications() async {
    await notificationBridge.requestAppNotifications();
    await refreshNotificationPermissions();
  }

  Future<void> createExpense({
    required String usagePlace,
    required String usageItem,
    required int amount,
    required bool discountEnabled,
    String? entryDate,
  }) async {
    await _run(() async {
      final entry = await api.createExpense(
        date: entryDate ?? _today(),
        usagePlace: usagePlace,
        usageItem: usageItem,
        amount: amount,
      );
      if (!discountEnabled && entry.paymentKey != null) {
        await api.excludeEntryDiscount(entry.paymentKey!);
      }
      await refreshInputArea(notify: false);
      statusMessage = '지출 추가 완료';
    });
  }

  Future<void> createPanel({
    required String panelType,
    required String title,
    required int amount,
    bool discountEnabled = true,
    String? spentOn,
  }) async {
    await _run(() async {
      final panel = await api.createPanel(
        month: currentMonth,
        panelType: panelType,
        title: title,
        amount: amount,
        spentOn: spentOn ?? _today(),
      );
      if (!discountEnabled &&
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

  Future<void> confirmPlannedEntry(int entryId) async {
    await _run(() async {
      await api.confirmPlannedEntry(entryId);
      await refreshPlannedManagementArea(notify: false);
      statusMessage = '카드 정기결제 확인 완료';
    });
  }

  Future<void> deletePlannedEntry(int entryId) async {
    await _run(() async {
      await api.deletePlannedEntry(entryId);
      await refreshPlannedManagementArea(notify: false);
      statusMessage = '카드 정기결제 삭제 완료';
    });
  }

  Future<void> excludeExistingEntryDiscount(String entryPaymentKey) async {
    await _run(() async {
      await api.excludeEntryDiscount(entryPaymentKey);
      await refreshEntriesArea(notify: false);
      statusMessage = '할인 제외 완료';
    });
  }

  Future<void> applyDefaultEntryDiscount(String entryPaymentKey) async {
    await _run(() async {
      await api.clearEntryDiscount(entryPaymentKey);
      await refreshEntriesArea(notify: false);
      statusMessage = '할인 적용 완료';
    });
  }

  Future<void> registerNotificationCandidate({
    required PendingCardNotification candidate,
    required String usageItem,
    required String target,
    required bool discountEnabled,
  }) async {
    final date = _dateFromMonthDay(candidate.monthDay);
    if (target == 'family_card') {
      await createPanel(
        panelType: 'family_card',
        title: usageItem.trim().isEmpty
            ? candidate.usagePlace
            : '${candidate.usagePlace} ${usageItem.trim()}',
        amount: candidate.amount,
        discountEnabled: discountEnabled,
        spentOn: date,
      );
    } else {
      await createExpense(
        usagePlace: candidate.usagePlace,
        usageItem: usageItem,
        amount: candidate.amount,
        discountEnabled: discountEnabled,
        entryDate: date,
      );
    }
  }

  Future<void> deletePanel(int panelId) async {
    await _run(() async {
      await api.deletePanel(panelId);
      await refreshPanelManagementArea(notify: false);
      statusMessage = '항목 삭제 완료';
    });
  }

  Future<void> excludeExistingPanelDiscount(int panelId) async {
    await _run(() async {
      await api.excludePanelDiscount(panelId);
      await refreshSettlementArea(notify: false);
      statusMessage = '할인 제외 완료';
    });
  }

  Future<void> applyDefaultPanelDiscount(int panelId) async {
    await _run(() async {
      await api.clearPanelDiscount(panelId);
      await refreshSettlementArea(notify: false);
      statusMessage = '할인 적용 완료';
    });
  }

  Future<void> completePanelType(String panelType) async {
    await _run(() async {
      await api.completePanelType(panelType);
      await refreshSettlementArea(notify: false);
      statusMessage = panelType == 'claim' ? '청구 처리 완료' : '가족카드 처리 완료';
    });
  }

  Future<void> sharePanel(String panelType) async {
    await Share.share(api.sharePageUri(panelType).toString());
  }

  Future<void> createCashFlow({
    required String title,
    required int amount,
    required bool isIncome,
    required bool isPrimaryIncome,
  }) async {
    await _run(() async {
      await api.createCashFlow(
        occurredOn: serverToday,
        title: title,
        amount: isIncome ? amount : -amount,
        isPrimaryIncome: isIncome && isPrimaryIncome,
      );
      await refreshCashArea(notify: false);
      statusMessage = '현금흐름 추가 완료';
    });
  }

  Future<void> deleteCashFlow(int flowId) async {
    await _run(() async {
      await api.deleteCashFlow(flowId);
      await refreshCashArea(notify: false);
      statusMessage = '현금흐름 삭제 완료';
    });
  }

  Future<void> saveLaunchSnapshot() async {
    try {
      final snapshot = await api.downloadSnapshot();
      final directory = await _snapshotDirectory();
      final backup = File(
          '${directory.path}/money-note-snapshot-${_timestampForFilename()}.money-note-snapshot.json');
      await backup.writeAsBytes(snapshot.bytes, flush: true);
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
      await Share.shareXFiles(
        [
          XFile(current.path,
              mimeType: 'application/json', name: snapshots.first.filename)
        ],
        text: 'Money-Note 스냅샷 백업',
      );
      localSnapshots = await listLocalSnapshots();
      statusMessage = '스냅샷 공유 준비 완료';
    });
  }

  Future<void> shareLocalSnapshot(String filename) async {
    await _run(() async {
      final snapshot = await _safeSnapshotFile(filename);
      await Share.shareXFiles(
        [
          XFile(snapshot.path,
              mimeType: 'application/json',
              name: 'money-note-snapshot-${_timestampForFilename()}.json')
        ],
        text: 'Money-Note 스냅샷 백업',
      );
      statusMessage = '스냅샷 공유 준비 완료';
    });
  }

  Future<void> restoreLocalSnapshot({
    required String filename,
    required String password,
  }) async {
    await _run(() async {
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

  Future<void> closeCurrentMonth({bool allowEarlyClose = false}) async {
    await _run(() async {
      final result =
          await api.closeCurrentMonth(allowEarlyClose: allowEarlyClose);
      await refresh(notify: false);
      statusMessage = '월마감 완료: ${result['closed_month'] ?? '마감할 월 없음'}';
    });
  }

  Future<void> updateSetting(String key, String value) async {
    await _run(() async {
      await api.updateSetting(key, value);
      await refreshSettingsArea(notify: false);
      statusMessage = '설정 저장 완료';
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    isBusy = true;
    statusMessage = '';
    notifyListeners();
    try {
      await action();
    } catch (error) {
      statusMessage =
          error is MoneyNoteApiException ? error.message : error.toString();
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
    return '${now.year.toString().padLeft(4, '0')}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
  }

  String _dateFromMonthDay(String monthDay) {
    final now = DateTime.now();
    final parts = monthDay.split('/');
    if (parts.length != 2) return _today();
    final month = int.tryParse(parts[0]) ?? now.month;
    final day = int.tryParse(parts[1]) ?? now.day;
    return '${now.year.toString().padLeft(4, '0')}-${month.toString().padLeft(2, '0')}-${day.toString().padLeft(2, '0')}';
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
    return '${now.year.toString().padLeft(4, '0')}${now.month.toString().padLeft(2, '0')}${now.day.toString().padLeft(2, '0')}-${now.hour.toString().padLeft(2, '0')}${now.minute.toString().padLeft(2, '0')}${now.second.toString().padLeft(2, '0')}';
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
