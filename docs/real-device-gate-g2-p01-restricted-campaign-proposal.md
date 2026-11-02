# Real-Device Gate G2-P01 — 단일 S23 FE 제한 캠페인 안전 계약 제안

**판정: READY — RESTRICTED G2 CONTRACT CANDIDATE READY FOR INDEPENDENT REVIEW.** 독립 검토할 수 있는 제한 후보를 작성했다. G2는 **PROPOSED — NOT APPROVED**이며 규범·구현·기기 권한을 만들지 않는다. 원 F01은 **BINDING — UNRESOLVED**, 유효 G1은 **BINDING — UNCHANGED**, 기존 G1 아키텍처 판정은 **BLOCKED**, G1 기술 proof 수용은 **0/12**다. 현재 유일한 운영 판정은 **DENY**다.

유효 [G1 계약](real-device-gate-g1-safety-contract.md)의 SHA-256은 `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`로 일치한다. N3/N4/N5 효력 완료와 후속 상태 주석 독립 검토를 함께 확인했다. 제목의 후보 이력이나 superseded O2 대체 논리를 현행 규범으로 사용하지 않았다. S7의 12개 해시 참조와 A01 출처 목록 96개를 현재 bytes에 대조했다. [출처·권한 확인](benchmarks/real-device-gate-g2-p01/source-and-authority-verification.json).

소유자의 “다른 Android를 의도적으로 연결하지 않는다”는 진술은 운영 가정이다. 단말 교체·relay·호스트 침해·관측 사이 변경을 OS가 막았다는 증거가 아니다. 한 S23 FE에서도 reset·재열거·server/adbd restart·옛 FD/queue·앱 재실행·부분 완료는 남는다. 따라서 이 후보는 원 F01의 아래 보증을 만족한다고 주장하지 않는다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

정확한 원문은 [PREP09 F01](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json)의 `/requirement_ko`다. [PREP10 결정](real-device-gate-prep10-f01-architecture-decision.md), [P01 proof matrix](benchmarks/real-device-gate-g1-p01/pr01-pr12-proof-matrix.json), [A01](real-device-gate-g1-a01-integrated-architecture.md), [정적 플랫폼 재평가](real-device-gate-g1-a01-static-platform-reassessment.md)의 차단 근거를 보존한다. USBFS 취소/close와 watcher는 실제 사건 뒤 모든 새 write를 막는 G1 fence가 아니다.

**후보의 범위와 선행 조건.** 소유자 통제 Galaxy S23 FE 1대·비갱신 물리 세션 1회·격리 test package·합성 fixture·host의 합성 backend·고정 smoke만 대상으로 한다. 전체 금융 correctness/performance·power-loss·T6.9·R1·배포 수용을 위한 시험이 아니다. 원 F01/G1의 한정 예외와 상위 정합 개정이 별도 승인·독립 검증·효력 기록으로 성립하기 전에는 이 후보로 어떤 연결도 할 수 없다.

기존 USB debugging과 정확한 승인 host trust가 준비된 단말만 대상으로 제안한다. 이번 후보는 디버깅 활성화·새 RSA trust prompt 승인·pairing·wireless ADB·device-wide 설정 변경을 포함하지 않는다. 미준비·준비 확인 불가라면 중단한다. 별도 준비를 자동으로 승인하거나 추가하지 않는다. 실제 serial/build·signer·APK·ABI·예산은 아직 수집하지 않았다. **E 전에 소유자의 기존 식별 자료로 모든 사전 값을 동결할 수 없으면 F 연결 승인을 요청할 수 없다.** F는 정해진 값을 실제 instance와 대조하는 단계다.

**아홉 위험의 평가.** 심각도는 피해 범위에 대한 정성 판단이며, 가능성은 측정된 사고율이 아니다. 각 위험의 exposure·예방·탐지·복구·잔여 위험·필수 거부 조건 전문은 [위협 모델](benchmarks/real-device-gate-g2-p01/restricted-threat-model.json)에 있다. 아래 운영 통제는 기술 강제로 집계하지 않는다.

