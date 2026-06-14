# 실행 방법

이 문서는 `money-note`를 로컬 개발 환경과 홈서버 배포 환경에서 실행하는 방법을 모아둔다.

## 전제

필요한 런타임:

- Docker 또는 Colima/Docker Compose
- Node.js와 npm
- Git
- Apache HTTP Server

현재 개발 환경에서 확인한 버전:

```bash
node --version
npm --version
docker compose version
```

## 데이터 디렉터리

repo 루트에서 아래 디렉터리를 사용한다.

```text
data/
```

- `data/`: SQLite DB 저장

이 디렉터리들은 개인 데이터가 들어가므로 git에 올리지 않는다.

## 백엔드 서버 실행

Docker Compose로 백엔드를 빌드하고 실행한다.

```bash
docker compose up --build -d
```

접속 주소:

```text
http://localhost:18080
```

상태 확인:

```bash
curl http://localhost:18080/health
```

기대 응답:

```json
{"status":"ok"}
```

로그 확인:

```bash
docker compose logs --tail=80 api
```

컨테이너 상태 확인:

```bash
docker compose ps
```

중지:

```bash
docker compose down
```

## 홈서버 첫 배포 절차

Ubuntu 24.04 홈서버에 처음 올릴 때의 기준 절차다. `docker run`에 익숙한 사람이라면, 이 프로젝트에서는 `docker compose`가 긴 `docker run ...` 명령을 파일로 저장해 두고 반복 실행하는 역할이라고 보면 된다.

요즘 소규모 개인 서버 배포에서는 서버에서 `git clone` 또는 `git pull`로 코드를 받는 방식도 여전히 흔하다. 다만 중요한 원칙은 코드와 운영 설정/데이터를 분리하는 것이다.

- 코드: Git repo에서 받는다.
- 설정: 서버의 `.env`에 둔다.
- 데이터: 서버의 `data/`에 둔다.
- 웹 빌드 산출물: `frontend/dist/`를 `/var/www/...`로 복사하고 Apache로 서비스한다.

즉, 서버에 repo를 두되 `.env`, SQLite DB, snapshot 백업 같은 운영 파일은 git에 올리지 않는다. 이 프로젝트는 1인 홈서버 서비스라서, 별도 CI/CD 없이 `git pull -> docker compose up --build -d -> frontend build -> /var/www 배치` 흐름을 기본 배포 방식으로 삼는다.

## 운영 안정화 원칙

현재 웹 프론트엔드와 백엔드는 실사용 후보 기준선이다. 오류가 발견되는 경우가 아니라면 기능 변경을 중단한다.

허용하는 변경:

- 데이터 손상 가능성 수정
- 계산 오류 수정
- 로그인, 공유 PIN, snapshot, restore 같은 안전 기능의 버그 수정
- 배포 문서와 운영 절차 보강
- 서버 설정, 도메인, HTTPS, 백업 위치처럼 배포에 필요한 조정

보류하는 변경:

- 새 기능 추가
- 화면 취향 변경
- API 의미 변경
- DB 의미 변경
- 대규모 리팩토링
- 기존 웹/API 동작을 흔드는 클라이언트 선행 작업

새 모바일 앱이나 맥 앱을 만들 때도 이 기준선을 흔들지 않는다. 필요한 기능이 생기면 먼저 기존 API로 가능한지 확인하고, API 변경이 필요하면 별도 작업으로 분리한다.

### 1. 서버에 필요한 도구 설치

서버에서 한 번만 수행한다.

```bash
sudo apt update
sudo apt install -y git curl ca-certificates apache2
```

Docker Engine과 Compose plugin은 Docker 공식 문서 방식으로 설치한다. 이미 `docker compose version`이 정상 출력되면 다시 설치하지 않아도 된다.

```bash
docker --version
docker compose version
```

일반 사용자로 Docker를 실행하고 싶으면 현재 사용자를 `docker` 그룹에 넣고 다시 로그인한다.

```bash
sudo usermod -aG docker "$USER"
```

### 2. 서버에 코드 받기

예시는 `/opt/money-note`에 배포하는 방식이다. 다른 경로를 써도 되지만, 이후 명령의 경로를 같이 바꾼다.

```bash
sudo mkdir -p /opt/money-note
sudo chown "$USER":"$USER" /opt/money-note
git clone git@github.com:hjkerman/money-note.git /opt/money-note
cd /opt/money-note
```

이미 받아둔 repo를 갱신할 때는 새로 clone하지 않고 아래만 실행한다.

```bash
cd /opt/money-note
git pull
```

### 3. 서버 설정 파일 만들기

repo 루트에 서버용 `.env` 파일을 만든다. 이 파일은 `docker compose`가 자동으로 읽으며, git에 올리지 않는다.

주의:

- 이 `.env`는 `/opt/money-note/.env`다.
- 프론트엔드 개발용 `frontend/.env`와 다른 파일이다.
- 서버 비밀값, 운영 도메인, cookie 설정은 repo 루트 `.env`에 둔다.
- `.gitignore`에 `.env`가 들어 있으므로 실수로 git에 올라가지 않는다.

복사해서 바로 만들려면 아래처럼 한다.

```bash
cd /opt/money-note
cat > .env <<'EOF'
MONEY_NOTE_TODAY=
MONEY_NOTE_CORS_ORIGINS=https://money.hjkerman.re.kr
MONEY_NOTE_COOKIE_SECURE=true
MONEY_NOTE_SESSION_DAYS=30
MONEY_NOTE_MOBILE_SESSION_DAYS=3650
MONEY_NOTE_APK_PATH=/app/downloads/money-note.apk
MONEY_NOTE_APK_FILENAME=money-note.apk
EOF
chmod 600 .env
```

