# T6.6F-B03-IC01-P03 실제 경로·관측 lease 검증

**FAILED — REAL INSTRUMENTED N=100K FULL PATH DID NOT COMPLETE.**
독립 B03 PASS, Phase B 비용 grid PASS 또는 배포 승인을 선언하지 않는다.

## 1. 시작 저장소 식별

HEAD/main/origin/main/실제 remote main은 모두 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이었다.
개발 checkout `/home/hjkerman/codex/money-note`에서만 작업했다. 초기 staged 변경은0개다.
[시작 inventory](../../benchmarks/t66f-b03-ic01-p03/evidence/starting-state.json)에 기존3,116개 파일 SHA,
전체 status·staged/unstaged/untracked 목록·index 파일 SHA 및 entries SHA를 기록했다.

## 2. 기존 IC01/P01/P02 worktree와 index 보존

기존 tracked diff는 진단 wrapper3개, +495/-47이다. 원 IC01/P01/P02 tests/report/raw evidence도
대조 대상으로 보존했다. reset/stash/clean/checkout/rebase/restage를 하지 않았다.
index 파일 SHA는 `d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`이고,
P01/P02의 `ls-files --stage -z` SHA `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`도 유지했다.
P03 추가는 새 test-only driver·fixture 검증·분석·증거·본 보고서다. 관련 없는 기존 변경은 발견하지 않았다.

## 3. P02 최적화 구현 확인

`counters.py`, B03 `server.py`, `mobile/test/support/logical_cost_sqlite.dart` 전체 미커밋 hunk를 읽고
[검토 행렬](../../benchmarks/t66f-b03-ic01-p03/evidence/ic01-p02-source-review.json)로 남겼다.
SQL classifier/savepoint/부분 성공/owner32와 prepared SQL LRU32, reset/rebind, NULL binding 및
종료 finalize를 확인했다. 결과 row cache가 아니다. P03은 이 세 source를 수정하지 않았다.
P02 helper SHA는 `893460abfeecd745094671de2d0f6488d4d1d3757872a7c6d96aeb8a2963e0d8` 그대로다.
**검증한 역사 실측**인 P02 E1 OFF/원 ON/최적 ON 중앙값은2.421673/6.790440/2.914532초다.
이를 현재 전체 D→E 비율로 전용하지 않는다.

## 4. 서로 다른 역사100k 실행

두 원 gzip request trace를 [새로 재집계](../../benchmarks/t66f-b03-ic01-p03/evidence/historical-runs.json)했다.

|실행|terminal HTTP 초|관측1/2/3 새 전송 객체|마지막 전송 후 관측3 잔여 초|
|---|---:|---|---:|
|B02 독립 감사|2463.561424|140256 / 161152 / 99124|236.812961|
|A02 구현|2590.048631|137120 / 148416 / 114996|110.159786|

두 실행을 합치거나 평균내지 않았다. E3/E4 local 후처리는 transfer lease와 구별한다.
원 header·wire oracle·host/JIT/page-cache 조건도 같다고 단정하지 않는다.

## 5. 실제100k fixture 식별

원 B02 seed와11-table raw source를 사용했다. 원 independent G1의 보존 immutable raw 객체를
read-only로 읽어 원 seed의 timestamp만 복원하고, 모든 다른 열과 준비 revision100025를 확인했다.
100,035개 raw 값의 canonical VALUE digest가 원 G1과 정확히 일치한다.
첫 준비 시도의 CURRENT_TIMESTAMP 불일치는 assertion을 완화하지 않고
[원 실패](../../benchmarks/t66f-b03-ic01-p03/evidence/fixture-attempt-1)로 보존했다.
다음 시도의 Flutter HTTP mock 실패도 [별도 보존](../../benchmarks/t66f-b03-ic01-p03/evidence/harness-attempt-2)했다.
두 실패 모두 실제 backend HTTP acquisition0건, 전체 cold 시도0회였다.
기존 B02의 실제 HttpOverrides를 적용한 동일 driver의 작은 TLS/갱신 smoke가 먼저 PASS했다.
각 준비 bootstrap은1156.148210/1042.278052초,최종 bootstrap은1071.393539초였다.
이 구간은 observation 생성 전이며 lease 내 취득 시간에 넣지 않는다.
최종 driver 전체5276.678335초에는 준비·bounded 실험·단일 full 실행이 포함된다.

