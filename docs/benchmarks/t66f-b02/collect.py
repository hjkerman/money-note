"""완료된 B02 자료를 SHA와 결합한다. 큰 DB 자체는 commit하지 않는다."""

from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import platform
import shutil
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
BASE = Path("/tmp/mn-b02")
OUT = HERE / "evidence"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    measured = []
    for n in [1000, 5000, 10000, 12000, 15000, 20000, 24900, 25000, 50000, 100000]:
        folder = BASE / str(n)
        result = json.loads((folder / "result.json").read_text())
        assert result["status"] == "PASS"
        (OUT / str(n)).mkdir(exist_ok=True)
        for name in [
            "result.json",
            "manifest-g1.json",
            "manifest-g2.json",
            "layout.json",
            "delta-analysis.json",
        ]:
            if (folder / name).exists():
                shutil.copyfile(folder / name, OUT / str(n) / name)
        g = result["g1"]
        measured.append(
            dict(
                n=n,
                objects=g["objects"],
                amplification=g["objects"] / n,
                delta=result["delta_new_reachable_objects"],
                payload=g["canonical_bytes"],
                edges=g["edges"],
                objects_sqlite_sha256=sha(folder / "objects.sqlite"),
                offline_input_bytes=(folder / "objects.sqlite").stat().st_size,
            )
        )
    for file in BASE.iterdir():
        if file.is_file() and file.suffix in [".json", ".txt", ".log"]:
            shutil.copyfile(file, OUT / file.name)
    logs = [
        "generations.log",
        "probes.log",
        "probes-jit.log",
        "probes-jit-2.log",
        "probes-jit-3.log",
        "simulations.log",
        "store.log",
        "probe-initial-serialization-error.log",
        "compile.log",
        "compile-2.log",
        "backend-targeted.log",
        "backend-targeted.xml",
        "flutter-targeted.jsonl",
        "flutter-targeted.err",
        "profile.jsonl",
        "profile.err",
        "npm-build.log",
    ]
    for name in logs:
        file = Path("/tmp/mn-b02-" + name)
        if file.exists():
            with gzip.GzipFile(str(OUT / (name + ".gz")), "wb", mtime=0) as zipped:
                zipped.write(file.read_bytes())
    store_report = json.loads((BASE / "probe-store-15000.json").read_text())
    assert store_report["status"] == "LOCAL_METADATA_BUDGET"
    file = next((BASE / "actual-client-store").rglob("*.sqlite"))
    with closing(sqlite3.connect(f"file:{file}?mode=ro", uri=True)) as db:
        counts = {
            t: db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            for t in [
                "objects",
                "refs",
                "edges",
                "staging",
                "staging_roots",
                "staging_objects",
            ]
        }
        metadata = (
            counts["objects"] * 192
            + counts["refs"] * 128
            + counts["edges"] * 256
            + counts["staging_roots"] * 128
            + counts["staging_objects"] * 128
            + db.execute("SELECT sum(length(manifest)+256) FROM staging").fetchone()[0]
        )
        usage = db.execute("SELECT * FROM usage").fetchone()
        assert usage[4] == metadata and metadata <= 32 * 1024**2
        manifest = json.loads((BASE / "15000/manifest-g1.json").read_text())
        ref = manifest["target"]["control_ref"]
        kind, body = db.execute(
            "SELECT kind,body FROM objects WHERE hash=?", (ref["hash"],)
        ).fetchone()
        assert (
            hashlib.sha256(
                b"money-note.sync.v1/" + kind.encode() + b"\0" + body
            ).hexdigest()
            == ref["hash"]
        )
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        checked = 0
        for digest, kind, body in db.execute("SELECT hash,kind,body FROM objects"):
            assert (
                hashlib.sha256(
                    b"money-note.sync.v1/" + kind.encode() + b"\0" + body
                ).hexdigest()
                == digest
            )
            checked += 1
        write(
            OUT / "store-durable-oracle.json",
            dict(
                status="PASS",
                counts=counts,
                usage=list(usage),
                metadata_independent=metadata,
                independent_hash_checked=checked,
                preserved_control_ref=ref,
                accepted_table_exists=bool(
                    db.execute(
                        "SELECT 1 FROM sqlite_master WHERE name='accepted'"
                    ).fetchall()
                ),
                complete_graph=False,
                database_sha256=sha(file),
            ),
        )
    with closing(sqlite3.connect(file)) as db:
        db.execute("BEGIN IMMEDIATE")
        db.rollback()
    env = dict(
        platform=platform.platform(),
        python=platform.python_version(),
        python_sqlite=sqlite3.sqlite_version,
        cpu=next(
            (
                line.split(":", 1)[1].strip()
                for line in Path("/proc/cpuinfo").read_text().splitlines()
                if line.startswith("model name")
            ),
            None,
        ),
        meminfo=Path("/proc/meminfo").read_text().splitlines()[:3],
        filesystem=subprocess.check_output(
            ["findmnt", "-T", "/tmp", "-n", "-o", "FSTYPE,OPTIONS"], text=True
        ).strip(),
        sample_policy="warmup 없는 단회 기술 표본; median/p95 아님",
        android_device_test=False,
        jit_compiler_included_in_rss=True,
        concurrent_experiments=True,
    )
    write(OUT / "environment.json", env)
    write(
        OUT / "summary.json",
        dict(
            grid=measured,
            product_limit_raised=False,
            large_full_http_acquisition_executed=False,
            android_memory_proven=False,
            logical_byte_campaign_complete=False,
        ),
    )
    write(
        OUT / "manifest.json",
        {
            str(p.relative_to(OUT)): dict(bytes=p.stat().st_size, sha256=sha(p))
            for p in sorted(OUT.rglob("*"))
            if p.is_file() and p.name != "manifest.json"
        },
    )
    print("독립 자료와 SHA 결합 완료:", len(measured), "graph 지점")


if __name__ == "__main__":
    main()
