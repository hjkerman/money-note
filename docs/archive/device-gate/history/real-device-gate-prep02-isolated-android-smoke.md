# Real-Device Gate PREP02 — 테스트 전용 Android 격리와 에뮬레이터 smoke

**최종 판정: PASS — ISOLATED ANDROID EMULATOR SMOKE VERIFIED.** 테스트 package·서명·합성 backend·에뮬레이터 신원과 실제 설치·실행·소형 smoke를 검증했다. 실기기 접근, 운영 backend 요청, large-N 측정, production APK 빌드, commit·push·배포는 수행하지 않았다.

시작과 종료 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 기존 수정 12개와 미추적 역사 자료를 포함한 6,676개 파일을 시작 기준으로 고정했다. 이번 작업이 수정한 기존 파일은 `mobile/android/app/build.gradle.kts` 하나이며, 새 source/configuration 파일은 10개다. 기존 staging은 비어 있었고 index 원문과 staged path/mode/blob identity가 모두 보존됐다.

필수 프로젝트 문서, 보안·runbook, PREP01 본문과 continuation-01 보고서·JSON·실행기, 현재 Android/Flutter 설정, 기존 API·합성 fixture·회귀 테스트, 현행 T6.6C Android gate와 승인된 B11 종결 처분을 읽었다. 과거 채팅 이력에 의존하지 않았다. 서버 API의 금융 projection authority와 기존 모바일 안전성 경계를 유지했다.

## 검증 결과와 증거

최종 실행은 `prep02-6cf3fb018f7f`다. [실행 결과](../../../benchmarks/real-device-gate-prep02/android-smoke-results.json), [대상 재검증](../../../benchmarks/real-device-gate-prep02/emulator-target-verification.json), [다음 행동 결정](../../../benchmarks/real-device-gate-prep02/next-action-decision.json)에 같은 판정을 기록했다.

| 항목 | 결과 |
| --- | --- |
| 에뮬레이터 기반 | 검증 완료: 기존 SDK·API36 이미지·AVD 재사용, KVM 실제 열린 fd 확인 |
| package·앱 저장소 | PASS: 서로 다른 ID, sharedUserId 없음, 테스트 dataDir 실측 |
| 서명 | PASS: 이번 실행에서 생성한 테스트 키와 APK certificate digest 일치 |
| 합성 backend | PASS: 신규 합성 DB, 계정 1·원장 2·현금흐름 1, 비합성 행 0 |
| APK build·install·launch | PASS: 테스트 debug APK 76,489,882바이트, 설치 exit0 |
| 합성 smoke | PASS: 인증 거부·로그인·strict bundle·Snapshot 저장/readback·로그아웃 |
| 실패 경로 | PASS: 설정 누락·금지 주소·의도적 실패 모두 요청 0회, 결과 검사 exit1 |
| 종료 | 테스트 package 제거, 에뮬레이터 exit0, 전용 ADB/backend 종료, 남은 task port 0 |
| 물리 기기·운영 backend·large-N | 접근 없음·접근 없음·측정 0 |

## Android 구성과 production 보존

정확한 production ID는 `kr.re.hjkerman.money_note`, 테스트 ID는 **`kr.re.hjkerman.money_note.devicegate`**다. [variant 증거](../../../benchmarks/real-device-gate-prep02/android-variant-isolation.json)에 merged manifest와 실제 APK 검사를 연결했다.

`devicegate` flavor는 명시적인 `assembleDevicegateDebug` 요청에서만 구성된다. 기본 production 경로에는 flavor를 추가하지 않아 기존 `assembleDebug`·`assembleRelease` 및 `app-release.apk` 경로를 유지한다. 비밀 파일을 제외한 build scratch의 task 목록에서도 기존 unflavored task 두 개를 확인했다. Production defaultConfig·release signing·sharedReleaseKey 본문은 기존 바이트와 일치하며, 기존 manifest·권한·Dart 진입점은 수정하지 않았다. Production release APK와 production 서명 검증은 이번 범위에서 실행하지 않았다.

테스트 label은 `Money Note PREP02 TEST`, version suffix는 `-PREP02-TEST`다. 테스트 dataDir는 `/data/user/0/kr.re.hjkerman.money_note.devicegate`로 확인했다. sharedUserId가 없으며 production package는 검증된 에뮬레이터에 없었다. Production APK를 함께 설치해 격리를 시험하지 않았다.

테스트 overlay는 cloud backup과 device transfer의 모든 저장 영역을 제외한다. 알림 listener·production MainActivity·FileProvider·다른 앱 조회, 알림·배터리 예외·APK 설치 특별 권한을 제거한다. 전용 Activity는 알림·공유·업데이트·import bridge를 등록하지 않는다. 테스트 화면에는 운영 로그인·데이터 import·restore 흐름이 없고 backend restore 경로도 허용하지 않는다. 이 변경은 테스트 source set에만 적용된다.

