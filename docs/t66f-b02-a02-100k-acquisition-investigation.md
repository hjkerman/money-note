# T6.6F-B02-A02 — 100k 획득 잔여 병목 조사

## 01. 시작 HEAD

**판정: T6.6F-B02-A02 INVESTIGATION COMPLETE — MINIMAL CORRECTION IDENTIFIED.**
조사를 완료했으며 교정은 적용하지 않았다. 권고는 서로 독립적으로 시험할 두 변경이다.
① backend C1 admission에서 동일 값의 중복 인코딩을 제거한다.
② 새 관측의 **정확한 Target가 같은 경우에만**, 진행 중인 cold graph 검증의 위치를 유지한다.
둘 다 실제 100k 완료·보안 재감사를 통과하기 전까지 승인된 구현 또는 성능 보장이 아니다.

시작 HEAD/local main/origin/main/실제 remote main은 모두
`6282c1c3577c42bba9382d786745d583a5d88236`이었다. branch는 main이다.
합성 개발 checkout만 사용했다. production API/DB/자격증명·서비스에 접근하지 않았다.

## 02. Dirty worktree inventory

**DIRECTLY OBSERVED FACT:** 기존 tracked 변경은 8개 파일, +601/-48이다.
`backend/isolated_sync/transfer.py`, `mobile/lib/src/{app_state.dart,segmented/fetch.dart,segmented/protocol.dart,segmented/store.dart}`,
두 release artifact JSON 및 `mobile/test/segmented_adapter_isolation_test.dart`다.
신규 prefix/packet/profile/batch/authority/crash tests, 기존 B02/A01 보고서와 evidence도 미추적 상태였다.
이는 조사 대상이며 제거하거나 HEAD로 대체하지 않았다. unrelated 변경으로 임의 분류한 파일은 없다.
전체 목록·1,766개 기존 파일 SHA·1,291개 index entry는
[initial-state.json](benchmarks/t66f-b02-a02/initial-state.json)에 있다.

## 03. Source SHA와 index 보존

|제품 입력|시작 SHA-256|
|---|---|
|transfer.py|`b6d4dd33c4614f45988164c5efb644ebb113e0d6ae12bd51659ae98f36aef948`|
|fetch.dart|`90439d1d712947dee466769d56d75797b0779c23c90a528a167aff1e484ef8c6`|
|store.dart|`f2b451238b868b865beda40cfb39054d9c4a3ff36b5e27c7796b2759ee07811a`|
|graph.dart|`4738e691fd8b75e41ab01ab408b50406787815bc8956bd6e38951f336fa3172e`|
|protocol.dart|`78f1bec87d2db04c731b05619b4677afedbef666754089240f02f1e8f19e03ee`|
|app_state.dart|`c1d65f36dbd09a5f33b4a5d8d0e8b7a67ea429b0811592fce32aaeb65f9c46c1`|

저장된 100k 실행의 `active-http-100000.json` fetch/transfer SHA가 현재와 일치한다.
logical index 전체 및 staged/unstaged binary diff digest를 종료 시 다시 비교했다.
원 index에는 staged diff가 없었다. raw index 파일의 timestamp 보존을 주장하는 검사는 아니다.

## 04. 기존 B02/B02-A01 변경

원 large profile, E1 bounded staging, cold-only packet 충전, request-local typed prefix cache,
검토된 두 engine hash 및 source isolation guard를 그대로 조사했다.
기본 E2 100,000/200,000 objects/edges, 기본 E1 metadata32MiB는 유지된다.
명시적인 host 검증 profile만 500,000/1,000,000 objects/edges와 metadata384MiB다.
64 objects/1MiB packet, object64MiB/payload512MiB/path512/stages128,
request3회/observation3회/TTL900초를 바꾸지 않았다.
기존 [교정 보고서](t66f-b02-a01-targeted-correction.md)는 구현자 기록이며 독립 완료 판정이 아니다.

## 05. 성공한 50k 기준선

**DIRECTLY OBSERVED FACT — 기존 raw trace 재분석:** ledger50,000/전체50,035행,
V200,331/E200,327/depth22, canonical130,710,592B다.
실제 TLS backend→E2/E1→원 AppState E3→E4 전체 값 digest, identical0개,
one-row26개, fresh-process/restart delta의 기존 성공 증거를 보존했다.
전체 cold를 다시 실행하지 않았다.

중요한 timing 경계 차이가 있다. 같은 server monotonic trace에서 마지막 객체 응답은
첫 관측 요청 시작 후 **2,388.495초**, 마지막 terminal manifest는 **2,388.956초**다.
client E3 publication 완료는2,624.557초, E4 전체 digest 포함 cold는2,637.065초다.
따라서2,637초 전부를 E2 transfer 시간으로 부르면 안 된다.
E2 terminal은 세 번째 lease 종료보다 약311초 앞섰다. E3 완료는 약75초 앞섰지만,
§16의 이미 완전 취득한 bytes 무결성과 E3 현재 ticket 권한은 별개의 조건이다.

## 06. 실패한 100k 기준선

ledger100,000/전체100,035행, V400,532/E400,528/depth23,
canonical261,543,083B다. client cold2,700.166286초 후 `OBSERVATION_EXPIRED`다.
외부 guard 종료가 아니며 E3/E4/one-row delta는 실행되지 않았다.
294,624개 객체/207,943,893 canonical B가 실제 E1에 삽입됐고105,908개가 남았다.
최종 DB500,199,424B, metadata246,545,216B/stages3/FK오류0,
accepted current/previous=null/sequence0, generations/root pins0이었다.
원 fresh-process 보고서도294,624개/stages3 healthy 및 accepted=null을 기록한다.
이것은 완전한 100k read 또는 효율적인 resume의 성공 증거가 아니다.

## 07. 원 100k 관측 timeline

