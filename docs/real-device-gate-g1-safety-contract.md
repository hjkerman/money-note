# Real-Device Gate G1 — 원 F01에 종속되는 보충 안전 계약 후보

문서 후보 ID: G1-SUPPLEMENT-DRAFT-01. 제안 목적지: `docs/real-device-gate-g1-safety-contract.md`.

규범 상태 주석: 제목·도입부, G1-12 마지막 문장 및 S6의 ‘현재 이 적용 승인은 없다’는 후보 작성 당시의 상태·결정을 기록한 것이며, 현행 보충 규범 효력은 docs/benchmarks/real-device-gate-g1-n3-application/completion-record.json의 G1-N3-N4-N5-DOCUMENT-APPLICATION-COMPLETE-01에 따른다.
**미적용 후보다.** 조건부 설계 채택과 보충 방향·문서 작성은 승인됐으나 이 문서의 규범 적용·활성화는 승인되지 않았다. 이 파일은 심사 사본이며 현재 구속 계약이 아니다. 운영 ADB dispatch와 모든 기기 접근은 BLOCKED다. 이 후보의 문장 중 의무형은 향후 별도 exact 승인·적용 시 추가로 구속할 요구를 뜻한다.

## S1. 권한·상위 규범·원 F01 우선

원 F01의 정확한 요구는 다음과 같으며 한 글자도 대체하거나 축소하지 않는다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

출처는 `docs/benchmarks/real-device-gate-prep09/f01-architectural-blocker.json#/requirement_ko`이며 원 PREP03 F01 이력과 함께 읽는다. G1은 이 요구를 만족시키기 위한 추가 집행·등록·격리·증거 의무다. **원 F01 AND 상위 적용 의무 AND G1의 모든 적용 의무**를 누적 요구하며 G1만을 만족하는 대체 경로를 만들지 않는다(MUST). 어떤 원 F01 의무도 신뢰 가정이나 잔여 위험 수용으로 면제할 수 없다(MUST NOT).

상위 규범은 `docs/t66/b/t66b-hot-cold-design.md`의 §27·§29와 `docs/t66/c/t66c-delta-sync-protocol.md`의 §26·§34·§34-B11·§35·§35-T69·§38.8–12다. G1은 Android 실제 내구성/whole-F·post-T6.6 기기 gate·T6.9·R1/rollout/deployment 의무를 재배치하거나 소거하지 않는다. 충돌·정합성 미입증이면 더 약한 규칙을 고르지 말고 BLOCKED로 종료한다.

원 G1 설계가 검토했던 조건부 대체/no-other-target 논리는 역사 설계 근거다. 이번 규범 관계는 소유자의 SUPPLEMENT, NOT REPLACE 결정에만 따른다. no-other-target·transport ID·반복 probe·격리만으로 원 F01의 동일 신원/연결 세대와 실제 mutation 수신자 결합이 증명됐다고 간주하지 않는다. 지원 mechanism으로 그 원 결합을 입증하지 못하면 G1 proof가 모두 있더라도 mutation은 금지다. 물리적으로 같은 순간의 별도 하드웨어 연산을 새로 요구하거나 제공한다고 주장하지도 않는다.

세 보호인 **최초 단말 신원 결합, 실제 승인 채널과 수신자의 결합, OS가 강제하는 기기 격리**는 면제할 수 없다. 원 N01/F02/F03/FC01 독립 종결은 보존하되 이들이 원 F01 해결이나 G1 기술 수용의 증거로 전환되지 않는다.

## S2. 추가로 적용할 12개 조항

원 승인 조항 ID와 보증을 보존한다. G1-01의 대체→보충·원 F01 비면제와 G1-12의 이번 작성 권한 이력만 명시 변경했다. 다른 10개 조항은 원문과 같다. 모든 조항은 S1의 상위·원 F01 누적조건 아래에서만 해석한다.

### G1-01 — 적용 범위와 효력

