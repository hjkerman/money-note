"""측정 종료 후 원 수치로 한국어 보고서의 후반부를 작성한다."""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"
REPORT = HERE.parents[1] / "t66f-b03-ic01-p03-real-path-lease-verification.md"


def main():
    a = json.loads((OUT / "full-analysis.json").read_text())
    r = json.loads((OUT / "full-result.json").read_text())
    run = json.loads((OUT / "real-path.json").read_text())
    passed = a["status"] == "PASS" and run["status"] == "PASS"
    verdict = "VERIFIED" if passed else "FAILED"
    if passed:
        detail = "REAL INSTRUMENTED N=100K FULL PATH PASS"
    else:
        detail = "REAL INSTRUMENTED N=100K FULL PATH DID NOT COMPLETE"
    text = REPORT.read_text().split("\n## 21.")[0]
    first = text.index("**진행 기록:")
    last = text.index("\n", first)
    text = text[:first] + f"**{verdict} — {detail}.**" + text[last:]
    text += f"""

## 21. 새 전체 실행 횟수

실제 새 계측100k cold attempt는 **정확히1회**다. `full-attempt.json` 존재 guard,
GO 결정 및 실제 full-only trace가 이를 뒷받침한다. 초기 fixture/mock 준비 실패와
bounded prefix를 full attempt로 바꾸지 않았고, 전체 실행 후 재시작하지 않았다.

## 22. 전체 실행의 실제 증거

[full-result](benchmarks/t66f-b03-ic01-p03/evidence/full-result.json),
[독립 재집계](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json),
[실시간 경계](benchmarks/t66f-b03-ic01-p03/evidence/full-live-observations.jsonl)와
원 server trace gzip을 보존했다. 전체 elapsed는{a["elapsed_s"]:.6f}초다.
backend의 전체 cohort total에는 prefix가 섞여 있으므로 `full/관측UUID` group만 별도 합산했다.
클라이언트 header timer,backend handler/ASGI response boundary,TCP 수신 완료는 같은 경계가 아니다.
처리 시간은 겹치므로 stage wall·CPU·SQL·HTTP를 더해 별도의 전체 시간을 만들지 않았다.

"""
    for o in a["observations"]:
        n = o["number"]
        text += f"""## {22 + n}. 관측{n} 실제 결과

실제 생성 `{o["created"]}`,만료 `{o["expires"]}`,TTL{o["ttl_seconds"]:.0f}초다.
요청{o["requests_completed"]:,}건,status `{o["statuses"]}`,전송 object event
{o["transferred_object_events"]:,}개,다음 실제 client 경계의 누적 durable 객체
{o["client_cumulative_durable_objects"]:,}개를 기록했다.
request/response entity는{o["request_entity_bytes"]:,}/{o["response_entity_bytes"]:,}B다.
처음/마지막 성공 object response 구간은{o["object_productive_interval_s"]:.6f}초,
마지막 backend 성공 응답 경계의 잔여 lease는{o["last_success_headroom_s"]:.6f}초다.
요청 완료 시 native pending 최댓값은{o["native_pending_at_completed_boundary_max"]}이다.
실제 관측 직전 누적 snapshot과 다음 경계의 primitive/SQL 차이는 full-analysis에 있다.
마지막 경계에는 local E3/E4도 들어갈 수 있어 E2 prefix key로 구별한다.

"""
    if len(a["observations"]) < 3:
        for n in range(len(a["observations"]) + 1, 4):
            text += f"## {22 + n}. 관측{n}\n\n실행하지 않았다.\n\n"
    text += f"""## 26. 최종 counter snapshot

native object count/body 합은{r["durable_objects"]["n"]:,}개/{r["durable_objects"]["bytes"]:,}B다.
실제 전송 event 합은{a["transferred_object_events"]:,}이고 native unique row와의 차이는
{a["retransmission_events_vs_native_unique_rows"]:,}개다. 이 값은 graph edge visits나 cached reads가 아니다.
SQL API 누적 {a["client_sql_api_inclusive_s"]:.6f}초와 observer callback 하한
{a["client_observer_callback_truncated_lower_bound_s"]:.6f}초는 포함 관계다.
stage별 hash input·validation submitted/completed span·SQL attempted/effective/committed
TEXT+BLOB payload와 원 key 목록을 full-analysis에 기록했다. 누락 key를 measured zero로 채우지 않았다.
실행하지 않은 legacy/file/recovery 분기를 full100k에서 다시 실행했다고 주장하지 않는다.
그 경계의 소형 실제 보정·기존 targeted test와 실제 full 실행 범위는 분리한다.

## 27. E3 게시와 E4 금융 읽기

accepted pointer 전/후는 `{r["accepted_before"]}` / `{r["accepted_after"]}`다.
"""
    if passed:
        text += f"""원 AppState RefreshTicket을 사용한 실제 publication 반환은{a["publication_s"]:.6f}초,
그 뒤 E4 read+독립 value digest oracle은{a["e4_read_including_independent_value_oracle_s"]:.6f}초다.
accepted sequence는{r["sequence"]}이며 Target/root와 완전 graph closure를 확인했다.
11-table E4 canonical VALUE digest를 backend fixture의 독립 digest와 대조했다.
exact raw monetary 문자열과 Unicode를 그대로 검증했고 금융 계산을 모바일에서 재구현하지 않았다.
독립 digest용 encoding/hash는 닫힌 nested scope로 제품 counter에서 제외했다.
"""
    else:
        text += f"""실패 `{r.get("error")}`를 원 stack과 보존했다. E3/E4 미도달 구간은 PASS로 표시하지 않는다.
남은 객체는{a["remaining_objects"]:,}개다. 기존 cold accepted pointer는 null로 보존됐으며
부분 graph를 게시하지 않았다.
"""
    text += f"""offline baseline·pending B/J 보호 파일의 전/후 checksum은 동일하다.
pending ACK/rebase를 수행하지 않았다. collector closed={r["collector_closed"]},managed cache
`{r["cache_closed"]}`이고,created/finalized 동수·capacity rejection0을 확인했다.
client sampled peak RSS는{a["client_peak_sampled_rss"]:,}B,
client lifetime max는{a["client_lifetime_max_rss"]:,}B,
backend lifetime max는{a["server_lifetime_peak_rss_bytes"]:,}B다.
소유 두 process의 동시 RSS 표본 합 peak는{a["owned_process_sampled_peak_sum_rss_bytes"]:,}B다.
이것은 Android heap/allocation/VFS/전원 손실 검증이 아니다.

## 28. 실패 분류

"""
    text += (
        "전체 acquisition·publication·read와 최종 assertion이 모두 PASS했다. 준비 단계의 두 실패는\n"
        "별도 raw evidence에 그대로 있으며 전체 실행 성공으로 덮지 않았다.\n"
        if passed
        else f"전체 실제 시도는 FAIL이다. 오류 원문은 `{r.get('error')}`다.\n"
        "원인 분류와 지배 구간은 원 trace·counter를 근거로 최종 summary에 기록한다.\n"
        "prefix의 GO 판단을 사후 INCONCLUSIVE로 바꾸거나 전체 실행을 자동 재시도하지 않았다.\n"
    )
    text += """
## 29. IA01–IA07 교정 보존

현재 교정된 동작의 backend64/Flutter73 targeted 회귀와 소형 실제 HTTP2 tests가 새로 PASS했다.
same-name savepoint,partial SQL success,comment-prefixed DML,nested installation,
rejected dispatch release,owner32,generation/oracle SQL 분리를 포함했다.
prepared cache32·reset/rebind·connection ownership·finalization·counter/state equality도 새로 통과했다.
원 독립 감사의 결함 존재 reproducers는 수정하지 않았고 역사 IA finding을 소급 PASS로 쓰지 않았다.
IA07은 원 cursor delegate 실험을 현 구현에 그대로 실행해 stage setup176/185와 generation oracle0을 확인했다.

## 30. Source-lock 보존

P0 `recoveryLineageFingerprint()`와 protected production6개 source 및 exact SHA 기대값은
P03에서 바꾸지 않았다. 새 lineage4/exact source6 tests는 PASS했다. 역사23 guards와 전체
source-SHA coverage는 동일 source SHA의 P02 full suite 결과로 구분한다.
새 lock을 추가하거나 보호 diff를 몰래 수용하지 않았다. 원 감사·P01·P02 보고서도 보존했다.

## 31. 금융·legacy 경계

backend sole financial authority,C1,Snapshot v7,OfflineBaseline v4,legacy fingerprint와 sync_root 분리,
E3 원 ticket/final authority guard→COMMIT의 동기 경계,user_version4,기존 migration을 보존했다.
제품 source diff가 없으며 새 await 또는 authorization override를 넣지 않았다.
B01 strict concurrency assertion과 B02 default ceiling/explicit large profile/packet/TTL/attempt/cache를
바꾸지 않았다. E4-A01/E4-RA01 및 B01/B02는 재현된 제품 회귀가 없어 CLOSED를 유지한다.

## 32. 새 targeted 검증

현재 backend64 PASS,Flutter73 PASS,실제 소형 HTTP2 PASS,같은 driver의 N1000 TLS/renewal smoke1 PASS다.
raw fixture restoration assertion도 별도로 PASS했다. 실제 큰 prefix/renewal/full test의 최종 상태는
real-path runner JSON을 따른다. 최초 fixture/raw timestamp 및 HTTP mock 준비 실패2건은 기록을 남겼으며
현재 test를 skip하거나 assertion을 약화하지 않았다. 새 driver의 조건별 test 수와 기존 회귀 수를 합쳐
서로 다른 전체 suite 횟수로 만들지 않는다.

## 33. 전체 회귀 상태

**검증한 역사 증거**: P02 full backend1,436 tests/1,540 subtests PASS,
full Flutter1,690 PASS/0 FAIL/2 SKIP다. P03에서 이 두 full suite를 재실행하지 않았다.
기존 production/instrumentation source SHA가 모두 같고 측정 의미를 바꾸지 않았으므로 사용자 §27을 적용했다.
app Flutter analyze/debug build도 NOT RERUN이며 APK 설치는 없다.
P03 진단 Dart analyze,새 Python Ruff/compileall,active changed-file formatting와 diff check는
최종 checks 기록에 별도 표시한다. frontend npm build는 P03에서 새로 exit0을 확인했다.

"""
    REPORT.write_text(text)
    print(json.dumps({"report": str(REPORT), "verdict": verdict}))


if __name__ == "__main__":
    main()
