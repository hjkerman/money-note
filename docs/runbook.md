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

인증 관련 설정:

```text
MONEY_NOTE_SESSION_COOKIE_NAME=money_note_session
MONEY_NOTE_SESSION_DAYS=30
MONEY_NOTE_COOKIE_SECURE=false
```

운영에서 HTTPS 뒤에 둘 때는 `MONEY_NOTE_COOKIE_SECURE=true` 사용을 고려한다.

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
- 즉시결제와 수기 할인액 처리는 익월 14일까지 가능하다.
- 자동 배분 기본 한도는 현재 유동성이며, 날짜 오름차순으로 배분한다.
- 현금흐름 입금에 `주 수입`을 표시하면 파산심사위원회의 해당 월 심사 기준으로 사용한다.
- 주 수입이 없으면 `base_next_month_liquidity` 설정값을 기본 심사 기준액으로 사용하며 결제 화면에서 변경할 수 있다.
- 14일 경과 후 미결제 기록이 있으면 실제 카드 결제는 완료된 것으로 의제하고, 사용자가 유동성 현황을 보정한 뒤 `유동성 보정 완료`를 누른다.

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

가장 오래된 미마감 월 기록을 전체 기록으로 넘긴다.

```bash
curl -X POST http://localhost:18080/api/month/current/close \
  -H 'Content-Type: application/json' \
  -d '{"allow_early_close":false}'
```

동작:

- 카드 정기결제, 즉 `entry_kind = planned`인 항목을 제외한 `current` 기록을 `archive`로 복사한다.
- 복사된 기록은 `전체 기록(본인)` export 시 hard data 아래에 append된다.
- 카드 정기결제 항목은 당월 기록에 남는다.
- 현재 달은 매월 27일부터 `allow_early_close=true`로 조기 마감할 수 있다.
- 조기 마감 뒤 같은 달 날짜로 추가한 일반 지출은 `archive`에 바로 저장된다.
- 청구와 타인정산은 월마감과 무관하며, 각 탭의 `일괄 처리 완료`로 현재 전달분을 삭제한다.

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
