"""D2b file-backed differential oracles; full scans happen ONLY in assertions."""

from datetime import date
import os
import random
import signal
import sqlite3
from unittest.mock import patch

import pytest

from app.services.snapshot import export_snapshot_from_connection
from isolated_sync.canonical import CanonicalError, Key, Object, encode
from isolated_sync.capture import CaptureConnection
from isolated_sync.facts import REFERENCES, build_facts, read_state
from isolated_sync.finalization import FinalizationSandbox, generation
from isolated_sync.maintenance import DAY_LIMIT, cash_prefix
from isolated_sync.patricia import Index
from isolated_sync.raw import MONEY_SETTINGS, PRIMARY, TABLES
from tests.isolated_sync_reference import audit_tree, facts_from_raw, patricia_root
from tests.test_isolated_sync_capture import ROWS, insert


@pytest.fixture
def sandbox():
    with FinalizationSandbox() as db:
        with db.connect() as conn:
            for table, source in ROWS.items():
                value = dict(source)
                if table == "cash_flows":
                    value["amount_value"] = -50
                insert(conn, table, value)
            for key in MONEY_SETTINGS:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
        db.install()
        db.bootstrap()
        yield db


def verify(conn):
    """Independent row/facts extraction, separate radix root oracle, SQL totals."""
    current, ctx, store, trees, index = generation(conn)
    data = read_state(conn)
    for table in TABLES:
        assert [r.value() for r in trees[table].rows()] == data[table]
        assert [r["value"] for r in audit_tree(trees[table])] == data[table]
    expected = facts_from_raw(ctx, data)
    assert {f.key: f.value for f in index.facts()} == expected
    assert index.object().ref() == patricia_root(ctx, list(index.facts()))
    assert index.object() == Index.build(ctx, build_facts(ctx, data)).object()
    assert current["revision"] == conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
    from isolated_sync.inputs import input_index, input_key
    from isolated_sync.patricia import Fact
    local_facts = [Fact.make(input_key("cash_prefix", r[0]), r[1]) for r in conn.execute("SELECT ordinal,total FROM sync_cash_prefix")]
    local_facts.extend(Fact.make(input_key(r[0], r[1]), r[2]) for r in conn.execute("SELECT domain,key,total FROM sync_totals"))
    assert input_index(conn, store, current["tx_id"]).object() == Index.build(ctx, local_facts).object()
    for day in ("2026-01-01", "2026-10-05", "9999-12-31"):
        assert cash_prefix(conn, day) == sum(int(r["amount_value"]) for r in data["cash_flows"] if r["occurred_on"] <= day)
    expected_reverse = set()
    for table in TABLES:
        for value in data[table]:
            key = Key(value[PRIMARY[table]])
            for field, dst in REFERENCES.get(table, ()):
                if value[field] is not None:
                    expected_reverse.add((dst, encode(Key(value[field]).wire()), table, encode(key.wire()), field))
            if table == "card_payment_batch_items":
                expected_reverse.add(("@ledger_payment_key", encode(Key(value["entry_payment_key"]).wire()), table,
                                      encode(key.wire()), "entry_payment_key"))
    assert set(map(tuple, conn.execute("SELECT * FROM sync_reverse"))) == expected_reverse
    expected_context = {(table, encode(Key(value[PRIMARY[table]]).wire())) for table in TABLES
                        for value in data[table] if (
                            table == "ledger_entries" and (value["entry_kind"] == "planned" or
                            any(value[f] is not None for f in ("source_planned_entry_id", "confirmed_at", "confirmed_month")))) or (
                            table == "monthly_panels" and value["panel_type"] == "fixed")}
    assert set(map(tuple, conn.execute("SELECT * FROM sync_context_reverse"))) == expected_context
    from collections import Counter
    counts = Counter(("closed_count", row["entry_date"][:7]) for row in data["ledger_entries"]
                     if row["book_section"] == "archive" and row["entry_kind"] == "expense" and row["entry_date"])
    for table, field in (("ledger_entries", "entry_date"), ("monthly_panels", "month"), ("card_payment_batches", "usage_month")):
        counts.update(("policy_horizon", row[field][:7]) for row in data[table] if row[field])
    assert {(r[0], r[1]): int(r[2]) for r in conn.execute("SELECT * FROM sync_totals")} == dict(counts)
    assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    # Every persisted graph edge resolves; no accepted generation uses placeholders.
    assert not conn.execute("SELECT 1 FROM sync_object_edges e LEFT JOIN sync_objects o ON e.child=o.hash WHERE o.hash IS NULL").fetchall()
    return current["raw_hash"], current["index_hash"], current["revision"]


