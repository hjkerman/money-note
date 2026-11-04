# Real-Device Gate PREP07 — N01 수정·F01 실행 차단·설계 경계 독립 검토

**최종 판정: FAIL — UNSAFE DISPATCH OR ORPHANED CHILD REPRODUCED.**

세 결정은 다음과 같다.

| 대상 | 독립 판정 |
| --- | --- |
| PREP05-N01 자식 수명 수정 | **INDEPENDENTLY CLOSED** |
| F01 fail-closed 실행 경계 | **FAILED** |
| F01 원자적 신원 결합 해결 | **UNRESOLVED** |

원 N01 두 재현과 후손을 포함한 외부 controller 관측에서 부모 종료 뒤 생존 자식·추가 쓰기는 없었다. 반면 일반 `run/start` helper는 첫 실행 파일의 basename만 `adb`와 비교한다. 같은 ADB 파일을 다른 symlink 이름으로 지정하거나 env/sh/Python으로 감싸면 authority 검사 없이 subprocess 생성 지점까지 도달했다. 이를 **PREP07-FC01 · HIGH**로 기록한다.

모든 위험 argv는 **Popen 직전 가로채 실제 exec를 막았다**. 실제 ADB 호출·emulator 조작·물리 기기 접근은 전부 0회다. FAIL은 unsafe dispatch 경로가 재현됐기 때문이며, N01 orphan 재발이나 실제 단말에서 mutation 완료를 관측한 것은 아니다. Real-Device Gate 전체 PASS나 기기 실행 권한을 부여하지 않는다.

## 1. 독립성·범위·기준선

검토자는 기존 PREP03/PREP05 독립 감사 세션이며 PREP06 구현에 참여하지 않았다. **REVIEWER INDEPENDENCE: SATISFIED.** PREP06의 46/46을 독립 수용으로 간주하지 않고 실제 source와 원 재현기, 실패 경로를 다시 검사했다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 시험 전에 기존 파일 **7,215개**의 내용·mode, Git index와 staged path/mode/blob identity를 고정했다. 기존 tracked 수정 13개와 미추적 자료를 유지했다. [시작 기록](../../../benchmarks/real-device-gate-prep07/preservation-before.json), [최종 보존 결과](../../../benchmarks/real-device-gate-prep07/preservation.json).

AGENTS, development-artifact-hygiene, 필수 프로젝트·도메인·알려진 이슈·서버 authority 경계, PREP03–PREP06 보고서·finding 정의·원시 재현·변경 inventory·현재 devicegate source를 적용했다. 금융 projection은 서버 authority로 유지하며 모바일 금융 계산·B03·binding protocol에 새 의무나 구현 변경을 넣지 않았다.

허용된 검토는 정적 분석, mock dispatch interception, controlled host child와 관련 회귀뿐이다. 제품·harness·기존 테스트 source를 수정하지 않았고 F01 workaround나 새 실행기를 구현하지 않았다.

## 2. 원 요구와 PREP06 변경의 신원

[requirements-reconstruction.json](../../../benchmarks/real-device-gate-prep07/requirements-reconstruction.json)에 시험 전 원 정의를 보존했다.

- **F01 · HIGH:** 같은 serial의 재등록이나 마지막 조회 뒤 변화가 검증 권한을 다른 대상에 넘기지 않아야 한다. 승인 transport/server와 실제 mutation 수신자를 결합하고 소유 emulator 외 USB/TCP 접근을 배제해야 한다. 원 소프트웨어 신원 변화 모델은 실제 phone 치환 증거가 아니다.
- **PREP05-N01 · HIGH:** `run.finally → stop_group`의 SIGTERM 유예 중 추가 취소가 SIGKILL·wait/reap·증거 저장을 건너뛰고, 등록되지 않은 자식이 부모 종료 뒤 쓰기를 계속했다. 종료·reap·증거 저장을 보호하고 종료를 확인하지 못하면 후속 실행을 차단해야 한다.
- **F02/F03:** PREP05에서 각각 호스트 HTTP 경계와 APK 구조·sealed 바이트 경계로 독립 종결됐다. 번호와 종결 범위는 유지했다.

