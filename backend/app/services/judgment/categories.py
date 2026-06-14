from __future__ import annotations


CATEGORY_LABELS = {
    "essential": "안 썼으면 큰일 났을 돈",
    "questionable": "꼭 써야 했을까...?",
    "dignity": "최소한의 품위유지비",
    "unclassified": "미분류",
}


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