|관측 ID|validated → expires (UTC)|새 객체|object 요청 200 / 410|첫 새 요청 전 간격|
|---|---|---:|---:|---:|
|29aeb31a-cfde-48e2-ae90-5192c848518c|05:33:33 →05:48:33|101,472|1,653 /1|0.079932초|
|a15f8b08-2958-4b25-94fe-37cd32503cf0|05:48:33 →06:03:33|102,400|1,600 /1|114.228381초|
|4a206a9a-75de-4f14-a6b4-94c516515f38|06:03:33 →06:18:33|90,752|1,418 /1|207.177805초|

날짜는2026-10-19다. 세 Target sync_root는 모두
`fa612999ce572d8ba613589550d7282fca6d587748f1eae64efc6846ecb384e9`다.
lease는 available부터 fixed900초이며 object 요청으로 연장되지 않는다.
410 body는 `error.code=OBSERVATION_EXPIRED`, `action=new_observation`,
`current_ns=null`, `retry_after_ms=null`이다.
원 요청·오류는 `docs/benchmarks/t66f-b02-a01-correction/http-100000-server-{requests.jsonl,http-failures.json}.gz`에 있다.
재집계는 [analyze_traces.py](benchmarks/t66f-b02-a02/analyze_traces.py),
[trace-analysis.json](benchmarks/t66f-b02-a02/trace-analysis.json)으로 재현한다.

## 08. 관측별 유용한 진척

|N/관측|새 객체|응답 entity B|decoded canonical B|
|---|---:|---:|---:|
|50k/1|81,751|106,190,145|70,774,424|
|50k/2|80,064|65,453,279|40,409,531|
|50k/3|38,516|31,603,909|19,526,637|
|100k/1|101,472|161,825,749|110,348,264|
|100k/2|102,400|83,801,264|51,737,889|
|100k/3|90,752|74,275,554|45,857,740|

100k 총 response entity319,902,567B는 object error body도 포함한다.
전체 요청 entity384,953,287B이며 반복된 root-to-object path 문자열도 비용이다.
관측 간 중복 객체 전송은0이다. 첫 관측은 큰 raw leaves도 취득하므로 tail index
객체만 전송하는 후속 관측과 객체당 bytes/CPU가 다르다. 총량을3으로 나누지 않았다.

## 09. D3c 잔여 요청 고정비

**INDEPENDENT MEASUREMENT — 기존 native timer 재집계:** 100k object handler의
직접 경과시간 합은1,784.164초다. 실제 max active1이므로 요청끼리는 중첩되지 않는다.

|서로 중첩하지 않는 scope|관측1|관측2|관측3|합계|
|---|---:|---:|---:|---:|
|RetentionSandbox.connect|114.520|115.163|100.559|330.242초|
|ObservationRepository._lookup|309.210|316.933|274.822|900.965초|
|PathResolver.resolve|218.395|146.409|126.993|491.797초|
|나머지 handler|21.351|21.231|18.579|61.160초|

아래는 **중첩된** 진단 timer이므로 위 표에 더하면 안 된다.
versions()185.703초, current schema304.904초, _view_object343.043초다.
매 object HTTP 요청은 credential/transfer/terminal의3 connections, _lookup2회,
versions2회, hot/control _view_object4회를 수행한다.
`http.py:134,170`, `observation.py:89,353,515`, `retention_schema.py:217`가 근거다.

|작업|분류|
|---|---|
|body parsing/auth/lease/identity/permit/최종 guard|요청당; 일부 입력 bytes당|
|connect/schema/metadata/Versions|요청·connection·transaction당|
|request-local typed prefix|서로 다른 prefix/context당|
|terminal object hash/C1/shape|반환 객체·bytes당, 반복 요청도 그대로|
|base64/response encode|응답 bytes·객체당|
|COMMIT/close/cleanup|transaction·요청당|

## 10. Prefix cache 효과

100k prefix hits4,817,684/validations461,537, resolver reads756,161이다.
**294,624 terminal reads +461,537 prefix reads =756,161**로 서로 맞는다.
최대131 entries/67,666 canonical charged B로32,768 entries/1MiB 한도보다 작다.
capacity 압박이 병목이라는 증거가 없다. eviction 자체의 별도 counter는 없으므로
실측 eviction 숫자를 만들지 않는다. cache는 요청·private transaction 안에서 폐기된다.
terminal 검증, typed edge/context/descriptor와 취소·transaction-change guard는 유지됐다.
이 cache가 성공적이라는 사실은 _lookup의 별도 C1/metadata 작업까지 제거됐다는 뜻이 아니다.

## 11. 실제 packet 충전

100k 성공4,671 packets 중4,596개가64 items다(약98.39%). 전체 평균은 약63.075,
median/p95는 모두64다. 관측2/3의 성공 packet은 **전부64개**다.
초기 underfill75개에는 raw leaf의 byte cap 및 부모를 먼저 얻어야 하는 dependency에
부합하는 모양이 있다. 원 trace에 stop-reason이 없어 각 packet의 정확한 원인을
소급 단정하지 않는다. 그러나 tail scheduler를 더 채워 큰 개선을 얻는다는 주장은 근거가 없다.
서버 객체 응답은 no partial success이며 기존64/1MiB를 유지했다.

## 12. Request-size 민감도

새 [request_cost.py](benchmarks/t66f-b02-a02/request_cost.py)는 실제
RetentionSandbox→auth→ASGI handler→typed resolver→terminal을 사용한다.
TCP/TLS는 제외된다. seed1k/5k의 실제 graph는4,132/20,148 objects다.
shared DFS prefix와 넓게 흩어진 prefix, items1/8/32/64를 각각 warmup 뒤
untraced/traced/untraced/traced로 실행해64개 측정 응답을 얻었다.

|fixture/shape|1 item median|64 items median|64 items SELECT/요청(계측 표본)|
|---|---:|---:|---:|
|1k/shared|0.261초|0.304초|275|
|1k/spread|0.274초|0.509초|601|
|5k/shared|0.252초|0.302초|277|
|5k/spread|0.237초|0.503초|760|

