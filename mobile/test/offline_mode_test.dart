import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
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
import 'package:money_note_mobile/src/screens/cash_flow_screen.dart';
import 'package:money_note_mobile/src/screens/input_screen.dart';
import 'package:money_note_mobile/src/screens/management_screen.dart';

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
  bool registeredCandidate = false,
  bool legacyRegisteredCandidate = false,
  String? resolvedReconciliationId,
}) {
  return OfflineBaseline(
    syncedAt: DateTime.utc(2026, 9, 17, 3, 14),
    authoritativeSnapshot: includeAuthority
        ? {
            'schema_version': 2,
            'exported_at': '2026-09-17T03:14:00Z',
            'data': <String, dynamic>{
              'notification_candidate_registrations': [
                if (registeredCandidate || legacyRegisteredCandidate)
                  {
                    'registration_key': 'woori_card:orphan-candidate',
                    'target': 'ledger',
                    'target_id': 41,
                    'request_fingerprint': legacyRegisteredCandidate
                        ? 'ee32b8775b2becc65724d7f1c7da75e08ab00daa40c31a14acff98e635a0030a'
                        : '91a7f4cce506f90bb3bb45f23db994b2aa2b269a5e583d9e023976fc9aa0477f',
                  },
              ],
              if (legacyRegisteredCandidate)
                'ledger_entries': [
                  {
                    'id': 41,
                    'entry_date': '2026-09-17',
                    'title': '[가게] 식사',
                    'usage_place': '가게',
                    'usage_item': '식사',
                    'amount_value': 1000,
                    'spending_category': null,
                    'discount_override': 0,
                    'aux_amount_value': null,
                  },
                ],
            },
          }
        : null,
    serverStateFingerprint: includeAuthority
        ? 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
        : null,
    resolvedReconciliationId: resolvedReconciliationId,
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

Future<void> _saveLinkedMetadata(
    OfflineStore store, OfflineWorkspaceMetadata metadata) async {
  final baseline = await store.loadBaseline();
  await store.saveMetadata(OfflineWorkspaceMetadata.fromJson({
    ...metadata.toJson(),
    'baseline_lineage_fingerprint':
        baseline == null ? null : store.recoveryLineageFingerprint(baseline),
  }));
}

Future<void> _saveCommittedFixture(OfflineStore store, String id) async {
  final baseline = (await store.loadBaseline())!;
  final artifact = await store.createMobileRecoveryArtifact(
    baseline: baseline,
    operations: await store.loadJournal(),
    metadata: OfflineWorkspaceMetadata(
      mode: ConnectivityMode.reconciliationRequired,
      reconciliationChoice: ReconciliationChoice.applyToServer,
      reconciliationId: id,
      phase: ReconciliationPhase.preparing,
    ),
  );
  await _saveLinkedMetadata(
      store,
      OfflineWorkspaceMetadata(
        mode: ConnectivityMode.reconciliationFinalizing,
        reconciliationChoice: ReconciliationChoice.applyToServer,
        reconciliationId: id,
        phase: ReconciliationPhase.mobileCommitted,
        serverCommitStatus: ServerCommitStatus.committed,
        currentServerFingerprint:
            'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
        serverArtifactFilename: 'server.snapshot',
        mobileArtifactFilename: artifact.filename,
        mobileArtifactSha256: artifact.sha256,
      ));
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
        'state_revision': committed ? 2 : 1,
        'evaluation_date': '2026-09-17',
        'discount_policy_defaults': const {
          'owner': 'enabled',
          'family': 'disabled'
        },
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

class _DelayedRefreshApi extends _OfflineApi {
  final summaryRequested = Completer<void>();
  final releaseSummary = Completer<void>();

  @override
  Future<Summary> summary() async {
    if (!summaryRequested.isCompleted) summaryRequested.complete();
    await releaseSummary.future;
    return super.summary();
  }
}

class _ChangingBaselineApi extends _OfflineApi {
  int baselineCalls = 0;

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async {
    baselineCalls += 1;
    final fingerprint = baselineCalls == 1
        ? _baseline().serverStateFingerprint
        : _OfflineApi.currentFingerprint;
    if (baselineCalls == 2) remainingLiquidity = 9000;
    return {
      'snapshot': const {
        'schema_version': 2,
        'exported_at': '2026-09-17T03:14:00Z',
        'data': <String, dynamic>{},
      },
      'state_fingerprint': fingerprint,
      'state_revision': baselineCalls == 1 ? 1 : 2,
      'evaluation_date': '2026-09-17',
      'discount_policy_defaults': const {
        'owner': 'enabled',
        'family': 'disabled'
      },
    };
  }
}

class _AbaRefreshApi extends _OfflineApi {
  int envelopeCalls = 0;
  bool changeEvaluationDate = false;

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async {
    envelopeCalls += 1;
    final result = await super.offlineReconciliationBaseline();
    if (envelopeCalls == 1) remainingLiquidity = 101234;
    if (envelopeCalls == 2) remainingLiquidity = 100000;
    return {
      ...result,
      'state_revision': envelopeCalls == 1 ? 1 : 3,
      'evaluation_date': changeEvaluationDate && envelopeCalls > 1
          ? '2026-09-18'
          : '2026-09-17',
    };
  }
}

class _OverlappingRefreshApi extends _OfflineApi {
  final firstRequested = Completer<void>();
  final secondRequested = Completer<void>();
  final firstResult = Completer<Summary>();
  final secondResult = Completer<Summary>();
  int summaryCalls = 0;

  @override
  Future<Summary> summary() {
    summaryCalls += 1;
    if (summaryCalls == 1) {
      firstRequested.complete();
      return firstResult.future;
    }
    secondRequested.complete();
    return secondResult.future;
  }
}

class _FailingDeleteJournalStore extends OfflineStore {
  _FailingDeleteJournalStore(Directory directory)
      : super(directoryProvider: () async => directory);

  bool failNextDelete = true;

  @override
  Future<void> deleteJournal() async {
    if (failNextDelete) {
      failNextDelete = false;
      throw const OfflinePersistenceException(
        'injected journal cleanup failure',
      );
    }
    await super.deleteJournal();
  }
}

class _FailingBaselineStore extends OfflineStore {
  _FailingBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);

  bool failNextReplace = false;

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline) async {
    if (failNextReplace) {
      failNextReplace = false;
      throw const OfflinePersistenceException(
        'injected fresh baseline persistence failure',
      );
    }
    await super.replaceBaseline(baseline);
  }
}

class _DelayedMutationApi extends _OfflineApi {
  final cashCreateRequested = Completer<void>();
  final cashCreateResult = Completer<CashFlow>();
  int cashCreateCalls = 0;

  @override
  Future<CashFlow> createCashFlow({
    required String occurredOn,
    required String title,
    required int amount,
    required bool isPrimaryIncome,
  }) {
    cashCreateCalls += 1;
    if (!cashCreateRequested.isCompleted) cashCreateRequested.complete();
    return cashCreateResult.future;
  }
}

class _FormAppState extends AppState {
  _FormAppState() : super(_OfflineApi());

  Completer<bool> expenseCompletion = Completer<bool>();
  Completer<bool> cashCompletion = Completer<bool>();
  Completer<bool> panelCompletion = Completer<bool>();
  Completer<PlannedChargePreview> plannedPreviewCompletion =
      Completer<PlannedChargePreview>();
  Completer<bool> plannedConfirmCompletion = Completer<bool>();
  int expenseCalls = 0;
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

  group('N1 orphan lineage fails closed', () {
    test('baseline only and empty journal remain valid ONLINE startup',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      expect(
          await AppState(_OfflineApi(), offlineStore: store)
              .restorePersistedOfflineWorkspace(),
          isFalse);
      await File('${directory.path}/offline-mode/journal.ndjson')
          .writeAsString('', flush: true);
      expect(
          await AppState(_OfflineApi(), offlineStore: _store(directory))
              .restorePersistedOfflineWorkspace(),
          isFalse);
    });

    test('missing state with pending -500 never attaches J to S=101234',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 100000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      final api = _OfflineApi()
        ..available = true
        ..remainingLiquidity = 101234;
      final state = AppState(api, offlineStore: _store(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      await state.refresh();
      expect(await state.enterOfflineMode(), isFalse);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
      expect(await store.loadJournal(), hasLength(1));
    });

    test('pending J with missing B or corrupt state is recovery blocked',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0
        },
      );
      final missingBaseline = AppState(_OfflineApi(), offlineStore: store);
      expect(await missingBaseline.restorePersistedOfflineWorkspace(), isTrue);
      expect(missingBaseline.isPersistenceRecoveryBlocked, isTrue);
      await store.replaceBaseline(_baseline());
      await File('${directory.path}/offline-mode/state.json')
          .writeAsString('{corrupt', flush: true);
      final corrupt = AppState(_OfflineApi(), offlineStore: _store(directory));
      expect(await corrupt.restorePersistedOfflineWorkspace(), isTrue);
      expect(corrupt.isPersistenceRecoveryBlocked, isTrue);
    });

    test('valid B/state/J lineage restores but altered B blocks', () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 100000));
      final original = AppState(_OfflineApi(), offlineStore: store);
      expect(await original.enterOfflineMode(), isTrue);
      expect(
          await original.createCashFlow(
            occurredOn: '2026-09-17',
            title: '현금',
            amount: 500,
            isIncome: false,
            isPrimaryIncome: false,
          ),
          isTrue);
      final valid = AppState(_OfflineApi(), offlineStore: _store(directory));
      expect(await valid.restorePersistedOfflineWorkspace(), isTrue);
      expect(valid.isOffline, isTrue);
      expect(valid.summary!.remainingLiquidity, 99500);
      await store.replaceBaseline(_baseline(remainingLiquidity: 101234));
      final mismatch = AppState(_OfflineApi(), offlineStore: _store(directory));
      expect(await mismatch.restorePersistedOfflineWorkspace(), isTrue);
      expect(mismatch.isPersistenceRecoveryBlocked, isTrue);
    });

    test('incomplete and contradictory persisted metadata fails closed',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 100000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      final invalid = [
        const OfflineWorkspaceMetadata(mode: ConnectivityMode.offline),
        const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          reconciliationChoice: ReconciliationChoice.applyToServer,
          reconciliationId: 'reconcile-resolved-conflict',
          phase: ReconciliationPhase.mobileCommitted,
          serverCommitStatus: ServerCommitStatus.committed,
        ),
        const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.reconciliationRequired,
          reconciliationChoice: ReconciliationChoice.applyToServer,
          reconciliationId: 'reconcile-impossible-status',
          serverCommitStatus: ServerCommitStatus.committed,
        ),
        const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.reconciliationFinalizing,
          reconciliationChoice: ReconciliationChoice.applyToServer,
          phase: ReconciliationPhase.mobileCommitted,
          serverCommitStatus: ServerCommitStatus.committed,
        ),
        const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          mobileArtifactFilename: 'partial-mobile-bundle',
        ),
        const OfflineWorkspaceMetadata(
          mode: ConnectivityMode.offline,
          serverChanged: true,
        ),
      ];
      for (var index = 0; index < invalid.length; index++) {
        if (index == 0) {
          await store.saveMetadata(invalid[index]);
        } else {
          await _saveLinkedMetadata(store, invalid[index]);
        }
        final state = AppState(_OfflineApi(), offlineStore: _store(directory));
        expect(await state.restorePersistedOfflineWorkspace(), isTrue);
        expect(state.isPersistenceRecoveryBlocked, isTrue);
        expect(await state.enterOfflineMode(), isFalse);
        expect(
            await state.createCashFlow(
              occurredOn: '2026-09-17',
              title: '금지',
              amount: 1,
              isIncome: false,
              isPrimaryIncome: false,
            ),
            isFalse);
        expect(await store.loadJournal(), hasLength(1));
      }
    });
    test('finalizing with a different valid journal is recovery blocked',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final original = await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await _saveCommittedFixture(store, 'reconcile-journal-identity');
      final changed = OfflineJournalOperation(
        operationId: original.operationId,
        type: original.type,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -700,
          'is_primary_income': 0,
        },
        createdAt: original.createdAt,
        sequence: original.sequence,
      );
      await File('${directory.path}/offline-mode/journal.ndjson')
          .writeAsString('${jsonEncode(changed.toJson())}\n', flush: true);
      final state = AppState(_OfflineApi(), offlineStore: _store(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(await store.loadJournal(), hasLength(1));
    });

    test('incomplete finalizing commit metadata is recovery blocked', () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0
        },
      );
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.reconciliationFinalizing,
            reconciliationChoice: ReconciliationChoice.applyToServer,
            reconciliationId: 'reconcile-damaged-finalizing',
            phase: ReconciliationPhase.mobileCommitted,
            serverCommitStatus: ServerCommitStatus.none,
          ));
      final state = AppState(_OfflineApi(), offlineStore: _store(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(await store.loadJournal(), hasLength(1));
    });
  });

  group('N5 offline notification candidate identity', () {
    Map<String, dynamic> candidatePayload(
            {int amount = 1000, bool discount = true}) =>
        {
          'book_section': 'current',
          'entry_kind': 'expense',
          'entry_date': '2026-09-17',
          'title': '[가게] 식사',
          'usage_place': '가게',
          'usage_item': '식사',
          'amount_value': amount,
          'spending_category': null,
          'discount_enabled': discount,
          'candidate_registration_key': 'woori_card:orphan-candidate',
        };

    test('same key and payload survive restart with one durable operation',
        () async {
      final directory = await _temporaryDirectory();
      final first = _store(directory);
      final operation = await first.appendOperation(
        type: OfflineOperationType.createCardExpense,
        payload: candidatePayload(),
      );
      final restarted = _store(directory);
      final retry = await restarted.appendOperation(
        type: OfflineOperationType.createCardExpense,
        payload: candidatePayload(),
      );
      expect(retry.operationId, operation.operationId);
      expect(await restarted.loadJournal(), hasLength(1));
      for (final changed in [
        candidatePayload(amount: 2000),
        candidatePayload(discount: false)
      ]) {
        await expectLater(
          restarted.appendOperation(
              type: OfflineOperationType.createCardExpense, payload: changed),
          throwsA(isA<OfflinePersistenceException>()),
        );
      }
      expect(await restarted.loadJournal(), hasLength(1));
    });

    test(
        'candidate already in authoritative baseline never enters J or projection',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(
        remainingLiquidity: 99000,
        registeredCandidate: true,
      ));
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);
      Future<bool> register({int amount = 1000, bool discount = true}) =>
          state.createExpense(
            usagePlace: '가게',
            usageItem: '식사',
            amount: amount,
            discountEnabled: discount,
            entryDate: '2026-09-17',
            candidateRegistrationKey: 'woori_card:orphan-candidate',
          );
      expect(await register(), isTrue);
      expect(state.summary!.remainingLiquidity, 99000);
      expect(await store.loadJournal(), isEmpty);
      final restarted =
          AppState(_OfflineApi(), offlineStore: _store(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
      expect(
          await restarted.createExpense(
            usagePlace: '가게',
            usageItem: '식사',
            amount: 1000,
            discountEnabled: true,
            entryDate: '2026-09-17',
            candidateRegistrationKey: 'woori_card:orphan-candidate',
          ),
          isTrue);
      expect(restarted.summary!.remainingLiquidity, 99000);
      expect(await store.loadJournal(), isEmpty);
      expect(await register(amount: 2000), isFalse);
      expect(await register(discount: false), isFalse);
    });

    test(
        'old baseline registration hash needs matching stored authoritative row',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(
          remainingLiquidity: 99000, legacyRegisteredCandidate: true));
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);
      Future<bool> register(int amount) => state.createExpense(
            usagePlace: '가게',
            usageItem: '식사',
            amount: amount,
            discountEnabled: true,
            entryDate: '2026-09-17',
            candidateRegistrationKey: 'woori_card:orphan-candidate',
          );
      expect(await register(1000), isTrue);
      expect(state.summary!.remainingLiquidity, 99000);
      expect(await store.loadJournal(), isEmpty);
      expect(await register(2000), isFalse);
    });

    test(
        'baseline candidate already assigned to Family cannot be appended as ledger',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final json = _baseline(registeredCandidate: true).toJson();
      final data = (json['authoritative_snapshot'] as Map)['data'] as Map;
      (data['notification_candidate_registrations'] as List).single['target'] =
          'family_card';
      await store.replaceBaseline(OfflineBaseline.fromJson(json));
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.enterOfflineMode(), isTrue);
      expect(
          await state.createExpense(
            usagePlace: '가게',
            usageItem: '식사',
            amount: 1000,
            discountEnabled: true,
            entryDate: '2026-09-17',
            candidateRegistrationKey: 'woori_card:orphan-candidate',
          ),
          isFalse);
      expect(await store.loadJournal(), isEmpty);
    });

    test(
        'concurrent duplicate registration is one durable J and one projection',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final operations = await Future.wait([
        store.appendOperation(
            type: OfflineOperationType.createCardExpense,
            payload: candidatePayload()),
        store.appendOperation(
            type: OfflineOperationType.createCardExpense,
            payload: candidatePayload()),
      ]);
      expect(operations[0].operationId, operations[1].operationId);
      expect(await store.loadJournal(), hasLength(1));

      await store.replaceBaseline(_baseline(remainingLiquidity: 100000));
      await _saveLinkedMetadata(store,
          const OfflineWorkspaceMetadata(mode: ConnectivityMode.offline));
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.offlineJournal, hasLength(1));
      expect(state.summary!.remainingLiquidity, 99012);
      expect(
          await state.createExpense(
            usagePlace: '가게',
            usageItem: '식사',
            amount: 1000,
            discountEnabled: true,
            entryDate: '2026-09-17',
            candidateRegistrationKey: 'woori_card:orphan-candidate',
          ),
          isTrue);
      expect(state.offlineJournal, hasLength(1));
      expect(state.summary!.remainingLiquidity, 99012);
    });
  });

  group('durable offline store', () {
    test('unresolved registration key must not bind an unrelated new draft',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final first = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '첫 번째 생활비',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': false,
      };
      final other = <String, dynamic>{
        ...first,
        'title': '별개 지출',
        'amount_value': 700
      };
      expect(
          await store.reserveManualPanelRetryKey(first,
              preferredKey: 'manual-panel-first'),
          'manual-panel-first');
      final restarted = _store(directory);
      await expectLater(
          restarted.reserveManualPanelRetryKey(other,
              preferredKey: 'manual-panel-other'),
          throwsA(isA<OfflinePersistenceException>()));
      expect((await restarted.loadPendingManualPanelRetry())!.key,
          'manual-panel-first');
      expect((await restarted.loadPendingManualPanelRetry())!.input, first);
    });

    test('unknown manual panel result keeps one identity across edited drafts',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final first = {
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '생활비',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': false,
      };
      final changed = {...first, 'amount_value': 700};
      final firstKey = await store.reserveManualPanelRetryKey(first,
          preferredKey: 'manual-panel-original');
      final restarted = _store(directory);
      await expectLater(
          restarted.reserveManualPanelRetryKey(changed,
              preferredKey: 'manual-panel-new'),
          throwsA(isA<OfflinePersistenceException>()));
      expect(
          await restarted.reserveManualPanelRetryKey(first,
              preferredKey: 'manual-panel-other-process'),
          firstKey);
      expect(await restarted.reserveManualPanelRetryKey(first), firstKey);
      await expectLater(
          restarted.completeManualPanelRetryKey(changed, firstKey),
          throwsA(isA<OfflinePersistenceException>()));
      await restarted.completeManualPanelRetryKey(first, firstKey);
      expect(
          await restarted.reserveManualPanelRetryKey(first,
              preferredKey: 'manual-panel-fresh'),
          'manual-panel-fresh');
    });

    test('manual retry cleanup failure retains original input and key',
        () async {
      final directory = await _temporaryDirectory();
      final failingStore = OfflineStore(
        directoryProvider: () async => directory,
        beforeManualRetryCleanup: () async =>
            throw StateError('cleanup failed'),
      );
      final input = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'family_card',
        'title': '이전 가족카드',
        'spent_on': '2026-09-17',
        'amount_value': 10000,
        'discount_enabled': false,
      };
      final key = await failingStore.reserveManualPanelRetryKey(input,
          preferredKey: 'manual-panel-cleanup');
      await expectLater(failingStore.completeManualPanelRetryKey(input, key),
          throwsA(isA<StateError>()));
      final restarted = _store(directory);
      expect((await restarted.loadPendingManualPanelRetry())!.input, input);
      expect(await restarted.hasPendingManualPanelRetry(), isTrue);
      await restarted.completeManualPanelRetryKey(input, key);
      expect(await restarted.hasPendingManualPanelRetry(), isFalse);
      expect(
          await restarted.reserveManualPanelRetryKey(
              {...input, 'title': '새 가족카드'},
              preferredKey: 'manual-panel-new'),
          'manual-panel-new');
    });
    test('legacy digest-only manual retry accepts exact input but not edits',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final input = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '이전 형식',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': true,
      };
      const key = 'manual-panel-legacy';
      await store.reserveManualPanelRetryKey(input, preferredKey: key);
      final retryFile =
          File('${directory.path}/offline-mode/manual-panel-retries.json');
      final v2 = jsonDecode(await retryFile.readAsString()) as Map;
      await retryFile.writeAsString(jsonEncode({
        'schema_version': 1,
        'keys': {v2['input_digest']: key},
      }));
      final restarted = _store(directory);
      expect((await restarted.loadPendingManualPanelRetry())!.input, isNull);
      expect(await restarted.reserveManualPanelRetryKey(input), key);
      await expectLater(
          restarted.reserveManualPanelRetryKey({...input, 'amount_value': 700}),
          throwsA(isA<OfflinePersistenceException>()));
      await restarted.completeManualPanelRetryKey(input, key);
      expect(await restarted.hasPendingManualPanelRetry(), isFalse);
    });
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
    test('valid EOF record remains durable when the next record is appended',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      for (final amount in [-500, -700]) {
        await store.appendOperation(
          type: OfflineOperationType.createCashFlow,
          payload: {
            'occurred_on': '2026-09-17',
            'title': '현금',
            'amount_value': amount,
            'is_primary_income': 0,
          },
        );
      }
      final journal = File('${directory.path}/offline-mode/journal.ndjson');
      final bytes = await journal.readAsBytes();
      expect(bytes.last, 0x0a);
      await journal.writeAsBytes(bytes.sublist(0, bytes.length - 1),
          flush: true);

      expect(
        (await _store(directory).loadJournal())
            .map((operation) => operation.payload['amount_value']),
        [-500, -700],
      );

      await _store(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '추가',
          'amount_value': -300,
          'is_primary_income': 0,
        },
      );
      final restarted = await _store(directory).loadJournal();
      expect(restarted.map((operation) => operation.sequence), [1, 2, 3]);
      expect(
        restarted.map((operation) => operation.payload['amount_value']),
        [-500, -700, -300],
      );
    });

    test('truncated JSON and UTF-8 tails preserve every complete record',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
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
      final koreanPrefix = utf8.encode('한').sublist(0, 2);
      await journal.writeAsBytes(koreanPrefix,
          mode: FileMode.append, flush: true);

      final recovered = await _store(directory).loadJournal();
      expect(recovered, hasLength(1));
      expect(recovered.single.payload['amount_value'], 500);

      await _store(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '복구 후',
          'amount_value': 700,
          'is_primary_income': 0,
        },
      );
      final restarted = await _store(directory).loadJournal();
      expect(restarted.map((operation) => operation.sequence), [1, 2]);
      expect(restarted.map((operation) => operation.payload['amount_value']),
          [500, 700]);

      await journal.writeAsString('{"schema_version":',
          mode: FileMode.append, flush: true);
      expect(await _store(directory).loadJournal(), hasLength(2));
      await _store(directory).appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '두 번째 복구 후',
          'amount_value': 300,
          'is_primary_income': 0,
        },
      );
      expect(await _store(directory).loadJournal(), hasLength(3));
    });

    test('concurrent appends serialize sequence allocation and durable writes',
        () async {
      final directory = await _temporaryDirectory();
      final firstWriteEntered = Completer<void>();
      final releaseFirstWrite = Completer<void>();
      var hookCalls = 0;
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeJournalAppendWrite: () async {
          hookCalls += 1;
          if (hookCalls == 1) {
            firstWriteEntered.complete();
            await releaseFirstWrite.future;
          }
        },
      );

      final first = store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': 'A',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await firstWriteEntered.future;
      final second = store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': 'B',
          'amount_value': -700,
          'is_primary_income': 0,
        },
      );
      releaseFirstWrite.complete();

      final appended = await Future.wait([first, second]);
      expect(appended.map((operation) => operation.sequence), [1, 2]);
      final restarted = await _store(directory).loadJournal();
      expect(restarted.map((operation) => operation.sequence), [1, 2]);
      expect(restarted.map((operation) => operation.payload['amount_value']),
          [-500, -700]);
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

    test('unconfirmed manual registration blocks offline epoch across restart',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      const input = <String, dynamic>{
        'month': '2026-09',
        'panel_type': 'claim',
        'title': '미확인 청구',
        'spent_on': '2026-09-17',
        'amount_value': 500,
        'discount_enabled': false,
      };
      final key = await store.reserveManualPanelRetryKey(input);
      final restartedStore = _store(directory);
      final state = AppState(_OfflineApi(), offlineStore: restartedStore);

      expect(await state.enterOfflineMode(), isFalse);
      expect(state.isOnline, isTrue);
      expect(state.offlineEntryMessage, contains('저장 결과를 확인하지 못한'));
      expect(await restartedStore.hasPendingManualPanelRetry(), isTrue);
      await restartedStore.completeManualPanelRetryKey(input, key);
      expect(await state.enterOfflineMode(), isTrue);
    });

    test('in-flight online write cannot race a new offline epoch', () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final state = AppState(_OfflineApi(), offlineStore: store)..isBusy = true;
      expect(await state.enterOfflineMode(), isFalse);
      expect(state.offlineEntryMessage, contains('저장 또는 상태 전환'));
      expect((await store.loadMetadata()).mode, ConnectivityMode.online);
      state.isBusy = false;
      expect(await state.enterOfflineMode(), isTrue);
    });

    test('malformed manual retry identity fails closed on offline entry',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final retryFile =
          File('${directory.path}/offline-mode/manual-panel-retries.json');
      await retryFile.writeAsString('{"schema_version":1,"keys":{"draft":42}}');
      final state = AppState(_OfflineApi(), offlineStore: store);

      expect(await state.enterOfflineMode(), isFalse);
      expect(state.isOnline, isTrue);
      expect(state.offlineEntryMessage, contains('재시도 기록을 읽을 수 없습니다'));
      expect(await retryFile.exists(), isTrue);
    });

    test('malformed manual retry identity blocks normal startup refresh',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      final retryFile =
          File('${directory.path}/offline-mode/manual-panel-retries.json');
      await retryFile.writeAsString(
          '{"schema_version":2,"key":"x","input_digest":"bad","input":{}}');
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(await retryFile.exists(), isTrue);
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
      await _saveLinkedMetadata(
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
      await _saveLinkedMetadata(
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
    test('untrusted complete journal corruption fails closed on restart',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await _saveLinkedMetadata(
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

      final api = _OfflineApi()..available = true;
      final state = AppState(api, offlineStore: _store(directory));
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
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '대기 중',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await _saveCommittedFixture(store, 'reconcile-finalizing-identity');
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isReconciliationFinalizing, isTrue);

      expect(await state.enterOfflineMode(), isFalse);
      final metadata = await store.loadMetadata();
      expect(metadata.mode, ConnectivityMode.reconciliationFinalizing);
      expect(metadata.reconciliationId, 'reconcile-finalizing-identity');
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
    test('late ONLINE refresh cannot replace a frozen Offline lineage',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 10000));
      final api = _DelayedRefreshApi()..available = true;
      final state = AppState(api, offlineStore: store)..user = _baseline().user;

      final delayedRefresh = state.refresh();
      await api.summaryRequested.future;
      expect(await state.enterOfflineMode(), isTrue);
      expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '오프라인 출금',
          amount: 500,
          isIncome: false,
          isPrimaryIncome: false,
        ),
        isTrue,
      );
      api.remainingLiquidity = 11234;
      api.releaseSummary.complete();

      await expectLater(delayedRefresh, throwsA(isA<MoneyNoteApiException>()));
      expect(state.isOffline, isTrue);
      expect(state.summary!.remainingLiquidity, 9500);
      expect(
        (await store.loadBaseline())!.summary.remainingLiquidity,
        10000,
      );
      expect(await store.loadJournal(), hasLength(1));
    });

    test('mixed display and Snapshot generations are rejected and retried',
        () async {
      final directory = await _temporaryDirectory();
      final api = _ChangingBaselineApi()..available = true;
      final store = _store(directory);
      final state = AppState(api, offlineStore: store)..user = _baseline().user;

      await state.refresh();

      expect(api.baselineCalls, 4);
      expect(state.summary!.remainingLiquidity, 9000);
      final installed = await store.loadBaseline();
      expect(installed!.summary.remainingLiquidity, 9000);
      expect(installed.serverStateFingerprint, _OfflineApi.currentFingerprint);
    });
    test('A-B-A with equal fingerprint rejects middle display by revision',
        () async {
      final directory = await _temporaryDirectory();
      final api = _AbaRefreshApi()..available = true;
      final store = _store(directory);
      final state = AppState(api, offlineStore: store)..user = _baseline().user;
      await state.refresh();
      expect(api.envelopeCalls, 4);
      expect(state.summary!.remainingLiquidity, 100000);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('evaluation date change rejects stale display even without DB change',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 10000));
      final api = _AbaRefreshApi()
        ..available = true
        ..changeEvaluationDate = true;
      final state = AppState(api, offlineStore: store)..user = _baseline().user;
      await expectLater(state.refresh(), throwsA(isA<MoneyNoteApiException>()));
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 10000);
    });

    test('newer ONLINE refresh wins when its response completes first',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final api = _OverlappingRefreshApi()..available = true;
      final state = AppState(api, offlineStore: store)..user = _baseline().user;
      final first = state.refresh();
      await api.firstRequested.future;
      final second = state.refresh();
      await api.secondRequested.future;
      api.secondResult.complete(_baseline(remainingLiquidity: 101234).summary);
      await second;
      api.firstResult.complete(_baseline(remainingLiquidity: 100000).summary);
      await expectLater(first, throwsA(isA<MoneyNoteApiException>()));
      expect(state.summary!.remainingLiquidity, 101234);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 101234);
    });

    test('newer ONLINE refresh wins when older response completes first',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      final api = _OverlappingRefreshApi()..available = true;
      final state = AppState(api, offlineStore: store)..user = _baseline().user;
      final first = state.refresh();
      await api.firstRequested.future;
      final second = state.refresh();
      await api.secondRequested.future;
      api.firstResult.complete(_baseline(remainingLiquidity: 100000).summary);
      await expectLater(first, throwsA(isA<MoneyNoteApiException>()));
      api.secondResult.complete(_baseline(remainingLiquidity: 101234).summary);
      await second;
      expect(state.summary!.remainingLiquidity, 101234);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 101234);
    });
    test('AppState mutation single-flight rejects concurrent re-entry',
        () async {
      final directory = await _temporaryDirectory();
      final api = _DelayedMutationApi()..available = true;
      final state = AppState(api, offlineStore: _store(directory))
        ..user = _baseline().user;

      final first = state.createCashFlow(
        occurredOn: '2026-09-17',
        title: '한 번만 저장',
        amount: 500,
        isIncome: true,
        isPrimaryIncome: false,
      );
      await api.cashCreateRequested.future;
      final duplicate = await state.createCashFlow(
        occurredOn: '2026-09-17',
        title: '중복 진입',
        amount: 500,
        isIncome: true,
        isPrimaryIncome: false,
      );
      expect(duplicate, isFalse);
      expect(api.cashCreateCalls, 1);

      api.cashCreateResult.complete(CashFlow(
        id: 1,
        occurredOn: '2026-09-17',
        title: '한 번만 저장',
        amountValue: 500,
        sortOrder: 1,
        isPrimaryIncome: false,
      ));
      expect(await first, isTrue);
      expect(api.cashCreateCalls, 1);
    });

    test('offline append failure leaves journal and projection unchanged',
        () async {
      final directory = await _temporaryDirectory();
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeJournalAppendWrite: () async {
          throw const OfflinePersistenceException(
              'injected journal disk failure');
        },
      );
      await store.replaceBaseline(_baseline(remainingLiquidity: 10000));
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
          ));
      final state = AppState(_OfflineApi(), offlineStore: store);
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);

      expect(
        await state.createCashFlow(
          occurredOn: '2026-09-17',
          title: '기록되면 안 됨',
          amount: 500,
          isIncome: false,
          isPrimaryIncome: false,
        ),
        isFalse,
      );

      expect(state.isOffline, isTrue);
      expect(state.offlineJournal, isEmpty);
      expect(state.summary!.remainingLiquidity, 10000);
      expect(await store.loadJournal(), isEmpty);
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
    await tester.runAsync(() => _saveLinkedMetadata(
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
    await tester.runAsync(() => _saveLinkedMetadata(
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

  testWidgets('expense keyboard and button re-entry produces one submit',
      (tester) async {
    final state = _FormAppState();
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

  testWidgets('expense failure and stale completion preserve the current draft',
      (tester) async {
    final state = _FormAppState();
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
    final state = _FormAppState();
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
    final state = _FormAppState();
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
    final state = _FormAppState()
      ..monthCloseStatus = _baseline().monthCloseStatus
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
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
          failingStore,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
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
      await _saveLinkedMetadata(
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
      await _saveLinkedMetadata(
          store,
          OfflineWorkspaceMetadata(
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
      await store.replaceBaseline(_baseline(
          remainingLiquidity: 9900,
          resolvedReconciliationId: pending.reconciliationId));
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
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
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
        'fresh baseline persistence failure preserves finalizing lineage for restart',
        () async {
      final directory = await _temporaryDirectory();
      final store = _FailingBaselineStore(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 10000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '이미 반영된 출금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await _saveCommittedFixture(store, 'reconcile-baseline-write-failure');
      final api = _OfflineApi()
        ..available = true
        ..committed = true
        ..remainingLiquidity = 9500;
      store.failNextReplace = true;
      final state = AppState(api, offlineStore: store);

      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isReconciliationFinalizing, isTrue);
      expect(state.mobileCommitIsCommitted, isTrue);
      expect(await store.loadJournal(), hasLength(1));
      final preserved = await store.loadBaseline();
      expect(preserved!.summary.remainingLiquidity, 10000);
      expect(preserved.resolvedReconciliationId, isNull);

      final restarted = AppState(api, offlineStore: _store(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
      expect(restarted.isOnline, isTrue);
      expect(api.mobileWinsCalls, 0);
      expect(await store.loadJournal(), isEmpty);
      final fresh = await store.loadBaseline();
      expect(fresh!.summary.remainingLiquidity, 9500);
      expect(
          fresh.resolvedReconciliationId, 'reconcile-baseline-write-failure');
    });

    test(
        'cleanup failure never reprojects committed journal onto fresh baseline',
        () async {
      final directory = await _temporaryDirectory();
      final store = _FailingDeleteJournalStore(directory);
      await store.replaceBaseline(_baseline(remainingLiquidity: 10000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '이미 반영된 출금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await _saveCommittedFixture(store, 'reconcile-cleanup-failure');
      final api = _OfflineApi()
        ..available = true
        ..committed = true
        ..remainingLiquidity = 9500;
      final state = AppState(api, offlineStore: store);

      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isReconciliationFinalizing, isTrue);
      expect(state.summary!.remainingLiquidity, 9500);
      expect(await store.loadJournal(), hasLength(1));
      final fresh = await store.loadBaseline();
      expect(fresh!.resolvedReconciliationId, 'reconcile-cleanup-failure');
      expect(fresh.summary.remainingLiquidity, 9500);

      api.available = false;
      final restarted = AppState(api, offlineStore: _store(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);
      expect(restarted.isReconciliationFinalizing, isTrue);
      expect(restarted.summary!.remainingLiquidity, 9500);
      expect(await store.loadJournal(), hasLength(1));

      api.available = true;
      expect(await restarted.resumeReconciliationFinalization(), isTrue);
      expect(restarted.isOnline, isTrue);
      expect(await store.loadJournal(), isEmpty);
      expect(
        (await store.loadBaseline())!.summary.remainingLiquidity,
        9500,
      );
    });

    test(
        'Server Wins fetch failure preserves offline state and restart progress',
        () async {
      final directory = await _temporaryDirectory();
      final store = _store(directory);
      await store.replaceBaseline(_baseline());
      await _saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
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
      await _saveLinkedMetadata(
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
