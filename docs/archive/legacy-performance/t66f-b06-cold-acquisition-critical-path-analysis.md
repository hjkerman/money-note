# T6.6F-B06 — cold 취득 임계 경로와 다음 계측 결정

**판정: PASS — NEXT EXPERIMENT IDENTIFIED.** 다음 작업은 **B — TARGETED PROFILING**, 즉 백엔드 D3의 `RetentionSandbox.connect`와 중첩 schema 검증 비용을 분리하는 짧은 진단 하나다. 5k ON에서 백엔드 요청 처리의 포함 시간은 전체의 59.86–65.82%다. 그러나 순수 함수 CPU, SQLite 대기, 관측자 CPU는 분리되지 않았고, 아직 특정 중복 검사를 제거하는 구현을 정당화하지 못한다.

B05는 **CORRECTNESS-QUALIFIED EXPERIMENTAL CANDIDATE; MATERIAL END-TO-END BENEFIT NOT ESTABLISHED**로 보존한다. `_lookup`의 실제 hot decode는 25% 줄었으나, 순서를 바꾼 두 5k ON 비교 모두 전체 취득 시간은 기준 소스가 짧았다. 실험 후보를 채택하거나 원 IR07 기준을 대체하지 않았다. 이번 B06은 기존 자료 분석만 수행했다. 새 cold·microbenchmark·회귀 suite 실행은 모두 0회이며 제품·계측·admission·release artifact를 변경하지 않았다.

## 소스와 기준의 처분

시작과 종료 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. 기존 미커밋 상태를 유지한다. 세 archive의 파일별 SHA·mode·canonical payload와 별도로 engine source map을 재계산했다. payload digest를 engine SHA로 취급하지 않았다. [신원 검증](../../benchmarks/t66f-b06/source-identities.json), [재계산 스크립트](../../benchmarks/t66f-b06/identities.py)에 방법과 실제 archive 경로가 있다.

|후보|파일 수|canonical payload SHA-256|실제 engine SHA|
|---|---|---|---|
|B03|899|`8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`|`7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c`|
|B05|901|`d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae`|`f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`|
|B05A|905|`29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542`|`f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`|

원 B03 archive SHA는 `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5`, B05는 `745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e`, B05-A는 `b239b9d277e5fd747c2f85c5577f42e203ad7a737b29317f0e23581d6b13b0f1`이다. B05 archive에는 승인 전의 기존 release 선언이 보존돼 있으므로 실제 최적화 engine과 선언이 다르다. 이는 B05-A에서 해결된 역사 상태이며 새 결함으로 재개방하지 않는다. B05-A의 선언과 실제 engine은 일치한다.

현재 live의 후보 정의 905파일은 B05-A 동결 payload `29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542`와 bytes/mode가 같다. 새 보고서 등 후보 밖 파일을 포함한 전체 dirty tree의 digest라고 주장하지 않는다. 현재 engine은 `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`다.

실험 최적화는 `backend/isolated_sync/observation.py:ObservationRepository._lookup`에 있고 그 파일 SHA는 `cb69ddaaa2fc9ab7a7336937248b3748829043dce45a07cdf216e35db11ca408`다. admission은 `mobile/lib/src/segmented/protocol.dart`, 직접 연동 artifact는 `mobile/assets/segmented/isolated-release-artifacts.json` 및 `docs/specimens/t66d3b-release-artifacts.json`이다. 현재 release JSON SHA `8a2734c48f9355ba8930f75cf779d0da7c8fcdd19f297a8c3f78004e653da092`를 보존했다.

향후 성능 기준은 **원 B03 동결 백엔드, engine `7ad114bc…`**로 명시한다. 실제 Flutter의 교차 engine 비교에는 두 engine을 정확히 인정하는 공통 B05-A client 신원을 따로 기록한다. live의 최적화 소스를 성능 기준으로 자동 승격하지 않는다. 지금 필요한 안전한 선택은 실험 설정에서 동결 A를 사용하는 것이며 live revert가 아니다. 영구 기각이 필요해지면 별도 범위에서 최소 역diff와 실제 source/release/guard 정합 전이를 함께 검토해야 한다. 단일 함수만 복구해 SHA와 artifact를 불일치시키지 않는다. [후보 처분 기록](../../benchmarks/t66f-b06/candidate-disposition.json).

B03 독립 정확성은 **CLOSED — IR07, 원 동결 소스와 지원 runtime에 한정**한다. B05-A/B05-B의 영향 범위 자격 검증을 새 소스의 IR07 독립 감사로 부르지 않는다.

## 기존 측정 목록과 비교 가능성

[측정 목록](../../benchmarks/t66f-b06/measurement-inventory.json)은 136개 기록을 분류하고 각 raw 경로·SHA, N/H/D, engine/source/fixture, 완료 상태, 실제 accepted identity, 카운터와 시간 경계를 보존한다. raw가 없는 수치는 `null`이며 OFF 카운터를 0으로 채우지 않는다.