median은 각 조건 untraced2회다. 작은 표본에서 의미 있는 p95를 주장하지 않는다.
packet64는1개에 비해 고정비를 상각하지만, spread paths의 marginal prefix 작업은 커진다.
최대 object bytes·response cap·cancellation latency·error retry 증폭의 절충도 남는다.
현재 count 한도를 넘는 packet은 시험하지 않았고 권고하지 않는다.
작은 N 두 개만으로 metadata 전체 규모와 무관한 상수를 증명하지는 않는다.

## 13. E2 관측 갱신 제어 흐름

**SOURCE-LEVEL BEHAVIOR:** `fetch.dart:273`의 observation loop 안에서
새 stage, `_VerificationFrontier(:286)`, `verifyAcquisitionGraph(:305)`를 만든다.
410/new_observation은`:406`에서 stage를 interrupted로 기록하고 release한 뒤
nonce/resume/stage를 초기화한다. 다음 반복은 root부터 새 verifier다.
`graph.dart:181`의 seen/visiting 및 완성 subtree summary도 새로 만들어진다.
E1 bytes는 남지만 frontier/DFS 위치/이번 부분 graph 결과는 다음 관측으로 전달되지 않는다.
완전 graph 뒤의 terminal same-nonce manifest와 원 AppState/E3 ticket 검사는 별도다.

## 14. 반복 graph 순회

100k는 E3에 도달하지 않았고 graph_nodes_examined599,176회다.
294,624개만 새로 저장됐으므로 이 둘의 차304,552회는 새 immutable 저장만으로
설명할 수 없는 방문이다. lookahead와 미완성 ancestor 때문에 관측별 cached 객체 수와
방문 수를 정확히 같다고 단정하지 않는다. source의 root 재시작과 소형 실험이 반복을 확인한다.
갱신2/3의 첫 새 요청 전321.406초는 **server manifest 완료→다음 요청 도착** 경계다.
순수 Dart CPU/SQL 시간이 아니라 staging·검증·event-loop 등 local interval의 직접 하한 증거다.
완전한 client 함수별 exclusive CPU 분할은 원 trace에 없다.

## 15. Cached 검증과 SQLite reads

E1 `_read(store.dart:431)`는 size/body/edges SELECT 및 실제
VerifiedObject.verify를 수행한다. `_coldProgress(fetch.dart:621)`는 staging membership을
조회하고64/1MiB cached progress batch를 다시 commit하면서 `_read`한다.
100k store counter는 object reads1,199,415, verified_bytes960,490,674다.
이 숫자는 구현 counter이며 SQL trace나 전층 logical validate bytes로 바꾸어 부르지 않는다.
source상 성공 _read마다 object 관련 SELECT 최소3회가 있으나 그 계산도 실측 SQL 합계가 아니다.
E1 actual insert는294,624회로 중복 삽입이 아니라 반복 **읽기·검증·progress**가 핵심이다.

## 16. Cursor 수명 교정

현재 `_parents`는 실제 DFS ancestor이고 `_strictAncestor`가 false인 순간
`:695`에서 pop한다. `_cursors`는 별도 bounded lookahead다.
이전 실패 revision처럼 cached-only walk의 모든 parent를 enqueue하지 않는다.
현재 소형 renewal과 기존 compact counterexample/cached-parent 회귀가 통과했다.
따라서 남은 비용은 보존해야 할 cursor 수명 교정의 회귀로 보이지 않는다.
경로 위치, immutable 검증 결과, 현재 publication authority를 같은 개념으로 취급하지 않는다.

## 17. 관측 간 재사용 가능성

|상태|현 계약상 취급|
|---|---|
|완성된 E1 bytes/typed Ref|fresh NS/versions/정확한 Ref 아래 재사용 가능; 현행도 재전송 안 함|
|현재 active call에서 검증한 immutable 구조|§15.3/16의 explicit Ref 재사용 및 §24 session integrity 아래 제한적인 진척 보존 후보|
|부분 graph의 visiting node/미완성 parent|완전 subtree 또는 전체 closure로 승격 불가|
|완전 accepted provenance|소유 store의 freshness/data_version·현재 context 아래 기존 E3 규칙으로 재사용|
|observation ID/nonce/lease/session ticket|새 관측의 권한으로 재사용 불가|
|이전 E3 receipt|새 요청의 설치 권한이 아님|
|process restart의 메모리 cursor|재사용 불가; 기존 durable objects/full recovery 경로|

권고는 오래된 receipt를 새 권한으로 사용하는 것이 아니라 **같은 active operation의
중단되지 않은 검증 위치**를 정확한 동일 Target 확인 뒤 이어가는 것이다.
unknown data_version 변경·store reopen·validator 변경 시에는 계속 재사용하지 않는다.

## 18. Generation 변경 안전성

A가G1/B가G2이면 B manifest를 fresh 인증·cache namespace·versions로 검증한다.
G1의 완성 immutable Ref가G2에도 정확히 나타나면 bytes 재사용은 가능하다.
그러나 G1 root/DFS 위치/summary closure를G2 전체 proof로 가져오지 않는다.
**권고의 가장 작은 규칙은 Target 한 byte라도 다르면 현재 방식으로 root 재시작**이다.
G2에서 도달하지 않는 G1 객체는 unreferenced staging일 수 있으나 accepted membership는 아니다.
이번 기존 `renew_different` 회귀는 거부·미게시·reopen을 확인했으며,
미구현 최적화의 changed-generation 안전성을 이미 입증한 것은 아니다.

## 19. E1 write와 batch

현재64 entries/1MiB bounded object+edges+progress transaction은 유지됐다.
동일 객체 immutable conflict 검사·새 bytes verify·readback, schema와 trigger 기반 usage 검사를 수행한다.
E1 transaction9,565회, 새 insert294,624회다. 이를 객체별 단독 transaction294,624회로 부르면 안 된다.
성공 object packets4,671회보다 많은 나머지 transaction은 cached progress 및 stage/bookkeeping를 포함한다.
원 100k trace에는 client SQL/COMMIT별 시간이 없어 E1 전체 쓰기 시간을 정밀 분리하지 않는다.
소형1k 대조81 commits→중간 renewal118 commits, COMMIT 경계 합 median0.461→0.564초였다.
이는 before_commit→after_commit 경계이며 전체 batch 검증·write 시간의 합이 아니다.
E1 저장 구조·batch size·journal mode 재설계를 권할 증거는 없다.

