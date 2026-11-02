# Money Note — Real-Device Gate G1-A01 통합 아키텍처 설계

**판정: BLOCKED — NO DEFENSIBLE ARCHITECTURE UNDER CURRENT CONSTRAINTS.**

설치 전 OOB 등록, USB FD 하나만 소유하는 전용 ADB broker, 서명된 계획에 따라 한 번 실행하는 isolated 테스트 앱을 **하나의 연결된 후보 A01-C1**로 검토했다. 현재 신뢰·플랫폼 조건에서 이 후보를 구현 가능한 통합 아키텍처로 선정할 수 없다. 최초 물리 단말과 실제 채널의 등록 결합이 미입증이고, USB reset·수신자/채널 무효화 사건과 실제 새 write를 함께 폐기하는 지원 primitive도 확인되지 않았다. OS 구성 요소를 나열하거나 설치 뒤 앱 key를 만들면 이 두 공백이 해결된다고 보지 않는다.

이번 결과는 모든 플랫폼에서의 불가능성 증명이 아니다. 현재 저장소 구현·검토한 공개 인터페이스·실제 host의 정적 관측으로 원 F01과 세 비면제 보호를 충족하는 후보가 성립하지 않았다는 판정이다. 단일 bounded 질문만 남은 상태도 아니므로 PARTIAL로 분류하지 않는다. 구현 가능성이 확인되기 전 후속 구현 slice나 대규모 native/커널 개발 일정을 만들지 않는다.

새 G1-A01 설계 세션이며 FS1 독립 감사 세션을 이어 사용하지 않았다. 역사 FS1 감사는 입력 근거로 읽고 실제 source pin을 재대조했을 뿐 이번 저자의 독립 기술 수용으로 전환하지 않았다. 실행 코드·유효 계약·원 F01·B03·source lock·Git index 변경 권한, 장치 접근 권한, 기술 proof 수용 권한은 없다. **기술 proof는 0/12 수용, 36 facet 모두 미수용, 원 F01은 구속·미해결, 운영 ADB dispatch는 계속 BLOCKED다.**

## 1. 권위·현재 소스 신원

현행 유효 계약은 [G1 안전 계약](real-device-gate-g1-safety-contract.md)이며 실제 SHA-256은 다음과 같다.

`679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`

계약·의존성·효력·명세·현재 FS1 source에 대한 **41개 pin을 실제 bytes에서 재계산해 모두 일치**함을 확인했다. [신원/효력 검사](benchmarks/real-device-gate-g1-a01/source-and-authority-verification.json)에 개별 expected/actual을 남겼다. N3/N4/N5 완료 사건 `G1-N3-N4-N5-DOCUMENT-APPLICATION-COMPLETE-01`과 직접 연결된 승인·적용·독립 정합성 기록을 대조했다. 현재 계약의 상태 주석 한 줄을 제외하면 과거 승인본 SHA `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e`가 복구된다. 과거의 미적용 문구와 N3/N5 당시 hash를 현재 hash로 덮어쓰지 않는다.

| 대상 | 확인한 현재 SHA-256 |
| --- | --- |
| FS1 기술 명세 | `2ae1c27bdd6c72664190063c507b2820f1c7a3a40eba7b8d3fcfb9a6322adfda` |
| guards.py | `005be5c2d9f55ecde81e93dbf626e62bbb0e61b45d1984b88f5d5dc094fe79a7` |
| test_safety.py | `a943a150bcc528b6cb0a2479933d57b5fa8c62bdf8fec43c91b04749ae1d6ead` |
| dispatch.py | `63af7b01dedec4242b990bffed1a5c81b241d5fe8728c04ef3a4ce65b8d08293` |
| smoke.py | `36dde3d1407703048e79dbb20e8764e9b7d28c5c8804611d9d45142541669a10` |

[전체 근거 목록](benchmarks/real-device-gate-g1-a01/source-catalog.json)은 96개 로컬 문서·소스·자료의 경로/크기/hash를 고정한다. AGENTS, artifact hygiene, project-state, domain-model, known-issues, architecture의 서버 authority 경계, security/runbook의 인증·개발/운영 분리, 원 PREP01·PREP03 F01·PREP09·PREP10, 현 G1·N3/N5·주석 후속 기록, P01 및 원 proof/phase/gate 행렬, FS1 명세·구현·독립 감사와 Android 격리/lifecycle 소스를 읽었다. 과거 O2/O3 문서 자체를 현행 규범으로 사용하지 않고, 현 계약 S4/S7가 해시로 편입한 의무·facet·거부 기준만 누적 적용했다.

원 F01의 정확한 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

[원 finding](benchmarks/real-device-gate-prep03/finding-register.json)의 같은 serial transport 재등록과 [PREP09 잔존 반례](benchmarks/real-device-gate-prep09/regression/prior/f01-unclosed-interface-counterexample.json)의 `changed-after-last-probe` 모의 mutation을 보존한다. 이는 실제 개인 phone 치환 exploit의 관측이 아니며, 진단 PASS도 F01 해결이 아니다. PREP10 옵션표를 재선택하는 대신 실제 자원 graph·FD 수명·reset·앱 제어/결과까지 한 후보로 연결해 아래에서 반증 경계를 확인했다.

상위 B §27/29, C §26/34/34-B11/35/35-T69/38.8–12의 actual 절도 읽었다. Android 내구성·기존 B/J/legacy·restore/MW·30개 artifact/GC·원 B03 증거·whole-F·실기기 성능 단계 분리는 유지한다. 본 설계가 T6.9 재개, R1 활성화, rollout/배포 또는 새 모바일 금융 검증 의무를 만들지 않는다. 서버 DB/API의 확정 금융 authority와 모바일 필수 wire/저장/복구/generation 경계는 변경하지 않는다.

## 2. 구별해야 하는 신원과 불변식

다음 신원은 서로 대체할 수 없다. 문자열은 증거를 지칭할 수 있지만 실제 resource나 실물의 인증 자체는 아니다.

| 기호 | 신원 | 의미와 수명 | 단독으로 제공하지 않는 보증 |
| --- | --- | --- | --- |
| P | 물리 단말 | 소유자가 연결 전 특정한 Galaxy S23 FE 실물. 현재 승인된 식별 근거/제조사 인증키 없음. | owner-local/OOB 신뢰 등록 필수. serial·모델·IMEI 문자열만으로 인증 불가. |
| U | USB 장치/연결 incarnation | 열린 usbfs file의 usb_dev_state→usb_device 및 interface/endpoint 객체 수명. bus/address/dev_t는 재사용 가능. | FD 수명은 물리 P 인증과 다름. reset에 영구 폐기된다는 지원 계약 없음. |
| T | ADB transport | 한 server process의 atransport 객체. 숫자 transport_id는 선택자. | server restart/다른 backend/reconnect를 넘는 인증 아님. |
| S | ADB server 세대 | 고정 실행 inode/build와 실제 process·소유 control IPC의 수명. pidfd는 그 process 수명 보조. | PID/port/UUID만으로 server/peer 인증 불가. |
| H | host process | host boot+전용 UID+실행 inode+namespace/cgroup+실제 pidfd/IPC. | UID/boot 문자열은 증거 식별자. OS 적용/자원 참조와 묶어야 함. |
| A | test package/signer | kr.re.hjkerman.money_note.devicegate, 별도 signing cert, 최종 APK SHA, 실제 Android UID/install instance. | 같은 signer로 여러 phone에 설치 가능. P/U 인증 아님. |
| R | device-side 실행자 | stock adbd/boot의 해당 service stream, 설치 뒤 test UID의 논리 task/consumed record. | shell stream·PM 설치 완료·Activity 시작·task 종료·durable 결과는 별개. |
| C | 실제 command channel | 특정 S/T/U/R에 고정된 IPC/ADB service stream 객체와 bytes의 전달 관계. | socket 이름/직전 peer 조회/FS1 hash만으로 수신자 인증 불가. |

물리 P의 최초 식별에는 **연결 전 owner-local 기록과 설치 없는 OOB 검증**이 필요하다. host USB/ADB 메타데이터로 P를 처음 정의하거나, 앱 설치 뒤 key로 최초 설치를 소급 인증할 수 없다. package/signing key는 앱 제작/설치 신원이며 같은 key로 여러 물리 단말에 설치될 수 있다.