|자료|기록 수|이번 분석에 쓰는 범위|비교 한계|
|---|---|---|---|
|B04|106|정상 비용 72, 주요 cold 8, 진단 26|진단 26에는 초기 cold 2 포함; 주 cold 집계에서 제외|
|B05|16|로컬 micro 8, backend-only 전송 8|첫 backend-only 4건은 A/B 조건 불일치; 나머지도 Flutter E3/E4 없음|
|B05-A|12|N1k 8, N5k 4의 완료 cold|조건당 N1k 2회, N5k 1회|
|B05-B|2|N5k ON 기준→최적화, 완료 cold|독립 역순 재현; 조건당 1회|
|주 cold 합계|22|B04 8 + B05-A 12 + B05-B 2|여러 연구를 새 matched pair로 합치지 않음|

B04 N계열은 publication 반환까지의 시간을 사용하고 E4 read는 별도다. B05-A/B05-B는 AppState의 segmented-internal publication과 bounded E4 accepted read까지다. UI/Offline-ready 설치 시간이 아니다. B04의 분리 E4를 단순히 더해 새로운 연속 측정으로 만들지 않았다. B05-A/B05-B의 전체 사후 financial/graph oracle와 UTC 종료 기록은 primary stopwatch 밖이다. client CPU tick도 사후 검증을 포함하므로 primary client CPU로 쓰지 않는다.

B04와 B05-A/B05-B는 timestamp/fixture 신원이 달라 직접 matched 비교가 아니다. 반면 두 5k ON 연구는 같은 template SHA `c7d03671c9a7fdaa595cdacc349164421474aed0fbbd38d69a655b804ead31dc`, 금융 raw digest `f5d7ff2a2e882377acb209f8f836223ad23b69fb86a829cec7da450fad5cab03`, client component `76e438cc4aaec70c901bf3b4ec1e991c4d3f7a19a3956cd9626741e72b62ecc5`, 동일 세 driver bytes를 사용했다. [독립 driver 신원](../../benchmarks/t66f-b05b/driver-identities.json), [독립 비교 원문](../../benchmarks/t66f-b05b/comparison-summary.json).

지원 환경은 CPython 3.12.3/backend SQLite 3.45.1, Flutter 3.47.4/Dart 3.13.3, client SQLite 3.53.4다. client native library SHA는 `0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace`다. 새 loopback TLS pool, backend 주소공간 8GiB, 기존 HOST largeGraphVerification profile, client FK ON/synchronous EXTRA/journal DELETE, 실제 900초 observation과 기존 최대 3 attempts를 유지한 역사 측정이다. 준비 backend view는 이미 생성된 상태이고 client의 objects/accepted generation은 빈 상태다. OS cache cold를 주장하지 않는다. [B04 환경](../../benchmarks/t66f-b04/environment.json), [B05-A 환경](../../benchmarks/t66f-b05a/environment.json), [B05-B preflight](../../benchmarks/t66f-b05b/preflight.json).

§35의 다섯 N은 1k/5k/10k/50k/100k다. 규범은 H/D 고정을 요구하지만 숫자 H/D나 절대 지연 합격선을 지정하지 않는다. 실제 N은 ledger 행 수, 기타 authority는 35행, archive는 N−105행, current ledger는 105행이다. hot 87,364B/control 3,178B를 고정했고 H를 105 하나로 축약하지 않았다. 이 cold의 D는 해당 없음(`null`)이다. B04 정상 비용의 no-change D=0, 카드/현금 UPDATE 각각 D=1과 분리한다.

### 실제 cold 시간

다음 B04 표는 같은 연구 내부 N계열이다. backend/HTTP/SQL은 포함 시간이므로 열을 더하지 않는다. 모든 행의 E1/E2/E3/E4가 완료됐으나 T는 publication 반환 경계다. raw 경로는 `benchmarks/t66f-b04/raw/n<N>-v3/cold-0-<mode>.json`이다.

|N|계측|객체|HTTP 횟수|T (초)|backend (초)|HTTP (초)|SQL API (초)|
|---|---|---|---|---|---|---|---|
|1000|OFF|4,132|82|33.367267|20.990641|21.409654|4.604357|
|1000|ON|4,132|82|35.003695|22.770095|23.107042|5.033741|
|5000|OFF|20,148|335|131.769341|81.436781|82.691891|18.890112|
|5000|ON|20,148|335|147.352910|88.801818|90.297687|24.860576|
|10000|OFF|40,170|653|293.277913|184.258306|187.187810|44.453867|
|10000|ON|40,170|653|292.402266|181.480623|183.967365|45.894860|
|50000|OFF|200,331|3180|1489.494416|847.286590|858.559499|270.939620|
|50000|ON|200,331|3180|1573.537722|953.533246|966.066640|262.930430|

다음 표는 B05-A/B05-B의 동일한 publication+bounded E4 경계다. 각 링크가 시간·단계 완료·engine·실제 accepted UUID/Target을 담은 raw를 가리킨다. UUID는 독립 발급되므로 UUID 문자열 일치를 요구하지 않고 동일 engine의 Target/상대 sequence와 검증된 graph를 비교했다.

