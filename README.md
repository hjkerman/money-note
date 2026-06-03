# money-note

기존 Excel 가계부의 운용 방식을 최대한 유지하면서, 당월 기록을 데스크탑과 모바일에서 조작할 수 있게 만들기 위한 개인 가계부 앱입니다.

기본 source of truth는 서버 DB입니다. Excel 파일은 초기 데이터 import와 휴대 가능한 snapshot export 용도로 사용합니다.

## 현재 계획

- 백엔드: FastAPI, SQLite, openpyxl
- 배포: Ubuntu 24.04 홈서버에서 Docker Compose로 실행
- 웹 프론트엔드: Vite + React + TypeScript
- macOS 앱: 웹 프론트엔드를 먼저 만든 뒤 Tauri로 wrapping
- 모바일 앱: 필요함. 우선 웹 프론트엔드/API를 안정화하고, 이후 Android 중심으로 구현 방식 결정
- Excel workbook 구조:
  - `당월 기록`: 현재 월 운용 시트
  - `전체 기록(본인)`: 누적 기록 시트

## 클라이언트 개발 방향

먼저 `frontend/`에 웹 앱을 만듭니다. 이 웹 앱은 홈서버의 `/var/www/...`에 정적 파일로 배포할 수 있게 `dist/` 산출물을 생성합니다.

그 다음 같은 웹 UI를 Tauri로 감싸 macOS `.app`을 만듭니다. 인증서, 서명, notarization은 별도 배포 단계에서 처리합니다.

모바일 앱도 필요합니다. 현재는 서버 API와 웹 UI를 먼저 안정화한 뒤, Android에서 가장 덜 고통스러운 형태로 확장하는 것을 목표로 합니다.

## 빠른 시작

현재 가계부 Excel 파일을 `data/template.xlsx`로 복사한 뒤 import합니다.

```bash
mkdir -p data exports
cp /path/to/금전사용기록.xlsx data/template.xlsx
docker compose run --rm api python scripts/import_xlsx.py /app/data/template.xlsx --replace
```

서버를 시작합니다.

```bash
docker compose up --build
```

API는 `http://localhost:18080`에서 접근할 수 있습니다.

## 웹 프론트엔드 개발

```bash
cd frontend
npm install
npm run dev
```

개발 서버는 기본적으로 `http://localhost:5173`에서 실행됩니다. API 주소는 필요하면 `.env`에서 바꿉니다.

```bash
VITE_API_BASE_URL=http://localhost:18080
```

정적 배포 파일을 생성합니다.

```bash
npm run build
```

생성된 `frontend/dist/`를 홈서버의 `/var/www/...` 아래에 배치하면 됩니다.

## API 호출 예시

자세한 명세는 아래 문서를 참고합니다.

- [API 명세](docs/api.md)
- [DB 명세](docs/database.md)
- [실행 방법](docs/runbook.md)

```bash
curl http://localhost:18080/health
curl http://localhost:18080/api/month/current/summary
curl http://localhost:18080/api/entries/current
curl http://localhost:18080/api/month/current/panels
curl http://localhost:18080/api/share/claim
curl http://localhost:18080/api/share/settlement
curl -X POST http://localhost:18080/api/export
curl -O http://localhost:18080/api/export/latest.xlsx
```

읽기 전용 웹 화면:

- `http://localhost:18080/share/claim`
- `http://localhost:18080/share/settlement`

당월 기록을 월마감 처리합니다.

```bash
curl -X POST http://localhost:18080/api/month/current/close
```

월마감은 `나갈 돈`이 아닌 당월 기록을 동적 전체 기록으로 append하고, `나갈 돈` 항목은 당월 기록에 남겨둡니다.

`나갈 돈` 항목을 추가합니다.

```bash
curl -X POST http://localhost:18080/api/month/current/planned \
  -H 'Content-Type: application/json' \
  -d '{"title":"[매월 n일] 새 예정 지출","amount_value":12345}'
```

당월 기록 또는 `나갈 돈` 항목의 사용자 정의 정렬을 적용합니다.

```bash
curl -X POST http://localhost:18080/api/month/current/reorder \
  -H 'Content-Type: application/json' \
  -d '{"ordered_ids":[3,1,2]}'

curl -X POST http://localhost:18080/api/month/current/planned/reorder \
  -H 'Content-Type: application/json' \
  -d '{"ordered_ids":[28,23,24]}'
```

## 데이터 디렉터리

- `data/`: SQLite DB와 선택적 workbook template 저장
- `exports/`: 생성된 `.xlsx` snapshot 저장

위 디렉터리들은 개인 데이터가 들어가는 위치라 git 추적에서 제외합니다.
