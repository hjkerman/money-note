# Real-Device Gate G1-O2 — 세 차단 지적에 한정한 계약 제안 수정

**판정: PASS — CORRECTED G1 PROPOSAL READY FOR INDEPENDENT R02 REVIEW.** 이는 수정 제안의 문서 준비 판정이며 G1 채택·적용, R01 finding의 독립 종결, 기술 proof 수용 또는 실행 승인이 아니다. G1은 미승인·미적용이고 원 F01은 계속 binding/unresolved다. 운영 dispatch와 기기 접근 차단을 유지한다.

## 1. 권한·검토 대상·버전 보존

이번 작업은 원 G1 제안 작성 세션의 O2 문서 수정이며 G1-R01 독립 검토 세션이 아니다. 소유자는 G1-R01-F01/F02/F03만의 문서 수정을 승인했다. [O2 권한](benchmarks/real-device-gate-g1-o2/owner-o2-authorization.json). R01의 실제 finding 원문·최소 수정·수용 기준을 확인했으며 기록에 없는 reviewer 요구를 새 finding으로 만들지 않았다.

검토한 원안은 [기존 제안서](real-device-gate-g1-safety-contract-proposal.md), R01은 [독립 보고서](real-device-gate-g1-r01-independent-contract-review.md)와 [원 finding JSON](benchmarks/real-device-gate-g1-r01/independent-findings.json)이다. R01 JSON 13개는 전체 파싱·해시로 확인했고 큰 보존 목록도 원문을 변경하지 않았다. [입력 목록](benchmarks/real-device-gate-g1-o2/r01-input-inventory.json).

기존 파일을 덮어쓰지 않는 방식을 택했다. 새 [corrected candidate](real-device-gate-g1-o2-corrected-proposal.md)는 `G1-O2-CANDIDATE-01` revision이며 원 package/contract ID와 G1-01–12, PR01–12, RJ01–14를 유지한다. 원안·기존 unsigned template·R01은 그대로 두고 관련 원문 8개를 새 증거의 `original/`에도 보존했다. 원/수정 markdown 및 JSON diff는 [redline과 해시](benchmarks/real-device-gate-g1-o2/proposal-redline-and-hashes.json), 정확 원문/수정문·사유·proof/RJ·승인 단계·강도는 [변경 matrix](benchmarks/real-device-gate-g1-o2/finding-correction-matrix.json)에 있다.

| 신원 | SHA-256 |
| --- | --- |
| R01이 심사한 원 제안서 | `2630cbc850c3c66fb2283160315691f656335e3d5c2681d71e54c9a747218b5a` |
| O2 corrected candidate | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| 원 규범 초안 JSON | `71e149e1c38b5c38bdaf1f24a2fffd2635aefbd3a6c8d4970e21c79d9bf556ea` |
| 수정 규범 초안 JSON | `c26dd72ddcd0f55f66a641a400a4b51df840cb530c8e559f47a8060c8ebf7bc8` |

## 2. 세 원 finding과 제안 해결

| 원 finding | 실제 R01 지적 | 이번 수정 | 독립 처분 |
| --- | --- | --- | --- |
| G1-R01-F01 | 단일 DEVICE_ACCESS gate가 연결 전 CP와 실제 U*/C*가 필요한 IP를 혼동 | 12 PR별 CP/IP/POST facet과 PH0–PH5 수집·수용·reviewer·machine 상태, 연결/read-only 식과 첫 mutation 식을 분리 | ADDRESSED — 제안 문구 기준, R02 대기 |
| G1-R01-F02 | PR07의 새 effect 금지와 G1-09의 이미 수신된 작업 후속 완료의 판정 경계 불일치 | G1-06/09·PR07·T10이 SUBMISSION_COMMIT, 예약/미전송, same action 잔여 bytes, ACK/remote task, UNKNOWN_QUARANTINED와 독립 사후 처분을 공유 | ADDRESSED — 제안 문구 기준, R02 대기 |
| G1-R01-F03 | V1 모형과 비Android V2 이후 실제 앱 lifecycle·독립 PR12 수용의 경로 결측 | C3 emulator·C4 최종 APK 실제 lifecycle·C5 중단/부분 완료, D/E2/E4의 독립 수용과 owner gate를 유한 단계로 명시 | ADDRESSED — 제안 문구 기준, R02 대기 |