|자료/engine/계측|N|순번|전체 T (초)|객체|lookup (초)|
|---|---|---|---|---|---|
|[B05A A OFF](../../benchmarks/t66f-b05a/raw/n1000-0-A-off/run.json)|1000|0|31.966206|4,132|8.411466|
|[B05A B OFF](../../benchmarks/t66f-b05a/raw/n1000-1-B-off/run.json)|1000|1|29.485876|4,132|7.396431|
|[B05A B ON](../../benchmarks/t66f-b05a/raw/n1000-2-B-on/run.json)|1000|2|29.896952|4,132|6.906503|
|[B05A A ON](../../benchmarks/t66f-b05a/raw/n1000-3-A-on/run.json)|1000|3|32.640993|4,132|8.905636|
|[B05A B OFF](../../benchmarks/t66f-b05a/raw/n1000-4-B-off/run.json)|1000|4|29.811573|4,132|7.722953|
|[B05A A OFF](../../benchmarks/t66f-b05a/raw/n1000-5-A-off/run.json)|1000|5|30.952197|4,132|9.181800|
|[B05A A ON](../../benchmarks/t66f-b05a/raw/n1000-6-A-on/run.json)|1000|6|33.901548|4,132|9.058759|
|[B05A B ON](../../benchmarks/t66f-b05a/raw/n1000-7-B-on/run.json)|1000|7|33.219919|4,132|8.060923|
|[B05A B ON](../../benchmarks/t66f-b05a/raw/n5000-0-B-on/run.json)|5000|0|153.265907|20,148|36.590073|
|[B05A A ON](../../benchmarks/t66f-b05a/raw/n5000-1-A-on/run.json)|5000|1|152.688187|20,148|43.310019|
|[B05A A OFF](../../benchmarks/t66f-b05a/raw/n5000-2-A-off/run.json)|5000|2|152.966598|20,148|43.807800|
|[B05A B OFF](../../benchmarks/t66f-b05a/raw/n5000-3-B-off/run.json)|5000|3|142.070529|20,148|36.177263|
|[B05B A ON](../../benchmarks/t66f-b05b/raw/n5000-0-A-on/run.json)|5000|0|149.743978|20,148|38.704527|
|[B05B B ON](../../benchmarks/t66f-b05b/raw/n5000-1-B-on/run.json)|5000|1|155.002541|20,148|35.592555|

B05-A 5k ON은 B→A, B05-B는 A→B 순서다. 두 pair 모두 새 client DB의 accepted null/sequence0에서 sequence1 게시와 실제 E4 read까지 완료했다. reachable/staged/committed는 각각 20,148개·13,146,158B, HTTP는 335회(객체 332, manifest 2, release 1), lookup은 667회다. manifest의 두 번째 응답은 terminal 재확인이며 새 lease 갱신이 아니다. 네 실행의 만료·갱신은 0, scope pending/error도 0이다.

독립 raw/graph/financial 검증은 PASS이며, engine 간 Target 차이는 engine context, hot hash, sync_root로 설명된다. 금융 state digest `6174fac48d00c00cf015d8dbfdfaddea67bec633c0aa099ac7b932f6a423ad22`와 ledger digest `291ae2c544f13e2602fd62f615ce3da71ba40e8ff9bde2fcbcae5d7c1555c9ac`는 같다. engine별 object identity의 정당한 차이를 금융 차이로 처리하거나 제거해 버리지 않았다.

## 시간 경계와 임계 경로

`fetch.dart`의 cold frontier는 한 packet HTTP exchange를 await한 뒤 그 응답을 검증·저장하고 다음 packet으로 진행한다. SQL API는 동기 FFI다. 백엔드도 한 응답의 보호 bytes와 outer terminal guard를 준비한 뒤 반환한다. 네 5k ON raw에서 backend 요청 interval의 중첩은 없다. 따라서 요청 처리 누적은 직렬 취득의 주요 경로다. 다만 백엔드와 client의 두 clock을 하나의 절대 timeline으로 합치거나, client interval trace 없이 완전한 함수별 exclusive profile을 얻었다고 주장하지 않는다.

| 경계 | 포함 관계와 해석 |
|---|---|
| backend handler wall/CPU | auth·DB·조회·관측·worker 처리를 포함; process CPU는 함수 전용 CPU가 아님 |
| client HTTP | handler를 포함; HTTP−handler는 TLS/전송/queue/send·receive scheduling/관측 혼합 잔여 |
| D3 prepared/auth | auth는 prepared 안; admission/resolution도 prepared 안 |
| D3 acquire | admission→resolution→serialization/내부 terminal은 순차 표식; outer terminal HTTP는 prepare 뒤 |
| lookup | admission과 outer terminal 등을 가로지르는 함수 집계; resolution과는 분리되나 위 상위 표식 안 |
| client E2 envelope | 초기 recovery 포함; HTTP·E1 SQL·graph 처리 포함 |
| E1 SQL API | E2/E3 내부; blocking SQLite·관측 wrapper 포함, physical I/O 시간 아님 |
| E3 envelope | cold 검증·prepare·guard/commit/readback 포함; final transaction만의 시간이 아님 |
| callback 하한 | SQL API 안의 일부; 전체 observer CPU를 뜻하지 않음 |

[임계 경로 계산](../../benchmarks/t66f-b06/critical-path-summary.json)의 모든 숫자는 inventory key와 raw metric 경로를 참조한다. 아래 포함 시간 표도 열이나 행을 더해 total로 사용하지 않는다.

