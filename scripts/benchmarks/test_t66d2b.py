from pathlib import Path

import pytest

from scripts.benchmarks.t66d2b import ROOT, check_output, summarize


def test_compact_summary_preserves_values_and_distinguishes_sql_from_objects():
    samples = [{"total_ms": 3, "object_writes": 1, "sql": {"SELECT": 10}},
               {"total_ms": 7, "object_writes": 0, "sql": {"SELECT": 12, "INSERT": 2}}]
    workload = dict(samples=samples, warmups=3, median_ms=5, p95_ms=7,
                    ordinary_ledger_scans=[], unique_query_plans=["synthetic plan"])
    raw = dict(seed=662600, datasets={"376": dict(rows=376, workloads={"card": workload})})
    compact = summarize(raw)
    result = compact["datasets"]["376"]["workloads"]["card"]
    assert result["median_metrics"] == {"total_ms": 5, "object_writes": .5}
    assert result["median_sql_calls"] == {"SELECT": 11, "INSERT": 1}
    assert result["sample_count"] == 2 and result["ordinary_ledger_scans"] == []
    assert "samples" not in result and "unique_query_plans" not in result
    assert raw["datasets"]["376"]["workloads"]["card"]["samples"] == samples


def test_output_scope_and_no_overwrite(tmp_path):
    check_output(tmp_path / "new.json")
    for path in (ROOT / "bundle.json", Path("/var/lib/synthetic.json"), tmp_path):
        with pytest.raises(ValueError):
            check_output(path)


def test_writer_plan_classification_includes_aliases_not_zero_row_schema_probes():
    from scripts.benchmarks.t66d2b_writers import historical_scans
    assert historical_scans("SELECT * FROM ledger_entries LIMIT 0", ["SCAN ledger_entries"]) == []
    assert historical_scans("SELECT * FROM ledger_entries l", ["SCAN l"]) == ["SCAN l"]
    assert historical_scans("SELECT * FROM cash_flows", ["SCAN cash_flows"]) == ["SCAN cash_flows"]
    assert historical_scans("SELECT * FROM sync_objects", ["SCAN sync_objects"]) == ["SCAN sync_objects"]
    assert historical_scans("SELECT * FROM ledger_entries WHERE id=?", ["SEARCH ledger_entries USING INTEGER PRIMARY KEY"]) == []


def test_writer_returned_row_counter_does_not_change_sqlite_values():
    import sqlite3
    from scripts.benchmarks.t66d2b_writers import CountedCursor
    with sqlite3.connect(":memory:") as conn:
        count = [0]
        cursor = CountedCursor(conn.execute("SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3"), count)
        assert cursor.fetchone() == (1,)
        assert cursor.fetchall() == [(2,), (3,)] and count == [3]
        assert cursor.fetchone() is None and count == [3]
        assert list(CountedCursor(conn.execute("SELECT 'text'"), count)) == [("text",)]
        assert count == [4]
