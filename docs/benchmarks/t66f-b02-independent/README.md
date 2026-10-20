# T6.6F-B02 독립 감사 재현 자료

대상은 `1cabf319f0ac2c2069e804b47cb527b55e3374db`이며 제품 소스를 바꾸지 않는다.
모든 데이터·인증·TLS·SQLite는 disposable synthetic fixture다. production API/DB를 사용하지 않는다.

## 증거 경계

- `inventory.json`: 시작 HEAD, clean 상태, index와 원 tracked 2,041개 파일 SHA.
- `executed-sources/`, `executed-source-sha256.json`: formatting 전 실제 실행한 harness 원문.
- `evidence/{1000,50000,100000}/`: 실제 loopback TLS HTTP·client·독립 read-only oracle·새 프로세스 결과 gzip.
- `summary.json`: 원 trace 재집계. `summarize.py`로 재생성한다.
- `execution-*.json`: 외부 process exit, 시간·15초 RSS 표본·resource guard. 내부 client timer와 구별한다.
- `final-state.json`: accepted pointer checksum, receipt, DB integrity, usage, DELETE journal read-only 재검사.
- `flutter-full.jsonl`, `backend-full.xml`, `*.exit`: 실제 전체 회귀. `flutter-by-file.json`은 hidden setup/loading을 제외한다.
- `*-diagnostic/`: 감사 harness 초기 import·fixture oracle·package context 오류를 지우지 않고 보존했다. 제품 결함이나 최종 PASS count에 섞지 않는다.

## 소형 독립 검사

저장소 root에서 Python 검사를 수행한다.

```sh
PYTHONPATH=backend:docs/benchmarks/t66f-b02-independent .venv/bin/python -m pytest -q docs/benchmarks/t66f-b02-independent/test_backend.py
```

`mobile/`에서 Dart 검사를 수행한다.

```sh
flutter test --no-pub --concurrency=1 ../docs/benchmarks/t66f-b02-independent/e2_audit_test.dart ../docs/benchmarks/t66f-b02-independent/budget_test.dart ../docs/benchmarks/t66f-b02-independent/cross_layer_test.dart
```

이 세 Dart 파일은 34개 E1/E2/budget 검사 및 9개 cross-layer 검사를 포함한다.
backend의 26 parameter 실행에는 C1 old/new 2,013입력 × 2함수 differential 한 건이 포함된다.
기존 strict resolver는 `git show` 결과를 별도 module로 읽는다. 현재 checkout을 덮어쓰지 않는다.

## 실제 대규모 경로

`run_campaign.py smoke`는 1k 전체 경로다. `large`는 선행 `backend-full.exit`,
`flutter-full.exit`, `smoke.exit`가 모두 0인지 확인한 후 50k와 100k를 순차 실행한다.
저장된 이전 exit 파일만 보고 현재 환경이 재검증됐다고 해석하지 말아야 한다.
재실행 시 새로운 evidence 디렉터리/checkout에서 사용하여 이 감사의 원시 증거를 덮어쓰지 않는다.

```sh
.venv/bin/python docs/benchmarks/t66f-b02-independent/run_campaign.py smoke
.venv/bin/python docs/benchmarks/t66f-b02-independent/run_campaign.py large
```

large는 여유 RAM >12GiB, 임시 디스크 >8GiB를 요구한다. 각 실행 7,200초,
process-tree RSS 8GiB, free disk 2GiB의 외부 guard를 둔다. product의 900초 TTL,
3 observations, 3 request attempts, 64-object/1MiB packet은 그대로다.
외부 guard 종료는 `external_termination`으로 구분하며 application expiry로 보고하지 않는다.
새 DB·cert/key는 `/tmp/mn-b02-independent-*`에만 만들며 DB/인증서/키/APK를 Git에 포함하지 않는다.

독립 oracle는 Python stdlib JSON 재인코딩과 SHA256 framing, 자체 typed-child parser,
backend 원천 SQL rows, wire 원문, client read-only SQLite를 대조한다. 금융 계산식을 재구현하지 않는다.
transport/seed/server lifecycle 일부는 기존 synthetic harness를 재사용한다. 이를 독립적인
금융 계산 엔진이나 완전히 별개의 fixture generator로 표현하지 않는다.

## 계측 해석

HTTP 수치는 ASGI request/response entity이며 TLS/TCP·HTTP header 전체 wire bytes가 아니다.
`sql_execute_tokens`는 request context의 명시적 `RetentionConnection.execute` 호출이다.
SQLite trigger 내부 VM step이나 physical I/O와 다르다. store `object_reads`,
`transactions`, `verified_bytes`는 구현 counter이므로 독립 SQL byte accounting으로 바꾸어 부르지 않는다.
client RSS는 flutter_tester/Dart VM/harness/E1/E2/E3/E4를 포함한다. tree RSS는 child backend와
fresh Dart child 등을 더한 표본이며 shared page를 중복 셀 수 있다. Android memory proof가 아니다.

`.dart_tool/package_config.json`은 분석용 generated 파일이고 Git에서 제외한다. 외부 docs Dart
분석을 재현할 때 mobile의 package config를 복사하고 각 rootUri를 원 config 기준 absolute URI로
변환한다. 제품 `flutter analyze`는 별도로 mobile에서 실행했다.

전체 Phase B logical hash/validate/write bytes, Android VFS/I/O·hardware power-loss 및
R1/activation 요구는 이 증거로 완료되지 않는다. 자세한 판정은 독립 감사 보고서를 따른다.

Flutter analyze/build의 plain log만 terminal trailing spaces를 정리했다. byte-exact 원 출력은 같은 이름의 `.log.gz`에 보존한다. 첫 diff-check 진단도 별도 보존했다.
