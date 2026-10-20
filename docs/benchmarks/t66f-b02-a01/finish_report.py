"""완료된 evidence에서 최종 한국어 보고서를 만든다. gate를 임의 PASS로 바꾸지 않는다."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = Path(json.loads((HERE / "active-run.json").read_text())["out"])
FIRST = Path(json.loads((HERE / "runs.json").read_text())["initial_run"])


def read(path):
    return json.loads(path.read_text())


def f(n):
    return f"{n:,.3f}"


def table(headers, rows):
    return (
        "|"
        + "|".join(headers)
        + "|\n|"
        + "|".join("---" for _ in headers)
        + "|\n"
        + "\n".join("|" + "|".join(map(str, row)) + "|" for row in rows)
        + "\n"
    )


def main():
    a = read(OUT / "analysis.json")
    r = read(OUT / "reconciled.json")
    result = a["client_result"]
    evidence = read(HERE / "evidence/summary.json")
    preserve = read(HERE / "preservation-final.json")
    source = read(HERE / "source-evidence.json")
    initial = read(HERE / "initial-state.json")
    component = read(FIRST / "backend-component.json")
    e1 = read(FIRST / "e1-component.json")
    obs = r["observations"]
    fresh = read(OUT / "fresh-process.json")
    assert len(obs) == 3 and len(a["errors"]) == 3, "관측3회 전체 evidence 필요"
    assert all(
        e["failure_body"]["error"]["code"] == "OBSERVATION_EXPIRED" for e in a["errors"]
    )
    assert (
        not preserve["mismatches"]
        and preserve["index_entries_preserved"]
        and preserve["staged_preserved"]
    )
    assert result["error"] == "AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)"
    assert r["all_targets_equal"] and r["commit_new_count_matches_usage"]
    counts = evidence["targeted_flutter"]["counts"]
    passed = counts.get("success", 0)
    failed = counts.get("failure", 0) + counts.get("error", 0)
    backend = evidence["targeted_backend_suites"]
    backend_tests = sum(int(s["tests"]) for s in backend)
    assert failed == 2, "기존 source-SHA 외 신규 실패 분류가 먼저 필요"
    assert all(
        "source unchanged:" in (x["test"] or {}).get("name", "")
        or "AppState E4 entry" in (x["test"] or {}).get("name", "")
        for x in evidence["targeted_flutter"]["errors"]
    )
    assert all(
        int(s.get("failures", 0)) + int(s.get("errors", 0)) == 0 for s in backend
    )
    assert fresh["healthy"] and fresh["legacy_and_pending_bytes_preserved"]
    stages = result["acquisition"]
    assert all(s["error_code"] == "OBSERVATION_EXPIRED" for s in stages)
    verdict = "T6.6F-B02-A01 INVESTIGATION COMPLETE — MINIMAL CORRECTION IDENTIFIED"
    old = read(FIRST / "result.json")
    lease_table = table(
        [
            "관측",
            "ID",
            "validated_at / expires_at",
            "오류 헤더까지 초",
            "새 durable 객체",
            "객체 요청/200",
            "decoded B",
            "응답 entity B",
            "재전송",
        ],
        [
            [
                o["attempt"],
                f"`{o['id']}`",
                f"{o['validated_at']} / {o['expires_at']}",
                f(o["client_headers_to_terminal_error_seconds"]),
                o["new_durable_objects"],
                f"{o['object_requests']}/{o['success_responses']}",
                o["decoded_bytes"],
                o["response_entity_bytes"],
                o["redownload_prior_observation"],
            ]
            for o in obs
        ],
    )
    work_table = table(
        [
            "서로 중첩되지 않는 경계",
            "wall 초",
            "thread CPU 초",
            "성공 object handler 중 비율",
        ],
        [
            [
                k,
                f(v),
                f(r["disjoint_server_cpu_seconds"][k]),
                f"{100 * r['disjoint_server_work_share'][k]:.2f}%",
            ]
            for k, v in r["disjoint_server_work_seconds"].items()
        ],
    )
    packet_table = table(
        ["items/packet", "요청 수", "handler median ms"],
        [
            [k, v["count"], f(v["handler_median_ms"])]
            for k, v in r["packet_distribution"].items()
        ],
    )
    product_table = table(
        ["보존한 제품 경로", "시작=종료 SHA-256"],
        [[p, f"`{h}`"] for p, h in initial["product_hashes"].items()],
    )
    sections = []

    def s(number, title, body):
        sections.append(f"## {number:02d}. {title}\n\n{body.strip()}\n")

    s(
        1,
        "판정과 시작 저장소",
        f"""**{verdict}**.
