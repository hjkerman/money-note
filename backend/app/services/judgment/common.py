from __future__ import annotations

from datetime import date
import hashlib
from importlib import resources
import random
from typing import Any

import yaml


_MESSAGE_RANDOM = random.Random()
_MESSAGE_CACHE: dict[str, dict[str, Any]] = {}


def _load_domain_messages(domain: str) -> dict[str, Any]:
    cached = _MESSAGE_CACHE.get(domain)
    if cached is not None:
        return cached
    path = resources.files(__package__).joinpath("messages", f"{domain}.yaml")
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"judgment message file must be a mapping: {domain}")
    _MESSAGE_CACHE[domain] = loaded
    return loaded


def get_messages(domain: str, key: str) -> tuple[str, ...]:
    current: Any = _load_domain_messages(domain)
    for part in key.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(f"unknown judgment message key: {domain}.{key}")
        current = current[part]
    if not isinstance(current, list) or not all(isinstance(item, str) for item in current):
        raise ValueError(f"judgment message key must point to a string list: {domain}.{key}")
    return tuple(current)


def choose_seeded_message(messages: tuple[str, ...], *signals: object, seed: object) -> str:
    """테스트와 고정 검증용 seed 기반 선택기다."""
    key = "|".join([str(seed), *(str(signal) for signal in signals)])
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return messages[int.from_bytes(digest[:4], "big") % len(messages)]


def choose_message(messages: tuple[str, ...], *signals: object, seed: object | None = None) -> str:
    """운영에서는 요청마다 바뀌고, 테스트에서는 seed로 고정 가능한 문구 선택기다."""
    if not messages:
        raise ValueError("judgment message pool is empty")
    if seed is not None:
        return choose_seeded_message(messages, *signals, seed=seed)
    return messages[_MESSAGE_RANDOM.randrange(len(messages))]


def judgment_message(domain: str, key: str, *signals: object, seed: object | None = None) -> str:
    return choose_message(get_messages(domain, key), *signals, seed=seed)


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


def safe_float(value: object, default: float = 0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value or default)
    except (TypeError, ValueError):
        return default


def ratio(numerator: float, denominator: float, default: float = 0) -> float:
    return numerator / denominator if denominator else default


def days_between(start_value: str, end_value: str) -> int:
    try:
        return (date.fromisoformat(end_value[:10]) - date.fromisoformat(start_value[:10])).days
    except ValueError:
        return 0


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