|포함 시간 (초)|B05A A|B05A B|B05B A|B05B B|
|---|---|---|---|---|
|전체 T|152.688187|153.265907|149.743978|155.002541|
|E2+초기 recovery|136.934759|136.859718|134.765979|136.922651|
|HTTP 누적|101.855216|95.740597|92.732616|94.095604|
|backend handler|100.495743|94.165475|91.239141|92.785343|
|backend process CPU|100.321037|93.953099|91.050360|92.603560|
|lookup|43.310019|36.590073|38.704527|35.592555|
|hot body decode|19.723485|13.193669|17.574797|12.708559|
|D3 resolution|25.741441|26.049393|22.977004|25.270038|
|SQL API 전체|19.532613|25.315526|24.994259|26.086545|
|E3 envelope|15.670200|16.325732|14.896308|17.991767|
|E3 native transaction|0.016139|0.016311|0.020342|0.005516|
|E3 readback|0.002329|0.002084|0.004137|0.001838|
|E4 bounded read|0.080307|0.077304|0.075779|0.085387|
|SQL callback 하한|1.114755|1.102742|1.158811|1.229020|

백엔드 process CPU/handler wall은 약 99.8%다. 이 host·직렬 실험에서 큰 backend 대기보다는 CPU 실행이 큰 것으로 보이지만 Python 제품 코드/SQLite CPU/B03 callback CPU는 구별되지 않는다. client의 순수 validation CPU, SQL fsync/DB 대기, GC/JIT 및 observer 전용 CPU는 **미측정**이다. 이 자료는 Android 메모리나 VFS 안전성의 증거가 아니다.

B04 내부 cold ON/OFF 비율은 N1k 1.0490배, N5k 1.1183배, N10k 0.9970배, N50k 1.0564배다. N50k의 전체 차이는 +84.043306초인데 handler는 +106.246656초, SQL API는 −8.009190초였다. 이 경계들은 중첩되고 환경 변동도 있으므로 전체 차이나 backend 차이를 observer 전용 CPU로 부르지 않는다. callback 누적 하한 역시 전체 관측 비용이 아니다. 계측 교란은 원 B04의 PARTIALLY CHARACTERIZED를 유지한다. [역사 내부 쌍 계산](../../benchmarks/t66f-b06/perturbation-context.json). B05-A/B05-B의 ON source 비교를 서로 다른 계측 모드의 비교로 재해석하지 않았다.

### 조건부 비중복 시간 배분

아래는 실제 exclusive profiler 출력이 아니다. 순차 HTTP/동기 SQL이라는 source 경계에 조건을 둔 **파생 시간 예산**이다. `E2 기타=E2 envelope−HTTP−acquisition SQL`, `HTTP 기타=HTTP−handler`, `경계 잔여=T−E2−E3−E4`다. SQL 전체 대신 E2까지의 SQL만 빼고 E3는 온전한 envelope로 남겼다. 이 배분만 합이 T가 된다. 잔여를 순수 네트워크 또는 client CPU로 이름 붙이지 않는다.

|파생 배분 (초)|B05A A|B05A B|B05B A|B05B B|
|---|---|---|---|---|
|backend handler|100.495743|94.165475|91.239141|92.785343|
|HTTP 기타 혼합|1.359473|1.575122|1.493475|1.310261|
|E2 중 timed SQL API|16.556390|22.290114|22.105858|22.643932|
|E2 기타 미귀속|18.523153|18.829007|19.927505|20.183115|
|E3 envelope|15.670200|16.325732|14.896308|17.991767|
|E4 bounded read|0.080307|0.077304|0.075779|0.085387|
|경계 잔여|0.002921|0.003153|0.005912|0.002736|

handler가 전체의 59.86–65.82%이고 HTTP 밖 추가 혼합 비용은 약 0.85–1.03%다. 그러므로 이 loopback 자료에서 순수 네트워크 지연을 우선 원인으로 고를 근거는 작다. WAN/실기기에서는 별도 측정이 필요하다. E3 native transaction과 readback은 합쳐도 약 25ms 이하인데, cold E3 envelope는 14.90–17.99초다. 작은 final COMMIT만을 주요 병목으로 지목할 수 없다.

`backend handler−lookup−resolution`은 29.558–31.923초, 전체의 19.74–20.59%다. 두 하위 구간은 source에서 분리돼 있지만, 이 차이는 **connection/schema/auth/그 외 framing·관측을 포함한 미귀속 예산**이다. connection의 직접 시간도, 제거 가능한 시간도 아니다. `_lookup`과 resolution의 포함 시간을 모두 또 더해 잘못된 전체를 만들지 않았다.

## 국소 이득, 상한 모델과 전체 변동

네 5k ON 실행 모두 constructor hot decode는 667회다. baseline body decode 2,001회와 optimized 1,334회를 합쳐 hot 전체는 2,668→2,001회, 정확히 25% 감소한다. 다음 표는 **나머지 경로가 고정되고 lookup interval이 직렬 임계 경로라는 조건**의 Amdahl식 계산이다. 국소 wall 차이에도 표본 변동과 경량 probe 비용이 섞이므로 모델 값을 실현 가능한 확정 절감량으로 취급하지 않는다.

|자료|기준 lookup/T|lookup 감소|국소 감소율|다른 비용 고정 모델의 T 감소|lookup 전부 0의 느슨한 상한|
|---|---|---|---|---|---|
|B05A|28.37%|6.719946초|15.52%|4.40%|28.37%|
|B05B|25.85%|3.111972초|8.04%|2.08%|25.85%|

