# Money Note 모바일 앱

Flutter 기반 모바일 클라이언트다.

현재 목표는 웹 앱의 모든 기능을 옮기는 것이 아니라, 모바일에서 자주 쓰는 흐름을 빠르게 제공하는 것이다.

하단 탭:

- 홈
- 정산
- 입력
- 현금
- 설정

홈 탭에는 서버 Judgment 응답을 재사용한 예산심사위원회, 카드 한도 감시, 파산심사위원회 카드와 최근 입력 10건을 표시한다. 카드 지출 입력 폼과 당월 전체 원장은 입력 탭에 둔다.

설정 탭에는 동결 금액, 현금성 고정지출, 카드 정기결제, 월마감, 백업/복원, 운영 설정을 모아 둔다.
모바일 앱의 금융 원본은 서버 DB다. 시작할 때 기존 OFFLINE lineage가 있으면 먼저 복원한다. 정상 ONLINE 시작 중 서버에 연결할 수 없으면 검증된 마지막 온라인 baseline이 있는 경우에만 오프라인 모드 사용 또는 종료를 선택하게 한다. 유효한 baseline이 없으면 오프라인 입력을 시작하지 않으며, 로컬 lineage가 손상된 경우에는 복구 차단 상태를 표시한다.

## 데이터 새로고침 정책

ONLINE에서 등록, 삭제, 확인 처리 뒤에는 관련 화면의 새로고침 경로를 호출한다. 이 경로들은 현재 공통 authoritative refresh를 사용하여 화면 데이터와 서버 Snapshot을 하나의 coherent baseline generation으로 설치한다. 중간 요청이 실패하거나 서버 revision·기준일이 달라지면 기존 valid baseline을 유지한다.

홈·입력·현금·정산·설정의 변경 후 갱신은 모두 같은 authoritative refresh 경계로 이어진다. 화면별 이름이 조회 범위의 분리를 뜻하지 않는다.

ONLINE에서 앱이 백그라운드에서 포그라운드로 돌아오면 서버 데이터를 다시 조회한다. OFFLINE에서는 서버 데이터나 Snapshot을 자동 적용하지 않고 연결 회복만 확인한다.
하단 탭의 `홈`, `정산`, `입력`, `현금`은 아래로 당겨서 새로고침할 수 있다.
`설정` 탭은 당겨서 새로고침을 두지 않는다.
대신 설정 안의 동결 금액, 현금성 고정지출, 카드 정기결제 화면은 각각 아래로 당겨서 같은 authoritative refresh를 요청할 수 있다.

현재 API는 영역별 단일 집계 엔드포인트를 따로 두지 않는다. 모바일은 기존 조회 API를 조합하고, 전후 authoritative Snapshot fingerprint·server revision·기준일이 일치할 때만 화면 상태와 offline-ready baseline을 교체한다. 먼저 시작된 refresh가 나중에 끝나도 새 generation을 덮지 못한다.

앱 실행과 포그라운드 복귀의 ONLINE 동기화가 성공하면 별도의 로컬 Snapshot 자동 저장을 시도한다. 이 파일은 offline baseline·journal과 다른 사용자 백업이며 최근 30개만 유지한다. 자동 백업 실패가 성공한 화면 동기화를 취소하지는 않는다.

## Offline Mode

설정에서 의도적으로 진입하거나 서버 연결 실패 안내에서 선택할 수 있다. 진입에는 완성된 authoritative baseline이 필요하며, 해당 offline epoch 동안 baseline은 고정된다. 카드 사용(사용자 할인 의도·실결제액 입력 포함), 현금 입출금, 현금성 고정지출 확인, 카드 정기결제 확인만 durable ordered journal에 저장한다. 월마감·설정 변경·기존 항목 삭제/수정·Snapshot 복원은 오프라인에서 할 수 없다.

화면의 `오프라인 예상값`은 표시용 projection이며 서버의 계산 결과나 reconciliation 입력이 아니다. 연결이 돌아와도 자동으로 ONLINE 상태를 덮지 않고 `RECONCILIATION_REQUIRED`에서 사용자가 Mobile Wins 또는 Server Wins를 선택·확인한다. 서버 반영 결과가 모호하거나 fresh sync가 끝나지 않았다면 finalizing 상태에서 복구를 이어가며, 저장된 lineage를 신뢰할 수 없으면 금융 작업을 차단한다. 상세 상태·저장·복구 계약은 [Offline Mode 문서](../docs/offline-mode.md)를 따른다.

