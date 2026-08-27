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

새 클라이언트를 만들 때도 이 기준선을 흔들지 않는다. 필요한 기능이 생기면 먼저 기존 API로 가능한지 확인하고, API 변경이 필요하면 별도 작업으로 분리한다.

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
MONEY_NOTE_LOGIN_MAX_FAILURES=5
MONEY_NOTE_LOGIN_WINDOW_SECONDS=300
MONEY_NOTE_SHARE_PIN_MAX_FAILURES=10
MONEY_NOTE_SHARE_PIN_WINDOW_SECONDS=600
MONEY_NOTE_API_REQUEST_MAX_BYTES=1048576
MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES=26214400
MONEY_NOTE_AUDIT_LOG_RETENTION_DAYS=180
MONEY_NOTE_PRE_RESTORE_KEEP_COUNT=30
MONEY_NOTE_TRUST_PROXY_HEADERS=true
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
- HTTPS 운영 Origin이 있으면 `MONEY_NOTE_COOKIE_SECURE=true`가 필수다. 그렇지 않으면 서버가 기동을 거부한다.
- 처음 로컬 확인만 할 때는 `MONEY_NOTE_COOKIE_SECURE=false`가 편하다.
- `MONEY_NOTE_SESSION_DAYS`는 웹 cookie 로그인 세션 유지 기간이다.
- `MONEY_NOTE_MOBILE_SESSION_DAYS`는 모바일 앱 Bearer 토큰 유지 기간이다. 기본값은 `3650`일이며, 웹 cookie 로그인 기간과 별도로 관리된다.
- 로그인과 공유 PIN 제한값은 공개 주소에서 무제한 대입을 막는다.
- `MONEY_NOTE_API_REQUEST_MAX_BYTES`는 일반 변경 API의 요청 본문 최대 크기다. 기본값은 `1 MiB`다.
- `MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES`는 일반 상한보다 큰 snapshot restore JSON 전용 최대 크기다. chunked 요청에도 적용되며 기본값은 `25 MiB`다.
- `MONEY_NOTE_AUDIT_LOG_RETENTION_DAYS`와 `MONEY_NOTE_PRE_RESTORE_KEEP_COUNT`는 서버 시작 시 오래된 운영 보조 자료를 정리한다.
- Apache와 Docker Compose 기본 구조에서는 `MONEY_NOTE_TRUST_PROXY_HEADERS=true`를 쓴다. 백엔드를 인터넷에 직접 노출하면 `false`로 바꾼다.
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
sudo chown -R 1000:1000 /opt/money-note/data
sudo chmod 700 /opt/money-note/data
```

API 컨테이너는 UID/GID `1000`의 비루트 사용자로 실행한다. 다른 소유자의 기존 DB를 복사했다면 파일과 `snapshot-backups/`도 UID/GID `1000`이 쓸 수 있어야 한다. 기존 DB 파일은 가능하면 `chmod 600`으로 두고, 호스트의 다른 일반 계정에는 `data/` 접근 권한을 주지 않는다.

기존 DB를 옮겨서 시작하려면 서버의 아래 위치에 둔다.

```text
/opt/money-note/data/money-note.sqlite3
```

DB 파일을 직접 복사한 뒤에는 다음 서버 시작 때 누락 컬럼 보강, 오래된 설정 정리 같은 마이그레이션이 자동으로 실행된다.

유동성 이름 migration은 기존 `app_settings`와 `app_labels` 값을 현재 key로 옮긴 뒤 과거 key를 삭제한다. 새 key와 과거 key가 모두 있고 값이 다르면 데이터를 추측해 덮어쓰지 않고 API 시작을 중단한다. 이 경우 SQLite 하드카피를 보존한 상태에서 두 값을 확인하고 하나의 의도된 값으로 정리한 뒤 다시 시작한다.

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
  python scripts/create_user.py your-username 12자-이상-비밀번호 \
  --display-name "사용자" \
  --replace
```

사용자명과 비밀번호는 실제 값으로 바꾼다. 비밀번호는 12자 이상이어야 하며 평문 저장되지 않고 해시만 저장된다. `--replace`로 재설정하면 기존 웹·모바일 세션도 모두 종료한다.

### 7. 웹 프론트엔드 빌드

운영 서버의 Node.js 설치 상태에 빌드가 좌우되지 않도록 `node:22-alpine` 컨테이너에서 빌드한다. 일상 배포의 `scripts/deploy-server.sh`도 같은 방식을 사용한다.

운영 배포에서는 프론트엔드가 API 서버 절대주소를 들고 있지 않게 만든다. `VITE_API_BASE_URL`을 빈 값으로 빌드하면 브라우저가 현재 도메인 기준의 상대경로 `/api/...`, `/share/...`로 요청한다. 그러면 Apache가 내부 백엔드 `127.0.0.1:18080`으로 넘긴다.

```bash
cd /opt/money-note/frontend
docker run --rm \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --env VITE_API_BASE_URL= \
  --volume /opt/money-note/frontend:/app \
  --workdir /app \
  node:22-alpine \
  sh -c 'npm ci --no-audit --no-fund && npm run build'
```

빌드 결과는 아래에 생긴다.

```text
/opt/money-note/frontend/dist/
```

### 8. 웹 파일 배치

운영 Apache의 `DocumentRoot`인 `/var/www/money`에 배치한다.

```bash
sudo mkdir -p /var/www/money
sudo rsync -a --delete /opt/money-note/frontend/dist/ /var/www/money/
```

이 단계까지 끝나면 백엔드는 `localhost:18080`, 프론트엔드 정적 파일은 `/var/www/money`에 있는 상태다.

Android 앱과 Google 비밀번호 관리자를 웹 도메인에 연결하려면 프론트엔드 빌드 결과에 아래 파일이 반드시 포함되어야 한다.

```text
/var/www/money/.well-known/assetlinks.json
```

배치 후 서버에서 확인한다.

