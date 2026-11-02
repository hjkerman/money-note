# T6.6F-B04 — Phase B 측정 가능성·계측 시간 교란·제한 규모 실제 비용 검증

**PASS — 제한된 B04 측정 목표 완료** B03 계측 정확성은 **CLOSED — IR07**로 유지한다. 이번 결과는 Phase B 전체 PASS가 아니다. 100k 판정은 **NO-GO**이며 새 100k cold 실행은 **0회**다. 허용된 네 N의 실제 cold·정상 비용과 대응 시간 비교를 완료했지만, 현재 계측ON100k cold를 다시 시도할 개선 근거는 확보하지 못했다. 전체 다섯 지점·large-N I25와 Android gate는 미완료다.

[실행 manifest](benchmarks/t66f-b04/run-manifest.json)는 유효한 정상 비용·완료된 cold·진단 전용·미완료를 분리한다. 유효한 통제 측정 80개/40쌍, 완료된 기타 publication 진단 26개, 별도 stage 진단 6개다. [실행 전 계획](benchmarks/t66f-b04/plan.md), [계약 행렬](benchmarks/t66f-b04/contract-matrix.json), [쌍별 원자료](benchmarks/t66f-b04/pairs.json), [논리 비용](benchmarks/t66f-b04/logical-costs.json)에 연결한다.

## 계약과 실제 설정

§35의 바인딩 N은 **1000/5000/10000/50000/100000**이다. H는 hot/참조 working set와 필수 control/policy descriptor 크기, D는 base 이후 변경 행이다. 규범에는 **숫자 H/D, 반복 횟수, 절대 지연 합격선이 없다**. 숫자를 새 규범으로 만들지 않았다. 정상 목표는 O(H+changed bytes+L log P+256E), full history fetch/hash/serialize/write 0회이며 I25는 steady-state full-N 작업 금지다. cold/full sync의 O(N)는 허용된다. 해당 조건은 실제 논리 비용과 source 경계로 판단하며 wall-time 곡선을 복잡도 증명으로 바꾸지 않는다.

|구분|요구·이번 적용|남은 의무|
|---|---|---|
|바인딩 §35|다섯 N에서 H/D 고정 no-change/card/cash 반복|100k 미실행|
|기존 실험 설정|seed662602·평가일2026-10-05·current ledger105·다른10개 table35행|N label은 ledger N, 전체 authoritative N+35|
|기존 실험 설정|초기 hot87364B/control3178B; archive N−105|105만으로 H 전체를 정의하지 않음|
|실험 D|no-change0, 카드id1002·현금id101 UPDATE 각각1|세 trial은1001/1002/1003원, −51/−52/−53원|
|바인딩 §16|실제900초 TTL, 기존 attempts3/observations3|연장·증가0|
|바인딩 §25|같은 Target·정확한 base·원 AppState guard→COMMIT|inactive segmented 내부 경계; UI 활성화 없음|
|바인딩 §35·I25|실제 hash/primary span/SQL payload와 operation 수|100k·완전한 rows-read/압축 비교 의무는 별도 미완료|
|추가 실험 선호|정상3회 반복, 규모/회차별 순서 반전, fresh HTTP pool|OS cache flush 없음; n3 p95는 표본 최대값|
|task 제한|하위 네 N만 실행, N100k cold 금지|별도 명시 승인 필요|

## 소스·환경·보존

|항목|검증|
|---|---|
|시작/종료 HEAD|ebcbd54d90eeee194a04b9eea6367f446ee2fd28|
|B03 payload SHA-256|8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8|
|archive SHA-256|fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5|
|선택 source|899개 / 9,801,906B, 모든 바이트·mode 일치|
|나머지 baseline|고정 Git blob·실행 비트까지 대조|
|실행 workspace|/tmp/money-note-t66f-b04-20261026/tree|
|live payload 차이|[]|
|runtime|CPython3.12.3 / backend SQLite3.45.1 / client SQLite3.53.4 / Flutter3.47.4 / Dart3.13.3|
|Git index·기존 파일|시작 실제 index bytes/entries와 동일, 기존 파일 변경0개|

