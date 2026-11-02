# G1-A01 후속 — 정적 플랫폼 실행 가능성·단일 S23 FE 재평가

**판정: BLOCKED 유지.** 개인 Galaxy S23 FE 한 대만 사용하는 조건은 다른 실물 Android가 필요한 운영 이력을 줄인다. 그러나 같은 S23 FE의 USB·ADB·수신자 세대 변화와 폐기된 권한의 큐/FD를 통한 새 제출은 여전히 가능성 검토 대상이다. 현재 검토한 Linux USBFS/stock ADB 인터페이스에서 이 전체 경계를 강제하는 지원 메커니즘을 확인하지 못했다. 새 구현안이나 구현 일정은 제안하지 않는다.

유효 G1 SHA-256은 `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`로 재확인했다. 원 F01·G1 S1/S3/G1-04–11·PR03–07은 그대로 구속된다. 이전 A01·PREP09·FS1은 역사 기록으로 보존한다. 이번 owner 결정은 정적 조사와 단일 기기 운영 조건만 부여하며 연결/read-only·설치·기술 수용이나 AS01–AS06 전체의 승인이 아니다. [승인 범위·현재 소스 신원](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/owner-scope-and-source-identities.json).

**조사 범위와 하나의 선정 메커니즘**

공개 upstream Linux **v6.8**의 `urb.c`, `hcd.c`, USBFS UAPI, device cgroup 소스 4개와 공식 문서 2개를 새로 고정하고, 기존 v6.8 `devio.c` 및 고정 AOSP selector/reset 소스를 읽었다. 실제 Ubuntu patched kernel/Google ADB binary와 이 소스의 build 대응은 인증하지 않았다. 모든 가능한 커널·플랫폼의 불가능성을 주장하는 결론이 아니다.

