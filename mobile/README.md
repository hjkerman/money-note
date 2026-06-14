# Money Note 모바일 앱

Flutter 기반 모바일 클라이언트다.

현재 목표는 웹 앱의 모든 기능을 옮기는 것이 아니라, 모바일에서 자주 쓰는 흐름을 빠르게 제공하는 것이다.

우선 화면:

- 입력
- 결제
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
