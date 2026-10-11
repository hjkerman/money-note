"""D3B-M01: real ASGI Task.cancel(), native barriers and fresh SQLite oracles.

Timeouts only detect deadlocks. No sleep determines a cancellation ordering.
Helper-only races supplement, rather than replace, the real HTTP regressions.
"""

import asyncio
import json
import sqlite3
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import pytest

from isolated_sync import http, workers
from isolated_sync.observation import ObservationRepository
from isolated_sync.raw import TABLES
from isolated_sync.transfer import TransferLimits
from isolated_sync.workers import WorkerBudget
from tests.test_isolated_sync_observation import EVAL, NOW
from tests.test_isolated_sync_transfer import TOKEN_A, URL, client, observe, request

pytest_plugins = ('tests.test_isolated_sync_transfer',)


def persisted(db):
    # Independent persisted-state oracle. Transfer must not alter ANY of these.
    with sqlite3.connect(db.path, timeout=1) as conn:
        tables = (*TABLES, 'authoritative_state_revision', 'sync_current', 'sync_commits',
                  'sync_observations', 'sync_observation_pins', 'sync_objects')
        state = {table: conn.execute('SELECT * FROM '+table+' ORDER BY rowid').fetchall() for table in tables}
        conn.execute('BEGIN IMMEDIATE')  # No leaked writer lock/transaction.
        conn.rollback()
        return state


class Barrier:
    def __init__(self, loop, stage='authenticated', count=1, fail=False):
        self.loop, self.stage, self.fail = loop, stage, fail
        self.entered = [asyncio.Event() for _ in range(count)]
        self.release = Event()
        self.tickets = []

    def fault(self, stage, ticket):
        if stage != self.stage:
            return
        index = len(self.tickets)
        self.tickets.append(ticket)
        if index < len(self.entered):
            self.loop.call_soon_threadsafe(self.entered[index].set)
        assert self.release.wait(10), 'native barrier not released'
        if self.fail:
            raise RuntimeError('synthetic worker failure')

    async def wait(self, count=1):
        async with asyncio.timeout(10):
            await asyncio.gather(*(e.wait() for e in self.entered[:count]))


class Rig:
    def __init__(self, db, manifest, *, fault=None, limit=2):
        self.manifest = manifest
        repo = ObservationRepository(db, clock=lambda: NOW, evaluation=lambda: EVAL)
        self.adapter = http.Adapter(repo, TransferLimits(concurrent_requests=limit), fault=fault)
        with patch.object(http, 'Adapter', return_value=self.adapter):
            self.app = http.create_app(repo)

    async def invoke(self, messages, *, receive_gate=None, manifest_request=None):
        body = json.dumps(manifest_request or request([self.manifest['target']['raw_ref']['hash']])).encode()
        used = False

        async def receive():
            nonlocal used
            if receive_gate and not used:
                receive_gate[0].set()
                await receive_gate[1].wait()
            if not used:
                used = True
                return dict(type='http.request', body=body, more_body=False)
            await asyncio.Future()  # is_disconnected's cancelled poll = False.

        async def send(message):
            messages.append(message)

        path = URL if manifest_request else URL+'/'+self.manifest['observation_id']+'/objects'
        scope = dict(type='http', asgi={'version': '3.0'}, http_version='1.1', method='POST',
                     scheme='http', path=path, raw_path=path.encode(), query_string=b'', root_path='',
                     headers=[(b'content-type', b'application/json'),
                              (b'authorization', ('Bearer '+TOKEN_A).encode())],
                     client=('127.0.0.1', 1), server=('testserver', 80))
        await self.app(scope, receive, send)

    async def drain(self):
        async with asyncio.timeout(10):
            with self.adapter.workers._lock:
                tasks = list(self.adapter.workers._tasks)
            await asyncio.gather(*tasks, return_exceptions=True)
        assert self.adapter.workers.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)
        permits = [self.adapter.workers.slots.acquire(False) for _ in range(3)]
        assert permits == [True]*self.adapter.limits.concurrent_requests + [False]*(3-self.adapter.limits.concurrent_requests)
        for acquired in permits:
            if acquired:
                self.adapter.workers.slots.release()


