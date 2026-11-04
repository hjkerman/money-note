# T6.6F-B03-IC03 설치 세대 교대 교정과 후보 동결

## 1. 작업 판정과 저장소

**PASS — IC03 교정과 후보 동결을 완료했다.** 본 작업은 구현 측 교정·검증·동결이며 독립 감사가 아니다. B03 correctness의 독립 closure는 새 auditor의 의무다. 최종 근거는 [completion.json](../../benchmarks/t66f-b03-ic03/evidence/completion.json)과 immutable pre-freeze `summary.json`이다.

시작 HEAD/main/origin/main/실제 remote main은 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. dirty worktree는 예상된 IC01–IC02/P01–P05/IR01–IR04·artifact hygiene 작업이다. 시작 staged diff는 없으며 staged path/mode/blob/stage의 SHA-256은 `8df943cd1934be9aaa6f1f5b9a0dcc1a796e255019c8936e52c50ab414d535b8`, 물리 index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`다. 모든 Git 조회는 optional lock을 끈다.

시작 시 기존 파일 4,133개의 content/mode와 Git 상태를 기록했다. 여유 디스크는 104,115,200,000B였고 전용 `/tmp/money-note-ic03.bv1_oq77`를 사용했다. 운영 데이터·API·서비스는 사용하지 않았다.

## 2. 역사 IR04 후보

IR04 payload는 `27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3`, archive는 `4655111c579503ef2c0969f82b5dca4830c06ac1123002cd6e8887109728b012`다. 825개 source / 9,129,332B를 재해시했으며 시작 live source와 차이는 없었다. 영향을 받는 두 진단 source도 archive의 실제 `source/` member와 byte-for-byte 같았다. 이 실패 후보와 IR02 후보를 수정하지 않는다.

## 3. 원 IR04-N01 재현

원 `test_ir04_rollover_native.py`의 assertion과 trace 원리는 유지하고 absolute `/tmp` root와 output 경로만 작업 scratch로 치환했다. ASCII와 Unicode 두 case가 수정 전 모두 실패했다.

| literal | native parser | 실제 입력 | 과거 계수 | 교정 후 계수 |
|---|---:|---:|---:|---:|
| `{}` | 1회 | 2B | 2회 / 4B | 1회 / 2B |
| `"한😀"` | 1회 | 9B | 2회 / 18B | 1회 / 9B |

원 실패 결과는 `before-native.*`, 교정 결과는 `ir04-original-after.*`와 `after-rollover-native-*.json`에 구분 보존한다. 원 reproducer는 수정하지 않았다.

## 4. 영향 runtime와 경계

영향은 Python test-only `docs/benchmarks/t66f-b03/counters.py`의 primitive·worker wrapper 설치 수명이다. 제품 parser, backend 금융 엔진, Dart/Flutter 제품·진단 소스와 SQL observer 구현은 변경하지 않았다.

## 5. Delegate 캡처 원인

기존 `instrument()`는 `canonical._parse_json`과 `canonical.encode`를 먼저 캡처한 뒤 installation reference를 얻었다. B가 A의 observer를 캡처한 상태로 멈추고 A가 마지막 reference를 해제하면, B는 새 최초 owner로 시작하면서 이미 퇴역한 A observer를 delegate로 다시 감쌌다. native parse는 한 번이지만 진단 observer 두 개를 통과했다.

## 6. 세대 교대와 teardown 소유권

기존 installation helper는 준비 완료 대기·reference 수와 마지막 reference의 teardown을 이미 관리한다. teardown은 같은 `INSTALL_LOCK` 안에서 완료되고 state identity를 대조해 registry를 제거한다. 이 보호를 얻기 전의 캡처가 문제였다. 새로운 token/history registry를 추가하는 대신 이 기존 소유권 안으로 캡처를 이동했다.

## 7. 최소 교정

`instrument()`와 `instrument_workers()` 모두 installation reference를 먼저 얻고, 해당 세대의 최초 owner만 delegate·wrapper를 생성한다. 이미 활성화된 세대에 합류하는 scope는 기존 wrapper를 재사용한다. reference가 있는 동안 해당 세대는 퇴역하지 못하며 새 세대는 이전 teardown 완료 뒤의 delegate를 캡처한다.

worker도 동일한 선행 캡처 구조였다. 동일 interleaving을 과거 archive source에 적용한 별도 control에서 accepted·rejected dispatch 모두 hold 1개가 남았다. 같은 소유권 이동 뒤 두 경우 모두 native init 1회·pending hold 0으로 끝났다. 이는 별도 worker 실행 알고리즘 변경이 아니라 같은 diagnostic delegate 수명 교정이다.

정확한 IR04 대비 diff는 [implementation.diff](../../benchmarks/t66f-b03-ic03/implementation.diff)에 보존한다. 새 await, 제품 작업 전체를 잠그는 lock, 계수 보정·동일 bytes deduplication, 영구 wrapper 설치는 없다.

## 8. 수명 불변식

| 불변식 | 교정 근거 |
|---|---|
| delegate 한 번 호출 | 캡처를 installation reference 뒤로 이동; native frame oracle로 검증 |
| 이전 세대가 새 세대를 해제하지 않음 | 기존 reference·lock·state identity teardown 사용 |
| 최초 동시 설치 준비 완료 | 기존 readiness/Event 실패 전파 유지 |
| 마지막 reference만 복원 | 기존 refcount 유지; 중간 scope 종료에서 wrapper identity 불변 |
| 유한 상태 | 기존 세 고정 설치 종류만 사용; retired generation 기록 없음 |
| 권한과 분리 | ACTIVE는 기존 계수 context이며 AppState/observation authority를 대신하지 않음 |

## 9. 결정적 concurrency matrix

새 `backend/tests/test_logical_cost_ic03.py`의 고유 14개 case는 trace·Event로 실제 순서를 강제한다. 임의 sleep을 성공 조건으로 쓰지 않는다.

| 경계 | 확인 |
|---|---|
| reference 직전 preemption | ASCII/Unicode/서로 다른 literal, generation·transfer stage 6개 |
| teardown 복원 전·후 정지 | 다음 activation은 이전 teardown 완료까지 대기 2개 |
| 새 scope가 열린 뒤 이전 scope 종료 | 같은 세대 reference가 wrapper를 유지; 동일 bytes 두 실제 호출 모두 계수 |
| nested·반복 세대 | 100회 create/close, reference 3개 nested, 매번 native 복원·registry 비움 |
| 설치 실패·중단 | RuntimeError·KeyboardInterrupt 후 reference 해제와 다음 설치 성공 |
| worker 세대 교대 | accepted·rejected dispatch의 실제 init·hold·completion·원 method 복원 |

최초 동시 scope 2개/4개와 부분 설치 실패는 원 IR04·기존 IC02 oracle에서도 추가 확인했다.

## 10. Exactly-once parse

실제 native parser code object의 `call` frame을 관찰하여 raw buffer를 기록한다. collector의 값을 기대값으로 복사하지 않는다. 동일 입력의 별개 두 호출은 두 event로 남는다. `__wrapped__` identity와 teardown 이후 원 함수 identity도 확인한다. encoding은 C1 decode 자체의 encode와 명시적 encode를 각각 수행하므로 native return 두 개를 독립 관찰해 calls/output bytes와 대조한다.

## 11. Scope와 stage

각 collector의 stage와 실제 raw 길이를 대조한다. generation/transfer/observation을 합산하거나 다른 scope의 이벤트를 나눠 갖지 않는다. 닫힌 collector에서 늦게 수행한 실제 parse가 이전 snapshot을 바꾸지 않는 것도 확인했다. 기존 HTTP/TLS와 Flutter async context는 유지한다.

## 12. 설치 실패와 복구

부분 patch 실패와 BaseException은 설치 본문 실행 전에 전파된다. 이번 scope가 얻은 reference만 기존 finally에서 해제하며 원 primitive를 복원한다. 실패 waiter도 계측 준비가 된 것으로 진행하지 않는다. 다음 정상 설치가 정확한 첫 event를 계수한다.

## 13. IA04 원 nested 재현

원 nested 3 parse/6B oracle을 유지해 실행했다. nested scope마다 wrapper를 새로 만들지 않으며, 서로 다른 실제 event를 합치지 않는다. 구현 측 PASS는 독립 IA04 closure를 의미하지 않는다.

## 14. IR03-N02 원 최초 설치 재현

원 first-install scheduling assertion과 실제 patch 직전 2/4 waiter oracle을 실행했다. 두 번째 scope의 실제 parse 1회/2B가 계수되며, readiness 이전에 본문을 실행하지 못한다. 원 seam뿐 아니라 실제 pre-patch 경계도 검사한다.

## 15. IR03-N01 SQL 회귀

Python/Dart의 CREATE/ALTER/DROP·동일 이름 재생성·DML·transaction/savepoint·cached statement 재사용을 원 literal/native SQLite oracle로 대조했다. ALTER 누적 6B, DROP/recreate 누적 4B의 attempted/effective/committed 계수는 유지됐다. 외부 연결의 미지원 concurrent DDL은 기존처럼 DML 이전에 측정 incomplete로 거부한다. 지원 범위를 넓히거나 좁히지 않았다.

## 16. IA01–IA07

| ID | 현재 구현 측 판정 근거 |
|---|---|
| IA01 | 같은 이름 savepoint의 가장 안쪽 frame과 native durable bytes |
| IA02 | 부분 OR FAIL·batch prefix·rollback/commit |
| IA03 | 주석을 앞에 둔 첫 DML payload |
| IA04 | 원 nested + IR03 first install + IR04 rollover |
| IA05 | 거부 native dispatch hold 반환과 late completion |
| IA06 | 32 owner 허용·33번째 명시 거부·rollback 정리 |
| IA07 | 원 프로그램의 실제 oracle SELECT 두 개는 setup; generation 0건을 별도 엄격 assertion |

현재 동작의 원 oracle과, 결함 존재를 기대하는 승인된 역사 assertion 실행을 구분한다. 원 assertion을 수정하거나 SKIP/XFAIL하지 않았다.

## 17. 계수 정확성

hash는 실제 native constructor/update 입력, validation은 primary 실제 submitted/completed/failed span, SQL은 실제 TEXT UTF8/BLOB의 attempted/effective/committed 경계를 따른다. 세 byte 종류를 unique 데이터량으로 합치지 않는다. 해시·파싱·영속 쓰기를 계측 목적으로 추가하지 않았다. 계수 정의나 SQL 트랜잭션 순서를 변경하지 않았다.

## 18. 유한 자원

설치 registry는 기존 세 고정 종류이고 마지막 reference에서 제거된다. transaction owner 32, savepoint 32, observer table 128, Dart prepared cache 32 등 기존 한도를 유지했다. 새 무제한 generation history나 wrapper chain은 없다. 원 worker cancel/late tail, owner overflow, closed collector와 cache lifecycle 회귀를 재사용했다.

## 19. 실제 D→E와 E3/E4

실제 인증 TLS 통합 6개가 통과했다. 독립 native SHA/parser witness, durable SQLite canonical bytes, accepted sequence·sync_root, cold·identical·card/cash delta, 손상 입력 거부와 이전 accepted 상태 보존, E3 publication/E4 reads 및 OFF/ON 금융 동등성을 확인했다. 최대 작은/중간 fixture만 사용했고 새100k cold는0이다.

## 20. Source-lock과 제품 의미

현재 보호 파일 6개의 exact SHA와 P0 recovery-lineage 소스는 바뀌지 않았다. source-lock 기대 SHA를 갱신하지 않았다. Snapshot v7/OfflineBaseline v4, 금융 raw strings·Unicode/C1, sync_root와 legacy fingerprint 분리, E3 original ticket·동기 final guard→COMMIT, E4 source/provenance, Frozen B/J는 기존 회귀와 실제 경로로 확인한다. binding protocol·schema·관측 TTL/횟수·R1/production activation은 변경하지 않았다.

## 21. Fresh 검증과 원자료

정확한 명령/cwd/exit/source SHA는 `docs/benchmarks/t66f-b03-ic03/evidence/*.json`에, 원문은 gzip과 JUnit에 보존한다. 같은 label이나 과거 evidence 경로를 덮어쓰지 않는다.

| Fresh 범위 | 결과 |
|---|---|
| IC03/IC02/IC01 lifecycle | 50 PASS; 신규 고유 IC03 14개 포함 |
| 원 IR04 trace·설치 oracle | 6 PASS |
| 원 IR03·인접 schema/TLS/trigger oracle | 44 PASS |
| IA07 실제 출력의 별도 엄격 판정 | PASS |
| Flutter 계수·SQL·async·lineage·source-lock·독립 oracle | 104 PASS / 0 FAIL / 0 SKIP |
| 실제 HTTP·E1/E3/E4 | 6 PASS / 0 FAIL / 0 SKIP |
| backend 전체 | 1,460 tests / 1,540 subtests PASS; exit 0, 기존 warning 1개, 1,150.39초 |
| 동결 재구성 source의 원 IR04·IC03 oracle | 20 PASS / 0 FAIL / 0 SKIP |
| 정적·형식·build | Flutter analyze, Ruff, compileall/py_compile, format, git diff check, frontend npm build PASS |

이 표는 실행별 결과이며 겹치는 테스트를 새로운 고유 case로 중복 합산하지 않는다.

초기 도구 오류도 보존했다. venv symlink를 resolve해 system Python으로 실행한 첫 시도는 pytest 미설치로 재현하지 못했으며, 올바른 venv 경로의 `before-native`가 역사 실패 증거다. 새 테스트의 첫 encode 기대값은 C1 decode 자체의 encode를 빼먹어 6개가 실패했다. 실제 native encode return을 관찰하는 oracle로 수정했고 원 독립 assertion이나 제품 계수는 바꾸지 않았다. 이전 worker source의 2 FAIL은 같은 결함의 의도적 역사 control이다.

## 22. 전체 suite 결정

Python wrapper는 전역 primitive와 worker 설치에 닿으므로 backend 전체 suite를 한 번 수행해 통과했다. Flutter 제품·Dart 진단 소스는 IR04/IC02와 정확히 같고 Python 효과는 6개 실제 HTTP/native witness 경로로 새로 검증했다. 따라서 Flutter 전체 수시간 반복은 하지 않고 위 110개 관련 case를 새로 실행했다. 과거 IC02 full backend 1,446/1,540과 Flutter 1,698 PASS/2 SKIP은 역사 결과이며 IC03 fresh full Flutter PASS로 부르지 않는다.

## 23. Source inventory

구현 수정은 `docs/benchmarks/t66f-b03/counters.py` 한 파일이다. 새 source는 `backend/tests/test_logical_cost_ic03.py`, IC03 검증 runner와 동결·재구성 도구다. 새 후보는 기존 825개 전체 source에 원 독립 IR03/IR04 reproducer와 IC03 source를 더한 **850개 / 9,247,384B**다. report/raw output은 별도 context/evidence이며 source digest에 거대한 실험 DB나 build cache를 넣지 않는다.

## 24. 역사 증거

IR02/IR04 실패 후보, 원 IR03/IR04 finding과 reproducer, IC02 보고서와 기존 source-lock은 변경하지 않는다. P02 XML exact 손실은 IR04의 EVIDENTIARY SUBSTITUTE 판정을 유지하며 복구 조사·조작을 하지 않았다. 역사 index stat incident를 byte-identical 보존이라고 바꾸지 않는다.

## 25. Git staged 내용

시작과 끝의 staged path/mode/blob/stage 및 물리 index SHA가 모두 일치했다. 기존 파일 4,133개 중 승인된 `counters.py`만 변경됐고 모든 기존 감사 source·증거·IR02/IR04 sidecar는 유지됐다. 본 작업은 stage/reset/commit/push를 하지 않는다. 최종 대조는 `evidence/final-preservation.json`에 기록한다.

## 26. 새 canonical digest

entries는 path 순서로 정렬하고 UTF8 `json.dumps(ensure_ascii=False, sort_keys=True, separators=(',',':'))`의 SHA-256을 payload digest로 사용한다. file bytes/SHA/POSIX mode와 고정 Git base·tracked deletion·필수 untracked를 기록한다. source가 생성 도중 바뀌면 동결을 거부한다. 최종 payload SHA-256은 `dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370`다. archive SHA와 source payload SHA는 별개다. 초기 proposal은 동결 도구의 metadata/gate 확정 전 inventory이므로 실제 후보 식별에는 최종 manifest만 사용한다.

## 27. 새 source-only snapshot

모든 필수 구현 검증이 PASS한 뒤 별도 `.ic03-` staging에서 archive/member/context를 검증하고 새 digest 경로로 atomic rename했다. 기존 IR02/IR04 directory를 덮어쓰지 않는다. 파일0444·directory0555와 digest로 보호하며 administrator-proof WORM이라고 주장하지 않는다. 실제 경로는 `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370`이며 archive SHA-256은 `145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21`다. [HANDOFF](../../../../audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370/HANDOFF.md)에 다음 독립 auditor가 즉시 실행할 범위를 기록했다. `freeze-reconstruction.json`과 `snapshot-final-check.json`이 확인 근거다.

## 28. 재구성

고정 Git object의 base archive 위에 frozen source/만 overlay하고 모든 파일의 bytes/mode와 선택되지 않은 base blob·실행 비트를 대조한다. 실행 가능한 source를 mutable tree에서 복사해 대체하지 않는다. 재구성된 tree에서도 새 lifecycle14개와 원 IR04 oracle6개가 모두 통과했다. 선택 source 850개와 나머지 base 2,010개를 bytes·mode로 검증했고 시험 후 source identity와 실제 import 경로도 다시 확인했다. 이 추가 검증 역시 구현 측 검증이다.

## 29. 임시 산출물

전용 scratch에 소형 source/SQLite/pytest·경로 adapter와 재구성본을 두고 기존 Flutter/Python 의존성을 재사용했다. 새 build root나100k DB를 만들지 않았다. 모든 원자료·source adapter·동결본을 보존한 뒤 완료된 task-owned scratch만 정리한다. 실제 완료 child와 참조 부재를 확인한 IC03 private scratch와 새 IC03 pycache만 삭제했다. 2,974개 파일을 정리했으며 할당량 기준 약 **107,458,560B(102.5 MiB)**를 회수했다. 원자료·path adapter 17개·20개 재구성 결과와 새 frozen 후보는 보존했고 남은 IC03 scratch는 없다. 일부 기존 system daemon의 fd 접근 제한은 소유권·완료된 private child와 분리해 기록했다. `evidence/cleanup.json`이 근거다. 기존 scratch/build cache와 frozen 후보는 삭제하지 않았다.

## 30. 남는 의무

B03 correctness는 별도 구현 미참여 XHigh 감사가 필요하다. 전체 측정 feasibility, 역사 P03의 397,146/400,532·세 관측 만료 실패, fixed-H/D five-point 비용 grid와 I25 large-N, Android memory/VFS/I/O·physical power loss, R1 large restore/activation, production deployment는 이번 교정으로 해결되지 않는다. B01/B02는 CLOSED로 유지한다.

## 31. 다음 행동

새 snapshot의 HANDOFF를 따라 구현에 참여하지 않은 XHigh auditor가 IR04-N01·IR03-N02·IA04와 인접 계수·scope·자원·실제 HTTP 경계를 독립 재감사한다. 별도의 준비·후보 동결 작업을 다시 요구하지 않는다.

## 최종 footer

```text
T6.6F-B03-IC03 CORRECTION AND FREEZE:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

HISTORICAL IR04 CANDIDATE:
PRESERVED

HISTORICAL IR04-N01 FINDING:
PRESERVED

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY IC03:
NO

PRE-EXISTING UNCOMMITTED SOURCE:
PRESERVED EXCEPT AUTHORIZED IC03 CHANGES

IR04-N01 ORIGINAL REPRODUCER:
PASS

IR04-N01 ROOT CAUSE:
설치 reference 획득 전 캡처한 퇴역 세대 observer를 새 세대 wrapper의 delegate로 재사용했다.

EXACTLY-ONCE PARSE ACCOUNTING:
PASS

2-BYTE INPUT ACCOUNTING:
PASS

DELEGATE CAPTURE:
PASS

INSTALLATION GENERATION HANDOFF:
PASS

TEARDOWN OWNERSHIP:
PASS

PER-SCOPE ATTRIBUTION:
PASS

NESTED INSTALLATION:
PASS

FIRST-INSTALL CONCURRENCY:
PASS

REPEATED ACTIVATION/CLOSE:
PASS

IA01:
PASS

IA02:
PASS

IA03:
PASS

IA04:
IMPLEMENTATION PASS — INDEPENDENT CLOSURE PENDING

IA05:
PASS

IA06:
PASS

IA07:
PASS

IR03-N01:
PASS

IR03-N02:
PASS

HASH BYTE COUNTERS:
PASS

VALIDATION INPUT SPANS:
PASS

SQL LOGICAL WRITE BYTES:
PASS

TRANSACTION/SAVEPOINT ACCOUNTING:
PASS

STAGE ATTRIBUTION:
PASS

SCOPE AND RESOURCE BOUNDS:
PASS

BACKEND CONCURRENCY/TLS:
PASS

FLUTTER ASYNC/NATIVE:
PASS

REAL D3→HTTP→E2→E1:
PASS

E3/E4:
PASS

PRODUCT EQUIVALENCE:
PASS — 문서화된 지원 측정 범위

SOURCE-SHA GUARDS:
PASS

FRESH IC03 TESTS:
14 PASS / 0 FAIL / 0 SKIP

FULL BACKEND:
PASS — 1460 tests / 1540 subtests

FULL FLUTTER:
NOT RERUN — 관련 110개 fresh PASS

NEW CANDIDATE PAYLOAD SHA-256:
dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370

NEW CANDIDATE SOURCE INVENTORY:
850 files / 9247384 bytes

NEW SNAPSHOT PATH:
/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370

NEW SNAPSHOT ARCHIVE SHA-256:
145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21

NEW SNAPSHOT RECONSTRUCTION:
PASS — source850개·base2010개 확인, 재구성 테스트20개 PASS

INDEPENDENT HANDOFF:
READY

HISTORICAL P02 XML LOSS:
RECORDED — NO FABRICATED RECOVERY

HISTORICAL GIT INDEX STAT INCIDENT:
RECORDED — STAGED CONTENT CHECKED

TEMPORARY ARTIFACTS:
IC03 source/SQLite/pytest·재구성 scratch 삭제; 할당량 기준 약102.5 MiB 정리
원자료·adapter·새 snapshot 보존; 기존 scratch/build cache는 보존

NEW FULL N=100K COLD RUNS:
0

B03 INDEPENDENT CORRECTNESS:
OPEN — NEW AUDIT REQUIRED

PHASE B FIVE-POINT COST GRID:
NOT VERIFIED

E3 I25 LARGE-N SCALING:
NOT VERIFIED

FULL-SCALE MEASUREMENT FEASIBILITY:
NOT VERIFIED

B01:
CLOSED

B02:
CLOSED

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY/VFS/POWER-LOSS:
NOT VERIFIED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

PRODUCT SOURCE CHANGES:
NONE — test-only counters.py의 primitive/worker 설치 소유권만 수정

BINDING PROTOCOL:
UNCHANGED

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
PASS

NEXT ACTION:
새 동결 후보의 HANDOFF에 따라 구현 미참여 XHigh auditor가 B03 정확성 재감사를 수행하세요.
```
