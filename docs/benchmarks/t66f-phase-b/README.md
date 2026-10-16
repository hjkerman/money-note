# T6.6F Phase B 독립 검증 자료

대상 제품은 `af9525e20e6df1dd7dfc152d3db79c1eb07925d2`, 시작 감사 commit은
`a7d045f3a73e8b1cd46faf0946251d712a5d6448`이다. 제품 source는 수정하지 않는다.
`coverage.md`는 대규모 회귀 전에 작성한 B0 mapping이다. 최종 결과는 별도 보고서와
수집된 summary/cases를 기준으로 한다. 이 README의 실행 설명은 PASS 주장이 아니다.

## 실제 전송과 oracle

`server.py`는 NEW `RetentionSandbox`와 synthetic token만 생성하고 실제
`isolated_sync.http.create_app()`을 Uvicorn TLS loopback listener에 연결한다.
Flutter `harness.dart`는 실제 `MoneyNoteApiClient`/`IOClient`/`HttpClient`를 사용한다.
자가 서명 인증서 허용은 이 새 loopback host와 해당 임시 port에만 적용된다.
Flutter test binding의 기본 mock HTTP를 이 client 생성 범위에서만 대체한다.
일반 앱의 transport/configuration은 변경하지 않는다.

관측 응답이 manifest다. 실제 D3b 객체 전송은 typed path/offset/length를 포함한 POST다.
D3c는 release/expiry/retention이다. capabilities는 R1 전체 지원을 허위 광고하지 않도록 404다.
stdin pipe는 fixture 변경·clock·barrier·독립 기대값 제어이며 금융 객체 전송 통로가 아니다.

wire observer는 ASGI receive/send에서 실제 request/response 크기, status, 객체 hash와
decoded payload 길이를 기록한다. 금융 비교 oracle은 같은 새 DB의 backend exporter와
`_construct/_prepare`다. 비교용 legacy producer에서만 isolated schema version 및 revision
trigger admission gate를 시험 profile에 맞추고 날짜를 고정한다. 금융 함수·raw 검증·manifest
hash·정렬·presenter는 실제 backend 코드다. 정상 runtime에서 이 profile이 legacy admission을
통과한다고 주장하지 않는다. 판단 문구의 random 선택만 고정한다.

기대 graph는 backend SQL에서 독립 child extractor/C1/SHA로 만든다. 별도 SQLite 연결의
client body bytes와 비교하고, `t66e4-audit/state_oracle.py`의 별도 F(raw)/Patricia/v7/lineage
oracle을 실행한다. 이전 감사 helper 재사용과 새 Phase B 시나리오를 구별한다.

## 작업량 관찰

`measure.py`는 감사 source만 새로 복사한 mobile 프로젝트를 만든다. 실제 sqlite3 connection을
`t66e3-audit/audit_trace.dart` delegate로 감싸 statement/returned row/BLOB bytes/pin I/D/U를 센다.
full verification/recovery/legacy read/lineage 함수 진입은 임시 copy에서만 관찰한다.
제품이 제공하는 work counter를 결과 oracle로 읽지 않는다.

backend는 자기 sandbox connection의 실제 SQLite expanded-statement trace를 관찰한다.
literal/hash/BLOB를 `?`로 정규화해 유한한 SQL 빈도 자료를 만든다. SQLite의 trigger 관련
반복 trace를 VM instruction이나 실제 read-row 수로 부르지 않는다. backend source row set
oracle/클라이언트 검증 oracle 비용은 측정 구간 밖이다. 측정 latency는 여러 회귀가 병행한
HOST 값이며 production latency·실기기·median/p95 규모 증명으로 확대하지 않는다.

## 실제 process 종료

`test_backend.py`는 fork child가 capture/finalization/COMMIT barrier에 도착한 뒤 실제
SIGKILL한다. `test_crash.py`는 parent가 소유한 실제 TLS backend를 유지하고 Flutter child의
원 AppState 경로를 종료한다. initial G1 설치 후 parent가 실제 backend G2를 COMMIT한 뒤
child가 다음 요청을 시작한다. 실제 PID/barrier·source/pins/B/pending·fresh process 결과를
JSON에 기록한다. exception injection을 SIGKILL로 세지 않는다. hardware power loss는 미검증이다.

## 재실행

아래 명령은 개발 checkout와 새 `/tmp` 출력 폴더만 사용한다.

```bash
cd /home/hjkerman/codex/money-note/mobile
flutter test --no-pub --machine --dart-define=F_PHASE_B_OUTPUT=/tmp/mn-f-new/integration.json ../docs/benchmarks/t66f-phase-b/integration_test.dart
cd ..
.venv/bin/python docs/benchmarks/t66f-phase-b/measure.py /tmp/mn-f-new/cost
F_BACKEND_OUTPUT=/tmp/mn-f-new/backend .venv/bin/python -m pytest -q docs/benchmarks/t66f-phase-b/test_backend.py
F_CRASH_OUTPUT=/tmp/mn-f-new/crash .venv/bin/python -m pytest -q docs/benchmarks/t66f-phase-b/test_crash.py
F_HTTP_OUTPUT=/tmp/mn-f-new/http .venv/bin/python -m pytest -q docs/benchmarks/t66f-phase-b/test_http_concurrency.py
F_GENERATION_OUTPUT=/tmp/mn-f-new/generation .venv/bin/python -m pytest -q docs/benchmarks/t66f-phase-b/test_generation_cost.py
```

환경 변수의 정확한 이름은 각 test의 `OUT` 정의도 함께 확인한다. 이번 완료 출력은
`/tmp/mn-t66f-phase-b`였으며 source/configuration이나 production 경로로 바꾸지 않는다.

전체 회귀는 아래와 같이 별도 실행한다. 결과는 exit와 machine/JUnit를 함께 확인한다.

```bash
cd /home/hjkerman/codex/money-note/backend
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-f-new/backend-full.xml
cd ../mobile
flutter test --no-pub --machine --concurrency=2
flutter analyze --no-pub
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=https://phase-b.invalid
```

APK는 build만 하고 설치·배포하지 않는다. `collect.py`는 모든 최종 실행의 종료 guard를
확인한 뒤 이 감사 폴더에 bounded evidence/summary/cases를 만든다. 새 49개와 원 회귀를
구분하며 전체 backend 실패 두 번과 첫 Flutter 실패를 지우지 않는다.

`cost_test.dart`는 observer가 삽입된 임시 copy에서만 실행한다. 정상 mobile source에는
`audit_trace.dart`를 추가하지 않는다. `fresh_test.dart`/`crash_child_test.dart`는 위 parent가
만든 입력을 필요로 하는 fixture이며 독립 standalone suite가 아니다.

부정 manifest를 파싱하지 못하면 client는 observation ID를 모를 수 있다. 독립 사례 사이에는
규범의 실제 server TTL로 lease를 만료시켜 quota를 분리한다. TCP 검사는 object header를
거부하여 E2가 lease DELETE도 수행하도록 한다. DELETE 204 이후 idle pooled socket 한 개와
누적 outstanding response를 구분하며 같은 limit=1 client의 후속 성공도 확인한다.

역사적 FAIL 보고서·원 반례 assertion·원 benchmark는 수정하지 않는다. R1/production/배포/설치
gate는 이 harness가 열지 않는다.
