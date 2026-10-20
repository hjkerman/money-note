# T6.6F Phase B 최종 감사 재현 자료

대상 제품은 `1cabf319f0ac2c2069e804b47cb527b55e3374db`, 시작 감사는
`ae0f37250c8f54893cb2ac5eab1d3c9844a7d983`다. 제품 소스·프로토콜을 변경하지 않는다.
최종 판정은 INCONCLUSIVE이며 full logical-byte grid를 측정했다고 주장하지 않는다.

- `inventory.json`: 첫 clean ref 확인 뒤 시작 tracked 2251개 SHA, B02 기존 2041개 대조,
  원 감사 이후 commit별 전체 inventory. 출력 시점의 새 untracked 감사 파일도 따로 명시한다.
- `coverage.json`/`coverage.csv`: 39절/25 invariant/34 negative/12 proof/13 최종 gate의 123행.
- `instrumentation.md`: counter 정의·overlap·calibration·실제 Dart seam 부재와 사용자 §14 stop rule.
- `counters.py`/`test_counters.py`: 실제 Python C1/Store의 좁은 test-only 관측과 독립 calibration.
- `reconcile.py`: 기존 raw HTTP를 재합산하고 fixture·root pin·cold/restart scope·20개 분포를 확인한다.
  50k/100k의 새 network 실행이 아니다. `reconcile-diagnostic-*`는 감사 도구 초기 가정 오류다.
- `overhead.py`: Python Object constructor 1000회의 paired observer overhead. 앱 latency가 아니다.
- `run_checks.py`: 실제 full suites/build/static 명령, 7200초/8GiB RSS/free disk2GiB guard·exit·gzip log.
- `finish.py`: 이번 캠페인의 실제 종료 자료를 읽어 보고서를 작성한 도구. 역사 보고서에 재실행하지 않는다.
- `executed-sources/`: formatting 직전 감사 Python 원문. AST 동등성은 `format-equivalence.json`에 있다.
  이 archive는 product source-copy instrumentation build가 아니다. 새 출력 설명·coverage metadata가
  추가된 최종 파일은 Git commit으로 식별하며 과거 full-run command/function은 변경하지 않았다.

현재 `validation_completed_input_bytes`는 `_parse_json`의 정상 전체 UTF-8/JSON 입력이다.
전체 typed/raw/facts/receipt/hashing 비용 합계가 아니다. INSERT 관측기도 BLOB/TEXT positional
VALUES subset이며 trigger·UPDATE·prepared statement 전체 payload가 아니다. `verified_bytes`,
HTTP bytes, canonical unique size, metadata charge 또는 DB size로 이 누락분을 채우지 않는다.

## 안전한 재현

기존 폴더의 evidence를 덮어쓰지 않는다. 개발 checkout 안에 **새 이름의** 감사 폴더를 만들고
필요한 Python 도구와 `evidence/`를 복사한 뒤 같은 디렉터리 깊이에서 재현한다. 아래 `REPLAY`
경로는 반드시 아직 없는 이름으로 선택한다. production DB·credential·Snapshot은 사용하지 않는다.

```bash
cd /home/hjkerman/codex/money-note
set -e
REPLAY=docs/benchmarks/t66f-phase-b-final-replay
mkdir "$REPLAY"
mkdir "$REPLAY/evidence"
cp docs/benchmarks/t66f-phase-b-final/counters.py "$REPLAY/"
cp docs/benchmarks/t66f-phase-b-final/test_counters.py "$REPLAY/"
cp docs/benchmarks/t66f-phase-b-final/reconcile.py "$REPLAY/"
cp docs/benchmarks/t66f-phase-b-final/overhead.py "$REPLAY/"
PYTHONPATH="backend:$REPLAY" .venv/bin/python -m pytest -q "$REPLAY/test_counters.py" --junitxml="$REPLAY/evidence/calibration.xml"
.venv/bin/python "$REPLAY/reconcile.py"
PYTHONPATH="backend:$REPLAY" .venv/bin/python "$REPLAY/overhead.py"
```

`inventory.py`는 최초 BASE HEAD를 요구하는 일회성 시작 기록 도구다. `finish.py`는 이번 보고서의
소유 작업 중에만 사용했다. 재현 폴더에서 역사 보고서를 대상으로 실행하지 않는다. full suites가
필요하면 새 출력 경로의 runner를 사용하고 새 exit를 기다려야 한다. 이전 완료 JSON만으로
새 PASS를 주장할 수 없다. 50k/100k cold campaign은 이 재현 명령에 포함하지 않았다.

전체 backend/Flutter의 성공 로그는 gzip으로만 보존한다. main test/subtest 및 hidden
loading/setup·skip을 분리하며 숫자를 중복 합산하지 않는다. debug APK는 build만 하고 설치하지 않는다.
최종 SHA/네 ref/clean 결과는 report의 Git 식별 명령과 종료 사용자 응답으로 확인한다.
