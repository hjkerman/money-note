> **현재 상태 — 승인 후속 C01: PARTIAL — HOST READY, CONFIGURATION INCOMPLETE.** KVM·최소 SDK 설치·두 번의 헤드리스 guest smoke는 검증했고, 앱 격리 구현은 별도 승인 전까지 차단됩니다. 아래 1–10절은 최초 BLOCKED 시도의 역사 기록입니다. 최신 결과는 11절에 있으며 최초 원문은 `docs/benchmarks/real-device-gate-prep01/continuation-01/original-blocked-report.md`에 보존했습니다.

# Real-Device Gate PREP01 — 헤드리스 Android 환경 기반 점검

**최종 판정: BLOCKED — HUMAN SYSTEM AUTHORIZATION REQUIRED.** 현재 사용자로 `/dev/kvm`을 `O_RDWR`로 열면 `EACCES(13)`가 발생한다. 사용자 PREP01 §3에 따라 그룹 변경은 명시 인간 승인이 필요하다. 권한을 바꾸거나 Emulator·이미지를 설치하지 않았으며, 부팅·APK 설치·Android smoke는 모두 **NOT RUN**이다. 실기기에 연결하거나 기기 명령을 보내지 않았다.

이 보고서는 환경 발견 결과, 미실행 구성안, 앱 격리 결측과 향후 단일 세션 안전 계약을 남긴다. 에뮬레이터 기반을 검증했다는 PASS나 실제 Real-Device Gate 진입 승인을 발급하지 않는다.

## 1. 기준선과 범위

- 저장소: `/home/hjkerman/codex/money-note`.
- 수집 기준 시각: `2026-10-27T08:16:09.826467+00:00` / 한국 시각 `2026-10-27 17:16:09`.
- HEAD: `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`로 예상 historical HEAD와 일치한다.
- 작업 전에 tracked 수정 12개와 다수 미추적 역사 증거가 있었다. 이를 되돌리거나 현재 HEAD의 깨끗한 source로 오인하지 않았다.
- 시작 index SHA256: `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`.
- 시작 `git ls-files --stage -z` SHA256: `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`. staged diff는 비어 있었다.

AGENTS.md, project-state/domain-model/known-issues, development-artifact-hygiene, architecture의 서버 authority 경계, runbook의 개발·Android·검증 절을 적용했다. 서버 DB/API가 금융 projection의 authority이며 모바일의 구조·identity·Snapshot 복구·generation·durable baseline·Offline/pending 경계를 유지한다. 새 금융 계산기나 admission 의무를 만들지 않았다.

현행 규범 근거는 [B §27/§29](t66/b/t66b-hot-cold-design.md), [C §26/§34-B11/§35/§38.8–12](t66/c/t66c-delta-sync-protocol.md), [B11 종결 재판정](t66f-b11-post-amendment-closure-readjudication.md)이다. B11 승인·행정 종결을 물리 기기 실행 승인으로 해석하지 않는다. 이번 사용자 지시는 호스트 준비만 허용한다. 기존 실기기 요구에는 Android driver PRAGMA/VFS, native commit fence, I/O 오류, previous recovery와 내구성 증명이 남는다. 에뮬레이터 성공으로 이 증거를 대체할 수 없다.

[PRE05 결정](benchmarks/t69-pre05/next-action-decision.json)은 외부 observer의 정적 가능성만 인정하고 qualification·실행 GO·두 I25 수용을 부여하지 않았다. 그 결론만 인계했다. PRE05-Q01 계획 작성, observer 구현·자격검증, T6.9 측정이나 baseline 취득을 재개하지 않았다.

원 B03 identity는 다음과 같으며, 현재 미커밋 working tree와 구분한다.

| 구분 | SHA256 |
| --- | --- |
| 원 canonical payload | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| 원 engine | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| 원 frozen archive | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |

[source identity](benchmarks/real-device-gate-prep01/source-identity.json)는 원 sidecar 5개의 바이트·mode가 PRE05 기록과 일치함을 기록한다. archive 복원, engine 재계산, IR07/의무 재수용은 수행하지 않았다. source-SHA guard와 binding protocol을 바꾸지 않았다.

## 2. 읽기 전용 호스트 preflight

실측 원본은 [host-preflight.json](benchmarks/real-device-gate-prep01/host-preflight.json)에 있다. 용량은 수집 시점의 값이다.

| 항목 | 관측 |
| --- | --- |
| 장비 | ASUSTeK `TUF GAMING FX504GM_FX80GM`, version 1.0; 개인 hardware serial은 읽지 않음 |
| OS/kernel | Ubuntu 24.04.5 LTS, `6.8.0-147-generic`, x86_64 |
| 가상화 환경 | `systemd-detect-virt`: `none`; CPU VT-x/`vmx` 노출 |
| CPU | Intel Core i7-8750H, 6코어/12스레드; 현재 affinity 12개 |
| RAM | 총 23.33 GiB, 가용 21.02 GiB |
| Swap | 총 약 8 GiB, 사용 0 |
| root/checkout 여유 | `102,983,340,032 B` ≈ 95.91 GiB |
| 보조 FS 여유 | `/mnt/nextcloud-data`: `593,133,588,480 B` ≈ 552.40 GiB; 용량만 확인, 쓰기/설치 대상 아님 |
| 사용자 | `hjkerman`, uid/gid 1000 |
| 활성 그룹 | hjkerman, adm, cdrom, sudo, dip, plugdev, lxd, docker, render |
| KVM | `/dev/kvm`, `root:kvm`, gid 994, `0660` |
| KVM 접근 | read/write `false`, 일반 사용자 `os.open(..., O_RDWR)` → `Permission denied`, errno 13 |

