# T6.6E4 T01/T02/T03 — targeted completion 증거

이 디렉터리는 이전 미완료 구현과 `../t66e4/` 비용 자료를 대체하지 않는다.
원본 BLOCKED/P0 보고서·다섯 진단 파일·3 PASS/2 FAIL 역사적 assertion은 변경하지 않는다.
독립 E4 감사 PASS나 R1 완료, production 활성화를 의미하지 않는다.

## 재현

`mobile/`에서 실제 backend ASGI/폐기용 SQLite를 사용하는 비용 비교를 실행한다.
금융 fixture 자체는 `/tmp`에만 두며 commit하지 않는다.

```bash
flutter test --no-pub --machine \
  --dart-define=E4_COST_OUT=/tmp/mn-e4-frozen-cost.json \
  --dart-define=E4_FIXTURE_OUT=/tmp/mn-e4-native-fixtures.json \
  --plain-name='independent before/full' \
  test/segmented_e4_provenance_test.dart > /tmp/mn-e4-cost.jsonl
```

Repository root에서 기존 독립 E3 SQL observer를 **폐기용 source copy**에 연결한다.
제품 source/실행 DB에 observer나 SQL callback을 등록하지 않는다.

```bash
.venv/bin/python docs/benchmarks/t66e4/measure.py \
  /tmp/mn-e4-frozen-sql.json /tmp/mn-e4-native-fixtures.json --frozen
.venv/bin/python docs/benchmarks/t66e4-targeted/verify_preservation.py
.venv/bin/python docs/benchmarks/t66e4-targeted/verify_cost.py \
  docs/benchmarks/t66e4-targeted/frozen-sql-cost.json
sha256sum -c docs/benchmarks/t66e4-p0/preserved-history.sha256
```

`mobile/`에서 targeted/전체 회귀를 실행한다. 로그는 payload를 출력하지 않고 machine
요약으로 집계한다. historical `t66e4-contract/probe_test.dart`는 별도로 실행한다.

```bash
flutter test --no-pub --machine test/segmented_e4_handoff_test.dart \
  test/segmented_e4_frozen_test.dart test/segmented_e4_provenance_test.dart \
  test/segmented_e4_handoff_crash_test.dart > /tmp/mn-e4-targeted.jsonl
flutter test --no-pub --machine test > /tmp/mn-e4-full.jsonl
```

`handoff_child_test.dart`는 부모가 만든 `e4-owned` 임시 디렉터리만 허용한다.
부모가 actual Flutter tester PID를 SIGKILL한 뒤 별도 SQLite connection과 fresh owning
store, Python backend Snapshot validator로 B/pins/marker를 검사한다.

## oracle와 비용 범위

| 항목 | 독립 근거 |
| --- | --- |
| legacy 값/identity | 실제 backend exporter, v7 manifest/fingerprint/restore validator |
| frozen graph | 실제 backend object set과 독립 recursive SQLite closure 비교 |
| 원 B/J | 원 OfflineStore full reader/hash 및 exact JSON/ordered operations 비교 |
| pending retirement | exact token/owner/status/retryIdentity, file bytes, 실제 AppState original ticket |
| SQL 작업량 | 기존 AuditDatabase의 actual SELECT/execute/returned rows/BLOB/pin write 계수 |
| crash | native transaction/file rename 경계의 actual SIGKILL과 fresh-process reopen |
| P0 보존 | 18 current/checkpoint SHA, 기존 report prefix 21,663B, 원본 5개 SHA |

`measure.dart`의 storage-only `finalAuthorityFence: () {}`는 SQL 작업량 측정일 뿐 설치
권한 시험이 아니다. 실제 권한은 별도의 AppState race suite가 검증한다. 제품 작업 계수와
독립 SQL 계수를 함께 남기며 elapsed time만으로 incremental PASS를 주장하지 않는다.

Full B JSON 읽기/hash와 complete materialization은 명시 legacy 경계 및 cold/reopen의
허용된 O(N) 작업이다. Healthy Frozen-B 반복은 metadata/schema/root pin 검사와 control/hot
hash-on-read만 반복하고, pending J는 기존 O(J) provisional projection으로 매번 새로 읽는다.
일반 segmented-native handoff에는 flat B 생성/hash를 넣지 않는다.

