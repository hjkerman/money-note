# T6.6F-B01 — backend concurrency 조사

## 조사 시작과 확정 범위

시작 HEAD/main/origin/main/실제 원격 main은 모두
`c479a379b54e196439c522c1fdf56eca713ca8ad`였으며 working tree는 clean이었다.
원 Phase B INCONCLUSIVE 보고서·두 실패 로그·기존 감사 tests는 수정하지 않는다.
이는 Phase B 전체 완료나 독립 B01 validation PASS 보고서가 아니다.

## OBSERVED FAILURE — 제품/원 시험 변경 전

원 시험은 `backend/tests/test_isolated_sync_transfer.py::test_bounded_concurrent_quota_and_same_request_status`다.
원 497행의 정확한 assertion은 다음과 같다.

```python
assert sorted(r.status_code for r in results) == [201]*4+[429]
```

두 역사적 전체 실행은 각각 2,300.31/1,877.89초, 1,314 PASS/1 FAIL 및 1,540 subtests PASS다.
두 경우 모두 `[201,201,201,201,503]`이며 response body/SQLite trace는 당시 저장되지 않았다.
따라서 두 과거 실패의 개별 내부 원인이 동일했다고 소급 확정하지 않는다.

원 시험 단독은 PASS였다. 제품/시험을 변경하지 않은 opt-in 계측의 반복 8회에서는
6 PASS/2 FAIL로 같은 assertion/status signature를 재현했다. 이 campaign은 기준 전체 회귀와
동시 실행한 조건이며 완전 무부하 isolated sample이라고 부르지 않는다.
새 observer의 첫 실행은 기존 이중 close에서 `in_transaction`을 읽는 계측 자체 결함을 보였다.
그 실패는 제품 반례로 세지 않고 기존 idempotent close를 보존하도록 observer만 고쳤다.

## CONFIRMED ROOT CAUSE — 시험의 lock budget 전제

재현한 두 실패의 실제 HTTP body는 `503`, code `ROOT_NOT_READY`, action `retry_same`,
retry_after_ms `100`, current_ns `null`이다. 정상 JSON/no-store/nosniff 응답이며 내부 예외
또는 token을 노출하지 않는다. 해당 원 request UUID와 thread/connection timeline을 evidence에 남긴다.

두 실패는 create의 `BEGIN IMMEDIATE`가 각각 **1,002,708 / 1,007,129µs** 뒤
`OperationalError`, SQLite code **5 / SQLITE_BUSY**, `database is locked`로 끝났다.
다른 create와 terminal lookup의 짧은 writer transaction들이 선행했다. SQLite는 FIFO admission을
약속하지 않는다. quota를 읽기 전에 lock budget이 끝난 request이므로 아직 `LEASE_LIMIT`로
판정할 수 없다. 실제 durable available 4개/pins 20개, FK/integrity 정상 및 모든 관찰 handle의
close를 확인했다. worker limit 8에서 5개 요청이므로 permit admission 초과가 이 재현의 원인은 아니다.

T6.6C §15.2/§17은 bounded contention의 `503 ROOT_NOT_READY/retry_same`을 허용하며,
§16의 quota 4개/초과 429는 해당 quota decision에 도달한 transaction의 결과다.
원 quota 시험은 실제 금융 projection까지 포함한 5 create+4 terminal의 writer 경쟁이
기본 **1,000ms** 이내에 모두 admission될 것이라는 별도 scheduling 가정을 두고 있었다.
그 전제는 규범 보장이 아니다. 실제 503를 429로 변환하는 제품 수정은 하지 않는다.

### 실제 대표 실패 timeline

시간은 해당 pytest call 시작으로부터의 µs이며 PID `325311`이다. connection 번호는
CPython 객체 주소 재사용과 분리한 observer의 단조 local identity다. 원 request UUID는
실패 `ef655f50-d4bb-4863-a598-495f174a5174`, 최초 writer는
`935fa240-e3b4-445f-84a2-c40ab183294d`다. 이 값은 storage/진단 identity이지 인증 token이 아니다.

