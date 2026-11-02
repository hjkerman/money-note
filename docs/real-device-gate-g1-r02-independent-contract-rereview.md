# Real-Device Gate G1-R02 — 수정 G1 안전 계약 독립 재검토

**최종 판정: PARTIAL — FURTHER TARGETED CORRECTIONS REQUIRED.** 원 지적 3개 중 G1-R01-F01과 G1-R01-F03은 문서 결함 범위에서 독립 종결한다. G1-R01-F02는 잔여 작업의 시간 기준이 본문과 두 JSON에서 달라 **OPEN — MATERIAL DEFECT**로 유지한다. 남은 차단 지적은 1개이며 최소 문서 정정으로 해소할 수 있다. G1 승인·적용·구현·기술 proof 수용·기기 실행 권한은 부여하지 않았다.

## 1. 독립성·권한·방법

이 세션은 원 G1-R01 독립 검토 세션을 이어 사용했으며 원 제안/O2 작성과 PREP02–PREP08 구현에 참여하지 않았다. 독립성은 **SATISFIED**다. 이번에도 구현/승인/기기 실행 권한 없이 정적 재검토만 수행했다. 독립 종결은 R01 문서 finding의 처분이며 PR01–PR12의 실제 기술 증명 수용이 아니다.

AGENTS와 산출물 관리 규칙을 다시 읽었다. R01에서 전체 읽은 project-state/domain-model/known-issues 및 architecture 서버 authority 경계는 실제 hash가 같음을 확인해 기존 규범을 적용했다. 원안·R01 보고서/finding·PREP10·원 F01 근거는 보존된 정확 신원으로 대조했고 수정 후보와 O2 보고서·JSON·redline·미서명 양식을 읽었다. O2 저자의 문서 PASS와 JSON 자체 판정을 이번 독립 판정의 전제로 사용하지 않았다.

개발 checkout에서 문서/JSON/hash/AST/참조/시점·의존성만 검사했다. 제품/시험/devicegate 모듈 import·ADB(도움말 포함)·emulator·물리 기기·APK 설치·backend/API·OS 정책 변경·T6.9 측정은 모두 0이다. 문서 전용 재검토 범위가 일반 AGENTS build 권고보다 우선하므로 npm/backend 시험은 실행하지 않았다. O2의 과거 72 tests·44 subtests와 npm 성공은 역사 자료로만 보존했고 이번 실행 결과로 집계하지 않았다.

## 2. 후보와 근거의 정확 신원

| 대상 | 확인 결과 |
| --- | --- |
| 원 제안서 SHA-256 | 2630cbc850c3c66fb2283160315691f656335e3d5c2681d71e54c9a747218b5a |
| 수정 후보 SHA-256 | e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279 |
| 후보 revision | G1-O2-CANDIDATE-01 / G1-PROPOSAL-01 / F01-G1-DRAFT-01 |
| 수정 계약 JSON SHA-256 | c26dd72ddcd0f55f66a641a400a4b51df840cb530c8e559f47a8060c8ebf7bc8 |
| 미서명 승인 양식 SHA-256 | 954363a277122c2fe405e29e22175386ce148b8f475a270f507a878a5c80d824 |
| HEAD | ebcbd54d90eeee194a04b9eea6367f446ee2fd28 |
| branch | refs/heads/main |
| Git index SHA-256 | 33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b |
| staged path/mode/blob SHA-256 | 9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f |

두 supplied hash는 실제 파일 bytes와 일치해 후보 동일성 중단 조건은 발생하지 않았다. [수정 후보](real-device-gate-g1-o2-corrected-proposal.md), [수정 보고서](real-device-gate-g1-o2-contract-corrections.md), [원안](real-device-gate-g1-safety-contract-proposal.md), [R01](real-device-gate-g1-r01-independent-contract-review.md)을 서로 다른 역사 버전으로 유지했다.

원안/R01/O2/PREP09/PREP10 manifest 5개의 참조 178개, 두 승인 양식의 pin/target 대조 30건, O2 카탈로그 66개, R01/O2 JSON 47개를 확인했다. redline 6개를 actual 전후 bytes에서 재생성해 일치했고 원문 사본 8개와 보호 source 9개도 일치했다. 이는 안전 보장 분모가 아니라 파일/참조 검사 수다. [신원 평가](benchmarks/real-device-gate-g1-r02/candidate-integrity-review.json), [정적 검증](benchmarks/real-device-gate-g1-r02/static-integrity-and-reference-validation.json).

## 3. 세 원 finding의 독립 처분