반환 SQL rows/BLOB 계수는 SQLite VM step·physical page I/O·OS cache miss 전체가 아니다.
RSS는 fixture/JIT/observer를 포함하는 관측 현재값이지 production peak memory 보장이 아니다.
첫 SQL 측정은 store.open을 timed recovery 밖에 두었다. 별도 `fresh_handle_open` phase를
추가한 측정은 open의 native schema/usage aggregate 검사 SQL·latency도 분리해서 보존한다.
Aggregate SELECT의 returned row 수를 실제 SQLite scanned row 수라고 표현하지 않는다.
유한한 두 규모의 synthetic 결과를 Android throughput이나 hardware power-loss 증명으로
확대하지 않는다. Arbitrary OS-level open DB unlink/replacement는 지원하지 않는다.

## 보존한 개발 실패

최초 child fixture의 상대 import 경로 오류로 crash suite 6 PASS/2 FAIL이 발생했다.
경로만 수정하고 assertion을 유지했다. 이후 full suite의 E4 v5 초기화가
`STORE_SCHEMA_CORRUPT`로 거부되었다. 원인은 schema catalog parser가 `CREATE UNIQUE INDEX`를
누락한 것이며, 닫힌 schema 검사를 완화하지 않고 정확한 정의를 포함하도록 수정했다.
최종 결과와 혼동하지 않도록 이전 실행 요약을 별도로 남긴다.

큰 실제 backend fixture의 비용 suite를 full regression과 중복 실행한 600초 harness timeout도
보존한다. 최종 실행은 중복 fixture를 없애고 full regression에서 비용을 함께 생성한다.
이 테스트의 유한 harness ceiling만 1,200초로 확장했으며 제품 transport timeout·재시도·작업량
assertion은 바꾸지 않았다. Timeout 뒤 ACQUISITION_BUSY 등 후속 오류도 green으로 숨기지 않는다.
정확한 최초 결과는 [`development-runs.json`](development-runs.json)에 있다.

P0 historical 3 PASS/2 FAIL은 유효 서버 금액을 거부해야 한다는 **교정 전 기대값**이다.
현재 P0 regression 및 독립 differential 결과와 분리한다. 기대값을 바꿔 PASS로 만들지 않는다.

## 최종 결과

[`regression-summary.json`](regression-summary.json)은 actual 최종 whole-suite 종료 집계다.
T01 35/T02 19/T03 11/새 SIGKILL 13 = 78 PASS이며, 기존 E4 85건까지 합해 163 PASS다.
전체 Flutter는 1,440 PASS/0 FAIL/2 SKIP, 기존 E3 I25 publication은 30 PASS다.
Backend는 1,315 tests+1,540 subtests PASS이며 analyze/debug build/changed-format/Ruff/
compileall/frontend build도 PASS했다. 독립 E4 audit PASS를 의미하지 않는다.

- [`frozen-legacy-work-final.json`](frozen-legacy-work-final.json): 실제 원 full reader/hash와
  optimized B/J exact 비교, 4/400 history의 파일·객체 작업량.
- [`frozen-sql-cost.json`](frozen-sql-cost.json): 첫 독립 SQL 계수와 warm query text.
- [`frozen-sql-with-open.json`](frozen-sql-with-open.json): 첫 자료를 유지하고 cold open까지
  분리한 두 번째 독립 실행. Aggregate returned rows와 physical scanned rows는 다르다.
- [`source-hashes.json`](source-hashes.json): 최종 source/test/observer 25파일 correspondence.
- [`development-runs.json`](development-runs.json): schema/import/timeout/context-oracle 실패 이력.

142/1,728 required objects에서 warm은 64 SQL/288 returned rows/9,451B이며 raw/index/full
recovery/root pin 쓰기가 모두 0이었다. Cold·외부 COMMIT·fresh handle은 full 검증하고 다음
warm부터 다시 같은 비용으로 돌아왔다. First frozen ownership은 INSERT 1/state UPDATE 1,
root pin I/D/U 0이다. 이 수치는 유한 synthetic work 증거이지 production 시간 보장이 아니다.
Monetary parser 각각의 호출 횟수나 native VM page scan 전체를 계측한 것으로 표현하지 않는다.

원본 자료의 whole-file SHA 요구 때문에 최신 완료 보고서는 원 `t66e4-implementation.md`를
덮어쓰지 않고 [resumption §11](../../t66e4-implementation-resumption.md)에 추가했다.
일반 사용자 segmented Offline/recovery는 여전히 R1-gated이며 production에서 활성화하지 않는다.
