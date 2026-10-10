from datetime import date
import json
import random
import sqlite3
from pathlib import Path

import pytest

from app.services.snapshot import _validate_financial_relationships, export_snapshot_from_connection
from isolated_sync.canonical import CanonicalError, Key, encode
from isolated_sync.capture import CaptureSandbox
from isolated_sync.facts import REFERENCES, build_facts, read_state, validate_index, validate_state
from isolated_sync.patricia import Index
from isolated_sync.raw import MONEY_SETTINGS, PRIMARY, SHAPES, TABLES, Row
from isolated_sync.rebuild import rebuild
from tests.isolated_sync_reference import audit_tree, c1, facts_from_raw, patricia_root, ref
from tests.test_isolated_sync_capture import ROWS, insert
from tests.test_isolated_sync_segments import CTX


@pytest.fixture
def database():
    with CaptureSandbox(install=False) as sandbox, sandbox.connect() as conn:
        for table, source in ROWS.items():
            value = dict(source)
            if table == "cash_flows":
                value["amount_value"] = -50
            insert(conn, table, value)
        for key in MONEY_SETTINGS:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
        conn.commit()
        yield conn


def test_actual_schema_and_complete_catalog(database):
    data = read_state(database)
    assert len(TABLES) == 11
    for table in TABLES:
        columns = list(database.execute(f"PRAGMA table_info({table})"))
        assert {r[1] for r in columns} == set(SHAPES[table])
        assert [r[1] for r in columns if r[5]] == [PRIMARY[table]]
        actual = {(r[3], r[2]) for r in database.execute(f"PRAGMA foreign_key_list({table})")}
        assert actual == {(f, t) for f, t in REFERENCES.get(table, ()) if t != "@ledger_payment_key"}
    _validate_financial_relationships(database)
    assert not database.execute("PRAGMA foreign_key_check").fetchall()
    full = rebuild(CTX, data)
    assert {f.key: f.value for f in full.index.facts()} == facts_from_raw(CTX, data)
    assert full.index.lookup(["aggregate", "active_batch"])
    assert full.index.lookup(["context", "last_closed_month"])
    assert full.index.object().ref() == patricia_root(CTX, list(full.index.facts()))
    for table, tree in full.trees.items():
        records = audit_tree(tree)
        assert [r["value"] for r in records] == data[table]
        for record in records:
            value, key = record["value"], record["key"]
            expected = ref("row", dict(ns=CTX.ns.wire(), raw_schema=CTX.raw_schema,
                                        table=table, key=key, value=value))["hash"]
            assert json.loads(full.index.lookup(["pk", table, key]).value) == expected
    # Every ref has exactly one inverse committing to its source row, not a locator.
    all_facts = {f.key: f.value for f in full.index.facts()}
    for f in full.index.facts():
        key, value = json.loads(f.key), json.loads(f.value)
        if key[0] == "ref":
            src, pk, field = key[1:]
            inverse = ["reverse", *value, src, pk, field]
            assert all_facts[encode(inverse)] == all_facts[encode(["pk", src, pk])]
    _, snapshot = export_snapshot_from_connection(database, date(2026, 10, 5))
    assert {t: sorted(snapshot["data"][t], key=lambda r: r[PRIMARY[t]]) for t in TABLES} == data