## 테스트 서명

[서명 격리 증거](../../../benchmarks/real-device-gate-prep02/signing-isolation.json)의 certificate SHA-256은 다음과 같다.

```text
f0764baf3b392975a28ca69bf743b76b732f7d7f014f5e480511901f43fd40a7
```

`deviceGateTest` 설정은 task scratch에서 `keytool`로 새로 생성한 30일 RSA 2048 테스트 키를 사용했다. 공개 subject는 `CN=PREP02 Synthetic Test,O=Money Note Test,C=KR`다. `keytool`의 공개 certificate digest와 `apksigner verify --print-certs` 결과를 대조했다. 개인키나 비공개 자격정보를 보고서·Git에 넣지 않았다.

테스트 Gradle 분기는 production `key.properties`를 열기 전에 선택하며 production signing 환경변수도 읽지 않는다. Build 입력은 source/configuration allowlist로 복사하고 production key.properties·keystore·환경파일을 제외했다. 기존 production 서명 선택 본문은 보존했다. 실패 이력까지 포함해 생성한 테스트 개인키 6개는 검증 종료 후 모두 삭제했다.

## 합성 backend와 네트워크 경계

[backend 격리 증거](../../../benchmarks/real-device-gate-prep02/synthetic-backend-isolation.json)의 호스트 주소는 **`127.0.0.1:18081`**, Android 주소는 **`http://10.0.2.2:18081`**다. 최종 데이터 경로는 `work/dev-data/prep02-6cf3fb018f7f/`였으며 종료 후 삭제했다. 기존 `work/dev-data/money-note.sqlite3`, production DB·Snapshot·환경파일·운영 계정은 사용하지 않았다.

Wrapper는 상속된 Money Note/Vite 설정을 제거한 뒤 신규 DB를 생성한다. 기존 `app.main`, 인증, repository 입력 검증, 금융 계산과 authoritative-state API를 그대로 사용한다. 합성 계정 1개와 합성 원장 2개·현금흐름 1개만 생성했고 서버 평가일은 `2026-10-05`다. 종료된 합성 DB에서 행 수와 합성 표식을 확인했으며 비합성 행은 0, 파일 크기는 221,184바이트였다.

허용 경로는 identity·health·기존 mobile-login/me/logout·authoritative-state뿐이다. 그 밖의 요청은 wrapper에서 403으로 거부하며 실제 `/api/entries` 요청으로 확인했다. 기존 인증·correctness guard를 약화하지 않았다. Backend는 요청 64회, 데이터 16 MiB, 파일별 32 MiB와 유한한 실행시간으로 제한한다. 이 smoke는 새로운 금융 입력을 서버에 재전송하거나 B03 동기화 경로를 수정하지 않는다.

테스트 Gradle과 Dart 진입점은 정확한 주소와 필수 구성이 없으면 실패한다. Client는 정확한 origin·method/path를 다시 제한하고 proxy를 우회하며 redirect를 거부한다. 요청 12회·응답 256 KiB 제한을 둔다. Android network-security overlay도 cleartext 허용 host를 `10.0.2.2`로 제한한다. 다른 포트와 경로 차단은 Dart allowlist가 담당한다. 운영 포트 18080의 실제 연결을 시험하지 않았으며 금지 주소 검증은 네트워크 요청 전에 종료했다.

## 에뮬레이터 신원과 smoke

[기반 재확인](../../../benchmarks/real-device-gate-prep02/prep02-6cf3fb018f7f/foundation.json)에서 Ubuntu 24.04.5 x86_64, Emulator 37.2.12.0, API36 Google APIs x86_64 revision7을 재확인했다. 기존 AVD `money_note_prep01_api36_x86_64`와 2 GiB RAM·2 vCPU·swiftshader·6 GiB userdata·headless/no-snapshot 구성을 유지했다. SDK·AVD를 재생성하지 않았다. 부모 도구에 없는 기존 kvm 그룹은 `sg kvm` 자식에서 활성화했으며 새 그룹·시스템 권한 변경이나 sudo는 없었다.

실제 target은 `emulator-5580`이며 fingerprint는 다음과 같다.

```text
google/sdk_gphone64_x86_64/emu64xa:16/BE2A.250530.026.F3/13894323:userdebug/dev-keys
```

