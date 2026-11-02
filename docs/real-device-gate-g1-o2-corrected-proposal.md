# Real-Device Gate — G1 별도 안전 계약 제안서 — O2 수정 후보

**Revision: G1-O2-CANDIDATE-01. 원안과 G1-R01은 역사 근거로 보존하며 이번 후보만 R02 검토 대상으로 삼는다. O2의 문서 수정 승인은 G1 채택/적용 또는 검증/기기 실행 승인이 아니다.**

**문서 ID: G1-PROPOSAL-01 / 계약 초안 ID: F01-G1-DRAFT-01.**

**제안 작성 완료 — G1 미승인·미적용, 원 F01 계속 유효, 운영 dispatch 및 기기 접근 차단 유지.** 소유자의 이번 O2 결정은 G1-R01의 세 차단 finding에 한정한 문서 수정과 R02 인계 준비만 승인한다. 계약 채택·위험 수용·구현·검증 캠페인·ADB·emulator·개인 기기 연결/설치/시험을 승인하지 않는다. [이번 승인 범위 기록](benchmarks/real-device-gate-g1-o2/owner-o2-authorization.json).

G1의 심의 대상은 **transport ID 선택 + 강제 격리 ADB/device 환경 + 명시적 등록·연결 세대 + 고정 action·1회 세션·실패 즉시 중단**이다. 조건부 no-other-target 보증을 제안하지만 현재 그 보증이 성립했다고 판정하지 않는다. 특히 **최초 단말 등록(PR03), USB incarnation 강제(PR04), 실제 server/channel 결합(PR05), 전면 매개(PR06), 효과 전달 전 권한 폐기(PR07)는 미해결 필수 증명**이다. 이 결측을 잔여 위험 수용으로 면제할 수 없다.

## 1. 현재 결정과 문서의 효력

원 F01 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

G1 초안은 이를 이미 충족했다는 해석이 아니다. 원 identity/mutation 결합 proof를 **명시한 신뢰 가정, 독립 초기 등록, 실제 자원 수명 결합과 OS 도달 제한에 의한 조건부 엄격 승인 계약**으로 대체할지를 소유자가 별도로 심의할 수 있도록 준비한 문서다. 원 요구는 exact amendment 승인·적용이 완료될 때까지 계속 binding이다. 문구 변경이나 위험 서명을 F01의 기술적 해결·종결로 표현하지 않는다. [원 F01 결정](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json), [PREP10 판정](real-device-gate-prep10-f01-architecture-decision.md).

이번 작업에서는 규범 원본·B03/B11 binding·금융 authority·기존 실행기/guard/app을 수정하지 않는다. 현재 `scripts/devicegate/dispatch.py`의 무조건 거부와 `require_host_confinement()`의 거부를 보존한다. 시험 어댑터, 새 boolean/token/환경 설정 또는 문서 승인을 운영 활성화 경로로 만들지 않는다. [현재 중앙 경계](../scripts/devicegate/dispatch.py), 근거 R09·R10·R12.

후속 규범 채택을 승인하더라도 그것은 **어떤 보증을 요구할지** 정하는 결정이다. 해당 보증의 구현·독립 proof 수용과 실제 기기 접근·첫 mutation 승인은 별개다. 채택 문구의 정확 hash, 적용할 규범 위치와 redline, 원 F01의 대체 범위·효력 시점이 명시되지 않으면 계약은 바뀌지 않는다. 현재 normative destination도 정하지 않았으며 새 규범 파일을 만들지 않았다.

## 2. 근거와 보증 등급

프로젝트 이력은 PREP01–PREP10 보고서·JSON·현재 source로 재구성했다. 공개 인터페이스 의미는 PREP10에 보존된 공식 문서와 AOSP revision `1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc`의 고정 사본을 사용한다. 이번에는 ADB help/version도 실행하지 않았고 최신 binary 기능이나 실제 host/device 상태를 새로 조사하지 않았다.

