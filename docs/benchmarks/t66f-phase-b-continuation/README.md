# T6.6F Phase B 후속 독립 검증

시작 commit은 `a08b91d9625ad685cea9ab8d0e977849a097f0ab`다. 최종 판정은
`docs/t66f-phase-b-continuation.md`를 따른다. 이 디렉터리는 합성 감사 자료만 포함한다.
제품·원 assertions·과거 FAIL/INCONCLUSIVE 보고서를 변경하지 않는다.

## 실험과 oracle

`grid.py`는 실제 backend generation/finalizer, 실제 loopback TCP HTTP handler와 별도
SQLite body 조회를 사용한다. seed 662602, 평가일 2026-10-05, current ledger 105개를 고정하고
전체 ledger N을 1k/5k/10k/50k/100k로 확장한다. 참조·설정·정책 working set도 고정한다.
각 no-change/card/cash에 warmup 3회와 측정 20회를 구분한다. 카드·현금의 두 값 전환은
**ABA/immutable 재사용 workload**다. 이 결과를 매번 새 bytes를 만드는 workload로 부르지 않는다.

실제 full backend bundle의 gzip6/Brotli4는 별도의 **오프라인 압축 비교**다. HTTP에 compression을
추가하지 않는다. 원시 canonical object bytes, base64 포함 entity, header field 크기를 구분한다.
header field 합은 status line/TLS/IP framing을 포함한 packet bytes가 아니다. backend Meter의
반환 행과 BLOB 길이는 SQLite VM 단계·pager I/O가 아니다. `bound_blob_bytes`는 실제 물리 쓰기량이
아니며, `sync_pins` 문자열 카운터는 실제 observation pin table을 포괄하지 않아 pin oracle로 쓰지 않는다.

`unique_server.py`/`unique_cost_test.dart`는 별도 H=현재 ledger 1개 및 고정 참조 profile로
정확한 전체 N=1k/5k/10k를 만든다. 매번 새로운 고정 폭 금액 D=1을 사용한다. 이는 금융 계산을
복제하지 않고 실제 backend writer/finalizer를 통과한다. backend가 새 immutable object를
만들고 실제 Flutter client가 object request를 보내는 것을 각각 assertion으로 확인한다.
초기 객체는 E1 `VerifiedObject.verify`로 개별 검증한 **측정 밖 cache fixture**로만 준비한다.
accepted/receipt/generation/source/pending은 직접 삽입하지 않는다. 원 AppState ticket과 실제
HTTP/E2/E3/E4를 통해 최초 accepted를 만든다. cache 준비를 cold acquisition 성능으로 보고하지 않는다.

`cost_test.dart`의 기존 history 인수 1000/5000/10000은 실제 ledger 1001/5001/10001이다.
이 세 추가 ABA 측정은 정확한 의무 N grid와 구별한다. 최초 1001행만 실제 cold object transfer다.
서버 clock이 fixture에서 고정되므로 이 긴 cold 실행을 실제 TTL 내 완료 증명으로 사용하지 않는다.

`measure.py`는 검증된 독립 native SQLite delegate를 **폐기용 제품 source copy**에만 연결한다.
실제 statements/반환 행/BLOB bytes/generation-root pin I/D/U를 센다. full verification 함수 진입도
임시 copy에서 관찰한다. 이것은 제품이 제공하는 work counter를 읽는 방식이 아니다.
오라클용 full graph/full legacy 조회는 비용 구간 밖이다. source observer 원본은
`docs/benchmarks/t66e3-audit/audit_trace.dart`다. full-copy method는 기존 독립 E4 감사와 같다.

`adversarial_test.dart`와 `lineage_test.dart`는 실제 TLS HTTP 및 원 AppState ticket을 사용한다.
독립 SQL과 workspace 파일의 accepted/source/B/pending/pins를 비교하며, frozen 재읽기는 별도
프로세스에서도 수행한다. Content-Type 진단은 거부를 요구하는 실험 assertion 자체를 보존한다.
이 1건의 실제 FAIL과 binding contract에 MIME 거부 규칙이 없다는 해석을 함께 기록한다.
거부 rule을 새로 추가하거나 실패를 PASS로 바꾸지 않는다.

