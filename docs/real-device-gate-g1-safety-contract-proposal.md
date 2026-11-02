# Real-Device Gate — G1 별도 안전 계약 제안서

**문서 ID: G1-PROPOSAL-01 / 계약 초안 ID: F01-G1-DRAFT-01.**

**제안 작성 완료 — G1 미승인·미적용, 원 F01 계속 유효, 운영 dispatch 및 기기 접근 차단 유지.** 소유자의 이번 결정은 별도 G1의 문서 작성과 독립 검토 준비만 승인한다. 계약 채택·위험 수용·구현·검증 캠페인·ADB·emulator·개인 기기 연결/설치/시험을 승인하지 않는다. [이번 승인 범위 기록](benchmarks/real-device-gate-g1-proposal/owner-proposal-authorization.json).

G1의 심의 대상은 **transport ID 선택 + 강제 격리 ADB/device 환경 + 명시적 등록·연결 세대 + 고정 action·1회 세션·실패 즉시 중단**이다. 조건부 no-other-target 보증을 제안하지만 현재 그 보증이 성립했다고 판정하지 않는다. 특히 **최초 단말 등록(PR03), USB incarnation 강제(PR04), 실제 server/channel 결합(PR05), 전면 매개(PR06), 효과 전달 전 권한 폐기(PR07)는 미해결 필수 증명**이다. 이 결측을 잔여 위험 수용으로 면제할 수 없다.

## 1. 현재 결정과 문서의 효력

원 F01 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

G1 초안은 이를 이미 충족했다는 해석이 아니다. 원 identity/mutation 결합 proof를 **명시한 신뢰 가정, 독립 초기 등록, 실제 자원 수명 결합과 OS 도달 제한에 의한 조건부 엄격 승인 계약**으로 대체할지를 소유자가 별도로 심의할 수 있도록 준비한 문서다. 원 요구는 exact amendment 승인·적용이 완료될 때까지 계속 binding이다. 문구 변경이나 위험 서명을 F01의 기술적 해결·종결로 표현하지 않는다. [원 F01 결정](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json), [PREP10 판정](real-device-gate-prep10-f01-architecture-decision.md).

이번 작업에서는 규범 원본·B03/B11 binding·금융 authority·기존 실행기/guard/app을 수정하지 않는다. 현재 `scripts/devicegate/dispatch.py`의 무조건 거부와 `require_host_confinement()`의 거부를 보존한다. 시험 어댑터, 새 boolean/token/환경 설정 또는 문서 승인을 운영 활성화 경로로 만들지 않는다. [현재 중앙 경계](../scripts/devicegate/dispatch.py), 근거 R09·R10·R12.

후속 규범 채택을 승인하더라도 그것은 **어떤 보증을 요구할지** 정하는 결정이다. 해당 보증의 구현·독립 proof 수용과 실제 기기 접근·첫 mutation 승인은 별개다. 채택 문구의 정확 hash, 적용할 규범 위치와 redline, 원 F01의 대체 범위·효력 시점이 명시되지 않으면 계약은 바뀌지 않는다. 현재 normative destination도 정하지 않았으며 새 규범 파일을 만들지 않았다.

## 2. 근거와 보증 등급

프로젝트 이력은 PREP01–PREP10 보고서·JSON·현재 source로 재구성했다. 공개 인터페이스 의미는 PREP10에 보존된 공식 문서와 AOSP revision `1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc`의 고정 사본을 사용한다. 이번에는 ADB help/version도 실행하지 않았고 최신 binary 기능이나 실제 host/device 상태를 새로 조사하지 않았다.

[근거 목록](benchmarks/real-device-gate-g1-proposal/evidence-catalog.json)은 PREP10의 R/AOSP 근거를 원 경로·SHA로 참조하고, 이번 소유자 지시와 제안 배경을 G01–G07로 추가한다. 현재 사용자 지시는 텍스트 전사로 보존했으며 원 메시지 전송 bytes의 해시나 별도 실명 서명을 입증했다고 주장하지 않는다.

| 등급 | 인정할 수 있는 사실 | 확장해서는 안 되는 결론 |
| --- | --- | --- |
| 저장소에서 확인 | 중앙 무조건 거부, PREP09의 FC01/N01/F02/F03 종결 기록, 원 F01 모의 반례 | 이 기록만으로 G1 구현·실기기 자격 검증 완료 |
| 공개 인터페이스 | `-t`의 transport ID 선택, `--one-device`의 USB filter, Android 앱 sandbox 원칙 | 불변 물리 기기 인증, 전체 OS 격리, 원자 조건부 mutation |
| 고정 소스의 조건부 성질 | server 내부 ID counter, 새 USB 객체, 일부 TCP 같은 객체 reconnect, ID의 serial보다 높은 선택 우선순위, client 자동 server lifecycle | 설치 binary와 동일한 수명 의미, `-s/-t`의 AND 검증, ID 동일이면 무단절이라는 주장 |
| 제안·미입증 | 실제 USB/server/channel incarnation 고정, 우회 불가 OS 경계, 등록 후 no-other-target, 앱 1회 시험 gate | 문서에 요구를 썼다는 이유로 이미 제공되는 capability라고 주장 |
| best effort | 반복 probe·inventory 감시·이상 후 kill | 마지막 검사와 실제 전달 사이의 원자성 |
| 보증하지 않음 | 침해된 신뢰 기반·악성 USB relay 방어, 데이터 손실 0, 이미 제출된 작업의 즉시 rollback, remote exactly-once | 소유자 서명으로 미입증 기술 보증을 사실로 변경 |