async def cancel(task):
    assert task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.parametrize('stage', ['authenticated', 'objects_prepared', 'serialized', 'terminal'])
def test_real_asgi_cancel_retains_native_permit_and_cleans_sqlite(db, stage):
    manifest = observe(client(db)).json()
    before = persisted(db)

    async def scenario():
        barrier = Barrier(asyncio.get_running_loop(), stage, count=2)
        rig = Rig(db, manifest, fault=barrier.fault)
        responses = [[], []]
        tasks = [asyncio.create_task(rig.invoke(m)) for m in responses]
        try:
            # objects_prepared holds BEGIN IMMEDIATE; the second worker waits
            # for SQLite, so this stage uses one barrier entrant, two jobs.
            await barrier.wait(1 if stage == 'objects_prepared' else 2)
            await asyncio.gather(*(cancel(task) for task in tasks))
            assert rig.adapter.workers.snapshot()['leases'] == 2
            assert all(t.cancelled.is_set() for t in barrier.tickets)
            for _ in range(5):
                busy = []
                await rig.invoke(busy)
                assert busy[0]['status'] == 503
                assert b'ROOT_NOT_READY' in busy[1]['body']
            assert rig.adapter.workers.snapshot()['running'] <= 2
            assert responses == [[], []]  # No ASGI start OR body escaped.
        finally:
            barrier.release.set()
            await rig.drain()
        assert responses == [[], []]
        success = []
        await rig.invoke(success)
        assert success[0]['status'] == 200
        await rig.drain()

    asyncio.run(scenario())
    assert persisted(db) == before


def test_cancel_before_ticket_creation_is_not_forgotten(db):
    manifest = observe(client(db)).json()
    before = persisted(db)

    async def scenario():
        barrier = Barrier(asyncio.get_running_loop(), 'before_ticket')
        rig = Rig(db, manifest)
        credential = rig.adapter.credential
        tickets = []

        def blocked(req):
            barrier.fault('before_ticket', None)
            return credential(req)

        def ticket(stage, value):
            tickets.append(value)

        rig.adapter.credential, rig.adapter.fault = blocked, ticket
        messages = []
        task = asyncio.create_task(rig.invoke(messages))
        try:
            await barrier.wait()
            await cancel(task)
            assert rig.adapter.workers.snapshot()['running'] == 1
            assert not tickets
        finally:
            barrier.release.set()
            await rig.drain()
        assert len(tickets) == 1 and tickets[0].cancelled.is_set()
        assert messages == []

    asyncio.run(scenario())
    assert persisted(db) == before


@pytest.mark.parametrize('stage', ['pin_raw', 'before_commit', 'serialized'])
def test_asgi_manifest_cancellation_leaves_absent_or_complete_pins(db, stage):
    manifest = observe(client(db)).json()
    before = persisted(db)
    nonce = dict(protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0)

    async def scenario():
        barrier = Barrier(asyncio.get_running_loop(), stage)
        rig = Rig(db, manifest, fault=barrier.fault)
        create = rig.adapter.repo.create
        def injected(*args, **kwargs):
            return create(*args, **kwargs, fault=lambda point, conn: barrier.fault(point, None))
        rig.adapter.repo.create = injected
        messages = []
        task = asyncio.create_task(rig.invoke(messages, manifest_request=nonce))
        try:
            await barrier.wait()
            await cancel(task)
            assert rig.adapter.workers.snapshot()['running'] == 1
        finally:
            barrier.release.set()
            await rig.drain()
        assert messages == []

    asyncio.run(scenario())
    after = persisted(db)
    if stage != 'serialized':
        assert after == before  # Partial pin insertion rolled back completely.
    else:
        # Response lost AFTER atomic creation may leave a COMPLETE orphan.
        # D3c, not request cancellation, will later retire/release it safely.
        with sqlite3.connect(db.path) as conn:
            rows = conn.execute('SELECT id,status FROM sync_observations WHERE request_id=?', (nonce['request_id'],)).fetchall()
            assert len(rows) == 1 and rows[0][1] == 'available'
            pins = conn.execute('SELECT role,active FROM sync_observation_pins WHERE observation_id=?', (rows[0][0],)).fetchall()
            assert set(pins) == {(role, 1) for role in ('raw', 'index', 'hot', 'control', 'input')}
            assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        for table in (*TABLES, 'authoritative_state_revision', 'sync_current', 'sync_commits'):
            assert after[table] == before[table]