| 원 finding | 판정 | 이유 |
| --- | --- | --- |
| G1-R01-F01 | INDEPENDENTLY CLOSED | 12개 PR 각각에 CP/IP/POST 증거·최초 수집/수용 phase·비참여 수용자·무효화가 명시됐다. 연결 허가와 첫/후속 mutation 허가가 분리되고 미래 U*/C* IP나 POST를 연결 전 수용하도록 요구하지 않는다. PR12는 다른 11개 같은 facet을 통합하므로 자기 수용 순환이 없다. 수집/기계 PASS/독립 수용/owner grant는 각각 별도다. |
| G1-R01-F02 | OPEN — MATERIAL DEFECT | 대부분의 요청된 공통 판정은 명확해졌지만 잔여 작업 cutoff가 두 machine-readable JSON과 본문에서 다르므로 원 finding의 단일 판정 기준을 충족하지 못한다. 수정을 두 시간 기준의 정합화로 한정할 수 있어 전체 판정은 PARTIAL이다. |
| G1-R01-F03 | INDEPENDENTLY CLOSED | A/B의 설계·source 동결, C1 mock, C2 실제 OS/USB lab, 별도 승인 C3 emulator, C4 최종 APK 실제 lifecycle, C5 중단/부분 완료, D source/runtime/OS 적용성과 CP 독립 수용, E1 수집/E2 IP 수용/E3 owner 첫 mutation/E4 POST 처분의 경로와 상한이 정의됐다. 지원 경로나 필수 증거가 없으면 BLOCKED/REJECTED이며 개인 phone을 첫 실험 장소로 쓰지 않는다. |

### G1-R01-F01 — 독립 종결

원래 결함은 전체 PR을 연결 전 하나의 accepted 상태로 요구하면서 실제 U*/C* transcript까지 선행 수용하도록 읽히는 모호성이었다. 수정 §9와 [proof 행렬](benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json)은 모든 PR의 CP/IP/POST를 명시하고 [허가식](benchmarks/real-device-gate-g1-o2/device-admission-conditions.json)을 연결/read-only·첫 mutation·후속 mutation·사후 분류로 분리한다.

CP는 PH0에서 검증 메커니즘/적용성·사전 신원을 수집하고 IR_TECH가 수용한다. 실제 개인 세션 IP는 별도 owner 연결 승인 뒤 PH1 read-only로 수집하고 PH2 IR_SESSION이 수용한다. PH3 owner 첫 mutation 확인 전 설치/marker/launch는 0이다. POST는 PH4 실제 이력 수집·PH5 분리 후 평가이며 실행 권한을 소급 만들지 않는다. 첫 설치 전에 설치 receipt를 요구하지 않고, 설치로 생긴 material 증거는 고정 read-only checkpoint·IR_SESSION 수용 전 다음 launch를 막는다.

PR12 각 facet은 PR01–PR11의 같은 facet만 통합한다. 명시된 36개 facet 의존성은 순환하지 않으며 연결 gate는 미래 IP/POST나 첫 mutation grant를 선행 요구하지 않는다. 수집·MACHINE_CHECK_PASSED·INDEPENDENTLY_ACCEPTED·AUTHORITY_GRANTED는 다른 기록이다. 전문 수용과 owner 권한을 기계 PASS로 대신하지 않으므로 원 수용 기준을 충족한다. 선언식 검사이며 실제 판정기나 기기 binding proof를 실행한 결과는 아니다.

### G1-R01-F02 — 한정된 시간 기준 결함으로 유지

제출 전 취소·RESERVED 미전송·이미 수신된 작업·ACK 이후 task·server/transport 교체·host 자식 잔존의 6개 경우와 UNKNOWN_QUARANTINED 처분은 추가됐다. host kill과 remote task 종료를 구별하고, 진행 중 권한 폐기와 N01 stop/reap·부분 증거 보존·자동 readback/reconnect/cleanup 금지를 유지한 점도 적절하다. 다만 다음 두 정의는 본문의 시간 기준과 일치하지 않는다.

| 정확 근거 | 실제 문구/의미 |
| --- | --- |
| 수정 후보 §8, 148행 | SUBMISSION_COMMIT = 고정 receiver/channel로 실제 bytes 제출이 시작됐음이 입증된 사건 |
| 수정 후보 §8, 150행 | 무효화 전에 동일 action/receiver/channel에 이미 제출된/버퍼링된 bytes·원격 작업만 잔여 범위 |
| g1-contract-proposal.json:90 /formal_conditions/in_flight_definition_ko | commit 전에 같은 action/receiver/channel에 이미 제출된/버퍼링된 bytes와 remote 작업만 잔여 범위다. RESERVED만 된 action, 새 host write, 새 channel/receiver 취득·buffer 이동은 예외가 아니다. |
| pr07-g109-consistency.json:38 /remaining_work_ko | commit 전에 같은 action/receiver/channel에 이미 제출된/버퍼링된 bytes와 remote 작업만 잔여 범위다. RESERVED만 된 action, 새 host write, 새 channel/receiver 취득·buffer 이동은 예외가 아니다. |