작업 개수 25% 감소가 전체 지연 25% 감소를 뜻하지 않는다. 관측된 국소 개선을 다른 비용 고정 모델에 넣으면 전체의 2.08–4.40% 수준이다. 모든 lookup을 0으로 만드는 비현실적 상한조차 25.85–28.37%이며 필수 권한/lease/정합 검증을 생략할 수 없으므로 최적화 목표가 아니다. B05의 20 lookup 로컬 진단에서 OFF 50.091808→42.538985ms, ON 50.918436→43.002099ms라는 결과 역시 실제 Flutter 전체 시간을 대체하지 않는다. [B05 로컬 원문](../../benchmarks/t66f-b05/run-manifest.json).

B05-A 5k ON은 152.688187→153.265907초(+0.577720초, 개선율 −0.378366%), B05-B는 149.743978→155.002541초(+5.258563초, −3.511702%)다. 두 순서 모두 기준이 빨랐다. 아래는 **optimized−baseline**의 관측 delta다. 첫 열은 함수별 인과 기여가 아닌 조건부 비중복 배분이고, nested 지표는 별도 해설로만 쓴다.

|파생 배분 delta (초)|B05A|B05B|
|---|---|---|
|backend handler|-6.330268|+1.546202|
|HTTP 기타 혼합|+0.215649|-0.183214|
|E2 중 timed SQL API|+5.733724|+0.538074|
|E2 기타 미귀속|+0.305854|+0.255610|
|E3 envelope|+0.655532|+3.095459|
|E4 bounded read|-0.003003|+0.009608|
|경계 잔여|+0.000232|-0.003176|

B05-A에서는 lookup이 6.720초 줄고 handler도 6.330초 줄었다. 동시에 E2 중 SQL API가 5.734초, E3 envelope가 0.656초 늘었다. B05-B에서는 lookup이 3.112초 줄었지만 handler의 lookup 밖 비용이 4.658초 늘어 handler 자체가 1.546초 늘었다. 그 밖 비용 증가 중 resolution은 2.293초, 미귀속 backend 예산은 2.365초다. E3 envelope도 3.095초 늘었다. 증가가 발생한 시간 경계는 관측됐지만, 개별 증가를 최적화가 유발했다고 입증하지 못했다. SQL 전체 증가는 B05-A 5.783초/B05-B 1.092초이며 E2/E3에 포함되므로 다시 더하지 않는다. [변동 귀속 계산](../../benchmarks/t66f-b06/variance-attribution.json).

같은 engine의 두 연구 사이 T 범위는 A 2.944209초, B 1.736634초다. 이는 각 2개 관측의 범위이며 모집단 noise나 신뢰구간이 아니다. JIT/GC·cache·CPU 주파수/스케줄링·SQLite blocking·관측 비용 변화는 미분리 가설이다. 두 순서에서 기준 우세가 유지됐으므로 단순한 첫 실행 warmup 설명도 입증되지 않았다. 원인이 fixture 객체 증가라는 설명은 동일 객체/요청/lookup 수와 독립 의미 검증에 맞지 않는다. 기존 1k ON/OFF 및 5k OFF에서 관측한 국소·일부 전체 개선을 삭제하지 않되, 그것으로 5k ON 반복 결과를 덮지 않는다. 통계적 유의성이나 확정 성능 회귀를 주장하지 않는다.

### 논리 비용과 실제 작업

다음 표의 backend hash는 `*/sha256/hash_input_bytes`, primary는 `*/json/submitted_bytes`, client는 해당 stage의 hashInputBytes/submittedBytes 합이다. 관측된 반복 처리 span이며 고유 fixture 크기와 다르다. 별도 인증 SHA 입력 12,395B는 backend hash 열에 넣지 않았다. B05-A와 B05-B의 같은 engine counter map 전체가 같다는 독립 결과와 raw를 확인했다.

|5k ON 논리 값|기준 A|최적화 B|
|---|---|---|
|backend hash 입력 B|118,833,034|118,833,034|
|backend primary 입력 B|359,789,383|301,517,595|
|client hash 입력 B|108,575,771|108,575,771|
|client primary 입력 B|176,967,697|176,967,697|
|E1 objects committed BLOB B|13,146,158|13,146,158|

backend primary 감소 58,271,788B는 `667×87,364`와 일치한다. 실제 불필요한 decode 한 번이 사라진 B03 Case B의 설명 가능한 작업 감소이며 누락된 관측을 이득으로 센 것이 아니다. hash/client validation/SQL은 그대로다. client SQL의 attempted text/BLOB은 9,490,460/13,150,581B, effective와 committed는 각각 8,140,427/13,150,581B다. scalar 423,142개는 byte로 임의 변환하지 않았다. backend SQL attempted/effective/committed text/BLOB은 모두 3,797/5,790B다. 이 scope는 raw의 observation+transfer이며 fixture bootstrap은 밖이다. SQL API 시간과 이 logical payload를 physical disk I/O로 바꾸지 않는다. OFF의 같은 비용을 0이라고 하지 않는다.

## N계열과 source 구조