[무결성](benchmarks/t66f-b04/source-identity.json)과 [마지막 보존 검사](benchmarks/t66f-b04/preservation-after.json)를 보존했다. 동결 archive는 수정하지 않았고, 실행본은 기준 Git archive 위에 payload를 복원했다. 제품/B03 계측/규범/SHA 기대값·Snapshot v7/OfflineBaseline v4·원 authority guard는 불변이다. 새 코드는 B04 실험 driver/분석뿐이다. build 의존성만 기존 개발 runtime을 사용했다. 일반 sandbox는 bwrap loopback 초기화 오류로 시작하지 못해 승인 검토된 실행 경로를 사용했다. 자동 승인 거부는 없었다.

실제 TLS는 새 loopback ephemeral port·같은 합성 credential·같은 서버/Target을 사용했다. 운영18080·DB·Snapshot·환경 파일·서비스에는 접근하지 않았다. 모든 규모에 기존 HOST large verification profile(object500000/metadata384MiB)을 동일하게 적용했다. 이는 운영 제한 변경이나 Android 메모리 합격 근거가 아니다. [환경 manifest](benchmarks/t66f-b04/environment.json)와 규모별 execution 파일에 실제 RSS·disk 표본을 남겼다.

## ON/OFF 방법과 도구 오류

각 mode는 독립된 빈 client DB에서 같은 Target을 실제 cold 취득하고, 같은 accepted Target/상대 sequence 위에서 정상 작업을 반복했다. namespace·immutable identity·authorization·H/D·runtime·리소스·관측 정책을 맞췄다. 로컬 generation UUID는 독립 발급되므로 UUID 일치 대신 Target·상대 sequence·DB count/body bytes·E4 값의 동등성을 검사하고 실제 UUID를 모두 기록했다. Cold의 backend는 bootstrap과 독립 oracle 뒤 warm 상태이며, client accepted/objects/staging은 비어 있다. OS page-cache cold를 주장하지 않는다. backend bootstrap과 mutation generation은 별도 **ON 단일 scope**이고 ON/OFF generation 쌍이 아니다.

첫1k 진단은20 operation을 완료했으나 ON 정상9회 중8회에서 send 실패·retry1건과 약15초 대기가 있었다. 초기 예외 타입은 미기록이므로15초 timeout과 맞는다는 정황을 확정된 예외 분류로 바꾸지 않는다. 동일 boot의 후행 wall/단조시계 anchor에서는 backend 첫 요청 이전의 대기로 관찰됐지만, 초기 실행과 anchor 사이 wall-clock drift 상한은 기록하지 않았다. 완료된 body 시간에 실패한 send 대기를 숨겨 넣지 않았다. 양 mode에 매 operation 새 HTTP pool을 적용한 통제 cohort에서는 해당 오류가 사라졌다. 이 비교는 pool 수명에 민감한 교란을 보여주지만 stale socket/Zone 내부 경합의 세부 원인을 독립 분리하지 않았으며, 15초를 observer CPU라고 부르지 않는다. 첫 결과는 정상 grid와 분리했다. P02 prepared cache가 ON에 포함되므로 ON/OFF 차이는 cache 이득과 관측 비용을 포함한 순효과다. ON에는 TEMP row callback Stopwatch도 추가되어 있으며 이 타이머 자신의 비용을 독립 제거하지 않았다. 따라서 아래 비율은 B03+명시한 timing facade 구성의 실측 순효과이지 순수 B03 callback CPU가 아니다. 정상 pair는 두 client가 같은 process에 함께 살아 있어 RSS·JIT·OS cache 차이도 남는다.

초기 driver의 TreeKey import 누락은 측정 전 compile 오류, 두 번째 준비의 기존 scratch/pending 재사용 거부는 측정 전 환경 오류였다. 새 cohort별 root 존재 금지로 바로잡았다. 첫1k 종료의 namespace BLOB JSON 오류는20개 완료 측정 뒤 artifact 단계 실패이며, 이미 생성된 SQLite backup을 독립 검증해 보존했다. fuser의 `--` 인자 형식 오류는 삭제0개에서 멈췄고 절대경로 호출로 수정했다. pubroot 밖 analyzer의 패키지 해석 오류는 import 경로만 바꾼 task-owned package 내부 분석본으로 분리했다. 원 로그와 [도구 사건 목록](benchmarks/t66f-b04/tooling-incidents.json)을 보존했다. B03 finding으로 재분류하지 않는다.

