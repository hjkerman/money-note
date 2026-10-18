# 후속 논리 byte 계측 경계

이 문서는 계획이다. 현재 B02에서 아래 전층 counter를 모두 측정했다고 주장하지 않는다.

|경계/실제 위치|test-only 독립 hook|정의와 중복|oracle·overhead|
|---|---|---|---|
|Backend `canonical.py:hash_bytes`, `Object.make`, `row_hash`; `facts.py`/`patricia.py`|hashlib delegate의 update/digest 입력을 계수하고 fixture별 별도 observer와 비교|domain prefix+NUL+실제 raw preimage 길이; 같은 bytes를 두 번 hash하면 두 번 센다. encode 출력 길이와 같다고 추정하지 않는다|표준 SHA와 root exact equality; 호출당 정수 덧셈과 표본 histogram|
|Backend `canonical.py:decode_c1`/`decode_json`, graph/row validators|decoder와 validator 진입 경계를 분리해 test decorator|canonical decode 입력과 구조 validator 처리 범위를 별도 기록; 중첩 호출의 inclusive/exclusive counter를 구별|독립 C1/typed walk·원 금융 oracle; double-count 경계 공개|
|Backend `store.py:Store.put`, finalizer/observation metadata SQL|실제 connection delegate에서 bind BLOB/TEXT bytes와 transaction outcome 관찰|신규 object INSERT body, receipt/manifest/root write의 logical bind bytes. 시도/rollback/known committed를 나눔; UPDATE가 같은 값을 쓰는 경우도 시도량에 포함|별도 SQLite diff와 row SHA; 반환 SELECT BLOB 길이는 write로 사용 안 함|
|D3 `transfer.py:TransferRepository`·ASGI send|실제 response entity capture + 독립 base64 decoding|HTTP JSON/entity bytes, decoded chunk bytes, 요청/응답 header field bytes를 각각 기록. TLS/IP packet bytes와 다름|parent Ref/offset·raw SHA; 캡처 자체 buffering overhead를 performance 실행과 분리|
|E1 `c1.dart:objectHash/localChecksum`, `object.dart:VerifiedObject.verify` 및 `body` getter|테스트용 source copy 또는 동일 호출을 연결한 instrumentation build에서 hash sink/decoder delegate 관찰|hash 입력 preimage, C1 decode/encode 및 row/shape validation 입력을 서로 다른 counter로 계수. get/put/record가 같은 object를 재검증하는 실제 중복도 포함|원본과 exact bytes/root 및 오류 동등성 검사; source copy는 제품 불변 SHA와 계측 diff 공개|
|E1 `store.dart:putVerifiedObject/_read/_transaction`|native SQLite delegate에서 실제 bind값 byte length 및 COMMIT/ROLLBACK 분류|object/manifest/metadata의 logical submitted write bytes; attempted와 committed 분리. metadata fixed charge는 bytes written 아님|새 연결 usage·objects/refs/edges/pointer exact 검사; SQL tracing 비용 별도 표본|
|E2 `fetch.dart` chunk assembly/graph loader|transport observer + 위 E1 sink를 acquisition phase tag로 집계|downloaded chunk bytes/cache-read bytes/validator bytes 구분. `metrics.payloadBytes`만을 independent counter로 사용 안 함|실제 D3 output과 expected missing reachable set; 중첩 E1 수치와 더하지 않음|
|E3 `verification.dart`/`patricia_edit.dart`/`store_publication.dart`|fact-key/row/index root hash sink + receipt/root pin SQL delegate|새 fact bytes, 변경 frontier validation, receipt·accepted pointer logical writes. cold/fallback과 healthy delta를 분리|backend F(raw) root, original-ticket guard, separate accepted SQLite oracle|
|E4 `store_read.dart`, `store_frozen.dart`, `workspace.dart`, `adapters.dart`|hash-on-read/legacy materialization/frozen provenance phase tag + file-write delegate|healthy hot/control bytes와 cold full v7/B encode/hash/readback bytes 분리. Snapshot fingerprint preimage와 sync_root preimage를 구별|기존 frozen v7/OfflineBaseline lineage·pending bytes exact equality; 정상 pin write 0 검사|

한 연산의 inclusive 합과 하위 phase 합을 다시 더하지 않는다. `actual_loader_body_bytes`는
B02 read-only loader가 validator에 넘긴 BLOB 길이일 뿐, 모든 hash/validate 횟수를 반영하지 않는다.
`canonical_bytes`는 unique stored payload 합이고, DB/WAL/file 증가·pager physical I/O·fsync 횟수와
다르다. byte 추적 빌드와 latency 빌드는 overhead를 명시해 분리한다. source-copy hook에는 기존
negative/monetary/authority 회귀와 trace-on/off 출력 동등성이 먼저 필요하다.