def test_cancel_during_body_admission_has_no_worker_or_permit_leak(db):
    manifest = observe(client(db)).json()

    async def scenario():
        rig = Rig(db, manifest)
        gate = asyncio.Event(), asyncio.Event()
        messages = []
        task = asyncio.create_task(rig.invoke(messages, receive_gate=gate))
        await gate[0].wait()
        assert rig.adapter.workers.snapshot() == dict(leases=1, jobs=0, running=0, tasks=0)
        await cancel(task)
        await rig.drain()
        assert messages == []

    asyncio.run(scenario())


@pytest.mark.parametrize('fail', [False, True])
def test_cancelled_worker_late_result_or_exception_is_observed(db, fail):
    manifest = observe(client(db)).json()

    async def scenario():
        loop = asyncio.get_running_loop()
        errors = []
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        barrier = Barrier(loop, fail=fail)
        rig = Rig(db, manifest, fault=barrier.fault, limit=1)
        messages = []
        task = asyncio.create_task(rig.invoke(messages))
        try:
            await barrier.wait()
            await cancel(task)
            assert rig.adapter.workers.snapshot()['leases'] == 1
        finally:
            barrier.release.set()
            await rig.drain()
        assert not errors and messages == []

    asyncio.run(scenario())


@pytest.mark.parametrize('order', ['cancel_first', 'complete_first'])
def test_asgi_completion_cancellation_race_exact_once(db, order):
    manifest = observe(client(db)).json()

    async def scenario():
        barrier = Barrier(asyncio.get_running_loop(), 'serialized')
        rig = Rig(db, manifest, fault=barrier.fault, limit=1)
        messages = []
        task = asyncio.create_task(rig.invoke(messages))
        try:
            await barrier.wait()
            if order == 'cancel_first':
                task.cancel()
                barrier.release.set()
            else:
                barrier.release.set()
                task.cancel()  # Same event-loop turn as native completion.
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            barrier.release.set()
            await rig.drain()
        assert messages == []

    asyncio.run(scenario())


@pytest.mark.parametrize('point', ['create_task', 'executor'])
def test_submission_failure_releases_exactly_once(db, point):
    manifest = observe(client(db)).json()

    async def failed_dispatch(*args):
        raise RuntimeError('synthetic executor unavailable')

    async def scenario():
        rig = Rig(db, manifest)
        messages = []
        hook = (patch.object(workers.asyncio, 'create_task', side_effect=RuntimeError('synthetic submission failure'))
                if point == 'create_task' else patch.object(workers, 'run_in_threadpool', failed_dispatch))
        with hook:
            await rig.invoke(messages)
        assert messages[0]['status'] == 500
        await rig.drain()
        success = []
        await rig.invoke(success)
        assert success[0]['status'] == 200
        await rig.drain()

    asyncio.run(scenario())


@pytest.mark.parametrize('phase', ['before_start', 'running'])
def test_supervisor_shutdown_cannot_release_a_running_worker(phase):
    async def scenario():
        budget = WorkerBudget(1)
        lease = budget.acquire()
        entered, gate = asyncio.Event(), Event()
        loop = asyncio.get_running_loop()
        called = []

        def function():
            called.append(True)
            loop.call_soon_threadsafe(entered.set)
            assert gate.wait(10)

        async def pending(fn, *args):
            entered.set()
            await asyncio.Future()

        with patch.object(workers, 'run_in_threadpool', pending) if phase == 'before_start' else patch.object(workers, 'run_in_threadpool', workers.run_in_threadpool):
            requester = asyncio.create_task(lease.run(function))
            await entered.wait()
            await cancel(requester)
            lease.close()
            with budget._lock:
                supervisors = list(budget._tasks)
            assert len(supervisors) == 1
            supervisors[0].cancel()  # asyncio.run shutdown does this too.
            await asyncio.gather(*supervisors, return_exceptions=True)
            if phase == 'running':
                assert budget.snapshot()['running'] == 1
                assert budget.acquire() is None
            else:
                assert budget.snapshot()['leases'] == 0 and not called
            gate.set()
        # Native exit is independently notified through the threading budget.
        await asyncio.to_thread(wait_empty, budget)
        assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)

    asyncio.run(scenario())


