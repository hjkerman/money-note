# Real-Device Gate G1-N5 — 적용 후 독립 정합성 검토

**판정: PASS — 승인된 문서의 exact 적용 정합성 범위. 차단 finding은 0개다.** 실제 [적용 문서](real-device-gate-g1-safety-contract.md)는 승인된 후보·패치 결과와 정확히 같다. 이 판정은 기술 proof 수용, 원 F01 해결, 구현·ADB·emulator·단말·설치·Real-Device Gate·R1·production 실행 허가가 아니다. 소유자가 요구한 별도 완료 기록은 이 검토자가 발급하지 않았으며, 적용 책임자는 이 N5 PASS와 검토된 N4 기록·실제 대상 hash를 대조한 뒤 문서 적용 완료를 기록해야 한다.

**검토자의 독립성과 한계.** fork_turns=none의 새 검토 맥락에서 시작했으며 원안·O2/O3 정정·보충안 작성, 관련 구현·측정·규범 적용에 참여하지 않았다. 같은 orchestration 안의 별도 agent이며 외부 인간 검토자나 별도 최상위 세션은 아니다. 앞선 적용 전 preflight와 이번 적용 후 검토는 한 번의 N5 문서 검토의 두 단계다. 적용자의 PASS·boolean을 독립 증거로 승계하지 않고 실제 파일과 원문·해시를 다시 대조했다. 제품 모듈을 import하거나 시험하지 않았다.

**정확한 신원.** 아래 값은 실제 파일 bytes에서 독립 재계산했다. [전체 신원 대조](benchmarks/real-device-gate-g1-n5-consistency/postapplication-identities.json)에 세부 결과를 보존한다.

| 대상 | 검증한 SHA-256 |
| --- | --- |
| 실제 목적지·승인 후보 전문 | `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e` |
| 승인 원 패치·N4 보존 사본 | `05141e21d61945703073b0c4afbcf24ba6eb8e2cdce020dc1fffbb66d7452d9c` |
| 승인 O2 원본 | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| 검토한 N4 application-record.json | `8b5d5e17ed88829a85b138a09f085294342fd455822f9345e388e9ca285ce5e7` |
| 검토한 N3 owner-authorization-decision.json | `54015b360bf8454c7eaad27ef4d59effbe6dd53bd304830dffd57d7dbd43950c` |
| 현행 owner 원문 로컬 전사 | `d3ea5e9264bf9d1fa7bbf8ab18f939ac8c141b1c677e06b7e1f320213ec45eba` |
| N2 독립 보고서 | `e328b36477f763cfcd7df5301092764323cb699b2677e459b3c1ea2491a95189` |
| N2 dependency lock | `a14fb26d84df0b7774d42a953e129e7a4e09105b2f4c85e59a6706fc7bf3ba47` |

N2 입력 99개, N2 보고서와 manifest가 고정한 artifact 16개의 실제 SHA·크기를 재검증했다. N2 참조 목록의 15개 원 JSON에서 path/SHA 참조를 새로 발굴해 178건 전체 집합과 실제 파일을 대조했다. N3/N4 기록의 참조 17건도 각각 원 파일과 일치한다. 승인 patch는 `/dev/null`에서 지정 목적지 하나만 추가하는 164행이며, 추가행을 메모리에서 복원한 bytes가 실제 목적지 및 승인 후보와 정확히 같다. 목적지는 21,639바이트의 일반 파일이며 symlink가 아니다. 검토자는 패치를 다시 적용하거나 승인 artifact·후보·목적지를 수정·재생성하지 않았다.

적용 전 독립 기준선과 root 기준선에는 실제 목적지 부재가 기록돼 있다. 적용 후 실제 목적지 bytes는 위 exact 신원이다. N4가 기록한 두 `git apply --no-index` 명령은 check와 한 번의 적용으로 한정돼 있으며, 기록된 unused isolated index는 실제로 부재다. 검토자가 그 명령을 재실행하거나 명령 이력을 외부에서 암호 인증한 것은 아니다. 실제 결과와 index·원본 보존을 별도로 확인했다.

