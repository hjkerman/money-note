# 보안 운영

Money Note는 1인용이지만 인터넷에 공개되는 금융 기록 서비스다. 사용자가 한 명이라는 사실은 권한 모델을 단순하게 만들 뿐, 로그인·세션·백업 보호를 생략할 근거는 아니다.

## 보호 대상

- 원장, 현금흐름, 청구, 가족카드와 카드 결제 상태
- 사용자 비밀번호와 로그인 세션
- 가족 공유 PIN과 공유 세션
- Snapshot 및 `pre_restore`
- 본인·가족 카드 끝 4자리와 운영 설정

## 인증 경계

- 웹은 `POST /api/auth/login`이 발급한 `HttpOnly`, `SameSite=Lax` cookie만 사용한다.
- 웹 로그인 응답은 Bearer 토큰을 JSON에 노출하지 않는다.
- 모바일은 `POST /api/auth/mobile-login`이 발급한 장기 Bearer 토큰을 Android 보안 저장소에 보관한다.
- DB에는 세션 토큰 원문이 아니라 SHA-256 해시만 저장한다.
- 본체 비밀번호는 12자 이상이며 PBKDF2-SHA256으로 해시한다.
- 비밀번호 변경과 서버 쉘의 `--replace` 재설정은 기존 본체 세션을 모두 종료한다.
- 공유 PIN은 본체 로그인과 분리된 읽기 전용 세션에만 사용한다. PIN 변경 시 기존 공유 세션을 모두 종료한다.
- 공유 PIN 해시와 기본값 여부는 일반 설정 조회 API 및 Snapshot에서 제외한다.

## 공개 요청 방어

- 로그인 실패: 기본 5회/5분 제한
- 공유 PIN 실패: 기본 10회/10분 제한
- 제한기는 단일 서버 프로세스 메모리에 최대 4,096개 접속자 키만 저장한다. 프로세스 재시작 또는 다중 인스턴스 공유 제한이 필요해지면 DB나 외부 저장소로 옮겨야 한다.
- 브라우저 변경 요청은 허용한 Origin 또는 같은 Origin만 받는다.
- `MONEY_NOTE_CORS_ORIGINS=*`는 기동 시 거부한다.
- 운영 HTTPS Origin을 설정하면 `MONEY_NOTE_COOKIE_SECURE=true`가 아니면 기동하지 않는다.
- 일반 변경 API 본문은 기본 1 MiB, Snapshot restore 본문은 기본 25 MiB를 넘으면 `Content-Length` 유무와 관계없이 `413`으로 거부한다.
- API와 공유 응답은 캐시 금지, 프레임 차단, MIME 추측 차단, referrer 차단 헤더를 사용한다.
- 공유 HTML은 사용자 입력을 HTML escape한 뒤 출력한다.

## 데이터와 컨테이너

- Docker 컨테이너는 비루트 사용자로 실행한다.
- 루트 파일시스템은 읽기 전용이며 `/tmp`만 임시 쓰기를 허용한다.
- DB는 호스트 `data/` volume에만 쓴다.
- APK 디렉터리는 컨테이너에서 읽기 전용이다.
- 컨테이너에 `no-new-privileges`를 적용한다.
- Android 앱은 운영체제 백업을 끈다. 서버 Snapshot이 백업 원본이다.
- Android release 빌드는 평문 HTTP 통신을 거부한다. 로컬 HTTP 개발 주소는 debug 빌드에서만 사용한다.

## Snapshot

- Snapshot은 장부 운용 데이터와 비민감 설정만 포함한다.
- `users`, `auth_sessions`, `share_sessions`, `audit_logs`, 비밀번호 해시, 공유 PIN 해시는 제외한다.
- restore는 manifest 검증, 현재 스키마 정규화, 임시 DB dry-run을 먼저 통과해야 한다.
- 실제 DB를 바꾸기 직전에 mandatory `pre_restore`를 원자적으로 생성하고 다시 검증한다.
- restore 트랜잭션 실패 시 운영 DB 변경을 rollback한다.

## 운영 필수값

```text
MONEY_NOTE_CORS_ORIGINS=https://실제-도메인
MONEY_NOTE_COOKIE_SECURE=true
MONEY_NOTE_TRUST_PROXY_HEADERS=true
```

`MONEY_NOTE_TRUST_PROXY_HEADERS=true`는 백엔드가 Apache/Docker의 사설·loopback 주소에서 온 요청에 한해 마지막 `X-Forwarded-For` 값을 접속자 주소로 사용하게 한다. 백엔드를 인터넷에 직접 노출한다면 `false`로 둔다.

`.env`, SQLite DB, Snapshot, APK, JKS, `key.properties`, 비밀번호와 토큰을 Git에 넣지 않는다.

## 남는 위험

- 네 자리 공유 PIN 자체의 경우의 수는 작다. 실패 제한과 읽기 전용 범위가 피해를 줄이지만 강한 인증은 아니다. 기본값 `0000`은 즉시 바꾼다.
- 모바일 토큰 기본 수명은 10년이다. 휴대폰 분실 시 웹에서 비밀번호를 변경해 모든 본체 세션을 종료한다.
- 현재 MFA와 원격 세션 목록 UI는 없다.
- SQLite와 `pre_restore`가 같은 디스크에 있으므로 디스크 고장은 별도 장치에 내려받은 Snapshot으로 대비한다.
- 루팅된 Android, 탈취된 서버 계정, Apache 설정 오류는 애플리케이션만으로 완전히 방어할 수 없다.

## 배포 후 확인

1. HTTPS 인증서와 리디렉션이 정상인지 확인한다.
2. 로그인 응답 JSON의 `session_token`이 `null`인지 확인한다.
3. browser cookie에 `HttpOnly`, `Secure`, `SameSite=Lax`가 있는지 확인한다.
4. 비로그인 변경 API가 `401`인지 확인한다.
5. 허용하지 않은 Origin의 변경 요청이 `403`인지 확인한다.
6. 기본 공유 PIN 경고가 사라질 때까지 PIN을 변경한다.
7. Snapshot 다운로드와 `pre_restore` 복원을 정기적으로 손검증한다.
