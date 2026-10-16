# E4-RA01 독립 재감사 증거

대상은 `af9525e20e6df1dd7dfc152d3db79c1eb07925d2`다. 제품·원 감사·원 반례는 수정하지 않는다.
판정과 한계는 [독립 보고서](../../t66e4-ra01-independent-reaudit.md)를 따른다.

`inventory.json`은 최초 refs/실제 remote/clean 상태, 전체 교정 29파일과 역사적 자료 44파일의 SHA,
정확한 Git tree를 기록한다. `summary.json`/`cases.json`은 실제 machine/JUnit 결과에서 집계한다.
기존 구현 시험을 새 독립 시험 수에 넣지 않는다. `independent-state.json`, `provenance-state.json`,
`original-three.json`, `crashes.json`에는 별도 연결의 committed rows·source identity·B/J/pending byte
digest와 fresh-process 결과를 둔다. 실제 DB·APK·credential·전체 성공 로그는 commit하지 않는다.

## 새 독립 시험

`independent_test.dart`의 18개 사례는 연속 legacy/native 전환, 최초 설치 rollback/retry, 잘못된
predecessor 타입, native-only owner, 검증 후 최신 request, schema/source 변경, wrong operation sequence,
반복 reopen/recovery, unknown pending과 Frozen-B 보존을 검사한다.
`provenance_test.dart`의 6개 사례는 foreign principal/dataset/epoch predecessor, 같은 Snapshot의 다른
legacy lineage, truncated receipt, E3 검증 뒤 root pin 손실을 검사한다.

`test_crash.py`의 3개 사례는 실제 tester PID에 SIGKILL을 보낸다. 최초 native pointer/COMMIT 전,
최초 native COMMIT 후, legacy→native→새 legacy의 Frozen pointer/COMMIT 전 경계다.
새 process에서 반복 recovery 후 별도 Python SQLite/C1/SHA/typed graph/F(raw)/Patricia/v7/v4 oracle로
검사한다. 예외 주입과 프로세스 종료를 구분하며 OS crash·전원 손실 보장을 주장하지 않는다.

`measure.py`는 원 독립 SQL observer를 폐기용 source copy에만 붙인다. 제품 counters를 oracle로
읽지 않는다. `cost_test.dart`의 새 7/256 history fixture에서 실제 SQL·반환 rows·object body bytes·
raw/index 조회·full verifier/legacy reader 함수 진입·pin I/D/U를 센다. SQL 반환 rows는 VM scan이나
physical I/O가 아니며 RSS는 peak memory가 아니다. 현재 worktree 제품을 계측하지 않는다.

## 재실행

새 출력 폴더를 사용한다. backend bridge와 fixture는 새 synthetic 데이터와 폐기용 SQLite만 사용한다.

```bash
mkdir -p /tmp/mn-ra01-independent-rerun
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=RA01_AUDIT_OUTPUT=/tmp/mn-ra01-independent-rerun/new-independent-final.json \
  ../docs/benchmarks/t66e4-ra01-reaudit/independent_test.dart
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=NR_PROVENANCE_OUTPUT=/tmp/mn-ra01-independent-rerun/provenance-final.json \
  ../docs/benchmarks/t66e4-ra01-reaudit/provenance_test.dart
cd ..
NR_CRASH_OUTPUT=/tmp/mn-ra01-independent-rerun/new-crash .venv/bin/python -m pytest -q \
  docs/benchmarks/t66e4-ra01-reaudit/test_crash.py \
  --junitxml=/tmp/mn-ra01-independent-rerun/new-crash.xml
.venv/bin/python docs/benchmarks/t66e4-ra01-reaudit/measure.py \
  /tmp/mn-ra01-independent-rerun/independent-cost-final
.venv/bin/python docs/benchmarks/t66e4-ra01-reaudit/run_regressions.py \
  /tmp/mn-ra01-independent-rerun/regressions
```

전체 Flutter/backend와 원 비용·P0·정적 검사는 보고서의 실행 목록을 따른다. `collect.py`는 완료된
전체 로그/JUnit과 이 경로의 inventory를 읽고 감사 evidence만 갱신한다. 시험을 실행하거나 실패를
PASS로 바꾸는 도구가 아니다. 원 반례 RA16–18은 수정 없는 이전 감사 파일을 실행한다.

## 중간 harness 오류와 역사적 실패

새 harness의 누락 import 컴파일 오류와 NR02의 과도한 pin 보존 요구를 최종 결과와 분리한다.
NR02의 최초 assertion은 여러 정상 게시 뒤에도 모든 옛 generation owner를 영구 보존하라고 요구했다.
계약은 실제 accepted/previous/Frozen 의무를 보존한다. 새 시험을 실제 Frozen owner의 모든 root rows
보존으로 바로잡고 before/after accepted/installed/Frozen/roots를 기록했다. 최초 실패 로그 digest와
오류는 `summary.json`에 남긴다. 원 감사 시험의 assertion은 변경하지 않았다.

원 monetary diagnostic의 3 PASS/2 FAIL은 superseded pre-P0 기대값이다. 원 P0 Python의 4 PASS/1 FAIL은
새 E4 파일을 과거 commit에서 찾는 fixture 오류이며 기존 compatible replay를 별도 실행한다.
24,836개 monetary/C1/hash differential assertions의 mismatch와 이 Git fixture 오류를 혼동하지 않는다.
이미 손상된 legacy preparation의 RA16/18은 명시 거부/evidence 보존으로 닫으며 자동 수리를 주장하지
않는다. 정상 source의 실패 보존 및 native source의 retained Frozen association 읽기는 별도 검증한다.

Phase B·R1·deployment·APK installation·production segmented activation은 실행하지 않는다.