@pytest.mark.parametrize("keys,accepted", [
    ([None, None], True), (["", ""], False), (["same", "same"], False),
    (["A", "a"], True), (["a", "a "], True), (["a\0b", "a\0c"], True),
    (["a\0b", "a\0b"], False), (["é", "é"], True), (["😀", "😁"], True),
    (["😀", "😀"], False), ([" ", ""], True), ([None, ""], True),
])
def test_n4_real_migrated_sqlite_parity(database, keys, accepted):
    database.execute("DELETE FROM card_payment_events")
    database.commit()
    database.execute("SAVEPOINT n4")
    sqlite_ok = True
    try:
        for i, key in enumerate(keys):
            database.execute("INSERT INTO card_payment_events(id,event_date,event_type,total_amount,idempotency_key) "
                             "VALUES (?,'2026-10-05','discount',0,?)", (i+100, key))
    except sqlite3.IntegrityError:
        sqlite_ok = False
    database.execute("ROLLBACK TO n4")
    data = read_state(database)
    template = dict(id=100, batch_id=None, event_date="2026-10-05", event_type="discount", total_amount=0,
                    note="", cash_flow_id=None, idempotency_key=None, request_fingerprint=None, created_at="fixed")
    data["card_payment_events"] = [{**template, "id": i+100, "idempotency_key": key} for i, key in enumerate(keys)]
    try:
        build_facts(CTX, data)
        mobile_contract_ok = True
    except CanonicalError:
        mobile_contract_ok = False
    assert sqlite_ok == mobile_contract_ok == accepted


@pytest.mark.parametrize("attack", ["pk", "payment_key", "batch_pair", "batch_entry", "allocation_pair",
                                    "missing_fk", "missing_logical", "n4", "sum", "outflow", "active",
                                    "cash_owner", "fixed_owner", "setting", "partial_epoch", "missing_reverse"])
def test_structural_attacks(database, attack):
    data = read_state(database)
    if attack == "pk":
        data["ledger_entries"].append(dict(data["ledger_entries"][0]))
    elif attack == "payment_key":
        data["ledger_entries"].append({**data["ledger_entries"][0], "id": 999})
    elif attack in ("batch_pair", "batch_entry"):
        data["card_payment_batch_items"].append({**data["card_payment_batch_items"][0], "id": 999})
    elif attack == "allocation_pair":
        data["card_payment_allocations"].append({**data["card_payment_allocations"][0], "id": 999, "amount_value": 0})
    elif attack == "missing_fk":
        data["card_payment_events"][0]["batch_id"] = 999
    elif attack == "missing_logical":
        data["card_payment_allocations"][0]["entry_payment_key"] = "absent"
    elif attack == "n4":
        event = data["card_payment_events"][0]
        event["idempotency_key"] = ""
        data["card_payment_events"].append({**event, "id": 999, "total_amount": 0, "cash_flow_id": None})
    elif attack == "sum":
        data["card_payment_events"][0]["total_amount"] += 1
    elif attack == "outflow":
        data["cash_flows"][0]["amount_value"] = -49
    elif attack == "active":
        data["card_payment_batches"].append({**data["card_payment_batches"][0], "id": 999})
    elif attack == "cash_owner":
        data["card_payment_events"].append({**data["card_payment_events"][0], "id": 999,
                                            "event_type": "discount", "total_amount": 0})
    elif attack == "fixed_owner":
        panel = data["monthly_panels"][0]
        panel.update(panel_type="fixed", confirmed_cash_flow_id=100, spent_on="2026-10-05",
                     confirmed_month="2026-10", confirmed_at="2026-10-05T12:00:00Z")
    elif attack == "setting":
        data["app_settings"] = [r for r in data["app_settings"] if r["key"] != "card_limit"]
    elif attack == "partial_epoch":
        data["ledger_entries"][0].update(entry_kind="planned", confirmed_month="2026-10")
    else:
        # Individually canonical index missing one inverse is not F(raw).
        facts = build_facts(CTX, data)
        assert {f.key: f.value for f in facts} == facts_from_raw(CTX, data)
        missing = next(f for f in facts if json.loads(f.key)[0] == "reverse")
        corrupted = Index.build(CTX, [f for f in facts if f != missing])
        assert corrupted.validate() == len(facts)-1
        assert corrupted.object().hash != Index.build(CTX, facts).object().hash
        with pytest.raises(CanonicalError, match="REJECT_FACT_COMPLETENESS"):
            validate_index(CTX, data, corrupted)
        return
    with pytest.raises(CanonicalError):
        build_facts(CTX, data)