## 20. 전체 critical path

100k wall2,700.166초 중 object ASGI handler1,784.164초(약66.1%)와
갱신 뒤 두 local interval321.406초는 시간축상 분리된다.
그 차이 약594.596초는 object response 처리·packet 생성·local E1/E2 작업·관측/해제 등이다.
이를 순수 network나 SQLite write로 이름 붙이지 않는다.
클라이언트는 packet response→검증/저장→다음 packet의 유한 backpressure를 유지하고,
그 동안 server lease clock은 계속 간다. 겹치는 timer 합산으로100% 분해를 만들지 않았다.

permit acquire 전체0.06586초, executor 시작 대기1.256초,
BEGIN 전체0.13708초로 lock/permit queue가 주원인이라는 증거가 없다.
100k에는 저장된 ASGI410 외 다른 HTTP 오류가 없다. 미도달 native 시도/대기·실패는
독립 client attempt trace가 없어0이라고 소급 확정하지 않는다.

## 21. 처리량·완료 모델

[completion-model.json](benchmarks/t66f-b02-a02/completion-model.json)은 **MODEL-BASED ESTIMATE**다.
마지막 관측에서 new object당 약7.63ms, handler당 약5.74ms를 관측했다.
첫 raw-heavy 추가 비용과 cached 진척량에 비례하는 renewal gap을 따로 두었다.
교정 전 모델은 약295,097개로 실제294,624개에 가깝지만 이는 관측값으로 보정한
설명 모델이지 외부 검증 또는 일반 복잡도 증명이 아니다.

|기존3×900초에서의 가정|모델 결과|
|---|---|
|현재 그대로|약105,435개 부족; 실제105,908개 부족|
|재순회 gap만 제거|약63,270개 부족|
|중복 C1 제거 효과25%만 적용|약47,039개 부족|
|같은 Target 재순회 제거 + handler25% 감소|약2,608.65초에400,532개|
|같은 Target 재순회 제거 + handler28% 감소|약2,539.72초에400,532개|
|같은 Target 재순회 제거 + handler20% 감소|여전히 약3,626개 부족|

25~28%는 소형 요청의 실제 중복 encode 시간 점유율과 비슷하지만 새 구현의 speedup을
실측한 값이 아니다. CPU 주파수/metadata/path/진척 위치/guard·stage 추가 비용이 달라질 수 있다.
E2 terminal 뒤 E3/E4 약정은 모델 밖이다. **실제100k 성공으로 인용할 수 없다.**
한쪽 교정만으로 충분하다는 직접 근거는 없고, 두 변경의 한정 검증을 시작할 근거는 있다.

## 22. 독립 요청 비용 실험

[request-cost.json](benchmarks/t66f-b02-a02/request-cost.json)과
[codec-cost.json](benchmarks/t66f-b02-a02/codec-cost.json)에 원 samples/counters/profile이 있다.
실제 authorized terminal bytes를 독립 SQLite graph/hash oracle와 base64로 대조했다.
각 fixture에서 wrong root422 뒤 정상 요청200도 확인했다.
새 codec 실험8회는 실제 ASGI 요청에서 caller별 encode 작업만 계수했다.

`canonical.py:131`의 decode_json이 full nested validation을 위해 encode(value)를 호출하고,
`:146`의 decode_c1이 같은 value를 canonical equality 비교용으로 다시 encode한다.
2회 모두 동일 encoder이며 사이에 value를 바꾸는 동작은 없다.
64-item shared/spread 표본에서 첫 **inner C1** encode는 handler의 약24.3~27.5%,
median26.54%였다. Outer HTTP JSON의 필수 validation encode는 별도로 계수해 제거 후보에서 제외했다.
cProfile에서도 encode/emit·decode_c1/Object.body가 상위 native CPU work였다.
프로파일이 더 느리므로 그 총 시간을 production latency로 쓰지 않았다.

## 23. 독립 renewal 비용 실험

[renewal_cost.dart](benchmarks/t66f-b02-a02/renewal_cost.dart)는 실제 E1/E2를 사용한다.
backend-produced fixture bytes와 controlled410 transport를 사용하므로 **real HTTP 통합 증거가 아니다**.
제품 TTL을 바꾸지 않고 약절반 durable 진행 후 한 번410을 주입했다.
N0/200/1000의 V126/926/4130에서 대조·renewal 각2회, 총12회 완료했다.
모든 최종 object hash 집합이 독립 fixture closure와 같고 insert/fault count도 정확했다.
accepted=null/FK0을 직접 SQLite로 확인했다.

|V|갱신 시 durable|대조 object reads|갱신 object reads|graph nodes 대조→갱신|갱신 뒤 첫 새 요청 전 median|
|---:|---:|---:|---:|---|---:|
|126|68|252|388|126→145|0.062초|
|926|524|1,852|2,900|926→1,188|0.328초|
|4,130|2,128|8,260|12,516|4,130→5,950|1.457초|

V4130 elapsed median5.673→7.148초, transfer/actual insert는 두 경우 모두4,130개였다.
이는 bytes 재사용 성공과 반복 graph/local validation 비용이 동시에 존재함을 보여준다.
work counter는 구현 측 counter임을 유지하고, 직접 elapsed/fault/durable closure로 교차확인했다.

## 24. 계측 교란·환경·한계

OS/CPU/runtime/메모리·디스크는 [environment.json](benchmarks/t66f-b02-a02/environment.json)에 있다.
Linux x86_64/i7-8750H12 logical CPUs, RAM약23GiB/available약21GiB,
시작 여유 disk약36GiB, Python3.12.3/SQLite3.45.1, Dart3.13.3,
실제 Dart SQLite3.53.4다. host 합성 측정이며 Android 측정이 아니다.
100k 원 실행 active 파일은 다른 synthetic regression PID가 없음을 기록한다.
50k는 full regression과 중첩됐으므로50k/100k CPU 차이를 순수 N 효과로 단정하지 않는다.
이번 소형 실험 일부는 서로 시간적으로 겹칠 수 있어 독점 host 처리량 보장이 아니다.

