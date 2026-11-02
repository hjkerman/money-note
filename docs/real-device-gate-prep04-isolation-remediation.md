# Real-Device Gate PREP04 — 격리 결함 부분 수정과 자체 회귀검증

**최종 판정: PARTIAL — SOME FINDINGS REMAIN OPEN.** F02와 F03은 자체검증으로 수정 효과를 확인했다. F01은 연결 세대 고정·취소 처리를 보강했지만 마지막 신원 확인과 mutation의 원자적 결합, USB 접근 및 소유 에뮬레이터 외 TCP 접근 차단을 완성하지 못했다. 따라서 실행기의 실제 진입을 차단하고 에뮬레이터 smoke를 실행하지 않았다. 독립 수정 수용 검사는 아직 수행되지 않았으며, PREP03의 **FAIL — HISTORICAL**을 유지한다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 시작 시 기존 파일 6,842개의 내용·mode, Git index 원문과 index path/mode/blob identity를 고정했다. 기존 tracked 수정 13개와 미추적 작업은 이번 변경으로 취급하지 않는다. 실제 source 기준은 HEAD 단독이 아니라 이 working-tree 기준선과 [변경 목록](benchmarks/real-device-gate-prep04/source-change-inventory.json)의 전후 SHA-256이다.

필수 프로젝트 문서, 보안·runbook, PREP01–PREP03 보고서, PREP03 finding register·음성 검사·ADB/네트워크 증거, PREP02 실행기·backend·Flutter 진입점·테스트, Android build·manifest·XML 설정을 확인했다. 금융 계산, B03 동기화, E3와 binding/source-SHA admission 변경은 수행하지 않았다.

| 원문 finding | 심각도와 원래 조건 | 실제 원인 | PREP04 상태 |
| --- | --- | --- | --- |
| F01 | HIGH. 신원 확인 뒤 같은 serial의 transport 1이 2로 재등록되거나 마지막 확인 뒤 원격 신원이 바뀜 | `transport_id`를 저장하지 않고 새 subprocess가 `-s`로 다시 선택함. 서버 세대와 실제 연결·mutation이 원자적으로 결합되지 않음 | **OPEN**. 재등록 거부와 취소 처리는 통과했지만 마지막 신원 변경 반례와 호스트 격리는 미해결 |
| F02 | MEDIUM. 준비 endpoint가 3xx를 반환하거나 startup 중 다른 local service가 포트 선점 | `ProxyHandler({})`가 기본 urllib redirect handler를 제거하지 않음. listener의 PID/socket 소유 검사도 없음 | **CLOSED BY SELF-TEST** |
| F03 | MEDIUM. 새 exported component 추가 또는 `dataExtractionRules` 참조 제거 | 일부 문자열 denylist가 전체 component·권한·authority·backup/transfer/network 구조를 검사하지 않음 | **CLOSED BY SELF-TEST** |

요청서의 절 제목과 달리 원문 ID는 **F01=ADB, F02=호스트 네트워크, F03=APK 구조 admission**이다. 이 보고서는 [PREP03 원문 register](benchmarks/real-device-gate-prep03/finding-register.json)를 따른다. APK 바이트 고정과 subprocess 취소는 소유자가 추가로 요구한 보강이며, 이를 원래 F03의 관측 결함으로 소급해 표현하지 않는다.

수정 전에 원 감사 재현기를 별도 출력 경로로 실행해 원래 실패 5개를 모두 재현했다. 실제 urllib·합성 loopback 서버로 비허용 임시 포트에 GET이 도달했고, 모의 transport/신원 변경 2개와 변형 APK 검사 입력 2개가 수용됐다. 운영 endpoint와 물리 기기는 사용하지 않았다. [원래 실패 재현](benchmarks/real-device-gate-prep04/historical-reproduction/host-negative-results.json)은 PREP03 역사 자료를 덮어쓰지 않은 새 증거다.