def test_bootstrap_and_single_mutation(sandbox):
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='changed' WHERE id=100")
        metrics = conn.finalize()
        conn.commit()
        assert verify(conn) != before
        assert metrics["net_rows"] == 1
        assert metrics["object_writes"] > 0


@pytest.mark.parametrize("sequence", [
    ["INSERT INTO app_labels VALUES ('new','a','fixed')", "UPDATE app_labels SET value='b' WHERE key='new'"],
    ["INSERT INTO app_labels VALUES ('new','a','fixed')", "DELETE FROM app_labels WHERE key='new'"],
    ["DELETE FROM app_labels WHERE key='d1-label'", "INSERT INTO app_labels VALUES ('d1-label','b','fixed')"],
    ["INSERT INTO ledger_entries(id,book_section,entry_kind,title,sort_order) VALUES (200,'archive','expense','move',1)",
     "UPDATE ledger_entries SET id=201 WHERE id=200"],
    ["UPDATE app_labels SET key='moved' WHERE key='d1-label'"],
    ["UPDATE app_labels SET value='a' WHERE key='d1-label'", "UPDATE app_labels SET value='b' WHERE key='d1-label'"],
])
def test_coalescing_identity_reuse_and_movement(sandbox, sequence):
    with sandbox.connect() as conn:
        conn.begin_capture()
        for sql in sequence:
            conn.execute(sql)
        conn.finalize()
        conn.commit()
        verify(conn)


@pytest.mark.parametrize("stage", ["capture", "coalescing", "trees", "facts", "closure", "aggregates", "objects", "root"])
def test_atomic_failure_reopen(sandbox, stage):
    with sandbox.connect() as conn:
        original = list(conn.iterdump())
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='abort' WHERE id=100")

        def fault(point):
            if point == stage:
                raise RuntimeError("injected")

        with pytest.raises(RuntimeError, match="injected"):
            conn.finalize(fault=fault)
        assert not conn.in_transaction
    with sandbox.connect() as reopened:
        assert list(reopened.iterdump()) == original
        verify(reopened)


def test_second_fence_cannot_accept_capture_only(sandbox):
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='unfinalized' WHERE id=100")
        with pytest.raises(CanonicalError):
            conn.finalize_capture()
        CaptureConnection.finalize_capture(conn)  # explicit D1 base call still cannot commit
        with pytest.raises(sqlite3.IntegrityError):
            conn.commit()
        conn.rollback()
        assert verify(conn) == before


def test_write_after_finalization_and_nested_savepoint(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("SAVEPOINT nested")
        conn.execute("UPDATE ledger_entries SET title='inside' WHERE id=100")
        conn.execute("RELEASE nested")
        with pytest.raises(sqlite3.IntegrityError):
            conn.commit()
        conn.finalize()
        with pytest.raises(sqlite3.IntegrityError, match="capture context"):
            conn.execute("UPDATE ledger_entries SET title='late' WHERE id=100")
        conn.commit()
        verify(conn)


@pytest.mark.parametrize("key", ["share_pin_hash", "share_pin_is_default"])
def test_sensitive_revision_only(sandbox, key):
    sentinel = "SYNTHETIC-DO-NOT-TRANSFER"
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?,?)", (key, sentinel))
        stats = conn.finalize()
        conn.commit()
        after = verify(conn)
        assert after[:2] == before[:2] and after[2] > before[2]
        assert stats["net_rows"] == stats["object_writes"] == 0
        for table, column in (("sync_objects", "body"), ("sync_rows", "body"), ("sync_change_cells", "value")):
            assert not conn.execute(f"SELECT 1 FROM {table} WHERE instr({column},?)>0", (sentinel,)).fetchall()