**제출 시작 commit과 권한 무효화는 다른 사건이다.** `RESERVED → SUBMISSION_COMMIT → 같은 action bytes 수신 → 무효화 → 기존 remote 작업의 완료 불명`이라는 정적 이력에서 본문은 무효화 전 수신 bytes를 잔여 범위로 분류한다. 반면 두 JSON의 문구를 그대로 따르면 제출 시작 이전에 이미 제출된 작업만 잔여 범위여서 같은 이력을 포함하지 못한다. host 메모리 queue는 commit이 아니라고 별도로 제외돼 있으므로 그 queue로 차이를 해소할 수도 없다. 이 이력은 실행하지 않은 문서상 순서 반례이며 실제 기기 위반을 재현했다는 주장이 아니다.

정확 규범 초안은 조항 배열이라고 명시돼 있지만 같은 승인 dossier가 formal 조건과 공통 판정 JSON도 pin하고 PR07/T10이 이를 사용한다. 본문 의도를 추정해 두 필드를 무시하거나 commit을 정의 없는 무효화 commit으로 읽으면 원 finding의 공통 판정 기준을 다시 구현자 판단에 맡기게 된다. 그래서 단순 hash 검증 PASS로 종결할 수 없다.

**최소 수정은 두 JSON의 잔여 작업 cutoff를 본문과 동일한 무효화 시점으로 통일하는 것이다.** SUBMISSION_COMMIT의 제출 시작 의미·RESERVED 제외·다른 대상 효과=0·폐기 뒤 새 제출/write/자원 취득=0·UNKNOWN_QUARANTINED·N01/remote 구별은 그대로 유지해야 한다. 관련 수정 matrix/redline/승인 pin 해시는 새 수정 버전에서 갱신하고 현재 원안/O2/R01 증거는 보존해야 한다. 이번 재검토는 어떤 후보도 수정하지 않았다.

### G1-R01-F03 — 독립 종결

수정 §10과 [유한 단계](benchmarks/real-device-gate-g1-o2/finite-validation-stages.json)는 실제 Android 검증과 독립 수용의 공백을 메웠다. C3는 별도 승인된 owned emulator 연결·단절·restart/교체 4개, C4는 최종 APK의 정상 시작·중복 intent·process 재생성·claim 뒤 death·partial death·완료 뒤 restart 6개, C5는 제출/ACK/task·host/guest 중단 6개를 고정 fixture에서 각 1회로 한정한다.

C4는 실제 APK bytes/signer/ABI/Android image/process/task/durable 상태를 독립 관측하고 C5는 host kill을 remote 종료로 수용하지 않는다. D는 source/tool/runtime/OS/정책·실제 sink 및 phone 적용성 차이를 검토해 CP를 독립 수용하며, E2는 실제 세션 IP, E4는 분리 후 확보된 POST만 수용한다. emulator가 물리 USB/phone P* binding을 대체하지 않으며 자격 경로·실제 lifecycle·적용성 proof가 없으면 BLOCKED다. 실제 검증이 수행됐다는 뜻은 아니다.

[원 finding별 상세 처분](benchmarks/real-device-gate-g1-r02/r01-finding-closure.json)에 R01의 원 수용 기준과 근거 hash/JSON pointer/남은 반례를 연결했다. 역사 R01 finding 원문은 수정하지 않았다.

## 4. 모든 mandatory proof의 수집·수용 경계

아래의 모든 CP 최초 수집/유효 수용은 PH0/PH0·IR_TECH, IP는 PH1/PH2·IR_SESSION, POST는 PH4/PH5·IR_EVIDENCE다. 현재 36개 facet 모두 PROOF_PLANNED·NOT_RUN·PENDING이며 증거/수용자 필드는 비어 있다. 이는 36개 새 의무가 아니라 기존 PR01–PR12 안의 시점 구분이다. **실제 기술 proof 수용은 0/12다.**

