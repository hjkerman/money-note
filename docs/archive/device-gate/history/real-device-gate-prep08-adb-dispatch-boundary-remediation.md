# Real-Device Gate PREP08 — ADB 공통 실행 경계와 FC01 우회 차단

**최종 판정: PASS — FC01 DISPATCH BYPASSES CLOSED BY SELF-TEST.** 원 PREP07-FC01의 8개 우회를 자체검증으로 차단했다. 이번 구현 세션에는 독립 수용 권한이 없다. **PREP07 독립 감사의 FAIL은 역사적 판정으로 그대로 보존하며, F01 원자적 신원 결합은 UNRESOLVED, 운영 dispatch는 BLOCKED다.** 실제 ADB·에뮬레이터·물리 기기 접근과 APK 설치는 모두 0회다. 실기기 실행 권한은 NOT GRANTED다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이며 예상값과 일치했다. 변경 전에 기존 파일 **7,275개**의 내용·mode와 전체 Git index의 path/mode/blob 신원을 기록했다. 기존 tracked 변경 13개와 미추적 작업은 이번 변경이 아니다. [시작 기록](../../../benchmarks/real-device-gate-prep08/preservation-before.json), [변경 전 finding·정확한 assertion](../../../benchmarks/real-device-gate-prep08/before-findings.json), [최종 보존 결과](../../../benchmarks/real-device-gate-prep08/preservation.json)를 함께 제공한다.

AGENTS와 필수 프로젝트·도메인·알려진 이슈·서버 authority 경계, 산출물 관리 규칙, PREP03–PREP07 원 보고서와 finding register·원 재현기, 현재 devicegate 소스와 시험을 대조했다. 제품 금융 계산·동기화·프로토콜·운영 구성은 수정하지 않았다. 이 세션은 PREP07 독립 감사의 연장이 아닌 구현·자체검증 세션이다.

**원 결함과 변경 전 재현.** PREP07-FC01은 일반 `Harness.run/start`가 첫 실행 파일의 basename이 `adb`일 때만 `require_device_authority()`를 호출하여 alias와 wrapper가 권한 검사 없이 프로세스 생성 지점에 도달하는 HIGH finding이다. 원 위치는 `smoke.py:232–233,318–319`의 분류와 `:251,:325`의 `subprocess.Popen`이다. 두 경로의 primitive는 같지만 `run`은 동기 대기·정리, `start`는 background 자식 등록을 담당했다. 기존 의도는 `require_device_authority → require_host_confinement`의 무조건 거부였으며 이름 불일치가 그 경계를 생략시켰다.

변경 전 원 재현기의 출력·scratch 경로만 PREP08로 바꾸어 **8/16**을 다시 관측했다. 8개 위험 요청 모두 Popen mock에 도달했으며 실제 실행은 없었다. 원 기대식은 아래와 같고, 변경 후 재현에서도 그대로 유지했다.

```python
passed = not attempts and result == 'PREP04_ADB_HOST_CONFINEMENT_NOT_IMPLEMENTED'
```

원 argv의 payload는 테스트 package에 대한 `shell pm clear`다. 아래 8개를 각각 별도 unittest로 실행했다. 같은 inode alias는 새 task-owned symlink의 device/inode를 실제 SDK ADB와 대조했으며 실행하지 않았다. 다른 원 argv는 보존된 PREP07 interception JSON에서 그대로 가져왔다.

| 원 경로 ID | wrapper와 예정된 실행 | 변경 전 | 변경 후 |
| --- | --- | --- | --- |
| `run_same_inode_alias` | `sdk-tool-alias → ADB` | Popen 도달 | 차단·primitive 0회 |
| `run_env_wrapper` | `/usr/bin/env → ADB` | Popen 도달 | 차단·primitive 0회 |
| `run_shell_wrapper` | `/bin/sh -c → ADB` | Popen 도달 | 차단·primitive 0회 |
| `run_python_wrapper` | `Python → os.execv(ADB)` | Popen 도달 | 차단·primitive 0회 |
| `start_same_inode_alias` | `sdk-tool-alias → ADB` | Popen 도달 | 차단·primitive 0회 |
| `start_env_wrapper` | `/usr/bin/env → ADB` | Popen 도달 | 차단·primitive 0회 |
| `start_shell_wrapper` | `/bin/sh -c → ADB` | Popen 도달 | 차단·primitive 0회 |
| `start_python_wrapper` | `Python → os.execv(ADB)` | Popen 도달 | 차단·primitive 0회 |

