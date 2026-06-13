# money-note

개인 신용카드 생활에 맞춘 1인용 가계부 웹 앱입니다.

서버 DB가 원본 데이터입니다. 과거의 스프레드시트 운용 방식에서 출발했지만, 현재 앱은 웹 UI와 API를 중심으로 동작합니다.

## 현재 계획

- 백엔드: FastAPI + SQLite
- 배포: Ubuntu 24.04 홈서버에서 Docker Compose와 Apache reverse proxy로 실행
- 웹 프론트엔드: Vite + React + TypeScript
- 운영 모드: 웹 프론트엔드와 백엔드는 오류 수정이 아닌 한 기능 변경을 중단
- 데스크탑/모바일 앱: 현행 웹/API를 안정된 기준선으로 삼고, 별도 클라이언트에서 검토

## 운영 안정화 원칙

현재 웹 프론트엔드와 백엔드는 실사용 후보 기준선으로 본다.

- 오류, 보안 문제, 데이터 손상 위험, 배포 실패를 고치는 변경은 허용한다.
- 단순 취향 변경, 새 기능, 대규모 구조 변경은 기본적으로 보류한다.
- 새 클라이언트가 필요하면 기존 API와 DB 의미를 흔들지 않는 방향을 먼저 검토한다.
- 운영 DB와 snapshot 백업을 우선 보호한다.

## 주요 기능

- 당월 지출: 사용일, 사용처, 사용항목, 금액, 분류를 관리
- 카드 정기결제: 결제일순 정렬, 확인 시 당월 지출로 편입
- 청구/가족카드: 가족에게 보여줄 읽기 전용 공유 화면과 일괄 처리 완료
- 동결: 살지 말지 보류한 임시 항목. 실제 지출은 직접 기록하고 동결 항목은 삭제
- 현금흐름: 현금 입출금 기록을 유동성 현황에 반영
- 카드 할인: 월별 혜택 여부를 설정하고, 혜택 적용 달에는 카드 지출에 기본 1.2% 할인을 반영. 개별 항목은 할인 제외 가능
- 이번달 결제: 직전월 카드 사용분을 날짜순으로 자동 배분하거나 직접 선택해 일부 즉시결제
- 카드 사용내역 이월: 결제 화면에서 항목을 일부결제하거나 다음 달 장부 맨 앞으로 이월
- 수동 월마감: 새 달 기록을 먼저 입력해도 가장 오래된 미마감 월 하나만 전체 기록으로 이동
- 조기 월마감: 매월 27일부터 명시 확인 후 현재 달을 닫을 수 있고, 이후 같은 달 지출은 전체 기록에 바로 추가
- 전월 매입 지연 보정: 카드사가 뒤늦게 올린 직전월 사용내역을 이번달 결제 대상에 추가
- 관리 로그: 변경 API의 사용자·경로·결과를 조회하고 필요할 때 전체 초기화
- Snapshot 백업/복원: 장부 운용 데이터 전체와 비민감 운영 설정을 SHA-256 manifest가 포함된 JSON snapshot으로 보관하고 복원
- 위험 초기화: 현재 비밀번호 확인 후 장부 운용 데이터만 전체 삭제
- 판단 모듈: 분류 기준과 문구를 백엔드 `judgment` 모듈로 분리하고 프론트는 서버 판단 결과를 표시
- 가족 공유 PIN: 청구/가족카드 공유 링크를 기본 PIN `0000`으로 잠그고, 변경 가능한 네 자리 PIN과 장기 세션 적용

## 빠른 시작

처음 배포하는 경우에는 [실행 방법](docs/runbook.md)의 `홈서버 첫 배포 절차`를 먼저 읽는 것을 권장합니다.

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

생성된 `frontend/dist/`를 홈서버의 `/var/www/...` 아래에 배치하고, Apache가 `/api/`와 `/share/`를 백엔드 컨테이너로 넘기게 합니다.

## 문서

- [API 명세](docs/api.md)
- [DB 명세](docs/database.md)
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
curl http://localhost:18080/api/share/family_card
curl -OJ http://localhost:18080/api/admin/snapshot
```

로그인이 필요한 API는 브라우저 세션 또는 `Authorization: Bearer ...` 헤더가 필요합니다.

## Docker 데이터

- `data/`: SQLite DB 저장
- 컨테이너 내부 DB 경로: `/app/data/money-note.sqlite3`
- 호스트 기준 DB 경로: `data/money-note.sqlite3`
