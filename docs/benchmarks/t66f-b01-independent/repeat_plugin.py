"""원 quota 함수를 그대로 실행하면서 별도 HTTP/SQLite oracle를 기록한다."""

from contextlib import closing
import gc
import hashlib
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import patch

import pytest

from observer import Observer, database_fds


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    if item.name != "test_bounded_concurrent_quota_and_same_request_status":
        return (yield)
    db = item.funcargs["db"]
    item._b01_path = str(db.path)
    native_before = database_fds(db.path)
    source = item.module.observe
    passed, cleanup_error = False, None
    observed = Observer()

    def capture(client, *args, **kwargs):
        return observed.capture(source(client, *args, **kwargs))

    try:
        with observed, patch.object(item.module, "observe", capture):
            result = yield
            passed = True
            try:
                observed.permits_free(8)
            except BaseException as error:
                cleanup_error = repr(error)
                raise
            return result
    finally:
        with closing(sqlite3.connect(db.path)) as connection:
            state = dict(
                available=connection.execute(
                    "SELECT count(*) FROM sync_observations WHERE status='available'"
                ).fetchone()[0],
                pins=connection.execute(
                    "SELECT count(*) FROM sync_observation_pins"
                ).fetchone()[0],
                request_ids=[
                    r[0]
                    for r in connection.execute(
                        "SELECT request_id FROM sync_observations ORDER BY request_id"
                    )
                ],
                journal_mode=connection.execute("PRAGMA journal_mode").fetchone()[0],
                integrity=connection.execute("PRAGMA integrity_check").fetchone()[0],
                foreign_keys=connection.execute("PRAGMA foreign_key_check").fetchall(),
            )
        value = dict(
            test=item.nodeid,
            assertion_passed=passed,
            cleanup_error=cleanup_error,
            source_sha256=hashlib.sha256(
                Path(item.module.__file__).read_bytes()
            ).hexdigest(),
            native_fd_before=native_before,
            native_fd_after=database_fds(db.path),
            durable=state,
            **observed.result(),
        )
        Path(os.environ["B01_REPEAT_RECORD"]).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item, nextitem):
    result = yield
    if hasattr(item, "_b01_path"):
        path = Path(os.environ["B01_REPEAT_RECORD"])
        value = json.loads(path.read_text())
        value["native_fd_after_fixture_teardown"] = database_fds(item._b01_path)
        value["database_path_exists_after_teardown"] = Path(item._b01_path).exists()
        value["gc_objects_collected_after_teardown"] = gc.collect()
        value["native_fd_after_explicit_gc"] = database_fds(item._b01_path)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    return result