[변경 전 새 재현](../../../benchmarks/real-device-gate-prep08/before-reproduction/dispatch-interception-results.json)과 [최종 소스의 원 assertion 재현 16/16](../../../benchmarks/real-device-gate-prep08/after-terminal-reproduction/dispatch-interception-results.json), [8경로 독립 시험 결과](../../../benchmarks/real-device-gate-prep08/fc01-eight-path-regression.json)를 보존했다. PREP07 원본 파일은 수정하지 않았다.

**공통 경계와 지원 범위.** 변경 전 구조는 `run/start → basename 조건부 authority → Popen`이었다. 변경 후에는 두 Popen을 모두 `dispatch.spawn_process`로 대체했다. 이 함수 본문은 무조건 `DispatchDenied`를 발생시키는 한 문장이다. process 생성 primitive, 권한 객체, 발급 함수, 허용 Boolean, 환경·설정 분기와 mutable authorization state가 없다. 기존 F01 오류 코드를 유지하므로 원 재현기의 기대식을 바꾸지 않았다.

같은 함수를 `run/start` 진입 직후에도 호출한다. argv 변환, cwd/env/log 객체 평가, caller의 `guard` callback, 로그 파일 생성보다 앞서 거부한다. 원 process 생성 위치에도 같은 경계를 남겼으므로 정상 진입만 검사하는 구조가 아니다. 예외는 권한을 폐기하고 전파하며 다른 sink로 fallback하지 않는다. `start`의 내부 예외에서는 연 출력 handle도 닫는다. N01의 등록·취소 보호·종료·reap 구현은 유지했다.

**현재 일반 host dispatch도 비활성화한다.** `keytool`, APK 검사 도구, 합성 backend 시작은 목적상 호스트 작업이다. Flutter·Gradle 명령도 현재 빌드·분석·단위검사 argv이며 실제 기기 변경이 관측된 것은 아니다. 그러나 범용 interpreter나 build tool에 별도 실행 예외를 주면 후손 ADB를 다시 열 수 있으므로 PREP08에서는 이들에 운영 권한을 발급하지 않았다. 독립적인 웹 빌드와 backend 회귀는 devicegate 실행기 밖의 전용 검증 사본에서 정상 수행했다. 전역 subprocess monkeypatch를 운영 코드에 도입하지 않았다.

다음 표의 전체 기계 목록과 함수·import·호출 위치는 [dispatch-reachability-inventory.json](../../../benchmarks/real-device-gate-prep08/dispatch-reachability-inventory.json)에 있다. 운영 모듈 `smoke.py`, `guards.py`, `backend.py`, `dispatch.py`를 모두 검사했다. 원 8건의 성공만으로 완전성을 주장하지 않는다.

