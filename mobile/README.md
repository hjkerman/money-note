# Money Note 모바일 앱

Flutter 기반 모바일 클라이언트다.

현재 목표는 웹 앱의 모든 기능을 옮기는 것이 아니라, 모바일에서 자주 쓰는 흐름을 빠르게 제공하는 것이다.

우선 화면:

- 입력
- 현금
- 내역
- 정산
- 상태

입력 탭에는 서버 Judgment 응답을 재사용한 `오늘의 예산심사위원회` 카드가 표시된다. 전체 Judgment는 상태 탭에서 확인한다.

상태 탭의 `관리` 화면에는 동결 금액, 현금성 고정지출, 카드 정기결제, 월마감, 백업/복원, 설정을 모아 둔다.
모바일 앱은 서버 DB를 원본으로 사용하므로 앱 시작 시 서버에 연결할 수 없으면 종료 안내를 표시한다.

## 데이터 새로고침 정책

등록, 삭제, 확인 처리 같은 버튼 조작 뒤에는 전체 앱 데이터를 다시 받지 않고 관련 영역만 다시 받는다.

- 입력/내역/카드 정기결제: 원장, 요약, Judgment, 월마감 상태, 할인 정책
- 현금: 현금흐름, 요약, Judgment
- 정산/동결/현금성 고정지출: 월별 패널, 요약, Judgment, 할인 정책
- 설정: 설정, 요약, Judgment, 할인 정책

하단 탭의 `입력`, `현금`, `내역`, `정산`은 아래로 당겨서 새로고침할 수 있다.
`상태` 탭은 조회 중심 화면이므로 당겨서 새로고침을 두지 않는다.
대신 `상태 -> 관리` 안의 동결 금액, 현금성 고정지출, 카드 정기결제 화면은 각각 아래로 당겨서 해당 영역을 다시 조회한다.

현재 API는 영역별 단일 집계 엔드포인트를 따로 두지 않는다.
따라서 모바일은 기존 API를 조합해 관련 데이터만 다시 받는다.
일반적인 버튼 조작 1회는 작은 JSON 요청 3~6개 정도이며, 1인용 장부의 월간 데이터 규모에서는 모바일 데이터 사용량이 매우 작다.
앱 실행 시 자동 저장되는 snapshot은 상대적으로 크지만, 기존 엑셀 기준 수년치 데이터도 수백 KB 이하였으므로 실행 빈도 기준으로도 부담이 낮다.

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

## 알림 원문 보관함

Android 앱은 NotificationListenerService로 알림 원문을 관측한다.

현재 정책:

- 모든 앱 알림을 저장한다.
- packageName allowlist로 거르지 않는다.
- 자동 후보 생성, 자동 지출 등록, 자동 가족카드 등록을 하지 않는다.
- 서버로 아무 데이터도 보내지 않는다.
- 최근 100건만 앱 로컬에 저장한다.
- `알림에서 가져오기` 화면은 Raw Notification Archive로 동작한다.
- 화면에서 packageName, title, text, bigText, textLines, rawText 등을 확인한다.
- `txt 로그 공유`로 `MN_NOTIFY` 관측 내용을 파일 형태로 공유할 수 있다.
- 알림 파서 재개발 전까지 이 화면은 실제 Android Notification에 어떤 값이 들어오는지 확인하는 공사장이다.
