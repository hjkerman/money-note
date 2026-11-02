# Real-Device Gate G1-R03 — 무효화 시점 정정 독립 종결 검토

**최종 판정: PASS — G1-R01-F02 INDEPENDENTLY CLOSED; G1 CONTRACT READY FOR OWNER DECISION.** G1-R01-F02의 문서 결함을 독립 종결한다. 기존 G1-R01-F01·F03 독립 종결도 보존한다. 이 PASS는 정확히 식별된 제안 패키지의 소유자 결정 준비만 의미하며 G1 승인·적용, 필수 기술 proof 수용, 원 F01 구현 문제 해결 또는 기기 실행 허가가 아니다.

## 1. 독립성·범위

원 G1-R01/R02 독립 검토 세션을 이어 사용했다. G1-O3 및 원 제안 작성·관련 구현에는 참여하지 않았으며 독립성은 **SATISFIED**다. 이번 범위는 변경 없는 O2 MD, 두 O3 successor, exact-hash provenance/미서명 승인 참조와 F01/F03 종결 보존에 한정했다. 직접적인 새 모순이 없어 전체 12개 조항 심사를 재개하지 않았다.

AGENTS와 산출물 관리 규칙을 다시 읽고, 이미 읽은 project-state/domain-model/known-issues·architecture 및 O2 후보의 bytes가 R02와 같음을 확인했다. [O3 수정 보고서](real-device-gate-g1-o3-invalidation-boundary-correction.md), [R02 원 지적](real-device-gate-g1-r02-independent-contract-rereview.md), 원 PR07/G1-09·두 successor·record-set·승인 양식을 대조했다. 저자의 schema/자체 PASS를 독립 안전 판정으로 사용하지 않았다.

문서/JSON/해시/정적 사건 순서만 검사했다. 제품·시험/devicegate 모듈 import, ADB(도움말 포함), emulator, 물리 기기, APK 설치, backend/API·OS 정책·T6.9 작업은 모두 0이다. 문서 전용 범위가 일반 AGENTS build 권고보다 우선하므로 npm/backend 검증도 새로 실행하지 않았다. O3의 과거 host 검증 결과를 기술 proof나 이번 실행 결과로 집계하지 않는다.

## 2. 후보·후속 기록의 정확 신원

| 대상 | 실제 검증된 SHA-256 |
| --- | --- |
| docs/real-device-gate-g1-o2-corrected-proposal.md | e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279 |
| docs/benchmarks/real-device-gate-g1-o3/g1-contract-proposal.json | 24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499 |
| docs/benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json | 99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338 |
| O3 effective-record-set.json | 671185f6cd585125bb78225d4c9fa1a631818f149f33ba1c20261a84791a6053 |
| O3 unsigned owner-approval-template.json | c7b0d33718bf2074cd89a8db5c27c80928ed0d2262202b27cbf8edb5236f3c5b |

세 기대 hash가 실제 bytes와 모두 일치했다. O2 후보 MD는 변경되지 않았다. 각 successor는 O2 원본에서 지정된 한 pointer의 `commit 전에`를 `무효화 전에`로 한 번 바꾼 결과이며 파일당 +3바이트다. 나머지 값·key/배열·공백·metadata는 동일하다. 계약 조항 배열, SUBMISSION_COMMIT 정의와 PR07 독립 수용 조건도 그대로다.

| 후속 기록 | 유일한 변경 pointer | 전후 bytes |
| --- | --- | --- |
| docs/benchmarks/real-device-gate-g1-o3/g1-contract-proposal.json | /formal_conditions/in_flight_definition_ko | 10280 → 10283 |
| docs/benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json | /remaining_work_ko | 5166 → 5169 |

R01/R02/O2/O3 manifest 4개 참조 108개와 path/hash 참조 77건을 실제 파일에 대조했다. 원문 사본 3개, R02가 심사한 O2 JSON 34개와 보호 source 9개도 같은 hash다. 이 수치는 파일 대조 건수이며 안전 증명 분모가 아니다. [독립 정적 대조](benchmarks/real-device-gate-g1-r03/static-provenance-validation.json), [신원 산출물](benchmarks/real-device-gate-g1-r03/candidate-and-successor-hashes.json).

## 3. 무효화 사건의 의미와 원 반례 판정

