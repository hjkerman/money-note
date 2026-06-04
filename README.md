# money-note

기존 Excel 가계부의 운용 방식을 최대한 유지하면서, 당월 기록을 데스크탑과 모바일에서 조작할 수 있게 만들기 위한 개인 가계부 앱입니다.

기본 source of truth는 서버 DB입니다. Excel 파일은 초기 데이터 import와 휴대 가능한 snapshot export 용도로 사용합니다.

## 현재 계획

- 백엔드: FastAPI, SQLite, openpyxl
- 배포: Ubuntu 24.04 홈서버에서 Docker Compose로 실행
- 웹 프론트엔드: Vite + React + TypeScript
- macOS 앱: 같은 웹 프론트엔드를 Tauri로 wrapping
- 모바일 앱: 필요함. 우선 웹 프론트엔드/API를 안정화하고, 이후 Android 중심으로 구현 방식 결정
- Excel workbook 구조:
  - `당월 기록`: 현재 월 운용 시트
  - `전체 기록(본인)`: 누적 기록 시트

## 클라이언트 개발 방향

먼저 `frontend/`에 웹 앱을 만듭니다. 이 웹 앱은 홈서버의 `/var/www/...`에 정적 파일로 배포할 수 있게 `dist/` 산출물을 생성합니다.

같은 웹 UI를 Tauri로 감싸 macOS `.app`도 실행합니다. 현재 `frontend/src-tauri/`에 데스크탑 앱 골격이 있으며, 개발 실행은 `npm run tauri:dev`로 합니다. 인증서, 서명, notarization은 별도 배포 단계에서 처리합니다.

모바일 앱도 필요합니다. 현재는 서버 API와 웹 UI를 먼저 안정화한 뒤, Android에서 가장 덜 고통스러운 형태로 확장하는 것을 목표로 합니다.

## 현재 구현된 주요 기능

- 당월 지출 추가: `사용처`와 `사용항목`을 나눠 입력하고, Excel export 때는 `[사용처] 사용항목` 형식으로 유지
- 카드 정기결제: 당월 지출과 같은 `사용처`/`사용항목` 구조로 입력하고, 확인 시 당월 지출로 편입
- 분류 저장 UX: 분류 변경은 pending 상태로 모이고 `변경 사항 저장` 버튼으로 일괄 저장
- 청구/타인정산: 행별 삭제와 전체 초기화 지원
- 동결: 확인 시 당월 기록으로 편입 가능
- 할부: 할부액, 수수료율, 개월수를 입력하면 월 납입액을 원 단위 올림으로 계산
- 현금흐름: 현금 입출금 기록이 유동성 현황에 반영
- 이번달 결제: 직전월 카드 사용분을 날짜순으로 자동 배분하거나 직접 선택해 일부 즉시결제/할인액 처리
- 통행료 이월: `통행료`/`하이패스` 항목은 할인·일부결제 없이 전액 처리하거나 다음 달 장부 맨 앞으로 이월
- 수동 월마감: 새 달 기록을 먼저 입력해도 가장 오래된 미마감 월 하나만 전체 기록으로 이동
- 조기 월마감: 매월 27일부터 명시 확인 후 현재 달을 닫을 수 있고, 이후 같은 달 지출은 전체 기록에 바로 추가
- 전월 매입 지연 보정: 카드사가 뒤늦게 올린 직전월 사용내역을 이번달 결제 대상에 추가
- 청구/타인정산 일괄 처리 완료: 전달이 끝난 현재 목록을 한 번에 삭제
- 관리 로그: 변경 API의 사용자·경로·결과를 조회하고 필요할 때 전체 초기화
- 결제 심사: 결제일까지 남은 기간과 주 수입 대비 미결제액을 바탕으로 파산심사위원회 문구 표시
- UI 구조: 주요 테이블은 테이블과 입력창이 같은 panel 안에 있는 형태로 통일
- 통계/월별 기록: `통계 보기` 아래에서 함께 확인
- 판단 모듈: 분류 기준과 문구를 `judgment` 모듈로 분리
- 가족 공유 PIN: 청구/타인정산 공유 링크를 기본 PIN `0000`으로 잠그고, 변경 가능한 네 자리 PIN과 장기 세션 적용

## 빠른 시작

현재 가계부 Excel 파일을 `data/template.xlsx`로 복사한 뒤 import합니다.

```bash
mkdir -p data exports
cp /path/to/금전사용기록.xlsx data/template.xlsx
docker compose run --rm api python scripts/import_xlsx.py /app/data/template.xlsx --replace
```

서버를 시작합니다.

```bash
docker compose up --build -d
```

API는 `http://localhost:18080`에서 접근할 수 있습니다.

웹 프론트엔드는 별도로 실행합니다.

```bash
cd frontend
npm install
npm run dev
```

접속 주소:

```text
http://127.0.0.1:5173
```

macOS 앱으로 확인하려면 웹 개발 서버 대신 Tauri 개발 앱을 실행합니다.

```bash
cd frontend
npm run tauri:dev
```

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

## macOS 앱 개발

Tauri 앱은 웹 앱을 그대로 감싸므로, 화면 구조와 API 호출 방식은 웹 프론트엔드와 같습니다.

필요한 런타임:

```bash
brew install rust
```

개발 실행:

```bash
cd frontend
npm install
npm run tauri:dev
```

앱 번들 생성:

```bash
npm run tauri:build
```

주의:

- `tauri:dev`는 내부에서 Vite 개발 서버를 `http://localhost:5173`에 띄웁니다.
- macOS 앱 기본 개발 창은 1440x920으로, 표와 분류 드롭다운을 보기 좋게 조금 넓게 잡아둡니다.
- 이미 `npm run dev`가 같은 포트에서 실행 중이면 먼저 종료한 뒤 `tauri:dev`를 실행합니다.
- API 서버는 별도로 `docker compose up --build -d`로 실행되어 있어야 합니다.

## API 호출 예시

자세한 명세는 아래 문서를 참고합니다.

- [API 명세](docs/api.md)
- [DB 명세](docs/database.md)
- [실행 방법](docs/runbook.md)
- [macOS 앱 실행](docs/desktop-app.md)
- [아키텍처](docs/architecture.md)
- [테스트 절차](docs/test-plan.md)

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

가장 오래된 미마감 기록을 월마감 처리합니다. 현재 달은 매월 27일부터 조기 마감할 수 있습니다.

```bash
curl -X POST http://localhost:18080/api/month/current/close \
  -H 'Content-Type: application/json' \
  -d '{"allow_early_close":false}'
```

조기 마감은 `allow_early_close=true`로 명시해야 합니다. 월마감은 카드 정기결제가 아닌 해당 월 기록을 동적 전체 기록으로 append하고, 카드 정기결제 항목은 당월 기록에 남겨둡니다. 마감한 달 날짜로 뒤늦게 추가한 지출은 전체 기록에 바로 보관됩니다.

카드 정기결제 항목을 추가합니다.

```bash
curl -X POST http://localhost:18080/api/month/current/planned \
  -H 'Content-Type: application/json' \
  -d '{"title":"[구독서비스] 월간 생존권","usage_place":"구독서비스","usage_item":"월간 생존권","amount_value":12345,"due_day":10}'
```

당월 기록 또는 카드 정기결제 항목의 사용자 정의 정렬을 적용합니다.

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
