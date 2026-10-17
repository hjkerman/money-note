# T6.6F-B01 독립 targeted 검증

## 01. 대상과 판정 범위

대상 교정 commit은 `f4ae582b548a5a445ce72c1d1a0d8543836044f3`, 원 Phase B 감사는
`c479a379b54e196439c522c1fdf56eca713ca8ad`다. B01의 test-harness 교정만 검증한다.
제품 수정, Phase B continuation, R1, deployment·APK 설치·segmented activation은 수행하지 않는다.
최종 판정은 **PASS — T6.6F-B01 INDEPENDENT TARGETED VALIDATION COMPLETE**다.
두 full regression의 실제 exit/JUnit/terminal 및 독립 완료 guard를 확인했다.

## 02. 저장소·원격·diff

변경 전 HEAD/main/origin/main/실제 `git ls-remote origin refs/heads/main`은 모두 대상 commit이었다.
작업 트리는 clean이었다. AGENTS와 필수 도메인·신뢰 경계·개발 검증 규칙을 적용했다.
[inventory.json](benchmarks/t66f-b01-independent/inventory.json)에 exact tree, refs, 원 assertions,
제품·test·역사 자료 237개 SHA/Git blob을 기록했다.

전체 correction diff는 19개 파일, +12,627/-2다. 기존 파일 수정은
`backend/tests/test_isolated_sync_transfer.py` 하나이며 import와 한 함수의 repository/client
구성만 변경했다. 신규 18개는 B01 보고서·독립 검증 전 구현측 tests/observer/repeat/collector 및
JSON 증거다. dependency·production configuration·schema·backend/Flutter product source 변경은 0이다.
전체 파일 inventory와 실제 source/hash는 inventory에 보존했다.

## 03. 원 Phase B 실패

**HISTORICAL PHASE B EVIDENCE:** 원 두 full run은 각각 1,314 PASS/1 FAIL +1,540 subtests
PASS였다. quota assertion에서 `[201,201,201,201,503]`을 관찰했다. 당시의 HTTP response body,
SQLite wait trace·정확한 lock holder·실행 부하 원인은 저장되지 않았다. 원 보고서/로그는 불변이다.

## 04. 정확한 원 assertion

대상은 `backend/tests/test_isolated_sync_transfer.py::test_bounded_concurrent_quota_and_same_request_status`다.
원 status assertion은 다음과 같으며, 나머지 Available 4/pins 20 assertion도 그대로다.

```python
assert sorted(r.status_code for r in results) == [201]*4+[429]
```

Barrier(5), ThreadPoolExecutor(5), worker limit8을 유지한다. 이 함수의 다섯 `observe()`는 각각
새 UUID를 만드는 **distinct request**이며 같은 principal의 Available quota4를 경쟁한다.
함수명에 same-request가 있어도 duplicate 검증은 별도 사례다. 결과 순서 대신 multiset 전체를
검사하며 503을 허용하거나 429로 변환하지 않는다.

## 05. Assertion·다른 fixture 동등성

새 독립 I01은 Git 원본과 현재 세 assert의 source segment를 exact 비교했다. 다른 모든 함수의
AST도 같다. 대상 함수에 SKIP/XFAIL decorator는 없다. 실제 원 expression을 실행해
`[201,201,201,429,503]`와 `[201,201,201,201,503]`가 모두 False임을 확인했다.
원 case를 반복 및 full suite에서 그대로 실행하며 assertion을 대체하지 않는다.

## 06. Lock budget 교정

원 `client()` helper는 `ObservationRepository`의 기본 `Limits()`를 암묵 소비했다.
`observation.py:121`은 기본 1,000ms, `:129`는 허용 범위 1..5,000ms다. 교정된 quota 함수만
`ObservationLimits(lock_wait_ms=5000)`을 명시한다. clock=NOW/evaluation=EVAL·worker8·quota4와
원 auth/producer/terminal 경로는 같다. test-local repository를 구성하며 전역 default를 바꾸지 않는다.

## 07. 5초의 기존 지원 근거