| 시간 | 실제 사건 |
|---:|---|
| 428,165 | connection 6의 첫 create가 writer 획득 |
| 528,018 | 실패 request의 connection 8이 BEGIN IMMEDIATE 대기 시작 |
| 776,042 | connection 6 COMMIT trace |
| 804,708 → 955,785 | connection 10 create 획득 → COMMIT trace |
| 965,442 → 1,161,039 | connection 9 create 획득 → COMMIT trace |
| 1,188,433 → 1,382,692 | terminal lookup 12/13/11이 각각 writer 획득·COMMIT |
| 1,452,619 | 먼저 기다리던 connection 7 create가 writer 획득 |
| 1,530,737 | connection 8의 1,002,708µs wait가 SQLITE_BUSY로 종료 |
| 1,593,530 | connection 7 create COMMIT trace |
| 1,631,953 → 1,668,883 | connection 14 terminal 획득 → COMMIT trace |

SQLite COMMIT trace는 native statement 진입 관찰이지 disk flush 완료시각이 아니다.
각 execute/commit 반환·close도 원 evidence에 별도 기록한다. 실패 request는 quota SELECT에
도달하지 않았다. 두 실패의 client-observed HTTP 시간은 1.451/1.535초였다.
server native prepare/create·lookup의 시작/종료는 별도로 관찰하며 client total과 더하지 않는다.

### 가장 작은 교정 결정

분류는 **B — Test harness defect**다. 원 status/pin/count assertion은 그대로 보존한다.
quota 시험에만 기존 `Limits`가 허용하는 유한 synthetic lock budget **5,000ms**를 명시한다.
이는 이미 `test_concurrent_quota_replacement_is_atomic`가 사용하는 설정이다.
기본 제품 lock timeout·100ms connect timeout·transaction lifetime·HTTP mapping·permit·retry는 불변이다.
전역 timeout 상향, assertion 허용값 추가, sleep/retry loop, concurrency 직렬화는 추가하지 않는다.

새 결정적 comparator는 같은 writer를 실제 두 connection이 기다리게 한다. 기본 budget 요청의
실제 503 응답을 barrier로 삼아 writer를 해제하며 더 긴 synthetic budget 요청은 정상 완료해야 한다.
시간을 맞추기 위한 임의 sleep 없이 budget 차이와 release 이후 동일 nonce의 201→200을 검사한다.
이 증거와 전체 회귀 완료 전에는 교정 완료를 선언하지 않는다.

## CORRECTION MADE — 변경 경계와 보존

유일한 기존 파일 변경은 `backend/tests/test_isolated_sync_transfer.py`의 import 한 줄과
해당 quota 함수의 client construction이다. 실제 repository/create_app, auth, 금융 presenter,
SQLite transaction·4 Available/20 pins assertion은 그대로다. 원 세 assertion의 exact bytes를
Git 기준 source와 AST 위치로 추출해 비교한 신규 test가 PASS했다. `Barrier(5)`/실제 5 thread,
다중 connection·same-principal 경쟁을 유지하며 요청을 한 줄로 직렬화하지 않는다.

`backend/app`, `backend/isolated_sync`, `mobile/lib`의 diff는 0이다. schema/engine artifact,
원 permit·database identity fence·pending/B/J/v7/v4·금융 parser/projection은 수정하지 않는다.
production SQLite checkpoint는 4이며 segmented runtime은 비활성이다. 이전 source ownership
교정과 원 Phase B 감사 commit의 53파일(보고서 포함)도 그대로다. 직접 SHA 보존 검사는 제품/관련 역사
자료 221파일을 포함한다.

새 targeted 네 사례는 실제 default 1초/최대 synthetic 5초 wait comparator, 두 lifecycle의
busy·invalid 뒤 정상 요청/permit 반환, 원 3-assertion byte equality다. comparator는 실제
SQLITE_BUSY 1.002초 뒤 writer를 해제해 긴 요청의 201 및 다른 원 nonce 201→200을 확인했다.
throw나 status만 보지 않고 별도 SQLite에서 미성공 attempt의 objects/current/pins/observations
불변, 성공 뒤 2 observations/10 pins와 FK 일관성을 검사했다.

### 조사 전체 재현의 표시 한계

교정 전에 시작한 전체 실행은 원 시험 모듈을 이미 수집한 process에서 원 1초 설정을 실행했다.
실행 도중 disk의 시험 setup을 고쳐 pytest의 사후 source 표시가 새 파일을 읽었다. 결과는
원 assertion의 옛 bytecode 497행에서 `[201,201,201,201,503]`, 1 FAIL/1,314 PASS,
1,540 subtests PASS / 1,558.03초다. 표시된 새 파일의 `barrier = Barrier(5)`를 실패 assertion으로
재해석하지 않는다. 이를 교정 후 실행으로 분류하거나 원 로그를 고쳐 정리하지 않는다.