Serial은 단독 신뢰 근거가 아니다. 실행기는 host USB ADB/MTP interface 부재, 전용 loopback ADB 목록, 자기 소유 QEMU PID·binary hash·uid/gid·AVD 경로·실제 KVM fd·console/ADB socket 소유권을 확인한 뒤 Android qemu/API/ABI/AVD/fingerprint를 대조한다. 모든 device command에 정확한 host·port·`-s emulator-5580`을 지정한다. USB·TCP·다른 serial·복수/모호한 transport·unauthorized를 거부하며 자동 대상 전환은 없다.

최종 실행에서는 boot를 포함해 **16회** 전체 identity를 확인했다. 설치, 네 번의 launch, 각 stop·clear, uninstall, shutdown 앞에 재검증 기록이 있다. 실패 시 남은 테스트 package를 제거하는 경로도 기존 PREP02 APK 해시와 일치하는 경우만 허용한다. 임의의 기존 package나 다른 기기는 정리하지 않는다.

설치 전에 `aapt`로 package·label·version·activity·권한·backup·shared UID 부재를 확인하고 `apksigner`로 테스트 서명을 대조했다. APK 설치는 최종 실행에서 약 12.675초, exit0이었다. 네 번의 launch 중 세 번은 의도한 음성 검증이다. 정상 smoke는 **7개 요청**으로 미인증 401, 합성 로그인과 principal 확인, 기존 strict bundle parser, 원장 2행, Snapshot 1개 저장과 정확한 readback, 로그아웃을 확인했다. Snapshot은 8,040바이트이며 SHA-256은 `98d418cca4982fc6f87adc7147588348a70e69d13c4c1699e82dadcb8170ec15`다. 금융 합계를 모바일에서 다시 계산하지 않았다.

최종 테스트 APK는 [산출물 정보](../../../benchmarks/real-device-gate-prep02/test-apk-artifact.json)에 연결했다. 보존 경로는 `work/real-device-gate-prep02/artifacts/money-note-prep02-devicegate-debug-6cf3fb018f7f.apk`, SHA-256은 `e0ca26b0d05d57242c80d004a8defc7b080f0f579000ced21f0ac99254643582`다. 실행별 원 build 경로는 종료 정리 후 폐기됐으며 이 보존 경로를 사용한다.

## 실패 이력과 검증 한계

[시도 이력](../../../benchmarks/real-device-gate-prep02/attempt-history.json)에 전체 6회를 보존했다. 처음 다섯 번을 성공으로 바꾸지 않았다.

| 시도 | 결과와 수정 |
| --- | --- |
| a0a5e35b3f3f | 정적 분석의 불필요 import 경고로 중단; import 제거 |
| 7b149d50ca3d | Gradle DSL의 java 이름 충돌로 build 실패; Base64 import로 수정 |
| 525b0e200d91 | Flutter의 상대 target 경로가 guard에서 거부됨; 프로젝트 기준 경로 검증으로 보정 |
| ce9cf00af057 | APK 검증 후 합성 fixture의 필수 usage_place 누락으로 backend 시작 거부; fixture 입력 보완 |
| 92ccbded22b2 | 신원 검증 후 install의 15초 제한 초과로 비영 종료; 설치 제한을 90초로 명시하고 검증된 task APK 정리 경로 추가 |
| 6cf3fb018f7f | 전체 PASS; 정상 제거·에뮬레이터 exit0·남은 task port 0 |

설정 누락 build는 정확한 backend guard에서 실패했음을 로그로 확인했다. 실제 앱의 설정 누락·금지 backend·의도적 실패는 각각 요청 0회, 고정 실패 코드, 결과 검사 exit1로 확인했다. Python 안전성 테스트 5개는 명시 serial·USB/TCP/모호한 transport 거부, 매 mutation의 검증 선행, identity 거부 시 device command 미실행과 CLI 비영 종료를 확인했다. Flutter 격리·기존 bundle 테스트 31개와 정적 분석도 통과했다.

별도 task scratch에서 `npm run build`와 기존 backend 회귀가 통과했다. Backend는 authoritative-state·auth·financial-state-gaps 72개 및 subtest 44개이며 [회귀 증거](../../../benchmarks/real-device-gate-prep02/repository-validation.json)에 명령·exit·압축 로그·XML을 남겼다. 이 검증들은 실기기 내구성·B03 성능·전체 앱 UI 검증이나 T6.9 observer 자격이 아니다.

두 번째 시도의 Flutter native build hook은 NDK `27.0.12077973`을 추가 확보했다. 기존 NDK28·Emulator·이미지·AVD는 유지했으며 추가 다운로드를 수동 반복하지 않았다. 기존 SDK license SHA-256은 PREP01과 같고 새 license 동의 입력은 없었다. [도구 이력](../../../benchmarks/real-device-gate-prep02/toolchain-adjustment.json)에 자동 취득 로그를 연결했다. 기존 SDK·AVD의 약 6.08 GiB 설치를 재설치했다는 의미가 아니다.

