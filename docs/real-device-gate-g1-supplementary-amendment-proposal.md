# Real-Device Gate G1 — 원 F01 하위 보충 규범의 정확한 개정 후보

**원 F01을 대체하지 않는 보충 후보 1개와 정확한 redline·의존성·독립 검토 인계 자료를 준비했다.** 소유자의 보충 방향 선택과 문서 작성 권한을 새 기록에 남겼다. 실제 규범 적용·활성화, 구현, 기술 proof 수용, ADB·Android 접근은 수행하거나 승인하지 않았다.

검토 대상은 [미적용 전문 후보](benchmarks/real-device-gate-g1-supplementary-amendment/candidate/real-device-gate-g1-safety-contract.md), [새 문서 추가 redline](benchmarks/real-device-gate-g1-supplementary-amendment/normative-amendment.redline.patch), [승인 조항 대비 통합 redline](benchmarks/real-device-gate-g1-supplementary-amendment/integration-clauses.redline.patch)이다. 저자의 준비 완료 판정이며 독립 N2 ACCEPT나 적용 허가는 아니다.

## 1. 소유자 결정과 작성 범위

[원문 전사](benchmarks/real-device-gate-g1-supplementary-amendment/owner-direction-source.md)와 [방향·권한 기록](benchmarks/real-device-gate-g1-supplementary-amendment/owner-supplement-direction.json)은 **SUPPLEMENT, NOT REPLACE**를 선택한다. 이미 승인된 설계 기준은 유지하되 원 F01에 종속되는 추가 요구만 제안한다. 이번 결정은 exact 후보·redline·정합성 자료·인계 작성만 허용한다. 메시지의 정확한 결정 시각은 제공되지 않아 null이며 별도 기록 시각만 남겼다. 전사 파일의 SHA는 저장 파일의 신원이지 메시지 전송 bytes나 암호학적 서명을 인증한 결과가 아니다.

기존 [N0–N5 적용 계획](benchmarks/real-device-gate-g1-conditional-adoption/normative-application-plan.json)의 N1에 해당하는 한 dossier를 준비했다. 이전의 미선택 상태·미서명 양식·검토 판정은 역사 그대로 보존했고 [이번 현재 상태](benchmarks/real-device-gate-g1-supplementary-amendment/current-status.json)가 보충 선택과 새 후보를 연결한다. 소유자의 설계/방향 승인을 이 exact 후보의 규범 적용 승인으로 확대하지 않았다.

## 2. 목적지와 상위 권한을 확인한 근거

제안 목적지는 기존 계획의 **`docs/real-device-gate-g1-safety-contract.md`**다. 현재 해당 파일은 없으며 이 작업에서도 생성하지 않았다. 전문은 증거 디렉터리의 `candidate/` 안에만 있다. 이 경로가 이미 canonical 규범이었다거나 현행 문서에 G1 절이 있다고 주장하지 않는다.