로컬 개발 주소도 함께 허용해야 하면 `MONEY_NOTE_CORS_ORIGINS`를 쉼표로 이어 쓴다.

```text
MONEY_NOTE_CORS_ORIGINS=https://money.hjkerman.re.kr,http://localhost:5173,http://127.0.0.1:5173
```

설명:

- `MONEY_NOTE_TODAY`는 운영에서는 비워둔다.
- `MONEY_NOTE_CORS_ORIGINS`에는 실제 웹 프론트엔드 주소를 넣는다.
- HTTPS 뒤에서 운영하면 `MONEY_NOTE_COOKIE_SECURE=true`를 권장한다.
- 처음 로컬 확인만 할 때는 `MONEY_NOTE_COOKIE_SECURE=false`가 편하다.
- `MONEY_NOTE_SESSION_DAYS`는 웹 cookie 로그인 세션 유지 기간이다.
- `MONEY_NOTE_MOBILE_SESSION_DAYS`는 모바일 앱 Bearer 토큰 유지 기간이다. 기본값은 `3650`일이며, 웹 cookie 로그인 기간과 별도로 관리된다.
- `MONEY_NOTE_APK_PATH`는 설정 모달에서 내려받을 Android APK 파일의 컨테이너 내부 경로다. APK를 아직 제공하지 않을 때는 비워둬도 된다.

`docker-compose.yml`은 위 값을 자동으로 읽어 컨테이너에 전달한다.

적용될 값을 확인하려면 아래 명령을 쓴다.

```bash
docker compose config
```

`.env`를 수정한 뒤 이미 서버가 떠 있다면 다시 올린다.

```bash
docker compose up --build -d
```

### 4. 데이터 디렉터리 확인

SQLite DB는 repo 루트의 `data/`에 저장된다.

```bash
mkdir -p /opt/money-note/data
```

기존 DB를 옮겨서 시작하려면 서버의 아래 위치에 둔다.

```text
/opt/money-note/data/money-note.sqlite3
```

DB 파일을 직접 복사한 뒤에는 다음 서버 시작 때 누락 컬럼 보강, 오래된 설정 정리 같은 마이그레이션이 자동으로 실행된다.

### 5. 서버 컨테이너 실행

```bash
cd /opt/money-note
docker compose up --build -d
```

정상 여부 확인:

```bash
docker compose ps
curl http://localhost:18080/health
```

정상 응답:

```json
{"status":"ok"}
```

로그 확인:

```bash
docker compose logs --tail=80 api
```

### 6. 관리자 계정 만들기

처음 배포한 DB에는 계정이 없을 수 있다. 아래 명령으로 계정을 만들거나 비밀번호를 재설정한다.

```bash
docker compose exec -T api env PYTHONPATH=/app \
  python scripts/create_user.py your-username your-password \
  --display-name "사용자" \
  --replace
```

`your-username`과 `your-password`는 실제 값으로 바꾼다. 비밀번호는 평문 저장되지 않고 해시만 저장된다.

### 7. 웹 프론트엔드 빌드

서버에 Node.js가 없다면 설치한다. Ubuntu에서는 NodeSource나 `nvm` 중 편한 방식을 쓰면 된다. 이미 `node --version`과 `npm --version`이 나오면 넘어간다.

운영 배포에서는 프론트엔드가 API 서버 절대주소를 들고 있지 않게 만든다. `VITE_API_BASE_URL`을 빈 값으로 빌드하면 브라우저가 현재 도메인 기준의 상대경로 `/api/...`, `/share/...`로 요청한다. 그러면 Apache가 내부 백엔드 `127.0.0.1:18080`으로 넘긴다.

```bash
cd /opt/money-note/frontend
npm install
cat > .env.production <<'EOF'
VITE_API_BASE_URL=
EOF
npm run build
```

빌드 결과는 아래에 생긴다.

```text
/opt/money-note/frontend/dist/
```

### 8. 웹 파일 배치

예시는 `/var/www/money-note`에 배치하는 방식이다.

```bash
sudo mkdir -p /var/www/money-note
sudo rsync -a --delete /opt/money-note/frontend/dist/ /var/www/money-note/
```

이 단계까지 끝나면 백엔드는 `localhost:18080`, 프론트엔드 정적 파일은 `/var/www/money-note`에 있는 상태다.

Android 앱과 Google 비밀번호 관리자를 웹 도메인에 연결하려면 프론트엔드 빌드 결과에 아래 파일이 반드시 포함되어야 한다.

```text
/var/www/money-note/.well-known/assetlinks.json
```

배치 후 서버에서 확인한다.

```bash
test -f /var/www/money-note/.well-known/assetlinks.json
curl -s https://money.hjkerman.re.kr/.well-known/assetlinks.json
```

브라우저나 `curl`에서 JSON 배열이 그대로 보이면 된다. `404`, HTML, `index.html` 내용이 보이면 Apache rewrite나 파일 배치가 잘못된 것이다.

### 9. Apache reverse proxy 연결

Apache 모듈을 켠다.

```bash
sudo a2enmod proxy proxy_http rewrite headers ssl
sudo systemctl reload apache2
```

사이트 설정 파일을 만든다. 도메인과 인증서 경로는 서버 상황에 맞게 바꾼다.

```bash
sudo nano /etc/apache2/sites-available/money-note.conf
```

HTTP만 먼저 확인할 때의 최소 예시:

