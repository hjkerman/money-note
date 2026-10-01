import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_projection.dart';

import 'support/offline_mode_fixtures.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();
  test(
      'early fixed projection preserves server period and does not duplicate reserve',
      () {
    final json = baselineFixture(currentMonthSpendable: 6000).toJson();
    final status = json['month_close_status'] as Map<String, dynamic>;
    status['calendar_date'] = '2026-09-30';
    status['calendar_month'] = '2026-09';
    status['last_closed_month'] = '2026-09';
    status['card_recurring_confirmation_available'] = false;
    final panel = (json['panels'] as List).single as Map<String, dynamic>;
    panel['can_confirm_fixed'] = true;
    panel['fixed_execution_month'] = '2026-10';
    final baseline = OfflineBaseline.fromJson(json);
    final restored = OfflineBaseline.fromJson(baseline.toJson());
    expect(restored.panels.single.fixedExecutionMonth, '2026-10');
    expect(
        restored.monthCloseStatus.cardRecurringConfirmationAvailable, isFalse);
    final projection = OfflineProjection.from(
        baseline,
        [
          OfflineJournalOperation(
              operationId: 'early',
              sequence: 1,
              type: OfflineOperationType.confirmFixedExpense,
              payload: const {
                'panel_id': 30,
                'occurred_on': '2026-09-30',
                'actual_amount': 800
              },
              createdAt: DateTime.utc(2026, 9, 30)),
        ],
        projectedAt: DateTime(2026, 9, 30));
    expect(projection.summary.cashFlowBalance, 4200);
    expect(projection.summary.currentMonthSpendable, 6200);
    expect(projection.panels.single.confirmedMonth, '2026-10');
    expect(projection.panels.single.spentOn, '2026-09-30');
    expect(projection.panels.single.canConfirmFixed, isFalse);
    final journal = [
      OfflineJournalOperation(
        operationId: 'early',
        sequence: 1,
        type: OfflineOperationType.confirmFixedExpense,
        payload: const {
          'panel_id': 30,
          'occurred_on': '2026-09-30',
          'actual_amount': 800
        },
        createdAt: DateTime.utc(2026, 9, 30),
      )
    ];
    expect(
        OfflineProjection.from(baseline, journal,
                projectedAt: DateTime(2026, 10, 1))
            .summary
            .currentMonthSpendable,
        5200);
    // The same transition must also work when the early transfer was already
    // committed in the authoritative baseline, not only present in J.
    final committedJson = baseline.toJson();
    final committedPanel =
        (committedJson['panels'] as List).single as Map<String, dynamic>;
    committedPanel['confirmed_month'] = '2026-10';
    committedPanel['confirmed_at'] = '2026-09-30T03:00:00Z';
    committedPanel['confirmed_cash_flow_id'] = 99;
    expect(
        OfflineProjection.from(OfflineBaseline.fromJson(committedJson), [],
                projectedAt: DateTime(2026, 10, 1))
            .summary
            .currentMonthSpendable,
        5000);
    expect(journal.single.payload.keys,
        unorderedEquals(['panel_id', 'occurred_on', 'actual_amount']));
  });

  group('offline state machine and projection', () {
    test('no baseline rejects deliberate offline entry', () async {
      final directory = await temporaryDirectoryFixture();
      final state = AppState(OfflineApiFake(),
          offlineStore: offlineStoreFixture(directory));

      expect(await state.enterOfflineMode(), isFalse);
      expect(state.isOnline, isTrue);
      expect(state.offlineEntryMessage, contains('한 번 동기화'));
    });

    test('unconfirmed manual registration blocks offline epoch across restart',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      const input = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '미확인 청구',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': false,
      };
      final key = await store.reserveManualPanelRetryKey(input);
      final restartedStore = offlineStoreFixture(directory);
      final state = AppState(OfflineApiFake(), offlineStore: restartedStore);

      expect(await state.enterOfflineMode(), isFalse);
      expect(state.isOnline, isTrue);
      expect(state.offlineEntryMessage, contains('저장 결과를 확인하지 못한'));
      expect(await restartedStore.hasPendingManualPanelRetry(), isTrue);
      await restartedStore.completeManualPanelRetryKey(input, key);
      expect(await state.enterOfflineMode(), isTrue);
    });

    test('in-flight online write cannot race a new offline epoch', () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final state = AppState(OfflineApiFake(), offlineStore: store)
        ..isBusy = true;
      expect(await state.enterOfflineMode(), isFalse);
      expect(state.offlineEntryMessage, contains('저장 또는 상태 전환'));
      expect((await store.loadMetadata()).mode, ConnectivityMode.online);
      state.isBusy = false;
      expect(await state.enterOfflineMode(), isTrue);
    });

    test('malformed manual retry identity fails closed on offline entry',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final retryFile =
          File('${directory.path}/offline-mode/manual-panel-retries.json');
      await retryFile.writeAsString('{"schema_version":1,"keys":{"draft":42}}');
      final state = AppState(OfflineApiFake(), offlineStore: store);

      expect(await state.enterOfflineMode(), isFalse);
      expect(state.isOnline, isTrue);
      expect(state.offlineEntryMessage, contains('재시도 기록을 읽을 수 없습니다'));
      expect(await retryFile.exists(), isTrue);
    });

    test('malformed manual retry identity blocks normal startup refresh',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final retryFile =
          File('${directory.path}/offline-mode/manual-panel-retries.json');
      await retryFile.writeAsString(
          '{"schema_version":2,"key":"x","input_digest":"bad","input":{}}');
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(await retryFile.exists(), isTrue);
    });

    test('offline card use without override keeps baseline discount intent',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      expect(
          await state.createExpense(
            usagePlace: '기본 할인 가게',
            usageItem: '식사',
            amount: 5000,
            discountEnabled: true,
            entryDate: '2026-09-17',
          ),
          isTrue);

      final payload = state.offlineJournal.single.payload;
      expect(payload['discount_enabled'], isTrue);
      expect(payload.containsKey('discount_override_amount'), isFalse);
      expect(payload.containsKey('effective_amount_value'), isFalse);
      expect(state.summary!.currentDiscountTotal, 60);
      expect(state.summary!.cardTotal, 5940);
      expect(state.summary!.remainingLiquidity, 5060);
      expect(state.expenseEntries.single.effectiveAmount, 4940);
      expect(state.usesConservativeCardEstimate, isFalse);
    });

    test('missing baseline discount policy falls back to gross estimate',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(
        baselineFixture(includeProjectionPolicy: false),
      );
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      expect(
          await state.createExpense(
            usagePlace: '정책 미확인 가게',
            usageItem: '',
            amount: 5000,
            discountEnabled: true,
            entryDate: '2026-09-17',
          ),
          isTrue);

      expect(state.summary!.currentDiscountTotal, 0);
      expect(state.summary!.remainingLiquidity, 5000);
      expect(state.expenseEntries.single.effectiveAmount, 5000);
      expect(state.usesConservativeCardEstimate, isTrue);
    });

    test('offline card use with discount exclusion uses gross amount',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      expect(
          await state.createExpense(
            usagePlace: '할인 제외 가게',
            usageItem: '',
            amount: 5000,
            discountEnabled: false,
            entryDate: '2026-09-17',
          ),
          isTrue);

      expect(state.offlineJournal.single.payload['discount_enabled'], isFalse);
      expect(state.summary!.remainingLiquidity, 5000);
      expect(state.usesConservativeCardEstimate, isFalse);
      expect(state.expenseEntries.single.effectiveAmount, 5000);
    });

    test('offline actual-payment override is journaled and projected exactly',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      expect(
          await state.createExpense(
            usagePlace: '직접 입력 가게',
            usageItem: '결제',
            amount: 5000,
            discountEnabled: true,
            netAmountOverride: 4700,
            entryDate: '2026-09-17',
          ),
          isTrue);

      final payload = state.offlineJournal.single.payload;
      expect(payload['amount_value'], 5000);
      expect(payload['discount_override_amount'], 300);
      expect(payload.containsKey('effective_amount_value'), isFalse);
      expect(payload.containsKey('remaining_liquidity'), isFalse);
      expect(state.summary!.currentDiscountTotal, 300);
      expect(state.summary!.cardTotal, 5700);
      expect(state.summary!.remainingLiquidity, 5300);
      expect(state.usesConservativeCardEstimate, isFalse);
      expect(state.expenseEntries.single.effectiveAmount, 4700);

      final bundle = await state.loadReconciliationBundle();
      final bundledPayload = bundle!.operations.single.payload;
      expect(bundledPayload['discount_override_amount'], 300);
      expect(bundledPayload.containsKey('effective_amount_value'), isFalse);
    });

    test('cash-flow estimate includes device-local today and excludes future',
        () {
      final projection = OfflineProjection.from(
          baselineFixture(),
          [
            OfflineJournalOperation(
              operationId: 'today',
              type: OfflineOperationType.createCashFlow,
              payload: const {
                'occurred_on': '2026-09-17',
                'title': '오늘 입금',
                'amount_value': 500,
                'is_primary_income': 0,
              },
              createdAt: DateTime.utc(2026, 9, 17),
              sequence: 1,
            ),
            OfflineJournalOperation(
              operationId: 'future',
              type: OfflineOperationType.createCashFlow,
              payload: const {
                'occurred_on': '2026-09-18',
                'title': '미래 입금',
                'amount_value': 700,
                'is_primary_income': 0,
              },
              createdAt: DateTime.utc(2026, 9, 17),
              sequence: 2,
            ),
          ],
          projectedAt: DateTime(2026, 9, 17, 12));

      expect(projection.summary.cashFlowBalance, 5500);
      expect(projection.summary.remainingLiquidity, 10500);
      expect(projection.cashFlows, hasLength(2));
    });

    test('offline settings changes remain unavailable and are not journaled',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      await state.updateSetting('scheduled_income', '1');

      expect(state.statusMessage, contains('온라인에서만'));
      expect(state.settings.values['scheduled_income'], '100000');
      expect(state.offlineJournal, isEmpty);
      expect(await store.loadJournal(), isEmpty);
    });

    test('approved writes append authoritative inputs and update estimates',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(
        directory,
        clock: () => DateTime.utc(2026, 9, 17, 5),
      );
      await store.replaceBaseline(baselineFixture());
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      expect(
        await state.createExpense(
          usagePlace: '가게',
          usageItem: '식사',
          amount: 100,
          discountEnabled: true,
          entryDate: '2026-09-01',
        ),
        isTrue,
      );
      await state.createCashFlow(
        occurredOn: '2026-09-01',
        title: '현금 입금',
        amount: 500,
        isIncome: true,
        isPrimaryIncome: false,
      );
      await state.createCashFlow(
        occurredOn: '2026-09-01',
        title: '현금 출금',
        amount: 200,
        isIncome: false,
        isPrimaryIncome: false,
      );
      await state.confirmFixedPanel(30, '2026-09-01', 800);
      await state.confirmPlannedEntry(20, '2026-09-01', 1200);

      expect(state.offlineJournal, hasLength(5));
      expect(
        state.offlineJournal.map((operation) => operation.type).toSet(),
        {
          OfflineOperationType.createCardExpense,
          OfflineOperationType.createCashFlow,
          OfflineOperationType.confirmFixedExpense,
          OfflineOperationType.confirmPlannedCardExpense,
        },
      );
      expect(state.summary!.remainingLiquidity, 10701);
      expect(state.summary!.fixedCashProcessedTotal, 800);
      expect(state.summary!.fixedCashTotal, 1000);
      expect(state.financialValuesAreEstimated, isTrue);
      expect(state.usesConservativeCardEstimate, isTrue);
      expect(state.expenseEntries.where((entry) => entry.isOfflinePending),
          hasLength(2));
      expect(
          state.cashFlows.where((flow) => flow.isOfflinePending), hasLength(3));
      expect(
        state.offlineJournal.every((operation) =>
            !operation.payload.containsKey('remaining_liquidity') &&
            !operation.payload.containsKey('effective_amount_value')),
        isTrue,
      );

      final beforeClose = state.offlineJournal.length;
      await state.closeCurrentMonth(targetMonth: '2026-09');
      expect(state.offlineJournal, hasLength(beforeClose));
      expect(state.statusMessage, contains('온라인에서만'));
      expect(
          (await offlineStoreFixture(directory).loadJournal()), hasLength(5));
    });

    test(
        'offline fixed confirmation preserves next-cycle reserve in displayed spendable',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory,
          clock: () => DateTime.utc(2026, 9, 17, 5));
      await store.replaceBaseline(baselineFixture(
          remainingLiquidity: 10000, currentMonthSpendable: 10000));
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      expect(await state.confirmFixedPanel(30, '2026-09-17', 800), isTrue);

      expect(state.summary!.remainingLiquidity, 10200);
      expect(state.summary!.currentMonthSpendable, 9200);
      expect(state.summary!.fixedCashProcessedTotal, 800);
    });

    test(
        'offline refresh and restart use health only, then require reconciliation',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
          ));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-01',
          'title': '입금',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );

      final unavailableApi = OfflineApiFake();
      final restarted = AppState(unavailableApi,
          offlineStore: offlineStoreFixture(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
      expect(restarted.isOffline, isTrue);
      expect(restarted.offlineJournal, hasLength(1));
      expect(unavailableApi.healthCalls, 1);
      expect(unavailableApi.stateFetchCalls, 0);

      restarted.isBootstrapping = false;
      await restarted.resumeFromBackground();
      expect(restarted.isOffline, isTrue);
      expect(unavailableApi.healthCalls, 2);
      expect(unavailableApi.stateFetchCalls, 0);

      await restarted.refresh();
      expect(restarted.isOffline, isTrue);
      expect(unavailableApi.healthCalls, 3);
      expect(unavailableApi.stateFetchCalls, 0);

      final recoveredApi = OfflineApiFake()..available = true;
      final recovered =
          AppState(recoveredApi, offlineStore: offlineStoreFixture(directory));
      expect(await recovered.restorePersistedOfflineWorkspace(), isTrue);
      expect(recovered.isReconciliationRequired, isTrue);
      expect(recoveredApi.healthCalls, 1);
      expect(recoveredApi.stateFetchCalls, 0);
      expect(recovered.canCreateCashFlow, isFalse);

      final journalCount = recovered.offlineJournal.length;
      await recovered.createCashFlow(
        occurredOn: '2026-09-01',
        title: '금지된 쓰기',
        amount: 1,
        isIncome: true,
        isPrimaryIncome: false,
      );
      expect(recovered.offlineJournal, hasLength(journalCount));
      expect(recovered.statusMessage, contains('조정을 완료'));
    });

    test('reconciliation choice is persisted without replay or cleanup',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.reconciliationRequired,
          ));
      await store.appendOperation(
        type: OfflineOperationType.createCardExpense,
        payload: const {
          'entry_date': '2026-09-01',
          'usage_place': '가게',
          'amount_value': 100,
        },
      );
      final api = OfflineApiFake()..available = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();

      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );

      final bundle = await state.loadReconciliationBundle();
      expect(bundle!.choice, ReconciliationChoice.applyToServer);
      expect(bundle.operations, hasLength(1));
      expect(state.isReconciliationRequired, isTrue);
      expect(await store.loadBaseline(), isNotNull);
      expect(await store.loadJournal(), hasLength(1));

      final restarted =
          AppState(api, offlineStore: offlineStoreFixture(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
      expect(
          restarted.reconciliationChoice, ReconciliationChoice.applyToServer);
      expect(restarted.reconciliationRecoveryReady, isTrue);
      expect(api.mobileWinsCalls, 0);
      expect(api.stateFetchCalls, 0);
      expect(await store.loadJournal(), hasLength(1));
    });
    test('untrusted complete journal corruption fails closed on restart',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
          ));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '정상',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      final journal = File('${directory.path}/offline-mode/journal.ndjson');
      await journal.writeAsString('not-json\n',
          mode: FileMode.append, flush: true);
      final before = await journal.readAsBytes();

      final api = OfflineApiFake()..available = true;
      final state = AppState(api, offlineStore: offlineStoreFixture(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(state.isOnline, isFalse);
      expect(state.canCreateCashFlow, isFalse);

      expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '금지',
          amount: 1,
          isIncome: true,
          isPrimaryIncome: false,
        ),
        isFalse,
      );
      await state.refresh();
      expect(api.stateFetchCalls, 0);
      expect(await journal.readAsBytes(), before);
    });

    test('finalizing reconciliation rejects ordinary Offline re-entry',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '대기 중',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await saveCommittedFixture(store, 'reconcile-finalizing-identity');
      final state = AppState(OfflineApiFake(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isReconciliationFinalizing, isTrue);

      expect(await state.enterOfflineMode(), isFalse);
      final metadata = await store.loadMetadata();
      expect(metadata.mode, ConnectivityMode.reconciliationFinalizing);
      expect(metadata.reconciliationId, 'reconcile-finalizing-identity');
      expect(await store.loadJournal(), hasLength(1));
    });
  });
}
