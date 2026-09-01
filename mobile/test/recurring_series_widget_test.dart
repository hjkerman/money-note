import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/screens/management_screen.dart';

class _RecurringTestState extends AppState {
  _RecurringTestState()
      : super(MoneyNoteApiClient(baseUrl: 'https://example.invalid'));

  int? confirmedPlannedId;
  int? confirmedPlannedAmount;
  int? confirmedFixedId;
  int? confirmedFixedAmount;

  void replaceEntries(List<LedgerEntry> value) {
    entries = value;
    notifyListeners();
  }

  void replacePanels(List<MonthlyPanel> value) {
    panels = value;
    notifyListeners();
  }

  @override
  Future<PlannedChargePreview> previewPlannedEntry(
      int entryId, int actualAmount) async {
    return PlannedChargePreview(
      amountValue: actualAmount,
      discountPolicy: 'disabled',
      automaticDiscountEligible: false,
      effectiveDiscountAmount: 0,
      effectiveAmountValue: actualAmount,
    );
  }

  @override
  Future<void> confirmPlannedEntry(
      int entryId, String entryDate, int actualAmount) async {
    confirmedPlannedId = entryId;
    confirmedPlannedAmount = actualAmount;
  }

  @override
  Future<void> confirmFixedPanel(
      int panelId, String occurredOn, int actualAmount) async {
    confirmedFixedId = panelId;
    confirmedFixedAmount = actualAmount;
  }
}

LedgerEntry _planned({
  required int id,
  required int dueDay,
  required int amount,
  required int sortOrder,
}) {
  return LedgerEntry(
    id: id,
    bookSection: 'current',
    entryKind: 'planned',
    title: '정기결제 $id',
    usagePlace: '사용처 $id',
    usageItem: '세부내역 $id',
    amountValue: amount,
    effectiveAmountValue: amount,
    dueDay: dueDay,
    sortOrder: sortOrder,
  );
}

MonthlyPanel _fixed({
  required int id,
  required int amount,
  required int sortOrder,
}) {
  return MonthlyPanel(
    id: id,
    month: '2026-09',
    panelType: 'fixed',
    title: '고정지출 $id',
    amountValue: amount,
    sortOrder: sortOrder,
    discountAmount: 0,
    discountOverride: 0,
  );
}

String _fieldText(WidgetTester tester, String key) {
  final field = tester.widget<TextField>(find.byKey(ValueKey(key)));
  return field.controller!.text;
}

void _useTallTestSurface(WidgetTester tester) {
  tester.view.devicePixelRatio = 1;
  tester.view.physicalSize = const Size(1200, 2400);
  addTearDown(tester.view.reset);
}

