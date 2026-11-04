# T6.6F-B07 — 제한된 connect/schema 비용 귀속

**PASS — MATERIAL COST ATTRIBUTED. 엔지니어링 결정은 A — CONFIRMED MATERIAL TARGET이다.** 원 B03 소스의 실제 D3 handler에서 연결·스키마 검사가 요청마다 반복됨을 확인했다. 상세 계측한 객체 요청 14개의 handler 3.458826초 중 connect는 1.193978초(34.52%), 연결 내부 schema 검증은 1.163873초(33.65%)였다. 그 안에서 불변 schema로부터 기대 revision trigger 계약을 다시 파싱한 시간은 0.278446초(전체 handler의 8.05%)다.

A 판정은 **불변 기대 계약의 반복 컴파일을 다음 최소 후보로 검증할 근거**에 한정한다. 실제 DB 검증을 생략하거나 연결을 재사용하는 구현은 하지 않았다. 안전한 순절감량과 실제 Flutter end-to-end 개선은 미검증이다. B05 `_lookup` 후보는 실험용으로 유지하며 그 최적화 캠페인을 반복하지 않았다.

실제 실행은 manifest 1 + 객체 packet 28 + release 1 = **30/32 요청**, 외부 watchdog 기준 **9.233623/120초**였다. 재시도·만료·오류·미완료 scope는 0이다. [실행 manifest](../../benchmarks/t66f-b07/run-manifest.json), [원 packet 기록](../../benchmarks/t66f-b07/packets.jsonl), [구조화된 timing](../../benchmarks/t66f-b07/packet-timings.json), [외부 예산 기록](../../benchmarks/t66f-b07/execution-budget.json)에 모두 보존했다.

## 소스·fixture·환경

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. live dirty 소스를 baseline으로 쓰지 않았다. 현재 live engine `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`를 별도로 재계산했고 변경하지 않았다. [live와 측정 source 층](../../benchmarks/t66f-b07/live-engine-identity.json)을 분리했다. 원 동결 archive `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5`를 한 개의 격리 tree로 복원하고 899파일의 bytes/mode 및 canonical manifest digest를 확인했다.

|신원 층|검증값|
|---|---|
|원 B03 payload|`8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`|
|실제 backend engine|`7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c`|
|보존 N1k 압축 fixture|`e9d805a03399bd4f940e7af2416dc13f7e7dd962525e986db1810980c897550d`|
|복원 SQLite template|`aba6a044985f9f148e770fcd484e554373b12cc20f1d48ee441814ed8b7318d2`|

fixture는 B05-A의 `fixture-template-n1000.sqlite.gz`와 `fixture-n1000.json` 원본이다. 교체 fixture를 생성하지 않았다. 원 template은 8,859,648B이며 독립 SQLite backup으로 실제 소유 sandbox에 복원했다. 공통 template 안에 다른 engine의 사전 준비 view도 있지만, 실제 실행 소스·manifest·다운로드 대상은 모두 원 engine A였다. 새 manifest Target은 보존 A Target과 정확히 같았다. payload SHA와 engine SHA는 별개로 검증했다. [preflight](../../benchmarks/t66f-b07/preflight.json), [전체 source manifest](../../benchmarks/t66f-b07/baseline-source-manifest.json), [복원 도구](../../benchmarks/t66f-b07/prepare.py).

N은 ledger 1,000행이다. current ledger 105행·기타 authority 35행, hot 87,364B/control 3,178B를 고정했다. 전체 reachable graph는 4,132개·2,749,721B다. cold 초기화 준비를 쓰므로 D는 해당 없음(null)이며 0으로 대체하지 않았다. §35는 다섯 N=1k/5k/10k/50k/100k와 H/D 고정을 규정하지만 숫자 성능 합격선은 정하지 않는다.

