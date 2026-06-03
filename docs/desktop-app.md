# macOS 앱 실행

이 문서는 Tauri 기반 macOS 앱을 실행하고 빌드하는 방법을 정리한다.

## 개념

macOS 앱은 별도 화면을 새로 만들지 않는다. `frontend/`의 Vite + React 웹 앱을 그대로 Tauri WebView로 감싼다.

따라서 화면 구조, API 호출, 로그인 방식, 테이블 조작 방식은 웹 앱과 같다.

## 필요한 것

- Docker Compose
- Node.js와 npm
- Rust/Cargo

Rust가 없다면 Homebrew로 설치한다.

```bash
brew install rust
```

확인:

```bash
cargo --version
rustc --version
```

## API 서버 실행

앱은 서버 API와 통신하므로, 먼저 백엔드를 실행한다.

```bash
docker compose up --build -d
```

상태 확인:

```bash
curl http://127.0.0.1:18080/health
```

기대값:

```json
{"status":"ok"}
```

## 개발 앱 실행

`tauri:dev`는 내부에서 Vite 개발 서버를 띄우고 macOS 앱 창을 연다.

```bash
cd frontend
npm install
npm run tauri:dev
```

실행되면 `Money Note` 앱 창이 열린다.

기본 개발 창 크기는 1440x920이다. 표를 자주 보는 앱이라 좌우 폭을 넉넉하게 잡아두었다.

## 포트 충돌

`npm run dev`와 `npm run tauri:dev`는 둘 다 5173 포트를 사용한다.

웹 브라우저만 확인할 때:

```bash
cd frontend
npm run dev
```

macOS 앱을 확인할 때:

```bash
cd frontend
npm run tauri:dev
```

둘을 동시에 실행하지 않는다. 이미 5173 포트가 사용 중이면 기존 개발 서버를 종료한 뒤 Tauri 앱을 실행한다.

포트 확인:

```bash
lsof -nP -iTCP:5173 -sTCP:LISTEN
```

## 인증

웹 브라우저에서는 `money_note_session` cookie가 기본 인증 수단이다.

Tauri 앱에서는 WebView cookie가 개발 origin에 따라 흔들릴 수 있으므로, 로그인 응답의 `session_token`을 저장하고 이후 요청에 `Authorization: Bearer ...` 헤더로 함께 보낸다.

이 덕분에 로그인 성공 직후 다시 로그인 화면으로 돌아가는 문제를 피한다.

## 앱 번들 생성

개발용 앱이 아니라 실제 `.app` 번들을 만들 때:

```bash
cd frontend
npm run tauri:build
```

생성 위치:

```text
frontend/src-tauri/target/release/bundle/
```

서명, notarization, 배포용 인증서는 별도 단계에서 처리한다.

## 문제 해결

로그인 후 바로 로그인 화면으로 돌아오면:

- API 서버가 켜져 있는지 확인한다.
- `http://127.0.0.1:18080/health`가 응답하는지 확인한다.
- 프론트엔드가 최신 코드로 실행 중인지 확인한다.

앱 창이 열리지 않으면:

- 5173 포트 충돌 여부를 확인한다.
- Rust/Cargo 설치 여부를 확인한다.
- `npm install`을 다시 실행한다.

Tauri 첫 빌드가 오래 걸리면:

- 정상이다. 첫 실행 때 Rust dependency를 내려받고 컴파일한다.
- 이후 실행은 훨씬 빨라진다.
