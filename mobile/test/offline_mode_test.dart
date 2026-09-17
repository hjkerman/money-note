import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

OfflineBaseline _baseline({int remainingLiquidity = 10000}) {
  return OfflineBaseline(
    syncedAt: DateTime.utc(2026, 9, 17, 3, 14),
    user: AuthUser(
      id: 1,
      username: 'owner',
      displayName: 'Owner',
      sharePinNeedsChange: false,
    ),
    summary: Summary(
      scheduledIncome: 100000,
      cardTotal: 1000,
      currentSpendingTotal: 1000,
      currentDiscountTotal: 0,
      plannedRecurringTotal: 1500,
      fixedCashTotal: 1000,
      frozenAssetTotal: 0,
      cashFlowBalance: 5000,
      remainingLiquidity: remainingLiquidity,
      claimOriginalTotal: 0,
      claimNetTotal: 0,
      familyCardOriginalTotal: 0,
      familyCardNetTotal: 0,
      visibleCashFlowTotal: 5000,
    ),
    cardPaymentStatus: CardPaymentStatus(effectiveRemainingTotal: 0),
    judgment: JudgmentState(
      budget: JudgmentTone(message: 'budget'),
      credit: JudgmentTone(message: 'credit'),
      payment: JudgmentTone(message: 'payment'),
    ),
    monthCloseStatus: MonthCloseStatus(
      calendarDate: '2026-09-17',
      calendarMonth: '2026-09',
      needsClose: false,
      isEarlyClose: false,
      earlyCloseAvailable: false,
      earlyCloseStartDay: 25,
      canClose: true,
      oldestOpenMonth: '2026-09',
    ),
    settings: AppSettings(values: const {
      'owner_card_last4': '1234',
      'family_card_last4': '5678',
      'scheduled_income': '100000',
    }),
    ownerDiscountMonth:
        CardDiscountMonth(month: '2026-09', scope: 'owner', policy: 'enabled'),
    familyDiscountMonth:
        CardDiscountMonth(month: '2026-09', scope: 'family', policy: 'enabled'),
    transitDiscountProfile:
        TransitDiscountProfileStatus(month: '2026-09', profile: 'owner'),
    entries: [
      LedgerEntry(
        id: 20,
        bookSection: 'current',
        entryKind: 'planned',
        title: '[통신사] 요금',
        sortOrder: 1,
        usagePlace: '통신사',
        usageItem: '요금',
        amountValue: 1500,
        dueDay: 10,
      ),
    ],
    confirmedPlannedEntries: const [],
    panels: [
      MonthlyPanel(
        id: 30,
        month: '2026-09',
        panelType: 'fixed',
        title: '관리비',
        sortOrder: 1,
        discountAmount: 0,
        discountOverride: 0,
        amountValue: 1000,
      ),
    ],
    cashFlows: const [],
  );
}

Future<Directory> _temporaryDirectory() async {
  final directory = await Directory.systemTemp.createTemp('money-note-offline-');
  addTearDown(() async {
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  });
  return directory;
}

OfflineStore _store(
  Directory directory, {
  DateTime Function()? clock,
}) {
  return OfflineStore(
    directoryProvider: () async => directory,
    clock: clock,
  );
}

class _OfflineApi extends MoneyNoteApiClient {
  _OfflineApi() : super(baseUrl: 'https://example.invalid');

  bool available = false;
  bool failJudgment = false;
  int healthCalls = 0;
  int stateFetchCalls = 0;
  int remainingLiquidity = 10000;

  @override
  Future<void> health() async {
    healthCalls += 1;
    if (!available) {
      throw MoneyNoteConnectionException('서버에 연결할 수 없습니다.');
    }
  }

  @override
  Future<Summary> summary() async {
    stateFetchCalls += 1;
    return _baseline(remainingLiquidity: remainingLiquidity).summary;
  }

  @override
  Future<CardPaymentStatus> currentCardPaymentStatus() async {
    stateFetchCalls += 1;
    return _baseline().cardPaymentStatus;
  }

  @override
  Future<JudgmentState> judgment() async {
    stateFetchCalls += 1;
    if (failJudgment) throw StateError('incomplete refresh');
    return _baseline().judgment;
  }

  @override
  Future<List<LedgerEntry>> currentEntries() async {
    stateFetchCalls += 1;
    return _baseline().entries;
  }

  @override
  Future<List<LedgerEntry>> confirmedPlannedEntries() async {
    stateFetchCalls += 1;
    return const [];
  }