transport ID는 신뢰 server process 안의 객체 선택이다. server가 교체되면 숫자가 재사용될 수 있고, 일부 TCP reconnect는 같은 객체를 유지한다. `-s/-t` 조합을 두 신원 조건의 AND로 취급하지 않는다. `--one-device`나 private port만으로 USB/TCP/외부 client를 격리했다고 보지 않는다. 근거 `AOSP-transport.cpp:279–282,830–849,903–947`, `AOSP-client/adb_client.cpp:81–105,250–352`, [PREP10 인터페이스 검토](benchmarks/real-device-gate-prep10/adb-interface-capability-review.json).

## 3. G1에서 제안하는 보증과 정확한 차이

`P*`는 소유자가 승인한 물리 단말, `U*`는 그 단말의 특정 USB 연결 incarnation, `S*`는 신뢰 ADB server 자원 세대, `C*`는 실제 service 전달 채널, `T*`는 그 server 안의 transport ID, `R*`는 receiver의 boot/adbd 세대다. `H*`는 host boot/격리 principal·환경이다.

제안하는 승인 문맥은 `a=(owner-decision, session, P*, U*, H*, S*, C*, T*, R*, manifest-hash, artifact-hash, next-action, expiry)`다. 이 표기는 **요구를 나타내는 수학적 모델**이며 ADB가 이런 token이나 immutable device handle을 제공한다는 주장이 아니다. 문자열·UUID·PID/start time을 저장하는 것과 실제 자원에 대한 권한을 강제하는 것은 구별한다.

G1의 조건부 안전 속성은 다음 네 가지를 함께 요구한다.

1. 실제 등록 증거로 `P* ↔ U* ↔ C*`를 결합하고, 승인된 신뢰 가정 아래 모든 action의 실제 도달 집합을 `{P*}` 안으로 강제한다.
2. 효과를 동결 manifest의 test action·test-private synthetic 데이터와 명시한 필수 OS bookkeeping에 한정한다. 개인 데이터와 production에는 접근하지 않는다.
3. 연결·server/channel·receiver 세대 변화, 취소·감독 상실·예산 초과에서는 권한을 단방향 폐기하고 새 action 제출을 금지한다. 동일 이름/번호의 재등장으로 복구하지 않는다.
4. 호스트의 논리 action별 dispatch 시도는 최대 1회다. 앱 process 재생성·중복 intent도 논리 시험의 자동 replay를 일으키지 않아야 한다. 응답 유실은 UNKNOWN이고 재시도하지 않는다.

이는 물리적으로 동시인 identity+mutation 연산을 제공한다는 주장이 아니다. 원 F01의 마지막 probe 뒤 신원 변화 반례와 강한 결합 요구를 소급 폐기하지 않는다. 신뢰 Android/boot 문맥에서 material 신원이 안정적이라는 가정을 수용할지도 별도 owner 결정이다. 그 가정으로도 **실수로 다른 정상 단말이 유일하게 연결되는 경우, 재열거·server 교체·실제 채널 변경은 제외할 수 없다.** 해당 경우는 G1 내부에서 필수로 막아야 한다.

## 4. 별도 채택 시 적용할 조항 초안

아래 조항과 [계약 JSON](benchmarks/real-device-gate-g1-proposal/g1-contract-proposal.json)은 모두 **미승인 초안**이다. 승인 대상의 정확 문구는 JSON의 `normative_clauses_if_separately_adopted`이며 이 표는 심의를 위한 요약이다.