요청 실험은 aggregate perf_counter_ns/thread_time_ns로 기록했다. counter/timer on/off median
ratio의 전체 median은1.0163이다. 조건별2회뿐이라 tail 변동이 크고 정확한 overhead 상한은 아니다.
codec on/off median 차이는 shared 약9%, spread 약6%다. trace는 새 await를 넣지 않는다.
기존 대형 서버 timer는 inclusive이며 postprocess 시간도 별도로 보존되어 있다.

Dart VM mirrors로 실제 store connection을 읽어 native trace 등록을 시도했으나 현재 native
library가 `sqlite3_sql` symbol을 export하지 않았다. `OMIT_TRACE` compile flag는 관측되지 않았다.
다른 SQLite library를 연결하거나 제품을 변경하지 않고 그 계측을 포기했다.
따라서 client independent SQL profile은 **미측정**이다.
두 harness compile 오류 및 이 runtime 제한은 별도 로그로 보존했다.
처음 중간 N4000 시도도 기존 bridge의 지원 범위0..1000 assert에서 종료됐고
제품 실패로 세지 않았다. 이후 지원되는 N0/200/1000만 사용했다.
64+8 요청과12 renewal의 유한 campaign 뒤 큰50k/100k를 재실행하지 않았다.
실제 diagnostic regression에는600초, npm에는300초 외부 guard를 사용했다.

## 25. 주된 잔여 병목

**F-B02-A02-I01 / INFORMATIONAL:** 요청마다 반복하는 C1/metadata 처리다.
위치: canonical.py:131–150, observation.py:515, http.py:170.
계약 §7/15/16은 full strict validation과 최종 guard를 요구하지만 같은 value의 동일 C1
인코딩을2번 하도록 요구하지 않는다. 실제64-item HTTP/SQLite oracle 및 caller timer로 재현했다.
예상은 canonical·오류 의미 보존, 실제는 동등한 encoder가2회 실행되는 것이다.
영향은 유한 lease 안의 처리량이며 금융 오계산·불완전 graph 승인 결함은 확인하지 않았다.
최소 권고는 validation/strict canonical comparison에 하나의 encode 결과를 쓰는 내부 경로 분리다.
이 finding 자체를 MEDIUM correctness violation으로 승격하지 않는다.
100k 필수 완료 gate는 여전히 열려 있고 향후 교정은 재감사해야 한다.

## 26. 두 번째 잔여 병목

**F-B02-A02-I02 / INFORMATIONAL:** 같은 Target라도 fresh observation마다 private
graph/seen/frontier를 잃고 cached read/validation/progress를 반복한다.
위치 fetch.dart:273–417, graph.dart:181 이후 visit loop.
§15.3/16/24의 Ref/NS/fresh-authority 조건을 유지한 active-call 위치 재사용은 조사 가능한 최적화다.
예상은 fresh 권한과 complete closure, 실제는 안전하지만 root 재시작으로321초 이상의
갱신 interval을 소비했다. controlled410/독립 durable closure가 재현 근거다.
최소 권고는 같은 Target에 한정한 in-flight traversal 지속이며 영속 새 receipt가 아니다.
Cold/restart O(N)은 허용되므로 이 반복만으로 I25 위반을 확정하지 않는다.

E1 새 객체 쓰기·실제 typed path marginal work는 필요한 비용이다.
permit/lock/packet 미충전은 주원인으로 확인되지 않았다. client hash 대 SQLite 자체 시간 비율은
**UNCONFIRMED HYPOTHESIS**로 남기며 순위를 확정하지 않는다.

## 27. 교정 대안

|선택|대상·기대 효과|계약·위험|기본 경로·복잡도·개인용 적합성|판단|
|---|---|---|---|---|
|A C1 동일 encode 중복 제거|실측 요청 약26.5%의 중복 후보|같은 parse/encoder/오류 검사 모두 보존; C1 차분 필수|backend codec 호출에 영향, LOW, 새 infrastructure 없음|권고 A1|
|A2 immutable build Versions 재사용|원 trace185.7초의 일부|build descriptor와 auth cache 분리·가변 registry 경계 필요|별도 identity 결정·시험 필요|우선 제외|
|B packet 확대/추가 충전|tail 이미64/64|기존 packet 한도 변경 근거 없음|복잡도 대비 효과 작음|기각|
|C 같은 Target traversal 지속|갱신321초 및 반복 local work 후보|새 관측·Target exact 비교·current session 필수|명시 large cold 경로만, MEDIUM, 기존 store 사용|권고 C1|
|D E1 lookup batching/저장 재설계|client pure SQL 비율 미측정|durability·schema proof 확대|현재 근거 부족|보류|
|E A1+C1을 독립 교정 후 결합|모델에서3×900초 달성 가능성|각각 differential·negative·통합 감사|LOW+MEDIUM; 별도 persistent subsystem 없음|최소 결합안|
|F TTL/attempt 증가·새 protocol|현재 계약과 상충|§16/17 위반 또는 별도 결정|개인용에도 무한 retry 불가|이번 범위 기각|

전역/관측 간 backend prefix cache, 분산 queue, 새 저장 엔진·microservice는 제안하지 않는다.

## 28. 권고 최소 교정

**RECOMMENDED CORRECTION:** A1과 C1을 별도 검증 가능한 두 subchange로 진행한다.
A1은 encoder/JSON 문법·Unicode·money·hash domain을 바꾸지 않고 strict parse 후
canonical encode의 중복 수행만 제거한다. 일반 decode_json의 검증도 그대로 남긴다.
C1은 동일한 active acquisition에서 새 관측의 **Target 전체 exact equality**가 확인될 때만
suspended graph traversal을 계속한다. 새 observation ID/request nonce·manifest·stage는 새것이다.
구조 완료·F(raw)/index·hot/raw·E3/E4 권한 검사를 생략하지 않는다.
실측 개선이 모델보다 작으면 추가 범위 확대 대신 좁은 실험으로 다시 판단한다.

