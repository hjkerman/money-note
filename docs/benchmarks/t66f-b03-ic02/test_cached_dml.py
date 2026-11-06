"""DDL 이전에 실행한 동일 bound DML의 재사용을 literal ledger와 대조한다."""

from contextlib import closing
import importlib.util
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
spec = importlib.util.spec_from_file_location(
    "ic02_cached_dml", ROOT / "docs/benchmarks/t66f-b03/counters.py"
)
cost = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cost)


def test_cached_bound_insert_survives_alter_and_drop_without_duplicate_events():
    states = []
    statement = "INSERT INTO payload(k,b) VALUES(?,?)"
    for enabled in (False, True):
        collector = cost.Collector()
        factory = cost.observed_factory() if enabled else sqlite3.Connection
        with closing(
            sqlite3.connect(":memory:", isolation_level=None, factory=factory)
        ) as db:
            with collector.stage("generation"):
                db.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
                db.execute(statement, ("a", b"1"))
                db.execute("ALTER TABLE payload ADD COLUMN extra BLOB DEFAULT x'0203'")
                db.execute(statement, ("b", b"456"))
                db.execute("DROP TABLE payload")
                db.execute("CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)")
                db.execute(statement, ("c", b"78"))
            states.append(db.execute("SELECT k,b FROM payload").fetchall())
        if enabled:
            # Three native row events: 1B, then 3B+2B DEFAULT, then 2B.
            # ALTER's synthesized default on the old row is not another INSERT.
            for outcome in ("attempted", "effective", "committed"):
                assert (
                    collector.values[f"generation/payload/INSERT/{outcome}/blob_bytes"]
                    == 8
                )
            assert collector.values["generation/payload/INSERT/effective/rows"] == 3
    assert states == [[("c", b"78")], [("c", b"78")]]