첫 실제900초 lease 만료와 처리 비용을 재현했고 logger 경합을 분리한 확인 실행도3회 모두 실제
OBSERVATION_EXPIRED로 끝났다. 최소 후속 범위는 cold packet 충전 개선과 동일 요청 안의 bounded
검증 prefix 재사용이다. 제품 수정·commit·push는 하지 않았다. B02와 Phase B는 여전히 미완료다.

HEAD/main/origin/main/actual remote main은 시작 및 종료 모두 `6282c1c3577c42bba9382d786745d583a5d88236`.
Dirty B02는 정상 조사 입력이다. 최종[보존 검증](benchmarks/t66f-b02-a01/preservation-final.json)을 참조한다.""",
    )
    s(
        2,
        "정확한 기존 미커밋 입력",
        """제품3개326+/31−와 원 untracked B02 구현 보고서·evidence·4개 test 및 support가 존재했다.
전체 목록, staged diff와 index의 논리 entries는 [최초 기준](benchmarks/t66f-b02-a01/initial-state.json)에 있다.
원 index의 staged diff는 비어 있었다. 원 diff·untracked 파일을 복구/교체하거나 stage하지 않았다.""",
    )
    s(
        3,
        "제품 파일 hash 보존",
        product_table
        + f"""\n기존 {preserve["original_files"]}개 비무시 파일의 내용 SHA 불일치0, 원 tracked binary diff 동일,
논리 index entries 및 staged diff 동일이다. 모든 역사적 FAIL/INCONCLUSIVE 보고서를 보존했다.""",
    )
    s(
        4,
        "규범 observation 계약",
        """**SOURCE-LEVEL INVARIANT**: T6.6C §16은 Available부터 최대900초, principal별 Available4개,
원 credential·NS·Target 결합을 요구한다. §17은 active observation 재시도 최대3회다.
900초 초과 lease 또는 횟수 증가를 최소 수정으로 권고하지 않는다. §24/25의 complete graph·native
publication, §26의 DELETE+EXTRA, §29의 B/J, §31/34의 R1 및 §35/I25 경계도 유지한다.""",
    )
    s(
        5,
        "Backend lease 생성과 만료",
        """`observation.py:114` Limits, `create`의 terminal `validated_at/expires_at`, `_check_lease:323`,
`_lookup:515`를 대조했다. Bootstrap/대부분의 생성 작업은 lease 시작 전이다. Lease는 fixed이며
object 요청이 연장하지 않는다. 서버 UTC가 권한 oracle이고 timestamp는 초 단위다. 단말 clock은
bookkeeping이다. HTTP15초, busy1000ms, lease900초, 전체 acquisition wall time은 서로 다르다.""",
    )
    s(
        6,
        "E2 갱신·재시도",
        """`fetch.dart:254` acquire loop는 fresh observation마다 새 nonce/stage를 만든다. Same nonce/body는
같은 persisted manifest여야 한다. `_request`는 retry_same/일부 transport 오류만 bounded retry한다.
Graph 완료 뒤 같은 nonce의 terminal manifest를 다시 검사한다. Expired partial graph는 게시하지 않는다.
새 lease는 다른 generation일 수 있으며 old bytes 재사용과 old authority 재사용은 분리된다.""",
    )
    s(
        7,
        "N=50k fixture",
        f"""실제11-table ledger50000/총50035행, V200331/E200327,130710592 canonical B,
index-node100056/index-leaf100057, depth22/fanout32/최대 object151684 B다. 원 seed662602와 H(current105
및 참조·descriptor)를 유지했다. Cold base=null/D0이다. 확인 bootstrap은
{f(a["fixture"]["bootstrap_seconds"])}초, DB{a["fixture"]["backend_db_bytes"]}B였다. 두 run의 NS는 다르며
cache를 섞지 않았다. [확인 fixture](benchmarks/t66f-b02-a01/evidence/confirmation/server/backend-fixture.json).""",
    )
    s(
        8,
        "환경·계측과 단독 실행",
        """HOST x86_64 i7-8750H(12 logical CPU), 약24GB RAM, Python3.12.3/backend SQLite3.45.1/client SQLite3.53.4(sqlite3 package3.7.0),
Flutter3.47.4/Dart3.13.3 환경이다. 실제 cgroup/메모리/디스크와 runtime은 evidence에 기록한다.
다른 benchmark/full regression을 함께 돌리지 않았다. 정상 host daemon은 멈추거나 접근하지 않았다.
계측은 원 함수에 위임하며 server perf_counter/thread_time, client Stopwatch를 각각 쓴다.
서로 다른 monotonic 원점을 빼지 않는다. Trace/계측 비용은 포함된다. Android 측정이 아니다.""",
    )
    s(
        9,
        "완전한 실제 cold 실행 결과",
        f"""**DIRECTLY OBSERVED FACT**: 첫 run은 첫 lease의410을 관측한 뒤 두 번째 관측에서