`docs/t66/d/implementation/t66d3a-implementation.md:364`는 기존 configurable 1..5,000ms를
명시한다. Git 원 기준의 `test_concurrent_quota_replacement_is_atomic`도 이미 5,000ms를 썼다.
I01은 현재 5,000 허용 및 5,001/0/bool 거부를 실제 검사했다. 이는 지원되는 유한 synthetic
budget이지 임의로 오래 걸리는 작업의 성공 보장이 아니다. T6.6C는 1초 또는 5초 안의 성공을
보장하지 않으며 busy의 503/retry_same을 허용한다.

## 08. Scope·production 격리

I08의 양쪽 실행 순서와 I09의 실제 PRAGMA 조회에서 다른 repository/default는 유지됐다.
native connection admission timeout100ms, repository 기본1,000ms, transaction lifetime10초,
quota4, HTTP mapping/retry·worker capacity는 불변이다. busy_timeout은 해당 새 connection의
설정이며 repository operation 후 native handle을 닫는다. 정상 앱·production SQLite checkpoint4,
Snapshot v7/v4·Frozen B/J·R1 gate에 대한 product diff는 0이다. 운영 상태에 접속한 검사는 아니다.

## 09. 과거 body의 한계

**B01 IMPLEMENTATION-SIDE CLAIM:** 새 조사 재현에서는 ROOT_NOT_READY/BUSY를 기록했지만,
과거 두 실패의 내부 원인까지 소급 확정하지 않는다고 명시했다. 실제 보존 자료도 이 구분과 맞는다.
조사 중 초기 observer가 closed handle의 `in_transaction`을 읽어 만든 500은 별도 진단 이력이며
제품 반례로 세지 않는다. 조사 full 두 실행의 native exit가 null인 것도 그대로 인정한다.

**UNVERIFIED HISTORICAL ASSUMPTION:** 과거 두 503의 각 내부 원인, 정확한 당시 부하와 모든
OS scheduling의 동치는 여전히 증명되지 않았다. 새 재현을 과거 관찰로 바꾸지 않는다.

## 10. 독립 1초 재현

**NEW INDEPENDENT B01 EVIDENCE:** 원 파일 exact-copy 네 반복 중 3 PASS/1 FAIL였다.
새 observer로 저장한 실패는 실제 `BEGIN IMMEDIATE`가 1,007,192µs 뒤 code5/SQLITE_BUSY,
`database is locked`로 끝났고 원 UUID에 대해 503/ROOT_NOT_READY/retry_same/100ms/null을 반환했다.
원 strict assertion이 실패했으며 503을 성공에 포함하지 않았다.

이 외 I02는 외부 실제 writer를 잡고, 5초 waiter 다섯 개의 native BEGIN 진입을 Event로 확인한
뒤 1초 probe를 보냈다. probe가 실제 BUSY response를 반환한 뒤에만 writer를 해제한다.
실패 시 별도 SQLite의 objects/current/observations/pins/budget·financial digest는 이전과 같다.
원 copy의 자연 경합과 결정적 외부 writer 실험은 서로 다른 재현으로 구분한다.

## 11. 독립 5초 검증

I02의 writer 해제 뒤 다섯 long waiters는 정확히 4×201 +1×429였다. 원 교정 함수의 독립
반복 12회도 12 PASS였다. cleanup 추가 관측의 4+1회까지 포함한 교정 함수 단독 실행은
17 PASS/0 FAIL다. 관련 group/full run의 같은 case를 이 반복 수에 다시 더하지 않는다.
유한 성공 횟수를 모든 scheduling의 수학적 증명으로 확대하지 않는다.

## 12. HTTP status/body

1초 실패에는 actual code5 native evidence와 일치하는 503/error code/action/retry-after 및
no-store/nosniff가 있다. quota decision에 도달한 다섯 요청은 429 LEASE_LIMIT와 네 available
manifest를 반환한다. 429와 503은 §17에 따라 retry_same이지만 원 quota 성공 assertion에서
서로 대체할 수 없다. 503 제거·masking·error membership 완화는 없었다.

## 13. SQLite transaction timeline

