# T6.6F-B01 독립 검증 자료

대상은 `f4ae582b548a5a445ce72c1d1a0d8543836044f3`이다. 제품 수정이나 Phase B 후속 campaign을
수행하지 않는다. `inventory.json`은 최초 refs/원격/tree, 교정 inventory, 원 세 assertions와
제품·역사 자료의 SHA를 기록한다. 판정은 최종 독립 보고서와 완료된 실행 결과를 기준으로 한다.

## 독립성

`test_independent.py`는 기존 B01 네 테스트를 호출하지 않는다. 원 backend transfer template의
합성 SQL seed를 재사용하되 매 사례의 새 DB로 backup하고 backup connection을 명시 close한다.
HTTP는 실제 `create_app()` handler와 실제 auth/SQLite repository를 쓴다. 별도 raw SQLite
connection으로 observations/pins/current/object·financial digest/integrity/FK를 검사한다.

외부 실제 writer가 잠금을 가진 동안 5초 요청 다섯 개의 native `BEGIN IMMEDIATE` 진입을
trace callback/Event로 확인한다. 1초 probe의 실제 BUSY 응답이 반환돼야 writer를 해제한다.
임의 sleep, 성공을 위한 status 변환, quota 확대, product timeout 변경은 없다.
인증 변경·취소·COMMIT 전후 실제 SQL 오류·A/B source identity·fixture 순서도 별도 검사한다.

`observer.py`는 새 독립 delegate다. SQL·반환·예외·timeout·순서를 바꾸지 않고 execute
호출 종류와 connection별 boundary/close/HTTP response를 기록한다. SQL parameters나 credential은
저장하지 않는다. execute/SELECT 호출 수는 VM instruction·read rows·disk I/O가 아니다.
permit snapshot뿐 아니라 실제 capacity만큼 acquire하고 하나 초과를 거부하는지도 검사한다.
FD는 `/proc/self/fd`에서 해당 DB와 WAL/SHM, 삭제된 같은 경로까지 구분한다.

`repeat.py`는 원 quota 함수의 유한 반복이다. 기준은 `git show c479a379:...`의 exact bytes를
새 `/tmp` file로만 복사한다. checkout/reset·원 test 수정·assertion 완화는 하지 않는다.
반복 plugin은 같은 독립 observer를 적용한다. 원 fixture의 plain SQLite context가 native
close와 같지 않다는 점 때문에 call 직후/fixture teardown 후/GC 후 FD를 따로 기록한다.
GC 진단은 원 assertion 실행이 끝난 뒤다. GC 전 잔류를 0으로 덮어쓰지 않는다.

`http_quota_test.dart`는 기존 실제 TLS server/harness를 사용하여 4 lease + 429를 검사한다.
같은 limit=1 IOClient의 실제 Flutter E2가 세 번 quota 거부 후, lease release 뒤 완전한
C1/hash 검증 취득에 성공하는지 확인한다. 별도 client SQLite bytes를 backend oracle와 비교한다.
E3 accepted pointer나 E4 설치는 이 새 smoke가 수행하지 않는다.

## 재현

아래 output은 매 실행에 새 경로를 사용한다.

```bash
cd /home/hjkerman/codex/money-note
B01_INDEPENDENT_OUTPUT=/tmp/mn-b01-new/cases .venv/bin/python -m pytest -q docs/benchmarks/t66f-b01-independent/test_independent.py --junitxml=/tmp/mn-b01-new/independent.xml
.venv/bin/python docs/benchmarks/t66f-b01-independent/repeat.py /tmp/mn-b01-new/repetition
.venv/bin/python docs/benchmarks/t66f-b01-independent/repeat.py /tmp/mn-b01-new/teardown --corrected-only --runs 1
cd mobile
flutter test --no-pub --machine --name '^FB(01|13|14) |^I10 ' --dart-define=F_PHASE_B_OUTPUT=/tmp/mn-b01-new/flutter-existing.json --dart-define=B01_HTTP_OUTPUT=/tmp/mn-b01-new/flutter-quota.json ../docs/benchmarks/t66f-phase-b/integration_test.dart ../docs/benchmarks/t66f-b01-independent/http_quota_test.dart
cd ../backend
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-b01-new/full-1.xml
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-b01-new/full-2.xml
```

full backend는 기존 `backend` cwd workflow 명령으로 새 process·자가 소유 fixtures에서 두 번
순차 실행한다. JUnit에는 main tests와 subtests가 함께 있으므로 terminal summary와 대조한다.
원 process의 실제 wait exit를 JSON에 보존하며 만료된 tool session의 exit를 추측하지 않는다.
새 tests는 docs 아래에 있어 backend 전체 main-test 수에 자동 합산되지 않는다.

과거 두 Phase B 실패의 response body는 없다. 새 관찰을 그 과거 관찰로 바꾸지 않는다.
B01 PASS도 전체 Phase B/F·R1·일반 사용자 activation·배포 완료를 의미하지 않는다.