최종 fixture는100,000 ledger rows,400,532 objects,400,528 edges,depth23,
canonical261,543,083B다. 원 raw 값은 같지만 새 NS/epoch 때문에 root/object hash는 새 identity다.
ON/OFF 사이에는 같은 현재 Target/root를 사용한다. 원 이름의 별도 fixture를 발명하지 않았다.
최종 [fixture](../../benchmarks/t66f-b03-ic01-p03/evidence/fixture.json)와
[원 raw 복원 증거](../../benchmarks/t66f-b03-ic01-p03/evidence/fixture-raw-restoration.json)에 실제 값을 기록했다.

측정 사이의 대기 구간에서 native read-only recursive edge SQL로 크기 census를 따로 수행했다.
제품 hash/parse를 추가하지 않았으며 generation 또는 D3 제품 SQL 계수에 넣지 않았다.
byte-size p95는 전체 객체 census의 분위수이며 runtime p95가 아니다.

|kind|개수|canonical B|min / p50 / p95 / max B|
|---|---:|---:|---|
|raw-root|1|2631|2631 / 2631 / 2631 / 2631|
|index-root|1|398|398 / 398 / 398 / 398|
|hot|1|87364|87364 / 87364 / 87364 / 87364|
|control|1|3178|3178 / 3178 / 3178 / 3178|
|snapshot-leaf|401|59211510|377 / 151684 / 151684 / 152198|
|snapshot-node|14|72232|2518 / 5687 / 5687 / 5687|
|index-node|200056|103763941|507 / 518 / 522 / 536|
|index-leaf|200057|98401829|430 / 501 / 502 / 574|

## 6. ON/OFF 실험 설계

[사전 고정 계획](../../benchmarks/t66f-b03-ic01-p03/plan.json)은24-packet warmup 한 쌍,
160-packet cold prefix3쌍(OFF→ON, ON→OFF, OFF→ON),80-packet renewal 한 쌍이다.
새 client DB를 각 모드마다 만들고, original IncrementalFetcher.largeGraphVerification을 그대로 썼다.
다음 요청 전에 `P03_PREFIX_END`로 중단하며 incomplete graph의 accepted pointer는 항상null이었다.
각 measured prefix의5,920개 hash set·요청 shape·raw body byte 합·work map이 모두 일치했다.
같은 TLS server,token,Target,packet64/1MiB,SQLite 설정과 runtime을 사용했다. OS cache를 강제 flush하지 않았고
반복 순서와 범위를 공개했다. n=3에서 population runtime p95를 만들지 않았다.

## 7. Prefix 대표성

각 measured prefix는5,920개/62,070,354B이며 원 raw snapshot 초기 구간과 후반 index DFS를 포함한다.
raw가 전체보다 크게 가중되므로 전체 대표성은 **PARTIAL**이다. 후반79개의 완전 packet cycle은
5,056개 작은 index 객체를 포함한다. 그 실제 request-start→next-request-start 시간으로 별도 strata를 만들었다.
전체 크기 census와 기존 P02 실제100k 종류별 표본, 이번 소형 full TLS 보정을 함께 참조했다.
큰 client DB/page-cache,후반 graph 위치,hot/control 마지막 전송의 비용은 prefix만으로 확정하지 않는다.

## 8. 실제 HTTP 비용

**직접 실측**은 transport.exchange 호출→완전 reply bytes 수신까지다. backend wall/CPU는 그 안에
포함되므로 다시 더하지 않는다. request/response entity와 canonical object bytes는 서로 다른 열이다.
모드별 중앙값과 실제 pair별 차이는 다음과 같다. 각 cell 단위는 초다.

|구간|OFF 중앙값|ON 중앙값|
|---|---:|---:|
|wall_us|157.788449|153.279051|
|http_us|96.885493|91.012151|
|sql_us|8.201890|7.814633|
|residual_e2_us|52.745872|53.558125|

|pair|ON−OFF 전체|HTTP|SQL|잔여 E2|
|---|---:|---:|---:|---:|
|1|-9.110120|-7.016749|-2.329333|0.235962|
|2|6.310332|4.053048|-0.387257|2.644541|
|3|7.739328|7.148638|-0.212438|0.803128|

모드 중앙값의 차이와 pair 차이 중앙값은 다르다. pair 차이 중앙값은
6.310332초다. 첫 음수 차이를 계측의 일반 speedup으로 해석하지 않는다.
환경/JIT/cache 변동과 유한 표본의 범위를 그대로 남겼다.

## 9. E2 검증 비용