| 실제 현행 문서·절 | 확인한 상위 의무 | 후보의 관계 |
| --- | --- | --- |
| [B §27](t66/b/t66b-hot-cold-design.md#27-성능-acceptance와-미래-scaling-benchmark), [B §29](t66/b/t66b-hot-cold-design.md#29-t66cde-의존성-지도) | 성능 증거와 T6.6F 이후 실기기 gate·구현/수용 순서 | 기존 범위·순서를 바꾸지 않음 |
| [C §26](t66/c/t66c-delta-sync-protocol.md#26-android-durability와-safe-fallback) | 실제 Android driver·VFS·native fence·I/O·전원 손실 proof와 rollout 차단 | G1 또는 emulator PASS로 대체하지 않음 |
| [C §34·§34-B11](t66/c/t66c-delta-sync-protocol.md#34-미래-rollout과-구현-의존성) | 별도 구현·rollout 승인, 제한 증거 이관과 whole-F/R1 차단 | G1이 이관·활성화 예외를 만들지 않음 |
| [C §35·§35-T69](t66/c/t66c-delta-sync-protocol.md#35-complexity압축-비교와-measurable-gate) | 실측·기기/host 구분, 원 B03 증거와 T6.9 수용 계약 | 수집·수용 의무나 실행 GO를 바꾸지 않음 |
| [C §38.8–12 및 실패 처리](t66/c/t66c-delta-sync-protocol.md#38-내부-정합성미해결-구현-proof) | Android/legacy/복구/backup/실기기 proof, 실패 시 차단과 별도 명세 변경 감사 | 원 의무를 누적 유지 |
| [PREP09 F01 요구](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json)와 원 PREP03 finding | 동일 신원·수신자/연결 세대의 원자적 결합과 권한 비승계 | 최상위 안전 제약으로 그대로 유지 |

실제 절 제목·현재 행 위치·파일 및 절 bytes SHA는 [목적지·권한 검토](benchmarks/real-device-gate-g1-supplementary-amendment/governing-authority-and-destination.json)에 고정했다. B/C는 상위 gate를 정하지만 G1 전용 목적지를 지정하지 않는다. 따라서 기존 계획의 별도 안전 계약 문서를 그 아래 **추가 요구만 담는 새 문서 후보**로 제안했다. 기존 B/C protocol에 가짜 G1 절을 추가하거나 실제 구속 파일을 편집하지 않았다.

새 경로의 구속 권한은 현재 존재하지 않는다. N2 독립 후보 검토 → N3 목적지·정확한 변경문·의존성·효력/역할을 지정한 소유자 승인 → N4 승인 bytes 적용 → N5 독립 적용 정합성과 승인 효력 조건·완료 기록이 충족돼야 지정 범위 효력이 생긴다. 이 보충안이 적용되더라도 원 F01은 계속 누적 구속된다.

## 3. 보충 규범의 정확한 내용과 두 조항의 변경

후보 S1의 허가 관계는 **원 F01 AND 상위 적용 의무 AND G1의 모든 적용 의무**다. 원 신원·mutation 결합을 조건부 no-other-target, transport ID, 반복 probe, 소유자 위험 수용으로 대신하지 못한다. 지원 메커니즘으로 원 F01을 입증할 수 없으면 G1 관련 증거가 있어도 mutation은 계속 DENY다. 이를 이미 구현하거나 보증을 입증했다는 주장은 없다.

원 F01 문장은 후보 S1에 정확히 인용했다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

| 조항 | 제안 변경 | 안전 의미 |
| --- | --- | --- |
| G1-01 | `조건부 대체 계약 제안` → `하위 보충 계약 제안`; 원 F01의 `변경·대체·면제하지 않음` 명시 | 원 F01의 누적 구속 강화. 대체 경로 제거 |
| G1-12 | 당시 O2 문서 수정 권한 문장을 이번 보충 후보·독립 검토 자료 작성 권한으로 갱신 | 모든 gate와 실행 금지 유지. 과거 O2 자체는 변경하지 않음 |
| G1-02–G1-11 | 원 조항 object와 동일 | 10개 조항의 title/text를 그대로 보존 |

12개 조항 ID는 모두 유지했다. 두 문구 변경을 “12개 원문 모두 불변”으로 표현하지 않는다. [정확 변경 map](benchmarks/real-device-gate-g1-supplementary-amendment/amendment-clause-change-map.json)은 승인 원문·후보문·사유·강도와 pointer를 전부 기록한다. 원 설계 MD/JSON은 수정하지 않았다. 별도 조항 redline은 이 두 변경만 보이며, 새 문서 redline은 부재 파일에서 후보 전문을 추가하는 정확한 diff다.

후보 S3은 CP에 메커니즘 증거, IP에 실제 등록 세대와 첫 mutation 전 원 F01 결합 증거를 둔다. 기존 PR03–PR07·PR12 안에서 원 binding 의무를 대조하며 PR13이나 waiver를 만들지 않는다. 미래 U*/C*·POST를 연결 전에 요구하는 순환도 만들지 않는다. 별도 CP/owner 연결 grant 아래 고정 read-only 등록만 가능하고, IP와 owner 첫 mutation 확인 전에는 **첫 APK 설치도 금지**다. 현재는 어느 연결/변경 권한도 없다.

PR07/G1-09는 무효화 사건을 cutoff로 유지한다. SUBMISSION_COMMIT·원격 시작·저장 commit·ACK·host 관측/집행은 다르다. 무효화 전에 제출됐지만 그때 완료/종료가 독립 확인되지 않은 작업은 UNKNOWN_QUARANTINED다. host cancel로 원격 정지·실패·commit을 추정하지 않고 새 제출/write/자원 취득과 mutation·readback/reconnect·자동 cleanup을 금지한다. 확보된 증거의 독립 처분도 폐기된 같은 세션을 복구하지 않는다.

## 4. 의존성과 비회귀

| 보존할 승인 설계 | 실제 SHA-256 |
| --- | --- |
| G1-O2 수정 후보 | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| G1-O3 계약 후속 JSON | `24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499` |
| G1-O3 PR07/G1-09 후속 JSON | `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` |

[의존성 lock](benchmarks/real-device-gate-g1-supplementary-amendment/approved-design-and-dependency-lock.json)은 이 세 승인 신원과 proof·phase·gate·거부 기준·유한 계획·가정/위험·O3 record-set을 고정한다. 원 12개 PR의 의무·필수 증거·phase_acceptance·면제 불가 조건을 전부 참조하고, 14개 RJ의 원문·처분은 후보 S4에도 그대로 담았다. 참조 파일의 과거 상태/대체 대안/미서명 metadata를 새 authority로 가져오지 않는 범위를 명시했다.

세 면제 불가 보호인 최초 단말 신원 결합·실제 채널/수신자 결합·OS 강제 격리는 보존했다. AS01–AS06·GR01–GR07의 항목별 수용은 이번에 부여되지 않았다. 조건부 가정은 원 F01의 의무를 줄이지 못하며 잔여 위험 서명은 기술 proof가 아니다. 개인 단말의 test package/signer/storage와 합성 backend/fixture, 고정 명령·한 세션·예산·재시도 금지·개인/production 데이터 비접근 요구를 유지한다.

[의존성·정합성 대조](benchmarks/real-device-gate-g1-supplementary-amendment/dependency-consistency-review.json)는 저자의 검토 준비다. G1-R03가 독립 종결한 세 문서 finding과 N01/F02/F03/FC01 종결은 보존하되, 새 보충 후보를 R03가 심사했다고 주장하지 않는다. 기술 증명 수용은 **0/12**다.

## 5. 정확한 후보 신원과 독립 검토 인계

| 산출물 | 실제 SHA-256 |
| --- | --- |
| 미적용 전문 후보 | `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e` |
| 새 문서 추가 redline | `05141e21d61945703073b0c4afbcf24ba6eb8e2cdce020dc1fffbb66d7452d9c` |
| 원 조항 대비 통합 redline | `ab3da7a1c0525658459071f129974547bd8e5de98ba26b8d1f4f8760b5d5983b` |

목적지의 적용 전 상태는 **ABSENT**이며 before SHA는 null이다. 위 후보 SHA가 proposed-after 신원이고 실제 목적지의 현재 SHA라고 가장하지 않는다. [신원 기록](benchmarks/real-device-gate-g1-supplementary-amendment/amendment-package-hashes.json)에 전문·두 diff·원문 render·review inputs·미서명 양식의 실제 해시를 남겼다.

[독립 N2 인계](benchmarks/real-device-gate-g1-supplementary-amendment/independent-review-handoff.json)는 작성·관련 구현/측정·적용 비참여자가 **한 exact dossier를 한 번 문서로 검토**하도록 범위를 한정한다. 원 F01 누적성, 목적지/실제 절, 12/12/14·세 보호, 시간 의미·단계별 수용/owner 분리, 정확 diff/해시와 보존을 심사한다. 새 모형·OS·emulator·기기 시험은 범위 밖이다. 독립 검토는 아직 수행하지 않았다.

성공하면 이 후보의 **별도 owner N3 적용 결정 준비**만 인정한다. 결측·충돌·보호 약화면 BLOCKED/REJECTED로 종료하고 자동 수정/재심사 루프를 만들지 않는다. [미서명 미래 적용 양식](benchmarks/real-device-gate-g1-supplementary-amendment/unsigned-application-authorization-template.json)은 exact 후보/목적지/의존성을 pin하되 owner 승인·서명·역할/효력·위험 수용·모든 실행 grant를 미부여로 둔다.

## 6. 자체 정적 검증과 보존

[검증·보존 결과](benchmarks/real-device-gate-g1-supplementary-amendment/validation-and-preservation.json)는 JSON 구문·국소 schema, 실제 절/pointer·의존성/승인 해시, 두 diff의 exact byte 복원, 12/12/14와 세 보호·권한 분리, 원본·source locks·HEAD·Git index·외부 B03 sidecar 보존을 기록한다. [전체 증거 manifest](benchmarks/real-device-gate-g1-supplementary-amendment/evidence-manifest.json)에 실제 산출물 해시를 고정한다. 이는 독립 심사나 기술 proof가 아니다.

기존 구속 protocol·개인 데이터·제품/금융/B03·executor·OS는 변경하지 않았다. ADB(도움말 포함)·emulator·물리 기기·APK 설치·API·production·T6.9·R1은 모두 미수행이다. 문서 전용 범위에서 npm/backend/Flutter 검증을 새로 실행하거나 과거 결과를 이번 proof로 집계하지 않았다. 큰 build/DB/benchmark scratch와 삭제 대상은 없고 역사 증거·원 source locks·기존 index를 보존했다. commit/push는 없다.

**다음 행동은 독립 N2 문서 검토 1회다.** 검토자의 판정과 별도 exact owner 적용 승인 전까지 목적지 생성·규범 적용·구현·기기 실행은 계속 금지한다.
