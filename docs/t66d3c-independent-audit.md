# T6.6D3c 독립 구현 감사

## A. 요약 판정

**FAIL — TARGETED D3c CORRECTION REQUIRED**

`D3C-A01` **MEDIUM / CONFIRMED FAILURE** 한 건을 확인했다. `RetentionSandbox.connect()`의
마지막 inode 검사와 실제 SQLite open 사이에 파일이 교체되면, 다른 inode의 DB에서 실제 삭제가
COMMIT된 뒤 소유권 오류가 발생한다. 실제 GC를 자가 소유 synthetic DB에만 허용한다는
binding 경계를 위반한다. 같은 experimental schema/fence를 가진 synthetic 사본 두 개로 재현했으며
생산 DB 접근, 금융 행 손상, 보호 중인 graph의 삭제를 입증한 것은 아니다.

독립 **74개 사례 중 73 PASS / 1 FAIL**, 전체 backend **1,284 tests + 1,540 subtests PASS**다.
보존 root, historical certificate 분리, 정상 파일에서의 mark/sweep, worker/GC 직렬화,
post-GC 재구성은 검증을 통과했다. 일반 회귀 성공이 admission 반례를 해소하지는 않는다.
확정된 파일 admission 결함을 먼저 수정하고 재감사해야 한다. T6.6E 시작과 배포는 승인하지 않는다.

## B. 감사 commit과 저장소 상태

감사 시작 시 다음 값이 모두 일치했고 working tree는 clean이었다.

| 항목 | 확인 값 |
| --- | --- |
| Branch | `main` |
| `HEAD`, local `main`, `origin/main`, 실제 remote `main` | `bcb0c47d42c5fb770ce40b70b0c14ad30d0c15f5` |
| Baseline | `e1b6e6493c6e2644275f37173f25a46be84b8173` |
| 구현 diff | 13 files, 5,847 insertions / 9 deletions |

두 commit의 존재와 전체 변경 범위를 확인했다. 보고서 작성 직전 `git ls-remote --exit-code origin
refs/heads/main`도 지정 target을 반환했다. 감사 산출물 commit 뒤 HEAD가 바뀌는 것은 구현 target
변경이 아니다. 감사 commit은 이 문서와 `docs/benchmarks/t66d3c-audit/`만 포함한다.
자기 hash 순환을 피하기 위해 감사 commit hash와 최종 remote 상태는 최종 응답에 명시한다.

## C. 범위와 독립성

이번 작업은 D3c 보존·historical evidence·GC와 D3b worker lifetime 연계를 감사했다.
D3b 전체 architecture를 반복 감사하거나 T6.6E/R1을 구현하지 않았다. 원 구현과 correction에
참여하지 않았으며, 구현자의 PASS·benchmark 수치를 독립 결과로 재사용하지 않았다.

`AGENTS.md`, project-state/domain-model/known-issues, architecture 신뢰 경계, offline-mode,
binding T6.6C, D3a/D3b 및 D3c 보고서, 실제 source와 tests를 대조했다. 권한·개발 격리·검증은
security/runbook의 기존 경계도 따랐다. 금융 projection authority는 기존 backend이며 새 금융
계산 엔진을 작성하지 않았다. 독립 fact/Patricia 계산은 구조 무결성 검사다.

세 증거 층을 모두 사용했다. Source에서는 SQL·FK·trigger·transaction을 추적했고, 별도
SQLite/JSON/hash oracle로 삭제 집합을 계산했으며, synthetic 실제 삭제·경쟁·SIGKILL·ASGI 취소를
실행했다. `backend/tests`의 fixture나 구현자의 reachability helper를 독립 기대값에 사용하지 않았다.

## D. Binding 보존 정책

`docs/t66c-delta-sync-protocol.md:331`의 §16-S를 규범으로 적용했다. 현재 complete 세대,
유효 observation의 다섯 root, 아직 객체가 필요한 실제 native worker, 미해결 publication/recovery,
승인된 explicit obligation은 보호한다. Historical certificate는 증거를 보존하되 영구 graph root로
취급하지 않는다. 임의 previous 세대의 자동 rollback 보존은 요구하지 않는다.

과거 날짜의 authoritative 금융 행도 보존 대상이다. 모바일 frozen B/J·pending·기존 Snapshot 파일
보존과 이 객체 GC를 혼동하지 않았다. 실제 삭제는 현재 단계에서 자가 소유 synthetic profile에만
허용된다. 마지막 조건에서 `D3C-A01` 위반이 확인됐다.

## E. 전체 변경 파일

| 파일 | 실제 변경과 감사 결과 |
| --- | --- |
| `backend/isolated_sync/finalization.py` | epoch bootstrap hook 추가; accepted generation/fence 계약 유지 |
| `backend/isolated_sync/http.py` | opt-in observation DELETE/release와 기존 worker budget 사용 |
| `backend/isolated_sync/observation.py` | admission/charge/replay 확장 hook; terminal guard 유지 |
| `backend/isolated_sync/retention.py` | lifecycle, explicit roots, mark/sweep |
| `backend/isolated_sync/retention_schema.py` | version 1,000,005, evidence FK 분리, live roots/count/fence |
| `backend/tests/test_isolated_sync_retention.py` | 신규 57개 구현자 사례 |
| `docs/architecture.md` | 서버 보존 경계 설명 |
| `docs/benchmarks/t66d3c/summary.json` | 48 cells / 960 samples / 4 maintenance 결과 |
| `docs/project-state.md` | D3c 상태 |
| `docs/specimens/t66d3b-release-artifacts.json` | financial_engine source manifest hash만 변경 |
| `docs/t66c-delta-sync-protocol.md` | 승인된 §16-S 명확화 |
| `docs/t66d3c-implementation.md` | 구현 보고서 |
| `scripts/benchmarks/t66d3c.py` | 명시 synthetic benchmark |

