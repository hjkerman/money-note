import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';

class _RegistrationApi extends MoneyNoteApiClient {
  _RegistrationApi() : super(baseUrl: 'https://example.invalid');

  String? lastKey;
  int? lastDiscountAmount;
  int discountPatchCalls = 0;
  int panelDiscountPatchCalls = 0;
  bool failPanelDiscount = false;

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
  }) async {
    lastKey = candidateRegistrationKey;
    return MonthlyPanel(
      id: 2,
      month: month,
      panelType: panelType,
      title: title,
      sortOrder: 1,
      discountAmount: 0,
      discountOverride: 0,
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
  _FailingRefreshState(super.api);

  @override
  Future<void> refreshInputArea({bool notify = true}) async {
    throw StateError('refresh failed');
  }

  @override
  Future<void> refreshSettlementArea({bool notify = true}) async {
    throw StateError('refresh failed');
  }
}

void main() {
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

  test('가족 사용 후보의 명시적 할인 제외는 패널 할인 요청으로 전달한다', () async {
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
    expect(api.panelDiscountPatchCalls, 1);
  });

  test('가족 사용 후보의 할인 제외 실패는 후보를 남겨 같은 key로 재시도한다', () async {
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

    expect(await register(), isFalse);
    expect(state.statusMessage, contains('동일 후보로 다시 등록'));
    expect(api.lastKey, 'woori_card:family-retry');
    api.failPanelDiscount = false;
    expect(await register(), isTrue);
    expect(api.lastKey, 'woori_card:family-retry');
    expect(api.panelDiscountPatchCalls, 2);
  });
}