새 observer는 connection별 native BEGIN/COMMIT/ROLLBACK trace, execute 반환/오류 시간과 close,
HTTP completion·request UUID·thread를 기록한다. COMMIT trace는 statement 진입이며 flush 완료
시각이 아니다. [원 재현 및 독립 사례](benchmarks/t66f-b01-independent/README.md)의 delegate는
원 함수/SQL/exception을 그대로 전달하며 SQL parameter·credential을 기록하지 않는다.
실제 lock 획득·오류와 해제는 barrier/Event 또는 native SQLite return으로 관찰했다.

## 14. Quota·same-request

I02/I04는 Available4와 root pins20 및 financial revision 불변을 별도 SQL로 확인했다.
I04는 같은 nonce의 concurrent 201/200, 동일 response bytes·한 observation/5 pins,
같은 nonce의 다른 body409 REQUEST_CONFLICT, full quota의 same-nonce200와 새 nonce429를 검증했다.
서버 observation quota와 worker permit8은 서로 다른 자원이다.

## 15. Permit lifecycle

Observer snapshot뿐 아니라 실제 capacity만큼 acquire하고 하나 초과는 거부하는 probe로
각 HTTP operation 뒤 capacity 반환을 확인했다. I05는 authenticated/native BEGIN wait 두
경계에서 실제 ASGI Task를 취소했다. requester가 사라져도 native worker가 살아 있는 동안
후속 요청은 503이며 permit을 조기 반환하지 않는다. release/rollback·native exit 뒤에는 정상
201 및 capacity1이 복구된다. native 작업 완료 전 forced thread termination은 없다.

## 16. DB identity

I07 두 경계에서 A request를 멈추고 A 경로가 B를 가리키게 했다. A의 stale request는 성공하지
못했고 B의 모든 직접 snapshot은 그대로였다. B의 자기 owner 경로는 새 요청201이 가능했으며,
A의 원 inode 복원 뒤 original nonce는 absent이면201, 이미 COMMIT됐으면200이었다.
WAL/SHM 파일은 조작하지 않았다. 원 D3C-A01 actual-open/ABA 반례 6개도 변경 없이 통과했다.
이 결과를 전체 남은 integrated DB-identity matrix의 완료로 확대하지 않는다.

## 17. Connection·rollback cleanup

제품 operation의 관찰한 native handles는 명시 close됐다. 새 cloned fixture는 backup handles도
명시 close하며 I02의 실제 DB FD가 call 전후 모두 0이었다. I09는 repo context 후 native query가
closed 오류를 내고 새 connection의 admission100ms/BEGIN/rollback이 정상임을 확인했다.
I06의 실제 SQL error는 COMMIT 전이면 전체 rollback, COMMIT 뒤이면 complete lease/pins 유지와
같은 nonce200 재조회로 구분했다. 뒤의 오류를 성공한 rollback이라고 부르지 않는다.

**B01-IV01 / INFORMATIONAL — 원 test fixture의 GC 의존 backup handle 정리.**
`backend/tests/test_isolated_sync_transfer.py:58`의 plain `with sqlite3.connect(...)`는 native
close가 아니다. 원 반복에서 해당 DB FD는 call 전1→후2, fixture teardown 후 deleted FD2,
명시 GC 후0이었다. I09에서도 raw context 종료 뒤 query가 가능하고 명시 close 뒤에야 거부됨을
직접 확인했다. 제품의 관찰한 14개 HTTP connection은 모두 close됐고 새 explicit-close fixture의
FD는 0→0이었다. 활성 writer transaction이나 영속/permit leak의 증거는 아니다.

이 GC 관찰을 원 BUSY 원인으로 연결한 근거는 없다. 재현된 실패는 create BEGIN의 1초
deadline이었다. 이 관찰은 원 quota assertion을 약화하지 않으며 B01 blocker가 아니다. 최소 권고는 별도
test-helper 정리에서 backup handles에 `contextlib.closing`을 명시하는 것이다. 감사자가 고치지
않았다. GC 전 잔류를 지우거나 즉시 native FD0이라고 보고하지 않는다.

## 18. 원 test 반복

원 exact-copy4: 3 PASS/1 FAIL. 교정 source12: 12 PASS/0 FAIL. FD lifecycle 추가4+1도 모두
PASS로 합계 교정 함수17 PASS다. source copy는 새 `/tmp`에만 만들었고 각 subprocess의
command/JUnit/실제 exit·response/native timeline을 기록한다. 원 checkout/history는 바꾸지 않았다.