잔여 E2는 acquire wall−HTTP−DB API wall이다. hash/C1/graph traversal/cooperation/encode/control을
포함하므로 순수 parser CPU라고 부르지 않는다. CPU는 process100Hz tick이며 단독 parser CPU는 미측정이다.
시간 구간의 미세한 snapshot/검증 probe·timer truncation도 순수 제품 CPU로 바꾸지 않는다.

## 10. E1 staging 비용

SQL timer는 실제 E1 Database.execute/select 구간이며 native SQL·diagnostic wrapper·callback을 포함한다.
전체 E1의 사전 hash/validation 시간과 같지 않다. stage 소유권은 E2 caller, persistence 소유 경계는
objects/refs/edges/staging 등의 SQL table이다. 이 둘을 E1+E2라는 중복 합계로 더하지 않는다.
매 measured ON에서 object INSERT attempted/effective/committed BLOB은 각각62,070,354B,
effective new rows는5,920으로 별도 native SQLite count/sum(body)와 일치했다.

## 11. SQL observer 시간

TEMP row UDF body 합은 SQL에 포함된 observer 시간의 하한이다. prefix 분류·pending map·settle·
prepare/finalize 비용 전체를 독립 분리한 시간이 아니다. callback별 microsecond truncation이 있고,
full exclusive observer wall과 allocation은 미측정이다. 측정 timer 자체도 ON diagnostic 부하에 포함된다.
미측정을0으로 채우지 않았다. [원 records](../../benchmarks/t66f-b03-ic01-p03/evidence/prefix-results.json)를 보존한다.

## 12. Prepared cache

연결별 managed peak32,측정 prefix별 created40/finalized40,capacity rejection0을 확인했다.
8개 eviction은 종료 누락이 아니다. hit/miss/eviction/finalize는 payload bytes와 구별하며
setup·acquisition·마지막 확인을 포함한 connection lifetime 값임을 명시한다.
caller-owned/uncached transient statement까지 포함한 모든 native handle 상한32를 주장하지 않는다.

## 13. Counter 대조와 overlap

hash는 실제 domain/NUL/byte feed,validation은 primary submitted/completed/failed span,
write는 NEW TEXT UTF8/BLOB attempted/effective/지원된 committed 의미를 유지했다.
반복 hash/read/validation은 실제 수행 횟수대로 계수하고 structural visits는 별도 work다.
동일 object가 hash·parse·persist에 각각 기여할 수 있지만 unique byte 총합으로 합치지 않는다.
SQL bind/statement count/HTTP/entity/file growth/physical I/O도 서로 다르다.
현재 primitive exact calibration과 소형 실제 native SHA/parser witness,큰 prefix의 독립 byte 하한 및
native durable payload를 함께 대조했다. counter 값을 자기 expected oracle로 사용하지 않았다.

## 14. 자원 사용

8GiB backend address-space/runner process-tree RSS guard와2GiB free-disk guard를 유지했다.
초기 MemAvailable은 약21GB,free disk는 약18.3GB였다. collector는 고정 enum/aggregate,
table128/savepoint32/transaction owner32 및 managed statement32를 유지한다.
[host clock/RSS 표본](../../benchmarks/t66f-b03-ic01-p03/evidence/host-clock-samples.jsonl)은
실험 소유 PID만 관찰하고 유한 개수로 끝난다. sampled RSS와 lifetime maxRss/ru_maxrss,
heap/allocation 및 Android memory를 혼동하지 않는다.

## 15. 실제 observation renewal

기존 repository clock injection으로48번째 성공 packet 뒤+901초를 이동시켰다.
900초를 기다린 wall 측정은 아니며,actual HTTP·authorization·SQLite·new manifest·rebind는 생략하지 않았다.
실제410→release204→fresh201→resumed200을 양쪽 모드에서 통과했다. TTL900/최대3은 불변이다.

|직접 실측|OFF|ON|
|---|---:|---:|
|expiry detection 초|0.057840009|0.168215833|
|새 authorized manifest handler 초|0.313987555|0.309934287|
|expiry 요청 시작→재개 요청 시작 초|0.482685183|0.628143142|
|새 manifest 응답→재개 요청 초|0.018387777|0.017992944|

## 16. 관측 간 staged 재사용