Production schema/routes/startup/auth defaults, 금융 공식, Snapshot v7, OfflineBaseline v4,
journal/reconciliation, Flutter/mobile 구현 변경은 없었다. Release bundle을 실제 source에서 생성해
파일과 일치시켰고 base64 길이·SHA-256을 검사했다. Raw/projection schema와 policy registry 및
versions는 baseline과 같고 engine manifest만 source 변경을 반영했다.

## F. Retention root 목록

| 정당한 보존 의무 | 실제 보호 경계 |
| --- | --- |
| 현재 accepted complete 세대 | `sync_current`의 raw/index와 current certificate의 input; live FK roots 3개 |
| Available observation | raw/index/input/hot/control의 5개 active pin |
| retired지만 release 미완료 | lifecycle `released=0`인 기존 다섯 pin을 계속 보호 |
| 실제 materialization worker | 같은 DB의 `BEGIN IMMEDIATE` transaction으로 GC 삭제와 직렬화 |
| publication/finalization 미완료 | 하나의 write transaction; 미commit 객체는 외부 GC에 보이지 않음 |
| crash recovery | SQLite rollback/WAL와 원자 current/root trigger; mark는 durable 재사용하지 않음 |
| 명시 승인 obligation | `scope='explicit'` FK roots; arbitrary HTTP download 권한은 부여하지 않음 |
| 공유 descendant | 모든 root의 typed reachability 합집합으로 보존 |

`retention.py:211`은 직접 current/certificate/pins/lifecycle와 persisted roots를 교차 검사한다.
Historical certificate 자체, pin 없는 hot/control cache, 존재하지 않는 backup 의무를 추가 root로
발명하지 않았다. Transfer의 네 root만 공개되고 다섯 번째 input-proof는 내부 보존에 남는다.

## G. Historical certificate 증거

`sync_commits`의 tx identity, base/target epoch·revision, raw/index/input digest, change_count,
complete status를 보존한다. `sync_capture_commits`, `sync_tx_fence`, `sync_authority_fence`도
GC가 삭제하지 않는다. 실제 GC 전후 이 행들을 직접 SELECT하여 같음을 비교했다.

완료된 historical publication의 증거와 현재 재구성 authority가 분리됐다. `complete`는 과거
publication이 완료됐다는 증거이며 객체가 영구 남았다는 보증으로 새롭게 해석하지 않는다.
현재 acceptance는 `sync_current`와 실제 roots를 검사하고 observation lookup은 기존 credential,
Target, lease와 pin 상태를 요구한다. 과거 certificate만으로 download observation을 만들 수 없다.

## H. FK와 object reference 분리

`retention_schema.py:20`과 `:117`은 세 테이블의 명시적 `REFERENCES sync_objects(hash)`만
분리한다. 대상은 `sync_commits`, `sync_observations`, `sync_observation_pins`다. Digest 필드,
CHECK·NOT NULL, certificate identity 및 deferred coverage fence는 유지된다.

현재 `sync_current`의 object FK와 새 `sync_retention_roots`의 object FK가 live availability를
보장한다. D3c 설치는 exact D3a schema를 확인하고 FK OFF를 BEGIN 전에 설정한 별도 owned
connection에서 테이블을 재구성하며 FK 검사 후 commit한다. Production version 4 migration이 아니다.
FK retirement COMMIT 전후 SIGKILL에서 각각 version 1,000,004 / 1,000,005로 원자 복구했다.
금융 행·certificate evidence·current 재구성은 모두 보존됐다.

## I. 현재 세대 보호

`retention_schema.py:67`의 current INSERT/UPDATE trigger는 current의 세 root를 같은 write
transaction에서 바꾼다. `Collector._roots()`는 current certificate와 실제 root 집합을 검증한다.
Sweep은 writer lock 안에서 fence, exact schema, accepted generation을 다시 확인한다.

독립 orphan 계산과 실제 삭제의 차집합이 일치했다. 모든 정상-file GC·crash·경쟁 사례에서 현재
raw 11 tables, 구조 fact, global Patricia와 내부 input proof를 재구성했다. Future finalization도
historical object 회수 뒤 성공했다.

## J. Observation과 pin 보호

다섯 pin은 하나의 transaction에서 publish/release된다. Role/hash/active와 Target/certificate,
lifecycle를 `RetentionRepository._record()`가 교차 검사한다. `retention.py:83`의 release 중 오류가
나면 partial pin release는 rollback되고 확정 retirement만 sticky하게 남을 수 있다.

다섯 pin 각각의 중간 fault, retired, before/after COMMIT의 8개 독립 사례를 실행했다.
재시도는 idempotent하고 네 thread의 동시 release에서도 underflow가 없었다. 잘못된 principal의
release는 거부됐다. Release 미완료의 retired record는 graph를 계속 보호한다.

## K. Transfer/native worker 보호

`transfer.py:283`의 `TransferRepository.acquire()`는 observation lookup, typed-path object
검증, 모든 chunk/base64 payload 준비와 terminal guard를 하나의 `ObservationRepository._connection()`
안에서 수행한다. 이 connection은 `observation.py:261`의 `BEGIN IMMEDIATE`를 소유한다.

Native worker가 materialization에서 막힌 동안 GC는 write lock을 얻지 못했다. HTTP task를
취소해도 worker의 transaction과 permit이 유지됐다. 객체 의존성이 끝난 뒤에는 완전 materialize된
응답이 있으므로 GC가 원본을 회수할 수 있었다. Network await 동안 DB transaction을 유지하지 않았다.

## L. D3B-M01 보존

