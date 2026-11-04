# Real-Device Gate G1-P01 — 기술 증명 실행 가능성 및 구현 계획

**판정: BLOCKED — NON-WAIVABLE SAFETY REQUIREMENT NOT FEASIBLE UNDER CURRENT ASSUMPTIONS.** 현재 저장소와 확인된 지원 근거로는 최초 단말 신원 결합, 실제 승인 채널과 수신자 결합, OS가 강제하는 기기 격리를 확립할 수 없다. 추가 polling·transport 선택·no-other-target·사후 앱 key·위험 서명으로 이 공백을 채울 수 없다. 모든 가능한 플랫폼의 불가능성을 증명한 판정은 아니다. 현 아키텍처에서 필수 메커니즘이 자격을 얻지 못했다는 범위의 판단이다.

안전한 첫 호스트 전용 준비 작업은 **FS1: 실행 권한을 만들지 않는 동결 action manifest의 순수 byte 검증기** 하나다. 실제 존재를 확인한 `scripts/devicegate/guards.py`와 `scripts/devicegate/test_safety.py` 두 파일의 추가 변경만 대상으로 삼는다. 이 준비 작업의 존재가 전체 G1 아키텍처의 실행 가능성을 입증하지 않으므로 전체 판정은 BLOCKED다. FS1 구현도 현재 승인되지 않았다.

이번 작업은 새 계획 문서와 근거만 작성한다. 기술 증명은 **12개 분석, 0/12 수용**, 36개 CP/IP/POST facet 모두 미수용이다. 원 F01은 **BINDING — UNRESOLVED**, 중앙 운영 dispatch는 **CLOSED/BLOCKED**다. 기기 등록·구현·OS 변경·ADB·emulator·APK 설치·물리 기기 접근은 수행하지 않았다. 이 계획 작성자는 기술 proof의 독립 수용자가 아니다.

## 1. 유효 규범과 읽은 근거

유효 계약은 [canonical G1 계약](real-device-gate-g1-safety-contract.md)이다. 실제 SHA-256은 다음과 같이 지정값과 일치한다.

`679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`

S7의 해시 고정 참조 12건, 승인 dependency lock의 직접 참조 16건, 효력·주석 연결 10건을 실제 bytes에서 대조했다. [해시·권한 검증](benchmarks/real-device-gate-g1-p01/contract-and-authority-verification.json)에 결과를 남겼다. S4/S7가 정확히 편입한 O2 required-proof/phase/gate/finite-plan의 의무·필수 증거만 현재 계약 아래 읽는다. 과거 O2의 대체 제안이나 `NOT_APPLIED` metadata를 현행 규범으로 삼지 않는다. 원 F01 AND 상위 적용 의무 AND 모든 유효 G1 의무가 누적된다.

[N3 완료 사건](benchmarks/real-device-gate-g1-n3-application/completion-record.json)의 ID는 `G1-N3-N4-N5-DOCUMENT-APPLICATION-COMPLETE-01`이다. N3 exact 승인·N4 적용·[N5 독립 정합성](real-device-gate-g1-n5-independent-application-consistency.md) 뒤의 효력 사건을 확인했다. N3/N5 당시 계약 hash `967e6b07…`는 [주석 전 보존 원본](benchmarks/real-device-gate-g1-status-annotation/original-before.md)에 대응한다. [상태 주석 정정](archive/device-gate/history/real-device-gate-g1-status-annotation-correction.md)과 [독립 검토](archive/device-gate/history/real-device-gate-g1-status-annotation-independent-review.md)가 현행 `679a16e0…` 신원으로 연결한다. 과거 해시·미결 사건을 재작성하지 않았다. 문서 적용·정정 PASS는 기술 수용이 아니다.

원 [PREP01 물리 기기 안전 요구](benchmarks/real-device-gate-prep01/physical-device-safety-contract.json)와 [기기 gate의 필수 공란 거부](real-device-gate-prep01-headless-emulator-foundation.md:172)도 읽고 고정 manifest 필드 29개·명시 owner 승인·고정 한 세션·개인 데이터 금지·단절 뒤 자동 정리 금지를 보존한다. 과거 `allowed_argv_templates`는 G1의 실제 literal argv/input 동결보다 약한 허용으로 쓰지 않는다.

AGENTS.md, 개발 산출물 위생, 프로젝트 상태·도메인 모델·알려진 이슈, architecture의 서버 authority 경계, runbook의 개발·검증 경계도 읽었다. 서버 DB/API의 금융 authority와 모바일 필수 구조·저장·복구·generation·Offline/pending 경계는 변경 대상이 아니다. B03 동기화·E3 guard-to-COMMIT·금융 계산·R1·운영 데이터는 이 계획의 구현 범위 밖이다.

| 상위 규범 | 유지되는 요구 |
| --- | --- |
| B §27·§29 | 실제 5개 규모/workload·gzip·rows/bytes/RTT·실기기 단계 분리; HOST 수치를 phone 수치로 표현 금지 |
| C §26 | Android SQLite pragmas/VFS·commit fence·I/O error·power-loss·previous recovery의 실제 구현 증명 |
| C §34·§34-B11 | 원 B03 8개 증거의 제한 이관과 별도 실행·독립 수용; 행정 종결은 formal whole-F PASS 아님 |
| C §35·§35-T69 | 원 source/runtime/fixture의 100k/5점·accepted provenance·계측·증거 보존 의무; T6.9는 계속 DEFERRED |
| C §38.8–12 | Android 내구성, legacy/B/J/migration, restore/MW, 30개 artifact/GC, scaling·post-T6.6 실기기 gate 차단 유지 |

원 F01의 정확한 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

[원 PREP03 finding](benchmarks/real-device-gate-prep03/finding-register.json), [PREP09 원 F01 결정](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json), [독립 잔존 반례](benchmarks/real-device-gate-prep09/regression/prior/f01-unclosed-interface-counterexample.json)를 직접 읽었다. 마지막 probe 뒤 `changed-after-last-probe`에서 모의 mutation이 남는 반례다. 실제 phone 치환·침해를 관측한 것으로 확대하지 않는다. 그 진단의 PASS는 결함 존속을 확인한 meta-test다. [PREP09 감사](archive/device-gate/history/real-device-gate-prep09-independent-dispatch-audit.md)의 N01/F02/F03/FC01 독립 종결을 인계하며 원 F01 해결로 전환하지 않는다. [PREP10](real-device-gate-prep10-f01-architecture-decision.md)의 B+C 조건부 후보는 역사 설계 비교다. 유효 보충 계약 아래 원 F01을 대체하는 선택지로 쓰지 않는다.

## 2. 현재 코드에서 확인한 지원과 한계

| 확인한 코드 | 현재 지원 | 충족되지 않는 보증 |
| --- | --- | --- |
| [dispatch.py:20](../scripts/devicegate/dispatch.py:20) | `spawn_process`가 인자를 평가하지 않고 무조건 `DispatchDenied` 발생 | OS sandbox·실제 device/channel binding |
| [smoke.py:80](../scripts/devicegate/smoke.py:80), [:183](../scripts/devicegate/smoke.py:183) | confinement·authority도 무조건 거부, 예외 후 `target_revoked` | 허용 가능한 운영 구현·qualified launcher |
| [run/start](../scripts/devicegate/smoke.py:228) | 진입과 terminal sink의 같은 중앙 거부, 취소 보호·소유 자식 등록/회수 | 실제 무효화 사건과 모든 host write의 순서화 |
| [host_guard/read_device/verify](../scripts/devicegate/smoke.py:500) | server/socket/transport·Android 속성을 순차 조회, 명시 `-s/-t` | 실제 service-channel peer와 검증 자원의 동일성, 원 F01 원자적 결합 |
| [guards.py](../scripts/devicegate/guards.py:42) | process/socket 조회·고정 합성 HTTP·sealed APK·pidfd/subreaper stop/reap | USB incarnation 인증·remote 종료·host 전체 우회 불가 |
| [앱 진입](../mobile/lib/main_devicegate.dart:19) | package/run ID 검사 뒤 합성 smoke 수행 | 재생성·duplicate intent 뒤 durable one-shot/replay 방지 |
| [Activity](../mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt:9) | configuration·16KiB private 결과 파일 기록 | durable consumed claim·기기 crypto enrollment·task 종료 증명 |
| [앱 네트워크](../mobile/lib/devicegate/isolation.dart:5), [Gradle](../mobile/android/app/build.gradle.kts:11) | test-only signer/package, exact emulator endpoint/route·redirect 거부 | phone-compatible 종단·실제 egress/OS 격리 |

`smoke.py`의 `application`, `remove_owned_test_package`, `finish`에는 전체 package 목록 조회·반복 결과 polling·4개 mode launch·clear/uninstall·emulator 종료의 과거 경로가 있다. 모두 현재 거부 경계 뒤에 있다. 이를 Galaxy 경로로 열거나 그대로 재사용하면 G1의 동결 action·최소 수집·무효화 후 정리 금지 요구를 만족하지 못한다. 이미 독립 종결된 F02/F03/N01의 범위를 새 phone 네트워크·lifecycle·identity로 확대하지 않는다.

검토한 고정 AOSP revision은 `1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc`다. 역사 공식 소스 사본 17개 해시를 재대조했다. 설치 Google binary와 그 source의 대응은 여전히 UNVERIFIED다. 현재 binary를 help/version으로 실행하지도 않았다. 보존 APK의 Flutter engine이 x86_64뿐이라는 PREP10 기록을 확인했으며 실제 phone ABI·OS·APK 적합성을 관측하지 않았다. [소스 목록](benchmarks/real-device-gate-g1-p01/source-catalog.json)에 경로·해시·함수 행과 적용 한계를 기록했다.

## 3. 세 비면제 보호의 실행 가능성

### A. 최초 단말 신원 결합 — ARCHITECTURAL BLOCKER

현재 설치 전 `P* → U* → C*/R*` 결합을 입증할 qualified mechanism이 없다. 연결 전에는 정확한 P*의 독립 owner-local 식별 근거와 bootstrap 메커니즘을 CP로 먼저 수용해야 한다. 모든 CP와 별도 owner 연결/read-only grant 후에만 PH1에서 실제 U*/C*를 등록한다. 미래 instance 값을 CP 선행조건으로 요구하지 않으며, 모든 IP의 독립 수용과 별도 첫 mutation grant 전 설치/marker/launch는 0이다.

| 구별할 대상 | 실제 의미와 한계 |
| --- | --- |
| ADB serial | 선택 이름/보고 필드. 물리 단말 인증·연결 incarnation 증명이 아님 |
| ADB transport ID | 같은 server 세대 안 객체 선택. 물리 P* 인증과 다름 |
| USB enumeration | bus/port/address/node의 현재 위치. 재사용·reset·교체 수명을 별도로 증명해야 함 |
| OS-level exposure | 자격 있는 정책이 도달 집합을 제한할 수 있으나, 처음 노출한 기기가 P*라는 proof가 먼저 필요 |
| device-side application identity | package/signer/run ID는 앱/시험 문맥. 첫 설치 대상의 물리 identity가 아님 |
| cryptographic identity | 현재 앱/등록 코드에 지원 없음. 설치 후 key를 만들거나 pinning해도 잘못된 최초 설치를 소급 인증하지 못함 |

