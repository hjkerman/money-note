# 실행 방법

이 문서는 `money-note`를 로컬 개발 환경과 홈서버 배포 환경에서 실행하는 방법을 모아둔다.

## 전제

필요한 런타임:

- Docker 또는 Colima/Docker Compose
- Node.js와 npm
- Git

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
exports/
```

- `data/`: SQLite DB와 Excel template 저장
- `exports/`: export된 `.xlsx` 파일 저장

이 디렉터리들은 개인 데이터가 들어가므로 git에 올리지 않는다.

## 최초 Excel import

현재 Excel 파일을 template으로 복사한 뒤 DB로 import한다.

```bash
mkdir -p data exports
cp /path/to/금전사용기록.xlsx data/template.xlsx
docker compose run --rm api python scripts/import_xlsx.py /app/data/template.xlsx --replace
```

주의:

- 원본 Excel 파일은 직접 수정하지 않는다.
- `--replace`는 기존 DB의 기록/라벨을 비우고 다시 import한다.
- 실제 운영 중에는 `--replace`를 조심해서 사용한다.

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

## 백엔드 환경변수

`docker-compose.yml` 기준 기본값:

```text
MONEY_NOTE_DB_PATH=/app/data/money-note.sqlite3
MONEY_NOTE_EXPORT_DIR=/app/exports
MONEY_NOTE_TEMPLATE_PATH=/app/data/template.xlsx
```

개발용 CORS:

```text
MONEY_NOTE_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

운영에서 웹 프론트엔드 도메인이 달라지면 `MONEY_NOTE_CORS_ORIGINS`에 해당 origin을 추가한다.

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
http://localhost:5173
```

API 서버 주소는 `.env`로 지정할 수 있다.

```bash
cp .env.example .env
```

`.env` 예시:

```text
VITE_API_BASE_URL=http://localhost:18080
```

## 웹 프론트엔드 정적 빌드

```bash
cd frontend
npm run build
```

산출물:

```text
frontend/dist/
```

홈서버에서 웹으로 배포할 때는 `frontend/dist/`의 내용을 `/var/www/...` 아래에 배치한다.

예시:

```bash
sudo mkdir -p /var/www/money-note
sudo rsync -a --delete frontend/dist/ /var/www/money-note/
```

인증서, reverse proxy, 도메인 연결은 서버 운영 환경에서 별도로 설정한다.

## Excel export

API로 export 파일을 생성한다.

```bash
curl -X POST http://localhost:18080/api/export
```

최신 export 파일 다운로드:

```bash
curl -O http://localhost:18080/api/export/latest.xlsx
```

생성된 파일은 컨테이너 기준 `/app/exports`, 호스트 기준 `exports/`에 저장된다.

## 월마감

당월 기록을 전체 기록으로 넘긴다.

```bash
curl -X POST http://localhost:18080/api/month/current/close
```

동작:

- `나갈 돈`을 제외한 `current` 기록을 `archive`로 복사한다.
- 복사된 기록은 `전체 기록(본인)` export 시 hard data 아래에 append된다.
- `나갈 돈` 항목은 당월 기록에 남는다.

## 읽기 전용 공유 화면

청구:

```text
http://localhost:18080/share/claim
```

타인정산:

```text
http://localhost:18080/share/settlement
```

가족에게 앱 설치 없이 보여주기 위한 read-only 웹 화면이다.

## Tauri 계획

현재는 웹 프론트엔드를 먼저 만든다. 이후 같은 `frontend/` UI를 Tauri로 wrapping해 macOS 앱을 만든다.

예상 흐름:

```bash
cd frontend
npm install
npm run build
```

그 다음 Tauri 설정을 추가하고 `.app` 빌드를 구성한다. 인증서, 서명, notarization은 배포 단계에서 별도로 처리한다.

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

