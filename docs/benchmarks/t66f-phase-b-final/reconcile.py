"""과거 raw trace를 새로 집계한다. 새 runtime 측정으로 표시하지 않는다."""

from collections import Counter
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OLD = ROOT / "docs/benchmarks/t66f-phase-b-continuation"
B02 = ROOT / "docs/benchmarks/t66f-b02-independent"


def load(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == ".gz" else raw)


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def stats(samples):
    return dict(
        n=len(samples),
        median=statistics.median(samples),
        p95=sorted(samples)[math.ceil(0.95 * len(samples)) - 1],
    )


def reconcile_large(n):
    folder = B02 / "evidence" / str(n)
    result = load(folder / "result.json.gz")
    with gzip.open(folder / "server-requests.jsonl.gz", "rt") as stream:
        trace = [json.loads(line) for line in stream]
    assert result["status"] == "PASS_COLD_IDENTICAL_DELTAS_RESTART"
    fixture = result["fixture"]
    assert fixture["raw_rows"]["ledger_entries"] == n
    assert sum(fixture["raw_rows"].values()) == n + 35
    assert fixture["kind_bytes"]["hot"] == 87364
    assert fixture["kind_bytes"]["control"] == 3178
    measured = dict(
        requests=len(trace),
        request_entity_bytes=sum(r["request_bytes"] for r in trace),
        response_entity_bytes=sum(r["response_bytes"] for r in trace),
    )
    original = load(folder / "server-wire-final.json.gz")
    for key, value in measured.items():
        assert value == original[key], (n, key)
    stop = next(
        i for i, r in enumerate(trace) if r.get("manifest") and r["status"] == 200
    )
    cold = trace[: stop + 1]
    good = [r for r in cold if r["path"].endswith("/objects") and r["status"] == 200]
    issued = [r["manifest"] for r in cold if r.get("manifest") and r["status"] == 201]
    assert 1 <= len(issued) <= 3
    assert len({r["target"]["sync_root"] for r in issued}) == 1
    assert sum(r.get("chunks", 0) for r in good) == fixture["objects"]
    assert sum(r.get("decoded_bytes", 0) for r in good) == fixture["canonical_bytes"]
    assert sum(r.get("new_global_hashes", 0) for r in good) == fixture["objects"]
    phases = []
    for phase in result["phases"]:
        work = phase["store_work"]
        if phase["phase"] != "restart_delta":
            assert work.get("full_verifications", 0) == 0
            assert work.get("canonical_full_builds", 0) == 0
            assert work.get("full_raw_rows", 0) == 0
        else:
            # 새 handle recovery는 §18/24/35의 정상 steady-state와 다른 O(N) 경계다.
            assert work["full_recoveries"] == 1
            assert work["full_raw_rows"] == 2 * (n + 35)
        if phase["phase"] == "identical":
            assert phase["transferred_objects"] == 0
            assert phase["http_delta"]["object_requests"] == 0
            assert phase["sequence"] == 1
        else:
            oracle = load(folder / ("independent-" + phase["phase"] + ".json.gz"))
            assert oracle["status"] == "PASS"
            assert phase["transferred_objects"] == phase["expected_new_objects"]
            pins = oracle["current_pins"]
            target = oracle["receipt"]["target"]
            assert len(pins) == 4
            assert {pin["hash"] for pin in pins} == {
                target[key]["hash"]
                for key in ["raw_ref", "index_ref", "hot_ref", "control_ref"]
            }
        phases.append(phase)
    oracle = load(folder / "independent-cold.json.gz")
    assert oracle["reachable_digest"] == fixture["audit_reachable_hash_set_sha256"]
    assert oracle["raw_value_sha256"] == fixture["raw_value_sha256"]
    fresh = load(folder / "fresh-process.json.gz")
    assert fresh["status"] == "PASS" and fresh["old_authority_reused"] is False
    execution = load(B02 / f"execution-{n}.json")
    assert execution["exit_code"] == 0 and execution["external_termination"] is None
    return dict(
        lineage=dict(
            producing_product="1cabf319f0ac2c2069e804b47cb527b55e3374db",
            independent_audit="ae0f37250c8f54893cb2ac5eab1d3c9844a7d983",
            raw_folder=str(folder.relative_to(ROOT)),
            newly_executed=False,
            source_changed_after=False,
        ),
        fixture=fixture,
        all_http=measured,
        all_http_statuses=dict(Counter(str(r["status"]) for r in trace)),
        cold=dict(
            observations=len(issued),
            success_object_requests=len(good),
            all_requests=len(cold),
            all_request_entity_bytes=sum(r["request_bytes"] for r in cold),
            all_response_entity_bytes=sum(r["response_bytes"] for r in cold),
            successful_object_request_bytes=sum(r["request_bytes"] for r in good),
            successful_object_response_bytes=sum(r["response_bytes"] for r in good),
            canonical_payload_bytes=fixture["canonical_bytes"],
            root=issued[0]["target"]["sync_root"],
            independently_inspected_db_bytes=oracle["database_bytes"],
            store_work_observed_from_product=result["cold_store_work"],
        ),
        phases=phases,
        fresh_process=fresh,
        storage_final=dict(
            database_bytes=result["e1_database_bytes"],
            usage=result["usage"],
            wal_bytes=0,
            boundary="cold·delta·restart 후; WAL은 별도 B02 final-state 검사의 관찰값",
        ),
        resource=dict(
            process_peak_rss=result["client_process_rss_peak_bytes"],
            tree_sample_peak=execution["peak_sampled_process_tree_rss"],
            seconds=execution["elapsed_s"],
        ),
        independent_logical_hash_bytes=None,
        independent_logical_validation_bytes=None,
        independent_logical_write_bytes=None,
    )