## 19. 관련 concurrency

실제 관련 group은 90 PASS/0 FAIL이다. observation/transfer/failures/cancellation/retention ownership
파일에서 concurrent/busy/identity/cancel/ownership/quota를 선택했다. 원 D3B-M01의 native
worker lifetime 및 D3C-A01 actual-open FD fence를 source와 기존 회귀로 확인했다.
새 독립 사례 수로 기존 90개를 더하지 않는다. 원 quota/auth/duplicate 세 case를 같은 process에서
quota-first와 quota-last로 배치한 순서 검증도 각각3 PASS였다. 이 6개는 반복17/새15에 더하지 않는다.

## 20. 새 독립 사례

14 backend +새 실제 TLS Flutter quota/E2 1 = **15 PASS/0 FAIL**다. 기존 B01 correction4는
별도 재실행 4 PASS다. 독립 사례의 expected/actual/oracle와 사용자 15-theme mapping은
최종 `cases.json`/`summary.json`에 기록한다. 목록 수를 실행 수로 간주하지 않는다.

## 21. 전체 backend run 1

원 workflow의 `backend` cwd에서 `../.venv/bin/python -m pytest -q --junitxml=...`를 실행했다.
실제 exit0, timeout=false, main1,315 PASS +subtests1,540 PASS, JUnit entries2,855/failure0/error0/
skip0다. 실제 process elapsed1,487.843초이며 JUnit time1,487.272초와 구분한다.
Start/end/PID/command 및 완전한 JUnit을 독립 증거에 보존한다.

## 22. 전체 backend run 2

별도 process·새 fixtures에서 같은 명령을 순차 실행했다. 실제 exit0, timeout=false,
main1,315 PASS +subtests1,540 PASS, JUnit entries2,855/failure0/error0/skip0다.
process elapsed는 1517.054초, JUnit time은 1516.477초다.
두 full run 모두 알려진 Starlette TestClient/httpx deprecation warning 1개였으며 예상하지 못한
경고나 test timeout은 없었다. 실제 wait exit가 보존되어 만료된 session의 code를 추정하지 않는다.

## 23. 실제 HTTP 상호운용

원 Phase B 실제 TLS backend2와 기존 Flutter FB01/13/14 세 smoke가 모두 PASS다.
새 I10은 실제 네 lease201 +quota429/error body, 같은 limit1 client에서 E2의 bounded429 세
시도와 실패 상태의 accepted=null/objects0을 확인했다. 네 lease를204로 release한 뒤 같은
client의 complete verified acquisition과 별도 client SQLite의 backend canonical bytes 일치를
검증했다. 이 새 smoke는 E3 publication/E4 설치를 하지 않는다.

현재 선택 Flutter는 4 PASS/0 FAIL/0 SKIP다. **FULL FLUTTER REGRESSION:
NOT RERUN IN B01 TARGETED VALIDATION.** 과거1,503 PASS/2 SKIP를 현재 결과로 전용하지 않는다.

## 24. Resource·SQL 비용

교정 전 성공과 교정 후 성공의 독립 counter는 모두 **4,355 execute/1,450 SELECT/14 handles**다.
실패 경로와 성공 경로를 같은 workload 비용으로 비교하지 않는다. execute 호출 수는 VM/row/I/O
수가 아니다. Product tree와 SQL/retry/quota/default diff가 0인 사실도 확인했다. 대기시간 설정은
성공 경로의 추가 scan/retry를 만들지 않는다. E3 I25나 전층 storage cost를 B01로 닫지 않는다.

## 25. 제품·원 assertions 불변

원 전체 correction diff에서 backend/app·backend/isolated_sync·mobile/lib·frontend는 불변이다.
감사자는 이 보고서와 새 감사 전용 폴더만 추가한다. 현재 target test도 auditor 변경0이며
원 세 assertion과 기존 Phase B/B01 보고서·raw evidence SHA를 최종 보존 검사한다.

## 26. 기존 Phase B 증거의 이월

