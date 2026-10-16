# T6.6F-B01 재현·증거

원 Phase B의 backend concurrency gate만 조사한다. 기존 보고서·원 assertions·제품 코드는
보존한다. 분류는 **TEST HARNESS**이며 quota 시험에만 기존 허용 budget 5,000ms를 명시한다.
제품의 기본 busy timeout 1,000ms, HTTP 503/retry_same, quota 4와 pins·permit 계약은 불변이다.
이는 독립 B01 PASS 또는 Phase B 완료 선언이 아니다.

## 분리된 재현

`repeat.py --baseline`은 `git show c479a379…:backend/tests/test_isolated_sync_transfer.py`의
exact bytes를 새 `/tmp` output 안에만 복사한다. 현재 checkout·Git history·제품을 되돌리지 않는다.
원 시험·fixture·세 assertions를 수정하지 않는다. `--baseline` 없는 실행은 현재 교정 setup이다.
반복 횟수는 1–16으로 제한하며 campaign 자체의 exit 0은 각 사례 PASS 판정이 아니다.
각 실제 pytest exit/JUnit/status/body/SQL timeline을 개별 보존한다.

```bash
cd /home/hjkerman/codex/money-note
.venv/bin/python docs/benchmarks/t66f-b01/repeat.py /tmp/mn-b01-new/before --baseline --runs 8
.venv/bin/python docs/benchmarks/t66f-b01/repeat.py /tmp/mn-b01-new/before-light --baseline --light --runs 4
.venv/bin/python docs/benchmarks/t66f-b01/repeat.py /tmp/mn-b01-new/after --runs 8
B01_OUTPUT=/tmp/mn-b01-new/targeted .venv/bin/python -m pytest -q \
  docs/benchmarks/t66f-b01/test_b01.py --junitxml=/tmp/mn-b01-new/targeted-final.xml
cd backend
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-b01-new/backend-after-1.xml \
  > /tmp/mn-b01-new/backend-after-1.log 2>&1
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-b01-new/backend-after-2.xml \
  > /tmp/mn-b01-new/backend-after-2.log 2>&1
```

완료 gate에서는 두 전체 run 모두 종료한 PASS와 original 3-assertion byte equality를 요구한다.
원 baseline 재현의 FAIL은 지우지 않는다. 첫 조사 full run은 옛 시험 함수가 이미 수집된 뒤
source 파일이 바뀌어 pytest의 표시 source가 새 파일을 읽었다. 그 run의 old bytecode 행 번호
497와 새 표시 `barrier = Barrier(5)`를 혼동하지 않는다. 원 로그는 그대로 보존하며, 별도
baseline copy campaign은 이 표시 모호성이 없는 재현이다. 제품 구현은 모든 실행에서 동일하다.

## 비침습 observer

`forensics.py`는 opt-in pytest plugin이다. quota 시험의 call 구간에만 적용하며 원 assertions,
SQL timeout·query ordering·transaction·HTTP 반환을 바꾸지 않는다. connection별 BEGIN 전후/SQLite
COMMIT trace/close, request UUID/phase/thread/PID, SQL statement 종류/횟수, HTTP status/body/headers,
별도 연결의 observations/pins/FK/integrity와 DB device/inode를 관찰한다. SQL parameters·auth headers·
credential은 기록하지 않는다. Device/inode는 진단 정보이지 D3c actual-open FD fence 대체물이 아니다.
counter는 execute 호출 수이며 VM instruction·read row·물리 disk I/O가 아니다.
`--light`는 execute/connect/commit/close wrapper를 전부 생략하고 응답과 원 예외 context chain의
frame 정보만 관찰한다. SQL values·locals는 기록하지 않는다. 상세 observer가 없는 원 기준
copy에서도 실제 SQLITE_BUSY를 확인하여 계측 overhead의 영향을 구분한다.

첫 observer는 closed handle의 `in_transaction` 조회로 이중 close semantics를 바꿨다. 이를
고친 뒤 얻은 trace만 원 실패 원인 증거로 사용한다. 그 이전 500 실패는 계측 오류로 분리한다.

## 결정적 새 사례

`test_b01.py`의 네 사례는 실제 ASGI/SQLite/서버 auth fixture를 사용한다.