`{old["error"]}`로 끝났다. 원 raw exception은 포착되지 않았다. 비대기 IOSink.flush 중 쓰기의
StateError와 원 transport의 동일 TRANSPORT_FAILED mapping을 별도 재현했다. Logger가 원인이라고
소급 확정하지 않고 첫 실행을3회 만료로 세지 않는다. [첫 자료](benchmarks/t66f-b02-a01/evidence/first/).

조사 logger만 동기 append로 바꾼 확인 run은 exit{a["execution"]["exit_code"]}, 외부 중단 없이
{f(result["elapsed_us"] / 1e6)}초의 client cold 후 `{result["error"]}`로 종료했다.
실제 backend HTTP/E2/E1/AppState 경로였고 E3 accepted/E4 read에는 도달하지 않았다.
N100k는 실행하지 않았다. [실행 기록](benchmarks/t66f-b02-a01/evidence/confirmation/execution.json).""",
    )
    for index in range(3):
        o = obs[index]
        s(
            10 + index,
            f"관측 {index + 1} timeline",
            f"""ID `{o["id"]}`. Principal{o["principal"]}, NS와 root는 reconciled JSON에 exact 보존했다.
`{o["validated_at"]}` → `{o["expires_at"]}`, TTL900초. Manifest 헤더부터 terminal error 헤더까지
{f(o["client_headers_to_terminal_error_seconds"])}초. 새 durable 객체{o["new_durable_objects"]}, object HTTP
{o["object_requests"]}회,200 응답{o["success_responses"]}회, 새 decoded{o["decoded_bytes"]}B다.
마지막 HTTP410 body의 code/action은 OBSERVATION_EXPIRED/new_observation이다.""",
        )
    s(
        13,
        "관측별 useful 진행",
        lease_table
        + f"""\n최종 durable 객체{result["usage"]["objects"]}/{a["fixture"]["graph"]["objects"]},
logical payload{result["usage"]["payload"]}B다. Commit hook 합계와 direct SQL usage가 일치한다.
별도 Python read-only SQL도 objects35496/payload47431669B, stage별 unique links15178/26931/35325,
accepted/generation/receipt/frozen pin 미게시와 FK 정상, legacy file SHA 보존을 확인했다.
[독립 SQL](benchmarks/t66f-b02-a01/evidence/confirmation/durable-state.json)을 참조한다.
Failed tail packet 또는 마지막 cached-progress 메모리를 durable 완료로 세지 않는다.""",
    )
    s(
        14,
        "검증된 객체 재사용",
        f"""각 관측의 Target 전체가 같았음을 exact JSON 비교했다. 이전 관측 객체 재전송은
{sum(o["redownload_prior_observation"] for o in obs)}개다. 저장 BLOB는 재사용되지만 미완료 cold에는
accepted-base provenance가 없으므로 full typed closure와 hash-on-read 및 새 stage progress가 반복된다.
Cached object, complete graph proof, publication authority는 별개다.""",
    )
    s(
        15,
        "요청 admission·permit·lock",
        f"""**INDEPENDENT MEASUREMENT**: WorkerBudget는 queue 없는 nonblocking semaphore다.
성공/거절 수와 native-start/BEGIN 시간은 requests trace에 있다. 성공 object 요청에서
permit 획득 중앙값0.010789ms, native-start 대기0.266369ms, BEGIN IMMEDIATE0.031196ms였다.
BEGIN 합계230.373ms로 busy 한도 소진이 주원인이라는 근거는 없다. 503/429는 각각
{a["statuses"].get("503", 0)}/{a["statuses"].get("429", 0)}회다. 같은 순차 HTTP 경로에서
max active handler{a["max_concurrent_handlers"]}, TCP connection{a["tcp_connections"]}개를 관측했다.
기존 admission_ms를 permit wait로 부르지 않는다. 실제 connect/schema/_lookup 비용을 포함한다.
정상 응답 종료에서 permit/jobs snapshot을 확인하며 final backend 관련 회귀도 분리 실행했다.""",
    )
    s(
        16,
        "HTTP 처리량과 packet 분포",
        packet_table
        + f"""\n평균 {r["mean_objects_per_packet"]:.3f} objects/packet,
성공 decoded 합계{r["successful_decoded_bytes"]}B다. Server entity/partial header-field bytes와 실제
TCP/TLS framing은 다르다. Client send→header와 server handler를 관측했으나 body 수신과 로컬
decode를 완전히 분리한 순수 network 시간은 아니다. 낮은 유효 throughput을 회선 대역폭 부족으로
해석하지 않는다. Cache 재순회 직후 client가 응답 헤더 이전 Broken pipe를2회 관측했다.
기존 transport가 이를 retry 가능한 TRANSPORT_UNAVAILABLE로 분류하고 다음 시도에200을 받았다.
스케줄된 backoff는각100ms, 실제 다음 send까지101.839/101.420ms였다. 서버는 이 실패한 send를
수신하지 않았다. Request attempt 상한3을 늘릴 필요를 보인 결과가 아니다.""",
    )
    s(
        17,
        "E2 hash·C1 validation",
        f"""Primary의 exact 전체 E2 hash CPU/byte 계수는 미완료이며 client gap 안에 포함된다.
