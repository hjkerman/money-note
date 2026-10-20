# 논리 비용의 정의와 계측 중단 경계

제품 source를 변경하지 않았다. 현재 full-grid의 세 byte counter는 미완료다.
아래 정의·부분 calibration과 전체 D→E 증명의 완료 여부를 구분한다.

## 집계 단위

기본 단위는 실제 operation invocation이다. 같은 원문을 두 번 처리하면 두 번 센다.
소유 operation에 한 번 귀속하고 호출 layer의 inclusive 합계를 다시 더하지 않는다.
상위 구간은 cold acquisition, identical, card D=1, cash D=1, restart/fallback,
E4 healthy read, explicit legacy materialization으로 구분한다. 여러 관측에 걸친 cold는
같은 acquisition의 실제 retry를 포함한다. HTTP request 단위와 generation 단위는 별도다.

- `HASH_INPUT_BYTES`: 실제 cryptographic sink에 전달한 byte 길이의 합.
  protocol object는 domain prefix+NUL+원문이며 row/fact-key/view/checksum 목적을 분리한다.
  같은 bytes의 재hash와 chunked update를 모두 센다. hashing을 생략한 cache hit는 0이다.
  auth/session hash를 관측한다면 별도 purpose로 기록하고 credential 값은 저장하지 않는다.
- `VALIDATION_INPUT_BYTES`: 지정한 byte-consuming validation 경계의 실제 입력 길이 합이다.
  canonical decoder, raw/typed byte admission, integrity hash 등을 서로 다른 subcounter로 둔다.
  structured row/fact 검사는 실제 byte 입력이 없는 한 record visits로 따로 센다.
  편의상 재인코딩한 길이를 실제 방문 byte라고 부르지 않는다. 실패 시 submitted와
  확정적으로 완전히 처리한 bytes를 분리한다. 실패 위치 이전 prefix 길이를 추측하지 않는다.
- `PERSISTENCE_LOGICAL_WRITE_BYTES`: 실제 persistence API에 제출한 payload bytes다.
  BLOB은 길이, TEXT는 해당 API의 실제 encoding으로 제출한 길이다. SQL text·literal·scalar
  argument·selector·metadata·object content를 분리한다. 완전한 계측은 implicit trigger writes,
  UPDATE/DELETE, prepared statements, transaction outcome까지 포함해야 한다.
  이 감사의 좁은 INSERT 관측기는 그 전체를 구현하지 않는다.

hash는 validation의 일부일 수 있다. byte parser와 hash가 같은 원문을 처리해도 두 operation의
실제 비용이다. hash/validation/write는 서로 겹치는 입력을 가지므로 하나의 총 byte로 합하지 않는다.
정의가 정해진 세 phase subcounter도 inclusive와 exclusive를 동시에 더하지 않는다.
이번 primary validation byte 경계는 **hashing을 제외한 UTF-8/JSON/C1 byte admission**이다.
reference traversal·typed/raw/global facts·receipt의 semantic 검사는 각각 별도 operation/record
visits로 구분하고, byte 입력을 실제 받는 상위 verifier의 inclusive 입력은 하위 decoder 합에
다시 더하지 않는다. 따라서 소형 decoder 수치만으로 semantic validation 전체 비용을 입증하지
못한다. hash를 포함한 integrity-validation inclusive view를 만들더라도 별도 열로만 제시한다.

## 새로 관측한 범위

`counters.py`는 `canonical.hashlib`를 stdlib SHA delegate로 바꾸고 `_parse_json`을 감싼다.
production `Object`, `Store.put/get`와 원 exception을 그대로 사용한다. product 파일/의존성
교체·source copy가 아니다. oracle는 별도 stdlib SHA와 literal byte 길이·직접 SQLite SELECT다.

hash는 constructor 초기 bytes와 실제 update 입력을 센다. decoder는 operation에 제출한 길이와
정상 반환한 full UTF-8/JSON 입력 길이를 분리한다. C1 equality 실패 전 정상 JSON parse는
completed로 기록한다. malformed UTF-8의 trailing bytes까지 처리됐다고 주장하지 않는다.
typed/raw/facts/receipt 모든 단계의 총 validation byte를 이 값으로 대신할 수 없다.

