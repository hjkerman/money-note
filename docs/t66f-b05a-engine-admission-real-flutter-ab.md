# T6.6F-B05-A — exact engine 입장과 실제 Flutter cold A/B

**PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE.** 승인된 exact 입장·artifact 전이를 적용하고 backend 전체1,904 tests/1,540 subtests, 영향 Flutter205 tests를 통과했다. 실제 N1k8회/N5k4회 모두 새 client DB에서 E2/E1→AppState E3 publication→E4 accepted read를 완료했고 독립 canonical graph/row oracle와 native accepted pointer도 일치했다. B05의 artifact 실패와 기존 Flutter41개 실패가 해결됐다.

**모든 모드·규모의 성능 이득이 입증된 판정은 아니다.** OFF는 N1k5.75%/N5k7.12% 개선을 관찰했고 ON은 N1k5.15% 개선, N5k0.38% 악화였다. N5k ON의 반대 순서 독립 재현을 우선하며 N50k 후속은 현재 권고하지 않는다. N100k NO-GO와 전체 Phase B INCONCLUSIVE를 유지한다. production은 허가되지 않았다.

[실행 manifest](benchmarks/t66f-b05a/run-manifest.json), [전체 시간·stage 비교](benchmarks/t66f-b05a/timing-comparison.json), [자격 판정](benchmarks/t66f-b05a/qualification.json), [집중 독립 인계](benchmarks/t66f-b05a/HANDOFF.md)에 원문을 연결했다. 역사 B04/B05 시간을 새 matched control로 사용하지 않았다.

## 시작 source와 승인 경계

