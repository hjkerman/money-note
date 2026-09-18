import copy
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.auth import create_user
from app.routers.offline_reconciliation import post_offline_mobile_wins
from app.config import get_settings
from app.db import init_db, session
from app.schemas import OfflineMobileWinsIn
from app.services.offline_reconciliation import (
    ReconciliationConflictError,
    ReconciliationDigestMismatchError,
    apply_mobile_wins,
    export_offline_baseline,
    inspect_reconciliation,
)
from app.services.snapshot import (
    read_pre_restore_backup,
    snapshot_state_fingerprint,
)


class InjectedFailure(RuntimeError):
    pass


class OfflineReconciliationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "money-note.sqlite3"
        self.env = patch.dict(
            os.environ,
            {
                "MONEY_NOTE_DB_PATH": str(self.db_path),
                "MONEY_NOTE_TIMEZONE": "Asia/Seoul",
            },
        )
        self.env.start()
        get_settings.cache_clear()
        init_db()
        self.user = create_user("reconcile-test", "test-password-123", "테스트")
        self._seed_baseline()
        exported = export_offline_baseline()
        self.baseline_snapshot = exported["snapshot"]
        self.baseline_fingerprint = exported["state_fingerprint"]

    def tearDown(self) -> None:
        get_settings.cache_clear()
        self.env.stop()
        self.temp_dir.cleanup()

    def test_failure_before_a_rolls_back_to_server_s(self) -> None:
        self._assert_injected_rollback("before_operation", 1)

    def test_failure_while_applying_b_rolls_back_a_and_server_s(self) -> None:
        self._assert_injected_rollback("before_operation", 2)

    def test_failure_after_c_before_commit_rolls_back_everything(self) -> None:
        self._assert_injected_rollback("before_commit", None)

    def test_commit_response_loss_retry_returns_committed_result_without_duplicates(self) -> None:
        current = self._mutate_server()
        payload = self._payload(
            self._abc_operations(),
            expected_server_fingerprint=current,
            confirm_server_changed=True,
        )

        first = apply_mobile_wins(payload)
        first_counts = self._financial_counts()
        retried = apply_mobile_wins(payload)

        self.assertEqual(retried, first)
        self.assertEqual(self._financial_counts(), first_counts)
        self.assertEqual(retried["status"], "committed")
        self.assertEqual(
            inspect_reconciliation(
                self.baseline_fingerprint,
                payload.reconciliation_id,
            )["reconciliation"],
            first,
        )
        with session() as conn:
            operation_count = conn.execute(
                "SELECT COUNT(*) AS count FROM offline_reconciliation_operations"
            ).fetchone()["count"]
        self.assertEqual(operation_count, 3)

    def test_same_reconciliation_id_with_different_payload_is_hard_rejected(self) -> None:
        current = self._fingerprint()
        payload = self._payload(
            self._abc_operations(),
            expected_server_fingerprint=current,
        )
        apply_mobile_wins(payload)
        changed_operations = self._abc_operations()
        changed_operations[0]["payload"]["amount_value"] = 99999
        changed = self._payload(
            changed_operations,
            reconciliation_id=payload.reconciliation_id,
            expected_server_fingerprint=current,
        )

        with self.assertRaises(ReconciliationDigestMismatchError):
            apply_mobile_wins(changed)

        self.assertEqual(self._financial_counts()["cash_flows"], 1)

    def test_operation_id_cannot_be_replayed_under_a_new_reconciliation(self) -> None:
        first = self._payload(
            self._abc_operations(),
            expected_server_fingerprint=self._fingerprint(),
        )
        apply_mobile_wins(first)
        committed_fingerprint = self._fingerprint()
        committed_counts = self._financial_counts()
        second = self._payload(
            self._abc_operations(),
            reconciliation_id="reconcile-20260918-0002",
            expected_server_fingerprint=committed_fingerprint,
            confirm_server_changed=True,
        )

        with self.assertRaisesRegex(ValueError, "operation_id was already reconciled"):
            apply_mobile_wins(second)

        self.assertEqual(self._fingerprint(), committed_fingerprint)
        self.assertEqual(self._financial_counts(), committed_counts)

    def test_non_contiguous_journal_is_rejected_before_mutation(self) -> None:
        before = self._fingerprint()
        operations = self._abc_operations()
        operations[1]["sequence"] = 3
        payload = self._payload(
            operations,
            expected_server_fingerprint=before,
        )

        with self.assertRaisesRegex(ValueError, "contiguous and ordered"):
            apply_mobile_wins(payload)

        self.assertEqual(self._fingerprint(), before)
        with session() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM offline_reconciliations").fetchone())

    def test_server_change_requires_additional_confirmation_and_mobile_wins_is_apply_b_j(
        self,
    ) -> None:
        server_s_fingerprint = self._mutate_server()
        payload = self._payload(
            self._full_operations(),
            expected_server_fingerprint=server_s_fingerprint,
            confirm_server_changed=False,
        )

        status = inspect_reconciliation(self.baseline_fingerprint)
        self.assertTrue(status["server_changed"])
        self.assertEqual(
            status["current_server_fingerprint"],
            server_s_fingerprint,
        )
        with self.assertRaises(ReconciliationConflictError):
            apply_mobile_wins(payload)

        committed = apply_mobile_wins(payload.model_copy(update={"confirm_server_changed": True}))

        self.assertTrue(committed["server_changed"])
        self.assertEqual(committed["pre_server_fingerprint"], server_s_fingerprint)
        self.assertEqual(committed["operation_count"], 7)
        _, recovery = read_pre_restore_backup(committed["server_artifact_filename"])
        self.assertEqual(
            snapshot_state_fingerprint(recovery),
            server_s_fingerprint,
        )
        with session() as conn:
            titles = {row["title"] for row in conn.execute("SELECT title FROM ledger_entries")}
            cash = {
                row["title"]: row["amount_value"]
                for row in conn.execute("SELECT title, amount_value FROM cash_flows")
            }
            overrides = {
                row["title"]: (row["aux_amount_value"], row["discount_override"])
                for row in conn.execute(
                    """
                    SELECT title, aux_amount_value, discount_override
                    FROM ledger_entries
                    WHERE entry_kind = 'expense'
                    """
                )
            }
            planned = conn.execute(
                """
                SELECT confirmed_month, amount_value
                FROM ledger_entries
                WHERE entry_kind = 'planned'
                """
            ).fetchone()
            fixed = conn.execute(
                """
                SELECT confirmed_cash_flow_id, confirmed_month
                FROM monthly_panels
                WHERE panel_type = 'fixed'
                """
            ).fetchone()
        self.assertNotIn("서버에서만 추가됨", titles)
        self.assertIn("[식당] 기본 할인", titles)
        self.assertIn("[약국] 할인 제외", titles)
        self.assertIn("[서점] 실결제 지정", titles)
        self.assertIn("정기 구독", titles)
        self.assertEqual(cash["현금 출금"], -5000)
        self.assertEqual(cash["현금 입금"], 10000)
        self.assertEqual(cash["월세"], -38000)
        self.assertEqual(overrides["[식당] 기본 할인"], (None, 0))
        self.assertEqual(overrides["[약국] 할인 제외"], (0, 1))
        self.assertEqual(overrides["[서점] 실결제 지정"], (3000, 1))
        self.assertEqual(planned["confirmed_month"], "2026-09")
        self.assertEqual(fixed["confirmed_month"], "2026-09")
        self.assertIsNotNone(fixed["confirmed_cash_flow_id"])
        self.assertEqual(
            committed["summary"],
            {
                "scheduled_income": 1000000,
                "cash_flow_balance": 67000,
                "remaining_liquidity": 999252,
                "current_spending_total": 71000,
                "current_discount_total": 3252,
                "card_total": 67748,
                "planned_recurring_total": 12000,
                "fixed_cash_total": 40000,
                "transfer_or_deposit_total": 52000,
                "frozen_asset_total": 0,
                "claim_original_total": 0,
                "claim_net_total": 0,
                "family_card_original_total": 0,
                "family_card_net_total": 0,
                "visible_cash_flow_total": -33000,
            },
        )

    def test_server_recovery_artifact_failure_prevents_reconciliation(self) -> None:
        before = self._fingerprint()
        payload = self._payload(
            self._abc_operations(),
            expected_server_fingerprint=before,
        )

        with patch(
            "app.services.offline_reconciliation.create_pre_reconcile_server_backup",
            side_effect=OSError("injected artifact failure"),
        ):
            with self.assertRaisesRegex(OSError, "artifact failure"):
                apply_mobile_wins(payload)

        self.assertEqual(self._fingerprint(), before)
        with session() as conn:
            record = conn.execute("SELECT 1 FROM offline_reconciliations").fetchone()
        self.assertIsNone(record)

    def test_mobile_wins_endpoint_requires_current_password(self) -> None:
        before = self._fingerprint()
        payload = self._payload(
            self._abc_operations(),
            expected_server_fingerprint=before,
        ).model_copy(update={"password": "wrong-password"})

        with self.assertRaises(HTTPException) as raised:
            post_offline_mobile_wins(payload, self.user)

        self.assertEqual(raised.exception.status_code, 422)
        self.assertEqual(self._fingerprint(), before)
        with session() as conn:
            self.assertIsNone(conn.execute("SELECT 1 FROM offline_reconciliations").fetchone())

    def test_derived_projection_values_are_never_accepted_as_authoritative_input(self) -> None:
        before = self._fingerprint()
        operation = self._abc_operations()[0]
        operation["payload"]["remaining_liquidity"] = 123
        payload = self._payload(
            [operation],
            expected_server_fingerprint=before,
        )

        with self.assertRaisesRegex(ValueError, "derived financial values"):
            apply_mobile_wins(payload)

        self.assertEqual(self._fingerprint(), before)

    def _assert_injected_rollback(
        self,
        failure_stage: str,
        failure_sequence: int | None,
    ) -> None:
        server_s_fingerprint = self._mutate_server()
        operations = self._abc_operations()
        payload = self._payload(
            operations,
            expected_server_fingerprint=server_s_fingerprint,
            confirm_server_changed=True,
        )

        def inject(stage: str, sequence: int | None) -> None:
            if stage == failure_stage and sequence == failure_sequence:
                raise InjectedFailure(f"{stage}:{sequence}")

        with self.assertRaises(InjectedFailure):
            apply_mobile_wins(payload, failure_injector=inject)

        self.assertEqual(self._fingerprint(), server_s_fingerprint)
        self.assertEqual(len(payload.operations), 3)
        with session() as conn:
            self.assertEqual(
                conn.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM ledger_entries
                    WHERE title LIKE '오프라인 %'
                    """
                ).fetchone()["count"],
                0,
            )
            self.assertIsNone(conn.execute("SELECT 1 FROM offline_reconciliations").fetchone())

    def _seed_baseline(self) -> None:
        with session() as conn:
            conn.executemany(
                """
                INSERT INTO app_settings(key, value)
                VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                (
                    ("scheduled_income", "1000000"),
                    ("cash_flow_balance", "100000"),
                    ("card_discount_policy:owner:2026-09", "enabled"),
                ),
            )
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    id, book_section, entry_kind, title, usage_place, usage_item,
                    amount_value, sort_order, due_day
                )
                VALUES (1, 'current', 'planned', '정기 구독', '구독처', '서비스',
                        12000, 1, 15)
                """
            )
            conn.execute(
                """
                INSERT INTO monthly_panels(
                    id, month, panel_type, title, amount_value, sort_order
                )
                VALUES (1, '2026-09', 'fixed', '월세', 40000, 1)
                """
            )

    def _mutate_server(self) -> str:
        with session() as conn:
            conn.execute(
                """
                INSERT INTO ledger_entries(
                    book_section, entry_kind, entry_date, title, amount_value,
                    sort_order, payment_key
                )
                VALUES ('current', 'expense', '2026-09-11',
                        '서버에서만 추가됨', 7777, 99, 'server-only-payment')
                """
            )
        return self._fingerprint()

    def _fingerprint(self) -> str:
        return export_offline_baseline()["state_fingerprint"]

    def _financial_counts(self) -> dict[str, int]:
        with session() as conn:
            return {
                "ledger_entries": conn.execute(
                    "SELECT COUNT(*) AS count FROM ledger_entries"
                ).fetchone()["count"],
                "cash_flows": conn.execute("SELECT COUNT(*) AS count FROM cash_flows").fetchone()[
                    "count"
                ],
            }

    def _payload(
        self,
        operations: list[dict],
        *,
        reconciliation_id: str = "reconcile-20260918-0001",
        expected_server_fingerprint: str,
        confirm_server_changed: bool = False,
    ) -> OfflineMobileWinsIn:
        return OfflineMobileWinsIn(
            schema_version=1,
            reconciliation_id=reconciliation_id,
            baseline_fingerprint=self.baseline_fingerprint,
            baseline_snapshot=copy.deepcopy(self.baseline_snapshot),
            operations=copy.deepcopy(operations),
            mobile_artifact_sha256="a" * 64,
            expected_server_fingerprint=expected_server_fingerprint,
            confirm_server_changed=confirm_server_changed,
            password="test-only-password",
        )

    @staticmethod
    def _operation(sequence: int, operation_type: str, payload: dict) -> dict:
        return {
            "schema_version": 1,
            "operation_id": f"offline-operation-{sequence:04d}",
            "operation_type": operation_type,
            "payload": payload,
            "created_at": f"2026-09-18T00:00:{sequence:02d}Z",
            "sequence": sequence,
            "status": "pending",
        }

    def _abc_operations(self) -> list[dict]:
        return [
            self._operation(
                1,
                "CREATE_CARD_EXPENSE",
                {
                    "book_section": "current",
                    "entry_kind": "expense",
                    "entry_date": "2026-09-10",
                    "title": "오프라인 A",
                    "usage_place": "상점 A",
                    "usage_item": None,
                    "amount_value": 10000,
                    "spending_category": None,
                    "discount_enabled": True,
                },
            ),
            self._operation(
                2,
                "CREATE_CASH_FLOW",
                {
                    "occurred_on": "2026-09-10",
                    "title": "오프라인 B",
                    "amount_value": -1000,
                    "is_primary_income": 0,
                },
            ),
            self._operation(
                3,
                "CREATE_CARD_EXPENSE",
                {
                    "book_section": "current",
                    "entry_kind": "expense",
                    "entry_date": "2026-09-10",
                    "title": "오프라인 C",
                    "usage_place": "상점 C",
                    "usage_item": None,
                    "amount_value": 20000,
                    "spending_category": None,
                    "discount_enabled": False,
                },
            ),
        ]

    def _full_operations(self) -> list[dict]:
        values = self._abc_operations()
        values[0]["payload"].update(
            {"title": "[식당] 기본 할인", "usage_place": "식당", "usage_item": "기본 할인"}
        )
        values[1] = self._operation(
            2,
            "CREATE_CARD_EXPENSE",
            {
                "book_section": "current",
                "entry_kind": "expense",
                "entry_date": "2026-09-10",
                "title": "[약국] 할인 제외",
                "usage_place": "약국",
                "usage_item": "할인 제외",
                "amount_value": 20000,
                "spending_category": None,
                "discount_enabled": False,
            },
        )
        values[2] = self._operation(
            3,
            "CREATE_CARD_EXPENSE",
            {
                "book_section": "current",
                "entry_kind": "expense",
                "entry_date": "2026-09-10",
                "title": "[서점] 실결제 지정",
                "usage_place": "서점",
                "usage_item": "실결제 지정",
                "amount_value": 30000,
                "spending_category": None,
                "discount_enabled": True,
                "discount_override_amount": 3000,
            },
        )
        values.extend(
            [
                self._operation(
                    4,
                    "CREATE_CASH_FLOW",
                    {
                        "occurred_on": "2026-09-10",
                        "title": "현금 출금",
                        "amount_value": -5000,
                        "is_primary_income": 0,
                    },
                ),
                self._operation(
                    5,
                    "CREATE_CASH_FLOW",
                    {
                        "occurred_on": "2026-09-10",
                        "title": "현금 입금",
                        "amount_value": 10000,
                        "is_primary_income": 0,
                    },
                ),
                self._operation(
                    6,
                    "CONFIRM_FIXED_EXPENSE",
                    {
                        "panel_id": 1,
                        "occurred_on": "2026-09-10",
                        "actual_amount": 38000,
                    },
                ),
                self._operation(
                    7,
                    "CONFIRM_PLANNED_CARD_EXPENSE",
                    {
                        "entry_id": 1,
                        "entry_date": "2026-09-15",
                        "actual_amount": 11000,
                    },
                ),
            ]
        )
        return values


if __name__ == "__main__":
    unittest.main()