```bash
test -f /var/www/money/.well-known/assetlinks.json
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

    DocumentRoot /var/www/money

    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:18080/api/
    ProxyPassReverse /api/ http://127.0.0.1:18080/api/
    ProxyPass /share/ http://127.0.0.1:18080/share/
    ProxyPassReverse /share/ http://127.0.0.1:18080/share/
    ProxyPass /health http://127.0.0.1:18080/health
    ProxyPassReverse /health http://127.0.0.1:18080/health

    <Directory /var/www/money>
        Require all granted
        Options -Indexes
        Header always set Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        Header always set X-Content-Type-Options "nosniff"
        Header always set X-Frame-Options "DENY"
        Header always set Referrer-Policy "no-referrer"
        Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
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

    DocumentRoot /var/www/money

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/money.hjkerman.re.kr/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/money.hjkerman.re.kr/privkey.pem
    Header always set Strict-Transport-Security "max-age=31536000"

    RequestHeader set X-Forwarded-Proto "https"
    ProxyPreserveHost On
    ProxyPass /api/ http://127.0.0.1:18080/api/
    ProxyPassReverse /api/ http://127.0.0.1:18080/api/
    ProxyPass /share/ http://127.0.0.1:18080/share/
    ProxyPassReverse /share/ http://127.0.0.1:18080/share/
    ProxyPass /health http://127.0.0.1:18080/health
    ProxyPassReverse /health http://127.0.0.1:18080/health

    <Location /api/admin/snapshot/restore>
        LimitRequestBody 26214400
    </Location>

    <Directory /var/www/money>
        Require all granted
        Options -Indexes
        Header always set Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'"
        Header always set X-Content-Type-Options "nosniff"
        Header always set X-Frame-Options "DENY"
        Header always set Referrer-Policy "no-referrer"
        Header always set Permissions-Policy "camera=(), microphone=(), geolocation=()"
        RewriteEngine On
        RewriteCond %{REQUEST_FILENAME} !-f
        RewriteCond %{REQUEST_FILENAME} !-d
        RewriteRule ^ /index.html [L]
    </Directory>

    ErrorLog ${APACHE_LOG_DIR}/money-note-error.log
    CustomLog ${APACHE_LOG_DIR}/money-note-access.log combined
</VirtualHost>
```

운영에서는 앞의 HTTP 확인용 vhost를 계속 서비스하지 말고 HTTPS로 리디렉션한다.

```apache
<VirtualHost *:80>
    ServerName money.hjkerman.re.kr
    Redirect permanent / https://money.hjkerman.re.kr/
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

운영에서 브라우저 개발자 도구를 열었을 때 API 요청 주소가 `https://money.hjkerman.re.kr/api/...` 형태여야 한다. `http://127.0.0.1:18080/api/...`가 보이면 `VITE_API_BASE_URL`이 빈 값으로 적용되지 않은 빌드다. 위 컨테이너 명령이나 `scripts/deploy-server.sh --force`로 다시 빌드하고 `/var/www/money`에 배치한다.

### 10. 배포 후 손검증

브라우저에서 실제 도메인에 접속한 뒤 아래를 확인한다.

1. 로그인 가능
2. 새 당월 지출 1건 추가 후 즉시 표시
3. 설정에서 snapshot 백업 다운로드 가능
4. 청구 공유 링크와 가족카드 공유 링크가 PIN 화면을 거쳐 열림
5. `docker compose logs --tail=80 api`에 반복 오류가 없음
6. 로그인 cookie에 `HttpOnly`, `Secure`, `SameSite=Lax`가 설정됨
7. 웹 로그인 응답 JSON의 `session_token`이 `null`임
8. 기본 공유 PIN `0000` 경고가 사라지도록 운영 PIN을 변경함

### 11. 업데이트 절차

일상적인 업데이트는 개발 Mac의 repo 루트에서 아래 한 줄로 수행한다.

```bash
./scripts/deploy-server.sh
```

스크립트는 로컬 커밋이 `origin/main`에 push되었는지 확인한 뒤 SSH로 서버의 `main`을 fast-forward한다. 마지막으로 **실제 배포가 완료된 커밋 해시**를 `/opt/money-note/.git/money-note-deployed-commit`에 기록하고, 그 이후 변경 파일을 기준으로 백엔드와 프론트엔드 중 필요한 영역만 다시 빌드한다. 프론트엔드는 서버에 설치된 Node.js가 아니라 `node:22-alpine` Docker 이미지로 빌드한다. Docker 재빌드, 웹 파일 동기화, API health check가 모두 성공한 뒤에만 이 기록을 갱신한다. 따라서 서버에서 `git pull`만 수행되고 빌드가 실패한 경우에도 다음 실행에서 누락된 배포를 다시 시도한다.

최초 한 번은 로컬에 공용 배포 설정을 만든다.

```bash
cp .env.deploy.example .env.deploy
chmod 600 .env.deploy
```

`.env.deploy`에서 SSH host/user와 서버 경로를 실제 값으로 바꾼다. 이 파일은 서버의 서비스용 `.env`와 별개이며 Git에서 제외된다. SSH 개인키 내용이나 암호를 넣지 말고, 필요하면 `MONEY_NOTE_DEPLOY_IDENTITY_FILE`에 로컬 key file 경로만 둔다.

또한 서버에서 배포 사용자가 Apache 웹 루트에 직접 동기화할 수 있도록 최초 한 번만 권한을 정리한다.

```bash
sudo chown -R "$USER":www-data /var/www/money
sudo chmod -R u+rwX,go+rX /var/www/money
```

그 뒤에는 서버 셸에 들어가 `git pull`, `npm run build`, `rsync`를 직접 실행할 필요가 없다. 변경 파일 판정과 관계없이 프론트엔드와 백엔드를 모두 다시 배포하려면 다음을 사용한다.

```bash
./scripts/deploy-server.sh --force
```

수동 점검이 필요할 때만 서버에서 아래를 확인한다.

```bash
curl http://localhost:18080/health
docker compose logs --tail=80 api
```

