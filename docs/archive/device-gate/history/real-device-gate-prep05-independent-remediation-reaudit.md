# Real-Device Gate PREP05 — F01–F03 독립 재감사와 잔여 차단 판정

**최종 판정: FAIL — CONFIRMED MATERIAL ISOLATION OR TARGETING VIOLATION.**

F02의 호스트 리다이렉트 결함과 F03의 APK 구조 admission 결함은 **독립 종결**한다. F01은 transport 재등록 거부가 보강됐으나 마지막 신원 조회 뒤 변화 모델과 실제 target/host confinement 보증이 남아 있어 **OPEN**이다. 별도로 **PREP05-N01 · HIGH**를 발견했다. 취소 또는 timeout의 자식 정리 중 추가 signal이 들어오면 부모가 종료된 뒤에도 실제 로컬 자식이 쓰기를 계속했다.

전체 FAIL은 원 F01의 모의 반례를 물리 기기 exploit으로 확대해서 정한 판정이 아니다. 새 취소 결함에서 실제 host subprocess의 작업 지속과 불완전한 회수를 재현했기 때문이다. 운영 데이터·운영 endpoint·실제 ADB·물리 Android 기기를 사용하지 않았다. Live emulator smoke는 의도적으로 **NOT RUN**이다.

## 1. 독립성·기준선·허용 범위

검토자는 원 PREP03 독립 감사 세션이며 PREP04 구현에 참여하지 않았다. **REVIEWER INDEPENDENCE: SATISFIED.** 과거 자기 감사 결과도 현재 코드와 직접 재현 결과로 다시 평가했다. PREP04의 자체검증 성공을 독립 수용으로 취급하지 않았다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 기존 파일 **6,944개**, Git index 원문과 staged path/mode/blob identity를 시험 전에 고정했다. 기존 tracked 수정 13개와 미추적 역사 자료를 유지했다. [시작 기록](../../../benchmarks/real-device-gate-prep05/preservation-before.json), [최종 보존 결과](../../../benchmarks/real-device-gate-prep05/preservation.json).

AGENTS, artifact hygiene, project-state/domain-model/known-issues, 서버 authority 경계와 기존 runbook·security 규칙, PREP02–PREP04 보고서·JSON·원 finding register·원 재현기·변경 inventory·실패 회귀를 확인했다. 서버 금융 authority와 모바일 구조·identity·Snapshot·Offline 경계를 바꾸지 않았다. 제품 및 harness source, 테스트 source, 정책 파일은 수정하지 않았다. 생성한 파일은 PREP05 소유 보고서·증거·호스트 fixture뿐이다.

## 2. 원 finding의 정확한 신원

시험 전 [original-finding-reconciliation.json](../../../benchmarks/real-device-gate-prep05/original-finding-reconciliation.json)에 원 register의 정의와 해시를 기록했다. PREP04 matrix 안의 원 finding 사본도 PREP03 register와 동일했다.

| ID | 원 심각도·component | 원 실패와 재현 | 필요한 불변식 | PREP04 의도·남은 불확실성 |
| --- | --- | --- | --- | --- |
| F01 | HIGH · ADB 대상/연결 세대 | `transport_id`를 무시하여 같은 serial의 재등록을 승인. 마지막 조회 뒤 신원 변화 모델도 mutation 수용 | 연결·서버 세대가 바뀌면 권한 폐기; 승인 연결을 소유 emulator에 결합하고 USB/외부 TCP 배제 | transport/server 고정·권한 취소·자식 수명 보강. 실제 socket 결합과 host confinement은 미완결 |
| F02 | MEDIUM · 호스트 backend HTTP | `host_backend_redirect_unauthorized_port`: urllib가 302를 따라 비허용 loopback 포트로 GET | redirect와 허용 밖 목적지 dispatch 거부; backend socket 소유·응답 제한 | `SyntheticHTTP`의 고정 AF_INET 목적지, listener/accepted socket 소유, 3xx·응답 크기 거부 |
| F03 | MEDIUM · APK manifest/resource admission | `apk_new_exported_component`, `apk_missing_transfer_rules`: 문자열 denylist가 새 component와 규칙 참조 누락 수용 | 최종 manifest·권한·authority·backup/transfer/network 구조를 명시 정책과 대조 | 전체 compiled XML 정책과 sealed artifact 연결. 실제 Android installer 성공은 별도 미실행 |