**원 F01과 상위 규범.** 적용 문서 S1의 인용은 PREP09의 실제 `requirement_ko`와 정확히 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

원 F01은 계속 구속되며 미해결이다. 적용 문서는 원 F01 AND 상위 적용 의무 AND 모든 적용 G1 의무를 누적하고, 충돌·정합성 미입증이면 BLOCKED로 종료한다. no-other-target·transport ID·반복 probe·격리·위험 수용이 원 결합을 대신하지 못한다. B §27·§29, C §26·§34·§34-B11·§35·§35-T69·§38의 8개 실제 절은 제목·행 범위·절 bytes hash·전체 파일 hash를 모두 재대조했다. Android durability, 원 B03 증거, whole-F, 별도 기기 gate·R1·rollout/deployment 요구가 남는다. 원 N01/F02/F03/FC01 독립 종결과 해당 source·역사 manifest는 변하지 않았으며, 이를 원 F01 해결이나 새 기술 proof 수용으로 전환하지 않았다.

**12개 조항·12개 proof·14개 거부·세 보호.** 적용 문서의 실제 12개 조항 문단을 승인 O3 object 및 보충 change map과 대조했다. G1-01의 대체에서 누적 보충으로의 변경과 G1-12의 당시 작성 권한 서술만 명시 변경됐고 나머지 10개 조항은 승인 원 object와 정확히 같다. 12개 proof는 원 object hash, 필수 의무·증거 및 CP/IP/POST facet 전체를 양쪽 원 matrix와 대조했다. 36개 facet의 독립 수용은 PENDING, authority는 NOT_GRANTED, evidence reference는 null이다. 기술 proof 수용은 계속 **0/12**다.

14개 RJ의 거부 원문과 KEEP_BLOCK 처분은 적용 문서 표에 모두 일치한다. 최초 단말 신원 결합·실제 승인 채널과 수신자 결합·OS 강제 기기 격리는 면제할 수 없다. AS01–AS06와 GR01–GR07은 N3에서 모두 미수용으로 남고 문서 적용이 위험 수용·waiver를 생성하지 않는다. 상세 검사는 [의무 보존 결과](benchmarks/real-device-gate-g1-n5-consistency/postapplication-obligation-preservation.json)에 있다.

무효화 사건을 잔여 작업의 cutoff로 유지한다. 실제 제출 시작, 원격 task 시작, durable commit, ACK, host 관측·집행 시점이 구별된다. 폐기 뒤 새 제출/write/자원 취득/buffer 이동은 0이며 지연된 관측은 유예가 아니다. 이미 같은 action/receiver/channel에 제출된 bounded 작업만 잔여 범위이고, 결과·remote 종료 미입증은 UNKNOWN_QUARANTINED다. 실제 위반은 UNKNOWN으로 면제하지 않는다. host stop/reap이나 늦은 ACK는 remote 종료·rollback 또는 폐기된 세션의 권한 복구를 증명하지 못한다. 추가 mutation/readback/reconnect/자동 cleanup 금지가 적용 문서에 그대로 있다. 최초 연결·첫 설치/marker/launch·후속 mutation에는 각각 독립 CP/IP 수용과 별도 owner grant가 필요하다.

**작성 시점 문구와 후속 권한 사건.** 적용 파일 5행의 ‘미적용 후보’, G1-12의 ‘이번 결정은 문서 작성만 승인’, S6의 ‘현재 이 적용 승인은 없다’는 승인된 후보 작성 당시 상태를 동결한 문장이다. 이 문장들은 exact 승인 bytes이므로 수정하지 않았다. 후보 작성 기록은 01:33:35 UTC, N2 검토 기록은 01:58:20 UTC, 현행 N3 결정 기록은 02:45:23 UTC, 독립 preflight는 02:50:12 UTC, 실제 N4 적용은 02:51:02 UTC로 구별된다. 이 시간은 로컬 기록 사건이며 정확한 owner 메시지 결정 시각은 null로 남겼다.