시작 HEAD `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch `main`이다. 기존 dirty source·untracked 증거·staged path/mode/blob 및 index 원문 SHA는 [입구 보존 기록](benchmarks/t66f-b05a/preservation-before.json)에 있다. 기준 B03 archive와 B05 archive를 독립 scratch에 복원해 각각899파일/901파일의 SHA·bytes·mode와 나머지 baseline을 검증했다. B05 live `_lookup` source는 이미 최적화된 `cb69ddaaa2fc9ab7a7336937248b3748829043dce45a07cdf216e35db11ca408`였고 B05-A에서 수정하지 않았다.

| 식별자 | 검증값·뜻 |
|---|---|
| B03 canonical payload | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| B03 archive SHA | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |
| B05 canonical payload | `d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae` |
| B05 archive SHA | `745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e` |
| baseline engine SHA | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| optimized engine SHA | `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3` |
| 새 release JSON SHA | `8a2734c48f9355ba8930f75cf779d0da7c8fcdd19f297a8c3f78004e653da092` |
| 새 B05-A payload | `29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542` |

payload digest와 engine SHA는 별개이며 allowlist에는 실제 engine SHA를 넣었다. backend/app의 재귀 Python, isolated_sync의 Python, judgment/messages YAML의 실제 bytes SHA map에 profile `isolated-d3a/1`을 붙여 C1 encode한 뒤 SHA-256을 계산한다. stdlib JSON의 독립 canonical encoder가 product `engine_artifact()` bytes와 일치했다. [입장 검토](benchmarks/t66f-b05a/admission-review.json)에 입력과 source delta가 있다.

편집 전에 B05 `admission-proposal.json`/`.patch`와 실제 의존 경로를 대조했다. 사용자 B05-A §0·§5·§6·§20의 명시적 범위로 아래 기존4파일만 바꿨다. 제품 실행 source는 protocol의 exact 상수·동등 비교 항목뿐이다. raw/projection/policy/version 계약이나 sync 계산을 변경하지 않았다.

| 허용된 기존 경로 | 이전 SHA-256 | 새 SHA-256 |
|---|---|---|
| `mobile/lib/src/segmented/protocol.dart` | `84616e8254d6959c04ca5eb50b818de66dc7cb041ca14c4def1bb89590e9be8e` | `e0488a25a3826af724276ae28a6543c52c5b115c3df0d5e9462886f88196f604` |
| `mobile/assets/segmented/isolated-release-artifacts.json` | `9a946c087a41e99f49e11cc48b581a69fca9d91da7980fe373479704aa26a54e` | `8a2734c48f9355ba8930f75cf779d0da7c8fcdd19f297a8c3f78004e653da092` |
| `docs/specimens/t66d3b-release-artifacts.json` | `9a946c087a41e99f49e11cc48b581a69fca9d91da7980fe373479704aa26a54e` | `8a2734c48f9355ba8930f75cf779d0da7c8fcdd19f297a8c3f78004e653da092` |
| `mobile/test/segmented_adapter_isolation_test.dart` | `b3bb7bcabf035a60c30a9974e8c252db1c72dbb682be40e179bc68b95939baf9` | `b748d862d3e9f79ae78f068d70d943af9c06b090154f3be978ecc08fd475ceb9` |

현재 financialEngine은 검증된 F84로 정하고, 기존7ad는 b04FinancialEngine에 그대로 보존했다. 기존 afe/f34도 유지해 exact4개만 허용한다. wildcard·prefix·동적 incoming SHA 신뢰·경고 전환은 없다. [정확한 diff](benchmarks/t66f-b05a/admission.patch), [허용 inventory](benchmarks/t66f-b05a/authorized-change-inventory.json)에 근거한다. 새 직접 테스트2개와 정적 검토·변조 witness를 추가했다. 다른 source-lock 예외는 없다.

기존 source-lock 테스트는 새 protocol exact SHA를 검사한 뒤 승인된 두 fragment를 원복해 **원래 historical protocol SHA도 다시 검사**한다. 기존 review 파일을 갱신하지 않았다. [예외 기록](benchmarks/t66f-b05a/source-lock-review.json)과 [보호 결과](benchmarks/t66f-b05a/source-guards.json)에 원래7개 보호 source, B03 counter/helper 및 `_lookup` 불변을 확인했다.

## 원 실패 분류와 artifact 일치

원 backend 실패는 `test_release_artifact_hashes_exact_bytes_and_target`였다. 체크인 bundle의 engine은7ad, 실제 최적화 source의 bundle은F84였으며 source map에서 observation.py의 SHA 한 항목만 달랐다. B03 baseline의 해당 file SHA는635e1703…399a3e, B05는cb69ddaa…1ca408이다. versions/raw schema/projection schema/policy registry 및 engine profile은 정확히 같았다. 전체 JSON 이전/새 digest는 위 파일 표에 있다. 단순히 실패한 기대값을 새 값으로 교체하지 않았다.

기존 `isolated_sync.artifacts.release_bundle()`와 A02의 JSON 직렬화 방식으로 두 current artifact만 갱신했다. 두 번 생성한 결과, B05의 사전 제안 bundle, 독립 actual source map이 모두 같았다. artifact 각 component의 declared SHA와 decoded bytes도 맞았다. [generator](benchmarks/t66f-b05a/admit.py)는 결정성·단일 source delta·불변 artifact3개를 assert한 뒤에만 적용했다. 다른 release 파일·운영 설정은 갱신하지 않았다. 이전 파일 bytes는 B05-A `before/`에 gzip으로 보존했고 원 B03/B05 archive도 보존했다.

원 Flutter raw의41개 실패는 **primary exact 입장40건, cascading 집계1건**이며 같은 테스트의 후속 teardown 오류35 event가 더 있었다. unclassified event는0개였다. 수정 전 최소 N16 재현에서도 실제 `UNSUPPORTED_CONTRACT`가 나왔다. 이를 근거 없이 전부 cascade로 취급하지 않았다. [분류 원문](benchmarks/t66f-b05a/original-error-classification.json)과 before JSONL을 보존한다. 수정 후 같은41개 테스트 이름 모두 성공했고 관련 나머지 검사도 통과했다. 새로운 독립 기능 회귀·환경 오류가 남았다고 관측하지 않았다.

## 정확성 gate

| gate | 새 결과 |
|---|---|
| baseline/optimized/old2 exact 입장 | PASS,4개 보존 |
| unknown·1문자 변조·변조 source map·payload hash 거부 | PASS |
| actual source→engine→release artifact 일치 | PASS |
| B05 집중 오류·손상·short circuit·반복/동시·generation·counter |20 PASS |
| 새 source/admission backend 및 기존 artifact 회귀 |5 PASS; 집중 합계25 |
| 전체 backend |1,904 tests +1,540 subtests PASS, 실패·skip0, exit0,1,315.37초 |
| 영향 Flutter |205 PASS, 실패·skip0, exit0,1,300.094초 |
| 보호 source/P0 fingerprint·source restoration |PASS |
| frontend npm run build |PASS |
| 별도 driver compile smoke |PASS |

[회귀 manifest](benchmarks/t66f-b05a/regressions.json), backend JUnit과 압축 로그·Flutter JSONL에 명령/cwd/결과를 남겼다. backend full 명령은 후보 `backend`에서 CPython3.12.3으로 `backend_regression.py -q -p no:cacheprovider --basetemp=<B05-A scratch>/disposable/backend-full --junitxml=<B05-A evidence>/backend-full.xml`이다. 이전 IC06의 역사 reproducer adapter는 기대값을 유지하고 출력만 B05-A로 분리했다. 전체 backend는1회만 실행했다. 영향 Flutter는 protocol/admission, adapter isolation, I25 publication, E4 provenance, lineage/source-lock, logical-cost core/boundaries/HTTP/IC01/IC02를 포함해 실제 E2/E1·async/native·E3/E4를 검사했다. 변경 없는 전체 Flutter suite를 추가 반복하지 않았다.

IR07은 **원래 B03 source와 지원 runtime에서 CLOSED**다. 새 source가 독립 IR07을 통과했다고 하지 않는다. instrumentation source는 바꾸지 않았고 그 근거는 재사용하며 직접 영향 연산만 새로 검증했다.

## 실제 cold 실험의 통제

지원 환경은 CPython3.12.3/backend SQLite3.45.1, Flutter3.47.4/Dart3.13.3, 실제 client SQLite3.53.4다. native maps와 library SHA를 [runtime 증거](benchmarks/t66f-b05a/runtime-and-reconstruction.json)에 보존했다. backend 주소공간 제한8GiB, 기존 B04 explicit HOST largeGraphVerification profile을 사용했다. production 기본 한도를 바꾸지 않았다. [계획](benchmarks/t66f-b05a/execution-plan.json)은 N1k8회, 성공 시 N5k4회, 합계12회로 고정했고 유리한 결과를 얻으려고 추가 반복하지 않았다.

N 표기는 B04 fixture의 ledger_rows다. actual authority rows는 N+35, archive ledger는 N−105다. current ledger105와 다른 authority35, hot87,364B/control3,178B를 고정했다. binding §35는 H 고정만 규정하고 숫자 H는 지정하지 않는다. 이번 workload는 cold이므로 D는 해당 없음이며0으로 위조하지 않았다. no-change/card/cash grid를 이번에 실행했다고 하지 않는다.

baseline backend는 frozen B03 복원, optimized backend는 B05 복원+승인된 admission/artifact/test 전이다. 두 engine 모두 **같은 새 exact4개 client**를 사용한다. baseline을 지원하는 명시적 compatibility 항목이 있으므로 유효하다. client component digest는 `76e438cc4aaec70c901bf3b4ec1e991c4d3f7a19a3956cd9626741e72b62ecc5`로 모든 조건에서 같다. 이를 original B03 전체 client와 byte-equivalent라고 부르지 않는다.

fixture API로 A/B의 context별 view를 만든 공통 SQLite template을 준비하고 모든 조건에 독립 backup했다. raw/namespace/저장 timestamp/auth 및 control view를 같게 했다. control exported_at 정렬을 위한 clock 주입은 **준비 단계에만** 사용했다. 실제 server는 기본 utc_now, 새900초 lease와 기존3 attempts다. cached view의 hot/context는 각 engine에 맞게 분리돼 있고 D3/클라이언트가 그 일관성을 검사했다. 금융 body를 편집하거나 old engine으로 위장하지 않았다. 모든 actual client는 objects0/current null/sequence0에서 시작했고 이전 staged DB를 재사용하지 않았다.

Backend raw/index bootstrap 및 준비 view 생성은 primary cold timing 밖이다. 모든 조건이 같은 준비 template을 사용한다. 이 준비 비용은 fixture JSON의 generation 값으로 따로 보존했으며 OFF/ON cold generation 결과에 합산하지 않았다. 실제 manifest hot generation은 요청 내 기존 `repo.metrics`로 별도 기록했다. 새 ephemeral loopback TLS, 고정 합성 credential/principal, fresh HTTP pool, 같은 runtime/resource/관찰 정책을 사용했다.18080/18081이나 production DB/.env는 쓰지 않았다.

실행 순서는 N1k에서 A OFF→B OFF→B ON→A ON / B OFF→A OFF→A ON→B ON, N5k에서 B ON→A ON→A OFF→B OFF다. A는 baseline, B는 optimized다. N1k는 조건당2회, N5k는1회다. OS cache를 비우지 않았고 host Flutter JIT/첫 실행·CPU/SQL·network 변동을 완전히 통제하지 못했다.

## 실제 완료 시간과 상태

측정 경계는 실제 `AppState.publishSegmentedForIsolatedUse`와 bounded E4 accepted read 완료다. **segmented-internal accepted publication**이며 UI/Offline-ready installation을 주장하지 않는다. 모든 실행에서 expected target, sequence1/previous null, native accepted UUID, graph/row closure, staged/committed 객체 및 FK/quick_check를 확인했다. 별도 전체 E4 raw row/financial state digest와 Python oracle는 collector close와 primary timer 뒤에 실행했다.

| N | 계측 | 조건당 반복 | A 중앙값 s | B 중앙값 s | B−A s | 관찰 감소율 |
|---|---|---:|---:|---:|---:|---:|
| 1,000 | OFF | 2 | 31.459201 | 29.648725 | -1.810477 | +5.75% |
| 1,000 | ON | 2 | 33.271270 | 31.558435 | -1.712835 | +5.15% |
| 5,000 | OFF | 1 | 152.966598 | 142.070529 | -10.896069 | +7.12% |
| 5,000 | ON | 1 | 152.688187 | 153.265907 | +0.577720 | -0.38% |

N5k의 중앙값은 singleton 값이며 p95·신뢰구간·통계적 유의성을 주장하지 않는다. N1k 네 pair는 모두 B가 빨랐지만 N5k ON으로 일반화할 수 없다. 개인 실행을 숨기거나 outlier를 제외하지 않았다.

| 실행 순서 ID | 도달 / staged / committed 객체 | 전체 완료 s | accepted UUID |
|---|---:|---:|---|
| n1000-0-A-off | 4,132 / 4,132 / 4,132 | 31.966206 | `100b3c49-60a3-4c81-ab26-3fd79c54be83` |
| n1000-1-B-off | 4,132 / 4,132 / 4,132 | 29.485876 | `ccb4510d-9cd0-4bde-9d50-1586f56a1f75` |
| n1000-2-B-on | 4,132 / 4,132 / 4,132 | 29.896952 | `ac657935-3706-4e94-a50f-6a965e60c810` |
| n1000-3-A-on | 4,132 / 4,132 / 4,132 | 32.640993 | `a3a579c5-b48e-46e2-8821-79ca8914d30c` |
| n1000-4-B-off | 4,132 / 4,132 / 4,132 | 29.811573 | `bdda985f-591b-485f-bc0e-1bc67d637e37` |
| n1000-5-A-off | 4,132 / 4,132 / 4,132 | 30.952197 | `8b345db4-686f-40db-8981-6999257227bc` |
| n1000-6-A-on | 4,132 / 4,132 / 4,132 | 33.901548 | `630f3afa-6b6c-49dd-ab01-dff1fc749c39` |
| n1000-7-B-on | 4,132 / 4,132 / 4,132 | 33.219919 | `046cefde-9915-485e-99d3-cebf767877ec` |
| n5000-0-B-on | 20,148 / 20,148 / 20,148 | 153.265907 | `982d33e5-3f61-4c59-aa07-d4073530f05b` |
| n5000-1-A-on | 20,148 / 20,148 / 20,148 | 152.688187 | `0d5badee-21d5-4a0e-839c-bf8282d5d66e` |
| n5000-2-A-off | 20,148 / 20,148 / 20,148 | 152.966598 | `476d3c3c-3de6-485a-a6a9-c4c940316373` |
| n5000-3-B-off | 20,148 / 20,148 / 20,148 | 142.070529 | `63e1fb81-fdcf-4c39-9aed-9aa0ee23f4eb` |

12/12가 정상 완료됐고 미완료0, scope completion error0, 관찰 만료·renewal0이다. 각 accepted pointer는 해당 engine의 internally consistent manifest를 가리켰다. [각 raw 디렉터리](benchmarks/t66f-b05a/raw/)의 `independent-verification.json`은 client/backend 전체 도달 hash 집합과 native pointer를 검증한다. 원본과 일치하는 matched SQLite backup24개 및 공통 template2개를 보존했다.

## stage·로컬 작업과 원인 해석

시간은 초이며 서로 겹친다. E2는 **초기 recovery를 포함한 시작→terminal release 뒤 첫 E3 metadata SQL** envelope다. exact acquire API 단독 시간으로 쓰지 않는다. E1은 원 execute/select SQL API 누적이며 E2/E3 내부에 포함된다. E3 envelope는 첫 metadata SQL→AppState 반환, native transaction/readback은 product의 별도 값이다. E4는 bounded accepted read다. backend generation도 handler 내부에 포함된다. 이 값들을 더해 가짜 전체 시간을 만들지 않는다.

| 실행 | backend generation | handler / CPU | HTTP | E2 envelope | SQL API | E3 envelope | E3 transaction / readback | E4 read |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| n1000-0-A-off | 0.174 | 18.257 / 18.194 | 18.684 | 27.545 | 5.070 | 4.327 | 0.0052 / 0.0020 | 0.0907 |
| n1000-1-B-off | 0.173 | 17.557 / 17.510 | 17.901 | 25.192 | 3.917 | 4.208 | 0.0052 / 0.0016 | 0.0847 |
| n1000-2-B-on | 0.226 | 17.978 / 17.939 | 18.292 | 25.976 | 4.099 | 3.833 | 0.0054 / 0.0016 | 0.0860 |
| n1000-3-A-on | 0.244 | 20.701 / 20.661 | 21.000 | 28.758 | 4.099 | 3.796 | 0.0054 / 0.0016 | 0.0852 |
| n1000-4-B-off | 0.181 | 18.118 / 18.074 | 18.428 | 25.598 | 3.988 | 4.123 | 0.0053 / 0.0016 | 0.0885 |
| n1000-5-A-off | 0.181 | 19.520 / 19.478 | 19.826 | 26.766 | 3.839 | 4.100 | 0.0054 / 0.0027 | 0.0846 |
| n1000-6-A-on | 0.251 | 21.097 / 21.049 | 21.393 | 30.011 | 5.083 | 3.805 | 0.0158 / 0.0016 | 0.0830 |
| n1000-7-B-on | 0.258 | 20.539 / 20.488 | 20.835 | 29.327 | 5.060 | 3.808 | 0.0166 / 0.0016 | 0.0834 |
| n5000-0-B-on | 0.307 | 94.165 / 93.953 | 95.741 | 136.860 | 25.316 | 16.326 | 0.0163 / 0.0021 | 0.0773 |
| n5000-1-A-on | 0.290 | 100.496 / 100.321 | 101.855 | 136.935 | 19.533 | 15.670 | 0.0161 / 0.0023 | 0.0803 |
| n5000-2-A-off | 0.188 | 95.124 / 94.969 | 96.465 | 133.080 | 22.070 | 19.799 | 0.0056 / 0.0016 | 0.0858 |
| n5000-3-B-off | 0.206 | 86.427 / 86.253 | 87.743 | 125.959 | 22.587 | 16.038 | 0.0159 / 0.0016 | 0.0717 |

실제 source 경로에 동일한 경량 `_lookup`/hot body timing을 양쪽 조건에 추가했다. B03 구현을 수정하지 않았다. constructor가 호출하는 C1 decode1회 및 body의 실제 decode 호출을 세고 body decode-associated wall을 측정했다. constructor hash 시간을 body decode 시간으로 오인하지 않는다.

| N | 계측 | lookup 횟수/실행 | hot 총 decode A→B | 평균 lookup ms의 반복 중앙값 A→B | body decode 누적 s A→B | 로컬 감소율 |
|---|---|---:|---:|---:|---:|---:|
| 1,000 | OFF | 161 | 644→483 | 54.637→46.955 | 4.044→2.751 | 14.06% |
| 1,000 | ON | 161 | 644→483 | 55.790→46.483 | 4.090→2.679 | 16.68% |
| 5,000 | OFF | 667 | 2668→2001 | 65.679→54.239 | 20.194→13.147 | 17.42% |
| 5,000 | ON | 667 | 2668→2001 | 64.933→54.858 | 19.723→13.194 | 15.52% |

정상 lookup은4→3 hot decode로25% 줄었다. 실제 N1k는161 lookup에서644→483회, N5k는667 lookup에서2,668→2,001회다. 이전 B05의80→60/20회는 역사 로컬 진단이며 새 actual cold count와 구별한다. 제거된 연산은 분명하지만 그 누적시간 차이가 전체 cold 차이와 반드시 같지는 않다. 동반 해시·재인코딩·GC·DB·scheduling 기여를 완전히 원인 분해하지 못했다.

N5k ON의 handler100.496→94.166초와 body decode19.724→13.194초는 줄었다. 동시에 client SQL API19.533→25.315초, E3 envelope15.670→16.326초로 늘어 전체153.266초는 baseline152.688초보다 약0.578초 느렸다. 겹치는 범위이므로 이 차이를 단순 가감해 인과 증명하지 않는다. SQL API는 blocking SQLite와 관측 비용을 함께 포함하며 SQL callback만이 원인이라고 하지 않는다. B ON이 새 Dart process의 첫 조건이었다는 warmup/order 가설도 남아 있다.

ON/OFF 비율은 N1k A1.0576/B1.0644, N5k A0.9982/B1.0788이다. N5k baseline ON이 OFF보다 약간 빠른 것 자체가 작은 표본·환경 변동을 보여준다. 이 비율을 순수 observer CPU로 해석하지 않는다. client CPU tick은 후속 semantic 검증을 포함하므로 primary CPU 비교에서 제외했다. process peak RSS도 이전 repetition과 검증을 포함한다. Android 메모리/물리 I/O/전력 안전성 근거로 쓰지 않는다.

## 금융·canonical·counter 동등성

[차이 검증](benchmarks/t66f-b05a/cross-engine-differences.json)에서 두 N 모두 persistent target 차이는 **context.financial_engine, hot_ref.hash, sync_root 세 경로뿐**이다. hot body 차이는 context.financial_engine 하나뿐이고 나머지 모든 canonical 객체 집합·bytes는 같다. raw/index/control ref와 금융 raw/semantic card/cash 및 전체 E4 financial state digest는 같다. 같은 engine의 ON/OFF target과 object set은 모두 동일하다. observation/request/accepted UUID·lease 시각은 fresh 실행별 신원이며 동일하다고 요구하지 않았다.

B03는 **EXPLAINED WORK REDUCTION**이다. 실제 중복 parse/C1 재인코딩을 제거했으므로 backend primary 입력이 lookup당 hot87,364B씩 감소한다. hash, client primary, SQL attempted/effective/committed는 같은 logical workload에서 동일했다. OFF counter는 null이며0이 아니다. caller stage를 e1로 강제 재명명하지 않았다. 객체 persistence는 원 scope의 `e2/objects/...`에 기록됐다.

아래는 각 N의 ON 첫 pair다. N1k 두 번째 pair도 같은 계수 동등성·감소량을 확인했다.

| N | 지표·scope | A | B |
|---|---|---:|---:|
| 1,000 | backend 일반 SHA 입력 B | 27,558,894 | 27,558,894 |
| 1,000 | backend primary 입력 B | 81,972,017 | 67,906,413 |
| 1,000 | client hash 입력 B | 22,880,416 | 22,880,416 |
| 1,000 | client primary 입력 B | 37,516,845 | 37,516,845 |
| 1,000 | objects committed BLOB B | 2,749,721 | 2,749,721 |
| 1,000 | SQL attempted TEXT / BLOB B | 1,946,910 / 2,754,138 | 1,946,910 / 2,754,138 |
| 1,000 | SQL effective TEXT / BLOB B | 1,669,996 / 2,754,138 | 1,669,996 / 2,754,138 |
| 1,000 | SQL committed TEXT / BLOB B | 1,669,996 / 2,754,138 | 1,669,996 / 2,754,138 |
| 5,000 | backend 일반 SHA 입력 B | 118,833,034 | 118,833,034 |
| 5,000 | backend primary 입력 B | 359,789,383 | 301,517,595 |
| 5,000 | client hash 입력 B | 108,575,771 | 108,575,771 |
| 5,000 | client primary 입력 B | 176,967,697 | 176,967,697 |
| 5,000 | objects committed BLOB B | 13,146,158 | 13,146,158 |
| 5,000 | SQL attempted TEXT / BLOB B | 9,490,460 / 13,150,581 | 9,490,460 / 13,150,581 |
| 5,000 | SQL effective TEXT / BLOB B | 8,140,427 / 13,150,581 | 8,140,427 / 13,150,581 |
| 5,000 | SQL committed TEXT / BLOB B | 8,140,427 / 13,150,581 | 8,140,427 / 13,150,581 |

N1k primary 감소14,065,604B=161×87,364, N5k58,271,788B=667×87,364다. 실제 objects committed BLOB은 모든 ON run에서 native body bytes 합과 정확히 같았다. SQL scalar/null/행 이벤트는 원 typed counter에 따로 보존하며 임의 byte 공식을 만들지 않았다. TEXT/BLOB은 logical NEW payload이며 disk file 증가·physical I/O·HTTP entity bytes가 아니다. [논리 계수](benchmarks/t66f-b05a/logical-counters.json)에 raw 연결과 stage·attempt 구분이 있다.

분석 최초 committed key 추출은 timing/metric 순서를 잘못 가정해 assertion이 실패했다. 원 helper의 실제 `.../blobBytes/committed` 순서로 추출만 수정했고 원시 값과 native DB가 일치했다. 계측 source나 측정값을 수정하지 않았고 재측정하지 않았다. [방법 기록](benchmarks/t66f-b05a/analysis-method-notes.json)에 남겼다.

## 자격·후속 판단과 source 동결

입장·정확성·실제 경로 자격은 완료됐다. 그러나 instrumented N5k 전체 이득은 미입증이므로 **PASS — QUALIFIED, SYSTEM BENEFIT DEMONSTRATED**를 사용하지 않는다. 정상 OFF의 관찰 이득 때문에 전체 최적화를 무효라고 단정하지도 않는다. wider adoption은 집중 독립 검증 대기 상태이며 실험 후보만 보존한다. 이번 실행에서 `_lookup`를 추가 최적화하거나 SQL/전체 알고리즘을 바꾸지 않았다.

N50k 후속은 현재 **NOT JUSTIFIED**다. 먼저 같은 동결 source의 N5k ON을 반대 순서 한 pair로 독립 재현해 client SQL/초기 warmup 변동과 whole-path 효과를 확인하는 것이 더 작은 작업이다. 새로운 N10k/N50k/N100k cold는 모두0회다. 역사 P03의100k397,146/400,532 실패와 B04의50k OFF1,489.49초/ON1,573.54초는 그대로 보존하며 이번 fresh control로 섞지 않는다. 작은 N의 완료로 full-scale confidence를 외삽하지 않고 **100k NO-GO**를 유지한다.900초 TTL과 attempt count는 변경하지 않았다.

새 source-only snapshot은 `/home/hjkerman/codex/audit-candidates/money-note/t66f-b05a/29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542`이다. payload `29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542`,905파일/9,820,267B이며 archive SHA는 `b239b9d277e5fd747c2f85c5577f42e203ad7a737b29317f0e23581d6b13b0f1`다. 새 빈 scratch에서905개 SHA/bytes/mode와 나머지 baseline2,010개 Git blob/실행 mode를 검증했다. 복원 `release_bundle()`이 current 두 JSON과 일치하고 engineF84가 재계산됐다. venv/build/DB/.env는 archive에 없다. [manifest](benchmarks/t66f-b05a/candidate-source-manifest.json)와 [freeze](benchmarks/t66f-b05a/freeze.json)를 따른다.

후속 독립 검토는 decode 재사용·오류/거부 순서·bounded lifetime, exact4개 admission·artifact/원복 source-lock, actual byte/semantic 동등성 및 측정 provenance에 집중하면 된다. 새 source가 IR07 독립 통과한 것은 아니며 변경하지 않은 instrumentation의 설치·취소 lifecycle 전체 감사를 다시 요구하지 않는다.

## Git·증거 보존과 정리

[최종 보존 기록](benchmarks/t66f-b05a/preservation-after.json)은 기존 path의 변화가 승인된 네 경로뿐임을 확인한다. old B03/B04/B05 report/raw/archive, staged path/mode/blob와 index 원문, HEAD/branch가 보존됐다. 기존 `_lookup`와 B03 instrumentation도 entry bytes 그대로다. binding, 금융 source, Snapshot7/OfflineBaseline4, sync_root 계산, E3 authority guard-to-COMMIT, E4 provenance, P0 규칙, production activation은 수정하지 않았다. reset/stash/clean/checkout/rebase/restage/commit/push 및 배포는 없었다.

소유 프로세스와 열린 fd가 없는 것을 확인한 뒤 B05-A scratch9,104파일, 관찰 할당량866.07MiB를 제거했다. matched client/backend backup24개, template2개, native runtime library, 압축 raw/회귀 결과 및 source freeze를 보존했다. evidence는 정리 시 약107.6MiB였다. 기존 파일·cache·역사 증거·활성 DB/WAL 삭제0이다. [정리 기록](benchmarks/t66f-b05a/cleanup.json), [보존 backup SHA](benchmarks/t66f-b05a/retained-backups.json)에 근거한다.

B01/B02는 CLOSED, B03는 원 audited source에서 CLOSED, B04는 bounded PASS다. 전체 Phase B grid/I25 large-N 및 Android memory/VFS/power loss를 이번 결과로 승격하지 않는다. Phase B INCONCLUSIVE, R1 activation CLOSED, large restore DEFERRED, production NOT AUTHORIZED를 유지한다.

**다음 작업:** 동결 B05-A 후보의 N=5k ON A/B를 반대 순서로1쌍 독립 재현한다.

## 필수 최종 기록

```text
T6.6F-B05-A ENGINE ADMISSION AND REAL FLUTTER A/B:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28 (main)

