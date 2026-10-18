# T6.6F-B02 E2 객체 예산·대형 graph 조사

## 01. 시작 identity와 조사 범위

**B02 INVESTIGATION COMPLETE — MINIMAL E2 OBJECT-BUDGET CORRECTION RECOMMENDED**다.
이는 명시적 비활성 검증 profile의 후속 교정 권고이며 대형 Android 지원 승인이 아니다.

시작 HEAD/main/origin/main/실제 remote main은 모두
`c591a7a0d10b208ed0c0e7efd239576f91052c66`였다. 최초 worktree는 clean이었다.
[repository.json](benchmarks/t66f-b02/repository.json)과 기존 전체 tracked SHA를 보존했다.
제품은 마지막 독립 감사 대상 `af9525e20e6df1dd7dfc152d3db79c1eb07925d2`와 같다.
운영 DB/API/credential/service에는 접근하지 않았다. 모든 실험은 합성·disposable HOST 조사다.
제품·protocol·기존 테스트·역사 보고서는 수정하지 않았다.

## 02. Phase B의 현재 경계

[원 Phase B](t66f-phase-b-independent-verification.md), [B01 독립 검증](t66f-b01-independent-validation.md),
[후속 Phase B](t66f-phase-b-continuation.md)의 역사적 FAIL/INCONCLUSIVE는 그대로다.
이전 backend 5개 N의 측정, 지원 client 세 N의 interop, 전체 backend 1315/1540 및 Flutter
1503 PASS/2 SKIP는 **이전 독립 증거**다. 이번 결과로 새 full-suite PASS라고 부르지 않는다.
B01 및 E4-A01/RA01 closure를 다시 OPEN으로 바꾸는 제품 변경은 없다.

이 조사는 큰 두 N의 지원 차이와 자원·최소 변경안을 설명한다. F 전체 검증이나 R1 구현을
대신하지 않는다. 아래 **OBSERVED IMPLEMENTATION FACT**, **INDEPENDENT MEASUREMENT**,
**ANALYTICAL ESTIMATE**, **ARCHITECTURAL RECOMMENDATION**, **UNVERIFIED ASSUMPTION**을 구분한다.

## 03. 정확한 E2 limit

**OBSERVED IMPLEMENTATION FACT:** `mobile/lib/src/segmented/fetch.dart:24–54`의
`FetchLimits.graphObjects=100000`, `graphEdges=200000`는 기본값이면서 validate의 hard ceiling이다.
`graphObjects:100001`은 HTTP 전 `FETCH_LIMIT_INVALID`다. E1 `store.dart:20–28`의 별도 기본값은
`objectCount=100000`, `metadataBytes=32MiB`다. E1 설정 API는 양수 objectCount를 받지만,
E2의 hard ceiling을 우회하는 정상 대형 acquisition 경로는 없다. 이번에는 어느 값도 올리지 않았다.

## 04. 계산 대상·scope

`fetch.dart:272–352`는 `min(fetch.graphObjects,store.objectCount)`를 graph validator에 전달한다.
`graph.dart:205–206`은 새로 방문하는 hash 수를, `:260–263`은 재사용한 subtree의 object/edge까지
합한 **전체 target closure**를 검사한다. raw/index/hot/control 및 모든 internal/leaf/root를 포함한다.
manifest에는 total object count가 없다. 서버의 발표 수를 신뢰하는 검사가 아니다.

|수량|현재 의미|
|---|---|
|전체 generation 객체|네 root에서 도달하는 전체 typed immutable graph; 최종 cap 대상|
|delta 전송 객체|missing인 신규 bytes; 전체 cap과 별개|
|방문·재검증 객체|fresh/cold에서는 전체, 유효 session provenance이면 changed subtree만|
|동시 payload 보유|한 object 조립·검증 copy와 parsed body; 전체 payload 배열은 E2에 없음|
|동시 metadata 보유|O(V+E) summaries/refs; E3는 별도 raw/facts/catalog도 보유|
|E1 objectCount|한 namespace SQLite 안의 모든 객체; staged/orphan/previous/frozen 포함|

동일 hash 재참조는 `seen`으로 재다운로드를 막고 매 edge의 type/membership을 검사한다.
cold graph의 subtree 합이 unique `seen.length`와 다르면 `GRAPH_DUPLICATE_CHILD`다.
한 valid generation의 중복 경로를 무조건 허용해 객체 수를 부풀리는 구조가 아니다.
재시도마다 traversal 상태는 새로 시작하며 별도 session 누적 counter는 없다. durable 객체는 남고,
새 target 전체 및 저장소 전체 예산을 다시 적용한다. unchanged와 delta에도 최종 전체 cap이 적용된다.

## 05. Protocol limit 여부

T6.6C 전체와 §7/8/11/15/18/24/35를 대조했다. **100000 객체 제한은 protocol에 없다.**
§35의 100k는 역사 row N이다. E1 source comment와 구현 보고서 §M은 local configurable
resource policy라고 명시한다. E2 구현 §10/독립 감사 §19도 모든 100k graph가 다른 예산과
무관하게 저장된다고 보장하지 않는다. 분류는 **IMPLEMENTATION**이며 test-harness-only가 아니다.

## 06. 원 안전 근거

Git `141e011`의 최초 E1부터 object100k/metadata32MiB, `69a8fd1`의 최초 E2부터
graph100k/edges200k가 존재한다. 당시 문서·시험은 유한 traversal/HTTP/저장/재시도,
과대 객체·graph·parse·depth 및 SQLite-full 거부를 근거로 한다. 특정 100000 숫자를 도출한
RSS/Android 실측 자료는 발견하지 못했다. 따라서 안전 목적은 확인, **수치의 경험적 근거는 PARTIAL**이다.

count는 memory·hash/parse CPU·HTTP·disk 작업의 거친 대리 한도다. cycle은 별도 visiting 검사,
fan-out은 typed format 검사, integer/count는 별도 parser 검사다. 이 방어들은 정확히 100000이라는
숫자에 의존하지 않지만, 그 사실만으로 전체 count 한도를 없애도 안전하다는 결론은 나오지 않는다.

## 07. 기존 다른 자원 한도와 빈칸