def reconcile_grid():
    rows = []
    for n in [1000, 5000, 10000, 50000, 100000]:
        raw = load(OLD / f"evidence/grid/{n}.json")
        assert (
            raw["status"] == "PASS" and raw["n"] == n and raw["hot_ledger_rows"] == 105
        )
        phases = {}
        for phase in raw["phases"]:
            samples = phase["samples"]
            assert len(samples) == 20 and raw["warmups"] == 3
            assert all(
                s["status"] == 201
                and s["h_object_sizes"] == {"hot_ref": 87364, "control_ref": 3178}
                for s in samples
            )
            phases[phase["phase"]] = dict(
                total_ns=stats([s["total_ns"] for s in samples]),
                sql=stats([s["counters"]["sql"] for s in samples]),
                returned_rows=stats([s["counters"]["rows_returned"] for s in samples]),
                http_entity_bytes=stats([s["http_entity_bytes"] for s in samples]),
            )
        compression = raw["compression"]
        for algorithm in compression["algorithms"].values():
            actual = stats(algorithm["samples_ns"])
            assert all(actual[k] == algorithm["latency_ns"][k] for k in actual)
        rows.append(
            dict(
                n=n,
                historical_ledger_rows=n - 105,
                ledger_current_rows=105,
                other_reference_rows=35,
                hot_bytes=87364,
                control_bytes=3178,
                d_unchanged=0,
                d_card_cash=1,
                objects=raw["independent_graph"]["objects"],
                canonical_bytes=raw["independent_graph"]["bytes"],
                backend_historical_phases=phases,
                compression_historical=compression,
                current_full_cost_status="INCONCLUSIVE",
                logical_hash_bytes=None,
                logical_validation_bytes=None,
                logical_write_bytes=None,
                backend_samples_are_fresh=False,
                small_client_profile="current ledger 1행 별도 fixture; current 105행 profile과 비용 곡선을 합치지 않음. H 전체를 1/105로 정의하지 않음"
                if n <= 10000
                else None,
            )
        )
    return rows