`workers.py`는 이번 구현 diff에서 바뀌지 않았다. Permit은 HTTP coroutine finally만으로
반환되지 않고, `NativeJob.invoke()`의 실제 native 종료 또는 locked pre-start abort 뒤 반환된다.
공유 `threading.Event`와 shielded supervisor를 사용하는 기존 correction 경계가 보존됐다.

실제 ASGI task 두 개를 `Task.cancel()`로 반복 취소한 뒤 두 native worker를 계속 barrier에
두었다. 추가 여섯 요청은 모두 503이었고 세 번째 native entry는 없었다. 독립 실제 entry/exit
counter의 최대는 **2**, 종료 후 permit은 **2**, cancellation 뒤 protected ASGI event는 **0**이었다.
기존 D3B-M01 correction 25개도 전체 backend 회귀에서 모두 통과했다.

## M. 독립 reachability oracle

`docs/benchmarks/t66d3c-audit/test_audit.py`는 direct SQLite SELECT로 current/certificate,
unreleased observation의 다섯 pin과 explicit roots를 읽는다. Production GC의 `_roots`,
`mark`, `PathResolver`, `Store.edges`를 기대 집합 생성에 호출하지 않는다.

JSON을 직접 decode하고 별도 C1 encoder와 `hashlib.sha256` domain hash를 검사한다. Raw-root의
11-table 순서, snapshot table/height/count/min/max, Patricia prefix/count, ref byte length,
namespace와 persisted typed edge 집합을 독립 검증한다. 별도 DFS로 `R`을 만들고 `U=O-R`을 구한다.
GC가 제시한 candidates와 실제 남은 객체를 각각 대조한다. Cache preimage도 reachable inline row에서
별도로 계산한다. 실제 정상-file 삭제는 모두 `U`에 속했다.

## N. Mark/sweep transaction 분석

1. `retention.py:235`에서 read transaction의 첫 fence read가 WAL snapshot을 고정한다.
   전체 graph·edge·count·budget·root를 검증해 owner-bound memory mark를 만든다.
2. `:322`에서 batch마다 새 `BEGIN IMMEDIATE`를 얻는다. `:334`의 fence가 다르면 삭제 전에
   `REJECT_GC_STALE_MARK`로 끝난다. Publication/root/object/count 변경 trigger는 같은 transaction의
   fence를 증가시킨다.
3. Exact schema/current acceptance 확인 후 incoming=0, pins=0인 candidate만 부모 edge부터
   삭제한다. FK와 delete trigger가 추가로 보호한다. Cache 후보도 동일 fence 안에서 삭제한다.
4. `:367`에서 한 batch를 commit하고 connection을 닫는다. `:373`은 write lock 밖에서 전체
   새 mark를 계산한다. 다음 batch는 그 새 snapshot만 사용한다.

동시 GC도 첫 batch 이후 다른 mark의 fence가 stale해진다. Mark의 owner token과 fence 때문에
arbitrary hash list나 이전 process의 stale plan을 정상 API로 재사용하지 못한다. Failed batch는
rollback된다. 다만 파일 identity를 실제 열린 DB에 결합하지 못하는 `D3C-A01`은 이 transaction
논리가 승인한 DB에서 수행된다는 전제 자체를 깨뜨린다.

## O. Writer/GC 경쟁

| 요구 사례 | 독립 실행과 관측 |
| --- | --- |
| W1 mark 뒤 새 세대 publish | stale fence로 삭제 0 |
| W2 finalization 미commit | sweep write lock 거부; commit 뒤 기존 mark stale |
| W3 deletion batch 사이 writer | 첫 batch 보존 graph 확인, 다음 stale plan 거부 |
| W4 epoch 변경 | current/root/pin fence 변화로 stale 거부 |
| W5 기존 candidate hash 재사용 | 과거와 같은 raw hash가 current가 된 뒤 stale 삭제 거부 |
| W6 writer/GC write ownership 경쟁 | `BEGIN IMMEDIATE` 직렬화; fresh current 완전성 유지 |

Mark의 WAL snapshot을 실제 열어 둔 채 writer/observation/epoch publication을 별도 connection에서
commit하는 세 사례도 실행했다. Publication은 read mark 때문에 막히지 않았고, 뒤 sweep은 stale
mark를 거부했다. 자동 무제한 retry나 queue는 추가하지 않았다.

## P. Observation/GC 경쟁

새 observation pin publication, release, epoch 변경, explicit root 등록 뒤 기존 mark는 모두
stale로 거부됐다. Expiry exact boundary, duplicate release, metadata reclaim 중 crash,
clock rollback, reclaimed ID/nonce retry, 공유 principal graph를 각각 실행했다.

한 principal의 release가 다른 principal의 공유 객체를 지우지 않았다. 공유 bytes가 같아도 다른
principal의 observation으로 transfer하면 403이었다. Retired observation ID는 metadata 제거 뒤에도
인가되지 않았다. Exact lease boundary는 terminal 거부로 끝났고 pin release 전까지 그래프를 보호했다.

## Q. Transfer/GC 경쟁

| 독립 시점 | 관측 결과 |
| --- | --- |
| AnyIO limiter에서 native 시작 전 취소 | native entry 0, permit 2 복구, GC 뒤 late start 없음 |
| 인증 직후 취소 | worker Event 설정, native 종료 전 permit 유지, GC 안전 진행 |
| `objects_prepared`에서 취소 | worker가 DB lock 소유; GC locked 거부; 보호 graph 유지 |
| `serialized`에서 취소 | materialization 완료 후 GC 가능; protected response 없음 |
| terminal 직전 취소 | terminal guard를 우회한 성공 없음 |
| 두 worker 생존 중 반복 취소·추가 6요청 | 최대 native 2, 추가 요청 모두 503 |
| network body send 대기 중 disconnect 상당 취소 | 이미 materialize한 source를 GC로 회수; 취소 뒤 body 없음 |
| materialization 예외 | HTTP 500 `STORAGE_FAILED`, permit/connection 정리 후 GC·유효 요청 복구 |
| active worker 중 shutdown | 신규 admission 503, 종료 전 permit 유지, 종료 뒤 두 permit 복구 |

