# Real-Device Gate G1 — 조건부 설계 채택 기록과 규범 적용 계획

**소유자의 조건부 설계 채택 결정을 기록했다. 지정한 세 산출물의 실제 SHA-256이 모두 일치하고, G1-R03의 문서 finding 종결도 확인했다.** G1은 향후 구현 계획과 기술 증명 자격검증을 준비하는 승인된 설계 기준이다. 구속 계약 적용·구현·검증 캠페인·기기 접근은 승인되지 않았다. 원 F01은 계속 유효하고 미해결이며 운영 ADB dispatch는 차단한다.

## 1. 정확한 승인 대상과 근거

| 소유자가 지정한 승인 대상 | 실제 검증한 SHA-256 |
| --- | --- |
| [G1-O2 수정 후보](real-device-gate-g1-o2-corrected-proposal.md) | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| [G1-O3 계약 후속 JSON](benchmarks/real-device-gate-g1-o3/g1-contract-proposal.json) | `24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499` |
| [G1-O3 PR07/G1-09 후속 JSON](benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json) | `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` |

[독립 R03 보고서](real-device-gate-g1-r03-independent-f02-closure.md)와 [F02 종결 기록](benchmarks/real-device-gate-g1-r03/f02-independent-closure.json)은 이 세 신원에 대한 문서 검토 PASS를 기록한다. G1-R01-F01/F03 종결 보존도 [원 독립 기록](benchmarks/real-device-gate-g1-r03/prior-findings-nonregression.json)에서 확인했다. 이 종결은 문서 결함 범위이며, 원 F01 기술 문제의 종결이나 필수 증명 수용이 아니다. 이번 작업에서 독립 재심사나 기술 시험을 다시 수행하지 않았다.

[해시·검토 근거 대조](benchmarks/real-device-gate-g1-conditional-adoption/artifact-and-review-verification.json)는 위 세 승인 대상과 보조 참조를 분리한다. proof·거부 기준·가정·위험·gate·유한 검증 계획·O3 record-set은 기존 의미를 해석하는 고정 참조다. 이들의 참조 해시를 기록한 것이 소유자의 승인 범위를 새 산출물이나 위험 수용으로 확장하지 않는다.

## 2. 소유자 결정의 기록 방식

[이번 결정 기록](benchmarks/real-device-gate-g1-conditional-adoption/owner-design-adoption-decision.json)의 ID는 `G1-DESIGN-ADOPTION-01`이다. [사용자 결정 원문 전사](benchmarks/real-device-gate-g1-conditional-adoption/owner-decision-source.md)와 세 정확한 승인 대상, 독립 R03 근거, 허용 범위 및 제외 범위를 함께 기록했다. 원문 전사 파일의 해시는 저장된 UTF-8 파일 신원이며 메시지 전송 bytes나 암호학적 서명의 증명이 아니다. 소유자 신원은 이 세션에서의 명시적 자기 선언이며 이름을 발명하지 않았다. 메시지의 정확한 결정 시각이 제공되지 않아 결정 시각은 null이고 기록 시각만 별도로 남겼다.

기존 변경관리의 **명시적 owner 범위 → exact-hash 대상 → 별도 적용 기록 → 독립 적용 정합성 확인 → 현재 상태 연결** 방식을 따른다. 이는 [G1-O2 §1·§12의 규범 적용 조건](real-device-gate-g1-o2-corrected-proposal.md), [R03의 결정 준비 범위](benchmarks/real-device-gate-g1-r03/owner-decision-readiness.json), [B11의 승인·적용·역사 보존 기록 방식](t66f-b11-approved-amendment-application.md)을 근거로 한다. B11의 승인 자체를 G1로 이전하지 않는다.