|기존 한도|실제 범위|
|---|---|
|object64MiB / total payload512MiB|객체 조립·저장 및 누적 payload; object bytes와 graph count는 별개|
|metadata32MiB / staging128|행 종류별 논리 charge; 실제 SQLite 파일 크기 아님|
|databasePages262144|측정 page4096 기준1GiB; 공간 부족 시 rollback|
|manifest8MiB, request3MiB, chunk1MiB|HTTP entity·decoded chunk 경계; full graph 크기를 뜻하지 않음|
|path512 / C1 nesting128|graph 경로와 JSON depth 별개|
|acquisition 1/isolate, 순차 object HTTP|다른 isolate/process의 전역 scheduler 보장은 아님|
|request3회, observation3회, delay≤5s|호출별 유한 retry; 무한 성공 retry 없음|
|HTTP 기본15s/허용최대60s, release2s|요청 timeout·cleanup, 전체 수집 deadline 아님|
|server lease900s|현재 terminal observation이 유효해야 함; client가 연장할 권한 없음|

별도 Dart heap/RSS hard quota, 전체 acquisition 전송 bytes의 독립 누적 cap, 전체 verification
wall-time cap은 확인하지 못했다. 총 저장 예산·per-object 한도·유한 traversal/retry가 조합된
방어다. decompression protocol은 도입하지 않았으므로 가상의 decompression cap도 주장하지 않는다.

## 08. H/D/N과 실제 fixture

규범 §35: N=전체 역사 row, H=hot/참조 working set와 required control/policy descriptor 크기,
D=base 이후 changed rows. 의무 N은 1k/5k/10k/50k/100k다. 규범에 숫자 H/D는 없다.
기존 독립 fixture의 seed662602·평가일2026-10-05·current ledger105를 유지하고 N−105 archive를
생성했다. D=1은 id1002의 금액 한 번 변경이다. hot87364B/control3178B 및 다른 table35행이 고정이다.
12k/15k/20k/24900/25000은 경계 조사 보조 지점이며 새 의무 grid를 만든 것이 아니다.
새 UUID는 합성 identity다. 금융 rows는 결정적이고 실행별 manifest·export SHA를 보존한다.
기존 benchmark의 N label은 ledger의 현재+과거 전체 N행이다. 다른35개 참조/control 행도
포함한 실제11-table authoritative rows는50035/100035다. 이를 각각50000/100000 total
authoritative records라고 축소하지 않는다. H에 고정된 참조 행을 포함한 원 fixture를 그대로 쓴다.

## 09. 50k graph

새 실제 backend bootstrap/finalizer/observation과 별도 SHA·typed SQL walker가 **200331 객체,
130710592 canonical bytes**를 확인했다. 원 감사 수치와 같다. ledger50000 외 필수10개 table의
35행을 모두 기록했다. index-leaf100057/index-node100056/index-root1, snapshot-leaf206/
snapshot-node8/raw-root1, hot/control 각1이다. 새 D1은25 객체/256525B, 재사용200306개다.
catalog는200363개였고32개는 reachable closure 밖의 bootstrap 중간 객체였다. E2 count에 섞지 않는다.

## 10. 100k graph

새 재생성은 **400532 객체/261543083B**, ledger100000+기타35행을 확인했다.
index-leaf200057/index-node200056/index-root1, snapshot-leaf401/snapshot-node14/raw-root1,
hot/control 각1이다. depth23/fan-out32/최대 객체152198B이며 50k는22/32/151684B다.
manifest에는 전체 count가 없고 각 root/Ref와 typed descendant에서 독립 도출했다.
G1 catalog400564 중32개는 unreachable이며, D1 신규26개/258047B·재사용400506개,
G1/G2 union400558개다. 실제 HTTP downloads/cache-hit/wire bytes는 이번 큰 두 지점에서
**미측정(null)**이다. readonly verifier 방문100000을 download100000으로 바꾸지 않는다.
table별 actual rows·kind별 bytes·두 Target identity는 [100k 결과](benchmarks/t66f-b02/evidence/100000/result.json)에 있다.

## 11. Amplification

이 fixture의 facts는 PK=N+35, unique=N+4, 나머지 ref/reverse/aggregate/context 등이18개라
F=2N+57이다. SHA fact-key collision은 이 fixture에 없다. canonical Patricia는 leaf F,
branch F−1, root1이므로 **index=2F=4N+114**다. raw B+tree와 hot/control을 더하면 전체 V다.
근거는 `backend/isolated_sync/facts.py:25–43`, `patricia.py:64–100`, T6.6C §10/11이다.

|N|raw-root/leaf/node|index root/leaf/node|hot/control|전체 V/N|
|---|---|---|---|---|
|50000|1/206/8|1/100057/100056|1/1|4.00662|
|100000|1/401/14|1/200057/200056|1/1|4.00532|

큰 수의 대부분은 per-fact canonical index 구조에서 발생한다. 중복 traversal·fixture 행 수 오류가
원인이라는 증거는 없다. graph 모델의 duplicated references는0이다. PK/payment-key fact를 제거하거나
Patricia leaf를 임의 packing하면 structural=1/C1/root identity가 바뀌므로 이번 최소 변경으로 제안하지 않는다.

## 12. Full graph와 delta

|N|전체 G1|D1 신규/재사용|신규 bytes|G1+G2 union|
|---|---|---|---|---|
|1000|4132|17/4115|246769|4149|
|5000|20148|21/20127|251460|20169|
|10000|40170|23/40147|252685|40193|
|12000|48177|23/48154|253178|48200|
|15000|60189|23/60166|254655|60212|
|20000|80210|23/80187|254823|80233|
|24900|99830|24/99806|255505|99854|
|25000|100230|24/100206|255505|100254|
|50000|200331|25/200306|256525|200356|
|100000|400532|26/400506|258047|400558|

큰 두 N의 신규 구성은 hot1/index-root1/index-leaf1/raw-root1/snapshot-node2/snapshot-leaf1과
index-node18/19다. 실제 E2가 G1만 완전히 캐시하고 provenance가 유효하다는 가정에서 새25/26개가
missing frontier다. 이는 실제 download 관찰이 아니라 독립 set 비교다. 기존 graph는 그대로 필요하다.

