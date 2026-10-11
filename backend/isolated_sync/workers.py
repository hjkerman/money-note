"""Bounded native-operation ownership, independent of an ASGI task's lifetime.

No executor of our own and no admission queue. A cancelled requester signals
its operation but cannot return capacity still occupied by a native worker.
The threading semaphore can safely be released by the native completion path,
including when its original event loop is no longer running.
"""

import asyncio
from threading import BoundedSemaphore, Event, Lock

from starlette.concurrency import run_in_threadpool


class PreparationCancelled(RuntimeError):
    """A cancelled admitted operation never became a prepared response."""


class WorkerBudget:
    def __init__(self, limit):
        self.slots = BoundedSemaphore(limit)
        self._lock = Lock()
        self._leases = set()
        self._tasks = set()
        self._stopped = False

    def acquire(self):
        with self._lock:
            if self._stopped or not self.slots.acquire(blocking=False):
                return None
            lease = WorkerLease(self)
            self._leases.add(lease)
            return lease

    def shutdown(self):
        # Non-blocking: a stuck worker still owns capacity. Never interrupt a
        # SQLite connection, cancel a shared executor or release a live lease.
        with self._lock:
            self._stopped = True
            leases = list(self._leases)
        for lease in leases:
            lease.cancel()

    def snapshot(self):
        """Bounded synthetic diagnostics; no credential/ticket content."""
        with self._lock:
            jobs = [job for lease in self._leases for job in lease._jobs]
            return dict(leases=len(self._leases), jobs=len(jobs),
                        running=sum(job.started for job in jobs), tasks=len(self._tasks))


class WorkerLease:
    def __init__(self, budget):
        self.budget = budget
        self.cancelled = Event()  # Exists BEFORE dispatch/auth/ticket creation.
        self._closed = False
        self._jobs = set()

    def _release_if_finished(self):
        # Caller holds the budget lock. Removal is the exact-once release gate.
        if self._closed and not self._jobs and self in self.budget._leases:
            self.budget._leases.remove(self)
            self.budget.slots.release()

    def close(self):
        self.cancel()
        with self.budget._lock:
            self._closed = True
            self._release_if_finished()

    def cancel(self):
        self.cancelled.set()
        with self.budget._lock:
            pending = [job for job in self._jobs if not job.started and job.task is not None]
        for job in pending:
            try:
                # Queued supervisors must leave the shared executor limiter.
                # If native start races this cancellation, settled() sees it
                # and leaves completion/permit ownership to invoke().
                job.task.get_loop().call_soon_threadsafe(job.task.cancel)
            except RuntimeError:
                # A closed loop cannot start new work or run done callbacks.
                # Atomically prohibit a late native start before dropping it.
                with self.budget._lock:
                    if not job.started:
                        self.budget._tasks.discard(job.task)
                        job._finish()

    async def run(self, function, *args):
        job = NativeJob(self)
        with self.budget._lock:
            if self._closed:
                raise RuntimeError("closed worker lease")
            if self._jobs:
                raise RuntimeError("worker lease already executing")
            self._jobs.add(job)
        coroutine = None
        try:
            coroutine = run_in_threadpool(job.invoke, function, args)
            task = asyncio.create_task(coroutine)
        except BaseException:
            if coroutine is not None:
                coroutine.close()
            job.settled(None)  # Submission failed; no worker owns this job.
            raise
        with self.budget._lock:
            job.task = task
            self.budget._tasks.add(task)  # Strong reference until settled.
        task.add_done_callback(job.settled)
        # Shield preserves the supervisor on requester cancellation. It does
        # NOT own the permit: only native exit (or proven non-start) completes
        # a job. This also handles event-loop shutdown cancelling supervisors.
        return await asyncio.shield(task)


class NativeJob:
    def __init__(self, lease):
        self.lease = lease
        self.started = self.finished = False
        self.task = None

    def invoke(self, function, args):
        with self.lease.budget._lock:
            if self.finished:  # A cancelled queued supervisor cannot start late.
                return None
            self.started = True
        try:
            if self.lease.cancelled.is_set():
                raise PreparationCancelled()
            return function(*args)
        finally:
            # All function-level SQLite rollback/close/finally blocks have run.
            with self.lease.budget._lock:
                self._finish()

    def _finish(self):
        if not self.finished:
            self.finished = True
            self.lease._jobs.discard(self)
            self.lease._release_if_finished()

    def settled(self, task):
        if task is not None:
            try:
                task.exception()  # Observe errors even after requester exited.
            except asyncio.CancelledError:
                pass
        with self.lease.budget._lock:
            self.lease.budget._tasks.discard(task)
            if not self.started:
                self._finish()