## 시간 경계와 교란 실측

|측정|실제 경계·한계|
|---|---|
|내부 동기화 wall|원 AppState.publishSegmentedForIsolatedUse 호출→반환. segmented 내부 accepted publication이며 실제 UI/Offline-ready 완료는 미측정|
|backend handler|ASGI app 진입→응답 bytes 준비 완료. native wait 포함; CPU는 별도 process_time_ns|
|D3 내부|auth/prepared/admission/resolution/terminal serialization/terminal HTTP. 서로 포함되므로 더하지 않음|
|HTTP|send→body 완료, header 별도; 실패 send 시간 별도. 순수 network 지연이 아님|
|E1 SQL API|Database.execute/select 호출 inclusive; native DB·wrapper·UDF 포함|
|callback|Dart TEMP row UDF body 합의 하한. 전체 observer CPU가 아님|
|E3 commit/readback|제품이 반환한 transaction/readback stopwatch. 전체 E3Verify/Prepare와 다름|
|50k 별도 stage|공개 E2 acquire / E3 verify API·proof / prepare 각각 stopwatch; accepted 불변 후 discard|
|E4|실제 accepted read scope에서 ledger/cash 각1행과 hot 읽기|
|CPU·불확실성|client /proc10ms tick, backend process CPU; shared timer 비용·OS cache/JIT/순서·scheduling 잔존|

다음 OFF/ON은 각 cell의 wall median/p95(초), 비율은 **쌍별 ON/OFF 비율의 중앙값[min,max]**이다. 비율 중앙값은 두 mode 중앙값의 몫과 다를 수 있다. cold n=1, 정상 n=3이며 p95는 표본 최대값이다. 모집단 tail·통계적 신뢰구간을 주장하지 않는다.

|N|작업|쌍|OFF median/p95 s|ON median/p95 s|쌍별 비율 중앙값[범위]|backend 비율 중앙값|SQL API 비율 중앙값|
|---|---|---|---|---|---|---|---|
|1000|cold|1|33.367/33.367|35.004/35.004|1.049[1.049,1.049]|1.085|1.093|
|1000|무변경|3|2.745/2.762|2.893/2.900|1.057[0.953,1.070]|1.265|1.126|
|1000|카드 1행|3|7.376/7.400|7.770/7.954|1.075[1.050,1.078]|1.076|1.185|
|1000|현금 1행|3|6.917/7.073|7.364/7.393|1.065[1.045,1.068]|1.077|1.256|
|5000|cold|1|131.769/131.769|147.353/147.353|1.118[1.118,1.118]|1.090|1.316|
|5000|무변경|3|2.480/2.489|2.632/2.653|1.066[1.061,1.081]|1.243|1.116|
|5000|카드 1행|3|8.109/8.120|8.051/8.586|1.044[0.967,1.057]|1.083|1.048|
|5000|현금 1행|3|6.645/6.876|6.861/7.308|1.047[1.032,1.063]|1.076|1.044|
|10000|cold|1|293.278/293.278|292.402/292.402|0.997[0.997,0.997]|0.985|1.032|
|10000|무변경|3|2.524/2.681|2.662/2.878|1.055[1.043,1.073]|1.260|1.095|
|10000|카드 1행|3|9.501/9.539|8.871/9.924|1.042[0.930,1.045]|1.073|1.026|
|10000|현금 1행|3|6.946/7.713|8.027/8.168|1.062[1.041,1.176]|1.092|1.058|
|50000|cold|1|1489.494/1489.494|1573.538/1573.538|1.056[1.056,1.056]|1.125|0.970|
|50000|무변경|3|2.839/2.841|3.052/3.133|1.074[0.978,1.240]|1.255|1.204|
|50000|카드 1행|3|10.248/10.442|10.921/10.959|1.048[1.046,1.070]|1.069|1.027|
|50000|현금 1행|3|8.250/8.275|8.865/8.931|1.074[1.027,1.079]|1.087|1.044|

