# T6.6F-B03-IC01-P04 후반 상태 차등 진단

**INCONCLUSIVE — PRESERVED STATE OR ESSENTIAL EVIDENCE UNAVAILABLE.**

원397,146개 client DB는 보존돼 있으나 동일 Target의 backend SQLite·완전 catalog·증명 자료는
P03 서버 종료에서 삭제됐다. 실제 인증된 D3→HTTP→E2→E1 tail을 실행하지 않았다.
6개 일관 복제본의 E1 보조 네 모드 비교와 독립 counter 보정은 PASS했지만,
일관된 wall-time 증가를 분리하지 못했다. P03 실패는 그대로 FAIL이며 새100k cold 시도는0회다.

## 1. 시작 저장소와 Git index

HEAD/main/origin/main/실제 remote main은 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이었다.
staged 변경은 없고 기존 tracked 변경은 B03 backend 진단2개와 Flutter test support wrapper1개다.
[시작 inventory](benchmarks/t66f-b03-ic01-p04/evidence/starting-state.json)에 staged/unstaged/untracked,
기존3,301개 파일 SHA와 index를 기록했다. P03 이전3,116개와 P03 추가 증거까지 보존 대상이다.
index 파일 SHA는 `d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`,
entries SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다.
reset/stash/clean/checkout/rebase/restage를 하지 않았다.

## 2. IC01/P01/P02/P03 보존과 판정 경계

기존 미커밋 source·시험·보고서·원 독립 findings·P03 실패 자료를 변경하지 않았다.
추가는 본 보고서와 `docs/benchmarks/t66f-b03-ic01-p04/`뿐이다.
프로젝트 상태·domain-model·known-issues·architecture의 서버 authority 경계와
요청된 B03/IC01/P01/P02/P03/B02/A02/Phase B closure 문서를 현재 source와 대조했다.
규범 §5,§15–17,§22–26,§29,§31,§34–35를 적용한다.
구현 측 보정,이번 독립 byte oracle,검증한 역사 full suite,시간 추정 및 필수 미확인 증거를 구분한다.

## 3. P03 실패 재구성

[원 gzip trace 재집계](benchmarks/t66f-b03-ic01-p04/evidence/p03-reconstruction.json)는
P03의 `label=full`6282개 요청만 사용했다. prefix cohort를 섞지 않았다.
세 관측의 성공 object packet은2089/2156/2028개,전송 객체는129376/137984/129786개다.
합397146은 native unique rows 및 실제 object INSERT effective rows와 같다.
각 관측은201→성공200들→410 OBSERVATION_EXPIRED→release204로 종료했다.
관측3 뒤 새 관측을 만들지 않았고 전체2699.957907초에 실패했다. 외부 강제 종료나 RSS guard 실패가 아니다.
`disposable-location.json`의 `full_attempts:0`은 초기 위치 기록의 미갱신 값이다.
실제 횟수는 `full-attempt.json`,full trace와 FAIL result로 확인하며0으로 오독하지 않는다.

## 4. 세 관측의 실제 timeline

모든 생성/만료일은2026-10-22 UTC다. backend 시간은 원 `perf_counter_ns`,client SQL은
Dart Stopwatch 누적값이다. 보존한 same-host monotonic/UTC anchor의 offset span은11721ns다.
서로 다른 실행의 절대 monotonic 시각을 합치지 않았다.

|관측|생성→만료|새 객체|성공 packet|backend wall / CPU 초|client SQL 경계 차이 초|callback 하한 경계 차이 초|
|---|---|---:|---:|---:|---:|---:|
|1|07:06:30→07:21:30|129376|2089|631.580178 / 630.482822|110.720868|7.121624|
|2|07:21:30→07:36:30|137984|2156|652.256539 / 651.168348|124.278048|7.962837|
|3|07:36:30→07:51:30|129786|2028|602.578088 / 601.606056|145.070668|8.464119|

client 경계는 fresh observation 요청 직전부터 다음 같은 경계까지여서 release/renewal 일부를 포함한다.
SQL에 callback이 포함되고 backend handler는 HTTP 대기 안에 있다. 서로 더해 전체 시간을 만들지 않는다.
complete client HTTP wait,hash-only wall,parser-only wall,traversal-only wall 및 timing observer 자체 비용은
원 기록에 분리돼 있지 않다. 해당 항목은 NOT MEASURED이며0이 아니다.
마지막 성공/시도 원 request와 구간별 progress·bytes·counter 차이를 JSON에 보존했다.