`store.work`를 독립 계수로 부르지 않는다. 별도 원50k 부표본64 paths/141 objects의 원 PathResolver는
{component["actual_object_reads"]}회 object read, 동일 context {component["repeated_validation_contexts"]}회 반복,
C1 입력{component["calls"]["canonical_validate_input_bytes"]}B/hash 입력{component["calls"]["hash_input_bytes"]}B를
관측했다. Canonical inclusive {f(component["inclusive_ns"]["canonical_validate"] / 1e6)}ms,
hash {f(component["inclusive_ns"]["hash"] / 1e6)}ms이며 중첩 시간을 더하지 않는다.
[Component](benchmarks/t66f-b02-a01/evidence/first/backend-component.json)는 전층 대체가 아니다.""",
    )
    s(
        18,
        "E1 SQLite·batch",
        f"""Batch는 기존64 entries/1MiB이며 COMMIT{a["e1_commits"]}회, 새 object를 포함한 batch
{a["e1_new_object_commits"]}회다. 첫 insert→COMMIT 합계 {f(a["e1_insert_to_commit_ms"]["total"] / 1000)}초는
pre-BEGIN 검사 일부를 제외한 하한이다. 그 안에 COMMIT-only
{f(a["e1_commit_only_ms"]["total"] / 1000)}초가 중첩되므로 더하지 않는다. DELETE+EXTRA/FK를 유지한다.
부표본141 objects/71048B를3개 새 store에 실제64 batch로 쓰면 각각3 commits였고 처리량은
{", ".join(f"{x['objects_per_second']:.1f}" for x in e1["cold_stage_writes"])} objects/s였다.
Small component/JIT/host 값이며 Android 또는 전체 large write의 증거가 아니다.""",
    )
    s(
        19,
        "실제 overlap·backpressure",
        """Fetch→C1/hash→동기 E1 batch/COMMIT→다음 wave 순서이며 HTTP는1개다. Local write와 다음
packet fetch가 겹치는 pipeline은 아니다. In-memory paths/progress는 각각64로 bounded이고 bytes도
1MiB envelope를 따른다. Network가 local 작업을 기다리는 동안에도 lease clock은 간다.
원 response 객체/stream/detachSocket을 바꾸지 않은 IOClient 계측이다.
Cache 순회 중30초 snapshot 간격이 약45초까지 늘었다. Bounded batch가 event-loop 지연을
자동 제한하지는 않는다. Kernel peak RSS와 periodic sampler도 구분한다.""",
    )
    s(
        20,
        "Lease 소모와 critical path",
        work_table
        + f"""\nClient wall {f(result["elapsed_us"] / 1e6)}초,
전체 server handler work {f(a["handler_work_seconds"])}초, client HTTP send→header 합계
{f(a["client_http_inclusive_seconds"])}초, header→다음 send gap 합계 {f(a["client_gap_seconds"])}초다.
Lookup/connect/resolve는 성공 object 요청에서 서로 중첩되지 않는다. 그 내부 view/schema/versions는
nested inclusive이므로 다시 더하지 않는다. Timeout/backoff는 wire/error와 source 분기로 판정한다. 위 client gap에는 두 native 오류와
약0.203초 retry 간격도 포함된다. E2 세부 CPU split은 미측정이지만 local/body/retry가 포함된 전체
gap도 wall의약9.2%여서, 이를 서버 metadata보다 큰 주원인이라고 볼 수 없다.""",
    )
    s(
        21,
        "처리량 모델·추정",
        """**ANALYTICAL ESTIMATE**: 3×900초에200331/400532 objects를 받으려면 각각 약74.2/148.3
objects/s의 순진한 평균이 필요하다. Lease 생성·reuse·local verification이 있어 실제 목표는 더 높다.
64개 실제 packet도 수백 ms이므로 batch 충전만의100k 성공을 보장하지 않는다. 반복 prefix를
request-local로 재사용하는 후보를 함께 권고한다. 예측 수치를 실제 post-correction 결과로 쓰지 않는다.""",
    )
    s(
        22,
        "Fresh-process 안전성과 진행 재사용",
        f"""기존 실제 Dart reopen/recover/health는 healthy={fresh["healthy"]},