| PR | 연결 전 CP 근거 | 승인 등록 후 IP 근거 | 연결 전 얻을 수 없는 값 |
| --- | --- | --- | --- |
| PR01 | 규범 우선순위·exact 승인 종류와 DENY 정책 | 실제 연결 세션에 적용되는 규범/manifest scope 일치; owner grant는 별도 기록 | 실제 session id·승인 범위의 live 귀속 |
| PR02 | 최종 source/tool/APK/signer/fixture·봉인 bytes 및 binary 의미 | 실제 host/tool/runtime과 전송할 봉인 bytes의 동결 신원 대조 | 실행 host/process·실제 fd/봉인 세대 |
| PR03 | 설치/marker 없이 P*를 U*/C*에 결합할 qualified mechanism·독립 사전 식별·wrong-singleton 음성 근거 | 실제 P*/U*/C* 등록 transcript와 독립 식별 대응·연속성 수용 | 현재 대상 U*/C*와 actual receiver transcript |
| PR04 | 정확 OS/driver/backend의 USB incarnation/재열거·주소 재사용 강제 proof | 실제 U*·열린 USB 자원·OS recipe 적용과 새 incarnation 차단 확인 | 현재 U* kernel resource·실제 열거 수명 |
| PR05 | actual server/channel 결합·no auto restart/reexec/fallback의 정확 binary/OS proof | 실제 S*/C*/T* peer/resource 수명과 승인 귀속 확인 | 현재 S*/C*/T*와 actual socket peer |
| PR06 | wrapper/후손/FD/socket/TCP/mDNS를 포함한 정확 OS 전면 매개 proof | 현재 principal/namespace/policy/FD·도달 집합의 recipe 일치 확인 | 현재 정책 부착·실제 열린 자원/후손 세대 |
| PR07 | 공통 제출 경계·다른 대상 효과=0·폐기 후 새 제출=0·1회 시도·자식 회수의 proof | 해당 session의 감독·폐기 enforcement가 무장됐고 예약/제출 사건과 현재 권한이 정확히 결합됨 | 현재 제출/폐기 사건·감독/자식 수명 기록 |
| PR08 | 최종 APK 격리와 실제 Android 앱 lifecycle·중복 intent/process 재생성 replay=0; phone 적용성 근거 | 첫 설치 전 fresh test package 부재·OS/ABI/선정 APK 적용성; 설치된 앱 증거를 미리 요구하지 않음 | 개인 대상 test package 부재·실제 OS/ABI 귀속 |
| PR09 | 합성 backend/host와 Android 경로·origin/route/redirect/egress의 정확 proof | 실제 backend/route/listener/namespace와 사전 검증한 경로의 귀속 확인 | 현재 종단/route·backend process 귀속 |
| PR10 | 정책·시간/bytes/여유 hard/soft 한계·journal/UNKNOWN·격리 처분 proof | 현재 세션의 여유/예산/증거 저장과 deadline/remote 한계 확인 | 실제 세션 여유·시간/bytes/수신 상태 |
| PR11 | 등록/설치/시작/수집의 literal action/bytes/경로/순서·효과·예산 완결성 | 실제 등록 session과 next action의 immutable manifest 대조; live 값은 사전 정의 slot만 | 실제 연결 세대 slot·action ordinal; 새 명령/사전 identity 공란 채우기는 불가 |
| PR12 | PR01–PR11의 CP 증거·source/runtime/OS 대응과 기존 종결 보존의 독립 통합 수용 | PR01–PR11 IP와 CP 보존·등록 후 보충 증거를 독립 통합 수용; 자신을 선행조건으로 삼지 않음 | 연결 후 IP 묶음과 개별 session reviewer 수용 기록 |

모든 POST는 이미 확보된 실제 action·무효화·결과·부분 증거를 정확 source/runtime/OS/session에 귀속해 이행/위반/UNKNOWN을 판정한다. 모든 CP/IP의 미수용·만료·세대 불일치·권한 철회는 해당 연결/mutation gate를 닫는다. 새 material 증거가 필요한 후속 checkpoint의 자동 형식 검사는 독립 수용을 발급하지 않고 IR_SESSION의 보충 수용이 필요하다. PR07의 시점 배치는 해소됐으나 별도의 잔여 작업 의미 정합성은 위 G1-R01-F02 결함으로 남는다. [12개 상세 경계](benchmarks/real-device-gate-g1-r02/mandatory-proof-boundary-review.json).

## 5. 12개 조항·12개 proof·14개 거부 기준의 회귀 검토

개수 일치만으로 보존을 추론하지 않았다. 조항 6개는 text bytes가 동일하고, 나머지 6개는 이전 의무와 새 강제/수용 구조를 의미로 대조했다.