  @override
  Future<List<MonthlyPanel>> currentPanels() async {
    stateFetchCalls += 1;
    return _baseline().panels;
  }

  @override
  Future<List<CashFlow>> cashFlows({
    String? dateFrom,
    String? dateTo,
    int? limit,
  }) async {
    stateFetchCalls += 1;
    return const [];
  }

  @override
  Future<AppSettings> settings() async {
    stateFetchCalls += 1;
    return _baseline().settings;
  }

  @override
  Future<MonthCloseStatus> monthCloseStatus() async {
    stateFetchCalls += 1;
    return _baseline().monthCloseStatus;
  }

  @override
  Future<CardDiscountMonth> discountMonth(String month, String scope) async {
    stateFetchCalls += 1;
    return scope == 'owner'
        ? _baseline().ownerDiscountMonth
        : _baseline().familyDiscountMonth;
  }

  @override
  Future<TransitDiscountProfileStatus> transitDiscountProfile(
      String month) async {
    stateFetchCalls += 1;
    return _baseline().transitDiscountProfile;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('durable offline store', () {
    test('baseline is atomically replaced and survives a new store instance',
        () async {
      final directory = await _temporaryDirectory();
      final firstStore = _store(directory);
      await firstStore.replaceBaseline(_baseline(remainingLiquidity: 10000));
      expect((await firstStore.loadBaseline())!.summary.remainingLiquidity,
          10000);

      await firstStore.replaceBaseline(_baseline(remainingLiquidity: 9000));
      final restartedStore = _store(directory);
      final restored = await restartedStore.loadBaseline();

      expect(restored!.summary.remainingLiquidity, 9000);
      expect(restored.syncedAt, DateTime.utc(2026, 9, 17, 3, 14));
      expect(restored.user.sessionToken, isNull);
      expect(
        directory
            .listSync(recursive: true)
            .whereType<File>()
            .where((file) => file.path.endsWith('.tmp')),
        isEmpty,
      );
    });

    test('journal is append-only, ordered, durable, and rejects derived values',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(
        directory,
        clock: () => DateTime.utc(2026, 9, 17, 4),
      );

      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-01',
          'title': '입금',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      await store.appendOperation(
        type: OfflineOperationType.createCardExpense,
        payload: const {
          'entry_date': '2026-09-01',
          'usage_place': '가게',
          'amount_value': 100,
        },
      );

      final restored = await _store(directory).loadJournal();
      expect(restored.map((operation) => operation.sequence), [1, 2]);
      expect(restored.map((operation) => operation.operationId).toSet(),
          hasLength(2));
      expect(restored.every((operation) => operation.status == 'pending'),
          isTrue);
      await expectLater(
        store.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: const {'remaining_liquidity': 1},
        ),
        throwsArgumentError,
      );

      final journal = File(
          '${directory.path}/offline-mode/journal.ndjson');
      await journal.writeAsString(
        'interrupted-json-row',
        mode: FileMode.append,
        flush: true,
      );
      await _store(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-02',
          'title': '재시작 후 입금',
          'amount_value': 200,
          'is_primary_income': 0,
        },
      );
      expect(await _store(directory).loadJournal(), hasLength(3));

      final rows = const LineSplitter()
          .convert(await journal.readAsString())
          .map((line) => jsonDecode(line) as Map<String, dynamic>);
      expect(
        rows.every((row) {
          final payload = row['payload'] as Map<String, dynamic>;
          return !payload.containsKey('remaining_liquidity') &&
              !payload.containsKey('effective_amount_value');
        }),
        isTrue,
      );
    });
  });

  group('offline state machine and projection', () {
    test('no baseline rejects deliberate offline entry', () async {
      final directory = await _temporaryDirectory();
      final state = AppState(_OfflineApi(), offlineStore: _store(directory));

      expect(await state.enterOfflineMode(), isFalse);
      expect(state.isOnline, isTrue);
      expect(state.offlineEntryMessage, contains('한 번 동기화'));
    });

    test('approved writes append authoritative inputs and update estimates',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(
        directory,
        clock: () => DateTime.utc(2026, 9, 17, 5),
      );
      await store.replaceBaseline(_baseline());
      final state = AppState(_OfflineApi(), offlineStore: store);
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
      expect(state.summary!.remainingLiquidity, 10700);
      expect(state.financialValuesAreEstimated, isTrue);
      expect(state.usesConservativeCardEstimate, isTrue);
      expect(state.expenseEntries.where((entry) => entry.isOfflinePending),
          hasLength(2));
      expect(state.cashFlows.where((flow) => flow.isOfflinePending),
          hasLength(3));
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
      expect((await _store(directory).loadJournal()), hasLength(5));
    });

    test('offline refresh and restart use health only, then require reconciliation',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
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

      final unavailableApi = _OfflineApi();
      final restarted = AppState(unavailableApi, offlineStore: _store(directory));
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

      final recoveredApi = _OfflineApi()..available = true;
      final recovered =
          AppState(recoveredApi, offlineStore: _store(directory));
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
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
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
      final api = _OfflineApi()..available = true;
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
    });
  });

  group('online refresh baseline and connection classification', () {
    test('successful refresh replaces baseline; incomplete refresh preserves it',
        () async {
      final directory = await _temporaryDirectory();
      final api = _OfflineApi()..available = true;
      final store = _store(directory);
      final state = AppState(api, offlineStore: store)
        ..user = _baseline().user;

      await state.refresh();
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 10000);

      api.remainingLiquidity = 9000;
      await state.refresh();
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 9000);

      api.remainingLiquidity = 8000;
      api.failJudgment = true;
      await expectLater(state.refresh(), throwsStateError);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 9000);
    });

    test('transport failure prompts, but application validation error does not',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final unavailableClient = MockClient((request) async {
        throw http.ClientException('offline', request.url);
      });
      final unavailableApi = MoneyNoteApiClient(
        client: unavailableClient,
        baseUrl: 'https://example.invalid',
      );
      final unavailableState = AppState(unavailableApi, offlineStore: store);
      await expectLater(
        unavailableApi.summary(),
        throwsA(isA<MoneyNoteConnectionException>()),
      );
      expect(unavailableState.serverFailurePromptPending, isTrue);
      expect(await unavailableState.enterOfflineMode(), isTrue);
      expect(unavailableState.isOffline, isTrue);

      final validationApi = MoneyNoteApiClient(
        client: MockClient((request) async => http.Response(
              jsonEncode({'detail': 'invalid amount'}),
              422,
              headers: {'content-type': 'application/json'},
            )),
        baseUrl: 'https://example.invalid',
      );
      final validationState = AppState(validationApi);
      await expectLater(
        validationApi.summary(),
        throwsA(isA<MoneyNoteApiException>()),
      );
      expect(validationState.serverFailurePromptPending, isFalse);
    });
  });

  testWidgets('server failure prompt offers offline mode and app exit',
      (tester) async {
    final directory = await _temporaryDirectory();
    final state = AppState(
      _OfflineApi(), offlineStore: _store(directory),
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

    await tester.tap(find.text('오프라인 모드 사용'));
    await tester.pumpAndSettle();
    expect(find.text('온라인 상태에서 한 번 동기화가 필요합니다.'), findsOneWidget);

    await tester.tap(find.text('앱 종료'));
    await tester.pump();
    expect(
      platformCalls.any((call) => call.method == 'SystemNavigator.pop'),
      isTrue,
    );
  });

  testWidgets('offline shell keeps banner and estimated financial labels visible',
      (tester) async {
    final directory = await _temporaryDirectory();
    final store = _store(directory);
    await store.replaceBaseline(_baseline());
    final state = AppState(_OfflineApi(), offlineStore: store);
    expect(await state.enterOfflineMode(), isTrue);
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

  testWidgets('reconciliation boundary is read-only and requires an explicit choice',
      (tester) async {
    final directory = await _temporaryDirectory();
    final store = _store(directory);
    await store.replaceBaseline(_baseline());
    await store.saveMetadata(const OfflineWorkspaceMetadata(
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
    final state = AppState(
      _OfflineApi()..available = true,
      offlineStore: store,
    );
    await state.restorePersistedOfflineWorkspace();
    state.isBootstrapping = false;
    addTearDown(state.dispose);

    await tester.pumpWidget(MoneyNoteApp(
      stateOverride: state,
      bootstrapOnStart: false,
    ));
    expect(find.text('오프라인 변경사항을 서버에 적용'), findsOneWidget);
    expect(find.text('오프라인 변경사항을 폐기하고 서버 데이터 사용'), findsOneWidget);

    await tester.tap(find.text('오프라인 변경사항을 서버에 적용'));
    await tester.pumpAndSettle();
    expect(state.reconciliationChoice, ReconciliationChoice.applyToServer);
    expect(state.isReconciliationRequired, isTrue);
    expect(await store.loadJournal(), hasLength(1));
    expect(find.textContaining('Phase 2'), findsOneWidget);
  });
}
