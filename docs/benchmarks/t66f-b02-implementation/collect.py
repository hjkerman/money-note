"""실행한 증거만 요약한다. 원 조사/감사 파일은 쓰지 않는다."""

from collections import Counter
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent


def machine(path):
    counts = Counter()
    names = {}
    done = None
    errors = []
    for line in path.read_text().splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        if row.get("type") == "testStart":
            names[row["test"]["id"]] = row["test"]["name"]
        if row.get("type") == "testDone" and not row.get("hidden"):
            counts["skip" if row.get("skipped") else row["result"]] += 1
        if row.get("type") == "done":
            done = row
        if row.get("type") == "error":
            errors.append(row)
    return dict(counts=counts, terminal=done, errors=errors, tests=names)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    evidence = HERE / "evidence"
    evidence.mkdir(exist_ok=True)
    summary = dict(starting_commit="6282c1c3577c42bba9382d786745d583a5d88236")
    for name in (
        "profile-tests",
        "profile-final",
        "profile-corrected",
        "profile-authority-final",
        "independent-profile",
        "flutter-full",
        "flutter-bounded-full",
        "bounded-profile-tests",
        "bounded-final-targeted",
        "bounded-final-verified",
        "batch-boundaries",
        "profile-boundaries-final",
        "profile-crash",
    ):
        path = args.out / f"{name}.jsonl"
        if path.exists():
            summary[name] = machine(path)
            (evidence / f"{name}.jsonl.gz").write_bytes(
                gzip.compress(path.read_bytes(), mtime=0)
            )
            err = path.with_suffix(".err")
            if err.exists():
                (evidence / err.name).write_bytes(err.read_bytes())
    for name in (
        "n50000",
        "n100000",
        "bounded50000",
        "bounded100000",
        "complete1000",
    ):
        folder = args.out / name
        value = {}
        for file in ("result.json", "fresh-process.json", "server-final-stats.json"):
            if (folder / file).exists():
                value[file] = json.loads((folder / file).read_text())
        if (folder / "flutter.jsonl").exists():
            value["test"] = machine(folder / "flutter.jsonl")
        summary[name] = value
        dest = evidence / name
        dest.mkdir(exist_ok=True)
        for path in folder.rglob("*") if folder.exists() else []:
            if path.is_file() and path.suffix in (".json", ".jsonl", ".err", ".stderr"):
                rel = path.relative_to(folder)
                target = dest / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix == ".jsonl":
                    target.with_suffix(".jsonl.gz").write_bytes(
                        gzip.compress(path.read_bytes(), mtime=0)
                    )
                else:
                    target.write_bytes(path.read_bytes())
    for name in (
        "analyze-final-source.log",
        "analyze-final.log",
        "build.log",
        "build-final.log",
        "frontend-build.log",
        "frontend-build-final.log",
        "ruff-final.log",
        "compileall-final.log",
        "format-final.log",
        "app-state-final-format.log",
        "python-format-final.log",
        "final-targeted.jsonl",
        "final-targeted.err",
        "final-sequential-targeted.jsonl",
        "final-sequential-targeted.err",
    ):
        path = args.out / name
        if path.exists():
            (evidence / f"{name}.gz").write_bytes(
                gzip.compress(path.read_bytes(), mtime=0)
            )
            if name.endswith(".jsonl"):
                summary[name] = machine(path)
    xml = args.out / "backend-full.xml"
    if xml.exists():
        suites = ET.parse(xml).getroot()
        summary["backend-full"] = [s.attrib for s in suites.iter("testsuite")]
        (evidence / xml.name).write_bytes(xml.read_bytes())
        (evidence / "backend-full.log.gz").write_bytes(
            gzip.compress((args.out / "backend-full.log").read_bytes(), mtime=0)
        )
    protected = {}
    paths = (
        subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    excluded = {
        "mobile/lib/src/app_state.dart",
        "mobile/lib/src/segmented/fetch.dart",
        "mobile/lib/src/segmented/store.dart",
    }
    for name in paths:
        if not name or name in excluded:
            continue
        if name.startswith(
            ("mobile/lib/", "mobile/test/", "backend/", "docs/t66", "docs/benchmarks/")
        ):
            current = (ROOT / name).read_bytes()
            old = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
            protected[name] = dict(
                sha256=hashlib.sha256(current).hexdigest(), unchanged=current == old
            )
    summary["protected_files"] = len(protected)
    summary["protected_files_unchanged"] = all(
        v["unchanged"] for v in protected.values()
    )
    summary["intentional_product_changes"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in sorted(excluded)
    }
    (evidence / "product.diff.gz").write_bytes(
        gzip.compress(
            subprocess.check_output(["git", "diff", "--", *sorted(excluded)], cwd=ROOT),
            mtime=0,
        )
    )
    (evidence / "preservation.json").write_text(json.dumps(protected, indent=2) + "\n")
    (evidence / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "protected_files": len(protected),
                "unchanged": summary["protected_files_unchanged"],
            }
        )
    )


if __name__ == "__main__":
    main()