기존 O2/O3 미서명 승인 양식과 R01/R02/R03 당시의 미승인 상태는 역사 그대로 보존했다. 새 [현재 상태 기록](benchmarks/real-device-gate-g1-conditional-adoption/current-status.json)이 이번 후속 결정을 연결한다. 기존 양식의 `G1_adopted`를 일괄 true로 바꾸거나 규범 채택 대안 O4를 선택한 것으로 기록하지 않았다. 이번 결정은 명시된 **설계 채택**이며 정확한 규범 변경문·목적지·효력·적용 승인이 포함되지 않았기 때문이다. 새 기록은 운영 실행기가 읽는 권한 토큰이나 활성화 경로가 아니다.

## 3. 현재 권한의 다섯 경계

| 경계 | 현재 상태 | 허용되는 의미와 별도 조건 |
| --- | --- | --- |
| 소유자 설계 승인 | **조건부 채택 승인** | 지정한 세 산출물을 향후 구현 계획·기술 증명 자격검증 준비의 기준으로 사용 |
| 구속 계약 적용 | **미승인·미적용** | 정확한 규범 목적지·변경문·원 F01과의 관계·효력 조건 및 통제된 적용의 별도 승인 필요 |
| 기술 구현 승인 | **미부여** | 소스·executor·app·OS 환경 변경과 각 검증 캠페인은 정확한 범위를 별도 승인해야 함 |
| 독립 기술 증명 수용 | **0/12** | 문서 PASS·machine check·소유자 승인과 별개. CP/IP/POST별 지정 비참여자의 실제 증거 수용 필요 |
| 실기기 실행 승인 | **미부여·차단** | CP 전부와 D 수용 뒤 연결·고정 read-only 등록 승인, IP 전부와 E2 수용 뒤 첫 mutation 승인 및 후속 checkpoint가 각각 필요 |

설계 승인은 proof 수용을 의미하지 않고 proof 수용도 실행 허가가 아니다. emulator·lab·mock 실행도 이번에 승인되지 않았다. [권한 단계 등록부](benchmarks/real-device-gate-g1-conditional-adoption/authority-stage-register.json)는 각 상태를 별도 필드로 기록한다. 연결·첫 mutation·다음 mutation의 현재 판정은 모두 DENY다.

12개 조항, 12개 필수 proof, 14개 거부 기준과 다음 세 보호는 유지한다: **최초 단말 신원 결합, 실제 승인 채널과 수신자의 결합, OS가 강제하는 기기 격리.** 이번 승인은 AS01–AS06 또는 GR01–GR07 각각의 위험 수용을 명시하지 않았으므로 수용 목록을 비워 둔다. GR05–GR07의 필수 보호 결측을 잔여 위험 서명으로 면제할 수 없고, GR01–GR04도 향후 정확한 범위 결정 없이 수용된 것으로 처리하지 않는다.

## 4. 한정 규범 적용 계획 — 아직 실행하지 않음

목표는 **한 개의 정확한 규범 적용 후보와 한 번의 owner 적용 결정**을 만드는 것이다. 현재 작성한 것은 그 계획이며, 규범 변경문이나 새 구속 계약을 적용하지 않았다. [유한 적용 계획](benchmarks/real-device-gate-g1-conditional-adoption/normative-application-plan.json)은 단계별 입장 조건·역할·산출물·거부·종료를 고정한다.

