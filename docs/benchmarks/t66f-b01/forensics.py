"""Opt-in pytest observer: original assertions and product code are untouched.

Only the synthetic transfer quota test is instrumented. No SQL parameters,
request headers, credentials or unrelated tests are recorded.
"""

from collections import Counter
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock, get_ident, local
from time import perf_counter_ns
import traceback
from unittest.mock import patch

import pytest


NAME = "test_bounded_concurrent_quota_and_same_request_status"


def pytest_addoption(parser):
    parser.addoption("--b01-output")
    parser.addoption("--b01-light", action="store_true")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    output = item.config.getoption("--b01-output")
    light = item.config.getoption("--b01-light")
    if not output or item.originalname != NAME:
        yield
        return
    from isolated_sync.http import Adapter
    from isolated_sync.observation import ObservationRepository
    from isolated_sync.observation_schema import (
        ObservationConnection,
        ObservationSandbox,
    )

    db = item.funcargs["db"]
    started, lock, context = perf_counter_ns(), Lock(), local()
    events, responses, statements, handles = [], [], Counter(), {}

    def connection_id(conn):
        # Keep a monotonic identity even when CPython reuses an object's id.
        with lock:
            if not hasattr(conn, "_b01_id"):
                conn._b01_id = len(handles) + 1
                handles[conn._b01_id] = dict(thread=get_ident(), closed=False)
            return conn._b01_id

    def record(event, **values):
        row = dict(
            event=event,
            us=(perf_counter_ns() - started) // 1000,
            pid=os.getpid(),
            thread=get_ident(),
            request_id=getattr(context, "request_id", None),
            phase=getattr(context, "phase", None),
            **values,
        )
        with lock:
            events.append(row)

    def error_values(error):
        chain, cause = [], error
        while cause is not None and len(chain) < 4:
            chain.append(
                dict(
                    error_type=type(cause).__name__,
                    code=getattr(cause, "code", None),
                    sqlite_errorcode=getattr(cause, "sqlite_errorcode", None),
                    sqlite_errorname=getattr(cause, "sqlite_errorname", None),
                    message=str(cause) if isinstance(cause, sqlite3.Error) else None,
                    frames=[
                        dict(
                            file=Path(frame.filename).name,
                            line=frame.lineno,
                            function=frame.name,
                        )
                        for frame in traceback.extract_tb(cause.__traceback__)
                    ],
                )
            )
            cause = cause.__cause__ or cause.__context__
        return dict(
            error_type=type(error).__name__,
            code=getattr(error, "code", None),
            sqlite_errorcode=getattr(error, "sqlite_errorcode", None),
            sqlite_errorname=getattr(error, "sqlite_errorname", None),
            message=str(error) if isinstance(error, sqlite3.Error) else None,
            exception_chain=chain,
        )

    execute = ObservationConnection.execute

    def traced_execute(conn, sql, parameters=()):
        identity = connection_id(conn)
        key = " ".join(sql.split())
        command = key.upper()
        boundary = command.startswith(
            (
                "BEGIN",
                "COMMIT",
                "ROLLBACK",
                "SAVEPOINT",
                "RELEASE",
                "PRAGMA BUSY_TIMEOUT",
            )
        )
        with lock:
            statements[key] += 1
        mark = perf_counter_ns()
        if boundary:
            record("sql_begin", connection=identity, sql=key)
        try:
            result = execute(conn, sql, parameters)
        except BaseException as error:
            record(
                "sql_error",
                connection=identity,
                sql=key,
                elapsed_us=(perf_counter_ns() - mark) // 1000,
                **error_values(error),
            )
            raise
        if boundary:
            record(
                "sql_end",
                connection=identity,
                sql=key,
                elapsed_us=(perf_counter_ns() - mark) // 1000,
            )
        return result

    connect = ObservationSandbox.connect

    def traced_connect(sandbox):
        mark = perf_counter_ns()
        record("connect_begin")
        try:
            conn = connect(sandbox)
        except BaseException as error:
            record(
                "connect_error",
                elapsed_us=(perf_counter_ns() - mark) // 1000,
                **error_values(error),
            )
            raise
        identity = connection_id(conn)
        record(
            "connect_end",
            connection=identity,
            elapsed_us=(perf_counter_ns() - mark) // 1000,
        )
        conn.set_trace_callback(
            lambda sql: (
                record("sqlite_trace", connection=identity, sql=sql)
                if sql.upper() in ("COMMIT", "ROLLBACK", "BEGIN IMMEDIATE")
                else None
            )
        )
        return conn

    def connection_action(name):
        original = getattr(ObservationConnection, name)

        def invoke(conn, *args):
            identity = connection_id(conn)
            # CaptureConnection.__exit__ already closes; the repository finally
            # deliberately closes again. sqlite3.close() is idempotent, whereas
            # reading in_transaction on that closed handle is not.
            try:
                in_transaction = conn.in_transaction
            except sqlite3.ProgrammingError:
                in_transaction = None
            record(name + "_begin", connection=identity, in_transaction=in_transaction)
            try:
                return original(conn, *args)
            except BaseException as error:
                record(name + "_error", connection=identity, **error_values(error))
                raise
            finally:
                if name == "close":
                    with lock:
                        handles[identity]["closed"] = True
                record(name + "_end", connection=identity)

        return invoke

    def phase_method(cls, name):
        original = getattr(cls, name)

        def invoke(self, *args, **kwargs):
            prior = getattr(context, "phase", None)
            context.phase = name
            if name == "prepare":
                context.request_id = args[1]["request_id"]
            elif name == "terminal":
                context.request_id = args[0].request_id
            record(name + "_begin")
            try:
                return original(self, *args, **kwargs)
            except BaseException as error:
                record(name + "_error", **error_values(error))
                raise
            finally:
                record(name + "_end")
                context.phase = prior

        return invoke

    observe = item.module.observe

    def traced_observe(client, *args, **kwargs):
        mark = perf_counter_ns()
        response = observe(client, *args, **kwargs)
        parsed = response.json()
        row = dict(
            method="POST",
            endpoint=item.module.URL,
            status=response.status_code,
            body=parsed,
            headers={
                k: response.headers[k]
                for k in ("content-type", "cache-control", "x-content-type-options")
                if k in response.headers
            },
            elapsed_us=(perf_counter_ns() - mark) // 1000,
            completed=True,
        )
        with lock:
            responses.append(row)
        record(
            "http_response",
            status=response.status_code,
            response_request_id=parsed.get("request_id"),
        )
        return response

    with ExitStack() as patches:
        if not light:
            patches.enter_context(
                patch.object(ObservationConnection, "execute", traced_execute)
            )
            patches.enter_context(
                patch.object(ObservationSandbox, "connect", traced_connect)
            )
            for name in ("commit", "rollback", "close"):
                patches.enter_context(
                    patch.object(ObservationConnection, name, connection_action(name))
                )
        for cls, name in (
            (Adapter, "prepare"),
            (Adapter, "terminal"),
            (ObservationRepository, "create"),
            (ObservationRepository, "lookup"),
        ):
            patches.enter_context(patch.object(cls, name, phase_method(cls, name)))
        patches.enter_context(patch.object(item.module, "observe", traced_observe))
        outcome = yield

    with sqlite3.connect(db.path) as conn:
        persisted = dict(
            observations=conn.execute(
                "SELECT request_id,status,principal_id FROM sync_observations ORDER BY request_id"
            ).fetchall(),
            pins=conn.execute(
                "SELECT role,active,count(*) FROM sync_observation_pins GROUP BY role,active ORDER BY role,active"
            ).fetchall(),
            journal_mode=conn.execute("PRAGMA journal_mode").fetchone()[0],
            integrity=conn.execute("PRAGMA integrity_check").fetchone()[0],
            foreign_key_check=conn.execute("PRAGMA foreign_key_check").fetchall(),
        )
    stat = Path(db.path).stat()
    data = dict(
        test=item.nodeid,
        assertion_failed=outcome.excinfo is not None,
        elapsed_us=(perf_counter_ns() - started) // 1000,
        database_identity=dict(device=stat.st_dev, inode=stat.st_ino),
        events=events,
        responses=responses,
        handles=handles,
        statements=dict(sorted(statements.items())),
        persisted=persisted,
        original_test_sha256=hashlib.sha256(
            Path(item.module.__file__).read_bytes()
        ).hexdigest(),
        observer_mode="response_exception_only" if light else "sql_timeline",
        observer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    )
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