ASGI event 자체를 기록했다. Network 사례의 `http.response.start`는 취소 이전에 발생했고
protected body는 전송되지 않았다. 다른 취소 barrier 사례는 response event가 하나도 없었다.

## R. Crash/restart

독립 child process에 실제 SIGKILL을 가하는 **13개 경계**를 실행했다.

| 경계 | restart의 persisted 상태 |
| --- | --- |
| retirement COMMIT 전/후 | available+5 pins / retired+5 pins |
| pin release COMMIT 전/후 | available+5 pins / retired+0 pins |
| mark 생성 뒤 | 삭제 0, 새 mark로 재개 가능 |
| deletion batch COMMIT 전/후 | 삭제 0 / 정확히 2 objects 삭제 |
| metadata reclaim 중/COMMIT 뒤 | 기존 retired metadata 유지 / 안전하게 제거 |
| epoch publication COMMIT 전/후 | 기존 current/pins / 새 current와 old pins 0 |
| historical FK migration COMMIT 전/후 | old profile / 새 profile, certificate 증거 보존 |

모든 경우 fresh connection에서 financial rows/revision, FK/integrity, current certificate/root,
observation pin 상태를 검사했다. 별도 fresh process의 current 재구성, dry mark 및 후속 actual GC도
통과했다. SIGKILL은 process interruption 검증이며 hardware power-loss 보증으로 표현하지 않는다.

## S. Clock rollback과 epoch

900초 exact expiry 후 retirement/metadata reclaim을 수행하고 clock을 원래 시점으로 되돌렸다.
기존 ID와 nonce는 다시 인가되지 않았다. User inactive 뒤 reactivation에서도 replay evidence를
남겨 새 Target로의 부활을 막았다. 원 credential 행 삭제와 epoch 변경은 replay 회수 근거로 처리됐다.

`RetentionConnection._epoch_bootstrapped()`는 새 current publication transaction 안에서 old
observation retirement·pin inactive·released 상태를 변경한다. Bootstrap 중 crash에서 current와
old pin 상태가 따로 commit된 반례는 없었다. 기존 D3a M01/M02 129개 observation suite도 통과했다.

## T. Metadata 회수

`retention.py:115`의 maintain은 인증/expiry/epoch 상태로 release할 항목을 정하고 안전한
released record만 회수한다. Pin·observation 삭제와 budget refund, compact replay insert가 하나의
transaction이다. Pin 없는 hot/control view는 authority로 취급하지 않고 prune한다.

같은 credential·namespace가 다시 유효해질 수 있으면 nonce/request digest를 512-byte logical
charge로 보존한다. 단순 session 시간 만료나 user inactive를 영구 재사용 불가로 간주하지 않는
source 경계를 확인했다. Historical certificate/fence 행을 budget 회수 때문에 삭제하지 않았다.

## U. Quota와 budget

실제 기본값은 lease 900초, principal별 4개, 총 observation records 4,096개, logical total budget
64 MiB이며 개별 metadata 한도는 8 MiB다. 기존 값은 바뀌지 않았다.

독립 테스트는 records/principal limit=2, logical budget=120,000으로 낮춰 5차례 create/expire/reclaim
cycle을 실행했다. 과도한 요청 거부, active lease 보존, lifecycle/replay charge 합계와 used_bytes의
일치, reclaim 뒤 quota 복구를 확인했다. 전체 default 4,096개를 동시에 채우는 stress는 실행하지
않았다. 같은 SQL 조건과 accounting을 실제 configured boundary에서 검증했고 source의 정수
CHECK와 합계 검증도 확인했으므로, 이것만으로 별도 correctness blocker를 만들지 않았다.
기존 credential의 compact replay evidence는 유한 budget을 계속 소비할 수 있으며 무한 nonce의
무한 수용을 보장하지 않는다.

## V. GC admission과 격리

일반 wrong path, pre-existing symlink, replaced inode, 잘못된 owner marker, ATTACH, old profile의
6개 거부는 통과했다. Constructor는 기존 DB path/env를 받지 않고 Collector 기본은 dry-run이다.
Normal backend startup/금융 route에는 GC 연결이 없으며 HTTP GC endpoint도 없다.

그러나 **마지막 pre-open check 직후**의 파일 교체는 거부하지 못했다. `D3C-A01`은 private
ownership method를 무력화하지 않고 실제 filesystem interleaving만 삽입했다. Source의 path stat과
SQLite open은 별개 operation이고 open된 inode를 commit 전에 확인하지 않는다.
Admission 결과는 **FAIL**이다. 구체적인 precondition과 최소 수정은 AE에 기록했다.

## W. Corruption과 fail-closed

15개 독립 corruption 사례에서 actual GC를 호출했다. Object body, C1 version, raw schema,
namespace, kind, typed edge, incoming count, pin count, logical budget, pin hash, lifecycle,
current certificate, missing root, unknown schema, row-cache preimage를 각각 변조했다.
모두 mark/admission 오류를 반환했고 object 삭제 수는 0이었다.