| 조항 | 원문 동일 | 보호·변경 평가 |
| --- | --- | --- |
| G1-01 | 예 | 범위·효력 원문 동일. 별도 exact 채택과 규범 적용 전 원 F01 계속 binding. |
| G1-02 | 예 | 원문 동일. 최초 P*/U* 결합과 실제 도달 집합 {P*} 및 허용 효과 경계 유지. |
| G1-03 | 아니오 | CP와 IP 및 owner 연결/첫 mutation을 분리. 사전 identity/plan 공란의 live 보충 금지와 설치 전 IP 의무 유지. |
| G1-04 | 예 | 원문 동일. actual resource lifetime·모든 세대 binding을 문자열/PID/polling과 구별. |
| G1-05 | 예 | 원문 동일. wrapper/후손/FD/TCP/mDNS 전면 매개·no auto server 수명/fallback 유지. |
| G1-06 | 아니오 | 진행 중 무효화·host 자식 회수·remote UNKNOWN_QUARANTINED를 명시. 비승계/새 제출 금지는 강화됐으나 연결한 잔여 정의에 G1-R01-F02 공백이 남음. |
| G1-07 | 예 | 원문 동일. literal bytes/argv/순서·예산 동결·시도<=1·앱 restart replay 금지 유지. |
| G1-08 | 예 | 원문 동일. test-only package/signer/private storage/synthetic backend와 개인/production·특별 권한 금지 유지. |
| G1-09 | 아니오 | RESERVED·ACK·remote task·격리·host/remote 중단 구별을 명확화. 다만 formal 잔여 범위 cutoff가 본문과 달라 G1-R01-F02 미종결. |
| G1-10 | 아니오 | CP/IP의 예산·실제 상태와 POST 사후 수용을 분리. 결측을 성공 처리하지 않고 권한 소급 발급 금지 유지. |
| G1-11 | 아니오 | 36개 시점 facet을 기존 12 PR 내부에 명시. machine/독립 수용/owner 분리, 실제 Android lifecycle 및 nonwaivable proof 유지. |
| G1-12 | 아니오 | 채택/적용·구현·검증·독립 수용·owner 연결·첫 mutation·POST를 분리하고 유한 실패 종료를 명시. |

| PR | 보존 평가 |
| --- | --- |
| PR01 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR02 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR03 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR04 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR05 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR06 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR07 | 오대상 효과=0·폐기 후 새 제출/write/자원 취득=0·시도<=1·host 자식 회수와 UNKNOWN을 명시해 의도를 보존했다. 공통 잔여 작업 cutoff의 G1-R01-F02 정합화는 아직 필요하다. |
| PR08 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR09 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR10 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR11 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |
| PR12 | 원 의무·증거·비면제 원문은 유지하고 gate를 CP/IP/연속성/POST로 세분했다. |

PR07 외 11개는 obligation/required evidence/비면제 원문을 그대로 유지하며 시점 gate와 facet만 보완했다. PR07은 오대상/폐기 후 제출/자원/시도/감독의 보장을 구체화하고 host kill·polling으로 원격 상태를 면제하지 않는다. 다만 공통 잔여 작업 정의는 아직 모순된다. 안전 보호를 잃거나 위험 서명으로 waive한 변경은 발견하지 못했고 이 미정합성을 보호 상실의 FAIL로 과장하지 않았다.

| 거부 기준 | 보존된 실제 조건 |
| --- | --- |
| RJ01 | proposal-only 지시를 계약 채택/실행 승인으로 사용 |
| RJ02 | 실제 USB incarnation/최초 P* 등록이 불명확하거나 설치 뒤 key로 소급 bootstrap 인증 |
| RJ03 | -s/-t·one-device·단일 목록·PID polling을 원자적 binding/OS isolation으로 수용 |
| RJ04 | 서버/USB 주소/ID/receiver 세대가 바뀌어도 기존 승인 재사용 |
| RJ05 | auto server start/restart/reexec·TCP reconnect·fallback·부모 밖 후손 ADB 경로 허용 |
| RJ06 | OS 강제 경계 대신 저장된 boolean/UUID/검사 후 kill만 사용 |
| RJ07 | 명령/bytes/manifest/budget 미정 또는 연결 후 source/APK/계획 변경 |
| RJ08 | 첫 mutation 전 owner 확인 없음·앱 재생성/중복 intent 자동 replay |
| RJ09 | production/개인 데이터/광역 로그/공유 저장소·특별 권한/기기 정책 변경 필요 |
| RJ10 | UNKNOWN을 성공 처리하거나 retry·clear/uninstall·추가 probe로 자동 회복 |
| RJ11 | 등록/강제 경계/전면 매개 proof 결측을 residual-risk 서명으로 면제 |
| RJ12 | 문서/모형 PASS나 저자 self-review를 독립 OS/phone 검증으로 집계 |
| RJ13 | hard realtime remote stop·exactly-once·개인 데이터 손실 0의 미입증 주장 |
| RJ14 | 기존 F01/역사 증거/source locks/index를 수정하거나 문구 변경을 기술적 수정 완료로 표현 |

RJ01–RJ14는 ID·문구·처분 전체가 원안과 동일하다. R01에서 직접 명시와 다른 조항/PR가 보완한다고 구별했던 범위도 그대로며, 제안 개선을 새로 직접 들어간 기준이라고 주장하지 않는다. 가정 AS01–06 및 위험 GR01–07 register도 원안과 bytes가 같다. 최초 P* binding·actual recipient/channel binding·OS 강제 격리는 계속 비면제이고 emulator/단독 목록/serial/transport 숫자/owner 위험 수용으로 대체되지 않는다.