## 29. 제외한 대안

900초/3관측 확대는 binding 계약을 바꾼다. cache count 확대는 현재 peak와 맞지 않는다.
server `_lookup`·schema/actual FD fencing·terminal guard 자체 삭제도 제안하지 않는다.
서로 다른 connection의 auth 결과나 mutable metadata를 그대로 신뢰하는 request-spanning
cache도 이번 최소안에 포함하지 않는다. E1 새 engine/WAL 변경은 근거와 필요성이 없다.

## 30. 개인 단일 사용자 적합성

오래된 개인 이력100k의 드문 cold 비용은 허용하되 routine 한 행 delta에 cold 반복을 추가하면 안 된다.
두 권고는 기존 HTTP/immutable store/async 검증을 활용하며 queue service·신규 DB·영속 cursor가 없다.
normal startup 비용과 default budget은 늘리지 않는다. backend codec 변경은 기본 호출에도
영향을 줄 수 있어 전체 회귀가 필요하다. E2 권고는 현재 명시 large cold branch로 한정한다.
새 protocol·migration·일반 사용자 선택 UI는 필요하지 않다.
새 lifetime 분기 때문에 retry/cancel maintenance 비용은 증가하므로 MEDIUM 복잡도로 평가한다.

## 31. 보안·정확성 제약

C1 exact bytes/Unicode/duplicate keys/int64/REAL money/raw money lexeme·hash/type/domain을 유지한다.
가져온 object-specific 검증과 서버 typed parent 경로를 생략하지 않는다.
900초/관측3/request3/64 objects/1MiB/path512/500k objects/1m edges 및 기존 memory/disk budget을 유지한다.
credential/owner/NS/epoch/Versions/data_version·최종 guard는 매 요구 경계에서 fresh하게 검사한다.
Graph 불완전·잘못된 Ref·storage full·취소면 accepted/legacy를 교체하지 않는다.
Frozen B/J·금액 원문·Snapshot v7/OfflineBaseline v4·sync_root와 v7 fingerprint 구별은 그대로다.

## 32. 향후 정확한 파일·loop 변경 범위

1. `backend/isolated_sync/canonical.py:131–150`: strict parsing과 encode 결과의 내부 경계를 분리한다.
   decode_c1에서 같은 value의 encode1회를 유지하여 canonical equality와 nested admission을 모두 충족한다.
   Object.body cache·금융 알고리즘·typed resolver cache는 변경하지 않는다.
2. `mobile/lib/src/segmented/fetch.dart:253–450,478–797`: packet/observation 갱신의 owner를 하나의
   active cold acquisition에 둔다. 410이 verifier Future를 unwind하기 전에 유한 fresh 관측을 얻는
   경로를 검토한다. 같은 Target이면 DFS/seen/frontier를 유지하고 current observation/stage binding만
   교체한다. Target 변경이면 진행 위치는 버리고 이미 받은 Ref bytes만 기존 경로로 재사용한다.
3. 총 observation budget3을 nested loop마다 새로 부여하면 안 된다. terminal manifest410에서도
   새 관측 검증을 해야 하며 완료되지 않은 graph를 graph_verified로 표시하면 안 된다.
4. 새 stage는 fresh manifest bytes와 반드시 일치해야 한다. 기존 createStaging/recordAcquisition을 사용한다.
   old progress를 새 권한으로 복사하지 않고 root pins·orphan cleanup을 보존한다.
5. oversized object의 부분 chunks를 관측 사이에 자동 합치지 않는다. 만료되면 그 object buffer를 버리고
   같은 Ref라도 새 관측에서 object 전체를 다시 받거나 완전히 검증된 durable object만 재사용한다.
6. E1/E3/E4/graph.dart 변경은 현재 근거로 요구하지 않는다. store 계약 변경이 불가피하면 범위를 넓혀
   구현하기 전에 별도 근거를 제시한다. process restart는 기존 conservative recovery 그대로다.

기존 B02/A01 코드는 유지한다. protocol/migration/server endpoint 변경은 불필요하다.
이 계획은 아직 구현하지 않았으며 기존 불완전 작업의 커밋을 승인하지 않는다.

## 33. 100k cold·delta 검증 계획

A1: 전체 C1 supported/negative/money/Unicode/historical REAL corpus, 기존 strict encoder와 byte/error
차분, raw/index/root consistency 및 실제 D3c 요청별 timer를 확인한다.
C1: 같은 Target에서 packet 중410, graph 완료 후 terminal410, 세 번째 관측 소진,
새G2/raw/context/Versions/NS/principal 변경, invalid manifest·corrupt cached bytes·missing child를 시험한다.
lookup corruption/data_version 변경 시 reuse 중지, 원 cursor16 count 반례와 cached-parent filling도 유지한다.

logout/reauth/token 교체·mutation·new request supersession·offline/cancel/yield·취소 중 renewal,
oversized chunk 중단·SQLITE_FULL·새 stage commit 실패·fresh-process reopen을 확인한다.
이전 valid accepted generation·legacy B/J bytes·pins를 독립 SQLite/파일 oracle로 비교한다.
그 뒤 실제 fixed-H50k 전체 cold/E3/E4/identical0/one-row delta/restart 회귀를1회 실행한다.
100k는 별도 무경쟁 host에서 동일 실제 TLS 경로로 cold400,532 closure/E3/E4 전체 값 digest,
identical0/독립 reachable-set delta/one-row/Frozen retention·fresh restart를 실행한다.
세 observation·server TTL·client object/hashing/write/resource counter를 보존한다.
성공하기 전 B02 COMPLETE 또는 Phase B 재개를 승인하지 않는다.

## 34. Source-lock 영향