문제가 생기면 우선 `docker compose logs --tail=200 api`와 Apache 로그를 본다. 프론트엔드 화면만 이상하면 Node 빌드 컨테이너의 성공 여부, 빈 `VITE_API_BASE_URL`, `/var/www/money` 배치 여부를 먼저 확인한다.

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
MONEY_NOTE_SESSION_DAYS=30
MONEY_NOTE_MOBILE_SESSION_DAYS=3650
MONEY_NOTE_COOKIE_SECURE=false
MONEY_NOTE_LOGIN_MAX_FAILURES=5
MONEY_NOTE_LOGIN_WINDOW_SECONDS=300
MONEY_NOTE_SHARE_PIN_MAX_FAILURES=10
MONEY_NOTE_SHARE_PIN_WINDOW_SECONDS=600
MONEY_NOTE_API_REQUEST_MAX_BYTES=1048576
MONEY_NOTE_SNAPSHOT_RESTORE_MAX_BYTES=26214400
MONEY_NOTE_AUDIT_LOG_RETENTION_DAYS=180
MONEY_NOTE_PRE_RESTORE_KEEP_COUNT=30
MONEY_NOTE_TRUST_PROXY_HEADERS=true
```

위 목록은 현재 `docker-compose.yml`이 `.env`에서 컨테이너로 전달하는 설정이다. 백엔드는 cookie 이름 `money_note_session`과 KST offset `540`을 기본값으로 지원하지만, 현재 Compose 파일은 두 값을 운영 override로 노출하지 않는다. 이를 바꾸려면 문서의 `.env`만 수정하지 말고 Compose 환경변수 매핑도 함께 추가해야 한다.

운영 HTTPS Origin을 설정하면 `MONEY_NOTE_COOKIE_SECURE=true`가 필수다. CORS Origin은 `*`를 허용하지 않으며 scheme과 host를 포함한 정확한 주소를 쉼표로 나열한다.

웹 로그인 cookie는 `MONEY_NOTE_SESSION_DAYS`를 따른다. 모바일 앱은 `/api/auth/mobile-login`에서 받은 Bearer 토큰을 저장하며 `MONEY_NOTE_MOBILE_SESSION_DAYS`를 따른다. 공유 페이지 PIN 세션은 별도 장기 세션을 사용한다.

날짜 민감 기능 검증:

```bash
MONEY_NOTE_TODAY=2026-07-01 docker compose up --build -d
```

`MONEY_NOTE_TODAY`는 월마감, 카드대금, 정기결제 표시처럼 앱 기준일이 필요한 흐름을 검증하기 위한 개발용 override다. 비워두면 실제 오늘 날짜를 사용한다. 운영 서버에서는 설정하지 않는다.

앱 기준일은 기본적으로 KST(+09:00, offset `540`)로 계산한다. 현재 운영 Compose는 이 값을 고정 기본값으로 사용한다.

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

모바일 앱은 `mobile/` 디렉터리의 Flutter 프로젝트다. 웹 앱을 그대로 줄인 것이 아니라, 홈 상태 확인, 빠른 입력, 현금흐름 관리, 당월 내역 확인, 청구/가족카드 정산에 집중한다. 카드대금 실제 결제는 카드사 앱에서 처리하고, Money-Note 모바일 앱에서는 현금 유동성 보정에 집중한다.

모바일 현금 탭과 웹 현금흐름 탭은 서버 기준 날짜를 사용해 직전 월 1일부터 당월 말일까지의 현금흐름만 조회한다. 서버 DB에는 과거 현금흐름이 계속 보존된다. 웹은 `통계 보기` 모달의 `현금흐름` 보기에서 전체 기록을 한 번 불러와 월별로 보여주며, API에서 조건 없는 `GET /api/cash-flows`를 호출해도 전체 기록을 조회할 수 있다.

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

앱 실행 후 로그인 세션이 살아 있으면 서버에서 snapshot을 자동으로 받아 앱 내부에 누적 저장한다. 이 자동 백업은 사용자가 매번 파일을 직접 내려받지 않아도 되는 안전장치다. `설정 -> 백업 / 복원`에서 저장된 스냅샷 목록을 확인하고, 특정 파일을 공유하거나 복원하거나 삭제하거나 전체 삭제할 수 있다.

### ChatGPT 회계감사 공유

홈의 `예산심사위원회` 카드를 누르면 `ChatGPT에게 회계감사 받기` 창이 열린다. 서버 현재 월을 기본값으로 사용하되 실제 장부, 현금흐름 또는 미정산 자료가 존재하는 연월만 선택지에 표시한다. `회계감사 소집`은 선택 월 자료를 기존 API에서 다시 읽고 하나의 Markdown 파일로 조립해 Android ChatGPT 앱(`com.openai.chatgpt`)으로 직접 보낸다. 별도 백엔드 endpoint는 없다.

보고서에는 선택 월의 본인 카드 지출, 현금흐름, 미정산 청구, 미정산 가족카드가 포함된다. 본인 원장의 사용금액과 서버 확정 할인액·실결제액을 함께 적고, 청구와 가족카드를 본인 소비로 합산하지 말라는 분석 지침도 파일 안에 포함한다. 처리 완료된 청구와 가족카드는 운영 중 삭제되므로 과거 월 보고서에도 현재 남아 있는 항목만 들어갈 수 있다.

보고서 끝의 `현재 운영 참고자료`에는 보고서 생성 시점의 현금성 고정지출, 확인 여부와 무관한 카드 정기결제 템플릿, 현재 미삭제 동결 항목을 표시한다. 이는 선택 월 당시의 역사 자료가 아니다. 동결 항목은 등록일만 표시하며, 사용자가 해동하여 삭제한 항목의 이력은 저장하거나 추정하지 않는다. 고정지출·정기결제·동결 금액은 소비 원장과 단순 합산하지 말라는 지침도 Markdown 안에 포함한다.

보고서는 `cache/ai-audit/` 아래에 임시 생성한다. FileProvider는 이 하위 경로만 노출하고 ChatGPT 앱에 읽기 권한만 부여한다. 사용자가 Money-Note로 돌아오면 파일을 삭제하며, 앱이 공유 도중 종료된 경우에도 다음 앱 실행 때 남은 파일을 먼저 삭제한다. 따라서 일반 다운로드 폴더나 사용자가 관리해야 하는 저장 공간에는 보고서를 남기지 않는다.

실기기 확인 전 Google Play의 ChatGPT Android 앱을 설치한다. 설치되지 않았으면 앱은 `ChatGPT 앱을 찾을 수 없습니다.`라고 안내한다. 공유 후 ChatGPT 작성창에 `.md` 첨부파일만 선택되어 있는지 확인한다. 역할, 데이터 해석 규칙과 출력 형식은 모두 파일 안에 포함되며, 사용자는 전송 전에 작성창에 이번 감사의 추가 질문만 입력한다. ChatGPT 앱의 공유 수신 방식이 바뀌면 Android의 `ChatGptShareBridge`만 우선 점검한다.

### 모바일 APK 직접 업데이트

모바일 `설정` 탭 맨 아래의 `APK 다운로드`는 버전 확인 기능이 아니다. 사용자가 누를 때 서버에 현재 배치된 `/api/admin/apk`를 모바일 Bearer 인증으로 내려받고 Android 설치 화면을 연다. 서버에 새 APK를 배치하면 이 버튼은 즉시 그 파일을 받는다. 별도 버전 manifest나 업데이트 확인 API는 사용하지 않는다.

버튼 위의 `현재 설치 버전`은 Android가 현재 설치본에서 읽은 `versionName (versionCode)`다. Git 커밋 시각이나 수동 변경사항 문구는 표시하지 않으므로 빌드 시 추가 메타데이터를 관리할 필요가 없다.

다운로드는 앱 전용 cache의 `apk-updates/`에 `.part` 파일로 스트리밍한다. 응답 MIME type이 APK가 아니거나, 파일이 비었거나, `Content-Length`와 실제 수신량이 다르거나, 200MB를 초과하면 설치를 중단하고 임시 파일을 삭제한다. 완전히 받은 뒤에만 `.apk`로 이름을 바꾼다.

Android 네이티브 설치층은 APK의 package name이 현재 앱의 `kr.re.hjkerman.money_note`와 같은지 확인하고, 설치된 앱과 다운로드한 APK의 서명 인증서 SHA-256이 같은지 대조한다. 버전 번호의 대소는 비교하지 않으며 실제 업그레이드·다운그레이드 허용 여부는 Android Package Installer가 결정한다. APK는 기존 release JKS로 계속 서명해야 한다. 다른 키로 서명된 파일은 Money-Note가 설치 화면을 열기 전에 거부한다.

Android 8 이상에서 최초 사용 시 `이 출처의 앱 설치 허용` 화면이 열린다. 허용한 뒤 Money-Note로 돌아와 `APK 다운로드`를 다시 누른다. 설치가 끝나거나 취소되어 Money-Note로 돌아오면 임시 APK를 삭제하고, 앱이 설치 도중 종료된 경우 다음 실행 시 남은 파일을 정리한다. APK 전송은 운영 HTTPS를 사용한다.

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

### 6.1. 한 명령으로 모바일 release 배포

일상적인 모바일 배포는 repo 루트의 `scripts/release-mobile.sh`를 사용한다. 이 스크립트는 작업 트리가 깨끗한지 확인하고 Flutter 정적 분석·테스트·release 빌드를 수행한 뒤, APK를 서버 임시 경로로 `scp` 전송한다. 로컬과 원격의 SHA-256이 같을 때만 `/opt/money-note/downloads/money-note.apk`로 원자적으로 교체한다. Docker의 `downloads/` bind mount에는 즉시 반영되므로 컨테이너를 재시작하지 않는다.

서버 배포와 같은 `.env.deploy`를 사용한다. 아직 만들지 않았다면 예제를 복사하고 실제 SSH 정보를 입력한다.

```bash
cp .env.deploy.example .env.deploy
chmod 600 .env.deploy
```

`MONEY_NOTE_DEPLOY_IDENTITY_FILE`에는 SSH 개인키 내용이나 암호가 아니라 로컬 key file 경로만 적는다. 비워두면 SSH config와 `ssh-agent`를 사용한다. YubiKey FIDO2 SSH key를 쓸 때는 OpenSSH가 생성한 key-handle file 경로를 적고 PIN·터치는 OpenSSH에 맡긴다. Android release JKS 설정은 기존 `mobile/android/key.properties`에 두거나 같은 환경파일의 `MONEY_NOTE_KEYSTORE_*` 값을 사용한다.

모바일 버전은 자동으로 올리지 않는다. `mobile/pubspec.yaml`의 버전을 확인한 뒤 다음 한 줄로 배포한다.

```bash
./scripts/release-mobile.sh
```

스크립트는 Git commit이나 push를 수행하지 않는다. 에이전트 작업에서는 모바일 검증 및 release 빌드, 커밋, push를 마친 뒤 같은 커밋의 작업 트리가 깨끗한 상태에서 이 스크립트를 실행한다. 모바일 변경이 없는 push에는 APK를 다시 배포하지 않는다.

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

release manifest는 평문 HTTP 통신을 차단한다. 운영 빌드의 `MONEY_NOTE_API_BASE_URL`은 반드시 `https://` 주소여야 하며, 로컬 `http://10.0.2.2:18080`은 debug 실행에만 사용한다.

