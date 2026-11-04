# Real-Device Gate PREP06 — ADB 권한 차단과 취소 안전 자식 수명 관리

**최종 판정: BLOCKED — TARGET IDENTITY GUARANTEE REQUIRES ARCHITECTURAL CHANGE.** PREP05-N01은 자체검증으로 수정 효과를 확인했다. F01은 현재의 분리된 ADB 조회·mutation 인터페이스로 요구된 원자적 신원 보증을 제공하지 못하므로 종결하지 않는다. 실제 진입 차단을 유지하고 직접 호출되는 기기 dispatch 경로에도 같은 차단을 적용했다. 에뮬레이터·실기기·실제 ADB 명령은 실행하지 않았다. 독립 수용 검사는 아직 수행되지 않았다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 시작 당시 기존 파일 7,026개의 SHA-256·mode, index 원문 및 index path/mode/blob identity를 보존했다. 기존 tracked 수정 13개와 미추적 작업은 이번 변경이 아니다. PREP03–PREP05의 finding 정의, 원 재현기, 실패 증거와 실제 devicegate 소스를 먼저 대조했다. 전후 source identity는 [source-change-inventory.json](../../../benchmarks/real-device-gate-prep06/source-change-inventory.json), 기존 파일 기준선은 [preservation-before.json](../../../benchmarks/real-device-gate-prep06/preservation-before.json)에 있다.

| Finding | 정확한 정의와 원 재현 | PREP06 결정 |
| --- | --- | --- |
| F01 · HIGH | 같은 serial의 transport 재등록과 마지막 신원 probe 이후 변화 모델에서 mutation이 계속됨. PREP05는 재등록 거부를 인정했으나 최종 probe 뒤 변화와 실제 transport/host 결합을 OPEN으로 유지 | **BLOCKED**. 실제 dispatch 거부는 containment이며 원자적 신원 보증의 수정 완료가 아님 |
| PREP05-N01 · HIGH | `run.finally → stop_group`의 SIGTERM 유예 중 추가 취소가 SIGKILL·wait/reap·진단 저장을 건너뜀. `run()`의 자식 핸들이 바깥 정리에 등록되지 않아 부모 종료 뒤 쓰기 지속 | **자체검증 통과, 독립 수용 대기** |
| F02 | PREP05 독립 종결된 고정 목적지·redirect 거부·backend socket 소유 경계 | **INDEPENDENTLY CLOSED — PRESERVED** |
| F03 | PREP05 독립 종결된 전체 APK 구조 admission·서명·sealed 바이트 전달 경계 | **INDEPENDENTLY CLOSED — PRESERVED** |

수정 전에 원 PREP05 F01 fixture 함수를 그대로 사용해 마지막 probe 뒤 바뀐 fingerprint 상태에서 모의 install argv가 호출되는 것을 다시 확인했다. 실제 ADB는 호출하지 않았다. 원 N01 재현기 두 개도 경로만 PREP06으로 바꿔 반복했다. 첫 취소 정리 중 추가 signal, timeout 정리 중 signal 모두 부모 exit 1 뒤 자식이 살아 있었고, 0.16초 관측 동안 marker가 각각 **40바이트 증가**했다. 별도 controller가 정확한 task 자식을 강제 종료·회수했다. [수정 전 원 증거](../../../benchmarks/real-device-gate-prep06/before-reproduction/cancellation-independent-results.json)는 역사 PREP05 결과를 덮어쓰지 않은 새 재현이다.

F01의 마지막 probe와 실제 명령 사이에는 호스트 재검사, 새 ADB subprocess의 transport 선택, remote mutation이 각각 존재한다. 조회를 한 번 추가해도 새 조회 뒤 같은 간격이 남는다. 기존 serial·양수 transport ID·private server 세대 대조는 재등록을 거부하지만, 그 값만으로 probed software identity와 mutation 수신자를 하나의 원자적 권한으로 묶지는 않는다.