PREP06의 `smoke.py`, `guards.py`, `test_prep06.py` SHA와 최종 source archive 3개가 현재 파일과 일치했다. F02/F03 보호 block 10개의 AST 원문 해시, 정책 JSON과 기존 `test_remediation.py`도 일치했다. [source-provenance.json](../../../benchmarks/real-device-gate-prep07/source-provenance.json).

N01 변경은 spawn 취소 전 자식 등록, 정리·강제 종료·reap·진단 저장 전체의 취소 지연, 종료 proof와 subreaper/pidfd 회수, 확인 실패의 sticky 차단이다. F01 변경은 전용 device 함수 및 정규 ADB argv의 직접 wrapper 호출 앞에 `require_device_authority()`를 추가한 것이다. 이 두 보강을 각각 평가했다.

## 3. N01 독립 검증 — 종결

**N01 CHILD LIFECYCLE: INDEPENDENTLY CLOSED.** [개별 결정](../../../benchmarks/real-device-gate-prep07/n01-independent-verification.json).

원 PREP05 `cancellation-probe.py`는 출력·scratch 경로만 바꿔 다시 실행했다. 실제 `run/execute/finish`를 쓰고 preflight의 작업만 감사 소유 host writer로 대체하는 원 재현 조건을 유지했다.

| 원 재현 조건 | 부모 종료 시 marker | 0.16초 뒤 marker | 생존 자식 |
| --- | --- | --- | --- |
| 첫 취소 정리 중 두 번째 signal | 30바이트 | 30바이트 | 없음 |
| timeout 정리 중 signal | 145바이트 | 145바이트 | 없음 |

원 재현은 **2/2 통과**했다. [원 재현 결과](../../../benchmarks/real-device-gate-prep07/original-n01/cancellation-independent-results.json).

PREP06 집중 회귀를 별도 PREP07 경로에서 실행했다. Lifecycle 17개 중 controller 관측 10건은 초기 취소, 반복 취소, timeout, 같은 group의 후손, `setsid()`로 이탈한 후손, reap 중 취소, 증거 저장 중 취소, background `start` 정리, spawn 중 취소와 종료 acknowledgement 유실을 포함했다. controller가 관측한 자식/후손 PID 12개는 부모 종료 직후 모두 부재였고 marker 증가도 0이었다. [controller 결과](../../../benchmarks/real-device-gate-prep07/focused/cancellation-lifecycle-results.json), [raw 관측 archive](../../../benchmarks/real-device-gate-prep07/controller-observations.tar.gz).

자식은 SIGTERM을 무시하도록 만들어 강제 종료를 필요로 했다. 실제 proof에 SIGKILL, leader exit code·reap, descendant reap, process-group 부재와 새 subreaper adoption 부재가 기록됐다. 이 내부 proof만 믿지 않고 바깥 controller의 PID 부재·marker 무증가와 대조했다.

실패 경로도 확인했다. `ECHILD`만으로 살아 있는 group의 종료를 인정하지 않고 확인 deadline 뒤 `ChildCleanupFailure`가 발생했다. pidfd/subreaper capability가 없으면 spawn 전에 거부했다. 실제 종료 뒤 acknowledgement 유실을 주입하면 `CHILD_TERMINATION_UNCONFIRMED`가 유지되고 이후 `run/start/mutation`은 거부됐다. kernel 차원의 영구 종료 불가 상태를 실제 만들었다는 주장은 아니다.

관련 위치는 `smoke.py:192`의 등록, `:208`의 proof 검사, `:277`의 취소 보호 정리·저장, `:673`의 outer fallback, `guards.py:26,273,302`의 취소 지연·adoption 회수·종료 proof다. 전용 Linux 단일-owner executor이며 같은 interpreter에서 unrelated subprocess를 병렬 생성하지 않는 기존 전제 내에서 N01을 수용한다. 이 수용은 F01 해결과 별개다.

## 4. F01 정적 reachability

[reachability 결과](../../../benchmarks/real-device-gate-prep07/f01-fail-closed-reachability.json)의 결론은 **FAILED**다.

