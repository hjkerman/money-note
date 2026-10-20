"""새 correction evidence만 수집한다. 과거 audit/evidence는 읽기 전용이다."""

from collections import Counter
import gzip
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def machine(path):
    counts, failures, done = Counter(), [], None
    if not path.exists():
        return None
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("type") == "testDone" and not row.get("hidden"):
            counts["skip" if row.get("skipped") else row["result"]] += 1
        elif row.get("type") == "error":
            failures.append({k: row[k] for k in ("testID", "error", "stackTrace")})
        elif row.get("type") == "done":
            done = row
    return dict(counts=counts, completed=done, failures=failures)


def archive(source, name):
    if source.exists():
        (HERE / name).write_bytes(gzip.compress(source.read_bytes(), mtime=0))


def http(n, suffix=""):
    pointer = read(HERE / f"active-http-{n}{suffix}.json")
    if pointer is None:
        return {"status": "NOT RUN"}
    out = Path(pointer["out"])
    rows, hist, metrics = [], Counter(), Counter()
    trace = out / "server/requests.jsonl"
    if trace.exists():
        for line in trace.read_text().splitlines():
            row = json.loads(line)
            if row.get("chunks"):
                hist[row["chunks"]] += 1
                m = row.get("implementation_metrics", {})
                for key in (
                    "object_reads",
                    "object_bytes_read",
                    "prefix_cache_hits",
                    "prefix_validations",
                    "decoded_bytes",
                ):
                    metrics[key] += m.get(key, 0)
            rows.append(row)
    for name in (
        "result.json",
        "execution.json",
        "server-final-stats.json",
        "fresh-process.json",
        "post-reads.json",
        "cold-summary.json",
        "durable-state.json",
        "flutter.jsonl",
        "flutter.err",
        "server.stderr",
        "server/requests.jsonl",
        "server/http-failures.json",
        "server/backend-fixture.json",
        "server/wire-final.json",
    ):
        archive(out / name, f"http-{n}{suffix}-{name.replace('/', '-')}.gz")
    # Three explicit mutations at most; preserve backend expected rows/counts.
    mutations = sorted((out / "server").glob("mutation-*.json"))
    assert len(mutations) <= 3
    for path in mutations:
        archive(path, f"http-{n}{suffix}-server-{path.name}.gz")
    manifests = [r["manifest"] for r in rows if "manifest" in r]
    return dict(
        out=str(out),
        execution=read(out / "execution.json"),
        result=read(out / "result.json"),
        fresh_process=read(out / "fresh-process.json"),
        post_reads=read(out / "post-reads.json"),
        cold_summary=read(out / "cold-summary.json"),
        durable_state=read(out / "durable-state.json"),
        full_http_test=machine(out / "flutter.jsonl"),
        packet_histogram=hist,
        implementation_metrics=metrics,
        observations=[
            dict(
                id=m["observation_id"],
                validated=m["validated_at"],
                expires=m["expires_at"],
                sync_root=m["target"]["sync_root"],
            )
            for m in manifests
        ],
        server_stats=read(out / "server-final-stats.json"),
    )


def main():
    runtime = Path(sys.argv[1])
    result = dict(
        starting_head="6282c1c3577c42bba9382d786745d583a5d88236",
        classification="IMPLEMENTATION-SIDE; independent audit pending",
        r1="CLOSED",
        commit=None,
        push=False,
        runtime=str(runtime),
        tests={},
        large={},
    )
    for name in (
        "packet-v5",
        "packet-cursor",
        "artifact-b02",
        "source-guards-reviewed",
        "source-guards-final",
        "cursor-guards-b02",
        "flutter-full",
        "flutter-full-before-cursor-fix",
        "wire-regression",
    ):
        result["tests"][name] = machine(runtime / f"{name}.jsonl")
    for name in ("backend-full", "backend-related", "prefix-28", "prefix-final-source"):
        path = runtime / f"{name}.log"
        if path.exists():
            text = path.read_text()
            result["tests"][name] = dict(
                terminal_summary=re.findall(
                    r"[^\n]*(?:passed|failed|error)[^\n]*", text
                )[-2:]
            )
    result["packet_component"] = read(runtime / "packet-performance.json")
    for n in (1000, 50000, 100000):
        suffix = (
            "-cursor-lifetime"
            if (HERE / f"active-http-{n}-cursor-lifetime.json").exists()
            else ""
        )
        result["large"][str(n)] = http(n, suffix)
    result["before_cursor_fix"] = {
        "first_1000": http(1000),
        "failed_50000": http(50000),
        "flutter_interrupted": read(
            HERE / "flutter-before-cursor-fix-interruption.json"
        ),
    }
    result["packet_component_cursor_fixed"] = read(
        runtime / "packet-cursor-performance.json"
    )
    # Only new runtime logs; no credentials, cert/private keys, or DB copies.
    for path in runtime.iterdir():
        if path.suffix in (".jsonl", ".err", ".log", ".xml", ".json"):
            archive(path, "log-" + path.name + ".gz")
    (HERE / "summary.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "tests": {
                    k: v.get("counts", v.get("terminal_summary")) if v else None
                    for k, v in result["tests"].items()
                },
                "large": {
                    k: v.get("result", {}).get("status")
                    if v.get("result")
                    else v.get("status", "RUNNING")
                    for k, v in result["large"].items()
                },
            }
        )
    )


if __name__ == "__main__":
    main()