| 세 비면제 보장 | 회귀 판정 | 근거 |
| --- | --- | --- |
| 최초 물리 단말 결합 | PRESERVED | qualified 등록 메커니즘은 연결 전, 실제 P*/U*/C* transcript는 승인 등록 후 독립 수용. 설치/marker 소급 bootstrap과 위험 면제 금지. |
| actual channel과 실제 수신자 결합 | PRESERVED | USB/server/channel/transport/receiver 실제 자원 세대 proof와 비승계 의무 유지. G1-R01-F02 cutoff 공백은 면제로 처리하지 않음. |
| 허용 기기 집합의 OS 강제 격리 | PRESERVED | 단일 목록/one-device/private port를 OS proof로 바꾸지 않고 wrapper/후손/FD/socket/TCP/mDNS 통제와 실제 자원 수명 논증 요구. |

원 F01 요구 문장은 원안 및 PREP09와 동일하고 별도 exact 규범 채택·적용 전 계속 binding/unresolved다. `dispatch.spawn_process`와 `require_host_confinement`의 본문은 AST에서 단일 무조건 raise이며 PREP10 이후 보호 source 9개의 해시도 같다. N01/F02/F03/FC01의 독립 종결을 보존했으며 runtime 재검증을 새로 했다고 집계하지 않았다. B03·금융 authority·동기화·서명/production source는 변경하지 않았다. [전체 회귀 평가](benchmarks/real-device-gate-g1-r02/normative-regression-review.json).

## 6. 유한 단계와 승인 분리

| 단계 | 진입 조건 | 상한 | 출구/권한 경계 |
| --- | --- | --- | --- |
| A 정적 architecture·authority 심사 | 정확 O2 candidate와 원 F01/R01; 비참여 심사자 | {"reviews": 1, "seconds": 7200, "evidence_bytes": 10485760} | R02 문서 판정과 별도 owner 범위 결정; 구현/실행 승인 아님 |
| B 별도 승인 구현 후보 동결 | 구체 구현/OS/app 범위에 대한 별도 owner 승인; A 결과 | {"candidates": 1, "freeze_reviews": 1, "evidence_bytes": 20971520} | 단일 후보·scope 종료. 승인된 구현 작업 시간 상한도 착수 전 exact로 고정; 없으면 미착수 |
| C1 mock isolation·dispatch denial | B 동결·별도 V1 승인; 기존 거부 경계 보존 | {"models": 1, "trace_ids": 12, "seconds": 3600, "evidence_bytes": 10485760, "fixed_histories": 14} | mock 결과 한 묶음; 실제 USB/Android proof 아님 |
| C2 실제 host OS·USB 격리 lab | 정확 lab/host/fixture에 대한 별도 owner 승인; qualified 비개인 경로 | {"recipes": 1, "scenarios": 8, "seconds": 5400, "evidence_bytes": 20971520} | 정확 OS enforcement dossier; qualified mechanism 없으면 BLOCKED |
| C3 격리 emulator 실행·재연결 | 별도 emulator 실행 승인·물리 USB 접근 차단과 owned-QEMU/연결 결합의 자격 proof·B동결 | {"fixtures": 4, "scenarios": 4, "seconds": 1800, "evidence_bytes": 20971520} | 실제 Android 연결 동작 증거; physical USB/phone 신원 proof 아님 |
| C4 최종 APK의 실제 앱 task lifecycle | C3 수용·최종 artifact/OS 적용 범위 동결·별도 app 검증 승인 | {"fixtures": 6, "scenarios": 6, "seconds": 2700, "evidence_bytes": 20971520} | PR08 CP actual lifecycle dossier. 같은 source만으로 phone OS/ABI 적용성 수용 금지 |
| C5 host/guest 중단·부분 완료 | 별도 interruption 승인·C3/4와 같은 동결 artifact·전송경계 oracle | {"fixtures": 6, "scenarios": 6, "seconds": 2700, "evidence_bytes": 20971520} | 부분 완료/격리 수용 증거. 각 의도적 음성 fixture는 격리 종료; 다음 사전 지정 fresh fixture는 복구 retry가 아님 |
| D source/runtime/artifact·모든 CP 독립 수용 | A–C5 exact 증거와 개별 PR01–PR11 CP; 비참여 reviewer | {"decisions": 1, "seconds": 7200, "evidence_bytes": 52428800} | CP_ALL_ACCEPTED 또는 BLOCKED/REJECTED 한 판정; owner grant 아님 |
| E0 실제 단말 작업 전 owner 결정 | G1 별도 authoritative 채택/적용과 D의 모든 CP·사전 exact target/manifest | {"owner_decisions": 1, "sessions": 1, "automatic_retries": 0} | 실기기 연결 전 명시 GO 또는 DENY; O2에서는 NOT_GRANTED |
| E1 통제된 개인 단말 연결·고정 등록 | ALLOW_CONTROLLED_CONNECTION의 모든 조건; 현재 O2에서는 DENY | {"sessions": 1, "shared_E1_E3_seconds_ceiling": 600, "shared_evidence_bytes": 10485760} | IP evidence collected만; 수집/machine PASS가 수용/허가 아님 |
| E2 연결 후 모든 IP 독립 보충 수용 | 같은 살아 있는 session의 CP 보존·E1 evidence·고정 session deadline | {"decisions": 1, "must_fit_shared_session_deadline": true} | IP_ALL_ACCEPTED 또는 BLOCKED/격리; 첫 mutation GO 아님 |
| E3 owner 첫 mutation·고정 acquisition | ALLOW_FIRST_MUTATION 전부·별도 owner 첫 mutation grant | {"sessions": 1, "attempts_per_action": 1, "shared_E1_E3_seconds_ceiling": 600, "shared_evidence_bytes": 10485760} | 완료 또는 REVOKED/UNKNOWN_QUARANTINED. 세션 안 수용/owner 대기시간도 600초 이내; 무응답 승인 없음 |
| E4 분리 후 모든 POST 독립 수용·실패 처분 | 실행 종료/폐기·개인 단말 분리·이미 확보된 증거만 | {"decisions": 1, "seconds": 7200, "evidence_bytes": 52428800} | 증거 수용/위반/UNKNOWN 한 판정. 새 실행/규범 허가나 같은 세션 복귀 없음 |

