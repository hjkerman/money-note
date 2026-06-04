import { MonthlyPanel, SpendingCategory } from "./api";

export type CreditUsageTone = {
  level: "quiet" | "steady" | "warning" | "danger";
  message: string;
};

export type SpendingStatTone = {
  key: SpendingCategory | null;
  title: string;
  caption: string;
};

export type PaymentPressureTone = {
  level: "quiet" | "steady" | "warning" | "danger";
  message: string;
};

export type BudgetCommitteeInput = {
  expenseTotal: number;
  expenseCount: number;
  cashFlowTotal: number;
  cashFlowCount: number;
  claimTotal: number;
  claimCount: number;
  settlementTotal: number;
  settlementCount: number;
  frozenTotal: number;
  frozenCount: number;
};

// 청구 항목 자동 분류와 통계 문구에서 사용하는 판단 기준이다.
const SMALL_CLAIM_LIMIT = 2_000;
const ESSENTIAL_CLAIM_PATTERN =
  /(병원|치과|의원|약국|약제|감기|정신과|정형외과|진료|검사|수술|이자|대출|통신|보험|관리비|교통|lpg|가스|유류|주유|하이패스)/;
const QUESTIONABLE_CLAIM_PATTERN = /(커피|카페|빽다방|편지지|간식|술|담배|게임|취미|굿즈)/;

// 같은 장부 상태에는 같은 문구를 돌려주되, 상태가 달라지면 후보 문구도 달라지게 한다.
function chooseJudgment(messages: string[], ...signals: number[]): string {
  const seed = signals.reduce((total, signal, index) => {
    const normalized = Number.isFinite(signal) ? Math.round(Math.abs(signal) * (index + 3)) : 0;
    return (total * 31 + normalized) >>> 0;
  }, 17);
  return messages[seed % messages.length];
}

// 분류 코드를 사용자가 읽는 라벨로 바꾼다.
export function categoryLabel(category: SpendingCategory | null): string {
  if (category === "essential") return "안 썼으면 큰일 났을 돈";
  if (category === "questionable") return "꼭 써야 했을까...?";
  return "미분류";
}

// 소비 통계 카드의 제목과 설명을 제공한다.
export function spendingStatTones(): SpendingStatTone[] {
  return [
    {
      key: "essential",
      title: categoryLabel("essential"),
      caption: "안 썼으면 일이 커졌을 돈. 생존 인프라.",
    },
    {
      key: "questionable",
      title: categoryLabel("questionable"),
      caption: "과거의 내가 예산위원회에 출석해야 합니다.",
    },
    {
      key: null,
      title: "아직 심문 전",
      caption: "판결을 기다리는 소비들.",
    },
  ];
}