[근거 목록](benchmarks/real-device-gate-g1-o2/evidence-catalog.json)은 PREP10의 R/AOSP 근거를 원 경로·SHA로 참조하고, 이번 소유자 지시와 제안 배경을 G01–G07로 추가한다. 현재 사용자 지시는 텍스트 전사로 보존했으며 원 메시지 전송 bytes의 해시나 별도 실명 서명을 입증했다고 주장하지 않는다.

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

아래 조항과 [계약 JSON](benchmarks/real-device-gate-g1-o2/g1-contract-proposal.json)은 모두 **미승인 초안**이다. 승인 대상의 정확 문구는 JSON의 `normative_clauses_if_separately_adopted`이며 이 표는 심의를 위한 요약이다.

| 조항 | 제안하는 의무 |
| --- | --- |
| G1-01 효력 | 단일 owner·특정 개인 단말·한 고정 세션으로 한정한다. 별도 채택/적용 전에는 원 F01 유지 |
| G1-02 안전 속성 | 신뢰 가정과 초기 결합 proof 아래 actual reachability를 `P*`에 제한하고 승인 범위 밖 effect 경로를 허용하지 않음 |
| G1-03 초기 등록 | CP 전부 수용 + owner 연결 grant와 IP 전부 수용 + owner 첫 mutation grant를 별도 식으로 판정 |
| G1-04 자원 결합 | actual USB/server/client channel/transport/receiver 세대를 승인 문맥에 강제 결합. 이름/ID/polling은 대체 불가 |
| G1-05 전면 매개 | wrapper·후손·다른 client/socket·FD 전달·TCP/mDNS·재열거 우회와 auto server start/restart/reexec/fallback을 차단 |
| G1-06 폐기 | 진행 중에도 폐기·새 제출/write/자원 취득 금지; 미입증 remote는 UNKNOWN_QUARANTINED |
| G1-07 1회 action | literal argv/입력 bytes/artifact/순서/예산을 사전 고정. action 최대 1회 제출 시도, 앱 restart replay 금지 |
| G1-08 개인 데이터 | 별도 package/signer/storage와 synthetic backend. 필수 OS 부수효과는 명시하되 개인 앱/production/특별 권한/기기 전체 정책 변경 금지 |
| G1-09 진행 중 작업 | 동일 SUBMISSION_COMMIT 경계, RESERVED 예외 금지, 이미 제출된 작업/ACK·격리·독립 처분 분리 |
| G1-10 증거·예산 | CP/IP 예산·실제 세대와 PH5 POST 이력 수용 분리; remote task/자식/증거 결측 보존 |
| G1-11 독립 proof | CP/IP/POST와 수집·machine check·독립 수용·owner 권한 구분; 실제 Android lifecycle proof 필요 |
| G1-12 별도 권한 | 유한 emulator/app/중단/독립 수용 단계와 owner 연결/첫 mutation gate 분리; 실패는 종료 |

## 5. 신뢰 가정과 위협 모델

[가정 register](benchmarks/real-device-gate-g1-o2/guarantee-and-assumption-register.json)의 AS01–AS06은 모두 **PENDING — NOT ACCEPTED**다.

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

## 8. PR07/G1-09의 공통 제출 경계와 진행 중 무효화 — O2-F02

PR07의 새 effect 전달 금지는 **다른 target effect=0**과 **무효화 후 새 제출/write/자원 취득=0**으로 독립 판정한다. 이미 승인된 동일 action이 같은 receiver/channel에서 나중에 만든 효과를 새 action의 전달과 혼동하지 않는다. 기존 host 시도<=1, actual recipient binding, OS enforcement와 N01 자식 회수 의무는 줄이지 않는다.

`SUBMISSION_COMMIT`은 고정 receiver/channel에 승인 bytes의 실제 제출이 시작됐음을 입증한 사건이다. PREPARED/RESERVED·host 메모리 queue·Popen/argv 생성·마지막 probe는 commit이 아니다. 지원되는 경계와 사건 순서 proof는 PR04–PR07에 여전히 OPEN이다. 순서나 실제 receiver를 입증하지 못하면 UNKNOWN_QUARANTINED이며 이 상태가 오대상 효과나 폐기 후 제출 위반을 면제하지 않는다.

