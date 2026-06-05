# money-note

개인 신용카드 생활에 맞춘 1인용 가계부 웹 앱입니다.

서버 DB가 원본 데이터입니다. 과거의 스프레드시트 운용 방식에서 출발했지만, 현재 앱은 웹 UI와 API를 중심으로 동작하며 백업은 CSV zip으로 관리합니다.

## 현재 계획

- 백엔드: FastAPI + SQLite
- 배포: Ubuntu 24.04 홈서버에서 Docker Compose로 실행
- 웹 프론트엔드: Vite + React + TypeScript
- 데스크탑 앱: 웹 프론트엔드가 안정된 뒤 다시 검토
- 모바일 앱: 필요함. 우선 웹 프론트엔드/API를 안정화하고, 이후 Android 중심으로 구현 방식 결정

## 주요 기능

- 당월 지출: 사용일, 사용처, 사용항목, 금액, 분류를 관리
- 카드 정기결제: 결제일순 정렬, 확인 시 당월 지출로 편입
- 청구/타인정산: 가족에게 보여줄 읽기 전용 공유 화면과 일괄 처리 완료
- 동결: 살지 말지 보류한 임시 항목. 실제 지출은 직접 기록하고 동결 항목은 삭제
- 할부: 할부액, 수수료율, 개월수를 입력하면 월 납입액을 원 단위 올림으로 계산
- 현금흐름: 현금 입출금 기록을 유동성 현황에 반영
- 이번달 결제: 직전월 카드 사용분을 날짜순으로 자동 배분하거나 직접 선택해 일부 즉시결제/할인액 처리
- 통행료 이월: `통행료`/`하이패스` 항목은 할인·일부결제 없이 전액 처리하거나 다음 달 장부 맨 앞으로 이월
- 수동 월마감: 새 달 기록을 먼저 입력해도 가장 오래된 미마감 월 하나만 전체 기록으로 이동
- 조기 월마감: 매월 27일부터 명시 확인 후 현재 달을 닫을 수 있고, 이후 같은 달 지출은 전체 기록에 바로 추가
- 전월 매입 지연 보정: 카드사가 뒤늦게 올린 직전월 사용내역을 이번달 결제 대상에 추가
- 관리 로그: 변경 API의 사용자·경로·결과를 조회하고 필요할 때 전체 초기화
- CSV 백업/복원: 장부 운용 데이터를 zip으로 내보내고 다시 가져오기
- 판단 모듈: 분류 기준과 문구를 백엔드 `judgment` 모듈로 분리하고 프론트는 서버 판단 결과를 표시
- 가족 공유 PIN: 청구/타인정산 공유 링크를 기본 PIN `0000`으로 잠그고, 변경 가능한 네 자리 PIN과 장기 세션 적용

## 빠른 시작

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

## CSV 백업

웹 상단의 `CSV 백업` 버튼으로 현재 장부 운용 데이터를 zip 파일로 받을 수 있습니다.

복원은 `CSV 복원` 버튼으로 수행합니다. 복원 시 기존 장부 운용 데이터는 백업 파일 내용으로 교체되지만, 사용자 계정과 세션, 관리 로그는 유지됩니다.

포맷 상세:

- [CSV 백업 포맷](docs/csv-backup.md)

## 문서

- [API 명세](docs/api.md)
- [DB 명세](docs/database.md)
- [CSV 백업 포맷](docs/csv-backup.md)
- [실행 방법](docs/runbook.md)
- [아키텍처](docs/architecture.md)
- [테스트 절차](docs/test-plan.md)

## API 호출 예시

```bash
curl http://localhost:18080/health
curl http://localhost:18080/api/month/current/summary
curl http://localhost:18080/api/entries/current
curl http://localhost:18080/api/month/current/panels
curl http://localhost:18080/api/share/claim
curl http://localhost:18080/api/share/settlement
curl -O http://localhost:18080/api/backups/csv
```

로그인이 필요한 API는 브라우저 세션 또는 `Authorization: Bearer ...` 헤더가 필요합니다.

## Docker 데이터

- `data/`: SQLite DB 저장
- 컨테이너 내부 DB 경로: `/app/data/money-note.sqlite3`
- 호스트 기준 DB 경로: `data/money-note.sqlite3`