ADMISSION AUTHORIZATION SCOPE:
COMPLIANT

ORIGINAL B03 SOURCE:
PRESERVED

B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL SOURCE

B05 OPTIMIZATION:
FUNCTION-LOCAL DECODE REUSE

BASELINE ENGINE SHA:
7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c

OPTIMIZED ENGINE SHA:
f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3

BASELINE CANDIDATE PAYLOAD SHA-256:
8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8

OPTIMIZED B05 PAYLOAD SHA-256:
d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae

EXACT ALLOWLIST UPDATE:
PASS — 새 exact1개 추가, 기존3개 보존

UNKNOWN ENGINE REJECTION:
PASS — unknown/변조/source mutation/payload SHA 거부

RELEASE ARTIFACT CONSISTENCY:
PASS

ORIGINAL BACKEND HASH FAILURE:
RESOLVED

ORIGINAL FLUTTER 41 ERRORS:
RESOLVED — 동일41개 이름 모두 PASS

FULL BACKEND:
PASS —1904 tests/1540 subtests; 실패·skip0

FLUTTER AFFECTED:
PASS —205 tests

N=1K BASELINE OFF:
31.459202 s —2회 중앙값

N=1K OPTIMIZED OFF:
29.648725 s —2회 중앙값

N=1K BASELINE ON:
33.271271 s —2회 중앙값

