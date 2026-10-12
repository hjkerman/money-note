# T6.6E1 E1-A01/A02 독립 targeted 재감사 증거

대상은 `98f0bfaeb5b454796eb9dc40290ae1e340ce80ca`이며, 기준은
`133391242b44573cfe3c1efb9950fa526be0b7f8`이다. 모든 추가 실행은 새 disposable
SQLite와 임시 디렉터리만 사용한다. 구현·기존 반례·과거 FAIL 결과를 변경하지 않는다.

## 실행

Repository root에서 실행한다. 기존 mobile dependency 설정이 필요하며 설치나 배포를
수행하지 않는다. `DART`는 필요한 경우 현재 Dart 실행 파일 경로로 지정한다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-a01-a02-reaudit/test_reaudit.py
.venv/bin/python docs/benchmarks/t66e1-a01-a02-reaudit/replay_original.py
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py
```

기본 결과 경로는 `/tmp/mn-e1-a01-a02-reaudit`다. 새 pytest suite는
`E1_REAUDIT_OUTPUT`으로 출력 경로를 바꿀 수 있다. `replay_original.py`는 원래
`reproduce_findings.py`를 변경 없이 실행하고, `findings.json`의 출력만 임시 경로로
돌린다. 이 redirect는 production 객체·검증·SQLite 동작에 관여하지 않는다.
과거 `findings.json`의 SHA-256이 실행 전후 동일한지도 검사한다.

## 파일과 독립 오라클

| 파일 | 역할 |
|---|---|
| `make_corpus.py` | 실제 backend `setting_money`, `Row.make`, `leaf`로 기대 판정·바이트를 생성하고 Python JSON 및 hashlib로 추가 확인 |
| `session_worker.dart` | 변경 없는 E1 API를 별도 장기 실행 process에서 호출; 기존 fault hook을 제어 barrier로만 사용 |
| `test_reaudit.py` | 별도 Python SQLite 연결로 전체 행·BLOB·usage·FK·lock·COMMIT 결과 확인 |
| `replay_original.py` | 원래 독립 ASGI/SQLite 최소 반례 재실행, 과거 증거 보존 |
| `results.json` | 이번 실행의 실제 건수·환경·측정·판정 근거 |
| `cases.json` | 새 38개 시나리오의 기대값과 관측값, SQL 정의 및 interleaving |
| `original-replay.json` | 원래 반례의 이번 ASGI/SQLite 실제 결과 |
| `performance.json` | 4개 cell 각각 200회 측정 원자료; 단위 µs |

전체 차분 corpus는 매 실행마다 `/tmp`에 생성한다. 4,755건 중 보고된 165건을 포함하고
4,590건을 추가했다. 모든 Unicode codepoint의 Python `isspace()`를 열거해 얻은
29종의 앞·뒤 조합 29×29×4, 경계 문자 57종의 위치 변화, BOM/format/NUL,
문법·범위·5,000자리 문자열, seed `66010102`의 256건을 포함한다. Dart 검증기로
기대 판정을 만들지 않는다. 음성 객체는 canonical/hash-valid지만 backend가 승인해
전달한 객체라고 주장하지 않는다. corpus digest는 `results.json`에 기록한다.

## 새 pytest 시나리오

| 사례군 | 건수 | 기대값 및 실제 관측 | 독립 오라클 |
|---|---:|---|---|
| monetary differential 및 reopen | 1 | 4,755건 일치, 3,816 승인/939 거부; 유일 객체 3,815개 원문 그대로 저장 | backend, Python JSON/hashlib, fresh SQLite·process |
| 11개 필수 trigger 각각 `WHEN 0` | 11 | duplicate/cleanup 거부, 이전 전체 행 동일, valid read 유지 | 독립 SQL catalog와 8-table snapshot |
| 성공 이후 trigger 제거, 5개 mutator | 5 | 매 write `STORE_SCHEMA_CORRUPT`, 추가 COMMIT 0 | 장기 실행 handle + 별도 SQLite |
| 첫 valid object 이후 원래 한도 재현 | 1 | objects 1→1, reopen 거부, 기존 BLOB 유지 | 실제 committed rows/hash/usage |
| 정확한 schema 정책 | 5 | formatting/extra view/extra index/missing index/altered table 거부 | 실제 sqlite_master 및 row snapshot |
| validation–COMMIT 사이 DDL | 8 | transaction 중 DDL `SQLITE_BUSY(5)`; COMMIT 뒤 DDL 성공, 다음 write 거부 | 2 process/2 native SQLite runtime와 barrier |
| DDL writer가 BEGIN보다 먼저 선점 | 2 | `STORE_BUSY`, DDL rollback 뒤 정상/commit 뒤 schema 거부 | 실제 SQLite write lock |
| SHARED reader에 의한 COMMIT busy | 1 | 실패한 insert 전부 rollback; 독자 종료 뒤 재시도 정상 | independent read transaction 및 actual rows |
| 감사자가 exact DDL 복구 | 1 | 정상 duplicate, quota 초과 insert rollback | 실제 count 1, 객체·staging 보존 |
| 동일 handle 반복 성공/DDL/반복 재시도 | 1 | 캐시된 성공으로 schema 검사를 생략하지 않음 | 변경 전후 전체 행 비교 |
| schema를 복원한 payload 손상 | 1 | schema 오류와 구분한 read-time 무결성 거부 | exact DDL, corrupted BLOB 직접 조회 |
| 제한된 성능 측정 | 1 | 정상 insert/duplicate 각 200회, schema/base transaction 각 200회 | native SQLite 시간·catalog 정의 20개 |
| 합계 | 38 | PASS 38, FAIL 0 | `results.json` |

추가 테스트에서 사용하는 checkpoint는 제품에 원래 존재하는 hook이다. 구현 source를
instrumentation하거나 hook으로 검증 자체를 대체하지 않았다. DDL blocker는 실제
SQLite 결과이며 mock locking 모델이 아니다.

## 성능 해석

Duplicate warmup 20회 후 실제 E1 API로 duplicate 200회와 서로 다른 server-derived
객체 insert 200회를 측정한다. 별도 Dart SQLite 연결에서 BEGIN/ROLLBACK만 하는
cell과 동일한 2개 schema query·20개 정의 비교를 추가한 cell을 번갈아 200회씩 잰다.
후자는 private `_requireSchema`를 직접 호출한 profiler가 아니라 같은 SQL/비교 비용의
분리 측정이다. 현재 host의 JIT, filesystem sync, 병행 backend 회귀 영향을 포함한다.
운영·실기기 latency나 고정 overhead 상한으로 해석하지 않는다.

## 회귀 명령

```sh
cd mobile
flutter test --no-pub --machine
flutter analyze --no-pub
dart format --output=none --set-exit-if-changed lib/src/segmented test/segmented_protocol_test.dart test/segmented_store_test.dart test/segmented_crash_test.dart test/segmented_money_correction_test.dart test/segmented_schema_correction_test.dart test/support/segmented_fixture.dart test/support/segmented_crash_worker.dart
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
```

```sh
cd backend
../.venv/bin/python -m pytest -q --durations=10
```

```sh
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
.venv/bin/ruff check backend/app backend/isolated_sync backend/tests scripts docs/benchmarks/t66e1-a01-a02-reaudit
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts docs/benchmarks/t66e1-a01-a02-reaudit
cd frontend
npm run build
```

APK는 compile만 했으며 설치하지 않았다. machine 결과의 hidden loader 37개는 테스트
건수에서 제외했다. Backend JUnit의 subtests는 별도 정규 tests로 중복 계수하지 않았다.
기존 Flutter diagnostic 2개는 SKIP이며 통과로 계수하지 않았다.