| 단계 | 범위·산출물 | 종료 조건 |
| --- | --- | --- |
| N0 — 이번 기록 | 세 해시와 R03·결정 원문 대조, 권한 구분, 현재 계획 작성 | 완료. 후속 적용/구현 자동 착수 없음 |
| N1 — 규범 후보 1개 준비 | 소유자가 정할 규범 관계·목적지를 반영해 exact redline·전후 해시·조항/PR/RJ 추적·가정/위험 scope·효력 조건을 한 문서 dossier로 동결 | 필수 범위 결정·필드 결측이면 BLOCKED. 실제 규범 파일은 바꾸지 않음 |
| N2 — 후보의 독립 문서 검토 1회 | 작성·적용·관련 구현 비참여자가 원 12/12/14·세 보호·PR07/G1-09·권한 분리·기존 규범과의 충돌을 확인 | ACCEPT 또는 BLOCKED/REJECTED. R03를 미래 redline 심사로 대체하지 않음 |
| N3 — 소유자의 exact 규범·적용 결정 1회 | 목적지·변경문 해시·원 F01 대체/보충 범위·가정/위험 항목·효력 조건·문서 적용 역할/검토 역할을 명시 승인 | 승인 없이는 N4 금지. 소유자는 규범 결정과 해당 문서 적용 허가를 한 명시적 결정에 함께 줄 수 있음 |
| N4 — 승인된 문서 적용 1회 | 승인된 파일/bytes만 materialize, 적용 전 사본과 실제 전후 SHA·재현 가능한 diff·결정 근거를 기록 | 미승인 파일/문구·원문 drift·누락이면 중단. 코드·OS·기기·Git index 변경 없음 |
| N5 — 적용 정합성 독립 확인 1회 | 비참여 검토자가 exact 적용, 원 F01 처리 범위, 모든 보존 조건과 현재 DENY를 대조 | 승인된 효력 조건과 독립 PASS·완료 기록이 모두 충족될 때만 지정 범위 효력 성립. 실패 시 새 규칙 비활성·BLOCKED |

N1의 **목적지 제안**은 새 `docs/real-device-gate-g1-safety-contract.md` 한 파일과 별도 적용 증거다. 이 경로는 현재 생성하지 않았고 canonical 지위를 부여하지 않았다. 역사 PREP/G1 문서와 B03/B11·B/C 규범·금융 의미·source locks를 수정하지 않는 후보를 우선한다. 기존 구속 문구를 바꿔야만 정합성이 생긴다면 범위를 넓히지 않고 새 owner 결정을 요청하도록 계획했다.

N1/N3에서 원 F01과의 관계는 반드시 다음 중 하나를 정확히 선택해야 한다.

- **보충 계약:** G1의 추가 의무만 구속하고 원 F01을 계속 누적 적용한다. 원 F01 미충족을 통과시키는 대체 실행 경로가 생기지 않는다.
- **한정 대체 계약:** 단일 고정 세션에 대체하는 원 F01의 정확한 의무·신뢰 가정·제외 위협·효력 경계와 범위 밖 원 요구의 존속을 별도 승인한다. 기술 만족이나 F01 기술 종결로 표현하지 않는다.
- **적용 보류:** 설계 계획의 기준으로만 유지하며 원 F01·실행 차단을 계속 적용한다.

현재는 어느 규범 선택도 적용하지 않았다. 미래 dossier에 승인된 설계와 다른 실질적 문구가 필요하면 그 차이를 redline에 드러내고 새 설계 결정을 받아야 한다. 12개 조항은 원 exact object와 연결하며, 초안의 역사 상태·목적지·효력 표시를 바꿀 부분도 무단 편집하지 않고 모두 owner 승인 대상에 넣는다. 계획 수립 승인을 그 미래 변경문 승인으로 확대하지 않는다.

N1–N5는 후보·검토·적용 각 1회이며 실패 후 자동 수정·재심사·반복 조사로 이어지지 않는다. BLOCKED/REJECTED에서 종료하고 새 범위 결정이 있어야 다시 시작한다. N5 이후에도 구현과 실행은 차단한 채 끝난다. 원 유한 검증 계획의 B–E 단계는 참조만 유지하며 지금 수행하거나 새 캠페인으로 예약하지 않았다.

## 5. 이후 기술 증명·기기 승인으로 넘어가기 위한 조건

정확한 구현 범위 승인과 단일 후보 동결은 규범 적용과 별개다. mock·OS/lab·emulator·실제 앱 lifecycle·중단/부분 완료·source/runtime/artifact 신원 검증은 기존 [유한 검증 계획](benchmarks/real-device-gate-g1-o2/finite-validation-stages.json)과 별도 승인을 따른다. emulator 완료는 물리 USB 격리나 개인 단말 신원의 proof가 아니다.