| 경로 | 현재 동작 |
| --- | --- |
| `main → execute → preflight` | `require_host_confinement()`가 먼저 실패해 build/backend/ADB 전 중단 |
| `boot()` 직접 호출 | 같은 guard가 ADB server·emulator 시작 전 중단 |
| `verify/mutate/read_device` 직접 호출 | `require_device_authority()`가 현재 미자격 상태를 거부하고 권한 폐기 |
| `application → install_verified_apk → mutate` | 전용 device 경계에서 차단 |
| 기존 package 제거·로그·결과 조회·shutdown | `read_device/mutate`를 거쳐 차단 |
| `run/start`에 정규 basename `adb` 전달 | authority 거부, Popen 0회 |
| `run/start`에 alias 또는 wrapper 전달 | **authority를 건너뛰어 Popen에 도달** |

`require_host_confinement()`는 환경·설정 파일을 읽지 않고 무조건 raise한다. CLI에도 우회 option은 없다. Target 발견, transport 값이나 가상의 qualification 필드를 채워도 현재 guard는 권한을 발급하지 않았다. `--check-result`는 host JSON 판정 경로이며 device mutation을 실행하지 않는다.

따라서 정상 CLI와 전용 device 함수에 한정하면 차단은 유효하다. 그러나 이번 요구에는 import한 내부 helper를 직접 호출하는 경로도 포함되므로 위 결과만으로 전체 경계를 수용할 수 없다.

## 5. 신규 finding — PREP07-FC01 · HIGH

**제목:** 일반 `run/start`의 basename 판별로 비자격 ADB dispatch가 도달 가능하다. [finding register](../../../benchmarks/real-device-gate-prep07/finding-register.json), [독립 interception 결과](../../../benchmarks/real-device-gate-prep07/dispatch-interception-results.json).

정확한 영향 위치는 `smoke.py:232–233`과 `:318–319`의 판별, `:251`과 `:325`의 Popen이다. 첫 argv의 `Path(...).name == ADB.name`일 때만 device authority를 요구한다.

독립 시험은 실제 SDK ADB와 같은 device/inode를 가리키는 task-owned symlink를 만들었다. 이름은 `sdk-tool-alias`다. 다음 입력들은 `run`과 `start` 양쪽에서 모두 authority 없이 subprocess 생성 지점에 도달했다.

- 같은 ADB inode의 다른 이름 symlink.
- `/usr/bin/env <정규 adb 경로> ...`.
- `/bin/sh -c '<정규 adb 경로> ...'`.
- Python에서 정규 ADB를 `execv`하는 wrapper.

Payload는 test package의 `pm clear` argv였다. 실제 exec 전에 Popen을 가로챘으므로 어떤 payload·wrapper·ADB도 실행하지 않았다. **우회 도달 8건**, 정규 ADB·전용 API·환경/qualification 거부 성공 8건으로 interception 검사는 **8/16**이었다. Source monkeypatch나 진단용 authority patch는 이 우회에 필요하지 않았다.

이 결과는 운영자가 정상 CLI를 실행하면 자동으로 phone에 접근한다는 주장이나 외부 공격자가 OS 권한을 얻었다는 증명이 아니다. 일반 helper를 재사용하는 운영/시험 호출이 별도 신원 제어 없이 device 명령을 dispatch할 수 있다는 명시 요구의 위반이다. 같은 OS 사용자가 저장소 밖에서 임의 프로그램을 실행하는 것까지 이 Python 모듈이 막는다는 가정도 하지 않는다.

필수 조치는 Popen 이전의 허용 host 작업과 device dispatch 경계를 닫는 것이다. 단순 basename 판별이나 `argv[0].resolve()`만으로는 interpreter/env wrapper를 해결하지 못한다. 직접 helper·동일 inode alias·중첩 wrapper까지 허용 경계를 검증하는 별도 보강이 필요하다. 이번 감사에서는 수정하거나 F01 executor를 새로 구현하지 않았다.

이 finding은 N01의 자식 회수 성공이나 원 F01의 원자성 미해결과 구분한다. **전체 PREP07 FAIL의 직접 근거는 FC01**이다.

## 6. 진단 bypass·환경·예외·기존 실행기

[우회 통제 검토](../../../benchmarks/real-device-gate-prep07/f01-bypass-control-review.json)에서 두 가지를 구분한다.