## 5. 원397146개 staged 상태의 identity

원 파일은 `/tmp/mn-p03-real-RMZIIJ/full-client/segmented-store-v1/` 아래
`f5c0796c0a144c198b70925f5ba95a3bf1005986eba3b7f677fbbda85258005f.sqlite`다.
파일612196352B,objects397146개,body259743775B,refs397238개,edges397234개다.
WAL/SHM이 없고 read-only quick_check/foreign_key_check는 정상이다. 명시적 checkpoint나 migration을 하지 않았다.
accepted current/previous는null,sequence0,generations 및 generation_roots는0개다.
세 acquisition은 모두 interrupted/OBSERVATION_EXPIRED이고 원 staging manifest/NS/epoch/root를 보존했다.
원 cache key는 보존 Target·원 server의 loopback 주소 형식·유한 port 후보를 독립 C1/SHA로 대조해
`https://127.0.0.1:52741` 하나로 식별했다. 이는 측정 밖 identity 확인이며 credential 복구나 인가가 아니다.

## 6. 남은3386개 집합

|종류|미수신 객체|canonical bytes|
|---|---:|---:|
|index-node|1647|854508|
|index-leaf|1737|854258|
|hot|1|87364|
|control|1|3178|
|합계|3386|1799308|

이 count/byte 차이는 P03 생성 시 완전 graph oracle와 원 partial DB를 대조한 값이다.
저장된 객체는 모두 원 roots의 알려진 reachable 집합 안에 있어 unrelated orphan을 목표에서 빼지 않았다.
그러나 **완전한3386개 hash 목록은 확보하지 못했다.** 실제 refs에서 missing인 frontier는92개/136538B다.
나머지3294개는 아직 수신하지 않은 부모 아래여서 현재 DB에서 이름을 알 수 없다.
[known-frontier](benchmarks/t66f-b03-ic01-p04/evidence/known-frontier.json)를 전체 missing set으로 광고하지 않는다.

## 7. 일관 snapshot·clone

[준비 코드](benchmarks/t66f-b03-ic01-p04/prepare.py)는 원 파일을 `mode=ro&immutable=1`로 열고
SQLite backup API로 별도의 폐기용6개 복제본을 만들었다. 원 main 파일 단순 복사를 하지 않았다.
모든 table의 schema·PK 순서·타입 구별 실제 SQL 값으로 만든 streaming digest가 원본과 일치했다.
clone별 accepted·staging·profile·objects·metadata 및 offline-mode 파일은 동일하다.
반복 전에는 원본을 읽어 해당 **폐기용 clone만** 다시 backup하고 동일 digest를 확인했다.
원본에는 write/checkpoint/sidecar 정리를 하지 않았다.
종료 후 전체 SQL 값 대조에서도 A/B/C/D 네 결과는 같고 smoke A/B도 같았다.

## 8. ON/OFF 실험 설계와 실제 HTTP 제약

[고정 계획](benchmarks/t66f-b03-ic01-p04/plan.json)은128-object E1 smoke 한 쌍과
2048-object 네 모드 보조 비교2반복이다. 첫 순서는A/B/D/C,둘째는C/D/B/A다.
추가 표본·더 큰 cohort·새 cold run으로 확대하지 않았다.
실제 HTTP tail 쌍은 **0회**다. 완전한 source catalog와 backend current/commit/input/retention 증명이
없으므로 실제 D3 handler를 같은 Target로 안전하게 시작할 수 없었다.
원 backend는 `CaptureSandbox.__exit__()`에서 TemporaryDirectory를 제거한다.
P03 보존 항목에는 manifest·graph 요약·trace가 있지만 그 SQLite의 일관 사본은 없다.
historical source는 NS가 다르며 실제 검증에서도 CACHE_CONTEXT_MISMATCH로 거부됐다.
규범 §5의 restart epoch 회전을 생략하거나 expired 관측을 되살리지 않았다.

## 9. 정확한 네 모드

|모드|논리 counter|추가 SQL/callback timer|이번 의미|
|---|---|---|---|
|A|OFF|OFF|native E1 보조 기준|
|B|ON|OFF|현재 IC01/P02 CostDatabase와 LogicalCost|
|C|OFF|ON|P03 TimedDatabase SQL API 경계|
|D|ON|ON|P03의 outer SQL/inner callback timing과 같은 조합|