B04는 N1k→50k에서 reachable 객체 4,132→200,331, HTTP 82→3,180회로 증가했다. 같은 계열 ON T는 35.004→1,573.538초다. 단순 곡선만으로 알고리즘의 O(N)를 증명하지 않는다. source는 cold에서 전체 reachable graph 취득·검증·durable 저장을 수행하며, HTTP packet의 item/bytes/depth 한도 때문에 객체 수와 함께 요청 수가 증가한다. 이 구조와 아래 실제 작업 카운터가 규모에 따른 비용 증가를 뒷받침한다. [규모별 추출값](../../benchmarks/t66f-b06/scaling-summary.json).

|ON 작업량|N5k|N50k|
|---|---|---|
|client transactions|338|3,557|
|client object reads|80,632|849,101|
|client verified bytes|55,871,359|576,807,763|
|graph nodes examined|20,148|200,331|
|cold full raw rows|5,035|50,035|
|cold full fact rows|10,057|100,057|
|cold canonical full builds|1|1|

N5k의 backend SQL은 195,621 statements, 객체 조회 50,546회, prefix validation 30,398회와 cache hit 243,998회다. N50k는 각각 1,881,024/512,310/311,979/3,078,767회다. 이미 packet-private prefix cache가 있으므로 무조건 전역 cache나 검증 생략을 제안할 수 없다. `PathResolver.resolve/validate`는 terminal과 prefix miss에 membership/context/ref/hash/C1 검증을 수행한다. 이 함수의 약 15–17% 시간 중 중복·제거 가능 비율은 미측정이다. E1은 packet batch transaction을 사용하며 20,148객체에 338 transactions다. per-object COMMIT이 병목이라는 가설은 이 source와 수치에 맞지 않는다.

cold의 full verification/canonical build 1회는 허용된 초기화다. 별도 정상 N50k stage no-change/card/cash 진단은 E3의 `full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds/graph_nodes_examined`가 모두 0이다. 이 진단은 prepare 후 discard한 별도 범위이며 정규 게시 비용 cell로 합치지 않았다. cold O(N) 때문에 정상 E3가 full-N을 수행한다고 재해석하지 않는다. [세 stage 원문과 key](../../benchmarks/t66f-b06/critical-path-summary.json)의 `steady_E3_I25_distinction`에 연결했다. 100k 미실행이므로 large-N I25 전체와 다섯 지점 비용 grid는 여전히 PARTIAL이다.

B04 N50k ON의 실제 HTTP 누적은 966.067초, handler는 953.533초, SQL API는 262.930초다. 보고서의 1,399.633084초 transfer window는 client 작업을 포함하는 연속 취득 창이며 HTTP 누적 시간이 아니다. auth/prepared/http/admission/outer-terminal도 서로 중첩돼 있으므로 합산하지 않는다. backend generation은 요청 내 hot generation과 준비 raw/index bootstrap을 구분해야 한다. 네 5k ON의 요청 내 generation은 0.237–0.307초, 전체의 0.21% 미만이다. 준비 backend generation을 cold 임계 경로의 지배 비용으로 분류할 근거는 없다.

## 후보 순위와 단일 다음 작업

다음 순위는 **추가 확인 가치**의 순서다. 서로 겹치는 후보를 더해 100%로 만들지 않는다. 구현 가능한 절감량이 입증된 순위가 아니다. [기계 판독 순위](../../benchmarks/t66f-b06/bottleneck-ranking.json)에 포함 관계·source·위험·검증비·SHA 영향을 분리했다.

|순위|후보와 측정 범위|회수 가능한 비용|복잡도·정확성 위험·검증비|규모와 SHA 영향|
|---|---|---|---|---|
|1|backend의 lookup/resolution 밖 미귀속 29.558–31.923초, T의 19.74–20.59%|connection/schema 직접 비율은 미측정|경계 timer는 작음; 필수 auth/lease/schema 보존 위험은 높아 구현 금지; 작은 backend replay로 확인 가능|요청마다 반복하는 source 경로; 영구 backend 수정 시 새 engine/artifact/admission 필요|
|2|PathResolver resolution 22.977–26.049초, 약 15–17%|필수 조회·검증 중 중복 비율 미측정|중간 복잡도, corruption/rejection/cache 수명 위험; graph 회귀 필요|packet/terminal/prefix miss 증가; backend SHA 영향|
|3|client SQL API 19.533–26.087초, 약 13–17%|CPU/대기/관측 혼합, 미측정|durability·복구 위험 높음; 실제 Flutter 검증비 큼|batch 저장 구조; client component/보호 source 영향|
|4|E2의 HTTP/timed SQL 밖 약 18.5–20.2초, 약 12–13%|parse/traversal/GC/기타 API 혼합|Dart CPU 경계 분리 필요; wire/graph 신뢰 경계 위험|cold 전체 graph 방문; client SHA/lock 영향|
|5|cold E3 envelope 14.896–17.992초, 약 10–12%|cold 필수 검사와 중복 비율 미측정|authority fence·accepted proof 위험 매우 높음; E3/E4/P0 검증 필요|정상 I25와 구별; client 보호 source 영향|
|6|HTTP−handler 약 1.31–1.58초 및 요청 내 generation 0.237–0.307초|순수 전송은 미분리; 현재 상위 예산은 작음|protocol batching 재설계는 큰 비용/위험; 현재 우선 근거 부족|loopback 결과만 유효; protocol/backend 수정이면 다수 계약·SHA 영향|

