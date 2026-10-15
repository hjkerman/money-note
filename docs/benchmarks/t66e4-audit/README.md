# T6.6F Phase A / E4 독립 감사 재현

대상은 `e386586194edbef1fc35f0ea1cf4145a2ae32685`, 전체 비교 기준은
`ab59d6bbc39f27c36beb059f984ef527ac7b0bef`다. 제품 source는 변경하지 않는다.
판정·정확한 계수·제한은 [감사 보고서](../../t66e4-independent-audit.md)에 둔다.
Phase B, R1, 배포, APK 설치 또는 segmented 활성화를 수행하는 도구가 아니다.

## 새 독립 사례

- `independent_test.dart`: 수정하지 않은 제품 구현에서 35개. 실제 synthetic backend의
  authenticated observation과 E1 검증 cache를 사용한다. 새로운 cache가 generation
  membership이나 AppState 권한을 대신하지 않는다. SQL의 accepted/installed/frozen,
  실제 legacy B/pending bytes를 별도로 확인한다.
- `state_oracle.py`: 새 read-only SQLite 연결에서 실제 C1/hash/typed edges, 네 roots의
  closure, receipt/counts, F(raw) 및 global Patricia를 검증한다. 과거 독립 E3 oracle를
  재사용하되 E4 installed/frozen/legacy association과 11-table export 순서·원 control
  metadata 검사를 추가했다. 제품 reachability helper나 `graph_verified`를 기대값으로 쓰지 않는다.
- `test_crash.py`, `crash_child_test.dart`: 이미 실제 G1을 설치한 상태에서 G2 handoff
  6곳을 SIGKILL한다. 새 process의 data-only recovery와 별도 Python SQLite/lineage 검사를
  수행한다. 원 outcomeUnknown marker는 모든 경우 byte-identical로 남아야 한다.
- `cost_test.dart`, `measure.py`: 5/512 history의 실제 서버 graph에서 반복 읽기와
  full fallback을 측정한다. 임시 source copy에만 실제 SQL proxy와 함수 진입 observer를
  연결한다. 제품 `work`/`fullBaselineReads` counter를 판정 oracle로 읽지 않는다.
- `test_p0_replay.py`: 원 P0 assertion을 모두 유지한다. 후속 E4 신규 파일을 과거 E3
  commit에서 복원하려던 원 fixture의 enumeration에 `--diff-filter=M`만 적용한다.
  원본 P0 시험 파일과 역사적 3 PASS/2 FAIL 진단은 수정하지 않는다.
- `stale_recovery_test.dart`: 같은 실제 AppState의 이전 취소 요청이 복구 metadata read에서
  대기하는 동안 최신 요청을 정상 설치한다. 이전 recovery를 재개한 뒤 source/B/pending과
  별도 SQL rows 및 store close/reopen 결과를 비교한다. 제품 코드는 계측하지 않는다.
  올바른 상태 보존을 요구하는 assertion이 **FAIL**하여 E4-A01을 재현한다.

새 사례 수는 **35 + 6 + 2 + 1 + 1 = 45**, **44 PASS / 1 FAIL**이다.
FA01 positive assertion 보강 후 2개 재실행과 FA17의 첫 실패/취소 재실행을 중복 계수하지 않는다.
비용 phase 30개, child Flutter 호출 12개,
기존 183/163개 회귀를 새 사례 수에 더하지 않는다.

## 실행

repository에 준비된 `.venv`와 `/home/hjkerman/.flutter/bin`을 사용한다.
출력 경로는 새 감사 전용 임시 디렉터리로 정한다. production 경로를 입력하지 않는다.
성공 로그 전체·DB·credential·APK를 commit하지 않는다.

