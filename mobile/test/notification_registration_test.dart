import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';
import 'package:money_note_mobile/src/offline/offline_store.dart';

class _RegistrationApi extends MoneyNoteApiClient {
  _RegistrationApi() : super(baseUrl: 'https://example.invalid');

  String? lastKey;
  String? lastPanelMonth;
  int? lastDiscountAmount;
  int discountPatchCalls = 0;
  int panelDiscountPatchCalls = 0;
  bool? lastInitialDiscountEnabled;
  bool failPanelDiscount = false;
  bool losePanelResponseOnce = false;
  final panelKeys = <String?>[];

  @override
  Future<LedgerEntry> createExpense({
    required String date,
    required String usagePlace,
    required String usageItem,
    required int amount,
    required bool discountEnabled,
    int? discountOverrideAmount,
    String? spendingCategory,
    String? candidateRegistrationKey,
  }) async {
    lastKey = candidateRegistrationKey;
    lastDiscountAmount = discountOverrideAmount;
    return LedgerEntry(
      id: 1,
      bookSection: 'current',
      entryKind: 'expense',
      title: usagePlace,
      sortOrder: 1,
      entryDate: date,
      usagePlace: usagePlace,
      usageItem: usageItem,
      amountValue: amount,
      paymentKey: 'entry-1',
    );
  }

  @override
  Future<LedgerEntry> updateEntryDiscount(
      String entryPaymentKey, int discountAmount) async {
    lastDiscountAmount = discountAmount;
    discountPatchCalls += 1;
    return LedgerEntry(
      id: 1,
      bookSection: 'current',
      entryKind: 'expense',
      title: '가게',
      sortOrder: 1,
      amountValue: 1000,
      paymentKey: entryPaymentKey,
      auxAmountValue: discountAmount,
      discountOverride: 1,
      effectiveDiscountAmount: discountAmount,
      effectiveAmountValue: 1000 - discountAmount,
    );
  }

  @override
  Future<MonthlyPanel> createPanel({
    required String month,
    required String panelType,
    required String title,
    required int amount,
    String? spentOn,
    String? candidateRegistrationKey,
    bool? initialDiscountEnabled,
  }) async {
    lastKey = candidateRegistrationKey;
    panelKeys.add(candidateRegistrationKey);
    lastInitialDiscountEnabled = initialDiscountEnabled;
    lastPanelMonth = month;
    if (losePanelResponseOnce) {
      losePanelResponseOnce = false;
      throw MoneyNoteConnectionException('injected response loss');
    }
    return MonthlyPanel(
      id: 2,
      month: month,
      panelType: panelType,
      title: title,
      sortOrder: 1,
      discountAmount: 0,
      discountOverride: initialDiscountEnabled == false ? 1 : 0,
      automaticDiscountEligible: true,
      amountValue: amount,
      spentOn: spentOn,
    );
  }

  @override
  Future<MonthlyPanel> excludePanelDiscount(int panelId) async {
    panelDiscountPatchCalls += 1;
    if (failPanelDiscount) {
      throw MoneyNoteApiException('injected panel discount failure');
    }
    return MonthlyPanel(
      id: panelId,
      month: '2026-09',
      panelType: 'family_card',
      title: '가게',
      sortOrder: 1,
      discountAmount: 0,
      discountOverride: 1,
      amountValue: 1000,
    );
  }
}

class _FailingRefreshState extends AppState {
  _FailingRefreshState(super.api, {super.offlineStore});

  @override
  Future<void> refreshInputArea({bool notify = true}) async {
    throw StateError('refresh failed');
  }

  @override
  Future<void> refreshSettlementArea({bool notify = true}) async {
    throw StateError('refresh failed');
  }
}

class _SuccessfulPanelRefreshState extends AppState {
  _SuccessfulPanelRefreshState(super.api, {super.offlineStore});

  @override
  Future<void> refreshSettlementArea({bool notify = true}) async {}
}