N=1K OPTIMIZED ON:
31.558436 s —2회 중앙값

N=1K REAL COLD A/B:
COMPLETE —8/8

N=5K REAL COLD A/B:
COMPLETE —4/4

ACTUAL E3 PUBLICATION:
PASS —12/12

ACTUAL E4 ACCEPTED READ:
PASS —12/12

CROSS-ENGINE SEMANTIC EQUIVALENCE:
PASS

WITHIN-ENGINE ON/OFF EQUIVALENCE:
PASS

CANONICAL FINANCIAL DATA:
PRESERVED

ENGINE-DEPENDENT OBJECT IDENTITIES:
DIFFERENCES EXPLAINED — context.engine/hot_ref.hash/sync_root만 차이

B03 COUNTER SEMANTICS:
EXPLAINED WORK REDUCTION

LOOKUP DECODE REDUCTION:
lookup당 hot4→3,25%; N1k644→483/N5k2668→2001회

LOOKUP LOCAL PERFORMANCE:
실제 path 평균 lookup 중앙값:1k OFF54.637→46.955ms/ON55.790→46.483ms
5k OFF65.679→54.239ms/ON64.933→54.858ms

END-TO-END COLD SPEEDUP:
1k OFF5.75%/ON5.15%;5k OFF7.12%/ON-0.38%