지원 runtime은 CPython 3.12.3/backend SQLite 3.45.1이다. 주소공간 제한은 기존 8GiB를 유지했다. 실제 UTC로 새 900초 observation을 만들었고 기존 최대 3 attempts를 변경하지 않았다. 이 실행은 Starlette TestClient의 **실제 ASGI D3 route와 실제 WorkerBudget/SQLite 경로**를 사용했다. socket/TLS를 거치지 않아 네트워크 지연을 측정하지 않았다. B05-A/B05-B의 실제 Flutter 전체 시간과 새 matched pair로 취급하지 않는다. Android/Flutter 실행, emulator, production API·DB 접근은 0이다.

원 B03 제품/B03 계측 파일은 전후 bytes가 같다. runtime에 붙인 함수 wrapper는 **B07 실험 계측**이며 IR07이 감사한 타이머라고 주장하지 않는다. B03 `instrument`, `instrument_connections`, `instrument_workers`와 기존 안전 preflight를 그대로 사용했고 B03 ON은 모든 요청에서 유지했다. 기존 monitoring/SQL 계측 구현이나 source lock을 수정하지 않았다.

## 실제 호출 경로와 연결 수명

[호출 경로와 source SHA](../../benchmarks/t66f-b07/source-call-graph.json)에 원본 파일을 연결했다.

1. `Adapter.dispatch`가 실제 body/contract를 검사하고 `WorkerLease.run(Adapter.prepare)`를 호출한다.
2. `Adapter.credential`은 `RetentionSandbox.connect`로 새 연결을 열어 원 token/principal을 검증하고 finally에서 닫는다.
3. 객체 요청의 `TransferRepository.acquire`는 `ObservationRepository._connection`에서 별도 새 연결을 연다. `BEGIN IMMEDIATE`/savepoint 안에서 `_lookup`, `PathResolver.resolve`, 내부 terminal 검사와 응답 bytes 준비를 수행한다. 네트워크 await 동안 transaction을 유지하지 않는다.
4. prepare 뒤 `Adapter.terminal`이 `repo.lookup`→`_connection`으로 세 번째 새 연결을 열어 권한·lease·Target을 재검증한다. 마지막 guard 뒤 응답을 반환한다.
5. `_connection`의 context exit와 finally는 close를 호출한다. 원 구현의 중복 close 호출을 바꾸지 않았다.

30요청에서 `connect=90`, `_open=90`, `close 호출=150`이었다. 모든 요청에서 fresh connect/open은 3회이고 close 호출은 5회다. 150은 고유 연결 수가 아니다. credential은 한 번, 두 repository 연결은 각각 context와 finally에서 닫는다. pooling/reuse는 없었다. native FD peak나 별도 누수 추세는 측정하지 않았으나 collector의 pending/error는 모두 0이고 자식 프로세스가 정상 종료했다.

`RetentionSandbox._open`은 소유 inode/fd 확인, `sqlite3.connect(factory=RetentionConnection, timeout=0.1, cached_statements=0)`와 연결 소유 검사를 포함한다. 이후 `connect`는 FK·recursive trigger·user_version PRAGMA, 버전별 validator, WAL journal 확인과 authorizer 설치를 수행한다. 보존 DB의 retention version `1_000_005`에서는 `retention_schema.validate_schema`→`finalization.validate_schema`가 매번 실행된다. 다른 지원 버전의 분기는 source상 조건부이며 이번 현재 버전 경로에서는 모든 연결이 검증됐다.

`finalization.validate_schema`는 `app.db_migrations._validate_current_schema`의 가져온 alias를 호출한다. 실제 table/column/index/FK/revision trigger·sync metadata/profile/accounting 검사는 계속 수행된다. `_validate_revision_triggers`는 매 연결에 기대 계약 33개를 schema에서 파싱하고, 실제 DB trigger 82개를 파싱·대조한다. 기대값은 schema 문자열에 의존하고 실제값은 해당 연결의 DB에서 읽는다.

첫 manifest의 `ObservationRepository.create`는 writer lock 이후 `conn._validate_capture_schema()`를 추가로 호출한다. 따라서 첫 요청은 connect 3회에 retention/finalization validation 4회다. 추가 한 번은 connect 밖이다. 객체 요청에서는 connect 내부 3회 외의 validation이 없었다. 이 구분 없이 schema 합을 connect 내부 시간이라고 보고하지 않았다.