| 조항 | 제안하는 의무 |
| --- | --- |
| G1-01 효력 | 단일 owner·특정 개인 단말·한 고정 세션으로 한정한다. 별도 채택/적용 전에는 원 F01 유지 |
| G1-02 안전 속성 | 신뢰 가정과 초기 결합 proof 아래 actual reachability를 `P*`에 제한하고 승인 범위 밖 effect 경로를 허용하지 않음 |
| G1-03 초기 등록 | 연결 전 exact identity/manifest 승인, 변경 없는 고정 read-only 등록, 첫 mutation 전 transcript 대조·owner 확인 |
| G1-04 자원 결합 | actual USB/server/client channel/transport/receiver 세대를 승인 문맥에 강제 결합. 이름/ID/polling은 대체 불가 |
| G1-05 전면 매개 | wrapper·후손·다른 client/socket·FD 전달·TCP/mDNS·재열거 우회와 auto server start/restart/reexec/fallback을 차단 |
| G1-06 폐기 | 단절·재등록·receiver 변화·취소·예산 초과·감독 상실 후 같은 세션 복귀·재접속·재선택 없음 |
| G1-07 1회 action | literal argv/입력 bytes/artifact/순서/예산을 사전 고정. action 최대 1회 제출 시도, 앱 restart replay 금지 |
| G1-08 개인 데이터 | 별도 package/signer/storage와 synthetic backend. 필수 OS 부수효과는 명시하되 개인 앱/production/특별 권한/기기 전체 정책 변경 금지 |
| G1-09 진행 중 작업 | 폐기 이후 새 제출 금지. 이미 제출된 bytes/원격 작업의 완료 가능성은 인정하고 불명확하면 UNKNOWN. rollback/자동 cleanup 없음 |
| G1-10 증거·예산 | bounded stage/action journal, 고정 시간/bytes/여유/memory 한도, 부분 증거 보존. 증거 실패도 성공 처리하지 않음 |
| G1-11 독립 proof | 비참여 검토자가 실제 effect sink·강제 경계를 수용. 문서/모형/위험 서명은 등록·OS proof를 대체하지 못함 |
| G1-12 별도 권한 | 규범·구현·mock/OS 검증·기기 연결·첫 mutation을 각각 명시 범위로 승인. 이번 승인에서 자동 파생되는 권한 없음 |

## 5. 신뢰 가정과 위협 모델

[가정 register](benchmarks/real-device-gate-g1-proposal/guarantee-and-assumption-register.json)의 AS01–AS06은 모두 **PENDING — NOT ACCEPTED**다.

| ID | 소유자가 심의할 가정 | 여전히 증명해야 하는 것 |
| --- | --- | --- |
| AS01 | host admin/kernel/hypervisor와 정확 OS 정책을 신뢰 | 일반 process·후손·다른 client에 대한 실제 접근 제한·우회 거부 |
| AS02 | 고정 ADB/adbd/toolchain을 신뢰 | 실제 사용 binary에 적용되는 selector/lifecycle 의미와 source·artifact provenance |
| AS03 | Android/kernel/package manager 비침해, 승인 boot 세대의 material 신원 안정성 | boot/adbd 교체에서 권한 폐기, test package/signer/storage 격리 |
| AS04 | 악성 USB proxy/relay·신원 위장·공격적 물리 교체를 threat model 밖으로 둘지 | 실수로 잘못 연결한 정상 phone, 같은 이름/주소의 새 객체, 짧은 단절은 내부 위협으로 방어 |
| AS05 | owner-local 독립 식별 기록의 신뢰 근거 | 그 기록의 `P*`와 actual `U*/C*`의 결합. 소유/케이블/단독 목록만으로 대체 불가 |
| AS06 | OS bookkeeping·공유 자원 소비·이미 받은 작업의 후속 완료 가능성 인정 | 실제 세션의 effect·예산·UNKNOWN 처분과 개인 데이터 비접근 |

AS05는 ‘owner가 맞다고 했으니 초기 binding proof가 필요 없다’는 포괄 예외가 아니다. registered 값이 바뀌지 않았다는 검사와 resource가 바뀌지 않았다는 강제는 별개다. 가정을 위반한 공격까지 방어해야 한다면 그 보증을 주지 못하는 B+C를 기각해야 하며 문구를 모호하게 바꿔 충족한 것으로 표시하지 않는다.

## 6. 초기 등록과 첫 설치의 경계

**최초 APK 설치도 mutation이다.** 테스트 앱 설치 뒤 생성한 key/nonce나 결과 파일로 처음부터 올바른 단말이었다고 소급 증명할 수 없다. 등록용 marker 설치·쓰기 역시 초기 안전성 검사를 통과하기 전에는 허용하지 않는다. 현재 앱에 cryptographic registration이나 G1 one-shot 승인 기능이 있다고 가정하지 않는다. 근거 R07·R17·R18·G06.

후보 등록 절차는 다음 경계를 요구하지만 **지원되는 구체 구현은 아직 선정·자격검증되지 않았다.**