`test_prep06.py:153`의 `patch.object(require_host_confinement)` 자체는 시험의 `with` 범위 안에 있으며 h.run과 OS/ADB 경계도 모두 mock이다. 이 원 반례 진단을 실행해도 실제 ADB에는 도달하지 않는다. 환경변수나 JSON으로 해당 patch를 켜는 일반 실행 분기는 없다. **그 진단 patch 자체는 ISOLATED**다.

반면 같은 효과의 authority 우회가 FC01의 일반 helper 입력으로 가능하다. 따라서 **진단용 bypass 자체는 ISOLATED**, **일반 helper를 통한 별도 실행 경계 우회는 REACHABLE**로 기록한다. 진단용 toggle이 발견됐다고 혼동해서는 안 되며, 진단 patch의 격리 성공도 FC01을 닫지 않는다.

전용 API의 오류·취소는 session을 폐기하고, N01 확인 실패는 후속 실행 전체를 차단했다. 이 성공은 일반 wrapper의 판별 결손을 메우지 않는다. PREP02–PREP06의 보존 source·replay는 현재 main의 fallback으로 호출되지 않는다. 역사 자료를 임의로 실행하거나 Python source를 바꾸는 행위는 이번 정상 구성의 권한으로 취급하지 않았다.

## 7. 46/46과 기존 회귀의 의미

| 검사 실행 묶음 | 결과 |
| --- | --- |
| 원 N01 controller 재현 | 2/2 |
| PREP06 집중 | 46/46: ADB 8, lifecycle 17, F02/F03 21 |
| PREP07 직접 dispatch interception | 8/16; 우회 8건 |
| 기존 `test_safety.py` | 4/5; fixture 오류 1건 |
| 전체 host 검사 실행 건수 | **60/69** |
| 별도 npm build | exit 0 |
| 별도 backend 회귀 | 72 passed, 44 subtests passed |

60/69는 실행 건수이며 서로 다른 보안 불변식의 수나 완료율이 아니다. 반복되는 조건이 있고, 46개 중 하나는 **가정으로 guard를 연 전체 mock 모델에서 F01이 여전히 미해결임을 확인하는 진단**이다. 이 meta-test의 성공을 F01 신원 불변식 충족으로 세지 않는다.

기존 시험의 정확한 오류는 `SafetyTest.test_every_mutation_requires_fresh_verification`이다. `__new__`로 만든 fixture에 새 `target_revoked` 필드가 없어 AttributeError가 발생한다. Device dispatch 전에 중단되므로 새로운 unsafe 실행의 증거는 아니지만 회귀 suite가 현재 fixture와 호환되지 않는다. **PREP07-T01 · LOW**로 남기고 시험을 고치거나 성공으로 바꾸지 않았다. [실패 로그](../../../benchmarks/real-device-gate-prep07/existing-safety.log.gz).

## 8. F02·F03 종결 보존

**F02 NETWORK ISOLATION: INDEPENDENT CLOSURE PRESERVED.** 기존 NetworkTests 8개를 현재 source에서 재실행했다. 소유 loopback fixture의 3xx를 거부해 비허용 목적지로 요청하지 않았고, 고정 dispatch·proxy/DNS·socket 소유·body 제한 경계가 유지됐다.

**F03 APK INTEGRITY: INDEPENDENT CLOSURE PRESERVED.** 기존 APKTests 13개에서 구조/권한/authority/resource·서명 거부, source 교체와 seal, 실제 로컬 stdin 소비·검사 실패 거부가 유지됐다. 실제 Android 설치는 하지 않았다.

Guard의 관련 보호 block 10개와 정책·기존 시험 원문이 PREP06 전후 동일했다. 공통 run/cleanup 변경 아래 관련 host 회귀도 통과했으므로 두 finding을 다시 열 근거는 없다. [f02-f03-regression-status.json](../../../benchmarks/real-device-gate-prep07/f02-f03-regression-status.json). FC01은 이 두 경계를 재명명한 finding이 아니다.

## 9. F01 설계 결정 경계 — 분석만 수행

**F01 ATOMIC IDENTITY BINDING: UNRESOLVED.** [설계 경계 기록](../../../benchmarks/real-device-gate-prep07/f01-architecture-decision-boundary.json).

