from __future__ import annotations

from datetime import date
import hashlib


MEDICAL_WORDS = (
    "병원",
    "치과",
    "의원",
    "약국",
    "약제",
    "진료",
    "검사",
    "수술",
    "정신과",
    "정신건강",
    "감기",
    "내과",
    "이비인후과",
)
PSYCHIATRY_WORDS = ("정신과", "정신건강", "상담")
COLD_WORDS = ("감기", "내과", "이비인후과")
TRANSPORT_WORDS = ("교통", "하이패스", "주유", "유류", "lpg", "가스")
SMALL_CLAIM_LIMIT = 2_000
ESSENTIAL_CLAIM_WORDS = (
    "병원",
    "치과",
    "의원",
    "약국",
    "약제",
    "감기",
    "정신과",
    "정형외과",
    "진료",
    "검사",
    "수술",
    "이자",
    "대출",
    "통신",
    "보험",
    "관리비",
    "교통",
    "lpg",
    "가스",
    "유류",
    "주유",
    "하이패스",
    "통행",
)
QUESTIONABLE_CLAIM_WORDS = ("커피", "카페", "빽다방", "편지지", "간식", "술", "담배", "게임", "취미", "굿즈")
DIGNITY_WORDS = ("세탁", "의류", "옷", "미용", "이발", "헤어", "면도", "칫솔", "치약", "샴푸", "비누", "화장품")
CATEGORY_LABELS = {
    "essential": "안 썼으면 큰일 났을 돈",
    "questionable": "꼭 써야 했을까...?",
    "dignity": "최소한의 품위유지비",
    "unclassified": "미분류",
}


def stable_choice(messages: tuple[str, ...], *signals: object) -> str:
    """같은 판단 근거에는 같은 문구를 돌려주는 결정적 선택기다."""
    key = "|".join(str(signal) for signal in signals)
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return messages[int.from_bytes(digest[:4], "big") % len(messages)]


def title_contains(row: dict, words: tuple[str, ...]) -> bool:
    title = str(row.get("title") or "").lower()
    return any(word in title for word in words)