무효화 전에 동일 action/receiver/channel에 이미 제출된/버퍼링된 bytes·원격 작업만 잔여 범위다. 무효화 뒤 새 host write, 남은 bytes를 새 channel/receiver에 이전, 새 resource 취득은 항상 금지한다. host 취소/kill이 device-side task를 즉시 종료하거나 rollback한다고 주장하지 않는다.

| 이력 | 필수 판정 |
| --- | --- |
| 제출 전 취소 | NOT_SUBMITTED, REVOKED·QUARANTINED; 전송 0 |
| RESERVED 뒤 미전송 취소 | 예약은 소비됐지만 제출 권한 없음. 미전송 입증 불가이면 UNKNOWN_QUARANTINED |
| 이미 수신된 고정 action이 취소 후 완료 | 다른 target 효과0·새 제출0은 필수. 후속 완료/ACK를 별도로 기록하고 세션 복귀 없음 |
| ACK 뒤 app task 지속 여부 불명 | action ACK는 보존하되 remote_task=UNKNOWN, session=UNKNOWN_QUARANTINED |
| server/transport/receiver 교체 중 부분 전송 | 새 자원·재접속·buffer 이전0. 결과/종료 미입증은 UNKNOWN_QUARANTINED |
| host/supervisor 실패 또는 자식 잔존 | 새 제출 차단·기존 N01의 bounded stop/reap proof 필요. host 미회수는 안전 실패이고 remote 종료는 추정하지 않음 |

연결/transport의 단절·reset·교체, ADB server/client 재시작, 실제 channel·receiver 세대/신원 불일치, authority 철회·취소, 감독 상실, 자원/시간/증거 실패는 진행 중에도 authority를 영구 REVOKED로 만든다. 같은 이름/ID 재등장이나 뒤늦은 ACK로 복구하지 않는다. 소유 host 자식·후손은 기존 N01 범위로 회수하며 기기에 stop/kill/clear/uninstall을 보내는 자동 복구는 없다.

IR_EVIDENCE는 이미 확보된 host/선행 승인 observer 기록만으로 실제 수신자·commit/무효화 순서·ACK·remote task·자식 회수를 독립 처분한다. 종료 proof가 없으면 UNKNOWN_QUARANTINED 유지, 추가 mutation/readback/reconnect/수집 금지다. 독립 해소도 폐기된 같은 세션을 재개하지 않는다. 새 작업은 해소 뒤 별도 owner 결정이다. [공통 판정 JSON](benchmarks/real-device-gate-g1-o2/pr07-g109-consistency.json).

## 9. 단계별 proof 수집·수용과 두 허가식 — O2-F01

| phase | 의미 | 허용 범위 |
| --- | --- | --- |
| PH0 | 연결 전 준비 | 개인 대상 미연결; 별도 승인된 static/mock/lab/emulator 증거와 CP 수용. O2에서 실제 캠페인 미실행 |
| PH1 | 통제된 연결·등록 | CP 전부 수용 및 별도 owner 연결 승인 후 고정 read-only 등록만; 모든 mutation 0 |
| PH2 | 연결 후 binding 수용 | 실제 U*/S*/C*/T*/R* transcript를 IR_SESSION이 수용; mutation 0 |
| PH3 | mutation 직전 승인 | CP/IP 전부 수용과 owner 첫 mutation 승인·유효성/연속성 검사; 첫 제출 전까지 mutation 0 |
| PH4 | 진행 중 연속성 | 승인된 action만 1회; 각 후속 action 직전 checkpoint. 무효화 때 새 제출 금지·격리 |
| PH5 | 종료 후 증거 평가 | 분리 후 host에 확보된 증거만 IR_EVIDENCE 수용. 새 device 접근/권한 없음 |

각 PR01–PR12 안에 **CP(개인 단말 연결 전 메커니즘/적용성), IP(승인 등록 후 첫 mutation 전 개별 세대), POST(종료 이력)**를 둔다. PR ID를 늘리거나 전체 PR의 단일 accepted boolean으로 합치지 않는다. PH0의 별도 승인된 lab/Android 증거와 PH1의 실제 개인 단말 값을 구별한다. O2에서는 이 증거를 수집/수용하지 않았고 모든 기술 facet은 PROOF_PLANNED/PENDING이다.