F02 수정은 [guards.py](../scripts/devicegate/guards.py)의 `SyntheticHTTP`와 실행기의 `backend()`에 있다. 임의 URL을 받지 않고 허용 method/path 두 개만 받는다. 실제 dispatch는 AF_INET socket에 고정 `127.0.0.1:18081`을 전달하며 DNS·환경 proxy·redirect handler를 사용하지 않는다. 요청 전에 기동한 backend 프로세스의 시작 세대, listener inode와 해당 TCP 연결의 accepted socket 소유권을 확인한다. 모든 3xx를 HTTP 응답 직후 거부하고, 응답은 256 KiB·유한 timeout으로 제한하며 truncated body도 거부한다. 신원 조회와 금지 mutation의 403 확인 모두 같은 경로를 쓴다. Flutter의 정확한 `10.0.2.2:18081` origin·method/path·redirect 거부와 `DIRECT` 설정, IPv4/IPv6 대체 표기 거부, Android cleartext 허용 범위는 수정하지 않았다. 이것은 해당 요청 경로의 격리 검증이며 호스트 전체 방화벽이나 악성 kernel/NAT에 대한 증명이 아니다.

F03 수정은 `admit_apk()`·`SealedAPK`, 실행기의 `admit_built_apk()`·`install_verified_apk()`에 있다. 새 [apk-policy.json](../scripts/devicegate/apk-policy.json)은 PREP03가 검사한 현재 APK의 compiled XML 전체 구조를 고정한다. 새 component뿐 아니라 권한, exported/permission, provider authority, backup/transfer/network/share resource 본문과 참조 ID 변경을 모두 거부한다. Package·version·label·Activity·서명자 수·예상 테스트 certificate와 v2 서명 검증도 요구한다. 원 APK에는 plugin native library의 세 ABI가 있으므로 실제 보존 목록을 고정했으며, x64 전용이라고 추측하지 않았다. Resource ID·버전·의존성 변경도 자동 수용하지 않으므로 정상 변경 때 명시적인 정책 검토가 필요하다.

빌드 경로의 APK를 `O_NOFOLLOW`로 열어 task-owned memfd에 복사한 뒤 커널의 WRITE/GROW/SHRINK/SEAL seal을 모두 적용한다. 예상 SHA-256과 sealed inode의 바이트를 대조하고 **같은 inode**를 aapt와 apksigner에 전달한다. 설치 경로는 mutable APK pathname을 다시 열지 않고 sealed fd를 `cmd package install -t -S <크기>`의 stdin으로 전달한다. 검사가 완료되지 않으면 설치할 수 없고 production APK fallback은 없다. 검증 후 pathname 교체, pinning 도중 내용 변경, symlink, 쓰기·크기 변경 시도와 실제 로컬 자식의 stdin 소비를 검사했다. 전후 hash만으로 동시 교체 race가 닫혔다고 주장하지 않는다.

실제 보존 APK 76,489,882바이트를 최종 소스의 sealed memfd에서 SDK aapt·apksigner로 다시 검사했다. SHA-256은 `e0ca26b0d05d57242c80d004a8defc7b080f0f579000ced21f0ac99254643582`, 테스트 인증서는 `f0764baf3b392975a28ca69bf743b76b732f7d7f014f5e480511901f43fd40a7`로 일치했다. 새 키 생성, production signing secret 접근, APK 설치는 하지 않았다. [실제 APK 검사](benchmarks/real-device-gate-prep04/retained-apk/apk-verification.json)의 `test_key_generated_this_run=false`도 확인했다. 새 APK 빌드와 실제 Android installer의 성공은 이번 결과에 포함하지 않는다.

