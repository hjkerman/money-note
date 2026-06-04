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

// 청구 항목 자동 분류와 통계 문구에서 사용하는 판단 기준이다.
const SMALL_CLAIM_LIMIT = 2_000;
const ESSENTIAL_CLAIM_PATTERN =
  /(병원|치과|의원|약국|약제|감기|정신과|정형외과|진료|검사|수술|이자|대출|통신|보험|관리비|교통|lpg|가스|유류|주유|하이패스)/;
const QUESTIONABLE_CLAIM_PATTERN = /(커피|카페|빽다방|편지지|간식|술|담배|게임|취미|굿즈)/;

// 분류 코드를 사용자가 읽는 라벨로 바꾼다.
export function categoryLabel(category: SpendingCategory | null): string {
  if (category === "essential") return "이건 안 썼으면 큰일 났을 돈";
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
  if (usageRate > 0.5) {
    return {
      level: "danger",
      message: "추정치가 한도의 50%를 넘었습니다. 신용도라는 단어가 정장을 입고 회의실에 들어옵니다.",
    };
  }
  if (usageRate > 0.3) {
    return {
      level: "warning",
      message: "추정치가 한도의 30%를 넘었습니다. 아직 사고는 아니지만, 카드 명의자의 표정은 회계감사 모드입니다.",
    };
  }
  if (usageRate >= 0.1) {
    return {
      level: "steady",
      message: "추정치가 한도의 10-30% 구간입니다. 현실과 타협한 사용량, 아직 회의록은 온건합니다.",
    };
  }
  return {
    level: "quiet",
    message: "한도의 10% 아래입니다. 이상적인 사용량이지만, 인생이 늘 이상적이면 가계부가 이렇게 재밌진 않았겠지요.",
  };
}

// 결제일과 정규 유동성 대비 미결제액을 바탕으로 카드 결제 심사평을 만든다.
export function paymentPressureTone(
  remainingAmount: number,
  daysUntilDue: number,
  regularLiquidity: number,
): PaymentPressureTone {
  if (remainingAmount <= 0) {
    return {
      level: "quiet",
      message: "이번 달 카드 채무는 정리되었습니다. 예산위원회가 드물게 박수를 칩니다.",
    };
  }
  const liquidityRate = regularLiquidity > 0 ? remainingAmount / regularLiquidity : 1;
  if (daysUntilDue < 0) {
    return {
      level: "danger",
      message: "결제일이 지났는데 미결제 기록이 남았습니다. 파산자는 아니겠지만 장부는 그렇게 증언 중입니다.",
    };
  }
  if (daysUntilDue <= 2 || liquidityRate >= 1.5) {
    return {
      level: "danger",
      message: "결제일과 미결제액이 함께 압박 중입니다. 파산 심사위원회가 서류철을 펼쳤습니다.",
    };
  }
  if (daysUntilDue <= 5 || liquidityRate >= 1) {
    return {
      level: "warning",
      message: "정규 유동성보다 미결제액의 목소리가 큽니다. 아직 파산자는 아니지만 해명이 필요합니다.",
    };
  }
  if (liquidityRate >= 0.5) {
    return {
      level: "steady",
      message: "결제액이 정규 유동성의 절반을 넘었습니다. 예산위원회가 안경을 고쳐 쓰는 중입니다.",
    };
  }
  return {
    level: "quiet",
    message: "미결제액은 아직 통제 가능한 범위입니다. 파산 심사위원회는 오늘 휴회합니다.",
  };
}
