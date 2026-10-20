"""이미 실행한 조사 evidence만 수집한다. PEM/DB/credential은 포함하지 않는다."""

from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE / "evidence"
FIRST = Path(json.loads((HERE / "runs.json").read_text())["initial_run"])
FINAL = Path(json.loads((HERE / "active-run.json").read_text())["out"])


def machine(path):
    counts = Counter()
    names = {}
    errors = []
    done = None
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("type") == "testStart":
            names[row["test"]["id"]] = row["test"]
        if row.get("type") == "testDone" and not row.get("hidden"):
            counts["skip" if row.get("skipped") else row.get("result", "unknown")] += 1
        if row.get("type") == "error":
            errors.append(row)
        if row.get("type") == "done":
            done = row
    return dict(
        counts=counts,
        terminal=done,
        errors=[dict(test=names.get(e.get("testID")), error=e) for e in errors],
    )


def main():
    assert (FINAL / "execution.json").exists(), "최종 cold 실행 미완료"
    assert (FINAL / "postchecks-complete.json").exists(), "후속 검사 미완료"
    EVIDENCE.mkdir(exist_ok=True)
    summary = dict(
        first_out=str(FIRST),
        confirmation_out=str(FINAL),
        starting_head="6282c1c3577c42bba9382d786745d583a5d88236",
        full_flutter="NOT RERUN",
        full_backend="NOT RERUN",
        r1="CLOSED",
        new_commit=None,
        push=False,
    )
    common = [
        "durable-state.json",
        "command.json",
        "execution.json",
        "result.json",
        "analysis.json",
        "reconciled.json",
        "resources.jsonl",
        "client-timeline.jsonl",
        "flutter.jsonl",
        "flutter.err",
        "server.stderr",
        "server-final-stats.json",
        "fresh-process.json",
        "fresh-reopen.log",
        "fresh-reopen.err",
        "postchecks.json",
        "postchecks-complete.json",
        "targeted-flutter.log",
        "targeted-flutter.err",
        "targeted-backend.log",
        "targeted-backend.err",
        "targeted-backend.xml",
        "frontend-build.log",
        "frontend-build.err",
        "ruff-backend.log",
        "ruff-backend.err",
        "compileall.log",
        "compileall.err",
        "diff-check.log",
        "diff-check.err",
        "component-sample.json",
        "backend-component.json",
        "backend-component.log",
        "e1-component.json",
        "e1-component.log",
        "reuse-result.json",
        "reuse-result-v2.json",
        "reuse-flutter.jsonl",
        "reuse-flutter.err",
        "reuse-v2-flutter.jsonl",
        "reuse-v2-flutter.err",
        "reuse-raw-error.log",
        "reuse-raw-error-v2.log",
        "sink-probe.log",
        "sink-transport-probe.log",
        "server/backend-fixture.json",
        "server/requests.jsonl",
        "server/wire-final.json",
        "server/http-failures.json",
        "server/manifest-1.json",
        "server/manifest-2.json",
        "server/manifest-3.json",
    ]
    for label, folder in [("first", FIRST), ("confirmation", FINAL)]:
        destination = EVIDENCE / label
        destination.mkdir(exist_ok=True)
        for name in common:
            path = folder / name
            if not path.is_file():
                continue
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            data = path.read_bytes()
            if path.suffix in (".jsonl", ".log", ".err", ".stderr") or name.endswith(
                "analysis.json"
            ):
                target = target.with_suffix(target.suffix + ".gz")
                data = gzip.compress(data, mtime=0)
            target.write_bytes(data)
        environment = json.loads((folder / "environment.json").read_text())
        # Keep actual resource values, omit unrelated daemon argv from public evidence.
        environment.pop("processes", None)
        (destination / "environment.json").write_text(
            json.dumps(environment, indent=2) + "\n"
        )
        summary[label] = dict(
            execution=json.loads((folder / "execution.json").read_text()),
            result=json.loads((folder / "result.json").read_text()),
            test=machine(folder / "flutter.jsonl"),
        )
    summary["targeted_flutter"] = machine(FINAL / "targeted-flutter.log")
    summary["diagnostic_mock_v2"] = machine(FIRST / "reuse-v2-flutter.jsonl")
    summary["targeted_backend_suites"] = [
        s.attrib
        for s in ET.parse(FINAL / "targeted-backend.xml").getroot().iter("testsuite")
    ]
    summary["postchecks"] = json.loads((FINAL / "postchecks.json").read_text())
    (EVIDENCE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    manifest = {
        str(p.relative_to(EVIDENCE)): dict(
            bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()
        )
        for p in sorted(EVIDENCE.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (EVIDENCE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                files=len(manifest),
                targeted_flutter=summary["targeted_flutter"]["counts"],
                backend=summary["targeted_backend_suites"],
            )
        )
    )


if __name__ == "__main__":
    main()