[시간 원자료](benchmarks/t66f-b04/timing-summary.json)와 pairs.json에 OFF/ON·절대 차이·비율·CPU·E3·E4를 모두 보존했다. 겹치는 handler/HTTP/SQL/callback을 합친 가짜 총시간은 없다. 순수 Python callback CPU·hash-only wall·network-only latency는 미측정이다.

## Cold·정상 비용의 분리

|N|reachable objects|고유 canonical B|cold OFF s|cold ON s|서로 다른 관측 OFF/ON|완료 전 만료 OFF/ON|
|---|---|---|---|---|---|---|
|1000|4,132|2,749,721|33.367|35.004|1/1|False/False|
|5000|20,148|13,146,158|131.769|147.353|1/1|False/False|
|10000|40,170|26,160,538|293.278|292.402|1/1|False/False|
|50000|200,331|130,710,592|1489.494|1573.538|2/2|True/True|

동일 nonce의 terminal replay200은 새 lease가 아니다. 각 Available의900초를 따로 적용했고 실제 갱신만 distinct observation ID로 센다. 완전 취득 뒤의 E3 local 후처리는 transfer TTL과 별도다. 모든 완료 cold는 accepted sequence0→1과 객체 수·고유 BLOB 합을 확인했다. 정상 no-change는 accepted UUID/sequence를 유지하고 신규 immutable0이며, 카드·현금은 정확히 한 행 변경 후 sequence를1씩 전진시켰다.

backend cold bootstrap ON과 첫 카드/현금 generation ON은 다음과 같다. source seed 준비·독립 graph oracle는 timer 밖이며 실제 capture/finalize/commit은 generation scope 안이다. 이 값을 client/request 시간에 더해 ON/OFF 총량을 만들지 않는다.

|N|generation ON|wall s|process CPU s|실제 hash 입력 B|primary submitted B|
|---|---|---|---|---|---|
|1000|bootstrap|11.122|11.096|7,781,077|14,028,338|
|1000|card|0.658|0.639|990,156|2,311,614|
|1000|cash|0.353|0.333|113,298|266,088|
|5000|bootstrap|54.824|54.660|38,198,999|68,930,077|
|5000|card|0.755|0.731|1,017,373|2,369,945|
|5000|cash|0.384|0.363|118,239|278,035|
|10000|bootstrap|93.186|92.909|76,266,202|137,643,584|
|10000|card|0.622|0.601|1,025,668|2,388,353|
|10000|cash|0.359|0.337|119,953|282,903|
|50000|bootstrap|519.243|517.979|382,256,927|690,163,790|
|50000|card|0.773|0.752|1,057,781|2,457,090|
|50000|cash|0.401|0.363|126,503|299,391|

## 실제 논리 비용

각 byte 열은 독립 지표다. Hash는 실제 sink 입력(domain/NUL·반복 포함), primary validation은 UTF8/JSON/C1에 제출한 span이며 structured visits와 다르다. Backend JSON 완료와 Dart 전체 C1 완료도 구별한다. SQL은 NEW TEXT UTF8/BLOB payload이고 UPDATE는 NEW row 전체, DELETE 신규 payload0이다. scalar는 개수로 분리한다. API bind·HTTP entity·파일 성장·VFS/물리 I/O를 대용으로 쓰지 않았다. OFF counter는 **null/미계측**이며0 비용이 아니다.

아래는 각 규모 첫 novel delta/trial0의 정확한 값이다(평균·추정 아님). client hash/validation은 publication과 정해진 E4 read를 포함하므로 E4는 stage 파일로 따로 확인할 수 있다. 나머지 두 정상 반복과 cold의 전체 counter는 logical-costs.json 및 원 JSON에 있다.