- 기본 budget과 synthetic quota budget을 같은 외부 writer에 대기시킨다. 기본 요청의 실제 503을
  확인한 뒤 writer를 해제한다. 긴 budget 요청의 201 및 같은 nonce retry 201→200을 검사한다.
- 두 disposable lifespan에서 busy/invalid 이후 정상 요청, durable state 불변 및 모든 permit 반환을 검사한다.
- Git 기준 원 세 assertion과 현재 assertion의 byte equality 및 기본/최대 budget을 검사한다.

새 임의 sleep·retry·status 허용값 추가는 없다. 기존 실제 TLS concurrency suite의 명시 protocol
backoff는 그대로 재실행하며 B01 교정으로 새로 추가한 retry가 아니다.

## 관련 회귀와 상호운용

```bash
cd /home/hjkerman/codex/money-note/backend
../.venv/bin/python -m pytest -q \
  tests/test_isolated_sync_observation.py tests/test_isolated_sync_transfer.py \
  tests/test_isolated_sync_transfer_failures.py tests/test_isolated_sync_transfer_cancellation.py \
  tests/test_isolated_sync_retention_ownership.py \
  -k 'concurrent or busy or identity or cancel or ownership or quota'
cd ..
F_HTTP_OUTPUT=/tmp/mn-b01-new/real-http .venv/bin/python -m pytest -q \
  docs/benchmarks/t66f-phase-b/test_http_concurrency.py
cd mobile
flutter test --no-pub --machine --name '^FB(01|13|14) ' \
  --dart-define=F_PHASE_B_OUTPUT=/tmp/mn-b01-new/flutter-http.json \
  ../docs/benchmarks/t66f-phase-b/integration_test.dart
```

제품 backend/Flutter/engine bytes가 불변인 한정 harness 수정이므로 full Flutter 수를 새로
주장하지 않는다. 선택한 실제 TLS Flutter 세 사례와 전체 backend를 새로 실행한다.
full Flutter 1,503/2 SKIP는 원 Phase B의 보존된 과거 증거로만 구분한다.

## 집계·제한

`collect.py <실제 output> --require-complete`는 stdout으로 집계한다. repo artifact를 자동
overwrite하지 않는다. original before/after/quiet campaign과 full1/full2·targeted·related·TLS·Flutter
파일명이 collector와 일치해야 한다. 선택한 baseline copies와 실패 trace는 별도 evidence로 보존한다.
raw DB·credentials·APK·성공 로그 전체를 Git에 넣지 않는다.

유한 반복 PASS를 모든 scheduling의 증명으로 확대하지 않는다. 두 과거 실패의 body/lock trace는
당시 없었으므로 새 재현으로 덮어쓰지 않는다. Phase B §34의 scaling/compression/실기기/R1와
전체 cross-layer matrix·storage cost·DB identity coverage 의무는 별도 후속 감사에 남는다.
R1 CLOSED, production activation·deploy·APK 설치·서비스 restart 없음.

## 확정 artifact

- `summary.json`: 두 full JUnit/pytest summary, 모든 반복 cohort와 order·실제 HTTP·보존 SHA.
- `baseline-sql-failure.json`, `baseline-light-failure.json`: 원 exact-copy의 실제 실패 body와 SQL/예외 근거.
- `corrected-sql-success.json`: 최종 정상 결과와 actual SQL/connection/pin 상태.
- `deterministic.json`, `real-http.json`: writer release·default busy·permit 및 실제 TLS 증거.
- `flutter-interoperability.json`: 큰 원 oracle의 digest와 세 현재 smoke의 identity·wire 계수.
- `source-format.json`, `source-hashes.json`: full collection/최종 AST 동등성과 실제 snapshot.
- `checks.json`, `process-status.json`: 실제 정적 검사 exit와 재조회하지 못한 full exec exit의 명시적 구분.
- `diagnostic-history.json`: observer 자체의 초기 실패를 제품 finding/재현 수에서 분리한 이력.

최종 교정 반복 12/12, 신규 targeted 4/4, 관련 family 90/90, 순서 변형 3+3,
실제 TLS 2/2 및 Flutter HTTP 3/3 PASS다. full backend 두 번 모두
1,315 tests + 1,540 subtests PASS다. 구현측 RESOLVED이며 독립 B01 validation은 별도다.
