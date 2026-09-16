"""Exact-once audit through real entry creation, month close and toll presentation."""

from datetime import date
import json
import sqlite3

import pytest

from app.config import get_settings
from app.db import init_db, session
from app.repositories.entries import create_entry
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn, LedgerEntryIn
from app.services.card_payments import (
    active_card_payment_unpaid_total,
    cancel_toll_deferral,
    create_card_payment_event,
    current_payment_status,
    defer_toll_payment,
    delete_card_payment_event,
)
from app.services.month import close_current_month
from app.services.summary import current_summary_values


TODAY = date(2026, 9, 1)


@pytest.fixture
def toll_batch(tmp_path, monkeypatch):
    monkeypatch.setenv("MONEY_NOTE_DB_PATH", str(tmp_path / "audit.sqlite3"))
    monkeypatch.setenv("MONEY_NOTE_TODAY", TODAY.isoformat())
    get_settings.cache_clear()
    try:
        init_db()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '0' WHERE key = 'scheduled_income'")
            conn.execute(
                "INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order) "
                "VALUES ('2026-08-31', 'synthetic opening cash', 1000000, 1)"
            )
        keys = {}
        for label, title, amount in (("A", "하이패스 A", 100000), ("B", "통행료 B", 20000)):
            entry = create_entry(LedgerEntryIn(
                book_section="current", entry_kind="expense", entry_date="2026-08-10",
                title=title, usage_place="통행료", usage_item=label,
                amount_value=amount, sort_order=0,
            ))
            keys[label] = entry["payment_key"]
        before = current_summary_values()
        assert (before["card_total"], before["remaining_liquidity"]) == (120000, 880000)
        assert close_current_month(target_month="2026-08")["archived"] == 2
        status = current_payment_status()
        assert len(status["rows"]) == 1
        assert status["rows"][0]["is_group"]
        assert status["rows"][0]["is_toll"]
        assert set(status["rows"][0]["payment_keys"]) == set(keys.values())
        yield keys
    finally:
        get_settings.cache_clear()


def observe(keys, deferred, paid=0):
    """Check financial totals and persisted item states after every operation."""
    expected_current = sum({"A": 100000, "B": 20000}[label] for label in deferred)
    expected_batch = 120000 - expected_current - paid
    summary = current_summary_values()
    batch = active_card_payment_unpaid_total()
    status = current_payment_status()
    assert summary["scheduled_income"] == 0
    assert summary["cash_flow_balance"] == 1000000 - paid
    assert summary["card_total"] == expected_current
    assert batch == expected_batch
    assert status["recorded_remaining_total"] == expected_batch
    assert summary["card_total"] + batch + paid == 120000
    assert summary["remaining_liquidity"] == 880000
    with session() as conn:
        entries = {row["payment_key"]: dict(row) for row in conn.execute(
            "SELECT payment_key, book_section, entry_date FROM ledger_entries"
        )}
        deferrals = {row[0] for row in conn.execute(
            "SELECT entry_payment_key FROM card_payment_deferrals"
        )}
    assert set(entries) == set(keys.values())
    assert deferrals == {keys[label] for label in deferred}
    for label, key in keys.items():
        assert entries[key]["book_section"] == ("current" if label in deferred else "archive")
        assert entries[key]["entry_date"] == (
            "2026-09-01" if label in deferred else "2026-08-10"
        )
    presented_keys = [key for row in status["rows"] for key in row["payment_keys"]]
    assert sorted(presented_keys) == sorted(keys.values())
    for row in status["rows"]:
        assert row["is_toll"]
        assert all((key in deferrals) == row["is_deferred"] for key in row["payment_keys"])
    return {
        "deferred": sorted(deferred), "cash": summary["cash_flow_balance"],
        "current": summary["card_total"], "batch": batch,
        "obligation": summary["card_total"] + batch, "paid": paid,
        "remaining_liquidity": summary["remaining_liquidity"],
    }


def pay_b(keys, amount=5000):
    return create_card_payment_event(CardPaymentEventIn(
        idempotency_key=f"toll-freeze-payment-b-{amount}",
        event_date=TODAY, event_type="immediate",
        allocations=[CardPaymentAllocationIn(
            entry_payment_key=keys["B"], amount_value=amount,
        )],
    ))


@pytest.mark.parametrize("operations", [
    (),
    ("defer_a",),
    ("defer_a", "defer_b"),
    ("defer_a", "retry_a"),
    ("defer_a", "cancel_a"),
    ("defer_a", "defer_b", "cancel_a"),
    ("pay_b", "defer_a", "reject_b"),
    ("defer_a", "interrupt_b"),
], ids=[
    "1-current-current", "2-deferred-current", "3-deferred-deferred",
    "4-same-retry", "5-partial-defer-cancel", "6-full-defer-partial-cancel",
    "7-partially-paid-sibling-rejected", "8-second-operation-db-failure",
])
def test_toll_mixed_state_matrix(toll_batch, operations, request):
    keys = toll_batch
    deferred = set()
    paid = 0
    observations = [observe(keys, deferred, paid)]
    for operation in operations:
        if operation in {"defer_a", "defer_b"}:
            label = operation[-1].upper()
            defer_toll_payment(keys[label])
            deferred.add(label)
        elif operation == "retry_a":
            with session() as conn:
                before = tuple(conn.execute("SELECT * FROM card_payment_deferrals").fetchone())
            defer_toll_payment(keys["A"])
            with session() as conn:
                after = tuple(conn.execute("SELECT * FROM card_payment_deferrals").fetchone())
            assert before == after
        elif operation == "cancel_a":
            assert cancel_toll_deferral(keys["A"])
            deferred.remove("A")
        elif operation == "pay_b":
            pay_b(keys)
            paid = 5000
        elif operation == "reject_b":
            with pytest.raises(ValueError, match="이미 일부결제"):
                defer_toll_payment(keys["B"])
        elif operation == "interrupt_b":
            # Fail after B's deferral INSERT, before its ledger UPDATE commits.
            with session() as conn:
                conn.execute(
                    "CREATE TRIGGER interrupt_second_defer BEFORE UPDATE ON ledger_entries "
                    "WHEN OLD.usage_item = 'B' BEGIN "
                    "SELECT RAISE(ABORT, 'injected second operation failure'); END"
                )
            with pytest.raises(sqlite3.IntegrityError, match="injected second operation"):
                defer_toll_payment(keys["B"])
        observations.append(observe(keys, deferred, paid))
    request.node.user_properties.append(("financial_states", json.dumps(observations)))


def test_toll_partial_cancel_database_failure_rolls_back(toll_batch):
    keys = toll_batch
    defer_toll_payment(keys["A"])
    observe(keys, {"A"})
    defer_toll_payment(keys["B"])
    observe(keys, {"A", "B"})
    with session() as conn:
        conn.execute(
            "CREATE TRIGGER interrupt_cancel BEFORE DELETE ON card_payment_deferrals "
            "BEGIN SELECT RAISE(ABORT, 'injected cancel failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="injected cancel failure"):
        cancel_toll_deferral(keys["A"])
    observe(keys, {"A", "B"})


@pytest.mark.parametrize("amount", [5000, 20000])
def test_toll_sibling_payment_and_cancellation_preserve_liquidity(toll_batch, amount):
    keys = toll_batch
    defer_toll_payment(keys["A"])
    observe(keys, {"A"})
    event = pay_b(keys, amount)
    observe(keys, {"A"}, amount)
    assert delete_card_payment_event(event["id"])
    observe(keys, {"A"})