def wait_empty(budget):
    # A deterministic notification, not a polling/sleep ordering oracle.
    # Attaching a release observer is safe because this semaphore is thread-safe.
    assert budget.slots.acquire(timeout=10)
    budget.slots.release()


def test_one_lease_cannot_dispatch_parallel_native_operations():
    async def scenario():
        budget = WorkerBudget(1)
        lease = budget.acquire()
        barrier = Barrier(asyncio.get_running_loop())
        task = asyncio.create_task(lease.run(barrier.fault, 'authenticated', None))
        try:
            await barrier.wait()
            with pytest.raises(RuntimeError, match='already executing'):
                await lease.run(lambda: None)
            assert budget.snapshot()['running'] == 1
        finally:
            barrier.release.set()
            await task
            lease.close()
        assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)

    asyncio.run(scenario())


def test_cancelled_queued_worker_keeps_admission_bounded(db):
    manifest = observe(client(db)).json()

    async def scenario():
        rig = Rig(db, manifest, limit=1)
        entered, gate = asyncio.Event(), asyncio.Event()
        real = workers.run_in_threadpool
        submitted = []

        async def delayed(*args):
            submitted.append(True)
            entered.set()
            await gate.wait()  # Existing executor/limiter queue, not our queue.
            return await real(*args)

        messages = []
        with patch.object(workers, 'run_in_threadpool', delayed):
            task = asyncio.create_task(rig.invoke(messages))
            await entered.wait()
            assert rig.adapter.workers.snapshot()['jobs'] == 1
            for _ in range(8):
                busy = []
                await rig.invoke(busy)
                assert busy[0]['status'] == 503
            assert len(submitted) == 1
            await cancel(task)
            # No release of the artificial executor gate: this job never
            # starts, and must still leave the queue and restore capacity.
            await rig.drain()
        assert messages == []

    asyncio.run(scenario())


def test_cancel_while_real_anyio_executor_limiter_is_occupied(db):
    import anyio.to_thread

    manifest = observe(client(db)).json()

    async def scenario():
        rig = Rig(db, manifest, limit=1)
        entered = asyncio.Event()
        real = workers.run_in_threadpool
        tickets = []
        rig.adapter.fault = lambda stage, ticket: tickets.append(ticket)
        limiter = anyio.to_thread.current_default_thread_limiter()
        previous = limiter.total_tokens
        limiter.total_tokens = 1

        async def queued(*args):
            entered.set()
            return await real(*args)

        messages = []
        try:
            async with limiter:
                with patch.object(workers, 'run_in_threadpool', queued):
                    task = asyncio.create_task(rig.invoke(messages))
                    await entered.wait()
                    assert rig.adapter.workers.snapshot()['running'] == 0
                    await cancel(task)
                    await rig.drain()
                    assert limiter.borrowed_tokens == 1  # Only this test owns one.
            assert not tickets and messages == []
        finally:
            limiter.total_tokens = previous

    asyncio.run(scenario())


def test_cancel_before_native_start_never_authenticates_or_returns_success(db):
    manifest = observe(client(db)).json()

    async def scenario():
        rig = Rig(db, manifest, limit=1)
        entered, gate = asyncio.Event(), asyncio.Event()
        real = workers.run_in_threadpool
        tickets = []
        rig.adapter.fault = lambda stage, ticket: tickets.append(ticket)

        async def delayed(*args):
            entered.set()
            await gate.wait()
            return await real(*args)

        messages = []
        with patch.object(workers, 'run_in_threadpool', delayed):
            task = asyncio.create_task(rig.invoke(messages))
            await entered.wait()
            # A live requester with a separately signalled cancellation must
            # get a rejection, not a successful empty/no-change response.
            with rig.adapter.workers._lock:
                lease = next(iter(rig.adapter.workers._leases))
            lease.cancelled.set()
            gate.set()
            await task
            await rig.drain()
        assert not tickets and messages[0]['status'] == 403

    asyncio.run(scenario())