Android Gradle 메모:

- 앱 모듈은 `org.jetbrains.kotlin.android` 플러그인을 직접 적용하지 않는다.
- 루트 설정은 Flutter 플러그인 호환을 위해 Kotlin Gradle Plugin `2.2.20` 버전만 선언한다.
- Android 빌드 도구는 Android Gradle Plugin `8.11.1`, Gradle `8.14.3`, JDK 17을 사용한다. Flutter `3.44.8`에서 Gradle 9 계열은 Money Note와 빈 Flutter 앱 모두 설정 초기화 오류가 발생하므로, 실제 APK 빌드가 검증된 이 조합을 유지한다.
- `kotlin.compilerOptions` DSL로 JVM target을 지정한다.
- 일부 Flutter 플러그인이 아직 Kotlin Android 플러그인을 직접 적용하므로 `android.builtInKotlin=false`와 `android.newDsl=false`를 유지한다. 플러그인들이 AGP 내장 Kotlin을 지원하면 두 플래그를 제거하고 빌드를 재검증한다.
- `share_plus 13.2.1`에서는 과거의 플러그인 자체 Kotlin Gradle Plugin 경고가 재현되지 않는다.

Android 도구 버전을 바꾼 뒤에는 최소한 다음을 모두 실행한다.

```bash
cd mobile
flutter clean
flutter pub get
flutter analyze
flutter test
flutter build apk --debug
cd android
./gradlew :app:testDebugUnitTest --quiet
```

### 8. 카드·통행료 알림 수집 확인

모바일 앱의 `알림에서 가져오기`는 우리카드 승인과 고속도로 통행료+ 알림을 로컬 후보함으로 모으는 화면이다. 출처별 원문과 파싱 상태는 `설정 -> 최근 납치한 알림`의 `우리카드`/`통행료` 탭에서 확인한다.