def test_no_change_and_neutral_sequence(sandbox):
    with sandbox.connect() as conn:
        original = verify(conn)
        for neutral in (False, True):
            conn.begin_capture()
            if neutral:
                conn.execute("INSERT INTO app_labels VALUES ('neutral','a','fixed')")
                conn.execute("DELETE FROM app_labels WHERE key='neutral'")
            stats = conn.finalize()
            conn.commit()
            assert verify(conn)[:2] == original[:2]
            assert stats["object_writes"] == 0


@pytest.mark.parametrize("seed", [662501, 662502, 662503])
def test_random_sql_histories(sandbox, seed):
    rng = random.Random(seed)
    with sandbox.connect() as conn:
        for step in range(40):
            conn.begin_capture()
            for _ in range(rng.randint(1, 5)):
                key = "random-" + str(rng.randrange(20))
                if rng.randrange(3):
                    conn.execute("INSERT INTO app_labels VALUES (?,?,'fixed') ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                 (key, "한글😀" + str(rng.randrange(100))))
                else:
                    conn.execute("DELETE FROM app_labels WHERE key=?", (key,))
            conn.finalize()
            conn.commit()
            verify(conn)


def test_legacy_snapshot_logical_parity(sandbox):
    with sandbox.connect() as conn:
        _, snapshot = export_snapshot_from_connection(conn, date(2026, 10, 5))
        conn.begin_capture()
        conn.execute("UPDATE app_labels SET value=value")
        conn.finalize()
        conn.commit()
        _, after = export_snapshot_from_connection(conn, date(2026, 10, 5))
        assert snapshot["data"] == after["data"]
        assert {k: v for k, v in snapshot["manifest"].items() if k != "content_sha256"} == {
            k: v for k, v in after["manifest"].items() if k != "content_sha256"}
        assert DAY_LIMIT > 3_000_000


@pytest.mark.parametrize("sql", [
    "DELETE FROM card_payment_batches WHERE id=100",
    "DELETE FROM card_payment_events WHERE id=100",
    "UPDATE card_payment_events SET event_type='discount'; DELETE FROM cash_flows WHERE id=100",
])
def test_cascades_and_set_null(sandbox, sql):
    with sandbox.connect() as conn:
        conn.begin_capture()
        for statement in sql.split(";"):
            conn.execute(statement)
        stats = conn.finalize()
        conn.commit()
        assert stats["changes"] >= 2
        verify(conn)


@pytest.mark.parametrize("sql", [
    "UPDATE cash_flows SET amount_value=-99 WHERE id=100",
    "DELETE FROM cash_flows WHERE id=100",
    "DELETE FROM ledger_entries WHERE id=100",
    "UPDATE card_payment_allocations SET amount_value=49 WHERE id=100",
    "DELETE FROM app_settings WHERE key='card_limit'",
    "INSERT INTO ledger_entries(id,book_section,entry_kind,title,sort_order,payment_key) VALUES (200,'archive','expense','bad',2,'card-100')",
    "INSERT INTO card_payment_batches(id,usage_month) VALUES (200,'2026-09')",
])
def test_global_structural_failures_rollback(sandbox, sql):
    with sandbox.connect() as conn:
        before = list(conn.iterdump())
        conn.begin_capture()
        conn.execute(sql)
        with pytest.raises(CanonicalError):
            conn.finalize()
        assert not conn.in_transaction
        assert list(conn.iterdump()) == before
        verify(conn)


def test_event_aggregate_complete_final_state(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("UPDATE card_payment_allocations SET amount_value=75 WHERE id=100")
        conn.execute("UPDATE card_payment_events SET total_amount=75 WHERE id=100")
        conn.execute("UPDATE cash_flows SET amount_value=-75 WHERE id=100")
        conn.finalize()
        conn.commit()
        verify(conn)


@pytest.mark.parametrize("defect", ["marker", "cell", "old", "new", "base", "epoch"])
def test_capture_and_base_defects(sandbox, defect):
    with sandbox.connect() as conn:
        before = list(conn.iterdump())
        tx = conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='changed' WHERE id=100")
        with conn._metadata():
            if defect == "marker":
                conn.execute("DELETE FROM sync_change_cells WHERE revision IN (SELECT revision FROM sync_changes WHERE tx_id=?)", (tx,))
                conn.execute("DELETE FROM sync_changes WHERE tx_id=?", (tx,))
            elif defect == "cell":
                conn.execute("DELETE FROM sync_change_cells WHERE column_name='title' AND revision IN (SELECT revision FROM sync_changes WHERE tx_id=?)", (tx,))
            elif defect in ("old", "new"):
                conn.execute("UPDATE sync_change_cells SET value='forged' WHERE side=? AND column_name='title' AND revision IN (SELECT revision FROM sync_changes WHERE tx_id=?)", (defect, tx))
        args = {"expected_revision": -1} if defect == "base" else {"expected_epoch": "wrong"} if defect == "epoch" else {}
        with pytest.raises((RuntimeError, CanonicalError)):
            conn.finalize(**args)
        assert list(conn.iterdump()) == before


def test_rollback_savepoint_restores_finalization(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='before-savepoint' WHERE id=100")
        conn.execute("SAVEPOINT retry")
        conn.finalize()
        conn.execute("ROLLBACK TO retry")
        conn.execute("RELEASE retry")
        conn.execute("UPDATE ledger_entries SET title='after-rollback' WHERE id=100")
        conn.finalize()
        conn.commit()
        verify(conn)


def test_bound_operations_do_not_use_full_enumeration(sandbox):
    from isolated_sync.segments import Tree
    from isolated_sync.patricia import Index
    with sandbox.connect() as conn:
        statements = []
        conn.set_trace_callback(statements.append)
        with patch.object(Tree, "objects", side_effect=AssertionError("full objects")), patch.object(
            Tree, "rows", side_effect=AssertionError("all rows")), patch.object(
            Index, "facts", side_effect=AssertionError("all facts")), patch.object(
            Index, "build", side_effect=AssertionError("rebuild")):
            conn.begin_capture()
            conn.execute("UPDATE ledger_entries SET title='bounded' WHERE id=100")
            conn.finalize()
            conn.commit()
        conn.set_trace_callback(None)
        assert not any("SELECT * FROM ledger_entries" in s and "WHERE id=" not in s for s in statements)
        verify(conn)


def test_writer_contention_and_reader_atomicity(sandbox):
    with sandbox.connect() as writer, sandbox.connect() as reader, sandbox.connect() as other:
        base = verify(reader)
        writer.begin_capture()
        writer.execute("UPDATE ledger_entries SET title='uncommitted' WHERE id=100")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            other.begin_capture()
        assert verify(reader) == base
        _, old_snapshot = export_snapshot_from_connection(reader, date(2026, 10, 5))
        assert next(r for r in old_snapshot["data"]["ledger_entries"] if r["id"] == 100)["title"] != "uncommitted"
        writer.finalize()
        assert verify(reader) == base
        writer.commit()
        assert verify(reader) != base
        other.begin_capture()
        other.execute("UPDATE ledger_entries SET title='retry' WHERE id=100")
        other.finalize()
        other.commit()
        verify(reader)


@pytest.mark.parametrize("stage", ["raw", "objects", "root", "prepared", "committed"])
def test_process_exit_recovery(sandbox, stage):
    with sandbox.connect() as conn:
        before = verify(conn)
    pid = os.fork()
    if pid == 0:
        try:
            signal.alarm(30)
            conn = sandbox.connect()
            conn.begin_capture()
            conn.execute("UPDATE ledger_entries SET title='process-child' WHERE id=100")
            if stage == "raw":
                os._exit(37)

            def fault(point):
                if point == stage:
                    os._exit(37)

            conn.finalize(fault=fault)
            if stage == "prepared":
                os._exit(37)
            conn.commit()
            os._exit(37)
        except BaseException:
            os._exit(99)
    _, status = os.waitpid(pid, 0)
    assert os.waitstatus_to_exitcode(status) == 37
    with sandbox.connect() as reopened:
        assert (verify(reopened) == before) == (stage != "committed")


@pytest.mark.parametrize("damage", ["object", "missing", "index", "trigger", "columns", "version"])
def test_corruption_and_schema_fail_closed(sandbox, damage):
    with sqlite3.connect(sandbox.path) as conn:
        if damage == "object":
            conn.execute("UPDATE sync_objects SET body=CAST('corrupt' AS BLOB) WHERE hash=(SELECT raw_hash FROM sync_current)")
        elif damage == "missing":
            conn.execute("DELETE FROM sync_objects WHERE hash=(SELECT raw_hash FROM sync_current)")
        elif damage == "index":
            conn.execute("DROP INDEX sync_fk_event_cash")
        elif damage == "trigger":
            conn.execute("DROP TRIGGER revision_cash_flows_insert")
        elif damage == "columns":
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN unexpected TEXT")
        else:
            from isolated_sync.finalization import VERSION
            conn.execute(f"PRAGMA user_version={VERSION+1}")
    with pytest.raises((RuntimeError, CanonicalError)):
        with sandbox.connect() as conn:
            generation(conn)


def test_bootstrap_rotation_and_install_idempotence(sandbox):
    with sandbox.connect() as conn:
        _, before_context, _, _, _ = generation(conn)
        data = read_state(conn)
        revision = conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0]
    sandbox.install()
    after_context = sandbox.bootstrap()
    assert before_context.ns.server_id == after_context.ns.server_id
    assert before_context.ns.dataset_id == after_context.ns.dataset_id
    assert before_context.ns.epoch != after_context.ns.epoch
    with sandbox.connect() as conn:
        verify(conn)
        assert read_state(conn) == data
        assert conn.execute("SELECT revision FROM authoritative_state_revision").fetchone()[0] == revision


def test_unique_swap_removes_all_old_membership_first(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 200, "payment_key": "second"})
        conn.finalize()
        conn.commit()
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET payment_key='temporary' WHERE id=100")
        conn.execute("UPDATE ledger_entries SET payment_key='card-100' WHERE id=200")
        conn.execute("UPDATE ledger_entries SET payment_key='second' WHERE id=100")
        conn.execute("UPDATE card_payment_batch_items SET entry_payment_key='second' WHERE entry_id=100")
        conn.execute("UPDATE card_payment_allocations SET entry_payment_key='second' WHERE entry_payment_key='card-100'")
        conn.finalize()
        conn.commit()
        verify(conn)


@pytest.mark.parametrize("seed", [662511, 662512])
def test_random_multitable_cash_event_histories(sandbox, seed):
    rng = random.Random(seed)
    with sandbox.connect() as conn:
        for step in range(30):
            conn.begin_capture()
            amount = rng.randrange(1, 500)
            conn.execute("UPDATE card_payment_allocations SET amount_value=? WHERE id=100", (amount,))
            conn.execute("UPDATE card_payment_events SET total_amount=? WHERE id=100", (amount,))
            conn.execute("UPDATE cash_flows SET amount_value=? WHERE id=100", (-amount,))
            conn.execute("UPDATE ledger_entries SET title=? WHERE id=100", ("seeded-" + str(step),))
            insert(conn, "cash_flows", dict(id=500+step, occurred_on="2026-07-03", title="history", amount_value=rng.randrange(-500, 500), sort_order=step))
            if step > 2:
                conn.execute("DELETE FROM cash_flows WHERE id=?", (500+step-3,))
            conn.finalize()
            conn.commit()
            verify(conn)


@pytest.mark.parametrize("scenario", ["card", "cash", "recurring", "fixed", "payment", "policy", "archive", "historical_delete"])
def test_actual_financial_writer_parity(scenario):
    from app.repositories.cash_flows import create_cash_flow
    from app.repositories.entries import append_planned_entry, confirm_planned_entry, create_entry, delete_entry
    from app.repositories.panels import create_panel
    from app.schemas import CashFlowIn, LedgerEntryIn, MonthlyPanelIn, PlannedEntryIn, CardPaymentEventIn
    from app.services.card_charge.profiles import set_transit_discount_profile
    from app.services.card_payments import create_card_payment_event, current_payment_status
    from app.services.panels import confirm_fixed_panel
    from app.services.summary import _summary_values_from_read_view, cash_flow_total
    from tests.test_authoritative_state import FrozenSnapshotClock

    results = []
    for segmented in (False, True):
        with FinalizationSandbox() as db:
            with db.connect() as conn:
                for key in MONEY_SETTINGS:
                    conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
                for table, source in ROWS.items():
                    value = dict(source)
                    if table == "cash_flows":
                        value["amount_value"] = -50
                    insert(conn, table, value)
                insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 200, "book_section": "archive", "payment_key": "history"})
                if scenario == "payment":
                    conn.execute("DELETE FROM card_payment_deferrals")
            if segmented:
                db.install()
                db.bootstrap()
            with db.connect() as conn:
                conn.begin_capture() if segmented else conn.execute("BEGIN IMMEDIATE")
                from isolated_sync.inputs import BoundedInputs
                writer = BoundedInputs(conn) if segmented else conn
                writer_queries = []
                conn.set_trace_callback(writer_queries.append)
                if scenario == "card":
                    create_entry(LedgerEntryIn(book_section="current", entry_date="2026-10-05", usage_place="shop", usage_item="item", amount_value=1234, sort_order=2, payment_key="new-card"), conn=writer)
                elif scenario == "cash":
                    create_cash_flow(CashFlowIn(occurred_on="2026-10-05", title="cash", amount_value=-123, sort_order=2), conn=writer)
                elif scenario == "recurring":
                    source = append_planned_entry(PlannedEntryIn(title="recurring", usage_place="service", amount_value=5000, due_day=5), conn=writer)
                    with patch("app.repositories.entries.new_payment_key", return_value="deterministic-recurring"):
                        confirm_planned_entry(source["id"], today=date(2026, 10, 5), actual_amount=4500, conn=writer)
                elif scenario == "fixed":
                    panel = create_panel(MonthlyPanelIn(month="2026-10", panel_type="fixed", title="fixed", amount_value=5000, sort_order=2, due_day=5), conn=writer)
                    confirm_fixed_panel(panel["id"], "2026-10-05", actual_amount=4500, conn=writer, today=date(2026, 10, 5))
                elif scenario == "payment":
                    create_card_payment_event(CardPaymentEventIn(event_date="2026-10-05", event_type="immediate", idempotency_key="d2b-synthetic-receipt", allocations=[dict(entry_payment_key="card-100", amount_value=30)]), today=date(2026, 10, 5), conn=writer)
                elif scenario == "policy":
                    set_transit_discount_profile("2026-10", "owner", conn=writer)
                elif scenario == "archive":
                    conn.execute("UPDATE ledger_entries SET entry_date='2026-07-03',title='edited history' WHERE id=200")
                else:
                    delete_entry(200, conn=writer)
                conn.set_trace_callback(None)
                if scenario in {"payment", "historical_delete"}:
                    # Preserve the original counterexample as the legacy oracle;
                    # the explicit isolated adapter must eliminate that query.
                    assert any(q.strip() == "SELECT * FROM ledger_entries" for q in writer_queries) is (not segmented)
                bounded_summary = _summary_values_from_read_view(writer, today=date(2026, 10, 5))
                assert bounded_summary == _summary_values_from_read_view(conn, today=date(2026, 10, 5))
                assert current_payment_status(date(2026, 10, 5), conn=writer) == current_payment_status(date(2026, 10, 5), conn=conn)
                from tests.test_isolated_sync_capture import freeze_timestamps
                freeze_timestamps(conn)
                if segmented:
                    conn.finalize()
                conn.commit()
            with db.connect() as conn, patch("app.services.snapshot.datetime", FrozenSnapshotClock):
                _, snapshot = export_snapshot_from_connection(conn, date(2026, 10, 5))
                summary = _summary_values_from_read_view(conn, today=date(2026, 10, 5))
                results.append((snapshot, summary, current_payment_status(date(2026, 10, 5), conn=conn)))
                if segmented:
                    verify(conn)
                    assert cash_prefix(conn, "2026-10-05") == cash_flow_total(conn, today=date(2026, 10, 5))
    assert results[0] == results[1]


