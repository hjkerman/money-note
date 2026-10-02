import 'dart:convert';
import 'dart:io';

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
  Future<bool> confirmPlannedEntry(
      int entryId, String entryDate, int actualAmount) async {
    confirmedPlannedId = entryId;
    confirmedPlannedAmount = actualAmount;
    return true;
  }

  @override
  Future<bool> confirmFixedPanel(
      int panelId, String occurredOn, int actualAmount) async {
    confirmedFixedId = panelId;
    confirmedFixedAmount = actualAmount;
    return true;
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
  testWidgets('날짜 없는 archive 실제 지출도 서버 confirmed 금액을 표시한다', (tester) async {
    _useTallTestSurface(tester);
    final state = _RecurringTestState();
    addTearDown(state.dispose);
    final payload = jsonDecode(
        File('../backend/tests/fixtures/confirmed_recurring_actual.json')
            .readAsStringSync()) as Map<String, dynamic>;
    state.confirmedPlannedEntries = [
      LedgerEntry.fromJson({...payload, 'id': 1, 'sort_order': 1})
    ];
    await tester.pumpWidget(
        MaterialApp(home: PlannedEntryManagementScreen(state: state)));
    expect(find.text('실제 원금'), findsOneWidget);
    expect(find.text('7,000원'), findsOneWidget);
    expect(find.text('84원'), findsOneWidget);
    expect(find.text('6,916원'), findsOneWidget);
    expect(find.text('5,000원'),
        findsWidgets); // separate planned-principal label remains intentional
  });

  testWidgets('월마감 이후 서버가 현금 선처리만 열고 카드 확인은 닫는다', (tester) async {
    _useTallTestSurface(tester);
    final state = _RecurringTestState();
    state.monthCloseStatus = MonthCloseStatus.fromJson({
      'calendar_date': '2026-09-30',
      'calendar_month': '2026-09',
      'last_closed_month': '2026-09',
      'card_recurring_confirmation_available': false,
    });
    state.entries = [_planned(id: 1, dueDay: 1, amount: 1000, sortOrder: 1)];
    await tester.pumpWidget(
        MaterialApp(home: PlannedEntryManagementScreen(state: state)));
    expect(
        tester
            .widget<ElevatedButton>(
                find.widgetWithText(ElevatedButton, '확인 처리'))
            .onPressed,
        isNull);
    for (final allowed in [false, true]) {
      state.panels = [
        MonthlyPanel.fromJson({
          'id': 11,
          'month': '2026-10',
          'panel_type': 'fixed',
          'title': 'October',
          'sort_order': 1,
          'amount_value': 1000,
          'can_confirm_fixed': allowed,
          'fixed_execution_month': '2026-10',
        })
      ];
      await tester.pumpWidget(MaterialApp(
          home: PanelManagementScreen(
        state: state,
        panelType: 'fixed',
        title: '고정지출',
        inputLabel: '내용',
        emptyText: '없음',
      )));
      state.notifyListeners();
      await tester.pump();
      final button = tester
          .widget<ElevatedButton>(find.widgetWithText(ElevatedButton, '확인 처리'));
      expect(button.onPressed != null, allowed);
    }
  });

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

  testWidgets('현금성 고정지출은 서버 실제 처리액과 전체 예정액을 함께 표시한다', (tester) async {
    _useTallTestSurface(tester);
    final state = _RecurringTestState();
    state.summary = Summary.fromJson({
      'fixed_cash_total': 10000,
      'fixed_cash_processed_total': 8000,
    });

    await tester.pumpWidget(MaterialApp(
      home: PanelManagementScreen(
        state: state,
        panelType: 'fixed',
        title: '현금성 고정지출',
        inputLabel: '지출 내용',
        emptyText: '현금성 고정지출이 없습니다.',
      ),
    ));

    expect(find.text('8,000원 / 총 10,000원'), findsOneWidget);
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
