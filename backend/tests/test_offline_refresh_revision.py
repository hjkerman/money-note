"""Counterexamples for the mobile offline-ready refresh envelope."""

from datetime import date
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.config import get_settings
from app.db import AUTHORITATIVE_REVISION_TABLES, init_db, session
from app.repositories.panels import create_panel
from app.repositories.notification_registration import registration_fingerprint
from app.schemas import MonthlyPanelIn
from app.services.offline_reconciliation import export_offline_baseline
from app.services.presentation import present_monthly_panel
from app.services.snapshot import SNAPSHOT_TABLES


class RefreshRevisionTest(unittest.TestCase):
    def test_every_snapshot_table_has_a_revision_trigger(self) -> None:
        self.assertEqual(set(AUTHORITATIVE_REVISION_TABLES), set(SNAPSHOT_TABLES))

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {"MONEY_NOTE_DB_PATH": str(Path(self.temp_dir.name) / "fixture.sqlite3")},
        )
        self.env.start()
        get_settings.cache_clear()
        init_db()

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_same_second_aba_changes_revision_even_when_hash_returns_to_a(self) -> None:
        first = export_offline_baseline()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '101234' WHERE key = 'card_limit'")
        middle = export_offline_baseline()
        with session() as conn:
            conn.execute("UPDATE app_settings SET value = '5800000' WHERE key = 'card_limit'")
        last = export_offline_baseline()

        self.assertNotEqual(first["state_fingerprint"], middle["state_fingerprint"])
        self.assertEqual(first["state_fingerprint"], last["state_fingerprint"])
        self.assertLess(first["state_revision"], middle["state_revision"])
        self.assertLess(middle["state_revision"], last["state_revision"])

    def test_snapshot_and_revision_share_one_read_transaction(self) -> None:
        first = export_offline_baseline()
        with session() as conn:
            conn.execute(
                "INSERT INTO cash_flows(occurred_on, title, amount_value, sort_order) VALUES ('2026-09-25', '입금', 1234, 0)"
            )
        second = export_offline_baseline()
        self.assertEqual(len(first["snapshot"]["data"]["cash_flows"]), 0)
        self.assertEqual(len(second["snapshot"]["data"]["cash_flows"]), 1)
        self.assertGreater(second["state_revision"], first["state_revision"])

    def test_evaluation_date_changes_without_database_mutation(self) -> None:
        with patch("app.services.offline_reconciliation.app_today", return_value=date(2026, 9, 17)):
            first = export_offline_baseline()
        with patch("app.services.offline_reconciliation.app_today", return_value=date(2026, 9, 18)):
            next_day = export_offline_baseline()
        self.assertEqual(first["state_fingerprint"], next_day["state_fingerprint"])
        self.assertEqual(first["state_revision"], next_day["state_revision"])
        self.assertNotEqual(first["evaluation_date"], next_day["evaluation_date"])

    def test_policy_mutation_advances_generation_even_if_reverted(self) -> None:
        first = export_offline_baseline()
        with session() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:owner:2026-09', 'disabled')"
            )
        middle = export_offline_baseline()
        with session() as conn:
            conn.execute("DELETE FROM app_settings WHERE key = 'card_discount_policy:owner:2026-09'")
        last = export_offline_baseline()
        self.assertEqual(first["state_fingerprint"], last["state_fingerprint"])
        self.assertLess(first["state_revision"], middle["state_revision"])
        self.assertLess(middle["state_revision"], last["state_revision"])

    def test_notification_panel_creation_binds_initial_discount_and_month(self) -> None:
        with session() as conn:
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:family:2026-08', 'enabled')"
            )
            conn.execute(
                "INSERT INTO app_settings(key, value) VALUES ('card_discount_policy:family:2026-09', 'disabled')"
            )
        payload = MonthlyPanelIn(
            month="2026-08", panel_type="family_card", title="가게",
            spent_on="2026-08-31", amount_value=10000, sort_order=0,
            discount_override=1, discount_amount=0,
            candidate_registration_key="woori_card:historical-family",
        )
        off = create_panel(payload)
        self.assertEqual(present_monthly_panel(off)["effective_amount_value"], 10000)
        self.assertEqual(create_panel(payload)["id"], off["id"])
        payload.discount_override = 0
        with self.assertRaisesRegex(ValueError, "다른 내용"):
            create_panel(payload)
        with session() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM monthly_panels").fetchone()[0], 1)

        on_payload = MonthlyPanelIn(
            month="2026-08", panel_type="family_card", title="가게",
            spent_on="2026-08-31", amount_value=10000, sort_order=0,
            candidate_registration_key="woori_card:historical-family-on",
        )
        on = create_panel(on_payload)
        self.assertEqual(present_monthly_panel(on)["effective_amount_value"], 9880)
        on_payload.discount_override = 1
        with self.assertRaisesRegex(ValueError, "다른 내용"):
            create_panel(on_payload)

    def test_manual_claim_family_initial_exclusion_is_atomic_and_idempotent(self) -> None:
        for target in ("claim", "family_card"):
            with self.subTest(target=target):
                key = f"manual-panel:{target}:one"
                payload = MonthlyPanelIn(
                    month="2026-09", panel_type=target, title="생활비",
                    spent_on="2026-09-17", amount_value=10000, sort_order=0,
                    discount_override=1, discount_amount=0,
                    candidate_registration_key=key,
                )
                invalid = payload.model_copy(update={"title": ""})
                with self.assertRaisesRegex(ValueError, "세부내역"):
                    create_panel(invalid)
                # Failure after the row (and its initial discount intent) is inserted
                # still rolls back the whole logical create.
                with patch("app.repositories.panels.save_registration", side_effect=RuntimeError("after insert")):
                    with self.assertRaisesRegex(RuntimeError, "after insert"):
                        create_panel(payload)
                with session() as conn:
                    self.assertEqual(conn.execute(
                        "SELECT COUNT(*) FROM monthly_panels WHERE panel_type = ?", (target,)
                    ).fetchone()[0], 0)
                created = create_panel(payload)  # Treat response as lost.
                retry = create_panel(payload)
                self.assertEqual(retry["id"], created["id"])
                self.assertEqual(present_monthly_panel(retry)["effective_amount_value"], 10000)
                payload.discount_override = 0
                with self.assertRaisesRegex(ValueError, "다른 내용"):
                    create_panel(payload)
                with session() as conn:
                    self.assertEqual(conn.execute(
                        "SELECT COUNT(*) FROM monthly_panels WHERE panel_type = ?", (target,)
                    ).fetchone()[0], 1)

    def test_legacy_candidate_retry_is_upgraded_only_when_final_discount_matches(self) -> None:
        payload = MonthlyPanelIn(
            month="2026-09", panel_type="family_card", title="가게",
            spent_on="2026-09-17", amount_value=10000, sort_order=0,
            discount_override=1, candidate_registration_key="woori_card:legacy-off",
        )
        created = create_panel(payload)
        values = payload.model_dump()
        values["spent_on"] = "2026-09-17"
        old_digest = registration_fingerprint("family_card", values, legacy_panel=True)
        with session() as conn:
            conn.execute(
                "UPDATE notification_candidate_registrations SET request_fingerprint = ? WHERE registration_key = ?",
                (old_digest, "woori_card:legacy-off"),
            )
        self.assertEqual(create_panel(payload)["id"], created["id"])
        payload.discount_override = 0
        with self.assertRaisesRegex(ValueError, "다른 내용"):
            create_panel(payload)

    def test_claim_and_family_candidate_discount_inputs_have_expected_amounts(self) -> None:
        with session() as conn:
            for scope in ("owner", "family"):
                conn.execute(
                    "INSERT INTO app_settings(key, value) VALUES (?, 'enabled')",
                    (f"card_discount_policy:{scope}:2026-08",),
                )
        for target in ("claim", "family_card"):
            for enabled, expected in ((True, 9880), (False, 10000)):
                with self.subTest(target=target, enabled=enabled):
                    created = create_panel(MonthlyPanelIn(
                        month="2026-08", panel_type=target, title="가게",
                        spent_on="2026-08-31", amount_value=10000,
                        sort_order=0, discount_override=0 if enabled else 1,
                        candidate_registration_key=f"woori_card:{target}:{enabled}",
                    ))
                    self.assertEqual(present_monthly_panel(created)["effective_amount_value"], expected)


if __name__ == "__main__":
    unittest.main()
