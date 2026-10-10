"""Bounded inputs versus legacy full-state financial oracles, synthetic only."""

from datetime import date
from unittest.mock import patch

import pytest

from app.repositories.cash_flows import create_cash_flow
from app.repositories.entries import append_planned_entry, confirm_planned_entry, delete_entry, list_confirmed_planned_entries
from app.schemas import CashFlowIn, PlannedEntryIn, CardPaymentEventIn
from app.services.card_payments import create_card_payment_event
from app.services.financial_relationships import validate_runtime_card_payment_ownership, validate_runtime_recurring_ownership
from app.services.summary import cash_flow_total
from isolated_sync.canonical import CanonicalError
from isolated_sync.inputs import BoundedInputs, input_index, input_key
from isolated_sync.patricia import Fact, Index
from tests.d2b_financial_reference import projections
from tests.test_isolated_sync_finalization import sandbox as make_sandbox, verify
from tests.test_isolated_sync_capture import ROWS, insert


@pytest.fixture
def sandbox():
    yield from make_sandbox.__wrapped__()


def test_all_twelve_projections_and_read_only_scope(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        assert projections(writer) == projections(conn)
        create_cash_flow(CashFlowIn(occurred_on="2026-10-04", title="signed", amount_value=123, sort_order=2), conn=writer)
        assert projections(writer) == projections(conn)
        conn.finalize()
        conn.commit()
        verify(conn)
        with pytest.raises(CanonicalError, match="CONTEXT"):
            writer.cash_total("2026-10-05")


def test_overlay_wide_money_history_delete_move_and_savepoint(sandbox):
    from app.money import MAX_MONEY
    with sandbox.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        for n, amount in enumerate((MAX_MONEY, MAX_MONEY, -MAX_MONEY, -MAX_MONEY)):
            insert(writer, "cash_flows", dict(id=500+n, occurred_on="2026-08-01", title="wide", amount_value=amount, sort_order=n))
        conn.execute("SAVEPOINT change_dates")
        conn.execute("UPDATE cash_flows SET occurred_on='2026-12-01' WHERE id=500")
        for day in ("2026-01-01", "2026-09-30", "2026-10-05", "9999-12-31"):
            assert cash_flow_total(writer, today=date.fromisoformat(day)) == cash_flow_total(conn, today=date.fromisoformat(day))
        conn.execute("ROLLBACK TO change_dates")
        conn.execute("RELEASE change_dates")
        conn.execute("DELETE FROM cash_flows WHERE id=503")
        conn.execute("UPDATE cash_flows SET amount_value=? WHERE id=501", (-MAX_MONEY,))
        assert writer.cash_total("9999-12-31") == cash_flow_total(conn, today=date.max)
        conn.finalize()
        conn.commit()
        verify(conn)


def test_month_counts_horizon_transaction_overlay(sandbox):
    from app.repositories.entries import list_recent_closed_month_expense_counts
    from app.services.snapshot import _snapshot_policy_horizon
    from isolated_sync.facts import read_state
    with sandbox.connect() as conn:
        conn.begin_capture()
        for n, month in enumerate(("2026-01", "2026-02", "2026-03", "2026-04", "2026-12")):
            insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 500+n, "book_section": "archive", "entry_date": month+"-01", "payment_key": str(n)})
        conn.finalize()
        conn.commit()
        conn.begin_capture()
        writer = BoundedInputs(conn)
        conn.execute("DELETE FROM ledger_entries WHERE id IN (503,504)")
        conn.execute("UPDATE ledger_entries SET entry_date='2027-01-01' WHERE id=500")
        for limit in (1, 3, 10):
            assert list_recent_closed_month_expense_counts(limit, conn=writer) == list_recent_closed_month_expense_counts(limit, conn=conn)
        assert writer.policy_horizon("2026-10") == _snapshot_policy_horizon(read_state(conn), date(2026, 10, 5))
        conn.finalize()
        conn.commit()
        verify(conn)


