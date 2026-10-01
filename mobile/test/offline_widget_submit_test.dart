import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/screens/cash_flow_screen.dart';
import 'package:money_note_mobile/src/screens/input_screen.dart';
import 'package:money_note_mobile/src/screens/management_screen.dart';

import 'support/offline_mode_fixtures.dart';

class FormAppStateFake extends AppState {
  FormAppStateFake() : super(OfflineApiFake());

  Completer<bool> expenseCompletion = Completer<bool>();
  Completer<bool> cashCompletion = Completer<bool>();
  Completer<bool> panelCompletion = Completer<bool>();
  Completer<PlannedChargePreview> plannedPreviewCompletion =
      Completer<PlannedChargePreview>();
  Completer<bool> plannedConfirmCompletion = Completer<bool>();
  int expenseCalls = 0;
  bool? lastExpenseDiscountEnabled;
  int cashCalls = 0;
  int panelCalls = 0;
  int plannedPreviewCalls = 0;
  int plannedConfirmCalls = 0;

  @override
  Future<bool> createExpense({
    required String usagePlace,
    required String usageItem,
    required int amount,
    required bool discountEnabled,
    int? netAmountOverride,
    String? spendingCategory,
    String? entryDate,
    String? candidateRegistrationKey,
  }) {
    expenseCalls += 1;
    lastExpenseDiscountEnabled = discountEnabled;
    return expenseCompletion.future;
  }