// 장부의 모든 주요 변화에 반응하는 상단 예산심사위원회 한 줄 평을 만든다.
export function budgetCommitteeTone(input: BudgetCommitteeInput): CreditUsageTone {
  const activityCount =
    input.expenseCount + input.cashFlowCount + input.claimCount + input.settlementCount + input.frozenCount;
  const say = (messages: string[]) => messages[activityCount % messages.length];

  if (activityCount === 0) {
    return {
      level: "quiet",
      message: say([
          "아직 기록이 없습니다. 예산심사위원회가 의사봉만 닦고 있습니다.",
          "장부가 고요합니다. 평화인지 기록 누락인지는 위원회도 아직 판단을 유보합니다.",
          "이번 달 첫 안건을 기다리는 중입니다. 무소비라면 위업이고 미기록이라면 곧 들통납니다.",
        ]),
    };
  }

  if (input.cashFlowTotal < 0 && Math.abs(input.cashFlowTotal) > input.expenseTotal) {
    return {
      level: "warning",
      message: say([
          "카드보다 현금이 더 적극적으로 퇴장했습니다. 계좌가 별도 의견서를 제출했습니다.",
          "장부의 주연은 카드가 아니라 현금 유출입니다. 예산위원회가 통장 쪽으로 고개를 돌립니다.",
          "현금흐름이 소비 기록보다 큰 목소리를 냅니다. 보이지 않는 지출도 발언권은 있습니다.",
        ]),
    };
  }

  if (input.frozenTotal > input.expenseTotal && input.frozenCount > 0) {
    return {
      level: "steady",
      message: say([
          "쓴 돈보다 동결한 돈이 큽니다. 미래의 소비가 현재의 장부에서 대기번호를 받았습니다.",
          "동결 자산이 당월 지출보다 당당합니다. 아직 사지 않았다는 사실이 이번 달의 절약입니다.",
          "소비 후보군이 실제 소비보다 큽니다. 예산심사위원회가 결정을 미룬 용기를 높이 평가합니다.",
        ]),
    };
  }

  if (input.claimTotal + input.settlementTotal > input.expenseTotal && input.claimCount + input.settlementCount > 0) {
    return {
      level: "steady",
      message: say([
          "본인 소비보다 가족회계의 존재감이 큽니다. 이번 달 장부는 개인전보다 단체전에 가깝습니다.",
          "청구와 정산이 당월 지출보다 활발합니다. 가족이라는 제도가 회계상으로도 실재합니다.",
          "가족 관련 숫자가 장부 전면에 나섰습니다. 신뢰는 유지되고 계산기는 바쁩니다.",
        ]),
    };
  }

  if (input.expenseCount >= 30) {
    return {
      level: "warning",
      message: say([
          "당월 지출 건수가 풍성합니다. 한 건 한 건은 생활이지만 합치면 행정입니다.",
          "소비 기록이 30건을 넘었습니다. 삶이 성실하게 영수증을 생산하고 있습니다.",
          "장부가 제법 두꺼워졌습니다. 예산심사위원회가 속독 능력을 요구받습니다.",
        ]),
    };
  }

  if (input.cashFlowTotal > input.expenseTotal && input.cashFlowTotal > 0) {
    return {
      level: "quiet",
      message: say([
          "현금 유입이 당월 지출보다 큽니다. 예산심사위원회가 이례적으로 칭찬을 결재합니다.",
          "들어온 돈이 쓴 돈보다 우세합니다. 장부가 사용자에게 유리한 증언을 남깁니다.",
          "현재까지는 유입 우세입니다. 재정적 품위가 일시적으로 확인되었습니다.",
        ]),
    };
  }

  if (input.expenseTotal >= 1_000_000) {
    return {
      level: "warning",
      message: say([
          "당월 소비가 일곱 자리에 진입했습니다. 삶의 밀도가 카드 명세서에도 반영되었습니다.",
          "지출 총액이 백만 원을 넘었습니다. 경제에는 기여했고 위원회에는 안건을 제공했습니다.",
          "소비 활동이 매우 적극적입니다. 예산심사위원회가 설명자료의 글자 크기를 줄입니다.",
        ]),
    };
  }

  return {
    level: "quiet",
    message: say([
        "현재까지는 사람 사는 수준의 소란입니다. 예산심사위원회가 관찰 의견만 남깁니다.",
        "장부는 대체로 평온합니다. 소비는 있었고 재난으로 분류되지는 않았습니다.",
        "이번 달 재정은 설명 가능한 범위에서 움직이고 있습니다. 위원회는 일단 믿어보기로 합니다.",
        "기록이 쌓이고 있습니다. 숫자는 정직하며 아직 지나치게 공격적이지 않습니다.",
      ]),
  };
}

// 청구 항목은 사용자가 직접 분류하지 않으므로 제목/금액 기반으로 자동 판정한다.
export function classifyClaimPanel(panel: MonthlyPanel): SpendingCategory | null {
  const title = panel.title.toLowerCase();
  if ((panel.amount_value ?? 0) > 0 && (panel.amount_value ?? 0) <= SMALL_CLAIM_LIMIT) {
    return "questionable";
  }
  if (ESSENTIAL_CLAIM_PATTERN.test(title)) {
    return "essential";
  }
  if (QUESTIONABLE_CLAIM_PATTERN.test(title)) {
    return "questionable";
  }
  return null;
}