R01은 기존 세 보장의 정의나 현재 차단이 이미 무너졌다고 판단하지 않았다. 수정도 초기 물리 결합·actual channel binding·OS 격리 의무를 줄이지 않는다. 조항 G1-01/02/04/05/07/08은 정확 원문을 유지하고, 03/06/09/10/11/12는 세 finding에 필요한 시점·공통 판정·수용 경로만 보완했다. RJ14개 원문과 ID는 모두 유지했다. PR07의 표현 정밀화는 원 의무의 완화가 아니며 이미 수신한 작업의 완료 자체가 위반이라는 새 요구나 hard realtime remote stop을 만들지 않았다.

## 3. F01 — 수집·수용·권한의 단계 경계

PH0=개인 단말 연결 전 준비/별도 승인된 lab·Android 검증, PH1=owner가 별도 허용한 고정 read-only 등록, PH2=실제 인스턴스 독립 수용, PH3=owner 첫 mutation 승인, PH4=진행 중 연속성/다음 action checkpoint, PH5=분리 후 증거 평가다.

각 PR 안의 CP는 메커니즘과 exact source/artifact/OS 적용성, IP는 실제 개인 세션의 P*/U*/S*/C*/T*/R* 및 runtime 귀속, POST는 이미 수행한 이력에 대한 수용이다. PR ID를 늘리지 않고 모두 명시했다. [12개 상세 행렬](benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json)은 각 facet의 earliest collection/acceptance, 필수 비참여자, machine status·추가 인간 판단, preconnection 불가 evidence, mutation 전 허용 여부·실패 처분을 포함한다.

PROOF_PLANNED, EVIDENCE_COLLECTED, MACHINE_CHECK_PASSED, INDEPENDENTLY_ACCEPTED와 AUTHORITY_GRANTED는 대체 불가다. 마지막 값은 proof 상태가 아니라 owner의 별도 권한 기록이다. O2의 기술 facet은 모두 planned/pending이고 수집·machine PASS·독립 수용·owner grant를 만들지 않았다.

연결 전 모든 CP가 IR_TECH에게 수용되고 owner가 exact 연결/read-only 범위를 승인해야 **ALLOW_CONTROLLED_CONNECTION**만 검토할 수 있다. 이 gate는 미래 U*/C*의 관측이나 IP/POST 수용을 요구하지 않는다. 승인 등록 이후 모든 IP가 IR_SESSION에게 수용되고 owner가 exact transcript/manifest의 첫 mutation을 별도 승인해야 **ALLOW_FIRST_MUTATION**을 검토한다. CP 한 개라도 미수용이면 연결 DENY, IP 한 개라도 미수용이면 설치·marker·launch 포함 mutation DENY다.

PR12.CP/IP/POST는 각각 PR01–PR11의 같은 facet을 통합하며 자기 수용을 선행 요구하지 않는다. 첫 설치 전에 실제 설치 receipt를 요구하지 않으며, 승인 설치 후 생성된 material 증거는 사전 정의 read-only checkpoint/IR_SESSION 보충 수용을 거쳐야 다음 launch/mutation이 가능하다. 사전 identity/argv/예산 공란을 live probe로 채우는 예외는 없다. POST는 사후 분류이며 권한을 소급 만들지 않는다. [선언식](benchmarks/real-device-gate-g1-o2/device-admission-conditions.json)은 실행 코드가 아니며 현재 모든 연결/mutation gate는 DENY다.

## 4. F02 — 진행 중 무효화와 UNKNOWN·격리