def test_exact_wide_cash_prefix_and_date_horizon(sandbox):
    from isolated_sync.canonical import MAX_MONEY
    from isolated_sync.maintenance import closed_counts, policy_horizon
    with sandbox.connect() as conn:
        conn.begin_capture()
        for n, amount in enumerate((MAX_MONEY, MAX_MONEY, -MAX_MONEY, -MAX_MONEY)):
            insert(conn, "cash_flows", dict(id=500+n, occurred_on="2026-09-01", title="exact", amount_value=amount, sort_order=n))
        insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 500, "book_section": "archive", "entry_date": "2026-12-31", "payment_key": "future"})
        conn.finalize()
        conn.commit()
        assert cash_prefix(conn, "2026-09-30") == 0
        assert policy_horizon(conn, "2026-10") == "2026-12"
        assert closed_counts(conn) == [1]
        verify(conn)


def test_d1_migration_atomic_failure(sandbox):
    from isolated_sync.finalization import SQL
    from isolated_sync import capture
    with FinalizationSandbox() as db:
        capture.CaptureSandbox.install(db)
        with db.connect() as conn:
            before = list(conn.iterdump())
        with patch("isolated_sync.finalization.SQL", SQL + "CREATE TABLE sync_broken AS SELECT * FROM absent;"):
            with pytest.raises(sqlite3.OperationalError):
                db.install()
        with db.connect() as conn:
            assert conn.execute("PRAGMA user_version").fetchone()[0] == capture.ISOLATED_SCHEMA_VERSION
            assert list(conn.iterdump()) == before


