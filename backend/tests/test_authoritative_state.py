"""Backend bundle oracle: legacy HTTP projections stay the reference contract."""

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sqlite3
import threading
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.auth import create_mobile_session_token, create_user, _hash_session_token, change_password
from app.config import get_settings
from app.db import init_db, session
from app.money import MAX_MONEY
from app.main import app
from app.repositories.entries import append_planned_entry, confirm_planned_entry, delete_entry
from app.schemas import CardPaymentAllocationIn, CardPaymentEventIn, PlannedEntryIn
from app.services import authoritative_state as bundle_service
from app.services.card_payments import create_month_close_card_payment_batch, create_card_payment_event
from app.services.judgment.common import _MESSAGE_RANDOM
from app.services.month import close_current_month
from tests.db_fixture import IsolatedDatabaseTestCase


class FrozenSnapshotClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return datetime(2026, 10, 5, 12, tzinfo=timezone.utc)


def legacy_acquisition(client, today="2026-10-05"):
    month = today[:7]
    previous = "2026-09-01" if month == "2026-10" else "2026-08-01"
    end = "2026-10-31" if month == "2026-10" else "2026-09-30"
    paths = {
        "B0": "/api/offline-reconciliation/baseline",
        "month_close_status": "/api/month/current/status",
        "entries": "/api/entries/current",
        "panels": "/api/month/current/panels",
        "summary": "/api/month/current/summary",
        "card_payment_status": "/api/card-payments/current",
        "judgment": "/api/judgment/current",
        "confirmed_planned_entries": "/api/month/current/planned/confirmed",
        "settings": "/api/settings",
        "cash_flows": f"/api/cash-flows?from={previous}&to={end}",
        "owner_discount_month": f"/api/card-discounts/months/{month}?scope=owner",
        "family_discount_month": f"/api/card-discounts/months/{month}?scope=family",
        "transit_discount_profile": f"/api/card-discounts/profiles/transit/{month}",
        "B1": "/api/offline-reconciliation/baseline",
    }
    responses = {}
    for key, path in paths.items():
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code, response.text[:300])
        responses[key] = response.json()
    return responses


class AuthoritativeStateTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock_env = patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-05"})
        self.clock_env.start()
        get_settings.cache_clear()
        self.user = create_user("bundle-owner", "synthetic-password-123")
        self.token = create_mobile_session_token(self.user["id"])
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='0' WHERE key IN ('scheduled_income','cash_flow_balance')")
        self.client = TestClient(app, headers={"Authorization": f"Bearer {self.token}"},
                                 raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.clock_env.stop()
        super().tearDown()

    def financial_dump(self):
        with session() as conn:
            return tuple(line for line in conn.iterdump() if "auth_sessions" not in line)

    def assert_equivalent(self, today="2026-10-05"):
        with patch("app.services.snapshot.datetime", FrozenSnapshotClock):
            _MESSAGE_RANDOM.seed(1234)
            old = legacy_acquisition(self.client, today)
            _MESSAGE_RANDOM.seed(1234)
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200, response.text[:500])
        new = response.json()
        self.assertEqual(new["bundle_version"], 1)
        self.assertEqual(new["principal"], {"user_id": self.user["id"]})
        self.assertEqual(new["state"], {k: v for k, v in old.items() if k not in {"B0", "B1"}})
        self.assert_raw_types(new["state"], {k: v for k, v in old.items() if k not in {"B0", "B1"}})
        self.assertEqual(new["snapshot"], old["B1"]["snapshot"])
        self.assertEqual(new["authority"], {k: v for k, v in old["B1"].items() if k != "snapshot"})
        self.assertEqual(old["B0"], old["B1"])
        # JSON preserves exact raw values, nulls, ordering and complete typed fields.
        self.assertEqual(json.loads(response.content)["state"], new["state"])
        # Level 2: every existing typed candidate section is the same input to
        # the unchanged client parsers (the separate Dart oracle exercises them).
        for key in ("entries", "panels", "summary", "cash_flows", "settings",
                    "confirmed_planned_entries", "owner_discount_month", "family_discount_month",
                    "transit_discount_profile", "judgment", "month_close_status", "card_payment_status"):
            self.assertEqual(new["state"][key], old[key], key)
        # Level 3: complete authoritative table/count/data/policy/content hashes
        # and Snapshot ID, not merely a selected monetary total.
        self.assertEqual(new["snapshot"]["manifest"], old["B1"]["snapshot"]["manifest"])
        self.assertEqual(new["snapshot"]["snapshot_id"], old["B1"]["snapshot"]["snapshot_id"])
        return new

    def assert_raw_types(self, new, old):
        self.assertIs(type(new), type(old), f"raw type parity: {new!r} versus {old!r}")
        if isinstance(old, dict):
            for key in old:
                self.assert_raw_types(new[key], old[key])
        elif isinstance(old, list):
            for left, right in zip(new, old):
                self.assert_raw_types(left, right)

    def test_empty_state_matches_all_fourteen_legacy_responses(self):
        before = self.financial_dump()
        self.assert_equivalent()
        self.assertEqual(self.financial_dump(), before)

    def test_unauthenticated_bundle_is_rejected(self):
        response = TestClient(app).get("/api/authoritative-state")
        self.assertEqual(response.status_code, 401)

    def card(self, key, amount=10000, section="current", entry_date="2026-10-03", title="ordinary", override=0, aux=None):
        with session() as conn:
            return conn.execute(
                "INSERT INTO ledger_entries(book_section,entry_kind,entry_date,title,usage_place,"
                "amount_value,sort_order,payment_key,discount_override,aux_amount_value) "
                "VALUES(?,'expense',?,?,'merchant',?,1,?,?,?)",
                (section, entry_date, title, amount, key, override, aux),
            ).lastrowid

    def recurring(self, actual=7000):
        source = append_planned_entry(PlannedEntryIn(title="template", usage_place="service",
                                                    amount_value=5000, due_day=5))["id"]
        result = confirm_planned_entry(source, today=date(2026, 10, 5), actual_amount=actual)
        return source, result["entry"]["id"]

    def test_rich_financial_state_raw_typed_and_baseline_equivalence(self):
        self.card("ordinary")
        self.card("zero-override", override=1, aux=0)
        self.card("utility", title="도시가스")
        self.card("utility-override", title="전기요금", override=1, aux=100)
        for key in ("toll1", "toll2"):
            self.card(key, section="archive", entry_date="2026-09-03", title="하이패스")
        self.card("old-card", section="archive", entry_date="2026-09-03")
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='2026-09' WHERE key='last_closed_month'")
            create_month_close_card_payment_batch(conn, "2026-09")
            for amount, occurred, primary in ((100000, "2026-10-01", 1), (-1234, "2026-10-04", 0),
                                               (3000, "2026-09-03", 0), (9999, "2026-11-01", 0)):
                conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order,is_primary_income) "
                             "VALUES(?,'cash',?,1,?)", (occurred, amount, primary))
            for kind in ("claim", "family_card", "frozen", "fixed"):
                conn.execute("INSERT INTO monthly_panels(month,panel_type,title,amount_value,sort_order,due_day) "
                             "VALUES('2026-10',?,'panel',10000,1,5)", (kind,))
        create_card_payment_event(CardPaymentEventIn(
            idempotency_key="bundle-partial-payment-0001", event_date=date(2026, 10, 5), event_type="immediate",
            allocations=[CardPaymentAllocationIn(entry_payment_key="old-card", amount_value=1000)],
        ), today=date(2026, 10, 5))
        source, child = self.recurring()
        with session() as conn:
            # An active generated child can reside in archive with NULL mutable date.
            conn.execute("UPDATE ledger_entries SET book_section='archive',entry_date=NULL,title='edited actual' WHERE id=?", (child,))
        before = self.financial_dump()
        new = self.assert_equivalent()
        confirmed = next(row for row in new["state"]["confirmed_planned_entries"] if row["id"] == source)
        self.assertEqual(confirmed["confirmed_amount_value"], 7000)
        self.assertEqual(self.financial_dump(), before)
        self.assertTrue(new["state"]["card_payment_status"]["rows"][0]["is_group"])

    def test_early_fixed_and_reset_sensitive_summary_remain_distinct(self):
        self.card("old-card", section="archive", entry_date="2026-09-01")
        with session() as conn:
            create_month_close_card_payment_batch(conn, "2026-09")
            conn.execute("INSERT INTO app_settings(key,value) VALUES('card_payment_liquidity_reset_ack_month','2026-10')")
            flow = conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order) "
                                "VALUES('2026-10-01','early',-7000,1)").lastrowid
            conn.execute("INSERT INTO monthly_panels(month,panel_type,title,amount_value,sort_order,spent_on,"
                         "confirmed_month,confirmed_at,confirmed_cash_flow_id) VALUES('2026-09','fixed','fixed',"
                         "5000,1,'2026-10-01','2026-10','2026-10-01 00:00:00',?)", (flow,))
        new = self.assert_equivalent()
        self.assertGreater(new["state"]["card_payment_status"]["recorded_remaining_total"], 0)
        self.assertEqual(new["state"]["summary"]["card_total"], 0)

    def test_exact_money_boundary_equivalence(self):
        with session() as conn:
            conn.execute("INSERT INTO cash_flows(occurred_on,title,amount_value,sort_order) VALUES('2026-10-03','boundary',?,1)", (MAX_MONEY,))
        self.assertEqual(self.assert_equivalent()["state"]["summary"]["cash_flow_balance"], MAX_MONEY)

    def test_migrated_real_affinity_keeps_raw_payment_representation(self):
        self.db_path.unlink()
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript((Path(__file__).parent / "fixtures/schema_pre_batch.sql").read_text())
        init_db()
        self.user = create_user("historical-owner", "synthetic-password-123")
        self.token = create_mobile_session_token(self.user["id"])
        self.client.headers["Authorization"] = f"Bearer {self.token}"
        self.card("historical-card", section="archive", entry_date="2026-09-03")
        with session() as conn:
            create_month_close_card_payment_batch(conn, "2026-09")
        self.assert_equivalent()

    def test_cancellation_reconfirmation_and_month_close_equivalence(self):
        source, child = self.recurring()
        delete_entry(child)
        confirm_planned_entry(source, today=date(2026, 10, 5), actual_amount=8000)
        self.assert_equivalent()
        with patch.dict(os.environ, {"MONEY_NOTE_TODAY": "2026-10-31"}):
            get_settings.cache_clear()
            close_current_month(today=date(2026, 10, 31), allow_early_close=True)
            self.assert_equivalent(today="2026-10-31")

    def test_one_snapshot_summary_payment_and_three_live_connections(self):
        from app import db
        with patch.object(bundle_service, "export_snapshot_from_connection", wraps=bundle_service.export_snapshot_from_connection) as snapshot, \
             patch.object(bundle_service, "_summary_values_from_read_view", wraps=bundle_service._summary_values_from_read_view) as summary, \
             patch.object(bundle_service, "current_payment_status", wraps=bundle_service.current_payment_status) as payment, \
             patch.object(db, "connect", wraps=db.connect) as connect:
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200, response.text[:500])
        self.assertEqual((snapshot.call_count, summary.call_count, payment.call_count, connect.call_count), (1, 1, 1, 3))

    def test_construction_uses_one_read_only_connection_and_no_helper_clock(self):
        original = bundle_service._construct
        seen = []

        def construct(conn, credential):
            seen.append(conn)
            self.assertTrue(conn.in_transaction)
            self.assertEqual(conn.execute("PRAGMA query_only").fetchone()[0], 1)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("UPDATE app_settings SET value='999' WHERE key='cash_flow_balance'")
            with patch("app.services.summary.app_today", side_effect=AssertionError("independent Summary clock")), \
                 patch("app.services.presentation.app_today", side_effect=AssertionError("independent presenter clock")), \
                 patch("app.repositories.entries.app_today", side_effect=AssertionError("independent entries clock")), \
                 patch("app.services.card_payments.app_today", side_effect=AssertionError("independent payment clock")), \
                 patch("app.services.month.app_today", side_effect=AssertionError("independent month clock")), \
                 patch("app.services.snapshot.app_today", side_effect=AssertionError("independent Snapshot clock")), \
                 patch("app.services.judgment.insight.app_today_iso", side_effect=AssertionError("independent judgment clock")):
                return original(conn, credential)

        self.recurring()
        with patch.object(bundle_service, "_construct", construct):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200, response.text[:500])
        self.assertEqual(len(seen), 1)

    def test_malformed_authoritative_states_reject_the_entire_bundle(self):
        corruptions = {
            "fractional principal": "INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order) VALUES('current','expense','bad',0.5,1)",
            "unsafe money": f"UPDATE app_settings SET value='{MAX_MONEY+1}' WHERE key='cash_flow_balance'",
            "partial recurring": "INSERT INTO ledger_entries(book_section,entry_kind,title,amount_value,sort_order,confirmed_month) VALUES('current','planned','bad',5000,1,'2026-10')",
            "missing fixed child": "INSERT INTO monthly_panels(month,panel_type,title,amount_value,sort_order,confirmed_at,confirmed_month) VALUES('2026-10','fixed','bad',5000,1,'2026-10-01 00:00:00','2026-10')",
            "missing revision": "DELETE FROM authoritative_state_revision",
            "negative revision": "UPDATE authoritative_state_revision SET revision=-1",
            "broken trigger": "DROP TRIGGER revision_ledger_entries_insert",
        }
        for label, sql in corruptions.items():
            with self.subTest(label=label):
                with session() as conn:
                    conn.execute("SAVEPOINT corrupt")
                    conn.execute(sql)
                    # Connection is separate: release/commit to expose exactly this state.
                before = self.financial_dump()
                response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 422, response.text[:500])
                self.assertNotIn("state", response.json())
                self.assertEqual(self.financial_dump(), before)
                # Fresh fixture per corruption without allowing a prior PASS to survive.
                with session() as conn:
                    conn.execute("DELETE FROM ledger_entries")
                    conn.execute("DELETE FROM monthly_panels")
                    conn.execute("UPDATE app_settings SET value='0' WHERE key='cash_flow_balance'")
                    conn.execute("INSERT OR REPLACE INTO authoritative_state_revision(id,revision) VALUES(1,0)")
                    if label == "broken trigger":
                        from app.db import SCHEMA
                        from app.db_migrations import _statements
                        for statement in _statements(SCHEMA):
                            if statement.startswith("CREATE TRIGGER IF NOT EXISTS revision_ledger_entries_insert"):
                                conn.execute(statement)

    def test_projection_model_serialization_snapshot_failures_preserve_financial_state(self):
        for target in ("export_snapshot_from_connection", "current_payment_status", "_prepare", "_terminal_guard"):
            with self.subTest(target=target):
                before = self.financial_dump()
                with patch.object(bundle_service, target, side_effect=RuntimeError("controlled failure")):
                    response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 422)
                self.assertEqual(self.financial_dump(), before)
        for target in ("AuthoritativeState.model_validate", "JSONResponse.render"):
            with self.subTest(target=target):
                before = self.financial_dump()
                with patch(f"app.services.authoritative_state.{target}", side_effect=TypeError("controlled encoding failure")):
                    response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 500)
                self.assertEqual(self.financial_dump(), before)

    def test_missing_presentation_field_is_not_replaced_by_a_typed_default(self):
        self.card("missing-projection")
        original = bundle_service.present_ledger_entries

        def incomplete(*args, **kwargs):
            rows = original(*args, **kwargs)
            if rows:
                rows[0].pop("effective_discount_amount")
            return rows

        before = self.financial_dump()
        with patch.object(bundle_service, "present_ledger_entries", incomplete):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.financial_dump(), before)

    def write_cash_setting(self, value):
        with session() as conn:
            conn.execute("UPDATE app_settings SET value=? WHERE key='cash_flow_balance'", (str(value),))

    def test_commit_before_financial_pin_is_included(self):
        original = bundle_service._construct

        def before_pin(conn, credential):
            self.write_cash_setting(1234)
            return original(conn, credential)

        with patch.object(bundle_service, "_construct", before_pin):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"]["summary"]["cash_flow_balance"], 1234)

    def test_wal_commit_during_construction_or_encoding_rebuilds_whole_view(self):
        with session() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
        for stage in ("export_snapshot_from_connection", "_prepare"):
            with self.subTest(stage=stage):
                original = getattr(bundle_service, stage)
                count = 0

                def concurrent(*args, **kwargs):
                    nonlocal count
                    result = original(*args, **kwargs)
                    count += 1
                    if count == 1:
                        self.write_cash_setting(3000 + count)
                    return result

                with patch.object(bundle_service, stage, concurrent):
                    response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 200, response.text[:500])
                self.assertEqual(count, 2)
                self.assertEqual(response.json()["state"]["summary"]["cash_flow_balance"], 3001)
                self.assertEqual(response.json()["snapshot"]["data"]["app_settings"],
                                 self.client.get("/api/offline-reconciliation/baseline").json()["snapshot"]["data"]["app_settings"])

    def test_delete_writer_waits_for_read_view_then_terminal_detects_commit(self):
        ready = threading.Event()
        done = threading.Event()
        failures = []
        threads = []
        original_prepare = bundle_service._prepare
        original_guard = bundle_service._terminal_guard

        def writer():
            try:
                with session(transaction_mode="IMMEDIATE") as conn:
                    conn.execute("UPDATE app_settings SET value='4321' WHERE key='cash_flow_balance'")
                    ready.set()
                done.set()
            except Exception as exc:
                failures.append(exc)
                done.set()

        def prepare(value):
            if not threads:
                thread = threading.Thread(target=writer)
                threads.append(thread)
                thread.start()
                self.assertTrue(ready.wait(2))
                self.assertFalse(done.is_set(), "DELETE writer cannot commit through this financial read")
            return original_prepare(value)

        def guard(*args):
            self.assertTrue(done.wait(2))
            return original_guard(*args)

        with patch.object(bundle_service, "_prepare", prepare), patch.object(bundle_service, "_terminal_guard", guard), \
             patch.object(bundle_service, "_construct", wraps=bundle_service._construct) as construct:
            response = self.client.get("/api/authoritative-state")
        for thread in threads:
            thread.join(2)
        self.assertFalse(failures)
        self.assertEqual(response.status_code, 200, response.text[:500])
        self.assertEqual(construct.call_count, 2)
        self.assertEqual(response.json()["state"]["summary"]["cash_flow_balance"], 4321)

    def test_between_view_and_guard_schema_revision_aba_and_bounded_retry(self):
        for change in ("revision", "schema", "ABA", "always"):
            with self.subTest(change=change):
                original = bundle_service._terminal_guard
                calls = 0

                def guard(*args):
                    nonlocal calls
                    calls += 1
                    if calls == 1 or change == "always":
                        if change == "schema":
                            with session() as conn:
                                conn.execute("CREATE INDEX bundle_test_index ON app_settings(value)")
                        elif change == "ABA":
                            with session() as conn:
                                row = conn.execute("SELECT value FROM app_settings WHERE key='cash_flow_balance'").fetchone()
                                conn.execute("UPDATE app_settings SET value='1' WHERE key='cash_flow_balance'")
                                conn.execute("UPDATE app_settings SET value=? WHERE key='cash_flow_balance'", (row[0],))
                        else:
                            self.write_cash_setting(calls)
                    return original(*args)

                with patch.object(bundle_service, "_terminal_guard", guard):
                    response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 409 if change == "always" else 200, response.text[:500])
                self.assertEqual(calls, 3 if change == "always" else 2)

    def test_commit_immediately_after_terminal_pin_is_a_subsequent_event(self):
        original = bundle_service._terminal_guard
        initial = self.client.get("/api/month/current/summary").json()["cash_flow_balance"]

        def guard(*args):
            accepted = original(*args)
            self.write_cash_setting(initial + 1)
            return accepted

        with patch.object(bundle_service, "_terminal_guard", guard):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["state"]["summary"]["cash_flow_balance"], initial)

    def test_midnight_month_transition_rebuilds_all_sections(self):
        dates = [date(2026, 9, 30), date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 1)]
        with patch.object(bundle_service, "app_today", side_effect=dates), \
             patch.object(bundle_service, "_construct", wraps=bundle_service._construct) as construct:
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200, response.text[:500])
        self.assertEqual(construct.call_count, 2)
        new = response.json()
        self.assertEqual(new["authority"]["evaluation_date"], "2026-10-01")
        self.assertEqual(new["state"]["month_close_status"]["calendar_month"], "2026-10")
        self.assertEqual(new["state"]["card_payment_status"]["calendar_date"], "2026-10-01")
        self.assertEqual(new["state"]["owner_discount_month"]["month"], "2026-10")

    def test_original_session_cannot_be_replaced_after_construction(self):
        cases = ("expiry", "revocation", "logout", "deactivation", "relogin", "password", "different-owner")
        for case in cases:
            with self.subTest(case=case):
                token = create_mobile_session_token(self.user["id"])
                self.client.headers["Authorization"] = f"Bearer {token}"
                original = bundle_service._terminal_guard

                def guard(*args):
                    with session() as conn:
                        if case == "expiry":
                            conn.execute("UPDATE auth_sessions SET expires_at='2000-01-01T00:00:00Z' WHERE session_token_hash=?", (_hash_session_token(token),))
                        elif case == "deactivation":
                            conn.execute("UPDATE users SET is_active=0 WHERE id=?", (self.user["id"],))
                        elif case == "different-owner":
                            other = create_user("other-owner", "synthetic-password-123")
                            conn.execute("UPDATE auth_sessions SET user_id=? WHERE session_token_hash=?", (other["id"], _hash_session_token(token)))
                        else:
                            conn.execute("DELETE FROM auth_sessions WHERE session_token_hash=?", (_hash_session_token(token),))
                    if case == "relogin":
                        create_mobile_session_token(self.user["id"])
                    if case == "password":
                        self.assertTrue(change_password(self.user["id"], "synthetic-password-123", "new-password-1234"))
                    return original(*args)

                with patch.object(bundle_service, "_terminal_guard", guard), \
                     patch.object(bundle_service, "_construct", wraps=bundle_service._construct) as construct:
                    response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 401, response.text[:500])
                self.assertEqual(construct.call_count, 1)
                with session() as conn:
                    conn.execute("UPDATE users SET is_active=1 WHERE id=?", (self.user["id"],))

    def test_cookie_credential_never_falls_back_to_valid_bearer(self):
        cookie_token = create_mobile_session_token(self.user["id"])
        self.client.cookies.set(get_settings().session_cookie_name, cookie_token)
        original = bundle_service._terminal_guard

        def guard(*args):
            self.assertEqual(args[0].token_hash, _hash_session_token(cookie_token))
            with session() as conn:
                conn.execute("DELETE FROM auth_sessions WHERE session_token_hash=?", (_hash_session_token(cookie_token),))
            return original(*args)

        with patch.object(bundle_service, "_terminal_guard", guard):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 401)
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/authoritative-state").status_code, 200)

    def test_terminal_time_is_fresh_after_reads_and_does_not_touch_session(self):
        now = datetime.now(timezone.utc)
        with session() as conn:
            conn.execute("UPDATE auth_sessions SET expires_at=? WHERE session_token_hash=?",
                         ((now + timedelta(seconds=30)).strftime("%Y-%m-%dT%H:%M:%SZ"), _hash_session_token(self.token)))
        from app import db
        original_connect = db.connect
        queries = []

        def connect():
            conn = original_connect()
            conn.set_trace_callback(queries.append)
            return conn

        def fresh_now():
            self.assertTrue(any("FROM auth_sessions JOIN users" in sql for sql in queries))
            return now + timedelta(seconds=31)

        with patch.object(db, "connect", connect), patch.object(bundle_service, "_utc_now", fresh_now):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(sum(sql.startswith("UPDATE auth_sessions") for sql in queries), 1)
        self.assertFalse(any(sql.startswith("DELETE FROM auth_sessions") for sql in queries))

    def test_unrevoked_old_session_remains_valid_after_same_owner_login(self):
        original = bundle_service._terminal_guard

        def guard(*args):
            create_mobile_session_token(self.user["id"])
            return original(*args)

        with patch.object(bundle_service, "_terminal_guard", guard):
            response = self.client.get("/api/authoritative-state")
        self.assertEqual(response.status_code, 200)

    def test_independent_parallel_requests_do_not_share_a_view_or_mutable_context(self):
        from concurrent.futures import ThreadPoolExecutor
        identities = []
        contexts = []
        original = bundle_service._construct

        def construct(conn, credential):
            result = original(conn, credential)
            identities.append(conn)
            contexts.append(result[2])
            with self.assertRaises(TypeError):
                result[2].settings["cash_flow_balance"] = "999"
            return result

        with patch.object(bundle_service, "_construct", construct), ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: self.client.get("/api/authoritative-state"), range(2)))
        self.assertTrue(all(response.status_code == 200 for response in responses))
        self.assertIsNot(identities[0], identities[1])
        self.assertIsNot(contexts[0], contexts[1])

    def test_malformed_new_view_never_reuses_a_previous_pass(self):
        self.assertEqual(self.client.get("/api/authoritative-state").status_code, 200)
        self.card("bad-new-state", amount=None)
        with session() as conn:
            batch = conn.execute("INSERT INTO card_payment_batches(usage_month,status) VALUES('2026-09','active')").lastrowid
            entry = conn.execute("SELECT id FROM ledger_entries WHERE payment_key='bad-new-state'").fetchone()[0]
            conn.execute("INSERT INTO card_payment_batch_items(batch_id,entry_id,entry_payment_key) VALUES(?,?,'bad-new-state')", (batch, entry))
        self.assertEqual(self.client.get("/api/authoritative-state").status_code, 422)

    def test_current_missing_column_and_corrupted_snapshot_do_not_get_defaults(self):
        with session() as conn:
            conn.execute("ALTER TABLE monthly_panels DROP COLUMN due_day")
        self.assertEqual(self.client.get("/api/authoritative-state").status_code, 422)

    def test_corrupted_snapshot_generation_rejects_all_sections(self):
        original = bundle_service.export_snapshot_from_connection

        def invalid(*args, **kwargs):
            name, value = original(*args, **kwargs)
            value["data"].pop("ledger_entries")
            return name, value

        with patch.object(bundle_service, "export_snapshot_from_connection", invalid):
            self.assertEqual(self.client.get("/api/authoritative-state").status_code, 422)

    def test_timezone_change_at_terminal_rebuilds_context(self):
        original = bundle_service._terminal_guard
        settings = get_settings()
        offset = settings.timezone_offset_minutes
        count = 0

        def guard(*args):
            nonlocal count
            count += 1
            if count == 1:
                settings.timezone_offset_minutes = offset + 60
            return original(*args)

        try:
            with patch.object(bundle_service, "_terminal_guard", guard):
                self.assertEqual(self.client.get("/api/authoritative-state").status_code, 200)
            self.assertEqual(count, 2)
        finally:
            settings.timezone_offset_minutes = offset

    def test_auth_invalidation_during_wal_encoding_is_seen_by_fresh_terminal_view(self):
        with session() as conn:
            conn.execute("PRAGMA journal_mode=WAL")
        for invalidation in ("expiry", "logout", "deactivation", "password-session-invalidation"):
            with self.subTest(invalidation=invalidation):
                token = create_mobile_session_token(self.user["id"])
                self.client.headers["Authorization"] = f"Bearer {token}"
                original = bundle_service._prepare

                def prepare(value):
                    response = original(value)
                    with session() as conn:
                        if invalidation == "expiry":
                            conn.execute("UPDATE auth_sessions SET expires_at='2000-01-01T00:00:00Z' WHERE session_token_hash=?", (_hash_session_token(token),))
                        elif invalidation == "deactivation":
                            conn.execute("UPDATE users SET is_active=0 WHERE id=?", (self.user["id"],))
                        else:
                            conn.execute("DELETE FROM auth_sessions WHERE user_id=?", (self.user["id"],))
                    return response

                with patch.object(bundle_service, "_prepare", prepare), \
                     patch.object(bundle_service, "_construct", wraps=bundle_service._construct) as construct:
                    response = self.client.get("/api/authoritative-state")
                self.assertEqual(response.status_code, 401)
                self.assertEqual(construct.call_count, 1)
                with session() as conn:
                    conn.execute("UPDATE users SET is_active=1 WHERE id=?", (self.user["id"],))

    def test_bundle_fixed_metadata_requires_the_same_iso_date_format_as_current_v7(self):
        value = {"data": {"monthly_panels": [{
            "panel_type": "fixed", "confirmed_cash_flow_id": 1,
            "confirmed_at": "2026-10-01 00:00:00", "confirmed_month": "2026-10", "spent_on": "20261001",
        }]}}
        with self.assertRaises(ValueError):
            bundle_service._validate_fixed_metadata(value, None)

    def test_baseline_policy_defaults_cannot_omit_either_scope(self):
        original = bundle_service._construct

        def incomplete(conn, credential):
            value, identity, context = original(conn, credential)
            value["authority"]["discount_policy_defaults"].pop("family")
            return value, identity, context

        with patch.object(bundle_service, "_construct", incomplete):
            self.assertEqual(self.client.get("/api/authoritative-state").status_code, 422)