MEASUREMENT UNCERTAINTY:
1k조건당2회/5k1회; JIT/cache·SQL API 변동; 유의성·전체 규모 이득 미주장

N=50K FOLLOW-UP:
NOT JUSTIFIED —5k ON 반대 순서 재현 우선

N=50K FULL COLD RUNS:
0

N=100K FULL COLD RUNS:
0

N=100K FULL-SCALE FEASIBILITY:
NO-GO

OPTIMIZATION ADOPTION:
AWAITING INDEPENDENT QUALIFICATION — 실험 후보만 보존

SOURCE-SHA GUARDS:
PASS — 기존7개 및 protocol 원복 SHA 검사 유지

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B05-A:
NO

HISTORICAL EVIDENCE:
PRESERVED

BINDING PROTOCOL:
UNCHANGED

PRODUCTION ACTIVATION:
NOT AUTHORIZED

NEW CANDIDATE MANIFEST:
docs/benchmarks/t66f-b05a/candidate-source-manifest.json

NEW EXPERIMENTAL SNAPSHOT:
/home/hjkerman/codex/audit-candidates/money-note/t66f-b05a/29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542

TEMPORARY ARTIFACT CLEANUP:
B05-A scratch9104파일/관찰 할당량866.07MiB 제거; matched DB24개/template2개/source snapshot·raw 보존

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED FOR ORIGINAL AUDITED SOURCE

B04:
PASS — BOUNDED

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY/VFS/POWER LOSS:
NOT VERIFIED

R1 ACTIVATION:
CLOSED

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE

NEXT ACTION:
동결 B05-A 후보의 N=5k ON A/B를 반대 순서로 1쌍 독립 재현한다.
```
