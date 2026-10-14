"""새 synthetic fixture와 외부 SQLite oracle로 E3/I25를 독립 검증한다."""

from contextlib import contextmanager
from collections import Counter
import copy
import base64
import hashlib
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import sqlite3
import subprocess
import tarfile
import time
from uuid import uuid4

import pytest

from oracle import c1, facts, graph, h, patricia, persisted

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(os.environ.get("E3_AUDIT_OUTPUT", "/tmp/mn-e3-audit/independent"))


def read_json(process, timeout=180):
    with selectors.DefaultSelector() as selector:
        selector.register(process.stdout, selectors.EVENT_READ)
        assert selector.select(timeout), "worker 응답 상한 초과"
        line = process.stdout.readline()
    assert line, "worker가 예상 없이 종료됨"
    return json.loads(line)


@pytest.fixture(scope="session")
def corpus(tmp_path_factory):
    reuse = os.environ.get("E3_AUDIT_CORPUS")
    if reuse:
        result = {}
        for history in (4, 400):
            paths = [
                Path(reuse) / f"{history}-{n}.json"
                for n in range(6)
                if (Path(reuse) / f"{history}-{n}.json").exists()
            ]
            fixtures = [json.loads(p.read_text()) for p in paths]
            for fixture in fixtures:
                _, rows, _ = graph(fixture)
                assert (
                    patricia(
                        fixture["manifest"]["target"],
                        facts(fixture["manifest"]["target"], rows),
                    )
                    == fixture["manifest"]["target"]["index_ref"]
                )
            result[history] = (fixtures, paths)
        return result
    root = tmp_path_factory.mktemp("e3-independent-corpus")
    result = {}
    for history in (4, 400):
        process = subprocess.Popen(
            [
                str(ROOT / ".venv/bin/python"),
                str(ROOT / "scripts/benchmarks/t66e2_server.py"),
                str(history),
            ],
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        first = read_json(process)
        token = first["token"]
        fixtures = [first["fixture"]]

        def command(value):
            process.stdin.write(json.dumps(value) + "\n")
            process.stdin.flush()
            return read_json(process)

        try:
            for operation in (
                "mutate",
                "insert_history",
                "delete_history",
                "mutate",
                "mutate",
            ):
                command({"command": operation, "count": 96})
                response = command(
                    {
                        "command": "http",
                        "method": "POST",
                        "path": "/api/sync/v1/observations",
                        "headers": {
                            "Authorization": "Bearer " + token,
                            "Content-Type": "application/json",
                        },
                        "body_base64": base64.b64encode(
                            c1(
                                {
                                    "protocol": 1,
                                    "request_id": str(uuid4()),
                                    "base": None,
                                    "inline_bytes": 0,
                                }
                            )
                        ).decode(),
                    }
                )
                assert response["status"] == 201
                fixture = command({"command": "oracle"})
                fixtures.append(fixture)
                command(
                    {
                        "command": "http",
                        "method": "DELETE",
                        "path": "/api/sync/v1/observations/"
                        + fixture["manifest"]["observation_id"],
                        "headers": {"Authorization": "Bearer " + token},
                    }
                )
            paths = []
            for n, fixture in enumerate(fixtures):
                _, rows, _ = graph(fixture)
                assert (
                    patricia(
                        fixture["manifest"]["target"],
                        facts(fixture["manifest"]["target"], rows),
                    )
                    == fixture["manifest"]["target"]["index_ref"]
                )
                path = root / f"{history}-{n}.json"
                path.write_bytes(c1(fixture))
                paths.append(path)
            result[history] = (fixtures, paths)
        finally:
            command({"command": "exit"})
            process.communicate(timeout=10)
            assert process.returncode == 0
    return result


@pytest.fixture(scope="session")
def copied_package(tmp_path_factory):
    root = tmp_path_factory.mktemp("e3-instrumented-copy")
    mobile = root / "mobile"
    shutil.copytree(ROOT / "mobile/lib", mobile / "lib")
    store = mobile / "lib/src/segmented/store.dart"
    source = store.read_text()
    assert source.count("db = sqlite3.open(path);") == 1
    store.write_text(
        source.replace(
            "import 'work.dart';", "import 'work.dart';\nimport 'audit_trace.dart';"
        ).replace("db = sqlite3.open(path);", "db = AuditDatabase(sqlite3.open(path));")
    )
    shutil.copyfile(
        HERE / "audit_trace.dart", mobile / "lib/src/segmented/audit_trace.dart"
    )
    original = ROOT / "mobile/.dart_tool/package_config.json"
    config = json.loads(original.read_text())
    for package in config["packages"]:
        uri = package["rootUri"]
        if ":" not in uri:
            package["rootUri"] = (original.parent / uri).resolve().as_uri() + "/"
        if package["name"] == "money_note_mobile":
            package["rootUri"] = mobile.as_uri() + "/"
    location = mobile / ".dart_tool/package_config.json"
    location.parent.mkdir()
    location.write_text(json.dumps(config))
    shutil.copyfile(
        original.with_name("native_assets.yaml"),
        location.with_name("native_assets.yaml"),
    )
    return location


@contextmanager
def worker(tmp_path, paths, config, root=None):
    root = root or tmp_path / "store"
    job = tmp_path / (str(uuid4()) + ".json")
    job.write_text(json.dumps({"fixtures": [str(p) for p in paths], "root": str(root)}))
    errors = (tmp_path / (str(uuid4()) + ".log")).open("w")
    process = subprocess.Popen(
        [
            "/home/hjkerman/.flutter/bin/dart",
            "--packages=" + str(config),
            str(HERE / "probe.dart"),
            str(job),
        ],
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=errors,
        text=True,
        bufsize=1,
    )
    ready = read_json(process)
    path = ready["path"]

    def command(**value):
        process.stdin.write(json.dumps(value) + "\n")
        process.stdin.flush()
        return read_json(process)

    try:
        yield command, path, process, root
    finally:
        if process.poll() is None:
            process.stdin.write('{"action":"exit"}\n')
            process.stdin.flush()
            try:
                process.wait(10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(5)
        errors.close()
        assert process.returncode in (0, -signal.SIGKILL)


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / (name + ".json")).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )


def totals(events):
    fields = (
        "pin_insert",
        "pin_delete",
        "pin_update",
        "rows_returned",
        "body_bytes_read",
        "raw_rows_read",
        "raw_objects_read",
        "index_objects_read",
    )
    return {
        "sql_statements": len(events),
        "object_body_reads": sum(len(e.get("object_identities", [])) for e in events),
        "unique_objects_read": len(
            {identity for e in events for identity in e.get("object_identities", [])}
        ),
        **{f: sum(e.get(f, 0) for e in events) for f in fields},
    }


@pytest.mark.parametrize("history", [4, 400])
def test_independent_sql_cost_diff_and_retained_graph(
    tmp_path, corpus, copied_package, history
):
    fixtures, paths = corpus[history]
    records = []
    previous = None
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        schedule = [
            ("cold", 0),
            ("identical", 0),
            ("single-change", 1),
            ("identical-after-change", 1),
            ("structural-insert", 2),
            ("structural-delete", 3),
            ("identical-again", 3),
        ]
        if len(fixtures) > 4:
            schedule.extend(
                [
                    ("repeated-small-1", 4),
                    ("repeated-small-2", 5),
                    ("identical-after-repeated", 5),
                ]
            )
        latest = len(fixtures) - 1
        schedule.extend(
            [
                ("guard-fails", latest),
                ("retry", latest),
                ("reopen", latest),
                ("after-reopen", latest),
            ]
        )
        for label, target in schedule:
            result = command(action=label, target=target)
            events = result.pop("events")
            record = dict(
                scenario=label,
                **totals(events),
                phases={
                    phase: totals([e for e in events if e["phase"] == phase])
                    for phase in {e["phase"] for e in events}
                },
                latency_us=result["latency_us"],
                publication_transactions_us=[
                    e["transaction_us"]
                    for e in events
                    if e.get("transaction_us") is not None
                    and e["phase"] == "publication"
                ],
                sql_histogram=dict(Counter(e["sql"] for e in events)),
            )
            if label == "guard-fails":
                assert (
                    not result["ok"]
                    and result["error"] == "SegmentedException(AUDIT_GUARD)"
                )
            else:
                assert result["ok"], result
                expected, rows, _ = graph(fixtures[target])
                assert set(result.pop("graph_hashes")) == expected
                old_set = set() if previous is None else graph(fixtures[previous])[0]
                record.update(
                    changed_objects=len(expected - old_set),
                    reused_objects=len(expected & old_set),
                    removed_objects=len(old_set - expected),
                )
                if previous is not None:
                    _, old_rows, _ = graph(fixtures[previous])
                    expected_diff = {
                        (table, c1(r["key"])): (r["value"], None)
                        for table in old_rows
                        for r in old_rows[table]
                    }
                    for table, items in rows.items():
                        for r in items:
                            ident = (table, c1(r["key"]))
                            old = expected_diff.get(ident, (None, None))[0]
                            expected_diff[ident] = (old, r["value"])
                    expected_diff = {
                        k: v for k, v in expected_diff.items() if c1(v[0]) != c1(v[1])
                    }
                    actual_diff = {
                        (c["table"], c1(c["key"])): (c["before"], c["after"])
                        for c in result["changed"]
                    }
                    assert actual_diff == expected_diff
                previous = target
                if label.startswith("identical") or label == "after-reopen":
                    assert result["object_requests"] == 0
                    # byte 비용은 bounded leaf/H에 의존한다. 임의 100KB 상한을 규범으로 만들지 않는다.
                    assert record["raw_objects_read"] <= 8
                    assert record["index_objects_read"] <= 4
                    assert record["pin_insert"] == 4 and record["pin_update"] == 0
                    assert not any("WITH RECURSIVE closure" in e["sql"] for e in events)
                if label == "single-change" or label.startswith("repeated-small"):
                    assert len(result["changed"]) == 1 and record["pin_insert"] == 4
                record.update(
                    target=result["target"],
                    object_requests=result["object_requests"],
                    payload_bytes=result["payload_bytes"],
                    changed_rows=len(result["changed"]),
                    graph_objects=len(expected),
                )
            record["persisted"] = persisted(path, fixtures)
            assert record["persisted"]["root_pin_rows"] <= 12
            records.append(record)
        save("cost-" + str(history), records)


