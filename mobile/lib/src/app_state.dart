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
  bool isBusy = false;
  String statusMessage = '';
  AuthUser? user;
  Summary? summary;
  JudgmentState? judgment;
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
    ]);
    summary = results[0] as Summary;
    judgment = results[1] as JudgmentState;
    entries = results[2] as List<LedgerEntry>;
    panels = results[3] as List<MonthlyPanel>;
    cashFlows = results[4] as List<CashFlow>;
    settings = results[5] as AppSettings;
    ownerDiscountMonth = await api.discountMonth(currentMonth, 'owner');
    familyDiscountMonth = await api.discountMonth(currentMonth, 'family');
    if (notify) notifyListeners();
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
      await refresh(notify: false);
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
      await refresh(notify: false);
      statusMessage = panelType == 'claim' ? '청구 추가 완료' : '가족카드 추가 완료';
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
      await refresh(notify: false);
      statusMessage = '항목 삭제 완료';
    });
  }

  Future<void> completePanelType(String panelType) async {
    await _run(() async {
      await api.completePanelType(panelType);
      await refresh(notify: false);
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
        occurredOn: _today(),
        title: title,
        amount: isIncome ? amount : -amount,
        isPrimaryIncome: isIncome && isPrimaryIncome,
      );
      await refresh(notify: false);
      statusMessage = '현금흐름 추가 완료';
    });
  }

  Future<void> deleteCashFlow(int flowId) async {
    await _run(() async {
      await api.deleteCashFlow(flowId);
      await refresh(notify: false);
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
