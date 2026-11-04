# T6.6F-B05-B — 독립 N=5k ON 역순 재현과 성능 자격 판정

**PASS — REVERSED-ORDER REPLICATION COMPLETED.** 계획한 실제 Flutter cold 두 번을 기준(A)→최적화(B) 순서로 각각 한 번 완료했다. 각 실행은 실제 D3→인증 HTTP/TLS→E2→E1→AppState E3 게시→E4 accepted read에 도달했다. 독립 객체·native accepted·11개 raw table·금융 state 검증과 계측 scope 종료 검사가 모두 통과했다.

**성능 판정은 NO MATERIAL SYSTEM BENEFIT OBSERVED, N=50k 후속은 NOT JUSTIFIED다.** 역사 B05-A는 최적화가 0.577720초 느렸고, 이번 역순에서는 5.258563초 느렸다. `_lookup`의 국소 이득과 decode 25% 감소는 보존됐지만 N=5k ON 전체 경로의 이득은 두 순서 모두 관찰되지 않았다. 이 결론은 성능 이득 미관찰에 관한 공학적 판단이며, 확정적인 성능 악화나 통계적 유의성을 뜻하지 않는다. N=100k NO-GO와 전체 T6.6F Phase B INCONCLUSIVE를 유지한다.

[실행 manifest](../../benchmarks/t66f-b05b/run-manifest.json), [기계 판독 비교](../../benchmarks/t66f-b05b/comparison-summary.json), [독립 검증](../../benchmarks/t66f-b05b/verification-summary.json), [checksum 목록](../../benchmarks/t66f-b05b/SHA256SUMS)이 원자료를 연결한다. 재취득 없이 검토할 수 있도록 두 실행의 raw JSON·HTTP 요청 기록·Flutter JSONL과 일관된 client/backend SQLite backup 네 개를 보존했다.

## 독립성과 정확한 실행 출처

이 세션의 제공 이력에는 B03/B05/B05-A 구현·후보 준비 참여가 없다. 구현 비참여 독립성은 SATISFIED이며 위임 없이 수행했다. 다른 세션의 인적 정체나 UI reasoning 설정을 외부 인증했다고 주장하지 않는다. 제품·계측·allowlist·release artifact·binding·금융 canonical bytes는 수정하지 않았다. 원 B03 IR07 감사는 재수행하지 않았고 기존 admission 폐쇄를 재개하지 않았다. 이번 pair의 성공을 최적화 전체에 대한 광범위한 독립 정확성 인증으로 확대하지 않는다.

| 층위 | 검증한 식별자 |
| --- | --- |
| 시작·종료 HEAD | `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` |
| 원 B03 payload / 기준 backend | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| B05 최적화 parent payload | `d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae` |
| B05-A 동결 payload / 최적화 실행 | `29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542` |
| 기준 engine | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| 최적화 engine | `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3` |
| 공유 Flutter lib+admission component digest | `76e438cc4aaec70c901bf3b4ec1e991c4d3f7a19a3956cd9626741e72b62ecc5` |
| 공유 client release JSON SHA | `8a2734c48f9355ba8930f75cf779d0da7c8fcdd19f297a8c3f78004e653da092` |
| 공통 합성 SQLite template SHA | `c7d03671c9a7fdaa595cdacc349164421474aed0fbbd38d69a655b804ead31dc` |

[독립 복원 기록](../../benchmarks/t66f-b05b/source-integrity.json)은 세 archive의 SHA, canonical entries digest, 중복 member·안전 경로·regular-file 여부, 파일 bytes·mode를 확인한다. 고정 Git archive 위에 B03 899개와 B05-A 905개를 각각 복원했다. B05 parent 901개도 archive 내부에서 검증했다. 나머지 고정 baseline 각2,010개의 Git blob·실행 비트를 종료 전 다시 대조했다. 실제 실행은 mutable live source를 복사한 후보가 아니다.