def test_commit_busy_retry_and_storage_full_rollback(sandbox):
    with sandbox.connect() as reader, sandbox.connect() as writer:
        reader.execute("BEGIN DEFERRED")
        before = verify(reader)
        writer.begin_capture()
        writer.execute("UPDATE ledger_entries SET title='busy' WHERE id=100")
        writer.finalize()
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            writer.commit()
        assert verify(reader) == before
        reader.rollback()
        writer.commit()
        verify(writer)
    with sandbox.connect() as conn:
        before = verify(conn)
        conn.begin_capture()
        conn.execute("UPDATE ledger_entries SET title='disk-full' WHERE id=100")

        def limit_storage(stage):
            if stage == "aggregates":
                with conn._metadata():
                    pages = conn.execute("PRAGMA page_count").fetchone()[0]
                    conn.execute(f"PRAGMA max_page_count={pages}")

        with pytest.raises(sqlite3.OperationalError, match="full"):
            conn.finalize(fault=limit_storage)
    with sandbox.connect() as reopened:
        assert verify(reopened) == before


def test_persisted_split_merge_and_reopened_lazy_paths(sandbox):
    with sandbox.connect() as conn:
        conn.begin_capture()
        for n in range(300):
            insert(conn, "ledger_entries", {**ROWS["ledger_entries"], "id": 500+n,
                   "book_section": "archive", "payment_key": "boundary-"+str(n)})
        conn.finalize()
        conn.commit()
        assert generation(conn)[3]["ledger_entries"].root.height == 1
        verify(conn)
    with sandbox.connect() as conn:
        conn.begin_capture()
        conn.execute("DELETE FROM ledger_entries WHERE id BETWEEN 500 AND 799")
        conn.finalize()
        conn.commit()
        assert generation(conn)[3]["ledger_entries"].root.height == 0
        verify(conn)