objects_checked={fresh["objects_checked"]}, stages_checked={fresh["stages_checked"]}, accepted=null,
legacy/pending bytes 동일이었다. 원50k의 별도 cache 사본 진단은 실제 E2/IOClient로 cached prefix를
재검사한 뒤 예정한 mock422에 도달했다. 이것은 실제 backend 전체 resume PASS가 아니다.
Incomplete observation은 current 권한으로 부활하지 않았다.""",
    )
    s(
        23,
        "Cross-generation 안전성",
        """Primary3개 Target는 같았으며 일부러 다른 generation을 만든 시험은 아니다.
Source cache NS/principal/Versions/typed Ref와 new-root closure, current credential 검사를 대조했다.
기존 small generation-churn/new-root/mixed-object 및 profile-context 회귀를 재실행한다.
인증/authority reuse는 금지하며 restart는 fresh ticket/lease가 필요하다. Large cross-generation 전체
성공 및 large one-row delta는 여전히 NOT RUN이다.""",
    )
    s(
        24,
        "Memory·SQLite·disk 경계",
        f"""Client peak RSS {result["client_process_rss_peak_bytes"]}B,
E1 DB{result["e1_database_bytes"]}B/metadata{result["usage"]["metadata"]}B/payload{result["usage"]["payload"]}B다.
30초 snapshot에서 WAL은0이며 E1은 DELETE journal이다. Transient rollback journal peak/physical
write amplification/pure Dart heap은 미측정이다. Backend는 WAL이다. `/proc` RSS/CPU/I/O/FD raw를
보존하지만 logical bytes와 혼동하지 않는다. Host 여유 RAM은 Android 안전성 증명이 아니다.""",
    )
    s(
        25,
        "원래 Flutter 네 실패",
        """원 후속 full log의 정확한4개를 [forensics](benchmarks/t66f-b02-a01/historical-failures.json)에 보존했다.
1) `segmented_large_profile_authority_test.dart` valid: pin_inserts 기대0/실제4.
2) `segmented_adapter_isolation_test.dart:48` fetch SHA mismatch.
3) 같은 파일`:104` AppState 복원 SHA mismatch.
4) `segmented_large_batch_test.dart:118` cached3×524288B 기대 거부/당시 허용.
이 full run은 최종 cached-byte 수정 전 compiled source였다. 과거 FAIL을 새 PASS로 덮지 않는다.""",
    )
    s(
        26,
        "Source-SHA gate 판단",
        f"""Fetch 기대 `{source["sha_guards"]["fetch_expected"]}` / 현재
`{source["sha_guards"]["fetch_actual"]}`. AppState 복원 기대
`{source["sha_guards"]["appstate_restored_expected"]}` / 현재
`{source["sha_guards"]["appstate_restored_actual"]}`다. 이전 audited fetch/default/authority source를
보호하는 gate이며 단순한 무해한 fixture라고 폐기하지 않는다. SHA 기대값은 변경하지 않았다.
변경 전체의 승인된 재감사 및 별도 source-lock 근거가 있어야 미래 갱신을 검토할 수 있다.""",
    )
    s(
        27,
        "현재 targeted 결과",
        f"""기존 selected Flutter **{passed} PASS/{failed} FAIL/{counts.get("skip", 0)} SKIP**.
실패2개는 그대로인 source-SHA guard다. 현재 pin/batch 행동 검사는 통과했으나 역사 pin0 assertion이
통과한 것은 아니다. 현재 새 pin oracle는 임시 root4개와 영구 SQL pin 동일성을 구분한다.
Backend 관련 **{backend_tests} tests PASS**, mock 경계진단1 PASS다. Full Flutter/backend는 NOT RERUN.
Npm build/backend Ruff/조사 Ruff/compileall/새 조사 파일 format/git diff check는 실제PASS다.
Flutter analyze/build 및 full 회귀는 이번에 NOT RUN이다. 실제 exit와 command는 postchecks/evidence
및 [최종 품질 기록](benchmarks/t66f-b02-a01/quality-final.json)에 보존한다.""",
    )
    s(
        28,
        "병목 순위",
        """1. **PRIMARY**: 작은 packet 수를 증폭시키는 D3의 요청별 metadata/C1/연결 검증 CPU.