**선택은 B — TARGETED PROFILING 하나다.** `Adapter.credential`, `TransferRepository.acquire`의 `_connection`, `Adapter.terminal`의 lookup은 객체 요청마다 각기 fresh `RetentionSandbox.connect` 경로를 사용한다. `connect`는 open/ownership, PRAGMA, version과 exact schema validator를 실행한다. `retention_schema.validate_schema`→`finalization.validate_schema`에는 authoritative schema/column/table_xinfo, sync metadata·trigger·profile 비교가 있다. 이 반복은 실제 source로 확인되지만 시간은 미측정이다. 따라서 schema가 확정된 지배 병목이라고 결론 내리지 않는다.

[단일 다음 작업 명세](../../benchmarks/t66f-b06/next-action-decision.json)는 다음과 같다.

- 원 B03 backend/engine `7ad114bc…`, CPython 3.12.3/SQLite 3.45.1과 B03 ON을 유지한다. 보존 B05-A N1k 합성 template을 독립 SQLite backup으로 복원하고 새 합성 auth/정상 UTC lease를 사용한다.
- 고정 8 packet 묶음을 control→probe→probe→control로 실행하되 총 **최대 32 packet, 120초, 주소공간 8GiB**로 제한한다. 전체 Flutter cold나 engine A/B가 아니며 product/release 파일 변경은 0이다. 900초 TTL·3 attempts는 그대로다. 120초는 진단 예산이며 제품 합격선이 아니다.
- task 소유의 method 경계 timer만으로 각 `connect`의 호출수·wall_ns·thread_CPU_ns, 중첩 schema validator의 inclusive/exclusive 시간, auth/admission/outer-terminal 귀속을 집계한다. 통제 묶음으로 timer 교란을 확인하고 응답/오류/기존 counter sanity를 대조한다. 큰 per-object 로그를 남기지 않는다.
- B03 지원 preflight를 우회하는 `sys.setprofile`/trace/비허용 PEP669 observer는 켜지 않는다. B03 instrumentation을 바꾸지 않는다.
- 필수 검사를 유지하면서 줄일 수 있는 반복 작업이 충분한 비중을 차지할 때만 별도 최소 최적화안을 고른다. 실제 schema 시간이 작으면 그 가설을 기각한다. 이 프로파일링은 새로운 구현 승인으로 확대하지 않는다.

전체 미귀속 예산을 0으로 만드는 조건부 상한은 약 20%지만, 실제 connection/schema의 비중과 가능한 절감은 아직 정해지지 않았다. 숫자 성능 합격선을 새로 만들지 않았다. 현재 추가 구현보다 이 작은 경계 측정의 가치가 크다. 실기기에서만 알 수 있는 메모리/VFS와 별개인 공유 서버 CPU 비용을 저비용으로 분리하기 때문이다. 단순히 국소 최적화를 다시 시도하거나 비싼 50k A/B를 요청할 근거는 없다.

## full-scale·로드맵·보존

100k instrumented full cold는 **NO-GO**다. 역사 P03는 397,146/400,532 staged 객체, 세 observation 만료, E3/E4 미완료의 실패이며 반복하지 않았다. [B04의 원 증거 연결](../../benchmarks/t66f-b04/historical-p03.json)에 handler/CPU/SQL/callback 경계가 보존돼 있다. 삭제된 원 matched DB를 새 자료라고 주장하지 않는다. B04 50k OFF 1,489.494416초/ON 1,573.537722초와 B05의 불확정 전체 이득으로는 그 실패의 재발 가능성이 충분히 낮아졌다고 할 수 없다. 1k/5k를 100k 완료 보증으로 외삽하지 않는다.

B01/B02와 원 B03는 CLOSED, B04는 bounded PASS, B05-A는 admission/real-path PASS, B05-B는 독립 역순 재현 PASS다. B05 시스템 이득은 NOT ESTABLISHED다. Phase B는 **INCONCLUSIVE**, 다섯 지점 grid와 large-N I25는 PARTIAL이다. §35의 미완성 rows-read/HTTP·압축·framing 비교, 100k 정상 cost 및 large-N 검증 의무가 남는다. Galaxy S23 FE의 격리 app ID/storage를 쓰는 Real-Device Gate는 미완료이고 Android memory/VFS/physical I/O/power loss는 미검증이다. 다음 작은 host 진단을 넘어 제품 최적화를 선행할 근거는 아직 없다. T6.7 UX/T6.8 cleanup 구현으로 이동하거나 T6.9 미래 감사를 현재 통과 증거로 쓰지 않는다. T7 큰 snapshot 처리는 별도다. R1 activation은 CLOSED, production deployment는 NOT AUTHORIZED다.