F01은 네트워크 finding이 아니며 F02도 ADB finding이 아니다. 요청서의 ADB·lifecycle 검토는 F01 및 별도 신규 finding에서 수행했다. APK 바이트 고정·교체 방지는 원 F03의 구조 결함과 구분되는 추가 검증 범위로 다뤘다. 원 finding을 재명명하거나 새 규범을 소급 추가하지 않았다.

## 3. PREP04 source와 역사 증거의 대조

[소스 provenance](../../../benchmarks/real-device-gate-prep05/source-provenance.json)에서 실제 `smoke.py`, `guards.py`, `apk-policy.json`, `test_remediation.py` 네 파일의 SHA가 PREP04 source-change-inventory 및 최종 archive와 일치했다. 자체보고만 읽고 다른 source를 시험한 것은 아니다.

PREP04 변경은 기존 `smoke.py` 수정과 신규 guard·정책·시험 세 파일이다. PREP04 시작 snapshot의 관련 backend/mobile·B03·규범·T6.9 파일 **777개**에 차이가 없었다. 원 B03 frozen sidecar 5개의 SHA·mode도 일치했다.

PREP01 C01 75개, PREP02 121개, PREP03 33개, PREP04 98개 manifest 참조의 해시가 모두 일치했다. PREP01 초기 manifest의 갱신 전 보고서 해시 한 개가 현 보고서와 다른 것은 기존 역사 버전 구분이며, PREP03에서 확인한 원문 보존 사본을 유지한다. 어느 역사 증거도 다시 쓰지 않았다.

## 4. 모순처럼 보인 상태와 정확한 실패 시험

**F01 OPEN / NETWORK REDIRECT SAFETY PASS**는 다른 경계의 상태다. 네트워크 성공은 F02를 뒷받침하며 F01의 잔여 target 보증을 수용하지 않는다. 번호 매핑의 모순은 없었다.

**F02 CLOSED BY SELF-TEST / ADB RECONNECT AND CANCELLATION PARTIAL**도 같은 이유로 양립한다. ADB와 lifecycle은 F01 및 추가 수명 보강이다. F02의 범위를 임의로 바꿔 ADB 부족을 F02의 잔여 문제로 넣지 않았다. 이번에 발견한 취소 결함도 F02 재개방 대신 별도 N01로 기록한다.

두 집계에서 남은 실패는 같은 원인이다.

- 집중 33/34: `ADBTests.test_original_identity_changes_after_final_probe_REMAINS_OPEN`. PREP04 원 ID는 `__main__.ADBTests...`이며 독립 runner에서는 module prefix만 `prep05_reviewed_tests`로 바뀐다.
- 역사 회귀 44/45: `adb_identity_changes_after_final_probe`.
- 집중 시험의 실제 실패 assertion: 마지막 `emu avd name` 반환 뒤 `switched=True`가 되고 install 호출에서 `mutated=True`가 되어 `assertFalse(state['mutated'])`가 실패한다.

이는 transport ID 1→2 재등록 시험의 실패가 아니다. 그 재등록은 현재 거부된다. 네트워크 redirect나 APK admission 실패도 아니다. `expectedFailure`를 성공 분자에 넣지 않았으며 두 runner의 실제 exit code도 **1**이었다. [회귀 결과](../../../benchmarks/real-device-gate-prep05/regression-reproduction-results.json).

원 실패 모델은 실제 기기나 `ro.*` 속성을 바꾸지 않고 로컬 상태 flag를 바꾼다. 따라서 이 실패만으로 실제 다른 기기 선택이나 물리 phone 탈취를 입증할 수 없다. 독립 추가 모의에서는 이후 조회가 반환할 fingerprint 상태도 바꿨으나 동일하게 모의 범위다. F01의 실제 target 결합·host confinement 요구가 미완료인 점과 이 모델의 한계를 함께 유지한다.

## 5. F01 판정 — OPEN

기술 상태는 **PARTIALLY FIXED**, finding 수용 결정은 **OPEN — VERIFIED DEFECT REMAINS**다. [개별 결정](../../../benchmarks/real-device-gate-prep05/f01-independent-verification.json).

