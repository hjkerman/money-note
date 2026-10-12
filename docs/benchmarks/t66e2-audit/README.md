# T6.6E2 독립 감사 재현

대상은 `69a8fd15b581357ef4be859fec03525bd6070fb4`, 기준은
`bd3a7e08c5b810c8c30d26e498d1994218b33b71`이다. 제품 구현을 수정하지 않는다.
모든 데이터베이스는 `RetentionSandbox` 또는 pytest 임시 디렉터리에 새로 만든다.
production 경로, API, credential, 실제 금융 데이터는 사용하지 않는다.

## 독립 oracle

- `audit_backend.py`: 실제 D1/D2b/D3a/D3b/D3c를 새 synthetic DB에서 실행한다.
  임의 credential은 private pipe로만 전달하며 evidence에 저장하지 않는다.
  서버 helper의 reachability 결과를 기대 집합으로 사용하지 않는다. 직접 SQLite
  BLOB을 읽어 Python JSON C1, hashlib domain hash, 명시적인 typed edges로 순회한다.
  11개 raw table의 실제 행과 leaf를 비교하고 받은 facts로 Patricia를 독립 재구성한다.
- `worker.dart`: 제품 transport/fetch/store를 호출하는 독립 HTTP client다.
  실제 ASGI bridge 또는 서버에서 얻은 fixture를 사용한다. 요청 method/path/body,
  status, byte 수와 credential 일치 여부만 기록한다. credential 원문은 기록하지 않는다.
  negative cases에서는 protocol, context, hash, graph, quota, cancellation을 변형한다.
- `test_audit.py`: fresh Python SQLite connection으로 BLOB, domain hash, staging의
  정확한 참조 집합, checksum, accounting, FK/integrity, write-lock 해제와 활성 pointer
  부재를 확인한다. 7개 barrier에서 실제 Dart child에 SIGKILL을 보내고 별도 process로
  reopen/resume한다. 잘못된 단계의 오류를 성공으로 세지 않도록 negative 오류 code도
  검증한다. 실행별 fixture 파일을 분리한다.

실제 ASGI 검증은 private subprocess/TestClient 통합이며 TLS socket 성능 검증이 아니다.
추가 `native_transport.dart`는 임시 자체 서명 인증서와 실제 loopback HTTPS/IOClient로
header 거부 뒤의 연결 누수를 재현한다. 정상 응답 대조군과 6회 public acquire 누적을
검증한다. `-k native`로 이 5개를 별도 실행할 수 있으며 현재 4 FAIL이 확인되는 결함 증거다. 교정 후에는 assertion을 그대로 통과해야 한다.
동일 Target 계수를 위해 합성 서버의 무작위 Judgment 문구 선택만 고정한다. backend의
금융 계산, canonical/hash, auth, lease, publication과 transfer는 실제 구현을 사용한다.
새 corpus는 74개 독립 시나리오다. 69개 기본 사례는 PASS였으며, 새 실제 IOClient
대조군 1개는 PASS, native cleanup 재현 4개는 FAIL이다. E2-A01을 보존한 failing tests를
xfail하거나 약화하지 않았다. 최종 수치와 각 시나리오 결과는 `summary.json`에 있다.

## 재현 명령

checkout에서 기존 Python/Flutter toolchain과 dependencies를 사용한다.
추가 설치나 서비스 실행은 필요 없다. Dart 경로는 필요하면 `DART` 환경변수로 지정한다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66e2-audit/test_audit.py -k 'not native' --junitxml=/tmp/mn-e2-audit/independent.xml
.venv/bin/python -m pytest -q docs/benchmarks/t66e2-audit/test_audit.py -k native --junitxml=/tmp/mn-e2-audit/native.xml
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py docs/benchmarks/t66e1-a01-a02-reaudit/test_reaudit.py --junitxml=/tmp/mn-e2-audit/e1.xml
cd mobile
flutter test --no-pub --machine
flutter analyze --no-pub
dart format --output=none --set-exit-if-changed lib test
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=https://independent.synthetic
cd ../backend
../.venv/bin/python -m pytest -q --durations=10 --junitxml=/tmp/mn-e2-audit/backend.xml
cd ..
.venv/bin/python -m pytest -q scripts/tests --junitxml=/tmp/mn-e2-audit/safety.xml
.venv/bin/python -m pytest -q scripts/benchmarks --junitxml=/tmp/mn-e2-audit/diagnostics.xml
.venv/bin/ruff check backend/app backend/isolated_sync backend/tests scripts/local_deploy.py scripts/tests docs/benchmarks/t66e2-audit
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts docs/benchmarks/t66e2-audit
npm --prefix frontend test
npm --prefix frontend run build
git diff --check
```

stdout/stderr 상세 로그와 시험 DB는 `/tmp/mn-e2-audit` 및 pytest 임시 경로에 둔다.
성공 로그 전체를 report에 복사하지 않는다. 중단된 backend 실행은 집계에서 제외하고
완료된 재실행만 계수한다. 전체 Dart formatting에서 기존 파일 10개가 formatter와
다르지만 모두 baseline과 byte가 같다. E2 변경 Dart 파일 13개는 통과했다.

7개 SIGKILL 시나리오는 manifest 수신, 응답 중간, 검증 후 insert 전, object COMMIT 후,
staging-object INSERT 중, graph_verified UPDATE/INSERT transaction 중, API return 전이다.
SIGKILL resume에는 서버 fixture를 사용하는 mock authority를, 실제 ASGI resume에는
reopen과 실제 retired-observation 410 처리를 사용한다. 둘을 동일한 실험으로 주장하지
않으며 OS crash 또는 hardware power-loss durability를 주장하지 않는다.
