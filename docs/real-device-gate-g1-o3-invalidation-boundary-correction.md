# Real-Device Gate G1-O3 — 무효화 사건 시점과 exact-hash 후속 기록 정정

**판정: PASS — F02 CORRECTION READY FOR INDEPENDENT R03 REVIEW.** 저자의 문서 정정 준비 판정이며 G1-R01-F02의 독립 종결이나 12개 기술 proof 수용이 아니다. G1 미승인·미적용, 원 F01 binding/unresolved, 운영 dispatch BLOCKED를 유지한다.

## 1. 검토한 정확 근거와 최소 수정

원 G1 제안서와 O2 candidate의 실제 file bytes를 먼저 검사했고 주어진 두 SHA와 일치했다. 불일치 중단 조건은 발생하지 않았다. [R02 보고서](real-device-gate-g1-r02-independent-contract-rereview.md)와 [정확 finding](benchmarks/real-device-gate-g1-r02/r01-finding-closure.json)의 `/findings/1/remaining_gap`에서 두 파일·pointer·원문·순서 반례·최소 수정을 확인했다.

| 후속 정정 파일 | 유일하게 정정한 pointer | 정정 |
| --- | --- | --- |
| `docs/benchmarks/real-device-gate-g1-o3/g1-contract-proposal.json` | `/formal_conditions/in_flight_definition_ko` | `commit 전에` → `무효화 전에` |
| `docs/benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json` | `/remaining_work_ko` | `commit 전에` → `무효화 전에` |

두 값의 정정 후 전문은 같다.

> 무효화 전에 같은 action/receiver/channel에 이미 제출된/버퍼링된 bytes와 remote 작업만 잔여 범위다. RESERVED만 된 action, 새 host write, 새 channel/receiver 취득·buffer 이동은 예외가 아니다.

각 successor는 O2 원문 bytes에서 해당 문자열의 `commit` 6바이트를 `무효화` UTF-8 9바이트로 한 번 바꾼 결과다. 파일당 +3바이트이며 다른 JSON 값·key/배열·메타데이터·공백은 그대로다. `SUBMISSION_COMMIT` 정의나 durable commit 언급을 전역 치환하지 않았다. [정정 map](benchmarks/real-device-gate-g1-o3/r02-f02-correction-map.json), [두 파일 patch와 전후 해시](benchmarks/real-device-gate-g1-o3/affected-artifact-hashes.json).

## 2. 사건의 시간 의미

| 시각/사건 | 구분 |
| --- | --- |
| t_I 무효화 사건 | 잔여 작업의 기준 시점. 단절·server/receiver 교체·신원 불일치·취소/권한 철회·감독/예산/증거 실패가 원인인 경우에도 이 사건 이후 신규 제출은 금지 |
| t_E 무효화 집행 효력 | 무효화가 실제 거부 장치에 반영되는 시각. 승인 비유효의 규범 기준은 t_I이며 집행 지연을 새 제출 허용의 유예로 쓰지 않음. 그 사이의 안전성도 PR04–PR07 proof 대상 |
| t_O host 관측·기록 | host가 본/기록한 시각. 실제 사건 t_I와 집행 t_E 둘 다와 구별하고 관측 지연으로 cutoff를 바꾸지 않음 |
| t_D dispatch 시도 | 논리 action을 보내려는 시도. RESERVED/host queue/Popen 생성만으로 bytes 제출이나 remote 수신이 증명되지 않음 |
| t_S SUBMISSION_COMMIT | 승인된 동일 receiver/channel로 실제 bytes 제출이 시작됐다는 기존 정의. 무효화 사건도 DB commit도 아님 |
| t_R remote task 시작 | dispatch·제출과 다른 시점. 시작만 보고 과거 제출 귀속/완료를 추론하지 않음 |
| t_C commit/durable publication | 실제 저장 효과에 관한 사건. 증거 없이는 발생/미발생을 가정하지 않으며 잔여 범위 cutoff로 사용하지 않음 |
| t_A ACK | receipt/응답 수신. 전체 task 종료나 독립 수용과 다를 수 있고 늦은 ACK는 권한을 복구하지 않음 |
| t_H host 취소 | 무효화 원인이면 그 사건을 t_I로 평가. host stop/reap은 device 정지/rollback의 증명이 아님 |