|N|작업|새 객체|client hash B|client submitted/completed B|SQL attempted/effective/committed B|objects committed B|
|---|---|---|---|---|---|---|
|1000|무변경|0|561,618|16,610,025/16,610,025|6,030/5,708/5,708|0|
|1000|카드 1행|18|2,279,785|19,505,390/19,505,390|268,796/265,912/265,912|249,934|
|1000|현금 1행|18|1,103,293|17,527,660/17,527,660|119,411/116,673/116,673|100,968|
|5000|무변경|0|564,304|16,615,338/16,615,338|6,033/5,711/5,711|0|
|5000|카드 1행|22|4,681,436|21,942,454/21,942,454|279,613/275,074/275,074|254,625|
|5000|현금 1행|20|1,123,698|17,558,640/17,558,640|121,827/118,821/118,821|102,007|
|10000|무변경|0|565,101|16,617,149/16,617,149|6,036/5,714/5,714|0|
|10000|카드 1행|24|4,770,728|22,042,151/22,042,151|282,204/277,395/277,395|255,850|
|10000|현금 1행|20|1,121,477|17,557,759/17,557,759|121,834/118,829/118,829|102,012|
|50000|무변경|0|567,960|16,622,809/16,622,809|6,039/5,717/5,717|0|
|50000|카드 1행|26|6,645,629|23,949,303/23,949,303|291,000/284,742/284,742|259,690|
|50000|현금 1행|22|1,140,507|17,587,164/17,587,164|124,259/120,985/120,985|103,059|

|N|작업|backend request hash B|backend primary submitted/completed B|backend SQL attempted/effective/committed B|
|---|---|---|---|---|
|1000|무변경|641,981|1,284,380/1,284,380|8,690/8,690/8,690|
|1000|카드 1행|5,659,599|15,760,062/15,760,062|8,690/8,690/8,690|
|1000|현금 1행|5,365,356|15,033,173/15,033,173|8,690/8,690/8,690|
|5000|무변경|644,615|1,292,282/1,292,282|8,690/8,690/8,690|
|5000|카드 1행|6,716,429|18,836,366/18,836,366|8,690/8,690/8,690|
|5000|현금 1행|5,892,543|16,567,641/16,567,641|8,690/8,690/8,690|
|10000|무변경|641,678|1,283,462/1,283,462|8,694/8,694/8,694|
|10000|카드 1행|7,236,057|20,348,190/20,348,190|8,694/8,694/8,694|
|10000|현금 1행|5,889,753|16,559,142/16,559,142|8,694/8,694/8,694|
|50000|무변경|642,518|1,285,981/1,285,981|8,694/8,694/8,694|
|50000|카드 1행|7,772,413|21,909,917/21,909,917|8,694/8,694/8,694|
|50000|현금 1행|6,417,476|18,095,069/18,095,069|8,694/8,694/8,694|

모든 유효 ON operation에서 E1 objects INSERT committed BLOB은 독립 DB의 sum(length(body)) 증가와 같았다. Attempted/effective/committed는 실제 scope에서 분리했고 rollback·실패 span도 별도 key로 보존했다. 신규 저장량과 repeated processing bytes를 혼동하지 않는다. 전체 최종 상태는 SQLite backup API로 보존해 quick_check/FK 및 독립 canonical SHA·reachable set·11개 table의 실제 값 digest를 backend와 양 client에서 대조했다. [보존 artifact 목록](benchmarks/t66f-b04/artifacts/)에 gzip SHA와 uncompressed SQLite SHA·실제 Target/UUID/sequence가 있다. 삭제된 원 P03 자료를 복구한 사본이 아니다.

## E3 I25 관측

|N|작업|E3 hash B|E3Verify primary B|hot raw 행|변경 행|tree examined|E3 SQL committed B|
|---|---|---|---|---|---|---|---|
|1000|무변경|282,944|16,034,677|110|0|2|3,598|
|1000|카드 1행|492,564|16,712,852|110|1|6|3,734|
|1000|현금 1행|332,248|16,087,160|110|1|4|3,734|
|5000|무변경|282,982|16,034,687|110|0|2|3,601|
|5000|카드 1행|508,952|16,740,128|110|1|6|3,737|
|5000|현금 1행|336,686|16,093,901|110|1|4|3,737|
|10000|무변경|283,012|16,034,700|110|0|2|3,603|
|10000|카드 1행|512,574|16,747,045|110|1|8|3,739|
|10000|현금 1행|336,657|16,094,042|110|1|4|3,739|
|50000|무변경|283,051|16,034,713|110|0|2|3,606|
|50000|카드 1행|531,562|16,778,365|110|1|8|3,742|
|50000|현금 1행|341,215|16,100,675|110|1|4|3,742|