def coverage():
    old = load(OLD / "coverage-final.json")
    categories = {
        "A": "VERIFIED — REUSABLE INDEPENDENT EVIDENCE",
        "B": "VERIFIED — REGRESSION REQUIRED",
        "C": "UNVERIFIED — MANDATORY F GATE",
        "D": "DEFERRED — R1",
        "E": "REQUIRED BUT ENVIRONMENT UNAVAILABLE",
        "F": "CONTRACT AMBIGUITY",
        "G": "DEFERRED — ACTIVATION / DEVICE GATE",
    }
    rows = []
    for group in ["sections", "invariants", "implementation_proofs", "negative_plan"]:
        for row in old[group]:
            entry = dict(row)
            entry["group"] = group
            entry["prior_category"] = row["classification"]
            entry["prior_audited_product"] = row["audited_product"]
            entry["audited_product"] = "1cabf319f0ac2c2069e804b47cb527b55e3374db"
            entry["protocol_clause"] = {
                "sections": "§" + row["id"][1:],
                "invariants": "§36/" + row["id"],
                "implementation_proofs": "§38/" + row["id"],
                "negative_plan": "§37/" + row["id"],
            }[group]
            entry["evidence_still_applicable"] = (
                "명시된 correctness 범위 유효; C1/fetch/transfer 변경 이전 비용은 현재 실측으로 전용 금지"
            )
            entry["prior_evidence"] = [
                row["prior_evidence"],
                "docs/benchmarks/t66f-phase-b-continuation/coverage-final.json",
                "docs/benchmarks/t66f-b02-independent/summary.json",
            ]
            entry["measurement_method"] = (
                "기존 독립 raw evidence 재대조·tracked SHA 2251개 보존·현재 전체 회귀; 원 검사 범위를 확대하지 않음"
            )
            entry["final_acceptance"] = (
                row["requirement"]
                + " — 해당 규범의 MUST/MUST NOT과 원 oracle 기대값 충족; 범위 밖 증거를 새 PASS로 확대하지 않음"
            )
            entry["additional_evidence_required"] = row["remaining_action"]
            entry["final_status"] = (
                "VERIFIED — 해당 기존 검사 범위; 전수 새 독립 주입 주장이 아님"
                if row["status"] == "A"
                else "INCONCLUSIVE"
            )
            if row["id"] in {"S30"}:
                entry.update(
                    status="A",
                    final_status="VERIFIED — B02 큰 cold continuation·fresh process; 모든 실패 조합의 새 전수 검사는 아님",
                    additional_evidence_required="기존 failure/authority 회귀",
                )
            if row["id"] in {"S34", "S35", "S38", "I25", "P7", "P12"}:
                entry.update(
                    status="C",
                    final_status="INCONCLUSIVE",
                    additional_evidence_required="현재 소스의 고정 H/D 5개 N no-change/card/cash: 전층 hash/validation/write bytes·정상 full-N 작업 0·median/p95; 기존 부분 증거는 유지",
                )
            if row["id"] in {"S26", "P8"}:
                entry.update(
                    status="E",
                    final_status="REQUIRED BUT MISSING — 실제 Android VFS/I/O·power-loss; §26 명시 activation blocker. isolated Phase B PASS 이전 배치 시점은 별도 모호성 행 참조",
                    additional_evidence_required="지원된 실제 Android driver/pragmas/native fence/I/O·전원 손실 증거",
                )
            if row["id"] in {"S31", "S33", "I23", "P10", "N31", "N32"}:
                entry.update(
                    status="D",
                    final_status="DEFERRED — R1; §34 전체 F exit dependency는 미충족",
                    additional_evidence_required="별도 승인된 R1 구현·독립 검증",
                )
            if row["id"] in {"P9", "P11"}:
                entry.update(
                    status="C",
                    final_status="INCONCLUSIVE — legacy/host 부분 증거만 유효; R1·activation 하위 의무는 분리 행에 보존",
                    additional_evidence_required="원 행의 legacy parity/retention/storage-pressure 의무 및 별도 R1 migration·backup 의무를 모두 충족",
                )
                entry["subrequirements"] = {
                    "현재_legacy_host_범위": "VERIFIED — REUSABLE INDEPENDENT EVIDENCE; 원 v7/v4/B/J/materialization·standalone backup 의미·host pressure 회귀 범위",
                    "미완료_별도_R1_범위": "DEFERRED — R1; migration/rollback 또는 R1 artifact/backup/storage-exhaustion; 전체 F dependency 미충족",
                    "부모_행_판정": "원 mixed 행 INCONCLUSIVE 보존. R1 미완료를 새 D/E 제품 결함으로 재분류하지 않음",
                }
            entry["classification"] = categories[entry["status"]]
            rows.append(entry)
    extras = [
        (
            "COST-HASH",
            "§35/I25",
            "C",
            "D1–E4 실제 hash preimage·반복 횟수; Python C1 소형 계측만 PARTIAL",
        ),
        (
            "COST-VALIDATE",
            "§23/35/I25",
            "C",
            "전체 decoder/typed/raw/facts/receipt의 실제 validation 입력; 소형 JSON 경계만 PARTIAL",
        ),
        (
            "COST-WRITE",
            "§24/25/35/I25",
            "C",
            "object/edge/stage/manifest/receipt/pointer/pin 전체 write; 소형 INSERT BLOB/TEXT만 PARTIAL",
        ),
        (
            "COST-MATCHED-GRID",
            "§35",
            "C",
            "N=1k/5k/10k/50k/100k의 같은 H no-change/card/cash 전층 grid; 다른 H 자료를 합치지 않음",
        ),
        (
            "COST-MEDIAN-P95",
            "§35",
            "C",
            "현재 전층 matched workload의 median/p95; 이전 3+20 및 cold n=1 범위 구별",
        ),
        (
            "COST-RESOURCE",
            "§35",
            "C",
            "큰 HOST cold 범위 유효; 전체 workload 자원·temporary peak 등 관측 범위 명시 필요",
        ),
        (
            "E4-FROZEN-LARGE",
            "§22/29/31",
            "D",
            "큰 accepted read는 검증; >25MiB native legacy installation 확대는 R1 budget/activation 소유. 임의로 limit를 높이지 않음",
        ),
        (
            "DEVICE-PERFORMANCE",
            "§35/§38.12",
            "G",
            "절대 latency·지원 단말 memory/performance는 post-T6.6. HOST로 대체하지 않음",
        ),
        (
            "DEVICE-F-STAGE",
            "§26/34/§38.8",
            "F",
            "Android proof의 명시 rollout 차단은 명확하나 isolated Phase B PASS 이전인지 별도 명문 없음. 전체 F proof 완료 주장은 불가",
        ),
        (
            "R1-F-DEPENDENCY",
            "§31/33/34",
            "D",
            "R1 별도 소유이나 §34에서 F 앞의 dependency다. 전체 F SATISFIED로 제거할 수 없음",
        ),
        (
            "MIME-DIAGNOSTIC",
            "§4/15",
            "A",
            "valid JSON + text/html 거부 진단의 역사 FAIL 보존. binding MIME 거부 의무 없음",
        ),
        (
            "B01-CLOSURE",
            "§17; 원 strict test",
            "B",
            "5초 test-local lock budget 및 [201]*4+[429] strict assertion; 전체 backend 회귀",
        ),
        (
            "B02-CLOSURE",
            "§18/25/35",
            "A",
            "50k/100k real D→E·delta·fresh process raw evidence 재대조; 전체 비용 PASS와 구별",
        ),
    ]
    for identity, clause, status, description in extras:
        rows.append(
            dict(
                id=identity,
                group="final_gates",
                protocol_clause=clause,
                requirement=description,
                status=status,
                classification=categories[status],
                original_status="이전 부분 증거/미확인 항목",
                prior_evidence=[
                    "docs/t66f-phase-b-continuation.md",
                    "docs/t66f-b02-independent-targeted-audit.md",
                ],
                audited_product="1cabf319f0ac2c2069e804b47cb527b55e3374db",
                evidence_still_applicable="범위별로만 유효",
                additional_evidence_required=description,
                measurement_method="현재 source inspection 및 raw evidence 재집계",
                final_acceptance=description,
                final_status="VERIFIED"
                if status == "A"
                else "DEFERRED"
                if status in {"D", "G"}
                else "INCONCLUSIVE",
            )
        )
    assert len(rows) == 123 and len({r["id"] for r in rows}) == 123
    return dict(
        categories=categories,
        rows=rows,
        phase_b="INCONCLUSIVE",
        overall_f="NOT SATISFIED",
        no_binding_requirement_dropped=True,
    )