PR07의 독립 수용 조건은 다른 target effect=0, 무효화 후 새 제출/write=0, 새 resource 취득=0, action별 시도<=1, 기존 N01 범위의 host 자식 회수다. `SUBMISSION_COMMIT`은 실제 고정 receiver/channel에 승인 bytes 제출이 시작됐음이 입증된 경계이며 Popen 생성·메모리 queue·RESERVED·마지막 probe는 이에 해당하지 않는다.

제출 전 취소와 RESERVED 뒤 미전송 취소는 이후 전송 0이어야 한다. 이미 수신한 고정 action이 무효화 뒤 완료하는 이력은 다른 target 전달/새 action 제출과 분리하고 ACK·remote task 상태를 보존한다. 이미 제출된 동일 action/receiver/channel bytes만 잔여 범위이며 새 host write나 새 channel로 나머지를 보내는 것은 금지한다.

server restart, transport 단절/교체, identity/receiver 세대 불일치, authority 철회, 감독 상실과 한도/증거 실패가 진행 중 발생해도 authority는 영구 REVOKED다. 소유 host 자식은 기존 N01 보증으로 stop/reap하고 회수 미확인은 안전 실패다. host kill이 device task 종료를 뜻하지 않는다. remote 종료/결과 또는 사건 순서 미입증이면 **UNKNOWN_QUARANTINED**를 명시하며 ACK도 같은 세션의 권한을 복구하지 않는다.

격리 뒤 추가 mutation·readback/reconnect·자동 device stop/clear/uninstall은 없다. IR_EVIDENCE는 이미 확보한 host/선행 승인 observer 기록으로 독립 사후 처분하며 종료 proof가 없으면 격리를 유지한다. 해소 판정도 폐기된 세션을 재개하지 않고 새 작업은 별도 owner 결정이다. [6개 판정 이력과 사건별 처분](benchmarks/real-device-gate-g1-o2/pr07-g109-consistency.json). T10은 12개 trace ID를 유지하면서 3개의 고정 하위 이력으로 분해해 총 고정 이력 수 14개를 공개했고 1시간/10MiB 상한은 늘리지 않았다. 실제 실행은 0이다.

## 5. F03 — 유한 end-to-end 경로

| 단계 | 제안한 범위·종료점 |
| --- | --- |
| A | static architecture/authority 문서 심사 1회·2시간·10MiB |
| B | 별도 승인 구현 후보 1개·동결 심사 1회; 구현 범위/작업 예산 미지정이면 착수 불가 |
| C1 | mock 1개·T01–T12/고정14이력·1시간·10MiB; 실제 OS proof 아님 |
| C2 | exact OS/USB lab recipe 1개·8음성·90분·20MiB; 물리 USB resource proof 필요 |
| C3 | 별도 승인된 owned emulator 실행/단절/server restart/교체 4시나리오·30분·20MiB |
| C4 | 최종 APK의 actual Android start/중복 intent/process recreation/claim 뒤 death/partial death/완료 뒤 restart 6시나리오·45분·20MiB |
| C5 | host/guest 중단·ACK 유실/부분 완료·remote task 지속·격리 6시나리오·45분·20MiB |
| D | source/runtime/artifact/OS/실제 sink·개별 CP와 PR12.CP 독립 통합 수용 1회·2시간·50MiB |
| E0 | 모든 CP와 별도 규범 authority 뒤 owner가 첫 real-device 연결/read-only 범위를 명시 결정; 현재 미부여 |
| E1/E2 | 통제 등록 evidence 수집 뒤 모든 IP와 PR12.IP의 독립 수용. 수집/기계 PASS만으로 mutation 불가 |
| E3 | 별도 owner 첫 mutation 승인 뒤 고정 action만 1회씩; checkpoint/연속성 불충족이면 중단 |
| E4 | 분리 후 이미 확보된 증거의 모든 POST·독립 사후 처분 1회·2시간·50MiB; 새 실행 권한 없음 |