G1은 단일 소유자의 특정 개인 Galaxy S23 FE에서 한 고정 세션·합성 테스트 앱을 대상으로 하는 하위 보충 계약 제안이다. 별도 exact-hash 채택 승인과 통제된 규범 적용 전에는 효력이 없다. 원 F01은 계속 binding이고 변경·대체·면제하지 않으며 기술적 해결·종결로 표시하지 않는다.

### G1-02 — 조건부 안전 속성

승인된 물리 단말 P*와 그 단일 USB 연결 incarnation U*를 신뢰 등록 증거로 결합하고, 명시 승인한 신뢰 host/ADB/adbd/Android 가정 아래 모든 action의 실제 도달 집합을 {P*} 안으로 강제한다. 승인 target/연결/계획/bytes 외로 effect가 나가는 우회 경로를 허용하지 않는다.

### G1-03 — 사전 승인과 초기 등록

연결 허가식 ALLOW_CONTROLLED_CONNECTION은 PR01–PR12의 CP 독립 수용과 exact owner 연결/read-only grant만으로 판정하고 미래 U*/C* IP 관측값을 선행 요구하지 않는다. 승인된 고정 read-only 등록 뒤 모든 IP의 독립 수용과 별도 owner 첫 mutation grant를 ALLOW_FIRST_MUTATION으로 판정한다. IP 수용 전에는 설치/marker/launch를 포함한 mutation이 0이어야 한다. 사전 exact identity/계획 공란을 연결 후 임의 보충하는 예외는 없다.

### G1-04 — 권한의 resource 결합

승인 문맥은 owner 승인·세션·host boot/전용 principal·server resource 세대·실제 client channel·USB incarnation·transport ID·receiver boot/adbd 세대·plan/artifact·action 순서·만료를 함께 결합해야 한다. 이름/PID/주소/ID 문자열, UUID 또는 직전 polling만으로 resource 결합이 성립했다고 보지 않는다. 해당 자원 handle의 지원 여부와 강제 방식은 구현 proof 대상이다.

### G1-05 — 전면 매개와 transport 선택

기기 도달은 검증한 최소 실행 경계만 통해야 하며 wrapper·후손·다른 client/server·FD 전달·TCP/mDNS·재열거 접근을 강제 차단한다. transport ID는 같은 server 세대 안의 객체 선택 수단일 뿐 물리 인증이 아니다. -s/-t AND 검증, one-device 전면 격리, 사전 PID 조회의 원자성을 주장하지 않는다. 자동 server 시작/restart/reexec·fallback을 허용하지 않는다.

### G1-06 — 단방향 폐기

연결/transport 단절·reset/재등록/교체, server/client/channel restart·세대 변화, receiver/신원 불일치, 취소/권한 철회·감독/자식 회수 상실·한도/증거 실패는 진행 중에도 authority를 영구 REVOKED로 만든다. PR07/G1-09의 동일 SUBMISSION_COMMIT 정의로 새 제출/write·새 자원 취득을 금지하며 host 소유 자식은 기존 N01 보증으로 stop/reap한다. 같은 이름/세대 번호의 재등장이나 뒤늦은 ACK로 복구하지 않는다. remote 종료/결과 미입증이면 UNKNOWN_QUARANTINED로 유지한다.

### G1-07 — 고정 action과 재시도 금지

승인 전에 action별 실제 argv·input bytes·APK hash·component·파일 경로·순서·예산·증거 범위를 동결한다. 호스트 action별 dispatch 시도는 최대 1회다. 시험 앱의 프로세스 재생성·중복 intent도 논리 시험의 자동 재실행을 일으키지 않아야 한다. 같은 데이터에 대한 안전한 exactly-once remote 완료는 약속하지 않는다.

### G1-08 — 허용 효과와 개인 데이터

효과는 test package 설치/실행과 명시한 private synthetic 파일·합성 endpoint에 한정한다. 설치의 package-manager 기록·앱 lifecycle 등 필수 OS bookkeeping과 공유 CPU/저장 자원 소비는 별도 선언된 부수효과다. 개인 앱/데이터·production ID/credential/DB/Snapshot·공유 저장소 접근, broad deletion, root/reset/bootloader·device-wide 정책 변경·특별 접근 권한은 금지한다.

