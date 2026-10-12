# T6.6E2 합성 수집·회귀 증거

기준 commit은 `bd3a7e08c5b810c8c30d26e498d1994218b33b71`이다. Production
endpoint, 실제 계정, 기존 금융 DB를 사용하지 않는다. 실제 backend integration은
`scripts/benchmarks/t66e2_server.py`가 새 RetentionSandbox에 11개 table과 합성
session을 만들고 D3a/D3b/D3c ASGI를 호출하는 private stdin bridge다.
TLS socket이나 Android 단말의 성능 측정은 아니다.

## 재현

기존 repository Flutter dependencies와 `.venv` backend test 환경을 사용한다.
APK는 설치하지 않는다. 성공 로그에는 payload/token을 출력하지 않는다.

```sh
cd mobile
E2_BENCHMARK_OUTPUT=/tmp/money-note-e2-benchmark.json flutter test --no-pub test/segmented_http_integration_test.dart
flutter test --no-pub --machine
flutter analyze --no-pub
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
```

Root에서:

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py docs/benchmarks/t66e1-a01-a02-reaudit/test_reaudit.py
.venv/bin/python docs/benchmarks/t66e1-a01-a02-reaudit/replay_original.py
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
```

Backend 전체 회귀는 `backend`에서 `../.venv/bin/python -m pytest -q`로 실행한다.

## 독립성과 측정 범위

- Cold fixture의 ledger는 현재 1행 + historical 합성 260행이다. 나머지 10개
  table도 실제 authoritative schema에 seed한다. 모든 data는 폐기용이다.
- Expected reachable set은 Python direct SQLite + 별도 reference parser + hashlib다.
  Dart E2 graph walker를 expected oracle로 사용하지 않는다.
- 통합 테스트는 모든 저장 BLOB을 비교하고, 11개 raw tables와 direct source rows를
  대조하며, 다운로드 facts로 별도 canonical Patricia builder를 실행한다.
- 실제 object payload 요청 수는 bridge에서 센다. 내부 `isComplete`만 검사하지 않는다.
- `verification_us`는 E1 cache-read 검증 또는 full-object 검증/put 구간의 합이다.
  후자는 SQLite write/readback 시간을 포함하며, progress/graph/manifest의 모든
  검증 시간을 포함하는 CPU profiler 수치가 아니다.
- Elapsed는 observation/terminal retry/release와 로컬 durable staging을 포함한다.
  Payload bytes와 HTTP JSON/base64 response bytes를 구별한다.
- Incremental cell은 관측 T의 수집 중 다음 writer U도 COMMIT한다. 결과는 T의
  immutable graph이며 별도로 캡처한 T의 direct source oracle과 비교한다. 따라서
  해당 cell elapsed에는 이 bounded writer interleaving 비용도 포함된다.
- 네 cell 각각 1회 HOST 측정이다. 실제 서버 cold graph의 1,168개 순차 인증 요청과
  전체 회귀 비용 때문에 20회 반복을 주장하지 않는다. 여러 회귀와의 경합·JIT·fsync를
  포함한다. Median/production throughput/기기 속도 개선을 주장하지 않는다.
- 동일 Target 조건에서만 합성 Judgment 선택을 고정한다. 같은 raw revision에서
  실제 hot bytes가 바뀌면 별도 object 다운로드가 필요한 정상 변화다.
- RSS profiler 측정은 하지 않았다. 실행 구조는 동시 요청 1개, bounded object/chunk,
  compact graph metadata와 E1 quotas로 제한한다. 엄격한 fixed-memory 증명은 아니다.

## 테스트 범주 연결

| 요구 범주 | 실제 테스트 |
| --- | --- |
| observation/manifest/auth/context/잘못된 fields | `segmented_fetch_test.dart`, `segmented_transport_test.dart`, 실제 ASGI auth cases |
| hash/type/version/identity/offset/length/C1/response budget | fetch의 transfer 변형과 hash-valid negative graph, transport response cases |
| cache/zero payload/change/shared subtree | fetch cache/churn, 실제 HTTP cold/identical/incremental oracle |
| table/descriptor/Patricia/empty/duplicate/missing/internal root | fetch graph cases와 별도 11-table/Patricia reconstruction |
| network/lease/reacquisition/retry/cancel | fetch lifecycle/retry cases와 실제 ASGI expiry/revocation |
| single-flight/bounded concurrency | 같은 store 및 별도 store admission 거부, 순차 HTTP count |
| storage-full/E1 trigger integrity/migration | acquisition store tests, 실제 SQLITE_FULL, 기존 A01/A02 전체 회귀 |
| restart/실제 process termination | fetch recovery, 실제 HTTP resume, 새 SIGKILL 3개 및 기존 E1 경계 |
| B/J/Baseline/Snapshot/UI 비활성 | acquisition 파일 byte 비교, 기존 offline/Snapshot tests, runtime source isolation |

`summary.json`은 최종 실행의 실제 집계와 네 측정 cell을 기록한다. 과거 E1 감사의
FAIL/재감사 증거를 수정하지 않는다. 이 자료는 **구현 내부 검증**이며 독립 E2 감사
PASS나 E3/production 활성화 승인이 아니다.
