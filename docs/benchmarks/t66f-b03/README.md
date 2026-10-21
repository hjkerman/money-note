# B03 합성 계측 증거

> 최종 구현 검증: **신규 75 PASS**, 전체 backend **1,392 tests / 1,540 subtests PASS**,
> 전체 Flutter **1,648 PASS / 0 FAIL / 2 SKIP**. `evidence/lineage-calibration-summary.json`의
> regression gate는 PASS다. 별도 독립 B03 감사·5-point 비용 grid·Phase B PASS는 아니다.
> `sealed-*`는 최종 완료-cohort observer의 실행이며 아래 과거 checkpoint를 대체 판정한다.

> 최신 lineage 한정 승인을 적용했다. 현재 소스 기준은 `source-lock-review.json`,
> 전층 경계는 `lineage-coverage.json`, 최종 실행은 `evidence/lineage-*`로 분리한다.
> 아래 승인 전·이전 승인 checkpoint의 BLOCKED/FAIL 기록은 역사 자료다.
> 최종 전체 회귀가 완료되기 전에는 구현 COMPLETE로 해석하지 않는다.

> 승인 후: C1/AppState의 원 보호 검사와 새 exact source 검사는 28 PASS다.
> 현재 blocker는 P0 `OfflineStore.recoveryLineageFingerprint`의 미계측 SHA 경계에 대한
> 별도 한정 승인이다. `collect_approved.py` 및 `evidence/approved-*`가 후속 결과다.
> 아래 승인 전 기록과 원 21 PASS/2 FAIL 증거는 보존한다.

이 경로는 제품 telemetry/API가 아니다. 기본 비활성인 in-process 관측기와 합성
테스트만 포함한다. 현재 판정은 **BLOCKED**이며 전체 grid·독립 B03 감사 PASS가 아니다.
완전한 제한은 [구현 보고서](../../t66f-b03-logical-cost-instrumentation.md)를 따른다.

## 재현

저장소 root에서 다음 명령을 사용한다. 환경의 `MONEY_NOTE_*` 운영 설정은 전달하지
않고 disposable DB·합성 TLS fixture만 사용한다. 성공 로그를 전체 출력하지 않는다.

```sh
.venv/bin/python -m pytest -q backend/tests/test_logical_cost_instrumentation.py
.venv/bin/python -m pytest -q docs/benchmarks/t66f-phase-b-final/test_counters.py
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub test/segmented_logical_cost_test.dart
/home/hjkerman/.flutter/bin/flutter test --no-pub test/segmented_logical_cost_http_test.dart
/home/hjkerman/.flutter/bin/flutter test --no-pub test/segmented_logical_cost_overhead_test.dart
/home/hjkerman/.flutter/bin/flutter test --no-pub test/segmented_logical_cost_lineage_test.dart test/segmented_logical_cost_boundaries_test.dart test/segmented_logical_cost_source_lock_test.dart
```

`server.py`는 기존 Phase B의 disposable real HTTP/TLS harness를 감싼다. 비공개 stdin
`cost` 명령으로 합계만 반환하며 제품 endpoint나 credentials를 추가하지 않는다.
`run_checks.py backend-full`은 기존 bounded runner를 재사용한다. 증거가 이미 있으면
덮어쓰기를 거부하므로 새 캠페인은 별도 검토한 출력 경로를 사용한다.
`collect.py`는 명시한 `/tmp/mn-b03-*` 결과만 수집한다. 기존 감사 자료를 탐색·덮어쓰지 않는다.

## 형식과 해석

`evidence_format.py`의 `schema_version=1`은 run/fixture/workload/layer/stage/operation/
counter/status/unit/coverage를 담는다. actual cold generation으로 반복 실행을 구분한다.
정수는 decimal string이며 hash·validation·write를 합쳐 unique data 양이라고 하지 않는다.
SQL bind bytes, TEXT/BLOB NEW row bytes, scalar counts와 physical file I/O는 서로 다르다.
TEMP BEFORE/AFTER 관측과 실제 COMMIT/ROLLBACK 결과로 시도·효과·commit을 구분한다.
작은 실패 parser의 submitted span은 정확한 소비 prefix 측정이 아니다.