def test_native_exit_after_original_loop_closed_returns_capacity():
    budget = WorkerBudget(1)
    lease = budget.acquire()
    loop = asyncio.new_event_loop()
    entered, release = Event(), Event()

    def blocked():
        entered.set()
        assert release.wait(10)
        raise RuntimeError('synthetic exception after event loop shutdown')

    async def scenario():
        task = asyncio.create_task(lease.run(blocked))
        await asyncio.to_thread(entered.wait, 10)
        await cancel(task)
        lease.close()
        with budget._lock:
            supervisors = list(budget._tasks)
        for supervisor in supervisors:
            supervisor.cancel()
        await asyncio.gather(*supervisors, return_exceptions=True)
        assert budget.snapshot()['running'] == 1

    try:
        loop.run_until_complete(scenario())
        loop.close()
        assert budget.acquire() is None
    finally:
        release.set()
        wait_empty(budget)
        if not loop.is_closed():
            loop.close()
    assert budget.snapshot() == dict(leases=0, jobs=0, running=0, tasks=0)


def test_path_checkpoints_stop_cancelled_batch_before_next_object(db):
    from isolated_sync.transfer import PathResolver

    manifest = observe(client(db)).json()
    rig = Rig(db, manifest)
    inspected = []
    with db.connect() as conn:
        def checkpoint():
            inspected.append(True)
            if len(inspected) == 2:
                raise workers.PreparationCancelled()

        resolver = PathResolver(conn, rig.adapter.repo, manifest['target'], checkpoint)
        # Derive a real table-child edge from independent stored parent bytes.
        raw = conn.execute('SELECT body FROM sync_objects WHERE hash=?',
                           (manifest['target']['raw_ref']['hash'],)).fetchone()[0]
        child = json.loads(raw)['tables'][0]['root']['ref']['hash']
        with pytest.raises(workers.PreparationCancelled):
            resolver.resolve([manifest['target']['raw_ref']['hash'], child])
        assert resolver.reads == 1 and len(inspected) == 2


def test_shutdown_signals_handles_without_releasing_live_capacity(db):
    manifest = observe(client(db)).json()

    async def scenario():
        barrier = Barrier(asyncio.get_running_loop())
        rig = Rig(db, manifest, fault=barrier.fault, limit=1)
        messages = []
        async with rig.app.router.lifespan_context(rig.app):
            task = asyncio.create_task(rig.invoke(messages))
            await barrier.wait()
        assert barrier.tickets[0].cancelled.is_set()
        assert rig.adapter.workers.snapshot()['leases'] == 1
        assert rig.adapter.workers.acquire() is None
        try:
            await cancel(task)
        finally:
            barrier.release.set()
            await rig.drain()
        assert messages == []

    asyncio.run(scenario())


def test_bounded_cancellation_stress_never_overadmits_and_recovers(db):
    manifest = observe(client(db)).json()
    before = persisted(db)

    async def scenario():
        rig = Rig(db, manifest)
        maximum = 0
        cancelled_responses = []
        for wave in range(5):
            barrier = Barrier(asyncio.get_running_loop(), count=2, fail=bool(wave % 2))
            rig.adapter.fault = barrier.fault
            responses = [[], []]
            tasks = [asyncio.create_task(rig.invoke(m)) for m in responses]
            try:
                await barrier.wait(2)
                maximum = max(maximum, rig.adapter.workers.snapshot()['running'])
                await asyncio.gather(*(cancel(task) for task in tasks))
                for _ in range(4):
                    busy = []
                    await rig.invoke(busy)
                    assert busy[0]['status'] == 503
                assert len(barrier.tickets) == 2
                assert all(t.cancelled.is_set() for t in barrier.tickets)
                assert rig.adapter.workers.snapshot() == dict(leases=2, jobs=2, running=2, tasks=2)
            finally:
                barrier.release.set()
                await rig.drain()
            cancelled_responses.extend(responses)
            rig.adapter.fault = None
            good = []
            await rig.invoke(good)
            assert good[0]['status'] == 200
            await rig.drain()
        assert maximum == 2 and cancelled_responses == [[]]*10

    asyncio.run(scenario())
    assert persisted(db) == before