처리 원칙:

- Android `NotificationListenerService`는 하나만 사용한다.
- 우리카드 패키지는 `com.wooricard.smartapp`이다.
- 고속도로 통행료+ 패키지는 Google Play 등록정보로 확인한 `com.ex.hipass_app`이다.
- 일시불 승인 알림만 자동 후보 생성 대상으로 삼는다.
- 후보는 앱 로컬에 저장하며, 알림 수신 즉시 서버로 전송하지 않는다.
- 사용자가 후보를 확인하고 `등록`을 눌렀을 때만 기존 본인 원장, 청구, 가족카드 API를 호출한다.
- 본인카드 후보는 기본 `본인 사용`, 선택 가능 대상은 `본인 사용`/`청구 사용`이다.
- 가족카드 후보는 기본 `가족 사용`, 선택 가능 대상은 `가족 사용`/`본인 사용`이다.
- 할부 승인, 파싱 실패, 광고/혜택 안내는 후보로 만들지 않고 `최근 납치한 알림`의 우리카드 로그에 남긴다.
- 고속도로 통행료+ 알림은 날짜·시각을 먼저 찾고, 이후 구간에서 금액과 요금 확인 불가 표식을 찾아 통행료 후보를 만든다.
- 날짜는 있지만 금액을 읽지 못한 알림은 `partial` 후보로 저장하며 사용자가 금액을 입력하기 전에는 등록할 수 없다.
- 통행료 후보는 기본 `본인 사용`, 선택 가능 대상은 `본인 사용`/`청구 사용`이고 할인은 항상 제외한다.
- 기존 통행료 원문 로그는 후보로 소급 변환하지 않는다. 앱 갱신 뒤 새로 받은 알림만 후보가 된다.
- 출처별 로그는 로컬에 최근 30건만 유지한다.
- 리스너 재연결 시 알림창에 남은 우리카드·통행료 알림을 다시 읽고 기존 파서와 저장 경로로 처리한다.
- 중복 방지 처리 이력은 `notificationKey + postTime`을 기준으로 마지막 관측 후 7일, 최대 512건 유지한다. 등록·삭제한 후보도 보관 기간에는 다시 생성하지 않는다.
- 후보·원문·처리 이력 JSON은 Android `AtomicFile`로 교체하여 저장 도중 프로세스가 종료되어도 직전 파일을 복구할 수 있게 한다.
- 저장 시 Android 로그 태그 `MN_NOTIFY`로 packageName, title, text, bigText, rawText, 파싱 상태, 후보 생성 여부, 저장 건수를 남긴다.
- `최근 납치한 알림`의 각 탭에서 원문을 개별 또는 출처별 파일로 공유하고 삭제할 수 있다.
- Android의 `새 내역 발견!` 요약 알림은 통행료 후보를 본인카드 미확인 건수에 합산한다. 후보 화면에서는 기존처럼 통행료 묶음을 따로 표시한다.
- 우리카드 파싱 실패·할부 수동처리와 통행료 파싱 실패·금액 미확인(`partial`)은 별도 `알림 파싱 확인 필요` 알림을 누르면 해당 출처의 원문 탭으로 이동한다. 금액 미확인 경고는 후보를 등록하거나 삭제하면 해제된다.

Android에서 권한을 켠다.

1. 앱의 `입력` 탭으로 이동한다.
2. `알림에서 가져오기`를 누른다.
3. Android 설정에서 Money-Note의 알림 접근 권한을 허용한다.
4. 홈 화면에 `앱 알림 표시 권한` 경고가 보이면 `앱 알림 허용`을 눌러 앱 알림도 허용한다.

앱 실행 시 필요한 권한이 빠져 있으면 홈 화면에 `카드 알림 낚시 준비가 덜 됐습니다.` 경고가 표시된다. 알림 낚시에 필요한 권한은 두 가지다.

- 알림 접근 권한: Android 알림 원문을 관측하기 위한 권한
- 앱 알림 표시 권한: 향후 알림 관련 안내를 띄우기 위한 권한

알림 수집과 후보 생성 동작은 아래 파일을 먼저 확인한다.

```text
mobile/android/app/src/main/kotlin/com/example/money_note_mobile/CardNotificationListenerService.kt
mobile/android/app/src/main/kotlin/com/example/money_note_mobile/NotificationSource.kt
mobile/android/app/src/main/kotlin/com/example/money_note_mobile/NotificationCandidateStore.kt
mobile/android/app/src/main/kotlin/com/example/money_note_mobile/HighwayTollNotificationParser.kt
mobile/android/app/src/main/kotlin/com/example/money_note_mobile/NotificationCaptureNotifier.kt
```

별도 polling이나 백그라운드 상시 루프는 두지 않는다. 알림 리스너 콜백으로 들어온 지원 패키지 알림만 처리한다. `CardNotificationListenerService`라는 클래스명은 기존 알림 접근 권한의 Android component를 유지하기 위한 호환 이름이다.

#### 패키지명 확인

현재 고속도로통행료+ 패키지는 `com.ex.hipass_app`으로 확인되어 있다. 향후 앱 교체나 패키지 변경이 의심되면 설치된 실기기에서 확인한다.

```bash
adb shell pm list packages | rg 'hipass|toll|wooricard'
```

앱을 화면에 띄운 뒤 현재 foreground activity를 확인할 수도 있다.

```bash
adb shell dumpsys activity activities | rg 'mResumedActivity'
```

알림이 도착할 때 Money Note가 실제로 저장했는지 확인한다.

```bash
adb logcat -s MN_NOTIFY
```

통행료 로그 카드의 `Package` 값이 `com.ex.hipass_app`인지 확인한다. 공식 Google Play 주소도 패키지 ID를 포함한다.

```text
https://play.google.com/store/apps/details?id=com.ex.hipass_app
```

#### 통행료 파싱과 수동 확정

고속도로 통행료+는 알림 본문의 완전한 문장 규격을 공개하지 않는다. 파서는 문장 전체 일치를 요구하지 않고 다음 순서로 읽는다.

