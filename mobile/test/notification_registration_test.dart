import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';

class _RegistrationApi extends MoneyNoteApiClient {
  _RegistrationApi() : super(baseUrl: 'https://example.invalid');

  String? lastKey;

  @override
  Future<LedgerEntry> createExpense({
    required String date,
    required String usagePlace,
    required String usageItem,
    required int amount,
    String? spendingCategory,
    String? candidateRegistrationKey,
  }) async {
    lastKey = candidateRegistrationKey;
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
      amountValue: amount,
      spentOn: spentOn,
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
}