모든 아래 I01–I10에 공통으로 적용되는 actor·수명·실패 규칙은 다음과 같다. 제안하는 신뢰 주체는 owner/OOB 관찰자, host 관리자·kernel/driver·provisioning 경계, 고정 broker/ADB/adbd/Android/서명 앱과 artifact custody다. **이 신뢰 가정은 아직 소유자가 항목별 수용하지 않았다.** manifest/receipt 공급자, task controller와 후손, 다른 USB/ADB 기기, 다른 비특권 host/app process와 재생성 intent는 불신한다. 악성 root·Android·USB relay를 조용히 위협 모델 밖으로 제외하지 않는다. AS01–AS06의 미수용 상태를 유지하며, 향후 가정 수용만으로 필수 proof 결측을 면제할 수도 없다.

권한 수명은 별도 exact owner grant부터 만료 또는 실제 무효화 사건 중 먼저 발생한 때까지다. 연결/read-only, 첫 mutation, 후속 checkpoint는 다르다. 연결 세대 수명은 같은 U/S/C/T/R의 실제 resource 수명 교집합이다. USB 단절·교체·reset·재열거/재등록, server/client/channel 재시작, transport/receiver 세대·신원 불일치, host 중단·감독/자식 회수 상실, 철회·취소, 계획/artifact/정책 drift, 시간/bytes/용량/증거 실패는 단방향 REVOKED다. 같은 ID의 재등장·late ACK·POST 판정으로 복구하지 않는다.

결측·불일치·집행 지원 부재는 DENY다. 이미 제출된 작업의 결과·원격 종료 미입증은 UNKNOWN_QUARANTINED이며 실제 늦은 write/오대상 effect는 FAIL_VIOLATION이다. UNKNOWN을 실제 위반의 면제로 사용하지 않는다. 아래 표는 각 보증의 보호 대상·신원·경계·독립 수용 증거·한계를 특정한다. 공통 actor/수명/무효화/실패 규칙은 모든 행에 적용되며 기계 파일의 `/common_model` 참조로도 고정했다.

| ID·보증 | 보호 자산·작업 / 신원 | 필요한 집행 경계 | 독립 수용에 필요한 증거 | 잔여 한계 |
| --- | --- | --- | --- | --- |
| I01 승인 provenance와 단계 | owner 승인·개인 단말 접근 / H,P,M | 신뢰 owner/IR 수용 경계 | exact 계약·grant·36 facet receipt의 종류/scope/기한 대조 | 해시/JSON은 서명·owner 인증 아님 |
| I02 설치 전 P→U→C/R 결합 | 첫 read-only 등록 및 최초 APK 설치 / P,U,C,R | owner OOB + 실제 USB/ADB 자원 | 설치/marker/launch 없는 화면/wire transcript, wrong-singleton 음성 대조, 독립 CP/IP | 현 Galaxy 적용·relay 배제·등록 부수효과 미입증 |
| I03 USB incarnation의 비승계 | 다른 단말/새 열거에 command bytes 전달 금지 / P,U,T | USB kernel/backend와 새 open/FD 획득 차단 | 정확 kernel/backend 수명 분석·두 target lab에서 disconnect/reset/dev_t 재사용 효과 관측 | 고정 FD는 reset 영구 폐기나 물리 인증 보증 아님 |
| I04 실제 채널·수신자·세대 결합 | 승인 action의 실제 command 전달 / H,S,C,T,U,R,M | 단일 broker의 실제 service/USB 제출점 | 동일 객체 graph와 action별 bytes/offset→실제 receiver, no-start/reexec/fallback | stock CLI는 위 capability를 제공하지 않음 |
| I05 OS 전면 매개 | USB/다른 ADB/네트워크/FD를 통한 우회 실행 / H,U,C | root 적용 mandatory device/network/IPC/process 경계 | 전용 UID/정책/FD 목록·부정 우회 실제 sink 관측·lab 두 target | 신뢰 root/kernel 침해 방어 아님. 현재 정책 미부착 |
| I06 실제 무효화 사건 cutoff | 새 제출/write/자원 취득/버퍼 이동 금지 / H,U,S,C,T,R | 사건과 실제 I/O를 같은 순서에 두는 집행점 | t_event/t_observe/t_enforce와 실제 sink 이력; reset/취소/ACK 유실 반례 | userspace watcher/lock/kill·usbfs FD만으로 해당 순서 강제 불가 |
| I07 1회 시도 및 앱 replay 차단 | host action 제출 및 논리 시험 효과 / M,action,A,R | host durable 소모 + native claim-before-effect | 동시 시도·예약 후 crash·duplicate intent·프로세스 재생성·EIO 실제 Android 증거 | at-most-once 시도는 remote exactly-once 완료 아님 |
| I08 허용 artifact/효과/합성 경로 | 설치/launch/앱 저장/합성 backend 요청 / M,APK,signer,A,backend | 봉인 artifact 소비·APK admission·app sandbox·종단 제한 | 최종 ABI/merged manifest·signer·동일 fd bytes·route·비허용 sink 0 | 기존 x86_64/10.0.2.2 artifact는 phone 후보가 아님 |
| I09 증거/원격 수명/격리 분리 | 진행 중 작업·ACK·결과·host 자식 회수 / action,C,R,H | 사전 개방 bounded journal·독립 사후 처분 | SUBMISSION_COMMIT·ACK·durable 결과·remote 종료·child reap 각각 증거 | 이미 제출한 bounded 작업은 계속될 수 있음. 추가 readback/cleanup 금지 |
| I10 원 F01·상위·G1 누적 및 독립 수용 | 기기 gate/후속 연구/실행 허가 / source,runtime,OS,session | 비참여 IR_TECH/IR_SESSION/IR_EVIDENCE와 owner 분리 | PR01–11 후 PR12, CP PH0/IP PH2/POST PH5, 상위 B/C 유지 | 설계/제품 tests/FS1 PASS는 기술 수용 아님 |

상세 규범 pointer와 필드는 [불변식/신뢰 경계 JSON](benchmarks/real-device-gate-g1-a01/security-invariants-and-trust-boundaries.json)에 있다. 이는 새 규범 조항이나 PR13을 제정한 것이 아니라 기존 원 F01/G1/PR 의무의 설계 추적성이다.

## 3. 단일 통합 후보 A01-C1

후보의 경로는 **소유자 OOB 등록 → root가 제한한 단일 USB file → 단일 native ADB broker의 transport/service → 별도 설치 checkpoint → 서명 plan을 한 번 소모하는 test UID → 동일 transport의 제한된 합성 RPC/결과**다. stock CLI를 매 action마다 실행하지 않는다. 연결 전 승인할 실제 action/input/OS bookkeeping과 resource 획득 규칙을 동결하고, actual generation slot만 등록 후 채운다. 정확 target/OS/build/계획 공란을 연결 뒤 임의 보충하지 않는다.

| 구성 | 구체 책임 | 현재 구현/미충족 사항 |
| --- | --- | --- |
| K0 소유자 OOB 등록 | 설치 전 실물 사전 식별과 fresh host key의 신뢰 Android 화면/wire 확인. | 설계 후보. 해당 Galaxy·동시 AUTH·relay 배제 근거 없음. |
| K1 권한 있는 host provisioning | 전용 UID·빈 USB mount·private net/IPC/PID·device cgroup BPF deny·capability 제거 후 정확한 FD만 전달. | 미구성·별도 관리자 승인 필요. |
| K2 USB FD 전용 ADB broker | 한 usbfs FD와 단일 in-process ADB transport만 소유. stock CLI·global server·discovery·reconnect·reset 호출 경로 제거. | stock 지원 인터페이스 없음. source 대응 native 수정 필요. reset/cutoff 미충족. |
| K3 권한/시도/증거 제어 | 외부 신뢰 manifest pin·CP/IP·owner grant·동결 action을 하나의 소모 ledger와 bounded journal로 결합. | FS1은 synthetic 자료 검사만 구현. operational validator/ledger 없음. |
| K4 isolated 앱 1회 실행 | 검토 APK 설치 뒤 서명된 exact plan/grant만 수용하고 native durable claim 후 합성 task 한 번. 상시/privileged agent 없음. | 기존 package/signer 격리만 존재. durable claim·서명 제어 없음. |
| K5 합성 backend 전용 중계 | 동일 T의 localabstract service→앱 native local socket→bounded RPC로 host 합성 backend 연결. phone의 새 TCP/reverse/Wi-Fi 설정 배제. | stock 서비스 종류는 있음. 최종 Android SELinux/peer/종단 적용성 미검증. 현재 emulator HTTP 경로 사용 불가. |
| K6 독립 증거 처분 | 소스/OS/자원·실제 효과를 각 facet에 묶고 비참여 검토자가 별도 판단. | 기술 수용 0/12 유지. |

