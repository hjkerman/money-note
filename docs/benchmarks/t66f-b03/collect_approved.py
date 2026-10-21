"""승인 후 결과만 별도 보존한다. 승인 전 FAIL/집계와 역사 자료는 덮어쓰지 않는다."""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from collect import OUT, ROOT, flutter
from evidence_format import snapshot


def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def main():
    runs = {}
    for name in [
        "approved-source-lock",
        "approved-source-lock-final",
        "backend-approval",
        "backend-approval-final",
        "approved-backend-final-2",
        "approved-backend-final-3",
        "approved-analyze-1",
        "approved-analyze-final",
        "approved-analyze-final-2",
        "approved-boundary",
        "approved-boundary-2",
        "approved-boundary-3",
        "approved-calibration-final",
        "approved-calibration-final-2",
        "approved-http",
        "approved-http-2",
        "approved-http-3",
        "approved-http-final",
        "approved-frozen-final",
        "approved-file-delegate-final",
    ]:
        for suffix in [".xml", ".log", ".jsonl", ".err"]:
            source = Path("/tmp") / ("mn-b03-" + name + suffix)
            if not source.is_file():
                continue
            raw = source.read_bytes()
            target = OUT / (name + suffix + ("" if suffix == ".xml" else ".gz"))
            target.write_bytes(raw if suffix == ".xml" else gzip.compress(raw, mtime=0))
            if suffix == ".jsonl":
                runs[name] = flutter(source)
            elif suffix == ".xml":
                root = ET.fromstring(raw)
                runs[name] = dict(
                    tests=len(list(root.iter("testcase"))),
                    fail=len(list(root.iter("failure"))),
                    errors=len(list(root.iter("error"))),
                )
    for source in [Path(f"/tmp/mn-b03-approved-http-3-n{n}.json") for n in [9, 260]]:
        if source.exists():
            data = json.loads(source.read_text())
            label = source.stem.removeprefix("mn-b03-")
            write(label + ".json", data)
            for layer, key in [
                ("flutter-primitives", "primitive"),
                ("flutter-sqlite", "sqlite"),
                ("backend", "backend"),
            ]:
                write(
                    label + "-" + layer + ".json",
                    snapshot(
                        data["run_id"] + ":" + data["phases"]["cold"]["generation"],
                        data["fixture"],
                        "cold-identical-delta-accepted-read-fresh-cumulative",
                        layer,
                        data["phases"]["final"][key],
                        data["environment"],
                        {
                            "scope": data["coverage"],
                            "exclusions": data["exclusions"],
                            "missing_mandatory": "OfflineStore.recoveryLineageFingerprint actual SHA input",
                        },
                    ),
                )
    for source in [
        Path("/tmp/mn-b03-approved-frozen-final-frozen.json"),
        Path("/tmp/mn-b03-approved-http-final-concurrent.json"),
        Path("/tmp/mn-b03-approved-overhead-dart.json"),
    ]:
        if source.exists():
            write(source.name.removeprefix("mn-b03-"), json.loads(source.read_text()))
    initial = json.loads((OUT / "initial.json").read_text())
    changed = {
        p: dict(
            old_sha256=old,
            new_sha256=hashlib.sha256((ROOT / p).read_bytes()).hexdigest(),
        )
        for p, old in initial["sha256"].items()
        if (ROOT / p).is_file()
        and hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != old
    }

    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT).decode().strip()

    write(
        "approved-repository.json",
        dict(
            head=git("rev-parse", "HEAD"),
            main=git("rev-parse", "main"),
            origin_main=git("rev-parse", "origin/main"),
            remote_main=git("ls-remote", "origin", "refs/heads/main"),
            status=git("status", "--short"),
            staged=git("diff", "--cached", "--name-status"),
            changed_tracked_files=changed,
            missing_tracked_files=[
                p for p in initial["sha256"] if not (ROOT / p).is_file()
            ],
            commit="NOT PERFORMED",
            push="NOT PERFORMED",
        ),
    )
    write(
        "approved-calibration-summary.json",
        dict(
            schema_version=1,
            runs=runs,
            source_lock_approval="현재 검토 B03 5개 소스 exact revision과 기존 C1/AppState 검사 갱신만 승인",
            source_lock_manifest="../source-lock-review.json",
            pending_approval="P0 OfflineStore.recoveryLineageFingerprint 한정 hash hook 및 exact source-lock 확장",
            coverage="PARTIAL — 실제 Frozen lineage SHA 입력 미관측",
            checks={
                name: json.loads((OUT / (name + ".json")).read_text())
                for name in [
                    "approved-backend-full",
                    "approved-flutter-full",
                    "approved-analyze",
                    "approved-build",
                    "approved-frontend",
                    "approved-ruff",
                    "approved-format",
                    "approved-compileall",
                ]
                if (OUT / (name + ".json")).exists()
            },
            verdict="BLOCKED — 별도 P0 source-lock 승인 필요",
        ),
    )
    print(
        json.dumps(dict(runs=runs, changed_tracked=list(changed)), ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