이는 동일 금융 내용으로 cap을 회피할 수 있다는 뜻이 아니다. E2는 full closure를 증명해야 한다.
이미 verified immutable subtree의 connection-owned provenance를 재사용하는 경로가 E3/I25 교정으로
존재한다. 재사용을 새로 설계하지 말고 유지한다. receipt는 current AppState authorization이 아니다.
새 연결/data_version 변경/손상 시 full fallback을 생략해서는 안 된다.

## 13. 현재 실제 실패 경계

실제 verifier를 기본100000/200000으로 호출한 readonly component 시험은 24900행의99830 객체에서
통과하고 25000행 이상에서 `GRAPH_OBJECT_BUDGET`로 거부했다. 큰 두 N은 실제100000번째 load 후
거부한다. 이는 HTTP download count가 아니라 실제 validator에 전달한 read-only loader count다.
full E2를 이 graph 크기로 통과시켰다고 주장하지 않는다.

독립 작은 graph V4132에서 V−1/V/V+1을 cold와 provenance 재사용 각각 시험했다.
V−1은 모두 거부했고 재사용 거부 때 loader 호출은0이었다. V/V+1은 통과했다. 따라서 cap은 신규
download만의 한도가 아니다. 한도를 올려도 최종 full closure 검사 자체를 삭제하거나 delta count로
바꾸면 안 된다. 실사용 cold에서는 아래 metadata 한도가 graph cap보다 먼저 막을 수 있다.

## 14. 기본 E1의 실제 저장 경계

기본값의 실제 공개 `putVerifiedObject`와 `recordStagedObject`를 합성15k 입력에 적용했다.
**47656개/24084281 payload B**, metadata33554367B에서 `LOCAL_METADATA_BUDGET`로 멈췄다.
걸린 시간은1615.365초다. 이 자체 조사 traversal 순서는 실제 HTTP graph DFS와 다르므로
모든 E2에서 동일한 ordinal로 거부된다고 일반화하지 않는다.

새 연결에는 objects47656/refs47665/edges47661/staging_objects47655가 있었다.
마지막 object put은 COMMIT됐고 그 다음 progress transaction만 rollback됐다. 이는 전체
acquisition rollback이 아니다. 해당 valid object는 retry cache로 남을 수 있지만 staged graph를
complete/accepted로 선언하지 않는다. accepted table 자체가 없는 E1/E2 profile다.
별도 모든 BLOB의 domain SHA·기존 control ref·usage 재계산·FK/integrity 및 새 writer lock 획득을
확인했다. prior legacy/Frozen을 설치한 새 시험이라고 주장하지 않는다. 그 보존은 실행한 기존 회귀 범위다.

core 행 charge는 objects192 + refs128 + edges256 + staged-link128이며 complete forest의
E=V−4다. manifest/root 소액을 제외하면 한 cold staging은 **704V**다. 32MiB는 약47662 객체에서
소진하므로 nominal100k가 실제 기본 저장 가능 용량이라는 해석은 틀리다. 12k의48177 객체부터
완전한 staged graph의 계산 charge가 기본 예산보다 크다. 고정 charge와 physical file bytes를 구별한다.

## 15. 안전한 offline 대형 분석

readonly export는 E1 DB가 아니다. `layout.py`는 별도 core-table/index bulk footprint 모델,
`probe.dart facts`는 실제 공개 F(raw)/Patricia component, `simulation`은 독립 요약 보유 모델이다.
GraphClosure/CompleteGenerationProof/accepted pointer를 조작하지 않는다. products의 object
limit를 높여 실행한 결과도 아니다. typed object 검증은 제품 validator를 공유하고 SHA/도달 집합은
Python 표준 SHA와 기존 독립 child extractor를 사용했다. oracle의 공유 의존성을 숨기지 않는다.

## 16. Host CPU·memory

|N|backend bootstrap wall/CPU s|backend peak MiB|graph component 상태/시간 s/peak MiB|facts component 시간 s/peak MiB|
|---|---|---|---|---|
|1000|5.60/5.58|72.4|PASS/1.97/305.9|0.93/300.4|
|5000|32.41/32.36|106.0|PASS/7.03/313.2|3.67/297.9|
|10000|66.70/66.62|149.7|PASS/12.02/301.1|7.77/304.3|
|12000|80.91/80.82|166.8|PASS/18.92/308.6|10.93/309.3|
|15000|103.13/102.97|191.7|PASS/22.63/318.4|13.77/318.6|
|20000|142.79/142.05|238.5|PASS/29.40/340.3|18.38/332.2|
|24900|164.47/163.45|278.6|PASS/30.09/354.9|21.81/354.6|
|25000|212.08/210.66|279.4|GRAPH_OBJECT_BUDGET/36.15/348.6|21.33/351.8|
|50000|384.62/382.39|497.6|GRAPH_OBJECT_BUDGET/41.28/346.9|45.20/448.2|
|100000|713.63/711.55|933.7|GRAPH_OBJECT_BUDGET/47.06/352.0|76.70/632.7|

graph의 budget 거부는 기대한 안전 거부다. elapsed는 프로세스 기동을 제외한 Stopwatch, peak는
프로세스 전체다. `/usr/bin/time`에는 기동 포함 wall/user/system이 별도로 있다.

|요약+raw+facts 동시 보유 모델|시간 s|peak MiB|
|---|---|---|
|1000|2.50|302.6|
|10000|20.83|332.0|
|50000|116.39|597.2|
|100000|196.50|922.5|

warmup 없는 단회 기술 표본이며 median/p95나 엄격한 heap 상한이 아니다. RSS에는 JIT compiler,
VM·native SQLite가 포함된다. facts component는 index root를 backend target과 exact 비교했다.
simulation의 summary 구조/GC와 실제 E3 `_Summary`/`_RawCatalog`/locations/receipt 공존은 다르다.
이 모델 RSS를 actual E3 전체 peak의 상한 또는 하한이라고 단정하지 않는다. heap snapshot·temporary
allocation volume은 측정하지 못했다. `/usr/bin/time` CPU/peak를 별도로 보존했다.
한 행 변경의 실제 backend finalizer wall/CPU는50k0.954/0.932초,100k0.941/0.903초였다.
이는 observation·HTTP·client를 포함하지 않는 단일 실행이며 end-to-end latency로 합산하지 않는다.

## 17. SQLite·임시 공간·동기화