공식 CLI의 `-s`는 serial, `-t`는 transport ID 선택이고 `--one-device`는 USB 연결 제한이다. 따라서 transport ID와 private server 세대 고정은 serial 재등록·자동 재선택 위험을 줄이지만, 임의 software identity predicate와 mutation의 원자적 권한 그 자체는 아니다. [ADB 공식 매뉴얼](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

공식 services 계약은 선택한 transport의 연결을 adbd로 전환하고 그 위에서 shell/exec/abb 등을 수행한다. 검토한 공개 계약에서는 조회한 임의 identity 조건을 mutation과 한 원자적 조건부 권한으로 묶는 primitive를 확인하지 못했다. 이는 문서와 현재 구현에 한정한 판단이며 모든 가능한 ADB 확장이나 OS 설계가 불가능하다는 결론은 아니다. [ADB 공식 services 문서](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/dev/services.md)

| 후보 | 보증에 도움이 되는 점 | 아직 필요한 조건 |
| --- | --- | --- |
| Transport ID·private server 세대 고정 | 같은 serial의 재등록과 자동 대상 전환 억제 | 실제 연결을 소유 QEMU socket에 결합하는 증거와 최종 identity 조건의 의미 |
| 지속·인증 연결과 격리 executor | 연결 재선택 간격과 다른 물리 target 접근 축소 | broker가 승인 연결만 사용, 재연결 권한 폐기, USB·다른 목적지 실제 차단, 도구/image/lifecycle 신뢰 |
| 수신 측 조건부 mutation 권한 경계 | 신원·generation 확인과 mutation의 동일 경계 집행 후보 | 별도 설계 승인·구현·자격검증; 현재 존재하지 않음 |

특히 허용 host 프로그램이 별도 ADB를 실행할 수 있다면 argv 수준 guard만으로 전체 실행 경계를 보증할 수 없다. FC01은 이 문제의 현재 도달 가능한 예다. 물리 실행 환경과 불변 target identity의 명시 보증으로 충분한지, 임의 mutable software predicate의 원자성을 계속 요구할지는 정식 architecture/safety-contract 심사 대상이다. 감사가 수용 기준을 줄이거나 원 반례를 소급 폐기해서 PASS를 만들지 않는다.

N01 수용, F01 차단 수용, F01 설계 해결은 각각 별도 결정이며 이번에는 첫째만 통과했다. 새 broker·executor·수신 측 프로토콜을 구현하지 않았다.

## 10. 보존·산출물·권한

PREP03 33개, PREP04 98개, PREP05 81개, PREP06 187개 manifest 참조의 SHA가 모두 일치했다. 관련 backend/mobile·규범·B03·T6.9 파일 777개와 원 B03 frozen sidecar 5개도 일치했다. 현재 source 세 파일과 archive도 검증했다.

Git index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged identity SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`로 전후 동일하다. 기존 7,215개 파일의 내용·mode, HEAD·branch와 역사 증거를 보존했다. Reset·stash·clean·checkout·rebase·restage·commit·push는 하지 않았다.

Task-owned scratch의 source 사본·임시 DB·build 출력과 alias만 소유권·비활성 확인 후 정리했다. 원 N01 사본, controller raw 관측 archive·JSON, interception argv, 실패 로그, 압축 검증 로그·JUnit은 PREP07에 남겼다. 정확한 삭제 규모는 [artifact-cleanup.json](../../../benchmarks/real-device-gate-prep07/artifact-cleanup.json)에 있다. 기존 SDK·AVD·APK·cache·source lock은 삭제하지 않았다.

B03 동기화·E3·서버 금융 의미·승인된 binding protocol/B11·production configuration은 **UNCHANGED**다. 실제 ADB 0, emulator 0, 물리 기기 접근 NO, APK 설치 0이다. T6.9는 DEFERRED, formal T6.6F closure와 production deployment는 NOT AUTHORIZED, R1은 CLOSED다. 실기기 실행 권한은 **NOT GRANTED**이며 live harness는 계속 실행 금지다.

**다음 행동: 실제 실행 금지를 유지한 채 PREP07-FC01의 run/start 우회 차단만을 위한 보강 범위를 별도 승인 심사에 제출한다.**
