"""합성 감사 원시 증거와 실제 결과를 보존한다. 제품 구현은 호출/수정하지 않는다."""

from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/mn-f-continuation")
OUT = HERE / "evidence"
OUT.mkdir(exist_ok=True)
manifest = {}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def save(source, target, compressed=False):
    if not source.is_file():
        return
    raw = source.read_bytes()
    dest = OUT / (target + (".gz" if compressed else ""))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(gzip.compress(raw, mtime=0) if compressed else raw)
    manifest[str(dest.relative_to(HERE))] = {
        "source": str(source),
        "uncompressed_bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "stored_sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
    }


def machine(path):
    tests, cases, finish = {}, [], None
    for line in path.read_text().splitlines():
        try:
            e = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(e, dict):
            continue
        if e.get("type") == "testStart":
            tests[e["test"]["id"]] = e["test"]["name"]
        if e.get("type") == "testDone" and not e.get("hidden"):
            cases.append(
                dict(
                    name=tests.get(e["testID"]),
                    result=e["result"],
                    skipped=e.get("skipped", False),
                    log=path.name,
                )
            )
        if e.get("type") == "done":
            finish = e
    return dict(cases=cases, finish=finish)


def stats(values):
    a = sorted(values)
    return dict(
        n=len(a),
        min=a[0],
        median=statistics.median(a),
        p95=a[math.ceil(0.95 * len(a)) - 1],
        max=a[-1],
    )


grid = []
for n in [1000, 5000, 10000, 50000, 100000]:
    path = SOURCE / ("grid-final-small/grid" if n < 50000 else "grid") / f"{n}.json"
    x = json.loads(path.read_text())
    save(path, f"grid/{n}.json")
    grid.append(
        dict(
            n=n,
            status=x["status"],
            graph=x["independent_graph"],
            counts=x["counts"],
            compression=x["compression"],
            cold_bootstrap_ns=x["cold_bootstrap_ns"],
            max_rss_kib=x["max_rss_kib"],
            db_files=x["db_files"],
            phases=[
                dict(
                    phase=a["phase"],
                    distributions=a["distributions"],
                    counters={
                        k: stats([s["counters"].get(k, 0) for s in a["samples"]])
                        for k in [
                            "sql",
                            "SELECT",
                            "rows_returned",
                            "blob_bytes_returned",
                            "bound_blob_bytes",
                            "INSERT",
                            "UPDATE",
                            "DELETE",
                        ]
                    },
                    hot_bytes=sorted(
                        set(s["h_object_sizes"]["hot_ref"] for s in a["samples"])
                    ),
                    control_bytes=sorted(
                        set(s["h_object_sizes"]["control_ref"] for s in a["samples"])
                    ),
                )
                for a in x["phases"]
            ],
        )
    )
write(OUT / "grid-summary.json", grid)

costs = []
for name in [
    "client-1000",
    "client-5000-complete",
    "client-10000-complete",
    "unique-1000",
    "unique-5000",
    "unique-10000",
]:
    directory = SOURCE / name
    path = directory / "cost.json"
    if not path.exists():
        costs.append(dict(id=name, status="INCOMPLETE"))
        continue
    x = json.loads(path.read_text())[0]
    save(path, f"cost/{name}.json", True)
    save(directory / "cost-exit.json", f"cost/{name}-exit.json")
    save(directory / "cost.log", f"cost/{name}-machine.log", True)
    groups = {}
    for prefix in ["identical_", "card_", "cash_", "repeated_frozen_"]:
        all_samples = [a for a in x["phases"] if a["phase"].startswith(prefix)]
        measured = all_samples[3:]
        groups[prefix.rstrip("_")] = {
            k: stats([s[k] for s in measured])
            for k in [
                "sql",
                "rows_returned",
                "object_bytes",
                "raw_nodes",
                "raw_rows",
                "index_nodes",
                "http_requests",
                "object_requests",
                "http_response_bytes",
                "decoded_payload_bytes",
                "pin_insert",
                "pin_delete",
                "pin_update",
                "full_verify",
                "frozen_full_recovery",
                "legacy_full_read",
                "lineage_hash",
                "microseconds",
                "rss_bytes",
            ]
        }
    singled = [
        {
            k: v
            for k, v in s.items()
            if k not in ["backend_sql_trace", "sql_frequencies", "requested_objects"]
        }
        for s in x["phases"]
        if not any(
            s["phase"].startswith(p)
            for p in ["identical_", "card_", "cash_", "repeated_frozen_"]
        )
    ]
    costs.append(
        dict(
            id=name,
            status="PASS"
            if json.loads((directory / "cost-exit.json").read_text())["exit"] == 0
            else "FAIL",
            exact_ledger_n=x.get("ledger_rows"),
            historical_history_parameter=x.get("history"),
            preparation_us=x.get("preparation_us"),
            groups=groups,
            single_samples=singled,
        )
    )
write(OUT / "cost-summary.json", costs)

runs, selected = {}, {}
for name in [
    "profile.log",
    "negative-final.log",
    "authority-complete.log",
    "supersession.log",
    "offline.log",
    "lineage.log",
    "media-diagnostic.log",
]:
    data = machine(SOURCE / name)
    runs[name] = data
    for case in data["cases"]:
        if not case["name"].startswith("C-"):
            continue
        ident = case["name"].split()[0]
        case["id"] = ident
        case["category"] = (
            "diagnostic_outside_binding"
            if ident == "C-N-content_type"
            else "negative"
            if ident.startswith("C-N-")
            else "authority"
            if ident.startswith(("C-A-", "C-I-", "C-L"))
            else "functional"
        )
        selected[ident] = case