```apache
<VirtualHost *:80>
    ServerName money.hjkerman.re.kr

    DocumentRoot /var/www/money-note

    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:18080/api/
    ProxyPassReverse /api/ http://127.0.0.1:18080/api/
    ProxyPass /share/ http://127.0.0.1:18080/share/
    ProxyPassReverse /share/ http://127.0.0.1:18080/share/
    ProxyPass /health http://127.0.0.1:18080/health
    ProxyPassReverse /health http://127.0.0.1:18080/health

    <Directory /var/www/money-note>
        Require all granted
        Options -Indexes
        RewriteEngine On
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule ^ /index.html [L]
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/money-note-error.log
    CustomLog ${APACHE_LOG_DIR}/money-note-access.log combined
</VirtualHost>
```

HTTPS 적용 후의 예시:

```apache
<VirtualHost *:443>
    ServerName money.hjkerman.re.kr

    DocumentRoot /var/www/money-note

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/money.hjkerman.re.kr/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/money.hjkerman.re.kr/privkey.pem

    RequestHeader set X-Forwarded-Proto "https"
    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:18080/api/
    ProxyPassReverse /api/ http://127.0.0.1:18080/api/
    ProxyPass /share/ http://127.0.0.1:18080/share/
    ProxyPassReverse /share/ http://127.0.0.1:18080/share/
    ProxyPass /health http://127.0.0.1:18080/health
    ProxyPassReverse /health http://127.0.0.1:18080/health

    <Directory /var/www/money-note>
        Require all granted
        Options -Indexes
        RewriteEngine On
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule ^ /index.html [L]
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/money-note-error.log
    CustomLog ${APACHE_LOG_DIR}/money-note-access.log combined
</VirtualHost>
```

사이트를 활성화하고 설정 문법을 확인한다.

```bash
sudo a2ensite money-note.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

인증서는 `certbot` 등으로 별도 적용한다. HTTPS 적용 뒤에는 repo 루트 `.env`에서 `MONEY_NOTE_COOKIE_SECURE=true`를 사용하고, 서버 컨테이너를 다시 올린다.

```bash
cd /opt/money-note
docker compose up --build -d
```

운영에서 브라우저 개발자 도구를 열었을 때 API 요청 주소가 `https://money.hjkerman.re.kr/api/...` 형태여야 한다. `http://127.0.0.1:18080/api/...`가 보이면 `frontend/.env.production`을 만든 뒤 프론트엔드를 다시 빌드하고 `/var/www/money-note`에 다시 배치한다.

### 10. 배포 후 손검증

브라우저에서 실제 도메인에 접속한 뒤 아래를 확인한다.

1. 로그인 가능
2. 새 당월 지출 1건 추가 후 즉시 표시
3. 설정에서 snapshot 백업 다운로드 가능
4. 청구 공유 링크와 가족카드 공유 링크가 PIN 화면을 거쳐 열림
5. `docker compose logs --tail=80 api`에 반복 오류가 없음

### 11. 업데이트 절차

코드를 새 버전으로 올릴 때는 아래 순서로 한다.

```bash
cd /opt/money-note
git pull
docker compose up --build -d
cd frontend
npm install
cat > .env.production <<'EOF'
VITE_API_BASE_URL=
EOF
npm run build
sudo rsync -a --delete dist/ /var/www/money-note/
```

업데이트 후 확인:

```bash
curl http://localhost:18080/health
docker compose logs --tail=80 api
```

문제가 생기면 우선 `docker compose logs --tail=200 api`와 Apache 로그를 본다. 프론트엔드 화면만 이상하면 `npm run build`, `frontend/.env.production`, `/var/www/money-note` 배치 여부를 먼저 확인한다.

```bash
sudo tail -n 120 /var/log/apache2/money-note-error.log
sudo tail -n 120 /var/log/apache2/money-note-access.log
```

## 백엔드 환경변수

`docker-compose.yml` 기준 기본값:

```text
MONEY_NOTE_DB_PATH=/app/data/money-note.sqlite3
```

개발용 CORS:

```text
MONEY_NOTE_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

운영에서 웹 프론트엔드 도메인이 달라지면 `MONEY_NOTE_CORS_ORIGINS`에 해당 origin을 추가한다.

인증 관련 설정:

```text
MONEY_NOTE_SESSION_COOKIE_NAME=money_note_session
MONEY_NOTE_SESSION_DAYS=30
MONEY_NOTE_MOBILE_SESSION_DAYS=3650
MONEY_NOTE_COOKIE_SECURE=false
```

운영에서 HTTPS 뒤에 둘 때는 `MONEY_NOTE_COOKIE_SECURE=true` 사용을 고려한다.

웹 로그인 cookie는 `MONEY_NOTE_SESSION_DAYS`를 따른다. 모바일 앱은 `/api/auth/mobile-login`에서 받은 Bearer 토큰을 저장하며 `MONEY_NOTE_MOBILE_SESSION_DAYS`를 따른다. 공유 페이지 PIN 세션은 별도 장기 세션을 사용한다.

날짜 민감 기능 검증:

```bash
MONEY_NOTE_TODAY=2026-07-01 docker compose up --build -d
```

`MONEY_NOTE_TODAY`는 월마감, 카드대금, 정기결제 표시처럼 앱 기준일이 필요한 흐름을 검증하기 위한 개발용 override다. 비워두면 실제 오늘 날짜를 사용한다. 운영 서버에서는 설정하지 않는다.

앱 기준일은 기본적으로 KST(+09:00)로 계산한다. 다른 시간대가 필요하면 `MONEY_NOTE_TIMEZONE_OFFSET_MINUTES`에 UTC 기준 분 단위 offset을 지정한다. 한국 시간은 기본값 `540`이다.

Android APK 다운로드:

```text
MONEY_NOTE_APK_PATH=/app/downloads/money-note.apk
MONEY_NOTE_APK_FILENAME=money-note.apk
```

`MONEY_NOTE_APK_PATH`는 컨테이너 안에서 보이는 APK 파일 경로다. `docker-compose.yml`은 기본으로 서버 repo의 `./downloads` 디렉터리를 컨테이너의 `/app/downloads`에 연결한다.

따라서 서버에서는 아래처럼 APK를 둔다.

```bash
mkdir -p /opt/money-note/downloads
cp money-note.apk /opt/money-note/downloads/money-note.apk
```

그 뒤 `/opt/money-note/.env`에 위 값을 넣고 서버를 다시 올린다.

```bash
docker compose up --build -d
```

웹에서는 `설정 -> Android 앱 설치 파일 -> APK 다운로드` 버튼으로 내려받는다. APK 파일이 아직 없거나 `MONEY_NOTE_APK_PATH`가 비어 있으면 다운로드는 `apk file not found`로 실패한다.

## 모바일 앱 개발과 APK 빌드

모바일 앱은 `mobile/` 디렉터리의 Flutter 프로젝트다. 웹 앱을 그대로 줄인 것이 아니라, 빠른 입력, 현금흐름 관리, 당월 내역 확인, 청구/가족카드 정산, 상태 확인에 집중한다. 카드대금 실제 결제는 카드사 앱에서 처리하고, Money-Note 모바일 앱에서는 현금 유동성 보정에 집중한다.

주 검증 기기는 Galaxy S23 FE / One UI 8.5다. 에뮬레이터에서는 최신 Android API로 빌드와 권한 흐름을 먼저 확인하고, 실기기에서는 알림 접근 권한, 우리카드 알림 수신, 큰 글꼴 표시를 반드시 확인한다.

### 1. 개발 도구 확인

필요한 도구:

- Flutter SDK
- Android Studio
- Android SDK
- Android SDK Command-line Tools
- Android SDK Platform-Tools

설치 상태는 아래로 확인한다.

```bash
cd mobile
flutter doctor -v
```

`Android toolchain` 항목에서 `cmdline-tools component is missing`이 나오면 Android Studio에서 아래를 설치한다.

1. Android Studio 실행
2. `Settings` 또는 `Preferences` 열기
3. `Languages & Frameworks -> Android SDK` 이동
4. `SDK Tools` 탭 선택
5. `Android SDK Command-line Tools` 체크
6. 적용

라이선스가 필요하다고 나오면 아래를 실행한다.

```bash
flutter doctor --android-licenses
```

모든 항목에 동의한 뒤 다시 확인한다.

```bash
flutter doctor -v
```

### 2. 의존성 설치

```bash
cd mobile
flutter pub get
```

### 3. 로컬 서버에 붙여 실행

Android 에뮬레이터에서 개발 머신의 `localhost`는 `10.0.2.2`로 접근한다.

```bash
cd mobile
flutter run --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18080
```

실제 서버에 붙일 때는 운영 도메인을 넣는다.

```bash
flutter run --dart-define=MONEY_NOTE_API_BASE_URL=https://money.hjkerman.re.kr
```

모바일 앱은 서버 DB를 원본으로 사용한다. 앱 시작 시 `/health`에 닿지 않으면 로그인 화면으로 넘어가지 않고 종료 안내를 표시한다.

모바일 앱은 로그인 응답의 `session_token`을 저장하고, 이후 API 요청에 `Authorization: Bearer ...` 헤더를 보낸다.

모바일 로그인은 `/api/auth/mobile-login`을 사용한다. 이 경로는 웹 cookie를 만들지 않고, `MONEY_NOTE_MOBILE_SESSION_DAYS` 기준의 장기 Bearer 토큰만 발급한다.

앱 실행 후 로그인 세션이 살아 있으면 서버에서 snapshot을 자동으로 받아 앱 내부에 누적 저장한다. 이 자동 백업은 사용자가 매번 파일을 직접 내려받지 않아도 되는 안전장치다. 상태 탭의 `관리 -> 백업 / 복원`에서 저장된 스냅샷 목록을 확인하고, 특정 파일을 공유하거나 복원하거나 삭제하거나 전체 삭제할 수 있다.

### 4. 검사와 테스트

```bash
cd mobile
flutter analyze
flutter test
```

### 5. APK 빌드

운영 서버용 APK를 만든다.

릴리즈 서명키를 사용할 때는 `mobile/android/key.properties`를 만든다. 이 파일은 git에 올리지 않는다.

```properties
storeFile=/Users/hjkerman/keys/money-note-release.jks
storePassword=키스토어_비밀번호
keyAlias=money-note
keyPassword=키_비밀번호
```

환경변수로도 같은 값을 줄 수 있다.

```bash
export MONEY_NOTE_KEYSTORE_PATH=/Users/hjkerman/keys/money-note-release.jks
export MONEY_NOTE_KEYSTORE_PASSWORD=키스토어_비밀번호
export MONEY_NOTE_KEY_ALIAS=money-note
export MONEY_NOTE_KEY_PASSWORD=키_비밀번호
```

`key.properties` 또는 환경변수가 모두 채워져 있으면 debug APK와 release APK 모두 같은 release 키로 서명된다. 값이 비어 있으면 개발 편의를 위해 기본 debug 서명으로 빌드된다.

Money-Note는 웹 도메인 `money.hjkerman.re.kr`과 Android 앱의 비밀번호 관리자를 연결하기 위해 아래 파일을 프론트엔드 정적 파일에 포함한다.

```text
frontend/public/.well-known/assetlinks.json
```

이 파일에는 Android 패키지명 `kr.re.hjkerman.money_note`와 release signing certificate의 SHA-256 fingerprint가 들어간다. 서명키를 바꾸면 이 fingerprint도 다시 뽑아서 갱신해야 한다.

현재 키 지문 확인 명령:

```bash
keytool -list -v \
  -keystore /Users/hjkerman/keys/money-note-release.jks \
  -alias money-note