`smoke.py:70,402,416,441`은 유일한 양수 transport ID, private ADB server의 PID/start time/exe/listener inode, 정확한 serial과 승인 transport를 검사한다. Disconnect·ID 변경·서버 세대 변화·신원 오류·취소에서는 `target_revoked`를 설정한다. 독립 모의에서 마지막 inventory의 ID가 1→2로 바뀌면 mutation은 호출되지 않았고, 원 ID가 돌아와도 같은 session의 권한이 복원되지 않았다. 기존 명시 serial·잘못된 신원 거부 시험도 통과했다.

하지만 원 마지막 조회 뒤 변화 모델은 여전히 mutation을 수용한다. Active ADB 연결과 소유 QEMU socket의 결합, USB 접근과 외부 exact-address TCP 경로 배제, 실제 `-s/-t` 조합의 자격 증거도 없다. 매 명령 사이의 host 재검사나 `-t` 하나로 이 보증 전체가 완성됐다고 인정하지 않는다.

`require_host_confinement()`는 현재 무조건 `PREP04_ADB_HOST_CONFINEMENT_NOT_IMPLEMENTED`를 발생시킨다. `preflight()`와 `boot()` 앞부분에서 이를 호출하며 우회 인자·환경변수는 없다. 독립 검사에서도 build/backend/ADB/emulator 단계 전 exit 1이었다. 이 **진입 차단은 유효한 containment**지만 F01 수정 완료는 아니다. 감사는 차단을 해제하지 않았다.

필요한 최소 범위는 기존 진입 차단을 유지하면서 승인 transport/server의 실제 연결을 소유 QEMU endpoint에 결합하고, USB와 다른 TCP 목적지를 배제하는 launcher를 별도 구현·자격검증하는 것이다. `getprop`을 한 번 더 읽어 간격을 옮기는 것만으로 종결하거나, 관측 불가능한 임의 소프트웨어 변화까지 원자적으로 검출한다는 새 보증을 만들지 않는다.

## 6. F02 판정 — 독립 종결

**ACCEPTED CLOSED — INDEPENDENTLY VERIFIED.** [개별 결정](../../../benchmarks/real-device-gate-prep05/f02-independent-verification.json).

`guards.py:49,71`과 실제 `Harness.backend()`를 검사했다. 임의 URL 대신 허용 method/path만 받고, 실제 `connect()`는 고정 AF_INET `127.0.0.1:18081`이다. Listener와 해당 accepted socket이 기동 process에 속하는지 HTTP bytes를 보내기 전에 확인한다. DNS resolver·환경 proxy·urllib redirect handler를 쓰지 않는다.

독립 fixture는 감사 process가 실제로 소유한 loopback listener·accepted socket을 `/proc`에서 검사했다. 별도 관측 서버를 비허용 목적지로 두고 **GET identity와 POST 403 확인 각각 301/302/303/307/308**을 반환했다. 실제 `Harness.backend()`가 모두 `HOST_REDIRECT_REJECTED`로 실패했고 비허용 서버에 도달한 HTTP 요청은 **0회**였다. 허용 밖 URL/query/IPv6 경로는 socket 생성 전 거부했다. 실제 connect 인수도 모두 고정 목적지였다.

집중 8개를 새 독립 runner에서 다시 실행해 다른 PID listener 거부, accepted socket 소유 실패 시 HTTP bytes 0, body 크기·truncation 거부와 backend 기동 실패도 확인했다. 상속 proxy와 DNS 함수를 금지한 조건도 통과했다. 변경하지 않은 Flutter transport의 exact origin·route·redirect·DIRECT 통제도 원 12개 host 시험에서 재확인했다.

종결 범위는 이 HTTP 경로다. Host 전체 방화벽·악성 kernel/NAT 방어 또는 F01의 ADB confinement까지 PASS로 확장하지 않는다.

## 7. F03 판정 — 독립 종결

**ACCEPTED CLOSED — INDEPENDENTLY VERIFIED.** [개별 결정](../../../benchmarks/real-device-gate-prep05/f03-independent-verification.json).

`admit_apk()`는 원 denylist를 compiled XML 전체 구조 대조로 바꿨다. 원 exported component 추가와 transfer 규칙 참조 누락, 잘못된 package·signer, 권한·authority·component 보호·network/backup/share resource 변경을 거부했다. APK policy는 version/resource ID 변화도 자동 수용하지 않는다. 이는 기존 F03의 요구와 직접 대응한다.

실제 보존 APK를 `Harness.admit_built_apk()`에서 새 sealed memfd에 복사하고 같은 fd로 SDK `aapt`·`apksigner`를 실행했다.