| 공개 진입·참조 | 중간 경로·sink | 변경 가능성 | 기존 검사·우회 여부 | 조치·현재 상태 |
| --- | --- | --- | --- | --- |
| CLI `main --serial`·`execute` | `preflight → build/backend/boot/application` | 후속 기기 변경 | host confinement에서 이미 거부 | 기존 거부 유지·하위 공통 경계 추가 |
| CLI `--check-result` | `check_result` | host JSON 검사 | process 경로 없음 | 변경 불필요 |
| 직접 `run`·`start` | 각 Popen 위치 → 공통 `spawn_process` | 임의 argv의 직접·간접 변경 | basename으로 우회 가능 | 입력 평가 전과 sink에서 무조건 거부 |
| bound/unbound/import/partial 사전 참조 | 원 helper 함수 객체 → 같은 경계 | 원 helper와 동일 | wrapper argv이면 우회 가능 | Popen monkeypatch와 무관하게 거부 |
| symlink·env·sh·Python·중첩 wrapper | `run/start → 공통 경계` | ADB 변경 가능 | 이름 분류 우회 | wrapper 자체 생성 0회 |
| caller callback·argv/cwd/env/log 객체 | helper 입력 평가 | 숨은 코드 실행 가능 | 원 범용 helper는 입력 평가 진행 | 거부 요청에서는 평가 자체를 수행하지 않음 |
| `preflight` | `EMU -version/-accel-check → run` | 표시된 argv는 host 검사 | host confinement 선행 거부 | 거부 유지·직접 run도 거부 |
| `boot` | ADB server·emulator → `start`, 이후 device helper | 연결·에뮬레이터 동작 | host confinement 선행 거부 | 모든 시작 경로 차단 |
| `build` | keytool·Flutter·Gradle → `run` | host 빌드, 도구 후손 격리는 미자격 | 일반 run에서 별도 통제 부족 | 도구 시작 차단 |
| `admit_built_apk` | aapt·apksigner → `run` | host APK 검사 | 일반 run | admission 본문 보존·실행 차단 |
| `backend` | 전용 Python → `start → SyntheticHTTP` | 소유 코드상 합성 host 서버 | 일반 start | 시작·HTTP client 생성 전 차단 |
| `install_verified_apk` | sealed fd → `mutate → read_device → run` | APK 설치 | device authority 거부 | sealed 계약 보존·dispatch 차단 |
| `mutate/verify/read_device` | authority·host guard → `run` | 기기 변경 또는 조회 | 기존 authority는 거부 | 기존 거부 및 공통 sink 거부 |
| `application` | 설치·launch·결과·로그·stop/clear/uninstall | 기기 변경 | 전용 device 경계 | 모든 하위 실행 차단 |
| 기존 package 정리 | 조회·`pull/uninstall → mutate` | 기기·host 파일 변경 | 전용 device 경계 | 모든 하위 실행 차단 |
| `finish` | 선택적 device 정리 / 소유 host 자식 회수 | device 종료 또는 host 종료 | revoked이면 device 정리 생략 | device 차단·기존 host 회수 보존 |
| `host_guard/host_inventory` | 고정 `host:devices-l` socket 조회 | 읽기 전용·process 생성 없음 | device 호출은 authority 선행 | 이번 시험은 전부 모의·실제 ADB protocol 요청 없음 |
| guards의 HTTP/APK/lifecycle helper | socket·파일·기존 자식 signal/wait/pidfd | ADB 변경·새 process 없음 | 기존 소유·무결성 검사 | 원문과 독립 종결 보존 |
| `backend.py main` 독립 진입 | 합성 DB·단일 `uvicorn.run(app)` | host 서버, 소유 코드에 ADB 없음 | fresh synthetic 경로 | 원문 보존·실제 기동 미실행 |
| `spawn_process` 직접·사전 캡처 참조 | 무조건 예외 | 변경 불가 | 신규 경계 | 언제나 거부 |

운영 모듈에서 도달 가능한 `subprocess.run/call/check_call/check_output`, asyncio subprocess, `os.system/popen/fork/spawn/exec` 경로와 devicegate shell script는 발견되지 않았다. `shell=True`도 없다. ctypes의 기존 native 호출은 subreaper `prctl`과 `pidfd_open` syscall 434이며 process 생성이 아니다. 변경 후 운영 모듈의 실제 process 생성 primitive는 **0개**, 원 sink 위치의 공통 거부 지점은 **2개**, 추가 입력 전 거부 지점은 **2개**다.

이 보증은 **신뢰된 devicegate 소스의 지원 실행 경로**에 한정한다. 임의 Python 코드가 raw stdlib·사전 캡처한 raw Popen·native 함수를 직접 호출하거나, 소스를 monkeypatch하거나, 외부 process를 독립 실행하는 것까지 금지하는 OS sandbox는 아니다. 현재 지원 소스에는 그런 raw 생성 alias가 없으며 helper 함수의 사전 캡처 참조는 검증했다. 악성 코드·import hook·외부 process까지 포함하려면 USB·목적지 egress와 실행 권한을 강제하는 별도 OS 격리가 필요하다. 이를 PREP08에서 구현하거나 자격검증한 것으로 표현하지 않는다.

**거부 시험과 진단 격리.** [공통 경계 불변식](../../../benchmarks/real-device-gate-prep08/centralized-boundary-invariant.json)은 새 경계 시험 **27/27**과 세부 denial 관측을 제공한다. Popen뿐 아니라 동기 subprocess wrapper, asyncio 생성 함수, os process 생성 함수를 mock sink로 가로채 호출 0회를 요구했다. 직접 helper, 중첩 wrapper, 함수 참조 alias, 누락·오래됨·잘못된 형식·변조된 authorization 입력, 환경·가상 qualification 필드, 예상 밖 예외, caller coercion·callback 미평가와 동시 호출 24건을 검사했다. 새 실행 파일·primitive alias·동적 process module 참조·native syscall 또는 무조건 거부 변경을 찾는 검사에 음성 소스 예제를 주입하여 탐지도 확인했다. 이 검사는 임의 악성 Python 전체에 대한 형식 증명은 아니다.

기존 F01 진단은 `test_prep06.py`의 source patch 범위 안에서 `h.run`과 OS/ADB 경계를 모두 모의한다. 일반 실행의 환경·CLI·설정으로 켜는 분기가 없다. 선행 host authority를 가정으로 열어도 실제 `run/start`의 공통 경계는 계속 거부한다.