```

운영 서버에 프론트엔드 빌드 결과물을 배포한 뒤 아래 URL이 JSON 파일로 열려야 한다.

```text
https://money.hjkerman.re.kr/.well-known/assetlinks.json
```

이 연결은 Google 비밀번호 관리자가 웹에 저장한 `money.hjkerman.re.kr` 로그인 정보를 Android 앱 로그인 화면에서도 같은 서비스의 계정으로 판단할 수 있게 돕는다.

```bash
cd mobile
flutter build apk --release --dart-define=MONEY_NOTE_API_BASE_URL=https://money.hjkerman.re.kr
```

산출물:

```text
mobile/build/app/outputs/flutter-apk/app-release.apk
```

### 6. 서버에서 APK 다운로드 제공

빌드한 APK를 서버 repo의 `downloads/`에 둔다.

```bash
mkdir -p /opt/money-note/downloads
cp mobile/build/app/outputs/flutter-apk/app-release.apk /opt/money-note/downloads/money-note.apk
```

서버 `.env`에는 아래를 둔다.

```text
MONEY_NOTE_APK_PATH=/app/downloads/money-note.apk
MONEY_NOTE_APK_FILENAME=money-note.apk
```

서버를 다시 올린다.

```bash
cd /opt/money-note
docker compose up --build -d
```

웹 설정 모달의 `Android 앱 설치 파일` 영역에서 APK를 내려받을 수 있다.

### 7. 변경 후 에뮬레이터에 다시 띄우기

모바일 앱 코드를 수정한 뒤 에뮬레이터에서 바로 확인할 때는 아래 순서를 쓴다.

먼저 에뮬레이터가 떠 있는지 확인한다.

```bash
cd mobile
flutter devices
```

정적 검사와 테스트를 실행한다.

```bash
flutter analyze
flutter test
```

운영 서버에 붙여 에뮬레이터에서 실행한다.

```bash
flutter run -d emulator-5554 --dart-define=MONEY_NOTE_API_BASE_URL=https://money.hjkerman.re.kr
```

로컬 Docker 서버에 붙일 때는 Android 에뮬레이터에서 호스트 머신을 `10.0.2.2`로 본다.

```bash
flutter run -d emulator-5554 --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18080
```

이미 `flutter run`이 붙어 있는 상태에서 소스만 바꿨다면 터미널에서 `r`을 눌러 빠르게 반영한다. 앱을 완전히 다시 시작해야 하면 `R`을 누른다. 실행 연결은 끊고 앱은 에뮬레이터에 남기려면 `d`를 누른다.

릴리즈 APK까지 확인하려면 아래를 실행한다.

```bash
flutter build apk --release --dart-define=MONEY_NOTE_API_BASE_URL=https://money.hjkerman.re.kr
```

### 8. 카드 알림 후보 등록 확인

모바일 앱의 `알림에서 가져오기`는 카드사 알림을 곧바로 서버에 올리지 않는다. Android의 NotificationListenerService가 알림을 받으면 파싱된 후보만 앱 로컬 저장소에 보관하고, 사용자가 후보를 확인한 뒤 `등록`을 눌렀을 때만 서버 API를 호출한다.

처리 원칙:

- 우리카드 앱 allowlist에 포함된 패키지 알림만 처리한다.
- 여기서 allowlist는 화면에 보이는 앱 이름이 아니라 Android 내부 패키지명 기준이다. 구현은 `StatusBarNotification.packageName`을 확인한다.
- 다른 앱 알림은 읽히더라도 저장하지 않고 즉시 무시한다.
- 알림 원문은 장기 저장하지 않는다.
- 저장하는 값은 카드 뒷자리, 사용일, 시간, 금액, 사용처 같은 파싱 결과뿐이다.
- 본인카드 뒷자리는 당월 지출 등록으로, 가족카드 뒷자리는 가족카드 등록으로 연결한다.
- 식별되지 않은 카드는 후보 화면에서 사용자가 직접 대상을 고른다.
- 등록 전 사용자는 사용처, 사용항목, 금액, 할인 적용 여부를 수정할 수 있다.
- 후보 저장에 성공하면 앱이 `카드 알림 후보 1건 포착` 알림을 띄운다.
- 이 알림은 서버 등록 완료 알림이 아니라, 로컬 등록 대기 후보가 생겼다는 신호다.

Android에서 권한을 켠다.

1. 앱의 `입력` 탭으로 이동한다.
2. `알림에서 가져오기`를 누른다.
3. `알림 접근 권한 열기`를 누른다.
4. Android 설정에서 Money-Note의 알림 접근 권한을 허용한다.
5. 입력 화면 상단에 `앱 알림 표시 권한` 경고가 보이면 `앱 알림 허용`을 눌러 앱 알림도 허용한다.

앱 실행 시 필요한 권한이 빠져 있으면 입력 화면 상단에 `카드 알림 낚시 준비가 덜 됐습니다.` 경고가 표시된다. 알림 낚시에 필요한 권한은 두 가지다.

- 알림 접근 권한: 우리카드 알림을 읽기 위한 권한
- 앱 알림 표시 권한: 후보 저장 성공 알림을 띄우기 위한 권한

현재 알림 파서는 아래 형식을 기준으로 한다.

```text
[일시불.승인(9452)]06/14 17:08 5,000원 / 누적:542,899원
사랑방
```

포맷이나 카드사 앱 패키지가 바뀌면 아래 파일을 먼저 확인한다.

```text
mobile/android/app/src/main/kotlin/com/example/money_note_mobile/CardNotificationListenerService.kt
```

이 파일의 `CARD_APPROVAL_REGEX`가 알림 포맷 파서이고, `AllowedCardApps`가 처리 대상 패키지 allowlist다. 별도 polling이나 백그라운드 상시 루프는 두지 않는다.

## 로그인 계정 생성

사용자 계정은 DB에 저장한다. 비밀번호는 PBKDF2-SHA256 해시로 저장되며 평문 저장하지 않는다.

컨테이너에서 계정을 생성한다.

```bash
docker compose exec -T api env PYTHONPATH=/app \
  python scripts/create_user.py your-username your-password \
  --display-name "사용자" \
  --replace