`retention_schema.metadata_contract`, `capture_schema/_columns`, 기대 table map에는 원래 bounded cache가 있다. cache를 비우지 않았다. 이번 process의 retention metadata는 **miss 1/hit 90**이었다. 첫 요청의 metadata reference 생성 약 0.404813초는 이미 한 번만 수행되는 비용이다. 이를 모든 packet의 반복 비용으로 외삽하지 않는다.

## 실행 예산과 타이머 경계

외부 parent는 새 session/process group을 소유하고 119초에 SIGKILL하도록 했다. 자식은 110초 뒤 새 요청을 시작하지 않는다. watchdog 자체를 별도 잠든 task-owned child로 검증했고 약 0.104초에 강제 종료됐다. 이 infrastructure 검사에는 D3 요청이 없었다. 실제 packet campaign은 단 한 번이었고 watchdog은 발동하지 않았다. [watchdog 코드](../../benchmarks/t66f-b07/run.py), [자체 검증](../../benchmarks/t66f-b07/watchdog-selftest.json), [사전 계획](../../benchmarks/t66f-b07/plan.json).

순서는 `manifest(probe)`→`control1 7개`→`probe1 7개`→`probe2 7개`→`control2 7개`→`release(probe)`다. 즉 14개 control 객체 요청과 14개 probe 객체 요청에 setup/release 2개를 더했다. 실제 경로를 호출하는 별도 smoke 요청은 없었다. 모든 attempt를 dispatch 전에 `requests.jsonl`에 기록했다. 자식 startup/import/fixture 복원/요청/사후 backup/종료를 포함한 parent 벽시계가 9.233623초였으므로 120초 범위 안이다. 요청 handler 합 7.778015초를 실행 벽시계로 대체하지 않는다.

같은 7개 packet은 hot/control/raw/index root 각 1개, 큰 snapshot leaf 1개, index leaf 64개, index node 64개다. 묶음당 133개 고유 객체·307,454B이며 네 묶음은 532개 전달 event다. 전체 4,132객체 cold를 취득하지 않았다. 한 packet은 한 객체와 같지 않다. 각 응답의 ref/offset/length/base64 bytes를 보존 fixture의 독립 hash 확인된 bytes와 대조했다. [요청 경로 계획](../../benchmarks/t66f-b07/packet-plan.json).

|측정 경계|범위와 한계|
|---|---|
|handler wall/process CPU|실제 ASGI app 호출부터 buffered response 준비 완료까지; serialize한 raw 로그·body 전달은 뒤다|
|connect inclusive|원 함수의 전체 동기 구간; open/schema와 중첩|
|open inclusive|소유권 확인과 native connection 생성 포함; 순수 sqlite3.connect 전용 timer는 아님|
|schema/validation|동기 함수별 perf_counter_ns와 thread_time_ns; 중첩 tree의 직접 자식을 빼 self 계산|
|SQL execute|RetentionConnection.execute의 일부 API 시간; cursor fetch·in-memory SQL·전체 physical I/O는 미포함|
|control|같은 wrapper 분기와 B03 ON, 상세 함수 clock 수집만 끔; 완전히 unwrapped 기준은 아님|

thread별 stack으로 중첩을 관리했고 한 요청씩 실행했다. connect interval끼리 중첩되지 않았고 self wall/CPU는 모두 음수가 아니었다. 함수 내부 SQL/검증 inclusive 시간을 상위 시간에 또 더하지 않았다. handler는 async envelope이므로 worker thread CPU를 handler 전용 CPU라고 부르지 않는다.

## 분포와 비중복 귀속

아래 첫 표의 모집단은 **객체 probe 14요청의 42개 연결**이다. process 최초 연결은 sandbox 준비 때 이미 사용됐으므로 이 표를 process/OS cache cold로 부르지 않는다. 기존 process cache가 warm한 이후에도 연결은 매번 fresh다. p90은 nearest rank이며 작은 표본에 통계적 유의성을 주장하지 않는다.