def variant(original, kind):
    value = copy.deepcopy(original)
    objects = {
        o["ref"]["hash"]: base64.b64decode(o["data_base64"]) for o in value["objects"]
    }
    rebuilt = {}
    mapped = {}
    edited = False

    def visit(ref):
        nonlocal edited
        if ref["hash"] in mapped:
            return mapped[ref["hash"]]
        body = json.loads(objects[ref["hash"]])
        k = body["kind"]
        if k == "raw-root":
            for t in body["tables"]:
                t["root"]["ref"] = visit(t["root"]["ref"])
        elif k == "snapshot-node":
            for d in body["children"]:
                d["ref"] = visit(d["ref"])
        elif k == "index-root":
            body["facts"] = visit(body["facts"])
        elif k == "index-node":
            for side in ("left", "right"):
                body[side] = visit(body[side])
        if not edited:
            if kind == "index-value" and k == "index-leaf":
                body["facts"][0]["value"] = "독립 잘못된 fact"
                edited = True
            elif (
                kind == "stale-index"
                and k == "snapshot-leaf"
                and body["table"] == "ledger_entries"
                and body["rows"]
            ):
                body["rows"][0]["value"]["title"] = "독립 raw 변경"
                edited = True
            elif kind == "hot-money" and k == "hot":
                body["state"]["settings"]["scheduled_income"] = "123"
                edited = True
            elif kind == "hot-extra" and k == "hot":
                row = copy.deepcopy(body["state"]["entries"][0])
                row["id"] = 900000
                body["state"]["entries"].append(row)
                edited = True
            elif kind == "hot-context" and k == "hot":
                body["context"]["evaluation_date"] = "2026-10-01"
                edited = True
            elif kind == "unsupported" and k == "hot":
                body["canon"] = 2
                edited = True
            elif kind == "child-bytes" and k == "raw-root":
                body["tables"][0]["root"]["ref"]["bytes"] = str(
                    int(body["tables"][0]["root"]["ref"]["bytes"]) + 1
                )
                edited = True
            elif kind in ("missing-new", "malformed-new") and k == "hot":
                body["state"]["judgment"]["message"] = "새 독립 반례"
                edited = True
        raw = c1(body)
        new = dict(hash=h(k, raw), bytes=str(len(raw)))
        rebuilt[new["hash"]] = raw
        mapped[ref["hash"]] = new
        return new

    target = value["manifest"]["target"]
    target.pop("sync_root")
    target["revision"] = str(int(target["revision"]) + 1)
    for role in ("raw", "index", "hot", "control"):
        target[role + "_ref"] = visit(target[role + "_ref"])
    if kind == "wrong-epoch":
        target["ns"]["epoch"] = str(uuid4())
    elif kind == "wrong-principal":
        target["principal_id"] += 1
    elif kind == "stale-revision":
        target["revision"] = "0"
    target["sync_root"] = h("view", c1(target))
    hot = target["hot_ref"]["hash"]
    if kind == "missing-new":
        rebuilt.pop(hot)
    if kind == "malformed-new":
        rebuilt[hot] = rebuilt[hot][:-1] + b" "
    value["objects"] = [
        dict(
            ref=dict(hash=k, bytes=str(len(v))),
            data_base64=base64.b64encode(v).decode(),
        )
        for k, v in rebuilt.items()
    ]
    return value