void main() {
  test(
      'definitively rejected first manual create must not strand its retry key',
      () async {
    final directory =
        await Directory.systemTemp.createTemp('money-note-manual-reject-');
    addTearDown(() async => directory.delete(recursive: true));
    final store = OfflineStore(directoryProvider: () async => directory);
    final api = MoneyNoteApiClient(
      baseUrl: 'https://example.invalid',
      client: MockClient((request) async => http.Response(
          '{"detail":"invalid panel"}', 400,
          headers: {'content-type': 'application/json'})),
    );
    final state = AppState(api, offlineStore: store);
    expect(
        await state.createPanel(
          panelType: 'claim',
          title: '거절될 청구',
          amount: 500,
          spentOn: '2026-09-17',
          manualRegistrationKey: 'manual-panel-rejected',
        ),
        isFalse);
    expect(await store.hasPendingManualPanelRetry(), isFalse);
  });

  test('a later validation error cannot discard an already ambiguous retry',
      () async {
    final directory =
        await Directory.systemTemp.createTemp('money-note-ambiguous-reject-');
    addTearDown(() async => directory.delete(recursive: true));
    OfflineStore store() =>
        OfflineStore(directoryProvider: () async => directory);
    final first = _SuccessfulPanelRefreshState(
        _RegistrationApi()..losePanelResponseOnce = true,
        offlineStore: store());
    Future<bool> submit(AppState state) => state.createPanel(
          panelType: 'claim',
          title: '미확정 청구',
          amount: 500,
          spentOn: '2026-09-17',
          manualRegistrationKey: 'manual-panel-ambiguous',
        );
    expect(await submit(first), isFalse);
    final rejecting = AppState(
      MoneyNoteApiClient(
        baseUrl: 'https://example.invalid',
        client: MockClient((request) async =>
            http.Response('{"detail":"invalid panel"}', 400)),
      ),
      offlineStore: store(),
    );
    expect(await submit(rejecting), isFalse);
    expect(await store().hasPendingManualPanelRetry(), isTrue);
  });

  test('후보 원장은 저장 응답 이후 갱신 실패에도 성공으로 처리한다', () async {
    final api = _RegistrationApi();
    final state = _FailingRefreshState(api);

    final success = await state.createExpense(
      usagePlace: '가게',
      usageItem: '지출',
      amount: 1000,
      discountEnabled: true,
      entryDate: '2026-09-01',
      candidateRegistrationKey: 'woori_card:card-a',
    );

    expect(success, isTrue);
    expect(api.lastKey, 'woori_card:card-a');
    expect(state.statusMessage, contains('저장됐습니다'));
  });

  test('온라인 실결제액 입력은 최초 create request에 원자적으로 포함한다', () async {
    final api = _RegistrationApi();
    final state = _FailingRefreshState(api);

    final success = await state.createExpense(
      usagePlace: '가게',
      usageItem: '지출',
      amount: 1000,
      discountEnabled: true,
      netAmountOverride: 700,
      entryDate: '2026-09-01',
      candidateRegistrationKey: 'woori_card:card-b',
    );

    expect(success, isTrue);
    expect(api.lastDiscountAmount, 300);
    expect(state.statusMessage, contains('저장됐습니다'));
    expect(api.discountPatchCalls, 0);
  });

  test('후보 청구도 저장 응답과 갱신 실패를 분리한다', () async {
    final api = _RegistrationApi();
    final state = _FailingRefreshState(api);

    final success = await state.createPanel(
      panelType: 'claim',
      title: '가게: 지출',
      amount: 1000,
      discountEnabled: true,
      spentOn: '2026-09-01',
      candidateRegistrationKey: 'woori_card:claim-a',
    );

    expect(success, isTrue);
    expect(api.lastKey, 'woori_card:claim-a');
    expect(state.statusMessage, contains('저장됐습니다'));
  });

  test('가족 사용 후보의 명시적 할인 제외는 최초 생성 요청에 포함한다', () async {
    final api = _RegistrationApi();
    final state = _FailingRefreshState(api);

    final success = await state.createPanel(
      panelType: 'family_card',
      title: '가게',
      amount: 1000,
      discountEnabled: false,
      spentOn: '2026-09-01',
      candidateRegistrationKey: 'woori_card:family-no-discount',
    );

    expect(success, isTrue);
    expect(api.lastKey, 'woori_card:family-no-discount');
    expect(api.lastInitialDiscountEnabled, isFalse);
    expect(api.panelDiscountPatchCalls, 0);
  });

  test('과거 가족카드 알림은 거래월과 할인 의도를 최초 생성에 함께 보낸다', () async {
    final api = _RegistrationApi();
    final state = _FailingRefreshState(api);
    expect(
        await state.createPanel(
          panelType: 'family_card',
          title: '가게',
          amount: 10000,
          discountEnabled: true,
          spentOn: '2026-08-31',
          candidateRegistrationKey: 'woori_card:historical-family',
        ),
        isTrue);
    expect(api.lastPanelMonth, '2026-08');
    expect(api.lastInitialDiscountEnabled, isTrue);
    expect(api.panelDiscountPatchCalls, 0);
  });

  test('가족 사용 후보의 할인 제외는 PATCH 실패 여부와 무관하게 원자적으로 생성한다', () async {
    final api = _RegistrationApi()..failPanelDiscount = true;
    final state = _FailingRefreshState(api);
    Future<bool> register() => state.createPanel(
          panelType: 'family_card',
          title: '가게',
          amount: 1000,
          discountEnabled: false,
          spentOn: '2026-09-01',
          candidateRegistrationKey: 'woori_card:family-retry',
        );

    expect(await register(), isTrue);
    expect(api.lastKey, 'woori_card:family-retry');
    expect(await register(), isTrue);
    expect(api.lastKey, 'woori_card:family-retry');
    expect(api.lastInitialDiscountEnabled, isFalse);
    expect(api.panelDiscountPatchCalls, 0);
  });

  test('수동 정산 응답 유실 후 재시작해도 같은 durable key로 재시도한다', () async {
    final directory =
        await Directory.systemTemp.createTemp('money-note-manual-panel-');
    addTearDown(() async => directory.delete(recursive: true));
    OfflineStore store() =>
        OfflineStore(directoryProvider: () async => directory);
    final api = _RegistrationApi()..losePanelResponseOnce = true;
    final first = _FailingRefreshState(api, offlineStore: store());
    Future<bool> submit(AppState state, String preferred) => state.createPanel(
          panelType: 'claim',
          title: '생활비',
          amount: 10000,
          discountEnabled: false,
          spentOn: '2026-09-17',
          manualRegistrationKey: preferred,
        );
    expect(await submit(first, 'manual-panel-original'), isFalse);
    expect(api.panelKeys, ['manual-panel-original']);
    final restarted = _FailingRefreshState(api, offlineStore: store());
    expect(await submit(restarted, 'manual-panel-new-process'), isFalse);
    expect(api.panelKeys, ['manual-panel-original', 'manual-panel-original']);
    expect(await store().hasPendingManualPanelRetry(), isTrue);
    final recovered = _SuccessfulPanelRefreshState(api, offlineStore: store());
    expect(await submit(recovered, 'manual-panel-after-refresh'), isTrue);
    expect(api.panelKeys.last, 'manual-panel-original');
    expect(await store().hasPendingManualPanelRetry(), isFalse);
    expect(api.lastInitialDiscountEnabled, isFalse);
    expect(api.panelDiscountPatchCalls, 0);
    expect(await submit(recovered, 'manual-panel-new-intent'), isTrue);
    expect(api.panelKeys.last, 'manual-panel-new-intent');
  });

  test('미확정 수동 등록은 재시작 후 원래 입력으로만 확인하고 새 draft key를 오염시키지 않는다', () async {
    final directory =
        await Directory.systemTemp.createTemp('money-note-manual-recovery-');
    addTearDown(() async => directory.delete(recursive: true));
    OfflineStore store() =>
        OfflineStore(directoryProvider: () async => directory);
    final api = _RegistrationApi()..losePanelResponseOnce = true;
    final first = _SuccessfulPanelRefreshState(api, offlineStore: store());
    expect(
        await first.createPanel(
          panelType: 'family_card',
          title: '이전 가족카드',
          amount: 10000,
          discountEnabled: false,
          spentOn: '2026-09-17',
          manualRegistrationKey: 'manual-panel-old',
        ),
        isFalse);
    final restarted = _SuccessfulPanelRefreshState(api, offlineStore: store());
    expect(await restarted.restorePersistedOfflineWorkspace(), isFalse);
    expect(restarted.manualPanelRetryPending, isTrue);
    expect(
        await restarted.createPanel(
          panelType: 'family_card',
          title: '별개 가족카드',
          amount: 700,
          discountEnabled: true,
          spentOn: '2026-09-17',
          manualRegistrationKey: 'manual-panel-new',
        ),
        isFalse);
    expect(api.panelKeys, ['manual-panel-old']);
    expect(await restarted.confirmPendingManualPanelRegistration(), isTrue);
    expect(api.panelKeys, ['manual-panel-old', 'manual-panel-old']);
    expect(restarted.manualPanelRetryPending, isFalse);
    expect(
        await restarted.createPanel(
          panelType: 'family_card',
          title: '별개 가족카드',
          amount: 700,
          discountEnabled: true,
          spentOn: '2026-09-17',
          manualRegistrationKey: 'manual-panel-new',
        ),
        isTrue);
    expect(api.panelKeys.last, 'manual-panel-new');
  });

  test('authoritative refresh 뒤 retry-key cleanup 실패는 restart 확인으로 복구한다',
      () async {
    final directory =
        await Directory.systemTemp.createTemp('money-note-manual-cleanup-');
    addTearDown(() async => directory.delete(recursive: true));
    final api = _RegistrationApi();
    final failingStore = OfflineStore(
      directoryProvider: () async => directory,
      beforeManualRetryCleanup: () async => throw StateError('cleanup failed'),
    );
    final first = _SuccessfulPanelRefreshState(api, offlineStore: failingStore);
    expect(
        await first.createPanel(
          panelType: 'claim',
          title: '기존 청구',
          amount: 500,
          spentOn: '2026-09-17',
          manualRegistrationKey: 'manual-panel-cleanup',
        ),
        isFalse);
    expect(first.manualPanelRetryPending, isTrue);
    expect(api.panelKeys, ['manual-panel-cleanup']);
    final recovered = _SuccessfulPanelRefreshState(api,
        offlineStore: OfflineStore(directoryProvider: () async => directory));
    expect(await recovered.restorePersistedOfflineWorkspace(), isFalse);
    expect(recovered.manualPanelRetryPending, isTrue);
    expect(await recovered.confirmPendingManualPanelRegistration(), isTrue);
    expect(api.panelKeys, ['manual-panel-cleanup', 'manual-panel-cleanup']);
    expect(recovered.manualPanelRetryPending, isFalse);
  });
}