각 renewal 실행은800개 객체를 durable하게 보존했고 transfer event 합과 native unique rows가 같았다.
재전송0,같은 exact Target,continuation1,accepted null을 확인했다. 새 관측 전/끝의 실제 누적
hash/validation/SQL/work snapshot은 원 records에 있다. 그 차이에는 재개 뒤 새 객체 처리도 있으므로
이를 renewal만의 exclusive byte로 표기하지 않는다. cached load 횟수 일부는 public failure result에
노출되지 않으며0으로 바꾸지 않는다. 유지된 immutable 객체와 반복 read operation은 구별한다.
소스 rebind는 stage/manifest/작은 progress만 바꾸고 이미 완료한 active DFS proof를 유지한다.
표본 하나로 모든 N에서의 시간 복잡도를 확정하지 않는다.

## 17. 인가·scope 종료

1,194/1,194 backend request scope 완료,pending0,모든 새 client scope close와 native handle finalization을
확인했다. ContextVar/Zone과 원 credential/dataset/epoch/target guards는 그대로다.
소형 overlapping TLS의201/401 독립 byte witness도 새로 PASS했다.
TLS client를 먼저 닫고 원 worker.join(15)/exit0 fence를 유지했다. 원 P01 종료 실패 증거는 삭제하지 않았다.
실제 late worker/rejected dispatch/closed scope는 새 targeted regression으로 확인했다.

## 18. 관측별 feasibility 모델

**실험 추정**이며 실제 전체 실행 결과가 아니다. 원 각 관측의 productive interval과 실제
prefix/index-cycle delta 및 renewal 양의 delta를 각각 적용했다.900초를 각 관측에 독립 적용했고,
2700초의 자유로운 단일 budget으로 계산하지 않았다. E1 비율을 전체시간에 곱하지 않았다.

|역사 기준|민감도|관측1/2/3 예상 capacity|합계|
|---|---|---|---:|
|independent|min|149937 / 170498 / 140974|461409|
|independent|median|133616 / 154563 / 129901|418080|
|independent|max|129979 / 150506 / 127023|407508|
|implementation|min|146274 / 156316 / 137145|439735|
|implementation|median|130868 / 142817 / 126643|400328|
|implementation|max|127428 / 139346 / 123907|390681|

현재 ON의 실제 절대 cycle율만 적용한 별도 capacity 추정은425665/421952/379320개다.
큰 SQLite DB·후반 경로 비용은 직접 확인 전이므로 추정을 성공으로 바꾸지 않는다.

## 19. 모델 불확실성

느린 역사 중앙 모델400,328개는 목표보다204개 적다. 약0.05% 차이는 유한 평균율의
관측 간 재배치·wall 변동보다 작으며,예측 가능한 expiry 증명으로 취급하지 않았다.
역사 양쪽 min/median/max와 현재 절대율의 불리한 표본도 공개했다. late large-store I/O,
E3/E4 local cost,metadata 크기,반복 검증과 header/handler/entity 경계는 별도 제한이다.
모델이 보증하지 못하는 실제 lease 성립 여부는 허용된 한 번의 full experiment로 확인한다.

## 20. 유한 GO 결정

**GO — ONE FULL N=100K INSTRUMENTED RUN IS JUSTIFIED.**
[결정 원문](../../benchmarks/t66f-b03-ic01-p03/evidence/decision.json)은 정확 counter,동일 입력,
실제 renewal,닫힌 scope,유한 host 자원과 양쪽 역사 민감도를 확인했다.
불확실성이 있지만 합법적인3개 관측의 현실적인 완료 경로가 있으며,한 번의 실험을 막을
재현된 lifetime 결함 또는 확정적 lease 소진은 없었다. full client는 새로운 빈 DB,
server clock offset0,TTL900/최대3,기존 retry/packet/profile 그대로다. 자동 재시작은 없다.


## 21. 새 전체 실행 횟수

실제 새 계측100k cold attempt는 **정확히1회**다. `full-attempt.json` 존재 guard,
GO 결정 및 실제 full-only trace가 이를 뒷받침한다. 초기 fixture/mock 준비 실패와
bounded prefix를 full attempt로 바꾸지 않았고, 전체 실행 후 재시작하지 않았다.

## 22. 전체 실행의 실제 증거

[full-result](../../benchmarks/t66f-b03-ic01-p03/evidence/full-result.json),
[독립 재집계](../../benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json),
[실시간 경계](../../benchmarks/t66f-b03-ic01-p03/evidence/full-live-observations.jsonl)와
원 server trace gzip을 보존했다. 전체 elapsed는2699.957907초다.
backend의 전체 cohort total에는 prefix가 섞여 있으므로 `full/관측UUID` group만 별도 합산했다.
클라이언트 header timer,backend handler/ASGI response boundary,TCP 수신 완료는 같은 경계가 아니다.
처리 시간은 겹치므로 stage wall·CPU·SQL·HTTP를 더해 별도의 전체 시간을 만들지 않았다.

