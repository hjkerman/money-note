import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/ai_audit_report.dart';
import 'package:money_note_mobile/src/models.dart';

LedgerEntry _entry({
  required int id,
  required String date,
  String place = '사용처',
  String item = '세부내역',
  int amount = 10000,
  int discount = 120,
}) {
  return LedgerEntry(
    id: id,
    bookSection: 'archive',
    entryKind: 'expense',
    title: '[$place] $item',
    sortOrder: id,
    entryDate: date,
    usagePlace: place,
    usageItem: item,
    amountValue: amount,
    spendingCategory: 'dignity',
    effectiveDiscountAmount: discount,
    effectiveAmountValue: amount - discount,
  );
}

MonthlyPanel _panel({
  required int id,
  required String type,
  required String date,
  required String title,
  int amount = 20000,
  int discount = 240,
}) {
  return MonthlyPanel(
    id: id,
    month: date.substring(0, 7),
    panelType: type,
    title: title,
    sortOrder: id,
    discountAmount: discount,
    discountOverride: 1,
    spentOn: date,
    amountValue: amount,
    effectiveDiscountAmount: discount,
    effectiveAmountValue: amount - discount,
  );
}

LedgerEntry _plannedEntry({
  required int id,
  required int dueDay,
  required String place,
  String item = '',
  int amount = 15000,
}) {
  return LedgerEntry(
    id: id,
    bookSection: 'current',
    entryKind: 'planned',
    title: item.isEmpty ? place : '[$place] $item',
    sortOrder: id,
    usagePlace: place,
    usageItem: item.isEmpty ? null : item,
    amountValue: amount,
    effectiveAmountValue: amount,
    dueDay: dueDay,
  );
}

void main() {
  test('실제 데이터가 있고 서버 당월보다 늦지 않은 연월만 선택지로 만든다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      ledgerEntries: [
        _entry(id: 1, date: '2026-06-01'),
        _entry(id: 2, date: '2026-09-01'),
      ],
      cashFlows: [
        CashFlow(
          id: 1,
          occurredOn: '2026-08-02',
          title: '용돈',
          amountValue: 400000,
          sortOrder: 1,
          isPrimaryIncome: true,
        ),
      ],
      panels: [
        _panel(
          id: 1,
          type: 'claim',
          date: '2026-07-03',
          title: '생활비',
        ),
      ],
      confirmedPlannedEntries: const [],
    );

    expect(data.availableMonths, ['2026-08', '2026-07', '2026-06']);
  });

  test('선택 월의 서버 계산 금액과 회계감사 지침을 Markdown으로 묶는다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      ledgerEntries: [
        _entry(
          id: 1,
          date: '2026-08-02',
          place: '가게|지점',
          item: '첫 줄\n둘째 줄',
        ),
        _entry(id: 2, date: '2026-07-31'),
        _plannedEntry(
          id: 3,
          dueDay: 5,
          place: '음악 서비스',
          amount: 7900,
        ),
      ],
      cashFlows: [
        CashFlow(
          id: 1,
          occurredOn: '2026-08-01',
          title: '주 수입',
          amountValue: 400000,
          sortOrder: 1,
          isPrimaryIncome: true,
        ),
        CashFlow(
          id: 2,
          occurredOn: '2026-08-03',
          title: '현금 지출',
          amountValue: -5000,
          sortOrder: 2,
          isPrimaryIncome: false,
        ),
      ],
      panels: [
        _panel(
          id: 1,
          type: 'claim',
          date: '2026-08-04',
          title: '약국',
        ),
        _panel(
          id: 2,
          type: 'family_card',
          date: '2026-08-05',
          title: '가족 사용',
        ),
        _panel(
          id: 3,
          type: 'fixed',
          date: '2026-06-01',
          title: '월세',
          amount: 300000,
          discount: 0,
        ),
        _panel(
          id: 4,
          type: 'frozen',
          date: '2026-08-10',
          title: '노트북 교체 자금',
          amount: 500000,
          discount: 0,
        ),
      ],
      confirmedPlannedEntries: [
        _plannedEntry(
          id: 4,
          dueDay: 15,
          place: '통신사',
          item: '휴대전화 요금',
          amount: 55000,
        ),
      ],
    );

    final markdown = data.buildMarkdown(
      '2026-08',
      generatedAt: DateTime.parse('2026-08-17T12:00:00+09:00'),
    );

    expect(markdown, contains('# Money-Note 회계감사 자료 - 2026년 8월'));
    expect(markdown, contains('당신은 개인 가계부 서비스 Money Note의 외부 회계감사관입니다.'));
    expect(markdown, contains('가게\\|지점'));
    expect(markdown, contains('첫 줄 둘째 줄'));
    expect(markdown, contains('10,000원 | 120원 | 9,880원'));
    expect(markdown, contains('+400,000원'));
    expect(markdown, contains('-5,000원'));
    expect(markdown, contains('미정산 청구'));
    expect(markdown, contains('미정산 가족카드'));
    expect(markdown, contains('현재 운영 참고자료'));
    expect(markdown, contains('월세 | 300,000원'));
    expect(markdown, contains('매월 5일 | 음악 서비스'));
    expect(markdown, contains('매월 15일 | 통신사 | 휴대전화 요금 | 55,000원'));
    expect(markdown, contains('2026-08-10 | 노트북 교체 자금 | 500,000원'));
    expect(markdown, contains('선택 월 당시의 이력이 아니라 보고서 생성 시점 현재'));
    expect(markdown, contains('해동하여 삭제한 과거 항목은 포함되지 않으며'));
    expect(markdown, isNot(contains('2026-07-31')));
  });

  test('데이터가 없는 연월의 보고서 생성을 거부한다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      ledgerEntries: [_entry(id: 1, date: '2026-08-02')],
      cashFlows: const [],
      panels: const [],
      confirmedPlannedEntries: const [],
    );

    expect(() => data.buildMarkdown('2026-07'), throwsArgumentError);
  });
}