1. 정확한 패키지명으로 출처를 식별한다.
2. 제목과 본문에서 `카드`·`내역`·`알림` 또는 유료도로 통과 핵심 표식을 확인한다.
3. 날짜·시각을 독립적으로 찾는다.
4. 발견한 날짜·시각 이후에서만 금액과 `요금`·`확인`·부정 표현을 찾는다.
5. 날짜·시각 끝과 금액/오류 표식 시작 사이의 문자열을 구간으로 정리한다.
6. 날짜가 없으면 `failed`, 날짜만 있으면 `partial`, 날짜와 금액이 있으면 `parsed`로 기록한다.
7. 사용자는 후보에서 본인 사용 또는 청구 사용, 금액을 확인한 뒤 `등록`한다.

통행료 후보의 사용처는 `통행료`다. `미지정(입구)-인천`은 `미지정-인천`으로 정리하고 양 끝 이름이 같으면 하나로 줄인다. 통행료는 우리카드 기본 할인 대상이 아니므로 할인 UI를 표시하지 않고 할인 제외로 등록한다. 후보와 원문만 저장된 상태는 원장이나 청구 금액에 영향을 주지 않는다.

실기기 확인 순서:

1. 새 통행료 알림을 받은 뒤 Android의 `새 내역 발견!` 알림에서 본인카드 미확인 건수가 1 증가하는지 확인한다.
2. `알림에서 가져오기`의 본인카드 탭에서 `통행료 후보(계: n원)` 묶음을 확인한다.
3. 금액 확인 불가 알림은 빈 금액으로 보이고 `알림 파싱 확인 필요` 알림도 나타나며, 금액 입력 전 등록되지 않는지 확인한다.
4. 본인 사용과 청구 사용을 각각 한 번 등록하고 서버 조회 결과를 확인한다.
5. 후보 등록/삭제 뒤 Android의 본인카드 미확인 건수가 즉시 줄어드는지 확인한다.
6. 관련 통행료 알림인데 날짜가 없는 표본은 후보 대신 파싱 실패 알림과 원문 로그가 남는지 확인한다.
7. 앱이 열린 상태에서 `새 내역 발견!` 알림을 누르면 즉시 `알림에서 가져오기` 화면이 열리는지 확인한다.
8. 알림 접근 권한을 껐다 켠 뒤 알림창에 남은 지원 알림이 한 번만 회수되고 후보가 중복되지 않는지 확인한다.
9. 후보를 등록하거나 삭제한 뒤 같은 활성 알림을 재수집해도 7일 안에는 후보가 되살아나지 않는지 확인한다.

후불 하이패스카드 또는 차량 하이패스 단말기 직접 판독은 별도 하드웨어와 폐쇄형 규격을 다루는 프로젝트가 되므로 Money Note의 현재 fallback 범위에서 제외한다.

## 로그인 계정 생성

사용자 계정은 DB에 저장한다. 비밀번호는 PBKDF2-SHA256 해시로 저장되며 평문 저장하지 않는다.

컨테이너에서 계정을 생성한다.

```bash
docker compose exec -T api env PYTHONPATH=/app \
  python scripts/create_user.py your-username 12자-이상-비밀번호 \
  --display-name "사용자" \
  --replace
```

로컬 개발 DB에는 별도 테스트 계정을 만들 수 있다. 테스트 계정 정보는 git에 기록하지 않는다.

본체 비밀번호는 12자 이상이어야 한다.

## 비밀번호를 잊었을 때

이 서비스는 1인 사용을 전제로 하므로, 웹에서 별도 재가입 절차를 제공하지 않는다. 비밀번호를 잊으면 서버 로컬 shell에서 기존 계정의 비밀번호를 재설정한다.

```bash
docker compose exec -T api env PYTHONPATH=/app \
  python scripts/create_user.py your-username 12자-이상-새-비밀번호 \
  --display-name "사용자" \
  --replace
```

`--replace`는 같은 `username`이 이미 있을 때 비밀번호 해시와 표시 이름을 갱신하고 기존 웹·모바일 세션을 모두 종료한다. DB에는 새 비밀번호 평문이 저장되지 않고 새 PBKDF2-SHA256 해시만 저장된다.

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

- 웹 브라우저는 `money_note_session` HttpOnly cookie만 사용한다.
- 웹 로그인 응답은 `session_token`을 노출하지 않는다.
- 모바일만 `/api/auth/mobile-login`에서 장기 Bearer 토큰을 받는다.
- 비밀번호 오류는 화면에 `아이디 또는 비밀번호가 맞지 않습니다.`로 표시한다.

조작 저장 방식:

- 추가, 삭제, 확인, 초기화는 버튼을 누르는 즉시 서버 DB에 반영된다.
- 분류 변경을 포함한 드롭다운과 버튼 조작은 즉시 서버 DB에 반영한다.
- 변경 후 관련 영역을 다시 조회해 서버가 확정한 할인·합계·판단 결과를 화면에 반영한다.

카드 결제 관리:

- `이번달 결제` 탭은 마지막 월마감이 만든 활성 결제 batch를 보여준다. 달력상 직전월을 클라이언트가 추정하지 않는다.
- 즉시결제는 익월 14일까지 가능하다.
- 웹은 한 번의 즉시결제 시도에 idempotency key를 만들고 응답 이후 화면 재조회까지 성공할 때까지 같은 key를 유지한다. 네트워크 응답이 끊겨 재시도해도 서버는 같은 결제와 현금흐름을 중복 생성하지 않는다.
- 본인카드와 가족카드는 독립된 정책 객체와 월별 혜택 스위치를 가진다. 현재 두 정책은 우연히 같은 1.2% 계산식을 사용한다.
- 통행료카드는 항상 자동 할인 없음이다. 교통카드는 설정에서 현재 월부터 `자동 할인 없음` 또는 `본인카드와 동일`을 선택하며, 후자는 본인카드 계산식과 그 월의 혜택 상태를 함께 따른다.
- 개별 항목의 `할인 제외`를 누르면 수동 override 0원이 저장된다. 실결제액 직접 수정으로 저장한 수동 override는 카드 종류와 월별 혜택 상태보다 우선한다.
- 자동 배분 기본 한도는 현금흐름 반영액이며, 날짜 오름차순으로 배분한다.
- 하이패스/통행료가 여러 건이면 결제 화면에서는 하나의 통합 행으로 보인다. 결제나 이월을 누르면 내부 원본 항목에 순서대로 반영된다.
- 결제 화면에서 장부 행을 삭제할 수 있다. 삭제하면 해당 행의 즉시결제, 할인, 이월 참조도 함께 정리된다.
- 청구 탭의 하이패스/통행료는 집에 청구하는 별도 패널 데이터이므로 결제 화면의 통합 행에 섞이지 않는다.
- 현금흐름 입금에 `이달 기준 수입`을 표시하면 파산심사위원회의 해당 월 심사 기준으로 사용한다.
- 이달 기준 수입이 없으면 `scheduled_income` 설정값, 즉 `기본 예정 수입`을 수입 하한선 겸 fallback 심사 기준액으로 사용하며 설정 화면에서 변경할 수 있다.
- 14일 경과 후 미결제 기록이 있으면 이를 숨기지 않고 안내한다. 사용자가 카드사 내역을 확인하고 현금흐름 반영액을 보정한 뒤 `현금흐름 보정 완료`를 누른다.
- 카드 즉시결제가 만든 현금흐름을 현금흐름 화면에서 직접 삭제하는 것은 현재 차단하지 않는다. 이 경우 결제 이벤트와 Active 계좌 잔액이 어긋날 수 있으므로 정상 취소는 `이번달 결제`의 이벤트 취소를 사용한다.