@pytest.mark.parametrize(
    "kind",
    [
        "index-value",
        "stale-index",
        "hot-money",
        "hot-extra",
        "hot-context",
        "unsupported",
        "child-bytes",
        "missing-new",
        "malformed-new",
        "wrong-epoch",
        "wrong-principal",
        "stale-revision",
    ],
)
def test_complete_and_incremental_reject_independent_invalid_targets(
    tmp_path, corpus, copied_package, kind
):
    fixtures, paths = corpus[4]
    changed = variant(fixtures[0], kind)
    file = tmp_path / "variant.json"
    file.write_bytes(c1(changed))
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        before = persisted(path, fixtures)
        result = command(action="verify-variant", fixture=str(file))
        assert (
            not result["full"]["accepted"] and not result["incremental"]["accepted"]
        ), result
        assert persisted(path, fixtures) == before
        save("invalid-" + kind, result)


@pytest.mark.parametrize("failure", ["fault-before", "fault-after", "guard-fails"])
def test_rollback_vs_committed_error_and_fresh_recovery(
    tmp_path, corpus, copied_package, failure
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        result = command(action=failure, target=1)
        assert not result["ok"]
        state = persisted(path, fixtures)
        assert state["pointer"]["sequence"] == (2 if failure == "fault-after" else 1)
        assert result["committed_error"] == (failure == "fault-after")
        assert command(action="reopen-only")["ok"]
        save(
            failure,
            dict(
                outcome={k: v for k, v in result.items() if k != "events"},
                persisted=state,
            ),
        )


def test_concurrent_stale_base_cannot_commit(tmp_path, corpus, copied_package):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (a, path, _, root):
        assert a(action="cold", target=0)["ok"]
        assert a(action="prepare-only", target=2)["ok"]
        with worker(tmp_path, paths, copied_package, root=root) as (b, __, ___, ____):
            assert b(action="publish", target=1)["ok"]
        result = a(action="commit-pending")
        assert result == dict(
            ok=False, error="SegmentedException(PUBLICATION_CONFLICT)"
        )
        assert persisted(path, fixtures)["pointer"]["sequence"] == 2
        save("stale-base", result)


@pytest.mark.parametrize("point", ["crash-before", "crash-after"])
def test_real_sigkill_and_fresh_process_recovery(
    tmp_path, corpus, copied_package, point
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, process, root):
        assert command(action="cold", target=0)["ok"]
        process.stdin.write(json.dumps(dict(action=point, target=1)) + "\n")
        process.stdin.flush()
        ready = root / "crash-ready"
        deadline = time.monotonic() + 40
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert ready.exists()
        process.send_signal(signal.SIGKILL)
        assert process.wait(5) == -signal.SIGKILL
        state = persisted(path, fixtures)
        assert state["pointer"]["sequence"] == (2 if point == "crash-after" else 1)
        with worker(tmp_path, paths, copied_package, root=root) as (
            restarted,
            __,
            ___,
            ____,
        ):
            assert restarted(action="recover")["ok"]
        save(point, dict(boundary=ready.read_text(), persisted=state))


@pytest.mark.parametrize("damage", ["schema", "receipt", "body", "missing-body", "pin"])
def test_external_corruption_invalidates_provenance_and_fails_closed(
    tmp_path, corpus, copied_package, damage
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        with sqlite3.connect(path) as db:
            before = db.execute("SELECT current_id,sequence FROM accepted").fetchone()
            if damage == "schema":
                db.execute("DROP TRIGGER immutable_body")
            elif damage == "missing-body":
                sql = db.execute(
                    "SELECT sql FROM sqlite_master WHERE name='retained_graph_object_delete'"
                ).fetchone()[0]
                db.execute("DROP TRIGGER retained_graph_object_delete")
                target = db.execute(
                    "SELECT hash FROM objects WHERE kind='snapshot-leaf' LIMIT 1"
                ).fetchone()[0]
                db.execute("DELETE FROM objects WHERE hash=?", (target,))
                db.execute(sql)
            elif damage == "body":
                sql = db.execute(
                    "SELECT sql FROM sqlite_master WHERE name='immutable_body'"
                ).fetchone()[0]
                db.execute("DROP TRIGGER immutable_body")
                target, body = db.execute(
                    "SELECT hash,body FROM objects WHERE kind='snapshot-leaf' LIMIT 1"
                ).fetchone()
                changed = bytes(body).replace(b'"canon":1', b'"canon":2', 1)
                assert changed != body
                db.execute("UPDATE objects SET body=? WHERE hash=?", (changed, target))
                db.execute(sql)
            elif damage == "receipt":
                sql = db.execute(
                    "SELECT sql FROM sqlite_master WHERE name='immutable_generation'"
                ).fetchone()[0]
                db.execute("DROP TRIGGER immutable_generation")
                ident, raw = db.execute(
                    "SELECT id,receipt FROM generations WHERE id=?", (before[0],)
                ).fetchone()
                r = json.loads(raw)
                r["facts"] = "99999"
                changed = c1(r)
                db.execute(
                    "UPDATE generations SET receipt=?,receipt_checksum=? WHERE id=?",
                    (changed, hashlib.sha256(changed).hexdigest(), ident),
                )
                db.execute(
                    "UPDATE usage SET metadata=metadata+?", (len(changed) - len(raw),)
                )
                db.execute(sql)
            else:
                sql = db.execute(
                    "SELECT sql FROM sqlite_master WHERE name='retained_root_delete'"
                ).fetchone()[0]
                db.execute("DROP TRIGGER retained_root_delete")
                db.execute(
                    "DELETE FROM generation_roots WHERE generation_id=? AND hash=?",
                    (before[0], fixtures[0]["manifest"]["target"]["hot_ref"]["hash"]),
                )
                db.execute(sql)
        result = command(action="recover")
        assert not result["ok"], result
        with sqlite3.connect(path) as db:
            assert (
                db.execute("SELECT current_id,sequence FROM accepted").fetchone()
                == before
            )
        save("corruption-" + damage, result)


def test_external_valid_commit_forces_complete_recovery(
    tmp_path, corpus, copied_package
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        with sqlite3.connect(path) as db:
            db.execute(
                "INSERT INTO staging SELECT ?,manifest,checksum,created_at FROM staging LIMIT 1",
                (str(uuid4()),),
            )
        result = command(action="publish", target=0)
        assert result["ok"], result
        recovery = totals([e for e in result["events"] if e["phase"] == "recovery"])
        required_bytes = sum(
            len(base64.b64decode(o["data_base64"])) for o in fixtures[0]["objects"]
        )
        assert recovery["body_bytes_read"] >= required_bytes
        assert persisted(path, fixtures)["pointer"]["sequence"] == 1
        save("external-commit", recovery)


def test_cached_preparation_cannot_move_to_reopened_connection(
    tmp_path, corpus, copied_package
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        assert command(action="prepare-only", target=1)["ok"]
        assert command(action="reopen-only")["ok"]
        result = command(action="commit-pending")
        assert result == dict(
            ok=False, error="SegmentedException(PREPARATION_CONNECTION_CHANGED)"
        )
        assert persisted(path, fixtures)["pointer"]["sequence"] == 1
        save("reopened-preparation", result)


def test_stage_cleanup_preserves_current_previous_and_shared_objects(
    tmp_path, corpus, copied_package
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        assert command(action="publish", target=1)["ok"]
        before = persisted(path, fixtures)
        assert command(action="cleanup-stages")["removed"] >= 2
        assert persisted(path, fixtures) == before
        with sqlite3.connect(path) as db:
            leaf = next(
                o["ref"]["hash"]
                for o in fixtures[0]["objects"]
                if json.loads(base64.b64decode(o["data_base64"]))["kind"]
                == "snapshot-leaf"
            )
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("DELETE FROM objects WHERE hash=?", (leaf,))
            db.rollback()
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(
                    "DELETE FROM edges WHERE parent=?",
                    (fixtures[0]["manifest"]["target"]["raw_ref"]["hash"],),
                )
            db.rollback()
        assert persisted(path, fixtures) == before
        save("stage-retention", before)


def test_real_busy_failure_preserves_prior_accepted_target(
    tmp_path, corpus, copied_package
):
    fixtures, paths = corpus[4]
    with worker(tmp_path, paths, copied_package) as (command, path, _, __):
        assert command(action="cold", target=0)["ok"]
        before = persisted(path, fixtures)
        lock = sqlite3.connect(path)
        try:
            lock.execute("BEGIN IMMEDIATE")
            result = command(action="publish", target=1)
            assert not result["ok"] and "STORE_BUSY" in result["error"]
            assert persisted(path, fixtures) == before
        finally:
            lock.rollback()
            lock.close()
        assert command(action="publish", target=1)["ok"]
        save(
            "sqlite-busy",
            {"first_error": result["error"], "after_retry": persisted(path, fixtures)},
        )


@pytest.mark.parametrize("history", [4, 400])
def test_preserved_pre_i25_source_reproduces_full_n_work(
    tmp_path, corpus, copied_package, history
):
    fixtures, paths = corpus[history]
    mobile = tmp_path / "before/mobile"
    shutil.copytree(ROOT / "mobile/lib", mobile / "lib")
    for relative in (
        "mobile/lib/src/segmented/fetch.dart",
        "mobile/lib/src/segmented/graph.dart",
    ):
        destination = tmp_path / "before" / relative
        destination.write_bytes(
            subprocess.check_output(
                ["git", "show", "9a53b139cbb99d40020ba0635cf6b44730f3ca51:" + relative],
                cwd=ROOT,
            )
        )
    with tarfile.open(
        ROOT / "docs/benchmarks/t66e3/i25-before-worktree.tgz"
    ) as archive:
        for member in archive.getmembers():
            assert (
                member.isfile()
                and ".." not in Path(member.name).parts
                and not member.name.startswith("/")
            )
            if member.name.startswith("mobile/lib/"):
                destination = tmp_path / "before" / member.name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.extractfile(member).read())
    store = mobile / "lib/src/segmented/store.dart"
    source = store.read_text()
    assert source.count("db = sqlite3.open(path);") == 1
    store.write_text(
        source.replace(
            "import 'work.dart';", "import 'work.dart';\nimport 'audit_trace.dart';"
        ).replace("db = sqlite3.open(path);", "db = AuditDatabase(sqlite3.open(path));")
    )
    shutil.copyfile(
        HERE / "audit_trace.dart", mobile / "lib/src/segmented/audit_trace.dart"
    )
    original = ROOT / "mobile/.dart_tool/package_config.json"
    config = json.loads(original.read_text())
    for package in config["packages"]:
        uri = package["rootUri"]
        if ":" not in uri:
            package["rootUri"] = (original.parent / uri).resolve().as_uri() + "/"
        if package["name"] == "money_note_mobile":
            package["rootUri"] = mobile.as_uri() + "/"
    location = mobile / ".dart_tool/package_config.json"
    location.parent.mkdir()
    location.write_text(json.dumps(config))
    shutil.copyfile(
        original.with_name("native_assets.yaml"),
        location.with_name("native_assets.yaml"),
    )
    job = tmp_path / "before-job.json"
    job.write_text(
        json.dumps(
            {
                "fixtures": [str(p) for p in paths],
                "root": str(tmp_path / "before-store"),
            }
        )
    )
    run = subprocess.run(
        [
            "/home/hjkerman/.flutter/bin/dart",
            "--packages=" + str(location),
            str(HERE / "before_probe.dart"),
            str(job),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert run.returncode == 0, run.stderr[-3000:]
    result = json.loads(run.stdout)
    records = []
    for r in result["records"]:
        r.update(totals(r.pop("events")))
        records.append(r)
        if r["scenario"] in ("identical", "repeated"):
            assert (
                r["raw_objects_read"] + r["index_objects_read"] > r["objects"]
                and r["pin_insert"] == r["objects"]
            )
    persisted(result["path"], fixtures)
    save("before-cost-" + str(history), records)