제품 hash/parser/SQL은 그대로 한 번씩 위임했다. 새 일반 tracing 체계를 만들지 않았다.
공통 coarse wall/CPU/RSS는 구간 전후만 읽고 큰 per-object log나 active-window 전체 DB oracle는 없다.
OFF counter는 null/NOT INSTRUMENTED다. timing OFF의 SQL time과 callback time도 NOT MEASURED다.

## 10. 실제 취득 tail 비용과 보조 결과

**실제 missing-object tail 비용은 NOT MEASURED.** 아래는 원 크기의 DB에서 이미 저장된2048개
index object를 제품 `putVerifiedStagedBatch(ref,bytes:null)`로 새 **local-only** stage에 연결한 보조 실측이다.
옛 manifest는 local fixture로만 사용했고 HTTP/IncrementalFetcher.acquire/publication을 호출하지 않았다.
expired manifest를 current authorization으로 사용한 것이 아니다.

|모드|반복1 초|반복2 초|중앙값 초|
|---|---:|---:|---:|
|A|0.725238|0.929865|0.827552|
|B|1.029967|0.570553|0.800260|
|C|0.992589|0.563818|0.778204|
|D|0.598216|0.953812|0.776014|

신규 immutable payload 취득은0개,local progress link는2048개,transaction은32회다.
새 flow가 전체397146개를 재순회하는 비용이나 남은3386개 취득 시간으로 이 값을 바꾸지 않는다.

## 11. HTTP 기여

P03 원 service wall 합과 packet 수는 §4에 있다. 가장 느린 성공 handler도 약1.046초였고
이는 초반 큰 raw packet이다. 큰 후반 지연은 handler 내부의52초 요청이 아니라 **요청 사이 공백**이었다.
관측3의6282번째 전체 요청까지 expired 정리는 정상이며 source credential/typed path 검사를 우회하지 않았다.
P04 실제 큰 tail HTTP는 없으므로 HTTP ON/OFF 차이나 새 response bytes를0으로 만들지 않았다.
별도 소형 실제 TLS2 tests는 새로 PASS했지만 다른 작은 fixture의 원시 보정/인가 증거다.

## 12. E2 검증 기여

P03에서 client hashing·canonical validation·traversal의 분리 wall은 없다.
E2 `SyncVersions.rawSchema`는 `toJson()`의 실제324B parser span을 사용하고,
index-leaf는 실제 fact-key hash도 수행한다. 이것은 계수에서 누락하거나 object 크기×edge로 만들지 않는다.
중단된 active DFS/seen/frontier는 durable receipt가 아니다. `fetch.dart:_acquireContinuousCold`는
call 안에서만 같은 Target renewal proof를 유지하며 새 process에서는 이 증명이 사라진다.
따라서 clone에서 새 acquire를 시작하면 cached object 재검증·stage 연결·graph 순회도 필요하다.
이를3386개 network payload만의 tail로 부르지 않는다.

## 13. E1 persistence 기여

P03 client SQL API 누적380.084418초에는 진단 wrapper와 callback이 포함된다.
관측별 경계 차이는 §4에 있다. 이것을 physical SQLite/VFS I/O 또는 순수 fsync 시간으로 부르지 않는다.
이번 E1 cohort의 stage TEXT는 attempted/effective/지원된 committed 모두204800B다.
actual SQLite CAST-to-BLOB UTF8 길이로 독립 확인했다. 이미 저장된 object body를 재삽입하지 않았고
동일 body합259743775B가 유지됐다. trigger의 scalar update count와 TEXT/BLOB bytes는 별개다.

## 14. SQL observer 기여

P03의23.548612초는 TEMP callback **본체**의 누적 하한이다.
SQL 분류·prepare/trigger·FFI·pending settle·counter allocation·GC·cache와 timer 자신을 전부 분리한 값이 아니다.
이번 D의 callback 하한은0.028376/0.029464초였다. D의 SQL API 구간은0.297512/0.648698초로
callback을 포함한다. C의 SQL API는0.678296/0.279636초다.
이 값들을 합산하거나23.55초를 없애면 cold가 성공한다고 추론하지 않는다.

## 15. 추가 timing observer 영향