| 위험 | 노출·심각도와 단일 기기 가정의 영향 | 주요 통제·복구 한계 | 반드시 거부하는 경우 |
| --- | --- | --- | --- |
| R01 다른 물리 기기 | install/launch·조회 오도달, 치명적. 다른 기기 우발 노출은 줄지만 확률 미측정·0 아님 | 소유자 실물/케이블 대조, 단일 target 관측, 고정 selector. 원자 결합·OS 독점 미보장. host 회수만 가능 | 수!=1, identity 불명·불일치, 교체/relay 의심 |
| R02 개인·운영 데이터 피해 | 올바른 단말에서도 sandbox/OS 결함·공유 자원 노출, 치명적. 단말 수와 무관 | 독립 package/signer·private synthetic·최소 권한. 손실 0·완전 복구 보장 없음 | 개인/운영/공유 경로·광역 로그·특별 권한 필요 |
| R03 잘못되거나 악성 APK | 공급망·검증 뒤 치환·ABI 오류, 치명적. 단말 수와 무관 | 출처·의존성·compiled manifest·서명·봉인 bytes 감사. hash만으로 선의 증명 불가 | 출처/bytes/signer/ABI 결측, 기존 test package 충돌 |
| R04 계획 밖 동작 | 범용 명령·동시 실행·replay, 높음 | 독립 expected digest, literal plan, host 1회 admission, 앱 durable claim. 위반은 별도 실패 | 추가 argv/path/동작·빈 필드·self-attestation·중복 허용 |
| R05 취소 후 원격 지속 | install/PM·이미 받은 앱 작업, 높음. 동일 단말에서도 가능 | host stop/reap과 remote task/commit 분리. UNKNOWN 격리·자동 정리 없음 | 무제한 job/retry·잔여 지속 범위를 승인하지 않음 |
| R06 네트워크 이탈 | production/다른 backend·서비스, 치명적. 단말 수와 무관 | INTERNET 제거, 제한 ADB stream relay와 host egress. 현재 미구현 | IP 통신·임의 peer/route·fallback 가능, SELinux 경로 실패 |
| R07 재접속·세대 변화 | reset·server/adbd restart·TID 재사용·옛 queue, 높음 | 관측 즉시 새 controller action 금지·권한 폐기. 실제 사건부터 회수까지 전송 가능 | 단절·세대 불연속·감독 상실·자동 reconnect |
| R08 지속 변경 | APK/private 파일·PM/캐시·기존 trust 잔류, 중상 | 잔류 효과 사전 선언. 정상도 자동 uninstall 없음. 추후 별도 owner 정리 결정 | 새 설정/권한/trust 변경 필요, 잔류 수용 거부 |
| R09 자원·방해 | CPU/RSS/저장·전력·발열, 높음. 한 기기에 집중 | bytes/요청/file hard cap, 시간/RSS/열 soft threshold 분리. PM 전체 hard cap 미보장 | 한도 누락·cap 실패·과열·여유 부족·soft를 hard라 주장 |

**최소 제안 구조.** 커널 원자 fence나 상시 기기 agent가 이미 존재한다고 가정하지 않는다. 필요한 제안 구성은 네 묶음이다. 각각 C의 별도 구현 승인과 감사가 필요하며 현재 코드 변경은 0이다.

| 구성 | 확인된 현재 지원 | 새로 검증해야 할 집행과 실패 처리 |
| --- | --- | --- |
| 고정 plan/grant admission·journal·1회 runner | [guards.py](../scripts/devicegate/guards.py)의 APK 봉인·host child 회수·FS1 순수 parser | 별도 operational profile, 독립 digest 입력, action 순서/동시 진입 차단, 관측 폐기 latch. 실패 시 새 admission 0·host 회수·UNKNOWN |
| 제한 host 실행/통신 경계 | [dispatch.py](../scripts/devicegate/dispatch.py)·[smoke.py](../scripts/devicegate/smoke.py)의 중앙 무조건 DENY | 고정 실제 tool/IPC/FD·관리 server 수명·host egress 정책. 다른 target의 OS 전역 독점으로 표현 금지. auto start/restart/reconnect/fallback를 flags만으로 수용 금지 |
| one-shot 격리 앱 | [flavor](../mobile/android/app/build.gradle.kts)·[manifest](../mobile/android/app/src/devicegate/AndroidManifest.xml)·[Activity](../mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt)의 독립 package/signer/private result | [main_devicegate.dart](../mobile/lib/main_devicegate.dart)는 매 시작 `_smoke()`를 호출하므로 durable claim이 필요. 부작용 전 claim, 중복·재생성·재시작 replay 금지. 파일 rename만으로 내구성을 주장하지 않음 |
| 제한 stream relay·합성 backend | [isolation.dart](../mobile/lib/devicegate/isolation.dart)는 emulator `10.0.2.2:18081`의 제한 HTTP. [backend.py](../scripts/devicegate/backend.py)는 task-owned synthetic DB·loopback 서버 | 최종 APK INTERNET 제거, 같은 ADB transport의 제한 localabstract stream→고정 relay→소유한 `127.0.0.1:18081`만 사용. peer/session·route·body·response·egress 제한. phone ABI/SELinux 적용성은 미확인이고 D 실패면 종료. Wi-Fi/forward/reverse 대체 금지 |