  @override
  Future<bool> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isIncome,
    required bool isPrimaryIncome,
  }) {
    cashCalls += 1;
    return cashCompletion.future;
  }

  @override
  Future<bool> createPanel({
    required String panelType,
    required String title,
    required int amount,
    bool discountEnabled = true,
    String? spentOn,
    String? candidateRegistrationKey,
    String? manualRegistrationKey,
  }) {
    panelCalls += 1;
    return panelCompletion.future;
  }

  @override
  Future<PlannedChargePreview> previewPlannedEntry(
      int entryId, int actualAmount) {
    plannedPreviewCalls += 1;
    return plannedPreviewCompletion.future;
  }

  @override
  Future<bool> confirmPlannedEntry(
      int entryId, String entryDate, int actualAmount) {
    plannedConfirmCalls += 1;
    return plannedConfirmCompletion.future;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('home liquidity slot uses the server current-month amount',
      (tester) async {
    final state = AppState(OfflineApiFake())
      ..summary = baselineFixture(
        remainingLiquidity: 1261930,
        currentMonthSpendable: 441930,
      ).summary
      ..monthCloseStatus = baselineFixture().monthCloseStatus;
    addTearDown(state.dispose);

    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: HomeScreen(state: state)),
    ));

    expect(find.text('441,930원'), findsOneWidget);
    expect(find.text('1,261,930원'), findsNothing);
  });

  testWidgets('server failure prompt offers offline mode and app exit',
      (tester) async {
    final directory = (await tester.runAsync(temporaryDirectoryFixture))!;
    final state = AppState(
      OfflineApiFake(),
      offlineStore: offlineStoreFixture(directory),
    )
      ..isBootstrapping = false
      ..serverFailurePromptPending = true;
    final platformCalls = <MethodCall>[];
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (call) async {
        platformCalls.add(call);
        return null;
      },
    );
    addTearDown(() {
      tester.binding.defaultBinaryMessenger
          .setMockMethodCallHandler(SystemChannels.platform, null);
      state.dispose();
    });

    await tester.pumpWidget(MoneyNoteApp(
      stateOverride: state,
      bootstrapOnStart: false,
    ));

    expect(
      find.text('서버에 연결할 수 없습니다.\n오프라인 모드로 사용하시겠습니까?'),
      findsOneWidget,
    );
    expect(find.text('오프라인 모드 사용'), findsOneWidget);
    expect(find.text('앱 종료'), findsOneWidget);

    await SystemNavigator.pop();
    expect(
      platformCalls.any((call) => call.method == 'SystemNavigator.pop'),
      isTrue,
    );
  });

  testWidgets(
      'offline shell keeps banner and estimated financial labels visible',
      (tester) async {
    final directory = (await tester.runAsync(temporaryDirectoryFixture))!;
    final store = offlineStoreFixture(directory);
    await tester.runAsync(() => store.replaceBaseline(baselineFixture()));
    final state = AppState(OfflineApiFake(), offlineStore: store);
    expect(await tester.runAsync(state.enterOfflineMode), isTrue);
    state.isBootstrapping = false;
    addTearDown(state.dispose);

    await tester.pumpWidget(MoneyNoteApp(
      stateOverride: state,
      bootstrapOnStart: false,
    ));
    await tester.pump();

    expect(find.textContaining('오프라인 · 마지막 동기화'), findsOneWidget);
    expect(find.text('잔여 유동성(예상)').hitTestable(), findsOneWidget);
  });

  testWidgets(
      'reconciliation boundary is read-only and requires an explicit choice',
      (tester) async {
    final directory = (await tester.runAsync(temporaryDirectoryFixture))!;
    final store = offlineStoreFixture(directory);
    await tester.runAsync(() => store.replaceBaseline(baselineFixture()));
    await tester.runAsync(() => saveLinkedMetadata(
        store,
        const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.reconciliationRequired,
        )));
    await tester.runAsync(() => store.appendOperation(
          type: OfflineOperationType.createCardExpense,
          payload: const {
            'entry_date': '2026-09-01',
            'usage_place': '가게',
            'amount_value': 100,
          },
        ));
    final state = AppState(
      OfflineApiFake()..available = true,
      offlineStore: store,
    );
    await tester.runAsync(state.restorePersistedOfflineWorkspace);
    state.isBootstrapping = false;
    addTearDown(state.dispose);

    await tester.pumpWidget(MoneyNoteApp(
      stateOverride: state,
      bootstrapOnStart: false,
    ));
    expect(find.text('오프라인 변경사항을 서버에 적용'), findsOneWidget);
    expect(find.text('오프라인 변경사항을 폐기하고 서버 데이터 사용'), findsOneWidget);

    await tester.runAsync(() => state.selectReconciliationChoice(
          ReconciliationChoice.applyToServer,
        ));
    await tester.pump();
    expect(state.reconciliationChoice, ReconciliationChoice.applyToServer);
    expect(state.isReconciliationRequired, isTrue);
    expect(await tester.runAsync(store.loadJournal), hasLength(1));
    expect(find.textContaining('양쪽 recovery point가 검증되었습니다'), findsOneWidget);
    expect(find.text('Mobile Wins 최종 실행'), findsOneWidget);
  });
  testWidgets('server change shows an additional destructive confirmation',
      (tester) async {
    final directory = (await tester.runAsync(temporaryDirectoryFixture))!;
    final store = offlineStoreFixture(directory);
    await tester.runAsync(() => store.replaceBaseline(baselineFixture()));
    await tester.runAsync(() => saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.reconciliationRequired,
          ),
        ));
    await tester.runAsync(() => store.appendOperation(
          type: OfflineOperationType.createCardExpense,
          payload: const {
            'entry_date': '2026-09-01',
            'usage_place': '가게',
            'amount_value': 100,
          },
        ));
    final state = AppState(
      OfflineApiFake()
        ..available = true
        ..serverChanged = true,
      offlineStore: store,
    );
    await tester.runAsync(state.restorePersistedOfflineWorkspace);
    state.isBootstrapping = false;
    addTearDown(state.dispose);
    await tester.pumpWidget(MoneyNoteApp(
      stateOverride: state,
      bootstrapOnStart: false,
    ));

    await tester.runAsync(() => state.selectReconciliationChoice(
          ReconciliationChoice.applyToServer,
        ));
    await tester.pump();
    expect(
      find.text('오프라인 모드 시작 이후 서버 데이터도 변경되었습니다.'),
      findsOneWidget,
    );

    await tester.tap(find.text('Mobile Wins 최종 실행'));
    await tester.pumpAndSettle();
    expect(find.text('Mobile Wins를 실행할까요?'), findsOneWidget);
    expect(find.textContaining('오프라인 진입 직전 기준 B를 복원'), findsOneWidget);

    await tester.tap(find.text('Mobile Wins 계속'));
    await tester.pumpAndSettle();
    expect(find.text('서버 변경도 덮어쓸까요?'), findsOneWidget);
    expect(find.textContaining('Apply(B, J)'), findsOneWidget);
  });

  testWidgets('expense keyboard and button re-entry produces one submit',
      (tester) async {
    final state = FormAppStateFake();
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: ExpenseInputCard(state: state)),
    ));
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), '가게');
    await tester.enterText(fields.at(1), '500');

    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.tap(find.text('지출 추가'));
    expect(state.expenseCalls, 1);

    state.expenseCompletion.complete(true);
    await tester.pumpAndSettle();
    expect(tester.widget<TextField>(fields.at(0)).controller!.text, isEmpty);
    expect(tester.widget<TextField>(fields.at(1)).controller!.text, isEmpty);
  });

  testWidgets('utility expense checkbox defaults off and explicit apply wins',
      (tester) async {
    final state = FormAppStateFake();
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: ExpenseInputCard(state: state)),
    ));
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), '서울도시가스');
    await tester.enterText(fields.at(1), '10000');
    expect(tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
        isFalse);
    await tester.tap(find.byType(CheckboxListTile));
    await tester.pump();
    expect(tester.widget<CheckboxListTile>(find.byType(CheckboxListTile)).value,
        isTrue);
    await tester.tap(find.text('지출 추가'));
    expect(state.lastExpenseDiscountEnabled, isTrue);
    state.expenseCompletion.complete(true);
    await tester.pump();
  });

  testWidgets('expense failure and stale completion preserve the current draft',
      (tester) async {
    final state = FormAppStateFake();
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: ExpenseInputCard(state: state)),
    ));
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), '가게');
    await tester.enterText(fields.at(1), '500');
    await tester.tap(find.text('지출 추가'));
    state.expenseCompletion.complete(false);
    await tester.pumpAndSettle();

    expect(tester.widget<TextField>(fields.at(0)).controller!.text, '가게');
    expect(tester.widget<TextField>(fields.at(1)).controller!.text, '500');

    state.expenseCompletion = Completer<bool>();
    await tester.tap(find.text('지출 추가'));
    await tester.enterText(fields.at(1), '700');
    state.expenseCompletion.complete(true);
    await tester.pumpAndSettle();

    expect(state.expenseCalls, 2);
    expect(tester.widget<TextField>(fields.at(0)).controller!.text, '가게');
    expect(tester.widget<TextField>(fields.at(1)).controller!.text, '700');
  });

  testWidgets('cash-flow save failure preserves its draft', (tester) async {
    final state = FormAppStateFake();
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(body: CashFlowScreen(state: state)),
    ));
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), '현금 draft');
    await tester.enterText(fields.at(1), '500');
    await tester.testTextInput.receiveAction(TextInputAction.done);
    state.cashCompletion.complete(false);
    await tester.pumpAndSettle();

    expect(state.cashCalls, 1);
    expect(tester.widget<TextField>(fields.at(0)).controller!.text, '현금 draft');
    expect(tester.widget<TextField>(fields.at(1)).controller!.text, '500');
  });

  testWidgets(
      'recurring panel submit is single-flight and preserves failed or newer drafts',
      (tester) async {
    final state = FormAppStateFake();
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp(
      home: PanelManagementScreen(
        state: state,
        panelType: 'fixed',
        title: '현금성 고정지출',
        inputLabel: '지출 내용',
        emptyText: '없음',
      ),
    ));
    final fields = find.byType(TextField);
    await tester.enterText(fields.at(0), '관리비');
    await tester.enterText(fields.at(1), '500');

    await tester.testTextInput.receiveAction(TextInputAction.done);
    await tester.tap(find.text('추가'));
    expect(state.panelCalls, 1);
    state.panelCompletion.complete(false);
    await tester.pumpAndSettle();

    expect(tester.widget<TextField>(fields.at(0)).controller!.text, '관리비');
    expect(tester.widget<TextField>(fields.at(1)).controller!.text, '500');

    state.panelCompletion = Completer<bool>();
    await tester.tap(find.text('추가'));
    await tester.enterText(fields.at(1), '700');
    state.panelCompletion.complete(true);
    await tester.pumpAndSettle();

    expect(state.panelCalls, 2);
    expect(tester.widget<TextField>(fields.at(0)).controller!.text, '관리비');
    expect(tester.widget<TextField>(fields.at(1)).controller!.text, '700');
  });

  testWidgets(
      'recurring confirmation rejects stale preview and preserves the newer amount',
      (tester) async {
    final state = FormAppStateFake()
      ..monthCloseStatus = baselineFixture().monthCloseStatus
      ..entries = [
        LedgerEntry(
          id: 17,
          bookSection: 'current',
          entryKind: 'planned',
          title: '정기 구독',
          sortOrder: 1,
          usagePlace: '구독처',
          amountValue: 500,
          dueDay: 17,
          discountPolicy: 'enabled',
          automaticDiscountEligible: true,
          effectiveDiscountAmount: 6,
          effectiveAmountValue: 494,
        ),
      ];
    addTearDown(state.dispose);
    await tester.pumpWidget(MaterialApp(
      home: PlannedEntryManagementScreen(state: state),
    ));
    final amountField =
        find.byKey(const ValueKey('planned-recurring-amount-17'));
    await tester.drag(find.byType(ListView), const Offset(0, -600));
    await tester.pumpAndSettle();
    expect(amountField, findsOneWidget);

    await tester.tap(find.widgetWithText(ElevatedButton, '확인 처리'));
    await tester.tap(find.widgetWithText(ElevatedButton, '확인 처리'));
    expect(state.plannedPreviewCalls, 1);

    await tester.enterText(amountField, '700');
    state.plannedPreviewCompletion.complete(PlannedChargePreview(
      amountValue: 500,
      discountPolicy: 'enabled',
      automaticDiscountEligible: true,
      effectiveDiscountAmount: 6,
      effectiveAmountValue: 494,
    ));
    await tester.pumpAndSettle();

    expect(find.text('입력이 변경되었습니다. 현재 값으로 다시 확인하세요.'), findsOneWidget);
    expect(state.plannedConfirmCalls, 0);
    expect(
      tester.widget<TextField>(amountField).controller!.text,
      '700',
    );
  });
}