## 23. 관측1 실제 결과

실제 생성 `2026-10-22T07:06:30Z`,만료 `2026-10-22T07:21:30Z`,TTL900초다.
요청2,092건,status `{'201': 1, '200': 2089, '410': 1, '204': 1}`,전송 object event
129,376개,다음 실제 client 경계의 누적 durable 객체
129,376개를 기록했다.
request/response entity는168,656,334/184,663,889B다.
처음/마지막 성공 object response 구간은899.136718초,
마지막 backend 성공 응답 경계의 잔여 lease는0.066447초다.
요청 완료 시 native pending 최댓값은0이다.
실제 관측 직전 누적 snapshot과 다음 경계의 primitive/SQL 차이는 full-analysis에 있다.
마지막 경계에는 local E3/E4도 들어갈 수 있어 E2 prefix key로 구별한다.

## 24. 관측2 실제 결과

실제 생성 `2026-10-22T07:21:30Z`,만료 `2026-10-22T07:36:30Z`,TTL900초다.
요청2,159건,status `{'201': 1, '200': 2156, '410': 1, '204': 1}`,전송 object event
137,984개,다음 실제 client 경계의 누적 durable 객체
267,360개를 기록했다.
request/response entity는180,585,879/112,926,568B다.
처음/마지막 성공 object response 구간은899.180198초,
마지막 backend 성공 응답 경계의 잔여 lease는0.175972초다.
요청 완료 시 native pending 최댓값은0이다.
실제 관측 직전 누적 snapshot과 다음 경계의 primitive/SQL 차이는 full-analysis에 있다.
마지막 경계에는 local E3/E4도 들어갈 수 있어 E2 prefix key로 구별한다.

## 25. 관측3 실제 결과

실제 생성 `2026-10-22T07:36:30Z`,만료 `2026-10-22T07:51:30Z`,TTL900초다.
요청2,031건,status `{'201': 1, '200': 2028, '410': 1, '204': 1}`,전송 object event
129,786개,다음 실제 client 경계의 누적 durable 객체
397,146개를 기록했다.
request/response entity는169,819,083/106,218,110B다.
처음/마지막 성공 object response 구간은899.253438초,
마지막 backend 성공 응답 경계의 잔여 lease는0.021590초다.
요청 완료 시 native pending 최댓값은0이다.
실제 관측 직전 누적 snapshot과 다음 경계의 primitive/SQL 차이는 full-analysis에 있다.
마지막 경계에는 local E3/E4도 들어갈 수 있어 E2 prefix key로 구별한다.

## 26. 최종 counter snapshot

native object count/body 합은397,146개/259,743,775B다.
실제 전송 event 합은397,146이고 native unique row와의 차이는
0개다. 이 값은 graph edge visits나 cached reads가 아니다.
SQL API 누적 380.084418초와 observer callback 하한
23.548612초는 포함 관계다.
stage별 hash input·validation submitted/completed span·SQL attempted/effective/committed
TEXT+BLOB payload와 원 key 목록을 full-analysis에 기록했다. 누락 key를 measured zero로 채우지 않았다.
실행하지 않은 legacy/file/recovery 분기를 full100k에서 다시 실행했다고 주장하지 않는다.
그 경계의 소형 실제 보정·기존 targeted test와 실제 full 실행 범위는 분리한다.

## 27. E3 게시와 E4 금융 읽기

accepted pointer 전/후는 `None` / `None`다.
실패 `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)`를 원 stack과 보존했다. E3/E4 미도달 구간은 PASS로 표시하지 않는다.
남은 객체는3,386개다. 기존 cold accepted pointer는 null로 보존됐으며
부분 graph를 게시하지 않았다.
offline baseline·pending B/J 보호 파일의 전/후 checksum은 동일하다.
pending ACK/rebase를 수행하지 않았다. collector closed=True,managed cache
`{'hits': 7799724, 'misses': 41, 'evictions': 9, 'created': 41, 'finalized': 41, 'peakLive': 32, 'capacityRejections': 0}`이고,created/finalized 동수·capacity rejection0을 확인했다.
client sampled peak RSS는695,611,392B,
client lifetime max는695,275,520B,
backend lifetime max는979,402,752B다.
소유 두 process의 동시 RSS 표본 합 peak는1,363,668,992B다.
이것은 Android heap/allocation/VFS/전원 손실 검증이 아니다.

## 28. 실패 분류