**유한 검증 계획은 제안 구조로서 PASS**다. 각 단계에 허용/금지, 필수 증거, 객관적 pass/fail, 실행/독립 수용 책임, 한 후보/recipe·고정 시나리오 각 1회, 실패 BLOCKED/REJECTED 종료가 있다. B의 구현 시간 상한과 개인 세션의 exact 세부 예산은 착수/연결 전에 별도 확정해야 하며 공란이면 진행 불가다. E1–E3의 600초/10MiB는 공유 제안 ceiling이며 독립/owner 대기시간도 포함하고 무응답은 승인이 아니다.

예상 음성 fixture의 정해진 DENY/UNKNOWN은 그 관측만 PASS로 삼고 실제 새 제출·오대상 효과·자식 미회수·증거 결측은 campaign 종료다. 다음 고정 fresh fixture는 같은 revoked session의 복구 retry가 아니다. C1의 12 trace ID 중 T10의 3개 하위 이력으로 총 14개 이력을 공개했고 1시간/10MiB 상한은 늘리지 않았다. 별도 owner 범위 승인 없이 단계를 연결하는 권한은 없다.

설계 채택과 규범 적용, 구현 승인과 검증 실행, machine PASS와 독립 수용, 독립 수용과 owner 연결/첫 mutation 허가는 분리돼 있다. 유한 계획의 PASS가 PR07의 잔여 정의 모순을 해소하거나 실행 proof를 수용하는 것은 아니다. [승인·단계 평가](benchmarks/real-device-gate-g1-r02/approval-stage-separation.json).

## 7. exact-hash owner 결정 준비

수정 승인 양식은 실제 후보 MD와 수정 계약 JSON을 approval target으로 정확 pin하며 원안/옛 양식은 역사 provenance다. 승인자·시각·choice·scope·redline/목적지·효력 시점·review reference는 공란이고 채택/적용·후속 권한은 false다. 해시 생성·자체 PASS·이번 문서 처분으로 owner 서명을 만들지 않았다.

| 원 대안 | 검토 |
| --- | --- |
| O1 G1 기각·원 F01과 차단 유지 | 원 F01·현재 차단을 유지한 기각 가능. mandatory 보장을 확립할 수 없다는 사유도 별도 기록 가능. |
| O2 특정 조항 수정 요청 | 남은 G1-R01-F02의 두 JSON cutoff와 관련 hash 자료에 한정한 문서 수정 여부를 owner가 결정할 수 있다. 이번 검토가 수정하지 않는다. |
| O3 기기 없는 한정 mock만 별도 승인 | 1개 mock·12 ID/고정14이력·1시간/10MiB의 별도 선택지이며 G1 채택/기기 접근이 아니다. |
| O4 exact G1 규범 채택을 별도 승인 | 조건부 설계 채택과 별도 적용의 결정 구조는 적절하다. 다만 현재 exact dossier에는 G1-R01-F02 시간 기준 모순이 남아 채택 준비 완료로 수용할 수 없다. |