정상 completed 범위에서 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds는0이다. source의 store_publication.verifyPublicationCandidate는 유효한 same-connection base proof에서 verifyIncrementalGeneration으로 가고, prepare는 incremental receipt의 네 root만 pin한다. commit은 작은 accepted metadata CAS/usage/guard→native COMMIT/readback이다. incremental_verification의 checked/hotRow는 실제 hot/참조110행과 changed tree/facts를 검사한다. H행 검증에서 같은 bounded leaf의 C1 span이 반복되어 약16MB validation이 생길 수 있으나 전체 역사 N행 재검증은 아니다. 실제 span을 줄여 기록하지 않았다. 몇 점의 wall trend를 O(1) 증명으로 부르지 않으며 100k I25는 미확인이다.

50k 별도 진단은 같은 accepted base와 Target에서 공개 E2/E3 API를 직접 호출했다. prepare 뒤 discard했으며 accepted ID/previous/sequence/Target 불변을 assertion했다. 이후 실제 게시는 원 AppState guard를 사용했고, 사전 취득으로 cache가 warm해진 해당 publication은 정상 비용 cell에서 제외했다.

|작업|E2 OFF/ON s|E2 비율|E3 verify OFF/ON s|E3 verify 비율|prepare OFF/ON ms|
|---|---|---|---|---|---|
|무변경|0.707/0.893|1.262|1.952/2.040|1.045|24.606/26.766|
|카드 1행|8.294/8.711|1.050|2.399/2.277|0.949|24.692/26.293|
|현금 1행|6.481/6.651|1.026|2.358/2.087|0.885|25.145/26.121|

E2 API wall은 transport·E1·검증을 포함하며 기존 verification_us도 별도로 남겼다. 이를 순수 parser CPU로 바꾸지 않는다. E3 API stopwatch와 proof 자체 verificationMicroseconds를 함께 보존했다. stage별 E2_work/E3_verify_work가 acquisition과 publication 관측을 분리한다.

## 교란 판정·100k 실행 판단

**PARTIALLY CHARACTERIZED — IMPORTANT SCALE OR STAGE UNMEASURED**. 정상 workload의 쌍별 wall 비율 중앙값은1.042–1.075배, cold는0.997–1.118배다. 50k cold는 OFF1489.494416초/ON1573.537722초(+84.043306초,1.056424배), backend handler847.286590/953.533246초(1.125395배)다. 50k E2 API와 E3 verify/prepare도 별도 대응 측정했다. 그러나 실제 UI 설치 완료·generation OFF 대응·100k·순수 observer CPU와 추가 callback Stopwatch 자체 비용은 미분리다. backend wall과 CPU가 가깝고 request 처리 비중이 크지만, 이를 모두 Python observer CPU 탓으로 돌리지 않는다.

**100k: NO-GO**. 현재 구성의 계측ON100k full cold 재시도는 정당화되지 않는다. 50k ON 전송 구간은1399.633084초이며 첫900초 관측에서123735개, 두 번째에서76596개를 수신했다. backend953.53초 중 D3 admission285.69초, resolution260.03초, 외부 terminal HTTP290.76초가 관측되어 request 처리의 큰 고정 비용이 남아 있다. 이 내부 경계·auth/prepared/HTTP는 중첩되므로 합산하지 않는다. 역사 P03 실패 이후 실제100k 완료를 안전하게 예상할 성능 개선은 입증되지 않았다. 같은 per-object 비용·phase mix라는 단순 진단 가정조차 ON은 역사400532객체에 약2798.36초로, 최대 세900초 active window보다 길다. 이는 실제100k 예측 보증이나 새 합격선이 아니며, 더 큰 path/DB·마지막 phase·renewal/terminal·환경 변동을 검증하지 않았다. OFF의 단순값2582.05초도 약118초 여유만 남아 안전한 완료 보증이 아니다. OFF cold 뒤 정상ON이라는 대안은 별도 계획 후보일 뿐 이번 판정에서 GO로 승격하지 않았고 실행하지 않았다.