**실행 가능한 아키텍처 선정은 NONE이다.** A01-C1은 검토한 단일 후보이며 현 제약에서 거부했다. 아래 기술은 결측을 숨긴 구현 지시가 아니라 거부 이유와 향후 필요한 보증을 특정한다. 새 daemon/커널 API/agent가 이미 존재한다고 가정하지 않는다. [통합 구조/허가식 JSON](benchmarks/real-device-gate-g1-a01/integrated-architecture.json).

### A. 설치 전 신뢰 등록

제안 anchor는 소유자가 사전 특정한 실물, 그 실물의 신뢰 Android USB-auth 화면, 전용 broker만 소유하는 fresh session host key의 화면/wire 대응이다. 소유자는 등록 authority이며 IR_TECH가 설치 없는 메커니즘 CP를, IR_SESSION이 실제 P/U/C/R 대응 IP를 따로 심사해야 한다. serial·모델·화면에 적힌 식별 문자열 하나가 immutable physical identity라고 주장하지 않는다.

등록안은 다음 순서다.

1. 연결 전 owner-local 실물 참조·예정 OS/build·등록 protocol·fresh host 공개키의 전체 digest·예산을 동결한다. key 비밀값이나 개인 serial 원문을 이번 증거에 수집하지 않았다.
2. 개인 대상 없이 두 정상 단말의 wrong-singleton, 같은 serial, 동시 AUTH 요청과 relay 경계에 대해 메커니즘 CP를 먼저 입증하고 모든 CP를 독립 수용한다.
3. 별도 owner 연결/read-only grant와 host OS provisioning 뒤 한 USB file을 개방하고 새 open/import 경로를 닫는다.
4. 해당 key의 요청이 의도한 실물의 신뢰 화면에 표시됨을 owner가 대조하고, 같은 file/transport/channel transcript와 연결한다. UI의 ‘한 번 허용’ 조작이 필요하면 **별도 exact 권한과 허용 효과 심사**가 먼저 있어야 한다. 이를 자동 pairing 또는 단순 read-only grant에 숨기지 않는다. 현재 G1 허용 효과에 포함된다고 판정하지도 않는다. 기기 전체 정책 변경이 필요하면 이 후보는 거부한다.
5. 같은 resource에서 미리 동결한 read-only transcript로 build/boot/adbd와 fresh test package 부재를 수집한다. 설치·marker·앱 launch는 0이어야 한다.
6. 화면/wire·자원 연속성과 모든 IP/E2가 독립 수용된 뒤 owner가 별도 첫 mutation을 결정한다.

