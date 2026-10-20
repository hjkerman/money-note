"""실행된 결과만 새 summary로 수집. 첫 승인 전 summary/history는 불변."""

import importlib.util
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "preserved_a01_collector", HERE.parent / "t66f-b02-a01-correction/collect.py"
)
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
original.HERE = HERE  # all NEW archives go here, never into A01 evidence


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def main():
    value = dict(
        classification="IMPLEMENTATION-SIDE — independent audit pending",
        r1="CLOSED",
        tests={},
        large={},
    )
    for name in (
        "flutter-control",
        "flutter-continuation",
        "flutter-expanded",
        "guard-cleanup",
        "targeted-final",
        "flutter-full",
        "wire-regression",
    ):
        path = Path("/tmp") / f"mn-a02-{name}.jsonl"
        if not path.exists():
            path = path.with_suffix(".log")
        value["tests"][name] = original.machine(path)
    for name in (
        "codec-tests",
        "backend-targeted",
        "canonical-regression",
        "b01-strict",
        "backend-full",
        "backend-related",
    ):
        path = Path("/tmp") / f"mn-a02-{name}.log"
        if path.exists():
            value["tests"][name] = dict(
                terminal_summary=re.findall(
                    r"[^\n]*(?:passed|failed|error)[^\n]*", path.read_text()
                )[-3:]
            )
    for n in (1000, 50000, 100000):
        pointer = read(HERE / f"active-http-{n}.json")
        if pointer and (Path(pointer["out"]) / "execution.json").exists():
            value["large"][str(n)] = original.http(n)
        else:
            value["large"][str(n)] = {
                "status": "NOT RUN" if pointer is None else "RUNNING"
            }
    for name in (
        "codec-benchmark",
        "renewal-benchmark",
        "source-lock-review",
        "artifact-review-approved",
        "format-baseline-review",
        "preservation-final",
        "large-final-review",
        "process-results",
    ):
        value[name] = read(HERE / f"{name}.json")
    full_log = Path("/tmp/mn-a02-flutter-full.jsonl")
    suites, tests, counts = {}, {}, {}
    if full_log.exists():
        for line in full_log.read_text().splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if not isinstance(event, dict):
                continue
            if event.get("type") == "suite":
                suites[event["suite"]["id"]] = event["suite"].get("path")
            elif event.get("type") == "testStart":
                tests[event["test"]["id"]] = event["test"]
            elif event.get("type") == "testDone" and not event.get("hidden"):
                test = tests[event["testID"]]
                path = suites.get(test["suiteID"]) or test.get("url", "unknown")
                path = str(path).split("/mobile/test/")[-1]
                count = counts.setdefault(path, {})
                key = "skip" if event.get("skipped") else event["result"]
                count[key] = count.get(key, 0) + 1
    value["full_flutter_by_file"] = counts
    value["product_source_sha256"] = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in (
            "backend/isolated_sync/canonical.py",
            "backend/isolated_sync/transfer.py",
            "mobile/lib/src/app_state.dart",
            "mobile/lib/src/segmented/fetch.dart",
            "mobile/lib/src/segmented/protocol.dart",
            "mobile/lib/src/segmented/store.dart",
            "mobile/lib/src/segmented/graph.dart",
        )
    }
    for n, campaign in value["large"].items():
        for path, digest in (
            campaign.get("execution", {}).get("source_sha256", {}).items()
        ):
            assert value["product_source_sha256"][path] == digest, (n, path)
    value["validation"] = {}
    for phase in (
        "external-backend",
        "external-flutter",
        "checks",
        "format",
        "compatibility",
        "lint",
        "lineage-fixed",
    ):
        record = read(HERE / f"validation-{phase}.json")
        value["validation"][phase] = record
        if record is None:
            continue
        for command in record["commands"]:
            path = Path(command["log"])
            if "test" in command["args"] and "--machine" in command["args"]:
                value["tests"][command["name"]] = original.machine(path)
            elif "pytest" in command["args"]:
                value["tests"][command["name"]] = dict(
                    exit=command["exit"],
                    terminal_summary=re.findall(
                        r"[^\n]*(?:passed|failed|error)[^\n]*", path.read_text()
                    )[-3:],
                )
        # This runner owns the fresh synthetic output; never copy DBs/keys/APKs.
        out = Path(record["out"])
        assert out.parent == Path("/tmp") and out.name.startswith("mn-a02-")
        total = 0
        for path in out.rglob("*"):
            if path.is_file() and (
                path.suffix in (".json", ".jsonl", ".xml")
                or path.name == "negative-authority.json.diagnostic-content_type"
            ):
                total += path.stat().st_size
                assert path.stat().st_size < 20 * 1024**2 and total < 128 * 1024**2
                original.archive(
                    path,
                    "validation-"
                    + phase
                    + "-"
                    + str(path.relative_to(out)).replace("/", "-")
                    + ".gz",
                )
    # Only explicitly scoped synthetic runner text, never directories/DB/keys.
    for path in Path("/tmp").glob("mn-a02-*"):
        if path.is_file() and path.suffix in (
            ".json",
            ".jsonl",
            ".err",
            ".log",
            ".xml",
            ".exit",
        ):
            original.archive(path, "log-" + path.name + ".gz")
    (HERE / "final-summary.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            dict(
                tests={
                    k: v.get("counts", v.get("terminal_summary")) if v else None
                    for k, v in value["tests"].items()
                },
                large={
                    k: v.get("result", {}).get("status")
                    if v.get("result")
                    else v.get("status")
                    for k, v in value["large"].items()
                },
            )
        )
    )


if __name__ == "__main__":
    main()