@pytest.mark.parametrize("defect", ["cash", "count", "horizon", "missing_proof"])
def test_stale_maintained_input_fails_closed_and_rolls_back(sandbox, defect):
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        with conn._metadata():
            if defect == "cash":
                conn.execute("UPDATE sync_cash_prefix SET total='999'")
            elif defect == "missing_proof":
                # A reference cannot be absent or incompatible at view creation.
                conn.execute("UPDATE sync_commits SET input_hash=raw_hash")
            else:
                domain = "closed_count" if defect == "count" else "policy_horizon"
                conn.execute("INSERT OR REPLACE INTO sync_totals VALUES (?, '2026-10', '999')", (domain,))
        with pytest.raises(CanonicalError):
            writer = BoundedInputs(conn)
            if defect == "cash":
                writer.cash_total("2026-10-05")
            elif defect == "count":
                writer.closed_counts(3)
            else:
                writer.policy_horizon("2026-10")
        conn.rollback()
    with sandbox.connect() as conn:
        assert verify(conn) == before


@pytest.mark.parametrize("kind", ["event_total", "missing_key", "recurring_duplicate", "source_deleted"])
def test_affected_invalid_relationship_same_legacy_rejection(sandbox, kind):
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        writer = BoundedInputs(conn)
        validator = validate_runtime_card_payment_ownership
        if kind == "event_total":
            conn.execute("UPDATE card_payment_events SET total_amount=99 WHERE id=100")
        elif kind == "missing_key":
            conn.execute("UPDATE card_payment_allocations SET entry_payment_key='absent' WHERE id=100")
        else:
            source = append_planned_entry(PlannedEntryIn(title="service", usage_place="service", amount_value=500, due_day=5), conn=writer)
            with patch("app.repositories.entries.new_payment_key", return_value="recurring-one"):
                result = confirm_planned_entry(source["id"], today=date(2026, 10, 5), conn=writer)
            if kind == "recurring_duplicate":
                row = dict(conn.execute("SELECT * FROM ledger_entries WHERE id=?", (result["entry"]["id"],)).fetchone())
                insert(conn, "ledger_entries", {**row, "id": 900, "payment_key": "another-key"})
            else:
                conn.execute("DELETE FROM ledger_entries WHERE id=?", (source["id"],))  # real SET NULL
            validator = validate_runtime_recurring_ownership
        with pytest.raises(ValueError) as legacy:
            validator(conn)
        with pytest.raises(ValueError) as bounded:
            validator(writer)
        assert type(legacy.value) is type(bounded.value)
        assert str(legacy.value) == str(bounded.value)
        with pytest.raises(ValueError):
            conn.finalize()
    with sandbox.connect() as conn:
        assert verify(conn) == before


@pytest.mark.parametrize("kind", ["overpayment", "missing_entry", "changed_retry", "duplicate_key", "paid_delete", "recurring_twice"])
def test_command_error_and_idempotency_parity(sandbox, kind):
    with sandbox.connect() as conn:
        before = verify(conn)
        messages = []
        for bounded in (False, True):
            conn.begin_capture()
            writer = BoundedInputs(conn) if bounded else conn
            conn.execute("DELETE FROM card_payment_deferrals")
            request = dict(event_date="2026-10-05", event_type="immediate", idempotency_key="synthetic-retry-id-0001", allocations=[dict(entry_payment_key="card-100", amount_value=10)])
            if kind == "overpayment":
                request["allocations"][0]["amount_value"] = 10000
            elif kind == "missing_entry":
                request["allocations"][0]["entry_payment_key"] = "missing"
            elif kind == "duplicate_key":
                request["allocations"] *= 2
            try:
                if kind == "paid_delete":
                    delete_entry(100, conn=writer)
                elif kind == "recurring_twice":
                    source = append_planned_entry(PlannedEntryIn(title="recurring", usage_place="service", amount_value=0, due_day=5), conn=writer)
                    confirm_planned_entry(source["id"], today=date(2026, 10, 5), conn=writer)
                    confirm_planned_entry(source["id"], today=date(2026, 10, 5), conn=writer)
                else:
                    first = create_card_payment_event(CardPaymentEventIn(**request), today=date(2026, 10, 5), conn=writer)
                    assert first == create_card_payment_event(CardPaymentEventIn(**request), today=date(2026, 10, 5), conn=writer)
                    request["allocations"][0]["amount_value"] = 11
                    create_card_payment_event(CardPaymentEventIn(**request), today=date(2026, 10, 5), conn=writer)
            except ValueError as error:
                assert type(error) is ValueError  # not schema-construction failure
                messages.append((type(error), str(error)))
            else:
                pytest.fail("expected legacy/adapter rejection")
            conn.rollback()
        assert messages[0] == messages[1]
    with sandbox.connect() as conn:
        assert verify(conn) == before