실제 pair 차이 D−B는−0.431751/+0.383259초,C−A는+0.267351/−0.366047초다.
logical counter 차이 B−A도+0.304729/−0.359312초로 부호가 바뀐다.
표본2개에서 안정적인 추가 wall 비용을 격리하지 못했으며 p95·유의성·원인 비율을 만들지 않았다.
프로세스 CPU는100Hz tick이고 runtime의 여러 thread 때문에 일부 CPU가 wall보다 클 수 있다.
현재 증거로 optional timer 제거의 full-size 개선량을 확정하거나 구현하지 않는다.
P03 per-packet JSON·RSS·backend trace의 독립 overhead와 allocation/GC 원인도 미분리다.

## 16. Prepared statement 재사용

보조 B/D의 connection별 hit8430/miss31,created31/finalized31,peak31,rejection0이었다.
capacity32와 reset/rebind/connection ownership을 바꾸지 않았다. 결과 row cache도 없다.
기존 P02 lifecycle·bound·실패/close 회귀를 새로 PASS했다.
cache 초기화/open/snapshot/close 시간은 원 records에 별도로 있고 timing 없는 값을0으로 꾸미지 않았다.

## 17. 관측 renewal·인가

원 P03 실제 renewal의 expiry 요청 시작→첫 재개 요청은0.621458239/0.821405336초다.
TTL900/active flow 최대3회는 유지됐다. P04 큰 tail의 새 observation/renewal은 NOT EXERCISED다.
fresh observation·principal/NS/epoch/origin/Versions/Target 및 original ticket 검사를 생략하면
동등한 재개 실험이 아니므로 그런 우회는 하지 않았다.
작은 실제 TLS 및 focused fetch/authority tests에서 auth·expiry·staged reuse 검사를 새로 통과했다.

## 18. Graph closure와 남은 의존 작업

의존 순서는 다음과 같다.

1. 동일한 실제 backend의 fresh authorized observation과 원 identity 확인.
2. 새 process라면 staged bytes의 재검증과 새 progress links/DFS proof 재구성.
3. live D3 권한 아래 missing typed paths를 탐색해 index3384개와 hot/control2개 수신·검증·durable staging.
4. 완전 graph/typed membership/count 및 generation metadata proof 확인.
5. E3 complete Target/F(raw)/hot·raw/provenance 검증,receipt·pin 준비와 원 AppState guard의 원자 COMMIT.
6. E4 generation-consistent financial read,마지막 snapshot과 native/collector 종료.

§16은 lease를 transfer 권한으로 규정한다. 완전 취득·객체 검증 뒤의 local E3/E4에 임의의
추가900초/누적2700초 deadline을 적용하지 않는다. 반대로 필요한 bytes가 남은 incomplete graph를
만료 뒤 accepted로 만들 수도 없다. 이번에는 closure 조건 자체가 미충족이며 새 closure 비용은 미측정이다.

## 19. E3/E4 terminal-path

큰 resumed path의 E3/E4는 **NOT EXERCISED**다. accepted current/previous null과sequence0을 보존했다.
따라서 재개 terminal snapshot·100k monetary/Unicode read의 새 PASS가 없다.
역사 성공의 last HTTP 뒤 local closure·E3 반환 구간은 약392초였으나 exclusive E3 시간이 아니다.
이를3,386개 취득 추정 시간이나 유효 observation 잔여 시간에 단순 합산하지 않는다.
original AppState ticket/final guard→COMMIT은 source SHA와 새 작은 authority 회귀로 보존 확인했다.

## 20. Counter 정확성과 동일성

[독립 oracle](benchmarks/t66f-b03-ic01-p04/evidence/component-analysis.json)은 counter를 expected로 쓰지 않았다.
native body 길이와 실제 fact-key·view 입력의 literal framed buffer를 측정 후 독립 구성했다.

|경계|독립 expected = 실제 B/D|
|---|---:|
|object/fact-key/view hash 입력|1206871B /3126회|
|fact-key hash /view hash|1046회 /32회|
|metadata checksum 입력|47104B|
|primary validation submitted/completed|각1775992B /4224회|
|stage TEXT attempted/effective/committed|각204800B|