```

로컬 개발 DB에는 별도 테스트 계정을 만들 수 있다. 테스트 계정 정보는 git에 기록하지 않는다.

운영 전에는 충분히 긴 비밀번호로 관리자 계정을 다시 만든다.

## 비밀번호를 잊었을 때

이 서비스는 1인 사용을 전제로 하므로, 웹에서 별도 재가입 절차를 제공하지 않는다. 비밀번호를 잊으면 서버 로컬 shell에서 기존 계정의 비밀번호를 재설정한다.

```bash
docker compose exec -T api env PYTHONPATH=/app \
  python scripts/create_user.py your-username new-password \
  --display-name "사용자" \
  --replace
```

`--replace`는 같은 `username`이 이미 있을 때 비밀번호 해시와 표시 이름을 새 값으로 갱신한다. DB에는 새 비밀번호 평문이 저장되지 않고, 새 PBKDF2-SHA256 해시만 저장된다.

기존 로그인 세션을 모두 끊고 싶으면 DB에서 해당 사용자의 세션을 삭제한다.

```bash
docker compose exec -T api sqlite3 /app/data/money-note.sqlite3 \
  "DELETE FROM auth_sessions WHERE user_id = (SELECT id FROM users WHERE username = 'your-username');"
```

## 웹 프론트엔드 개발 서버

프론트엔드 의존성을 설치한다.

```bash
cd frontend
npm install
```

개발 서버를 실행한다.

```bash
npm run dev
```

접속 주소:

```text
http://127.0.0.1:5173
```

웹 앱에 접속하면 로그인 화면이 먼저 나타난다. 로그인 후 당월 기록 조작 화면으로 진입한다.

인증 방식:

- 웹 브라우저에서는 `money_note_session` cookie가 기본 인증 수단이다.
- cookie를 쓰기 어려운 클라이언트를 위해 로그인 응답의 `session_token`도 제공한다.
- 프론트엔드는 이후 요청에 `Authorization: Bearer ...` 헤더를 함께 보낼 수 있다.
- 비밀번호 오류는 화면에 `아이디 또는 비밀번호가 맞지 않습니다.`로 표시한다.

조작 저장 방식:

- 추가, 삭제, 확인, 초기화는 버튼을 누르는 즉시 서버 DB에 반영된다.
- 분류 변경은 화면에 임시로 쌓이고, 상단의 `변경 사항 저장` 버튼을 눌러야 서버 DB에 반영된다.
- 이 방식은 여러 지출을 빠르게 분류한 뒤 한 번에 저장하기 위한 UX다.

카드 결제 관리:

- `이번달 결제` 탭은 직전월 1일~말일 사용분을 보여준다.
- 즉시결제는 익월 14일까지 가능하다.
- 카드 할인은 월 정책이 혜택 없음이 아닌 경우 기본 1.2%로 계산한다. 개별 항목의 `할인 제외`를 누르면 해당 항목 할인액은 0원이다.
- 자동 배분 기본 한도는 현재 유동성이며, 날짜 오름차순으로 배분한다.
- 하이패스/통행료가 여러 건이면 결제 화면에서는 하나의 통합 행으로 보인다. 결제나 이월을 누르면 내부 원본 항목에 순서대로 반영된다.
- 결제 화면에서 장부 행을 삭제할 수 있다. 삭제하면 해당 행의 즉시결제, 할인, 이월 참조도 함께 정리된다.
- 청구 탭의 하이패스/통행료는 집에 청구하는 별도 패널 데이터이므로 결제 화면의 통합 행에 섞이지 않는다.
- 현금흐름 입금에 `이달 기준 수입`을 표시하면 파산심사위원회의 해당 월 심사 기준으로 사용한다.
- 이달 기준 수입이 없으면 `base_next_month_liquidity` 설정값, 즉 `기본 예정 수입`을 수입 하한선 겸 fallback 심사 기준액으로 사용하며 설정 화면에서 변경할 수 있다.
- 14일 경과 후 미결제 기록이 있으면 실제 카드 결제는 완료된 것으로 의제하고, 사용자가 유동성 현황을 보정한 뒤 `유동성 보정 완료`를 누른다.

API 서버 주소는 `frontend/.env`로 지정할 수 있다. 이 파일은 Vite 빌드 시점에 읽힌다.

```bash
cd frontend
cp .env.example .env
```

`frontend/.env` 예시:

```text
VITE_API_BASE_URL=http://localhost:18080
```

운영 도메인에서 정적 파일을 배포하고 `/api/`를 같은 도메인에서 Apache reverse proxy한다면 `frontend/.env.production`에는 아래처럼 빈 값을 둔다.

```text
VITE_API_BASE_URL=
```

이 값은 빌드 시점에 결과물에 박제된다. 따라서 `.env.production`을 만들거나 수정한 뒤에는 반드시 `npm run build`를 다시 실행하고, 새 `dist/`를 `/var/www/money-note/`에 다시 복사한다.

프론트엔드 코드는 운영 도메인에서 기본적으로 상대경로를 사용한다. 그래도 운영 배포에서는 `.env.production`을 명시적으로 만들어 두면 빌드 의도가 분명해진다.

운영 빌드 결과가 정상이라면 브라우저에서 API 요청은 현재 도메인 기준의 `/api/...`로 보인다. `127.0.0.1:18080`이 보이면 운영용 환경파일이 적용되지 않은 빌드다.

## 웹 프론트엔드 정적 빌드

```bash
cd frontend
npm run build
```

산출물:

```text
frontend/dist/
```

홈서버에서 웹으로 배포할 때는 `frontend/dist/`의 내용을 Apache `DocumentRoot`인 `/var/www/...` 아래에 배치한다.

예시:

```bash
sudo mkdir -p /var/www/money-note
sudo rsync -a --delete frontend/dist/ /var/www/money-note/
```

인증서, Apache reverse proxy, 도메인 연결은 서버 운영 환경에서 별도로 설정한다.

## Snapshot 백업과 복원

서버 DB가 단일 원본이다.

Snapshot은 장부 운용 데이터 전체와 앱 운영 설정을 담는 JSON 백업 파일이다. 원본 SQLite DB 파일을 그대로 내려받는 방식이 아니며, 사용자 계정과 세션, 관리 로그, 비밀번호/해시, 공유 PIN 해시는 포함하지 않는다.

내보내기:

웹에서는 `설정 -> 위험 작업 영역 -> snapshot 백업`에서 현재 장부와 설정을 단일 snapshot 파일로 내려받는다. 로그인된 사용자 작업이므로 비밀번호 재확인은 요구하지 않는다.

```bash
curl -OJ -b /tmp/money-note-cookie.txt \
  http://localhost:18080/api/admin/snapshot
