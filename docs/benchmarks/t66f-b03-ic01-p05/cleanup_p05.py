"""P05 등록 대상만 1회 정리한다. 디렉터리/기존 파일/retained DB를 지우지 않는다."""

import json
import os
from pathlib import Path
import subprocess
import time

from artifact_handoff import digest, verify_artifact

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "evidence"
if (OUT / "cleanup-manifest.json").exists():
    raise SystemExit("기존 cleanup 영수증이 있으므로 재실행하지 않음")
start = json.loads((OUT / "starting-state.json").read_text())
canonical = OUT / "run-final-format/artifacts/tls-normal"
verified = verify_artifact(canonical)
previous_cache = json.loads((OUT / "flutter-cache-before.json").read_text())
candidates = []
for file in (ROOT / "mobile/build/test_cache").rglob("*"):
    relative = str(file.relative_to(ROOT))
    if file.is_file() and relative not in previous_cache:
        candidates.append(
            (
                file,
                "Flutter test compiler cache",
                "P05 실행 직전 cache inventory에 없고 완료된 두 Flutter 명령에서 생성",
            )
        )
for parent in ("/tmp/mn-b03-rollback-BYWZFE", "/tmp/mn-b03-e1-BQDLAE"):
    for file in Path(parent).rglob("*"):
        if file.is_file():
            candidates.append(
                (
                    file,
                    "disposable SQLite calibration store",
                    "P05 시작 후 ctime; segmented_logical_cost_test.dart:218/294 createTemp와 새 시험 실행 대응",
                )
            )
for file in OUT.rglob("synthetic-key.pem"):
    candidates.append(
        (
            file,
            "ephemeral synthetic TLS key",
            "P05 새 evidence 경로의 종료된 TLS test child 생성; artifact manifest에 credential/key 없음",
        )
    )
rows = []


def available():
    value = os.statvfs(ROOT)
    return value.f_frsize * value.f_bavail


initial = available()
for path, kind, ownership in candidates:
    stat = path.lstat()
    row = dict(
        path=str(path),
        type=kind,
        ownership=ownership,
        created_after_start=stat.st_ctime_ns >= start["timestamp_ns"],
        size=stat.st_size,
        allocated=stat.st_blocks * 512,
        device=stat.st_dev,
        inode=stat.st_ino,
        sha256=digest(path),
        no_longer_required="시험 결과·source·독립 oracle·검증된 backend 보존본이 남고 모든 관련 runner 종료",
        retained_substitute=str(canonical),
        result="PRESERVED",
    )
    if not row["created_after_start"] or path.is_symlink():
        row["reason"] = "소유권 불명확 또는 symlink"
        rows.append(row)
        continue
    check = subprocess.run(["fuser", str(path)], text=True, capture_output=True)
    row["active_process_check"] = dict(
        command=["fuser", str(path)],
        returncode=check.returncode,
        reported_pids=check.stdout.strip(),
        stderr=check.stderr.strip(),
    )
    if check.returncode != 1 or check.stdout.strip() or check.stderr.strip():
        row["reason"] = "사용 여부를 확정할 수 없어 보존"
        rows.append(row)
        continue
    # 삭제 직전 동일 파일 여부를 다시 검증한다. parent나 wildcard 삭제는 없다.
    immediately = path.lstat()
    assert (
        immediately.st_dev,
        immediately.st_ino,
        immediately.st_size,
        immediately.st_mtime_ns,
    ) == (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    assert not path.is_symlink()
    before = available()
    path.unlink()
    after = available()
    row.update(
        result="DELETED",
        verification_unlinked=not path.exists(),
        timestamp_ns=time.time_ns(),
        observed_available_delta=after - before,
    )
    rows.append(row)
manifest = dict(
    schema_version=1,
    scope="P05 추가 opportunistic 정리. 기존 테스트 기본 sandbox cleanup는 lifecycle manifest로 별도 검증; 총 생성 I/O 수치가 아님",
    retained_backend_sha256=verified["snapshot_sha256"],
    retained_backend_integrity=verified["identity"]["integrity"],
    candidates=rows,
    created_registered=len(rows),
    created_registered_allocated=sum(r["allocated"] for r in rows),
    deleted_count=sum(r["result"] == "DELETED" for r in rows),
    deleted_allocated=sum(r["allocated"] for r in rows if r["result"] == "DELETED"),
    disk_available_before=initial,
    disk_available_after=available(),
    observed_disk_reclaimed=available() - initial,
    pre_existing_files_deleted=0,
    original_sqlite_artifacts="P05에서 접근·삭제하지 않음; 재부팅 후 원 경로 부재",
    retained_canonical_backend=str(canonical),
    candidates_requiring_approval=[r["path"] for r in rows if r["result"] != "DELETED"],
    directories_deleted=0,
)
with open(OUT / "cleanup-manifest.json", "x") as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
    stream.write("\n")
print(
    json.dumps(
        {
            k: manifest[k]
            for k in (
                "created_registered",
                "deleted_count",
                "deleted_allocated",
                "observed_disk_reclaimed",
                "pre_existing_files_deleted",
                "candidates_requiring_approval",
            )
        }
    )
)