[FS1 독립 감사](real-device-gate-g1-fs1-independent-audit.md)는 순수 synthetic-only validator를 수용한 기록이다. 외부 digest 검증 원칙은 참고할 수 있으나 `fs1-model`/`NOT_GRANTED`와 emulator endpoint를 실제 실행 profile로 해석할 수 없다. 실 runtime 호출도 없다. 현재 x86_64 emulator build 절차를 S23 FE APK 적합성으로 전환하지 않는다. N01/F02/F03/FC01 독립 종결 역시 원 F01 해결이나 G2 적격성으로 승격하지 않는다.

ADB 공식 문서는 client의 server 자동 시작과 기기가 host RSA 키를 승인하는 절차를 설명한다. 이 host 승인을 물리 단말의 암호학적 인증서로 취급하지 않는다. [Android ADB 문서](https://developer.android.com/tools/adb). Android의 UID sandbox는 격리 수단이지만 무피해 보증이 아니다. [Android 앱 sandbox](https://source.android.com/docs/security/app-sandbox). INTERNET 제거는 최소 권한 제안이며 최종 APK의 IP 금지·relay peer/SELinux 동작은 실제 검증을 남긴다. [INTERNET 권한](https://developer.android.com/reference/android/Manifest.permission#INTERNET). relay는 기존 A01 K5의 미구현 제안이며 공개 LocalSocket API 페이지의 이번 fetch timeout을 근거로 지원을 인증하지 않았다.

**실행 수명과 취소의 정확한 의미.** 제안 전이는 `DENY → preflight 수용 → F 연결 grant → read-only 등록·독립 보충 → G 첫 mutation grant → install 1회 → 독립 checkpoint → launch 1회 → 고정 evidence → 종료`다. identity/transport/권한/감독/한도/증거 이상 또는 취소가 관측되면 `REVOKED`로 가고 되돌아오지 않는다. 불명 결과는 `UNKNOWN_QUARANTINED`, 실제 범위 위반은 `FAIL_VIOLATION`이다.

G2가 제안하는 cutoff는 **관측/전달된 취소 뒤 controller의 새 action admission 금지**다. 실제 무효화 사건과 관측 사이, 관측·latch와 기존 child 종료 사이에는 이미 admission한 action의 추가 write/자원 사용이 있을 수 있다. 이는 G1보다 약한 보증이다. controller admission·Popen·host queue를 G1 `SUBMISSION_COMMIT`으로 재명명하지 않는다. 이후 host stop/reap을 수행해도 이미 받은 PM/앱 작업의 종료·실패·durable commit·rollback을 알 수 없을 수 있다. USB 단절·host 종료·원격 task 종료·durable mutation 완료를 별도 사건으로 기록한다. libusb도 취소 요청/완료와 이미 전달된 부분 데이터를 구별한다. [libusb 취소 계약](https://libusb.sourceforge.io/api-1.0/group__libusb__asyncio.html#cancellation).

폐기 후에는 같은 serial/TID·늦은 ACK로 재개하지 않는다. 추가 readback/reconnect/stop/clear/uninstall 없이 받은 증거만 독립 분류한다. 실제 금지 동작은 UNKNOWN으로 면제하지 않는다. 정상 완료도 자동 package 삭제를 하지 않으며 잔류 APK/private files·PM bookkeeping은 사전에 owner가 알아야 할 효과다. 추후 정리는 별도 owner 결정이고 전 상태 복원을 보장하지 않는다.

**규범 충돌 8개.** 아래 항목은 모두 **완화 제안**이다. 새 후보가 더 실용적이라는 이유로 동일 보호라고 부르지 않는다. 정확한 원문 발췌·locator·대체 조항·권한 요구는 [충돌 JSON](benchmarks/real-device-gate-g2-p01/g1-f01-normative-conflicts.json)에 고정했다. 지금 이 예외는 하나도 유효하지 않다.

| ID | 정확한 지배 조항 | 제안하는 차이와 필요한 별도 결정 |
| --- | --- | --- |
| NC01 | f01-architectural-blocker.json #/requirement_ko; real-device-gate-g1-safety-contract.md G1-04 | 소유자 실물 통제와 serial/server/TID 관측을 통한 제한 캠페인 선택을 허용하되 actual resource/recipient의 원자 결합은 보장하지 않는다. 원 F01 적용의 exact 캠페인 예외를 별도 신설하고 G1-02/04 및 PR05·관련 PR03–07의 이 범위 효력을 명시 조정해야 한다. F01 해결·종결 표시는 금지한다. |
| NC02 | real-device-gate-g1-safety-contract.md S1; real-device-gate-g1-safety-contract.md G1-02 | 동결한 owner 자료·눈에 보이는 케이블/단말·고정 조회 일치를 등록 요건으로 삼으며 설치 전 암호학적 단말 증명이나 P→U/C의 기술적 강제를 충족했다고 하지 않는다. S1의 최초 등록 비면제 및 PR03 CP/IP·RJ02/03/11에 대한 한정 대체 등록 기준을 규범으로 명시한다. host RSA prompt는 이를 증명하지 않는다. |
| NC03 | real-device-gate-g1-safety-contract.md G1-02; real-device-gate-g1-safety-contract.md G1-05 | runner와 relay의 최소 OS/IPC/egress 제한은 의무로 두지만 다른 기기·다른 host process까지 포함한 전역 독점은 owner 운영 규율과 관측에 의존한다. S1/G1-02/05/PR04/06/RJ03/06/11의 전면 매개를 exact 캠페인에서 더 약한 경계로 바꾸는 명시 개정이 필요하다. 다른 target 허용을 뜻하지 않는다. |
| NC04 | real-device-gate-g1-safety-contract.md S3 | 관측/전달된 취소 후 controller의 새 action admission 0과 기존 child stop/reap만 강제한다. 그 전 실제 사건 이후 및 child 종료까지 이미 admission한 action의 write/자원 사용이 잔류할 수 있다. G1-06/09·S3·PR07 실제 사건 기준과 잔여 범위를 명시적으로 완화해야 한다. admission을 SUBMISSION_COMMIT으로 재정의해 회피하지 않는다. |
| NC05 | real-device-gate-g1-safety-contract.md S1; real-device-gate-g1-safety-contract.md G1-11 | 이 캠페인과 별도 승인된 validation enclave에만 새 SC01–12의 독립 적격성·등록 검토·별도 owner grants를 진입 조건으로 삼는다. G1 PR 수용은 0/12로 유지한다. S1 누적·비면제 관계, G1-03/11, S3/S4/RJ11 및 pinned admission gates의 적용 예외와 새 모든 필수 조건을 상위 권한으로 exact 명시해야 한다. 일반 위험 동의로는 불가하다. |
| NC06 | dispatch.py spawn_process; smoke.py require_host_confinement; physical-device-safety-contract.json #/emulator_target_policy/serial_grammar | 별도 검토된 operational profile/실행 경로와 물리 USB를 차단한 emulator validation 경계를 신규 정의한다. 현 FS1 synthetic profile을 실기기 권한으로 승격하지 않는다. B에서 exact 예외의 적용 대상을 정의하고 C의 별도 구현 승인을 받아야 한다. D의 emulator 예외·검증 GO도 별도다. DENY 제거/flag 우회는 현재 금지이며 G2 일반 활성화 기능으로 열 수 없다. |
| NC07 | t66b-hot-cold-design.md §29; t66c-delta-sync-protocol.md §34-B11; t66c-delta-sync-protocol.md §38.12 | formal F exit 이전에도 개인 데이터 격리 소형 smoke 한 번에 진입할 수 있는 별도 entry 예외를 제안한다. 기존 B11/T6.9-E 예외를 이 허가로 읽지 않는다. B §29/C §34·§38.12/G1 S1·S3의 적용 순서에 대한 exact entry-only 예외를 명시 심사·승인해야 한다. §26/§38.8–11 전체 F·Android 내구성·T6.9·R1·rollout/deployment 의무와 acceptance 순서는 유지한다. |
| NC08 | physical-device-safety-contract.json #/executor_requirements/resource_cap_enforcement_required; physical-device-safety-contract.json #/required_frozen_manifest_fields; physical-device-safety-contract.json #/required_frozen_manifest_fields | input/output/private synthetic 파일·요청 수와 host 자원에는 강제 cap을 두되 phone 전체 app-data/code cache·process RSS/PM·공유 자원·발열/전력에는 승인한 감시·중단 threshold와 잔류 선언만 둔다. synthetic output cap을 전체 app-data hard cap으로 부르지 않는다. PREP01 강제 resource cap과 maximum_process_memory_bytes/max_app_data_bytes의 적용을 synthetic hard cap과 phone 전체 감시 threshold로 명시 분리·개정해야 한다. G1-10의 hard/soft 구분은 유지한다. 전체 phone process/app-data hard cap을 유지하라는 결정이면 현 후보는 실행 불가다. |

계획 사전 동결·정확한 사전 identity·합성 데이터·개인/운영/공유 경로 금지·host action 1회·앱 replay 금지·UNKNOWN 비성공·연결/첫 mutation 승인 분리는 유지한다. INTERNET 제거는 더 좁은 capability 제안이다. [통제와 보호 비교](benchmarks/real-device-gate-g2-p01/safety-controls-and-residual-risks.json). 그 밖에 위 8개를 제외한 제한을 완화할 필요가 발견되면 현 후보 범위를 확대하지 않고 중단한다.

NC07은 특히 B11의 기존 8개 증거 이관 예외를 개인 기기 허가로 읽지 않기 위한 **pre-formal-F entry-only 별도 예외 제안**이다. 상위 B §29/C §34·§38.12의 순서와 G1 S1/S3를 명시적으로 정합 처리해야 한다. C §26 및 §38.8–11의 Android 내구성/legacy/restore·30개 artifact 의무, 전체 F와 최종 T6.9 acceptance, R1/rollout/deployment 조건은 줄이지 않는다. 이 smoke 결과를 그 proof로 수용하지 않는다. NC08은 PREP01의 강제 resource cap과 `maximum_process_memory_bytes`/`max_app_data_bytes`를 synthetic hard cap과 phone 전체 감시 threshold로 분리하려는 차이를 명시한다. output 1MiB가 Flutter/OS code cache를 포함한 전체 app-data 상한은 아니다. phone 전체 hard cap을 유지하는 결정이면 이 후보는 실행할 수 없다.

B의 별도 절차는 **권한 있는 owner의 exact 개정 지시 → 후보/redline 독립 검토 → 우선순위·범위·효력·만료·철회·모든 의존 hash를 포함한 exact 승인 → 지정 규범 적용 → 비참여 일치 검증 → 명시 효력 기록**이다. 원 finding/역사 감사는 덮어쓰지 않는다. 필요한 상위 규범 정합 redline을 피하고 하위 G2만 선언할 수 없다. 일반적인 위험 동의·이번 READY·owner 단일 기기 진술은 현재 필수 보호를 면제하지 못한다. 향후 예외가 생겨도 원 F01의 기술적 해결·proof 수용이나 다른 캠페인 허가를 뜻하지 않는다.

**유한 검증·승인 순서.** 현재 A의 문서 작성만 수행했다. 독립 리뷰는 수행하지 않았으며 B–G는 전부 **NOT AUTHORIZED**다. 각 단계의 entry·허용 범위·증거·pass/fail·stop·권한 전문은 [유한 계획](benchmarks/real-device-gate-g2-p01/finite-authorization-and-validation-plan.json)에 있다.

| 단계 | 진입과 최대 범위 | 필수 통과 조건·독립 역할 | 중단/금지 |
| --- | --- | --- | --- |
| A 제안·독립 리뷰 | 이 후보 1개·문서 리뷰 1회 | 작성 비참여자가 9위험·8충돌·모든 SC/권한 분리를 확인 | 누락·권한 확대면 종료. 규범 적용/구현/기기 금지 |
| B 규범 결정·개정 | 별도 지시 후 redline 1개·리뷰 1회·적용 1회·적용 대조 1회 | owner exact 승인과 독립 개정·적용 검증 및 효력 기록 | 상위 정합/권한/hash 결측이면 종료. 실행 GO 없음 |
| C host-only 구현·감사 | 별도 구현 GO·후보 1개·고정 HC01–12 한 campaign·감사 1회 | 실제 source/binary·OS/IPC/egress·grant/digest·1회 admission·회수 감사 | 개발 중 DENY 유지. ADB/USB/emulator 실행 0 |
| D emulator/lifecycle | 별도 exact GO와 물리 USB 비노출 enclave 수용·EV01–12 각 1회·리뷰 1회 | 최종 APK/ABI의 claim/replay/부분 실패·IP 금지/relay·취소·자원 시험 | 실패면 종료·대체 경로 없음. phone 신원/물리 USB proof로 수용 금지 |
| E 독립 preflight | 모든 새 필수 SC 충족·완성된 사전 manifest 1개·리뷰 1회 | 구현/실행 비참여자가 출처·exact 값·외부 digest·hard/soft·잔여 범위를 대조 | 빈 serial/build/예산·trust 준비 불명·미검증 SC면 F 불가. 장치 접촉 금지 |
| F owner 연결 승인 | 별도 exact 연결/read-only grant·연결/등록 1회·등록 보충 리뷰 1회 | visible 대조·단일 관측 target·사전 값/실제 instance 대조 | 새 trust prompt·다중 target·세대/시간 오류면 폐기. 설치/marker/launch 0 |
| G 첫 mutation 승인 | 별도 exact grant·install<=1·독립 checkpoint<=1·launch<=1·사후 리뷰 1회 | 승인된 literal 순서·bytes·종료 증거. 불명은 UNKNOWN, 위반은 FAIL | 추가 readback/reconnect·자동 stop/clear/uninstall·retry 금지 |

후보 ceiling은 연결~종료 600초, 첫 mutation grant 최대 120초, APK 256MiB, 합성 요청 최대 12개·응답별 256KiB·request body 64KiB, private synthetic output 1MiB·result 16KiB, host evidence 10MiB, 동시 host action 1개다. 승인 값은 아니며 E에서 실제 계획을 이 이하로 완성한다. 전체 시간은 controller admission 시한이고 원격 hard termination 시한이 아니다. 단계별 timeout·여유 공간·host hard cap·phone RSS/열 threshold와 집행/감시 구분도 공란을 허용하지 않는다. owner/리뷰 대기여도 자동 연장하지 않는다. [기계 판독 계약 후보](benchmarks/real-device-gate-g2-p01/restricted-campaign-contract-candidate.json).

C의 HC12개는 schema/digest·APK·순서/동시성·grant·target/세대·폐기·server lifecycle·FD/IPC·relay/egress·한도·late ACK를 고정 검증한다. D의 EV12개는 정상·중복 intent·재생성·claim 전후/중간 효과 중단·네트워크·peer·transport/server 변경·host 취소/ACK 유실·최대 입력을 각 1회 검증한다. 현재 어떤 시험도 실행하지 않았다. 실패는 단계 종료이며 같은 작업의 자동 수정/재감사 루프를 만들지 않는다. 새로운 수정이 필요하면 별도 결정이 필요하다. 필수 통제가 성립하지 않으면 물리 캠페인은 **BLOCKED**로 끝나며, 이 계획은 실기기 시험이 결국 가능해진다고 약속하지 않는다.

**이번 산출물과 보존.** 실행 소스·계약·역사 보고서·B03·Git index를 변경하지 않고 이 보고서와 새 dossier만 추가했다. ADB/help/version·USB/기기 명령·emulator·기기 접촉·APK 설치·production 기록 접근·G1 proof 수용은 모두 0이다. 정적 제안 작업이므로 npm/backend build/test를 재실행하지 않았고, FS1 등의 과거 PASS를 새 G2 proof로 집계하지 않았다. DB/build/cache 생성·삭제도 없다. 종료 대조에서 기존 8,239개 경로·외부 frozen sidecar 5개·source lock 27개와 HEAD/index/staged가 보존됐다. 상세 결과는 [보존 검증](benchmarks/real-device-gate-g2-p01/validation-and-preservation.json), 산출물 신원은 [증거 manifest](benchmarks/real-device-gate-g2-p01/evidence-manifest.json)에 기록한다. N01/F02/F03/FC01 독립 종결·T6.9 DEFERRED·R1 CLOSED·production 미승인을 유지한다.

가장 작은 다음 결정은 **소유자가 이 후보와 8개 완화 항목에 대한 비참여 독립 검토 1회만 별도로 의뢰하는 것**이다. 개정안 작성·적용·구현·emulator·물리 연결·첫 mutation은 이후 각 단계의 별도 결정이다. [소유자 선택지](benchmarks/real-device-gate-g2-p01/owner-decision-options.json).