검토한 공식 CLI 계약에서 `-s`는 serial, `-t`는 transport ID 선택이며, `--one-device`는 USB 연결 제한이다. 이 옵션을 원격 신원 조건 검사와 mutation의 원자적 결합으로 해석하지 않았다. [ADB 공식 매뉴얼](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

강한 프로세스 소유권은 소유 QEMU의 생존을 증명하는 데 도움이 되고, 이미 선택된 연결을 유지하면 재선택 간격을 줄일 수 있다. 그러나 현재 실행기는 실제 ADB active connection과 소유 QEMU socket을 결합하는 검증된 broker가 없고, mutable identity 조건을 명령 수신자가 mutation과 원자적으로 확인하는 계약도 없다. USB·소유 endpoint 외 TCP 차단을 자격검증한 launcher도 남아 있다. 이는 **현재 검토한 인터페이스와 구현에서의 결론**이며 모든 다른 ADB 확장이나 운영체제 설계가 불가능하다는 주장이 아니다.

필요한 아키텍처 제어는 **승인된 신원·generation을 동일 transport의 명령 수신자가 확인하고 mutation과 원자적으로 결합하는 권한 경계**, 그리고 그 transport를 소유 QEMU endpoint에 고정하는 검증된 실행 환경이다. 단순 host probe나 `-t` 추가로 대체할 수 없다. 신뢰 broker 또는 수신 측 계약의 도입은 현재 허용된 최소 CLI 수정과 프로토콜 불변 범위를 넘는다. 해당 제어를 구현한 것처럼 가장하거나 기존 신원 불변식을 축소하지 않았다. [F01 분석](../../../benchmarks/real-device-gate-prep06/f01-remediation-analysis.json)에 후보별 효력과 남은 조건을 구분했다.

F01 containment 변경은 `require_device_authority()`와 이를 호출하는 `verify()`·`mutate()`·`read_device()` 및 직접 ADB `run()`·`start()` 경로다. 기존 `preflight()`·`boot()`의 차단도 유지한다. 우회 인자나 환경변수는 없다. 자격이 없는 현재 상태에서는 실제 device argv를 dispatch하지 않고 권한을 폐기한다. 같은 session에서 재시도해 권한을 복구하지 않는다.

원 F01 fixture를 현재 기본 경로에 적용하면 probe·mutation 전에 차단된다. 반대로 **호스트와 ADB를 전부 모의한 상태에서 자격 조건만 가정으로 열면**, 마지막 probe 뒤 변화가 여전히 모의 mutation에 도달한다. [남은 인터페이스 반례](../../../benchmarks/real-device-gate-prep06/f01-unclosed-interface-counterexample.json)는 이 한계를 의도적으로 보존한다. 이 진단 검사의 통과를 F01 보안 불변식 충족이나 수정 종결로 집계하지 않는다. 원 모델은 같은 logical transport의 software identity 변화이며 실제 물리 기기 치환 증거가 아니다.

N01 수정은 자식 등록, 종료·회수 증명, 취소 보호와 증거 저장에 한정했다.

- `run()`과 `start()` 모두 새 자식 핸들을 pending 취소 전달 전에 executor registry에 등록한다. `run()`의 1차 정리에 문제가 있어도 바깥 `finish()`가 그 핸들을 잃지 않는다.
- `run.finally`의 SIGTERM·SIGKILL·wait/reap·명령 결과·압축 진단 저장 전체를 추가 취소로 끊기지 않게 보호한다. 추가 signal은 기록하고 안전 구간이 끝난 뒤 비영 종료로 전달한다. `finish()`의 자식 회수와 진단 저장도 보호한다.
- 성공한 cleanup에는 leader의 `Popen.wait`, descendant의 `waitpid`, process group 부재, 새 subreaper adoption 부재라는 증거를 요구한다. `ECHILD` 하나만으로 성공을 선언하지 않는다.
- 같은 group의 자식뿐 아니라 `setsid()`로 이탈해 전용 executor에 재입양된 자식도 회수한다. 생성 전 direct-child 기준선의 PID/start time을 제외하고, 새 adoption에는 pidfd로 신호를 보내 PID 재사용에 따른 오조작을 피한다. 기존 호스트 전체 PID를 검색해 종료하지 않는다.
- subreaper·pidfd·관측 기능은 자식 생성 전에 확인한다. 현재 Python 3.13이 `os.pidfd_open`을 노출하지 않아도 검증한 Linux syscall 경로를 사용한다. 지원 기능을 확인할 수 없으면 자식을 만들지 않고 실행 권한을 폐기한다.
- 종료·회수 확인에 실패하면 `ChildCleanupFailure`와 `safety_critical_failure`를 기록한다. 이후 `run()`·`start()`·기기 mutation은 거부한다. 바깥 정리의 추가 회수 시도는 명시적으로 기록하며 원 작업을 자동 재실행하지 않는다. 한 번 확인 실패한 안전 상태를 이후 회수 성공으로 지우지도 않는다.

종료 대기 예산은 group별 SIGTERM 유예 0.1초, leader wait 5초, descendant/adoption 확인 2초다. 이미 종료·회수가 확인된 핸들은 증거를 재사용한다. 이 보증의 실행 전제는 **task 자식만 생성하는 전용 Linux executor**이며, 같은 interpreter에서 unrelated subprocess를 병렬 생성하는 임의 embedding 환경을 자격검증한 것은 아니다. 시험한 host는 Linux `6.8.0-147-generic` x86_64다. 종료 확인 불가와 지원 기능 부재는 조용한 성공이 아니라 명시적인 안전 실패다. [N01 분석](../../../benchmarks/real-device-gate-prep06/n01-remediation-analysis.json)에 조건과 실패 처리 범위를 기록했다.

원 N01 두 재현은 최종 소스에서 **2/2** 통과했다. 자식은 SIGTERM을 무시했지만 SIGKILL 후 wait/reap됐고, 부모 종료 뒤 marker 증가와 살아 있는 자식은 모두 0이었다. 누락됐던 exit code와 압축 진단도 존재했다. [최종 원 재현](../../../benchmarks/real-device-gate-prep06/terminal-reproduction/cancellation-independent-results.json).

새 controller 관측 10개는 최초 취소, 반복 취소, timeout 후 취소, 강제 종료, reap 중 취소, 진단 저장 중 취소, spawn 등록 중 취소, `start()` 자식의 최종 정리, group descendant, 새 session으로 이탈한 descendant 및 확인 실패 주입을 포함한다. 일부 경우는 한 fixture에서 여러 조건을 함께 검사한다. controller는 executor와 별도 프로세스에서 종료 뒤 `/proc` 부재와 marker 크기를 다시 관측했다. 모든 관측에서 종료 후 쓰기 0, 잔존 자식 0이었다. 확인 실패 주입은 실제 종료 뒤 acknowledgement를 유실시킨 경우이며, 실제 kernel의 영구 종료 불가 상태를 만들어 시험한 것으로 표현하지 않는다.

| 검증 | 결과 | 의미와 한계 |
| --- | --- | --- |
| PREP06 집중 검사 | **46/46** | F01 8개, N01 및 기존 lifecycle 17개, 변경하지 않은 F02/F03 21개. F01의 한 검사는 미해결 아키텍처 반례가 남는다는 진단이며 종결 증거가 아님 |
| 원 N01 최종 재현 | **2/2** | 원 fixture 본문 유지, task 경로만 분리. controller 관측으로 종료 후 쓰기·생존 0 |
| PREP05 F02/F03 원 검사 본문 | **24/24** | 실제 합성 HTTP, SDK aapt/apksigner와 같은 sealed inode의 로컬 stdin 소비 |
| 기존 Flutter host 격리 | **12/12** | 기존 주소·redirect·package 진입 검사를 변경 없이 실행 |
| npm build | **PASS** | 별도 task 사본 |
| backend | **72 passed, 44 subtests passed** | 합성 임시 DB, 운영 API 접근 없음 |
| 실제 ADB·에뮬레이터 smoke | **NOT RUN** | F01 BLOCKED 유지 |

서로 겹치는 suite의 분모를 합산하지 않았다. [ADB 검사](../../../benchmarks/real-device-gate-prep06/adb-race-regression-results.json), [lifecycle 및 외부 관측](../../../benchmarks/real-device-gate-prep06/cancellation-lifecycle-results.json), [F02/F03 보존 결과](../../../benchmarks/real-device-gate-prep06/f02-f03-regression-results.json), [저장소 검증](../../../benchmarks/real-device-gate-prep06/repository-validation.json)에 명령·결과·source identity가 있다. 초기 fixture가 dummy 비밀값과 같은 단어를 진단 문장에 넣어 redaction assertion이 실패한 이력도 별도 보존했다. 당시에도 자식 생존이나 종료 후 쓰기는 관측되지 않았다.

정확한 구현·회귀 source 변경은 다음 3개다.

| 파일 | 필요한 변경 |
| --- | --- |
| `scripts/devicegate/smoke.py` | 실제 ADB dispatch 차단, 모든 자식 핸들 등록, 취소 보호·결과 저장·확인 실패 시 실행 폐기, PREP06 소유 출력 경로 |
| `scripts/devicegate/guards.py` | pending 취소 전달 제어, bounded 종료·reap 증명, subreaper adoption 및 pidfd 기반 자식 회수·사전 기능 검증 |
| `scripts/devicegate/test_prep06.py` | 원 F01 fixture, 원 취소 조건, 별도 controller 관측과 실패·이탈 descendant 회귀 |

`guards.py`는 F02/F03과 lifecycle helper가 같은 파일에 있어 수정이 필요했다. F02/F03의 구현을 재개방한 것은 아니다. `SyntheticHTTP`, socket/process 소유 검사, XML parser·APK admission·sealed artifact와 실행기의 build/backend/APK admission/설치 연결 등 **10개 보호 block의 원문 해시가 동일**하다. `apk-policy.json`, 기존 `test_remediation.py`, Flutter/Android source도 그대로다. 공통 `run()` 수명 관리가 APK 검사 자식에도 적용되므로 위 24개 및 21개 회귀를 실행해 의존 경계를 확인했다.

이 보고서와 `docs/benchmarks/real-device-gate-prep06/`는 새 task 문서·증거다. [보존 결과](../../../benchmarks/real-device-gate-prep06/preservation.json)는 승인된 기존 source 두 파일 외 기존 파일 변경·삭제·mode drift가 없음을 확인한다. HEAD·branch·Git index·기존 staged identity, PREP03–PREP05 원 실패와 독립 판정, 원 B03 frozen sidecar 5개를 보존했다. B03 동기화·E3·binding/source-SHA admission·금융 canonical 의미·production package/signing/configuration은 변경하지 않았다. 물리 기기·실제 ADB·운영 endpoint·실기기 실행·large-N·T6.9·배포는 미실행이다. Commit·push는 없다.

Raw worker PID·marker·명령·wait/reap 증거는 source archive 및 host-observation archive와 함께 보존했다. 비활성과 소유권을 확인한 뒤 PREP06 scratch의 사본·임시 DB·build 출력·일시 로그만 정리했다. 정확한 생성/삭제 항목과 회수 크기는 [artifact-cleanup.json](../../../benchmarks/real-device-gate-prep06/artifact-cleanup.json)에 있다. 기존 SDK·AVD·APK·cache와 과거 증거는 정리하지 않았다.

[독립 재검토 handoff](../../../benchmarks/real-device-gate-prep06/independent-reaudit-handoff.json)는 새 검토자가 별도 출력 경로에서 실행할 명령과 source 해시를 제공한다. N01 자체검증 성공은 독립 수용이 아니며 F01 BLOCKED를 해제하지 않는다. 신원 조건과 mutation을 원자적으로 묶는 아키텍처가 별도 승인·구현·자격검증되기 전까지 실제 harness와 emulator smoke를 실행해서는 안 된다.

**다음 행동: 별도 독립 검토자가 PREP06의 N01 수정과 F01 실행 차단·필요 아키텍처 통제를 기기 접근 없이 재검증한다.**