```

응답 파일 확장자는 `.money-note-snapshot.json`이며, `schema_version`, `exported_at`, `range`, `manifest`, `data`를 포함한다.

현재 snapshot 형식은 `schema_version = 3`이다.

`manifest`는 canonical JSON 기준 SHA-256 무결성 정보를 담는다. `manifest` 자기 자신은 hash 대상에서 제외하며, `data` 전체 hash와 테이블별 컬럼 목록, row count, table hash를 기록한다.

복원은 위험 작업이다. 현재 비밀번호를 다시 확인하며, 장부 운용 데이터와 비민감 운영 설정이 snapshot 내용으로 교체된다. 사용자 계정, 본체 로그인 세션, 가족 공유 세션, 관리 로그는 유지된다.

위험 작업 안전장치:

- 운영 DB를 수정하기 전에 snapshot 구조와 manifest를 검증한다.
- 운영 DB를 수정하기 전에 동일한 삽입 경로로 임시 DB dry-run restore를 수행한다.
- dry-run에서 외래키 오류가 발견되면 복원을 중단한다.
- 실제 restore 직전 현재 운영 DB를 `data/snapshot-backups/pre_restore-...money-note-snapshot.json` 파일로 반드시 저장한다.
- `pre_restore` 파일 생성, JSON parse, manifest 검증 중 하나라도 실패하면 복원을 중단한다.
- 실제 restore 도중 예외가 발생하면 트랜잭션 rollback으로 기존 운영 DB를 보존한다.

서버는 다음 작업 직전에도 현재 장부 상태를 `pre_restore` snapshot으로 자동 저장한다.

- snapshot restore
- 월마감 실행
- 장부 전체 초기화
- 청구 일괄 처리 완료
- 가족카드 일괄 처리 완료

따라서 실수로 큰 변경을 실행한 경우 설정 모달의 `복원 전 백업` 섹션에서 직전 상태로 되돌릴 수 있다.

웹에서는 `설정 -> 위험 작업 영역 -> snapshot 복원`에서 파일을 선택하고 현재 비밀번호를 입력한 뒤 실행한다.

복원 결과가 잘못되었다면 같은 설정 모달의 `복원 전 백업` 섹션을 사용한다.

절차:

1. `목록 조회`를 누른다.
2. restore 직전 시각의 `pre_restore` 항목을 확인한다.
3. 현재 비밀번호를 입력한다.
4. `되돌리기`를 누른다.
5. 필요 없어진 항목은 `삭제` 또는 `일괄 삭제`로 정리한다. 삭제에는 비밀번호 재확인을 요구하지 않는다.

`되돌리기`도 일반 restore와 동일한 검증과 dry-run을 거치며, 되돌리기 직전 상태 역시 새 `pre_restore`로 저장된다.

설정 모달의 `운영 데이터 크기` 섹션에서는 SQLite 파일 크기, 빈 DB 기준 추정 운영 데이터 크기, pre_restore 합계, 테이블별 row count를 확인할 수 있다. 이 값은 운영 상태 점검용이며 정확한 과금/용량 계산값은 아니다.

API로 복원:

```bash
python3 - <<'PY' > /tmp/snapshot-restore.json
import json
from pathlib import Path

snapshot = json.loads(Path("money-note-snapshot.money-note-snapshot.json").read_text())
print(json.dumps({"password": "your-password", "snapshot": snapshot}, ensure_ascii=False))
PY

curl -b /tmp/money-note-cookie.txt \
  -H 'Content-Type: application/json' \
  -d @/tmp/snapshot-restore.json \
  http://localhost:18080/api/admin/snapshot/restore
```

API로 복원 전 백업 목록 조회:

```bash
curl -b /tmp/money-note-cookie.txt \
  http://localhost:18080/api/admin/snapshot/pre-restore
```

API로 복원 전 백업 삭제:

```bash
curl -X DELETE -b /tmp/money-note-cookie.txt \
  http://localhost:18080/api/admin/snapshot/pre-restore/pre_restore-20260611T010101Z.money-note-snapshot.json