validation 식은 `1034232 + 2048×324 + 32×(1472+3×324)`다.
세 metadata version span은 ReleaseContract와 CacheNamespace 비교의 두 피연산자에서 실제 수행된다.
논리 span은 physical memory-read bytes가 아니며 hash·validation·write를 unique byte 총합으로 합치지 않는다.
각 반복 B/D의 전체 primitive/SQL/work map도 완전히 같았다. 모든 collector는 닫혔고 overflow는 없었다.
savepoint/rollback/retry/closed-scope/native-dispatch 경계는 새 current corrected tests로 별도 확인했다.
실행하지 않은 큰 HTTP/E3/E4까지 이 보정을 확대하지 않는다.

## 21. DB 동일성과 원본 보호

측정 전6개 clone의 전체 SQL 값은 원본과 같았다. 측정 후2048개 local link를 더한
A/B/C/D 결과끼리도 모든 table 값이 같았다. immutable object는397146개로 유지됐다.
원 SHA/논리값·accepted pointer·legacy 파일은 그대로다. 실제 non-null previous accepted generation의
복구를 이번 큰 clone에서 새로 검증했다는 뜻은 아니다. 그것은 기존 targeted/historical 증거 범위다.

## 22. 자원과 메모리

component runner process-tree 표본 peak는918994944B였다. focused Flutter 회귀 runner는2222817280B였다.
개별 Dart 표본·process lifetime max·runner 자식 포함 RSS·file 크기는 서로 구별한다.
동시에 실행한 다른 runner까지 합친 machine-wide peak나 Android heap을 측정한 것은 아니다.
보조 측정은 다른 검증 종료 뒤 실행했다. 준비/backup/digest는 window 밖이다.
8GiB runner guard와2GiB free-disk guard 안에서 종료했고 고정6개 복제본 외의 큰 실행을 만들지 않았다.

## 23. 서로 다른 역사 실행 비교

독립 cold2463.561424초와 A02 cold2590.048631초는 다른 실행이다.
P03의 동일 raw VALUE/종류/크기와 새 NS/epoch·root 차이를 유지해 비교한다.
각 원 trace의 가장 큰 client inter-packet gap은독립83.533117초,A02 65.945805초,P03 52.073764초다.
P03의2초 초과 gap합76.314375초에 비해 독립108.974708초,A02 72.214402초였다.
[별도 재집계](benchmarks/t66f-b03-ic01-p04/evidence/historical-gap-comparison.json)는
절대 clock을 합치지 않고 최초 cold 구간만 사용한다.
host/cache/JIT/SQLite/file 조건과 관찰자 구성이 같지 않으므로 차이를 모두 counter 비용으로 돌리지 않는다.
이 자료만으로 환경이 주원인이라는 B 판정을 내리지도 않는다.

## 24. Critical path 귀속

P03 최대 gap은389216개 수신 뒤52.073764초였다. 전후 server handler는약0.302/0.286초로 정상 범위다.
286688개 뒤20.693040초,136864개 뒤3.547572초도 client 요청 사이에 있었다.
주변 checkpoint의 SQL 증가는 관찰되지만 snapshot이128요청 간격이라 정확한52초 내부의
SQL/hash/traversal/GC/fsync 분할을 복원할 수 없다. 그 공백을 timer만의 낭비로 분류하지 않는다.
성공한 두 실행에도 큰 공백이 있어 product/host/representation tail의 가능성을 열어 두며
확정된 제품 결함이나 특정 instrumentation 병목으로 승격하지 않는다.

## 25. 실질 부족량 추정

만료 직전10/30/60/120/300초의 실제 전송률은각172.8/170.667/132.167/90.617/127.767개/초다.
단순 missing acquisition만의 추정은약19.6–37.4초 범위다. 이는 **실험 추정**이며 실제 tail 실측이 아니다.
정확한 순서의 typed-path 발견·cached rewalk·closure·hot/control verification 및 E3/E4는 포함하지 않는다.
최대64-item 기준 필요한 packet의 이론적 하한은53개지만 그래프 의존성 때문에 실제 횟수는 미확인이다.
새 process의397146개 rewalk 비용은 모른다. 그 크기를2048개 E1 표본에 곱해 실제 비용으로 꾸미지 않는다.

## 26. 인과 결론