|포함 경계|호출|합계 초|중앙값 ms/호출|최소–최대 ms|p90 ms|thread CPU 초|
|---|---|---|---|---|---|---|
|connect|42|1.193978|28.326|27.676–31.133|28.814|1.193761|
|_open|42|0.016854|0.347|0.313–0.699|0.583|0.016700|
|retention schema 전체|42|1.163873|27.620|26.949–30.234|28.112|1.163783|
|finalization.validate_schema|42|1.154971|27.408|26.735–30.031|27.912|1.154882|
|current schema validator|42|1.068287|25.367|24.663–28.007|25.831|1.068201|
|revision trigger 검사 전체|42|0.719058|16.969|16.648–19.787|17.687|0.718975|
|critical structure 검사|42|0.169025|4.039|3.802–4.218|4.129|0.168967|
|기존 metadata cache 호출|42|0.000100|0.002|0.002–0.006|0.002|0.000064|

manifest/release까지 상세 계측한 전체 16요청에서는 connect 48회·1.771249초, 중앙값 28.297ms/호출이었다. 첫 요청의 connect 3회 합은 0.493421초, handler는 0.796500초였다. 전체 connect의 최대 438.621ms는 첫 metadata cache miss 구간이다. 전체 retention validation은 49회·1.761338초이며 그 중 connect 내부는 48회·1.737122초다. 전체 finalization은 49회·1.346129초, connect 내부 48회·1.322118초다. 이 전체값과 객체-only 표를 혼합하지 않았다. raw의 connection_state 문구는 준비된 process/OS cache를 가리키며 모든 metadata cache가 첫 요청부터 warm했다는 뜻은 아니다. process_first_request와 위 cache miss를 함께 해석한다. 원자료의 함수별 interval과 [전체/객체 분포](../../benchmarks/t66f-b07/call-path-attribution.json)에 두 모집단을 모두 남겼다. control 함수 시간은 미측정이며 0으로 채우지 않았다.

객체 probe 14요청의 비중복 배분은 다음과 같다. 기존 제품 D3 resolution timer는 해당 요청 순서와 대응시켰다. connect와 lookup/resolution은 source에서 분리된다. 다른 1k/5k 실험을 섞은 합계가 아니다.

|handler 내부 배분|초|handler 비중|
|---|---|---|
|connect|1.193978|34.52%|
|lookup|1.647398|47.63%|
|resolution|0.525690|15.20%|
|그 밖 handler 잔여|0.091760|2.65%|

connect 1.193978초 안에서는 `_open` 0.016854초 + schema 1.163873초 + 나머지 PRAGMA/authorizer·wrapper 등 0.013251초로 나뉜다. 이는 connect의 직접 자식에 따른 배분이며 schema는 lookup/resolution에 포함되지 않는다. schema가 handler의 33.65%를 차지한다. opening 자체보다 검증이 큰 관측이다.

finalization은 schema 안이고, current schema 및 revision trigger 검사는 finalization 안이다. 이 포함 표들을 더해 총합으로 만들 수 없다. SQL execute 부분은 5,460호출·0.213083초/thread CPU 0.206805초였으며 schema 안에 포함된다. fetch/메타데이터 메모리 DB/진단자 exclusive CPU·fsync를 분리하지 못했으므로 이것을 전체 SQLite 비용으로 취급하지 않는다. 객체 probe handler의 process CPU 합은 약 3.457354초로 wall 3.458826초와 가깝고, connect의 thread CPU도 1.193761초로 wall과 가깝다. 이 실행에서는 CPU가 큰 것으로 볼 수 있으나 제품 Python/SQLite CPU/B03 관측자 CPU의 완전한 분리는 아니다.

### 타이머 교란과 의미 보존

control 객체 handler 합 3.367159초, probe 합 3.458826초로 차이는 +0.091667초, 비율 1.027224배다. 각 slot마다 control 2개/probe 2개이며 두 block 순서·CPU 주파수·cache 변동은 완전히 통제되지 않았다. 이 차이는 순수 timer CPU의 확정값이나 신뢰구간이 아니다. 공유 wrapper 분기 비용도 별도 분리하지 않았다. 상세 helper timer를 포함한 현 측정의 한계로 보존했다.