F01 부분 수정은 [smoke.py](../scripts/devicegate/smoke.py)의 `transport_id()`·`host_guard()`·`read_device()`·`run()`·`execute()`에 있다. transport ID의 존재·유일성·양수를 검사하고 승인된 ID와 private server의 PID/start time/exe/listener inode를 계속 대조한다. argv에 serial과 transport를 명시하며, disconnect·ID 변경·서버 세대 변화·신원 실패·취소에서 권한을 폐기한다. 이후 기기 cleanup도 수행하지 않는다. 실행 중 guard를 다시 확인하고 timeout·SIGINT·SIGTERM에서는 task-created process group을 종료하고 leader와 회수 가능한 자식을 reap한다. Spawn 도중 취소도 자식 등록 뒤 전달하며 부분 로그·명령 결과를 보존한다. 광범위한 `adb kill-server`는 사용하지 않았다.

그러나 위 검사는 각 subprocess의 dispatch와 원자적이지 않다. 같은 transport의 마지막 신원 확인 직후 소프트웨어 신원을 바꾸는 원 PREP03 반례는 여전히 모의 mutation을 수용한다. `-s`와 `-t`의 조합을 실제 ADB에서 검증하지 않았고 ADB active socket과 QEMU socket의 결합도 자격검증하지 않았다. 일반적인 USB/TCP serial 거부가 깨졌거나 실제 물리 기기 치환이 관측됐다는 뜻은 아니다.

이 호스트의 `unshare --user --map-root-user --net true`는 uid_map 설정에서 `Operation not permitted`로 실패했다. Landlock ABI는 4지만 포트 제한만으로 정확한 목적지 주소와 USB 배제를 함께 보증하지 않는다. 가능한 모든 대체 방식이 불가능하다고 결론 내리지 않으며, 이번 작업은 검증된 대체 launcher를 완성하지 못했다. 시스템 권한·방화벽·서비스 구성 변경은 하지 않았다. [호스트 격리 검토](benchmarks/real-device-gate-prep04/host-confinement-feasibility.json)에 한계를 기록했다.

따라서 `preflight()`와 `boot()`는 우회 옵션 없이 `PREP04_ADB_HOST_CONFINEMENT_NOT_IMPLEMENTED`로 중단한다. 실제 CLI 진입도 build/backend/ADB/emulator 전에 exit 1과 빈 commands 목록을 남겼다. 이 차단은 **F01의 수정 완료가 아니며**, PREP02의 실제 정상 실행을 현재 harness에서 재확인했다는 의미도 아니다. [에뮬레이터 결과](benchmarks/real-device-gate-prep04/emulator-smoke-results.json)는 **NOT RUN**이다.

| 검증 | 결과와 범위 |
| --- | --- |
| PREP03 원래 45개 검사 재실행 | **44/45**, F01 마지막 신원 변경 1개 OPEN. host 29셀의 기존 suite 1셀을 5개로 풀어 33개 + Flutter isolation 12개 |
| 새 집중 회귀 | **33/34**, 같은 F01 반례 1개 OPEN. 네트워크 8/8, ADB·수명 12/13, APK 13/13 |
| 기존 Python 안전 suite | **5/5**. serial·transport 거부, mutation 전 검증, CLI 거부 |
| Flutter host | **39/39**. 기존 isolation 4개 + PREP03 8개 + bundle 27개 |
| npm build | **PASS**, 별도 task source 사본 |
| backend | **72 passed, 44 subtests passed**, 합성 임시 DB |
| 실제 보존 APK 검사 | **PASS**, 같은 sealed inode에서 구조·resource·서명·hash 확인 |
| 실제 Android build/install/smoke | **NOT RUN**, F01 차단 조건 유지 |

집중검사의 `expectedFailure`는 성공 분자에 넣지 않고 JSON에서 **OPEN**으로 기록한다. 집중검사와 원 음성 재실행기 모두 최종 exit 1을 반환한다. 서로 겹치는 두 suite의 분모를 합쳐 성공률을 부풀리지 않는다. [원 검사 전체 매핑](benchmarks/real-device-gate-prep04/prep03-regression-coverage.json), [finding→code→test 매핑](benchmarks/real-device-gate-prep04/finding-remediation-matrix.json), 개별 network/ADB/APK 결과와 압축 회귀 로그에 명령·source identity·결과를 남겼다. 초기 자체 검사 입력 형식 보정 실패 2회도 보존했다.