[사전 검증](../../benchmarks/t66f-b05b/preflight.json)은 각 backend의 실제 Python/YAML source map을 stdlib canonical JSON으로 독립 인코딩한 결과와 제품 `engine_artifact()` bytes 및 release bundle을 대조했다. engine 입력 차이는 `backend/isolated_sync/observation.py` 하나이며, 기타 차이는 역사적으로 승인된 admission/artifact/test 전이와 실험 테스트다. 기준 backend의 역사 release JSON은 `9a946c…54e`, 최적화와 공통 client의 release JSON은 `8a2734…092`이며 이 호환은 B05-A exact admission에 포함돼 있다. **engine SHA와 source payload digest를 서로 대체하지 않았다.** unknown·변조·payload를 engine으로 넣는 거부 검사도 새로 통과했다.

## 확인한 순서와 실제 완료 결과

원 B05-A [manifest](../../benchmarks/t66f-b05a/run-manifest.json)의 ordinal, raw 시작·종료 UTC와 microsecond 원문을 대조했다. `n5000-0-B-on`은 07:43:54.884966Z에 시작해 07:46:29.575258Z에 종료했고, `n5000-1-A-on`은 07:46:31.145564Z에 시작했다. 따라서 원 순서는 **B→A**, 새 순서는 **A→B**다. [사전 계획](../../benchmarks/t66f-b05b/plan.json)은 결과를 보기 전에 두 번만 고정했으며 [실행 기록](../../benchmarks/t66f-b05b/execution.json)에 실제 명령·PID·resource sample을 남겼다.

| 비교 | 실행 순서 | 기준 s | 최적화 s | 기준−최적화 s | 개선율 % |
| --- | --- | --- | --- | --- | --- |
| 역사 B05-A | B→A | 152.688187 | 153.265907 | -0.577720 | -0.378365878429 |
| 독립 B05-B | A→B | 149.743978 | 155.002541 | -5.258563 | -3.511702487295 |

개선율은 `100 × (기준초 − 최적화초) / 기준초`다. 시간은 원시 microsecond를 그대로 초로 표시했다. 위 비율은 소수12자리 표시이며 전체 decimal 계산값은 비교 JSON에 있다. 양수는 최적화가 빠르다는 뜻이다. 두 pair를 평균내어 부정적인 결과를 상쇄하거나 source당 관측2개에서 신뢰구간을 만들지 않았다.

| 실행 | 시작 UTC | 검증 포함 종료 UTC | accepted UUID | 완료/도달 객체 | 결과 |
| --- | --- | --- | --- | --- | --- |
| n5000-0-A-on | 2026-10-26T08:57:01.964202Z | 2026-10-26T08:59:33.005562Z | 4ebe39bb-cd53-48ef-8e1f-994e9f86bf3d | 20148/20,148 | E1/E2/E3/E4·독립 검증 통과 |
| n5000-1-B-on | 2026-10-26T08:59:34.956493Z | 2026-10-26T09:02:11.437592Z | 3a01b291-0843-45ee-9782-700fef2c0325 | 20148/20,148 | E1/E2/E3/E4·독립 검증 통과 |

종료 UTC는 primary 뒤의 전체 semantic 검증까지 포함한다. primary는 stopwatch의 149,743,978µs / 155,002,541µs이며, UTC 두 값의 차이로 바꾸지 않았다. backend 준비·Flutter compile·client DB 초기화와 전체 사후 oracle는 primary 밖이다. 경계는 segmented-internal 게시와 bounded accepted read이며 UI/Offline-ready 설치나 Android 단말 성능을 측정한 것이 아니다.

## 동일 cold 조건과 완료 증명

두 client는 `objects=0`, `body_bytes=0`, `generations=0`, `accepted.id=null`, `sequence=0`에서 시작했다. 서로 다른 새 디렉터리·SQLite를 사용했고 기존 staged object나 accepted generation을 재사용하지 않았다. 두 backend는 checksum을 검증한 같은 역사 합성 template에서 독립 SQLite backup으로 시작했다. 공통 template 안의 각 engine 전용 hot/context view를 선택했으며 다른 engine의 accepted DB와 객체 graph를 혼합하지 않았다. 준비된 backend view는 B05-A와 같은 측정 전제이고, 준비 generation을 cold 시간에 합산하지 않았다.

N은 ledger 전체5,000행, archive4,895행·current105행이며 기타 authority35행을 더한 authority는5,035행이다. H는 current105·기타35, hot87,364B·control3,178B로 고정했다. D는 cold에 해당하지 않아 `null`이다. engine별 실제 reachable graph는 각각20,148개·13,146,158B, index/raw/control refs는 같고 hot 한 개의 hash와 Target context/sync_root만 다르다. 동일 N만으로 객체 수·byte 크기가 같다고 가정하지 않고 oracle로 확인했다.