원49/7/10 및 real HTTP·Flutter1,503/2 SKIP는 당시 범위·한계 그대로 보존한다. 제품 source가
같은 test-only 교정은 그 증거를 무효화하지 않는다. 원 backend FAIL와 Phase B INCONCLUSIVE는
역사적으로 유지한다. B01의 새 closure가 다른 INCONCLUSIVE 항목을 PASS로 바꾸지 않는다.

## 27. 후속 gap 분류

[continuation.md](benchmarks/t66f-b01-independent/continuation.md)에 A/B/C/D와 소유자·gate를
정리했다. 현재 Phase B의 고정 H/D·N 전체 grid/압축/median-p95·독립 authority/negative 및 전층
cost 증명은 남는다. R1/전환 계약은 별도 소유지만 전체 F 의존성에서 생략할 수 없다.
§26의 actual Android driver/I/O/power-loss proof 미완료는 rollout을 차단한다. §35는 device
절대 latency 목표를 post-T6.6 전에 임의 설정하지 않는다. HOST를 실기기 증거로 대체하지 않는다.
이 checklist를 B01에서 실행하지 않았다.

## 28. Findings

현재 새 CRITICAL/HIGH/MEDIUM/LOW correctness finding은 0이다. B01-IV01은 기존
test fixture의 자원 정리 관찰이며 INFORMATIONAL 1개다. 제품 문제를 flakiness로 숨기지 않았고,
정상 busy 응답을 제품 결함으로 재분류하지 않았다. 두 mandatory full runs도 실제 PASS로 끝났다. B01 범위에 미해결 correctness blocker는 없다.

## 29. B01 closure

재현된 메커니즘의 **ROOT CAUSE CLASSIFICATION: TEST HARNESS**는 source·HTTP·native SQLite와
strict quota evidence로 지지된다. 과거 두 실패의 개별 원인은 **NOT RETROSPECTIVELY PROVEN**이다.
두 mandatory full suites의 최종 종료까지 확인하여 **B01 FINDING: CLOSED**,
**BACKEND FULL REGRESSION GATE: PASS**로 확정한다. 원 strict assertion·quota·기본 budget·
제품 동작을 약화한 변경은 없다.

## 30. Phase B continuation readiness

**SAFE TO RESUME T6.6F PHASE B: YES**다. 이는 별도 invocation의 continuation readiness다.
이 task는 나머지 campaign을
실행하지 않았고 Phase B/F 완료를 선언하지 않는다. 필수 남은 gate는 continuation checklist와
원 보고서 §34를 함께 적용한다.

## 31. R1·production 제한

R1 Large Restore는 DEFERRED, activation gate CLOSED다. normal startup/read/write·Snapshot v7/
OfflineBaseline v4·Frozen B/J admission/lineage는 source상 불변이다. 사용한 DB·credentials는
새 자가 소유 synthetic fixture뿐이다. production API/DB/credentials/service/migration/deploy,
APK 설치·segmented activation을 수행하지 않았다.

## 32. Audit-only commit/push

완료된 독립15·원 교정 함수17반복·correction4·related90·identity6·order6·backend TLS2·
Flutter HTTP4와 full backend 두 실행, 보존237개/원 assertions·정적 검사를 확인했다.
새 감사 tests/instrumentation/evidence와 이 보고서만 staged diff를 검토해 commit/push한다. 자기 hash를 문서에 넣으려고 history를 amend하지 않는다.
이 문서를 추가한 commit은 `git log --diff-filter=A --format=%H -- docs/t66f-b01-independent-validation.md`로
식별하며 실제 최종 hash/네 refs·clean 증거는 최종 응답에서 보고한다. Commit은 배포 허가가 아니다.


## 필수 최종 상태