선정해 검토한 구체 메커니즘은 kernel driver API **`usb_poison_anchored_urbs()`**다. 같은 anchor에 연결된 URB를 poison하고 이후 그 anchor에 추가되는 URB도 poison한다. 개별 `usb_poison_urb()`는 `reject`를 올려 재제출을 `-EPERM`으로 막고 로컬 완료 handler 종료를 기다린다. `usb_unpoison_*`로 풀 수 있으므로 불가역 권한 정책은 별도다. 사용 문맥/수명 제약도 있다. [Linux 공식 API](https://www.kernel.org/doc/html/v6.8/driver-api/usb/usb.html#c.usb_poison_anchored_urbs), [고정 urb.c:127/746/846](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/official-sources/linux-v6.8-urb.c.txt).

실제 거부 지점은 [hcd.c:1132–1169](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/official-sources/linux-v6.8-hcd.c.txt)의 `urb->reject` 검사다. 이는 polling 관례보다 강한 kernel 집행이다. 다만 모든 전송이 같은 anchor를 사용하고 다른 anchor/새 URB/다른 FD·ADB 경로와 unpoison을 배제하는 것은 호출 driver의 별도 책임이다. anchor의 기존 URB는 순차 처리된다. 처리 시작/완료를 앞서 발생한 G1 무효화 사건과 동일시할 수 없다. 실제 사건과 전체 제출 경계의 직렬화 근거가 없으면 전체 보증이 되지 않는다.

이 기능은 **USBFS userspace 권한 폐기 API가 아니다.** [v6.8 UAPI:187–229](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/official-sources/linux-v6.8-usbdevice_fs.h.txt)와 `devio.c` 제출 경로에 G1 권한/세대와 위 anchor를 결합하는 인터페이스는 없다. Linux에 재제출 차단 primitive가 없다는 뜻이 아니라, 그 부분 기능이 현 G1 실행 경로 전체를 충족하지 않는다는 뜻이다. [정확한 파일 SHA·공식 URL](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/official-source-provenance.json).

| 실제 인터페이스 | 확인한 보장 범위와 한계 |
| --- | --- |
| `USBDEVFS_DISCARDURB` | `devio.c:2005–2027`은 지정 pending URB를 `usb_kill_urb()`로 정리한다. 새 SUBMITURB·다른 FD·ADB 큐를 같은 session 권한으로 영구 거부하는 latch는 아니다. |
| `USBDEVFS_DROP_PRIVILEGES` | `devio.c:2534–2550`은 허용 interface mask를 단방향 축소한다. 이미 claim한 interface는 `checkintf:838`/`claimintf:779`에서 먼저 허용하므로 mask0도 기존 I/O 전체 폐기라고 해석할 수 없다. |
| `close(fd)` | FD 하나의 제거와 마지막 file 참조의 release는 다르다. Linux에서는 진행 중 syscall의 참조로 I/O가 close 뒤 완료될 수도 있다. 원격 작업 종료 보증은 없다. [Linux close(2)](https://man7.org/linux/man-pages/man2/close.2.html) |
| device cgroup BPF | type/major/minor/access에 대한 device 접근 제어다. 이미 보유한 FD·ADB queue·plan/generation 전체를 폐기하는 API가 아니다. [공식 cgroup 문서](https://www.kernel.org/doc/html/v6.8/admin-guide/cgroup-v2.html#device-controller) |

위 USBFS 판단은 보존 [devio.c](benchmarks/real-device-gate-g1-a01/official-sources/linux-v6.8-devio.c.txt)의 정적 경로 분석이며 syscall을 실행한 시험 결과가 아니다.

**서로 다른 여섯 경계**

| 경계 | 이번 판단 |
| --- | --- |
| D1 host-side submission cutoff | 선정 API는 해당 URB/anchor의 재제출 차단만 제공. 실제 G1 무효화와 모든 retained queue/새 요청의 acceptance를 결합한 전체 경계 미확인. |
| D2 이미 진행 중인 kernel/USB 전송 | 취소/poison은 로컬 완료 정리 범위. 이미 일부 bytes 전달 가능. G1 예외는 무효화 전 같은 action/receiver/channel에 실제 제출됐음이 귀속된 bounded bytes에 한정. URB enqueue만으로 그 귀속을 자동 수용하지 않음. |
| D3 Android에 이미 전달된 명령 | 전송 중단은 전달된 명령의 회수/미실행/rollback 증거가 아님. ACK·commit·종료를 분리. |
| D4 분리 뒤 계속되는 device-side 작업 | 이미 제출된 동일 bounded task는 지속 가능. 결과/종료 미입증은 UNKNOWN_QUARANTINED, late ACK로 권한 복구 없음. |
| D5 최초 물리 기기 등록/신원 | 단일 S23 FE라는 owner 진술은 유용한 사전 식별 문맥. P→U→실제 C/R의 설치 전 신뢰 등록 증거·독립 CP/IP는 별도. 불변 제조사 인증서가 유일한 허용 수단이라고 새로 요구하지 않음. |
| D6 승인 단말만 도달하는 OS 강제 | 한 P/한 incarnation만 허용하는 최소 device/IPC/network/FD 정책으로 단순화 가능하나 전면 매개와 재획득 방지 수용을 제거할 수 없음. 현재 정책 미자격. |

호스트 큐/메모리의 예약과 해당 action/receiver/channel에 실제 제출된 bounded bytes는 다르다. `t_event < 새 제출 < watcher 관측/kill`을 막았다는 근거가 없는데 관측 뒤 fail-stop한 것만으로 합격시킬 수 없다. 첫 APK chunk 제출을 남은 전체 APK/후속 action의 제출로 간주하지 않는다. 반대로 무효화 전에 실제 제출된 범위의 후속 전송·작업까지 즉시 멈춰야 한다는 새 요구도 만들지 않는다.

[libusb 공식 취소 계약](https://libusb.sourceforge.io/api-1.0/group__libusb__asyncio.html#cancellation)은 취소 요청과 완료 callback을 구별하며, 취소 때 이미 일부 데이터가 전달됐을 수 있음을 명시한다. USB reset·FD close·cancel·transport disconnect는 Android 명령의 미실행/원격 종료/rollback을 입증하지 않는다. 결과나 remote 종료가 미확정이면 **UNKNOWN_QUARANTINED**, 실제 폐기 후 금지 제출이 확인되면 **FAIL_VIOLATION**이다. 늦은 ACK도 권한을 복구하지 않는다. 추가 readback/reconnect/stop/clear/uninstall로 자동 회복하지 않는다.

**단일 기기 가정이 바꾸는 것**

소유자의 한 대 조건은 **운영 가정**으로 반영한다. 그 가정이 실제로 지켜지는 이력에서는 다른 Android의 동시 연결·의도적 교체·다른 실물의 serial 복제 분기가 제외된다. 이는 OS가 그런 접속/대상을 기술적으로 막는다는 증거가 아니다. 제3자/relay/host 침해 배제나 모든 USB/TCP 경로의 안전을 추가로 승인한 것으로 읽지 않는다.

| 기존 A01 이력 | 단일 기기 조건에 따른 재분류 |
| --- | --- |
| T01 — 조건부 운영 제외 | 다른 실물 Android를 동시에 연결하는 이력은 owner 단일 기기 가정이 지켜지는 동안 제외. 기술적 접속 차단이 입증된 것은 아니며 PR06은 유지. |
| T02 — 분기별 구분 | 다른 Android로 의도적 물리 교체는 가정 밖. 동일 S23 FE의 분리/재연결·새 USB incarnation과 권한 승계 위험은 유지. |
| T03 — 분기별 구분 | 두 번째 실물 Android의 serial 복제 분기는 가정 밖. serial이 P/U/C 인증이 되지는 않으며 동일 기기의 재등록/옛 식별 자료 재사용은 유지. |
| T04 — 유지 | 같은 S23 FE에서도 transport 객체 소실·ID 재사용·옛 channel 귀속 가능. |
| T05 — 유지 | 같은 S23 FE에서 ADB server/client restart·ID/PID/주소 재사용 가능. |
| T06 — 유지 | 같은 물리 기기의 USB reset/재열거는 새 승인 세대 문제. |
| T07 — 유지 | host 중단·예약/검증 뒤 queue·FD 참조·writer가 남는 문제는 기기 수와 독립. |
| T08 — 유지 | 이미 받은 원격 task 지속·ACK 유실/late ACK는 같은 기기에서도 발생. |
| T09 — 유지 | 동일 phone의 test package/signer/설치 instance 교체. |
| T10 — 유지 | 같은 test UID에서 duplicate intent·재생성·old plan replay. |
| T11 — 분기별 구분 | 없는 두 번째 phone으로의 effect 분기는 가정 밖. 다른 process/server/socket/retained FD가 같은 phone의 승인 외 channel에 접근하는 우회는 유지. |
| T12 — 유지 | 동일 P라도 위조/과거 owner·enrollment·generation 증거는 현재 authority가 아님. |
| T13 — 유지 | APK/backend/artifact·종단 치환은 단말 수와 독립. |
| T14 — 유지 | 유효 manifest는 같은 phone의 올바른 boot/adbd/stream/앱 task 수신자까지 보증하지 않음. |

운영 분기 제외는 필수 proof 면제가 아니다. 현 G1의 PR03 wrong-singleton·PR04 두 target 효과 관측·PR06 우회 불가 메커니즘 증거는 남는다. 개인 캠페인에 두 번째 Android를 연결하라고 요구하지 않는다. 별도 lab 대체물로 검증할 수 있는 부분과 그 결과의 개인 P 적용성은 독립 심사 대상이며, 이번에 그 시험을 실행·승인하지 않았다. [14개 이력 재평가](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/single-device-reassessment.json).

**전용 ADB·fail-stop·고정 plan·앱 실행은 충분한가**

**조합해도 현 계약의 충분조건이 아니다.** `-t`는 같은 server 세대의 객체 선택 보조이며 serial과의 AND 인증도 아니다. 같은 phone에서도 server/TID/USB/adbd가 바뀐다. fail-stop은 실제 사건에 맞춘 제출 차단이 필요하고, 고정 plan은 bytes/효과를 제한할 뿐 현재 receiver 권한을 인증하지 않는다. 앱의 durable one-shot는 재생성/replay를 줄이지만 최초 APK 설치의 binding이나 host write cutoff는 해결하지 않는다. [고정 ADB selector:81](benchmarks/real-device-gate-prep10/official-sources/client__adb_client.cpp.txt), [reset 재처리:754](benchmarks/real-device-gate-prep10/official-sources/client__usb_libusb.cpp.txt).

OS 격리는 **동적 다중 기기 선택·자동 discovery·기기 간 권한 전환을 제거하고 한 P/한 incarnation만 허용하는 정적 구성**으로 단순화할 수 있다. 계약은 container·namespace·BPF 전부를 동시에 요구하지 않는다. 최소한 전용 비특권 실행 주체, 승인 자원만 노출, 새 open/import/reconnect와 다른 server/IPC/network/후손 경로 차단을 실제 OS가 강제하는 한 구성이 입증돼야 한다. 단일 node나 major/minor는 재사용될 수 있고 기존 FD를 폐기하지 않는다. 현재 충분성이 확인된 구성을 선정하지 못했다.

**가장 작은 현재의 방어 가능한 구조는 기존 전면 DENY뿐이다.** 실행을 허용하는 최소 구조에는 설치 전 신뢰 등록, 동일 세대의 actual resource/recipient 결합과 폐기 경계, OS 전면 매개가 모두 남는다. 고정 plan·격리 앱·UNKNOWN 정책·독립 CP/IP/POST 수용도 유지된다. 불변 제조사 인증서를 유일한 등록 수단으로 새로 요구하지 않으며, 소유자의 적격 OOB 확인을 평가할 여지는 있지만 한 대라는 진술만으로 P→U→C/R 입증을 대체하지 않는다.

**유한 결론과 권고 결정 하나**

이번 조사로 확인하지 못한 핵심 보증은 **실제 세대 무효화 사건 이후, retained/queued host 자원까지 포함한 모든 새 command/write acceptance의 차단**이다. 지금 확인한 USBFS/stock ADB 인터페이스를 그대로 두고 단일 기기 약속·selector·watcher/kill·선예약을 충분하다고 선언하려면 원 F01/G1을 축소해야 하므로 그렇게 판정할 수 없다. 다른 지원된 구현이 원계약을 만족할 가능성을 부정하는 것은 아니지만, 이번에는 새 driver/broker 구현을 가정해 공백을 채우지 않는다.

따라서 이전 **BLOCKED 판정은 바뀌지 않는다.** 세 비면제 보호와 독립 기술 proof는 미수용이며 **0/12**를 유지한다. 권고하는 다음 소유자 결정은 **“원 F01/G1을 그대로 유지한 채 G1 실기기 캠페인의 보류를 확정한다”** 하나다. 추가 추측 구현·자동 재조사·기기 실행으로 넘어가지 않는다.

이번에는 공개 소스/문서 읽기·hash/AST·문서 정합성 확인만 했다. 최신 승인인 정적 조사 제한에 따라 npm/backend build/test도 실행하지 않았으며 과거 PASS를 새 proof로 집계하지 않았다. ADB(help/version 포함)0·emulator0·USB/기기 열거/접근0·설정/권한/udev/namespace/kernel 변경0·구현0·기술 수용0·commit/push0이다. FS1 및 N01/F02/F03/FC01 독립 종결, B03·T6.9 DEFERRED·R1 CLOSED·production 미승인은 보존한다. 새 공개 소스는 실행하지 않는 `.txt` 분석 사본이다. 임시 DB/build/cache 생성·삭제는 해당 없다.

종료 대조에서 기존 8,225개 경로·외부 frozen sidecar5개·source lock27개·HEAD/index/staged가 모두 보존됐다. 보존 결과와 신규 문서의 hash는 [보존·정적 검사](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/validation-and-preservation.json), [증거 manifest](benchmarks/real-device-gate-g1-a01-static-platform-reassessment/evidence-manifest.json)에 기록한다. 이 문서는 원 A01 보고서나 계약을 덮어쓰지 않는 후속 정적 재평가다.