현재 guard23개는 실행해 PASS였다. 원 `protected-source.json`과 과거 기대값은 그대로다.
승인된 profile seam 제거 후 원 default SHA 복원 및 새 extension exact SHA를 함께 검사한다.
후속 fetch 변경은 새 extension review와 독립 감사가 필요하며 단순 SHA update로 끝낼 수 없다.
Backend canonical.py 변경도 engine_artifact 입력을 바꾼다. raw/projection/policy bytes/versions와
C1 출력 보존을 검증하고 **새 exact engine artifact 및 제한된 호환 목록의 별도 승인**을 받아야 한다.
기존 두 hash 승인으로 임의 세 번째 hash나 wildcard 허용까지 승인됐다고 해석하지 않는다.
이번에는 어떠한 asset·guard·SHA 기대값도 수정하지 않았다.

## 35. 현재·향후 회귀

**이번 실제 실행:** Flutter packet14+source isolation23+cleanup13 = **50 PASS/0 FAIL/0 SKIP**, CLI0.
Machine의 hidden loading/setup5개를 test 수에 넣지 않았다.
Backend prefix28+B01 원 strict quota1 = **29 PASS**, CLI0/JUnit0 errors/failures,
24.81초, 기존 Starlette/httpx deprecation warning1개다.
명령과 raw machine/JUnit/exit는 새 evidence에 있다.
Frontend npm build, Ruff, compileall, 새 조사 파일 Python/Dart 형식 검사 및 git diff --check도
각각 exit0이었다. analyze/APK build/full suite는 이번에 다시 실행하지 않았다.
원 `assert sorted(r.status_code for r in results) == [201]*4+[429]`는 transfer test:504에서 그대로다.

**이전 구현자 전체 실행을 독립 재집계:** Flutter visible1,578 PASS/2 SKIP/done.success=true,
hidden107개는 제외한다. Backend JUnit2883은1,343 tests+1,540 subtests이며
원 stdout1343 passed/1540 subtests 및 no failures와 맞는다. 이번 full regression은 **NOT RERUN**이다.
현재 backend/Flutter 전체 PASS로 소급 표시하지 않는다.

후속 제품 교정 뒤 full backend/D1–D3c/identity/permits/B01 및 full Flutter/E1–E4/I25/A01/RA01/
Frozen B/J/Snapshot/OfflineBaseline/authority/crash, analyze/build·source locks·format/Ruff/compileall/
diff check를 다시 실행해야 한다. APK 설치·배포·activation은 별도 금지다.

## 36. 독립 targeted 감사 계획

두 subchange의 exact diff를 독립 검토하고 semantic C1 differential과 changed-generation renewal
counterexamples를 구현자 fixture 외 독립 oracle로 재실행한다.
새 reuse가 current observation authorization 또는 E3 receipt로 오인되지 않음을 검사한다.
실제100k bytes·complete closure·F(raw)/index/hot/raw·financial value digest와 typed HTTP/SQL
증거를 대조한다. 모델 예측과 실측 차이를 보고하고 미완료면 PASS를 내리지 않는다.

## 37. 남은 logical-byte accounting

이번 timer/verified_bytes는 이 gate를 닫지 않는다.

|경계|향후 test-only hook과 byte 정의|중복·oracle|
|---|---|---|
|backend canonical/hash_bytes|실제 hash 함수 input domain framing+raw, encode/decode 검증에 처리된 UTF-8 bytes를 호출별 기록|같은 bytes 반복 처리도 합산; hashlib/원 C1 vectors 대조|
|D3 parse/response|request/response entity, base64 decoded object bytes 별도|HTTP ≠hash; wire 길이와 chunk refs 대조|
|E1 VerifiedObject.verify/_read/batch|실제 verify input bytes, SQL BLOB 신규 insert bytes와 metadata write 별도|E2 선행 verify와 E1 readback을 중복 제거하지 말고 layer별 기록; durable BLOB 합계 대조|
|E2 _packet/_fetch/closure|outer decode, object hash/validation, cache read, graph refs를 구분|구현 counter만 독립 증거로 부르지 않음|
|E3 verification/publication|F(raw)/index 처리 bytes, receipt/manifest/pin SQL writes|새 object payload와 pointer metadata를 혼합하지 않음|
|E4 read/handoff|object read/validation, legacy encode·baseline write bytes|Frozen/accepted 읽기와 handoff 경계 분리|

logical write bytes는 DB/WAL file 증가나 physical I/O와 같지 않다.
독립 native SQL 또는 안전한 test-only instrumentation의 한계를 명시해야 한다.

## 38. Android VFS/I/O·전원 손실

§26/38의 실제 Android driver/VFS/pragmas·I/O error·power-loss proof는 여전히 없다.
Host RSS·SQLite·SIGKILL은 이를 대체하지 않는다. 100k partial RSS약563MB를50k 완료/E3/E4
peak약1.55GB와 같은 phase 수치로 비교하지 않는다. 완전100k RSS·Android heap 안전성도 미검증이다.
실기기 절대 latency/performance는 post-T6.6 gate이며 이번 host 모델로 승인하지 않는다.

## 39. R1 경계

§31/33/34의 Large Restore/MW·bounded upload/chunk/hash·backup/atomic receipt·migration/rollback은
별도 R1 책임이다. host cold 최적화로 대신 구현하거나 준비 완료로 선언하지 않는다.
R1 gate CLOSED, general-user segmented Offline 미활성, production activation/배포/APK 설치 없음이다.

## 40. 최종 조사 판정

비용의 두 원인은 source와 독립 측정으로 구분됐다. C1의 동일 encode 중복과 동일 Target의
root 재순회가 실제 줄일 수 있는 작업이다. 기존 보호 기능 삭제나 lease 확장을 필요로 하지 않는
작은 교정안을 제시할 충분한 근거가 있다. **SAFE TO START TARGETED CORRECTION: YES**다.
다만 새 구현에서 모델 효과를 검증할 의무가 있고100k 성공을 보장하거나 승인한 것은 아니다.
새 Critical/High/Medium correctness finding0이며 remaining investigation blocker0이다.
client 순수 SQL/CPU 분할·완전100k resource·logical bytes·Android/R1은 각각 명시된 후속 한계다.
B02 및 Phase B는 계속 INCONCLUSIVE다.

## 41. Artifact·worktree 최종 보존