2. **SECONDARY**: 공통 path prefix를 같은 packet에서도 다시 hash/C1/shape 검사.
3. **SECONDARY**: expired cold 갱신 뒤 기존 cache 전체 typed/hash/progress 작업 반복.
4. **LOWER COST**: 현재 E1 commit/검증과 낮은 batch 충전율. 저장 구조 재설계 근거는 없다.
5. Permit queue/SQLite lock/backoff/순수 전송 대역폭 부족은 이번 재현의 주원인으로 지지되지 않는다.
Exact E2 CPU split이나 device I/O는 미측정이며 순위를 꾸미지 않는다.""",
    )
    s(
        29,
        "좁은 대안 비교",
        table(
            ["선택", "실제 병목/효과", "계약·위험", "복잡도/개인용 적합성", "권고"],
            [
                [
                    "Cold batch 충전",
                    "요청·commit 고정비 상각",
                    "부모 검증 path/64·1MiB/유한 cursor·depth 유지; I25 보호",
                    "중간/높음",
                    "우선",
                ],
                [
                    "Request-local validated prefix reuse",
                    "동일 context 반복 C1 제거",
                    "원 native transaction만; count/byte cap·fresh auth/TTL/FD 유지",
                    "중간/높음",
                    "함께 검토",
                ],
                [
                    "E1 새 저장 엔진/pragma 완화",
                    "주원인 근거 부족",
                    "durability 위험",
                    "높음/낮음",
                    "기각",
                ],
                [
                    "더 많은 HTTP 병렬화",
                    "CPU/GIL·writer-lock 병목을 자동 해소하지 못함",
                    "resource/authority 복잡성 증가",
                    "중간/낮음",
                    "우선 안 함",
                ],
                [
                    "Observation/request 횟수 증가",
                    "느린 작업 반복을 늘림",
                    "규범 최대3회",
                    "낮으나 계약 영향",
                    "기각",
                ],
                [
                    "900초 초과 lease",
                    "속도를 고치지 않음",
                    "규범 최대900초",
                    "계약 결정 필요",
                    "기각",
                ],
                [
                    "검증/마지막 guard 제거",
                    "위험한 생략",
                    "I13/I14/I22 위반",
                    "부적합",
                    "기각",
                ],
            ],
        ),
    )
    s(
        30,
        "최소 후속 수정 권고",
        """**RECOMMENDED FUTURE CHANGE**: `fetch.dart`의 large-profile cold frontier만 기존64/1MiB packet을
채우는 bounded parent-path cursor로 개선한다. Cached batch 사이에도 유한 단위로 event loop에
제어를 돌리고 직후 cancellation/session을 재검사하도록 검토한다. Lost paths를 전체 cache 재탐색으로 찾는 O(N²) 방식은
금지한다. Accepted provenance가 유효한 정상 delta에서는 unchanged subtree를 확장하지 않는다.
`transfer.py`에는 같은 request/connection/transaction/Target 안의 동일 typed path prefix만 bounded
reuse하는 방안을 둔다. Hash 단독이 아니라 expected Ref.bytes/kind/table/descriptor/Patricia context와
동일 path에 묶는다. Count·byte cap, oversized fallback, 원 cancellation·최초 validation·모든 membership·
마지막 credential/lease/actual FD guard를 유지한다. Cross-request authorization cache는 만들지 않는다.
E1 batch는 유지하고 E3/E4를 수정할 근거는 없다. 실제100k 성공은 후속 gate다.""",
    )
    s(
        31,
        "개인 단일 사용자 판단",
        """Rare large cold의 긴 작업은 허용할 수 있으나 무한 재시도·부분 authority·무제한 RAM은 허용하지
않는다. 정상 daily delta를 full cold로 만들지 않는다. 기존 object store/HTTP/transaction을 재사용하고
새 queue/service/storage engine/persistent protocol을 도입하지 않는다. 새 persistent state/migration,
normal startup work/default budget 증가는 필요하지 않다. Financial correctness를 속도와 교환하지 않는다.""",
    )
    s(
        32,
        "후속 테스트와 독립 감사",
        """50k/100k 실제 cold, identical/25·26-object one-row delta, restarted incomplete/accepted recovery,
wrong NS/principal/epoch/type/hash/descendant, corrupt/ENOSPC, cancel/reauth/newer ticket, concurrent E3,
prefix-cache context collision/eviction/oversized fallback, cursor/cache peak bounds와 actual SIGKILL을 요구한다.
Backend 수정 시 기존 release-artifact/source SHA 절차를 따라 exact identities를 검증한다. 원 quota
assertion과 E4-A01/RA01·Frozen B/J·full Flutter/backend/analyze/build를 보존하고 독립 targeted re-audit를 받는다.""",
    )
    s(
        33,
        "100k 함의",
        """필수100k는V400532/261543083B/depth23이다. 이번에는 실행하지 않았다. 현재50k의 실패와
component를100k 완료로 바꾸지 않는다. 후보 수정의 이점은 분석적 추정이며 같은 bounded attempts/lease
아래 실제 full D→E로 확인해야 한다. 그 이전에 large incremental/I25/storage 완료를 선언할 수 없다.""",
    )
    s(
        34,
        "남은 Phase B 비용 증거",
        """전체50k/100k accepted→E4 read/delta 및 전층 logical hash/validate/write byte 계수가 남는다.
