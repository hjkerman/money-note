"""Money must survive storage and aggregation exactly inside the product domain."""

import copy
import os
import sqlite3
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth import require_user
from app.db import init_db, session
from app.routers import month, operations
from app.services import snapshot
from app.services.summary import current_summary_values
from app import schemas
from app.money import exact_money, money_sum, MONEY_COLUMNS
from app.services.card_charge.policies import flat_statement_discount
from app.services.presentation import present_ledger_entry
from app.services.judgment.insight import app_judgment
from app.routers import entries, card_payments
from tests.db_fixture import IsolatedDatabaseTestCase

SAFE = 2**53 - 1
ERAS = ('pre_batch', 'card_batches', 'fixed_expenses', 'pre_notification',
        'notification', 'offline_phase2', 'current_unversioned', 'current_versioned')


class ExactMoneyDomainTest(IsolatedDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.clock = patch.dict(os.environ, {'MONEY_NOTE_TODAY': '2026-06-11'})
        self.clock.start()
        self.zero_settings()

    def tearDown(self):
        self.clock.stop()
        super().tearDown()

    def zero_settings(self):
        with session() as conn:
            conn.execute("UPDATE app_settings SET value='0' WHERE key IN ('scheduled_income','cash_flow_balance')")

    def historical(self, era):
        self.db_path.unlink()
        if era.startswith('current_'):
            init_db()
            if era == 'current_unversioned':
                with session() as conn:
                    conn.execute('PRAGMA user_version=0')
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript((Path(__file__).parent / 'fixtures' / f'schema_{era}.sql').read_text())

    def durable(self):
        with sqlite3.connect(self.db_path) as conn:
            return tuple(conn.iterdump())

    def client(self):
        app = FastAPI()
        app.include_router(operations.cash_router)
        app.include_router(operations.settings_router)
        app.include_router(month.router)
        app.include_router(entries.router)
        app.include_router(card_payments.payments_router)
        app.dependency_overrides[require_user] = lambda: {'id': 1}
        return TestClient(app, raise_server_exceptions=False)

    def resign(self, artifact):
        artifact['manifest'] = snapshot._build_manifest(artifact['data'],
            policy_context=artifact['card_charge_policy'], snapshot_metadata=snapshot._snapshot_metadata(artifact))
        artifact['snapshot_id'] = artifact['manifest']['content_sha256']
        return artifact

    def test_h1_pre_batch_api_rejects_unsafe_integer_without_rounding(self):
        self.historical('pre_batch')
        init_db()
        self.zero_settings()
        before = self.durable()
        with self.client() as client:
            response = client.post('/api/cash-flows', json={
                'occurred_on': '2026-06-11', 'amount_value': SAFE+2, 'sort_order': 1})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.durable(), before)

    def test_h1_pre_batch_v7_restore_rejects_unsafe_before_replacement(self):
        self.historical('pre_batch')
        init_db()
        artifact = snapshot.export_snapshot()[1]
        artifact['data']['cash_flows'] = [{'id': 1, 'occurred_on': '2026-06-11',
            'amount_value': SAFE+2, 'sort_order': 1}]
        before = self.durable()
        with self.assertRaises(ValueError):
            snapshot.restore_snapshot(self.resign(artifact))
        self.assertEqual(self.durable(), before)

    def test_h2_safe_rows_small_delta_is_not_absorbed_by_real_sum(self):
        self.historical('pre_batch')
        init_db()
        self.zero_settings()
        with session() as conn:
            for amount in (SAFE, 2, -SAFE):
                conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',?,1)", (amount,))
        self.assertEqual(current_summary_values()['cash_flow_balance'], 2)

    def test_h2_safe_final_value_uses_wide_exact_intermediates(self):
        with session() as conn:
            conn.execute("UPDATE app_settings SET value=? WHERE key='cash_flow_balance'", (str(SAFE),))
            conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',2,1)")
            conn.execute("INSERT INTO monthly_panels(month,panel_type,amount_value,sort_order) VALUES('2026-06','frozen',3,1)")
        # Cash itself is outside the external domain even though spendable fits.
        with self.assertRaises(ValueError):
            current_summary_values()

    def test_h2_all_response_components_safe_but_intermediate_exceeds_safe_range(self):
        with session() as conn:
            conn.execute("UPDATE app_settings SET value=? WHERE key='cash_flow_balance'", (str(SAFE),))
            conn.execute("UPDATE app_settings SET value='2' WHERE key='scheduled_income'")
            conn.execute("INSERT INTO monthly_panels(month,panel_type,amount_value,sort_order) VALUES('2026-06','frozen',3,1)")
        self.assertEqual(current_summary_values()['remaining_liquidity'], SAFE-1)
        self.assertEqual(current_summary_values()['current_month_spendable'], SAFE-1)

    def test_m1_aggregate_overflow_is_controlled_not_http_500(self):
        with session() as conn:
            for _ in range(2):
                conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',?,1)", (2**62,))
        with self.client() as client:
            response = client.get('/api/month/current/summary')
        self.assertEqual(response.status_code, 422)

    def test_valid_individual_rows_but_unsafe_aggregate_is_controlled(self):
        with session() as conn:
            for _ in range(2):
                conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',?,1)", (SAFE,))
        with self.client() as client:
            response = client.get('/api/month/current/summary')
        self.assertEqual(response.status_code, 422)

    def test_safe_rows_can_cancel_after_intermediate_exceeds_sqlite_int64(self):
        with session() as conn:
            for amount in [SAFE]*1050 + [-SAFE]*1050 + [1]:
                conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',?,1)",(amount,))
        self.assertEqual(current_summary_values()['cash_flow_balance'],1)
        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
        self.assertEqual(current_summary_values()['cash_flow_balance'],1)

    def test_all_eras_exact_boundary_survives_migration_and_roundtrip(self):
        for era in ERAS:
            with self.subTest(era=era):
                self.historical(era)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',?,1)", (SAFE,))
                init_db()
                self.zero_settings()
                init_db()
                artifact = snapshot.export_snapshot()[1]
                snapshot.restore_snapshot(copy.deepcopy(artifact))
                init_db()
                self.assertEqual(current_summary_values()['cash_flow_balance'], SAFE)
                with session() as conn:
                    self.assertEqual(conn.execute('SELECT amount_value FROM cash_flows').fetchone()[0], SAFE)

    def test_all_eras_unsafe_source_rejected_before_version_or_schema_change(self):
        for era in ERAS:
            with self.subTest(era=era):
                self.historical(era)
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute("INSERT INTO cash_flows(occurred_on,amount_value,sort_order) VALUES('2026-06-11',?,1)", (SAFE+2,))
                before = self.durable()
                with self.assertRaises((ValueError, RuntimeError)):
                    init_db()
                self.assertEqual(self.durable(), before)

    def test_supported_integer_domain_and_fractions(self):
        for value in (0, 1, -1, SAFE, -SAFE, SAFE-1, float(SAFE), '5000.0'):
            with self.subTest(value=value):
                self.assertEqual(exact_money(value), int(float(value)) if value == '5000.0' else int(value))
        for value in (SAFE+1, SAFE+2, -SAFE-1, -SAFE-2, 2**63-1,
                      2**63, 0.5, -0.5, '5000.00000000000001', 'None', float('inf')):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    exact_money(value)
        self.assertEqual(money_sum([SAFE, SAFE, -SAFE, -SAFE, 1]), 1)

    def test_all_accepted_authoritative_model_fields_have_the_same_boundary(self):
        cases = (
            (schemas.LedgerEntryIn, {'book_section':'current','sort_order':1}, ('amount_value','aux_amount_value','discount_override_amount')),
            (schemas.LedgerEntryPatch, {}, ('amount_value','aux_amount_value')),
            (schemas.PlannedEntryIn, {'title':'recurring','usage_place':'shop','due_day':11}, ('amount_value',)),
            (schemas.MonthlyPanelIn, {'month':'2026-06','panel_type':'claim','sort_order':1}, ('amount_value','discount_amount')),
            (schemas.MonthlyPanelPatch, {}, ('amount_value',)),
            (schemas.CashFlowIn, {'occurred_on':'2026-06-11','sort_order':1}, ('amount_value',)),
            (schemas.CardPaymentAllocationIn, {'entry_payment_key':'key'}, ('amount_value',)),
            (schemas.FixedPanelConfirmIn, {'occurred_on':'2026-06-11'}, ('actual_amount',)),
            (schemas.PlannedConfirmIn, {}, ('actual_amount',)),
            (schemas.PanelDiscountPatch, {}, ('discount_amount',)),
            (schemas.LateCardEntryIn, {'entry_date':'2026-05-01','usage_place':'shop'}, ('amount_value',)),
        )
        for model, defaults, fields in cases:
            base = {field:0 for field in fields} | defaults
            for field in fields:
                for value in (0, 1, SAFE, SAFE+1, SAFE+2, 0.5):
                    with self.subTest(model=model.__name__, field=field, value=value):
                        payload = base | {field:value}
                        if value <= SAFE and isinstance(value,int):
                            self.assertEqual(getattr(model.model_validate(payload), field), value)
                        else:
                            with self.assertRaises(ValueError):
                                model.model_validate(payload)

    def test_snapshot_raw_boundaries_every_version_and_financial_column(self):
        for version in (4,5,6,7):
            for table, columns in MONEY_COLUMNS.items():
                for column in columns:
                    for value in (SAFE, float(SAFE), SAFE+1, SAFE+2):
                        with self.subTest(version=version, table=table, column=column, value=value):
                            if value <= SAFE:
                                self.assertEqual(snapshot._normalize_snapshot_row(table, {column:value}, schema_version=version)[column], SAFE)
                            else:
                                with self.assertRaises(ValueError):
                                    snapshot._normalize_snapshot_row(table, {column:value}, schema_version=version)

    def test_discount_rate_remains_exact_and_normal_policy_unchanged(self):
        for value in (10000,5000,SAFE,SAFE-1):
            self.assertEqual(flat_statement_discount(value), value*12//1000)
        self.assertEqual(flat_statement_discount(10000),120)

    def test_presenter_does_not_truncate_malformed_runtime_principal(self):
        for value in (0.5, SAFE+2):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    present_ledger_entry({'amount_value':value,'entry_kind':'expense','payment_key':'key'}, settings={})

    def test_judgment_cash_feature_uses_the_same_exact_money_as_summary(self):
        flows = [{'amount_value':value} for value in (SAFE,2,-SAFE)]
        with patch('app.services.judgment.insight.budget_committee_tone', return_value={}) as budget:
            app_judgment([],[],flows,{'current_month_spendable':2},{}, {})
        self.assertEqual(budget.call_args.args[0]['cash_flow_total'],2)

    def test_settings_read_rejects_unsafe_runtime_money_without_serializing_it(self):
        for key in ('scheduled_income', 'cash_flow_balance', 'card_limit'):
            with self.subTest(key=key):
                with session() as conn:
                    conn.execute('UPDATE app_settings SET value=? WHERE key=?', (str(SAFE+2),key))
                before = self.durable()
                with self.client() as client:
                    response = client.get('/api/settings')
                self.assertEqual(response.status_code,422)
                self.assertEqual(self.durable(),before)
                with session() as conn:
                    conn.execute("UPDATE app_settings SET value='0' WHERE key=?", (key,))

    def test_actual_api_create_paths_safe_boundary_and_unsafe_rejection(self):
        cases = (
            ('/api/entries', {'book_section':'current','entry_date':'2026-06-11','title':'card','usage_place':'shop','sort_order':1}),
            ('/api/cash-flows', {'occurred_on':'2026-06-11','sort_order':1}),
            ('/api/month/current/planned', {'title':'recurring','usage_place':'shop','due_day':11}),
            ('/api/month/current/panels', {'month':'2026-06','panel_type':'claim','title':'claim','spent_on':'2026-06-11','sort_order':1}),
            ('/api/month/current/panels', {'month':'2026-06','panel_type':'family_card','title':'family','spent_on':'2026-06-11','sort_order':1}),
            ('/api/month/current/panels', {'month':'2026-06','panel_type':'fixed','title':'fixed','due_day':11,'sort_order':1}),
        )
        for path, payload in cases:
            with self.subTest(path=path, kind=payload.get('panel_type')):
                self.historical('current_versioned')
                self.zero_settings()
                with self.client() as client:
                    before = self.durable()
                    for amount in (SAFE+1,SAFE+2):
                        response = client.post(path,json=payload | {'amount_value':amount})
                        self.assertEqual(response.status_code,422)
                        self.assertEqual(self.durable(),before)
                    response = client.post(path,json=payload | {'amount_value':SAFE})
                    self.assertEqual(response.status_code,200,response.text)
                    self.assertEqual(response.json()['amount_value'],SAFE)

    def test_each_historical_financial_column_preserves_safe_boundary(self):
        for era in ERAS:
            for table, columns in MONEY_COLUMNS.items():
                for column in columns:
                    with self.subTest(era=era, table=table, column=column):
                        self.historical(era)
                        with sqlite3.connect(self.db_path) as conn:
                            present = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
                            if column not in present:
                                continue  # Future columns belong to numbered migration.
                            if table == 'ledger_entries':
                                conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,entry_date,title,amount_value,aux_amount_value,sort_order,payment_key,discount_override) VALUES(11,'current','expense','2026-06-11','card',?,?,1,'key',1)", (SAFE,SAFE if column=='aux_amount_value' else 0))
                            elif table == 'monthly_panels':
                                conn.execute("INSERT INTO monthly_panels(id,month,panel_type,title,amount_value,discount_amount,sort_order,discount_override) VALUES(11,'2026-06','claim','claim',?,?,1,1)",(SAFE,SAFE if column=='discount_amount' else 0))
                            elif table == 'cash_flows':
                                conn.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order) VALUES(11,'2026-06-11','cash',?,1)",(SAFE,))
                            else:
                                conn.execute("INSERT INTO ledger_entries(id,book_section,entry_kind,entry_date,title,amount_value,sort_order,payment_key,discount_override) VALUES(11,'archive','expense','2026-05-11','card',?,1,'key',1)",(SAFE,))
                                conn.execute("INSERT INTO cash_flows(id,occurred_on,title,amount_value,sort_order) VALUES(21,'2026-06-11','paid',?,1)",(-SAFE,))
                                conn.execute("INSERT INTO card_payment_events(id,event_date,event_type,total_amount,cash_flow_id) VALUES(31,'2026-06-11','immediate',?,21)",(SAFE,))
                                conn.execute("INSERT INTO card_payment_allocations(id,payment_event_id,entry_payment_key,amount_value) VALUES(41,31,'key',?)",(SAFE,))
                        init_db()
                        self.zero_settings()
                        init_db()
                        snapshot.restore_snapshot(snapshot.export_snapshot()[1])
                        init_db()
                        with session() as conn:
                            self.assertEqual(conn.execute(f'SELECT {column} FROM {table}').fetchone()[0],SAFE)
                        # All response monetary quantities must remain exact and bounded.
                        self.assertTrue(all(isinstance(value,int) and abs(value)<=SAFE
                                            for value in current_summary_values().values()))
