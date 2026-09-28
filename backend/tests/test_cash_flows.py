from datetime import date
import unittest

from tests.db_fixture import IsolatedDatabaseTestCase
from app.repository import create_cash_flow, list_cash_flows
from app.schemas import CashFlowIn


class CashFlowQueryTest(IsolatedDatabaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        for index, occurred_on in enumerate(
            ("2026-05-31", "2026-06-01", "2026-06-15", "2026-07-01"),
            start=1,
        ):
            create_cash_flow(
                CashFlowIn(
                    occurred_on=occurred_on,
                    title=f"현금흐름 {index}",
                    amount_value=index * 1_000,
                    sort_order=index,
                )
            )


    def test_no_query_returns_every_cash_flow_in_latest_order(self) -> None:
        rows = list_cash_flows()

        self.assertEqual([row["occurred_on"] for row in rows], [
            "2026-07-01",
            "2026-06-15",
            "2026-06-01",
            "2026-05-31",
        ])

    def test_date_range_is_inclusive(self) -> None:
        rows = list_cash_flows(date_from=date(2026, 6, 1), date_to=date(2026, 6, 15))

        self.assertEqual([row["occurred_on"] for row in rows], ["2026-06-15", "2026-06-01"])

    def test_limit_returns_latest_rows_after_date_filter(self) -> None:
        rows = list_cash_flows(date_from="2026-06-01", limit=2)

        self.assertEqual([row["occurred_on"] for row in rows], ["2026-07-01", "2026-06-15"])

    def test_invalid_query_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "시작일"):
            list_cash_flows(date_from="2026-07-01", date_to="2026-06-01")
        with self.assertRaisesRegex(ValueError, "1 이상"):
            list_cash_flows(limit=0)


if __name__ == "__main__":
    unittest.main()
