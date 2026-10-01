import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

CardDiscountProjectionPolicy flatProjectionPolicy(String scope) {
  return CardDiscountProjectionPolicy(
    schemaVersion: 1,
    policyId: '$scope-flat-statement-1.2',
    type: 'flat_statement',
    rounding: 'floor',
    rate: '0.012',
  );
}

OfflineBaseline baselineFixture({
  int remainingLiquidity = 10000,
  int? currentMonthSpendable,
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
      fixedCashProcessedTotal: 0,
      frozenAssetTotal: 0,
      cashFlowBalance: 5000,
      remainingLiquidity: remainingLiquidity,
      currentMonthSpendable: currentMonthSpendable,
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
          includeProjectionPolicy ? flatProjectionPolicy('owner') : null,
    ),
    familyDiscountMonth: CardDiscountMonth(
      month: '2026-09',
      scope: 'family',
      policy: 'enabled',
      projectionPolicy:
          includeProjectionPolicy ? flatProjectionPolicy('family') : null,
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

Future<Directory> temporaryDirectoryFixture() async {
  final directory =
      await Directory.systemTemp.createTemp('money-note-offline-');
  addTearDown(() async {
    if (await directory.exists()) {
      await directory.delete(recursive: true);
    }
  });
  return directory;
}

OfflineStore offlineStoreFixture(
  Directory directory, {
  DateTime Function()? clock,
}) {
  return OfflineStore(
    directoryProvider: () async => directory,
    clock: clock,
  );
}

Future<void> saveLinkedMetadata(
    OfflineStore store, OfflineWorkspaceMetadata metadata) async {
  final baseline = await store.loadBaseline();
  await store.saveMetadata(OfflineWorkspaceMetadata.fromJson({
    ...metadata.toJson(),
    'baseline_lineage_fingerprint':
        baseline == null ? null : store.recoveryLineageFingerprint(baseline),
  }));
}

Future<void> saveCommittedFixture(OfflineStore store, String id) async {
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
  await saveLinkedMetadata(
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

class OfflineApiFake extends MoneyNoteApiClient {
  OfflineApiFake() : super(baseUrl: 'https://example.invalid');

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
  Future<void> health({Duration timeout = const Duration(seconds: 15)}) async {
    healthCalls += 1;
    if (!available) {
      throw MoneyNoteConnectionException('서버에 연결할 수 없습니다.');
    }
  }

  @override
  Future<Summary> summary() async {
    stateFetchCalls += 1;
    return baselineFixture(remainingLiquidity: remainingLiquidity).summary;
  }

  @override
  Future<CardPaymentStatus> currentCardPaymentStatus() async {
    stateFetchCalls += 1;
    return baselineFixture().cardPaymentStatus;
  }

  @override
  Future<JudgmentState> judgment() async {
    stateFetchCalls += 1;
    if (failJudgment) throw StateError('incomplete refresh');
    return baselineFixture().judgment;
  }

  @override
  Future<List<LedgerEntry>> currentEntries() async {
    stateFetchCalls += 1;
    return baselineFixture().entries;
  }

  @override
  Future<List<LedgerEntry>> confirmedPlannedEntries() async {
    stateFetchCalls += 1;
    return const [];
  }

  @override
  Future<List<MonthlyPanel>> currentPanels() async {
    stateFetchCalls += 1;
    return baselineFixture().panels;
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
    return baselineFixture().settings;
  }

  @override
  Future<MonthCloseStatus> monthCloseStatus() async {
    stateFetchCalls += 1;
    return baselineFixture().monthCloseStatus;
  }

  @override
  Future<CardDiscountMonth> discountMonth(String month, String scope) async {
    stateFetchCalls += 1;
    return scope == 'owner'
        ? baselineFixture().ownerDiscountMonth
        : baselineFixture().familyDiscountMonth;
  }

  @override
  Future<TransitDiscountProfileStatus> transitDiscountProfile(
      String month) async {
    stateFetchCalls += 1;
    return baselineFixture().transitDiscountProfile;
  }

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async => {
        'snapshot': const {
          'schema_version': 2,
          'exported_at': '2026-09-17T03:14:00Z',
          'data': <String, dynamic>{},
        },
        'state_fingerprint': committed
            ? currentFingerprint
            : baselineFixture().serverStateFingerprint,
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