`RESERVED → SUBMISSION_COMMIT → 같은 action bytes 수신 → INVALIDATION → remote 완료 미확인`이라는 R02 반례에서 **무효화 전** 수신 bytes/작업만 잔여 범위다. 제출 시작보다 앞서 이미 제출돼야 한다는 모순을 제거했다. 사건 순서/수신자 또는 t_I 시점의 독립 완료·remote 종료가 미입증이면 UNKNOWN_QUARANTINED이고 commit/실패/취소 성공 어느 것도 추정하지 않는다.

무효화 뒤 새 제출/write/자원 취득·다른 receiver/channel로 남은 bytes 이전은 계속 금지다. 관측/집행이 늦었다는 이유로 t_I와 t_E 사이를 허용 창으로 만들지 않는다. 실제 새 제출/오대상 효과를 UNKNOWN으로 면제하지 않는다. remote task의 시작·후속 효과와 새 논리 action의 개시를 동일시하지 않으며 t_I 뒤 신규 action은 금지다.

ACK는 원 receipt대로 보존하되 결과/remote task 종료가 불명확하면 격리를 유지한다. 이미 확보한 host/선행 승인 observer 증거로 비참여자가 명시 처분하기 전에는 추가 mutation/readback/reconnect/자동 stop·clear·uninstall이 없다. 처분도 폐기된 같은 세션을 재개하지 않고 향후 허용 가능한 새 작업은 별도 owner 승인과 필수 gate를 필요로 한다. [사건 정의와 9개 정적 순서 예시](benchmarks/real-device-gate-g1-o3/invalidation-temporal-consistency.json). 이 예시는 실행한 모델/기기 시험이 아니다.

## 3. 후보 identity와 후속 기록의 적용 범위

기존 두 O2 JSON, 원안/O2 보고서·candidate·matrix/redline/양식 및 독립 R01/R02는 당시 심사한 역사 증거이므로 **덮어쓰지 않았다**. 원문 3개를 `original/`에도 보존했다. 새 O3 successor의 원 metadata/revision/time과 상대 참조는 원 O2 출처를 유지하고 별도 [effective-record-set](benchmarks/real-device-gate-g1-o3/effective-record-set.json)이 두 논리 record와 pointer만 후속 정정으로 해석하도록 명시한다. 이 대체는 미승인 제안 심사 패키지 안에서만 유효하며 binding 계약 적용이 아니다.

O2 candidate MD의 역사 hyperlink와 hash를 조용히 바꾸지 않았다. R03는 아래 동일 candidate와 O3 record-set을 함께 심사해야 한다. O2 matrix/patch/과거 PASS와 기존 pin의 pre-commit 인용은 역사 provenance이지 O3의 active 시간 규칙이 아니다.

| 문서 | 실제 SHA-256 |
| --- | --- |
| 원 G1 제안서 | `2630cbc850c3c66fb2283160315691f656335e3d5c2681d71e54c9a747218b5a` |
| 원 O2 candidate | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| 현재 candidate — 변경 없음 | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| O2 계약 JSON → O3 successor | `c26dd72ddcd0f55f66a641a400a4b51df840cb530c8e559f47a8060c8ebf7bc8` → `24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499` |
| O2 공통 판정 JSON → O3 successor | `3a585042e5115fa96df114632391d6cf82a62a73c860a771b236be18e97a6bd2` → `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` |
| O2 unsigned 양식 → O3 unsigned successor | `954363a277122c2fe405e29e22175386ce148b8f475a270f507a878a5c80d824` → `c7b0d33718bf2074cd89a8db5c27c80928ed0d2262202b27cbf8edb5236f3c5b` |