fixture 금융 raw digest는 `f5d7ff2a2e882377acb209f8f836223ad23b69fb86a829cec7da450fad5cab03`, ledger5,000행의 semantic digest는 `291ae2c544f13e2602fd62f615ce3da71ba40e8ff9bde2fcbcae5d7c1555c9ac`, financial state digest는 `6174fac48d00c00cf015d8dbfdfaddea67bec633c0aa099ac7b932f6a423ad22`다. 두 실행과 역사 B05-A의 값이 모두 같다. engine을 포함하는 hot의 hash 차이는 금융 state 차이가 아니다. 모바일에 금융 공식 재계산을 추가하지 않았다.

독립 oracle는 각 client/backend의 모든 reachable object hash·길이·edge와 raw rows를 순회하고, backend 실제 SQL row 및 E4에서 읽은 11개 table digest를 대조했다. native accepted pointer는 위 UUID·`previous=null`·`sequence=1`과 일치했다. 객체/staged/generation count는 모두20,148이고 `quick_check=ok`, FK 오류0이었다. backend335개 요청과 client collector가 모두 닫혔고 pending·completion error·HTTP error·만료 응답은0이다. 각 실행의 [기준 검증](../../benchmarks/t66f-b05b/raw/n5000-0-A-on/independent-verification.json)과 [최적화 검증](../../benchmarks/t66f-b05b/raw/n5000-1-B-on/independent-verification.json)에 matched backup SHA를 남겼다.

| 조건 | lease ID | validated_at | expires_at | 실제 갱신/만료 |
| --- | --- | --- | --- | --- |
| A | a98632fc-a349-4b2d-b855-ddd6935d5971 | 2026-10-26T08:57:02Z | 2026-10-26T09:12:02Z | 0 / 0 |
| B | 36674de7-8e99-4fb9-9fb0-6773e01121b5 | 2026-10-26T08:59:35Z | 2026-10-26T09:14:35Z | 0 / 0 |

실제 서버는 정상 UTC, 원900초 TTL·최대3 attempts를 사용했다. 각 실행은 새 observation201 한 번, 동일 request/observation/시각의 terminal 재확인200 한 번, release204 한 번이었다. lease 연장이 아니다. 최초 사후 집계가 manifest 응답2개를 갱신1로 잘못 센 부분은 [방법 기록](../../benchmarks/t66f-b05b/analysis-method-notes.json)에 원 metadata와 함께 보존하고 실제 갱신0으로 교정했다. raw·성능 조건·실행 횟수는 바꾸지 않았다.

지원 runtime은 CPython3.12.3/backend SQLite3.45.1, Flutter3.47.4/Dart3.13.3, client SQLite3.53.4다. client native library SHA `0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace`도 역사와 같다. `foreign_keys=ON`, `synchronous=EXTRA`, `journal_mode=DELETE`와 기존 HOST largeGraphVerification profile, backend8GiB 주소공간 한도를 유지했다. 고정 합성 credential/principal·evaluation date2026-10-05/offset540·새 HTTP pool·ephemeral loopback TLS를 사용했다. 운영18080·개발18081에는 요청하지 않았다. 시작 가용 공간은 약95.82GiB였으며 resource guard를 발동하지 않았다. 별도 Flutter/heavy benchmark와 충돌하는 프로세스는 관찰되지 않았다.

## 단계별 시간과 실제 작업량

아래 단위는 초다. E2는 초기 recovery부터 terminal release 뒤 첫 E3 metadata SQL까지의 envelope다. E1 SQL API는 E2/E3 안에 포함되며 callback 하한도 SQL API 안에 포함된다. handler·lookup·decode·HTTP도 중첩된다. **이 시간들을 합쳐 새 전체 elapsed를 만들지 않았다.** 전체 primary 시간은 위 실제 stopwatch 값이다. generation은 기존 요청 지표이며 준비된 전체 graph bootstrap 시간이 아니다.

