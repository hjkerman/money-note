# Real-Device Gate PREP03 — Android 격리와 에뮬레이터 실행기 독립 감사

**최종 판정: FAIL — CONFIRMED ISOLATION OR TARGETING VIOLATION.**

현재 APK의 package·테스트 서명·private 저장소·합성 fixture 분리는 확인했다. 그러나 호스트의 backend 준비 확인이 리다이렉트를 따라 허용되지 않은 origin에 실제 요청하는 동작을 합성 loopback HTTP로 재현했다. 같은 serial의 ADB transport 재등록을 거부하지 않는 경로와 향후 manifest 변경을 놓치는 APK admission도 확인했다. 따라서 PREP02 구성을 현재 상태 그대로 신뢰해 실기기 실행 계획 확정 단계로 넘길 수 없다.

이 판정은 운영 데이터 유출이나 실제 물리 기기 조작을 관측했다는 뜻이 아니다. 이번 감사의 운영 backend 요청, 실제 ADB 호출, 에뮬레이터 실행, 물리 기기 접근은 모두 **0회**다. 제품 수정·프로토콜 개정·commit·push·배포는 하지 않았다.

## 1. 범위·독립성·기준선

검토자는 PREP02 구현에 참여하지 않은 새 감사 세션이다. 제공된 PASS를 전제로 삼지 않고 저장소, 보존 소스, APK와 실행 증거를 다시 대조했다. 독립성은 **SATISFIED**다. 과거 실행을 직접 관찰한 검토자는 아니므로 그 실행에 관한 결론과 이번에 직접 재현한 결과를 구분한다.

- 저장소: `/home/hjkerman/codex/money-note`.
- 확인한 시작 HEAD: `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`; 예상 historical HEAD와 일치한다.
- 시작 시 tracked 수정 13개와 다수 미추적 역사 자료가 있었다. HEAD와 미커밋 working tree를 동일한 source라고 취급하지 않았다.
- 기존 파일 **6,808개**의 내용·mode와 Git index·staged identity를 기록했다. 최종 보존 결과는 [preservation.json](../../../benchmarks/real-device-gate-prep03/preservation.json)이다.
- 필수 지침, 도메인 모델, 알려진 이슈, architecture의 서버 authority 경계, security·runbook, PREP01/C01·PREP02 본문과 기계 증거를 검토했다. 로드맵은 T6.6B §27/29, 규범은 T6.6C §25/26/34-B11/35-T69/38, PRE05 결정과 PREP01 물리 기기 안전 계약을 적용했다.

서버 DB/API의 금융 authority, 모바일 구조·identity·Snapshot 복구·generation·durable baseline·Offline/pending 경계는 유지한다. 새로운 모바일 금융 재계산 의무를 추가하지 않았다.

## 2. 소스 provenance와 보존 APK

[소스 대조](../../../benchmarks/real-device-gate-prep03/source-provenance.json)에서 요청된 **11개 파일 모두** 현재 SHA-256이 PREP02 source-change-inventory와 일치했다. 최종 실행 `prep02-6cf3fb018f7f`에 보존된 모바일 source archive 8개도 현재 파일과 일치했다. 실행기 `executor.py.txt`와 backend 사본도 현재 source와 동일하다.

PREP01 시작 snapshot의 관련 backend·mobile·규범·B03 파일 **694개**를 대조했고, PREP02가 명시적으로 수정한 Gradle 파일을 제외하면 차이가 없었다. 원 B03 frozen sidecar 5개의 SHA와 mode도 일치했다. APK를 새로 빌드하지 않았으므로 재현 가능한 빌드나 source에서 binary까지의 독립적인 빌드 증명까지 주장하지 않는다.