별도 `repeat.py --baseline`은 원 commit의 전체 test file exact bytes를 새 임시 경로에만
보존·실행한다. checkout/reset·기존 파일 overwrite가 없고, 현재와 기준 products의 hash 일치를
별도 확인한다. 이 source-display 모호성 없는 campaign도 최종 증거와 분리해 기록한다.

원 기준 copy SHA-256는 `ddee07457cea3d99a830b367bb013abe8a6a2cb8474026aa27973ba8f218ade7`다.
상세 SQL 계측 copy 4회는 **2 PASS/2 FAIL**이며 두 실패의 BEGIN wait는
1,002,713/1,001,974µs였다. **SQL execute/connect/commit/close wrapper를 모두 생략한** 응답·예외
관찰 copy 4회도 **1 PASS/3 FAIL**이었다. 실제 예외 context chain의 내부 frame은
`observation.py:create:398 → contextlib.__enter__ → observation.py:_connection:267`의
`OperationalError(5, SQLITE_BUSY, database is locked)`이며 외부 `create:510 → reject:52`가
`ROOT_NOT_READY`로 분류했다. 그러므로 상세 SQL observer의 overhead만으로 생긴 실패라고
설명하지 않는다. 상세 계측 latency를 무계측 production latency로 부르지도 않는다.

이후 한정 setup의 formatter 정리는 source SHA만 바꾸고 전체 test AST digest는
`ce7a4c4d32feb495303d660406763ddef87ad35a30a75b856e169bb28bdd99db`로 동일했다.
`source-format.json`에 full-run collection/최종 source hash를 구분한다. 원 세 assertion bytes는
여전히 같으며 현재 status assertion 위치는 **504행**, 원 기준은 **497행**이다.

## 비용·권한·저장 영향

변경은 synthetic quota test의 PRAGMA busy budget 값 한 가지이며 production request 경로에
새 scan·retry·cache·global lock을 추가하지 않는다. 정상 결과를 낸 교정 전/후 계측 cohort 모두
**4,355 execute calls / 1,450 SELECT calls / 14 관찰 connection**이었다. 기존 5 creators와
4 terminal transactions, 4 successful observations/20 root pin rows를 유지했다. 교정 후 cohort의
최대 successful BEGIN wait **1,230,290µs**는 원 1초 전제가 실제로 충분하지 않았다는 추가 근거다.
이 계수는 조회 row 수/VM instruction/물리 I/O 또는 독립 E3 I25·전체 전층 cost proof가 아니다.

기본 100ms connect admission·1초 repository busy wait·10초 transaction lifetime 및 bounded worker는
그대로다. 시간 초과를 성공이나 quota 거부로 변환하지 않는다. 단계별 quota/index access, request
nonce·원 credential guard, source DB/certificate/root와 release의 identity fence도 변경하지 않았다.
원 D3B-M01 worker cancellation과 D3C-A01 actual-open FD 보증은 기존 family/전체 회귀로 검사하며
본 B01을 그 별도 독립 감사의 재완료로 표현하지 않는다.

원 fixture는 module template을 자체 생성 DB로 backup한 뒤 per-test SQLite를 yield한다.
plain backup handles의 context 종료는 commit/rollback 경계이며 native handle close와 같다고
추정하지 않는다. 그 시점 열린 writer transaction을 유지하지 않으며, 원 시험은 모든 pool future
종료 후 assertion과 fixture teardown을 실행한다. 실제 failing HTTP 연결 14개의 닫힘은 별도
계측 결과다. premature teardown·다른 DB replacement·permit leak은 재현 원인으로 확인하지 않았다.

## HYPOTHESIS NOT CONFIRMED

두 과거 full-suite 실패의 body·wait·PID는 원 기록에 없어 새 관찰로 대체하지 않는다.
과거 load의 정확한 원인, 다른 service의 자원 사용, 모든 OS scheduling의 안정성을 입증하지 않는다.
현재 재현은 assertion의 불충분한 lock-budget 전제를 직접 증명하지만 과거 응답이 다른 경로에서
503였을 가능성까지 배제했다고 주장하지 않는다. 제품 correctness finding은 이 증거에서 확정하지 않았다.

## INDEPENDENT RE-VERIFICATION STILL REQUIRED

