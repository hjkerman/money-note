# T6.6F-B03-IC01-P01 — 활성 계측 100k 관측 lease 사전 판정

**PREFLIGHT NO-GO — OBSERVER OVERHEAD CORRECTION REQUIRED**

새 전체100k cold 취득은 **0회**다. 실제 전체 실행의 실패나 `OBSERVATION_EXPIRED`를
주장하지 않는다. 한정된 실제100k HTTP와 E1 대조에서 현재 observer 비용이 크게 나타나
전체 실행을 정당화하지 못했다. B03-IC01은 INCOMPLETE, B01/B02는 CLOSED 유지다.

## 1. 시작 저장소 identity

HEAD/local main/origin/main/실제 remote main은 모두
`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이었다.
원 IC01 correction의 의도된 dirty 상태에서 시작했다. branch 전환·reset·stash·clean·rebase는 하지 않았다.

## 2. Dirty worktree inventory

기존 tracked 변경은 `docs/benchmarks/t66f-b03/counters.py`, `server.py`,
`mobile/test/support/logical_cost_sqlite.dart` 세 진단 파일이다. 기존 IC01 신규 tests/report/evidence도
그대로 있었다. 시작 파일2,852개의 SHA, staged/unstaged/untracked 목록 및 전체 시작 patch는
[starting-state.json](../../benchmarks/t66f-b03-ic01-p01/evidence/starting-state.json)에 기록했다.

## 3. Source와 index 보존

P01은 새 진단·검증 파일과 본 보고서만 추가했다. 기존 제품/계측 source·IC01 tests·보고서·역사 증거를
수정하지 않았다. index의 `git ls-files --stage -z` SHA는
`9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`로 동일하다.
원 staged 항목은0개이며 새 stage/commit/push도 없다. 보존 검사는 `inventory.py --check`다.

## 4. IA01–IA07 현재 교정 상태

현재 backend26개·Flutter18개 correction regression을 다시 실행해 PASS를 확인했다.
원 calibration·동시 scope·native hold·overflow 시험도 targeted 묶음에 포함했다.
IA07의 원 실제 cursor 위임은 여전히176/185행을 읽되 stage는 setup이며 제품 generation oracle SQL은0이다.
원 defect-existence backend4/Dart3은 승인된 동결 구현에서만 실행했다. 그 PASS를 현재 정확성으로 바꾸지 않는다.
원 findings의 역사적5 MEDIUM/2 LOW와 독립 FAIL 보고서를 보존했다. 새 회귀로 재개방한 ID는 없다.

## 5. B02 100k 역사 기준선 — 서로 다른 실행

[historical-baselines.json](../../benchmarks/t66f-b03-ic01-p01/evidence/historical-baselines.json)은
두 원 gzip request trace에서 별도로 재구성했다. 새 nonce terminal 확인과 lease renewal을 구분한다.

|실행|cold terminal HTTP|관측1/2/3 새 전송 객체|관측3 마지막 성공 뒤 여유|
|---|---:|---:|---:|
|A02 구현 측|2590.048631초|137120 / 148416 / 114996|110.160초|
|B02 독립 감사|2463.561424초|140256 / 161152 / 99124|236.813초|

두 실행 모두 reachable400532, edges400528, depth23, canonical261543083B다.
독립 실행은 E3 반환2856.089초/E4 전체 oracle2910.719초이고, 구현 실행은2982.185/3009.140초다.
이 local 후처리 시간을 transfer lease 안의 작업으로 합치지 않는다.

## 6. 원 2061개 표본의 의미

hash 순으로 index leaf/node 각1024, snapshot leaf8, 나머지5종 각1을 골랐다.
2344126B이며 cold E1 wall median은1.474117/4.033528초(off/on), 차이는2.559411초,
비율은2.7362배다. raw object의 최초 검증·batch schema/usage 검사·SQL commit·readback을 포함한다.
store open과 stage 생성은 timer 밖, 새 DML observer가 추가로 설치된다면 그 이후 work는 timer 안이다.
동일 객체·새 저장소를 모드별 사용했고 warmup 뒤5쌍이었다. OS cache를 강제로 비우지는 않았다.
전체 pipeline2590초에 이 비율을 곱하지 않았다.

## 7. 대표성과 새 표본

원 표본의 snapshot leaf 비중은 전체보다 높고 평균 객체 크기도 커 대표성은 PARTIAL이다.
새 표본은 index leaf/node 각2048, snapshot leaf4, snapshot node/raw/index/hot/control 각1,
합계 **4105개/2772337B**다. full graph의 약절반씩인 index leaf/node와 약0.1% snapshot leaf를
더 가깝게 맞췄다. 작은 종류는 의도적으로 포함했다. 완전한 확률 표본이라고 하지 않는다.
원 read-only client DB에는 후속 delta 객체까지400630개가 있으므로 초기 cold400532와 구분했다.
객체 hash·NS는 실제 보존 DB에서 가져왔고 원 DB에 쓰지 않았다.

## 8. SQL observer 비용 경계

|경계|빈도·관찰|
|---|---|
|SQL prefix/주석 분류·pending map 복사|각 wrapper SQL call. 별도20k-call microbench로 확인|
|bound TEXT/BLOB 길이 조회|bound parameter별. TEXT code-unit count와 실제 SQL UTF8 write bytes는 별개|
|BEFORE/AFTER TEMP observer|실제 row event별. IGNORE 시도·trigger/cascade UPDATE도 관측|
|SQL 준비·실행·종료|현재 driver의 parameterized execute는 매번 prepare/execute/close|
|owner/savepoint/commit 정산|각 owner·savepoint·transaction; 기존32-owner/32-frame 상한 유지|
|counter aggregation|각 metric update. 고정 category BigInt map이며 객체별 log 아님|
|snapshot|측정 구간 끝의 aggregate 직렬화. 매 객체마다 수행하지 않음|

E1 wrapper는 SQLite trace callback을 설치하지 않는다. TEMP UDF와 SQL delegate를 trace와 혼동하지 않는다.
프로파일 표본에서 cold45845개 SQL/65 transactions가 off/on 동일했고 UDF82254회,
`SqlCosts.add`621974회를 관찰했다. usage UPDATE20553회는 bytes0이지만 관측된 row work다.
금융·metadata byte 작업을 임의 생략하거나 scalar row에 가상 byte를 부여하지 않는다.

## 9. 실제 paired E1 측정

`components_test.dart`는 새 폐기용 store, 동일 객체·batch 순서·원64개/1MiB 상한을 사용한다.
warmup1회 뒤5 alternating pairs, cold 뒤 동일 객체를 null-bytes reuse로 새 stage에 연결했다.
기본 추가 timing delegate를 제거한 별도 실행의 DIRECT OBSERVATION은 다음과 같다.

|작업|off wall median|on wall median|off/on process CPU median|
|---|---:|---:|---:|
|cold E1|2.421558초|7.362457초|2.23 / 6.33초|
|reused E1 stage 연결|1.404854초|2.152303초|1.16 / 1.95초|
|동일 객체의 E2 verification primitive|0.712353초|0.724189초|raw JSON 참고|

cold pair별 차이는 객체당1121.6–1254.1µs였다. 재사용 stage 연결은 전체 E2 cached-read와
동일하지 않으므로 이를 원1,805,249 object reads에 곱하지 않는다.
실제 SQLite count/sum(body)와 committed BLOB bytes2772337B를 정확히 대조했다.
새 표본의 미완료 graph를 accepted로 게시하지 않았다.

## 10. 계측 overhead의 분해와 중첩

별도의 timing delegate 활성 실행에서 cold off/on wall은2.633365/7.159368초,
native SQL inclusive median은1.153662/5.151835초였다. UDF callback body는0.430791초,
`SqlCosts.add` 합계는0.169587초다. add 일부는 callback, 일부는 wrapper와 중첩한다.
이 수치를 모두 더해 overhead라고 하지 않는다. native 구간은 driver prepare·SQLite VDBE·
trigger expression·FFI 진입·callback·I/O를 포함하므로 나머지를 전부 CAST 비용이라고 단정하지 않는다.
profile timer 자체의 영향을 배제하려고 §9의 unprofiled 실행을 최종 모델에 사용했다.

20k-call microbench median은 prefix 분류93.945ms, metric add1.639ms,
160-key pending 복사34.332ms, primitive observe4.430ms였다. snapshot median은약0.1ms 수준이었다.
prefix/cache key나 snapshot만 줄이는 것으로 큰 native 증가분이 해소된다고 주장하지 않는다.

## 11. 관측별 feasibility 모델

각 역사 관측의 실제 productive 시간/새 객체 수에 측정된 cold E1의 pair별 추가 비용만 더했다.
각 관측에 독립적인900초를 적용했고 renewal/setup 예비시간은0으로 둔 낙관적 추정이다.
backend/E2/reused traversal의 추가 비용은 포함하지 않았으며0으로 측정됐다는 뜻이 아니다.

|역사 기준|관측1 예상 처리|관측2 예상 처리|관측3 예상 처리|합계|
|---|---:|---:|---:|---:|
|독립 기준·median pair|118123|132603|114032|364758|
|구현 기준·median pair|115908|123865|111515|351288|

가장 작은 관측 pair overhead를 적용해도 각각368864/355085개로 target400532보다 적다.
이는 **ANALYTICAL ESTIMATE**이지 실제 실패한 관측별 객체 수가 아니다.

## 12. 모델 불확실성

작은 새 E1 DB와 커지는600MiB 이상 full store는 page-cache/I/O 조건이 다르다.
hash 기반 종류별 선택과 실제 DFS packet 순서도 다르며 history별 backend harness 부하도 동일하지 않다.
관측 renewal 후 실제 packet/cache 순서가 바뀔 수 있다. 전체 C1 closure와 E3/E4 후처리는 이 모델에 없다.
이를 숨기거나2700초 하나의 공통 deadline으로 바꾸지 않았다.
제품 store는 DELETE/EXTRA/foreign_keys를 실제 open에서 읽어 검사한다. WAL checkpoint 측정이 아니라
rollback-journal 경로이며 physical write amplification·Android VFS는 미측정이다.

## 13. 명시적 GO/NO-GO

**NO-GO — MEASURED OVERHEAD ALREADY MAKES SUCCESS IMPLAUSIBLE.**

관측별 낙관 모델이 두 역사 기준 모두에서 목표에 못 미치고 실제 TLS overhead도 양수였다.
임의의 허용 overhead %를 새로 정하지 않았다. 현재 source로 한 번의 큰 cold 실행을 소비하는 것보다
동일 byte/counter 의미를 유지하는 observer 비용 교정이 우선이다. 이것은 수학적 불가능성 증명이나
B02 제품 결함 판정이 아니며, 관측 예산의 실제 소진을 재현한 결과도 아니다.

## 14. 전체 실험 횟수와 자원 guard

새 full100k instrumented cold campaign은0회다. 100k backend 하나를 실제 원 seed/bootstrap으로 만든 뒤
최대256 HTTP 요청으로 제한된 packet 실험만 수행했다. full E2.acquire/E3/E4는 호출하지 않았다.
기존8GiB address-space/runner RSS·2GiB free-disk guard,18분 packet-test timeout을 적용했다.
시작 시 약20GiB free disk/약20GiB available memory가 있었고 병렬 큰 benchmark는 없었다.

## 15. 실제 fixture identity

새 폐기용 backend의 oracle는100000 ledger rows,100035 authoritative rows,
400532 objects/400528 edges/depth23/canonical261543083B를 확인했다.
새 NS/epoch/root는 packet-results.json의 실제 Target에 기록했다. 과거 실행의 UUID/hash와 같다고
주장하지 않는다. 원 canonical fixture를 작거나 쉬운 모양으로 바꾸지 않았다.

## 16. 한정 관측 timeline

현재 real-clock observation은2026-10-21T13:02:46Z→13:17:46Z이며 TTL900초다.
index root부터 eligible child만24 packets/1152객체를 발견했고 depth18 이상인64-item packet3개를
같은 순서로 재요청했다. warmup 뒤 모드별15개 packet 표본, 각960 returned objects다.
발견 객체 분포는 index-root1/node906/leaf245라 HTTP shape의 대표성도 PARTIAL이다.
성공 object bytes와 요청/관측 echo·hash·NS를 양쪽에서 엄격히 비교했다.

## 17. 새 전체 관측1 진행

NOT RUN. §5의140256 또는137120은 원 역사 실행 값이다. 현재 전송 객체로 바꾸지 않는다.
새 한정 실험의 progress·request·bytes와 full100k 관측1을 구분한다.

## 18. 새 전체 관측2 진행

NOT RUN. 새 expiry/renewal 실험을 수행하지 않았다. 역사 trace의 두 번째 lease는 원문에 보존한다.

## 19. 새 전체 관측3 진행

NOT RUN. full terminal·전체 E1 durability·E3/E4 PASS를 한정 packet 결과로 선언하지 않는다.

## 20. 실제 HTTP 비용

발견24개와 warmup6개를 제외하고 backend/client 표본의 모드 순서를 정확히 대응시켰다.
모드별15개의 동일64-object packet에서 client HTTP median은291.299→313.939ms,
backend wall은286.588→309.169ms, backend CPU는285.677→308.329ms였다.
backend 시간은 HTTP 안에 포함되므로 합산하지 않는다. raw p50/p95·request/response/decoded bytes는
`packet-results.json`과 `feasibility-model.json`에 있다. TLS framing·physical I/O byte는 아니다.

## 21. E1 SQLite 비용

profiled actual4105-object cold는45845 delegated SQL/65 transactions다.
재사용 stage 연결은17005 SQL/65 transactions이며 INSERT objects 추가는 없었다.
unprofiled raw의 native timing/count0은 NOT INSTRUMENTED를 뜻한다. counter0으로 꾸미지 않는다.
small new store의65개 transaction을 full7930개나 per-observation transaction 수로 직접 환산하지 않는다.
역사 server trace에는 per-observation E1 COMMIT 시점이 없어 전송 객체 수와 durable 수를 동일시하지 않았다.

## 22. E2 validation 비용

§9는 실제 `VerifiedObject.verify` 입력에 대한 bounded primitive 대조다.
실제 packet의 outer C1/base64/typed-object 검증 median은10.416→10.753ms였다.
완전 frontier traversal·same-Target rebind·full closure의 추가 시간은 미측정이다.
추가 hash/parse를 기존 sync 실행에 넣지 않고 독립 calibration 구간으로 분리했다.

## 23. Backend 진단 비용

실제 인증된 D3 경로와 현재 IC01 primitive/connection/worker observer를 사용했다.
모드 선택은 private stdin이며 manifest·금융 row가 계측을 켤 수 없다. 전환 전 native cohort 완료를 검사했다.
각 요청의 collector는 request-local이며61/61개 scope 완료·pending0을 snapshot으로 확인했다.
generation은 이 preflight에서 NOT INSTRUMENTED, observation/transfer는 한정된 실제 work다.
backend global 설치는 packet timer 밖에서 전환해 매 요청 설치 비용을 억지로 넣지 않았다.

## 24. Collector 비용과 최소 교정 제안

현 driver의 parameterized execute는 SQL마다 prepare/execute/close한다. TEMP trigger가 붙으면
그 프로그램 준비 비용도 반복된다. 기존 `CostDatabase.prepare` API로 동일 actual100k index-leaf
payload2048개/1006531B를 넣은 한정 대조는111.443→41.453ms median이었다.
모든 기존 SQL counter map과 실제 row count/sum(body)가 두 경로에서 정확히 같았다.
이 실험은 전체 E1 cache 구현이나 100k speedup proof가 아니다.

**최소 권고**는 진단 `CostDatabase`의 반복 parameterized 단일 SQL에 한정한 connection-local,
유한 prepared-statement 재사용의 후속 교정이다. `_call`·native row observer·모든 byte/accounting 검사는
그대로 유지하고 값/인가/검증 결과를 cache하지 않는다. DDL/schema-change·failure·close에서의
invalidation/정리, bound 초과, reentry, IA01–IA07 동등성과 전체 회귀가 추가 gate다.
P01에서는 기존 API의 대조만 했고 IC01 wrapper나 제품 SQL 호출을 바꾸지 않았다.

## 25. Renewal·인가

새 full renewal은 NOT EXERCISED다. 실제 bounded HTTP는 원 credential/Target 아래 매 요청
인가를 받고 release204를 확인했다. 원 lease를 늘리거나 새 credential을 꾸미지 않았다.
역사 raw에는 첫 두 lease410→fresh observation→동일 root 진행이 존재한다.
현재 targeted 회귀에서 stale/session/expiry·scope·P0 경계를 다시 확인했다.

## 26. Snapshot 완결성

한정 request cohort61개에 대해서는 closure/pending을 확인했다. backend snapshot은 release 이전까지다.
모든 full mandatory stage를 합친 terminal snapshot은 NOT RUN이며 누락 generation/E3/E4를0으로 표시하지 않는다.
E1/validation 표본 counter는 실제 수행 bytes의 부분 측정이고 전체100k counter가 아니다.
fixture/oracle/preflight profiler 작업은 product-stage 비용에 합산하지 않는다.

## 27. 관찰된 종료 실패와 안전 정리

실제100k packet의 counter·canonical/echo assertion 뒤, 서버의 원 `assert not worker.is_alive()`가
실패해 테스트 exit1이었다. 외부 guard 종료나 `OBSERVATION_EXPIRED`가 아니다. 이 FAIL을 보존했다.
살아 있는 client를 닫기 전에 서버 exit/join을 기다린 순서를 고친 별도1k cleanup case는 exit0이었다.
큰 fixture에서 같은 정리를 재검증한 것은 아니므로 원 FAIL을 PASS로 소급 변경하지 않는다.
실패 adapter 원문/SHA를 보존하고 앞으로의 adapter에는 client-close 순서와 별도 result filename을 적용했다.
새 전체100k 실행이나 두 번째 큰 preflight를 자동 반복하지 않았다.

원 packet payload와 runner metadata의 filename 충돌은 관찰 즉시 별도 watcher가 실제 payload를
보존해 해결했다. 최종 재현 source는 result/runner 파일을 분리한다. 최초 컴파일의 Stopwatch API 오류와
최초 microbench 출력 충돌도 raw 실패/receipt에 남겼으며 제품 오류로 전용하지 않는다.

## 28. Fresh-process·기존 state 안전성

이번에 large accepted state를 만든 적은 없다. full100k fresh-process recovery는 NOT EXERCISED다.
기존100k source DB는 read-only였고 새 E1 표본은 publication 권한 없는 acquisition store였다.
한정 E1의 native durable count/payload와 small real-HTTP E3/E4·disabled equivalence는 확인했다.
원 pending B/J를 지우거나 acknowledge/rebase하거나 required pin을 해제한 작업은 없다.

## 29. B01/B02 보존과 targeted 회귀

fresh backend targeted68 PASS, Flutter current43+독립 current11+역사3+boundaries/lineage/source-lock20,
small actualHTTP2 PASS다. 역사적 잘못된 값 assertion7개는 승인한 frozen helper에서만 실행했다.
신규 P01 시나리오는 E1 profile/unprofile·parts·prepare·cleanup5 PASS, 큰 packet cleanup1 FAIL이다.
그 외 초기 실행·반복·직접 값 oracle를 신규 test 수로 더하지 않는다.
B01의 strict quota 및 B02의 profiles·64/1MiB packets·900초/3 observations·E3/E4는 변경하지 않았다.

## 30. Source-lock와 full suite 한계

제품 source·P0 lineage hook·현재/역사 exact SHA artifact는 P01 중 untouched이며 source-lock6개는 PASS다.
기존 IC01 full backend1436 tests/1540 subtests PASS와 Flutter1680 PASS/2 SKIP는 **이전 구현 측 증거**다.
현재 source가 동일하므로 전체 suite를 재실행하지 않았다. 이를 fresh full PASS라고 보고하지 않는다.
P01 신규 source의 Ruff/compileall/analyze/format과 diff whitespace, frontend build는 별도 확인한다.
이 최종 검사는 PASS다. 최초 신규 microbench의 unused import warning은 제거했고 이전 진단 로그를 보존했다.
향후 wrapper 교정이 들어가면 final-source 전체 backend/Flutter 회귀가 다시 필요하다.

## 31. 남은 feasibility blocker

현재 observer로 관측별 full100k 완료를 뒷받침하지 못한다. 오히려 한정 E1 비용과 실제 packet 증가가
전체 실행을 현재 정당화하지 못한다. SQL 준비 재사용의 전체 E1 효과·오류 동등성·정리 비용을 먼저 검증해야 한다.
원 큰 packet cleanup FAIL도 후속 큰 실험 전 반영할 인계 항목이다. 새 financial/canonical correctness 결함이나
B01/B02 재개방으로 분류하지 않는다. Android/VFS/power·full five-point I25·R1은 별도 미완료 의무다.

## 32. 다음 최소 작업

현재 IC01 진단 wrapper에 한정한 bounded prepared-statement 재사용 교정을 별도 작업으로 확정하고,
동일 E1 입력·counter 및 오류 정산 동등성을 먼저 검증한다. 이 권고는 구현 승인이나 독립 감사 PASS가 아니다.
전체 실행을 허용할 새 모델이 나온 뒤에만 기존 한 번의 full100k 실험 예산을 사용할 수 있다.

## 33. Git·최종 판정

**C. PREFLIGHT NO-GO — OBSERVER OVERHEAD CORRECTION REQUIRED**

기존 IC01의 correctness 변경·index·감사 evidence를 보존했고 commit/push는 하지 않았다.
작업 트리는 의도적으로 DIRTY다. IC01은 INCOMPLETE이며 독립 B03 재감사·Phase B grid 재개 승인이 아니다.
R1 activation CLOSED, 일반 사용자 segmented OFFLINE 비활성, 배포·APK 설치·production 접근 없음.

재현 진입점과 기계 집계는 [P01 디렉터리](../../benchmarks/t66f-b03-ic01-p01)를 따른다.
