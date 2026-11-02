# Money Note — Real-Device Gate G2-R01 독립 안전성 검토

**판정: PARTIAL. 최종 분류는 B — 특정 핵심 통제의 명확화가 필요한 잠정 방어 가능 후보다.** NC01–NC08을 모두 검토했으며, 여덟 변경은 모두 현행 보호 또는 진입 요건의 약화다. 제안이 이 손실을 공개하고 단계별 승인을 분리한 점은 확인했다. 그러나 **SC10의 S23 FE 적용성을 E에서 어떤 증거와 기준으로 사전 수용할지**가 명확하지 않다. 차단 finding은 이 한 건이다. G2 승인, 규범 변경, 구현·검증·연결·mutation 권한은 부여하지 않는다.

이번 검토는 G2-P01 작성에 참여하지 않은 새 독립 세션에서 수행했다. 저자의 READY나 검증 boolean을 승계하지 않고 실제 문서·소스 bytes와 원문 요구를 대조했다. 검토자 독립성은 **SATISFIED**다. 외부 인간 검증이나 구현 기술 증명의 독립 수용을 수행했다고 주장하지 않는다.

**지배 출처와 신원 확인**

권위 제안은 [G2-P01](real-device-gate-g2-p01-restricted-campaign-proposal.md)이다. 필수 JSON 여섯 개는 계약 후보, 위협 모델, 안전 통제·잔여 위험, NC01–08 충돌, 유한 승인·검증 계획, 소유자 선택지다. 모두 파싱하고 내용을 검토했으며 제안 manifest의 문서·증거 항목 10개를 실제 SHA-256으로 대조했다. **G2 PROPOSAL: VERIFIED**는 제안의 신원·출처 확인이며 내용 승인이나 기술적 적격성 판정이 아니다.

현행 [G1 계약](real-device-gate-g1-safety-contract.md)의 SHA-256은 요청값과 정확히 일치한다.

`679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`

G1의 제목과 과거 미적용 문구만으로 현행 효력을 부정하지 않았다. N3/N4/N5 [완료 기록](benchmarks/real-device-gate-g1-n3-application/completion-record.json)의 직접 의존성 다섯 개와 [상태 주석 독립 검토](real-device-gate-g1-status-annotation-independent-review.md)를 대조했다. 주석 한 행을 제거하면 과거 승인본 `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e`가 복구된다. S1–S7의 실질 요구는 계속 구속된다.

AGENTS.md, 산출물 위생 규칙, project-state/domain-model/known-issues와 architecture의 서버 authority 경계를 읽었다. 원 [PREP01 계약](benchmarks/real-device-gate-prep01/physical-device-safety-contract.json), [PREP03 원 F01](benchmarks/real-device-gate-prep03/finding-register.json), [PREP09 독립 감사](real-device-gate-prep09-independent-dispatch-audit.md)와 F01 결정, PREP10·상위 B §27/29·C §26/34/34-B11/35/35-T69/38.8–12를 대조했다. G1이 해시로 편입한 proof·phase·admission·거부 의무도 적용한다. 원 F01의 정확한 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

[A01](real-device-gate-g1-a01-integrated-architecture.md)과 [정적 플랫폼 재평가](real-device-gate-g1-a01-static-platform-reassessment.md)의 BLOCKED 판단은 원계약의 요구 아래 유지된다. 단일 단말 운영 가정, selector, watcher/kill, USBFS close/cancel을 원 F01 해결로 전환하지 않았다. [FS1 독립 감사](real-device-gate-g1-fs1-independent-audit.md)는 순수 PLAN_ONLY 검증기의 범위로만 보존한다. FS1은 실제 operational profile·소유자 grant·물리 수신자 결합을 수용하지 않는다. N01/F02/F03/FC01의 역사적 독립 종결도 같은 범위로 보존한다.