## 준비

이 디렉터리는 Flutter 소스와 설정을 담는다.

Flutter SDK가 설치된 환경에서 처음 한 번 플랫폼 파일을 생성한다.

```bash
cd mobile
flutter create --platforms=android .
flutter pub get
```

`lib/`와 `pubspec.yaml`은 이미 repo에 있으므로, 플랫폼 파일 생성 후 변경사항을 확인한다.

## 실행

로컬 API 서버에 붙여 실행한다.

```bash
flutter run --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
```

Android 에뮬레이터에서 호스트의 `localhost`는 `10.0.2.2`로 접근한다.

실서버에 붙일 때는 아래처럼 지정한다.

```bash
flutter run --dart-define=MONEY_NOTE_API_BASE_URL=https://money.hjkerman.re.kr
```

## APK 빌드

```bash
flutter build apk --release --dart-define=MONEY_NOTE_API_BASE_URL=https://money.hjkerman.re.kr
```

생성 파일:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

서버 설정 모달에서 APK 다운로드를 제공하려면 빌드된 APK를 서버의 `MONEY_NOTE_APK_PATH` 위치에 둔다.

서버의 개발 checkout에서 `./scripts/release-mobile.sh`는 기본 dry-run이다. `--stage-only`는 검사와 서명 빌드만, `--apply`는 검사·빌드·SHA-256 검증 후 local APK 원자적 교체까지 수행한다. Flutter/JDK/Android SDK와 기존 서명키가 필요하며 production에서 개발하지 않는다. 자세한 prerequisite와 보관 한도는 `docs/runbook.md`의 `한 명령으로 모바일 release 배포` 절을 따른다.

모바일 앱 자체에서는 `설정` 탭 맨 아래의 `APK 다운로드`로 서버에 현재 배치된 파일을 직접 받을 수 있다. 버전 확인은 하지 않으며, 기존 모바일 Bearer 인증으로 `/api/admin/apk`를 스트리밍 다운로드한 뒤 package name과 설치된 앱의 서명이 같은 경우에만 Android 설치 화면을 연다.

## 카드·통행료 알림 수집

Android 앱은 하나의 NotificationListenerService로 우리카드와 고속도로 통행료+ 알림을 관측한다.

현재 정책:

- 우리카드 packageName은 `com.wooricard.smartapp`이다.
- 고속도로 통행료+ packageName은 `com.ex.hipass_app`이다.
- 그 밖의 앱 알림은 후보로도 로그로도 저장하지 않는다.
- 일시불 승인 알림을 파싱해 본인카드/가족카드 후보함에 로컬 저장한다.
- 알림 수신 즉시 서버로 등록하지 않는다. 사용자가 후보를 확인하고 `등록`을 눌렀을 때만 기존 API를 호출한다.
- 할부 승인, 파싱 실패, 광고/혜택 안내 등은 후보로 만들지 않고 `최근 납치한 알림`의 우리카드 로그에 남긴다.
- 고속도로 통행료+ 알림은 날짜·시각, 구간, 금액을 파싱해 로컬 통행료 후보로 만든다.
- 날짜만 확인되거나 요금을 확인할 수 없는 알림도 빈 금액의 후보로 남긴다.
- 통행료 후보의 사용처는 `통행료`이고 할인은 적용하지 않는다.
- 각 출처 로그는 앱 로컬에 30건만 유지한다.
- 리스너 재연결 시 Android 알림창에 남은 지원 알림을 다시 읽는다.
- `notificationKey + postTime` 기반 처리 이력은 마지막 관측 후 7일, 최대 512건 유지하며 등록·삭제한 후보의 부활을 막는다.
- 후보·원문·처리 이력 JSON은 원자적으로 저장한다.
- 원문과 파싱 결과는 `설정 -> 최근 납치한 알림`의 `우리카드`/`통행료` 탭에서 확인한다.
- 기존 원문 로그를 후보로 소급 변환하지 않으며, 앱 갱신 뒤 새로 수신한 통행료 알림부터 후보가 된다.
