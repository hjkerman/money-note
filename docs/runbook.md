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
- 즉시결제는 익월 14일까지 가능하다.
- 카드 할인은 월 정책이 혜택 없음이 아닌 경우 기본 1.2%로 계산한다. 개별 항목의 `할인 제외`를 누르면 해당 항목 할인액은 0원이다.
- 자동 배분 기본 한도는 현재 유동성이며, 날짜 오름차순으로 배분한다.
- 하이패스/통행료가 여러 건이면 결제 화면에서는 하나의 통합 행으로 보인다. 결제나 이월을 누르면 내부 원본 항목에 순서대로 반영된다.
- 결제 화면에서 장부 행을 삭제할 수 있다. 삭제하면 해당 행의 즉시결제, 할인, 이월 참조도 함께 정리된다.
- 청구 탭의 하이패스/통행료는 집에 청구하는 별도 패널 데이터이므로 결제 화면의 통합 행에 섞이지 않는다.
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

## Snapshot 백업과 복원

서버 DB가 단일 원본이다.

Snapshot은 장부 운용 데이터 전체와 앱 운영 설정을 담는 JSON 백업 파일이다. 원본 SQLite DB 파일을 그대로 내려받는 방식이 아니며, 사용자 계정과 세션, 관리 로그, 비밀번호/해시, 공유 PIN 해시는 포함하지 않는다.

내보내기:

```bash
curl -OJ -b /tmp/money-note-cookie.txt \
  http://localhost:18080/api/admin/snapshot
```

응답 파일 확장자는 `.money-note-snapshot.json`이며, `schema_version`, `exported_at`, `range`, `manifest`, `data`를 포함한다.

현재 snapshot 형식은 `schema_version = 2`다.

`manifest`는 canonical JSON 기준 SHA-256 무결성 정보를 담는다. `manifest` 자기 자신은 hash 대상에서 제외하며, `data` 전체 hash와 테이블별 컬럼 목록, row count, table hash를 기록한다.

복원은 위험 작업이다. 현재 비밀번호를 다시 확인하며, 장부 운용 데이터와 비민감 운영 설정이 snapshot 내용으로 교체된다. 사용자 계정, 본체 로그인 세션, 가족 공유 세션, 관리 로그는 유지된다.

복원 안전장치:

- 운영 DB를 수정하기 전에 snapshot 구조와 manifest를 검증한다.
- 운영 DB를 수정하기 전에 동일한 삽입 경로로 임시 DB dry-run restore를 수행한다.
- dry-run에서 외래키 오류가 발견되면 복원을 중단한다.
- 실제 restore 직전 현재 운영 DB를 `data/snapshot-backups/pre_restore-...money-note-snapshot.json` 파일로 반드시 저장한다.
- `pre_restore` 파일 생성, JSON parse, manifest 검증 중 하나라도 실패하면 복원을 중단한다.
- 실제 restore 도중 예외가 발생하면 트랜잭션 rollback으로 기존 운영 DB를 보존한다.

웹에서는 `설정 -> 위험 작업 영역 -> snapshot 복원`에서 파일을 선택하고 현재 비밀번호를 입력한 뒤 실행한다.

복원 결과가 잘못되었다면 같은 설정 모달의 `복원 전 백업` 섹션을 사용한다.

절차:

1. `목록 조회`를 누른다.
2. restore 직전 시각의 `pre_restore` 항목을 확인한다.
3. 필요하면 `다운로드`로 파일을 별도 보관한다.
4. 현재 비밀번호를 입력한다.
5. `되돌리기`를 누른다.

`되돌리기`도 일반 restore와 동일한 검증과 dry-run을 거치며, 되돌리기 직전 상태 역시 새 `pre_restore`로 저장된다.

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

API로 복원 전 백업 다운로드:

```bash
curl -OJ -b /tmp/money-note-cookie.txt \
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

브라우저 웹앱은 로컬 파일시스템을 안정적으로 제어할 수 없으므로 `cur_backup`/`prev_backup` 회전을 구현하지 않는다.

기본 정책:

- 전체 snapshot을 저장한다.
- 각 기기는 최소 `cur_backup.money-note-snapshot.json`과 `prev_backup.money-note-snapshot.json` 두 벌을 유지한다.
- 새 snapshot은 바로 `cur_backup`을 덮어쓰지 않는다.
- 먼저 임시 파일로 저장한다.
- 저장한 파일을 다시 JSON parse한다.
- `schema_version`이 지원 범위인지 확인한다.
- manifest를 재계산해 snapshot에 기록된 값과 일치하는지 확인한다.
- 검증이 끝난 뒤 기존 `cur_backup`을 `prev_backup`으로 atomic rename한다.
- 마지막으로 새 임시 파일을 `cur_backup`으로 atomic rename한다.
- 검증 실패 파일은 `cur_backup`이나 `prev_backup`을 덮어쓸 수 없고, 필요하면 `quarantine/` 아래에 격리한다.

이 정책은 네트워크 중단, 앱 강제 종료, 깨진 JSON, 잘못된 최신 상태가 곧바로 유일한 백업을 덮어쓰는 사고를 줄이기 위한 최소 안전장치다.

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