### G1-09 — 진행 중인 원격 작업

PR07과 같은 SUBMISSION_COMMIT은 승인한 고정 receiver/channel에 실제 bytes 제출이 시작됐음이 입증된 경계다. RESERVED/메모리 queue는 예외가 아니다. 무효화 뒤 새 제출/host write/자원 취득/buffer 이동은 금지한다. 이미 제출된 동일 action/receiver/channel의 bounded bytes·remote 작업은 이후 완료될 수 있으나 결과/remote 종료 미입증이면 UNKNOWN_QUARANTINED이고 ACK도 세션을 복구하지 않는다. 추가 mutation·readback/reconnect·자동 stop/clear/uninstall은 금지하며 확보된 증거로 비참여자가 사후 처분한다. host 취소가 remote 정지/rollback을 보증한다고 주장하지 않는다.

### G1-10 — 예산과 증거

연결 전 CP에 고정 예산·bounded journal·UNKNOWN/격리 정책을 수용하고 등록 후 IP에 실제 여유/종단/세대와 시간/bytes를 수용한다. 무효화·부분 완료·ACK와 remote task 상태·host 자식 회수를 분리 기록하며 결측/증거 저장 실패는 성공이 아니다. PR10의 POST는 종료 후 확보된 증거의 독립 평가이며 실행 권한을 소급 발급하지 않는다. 실제 한계와 best-effort 감시는 구별한다.

### G1-11 — 독립 proof와 수용

PR01–PR12 각 ID 안의 CP(연결 전 메커니즘), IP(등록 후 첫 mutation 전 인스턴스), POST(종료 이력)를 구별한다. EVIDENCE_COLLECTED, MACHINE_CHECK_PASSED, INDEPENDENTLY_ACCEPTED, AUTHORITY_GRANTED는 대체 불가다. 비참여 검토자가 실제 source/runtime/artifact/OS/enforcement와 최종 APK의 실제 Android lifecycle 증거를 범위별 수용한다. 모든 CP 미수용이면 연결, 모든 IP 미수용이면 mutation을 거부한다. 모형/emulator 결과는 물리 USB/개인 단말 신원 proof를 대체하지 못하며 결측을 위험 서명으로 면제하지 않는다.

### G1-12 — 실행 전 별도 결정

규범 채택/적용, 구현, mock/OS/lab/emulator/app/interruption 검증, 독립 CP 수용, owner 연결/read-only grant, 독립 IP 보충 수용, owner 첫 mutation grant, 종료 후 POST 처분은 각각 지정 gate와 범위로 구별한다. 유한 단계에서 필수 proof를 세울 수 없으면 BLOCKED/REJECTED로 종료하고 자동 수정/재감사/재시도하지 않는다. 이번 소유자 결정은 보충 규범 후보와 독립 검토 자료의 문서 작성만 승인하며 규범 적용·구현·검증·기기 권한을 부여하지 않는다.

## S3. 단계별 누적 허가와 무효화

기존 `ALLOW_CONTROLLED_CONNECTION`, `ALLOW_FIRST_MUTATION`, `ALLOW_NEXT_MUTATION`, `ACCEPT_POST_EVIDENCE`의 모든 조건을 유지하고 아래 조건을 더한다. 이는 미구현 규범 선언이지 boolean/token·환경 변수로 여는 gate가 아니다.