`InsertConnection`은 정확한 positional `INSERT [OR IGNORE] INTO ... VALUES(?,...)`만
지원한다. 실제 BLOB/TEXT bind 입력, effective row count, explicit COMMIT/ROLLBACK을 나눈다.
중복 IGNORE의 attempted payload는 세지만 durable addition은 0이다. 숫자/NULL은 별도 개수이며
임의 8B 가중치로 bytes를 만들지 않는다. UPDATE/DELETE/다른 DML은 `unobserved_dml`이다.
trigger 내부·implicit close rollback·SQL literal의 bytes는 포함하지 않는다.
따라서 이 wrapper는 전층 logical-write oracle가 아니다.

## calibration

16개 pytest는 알려진 원문 길이와 독립 digest/SQL 상태를 oracle로 쓴다.
단일/반복 hash, chunked update, cached Ref 재사용, 반복 body decode, 성공/실패 validation,
counter 간 구별, 4-thread/64회 호출, signed64 초과 계수, exception 뒤 원 함수 복구,
UTF-8 TEXT/BLOB INSERT, attempted/effective IGNORE, rollback/retry, metadata/pin TEXT,
미관측 UPDATE의 명시, 실제 production Store 경계를 검증한다.
`calibration.xml`의 실제 결과와 `backend-small-observed.json`이 증거다.
metadata/pin TEXT의 길이는 object content write가 아니다.

Python int는 임의 정밀도로 계수하며 saturating counter를 사용하지 않는다. 정수 덧셈은 lock으로
보호하고 wrapper 적용/복구는 context manager다. native SQLite connection은 closing으로 닫는다.
실제 동시 HTTP 요청 전체를 계측한 결과로 확대하지 않는다. calibration evidence의
executed_cases는 실행 목록이며 PASS oracle는 JUnit 결과다.

## 관측 seam의 조사와 stop rule

|실제 위치|현재 관측 가능성|판정|
|---|---|---|
|backend `canonical.py:131,152,161`, `Object:202`, Store/connection injection|test-only monkeypatch/delegate 가능|소형 경계 calibration PASS, 전체 backend grid는 새로 실행하지 않음|
|D3 `transfer.py`, 기존 ASGI observer|request/response entity와 typed-path 로딩 관찰 가능|기존 raw trace 재집계. hash sink bytes로 바꾸지 않음|
|Dart `c1.dart:115,134,152,172`|직접 top-level decode·const `sha256` 호출; observer/Hash factory 인자 없음|현재 audit-only 경계에서 전체 hash/validation bytes 미관측|
|`object.dart:113,115`와 E3 verification/Patricia 호출|같은 정적 함수를 library 내부에서 직접 호출|test 외부 wrapper로 모든 재호출·실패·reuse를 가로챌 수 없음|
|`store.dart:125`, private `_db` 및 part 파일|const sqlite3 직접 open. `StoreFault(String)`는 bind 값/SQL payload를 전달하지 않음|fault 횟수·read-only DB diff만으로 모든 attempted writes를 복원할 수 없음|
|E4 `adapters.dart:145`의 legacy bundleHash|legacy hash 경계도 C1 object hash와 별개|허용된 materialization에서 추가 독립 관측 필요|

SDK 확인: crypto 3.0.7의 `src/sha256.dart:16`은 `const Hash sha256`, sqlite3 3.7.0의
`src/ffi/api.dart:12`는 `const Sqlite3 sqlite3`다. package source를 수정하지 않았다.
공개 SQLite update hook은 BLOB payload·IGNORE attempt·rollback write 총량을 제공하지 않는다.
private native connection에 trace callback을 외부에서 연결하는 기존 지원 seam도 없다.
기존 `audit_trace.dart`는 production tree에 없고 과거 임시 source-copy 계측에 사용됐다.
그 당시 동등성 proof의 범위는 유지하되 현재 production 실행의 새 hash counter로 전용하지 않는다.
VM debugger의 매호출 pause/SDK patch·FFI interposition은 검증된 bounded aggregate seam이 아니며
이번 캠페인에서 생산 경로와 동등하다고 입증한 계측기도 아니다. 그것을 가능하다고 가정해
대형 실행을 시작하지 않았다. 모든 가능한 tracer의 수학적 불가능성을 주장하지 않는다.