개인 단말 연결 전에 PR01–PR12.CP 및 D를 비참여자가 수용해야 한다. 미래 연결로만 얻는 IP/POST를 연결 전에 요구하는 순환은 만들지 않는다. 대신 유효한 규범 authority와 CP·사전 exact 신원/manifest·격리 메커니즘 아래 연결·고정 read-only 등록만 owner가 별도로 승인해야 한다. 연결 뒤 PR01–PR12.IP와 E2의 실제 세대 증거가 수용되기 전 모든 mutation은 금지한다. **첫 APK 설치도 mutation**이며 별도 owner 첫 mutation 확인과 exact artifact·등록 transcript가 필요하다. POST는 종료 후 이력 평가이며 과거 허가를 소급 생성하지 않는다.

PR07/G1-09의 잔여 작업 기준은 **무효화 사건**이다. 제출 시작·저장 commit·ACK와 구별하고 무효화 뒤 새 action/write/자원 취득은 금지한다. 무효화 전에 보냈지만 그때 독립 완료가 확인되지 않은 작업은 UNKNOWN_QUARANTINED다. host 취소로 원격 종료·실패·commit 여부를 추정하지 않는다. 추가 mutation·reconnect·자동 retry/cleanup 없이 확보된 증거의 독립 처분을 요구하며 폐기된 같은 세션은 재개하지 않는다.

개인 Galaxy S23 FE에는 별도 test package·signer·private storage·합성 backend/fixture만 허용하는 기존 요구를 유지한다. 개인 데이터·production·광역 삭제·root·bootloader·factory reset·기기 전체 정책 변경·넓은 권한은 허용하지 않는다. 고정 명령·한 세션·유한 예산·연결 뒤 소스/계획 변경 금지·자동 재시도 금지도 그대로다. 개인 데이터 손실 0, 이미 전달된 작업의 즉시 원격 정지, exactly-once는 보증하지 않는다. 이 잔여 위험의 수용은 최초 binding·actual recipient·OS enforcement의 기술 증명을 대신하지 못한다.

## 6. 검증·보존과 정확한 다음 결정

[정적 검증 결과](benchmarks/real-device-gate-g1-conditional-adoption/validation-and-preservation.json)는 JSON 구문·국소 schema, 승인 대상과 R03의 exact 해시 대조, 12/12/14와 세 보호, 권한 분리, 과거 파일·HEAD·Git index·외부 B03 sidecar 보존을 기록한다. [증거 manifest](benchmarks/real-device-gate-g1-conditional-adoption/evidence-manifest.json)에 새 기록과 이 보고서의 실제 SHA를 고정한다. 자기 검증을 독립 계약 심사나 기술 proof 수용으로 집계하지 않는다.

이번 범위는 결정 기록·적용 계획 문서다. 제품 import·npm/backend/Flutter 검증·ADB(도움말 포함)·emulator·물리 기기·API·production·T6.9 작업은 수행하지 않았다. 과거 host 검증 결과를 이번 검증 결과로 재사용하지 않았다. 큰 build/DB/benchmark 임시 산출물이 없어 정리 대상과 삭제는 없다. 원 N01/F02/F03/FC01 종결·B03/금융/source locks·모든 역사 증거와 기존 staged content를 보존하고 commit/push하지 않는다.

**다음 소유자 결정은 원 F01과의 보충/한정 대체 관계 및 규범 목적지의 선택이다.** [다음 결정 자료](benchmarks/real-device-gate-g1-conditional-adoption/next-owner-decision.json)에 보충·한정 대체·보류 대안을 제시했다. 문서 계획 작성에 대한 이번 권한은 이미 있으며 다시 요청하지 않는다. 아직 주어지지 않은 규범 범위 선택을 임의로 대신하지 않는다. 규범 변경문의 정확한 해시가 준비되고 독립 검토를 거친 뒤에만 N3의 별도 적용 승인을 요청한다.