현행 owner 원문은 그 후의 별도 exact 규범·문서 적용을 명시 승인하고 적용 후 독립 검토 전 완료 선언을 금지한다. N3 기록은 작성 당시 metadata를 후속 N3/N4/N5 사건과 분리한다. N4는 실제 문서를 만들었지만 N5 PENDING·NOT COMPLETE로 기록했다. S6 자체도 N2·N3·N4·N5·완료 사건을 구분한다. 따라서 **이 exact dossier를 함께 읽는 범위에서 적용 정합성을 차단하는 시간적 모순은 없다.** 목적지의 현재형 문장만 떼어 최신 승인 상태나 실행 허가로 사용하면 안 된다. 이번 N5 PASS는 후속 독립 검토 사건이며 아직 없는 완료 기록을 소급 생성하지 않는다. [독립 시간·권한 평가](benchmarks/real-device-gate-g1-n5-consistency/postapplication-temporal-authority-review.json)에 근거와 한계를 남겼다.

owner 신원은 현재 세션의 사용자가 명시적으로 소유자라고 밝힌 범위에서 평가했다. 전사 hash는 로컬 전사의 신원이며 메시지 전송 bytes·외부 실명·암호 서명·정확한 메시지 시각을 새로 인증한 것이 아니다. 문서 적용 권한은 구현·기술 수용·연결/read-only·첫 mutation·실행 권한과 계속 분리된다.

**원본·index·무관 작업 보존.** N2 역사 기준선 8,009개, N5 독립 적용 전 기준선 8,028개, root 적용 전 기준선 8,072개를 각각 실제 파일 bytes·mode 및 기록된 symlink 속성과 대조했다. 변경·누락은 0개다. 외부 B03 frozen sidecar 5개와 모든 최초 preflight/helper 실패 증거 14개도 보존됐다. 허용된 N3/N5 증거·보고서와 목적지 외의 새 파일은 없다. 무시된 runtime·production 전체를 전수 감사했다고 주장하지 않는다.

HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`, Git index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged entries SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`로 세 기준선과 일치한다. 검토 중 N3 입력들과 실제 대상·index가 변하지 않은 것도 종료 전에 확인했다.

**검증 범위와 산출물.** 적용 후 정적 검사 **458개 통과, 차단 finding 0개**다. [검사 목록](benchmarks/real-device-gate-g1-n5-consistency/postapplication-checks.json)과 [기계 판정](benchmarks/real-device-gate-g1-n5-consistency/postapplication-result.json)을 보존했다. 이 수는 문서·신원 검사 수이며 기술 proof 분모가 아니다. 운영 거부 함수는 제품 모듈 import 없이 AST에서 무조건 raise임을 확인했다. 사용자의 명시적인 문서 전용 제한에 따라 npm/backend/Flutter 시험도 실행하지 않았다. ADB 도움말 포함 호출·emulator·물리 단말·API·OS 변경·제품 구현·index 변경·커밋·푸시는 모두 0이다. 운영 dispatch는 CLOSED/DENY이며 production·T6.9를 재개하지 않았다.

초기 preflight helper의 형식 오류 및 parent가 전달한 판정 전 인프라 중단 이력은 보존했다. 검증기 형식 보정만 있었고 승인 artifact 변경이나 별도 규범 재심사는 없었다. 대형 임시 산출물은 NOT APPLICABLE이며 새 정적 증거만 추가했다. 기존 파일·DB·cache를 삭제하지 않았다.

본 보고서와 기계 판정의 exact hash는 순환 참조를 피하도록 [N5 적용 후 증거 manifest](benchmarks/real-device-gate-g1-n5-consistency/postapplication-evidence-manifest.json)에 고정한다. 적용 책임자가 후속 완료 기록에 사용할 판정은 **PASS — exact 문서 적용 정합성**이다. 원 F01은 binding·unresolved, 기술 proof는 0/12, 기기 실행 권한은 계속 미부여다.