`test_identity.py`는 실제 backend handler/repository에 결정적 authentication/serialization/terminal
barrier를 둔다. disposable DB A를 같은 논리 namespace의 B로 교체하고 각 원본 파일을 별도 SQLite로
검사한다. 새 DB의 전체 행, permit 및 financial digest를 대조한다. 일반 runtime DB 교체 지원을
활성화한다는 뜻이 아니다.

## 재현

아래는 모두 개발 checkout에서 실행하며 output에 새 `/tmp` 디렉터리를 사용한다.
`grid.py`의 bootstrap/전체 oracle는 비용 측정 구간과 분리한다. 큰 두 grid의 client는 현 E2
supported maximum 100,000 objects를 넘으므로, 이 제한을 올리거나 제품을 고치지 않는다.

```bash
.venv/bin/python docs/benchmarks/t66f-phase-b-continuation/grid.py --help
.venv/bin/python docs/benchmarks/t66f-phase-b-continuation/run_grid.py /tmp/mn-cont-new 1000 5000 10000 50000 100000
COST_N=1000 COST_TEST=unique_cost_test.dart .venv/bin/python docs/benchmarks/t66f-phase-b-continuation/measure.py /tmp/mn-cont-new/unique-1000
COST_N=5000 COST_TEST=unique_cost_test.dart .venv/bin/python docs/benchmarks/t66f-phase-b-continuation/measure.py /tmp/mn-cont-new/unique-5000
COST_N=10000 COST_TEST=unique_cost_test.dart .venv/bin/python docs/benchmarks/t66f-phase-b-continuation/measure.py /tmp/mn-cont-new/unique-10000
C_IDENTITY_OUTPUT=/tmp/mn-cont-new/identity .venv/bin/python -m pytest -q docs/benchmarks/t66f-phase-b-continuation/test_identity.py --junitxml=/tmp/mn-cont-new/identity.xml
cd mobile
flutter test --no-pub --machine --dart-define=CONTINUATION_OUTPUT=/tmp/mn-cont-new/negative.json --name '^C-N-' ../docs/benchmarks/t66f-phase-b-continuation/adversarial_test.dart
flutter test --no-pub --machine --dart-define=CONTINUATION_OUTPUT=/tmp/mn-cont-new/authority.json --name '^C-(A|I)-' ../docs/benchmarks/t66f-phase-b-continuation/adversarial_test.dart
flutter test --no-pub --machine --dart-define=CONTINUATION_OUTPUT=/tmp/mn-cont-new/lineage.json ../docs/benchmarks/t66f-phase-b-continuation/lineage_test.dart
cd ..
.venv/bin/python docs/benchmarks/t66f-phase-b-continuation/checks.py /tmp/mn-cont-new/checks backend-full
.venv/bin/python docs/benchmarks/t66f-phase-b-continuation/checks.py /tmp/mn-cont-new/checks flutter-full
```

`profile_test.dart`의 `C_BUDGET_WITNESS`/`C_MONEY_GOLDEN`은 수집된 JSON 경로를 받는다.
`graph_budget.py`는 자신이 소유한 측정 DB만 읽는다. `collect.py`는 raw machine/JUnit/측정 JSON을
압축·해시 보존하고, 기존 회귀와 새 unique test ID를 구분한다. 샘플 20개는 empirical p95이며
tail의 통계적 보증이 아니다. cold 1회로 median/p95를 만들지 않는다.

`evidence/executed-sources/`는 실제 실행된 형식 정리 전 소스도 보존한다. 최종 소스에서는
미사용 import 및 측정 밖 미사용 raw-table 변수 제거와 formatter만 적용했다. 실패한 초기 감사
fixture/진단 로그도 숨기지 않는다. 이전 correctness assertions는 전혀 수정하지 않았다.

HOST synthetic 측정이다. Android VFS/I/O·전원 손실·실기기 throughput·R1 완료·production 성능
증거로 사용하지 않는다. APK를 설치하거나 segmented 기본 경로를 활성화하지 않는다.