카드 교체 또는 할인 정책 변경:

1. `backend/app/services/card_charge/registry.py`에서 해당 카드의 기존 `PolicyBinding`을 수정하지 않는다.
2. 새 정책 객체와 효력 시작월 `YYYY-MM`을 가진 binding을 정책 이력 끝에 추가한다.
3. 본인카드, 가족카드, 통행료카드, 교통카드는 독립 이력이므로 실제로 바뀐 카드만 수정한다.
4. `backend/tests/test_card_charge.py`에 변경 전월과 변경 시작월의 계산을 모두 추가한다.
5. 서버 테스트와 Snapshot 복원 검증 후 백엔드 컨테이너만 재빌드한다. API 응답 형식을 바꾸지 않았다면 웹·모바일 재빌드는 필요 없다.

교통카드를 본인카드와 같은 혜택으로 전환하는 현재 지원 범위에서는 코드 binding을 바꾸지 않는다. 웹 또는 모바일 설정에서 `본인카드와 동일`을 변경하면 서버 기준 현재 월 키가 저장된다. 같은 월의 기존 교통카드 거래도 재계산되며 이전 월은 유지된다.

API 서버 주소는 `frontend/.env`로 지정할 수 있다. 이 파일은 Vite 빌드 시점에 읽힌다.

```bash
cd frontend
cp .env.example .env
```

`frontend/.env` 예시:

```text
VITE_API_BASE_URL=http://localhost:18080
```

운영 도메인에서 정적 파일을 배포하고 `/api/`를 같은 도메인에서 Apache reverse proxy한다면 빌드 환경의 `VITE_API_BASE_URL`을 빈 값으로 둔다.

```text
VITE_API_BASE_URL=
```

이 값은 빌드 시점에 결과물에 박제된다. `scripts/deploy-server.sh`는 Node 컨테이너에 빈 값을 명시한다. 수동 빌드라면 같은 환경값으로 다시 빌드한 뒤 새 `dist/`를 `/var/www/money/`에 복사한다.

프론트엔드 코드는 운영 도메인에서 상대경로를 사용한다. `frontend/.env.production` 파일은 자동 배포에 필요하지 않으며, 개발자가 수동 빌드를 반복할 때만 같은 빈 값을 기록하는 선택 사항이다.

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
sudo mkdir -p /var/www/money
sudo rsync -a --delete frontend/dist/ /var/www/money/
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

응답 파일 확장자는 `.money-note-snapshot.json`이며, `schema_version`, `exported_at`, `range`, `card_charge_policy`, `manifest`, `data`를 포함한다.

현재 snapshot export 형식은 `schema_version = 7`이다. v7은 확인된 현금성 고정지출의 확인 월, 카드 정기결제 원본 관계와 카드 결제 idempotency 정보를 추가로 보존한다. v4, v5, v6, v7을 복원하며 구버전의 nullable 신규 필드 누락은 허용한다. 파일 형식 v3 이하는 지원하지 않는다.

`manifest`는 canonical JSON 기준 SHA-256 무결성 정보를 담는다. `manifest` 자기 자신과 파생 식별자인 `snapshot_id`는 hash 대상에서 제외하며, `data` 전체 hash, 테이블별 컬럼 목록·row count·table hash, `card_charge_policy` hash, 주요 상단 메타데이터와 정책 명세를 포함한 전체 content hash를 기록한다.

`card_charge_policy`는 카드별 정책 ID, 적용 시작월, 정책 종류와 할인율, 교통카드 프로필 선택 의미, 교통·통행 분류 규칙, Snapshot 데이터가 포괄하는 마지막 월 `covered_through`를 담는 검증용 명세다. 복원 시 서버는 이를 실행하지 않고 현재 코드의 정책 레지스트리와 비교한다. 당시 binding이나 분류 규칙이 바뀌었으면 복원을 중단한다. `covered_through` 이후부터 적용되는 새 binding이 현재 서버에 추가된 경우는 허용한다. 2026-08-20 v4 백업 전환용으로 내부 카드 정책 명세 v1 읽기 경로만 남아 있다.

하위호환 정책:

- 서버는 snapshot 원문 기준으로 manifest를 먼저 검증한다.
- 버전 4~7은 manifest 검증 뒤 Snapshot 당시 카드 정책과 분류 규칙이 현재 서버에 보존되어 있는지 확인한다.
- v4의 과거 유동성 설정·라벨 key는 원문 manifest 검증 뒤 현재 key로 정규화한다.
- v4에 같은 의미의 과거 key와 현재 key가 함께 있고 값이 다르면 복원을 중단한다.
- 버전 3 이하는 지원하지 않는다.
- 검증을 통과한 뒤 현재 서버가 모르는 컬럼은 복원 삽입 전에 무시한다.
- 현재 서버에 새로 생긴 컬럼이 구버전 snapshot에 없으면 DB 기본값 또는 `NULL`로 복원한다.
- 금액 컬럼은 현재 DB에서 원화 정수 `INTEGER`로 저장한다.
- 구버전 snapshot/백업 JSON에 `1000.0`, `1000.9`처럼 float 금액이 있으면 검증 통과 후 DB 삽입 직전에 소수점 아래를 절삭해 `1000`으로 정규화한다.
- 필수 테이블 누락, 민감 설정 포함, manifest 불일치, 외래키 오류는 계속 복원 실패로 처리한다.
- `NOT NULL`이면서 기본값이 없는 새 필수 컬럼이 누락된 경우에는 임시 DB dry-run에서 실패해야 하며, 운영 DB는 건드리지 않는다.

