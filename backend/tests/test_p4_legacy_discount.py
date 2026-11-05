"""Read-only legacy discount projection; raw recovery data must remain intact."""
from datetime import date
from unittest.mock import patch

from app.db import session
from app.services.card_charge import DiscountCard, evaluate_stored_charge
from app.services.card_payments import create_month_close_card_payment_batch, current_payment_status, discount_month_status
from app.services.presentation import present_ledger_entries
from app.repositories.entries import list_entries
from app.services.snapshot import export_snapshot
from app.services.summary import current_summary_values
from tests import test_authoritative_state as fixtures
from tests.db_fixture import IsolatedDatabaseTestCase


class LegacyDiscountReadTest(IsolatedDatabaseTestCase):
    def setUp(self):
        self.fixture = fixtures.AuthoritativeStateTest()
        self.fixture.setUp()

    def tearDown(self):
        self.fixture.tearDown()

    def seed(self, *, events=False, section="current", month="2026-10", toll=False):
        with session() as conn:
            for index, amount in enumerate((100, 200)):
                conn.execute("""INSERT INTO ledger_entries
                    (book_section,entry_kind,entry_date,title,usage_place,amount_value,
                     sort_order,payment_key,discount_override,aux_amount_value)
                    VALUES (?,'expense',?,?,?,?,?,?,?,?)""",
                    (section, month+'-02', '고속도로 하이패스' if toll else '서점', '서점',
                     amount,index,f'legacy-{index}',int(not events or index == 1),
                     None if events and index == 0 else (200 if index == 0 else 0)))
            if events:
                event = conn.execute("""INSERT INTO card_payment_events
                    (event_date,event_type,total_amount) VALUES (?,'discount',200)""",
                    (month+'-03',)).lastrowid
                conn.execute("""INSERT INTO card_payment_allocations
                    (payment_event_id,entry_payment_key,amount_value) VALUES (?,'legacy-0',200)""", (event,))

    def financial_dump(self):
        with session() as conn:
            return tuple(line for line in conn.iterdump()
                         if 'auth_sessions' not in line and 'audit_logs' not in line)

    def test_override_summary_bundle_snapshot_are_read_only(self):
        self.check_read_only(False)

    def test_event_summary_bundle_snapshot_are_read_only(self):
        self.check_read_only(True)

    def check_read_only(self, events):
        self.seed(events=events)
        before = self.financial_dump()
        with patch('app.services.snapshot.datetime', fixtures.FrozenSnapshotClock):
            raw_before = export_snapshot()
            rows = present_ledger_entries(list_entries('current'))
            summary = current_summary_values()
            self.assertEqual(summary['card_total'], sum(r['effective_amount_value'] for r in rows))
            self.assertEqual(summary['current_discount_total'], 100)
            self.assertEqual(rows[0]['effective_discount_amount'], 100)
            self.assertEqual(rows[0]['effective_amount_value'], 0)
            self.assertEqual(discount_month_status('2026-10')['discounts']['legacy-0'], 100)
            self.fixture.assert_equivalent()
            response = self.fixture.client.get('/api/authoritative-state')
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['snapshot'], raw_before[1])
            self.assertEqual(export_snapshot(), raw_before)
            self.assertEqual(raw_before[1]['data']['ledger_entries'][0]['aux_amount_value'], None if events else 200)
        self.assertEqual(self.financial_dump(), before)

    def test_override_priority_and_valid_policy_cases(self):
        for card in (DiscountCard.OWNER, DiscountCard.FAMILY):
            for amount, override, enabled, policy, discount in (
                (100,200,True,'enabled',100), (100,100,True,'enabled',100),
                (100,0,True,'enabled',0), (10000,20,True,'disabled',20),
                (10000,None,False,'enabled',120), (10000,None,False,'disabled',0),
                (0,200,True,'enabled',0),
            ):
                with self.subTest(card=card, amount=amount, override=override, policy=policy):
                    result = evaluate_stored_charge(amount,override,enabled,policy,'2026-10','서점',card)
                    self.assertEqual(result.effective_discount_amount,discount)
                    self.assertEqual(result.effective_amount,amount-discount)
        self.seed(events=True)
        with session() as conn:
            conn.execute("UPDATE ledger_entries SET discount_override=1,aux_amount_value=20 WHERE payment_key='legacy-0'")
        row=present_ledger_entries(list_entries('current'))[0]
        self.assertEqual(row['effective_discount_amount'],20)

    def test_active_batch_and_toll_group_do_not_cross_subsidize(self):
        self.seed(section='archive',month='2026-09',toll=True)
        with session() as conn:
            create_month_close_card_payment_batch(conn,'2026-09')
        before=self.financial_dump()
        status=current_payment_status(date(2026,10,5))
        grouped=status['rows'][0]
        self.assertEqual(grouped['effective_discount_amount'],100)
        self.assertEqual(grouped['effective_amount_value'],200)
        self.assertEqual(grouped['remaining_amount'],200)
        self.assertEqual(self.financial_dump(),before)