- 연결 전에는 원 F01을 강제할 메커니즘·격리·세대 폐기의 독립 CP 증거와 상위의 해당 단계 진입 조건을 PR03–PR07 및 PR12.CP에 포함해 수용해야 한다. 미래 U*/C*의 IP나 POST·원격 mutation receipt를 연결 전에 요구하지 않는다. 사전 exact 신원/동결 manifest·모든 CP와 D 수용·별도 owner 연결/read-only grant가 없으면 연결은 금지다.
- 등록 뒤 첫 mutation 전에는 실제 U*/S*/C*/T*/R*와 승인 신원·실제 채널/수신자의 결합을 원 F01 그대로 PR03–PR07 및 PR12.IP에서 독립 입증해야 한다. 조건부 no-other-target로 대신할 수 없다. 모든 IP·E2 수용과 별도 owner 첫 mutation 확인 전에는 최초 APK 설치·marker·launch도 금지다. 미입증이면 DENY다.
- 각 후속 action과 실제 효과 전달에는 같은 원 F01·상위/G1 의무·현재 연속성과 사전 checkpoint가 계속 충족돼야 한다. 새 material 증거는 지정 비참여자가 수용하고 action별 host 제출 시도는 최대 1회다. 단절/교체 뒤 같은 session 권한 복구는 금지다.
- POST는 종료 이력의 독립 분류일 뿐 과거 또는 새 권한을 생성하지 않는다. 원 F01 증거를 새 PR13으로 우회하거나 기존 12개 PR 가운데 일부만 PASS로 묶지 않는다. 그 증거는 기존 binding/enforcement PR 안에서 명시적으로 대조한다.

진행 중 잔여 범위의 기준은 **무효화 사건**이다. `SUBMISSION_COMMIT`은 실제 제출 시작이고 durable commit·원격 task 시작·ACK·host 관측/집행 시각과 각각 다르다. 무효화 뒤 새 제출/write/자원 취득/buffer 이동은 0이어야 하며 지연된 관측·집행은 유예가 아니다. 실제 위반을 UNKNOWN으로 면제하지 않는다.

무효화 전에 동일 action/receiver/channel에 이미 제출된 bounded bytes·작업이 그때 독립 완료/종료로 확인되지 않았다면 UNKNOWN_QUARANTINED다. host stop/reap은 N01 자식 회수일 뿐 원격 정지·실패·commit·rollback을 입증하지 않는다. 추가 mutation/readback/reconnect/자동 stop·clear·uninstall 없이 이미 확보한 증거의 독립 처분을 요구한다. 늦은 ACK도 폐기된 같은 세션을 재개하지 못한다.

## S4. 필수 증명 12개와 거부 기준 14개

아래 PR의 의무·필수 증거·phase_acceptance·면제 불가 조건과 상세 CP/IP/POST 행렬을 S7의 정확한 해시로 고정해 참조한다(MUST). 전문 판단은 지정 비참여자에게 있고 수집·machine PASS·독립 수용·owner grant는 서로 대체할 수 없다. current_status 등 원 파일의 당시 metadata는 역사 상태이며 기술 수용을 발급하지 않는다. 현재 기술 수용은 **0/12**다.

| PR | 의무 | 원 required-proof-matrix의 정확한 pointer |
| --- | --- | --- |
| PR01 | 승인 provenance·계약 우선순위 | `/proofs/0` |
| PR02 | artifact/tool 신원 | `/proofs/1` |
| PR03 | 최초 등록과 bootstrap 결합 | `/proofs/2` |
| PR04 | USB incarnation 강제 | `/proofs/3` |
| PR05 | server/channel/transport 결합 | `/proofs/4` |
| PR06 | OS 전면 매개와 우회 불가 | `/proofs/5` |
| PR07 | 폐기·host 1회 시도·감독 수명 | `/proofs/6` |
| PR08 | 앱 격리와 자동 재실행 방지 | `/proofs/7` |
| PR09 | 합성 backend·네트워크 | `/proofs/8` |
| PR10 | 자원·증거·UNKNOWN 처분 | `/proofs/9` |
| PR11 | 명령·효과 allowlist 완결성 | `/proofs/10` |
| PR12 | 독립 통합 수용 | `/proofs/11` |

`proof-phase-and-acceptance-matrix.json`의 같은 ID별 세 facet과 phases/state_separation, `device-admission-conditions.json`의 원 gate 전부, 원 유한 단계의 실행/독립 수용·한도를 보존한다. 모형/emulator 증거는 물리 USB 격리나 개인 단말 신원을 증명하지 않는다. mandatory 증명을 세울 수 없으면 BLOCKED/REJECTED로 종료한다.

