import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/discount_default.dart';

void main() {
  test('utility descriptions only change the initial checkbox default', () {
    for (final word in ['도시가스', '가스요금', '전기', '전력', '수도']) {
      expect(cardDiscountDefaultEnabled(true, '서울$word', null), isFalse);
      expect(cardDiscountDefaultEnabled(true, '가게', '$word 요금'), isFalse);
    }
    expect(cardDiscountDefaultEnabled(true, '서점', '책'), isTrue);
    expect(cardDiscountDefaultEnabled(false, '서점', '책'), isFalse);
    expect(cardDiscountDefaultEnabled(true, '한국전력', null, explicitChoice: true),
        isTrue);
    expect(
        cardDiscountDefaultEnabled(true, '한국전력', null, explicitChoice: false),
        isFalse);
  });
}
