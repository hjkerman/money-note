# T6.6E4 재개 — 격리 adapter 검증과 비용

이 자료는 E4 전체 완료나 독립 감사 PASS가 아니다. P0 checkpoint와 격리 읽기 adapter의
실제 근거이며, 남은 E4 handoff는 [재개 보고서](../../t66e4-implementation-resumption.md)에 있다.
원래 `t66e4-contract/` 및 P0/audit 증거를 수정하지 않는다.

## 재현

Repository root에서 독립 SQL 측정을 실행한다.

```bash
.venv/bin/python docs/benchmarks/t66e4/measure.py /tmp/mn-e4-read-cost.json
```

새 TemporaryDirectory의 source copy에 **기존 독립 E3 SQL observer**만 연결한다.
실제 E2/D3a/D3b synthetic backend·새 SQLite store에서 history 4/400을 측정한다.
정상 제품에 observer를 추가하거나 production listener를 사용하지 않는다.

`mobile/`에서는 다음으로 새 E4 시험을 실행한다.

```bash
flutter test --no-pub --machine test/segmented_adapters_test.dart \
  test/segmented_adapter_authority_test.dart test/segmented_adapter_crash_test.dart \
  test/segmented_adapter_isolation_test.dart > /tmp/mn-e4-tests.jsonl
```

전체 machine 결과는 `summarize_flutter.py <log> <summary.json>`으로 집계한다.
hidden loader/skip/done success를 구분한다. 단순 process exit나 test 이름 나열은 PASS 근거가 아니다.

## 독립 oracle와 비용 구분

- `mobile/test/support/e4_backend_oracle.py`: actual backend exporter order·manifest·fingerprint·
  migrated restore dry-run. 원래 probe bytes를 유지하면서 새 폐기용 seed에만 Unicode/NULL/REAL/
  BINARY sorting 사례를 추가한다. Expected 값을 adapter로 생성하지 않는다.
- `measure.py/measure.dart`: select/execute 및 실제 returned rows/BLOB/pin writes.
  제품 operation counters는 참고로만 함께 기록한다. SQL 계측 latency에는 observer 비용도 든다.
- SQLite 별도 connection과 실제 child SIGKILL: pointer/pins/COMMIT 가능성·fresh recovery와
  exact legacy B/J bytes. hardware power loss proof가 아니다.
- 원 P0 감사의 corpus 24,836개, source hash와 이전 parser oracle는 그대로 재실행한다.

Cold/reopen의 full graph 검증은 허용된 초기 비용이다. 반복 hot read와 작은 generation 변경 뒤
hot read에는 raw/index full scan이나 pin rewrite가 없어야 한다. PK page는 요청 path/leaf 크기에
의존하며 history 전체를 읽는다고 가정하지 않는다. 두 유한 규모만으로 임의 크기의 기기 성능을
증명했다고 주장하지 않는다. R1·frozen publication·retirement handoff 비용은 아직 측정 대상이 아니다.
Native SQL probe는 store recovery/read 부분을 측정하며 store.open, Flutter typed factory,
legacy JSON 파일 읽기·projection 비용은 포함하지 않는다. 현재 standalone frozen legacy view의
반복 O(N+J)는 별도 미완료 항목이다. hot read 측정으로 이 경로까지 incremental PASS라고 주장하지 않는다.
`objects`는 서버 oracle의 현재 reachable graph 크기다. 추가 `persisted_objects`,
`root_pin_rows`, `accepted_sequence`는 timed phase 밖에서 별도 SQLite connection으로 센
committed storage 값이며 이를 혼동하지 않는다. 이전 `read-cost-final.json`도 그대로 보존한다.

최종 자료는 [`read-cost-with-storage.json`](read-cost-with-storage.json),
[`regression-summary.json`](regression-summary.json)과
[`worktree-preservation.json`](worktree-preservation.json)이다.
전체 Flutter는 1,362 PASS / 0 FAIL / 2 SKIP, 새 E4는 85 PASS / 0 FAIL이다.
독립 P0 24,836개 재실행도 mismatch 0이지만 새 E4에 대한 독립 감사 판정은 아니다.
현재 reachable graph 142/1,728 objects에서 반복 hot SQL은 71/71,
객체 body는 9,451/9,451B, full recovery와 pin writes는 0/0이었다.
새 connection recovery는 별도 full 검증을 실행했다. 전체 stage 완료와 미구현 handoff는
재개 보고서에서 구분한다.

## 개발 중 발견한 pagination 오류

`pagination-before.json`은 정수 PK의 typed key 값도 **문자열**이어야 한다는 실제 E1 계약을
새 E4 materializer가 두 번째 page에서 지키지 못한 반례다. 300 history + current 1행의 새
시험이 KEY_INVALID로 실패했다. E1 parser나 원 monetary source를 바꾸지 않고 검증용 PK 문자열을
만들도록 교정했다. 최종 source의 post-fix 결과와 전체 회귀를 별도로 보존한다.

## 보존 정책

원시 성공 로그/DB/financial fixture payload/credential은 commit하지 않는다. JSON 결과의
object hashes와 SQL/operation counts는 합성 증거다. 기존 다섯 진단 파일과 독립 감사 보고서는
역사적 assertion까지 그대로이며, 옛 3 PASS/2 FAIL을 현재 monetary 회귀 실패로 바꾸지 않는다.
