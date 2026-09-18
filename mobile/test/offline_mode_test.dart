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
import 'package:money_note_mobile/src/offline/offline_projection.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

CardDiscountProjectionPolicy _flatProjectionPolicy(String scope) {
  return CardDiscountProjectionPolicy(
    schemaVersion: 1,
    policyId: '$scope-flat-statement-1.2',
    type: 'flat_statement',
    rounding: 'floor',
    rate: '0.012',
  );
}

OfflineBaseline _baseline({
  int remainingLiquidity = 10000,
  bool includeProjectionPolicy = true,
  bool includeAuthority = true,
}) {
  return OfflineBaseline(
    syncedAt: DateTime.utc(2026, 9, 17, 3, 14),
    authoritativeSnapshot: includeAuthority
        ? const {
            'schema_version': 2,
            'exported_at': '2026-09-17T03:14:00Z',
            'data': <String, dynamic>{},
          }
        : null,
    serverStateFingerprint: includeAuthority
        ? 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        : null,
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
    ownerDiscountMonth: CardDiscountMonth(
      month: '2026-09',
      scope: 'owner',
      policy: 'enabled',
      projectionPolicy:
          includeProjectionPolicy ? _flatProjectionPolicy('owner') : null,
    ),
    familyDiscountMonth: CardDiscountMonth(
      month: '2026-09',
      scope: 'family',
      policy: 'enabled',
      projectionPolicy:
          includeProjectionPolicy ? _flatProjectionPolicy('family') : null,
    ),
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
  final directory =
      await Directory.systemTemp.createTemp('money-note-offline-');
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
  bool failServerRecovery = false;
  bool serverChanged = false;
  bool committed = false;
  bool loseMobileWinsResponse = false;
  bool failMobileWinsBeforeCommit = false;
  int mobileWinsCalls = 0;
  int reconciliationStatusCalls = 0;

  static const currentFingerprint =
      'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';

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

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async => {
        'snapshot': const {
          'schema_version': 2,
          'exported_at': '2026-09-17T03:14:00Z',
          'data': <String, dynamic>{},
        },
        'state_fingerprint':
            committed ? currentFingerprint : _baseline().serverStateFingerprint,
      };

  @override
  Future<Map<String, dynamic>> createOfflineServerRecovery({
    required String reconciliationId,
    required String baselineFingerprint,
  }) async {
    if (failServerRecovery) {
      throw MoneyNoteApiException('server recovery failed');
    }
    return {
      'server_artifact_filename':
          'pre_reconcile_server-20260917-$reconciliationId.money-note-snapshot.json',
      'current_server_fingerprint':
          serverChanged ? currentFingerprint : baselineFingerprint,
      'server_changed': serverChanged,
    };
  }

  @override
  Future<Map<String, dynamic>> reconcileOfflineMobileWins({
    required String reconciliationId,
    required String baselineFingerprint,
    required Map<String, dynamic> baselineSnapshot,
    required List<Map<String, dynamic>> operations,
    required String mobileArtifactSha256,
    required String expectedServerFingerprint,
    required bool confirmServerChanged,
    required String password,
  }) async {
    mobileWinsCalls += 1;
    if (failMobileWinsBeforeCommit) {
      throw MoneyNoteConnectionException('request failed before commit');
    }
    committed = true;
    if (loseMobileWinsResponse) {
      throw MoneyNoteConnectionException('response lost');
    }
    return {
      'status': 'committed',
      'reconciliation_id': reconciliationId,
    };
  }

  @override
  Future<Map<String, dynamic>> offlineReconciliationStatus({
    required String baselineFingerprint,
    String? reconciliationId,
  }) async {
    reconciliationStatusCalls += 1;
    return {
      'server_changed': serverChanged,
      'current_server_fingerprint': currentFingerprint,
      'reconciliation': committed
          ? {
              'status': 'committed',
              'reconciliation_id': reconciliationId,
            }
          : null,
    };
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
      expect(
          (await firstStore.loadBaseline())!.summary.remainingLiquidity, 10000);

      await firstStore.replaceBaseline(_baseline(remainingLiquidity: 9000));
      final restartedStore = _store(directory);
      final restored = await restartedStore.loadBaseline();

      expect(restored!.summary.remainingLiquidity, 9000);
      expect(restored.syncedAt, DateTime.utc(2026, 9, 17, 3, 14));
      expect(restored.user.sessionToken, isNull);
      expect(
        restored.ownerDiscountMonth.projectionPolicy!.rate,
        '0.012',
      );
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
      expect(
          restored.every((operation) => operation.status == 'pending'), isTrue);
      await expectLater(
        store.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: const {'remaining_liquidity': 1},
        ),
        throwsArgumentError,
      );

      final journal = File('${directory.path}/offline-mode/journal.ndjson');
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

    test('offline card use without override keeps baseline discount intent',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final state = AppState(_OfflineApi(), offlineStore: store);
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
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(
        _baseline(includeProjectionPolicy: false),
      );
      final state = AppState(_OfflineApi(), offlineStore: store);
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
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final state = AppState(_OfflineApi(), offlineStore: store);
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
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final state = AppState(_OfflineApi(), offlineStore: store);
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
          _baseline(),
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
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);

      await state.updateSetting('scheduled_income', '1');

      expect(state.statusMessage, contains('온라인에서만'));
      expect(state.settings.values['scheduled_income'], '100000');
      expect(state.offlineJournal, isEmpty);
      expect(await store.loadJournal(), isEmpty);
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
      expect(state.summary!.remainingLiquidity, 10701);
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
      expect((await _store(directory).loadJournal()), hasLength(5));
    });

    test(
        'offline refresh and restart use health only, then require reconciliation',
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
      final restarted =
          AppState(unavailableApi, offlineStore: _store(directory));
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
      final recovered = AppState(recoveredApi, offlineStore: _store(directory));
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

      final restarted = AppState(api, offlineStore: _store(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
      expect(
          restarted.reconciliationChoice, ReconciliationChoice.applyToServer);
      expect(restarted.reconciliationRecoveryReady, isTrue);
      expect(api.mobileWinsCalls, 0);
      expect(api.stateFetchCalls, 0);
      expect(await store.loadJournal(), hasLength(1));
    });
  });

  group('online refresh baseline and connection classification', () {
    test(
        'successful refresh replaces baseline; incomplete refresh preserves it',
        () async {
      final directory = await _temporaryDirectory();
      final api = _OfflineApi()..available = true;
      final store = _store(directory);
      final state = AppState(api, offlineStore: store)..user = _baseline().user;

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
    final directory = (await tester.runAsync(_temporaryDirectory))!;
    final state = AppState(
      _OfflineApi(),
      offlineStore: _store(directory),
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
    final directory = (await tester.runAsync(_temporaryDirectory))!;
    final store = _store(directory);
    await tester.runAsync(() => store.replaceBaseline(_baseline()));
    final state = AppState(_OfflineApi(), offlineStore: store);
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
    final directory = (await tester.runAsync(_temporaryDirectory))!;
    final store = _store(directory);
    await tester.runAsync(() => store.replaceBaseline(_baseline()));
    await tester
        .runAsync(() => store.saveMetadata(const OfflineWorkspaceMetadata(
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
      _OfflineApi()..available = true,
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
    final directory = (await tester.runAsync(_temporaryDirectory))!;
    final store = _store(directory);
    await tester.runAsync(() => store.replaceBaseline(_baseline()));
    await tester.runAsync(() => store.saveMetadata(
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
      _OfflineApi()
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

  group('Phase 2 reconciliation recovery', () {
    test('same timestamp recovery retries never overwrite an artifact',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(
        directory,
        clock: () => DateTime.utc(2026, 9, 18, 1, 2, 3),
      );
      final baseline = _baseline();
      await store.replaceBaseline(baseline);
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-01',
          'title': '입금',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      const metadata = OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
        reconciliationChoice: ReconciliationChoice.applyToServer,
        reconciliationId: 'reconcile-immutable-0001',
        phase: ReconciliationPhase.preparing,
      );
      final operations = await store.loadJournal();

      final first = await store.createMobileRecoveryArtifact(
        baseline: baseline,
        operations: operations,
        metadata: metadata,
      );
      final second = await store.createMobileRecoveryArtifact(
        baseline: baseline,
        operations: operations,
        metadata: metadata,
      );

      expect(second.filename, isNot(first.filename));
      expect(await store.listMobileRecoveryArtifacts(), hasLength(2));
      expect(
        await store.verifyMobileRecoveryArtifact(first.filename),
        first.sha256,
      );
      expect(
        await store.verifyMobileRecoveryArtifact(second.filename),
        second.sha256,
      );
    });

    test('server recovery failure prevents destructive reconciliation',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
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
      final api = _OfflineApi()
        ..available = true
        ..failServerRecovery = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();

      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );

      expect(await state.reconcileMobileWins(password: 'password'), isFalse);
      expect(api.mobileWinsCalls, 0);
      expect(await store.loadJournal(), hasLength(1));
      expect(await store.listMobileRecoveryArtifacts(), isEmpty);
      expect(state.isReconciliationRequired, isTrue);
    });

    test('mobile recovery failure prevents destructive reconciliation',
        () async {
      final directory = await _temporaryDirectory();
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeMobileRecoveryWrite: () async {
          throw const OfflinePersistenceException('injected write failure');
        },
      );
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
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
      final api = _OfflineApi()..available = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();

      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );

      expect(await state.reconcileMobileWins(password: 'password'), isFalse);
      expect(api.mobileWinsCalls, 0);
      expect(await store.loadJournal(), hasLength(1));
      expect(await store.listMobileRecoveryArtifacts(), isEmpty);
      expect(state.isReconciliationRequired, isTrue);
    });

    test('legacy baseline blocks Mobile Wins but preserves safe Server Wins',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(includeAuthority: false));
      await store.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
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
      final api = _OfflineApi()..available = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();

      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );
      expect(state.statusMessage, contains('Mobile Wins를 안전하게 실행할 수 없습니다'));
      expect(api.mobileWinsCalls, 0);
      expect(await store.listMobileRecoveryArtifacts(), isEmpty);

      await state.selectReconciliationChoice(
        ReconciliationChoice.discardAndUseServer,
      );
      final ready = await store.loadMetadata();
      expect(ready.phase, ReconciliationPhase.ready);
      expect(ready.serverChanged, isTrue);
      expect(ready.hasVerifiedRecoveryPoints, isTrue);
      expect(await store.loadJournal(), hasLength(1));

      expect(await state.reconcileServerWins(), isTrue);
      expect(state.isOnline, isTrue);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
    });

    test('persisted recovery preparation resumes after restart', () async {
      final directory = await _temporaryDirectory();
      final failingStore = OfflineStore(
        directoryProvider: () async => directory,
        beforeMobileRecoveryWrite: () async {
          throw const OfflinePersistenceException('injected write failure');
        },
      );
      await failingStore.replaceBaseline(_baseline());
      await failingStore.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
      ));
      await failingStore.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-01',
          'title': '입금',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      final api = _OfflineApi()..available = true;
      final state = AppState(api, offlineStore: failingStore);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );
      final reconciliationId =
          (await failingStore.loadMetadata()).reconciliationId;

      final restartedStore = _store(directory);
      final restarted = AppState(api, offlineStore: restartedStore);
      await restarted.restorePersistedOfflineWorkspace();
      final resumed = await restartedStore.loadMetadata();

      expect(resumed.reconciliationId, reconciliationId);
      expect(resumed.phase, ReconciliationPhase.ready);
      expect(resumed.hasVerifiedRecoveryPoints, isTrue);
      expect(await restartedStore.loadJournal(), hasLength(1));
      expect(
        await restartedStore.listMobileRecoveryArtifacts(),
        hasLength(1),
      );
      expect(restarted.isReconciliationRequired, isTrue);
    });

    test('mobile recovery bundle is immutable and detects corruption',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
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
      final state = AppState(
        _OfflineApi()..available = true,
        offlineStore: store,
      );
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );
      final metadata = await store.loadMetadata();
      final artifacts = await store.listMobileRecoveryArtifacts();
      final baseline = await store.loadBaseline();
      final operations = await store.loadJournal();

      expect(metadata.mobileArtifactFilename, isNotNull);
      expect(artifacts, hasLength(1));
      expect(
        await store.verifyMobileRecoveryArtifact(
          metadata.mobileArtifactFilename!,
          expectedReconciliationId: metadata.reconciliationId,
          expectedBaseline: baseline,
          expectedOperations: operations,
        ),
        metadata.mobileArtifactSha256,
      );
      await expectLater(
        store.verifyMobileRecoveryArtifact(
          metadata.mobileArtifactFilename!,
          expectedReconciliationId: 'reconcile-different-lineage',
          expectedBaseline: baseline,
          expectedOperations: operations,
        ),
        throwsA(isA<OfflinePersistenceException>()),
      );
      await expectLater(
        store.verifyMobileRecoveryArtifact(
          metadata.mobileArtifactFilename!,
          expectedReconciliationId: metadata.reconciliationId,
          expectedBaseline: _baseline(remainingLiquidity: 99999),
          expectedOperations: operations,
        ),
        throwsA(isA<OfflinePersistenceException>()),
      );

      await artifacts.single.writeAsString(
        'corrupt',
        mode: FileMode.append,
        flush: true,
      );
      await expectLater(
        store.verifyMobileRecoveryArtifact(metadata.mobileArtifactFilename!),
        throwsA(isA<OfflinePersistenceException>()),
      );
      expect(await store.loadJournal(), hasLength(1));
    });

    test('commit response loss resumes by status without duplicate replay',
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
      final api = _OfflineApi()
        ..available = true
        ..loseMobileWinsResponse = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );

      expect(
        await state.reconcileMobileWins(password: 'password'),
        isFalse,
      );
      expect(state.isReconciliationFinalizing, isTrue);
      expect(state.mobileCommitIsUnknown, isTrue);
      expect(api.mobileWinsCalls, 1);
      expect(await store.loadJournal(), hasLength(1));

      final restarted = AppState(api, offlineStore: _store(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);

      expect(restarted.isOnline, isTrue);
      expect(api.reconciliationStatusCalls, 1);
      expect(api.mobileWinsCalls, 1);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
      expect((await store.loadBaseline())!.serverStateFingerprint,
          _OfflineApi.currentFingerprint);
    });
    test('cleanup-boundary crash never replays a committed journal', () async {
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
      final api = _OfflineApi()
        ..available = true
        ..loseMobileWinsResponse = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );
      expect(
        await state.reconcileMobileWins(password: 'password'),
        isFalse,
      );
      final pending = await store.loadMetadata();
      await store.saveMetadata(OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationFinalizing,
        reconciliationChoice: ReconciliationChoice.applyToServer,
        reconciliationId: pending.reconciliationId,
        phase: ReconciliationPhase.mobileCommitted,
        serverCommitStatus: ServerCommitStatus.committed,
        serverChanged: pending.serverChanged,
        currentServerFingerprint: pending.currentServerFingerprint,
        serverArtifactFilename: pending.serverArtifactFilename,
        mobileArtifactFilename: pending.mobileArtifactFilename,
        mobileArtifactSha256: pending.mobileArtifactSha256,
        confirmServerChanged: pending.confirmServerChanged,
      ));
      await store.deleteJournal();

      final restarted = AppState(api, offlineStore: _store(directory));
      await restarted.restorePersistedOfflineWorkspace();

      expect(restarted.isOnline, isTrue);
      expect(api.mobileWinsCalls, 1);
      expect(api.reconciliationStatusCalls, 0);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
    });

    test('uncommitted request restarts with the same persisted choice and id',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
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
      final api = _OfflineApi()
        ..available = true
        ..failMobileWinsBeforeCommit = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );
      final reconciliationId = (await store.loadMetadata()).reconciliationId;

      expect(
        await state.reconcileMobileWins(password: 'password'),
        isFalse,
      );
      expect(api.committed, isFalse);

      final restarted = AppState(api, offlineStore: _store(directory));
      await restarted.restorePersistedOfflineWorkspace();
      expect(restarted.isReconciliationFinalizing, isTrue);
      expect(
          restarted.reconciliationChoice, ReconciliationChoice.applyToServer);
      expect((await store.loadMetadata()).reconciliationId, reconciliationId);
      expect(await store.loadJournal(), hasLength(1));

      api.failMobileWinsBeforeCommit = false;
      expect(
        await restarted.resumeReconciliationFinalization(
          password: 'password',
        ),
        isTrue,
      );
      expect(api.mobileWinsCalls, 2);
      expect(restarted.isOnline, isTrue);
      expect(await store.loadJournal(), isEmpty);
    });

    test('post-commit sync failure preserves journal until restart finalizes',
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
      api.failJudgment = true;

      expect(
        await state.reconcileMobileWins(password: 'password'),
        isFalse,
      );
      expect(state.isReconciliationFinalizing, isTrue);
      expect(state.mobileCommitIsCommitted, isTrue);
      expect(api.mobileWinsCalls, 1);
      expect(await store.loadJournal(), hasLength(1));

      api.failJudgment = false;
      final restarted = AppState(api, offlineStore: _store(directory));
      await restarted.restorePersistedOfflineWorkspace();

      expect(restarted.isOnline, isTrue);
      expect(api.mobileWinsCalls, 1);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
    });

    test(
        'Server Wins fetch failure preserves offline state and restart progress',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.saveMetadata(const OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationRequired,
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
      final api = _OfflineApi()..available = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.discardAndUseServer,
      );
      api.failJudgment = true;

      expect(await state.reconcileServerWins(), isFalse);
      expect(state.isReconciliationFinalizing, isTrue);
      expect(state.summary!.remainingLiquidity, 10500);
      expect(await store.loadJournal(), hasLength(1));

      final restarted = AppState(api, offlineStore: _store(directory));
      await restarted.restorePersistedOfflineWorkspace();
      expect(restarted.isReconciliationFinalizing, isTrue);
      expect(await store.loadJournal(), hasLength(1));

      api.failJudgment = false;
      expect(
        await restarted.resumeReconciliationFinalization(),
        isTrue,
      );
      expect(restarted.isOnline, isTrue);
      expect(api.mobileWinsCalls, 0);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
    });

    test('server change requires additional Mobile Wins confirmation',
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
      final api = _OfflineApi()
        ..available = true
        ..serverChanged = true;
      final state = AppState(api, offlineStore: store);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );

      expect(state.reconciliationServerChanged, isTrue);
      expect(
        await state.reconcileMobileWins(password: 'password'),
        isFalse,
      );
      expect(api.mobileWinsCalls, 0);
      expect(await store.loadJournal(), hasLength(1));

      expect(
        await state.reconcileMobileWins(
          password: 'password',
          confirmServerChanged: true,
        ),
        isTrue,
      );
      expect(api.mobileWinsCalls, 1);
      expect(state.isOnline, isTrue);
    });
  });
}