전체 실제 시도는 FAIL이다. 오류 원문은 `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)`다.
원인 분류와 지배 구간은 원 trace·counter를 근거로 최종 summary에 기록한다.
prefix의 GO 판단을 사후 INCONCLUSIVE로 바꾸거나 전체 실행을 자동 재시도하지 않았다.

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

## 34. 남은 IC01 blocker와 원인 분리

**실측 분류: OBSERVATION_EXPIRED.** 세 번째 lease를 모두 사용한 시점에
397,146/400,532개(약99.155%)가 durable하며3,386개가 남았다. 이 실행은
`FAILED — REAL INSTRUMENTED N=100K FULL PATH DID NOT COMPLETE`다.
모델의 불확실성을 실제 실패를 숨기는 INCONCLUSIVE 판정으로 사용하지 않는다.

필수 미완료 증거는 고정900초/최대3 관측 아래의 완전한 계측100k 취득,
완전 graph closure,E3 accepted publication,E4 금융 읽기와 최종 E3/E4 cost snapshot이다.
실행된 E2 구간의 primitive/SQL snapshot은 완결됐지만 전체 경로 snapshot은 **PARTIAL**이다.
renewal 전용 client hash/validation byte의 exclusive subdivision도 이번에는 분리하지 못했다.
재시도 중 실제 수행한 작업 자체는 E2 누적 counter에서 빠뜨리지 않았다.

|최종 실제 계수|값|의미|
|---|---:|---|
|E2 object hash 입력|1,228,705,816B|반복 수행한 실제 primitive 입력|
|E2 bookkeeping checksum 입력|10,804,480B|object identity hash와 별도|
|E2 primary validation submitted/completed|각2,346,583,052B|physical memory-read bytes가 아님|
|E2 SQL attempted TEXT+BLOB|453,571,981B|실제 row payload 시도|
|E2 SQL effective TEXT+BLOB|426,961,201B|유효 row payload|
|E2 SQL committed TEXT+BLOB|426,961,201B|지원 SQL transaction 의미의 commit|
|E2 object INSERT committed BLOB|259,743,775B|독립 SQLite sum(length(body))와 일치|
|backend observation hash / validation span|1,047,954 / 1,651,026B|full group만 합산|
|backend transfer hash / validation span|2,280,416,825 / 7,035,079,776B|D3 반복 검증 포함|
|backend generation hash / validation span|765,042,165 / 1,381,404,740B|fixture 생성 별도 scope|
|backend generation attempted / effective / committed TEXT+BLOB|495,172,894 / 490,197,936 / 490,197,936B|oracle SQL 제외|

backend transfer logical write는 attempted/effective19,080B,committed9,540B다.
만료 요청의 되돌린 작업을 committed payload로 승격하지 않았다. 어느 값도 physical I/O가 아니다.

실제 만료 요청 시작→새 관측의 첫 재개 요청 시작은0.621458239초와0.821405336초다.
세 번째410 뒤에는 네 번째 관측을 만들지 않았다. 외부 중단은 NONE,
runner process-tree peak RSS2,014,973,952B로8GiB guard 미만이며 resource failure가 아니다.
원 clock anchor 표본의 offset span은11,721ns다. 표의 UTC 변환과 microsecond 수치는
벽시계가 그 정밀도로 제품에 보장된다는 뜻이 아니다.

전체 크기의 동시 OFF 대조 실행은 없고 역사 두 실행의 host/cache/NS 조건은 같지 않다.
따라서 **계측만이 시간 부족의 유일한 원인이라는 인과관계는 미확정**이다.
이 P03 driver에는 원 P02 counter 외에 SQL execute/select 및 UDF callback별 Stopwatch,
128-request snapshot JSON과1초 RSS timer도 있다. 새 hash/parse/SQL을 추가하지 않았지만
관찰 자체의 CPU·allocation 부하는 포함한다. callback 본체 합23.548612초는 timer 자체
추가 부하의 측정값이 아니다. timer 없는 동일 후반 상태의 대조가 없으므로
이번 실패를 시간 관찰자가 없는 원 P02 ON 모드도 반드시 실패한다는 증명으로 전용하지 않는다.
실제 backend wall 합·client SQL·잔여 E2는 포함/겹침 관계가 있어 단순 합산하지 않는다.
새 instrumentation defect나 제품 authorization/financial defect를 이 결과만으로 발명하지 않는다.