이번 검증은 archive/source 재계산, raw metric 추출, 포함 관계·잔여 계산 assertions, 기존 파일 bytes/mode와 Git index 보존 확인이다. backend/Flutter/npm build는 B06에서 재실행하지 않았다. 역사 B05-A의 backend 1,904 tests/1,540 subtests와 Flutter 205 PASS를 새 실행으로 세지 않았다. [분석 검증](../../benchmarks/t66f-b06/analysis-validation.json), [입력 증거 목록](../../benchmarks/t66f-b06/evidence-manifest.json), [시작 보존](../../benchmarks/t66f-b06/preservation-before.json), [종료 보존](../../benchmarks/t66f-b06/preservation-after.json)에 결과를 기록했다.

기존 visible tracked/untracked 6,136파일의 bytes/mode/크기를 대조했고 기존 staged path/mode/blob/stage와 원 index bytes를 보존했다. index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`로 같다. 보고서와 `docs/benchmarks/t66f-b06/`만 추가했다. 제품/계측/allowlist/lock/protocol 변경, commit/push는 없다. 역사 archive와 증거를 덮어쓰지 않았다.

단일 scratch `/tmp/money-note-t66f-b06-20261026`에는 파생 출력 2개만 만들었고 동일 내용이 영구 JSON에 보존된 뒤 제거했다. DB/WAL·Flutter build tree·새 동결 후보는 만들지 않았다. 기존 cache/DB/다른 작업 파일은 지우지 않았다. [실제 정리 기록](../../benchmarks/t66f-b06/cleanup.json)에 파일 수와 회수량을 남겼다. 재현 순서는 evidence manifest에 기록한 `identities.py`→`extract.py`→`decide.py`→`report.py`와 보존/manifest/analysis 검증 단계다. 새 workload 없이 보존 자료만 읽는다. `provenance.py before`는 이번 시작 기록 전용이므로 기존 evidence 위에서 다시 실행하지 않는다.

다음 행동: **원 B03 기준 backend의 N=1k 보존 fixture에서 최대 32개 packet·120초로 connect/schema 비용을 분리 계측한다.**

## 최종 상태

```text
T6.6F-B06 COLD ACQUISITION CRITICAL-PATH ANALYSIS:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL SOURCE

B04 MEASUREMENT:
PASS — BOUNDED

B05-A:
PASS — ENGINE ADMISSION AND REAL-PATH QUALIFICATION

B05-B:
PASS — INDEPENDENT REVERSED-ORDER REPLICATION

B05 OPTIMIZATION DISPOSITION:
EXPERIMENTAL ONLY — SYSTEM BENEFIT NOT ESTABLISHED

LOOKUP LOCAL WORK REDUCTION:
25% HOT DECODE INVOCATIONS

5K ON B05-A:
BASELINE 152.69 s / OPTIMIZED 153.27 s

5K ON B05-B:
BASELINE 149.743978 s / OPTIMIZED 155.002541 s

COLD CRITICAL-PATH EVIDENCE:
PARTIAL

DOMINANT MEASURED STAGE:
backend handler 포함 시간 — 5k ON 91.239–100.496초

DOMINANT STAGE WALL-TIME SHARE:
59.86–65.82% — 포함 시간, 함수별 exclusive CPU 미분리

LOOKUP ESTIMATED MAXIMUM SYSTEM BENEFIT:
다른 비용 고정 모델 2.08–4.40%; lookup 전부 제거의 느슨한 상한 25.85–28.37%

OBSERVED END-TO-END VARIABILITY:
B−A +0.577720/+5.258563초; 같은 engine 간 범위 A 2.944209초/B 1.736634초, 각 2관측

NEXT BOTTLENECK CANDIDATES:
1 backend 미귀속 예산 19.74–20.59%; 2 resolution 약 15–17%; 3 SQL API 약 13–17% — 중첩·제거 가능량 미측정

NEXT RECOMMENDED ENGINEERING ACTION:
TARGETED PROFILING

NEXT TARGET:
backend D3 RetentionSandbox.connect → retention_schema/finalization.validate_schema

NEXT TARGET EVIDENCE:
handler−lookup−resolution 29.558–31.923초; 요청별 fresh connect 경로, 순수 schema 시간은 미측정

NEW FULL N=5K COLD A/B:
0

NEW FULL N=50K COLD:
0

NEW FULL N=100K COLD:
0

100K INSTRUMENTED FEASIBILITY:
NO-GO

PHASE B FIVE-POINT COST GRID:
PARTIAL

E3 I25 LARGE-N:
PARTIAL

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY/VFS/POWER LOSS:
NOT VERIFIED

REAL-DEVICE GATE:
NOT YET COMPLETED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

PRODUCT SOURCE MODIFIED:
NO

B03 INSTRUMENTATION MODIFIED:
NO

EXACT ALLOWLIST MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B06:
NO

HISTORICAL EVIDENCE:
PRESERVED

COMMIT:
NONE

PUSH:
NOT PERFORMED

B06 REPORT:
docs/t66f-b06-cold-acquisition-critical-path-analysis.md

EVIDENCE MANIFEST:
docs/benchmarks/t66f-b06/evidence-manifest.json

TEMPORARY ARTIFACT CLEANUP:
파생 임시 출력 2개와 단일 scratch 제거; DB/build 생성 0, 분석 증거 보존

FINAL VERDICT:
PASS — NEXT EXPERIMENT IDENTIFIED

NEXT ACTION:
원 B03 기준 backend의 N=1k 보존 fixture에서 최대 32개 packet·120초로 connect/schema 비용을 분리 계측한다.
```
