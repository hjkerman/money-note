import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/api_client.dart';
import 'package:money_note_mobile/src/app_state.dart';
import 'package:money_note_mobile/src/models.dart';

LedgerEntry _entry({
  required int id,
  required String date,
  int sortOrder = 1,
  String usagePlace = '사용처',
  int? manualDiscount,
  bool automaticDiscountEligible = true,
}) {
  final effectiveDiscount = manualDiscount ?? 0;
  return LedgerEntry(
    id: id,
    bookSection: 'current',
    entryKind: 'expense',
    title: '',
    sortOrder: sortOrder,
    entryDate: date,
    usagePlace: usagePlace,
    amountValue: 10000,
    paymentKey: 'payment-$id',
    auxAmountValue: manualDiscount,
    discountOverride: manualDiscount == null ? 0 : 1,
    automaticDiscountEligible: automaticDiscountEligible,
    effectiveDiscountAmount: effectiveDiscount,
    effectiveAmountValue: 10000 - effectiveDiscount,
  );
}

void main() {
  test('모바일 원장은 날짜와 등록 id가 최신인 항목부터 표시한다', () {
    final state = AppState(
      MoneyNoteApiClient(baseUrl: 'https://example.invalid'),
    );
    state.entries = [
      _entry(id: 1, date: '2026-07-01'),
      _entry(id: 2, date: '2026-07-01'),
      _entry(id: 3, date: '2026-07-02'),
    ];

    expect(state.expenseEntries.map((entry) => entry.id), [3, 2, 1]);
  });

  test('서버가 계산한 할인 제외와 수동 실결제액을 그대로 사용한다', () {
    final automatic = _entry(
      id: 1,
      date: '2026-07-01',
      usagePlace: '모바일 교통비',
      automaticDiscountEligible: false,
    );
    final manual = _entry(
      id: 2,
      date: '2026-07-01',
      usagePlace: '하이패스',
      manualDiscount: 1200,
    );

    expect(automatic.isDiscountIneligible, isTrue);
    expect(automatic.effectiveDiscountAmount, 0);
    expect(manual.effectiveDiscountAmount, 1200);
    expect(manual.effectiveAmount, 8800);
  });
}
