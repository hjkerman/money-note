# T6.6E4-A01 교정 재현

범위는 stale recovery의 source ownership 한 가지다. 원 Phase A 독립 감사와 원 FAIL 증거는
`../t66e4-audit/`에 그대로 둔다. 이 디렉터리는 독립 재감사 PASS나 Phase B/R1 완료 증거가 아니다.
상세 원인·mutation 표·제한은 [교정 보고서](../../t66e4-a01-correction.md)를 따른다.

## 실행

현재 checkout의 `.venv`와 설치된 Flutter를 사용한다. production 경로/API/credentials를 사용하지 않는다.
다음 출력 디렉터리는 새 임시 경로여야 한다. 기존 역사적 artifact를 덮어쓰지 않는다.

```bash
mkdir -p /tmp/mn-e4-a01-rerun
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --concurrency=2 test \
  > /tmp/mn-e4-a01-rerun/flutter-final.log 2>&1
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --concurrency=2 \
  --dart-define=AUDIT_E4_STALE_OUTPUT=/tmp/mn-e4-a01-rerun/after-final-native.json \
  ../docs/benchmarks/t66e4-audit/independent_test.dart \
  ../docs/benchmarks/t66e4-audit/stale_recovery_test.dart \
  > /tmp/mn-e4-a01-rerun/independent-native-final.log 2>&1
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=AUDIT_E4_STALE_OUTPUT=/tmp/mn-e4-a01-rerun/concurrent-state.json \
  ../docs/benchmarks/t66e4-a01/concurrent_recovery_test.dart \
  > /tmp/mn-e4-a01-rerun/concurrent.log 2>&1
cd ..
E4_A01_OUTPUT=/tmp/mn-e4-a01-rerun/crash-native-final .venv/bin/python -m pytest -q \
  docs/benchmarks/t66e4-a01/test_crash.py \
  --junitxml=/tmp/mn-e4-a01-rerun/crash-native-final.xml
python3 docs/benchmarks/t66e4-audit/measure.py /tmp/mn-e4-a01-rerun/cost-final
.venv/bin/python docs/benchmarks/t66e4-a01/validate.py /tmp/mn-e4-a01-rerun/final-checks
```

전체 증거 수집에는 원 감사 README의 P0 integration/원 corpus/호환 replay/원 6개 crash,
backend full JUnit, E2 cleanup 및 script tests도 새 임시 출력 경로에서 실행한다. `collect.py`의
파일명 mapping을 따른다. `before.json`이 없는 재실행은 이 디렉터리에 보존된 원 수정 전 재현을
명시적으로 재사용한다. 현재 수정 코드에서 수정 전 FAIL을 새로 실행한 것으로 표시하지 않는다.
모든 실제 실행이 끝난 뒤 `collect.py <출력 디렉터리> --require-complete`로 완료 수·성공 exit·
source/B/pending 보존을 재검사한다. 전체 Flutter가 진행 중이면 이 옵션은 PASS artifact를 만들지 않는다.

수정 전 원 재현은 원 audited commit에서 수행한 `reproducer.json.before`다. 현재 코드에서 이전 실패를
다시 만들기 위해 구현을 되돌리지 않는다. `collect.py`는 실제 machine/JUnit과 원 independent SQL
cost를 읽고 정상 warm 12개 조합의 교정 전후 작업량 동등성을 assert한다. 출력은 JSON이며 원 보고서를
수정하지 않는다. 원시 성공 로그·SQLite DB·APK·credentials는 commit 대상이 아니다.

## oracle와 계수

- unit 21개: 실제 SQLite·별도 connection·파일 bytes·기존 원 AppState·동기 마지막 hook·Completer.
- 별도 동시 복구 1개: 원 FA17의 설치·지속 상태 oracle를 유지하고 최신 B의 복구도 A와 함께 실행한다.
- 최종 새 crash 6개: 실제 tester PID SIGKILL 및 fresh process reopen. native COMMIT 이전 case는
  실제 별도 SQLite reader로 COMMIT busy 구간을 만들고 source 변경과 미COMMIT prepared row를 확인한다.
- 원 Phase A 45개: Dart 35 + 원 FA17 1 + 비용 2 + 원 crash 6 + P0 호환 replay 1이다.
- 기존 E4 authority grouping 51, 기존 E4 crash 17과 기존 E1/E2/E3 crash 26은 전체 Flutter에 포함된다.
  원 suite를 재실행한 횟수나 child worker 호출 수를 새 독립 case 수로 더하지 않는다.

`summary.json`은 실제 결과, `reproducer.json`은 원 실패/교정 후 지속 상태,
`cost.json`/`cost-comparison.json`은 raw SQL observer를 축약한 측정,
`crashes.json`은 첫 성공한 새 4개 crash의 source/lineage/pin/pending 결과다.
`crashes-strict.json`은 같은 4개를 kill 직후 source 관찰까지 보강해 재실행한 중간 증거다.
`crashes-final.json`은 native/native-only 이전 source 복구 두 경계를 추가한 최종 6개 증거다.
같은 case의 재실행을 새 14개 시험으로 세지 않는다. 이전 source 보완 전 비용과 재현은 원 파일로
남기고 `cost-final.json`, `cost-comparison-final.json`, `reproducer-final.json`에 최종 실행을 둔다.
Full graph 원자료는 전체 synthetic 금융 행 대신 원 oracle의 table counts/source digest/control digest와
required closure/receipt로 축약한다. 비용 artifact는 반복 SQL을 statement별 횟수로 보존한다.
SQL returned rows를 scanned VM rows로 바꾸거나 synthetic latency를 production 성능으로 표현하지 않는다.
`concurrent-recovery.json`은 최신 설치의 복구와 오래된 복구가 함께 실행된 지속 상태다.
새 교정 시험은 unit 21 + 별도 동시 복구 1 + SIGKILL 6 = 28개이며 중복 재실행은 더하지 않는다.
`session-exits.json`은 완료한 process exit와 진행 중 artifact 생성을 거절한 완료 guard의 결과를
구분해 보존한다. harness compile/잘못된 경로/역사적 fixture 실패를 최종 제품 FAIL로 섞지 않는다.

R1 gate CLOSED, 일반 startup/read/write 불변이다. debug APK는 build만 허용하며 설치/배포하지 않는다.
