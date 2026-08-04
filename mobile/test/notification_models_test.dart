import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/models.dart';

void main() {
  test('구버전 우리카드 후보 JSON을 그대로 읽는다', () {
    final candidate = CardNotificationCandidate.fromJson({
      'id': 'legacy',
      'captured_at': 1,
      'card_last4': '9452',
      'card_role': 'owner',
      'entry_date': '2026-08-04',
      'amount': 450,
      'merchant': '사용처',
      'raw_text': '원문',
    });

    expect(candidate.source, 'woori_card');
    expect(candidate.usageItem, '');
    expect(candidate.amount, 450);
    expect(candidate.isHighwayToll, isFalse);
  });

  test('금액 미확인 통행료 후보 JSON을 빈 금액으로 읽는다', () {
    final candidate = CardNotificationCandidate.fromJson({
      'id': 'toll',
      'source': 'highway_toll',
      'captured_at': 1,
      'card_role': 'owner',
      'entry_date': '2026-08-04',
      'amount': null,
      'merchant': '통행료',
      'usage_item': '미지정-고양',
      'raw_text': '원문',
    });

    expect(candidate.isHighwayToll, isTrue);
    expect(candidate.amount, isNull);
    expect(candidate.usageItem, '미지정-고양');
  });
}
