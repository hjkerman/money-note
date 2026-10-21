# B03 독립 계측 감사 증거

제품·binding protocol·기존 source-lock·과거 감사는 변경하지 않았다. 전체 판정은
[독립 보고서](../../t66f-b03-independent-instrumentation-audit.md)를 따른다.

`backend/tests/test_logical_cost_independent_audit.py`와
`mobile/test/segmented_logical_cost_independent_audit_test.dart`는 독립 literal/SHA/SQLite/
역사 함수 oracle를 사용한다. 이름이 `reproduce` 또는 `defect reproducer`인 사례는
**실제 계측 값이 독립 DB oracle와 다름을 확인하는 재현 시험**이다. 이 시험의 PASS를
계측의 PASS로 해석하지 않는다. 기존 제품 테스트 assertion은 수정하지 않았다.

`inventory.py`는 시작 commit의 추적 파일 전체와 실제 파일을 비교하고 B03 변경 284개의
SHA·JSON·압축·JUnit 원문 무결성 및 exact source 복원을 검사한다. `source-review.json`은
제품 6파일 각각의 원래 동작·관측·비활성·lock·상태·비동기·예외·할당·소유권·회귀·부작용을 기록한다.

`lineage-goldens.json`은 Python 표준 JSON/SHA로 만든 UTF-16 key-order 역사 계약의 별도 golden이다.
역사 함수는 `da818648`에서 읽었고 원문·원 SHA는 `evidence/historical-lineage-source.json`에 있다.
최소 hash 입력은 복구 가능한 전체 v4 baseline이라고 주장하지 않는다. 별도 기존 baseline 4종과
실제 Frozen 설치/새 프로세스 recovery 회귀가 그 구분을 보완한다.

`server.py`는 기존 B03 TLS harness에서 실제 native SHA/parser에 전달되는 buffer를 한 번
위임하면서 별도로 관찰한다. oracle를 위해 제품 hash나 parse를 다시 실행하지 않는다.
`http_test.dart`는 실제 backend→Flutter E1/E2/E3/E4와 enabled/disabled object/금융 값,
고유 object BLOB의 exact 합, 필수 hash/validation span의 독립 하한을 검사한다.
두 동시 TLS 요청은 정상 token 43B와 잘못된 token 25B로 구별한다. credentials는 증거에 저장하지 않는다.

`run.py`는 원 bounded runner의 실행·RSS/시간/disk guard를 별도 출력 경로로 사용한다.
같은 실행 이름의 증거는 덮어쓰지 않는다. Flutter 명령은 동일 build directory를 공유하므로
서로 순차 실행한다. 최초 별도 HTTP 실행의 native-assets 충돌 로그도 보존한다.

```bash
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py backend-calibration
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py flutter-independent
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py backend-full
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py flutter-full
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py flutter-calibration
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py independent-http-serial
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py authority
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py overhead-python
.venv/bin/python docs/benchmarks/t66f-b03-independent/run.py overhead-flutter
```

이미 존재하는 이름은 새 campaign 이름으로 명시 등록해야 한다. 성공 로그는 gzip 원문/JUnit으로
보존하며 실패할 때만 tail을 출력한다. 합성 fixture와 임시 SQLite만 사용한다. 운영 DB·Snapshot·
`.env`·API 18080·서비스·APK 설치·배포·segmented activation은 사용하지 않았다.

논리 hash/validation/write와 HTTP entity, SQL bind, NEW row, DB/WAL 크기 및 physical I/O는
서로 다른 지표다. 이 디렉터리는 five-point cost grid·100k cold 재실행·R1·Android VFS/power proof가 아니다.