원 Phase B §34의 전체 H/D/N scaling·compression/실기기·R1 resource/atomic apply,
18-row cross-layer race 전수·모든 protocol negative 독립 주입 등은 이 조사로 닫지 않는다.
최종 counts·선택된 family·실제 HTTP·보존 SHA·commit/push 증거는 완료 후 별도 절에 기록한다.
R1 gate는 CLOSED, production segmented sync는 비활성이다.

## 최종 실제 검증 결과

해결 선택은 **B — Test/environment correction completed**, 세부 분류는 **TEST HARNESS**다.
환경 quota·service·제품 timeout은 바꾸지 않았다. 제품 변경은 0이며 원 세 assertion도 불변이다.
구현측 최종 판정은 **T6.6F-B01 RESOLVED — READY FOR INDEPENDENT TARGETED VALIDATION**이다.

[summary.json](benchmarks/t66f-b01/summary.json)의 실제 JUnit/machine/개별 pytest exit와
`--require-complete` guard에 근거한다. 전체 backend의 2,855 JUnit entries는 main tests
1,315 + subtests 1,540이므로 main tests 수를 부풀리지 않는다.

| 실행 | 실제 결과 | 해석 |
|---|---|---|
| 원 감사의 두 full failures | 각각 1,314 PASS / 1 FAIL + 1,540 subtests PASS | 역사적 body/lock trace 미보존, 원 로그/SHA 불변 |
| 조사 전 원 시험 단독 | 1 PASS | 과거 실패를 해소하는 증거로 쓰지 않음 |
| 원 setup 상세 observer 반복 | 6 PASS / 2 FAIL | full 회귀 동시 부하, body/BEGIN wait 보존 |
| 원 기준 exact-copy 상세 반복 | 2 PASS / 2 FAIL | old file bytes 동일, body/1초 BUSY 보존 |
| 원 기준 exact-copy 응답-only 반복 | 1 PASS / 3 FAIL | SQL wrapper 없음, 실제 native exception chain 보존 |
| 조사 시작의 full run | 1,314 PASS / 1 FAIL + 1,540 subtests PASS, 1,558.03초 | old collected setup, source-display 한계 별도 기록 |
| 교정 setup 반복, full 회귀 동시 부하 | 8 PASS / 0 FAIL | 원 status/count/pin assertion 유지 |
| full 회귀 종료 후 교정 setup 반복 | 4 PASS / 0 FAIL | 최종 코드·observer, fresh disposable fixture |
| 신규 B01 targeted | **4 PASS / 0 FAIL**, 8.794초 | 실제 budget comparator/lifespan 2/원 assertion bytes |
| 관련 concurrency/cancellation/identity/quota family | **90 PASS / 0 FAIL**, 245.271초 | 기존 원 사례 재실행, 신규 case로 더하지 않음 |
| quota-first / quota-last 순서 변형 | **3 + 3 PASS / 0 FAIL** | 첫 duplicate node는 pytest가 deduplicate했으므로 4개라고 세지 않음 |
| 교정 후 full backend 1 | **1,315 tests + 1,540 subtests PASS**, 1,696.49초 | failure/error 0 |
| 교정 후 full backend 2 | **1,315 tests + 1,540 subtests PASS**, 1,568.76초 | failure/error 0, 별도 process/DB/수집 |
| 원 Phase B 실제 TLS concurrency | **2 PASS / 0 FAIL**, 10.507초 | lock 중 503, 해제 후 201→200, lease/pin/permit 정상 |
| 원 Phase B Flutter 실제 HTTP smoke | **3 PASS / 0 FAIL / 0 SKIP**, done=true | FB01 7-generation wire/SQL oracle, FB13 R1 closed, FB14 principal 격리 |
| Ruff / compileall | PASS / PASS | 실제 exit 0 |
| formatting / diff check | PASS / PASS | 신규 Python과 기존 setup 변경 범위만 검사; unrelated 편차 유지 |
| frontend tests / build | **21 PASS / PASS** | 비배포 build, 실제 exit 0 |
| 제품/관련 역사 자료 보존 | **221파일 SHA 일치**, changed 0 | 원 3 assertions byte equality 포함 |

교정 전 selected reproduction 합계는 **10 PASS/7 FAIL**이며 calibration·observer 자체 결함의
실행은 이 합계에서 제외하고 본문에 별도로 남겼다. 교정 후 반복은 **12 PASS/0 FAIL**다.
같은 test의 full/targeted/campaign 재실행을 새로운 case 수로 더하지 않는다. 새 B01 독립
요구 시나리오는 4개이며 이를 독립 감사 PASS라고 부르지 않는다.