| RJ | 거부 조건 원문 | 원 처분 |
| --- | --- | --- |
| RJ01 | proposal-only 지시를 계약 채택/실행 승인으로 사용 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ02 | 실제 USB incarnation/최초 P* 등록이 불명확하거나 설치 뒤 key로 소급 bootstrap 인증 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ03 | -s/-t·one-device·단일 목록·PID polling을 원자적 binding/OS isolation으로 수용 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ04 | 서버/USB 주소/ID/receiver 세대가 바뀌어도 기존 승인 재사용 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ05 | auto server start/restart/reexec·TCP reconnect·fallback·부모 밖 후손 ADB 경로 허용 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ06 | OS 강제 경계 대신 저장된 boolean/UUID/검사 후 kill만 사용 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ07 | 명령/bytes/manifest/budget 미정 또는 연결 후 source/APK/계획 변경 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ08 | 첫 mutation 전 owner 확인 없음·앱 재생성/중복 intent 자동 replay | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ09 | production/개인 데이터/광역 로그/공유 저장소·특별 권한/기기 정책 변경 필요 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ10 | UNKNOWN을 성공 처리하거나 retry·clear/uninstall·추가 probe로 자동 회복 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ11 | 등록/강제 경계/전면 매개 proof 결측을 residual-risk 서명으로 면제 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ12 | 문서/모형 PASS나 저자 self-review를 독립 OS/phone 검증으로 집계 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ13 | hard realtime remote stop·exactly-once·개인 데이터 손실 0의 미입증 주장 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |
| RJ14 | 기존 F01/역사 증거/source locks/index를 수정하거나 문구 변경을 기술적 수정 완료로 표현 | REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK |

RJ의 원문은 최소 거부 조건이다. 이번 작성 승인을 exact 규범 적용이나 실행 권한으로 확대하는 경우도 허가 범위 위반으로 거부한다. AS01–AS06와 GR01–GR07은 이번 결정에서 항목별 수용되지 않았다. 위험의 설명과 수용은 원 F01 또는 PR/세 보호를 면제하지 못한다.

## S5. 개인 단말·효과·증거의 한계

기존 test-only package·독립 signer·private synthetic storage·합성 backend/fixture를 함께 격리한다. 개인 앱/데이터·production DB/Snapshot/credential·광역 로그·공유 storage·root/reset/bootloader·기기 전체 정책 변경·넓은 권한·광역 삭제는 금지다. 최초 설치도 mutation이다. 명령·artifact·소스·fixture·시간/bytes·종료/증거 수집 범위를 연결 전에 동결하고 연결 뒤 adaptive 명령·소스 변경·자동 retry를 금지한다.

필수 OS bookkeeping과 공유 CPU/memory/저장 소비, 이미 전달된 작업의 부분 완료 가능성, 제한 증거/응답 유실을 숨기지 않는다. 개인 데이터 손실 0·즉시 원격 취소·remote exactly-once는 입증됐다고 주장하지 않는다. 이것은 위험 수용이 아니며 모든 필수 기술 증명과 owner의 별도 세션 범위 결정을 유지한다.

## S6. 별도 승인·규범 효력·적용 실패

설계 채택 → 규범 exact 적용 승인 → 통제된 문서 적용·독립 정합성 → 별도 구현/각 검증 승인 → 독립 CP 수용 → owner 연결/read-only grant → 독립 IP 수용 → owner 첫 mutation grant → 후속 checkpoint → POST 처분을 구별한다. 앞 단계 완료가 뒤 권한을 자동 부여하지 않는다. 현재 실행 판정은 모두 DENY다.

본 후보의 구속 효력은 N2의 독립 문서 검토, N3의 목적지/후보/redline/dependency hashes·역할·효력 조건을 명시한 owner 승인, N4의 승인 bytes 문서 적용, N5의 비참여 exact 적용 검증 PASS와 승인된 효력 사건·완료 기록이 모두 있을 때만 지정 범위에서 성립한다. 현재 이 적용 승인은 없다. 원 F01은 이 후보의 적용 뒤에도 계속 누적 구속되며 이 보충안으로 대체/중단되지 않는다.