| 실제 보존 APK 검사 | 결과 |
| --- | --- |
| 경로 | `work/real-device-gate-prep02/artifacts/money-note-prep02-devicegate-debug-6cf3fb018f7f.apk` |
| 크기 | 76,489,882바이트 |
| SHA-256 | `e0ca26b0d05d57242c80d004a8defc7b080f0f579000ced21f0ac99254643582` |
| application ID | `kr.re.hjkerman.money_note.devicegate` |
| production ID | `kr.re.hjkerman.money_note` |
| 버전 | `2.4.0-PREP02-TEST`, versionCode 15 |
| SDK | min 24, target 36, compile 36 |
| 실행 Activity | `com.example.money_note_mobile.DeviceGateActivity` |
| 서명 | APK Signature Scheme v2 검증 성공, signer 1개 |
| 인증서 SHA-256 | `f0764baf3b392975a28ca69bf743b76b732f7d7f014f5e480511901f43fd40a7` |

위 값은 실제 SDK의 `aapt dump badging/xmltree`와 `apksigner verify --verbose --print-certs`로 확인했다. 결과는 [APK manifest](../../../benchmarks/real-device-gate-prep03/apk-manifest.txt), [인증서 검사](../../../benchmarks/real-device-gate-prep03/apk-signature.txt)에 보존했다. APK 설치는 하지 않았다.

## 3. Android variant·manifest·서명·저장소

`build.gradle.kts:12–34`는 명시적인 devicegate debug task, 전용 Dart target과 정확한 endpoint·필수 defines를 요구한다. 해당 분기에서만 flavor와 `.devicegate` suffix를 만들고 release/profile devicegate variant는 비활성화한다. 혼합 task나 devicegate release 요청은 거부한다. 기본 production의 unflavored task는 유지된다.

실행기는 새 task scratch에서 전용 APK를 빌드하고 `app-devicegate-debug.apk`만 사용한다. 빌드 실패·파일 누락·잘못된 ID·인증서 불일치에서 멈추며 production APK를 고르는 대체 경로가 없다. 일반 production task에 테스트 entrypoint를 지정하는 역방향 조합까지 Gradle이 금지하지는 않지만, 실제 테스트 entrypoint의 package 검사는 네트워크 전에 이를 거부한다. 이번 Flutter widget 검사에서도 production package 신원을 거부했다.

병합된 APK에서 production MainActivity, 알림 listener, `${applicationId}.shared_files` provider, queries와 특별 권한 3개는 제거됐다. INTERNET 외에는 테스트 package로 구분된 signature 수준의 `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`만 사용한다. sharedUserId는 없다.

의존성 component가 전부 제거된 것은 아니다. ShareFileProvider와 InitializationProvider는 `exported=false`이며 authority도 각각 테스트 package의 `.flutter.share_provider`, `.androidx-startup`이다. SharePlusPendingIntent도 비공개다. ProfileInstallReceiver는 exported이지만 `android.permission.DUMP`를 요구한다. 이들은 현재 APK의 확인된 유출 취약점이 아니며 I01로 기록했다. 향후 component 추가를 자동 차단하는 admission은 F03처럼 불완전하다.

테스트 Gradle 분기는 production `key.properties`를 열기 전에 선택되고 production signing secret을 읽지 않는다. Harness는 source/config allowlist 사본에서 task-owned 테스트 키를 만들고 생성 인증서와 APK signer를 비교한다. 공개 assetlinks에 있는 production 인증서 `e3566d0aea6eb9c3b0011496c7710439e65165e61a36704db5e141875e8dfad5`와 테스트 인증서는 다르다. 개인키와 production signing 설정 파일은 읽지 않았다. Gradle 자체가 외부에서 받은 임의 keystore property의 소유권까지 증명하는 것은 아니며, 해당 보증은 고정 harness의 키 생성 경로에 의존한다.

Production `defaultConfig`, `sharedReleaseKey`, release signing block은 HEAD의 기존 본문과 바이트가 일치한다. 기존 production manifest·진입점·서명 선택 의미에도 변경이 없다. Production APK 빌드·설치·현재 production 인증서 실측은 수행하지 않았다.

