"""Read completed B01 evidence; never turn a diagnostic exit into a PASS."""

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import platform
import re
import sqlite3
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
BASE = "c479a379b54e196439c522c1fdf56eca713ca8ad"
TEST_PATH = "backend/tests/test_isolated_sync_transfer.py"
TEST_NAME = "test_bounded_concurrent_quota_and_same_request_status"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def junit(path):
    if not path.exists():
        return dict(state="NOT_COMPLETE")
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root)
    failures = []
    for suite in suites:
        for case in suite.findall("testcase"):
            for tag in ("failure", "error"):
                bad = case.find(tag)
                if bad is not None:
                    failures.append(dict(name=case.get("name"), evidence=bad.text))
    return dict(
        state="COMPLETE",
        **{
            key: sum(int(s.get(key, 0)) for s in suites)
            for key in ("tests", "failures", "errors", "skipped")
        },
        seconds=sum(float(s.get("time", 0)) for s in suites),
        failure_evidence=failures,
        sha256=sha(path.read_bytes()),
    )


def backend(folder, stem):
    result = junit(folder / (stem + ".xml"))
    log = folder / (stem + ".log")
    if log.exists():
        text = log.read_text()
        lines = [line for line in text.splitlines() if "subtests passed" in line]
        result.update(
            log_sha256=sha(log.read_bytes()), summary=lines[-1] if lines else None
        )
        if lines:
            result["main_pass"] = int(re.search(r"(\d+) passed", lines[-1])[1])
            result["subtests_pass"] = int(
                re.search(r"(\d+) subtests passed", lines[-1])[1]
            )
    return result


def assertion_bytes(source):
    function = next(
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name == TEST_NAME
    )
    lines = source.splitlines(keepends=True)
    return [
        "".join(lines[node.lineno - 1 : node.end_lineno])
        for node in ast.walk(function)
        if isinstance(node, ast.Assert)
    ]


def preservation():
    selected = [
        "backend/app",
        "backend/isolated_sync",
        "mobile/lib",
        "docs/benchmarks/t66f-phase-b",
        "docs/t66f-phase-b-independent-verification.md",
        "docs/t66/c/t66c-delta-sync-protocol.md",
        "docs/t66e4-independent-audit.md",
        "docs/t66e4-a01-independent-reaudit.md",
        "docs/t66e4-a01-correction.md",
        "docs/t66e4-ra01-correction.md",
    ]
    paths = (
        subprocess.check_output(
            ["git", "ls-tree", "-r", "--name-only", BASE, "--", *selected], cwd=ROOT
        )
        .decode()
        .splitlines()
    )
    hashes, changed = {}, []
    for path in paths:
        before = subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
        actual = (ROOT / path).read_bytes()
        hashes[path] = sha(actual)
        if before != actual:
            changed.append(path)
    original = subprocess.check_output(
        ["git", "show", BASE + ":" + TEST_PATH], cwd=ROOT
    ).decode()
    current = (ROOT / TEST_PATH).read_text()
    original_assertions, current_assertions = (
        assertion_bytes(original),
        assertion_bytes(current),
    )
    assert len(original_assertions) == 3 and original_assertions == current_assertions
    assert not changed, changed
    return dict(
        protected_count=len(paths),
        hashes=hashes,
        changed=changed,
        original_assertions_sha256=sha("".join(original_assertions).encode()),
        original_assertions_unchanged=True,
        original_test_sha256=sha(original.encode()),
        corrected_test_sha256=sha(current.encode()),
    )


