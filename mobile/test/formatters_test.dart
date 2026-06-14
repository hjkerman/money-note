import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/formatters.dart';

void main() {
  test('원화 금액을 한국어 UI에 맞게 표시한다', () {
    expect(won(128000), '128,000원');
  });

  test('날짜를 모바일 목록용 짧은 형식으로 표시한다', () {
    expect(shortDate('2026-07-01'), '07/01');
  });
}