가장 작은 다음 실험은 보존한 후반 staged 상태와 같은 graph에서 동등한 폐기용 store를 사용해
제한된 ON/OFF replay로 backend D3/HTTP,E2,diagnostic SQL 비용을 분리하는 것이다.
새 전체 cold acquisition,TTL 연장,관측 횟수 변경,제품 최적화를 이번 작업에 추가하지 않았다.

## 35. 독립 B03 재감사 준비

IA01–IA07 구현 교정과 P02 cache32는 새 targeted 회귀에서 보존됐지만,
필수100k full-path lease 증거가 실패했으므로 **IC01 INCOMPLETE,재감사 준비 NO**다.
원 IC01 correction 보고서의 미완료 판정을 그대로 보존했다. 독립 B03 PASS를 선언하지 않는다.
phase B five-point fixed-H/D/N grid는 미실행이며 계속 미검증이다.
Android memory/VFS/I/O와 실제 전원 손실,R1 large restore/activation은 별도 미검증/유예다.
제품 segmented sync 활성화와 배포·APK 설치는 수행하지 않았다.

## 36. Commit/push와 원본 보존

사용자 §28에 따라 실패 시 완료 명의 commit과 불완전 제품 push를 하지 않았다.
**COMMIT NONE / PUSH NOT PERFORMED.** 시작 HEAD/main/origin/main과 실제 remote main은
모두 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` 그대로다.
[최종 원본 보존](../../benchmarks/t66f-b03-ic01-p03/evidence/final-preservation.json)은
원3,116개 파일의 변경0개와 원 index SHA/entries SHA 일치를 확인한다.
worktree는 기존 IC01/P01/P02와 새 P03 증거 때문에 **DIRTY — INTENTIONAL**이다.
protocol,protected production source,source-SHA 기대값과 역사 보고서는 변경하지 않았다.

새 P03 분석 코드에 대한 Ruff/compileall와 Python/Dart formatting 및 git diff check는 PASS다.
진단 Dart analyze는 외부 docs 경로의 package 해석 오류를 먼저 기록한 뒤,
원 config의 상대 rootUri를 임시 절대 URI로 해석한 동일 파일 분석에서 No issues를 확인했다.
원 mobile config는 SHA 동일하며 임시 파일을 제거했다. 앱 전체 analyze/build PASS로 바꾸지 않는다.
새 P03 runner의 종료 후 공백 형식 정리 전 실행 원본은 `evidence/executed-run.py`에 보존했고
seal과 대조한다. 측정 의미 또는 기존 계측 source는 바꾸지 않았다.
seal 당시의 offline `model.py`에는 역사 implementation trace에 없는 필드 접근 오류가 있었다.
GO 전에 실제 `new_global_hashes` 합계와 strict5920 assertion을 쓰도록 고친 분석 source SHA도
최종 source review에 별도 공개했다. 실패 log를 남겼으며 실행 중인 HTTP/E2/E1 source 변경이 아니다.
실패했던 옛 offline model source 자체는 별도 archive하지 못했음을 명시한다.

## 37. 최종 판정과 다음 행동

**FAILED — REAL INSTRUMENTED N=100K FULL PATH DID NOT COMPLETE.**
허용된 한 번의 새 전체 실행은 관측3 만료로 끝났다. E3/E4 미도달 상태를
소형 성공이나 모델로 대체하지 않는다. B01/B02와 E4-A01/E4-RA01은 CLOSED를 유지한다.

다음 행동: 보존된 후반 staged 상태에서 제한된 ON/OFF 비용 분리 실험을 별도로 수행한다.



```text
T6.6F-B03-IC01-P03 REAL-PATH LEASE VERIFICATION:
FAILED

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

ORIGINAL IC01 CHANGES:
PRESERVED

P01 EVIDENCE:
PRESERVED

P02 PREPARED-STATEMENT REUSE:
PRESERVED

ORIGINAL GIT INDEX:
PRESERVED

FINAL WORKTREE:
DIRTY — INTENTIONAL

COMMIT:
NONE

PUSH:
NOT PERFORMED

BINDING PROTOCOL:
UNCHANGED

PRODUCT SYNC ALGORITHMS:
UNCHANGED

INSTRUMENTATION DEFAULT:
DISABLED

ACTUAL 100K FIXTURE:
VERIFIED

REACHABLE OBJECTS:
400532

HISTORICAL INDEPENDENT 100K:
2463.561424s

HISTORICAL IMPLEMENTATION 100K:
2590.048631s

P02 E1 OFF:
2.421673s

P02 E1 ORIGINAL ON:
6.790440s