출처 pin 37개, G1 S7 참조 12개, A01 catalogue 96개와 NC 원문 발췌 18개를 직접 대조해 불일치가 없었다. 이 집합은 중복될 수 있으며 기술 proof 개수로 합산하지 않는다. 상세 expected/actual 값은 [출처·권위 검증](benchmarks/real-device-gate-g2-r01/source-and-authority-verification.json)에 있다.

**NC01–NC08 독립 판단**

정확한 현재 요구 원문·파일·locator, 대안, 손실, 집행 가능성, 소유자 수용 항목과 개정 경로는 [독립 충돌 검토](benchmarks/real-device-gate-g2-r01/nc01-nc08-independent-review.json)에 항목별로 기록했다. 아래 표의 약화는 제안의 규범 비교이며, 실행 중인 새 취약점 여덟 건을 발견했다는 뜻이 아니다.

| ID | 현재 지배 요구 → 제안 대안 | 분류·잃는 보호 | 필요한 결정 |
| --- | --- | --- | --- |
| NC01 | 원 F01·G1-04의 실제 resource/receiver 결합 → 실물 통제·serial/server/TID 관측 | 약화. 검사와 mutation 수신자 사이의 원자 결합 상실 | 원 F01 적용 예외와 G1 S1/02/04·관련 PR/거부 기준의 상위 정합 개정 |
| NC02 | G1 S1/02의 설치 전 신뢰 등록 → 동결 owner 자료·눈에 보이는 단말/케이블·조회 대조 | 약화. 최초 P→U/C 결합의 기술 보증 상실 | 최초 등록 비면제·PR03 CP/IP·RJ02/03/11의 한정 대체 기준 명시 |
| NC03 | G1-02/05의 실제 도달 집합 강제·전면 매개 → runner/relay의 최소 OS 제한과 운영 규율 | 약화. 다른 process/FD/server/기기 경로의 전역 배제 상실 | G1 S1/02/05·PR04/06·관련 거부 기준의 정합 개정 |
| NC04 | G1 S3/06/09의 실제 사건 뒤 새 write 0 → 관측·취소 전달 뒤 새 controller admission 0 | 약화. 관측 전 및 child 회수 전 잔여 write 가능 | 실제 사건 기준과 PR07/O3 잔여 범위의 명시 변경 |
| NC05 | G1 S1/03/11의 원 F01·상위·전체 CP/IP 누적 수용 → 새 SC01–12 수용과 별도 grants | 약화. 기존 전체 증명의 진입 보호 상실 | S1/S3/S4·고정 admission/phase/거부 matrix의 상위 정합 개정 |
| NC06 | 실제 중앙 무조건 DENY·PREP01 emulator-only → 별도 operational/validation profile | 약화. 현재 전면 무실행보다 넓은 admission | 범위가 고정된 공식 예외와 의존 규범 정합화 후 별도 C/D 권한 |
| NC07 | B §29·C §34/38.12의 post-F 진입 → pre-formal-F의 소형 smoke entry | 약화. 해당 entry의 선행 순서 보호 상실 | 상위 B/C와 G1 S1/S3의 entry-only 예외; whole-F/최종 수용 의무 보존 |
| NC08 | PREP01 강제 resource cap 및 memory/app-data 예산 → 일부 hard cap·phone 전체 soft threshold | 약화. 전체 phone 자원 강제 상한 상실 | resource 계약의 hard/soft 적용 대상 명시 변경; 전체 hard cap 유지 시 후보 실행 불가 |

NC01–05는 하위 G2 문서 하나의 예외나 일반적인 위험 동의로 해결할 수 없다. G1 S1의 누적·비면제 관계와 해당 편입 의무를 바꾸는 **범위가 한정된 상위 정합 규범 개정**이 필요하다. NC06–08도 해당 PREP01·B/C·G1의 공식 예외와 의존성 정합화가 필요하다. 역사 finding·감사 bytes를 다시 쓰는 방식은 허용되지 않는다. 이번에는 어느 예외도 작성·승인·적용하지 않았다.