복원은 위험 작업이다. 현재 비밀번호를 다시 확인하며, 장부 운용 데이터와 비민감 운영 설정이 snapshot 내용으로 교체된다. 사용자 계정, 본체 로그인 세션, 가족 공유 세션, 관리 로그는 유지된다.

위험 작업 안전장치:

- 일반 snapshot export는 하나의 SQLite read transaction에서 모든 테이블을 읽어 중간 write가 일부 테이블에만 섞이지 않게 한다.
- 운영 DB를 수정하기 전에 snapshot 구조와 manifest를 검증한다.
- 운영 DB를 수정하기 전에 동일한 삽입 경로로 임시 DB dry-run restore를 수행한다.
- dry-run에서 외래키 오류가 발견되면 복원을 중단한다.
- 실제 restore 직전 write transaction을 먼저 확보하고, 같은 transaction에서 본 현재 운영 DB를 `data/snapshot-backups/pre_restore-...money-note-snapshot.json` 파일로 반드시 저장한다.
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

모바일 앱은 앱 실행 시 서버에서 snapshot을 내려받아 앱 전용 저장소에 백업 파일을 유지한다.

브라우저 웹앱은 로컬 파일시스템을 안정적으로 제어할 수 없으므로 자동 누적 백업을 구현하지 않는다.

기본 정책:

- 전체 snapshot을 저장한다.
- 앱 실행 때마다 새 파일명으로 snapshot을 누적 저장한다.
- Android에서 앱이 백그라운드에서 포그라운드로 돌아올 때도 서버 데이터를 다시 조회하고 새 snapshot을 저장한다.
- 파일명은 `money-note-snapshot-YYYYMMDD-HHMMSSmmm.money-note-snapshot.json` 형태를 사용한다.
- 기존 snapshot 파일을 덮어쓰지 않는다.
- 모바일 앱은 최근 30개 snapshot만 유지하며, 30개를 초과하면 가장 오래된 파일부터 삭제한다.
- 사용자는 모바일 `설정 -> 백업 / 복원` 화면에서 파일별 공유, 파일별 복원, 파일별 삭제, 전체 삭제를 수행한다.
- 모바일 앱의 snapshot은 서버 데이터 복원을 자동 수행하지 않는다. 사용자가 명시적으로 특정 snapshot을 선택하고 비밀번호를 입력했을 때만 서버 restore API를 호출한다.

이 정책은 네트워크 중단, 앱 강제 종료, 잘못된 최신 상태가 곧바로 유일한 백업을 덮어쓰는 사고를 줄이기 위한 최소 안전장치다. 저장 공간이 부담되면 모바일 스냅샷 관리 화면에서 오래된 파일을 직접 정리한다.

## 월마감

가장 오래된 미마감 월 기록을 전체 기록으로 넘긴다.

```bash
curl -X POST http://localhost:18080/api/month/current/close \
  -H 'Content-Type: application/json' \
  -d '{"allow_early_close":false,"target_month":"2026-06"}'
```

동작:

- 카드 정기결제, 즉 `entry_kind = planned`인 항목을 제외한 `current` 기록을 `archive`로 복사한다.
- `target_month`는 직전 status 조회의 `oldest_open_month`를 사용한다. 동일 target 재시도는 이미 처리된 결과로 끝나며 archive, 급여와 결제 batch를 중복 생성하지 않는다.
- 카드 정기결제 항목은 당월 기록에 남는다.
- 월마감 시점의 기본 예정 수입을 닫힌 달의 다음 달 1일자 `급여` 입금으로 한 건 기록한다. 이 행은 `이달 기준 수입`이며 같은 급여를 수동으로 다시 입력하지 않는다.
- 월마감이 끝나면 해당 월 원장으로 `이번달 결제`용 활성 batch를 새로 만든다.
- 결제 화면은 달력상 직전월을 자동 조회하지 않고, 마지막 월마감이 만든 활성 batch만 보여준다.
- 새 월마감이 실행되면 이전 결제 batch와 그 즉시결제/할인 배분은 임시 작업 데이터로 보고 삭제한다.
- 결제 화면에서 이월한 항목은 다음 달 원장 맨 위에 `[이월] [n월 사용 내역] ...` 형태로 남고, 그 달 월마감 후 다음 결제 batch에 편입된다.
- 현재 달은 매월 27일부터 `allow_early_close=true`로 조기 마감할 수 있다.
- 조기 마감 뒤 같은 달 날짜로 추가한 일반 지출은 `archive`에 바로 저장된다.
- 현금성 고정지출은 처리일이 오늘 이하일 때만 확인할 수 있다. 월마감은 `confirmed_month`가 마감 대상 월인 상태만 reset하므로 밀린 과거 월마감이 이후 주기 확인을 되돌리지 않는다.
- 청구와 가족카드는 월마감과 무관하며, 각 탭의 `일괄 처리 완료`로 월 값에 관계없이 현재 남은 전달 큐 전체를 삭제한다.
- 월마감 실패 시 archive 이동, `급여` 생성, 결제 batch가 모두 rollback된다. 실행 전 mandatory pre_restore는 그대로 남는다.

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
  http://localhost:18080/api/auth/mobile-login \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_token"])')"

curl -H "Authorization: Bearer $TOKEN" http://localhost:18080/api/auth/me
```

전체 보안 설정과 남는 위험은 [보안 운영](security.md)을 함께 확인한다.

## 관리 로그

본체 웹 상단의 `관리 로그`에서 변경 API의 최근 처리 이력을 확인할 수 있다. 요청 본문과 비밀번호는 기록하지 않는다. `로그 초기화`는 관리 로그 전체를 삭제하며 되돌릴 수 없다.

Docker 콘솔 로그는 다음 명령으로 별도 확인한다.

```bash
docker compose logs -f api
```