HTTP bytes, canonical payload, SQL file/WAL growth를 대신 쓰지 않는다. Backend hash_bytes/decode_c1/
serialization, E1 verify/hash/INSERT body, E2 chunk validation, E3 F(raw)/receipt/pins, E4 read/handoff에
실제 함수 input bytes를 세는 test-only hook과 direct SQL을 결합한다. 이번 작은 component byte 계수는
그 위치를 확인한 것이며 전층 measurement가 아니다.""",
    )
    s(
        35,
        "Android·R1 경계",
        """Android VFS/pragmas/I/O-success와 실제 power-loss proof는 여전히 요구된다. HOST RSS/SQLite,
SIGKILL로 대체하지 않는다. Device performance는 별도 gate다. Large Restore/MW/chunk/hash/backup/
atomic apply/receipt/migration/rollback은 R1 소유로 deferred이며 구현하지 않았다.
R1 activation은 CLOSED, 일반 사용자 segmented Offline과 production activation/배포는 하지 않았다.""",
    )
    s(
        36,
        "최종 조사 판정과 한계",
        f"""**{verdict}**. 주 병목과 좁은 후보를 직접 비용/저장/wire evidence로 식별했다.
제안 성능 향상·100k 완료·Android 안전성은 미검증이며 후보 구현 이후 실제 gate로 남는다.
확정 새 Critical/High/Medium correctness finding은0이다. 기존 B02 feasibility/완료 gate는 열린 상태다.
첫 logger 오류·초기 mock 오류는 조사 하네스 한계로 공개하고 제품 결함으로 세지 않는다.
B02 COMPLETE/Phase B PASS/T6.6F COMPLETE 또는 R1/배포 승인은 아니다.""",
    )
    s(
        37,
        "최종 보존·새 파일·Git",
        """원 B02 product/test/report/artifact와 staged 상태는 최초 SHA와 동일하다. 새로운 파일은
`docs/t66f-b02-a01-cold-acquisition-investigation.md` 및 `docs/benchmarks/t66f-b02-a01/`뿐이다.
상세 새 파일 목록은 preservation-final.json에 있다. Git commit/push/stage/reset/stash/clean/checkout,
프로토콜·source-SHA 기대값 변경은 수행하지 않았다. Flutter build/cache, Python __pycache__, frontend/dist
등 통상 test-generated ignored 파일은 별개다. 최종 tree는 원 B02와 조사 자료 때문에 dirty가 정상이다.""",
    )
    footer = f"""T6.6F-B02-A01 INVESTIGATION:
COMPLETE

STARTING HEAD:
6282c1c3577c42bba9382d786745d583a5d88236

INITIAL WORKTREE:
DIRTY — UNCOMMITTED B02 IMPLEMENTATION EXPECTED

FINAL WORKTREE:
DIRTY — ORIGINAL B02 CHANGES PRESERVED

NEW COMMIT:
NONE

PUSH:
NOT PERFORMED

EXISTING B02 PRODUCT FILES:
UNCHANGED

ORIGINAL STAGED CHANGES:
PRESERVED

BINDING PROTOCOL:
UNCHANGED

N=50K FIXTURE:
VERIFIED

N=50K REACHABLE OBJECTS:
200331

N=50K CONTROLLED COLD RUN:
OBSERVATION_EXPIRED

N=100K COLD RUN:
NOT EXECUTED

OBSERVATION LEASE CONTRACT:
VERIFIED

OBSERVATION TTL:
900초

LEASE EXPIRY SEMANTICS:
FIXED

OBSERVATION ATTEMPTS USED:
3

REQUEST ATTEMPTS USED:
{a["object_requests"] + 2} object send 시도 / 서버 도달{a["object_requests"]}회; native 오류2회는 두 번째 시도에 성공(상한3 유지)

ATTEMPT 1 DURATION:
{f(obs[0]["client_headers_to_terminal_error_seconds"])}초

ATTEMPT 2 DURATION:
{f(obs[1]["client_headers_to_terminal_error_seconds"])}초

ATTEMPT 3 DURATION:
{f(obs[2]["client_headers_to_terminal_error_seconds"])}초

ATTEMPT 1 NEW DURABLE OBJECTS:
{obs[0]["new_durable_objects"]}

ATTEMPT 2 NEW DURABLE OBJECTS:
{obs[1]["new_durable_objects"]}

ATTEMPT 3 NEW DURABLE OBJECTS:
{obs[2]["new_durable_objects"]}

ATTEMPT 1 HTTP BYTES:
{obs[0]["response_entity_bytes"]} 응답 entity B

ATTEMPT 2 HTTP BYTES:
{obs[1]["response_entity_bytes"]} 응답 entity B

ATTEMPT 3 HTTP BYTES:
{obs[2]["response_entity_bytes"]} 응답 entity B