모든 slot의 네 block 사이에서 B03 counter map 전체가 같았고 응답의 실제 객체 bytes도 같았다. 30 scope 모두 정상 close, pending/error 0이었다. 사후 read-only 대조는 원 template과 post-run backup의 authoritative 11개 테이블 및 users/auth_sessions 2개 테이블의 **SQL 저장 타입과 실제 값**을 그대로 비교해 통과했다. 금융 원문을 normalize하거나 모바일 금융 계산을 복제하지 않았다. reachable graph의 모든 원 canonical bytes도 그대로다. 이 검증은 B03 재감사나 전체 backend/Flutter 회귀 suite 재실행이 아니다. [사후 검증](../../benchmarks/t66f-b07/verification.json).

## 제거 후보와 5k 관련성

현재 버전의 각 연결은 schema 문자열에서 기대 revision 계약 33개를 `_revision_trigger_contract`로 다시 파싱한다. 객체 probe에서는 42×33=**1,386회·0.278446초**, 즉 handler 8.05%/connect 23.32%였다. actual DB 계약 파싱은 42×82=3,444회·0.314307초로 별도 측정했다. source 기대문은 `CREATE TRIGGER IF NOT EXISTS revision_`로 시작하고 보존 DB 실제 trigger SQL에는 그 prefix가 없음을 확인해 두 분류를 구분했다. 반환된 기대 계약은 문자열·tuple로 이루어진 순수 schema 파생값이며 actual DB 상태가 아니다.

schema의 반복은 확인됐지만 `validate_schema` 전체가 불필요한 것은 아니다. 현재 DB 구조/DDL/profile/revision/소유권/auth/lease의 검사는 신뢰 경계다. 동일한 기대문 파싱을 최대 1항목의 정확한 schema 키 아래 불변 tuple/frozenset으로 컴파일해 재사용하는 것은 **검증할 가치가 있는 최소 방향**이다. actual DB trigger 파싱/대조와 revision 상태 검사, fresh 연결·권한·lease 검사는 매번 유지해야 한다. 연결 pooling, PASS cache, schema 체크 생략은 제안 범위에 없다.

이미 한 번만 생성하는 metadata reference에 새 cache를 덧붙이는 방향도 아니다. B07에서는 어떤 cache나 최적화도 구현하지 않았다. 후보 작업 부분의 시간은 측정됐지만 replacement 비용, invalidation·동시성·예외 동등성과 실제 순절감은 아직 **NOT ESTABLISHED**다.

N5k baseline ON의 기존 두 raw에서 객체 요청은 각각 332회, 전체 HTTP는 335회다. 5,000행 또는 20,148객체를 곱하지 않는다. 원 source의 객체당 3 connect 경로에 따른 해당 객체 요청 연결은 996회다. 아래는 B07 객체 probe의 packet별 중앙값을 **같은 반복 경로/CPU 조건**이라는 가정 아래 곱한 진단 모델이다. manifest/recheck/release는 제외했다.

|역사 기준|기존 전체 cold 초|객체 요청 수|connect 조건부 예산 초|기대 파싱 전부 제거 모델 초|기존 cold 대비|
|---|---|---|---|---|---|
|B05A|152.688187|332|28.228623|6.571737|4.30%|
|B05B|149.743978|332|28.228623|6.571737|4.39%|

기대 파싱의 관측 packet 최소–최대 값을 사용하면 같은 계산 범위는 6.479–7.092초다. 이는 오차 구간이나 실제 5k 성능이 아니다. host 속도·page cache·DB 크기·packet mix·B03/B07 계측 차이와 새 cache 비용을 검증하지 않았다. actual 검사의 비용은 남고 기대 컴파일 최초 비용도 남는다. 6.572초는 전체 반복 파싱을 없앴다고 가정한 비용 예산이며 실제 speedup이라고 주장하지 않는다.

B06의 29.558–31.923초 residual은 역사 `handler−lookup−resolution`이며 schema 비용이라고 전제하지 않았다. 새 직접 측정의 connect 모델 28.229초가 그 근처라는 점은 가설과 일관되지만, 다른 요청 집합/transport/host 시각으로 얻은 값이므로 역사 residual을 완전히 설명한 matched 분해라고 할 수 없다. 순수 expected 부분만으로 그 전체를 없앨 수도 없다.

