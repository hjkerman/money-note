# T6.6E4-RA01 교정 재현

범위는 missing-required `previous_source`에 의한 native 설치/기존 Frozen-B 연결 유실 한 가지다.
원 감사·원 3 FAIL·P0·A01 evidence는 변경하지 않는다. 이 디렉터리는 독립 재감사 PASS가 아니다.
상세 source state matrix·지원 범위·제한은 [교정 보고서](../../t66e4-ra01-correction.md)를 따른다.

## 실행

새 출력 경로를 사용한다. 모든 데이터/credential은 bridge가 만든 임시 synthetic 환경이다.
원 수정 전 재현은 `reproducer-before.json`의 당시 commit에서 실행한 실제 결과다.
현재 checkout을 되돌리거나 수정 전 FAIL을 현재 코드에서 새로 얻었다고 주장하지 않는다.

```bash
mkdir -p /tmp/mn-e4-ra01-rerun
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --concurrency=2 test \
  > /tmp/mn-e4-ra01-rerun/flutter-complete-final.log 2>&1
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=REAUDIT_OUTPUT=/tmp/mn-e4-ra01-rerun/reaudit-complete-final.json \
  ../docs/benchmarks/t66e4-a01-reaudit/independent_test.dart \
  > /tmp/mn-e4-ra01-rerun/reaudit-complete-final.log 2>&1
cd ..
E4_RA01_OUTPUT=/tmp/mn-e4-ra01-rerun/crash-complete-final .venv/bin/python -m pytest -q \
  docs/benchmarks/t66e4-ra01/test_crash.py \
  --junitxml=/tmp/mn-e4-ra01-rerun/crash-complete-final.xml
.venv/bin/python docs/benchmarks/t66e4-ra01/measure.py /tmp/mn-e4-ra01-rerun/cost-owner-final
.venv/bin/python docs/benchmarks/t66e4-ra01/validate.py /tmp/mn-e4-ra01-rerun/checks-release-final
```

원 Phase A 36 Dart/2 cost/6 crash/P0 compatible replay 1, 기존 A01 21 unit/1 concurrent/6 crash,
P0 integration 18/corpus/보존 검사, 원 역사적 diagnostic, E2 cleanup와 backend full도 같은 임시
출력 경로로 실행한다. 동명 `test_crash.py` 두 개를 한 pytest 명령으로 실행할 때는
`--import-mode=importlib`를 쓴다. 원 P0 fixture 오류는 원 artifact로 보존하고 기존
`t66e4-audit/test_p0_replay.py`가 monetary assertions를 바꾸지 않은 compatible replay다.

`collect.py <결과 경로> --require-complete`는 실제 완료한 machine/JUnit 결과와 비용/보존 guard를
검사하고 JSON을 stdout으로 출력한다. 현재 worktree의 artifact를 자동 overwrite하지 않는다.
완료 안 된 full regression을 PASS로 만들지 않는다. before log가 없는 재실행은 보존된 수정 전
evidence를 명시적으로 재사용해야 한다. source hashes/원 결과와 현재 source를 구분한다.

최종 실제 결과는 `summary.json`/`cases.json`/`session-exits.json`에 있다. 신규 교정 51개
(unit 42 + native 비용 2 + 실제 종료 7), 전체 Flutter 1,503 PASS / 2 SKIP, Backend
1,315 tests / 1,540 subtests PASS다. `source-hashes.json`은 이 측정의 코드 snapshot을 고정한다.
`cost-before.json`과 `cost-after.json` 및 `cost-comparison.json`은 원 Frozen-B 측정 전후를,
`native-handoff-cost.json`은 추가 native 경계를 구분한다. 원 실패와 최종 원 반례의 상태는
`reproducer-before.json`/`reproducer-after.json`에 별도로 보존한다.

## 비용과 oracle

기존 독립 SQL observer를 폐기용 source copy에만 연결한다. 제품 counter를 oracle로 읽지 않는다.
원 Frozen-B warm zero-traversal/full verification/pin-write assertion은 그대로 유지한다.
새 native phase는 exact backend hot IDs의 snapshot leaves와 exact index root/facts head 밖의 graph 조회 및
leaf 중복 조회를 거부한다. native hot/raw verification은 Frozen-B-only read와 다른 작업이다.
`measure.py`의 추가 계측은 임시 SQL observer에서 root INSERT/generation DELETE의 UUID/hash parameters만
기록한다. body/credential은 추가 기록하지 않는다. 임시 candidate의 root 생성·해제와 before/after retained
pin 차이를 대조해 기존 accepted/Frozen pin의 실제 rewrite가 없음을 검사한다.
두 규모의 실제 raw/index/object read/rows/SQL frequencies/transaction timing을 보존한다.
반환 rows는 VM scanned rows가 아니며 RSS는 peak memory가 아니다.

원 비용 fixture의 global lex-first 손상 대상은 Frozen closure 밖일 수 있다. 원 assertions는
수정하지 않았다. `observe_original_cost.py`는 임시 copy에 대상 귀속 관찰만 더하고,
`corruption_selector_test.dart`/`corruption-selector.json`은 실제로 무관한 객체를 선택할 수
있음을 별도 재현한다. 이 fixture 귀속 시험 1개를 신규 교정 51개에 합산하지 않는다.
최종 원 비용 2개는 PASS이며, 당시 대상 귀속이 기록되지 않은 중간 실패는 개별 원인을
확정했다고 주장하지 않는다. 자세한 한계는 교정 보고서 §9에 있다.

7개 실제 종료 시험은 owned root/sentinel과 실제 tester PID를 사용한다. fresh process에서 source와
required pins/B/pending/lineage/R1 gate를 검사한다. 프로세스 종료를 hardware power loss나
cross-store atomicity의 증명으로 바꾸지 않는다.

원 RA16/RA18의 입력은 이미 predecessor를 손상시킨 legacy preparation이다. 이는 명시 거부/evidence
보존으로 닫고 guessed source로 수리하지 않는다. 별도 valid-source 실패와 `invalid_rejected` native
경계는 보존된 F0 association을 fresh process에서 isolated verified read할 수 있음을 검사한다.
native RecoveryBlocked를 성공 복구나 일반 Offline-ready로 표현하지 않는다.

DB·credentials·APK·성공 로그 전체는 commit 대상이 아니다. R1 CLOSED, Phase B/R1/deploy/activation
미실행이며 최종 구현 교정도 별도의 독립 targeted re-audit를 기다린다.