- 연결 전 owner-local 또는 기존 신뢰 자료에서 exact serial/OS/build의 근거를 확보하고, 그 값과 wire 필드 사이의 대응 근거를 검토한다. 화면의 식별자와 ADB serial이 당연히 같다고 가정하지 않는다.
- owner가 미리 승인한 연결 세션 안에서만, 이미 준비된 OS 제한이 actual USB incarnation을 특정하도록 하고 고정 read-only allowlist로 등록 transcript를 얻는다. 다른 phone을 조사하기 위한 추가 probe를 생성하지 않는다.
- transcript는 단순 이름과 목록 대신 실제 server/client 채널·USB 자원·receiver 세대에 연결돼야 한다. 두 정상 phone 중 잘못된 phone만 유일하게 존재하는 경우와 최종 probe 이후 교체를 독립 음성 대조로 거부해야 한다.
- 첫 mutation 전에 owner가 사전 고정 plan과 등록 transcript hash를 대조해 진행을 명시 확인한다. 이 gate 사이에 code/APK/argv/fixture/예산을 바꾸지 않는다.

연결 승인과 첫 mutation 확인은 **한 고정 세션의 사전 설계된 두 인간 gate**다. 이것이 현재 연결을 허용하는 것은 아니다. PREP01의 연결 전 exact identity 필수값 요구도 바꾸지 않는다. 사전 identity를 확보할 수 없으면 ‘연결해서 알아내기’가 자동 허용되지 않으며 별도 계약/수집 절차 결정을 반환한다. 등록에 기존 미승인 device-wide 설정 변경, unknown-source 설치 허용, pairing·debugging 활성화나 특별 권한이 필요하면 이 계획에서는 중단한다. [기존 연결 전 계약](real-device-gate-prep01-headless-emulator-foundation.md).

등록 메커니즘이 두 endpoint를 실제로 구별하지 못하거나 연결 수명을 증명하지 못하면 **PR03 FAIL → 기기 접근 불가**다. PR03을 미해결 위험으로 소유자에게 떠넘겨 G1 실행을 허용하는 대안은 제공하지 않는다.

## 7. 실제 실행 경계의 요구

다음은 제안 call-flow이며 실행 가능한 명령이나 존재하는 executor를 뜻하지 않는다.

```text
기기 없는 문서/구현/격리 proof와 artifact 동결 [향후 별도 승인]
  → owner의 exact 연결·세션 승인
  → 준비된 OS 경계 아래 지정 USB incarnation만 노출
  → 고정 read-only 등록: P* / U* / S* / C* / T* / R* 대조
  → owner의 등록 transcript·첫 mutation 진행 확인
  → 검증된 최소 경계가 동결 action 1개를 동일 자원 채널에 제출
  → test package와 명시 OS bookkeeping / synthetic backend만
  → 승인된 bounded 결과 수집 1회 → 종료·분리 → host 분석

세대 변화·취소·감독 상실·예산/증거 실패
  → REVOKED 또는 OUTCOME_UNKNOWN
  → 새 제출 / 재접속 / 재선택 / replay / 자동 cleanup 없음
  → 이미 받은 host 증거 보존
```

OS 경계는 전용 principal 또는 검토한 VM/동등 강제 경계에서 USB node/handle, 실제 client/server socket, 다른 endpoint/TCP/mDNS, 도구 후손과 FD 전달을 통제해야 한다. private port, network namespace, 단일 node mount, major/minor 허용목록만으로 모든 조건이 충족됐다고 보지 않는다. 재열거 때 node/주소가 재사용되는 경우까지 증명해야 한다. 실제 host에 적용 가능한 recipe와 필요한 권한은 아직 미검증이다. `LINUX-DEVICE-CGROUP`·`LINUX-USB-AUTH-CORRECTED`, R10.

server PID/start time·binary hash 검사 뒤 새 CLI를 띄우는 방식도 actual server/channel 결합을 단독 보장하지 않는다. 고정 AOSP client의 자동 기동·restart/reexec 경로와 다른 client가 server를 교체하는 경로를 함께 통제해야 한다. 지원 ADB만으로 이를 강제할 수 있다는 증거가 없으면 PR05를 FAIL로 두고 다른 구체 설계나 기각 결정을 반환한다. 별도 raw socket escape hatch를 기존 harness에 만들지 않는다.

### 고정 action과 효과 목록

아래는 향후 manifest가 채울 **의미 범주**이며 승인된 argv가 아니다. 실제 serial/bytes/경로/시간/명령 수는 미정이다. 공란이면 실행 manifest로 사용할 수 없다.

| 범주 | 허용하려는 좁은 의미 | 제한 |
| --- | --- | --- |
| 등록 조회 | exact 허용 신원 필드·선택 자원의 수명 대조 | 전체 앱/개인 자료 탐색·추가 adaptive probe 금지 |
| 테스트 설치 | 검토한 fresh test package에 봉인된 APK bytes 전달 | 기존 package가 있으면 중단. production ID 갱신·자동 삭제·`-r` 대체 정책 없음 |
| 테스트 시작 | exact test component와 고정 session/input | 중복 시작·process restart에 의한 자동 시험 replay를 app 경계에서 거부 |
| 결과 수집 | 승인한 test-private 상대 파일·자기 로그만 고정 횟수/bytes 수집 | 전체 logcat/dumpsys/bugreport, 임의 경로·개인 storage 금지 |
| 정리 | 최소 후보에 자동 uninstall/clear 없음 | 실패 뒤 device cleanup을 안전성 복구 명분으로 수행하지 않음 |