이번 신규 파일은 이 보고서와 `docs/benchmarks/t66f-b02-a02/`뿐이다.
실행 source의 format 전 사본은 `execution-sources.tgz`, 측정·진단 오류는 원 JSON/log에 있다.
기존 모든 파일 SHA·binary diff·staged logical index·역사 보고서 동일성 및 refs는
[final-preservation.json](benchmarks/t66f-b02-a02/final-preservation.json)에서 확인한다.
새로운 .pyc/build cache는 무시된 test-generated 파일이며 artifact commit 대상이 아니다.
원 미커밋 제품 bytes를 보존했고 commit/push/stage/reset/stash/clean/checkout을 하지 않았다.
최종 worktree는 의도적으로 DIRTY다.

```text
T6.6F-B02-A02 INVESTIGATION:
COMPLETE

STARTING HEAD:
6282c1c3577c42bba9382d786745d583a5d88236

INITIAL WORKTREE:
DIRTY — UNCOMMITTED B02/B02-A01 EXPECTED

FINAL WORKTREE:
DIRTY — ORIGINAL CHANGES PRESERVED

NEW COMMIT:
NONE

PUSH:
NOT PERFORMED

ORIGINAL PRODUCT FILES:
UNCHANGED

ORIGINAL STAGED INDEX:
PRESERVED

BINDING PROTOCOL:
UNCHANGED

SINGLE-USER ASSUMPTION:
APPLIED

N=50K COLD BASELINE:
PASS

N=50K REACHABLE OBJECTS:
200331

N=100K COLD BASELINE:
OBSERVATION_EXPIRED

N=100K REACHABLE OBJECTS:
400532

N=100K DOWNLOADED OBJECTS:
294624

N=100K REMAINING OBJECTS:
105908

N=100K OBSERVATIONS USED:
3

OBSERVATION TTL:
900s

ORIGINAL 100K TRACE:
ANALYZED

PER-OBSERVATION PROGRESS:
MEASURED

D3C PER-REQUEST COST:
MEASURED

D3C PER-OBJECT COST:
PARTIAL

D3C PREFIX CACHE:
EFFECTIVE

D3C METADATA/C1 REPEATED WORK:
QUANTIFIED

E2 PACKET UTILIZATION:
MEASURED

UNDERFILLED PACKET CAUSE:
PARTIAL

OBSERVATION RENEWAL CONTROL FLOW:
VERIFIED

FRONTIER REUSE:
RESTARTED

GRAPH RETRAVERSAL AFTER RENEWAL:
PARTIAL

CACHED OBJECT SQLITE LOOKUPS:
PARTIAL

REPEATED HASH/VALIDATION:
PARTIAL

CURSOR-LIFETIME CORRECTION:
PRESERVED

CROSS-OBSERVATION OBJECT REUSE:
PRESERVED

E1 WRITE COST:
PARTIAL

HTTP TRANSFER COST:
PARTIAL

PIPELINE CRITICAL PATH:
ESTABLISHED

INSTRUMENTATION OVERHEAD:
PARTIAL

REQUEST-COST MICROBENCHMARK:
PASS

RENEWAL-COST MICROBENCHMARK:
PASS

PRIMARY RESIDUAL BOTTLENECK:
요청당 metadata/C1 처리와 동일 value의 중복 canonical encode

SECONDARY RESIDUAL BOTTLENECK:
같은 Target의 관측 갱신 뒤 graph/cached-validation/progress 재순회

REDUNDANT WORK ROOT CAUSE:
CONFIRMED

100K COMPLETION MODEL:
SUPPORTED

PREFERRED MINIMAL CORRECTION:
C1 단일 검증 encode 경로와 fresh 동일 Target 아래 active cold traversal 지속을 별도 교정한다.

BACKEND CHANGE REQUIRED:
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

SQLITE MIGRATION REQUIRED:
NO

DEFAULT USER BEHAVIOR:
PRESERVED

RESOURCE BOUNDS:
PRESERVED

OBSERVATION AUTHORITY:
PRESERVED

NEW CORRECTION SOURCE PATHS:
backend/isolated_sync/canonical.py
mobile/lib/src/segmented/fetch.dart
별도 승인된 exact artifact·extension source-lock 검토 자료

REQUIRED NEW TESTS:
C1 byte/error 차분, 동일·변경 Target renewal, terminal410, 부분 chunk 폐기,
auth/cancel/data_version/storage 실패, 원 cursor 반례, 실제50k/100k cold·delta·restart 및 전체 회귀

SOURCE-LOCK IMPLICATIONS:
DOCUMENTED

CURRENT TARGETED TESTS:
79 PASS — Flutter50 + backend29
0 FAIL
0 SKIP

FULL FLUTTER REGRESSION:
NOT RERUN

FULL BACKEND REGRESSION:
NOT RERUN

PREVIOUS ACCEPTED STATE:
NOT EXERCISED

LEGACY B/PENDING:
NOT EXERCISED

INCOMPLETE GRAPH PUBLICATION:
NONE

T6.6F LOGICAL BYTE ACCOUNTING:
STILL INCOMPLETE

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION GATE:
CLOSED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

REMAINING INVESTIGATION BLOCKERS:
0 — 후속 교정의 실제100k 검증과 세부 미측정 한계는 본문에 별도 기록

SAFE TO START B02-A02 TARGETED CORRECTION:
YES

SAFE TO DECLARE B02 COMPLETE:
NO

SAFE TO RESUME T6.6F PHASE B:
NO

T6.6F PHASE B:
STILL INCONCLUSIVE

SAFE TO START R1:
NO

SAFE FOR GENERAL-USER ACTIVATION:
NO

SAFE TO DEPLOY:
NO

FINAL VERDICT:
T6.6F-B02-A02 INVESTIGATION COMPLETE —
MINIMAL CORRECTION IDENTIFIED

NEXT ACTION:
C1 중복 인코딩 제거와 동일 Target의 안전한 관측 갱신 지속을 각각 한정 교정한 뒤 실제100k cold·delta를 재검증한다.
```