def test_cross_month_confirmed_archive_null_date_and_policy_parity(sandbox):
    from app.services.card_charge.profiles import set_transit_discount_profile
    with sandbox.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        source = append_planned_entry(PlannedEntryIn(title="교통", usage_place="service", amount_value=1234, due_day=5), conn=writer)
        result = confirm_planned_entry(source["id"], today=date(2026, 10, 5), conn=writer)
        conn.execute("UPDATE ledger_entries SET book_section='archive',entry_date=NULL,amount_value=7000 WHERE id=?", (result["entry"]["id"],))
        set_transit_discount_profile("2026-10", "owner", conn=writer)
        for day in (date(2026, 10, 5), date(2026, 10, 31), date(2026, 11, 1)):
            assert projections(writer, day) == projections(conn, day)
        assert list_confirmed_planned_entries(date(2026, 10, 5), conn=writer)[0]["entry_date"] is None
        conn.finalize()
        conn.commit()
        verify(conn)


def test_complete_local_input_proof_full_rebuild(sandbox):
    from isolated_sync.finalization import generation
    with sandbox.connect() as conn:
        current, ctx, store, _, _ = generation(conn)
        facts = [Fact.make(input_key("cash_prefix", r[0]), r[1]) for r in conn.execute("SELECT ordinal,total FROM sync_cash_prefix")]
        facts.extend(Fact.make(input_key(r[0], r[1]), r[2]) for r in conn.execute("SELECT domain,key,total FROM sync_totals"))
        assert Index.build(ctx, facts).object() == input_index(conn, store, current["tx_id"]).object()


def test_recurring_confirmation_does_not_enumerate_closed_occurrences(sandbox):
    # Many past occurrences of ONE template, not merely unrelated archive rows.
    with sandbox.connect() as conn:
        conn.begin_capture()
        insert(conn, "app_settings", dict(key="last_closed_month", value="2026-09"))
        source = append_planned_entry(PlannedEntryIn(title="service", usage_place="service", amount_value=500, due_day=5), conn=conn)
        for n in range(300):
            insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 500+n,
                   "book_section": "archive", "source_planned_entry_id": source["id"],
                   "confirmed_month": "2026-01", "confirmed_at": f"2026-01-01T00:00:00.{n:06d}",
                   "entry_date": "2026-01-01", "payment_key": "old-occurrence-"+str(n)})
        conn.finalize()
        conn.commit()
        conn.begin_capture()
        writer = BoundedInputs(conn)
        queries = []
        execute = conn.execute
        def observed(sql, parameters=()):
            queries.append((sql, parameters))
            return execute(sql, parameters)
        conn.execute = observed
        confirm_planned_entry(source["id"], today=date(2026, 10, 5), conn=writer)
        actual = projections(writer)
        metrics = conn.finalize()
        conn.execute = execute
        assert actual == projections(conn)
        assert writer.relationship_rows < 150
        assert metrics["closure_rows"] < 25
        assert not any("WHERE id=? OR source_planned_entry_id=?" in sql for sql, _ in queries)
        epoch_queries = [(sql, params) for sql, params in queries if "source_planned_entry_id=? AND confirmed_month" in sql]
        assert epoch_queries
        for sql, parameters in epoch_queries:
            plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN "+sql, parameters)]
            assert any("sync_input_recurring_epoch" in row and "SEARCH" in row for row in plan)
        conn.commit()
        verify(conn)