```bash
mkdir -p /tmp/mn-e4-phase-a-rerun
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=AUDIT_E4_OUT=/tmp/mn-e4-phase-a-rerun/independent-persisted.json \
  ../docs/benchmarks/t66e4-audit/independent_test.dart \
  > /tmp/mn-e4-phase-a-rerun/independent.log 2>&1
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=AUDIT_E4_STALE_OUTPUT=/tmp/mn-e4-phase-a-rerun/stale-recovery.json \
  ../docs/benchmarks/t66e4-audit/stale_recovery_test.dart \
  > /tmp/mn-e4-phase-a-rerun/stale-recovery.log 2>&1
# 위 FA17은 교정 전 제품에서 exit 1이 예상되는 보존 반례다.
cd ..
E4_AUDIT_OUTPUT=/tmp/mn-e4-phase-a-rerun .venv/bin/python -m pytest -q \
  docs/benchmarks/t66e4-audit/test_crash.py \
  --junitxml=/tmp/mn-e4-phase-a-rerun/crash.xml
python3 docs/benchmarks/t66e4-audit/measure.py /tmp/mn-e4-phase-a-rerun/cost
E4_P0_AUDIT_OUTPUT=/tmp/mn-e4-phase-a-rerun/p0 .venv/bin/python -m pytest -q \
  docs/benchmarks/t66e4-audit/test_p0_replay.py
```

`cost_test.dart`는 `measure.py`가 만든 instrumented copy에서만 실행한다.
`audit_trace.dart`를 제품 library에 추가하지 않는다. 임시 copy의 package config만
다시 연결한다. observer는 이전 독립 E3의 `AuditDatabase`를 사용하며, driver가 실제
반환한 rows/BLOB과 실행한 SQL을 센다. full verifier, Frozen recovery, legacy load/hash의
진입은 별도 source instrumentation으로 센다. AppState 권한 proof는 계측하지 않은
35개 시험과 실제 SIGKILL에서 확인한다.

원본 P0 suite와 역사적 진단도 별도로 실행한다. 현재 원본 P0 suite의 4 PASS/1 fixture
실패와 호환 재현의 1 PASS를 숨기지 않는다. 금액/bytes/hash assertions는 완화하지 않는다.

## 비용 범위와 oracle

최종 graph는 146/2,177 objects다. storage-only 반복은 두 규모 모두 **64 SQL /
288 returned rows / 9,451 object-body bytes**다. 2개의 J를 포함한 전체 pending adapter는
**85 SQL / 423 returned rows / 9,451 object-body bytes**다. 두 경로 모두 raw/index/full
verification/legacy full read/hash/pin I/D/U는 0이다. B+J의 값과 operation identity/order는
변경하지 않은 full legacy reader와 exact 비교한다.

fresh handle, 외부 SQLite COMMIT, corrupt object, missing pin, changed legacy lineage도
계측한다. 전체 graph oracle와 fresh SQLite 검사는 측정 구간 밖에서 수행한다.
`warm-query-plans.json`은 같은 실제 schema를 새 in-memory SQLite에 생성한 독립
EXPLAIN 결과다. 객체·root pin 조회는 PK lookup이고 schema/singleton/frozen metadata만
제한된 scan을 한다.

SQL returned rows를 VM scanned rows로 부르지 않는다. object-body bytes에는 receipt,
metadata/J 파일·페이지 I/O·전체 serialization CPU가 포함되지 않는다. Cold open의 usage
aggregate는 별도 O(N) 작업이며 read phase에 포함하지 않았다. RSS는 JIT/fixture를 포함한
현재 process 값이지 Android peak memory가 아니다. 유한한 두 규모의 결과와 source
논증을 함께 사용하며 모든 미래 graph 크기의 실측 보장으로 표현하지 않는다.

## 보존 결과

`source-inventory.json`은 최초 clean Git/remote 상태와 전체 71파일의 SHA-256이다.
`summary.json`, `independent-cases.json`, `persisted-state.json`, `cost.json`,
`crash.json`, `warm-query-plans.json`, `finding-e4-a01.json`, `environment.json`은
이 감사의 관찰을 보존한다. 원본 구현 측
benchmark/FAIL/prefix를 덮어쓰지 않는다. `/tmp` 원시 로그의 영구 가용성을 전제하지 않는다.

최초 전체 Flutter의 SIGKILL barrier 3 FAIL, 최초 backend quota 503/429 실패, 감사
harness의 import/경로/순서/예외형 오류와 중단된 실행은 최종 결과와 구분한다.
test assertion, timeout, 제품 코드를 바꾸어 회귀를 통과시키지 않았다. 전체 Flutter 재실행은
동시 실행 수만 2로 제한했다. OS/hardware power loss, Android 설치, 운영 접근은 검증하지 않았다.