void main() {
  testWidgets('카드 정기결제 편집값은 재정렬과 추가 삭제 후에도 시리즈 id에 유지된다', (tester) async {
    _useTallTestSurface(tester);
    final state = _RecurringTestState();
    state.entries = [
      _planned(id: 1, dueDay: 10, amount: 1000, sortOrder: 1),
      _planned(id: 2, dueDay: 20, amount: 2000, sortOrder: 2),
    ];

    await tester.pumpWidget(
      MaterialApp(home: PlannedEntryManagementScreen(state: state)),
    );
    await tester.enterText(
      find.byKey(const ValueKey('planned-recurring-amount-1')),
      '1500',
    );

    state.replaceEntries([
      _planned(id: 1, dueDay: 30, amount: 1000, sortOrder: 2),
      _planned(id: 2, dueDay: 5, amount: 2000, sortOrder: 1),
    ]);
    await tester.pump();

    expect(_fieldText(tester, 'planned-recurring-amount-1'), '1500');
    expect(_fieldText(tester, 'planned-recurring-amount-2'), '2000');

    state.replaceEntries([
      _planned(id: 1, dueDay: 30, amount: 1000, sortOrder: 2),
      _planned(id: 3, dueDay: 1, amount: 3000, sortOrder: 1),
    ]);
    await tester.pump();

    expect(_fieldText(tester, 'planned-recurring-amount-1'), '1500');
    expect(_fieldText(tester, 'planned-recurring-amount-3'), '3000');

    final row = find.byKey(const ValueKey('planned-recurring-1'));
    final confirmButton = find.descendant(
      of: row,
      matching: find.widgetWithText(ElevatedButton, '확인 처리'),
    );
    await tester.ensureVisible(confirmButton);
    await tester.tap(confirmButton);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '확인 처리'));
    await tester.pumpAndSettle();

    expect(state.confirmedPlannedId, 1);
    expect(state.confirmedPlannedAmount, 1500);
  });

  testWidgets('현금성 고정지출 편집값은 행 순서가 바뀌어도 시리즈 id에 유지된다', (tester) async {
    _useTallTestSurface(tester);
    final state = _RecurringTestState();
    state.panels = [
      _fixed(id: 11, amount: 11000, sortOrder: 1),
      _fixed(id: 22, amount: 22000, sortOrder: 2),
    ];

    await tester.pumpWidget(
      MaterialApp(
        home: PanelManagementScreen(
          state: state,
          panelType: 'fixed',
          title: '현금성 고정지출',
          inputLabel: '지출 내용',
          emptyText: '현금성 고정지출이 없습니다.',
        ),
      ),
    );
    await tester.enterText(
      find.byKey(const ValueKey('fixed-recurring-amount-11')),
      '11500',
    );

    state.replacePanels([
      _fixed(id: 11, amount: 11000, sortOrder: 2),
      _fixed(id: 22, amount: 22000, sortOrder: 1),
    ]);
    await tester.pump();

    expect(_fieldText(tester, 'fixed-recurring-amount-11'), '11500');
    expect(_fieldText(tester, 'fixed-recurring-amount-22'), '22000');

    state.replacePanels([
      _fixed(id: 11, amount: 11000, sortOrder: 2),
      _fixed(id: 33, amount: 33000, sortOrder: 1),
    ]);
    await tester.pump();

    expect(_fieldText(tester, 'fixed-recurring-amount-11'), '11500');
    expect(_fieldText(tester, 'fixed-recurring-amount-33'), '33000');

    final row = find.byKey(const ValueKey('fixed-recurring-11'));
    final confirmButton = find.descendant(
      of: row,
      matching: find.widgetWithText(ElevatedButton, '확인 처리'),
    );
    await tester.ensureVisible(confirmButton);
    await tester.tap(confirmButton);
    await tester.pumpAndSettle();
    await tester.tap(find.widgetWithText(FilledButton, '확인 처리'));
    await tester.pumpAndSettle();

    expect(state.confirmedFixedId, 11);
    expect(state.confirmedFixedAmount, 11500);
  });

  testWidgets('빈 실제 원금은 label이나 기본 문구 대신 저장되지 않는다', (tester) async {
    _useTallTestSurface(tester);
    final state = _RecurringTestState();
    state.entries = [
      _planned(id: 7, dueDay: 7, amount: 7000, sortOrder: 1),
    ];

    await tester.pumpWidget(
      MaterialApp(home: PlannedEntryManagementScreen(state: state)),
    );
    final amountField =
        find.byKey(const ValueKey('planned-recurring-amount-7'));
    await tester.enterText(amountField, '');
    final row = find.byKey(const ValueKey('planned-recurring-7'));
    final confirmButton = find.descendant(
      of: row,
      matching: find.widgetWithText(ElevatedButton, '확인 처리'),
    );
    await tester.ensureVisible(confirmButton);
    await tester.tap(confirmButton);
    await tester.pump();

    expect(state.confirmedPlannedId, isNull);
    expect(find.text('실제 원금은 0원 이상의 정수로 입력하세요.'), findsOneWidget);
  });
}
