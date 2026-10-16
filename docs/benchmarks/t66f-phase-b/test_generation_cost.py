"""D2 finalization 작업량을 HTTP 전송 비용과 분리하여 독립 관찰한다."""

import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
from uuid import uuid4

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
OUT = Path(
    os.environ.get("F_GENERATION_OUTPUT", "/tmp/mn-t66f-phase-b/generation-cost")
)


@pytest.mark.parametrize("history", [7, 256])
def test_real_generation_mutation_cost_and_independent_complete_oracle(history):
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / (str(history) + ".log")).open("w") as log:
        p = subprocess.Popen(
            [str(ROOT / ".venv/bin/python"), str(HERE / "server.py"), str(history)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=log,
            text=True,
        )

        def command(value):
            p.stdin.write(json.dumps(value) + "\n")
            p.stdin.flush()
            return json.loads(p.stdout.readline())

        try:
            init = json.loads(p.stdout.readline())
            with (
                httpx.Client(verify=False, timeout=15) as client,
                sqlite3.connect(init["owned_db_path"]) as db,
            ):
                before = {r[0] for r in db.execute("SELECT hash FROM sync_objects")}
                before_revision = db.execute(
                    "SELECT revision FROM authoritative_state_revision"
                ).fetchone()[0]
                generation = command(
                    dict(command="mutate", title="generation cost changed")
                )
                after = {r[0] for r in db.execute("SELECT hash FROM sync_objects")}
                assert generation["new_immutable_objects"] == len(after - before)
                assert (
                    db.execute(
                        "SELECT revision FROM authoritative_state_revision"
                    ).fetchone()[0]
                    == before_revision + 1
                )
                assert not db.execute("PRAGMA foreign_key_check").fetchall()
                response = client.post(
                    init["origin"] + "/api/sync/v1/observations",
                    headers={"Authorization": "Bearer " + init["token"]},
                    json=dict(
                        protocol=1, request_id=str(uuid4()), base=None, inline_bytes=0
                    ),
                )
                assert response.status_code == 201, response.text
                current = command(dict(command="oracle"))
                spec = importlib.util.spec_from_file_location(
                    "phase_b_independent_graph",
                    ROOT / "docs/benchmarks/t66e3-audit/oracle.py",
                )
                oracle = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(oracle)
                closure, rows, edges = oracle.graph(current)
                target = current["manifest"]["target"]
                facts = oracle.facts(target, rows)
                assert oracle.patricia(target, facts) == target["index_ref"]
                old = {o["ref"]["hash"] for o in init["fixture"]["objects"]}
                table_queries = {
                    sql: count
                    for sql, count in generation["sql_trace"].items()
                    if any(
                        "FROM " + table in sql
                        for table in ["ledger_entries", "cash_flows", "monthly_panels"]
                    )
                }
                record = dict(
                    history=history,
                    backend_db_files={
                        label: Path(init["owned_db_path"] + suffix).stat().st_size
                        if Path(init["owned_db_path"] + suffix).exists()
                        else 0
                        for label, suffix in [
                            ("main", ""),
                            ("wal", "-wal"),
                            ("shm", "-shm"),
                        ]
                    },
                    fixture_sync_root=init["fixture"]["manifest"]["target"][
                        "sync_root"
                    ],
                    graph_objects=len(closure),
                    changed_transfer_objects=len(closure - old),
                    reused_transfer_objects=len(closure & old),
                    generation=generation,
                    financial_table_queries=table_queries,
                    edges=edges,
                    facts=len(facts),
                    independent_complete_root=target["index_ref"],
                )
                (OUT / (str(history) + ".json")).write_text(
                    json.dumps(record, ensure_ascii=False, indent=2)
                )
        finally:
            if p.poll() is None:
                p.stdin.write('{"command":"exit"}\n')
                p.stdin.flush()
                p.communicate(timeout=30)