| 측정 구간 | B05-A 기준 | B05-A 최적화 | B05-B 기준 | B05-B 최적화 |
| --- | --- | --- | --- | --- |
| 실제 Flutter cold + bounded E4 | 152.688187 | 153.265907 | 149.743978 | 155.002541 |
| E2·초기 recovery envelope | 136.934759 | 136.859718 | 134.765979 | 136.922651 |
| E1 SQL API 누적 | 19.532613 | 25.315526 | 24.994259 | 26.086545 |
| E3 envelope | 15.670200 | 16.325732 | 14.896308 | 17.991767 |
| E3 native transaction | 0.016139 | 0.016311 | 0.020342 | 0.005516 |
| E3 native readback | 0.002329 | 0.002084 | 0.004137 | 0.001838 |
| E4 bounded accepted read | 0.080307 | 0.077304 | 0.075779 | 0.085387 |
| HTTP send→body 누적 | 101.855216 | 95.740597 | 92.732616 | 94.095604 |
| backend handler 누적 | 100.495743450 | 94.165475015 | 91.239140755 | 92.785342970 |
| backend request process CPU | 100.321037236 | 93.953099388 | 91.050359854 | 92.603559737 |
| 요청 내 generation 기존 지표 | 0.289518 | 0.307001 | 0.237103 | 0.285187 |
| _lookup 누적 | 43.310018996 | 36.590073480 | 38.704526972 | 35.592554805 |
| hot body decode 누적 | 19.723485217 | 13.193669309 | 17.574797003 | 12.708559266 |
| client SQL callback 하한 | 1.114755 | 1.102742 | 1.158811 | 1.229020 |

새 두 실행은 HTTP335회·응답20,430,584B로 같았다. 각 실행의332개 object 요청 외에 observation 생성·terminal 재확인·release가 있었다. full counter와 [SQL stage 귀속](../../benchmarks/t66f-b05b/logical-counters.json), [실제 요청 기록](../../benchmarks/t66f-b05b/raw/n5000-0-A-on/server/requests.jsonl.gz)은 그대로 보존했다. client CPU tick과 peak RSS는 사후 검증·이전 실행까지 포함하므로 primary CPU나 단일 cold peak의 인과 근거로 사용하지 않았다.

| 실제 작업·논리 byte | 기준(A) | 최적화(B) |
| --- | --- | --- |
| _lookup 호출 | 667 | 667 |
| hot constructor decode | 667 | 667 |
| hot body decode | 2001 | 1334 |
| 전체 hot decode | 2668 | 2001 |
| backend JSON primary input B | 359789383 | 301517595 |
| backend hash input B | 118833034 | 118833034 |
| client primary input B | 176967697 | 176967697 |
| client hash input B | 108575771 | 108575771 |
| client SQL committed TEXT+BLOB B | 21291008 | 21291008 |
| backend SQL committed TEXT+BLOB B | 9587 | 9587 |
| objects 실제 committed BLOB B | 13146158 | 13146158 |

전체 hot decode는 constructor를 포함해2,668→2,001회, 정확히25% 줄었다. body 호출만 비교하면2,001→1,334회다. 실제 backend primary input 감소58,271,788B는 `667 × 87,364B`와 같았다. hash·client validation·SQL 작업은 동일했다. 특히 같은 engine의 역사 B05-A와 이번 B05-B에서 **client logical·SQL·backend counter map 전체가 정확히 동일**했다. 누락된 계측을 성능 이득으로 세지 않았다는 범위의 accounting sanity다. 이 byte 지표는 physical I/O·WAL·메모리 크기가 아니다.

## 순서 민감도와 자격 판단

부호 전환은 없었다. B→A와 A→B 모두 최적화가 느렸으므로 순서에 따라 최적화 우세가 뒤집혔다는 증거는 없다. ORDER SENSITIVITY는 NOT CLEARLY OBSERVED다. 다만 추가 시간 크기는0.577720→5.258563초로 달라졌다. 같은 engine의 두 관측 차이는 기준2.944209초, 최적화1.736634초였다. 역사 pair의0.577720초 차이는 이 변동보다 작고, 이번5.258563초는 각각보다 크다. source당2개뿐인 범위를 모집단 noise 한도나 악화의 유의성으로 해석하지 않는다. 순서와 시간 경과·cache/JIT·host 변동은 이 실험만으로 분리되지 않는다.