두 full runs는 별도 process/자가 소유 fixtures지만 일부 시간대에 병행했다. current source의
test AST가 같다는 점과 실제 workload/계측 차이를 기록했으며, 반복 PASS가 모든 scheduling의
수학적 안정성 증명은 아니다. 대기 budget은 여전히 유한하며 향후 극심한 resource starvation의
다른 실패를 성공으로 취급하지 않는다.

### 종료·원본 보존의 한계

재개 시 두 full 실행의 exec session handle이 만료되어 원 native exit code를 재조회하지 못했다.
완료된 JUnit의 모든 cases/failure/error와 일치하는 pytest terminal summary로 test PASS를 집계했다.
`process-status.json`의 해당 exit 값은 **null**이며 0을 만들어 넣지 않았다. 반면 최종 완료 guard,
quiet 반복의 각 pytest exit, targeted 및 최종 정적 검사의 실제 종료는 별도 수집했다.

Flutter full 1,503 PASS/2 SKIP, analyze/build는 원 Phase B의 **보존된 과거 증거**이며 이번에
다시 실행한 전체 Flutter 결과로 표시하지 않는다. 제품/engine/wire source SHA가 불변인 test-only
setup 교정이므로 현재 재실행은 위 실제 HTTP 세 사례로 제한했다. Backend full에는 D1–D3c,
원 worker cancellation/DB identity/migration/금융/Snapshot 회귀가 그대로 포함된다.

원 Flutter oracle 2,374,855B는 임시 원본을 유지하고 digest/작은 generation·wire 계수만
[flutter-interoperability.json](benchmarks/t66f-b01/flutter-interoperability.json)에 파생 보존한다.
이는 raw canonical bytes를 새 JSON으로 대체하거나 oracle의 독립 기대값을 변경한 것이 아니다.
DB·auth headers·token·APK·성공 로그 전체는 commit 대상이 아니다.

## Phase B 후속 의무와 readiness

B01 범위의 미해결 Critical/High/Medium blocker는 **0/0/0**이다. 실제 제품 결함을 확정하거나
기존 protocol의 error semantics를 약화하지 않았다. 독립 B01 targeted validation을 요청할 수 있다.

원 Phase B §34 및 §§24–27의 남은 범위는 그대로다.

- 고정 H/D, N=1k/5k/10k/50k/100k 전체 scaling grid와 gzip/Brotli 비교, median/p95·실기기 gate.
- Android VFS/I/O/power-loss 증명, R1 >25MiB upload/atomic apply/backup/resource 및 migration/rollback.
- 18-row cross-layer authority/race를 별도의 신규 실제 HTTP 시나리오로 전수 구성하는 증거.
- 모든 protocol negative의 독립 주입 및 기존 backend concurrency/DB identity 회귀 범위를 넘어서는 검증.
- 계측 단위·cold/steady-state 경계를 구분한 전체 end-to-end storage cost/resource 증명.

이 조사에서 일부 기존 실제 HTTP/DB identity 사례를 재실행했다고 위 범위를 자동 완료하지 않는다.
**T6.6F Phase B는 STILL INCONCLUSIVE**이며 독립 B01 validation 전 재개 승인도 없다.
R1 gate CLOSED, general-user segmented Offline 미활성, 배포·APK 설치·운영 service 변경 없음.

## Commit/push 증거

최종 완료 guard·제품 diff 0·원 assertions와 221개 보존 SHA·정적 검사를 확인한 뒤 명시한
test setup/신규 B01 tests·diagnostics·bounded evidence·이 보고서만 commit한다.
Message는 `test(backend): repair T6.6F-B01 concurrency harness`다.
이 보고서를 최초 추가한 commit은 다음 명령으로 식별한다. 자기 hash를 문서에 넣으려고
amend/rebase하지 않으며 실제 최종 hash·push 결과는 최종 응답과 remote ref가 증거다.

```bash
git log --diff-filter=A --format=%H -- docs/t66f-b01-backend-concurrency-investigation.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --short
```

정상 history의 push 이후 네 refs 일치와 clean tree를 확인한다. Commit/push는 deployment 또는
Phase B/R1 activation 승인이 아니다. 다음 단계는 이 교정의 독립 B01 targeted validation이다.