def test_resolver_rejects_incompatible_versions_and_refs(sandbox):
    with sandbox.connect() as conn:
        _, context, store, _, index = generation(conn)
        for ref in ({"hash": [], "bytes": "1"}, {"hash": "a"*64, "bytes": 1},
                    {"hash": "a"*64, "bytes": "01"}):
            with pytest.raises(CanonicalError):
                store.get(ref, {"raw-root"})
        conn.begin_capture()
        with conn._metadata():
            for value in (True, 2):
                invalid = Object.make({**index.object().body(), "canon": value})
                with pytest.raises(CanonicalError, match="CONTEXT"):
                    store.put(invalid)
            invalid = Object.make({**index.object().body(), "structural": True})
            store.put(invalid)
            with pytest.raises(CanonicalError, match="STRUCTURAL"):
                store.index(invalid.ref())
        conn.rollback()
        verify(conn)


def test_native_fk_mutation_query_plans_use_bounded_child_indexes(sandbox):
    with sandbox.connect() as conn:
        # Include SQLite's native FK work, not just Python-issued SELECTs.
        for table in ("ledger_entries", "cash_flows", "card_payment_batches", "card_payment_events"):
            plan = [r[3] for r in conn.execute(f"EXPLAIN QUERY PLAN DELETE FROM {table} WHERE id=?", (999,))]
            assert not any("SCAN ledger_entries" in p for p in plan), plan
        ledger_plan = [r[3] for r in conn.execute("EXPLAIN QUERY PLAN DELETE FROM ledger_entries WHERE id=999")]
        assert any("sync_fk_entry_source" in p for p in ledger_plan)
