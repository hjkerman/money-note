from __future__ import annotations

from datetime import date


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
        return "이달은 평온했습니다. 이런 달도 있어야 사람이 삽니다."
    if total >= 200_000:
        return "이달은 아팠습니다. 몸도 지갑도 같이 진료를 받았습니다."
    if any("치과" in str(row.get("title") or "") for row in rows):
        return "이달은 치아가 자본주의와 정면 충돌했습니다."
    return "생활은 계속되고, 영수증은 조용히 증언합니다."


def settlement_subtitle(rows: list[dict], total: float, current_card_total: float, card_limit: float) -> str:
    if not rows:
        return "이번 달 정산은 고요합니다. 평화가 숫자로 증명되었습니다."
    usage_rate = (current_card_total + total) / card_limit if card_limit > 0 else 0
    if usage_rate > 0.5:
        return "가족카드가 신용평가의 문 앞에서 정장을 고쳐 입고 있습니다."
    if usage_rate > 0.3:
        return "추정 합산 사용액이 한도의 30%를 넘었습니다. 카드 명의자의 심박수가 회계자료가 됩니다."
    if usage_rate >= 0.1:
        return "현실과 타협한 가족카드 사용 구간입니다. 할부 변수는 카드사만이 끝까지 알고 있습니다."
    return "형제자매 간 평화를 위한 숫자 보고서입니다."


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
    if questionable_count >= 3:
        return "예산위원회 출석 안건이 몇 건 보입니다."
    if card_total >= 500_000:
        return "생활이 비교적 적극적으로 전개되었습니다."
    if cash_total < 0:
        return "현금은 조용히 빠져나갔고, 장부는 그 사실을 알고 있습니다."
    return "전반적으로 사람 사는 수준의 소란입니다."


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