// 가족카드 한도 사용률에 따라 화면에 보여줄 경고 톤을 고른다.
export function creditUsageTone(usageRate: number): CreditUsageTone {
  const usagePercent = usageRate * 100;
  if (usageRate >= 0.8) {
    return {
      level: "danger",
      message: chooseJudgment(
        [
          "추정 한도의 80%를 넘었습니다. 카드 명의자는 이제 금융상품이 아니라 금융기반시설입니다.",
          "한도 여백이 장식용으로 변했습니다. 신용평가라는 말이 서류가방을 들고 현관에 와 있습니다.",
          "가족카드가 한도를 생활공간처럼 사용 중입니다. 명의자의 평정심은 별도 예산으로 편성해야겠습니다.",
        ],
        usagePercent,
      ),
    };
  }
  if (usageRate >= 0.5) {
    return {
      level: "danger",
      message: chooseJudgment(
        [
          "추정치가 한도의 절반을 넘었습니다. 신용도라는 단어가 정장을 입고 회의실에 들어옵니다.",
          "한도의 과반이 사용되었습니다. 가족의 소비가 민주적 절차 없이 다수당이 되었습니다.",
          "50% 선을 넘었습니다. 카드 명의자의 침착함이 이번 달의 가장 큰 무이자 할부입니다.",
        ],
        usagePercent,
      ),
    };
  }
  if (usageRate >= 0.3) {
    return {
      level: "warning",
      message: chooseJudgment(
        [
          "추정치가 한도의 30%를 넘었습니다. 아직 사고는 아니지만, 카드 명의자의 표정은 회계감사 모드입니다.",
          "현실과 타협하던 구간을 이탈했습니다. 가족카드 사용내역에 해명자료가 붙기 시작합니다.",
          "30% 초과입니다. 한도는 넉넉하지만 명의자의 마음에는 이미 임시제한이 걸렸습니다.",
          "카드는 정상 작동 중입니다. 다만 명의자의 심박수가 부가서비스처럼 따라옵니다.",
        ],
        usagePercent,
      ),
    };
  }
  if (usageRate >= 0.2) {
    return {
      level: "steady",
      message: chooseJudgment(
        [
          "한도의 20-30% 구간입니다. 현실과 타협은 했지만, 협상문 초안은 보관해두겠습니다.",
          "아직 권장 현실 범위입니다. 명의자는 웃고 있으나 눈은 한도 숫자를 보고 있습니다.",
          "사용량은 무난합니다. 가족 신용공동체의 평화가 조심스럽게 유지되고 있습니다.",
        ],
        usagePercent,
      ),
    };
  }
  if (usageRate >= 0.1) {
    return {
      level: "steady",
      message: chooseJudgment(
        [
          "한도의 10-20% 구간입니다. 카드사와 명의자 모두 비교적 예의 바른 표정입니다.",
          "꾸준한 사용의 모범답안 근처입니다. 이례적으로 회의록에 칭찬이 들어갑니다.",
          "이 정도면 신용은 일하고 불안은 휴가 중입니다.",
        ],
        usagePercent,
      ),
    };
  }
  return {
    level: "quiet",
    message: chooseJudgment(
      [
        "한도의 10% 아래입니다. 이상적인 사용량이지만, 인생이 늘 이상적이면 가계부가 이렇게 재밌진 않았겠지요.",
        "가족카드가 거의 명예직으로 근무 중입니다. 명의자의 혈압도 정상 범위입니다.",
        "한도 사용률이 얌전합니다. 신용평가위원회가 안건 부족으로 조기 퇴근합니다.",
      ],
      usagePercent,
    ),
  };
}