변경한 payload의 hash도 함께 재작성하여 모든 self-consistent corruption 조합을 만든 것은 아니다.
그런 조합을 전부 실행했다고 주장하지 않는다. Source는 hash 외에도 typed child, namespace,
table/version, persisted edge/count, root/lifecycle/budget를 검증한다. Cycle은 raw height 감소와
Patricia prefix 증가의 typed 검증에 의해 정상 graph로 통과하지 못한다. Hash collision은 SHA-256의
충돌 저항성을 전제로 하며 실험으로 입증하지 않는다.

## X. Historical 세대 회수와 기존 blocker

Historical certificate를 영구 root로 포함한 별도 DFS와 승인된 live roots의 DFS를 비교했다.

| 독립 fixture | current/live reachable | 모든 certificate reachable | certificate-only 실제 회수 |
| --- | ---: | ---: | ---: |
| label mutation 3회 | 250 | 283 | 33 |
| 같은 mutations 뒤 epoch bootstrap | 250 | 533 | 283 |

이는 과거 진단의 162/178 또는 152/328 fixture를 복제한 수치가 아니다. 같은 반례 구조에서
historical-only graph가 실제 SQLite에서 없어지고 certificate evidence는 남는 효과를 입증했다.
별도 old observation release fixture에서는 objects 35개와 cache preimage 3개를 회수하고 이후
writer finalization을 실행했다. Old observation이 유효한 동안에는 해당 graph를 유지했다.

## Y. Post-GC 재구성

Old와 current observation을 모두 유효하게 유지한 실제 GC 뒤 authenticated D3b ASGI 경로로
각각 재구성했다. 반환한 parent의 typed child를 따라 batch 요청하고 base64/C1/domain SHA-256,
ref bytes, observation binding과 immutable retry를 검증했다. 각 observation은 HTTP 14개 batch로
222 objects를 받아 해당 시점 SQLite raw state와 일치했다.

Hot/control root와 12개 projection의 구조도 확인했다. 민감 설정 값은 wire에 없었고 내부
input-proof root 요청은 거부됐다. Wrong principal 및 다른 observation의 root/path 권한을
검사했다. Future writer와 fresh-process current 재구성도 historical GC 뒤 성공했다.

## Z. 11 tables와 global Patricia

`ledger_entries`, `monthly_panels`, `cash_flows`, `card_payment_batches`,
`card_payment_batch_items`, `card_payment_events`, `card_payment_allocations`,
`card_payment_deferrals`, `notification_candidate_registrations`, `app_settings`, `app_labels`
**11/11**을 독립 SELECT와 비교했다. Private setting은 authoritative DB 보존과 wire 제외를
각각 검사했다.

독립 raw state에서 PK/unique/reference/reverse/aggregate/context facts를 구성하고 별도 Patricia
encoder로 104 facts와 global root를 계산했다. Production `Index.build()`나 `build_facts()`를
기대값에 사용하지 않았다. Current input-proof도 별도 날짜/index 구성과 row hash로 검증했다.
금융 공식이나 backend projection 계산을 복제하지 않았다.

## AA. Storage 회수 증거

두 독립 성능 DB에서 객체/cached row 집합과 body bytes를 direct SQLite oracle로 계산하고 실제
삭제 결과와 비교했다. 두 번째 GC의 object/cache 삭제는 모두 0이었다.

| ledger rows | objects 전→후 | object/cache 삭제 | logical bytes | main file 전→후 | freelist 전→후 |
| --- | --- | --- | ---: | --- | --- |
| 376 | 1,701→1,673 | 28 / 2 | 24,034 | 3,932,160→3,932,160 | 0→8 |
| 10,000 | 40,255→40,215 | 40 / 2 | 30,240 | 79,642,624→79,642,624 | 0→11 |

합계 **54,274 logical bytes**, 물리 main file 크기 변화는 두 DB 모두 **0 bytes**다.
Page size는 4,096이고 측정 시점 WAL bytes는 모두 0이었다. VACUUM은 실행하지 않았다.
Freelist 증가는 page 재사용 여지를 보여주며 disk-file shrinkage를 뜻하지 않는다.

구현자 artifact의 4개 DB 합계 3,300 objects / 180 cache rows / 23,313,490 bytes는 JSON 산술과
측정 script를 대조했다. 그 네 fixture의 960 samples를 이번 감사가 재실행한 수치로 제시하지 않는다.

## AB. GC 성능

독립 fixture의 10k는 `ledger_entries` 10,000행이다. 1행은 current, 나머지는 archive이며
다른 열 개 테이블도 채웠다. Bootstrap/seed/oracle은 GC timing 밖이고 actual collect의 lifecycle,
첫 mark, delete, 후속 full mark를 외부 monotonic clock으로 쟀다.

| 규모 | actual GC(s) | 첫 mark(s) | sweep+재검증(s) | deletion write-lock(ms) |
| --- | ---: | ---: | ---: | ---: |
| 376 | 6.169 | 3.068 | 3.053 | 52.497 |
| 10,000 | 119.624 | 59.422 | 60.097 | 50.244 |

Lock 값은 실제 실행한 source의 BEGIN 성공 뒤~COMMIT timer이며 BEGIN 대기와 전체 sweep 시간과
구분했다. 별도 작은 batch=7 historical 사례에는 67.68ms의 기록도 있다. 이 수치를 전체 가능한
부하의 상한으로 주장하지 않는다. Configured seconds는 SQL 한 문장을 중단하는 hard deadline이 아니다.

구현자 10k fixture는 bounded card/cash mutations 뒤 41,190 objects / 968 garbage objects를
사용했고 총 261.10초, lock 562.56ms였다. 첫 mark 179.66초와 재검증이 비용 대부분이며 benchmark의
`sweep_ms`는 순수 삭제 시간이 아니다. 이번 fixture와 garbage 수가 달라 속도 개선으로 해석하지 않는다.