root = ET.parse(SOURCE / "identity-final.xml").getroot()
for case in root.iter("testcase"):
    selected["C-DB-" + case.attrib["name"]] = dict(
        id="C-DB-" + case.attrib["name"],
        name=case.attrib["name"],
        category="backend_identity",
        result="failure"
        if case.find("failure") is not None or case.find("error") is not None
        else "success",
        log="identity-final.xml",
    )
write(
    OUT / "cases.json",
    dict(
        cases=list(selected.values()),
        runs=runs,
        counts=dict(
            Counter((c["category"] + ":" + c["result"]) for c in selected.values())
        ),
    ),
)

checks = {}
for file in (SOURCE / "checks").glob("*-process.json"):
    checks[file.stem] = json.loads(file.read_text())
for mode in [
    "backend-full",
    "flutter-full",
    "frontend",
    "analyze",
    "build",
    "ruff",
    "compileall",
    "format-python",
    "format-dart",
]:
    save(SOURCE / "checks" / f"{mode}-process.json", f"checks/{mode}-process.json")
    save(SOURCE / "checks" / f"{mode}.log", f"checks/{mode}.log", True)
save(SOURCE / "checks/backend-full.xml", "checks/backend-full.xml")
for name in [
    "b01-rerun.xml",
    "b01-rerun.log",
    "prior-http.log",
    "prior-http.json",
    "prior-quota.json",
    "selected-process-exits.json",
]:
    save(SOURCE / name, "regression/" + name, name.endswith(".log"))
for file in (SOURCE / "b01-rerun").glob("*.json"):
    save(file, "regression/b01/" + file.name)
for mode in ["backend-crash-regression", "crash-regression"]:
    save(SOURCE / (mode + ".xml"), "regression/" + mode + ".xml")
    save(SOURCE / (mode + ".log"), "regression/" + mode + ".log", True)
    for file in (SOURCE / mode).glob("*"):
        if file.is_file() and file.suffix in [".json", ".log"]:
            save(file, "regression/" + mode + "/" + file.name, file.suffix == ".log")
    path = SOURCE / (mode + ".xml")
    if path.exists():
        checks[mode] = next(ET.parse(path).getroot().iter("testsuite")).attrib
if (SOURCE / "prior-http.log").exists():
    checks["prior_http_smoke"] = machine(SOURCE / "prior-http.log")
if (SOURCE / "b01-rerun.xml").exists():
    checks["b01_independent_python_junit"] = next(
        ET.parse(SOURCE / "b01-rerun.xml").getroot().iter("testsuite")
    ).attrib
full_flutter = machine(SOURCE / "checks/flutter-full.log")
checks["flutter_counts"] = dict(
    passed=sum(
        c["result"] == "success" and not c["skipped"] for c in full_flutter["cases"]
    ),
    failed=sum(c["result"] != "success" for c in full_flutter["cases"]),
    skipped=sum(c["skipped"] for c in full_flutter["cases"]),
    finish=full_flutter["finish"],
)
suite = next(ET.parse(SOURCE / "checks/backend-full.xml").getroot().iter("testsuite"))
checks["backend_junit"] = suite.attrib
write(OUT / "checks-summary.json", checks)

for name in [
    "budget-50000.json",
    "money-golden.json",
    "environment.json",
    "executed-source-hashes.json",
    "native-environment.json",
    "authority-complete.json",
    "negative-final.json",
    "supersession.json",
    "offline.json",
    "lineage.json",
    "media-diagnostic.json.diagnostic-content_type",
    "identity-final.xml",
    "identity-formatted.xml",
    "identity.xml",
]:
    save(
        SOURCE / name,
        name,
        name.endswith(".diagnostic-content_type") or name == "identity.xml",
    )
for name in [
    "profile.log",
    "negative-final.log",
    "authority-complete.log",
    "supersession.log",
    "offline.log",
    "lineage.log",
    "media-diagnostic.log",
    "identity-final.log",
    "identity-formatted.log",
    "identity.log",
    "authority.log",
    "authority-final.log",
    "adversarial.log",
    "adversarial-2.log",
    "grid-process.log",
    "grid-final-small-process.log",
    "adversarial-before-singleflight.dart",
]:
    save(SOURCE / name, "runs/" + name, True)
for file in (SOURCE / "identity-final").glob("*.json"):
    save(file, "identity/" + file.name)
for file in (SOURCE / "executed-sources").glob("*"):
    save(file, "executed-sources/" + file.name, True)
for file in SOURCE.glob("grid-*-process.json"):
    save(file, "runs/" + file.name)
for n in [1000, 5000, 10000]:
    save(SOURCE / "grid" / f"{n}.json", f"preliminary-grid/{n}.json")
for name in ["client-5000", "client-5000-final"]:
    for file in (SOURCE / name).glob("*"):
        if file.is_file() and file.name in ["cost.log", "cost-exit.json"]:
            save(file, "preliminary-runs/" + name + "/" + file.name, True)
shutil.copyfile(HERE / "coverage-initial.json", OUT / "coverage-before-execution.json")
write(OUT / "manifest.json", manifest)
print(
    json.dumps(
        dict(
            grid_points=len(grid),
            cost_runs=[(x["id"], x["status"]) for x in costs],
            cases=dict(Counter(c["result"] for c in selected.values())),
            flutter=checks["flutter_counts"],
        ),
        ensure_ascii=False,
    )
)