P02 E1 OPTIMIZED ON:
2.914532s

REAL E2→E1 PREFIX PAIRS:
3

PREFIX REPRESENTATIVENESS:
PARTIAL

REAL HTTP ON/OFF COST:
ON 91.012151s / OFF 96.885493s — prefix 중앙값

REAL E2 ON/OFF COST:
ON 53.558125s / OFF 52.745872s — HTTP·SQL 제외 잔여 시간

REAL E1 ON/OFF COST:
ON 7.814633s / OFF 8.201890s — SQL API 포함 시간

SQL OBSERVER COST:
prefix ON 중앙값 0.350724s / full 23.548612s — callback 하한

RENEWAL ON/OFF COST:
ON 0.628143142s / OFF 0.482685183s

STAGED OBJECT REUSE:
PASS

AUTHORIZATION ACROSS RENEWAL:
PASS

HASH COUNTER ACCURACY:
PASS

VALIDATION COUNTER ACCURACY:
PASS

WRITE COUNTER ACCURACY:
PASS

STAGE ATTRIBUTION:
PASS — 실행된 경계

COUNTER SNAPSHOT COMPLETENESS:
FAIL — 전체 E3/E4 미도달

PREPARED STATEMENT CACHE BOUND:
PASS

COLLECTOR CLOSE:
PASS

NATIVE WORKER CLEANUP:
PASS

HOST MEMORY PEAK:
2014973952B — runner process-tree RSS 표본

PER-OBSERVATION LEASE MODEL:
SUPPORTED — 사전 GO 추정; 실제 완료 보장 아님

MODEL UNCERTAINTY:
DOCUMENTED

PREFLIGHT DECISION:
GO

NEW FULL INSTRUMENTED 100K ATTEMPTS:
1

FULL INSTRUMENTED 100K:
FAIL

OBSERVATION TTL:
900s

MAX OBSERVATIONS:
3

OBSERVATION 1:
129376개 전송·저장 후 만료, UTC 07:06:30–07:21:30

OBSERVATION 2:
137984개 추가, 누적 267360개, UTC 07:21:30–07:36:30

OBSERVATION 3:
129786개 추가, 누적 397146개, UTC 07:36:30–07:51:30 만료

FULL GRAPH CLOSURE:
FAIL

E1 DURABLE ACQUISITION:
FAIL — 부분 취득 397146개 영구 저장은 PASS

E3 PUBLICATION:
NOT EXERCISED

E4 FINANCIAL READ:
NOT EXERCISED

FULL HASH BYTE SNAPSHOT:
PARTIAL

FULL VALIDATION BYTE SNAPSHOT:
PARTIAL

FULL LOGICAL WRITE BYTE SNAPSHOT:
PARTIAL

UNATTRIBUTED MANDATORY WORK:
UNKNOWN — 전체 E3/E4 미실행; 실행 경계의 누락은 미발견

COUNTER OVERFLOW:
NONE

IA01–IA07 IMPLEMENTATION CORRECTIONS:
PASS

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

E3 ORIGINAL APPSTATE TICKET:
PRESERVED

E3 FINAL GUARD TO COMMIT:
PASS — 원 source·targeted 회귀; 이번 full은 미도달

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

NEW P03 TARGETED TESTS:
1 PASS
1 FAIL
0 SKIP

FULL BACKEND:
NOT RERUN
역사 P02: 1436 TESTS / 1540 SUBTESTS PASS

FULL FLUTTER:
NOT RERUN
역사 P02: 1690 PASS / 0 FAIL / 2 SKIP

FLUTTER ANALYZE:
NOT RERUN — P03 진단 Dart analyze는 새로 PASS

FLUTTER BUILD:
NOT RERUN

RUFF:
PASS — 새 P03 Python

COMPILEALL:
PASS — 새 P03 Python

GIT DIFF CHECK:
PASS

IC01 IMPLEMENTATION COMPLETION:
INCOMPLETE

SAFE FOR INDEPENDENT B03 RE-AUDIT:
NO

SAFE TO RESUME FIVE-POINT PHASE B COST GRID:
NO — INDEPENDENT B03 RE-AUDIT PENDING

T6.6F PHASE B:
STILL INCONCLUSIVE

BINDING T6.6F EXIT:
NOT SATISFIED

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
FAILED — REAL INSTRUMENTED N=100K FULL PATH DID NOT COMPLETE

NEXT ACTION:
보존된 후반 staged 상태에서 제한된 ON/OFF 비용 분리 실험을 별도로 수행한다.
```