`PROOF_PLANNED → EVIDENCE_COLLECTED → MACHINE_CHECK_PASSED → INDEPENDENTLY_ACCEPTED`는 proof 기록이고, `NOT_GRANTED / AUTHORITY_GRANTED / REVOKED`는 별도의 owner 권한 기록이다. 수집이나 machine check는 독립 수용이 아니며 독립 수용도 owner 허가가 아니다. 기계는 exact 증거/hash/scope/세대·기한/독립 receipt를 검사하고 기술 판단은 지정 비참여자가 한다.

| PR | PH0에서 수집·IR_TECH 수용할 CP | PH1 수집·PH2 IR_SESSION 수용할 IP | 연결 전에 얻을 수 없는 증거 |
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

모든 CP의 최초 수집/수용은 PH0, IP는 PH1/PH2, 실제 POST 이력은 PH4 수집 시작·PH5 IR_EVIDENCE 수용이다. 각 facet의 증거·machine status·reviewer·추가 인간 판단·무효화·허용/거부는 [12개 상세 행렬](benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json)에 고정한다. 각 CP 미수용 전에는 연결/mutation 금지, 각 IP 미수용 전에는 모든 mutation 금지다. POST 수용 전 실행 이력은 사전에 유효했던 CP/IP/owner 범위에서만 허용되며 POST가 과거 권한을 소급 만들지 않는다.

**ALLOW_CONTROLLED_CONNECTION** = 유효한 별도 규범 authority ∧ PR01–PR12.CP 전부 독립 수용 ∧ D의 통합 수용 ∧ exact 사전 신원/manifest ∧ owner의 연결·고정 read-only 등록 전용 grant ∧ 자격검증된 등록 전용/OS 경계 ∧ 무효화·격리 없음. 이 식은 미래 U*/C* 관측값, IP/POST, 첫 mutation grant를 선행 요구하지 않는다. PH1의 제한된 등록 외 mutation은 허용하지 않는다.

**ALLOW_FIRST_MUTATION** = 같은 연결 세션의 유효 CP ∧ PR01–PR12.IP 전부 독립 수용 ∧ E2 보충 수용 ∧ owner의 별도 첫 mutation grant(exact candidate/manifest/transcript) ∧ actual binding/OS enforcement/fresh package/bytes/예산·연속성 일치 ∧ UNKNOWN/REVOKED/QUARANTINED 없음. IP 하나라도 결측이면 최초 설치·marker·launch 포함 mutation 0이다. 첫 설치 gate에 설치로만 생성될 receipt나 POST를 요구하지 않는다.

**ALLOW_NEXT_MUTATION**은 위 수용/권한·연속성 외에 이전 action의 결과와 사전 정의된 checkpoint 수용을 요구한다. PR08의 실제 설치본/서명/bytes 확인처럼 새 material 증거는 승인 설치 후 고정 read-only로만 수집하고 IR_SESSION이 수용할 때까지 다음 launch/mutation 금지다. 새 입력은 generation slot만 채우며 사전 identity/명령/예산 공란이나 계획 변경을 허용하지 않는다. 매 action의 자동 연속성 검사는 사전 수용된 정책의 적용이며 새 독립 수용을 발급하지 않는다.

PR12.CP는 PR01–PR11.CP, PR12.IP는 PR01–PR11.IP, PR12.POST는 해당 POST만 통합해 자신을 선행조건으로 요구하지 않는다. 새 단절·restart·resource 변경 때 IP를 같은 session에서 다시 얻어 권한을 복구할 수 없다. 등록/수용/owner 대기가 deadline을 넘으면 승인으로 간주하지 않고 종료한다. [별도 허가식](benchmarks/real-device-gate-g1-o2/device-admission-conditions.json). 이 식은 미구현 선언이며 현재 연결·첫/후속 mutation 결정은 모두 DENY다.

## 10. 실제 Android lifecycle과 독립 수용까지의 유한 경로 — O2-F03

