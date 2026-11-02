# Real-Device Gate PREP10 — F01 대상 신원 결합 아키텍처와 소유자 결정안

**판정: C — SAFETY CONTRACT DECISION REQUIRED.**

**NO CURRENT OPTION ESTABLISHES THE REQUIRED GUARANTEE.** 현재 검토한 지원 ADB 인터페이스와 저장소 구현에서는 검증한 대상 신원·연결 세대와 실제 mutation 수신자를 원자적으로 결합한다는 원 F01 보증을 확립하지 못했다. 따라서 권고할 운영 아키텍처는 **NONE**, F01은 **UNRESOLVED**, 운영 dispatch는 **BLOCKED**다. 이 결론은 모든 가능한 아키텍처의 불가능성 증명이 아니라 이번에 검토한 공개 인터페이스·고정 소스·현재 구현에 대한 판단이다.

**유일한 다음 단계 분류는 ‘소유자 승인을 기다리는 공식 안전 계약 결정’이다.** 소유자는 원 계약과 차단을 유지하거나 별도 G1 계약안의 심의를 선택해야 한다. 좁은 mock 조사도 별도 선택지로 제공하지만 이번 작업에서 착수하거나 다음 단계로 자동 예약하지 않았다. 구현·프로토콜 개정·기기 실행·잔여 위험 수용 권한은 발급하지 않는다.

## 1. 근거와 검토 범위

새 아키텍처 검토 세션에서 저장소 자료로만 프로젝트 이력을 재구성했다. 외부 자료는 Android/AOSP/Linux의 공개 인터페이스 의미를 확인하는 데 사용했다. 과거 채팅이나 기기 상태를 추정하지 않았다. 확인한 HEAD는 예상값 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이며 시작부터 있던 tracked 변경 13개와 미추적 자료는 검토 기준선의 일부다.

필수 프로젝트·도메인·알려진 이슈·산출물 관리 문서, architecture의 서버 authority 경계, security와 runbook의 개발/기기/검증 절, PREP01–PREP09 보고서, 원 F01 finding·모의 재현기, 현재 dispatch/guard/시험 어댑터와 앱 source를 대조했다. 서버 DB/API의 금융 authority, 모바일 필수 구조·저장·복구·generation·Offline/pending 경계, B03/B11 규범은 그대로 둔다. 이 설계는 Android durability·T6.9 증거를 수용하는 작업이 아니다. [신뢰 경계](architecture.md), [Android 미완료 proof](t66/c/t66c-delta-sync-protocol.md).

주요 근거의 경로·행 범위·SHA-256과 공식 소스의 URL·revision·사본 SHA는 [근거 목록](benchmarks/real-device-gate-prep10/evidence-catalog.json)에 있다. 이하 R 번호는 저장소 근거, `AOSP-*`는 공식 고정 소스다. 중요한 결론마다 이 목록의 ID 또는 직접 링크를 붙였으며 기계 파일도 같은 ID를 참조한다.

| 근거 | 확인한 사실과 적용 한계 |
| --- | --- |
| R01·R28, PREP03 | 같은 serial의 transport 재등록과 마지막 조회 뒤 변화 모델에서 모의 mutation 지속. 실제 phone 치환·조작을 입증한 결과는 아님 |
| R02, PREP05 | 재등록 거부는 보강됐으나 마지막 probe 반례와 실제 연결/host confinement은 OPEN. 관측 불가능한 임의 software 변화의 탐지를 새 보증으로 만들지 말라는 한계도 보존 |
| R03, PREP06 | 동일 receiver 권한 경계와 실제 transport/host 결합이 필요. 현재 분리된 CLI 호출만으로 종결하지 않음 |
| R04–R06, PREP09 | FC01 독립 종결, 중앙 거부 검증, 어댑터 격리 PASS, 144/144·별도 원 재현 16/16, 새 material finding 0. F01은 여전히 차단 |
| R07·R08, PREP01 | exact manifest에 대한 소유자 1회 승인, 고정 action/예산, 재연결·adaptive retry 금지, 개인 데이터 접근 금지 |
| R09–R16, 현재 source | 중앙 `spawn_process`는 무조건 거부. `require_host_confinement`도 무조건 거부. 시험의 명시적 source patch는 운영 권한 아님 |
| R17–R20·R26 | 현재 테스트 앱·sealed APK와 emulator 전용 endpoint/구성. 기기측 보안 agent나 phone 준비 완료를 의미하지 않음 |

PREP09의 **PASS — FC01 CLOSED**와 N01/F02/F03의 독립 종결을 인계한다. PREP10에서 그 144개나 원 재현 16개를 다시 실행했다고 집계하지 않는다. 해당 source와 역사 증거의 내용·mode 보존으로 기존 종결을 유지한다. [PREP09 결정](benchmarks/real-device-gate-prep09/next-action-decision.json).

## 2. F01의 정확한 불변식

원문 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

이는 [PREP09 F01 결정](benchmarks/real-device-gate-prep09/f01-architectural-blocker.json)의 요구이며 원 PREP03의 연결 세대 취소·동일 transport 결합·소유 대상 외 도달 경로 배제와 함께 읽는다. 기존 emulator 전용 정책의 `qemu=1`, API36, x86_64, 정확한 AVD 조건을 phone 허용 정책으로 바꾸지 않았다. Galaxy S23 FE용 신원 등록 값이나 실행 승인 manifest는 아직 없다. R01·R04·R07·R13.