|N|unique canonical payload B|cold metadata 모델 B|core DB 모델 B|DB pages|
|---|---|---|---|---|
|1000|2749721|2910142|6410240|1565|
|15000|39217312|42374271|91570176|22356|
|50000|130710592|141034239|303841280|74180|
|100000|261543083|281975744|608186368|148483|

모든 모델 integrity/FK는 통과했고 duplicated references는0이다. Backend actual main DB는
50k 394645504B, 100k 789991424B였다.
backend main DB·offline export·모델 DB는 서로 다른 조사 파일이며 모바일 요구 공간으로 합산하지 않는다.
canonical 객체 payload를 base64로 인코딩했을 때의 오프라인 바이트 합은50k174576972B/100k349373964B다.
현 single-item E2와 빈 cache/inline0/객체<1MiB 조건에서는 최초 object 요청이 각각200331/400532개다.
이는 header/framing/retry/observation/release를 제외한 분석 값으로 실제 wire 측정은 아니다.

모델 bulk commit은 product per-object durable transaction latency가 아니다. 실제 E1 1000객체
표본은 put+progress47.153초, existing-stage cache 재확인1.763초, new-stage cache 기록23.604초였다.
같은 기본 DELETE/EXTRA/4096B profile, 예산 확대 없이 측정했다. CPU와 wall을 구분하고 다른 실험의
I/O 경합을 공개한다. 이 비율을400532개에 단순 곱하면 각각 약5.25시간/11.8분/2.63시간이다.
이는 **ANALYTICAL ESTIMATE**이며 실제 대형 HTTP·lease 실패를 재현한 결과가 아니다.

900초 lease와 새 staging의 durable 기록 비용을 무시하면 안 된다. E2는 새 observation 때 새 staging,
전체 closure 재탐색을 하므로 반복 만료의 진행성은 후속 핵심 gate다. timeout/lease를 늘려 안전성을
추정하지 않는다. 기본 E1은 WAL이 아니라 DELETE이므로 해당 store의 WAL 크기는 해당 없음이다.
rollback journal peak/physical write amplification/전체 임시 복사 peak는 미관찰이며 DB 증가를
논리 write bytes로 바꾸지 않는다.

## 18. Android의 전제·한계

문서의 주 검증 기기는 `docs/runbook.md:499`의 Galaxy S23 FE/One UI8.5다. 지원 최소 RAM이나
Dart heap allowance는 문서화돼 있지 않다. Gradle SDK는 Flutter 값에 위임하며 largeHeap 선언도 없다.
특정 device의 RAM·실제 가용 heap을 추측하지 않는다. HOST memory 약23GiB와 Android는 다르다.

