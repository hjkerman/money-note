"""B01 원 단언은 그대로 두고 해당 full-suite case의 status/body만 보존한다."""

import json
from pathlib import Path
import threading
import time
from unittest.mock import patch
import pytest

HERE = Path(__file__).resolve().parent


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    if item.name != "test_bounded_concurrent_quota_and_same_request_status":
        yield
        return
    from starlette.testclient import TestClient
    from isolated_sync.observation_schema import ObservationConnection

    original_post, original_execute = TestClient.post, ObservationConnection.execute
    rows, sql, lock = [], [], threading.Lock()

    def post(self, *args, **kwargs):
        started = time.monotonic_ns()
        response = original_post(self, *args, **kwargs)
        with lock:
            rows.append(
                {
                    "start_ns": started,
                    "end_ns": time.monotonic_ns(),
                    "status": response.status_code,
                    "body": response.json(),
                }
            )
        return response

    def execute(self, statement, *args, **kwargs):
        started = time.monotonic_ns()
        try:
            return original_execute(self, statement, *args, **kwargs)
        finally:
            kind = str(statement).lstrip().split()[0].upper()
            if kind in {"BEGIN", "COMMIT", "ROLLBACK", "PRAGMA"}:
                with lock:
                    sql.append(
                        {
                            "connection": id(self),
                            "thread": threading.get_ident(),
                            "operation": str(statement)[:160],
                            "start_ns": started,
                            "end_ns": time.monotonic_ns(),
                        }
                    )

    with (
        patch.object(TestClient, "post", post),
        patch.object(ObservationConnection, "execute", execute),
    ):
        yield
    (HERE / "full-b01-responses.json").write_text(
        json.dumps({"responses": rows, "sql": sql}, ensure_ascii=False, indent=2) + "\n"
    )
