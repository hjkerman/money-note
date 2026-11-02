# Real-Device Gate G1-N3 — 승인된 하위 보충 규범의 정확한 적용

**문서 적용 완료.** 소유자가 승인한 exact patch로 목적지 한 파일을 생성했고 결과 SHA가 일치했다. 작성·구현·측정·적용에 참여하지 않은 별도 검토 agent의 N5 정합성 검토가 PASS이며, 그 뒤 완료 기록을 발급했다. 원 F01과 상위 규범은 계속 구속되고 미해결 기술 문제와 모든 기기 실행 차단은 유지한다.

## 1. 승인 범위와 정확한 적용

[owner 원문 전사](benchmarks/real-device-gate-g1-n3-application/owner-authorization-source.md)와 [N3 승인 기록](benchmarks/real-device-gate-g1-n3-application/owner-authorization-decision.json)을 새 event로 보존했다. 세션에서 명시한 프로젝트 소유자 역할에 근거하며 개인 이름·암호 서명·메시지의 초 단위 결정 시각은 발명하지 않았다. decided_at은 null이고 기록 시각과 구별했다. N2에 고정된 의존성·승인 입력은 이번 exact 적용 범위의 근거로 연결하되 AS01–AS06/GR01–GR07의 위험 수용이나 기술 수용으로 확대하지 않았다.

| 대상 | 실제 SHA-256 |
| --- | --- |
| 승인 patch | `05141e21d61945703073b0c4afbcf24ba6eb8e2cdce020dc1fffbb66d7452d9c` |
| 적용된 [보충 안전 계약](real-device-gate-g1-safety-contract.md) | `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e` |
| 원 승인 O2 후보 | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| 보존한 O3 계약 successor | `24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499` |
| 보존한 O3 PR07/G1-09 successor | `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` |

목적지는 적용 전에 ABSENT였고 before SHA는 null이다. 소스·후보·patch를 재생성/대체하지 않았다. `/dev/null`에서 지정 경로 하나에 164행을 추가하는 승인 patch를 `git apply --no-index --check` 뒤 `git apply --no-index`로 한 번 적용했다. 두 명령은 성공했고 기존 Git 환경/설정을 격리했다. 대체 index 파일도 생성되지 않았으며 실제 index bytes·staged entries는 그대로다. 적용 결과는 21,639바이트이며 승인 후보와 byte 단위로 같다.

[N4 적용 기록](benchmarks/real-device-gate-g1-n3-application/application-record.json)은 정확한 argv·cwd·선택한 Git 격리 변수·exit code·전후 신원과 당시 N5 PENDING 상태를 보존한다. 이를 사후 PASS로 덮어쓰지 않고 [완료 기록](benchmarks/real-device-gate-g1-n3-application/completion-record.json)과 [현재 상태](benchmarks/real-device-gate-g1-n3-application/current-status.json)가 이후 N5 결과를 연결한다.

## 2. 적용 전 신원 확인과 독립 적용 후 검토

[새 해시 대조](benchmarks/real-device-gate-g1-n3-application/preapplication-hash-verification.json)는 N2 입력 99개·보고서 및 산출물 17개·참조 178건과 owner 명시 해시 3건을 실제 bytes에서 다시 확인했다. 기존 저자 checker의 PASS를 재사용하지 않았다. [별도 preflight](benchmarks/real-device-gate-g1-n5-consistency/preflight.json)도 비참여 검토자가 직접 원문·해시·목적지 부재를 확인했으며 그 PASS 전에는 목적지를 수정하지 않았다. 적용 직전 고정 입력을 다시 대조했고 불일치는 없었다.

[독립 N5 보고서](real-device-gate-g1-n5-independent-application-consistency.md)와 [machine 판정](benchmarks/real-device-gate-g1-n5-consistency/postapplication-result.json)은 실제 적용 뒤 목적지·patch/승인/의존성 신원, 12/12/14·세 보호, 원 F01·상위 규범, 시간 의미·권한 분리와 보존을 독립 평가했다. 차단 finding은 0개다. 검토자는 같은 orchestration 안에서 fork_turns=none으로 시작한 별도 agent이며 원 문서 작성·구현·측정·적용에 참여하지 않았다. 외부 인간이나 별도 최상위 세션의 검증으로 표현하지 않는다. 이 결과는 기술 proof 수용이 아닌 문서 적용 정합성 PASS다.