backend 계측은 실제 호출의 ContextVar, Dart 계측은 Zone을 따른다. process/isolate는 새
collector를 명시해야 한다. fixed categories만 누적하고 금융 원문·개별 object log를 저장하지 않는다.
작은 real TLS는 accepted graph의 cold/identical/delta/read/reopen을 검증했지만 normative
fixed-H/fixed-D grid나 native Frozen installation 전체 byte coverage로 확대하지 않는다.

## 보존한 실패와 남은 gate

초기 compile·SQL double-close·잘못 선택한 Frozen reopen probe 실패를 원 로그와 함께 보존했다.
원 `segmented_adapter_isolation_test.dart`는 변경하지 않았고 현 소스에서 21 PASS/2 FAIL이다.
source-lock 변경은 구체적 승인 대기이며 skip/xfail/기대 SHA 완화는 하지 않았다.

신규 calibration은 48 PASS(backend 20, Flutter 28), backend 전체는 1,388 tests /
1,540 subtests PASS다. 원 16 calibration과 재실행은 신규 수에 더하지 않는다. 전체 Flutter는
미실행이다. Python/Dart 소형 overhead를 보존하며 SQL 관측 오버헤드는 작지 않다.
독립 실제 HTTP 동시 계측·late import·expiry/retry/fallback·Frozen/file coverage와 대형
계측 perturbation의 미해결 한계를 숨기지 않는다. Android/R1/물리 power loss는 검증하지 않았다.

## 최종 계측 인터페이스와 H/D/N 캠페인 인계

최초/승인 전 기록은 위와 같이 보존한다. 현재 구현은 late import·실제 동시 TLS·native 취소 tail·
closed scope·retry/expiry·Frozen 및 별도 process의 실제 경계를 보정한다. 최종 결과는
`collect_lineage.py`가 완료된 runner/JUnit/machine 로그에서 수집한다. 과거 collector를 다시
실행해 이전 FAIL 집계를 현재 판정으로 덮어쓰지 않는다.

Backend는 `instrument()`, `instrument_connections()`, `instrument_workers()`를 합성 test session에만
설치하고 각 generation/HTTP 작업을 독립 `Collector.stage()`로 감싼다. 요청 종료와 실제 native
worker 종료는 다르므로 `finish_when_idle()` 뒤 snapshot을 확정한다. 기존 TLS wrapper는 이를
실제 D3 요청에 적용하며 sample은 16개다. engine source/endpoint는 바꾸지 않는다.

Flutter는 같은 기존 store에 `diagnosticDatabaseFactory`로 `CostDatabase`를 선택하고
`LogicalCost.run(stage, body)`를 쓴다. 실제 AppState isolated publish가 기존 E2/E3 호출에 stage를
부여한다. 명시 Frozen/file 시험에서만 `CostIo`의 합성 root 범위를 선택한다. fresh process는
새 collector를 열며 자동 전파라고 하지 않는다. collector는 권한·receipt가 아니다.

`evidence_format.snapshot(run_id, fixture, workload, layer, counters, environment, coverage)`는
정렬한 decimal aggregate를 stage/operation/unit/status로 내보낸다. `fixture`에는 동일 seed·평가일·
원문 descriptor identity와 **실제 H/D/N**을 명시한다. 제공 예제의 H=null인 작은 fixture를 규범
grid와 섞지 않는다. 정상 no-change D=0, card/cash D=1을 구분한다. cumulative snapshot 간 차분은
같은 run/collector에서만 계산하고 retry·recovery 작업은 별도 scope 또는 명시 phase로 남긴다.

후속 감사의 N은 protocol 그대로 1000/5000/10000/50000/100000이다. 기존 current ledger 105행
fixture의 H는 행 수만이 아니라 hot/control/descriptor 크기까지 포함한다. 기존 B02의
`verification_profile.dart`와 실제 HTTP harness를 재사용해 store factory·collector만 선택할 수 있다.
예제 측정 인터페이스가 준비됐다는 뜻이지 그 다섯 N의 비용이나 I25 PASS라는 뜻이 아니다.

계측을 켠 host timing은 앱의 무계측 latency가 아니다. TEMP trigger/UDF 관측은 특히 쓰기 비용을
늘리므로 계측 timing과 기존 성능 timing을 구분한다. 100k lease perturbation을 임의 계수로 보정하거나
이미 검증한 큰 cold를 B03 기본 loop에서 재실행하지 않는다. 실제 Android VFS/I/O·power proof의
명시 rollout 의무를 R1에 일괄 이관하거나 면제하지 않는다.
