import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

class FailingDeleteJournalStore extends OfflineStore {
  FailingDeleteJournalStore(Directory directory)
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

class FailingBaselineStore extends OfflineStore {
  FailingBaselineStore(Directory directory)
      : super(directoryProvider: () async => directory);

  bool failNextReplace = false;

  @override
  Future<void> replaceBaseline(OfflineBaseline baseline,
      {void Function()? beforePublish}) async {
    if (failNextReplace) {
      failNextReplace = false;
      throw const OfflinePersistenceException(
        'injected fresh baseline persistence failure',
      );
    }
    await super.replaceBaseline(baseline, beforePublish: beforePublish);
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('Phase 2 reconciliation recovery', () {
    test('same timestamp recovery retries never overwrite an artifact',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(
        directory,
        clock: () => DateTime.utc(2026, 9, 18, 1, 2, 3),
      );
      final baseline = baselineFixture();
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
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
      final api = OfflineApiFake()
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
      final directory = await temporaryDirectoryFixture();
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeMobileRecoveryWrite: () async {
          throw const OfflinePersistenceException('injected write failure');
        },
      );
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
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
      final api = OfflineApiFake()..available = true;
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(includeAuthority: false));
      await saveLinkedMetadata(
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
      final api = OfflineApiFake()..available = true;
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
      final directory = await temporaryDirectoryFixture();
      final failingStore = OfflineStore(
        directoryProvider: () async => directory,
        beforeMobileRecoveryWrite: () async {
          throw const OfflinePersistenceException('injected write failure');
        },
      );
      await failingStore.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
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
      final api = OfflineApiFake()..available = true;
      final state = AppState(api, offlineStore: failingStore);
      await state.restorePersistedOfflineWorkspace();
      await state.selectReconciliationChoice(
        ReconciliationChoice.applyToServer,
      );
      final reconciliationId =
          (await failingStore.loadMetadata()).reconciliationId;

      final restartedStore = offlineStoreFixture(directory);
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
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
        OfflineApiFake()..available = true,
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
          expectedBaseline: baselineFixture(remainingLiquidity: 99999),
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
      final api = OfflineApiFake()
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

      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
      expect(await restarted.restorePersistedOfflineWorkspace(), isTrue);

      expect(restarted.isOnline, isTrue);
      expect(api.reconciliationStatusCalls, 1);
      expect(api.mobileWinsCalls, 1);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
      expect((await store.loadBaseline())!.serverStateFingerprint,
          api.bundleFingerprint);
    });
    test('cleanup-boundary crash never replays a committed journal', () async {
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
      final api = OfflineApiFake()
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
      await saveLinkedMetadata(
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
      await store.replaceBaseline(baselineFixture(
          remainingLiquidity: 9900,
          resolvedReconciliationId: pending.reconciliationId));
      await store.deleteJournal();

      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
      await restarted.restorePersistedOfflineWorkspace();

      expect(restarted.isOnline, isTrue);
      expect(api.mobileWinsCalls, 1);
      expect(api.reconciliationStatusCalls, 0);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
    });

    test('uncommitted request restarts with the same persisted choice and id',
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
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-01',
          'title': '입금',
          'amount_value': 500,
          'is_primary_income': 0,
        },
      );
      final api = OfflineApiFake()
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

      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
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
      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
      await restarted.restorePersistedOfflineWorkspace();

      expect(restarted.isOnline, isTrue);
      expect(api.mobileWinsCalls, 1);
      expect(await store.loadJournal(), isEmpty);
      expect(await store.listMobileRecoveryArtifacts(), hasLength(1));
    });

    test(
        'fresh baseline persistence failure preserves finalizing lineage for restart',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = FailingBaselineStore(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '이미 반영된 출금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await saveCommittedFixture(store, 'reconcile-baseline-write-failure');
      final api = OfflineApiFake()
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

      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
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
      final directory = await temporaryDirectoryFixture();
      final store = FailingDeleteJournalStore(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '이미 반영된 출금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await saveCommittedFixture(store, 'reconcile-cleanup-failure');
      final api = OfflineApiFake()
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
      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await saveLinkedMetadata(
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
      final api = OfflineApiFake()..available = true;
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

      final restarted = AppState(api, offlineStore: offlineStoreFixture(directory));
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
      final api = OfflineApiFake()
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