CPU 가상화 지원과 KVM 노드 존재는 확인됐지만 사용자 KVM 사용은 차단돼 있다. `sudo` 그룹 소속은 이번 변경의 인간 승인이 아니다. shell sandbox의 기본 실행은 `bwrap: loopback: Failed RTM_NEWADDR`로 시작 전에 실패하여 승인 검토된 `require_escalated` 경로를 사용했다. 실행 uid는 계속 1000이며 sudo/root로 실행하지 않았다. 자동 승인 거부는 없었다.

최소 인간 조치는 아래 명령의 **명시 승인 후 관리자 실행**, 이어서 새 로그인이다. PREP01은 실행하지 않았다.

```bash
sudo usermod -aG kvm hjkerman
```

새 로그인에서 `id`, `/dev/kvm` mode와 일반 사용자 `O_RDWR` 접근을 재확인해야 한다. 권한이 계속 부족하면 원인을 보고하고 중단한다. `chmod 666`, root Emulator, software CPU 가속 우회, 커널/bootloader 변경은 사용하지 않는다. Linux Emulator의 VM 가속은 KVM을 사용한다. [Android 가속 문서](https://developer.android.com/studio/run/emulator-acceleration)

## 3. Android 도구와 프로젝트 구성

[android-toolchain-inventory.json](benchmarks/real-device-gate-prep01/android-toolchain-inventory.json)에 절대 경로·source.properties SHA·실제 version 출력·진단 exit code를 저장했다. PATH에 없다는 이유로 SDK 부재를 선언하지 않았다.

| 항목 | 관측 |
| --- | --- |
| Flutter | `/home/hjkerman/.flutter`, stable 3.47.4; framework `9584c6713b324636289d067944a46fd6b49df14b` |
| Dart | 3.13.3, linux_x64 |
| Java/Javac | OpenJDK 17.0.20.1, `/usr/lib/jvm/java-17-openjdk-amd64`; JAVA_HOME 미설정 |
| Android SDK | `/home/hjkerman/.android-sdk`; ANDROID_HOME/ANDROID_SDK_ROOT와 local.properties가 일치 |
| Command-line Tools | `cmdline-tools/latest/source.properties`: 23.0 |
| sdkmanager 실제 출력 | `1.0.16261425`; Android CLI 위임/deprecation·새 버전 안내가 함께 출력됨. 업데이트 안 함 |
| ADB | 절대 경로 `.../.android-sdk/platform-tools/adb`; 1.0.41 / 37.0.1-15733141 |
| Platforms | android-35 rev2, android-36 rev2 |
| Build Tools | 35.0.0, 36.0.0 |
| NDK / CMake | 28.2.13676358 / 3.22.1 |
| 기존 라이선스 | `licenses/android-sdk-license` 41B, nonempty hash 1개; 새 동의 없음 |
| Emulator/이미지 | 현재 SDK와 표준 후보 경로에서 설치 발견 못함; `emulator/`, `system-images/` 없음 |
| AVD | `avdmanager list avd` exit0, 정의 0개 |

SDK 라이선스 파일 존재만으로 아직 없는 Emulator·이미지의 라이선스 충족을 PASS로 표시하지 않는다. 새 동의가 필요한 경우 사용자 승인 전 중단한다. 현재 공식 문서도 sdkmanager의 Android CLI 전환을 안내한다. 따라서 후속 설치에서는 실제 도구의 지원 옵션·package identity를 확인하고 고정해야 한다. [Android SDK 도구 문서](https://developer.android.com/tools/sdkmanager)

프로젝트의 Kotlin Gradle Plugin은 2.2.20, AGP 8.11.1, Gradle wrapper 8.14.3, Java target 17이다. `minSdk/targetSdk/compileSdk`는 Flutter 기본값을 사용하며 **현재 설치 Flutter source에서 각각 24/36/36**임을 확인했다. NDK도 28.2.13676358이다. debug/release와 Flutter profile 경로는 있으나 productFlavor와 applicationIdSuffix는 없다. 기존 호환 플래그와 Gradle heap 설정은 변경하지 않았다.

ADB daemon은 수집 시 `127.0.0.1:5037`에서 listen하지 않아 host 목록 질의가 `Connection refused`였다. kernel에 이미 캐시된 USB interface descriptor에서 ADB(`ff/42/01`)와 MTP(`06/01/01`)는 모두 0개이며 Bluetooth·카메라·hub interface만 있었다. 이 작업의 물리 연결/조작은 **0회**다. `adb devices -l`이 빈 목록을 반환했다고 주장하지 않는다. ADB server·`flutter doctor`·`flutter devices`를 시작하면 USB 자동 연결이 생길 수 있어 실행하지 않았다. 기기 serial·endpoint·개인 저장소는 읽지 않았다. emulator serial도 관측되지 않았다.

## 4. 미실행 헤드리스 구성안

[emulator-configuration.json](benchmarks/real-device-gate-prep01/emulator-configuration.json)의 모든 runtime 값은 **PROPOSED ONLY**다. KVM blocker에서 설치·부팅을 멈췄다.

| 항목 | 후속 구성 후보 |
| --- | --- |
| API / ABI | Android 16 / API36 / x86_64; 현재 target36에 맞춤 |
| 이미지 package | `system-images;android-36;google_apis;x86_64` |
| AVD 이름 | `money_note_prep01_api36_x86_64` |
| AVD home | checkout `work/real-device-gate-prep01-avd`; 기존 AVD 덮어쓰기 금지 |
| 메모리 / vCPU | 2048 MiB / 2 |
| userdata / SD | 최대 4096 MiB / 별도 SD 없음 |
| graphics / VM | `swiftshader` / KVM 필수, `-accel on` |
| UI·스냅샷 | 창·audio·camera 없음, snapshot 저장/복원 없음 |
| console / serial | 후보 port5580 / `emulator-5580`; 실제 identity 아님 |
| 설치 Emulator·이미지 revision | 없음 / 미확정 |

현재 도구가 지원하는 `swiftshader`와 `-no-window`, `-accel on`을 후보로 택했다. 후속 binary의 help와 version을 확인한 뒤 적용하며 옵션 실패 시 자동으로 backend를 바꾸지 않는다. `swiftshader_indirect`는 사용 후보에서 제외했다. [헤드리스 실행 옵션](https://developer.android.com/studio/run/emulator-commandline), [GPU 옵션](https://developer.android.com/studio/run/emulator-acceleration)

이미지의 catalog 가용성·revision·다운로드 크기·checksum·요구 license는 이번에 확인하지 않았다. 설치 시 실제 패키지와 Emulator version을 고정하고 config.ini·binary/이미지 identity를 추가로 기록해야 한다. 시스템 설치나 host Java 교체는 현재 발견 결과상 필요하다고 입증되지 않았다.

추가 디스크 사용은 **20 GiB**, host 잔여는 **15 GiB 이상**, 가용 RAM은 **8 GiB 이상**, 동시 AVD는 1개로 제한하는 준비용 예산안이다. 부팅 180초, 작은 smoke 300초, 종료 유예 60초, host 로그 32 MiB 상한을 제안한다. 이는 실기기 성능 합격선이나 승인된 acquisition 예산이 아니다. 다운로드 직전 여유·예상 expanded 크기를 다시 검사하고 상한 초과면 중단한다. 이번 대형 다운로드는 0B다.

성공 인정에는 같은 AVD의 두 launch cycle에서 정확한 ADB serial → Android boot 완료 → 고정 응답 → 최대 1KiB task marker 쓰기/readback → 깨끗한 종료가 모두 필요하다. process가 존재하는 것만으로 boot PASS로 판정하지 않는다. 이 모든 확인은 **NOT RUN**이다.

## 5. 에뮬레이터 대상 선택 정책

기기 실행 스크립트나 범용 agent-controlled ADB 인터페이스는 구현하지 않았다. 이번 보조 수집기는 host 파일·도구 version·기존 host daemon 목록만 읽으며 device-targeted ADB를 호출하지 않는다.

향후 emulator executor는 다음 정책을 먼저 구현·독립 확인해야 한다.

1. serial 명시 인수가 없으면 실패한다. `emulator-[0-9]+` 형식도 필요조건일 뿐 신뢰 증거로 쓰지 않는다. USB serial·host:port·IPv4/IPv6·mDNS physical serial을 거부한다.
2. 물리 기기 부재를 독립 확인한 뒤 task 소유 emulator PID·binary hash·AVD 절대 경로·config·console/ADB port를 host에서 대조한다. 원격 ADB server와 자동 connect/pair를 허용하지 않는다.
3. 예상 transport 하나만 허용한다. 다른 transport가 있거나 offline/unauthorized·모호한 상태이면 기기 명령 전에 중단한다. 목록의 첫 항목을 선택하지 않는다.
4. host 검증 뒤에만 정확한 `adb -s EXACT_SERIAL`의 제한된 read-only 조회로 qemu identity, API, ABI, AVD 이름과 고정 build fingerprint를 확인한다. 설치/쓰기/종료 직전에도 재확인한다.
5. 모든 기기 명령에 `-s EXACT_SERIAL`을 명시한다. 무지정 ADB, `-d`, `-e`, 환경변수의 default target, 임의 shell 문자열과 자동 재선택을 금지한다.

예상하지 않은 기기 identity를 확인하려고 물리 기기에 probe를 보내지 않는다. host 단계에서 거부한다. 이 정책의 실제 negative/identity 검증도 emulator가 없어 이번에는 실행하지 않았다.

## 6. 앱 격리 판정과 좁은 제안

**TEST APPLICATION ISOLATION: BLOCKED.** 상세 source와 결측은 [application-isolation.json](benchmarks/real-device-gate-prep01/application-isolation.json)에 있다.

| 경계 | 현재 상태와 영향 |
| --- | --- |
| package | 모든 기본 variant의 ID가 `kr.re.hjkerman.money_note`; 별도 test ID 없음 |
| signing | hasReleaseSigning이면 debug도 sharedReleaseKey 사용. key.properties는 존재하며 내용·키는 읽지 않음. 독립 test signing 보장 없음 |
| endpoint | 기본 `http://10.0.2.2:18080`; 기본 main/bootstrap이 이 client를 생성. 운영 port에 향할 수 있어 무수정 실행 금지 |
| backend/account | 별도 기기용 합성 backend·account 미구성. 운영 서버의 계정만 나누는 것으로 장부가 격리되지 않음 |
| fixture | host 테스트용 합성 fixture 존재. Android 전용 seed/진입점/검증 harness 없음 |
| 저장소 | package sandbox 기반 secure storage/preferences·documents·files·cache. 같은 ID 설치는 기존 앱/데이터를 공유·갱신할 수 있음 |
| 권한 | INTERNET, POST_NOTIFICATIONS, 배터리 예외 요청, APK 설치 요청 및 알림 listener 존재. 특별 접근을 주면 개인 알림 관측 가능 |
| Android 통합 도구 | integration_test 의존성·mobile/integration_test·test_driver 없음. 기존 이름의 *integration_test.dart는 host flutter_test/HTTP 계층 시험 |

일반 로컬 경로는 documents의 `offline-mode/`와 `snapshots/`, privateRoot의 `segmented-store-v1/`, `segmented-e4-workspace/`다. native 알림은 `filesDir`·private preferences, 공유 파일은 `${applicationId}.shared_files` provider의 cache 하위 `ai-audit/`, `apk-updates/`다. 이 source 경로를 확인했을 뿐 설치된 앱의 private directory를 탐색하지 않았다. segmented 저장은 명시 opt-in 경로이며 ordinary startup에 등록하지 않았다. R1은 여전히 CLOSED다.

후속 narrow proposal은 `devicegate` flavor의 **`kr.re.hjkerman.money_note.devicegate`**, production key로 fallback하지 않는 test-only signing, 소형 합성 fixture와 전용 entrypoint다. 생산 ID·서명은 유지하고, test overlay에서 최소 smoke에 필요 없는 listener·특별 접근·다른 앱 공유/업데이트 경로를 배제하는 방안을 검토한다. 권한을 넓히지 않는다. 이는 제안이며 이번에 Gradle/Manifest/제품 Dart를 수정하지 않았다.

전용 entrypoint는 명시 endpoint를 검사한 뒤 client를 만들고 운영 default로 fallback하지 않아야 한다. emulator 후보 endpoint는 `http://10.0.2.2:18081`이며 host의 개발 API는 `127.0.0.1:18081`과 task 소유 합성 데이터만 사용한다. production port18080, 실제 credential·DB·Snapshot·알림 기록을 사용하지 않는다. 별도 package의 fresh storage와 실제 APK package/signing/merged permission을 검증하기 전에는 설치하지 않는다. 금융 알고리즘·B/J 형식·source guard·protocol을 변경할 필요는 없다.

## 7. smoke와 저장소 검증 결과

[emulator-smoke-results.json](benchmarks/real-device-gate-prep01/emulator-smoke-results.json)에 boot, writable storage, 재부팅 재현성, APK build/install/launch, package/signing/data 격리, Android integration, app 로그 회수, 의도된 test 실패 nonzero 확인을 각각 **NOT RUN**으로 기록했다. Emulator process 0, APK build/install 0, 앱 실행 0, device-targeted ADB 0이다. 실패 exit 전달 능력도 기기에서 검증하지 않았다.

AGENTS의 npm build·backend 검증은 기기를 사용하지 않고 별도 task scratch에서 완료했다. [repository-validation.json](benchmarks/real-device-gate-prep01/repository-validation.json)에 정확한 argv/cwd·제한 시간·환경 격리·exit code와 압축 로그를 보존했다.

| 검증 | 결과 |
| --- | --- |
| `npm run build` | 최종 PASS, exit0. TypeScript와 Vite 포함 |
| backend bounded regression | PASS, exit0; 47 passed, 14 subtests passed |
| 전체 backend/Flutter/Android suite | NOT RUN |
| Emulator smoke / 실제 기기 계측 / large-N | NOT RUN / 0 / 0 |

frontend의 첫 scratch build는 상대 import가 가리키는 기존 합성 `backend/tests/fixtures/confirmed_recurring_actual.json` 사본이 없어 TS2307로 실패했다. 해당 fixture 하나만 scratch에 추가한 동일 build는 PASS였다. 원본 소스/config는 수정하지 않았고 첫 실패 로그도 보존했다. 이미 통과한 backend는 반복하지 않았다.

backend 명령은 아래이며 모든 temporary DB/backup은 task TMPDIR에 한정했다. MONEY_NOTE_/VITE_ 상속 환경을 제거하고 task DB 경로를 지정했다. production 요청이나 개발 서버 기동은 없었다.

```text
/home/hjkerman/codex/money-note/.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_financial_state_gaps.py tests/test_toll_freeze_audit.py --basetemp=/home/hjkerman/codex/money-note/work/real-device-gate-prep01-x_c_5_ik/tmp/pytest --junitxml=/home/hjkerman/codex/money-note/docs/benchmarks/real-device-gate-prep01/backend-bounded-regression.xml
```

실행 cwd는 checkout `backend/`다. frontend 검증 cwd는 task scratch `validation/frontend/`이고 argv는 `npm run build`다. 기존 node_modules는 읽기 링크로 사용하고 공유 cache는 사용하지 않았다. 기존 generated dist·cache를 지우거나 갱신하는 정리는 하지 않았다. 이 결과는 host repository 검사이며 emulator/물리 성능이나 격리 PASS의 대체 증거가 아니다.

## 8. 향후 한 세션 물리 기기 안전 계약

[physical-device-safety-contract.json](benchmarks/real-device-gate-prep01/physical-device-safety-contract.json)은 **PREPARED — HIGH-LEVEL, NOT EXECUTION AUTHORIZATION**다. 실행기·승인된 serial·APK·시간/자원 예산은 아직 없으며, 필수 값이 비어 있으면 기기 연결 전에 중단한다.

순서는 **host/emulator 준비 → 독립 preflight → 소유자 명시 승인 → 고정 acquisition 한 번 → 제한된 증거 추출 → 기기 분리 후 host 분석**이다. 실행 전 source/plan/executor/APK/ADB/fixture hash, 정확한 serial·OS/build·test package/signing·backend·account·허용 argv/앱 상대 경로·각 단계와 전체 timeout·데이터/로그/메모리 상한·여유 공간·부분 실패 처분을 고정한다.

최종 executor는 실행만 하며 각 단계의 exit를 검사하고 예상 밖 오류·identity 변화·예산 초과에서 nonzero로 fail-stop해야 한다. 실행 중 code 수정, APK rebuild, 임의 ADB/shell 생성, 계획 변경, 대상 자동 전환과 실패 후 확대 캠페인은 금지한다. 개인 앱·알림·사진·공유 저장소, 전체 logcat/dumpsys/bugreport, root/remount/reboot/bootloader·광역 settings/appops/pm 조작에 접근하지 않는다. 허용된 test package 파일과 자기 PID 로그만 제한 수집한다.

진행 상태와 hash를 host에 단계별 기록하고 중단 시 이미 받은 partial evidence를 보존한다. 추출도 승인 allowlist·예산 안에서만 하며 USB 단절 시 재연결·다른 serial·clear/uninstall을 자동 시도하지 않는다. 추가 수집은 새 검토와 승인을 받는다. 개인 일상 단말의 전원 차단·강제 재부팅은 자동 포함하지 않는다. 이 제한이 미완료 Android 내구성 의무를 면제하지는 않는다.

실제 Galaxy S23 FE의 현재 OS·API·저장공간·serial은 조사하지 않았다. runbook의 Galaxy S23 FE/One UI 설명은 기존 목표 정보이며 이번 실측 값이 아니다.

## 9. 증거·보존·정리

필수 산출물은 [host-preflight](benchmarks/real-device-gate-prep01/host-preflight.json), [toolchain](benchmarks/real-device-gate-prep01/android-toolchain-inventory.json), [emulator 구성안](benchmarks/real-device-gate-prep01/emulator-configuration.json), [smoke](benchmarks/real-device-gate-prep01/emulator-smoke-results.json), [안전 계약](benchmarks/real-device-gate-prep01/physical-device-safety-contract.json), [다음 행동 결정](benchmarks/real-device-gate-prep01/next-action-decision.json)이다. 실제 핵심 명령·도구 version·exit 원문은 [command-invocations.json](benchmarks/real-device-gate-prep01/command-invocations.json)과 host 수집 source에 남겼다. 미실행 launch argv는 구성안과 명시적으로 구별한다.

보존 대상은 작업 전 tracked/untracked **6,578개 파일, 798,948,710 B**와 외부 원 B03 sidecar 5개다. 시작 SHA/mode manifest와 종료 대조 결과는 [preservation-before.json](benchmarks/real-device-gate-prep01/preservation-before.json), [preservation.json](benchmarks/real-device-gate-prep01/preservation.json)에 있다. 전 파일과 sidecar가 일치했고 Git index 원문·staged path/mode/blob·HEAD도 동일했다. 기존 수정 파일, B01–B11 및 PRE01–PRE05 역사 증거와 binding protocol을 보존했다. 새 저장소 파일은 이 보고서와 PREP01 증거 디렉터리로 한정한다.

task scratch는 `work/real-device-gate-prep01-x_c_5_ik` 하나였다. frontend 사본·build 출력·소형 합성 DB·pytest 임시물·원문 로그만 만들었다. 증거에 압축 로그와 JUnit·명령/결과를 옮긴 뒤 task 소유와 비활성을 확인해 파일 538개, 링크 149개를 정리했다. 파일 logical bytes는 6,688,720B이고 확인된 allocated bytes는 약 7.74 MiB다. 링크의 기존 node_modules 대상은 보존했다. 최종 삭제 경로·용량·결과는 [artifact-cleanup.json](benchmarks/real-device-gate-prep01/artifact-cleanup.json)에 기록했다. 기존 cache·역사 DB/증거·production 데이터는 삭제하지 않았다. 대형 benchmark 산출물 정리는 NOT APPLICABLE이다.

## 10. 판정과 다음 행동

| 항목 | 최종 상태 |
| --- | --- |
| PREP01 | **BLOCKED — HUMAN SYSTEM AUTHORIZATION REQUIRED** |
| KVM 사용자 접근 | BLOCKED |
| Headless boot / emulator smoke | NOT RUN / NOT RUN |
| Test application isolation | BLOCKED — 좁은 제안만 준비 |
| 실기기 연결·접근 / 측정 | 없음 / 0 |
| Large-N / N100k 취득 / 새 immutable graph | 모두 0 |
| Real-device 안전 계약 | PREPARED; executor·기기 실행 승인 없음 |
| T6.9 예비 작업 | DEFERRED — PRE05 PRESERVED |
| Phase B | ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED |
| Phase B 정량 증거 / 이관 의무 독립 수용 | INCONCLUSIVE / 0 of 8 |
| Formal T6.6F closure / R1 | NOT AUTHORIZED / CLOSED |
| 운영 배포 / commit / push | NOT AUTHORIZED / NONE / NOT PERFORMED |
| 제품 source / binding protocol / Git index 수정 | 모두 없음 |

**다음 행동은 하나다. 사용자 PREP01 §3에 따라 kvm 그룹 변경을 명시 승인한 뒤 관리자가 `sudo usermod -aG kvm hjkerman`을 실행하고 새 로그인 세션을 제공한다.** 그 전에는 설치·부팅을 진행하지 않는다. 이후에도 Emulator/이미지 license, 실제 version/config와 앱 격리 구현·smoke는 별도 미완료 조건으로 남는다.


## 11. 승인 후속 C01 — 현재 결과

**PARTIAL — HOST READY, CONFIGURATION INCOMPLETE.** KVM 실행·최소 사용자 SDK 설치·두 번의 헤드리스 guest smoke를 확인했다. 테스트 전용 앱 격리는 미구현이고 제품 source 변경은 별도 승인 대상이므로 APK build/install/launch와 Android 앱 integration은 실행하지 않았다. 물리 Android 기기의 연결·접근·조작은 없었다.

## 승인·기록 경계

사용자는 kvm 그룹 추가와 새 로그인을 수행했다고 알리고, 최소 user-local Emulator·호환 이미지·AVD 설치 및 emulator-only smoke를 명시 승인했다. 새 SDK license 동의, 추가 sudo/시스템 변경·넓은 권한, test flavor/제품 source 변경, 실제 기기 실행은 승인하지 않았다. 후속 “continue”도 새 약관 동의로 해석하지 않았다.

최초 BLOCKED 결과는 상위 PREP01 디렉터리의 원 JSON에 그대로 남아 있다. 당시 보고서는 [original-blocked-report.md](benchmarks/real-device-gate-prep01/continuation-01/original-blocked-report.md)에 원 바이트로 보존했다. 이 C01은 최초 판정을 소급 PASS로 바꾸지 않는 후속 결과다. 기존 manifest가 가리키는 보고서의 과거 SHA는 이 원문 사본에서 확인할 수 있다. 현재 주 보고서만 새 이력을 추가한다.

## 독립 재확인

| 항목 | 관측 |
| --- | --- |
| 계정 DB | `kvm:x:994:hjkerman`; `id hjkerman`에도 kvm 존재 |
| 도구 부모 | 이전 그룹 목록을 상속해 직접 KVM 접근은 계속 EACCES |
| 실제 작업 자식 | `sg kvm`으로 이미 가입된 그룹만 활성화; uid1000/gid994, sudo/root 아님 |
| `/dev/kvm` | `root:kvm`, 0660; 작업 자식의 read/write·O_RDWR 성공 |
| 실제 KVM 실행 | API12, 4KiB VM·vCPU 생성, HLT 1바이트 `KVM_RUN` → `KVM_EXIT_HLT(5)` |
| Emulator 가속 검사 | `emulator -accel-check`: `KVM (version 12) is installed and usable.` |
| 실제 guest 가속 | 정확한 headless QEMU PID의 uid1000/gid994, `/dev/kvm` 열린 fd를 매 기기 명령 전에 확인 |
| 시스템 변경 | 계정 DB·device mode·kernel·전역 Java·시스템 package 변경 0; 추가 sudo 0 |

[host-preflight.json](benchmarks/real-device-gate-prep01/continuation-01/host-preflight.json), [kvm-verification.json](benchmarks/real-device-gate-prep01/continuation-01/kvm-verification.json), [Emulator 검사](benchmarks/real-device-gate-prep01/continuation-01/emulator-binary-inspection.json)에 원 argv·exit와 관측을 기록했다. 현재 부모 프로세스의 그룹과 실제로 검증한 자식 세션을 구분한다. 향후 실행도 kvm이 활성화된 세션이어야 한다.

## 실제 설치와 license

기존 SDK는 `/home/hjkerman/.android-sdk`다. Flutter3.47.4/Dart3.13.3, JDK17, Command-line Tools23.0, Platform Tools37.0.1, platforms35/36, build-tools35/36, NDK28.2.13676358/CMake3.22.1의 기존 구성을 유지했다. 프로젝트의 min/target/compile SDK는 기존 24/36/36이다.

공식 Google repository XML로 후보 package·revision·archive 예상 checksum/크기를 고정하고 ZIP 중앙 디렉터리만 Range로 읽어 expanded 크기를 먼저 확인했다. [설치 사전 조사](benchmarks/real-device-gate-prep01/continuation-01/package-installation-preflight.json), [용량 조사](benchmarks/real-device-gate-prep01/continuation-01/installation-resource-preflight.json), [설치 결과](benchmarks/real-device-gate-prep01/continuation-01/installation-results.json), [설치 파일 SHA manifest](benchmarks/real-device-gate-prep01/continuation-01/installed-components-manifest.json)를 보존했다.

| 새 사용자 SDK 구성 | 고정 값 |
| --- | --- |
| Emulator | 37.2.12.0, build16428233; CLI package `emulator@37.2.12` |
| 이미지 | `system-images;android-36;google_apis;x86_64`, rev7 |
| Android / ABI | Android16 / API36 / x86_64 |
| 이미지 최소 Emulator | 35.4.9; 설치 버전이 충족 |
| 압축 archive 크기 | 349,654,171B + 1,895,447,397B |
| archive expanded 크기 | 903,291,301B + 4,585,389,445B |
| 실제 license 승인 | 기존 `android-sdk-license` hash `24333f8a63b6825ea9c5514f83c2829b004d1fee`로 두 package 모두 충족 |

초기 Python 문자열 hash는 SDK XML의 공백 정규화를 반영하지 못해 불일치로 보였다. 설치된 SDK의 JAXB `LicenseType`으로 원 XML을 읽고 `getLicenseHash/checkAccepted`를 호출한 결과 두 package 모두 **true**였다. [license-verification.json](benchmarks/real-device-gate-prep01/continuation-01/license-verification.json)이 최종 판정이며 초기 탐색값도 보존한다. `setAccepted`, license 동의 입력이나 우회는 실행하지 않았다. 설치 전후 기존 승인 파일 SHA도 같다.

실제 설치 명령은 다음 두 개다. stdin은 DEVNULL로 두었으며 update/force/yes·license 동의 명령은 쓰지 않았다. 각 argv·cwd·시간·exit·로그와 예산 중단 규칙은 설치 결과 및 보존한 실행 source에 있다.

```text
/home/hjkerman/.android-sdk/cmdline-tools/latest/bin/android --sdk=/home/hjkerman/.android-sdk sdk install emulator@37.2.12
/home/hjkerman/.android-sdk/cmdline-tools/latest/bin/android --sdk=/home/hjkerman/.android-sdk sdk install system-images/android-36/google_apis/x86_64@7
```

현재 sdkmanager가 위 Android CLI에 위임하는 것은 기존 설치 source/help와 [공식 SDK 도구 문서](https://developer.android.com/tools/sdkmanager)로 확인했다. command-line tools나 Java를 교체하지 않았다.

## 실제 AVD·host 예산

| 항목 | 검증한 구성 |
| --- | --- |
| AVD | `money_note_prep01_api36_x86_64` |
| AVD home | checkout `work/real-device-gate-prep01-avd` |
| 별도 사용자 runtime | checkout `work/real-device-gate-prep01-runtime/android-user` |
| RAM / vCPU | 2048 MiB / 2 |
| graphics / 가속 | swiftshader / `-accel on` 및 실제 KVM fd |
| userdata | 실제 6 GiB; 별도 SD 없음 |
| UI / snapshot | `-no-window`, audio·camera 없음, `-no-snapshot` |
| console / serial | 5580 / `emulator-5580` |
| 전용 ADB | loopback5038; 실행 종료 후 server·guest·task port 모두 없음 |
| fingerprint | `google/sdk_gphone64_x86_64/emu64xa:16/BE2A.250530.026.F3/13894323:userdebug/dev-keys` |

이미지/Emulator가 최초 미검증 4GiB 제안을 6GiB로 설정하는 것을 확인했다. 이를 실제 구성으로 명시했고 userdata를 축소·삭제하지 않았다. archive와 6GiB userdata를 함께 계산한 최대 예상 증가는 약 **13.2GiB**로, 승인된 host 증가 **20GiB**, 잔여 **15GiB** 한도 안이다. 이미지·GPU·RAM·vCPU·workload는 바꾸지 않았다. [저장 구성 보정](benchmarks/real-device-gate-prep01/continuation-01/storage-configuration-adjustment.json)에 근거가 있다. 이는 금융/실기기 성능 합격선이나 binding protocol 변경이 아니다.

정확한 launch argv·환경·binary SHA·config 전후는 [emulator-configuration.json](benchmarks/real-device-gate-prep01/continuation-01/emulator-configuration.json), [avd-config-before.ini](benchmarks/real-device-gate-prep01/continuation-01/avd-config-before.ini), [avd-config-after.ini](benchmarks/real-device-gate-prep01/continuation-01/avd-config-after.ini)에 있다. 실행기는 [emulator-only-smoke.py](benchmarks/real-device-gate-prep01/continuation-01/emulator-only-smoke.py)로 보존했다. 완료된 이 실행기의 출력 목적지는 이 C01에 고정되어 있으므로 후속 수집은 새 attempt·새 증거 경로를 먼저 고정해야 한다. 같은 AVD 재현성은 이번 최종 두 cycle에서 실제로 확인했다.

## targeting과 최종 guest smoke

전용 ADB server는 `--one-device emulator-5580` USB filter를 사용하고 mDNS 자동 연결을 끈다. host cache의 물리 ADB/MTP interface가 있거나 예상 밖 transport/포트가 있으면 중단한다. 정확한 task QEMU binary/PID·uid/gid·argv·KVM fd를 먼저 확인하고, 모든 기기 명령에 `-H 127.0.0.1 -P 5038 -s emulator-5580`을 명시했다. 각 단계에서 단 하나의 해당 transport와 Android qemu/API/ABI/AVD/fingerprint를 대조했다. 무지정 ADB, 물리 serial·TCP connect/pair, root·권한 완화·임의 shell 인터페이스는 사용하지 않았다. ADB 옵션의 의미는 [공식 ADB 매뉴얼](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)에 근거한다.

최종 [emulator-smoke-results.json](benchmarks/real-device-gate-prep01/continuation-01/emulator-smoke-results.json)의 두 cycle은 모두 다음을 통과했다.

- 정확한 serial·host identity·KVM fd 및 Android API36/x86_64/fingerprint 일치.
- `sys.boot_completed=1`, 고정 echo 응답.
- `/data/local/tmp`의 task marker **30B** write/readback, 명시적인 guest `sync`, 다음 launch에서 같은 값 readback.
- 고정 `exit 7`의 ADB 비영 종료 전달. 앱 test failure 시험의 대체로 사용하지 않음.
- `emu kill` 후 native exit0 및 transport 제거. 같은 AVD·같은 argv의 두 번째 cycle도 성공.
- host 로그 회수와 private server 종료, 남은 task port 0.

최종 두 boot 대기는 약 **27.10/27.18초**, 해당 smoke 전체는 약 **64.30초**였다. 이는 180초 boot·300초 smoke·60초 종료 유예 안의 환경 준비 진단값이다. phone 성능·large-N·내구성 gate 결과가 아니다. guest sync와 clean exit는 실기기 power-loss proof도 아니다.

운영 ID APK를 빌드·설치·실행하지 않았으며 test APK·앱 integration·앱별 로그·앱 데이터 격리 검증은 **NOT RUN**이다. guest smoke PASS와 전체 PREP01 PARTIAL을 구분한다.

## 실패 이력과 실제 한계

이번 후속에는 준비 검증기의 보정과 한 번의 파일 flush 실패가 있었다. [smoke-attempt-history.json](benchmarks/real-device-gate-prep01/continuation-01/smoke-attempt-history.json)과 `smoke-attempt-01`~`05`에 당시 executor·결과·로그/config를 각각 보존했다.

| 시도 | 원 결과와 처분 |
| --- | --- |
| 01 | ADB listener의 명시 hostname 미지원; server 시작 실패, guest·기기 명령 0 |
| 02 | host 검증기가 일반 QEMU 이름만 기대해 headless binary를 놓침; 기기 명령 전 중단, task process 종료 |
| 03 | emulator가 재저장한 ini의 key/value 공백 파싱 실패; launch 전 중단 |
| 04 | 실제 userdata6GiB와 미검증 4GiB 제안 차이를 거부; launch 전 중단, 전체 host 예산 안의 실제 구성으로 명시 |
| 05 | 첫 cycle PASS, 둘째 boot/identity/응답 PASS 뒤 marker0B로 중단. 명시 flush가 없었던 순서를 수정. 실패 정리 native exit **-6**도 보존 |
| 06 | 명시 guest sync를 포함한 두 cycle 전체 PASS, 두 정상 종료 모두 exit0 |

실제 guest launch는 실패 이력을 포함해 **총 5회**다. 최종 성공 두 번만 있었다고 전체 이력을 줄이지 않는다. 실패는 자동 대상 전환·표본/large-N 확대·제품 수정으로 우회하지 않았다. 물리 기기가 연결된 acquisition은 한 번도 없었다. 외부 Emulator crash/cache 경로는 삭제하지 않았으며 [native-failure-provenance.json](benchmarks/real-device-gate-prep01/continuation-01/native-failure-provenance.json)에 남겼다. 최종 정상 경로 성공으로 과거 -6이나 미완료 Android 내구성 의무를 소거하지 않는다.

## 앱 격리·보존·다음 행동

현재 앱 ID는 계속 `kr.re.hjkerman.money_note`이며 별도 flavor·test signing·합성 backend/account·전용 Android harness가 없다. 기본 endpoint와 debug 서명 공유 가능성 등 최초 분석은 그대로다. [application-isolation.json](benchmarks/real-device-gate-prep01/continuation-01/application-isolation.json)은 **BLOCKED — SEPARATE IMPLEMENTATION AUTHORIZATION REQUIRED**다. 개인 금융 데이터·credential·다른 앱 저장소·알림 접근·권한 grant와 backend 운영 API 사용은 모두 0이다.

[물리 기기 안전 계약](benchmarks/real-device-gate-prep01/continuation-01/physical-device-safety-contract.json)은 PREPARED로 유지한다. 이번 고정 emulator 실행기는 physical executor나 실기기 연결 승인이 아니다. 실제 단말의 serial·OS·저장소는 조사하지 않았다.

이전 npm build PASS와 backend47/subtest14 PASS는 원 범위로 보존했다. 제품 source 변경이 없으므로 이번 후속에서 이 검사를 반복하거나 새로운 앱 PASS로 표현하지 않았다. 이번 검증은 실제 KVM probe, SDK license/설치·identity, host targeting, guest smoke와 정적 산출물 검사다.

시작 시점 기존 tracked/untracked **6,601개 파일**과 원 B03 sidecar5개를 고정했다. 종료 대조는 [preservation.json](benchmarks/real-device-gate-prep01/continuation-01/preservation.json)에 있다. 보고서의 승인된 이력 갱신을 제외한 기존 파일·Git index/staged·HEAD를 보존한다. 최초 보고서 원문도 복사본의 SHA로 확인한다. SDK·AVD·키를 포함한 task runtime은 재사용 자원으로 보존하고, 증거를 옮긴 임시 probe/class·원문 로그·helper만 정리한다. 상세 경로·용량·남은 자원은 [artifact-cleanup.json](benchmarks/real-device-gate-prep01/continuation-01/artifact-cleanup.json)에 있다. 공유 cache나 crash DB는 정리하지 않는다.

T6.9 예비 작업은 **DEFERRED — PRE05 PRESERVED**, Phase B는 **ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED**, 이관 의무 수용은 **0/8**, formal T6.6F closure는 **NOT AUTHORIZED**, R1은 **CLOSED**, production deployment는 **NOT AUTHORIZED**다. source-SHA guard·binding protocol·제품 source·Git index를 바꾸지 않았다. commit/push는 없다.

**다음 행동: 테스트 전용 applicationId·별도 signing·합성 backend와 전용 Android smoke harness 구현 범위를 별도로 승인한다.** 현재 승인에는 이 제품 변경이 포함되지 않으므로 앱 단계는 중단한다.