기본 sandbox는 기존 PREP01과 같은 `bwrap` loopback 초기화 오류로 실행 전에 실패했다. 승인 검토된 실행 경로를 사용했고 자동 승인 거부는 없었다.

## 변경 파일과 보존

[정확한 source 변경 목록](../../../benchmarks/real-device-gate-prep02/source-change-inventory.json)의 11개 파일은 다음과 같다.

| 파일 | 목적 |
| --- | --- |
| `mobile/android/app/build.gradle.kts` | 명시적 테스트 flavor·독립 서명·target/endpoint guard |
| `mobile/android/app/src/devicegate/AndroidManifest.xml` | 테스트 label·전용 Activity·component/권한 격리 |
| `mobile/android/app/src/devicegate/res/xml/devicegate_data_extraction_rules.xml` | 테스트 backup·device transfer 제외 |
| `mobile/android/app/src/devicegate/res/xml/devicegate_network_security_config.xml` | 테스트 host 네트워크 제한 |
| `mobile/android/app/src/devicegate/kotlin/com/example/money_note_mobile/DeviceGateActivity.kt` | 테스트 전용 bounded 결과 channel |
| `mobile/lib/devicegate/isolation.dart` | endpoint·route·redirect·자원 제한 |
| `mobile/lib/main_devicegate.dart` | 기존 인증·bundle·Snapshot을 쓰는 합성 smoke |
| `mobile/test/devicegate_isolation_test.dart` | 주소·redirect·자원 제한 음성 검증 |
| `scripts/devicegate/backend.py` | 신규 합성 DB와 기존 API wrapper |
| `scripts/devicegate/smoke.py` | 에뮬레이터 전용 검증·설치·실행·종료 |
| `scripts/devicegate/test_safety.py` | targeting·실패·재검증 순서 oracle |

이 보고서와 `docs/benchmarks/real-device-gate-prep02/`의 증거도 새 파일이다. B03 engine·계측·source guard·frozen source·sidecar, T6.6F/T6.9 binding protocol과 B11 승인 개정은 수정하지 않았다. 실행된 모바일 source 8개, executor와 backend wrapper가 최종 source와 일치함을 해시로 확인했다.

[보존 대조](../../../benchmarks/real-device-gate-prep02/preservation.json)의 index SHA-256은 전후 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged identity SHA-256은 전후 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. 기존 unrelated 파일·역사 증거의 변경·삭제·mode drift는 0개다. [원 frozen source 대조](../../../benchmarks/real-device-gate-prep02/frozen-source-preservation.json)에서도 sidecar 5개의 SHA·mode를 확인했다. Reset·stash·clean·checkout·rebase·restage·commit·push는 수행하지 않았다.

[정리 기록](../../../benchmarks/real-device-gate-prep02/artifact-cleanup.json)에 따라 task-owned 중간 build·복사 source·합성 DB·일시 로그와 테스트 개인키를 정리했다. 논리 크기 약 **3.41 GiB**를 회수했고 최종 테스트 APK 약 72.95 MiB, 압축 로그·시도별 변경 source·JSON/XML 근거를 보존했다. 기존 파일·공유 cache·기존 SDK/AVD는 삭제하지 않았다. 추가 NDK27은 공유 build 도구로 남겼으며 자동 purge하지 않았다. 정리 차단 항목은 없다.

## 이후 gate에 남는 요구

T6.9 PRE01–PRE05는 **DEFERRED**, 이관 의무는 **0/8**로 유지한다. 승인된 B11의 Phase B 행정 종결은 유지하지만 정량 증거 수용·formal T6.6F closure·R1 활성화·production deployment 권한을 발급하지 않는다.

실기기 단계에는 별도 명시적 실행 승인, 정확한 target·APK·서명·fixture·허용 명령·예산·중단/복구 계약이 필요하다. Android driver PRAGMA/VFS·native commit fence·I/O 오류·process death·disk-full·pointer 손상·GC·previous recovery·전원 손실, legacy/old B/J/pending·migration/rollback, R1 recovery, 최근 30 backup/artifact/GC 의무는 이 smoke로 수용하지 않았다. 실제 단말의 latency·memory·전력·thermal 및 정식 gate entry도 별도다. Galaxy S23 FE를 비롯한 물리 기기에는 연결하거나 명령을 보내지 않았다.

**다음 행동: PREP02의 테스트 격리 구성과 에뮬레이터 실행기를 독립 검토한다.** 실기기 gate·T6.9 observer 자격검증·large-N·R1·배포의 실행 허가는 별도로 남는다.