승인 파일의 작성 당시 ‘미적용 후보/현재 미승인’ 표시는 exact 승인 bytes를 유지하기 위해 그대로 두었다. 현재 상태는 이 후속 owner 승인·N4 실제 적용·N5 독립 PASS·완료 event에 기록한다. 과거 문장을 바꾸거나 원 N2·O3/R03·미서명 양식·이전 미결 기록을 재작성하지 않았다.

## 3. 유지되는 안전 계약과 권한

| 경계 | 현재 상태 |
| --- | --- |
| 조건부 설계 채택 | 기존 owner 승인 유지 |
| G1 하위 보충 규범 문서 적용 | N3 exact 승인·N4 적용·N5 PASS 뒤 완료 |
| 원 F01 | **변경 없이 구속·기술적으로 미해결** |
| G1 아키텍처 구현·검증 캠페인 | 별도 승인 미부여·미착수 |
| 독립 기술 proof 수용 | **0/12** |
| 운영 ADB dispatch·연결/첫 mutation·실기기 gate | **CLOSED/BLOCKED, 승인 없음** |
| R1·production | 미활성·미승인 |

12개 G1 조항·12개 필수 proof·14개 거부 기준과 최초 단말 신원 결합·실제 승인 채널/수신자 결합·OS 강제 격리의 세 보호를 보존했다. 이미 N2가 심사한 G1-01/12의 보충/당시 권한 문구를 그대로 적용했으며 추가 조항 변경은 없다. 원 F01 AND 상위 적용 의무 AND 모든 G1 의무를 누적한다. 조건부 no-other-target·transport ID·반복 probe·위험 서명으로 원 F01을 대체하지 못한다.

무효화 사건 cutoff, SUBMISSION_COMMIT과 durable commit/ACK/원격 수명 구별, UNKNOWN_QUARANTINED·새 mutation/재접속/재시도/자동 cleanup 금지를 유지한다. 원 N01/F02/F03/FC01 독립 종결을 보존하되 G1 구현·F01 해결의 proof로 전환하지 않는다. B §27/§29와 C §26/§34/§34-B11/§35/§35-T69/§38.8–12의 상위 gate는 편집하거나 면제하지 않았다.

## 4. 보존과 작업 종료

[검증·보존 결과](benchmarks/real-device-gate-g1-n3-application/validation-and-preservation.json)는 기존 8,072개 파일의 bytes/mode/symlink와 외부 원 B03 sidecar 5개, HEAD·branch·Git index·staged entries가 같음을 기록한다. source locks·독립 감사·이전 승인/보고서·무관 worktree content는 보존됐다. 새 변경은 승인 목적지와 이번 적용/독립 검토 증거·보고서로 한정했다. [증거 manifest](benchmarks/real-device-gate-g1-n3-application/evidence-manifest.json)에 실제 파일 해시를 고정한다.

제품·B03·executor·OS 구현 변경, ADB(도움말 포함)·emulator·물리 기기·APK 설치·API·T6.9·R1·production 작업은 0이다. 문서 전용 범위에서 npm/backend/Flutter 검증을 실행하거나 과거 결과를 이번 proof로 집계하지 않았다. build/DB/benchmark scratch가 없어 큰 임시 산출물 정리는 해당 없고 삭제는 0바이트다. reset/stash/clean/checkout/rebase/restage/commit/push는 수행하지 않았다.

**정확한 규범 문서 적용 작업은 종료한다.** 구현이나 검증 캠페인이 필요하면 exact 범위와 증거 계획을 준비해 별도 owner 승인을 받아야 하며 이번 완료 기록이 그 권한을 부여하지 않는다.