표기상 `P*`는 승인된 물리 단말이고, 기존 emulator에서는 task 소유 QEMU 인스턴스다. `I*`는 승인된 OS/build·명령 수신자와 판정에 사용하는 신원 속성이다. serial·모델·fingerprint는 증거 요소이며 그 자체가 `P*`를 유일하게 인증하지 않는다. 승인 `a`는 세션, 대상 참조, 수신자/boot 세대, ADB server 세대, transport incarnation, plan/APK hash, 허용 action과 만료를 결합해야 한다. 이는 요구를 검토하기 위한 형식화이며 현재 존재하는 token/API를 기술한 것이 아니다.

| 시점 | 필요한 성질 |
| --- | --- |
| 승인 시점 `t_a` | 소유자가 승인한 대상 `P*`, 검증한 `I*`, 정확한 artifact/action과 세션 범위를 특정한다. USB debugging의 host key 허용과 실험 승인은 별개다 |
| dispatch 시점 `t_d` | 실제 command bytes가 들어갈 채널이 승인된 수신자·연결 세대에 속해야 한다. 직전 inventory의 PID/ID와 새 CLI의 실제 연결을 동일시하지 않는다 |
| mutation 실행 시점 `t_x` | 효과가 `P*`의 승인된 테스트 범위에만 발생하고, 그 action을 허용하는 수신자·세대 조건이 유효해야 한다. 사후 불일치 발견은 오대상 mutation을 되돌리지 않는다 |

의미상 안전 조건은 모든 세션 mutation `m`에 대해 `Effects(m) ⊆ ApprovedEffects(P*, test-package, plan)`이고 `Bound(a,m,receiver-generation,connection-generation)`인 것이다. 승인 전달과 실제 effect 수신자가 결합되는 선형화 지점 또는 명시한 위협 모델 아래의 대체 증명이 필요하다. 여러 순차 probe, 마지막 inventory, Python lock은 그 지점이 아니다.

물리적 USB 단절·재열거, transport 재등록, server process 교체, adbd/receiver 재시작, material 신원 불일치, 취소·예산 초과는 이전 승인을 폐기한다. 같은 phone·serial·숫자 ID가 다시 나타나도 기존 권한은 복구하지 않는다. 기존 serial은 이름, transport ID는 서버 객체 번호, USB bus/device 주소는 열거 위치이므로 각각 수명과 재사용을 따로 다뤄야 한다. R01–R04·R07, `AOSP-transport.cpp`·`AOSP-transport.h`.

다만 이미 수신된 remote 설치/앱 작업의 즉시 취소·rollback은 별도 문제다. host가 자식을 종료했다고 원격 mutation이 없었다고 판단할 수 없다. ‘폐기 이후 새 action을 보내지 않음’과 ‘연결 상실 순간부터 모든 remote effect가 즉시 멈춤’을 구분해야 한다. 후자의 실시간 보증은 검토한 API에 없으며 모호한 결과는 `OUTCOME_UNKNOWN`으로 보존해야 한다. N01은 host 자식 수명의 종결이며 이 remote 보증을 추가하지 않는다. R07·R21, [ADB 서비스 문서 사본](benchmarks/real-device-gate-prep10/official-sources/SERVICES.TXT.txt).

### 서로 대체할 수 없는 다섯 개념

| 개념 | 의미 | 단독으로 증명하지 못하는 것 |
| --- | --- | --- |
| A. 신원 검증 | 관측·등록 증거가 승인 대상을 가리키는지 판단 | 이후 채널의 연속성·실행 권한 |
| B. transport 선택 | server 객체 또는 원격 service stream 선택 | 물리 단말 인증·software predicate |
| C. 연결 연속성 | 승인한 incarnation을 계속 사용 | 같은 ID의 무단 재연결·같은 수신자 내부 상태 불변 |
| D. 실행 승인 | 소유자가 exact plan/action을 한 세션에 허용 | USB debugging 허용만으로의 실험 승인 |
| E. 단독 수신·효과 확인 | 의도한 대상의 effect와 다른 대상 도달 경로 배제를 입증 | exit0·자기 보고만으로 세션 밖 효과가 없다는 사실 |

