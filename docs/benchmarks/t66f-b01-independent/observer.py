"""새 B01 관측기: 원 SQL/반환/timeout을 바꾸지 않는 test-only delegate."""

from collections import Counter
from contextlib import ExitStack
import json
import os
from pathlib import Path
import sqlite3
from threading import Event, Lock, local, get_ident
from time import perf_counter_ns
from unittest.mock import patch

from isolated_sync import http
from isolated_sync.observation_schema import ObservationConnection, ObservationSandbox
from isolated_sync.workers import NativeJob, WorkerLease


class Observer:
    def __init__(self):
        self.start = perf_counter_ns()
        self.lock, self.context = Lock(), local()
        self.handles, self.events, self.responses, self.adapters = {}, [], [], []
        self.counts = Counter()
        self.native_begin, self.native_finished = {}, Event()

    def record(self, event, **data):
        with self.lock:
            self.events.append(
                dict(
                    us=(perf_counter_ns() - self.start) // 1000,
                    event=event,
                    thread=get_ident(),
                    request=getattr(self.context, "request", None),
                    **data,
                )
            )

    def identity(self, connection):
        with self.lock:
            if connection not in self.handles:
                self.handles[connection] = dict(id=len(self.handles) + 1, closed=False)
            return self.handles[connection]["id"]

    def capture(self, response):
        try:
            body = response.json()
        except ValueError:
            body = {"unparsed_bytes": len(response.content)}
        row = dict(
            status=response.status_code,
            body=body,
            headers={
                k: response.headers[k]
                for k in ["content-type", "cache-control", "x-content-type-options"]
                if k in response.headers
            },
        )
        with self.lock:
            self.responses.append(row)
        self.record(
            "http_response",
            status=response.status_code,
            request_id=body.get("request_id"),
        )
        return response

    def __enter__(self):
        self.stack = ExitStack()
        execute, connect, close = (
            ObservationConnection.execute,
            ObservationSandbox.connect,
            ObservationConnection.close,
        )
        adapter_class, finish, lease_close = (
            http.Adapter,
            NativeJob._finish,
            WorkerLease.close,
        )
        observer = self

        def traced_execute(conn, sql, parameters=()):
            cid = observer.identity(conn)
            verb = sql.lstrip().split()[0].upper()
            with observer.lock:
                observer.counts[verb] += 1
            boundary = verb in {
                "BEGIN",
                "COMMIT",
                "ROLLBACK",
                "SAVEPOINT",
                "RELEASE",
            } or sql.upper().startswith("PRAGMA BUSY_TIMEOUT")
            began = perf_counter_ns()
            if boundary:
                observer.record("execute_enter", connection=cid, sql=sql)
            try:
                result = execute(conn, sql, parameters)
            except BaseException as exc:
                observer.record(
                    "execute_error",
                    connection=cid,
                    sql=sql if boundary else verb,
                    sqlite_code=getattr(exc, "sqlite_errorcode", None),
                    sqlite_name=getattr(exc, "sqlite_errorname", None),
                    error_type=type(exc).__name__,
                    message=str(exc) if isinstance(exc, sqlite3.Error) else None,
                    elapsed_us=(perf_counter_ns() - began) // 1000,
                )
                raise
            if boundary:
                observer.record(
                    "execute_return",
                    connection=cid,
                    sql=sql,
                    elapsed_us=(perf_counter_ns() - began) // 1000,
                )
            return result

        def traced_connect(sandbox):
            conn = connect(sandbox)
            cid = observer.identity(conn)
            observer.record("connect_return", connection=cid)

            def trace(sql):
                if sql.upper() in {"BEGIN IMMEDIATE", "COMMIT", "ROLLBACK"}:
                    observer.record("sqlite_trace", connection=cid, sql=sql)
                    if sql.upper() == "BEGIN IMMEDIATE":
                        event = observer.native_begin.get(
                            getattr(observer.context, "request", None)
                        )
                        if event:
                            event.set()

            conn.set_trace_callback(trace)
            return conn

        def traced_close(conn):
            cid = observer.identity(conn)
            result = close(conn)
            with observer.lock:
                observer.handles[conn]["closed"] = True
            observer.record("close_return", connection=cid)
            return result

        def phase(name):
            original = getattr(adapter_class, name)

            def invoke(adapter, *args, **kwargs):
                prior = getattr(observer.context, "request", None)
                observer.context.request = (
                    args[1]["request_id"] if name == "prepare" else args[0].request_id
                )
                observer.record(name + "_enter")
                try:
                    return original(adapter, *args, **kwargs)
                finally:
                    observer.record(name + "_exit")
                    observer.context.request = prior

            return invoke

        def adapter(*args, **kwargs):
            value = adapter_class(*args, **kwargs)
            observer.adapters.append(value)
            return value

        def finished(job):
            result = finish(job)
            if job.lease._closed and not job.lease._jobs:
                observer.record("native_finished_after_requester_close")
                observer.native_finished.set()
            return result

        def closed(lease):
            observer.record("lease_close_enter", native_jobs=len(lease._jobs))
            result = lease_close(lease)
            observer.record("lease_close_return", native_jobs=len(lease._jobs))
            return result

        for cls, name, function in [
            (ObservationConnection, "execute", traced_execute),
            (ObservationConnection, "close", traced_close),
            (ObservationSandbox, "connect", traced_connect),
            (adapter_class, "prepare", phase("prepare")),
            (adapter_class, "terminal", phase("terminal")),
            (NativeJob, "_finish", finished),
            (WorkerLease, "close", closed),
            (http, "Adapter", adapter),
        ]:
            self.stack.enter_context(patch.object(cls, name, function))
        return self

    def __exit__(self, *args):
        return self.stack.__exit__(*args)

    def permits_free(self, capacity):
        evidence = []
        for adapter in self.adapters:
            before = adapter.workers.snapshot()
            assert before == dict(leases=0, jobs=0, running=0, tasks=0), before
            leases = [adapter.workers.acquire() for _ in range(capacity)]
            assert all(lease is not None for lease in leases)
            assert adapter.workers.acquire() is None
            for lease in leases:
                lease.close()
            evidence.append(before)
        return evidence

    def result(self):
        return dict(
            events=self.events,
            responses=self.responses,
            handles=list(self.handles.values()),
            execute_calls=sum(self.counts.values()),
            select_calls=self.counts["SELECT"],
            statements=dict(self.counts),
        )


def database_fds(path):
    prefix = str(Path(path).resolve())
    found = []
    for fd in Path("/proc/self/fd").iterdir():
        try:
            target = os.readlink(fd)
        except OSError:
            continue
        if target.removesuffix(" (deleted)") in {
            prefix,
            prefix + "-wal",
            prefix + "-shm",
        }:
            found.append({"fd": int(fd.name), "target": target})
    return found


def save(name, record):
    out = Path(
        os.environ.get("B01_INDEPENDENT_OUTPUT", "/tmp/mn-t66f-b01-independent/cases")
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / (name + ".json")).write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    )