def test_stale_cache_cannot_be_recertified_by_finalizer(sandbox):
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        conn.execute("UPDATE cash_flows SET amount_value=-51 WHERE id=100")
        # Keep the event financially coherent; corrupt ONLY the maintained cache.
        conn.execute("UPDATE card_payment_events SET total_amount=51 WHERE id=100")
        conn.execute("UPDATE card_payment_allocations SET amount_value=51 WHERE id=100")
        with conn._metadata():
            conn.execute("UPDATE sync_cash_prefix SET total='999'")
        with pytest.raises(CanonicalError, match="STALE_MAINTAINED"):
            conn.finalize()
    with sandbox.connect() as conn:
        assert verify(conn) == before


def test_input_scope_old_transaction_cannot_authorize_new_one(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        old = BoundedInputs(conn)
        conn.rollback()
        conn.begin_capture()
        with pytest.raises(CanonicalError, match="CONTEXT"):
            old.validate_card_ownership()
        conn.rollback()


@pytest.mark.parametrize("occurred_on,amount", [("2026-10-06", 1), ("2026-10-05", -1)])
def test_fixed_rejection_parity_and_no_durable_mutation(sandbox, occurred_on, amount):
    from app.repositories.panels import create_panel
    from app.schemas import MonthlyPanelIn
    from app.services.panels import confirm_fixed_panel
    with sandbox.connect() as conn:
        before = verify(conn)
        errors = []
        for bounded in (False, True):
            conn.begin_capture()
            writer = BoundedInputs(conn) if bounded else conn
            panel = create_panel(MonthlyPanelIn(month="2026-10", panel_type="fixed", title="fixed", amount_value=100, sort_order=2, due_day=5), conn=writer)
            with pytest.raises(ValueError) as failure:
                confirm_fixed_panel(panel["id"], occurred_on, actual_amount=amount, conn=writer, today=date(2026, 10, 5))
            assert type(failure.value) is ValueError
            errors.append(str(failure.value))
            conn.rollback()
        assert errors[0] == errors[1]
    with sandbox.connect() as conn:
        assert verify(conn) == before


def test_multiple_financial_commands_and_payment_cancellation(sandbox):
    from app.services.card_payments import delete_card_payment_event, set_entry_discount
    with sandbox.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        conn.execute("DELETE FROM card_payment_deferrals")
        flow = create_cash_flow(CashFlowIn(occurred_on="2026-10-05", title="income", amount_value=12345, sort_order=2), conn=writer)
        assert flow["amount_value"] == 12345
        set_entry_discount("card-100", 100, event_date="2026-10-05", conn=writer)
        event = create_card_payment_event(CardPaymentEventIn(event_date="2026-10-05", event_type="immediate", idempotency_key="synthetic-multi-001", allocations=[dict(entry_payment_key="card-100", amount_value=10)]), today=date(2026, 10, 5), conn=writer)
        assert projections(writer) == projections(conn)
        delete_card_payment_event(event["id"], conn=writer)
        assert projections(writer) == projections(conn)
        conn.finalize()
        conn.commit()
        verify(conn)


def test_legacy_nonpadded_discount_month_is_not_silently_normalized(sandbox):
    from app.services.card_payments import discount_month_status
    with sandbox.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        assert discount_month_status("2026-1", conn=writer) == discount_month_status("2026-1", conn=conn)
        conn.rollback()


def test_unrelated_cash_and_unbatched_discount_history_is_not_a_hot_input(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        for n in range(100):
            insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 500+n, "book_section": "archive", "entry_date": "2026-01-01", "payment_key": "cold-"+str(n)})
            insert(conn, "cash_flows", dict(id=500+n, occurred_on="2026-01-01", title="cold cash", amount_value=100, sort_order=500+n))
            insert(conn, "card_payment_events", dict(id=500+n, event_date="2026-01-01", event_type="discount", total_amount=1))
            insert(conn, "card_payment_allocations", dict(id=500+n, payment_event_id=500+n, entry_payment_key="cold-"+str(n), amount_value=1))
        conn.finalize()
        conn.commit()
        conn.begin_capture()
        writer = BoundedInputs(conn)
        queries = []
        execute = conn.execute
        def observed(sql, parameters=()):
            queries.append((sql, parameters))
            return execute(sql, parameters)
        conn.execute = observed
        actual = projections(writer)
        conn.execute = execute
        assert actual == projections(conn)
        assert writer.relationship_rows < 100
        assert not any("FROM cash_flows\n        WHERE occurred_on <=" in sql for sql, _ in queries)
        discounts = [(sql, params) for sql, params in queries if "JOIN card_payment_events" in sql and "e.event_type='discount'" in sql]
        assert discounts
        for sql, parameters in discounts:
            plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN "+sql, parameters)]
            assert any("SEARCH a USING INDEX idx_card_payment_allocations_entry" in row for row in plan)
        conn.finalize()
        conn.commit()
        verify(conn)