설치는 package-manager 기록, 시작은 OS lifecycle·자원 기록을 변경할 수 있다. 따라서 모든 bytes가 test UID의 private directory 안에서만 바뀐다는 보증은 제안하지 않는다. manifest에는 **test package 관련 필수 OS bookkeeping**과 공유 CPU/memory/저장 소비를 별도 effect 범주로 밝혀야 한다. 이를 광역 settings/appops 변경이나 다른 앱 접근의 예외로 사용할 수 없다.

현재 `main_devicegate.dart`는 `main()`에서 `_smoke()`를 호출한다. run ID 검사만으로 durable 1회 실행을 증명하지 않는다. 미래 G1에서 앱 process 재생성이 논리 시험을 재시작할 수 있는지 검토하고, 금지를 보장할 gate가 필요하면 **별도 승인된 app 구현과 proof**를 요구한다. 이번에는 앱을 바꾸지 않았다. 보존 APK의 Flutter engine=x86_64, emulator 전용 endpoint도 phone 준비 proof가 아니다. G06·R26·R17.

## 8. 실패·재시도·증거의 정확한 의미

성공 상태는 모든 고정 action과 필수 증거가 완료됐을 때만 `COMPLETED`다. 나머지는 `REVOKED` 또는 `OUTCOME_UNKNOWN`이며 같은 세션에서 실행 가능 상태로 돌아오지 않는다.

논리 action의 상태는 `PREPARED → RESERVED → SUBMISSION_STARTED → ACKED/UNKNOWN`으로 구분한다. `RESERVED`는 재시도 방지를 위해 시도를 소비한 기록이며 그 자체가 전송 시작은 아니다. 예약 뒤 취소되면 새 제출하지 않고 소비된 상태를 보존한다. 어디까지 전달됐는지 입증할 수 없으면 UNKNOWN이다.

`SUBMISSION_STARTED`는 이미 검증된 고정 receiver/channel에 승인 action의 실제 제출을 시작한 경우다. 폐기 전에 이미 제출된/버퍼링된 bytes와 remote 작업은 폐기 뒤 끝날 수 있다. 새 receiver에 버퍼를 옮기거나 새 channel을 열어 나머지를 보내는 것은 금지한다. ‘새 action 제출 없음’과 ‘이미 받은 remote 작업이 물리 사건 순간 멈춤’을 혼동하지 않는다. 사건 감시·host kill·N01의 host 자식 회수만으로 후자를 보장하지 않는다.

호스트 action별 시도 최대 1회와 앱의 논리 시험 replay 금지는 remote exactly-once 완료 보장이 아니다. 설치의 partial outcome, 응답 유실, remote 작업 지속, test package 잔존은 실제 가능한 처분 범주로 공개해야 한다. UNKNOWN에서 새 readback/clear/uninstall로 자동 진단·복구하지 않는다. 증거가 부족하면 부족한 채 종료하고 추가 수집은 새 결정으로 돌린다.

manifest에는 전체/단계 시간, 응답·app data·로그·host evidence bytes, 최소 여유, memory 상한, app/remote 작업에 대해 실제 강제할 수 있는 한계와 단순 감시 한계를 분리한다. deadline 초과를 관측하면 후속 작업을 막지만 OS scheduling 정지나 이미 받은 remote action의 hard realtime 종료를 보증하지 않는다. 이번 제안에 실제 phone 예산 값을 임의로 넣지 않았다. R07·R21·`AOSP-SERVICES.TXT`.

## 9. 필수 proof와 거부 기준

[필수 proof matrix](benchmarks/real-device-gate-g1-proposal/required-proof-matrix.json)는 모두 현 G1 실행 수용 **미완료**다. PR01은 이번 문서상의 권한 구분만 확인했고, PR02에는 과거 artifact 관측만 있다. 그 밖의 실제 enforcement proof는 OPEN이며 PR12 독립 심사도 수행되지 않았다.