def test_cascades_set_null_and_unrelated_targets(database):
    before = read_state(database)
    database.execute("DELETE FROM card_payment_batches WHERE id=100")
    data = read_state(database)
    assert not data["card_payment_events"] and not data["card_payment_allocations"]
    assert not data["card_payment_batch_items"]
    # Deferral/registration retain deleted/missing targets: not invented FKs.
    database.execute("DELETE FROM ledger_entries WHERE id=100")
    data = read_state(database)
    assert data["card_payment_deferrals"] and data["notification_candidate_registrations"]
    validate_state(data)
    assert Index.build(CTX, build_facts(CTX, before)).object().hash != Index.build(CTX, build_facts(CTX, data)).object().hash
    database.execute("INSERT INTO card_payment_events(id,event_date,event_type,total_amount,cash_flow_id) "
                     "VALUES (101,'2026-10-05','discount',0,100)")
    database.execute("DELETE FROM cash_flows WHERE id=100")
    data = read_state(database)
    assert data["card_payment_events"][0]["cash_flow_id"] is None
    validate_state(data)


@pytest.mark.parametrize("seed", [66221, 66222])
def test_sqlite_randomized_row_tree_facts_index(database, seed):
    rng = random.Random(seed)
    tree = rebuild(CTX, read_state(database)).trees["app_labels"]
    for step in range(80):
        key = f"random-{rng.randrange(30):02d}"
        old = database.execute("SELECT * FROM app_labels WHERE key=?", (key,)).fetchone()
        if old and rng.randrange(3) == 0:
            database.execute("DELETE FROM app_labels WHERE key=?", (key,))
            tree = tree.delete(Key(key))
        else:
            database.execute("INSERT INTO app_labels(key,value,updated_at) VALUES (?,?,'fixed') "
                             "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, f"{step} 😀"))
            new = dict(database.execute("SELECT * FROM app_labels WHERE key=?", (key,)).fetchone())
            tree = tree.put(Row.make("app_labels", new), replace=old is not None)
        data = read_state(database)
        assert [r["value"] for r in audit_tree(tree)] == data["app_labels"]
        facts = build_facts(CTX, data)
        index = Index.build(CTX, facts)
        assert index.object().ref() == patricia_root(CTX, facts)
        _validate_financial_relationships(database)
        assert not database.execute("PRAGMA foreign_key_check").fetchall()


def test_storage_class_and_sensitive_boundary(database):
    original = read_state(database)["ledger_entries"][0]
    for name in SHAPES["ledger_entries"]:
        for bad in (b"", b"blob"):
            with pytest.raises(CanonicalError):
                Row.make("ledger_entries", {**original, name: bad})
    for value in (1000.0, -0.0):
        row = Row.make("ledger_entries", {**original, "amount_value": value})
        assert row.raw == c1(row.value()) and b'.0' in row.raw
    for value in (0.5, float("inf"), 2**53, "1000", True, 10**1000):
        with pytest.raises(CanonicalError):
            Row.make("ledger_entries", {**original, "amount_value": value})
    with pytest.raises(CanonicalError):
        Row("ledger_entries", Key(999), encode(original))
    database.execute("INSERT INTO app_settings(key,value) VALUES ('share_pin_hash','DO-NOT-TRANSFER')")
    assert not any(r["key"] == "share_pin_hash" for r in read_state(database)["app_settings"])
    with pytest.raises(CanonicalError, match="^REJECT_SENSITIVE_SETTING$"):
        Row.make("app_settings", dict(key="share_pin_is_default", value="DO-NOT-TRANSFER", updated_at="fixed"))
    for key in ("liquidity_status", "base_next_month_liquidity"):
        for value in ("1.5", "1_000", "1e3", "9007199254740992"):
            with pytest.raises(CanonicalError):
                Row.make("app_settings", dict(key=key, value=value, updated_at="fixed"))


@pytest.mark.parametrize("seed", [66231, 66232])
def test_randomized_multi_table_reference_histories(database, seed):
    """Full-state diff here is a TEST oracle, not D2b capture integration."""
    from isolated_sync.segments import Tree

    rng = random.Random(seed)
    before = read_state(database)
    trees = {t: Tree.build(CTX, t, [Row.make(t, r) for r in before[t]]) for t in TABLES}
    old = {f.key: f for f in build_facts(CTX, before)}
    index = Index.build(CTX, old.values())
    for step in range(70):
        i = 1000 + rng.randrange(12)
        existing = database.execute("SELECT id FROM card_payment_events WHERE id=?", (i,)).fetchone()
        if existing and rng.randrange(3) == 0:
            # Event -> allocations cascade; independent cash/ledger delete follows.
            database.execute("DELETE FROM card_payment_events WHERE id=?", (i,))
            database.execute("DELETE FROM cash_flows WHERE id=?", (i,))
            database.execute("DELETE FROM ledger_entries WHERE id=?", (i,))
        elif existing:
            amount = rng.randrange(1000)
            database.execute("UPDATE card_payment_events SET total_amount=?,note=? WHERE id=?", (amount, str(step), i))
            database.execute("UPDATE card_payment_allocations SET amount_value=? WHERE id=?", (amount, i))
            database.execute("UPDATE cash_flows SET amount_value=? WHERE id=?", (-amount, i))
        else:
            amount = rng.randrange(1000)
            insert(database, "ledger_entries", dict(id=i, book_section="archive", entry_kind="expense",
                   entry_date="2020-01-01", title=f"old {step} 😀", amount_value=1000, payment_key=f"random-{i}", sort_order=i))
            insert(database, "cash_flows", dict(id=i, occurred_on="2026-10-05", title="cash", amount_value=-amount, sort_order=i))
            insert(database, "card_payment_events", dict(id=i, event_date="2026-10-05", event_type="immediate",
                   total_amount=amount, cash_flow_id=i, idempotency_key=f"random-{i}"))
            insert(database, "card_payment_allocations", dict(id=i, payment_event_id=i,
                   entry_payment_key=f"random-{i}", amount_value=amount))
        after = read_state(database)
        # Exact SQL raw state, not the tree's own traversal, determines membership.
        for table in TABLES:
            prior = {r[PRIMARY[table]]: r for r in before[table]}
            current = {r[PRIMARY[table]]: r for r in after[table]}
            for key in prior.keys() - current.keys():
                trees[table] = trees[table].delete(Key(key))
            for key in current:
                if current[key] != prior.get(key):
                    trees[table] = trees[table].put(Row.make(table, current[key]), replace=key in prior)
            assert [r["value"] for r in audit_tree(trees[table])] == after[table]
            trees[table].validate()
        new = {f.key: f for f in build_facts(CTX, after)}
        assert {key: f.value for key, f in new.items()} == facts_from_raw(CTX, after)
        for key, fact in old.items():
            if fact != new.get(key):
                index = index.delete(json.loads(key))
        for key, fact in new.items():
            if fact != old.get(key):
                index = index.put(fact)
        assert index.validate() == len(new)
        assert index.object().ref() == patricia_root(CTX, list(new.values()))
        _validate_financial_relationships(database)
        before, old = after, new


def test_cross_leaf_source_set_null_and_fixed_valid_period(database):
    data = read_state(database)
    source = {**data["ledger_entries"][0], "entry_kind": "planned", "entry_date": None,
              "payment_key": None, "confirmed_month": "2026-10", "confirmed_at": "2026-10-05T00:00:00Z"}
    child = {**data["ledger_entries"][0], "id": 900, "source_planned_entry_id": 100,
             "confirmed_month": "2026-10", "confirmed_at": "2026-10-05T00:00:00Z"}
    data["ledger_entries"] = [source, child] + [{**child, "id": i, "source_planned_entry_id": None,
                "payment_key": f"other-{i}", "confirmed_month": None, "confirmed_at": None} for i in range(101, 900)]
    data["card_payment_batch_items"][0]["entry_id"] = 900
    full = rebuild(CTX, data)
    assert full.trees["ledger_entries"].root.height == 1
    assert full.index.lookup(["reverse", "ledger_entries", ["i", "100"], "ledger_entries", ["i", "900"], "source_planned_entry_id"])
    # SQLite's SET NULL does not erase an execution epoch: invalid final state.
    database.execute("DELETE FROM card_payment_batches WHERE id=100")
    insert(database, "ledger_entries", {**child, "id": 901, "payment_key": "child-901"})
    database.execute("UPDATE ledger_entries SET entry_kind='planned',entry_date=NULL,confirmed_month='2026-10',"
                     "confirmed_at='2026-10-05T00:00:00Z' WHERE id=100")
    database.execute("DELETE FROM ledger_entries WHERE id=100")
    assert database.execute("SELECT source_planned_entry_id FROM ledger_entries WHERE id=901").fetchone()[0] is None
    with pytest.raises(CanonicalError):
        validate_state(read_state(database))


def test_fixed_cash_current_and_early_next_period(database):
    database.execute("DELETE FROM card_payment_batches WHERE id=100")
    database.execute("UPDATE monthly_panels SET panel_type='fixed',confirmed_cash_flow_id=100,"
                     "spent_on='2026-10-05',confirmed_month='2026-10',confirmed_at='2026-10-05T12:00:00Z' WHERE id=100")
    validate_state(read_state(database))
    _validate_financial_relationships(database)
    database.execute("UPDATE app_settings SET value='2026-10' WHERE key='last_closed_month'")
    # Last-closed may be absent in a bare migrated DB, so explicitly create it.
    database.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES ('last_closed_month','2026-10')")
    database.execute("UPDATE cash_flows SET occurred_on='2026-10-31' WHERE id=100")
    database.execute("UPDATE monthly_panels SET spent_on='2026-10-31',confirmed_month='2026-11' WHERE id=100")
    facts = build_facts(CTX, read_state(database))
    assert Index.build(CTX, facts).lookup(["unique", "cash_owner", [["i", "100"]]])
    _validate_financial_relationships(database)
    database.execute("UPDATE monthly_panels SET confirmed_month='2026-12' WHERE id=100")
    with pytest.raises(CanonicalError):
        build_facts(CTX, read_state(database))


def test_all_nullable_columns_preserve_null_and_no_blob(database):
    data = read_state(database)
    for table in TABLES:
        original = data[table][0]
        for column, spec in SHAPES[table].items():
            with pytest.raises(CanonicalError):
                Row.make(table, {**original, column: b""})
            if spec.startswith("?"):
                row = Row.make(table, {**original, column: None})
                assert row.value()[column] is None
            else:
                with pytest.raises(CanonicalError):
                    Row.make(table, {**original, column: None})


@pytest.mark.parametrize("table", TABLES)
def test_every_primary_identity_matches_sqlite(database, table):
    data = read_state(database)
    duplicate = data[table][0]
    database.execute("SAVEPOINT duplicate")
    with pytest.raises(sqlite3.IntegrityError):
        insert(database, table, duplicate)
    database.execute("ROLLBACK TO duplicate")
    data[table].append(dict(duplicate))
    with pytest.raises(CanonicalError, match="REJECT_DUPLICATE_PK"):
        build_facts(CTX, data)


def test_historical_real_affinity_actual_migration(tmp_path):
    from app.db import SCHEMA
    from app.db_migrations import initialize_database

    conn = sqlite3.connect(tmp_path / "synthetic-legacy.sqlite3")
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript((Path(__file__).parent / "fixtures/schema_pre_batch.sql").read_text())
        initialize_database(conn, SCHEMA)
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order) "
                     "VALUES ('current','expense','REAL',1000.0,1)")
        for key in MONEY_SETTINGS:
            conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?, '0')", (key,))
        assert conn.execute("SELECT typeof(amount_value) FROM ledger_entries WHERE title='REAL'").fetchone()[0] == "real"
        full = rebuild(CTX, read_state(conn))
        row = next(r for r in full.trees["ledger_entries"].rows() if r.value()["title"] == "REAL")
        assert type(row.value()["amount_value"]) is float
        assert b'"amount_value":1000.0' in row.raw
        assert row.raw == c1(row.value())
        assert not conn.execute("PRAGMA foreign_key_check").fetchall()
    finally:
        conn.close()
