"""General HTTP writes must preserve discount bounds and transaction atomicity."""
from tests import test_authoritative_state as fixtures
from tests.db_fixture import IsolatedDatabaseTestCase
from app.db import session
from app.services.snapshot import _validate_snapshot


class DiscountWriteTest(IsolatedDatabaseTestCase):
    def setUp(self):
        self.fixture = fixtures.AuthoritativeStateTest()
        self.fixture.setUp()
        self.client = self.fixture.client

    def tearDown(self):
        self.fixture.tearDown()

    def payload(self, **values):
        return dict(book_section="current", entry_kind="expense", entry_date="2026-10-05",
                    usage_place="서점", sort_order=0, amount_value=1000, discount_override=1,
                    aux_amount_value=100, **values)

    def dump(self):
        with session() as conn:
            return tuple(line for line in conn.iterdump()
                         if "audit_logs" not in line and "auth_sessions" not in line)

    def test_post_and_patch_rejection_atomicity(self):
        bad = self.payload(); bad['aux_amount_value'] = 1001
        before = self.dump()
        self.assertEqual(self.client.post('/api/entries', json=bad).status_code, 422)
        self.assertEqual(before, self.dump())
        good = self.client.post('/api/entries', json=self.payload()).json()
        for patch in ({'aux_amount_value':1001}, {'amount_value':99}):
            before = self.dump()
            self.assertEqual(self.client.patch(f"/api/entries/{good['id']}", json=patch).status_code,422)
            self.assertEqual(before,self.dump())

    def test_valid_boundary_summary_bundle_snapshot(self):
        for discount in (0,100,1000):
            payload = self.payload();payload['aux_amount_value']=discount
            response=self.client.post('/api/entries',json=payload)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()['effective_amount_value'],1000-discount)
        bundle=self.client.get('/api/authoritative-state').json()
        rows=bundle['state']['entries']
        self.assertEqual(sum(r['effective_amount_value'] for r in rows),bundle['state']['summary']['card_total'])
        _validate_snapshot(bundle['snapshot'])
        snapshot=self.client.get('/api/admin/snapshot')
        self.assertEqual(snapshot.status_code,200)
        _validate_snapshot(snapshot.json())
        patched=self.client.patch(f"/api/entries/{rows[0]['id']}",json={'amount_value':100,'aux_amount_value':100})
        self.assertEqual(patched.status_code,200,patched.text)
        self.assertEqual(patched.json()['effective_amount_value'],0)



    def test_initial_intent_and_archive_bounds(self):
        for intent in ({'discount_override_amount':1001}, {'book_section':'archive','aux_amount_value':1001}):
            payload=self.payload();payload.update(intent)
            self.assertEqual(self.client.post('/api/entries',json=payload).status_code,422)
        for intent in ({'discount_enabled':False}, {'discount_override_amount':100}):
            payload=self.payload();payload.update(aux_amount_value=1001,**intent)
            self.assertEqual(self.client.post('/api/entries',json=payload).status_code,200)

    def test_legacy_event_discount_amount_reduction(self):
        payload=self.payload();payload.update(discount_override=0,aux_amount_value=None)
        row=self.client.post('/api/entries',json=payload).json()
        with session() as conn:
            event=conn.execute("INSERT INTO card_payment_events(event_date,event_type,total_amount) VALUES ('2026-10-05','discount',200)").lastrowid
            conn.execute('INSERT INTO card_payment_allocations(payment_event_id,entry_payment_key,amount_value) VALUES (?,?,200)',(event,row['payment_key']))
        before=self.dump()
        response=self.client.patch(f"/api/entries/{row['id']}",json={'amount_value':199})
        self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(before,self.dump())
