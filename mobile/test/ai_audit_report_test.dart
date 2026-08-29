import 'package:flutter_test/flutter_test.dart';
import 'package:money_note_mobile/src/ai_audit_report.dart';
import 'package:money_note_mobile/src/models.dart';

const _stubAuditInstructions = '테스트용 회계감사 지침';

Summary _summary({
  int scheduledIncome = 1459200,
  int cashFlowBalance = 700000,
  int remainingLiquidity = 300000,
}) {
  return Summary(
    scheduledIncome: scheduledIncome,
    cardTotal: 0,
    currentSpendingTotal: 0,
    currentDiscountTotal: 0,
    plannedRecurringTotal: 0,
    fixedCashTotal: 0,
    frozenAssetTotal: 0,
    cashFlowBalance: cashFlowBalance,
    remainingLiquidity: remainingLiquidity,
    claimOriginalTotal: 0,
    claimNetTotal: 0,
    familyCardOriginalTotal: 0,
    familyCardNetTotal: 0,
    visibleCashFlowTotal: 0,
  );
}

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
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Summary가 서버의 재무 기준선 값을 그대로 읽는다', () {
    final summary = Summary.fromJson({
      'scheduled_income': 1459200,
      'cash_flow_balance': 823450,
      'remaining_liquidity': 412300,
      'card_total': 0,
      'current_spending_total': 0,
      'current_discount_total': 0,
      'planned_recurring_total': 0,
      'fixed_cash_total': 0,
      'frozen_asset_total': 0,
      'claim_original_total': 0,
      'claim_net_total': 0,
      'family_card_original_total': 0,
      'family_card_net_total': 0,
      'visible_cash_flow_total': 0,
    });

    expect(summary.scheduledIncome, 1459200);
    expect(summary.cashFlowBalance, 823450);
    expect(summary.remainingLiquidity, 412300);
  });

  test('실제 데이터가 있고 서버 당월보다 늦지 않은 연월만 선택지로 만든다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      summary: _summary(),
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
      auditInstructions: _stubAuditInstructions,
    );

    expect(data.availableMonths, ['2026-08', '2026-07', '2026-06']);
  });

  test('선택 월의 서버 계산 금액과 회계감사 지침을 Markdown으로 묶는다', () async {
    final auditInstructions = await loadAuditInstructions();
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      summary: _summary(),
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
      auditInstructions: auditInstructions,
    );

    final markdown = data.buildMarkdown(
      '2026-08',
      generatedAt: DateTime.parse('2026-08-17T12:00:00+09:00'),
    );

    expect(markdown, contains('# Money-Note 회계감사 자료 - 2026년 8월'));
    expect(markdown, contains('당신은 개인 가계부 서비스 Money Note의 외부 회계감사관입니다.'));
    expect(markdown, contains('객관적인 생존 필수 여부가 아니라'));
    expect(markdown, contains('지속 가능한 일상생활의 baseline'));
    expect(markdown, contains('합리적인 삶의 질과 사회생활'));
    expect(markdown, contains('품목명만을 근거로 사용자의 소비 분류가 잘못되었다고 판단하지 마세요'));
    expect(markdown, contains('목적이나 귀속 월을 추적하지 않습니다'));
    expect(markdown, contains('특정 카드 지출을 과거의 특정 동결액과 연결하지 마세요'));
    expect(markdown, contains('잔여 유동성을 평가할 때만 고려하세요'));
    expect(markdown, contains('세 개념을 서로 바꾸어 해석하지 마세요'));
    expect(markdown, contains('## 현재 재무 상태'));
    expect(markdown, contains('| 기준 월 수입 | 1,459,200원 |'));
    expect(markdown, contains('| Active 계좌 잔액 | 700,000원 |'));
    expect(markdown, contains('| 잔여 유동성 | 300,000원 |'));
    expect(markdown, contains('## 재무 운용 기준'));
    expect(markdown, contains('다음 급여 예정액을 현재 신용카드 사용의 재원으로 선반영하는'));
    expect(markdown, contains('이미 확보된 현금 범위에서 다음 예산 주기를 운영'));
    expect(
        markdown, contains('선택 월의 현금흐름 합계는 현재 Active 계좌 잔액이나 현재 잔여 유동성이 아닙니다'));
    expect(markdown, contains('계산은 Money Note 서버가, 해석은 회계감사가 담당합니다'));
    expect(markdown, contains('`scheduled_income`은 Money Note에 설정된 기준 월 수입'));
    expect(markdown, contains('장부 오류, 현금흐름 중복 또는 Summary 버그로 판단하지 마세요'));
    expect(markdown, contains('현재 소비 패턴의 지속 가능성을 자동으로 보장하지는 않습니다'));
    expect(markdown, contains('문제가 없다면 억지로 지출 축소를 권하지 마세요'));
    expect(markdown, contains('해당 항목은 판단을 유보하고'));
    expect(markdown, contains('필요한 추가 맥락을 구체적으로 질문하세요'));
    expect(markdown, contains('사용자가 답변한 경우 이후 판단에 반영하세요'));
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
    expect(markdown, contains('template의 예정 부담'));
    expect(markdown, contains('확인된 현금성 고정지출의 실제 출금액은 현금흐름에'));
    expect(markdown, contains('확정된 카드 정기결제의 실제 원금은 본인 카드 지출에'));
    expect(markdown, contains('해동하여 삭제한 과거 항목은 포함되지 않으며'));
    expect(markdown, isNot(contains('2026-07-31')));
  });

  test('과거 월 현금흐름과 보고서 생성 시점 Summary를 구분한다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      summary: _summary(
        scheduledIncome: 1459200,
        cashFlowBalance: 700000,
        remainingLiquidity: 300000,
      ),
      ledgerEntries: [_entry(id: 1, date: '2026-05-02')],
      cashFlows: [
        CashFlow(
          id: 1,
          occurredOn: '2026-05-01',
          title: '선택 월 현금흐름',
          amountValue: 100000,
          sortOrder: 1,
          isPrimaryIncome: false,
        ),
      ],
      panels: const [],
      confirmedPlannedEntries: const [],
      auditInstructions: _stubAuditInstructions,
    );

    final markdown = data.buildMarkdown(
      '2026-05',
      generatedAt: DateTime.parse('2026-08-17T12:00:00+09:00'),
    );

    expect(markdown, contains('| 2026-05-01 | 선택 월 현금흐름 | +100,000원 |'));
    expect(markdown, contains('| 기준 월 수입 | 1,459,200원 |'));
    expect(markdown, contains('| Active 계좌 잔액 | 700,000원 |'));
    expect(markdown, contains('| 잔여 유동성 | 300,000원 |'));
    expect(markdown, contains('선택 월 당시의 historical snapshot이 아니라'));
  });

  test('확정된 실제액과 현재 template 예정액을 서로 다른 영역에 출력한다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      summary: _summary(),
      ledgerEntries: [
        _entry(
          id: 1,
          date: '2026-08-12',
          place: '통신사',
          item: '확정된 카드 정기결제',
          amount: 12000,
          discount: 144,
        ),
        _plannedEntry(
          id: 2,
          dueDay: 12,
          place: '통신사',
          item: '카드 정기결제 template',
          amount: 15000,
        ),
      ],
      cashFlows: [
        CashFlow(
          id: 1,
          occurredOn: '2026-08-05',
          title: '확인된 현금성 고정지출',
          amountValue: -275000,
          sortOrder: 1,
          isPrimaryIncome: false,
        ),
      ],
      panels: [
        _panel(
          id: 1,
          type: 'fixed',
          date: '2026-08-01',
          title: '현금성 고정지출 template',
          amount: 300000,
          discount: 0,
        ),
      ],
      confirmedPlannedEntries: const [],
      auditInstructions: _stubAuditInstructions,
    );

    final markdown = data.buildMarkdown('2026-08');

    expect(
      markdown,
      contains('통신사 | 확정된 카드 정기결제 | 최소한의 품위유지비 | 12,000원 | 144원 | 11,856원'),
    );
    expect(markdown, contains('확인된 현금성 고정지출 | -275,000원'));
    expect(markdown, contains('현금성 고정지출 template | 300,000원'));
    expect(
      markdown,
      contains('매월 12일 | 통신사 | 카드 정기결제 template | 15,000원'),
    );
  });

  test('현재 운영 참고자료가 비어 있어도 Summary를 포함한다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      summary: _summary(),
      ledgerEntries: [_entry(id: 1, date: '2026-08-02')],
      cashFlows: const [],
      panels: const [],
      confirmedPlannedEntries: const [],
      auditInstructions: _stubAuditInstructions,
    );

    final markdown = data.buildMarkdown('2026-08');

    expect(markdown, contains('| 기준 월 수입 | 1,459,200원 |'));
    expect(markdown, contains('| Active 계좌 잔액 | 700,000원 |'));
    expect(markdown, contains('_현재 설정된 현금성 고정지출 없음_'));
    expect(markdown, contains('_현재 설정된 카드 정기결제 없음_'));
    expect(markdown, contains('_현재 남아 있는 동결 금액 없음_'));
  });

  test('데이터가 없는 연월의 보고서 생성을 거부한다', () {
    final data = AiAuditReportData(
      latestAllowedMonth: '2026-08',
      summary: _summary(),
      ledgerEntries: [_entry(id: 1, date: '2026-08-02')],
      cashFlows: const [],
      panels: const [],
      confirmedPlannedEntries: const [],
      auditInstructions: _stubAuditInstructions,
    );

    expect(() => data.buildMarkdown('2026-07'), throwsArgumentError);
  });
}