// 결제일과 정규 유동성 대비 미결제액을 바탕으로 카드 결제 심사평을 만든다.
export function paymentPressureTone(
  remainingAmount: number,
  daysUntilDue: number,
  regularLiquidity: number,
): PaymentPressureTone {
  const liquidityRate = regularLiquidity > 0 ? remainingAmount / regularLiquidity : remainingAmount > 0 ? 2 : 0;
  const signals = [remainingAmount, daysUntilDue, liquidityRate * 100];

  if (remainingAmount <= 0) {
    return {
      level: "quiet",
      message: chooseJudgment(
        [
          "이번 달 카드 채무는 정리되었습니다. 예산위원회가 드물게 박수를 칩니다.",
          "미결제액 0원. 파산심사위원회가 할 일을 잃고 예산심사위원회에 커피를 얻어 마십니다.",
          "결제 완료입니다. 카드사는 만족했고 장부는 잠시 인간을 신뢰하기로 했습니다.",
          "이번 회차는 무사 종결입니다. 재정적 품위가 아주 잠깐 관측되었습니다.",
        ],
        ...signals,
      ),
    };
  }

  if (daysUntilDue < 0) {
    return {
      level: "danger",
      message: chooseJudgment(
        [
          "결제일이 지났는데 미결제 기록이 남았습니다. 파산자는 아니겠지만 장부는 그렇게 증언 중입니다.",
          "결제일 경과 기록이 발견되었습니다. 현실에서는 결제됐겠지만 장부는 현재 묵비권을 행사 중입니다.",
          "14일은 지나갔고 미결제 기록은 남았습니다. 파산심사위원회가 사실관계 확인서를 요청합니다.",
          "정규결제 완료로 의제할 시점입니다. 유동성 보정 전까지 장부의 증언은 다소 공격적입니다.",
        ],
        ...signals,
      ),
    };
  }

  if (daysUntilDue === 0) {
    return {
      level: "danger",
      message: chooseJudgment(
        [
          "오늘이 결제일입니다. 지금 남은 금액은 숫자가 아니라 일정입니다.",
          "결제일 당일입니다. 파산심사위원회가 회의가 아니라 생중계를 시작했습니다.",
          "오늘까지입니다. 카드값과 유동성이 이제 서면이 아닌 대면 협상에 들어갑니다.",
        ],
        ...signals,
      ),
    };
  }

  if (liquidityRate >= 2) {
    return {
      level: "danger",
      message: chooseJudgment(
        [
          "미결제액이 심사 기준 수입의 두 배를 넘었습니다. 파산심사위원회가 회의실을 대회의실로 변경했습니다.",
          "기준 수입 두 회분 이상이 남았습니다. 아직 시간은 있지만 숫자의 태도가 매우 불손합니다.",
          "미결제액이 기준 수입을 두 번 설명해야 하는 규모입니다. 위원회가 보조자료를 요구합니다.",
        ],
        ...signals,
      ),
    };
  }

  if (daysUntilDue <= 2 || liquidityRate >= 1.5) {
    return {
      level: "danger",
      message: chooseJudgment(
        [
          "결제일과 미결제액이 함께 압박 중입니다. 파산심사위원회가 서류철을 펼쳤습니다.",
          "남은 날짜는 짧고 금액은 당당합니다. 재정적 겸손을 가르칠 시간이 되었습니다.",
          "상환 의지는 충분하겠지만 달력은 의지를 결제수단으로 받지 않습니다.",
          "위험 구간입니다. 지금 필요한 것은 낙관이 아니라 계좌 잔액과 버튼 클릭입니다.",
        ],
        ...signals,
      ),
    };
  }

  if (daysUntilDue <= 5 && liquidityRate >= 0.75) {
    return {
      level: "warning",
      message: chooseJudgment(
        [
          "결제일까지 닷새 이내인데 금액도 조용하지 않습니다. 위원회가 일정표와 통장을 번갈아 봅니다.",
          "시간과 금액이 동시에 협조적이지 않습니다. 아직 해명 기회는 남아 있습니다.",
          "결제일이 가까워졌습니다. 미결제액은 아직 숫자지만 곧 일정이 됩니다.",
        ],
        ...signals,
      ),
    };
  }

  if (liquidityRate >= 1) {
    return {
      level: "warning",
      message: chooseJudgment(
        [
          "심사 기준 수입보다 미결제액의 목소리가 큽니다. 아직 파산자는 아니지만 해명이 필요합니다.",
          "남은 카드값이 기준 수입 한 회분을 넘었습니다. 달력에 여유가 있을 때 숫자를 낮춰두는 편이 품위 있습니다.",
          "기준 수입을 초과한 미결제액입니다. 위원회가 '계획된 일인지'를 정중하게 묻습니다.",
          "금액만 보면 경고 구간입니다. 시간이 있다는 이유로 위원회를 실망시키지 마십시오.",
        ],
        ...signals,
      ),
    };
  }

  if (daysUntilDue <= 5) {
    return {
      level: "warning",
      message: chooseJudgment(
        [
          "금액은 감당 가능하지만 결제일이 가깝습니다. 미루기의 수익률은 늘 0%입니다.",
          "닷새 이내입니다. 충분히 낼 수 있는 돈을 늦게 내는 것은 장부가 특히 싫어하는 장르입니다.",
          "금액보다 달력이 더 위협적입니다. 즉시결제 버튼이 평소보다 친절해 보일 시점입니다.",
        ],
        ...signals,
      ),
    };
  }

  if (liquidityRate >= 0.75) {
    return {
      level: "steady",
      message: chooseJudgment(
        [
          "미결제액이 심사 기준 수입의 상당 부분을 차지합니다. 아직 평온하지만 의자는 반듯하게 앉으십시오.",
          "감당 가능한 범위의 상단입니다. 예산위원회가 질문지를 작성하다가 아직 보내지는 않았습니다.",
          "당장은 괜찮습니다. 다만 다음 소비가 이 문장의 분위기를 바꿀 수 있습니다.",
        ],
        ...signals,
      ),
    };
  }

  if (liquidityRate >= 0.5) {
    return {
      level: "steady",
      message: chooseJudgment(
        [
          "결제액이 심사 기준 수입의 절반을 넘었습니다. 예산위원회가 안경을 고쳐 쓰는 중입니다.",
          "기준 수입의 절반 이상이 아직 카드사 관할입니다. 통제 가능하지만 방심은 유료입니다.",
          "절반을 넘긴 미결제액입니다. 위원회는 낙관을 허용하되 근거를 요구합니다.",
        ],
        ...signals,
      ),
    };
  }

  if (liquidityRate >= 0.2) {
    return {
      level: "quiet",
      message: chooseJudgment(
        [
          "미결제액은 통제 가능한 범위입니다. 파산심사위원회는 관찰 의견만 남깁니다.",
          "아직 평온합니다. 카드값이 존재감을 드러내지만 발언권은 없습니다.",
          "상환 계획에 무리가 없어 보입니다. 위원회가 드물게 문장을 짧게 씁니다.",
        ],
        ...signals,
      ),
    };
  }

  return {
    level: "quiet",
    message: chooseJudgment(
      [
        "미결제액은 아직 통제 가능한 범위입니다. 파산심사위원회는 오늘 휴회합니다.",
        "남은 카드값이 얌전합니다. 장부가 사용자를 의심하지 않는 드문 시간입니다.",
        "상환 여력에 비해 미결제액이 작습니다. 위원회가 안건을 반려하고 점심을 먹으러 갑니다.",
        "재정적 기상 상태는 맑음입니다. 다만 카드 사용은 언제나 국지성 호우를 동반할 수 있습니다.",
      ],
      ...signals,
    ),
  };
}