국소 이득은 두 pair에서 유지됐다. 역사 `_lookup`은43.310018996→36.590073480초로15.515914497% 줄었고, 이번에는38.704526972→35.592554805초로8.040331223% 줄었다. 따라서 새 결과도 예상한 decode 작업 감소와 일관된다. B05-A의1k OFF/ON 개선과5k OFF 개선 관측도 보존하며, 이번 두 ON 결과로 그 역사 관측을 삭제하지 않는다.

**직접 관측한 전체 경로의 변화:** 이번에는 `_lookup`이3.111972167초 줄었지만 이를 포함한 handler 전체는1.546202215초 늘었고 HTTP도1.362988초 늘었다. E2 envelope는2.156672초, E3 envelope는3.095459초, SQL API는1.092286초 늘었다. E3 native transaction 자체는 오히려0.020342→0.005516초였다. 따라서 최종 COMMIT 하나나 lookup 하나가 전체 결과를 설명한다고 할 수 없다. acquisition envelope134.8~136.9초와 handler91.2~92.8초가 큰 구간이고, E3도14.9~18.0초를 차지한다. generation0.237~0.285초는 전체를 지배하지 않는다. 이들은 중첩 계측의 동반 변화이며 합산한 원인 분해가 아니다.

**가능하지만 입증하지 못한 설명:** JIT·OS page cache·DB/native 실행·CPU scheduling·host 부하 변화가 lookup 외 작업과 E3 검증 시간을 달리했을 수 있다. OS cache를 비우거나 CPU·thermal·fsync를 별도 통제·측정하지 않았으며, SQL callback 하한1.158811→1.229020초만으로 observer CPU나 디스크 sync가 단독 원인이라고 말할 수 없다. 원 B03 counter를 수정하거나 heavyweight per-object profiler를 추가하지 않았다.

두 순서 모두 실제 경로의 개선을 보이지 않았으므로 **NO MATERIAL SYSTEM BENEFIT OBSERVED**를 선택한다. 이는 국소 최적화가 무가치하다는 일반 명제도, 다른 규모·OFF·실기기에서 이득이 없다는 증명도 아니다. 현재5k ON 근거는50k의 비싼 반복을 정당화하지 않는다. 더 많은 작은 cold A/B를 자동 추가하지 않으며, 이번에는 추가 비용 없이 실험 후보를 보존하는 결정을 택한다.50k는 NOT JUSTIFIED,100k는 계속 NO-GO이고 실제10k/50k/100k cold는 모두0회다.

## 보존·검증·정리

새 검증은 backend admission4건, Flutter exact admission·unknown 거부9건과 compile-only1건, 실제 driver1건 안의 cold2회다. frontend `npm run build`도 격리 후보에서 통과했다. 전체 backend/Flutter 회귀는 재실행하지 않았으며 역사 B05-A1904 tests·1540 subtests/영향 Flutter205 PASS를 fresh 결과로 바꾸어 부르지 않는다. 초기 frontend build는 기존 node_modules 연결 누락으로 `tsc`를 찾지 못해127로 끝났고, runtime symlink만 연결해 실측 전에 회복했다. [검증 기록](../../benchmarks/t66f-b05b/checks.json)에 원 로그를 연결했다.

[종료 보존 기록](../../benchmarks/t66f-b05b/preservation-after.json)은 기존6064개 파일의 bytes·mode·크기, Git staged path/mode/blob/stage와 원 index bytes가 그대로임을 확인한다. index의 원문 사본도 evidence에 보존했다. reset·stash·clean·checkout·restage·commit·push는 하지 않았다. 과거 B03/B04/B05/B05-A·IR07·source-lock 증거와 외부 동결 archive를 보존했고 production activation·서비스·DB·Snapshot·환경 파일을 건드리지 않았다.

[정리 기록](../../benchmarks/t66f-b05b/cleanup.json)은 모든 task server와 Flutter 종료, matched backup 검증 뒤 B05-B 단일 scratch의 5919파일·관찰 할당량560.64MiB를 제거한 결과다. 외부 runtime cache·기존 파일·활성 DB/WAL은 삭제하지 않았다. 증거는 약35.68MiB이며 최종 보고서·후속 metadata 크기는 별도다. 남은 정리 검토 대상은 없다. 원 소스 재구성은 기존 archive와 task 스크립트로 가능하고, 최종 manifest는 정리된 scratch 대신 보존된 raw/backup 경로를 가리킨다.