N01·sealed stdin의 실제 host 자식 회귀를 위해 새 시험 파일에서만 실행 경계를 교체했다. 어댑터는 Python `-c`의 **원 합성 프로그램 전체 본문과 소유 scratch 경로를 별도로 대조**하고, 시험별 argv 목록도 요구한다. caller의 목록에 ADB·env/sh·Python exec wrapper를 넣거나 목록을 변조해도 이 독립 본문 검사에서 거부한다. shell/executable override도 거부한다. source-level 시험 patch가 끝나면 원 무조건 거부로 복구된다. 운영 소스는 이 어댑터를 import하지 않고, mock 권한 토큰이나 live dispatch를 여는 운영 옵션은 만들지 않았다.

**F01과 기존 독립 종결.** [F01 상태](../../../benchmarks/real-device-gate-prep08/f01-unresolved-safety-status.json)는 원자적 신원 결합을 계속 UNRESOLVED로 기록한다. 기본 구성에서 원 identity-change fixture는 probe·mutation 전에 차단된다. 반대로 모든 OS/ADB 경계가 모의된 가정 모델에서는 마지막 신원 probe 뒤 변경된 fingerprint에서 모의 mutation이 계속되는 원 반례가 남는다. 그 진단의 성공은 F01 해결이나 실제 기기 권한이 아니다. 추가 probe, Python lock, `adb -s/-t`, FC01 차단으로 신원과 실제 mutation 수신자의 원자성을 충족했다고 주장하지 않는다.

| 최종 호스트 회귀 | 결과 | 보존·한계 |
| --- | --- | --- |
| PREP08 경계 | **27/27** | 원 8개·추가 경로·진단 어댑터 거부 포함 |
| 기존 PREP06 F01 | **8/8** | 원 반례가 미해결임을 확인하는 모의 진단 1개 포함 |
| N01 및 기존 lifecycle | **17/17** | 별도 controller 10건·자식/후손 PID 12개, 종료 뒤 생존·추가 쓰기 0 |
| F02 네트워크 | **8/8** | 합성 loopback redirect 거부·비허용 목적지 요청 0 |
| F03 APK | **13/13** | 구조 거부·sealed 바이트·로컬 stdin 소비, Android 설치 없음 |
| 기존 안전 suite | **5/5** | 확인된 PREP07-T01 fixture 보정, 원 assertion 유지 |
| 주 호스트 suite 합계 | **78/78** | 자체검증이며 독립 수용 아님 |
| 원 PREP07 interception 재실행 | **16/16** | 위 suite와 중복되므로 분모에 합산하지 않음 |
| 별도 `npm run build` | **exit 0** | task 사본에서 수행 |
| 별도 backend | **72 passed, 44 subtests passed** | 기존 소형 회귀·합성 임시 DB, 운영 요청 없음 |
| 실제 ADB·에뮬레이터·물리 기기·설치 | **미실행** | 각각 0·0·접근 없음·0 |

[N01/F02/F03 결과](../../../benchmarks/real-device-gate-prep08/n01-f02-f03-regressions.json), [전체 개별 시험](../../../benchmarks/real-device-gate-prep08/verification/host-tests.json), [최종 실행 명령](../../../benchmarks/real-device-gate-prep08/verification-invocation.json), [웹·backend 검증](../../../benchmarks/real-device-gate-prep08/repository-validation.json)에 근거가 있다. N01/F02/F03은 **INDEPENDENT CLOSURE PRESERVED**이며 새 독립 수용을 부여한 것이 아니다. `guards.py`, `test_prep06.py`, `test_remediation.py` 전체 원문과 기존 보호 block 10개의 해시가 동일하다. N01의 회수·취소·증거 저장 구현을 다시 설계하지 않았다.

PREP07-T01은 변경 전 동일한 `target_revoked` 누락 AttributeError로 재현했다. 원인은 `__new__` fixture가 새 authority 전제를 모델링하지 않은 것이다. fixture 안에 `target_revoked=False`와 authority Mock을 추가했다. `verify/read_device`는 기존에도 모의였고, 6단계 verify/mutate 순서 및 검증 실패 시 mutation 미호출 assertion은 그대로다. 이 시험용 Mock을 운영 권한으로 사용하지 않는다.