OBSERVATION RENEWAL:
VERIFIED

CROSS-OBSERVATION OBJECT REUSE:
VERIFIED

CROSS-GENERATION REUSE SAFETY:
PASS — 기존 small 회귀·source 범위; large 변경 generation 미실행

HTTP REQUEST ADMISSION:
MEASURED

BACKEND PERMIT WAIT:
MEASURED

HTTP TRANSFER COST:
PARTIAL

E2 HASH/VALIDATE COST:
PARTIAL

E1 SQLITE WRITE COST:
PARTIAL — 실제 commit span 및 component, 전체 SQL bytes 아님

E1 BATCH SIZE:
최대64 entries / 1MiB

E1 COMMIT COUNT:
{a["e1_commits"]}

E1 OBJECT WRITE THROUGHPUT:
부표본 실제 batch API 900.6–1373.1 objects/s; large 전체 E1 API 시간은 미분리

PIPELINE OVERLAP:
VERIFIED — HTTP/저장은 순차

PIPELINE BACKPRESSURE:
VERIFIED

RETRY/BACKOFF COST:
MEASURED — Broken pipe2회, backoff각100ms; 실제 retry 간격 합계203.259ms

CRITICAL PATH:
ESTABLISHED

PRIMARY BOTTLENECK:
작은 E2 packet으로 증폭되는 D3 요청별 metadata/C1 검사

SECONDARY BOTTLENECK:
PathResolver의 동일 요청 내 공통 prefix 반복 검증

USEFUL PROGRESS ACROSS OBSERVATIONS:
PRESERVED

FRESH-PROCESS SAFE RECOVERY:
PASS

FRESH-PROCESS PROGRESS REUSE:
PASS — 별도 cache 사본의 실제 E2/IOClient+mock 경계 진단

OLD ACCEPTED GENERATION:
PRESERVED — 이 cold의 기존 selector는 null

LEGACY B/PENDING BYTES:
PRESERVED

FROZEN PINS:
NOT EXERCISED

INCOMPLETE GRAPH PUBLICATION:
NONE

ORIGINAL FLUTTER FAILURES:
4 IDENTIFIED

SOURCE-SHA GUARDS:
CLASSIFIED

ORIGINAL ASSERTIONS:
PRESERVED

CURRENT TARGETED TESTS:
{passed} PASS
{failed} FAIL — 원 source-SHA gate
{counts.get("skip", 0)} SKIP
Backend 관련 {backend_tests} PASS

FULL FLUTTER REGRESSION:
NOT RERUN

FULL BACKEND REGRESSION:
NOT RERUN

PREFERRED CORRECTION:
cold-only bounded packet 충전·event-loop yield + request-local bounded typed prefix 검증 재사용

PRODUCT PATHS AFFECTED BY FUTURE CORRECTION:
mobile/lib/src/segmented/fetch.dart
backend/isolated_sync/transfer.py
정식 release/source-lock artifact는 후속 승인 범위

SERVER CHANGE REQUIRED:
YES

E1 CHANGE REQUIRED:
NO

E2 CHANGE REQUIRED:
YES

E3 CHANGE REQUIRED:
NO

E4 CHANGE REQUIRED:
NO

PROTOCOL CHANGE REQUIRED:
NO

NEW SQLITE MIGRATION REQUIRED:
NO

SINGLE-USER SUITABILITY:
PASS

EXPECTED CORRECTION COMPLEXITY:
MEDIUM

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

REMAINING INVESTIGATION BLOCKERS:
0 — 후속 구현 성능/기기 증명은 별도 gate

SAFE TO START MINIMAL B02-A01 CORRECTION:
YES — 별도 승인된 후속 task에서만

SAFE TO DECLARE B02 COMPLETE:
NO

SAFE TO RESUME T6.6F PHASE B:
NO

T6.6F PHASE B:
STILL INCONCLUSIVE

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

SAFE TO DEPLOY:
NO

FINAL VERDICT:
T6.6F-B02-A01 INVESTIGATION COMPLETE —
MINIMAL CORRECTION IDENTIFIED

NEXT ACTION:
별도 후속 작업에서 제한된 cold packet 충전과 요청 내 prefix 검증 재사용을 구현하고 실제50k/100k 및 독립 재감사를 수행하세요.
"""
    path = ROOT / "docs/t66f-b02-a01-cold-acquisition-investigation.md"
    path.write_text(
        "# T6.6F-B02-A01 대형 cold acquisition 병목 조사\n\n"
        + "\n".join(sections)
        + "\n## 최종 상태\n\n```text\n"
        + footer
        + "```\n"
    )
    (HERE / "footer.txt").write_text(footer)
    print("최종 한국어 보고서 생성:", path)


if __name__ == "__main__":
    main()