공식 ADB 문서의 USB RSA 확인은 기기가 host debugging key를 허용하는 절차다. host가 phone의 불변 신원을 검증하는 세션별 실험 승인 증명은 아니다. [Android ADB guide](https://developer.android.com/tools/adb).

### 요구 유형에 대한 판정

원 문서는 host 조회와 remote instruction이 물리적으로 같은 순간에 발생해야 한다는 하드웨어 수준의 명령을 정의하지 않는다. 따라서 요구를 **① 물리적 동시성**으로 과대 강화하지 않는다. 현재 규범은 **④ 동일 수신자·연결 세대의 실행 승인 결합**을 요구하며, 목표상 **② 승인 대상 외 효과 금지**도 포함한다. **③ 명시한 위협 모델 아래의 엄격 승인**은 구현 가능한 형식이 될 수 있으나, 어떤 platform/초기 등록/신원 안정성을 신뢰할지 아직 명시 승인되지 않았다.

PREP05의 sentinel fingerprint 반례는 분리된 검사 결과를 뒤의 mutation에 넘기는 경계를 드러낸다. stock Android의 `ro.*`가 실제로 임의 순간 변경된다거나 실제 USB 연결이 다른 phone으로 순간 이동한다는 증거로 확대하지 않는다. 반대로 ‘정상 OS에서는 안정적일 것’이라는 가정을 승인 없이 원 결합 proof로 수용하지도 않는다. R02·R03·R05.

## 3. 지원 ADB 인터페이스의 능력과 한계

설치된 binary의 **host 전용 `help`, `version`만 2회** 실행했다. 버전은 `1.0.41 / 37.0.1-15733141`이다. discovery·server 접속·선택·기기 명령은 0회다. binary SHA와 원 출력을 [도구/산출물 검사](benchmarks/real-device-gate-prep10/installed-tool-and-artifact-review.json)에 보존했다.

수명 의미의 정적 검토 표본은 공식 AOSP revision `1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc`로 고정했다. **이 source와 설치된 Google 배포 binary의 빌드 대응은 UNVERIFIED**다. 아래에서 매뉴얼의 공개 계약과 소스에서 조건부로 추론한 성질을 구분한다. 실패한 문서 경로 404도 provenance에 남겼으며 정확한 root `SERVICES.TXT`와 Linux `usb/authorization.html`을 찾아 사용했다. [공식 출처 기록](benchmarks/real-device-gate-prep10/official-source-provenance.json).

| 인터페이스 | 확인한 기능 | F01에 남는 한계 |
| --- | --- | --- |
| `-s SERIAL` | 현재 해당 serial 대상 선택 | 불변 물리 신원·연결 세대 증명이 아니며 새 호출은 다시 선택 |
| `-t ID` | 해당 transport ID 선택 | 물리 단말 신원이나 identity predicate와 mutation의 transaction이 아님 |
| `--one-device SERIAL\|USB` | 서버 시작 시 USB 연결 대상 filter | 전체 TCP 제한·OS USB 격리·물리 인증이 아님 |
| `-H/-P/-L` | server host/port/listening socket 지정 | private port만으로 다른 client·server 교체·USB 도달 경로를 배제하지 못함 |
| transport 선택 smart socket | 선택 후 원격 서비스와 stream 연결 | 별도 CLI 사이에 재사용하는 attested device capability가 아님 |

선택 옵션의 공개 의미는 [공식 매뉴얼](https://android.googlesource.com/platform/packages/modules/adb/+/1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc/docs/user/adb.1.md)에 근거한다. 검토한 CLI·서비스 목록에는 ‘이 기기의 이 신원/세대 predicate가 맞으면 이 mutation을 원자 실행’하는 API가 없다. 이를 install-multi-package의 package transaction 원자성과 혼동하지 않는다. [서비스 문서](benchmarks/real-device-gate-prep10/official-sources/SERVICES.TXT.txt).

### transport ID가 제공하는 더 강한 선택 보증

고정 소스의 `NextTransportId()`는 프로세스 안에서 1부터 증가하는 counter다. `atransport`의 ID는 생성 때 지정되며 `const`다. `acquire_one_transport()`는 ID가 있으면 정확한 ID를 찾고, 없으면 오류를 반환한다. 새 USB 등록은 새 객체를 만든다. 따라서 **같은 신뢰 server process·동일 구현·새 USB 객체**라는 조건에서는 사라진 기존 ID를 같은 serial의 새 객체로 자동 선택하지 않는 성질을 설명할 수 있다. 무한한 ID 유일성이나 프로세스 간 유일성을 약속하지 않는다. [transport.cpp:279·903·1566](benchmarks/real-device-gate-prep10/official-sources/transport.cpp.txt), [transport.h:276·322](benchmarks/real-device-gate-prep10/official-sources/transport.h.txt).

중요한 반례는 두 가지다. server가 재시작하면 counter는 다시 시작할 수 있고, TCP transport의 destroy 경로는 kick되지 않은 객체를 reconnect handler에 넘길 수 있다. 따라서 **같은 ID라는 사실은 server 세대 동일성도, 모든 transport의 무단절 연속성도 증명하지 않는다.** TCP와 USB의 수명을 같은 것으로 취급할 수 없다. 이는 공식 고정 소스의 추론이며 설치 binary/단말에서 재현했다고 주장하지 않는다. `AOSP-transport.cpp:180–266, 830–849`·`AOSP-transport.h:276–322`.

또한 고정 client의 `switch_socket_transport()`는 ID가 있으면 serial보다 먼저 ID 경로를 선택한다. `-s SERIAL -t ID`는 **serial과 ID가 동시에 맞아야 한다는 AND 검증이 아니다.** 현재 harness의 두 인수 표기를 추가 신원 보증으로 집계하지 않는다. 실행은 중앙 거부로 막혀 있으며 이번에 source를 바꾸지 않았다. [client 소스:81–126](benchmarks/real-device-gate-prep10/official-sources/client__adb_client.cpp.txt), R13.

### 이미 선택한 연결의 재사용

공식 서비스 문서는 transport 선택 뒤 같은 socket을 원격 서비스로 연결하는 구조를 설명한다. 고정 소스는 `s->transport`를 설정하고 service peer에 전달하며, offline 처리에서 관련 socket을 닫는다. **이미 열린 한 service stream의 receiver 결합**은 매번 serial을 다시 선택하는 것보다 강한 근거다. [서비스 문서](benchmarks/real-device-gate-prep10/official-sources/SERVICES.TXT.txt), `AOSP-adb.cpp:173–194,1267–1325`·`AOSP-sockets.cpp:103–115,910–937`.

그러나 getprop 응답을 받은 raw stream을 install·launch·pull의 여러 서비스로 자유롭게 재사용하는 공개 CLI handle은 확인되지 않았다. 서비스로 전환된 socket은 해당 stream이며 새로운 host 서비스 세션이 아니다. 하나의 지속 shell에 고정 script를 보내는 설계는 가능 후보지만, 그 안의 check와 action도 순차 실행이고 일반 신원 predicate의 원자성을 새로 제공하지 않는다. 원격 shell/자식이 EOF 때 확실히 종료되는지도 별도 proof다.

일반 client에는 server 자동 기동과 version 불일치 때 restart/reexec하는 경로도 있다. 사전에 server PID를 확인한 다음 새 CLI를 띄우는 것으로 그 경로가 없어지지 않는다. 단일 세션 설계라면 자동 새 server 연결·재기동을 허용하지 않는 강제 경계가 필요하다. [client 소스:235–371](benchmarks/real-device-gate-prep10/official-sources/client__adb_client.cpp.txt). 검토 결과 전체는 [인터페이스 비교 JSON](benchmarks/real-device-gate-prep10/adb-interface-capability-review.json)에 있다.

## 4. 구체 아키텍처 비교

모든 옵션의 12개 평가 항목과 근거는 [아키텍처 비교 JSON](benchmarks/real-device-gate-prep10/architecture-option-comparison.json)에 있다. 다음 표의 보증은 검토 결과이며 운영 자격검증이 아니다.

| 옵션 | 정확한 효력 | 남는 F01 반례 | 비용·권한·개인 데이터 위험 | 판단 |
| --- | --- | --- | --- | --- |
| A. serial + 반복 검사 | 관측한 불일치를 거부하는 best effort | 마지막 probe 뒤 같은 serial의 새 receiver 선택 | 구현 낮음. debugging/USB 권한과 shell authority 필요. 오대상 설치·test package 변경 가능 | 원 계약 불충족 |
| B. transport ID | 같은 server의 특정 객체 선택; 새 USB 객체로의 fallback을 막는 조건부 성질 | server restart/ID 재사용, TCP의 같은 객체 reconnect, 같은 receiver의 신원 조건 변화 | 낮음~중간. A와 같은 phone 권한. 신원·서버·채널 결합을 별도로 증명해야 함 | 독립 해법 아님 |
| C. 단일 USB 노출 + 격리 server, B 병용 | 강제 경계가 실제 동작하면 도달 가능한 대상 집합 제한 | singleton 자체가 승인 phone이 아닐 수 있음; 주소/노드 재사용; 초기 등록·server 교체 race | 중간~높음. host admin의 전용 UID/VM·device/network 정책 준비가 필요할 수 있음. phone root/MDM 불필요. 설치·shell·공유 자원 영향은 남음 | 가장 작은 조건부 ADB 후보 |
| D. 앱 내부 1회 실행 agent | 등록된 앱 인스턴스/UID에서 local action 수행하여 반복 ADB 선택 제거 | 최초 설치·등록이 잘못된 단말이면 이후 key pinning도 잘못된 대상을 인증 | 높음. 전용 APK 설치와 foreground, 합성 통신용 INTERNET만. 범용 관리·background·특별 권한 금지. bootstrap은 별도 위험 | 설치 포함 F01 해법 아님 |
| E. 단일 service stream의 고정 script | 이미 고른 stream에서 check/action 실행하여 새 CLI 선택 일부 제거 | 최초 채널 오대상, check 뒤 predicate 변화, disconnect 뒤 remote action 지속 | 중간. shell 권한은 test UID보다 넓음. 입력·경로·remote 수명 검증 필요 | 원자 조건 API로 간주 불가 |

A/B는 신뢰 host/adbd를 전제로 한 정상 운영 또는 일부 연결 교체 오류를 다룬다. C는 강제 경계와 초기 결합을 입증하고 명시한 신뢰 가정 아래에서만 no-other-target 논증이 가능하다. D는 등록 이후 app-local action을 보호한다. E는 지속 서비스 문맥을 보호한다. 어느 것도 악성 host/admin/kernel/adbd·USB proxy·복제 신원을 일반적으로 방어한다는 증거는 없다.

### C: 격리로 충분해지는 조건과 부족한 조건

대상 수가 하나라는 것은 충분하지 않다. 세션 전체 도달 집합 `Reachable ⊆ {P*}`를 강제해야 한다. 승인 직전 다른 phone이 유일하게 연결되거나 승인 뒤 새 USB 노드가 재사용되면 단일 기기라는 수량 조건은 유지되면서 오대상일 수 있다. USB descriptor·주소·serial만으로 이 초기 결합을 인증하지 않는다. Linux 공식 문서도 descriptor 분류를 강한 인증으로 보지 않는다. [Linux USB authorization](https://docs.kernel.org/usb/authorization.html).

network namespace만으로 USB를 숨길 수 없고, mount에 node 하나만 보이게 하거나 device cgroup에 major/minor를 허용하는 것만으로 물리 신원·재열거 불가를 증명할 수 없다. device cgroup 문서의 접근 단위는 type/major/minor/rwm이다. 이 host가 실제 어떤 cgroup/namespace recipe를 지원하는지는 미검증이며 v1 문서를 현재 host의 지원 증거로 쓰지 않는다. [Linux device cgroup 문서](https://docs.kernel.org/admin-guide/cgroup-v1/devices.html).

실제 후보는 전용 UID 또는 별도 VM, 승인 incarnation의 USB 접근만 허용, 새 열거/주소 재사용 차단, 다른 host ADB socket·네트워크·mDNS·자동 scan 배제, 동일 UID ptrace/fd 전달·후손 interpreter 우회 통제, server 자동 기동·재기동 금지가 함께 필요하다. event watcher가 단절을 관측하면 kill한다는 순서만으로 race를 닫았다고 인정하지 않는다. host root/kernel과 초기 결합 자체를 무엇으로 신뢰할지는 소유자 결정이다.

현재 `require_host_confinement()`에는 namespace 사용 실패 이력과 미자격 launcher가 기록돼 있다. 이번에는 namespace·USB 정책을 시험하거나 변경하지 않았다. 따라서 C를 이 서버에서 바로 실행 가능한 설정으로 제시하지 않는다. R03·R10.

### D: 기기측 agent의 한계와 bootstrap

Android의 UID/process sandbox는 서로 다른 앱의 저장소를 분리하는 공식 platform 근거다. 하지만 현재 `main_devicegate.dart`는 시작 후 합성 smoke를 수행하고 intent의 run ID/package를 확인하는 앱이다. cryptographic enrollment, 소유자의 one-shot 승인, durable 소비 상태나 boot 세대 gate를 제공하는 agent가 아니다. 이를 이미 있는 기능으로 간주하지 않는다. [Android app sandbox](https://source.android.com/docs/security/app-sandbox), R17·R18.

후보 agent는 고정 plan/hash/nonce/expiry를 한 번만 수용하고 자신의 테스트 UID 안의 작업만 수행해야 한다. 앱/OS가 죽거나 결과가 유실되면 세션을 소비/실패 상태로 남기며 재시작·reinstall·replay하지 않는다. 임의 shell·다른 앱 조작·지속 background service·device owner·accessibility·notification 권한을 제공하지 않는다. 앱이 host와 분리되어 계속 실행될 수 있다면 그 local 실행 허용 범위와 중단 의미를 계약에 따로 정의해야 한다. 단절 즉시 정지의 하드 실시간 보증은 없다.

**최초 APK 설치도 mutation이다.** 설치 이후 생성한 앱 key와 화면 challenge는 이후 app 인스턴스 결합에 도움이 될 수 있지만 잘못된 phone에 처음 설치한 문제를 소급 해결하지 못한다. owner가 이미 허용된 로컬 설치 경로로 앱을 직접 설치하고 화면에서 1회 시작하는 변형은 ADB 설치 대상을 없애지만, 기존 승인된 배포 경로가 있다는 증거는 없다. 새로운 unknown-source 설치 허용·외부 배포·계정 사용·특별 권한을 임의로 가정하지 않는다. 수동 bootstrap도 최초 기기 변경에 대한 별도 owner 승인 대상이다.

무선 ADB pairing은 공식 지원되지만 bootstrap·key lifecycle·network 자동 연결 범위를 늘리며 원 identity predicate와 mutation의 transaction을 제공하지 않으므로 선택하지 않는다. [Android ADB guide](https://developer.android.com/tools/adb).

## 5. 증명 가능한 것과 가정에 의존하는 것

| 등급 | 이 작업에서 인정한 범위 |
| --- | --- |
| 저장소에서 확인 | 현재 중앙 무조건 거부, PREP09 독립 종결 기록, 원 mock 반례, 테스트 package/앱 source·historical artifact 신원 |
| 공개 문서의 보증 | serial/transport ID 선택, USB one-device filter, smart socket의 service 연결, Android UID sandbox의 일반 원칙 |
| 고정 소스의 조건부 추론 | server process 내부 ID 배정, 새 USB 객체, TCP 객체 reconnect, selector 우선순위, stream/offline close, client 자동 server lifecycle |
| 미검증 | 설치 binary와 source 대응, 이 host의 강제 USB/namespace/VM 경계, 실제 phone enrollment·OS/ABI·연결 수명, remote action의 수명/예산 |
| best effort | 반복 probe·목록 감시·실패 뒤 kill만으로의 race 축소 |
| 보증 없음 | 침해 platform/악성 USB에 대한 일반 물리 인증, 개인 데이터 손실 확률 0, host disconnect 순간 remote rollback, exit0만으로의 다른 기기 무효과 |

공개 API의 기능과 OS/application을 조합한 안전성 논증은 다르다. 새로운 app key·owner 승인을 추가해도 그 key의 초기 등록 대상이 `P*`라는 독립 근거가 없으면 잘못된 대상을 더 일관되게 인증할 뿐이다. 위험 수용은 이 논증의 결측을 채우는 기술 proof가 아니다.

## 6. 단일 고정 fail-stop 세션의 최소 후보

**현 계약에서 충분히 성립한 최소 해법은 없다.** 비교용으로는 **B+C가 가장 작은 조건부 ADB 후보**다. D의 신규 agent·등록·durable one-shot 상태 구현보다 추가 요소가 적고 기존 F03의 봉인 artifact와 test package 분리를 재사용할 수 있기 때문이다. 다만 초기 binding·강제 격리·신뢰 OS 가정이 남아 있으므로 실행용 권고는 **NONE**이다. 다음 흐름은 미승인 설계 설명이며 executable 또는 새 프로토콜이 아니다.

```text
기기 없는 준비
  → source / 도구 / APK / signer / fixture / plan / 예산 hash 동결
  → 독립 preflight
  → exact manifest와 최초 mutation을 포함하는 소유자 1회 승인
  → 승인 대상 P*와 singleton USB incarnation의 신뢰 등록 [미입증 경계]
  → OS 경계: 전용 UID/VM, 해당 USB만, TCP·다른 server·재열거 배제
  → 고정 server 세대 + 해당 transport 객체
  → 최소 승인 broker의 고정 action + 봉인 artifact
  → test package / private storage / synthetic backend
  → 유한 결과 수집 → 분리 → host 분석

어느 단계든 불일치·단절·시간 초과·취소
  → REVOKED 또는 OUTCOME_UNKNOWN
  → 새 기기 action 없음, 재연결·재선택·자동 정리 없음
  → 이미 받은 host 증거 보존
```

소유자↔plan이 실행 승인 경계이고, Codex↔고정 실행 환경은 연결 전 동결 경계다. OS 격리↔broker는 USB/클라이언트/도구 후손의 도달 경계이며, Android↔test UID는 개인 앱·저장소 경계다. synthetic backend↔production은 별도 데이터·endpoint 경계다. 현재 승인 broker나 phone 등록 경계는 없으므로 그 존재를 가정해 dispatch를 열 수 없다.

승인 상태는 `INIT → OWNER_APPROVED → ENROLLED → RUNNING → COMPLETED` 또는 `REVOKED/OUTCOME_UNKNOWN`으로 모델링한다. 실패 상태에서 같은 세션의 복귀 전이는 없다. physical 연결 세대·server 세대·receiver boot 세대 중 하나라도 바뀌면 새 권한을 만들지 않는다. 이미 승인 action이 원격에서 진행 중이면 정확한 결과가 없다는 사실을 보존하고 같은 action을 다시 보내지 않는다.

실행기·도구·APK·signer·fixture·plan의 exact 신원, 승인된 argv와 앱 상대 경로, 전체/단계 timeout·저장량·로그량·메모리·여유 공간·중단 처분이 모두 고정돼야 한다. 현재 시간·자원 예산과 실제 phone 값의 공란을 임의로 채우지 않았다. 유일한 세션이 실패하면 그 결과가 종료점이며 Codex가 source/APK/target/예산을 고쳐 재시도하지 않는다. R07·R08.

### 실제 적용 전에 남은 전제

1. 소유자가 유지할 invariant, 신뢰 platform, 제외 위협과 초기 등록 증거 기준을 결정해야 한다.
2. 고정 source/binary와 실제 host enforcement recipe, server/client 채널 세대 결합을 입증해야 한다. host admin 변경은 exact 범위 별도 승인이다.
3. phone과 맞는 APK/endpoint 구성이 필요하다. 보존 APK에는 여러 ABI의 의존 라이브러리가 있지만 **Flutter engine은 `lib/x86_64/libflutter.so`만 확인**됐다. phone ABI는 조사하지 않았다. 현재 앱은 emulator의 `10.0.2.2:18081`만 허용한다. 이것들을 Galaxy 준비 완료로 간주하지 않는다. R17·R20·R26.
4. 전용 package `kr.re.hjkerman.money_note.devicegate`, 독립 signer·private storage, backup/transfer 제외·component/permission admission을 유지해야 한다. 기존 test package가 있으면 자동 clear/uninstall하지 않고 중단해야 한다. production ID 갱신·broad rm·공유 저장소 정리는 허용하지 않는다. R07·R19·R20.
5. 구체 구현 milestone에서 필요한 독립 검증이 끝난 뒤에만 최초 설치부터 포함하는 exact 실행 승인을 별도로 받아야 한다. 설계 C 판정은 이 승인이 아니다.

F03 종결은 artifact 구조·서명·봉인 바이트 전달 보증이다. phone ABI·endpoint 적합성, 설치 대상 identity, 새 agent 승인을 포함한 보증으로 확장하지 않았다. 해당 전제의 미완료를 기존 F03 재개방이나 이번 구현 결함 수정으로 표현하지 않는다.

## 7. 개인 Galaxy S23 FE 보호와 남는 위험

개인 앱·사진·알림·계정·금융 데이터는 조사하거나 복사하지 않았다. 후보 설계에서도 별도 테스트 package/signing/storage와 신규 합성 backend·fixture만 사용해야 한다. 생산 포트 18080, 운영 credential/DB/Snapshot, 전체 앱 목록·logcat·dumpsys/bugreport는 사용하지 않는다. test package의 사전 허용 상대 파일과 자기 로그만 bounded하게 수집한다. R07·R24.

factory reset, bootloader 변경, root, 기기 전체 정책 변경, 알림·배터리 예외·설치 특별 권한·관리 권한, 개인 앱 clear/uninstall과 광역 storage 삭제는 선택지에 포함하지 않는다. host 격리 준비가 필요하면 phone 정책을 바꾸는 우회 대신 host의 exact 변경을 별도 심사해야 한다. 물리적으로 phone을 소유하거나 cable을 잡고 있다는 사실만으로 software target identity가 입증되지는 않는다.

| 잔여 위험 | 이번 판단과 필요한 처분 |
| --- | --- |
| 초기 오대상 등록·serial/descriptor 위장 | 현재 미해결. 단일 USB·사후 key pinning만으로 제거되지 않음 |
| server 교체·ID 재사용·짧은 단절 | actual channel/OS 세대 결합 proof 필요. polling 성공을 원자성으로 승격하지 않음 |
| 이미 수신된 설치·앱 작업 | host kill/단절 뒤 완료될 수 있으므로 결과 모호 시 UNKNOWN. 자동 replay/clear/uninstall 금지 |
| 올바른 테스트 앱의 자원 소비 | 저장공간·열·배터리·memory/OS 오류는 shared hardware 영향. 개인 데이터 손실 0을 보증할 수 없음 |
| 침해된 platform·USB proxy | 검토 옵션의 보증 밖. 제외 여부는 별도 소유자 결정이며 현재 수용되지 않음 |
| 제한 증거의 부족 | 증거가 없으면 FAIL/UNKNOWN을 유지. 수집 범위를 넓히거나 기기에 다시 연결하지 않음 |

현재 차단 상태에서는 이번 작업으로 발생한 기기 데이터 노출이 없다. 향후 잔여 위험의 확률이나 실제 단말 상태는 측정하지 않았다. [위험 register](benchmarks/real-device-gate-prep10/residual-risk-register.json)의 모든 `accepted_by_owner`는 false다.

## 8. 별도 계약 변경 제안 — 적용하지 않음

**F01-PROPOSAL-G1: PROPOSED ONLY — NOT APPLIED.** 아래는 원 F01이 이미 이 의미였다는 해석이 아니라 별도의 대체 계약안이다. [기계 판본](benchmarks/real-device-gate-prep10/proposed-contract-amendment.json).

> 소유자가 exact manifest로 승인한 단말 P*에 독립적으로 결합된 단일 USB incarnation과 신뢰 host/server/Android 아래에서, executor의 모든 기기 변경은 승인된 test package·action·artifact에만 도달해야 한다. 다른 transport/단말로의 재선택·연결 권한 승계를 금지한다. 단절·재등록·server/receiver 세대 변화·취소·실패에서는 권한을 영구 폐기하고 새 action을 보내지 않는다. 이미 수신된 action의 완료 여부가 불명확하면 UNKNOWN으로 보존하며 재실행·자동 삭제를 금지한다.

차이는 receiver 신원과 mutation의 원자적 결합 proof를 **명시 신뢰 가정 + 초기 대상 결합 proof + no-other-target/엄격 승인**으로 대체하는 데 있다. host admin/kernel/ADB/adbd/Android 신뢰, 악성 USB relay·복제 신원·침해 platform 제외 여부, material 신원의 boot 세대 내 안정성, 최초 `P*` 결합의 수용 증거, 이미 수신된 action의 UNKNOWN 처분을 소유자가 각각 결정해야 한다.

원 요구의 종결·수정 완료로 표시하지 않으며 normative 파일·binding/B03 protocol은 변경하지 않았다. G1이 승인되더라도 초기 결합·OS 강제 경계·구현 proof가 비어 있으면 실행은 계속 차단한다. 잔여 위험을 수용했다는 서명은 미입증 원자성이나 no-other-target을 기술적으로 증명하지 않는다.

## 9. 소유자 선택과 유한한 다음 단계

[소유자 선택 JSON](benchmarks/real-device-gate-prep10/owner-decision-options.json)에 승인 범위와 정확한 문안을 제공한다. 현재 기본값은 **O1**이며 소유자 응답을 받은 것으로 간주하지 않는다.

| 선택 | 소유자가 결정할 정확한 범위 | 승인으로 따라오지 않는 것 |
| --- | --- | --- |
| O1 | 원 F01 계약과 실행 차단 유지. 새 조사/구현/기기 접근 승인 없음 | 원자성 종결·실행 GO |
| O2 | 원 계약을 유지한 채 device/emulator/ADB 없는 B+C mock 조사만 별도 승인 | 실제 OS USB isolation proof·phone 안전·운영 source 변경 |
| O3 | G1 문구·신뢰 가정·제외 위협·initial binding 증거·in-flight UNKNOWN을 항목별 심의 | 원 F01 종결·구현 완료·실제 실행·단순 위험 수용에 의한 기술 proof |

O2를 선택할 때만 최대 1개 모형, 최대 12개 고정 trace, 최대 1시간, 총 산출물 10MiB의 in-memory 두 receiver 조사를 허용하는 별도 범위를 제시한다. 마지막 probe 뒤 변화, 같은 serial 새 객체, server restart/ID 재사용, 같은 ID TCP reconnect, 단절·응답 유실·취소·artifact drift·wrapper·다른 endpoint 등을 한 번씩 판정하고 PASS/FAIL과 증명 범위·남은 반례를 반환한다. 실제 ADB·USB·emulator는 필요하지 않다. mock PASS는 실제 USB/phone 보증으로 승격하지 않는다. 실패하면 구체 반례와 결정을 반환하며 자동 수정·반복 감사는 없다.

**이번에 선택한 다음 단계는 O2 실행이 아니라 공식 안전 계약 결정 대기다.** 원 계약을 유지한다면 충분한 결합 proof 없는 운영 경로는 계속 차단한다. O3를 심의한다면 승인된 문구를 적용하는 별도 작업과 구체 implementation/proof milestone이 필요하다. 그 milestone이 없는 독립 재감사를 반복 예약하지 않는다. 현재 어느 조사·구현도 추가 승인되지 않았다.

별도 승인 대상은 계약 결정, 조사/구현 범위, 필요할 경우 host admin 변경, phone용 APK/agent·합성 endpoint 변경, 그리고 독립 proof 완료 후의 exact 1회 세션이다. 실패 후 추가 수집·재연결·정리는 자동 연장된 권한이 아니다. [다음 행동 결정](benchmarks/real-device-gate-prep10/next-action-decision.json).

## 10. 검증·산출물·보존

| PREP10 작업 | 결과 |
| --- | --- |
| 저장소/공식 소스 정적 검토 | 요구·source hash·공식 revision/URL·한계 기록 |
| ADB host 전용 help/version | 2회, exit0; live discovery/selection/device request 0 |
| 웹 `npm run build` | PREP10 전용 사본에서 exit0 |
| backend 기존 소형 회귀 | 신규 합성 임시 DB에서 exit0, 72 tests·44 subtests 통과 |
| PREP09의 144/144·별도 16/16 | 역사 결과로 보존; PREP10 재실행 집계 아님 |
| Android build/install·emulator·실기기·large-N | 모두 미실행 |
| 새 executor·운영 source/protocol 변경 | 없음 |

웹/backend 명령·cwd·환경 격리·압축 로그·JUnit은 [저장소 검증](benchmarks/real-device-gate-prep10/repository-validation.json)에 보존했다. 성공 로그 전체를 출력하지 않았다. 기본 shell sandbox는 기존과 같은 bwrap loopback 초기화 실패였으며 승인 검토된 host 실행 경로를 사용했다. host-only 검증의 권한을 devicegate dispatch 허가로 사용하지 않았다.

필수 기계 파일 7개는 다음과 같다.

- [F01 불변식과 위협 모델](benchmarks/real-device-gate-prep10/f01-invariant-and-threat-model.json)
- [ADB 인터페이스 능력](benchmarks/real-device-gate-prep10/adb-interface-capability-review.json)
- [아키텍처 옵션 비교](benchmarks/real-device-gate-prep10/architecture-option-comparison.json)
- [권고 아키텍처 결정](benchmarks/real-device-gate-prep10/recommended-safety-architecture.json)
- [잔여 위험 register](benchmarks/real-device-gate-prep10/residual-risk-register.json)
- [소유자 결정 선택지](benchmarks/real-device-gate-prep10/owner-decision-options.json)
- [단일 다음 행동 결정](benchmarks/real-device-gate-prep10/next-action-decision.json)

작업 전 기존 파일 **7,432개**의 bytes/mode/symlink와 HEAD·branch·Git index·staged identity를 고정했다. 종료 대조에서 기존 파일 변경·삭제·mode drift가 없고 외부 원 B03 sidecar 5개도 보존됐다. index SHA-256은 전후 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged identity SHA-256은 전후 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. [보존 결과](benchmarks/real-device-gate-prep10/preservation.json).

필수 검증의 사본·build 출력·소형 합성 임시 DB·npm cache는 PREP10 소유 scratch 하나에서 만들고 모든 검증 process 종료 후 그 scratch만 정리했다. 보고서·기계 결정·공식 소스 사본·도구 출력·압축 로그·JUnit·검증/문서 조립 helper는 증거로 보존했다. 기존 SDK/AVD/APK/cache·역사 증거·다른 작업 파일·source lock은 정리하지 않았다. 생성/삭제 파일 수와 회수 용량은 [정리 기록](benchmarks/real-device-gate-prep10/artifact-cleanup.json)에 있다. 대형 benchmark 산출물 정리는 **NOT APPLICABLE**이다.

새 파일은 이 보고서와 PREP10 증거 디렉터리로 한정한다. reset·stash·clean·checkout·rebase·restage·commit·push는 수행하지 않았다. **N01/F02/F03/FC01 독립 종결 보존, T6.9 DEFERRED, formal T6.6F closure NOT AUTHORIZED, R1 CLOSED, production deployment NOT AUTHORIZED**다.

**최종 분류: C — SAFETY CONTRACT DECISION REQUIRED. 운영 dispatch와 기기 접근 차단을 유지한 채 소유자가 원 F01 계약 유지 또는 별도 G1 계약안 심의 여부를 명시적으로 결정한다.**
