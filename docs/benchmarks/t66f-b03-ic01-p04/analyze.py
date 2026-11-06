"""고정된 E1 보조 비교와 독립 byte oracle를 분석한다. tail 실행으로 승격하지 않는다."""

import json
from pathlib import Path
import statistics
from prepare import OUT, connect


def canonical(value):
    # This corpus uses supported C1 scalars; no floats or isolated surrogates.
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()


def feed_bytes(kind, payload):
    return len(b"money-note.sync.v1/" + kind.encode("ascii") + b"\0" + payload)


plan = json.loads((OUT / "clone-plan.json").read_text())
records = json.loads((OUT / "component-results.json").read_text())
samples = [r for r in records if r["repeat"] >= 0]
assert len(samples) == 8
target = plan["manifest"]["target"]
version_bytes = len(canonical(target["versions"]))
view = dict(target)
view.pop("sync_root")
manifest_bytes = len(canonical(plan["manifest"]))
body_bytes = 0
hash_bytes = 0
hash_calls = 0
fact_key_calls = 0
with connect(Path(plan["source"])) as db:
    for entry in plan["entries"]:
        raw = db.execute(
            "SELECT body FROM objects WHERE hash=?", (entry["hash"],)
        ).fetchone()[0]
        assert len(raw) == int(entry["bytes"])
        value = json.loads(raw)
        assert canonical(value) == raw
        body_bytes += len(raw)
        hash_bytes += feed_bytes(entry["kind"], raw)
        hash_calls += 1
        if entry["kind"] == "index-leaf":
            for fact in value["facts"]:
                hash_bytes += feed_bytes("fact-key", canonical(fact["key"]))
                hash_calls += 1
                fact_key_calls += 1
batches = 32
hash_bytes += batches * feed_bytes("view", canonical(view))
hash_calls += batches
span_bytes = (
    body_bytes + 2048 * version_bytes + batches * (manifest_bytes + 3 * version_bytes)
)
span_calls = 2048 * 2 + batches * 4
oracle = {
    "cohort_objects": 2048,
    "cohort_body_bytes": body_bytes,
    "version_bytes": version_bytes,
    "manifest_bytes": manifest_bytes,
    "fact_key_hash_calls": fact_key_calls,
    "view_hash_calls": batches,
    "hash_input_bytes": hash_bytes,
    "hash_calls": hash_calls,
    "validation_submitted_and_completed_bytes": span_bytes,
    "validation_calls": span_calls,
    "checksum_bytes": batches * manifest_bytes,
    "staging_links_attempted_effective_committed_text_bytes": 2048 * 100,
    "new_immutable_objects": 0,
    "method": "Independent native body lengths + literal framed buffers, native bound string lengths; performed after measurement. Three metadata version spans arise from ReleaseContract.verify and both CacheNamespace.verifyTarget operands. No product counter used as expected value.",
}
for r in samples:
    assert r["collector_closed"]
    if not r["logical"]:
        assert r["primitive"] is None and r["sql"] is None
        continue
    p = r["primitive"]
    assert int(p["e2/objectHash/hashInputBytes"]) == hash_bytes
    assert int(p["e2/objectHash/calls"]) == hash_calls
    assert int(p["e2/c1/submittedBytes"]) == span_bytes
    assert int(p["e2/c1/completedBytes"]) == span_bytes
    assert int(p["e2/c1/calls"]) == span_calls
    assert int(p["e2/checksum/hashInputBytes"]) == batches * manifest_bytes
    assert r["local_new_staging_text_bytes"] == 204800
for repeat in range(2):
    b = next(r for r in samples if r["mode"] == "B" and r["repeat"] == repeat)
    d = next(r for r in samples if r["mode"] == "D" and r["repeat"] == repeat)
    assert (
        b["primitive"] == d["primitive"]
        and b["sql"] == d["sql"]
        and b["work"] == d["work"]
    )
groups = {m: [r for r in samples if r["mode"] == m] for m in "ABCD"}
summary = {
    m: {
        "wall_s": [r["wall_us"] / 1e6 for r in rs],
        "median_wall_s": statistics.median(r["wall_us"] / 1e6 for r in rs),
        "cpu_100Hz_s": [r["cpu_ticks_100Hz"] / 100 for r in rs],
        "population_p95": None,
    }
    for m, rs in groups.items()
}
pairs = {}
for a, b, label in [
    ("A", "B", "logical_without_timing"),
    ("C", "D", "logical_with_timing"),
    ("A", "C", "timing_without_logical"),
    ("B", "D", "timing_with_logical"),
]:
    values = [
        (groups[b][i]["wall_us"] - groups[a][i]["wall_us"]) / 1e6 for i in range(2)
    ]
    pairs[label] = {
        "difference_s": values,
        "median_difference_s": statistics.median(values),
        "consistent_positive": all(v > 0 for v in values),
    }
result = {
    "scope": "E1 reuse component in original-size clones; NOT D3 HTTP/E2 acquisition tail",
    "four_mode_repetitions": 2,
    "smoke_pairs": 1,
    "matched_actual_tail_pairs": 0,
    "actual_tail_status": "NOT RUN",
    "new_full_100k_cold_attempts": 0,
    "modes": summary,
    "paired_differences": pairs,
    "oracle": oracle,
    "counter_equality_B_D": "PASS",
    "independent_byte_calibration": "PASS",
    "database_equality": json.loads((OUT / "clone-final-equivalence.json").read_text())[
        "status"
    ],
    "caution": "Bidirectional wall differences in n=2 do not isolate a stable slowdown. CPU may exceed wall with multithread runtime; no exclusive allocation, fsync or GC cause is measured. Callback body timing is not the incremental cost of timing it.",
}
(OUT / "component-analysis.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2) + "\n"
)
print(
    json.dumps(
        {"calibration": "PASS", "paired_differences": pairs, "actual_tail": "NOT RUN"}
    )
)