테스트 저장소는 별도 package sandbox다. PREP02의 보존 실측 dataDir는 `/data/user/0/kr.re.hjkerman.money_note.devicegate`이며 이번에는 package·shared UID 부재와 저장소 source를 대조했다. Activity 결과 파일은 `filesDir`, Snapshot은 기존 `LocalSnapshotRepository`와 package별 documents를 사용한다. 공용 외부 저장소·개인 데이터 migration·자동 restore 경로는 사용하지 않는다. 남은 share provider의 경로도 자기 cache의 `share_plus/`뿐이며 테스트 진입점은 공유 기능을 호출하지 않는다.

## 4. 백업과 기기 전송

실제 APK에서 `allowBackup=false`, `fullBackupContent=false`, `dataExtractionRules` 참조를 확인했다. [컴파일된 제외 규칙](../../../benchmarks/real-device-gate-prep03/apk-backup-rules.txt)은 cloud-backup과 device-transfer 양쪽에서 `root`, `file`, `database`, `sharedpref`, `external`, `device_root`, `device_file`, `device_database`, `device_sharedpref`의 `.`를 모두 제외한다. 별도 BackupAgent도 없다.

Android 12 이후 일부 제조사에서 `allowBackup=false`만으로 D2D 전송을 막는다고 단정할 수 없으므로, 이 별도 device-transfer 규칙 확인이 필요하다. 현재 APK는 해당 선언을 갖췄다. 실제 제조사 이관·복원 동작은 시험하지 않았다. [Android 공식 백업 설명](https://developer.android.com/identity/data/autobackup?hl=en)

현재 APK의 선언상 백업·전송 통제는 PASS다. 이 참조가 향후 빠졌을 때 harness가 중단하는지는 별개이며 F03 음성 검사에서 실패했다.

## 5. 합성 backend와 네트워크

`backend.py:16–39`는 새 절대 경로 `work/dev-data/prep02-*`의 직접 하위 directory만 허용하고 기존 directory·canonical path 불일치를 거부한다. 상속된 Money Note/Vite 환경을 제거한 뒤 해당 DB를 지정한다. `app/config.py`의 경로 처리도 대조했으며 dotenv를 통한 운영 설정 로딩은 없다.

Fixture는 합성 계정 1개, 합성 제목의 원장 2행, 현금흐름 1행과 고정 평가일 `2026-10-05`다. 기존 API·인증·서버 금융 계산을 사용한다. PREP02의 종료된 합성 DB 점검에는 비합성 행 0개, 파일 221,184바이트가 기록돼 있다. 그 DB는 정리됐으므로 이번에 다시 열지 않았다. 운영 DB·Snapshot·계정·token은 접근하지 않았다.

Backend는 `127.0.0.1:18081`에만 bind한다. Identity·health·mobile-login/me/logout·authoritative-state 외의 경로와 query는 wrapper가 거부한다. Backend 기동 자식이 종료된 모의 조건에서는 `SYNTHETIC_BACKEND_START_FAILED`, exit 1이며 boot·app 단계가 호출되지 않았다. 과거 실제 기동 실패 이력도 같은 방향을 지지한다.

Android client는 다음 통제를 독립 검사에서 통과했다.

- 정확한 `http://10.0.2.2:18081` 설정과 origin·method/path만 허용한다. 누락·운영과 같은 포트 18080·다른 host·userinfo·query·fragment는 underlying transport 전에 거부한다.
- Hostname, 다른 IPv4 표기, IPv6와 IPv4-mapped IPv6를 거부한다. 허용 대상이 고정 IP literal이므로 임의 DNS 해석·DNS 주소 변경으로 다른 host를 승인하는 경로가 없다.
- 실제 request의 `followRedirects=false`와 301/302/303/307/308 거부를 확인했다.
- 진입점은 `HttpClient.findProxy=DIRECT`를 지정한다. 호스트 준비 확인도 `ProxyHandler({})`를 사용하므로 상속 HTTP/HTTPS/ALL_PROXY가 해당 요청을 바꾸지 못한다.
- 요청 12회, 응답 256KiB와 timeout을 제한한다. Backend도 요청 64회·데이터 16MiB·파일별 32MiB·600초 예산을 둔다.

[컴파일된 NSC](../../../benchmarks/real-device-gate-prep03/apk-network-rules.txt)는 기본 cleartext를 금지하고 `10.0.2.2`만 예외로 둔다. 포트·경로는 Dart가 제한한다. 이를 Dart 소유 socket까지 강제하는 OS 방화벽이라고 주장하지 않는다. Flutter 문서도 플랫폼 소유 socket과 Dart/Flutter 소유 socket의 정책 적용을 구분한다. [Flutter 공식 설명](https://docs.flutter.dev/release/breaking-changes/network-policy-ios-android)

**호스트 준비 확인은 F02 때문에 FAIL이다.** 실제 `Harness.backend()`와 urllib를 사용하되 process 시작만 모의했다. 감사 소유 `127.0.0.1:18081` 서버가 302를 돌려주자 다른 임시 loopback 포트의 `/unauthorized-identity`에 GET이 도달했다. Proxy는 사용되지 않았다. 합성 응답의 run ID가 맞으면 검사는 그 뒤에도 수용됐으며, ID가 맞는지 확인하기 전에 이미 목적지 이탈 요청이 발생한다. 실제 운영 주소나 외부 주소로는 요청하지 않았다.

따라서 Android client의 redirect 거부나 PREP02 정상 smoke만으로 전체 host/app 네트워크 격리를 증명할 수 없다. IP literal 검사는 endpoint 소유권·host routing·NAT까지 증명하지도 않는다.

## 6. 모든 ADB 경로와 TOCTOU

PREP02 최종 `commands.json`의 150개 명령 중 기기 ADB 명령은 135개였다. 모두 `-H 127.0.0.1 -P 5038 -s emulator-5580`을 사용했고 `flutter run`은 없었다. 별도 host-only ADB server 시작은 `--one-device`와 `server nodaemon`이다. 이번 감사는 이 명령들을 실행하지 않았다.

| 경로 | 호출 전 보호와 범위 |
| --- | --- |
| 설치·launch | `mutate → verify → read_device`; 전용 APK·component 고정 |
| stop·clear·uninstall | 같은 mutation 검증 경로; test package 고정 |
| 이전 task package 제거 | private APK 경로 확인·pull·기존 PREP02 APK hash 대조 뒤 uninstall |
| 결과 읽기 | host guard 뒤 `run-as`로 test package의 고정 상대 파일만 읽음 |
| 로그 | test package `pidof` 뒤 `logcat --pid`, 최근 120행 제한 |
| 종료 | 검증 후 해당 emulator의 `emu kill` |
| 실패 정리 | identity 검증 실패 시 기기 정리를 진행하지 않고 task가 생성한 host process group만 종료 |

Serial은 정확히 `emulator-5580`이어야 한다. 일반 USB/TCP/IPv6/mDNS serial, USB marker, 복수·중복·offline/unauthorized 목록을 거부한다. `ADB_*`·`ANDROID_*` 환경은 제거·고정하며 host/port/serial도 argv에 명시한다. 잘못된 Android qemu 속성은 mutation 전에 거부했다. 마지막 목록에서 단절이 관측된 모의 조건도 mutation 없이 중단했다.

Positive identity는 serial prefix에만 의존하지 않는다. PREP01 도구 SHA, task QEMU process·exe·uid/gid·argv·KVM fd·console/ADB port socket 소유권·AVD config와 Android qemu/API/ABI/fingerprint/AVD를 확인한다. 보존 실행의 전체 identity 재검증은 16회이며 값은 일관됐다.

그러나 **F01의 TOCTOU 경계는 닫히지 않았다.** `verify()`의 네 getprop와 AVD 조회는 각각 별도 ADB 호출이다. 마지막 Android 조회, host 확인, 마지막 inventory, 새 ADB subprocess의 transport 선택, 실제 mutation은 서로 원자적으로 결합돼 있지 않다. 목록의 `transport_id`도 저장하거나 비교하지 않는다.

실제 `host_guard/verify/mutate/read_device`를 사용하고 OS·ADB 전송만 모의한 검사에서, 신원 조회 중 transport 1이 마지막 inventory에서 같은 serial의 transport 2로 바뀌어도 install argv가 호출됐다. 검증 직후 원격 신원이 바뀌는 별도 모의도 명령을 계속했다. 이는 재연결에 기존 검증 권한을 넘기는 동작의 재현이다. 일반 물리 기기의 serial 거부 우회나 실제 phone 치환을 증명한 결과는 아니다.

`--one-device`는 USB 연결을 제한하는 옵션이며 모든 TCP 대상의 신원을 보증하는 옵션이 아니다. 수동 USB interface 부재 점검에도 점검 뒤 연결이 생길 시간이 남는다. [공식 ADB 매뉴얼](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md)

따라서 절대적인 물리 기기 배제는 현 스크립트만으로 보증할 수 없다. 승인 transport ID와 private server 세대를 고정해 disconnect·재등록 시 권한을 폐기하고, 실제 명령을 그 transport에 결합해야 한다. 여기에 ADB의 USB 접근과 소유 emulator 외 TCP 경로를 막는 host 수준 격리가 필요하다. Transport ID 고정만으로 물리 배제가 완성된다고 보아서는 안 된다. 소유 QEMU의 socket 점검은 유지하되 ADB가 사용하는 연결과의 결합도 검증해야 한다.

## 7. 음성·회귀 검증 결과

[전체 음성 결과](../../../benchmarks/real-device-gate-prep03/negative-test-results.json)는 **45개 중 40개 통과, 5개 기대 거부 실패**다. 호스트 29셀에 포함된 기존 Python suite 1셀을 실제 5개 unittest로 풀어 33개로 집계하고, Flutter 기존 4개와 독립 8개를 더했다. Backend·npm 회귀는 이 분모에 넣지 않았다.

| 검사 | 관측 |
| --- | --- |
| 잘못된 APK ID·signer | 실제 build 검사 AST가 거부 |
| 실제 entrypoint의 잘못된 package·run ID·mode | 요청 0회, 실패 결과 |
| 누락·운영과 같은 주소 설정 | Dart 설정/요청 guard에서 거부; 기존 실제 앱 실패 증거도 요청 0회 |
| Hostname·IPv6·mapped·대체 IP 표기 | underlying send 전 거부 |
| Android client redirect 5종 | 모두 거부 |
| 호스트 준비 확인 redirect | **실패: 비허용 port로 실제 GET, F02** |
| 부적절한 serial·물리 신원·복수/단절 목록 | 거부, mutation 없음 |
| 검증 후 transport 재등록·신원 변화 | **2개 실패: 모의 mutation 계속, F01** |
| allowBackup=false 누락 | 거부 |
| 새 exported component·transfer 규칙 참조 누락 | **2개 실패: admission 통과, F03** |
| Backend 시작 실패 | exit 1, emulator/app 단계 미호출 |
| 앱 smoke timeout | `APP_RESULT_TIMEOUT`, 성공으로 승격하지 않음 |
| 부분 로그 회수 실패 | 예외 전파·FAIL 유지, 직전 app 결과 저장 호출 보존 |
| ADB 환경 덮어쓰기 시도 | 상속 target 제거, 고정 local host/port 유지 |

APK 음성 검사는 실제 `Harness.build()`에서 검증 문장만 AST로 추출해 변형된 aapt/signer 출력을 주입했다. 잘못된 APK를 새로 빌드하거나 설치한 시험은 아니다. 모의 ADB 시험도 실제 기기 명령을 보내지 않았다. Android Gradle 재빌드는 하지 않았으며 설정 누락 빌드 거부는 보존 실패 로그와 동일 source를 대조한 범위다.

[별도 저장소 검증](../../../benchmarks/real-device-gate-prep03/repository-validation.json)은 task scratch의 사본과 새 임시 DB에서 수행했다.

- `npm run build`: exit 0.
- Backend authoritative-state/auth/financial-state-gaps: **72 passed, 44 subtests passed**, exit 0.
- Flutter 격리 host 시험: **12개 통과**, exit 0. 실제 entrypoint의 요청 전 신원 거부도 포함한다.

에뮬레이터 재실행, production APK build, 제조사 backup/transfer, 실제 Android network 계측, 전체 제품 suite, large-N은 수행하지 않았다. 부분 로그 실패 시험은 성공 판정 방지를 확인한 것이며, 실기기용 내구성 있는 단계별 실패 journal까지 자격검증한 것은 아니다.

## 8. Finding register

정확한 위치·조건·영향·조치는 [finding-register.json](../../../benchmarks/real-device-gate-prep03/finding-register.json)에 있다. CRITICAL 0, HIGH 1, MEDIUM 2, LOW 0, INFORMATIONAL 2다.

| ID·심각도 | 위치 | 조건·실패·영향 | 필수 조치 | 에뮬레이터 차단 | 향후 실기기 차단 |
| --- | --- | --- | --- | --- | --- |
| F01 · HIGH | `scripts/devicegate/smoke.py:58,319,331,348` | 검증 뒤 동일 serial의 transport가 바뀌어도 명령 계속. 연결 세대에 대한 fail-stop 보증 결손이며 물리 기기 exploit은 미확인 | transport/server 세대 고정·재연결 취소·동일 transport 명령 결합·USB와 외부 TCP 차단 | 현 harness의 무인 재연결 가능 실행 차단 | 예 |
| F02 · MEDIUM | `scripts/devicegate/smoke.py:388,393,400,405` | 준비 endpoint의 3xx를 따라 비허용 origin에 실제 요청. 다른 service가 포트를 선점하는 startup 구간에서 조건 성립 가능 | redirect 전면 거부·정확한 origin·응답 제한·backend PID/socket 소유 대조·host egress 제한 | 현 네트워크 격리 보증에 의존하는 실행 차단 | 예 |
| F03 · MEDIUM | `scripts/devicegate/smoke.py:265,267,271` | dependency/manifest 변경 때 새 exported component나 transfer 규칙 누락을 놓침. 현재 APK 자체의 유출은 미확인 | 최종 APK의 전체 권한/component/authority/backup/network 허용 구조 검사와 음성 fixture | 이번에 검사한 고정 APK 자체는 차단하지 않음; 변경 빌드는 새 검사 필요 | 예 |
| I01 · INFORMATIONAL | `mobile/android/app/src/devicegate/AndroidManifest.xml:12` | 격리된 dependency provider/receiver가 남음. 현재 노출 결함 아님 | F03의 명시 허용 집합에 반영 | 아니오 | 아니오 |
| I02 · INFORMATIONAL | `docs/benchmarks/real-device-gate-prep01/evidence-manifest.json:1` | 초기 manifest의 보고서 해시는 갱신 전 버전. 원문 보존 사본과 일치 | 역사 버전을 구분해 인용 | 아니오 | 아니오 |

F01을 HIGH로 둔 이유는 물리 기기 조작을 확인해서가 아니라, 본 gate의 명시적인 연결 변경 시 취소 요구가 mutation 경로에서 충족되지 않기 때문이다. F02는 타 origin 요청을 재현했지만 production 접속·credential 유출은 없고, F03은 현재 고정 APK보다 설정 변경 이후의 admission 결손이다. 이 차이를 심각도와 영향에 반영했다.

## 9. B03·E3·금융 계약·규범 보존

관련 기존 파일 694개와 frozen sidecar 대조, PREP02의 정확한 변경 목록을 근거로 다음은 PREP02 전후 **UNCHANGED**다.

- B03 synchronization과 계측·source lock, engine source-SHA admission.
- E3 마지막 authority guard부터 동기 COMMIT까지의 제어 흐름.
- 서버 금융 canonical 처리와 카드 계산 모듈.
- Snapshot v7·OfflineBaseline·input-only journal·pending/reconciliation 계약.
- Production package·서명 선택 의미와 기존 unflavored build 경로.
- T6.6F/T6.9 규범, B11 승인된 이관 계약과 PRE05의 미수용 상태.

전용 smoke는 기존 full authoritative bundle parser와 Snapshot 저장/readback을 사용한다. B03 실제 D/E 계측이나 E3 publication 실행 proof가 아니다. 변경하지 않았다는 소스 결론을 새로운 B03 correctness·성능·실기기 내구성 PASS로 확장하지 않는다. 시작 working tree의 기존 B03/프로토콜 미커밋 변경도 감사에서 새로 만든 변경이 아니다.

## 10. 역사 증거·Git·임시 산출물

PREP01 C01 manifest 참조 75개, PREP02 참조 121개의 SHA가 모두 일치한다. PREP01 초기 manifest 22개 중 현 보고서 하나만 초기 해시와 다르며, 그 해시는 C01의 `original-blocked-report.md`와 정확히 일치했다. 최초 BLOCKED와 C01 결과, PREP02 다섯 실패와 최종 성공을 보존했다. 초기 manifest를 현재 보고서 해시로 다시 쓰지 않았다.

Git index SHA-256은 시작·종료 모두 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged identity는 모두 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. HEAD·branch·기존 6,808개 파일에도 내용/mode 회귀가 없다. Reset·stash·clean·checkout·rebase·restage·commit·push를 실행하지 않았다.

감사 전용 복사 source·build 출력·pytest 임시 DB는 `work/real-device-gate-prep03`에 한정했다. 모든 소유 subprocess 종료와 HTTP 서버 close 뒤, 증거·JUnit·압축 로그를 보존하고 해당 scratch만 정리했다. 보존한 재현기와 JSON은 모두 PREP03 증거 directory에 있다. 정확한 생성·삭제 크기와 정리 결과는 [artifact-cleanup.json](../../../benchmarks/real-device-gate-prep03/artifact-cleanup.json)에 기록했다. 기존 APK·AVD·SDK·cache·historical source는 삭제하지 않았다.

감사 helper의 manifest 형식·JSON 직렬화·모의 fixture 준비 오류는 보정한 뒤 검사를 완료했으며 [실행 메모](../../../benchmarks/real-device-gate-prep03/audit-execution-notes.json)에 남겼다. 제품 수정으로 해결한 것은 없다. 기본 shell sandbox의 기존 bwrap 초기화 실패 때문에 승인 검토된 host 실행을 사용했다. 자동 승인 거부는 없었다.

## 11. 향후 물리 기기 전제와 단일 다음 행동

실기기 이전에 F01~F03을 별도 권한의 구현 작업에서 보강하고 비참여 검토자가 재감사해야 한다. 현재 emulator 전용 실행기의 serial 제한을 완화하는 방식으로 실기기에 재사용해서는 안 된다.

그 이후에도 정확한 단말 신원·transport·APK/source/tool hash·테스트 인증서·합성 fixture·backend·허용 argv와 파일 경로·시간/용량/로그 한도·중단/부분 증거/회수 절차를 고정해야 한다. 전체 설치 앱 목록 조회나 범용 shell을 물리 기기에 그대로 가져가지 않고 test package 대상 조회만 검토해야 한다. Backend endpoint 변환도 별도 심사 대상이다. 고정 manifest에 대한 독립 preflight와 소유자의 명시적인 1회 실행 승인이 있어야 연결할 수 있다.

Android driver PRAGMA/VFS, native commit fence, I/O 오류·process death·disk-full·pointer/GC·previous recovery·전원 손실, legacy B/J/pending·migration/rollback·R1 recovery·최근 30 backup/artifact 의무는 이번 감사로 수용하지 않았다. T6.9 증거 작업은 DEFERRED, 이관 의무 수용은 0/8, formal T6.6F closure는 NOT AUTHORIZED, R1은 CLOSED, production deployment는 NOT AUTHORIZED다.

**다음 행동: 실기기 연결을 계속 금지한 상태에서 F01~F03 보강과 재검증을 위한 PREP04 구현 범위를 별도 승인 심사에 제출한다.**