Android는 메모리 압박에서 앱을 종료할 수 있다([Android memory 관리](https://developer.android.com/topic/performance/memory/manage-app-memory)).
Flutter DevTools는 heap/external/RSS/GC를 구별한다([공식 Memory view](https://docs.flutter.dev/tools/devtools/memory)).
따라서 cold full build 중 foreground 반응·background suspension·process death·배터리·저장 여유 및
retained Frozen+pending과의 공존은 별도 기기 측정이 필요하다. APK 설치나 기기 시험은 하지 않았다.

## 19. 단일-user 판단

`domain-model.md:17`은 단일-owner·공유 장부를 명시한다. 복수 auth principal 가능성은 여전히 있어
namespace/session fencing을 제거할 이유가 아니다. foreground reads/writes·background sync·pending·
세션 교체·취소·재시작은 한 사람에게도 겹친다.

100k는 수동 입력만의 일상량으로 강제할 수 없지만, 다계좌 import와 장기 보존에서는 배제할 규모도
아니다. 예를 들어20행/일을 가정하면 약13.7년이라는 단순 산술이며 실제 사용 빈도 측정은 아니다.
일상 delta의 수십 신규 객체와 드문 초기400k 객체를 분리한다. cold O(N)은 규범상 허용하지만
예측 불가능한 반복 실패를 허용한다는 뜻은 아니다. 분산 queue·서비스·새 DB·multi-tenant 인프라는 필요 근거가 없다.

## 20. A–H 최종 비교

**ARCHITECTURAL RECOMMENDATION:** 아래는 측정 결과와 향후 검증을 분리한 판단이다.
요청한20개 기준의 각 option별 평가는 [options.json](benchmarks/t66f-b02/options.json)에 있다.

|OPTION|PROTOCOL COMPATIBILITY|50K/100K SUPPORT|RESOURCE SAFETY|CORRECTNESS IMPACT|IMPLEMENTATION COMPLEXITY|SINGLE-USER SUITABILITY|REQUIRED NEW TESTS|RECOMMENDATION|
|---|---|---|---|---|---|---|---|---|
|A 유지|wire 그대로|미지원|현재 fail-closed|완전성 보존, F 미완료|없음|장기 history 해결 안 됨|현재 거부|최종 해법 아님|
|B count만 확대|local이면 호환|다른 예산에 막힘|증명 부족|guard 유지 필요|낮아 보임|불충분|다중 예산|단독 배제|
|C size-aware|local이면 호환|새 정책 검증 필요|세밀할 수 있으나 RAM=count overhead도 필요|새 accounting 검증|중간 이상|현재 과도할 수 있음|byte/count 교차·기기|유보|
|D provenance|이미 구현|full cap 해결 안 됨|정상 work 절약|authority와 분리 유지|보존 낮음|적합|재사용/무효화/fallback|필수 보존|
|E streaming/batch|기존 format이면 호환|cold 병목 개선 후보|bounded staging 가능, E3 전체 memory 별개|crash 경계 늘어남|작은 batch 중간/전면 높음|병목 한정이면 적합|batch 원자성·TTL·취소|실측 필요 시 국한|
|F 큰 명시 profile+기존 방어|wire/hash 그대로|실측 graph 수용 후보, 완료 미검증|기존 유한 cap 유지·새 envelope 검증|인증/closure/receipt 유지|profile 낮음|최소 후속 단계|큰 cold/lease/자원·negative|우선 권고|
|G 기존 경로/fixture만|현재 hard cap|지원 경로 없음|우회는 부적절|accepted 직접 삽입 불가|정상 해법 없음|해결 안 됨|정상 대형 E2 필요|배제|
|H 새 architecture/protocol|format 변경이면 새 결정|미검증|새 proof 필요|전층 identity 영향|높음|근거 부족|전층 재감사|현재 불필요|

공통으로 auth/principal/typed hash/C1/closure/F(raw)/atomic COMMIT/Frozen B/J를 유지해야 한다.
quota를 무제한으로 풀거나 partial graph를 accepted로 만드는 대안은 비교 대상이 아니다.

## 21. 선호 최소 해법

**F를 우선 권고한다.** 목표는 비활성 synthetic 경로의 명시적 대형 profile를 지원하는 최소 변경이다.
기본값을 전역 확대하거나100k 일반 Android 지원을 지금 선언하는 제안이 아니다.
실측 fixture의 수학적 최소는 V400532/edges400528, G1+G2 union400558 및 약282MB의
단일 cold logical metadata다. 따라서 count 하나보다 **일관된 resource envelope**가 필요하다.

후속 검토용 유한 후보는 `FetchLimits(graphObjects:500000,graphEdges:1000000)`와
`ClientStoreLimits(objectCount:500000,metadataBytes:384*1024*1024)`다.
이는 새로운 규범 한도가 아니며 exact minimum도 아니다. 실측 V보다 약25% 여유의 둥근 count와,
동일 전체 graph를 세 observation staging에 중복 기록할 경우 약367MiB의 charge를 고려한
HOST 검증 출발점이다. payload512MiB/object64MiB/pages262144 및 다른 guards는 그대로 둔다.
공유가 없는 두 전체400k graph나 더 많은 facts/문자열의 모든100k history를 지원한다고 보장하지 않는다.
원 defaults100k/32MiB도 유지하고, 명시 caller가 같은 profile로 reopen하도록 한다.

이 후보는 **향후 교정·검증을 시작할 제안**이지 안전한 Android ceiling의 승인값이 아니다.
cold real HTTP/900초 lease/restart 진행성·actual E3 peak를 먼저 측정해 통과시켜야 한다.
cap만 바꾸고 timeout/clock을 고정하여 green을 만드는 변경은 승인하면 안 된다.
실측 실패가 확인되면 기존 SQLite와 D3 batching 안에서 작은 bounded put/progress batch를
추가하는 다음 최소 단계를 검토한다. 지금 전면 streaming·새 DB·새 protocol을 먼저 만들 근거는 없다.

## 22. 배제·유보한 대안

현재 cap 유지(A)는 안전한 거부를 유지하지만 의무 grid를 닫지 못한다. E2 object 상수만 올리는(B)
변경은 E1 count/metadata와 edge cap을 놓친다. 새로운 adaptive budget(C)은 현 단계에 비해 복잡하다.
provenance 재사용(D)은 이미 있으므로 새 구현 프로젝트로 만들지 않는다. 전면 streaming(E)은
실측된 병목에만 한정해야 한다. existing path/fixture(G)만으로는 hard cap을 피할 수 없다.
wire/tree/Patricia 변경(H의 protocol 부분)은 최소 해법이 아니다. HTTP batching이 필요하더라도
기존 D3 최대64 items/decoded1MiB 계약을 재사용할 수 있고 새 서버 protocol부터 만들 필요는 없다.

## 23. 보존할 보안·무결성 계약

hash와 length/type/namespace/version, C1/Unicode/exact-money, parent membership, raw/index/hot 대응,
complete11 tables, cycle/dedup/path/fan-out 검사를 유지한다. 새 profile에도 object64MiB·payload512MiB·
manifest/request/chunk·staging·retry·HTTP 동시성·SQLite page 한도를 유한하게 둔다.
모든 상한을 한꺼번에 올리는 변경은 제안하지 않는다. bytes budget은 object-count의 대체 인증 수단이 아니다.
malicious graph의 전체 RAM·new-stage 수·actual hash work도 독립 측정해야 한다.

추가 보안 subsystem이나 authorization 모델은 제안하지 않는다. bounded batch를 추가한다면
aggregate decoded bytes·객체 수·transaction bytes·취소 checkpoint·rollback을 명시해야 한다.
기존 per-object 검증을 생략하거나 accepted provenance로 아직 받지 않은 child를 추정해서는 안 된다.

## 24. 향후 positive boundary

현재 cap의99999/100000/100001 **valid closure**와 proposed ceiling의 바로 아래/동일/위,
작은 실제 V−1/V/V+1 reuse, 정확한50k/100k graph를 시험한다. leaf 수만 맞춘 malformed fixture를
boundary 성공으로 세지 않는다. cold real HTTP, 동일 target, D1 card/cash, 여러 leaf/delete/split,
cached bytes·session provenance·fresh-process restart, Frozen G1 중 G2 수락을 구별한다.
profile metadata/page/payload 여유와 원 backend expected canonical financial records를 동시에 검사한다.

## 25. 향후 negative boundary

과대 graph/개별 object·malformed/cycle/duplicate·누락 raw/descendant·wrong type/hash/context/
principal/dataset/epoch/version·invalid receipt/pin/previous_source·allocation failure·SQLITE_FULL/
corrupt pointer·truncated transfer·logout/session replacement·stale ticket·concurrent accepted switch를
시험한다. count만 거부하는지보다 별도 SQLite·기존 B/J byte oracle로 prior valid accepted/source/
receipt/pins/pending이 보존되는지 확인한다. failed candidate는 설치·성공·ACK로 반환하면 안 된다.

## 26. 취소·재시작·recovery

각 object/허용 batch 전후 cancellation 및 current session 확인, 원 request ticket 최종 guard,
실제 process death 전/후 durable object/edge/progress 원자성을 시험한다. 새로운 batch 안에서
예외·COMMIT ambiguity가 있으면 known committed와 rollback을 구별한다. lease 재발급마다
처음부터 비싼 progress를 다시 기록해 영원히 끝나지 않는지 real clock으로 검사한다.
단순히 observation clock을 고정한 결과로 완료 시간을 입증하지 않는다. old accepted 및 B/J는
실패한 수집과 별개로 읽혀야 한다. SIGKILL은 hardware power loss 증명이 아니다.

## 27. E3 I25

큰 target의 전체 object count가 크다는 이유만으로 정상 delta 전체를 재검증하지 않는다.
existing accepted-session GraphProvenance/RawCatalog와 changed frontier 경로를 보존한다.
I25는 정상 full N fetch/hash/serialize/write0을 요구한다. cold/restart/invalid provenance의 full
fallback은 별도 예외다. 과거237 SQL/4 root pins와 이번 readonly component 비용을 혼합하지 않는다.
새 profile의 두 큰 N에서 independent hash/validate/write byte와 SQL·nodes·new object를 검증하기 전
I25 전체 grid는 INCONCLUSIVE다. expanded cap 자체가 I25 통과 증거는 아니다.

## 28. E4 Frozen-B

현재 healthy provenance reuse·hash-on-read·data_version/source/receipt/lineage invalidation은 변경 없다.
full materialization은 별도 O(N) 경계다. `store_read.dart:186`, `adapters.dart:111`의 기본25MiB
legacy export budget도 E2 cap과 별개다. 원 full bundle50k28.1MB/100k56.2MB라는 사실이 그 경로의
자동 허가가 아니다. 실제 v7/B payload를 측정해야 하고 >25MiB restore/MW는 R1 소유다.
large grid의 E4 generation-consistent logical read를 수행하되 허용되지 않은 legacy handoff를
억지로 성공시키지 않는다. E4-A01/RA01 fence나 previous_source를 생략할 필요는 없다.

## 29. Pending B/J

수집 예산 조정은 기존 pending retirement mechanism과 무관하다. GET/E3 accepted는 ACK가 아니고
server와 pending의 내용이 같아도 pending을 retire/rebase하지 않는다. Frozen G1+J와 G2의 shared
object retention, 다른 principal, failed cold/recovery에서 B/J IDs·ordering·bytes·lineage를 exact
비교한다. 원 Snapshot v7 fingerprint와 sync_root는 다른 identity다.

## 30. 후속 전체 D→E 계획

기존 `docs/benchmarks/t66f-phase-b/server.py`, `harness.dart`, continuation의 `grid_server.py`/
`unique_server.py`/`cost_harness.dart` 및
fixed-H fixture/oracle를 재사용한다. 실제 D1/D2 bootstrap → **D3a observation 응답 자체인 manifest**
→ **D3b typed object POST** → D3c retention/release → E2/E1 → original-ticket E3 → E4 read 순서다.
별도 manifest GET을 새로 만들지 않는다. accepted pointer 수동 삽입·backend DB→E1 direct copy는 금지한다.

50k/100k 각각 store-free cold와 실시간 TTL/retry/reopen 진행성을 먼저 검증한다. cold correctness가
통과한 다음 fixed H/D no-change/card/cash3 warmup+20 measured sample(기존 공개 실험 설정)을 수행한다.
cache-only와 cold, delta 신규 bytes와 full graph, interrupted staging 및 Frozen 유지 cost를 구분한다.
후속 profile가 fixture H를 바꾸면 기존 H=105 결과와 합쳐 하나의 grid로 제시하지 않는다.
TLS/auth/current-ticket/negative/authority/crash 회귀 후 새 product correction의 독립 재감사가 필요하다.

## 31. 논리 byte hook 계획

[byte-hooks.md](benchmarks/t66f-b02/byte-hooks.md)에 실제 backend/mobile 함수별 경계를 적었다.
HASH는 domain prefix 포함 실제 hash preimage, VALIDATE는 실제 canonical/shape/구조 검사 입력,
WRITE는 persistence에 제출한 logical value bytes이며 attempted/rollback/committed를 나눈다.
같은 bytes의 반복 처리는 실제 work로 센다. inclusive/exclusive phase를 명시해 이중 합산을 막는다.
이번 `actual_loader_body_bytes`, unique canonical sum, DB 증가나 wire bytes를 세 counter로 바꾸지 않는다.
test-only delegate/instrumented source copy는 원본과 output/error/authority 동등성 및 overhead 검증이 선행된다.

## 32. Android proof

T6.6C §26/§38 proof8의 actual driver/pragmas/VFS/native commit fence/I/O error/전원 손실 proof는
여전히 없다. HOST DELETE/EXTRA/full/rollback와 process SIGKILL을 Android proof로 대체하지 않는다.
device 절대 latency 목표는 §35의 post-T6.6 gate이며 지금 임의 RAM·초 threshold를 만들지 않는다.
선택 profile의 foreground/background memory·suspension·battery·저장 여유는 실제 지원 기기의 별도 gate다.

## 33. R1 분리

§31/33/34의 Large Restore/MW, chunk/hash/bounded staging·backup/artifacts·atomic apply/receipt,
migration/rollback은 R1/transition 소유다. B02 예산 조정을 R1로 대신 구현하거나 R1 완료 proof로
부르지 않는다. 실제 사용자 segmented Offline/recovery 활성화는 계속 차단한다.
전체 F의 상위 dependency를 삭제한 것도 아니다. 배포나 APK 설치를 수행하지 않았다.

## 34. 남은 불확실성과 회귀

이번 실행은 기존 E1/E2/codec Flutter **161 PASS/0 FAIL**, 원 독립 object-cap/필수 monetary
vector profile **2 PASS/0 FAIL**, backend canonical/facts/Patricia **95 PASS/0 FAIL**다.
모두 실제 exit0과 machine/JUnit terminal을 보존했다. npm build도 exit0이다.
원 `"\u001c+0001000.00\u001f"` authoritative reader/C1/hash와 local `exactMoney()` 거부 assertion은
바꾸지 않았다. raw Unicode와 금융 projection authority도 제품 source 불변 및 기존 회귀로 보존한다.

FULL FLUTTER/전체 backend/analyze/APK build는 **B02에서 재실행하지 않았다**. 앞의 전체 회귀는
시작 commit의 역사 증거다. 새 조사 source의 Ruff/format/compileall/diff와 종료 preservation은
별도 결과에 기록한다. 초기 조사 harness의 Version JSON 직렬화·generic 타입·import 경로 및 AOT
native-asset 오류는 실제 로그로 보존한다. 모두 새 조사 코드 오류였고 제품 실패나 수집 PASS로 세지 않는다.

단회 HOST 표본·repeat finite schedules의 한계를 유지한다. cold real HTTP400k request 및
terminal lease 완료, actual E3/E4 full large RSS, 두 큰 N의 logical bytes, Android proof는 여전히 미검증이다.
원100000 수치의 empirical provenance도 불완전하다. 기존 limits를 거부하는 동작 자체를 새로운
Critical/High/Medium correctness defect로 분류하지 않는다. 새 확정 C/H/M는0이다.

## 35. 최소 구현 변경 제안

1. `mobile/lib/src/segmented/fetch.dart:39–54`의 supported **명시 설정 ceiling**을 위 후보와 함께
   한 policy로 검토하고 objects/edges를 같이 맞춘다. 기본100k/200k는 유지하는 좁은 변경이 우선이다.
   `graph.dart`의 cold/재사용 최종 전체 count·type·cycle 검사는 그대로 둔다.
2. 기존 E1 constructor를 이용해 후속 synthetic harness의 모든 open/reopen에 같은500k/384MiB
   profile를 명시한다. `store.dart`의 default/usage schema/triggers/payload/page budget을 바꿀 필요는 없다.
   E3/E4는 같은 `store.limits.objectCount`를 쓰므로 다른 한도를 묵시 소비하지 않는지 검사한다.
3. 새 boundary/oversize/metadata/full-disk/failure 보존 테스트와 실제50k/100k **store-free** cold를
   먼저 실행한다. current provenance·original ticket·authority를 확장 profile에서도 그대로 확인한다.
4. cold가 lease/IO에서 실패하면 실패를 보존한다. 그때 `store.dart`의 기존 `_transaction` 안에서
   검증된 객체와 progress를 유한 batch로 저장하는 작은 API, `fetch.dart`의 유한 buffer를 검토한다.
   최대 객체 수와 aggregate bytes, 큰 singleton 예외의 기존64MiB 한도, COMMIT 전후 cancellation·
   session 확인·완료 전 flush/readback을 명시한다. partial batch는 complete가 아니다.
   필요한 경우 기존 D3 최대64/1MiB 요청 계약을 재사용한다. batch는 별도 crash 재감사를 받는다.
5. 정상 동일/delta 경로에 full catalog scan·full pin rewrite를 넣지 않고 남은 논리 byte campaign을 수행한다.

예산 profile 자체는 LOW, 실제 cold 병목까지 고치게 되면 MEDIUM 범위다. 정확한 cold 해결 비용은
미확정이다. 새 server protocol, SQLite migration, financial authority/cache 또는 R1 구현은 필요 제안이 아니다.

## 36. 독립 재감사·승인 조건

제안의 시작 가능 여부는 제품 완료·merge·Android 지원·activation 승인이 아니다.
source diff가 budgets/명시 profile/필요 시 bounded staging에만 한정됐는지 독립 확인하고,
원 strict concurrency·E1/E2 negative·E3I25·E4A01/RA01·money·B/J·SQLite_FULL·actual SIGKILL와
real-TTL cold/reopen을 실행한다. budget failure의 prior-state 보존이 필수다. 하나라도 필수 증거가
없으면 correction 완료나 Phase B PASS를 선언하지 않는다. 새 성능 문제를 숨기려고 TTL·반복 수·assertion을 완화하지 않는다.

## 37. Phase B 영향

현재50k/100k 전체 D→E 및 전층 logical hash/validate/write accounting은 미완료다.
B02는 원 cap의 정체와 다른 병목을 밝혔을 뿐 이를 닫지 않았다. B01 CLOSED 및 이전 독립 PASS는
원 scope로 보존한다. 제품 변경 뒤 affected regression/independent audit를 거쳐 두 큰 grid를 재개한다.
Android와 R1 상위 exit를 만족하기 전 전체 T6.6F 완료도 선언하지 않는다.

## 38. 최종 공학 권고

**B02 INVESTIGATION COMPLETE — MINIMAL E2 OBJECT-BUDGET CORRECTION RECOMMENDED.**
현재100000은 protocol이 아니라 복합 로컬 안전 정책의 한 부분이다. 큰 두 fixture는 유효한
canonical facts 때문에 각각 약4N 객체가 된다. 단순 상수 확대만으로 E1 metadata·cold IO/lease·
E3 memory proof가 해결되지는 않는다. 가장 작은 다음 단계는 기존 방어를 보존하는 명시적 HOST
대형 profile의 targeted correction과 독립 재검증이다. 이 시작을 권고하되 실제 대형 수집이 통과하기
전에는50k/100k 지원·전체 F 완료·Android 안전·활성화를 승인하지 않는다.
확정 새 Critical/High/Medium correctness 결함은0이며, Phase B 판정은 여전히 INCONCLUSIVE다.

## 39. 조사-only commit/push

새 보고서와 `docs/benchmarks/t66f-b02/`만 명시 stage한다. 원 tracked SHA·제품 Git tree·원 protocol 및
역사 보고서·B01 assertion을 대조한 [preservation.json](benchmarks/t66f-b02/preservation.json)을 남긴다.
큰 DB는 재생성 script/manifest/SHA로 재현하고 Git에 넣지 않는다. 생성한 commit은
`git log -1 --format=%H -- docs/t66f-b02-e2-object-budget-investigation.md`로 식별한다.
push 후 HEAD/main/origin/main/actual remote와 clean은 최종 응답에서 검증한다. 배포 권한은 아니다.
2026-10-17에는 사용량 한도로 자동 승인 검토가 완료되지 않아 stage 명령이 실행되지 않았다.
2026-10-18 재개 시 remote를 포함한 네 refs와 조사-only untracked 상태가 그대로임을 확인했다.
이는 제품 안전성 거부나 측정 실패가 아니며, 완료된 실험을 새 실행으로 중복 집계하지 않았다.

## 필수 최종 상태

```text
T6.6F-B02 INVESTIGATION:
COMPLETE

STARTING PHASE B CONTINUATION COMMIT:
c591a7a0d10b208ed0c0e7efd239576f91052c66

FINAL INVESTIGATION-ONLY COMMIT:
이 보고서를 추가한 commit: git log -1 --format=%H -- docs/t66f-b02-e2-object-budget-investigation.md

REPOSITORY STATE:
VERIFIED

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

SINGLE-USER PRODUCT ASSUMPTION:
EXPLICITLY APPLIED

E2 100K OBJECT LIMIT:
LOCATED

E2 LIMIT SOURCE:
mobile/lib/src/segmented/fetch.dart:28,47; graph.dart:205,260

E2 LIMIT TYPE:
IMPLEMENTATION

E2 LIMIT SEMANTICS:
각 target의 전체 reachable closure; 새 방문 수와 재사용 subtree 포함 최종 수를 모두 검사; download-only 아님

ORIGINAL SAFETY RATIONALE:
PARTIAL — 유한 자원 목적 확인, 100000의 실측 도출 근거는 미확인

OTHER RESOURCE LIMITS:
edges200000/path512/C1 depth128/object64MiB/payload512MiB/metadata32MiB/pages262144/staging128/HTTP·retry 예산

H DEFINITION:
hot/참조 working set와 required control/policy descriptor 크기

D DEFINITION:
base 이후 changed rows

N DEFINITION:
전체 역사 row; 원 fixture는 ledger 전체 N행과 고정 참조35행을 별도 공개

N=50K HISTORICAL ROWS:
VERIFIED — ledger50000, 전체 authoritative50035

N=50K REACHABLE OBJECTS:
200331

N=100K HISTORICAL ROWS:
VERIFIED — ledger100000, 전체 authoritative100035

N=100K REACHABLE OBJECTS:
400532

50K OBJECT AMPLIFICATION:
4.00662

100K OBJECT AMPLIFICATION:
4.00532

FULL GRAPH OBJECTS:
MEASURED

DELTA NEW OBJECTS:
MEASURED — 50k25개, 100k26개; 실제 다운로드는 미측정

E2 ACTUAL FAILURE POINT:
CONFIRMED — 설정 hard cap 및 실제 graph component 거부; 대형 전체 HTTP의 최초 실패 ordinal은 미실행

CLIENT MEMORY MEASUREMENT:
PARTIAL — 실제 component·별도 모델 RSS; 전체 대형 E2/E3/E4·Android peak 미관찰

CLIENT TEMPORARY STORAGE:
PARTIAL

BACKEND RESOURCE MEASUREMENT:
PARTIAL — actual CPU/wall/RSS/main DB, 전체 physical I/O는 미관찰

HOST MEASUREMENT LIMITATIONS:
DOCUMENTED

ANDROID MEMORY SAFETY:
NOT VERIFIED

COLD LARGE-GRAPH FEASIBILITY:
UNSUPPORTED — 현재 profile; 향후 실제 cold/lease 완료는 미검증

INCREMENTAL LARGE-GRAPH FEASIBILITY:
UNSUPPORTED — 현재 전체 target cap; 신규 frontier 자체는 작음

EXISTING INTEGRITY PROTECTIONS:
PRESERVED

EXISTING RESOURCE PROTECTIONS:
INCONCLUSIVE — 현재 거부는 정상; 확대 envelope의 실제 안전성은 추가 검증 필요

OPTION A — KEEP CURRENT LIMIT:
EVALUATED

OPTION B — INCREASE FIXED LIMIT:
EVALUATED

OPTION C — SIZE-AWARE BUDGET:
EVALUATED

OPTION D — PROVENANCE REUSE:
EVALUATED

OPTION E — BOUNDED STREAMING:
EVALUATED

OPTION F — HIGHER LIMIT + EXISTING SAFEGUARDS:
EVALUATED

OPTION G — NO PRODUCT CHANGE:
EVALUATED

OPTION H — ARCHITECTURAL DECISION:
EVALUATED

PREFERRED OPTION:
F — 명시적 비활성 대형 검증 profile; D 보존, 필요성이 실측될 때만 작은 bounded batch

JUSTIFICATION:
canonical graph는 약4N이고 graph·edge·E1 metadata 예산이 함께 필요하며 기존 저장·인가 구조를 재사용할 수 있다.

REQUIRED IMPLEMENTATION CHANGES:
fetch.dart의 명시 설정 ceiling; 기존 E1 constructor를 쓰는 후속 harness profile와 새 boundary 회귀; cold 실패가 확인되면 별도 bounded put/progress 검토

ESTIMATED CHANGE COMPLEXITY:
LOW — budget profile; cold IO 교정까지 필요하면 MEDIUM

NEW SECURITY PROTECTIONS REQUIRED:
NO — 새 subsystem 권고 아님; 확대 envelope·batch 도입 시 유한 bytes/취소/rollback 검증은 필수

NEW PROTOCOL REQUIRED:
NO

NEW SQLITE MIGRATION REQUIRED:
NO

E3 I25 IMPACT:
PRESERVED — 현재 source; 큰 grid 검증은 여전히 미완료

E4 FROZEN-B IMPACT:
PRESERVED — 현재 source·이전 독립 증거 범위

FROZEN B/J IMPACT:
PRESERVED

FUTURE 50K FULL D-E TEST:
DEFINED

FUTURE 100K FULL D-E TEST:
DEFINED

LOGICAL HASH BYTE HOOKS:
IDENTIFIED

LOGICAL VALIDATE BYTE HOOKS:
IDENTIFIED

LOGICAL WRITE BYTE HOOKS:
IDENTIFIED

ANDROID VFS/I-O PROOF:
STILL REQUIRED

POWER-LOSS PROOF:
STILL REQUIRED

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

REMAINING B02 BLOCKERS:
0 — 조사 완료의 blocker; 대형 실제 수집·logical bytes·Android/R1 gate는 후속에 남음

SAFE TO BEGIN TARGETED E2 CORRECTION:
YES — 별도 구현 작업의 명시적 비활성 profile부터; 완료·merge·Android 지원 승인 아님

SAFE TO RESUME FULL PHASE B GRID:
NO — 현재 제품 cap 불변; 교정과 독립 재검증 선행

T6.6F PHASE B VERDICT:
STILL INCONCLUSIVE

SAFE TO DECLARE T6.6F COMPLETE:
NO

SAFE TO START R1:
NO — SEPARATE PREREQUISITES PENDING

SAFE FOR GENERAL-USER ACTIVATION:
NO

SAFE TO DEPLOY:
NO

FINAL DECISION:
B02 INVESTIGATION COMPLETE — MINIMAL E2 OBJECT-BUDGET CORRECTION RECOMMENDED

NEXT ACTION:
별도 E2 교정에서 명시적 대형 profile와 경계 시험을 추가하고 실제 cold 수집·lease·자원 증거를 독립 검증한다.
```