공식 AOSP의 [AdbDebuggingManager 고정 소스](https://android.googlesource.com/platform/frameworks/base/+/f2387994151f/services/core/java/com/android/server/adb/AdbDebuggingManager.java)는 받은 host key의 fingerprint와 UI 허용을 연결하고, `alwaysAllow`에 따라 지속 저장 경로를 구분한다. **이것은 host 인증/허용 절차라는 사실까지만 확인했다.** 해당 Galaxy 펌웨어의 UI/daemon 대응, 동시에 요청된 다른 채널과의 귀속, key 전달의 단일성·relay 배제, 일회 허용의 실제 부수효과는 검증하지 않았다. 화면의 host key를 P의 인증서로 바꿔 해석할 수 없다. [보존 source/provenance](benchmarks/real-device-gate-g1-a01/official-source-provenance.json).

등록 artifact는 owner provenance/실물 참조·등록 protocol/hash·read-only grant·fresh key 전체 digest와 표시 fingerprint·OOB 관찰 방법·U file/endpoint·S/C/T resource graph·R boot/adbd transcript·source/tool/OS/plan scope·expiry·IP receipt를 함께 담아야 한다. 해시가 있는 JSON 자체를 owner 서명이나 실물 proof로 수용하지 않는다. root custody와 인증된 승인 전달 경로도 필요하다. 무효화 뒤에는 새 세션·새 승인·새 등록/수용이 필요하며 같은 session 재등록은 없다.

다른 정상 phone 하나, 같은 serial 복제, 화면 캡처/과거 transcript 재사용, 중간 relay와 동시 AUTH는 이 연결을 깨뜨릴 수 있다. 해당 기기와 채널의 근거 없이 ‘소유자가 케이블을 꽂았다’는 확인만으로 이들을 막았다고 주장할 수 없다. **현재 최초 등록은 BLOCKED다.** 신규 anchor 채택 의존성을 식별했을 뿐 owner 승인이나 기술 proof를 발급하지 않았다. [등록/신원 모델](benchmarks/real-device-gate-g1-a01/enrollment-and-identity-model.json).

### B. OS가 제한하는 노출과 실제 host의 능력

읽기 전용 관측은 Ubuntu **24.04.5 LTS**, Linux **6.8.0-147-generic**, UID/GID1000, 현재 자기 process `CapEff=0`, cgroup2, AppArmor/landlock/yama 등의 LSM을 확인했다. `/sys/fs/cgroup/cgroup.controllers`에 devices 파일이 없다는 이유로 device BPF가 미지원이라고 판단하지 않는다. 현재 자기 process의 seccomp=0은 향후 sandbox 정책 부착의 성공·실패 증명이 아니다. 도구 binary의 존재나 userns sysctl=1도 실제 recipe의 사용 가능성 증거가 아니다. USB 장치 목록·USB sysfs·ADB socket·container daemon에는 접근하지 않았다. [host 정적 관측](benchmarks/real-device-gate-g1-a01/host-readonly-environment.json).

선정해 평가한 OS recipe는 root-owned 최소 launcher가 전용 비특권 UID를 준비하고, private mount/net/PID/IPC 공간과 빈 USB `/dev`, host `/proc`·sysfs·global ADB/관리 socket 비노출, cgroup device 접근 deny, capability 제거·`no_new_privs`·seccomp를 함께 부착하는 것이다. 필요한 USB FD·sealed APK/input·승인 입력·bounded journal·control/backend socketpair·event/pidfd/timerfd는 등록 전에 고정하고, 이후 새 FD import·device open·mknod·socket/connect·SCM_RIGHTS·ptrace/pidfd_getfd·exec/fork·정책/namespace 변경을 차단한다. native broker에 필요한 최소 ioctl/ABI만 허용하고 reset/configuration/다른 interface 획득은 허용하지 않는 설계다. 이 정확 syscall 집합이 실제 broker에 충분한지도 미자격이다.

[Linux cgroup v2 device controller](https://docs.kernel.org/admin-guide/cgroup-v2.html#device-controller)는 type/major/minor의 device 접근을 BPF로 통제한다. 그 제어를 열린 FD의 진행 중 I/O 폐기나 P의 물리 인증으로 확대하지 않는다. [seccomp](https://docs.kernel.org/userspace-api/seccomp_filter.html)는 syscall 인자/ABI 제한 수단이며 포인터 안 plan·USB generation의 인증 수단은 아니다. 권한이 있는 신뢰 provisioning 담당과 broker의 소스 의미가 함께 필요하다.

따라서 전용 포트·`--one-device`·전용 server는 구성 선택일 뿐 OS enforcement가 아니다. network namespace만으로 USB를 숨길 수 없고, 단일 node bind mount나 major/minor 허용은 주소 재사용·reset을 해결하지 않는다. 후보는 **node 재open을 전면 금지하고 사전 개방 file만 유지**해 그 공백 일부를 줄이려 한다. global 5037/5038, 다른 AF_UNIX 서버, TCP ADB/IPv6/mDNS, 후손/interpreter와 상속 FD, `/proc/*/fd`, container 관리 socket, privileged launcher 재호출도 경계에 포함해야 한다. 신뢰 root/kernel을 침해한 공격까지 이 recipe로 막는다고 주장하지 않는다.

현재 전용 principal·정책·native broker·감독 recipe는 구성/시험되지 않았다. 첫 shell은 bwrap loopback 초기화 오류로 실행 전 실패했고 자동 승인 검토를 거친 host shell에서 분석을 수행했다. 그 실패를 모든 privileged namespace 구성의 보편적 불가능성으로 확대하지 않으며, host shell 승인을 G1 confinement 자격으로 쓰지도 않는다. **OS 격리는 설계 일부만 있고 현재 BLOCKED다.** [집행 경계 분석](benchmarks/real-device-gate-g1-a01/os-isolation-enforcement.json).

### C. 실제 채널·수신자·세대와 사건 cutoff

후보 broker는 고정 build의 native process 안에 USB-only ADB transport를 하나만 만들고 실제 control socketpair와 한 USB file을 소유한다. 각 service OPEN은 바로 그 transport 객체에서만 파생한다. 고정 install bytes, 고정 launch, 사전 승인한 앱 결과/RPC 외의 service를 열지 않는다. 매번 serial/TID로 새 CLI를 선택하거나 host의 범용 ADB listener를 통하지 않는다. pidfd는 process의 수명 증거에만 사용하고 channel/USB/remote recipient까지 자동 인증한다고 해석하지 않는다.

stock ADB에 이 FD-only 진입점이 존재한다고 주장하지 않는다. PREP10이 고정한 AOSP revision `1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc`의 libusb backend는 `libusb_open`, hotplug enumerate, `Reset()` 뒤 `process_device()` 재진입 경로를 갖는다. [보존 backend:568/754/1028](benchmarks/real-device-gate-prep10/official-sources/client__usb_libusb.cpp.txt). source 대응 native 변경 없이는 위 후보가 아니다. 이 AOSP revision과 설치 Google binary의 build 대응은 여전히 **UNVERIFIED**이며 이번에 binary를 help/version으로도 실행하지 않았다.

공개 [libusb API](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html)의 `libusb_wrap_sys_device`와 no-discovery 방식은 미리 연 FD로 I/O할 수 있다는 후보 근거다. Linux v6.8 [usbfs 비교 소스](https://kernel.googlesource.com/pub/scm/linux/kernel/git/torvalds/linux/+/refs/tags/v6.8/drivers/usb/core/devio.c)에서 open은 `usb_dev_state`에 `usb_device`를 참조하고, ioctl의 `connected()`는 file list/NOTATTACHED 상태를 확인한다. 그러나 성공 reset이 매번 handle을 무효화하는 계약은 없다. 이 source는 실제 Ubuntu patched kernel과 build 대응을 확인한 것이 아니다. [고정 분석 사본:1032/1499/2597/2858](benchmarks/real-device-gate-g1-a01/official-sources/linux-v6.8-devio.c.txt).

이로부터의 **설계 추론**은 좁다. 경로 재open을 막으면 같은 node가 다른 기기를 가리킬 때 재선택되는 경로를 줄일 수 있다. 하지만 file 고정만으로 모든 reset의 영구 폐기, adbd/receiver 세대 안정성, owner 철회와 모든 I/O의 순서를 확립하지 못한다. broker가 reset ioctl을 보내지 않아도 외부/kernel reset이 있다. `t_event < 새 chunk/stream 제출 < t_observe/kill`인 이력을 watcher·Python lock·추가 probe·pidfd만으로 배제하지 못한다. 실패한 syscall 호출, 실제 byte 제출, kernel queue에 이미 들어간 bytes, 아직 host memory에만 있는 bytes도 구별해야 한다.

필요한 강제 지점은 **실제 무효화와 같은 U/S/C/T/R에 대한 모든 새 action bytes·후속 chunk·자원 획득·버퍼 이동을 한 순서에 두고 reset을 영구 폐기로 만드는 primitive**다. 현재 확인한 API/소스에는 그러한 통합 authority primitive가 없다. 이름만 붙인 새 kernel/driver API나 원격 privileged agent를 구현 가능성 근거로 발명하지 않는다. 이 공백은 원 F01과 PR04/05/07에 직접 걸리므로 후보를 거부한다.

| 사건 | 필수 결과 |
| --- | --- |
| USB disconnect/reconnect·교체·reset/재열거 | 이전 세션 영구 REVOKED, 같은 serial/node/TID여도 새 open/transport/권한 승계 금지 |
| server/client/channel restart·TID 변경/재사용 | 새 S/C/T와 이전 grant 결합 금지; 자동 start/reexec/fallback 없음 |
| receiver boot/adbd·승인 신원 불일치 | 새 제출·write·자원 획득·버퍼 이동 0, 후속 mutation 금지 |
| host 중단·감독 상실·owner 철회/취소 | 이미 소모한 attempt를 복구하지 않음; host 자식 회수는 N01 범위, remote 결과 별도 |
| 같은 이름/ID 재등장·late ACK | 세션 재개 금지; 확보 receipt 보완과 권한 복구를 구별 |

`SUBMISSION_COMMIT`은 그 고정 receiver/channel에 실제 action bytes 제출이 시작됐음이 입증된 경계다. 예약·queue·memfd seal·Popen·소모 ledger·ACK가 아니다. APK 첫 chunk를 제출했다고 **아직 host에 남은 전체 APK와 다음 service**까지 이미 제출된 작업으로 취급할 수 없다. 무효화 전에 제출된 동일 action/receiver/channel의 bounded bytes·작업만 이후 완료될 수 있다. 결측은 UNKNOWN_QUARANTINED, 실제 금지 write는 FAIL_VIOLATION이며 지연 관측을 유예로 바꾸지 않는다. [채널/세대 모델](benchmarks/real-device-gate-g1-a01/channel-and-generation-binding.json).

### D. 기기측 실행 lifecycle

기존 test-only package/signer, private 결과 파일, backup/transfer 제외는 유용한 격리 기반이다. 그러나 `main_devicegate.dart:19`는 시작마다 `_smoke()`를 호출하고 `DeviceGateActivity.kt:18`은 run/mode와 결과 기록만 제공한다. 메모리 flag·singleTop·16KiB 제한·rename은 durable consumed claim이나 replay 방지가 아니다. 기존 앱에 cryptographic physical enrollment나 단일 실행 authority가 있다고 주장하지 않는다.

후보는 설치 뒤 테스트 UID 안에서 서명된 exact plan/grant를 검사하고 native durable claim을 **합성 네트워크/시험 저장 효과 전에** 동기 확정한다. `(session,plan,action,install_instance)`가 이미 있거나 손상/EIO/소모 뒤 process death이면 실행·자동 재개 없이 실패/UNKNOWN으로 남긴다. 결과 저장도 claim을 해제하지 않는다. 다른 key의 앱, 같은 package의 예상 밖 설치본, duplicate intent, Launcher 재진입, process 재생성은 grant/소모 검증 전 효과를 낼 수 없어야 한다. exported Activity/intent 자체를 trusted sender로 보지 않는다.

자기 hash 삽입의 순환은 피한다. plan core Q와 검증 공개키를 먼저 고정하고 Q digest를 포함한 APK를 build한 뒤, outer manifest M이 Q·최종 APK·signer·fixture·OS·action hash를 결합한다. owner는 exact M을 별도 승인하고 broker는 그 scope의 일회 grant만 전달한다. 앱 key/설치 nonce는 이후 앱 instance와 replay 경계만 다루며 최초 P binding을 소급 인증하지 않는다. 테스트 signer와 owner/host 세션 승인 서명 역할도 구별한다.

앱과 합성 backend의 후보 경로는 같은 T에서 파생한 `localabstract` service로 Android 앱의 native local socket에 접속하고 bounded RPC로 host의 소유 backend socketpair에 중계하는 방식 하나다. 앱에는 새 Wi-Fi/TCP/reverse 설정이나 범용 command를 주지 않는다. 고정 [ADB 서비스 목록](benchmarks/real-device-gate-prep10/official-sources/SERVICES.TXT.txt:208)에 service 종류는 있지만, 해당 Android SELinux/peer 자격과 최종 APK·Dart HTTP 중계의 적용성은 미입증이다. 현재의 `10.0.2.2:18081` allowlist/Gradle/resource와 x86_64 보존 APK를 phone 호환이라고 취급할 수 없다. 이 경로까지 미확인인 점도 READY/PARTIAL 선언을 막는다.

한 번 설치·launch한 테스트 UID의 고정 task로 후속 ADB 명령 수를 줄이는 것은 반복 원격 선택보다 강한 경계다. 다만 최초 설치, 호스트의 추가 write cutoff, 무단 초기 실행 문제를 없애지는 못한다. 일반 shell·다른 앱 조작·device owner/accessibility·상시 background service·root agent는 도입하지 않는다. 단순 설계가 부족한 이유는 durable one-shot와 Android lifecycle 증거가 필요하기 때문이며, persistent privileged agent가 필요해서가 아니다.

host 취소/EOF 뒤 이미 받은 local task는 계속될 수 있다. local deadline/중단은 보장 수준과 best-effort를 구분하고 공유 CPU/열·PM 작업에 hard realtime stop을 약속하지 않는다. ADB ACK·`am start` 반환·PM 성공·논리 task 종료·durable 결과를 각각 기록한다. task 종료/결과가 무효화 때 확보되지 않았으면 추가 readback/stop/clear/uninstall/reconnect 없이 UNKNOWN_QUARANTINED다. 완전 exactly-once·rollback·개인 데이터 손실 0을 보장하지 않는다.

[실행 수명 상태 기계](benchmarks/real-device-gate-g1-a01/execution-lifecycle-state-machine.json)는 authority, host attempt, submitted byte offset, ACK, remote task, durable 결과, host child reap, evidence, violation을 별도 차원으로 둔다. 현재 실제 도달 상태는 DENIED뿐이다. 뒤 상태 전이는 모두 미구현·미수용 설계다.

### E. 향후 fail-closed 실행 허가식

현재 `dispatch.spawn_process`는 인자를 평가하지 않는 무조건 raise이고 `require_host_confinement`도 무조건 거부다. 이 함수·소스 신원과 FS1 독립 PASS를 보존한다. 미래 구현을 여는 flag·환경변수·boolean·자기서명 receipt를 만들지 않았다.

FS1은 **`G1_FS1_PLAN_ONLY`, `SYNTHETIC`, `NOT_GRANTED`, `NOT_ACCEPTED`, 합성 serial/build/argv**를 정확히 요구한다. 실제 phone/native service 계획을 그대로 넣으면 거부되는 것이 정상이다. 따라서 ‘FS1 manifest PASS → 실행 허용’은 지원되는 통합 방식이 아니다. FS1의 순수 byte/digest 규칙은 후속 명세의 참고 근거가 될 수 있으나, 별도 operational profile·실제 허용 bytes/효과의 명세/구현/독립 검토가 필요하다. FS1 constants를 완화하거나 역사 수용을 새 executor에 이전하지 않는다.

미래 허가식의 설계는 `ALLOW_SUBMIT(a) = 아래 모든 조건 AND QualifiedAtomicSubmit(a, bound_resources, live_authority)`다. 어떤 조건이든 미상/결측이면 DENY다. 검사 tuple을 만든 뒤 별도 비동기 syscall로 넘기는 방식은 마지막 항을 충족하지 못한다.

1. 상위 gate와 원 F01 및 현 G1의 모든 적용 의무.
2. 명시한 trust assumptions/TCB의 owner 결정과 승인 provenance/custody; 가정은 기술 proof를 대체하지 않음.
3. 동결 operational manifest와 별도 신뢰 raw pin의 검증.
4. FS1 source/PLAN_ONLY 경계 보존; synthetic PASS는 권한 입력 아님.
5. 동일 source/tool/APK/fixture/OS에 대한 PR01–12.CP 독립 수용.
6. exact owner 연결/read-only grant.
7. 설치 전 P→U→C/R의 qualified OOB 등록과 신선한 transcript.
8. 실제 U/S/C/T/R/H handle의 동일 세대 결합.
9. 현재 OS mandatory USB/network/IPC/FD/process 격리의 적용 증거.
10. 해당 IP/첫 mutation 전 PR01–12.IP 독립 수용 및 별도 exact owner 첫 mutation grant.
11. 허용 ordinal/bytes/경로/효과/예산 및 필요한 새 checkpoint 수용.
12. action 미시도와 제출 전 durable 소모.
13. 실제 사건 cutoff를 강제하는 지원 I/O primitive.
14. 권한 유효·미철회·미만료·미격리와 감독/증거 저장 유지.

연결/read-only는 모든 CP+D·exact owner 연결/read-only grant·qualified 등록/OS 경계가 필요하고, 미래 U/C의 IP나 remote mutation receipt/POST를 연결 전 선행 요구하지 않는다. 최초 설치/marker/launch는 모든 IP/E2와 별도 owner 첫 mutation grant 뒤다. 후속 action은 동일 연속성·고정 checkpoint·새 material evidence의 지정 비참여 수용이 필요하다. POST는 확보 이력을 평가할 뿐 권한을 소급 발급하지 않는다. PR12는 PR01–11의 해당 facet 뒤 통합하며 자기 receipt를 선행 요구하지 않는다.

**현재 허가식 값은 DENY다.** K0 등록·K1 OS recipe·K2 submit fence·K5 Android 경로가 미자격이고 operational manifest profile/owner grant도 없다. 이 식은 문서 설계만 했으며 구현·활성화하지 않았다.

## 4. 필수 위협 이력 14개

각 행은 요구할 예방/검출과 그 한계를 함께 제시한다. ‘시험’은 모두 후속 승인과 해당 단계의 선행조건 아래 수행할 요구이며 이번 실행 결과가 아니다. source에서 한계를 확인한 것과 실제 효과 검증을 구별한다.

**T01 — 무단 두 번째 Android 연결**

공격 능력: 비권한 기기 추가·후손 raw ADB 시도. 필요한 결과: 다른 기기에 effect 0, 새 transport 등록/선택 금지.

집행/검출: K1 새 device open deny + K2 단일 inherited USB file·discovery 없는 transport. 현재 중앙 거부가 실제 보호. 남는 race/공백: provisioning 전 잘못된 FD를 넘기면 K0 없이는 예방 불가. 타 UID/global server 경계도 미자격.

필수 시험: 두 독립 USB sink에서 추가 연결·global ADB·wrapper 시도; 무단 sink bytes 0. 장치 없는 검증: 부분: 정책/syscall 음성은 host; 전체: 물리 USB lab 필수. 에뮬레이터: 보조만. 물리 상호작용: 비개인 두 USB target CP, 개인 대상 IP. **완전한 mitigation 수용은 없음.**

**T02 — 승인 단말 분리 후 교체**

공격 능력: 같은 port/node에 다른 phone 연결. 필요한 결과: 이전 권한 영구 폐기, 교체 target effect 0.

집행/검출: K2 기존 usb_device file만 유지하고 새 open/import/reconnect 금지. 남는 race/공백: kernel 관측 전 write 및 같은 FD를 보존하는 reset cutoff 미해결.

필수 시험: 개방 file 유지 상태에서 unplug/replace/dev_t 재사용, 두 sink와 모든 write 기록. 장치 없는 검증: 불가: 모형은 재선택 논리만. 에뮬레이터: 보조만. 물리 상호작용: 물리 USB lab 필수; 개인 U IP 별도. **완전한 mitigation 수용은 없음.**

**T03 — 다른 기기가 같은 ADB serial 제시**

공격 능력: descriptor/serial/build 복제·relay. 필요한 결과: 이름이 같아도 잘못된 P는 등록/설치 거부.

집행/검출: K0 owner-local 실물+fresh host-key 화면/wire 대응을 요구. serial을 인증으로 사용하지 않음. 남는 race/공백: host-key는 host 인증임. 신뢰 UI/단일 전달 경로·relay 배제 미입증이면 등록 BLOCKED.

필수 시험: 동일 serial 정상 두 단말 wrong-singleton 및 relay/동시 AUTH 음성 이력. 장치 없는 검증: 불가: 위조 증거 거부 부분만 host 가능. 에뮬레이터: 개인 P 인증 대체 불가. 물리 상호작용: 비개인 실물 OOB CP; 개인 P 대응 IP. **완전한 mitigation 수용은 없음.**

**T04 — transport ID 무효화/재사용**

공격 능력: 같은 숫자·server 교체 또는 TCP reconnect. 필요한 결과: 이전 transport 권한 승계 금지.

집행/검출: K2 숫자 재조회 대신 고정 process+atransport+USB+service graph, TCP 기능 제거. 남는 race/공백: native broker 미구현. 동일 객체의 내부 reset/receiver 변화는 별도 cutoff 필요.

필수 시험: TID 재사용/server 객체 재생성/동일 숫자 다른 sink로 허가가 전달되지 않음. 장치 없는 검증: 부분: 객체·권한 모델 및 synthetic process. 에뮬레이터: 실제 service 검증 필요. 물리 상호작용: USB 적용성 CP/IP 필요. **완전한 mitigation 수용은 없음.**

**T05 — ADB server 재시작**

공격 능력: process 종료 뒤 동일 PID/port/TID 재등장. 필요한 결과: REVOKED; auto-start/reexec/fallback 0.

집행/검출: K1 외부 socket·새 exec 차단, K2 한 process generation/실제 control IPC 소유. 남는 race/공백: pidfd 이벤트 전에 다른 writer/queue가 남으면 PR07 미충족.

필수 시험: 동일 PID/주소 모형·server 강제 종료·attempt 전후 interruption·다른 sink. 장치 없는 검증: 부분: host process/IPC 경계는 가능. 에뮬레이터: 동일 service 경로의 restart 필요. 물리 상호작용: 물리 적용성·실제 S IP 별도. **완전한 mitigation 수용은 없음.**

**T06 — USB 재열거/reset**

공격 능력: 같은 주소/FD가 남거나 새 node 등장. 필요한 결과: reset 자체에서 이전 세대 영구 폐기.

집행/검출: K1 새 open deny, K2 reset ioctl·reconnect 금지 설계. 남는 race/공백: 성공 reset은 handle 유효할 수 있음. 외부/kernel reset의 영구 latch가 없어 후보 거부.

필수 시험: reset 유지·재열거·같은 dev_t·동시 제출/부분 APK에서 실제 sink cutoff. 장치 없는 검증: 불가: 정적 반례 확인만 가능. 에뮬레이터: 물리 USB 대체 불가. 물리 상호작용: 비개인 USB/driver lab 필수. **완전한 mitigation 수용은 없음.**

**T07 — 검증과 dispatch 사이 host 중단**

공격 능력: SIGKILL/crash·감독 소실. 필요한 결과: 재시도/새 권한 0; 미확정은 격리.

집행/검출: K3 제출 전 durable attempt 소모·복구 금지, K1 외부 supervisor·N01 host 회수. 남는 race/공백: 모든 writer가 즉시 멈춘다는 증거 없음. supervisor kill만으로 cutoff 입증 불가.

필수 시험: 검증 뒤/예약 뒤/첫 byte 전후 interruption, child/remote 결과 별도 관측. 장치 없는 검증: 부분: durable host ledger·자식 회수. 에뮬레이터: 실제 Android remote task 이력 필요. 물리 상호작용: 현 대상 적용성 IP/POST 별도. **완전한 mitigation 수용은 없음.**

**T08 — host 취소 뒤 원격 작업 지속**

공격 능력: 이미 받은 task·ACK 유실·늦은 ACK. 필요한 결과: 새 host write 0; 종료/결과 미입증 UNKNOWN_QUARANTINED.

집행/검출: K4 사전 고정 local task/예산, K3 단방향 폐기·자동 stop/readback/cleanup 없음. 남는 race/공백: 이미 제출된 작업의 후속 effect 허용 범위만. 즉시 remote stop/rollback은 제공하지 않음.

필수 시험: 수신 전 취소·예약 후 미제출·수신 후 ACK 유실/늦은 완료를 실제 task observer와 대조. 장치 없는 검증: 불가: host stop이 remote 종료 증거 아님. 에뮬레이터: 실제 task/lifecycle 증거 필요. 물리 상호작용: phone 적용성·실제 이력은 별도 IP/POST. **완전한 mitigation 수용은 없음.**

**T09 — 앱 교체/다른 signer**

공격 능력: APK 경로 치환·다른 key·기설치 package. 필요한 결과: 불일치 install/launch 거부, 기존 앱 clear/uninstall 금지.

집행/검출: F03 sealed fd/admission 보존; K4 설치 전 부재와 설치 뒤 exact signer/APK checkpoint. 남는 race/공백: 설치 ACK와 실제 package identity는 별도. 승인 checkpoint 전 launch 금지.

필수 시험: host APK 치환/서명 음성 + Android 실제 installed signer/UID/checkpoint. 장치 없는 검증: 부분: artifact bytes/admission은 host 가능. 에뮬레이터: 설치 후 package/UID 증거 필요. 물리 상호작용: 개인 fresh 부재 IP·설치 checkpoint 별도. **완전한 mitigation 수용은 없음.**

**T10 — 오래된 plan replay**

공격 능력: duplicate intent·process recreation·옛 scoped grant. 필요한 결과: 논리 시험 자동 재실행 0.

집행/검출: K4 서명 outer plan+grant·기한·native durable consumed tuple. 남는 race/공백: 현재 앱에는 claim 없음. app data 삭제/reinstall 복구 경로 금지; Android durable 오류 proof 필요.

필수 시험: 동시 duplicate·relaunch·claim 직전직후 death·EIO/손상·옛 grant. 장치 없는 검증: 부분: 서명/ledger 모델. 에뮬레이터: 최종 APK lifecycle·I/O 필수. 물리 상호작용: 해당 phone OS/ABI 적용성 별도. **완전한 mitigation 수용은 없음.**

**T11 — OS 격리 경계 우회**

공격 능력: raw interpreter/child·SCM_RIGHTS·proc fd·global socket. 필요한 결과: 다른 기기/채널로 effect 전달 불가.

집행/검출: K1 전용 UID·mount/net/IPC·BPF device deny·seccomp/capability + K2 단일 fd. 남는 race/공백: root/kernel 침해 방어 아님; AS01 미수용. 정책 미부착·기존 FD/포인터 ioctl 의미 별도.

필수 시험: alias/wrapper·상속·SCM_RIGHTS·pidfd_getfd·ptrace·socket·새 USB open 및 두 sink. 장치 없는 검증: 부분: 실제 host 정책 음성은 별도 승인 후. 에뮬레이터: 보조만. 물리 상호작용: USB 실제 reachability CP lab 필수. **완전한 mitigation 수용은 없음.**

**T12 — 등록 증거 위조/재사용**

공격 능력: JSON 재해시·owner/reviewer 사칭·과거 transcript. 필요한 결과: 진짜 owner/실제 세대와 귀속 안 되면 DENY.

집행/검출: K0 새 challenge transcript, K3 root custody·인증된 owner/IR provenance·scope/기한 및 자원 graph. 남는 race/공백: SHA는 provenance 인증 아님. 현재 등록 anchor/저장소/custody 미구현.

필수 시험: self-accept/재해시/옛 session/교체 U의 receipt 거부, 실제 OOB 대조. 장치 없는 검증: 부분: 위조 입력 거부. 에뮬레이터: 개인 P 대응 증명 불가. 물리 상호작용: 실물 OOB/IP 필수. **완전한 mitigation 수용은 없음.**

**T13 — backend/APK artifact 치환**

공격 능력: build 뒤 파일/endpoint/listener 교체·redirect. 필요한 결과: 승인 bytes·합성 종단 외 effect 0.

집행/검출: F03 동일 sealed fd 소비, K5 사전 소유 IPC·합성 backend/fixture pin·route/byte 제한. 남는 race/공백: 현재 x86 APK/10.0.2.2는 phone용 아님. K5 UDS·SELinux/Android peer 적용성 미확인.

필수 시험: seal 후 pathname 교체/short write·backend 교체/3xx·비허용 route 실제 sink. 장치 없는 검증: 부분: artifact/host 종단은 host 가능. 에뮬레이터: 최종 Android RPC·route 필수. 물리 상호작용: 현 대상/receiver 귀속 IP 별도. **완전한 mitigation 수용은 없음.**

**T14 — manifest는 유효하나 수신자 무관**

공격 능력: 완전 canonical FS1/계획을 다른 channel에 제시. 필요한 결과: validator PASS로 dispatch 절대 허용하지 않음.

집행/검출: FS1 synthetic-only 유지 + future predicate에 K0/K1/K2 actual graph·CP/IP·owner grants 모두 AND. 남는 race/공백: 구조/서명은 receiver 결합 아님. qualified binding/submit primitive 없어서 현재 항상 DENY.

필수 시험: 유효 raw/같은 hash를 다른 U/S/C/T/R에 주고 실제 두 sink와 거부 대조. 장치 없는 검증: 부분: 현재 거부/논리 conjunction은 host 가능. 에뮬레이터: service 매핑 검증 보조. 물리 상호작용: 물리 recipient 결합 CP/IP 필수. **완전한 mitigation 수용은 없음.**

14/14 상세 actor·mechanism·race·시험·host/emulator/physical 분류와 PR 연결은 [위협 평가 JSON](benchmarks/real-device-gate-g1-a01/threat-scenario-assessment.json)에 있다. 기존 source와 중앙 DENY가 보장하는 현재 무실행을 미래 후보의 mitigation proof로 세지 않는다.

## 5. PR01–PR12 전체 기술 proof 대응

다음 표는 전체 의무를 줄인 대체 행렬이 아니다. [기계 대응 행렬](benchmarks/real-device-gate-g1-a01/pr01-pr12-architecture-mapping.json)은 유효 계약이 pin한 원 required-proof의 obligation/required_evidence를 그대로 보존하고, 원 phase 행렬의 36 facet evidence·reviewer·phase·dependency를 직접 추출했다. 각 PR의 세부 독립 수용 기준은 그 원 증거에 원 F01·동일 후보/실제 적용성·비참여 심사를 더해 대조하도록 명시했다.

공통 수집/수용 단계는 CP=PH0/PH0(IR_TECH), IP=PH1/PH2(IR_SESSION), POST=PH4/PH5(IR_EVIDENCE)다. 원 B/C 선행 gate와 P01의 A/C1/C2/C3/C4/C5/D/E1–E4를 제거하지 않는다. host-only로 가능한 일부와 전체 증명 가능성은 다르다. 개인 실물 신원·USB의 물리 수명은 emulator로 대체하지 않는다.

| PR·의무 | 기존 부분 / 제안 구성 | 장치 없는 범위 | 필요한 emulator/Android·물리 증거 | 남은 blocker |
| --- | --- | --- | --- | --- |
| PR01 승인 provenance·계약 우선순위 | N3/N5·상태 주석·중앙 DENY, FS1 순수 parser / K3,K6 | 전체 CP 가능; live session IP는 실제 등록 자료 필요 | 불필요; IP 자료는 개인 연결 후 수집하되 PR01 자체 알고리즘은 물리 I/O 불필요 | B03: 정확 owner/IR provenance·운영 profile 검증 없음 |
| PR02 artifact/tool 신원 | F03 sealed APK/admission과 FS1 digest 자료 / K2,K3,K4,K5 | bytes/봉인/source 대응은 가능; Android artifact 적용성은 별도 | 최종 ABI artifact 검증 필요; 실제 실행 fd/단말 ABI·설치 receipt IP 별도 | B02,B03: 고정 ADB source/binary 대응·phone 최종 artifact 없음 |
| PR03 최초 등록과 bootstrap 결합 | 등록 실행 구현 없음; emulator 문자열 probe만 / K0,K2 | 불가; host 입력 거부/프로토콜 정적 검토만 | P 인증 대체 불가; 비개인 wrong-singleton OOB CP + 개인 P/U/C 대응 IP 필수 | B01,B02: 설치 전 trusted OOB 화면/wire·same-channel binding 없음 |
| PR04 USB incarnation 강제 | passive USB 관측과 전면 거부 / K1,K2 | 불가; 정적 조건/정책 일부만 | USB proof 대체 불가; 비개인 USB 두 target CP lab + 실제 U IP 필수 | B02,B03: reset/재열거 영구 폐기·정확 kernel lifetime 미자격 |
| PR05 server/channel/transport 결합 | historical AOSP stream/TID 분석·순차 guard / K2,K3 | 부분: process/IPC 모델·source; 전체는 실제 service 필요 | 실제 ADB service/lifetime 증거 필요; USB/channel 실제 적용성과 S/C/T/R IP 필수 | B01,B02,B03: 실제 socket/transport/receiver 자원 graph와 submit fence 없음 |
| PR06 OS 전면 매개와 우회 불가 | FC01 지원 경로 중앙 거부 / K1,K2 | 부분: 실제 host 정책 음성은 가능; USB reachability 전체는 lab | 보조 검증; 비개인 USB 두 sink CP + 현재 정책/FD IP 필요 | B02,B03: host OS mandatory 정책 미구성·FD/I/O 범위 미자격 |
| PR07 폐기·host 1회 시도·감독 수명 | N01 host child 회수와 현재 중앙 DENY / K1,K2,K3,K4 | 부분: ledger/자식 회수; 전체 cutoff/remote는 불가 | 실제 interruption/task 이력 필요; USB reset/replace 두 sink CP + 실제 session 감독 IP/이력 POST | B02,B03: 실제 사건 cutoff·durable attempt/remote 수명·new buffer 차단 없음 |
| PR08 앱 격리와 자동 재실행 방지 | 별도 package/signer/private storage·backup 제외 / K4 | 부분: 최종 APK 구조/서명만 | 최종 APK 실제 lifecycle·I/O 오류 필수; 개인 fresh package 부재/OS/ABI IP, 설치 후 checkpoint는 별도 | B03: 현재 앱 재생성 자동 _smoke; native durable claim 없음 |
| PR09 합성 backend·네트워크 | F02 host 합성 HTTP와 emulator route allowlist / K1,K5 | 부분: host IPC/backend·route/redirect | 최종 Android 경로 필수; 실제 session 종단/route 귀속 IP 필요 | B03: phone UDS/RPC·SELinux/peer/종단·egress 미자격 |
| PR10 자원·증거·UNKNOWN 처분 | 시간/byte 제한 일부·private 결과 상한 / K3,K4,K6 | 부분: host evidence fault/한도; remote 예산/종료는 불가 | remote interruption/claim/result 관측 필요; 현재 여유/한도/증거 IP와 실제 이력 POST 필요 | B02,B03: bounded durable journal·hard/soft·remote 결과 분리 없음 |
| PR11 명령·효과 allowlist 완결성 | FS1 literal synthetic R/I/L/C 검사 / K2,K3,K4,K5 | 정적 완결성/순서 검토 가능; 실제 effect 완결성 별도 | 최종 app/service semantic 필요; 실제 endpoint/recipient/신원 slot IP 적용성 필요 | B01,B02,B03: operational bytes/service/효과·새 profile 미정 |
| PR12 독립 통합 수용 | FS1·PREP09 독립 종결과 역사 source lock 보존 / K6 | 전체 불가; metadata/해시 검토만 | PR08/09 등 최종 APK 증거 필요; USB lab/개인 IP·POST 자료 심사 필수 | B01,B02,B03: PR01–11 동일 후보 CP/IP 증거·통합 reviewer 없음 |

**DESIGNED / IMPLEMENTED / TESTED / INDEPENDENTLY ACCEPTED를 분리한다.** A01-C1은 상세 설계 후 거부한 후보다. 통합 구현/통합 시험/독립 수용은 모두 없다. 기존 component의 일부 구현·역사 tests/수용은 그 범위로만 남는다. FS1 자체는 IMPLEMENTED·TESTED·독립 감사 PASS지만, PR01/02/10/11 전체의 CP 수용조차 아니다. 모든 PR의 CP/IP/POST는 PENDING·NOT_GRANTED, 기술 proof 수용은 계속 **0/12**다.

P01의 비개인 C2는 1 recipe/8시나리오/5,400초/20MiB, C3는 4 fresh fixture/4시나리오/1,800초/20MiB, C4/C5는 각각 6 fixture/6시나리오/2,700초/20MiB다. C1은 12 ID/14 이력, D는 1결정/7,200초/50MiB, E1–E3의 600초/10MiB는 제안 상한일 뿐 실제 개인 세션 예산이 아니다. 각 별도 승인과 독립 수용을 유지하고 자동 retry/재감사/연장을 만들지 않는다. A01은 이 캠페인을 실행·예약하지 않았다.

## 6. 공학적 실행 가능성과 중단 결정

**B01 — 최초 P binding:** A01-C1의 fresh host-key OOB 화면 확인은 조사할 수 있는 구체 등록안이지만, 해당 Galaxy의 설치 전 화면/wire/실제 resource 귀속, 동시 AUTH·relay 배제, 필요한 수동 허용 효과와 신뢰 anchor 승인 근거가 없다. host-key prompt를 불변 기기 인증으로 해석할 수 없다. PR03/05/12가 차단된다.

**B02 — actual event/submit fence:** 단일 file/device 참조·no-reopen은 주소 재사용 경로 일부를 줄이지만 reset·receiver 변화·취소 뒤 새 write/자원/버퍼 이동을 막는 통합 primitive가 아니다. stock ADB의 reset/discovery 경로도 제거되지 않았다. source 대응 native 변경과 지원 OS/driver 집행 근거가 없는 상황에서 ‘broker가 있다’고 가정해 F01을 닫을 수 없다. PR04/05/07/12가 차단된다.

**B03 — OS/최종 artifact 적용성:** 확인한 host 기능은 향후 구성 후보의 근거일 뿐 적용된 mandatory 경계가 아니다. 관리자 provisioning·전용 UID/FD custody·실제 binary/source 대응·phone APK/ABI·앱 claim·UDS/SELinux 종단·독립 수용 담당이 필요하다. 도구 설치 여부나 AppArmor가 목록에 있다는 사실로 이 전체를 만족시키지 못한다.

기존 앱의 durable one-shot 강화는 제한된 범위의 후속 구현 과제로 성립할 수 있지만 B01/B02를 해결하지 않는다. 모든 bytes를 미리 queue에 넣거나 전체 script를 먼저 보낸 뒤 ‘이미 제출됨’이라고 이름 붙이는 방법도 동결 action별 권한·SUBMISSION_COMMIT·미전송 bytes 경계를 우회한다. owner 승인 전에 앱을 먼저 설치/등록하는 방안은 첫 mutation gate와 순환된다. 새 persistent privileged device agent는 이 문제의 최소 해법이 아니다.

추가 의존성은 명시적으로 **미승인**이다. 새 OOB 신뢰 anchor, host root의 제한 provisioning, 정확 native ADB/USB 지원, 비개인 두 target 및 독립 효과 관측 장비, 최종 Android artifact/OS 적용성, 인증된 owner/IR custody가 필요하다. 실제 장비의 존재나 phone debugging 상태를 확인하지 않았다. 향후 owner가 신뢰 가정을 명시하더라도 필수 기술 증명을 대신하지 않는다.

판정은 **BLOCKED**다. READY에는 구현 가능한 하나의 강제 경계가 필요하고, PARTIAL에는 그것을 결정할 단일 bounded 질문만 남아 있어야 한다. 현재는 설치 전 anchor와 사건 cutoff, 실제 OS/Android 경로가 각각 결측이다. ‘FD 유지 시험 한 번’이나 앱 replay 시험 하나로 전체 후보가 성립하지 않는다. **현재 trust model을 유지하면서 세 비면제 보호를 충족하는 end-to-end 아키텍처는 확인하지 못했다.** 새 플랫폼의 지원 근거가 필요하며 원 F01을 완화하는 결정은 요청하지 않는다.

핵심 기술 질문은 다음 하나로 지칭할 수 있으나, 이것 하나가 해결되면 전체가 READY라는 뜻은 아니다.

> 실제 USB reset·receiver/채널 무효화와 모든 새 제출/write/자원/버퍼 이동을 같은 순서에 두고 권한을 영구 폐기하는 지원 primitive가 이 플랫폼에 있는가?

현재 확인 근거는 없다. [실행 가능성 결정](benchmarks/real-device-gate-g1-a01/architecture-feasibility-decision.json)에 플랫폼/ADB/앱/재현성/권한/장비/복구별 평가와 B01–B03을 기록했다. owner에게 필요한 결정은 **원 F01과 현 차단을 유지한 채, 설치 전 신뢰 anchor와 사건 cutoff를 제공할 별도 플랫폼의 정적 재설계 범위를 승인할지**다. 장치 연결·read-only·설치·규범 변경·위험 면제 결정을 함께 요청하지 않는다.

## 7. 유한 구현 sequence의 처분

**새 구현 slice: NONE.** [finite-implementation-slices.json](benchmarks/real-device-gate-g1-a01/finite-implementation-slices.json)의 `slices=[]`, `implementation_feasibility_established=false`다. FS1은 이미 완료·독립 통과한 역사 slice로 보존하며 이번의 첫 구현으로 다시 제안하지 않는다. 구현 가능성이 미입증인데 파일/행수/일정만 구체화해 구현을 권고하지 않는다.

따라서 slice별 목적·잠재 소스·precondition·산출물·host 시험·독립 기준·owner approval·잔여 차단은 새 실행 단위로 발급하지 않는다. 앞 K0–K6는 후보 책임과 현재 gap을 설명하는 설계 지도이며 구현 순서/승인이 아니다. 향후 별도 설계가 성립해도 **첫 slice는 host-only이며 중앙 dispatch/confinement 무조건 거부와 운영 caller 0을 보존**해야 한다. 이 제약은 현재 slice 제안이나 소스 변경 허가가 아니다.

순환 없는 gate 순서는 유지한다. 비개인 lab의 메커니즘/최종 Android lifecycle CP → 비참여 CP 수용 → 별도 owner 개인 연결/read-only grant → mutation 없는 고정 OOB 등록/IP → 비참여 모든 IP/E2 수용 → 별도 owner 첫 mutation grant → 설치·고정 checkpoint → launch/단일 task → 분리 후 확보 증거 POST다. 설치 후 앱 key를 CP/초기 등록의 전제로 쓰지 않고 미래 IP를 CP 선행조건으로 삼지도 않는다. **read-only 개인 기기 접근도 현재 승인되지 않았다.**

## 8. 이번 검증·보존·산출물

현재 source·문서 hash/AST·의무 대응과 신규 JSON의 구조/상호 참조를 정적으로 확인했다. devicegate 모듈을 실행/import하거나 mock·OS/lab·Android proof 캠페인을 수행하지 않았다. 새 candidate 구현·권한 predicate 구현·실제 등록 artifact/grant/receipt 발급·서명키 생성은 모두 0이다. 공식 source는 `.txt` 분석 사본으로만 보존하며 executable로 배치하지 않았다.

AGENTS의 기존 제품 검증은 이번 task-owned frontend 사본과 합성 임시 DB/in-process TestClient에서 수행했다. `npm run build` exit0, backend `test_authoritative_state.py`, `test_auth.py`, `test_financial_state_gaps.py`는 **72 tests + 44 subtests, JUnit116·failure/error/skip0**이다. [정확한 검증 명령/범위](benchmarks/real-device-gate-g1-a01/repository-validation.json), 압축 로그·JUnit을 보존했다. 이 결과는 제품 회귀이며 A01 구현·G1 기술 safety·Android/USB proof 수용이 아니다. 성공 로그 전체는 출력하지 않았다.

시작 시 기존 Git tracked/nonignored **7,807개** 경로를 hash/mode/symlink로 고정하고, FS1 감사 기준선에서 Git ignored 역사 **390개**를 추가해 총 **8,197개**를 보호한다. 외부 frozen 원 B03 sidecar **5개**도 역사 hash와 일치함을 재확인했다. 최초 index hash는 FS1 감사의 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged entries는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`와 일치한다. HEAD `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`·main 및 기존 13개 tracked 수정은 그대로다. 이후 Git 읽기는 optional locks를 끄고 수행했다.

최종 [보존 검증](benchmarks/real-device-gate-g1-a01/preservation-verification.json)에서 기존 8,197개 경로의 변경/누락0, 외부 sidecar5개·source lock27개·HEAD/index/staged 신원 모두 보존을 확인했다. ignored runtime/cache/production 전체의 전수 감사라는 주장은 하지 않는다. 이전 PREP10/P01/FS1·원 반례·source locks를 덮어쓰지 않았다. 추가로 [기존 manifest 대조](benchmarks/real-device-gate-g1-a01/historical-manifest-verification.json)에서 FS1 감사 산출물25개와 PREP10 공식 source17개, 합계42개 hash가 일치했다.

제품 검사 scratch는 소유 표식과 실행 종료·관측 가능한 활성 참조 부재를 확인하고 로그/JUnit을 보존한 뒤 이번 task의 사본/임시 산출물 3,421,568바이트만 정리했다. 범위·용량은 [정리 기록](benchmarks/real-device-gate-g1-a01/artifact-cleanup.json)에 남긴다. 기존 DB/cache/파일은 삭제하지 않는다. 공개 문서 조회의 한 경로와 존재하지 않는 conftest 경로 확인 실패는 올바른 실제 경로로 정정했으며 권위·코드·역사 자료 변경으로 우회하지 않았다.

ADB(help/version 포함) 호출0, ADB server socket 요청0, USB/Android 기기 열거·접근0, emulator 운영0, APK 설치0, OS 정책/udev/권한/container/service 변경0, production 접근0이다. B03 synchronization, T6.9, R1, 배포 작업은 하지 않았다. reset/stash/clean/checkout/rebase/restage/commit/push는 수행하지 않았다.

| 필수 산출물 | 내용 |
| --- | --- |
| security-invariants-and-trust-boundaries.json | 8종 신원, 10개 보증, actor/수명/폐기/경계/증거/한계 |
| integrated-architecture.json | 단일 평가 후보 K0–K6와 미래 DENY 허가식·FS1 경계 |
| enrollment-and-identity-model.json | 신규 OOB anchor·설치 없는 등록안·미승인 효과·초기 blocker |
| os-isolation-enforcement.json | 실제 host 관측과 구성/OS enforcement 구별·FD/우회 경계 |
| channel-and-generation-binding.json | 실제 resource tuple·사건별 영구 폐기·지원 submit fence 결측 |
| execution-lifecycle-state-machine.json | authority/attempt/ACK/원격/durable/격리 상태 분리 |
| threat-scenario-assessment.json | 필수14이력·mechanism/race/시험/장치 없는 증명 한계 |
| pr01-pr12-architecture-mapping.json | 원 의무/증거·12 PR·36 facet·각 단계/비참여 수용 기준 |
| finite-implementation-slices.json | 실행 가능성 미입증으로 새 slice0·순환 없는 gate |
| architecture-feasibility-decision.json | BLOCKED·B01–B03·새 anchor/플랫폼에 필요한 owner 결정 |

[정적 문서 검사](benchmarks/real-device-gate-g1-a01/document-validation.json)와 [최종 증거 manifest](benchmarks/real-device-gate-g1-a01/evidence-manifest.json)는 새 산출물의 정합성과 bytes 신원을 기록할 뿐 독립 기술 proof 수용을 발급하지 않는다.

**최종 판정: BLOCKED — NO DEFENSIBLE ARCHITECTURE UNDER CURRENT CONSTRAINTS.** 원 F01과 세 보호를 유지하고, 운영 ADB·모든 장치 실행은 계속 차단한다. 다음 행동은 별도 플랫폼의 설치 전 신뢰 anchor와 사건 cutoff를 검토할 정적 재설계 범위를 소유자가 결정하는 것이다.