제안 범위는 특정 개인 Galaxy S23 FE·합성 테스트 앱·동결 한 세션으로 한정된다. O4는 조건부 설계 규범 채택 결정이며 exact redline·규범 목적지·F01 대체 범위·효력·통제된 적용을 별도로 정하기 전 원 F01을 바꾸지 않는다. 그 결정도 구현·emulator·연결·설치를 자동 허용하지 않는다.

**OWNER DECISION READINESS: NOT READY**는 미수정 exact dossier의 채택 준비에 대한 판정이다. owner가 O1 기각·O2 수정 여부를 결정할 수 없다는 뜻은 아니다. 두 JSON의 cutoff 모순이 남아 세 원 finding 전부 종결이라는 PASS 조건을 만족하지 못한다. 후보/규범 신원은 검증됐고 필수 보호 면제는 발견하지 못했으므로 BLOCKED/FAIL을 택하지 않았다. [결정 준비 평가](benchmarks/real-device-gate-g1-r02/owner-decision-readiness.json).

## 8. 보존·산출물·검증 한계

시작 HEAD/branch/index/staged identity를 고정했고 기존 파일 7,566개(834,449,847바이트)와 외부 frozen B03 sidecar 5개의 bytes/mode/symlink를 종료 대조했다. 기존 tracked 변경 13개는 이번 작업의 변경이 아니다. 원안·O2 candidate/양식·PREP/R01/O2 증거·source locks·원 B03를 보존했으며 새 파일은 이 보고서와 R02 디렉터리에만 있다. [전후 보존](benchmarks/real-device-gate-g1-r02/preservation.json), [최종 정합 검증](benchmarks/real-device-gate-g1-r02/final-validation.json).

필수 JSON 7개와 exact 신원/정적 참조·시점 반례·보존 자료·manifest·문서 helper를 남겼다. 새 build/DB/benchmark/scratch는 만들지 않았고 대형 임시 산출물 정리/회수량은 NOT APPLICABLE이다. 기존 자료나 cache를 삭제하지 않았다. reset·stash·clean·checkout·rebase·restage·commit·push는 0회다. T6.9 DEFERRED, formal T6.6F closure NOT AUTHORIZED, R1 CLOSED, production deployment NOT AUTHORIZED를 유지한다.

## 9. 단 하나의 다음 행동

소유자는 G1-R01-F02의 두 JSON 잔여 작업 정의를 무효화 시점으로 통일하고 관련 해시 자료를 갱신하는 문서 수정만 별도로 승인할지 결정한다.

## 10. 필수 최종 상태

```text
REAL-DEVICE GATE G1-R02:
PARTIAL

REVIEWER INDEPENDENCE:
SATISFIED

ORIGINAL PROPOSAL SHA-256:
2630cbc850c3c66fb2283160315691f656335e3d5c2681d71e54c9a747218b5a

CORRECTED CANDIDATE SHA-256:
e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279

CANDIDATE INTEGRITY:
PASS

G1-R01-F01:
INDEPENDENTLY CLOSED

G1-R01-F02:
OPEN

G1-R01-F03:
INDEPENDENTLY CLOSED

PROPOSAL CLAUSES:
12 / 12

MANDATORY PROOFS:
12 / 12

REJECTION CRITERIA:
14 / 14

THREE NON-WAIVABLE SAFEGUARDS:
PRESERVED

MACHINE DECISION / INDEPENDENT ACCEPTANCE:
SEPARATED

FINITE VALIDATION PLAN:
PASS

OWNER DECISION READINESS:
NOT READY

G1 APPROVAL:
NOT GRANTED

G1 APPLICATION:
NOT PERFORMED

MANDATORY TECHNICAL PROOFS ACCEPTED:
0 / 12

ORIGINAL F01:
BINDING — UNRESOLVED

OPERATIONAL ADB DISPATCH:
BLOCKED

LIVE ADB CALLS:
0

EMULATOR OPERATIONS:
0

PHYSICAL DEVICE ACCESSED:
NO

REAL-DEVICE EXECUTION AUTHORIZATION:
NOT GRANTED

N01 / F02 / F03 / FC01:
INDEPENDENT CLOSURES PRESERVED

GIT INDEX:
PRESERVED

HISTORICAL EVIDENCE:
PRESERVED

T6.9:
DEFERRED

FORMAL T6.6F CLOSURE:
NOT AUTHORIZED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

REPORT:
docs/real-device-gate-g1-r02-independent-contract-rereview.md

FINAL VERDICT:
PARTIAL — FURTHER TARGETED CORRECTIONS REQUIRED

NEXT ACTION:
소유자는 G1-R01-F02의 두 JSON 잔여 작업 정의를 무효화 시점으로 통일하고 관련 해시 자료를 갱신하는 문서 수정만 별도로 승인할지 결정한다.
```
