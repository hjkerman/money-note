
import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

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
      final directory = await temporaryDirectoryFixture();
      final first = offlineStoreFixture(directory);
      final operation = await first.appendOperation(
        type: OfflineOperationType.createCardExpense,
        payload: candidatePayload(),
      );
      final restarted = offlineStoreFixture(directory);
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(
        remainingLiquidity: 99000,
        registeredCandidate: true,
      ));
      final state = AppState(OfflineApiFake(), offlineStore: store);
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
          AppState(OfflineApiFake(), offlineStore: offlineStoreFixture(directory));
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(
          remainingLiquidity: 99000, legacyRegisteredCandidate: true));
      final state = AppState(OfflineApiFake(), offlineStore: store);
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final json = baselineFixture(registeredCandidate: true).toJson();
      final data = (json['authoritative_snapshot'] as Map)['data'] as Map;
      (data['notification_candidate_registrations'] as List).single['target'] =
          'family_card';
      await store.replaceBaseline(OfflineBaseline.fromJson(json));
      final state = AppState(OfflineApiFake(), offlineStore: store);
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
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

      await store.replaceBaseline(baselineFixture(remainingLiquidity: 100000));
      await saveLinkedMetadata(store,
          const OfflineWorkspaceMetadata(mode: ConnectivityMode.offline));
      final state = AppState(OfflineApiFake(), offlineStore: store);
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
}