```

API로 복원 전 백업 되돌리기:

```bash
curl -b /tmp/money-note-cookie.txt \
  -H 'Content-Type: application/json' \
  -d '{"password":"your-password"}' \
  http://localhost:18080/api/admin/snapshot/pre-restore/pre_restore-20260611T010101Z.money-note-snapshot.json/restore
```

### 클라이언트 자동 백업 정책

향후 모바일 앱과 맥 앱은 앱 실행 시 서버에서 snapshot을 내려받아 각 기기 로컬에 백업 파일을 유지한다.

브라우저 웹앱은 로컬 파일시스템을 안정적으로 제어할 수 없으므로 자동 누적 백업을 구현하지 않는다.

기본 정책:

- 전체 snapshot을 저장한다.
- 앱 실행 때마다 새 파일명으로 snapshot을 누적 저장한다.
- 파일명은 `money-note-snapshot-YYYYMMDD-HHMMSS.money-note-snapshot.json` 형태를 사용한다.
- 기존 snapshot 파일을 덮어쓰지 않는다.
- 사용자는 모바일 `상태 -> 관리 -> 백업 / 복원` 화면에서 파일별 공유, 파일별 복원, 파일별 삭제, 전체 삭제를 수행한다.
- 모바일 앱의 snapshot은 서버 데이터 복원을 자동 수행하지 않는다. 사용자가 명시적으로 특정 snapshot을 선택하고 비밀번호를 입력했을 때만 서버 restore API를 호출한다.

이 정책은 네트워크 중단, 앱 강제 종료, 잘못된 최신 상태가 곧바로 유일한 백업을 덮어쓰는 사고를 줄이기 위한 최소 안전장치다. 저장 공간이 부담되면 모바일 스냅샷 관리 화면에서 오래된 파일을 직접 정리한다.

## 월마감

가장 오래된 미마감 월 기록을 전체 기록으로 넘긴다.

```bash
curl -X POST http://localhost:18080/api/month/current/close \
  -H 'Content-Type: application/json' \
  -d '{"allow_early_close":false}'
```

동작:

- 카드 정기결제, 즉 `entry_kind = planned`인 항목을 제외한 `current` 기록을 `archive`로 복사한다.
- 카드 정기결제 항목은 당월 기록에 남는다.
- 현재 달은 매월 27일부터 `allow_early_close=true`로 조기 마감할 수 있다.
- 조기 마감 뒤 같은 달 날짜로 추가한 일반 지출은 `archive`에 바로 저장된다.
- 청구와 가족카드는 월마감과 무관하며, 각 탭의 `일괄 처리 완료`로 현재 전달분을 삭제한다.

## 읽기 전용 공유 화면

청구:

```text
http://localhost:18080/share/claim
```

가족카드:

```text
http://localhost:18080/share/family_card
```

가족에게 앱 설치 없이 보여주기 위한 read-only 웹 화면이다.

본체 웹 상단의 `공유 PIN 설정`에서 가족 공식 비밀번호 숫자 네 자리를 설정할 수 있다.

- PIN은 평문이 아니라 PBKDF2-SHA256 해시로 저장한다.
- 새 DB는 기본 PIN `0000`으로 잠긴다.
- 가족은 기본 PIN `0000`을 입력해 공유 페이지에 접근할 수 있다.
- 기본 PIN을 다른 값으로 바꿀 때까지 본체 로그인 후 경고가 표시된다.
- 공유 페이지는 항상 PIN 입력 또는 유효한 공유 세션을 요구한다.
- PIN 통과 시 공유 전용 세션을 최대 10년으로 발급한다.
- PIN을 변경하면 기존 가족 공유 세션은 모두 종료된다.
- 카카오톡 인앱 브라우저가 사이트 데이터를 지우면 장기 세션도 사라져 PIN을 다시 입력해야 한다.
- 운영 도메인에서는 HTTPS와 `MONEY_NOTE_COOKIE_SECURE=true`를 사용한다.

공유 화면에는 계좌번호, 송금 링크, 개인정보를 넣지 않는다. 금액과 항목은 공유될 수 있지만, 송금 유도 정보는 공개 링크에 싣지 않는 것을 원칙으로 한다.

## 테스트 절차

기능 확인 순서는 [테스트 절차](test-plan.md)를 따른다.

## 자주 쓰는 개발 검증

백엔드 문법 검사:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/money-note-pycache python3 -m compileall backend/app
```

프론트엔드 빌드:

```bash
cd frontend
npm run build
```

서버 health check:

```bash
curl http://localhost:18080/health
```

비로그인 조작 차단 확인:

```bash
curl -i -X POST http://localhost:18080/api/month/current/planned \
  -H 'Content-Type: application/json' \
  -d '{"title":"unauth test","amount_value":1}'
```

로그인 확인:

```bash
curl -c /tmp/money-note-cookie.txt \
  -H 'Content-Type: application/json' \
  -d '{"username":"your-username","password":"your-password"}' \
  http://localhost:18080/api/auth/login

curl -b /tmp/money-note-cookie.txt http://localhost:18080/api/auth/me
```

Bearer token 인증 확인:

```bash
TOKEN="$(curl -s \
  -H 'Content-Type: application/json' \
  -d '{"username":"your-username","password":"your-password"}' \
  http://localhost:18080/api/auth/login \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_token"])')"

curl -H "Authorization: Bearer $TOKEN" http://localhost:18080/api/auth/me
```

## 관리 로그

본체 웹 상단의 `관리 로그`에서 변경 API의 최근 처리 이력을 확인할 수 있다. 요청 본문과 비밀번호는 기록하지 않는다. `로그 초기화`는 관리 로그 전체를 삭제하며 되돌릴 수 없다.

Docker 콘솔 로그는 다음 명령으로 별도 확인한다.

```bash
docker compose logs -f api
```