**사용자 §14 stop rule을 적용했다.** Dart 전체 byte 측정과 이에 의존하는 C2 비용 grid를 멈췄다.
100k cold 재실행으로 이 관측 공백이 해소되지 않는다. backend 소형 calibration과 과거 raw
evidence 재대조·전체 회귀·contract reconciliation은 계속 수행했다.

## 별도 구현 세션의 최소 제안

1. `mobile/lib/src/segmented/c1.dart`에 기본 비활성 test observer/주입 가능한 hash·decode sink를
   둔다. prefix/실제 add bytes·decode 결과를 목적별 aggregate로 관찰하며 per-object log는 없다.
2. `mobile/lib/src/segmented/store.dart`의 `open`에 기본 sqlite3를 유지하는 test-only Database
   factory seam을 둔다. private `_db`와 모든 part 파일의 prepare/bind/execute/transaction을
   실제 delegate로 관찰한다. SQL constants·trigger writes·attempted/effective/rollback을
   별도 보정한다. fault callback을 SQL 값 로깅 기능으로 재해석하지 않는다.
3. typed/raw/closure의 structured validation은 bytes와 record visits의 경계를 먼저 확정한다.
   `object.dart` 및 `verification.dart`에 추가 hook이 필요한지는 그 정의 뒤 최소화한다.
   E4 허용 legacy hashing은 `authoritative_bundle_validation.dart:151`의 별도 bundleHash 경계가 필요하다.

이 제안은 적용하지 않았다. no-op observer는 동작 중립을 목표로 하지만 timing·allocation·
callback 재진입·source identity 변화가 있으므로 자동으로 중립이라고 인증할 수 없다.
특히 final fence→COMMIT 사이 observer callback/await는 금지다. source SHA guard와 backend
engine manifest 포함 여부를 실제로 재검토해야 한다. 기존 lock을 느슨하게 만들지 않고 exact
reviewed extension으로 처리하는 별도 승인이 필요하다. 변경된 소스에는 C1/negative/authority,
E1 transaction/I25/E4/frozen/source guards와 full backend/Flutter 회귀를 다시 수행해야 한다.
별도 구현을 승인한 뒤 독립 counter calibration·고정 H/D full grid 검증으로 돌아온다.

현 `backend/isolated_sync/observation.py:76`의 engine source 목록은 backend `app/**/*.py`,
`isolated_sync/*.py`, judgment message YAML이다. 제안한 **모바일만의** hook은 이 backend
engine artifact 입력이 아니므로 그 변경만으로 새 backend engine hash를 발급할 근거는 없다.
반면 `segmented_adapter_isolation_test.dart`는 `c1.dart`를 역사적 protected-source SHA와 직접
대조하므로 hook 추가 시 그 guard가 정상적으로 실패한다. 원 protected 파일을 고쳐 덮는 방식이
아닌 별도 정확한 변경 검토가 필요하다. backend source hook까지 범위를 늘리면 engine 입력과
현재 exact allow-list의 추가 검토가 생긴다. 이 감사에서는 어느 것도 변경하지 않았다.

## overhead·환경

현재 Python 관측기는 operation당 bounded aggregate 덧셈과 lock만 추가한다. 원문 보관·객체별
동기 log는 없고 counter key 수는 fixture에 대해 고정이다. `overhead.json`은 실제 Object
constructor 1000회, 3 warmup+20 measured paired/alternating samples의 perf_counter_ns다.
이 비교는 SHA+decoder wrapper의 HOST overhead이며 SQL·Flutter·event loop·실기기 overhead의
상한이 아니다. heavy observer latency를 일반 앱 성능으로 보고하지 않는다. 미래 Dart 관측기의
메모리·event-loop·timing 영향은 아직 측정하지 않았고 새 cost run 전에 검증해야 한다.