def text_contains(value: str, words: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(word in lowered for word in words)


def category_label(category: str | None) -> str:
    """소비 분류 코드를 사용자가 읽을 라벨로 바꾼다."""
    return CATEGORY_LABELS.get(category or "unclassified", CATEGORY_LABELS["unclassified"])


def spending_stat_tones() -> list[dict]:
    """소비 통계 카드 제목과 설명을 백엔드 기준으로 제공한다."""
    return [
        {
            "key": "essential",
            "title": category_label("essential"),
            "caption": "안 썼으면 일이 커졌을 돈. 생존 인프라입니다.",
        },
        {
            "key": "questionable",
            "title": category_label("questionable"),
            "caption": "과거의 내가 예산위원회에 출석해야 합니다.",
        },
        {
            "key": "dignity",
            "title": category_label("dignity"),
            "caption": "사람 꼴을 유지하기 위한 최소한의 사회적 비용입니다.",
        },
        {
            "key": None,
            "title": category_label(None),
            "caption": "아직 판결을 기다리는 소비들입니다.",
        },
    ]


def classify_claim_category(row: dict) -> str | None:
    """청구 항목은 사용자가 조작하지 않으므로 제목과 금액으로 자동 분류한다."""
    title = str(row.get("title") or "")
    amount = float(row.get("amount_value") or 0)
    if 0 < amount <= SMALL_CLAIM_LIMIT:
        return "questionable"
    if text_contains(title, ESSENTIAL_CLAIM_WORDS):
        return "essential"
    if text_contains(title, DIGNITY_WORDS):
        return "dignity"
    if text_contains(title, QUESTIONABLE_CLAIM_WORDS):
        return "questionable"
    return None


def app_judgment(
    entries: list[dict],
    panels: list[dict],
    cash_flows: list[dict],
    summary: dict,
    payment_status: dict,
    settings: dict[str, str],
) -> dict:
    """본체 웹앱에서 쓰는 모든 판단 문구를 한 번에 만든다."""
    expense_entries = [entry for entry in entries if entry.get("entry_kind") != "planned"]
    claim_rows = [panel for panel in panels if panel.get("panel_type") == "claim"]
    settlement_rows = [panel for panel in panels if panel.get("panel_type") == "settlement"]
    frozen_rows = [panel for panel in panels if panel.get("panel_type") == "frozen"]
    settlement_limit = float(settings.get("settlement_card_limit") or 5_800_000)
    settlement_total = sum(float(row.get("amount_value") or 0) for row in settlement_rows)
    owner_card_total = sum(float(entry.get("amount_value") or 0) for entry in expense_entries)
    owner_card_total += float(summary.get("installment_monthly_total") or 0)
    days_until_due = days_between(date.today().isoformat(), str(payment_status.get("due_date") or date.today().isoformat()))
    reference_liquidity = float(payment_status.get("primary_income_total") or 0)
    if reference_liquidity <= 0:
        reference_liquidity = float(settings.get("base_next_month_liquidity") or 400_000)

    return {
        "category_labels": CATEGORY_LABELS,
        "stat_tones": spending_stat_tones(),
        "claim_categories": {str(row["id"]): classify_claim_category(row) for row in claim_rows},
        "budget": budget_committee_tone(
            {
                "expense_total": sum(float(entry.get("amount_value") or 0) for entry in expense_entries),
                "expense_count": len(expense_entries),
                "cash_flow_total": sum(float(flow.get("amount_value") or 0) for flow in cash_flows),
                "cash_flow_count": len(cash_flows),
                "claim_total": sum(panel_net_amount(row) for row in claim_rows),
                "claim_count": len(claim_rows),
                "settlement_total": settlement_total,
                "settlement_count": len(settlement_rows),
                "frozen_total": sum(float(row.get("amount_value") or 0) for row in frozen_rows),
                "frozen_count": len(frozen_rows),
            }
        ),
        "credit": credit_usage_tone((owner_card_total + settlement_total) / settlement_limit if settlement_limit > 0 else 0),
        "payment": payment_pressure_tone(
            float(payment_status.get("recorded_remaining_total") or 0),
            days_until_due,
            reference_liquidity,
        ),
    }


def panel_net_amount(row: dict) -> float:
    return max(0, float(row.get("amount_value") or 0) - float(row.get("discount_amount") or 0))


def budget_committee_tone(input_data: dict) -> dict[str, str]:
    """장부 전체 변화에 반응하는 예산심사위원회 한 줄 평을 만든다."""
    activity_count = (
        input_data["expense_count"]
        + input_data["cash_flow_count"]
        + input_data["claim_count"]
        + input_data["settlement_count"]
        + input_data["frozen_count"]
    )

    def say(messages: tuple[str, ...]) -> str:
        return messages[activity_count % len(messages)]

    if activity_count == 0:
        return {
            "level": "quiet",
            "message": say(
                (
                    "아직 기록이 없습니다. 예산심사위원회가 의사봉만 닦고 있습니다.",
                    "장부가 고요합니다. 평화인지 기록 누락인지는 위원회도 아직 판단을 유보합니다.",
                    "이번 달 첫 안건을 기다리는 중입니다. 무소비라면 위업이고 미기록이라면 곧 들통납니다.",
                )
            ),
        }
    if input_data["cash_flow_total"] < 0 and abs(input_data["cash_flow_total"]) > input_data["expense_total"]:
        return {
            "level": "warning",
            "message": say(
                (
                    "카드보다 현금이 더 적극적으로 퇴장했습니다. 계좌가 별도 의견서를 제출했습니다.",
                    "장부의 주연은 카드가 아니라 현금 유출입니다. 예산위원회가 통장 쪽으로 고개를 돌립니다.",
                    "현금흐름이 소비 기록보다 큰 목소리를 냅니다. 보이지 않는 지출도 발언권은 있습니다.",
                )
            ),
        }
    if input_data["frozen_total"] > input_data["expense_total"] and input_data["frozen_count"] > 0:
        return {
            "level": "steady",
            "message": say(
                (
                    "쓴 돈보다 동결한 돈이 큽니다. 미래의 소비가 현재의 장부에서 대기번호를 받았습니다.",
                    "동결 자산이 당월 지출보다 당당합니다. 아직 사지 않았다는 사실이 이번 달의 절약입니다.",
                    "소비 후보군이 실제 소비보다 큽니다. 예산심사위원회가 결정을 미룬 용기를 높이 평가합니다.",
                )
            ),
        }
    if input_data["claim_total"] + input_data["settlement_total"] > input_data["expense_total"] and input_data["claim_count"] + input_data["settlement_count"] > 0:
        return {
            "level": "steady",
            "message": say(
                (
                    "본인 소비보다 가족회계의 존재감이 큽니다. 이번 달 장부는 개인전보다 단체전에 가깝습니다.",
                    "청구와 정산이 당월 지출보다 활발합니다. 가족이라는 제도가 회계상으로도 실재합니다.",
                    "가족 관련 숫자가 장부 전면에 나섰습니다. 신뢰는 유지되고 계산기는 바쁩니다.",
                )
            ),
        }
    if input_data["expense_count"] >= 30:
        return {
            "level": "warning",
            "message": say(
                (
                    "당월 지출 건수가 풍성합니다. 한 건 한 건은 생활이지만 합치면 행정입니다.",
                    "소비 기록이 30건을 넘었습니다. 삶이 성실하게 영수증을 생산하고 있습니다.",
                    "장부가 제법 두꺼워졌습니다. 예산심사위원회가 속독 능력을 요구받습니다.",
                )
            ),
        }
    if input_data["cash_flow_total"] > input_data["expense_total"] and input_data["cash_flow_total"] > 0:
        return {
            "level": "quiet",
            "message": say(
                (
                    "현금 유입이 당월 지출보다 큽니다. 예산심사위원회가 이례적으로 칭찬을 결재합니다.",
                    "들어온 돈이 쓴 돈보다 우세합니다. 장부가 사용자에게 유리한 증언을 남깁니다.",
                    "현재까지는 유입 우세입니다. 재정적 품위가 일시적으로 확인되었습니다.",
                )
            ),
        }
    if input_data["expense_total"] >= 1_000_000:
        return {
            "level": "warning",
            "message": say(
                (
                    "당월 소비가 일곱 자리에 진입했습니다. 삶의 밀도가 카드 명세서에도 반영되었습니다.",
                    "지출 총액이 백만 원을 넘었습니다. 경제에는 기여했고 위원회에는 안건을 제공했습니다.",
                    "소비 활동이 매우 적극적입니다. 예산심사위원회가 설명자료의 글자 크기를 줄입니다.",
                )
            ),
        }
    return {
        "level": "quiet",
        "message": say(
            (
                "현재까지는 사람 사는 수준의 소란입니다. 예산심사위원회가 관찰 의견만 남깁니다.",
                "장부는 대체로 평온합니다. 소비는 있었고 재난으로 분류되지는 않았습니다.",
                "이번 달 재정은 설명 가능한 범위에서 움직이고 있습니다. 위원회는 일단 믿어보기로 합니다.",
                "기록이 쌓이고 있습니다. 숫자는 정직하며 아직 지나치게 공격적이지 않습니다.",
            )
        ),
    }


def credit_usage_tone(usage_rate: float) -> dict[str, str]:
    usage_percent = usage_rate * 100
    if usage_rate >= 0.8:
        return {
            "level": "danger",
            "message": stable_choice(
                (
                    "추정 한도의 80%를 넘었습니다. 카드 명의자는 이제 금융상품이 아니라 금융기반시설입니다.",
                    "한도 여백이 장식용으로 변했습니다. 신용평가라는 말이 서류가방을 들고 현관에 와 있습니다.",
                    "가족카드가 한도를 생활공간처럼 사용 중입니다. 명의자의 평정심은 별도 예산으로 편성해야겠습니다.",
                ),
                round(usage_percent),
            ),
        }
    if usage_rate >= 0.5:
        return {
            "level": "danger",
            "message": stable_choice(
                (
                    "추정치가 한도의 절반을 넘었습니다. 신용도라는 단어가 정장을 입고 회의실에 들어옵니다.",
                    "한도의 과반이 사용되었습니다. 가족의 소비가 민주적 절차 없이 다수당이 되었습니다.",
                    "50% 선을 넘었습니다. 카드 명의자의 침착함이 이번 달의 가장 큰 무이자 할부입니다.",
                ),
                round(usage_percent),
            ),
        }
    if usage_rate >= 0.3:
        return {
            "level": "warning",
            "message": stable_choice(
                (
                    "추정치가 한도의 30%를 넘었습니다. 아직 사고는 아니지만, 카드 명의자의 표정은 회계감사 모드입니다.",
                    "현실과 타협하던 구간을 이탈했습니다. 가족카드 사용내역에 해명자료가 붙기 시작합니다.",
                    "30% 초과입니다. 한도는 넉넉하지만 명의자의 마음에는 이미 임시제한이 걸렸습니다.",
                    "카드는 정상 작동 중입니다. 다만 명의자의 심박수가 부가서비스처럼 따라옵니다.",
                ),
                round(usage_percent),
            ),
        }
    if usage_rate >= 0.1:
        return {
            "level": "steady",
            "message": stable_choice(
                (
                    "한도 사용률은 온건합니다. 신뢰는 유지되고 정산표는 제 역할을 합니다.",
                    "가족 신용공동체가 무난하게 운영 중입니다. 명의자의 불안은 아직 취미 수준입니다.",
                    "이 정도면 신용은 일하고 불안은 휴가 중입니다.",
                ),
                round(usage_percent),
            ),
        }
    return {
        "level": "quiet",
        "message": stable_choice(
            (
                "가족카드가 거의 명예직으로 근무 중입니다. 명의자의 혈압도 정상 범위입니다.",
                "한도 사용률이 얌전합니다. 신용평가위원회가 안건 부족으로 조기 퇴근합니다.",
                "한도의 10% 아래입니다. 이상적인 사용량이지만 인생이 늘 이상적이면 가계부가 이렇게 재밌진 않았겠지요.",
            ),
            round(usage_percent),
        ),
    }


def payment_pressure_tone(remaining_amount: float, days_until_due: int, reference_liquidity: float) -> dict[str, str]:
    liquidity_rate = remaining_amount / reference_liquidity if reference_liquidity > 0 else (2 if remaining_amount > 0 else 0)
    signals = (round(remaining_amount), days_until_due, round(liquidity_rate * 100))
    if remaining_amount <= 0:
        return {
            "level": "quiet",
            "message": stable_choice(
                (
                    "이번 달 카드 채무는 정리되었습니다. 예산위원회가 드물게 박수를 칩니다.",
                    "남은 결제금액이 없습니다. 파산심사위원회가 할 일을 잃고 커피를 탑니다.",
                    "카드 결제는 정리되었습니다. 통장은 피곤하지만 명예롭게 퇴근합니다.",
                ),
                *signals,
            ),
        }
    if days_until_due < 0:
        return {
            "level": "danger",
            "message": stable_choice(
                (
                    "결제일이 지났는데 미결제 기록이 남아 있습니다. 실제 결제는 끝난 것으로 보고 유동성 현황을 보정해야 합니다.",
                    "14일이 지났습니다. 파산심사위원회가 자동으로 의제를 정리하고, 통장 보정을 요구합니다.",
                    "결제 가능 기간이 종료되었습니다. 장부와 실제 계좌 사이의 화해 절차가 필요합니다.",
                ),
                *signals,
            ),
        }
    if days_until_due == 0:
        return {
            "level": "danger",
            "message": stable_choice(
                (
                    "오늘이 결제 가능 마지막 날입니다. 파산심사위원회가 회의실 조명을 전부 켰습니다.",
                    "D-Day입니다. 남은 결제금액이 있다면 지금은 철학보다 송금입니다.",
                    "오늘 안에 정리해야 합니다. 장부가 농담을 줄이고 실무 모드로 전환합니다.",
                ),
                *signals,
            ),
        }
    if liquidity_rate >= 2 or (days_until_due <= 2 and liquidity_rate >= 1):
        return {
            "level": "danger",
            "message": stable_choice(
                (
                    "남은 결제금액이 기준 수입을 크게 압도합니다. 파산심사위원회가 비상 안건을 상정했습니다.",
                    "금액과 일정이 함께 압박 중입니다. 장부가 사용자에게 조용한 재정 비상벨을 울립니다.",
                    "결제일까지 여유와 금액 여유가 동시에 부족합니다. 위원회가 웃음을 잠시 접었습니다.",
                ),
                *signals,
            ),
        }
    if days_until_due <= 5 and liquidity_rate >= 0.75:
        return {
            "level": "warning",
            "message": stable_choice(
                (
                    "결제일이 가까운데 남은 금액도 제법 큽니다. 파산심사위원회가 출석 요구서를 준비합니다.",
                    "시간과 금액이 함께 회의 안건이 되었습니다. 아직 늦진 않았지만 여유롭지도 않습니다.",
                    "남은 며칠이 가볍지 않습니다. 통장은 설득보다 입금을 원합니다.",
                ),
                *signals,
            ),
        }
    if liquidity_rate >= 1:
        return {
            "level": "warning",
            "message": stable_choice(
                (
                    "남은 결제금액이 기준 수입 이상입니다. 카드사는 침착하고 사용자는 그렇지 않을 수 있습니다.",
                    "금액이 기준선을 넘었습니다. 파산심사위원회가 자료 요청을 시작합니다.",
                    "아직 날짜는 남았지만 금액이 만만치 않습니다. 장부가 숫자로 압박 면접을 봅니다.",
                ),
                *signals,
            ),
        }
    if days_until_due <= 5 or liquidity_rate >= 0.5:
        return {
            "level": "steady",
            "message": stable_choice(
                (
                    "관리 가능한 구간이지만 방심하면 위원회가 태도를 바꿉니다.",
                    "아직 통제권은 사용자에게 있습니다. 다만 결제일 달력은 자꾸 말을 겁니다.",
                    "남은 금액은 현실적입니다. 현실적이라는 말이 늘 편하다는 뜻은 아닙니다.",
                ),
                *signals,
            ),
        }
    return {
        "level": "quiet",
        "message": stable_choice(
            (
                "현재 결제 압박은 낮습니다. 파산심사위원회가 관찰 의견만 남깁니다.",
                "남은 결제금액이 기준 수입 안에서 조용합니다. 아직 회계상 품위가 유지됩니다.",
                "카드 결제는 관리 가능한 범위입니다. 위원회가 드물게 온건한 표정을 짓습니다.",
            ),
            *signals,
        ),
    }


def days_between(start_value: str, end_value: str) -> int:
    try:
        return (date.fromisoformat(end_value[:10]) - date.fromisoformat(start_value[:10])).days
    except ValueError:
        return 0


def shared_panel_subtitle(
    panel_type: str,
    rows: list[dict],
    total: float,
    current_card_total: float,
    card_limit: float,
) -> str:
    """공유 화면 상단에 보여줄 패널별 평가 문구를 고른다."""
    if panel_type == "claim":
        return claim_subtitle(rows, total)
    return settlement_subtitle(rows, total, current_card_total, card_limit)


def claim_subtitle(rows: list[dict], total: float) -> str:
    if not rows:
        return stable_choice(
            (
                "이달은 평온했습니다. 이런 달도 있어야 사람이 삽니다.",
                "청구할 일이 없었습니다. 가족회계가 드물게 무소식으로 안부를 전합니다.",
                "이번 달 청구서는 백지에 가깝습니다. 평화가 숫자로 증명되었습니다.",
            ),
            total,
        )

    row_count = len(rows)
    medical_count = sum(1 for row in rows if title_contains(row, MEDICAL_WORDS))
    psychiatry_count = sum(1 for row in rows if title_contains(row, PSYCHIATRY_WORDS))
    cold_count = sum(1 for row in rows if title_contains(row, COLD_WORDS))
    transport_count = sum(1 for row in rows if title_contains(row, TRANSPORT_WORDS))
    tiny_count = sum(1 for row in rows if 0 < float(row.get("amount_value") or 0) <= 2_000)
    largest = max(float(row.get("amount_value") or 0) for row in rows)
    signals = (
        row_count,
        round(total),
        medical_count,
        psychiatry_count,
        cold_count,
        transport_count,
        tiny_count,
        round(largest),
    )

    if medical_count >= 4:
        return stable_choice(
            (
                "이달은 평소보다 많이 아팠습니다. 몸도 지갑도 추가 진료를 받았습니다.",
                "평시 의료 유지비를 크게 넘어섰습니다. 건강보험과 가족의 걱정이 증원 근무 중입니다.",
                "영수증 수가 평소 진료 일정을 초과했습니다. 집에서 걱정할 만큼 회복이 필요한 달이었습니다.",
            ),
            *signals,
        )
    if medical_count == 3:
        return stable_choice(
            (
                "정기 진료 외에 한 번 아팠습니다. 몸이 평시 예산에 소규모 추경을 요청했습니다.",
                "평소 의료 일정에 추가 진료 한 번이 있었습니다. 걱정할 정도는 아니지만 분명 아팠던 달입니다.",
                "의료 청구가 세 건입니다. 정기 유지보수 외에 몸이 한 차례 의견을 냈습니다.",
            ),
            *signals,
        )
    if psychiatry_count >= 2 and medical_count <= 2:
        return stable_choice(
            (
                "정기적인 마음 유지보수와 생활 진료가 있었습니다. 대체로 평시 운용 범위입니다.",
                "마음의 정기점검이 예정대로 진행되었습니다. 평시에도 사람은 유지보수가 필요합니다.",
                "평소의 의료 일정이 청구서에 반영되었습니다. 건강 관리가 사건이 아니라 운영으로 처리됩니다.",
            ),
            *signals,
        )
    if any("치과" in str(row.get("title") or "") for row in rows):
        return stable_choice(
            (
                "이달은 치아가 자본주의와 정면 충돌했습니다.",
                "치과 영수증이 포함되었습니다. 작은 뼈 몇 개가 재정에 상당한 발언권을 행사합니다.",
                "치아 관리비가 청구서에 출석했습니다. 웃음의 유지비는 생각보다 구체적입니다.",
            ),
            *signals,
        )
    if tiny_count >= 3:
        return stable_choice(
            (
                "소액 청구가 정성스럽게 모였습니다. 원칙은 훌륭하고 합계는 다소 민망합니다.",
                "작은 금액도 빠짐없이 청구되었습니다. 가족회계의 투명성이 현미경 수준입니다.",
                "천 원 단위 영수증들이 연대하여 청구서를 구성했습니다. 회계 원칙에는 예외가 없습니다.",
            ),
            *signals,
        )
    if transport_count >= max(2, row_count / 2):
        return stable_choice(
            (
                "이번 달은 가족의 명령과 도로 사정이 청구서를 작성했습니다.",
                "이동 관련 비용이 주류입니다. 가족 행사는 끝났고 하이패스 기록은 남았습니다.",
                "교통비가 가족 기여도를 숫자로 번역했습니다. 차량은 말이 없고 영수증은 정확합니다.",
            ),
            *signals,
        )
    if total >= 300_000 or largest >= 200_000:
        return stable_choice(
            (
                "청구 규모가 제법 큽니다. 가족회계가 이번 달에는 정식 안건으로 상정되었습니다.",
                "한 줄 또는 여러 줄이 합계에 상당한 존재감을 보입니다. 사유는 영수증이 증언합니다.",
                "이번 청구서는 가볍게 넘길 두께가 아닙니다. 다행히 숫자는 모두 공개되어 있습니다.",
            ),
            *signals,
        )
    if row_count >= 8:
        return stable_choice(
            (
                "생활은 계속되었고 영수증은 성실하게 출석했습니다.",
                "청구 건수가 풍성합니다. 가족을 위한 활동이 회계상으로도 매우 활발했습니다.",
                "한 달의 자잘한 수고가 여러 줄의 청구서로 번역되었습니다.",
            ),
            *signals,
        )
    return stable_choice(
        (
            "생활은 계속되고, 영수증은 조용히 증언합니다.",
            "가족 관련 지출을 정리했습니다. 숫자는 담담하고 사유는 대체로 타당합니다.",
            "이번 달 가족회계 보고입니다. 감정은 생략했고 영수증은 첨부했습니다.",
            "청구할 것은 청구했습니다. 가족 간 평화는 정확한 합계에서 시작됩니다.",
        ),
        *signals,
    )


def settlement_subtitle(rows: list[dict], total: float, current_card_total: float, card_limit: float) -> str:
    if not rows:
        return stable_choice(
            (
                "이번 달 정산은 고요합니다. 평화가 숫자로 증명되었습니다.",
                "가족카드 사용내역이 없습니다. 카드 명의자가 이유 없이 안도합니다.",
                "정산할 금액이 없습니다. 형제자매 간 신용공동체가 휴회 중입니다.",
            ),
            round(current_card_total),
            round(card_limit),
        )

    usage_rate = (current_card_total + total) / card_limit if card_limit > 0 else 0
    row_count = len(rows)
    largest = max(float(row.get("amount_value") or 0) for row in rows)
    largest_share = largest / total if total > 0 else 0
    signals = (row_count, round(total), round(current_card_total), round(usage_rate * 1000), round(largest_share * 100))

    if usage_rate >= 0.8:
        return stable_choice(
            (
                "가족카드가 한도를 주거공간처럼 사용 중입니다. 카드 명의자는 금융기반시설이 되었습니다.",
                "추정 합산 사용액이 한도의 80%를 넘었습니다. 평화로운 정산보다 긴급 브리핑에 가깝습니다.",
                "한도 여백이 희귀자원이 되었습니다. 다 갚는다는 신뢰와 별개로 명의자의 심장은 실시간입니다.",
            ),
            *signals,
        )
    if usage_rate >= 0.5:
        return stable_choice(
            (
                "가족카드가 신용평가의 문 앞에서 정장을 고쳐 입고 있습니다.",
                "추정 합산 사용액이 한도의 절반을 넘었습니다. 가족의 신뢰는 깊고 명의자의 한숨도 깊습니다.",
                "한도 과반이 사용되었습니다. 모두 갚을 것을 알지만 숫자는 먼저 사람을 놀라게 합니다.",
            ),
            *signals,
        )
    if usage_rate >= 0.3:
        return stable_choice(
            (
                "추정 합산 사용액이 한도의 30%를 넘었습니다. 카드 명의자의 심박수가 회계자료가 됩니다.",
                "현실적 타협 구간을 조금 벗어났습니다. 명의자는 정산 능력을 믿으며 동시에 불안해합니다.",
                "30% 선을 넘었습니다. 한도초과와는 멀지만 마음의 한도에는 근접했습니다.",
            ),
            *signals,
        )
    if largest_share >= 0.7 and total >= 100_000:
        return stable_choice(
            (
                "이번 정산은 사실상 한 건의 대형 안건과 그 부속자료입니다.",
                "한 항목이 정산액 대부분을 차지합니다. 소비라기보다 사건에 가까운 구성입니다.",
                "정산 내역의 권력이 한 건에 집중되어 있습니다. 사유가 타당하길 명의자가 조용히 바랍니다.",
            ),
            *signals,
        )
    if usage_rate >= 0.1:
        return stable_choice(
            (
                "현실과 타협한 가족카드 사용 구간입니다. 할부 변수는 카드사만이 끝까지 알고 있습니다.",
                "합산 사용률은 온건합니다. 신뢰는 유지되고 정산표는 제 역할을 합니다.",
                "가족 신용공동체가 무난하게 운영 중입니다. 명의자의 불안은 아직 취미 수준입니다.",
            ),
            *signals,
        )
    return stable_choice(
        (
            "형제자매 간 평화를 위한 숫자 보고서입니다.",
            "사용률이 얌전합니다. 가족카드도 이번 달에는 예의가 있었습니다.",
            "정산 규모가 평온합니다. 명의자의 신용도와 심박수 모두 무사합니다.",
        ),
        *signals,
    )


def claim_ledger_note(month: str, entries: list[dict], cash_flows: list[dict]) -> str:
    """어머니 청구서 하단에 붙일 전월~당월 가계부 한 줄 평가를 만든다."""
    start, end = previous_to_current_range(month)
    ranged_entries = [
        row
        for row in entries
        if row.get("entry_kind") != "planned" and in_date_range(str(row.get("entry_date") or ""), start, end)
    ]
    ranged_cash_flows = [
        row
        for row in cash_flows
        if in_date_range(str(row.get("occurred_on") or ""), start, end)
    ]
    card_total = sum(row.get("amount_value") or 0 for row in ranged_entries)
    cash_total = sum(row.get("amount_value") or 0 for row in ranged_cash_flows)
    questionable = sum(1 for row in ranged_entries if row.get("spending_category") == "questionable")
    verdict = ledger_verdict(card_total, cash_total, questionable)
    return (
        "가계부를 얼핏 보니, 전월부터 당월까지 "
        f"카드 기록은 {format_won(card_total)}, 현금흐름은 {format_won(cash_total)}입니다. {verdict}"
    )


def ledger_verdict(card_total: float, cash_total: float, questionable_count: int) -> str:
    """카드/현금/성찰 항목 수를 바탕으로 짧은 평가 문장을 고른다."""
    signals = (round(card_total), round(cash_total), questionable_count)
    if questionable_count >= 8:
        return stable_choice(
            (
                "예산위원회가 정기회의를 임시 국정조사로 전환했습니다.",
                "성찰 대상 소비가 풍성합니다. 과거의 본인이 답변서를 준비해야 합니다.",
                "꼭 필요했는지 묻는 항목이 너무 많아 질문 자체가 정규 업무가 되었습니다.",
            ),
            *signals,
        )
    if questionable_count >= 3:
        return stable_choice(
            (
                "예산위원회 출석 안건이 몇 건 보입니다.",
                "일부 소비는 당시의 본인만이 설명할 수 있습니다.",
                "장부에 작은 의문표가 여러 개 붙었습니다. 범죄는 아니고 생활입니다.",
                "반드시 필요하지는 않았으나 이미 충분히 인간적이었던 소비가 관측됩니다.",
            ),
            *signals,
        )
    if card_total >= 1_000_000:
        return stable_choice(
            (
                "생활이 매우 적극적으로 전개되었습니다. 카드사가 그 활약을 상세히 기억합니다.",
                "카드 기록이 일곱 자리에 진입했습니다. 삶의 밀도가 금액으로도 확인됩니다.",
                "소비 활동이 왕성했습니다. 경제지표에는 기여했고 개인 장부에는 설명이 필요합니다.",
            ),
            *signals,
        )
    if card_total >= 500_000:
        return stable_choice(
            (
                "생활이 비교적 적극적으로 전개되었습니다.",
                "카드 사용이 제법 활발했습니다. 삶이 조용하지 않았다는 증거입니다.",
                "지출은 있었으나 대체로 사람 사는 범위입니다. 위원회는 관찰 의견만 남깁니다.",
            ),
            *signals,
        )
    if cash_total <= -300_000:
        return stable_choice(
            (
                "현금이 상당히 빠져나갔습니다. 계좌가 이 기간을 개인적으로 기억할 것입니다.",
                "현금흐름이 명확한 출구 방향을 보였습니다. 장부는 침착하게 비상구를 가리킵니다.",
                "카드보다 현금이 더 많은 이야기를 남겼습니다. 통장은 이미 전문을 읽었습니다.",
            ),
            *signals,
        )
    if cash_total < 0:
        return stable_choice(
            (
                "현금은 조용히 빠져나갔고, 장부는 그 사실을 알고 있습니다.",
                "현금흐름은 소폭 마이너스입니다. 큰일은 아니지만 기록은 정직합니다.",
                "계좌에서 작은 썰물이 관측되었습니다. 아직 해안선은 안전합니다.",
            ),
            *signals,
        )
    if cash_total > card_total and cash_total > 0:
        return stable_choice(
            (
                "현금 유입이 카드 기록보다 큽니다. 가계부가 드물게 희망적인 자료를 제출했습니다.",
                "들어온 현금이 소비보다 우세합니다. 예산위원회가 칭찬 문구를 찾느라 잠시 당황했습니다.",
                "현금흐름이 순조롭습니다. 장부가 사용자 편에서 증언하는 보기 드문 기간입니다.",
            ),
            *signals,
        )
    return stable_choice(
        (
            "전반적으로 사람 사는 수준의 소란입니다.",
            "가계부상 특기할 재난은 없습니다. 평범함이 훌륭한 실적입니다.",
            "소비와 현금흐름 모두 대체로 설명 가능한 범위입니다.",
            "장부를 얼핏 본 결과, 이번 기간도 무사히 인간으로 살았습니다.",
        ),
        *signals,
    )


def format_won(value: float) -> str:
    return f"{round(value):,}원"


def previous_to_current_range(month: str) -> tuple[date, date]:
    year, month_number = (int(part) for part in month.split("-", 1))
    start_year = year if month_number > 1 else year - 1
    start_month = month_number - 1 if month_number > 1 else 12
    end_month = month_number + 1
    end_year = year
    if end_month == 13:
        end_month = 1
        end_year += 1
    return date(start_year, start_month, 1), date(end_year, end_month, 1)


def in_date_range(value: str, start: date, exclusive_end: date) -> bool:
    if not value:
        return False
    try:
        parsed = date.fromisoformat(value[:10])
    except ValueError:
        return False
    return start <= parsed < exclusive_end