## 결정·보존·정리

**결정: A — CONFIRMED MATERIAL TARGET.** 반복 connect/schema의 유의미한 실제 비용과 순수 기대 계약 컴파일이라는 작은 후보 부분을 식별했다. numeric binding 합격선을 새로 만들지 않았다. 다음 후보는 `backend/app/db_migrations.py:_validate_revision_triggers`의 schema 전용 기대 계약 컴파일에만 한정한다. shared backend 파일이므로 별도 구현 과제는 권한 범위, 새 engine SHA와 직접 연동 artifact/admission/source guard의 정합 전이, 영향 correctness 회귀를 함께 다뤄야 한다. B07은 해당 파일이나 admission을 수정하지 않았다. [단일 다음 결정](../../benchmarks/t66f-b07/next-action-decision.json).

B01/B02는 CLOSED, B03는 원 IR07 source에 대해 CLOSED다. B04 bounded PASS, B05-A/B05-B PASS, B05 experimental only, B06 next experiment PASS를 유지한다. 다섯 지점 cost grid와 large-N I25는 미완료이며 Phase B는 INCONCLUSIVE다. 100k instrumented full cold는 NO-GO, Real-Device Gate는 DEFERRED, Android memory/VFS/power는 NOT VERIFIED다. R1 activation은 CLOSED, production deployment는 NOT AUTHORIZED다. 이번 partial packet profiler로 Flutter 전체 cold·Android 안전성·100k 완료를 인증하지 않는다.

시작과 종료의 기존 visible tracked/untracked 6,160파일 bytes/mode/크기, staged path/mode/blob/stage 및 원 index를 대조했다. index SHA `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`를 보존했다. 원 B03 동결 archive와 B05/B05-A 후보, B04–B06 역사 증거를 수정하지 않았다. 제품·B03 계측·binding protocol·allowlist·release·source lock 변경, reset/stash/checkout/restage/commit/push는 모두 없다. 기존 live의 실험 최적화는 그대로 보존했다. [시작 보존](../../benchmarks/t66f-b07/preservation-before.json), [종료 보존](../../benchmarks/t66f-b07/preservation-after.json).

유일 scratch `/tmp/money-note-t66f-b07-20261026`에는 source tree 1개, 보존 template 복원 및 task-owned sandbox/backup만 만들었다. 정상 종료·899 source 파일 검증·금융 SQL 대조 뒤 고유 post-run SQLite backup을 압축하고 SHA를 검증해 보존했다. disposable source/DB는 소유·비활성을 확인한 뒤 정리했다. 기존 cache/DB/WAL은 삭제하지 않았다. task-owned 905파일·27,590,834B(관찰 할당량 29,585,408B)를 제거했다. 최초 정리 검사에서 발견한 빈 WAL/SHM 4개는 소유·빈 WAL·원 DB 해시·task 종료와 보이는 열린 fd를 확인한 뒤 정리했다. 다른 권한 process fd의 관측 한계도 cleanup-precheck에 남겼다. 실제 생성·삭제 파일 수와 회수량은 [정리 기록](../../benchmarks/t66f-b07/cleanup.json), 고유 DB와 입력/산출물 SHA는 [증거 manifest](../../benchmarks/t66f-b07/evidence-manifest.json)에 있다. `prepare.py`→`run.py selftest`→`run.py`가 실행 절차이고, 원 raw를 덮어쓰지 않는 새로운 task 경로에서만 재현해야 한다. `analyze.py`/`verify.py`는 사후 분석이며 새 packet을 보내지 않는다.

다음 행동: **별도 승인된 과제에서 원 B03의 `_validate_revision_triggers`에 정확한 schema 키·최대 1항목의 불변 기대 계약 컴파일 재사용 후보를 구현하고 실제 DB 검사 보존과 N=1k·32 packet/120초 성능을 검증한다.**

## 최종 상태