```text
T6.6F-B01 INDEPENDENT TARGETED VALIDATION:
PASS

ORIGINAL PHASE B AUDIT COMMIT:
c479a379b54e196439c522c1fdf56eca713ca8ad

AUDITED B01 CORRECTION COMMIT:
f4ae582b548a5a445ce72c1d1a0d8543836044f3

FINAL AUDIT-ONLY COMMIT:
이 문서를 추가한 commit — git log --diff-filter=A --format=%H -- docs/t66f-b01-independent-validation.md

REPOSITORY STATE:
VERIFIED

B01 CORRECTION DIFF:
REVIEWED

PRODUCT SOURCE MODIFIED BY B01:
NO

PRODUCT SOURCE MODIFIED BY AUDITOR:
NO

ORIGINAL CONCURRENCY TEST:
backend/tests/test_isolated_sync_transfer.py::test_bounded_concurrent_quota_and_same_request_status

ORIGINAL ASSERTION:
UNCHANGED

EXPECTED STATUS MULTISET:
[201, 201, 201, 201, 429]

UNEXPECTED 503 ACCEPTANCE:
NO

ROOT CAUSE CLASSIFICATION:
TEST HARNESS

ROOT CAUSE VALIDATION:
PASS

HISTORICAL FAILURE ROOT CAUSE:
NOT RETROSPECTIVELY PROVEN

ONE-SECOND LOCK-BUDGET REPRODUCTION:
PASS

FIVE-SECOND SUPPORTED BUDGET:
VERIFIED

FIVE-SECOND FIXTURE SCOPE:
PASS

PRODUCTION LOCK BUDGET:
UNCHANGED

HTTP STATUS/BODY:
PASS

SQLITE LOCK/WAIT EVIDENCE:
PASS

SQLITE TRANSACTION SAFETY:
PASS

QUOTA CORRECTNESS:
PASS

SAME-REQUEST SEMANTICS:
PASS

PERMIT ACQUISITION/RELEASE:
PASS

PERMIT LEAK:
NONE

DATABASE IDENTITY FENCING:
PASS

SQLITE CONNECTION CLEANUP:
PASS — 제품 경로; 원 backup fixture의 GC 지연은 B01-IV01 참조

NEW INDEPENDENT B01 CASES:
15 PASS
0 FAIL
0 INCONCLUSIVE

EXISTING B01 CORRECTION CASES:
4 PASS
0 FAIL

TARGETED REPEATED TEST:
17 PASS
0 FAIL

RELATED CONCURRENCY TESTS:
90 PASS
0 FAIL

FULL BACKEND RUN 1:
1315 TESTS
1540 SUBTESTS
PASS

FULL BACKEND RUN 2:
1315 TESTS
1540 SUBTESTS
PASS

BACKEND D1-D3C REGRESSION:
PASS

REAL BACKEND HTTP REGRESSION:
2 PASS
0 FAIL

RELEVANT FLUTTER HTTP REGRESSION:
4 PASS
0 FAIL

FULL FLUTTER REGRESSION:
NOT RERUN IN B01 TARGETED VALIDATION

INCREMENTAL COST IMPACT:
PRESERVED

PRODUCTION DEFAULT BEHAVIOR:
UNCHANGED

RUFF:
PASS

COMPILEALL:
PASS

CHANGED-FILE FORMATTING:
PASS

GIT DIFF CHECK:
PASS

PRIOR PHASE B EVIDENCE:
PRESERVED

REMAINING PHASE B §34 GAPS:
CLASSIFIED

PHASE B MANDATORY REMAINING GATES:
고정 H/D·N 전체 grid, 압축·median/p95, 독립 authority/negative 보완, 잔여 DB identity, 전층 storage/resource 및 E3 I25 cost 증명

R1-DEFERRED REQUIREMENTS:
Large Restore/MW·chunk/hash·bounded staging·backup·atomic apply/receipt·R1/전환 migration·rollback

ENVIRONMENT/DEVICE-DEPENDENT GATES:
Android driver/VFS/pragmas·I/O/power-loss proof, post-T6.6 실기기 성능 증명; rollout gate 유지

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

NEW LOW:
0

UNRESOLVED B01 BLOCKERS:
0

B01 FINDING:
CLOSED

BACKEND FULL REGRESSION GATE:
PASS

SAFE TO RESUME T6.6F PHASE B:
YES

T6.6F PHASE B STATUS:
INCOMPLETE — CONTINUATION REQUIRED

SAFE TO DECLARE T6.6F COMPLETE:
NO

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

SAFE TO DEPLOY:
NO

FINAL VERDICT:
PASS — T6.6F-B01 INDEPENDENT TARGETED VALIDATION COMPLETE

NEXT ACTION:
별도 T6.6F Phase B continuation에서 분류된 필수 검증 gate를 이어서 검증하세요.
```
