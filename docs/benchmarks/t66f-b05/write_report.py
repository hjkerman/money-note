"""검증된 JSON에서 한국어 B05 보고서와 필수 footer를 만든다."""
import json,pathlib
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05'
def get(n):return json.loads((E/n).read_text())
m=get('microbenchmark.json');t=get('timing-comparison.json');f=get('experimental-freeze.json');c=get('cleanup.json');q=get('qualification.json')
rows=t['backend_only'];table='\n'.join('| '+ ' | '.join([x['variant'],'ON' if x['on'] else 'OFF',str(x['objects']),str(x['lookup_calls']),str(x['hot_decode_calls_total']),f"{x['lookup_s']:.6f}",f"{x['hot_decode_associated_s']:.6f}",f"{x['backend_handler_s']:.6f}",f"{x['backend_process_CPU_s']:.6f}",f"{x['HTTP_send_to_body_s']:.6f}",f"{x['download_diagnostic_s']:.6f}",f"{x['raw_index_bootstrap_s']:.6f}"])+ ' |' for x in rows)
footer='''T6.6F-B05 LOOKUP HOT-BODY OPTIMIZATION:
PARTIAL

B05 CANDIDATE DECISION:
LOCALLY EFFECTIVE — 시스템 이득 미입증

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28 (main)

B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL FROZEN CANDIDATE

B04 BOUNDED MEASUREMENT:
PASS

BASELINE EXECUTABLE SOURCE:
8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8

OPTIMIZED EXECUTABLE SOURCE:
d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae (실험 payload)

OPTIMIZATION SOURCE FILE:
backend/isolated_sync/observation.py:ObservationRepository._lookup

OPTIMIZATION DIFF:
hot 본문을 로컬 hot_body로 한 번 decode해 기존 두 get 검사에 재사용

LOOKUP ROOT CAUSE:
정상 hot의 Object.body 중복 호출; constructor 포함4→3 decode/lookup

BASELINE DECODE INVOCATIONS:
80 hot decode /20 lookup; 수정 backend 진단528/조건

OPTIMIZED DECODE INVOCATIONS:
60 hot decode /20 lookup; 수정 backend 진단397/조건

REDUNDANT DECODE REDUCTION:
20/20 lookup; backend131/조건; 정상 lookup hot decode25% 감소

LOOKUP LOCAL TIMING:
OFF50.091808→42.538985ms (-15.08%); ON50.918436→43.002099ms (-15.55%)

SOURCE SEMANTICS:
EQUIVALENT — 동일 계약의 _lookup 집중 범위; 새 release 입장은 차단

CANONICAL BYTES:
DIFFERENT — 실제 source 간 engine metadata; 동일 계약 함수 비교 및 금융/raw 값은 IDENTICAL

IMMUTABLE OBJECT IDENTITY:
DIFFERENT — engine에 따른 hot/sync_root; 수정 진단 raw/index/control 및 같은 source ON/OFF는 IDENTICAL

ERROR/REJECTION SEMANTICS:
PRESERVED — 집중 오류·거부 및 short circuit; 새 engine은 기존 입장 가드가 거부

ON/OFF PRODUCT EQUIVALENCE:
PARTIAL — backend 그래프·금융 state 동일; 실제 client cold 미실행

B03 COUNTER SEMANTICS:
EXPLAINED WORK REDUCTION — 중복 parse/C1 재인코딩 제거; hash/SQL 동일

FOCUSED CORRECTNESS TESTS:
20 PASS; 최초 새 테스트 stage 오기1건 수정 후 통과

FULL BACKEND:
FAIL —1899 PASS/1 artifact exact-hash FAIL; 1540 subtests PASS

FLUTTER AFFECTED:
FAIL —117 PASS/41 ERROR; 미승인 engine 입장 및 후속 정리·집계

ACTUAL D3→HTTP→E2→E1:
NOT RERUN — D3/TLS만 완료, 새 engine의 client 입장 차단

E3 PUBLICATION:
NOT RERUN — 새 source 통합은 입장 단계에서 차단

E4 ACCEPTED READ:
NOT RERUN — 새 source 통합은 입장 단계에서 차단

MEASUREMENT N POINTS:
1000 (warm 함수 및 backend-only 진단)

CONTEMPORANEOUS A/B PAIRS:
backend-only2쌍 + 함수 진단4쌍; 실제 full cold0쌍

N=50K BASELINE OFF:
NOT RUN

N=50K OPTIMIZED OFF:
NOT RUN

N=50K BASELINE ON:
NOT RUN

N=50K OPTIMIZED ON:
NOT RUN

N=50K MEASURED SPEEDUP:
INCONCLUSIVE — 미측정

INSTRUMENTATION ON/OFF INTERACTION:
backend 진단 ON/OFF A1.1749, B0.9261; 변동과 overhead 분리 불가

HISTORICAL B04 N=50K OFF:
1489.49 s

HISTORICAL B04 N=50K ON:
1573.54 s

PERFORMANCE UNCERTAINTY:
warm 함수2블록/조건; backend1회/조건, OFF7.01% 악화·ON15.65% 개선; client cold 및 신뢰구간 없음

100K FULL COLD FEASIBILITY:
NO-GO

NEW N=100K FULL COLD RUNS:
0

OPTIMIZATION ADOPTION:
NOT RECOMMENDED — 정식 채택 보류, 실험 후보만 보존

NEW CANDIDATE PAYLOAD DIGEST:
d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae

NEW EXPERIMENTAL SNAPSHOT:
docs/benchmarks/t66f-b05/experimental-source.tar.gz (미자격 실험 패키지)

SNAPSHOT RECONSTRUCTION:
PASS —901파일 bytes/mode 및 engine 재계산

SOURCE-SHA GUARDS:
PASS — 기존 보호7개 및 원래 mobile exact guard 보존; 새 release admission 별도 차단

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B05:
NO

HISTORICAL EVIDENCE:
PRESERVED

BINDING PROTOCOL:
UNCHANGED

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED FOR ORIGINAL AUDITED SOURCE

B04:
PASS — BOUNDED MEASUREMENT

PHASE B FIVE-POINT GRID:
PARTIAL

E3 I25 LARGE-N SCALING:
PARTIAL

T6.6F PHASE B:
INCONCLUSIVE

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

TEMPORARY ARTIFACT CLEANUP:
B05 scratch8979파일 제거, 관찰 할당량520.85MiB; 원시 증거·backend backup8개·실험 source 보존

FINAL VERDICT:
PARTIAL — NECESSARY MEASUREMENT UNAVAILABLE

NEXT ACTION:
제시한 exact engine 허용 목록과 release artifact 갱신 범위를 명시적으로 승인한 뒤 N=1k 실제 Flutter cold A/B부터 검증한다.
'''
(E/'final-footer.txt').write_text(footer)
report=f'''# T6.6F-B05 — `_lookup` hot 본문 decode 재사용 실험

**최종 판정: PARTIAL — NECESSARY MEASUREMENT UNAVAILABLE. 후보 판단: LOCALLY EFFECTIVE, SYSTEM BENEFIT UNPROVEN.** 중복 decode는 확인·제거했고 집중 동등성20건이 통과했다. 같은 DB의 warm `_lookup` 중앙값은 OFF15.08%, ON15.55% 줄었다. 그러나 실제 client cold 수집은 새 exact engine 입장 승인 범위 밖이라 시작할 수 없었고, backend-only 진단의 OFF/ON 효과도 일관되지 않았다. 정식 채택·50k/100k 수집·전체 Phase B PASS를 권고하지 않는다. live tree의 최소 변경은 **미자격 실험 후보**로 남긴다.

[실행 manifest](benchmarks/t66f-b05/run-manifest.json)는 실제 전체 cold0건, 유효 backend 비교4조건/2쌍, 비교 무효인 최초 backend4건, warm 함수8블록, 미실행 cell을 구별한다. [자격 판정](benchmarks/t66f-b05/qualification.json)과 [인계서](benchmarks/t66f-b05/HANDOFF.md)를 함께 본다.

## 원본과 허용 범위

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. B04의 실행 source는 IR07 원본 frozen payload `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`이다. archive SHA는 `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5`;899파일/9,801,906바이트를 검증했다. baseline commit을 `git archive`로 복원하고 payload bytes/mode와 변경되지 않은 baseline inventory를 대조했다. 측정 전 live payload 차이는 없었다. B03 instrumentation은 변경하지 않았다. IR07 CLOSED는 원래 후보와 CPython3.12.3에만 적용된다.

[baseline manifest](benchmarks/t66f-b05/baseline-source-manifest.json), [초기 Git 기록](benchmarks/t66f-b05/preservation-before.json), [source 확인](benchmarks/t66f-b05/source-identity.json), [실행 source 비교](benchmarks/t66f-b05/executable-source-diff.json)에 근거한다. 격리 source167파일 비교에서 제품 실행 차이는 `backend/isolated_sync/observation.py` 하나였다. 기존 staged path/mode/blob와 index 원문 SHA, 관련 untracked 및 B04 raw hash를 보존했다. 기존 dirty `AGENTS.md`, B02/B03 서버·계측 및 Dart helper를 건드리지 않았다.

계약의 기준은 `docs/t66/c/t66c-delta-sync-protocol.md` §35·§36·E3 I25다. 전체 N은1k/5k/10k/50k/100k다. H 고정 요구에 숫자 H는 규정돼 있지 않으며, B04 실험 통제값은 current ledger105+다른 authority rows35, hot87,364B/control3,178B다. no-change D0, 카드·현금 각 한 레코드 UPDATE D1은 B04의 구체적 fixture 정의다. 이번 cold/lookup 진단의 D는 해당 없음이다. H 숫자나 성능 합격 임계값을 binding 값으로 새로 만들지 않았다.

| 요구·gate | 이번 처리 | 남은 조건 |
|---|---|---|
| 동일 source A/B | A는 B04 원본 복원, B는 최소 `_lookup` 차이 | 새로운 release engine 입장 승인 |
| 로컬 중복 제거 | 직접 primitive count, 같은 DB 교차 순서 ON/OFF | 전체 cold 영향은 별도 |
| 필수 검사·canonical/오류 보존 | 원 함수 및 독립 literal/hash 기대값20건 | 실제 새 release client 통합 |
| B03 비용 의미 | 실제 parse/C1 재인코딩 감소, 나머지 hash/SQL 대조 | E1 client 비용은 미측정 |
| 실제 N1k cold A/B | 입장 가드 차단으로 미실행 | exact allowlist/artifact 범위 승인 |
| N10k | 추가 정보 gate 미충족으로 미실행 | N1k 실제 수집 결과 |
| N50k 최대4 cold | 0회; 입장·작은 규모 전체 cold gate 미완료 | 작은 규모의 일관된 이득·자원 확인 |
| N100k full cold | 0회, 명시 제외 | 별도 실행 허가 및 개선 증거 |
| §35 전체 grid·large-N I25 | B04의 부분 결과 유지 | 부족 열·100k 직접 증거 |

실행 계획은 [execution-plan.json](benchmarks/t66f-b05/execution-plan.json)에 있다. 이는 진단 gate이며 계약에 없는 시간 임계값을 추가하지 않는다.

## 중복 작업과 최소 변경

`ObservationRepository._lookup`은 D3 transfer 입장과 응답 직전 terminal 경로에 있다. `lookup`/`roots`, `TransferRepository.acquire`, HTTP adapter terminal이 직접 연결된다. 성공 packet은 입장과 terminal의 두 lookup을 거친다. `_view_object`가 DB의 kind/body를 읽고 `Object` constructor의 C1·kind/hash 검사를 수행하며 ref/ns를 검사한다. `Object.body()`는 매번 immutable raw를 새 C1 map으로 decode한다. 정상 hot에서 constructor1회, namespace용 body1회, context용1회, projection_schema용1회로 총4회였다.

변경 전20 lookup에서 hot constructor20회/body60회, 총80회를 직접 관찰했다. hot 본문은 매번87,364B였다. [변경 전 가설](benchmarks/t66f-b05/root-cause-hypothesis.json)을 먼저 기록했다. 당시 body decode 총449.92ms/60회의 평균으로 중복 한 회당 약7.50ms가 제거 가능한 로컬 작업이라는 가설을 세웠다. 전체 cold의 최대 개선치로 환산하지 않았다. [call/decode profile](benchmarks/t66f-b05/lookup-call-decode-profile.json)과 원시 profile 두 JSON에 객체 종류별 count·크기·decode 시간이 있다. 초기 두 profile은 독립 생성 fixture이므로 matched A/B 시간 근거로 쓰지 않는다.

[최소 diff](benchmarks/t66f-b05/optimization.patch)는 hot 분기에서 `hot_body = obj.body()`를 한 번 수행하고 같은 두 `get` 검사에 사용하는 것뿐이다. 제품 파일 SHA는 `635e17038f4cc11d7db59dd6208aa1d1fbfd5a5750b04b20c40cc7714c399a3e`에서 `cb69ddaaa2fc9ab7a7336937248b3748829043dce45a07cdf216e35db11ca408`로 바뀌었다. constructor/ns 검사, context 우선 short circuit, projection 검사, raw/index/input proof, 마지막 auth/lease 검사는 유지한다. context 거부는 원래와 같은 body2회, projection 거부는3→2회다. map은 읽기만 하며 호출 내부에 머문다. 전역 cache·새 persistence·새 schema·교차 요청 mutable 공유가 없다. 예외 발생 시에도 기존 소유권 경계에 따라 해제된다.

## 정확성·source 입장과 회귀

새 [집중 테스트](../backend/tests/test_lookup_hot_body_b05.py)는 원 `_lookup` 함수의 보존본과 현재 module의 실제 globals를 사용한다. 반환값을 서로만 비교하지 않고 생성 manifest, literal 오류 code/action, stdlib SHA framing, 원 DB immutable bytes를 독립 기대값으로 확인한다. 단일/복수 객체, 같은 객체 반복 참조, 같은 길이의 다른 객체, 반복 호출·동시 호출, 이전/현재 generation, missing/hash corruption/invalid JSON/noncanonical/타입 오류, context/projection 거부, 초기·terminal auth 예외, mutable alias·객체 잔류, 성공 cold lookup 및 실제 B03 계수를 포함한다. 동일한 유효 C1 내용에 서로 다른 유효 content hash를 부여하는 경우는 정의상 불가능하다. 별도 Python 인스턴스의 같은 bytes/hash를 검사하고 다른 serialization은 거부했다.

최초 실행의19건은 통과했으며 새 비용 테스트1건은 제가 사용한 미지원 stage `lookup` 때문에 실행 오류였다. 지원되는 `transfer`로 테스트만 수정한 뒤20/20 PASS다. [최초 XML](benchmarks/t66f-b05/focused-initial.xml)과 [최종 XML](benchmarks/t66f-b05/focused.xml)을 분리 보존한다. 제품·B03 코드를 그 오류 때문에 수정하지 않았다.

전체 backend를 CPython3.12.3에서 새로 실행했다. **1,899 PASS/1 FAIL 및1,540 subtests PASS**, 1,157.99초다. 실패는 `test_release_artifact_hashes_exact_bytes_and_target` 하나다. history reproducer는 기존 IC06 방식대로 원 기대값에 맞는 역사 구현을 사용하고 출력 경로만 B05로 분리했다. 원 감사 기대값을 변경하지 않았다. [회귀 결과](benchmarks/t66f-b05/backend-regression.json), XML·압축 로그에 원문이 있다. 실패를 제외해 전체 PASS라고 쓰지 않는다.

원인은 실제 source가 들어가는 `engine_artifact()`다. 새 engine은 `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`이다. artifact manifest에서 달라진 source는 `isolated_sync/observation.py` 하나이며 versions/raw schema/projection schema/policy registry는 그대로다. 현재 mobile `ReleaseContract`는 승인된 기존 세 SHA만 허용한다. source-lock 테스트는 기존 `protocol.dart` exact SHA도 검사한다. 따라서 새 engine은 정상적으로 `UNSUPPORTED_CONTRACT`가 된다. `_lookup`·직접 테스트만 허용된 이번 범위를 mobile allowlist나 current artifact 갱신으로 확장하지 않았다. 기존 승인 선례 `docs/benchmarks/t66f-b02-a02-correction/artifact_review.py`도 새 exact hash 범위를 명시적으로 승인받았음을 기록한다.

현재 source에서 영향 Flutter를 실행한 결과117 PASS/41 ERROR다. protocol58, adapter isolation23, lineage4, source lock6, logical cost25 및 admission 전용1건이 통과했다. I25 publication30건/E4 provenance11건은 실제 backend fixture의 미승인 engine 입장 및 그 후속 teardown/집계에서 실패했다. 이 실패로 E3/E4의 동작 회귀를 입증하거나 통합 PASS를 선언하지 않는다. [suite별 결과](benchmarks/t66f-b05/flutter-affected-by-suite.json)와 압축 JSONL을 보존했다. 새 engine을 거부하고 원 baseline을 허용하는 strict guard 테스트는 PASS다. source guard7개는 기존 기대 SHA 그대로 PASS다. frontend `npm run build`도 PASS다. 변경 없는 전체 Flutter suite는 반복하지 않았다.

구체적 미적용 [승인안](benchmarks/t66f-b05/admission-proposal.json)과 [검토 diff](benchmarks/t66f-b05/admission-proposal.patch)는 새 exact SHA 하나와 기존 세 SHA 전부의 보존, current artifact2개, 직접 영향 테스트·새 B05 source-lock 기록만 다룬다. 승인 질문 후 받은 “continue”는 기존 범위의 작업 계속으로 처리했으며 추가 파일 변경 승인으로 확장하지 않았다. 이전 engine spoof·guard 해제·역사 review 갱신은 하지 않았다.

## 새 성능 진단과 불확실성

환경은 [environment.json](benchmarks/t66f-b05/environment.json)에 있다. 측정은 CPython3.12.3/backend SQLite3.45.1, Flutter3.47.4/Dart3.13.3, Linux host다. metadata를 캡처한 별도 system Python3.13.9는 측정 runtime과 분리 기록했다. 회귀가 끝난 뒤 성능 진단을 실행했다. 실제 client cold는 미실행이므로 B05 client SQLite runtime/SQL API/전체 메모리 peak는 새 측정으로 주장하지 않는다.

같은 current engine·같은 DB·같은 target에서 원 함수와 후보 함수만 교차한 [microbenchmark](benchmarks/t66f-b05/microbenchmark.json)는 A OFF→B OFF→B ON→A ON→A ON→B ON→B OFF→A OFF 순서다. 블록당10회, 조건당2블록/20회이며 installer 시간은 lookup 시간 밖이다.

| warm 함수 조건 | A 중앙값 ms | B 중앙값 ms | B−A ms | 감소율 |
|---|---:|---:|---:|---:|
| OFF | 50.091808 | 42.538985 | -7.552823 | 15.08% |
| ON | 50.918436 | 43.002099 | -7.916337 | 15.55% |

이는 동일 계약에서 알고리즘 차이를 격리한 진단이다. 실제 서로 다른 전체 source의 full cold pair는 아니다. 초기 profile의 hot80→60회 감소도 확인됐다. 별도 tracemalloc 한 번의 peak는 A2,736,466B/B2,322,846B였고 timing에 섞지 않았다. 한 host의 allocation 진단이며 Android 안전성 또는 정확한 최대 RSS 보증으로 쓰지 않는다. source상 추가 lifetime은 고정 H의 한 decoded map뿐이다.

새 source A/B의 N1k D3→실제 TLS 전송은 클라이언트 E2/E1과 분리했다. 사전에 독립 DB oracle로 만든 typed paths를 실제 auth API에 보냈다. 최초4건은 각각4,132객체를 성공 전송했지만 프로세스마다 control `exported_at`가 달라 최종 비교 assertion이 실패했다. [최초 기록](benchmarks/t66f-b05/backend-http-diagnostic-initial.json)은 **비교 무효**다. 이를 수정 결과와 섞지 않는다.

수정 진단은 동일 초기 UTC에 실제 monotonic 경과시간을 더하는 지원 clock 주입으로 시작 시각을 맞췄다. 이 시작 시각은 backend-only용 합성 UTC이며 실제 client wallclock과 비교한 실험이 아니다. 후속 실제 client cold에 이 합성 clock을 재사용하지 않는다. clock은 정지하지 않으며900초 lease와3 attempt 정책은 그대로다. 같은 synthetic auth, seed/저장 timestamp/namespace, N/H, runtime,8GiB backend 주소공간 제한, fresh DB·HTTP pool, loopback TLS 경로를 사용했다. 포트는 소유한 ephemeral listener이며 운영18080/개발18081을 사용하지 않았다. 전 조건에 같은 경량 decode/count timer를 넣었고 그 독립 비용은 분리하지 않았다. 객체별 거대한 log는 남기지 않았다. ON은 변경 없는 B03 instrumentation을 추가한다.

수정 순서는 A OFF→B OFF→B ON→A ON이다. raw/index/control ref 및 hot 금융 state는 네 조건에서 동일하고, 동일 source의 ON/OFF 전체 object set도 동일했다. 서로 다른 engine SHA가 들어가는 hot/context/sync_root는 정당하게 달라진다. 그 차이를 전체 canonical identity 동일이라고 숨기지 않는다. 원 함수/후보 함수의 같은 계약 비교에서는 전체 반환 manifest와 immutable bytes/hash가 동일하다.

아래 시간은 초다. lookup/decode/handler/HTTP는 겹치므로 더해서 전체 시간으로 만들지 않는다. 마지막 bootstrap은 모든 조건에서 **ON으로 실행한 측정 밖의 raw/index 준비**이며 OFF generation 결과가 아니다.

| source | 계측 | 객체 | lookup | hot decode | lookup s | hot decode s | handler s | backend CPU s | HTTP s | 전송 진단 s | 준비 bootstrap ON s |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{table}

전체 hot decode528→397회 중 제거된131회는 성공 lookup131회와 정확히 맞는다. 각 조건에 hot 생성 관련 고정4회도 포함돼 있으므로 전체 count와 lookup당4→3을 구별한다. 모든4조건은4,132객체를 받았고 collector가 닫혔으며 observation expiry는 없었다. [timing 비교](benchmarks/t66f-b05/timing-comparison.json), [fixture](benchmarks/t66f-b05/fixture-manifest.json), 개별 run JSON 및8개 지원 SQLite backup을 보존한다.

전송 진단은 OFF14.867066→15.909650초로 **7.01% 악화**, ON17.467165→14.733381초로 **15.65% 개선**했다. ON/OFF 비율도 A1.1749/B0.9261로 일관되지 않았다. body decode 감소가 실제 전체 request 이득과 같은 절대량으로 나타났다고 주장할 수 없다. 조건당1회이며 OS cache·호스트 변동·CPU frequency를 완전히 통제하지 못했다. backend CPU 시간과 wall 시간은 가까웠지만 이는 observer CPU 원인을 분리한 증거가 아니다. blocking DB·network·observer·scheduling 기여를 정밀 분해하지 못했다. 통계적 유의성·신뢰구간을 주장하지 않는다. 더 큰 크기로 반복해 곡선을 만들지 않았다.

실제 client E2/E1/E3/E4 시간, SQL API 시간, final accepted-generation ID는 모두 미측정/null이다. backend-only transfer 완료를 성공 cold acquisition으로 보고하지 않는다. N1k 전체 cold gate가 충족되지 않았고 backend 이득도 일관되지 않아 N10k/N50k로 상승하지 않았다. 새50k cold0회,100k cold0회다.

## 논리 비용과 B03 의미

실제 중복 validation parse를 없앤 **Case B**다. 같은 검사 결과를 한 map에서 읽어도 C1 decode가 수행하던 parse·재인코딩 관측은 실제로 한 회 줄어든다. 필수 검사 누락이나 계측 감춤으로 counter를 강제로 같게 하지 않았다.

집중 fixture hot6,211B에서는 primary 입력44,654→38,443B, calls23→22, encoding69,304→63,093B였다. hash 입력45,802B/11회와 SQL145문장은 같았다. N1k warm fixture87,364B의10 lookup ON 블록은 primary3,692,540→2,818,900B, calls230→220이다. 두 fixture 크기를 섞지 않는다.

| 수정 N1k backend ON 비용 | A | B | 해석 |
|---|---:|---:|---|
| 일반 SHA-256 입력 B | 21,949,339 | 21,949,339 | auth 별도; 입력 길이·횟수 동일 |
| primary JSON 제출/완료 B | 65,904,062 | 54,459,378 | 11,444,684B=131×87,364 감소 |
| SQL attempted TEXT/BLOB B | 1,742 / 2,893 | 1,742 / 2,893 | D3 관측 범위 동일 |
| SQL effective TEXT/BLOB B | 1,742 / 2,893 | 1,742 / 2,893 | 동일 |
| SQL committed TEXT/BLOB B | 1,742 / 2,893 | 1,742 / 2,893 | 동일 |

SQL scalar66개와 null0개도 각 구분에서 같다. scalar에 임의 byte 공식을 부여하지 않았다. [비용 표](benchmarks/t66f-b05/logical-byte-table.json)와 [해석](benchmarks/t66f-b05/logical-counter-interpretation.json)에 전체 stage별 원문 delta가 있다. observation에서1회, transfer에서130회 primary/encoding이 줄었고 나머지 계수는 동일했다. OFF logical counter는 null이며0이 아니다. 이 SQL은 D3 관측이며 client E1 또는 전체 Phase B 쓰기 비용 표를 대신하지 않는다. disk 증가·물리 I/O와 혼동하지 않는다.

## 후보·100k 판단과 남은 작업

새 실험 payload는 `{f['payload_sha256']}`,901파일/9,814,172B다. source-only [archive](benchmarks/t66f-b05/experimental-source.tar.gz)의 SHA는 `{f['archive_sha256']}`다. baseline commit+payload를 새 scratch에 복원해 모든 SHA/bytes/mode와 새 engine을 재계산했다. [freeze 기록](benchmarks/t66f-b05/experimental-freeze.json)의 reconstruction은 PASS다. 외부 B03 audit archive는 변경하지 않았으며 새 archive는 **실험용/미자격/미채택**이다. 전체 회귀 및 시스템 성능 자격을 통과한 frozen 후보로 표시하지 않는다.

현재 optimization의 정식 채택은 보류한다. 로컬 효과는 확인됐지만 필수 새 release 입장과 실제 cold A/B가 남았으며, OFF/ON backend 효과도 일관되지 않다. source diff, canonical/오류·거부 순서, 로컬 lifetime, 실제 B03 span 감소와 측정 provenance를 집중 독립 검토 대상으로 인계한다. 바뀌지 않은 instrumentation에 대해 새 설치·취소 전체 감사를 요구하지 않는다.

100k 판단은 **NO-GO 유지**다. 역사 P03은397,146/400,532 객체에서 세 window가 만료됐고 성공 E3/E4가 확립되지 않았다. 원 matched DB도 없다. 이 실패를 반복하거나 성공으로 재해석하지 않았다. 역사 B04의50k cold는 OFF1,489.494416초/ON1,573.537722초였으며 새 B05 matched control 값이 아니다. 이번 로컬·backend 진단만으로 그 full-scale 실패를 피할 whole cold 개선·renewal/progress 증거는 생기지 않았다.900초를 연장하거나3 attempt를 늘리지 않았으며 이를 임의의 전역 성능 SLA로 바꾸지 않았다. [재평가](benchmarks/t66f-b05/full-scale-reassessment.json)에 근거가 있다.

B01/B02/B03의 기존 CLOSED, B04 bounded PASS, R1 activation CLOSED를 유지한다. 전체5점 비용 grid와 large-N I25는 PARTIAL, Phase B는 INCONCLUSIVE다. Android memory/VFS/물리 I/O, hardware power loss는 NOT VERIFIED, R1 large restore는 DEFERRED, production은 NOT AUTHORIZED다. 새 `_lookup` source를 IR07 독립 통과라고 표현하지 않는다.

## 보존·정리와 다음 행동

[최종 보존 기록](benchmarks/t66f-b05/preservation-after.json)은 기존 모든 파일과 staged path/mode/blob 및 index 원문을 대조한다. 허용된 기존 파일 변화는 `observation.py` 하나이며 새 테스트·B05 증거는 별도로 보존했다. binding, mobile 구현, financial canonical 처리, Snapshot7/OfflineBaseline4, sync_root 계산, E3 authority guard-to-COMMIT, E4 provenance, P0 lineage, 관찰 제한과 production 활성화는 수정하지 않았다. commit/push/restage/checkout/reset/stash/clean 및 운영 접근은0이다.

단일 B05 scratch의 inactive 확인 후8,979파일, 관찰 할당량 {c['observed_removed_allocated_bytes']/1024**2:.2f}MiB를 제거했다. 압축 원문, fixture/source hash, 회귀 XML, 최초 실패/비교 무효 기록, source archive와 backend backup8개 약19.5MiB를 보존했다. client DB는 만들지 않았다. 기존 cache·역사 P03/P05/B03/B04 증거·frozen 후보·활성 DB/WAL은 삭제하지 않았다. [정리 기록](benchmarks/t66f-b05/cleanup.json)과 [backup hash](benchmarks/t66f-b05/retained-backend-backups.json)에 근거한다.

**다음 행동:** 제시한 exact engine 허용 목록과 release artifact 갱신 범위를 명시적으로 승인한 뒤 N=1k 실제 Flutter cold A/B부터 검증한다. 추가 승인이 필요한 이유는 현재 허용 범위가 `_lookup`와 직접 테스트뿐이며 기존 exact mobile admission/source-lock이 새 source를 거부하기 때문이다. 검토 가능한 SHA와 최소 변경 범위는 이미 `admission-proposal.json`/`.patch`에 마련했다.

## 필수 최종 기록

```text
{footer}```
'''
(R/'docs/t66f-b05-lookup-hot-body-decode-optimization.md').write_text(report)
print('한국어 보고서와 footer 작성 완료')