각 stage에는 entry, permitted/prohibited actions, required artifacts, objective pass/fail, responsible role/independent reviewer, maximum scope·attempt, failure disposition과 exit가 있다. [완전 단계 정의](benchmarks/real-device-gate-g1-o2/finite-validation-stages.json). E1–E3 공유 600초/10MiB는 제안 ceiling일 뿐 승인된 실기기 예산이 아니며 exact manifest의 실제 값이 공란이면 E0는 DENY다. 리뷰/owner 무응답으로 시간을 늘리거나 승인으로 간주하지 않는다.

emulator 성공은 물리 USB 격리·개인 phone 신원 proof가 아니다. actual APK/OS/ABI 적용성 근거가 없거나 F01/FC01을 우회하지 않는 안전한 emulator 경로를 마련할 수 없으면 BLOCKED다. 최종 앱의 실제 process/task·논리 effect는 독립 관측해야 하며 기존 PREP02 정상 smoke나 모형 T12로 PR08을 채우지 않는다. 한 번의 고정 캠페인이 필수 proof를 세우지 못하면 BLOCKED/REJECTED로 끝내고 자동 수정/재감사/추가 recipe·개인 단말 선행 시험을 시작하지 않는다.

## 6. R02 승인 대상과 현재 상태

새 [unsigned exact-hash template](benchmarks/real-device-gate-g1-o2/owner-approval-template.json)은 corrected candidate와 수정 dossier만 승인 대상으로 pin한다. 원안/기존 template hash는 역사 provenance로만 남고 새 서명이나 권한은 없다. [R02 인계](benchmarks/real-device-gate-g1-o2/independent-r02-handoff.json)는 원 세 finding의 exact 최소 수정/수용 조건과 원문 redline·CP/IP/POST·공통 경계·finite lifecycle proof 경로를 1회 비참여 문서 심사로 검토하도록 준비했다. 독립 R02는 아직 수행하지 않았다.

소유자 잔여 위험 수용은 등록·actual channel binding·OS enforcement proof를 면제하지 않는다. G1 채택/적용·운영 executor 구현·ADB·emulator·physical device·APK 설치 권한을 부여하지 않는다. 원 F01 요구, test-only package/signer/private storage와 synthetic backend, N01/F02/F03/FC01의 독립 종결 범위를 보존한다. B03·금융 의미·T6.9·R1·production은 불변/미승인이다.

## 7. 검증·보존

문서 JSON·ID·행렬·인과관계/선언식·원문 대조·redline 재현·링크/hash·unsigned 상태와 기존 source/index를 검증했다. 이 자체검증은 기술 proof 또는 독립 R02가 아니다. AGENTS 필수 npm build와 기존 backend 소형 회귀는 task 사본/신규 합성 임시 DB에서 exit0, 72 tests·44 subtests 통과했으며 G1 stage 실행 분모에 넣지 않는다. [저장소 검증](benchmarks/real-device-gate-g1-o2/repository-validation.json).

기존 7,517개 파일, 원안·R01 증거·HEAD·branch·index/staged identity, 외부 B03 sidecar 5개의 bytes/mode/symlink를 보존한다. 새 파일은 두 O2 보고서/candidate와 O2 증거로 한정한다. task-owned 검증 scratch만 비활성 확인 후 정리하며 기존 SDK/AVD/APK/cache/자료는 삭제하지 않는다. [보존](benchmarks/real-device-gate-g1-o2/preservation.json), [정리](benchmarks/real-device-gate-g1-o2/artifact-cleanup.json), [최종 문서 검증](benchmarks/real-device-gate-g1-o2/final-validation.json), [증거 manifest](benchmarks/real-device-gate-g1-o2/evidence-manifest.json).

**최종 판정: PASS — CORRECTED G1 PROPOSAL READY FOR INDEPENDENT R02 REVIEW.** 다음 행동은 별도 비참여 R02 검토자의 문서 심사이며 원 F01/G1의 승인이나 기기 실행은 아니다.
