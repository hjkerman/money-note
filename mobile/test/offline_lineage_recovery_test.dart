import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';

import 'support/offline_mode_fixtures.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('N1 orphan lineage fails closed', () {
    test('baseline only and empty journal remain valid ONLINE startup',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      expect(
          await AppState(OfflineApiFake(), offlineStore: store)
              .restorePersistedOfflineWorkspace(),
          isFalse);
      await File('${directory.path}/offline-mode/journal.ndjson')
          .writeAsString('', flush: true);
      expect(
          await AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory))
              .restorePersistedOfflineWorkspace(),
          isFalse);
    });

    test('missing state with pending -500 never attaches J to S=101234',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      final api = OfflineApiFake()
        ..available = true
        ..remainingLiquidity = 101234;
      final state = AppState(api, offlineStore: offlineStoreFixture(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      await state.refresh();
      expect(await state.enterOfflineMode(), isFalse);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
      expect(await store.loadJournal(), hasLength(1));
    });

    test('pending J with missing B or corrupt state is recovery blocked',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0
        },
      );
      final missingBaseline = AppState(OfflineApiFake(), offlineStore: store);
      expect(await missingBaseline.restorePersistedOfflineWorkspace(), isTrue);
      expect(missingBaseline.isPersistenceRecoveryBlocked, isTrue);
      await store.replaceBaseline(baselineFixture());
      await File('${directory.path}/offline-mode/state.json')
          .writeAsString('{corrupt', flush: true);
      final corrupt = AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
      expect(await corrupt.restorePersistedOfflineWorkspace(), isTrue);
      expect(corrupt.isPersistenceRecoveryBlocked, isTrue);
    });

    test('valid B/state/J lineage restores but altered B blocks', () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      final original = AppState(OfflineApiFake(), offlineStore: store);
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
      final valid = AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
      expect(await valid.restorePersistedOfflineWorkspace(), isTrue);
      expect(valid.isOffline, isTrue);
      expect(valid.summary!.remainingLiquidity, 99500);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 101234));
      final mismatch = AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
      expect(await mismatch.restorePersistedOfflineWorkspace(), isTrue);
      expect(mismatch.isPersistenceRecoveryBlocked, isTrue);
    });

    test('incomplete and contradictory persisted metadata fails closed',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
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
          await saveLinkedMetadata(store, invalid[index]);
        }
        final state = AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      final original = await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0,
        },
      );
      await saveCommittedFixture(store, 'reconcile-journal-identity');
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
      final state = AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(await store.loadJournal(), hasLength(1));
    });

    test('incomplete finalizing commit metadata is recovery blocked', () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
      await store.appendOperation(
        type: OfflineOperationType.createCashFlow,
        payload: const {
          'occurred_on': '2026-09-17',
          'title': '현금',
          'amount_value': -500,
          'is_primary_income': 0
        },
      );
      await saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.reconciliationFinalizing,
            reconciliationChoice: ReconciliationChoice.applyToServer,
            reconciliationId: 'reconcile-damaged-finalizing',
            phase: ReconciliationPhase.mobileCommitted,
            serverCommitStatus: ServerCommitStatus.none,
          ));
      final state = AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
      expect(await state.restorePersistedOfflineWorkspace(), isTrue);
      expect(state.isPersistenceRecoveryBlocked, isTrue);
      expect(await store.loadJournal(), hasLength(1));
    });
  });
}