기존 D0/V1/V2/V3 의도를 유지하며 A/B/C/D/E의 다음 단계로 구체화한다. 아래는 **별도 승인 대상 계획**이고 O2에서 구현·실행하거나 독립 수용하지 않았다. 각 단계의 entry, 허용/금지, artifact, 객관적 pass/fail, 실행 역할/비참여 수용자, 시도/시간/bytes, 실패/exit은 [완전 단계 JSON](benchmarks/real-device-gate-g1-o2/finite-validation-stages.json)에 고정한다.

| 단계 | 내용 | 제안한 최대 범위 | 종료점 |
| --- | --- | --- | --- |
| A | 정적 architecture·authority 심사 | {"reviews": 1, "seconds": 7200, "evidence_bytes": 10485760} | R02 문서 판정과 별도 owner 범위 결정; 구현/실행 승인 아님 |
| B | 별도 승인 구현 후보 동결 | {"candidates": 1, "freeze_reviews": 1, "evidence_bytes": 20971520} | 단일 후보·scope 종료. 승인된 구현 작업 시간 상한도 착수 전 exact로 고정; 없으면 미착수 |
| C1 | mock isolation·dispatch denial | {"models": 1, "trace_ids": 12, "seconds": 3600, "evidence_bytes": 10485760, "fixed_histories": 14} | mock 결과 한 묶음; 실제 USB/Android proof 아님 |
| C2 | 실제 host OS·USB 격리 lab | {"recipes": 1, "scenarios": 8, "seconds": 5400, "evidence_bytes": 20971520} | 정확 OS enforcement dossier; qualified mechanism 없으면 BLOCKED |
| C3 | 격리 emulator 실행·재연결 | {"fixtures": 4, "scenarios": 4, "seconds": 1800, "evidence_bytes": 20971520} | 실제 Android 연결 동작 증거; physical USB/phone 신원 proof 아님 |
| C4 | 최종 APK의 실제 앱 task lifecycle | {"fixtures": 6, "scenarios": 6, "seconds": 2700, "evidence_bytes": 20971520} | PR08 CP actual lifecycle dossier. 같은 source만으로 phone OS/ABI 적용성 수용 금지 |
| C5 | host/guest 중단·부분 완료 | {"fixtures": 6, "scenarios": 6, "seconds": 2700, "evidence_bytes": 20971520} | 부분 완료/격리 수용 증거. 각 의도적 음성 fixture는 격리 종료; 다음 사전 지정 fresh fixture는 복구 retry가 아님 |
| D | source/runtime/artifact·모든 CP 독립 수용 | {"decisions": 1, "seconds": 7200, "evidence_bytes": 52428800} | CP_ALL_ACCEPTED 또는 BLOCKED/REJECTED 한 판정; owner grant 아님 |
| E0 | 실제 단말 작업 전 owner 결정 | {"owner_decisions": 1, "sessions": 1, "automatic_retries": 0} | 실기기 연결 전 명시 GO 또는 DENY; O2에서는 NOT_GRANTED |
| E1 | 통제된 개인 단말 연결·고정 등록 | {"sessions": 1, "shared_E1_E3_seconds_ceiling": 600, "shared_evidence_bytes": 10485760} | IP evidence collected만; 수집/machine PASS가 수용/허가 아님 |
| E2 | 연결 후 모든 IP 독립 보충 수용 | {"decisions": 1, "must_fit_shared_session_deadline": true} | IP_ALL_ACCEPTED 또는 BLOCKED/격리; 첫 mutation GO 아님 |
| E3 | owner 첫 mutation·고정 acquisition | {"sessions": 1, "attempts_per_action": 1, "shared_E1_E3_seconds_ceiling": 600, "shared_evidence_bytes": 10485760} | 완료 또는 REVOKED/UNKNOWN_QUARANTINED. 세션 안 수용/owner 대기시간도 600초 이내; 무응답 승인 없음 |
| E4 | 분리 후 모든 POST 독립 수용·실패 처분 | {"decisions": 1, "seconds": 7200, "evidence_bytes": 52428800} | 증거 수용/위반/UNKNOWN 한 판정. 새 실행/규범 허가나 같은 세션 복귀 없음 |