def campaign(folder):
    path = folder / "summary.json"
    if not path.exists():
        return dict(state="NOT_COMPLETE")
    rows = json.loads(path.read_text())
    assert all(row["errors"] == 0 and row["exit"] in (0, 1) for row in rows)
    waits, errors, work = [], [], []
    for row in rows:
        data = json.loads((folder / (str(row["iteration"]) + ".json")).read_text())
        waits.extend(
            e["elapsed_us"]
            for e in data["events"]
            if e["event"] == "sql_end" and e["sql"] == "BEGIN IMMEDIATE"
        )
        errors.extend(e for e in data["events"] if e["event"] == "sql_error")
        # Normalize statement classes, not VM operations or scanned row counts.
        categories = Counter()
        for sql, count in data["statements"].items():
            categories[sql.split()[0].upper()] += count
        work.append(
            dict(
                iteration=row["iteration"],
                statuses=row["statuses"],
                sql_calls=dict(categories),
                observer_mode=data.get("observer_mode", "sql_timeline"),
                handles=len(data["handles"]) if data["handles"] else None,
                all_closed=all(h["closed"] for h in data["handles"].values())
                if data["handles"]
                else None,
                available=len(data["persisted"]["observations"]),
                pins=sum(r[2] for r in data["persisted"]["pins"]),
            )
        )
    return dict(
        state="COMPLETE",
        pass_count=sum(row["exit"] == 0 for row in rows),
        fail_count=sum(row["exit"] != 0 for row in rows),
        rows=rows,
        max_successful_begin_wait_us=max(waits) if waits else None,
        sql_errors=errors,
        work=work,
    )


def machine(path):
    if not path.exists():
        return dict(done=None)
    counts, done = Counter(), None
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            if event.get("type") == "testDone" and not event.get("hidden"):
                counts["SKIP" if event.get("skipped") else event["result"]] += 1
            elif event.get("type") == "done":
                done = event["success"]
    return dict(done=done, counts=dict(counts), sha256=sha(path.read_bytes()))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    folder = args.output
    result = dict(
        starting_commit=BASE,
        classification="TEST HARNESS",
        product_modified=False,
        environment=dict(
            python=platform.python_version(),
            platform=platform.platform(),
            sqlite=sqlite3.sqlite_version,
        ),
        original_isolated=junit(folder / "isolated-original.xml"),
        before_full=backend(folder, "backend-before"),
        after_full_1=backend(folder, "backend-after-1"),
        after_full_2=backend(folder, "backend-after-2"),
        before_repeated=campaign(folder / "repeated-under-suite"),
        baseline_copy_repeated=campaign(folder / "baseline-copy"),
        baseline_light_repeated=campaign(folder / "baseline-light"),
        after_repeated=campaign(folder / "repeated-after-under-suite"),
        after_quiet_repeated=campaign(folder / "repeated-after-quiet"),
        targeted=junit(folder / "targeted-final.xml"),
        related=junit(folder / "related.xml"),
        order_first=junit(folder / "order-variation.xml"),
        order_reversed=junit(folder / "order-reversed.xml"),
        real_http=junit(folder / "real-http.xml"),
        flutter_http=machine(folder / "flutter-http.log"),
        preservation=preservation(),
    )
    if args.require_complete:
        for name in ("after_full_1", "after_full_2"):
            run = result[name]
            assert (
                run["state"] == "COMPLETE" and run["failures"] == run["errors"] == 0
            ), name
            assert run["main_pass"] == 1315 and run["subtests_pass"] == 1540, name
        assert result["before_repeated"]["fail_count"] >= 1
        assert result["baseline_copy_repeated"]["fail_count"] >= 1
        assert result["before_full"]["state"] == "COMPLETE"
        for name in ("after_repeated", "after_quiet_repeated"):
            assert result[name]["fail_count"] == 0 and result[name]["pass_count"] >= 4
        for name in (
            "targeted",
            "related",
            "real_http",
            "order_first",
            "order_reversed",
        ):
            assert (
                result[name]["state"] == "COMPLETE"
                and result[name]["failures"] == result[name]["errors"] == 0
            ), name
        assert result["targeted"]["tests"] == 4 and result["real_http"]["tests"] == 2
        assert result["order_first"]["tests"] == result["order_reversed"]["tests"] == 3
        assert result["flutter_http"]["done"] is True and result["flutter_http"][
            "counts"
        ] == {"success": 3}
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