새 [미서명 양식](benchmarks/real-device-gate-g1-o3/owner-approval-template.json)은 동일 MD와 O3 계약 JSON을 승인 target으로 pin하고, O3 공통 판정/record-set·정정 근거 및 변경 없는 proof/plan/거부 기준을 실제 hash로 참조한다. 역사 인용은 별도 provenance 역할로 구분했다. owner decision·위험 수용·모든 후속 grant 필드는 원 양식과 동일한 미부여 상태다. 새 후보 MD identity나 서명/승인을 만들어내지 않았다.

## 4. 보존된 규범과 독립 종결

12개 clause object, 12개 PR obligation과 14개 RJ, SUBMISSION_COMMIT 정의·PR07 독립 조건·T10 및 PH0–PH5의 CP/IP/POST·허가식·유한 stage는 변경하지 않았다. 최초 물리 단말 결합, actual channel/recipient binding, OS 강제 격리의 세 면제 불가 보호도 그대로다. owner 잔여 위험 수용은 기술 proof가 아니다.

G1-R01-F01/F03은 R02가 독립 종결한 **문서 finding 범위**에서 보존했다. O3가 다시 독립 종결하거나 기술 수용으로 확장한 것이 아니다. G1-R01-F02는 저자가 정정했으며 R03 독립 판정 전까지 독립 OPEN 상태다. [회귀 대조](benchmarks/real-device-gate-g1-o3/normative-nonregression.json).

## 5. 정적 검증과 다음 행동

JSON syntax와 국소 Draft 2020-12 schema, finding→두 pointer 대조, 본문·두 successor·PR07/G1-09/T10의 시간 의미, F01/F03 관련 원 데이터·수용/gate/stage 보존, actual before/after byte edits와 pin/target·review input hash, HEAD/index/staged identity·역사 파일을 검증한다. schema는 두 successor의 전체 key·미변경 값을 보존하고 유일한 target pointer의 새 값만 허용하는 이 정정 전용 제약이며 기존 프로젝트 전체 schema가 있다고 주장하지 않는다. [schema](benchmarks/real-device-gate-g1-o3/successor-record-schemas.json), [최종 정적 검증](benchmarks/real-device-gate-g1-o3/final-validation.json).

AGENTS 필수 host npm/backend 검증은 task 사본·신규 합성 임시 DB에서만 수행하며 G1 기술 proof/모형/OS/Android 검증으로 집계하지 않는다. ADB(도움말 포함)·emulator·물리 기기·APK 설치·production·T6.9 작업은 0이다. G1 미승인·미적용, 원 F01 binding/unresolved, dispatch BLOCKED와 N01/F02/F03/FC01 종결을 유지하고 commit/push하지 않는다. [저장소 검증](benchmarks/real-device-gate-g1-o3/repository-validation.json).

기존 7,581개 파일과 외부 B03 sidecar 5개, HEAD·Git index·source locks·독립 감사 기록을 보존한다. 검증 scratch만 비활성/소유 확인 뒤 정리하며 기존 SDK/AVD/APK/cache/자료는 지우지 않는다. [보존](benchmarks/real-device-gate-g1-o3/preservation.json), [정리](benchmarks/real-device-gate-g1-o3/artifact-cleanup.json), [전체 exact hashes](benchmarks/real-device-gate-g1-o3/evidence-manifest.json).

**PASS — F02 CORRECTION READY FOR INDEPENDENT R03 REVIEW.** 다음 행동은 [R03 인계](benchmarks/real-device-gate-g1-o3/r03-review-handoff.json)의 동일 candidate·두 successor·무효화 사건 기준·hash package를 비참여자가 1회 정적으로 심사하는 것이다. 저자의 PASS는 독립 F02 종결이나 기기 실행 허가가 아니다.
