import 'dart:async';
import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_data.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

import 'support/offline_mode_fixtures.dart';

class DelayedRefreshApiFake extends OfflineApiFake {
  final summaryRequested = Completer<void>();
  final releaseSummary = Completer<void>();

  @override
  Future<Summary> summary() async {
    if (!summaryRequested.isCompleted) summaryRequested.complete();
    await releaseSummary.future;
    return super.summary();
  }
}

class ChangingBaselineApiFake extends OfflineApiFake {
  int baselineCalls = 0;

  @override
  Future<Map<String, dynamic>> offlineReconciliationBaseline() async {
    baselineCalls += 1;
    final fingerprint = baselineCalls == 1
        ? baselineFixture().serverStateFingerprint
        : OfflineApiFake.currentFingerprint;
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

class AbaRefreshApiFake extends OfflineApiFake {
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

class OverlappingRefreshApiFake extends OfflineApiFake {
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

class DelayedMutationApiFake extends OfflineApiFake {
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('online refresh baseline and connection classification', () {
    test(
        'successful refresh replaces baseline; incomplete refresh preserves it',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = OfflineApiFake()..available = true;
      final store = offlineStoreFixture(directory);
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;

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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture());
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
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      final api = DelayedRefreshApiFake()..available = true;
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;

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
      final directory = await temporaryDirectoryFixture();
      final api = ChangingBaselineApiFake()..available = true;
      final store = offlineStoreFixture(directory);
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;

      await state.refresh();

      expect(api.baselineCalls, 4);
      expect(state.summary!.remainingLiquidity, 9000);
      final installed = await store.loadBaseline();
      expect(installed!.summary.remainingLiquidity, 9000);
      expect(installed.serverStateFingerprint, OfflineApiFake.currentFingerprint);
    });
    test('A-B-A with equal fingerprint rejects middle display by revision',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = AbaRefreshApiFake()..available = true;
      final store = offlineStoreFixture(directory);
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;
      await state.refresh();
      expect(api.envelopeCalls, 4);
      expect(state.summary!.remainingLiquidity, 100000);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 100000);
    });

    test('evaluation date change rejects stale display even without DB change',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      final api = AbaRefreshApiFake()
        ..available = true
        ..changeEvaluationDate = true;
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;
      await expectLater(state.refresh(), throwsA(isA<MoneyNoteApiException>()));
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 10000);
    });

    test('newer ONLINE refresh wins when its response completes first',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final api = OverlappingRefreshApiFake()..available = true;
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;
      final first = state.refresh();
      await api.firstRequested.future;
      final second = state.refresh();
      await api.secondRequested.future;
      api.secondResult.complete(baselineFixture(remainingLiquidity: 101234).summary);
      await second;
      api.firstResult.complete(baselineFixture(remainingLiquidity: 100000).summary);
      await expectLater(first, throwsA(isA<MoneyNoteApiException>()));
      expect(state.summary!.remainingLiquidity, 101234);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 101234);
    });

    test('newer ONLINE refresh wins when older response completes first',
        () async {
      final directory = await temporaryDirectoryFixture();
      final store = offlineStoreFixture(directory);
      final api = OverlappingRefreshApiFake()..available = true;
      final state = AppState(api, offlineStore: store)..user = baselineFixture().user;
      final first = state.refresh();
      await api.firstRequested.future;
      final second = state.refresh();
      await api.secondRequested.future;
      api.firstResult.complete(baselineFixture(remainingLiquidity: 100000).summary);
      await expectLater(first, throwsA(isA<MoneyNoteApiException>()));
      api.secondResult.complete(baselineFixture(remainingLiquidity: 101234).summary);
      await second;
      expect(state.summary!.remainingLiquidity, 101234);
      expect((await store.loadBaseline())!.summary.remainingLiquidity, 101234);
    });
    test('AppState mutation single-flight rejects concurrent re-entry',
        () async {
      final directory = await temporaryDirectoryFixture();
      final api = DelayedMutationApiFake()..available = true;
      final state = AppState(api, offlineStore: offlineStoreFixture(directory))
        ..user = baselineFixture().user;

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
      final directory = await temporaryDirectoryFixture();
      final store = OfflineStore(
        directoryProvider: () async => directory,
        beforeJournalAppendWrite: () async {
          throw const OfflinePersistenceException(
              'injected journal disk failure');
        },
      );
      await store.replaceBaseline(baselineFixture(remainingLiquidity: 10000));
      await saveLinkedMetadata(
          store,
          const OfflineWorkspaceMetadata(
            mode: ConnectivityMode.offline,
          ));
      final state = AppState(OfflineApiFake(), offlineStore: store);
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
}