| ID | 기기 접근 전에 수용해야 할 proof |
| --- | --- |
| PR01 | exact owner 승인·규범 우선순위·G1 채택/적용과 실행 권한의 분리 |
| PR02 | 실제 binary의 selector/lifecycle 근거, source/artifact/tool/서명/fixture/봉인 bytes 신원 |
| PR03 | owner-local `P*`와 실제 `U*/C*`의 최초 결합; wrong singleton와 probe 뒤 교체 거부 |
| PR04 | USB incarnation 수명, 새 node/주소/major-minor 재사용과 reset/재열거 차단 |
| PR05 | server 자원 세대와 actual service channel 결합, ID 재사용/자동 server lifecycle 차단 |
| PR06 | wrapper·후손·FD·다른 socket/TCP 등 모든 도달 경로에 대한 OS 전면 매개 |
| PR07 | 취소/감독 상실/세대 변화의 실제 제출 전 폐기와 host action 1회 시도·UNKNOWN 거부 |
| PR08 | 최종 APK/package/signer/storage/backup/권한과 app 재생성·중복 intent의 시험 replay 거부 |
| PR09 | phone-compatible exact synthetic backend route/소유·redirect/egress/production fallback 거부 |
| PR10 | 유한 자원·증거·부분 실패/UNKNOWN과 이미 받은 remote 작업의 한계 |
| PR11 | 실제 literal argv/bytes/component/path/순서와 부수효과가 완결된 승인 manifest |
| PR12 | 같은 artifacts/OS/환경에 대한 비참여 독립 통합 수용, N01/F02/F03/FC01 종결 범위 보존 |

‘접근 전 proof’는 **기기 없는 단계의 메커니즘 자격검증**과 **나중에 승인된 연결 안에서 확인할 instance 값**을 구분한다. 아직 존재하지 않는 `U*` 값을 연결 전에 관측했다고 주장하지 않는다. 연결 전에는 메커니즘·입력 manifest·최소 범위·owner 승인까지 수용하고, 실제 등록 transcript와 첫 mutation gate는 승인된 연결 안에서 따로 수용해야 한다. 그 연결 자체도 현재 허용되지 않는다. [접근 조건 JSON](benchmarks/real-device-gate-g1-proposal/device-admission-conditions.json).

[거부 기준](benchmarks/real-device-gate-g1-proposal/approval-and-rejection-options.json)의 RJ01–RJ14 중 하나라도 해당하면 실행 GO는 불가하다. 특히 다음은 잔여 위험 수용으로 면제하지 않는다.

- 초기 등록을 단독 USB/serial/케이블 소유로 대체하거나 설치 이후 key로 소급 증명한다.
- 같은 숫자의 새 server/USB/transport에 권한을 넘기거나 polling/UUID/이상 후 kill을 실제 resource enforcement로 취급한다.
- 자동 start/reconnect/retry/fallback, wrapper·후손의 직접 접근, 앱 restart replay가 남는다.
- 개인/production 데이터·특별 권한·기기 전체 정책 변경이 필요하거나 fixed command/예산이 채워지지 않는다.
- UNKNOWN을 성공/재실행/자동 cleanup으로 처리하거나 문서·모형·저자 자체검증을 독립 OS proof로 집계한다.

## 10. 유한 검증 계획 — 실행하지 않음

[검증 계획](benchmarks/real-device-gate-g1-proposal/bounded-validation-plan.json)은 **제안**이다. 이번 승인으로 V1/V2/V3를 구현·실행하지 않았다. AGENTS 필수 웹/backend 검증을 G1 캠페인 결과로 집계하지 않는다.

| 단계 | 고정 범위·상한 | 끝나는 조건과 한계 |
| --- | --- | --- |
| D0 문서 검토 | 비참여 검토자 1명, exact dossier 1회, 제안 상한 2시간 | ACCEPT_FOR_OWNER_CONTRACT_DECISION / REQUEST_SPECIFIC_REVISION / REJECT 중 1개. 이번에는 입력 준비만 완료; 검토 수행·독립 PASS 없음 |
| V1 모형 | 별도 승인 시 in-memory 모형 1개, 고정 trace 12개, 최대 1시간·10MiB, ADB/emulator/USB/network/OS 변경 없음 | 결과·반례·가정 목록 1회 반환. 실패/시간 초과/불확실은 중단. 실제 USB proof 아님 |
| V2 강제 경계 | 별도 구현/host/lab 승인 시 정확 OS recipe 1개, 음성 8개, 최대 90분·20MiB, 개인 phone/Android/emulator 사용 없음 | 실제 resource/effect sink를 독립 관측. 비개인 대체 endpoint/USB 장비 선정도 사전 승인 대상. 개인 phone의 등록/적합성 수용 아님 |
| V3 실제 고정 세션 | 모든 선행 조건과 exact owner 승인 후에만 고려. 세션 1개, 자동 retry 0 | 실제 target/명령/예산이 공란이면 연결 불가. T6.9·전원 차단·R1·production 범위 없음 |

V1의 고정 trace는 T01 정상 1회·중복, T02 잘못된 유일 정상 단말, T03 마지막 probe 뒤 receiver 교체, T04 USB 이름/번호 재사용, T05 server 숫자 재사용, T06 같은 ID TCP reconnect, T07 receiver boot/adbd 변화, T08 wrapper/후손 우회, T09 artifact 치환, T10 전달 뒤 응답 유실·취소, T11 예산/증거 실패, T12 앱 재생성·intent replay다. 이 12개를 모든 가능한 interleaving의 형식 증명이라고 부르지 않는다.