두 successor의 정정 후 잔여 작업 정의는 정확히 같다.

> 무효화 전에 같은 action/receiver/channel에 이미 제출된/버퍼링된 bytes와 remote 작업만 잔여 범위다. RESERVED만 된 action, 새 host write, 새 channel/receiver 취득·buffer 이동은 예외가 아니다.

[O2 본문 150행](real-device-gate-g1-o2-corrected-proposal.md#8-pr07g1-09의-공통-제출-경계와-진행-중-무효화--o2-f02)의 무효화 전 경계와 [계약 JSON](benchmarks/real-device-gate-g1-o3/g1-contract-proposal.json)의 `/formal_conditions/in_flight_definition_ko`, [공통 판정 JSON](benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json)의 `/remaining_work_ko`가 같은 사건을 가리킨다. 원래 제출 시작 전의 이미 제출된 작업만 요구하던 모순은 없어졌다.

| 사건 | 구별된 의미 |
| --- | --- |
| t_I / INVALIDATION_EVENT | 연결/transport/receiver/server/신원·권한·감독·예산/증거 사건으로 해당 승인이 무효가 되는 기준 사건. 잔여 범위 cutoff이며 제출 시작/저장 commit으로 대체하지 않는다. |
| t_E / INVALIDATION_ENFORCEMENT_EFFECTIVE | 해당 무효화가 집행 장치의 실제 거부 상태에 반영되는 시각. 규범상 승인 비유효의 기준은 t_I이며 t_E로 늦추지 않는다. t_I..t_E에 새 제출/write/자원 취득을 허용하는 유예는 없고 지연 구간의 안전성도 PR04–PR07의 미수용 proof 대상이다. |
| t_O / HOST_OBSERVATION_OR_JOURNAL | host가 사건을 관측하거나 기록한 시각. 실제 사건 t_I 및 집행 시각 t_E와 각각 다르며 관측/기록 지연이 어느 cutoff도 바꾸지 않는다. |
| t_D / MUTATION_DISPATCH_ATTEMPT | 논리 action의 전송 시도. PREPARED/RESERVED/Popen/host queue는 실제 수신자에 bytes가 제출된 증거가 아니다. |
| t_S / SUBMISSION_COMMIT | 고정 승인 receiver/channel에 실제 bytes 제출이 시작됐음이 입증되는 기존 정의. t_I와 다르고 이 이름의 commit은 DB commit이 아니다. 원 정의를 그대로 보존한다. |
| t_R / REMOTE_TASK_START | 원격 task 시작. t_D/t_S와 동일시하지 않으며 시작 시각만으로 실제 제출 순서/수신자 귀속이나 완료를 추론하지 않는다. 새로운 논리 작업이 t_I 뒤 시작됐다면 기존 승인으로 허용하지 않는다. |
| t_C / DURABLE_COMMIT_OR_PUBLICATION | 원격 저장 또는 durable publication 사건. 실제 증거가 없는 상태에서 발생/미발생을 가정하지 않는다. 이후 완료 이력의 사실일 수 있지만 잔여 범위 cutoff가 아니다. |
| t_A / REMOTE_ACKNOWLEDGEMENT | 응답/receipt 수신. 전체 task 종료/독립 수용과 다를 수 있고 뒤늦은 ACK가 권한을 복구하지 않는다. |
| t_H / HOST_CANCELLATION | host 취소가 무효화 사건의 원인이면 그 사건이 t_I다. host 자식 종료/reap은 device-side 정지나 rollback의 proof가 아니다. |

실제 무효화 사건 t_I가 규범 cutoff다. 집행 반영 t_E나 host 관측 t_O까지 새 전송을 허용하는 유예가 없다. SUBMISSION_COMMIT(t_S)은 고정 receiver/channel로 실제 bytes 제출이 시작됐다는 증거이며 durable commit(t_C)이나 무효화가 아니다. remote task 시작·저장 효과·ACK도 서로 다른 사건으로 보존한다. 이 사건 순서/actual recipient를 강제·입증할 수 있는지는 여전히 미수용 PR04–PR07 기술 proof다.

| 독립 정적 이력 | 필수 분류 |
| --- | --- |
| 무효화 → 미전송이 입증된 dispatch 시도 | 잔여 작업 없음. 새 제출 거부, NOT_SUBMITTED·REVOKED. 미전송이 입증되지 않으면 UNKNOWN_QUARANTINED. |
| RESERVED → 무효화 → bytes 미전송 | 예약은 제출 증거가 아니며 잔여 작업 예외가 아니다. 이후 전송 0, 같은 세션 복귀 없음. |
| SUBMISSION_COMMIT → 같은 action bytes 수신 → 무효화 → remote 완료 미확인 | 무효화 전 동일 action/receiver/channel의 bounded bytes와 작업만 잔여 범위. UNKNOWN_QUARANTINED, 추가 제출/write/자원 취득 0. 원 R02 반례가 일관되게 분류됨. |
| 제출 → remote task 시작 → 무효화 → durable commit·완료 미확인 | 무효화 전 제출된 기존 작업만 보존한다. 저장 commit/실패/취소 완료를 추정하지 않고 UNKNOWN_QUARANTINED. |
| 제출 → durable commit 관측 → 무효화 → 전체 task 종료 미확인 | durable commit은 전체 task 종료나 권한 수용이 아니다. 알려진 사실은 보존하되 UNKNOWN_QUARANTINED. |
| 제출 → ACK → 무효화 → remote task 종료 미확인 | ACK receipt는 보존하고 remote task는 UNKNOWN, 세션은 UNKNOWN_QUARANTINED. ACK로 권한 복구 불가. |
| 제출 → 무효화 또는 host 취소/stop/reap → 늦은 ACK·기존 remote 작업 지속 | host 자식 회수와 device task 종료를 분리한다. 확보한 증거로 독립 처분할 때까지 UNKNOWN_QUARANTINED이며 같은 폐기 세션은 재개하지 않는다. |
| 실제 무효화 t_I → 새 host write/새 자원 취득 → 늦은 집행 t_E/관측 t_O | 허용 유예가 아니라 PR07 위반이다. FAIL_VIOLATION 및 격리로 분류하고 UNKNOWN으로 면제하지 않는다. |
| 제출 시작과 무효화의 순서 또는 actual receiver 귀속 불명 | 잔여 범위 성립을 추정하지 않는다. UNKNOWN_QUARANTINED, 후속 mutation/readback/reconnect 없음. 오대상 효과/새 제출 위반은 별도 실패다. |

위 표는 독립 문구 해석이며 실행된 모형/기기 시험이 아니다. 특히 원 R02 반례인 `RESERVED → SUBMISSION_COMMIT → 같은 action bytes 수신 → INVALIDATION → remote 완료 미확인`은 무효화 전 동일 수신자에게 제출된 기존 작업만 잔여 범위로 인정하고 **UNKNOWN_QUARANTINED**로 분류한다. 무효화 때 독립 완료/종료가 확인되지 않은 작업을 취소 성공·실패·미commit으로 추정하지 않는다. 늦은 ACK 또는 durable commit 관측도 전체 task 종료나 권한 복구가 아니다.

host stop/reap은 N01의 자식 회수 의무이며 device-side 작업 정지/rollback의 증거가 아니다. 기존 작업의 후속 효과와 새로운 논리 action의 개시는 구별되고 무효화 뒤 새 mutation·host write·자원 취득·다른 채널로 buffer 이전은 계속 금지다. 실제 위반을 UNKNOWN으로 면제할 수 없다. 격리 후 추가 readback/reconnect/자동 device stop/clear/uninstall 없이 이미 확보한 증거로만 비참여자가 처분하며, 그 처분도 폐기된 같은 세션을 재개하지 않는다.

**INVALIDATION-TIME SEMANTICS: CONSISTENT. PR07 / G1-09: CONSISTENT.** [시간 의미와 독립 순서 평가](benchmarks/real-device-gate-g1-r03/invalidation-semantics-review.json).

## 4. PR07/G1-09와 원 F01의 보존·F02 종결

원 G1-09부터 이미 수신된 작업의 후속 완료 가능성과 새 action 제출 금지를 구별하고 UNKNOWN·자동 replay/cleanup 금지를 요구했다. O2 PR07은 다른 대상 효과=0·무효화 뒤 새 제출/write/자원 취득=0·시도≤1·host 자식 회수를 명시했다. O3는 이 의무·실제 sink/bytes/순서 proof·비면제 조건을 한 글자도 바꾸지 않고 잘못된 잔여 범위 cutoff만 본문에 맞췄다. 새로운 예외나 하드 실시간 remote 정지 보증을 만들지 않는다.

원 F01의 신원/mutation 원자 결합과 세대 변경 시 권한 비승계 요구는 그대로 binding/unresolved다. 이번 문서 finding의 종결을 그 구현 문제의 해결로 표현하지 않는다. 최초 물리 단말 binding, actual channel/recipient binding, OS 강제 격리는 여전히 면제 불가이며 잔여 위험 수용은 proof가 아니다.

R02의 최소 수정과 수용 기준인 두 pointer 통일·제출 전/예약 후/기존 수신 후 무효화 이력의 일관 분류·새 제출 금지·미확인 remote UNKNOWN/격리·관련 hash 갱신·역사 보존을 충족했다. **G1-R01-F02: INDEPENDENTLY CLOSED.** 이 처분은 원 R01/R02 문서 결함에만 한정하며 실제 기술 proof 수용은 **0/12**다. [종결 기록](benchmarks/real-device-gate-g1-r03/f02-independent-closure.json).

## 5. F01/F03 종결과 기록 참조의 보존

| 기존 문서 finding | R03 처분 | 보존 근거 |
| --- | --- | --- |
| G1-R01-F01 | INDEPENDENTLY CLOSED — PRESERVED | 종결 근거인 O2 proof/phase/gate 및 finite stage 입력의 actual hashes와 해당 조항 배열이 그대로다. 두 잔여 작업 문구의 정정은 수집/수용/owner 분리나 유한 앱 검증 경로를 변경하지 않는다. 직접적인 모순이 없어 전체 계약 검토를 재개하지 않았다. |
| G1-R01-F03 | INDEPENDENTLY CLOSED — PRESERVED | 종결 근거인 O2 proof/phase/gate 및 finite stage 입력의 actual hashes와 해당 조항 배열이 그대로다. 두 잔여 작업 문구의 정정은 수집/수용/owner 분리나 유한 앱 검증 경로를 변경하지 않는다. 직접적인 모순이 없어 전체 계약 검토를 재개하지 않았다. |

F01의 CP/IP/POST·수집/기계/독립 수용/owner grant 구분과 첫 설치/후속 checkpoint, F03의 유한 host/lab/emulator/실제 앱 lifecycle·중단 및 D/E2/E4 수용 경로는 변경되지 않았다. hash·원문 불변 확인과 정정의 의미 범위만 대조했으며 전체 계약 재감사를 수행했다고 집계하지 않는다. N01/F02/F03/FC01 기존 독립 종결과 중앙 dispatch 거부 source의 hash도 보존됐다. [기존 finding 비회귀](benchmarks/real-device-gate-g1-r03/prior-findings-nonregression.json).

같은 revision/time/상대 경로를 가진 successor를 새 owner 승인으로 오인하지 않도록 [effective-record-set](benchmarks/real-device-gate-g1-o3/effective-record-set.json)은 두 논리 record/pointer만 O3로 해석하고 나머지 상대 참조의 기준을 O2 directory로 지정한다. 변경 없는 MD의 기존 hyperlink는 역사 위치를 유지한다. O2 원 JSON·matrix·patch·옛 승인 pin 및 R01/R02의 `commit 전` 인용은 역사 provenance이며 active 시간 규칙을 덮지 않는다. 이 대체는 미승인 제안 검토 패키지 안에서만 유효하고 binding 계약 적용이 아니다.

새 [unsigned 승인 양식](benchmarks/real-device-gate-g1-o3/owner-approval-template.json)은 동일 MD와 O3 계약 JSON을 target으로 pin하고, 새 공통 판정·record-set·정정 근거와 변경 없는 proof/plan/거부 기준의 실제 hash를 active 입력으로 고정한다. 원 양식/옛 JSON은 별도 historical provenance다. owner decision·비면제 proof 목록·모든 후속 grant는 O2와 동일한 미부여 상태이고 서명/승인을 만들지 않았다.

## 6. 소유자 결정 준비와 실행 경계

**OWNER DECISION READINESS: READY**는 검증된 **O2 MD + O3 record-set·두 successor + exact-hash 승인 입력**의 결합에 대한 판정이다. MD 파일 하나만으로 역사 O2 JSON의 오기가 고쳐졌다고 주장하지 않는다. 원 G1-R01의 세 문서 finding은 모두 독립 종결됐고 이 한정 검토에서 새 차단 모순이나 보호 약화는 발견하지 못했다.

소유자는 기각·한정 수정·조건부 설계 채택 여부를 별도로 결정할 수 있다. exact 규범 목적지·redline·원 F01 대체 범위·효력 시점·통제된 적용이 지정/승인되기 전 기존 규범은 바뀌지 않으며 현재 목적지는 UNDECIDED다. 설계 채택·규범 적용·구현/검증 승인·독립 기술 proof 수용·owner 연결/첫 mutation 허가는 서로 별개다. 이번 PASS는 어느 단계도 승인하거나 자동 예약하지 않는다. 운영 ADB dispatch와 기기 접근은 계속 차단한다. [결정 준비 평가](benchmarks/real-device-gate-g1-r03/owner-decision-readiness.json).

## 7. 보존·산출물

| 기준선 | 확인 신원 |
| --- | --- |
| head | ebcbd54d90eeee194a04b9eea6367f446ee2fd28 |
| branch | refs/heads/main |
| index_sha256 | 33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b |
| stage_sha256 | 9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f |

기존 파일 7,614개(838,320,772바이트)와 외부 frozen B03 sidecar 5개의 bytes/mode/symlink를 전후 대조했다. 기존 tracked 변경 13개와 미추적 자료는 이 작업이 만든 변경이 아니다. 원안/O2 후보·O3 successor/양식·PREP/R01/R02/O2/O3 역사 증거·source locks·원 B03를 보존했다. 새 파일은 이 보고서와 R03 디렉터리에만 있다. [보존 결과](benchmarks/real-device-gate-g1-r03/preservation.json), [최종 정합 검사](benchmarks/real-device-gate-g1-r03/final-validation.json).

필수 JSON 5개와 정적 provenance·시작/종료 보존·manifest·문서 helper를 남겼다. 새 build/DB/benchmark/scratch는 없고 대형 임시 산출물 정리/회수량은 NOT APPLICABLE이다. 기존 cache·자료를 삭제하지 않았고 reset·stash·clean·checkout·rebase·restage·commit·push도 수행하지 않았다. B03 금융/동기화·production configuration은 불변, T6.9 DEFERRED, formal T6.6F closure NOT AUTHORIZED, R1 CLOSED, production deployment NOT AUTHORIZED를 유지한다.

## 8. 단 하나의 다음 행동

소유자는 변경 없는 O2 후보와 O3 후속 기록의 정확 해시 묶음을 대상으로 G1 기각·수정·조건부 설계 채택 여부를 별도로 결정한다.

## 9. 필수 최종 상태

```text
REAL-DEVICE GATE G1-R03:
PASS

G1-R01-F01:
INDEPENDENTLY CLOSED — PRESERVED

G1-R01-F02:
INDEPENDENTLY CLOSED

G1-R01-F03:
INDEPENDENTLY CLOSED — PRESERVED

O2 CONTRACT SHA-256:
e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279

O3 SUCCESSOR JSON HASHES:
Contract JSON: 24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499
PR07/G1-09 JSON: 99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338

INVALIDATION-TIME SEMANTICS:
CONSISTENT

PR07 / G1-09:
CONSISTENT

HISTORICAL EVIDENCE:
PRESERVED

OWNER DECISION READINESS:
READY

G1 APPROVAL:
NOT GRANTED

G1 APPLICATION:
NOT PERFORMED

MANDATORY TECHNICAL PROOFS ACCEPTED:
0 / 12

ORIGINAL F01:
BINDING — UNRESOLVED

ADB OPERATIONAL DISPATCH:
BLOCKED

PHYSICAL DEVICE ACCESSED:
NO

REAL-DEVICE EXECUTION AUTHORIZATION:
NOT GRANTED

GIT INDEX:
PRESERVED

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
PASS — G1-R01-F02 INDEPENDENTLY CLOSED; G1 CONTRACT READY FOR OWNER DECISION

NEXT ACTION:
소유자는 변경 없는 O2 후보와 O3 후속 기록의 정확 해시 묶음을 대상으로 G1 기각·수정·조건부 설계 채택 여부를 별도로 결정한다.
```