def main():
    large = {str(n): reconcile_large(n) for n in [50000, 100000]}
    write("evidence/reconciled-large.json", large)
    grid = reconcile_grid()
    write("evidence/five-point-grid.json", grid)
    accepted_reads = {}
    for n in [50000, 100000]:
        path = (
            ROOT
            / f"docs/benchmarks/t66f-b02-a02-correction/http-{n}-post-reads.json.gz"
        )
        raw = load(path)
        assert raw["reads"] == 20
        assert raw["hot_control_hashes_match_backend_roots"] is True
        assert (
            raw["pin_rows_unchanged"] is True
            and raw["legacy_pending_bytes_unchanged"] is True
        )
        work = raw["work"]
        assert work["object_reads"] == 80
        assert all(
            work[key] == 0
            for key in [
                "full_recoveries",
                "full_verifications",
                "canonical_full_builds",
                "transactions",
                "pin_deletes",
            ]
        )
        accepted_reads[str(n)] = dict(
            raw=raw,
            source=str(path.relative_to(ROOT)),
            producing_commit="1cabf319f0ac2c2069e804b47cb527b55e3374db",
            boundary="구현자 원시 측정의 현재 독립 검토; work는 구현 counter. B02 독립 실행과 합치지 않음",
            independent_hash_or_validation_bytes=None,
        )
    write("evidence/reviewed-large-accepted-reads.json", accepted_reads)
    matrix = coverage()
    write("coverage.json", matrix)
    with (HERE / "coverage.csv").open("w") as stream:
        fields = [
            "id",
            "protocol_clause",
            "requirement",
            "original_status",
            "prior_evidence",
            "audited_product",
            "evidence_still_applicable",
            "additional_evidence_required",
            "measurement_method",
            "final_acceptance",
            "classification",
            "final_status",
        ]
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(matrix["rows"])
    used = [OLD / "coverage-final.json"] + list((OLD / "evidence/grid").glob("*.json"))
    used += [
        p for n in [50000, 100000] for p in (B02 / "evidence" / str(n)).glob("*.gz")
    ]
    used += [
        ROOT / f"docs/benchmarks/t66f-b02-a02-correction/http-{n}-post-reads.json.gz"
        for n in [50000, 100000]
    ]
    write(
        "evidence/reused-evidence-sha256.json",
        {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in used
        },
    )
    print(
        json.dumps(
            dict(
                large_raw_reconciliations=2,
                historical_backend_grid_points=5,
                coverage_rows=len(matrix["rows"]),
                current_cost_grid_passes=0,
                current_runtime_large_runs=0,
            )
        )
    )


if __name__ == "__main__":
    main()