초기 회귀 실패도 삭제하지 않았다. 첫 실행은 정적 검사기의 `hasattr(os, 'pidfd_open')` 오탐과 sink 이동에 따른 과거 최소 host fixture 필드 누락으로 72/74였고, 다음은 새 shell 파일 음성 예제 처리 오류로 74/75였다. 이후 77/77과 입력 전 차단 보강의 78/78을 확인했다. 시험 어댑터를 추가로 보강하면서 허용목록을 너무 일찍 고정해 동적 임시 경로 fixture를 거부한 실행도 있었다. 그 실행은 늦은 fixture signal로 중단됐으며 [당시 소스](../../../benchmarks/real-device-gate-prep08/driver-freeze-failure.py.txt)·압축 로그·raw 관측을 보존했다. 목록 등록을 보정하고 합성 본문 독립 대조를 유지한 최종 재실행은 **78/78**이다. 이 시험 어댑터 실패를 운영 N01의 모순 증거로 해석하거나, 이전 실패 실행을 성공으로 다시 쓰지 않았다.

**정확한 변경과 보존.** 소스 변경은 아래 **4개**뿐이다. [source-change-inventory.json](../../../benchmarks/real-device-gate-prep08/source-change-inventory.json)에 전후 SHA·mode, [정확한 patch](../../../benchmarks/real-device-gate-prep08/source-changes.patch)에 전체 변경이 있다.

| 파일 | 상태·목적 |
| --- | --- |
| `scripts/devicegate/smoke.py` | 기존 수정. 두 Popen 제거·공통 경계와 입력 전 거부, 예외 권한 폐기·start handle 정리 |
| `scripts/devicegate/dispatch.py` | 신규. 발급 수단과 process primitive가 없는 단일 거부 함수 |
| `scripts/devicegate/test_prep08.py` | 신규. 경계 회귀·새 sink 탐지·기존 시험의 제한된 합성 실행 어댑터 |
| `scripts/devicegate/test_safety.py` | 기존 수정. 확인된 T01 fixture 전제 보완, assertion 유지 |

그 밖의 새 파일은 이 한국어 보고서와 `docs/benchmarks/real-device-gate-prep08/`의 증거·재현/조립/검증/보존 스크립트다. 기존 파일 7,275개를 대조하여 승인된 기존 소스 두 파일 외 내용·mode·symlink 변경이나 삭제가 없음을 확인했다. 원 B03 frozen sidecar 5개와 보존 APK도 별도로 대조했다. PREP01–PREP07 보고서·원 실패 증거, B11 승인 자료, deferred T6.9와 기존 작업을 보존했다.

Git index SHA-256은 전후 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, index path/mode/blob identity SHA-256은 전후 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. [정확한 index entry 목록](../../../benchmarks/real-device-gate-prep08/git-stage-identities.json)을 제공한다. PREP08은 Git index를 수정하지 않았다. Reset·stash·clean·checkout·rebase·restage·commit·push·배포는 수행하지 않았다.

모든 검증 process 종료, controller의 자식 회수와 HTTP fixture close를 확인한 뒤, PREP08이 새로 만든 `work/real-device-gate-prep08`만 정리했다. 원 소스 사본·최종 patch·실패/성공 압축 로그·JSON·JUnit·각 시도 raw marker/PID/명령·회수 proof archive는 증거에 보존했다. [artifact-cleanup.json](../../../benchmarks/real-device-gate-prep08/artifact-cleanup.json)에 생성·삭제 항목과 회수 크기를 기록했다. 기존 SDK·AVD·APK·cache·자료는 정리하지 않았다.

B03 synchronization semantics와 source identity guard, B11 binding, 제품 금융·동기화·production configuration은 **UNCHANGED**다. 운영 API 요청·large-N·T6.9 측정·T6.9 증거 작업은 수행하지 않았다. 이관 의무 수용은 **0/8**, formal T6.6F closure는 NOT AUTHORIZED, R1은 CLOSED, production deployment는 NOT AUTHORIZED다. Commit은 NONE, push는 NOT PERFORMED다.

[PREP09 독립 검토 인계](../../../benchmarks/real-device-gate-prep08/prep09-independent-review-handoff.json)는 최종 source 신원, 새 증거·scratch 경로를 사용하는 재실행 명령과 검토 조건을 제공한다. 최종 분류는 **PASS — FC01 DISPATCH BYPASSES CLOSED BY SELF-TEST**이며 F01의 해결·독립 수용·실기기 승인을 뜻하지 않는다.

**다음 행동: PREP09의 비참여 독립 검토자가 실제 ADB·에뮬레이터·물리 기기 접근 없이 원본 8개 우회와 공통 거부 경계, 시험 어댑터 격리 및 N01/F02/F03 보존을 별도 증거 경로에서 재검증한다.**