이 후보의 적용 계획은 새 문서 1개·한 dossier·한 candidate review·한 문서 적용·한 적용 review로 제한된다. 실제 B/C binding protocol·B03/B11·제품·executor·OS·source lock·Git index는 변경 대상이 아니다. 범위/해시 drift·충돌·증거 결측이면 중단하고 BLOCKED/REJECTED로 기록한다. 자동 재작성·재심사·재적용·기기 복구는 없다. 역사 기록은 보존하고 새 규칙이 유효한 것처럼 동작시키지 않는다.

## S7. 정확한 설계 신원과 의존성

다음 세 파일의 승인 신원은 보존하며, 본 후보는 별도 신원의 통합 초안이다. 원 문서가 가리키는 과거 O2 temporal JSON 대신 지정 O3 successor 두 개를 사용한다. 원 파일의 대체 제안/과거 승인 상태를 이번 보충 규범의 우선순위로 가져오지 않는다.

| 승인 설계 산출물 | SHA-256 |
| --- | --- |
| `docs/real-device-gate-g1-o2-corrected-proposal.md` | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| `docs/benchmarks/real-device-gate-g1-o3/g1-contract-proposal.json` | `24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499` |
| `docs/benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json` | `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` |

아래 고정 참조의 의무/증거/거부/격리/시간·단계 정의를 S1의 누적조건 아래 읽는다. pointer `/`는 전체 유한 계획의 보존을 뜻하되 실행 권한을 부여하지 않는다. 원 기록의 metadata·옛 choice/template·과거 대체 제안·당시 미승인 상태는 provenance다. 원 proof와 거부 기준의 내용을 축소하는 재해석은 금지다.

| 의존성 경로 | SHA-256 | 핵심 pointer |
| --- | --- | --- |
| `docs/benchmarks/real-device-gate-g1-o2/required-proof-matrix.json` | `be77ec1dae508451875635dea84b80a44b912f4ab143c982bcb5ffd76012f63e` | `/proofs` |
| `docs/benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json` | `f6f0f9eb6c32f9ceaba8f1276b24b69ff8434a72449cdbd5f070c803d0832972` | `/proofs` |
| `docs/benchmarks/real-device-gate-g1-o2/approval-and-rejection-options.json` | `2ae6bad92530ea0388fc0b48da32242aa1c325b5881a4327388e639aaf181232` | `/rejection_criteria` |
| `docs/benchmarks/real-device-gate-g1-o2/device-admission-conditions.json` | `d4fccad2f13a6ebce0b373dfba473a599e294a58bc2ba626c9944a2b9dff7766` | `/declarative_machine_gates_not_implementation` |
| `docs/benchmarks/real-device-gate-g1-o2/finite-validation-stages.json` | `9c18e0630c3dca4694a4a057331caaddc8a00b70fa9b1d337562b9c85121f72e` | `/` |
| `docs/benchmarks/real-device-gate-g1-o2/guarantee-and-assumption-register.json` | `6229129e3f36b5058d39312283da2736d1c54d393114175c8df8a4185a87704b` | `/assumptions` |
| `docs/benchmarks/real-device-gate-g1-o2/residual-risk-and-acceptance-register.json` | `fe026d19b436931a99eec12488a5a7088d68d39c852968f347c958115bb34c3e` | `/risks` |
| `docs/benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json` | `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` | `/remaining_work_ko` |
| `docs/benchmarks/real-device-gate-g1-o3/effective-record-set.json` | `671185f6cd585125bb78225d4c9fa1a631818f149f33ba1c20261a84791a6053` | `/effective_records` |

링크/경로 해석 기준은 제안 목적지 `docs/real-device-gate-g1-safety-contract.md`와 저장소 root다. 실제 파일 신원·원본 대비 조항 변경·상위 절의 hash는 별도 심사 dossier에서 함께 확인해야 한다.
