# 격리된 payload 진단

이 디렉터리는 제품 startup/배포 경로에서 호출하지 않는 synthetic 진단 도구다.
T6.6A의 측정 계약·결과·한계는 [보고서](../../docs/t66a-payload-attribution.md)에 둔다.
기존 DB 입력은 받지 않으며 `MONEY_NOTE_*`를 제거한 뒤 임시 migrated DB를 생성한다.
큰 body와 DB는 Git에 넣지 않는다. 아래 `T66A_DIR`에는 `mktemp -d` 결과를 사용한다.

```bash
T66A_DIR=$(mktemp -d /tmp/mn-t66a-XXXXXX)
.venv/bin/python -m pytest -q scripts/benchmarks
.venv/bin/python scripts/benchmarks/t66a.py generate --output "$T66A_DIR"
.venv/bin/python scripts/benchmarks/t66a.py memory --output "$T66A_DIR"
```

별도 터미널에서 같은 디렉터리로 local-only HTTP wrapper를 시작한다.
`127.0.0.1:18081`이 이미 사용 중이면 기존 서비스를 중단하지 말고 이 진단을 중단한다.

```bash
.venv/bin/python scripts/benchmarks/t66a.py serve --output "$T66A_DIR"
```

모바일 checkout에서 실행한다. 첫 실행은 HTTP를 제외한 frozen-body 단계 측정,
둘째는 HTTP 측정이다. 둘째 명령의 `--plain-name`은 중복 단계 측정을 피한다.

```bash
flutter test --reporter expanded --dart-define=T66A_OUTPUT="$T66A_DIR" test/diagnostics/t66a_payload_test.dart
flutter test --reporter expanded --dart-define=T66A_OUTPUT="$T66A_DIR" --dart-define=T66A_HTTP=true --plain-name='actual IOClient' test/diagnostics/t66a_payload_test.dart
```

Wrapper는 Ctrl-C로 종료한다. 저장소 root에서 집계한다.

```bash
.venv/bin/python scripts/benchmarks/summarize_t66a.py --output "$T66A_DIR"
.venv/bin/python scripts/benchmarks/t66a.py native --output "$T66A_DIR"
.venv/bin/python scripts/benchmarks/t66a.py large --output "$T66A_DIR"
.venv/bin/python scripts/benchmarks/t66a.py export --output "$T66A_DIR"
.venv/bin/python -m ruff check scripts/benchmarks
git diff --check
```

`--quick`은 smoke용 2 sample이며 최종 통계로 사용하지 않는다.
최종 측정은 각 fixture/codec/단계 warmup 3회 + 관측 20회다.
RSS는 별도 child 1회의 거친 high-watermark이며 allocator peak가 아니다.
일반 `flutter test`에서는 `T66A_OUTPUT`이 없으므로 두 진단은 skip된다.
`native`는 같은 port에서 실제 Uvicorn/FastAPI의 raw HTTP header/entity를 별도로
3회 확인하고 즉시 종료한다. `large`는 선택적 50k probe이며 2GiB address-space,
90 CPU-second ceiling을 자체 설정한다. 추가로 `timeout 120s`를 붙일 수 있다.
50k route는 1회이며 compression 관측도 1회이므로 tail 통계로 해석하지 않는다.
보존된 synthetic specimen은 `compare --specimen /tmp/.../new-10000.json`으로
분석할 수 있다. 해당 원문이 소실되어도 주 fixture 생성/측정은 영향받지 않는다.
HTTP wrapper는 테스트 URL만 바꾸며 실제 `MoneyNoteApiClient`/`IOClient` 및
B-2 parser/OfflineStore를 그대로 사용한다. `/actual/376/...`은 실제 FastAPI
handler를 호출하되 fixture의 synthetic session으로 인증하고, 나머지는 captured
원문 body를 전송한다. 이는 운영 reverse proxy 또는 TLS의 측정이 아니다.
압축을 제품에 켜거나 financial 계산·프로토콜·저장 형식을 바꾸지 않는다.