| 실제 검사 항목 | 결과 |
| --- | --- |
| APK | `money-note-prep02-devicegate-debug-6cf3fb018f7f.apk`, 76,489,882바이트 |
| SHA-256 | `e0ca26b0d05d57242c80d004a8defc7b080f0f579000ced21f0ac99254643582` |
| package | `kr.re.hjkerman.money_note.devicegate` |
| 테스트 인증서 SHA-256 | `f0764baf3b392975a28ca69bf743b76b732f7d7f014f5e480511901f43fd40a7` |
| 서명/구조 | signer 1개, v2 검증 및 compiled manifest/XML 정책 대조 통과 |

`install_verified_apk()`의 mutation 전송만 안전한 로컬 소비자로 대체해 **검사한 바로 그 sealed fd·inode**를 실제 자식 stdin으로 읽었다. 읽은 전체 APK의 SHA가 동일했다. 별도 작은 파일 fixture에서 pathname을 교체해도 소비된 것은 원 sealed bytes였고, seal 이후 쓰기·크기 변경과 pin 이전 hash 불일치도 거부했다.

검사 실패를 주입하면 `apk_admitted=false`가 유지되고 설치 함수가 `APK_NOT_ADMITTED`로 거부했다. Production APK fallback은 없다. Production signing secret은 읽지 않았고 새 키도 만들지 않았다.

여기서 실제로 검증한 설치 경계는 installer에 전달할 stdin 바이트까지다. 실제 Android 설치 성공, 새 APK 빌드와 emulator smoke는 수행하지 않았다. 이 한계를 숨기지 않으며 이를 이유로 원 구조 finding을 임의로 확대하지도 않는다.

## 8. 신규 material finding — PREP05-N01 · HIGH

**OPEN — VERIFIED DEFECT REMAINS.** 원 F01–F03의 번호는 보존한다. [잔여 위험 register](../../../benchmarks/real-device-gate-prep05/residual-risk-register.json), [실제 취소 재현](../../../benchmarks/real-device-gate-prep05/cancellation-independent-results.json).

영향 위치는 `smoke.py:223–235`의 `run()` finally, `smoke.py:239`의 별도 process 등록 경로, `smoke.py:626`의 취소 handler, `guards.py:230–249`의 `stop_group()`이다.

실패 순서는 다음과 같다.

1. `run()`이 새 process group의 로컬 Python 자식을 시작한다. 자식은 SIGTERM을 무시하고 감사 소유 marker에만 짧게 쓴다.
2. 취소 또는 timeout으로 `run.finally → stop_group()`에 진입한다.
3. SIGTERM 뒤 SIGKILL 전 0.1초 유예 중 추가 SIGTERM이 handler의 `InterruptedError`를 발생시킨다.
4. SIGKILL·wait/reap과 뒤의 exit code·압축 진단 저장이 건너뛰어진다.
5. 이 자식은 `start()`의 자식과 달리 `self.processes`에 등록되지 않았다. 바깥 `finish()`도 회수하지 못한다. `execute.finally`의 signal ignore는 이미 늦다.

두 안전한 host fixture에서 모두 부모가 exit 1이고 `target_revoked=true`인데 자식이 살아 있었다.

| 재현 | 부모 종료 시 marker | 0.16초 뒤 marker | 결과 |
| --- | --- | --- | --- |
| 첫 취소 정리 중 두 번째 signal | 5바이트 | 45바이트 | 부모 종료 뒤 쓰기 지속 |
| timeout 정리 중 signal | 130바이트 | 170바이트 | 부모 종료 뒤 쓰기 지속 |

두 경우 `commands.json`은 바깥 finish가 남겼지만 해당 명령의 exit code와 압축 진단은 결측이었다. 단순히 process가 zombie인지 추측한 결과가 아니라 **부모 종료 뒤 실제 파일 크기가 증가한 관측**이다. 감사 controller가 정확한 task 자식 process group을 강제 종료하고 reap했으며 `/proc` 부재도 따로 확인했다. Fixture는 4초 자동 종료 상한도 가졌다.

`run/execute/finish`는 실제 구현을 사용했다. Preflight의 작업만 합성 host child로 대체했고, `stop_group` wrapper는 진입 시점을 관측한 뒤 원 함수를 그대로 호출했다. 실제 ADB나 알려진 위험이 있는 live emulator harness를 실행한 것은 아니다.