[별도 최소 성능 후보](benchmarks/t66f-b04/performance-candidate.json)는 ObservationRepository._lookup의 동일 hot body 두 decode를 함수 내부의 한 로컬 map으로 공유하는 것이다. 모든 context/projection/auth/TTL/canonical·terminal 검사는 유지하는 후보이며 이번에는 구현하지 않았다. 성공 object packet3174개에서 source상 최소554,586,672B의 중복 primary span 제거가 예상되지만, 실제 wall/CPU 절감이나100k 완료를 증명한 값이 아니다. admission과 terminal의 큰 시간 안에서 어느 성분이 줄어드는지는 같은50k 대응 측정으로 검증해야 한다.

역사 P03는 **HISTORICAL FULL-SCALE FAILURE — NOT REPEATED**다. 397,146/400,532 객체, 세 관측 만료, 2,699.957907초, E3/E4 미완료, 원 matched backend/client SQLite 부재를 유지한다. 당시 backend handler 합은 1886.414805초, process CPU 1883.257226초, client SQL 경계 합 380.069584초, row callback 하한 23.548580초다. SQL에 callback이 포함되고 handler는 HTTP wait와 겹치므로 더하지 않는다. 실패 원인을 instrumentation 하나로 단정하지 않는다. [원 raw 연결·수치](benchmarks/t66f-b04/historical-p03.json)를 보존했다.

## 검증·정리·남은 의무

새 backend 영향 회귀 27개 통과(실패0, 오류0, skip0), Flutter source-SHA 6개 통과, 보호 source7개 SHA·frontend npm build 통과다. 실제 bounded grid의 case4개와 각 operation 원자료는 별도다. 전체 suite를 새 PASS로 주장하지 않았다.

source-SHA guards와 전체 reconstruction 바이트/mode, 시작 index/기존 파일 보존을 마지막으로 확인했다. 전체 backend/Flutter·과거 cancellation lifecycle·IA01–IA07 재감사는 반복하지 않았다. B03 correctness 폐쇄를 작은 성능 fixture로 재판정하지 않았다.

규모별 matched SQLite backup·gzip·SHA·독립 graph/value oracle 뒤 비활성 task DB를 정리했다. 종료 scratch 3438개 파일과 앞선 경계 정리의 관찰 할당량 합은 2260.0MiB다(중간 SQLite/WAL 생성 I/O 전체 추정 아님). 증거는 약 387.2MiB 보존했다. 기존 파일·동결 후보·외부 cache 삭제0, 활성 DB/WAL 삭제0이다. 실제 free-disk 변화는 호스트의 다른 쓰기와 섞이므로 이 할당량 합과 같다고 주장하지 않는다.

남은 바인딩 의무는 100k의 fixed-H/D 정상 cost cell·large-N I25와 §35의 완전한 rows-read/HTTP·압축·framing 비교다. VM visit 세분화·추가 cold 표본·실제 UI 완료·generation의 대응 ON/OFF·exclusive observer CPU 분리는 추가 측정/진단 과제이며, 규범에 없는 숫자 표본 수나 합격선을 새 바인딩으로 만들지 않는다. Android memory/VFS·physical I/O·hardware power loss는 미검증이다. R1 large restore는 DEFERRED, R1 activation·B01/B02/B03는 CLOSED, production deployment는 NOT AUTHORIZED다. 전체 Phase B는 INCONCLUSIVE다.

다음 행동: **100k cold 재시도는 보류하고, _lookup의 hot body 중복 decode만 함수 내부에서 공유하는 별도 최소 후보를 만들어 같은50k ON/OFF로 취득 시간 개선을 검증한다.**

