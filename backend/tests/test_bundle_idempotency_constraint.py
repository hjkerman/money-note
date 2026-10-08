"""Use the ACTUAL migrated partial UNIQUE index, not Snapshot dry-run DDL."""

import json
from pathlib import Path
import sqlite3

from app.db import session
from tests.db_fixture import IsolatedDatabaseTestCase


class BundleIdempotencyConstraintTest(IsolatedDatabaseTestCase):
    def test_mobile_key_matrix_matches_migrated_binary_partial_unique(self):
        fixture = Path(__file__).resolve().parents[2] / "mobile/test/fixtures/bundle_idempotency_keys.json"
        cases = json.loads(fixture.read_text())
        with session() as conn:
            sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='idx_card_payment_events_idempotency'").fetchone()[0]
            self.assertIn("ON card_payment_events(idempotency_key)", sql)
            self.assertIn("WHERE idempotency_key IS NOT NULL", sql)
            columns = conn.execute("PRAGMA index_xinfo(idx_card_payment_events_idempotency)").fetchall()
            self.assertEqual([(r[2], r[4]) for r in columns if r[5]], [("idempotency_key", "BINARY")])
        for case in cases:
            with self.subTest(case=case["name"]), session() as conn:
                conn.execute("DELETE FROM card_payment_events")
                conn.execute("INSERT INTO card_payment_events(event_date,event_type,total_amount,note,idempotency_key) VALUES('2026-10-05','discount',0,'',?)", (case["keys"][0],))
                accepted = True
                try:
                    # Different IDs AND event types must not scope uniqueness.
                    conn.execute("INSERT INTO card_payment_events(event_date,event_type,total_amount,note,idempotency_key) VALUES('2026-10-05','immediate',0,'',?)", (case["keys"][1],))
                except sqlite3.IntegrityError:
                    accepted = False
                self.assertEqual(accepted, case["accept"])