확정된 사실은 관측3 만료,incomplete graph,client 쪽 큰 요청 간 공백,동일 counter/state의 보조 비교다.
논리 counter나 timing observer의 안정적인 wall excess,환경 지배,특정 SQL/GC defect는 분리하지 못했다.
따라서 A/B/E disposition을 선택하거나 특정 비용을 제거하면100k가 성공한다고 말할 수 없다.
actual tail/terminal path도 없으므로 C disposition을 선택하지 않는다.
**D — 동일 Target backend catalog·증명 자료 부재**가 현재 가장 좁고 입증된 차단 사유다.

## 27. 측정 한계

full tail ON/OFF는0쌍이다. 보조 E1 두 반복은 packet·missing object·full graph 분포의 대체물이 아니다.
wall 차이의 부호 반전 때문에 population p95나 확정 overhead 비율은 없다.
P03의exclusive observer allocation/GC/fsync,완전 HTTP wait와 pure E2 CPU는 NOT MEASURED다.
counter-only 모드B의 의미 보존은 E1 보조·소형 원시 보정에서 확인했지만 전체100k 완료 보장은 아니다.
mandatory logical events를 sampling하지 않았고 빠른 모드에서 counter 범위를 줄이지 않았다.
규범의 필수 logical-byte 계수와 UDF별 Stopwatch/active-window JSON 형식은 같은 의무가 아니다.
필수 전수 counter에 coarse 구간 wall을 결합하는 계측 방식은 원칙상 workload·TTL·attempt를 바꾸지 않고
구성할 수 있다. 그러나 이번에는 전체 D→E 범위의 그 방식과 고정 lease 완료를 검증하지 못했다.
따라서 이를 독립 승인된 Phase B 대체 증거나 grid 재개 허가로 취급하지 않는다.

## 28. Source-lock

P0 recoveryLineageFingerprint와 protected product6개/current exact SHA 기대값을 바꾸지 않았다.
새 lineage·source guards와 현재 corrected tests는 PASS다. 역사23 locks/full suites는 P02의 역사 증거다.
원 independent finding·frozen reproducers도 그대로다. IA07 원 cursor snippet은 수정 없이 현 source에 실행해
176/185행이setup에 있고 product generation catalog query0임을 새로 확인했다.
첫 P04 wrapper가 원 stdout의 Python repr를 JSON으로 읽은 실패는 별도 log로 남겼고
wrapper만 literal parser로 바로잡았다. 원 repro를 고치거나 실제 실패를 SKIP하지 않았다.

## 29. B01/B02·금융·legacy

B01 strict `[201]*4+[429]`,B02 ceilings/explicit large profile/packet/cache/TTL900/최대3회는 불변이다.
B01/B02,E4-A01/E4-RA01은 재현된 제품 회귀가 없어 CLOSED다.
backend 금융 authority,C1,exact monetary/Unicode,Snapshot v7,OfflineBaseline v4,
sync_root와 legacy fingerprint 분리,production schema와 E3 ticket/guard를 바꾸지 않았다.
Frozen B/J는 input-only이며 ACK/rebase를 하지 않았다. 원본과 모든 clone의 offline-mode 파일 hash는 같다.
실제100k E4/native Frozen-B 설치·Android/VFS/전원 손실은 이번 증거에 포함하지 않는다.

## 30. Fresh focused 검증

backend64 PASS,Flutter164 PASS,소형 실제 TLS2 PASS다. 새 P04 framework case는
E1 보조1개와 historical namespace 대체 거부1개로 **2 PASS/0 FAIL/0 SKIP**다.
clone 전후 전체 SQL 값·byte oracle·IA07 직접 실험은 별도의 native assertion 검사다.
두 모드의 시간 차이를 맞추기 위해 실패 시험을 SKIP/XFAIL하거나 source를 수정하지 않았다.
첫 IA07 helper의 출력 파싱 실패와 최종 교정 wrapper 결과를 구분해 보존했다.
frontend npm build도 새로 PASS했다. 새 진단 코드의 analyze/format/Ruff/compileall/diffcheck는 최종 receipts에 있다.

## 31. 전체 회귀 상태

제품/기존 instrumentation source가 그대로이므로 full backend·Flutter·앱 analyze/build를 재실행하지 않았다.
**검증한 역사 P02 결과**는 backend1436 tests/1540 subtests PASS,
Flutter1690 PASS/0 FAIL/2 SKIP다. 이를 fresh full PASS로 부르지 않는다.
APK 설치·서비스 변경·배포·segmented activation은 없다.

## 32. 단 하나의 권고 조치