```text
T6.6F-B07 BOUNDED CONNECT/SCHEMA ATTRIBUTION:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

BASELINE B03 SOURCE:
VERIFIED

BASELINE ENGINE SHA:
7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c

N=1K PRESERVED FIXTURE:
VERIFIED

BACKEND D3 ACTUAL REQUEST PATH:
VERIFIED

MEASURED PACKETS:
30 / 32 MAX — manifest 1, objects 28, release 1

MEASUREMENT WALL TIME:
9.233623 s / 120 s MAX

RETENTION SANDBOX CONNECT CALL FREQUENCY:
3회/요청, 전체 90회; 상세 timer 48회

FRESH CONNECTION PER REQUEST:
YES

SCHEMA VALIDATION PER REQUEST:
YES — 현재 버전에서 연결당 1회/요청당 3회; 최초 manifest 추가 1회

CONNECT TOTAL ELAPSED:
1.771249초/상세 48회; 객체 probe 42회는 1.193978초

CONNECT MEDIAN PER CALL:
28.297ms/상세 48회; 객체 probe 42회는 28.326ms

CONNECTION OPEN ELAPSED:
_open 포함 시간 0.019253초/48회; 순수 native open은 미분리

SCHEMA-RELATED ELAPSED:
connect 내부 1.737122초/48회; 객체 probe는 1.163873초/42회

FINALIZATION VALIDATE_SCHEMA ELAPSED:
connect 내부 1.322118초/48회; 객체 probe는 1.154971초/42회

NONOVERLAPPING ATTRIBUTION:
VALID — 동기 함수 tree와 직렬 handler 범위; SQL 전체 비용은 미분리

MEASURED HANDLER SHARE:
객체 probe 14개에서 connect 34.52%, schema 33.65%

AVOIDABLE CONNECT/SCHEMA FRACTION:
NOT ESTABLISHED — 기대 파싱 8.05% handler 측정, 안전한 순절감은 미검증

N=5K IMPACT ESTIMATE:
기존 332 object packets × 기대 파싱 중앙값 19.794ms = 6.572초 예산;
역사 cold의 4.30–4.39%, 실제 speedup 미검증

B06 UNASSIGNED BACKEND BUDGET:
29.558–31.923 s — HISTORICAL, NOT ASSUMED CONNECT COST

CONNECT/SCHEMA HYPOTHESIS:
CONFIRMED MATERIAL

NEXT ENGINEERING DECISION:
A — schema 전용 기대 revision 계약 컴파일의 제한적 재사용 후보 검증

ORIGINAL B03 INSTRUMENTATION:
UNCHANGED

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

ENGINE SHA ALLOWLIST MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B07:
NO

HISTORICAL EVIDENCE:
PRESERVED

NEW FULL N=5K COLD RUNS:
0

NEW FULL N=50K COLD RUNS:
0

NEW FULL N=100K COLD RUNS:
0

N=100K INSTRUMENTED FULL COLD:
NO-GO

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED FOR ORIGINAL IR07-AUDITED SOURCE

B04:
PASS — BOUNDED

B05:
EXPERIMENTAL ONLY

B05-A:
PASS

B05-B:
PASS

B06:
PASS — NEXT EXPERIMENT IDENTIFIED

T6.6F PHASE B:
INCONCLUSIVE

REAL-DEVICE GATE:
DEFERRED

ANDROID MEMORY/VFS/POWER:
NOT VERIFIED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

B07 REPORT:
docs/t66f-b07-bounded-connect-schema-attribution.md

B07 EVIDENCE:
docs/benchmarks/t66f-b07/

TEMPORARY ARTIFACT CLEANUP:
task-owned 905파일·약 28.21MiB 할당량 정리; 고유 backup·raw timing 보존

FINAL VERDICT:
PASS — MATERIAL COST ATTRIBUTED

NEXT ACTION:
별도 승인된 과제에서 원 B03의 _validate_revision_triggers에 정확한 schema 키·최대 1항목의 불변 기대 계약 컴파일 재사용 후보를 구현하고 실제 DB 검사 보존과 N=1k·32 packet/120초 성능을 검증한다.
```
