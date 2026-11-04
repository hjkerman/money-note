# T6.6F-B03-IC01 계측 한정 교정

**최종 판정: INCOMPLETE.** IA01–IA07의 구현 측 교정 회귀는 통과했지만,
활성 계측의 N=100k 관측 lease 적합성이 미확정이다. 이 문서는 독립 감사 PASS나 Phase B 완료를 선언하지 않는다.
원 감사의 **5 MEDIUM / 2 LOW**는 금융 제품 결함이 아닌 계측 결함이다.
원본 [독립 감사](../../t66f-b03-independent-instrumentation-audit.md), findings와 과거 수치는 보존한다.

## 1. 시작 상태와 범위

시작 HEAD/local main/origin/main/별도 remote main은 모두
`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이며 작업 트리와 index는 비어 있었다.
원 구현은 `a96e130682023522ec56ab6e2fc9f53ec8d77df6`다.
진단 wrapper 세 파일만 기존 source 변경 대상이다. backend/mobile 제품 소스,
binding protocol, DB schema, P0 함수 및 승인된 exact source-lock은 변경하지 않는다.
[보존 검사](../../benchmarks/t66f-b03-ic01/evidence/preservation.json)는 관련 377개 원 파일을 대조한다.

## 2. IA01–IA07 교정 행렬

|원 ID·등급|원 독립 재현·실제 원인|교정 경계·현재 검증|
|---|---|---|
|B03-IA01 MEDIUM|Python/Dart 동일 이름 savepoint가 첫 frame을 선택. native a=1B 보존, 계측 committed0/rollback3B|가장 최근 같은 이름 frame 선택. 별도 현재 oracle는 committed1/rollback2B. quoted/case/control-token도 보정|
|B03-IA02 MEDIUM|OR FAIL의 성공 prefix도 예외 발생 시 전체 statement rollback으로 분류. native3B/계측1B|명시 OR FAIL과 native extended constraint code의 보존 semantics 적용. FK/trigger ABORT는 제외. autocommit/transaction/후속 rollback 구분|
|B03-IA03 MEDIUM|첫 comment-DML의 첫 공백 token이 주석이라 TEMP observer 설치 누락|실행 SQL은 그대로 두고 제어 prefix에서 주석·quoted identifier만 읽음. 첫 DML에서 설치하며 read-only CTE에는 설치하지 않음|
|B03-IA04 LOW|nested instrument가 parser observer를 다시 감쌈. 실제3회6B→4회8B|세 종류 session 설치의 refcount와 마지막 teardown. 현재3회6B 및 부분 설치 실패 복원 보정|
|B03-IA05 MEDIUM|NativeJob 생성 hold 뒤 lease 등록 거부에는 기존 _finish 미호출|기존 run을 한 번 위임. 미등록 job의 진단 hold만 finally에서 회수. 등록된 취소/native tail은 원 _finish 소유|
|B03-IA06 LOW|한 transaction의 닫힌 collector를 pending map이 무제한 strong retain|transaction당 owner32개 명시 상한. 33번째는 실행 전 coverage 오류. 종료 후 owner/frame/pending 정리|
|B03-IA07 MEDIUM|mutate command 전체가 generation이라 before/after oracle SELECT도 포함|명시 sandbox capture/finalization 연결 구간만 generation. 독립 catalog SELECT는 setup에 남아 제품 합계에서 제외|

## 3. 수정 전 원 재현

`run.py baseline-backend`, `baseline-flutter`, `baseline-direct`의 exit는 모두0이다.
backend 원18개, Flutter 원14개 및 직접 실험3종을 실행했다. PASS는 결함 존재 assertion의
성공이지 계측 정확성 PASS가 아니다. 원 SQLite oracle와 counter의 차이도 그대로 확인했다.
직접 실험은 IA05 pending1/completion0, IA06 owner10/100/1000 보존,
IA07 generation에 두 catalog SELECT(176/185행)를 관찰했다.
원 명령·log·JUnit·실제 출력은 [IC01 evidence](../../benchmarks/t66f-b03-ic01/evidence)에 분리했다.
첫 현재 실행에서 역사 assertion 4개가 교정된 값 때문에 실패한 로그도 보존한다.

## 4. 역사 재현과 현재 정확성 분리

사용자가 명시 승인한 **역사 재현과 현재 검증 분리**를 적용한다.
원 backend/Dart 독립 테스트 파일, assertion, 원 경로와 역사 evidence는 수정하지 않는다.
backend 결함-existence 4개만 감사 commit에서 보존한 exact wrapper로 실행한다.
Flutter는 전체 일반 suite, 원 파일의 현재 oracle11개, 원 assertion 그대로인 역사3개를 순차 집계한다.
Dart 역사 실행용 사본은 import/출력 경로만 바꾸며 assertion은 원문과 같다.
새 현재 테스트는 고친 counter를 직접 native SQLite 상태와 엄격히 대조한다.
SKIP/XFAIL·오류 허용 확대·기대 counter 완화는 없다. 별도 runner가 필요하다는 점은 인계에 명시한다.
동결 source의 commit·SHA와 사본 변환은 `archive.py`/`historical/manifest.json`에 남긴다.
역사 사본은 원 mobile package의 Dart3.3 format을 사용한다. 길어진 golden 경로의 setup 식만
줄바꿈을 맞추고 원 assertion은 그대로 보존했다. 최신 기본 formatter와의 진단 차이도 로그에 남겼다.

## 5. SQL 시도·효과·commit 정의

기존 BEFORE row payload는 진입한 시도, AFTER는 실제 실행된 row event다.
TEXT는 실제 SQLite UTF8 길이, BLOB은 실제 길이이며 숫자에 가상 bytes를 부여하지 않는다.
AFTER event도 나중에 ABORT/ROLLBACK될 수 있으므로 effective를 durable이라고 하지 않는다.
committed는 지원된 논리 payload 작업 중 native commit에 살아남은 부분이며 최종 고유 row 집합이나
physical filesystem durability가 아니다. UPDATE는 NEW row 전체 payload, DELETE 신규 payload는0이다.
hash/validation/write는 겹치는 별개 연산 비용으로 unique data 총합으로 더하지 않는다.

## 6. Savepoint·부분 성공·실패

SQLite의 가장 가까운 동일 이름 resolution을 양쪽 wrapper에서 따른다.
ROLLBACK TO는 target frame을 남기고 더 안쪽 frame만 제거하며 RELEASE는 target도 제거한다.
32번째 frame은 허용, 33번째는 native 실행 전에 진단 오류다.
명시 OR FAIL의 CHECK/NOTNULL/PRIMARYKEY/UNIQUE native 오류는 성공 prefix를 보존한다.
FK 또는 trigger ABORT는 이 규칙을 덮어쓰므로 전체 실패 statement의 event를 되돌린다.
schema-defined ON CONFLICT FAIL/RAISE(FAIL)는 이 좁은 관측 계약에서 실행 전에 명시 거부한다.
지원하지 않는 복잡성을 완결 계수로 보고하지 않는다. 범용 SQL parser/journal/storage를 만들지 않았다.
TEMP observer가 rollback에 의해 사라질 수 있어 후속 DML에서 기존 IF NOT EXISTS observer를 재설치한다.
제품 SQL 재실행이나 원 transaction 순서 변경은 없다.

native executemany가 다음 입력을 요구한 것은 앞선 SQL 반복이 성공했다는 경계다.
입력 iterator가 그 뒤 실패해도 앞선 row를 statement rollback으로 만들지 않는다.
failed COMMIT은 열린 transaction의 pending을 그대로 보존하며 실제 후속 rollback에 정산한다.
Dart의 한 API call에 여러 DML을 넣는 형태는 실행 전에 coverage 오류로 거부한다.
SQL literal/주석 안의 semicolon과 단순 trailing semicolon은 이 거부와 구분한다.
이 검사는 SQL statement 구분용 좁은 진단 분류이며 C1/금융 payload를 재파싱하지 않는다.

## 7. 설치·native 수명·owner 경계

collector attribution은 기존 ContextVar/Zone이다. 설치 refcount는 고정 세 observer의 소유권일 뿐
새 current-run global이나 authority가 아니다. native dispatch의 원 예외와 실제 실행은 보존한다.
등록 전 거부만 진단 hold를 회수하고 native 시작/취소 후 tail은 원 완료 경계를 기다린다.
owner32개는 한 connection/transaction의 상한이며 통상 단일 run은1개다.
상한 초과는 active owner에게 coverage 오류를 남기고 해당 SQL을 실행하지 않는다.
pending data를 조용히 버리거나 owner를 합치지 않는다. rollback/commit/close에서 해제한다.

## 8. Generation/oracle 격리

역사 TLS harness 자체는 변경하지 않았다. B03 wrapper가 실제 sandbox 연결 구간에만 generation을
부여한다. oracle catalog 비교는 setup으로 분류하며 제품 generation 합계에는 포함하지 않는다.
감사자의 원 실제 cursor 위임 실험으로 다시176/185행을 보았고 두 stage는 모두 setup이다.
hash/write byte 오염까지 있었다는 주장은 하지 않는다. 실제 generation hash/persistence와 D3
요청의 ContextVar 범위는 보존하며 별도 실제 HTTP 회귀로 확인한다.

## 9. Hash·validation·전층·P0 보호

hash primitive, P0 lineage hook 및 제품 C1은 수정하지 않는다. validation 중복 계수는 IA04의
wrapper 설치만 교정한다. submitted/completed/failed span은 그대로 별개이며 실패 parser가
정확히 읽은 prefix라고 주장하지 않는다. structural visit에 객체 크기를 곱하지 않는다.
E1/E3 논리 SQL 정산을 고치되 E3 ticket·final guard·동기 guard→COMMIT은 변경하지 않는다.
E4 source/previous_source/Frozen/file 계측과 bytes도 변경하지 않는다.
기존 exact SHA·역사 SHA·P0 fingerprint 동등성 검사를 전체 suite에서 다시 실행한다.

## 10. 최종 소스 회귀와 실행 오류의 구분

확정 source 한정 실행은 backend68개(원 구현24/독립18/신규26), Flutter43개(원25/신규18)가 통과했다.
그중 backend 역사4개는 위 동결 구현에서만 실행했다.
최종 backend는 **1,436 tests / 1,540 subtests PASS**, exit0, failures/errors/skips0,
pytest1,824.30초였다. 최종 Flutter의 모든 기본 case 집계는 **1,680 PASS / 0 FAIL / 2 SKIP**다.
원 strict B01 quota assertion은 불변이다.
B02 objects/edges/metadata 및64-object/1MiB packet,900초 lease/관측3회 모두 불변이다.

두 중간 전체 실행은 추가 SQL 경계 보정 전에 PID/argv/process group을 확인하여 종료했다.
첫 실행은 약1092초 뒤 exit-15였으며 중간 PASS를 최종 수치로 사용하지 않는다.
개발 중 WITH read-only query에 TEMP observer를 설치하려던 확장은 실제 query_only 오류가
확인되어 제거했다. 원 동작 보존을 새 양쪽 regression으로 고정했고 반례는
`with-readonly-development.json`에 보존한다. 최종은 `backend-sealed`/`flutter-sealed`다.
원16개 Phase B calibration도 출력만 분리해16 PASS로 재실행했다. 이는 신규26/18에 합산하지 않는다.

Flutter는 실제 일반 suite1,666 PASS/2 SKIP 및 역사3개를 성공 실행한 뒤 현재11개를
실행할 명령에서 이 SDK가 지원하지 않는 `--exclude-name` 때문에 exit64였다.
`flutter-sealed.json`의 runner FAIL을 지우지 않았다. 같은 sealed source에 지원되는
negative-lookahead `--name`으로 원 현재11개를 다시 실행해 exit0/done.success=true를 확인했다.
최종 집계는 세 부분의 machine done/exit 및 `flutter-current-11.json`에 근거한다.
일반 tree 재실행을 하지 않은 것은 파일5개의 SHA가 전부 동일하기 때문이며, 빠진 case나
FAIL→SKIP 전환은 없다. 향후 `flutter_full.py --sealed`에는 교정된 SDK 필터를 사용한다.

high-N 표본의 첫 실행도 `PUBLICATION_PROFILE_REQUIRED`로 실패했다. acquisition-only E1에
E3 API를 호출한 검사 오류였으며 profile을 켜서 우회하지 않았다. 새 read-only connection으로
publication table 자체가 없음을 확인하도록 고쳤다. 기존 실패와 최종 성공 로그를 모두 보존한다.

## 11. 100k lease·오버헤드 — 필수 blocker

원 독립 100k cold terminal2463.561초와 세 번째 observation 마지막 object의236.81초 여유를
단순2700초 합산으로 바꾸지 않는다. 활성 계측의 동일 fixture HOST small/medium overhead와
보존된 합성 high-N 객체 표본을 먼저 보정한다. 표본 projection은 실제 instrumented100k 완료 증거가 아니다.
full100k cold를 자동 반복하거나 lease/관측 수를 늘리지 않았다. 이 gate는 **미완료**다.

동일 HOST·원 독립 probe의3 warmup/20 alternating pairs를 최종 source에서 실행했다.
다음은 **DIRECT OBSERVATION**이며 단위ms, 각 cell은 off/on median이다. 원 p95/CPU/RSS와
모든 표본은 `performance-summary.json` 및 원 raw JSON에 남긴다.

|runtime·표본|primitive wall median|SQL wall median|
|---|---:|---:|
|Python small,200 primitive/20 rows|3.181 / 5.056|0.070 / 1.448|
|Python medium,2000 primitive/200 rows|93.199 / 113.386|0.804 / 9.939|
|Flutter small,200 primitive/20 rows|2.016 / 2.751|0.431 / 3.404|
|Flutter medium,2000 primitive/200 rows|479.998 / 480.968|1.062 / 11.204|

small/medium wall과 CPU는 다른 runtime/shape 간 합산하지 않는다. p95는20개 표본의
nearest-rank19번째 값이다. Flutter CPU는 process100Hz clock tick이라 짧은 구간의0은
무비용 증명이 아니다. GC/공유 page를 포함한 RSS 차분은 heap allocation이 아니다.

보존된 합성100k DB의 실제 canonical 객체 **2,061개 / 2,344,126B**를 read-only로 뽑아
새 폐기용 large-profile E1에 원64-object/1MiB batch로 썼다. warmup1+교대5쌍에서
off/on median은 **1.474117 / 4.033528초**, max는 **1.729736 / 4.468412초**,
process max RSS는 **229,949,440B**, 활성 SQL aggregate key는179개였다.
객체별 log를 쌓지 않았고 native count/sum(body)와 committed BLOB 계수를 정확히 대조했다.
원 DB·accepted/pending은 변경하지 않았으며 sample graph를 게시하지 않았다.

**ANALYTICAL ESTIMATE**: 이2.559411초 차이를 모든400,532개에 동일 per-object 비용으로
기계적 환산하면 약497.393초다. 종류별 표본 분포가 원 전체와 다르고 backend/D3/E2/renewal이
빠졌으므로 이것은 실제100k 증가 시간도 실패 증거도 아니다. 그러나 원 관측3의236.81초 여유에
대해 투명한 측정이라고 낙관할 근거도 없다. 900초×3 합산으로 PASS 처리하지 않는다.

최소한 **활성 계측의 실제100k D3→E2→E1 경로에서 관측별 전송 진행·만료·재인가·잔여시간과
완결 snapshot을 확인하는 유한 실험**이 더 필요하다. 그 전에 이 표본의 SQL observer 비용을
감수할지, 허용된 진단 경계 안에서 비용을 더 줄일지 명시 계획을 세워야 한다.
이는 제품 B02 기능 결함이나 새 `OBSERVATION_EXPIRED` 재현으로 분류하지 않는다.

## 12. 남은 의무와 판정

전체 회귀·build/static 검사·작은 실제 HTTP 재대조는 통과했다. 오버헤드는 측정했지만
100k lease 적합성 gate가 남아 있어 완료 commit/push를 하지 않는다.
구현 측 IA 교정 결과와 독립 finding closure는 다르며 별도 독립 B03 재감사가 필요하다.
N=1k/5k/10k/50k/100k fixed H/D 비용 grid와 I25 proof는 다음 독립 Phase B 의무다.
Android memory/VFS/I/O·물리 전원 손실은 HOST 결과로 입증하지 않는다.
B01/B02/E4-A01/E4-RA01 CLOSED, Snapshotv7/OfflineBaselinev4/Frozen B/J·pending 계약은 보존한다.
R1 activation은 CLOSED이며 segmented 일반 사용자 활성화·배포·APK 설치는 하지 않는다.

## 13. 변경 source와 보호 경계 검토

기존 파일 변경은 `docs/benchmarks/t66f-b03/counters.py`, `server.py`,
`mobile/test/support/logical_cost_sqlite.dart`뿐이다. 원문 SHA와 현재 SHA는 preservation.json,
최종 회귀의 wrapper·새 단위 테스트5개 exact revision은 sealed-source.json에 기록한다.
counter wrapper만으로 관측/정산할 수 있어 새 제품 hook을 추가할 이유가 없다.
`mobile/lib/src/offline/offline_store.dart`와 제품6파일은 이전 감사 revision 그대로다.
역사 P0 SHA `a8d767e5…`와 현재 `907aa044…` 보호 계약 및 원 source-lock artifact를 갱신하지 않는다.
이번 작업은 이전 한정 승인을 다른 보호 파일 수정 승인으로 확대하지 않았다.

## 14. finding별 현재 실제 oracle

`reproductions.json`은 같은 SQL/parser/lease 입력으로 다음 실제 값을 저장한다.

|ID|역사 실제 값|현재 실제 값·독립 기대|
|---|---|---|
|IA01|native1B, committed0B|native1B, committed1B; inner rollback2B|
|IA02|native3B, committed1B|native3B, committed3B; 후속 실제 rollback 가능|
|IA03|native2B, committed0B|native2B, committed2B|
|IA04|실제3 parse에4 calls/8B|3 calls/6B|
|IA05|pending1/completion0, native budget0|pending0/completion1, native budget0|
|IA06|한 transaction owner1000/pending5000 keys|33번째 실행 전 명시 오류, native32행/pending160 keys, rollback 후0|
|IA07|generation의 두 oracle SELECT176/185행|같은176/185행은 setup, 제품 generation oracle SELECT0|

각 현재 값은 독립 SQLite SELECT/literal 호출 수/native budget 또는 실제 cursor 위임을 oracle로 삼는다.
counter에 넣은 값을 다시 expected로 사용하지 않는다. direct 실험은 pytest 신규 수에 더하지 않는다.
이 결과의 구현 측 교정과 별도 독립 finding closure를 혼동하지 않는다.

## 15. 전층 attribution 및 실패 경계

backend generation은 명시 sandbox 연결/원 bootstrap, D3는 독립 HTTP ContextVar다.
setup/oracle를 제품 generation 합계에서 제외한다. JSON completion과 전체 C1 admission 성공은
다르며 원 정의를 유지한다. Flutter caller Zone은 shared E1 작업을 한 번 소유하고 E3 verify/
prepare/commit을 구분한다. E3 readback은 e3Commit inclusive 값이며 다시 합산하지 않는다.
실패 SQL의 attempted/effective work는 지우지 않고 실제 rollback 부분만 구별한다.
retry/revalidation은 실제 수행한 만큼 반복 계수하고 provenance가 생략한 hash는0이다.
관측 만료/HTTP 실패/취소/closed scope/Frozen fallback은 원 회귀와 실제 TLS probe로 확인한다.

## 16. 메모리와 산술의 주장 범위

primitive category는 고정 enum, SQL table128/savepoint32/transaction owner32다.
pending aggregate는 row/object별 log가 아니다. bound는 connection별이며 전체 RAM이 임의의
connection 수와 무관하다고 주장하지 않는다. active owner를 버리거나 합쳐 overflow를 숨기지 않는다.
Python int/Dart BigInt의 기존 overflow 시험을 유지한다. closed snapshot은 불변이며 native tail은
finish_when_idle 경계로 완결한다. 정상 측정 session은 실제 작업이 종료된 뒤 해제해야 한다.

## 17. I25와 다섯 N의 인계

고정 H/D와 N=1000/5000/10000/50000/100000의 no-change/card/cash 비용 grid는 NOT RUN이다.
H에는 hot/control/required descriptor가 포함되며 current row105개만으로 H를 정의하지 않는다.
이번 SQL/counter 교정은 측정 수치를 신뢰할 전제이지 steady-state I25 PASS 증거가 아니다.
initial/restart/fallback/명시 legacy materialization의 허용 O(N)을 warm 비용으로 합치지 않는다.
raw cursor/executescript/native-handle 우회, 정확한 parser 소비 prefix, scalar record encoding,
opaque crypto 내부 및 physical VFS/WAL/file durability는 주장 범위 밖이다.
완결 측정은 지원된 실제 실행 경계와 종료 cohort, 원 counter·구조 operation·HTTP/resource를 함께 사용해야 한다.

## 18. 최종 Git 절차

completion gate가 남아 있으면 index와 dirty worktree를 보존하고 완료 commit/push를 하지 않는다.
정적 검사·build 성공도 배포 승인이 아니며 APK를 설치하지 않는다.
최종 HEAD/local main/origin/main/실제 remote main은 모두 시작 commit과 동일하다.
index는 비어 있고 dirty worktree를 의도적으로 보존했다. 완료 commit은 NONE, push는 NOT PERFORMED다.

## 19. 실제 HTTP·전층 대조와 기존 보호

원 독립 HTTP probe2개와 authority probe2개를 출력 경로만 IC01으로 분리해 실행했다.
TLS에서 실제 SHA/parser witness와 동시201/401 요청의 scope를 대조하고, 실제 generation/
observation/transfer counter와 Flutter E2 validation/E1 committed payload/E3/E4 금융 행을 비교했다.
단일 small cold off/on은25.526/21.679초였지만 한 쌍이므로 계측 speedup이라고 해석하지 않는다.
장부의 Unicode/정확 monetary 원문, root/objects/금융 rows의 enabled/disabled 동등성은 PASS다.
identical reuse에서 추가 object INSERT가 없고, stale/canceled authority 시 실제 accepted sequence0 및
committed accepted payload0을 확인하는 기존 assertion을 유지했다.

원 boundaries10/lineage4/HTTP3/overhead1/unit25/current source-lock6,
backend 원24와 별도 authority2를 합친 원 B03 구현75개는 모두 PASS다.
독립35개는 backend18/mobile14/별도HTTP2/overhead1이며 모두 실행했다.
그중7개만 승인된 역사 구현, 나머지28개는 현재 구현이다. 역사 PASS는 교정 정확성 증거로 합치지 않는다.
신규 교정은 backend26+Flutter18+실제high-N 표본1 = **45 PASS / 0 FAIL / 0 SKIP**다.
직접 실험·반복 실행·원16개 calibration은 신규 수에 합산하지 않았다.

Frozen/file 경계, P0 fingerprint byte 동등성, late import, closed scope/native tail,
retry/expiry/fallback 및 E1/E3 실제 row 정산은 기존 정확 oracle와 새 SQL 회귀로 유지했다.
E4 건강한 반복 읽기·출처 재사용 비용 검사는 통과했지만 전체 큰-N 비용 grid를 재측정한 것은 아니다.
B01/B02/E4-A01/E4-RA01을 재개할 새 제품 결함은 관찰하지 않았다.

## 20. 정적·build·보존 검사

최종 Flutter analyze, debug build, Ruff, compileall, 변경 파일 format 및 diff whitespace 검사는 PASS다.
동결 helper 원문은 format으로 덮어쓰지 않았고, 역사 실행 adapter만 원 package 언어3.3 기준으로 확인했다.
frontend `npm run build`도 exit0이다. APK는 build만 했고 설치하지 않았다.
`evidence/summary.json`의 실행 command·exit·elapsed와 raw log를 우선한다.
고의 종료한 중간 전체 실행, SDK filter 실패, 첫 high-N API 검사 실패 및 기존 non-normative MIME
진단 실패는 지우지 않는다. 전부 현재 제품 correctness 실패와 분리해 남겼다.

원 보호 제품6개 source와 P0 파일은 untouched이므로 새 source-lock 갱신이 필요하지 않다.
현재 exact SHA와 역사 revision restoration 회귀6개는 PASS이고 SKIP/XFAIL을 추가하지 않았다.
관련377개 보존 대조에서 기존 변경은 진단 wrapper3개뿐이다. 원 findings/report/test/evidence를
갱신하지 않았고 DB user_version4·schema·protocol·financial engine은 불변이다.

## 21. 재현 인계와 남은 blocker

실행 방법은 [IC01 README](../../benchmarks/t66f-b03-ic01/README.md), 최종 집계는
[summary.json](../../benchmarks/t66f-b03-ic01/evidence/summary.json), 비용 및 한계는
[performance-summary.json](../../benchmarks/t66f-b03-ic01/evidence/performance-summary.json)이다.
교정 source3개 및 새 단위 테스트2개의 exact SHA는 sealed-source.json에 고정했다.
새 유효 SHA를 역사 제품 source-lock의 대체 승인으로 쓰지 않는다.

**REMAINING UNCERTAINTY**는 일곱 finding의 정확 oracle 차이가 아니라 활성 계측100k의 관측별
완료 가능성이다. 전층 작은 byte reconciliation PASS를 large lease proof로 확대하지 않는다.
현재 독립 B03 재감사 준비 완료 선언은 **NO**, Phase B 최종 grid 재개도 독립 재감사 전 **NO**다.
추가 Critical/High/Medium/Low 제품 결함은 확인하지 않았다. 성능 증거 미확정을 새 severity finding
또는 이미 해결된 제품 B01/B02 재개로 임의 변환하지 않았다.

## 22. 최종 구현 측 판정

**T6.6F-B03-IC01 CORRECTION INCOMPLETE — ADDITIONAL TARGETED WORK REQUIRED**

일곱 계측 결함은 구현 측 exact oracle로 교정했지만, completion gate27/36을 충족할
100k 계측 lease 증거가 부족하다. 이 상태에서 완료 명의 commit/push를 하지 않는다.
다음 작업은 측정된 E1 observer 비용을 반영한 유한100k 관측별 계측 검증 계획을 확정하는 것이다.
전 다섯 N 비용 proof, Android/VFS/power-loss 및 R1은 계속 별도 의무다.