모형은 승인/선택 값과 **actual dispatch/effect receiver를 독립 상태**로 가져야 한다. actual receiver 교체가 실제 effect sink까지 전파되고 두 receiver의 효과를 독립 관측해야 한다. `binding=true`를 성공의 전제로 두거나 mock이 위험 sink를 지우면 시험은 무효다. V2는 이 추상 결과를 실제 OS/device 자원에 대응시키는 별도 proof이며 source 전체·byte·policy·도달 경로를 고정해야 한다.

각 단계는 한 번의 결과와 소유자 결정을 반환하는 종료점을 가진다. 실패를 자동 수정·재감사·추가 trace·다른 OS recipe로 이어가지 않는다. 다음 조사를 원하면 특정 반례 ID와 새 범위를 가진 별도 결정이 필요하다. 이번 문서가 후속 캠페인을 예약한 것은 아니다.

## 11. 개인 단말 잔여 위험과 수용 조건

[위험 register](benchmarks/real-device-gate-g1-proposal/residual-risk-and-acceptance-register.json)의 모든 `owner_accepted`는 false다. 이번 제안 작성으로 기기 데이터 노출은 없다.

| ID | 남는 위험 또는 proof 결측 | 수용 가능 범위 |
| --- | --- | --- |
| GR01 | 침해 host/Android/ADB·악성 USB relay | 신뢰/제외 위협의 범위만 명시 수용 가능. 해당 위협까지 보증한다고 주장 불가 |
| GR02 | 이미 받은 작업의 완료·partial install·test package 잔존 | UNKNOWN, 자동 replay/cleanup 금지, 필요한 owner 수동 처분의 비용을 사전 고지하고 수용 |
| GR03 | 열·배터리·저장/memory·필수 OS 기록·OS 오류 | 실제 기기의 수치 예산·여유·허용 effect를 확인한 별도 세션에서 수용. 개인 데이터 손실 0 보증 없음 |
| GR04 | 제한 증거·응답 유실로 결과가 영구 불명확 | FAIL/UNKNOWN 유지와 추가 자동 수집 금지, 미완료 세션으로 종료할 가능성 수용 |
| GR05 | 잘못된 정상 phone의 최초 등록 | 수용으로 면제 불가. PR03 미충족이면 접근 거부 |
| GR06 | 재열거·server/channel 교체·우회 dispatch | 수용으로 면제 불가. PR04–PR07 미충족이면 접근 거부 |
| GR07 | 앱 replay·개인/production 접근·부적합 endpoint/ABI | 수용으로 면제 불가. PR08/PR09/PR11 미충족이면 접근 거부 |

개인 앱/사진/알림/계정/금융 데이터, 생산 DB/Snapshot/credential에는 접근하지 않는다. test package·독립 signer·private storage·합성 backend/fixture를 함께 격리한다. root·factory reset·bootloader·기기 전체 정책 변경·광역 삭제·알림/accessibility/device-owner 등 넓은 권한은 허용하지 않는다. 성공/실패 뒤 자동 uninstall/clear도 최소 후보에서는 제외한다. 필요한 새 조치는 별도 승인이고 원 binding 요구가 다시 적용된다.

## 12. 명시적 승인 대안과 심사 패키지

소유자는 이번에 **제안 작성 방향만 승인**했다. 아래 O1–O4 중 계약 채택/캠페인/실행 결정을 내렸다고 기록하지 않는다. [결정 대안과 정확 문안](benchmarks/real-device-gate-g1-proposal/approval-and-rejection-options.json).

| 대안 | 승인 또는 거부할 정확 대상 | 따라오지 않는 권한 |
| --- | --- | --- |
| O1 G1 기각 | 원 F01과 차단을 유지하며 새 작업 없음 | 새 조사·구현·접근 |
| O2 특정 문서 수정 | clause/proof ID와 결함·수정 범위만 명시 | 자동 구현·반복 감사·실험 |
| O3 V1만 한정 승인 | 원 F01 유지 상태에서 exact plan/hash의 모형 1개/12 trace/1시간/10MiB만 | G1 채택, OS 변경·ADB·emulator·기기 접근 |
| O4 exact G1 규범 채택 별도 승인 | 비참여 문서 검토 뒤 exact 조항/가정/위험 hash, 대체 범위·목적지·효력 시점·적용 검증을 명시 | F01 기술적 해결/종결·구현·모형/OS 캠페인·연결/설치/실행 |