**다음 허용된 검증의 test-only 서버 종료 경계를 보강해 동일 epoch의 살아 있는 backend를
유한 tail handoff까지 유지하고,정리 전에 SQLite backup API로 완전한 source 사본을 보존한다.**

대상은 현재 disposable TLS harness의 `main()`이 `RetentionSandbox` context를 빠져나가는 경계다.
제품 `CaptureSandbox`나 production startup 정책을 고치는 요청이 아니다.
counter scope를 닫고 worker 완료 뒤 증거를 보존하며,명시 cleanup은 기존 client-close→worker-join 순서를 지킨다.
snapshot만 새 process로 복원하면서 old epoch를 강제로 유지하는 것은 §5에 어긋나므로 허용하지 않는다.
작은 fixture에서 byte-identical backup,fresh auth/expired 거부,원900초/3회 및 최종 cleanup을 확인해야 한다.
이는 하나의 **증거 수명/인계 보강 요청**이며 P04에서 구현하거나 새 full run을 실행하지 않았다.
성능 교정이나 끝없는 profiling을 권하지 않는다. source-SHA approval가 필요한 protected 변경은 없다.

## 33. IC01 구현 상태

IA01–IA07와 P02 cache32는 보존됐고 새 scoped 보정을 통과했다.
그러나 고정 lease 아래 계측100k 전체 취득·closure·E3/E4·최종 cost snapshot은 여전히 없다.
**IC01 INCOMPLETE**이며 원 IC01/P01/P02/P03 보고서를 완료 상태로 바꾸지 않았다.
현재 counter에 특정 수정이 필요하다는 근거도 확정하지 못했다.

## 34. 독립 B03 재감사·Phase B 경계

준비 완료 NO다. 보조 E1 counter 동일성과 source 보존은 재사용 가능한 calibration 증거지만
actual full cold 또는 actual resumed tail/terminal-path 성공 증거가 아니다.
B03 independent PASS·five-point grid 재개·T6.6F exit를 선언하지 않는다.
R1 large restore는DEFERRED,activation gate는CLOSED,Android/device/VFS/power-loss는미검증이다.

## 35. Git 상태와 최종 판정

commit NONE,push NOT PERFORMED다. 모든 기존 dirty 작업과 index 및 P03 원 SQLite를 그대로 두었다.
worktree는 새 P04 증거 때문에 DIRTY — INTENTIONAL이다.
[최종 보존 검사](benchmarks/t66f-b03-ic01-p04/evidence/final-preservation.json)와
[기계 요약](benchmarks/t66f-b03-ic01-p04/evidence/summary.json)을 함께 제공한다.

**INCONCLUSIVE — PRESERVED STATE OR ESSENTIAL EVIDENCE UNAVAILABLE.**
client DB는 VERIFIED이나 같은 Target의 backend catalog·증명이 없어서 필수 actual tail 비교는 차단됐다.
P03은실패,새100k cold는0회,독립 B03 PASS와 배포 허가는없다.