초기 신원 결합·실제 승인 채널과 수신자 결합·OS 강제 기기 격리는 **현재 면제 불가**다. 그 의무를 다른 모델로 바꾸려면 정당한 규범 개정이 먼저 성립해야 하며, 그 이후에도 원 F01의 기술적 해결이나 proof 수용으로 기록할 수 없다. 제안된 새 SC의 결측을 잔여 위험 서명으로 면제하는 경로도 없다.

**통제의 실질 집행과 개인 데이터 안전성**

[통제 집행성 검토](benchmarks/real-device-gate-g2-r01/control-enforceability-review.json)는 SC01–12를 사람의 운영 절차, 기존 구현의 부분 근거, 앞으로 구현·검증할 기술 경계로 구별한다. 현재 G2 통제의 기술적 독립 수용은 **0개**다. 미구현 통제 전부를 이번 리뷰의 새 차단 finding으로 나열하지 않았다. 후속 C/D/E의 구현·증거·독립 수용은 제안 자체가 이미 요구하는 필수 진입 조건이다.

격리 application ID `kr.re.hjkerman.money_note.devicegate`, 독립 signer, private synthetic storage, backup/개인 기능 제외는 정상 Android에서 직접 개인 데이터 접근을 줄일 수 있는 수단이다. 독립 package만 확인해서는 부족하다. 최종 merged APK의 permission/component/export/provider/shared UID와 고정 코드의 접근 경로, 공급망·서명·ABI 및 실제 전송 bytes까지 함께 확인해야 한다. 별도 계정만으로는 Money Note의 단일 장부를 격리하지 못하므로 자기 소유 합성 backend/DB/fixture를 함께 요구하는 제안은 타당하다. 서버 금융 authority와 모바일 wire·저장·복구·generation·Offline/pending 경계도 보존해야 한다. Android의 UID 기반 sandbox는 격리 수단이며 kernel/PM 결함까지 포함한 무피해 보증은 아니다. [Android 공식 sandbox 설명](https://source.android.com/docs/security/app-sandbox).

APK provenance는 신뢰 source·dependency/build 입력·compiled manifest·독립 signing certificate·ABI와 외부 승인 digest를 함께 묶어야 한다. `SealedAPK/admit_apk`의 기존 근거는 검증 후 pathname 치환을 막는 일부 보호다. hash·서명 일치만으로 악성 build나 결함 부재가 증명되지는 않는다. 기존 test package 부재와 설치 후 독립 checkpoint를 요구하고 replace/grant/downgrade를 금지하는 것은 개인 앱 덮어쓰기 예방에 도움이 된다. x86_64 emulator APK를 S23 FE APK로 인정하지 않았다.

고정 literal plan, 외부 신뢰 기록의 expected digest, action 순서/동시 진입 차단·host action당 1회 admission은 기술적으로 집행 가능한 방향이다. FS1의 self-consistent hash를 운영 승인으로 전환할 수 없다. 범용 shell·임의 argv/path/endpoint, 숨은 wrapper·후손 실행, 자동 server 시작/restart/reexec/reconnect/fallback도 실제 경계에서 거부해야 한다. ADB client가 server를 자동 시작하는 공식 동작과 RSA prompt의 host debugging 승인 의미를 확인했다. prompt는 phone의 물리 신원 인증이나 캠페인 승인이 아니다. [Android 공식 ADB 문서](https://developer.android.com/tools/adb).

관측된 단절·모호성·취소 뒤 새 controller admission을 막고 host 자식을 stop/reap하는 것은 가능하다. 그러나 `t_event`, `t_observe`, latch, kill, reap, USB 단절, remote task 종료, durable commit, ACK는 별개다. NC04는 실제 사건 이후에도 아직 admission한 child가 write할 수 있음을 허용하려는 변경이다. PM/앱이 이미 받은 작업은 host 종료 뒤에도 지속할 수 있다. libusb 역시 취소 시 일부 데이터가 이미 전달됐을 수 있음을 설명한다. [libusb 공식 취소 계약](https://libusb.sourceforge.io/api-1.0/group__libusb__asyncio.html#cancellation).

현재 `main_devicegate.dart`는 매 시작 `_smoke()`를 호출하므로 앱 재생성·중복 intent·재부팅에 대한 durable consumed claim이 새로 필요하다. 효과 전 claim, 충돌·손상·interruption 시 보수적 거부와 자동 재실행 금지는 필수다. 파일 rename 하나를 내구성 증명으로 사용할 수 없다. at-most-once 시도와 remote exactly-once 완료는 구별한다.

UNKNOWN_QUARANTINED는 성공·rollback·무피해 판정이 아니다. 이미 받은 증거만 고정하고 추가 readback/reconnect/stop/clear/uninstall/retry 없이 독립 처분해야 한다. 실제 승인 범위 위반은 FAIL_VIOLATION으로 기록하며 UNKNOWN으로 면제할 수 없다. 늦은 ACK도 폐기된 세션을 열지 못한다.

정상 종료에도 APK/private synthetic 파일·PM 기록·컴파일 cache·기존 USB trust는 남을 수 있다. 공유 CPU/RSS/저장·전력·발열은 다른 앱과 시스템에 영향을 줄 수 있고, 메모리 압박에 따른 process 종료나 저장 고갈 위험도 완전히 막지 못한다. 합성 output 1MiB는 전체 app-data 상한이 아니며 연결 600초와 grant 120초는 remote hard termination 기한이 아니다. 자동 uninstall을 하지 않는 정책과 별도 owner 정리 결정, 완전 원상 복원 불가를 사전 고지해야 한다. 예방 가능한 범위 이탈과 줄이거나 수용할 수밖에 없는 OS·공유 자원·잔류 위험은 [기기·데이터 위험 검토](benchmarks/real-device-gate-g2-r01/device-data-risk-review.json)의 R01–R09에 분리했다. 사고율 자료가 없어 수치 확률을 부여하지 않았다.

**차단 finding 한 건: R01-B01**

SC10은 최종 APK에서 INTERNET을 제거하고 같은 승인 ADB transport의 제한 localabstract stream과 peer/session 결합을 통해 소유 합성 backend만 쓰도록 요구한다. 현재 앱은 INTERNET과 emulator 전용 `10.0.2.2:18081` HTTP를 사용하고 해당 relay는 없다. 이 미구현 사실 자체는 예정된 C/D 작업이며 이번 B 판정의 이유가 아니다.

문제는 **필수 통제의 사전 수용 경계**다. [SC10](benchmarks/real-device-gate-g2-p01/safety-controls-and-residual-risks.json)의 `/controls/9`는 phone SELinux/ABI 적용성이 미확인이라고 한다. [유한 계획](benchmarks/real-device-gate-g2-p01/finite-authorization-and-validation-plan.json)의 D(`/stages/3`)는 최종 APK/ABI의 peer/SELinux 증거를 요구하면서 emulator 결과를 phone OS 적격성으로 전환하는 것을 금지한다. E(`/stages/4`)는 모든 SC 충족을 요구하고 F 이전 기기 접촉을 금지한다. 이 상태에서 E가 요구할 target 대응 근거와 G의 첫 승인 launch에서만 알 수 있는 통신 가용성 실패의 경계가 정해져 있지 않다.

INTERNET 권한과 UNIX local socket/peer credential API의 존재는 확인했다. 이로부터 특정 Samsung build의 adbd/app domain 정책이나 승인 stream/session 결합을 자동 추론할 수는 없다. AOSP 문서는 제조사·기기별 SELinux 정책을 명시한다. 이는 **에뮬레이터 결과만으로 해당 Samsung 경로를 수용할 수 없다는 추론**의 근거이며, 그 경로가 실제로 차단된다는 증거는 아니다. [INTERNET API](https://developer.android.com/reference/android/Manifest.permission#INTERNET), [LocalSocket API](https://developer.android.com/reference/android/net/LocalSocket), [기기별 SELinux 정책](https://source.android.com/docs/security/features/selinux/customize).

최소 명확화는 SC10 조항 하나에서 **E가 수용할 사전 증거·S23 FE OS/ABI 대응 범위**, 사전 입증할 **IP 금지·잘못된 peer/session 거부·fallback 0·bytes/요청 한도**, G에서만 확인 가능한 **통신 가용성 실패의 처분**을 구별해 지정하는 것이다. 정확 단말의 성공 통신을 반드시 사전 실증하라는 새 의무를 부과하지 않는다. 안전 속성이 사전에 충족되고 가용성만 불확실한 경우와 필수 안전 속성 자체가 미검증인 경우를 분리해야 한다. 후자가 남으면 계속 DENY이며 위험 서명이나 첫 phone 실행으로 대체할 수 없다.

이 명확화가 어느 evidence로도 성립하지 않으면 보류를 유지해야 한다. 새 lab campaign·장치 조회·넓은 감사 프로그램을 요구하거나 수행하지 않았다. [독립 finding](benchmarks/real-device-gate-g2-r01/independent-findings.json)에 정적 trigger·영향·최소 종료 기준을 기록했다. 실제 exploit, SELinux 거부 또는 통신 성공을 관측했다는 주장은 없다. 새로운 아홉 번째 규범 충돌도 선언하지 않았다.

**여덟 승인 경계의 분리**

| 순서 | 경계 | 독립 판단·남은 권한 |
| --- | --- | --- |
| 1 | G2 계약 제안 | 역사 G2-P01만 존재. 검토나 실행 권한을 만들지 않음 |
| 2 | 독립 검토 | 이번 R01만 완료. 차단 finding 1건, 규범·기술 수용 없음 |
| 3 | 소유자 규범 결정 | 별도 exact 지시·redline 검토·승인·지정 적용·독립 대조·효력 기록 필요 |
| 4 | 승인된 구현 | B 효력 뒤 별도 C GO 및 host-only 구현·감사 필요 |
| 5 | 에뮬레이터 검증 | 별도 D GO·물리 USB 비노출 enclave·EV01–12·독립 수용 필요 |
| 6 | 독립 preflight | 완성된 사전 manifest·모든 SC 수용 필요. 이번 검토는 E 수용 아님 |
| 7 | 물리 연결 승인 | E 이후 owner exact F 연결/read-only grant 필요. 설치/marker/launch 0 |
| 8 | 첫 mutation 승인 | F 등록 보충 수용 뒤 owner 별도 G grant 필요. install checkpoint 실패면 launch 없음 |

어느 단계도 다음 단계의 권한을 내포하지 않는다. 소유자·검토 대기 중 자동 연장도 없다. 연결 전에 사전 identity·계획·예산을 임의로 비워 두었다가 F에서 보충할 수 없고, 실제 U/C/T 등 등록 관측은 사전 조건과 대조하는 별도 instance 증거다. 이후 예외도 물리 세션 한 번과 별도 승인된 validation 범위로만 제한해야 한다. [규범·권한 경계](benchmarks/real-device-gate-g2-r01/normative-amendment-boundaries.json).

**실행 가능성 판정과 소유자 선택**

A를 선택하지 않았다. 보호 손실을 정직하게 공개하고 합리적인 통제를 열거했다는 이유만으로 필수 통제의 수용 기준이 완성됐다고 볼 수 없다. SC10의 현재 불명확성을 일반 잔여 위험으로 넘길 수도 없다. C도 선택하지 않았다. 현재 자료는 제한 relay·격리 앱·고정 계획 모델의 기술적 불가능성이나 필수 개인 데이터 접근을 입증하지 않는다. 최소 한 항목의 명확화로 판단할 여지가 있다.

따라서 **B. Potentially defensible, but a specific critical control or assumption must be clarified.**로 판정한다. G2의 규범 채택·개정 방향에 대한 긍정 결정 준비는 **NOT READY**다. 소유자는 기존 금지를 유지하거나, 별도 지시로 SC10의 수용 기준만 문서로 명확히 할 수 있다. 이 선택지를 제시한 것은 어느 선택을 실행하거나 승인한 것이 아니다. [소유자 선택지](benchmarks/real-device-gate-g2-r01/owner-decision-options.json).

**작업·증거 보존**

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 기존 tracked 수정 13개와 미추적 자료는 시작 상태로 취급했다. Git index SHA-256은 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged 항목 SHA-256은 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. [시작 기준선](benchmarks/real-device-gate-g2-r01/preservation-before.json)에 기존 8,250개 경로와 외부 frozen sidecar 다섯 개를 기록했다. source lock 27개도 이 범위에 포함한다. 종료 대조는 [보존·정적 검증](benchmarks/real-device-gate-g2-r01/validation-and-preservation.json), 새 산출물 신원은 [증거 manifest](benchmarks/real-device-gate-g2-r01/evidence-manifest.json)에 기록한다. ignored runtime/cache/production 전체를 전수 감사한 것은 아니다.

이번 변경은 이 보고서와 새 R01 dossier뿐이다. 코드·규범·기존 증거·source lock·HEAD·index·staged content를 변경하지 않았다. reset/stash/clean/checkout/rebase/restage/commit/push를 수행하지 않았다. ADB(help/version 포함), ADB server socket 요청, USB/Android 열거·접근, emulator 동작, APK 설치와 production API/데이터 접근은 모두 0이다. 문서/JSON 구조·원문·hash·로컬 링크·보존만 확인했으며 npm/backend/Flutter 빌드·runtime 테스트는 실행하지 않았고 과거 PASS를 이번 proof로 집계하지 않았다. 기술 proof 수용은 계속 0/12다.

대형 임시 실험 산출물 정리는 NOT APPLICABLE이다. 보존 기준선은 필수 증거로 남겼고 임시 DB·build·cache를 생성하거나 기존 파일을 삭제하지 않았다. 원 B03·T6.9 DEFERRED·R1 CLOSED·production 미승인 상태를 유지한다.

```text
REAL-DEVICE GATE G2-R01:
PARTIAL

REVIEWER INDEPENDENCE:
SATISFIED

G2 PROPOSAL:
VERIFIED

NC01–NC08:
8 / 8

DEFENSIBLE RESTRICTED CAMPAIGN:
CONDITIONAL

NON-WAIVABLE SAFETY CONFLICTS:
최초 신원·실제 채널/수신자 결합·OS 강제 격리는 현행 면제 불가이며 NC01–08의 공식 정합 개정 전에는 원 F01/G1을 모두 적용한다.

DEVICE-DATA SAFETY:
합성 전용·독립 package/signer·최소 권한으로 직접 노출을 줄일 수 있으나 SC10 사전 수용 기준과 후속 필수 검증이 남아 있다.

RESIDUAL RISKS:
오대상·관측 지연·취소 후 원격 지속·부분 완료·APK/파일/PM 잔류·공유 자원/발열/전력·OS/공급망 결함과 복구 불확실성은 제거되지 않는다.

BLOCKING FINDINGS:
1

OWNER DECISION READINESS:
NOT READY

G2 APPROVAL:
NOT GRANTED

ORIGINAL F01:
BINDING — UNRESOLVED

EFFECTIVE G1:
BINDING — UNCHANGED

G1 TECHNICAL PROOFS ACCEPTED:
0 / 12

ADB OPERATIONAL DISPATCH:
BLOCKED

PHYSICAL DEVICE ACCESSED:
NO

REAL-DEVICE EXECUTION AUTHORIZATION:
NOT GRANTED

GIT INDEX:
PRESERVED

HISTORICAL EVIDENCE:
PRESERVED

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
B. Potentially defensible, but a specific critical control or assumption must be clarified.

NEXT ACTION:
기존 실기기 금지를 유지한 채 SC10의 E 사전 수용 기준 한 항목만 문서로 명확히 하십시오.
```