요구 위반은 취소 뒤 자식 작업 지속과 실패 증거 누락이다. 현재 정상 CLI의 진입 차단은 유지돼 실제 기기 작업은 시작할 수 없지만, 그것이 이 실제 lifecycle 실패를 수정한 것은 아니다. 집중 시험의 단일 signal·timeout·spawn 취소 5개가 통과해도 정리 중 재진입 취소까지 수용한 근거가 되지 않는다.

**최소 수정 범위:** `run.finally`의 종료·강제 종료·reap·명령 결과/로그 저장 전체가 추가 취소로 끊기지 않도록 보호하고 pending 취소를 그 뒤 전달해야 한다. 정리 실패에도 바깥 cleanup이 자식을 회수할 수 있게 핸들을 보존해야 한다. 위 두 재현을 회귀에 포함하고 종료 뒤 추가 쓰기 0·자식 부재·exit code/진단 보존을 검사해야 한다. B03·금융·Android 제품 source 변경은 필요하지 않다. 이번 감사에서는 수정하지 않았다.

## 9. 회귀 결과와 실행 제한

| 검증 | 독립 관측 | 남은 실패 |
| --- | --- | --- |
| PREP04 집중 | 33/34, exit 1 | 원 F01 마지막 조회 뒤 변화 1개 |
| PREP03 역사 host 회귀 | 28/29셀, exit 1 | 같은 F01 반례 |
| 역사 원 45개로 환산 | **44/45** | 위 host의 Python suite 1셀을 실제 5개로 풀고 Flutter 12개를 더함 |
| PREP05 추가 독립 검사 | **27/30** | 원 F01 모델 1개 + 신규 N01 두 재현 |
| 기존 Python 안전 suite | 5/5 | 없음 |
| Flutter host 격리 | 12/12 | 없음 |
| npm build | exit 0 | 없음 |
| Backend 회귀 | 72 passed, 44 subtests passed | 없음 |

서로 겹치는 suite의 분모를 더하지 않았다. 원 실패 1개와 새 실패 2개를 다른 성공 숫자로 평균하거나 감추지 않았다. [검증 명령](../../../benchmarks/real-device-gate-prep05/reproduction-invocations.json), [저장소 검증](../../../benchmarks/real-device-gate-prep05/repository-validation.json).

Live emulator smoke는 **금지 / NOT RUN**이다. F01 진입 차단을 유지하고 N01도 해결·독립 재검증되기 전에는 smoke를 허용하지 않는다. 물리 Android 연결·조회·설치, production endpoint, 실제 금융 데이터, N100k/large-N, T6.9 증거, R1과 배포는 전부 미실행이다.

## 10. 보존·정리·권한 상태

HEAD·branch·Git index·기존 6,944개 파일을 보존했다. Index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged path/mode/blob SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`로 전후 동일하다. Reset·stash·clean·checkout·rebase·restage·commit·push는 하지 않았다.

B03 동기화·E3 guard-to-COMMIT·Snapshot/OfflineBaseline·engine source-SHA admission·승인된 binding protocol/B11·production package/signing/configuration은 **UNCHANGED**다. 성능·durability의 새 PASS를 부여하지 않았다. T6.9는 DEFERRED, 이관 의무 수용은 0/8, formal T6.6F closure·production deployment는 NOT AUTHORIZED, R1은 CLOSED다.

자식·검증 subprocess 종료와 HTTP fixture close를 확인한 뒤 PREP05 scratch만 정리했다. Source 사본·임시 DB·build 출력·marker의 증거 사본과 압축 로그·JUnit·SDK 검사 결과는 PREP05 증거에 보존했다. 정확한 삭제 규모와 보존 결과는 [artifact-cleanup.json](../../../benchmarks/real-device-gate-prep05/artifact-cleanup.json)에 있다. 기존 APK·AVD·SDK·cache·PREP01–PREP04 자료는 삭제하지 않았다.

최종 판정은 **FAIL — CONFIRMED MATERIAL ISOLATION OR TARGETING VIOLATION**이며 실기기 실행 권한은 **NOT GRANTED**다.

**다음 행동: 실제 실행 차단을 유지하는 PREP05-N01 최소 수정·회귀 작업을 별도 승인 심사에 제출한다.**