def test_financial_path_forbids_full_algorithm_enumeration(sandbox):
    from isolated_sync.segments import Tree
    with sandbox.connect() as conn:
        conn.begin_capture()
        with patch.object(Tree, "rows", side_effect=AssertionError("full rows forbidden")), \
                patch.object(Tree, "objects", side_effect=AssertionError("full objects forbidden")), \
                patch.object(Index, "facts", side_effect=AssertionError("full facts forbidden")), \
                patch.object(Index, "build", side_effect=AssertionError("full rebuild forbidden")):
            writer = BoundedInputs(conn)
            create_cash_flow(CashFlowIn(occurred_on="2026-10-05", title="bounded", amount_value=1, sort_order=2), conn=writer)
            projections(writer)
            conn.finalize()
            conn.commit()
        verify(conn)


def test_reopening_closed_recurring_period_revalidates_old_epochs(sandbox):
    # A closed child is reusable only while closure context still permits it.
    # Reopening MUST inspect it, even with an otherwise unchanged template.
    with sandbox.connect() as conn:
        conn.begin_capture()
        writer = BoundedInputs(conn)
        source = append_planned_entry(PlannedEntryIn(title="service", usage_place="service", amount_value=500, due_day=5), conn=writer)
        confirm_planned_entry(source["id"], today=date(2026, 10, 5), conn=writer)
        conn.execute("INSERT INTO app_settings(key,value) VALUES ('last_closed_month','2026-10')")
        conn.execute("UPDATE ledger_entries SET confirmed_month=NULL,confirmed_at=NULL,entry_date=NULL WHERE id=?", (source["id"],))
        conn.finalize()
        conn.commit()
        before = verify(conn)
        conn.begin_capture()
        writer = BoundedInputs(conn)
        conn.execute("UPDATE app_settings SET value='2026-09' WHERE key='last_closed_month'")
        errors = []
        for view in (conn, writer):
            with pytest.raises(ValueError) as failure:
                validate_runtime_recurring_ownership(view)
            errors.append(str(failure.value))
        assert errors[0] == errors[1]
        with pytest.raises(CanonicalError, match="RECURRING_ACTIVE"):
            conn.finalize()
    with sandbox.connect() as conn:
        assert verify(conn) == before


def test_commit_certificate_fk_lookups_do_not_scan_retained_fences(sandbox):
    # Certificate INSERT must resolve outstanding deferred FKs by target key,
    # not visit every retained transaction's fence. This is not a D1 change.
    with sandbox.connect() as conn, conn._metadata():
        queries = (("INSERT INTO sync_capture_commits VALUES (?,?,?,?,?)", (None,)*5),
                   ("INSERT INTO sync_commits VALUES (?,?,?,?,?,?,?,?,?,?)", (None,)*10))
        plans = [r[3] for sql, params in queries for r in conn.execute("EXPLAIN QUERY PLAN "+sql, params)]
        assert not any(p.startswith("SCAN sync_") for p in plans)
        assert any("sync_input_capture_fence_finalized" in p for p in plans)
        assert any("sync_input_authority_fence_finalized" in p for p in plans)