```text
T6.6F-B04 PHASE B MEASUREMENT FEASIBILITY:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07

B03 FROZEN PAYLOAD SHA-256:
8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8

MEASURED SOURCE IDENTITY:
VERIFIED

SUPPORTED MEASUREMENT RUNTIME:
CPython 3.12.3 / backend SQLite 3.45.1 / client SQLite 3.53.4 / Flutter 3.47.4 / Dart 3.13.3

BINDING H:
숫자 미지정; 실험 current ledger105 + 참조/control/policy, 초기 hot87364B/control3178B

BINDING D:
숫자 미지정; 이번 no-change0 / one-card1 / one-cash1

BINDING FIVE N POINTS:
1000 / 5000 / 10000 / 50000 / 100000

EXECUTED N POINTS:
1000/5000/10000/50000

UNEXECUTED N POINTS:
100000 — 이번 task 명시 제외, 별도 승인 필요

NO-CHANGE MEASUREMENTS:
4/5 지점; 각3회 ON + 3회 OFF

ONE-CARD DELTA MEASUREMENTS:
4/5 지점; 각3회 ON + 3회 OFF

ONE-CASH DELTA MEASUREMENTS:
4/5 지점; 각3회 ON + 3회 OFF

COLD BASELINE MEASUREMENTS:
8/8 하위 규모 계획; client cold, backend bootstrap은 별도 ON

VALID COMPLETED MEASUREMENTS:
80개 통제 측정 + 26개 기타 publication 진단 + 6개 stage 진단

INCOMPLETE/EXPIRED MEASUREMENTS:
0개 미완료; 완료된50k cold2개에서 각각1회 lease 만료 후 갱신; 도구 오류 별도

INSTRUMENTATION ON/OFF PAIRS:
40쌍 통제 비교 + 13쌍 publication 진단 + 3쌍 stage 진단

END-TO-END PERTURBATION:
정상 쌍별 비율 중앙값 1.042–1.075배; cold 0.997–1.118배; n1/n3 한계, 실제 UI 완료 미측정

BACKEND PERTURBATION:
정상 handler 쌍별 비율 중앙값 1.069–1.265배; generation ON만 측정

E1/E2 PERTURBATION:
SQL API 정상 중앙 비율 1.026–1.256배; 50k E2 API 별도 실측, 순수 parser CPU 아님

E3/E4 PERTURBATION:
transaction 정상 중앙 비율 0.813–1.119배, E4 0.993–1.264배; 50k verify/prepare 별도

LOGICAL HASH INPUT BYTES:
실제 sink 입력과 stage별 exact 합계 보존; OFF는 null

PRIMARY VALIDATION INPUT BYTES:
실제 submitted/completed/failed span 분리; 구조 방문 수와 별도

SQL LOGICAL WRITE BYTES:
NEW TEXT UTF8/BLOB; objects committed BLOB=독립 DB body 증가량

ATTEMPTED/EFFECTIVE/COMMITTED:
세 계수·rollback 별도 보존; scalar/NULL 개수와 물리 I/O 구분

COLD VERSUS STEADY STATE:
SEPARATED

E3 I25 MEASURED COVERAGE:
1000/5000/10000/50000 정상 경로 full-N counter0; source·stage 증거 보존

LOWER-N BINDING COST COMPLIANCE:
PARTIAL — 실제 논리 비용 근거 확보, 전체 §35 계측 열은 일부 미완료

FULL FIVE-POINT H/D/N COST GRID:
PARTIAL

LARGE-N E3 I25:
PARTIAL — 100k 미검증

RUNTIME PERTURBATION:
PARTIALLY CHARACTERIZED

N=100K FULL-SCALE FEASIBILITY:
NO-GO

N=100K FULL COLD RUNS IN B04:
0

HISTORICAL P03 N=100K:
FAILED — 397146 / 400532

MEASUREMENT ENVIRONMENT:
LIMITATIONS RECORDED

ON/OFF PRODUCT EQUIVALENCE:
PASS — exact Target/상대 sequence/DB bytes/E4 및 최종 raw graph 일치

SOURCE-SHA GUARDS:
PASS

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY SAFETY:
NOT VERIFIED

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B04:
NO

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

COMMIT:
NONE

PUSH:
NOT PERFORMED

BENCHMARK MANIFEST:
docs/benchmarks/t66f-b04/run-manifest.json

B04 REPORT:
docs/t66f-b04-phase-b-measurement-feasibility.md

TEMPORARY ARTIFACT CLEANUP:
B04 scratch 및 검증된 DB 정리; 관찰 할당량 2260.0MiB, matched 증거 보존; 기존 삭제0

FINAL VERDICT:
PASS

NEXT ACTION:
100k cold 재시도는 보류하고, _lookup의 hot body 중복 decode만 함수 내부에서 공유하는 별도 최소 후보를 만들어 같은50k ON/OFF로 취득 시간 개선을 검증한다.
```