```text
T6.6F-B03-IC01-P04 LATE-STAGE DIAGNOSIS:
INCONCLUSIVE

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

ORIGINAL IC01/P01/P02/P03 CHANGES:
PRESERVED

ORIGINAL GIT INDEX:
PRESERVED

FINAL WORKTREE:
DIRTY — INTENTIONAL

NEW COMMIT:
NONE

PUSH:
NOT PERFORMED

BINDING PROTOCOL:
UNCHANGED

PRODUCT SOURCE CHANGED:
NO

P03 FULL COLD RESULT:
FAILED — 397146 / 400532 OBJECTS

P03 OBSERVATIONS:
3 / 3 EXPIRED

P03 E3 PUBLICATION:
NOT REACHED

P03 E4 READ:
NOT REACHED

PRESERVED LATE-STAGE DATABASE:
VERIFIED

PRESERVED SOURCE DATA MODIFIED:
NO

DISPOSABLE CLONES:
6

CLONE LOGICAL EQUIVALENCE:
PASS

ORIGINAL REMAINING OBJECTS:
3386

MATCHED TAIL ON/OFF PAIRS:
0 — E1 보조 네 모드 비교만 2반복

TAIL EXPERIMENT:
NOT RUN

TAIL INSTRUMENTATION OFF TIME:
NOT MEASURED

TAIL INSTRUMENTATION ON TIME:
NOT MEASURED

ADDITIONAL TIMING OBSERVER COST:
PARTIAL — E1 보조 차이의 부호가 반복마다 반전

LOGICAL COST COUNTER OVERHEAD:
PARTIAL — 전체 tail 기여 미분리

HTTP CONTRIBUTION:
P03 backend wall 합 1886.414805s; P04 실제 tail 미측정

E2 CONTRIBUTION:
분리 wall 미측정; P03 최대 client 요청 간 공백 52.073764s

E1 CONTRIBUTION:
P03 SQL API 380.084418s; 보조 A/B/C/D 중앙값 0.827552/0.800260/0.778204/0.776014s

SQL OBSERVER CONTRIBUTION:
P03 callback 본체 하한 23.548612s; timer 자체 비용과 다름

GRAPH CLOSURE:
NOT EXERCISED

E3 RESUMED TERMINAL PATH:
NOT EXERCISED

E4 RESUMED TERMINAL PATH:
NOT EXERCISED

RESUMED TAIL COUNTER SNAPSHOTS:
NOT RUN — E1 보조 snapshot은 완전 대조

HASH BYTE ACCURACY:
PASS — 실행한 보정 범위

VALIDATION BYTE ACCURACY:
PASS — 실행한 보정 범위

WRITE BYTE ACCURACY:
PASS — 실행한 보정 범위

COUNTER SCOPE CLOSURE:
PASS

NATIVE WORKER CLEANUP:
PASS — focused 회귀·소형 TLS

OBSERVATION RENEWAL:
NOT EXERCISED — 큰 재개 경로

AUTHORIZATION:
PASS — focused 회귀·소형 TLS; 실제 tail 미실행

PREVIOUS ACCEPTED STATE:
PRESERVED

PENDING FROZEN B/J:
PRESERVED

HOST MEMORY PEAK:
component runner 918994944B; focused Flutter runner 2222817280B — process-tree RSS 표본

PRIMARY FAILURE CAUSE:
PARTIAL

SPECIFIC CAUSAL FINDING:
동일 Target backend가 cleanup돼 실제 tail 대조가 불가능하며, 큰 client 공백의 counter·timer 기여는 미분리다.

NEW FULL 100K COLD ATTEMPTS DURING P04:
0

IA01–IA07 IMPLEMENTATION CORRECTIONS:
PRESERVED

P02 PREPARED-STATEMENT CACHE:
PRESERVED

P0 LINEAGE FINGERPRINT:
PRESERVED

SOURCE-SHA GUARDS:
PASS

SOURCE-LOCK POLICY:
COMPLIANT

B01:
CLOSED

B02:
CLOSED

E3 FINAL GUARD TO COMMIT:
PRESERVED

E4-A01:
CLOSED

E4-RA01:
CLOSED

FROZEN B/J:
PRESERVED

SNAPSHOT V7:
PRESERVED

OFFLINE BASELINE V4:
PRESERVED

SYNC_ROOT / V7 FINGERPRINT:
SEPARATED

NEW P04 TARGETED TESTS:
2 PASS
0 FAIL
0 SKIP

FULL BACKEND:
NOT RERUN
역사 P02: 1436 TESTS / 1540 SUBTESTS PASS; fresh focused 64 PASS

FULL FLUTTER:
NOT RERUN
역사 P02: 1690 PASS / 0 FAIL / 2 SKIP; fresh focused 164 PASS

IC01 IMPLEMENTATION COMPLETION:
INCOMPLETE

SAFE FOR INDEPENDENT B03 RE-AUDIT:
NO

SAFE TO RESUME FIVE-POINT PHASE B GRID:
NO — B03 INDEPENDENT RE-AUDIT PENDING

T6.6F PHASE B:
STILL INCONCLUSIVE

ANDROID MEMORY SAFETY:
NOT VERIFIED

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

PRODUCTION SEGMENTED ACTIVATION:
NOT PERFORMED

SAFE TO DEPLOY:
NO

FINAL VERDICT:
INCONCLUSIVE — PRESERVED STATE OR ESSENTIAL EVIDENCE UNAVAILABLE

NEXT ACTION:
test-only 서버 종료 경계를 보강해 동일 epoch의 live backend를 tail 인계까지 유지하고 cleanup 전에 일관 SQLite 사본을 남긴다.
```