Post-batch 전체 재검증 때문에 maintenance는 batch 수 B에 대해 O(N×B)이며, garbage가 크고
batch 크기가 고정이면 최악 O(N²)에 접근할 수 있다. 이 반복은 source로 확인했고 비차단 최적화
후보다. Mark는 write lock 밖이지만 WAL checkpoint를 지연할 수 있다. 1,000,000 records / 1GiB
encoded cap은 decoded Python peak RSS의 상한이 아니다. Production contention 성능이나 cold-cache
disk I/O는 측정하지 않았다.

## AC. 정상 요청 성능과 복잡도

독립 HTTP 측정은 각 경로 2 warmups+5 samples, 2 sizes×3 workloads로 **30 measured samples**다.
SQL trace와 EXPLAIN을 수집했다. Trace를 포함한 개발 호스트 latency이며 matched before/after
실험이 아니므로 D3c 순수 추가 overhead로 해석하지 않는다.

| 경로 | 376 median(ms) / SQL 호출 | 10k median(ms) / SQL 호출 |
| --- | --- | --- |
| manifest retry | 147.34 / 558 | 200.62 / 558 |
| raw root | 118.88 / 431 | 183.68 / 431 |
| ledger leaf | 302.22 / 433 | 441.77 / 434 |

추가 leaf 호출 한 개는 tree 높이 증가와 일치했다. Historical certificates/objects/ledger의
필수 전체 scan은 없었다. EXPLAIN의 `SELECT rowid FROM ledger_entries LIMIT 0` scan 표시는
schema probe다. 별도 SQLite bytecode에서 행 순회 전에 `Goto→Halt`로 종료함을 확인했다.

Source의 mutation/D1/D2b에는 고정 trigger/accounting과 epoch hook만 추가됐고, D3a/D3b 요청은
indexed current/certificate/root/path 접근을 유지한다. Explicit GC의 전체 순회는 정상 요청에서
호출되지 않는다. Observation quota count는 bounded metadata 접근이다. 구현자의 48-cell benchmark는
warm measurements이며 trigger 내부 statement를 별도 세지 않고, GC contention과 동시에 정상
요청 latency를 측정하지 않았다. Source·query plan·회귀를 합쳐 mandatory historical O(N) 추가는
발견하지 못했다.

## AD. 전체 독립 사례와 회귀

| 독립 신규 사례군 | 사례 수 | 결과 |
| --- | ---: | --- |
| historical 실제 GC, post-GC HTTP, 기존 blocker 두 fixture | 4 | PASS |
| release fault·동시 release | 9 | PASS |
| expiry/revocation/inactive/epoch, quota cycles | 5 | PASS |
| stale fence 5종, 두 GC, 미commit writer, WAL overlap 3종 | 10 | PASS |
| SIGKILL 및 historical FK migration | 13 | PASS |
| persisted corruption | 15 | PASS |
| 기본 admission 거부 | 6 | PASS |
| hash 재사용, principal 공유·explicit protection | 2 | PASS |
| 취소·materialization·network·예외·shutdown 통합 | 9 | PASS |
| open inode TOCTOU 안전 회귀 | 1 | **FAIL** |
| 합계 | **74** | **73 PASS / 1 FAIL** |

각 실제 관측은 `docs/benchmarks/t66d3c-audit/results.json`에 있다. 처음 72개 전체 실행은
`1 failed, 71 passed in 116.46s`였고, 뒤에 추가한 original-blocker 두 사례는 `2 passed`였다.
Harness 개발 중 commit interception, read-only path property, HTTP error 기대값을 바로잡은
이전 실패는 제품 결함으로 집계하지 않았다. 최종 admission 반례는 독립 초기 probe와 최종 suite에서
반복 확인했다. Instrumentation은 runtime fault hook·barrier·mock와 파일 interleaving이며 tracked
구현 파일을 바꾸지 않았다.

| 실행 검증 | 직접 관측 결과 |
| --- | --- |
| 전체 backend | **1,284 tests + 1,540 subtests PASS**, pytest 1,333.34초, exit 0 |
| 포함된 D3c / D3B-M01 | 57 / 25 PASS; 전체 backend 수에 포함 |
| D3b transfer / transfer failures | 94 / 26 PASS |
| D3a observation M01/M02 | 129 PASS |
| D2b finalization / inputs | 73 / 30 PASS |
| D2a canonical / facts / Patricia / roots / segments | 34 / 50 / 11 / 10 / 21 PASS |
| D1 capture | 113 PASS |
| Snapshot suite / export metadata | 70 / 9 PASS |
| authoritative-state / 금융 / migrations | 전체 backend에 포함, PASS |
| safety/diagnostic | **59 PASS**, 3.97초, exit 0 |
| frontend | **21 tests / 6 files PASS** |
| Ruff 구현·tests·scripts 및 새 audit artifacts | PASS |
| compileall, frontend build, shell 구문 | PASS |
| `git diff --check` | PASS |

실행 명령은 다음과 같다. 성공 로그 전체를 출력하지 않고 summary/JUnit/exit를 보존했다.

```sh
cd backend
../.venv/bin/python -m pytest -q --durations=10 --junitxml=/tmp/mn-d3c-audit/backend-full.xml
cd ..
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
npm --prefix frontend run test
npm --prefix frontend run build
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts/tests scripts/benchmarks
.venv/bin/python -m ruff check docs/benchmarks/t66d3c-audit
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts/benchmarks
bash -n scripts/deploy-server.sh scripts/release-mobile.sh scripts/dev-server.sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py --junitxml=/tmp/mn-d3c-audit/independent-complete.xml
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py -k original_historical_certificate_root_blocker
.venv/bin/python docs/benchmarks/t66d3c-audit/benchmark_audit.py
git diff --check
```