C1의 기존 T01–T12 ID는 유지하고 T10의 고정 하위 이력은 제출 전·RESERVED 미전송·이미 수신된 작업의 취소 후 완료 3개로 명시한다. 각 한 번만 실행할 계획이며 12개 ID를 포괄 형식 증명이라 부르지 않는다. C2의 실제 USB 자원 proof와 C3 emulator 연결 proof는 서로 대체하지 못한다. C3에 F01/FC01을 우회하지 않는 자격 경로를 마련하지 못하면 BLOCKED다.

C4는 최종 APK bytes/signer/native ABI·실제 Android image/OS와 process/task 효과를 독립 관측한다. normal start, duplicate intent, process recreation, durable claim 뒤 death, partial task death, 완료 후 restart를 각 fresh fixture에서 한 번 검증한다. 모형 T12/기존 PREP02 정상 smoke만으로 PR08을 수용하지 않는다. emulator에서 사용한 artifact·OS/ABI와 phone 적용 범위가 다르면 D에서 별도 적용성 proof를 요구하고 없으면 BLOCKED다. emulator 성공은 개인 phone 신원/물리 USB 격리 proof가 아니다.

C5는 host/supervisor·guest/adbd 중단, ACK 유실/부분 완료, 이미 ACK된 task의 지속 여부를 실제 Android에서 검증한다. 사전 승인된 고정 음성 시나리오가 규정대로 DENY/UNKNOWN_QUARANTINED가 된 경우만 관측 PASS다. 새 host 제출·오대상 효과·자식 미회수는 FAIL이며 ‘예상 UNKNOWN’으로 덮지 않는다. remote 종료가 입증되지 않은 fixture는 격리하고 다시 device 명령을 보내지 않는다. 다음 사전 지정 fresh fixture는 재시도/복구가 아니며 실제 결측·위반이면 캠페인 자체를 종료한다.

D에서는 비참여 IR_TECH가 source/tool/runtime/final APK/OS 정책과 PR01–PR11.CP를 검토해 PR12.CP까지 명시 수용해야 한다. 이는 owner 연결 허가가 아니다. E0에서 소유자가 exact 연결/read-only 범위를 별도로 결정한 뒤에만 E1이 가능하다. 실제 인스턴스는 E1 수집, E2 독립 수용, E3의 별도 owner 첫 mutation 확인 순서다. E4는 확보된 증거로 모든 POST와 실패 처분만 수행한다.

모든 단계는 1개 후보/recipe와 고정 시나리오 각 1회이며 retry·자동 수정·추가 조사 루프가 없다. 지원 mechanism·actual lifecycle·적용성·identity/필수 증거가 없으면 해당 단계에서 BLOCKED/REJECTED로 종료하고 개인 단말을 먼저 조작해 결측을 채우지 않는다. E1–E3 공유 600초/10MiB는 제안 상한이지 승인된 실행값이 아니며 exact 세부값 공란이면 연결 불가다. 심사/owner 응답 대기도 상한 안에서 끝나야 하며 무응답은 승인이 아니다.

## 11. 개인 단말 잔여 위험과 수용 조건

[위험 register](benchmarks/real-device-gate-g1-o2/residual-risk-and-acceptance-register.json)의 모든 `owner_accepted`는 false다. 이번 제안 작성으로 기기 데이터 노출은 없다.

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

소유자는 이번에 **G1-R01-F01/F02/F03에 한정한 O2 문서 수정만 승인**했다. 아래 O1/O3/O4나 계약 채택/캠페인/기기 실행을 승인했다고 기록하지 않는다. 원안의 O2 선택지는 역사 근거로 보존하고 이번 권한은 별도 기록에 둔다. [결정 대안과 정확 문안](benchmarks/real-device-gate-g1-o2/approval-and-rejection-options.json).

