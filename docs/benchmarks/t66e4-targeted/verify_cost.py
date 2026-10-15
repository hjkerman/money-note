"""유한 두 규모의 독립 SQL 계수 oracle. Production big-O/latency 약속이 아니다."""
import json
from pathlib import Path
import sys


def main():
    rows = json.loads(Path(sys.argv[1]).read_text())
    if isinstance(rows, dict):
        rows = rows["scales"]
    assert len(rows) == 2
    warm = []
    for row in rows:
        phases = {phase["name"]: phase for phase in row["phases"]}
        for name in ("warm_frozen", "repeated_frozen", "unrelated_accepted_change",
                     "post_fallback_warm", "fresh_handle_warm"):
            phase = phases[name]
            for key in ("raw_rows", "raw_nodes", "index_nodes", "pin_insert", "pin_delete",
                        "pin_update", "full_recoveries", "full_frozen_recoveries"):
                assert phase[key] == 0, (row["history"], name, key, phase[key])
            count = (len(phase["object_identities"]) if "object_identities" in phase
                     else phase["distinct_objects"])
            assert count == 2
        for name in ("cold_frozen", "external_commit_full_fallback", "fresh_handle_full_recovery"):
            phase = phases[name]
            assert phase["full_frozen_recoveries"] == 1
            assert phase["raw_nodes"] > 0 and phase["index_nodes"] > 0
        pins = phases["frozen_pin_handoff"]
        assert pins["frozen_insert"] == pins["frozen_update"] == 1
        assert pins["pin_insert"] == pins["pin_delete"] == pins["pin_update"] == 0
        warm.append(phases["warm_frozen"])
    # H/J and the operation are fixed; N changes. This is the binding I25
    # synthetic scaling oracle, not an invented universal exact SQL budget.
    assert rows[0]["required_objects"] < rows[1]["required_objects"]
    for key in ("sql_statements", "returned_rows", "object_body_bytes"):
        assert warm[0][key] == warm[1][key], key
    print(json.dumps({"status": "PASS", "scales": len(rows),
                      "warm_sql_statements": warm[0]["sql_statements"],
                      "warm_object_body_bytes": warm[0]["object_body_bytes"]}))


if __name__ == "__main__":
    main()