ADB의 host-key 허용은 phone이 host를 허용하는 절차이며 반대 방향의 P* 인증이나 세션 실험 승인이 아니다. 동일 serial/build를 가진 다른 정상 phone 하나만 연결한 wrong-singleton은 반드시 거부해야 한다. 케이블 소유·목록 수량·사후 key는 충분하지 않다. Linux 공식 문서도 USB descriptor 신뢰를 경고한다. [Linux USB authorization](https://docs.kernel.org/usb/authorization.html).

최소 후보는 기존 Android가 설치 전에 제공하는 식별 채널과 owner-local 독립 기록을 고정 read-only transcript·실제 자원 연속성으로 연결하는 방법이다. 실제 지원·공격/실수 구별·wrong-singleton 근거가 아직 없어 선택할 수 없다. AS01–AS06의 신뢰 가정은 항목별 미수용이며, 가정을 승인해도 bootstrap 증거 결측을 면제할 수 없다.

### B. 실제 승인 채널과 수신자 결합 — ARCHITECTURAL BLOCKER

현재 `owned_tcp` 조회와 뒤의 새 CLI 실제 service 접속은 별도 사건이다. 고정 AOSP에서 `-t`는 같은 server 객체 선택을 강화하지만 `-s/-t`의 AND 검증이 아니다. ID는 server 재시작을 가로지르는 identity가 아니며 TCP reconnect 수명도 USB와 같지 않다. 이미 고른 한 service stream과 검증한 물리 단말·boot/adbd 세대의 결합을 따로 입증해야 한다. [고정 client 소스](benchmarks/real-device-gate-prep10/official-sources/client__adb_client.cpp.txt), [고정 transport 소스](benchmarks/real-device-gate-prep10/official-sources/transport.cpp.txt).

가장 작은 후보는 고정 binary·actual peer·transport 객체·USB 자원·receiver 세대를 결합하는 최소 resource broker다. pidfd는 host process 수명 보조 수단이며 socket/USB/receiver를 자동 인증하지 않는다. getprop service stream을 install/launch/readback에 자유롭게 재사용하는 공개 handle이 있다고 가정하지 않는다. 새 service 자원이 필요하면 사전 동결한 획득 규칙과 그 실제 receiver 결합까지 증명해야 한다.

transport 교체, USB 단절/재연결/reset, ADB server/client restart, device replacement, owner 철회, 동시 요청 모두에서 원 권한의 새 자원 승계와 남은 bytes 이전이 0이어야 한다. 한 host writer와 attempt ledger는 중복 제출 통제에 필요하지만 외부 USB/receiver 변화의 원자성을 만들지 않는다. 원 F01의 실행 승인 결합을 physical hardware의 동시 연산 요구로 과대 해석하지도 않는다. 현재 그 결합을 제공하는 지원 primitive가 미확인이라 운영 후보를 자격화할 수 없다.

### C. OS가 강제하는 기기 격리 — ARCHITECTURAL BLOCKER

환경 변수/private port는 설정 관례이고 `-s/-t/--one-device`는 process 선택이다. namespace/device-access 제한은 후보 구성 요소다. 이들을 모두 실제 도달 경로에 제거 불가능하게 적용하고 자원 수명까지 입증해야 mandatory enforcement가 된다. network namespace만으로 USB가 숨겨지지 않고, node 하나의 bind mount나 major/minor 허용은 P* 또는 incarnation 인증이 아니다.

필요한 구체 집행점은 다음과 같다.

- USB kernel/backend: 허가되지 않은 device/interface와 새 open·재열거·reset 재취득 차단, 기존 FD/URB/버퍼의 수명 규명.
- principal/process: 전용 비특권 principal, capability 제거·no_new_privs·exec 정책, ptrace/proc FD/SCM_RIGHTS·상속 FD 통제, 후손의 정책 변경·경계 탈출 차단.
- mount/device: 다른 USB node·정책 sysfs·host 제어 socket을 노출하지 않는 정확 recipe, node 재사용의 별도 차단.
- network/socket: 다른 ADB server·AF_INET/INET6/AF_UNIX·TCP discovery/mDNS/reconnect를 거부하고 합성 종단만 exact 허용.
- server/client: 검토 binary 고정·자동 start/restart/reexec/fallback 차단, 실제 peer/resource 수명 결합.
- revocation/I/O: 실제 무효화 사건과 새 effect 전달을 순서화하는 강제 경계. watcher와 사후 kill만으로 대체 불가.

Linux cgroup v2 device controller는 BPF와 type/major/minor의 장치 접근 제어를 설명한다. 이를 USB 물리 신원·진행 중 I/O 폐기 보증으로 확대하지 않는다. `cgroup.kill`도 host process tree의 기능이며 remote task 정지를 보장하는 수단으로 제시하지 않는다. [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html#device-controller).

현 host의 권한/kernel/LSM/cgroup/backend·실제 recipe는 미자격이다. 현재 도구의 bwrap 초기화 실패는 관측했지만, 모든 privileged recipe의 보편적 불가능성 증거로 삼지 않는다. qualified recipe가 없는 현재 상태에서 이 보호는 blocker다. [세 보호 상세](benchmarks/real-device-gate-g1-p01/three-safeguard-feasibility.json).

## 4. 실행 lifecycle과 중단 의미

아래는 **미구현 설계의 전이 조건**이다. 현 코드의 도달 상태는 `PRECONNECTION_DENIED`이며, 표의 뒤 전이를 실행하거나 허가하지 않았다. authority, action attempt, remote task, host child, 결과/위반을 각각 별도 필드로 보존해야 한다.

| 단계 | 전이 조건과 허용 범위 |
| --- | --- |
| `PRECONNECTION_DENIED → FROZEN` | 기기 없이 source/tool/최종 APK/fixture/target 식별/등록·action·효과·budget 동결. 정체성/계획 공란 허용 안 함. authority: `NOT_GRANTED`. |
| `FROZEN → CP_REVIEWED` | PR01–12.CP와 D가 비참여 IR_TECH에 의해 같은 적용 범위에서 수용. qualified OS·bootstrap·원 F01 메커니즘 포함. authority: `NOT_GRANTED`. |
| `CP_REVIEWED → READONLY_REGISTERING` | 별도 owner exact 연결/read-only grant, 실제 OS recipe 무장. 사전 고정 등록만. 설치/marker/launch=0. authority: `AUTHORITY_GRANTED_READONLY`. |
| `READONLY_REGISTERING → IP_REVIEWED` | 사전 정의 U*/S*/C*/T*/R* slot·실제 channel/receiver·budget/fresh package 부재를 PH1 수집, PR01–12.IP/E2를 PH2에서 독립 수용. authority: `AUTHORITY_GRANTED_READONLY`. |
| `IP_REVIEWED → ARMED` | owner의 별도 첫 mutation grant가 exact manifest·등록 transcript hash 지정, CP/IP 유지·deadline·모든 세대 일치. authority: `AUTHORITY_GRANTED_FIRST_MUTATION`. |
| `ARMED → RESERVED_CONSUMED` | 다음 고정 action ordinal을 durable하게 한 번 소모. 아직 실제 bytes 미제출. crash 후 UNUSED로 복구 금지. authority: `UNCHANGED`. |
| `RESERVED_CONSUMED → SUBMISSION_STARTED` | qualified primitive가 유효 authority와 동일 receiver/channel에서 승인 bytes의 실제 제출 시작을 입증. 메모리 queue·Popen·예약은 이 사건 아님. authority: `UNCHANGED`. |
| `SUBMISSION_STARTED → ACKED` | 사전 허용한 같은 channel 관측에서 action별 제출 bytes/ACK 귀속 확인. ACK는 PM durable 완료·비동기 task 종료와 별도. authority: `UNCHANGED`. |
| `ACKED → ARMED_OR_COMPLETE_EVIDENCE_PENDING` | 현재 권한 유효, 결과·필요한 postinstall read-only checkpoint와 새 material 증거의 IR_SESSION 수용 후에만 다음 action. 모두 완료·remote 종료/결과 확인이면 증거 대기. authority: `NO_NEW_GRANT`. |
| `ANY_LIVE_STATE → QUARANTINED_OR_UNKNOWN_QUARANTINED` | 무효화 사건 즉시 단방향 REVOKED, 새 제출/write/자원 획득/버퍼 이동 금지. 감독·자식 회수 수행. 어떤 제출/순서/종료가 미확정이면 UNKNOWN_QUARANTINED. authority: `REVOKED`. |
| `REVOKED → REVOKED` | 동일 serial/PID/TID 재등장·late ACK·독립 POST 처분에도 권한 복구 없음. 기존 receipt만 보존. authority: `REVOKED`. |
| `COMPLETE_OR_QUARANTINED → POST_CLASSIFIED` | 개인 단말 분리 뒤 확보된 host/선행 승인 observer 증거만 IR_EVIDENCE가 PH5 분류. 새로운 읽기/재연결/정리 없음. authority: `NO_AUTHORITY`. |

`SUBMISSION_COMMIT`은 승인된 고정 receiver/channel에 실제 action bytes 제출이 시작됐다고 귀속 가능한 전달 경계가 입증한 사건이다. PREPARED/RESERVED·메모리 queue·argv 생성·Popen·last probe PASS는 이 사건이 아니다. action의 한 번 소모는 제출 전에 durable하게 기록하고 crash 후 같은 세션의 재시도를 금지한다. 이는 remote exactly-once 완료의 약속이 아니다.

실제 무효화 발생 `t_event`, host 관측 `t_observe`, 집행 `t_enforce`, 각 실제 write/자원/버퍼 사건을 분리해야 한다. `t_observe/t_enforce`까지의 지연은 유예가 아니다. 무효화 뒤 새 제출·host write·자원 취득·buffer 이동은 0이어야 한다. 단일 event-loop나 timestamp만으로 외부 사건과의 순서가 강제됐다고 주장하지 않는다. 실제 sink의 순서를 모르면 UNKNOWN이며, 실제 늦은 write/오대상 effect가 확인되면 FAIL_VIOLATION이다. UNKNOWN으로 위반을 면제할 수 없다.

이미 같은 action/receiver/channel에 제출된 bounded bytes·그 원격 작업은 무효화 뒤 완료될 수 있다. 아직 전송하지 않은 APK 나머지 bytes나 RESERVED의 다음 action은 잔여 예외가 아니다. ACK는 service 응답, PM 내구 설치, 앱 task 종료와 별개다. 예를 들어 install ACK 후 앱 task 종료가 불명확하거나 `am start`가 반환했어도 시험이 계속되면 remote 상태를 별도로 확인해야 한다. 이 증거가 무효화 시 확보되지 않았다면 UNKNOWN_QUARANTINED다. 늦은 ACK는 기존 receipt를 보완할 뿐 authority를 복구하지 못한다.

| 사건 | 입증할 수 있는 범위 | 입증하지 못하는 것 |
| --- | --- | --- |
| host process termination | N01 조건 아래 소유 host process/후손 종료·reap. | ADB server queue·device PM/앱 task 종료·rollback·durable 금융/시험 결과. |
| transport disconnection | 연결 연속성 소실과 authority 폐기. | 이미 수신된 설치/앱 작업 중단 또는 durable 결과 부재. |
| device-side operation termination | 독립 remote task 관측이 실제 해당 task·세대의 종료를 입증한 범위. | 성공 commit 또는 rollback. 종료 전에 일부 내구 효과가 남을 수 있음. |
| durable mutation completion | 해당 action/receiver/plan과 저장 결과·필요 ACK/검증이 결합된 범위의 내구 결과. | 모든 remote task 종료·다른 기기 무효과·권한 재개. |

USB/transport 단절·reset/재등록/교체, server/client/channel 수명 변경, receiver identity/boot/adbd 불일치, 철회/취소, 감독 상실/자식 회수 미확인, deadline/bytes/자원/증거 실패, artifact/plan/policy drift는 단방향 REVOKED다. host stop/reap은 기존 N01 범위에서 수행하고 실패는 host 안전 실패로 기록한다. host 부모의 강제 죽음은 Python finally 실행조차 보장하지 않으므로 별도 OS 감독 경계가 필요하다. 그 경계가 있어도 remote stop/rollback을 추정하지 않는다.

장치 effect 전달과 사전에 열린 bounded 실패 journal은 분리해야 한다. journal 보존을 새 device write/FD/channel 취득의 우회 경로로 쓰지 않는다. 증거 저장 실패에도 성공을 반환하지 않는다. S3/G1-10과 이 실패 journal 경계의 정합성 역시 독립 심사 대상이다. 기기 안 앱의 사전 고정된 한 논리 시험이 계속될 수 있다는 사실을 선언하되 범용 agent의 새 명령/다음 action까지 이미 제출된 작업으로 넓히지 않는다.

무효화 뒤 새 readback/reconnect·추가 mutation·자동 stop/clear/uninstall은 금지다. 확보한 host/선행 승인 observer 증거만 비참여자가 사후 분류한다. remote 종료·durable 결과 미입증은 UNKNOWN_QUARANTINED를 유지한다. 정상 완료도 필요한 결과/종료·고정 read-only checkpoint와 새 material 증거의 IR_SESSION 수용 전에는 다음 action으로 넘어가지 않는다. [상태 전이·여섯 interruption 이력](benchmarks/real-device-gate-g1-p01/execution-lifecycle-threat-model.json).

## 5. 최소 구현 구성

다음 여섯 개는 책임 구분이며 새 daemon 여섯 개를 요구하지 않는다. M1/M3/M6는 같은 host 프로그램 안에 둘 수 있다. M2의 지원 primitive·초기 등록·OS recipe가 없으면 실행 가능한 설계로 승격할 수 없다. 현재 중앙 거부 함수는 모든 개발 단계에서 그대로 보존한다.

구현 순서는 FS1의 오프라인 구조 준비 → 별도 M2 단일 메커니즘/OS recipe 자격 결정 → 지원 가능한 경우에만 M2/M3 후보와 최종 M4/M5 artifact 동결 → 유한 host/lab/Android 검증 → M6 독립 수용이다. 각 화살표는 새 범위 승인 없이는 진행하지 않는다. PR03–07의 상호 참조는 같은 binding/enforcement 근거 묶음의 공동 검증 관계이며 선행 receipt를 서로 요구하는 순환 gate가 아니다. PR08/09도 같은 최종 APK·route 후보로 동결한다. 규범의 명시 facet 의존성은 원 행렬 그대로이고 PR12만 앞선 개별 facet 수용 뒤 통합한다.

### M1. 동결 manifest·권한/증거 종류 검증

| 항목 | 계획 |
| --- | --- |
| 책임 | 정확 source/artifact/action/효과/예산과 CP/IP/POST·owner grant 종류·scope 구조 검증. |
| 신뢰 경계 | 외부 승인/receipt 데이터→신뢰 executor; SHA는 내용 신원이며 owner 인증이 아님. |
| 현재 지원 | 봉인 APK와 구조 admission 일부. |
| 제안 기능 | 순수 byte parser·immutable manifest·범위별 receipt reader. |
| 잠재 영향 파일 | [scripts/devicegate/guards.py](../scripts/devicegate/guards.py), [scripts/devicegate/test_safety.py](../scripts/devicegate/test_safety.py) |
| 강제 방식 | 공란/변조/중복/종류 혼동은 거부; offline validator는 실행 권한을 만들지 않음. |
| 실패 처리 | 형식/identity 실패는 DENY 진단만; 기존 dispatch 거부 유지. |
| 검증 | 순수 fixture 양성·음성, authority 전이 없음, 모든 effect sink=0. |
| 의존성 | PR01, PR02, PR10, PR11 |

### M2. OS 전면 매개·resource binding 경계

| 항목 | 계획 |
| --- | --- |
| 책임 | P* 등록 근거와 U*/S*/C*/T*/R*를 실제 자원에 결합, 전체 device 도달 경로 및 사건 cutoff 집행. |
| 신뢰 경계 | 신뢰 provisioning principal/kernel/driver→비특권 broker/후손→USB/ADB/adbd. |
| 현재 지원 | 해당 기능 없음. require_host_confinement는 무조건 거부. |
| 제안 기능 | 정확 OS recipe와 지원 lifetime/submit primitive가 먼저 자격을 얻어야 하는 최소 broker. USB fd·pidfd·transport 숫자만으로 충분하다고 주장하지 않음. |
| 잠재 영향 파일 | [scripts/devicegate/smoke.py](../scripts/devicegate/smoke.py), [scripts/devicegate/guards.py](../scripts/devicegate/guards.py) |
| 강제 방식 | 전용 principal·제거 불가 device/network/IPC/FD/process 정책, 새 자원/자동 reconnect 차단, actual write와 invalidation 순서 강제. |
| 실패 처리 | 어느 메커니즘도 미자격이면 연결/운영 제출 경로 없음. watchdog만으로 통과 금지. |
| 검증 | 정적 lifetime 논증·별도 승인 C2 1recipe/8시나리오 두 sink·C3 실제 service 경로; mock/emulator를 USB proof로 승격 금지. |
| 의존성 | PR02, PR03, PR04, PR05, PR06, PR07, PR12 |

별도 OS provisioning/필요 native helper 소스는 현재 존재하지 않는다. 정확 신규 파일명·privileged 명령·실행 recipe를 발명하지 않고 별도 architecture 결정에서 지정.

### M3. 단방향 세션 제어·bounded journal·host 감독

| 항목 | 계획 |
| --- | --- |
| 책임 | attempt 1회 소모·고정 순서/checkpoint·REVOKED·UNKNOWN과 child/remote 결과를 분리. |
| 신뢰 경계 | owner/독립 수용→M2의 자원 제출; host 자식→remote 작업은 별개. |
| 현재 지원 | run/start 취소 보호·N01 stop/reap·target_revoked·출력 상한 polling. |
| 제안 기능 | durable consumed action ledger·사전 개방 bounded journal·resource event oracle·외부 supervisor 연계. |
| 잠재 영향 파일 | [scripts/devicegate/smoke.py](../scripts/devicegate/smoke.py), [scripts/devicegate/guards.py](../scripts/devicegate/guards.py), [scripts/devicegate/test_prep06.py](../scripts/devicegate/test_prep06.py), [scripts/devicegate/test_prep08.py](../scripts/devicegate/test_prep08.py) |
| 강제 방식 | M2의 qualified sink를 갖추기 전 기존 spawn_process는 그대로 무조건 raise. offline 모형/시험은 독립 synthetic sink에만 한정하며 운영 patch 경로 금지. |
| 실패 처리 | 권한 영구 폐기, host 소유 자식 회수, remote 미확정 격리. 자동 정리·재연결·재시도 없음. |
| 검증 | 원 N01/FC01 회귀 source 보존, C1 12/14 이력, C5 실제 interruption·독립 observer. |
| 의존성 | M1, M2, PR07, PR10, PR11 |

### M4. test 앱 durable one-shot·격리 결과

| 항목 | 계획 |
| --- | --- |
| 책임 | 승인 논리 시험을 네트워크/저장 효과 전에 한번 소모하고 재생성·중복 intent를 거부. |
| 신뢰 경계 | Android intent/Flutter engine→native test UID private durable store→합성 작업. |
| 현재 지원 | 격리 package/signer/storage/backup 제외·16KiB 결과 저장; durable claim 없음. |
| 제안 기능 | test-only native 동기 claim과 Dart 진입 gate, claim 손상/실패 시 작업 금지. 범용 command agent/지속 service/새 보안 권한은 불필요. |
| 잠재 영향 파일 | [mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt](../mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt), [mobile/lib/main_devicegate.dart](../mobile/lib/main_devicegate.dart), [mobile/android/app/src/devicegate/AndroidManifest.xml](../mobile/android/app/src/devicegate/AndroidManifest.xml), [scripts/devicegate/apk-policy.json](../scripts/devicegate/apk-policy.json), [mobile/test/devicegate_isolation_test.dart](../mobile/test/devicegate_isolation_test.dart) |
| 강제 방식 | 최종 APK에서 claim-before-effect와 no replay. claim은 device 물리 identity bootstrap 수단이 아님. |
| 실패 처리 | consumed 상태를 지우지 않고 재시작 때 종료/UNKNOWN만; clear/reinstall로 복구 금지. |
| 검증 | C4 여섯 fresh fixture lifecycle, C5 중단과 실제 Android durable I/O fault/효과 counter·phone 적용성 독립 심사. |
| 의존성 | M1, PR02, PR07, PR08, PR09, PR10 |

### M5. 고정 합성 backend·phone 경로

| 항목 | 계획 |
| --- | --- |
| 책임 | 정확한 합성 종단·경로·예산만 허용하고 production/redirect/fallback 차단. |
| 신뢰 경계 | host 합성 process/DB→고정 route→test app; production은 도달 불가. |
| 현재 지원 | 127.0.0.1:18081 synthetic backend·host F02·emulator 10.0.2.2 제한. |
| 제안 기능 | phone-compatible 경로 1개·정책/앱/Gradle/compiled resource 일치와 OS egress proof. |
| 잠재 영향 파일 | [scripts/devicegate/backend.py](../scripts/devicegate/backend.py), [scripts/devicegate/guards.py](../scripts/devicegate/guards.py), [mobile/lib/devicegate/isolation.dart](../mobile/lib/devicegate/isolation.dart), [mobile/android/app/build.gradle.kts](../mobile/android/app/build.gradle.kts), [mobile/android/app/src/devicegate/res/xml/devicegate_network_security_config.xml](../mobile/android/app/src/devicegate/res/xml/devicegate_network_security_config.xml), [scripts/devicegate/apk-policy.json](../scripts/devicegate/apk-policy.json) |
| 강제 방식 | M2 network 경계와 application exact origin/route·최대 요청·bytes·redirect 거부. |
| 실패 처리 | endpoint/route/listener 변경 시 폐기; 다른 origin 선택이나 18080 fallback 없음. |
| 검증 | host 기존 F02 보존, 비허용 sink hit=0, C3/4에서 실제 Android 종단/route 관측. |
| 의존성 | M1, M2, PR02, PR08, PR09, PR10, PR11 |

### M6. 독립 qualification dossier

| 항목 | 계획 |
| --- | --- |
| 책임 | source/runtime/artifact/OS/effect 관측과 reviewer receipt를 CP/IP/POST별 묶음으로 보존. |
| 신뢰 경계 | 저자/측정자 증거→비참여 심사자→owner 별도 결정. |
| 현재 지원 | 역사 독립 보고서·source lock·N3/N5 문서 검증. |
| 제안 기능 | 동일 후보의 36 facet receipt와 applicability·revocation ledger. 검사 수와 proof 수를 분리. |
| 잠재 영향 파일 | 실행 소스 없음; 새 qualification 문서만 |
| 강제 방식 | missing/expired/scope mismatch는 gate DENY; PR12 자기 의존 금지. |
| 실패 처리 | BLOCKED/REJECTED 또는 UNKNOWN 기록 후 종료. 자동 재심사·예산 연장 없음. |
| 검증 | 형식/hash/의존성 검사는 보조; 실제 전문 수용은 비참여자가 원 source/관측을 직접 심사. |
| 의존성 | M1, M2, M3, M4, M5, PR01, PR12 |

M4에는 현재 앱의 test-only durable claim-before-effect gate만 필요하다. Android Activity/process 재생성 가능성을 전제로, 메모리 flag·singleTop·host 1회 시도만으로 replay=0을 증명하지 않는다. 동기 claim 저장 실패·손상·소모 후 death는 실행을 막고 claim을 지우지 않아야 한다. 최종 APK의 실제 Android lifecycle 증거가 필요하다. [Android Activity lifecycle](https://developer.android.com/guide/components/activities/activity-lifecycle). 최초 설치를 해결하려고 crypto enrollment·범용 shell·항시 background agent·특별 권한을 추가하지 않는다. [구성요소 상세](benchmarks/real-device-gate-g1-p01/implementation-component-plan.json).

## 6. PR01–PR12 증명 행렬

분류는 계획 평가다. `IMPLEMENTATION AVAILABLE — EVIDENCE NOT ACCEPTED`는 전체 의무에 필요한 구현이 존재할 때만 쓰므로 현재 0개다. 부분 지원을 전체 구현 가능으로 집계하지 않았다. 구현 공백 6개, 아키텍처 차단 5개, 통합 수용의 근거 부족 1개다.

| PR | 계약의 제목 | 계획 분류 |
| --- | --- | --- |
| PR01 | 승인 provenance·계약 우선순위 | IMPLEMENTATION GAP |
| PR02 | artifact/tool 신원 | IMPLEMENTATION GAP |
| PR03 | 최초 등록과 bootstrap 결합 | ARCHITECTURAL BLOCKER |
| PR04 | USB incarnation 강제 | ARCHITECTURAL BLOCKER |
| PR05 | server/channel/transport 결합 | ARCHITECTURAL BLOCKER |
| PR06 | OS 전면 매개와 우회 불가 | ARCHITECTURAL BLOCKER |
| PR07 | 폐기·host 1회 시도·감독 수명 | ARCHITECTURAL BLOCKER |
| PR08 | 앱 격리와 자동 재실행 방지 | IMPLEMENTATION GAP |
| PR09 | 합성 backend·네트워크 | IMPLEMENTATION GAP |
| PR10 | 자원·증거·UNKNOWN 처분 | IMPLEMENTATION GAP |
| PR11 | 명령·효과 allowlist 완결성 | IMPLEMENTATION GAP |
| PR12 | 독립 통합 수용 | INSUFFICIENT SOURCE EVIDENCE |

각 ID는 [원 required-proof 행렬](benchmarks/real-device-gate-g1-o2/required-proof-matrix.json)의 `/proofs/0`부터 `/proofs/11` 및 [원 phase 행렬](benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json)의 같은 ID에서 추출했다. 행 번호로 의무를 추측하지 않았다. [P01 기계 행렬](benchmarks/real-device-gate-g1-p01/pr01-pr12-proof-matrix.json)은 원문 obligation/required evidence와 36개 facet 전체를 그대로 보존하고 계획 해석을 별도 필드로 둔다.

공통 phase는 CP 수집/수용 `PH0 / PH0`, IP `PH1 / PH2`, POST `PH4 / PH5`다. CP=개인 대상 연결 전 메커니즘/적용성, IP=승인된 등록 후 첫 mutation 전 실제 세대, POST=종료 이력이다. Stage0–6 번호와 혼동하지 않는다. 모든 facet은 실제 hash/수집 범위, exact source/tool/APK/OS/policy, session/generation 또는 offline 적용성, machine 결과, 비참여 reviewer receipt/scope/decision, 기한/폐기 상태를 요구한다. 증거 수집·machine PASS·독립 수용·owner grant는 네 별도 상태다.

### PR01 — 승인 provenance·계약 우선순위

**계획 분류: IMPLEMENTATION GAP — 수용 아님.**

1. **정확한 규범 요구:** 원 F01 계속 binding, exact-hash 별도 채택/적용·미부여 실행 권한 구분

   원 필수 증거: owner 승인 ledger·규범 redline·author/ref/hash·권한 없는 상태의 거부

2. **안전 보증:** 유효 보충 규범과 승인 종류·범위가 실행 허가로 혼동되지 않음.

3. **위협/실패:** 과거 proposal metadata, normative PASS, self-receipt를 연결/설치 권한으로 오인.

4. **현재 지원:** N3 완료·N5·주석 독립 검토와 dispatch의 무조건 거부가 존재. 근거: [scripts/devicegate/dispatch.py:20](../scripts/devicegate/dispatch.py:20), [scripts/devicegate/smoke.py:183](../scripts/devicegate/smoke.py:183), [docs/benchmarks/real-device-gate-g1-n3-application/completion-record.json](benchmarks/real-device-gate-g1-n3-application/completion-record.json).

5. **누락 집행:** 소유자 grant/비참여 receipt의 종류·exact scope·expiry를 검증하는 운영 ledger와 resource 귀속이 없음.

6. **필요한 구현 변경:** 입력 byte 기반 승인/receipt schema와 종류 분리 검증; 미부여 상태는 DENY만 출력. 향후 resource broker에만 독립 수용·owner grant 입력을 연결; 현재 거부 함수는 유지.

7. **필요 증거/계측:** 현재 canonical·완료 사건·후속 주석의 hash chain. 위조 종류/공란/만료/상충/과거 hash의 거부 fixture; reviewer 역할·비참여 선언·receipt scope.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 규범 우선순위·exact 승인 종류와 DENY 정책 IP `PH1 / PH2`·`IR_SESSION`: 실제 연결 세션에 적용되는 규범/manifest scope 일치; owner grant는 별도 기록 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH는 규범 우선순위와 종류 분리를, IR_SESSION은 실제 세션 귀속을 수용. unsigned JSON·해시를 외부 실명/서명으로 오인하지 않고 owner provenance 전달 경로를 별도 확정.

10. **무효화·철회:** 규범·승인·계획 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 기계 receipt를 신뢰해 읽는 host principal/저장소·시간 기준과 실제 owner provenance 전달 방법 미정.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR01.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR10, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR02 — artifact/tool 신원

**계획 분류: IMPLEMENTATION GAP — 수용 아님.**

1. **정확한 규범 요구:** runtime에 사용할 binary/source 대응과 APK/fixture/signing/source hash를 동결

   원 필수 증거: 실제 배포 binary 대응 근거 또는 해당 binary에 직접 적용되는 수명/selector 독립 proof; 봉인 bytes와 최종 manifest

2. **안전 보증:** 검토한 의미와 실제 소비 bytes가 같은 source/tool/APK/signer/fixture에 속함.

3. **위협/실패:** 경로 치환, hash만 같다는 주장, 설치 binary와 무관한 AOSP source, build 후 artifact 변동.

4. **현재 지원:** guards.SealedAPK와 구조 APK admission·독립 signer·기존 F03 종결. 근거: [scripts/devicegate/guards.py:157](../scripts/devicegate/guards.py:157), [scripts/devicegate/guards.py:178](../scripts/devicegate/guards.py:178), [scripts/devicegate/smoke.py:375](../scripts/devicegate/smoke.py:375), [mobile/android/app/build.gradle.kts:11](../mobile/android/app/build.gradle.kts:11), [docs/benchmarks/real-device-gate-prep10/installed-tool-and-artifact-review.json](benchmarks/real-device-gate-prep10/installed-tool-and-artifact-review.json).

5. **누락 집행:** 실제 ADB binary/source 대응, broker/OS 정책 동결과 phone용 최종 APK 적용성·전체 입력 봉인이 없음.

6. **필요한 구현 변경:** 도구 재빌드 provenance 또는 실제 고정 binary에 직접 적용되는 수명/selector proof 확보. source/tool/dependency/OS/정책/APK/fixture/명령 hash manifest와 immutable 소비 경로 설계. phone 호환 ABI/endpoint 최종 artifact는 별도 승인 범위에서만 생성.

7. **필요 증거/계측:** memfd seal/hash·동일 fd의 소비 bytes 관측; 원 F03 변형 fixture 유지. 최종 native engine ABI·signer·merged manifest·compiled resource; CP와 IP의 실제 실행 inode/FD 귀속.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 최종 source/tool/APK/signer/fixture·봉인 bytes 및 binary 의미 IP `PH1 / PH2`·`IR_SESSION`: 실제 host/tool/runtime과 전송할 봉인 bytes의 동결 신원 대조 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH가 최종 bytes와 binary 의미를 함께 수용하고 IR_SESSION이 실제 자원을 대조. 역사 APK 및 source hash만으로 phone 실행 적합성을 수용하지 않음.

10. **무효화·철회:** artifact/source/tool/서명/fixture/runtime 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 현재 보존 APK의 Flutter engine은 x86_64 이력이며 실제 phone ABI/OS는 관측하지 않음. AOSP 고정 revision과 Google 설치 binary 대응 UNVERIFIED.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR02.CP; post_execution: 없음. 계획상 결합 관계는 PR01, PR08, PR09, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR03 — 최초 등록과 bootstrap 결합

**계획 분류: ARCHITECTURAL BLOCKER — 수용 아님.**

1. **정확한 규범 요구:** owner-local P* 식별 근거를 실제 USB incarnation/원격 채널과 연결; 설치/marker 없이 완료

   원 필수 증거: 고정 등록 transcript·식별 필드의 화면/wire 대응 근거·실제 resource 연속성; 잘못된 유일 정상 단말 음성 대조·독립 승인

2. **안전 보증:** 첫 설치/marker 없이 승인 P*를 U*/C*·실제 receiver에 처음 결합.

3. **위협/실패:** 다른 정상 phone 하나만 연결된 wrong-singleton; serial/build 복제·설치 후 key로 소급 bootstrap.

4. **현재 지원:** 현재 serial/verify는 승인 emulator 문자열과 getprop를 검사하며 실제 authority는 거부. 근거: [scripts/devicegate/smoke.py:60](../scripts/devicegate/smoke.py:60), [scripts/devicegate/smoke.py:528](../scripts/devicegate/smoke.py:528), [docs/benchmarks/real-device-gate-prep09/f01-architectural-blocker.json](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json), [mobile/lib/main_devicegate.dart:33](../mobile/lib/main_devicegate.dart:33).

5. **누락 집행:** owner-local 독립 식별→실제 USB resource→원격 채널의 qualified 초기 binding 없음; crypto enrollment도 없음.

6. **필요한 구현 변경:** 연결 전 P* 식별 근거·고정 read-only transcript·화면/wire 대응 및 연결 연속성을 자격 심사. 기존 OS가 제공하는 설치 전 식별 수단의 실제 지원과 위협 모델을 입증할 때만 등록 경계 설계. 지원 불가면 BLOCKED 종료; 앱 key 설치·수동 설치·신뢰 서명으로 우회하지 않음.

7. **필요 증거/계측:** 개인 대상 없는 CP에서 동일 속성의 올바른/잘못된 두 비개인 fixture를 구별하는 근거. 미래 승인 PH1의 실제 P*/U*/C*/R* transcript, 독립 owner-local 대응, 설치/marker/launch=0 관측.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 설치/marker 없이 P*를 U*/C*에 결합할 qualified mechanism·독립 사전 식별·wrong-singleton 음성 근거 IP `PH1 / PH2`·`IR_SESSION`: 실제 P*/U*/C* 등록 transcript와 독립 식별 대응·연속성 수용 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH가 bootstrap 메커니즘과 wrong-singleton 거부를 PH0에서 먼저 수용하고, IR_SESSION이 실제 등록 후 PH2에서 대응을 수용. serial·물리 소유·케이블 통제·singleton만으로 불가.

10. **무효화·철회:** 신원 불일치·연결/receiver/server/channel 세대 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 현재 개인 단말의 설치 전 cryptographic identity나 검증 가능한 화면/wire field가 지원되는지 근거 없음. AS01–AS06은 아직 항목별 미수용이며 어떤 가정도 bootstrap proof 결측을 면제하지 못함.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR03.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR04, PR05, PR06, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR04 — USB incarnation 강제

**계획 분류: ARCHITECTURAL BLOCKER — 수용 아님.**

1. **정확한 규범 요구:** 새 장치/주소/major-minor 재사용·reset/재열거에서 새 열린 handle/대상을 얻지 못함

   원 필수 증거: 정확 kernel/backend/driver 접근 구조와 자원 수명 proof·격리 실험의 두 target 실제 effect 관측

2. **안전 보증:** 동일 U* 자원만 사용하며 새 열거/주소/major-minor 재사용으로 권한이 넘어가지 않음.

3. **위협/실패:** disconnect/reset 뒤 같은 node/주소의 다른 기기를 열거나 기존 transport를 새 USB handle에 재연결.

4. **현재 지원:** passive_usb는 관측만, require_host_confinement는 거부만 제공. 근거: [scripts/devicegate/smoke.py:80](../scripts/devicegate/smoke.py:80), [scripts/devicegate/smoke.py:97](../scripts/devicegate/smoke.py:97), [docs/benchmarks/real-device-gate-prep10/official-sources/client__usb_linux.cpp.txt](benchmarks/real-device-gate-prep10/official-sources/client__usb_linux.cpp.txt), [docs/benchmarks/real-device-gate-prep10/official-sources/client__usb_libusb.cpp.txt](benchmarks/real-device-gate-prep10/official-sources/client__usb_libusb.cpp.txt).

5. **누락 집행:** kernel/USB backend에 귀속된 incarnation 수명·재개방 불가·reset 폐기 primitive 미자격.

6. **필요한 구현 변경:** 정확 kernel/driver/native 또는 libusb backend의 열린 자원 수명과 reset/재열거 경로 분석. 자격 있는 one-incarnation 접근 경계와 새 device-open·FD 획득 차단 recipe 설계. major/minor allowlist·bind mount만으로 충족한다고 표시하지 않음.

7. **필요 증거/계측:** 정확 OS 정책/driver build/hash·원 자원 handle 수명. 독립 두 sink의 실제 effect·USB node 재사용/reset/재열거 8개 lab 시나리오.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 정확 OS/driver/backend의 USB incarnation/재열거·주소 재사용 강제 proof IP `PH1 / PH2`·`IR_SESSION`: 실제 U*·열린 USB 자원·OS recipe 적용과 새 incarnation 차단 확인 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH가 lifetime 논증과 실제 비개인 lab effect를 함께 수용. mock/emulator·단일 목록은 physical USB proof가 아님. IP에서는 실제 U*와 정책·열린 자원을 재대조.

10. **무효화·철회:** 단절/reset/재열거·OS 정책/driver/자원 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 현 host에서 지원할 강제 경계가 미검증; namespace 실패 이력은 있으나 privileged recipe의 보편적 불가능성 증거는 아님. 고정 USB fd의 모든 reset·재열거 동작을 현재 소스만으로 보장할 수 없음.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR04.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR03, PR05, PR06, PR07다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR05 — server/channel/transport 결합

**계획 분류: ARCHITECTURAL BLOCKER — 수용 아님.**

1. **정확한 규범 요구:** 점검한 server 세대가 실제 service channel의 server이고 ID 재사용·socket 교체·자동 restart/reexec 없음

   원 필수 증거: PID 숫자 외 process/resource lifetime 결합·실제 peer 연결/권한 경계·고정 binary의 no-fallback 분석

2. **안전 보증:** 검증한 S*와 실제 C* peer/T*/R*가 같고 재선택·교체·자동 server 수명 변경이 없음.

3. **위협/실패:** PID/port/TID 재사용, smart-socket 바꿔치기, client auto-start/reexec, TCP 객체 reconnect, 마지막 probe 뒤 수신자 변경.

4. **현재 지원:** process_generation/owned_tcp의 조회와 명시 -H/-P/-s/-t가 있으나 실제 service FD에 연결되지 않음. 근거: [scripts/devicegate/smoke.py:500](../scripts/devicegate/smoke.py:500), [scripts/devicegate/smoke.py:514](../scripts/devicegate/smoke.py:514), [scripts/devicegate/guards.py:42](../scripts/devicegate/guards.py:42), [docs/benchmarks/real-device-gate-prep10/official-sources/client__adb_client.cpp.txt](benchmarks/real-device-gate-prep10/official-sources/client__adb_client.cpp.txt).

5. **누락 집행:** 상호 검증된 실제 service-channel resource와 S*/U*/R*에 대한 지원 capability가 없음.

6. **필요한 구현 변경:** 매 action 새 CLI 대신 동일 server lifetime에 귀속한 최소 channel broker의 지원 가능성을 먼저 자격 심사. 실제 service peer·transport 객체·USB 자원·receiver boot/adbd 결합과 no-start/no-reexec/no-fallback을 binary·OS 수준에서 강제. 서비스가 바뀔 때 새 channel이 필요하면 사전 고정된 획득 규칙과 원 F01 결합을 다시 입증; 단일 getprop stream의 무제한 재사용 가정 금지.

7. **필요 증거/계측:** 실제 socket peer와 source-level resource lifecycle·선형화 지점, action별 bytes→receiver 관측. server/client 교체·same TID·TCP reconnect·concurrent action의 두 실제 sink 기록.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: actual server/channel 결합·no auto restart/reexec/fallback의 정확 binary/OS proof IP `PH1 / PH2`·`IR_SESSION`: 실제 S*/C*/T* peer/resource 수명과 승인 귀속 확인 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** 원 F01의 신원/동일 세대와 실제 mutation 수신자 결합을 IR_TECH/IR_SESSION이 명시 대조. -s/-t AND, pidfd만으로 socket 신원, one-device로 물리 인증을 주장하면 불수용.

10. **무효화·철회:** server/client/channel 교체·restart·disconnect/재선택; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 현재 stock 공개 CLI에 필요한 capability API는 확인되지 않음; 고정 binary 맞춤 proof가 필요한지 미해결. pidfd는 host process 수명에만 도움을 주며 실제 stream/USB/remote receiver를 자동 인증하지 않음.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR05.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR03, PR04, PR06, PR07, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR06 — OS 전면 매개와 우회 불가

**계획 분류: ARCHITECTURAL BLOCKER — 수용 아님.**

1. **정확한 규범 요구:** 허용 경계 밖 client/interpreter/후손/FD/다른 socket·TCP 목적지 접근 금지

   원 필수 증거: 전용 principal/정책의 정확 범위·효과 sink 목록·우회 음성 실험; 신뢰 root는 별도 가정

2. **안전 보증:** wrapper·후손·독립 client/server·FD·socket·TCP/mDNS를 포함한 모든 device effect sink를 OS가 매개.

3. **위협/실패:** 신뢰 wrapper 밖 process, 같은 UID ptrace/FD 유출, 상속 socket, 새 device node, 다른 server/TCP 경로.

4. **현재 지원:** FC01 중앙 Python 거부는 지원 네 모듈 경로에서 독립 종결; 호스트 전체 OS sandbox는 아님. 근거: [scripts/devicegate/dispatch.py:1](../scripts/devicegate/dispatch.py:1), [scripts/devicegate/smoke.py:80](../scripts/devicegate/smoke.py:80), [scripts/devicegate/test_prep08.py:70](../scripts/devicegate/test_prep08.py:70), [docs/real-device-gate-prep09-independent-dispatch-audit.md](archive/device-gate/history/real-device-gate-prep09-independent-dispatch-audit.md).

5. **누락 집행:** 전용 principal과 실제 적용된 device/network/mount/process 정책 및 탈출 불가 recipe 없음.

6. **필요한 구현 변경:** 권한 있는 설치 담당자와 비특권 executor 분리; 필요시 별도 비개인 host/VM recipe 하나만 선택. device 접근 deny-default, 새 incarnation 차단, 제한 mount/network/IPC, capability 제거·no_new_privs, ptrace/FD 전달/후손 탈출 통제의 정확 조합 자격 심사. 정책 적용 실패 시 모든 device 경로 거부; 중앙 거부 함수는 계속 유지.

7. **필요 증거/계측:** 정책 bytes/hash·kernel/LSM/cgroup backend·principal·namespace·허용 FD 집합. wrapper/interpreter/후손/SCM_RIGHTS·다른 socket/TCP/mDNS/USB 접근의 실제 음성 sink 관측.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: wrapper/후손/FD/socket/TCP/mDNS를 포함한 정확 OS 전면 매개 proof IP `PH1 / PH2`·`IR_SESSION`: 현재 principal/namespace/policy/FD·도달 집합의 recipe 일치 확인 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH가 실제 mandatory 정책 적용·자원 수명·우회 음성을 함께 수용. 신뢰 root는 별도 가정이며 Python AST tripwire·환경 변수·namespace 이름으로 대체 불가.

10. **무효화·철회:** principal/capability/정책/mount/FD 집합·감독 환경 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 현재 host의 권한·kernel/LSM/cgroup 지원·전용 principal·VM 실현 가능성 미검증. 정책만으로 기존 열린 FD와 진행 중 I/O가 어떤 시점에 차단되는지 별도 PR04/07 논증 필요.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR06.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR04, PR05, PR07, PR09다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR07 — 폐기·host 1회 시도·감독 수명

**계획 분류: ARCHITECTURAL BLOCKER — 수용 아님.**

1. **정확한 규범 요구:** 다른 대상 효과=0·무효화 뒤 새 제출/write/자원 취득=0·action별 시도<=1 및 host 자식 회수. 동일 action의 이미 제출된 작업은 G1-09 경계로 별도 UNKNOWN/격리 처분

   원 필수 증거: SUBMISSION_COMMIT/무효화 순서와 actual receiver/channel을 실제 sink·bytes·독립 자식/remote task 관측에 결합한다. RESERVED는 미전송이며 이미 받은 작업의 후속 완료와 새 제출을 분리한다. 순서/종료 미입증은 UNKNOWN_QUARANTINED; polling/host kill로 대체 불가.

2. **안전 보증:** 다른 target effect=0, 무효화 후 새 제출/write/자원 획득/버퍼 이동=0, host 시도<=1·자식 회수.

3. **위협/실패:** 지연 감시 사이 추가 write, RESERVED를 in-flight로 둔갑, 동시 중복 제출, host kill을 remote 종료로 오인.

4. **현재 지원:** target_revoked·취소 보호·pidfd/subreaper stop/reap의 N01 종결. run/start의 진입 거부로 현 노출 0. 근거: [scripts/devicegate/smoke.py:228](../scripts/devicegate/smoke.py:228), [scripts/devicegate/smoke.py:322](../scripts/devicegate/smoke.py:322), [scripts/devicegate/smoke.py:745](../scripts/devicegate/smoke.py:745), [scripts/devicegate/guards.py:251](../scripts/devicegate/guards.py:251), [scripts/devicegate/guards.py:302](../scripts/devicegate/guards.py:302), [docs/benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json](benchmarks/real-device-gate-g1-o3/pr07-g109-consistency.json).

5. **누락 집행:** 실제 무효화 사건과 실제 bytes sink에 동일 순서를 강제하는 primitive·durable action 소모·host crash supervisor 연계 없음.

6. **필요한 구현 변경:** authority/attempt/결과를 별도 상태로 관리; RESERVED와 실제 SUBMISSION_COMMIT 분리. 고정 action을 외부 제출 전에 한번 소모하고 crash 후 재시도 금지; owner 철회·disconnect 등을 실제 write 경계와 순서화하는 지원 enforcement 먼저 입증. N01 child 회수는 재사용하되 supervisor death/escaped child를 다루는 OS containment를 별도 자격 심사.

7. **필요 증거/계측:** 각 write의 bytes/offset/action/channel/receiver 귀속, invalidation 발생/관측/집행 시각 분리. 독립 host 자식 및 remote effect/task observer, O3 여섯 이력·T10 세 하위 이력·concurrent 시도.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 공통 제출 경계·다른 대상 효과=0·폐기 후 새 제출=0·1회 시도·자식 회수의 proof IP `PH1 / PH2`·`IR_SESSION`: 해당 session의 감독·폐기 enforcement가 무장됐고 예약/제출 사건과 현재 권한이 정확히 결합됨 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** O3 여섯 predicate와 S3 cutoff를 실제 sink로 입증. 늦게 감지해도 유예 없음. 순서/remote 종료 미입증은 UNKNOWN_QUARANTINED, 실제 늦은 write·오대상 effect는 FAIL_VIOLATION.

10. **무효화·철회:** 세대 변화·취소·deadline·감독/자식 회수/증거 실패; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** userspace lock/polling/후속 kill로 비동기 USB reset·외부 취소와 모든 I/O의 사건 순서를 강제할 수 없음. 필요한 지원 primitive가 없으면 별도 kernel/driver/adbd 변경 또는 새 architecture 결정이 필요하며 현재 계획은 구현을 승인하지 않음.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR07.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR03, PR04, PR05, PR06, PR08, PR10, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR08 — 앱 격리와 자동 재실행 방지

**계획 분류: IMPLEMENTATION GAP — 수용 아님.**

1. **정확한 규범 요구:** 별도 package/signer/private store/backup 제외·최소 권한; process 재생성/중복 intent의 시험 replay 금지

   원 필수 증거: 최종 APK admission과 fresh package 부재 검사·durable one-shot 필요성/구현 proof·명시한 앱 lifecycle

2. **안전 보증:** 독립 test UID/store/backup 제외와 논리 시험 최대 한 번; 앱 재생성·중복 intent는 effect를 재개하지 않음.

3. **위협/실패:** main 재진입으로 _smoke 재호출, duplicate intent·process death 뒤 자동 retry; 기존 package clear로 흔적 제거.

4. **현재 지원:** 별도 package/signer·최소 권한 manifest·backup/transfer 제외·private result 경로. main은 시작마다 _smoke를 호출. 근거: [mobile/lib/main_devicegate.dart:19](../mobile/lib/main_devicegate.dart:19), [mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt:9](../mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt:9), [mobile/android/app/src/devicegate/AndroidManifest.xml:16](../mobile/android/app/src/devicegate/AndroidManifest.xml:16), [mobile/android/app/build.gradle.kts:80](../mobile/android/app/build.gradle.kts:80).

5. **누락 집행:** durable one-shot claim과 claim-before-network/storage-effect 보장이 없고 최종 Android lifecycle 증거도 없음.

6. **필요한 구현 변경:** test-only native 경계에 plan/run/action별 durable consumed claim을 모든 합성 작업 전에 동기 확정. 동일 claim 존재·손상·I/O error·재생성은 실행 대신 거부/UNKNOWN; 결과 저장이 claim을 해제하지 않음. 최소 test app만 보강; 범용 원격 shell/상시 agent·특별 권한·암호 등록 엔진을 추가하지 않음.

7. **필요 증거/계측:** 최종 APK admission·native ABI·동기 저장 실패/claim 직전직후 death·task/프로세스/효과 counter. C4 여섯 lifecycle 시나리오를 최종 artifact에서 실제 Android로 확인; IP fresh package 부재는 설치 전 read-only로만.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 최종 APK 격리와 실제 Android 앱 lifecycle·중복 intent/process 재생성 replay=0; phone 적용성 근거 IP `PH1 / PH2`·`IR_SESSION`: 첫 설치 전 fresh test package 부재·OS/ABI/선정 APK 적용성; 설치된 앱 증거를 미리 요구하지 않음 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_ANDROID/IR_TECH가 최종 APK의 replay=0·durability·phone OS/ABI 적용성을 CP로 수용. singleTop/메모리 bool/호스트 one-attempt만으로 불가. 설치 뒤 새 checkpoint 수용 전 launch 금지.

10. **무효화·철회:** APK/signer/OS/lifecycle 정책 변경·replay·예상 밖 package 상태; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 동기 claim의 Android driver/VFS·I/O error 의미와 실제 phone OS 적용성이 미검증. 최종 universal APK로 emulator/phone 적용성을 함께 입증할지 비개인 동일 OS lab이 필요한지 선택 전.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR08.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR07, PR09, PR10, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR09 — 합성 backend·네트워크

**계획 분류: IMPLEMENTATION GAP — 수용 아님.**

1. **정확한 규범 요구:** phone 경로와 host egress가 exact synthetic origin/route에만 도달; redirect/production fallback 없음

   원 필수 증거: 검토한 phone-compatible endpoint 경로/종단 소유·예산·F02 범위 보존·비허용 sink hit=0

2. **안전 보증:** host·phone의 실제 egress와 종단이 exact synthetic origin/route에만 닿음.

3. **위협/실패:** 10.0.2.2를 phone 호환으로 오인, redirect/route 바꿔치기, hostname/proxy fallback 또는 운영 listener 도달.

4. **현재 지원:** host F02 SyntheticHTTP와 앱 origin/route/3xx 거부; backend는 새 합성 DB/loopback 18081. 근거: [scripts/devicegate/guards.py:72](../scripts/devicegate/guards.py:72), [scripts/devicegate/backend.py:12](../scripts/devicegate/backend.py:12), [mobile/lib/devicegate/isolation.dart:5](../mobile/lib/devicegate/isolation.dart:5), [mobile/android/app/build.gradle.kts:30](../mobile/android/app/build.gradle.kts:30), [mobile/android/app/src/devicegate/res/xml/devicegate_network_security_config.xml:1](../mobile/android/app/src/devicegate/res/xml/devicegate_network_security_config.xml:1).

5. **누락 집행:** 개인 phone 경로의 지원 설계·종단 소유/격리·host egress enforcement 없음.

6. **필요한 구현 변경:** phone-compatible 합성 경로 한 개를 연결 전에 정하고 host·Dart·Gradle·compiled network rule을 동일 exact origin에 맞춤. 전용 backend·환경/데이터/route 고정과 OS egress 차단; reverse/forward 등 추가 ADB 효과는 자동 채택하지 않고 별도 고정 허용 검토. 기존 host F02 의미와 tests 유지; 운영 endpoint 사용 금지.

7. **필요 증거/계측:** 고정 backend/listener/accepted socket의 실제 소유와 네트워크 경로·종단·namespace hash. redirect·origin·route·proxy·비허용 sink hit=0; 최종 Android 네트워크 실제 관측.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 합성 backend/host와 Android 경로·origin/route/redirect/egress의 정확 proof IP `PH1 / PH2`·`IR_SESSION`: 실제 backend/route/listener/namespace와 사전 검증한 경로의 귀속 확인 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH/IR_ANDROID는 실제 경로와 egress proof를 수용. host F02 종결을 phone 네트워크 proof로 전환하지 않고 CP/IP 종단 동일성을 확인.

10. **무효화·철회:** backend/route/namespace/종단/endpoint 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 현재 endpoint 10.0.2.2는 emulator 전용. Galaxy에서 안전한 exact route 및 별도 host 정책 미정. 선택 경로가 host/phone 네트워크 설정 변경·새 mutation을 필요로 하면 범위 승인이 별도로 필요.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR09.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR06, PR08, PR10, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR10 — 자원·증거·UNKNOWN 처분

**계획 분류: IMPLEMENTATION GAP — 수용 아님.**

1. **정확한 규범 요구:** 고정 deadline/bytes/용량과 bounded journal; 원격 지속/증거 부족을 성공이나 retry로 바꾸지 않음

   원 필수 증거: 수신 전후 ledger·partial/oversize/log failure·timeout의 결과; 보장 가능한 경계와 soft limit 구분

2. **안전 보증:** 한도·증거를 초과하거나 결과가 불명확하면 성공/재시도 없이 격리.

3. **위협/실패:** 로그 polling 사이 초과·journal 실패 뒤 계속 실행·host exit0로 remote commit 확정·ACK로 권한 복구.

4. **현재 지원:** run의 timeout/output polling·backend RLIMIT_FSIZE·응답 byte 제한·짧은 결과 파일 상한. 근거: [scripts/devicegate/smoke.py:228](../scripts/devicegate/smoke.py:228), [scripts/devicegate/smoke.py:500](../scripts/devicegate/smoke.py:500), [scripts/devicegate/backend.py:35](../scripts/devicegate/backend.py:35), [mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt:21](../mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt:21).

5. **누락 집행:** 전체 bounded durable journal·증거 예약·실제 hard/soft 범위 분리 및 UNKNOWN/remote task 상태가 없음.

6. **필요한 구현 변경:** 사전 고정 전체/단계 deadline·bytes·파일 수·여유·evidence 한도와 별도 action/remote/host 결과 schema. bounded journal 저장 실패 전에 새 제출을 차단하는 구조; crash 후 authority 복구 없음. 실제 hard limit(예: 봉인 입력 크기·허용 요청 수)과 감시 기반 timeout·공유 자원 soft limit를 구분.

7. **필요 증거/계측:** partial write/short read/oversize/ENOSPC/EIO/timeout·journal fault injection과 실제 submitted/ACK/task 상태 ledger. CP 정책 수용과 IP 현재 여유·종단·시간/bytes 귀속; POST는 확보 증거만 독립 분류.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 정책·시간/bytes/여유 hard/soft 한계·journal/UNKNOWN·격리 처분 proof IP `PH1 / PH2`·`IR_SESSION`: 현재 세션의 여유/예산/증거 저장과 deadline/remote 한계 확인 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH는 실제 보장 한계와 evidence failure 거부를, IR_SESSION은 현재 예산을, IR_EVIDENCE는 이력을 수용. 결측은 성공 아님; remote 종료 미입증은 UNKNOWN_QUARANTINED.

10. **무효화·철회:** 한도 초과·증거/응답 실패·시간 초과·무효화 사건; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** phone CPU/열/배터리·PM 설치 작업의 hard stop/용량 보증을 현재 API로 수용할 수 없음. host filesystem 예약·durable append와 실패 시 정보 보존 경계 미정.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR10.CP; post_execution: 없음. 계획상 결합 관계는 PR02, PR06, PR07, PR08, PR09, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR11 — 명령·효과 allowlist 완결성

**계획 분류: IMPLEMENTATION GAP — 수용 아님.**

1. **정확한 규범 요구:** 연결 전 실제 literal argv/input/path/semantic effect/순서 동결; 동적 명령 생성 없음

   원 필수 증거: action별 승인 source와 artifact·필수 OS bookkeeping·고정 결과 수집 횟수·cleanup 제외 명세

2. **안전 보증:** 연결 전 승인한 literal action/bytes/경로/효과/순서만 1회 실행.

3. **위협/실패:** 연결 후 명령 생성·반복 readback·기존 package 탐색/clear/uninstall·동적 경로·adaptive cleanup.

4. **현재 지원:** 고정 package/component 상수, 봉인 APK bytes와 앱/HTTP allowlist 일부 존재. 근거: [scripts/devicegate/smoke.py:460](../scripts/devicegate/smoke.py:460), [scripts/devicegate/smoke.py:618](../scripts/devicegate/smoke.py:618), [scripts/devicegate/smoke.py:639](../scripts/devicegate/smoke.py:639), [scripts/devicegate/smoke.py:688](../scripts/devicegate/smoke.py:688), [scripts/devicegate/guards.py:20](../scripts/devicegate/guards.py:20).

5. **누락 집행:** 전체 action manifest 동결·허용 slot·효과·증거 횟수·cleanup 제외 검증이 없음. 기존 application/finish는 emulator 전용 반복/삭제 경로.

6. **필요한 구현 변경:** 순수 host manifest validator로 literal argv/input digests/경로/순서/예산/효과·권한 종류를 검증. 향후 executor가 동결된 action만 소비하도록 분리; 현재 application/finish를 개인 phone 경로로 재사용하지 않음. live 값은 사전 정의 resource generation slot만 허용; target serial/OS/build/계획 공란은 DENY.

7. **필요 증거/계측:** 연결 전 action별 actual bytes·artifact/source·예산·수집 횟수·OS bookkeeping 목록. unexpected shell/parser/source/경로/bytes·중복 ordinal·임의 slot·cleanup/retry 주입을 실제 경계에서 거부.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: 등록/설치/시작/수집의 literal action/bytes/경로/순서·효과·예산 완결성 IP `PH1 / PH2`·`IR_SESSION`: 실제 등록 session과 next action의 immutable manifest 대조; live 값은 사전 정의 slot만 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH가 등록/설치/launch/결과 수집과 부수 OS 효과의 완결성을 수용. IR_SESSION은 동결 plan과 ordinal만 대조하며 새 명령/정체성 공란을 채우지 않음.

10. **무효화·철회:** plan/argv/bytes/source/경로/예산 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 최종 설치/수집 경로와 backend·OS 경계가 미정이므로 operational literal manifest를 지금 완성할 수 없음. read-only 등록도 0 effect라고 포괄 주장하지 않으며 OS bookkeeping 범위를 먼저 선언해야 함.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: 없음; connected_instance: PR11.CP; post_execution: 없음. 계획상 결합 관계는 PR01, PR02, PR03, PR05, PR06, PR07, PR08, PR09, PR10다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

### PR12 — 독립 통합 수용

**계획 분류: INSUFFICIENT SOURCE EVIDENCE — 수용 아님.**

1. **정확한 규범 요구:** PR02–PR11의 동일 artifact/OS recipe에서의 수용·N01/F02/F03/FC01 보존; 문서/모형/OS/phone proof 범위 구분

   원 필수 증거: 비참여 reviewer 선언·정확 source/fixture/tool/OS/runtime/effect 관측 hash·한계/미결정·명시 reviewer verdict

2. **안전 보증:** 같은 artifact/OS/세션에 귀속한 11개 증거를 비참여자가 통합 수용하고 기존 종결을 보존.

3. **위협/실패:** 자체 PASS·mock·emulator 결과를 OS/physical proof로 합산하거나 CP/IP/owner grant를 대체.

4. **현재 지원:** PREP09 독립 종결·N3/N5 문서 적용·주석 독립 검토와 고정 source locks. 현재 기술 receipt는 0. 근거: [docs/benchmarks/real-device-gate-prep09/next-action-decision.json](benchmarks/real-device-gate-prep09/next-action-decision.json), [docs/benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json](benchmarks/real-device-gate-g1-o2/proof-phase-and-acceptance-matrix.json), [docs/benchmarks/real-device-gate-g1-n5-consistency/postapplication-result.json](benchmarks/real-device-gate-g1-n5-consistency/postapplication-result.json).

5. **누락 집행:** 실제 구현 후보/OS recipe/최종 APK의 qualified 증거·비참여 기술 수용 receipt가 없음.

6. **필요한 구현 변경:** proof facet/범위별 receipt schema·원 source/artifact/OS 대응 dossier 준비. PR01–11 각각의 CP/IP/POST 후 PR12 통합을 별도로 판정; 자기 receipt를 선행조건으로 삼지 않음. 계획 작성자·구현자·측정 참여자는 해당 통합 독립 수용 역할을 맡지 않음.

7. **필요 증거/계측:** source/runtime/artifact/OS/fixture/effect 관측 hash, reviewer 비참여 선언·수용 범위·잔여 미결정. 원 F01 binding의 PR03–07 CP/IP 대조와 N01/F02/F03/FC01 source·역사 증거 보존.

8. **수집·수용 phase:** CP `PH0 / PH0`·`IR_TECH`: PR01–PR11의 CP 증거·source/runtime/OS 대응과 기존 종결 보존의 독립 통합 수용 IP `PH1 / PH2`·`IR_SESSION`: PR01–PR11 IP와 CP 보존·등록 후 보충 증거를 독립 통합 수용; 자신을 선행조건으로 삼지 않음 POST `PH4 / PH5`·`IR_EVIDENCE`: 실제 action/무효화/결과/증거를 동결 source/runtime/OS/session에 귀속하여 해당 의무의 이행/위반/UNKNOWN 판정

9. **독립 수용 조건:** IR_TECH는 모든 CP와 물리 적용성을 PH0에서 통합 수용, IR_SESSION은 모든 IP를 PH2에서 통합 수용, IR_EVIDENCE는 POST만 PH5에서 판정. 어느 것도 owner grant 아님.

10. **무효화·철회:** 필수 proof/identity/독립성 결측·대응 source/OS/runtime 변경; S3/G1-06의 공통 사건은 진행 중에도 단방향 REVOKED. 늦은 ACK·동일 이름 재등장·POST로 복구 금지.

11. **남은 불확실성:** 검토자·최종 runtime·기기 적용성 증거가 미지정; 현재 저자의 계획 평가로 기술 수용을 발급할 수 없음.

12. **의존성:** 원 facet의 명시 의존성은 offline_mechanism: PR01.CP, PR02.CP, PR03.CP, PR04.CP, PR05.CP, PR06.CP, PR07.CP, PR08.CP, PR09.CP, PR10.CP, PR11.CP; connected_instance: PR01.IP, PR02.IP, PR03.IP, PR04.IP, PR05.IP, PR06.IP, PR07.IP, PR08.IP, PR09.IP, PR10.IP, PR11.IP; post_execution: PR01.POST, PR02.POST, PR03.POST, PR04.POST, PR05.POST, PR06.POST, PR07.POST, PR08.POST, PR09.POST, PR10.POST, PR11.POST. 계획상 결합 관계는 PR01, PR02, PR03, PR04, PR05, PR06, PR07, PR08, PR09, PR10, PR11다. 후자는 새 규범 선행조건을 제정한 목록이 아니다.

PR12 CP/IP는 PR01–11 각 facet 수용 뒤 통합한다. 자기 수용을 선행조건으로 삼지 않는다. 최초 설치의 PR08 IP가 설치된 앱 receipt를 미리 요구해서도 안 된다. 설치 전 fresh package 부재·선정 APK 적용성을 확인하고, 승인 설치 뒤 실제 package/signer/bytes·start 전 필요한 새 증거는 사전 고정 read-only checkpoint와 IR_SESSION 보충 수용을 거친다. 결과가 UNKNOWN이면 다음 launch는 금지다.

## 7. 유한 기술 검증 캠페인

아래는 제안 한도와 후속 승인 단위다. **Stage1 구현, Stage2 mock/OS 검증, C2 lab, C3 emulator, Stage4 app/interruption, Stage5 기술 수용, Stage6 물리 접근은 모두 NOT AUTHORIZED**다. 현재 Stage0의 source 대조와 Stage3 형식의 제안 문서만 작성했으며 독립 기술 qualification이나 캠페인 실행은 하지 않았다. 앞 단계의 결과가 다음 실행을 자동 승인하지 않는다.

### Stage 0 — Source·위협 모델 자격 심사

- **진입:** 현 canonical SHA 검증, 상위 B/C·원 F01·PREP09/10·N3/N5·주석 후속 사건·source locks 확인. 현재 P01은 저자 계획 작성만. 시간/용량 상한은 제안이며 현재 소유자 실행 승인 아님.
- **최대 범위:** {"source_candidates": 1, "architecture_reviews": 1, "seconds_max": 7200, "evidence_bytes_max": 10485760}
- **필수 증거:** 12/12/14 추출·36 facet·원 F01/3보호 대조와 actual source catalog. bootstrap·resource/I/O lifetime·OS recipe·AS01–06 미수용·원 반례의 gap register.
- **통과:** 전체 G1 경로는 qualified 메커니즘 부재 시 BLOCKED. 문서 해시/정합성 확인과 FS1의 순수 범위 식별은 별도 계획 결과로 기록하며 CP 수용하지 않음.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** 비참여 IR_DOC/IR_TECH가 원 source/규범을 직접 대조해야 다음 기술 심사로 넘김. P01 저자는 독립 수용자가 아님.
- **중단:** S7/hash/상위 충돌·필수 mechanism 결측이면 full 경로 중단; 현재 PR03–07에 해당.
- **금지:** 기기 enumeration/ADB help 포함·OS 설정 변경·emulator·구현·proof 수용·계약 변경 금지.
- **원 단계 대응:** A, PH0.

### Stage 1 — Host-only enforcement 구현

- **진입:** 전체 구현은 Stage0 blocker의 별도 해결·정확 구현 승인이 필요. 이와 분리해 FS1만 2파일 범위의 별도 승인 후 수행 가능하며 전체 경로를 진행시키지 않음.
- **최대 범위:** {"candidates": 1, "first_slice_ref": "first-host-only-slice.json", "source_files_max": 2, "added_lines_max": 240, "implementation_seconds_proposed_max": 7200, "evidence_bytes_max": 10485760}
- **필수 증거:** FS1 candidate/diff stat·before/after source hash·고정 test corpus·scope receipt. dispatch/confinement 무조건 거부와 기존 HTTP/APK/child 함수 보존.
- **통과:** FS1의 순수 검증 데이터만 생성, 운영 caller/IO/권한 전이 0. M2/M3 전체 enforcement 구현이 완료됐다는 주장을 하지 않음.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** 비참여 reviewer가 실제 2파일 변경과 모든 기존 함수 보존·새 effect 경로 부재 검토. 전문 기술 CP 수용과 별개.
- **중단:** 기존 거부 변경·새 I/O/OS/Android·범위 확대 필요 또는 구현 시간/행/bytes 초과.
- **금지:** ADB·Android build/실행·OS 정책 부착·실기기 등록·운영 source grant/환경 bypass·B03 변경 금지.
- **원 단계 대응:** B, PH0.

### Stage 2 — Host-only adversarial tests

- **진입:** 정확 FS1 구현/test 범위 별도 승인. 전체 C1 모형 캠페인은 M2/M3 설계 자격과 별도 mock 승인 없으면 미착수. 실제 USB/OS C2 lab를 host mock 승인에 포함하지 않음.
- **최대 범위:** {"FS1_cases": 24, "FS1_seconds_max": 300, "FS1_evidence_bytes_max": 10485760, "C1_models_max": 1, "C1_trace_ids_max": 12, "C1_fixed_histories_max": 14, "C1_seconds_max": 3600, "C1_evidence_bytes_max": 10485760, "automatic_retries": 0}
- **필수 증거:** FS1 sink=0/거부 경계·24개 raw 결과. 별도 C1 승인 시 T01–T12와 T10 3하위 이력; 두 in-memory effect sink·무효화/제출 event 기록.
- **통과:** 기대 음성은 실제 DENY/격리 관측만 PASS. 모형의 가정과 미구현 OS/채널 보증을 명시. mock PASS로 C2/CP를 완성하지 않음.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** 모형 작성/구현/측정 비참여 IR_TECH가 두 sink·원 반례·추가 호출 누락 여부 직접 심사.
- **중단:** 의도하지 않은 effect·새 write·중복·source drift·실패·한도 초과 시 캠페인 종료.
- **금지:** live socket·USB enumeration/장치·ADB·emulator·기존 경계 patch·자동 retry 금지.
- **원 단계 대응:** C1, PH0.

### Stage 3 — 독립 심사를 받는 emulator 검증 제안

- **진입:** Stage0의 M2 qualified mechanism 후보와 정확 source/tool/최종 APK/OS recipe·lab 자격안이 있어야 실행 제안을 심사. 현재는 제안 문서만 만들 수 있으며 C2/C3 실행은 NOT AUTHORIZED.
- **최대 범위:** {"proposal_candidates": 1, "independent_proposal_reviews": 1, "proposal_seconds_max": 7200, "proposal_evidence_bytes_max": 10485760, "C2_if_separately_approved_exact_ceiling": {"recipes": 1, "scenarios": 8, "seconds": 5400, "evidence_bytes": 20971520}, "C3_if_separately_approved_exact_ceiling": {"fixtures": 4, "scenarios": 4, "seconds": 1800, "evidence_bytes": 20971520}, "automatic_retries": 0}
- **필수 증거:** C2의 실제 OS/USB·driver 자원 수명 1recipe/8음성·두 target sink 제안; 개인/Android 대상을 첫 lab로 쓰지 않음. C3 정상/단절/server restart/same-serial replacement 4개 fresh fixture 제안, USB 접근 배제·owned QEMU/channel 연결 근거. 정확 관측 계층·sink/bytes/remote task oracle·증거 저장·종료/격리·허가 범위.
- **통과:** 제안 review PASS는 실행 허가 아님. 실제 C2 별도 승인·수용 및 C3 안전 경로가 없으면 emulator 실행안도 BLOCKED. C2를 mock/emulator로 대체 금지.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** 비참여 IR_TECH가 C2·격리/채널 계획을, IR_ANDROID가 C3 actual Android 제안을 심사. 이후 별도 owner lab/emulator 승인 필요.
- **중단:** bootstrap/USB/I/O primitive·물리 적용성 또는 qualified emulator 경로 불명확이면 미실행 종료.
- **금지:** P01에서 emulator start/ADB·OS device policy 변경·실제 lab/device 접근·APK 설치 금지. physical USB/개인 P* identity를 emulator로 입증했다는 주장 금지.
- **원 단계 대응:** C2, C3, PH0.

### Stage 4 — Application lifecycle·interruption 검증

- **진입:** 별도 C2/C3 실행 승인·수용이 실제 존재하고 동일 최종 APK/OS 적용성·M4 one-shot가 동결된 경우에만, 별도 app/interruption 승인 후 실행. 현재 NOT AUTHORIZED.
- **최대 범위:** {"C4_exact_ceiling": {"fixtures": 6, "scenarios": 6, "seconds": 2700, "evidence_bytes": 20971520}, "C5_exact_ceiling": {"fixtures": 6, "scenarios": 6, "seconds": 2700, "evidence_bytes": 20971520}, "automatic_retries": 0}
- **필수 증거:** C4: normal·duplicate intent·process recreation·durable claim 후 death·partial task death·completion 후 restart 6개 fresh fixture. C5: 제출 전 취소·예약 후 미제출 취소·수신 후 ACK 유실·ACK 후 task 지속·host/supervisor death·guest/adbd 중단 6개 fresh fixture. 사전 무장한 독립 observer의 실제 Android task/effect·native durable claim·bytes/ACK·host 자식·quarantine·I/O 실패.
- **통과:** 각 논리 시험<=1·replay0, 다른 target effect0·폐기후 새 제출/write/자원/버퍼 이전0. host reap과 remote 종료를 별도로 판정; 미확정은 UNKNOWN, 실제 위반은 FAIL.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** IR_ANDROID 및 IR_TECH 모두 구현/fixture/측정 비참여. 최종 APK 실제 lifecycle와 phone OS/ABI 적용성 범위를 명시.
- **중단:** case 실패/증거 결측·한도 초과 시 BLOCKED/REJECTED. 의도적 음성 fixture는 격리 종료하며 동일 fixture 복구 금지.
- **금지:** 개인 phone을 첫 lifecycle 검증 장소로 쓰기·전원 차단/재부팅·revoked fixture에 새 ADB readback/cleanup·다른 APK로 PASS 승계 금지.
- **원 단계 대응:** C4, C5, PH0.

### Stage 5 — 독립 proof qualification

- **진입:** 정확 A–C5 dossier·개별 PR01–11.CP·기존 종결 보존·최종 artifact/OS/physical 적용성 증거가 모두 준비되고 별도 심사 범위 승인. 현재 NOT AUTHORIZED.
- **최대 범위:** {"decisions_max": 1, "seconds_max": 7200, "evidence_bytes_max": 52428800, "automatic_reaudits": 0}
- **필수 증거:** 12개 CP receipt의 source/tool/runtime/artifact/OS 대응·effect 관측·비참여 선언·유효기한/폐기 상태. PR03–07/12의 원 F01 신원/채널 binding 대조와 세 보호, N01/F02/F03/FC01 source·역사 증거.
- **통과:** PR01–11 CP 개별 수용 뒤 PR12 CP 통합. 하나라도 미입증이면 CP_ALL_ACCEPTED 불가·연결 DENY. CP 수용도 owner grant 아님.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** IR_TECH는 이 설계/구현/fixture/실행·측정에 참여하지 않은 지정 심사자. Android 전문 심사 자료 필요; 문서 저자 self-review 불가.
- **중단:** 현재 5개 architectural blocker·미수용 AS 또는 최종 Android 적용성 결측을 해소하지 못하면 이 단계 착수/수용 불가.
- **금지:** 서명된 residual risk waiver로 proof 결측 면제·모형/증거 수집/machine PASS를 수용으로 승격·IP/POST 소급 생성 금지.
- **원 단계 대응:** D, PH0.

### Stage 6 — 물리 기기 접근에 대한 별도 owner 결정

- **진입:** 모든 CP와 D 수용·사전 exact P* 신원/OS/build·manifest/등록 allowlist/한도·qualified confinement·미해결 quarantine 없음. 현재 전부 미충족.
- **최대 범위:** {"owner_connection_decisions_max": 1, "sessions_max": 1, "automatic_retries": 0, "proposed_physical_followup_ceiling_only": {"shared_E1_E3_seconds_max": 600, "shared_E1_E3_evidence_bytes_max": 10485760}, "actual_physical_budget": "NOT_SET_NOT_AUTHORIZED"}
- **필수 증거:** owner 연결/read-only grant 또는 DENY의 exact 범위·근거·hash. grant 뒤 별도 E1 수집/E2 독립 IP 수용/E3 owner 첫 mutation 순서가 필요하다는 명시.
- **통과:** owner가 연결/read-only만 별도 승인한 경우에도 mutation=0. 이 단계는 실제 개인 기기 실행·설치를 수행하지 않는다. 무응답·유효기간 초과는 승인 아님.
- **실패:** 필수 근거/귀속/독립성 결측·안전 위반·한도 초과는 FAIL/INCONCLUSIVE; 다음 단계 자동 진행 금지.
- **독립 reviewer:** IR_SESSION은 연결 전 CP/manifest/owner scope와 이후 실제 E1/E2의 다른 역할임을 확인. owner와 독립 수용자는 분리.
- **중단:** CP 미수용·신원/계획 공란·기한 초과·미해결 quarantine이면 owner 결정용 실행안을 DENY로 반환.
- **금지:** 기기 연결/ADB/설치/marker/launch 자동 시작·IP 없이 첫 mutation·운영 18080·T6.9/R1/production 활성화 금지.
- **원 단계 대응:** E0, PH0_TO_PH1.

원 유한 계획의 C1은 T01–T12 **12개 ID·14개 이력**이며 T10의 제출 전 취소/RESERVED 후 미제출 취소/수신 후 ACK 유실·취소 뒤 완료를 각각 고정한다. C2는 **1 recipe·8 시나리오·5,400초·20MiB**, C3는 **4 fixture·4 시나리오·1,800초·20MiB**, C4/C5는 각각 **6 fixture·6 시나리오·2,700초·20MiB** 상한을 보존했다. 각 case는 한 번이며 예상한 DENY/UNKNOWN이 실제 기준대로 관측된 경우만 시나리오 PASS다. 실제 결측·위반·timeout을 고치며 자동 반복하는 캠페인이 아니다.

C2의 실제 host OS/USB resource 수명과 두 target effect 증거는 필수다. Stage2의 host mock으로 대체하지 않는다. Stage3에서 별도 비개인 lab 제안을 심사하고, C2의 별도 실행 승인·실제 증거·독립 수용 전에는 C3 실행/Stage4/Stage5로 넘어갈 수 없다. 개인 phone을 첫 lab로 사용하지 않는다. emulator 결과는 physical USB 격리·개인 P* 식별 proof가 아니다. 같은 source의 다른 ABI/OS라는 사실만으로 최종 APK의 phone 적용성을 수용하지 않는다.

Stage5는 D의 **1결정·7,200초·50MiB** 안에서 모든 CP를 별도로 수용하거나 BLOCKED/REJECTED로 종료한다. Stage6은 E0의 owner 연결/read-only 결정만 준비한다. 연결 실행 자체는 이후 별도 범위다. E1의 고정 read-only 등록 → E2의 모든 실제 IP 독립 수용 → E3의 owner 첫 mutation grant → 고정 후속 checkpoint → 분리 후 E4/PH5 POST의 순서를 보존한다. E1–E3 공동 **600초/10MiB는 제안 상한**이며 실제 field/action별 예산은 owner가 별도로 exact로 고정해야 한다. 연결 후 심사/owner 응답 대기도 같은 상한 안이고 무응답은 승인도 연장도 아니다. E4는 확보된 증거의 사후 처분이며 소급 실행 허가를 만들지 않는다. [모든 원 단계 한도·12 trace·E1–E4 보존](benchmarks/real-device-gate-g1-p01/finite-validation-campaign.json).

## 8. 정확히 하나의 첫 호스트 전용 구현 slice

**FS1 — 실행 권한을 만들지 않는 동결 action manifest의 순수 byte 검증기. 현재 구현 NOT AUTHORIZED.** 두 기존 파일만 별도 구현 승인 대상으로 제출할 수 있다.

| 파일 | 허용할 변경 |
| --- | --- |
| [scripts/devicegate/guards.py](../scripts/devicegate/guards.py) | 새 순수 parser·immutable 반환 형식만 추가; 기존 HTTP/APK/자식 감독 함수의 본문·동작 보존 |
| [scripts/devicegate/test_safety.py](../scripts/devicegate/test_safety.py) | 새 순수 시험 class·in-memory fixture만 추가; 기존 test/assertion/fixture 보존 |

최대 2개 기존 파일·추가 240행(parser 100/test 140)·새 runtime 파일 0·후보 1개·고정 case 24개다. 구현 제안 상한 7,200초, 선택한 새 class 시험 300초/증거 10MiB이며 자동 재시도는 0이다. 새 caller·운영 통합·dispatch/confinement 변경·subprocess/socket/USB/OS/Android 실행·device registration은 포함하지 않는다. `dispatch.py`의 무조건 거부 hash와 기존 거부 함수의 bytes/AST를 보존해야 한다.

입력은 caller가 준 UTF-8 bytes와 expected digest뿐이다. 원본 byte hash·정확한 계약 신원·사전 target identity·source/tool/APK/signer/fixture 참조·literal argv/input/경로/효과/수집 횟수·action 순서·budget·허용 generation slot 구조를 검증한다. raw bytes 64KiB·깊이16·action32는 **FS1 제안 한도**이며 G1 실세션 값이 아니다. JSON duplicate key/non-finite·잘못된 type/UTF-8·공란·임의 command interpolation·동적 source를 거부한다. 미래 U*/C* 실측값이 없다는 이유로 CP 계획 검사를 막지는 않는다. 원 PREP01의 29개 freeze 필드는 [FS1 JSON](benchmarks/real-device-gate-g1-p01/first-host-only-slice.json)에 원문으로 포함한다. 합성 PLAN_ONLY 구조 검사를 실제 approved manifest나 공란 허용으로 전환하지 않는다.

FS1은 PLAN_ONLY/NOT_GRANTED/NOT_ACCEPTED만 다룬다. owner grant·self-asserted acceptance·aggregate boolean을 입력으로 줘도 실행 권한이나 독립 receipt로 바꾸지 않는다. 반환은 immutable 계획 데이터/형식 진단뿐이며 ALLOW·grant·token·자원 capability가 없다. 선언한 semantic effect의 실제 완결성·owner provenance 인증·OS/channel binding은 후속 별도 proof다. 이 한계를 구조 검사 PASS가 숨기지 않게 한다.

- **FS1-T01**: 동일한 유효 synthetic PLAN_ONLY bytes를 두 번 파싱해 동일 digest/immutable 내용을 얻되 authority는 NOT_GRANTED 유지.
- **FS1-T02**: expected plan digest와 실제 raw bytes가 한 byte라도 다르면 거부.
- **FS1-T03**: 현 canonical 계약 hash와 다른 값/O2 proposal의 authority 대체를 거부.
- **FS1-T04**: 필수 사전 target identity가 누락/null/공백이면 거부; 미래 U*/C* 값 부재를 선행 요구하지 않음.
- **FS1-T05**: 필수 source/tool/APK/signer/fixture 참조 중 하나라도 없거나 hash/길이 type이 틀리면 거부.
- **FS1-T06**: JSON duplicate key와 non-finite 숫자를 거부.
- **FS1-T07**: 잘못된 UTF-8/비정상 JSON/지원하지 않는 schema version을 거부.
- **FS1-T08**: 64KiB·depth16·action32 제안 경계와 각각 +1을 검사해 초과는 거부.
- **FS1-T09**: argv/string/bytes length에 bool/int/string을 혼용하거나 누락하면 거부.
- **FS1-T10**: 중복/역순/건너뛴 action ordinal과 duplicate action ID를 거부.
- **FS1-T11**: 사전 고정 source/bytes digest·경로·예산 하나를 바꾼 계획은 원 기대 hash에서 거부.
- **FS1-T12**: 상대경로 traversal·허용되지 않은 절대경로/공유 저장소·production package 참조를 거부.
- **FS1-T13**: 미정 action input·component·effect/OS bookkeeping 선언·수집 횟수의 누락을 거부.
- **FS1-T14**: 사전 선언 generation slot 외 임의 live slot/command interpolation을 거부.
- **FS1-T15**: shell script/interpreter fallback·동적 명령·임의 callback/opcode 필드 주입을 거부.
- **FS1-T16**: retry/clear/uninstall/광역 수집을 숨기는 미승인 action kind를 거부; declared effect의 실제 의미 proof는 별도임을 반환 진단에 유지.
- **FS1-T17**: deadline/bytes/용량/최대 횟수가 공란·음수·0·비정수이면 거부. 실제 session 예산을 자동 생성하지 않음.
- **FS1-T18**: CP/IP/POST 집계 boolean 또는 self-asserted accepted 상태를 독립 receipt로 취급하지 않고 거부.
- **FS1-T19**: owner grant/INDEPENDENTLY_ACCEPTED/AUTHORITY_GRANTED를 FS1 입력으로 주어도 거부.
- **FS1-T20**: 반환 계획/하위 배열을 바꾸려는 시도는 불가하며 원 입력 객체 변경이 파싱 결과에 영향 없음.
- **FS1-T21**: 실패·재호출·동시 두 parser 호출도 grant 상태나 effect sink를 만들지 않음.
- **FS1-T22**: 검증 중 subprocess·network·file-open·환경/clock/USB 조회 sink를 호출하면 test가 실패; parser 경로에서 실제 sink 호출 수 0.
- **FS1-T23**: dispatch.spawn_process 및 smoke require_host_confinement의 기존 거부 AST/함수 bytes와 source hash를 대조; 새 활성화 분기 없음.
- **FS1-T24**: 기존 함수·기존 test 본문 보존, 두 파일 외 source/index/역사 자료 drift 0과 새 parser의 운영 caller 0을 정적 확인.

새 class만 명시 선택하여 시험하고 운영 경계를 patch하지 않는다. 기존 CLI/합성 자식 adapter suite를 자동 선택하지 않는다. 검사 중 금지 I/O sink에 도달하면 실제 실행 전에 실패시킨다. 기존 함수/시험 본문 보존과 운영 caller 0을 함께 검토한다. 추가만 해도 전체 모듈 hash는 새 candidate 신원이다. 과거 source lock·독립 수용 증거를 갱신하거나 새 source로 자동 이전하지 않고, 변경 영향과 적용성 검토를 새 후보에 따로 귀속한다. 구현/fixture/측정 비참여자가 실제 변경을 검토해야 하며 24개 통과도 PR 수용이나 기기 권한이 아니다. 한도/순수 함수 경계를 넘기거나 기존 거부를 바꿔야 한다면 중단한다. [정확한 범위·before hash·24개 수용 시험](benchmarks/real-device-gate-g1-p01/first-host-only-slice.json).

FS1은 PR01/02/10/11의 CP 준비 자료를 제공한다. PR03 초기 P* 등록, PR04 USB incarnation, PR05 actual channel, PR06 OS 격리, PR07 사건 cutoff, PR08 실제 lifecycle, PR12 독립 수용은 해결하지 않는다. 이를 전체 G1의 READY로 표현하지 않는다.

## 9. 남는 차단 사유와 종료점

- **BL01 · ARCHITECTURAL BLOCKER · PR03, PR12**: 설치 전 P*의 owner-local 식별을 actual U*/C*/R*로 결합할 qualified mechanism 없음. 필요한 해결: 하나의 설치 없는 식별 mechanism·지원 근거·wrong-singleton 거부·화면/wire/자원 연속성 논증. 없으면 BLOCKED 종료. 인정하지 않는 대체: serial/기기1개/케이블 소유/사후 앱 key/위험 수용.

- **BL02 · ARCHITECTURAL BLOCKER · PR04, PR05, PR12**: 실제 command channel과 검증 server/USB incarnation/receiver 세대의 resource 결합 없음. 필요한 해결: 정확 binary/driver의 지원 handle·no-reacquire/no-reconnect와 actual peer/effect lifetime proof. 인정하지 않는 대체: -s/-t AND, PID/port/TID 숫자, no-other-target만의 대체 주장.

- **BL03 · ARCHITECTURAL BLOCKER · PR04, PR06, PR09, PR12**: 현재 host의 OS mandatory USB/network/FD/process recipe가 미자격. 필요한 해결: 선정한 exact recipe 1개와 지원 kernel/backend/권한·전면 effect sink 목록, C2 두-target 실제 lab/lifetime 증거. 별도 host/lab 승인 필요. 인정하지 않는 대체: 환경 변수/private port·Python 거부를 host 전체 sandbox로 해석하거나 namespace 이름·major/minor만 인증으로 수용.

- **BL04 · ARCHITECTURAL BLOCKER · PR05, PR06, PR07, PR12**: 실제 무효화 사건과 host write/자원 획득/버퍼 이동의 사건 cutoff를 강제할 지원 primitive 없음. 필요한 해결: event→sink의 선형화/자원 폐기 논증 및 독립 실제 bytes/두 sink 관측. guardian polling 지연과 pending I/O를 포함. 지원 없으면 현재 아키텍처 거부. 인정하지 않는 대체: 관측 뒤 kill·Python lock·reservation을 제출로 변경·UNKNOWN으로 늦은 write 위반 면제.

- **BL05 · INSUFFICIENT SOURCE EVIDENCE · PR01, PR02, PR03, PR08, PR09, PR12**: AS01–AS06/GR01–GR07 미수용, binary/source 대응·최종 phone APK/endpoint/OS 적용성·독립 수용 담당 미지정. 필요한 해결: 범위별 신뢰 가정의 명시 판단과 기술 보증의 분리, 고정 binary proof·최종 artifact Android/lab evidence 및 비참여 역할 지정. 가정 수용만으로 BL01–04 해소 불가. 인정하지 않는 대체: 보존 x86_64 APK를 phone용이라 주장·문서 N5를 technical receipt로 전환.

- **BL06 · IMPLEMENTATION GAP · PR07, PR08, PR10, PR11**: durable one-shot·attempt ledger·bounded journal·fixed action semantics/checkpoint가 없음. 필요한 해결: 별도 승인 범위의 M1/M3/M4 구현·실제 Android lifecycle/interruption 증거. FS1은 구조 준비 일부만 제공. 인정하지 않는 대체: host one attempt가 app replay를 막는다는 주장·rename/ACK/exit0로 durability나 task 종료 수용.

BL01–04는 별도의 exact source/OS 지원 근거를 갖춘 단일 초기 등록·resource binding·폐기 메커니즘이 필요하다. 한 번의 bounded architecture 심사에서 후보가 없거나 유한 단계의 필수 proof가 불가능하면 BLOCKED/REJECTED로 종료해야 한다. 새 범용 agent, 위험 수용, 개인 단말에 먼저 설치해서 얻는 증거로 대신하지 않는다. FS1은 이 결정을 기다리는 동안에도 안전하게 준비할 수 있는 독립 오프라인 범위지만 별도 구현 승인 전 착수하지 않는다. [미결 목록](benchmarks/real-device-gate-g1-p01/open-technical-blockers.json).

## 10. 이번 작업의 검증·보존·산출물

AGENTS.md가 요구한 기존 웹 build와 소형 backend 회귀만 별도 task-owned frontend 사본·새 합성 임시 SQLite·in-process TestClient로 실행했다. `npm run build`는 exit 0, backend의 기존 `test_authoritative_state.py`, `test_auth.py`, `test_financial_state_gaps.py`는 exit 0이다. pytest는 **72 passed·44 subtests passed**이며 JUnit은 실패/오류/skip 0과 tests=116을 기록한다. 정확한 명령/cwd/time은 [저장소 검증](benchmarks/real-device-gate-g1-p01/repository-validation.json), 압축 로그·JUnit에 보존했다. 이 결과는 G1 구현/검증 캠페인이나 기술 proof 수용이 아니다. 새 G1 테스트·Android build/Flutter 실행·devicegate 실행기 호출은 없었다.

ADB는 help/version 포함 0회, ADB server socket 요청 0회, USB/physical device 열거·접근 0회, emulator 운영 0회, APK 설치 0회다. 생산 API/데이터·OS 정책·서비스 변경은 없었다. 기본 shell sandbox의 bwrap loopback 초기화 오류 후 승인 검토된 host shell에서 문서 읽기/쓰기와 위 기존 호스트 검증만 수행했다. 이 host shell 권한을 G1 실행 권한으로 사용하지 않았다. 일부 읽기 경로의 파일명 조회 실패는 실제 경로를 확인해 정정했고 기존 자료를 생성/수정하지 않았다.

초기 기준선 7,744개 기존 Git tracked/non-ignored 파일과 과거 기준선에서 추가한 ignored 역사 파일 390개, 합계 **8,134개 기존 경로**, 외부 원 B03 frozen sidecar 5개를 보호한다. 시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged entries SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. 종료 재대조에서 **8,134개 기존 경로의 변경/누락 0, 외부 sidecar 5개·source lock 경로 27개·HEAD/index/staged 신원 모두 동일**을 확인했다. [보존 검사](benchmarks/real-device-gate-g1-p01/preservation-verification.json)에 결과를 고정했다. `git diff --stat`의 13개 기존 수정 파일은 시작부터 존재했으며 이번 작업이 변경하지 않았다. ignored runtime/cache/production 전체를 전수 감사했다는 뜻은 아니다.

검증이 끝난 뒤 소유 표식·해당 scratch 사용 process 부재와 로그/JUnit 보존을 확인했다. 이번 작업만의 사본/build/임시 자원 3,421,697바이트를 정리했고 기존 파일/cache/DB 삭제는 0이다. [정리 기록](benchmarks/real-device-gate-g1-p01/artifact-cleanup.json). 대형 benchmark 산출물은 NOT APPLICABLE이다. 역사 문서·반례·source locks·미커밋 변경·HEAD·Git index는 보존하며 reset/stash/clean/checkout/rebase/restage/commit/push는 수행하지 않는다.

| 필수 산출물 | 내용 |
| --- | --- |
| [pr01-pr12-proof-matrix.json](benchmarks/real-device-gate-g1-p01/pr01-pr12-proof-matrix.json) | 12개 정확한 의무·36 facet·12개 분석 항목·계획 분류 |
| [three-safeguard-feasibility.json](benchmarks/real-device-gate-g1-p01/three-safeguard-feasibility.json) | 세 비면제 보호·identity 종류·OS 집행점·미해결 근거 |
| [execution-lifecycle-threat-model.json](benchmarks/real-device-gate-g1-p01/execution-lifecycle-threat-model.json) | 상태 차원·전이·실제 사건 cutoff·remote/ACK/내구 결과 구별 |
| [implementation-component-plan.json](benchmarks/real-device-gate-g1-p01/implementation-component-plan.json) | 여섯 최소 책임·신뢰 경계·소스/강제/실패/시험/의존성 |
| [finite-validation-campaign.json](benchmarks/real-device-gate-g1-p01/finite-validation-campaign.json) | Stage0–6·원 C2/C3/C4/C5·E1–E4 의무/한도 보존 |
| [first-host-only-slice.json](benchmarks/real-device-gate-g1-p01/first-host-only-slice.json) | FS1 하나·검증한 두 파일·한도·24개 고정 수용 시험 |
| [open-technical-blockers.json](benchmarks/real-device-gate-g1-p01/open-technical-blockers.json) | 여섯 미결 영역·필요 해결·금지 대체·현재 BLOCKED 판정 |

정적 문서 검사 결과는 [document-validation.json](benchmarks/real-device-gate-g1-p01/document-validation.json), 최종 새 산출물 hash는 [evidence-manifest.json](benchmarks/real-device-gate-g1-p01/evidence-manifest.json)에 둔다. 문서 검사 통과를 독립 기술 수용으로 부르지 않는다. N01/F02/F03/FC01 독립 종결은 원 범위대로 유지하고 원 F01은 계속 구속·미해결이다. T6.9 DEFERRED, R1 CLOSED, production deployment NOT AUTHORIZED, commit NONE, push NOT PERFORMED다.

**다음 행동:** 운영 차단을 유지한 채 FS1의 두 파일·순수 검증기·24개 고정 사례 범위만 별도 구현 승인 대상으로 제출한다.
