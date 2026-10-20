# B02-A01 교정 증거

독립 감사가 아닌 구현자 검증이다. 원 dirty B02와 원 A01 조사 디렉터리는 변경하지 않는다.
`summary.json`은 완료된 결과와 진행 중 결과를 구분한다. `.gz`는 새 runtime 로그의 원 bytes다.
private TLS key·credential·전체 DB는 이 디렉터리에 수집하지 않는다.

## 재현 entry point

저장소 root에서 backend 테스트:

```sh
cd backend
../.venv/bin/python -m pytest -q tests/test_isolated_sync_prefix_reuse.py
```

모바일 root에서 전후 packet 비교 및 source isolation:

```sh
flutter test --no-pub test/segmented_cold_packet_test.dart test/segmented_adapter_isolation_test.dart
```

같은 보존 sample로 backend prefix component3회씩 비교:

```sh
.venv/bin/python docs/benchmarks/t66f-b02-a01-correction/prefix_benchmark.py
```

실제 TLS D→E는 `run_http.py 1000`, `run_http.py 50000`, `run_http.py 100000` 순서다.
각 실행은 새로운 `/tmp/mn-a01-corrected-N-*` DB를 만들며 최대7200초 외부 guard를 둔다.
이는 server observation의900초/3회와 다르다. 같은 N의 기존 campaign pointer가 있으면 무근거
반복을 거부한다. 독립 검증자는 원 pointer를 지우지 말고 새로운 증거 경로와 빈 temporary out을
명시하여 `full_http_test.dart`를 직접 실행해야 한다. 50k가 실제 통과하기 전에는100k를 실행하지 않는다.

첫50k에서 관측한 cached cursor 수명 결함의 source/실패 결과를 보존한 뒤, `cursor-lifetime` tag로만
해당 교정 revision을 별도 재검증한다. 예: `run_http.py 50000 cursor-lifetime`.
최초 실패 pointer와 압축 evidence는 그대로 두며 새 tag도 같은 이름으로 두 번 실행하지 않는다.

## 보존·오라클

- `initial-state.json`: 시작 refs/index/1,549개 파일 SHA. 최초 생성 후 덮어쓰기 거부.
- `original-worktree.diff.gz`, `fetch.dart.before.gz`, `transfer.py.before.gz`: 교정 전 실제 bytes.
- `before_fetch.dart`: 교정 전 알고리즘을 그대로 사용한 TEST-ONLY 비교본(import 위치·설명·formatter만 변경).
- `fetch.dart.failed-cursor.gz`: 실제 첫50k에서 실패한 revision의 정확한 bytes.
- `failed_cursor_fetch.dart`: 그 revision의 COUNT guard만16으로 주입한 compact 재현(PATH512 유지).
- `release-artifacts.before.json.gz`: 사용자 승인 이전의 exact 현재 release bundle 원본.
- `artifact-review.json`: transfer source 하나만 달라진 engine 및 불변 schema/policy/version 확인.
- `source-lock-review.json`: 변경된 extension만 새 exact revision으로 고정. 과거 default SHA는 그대로 검사.
- `prefix-performance.json`: 동일 fixture에서 실제 resolver/SQL trace/validation 호출 수. 전체 byte gate 아님.
- `http-N-*.gz`: 실제 TLS 응답/요청 메타데이터와 canonical backend/E4 value digest, recovery 결과.

신규 실패 로그에는 초기 테스트 작성 오류도 포함한다. API·BLOB fixture·schema 이름을 수정한 뒤
최종 테스트를 다시 실행했으며, 실패를 제품 PASS에 합산하지 않는다. 두 잘못된/비효율적인 새
테스트 실행의 외부 중단은 실제 observation 만료나 제품 crash로 분류하지 않는다.

## 경계

backend prefix counter의 canonical bytes는 Python heap이나 전체 hash/validate byte gate가 아니다.
E1 operation/fault counter는 물리 디스크 write amplification이나 모든 SQL rows-scanned 증거가 아니다.
host RSS는 Android 안전성 증거가 아니다. SIGKILL은 hardware power-loss 증거가 아니다.
R1은 CLOSED이며 Phase B의 전체 cost accounting과 독립 targeted audit가 남는다.

`verify_reads.dart`는 완료한 store의 새 process에서 hot/control hash와20회 accepted logical read를
검사한다. Snapshot/legacy Frozen-B 설치나 general-user Offline 준비 증거로 확대하지 않는다.

완료/실패한 새 runtime에서 `summarize_campaign.py OUT`을 실행하면 cold observation별
packet·HTTP entity·resolver·SQL 계수를 `cold-summary.json`으로 만든다. 최초 cold stage 수로
뒤의 identical/delta observation을 분리한다. Failed HTTP 요청의 resolver 내부 계수는 성공 응답
metrics와 달리 누락될 수 있으므로 이를 모든 실패 작업까지 포함한 전층 logical byte 총량으로
부르지 않는다. `collect.py RUNTIME`은 이 요약과 새 post-read 결과를 함께 압축 보존한다.

Shared64 component의 전체 validation은1,206→141회다. 이 중 terminal64회는 양쪽 모두
엄격히 유지되므로 nonterminal prefix만 분리하면1,142→77회다. 서로 다른 정의를 섞지 않는다.

대형 하네스의 `legacy_pending` 보호 key는 실제 protected 파일인 OfflineBaseline과
PendingOnlineWrite marker를 뜻한다. Frozen B/J journal·native frozen source를 이 하네스에서
새로 만든 것은 아니다. 해당 실제 B/J·영구 frozen 경계는 기존 E4 회귀 결과와 구분한다.
