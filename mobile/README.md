# Money Note 모바일 앱

Flutter 기반 모바일 클라이언트다.

현재 목표는 웹 앱의 모든 기능을 옮기는 것이 아니라, 모바일에서 자주 쓰는 흐름을 빠르게 제공하는 것이다.

우선 화면:

- 입력
- 현금
- 내역
- 가족
- 상태

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
flutter run --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18080
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

## 카드 알림 후보 등록

Android 앱은 NotificationListenerService로 우리카드 알림만 읽는다.

현재 정책:

- 우리카드 앱 allowlist에 포함된 패키지의 알림만 처리한다.
- 알림 원문은 저장하지 않고, 카드 뒷자리, 사용일, 시간, 금액, 사용처만 로컬 후보로 저장한다.
- 후보는 `알림에서 가져오기` 화면에서 확인/수정한 뒤 사용자가 `등록`을 눌러야 서버에 전송된다.
- 본인카드 뒷자리와 일치하면 당월 지출, 가족카드 뒷자리와 일치하면 가족카드 항목으로 등록한다.
- 일치하지 않으면 사용자가 등록 대상을 직접 고른다.
- 알림 포맷이 바뀌면 Android 네이티브 파서와 allowlist를 먼저 확인한다.