첫 독립 suite 실행 당시 72개였고 최종 파일에는 추가 두 개를 포함한 74개가 있다. 재실행하면
전체 74개가 수집된다. 알려진 안전 실패를 `xfail`로 감추지 않았다. Flutter/Android는 코드·의존성
변경이 없어 실행하지 않았고 production 접근을 동반하는 deployment dry-run도 수행하지 않았다.

## AE. 확인된 finding

### D3C-A01 — MEDIUM — 실제 열린 DB inode에 결합되지 않은 GC admission

**상태: CONFIRMED FAILURE / TARGETED D3c CORRECTION REQUIRED.**

**위치:** `backend/isolated_sync/retention_schema.py:170`의 `assert_owned()`, `:176`의 `connect()`,
특히 마지막 검사 `:178`과 실제 open `:179`. 파괴적 경로는 `backend/isolated_sync/retention.py:327`,
`:331`, object DELETE `:350`, COMMIT `:367`, 사후 ownership 재검사에 이르는 `:373`이다.

**위반 invariant:** §16-S의 actual GC는 자가 소유 폐기용 synthetic profile에만 허용돼야 한다.
Owner-bound mark와 pre-open path 검사가 실제 삭제 connection의 file identity를 증명하지 못한다.
오류 반환 전에 승인되지 않은 inode의 DB에 이미 COMMIT할 수 있다.

**최소 전제:** 같은 process 또는 owned temporary directory의 파일을 교체할 권한이 있는 local
실행 주체가 마지막 stat와 SQLite open 사이에 개입한다. 대상 사본은 정확한 experimental
version/schema/WAL profile, mark와 같은 fence 및 객체 집합을 가진다. 원격 HTTP만으로 가능한
공격이나 production version 4 DB 삭제 경로를 입증하지 않았다. 이 제한 때문에 MEDIUM으로
분류하며 Critical/High unsafe retained-object 삭제라고 주장하지 않는다.

**최소 독립 재현:**

1. 새 synthetic DB A를 seed/install/bootstrap하고 세 번 label mutation 후 `Collector.mark()`를 얻는다.
2. 새 synthetic DB B에 A의 SQLite backup을 복사한다. B는 별도 inode이며 A collector가 소유하지 않는다.
3. 정상 `assert_owned()`가 A를 확인한 뒤, `sqlite3.connect(A.path)` 직전에 A 파일을 rename하고
   그 경로를 B에 대한 symlink로 바꾼다. SQLite open 호출에만 결정적 interleaving을 삽입한다.
4. `collector.sweep(mark, batch=1)`를 실행한다. 최종 ownership 오류를 받은 뒤 fresh SQLite
   connection으로 B의 객체 집합을 다시 읽는다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py -k D3C_A01
```

**기대:** 실제로 열린 파일이 소유 DB가 아니면 destructive transaction/COMMIT 전에 거부하고 B는
byte/row 상태가 유지돼야 한다.

**관측:** B에서 index-root 객체 한 개가 실제로 삭제됐다. 마지막 full suite의 삭제 hash는
`3e337ab20a6ed16190024197ca46393beee357162a19109e15c078d3a5f4a2d4`다. 그 뒤 `self.mark()`가
symlink를 발견해 `REJECT_SYNTHETIC_OWNERSHIP`을 반환했다. SQLite COMMIT은 이미 완료되어
안전 거부처럼 보이는 예외로 삭제를 되돌릴 수 없었다. 두 synthetic DB의 원 금융 행과 production
데이터를 손상시켰다는 증거는 없다.

**독립 증거:** 안전 기대값 `assert after == before`가 실제로 실패하며 missing object가 하나다.
`results.json`의 `D3C-A01`은 `deletion_committed_before_ownership_error=true`와 실제 삭제 hash를
기록한다. 기존 implementation helper로 삭제 집합의 기대값을 계산하지 않고 direct SQLite
pre/post SELECT를 비교했다. Source의 `assert_owned→sqlite3.connect→COMMIT→mark` 순서와 일치한다.

**최소 권고 수정:** 모든 파괴적 connection에서 실제 열린 SQLite 파일 identity를 자가 소유
identity와 안전하게 결합해 검증한 뒤 transaction을 허용해야 한다. Path 교체·symlink race에
저항하는 open/ownership 경계를 마련하고, commit 뒤 재검사에 의존하지 않아야 한다.
Pre-open stat 한 번 추가나 오류 메시지 변경만으로 해결됐다고 판단해서는 안 된다. 동일한 직접
open을 사용하는 설치 경계도 함께 검토한다. 이번 감사는 구현을 수정하지 않았다.

**필수 회귀:** 마지막 pre-open 검사 뒤 path replacement를 barrier로 삽입하고 다른 synthetic
inode의 DB는 object/cache/metadata 모두 변경 0이어야 한다. 사후 예외가 아니라 COMMIT 전
거부를 확인한다. 정상 owned DB actual GC와 기존 graph/worker/crash 회귀도 유지해야 한다.

**다음 단계 영향:** D3c의 destructive admission 보장이 닫히지 않았다. 수정 범위는 파일 소유권과
open/transaction 결합으로 한정할 수 있다. T6.6E 구현으로 우회하거나 rollout 격리만으로 감사
통과를 선언하지 않는다.

## AF. 잔여 위험과 검증 한계

새 Critical 0, High 0, Medium 1, Low finding 0이다. 독립적으로 재현하지 못한 의심을 별도
finding으로 만들지 않았다. Batch별 full graph 검증 반복 비용, WAL checkpoint 지연, decoded
memory와 encoded cap 차이, 기본 quota 전체 최대 부하, cold-cache/GC contention latency는
앞 절에서 한계를 밝혔다. 이는 확인된 admission 결함과 구분한다.

Historical certificate/fence/capture 증거는 계속 늘 수 있다. 이번 GC는 전체 DB의 무한 사용에 대한
고정 용량 보증이 아니며 arbitrary historical rollback을 제공하지 않는다. 향후 R1 실제 restore
의무는 trusted explicit pin adapter가 필요하지만 현재 없는 의무를 D3c 결함으로 분류하지 않았다.

## AG. Production 안전

Production DB/API/service/credentials/`.env`에 접근하지 않았다. Production 파일을 개발 환경에
복사하지 않았다. 모든 실제 삭제·fault·SIGKILL은 이번 감사가 만든 synthetic SQLite에 한정했다.
Deployment, service restart, production migration, APK 설치, 정상 runtime segmented endpoint/GC
활성화는 수행하지 않았다. `backend/app`·frontend/mobile에서 isolated GC로 연결되는 새 참조도 없다.

감사자가 추가한 파일은 이 보고서와 `docs/benchmarks/t66d3c-audit/`뿐이다. 감사 대상 구현,
기존 tests/docs는 변경하지 않았다. Audit commit/push는 deployment 허가가 아니다.

## AH. 최종 판정

**FAIL — TARGETED D3c CORRECTION REQUIRED**

현재 세대·유효 observation의 graph 보존과 historical-only 객체 회수는 독립 검증을 통과했다.
그러나 destructive file admission의 확정 MEDIUM 결함 한 건이 남아 있어 감사 acceptance를
충족하지 못한다. Full regression PASS를 근거로 이 결함을 무시하지 않는다.

## AI. 다음 조치

실제 열린 SQLite 파일의 소유권을 COMMIT 전에 보장하도록 D3C-A01만 수정한 뒤, 보존된 재현과
관련 GC·worker·crash 회귀로 targeted 독립 재감사를 받는다.

```text
T6.6D3c INDEPENDENT AUDIT:
FAIL