다음 조치는 아래 footer의 한 문장으로 제한한다.

```text
T6.6F-B05-B INDEPENDENT 5K ON REPLICATION:
PASS

AUDITOR IMPLEMENTATION INDEPENDENCE:
SATISFIED

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL AUDITED SOURCE

B05-A ADMISSION:
PASS — HISTORICAL

BASELINE ENGINE SHA:
7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c

OPTIMIZED ENGINE SHA:
f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3

B05-A FROZEN CANDIDATE:
VERIFIED

SOURCE AND ARTIFACT INTEGRITY:
PASS

ORIGINAL B05-A 5K ON ORDER:
최적화(B) → 기준(A), n5000-0-B-on → n5000-1-A-on

NEW B05-B REVERSED ORDER:
기준(A) → 최적화(B), n5000-0-A-on → n5000-1-B-on

N=5K BASELINE ON:
149.743978 s

N=5K OPTIMIZED ON:
155.002541 s

HISTORICAL B05-A BASELINE ON:
152.69 s

HISTORICAL B05-A OPTIMIZED ON:
153.27 s

HISTORICAL B05-A IMPROVEMENT:
−0.38% (원시값 기준 -0.378365878429%)

NEW B05-B IMPROVEMENT:
-3.511702487295%

TWO-ORDER COMPARISON:
두 순서 모두 기준 우세; 최적화 추가 시간 0.577720 s → 5.258563 s, 부호 전환 없음

ORDER SENSITIVITY:
NOT CLEARLY OBSERVED

ACTUAL LOOKUP DECODE COUNTS:
기준 2,668회 / 최적화 2,001회; body 2,001 / 1,334회 + constructor 각667회

LOOKUP LOCAL BENEFIT:
PRESERVED

END-TO-END PERFORMANCE DECISION:
NO MATERIAL BENEFIT

REAL FLUTTER COLD:
2/2 PASS

ACTUAL D3→HTTP→E2→E1:
PASS

E3 PUBLICATION:
PASS

E4 ACCEPTED READ:
PASS

FINANCIAL SEMANTIC EQUIVALENCE:
PASS

ENGINE-DEPENDENT HASH DIFFERENCES:
EXPLAINED

WITHIN-ENGINE COUNTER SANITY:
PASS

OBSERVATION LEASE HANDLING:
VALID — 각900초, 새 lease1개·terminal 재확인1회·갱신0·만료0, 원3 attempts 유지

MEASUREMENT COMPARABILITY:
VALID — 동일 동결 source·fixture·runtime·방법; host/cache/JIT 변동 한계 보존

N=50K FOLLOW-UP:
NOT JUSTIFIED

N=50K FULL COLD RUNS:
0

N=100K FULL COLD RUNS:
0

N=100K FEASIBILITY:
NO-GO

FULL BACKEND REGRESSION:
NOT RERUN — HISTORICAL B05-A PASS

FULL FLUTTER REGRESSION:
NOT RERUN — HISTORICAL B05-A AFFECTED PASS

PRODUCT SOURCE MODIFIED:
NO

EXACT ALLOWLIST MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B05-B:
NO

HISTORICAL EVIDENCE:
PRESERVED

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED FOR ORIGINAL AUDITED SOURCE

B04:
PASS — BOUNDED

B05-A:
PASS — ADMISSION AND REAL-PATH QUALIFICATION

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY/VFS/POWER:
NOT VERIFIED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

RUN MANIFEST:
docs/benchmarks/t66f-b05b/run-manifest.json

AUDIT REPORT:
docs/t66f-b05b-independent-5k-on-ab-replication.md

TEMPORARY ARTIFACT CLEANUP:
B05-B scratch 5919파일·할당량 560.64 MiB 정리; matched SQLite4개·raw·source 식별자 보존; 기존 파일 삭제0

FINAL VERDICT:
PASS

NEXT ACTION:
동결 최적화를 추가 고비용 측정 없이 실험 후보로만 보존한다.
```
