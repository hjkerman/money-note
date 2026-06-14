import 'package:flutter/material.dart';

import 'api_client.dart';
import 'models.dart';

class AppState extends ChangeNotifier {
  AppState(this.api);

  final MoneyNoteApiClient api;

  bool isBootstrapping = true;
  bool isBusy = false;
  String statusMessage = '';
  AuthUser? user;
  Summary? summary;
  JudgmentState? judgment;
  CardPaymentStatus? cardPayments;
  List<LedgerEntry> entries = [];
  List<MonthlyPanel> panels = [];

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
    await api.loadSession();
    try {
      user = await api.me();
      await refresh();
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
      statusMessage = '로그인 완료';
    });
  }

  Future<void> logout() async {
    await _run(() async {
      await api.logout();
      user = null;
      summary = null;
      judgment = null;
      cardPayments = null;
      entries = [];
      panels = [];
      statusMessage = '로그아웃 완료';
    });
  }

  Future<void> refresh({bool notify = true}) async {
    final results = await Future.wait([
      api.summary(),
      api.judgment(),
      api.currentEntries(),
      api.currentPanels(),
      api.currentCardPayments(),
    ]);
    summary = results[0] as Summary;
    judgment = results[1] as JudgmentState;
    entries = results[2] as List<LedgerEntry>;
    panels = results[3] as List<MonthlyPanel>;
    cardPayments = results[4] as CardPaymentStatus;
    if (notify) notifyListeners();
  }

  Future<void> createExpense({
    required String usagePlace,
    required String usageItem,
    required int amount,
  }) async {
    await _run(() async {
      await api.createExpense(
        date: _today(),
        usagePlace: usagePlace,
        usageItem: usageItem,
        amount: amount,
      );
      await refresh(notify: false);
      statusMessage = '지출 추가 완료';
    });
  }

  Future<void> createPanel({
    required String panelType,
    required String title,
    required int amount,
  }) async {
    await _run(() async {
      await api.createPanel(
        month: currentMonth,
        panelType: panelType,
        title: title,
        amount: amount,
        spentOn: _today(),
      );
      await refresh(notify: false);
      statusMessage = panelType == 'claim' ? '청구 추가 완료' : '가족카드 추가 완료';
    });
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

  Future<void> payImmediately(CardPaymentRow row) async {
    if (row.paymentKeys.isEmpty || row.remainingAmount <= 0) return;
    await _run(() async {
      await api.createImmediatePayment(
        eventDate: _today(),
        note: '모바일 즉시결제',
        allocations: [
          {
            'entry_payment_key': row.paymentKeys.first,
            'amount_value': row.remainingAmount
          },
        ],
      );
      await refresh(notify: false);
      statusMessage = '즉시결제 기록 완료';
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
}