| 대안 | 승인 또는 거부할 정확 대상 | 따라오지 않는 권한 |
| --- | --- | --- |
| O1 G1 기각 | 원 F01과 차단을 유지하며 새 작업 없음 | 새 조사·구현·접근 |
| O2 특정 문서 수정 | clause/proof ID와 결함·수정 범위만 명시 | 자동 구현·반복 감사·실험 |
| O3 V1만 한정 승인 | 원 F01 유지 상태에서 exact plan/hash의 모형 1개/12 trace/1시간/10MiB만 | G1 채택, OS 변경·ADB·emulator·기기 접근 |
| O4 exact G1 규범 채택 별도 승인 | 비참여 문서 검토 뒤 exact 조항/가정/위험 hash, 대체 범위·목적지·효력 시점·적용 검증을 명시 | F01 기술적 해결/종결·구현·모형/OS 캠페인·연결/설치/실행 |

O4는 제안한 요구를 규범으로 채택하는 결정이므로 아직 구현 proof가 없는 사실을 ‘PASS’로 바꾸지 않는다. 채택 이후에도 PR02–PR12와 연결/등록/첫 mutation의 별도 승인이 미충족이면 접근은 계속 금지한다. 자동 deployment나 R1 활성화도 없다. 채택된 redline을 실제 규범에 반영하는 작업도 별도로 범위를 고정해야 한다.

[owner 승인 양식](benchmarks/real-device-gate-g1-o2/owner-approval-template.json)은 **미서명 양식**이다. proposal·조항·가정/위험·proof·검증 계획의 exact hash와 별도 결정 필드, 승인자·시각·적용 범위·동의한 위험 ID를 기록하도록 준비했다. G1 채택용 필드와 연결/첫 mutation용 필드를 분리하고 모두 미부여 상태로 둔다. 생성된 hash를 owner 승인으로 간주하지 않는다.

[독립 검토 입력](benchmarks/real-device-gate-g1-o2/independent-review-package.json)은 검토자 독립성, 원 계약 대비 변경, bootstrap/actual channel/우회 proof, 실제 effect oracle, 개인 데이터/UNKNOWN 경계를 묻는다. 작성·관련 구현·측정·운영 비참여 검토자가 exact dossier에 대해 이유와 clause/proof ID를 기록해야 한다. 저자의 문서 대조와 자동 형식 검증은 독립 심사가 아니다. 현재 검토자 배정·검토 수행·독립 수용은 **PENDING**이며 다른 사람에게 메시지를 전송하지 않았다.

**다음 단계는 하나다. 별도 비참여 R02 검토자가 이 corrected candidate의 exact hash와 세 원 finding의 제안 해결을 문서로 심사한다.** 독립 심사 준비를 캠페인 실행이나 기기 접근 승인으로 확장하지 않는다. [다음 행동 결정](benchmarks/real-device-gate-g1-o2/next-action-decision.json).

## 13. O2 수정 후보와 현재 권한

이 후보는 원 제안서와 G1-R01의 exact hash를 보존한 새 버전이다. 12 clause·12 PR·14 RJ의 ID를 유지하고 세 finding에 해당하는 문구/수용/단계만 수정했다. 원문·수정문·사유·관련 PR/RJ·승인 단계·강도 판정은 [수정 matrix](benchmarks/real-device-gate-g1-o2/finding-correction-matrix.json), 재현 가능한 redline과 전후 hashes는 [변경 신원](benchmarks/real-device-gate-g1-o2/proposal-redline-and-hashes.json)에 있다.

R01의 PARTIAL 판정과 finding은 수정하지 않는다. O2의 문서 PASS는 제안된 해결을 R02에 제출할 준비라는 뜻이고 독립 finding 종결이나 기술 proof 수용이 아니다. 원 F01은 binding/unresolved, G1 미승인·미적용, 운영 dispatch BLOCKED, 기기 접근/모형/OS/emulator 캠페인 미실행이다. N01/F02/F03/FC01 종결·B03/금융/역사/source locks/Git index를 보존하고 commit/push하지 않는다.

새 미서명 [승인 양식](benchmarks/real-device-gate-g1-o2/owner-approval-template.json)은 이 corrected candidate와 수정 JSON만 승인 대상으로 pin한다. 이전 원안/양식은 historical provenance이며 이번 후보의 승인 대상이 아니다. [O2 수정 보고서](real-device-gate-g1-o2-contract-corrections.md), [R02 인계](benchmarks/real-device-gate-g1-o2/independent-r02-handoff.json).