정확한 구현·정책·회귀 source 변경은 다음 4개다. 이 중 기존 파일 수정은 `smoke.py` 하나이며 나머지는 신규 파일이다.

| 경로 | 필요한 이유 |
| --- | --- |
| `scripts/devicegate/smoke.py` | 호스트 요청 교체, APK admission·sealed stdin 연결, transport/서버 세대·취소 처리, 미완성 실제 실행 차단 |
| `scripts/devicegate/guards.py` | 고정 목적지 dispatch와 프로세스/socket 소유 검사, compiled XML 허용 구조 검사, sealed artifact·process group 수명 관리 |
| `scripts/devicegate/apk-policy.json` | PREP03가 확인한 최종 APK의 전체 허용 구조와 resource ID 고정 |
| `scripts/devicegate/test_remediation.py` | 원 실패·오류·취소·동시 교체 및 남은 반례의 집중 회귀 |

이 보고서와 `docs/benchmarks/real-device-gate-prep04/`만 새 문서·증거다. 모든 기존 source 전후 hash는 [source-change-inventory.json](benchmarks/real-device-gate-prep04/source-change-inventory.json), 새 증거의 hash는 [evidence-manifest.json](benchmarks/real-device-gate-prep04/evidence-manifest.json)에 있다. 원 source 사본과 최종 source archive도 보존했다. [보존 결과](benchmarks/real-device-gate-prep04/preservation.json)는 승인된 기존 `smoke.py` 외에 변경·삭제·mode drift가 없음을 확인한다. Git index 원문과 staged identity, HEAD·branch, 기존 PREP01–PREP03 실패 증거, T6.6F/T6.9 자료, B03 frozen sidecar 5개를 보존했다.

Production package·signing·manifest·네트워크 경로, 금융 canonical 처리, B03/E3·binding/source-SHA admission은 바꾸지 않았다. 물리 기기 접근·실제 ADB 호출·에뮬레이터 launch·운영 요청·실기기 설치는 모두 0이다. 전체 제품 회귀, 제조사 transfer/backup, Android 네트워크 계측, process-death/전원손실 durability와 실제 단말 성능은 검증하지 않았다. T6.9는 DEFERRED, 이관 의무 수용 0/8, formal T6.6F closure와 production deployment는 NOT AUTHORIZED, R1은 CLOSED다. Reset·stash·clean·checkout·rebase·restage·commit·push는 수행하지 않았다.

Task scratch의 source 사본·frontend/mobile 검사 산출물·임시 DB·일시 로그는 소유권과 비활성을 확인하고 필수 압축 로그·JUnit·source archive를 보존한 뒤 정리했다. 대략 84 MiB를 회수했다. 기존 SDK/AVD/cache, 보존 APK와 frozen source는 정리 대상에서 제외했다. 정확한 크기·생성/삭제 항목·미해결 항목은 [artifact-cleanup.json](benchmarks/real-device-gate-prep04/artifact-cleanup.json)에 있다.

PREP05는 구현에 참여하지 않은 새 검토자가 수행해야 한다. [독립 검토 handoff](benchmarks/real-device-gate-prep04/prep05-independent-review-handoff.json)에 원 finding과 45개 입력, source hash, 별도 출력 경로를 지정한 재실행 명령을 연결했다. 집중검사 exit 1·F01 OPEN을 기대 결과로 보존하되 독립적으로 판단하고, F02의 비허용 목적지 요청 0회와 F03의 전체 구조 거부·동일 sealed 바이트 소비를 다시 확인해야 한다. PREP04 증거를 덮어쓰지 않아야 하며 실제 harness의 진입 차단을 해제하거나 물리 기기를 연결해서는 안 된다. F01이 열린 상태에서 독립 전체 PASS나 실기기 승인을 부여할 수 없다.

**다음 행동: PREP05 독립 검토자가 PREP04 증거와 F01 미해결 차단 조건을 인수해 물리 기기 접근 없이 F01–F03을 재감사한다.**