O4는 제안한 요구를 규범으로 채택하는 결정이므로 아직 구현 proof가 없는 사실을 ‘PASS’로 바꾸지 않는다. 채택 이후에도 PR02–PR12와 연결/등록/첫 mutation의 별도 승인이 미충족이면 접근은 계속 금지한다. 자동 deployment나 R1 활성화도 없다. 채택된 redline을 실제 규범에 반영하는 작업도 별도로 범위를 고정해야 한다.

[owner 승인 양식](benchmarks/real-device-gate-g1-proposal/owner-approval-template.json)은 **미서명 양식**이다. proposal·조항·가정/위험·proof·검증 계획의 exact hash와 별도 결정 필드, 승인자·시각·적용 범위·동의한 위험 ID를 기록하도록 준비했다. G1 채택용 필드와 연결/첫 mutation용 필드를 분리하고 모두 미부여 상태로 둔다. 생성된 hash를 owner 승인으로 간주하지 않는다.

[독립 검토 입력](benchmarks/real-device-gate-g1-proposal/independent-review-package.json)은 검토자 독립성, 원 계약 대비 변경, bootstrap/actual channel/우회 proof, 실제 effect oracle, 개인 데이터/UNKNOWN 경계를 묻는다. 작성·관련 구현·측정·운영 비참여 검토자가 exact dossier에 대해 이유와 clause/proof ID를 기록해야 한다. 저자의 문서 대조와 자동 형식 검증은 독립 심사가 아니다. 현재 검토자 배정·검토 수행·독립 수용은 **PENDING**이며 다른 사람에게 메시지를 전송하지 않았다.

**다음 단계는 하나다. 준비한 exact-hash 패키지의 비참여 문서 검토 결과를 근거로 소유자가 G1 기각·수정·한정 mock·별도 규범 채택 중 하나를 결정한다.** 독립 심사 준비를 캠페인 실행이나 기기 접근 승인으로 확장하지 않는다. [다음 행동 결정](benchmarks/real-device-gate-g1-proposal/next-action-decision.json).

## 13. 이번 작업의 검증과 보존

작업 전 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이고 기존 tracked 변경 13개와 미추적 자료를 그대로 인계했다. 기존 **7,476개 파일**과 외부 원 B03 sidecar 5개, HEAD·branch·Git index/staged identity를 전후 대조한다. PREP10의 보고서·결정·원 source 사본·manifest도 역사 증거로 보존하며 기존 ‘O3 미승인’ 기록을 소급 수정하지 않는다. 이번 소유자 선택은 새 승인 범위 기록에만 남긴다.

| 이번 실행 | 결과 |
| --- | --- |
| G1 요구·위험·proof·승인 범위 문서화 | proposal-only, 미적용 초안 |
| source/근거 hash와 문서 내부 ID·링크·승인 상태 대조 | 문서 형식·보존 검증, 기술 enforcement/독립 심사 PASS 아님 |
| `npm run build` | 작업 전용 사본에서 exit0 |
| 기존 backend 소형 회귀 | 신규 합성 임시 DB에서 72 tests·44 subtests 통과, exit0 |
| ADB 호출 | host-only 포함 0 |
| emulator/물리 기기/설치/실제 G1 모형·OS 캠페인 | 모두 0·미실행 |

[저장소 검증](benchmarks/real-device-gate-g1-proposal/repository-validation.json)에 argv/cwd·압축 로그·JUnit을 보존한다. 성공 로그 전체를 출력하지 않았다. 이 필수 검사들은 G1의 독립 proof나 12 trace 실행 결과가 아니다. 기존 bwrap 초기화 실패 이력에 따라 승인 검토된 host 실행 경로를 사용했으며 운영 executor나 Android 도구를 호출하지 않았다.

작업 소유 검증 scratch만 비활성 확인 후 정리하고, 보고서·결정 JSON·근거·미서명 승인 양식·검증 helper·압축 로그·JUnit은 보존한다. 기존 SDK/AVD/APK/cache·DB·source locks·다른 작업 파일은 정리하지 않는다. [정리 기록](benchmarks/real-device-gate-g1-proposal/artifact-cleanup.json), [보존 결과](benchmarks/real-device-gate-g1-proposal/preservation.json), [최종 문서 검증](benchmarks/real-device-gate-g1-proposal/final-validation.json), [증거 manifest](benchmarks/real-device-gate-g1-proposal/evidence-manifest.json).

**G1: DRAFT — NOT APPROVED / NOT APPLIED. F01: UNRESOLVED — ORIGINAL REQUIREMENT BINDING. 운영 dispatch: BLOCKED.** N01/F02/F03/FC01 독립 종결과 역사 증거·Git index를 보존한다. T6.9는 DEFERRED, formal T6.6F closure는 NOT AUTHORIZED, R1은 CLOSED, production deployment는 NOT AUTHORIZED다. 새 운영 executor/앱/프로토콜 구현·실제 기기 접근·commit·push는 없다.