AUDITED COMMIT:
bcb0c47d42c5fb770ce40b70b0c14ad30d0c15f5

AUDIT COMMIT:
이 보고서를 포함하는 감사 commit; 최종 응답에 hash 명시

REPOSITORY STATE:
VERIFIED

RETENTION POLICY:
VIOLATION — synthetic 소유권 admission 한정

AUTHORITATIVE FINANCIAL RECORDS:
PRESERVED

CURRENT COMPLETE GENERATION:
PROTECTED

HISTORICAL CERTIFICATE EVIDENCE:
PRESERVED

HISTORICAL CERTIFICATE OBJECT REFERENCES:
SAFELY SEPARATED

RETENTION ROOT INVENTORY:
COMPLETE

ACTIVE OBSERVATION PROTECTION:
PASS

IN-FLIGHT TRANSFER PROTECTION:
PASS

D3B-M01:
PRESERVED

ATOMIC PIN RELEASE:
PASS

IDEMPOTENT PIN RELEASE:
PASS

INDEPENDENT REACHABILITY ORACLE:
PASS

SHARED OBJECT PROTECTION:
PASS

MARK/SWEEP SAFETY:
PASS — 정상 소유 DB의 retained graph; admission은 FAIL

WRITER/GC CONCURRENCY:
PASS

OBSERVATION/GC CONCURRENCY:
PASS

TRANSFER/GC CONCURRENCY:
PASS

CRASH/RESTART:
PASS

CLOCK ROLLBACK:
PASS

EPOCH TRANSITION:
PASS

METADATA RECLAMATION:
PASS

QUOTA/BUDGET RECOVERY:
PASS

CORRUPTION FAIL-CLOSED:
PASS

GC ADMISSION SAFETY:
FAIL

SYNTHETIC ACTUAL GC:
PASS — 정상 소유 DB; 파일 교체 반례 별도 FAIL

POST-GC CURRENT RECONSTRUCTION:
PASS

POST-GC OBSERVATION RECONSTRUCTION:
PASS

ELEVEN TABLES:
11 / 11

GLOBAL PATRICIA:
PASS

HISTORICAL OBJECT RECLAMATION:
PASS

LOGICAL BYTES RECLAIMED:
54,274 bytes — 독립 성능 DB 2개 합계

PHYSICAL FILE SIZE CHANGE:
0 bytes — 두 main file 각각

10K GC DURATION:
119.624 seconds — 독립 fixture

MAXIMUM DELETION WRITE-LOCK:
52.497 ms — 명시 성능 DB 2개; 10k는 50.244 ms

NORMAL REQUEST O(N) REGRESSION:
NONE FOUND

INDEPENDENT AUDIT TESTS:
73 PASSED
1 FAILED

BACKEND FULL REGRESSION:
1,284 TESTS
1,540 SUBTESTS
PASS

D1/D2a/D2b:
PRESERVED

D3a:
PRESERVED

D3b:
PRESERVED

SNAPSHOT V7:
UNCHANGED

FINANCIAL FORMULAS:
UNCHANGED

NORMAL BACKEND RUNTIME:
UNCHANGED

SEGMENTED ENDPOINTS:
NOT ACTIVATED

PRODUCTION ACCESS:
NONE

DEPLOYMENT:
NOT PERFORMED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
1 — D3C-A01

NEW LOW:
0

UNCONFIRMED RISKS:
0 — 별도 finding 없음; 검증 한계는 AF 참조

D3c BLOCKERS:
1 — D3C-A01

SAFE TO START T6.6E:
NO

SAFE TO DEPLOY:
NO

FINAL VERDICT:
FAIL — TARGETED D3c CORRECTION REQUIRED

NEXT ACTION:
실제 열린 DB의 소유권 admission을 수정한 뒤 targeted 독립 재감사를 수행한다.
```
