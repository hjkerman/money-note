"""Representation oracle uses strict canonical UTF-8 AND migrated restoration."""
import copy
from datetime import date
import json
from pathlib import Path

from app.db import session
from app.services import snapshot as snapshots
from tests.db_fixture import IsolatedDatabaseTestCase


def unicode_cases():
    return json.loads((Path(__file__).resolve().parents[2] / "mobile/test/fixtures/bundle_unicode.json").read_text())


def unicode_value(case):
    # JSON decoding combines real pairs; isolated escapes remain invalid scalars.
    return json.loads('"' + ''.join(f"\\u{unit:04x}" for unit in case["units"]) + '"')


class BundleUnicodeTest(IsolatedDatabaseTestCase):
    def test_canonical_utf8_and_actual_migrated_restoration_matrix(self):
        _, original = snapshots.export_snapshot(date(2026, 10, 5))
        for case in unicode_cases():
            with self.subTest(case=case["name"]):
                value = unicode_value(case)
                for representation in (value, {"outer": [value]}, {value: "key"}):
                    if case["accept"]:
                        snapshots._stable_hash(representation)
                    else:
                        with self.assertRaises(UnicodeEncodeError):
                            snapshots._stable_hash(representation)
                specimen = copy.deepcopy(original)
                specimen["data"]["card_payment_events"] = [{
                    "id": 1, "batch_id": None, "event_date": "2026-10-05", "event_type": "discount",
                    "total_amount": 0, "note": "", "cash_flow_id": None, "idempotency_key": value,
                    "request_fingerprint": None, "created_at": "2026-10-05 12:00:00",
                }]
                if case["accept"]:
                    specimen["manifest"] = snapshots._build_manifest(
                        specimen["data"], snapshots._manifest_table_columns(original["manifest"]),
                        policy_context=specimen["card_charge_policy"], snapshot_metadata=snapshots._snapshot_metadata(specimen),
                    )
                    specimen["snapshot_id"] = specimen["manifest"]["content_sha256"]
                    snapshots.validate_reconciliation_snapshot(specimen)
                    snapshots.restore_snapshot(specimen)
                    with session() as conn:
                        self.assertEqual(conn.execute("SELECT idempotency_key FROM card_payment_events").fetchone()[0], value)
                        self.assertIsNotNone(conn.execute("SELECT 1 FROM sqlite_master WHERE name='idx_card_payment_events_idempotency'").fetchone())
                else:
                    # No stale-hash ValueError may hide representation failure.
                    with self.assertRaises(UnicodeEncodeError):
                        snapshots._stable_hash(specimen["data"])
                    with self.assertRaises(UnicodeEncodeError):
                        snapshots.validate_reconciliation_snapshot(specimen)
                    # Bypass only the already-demonstrated hash boundary to
                    # independently exercise REAL restore INSERT/binding path.
                    with session() as conn:
                        before = list(conn.iterdump())
                        conn.execute("SAVEPOINT unicode_oracle")
                        try:
                            with self.assertRaises(UnicodeEncodeError):
                                snapshots.replace_reconciliation_snapshot(conn, specimen["data"])
                        finally:
                            conn.execute("ROLLBACK TO unicode_oracle")
                            conn.execute("RELEASE unicode_oracle")
                        self.assertEqual(list(conn.iterdump()), before)

    def test_valid_unicode_actual_endpoint_preserves_financial_raw_string(self):
        from tests.test_authoritative_state import AuthoritativeStateTest

        oracle = AuthoritativeStateTest()
        oracle.setUp()
        try:
            for case in unicode_cases():
                if not case["accept"]:
                    continue
                with self.subTest(case=case["name"]):
                    value = unicode_value(case)
                    entry_id = oracle.card(f"unicode-{case['name']}", amount=0, title=value)
                    response = oracle.client.get("/api/authoritative-state")
                    self.assertEqual(response.status_code, 200)
                    bundle = response.json()
                    raw = next(row for row in bundle["snapshot"]["data"]["ledger_entries"] if row["id"] == entry_id)
                    projected = next(row for row in bundle["state"]["entries"] if row["id"] == entry_id)
                    self.assertEqual(raw["title"], value)
                    self.assertEqual(projected["title"], value)
        finally:
            oracle.tearDown()
