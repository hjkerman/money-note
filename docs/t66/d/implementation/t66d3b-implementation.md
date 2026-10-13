# T6.6D3b 구현 보고서

이 문서는 격리된 authenticated manifest/object transfer 구현과 내부 검증을 기록한다. 독립 D3b 감사와 production 활성화 승인을 대신하지 않는다. 규범 원본은 [T6.6C](../../c/t66c-delta-sync-protocol.md) §4, §7–11, §15–17이다.

## A. 시작 Git 검증

시작 branch는 `main`이며 HEAD, local main, origin/main, 실제 remote main은 모두 `9f9a94c03ff43c6d87e77e1dc2c30a30080cf71b`였다. Working tree는 clean이었다. 실제 parent는 `c6ce6d9f84633b24a2f43330a90487ca16d0b3c4`다. Reset이나 다른 revision으로의 전환 없이 작업했다.

## B. 변경 파일 목록

| 파일 | 변경 목적 |
| --- | --- |
| `backend/isolated_sync/http.py` | 명시적으로 구성하는 격리 ASGI app, 기존 인증 선택, ticket, terminal guard, HTTP 오류 |
| `backend/isolated_sync/transfer.py` | typed-path 인가, 방문 object/edge 검증, exact chunk, request budget |
| `backend/isolated_sync/artifacts.py` | release artifact packaging과 서버의 정확한 지원 contract 고정 |
| `backend/isolated_sync/observation.py` | 같은 직렬화 transaction에서 201/new와 200/retry를 알려 주는 선택적 local receipt |
| `backend/tests/test_isolated_sync_transfer.py` | 실제 HTTP·인증·lease·resource·전체 복원 검증 |
| `backend/tests/test_isolated_sync_transfer_failures.py` | 재계산한 hash 아래 잘못된 shape, lock interleaving, 실제 SIGKILL/reopen |
| `scripts/benchmarks/t66d3b.py` | 합성 in-process HTTP 성능·SQL plan 측정 |
| `scripts/benchmarks/test_t66d3b.py` | diagnostic 출력 경로·overwrite·startup 격리 검사 |
| `docs/specimens/t66d3b-release-artifacts.json` | 네 artifact의 exact C1 bytes/base64와 SHA-256 |
| `docs/benchmarks/t66d3b/summary.json` | 최종 source 측정 요약 |
| `docs/t66/d/implementation/t66d3b-implementation.md` | 본 보고서 |

기존 `backend/app`, mobile, frontend, schema migration, Snapshot exporter/restore, 금융 공식은 변경하지 않았다. 기존 D1 capture/fence, D2a 알고리즘, D2b finalizer도 변경하지 않았다. D3a의 선택적 receipt는 wire field나 authoritative certificate가 아니며 기존 caller의 반환값·lease·pin·retirement 흐름을 바꾸지 않는다.

## C. 격리 HTTP adapter — IMPLEMENTED / NOT ACTIVATED

`http.create_app(ObservationRepository(ObservationSandbox()))`를 명시적으로 구성해야 한다. 자체 startup hook, configured DB 경로, listener, login endpoint가 없다. `app.main`에 import/router 등록이 없다. Docs/OpenAPI 경로도 생성하지 않는다.

구현한 경로는 §15.2의 `POST /api/sync/v1/observations`와 §15.3의 `POST /api/sync/v1/observations/{id}/objects`다. `GET capabilities`는 의도적으로 404이며 전체 v1 support를 광고하지 않는다. §15.1의 고정 feature `large_restore:1`과 resource-proof가 필요한 `restore_bytes`를 R1 이전에 허위 광고하지 않기 위해서다. 이는 §15.1/§34의 미활성 준비 경계다. 새로운 wire feature 값이나 축소된 가짜 capability schema를 만들지 않았다.

## D. 기존 인증 통합 — IMPLEMENTED / VERIFIED

`app.auth._session_token_from_request()`와 `_hash_session_token()`을 그대로 사용한다. Cookie 우선, 그다음 Bearer라는 기존 선택 의미를 보존한다. Principal은 소유 합성 DB의 `auth_sessions.user_id`에서 구하고 D3a `_guard()`가 `users.is_active`, 원 token hash, expiry를 검증한다. Caller가 principal ID를 제출하는 경로가 없다. Shared/PIN session은 본체 `auth_sessions` credential이 아니다.

기존 `require_user()`는 configured normal DB session을 열기 때문에 격리 app에서 호출하지 않는다. 같은 실제 session/user model의 read-only 조회만 좁게 연결한다. Login 시스템을 추가하지 않고 `last_seen_at` 갱신이나 만료 session 삭제도 하지 않는다. Origin이 있는 POST는 같은 origin 또는 app 구성 시 명시한 allow-list만 허용한다.

검증: `test_original_credential_auth_lifecycle`, `test_cookie_precedence_and_origin`, `test_cross_principal_and_cross_generation_objects`.

## E. Manifest 취득 — IMPLEMENTED / VERIFIED

Required body `{protocol,request_id,base,inline_bytes}`를 strict JSON으로 읽고 D3a `create()`를 호출한다. 중복 key, 잘못된 Unicode, 숫자·shape·unknown field를 조용히 보정하지 않는다. 반환 manifest는 persisted D3a response의 exact C1 표현이다. 새 관측은 201, 같은 credential/request C1의 유효 retry는 200이다. 이 판정은 quota/생성과 같은 직렬화 transaction 안의 receipt로 얻으므로 사전 조회 race가 없다.

Inline budget은 0..1MiB를 받지만 현재 optimization은 빈 `inline_objects`다. 별도 Snapshot export나 임의 GET manifest wire를 추가하지 않았다.

## F. Observation과 immutable Target — IMPLEMENTED / VERIFIED

Target의 NS, principal, versions, raw revision, context, 네 Ref, sync_root를 그대로 전달한다. 새 generation이 commit되어도 이전 관측의 persisted Target/hot/control을 재생성하지 않는다. 같은 관측 retry에서 Judgment 함수를 호출하지 않는다. 새 관측의 randomized 문구와 기존 관측의 immutable content를 구분한다.

검증: `test_manifest_real_auth_retry_conflict_and_read_only`, `test_exact_root_response_retry_and_hash`, `test_cross_principal_and_cross_generation_objects`.

## G. Typed-path 인가 — IMPLEMENTED / VERIFIED

`PathResolver.resolve()`는 현재 인증된 관측의 raw/index/hot/control Ref만 첫 hash로 허용한다. 서버 자신의 object bytes를 C1/hash/domain/context로 검증한 뒤 그 안의 실제 typed child Ref만 다음 edge로 허용한다. 잘못된 root나 child는 그 guessed hash를 SQL로 조회하기 전에 거부한다. 보조 `sync_object_edges`를 클라이언트 인가 oracle로 신뢰하지 않는다.

Path는 1..512 hash이며 loop/repeated hash를 거부한다. Hash 문자열을 안다는 사실, principal ID, 다른 관측의 manifest/path는 독립적인 권한이 아니다. 동일 immutable object가 두 관측에 실제로 도달 가능하면 각자의 유효한 root/path 아래에서 같은 bytes를 전송할 수 있다. §15.3의 명시적 동일 Ref 재사용을 막는 가짜 관측별 object ID는 추가하지 않았다.

## H. Transferable root와 내부 root — IMPLEMENTED / VERIFIED

Transfer root는 raw-root, index-root, hot, control 네 개뿐이다. D3a의 다섯 번째 input-proof pin은 인가 map에 넣지 않는다. `sync_rows`의 row hash나 fact-key digest도 다운로드 link가 아니다.

검증: `test_independent_path_and_body_failures[internal_input]`, `[row_hash]`, `[arbitrary]` 및 전체 복원 oracle.

## I. Parent-child edge — IMPLEMENTED / VERIFIED

| 부모 | 실제 허용 edge |
| --- | --- |
| raw-root | 정확히 11개 ordered table entry의 root Ref |
| snapshot-node | ordered Child descriptor의 Ref |
| snapshot-leaf | 없음; row/key/value는 leaf 안에 포함 |
| index-root | facts Ref |
| index-node | left/right Ref와 prefix 방향 |
| index-leaf / index-empty | 없음 |
| hot / control | 없음 |

Table descriptor는 raw-root에 포함되며 별도 object가 아니다. 별도 row/payload object hierarchy를 발명하지 않았다. 방문 tree node는 table, height, count, ranges, fanout/occupancy, child descriptor를 확인한다. Leaf는 기존 `Row.make()`와 `leaf()`로 canonical shape·PK ordering·row/byte bounds를 확인한다. 방문 Patricia object는 structural version, count, prefix, bucket ordering/digest와 edge 방향을 확인한다. 전체 facts 완전성을 요청마다 재구축하지 않는다.

검증: descendant/grandchild HTTP 테스트, 독립 parent walk, 재계산한 hash 아래의 20개 잘못된 shape 증거.

## J. Content/hash/domain 정합성 — IMPLEMENTED / VERIFIED

Raw/index/tree object는 D2b `Store.get()`을 zero-capacity cache로 사용한다. Hot/control은 D3a `_view_object()`를 사용한다. D2a `Object`와 C1 decoder가 원 bytes의 canonicality, kind-domain hash, Ref 길이를 확인한다. 방문 edge의 허용 종류와 namespace/schema/canonicalization을 추가로 검사한다. 손상 object를 repair하거나 serializer로 바꾸어 제공하지 않는다.

Hash가 맞다는 사실만으로 authority를 인정하지 않는다. 먼저 D3a의 complete D2b certificate, Target, 원 credential, lease, pin association을 검증한다. 방문하지 않은 전역 구조의 완전성은 그 complete generation 계약과 미래 client complete validation 경계에 속한다.

## K. Immutable object 전송 — IMPLEMENTED / VERIFIED

요청 순서대로 `ObjectChunk={ref,offset,length,data_base64}`를 반환한다. Raw immutable bytes의 slice에 strict padded RFC4648 base64만 적용한다. Outer JSON이 금액/REAL/Unicode token을 재직렬화하지 않는다. INTEGER/REAL/signed zero/null/boolean 및 Unicode 표현은 decoded object bytes에서 그대로 유지된다. 모든 item이 통과해야 chunks를 공개하며 partial-success body가 없다.

## L. Request ticket와 terminal guard — IMPLEMENTED / VERIFIED

Ticket은 원 credential, request nonce, observation ID와 live cancellation Event를 묶는다. HTTP 입력은 ticket이나 guard를 만들 수 없다. Object batch 준비 안에서 D3a 초기·terminal lease 검사를 사용하고, response serialization 및 선택적 metrics callback, disconnect 확인 뒤에 다시 audited `lookup()`으로 마지막 auth/lease/epoch/root binding을 확인한다. Optional callback도 마지막 guard 뒤에 실행하지 않는다.

모든 protected response bytes와 headers를 준비한 뒤 terminal guard를 통과한다. DB transaction은 bounded 준비/검증까지만 살아 있고 HTTP 전송 중에는 닫혀 있다. Auth/session이 바뀌거나 취소된 요청은 보호 bytes 대신 오류만 반환한다. Guard 이후의 새로운 사건까지 push로 무효화하는 보장은 하지 않는다(§5/§16).

## M. 만료와 sticky retirement — PRESERVED / VERIFIED

D3a `_check_lease()`, `_lookup()`, `_connection()`의 M01/M02 correction을 그대로 사용한다. 만료 경계는 `now >= expires_at`이다. Terminal-expired lookup/object/retry를 거부하고 성공한 retirement COMMIT 뒤 clock rollback으로 status가 available로 돌아가지 않는다. Quota replacement의 durable retirement/savepoint ordering도 변경하지 않았다.

검증: initial/terminal 경계 주입 9개, ±1 microsecond 경계, 네 old+네 replacement 후 rollback/fresh connection, 기존 129개 D3a 회귀.

## N. Retry/idempotency — IMPLEMENTED / VERIFIED

같은 manifest nonce와 exact request C1는 유효 lease 안에서 동일 observation/body를 돌려준다. 다른 body는 409 REQUEST_CONFLICT다. Object request는 read-only이며 같은 관측/path/offset/length/request_id의 성공 body가 byte-identical하다. 응답 유실/중단 후 새 Target를 몰래 생성하지 않는다. Busy는 retry_same, 만료는 new_observation, revoked/replaced credential은 reauthenticate, epoch 변경은 full_resync다. 서버의 무한 자동 재시도 loop는 없다.

## O. HTTP 오류 — IMPLEMENTED / VERIFIED

`http.error_response()`는 §17의 `{protocol,request_id,error:{code,action,retry_after_ms,current_ns}}`를 반환한다. Current NS는 nullable이며 격리 adapter는 null을 사용한다. 401/403 인증, 409 epoch/base/nonce/conflict, 410 expiry/incomplete, 422 unsupported/invalid, 413 transfer budget, 429 lease quota, 503 busy/root readiness를 구분한다. 내부 storage/shape 손상은 500 STORAGE_FAILED로 fail closed한다. SQL, exception message, credential, row 값을 body에 넣지 않는다. 전체 Snapshot fallback도 없다.

## P. Size/resource budget — IMPLEMENTED / VERIFIED

| 자원 | 기본 상한/의미 |
| --- | --- |
| HTTP body | 3MiB; 64개의 최대 512-hash path를 표현 가능. Content-Length 사전 검사와 누적 stream byte 검사 |
| Body 수신 시간 | 10초; 구성 범위 1..60초 |
| Batch | 1..64 items |
| Decoded chunks 합 | 1MiB |
| 개별 chunk | 1..1MiB |
| Path | 1..512 hashes; item당 실제 path만 resolve |
| 동시 준비 요청 | 기본 2, 격리 구성 최대 16; 초과는 bounded retry 오류 |
| Outgoing buffering | 1MiB decoded + 정확한 base64 expansion + bounded JSON framing |
| 관측 metadata | 기존 D3a의 principal 4개, records 4096개, 64MiB logical budget 그대로 |

Offsets/Ref bytes는 규범 U64를 검증한 뒤 Python 정수로 계산하므로 overflow하지 않는다. Chunk 끝은 실제 object 길이 이하이어야 한다. 기존 허용 row를 거부하는 작은 object 길이 제한은 추가하지 않았다. Oversized singleton도 chunk로 취득한다.

Object C1/shape/hash 검증은 요청한 **전체 object**를 읽으므로 CPU/일시 메모리는 그 object bytes에도 비례한다. 이는 전체 history scan과 다르며 §8의 극단적인 row/key 입력 비용을 숨기지 않는다. Resolver cache는 0이고 이전 path object를 유지하지 않는다. 임의 크기의 giant SQLite value에 대한 일정한 heap 사용이나 production peak-memory resource proof를 주장하지 않는다. 배포 전 최대 실제 입력·동시성 resource proof가 필요하며, 전송 중 DB transaction을 유지하는 streaming으로 이를 우회하지 않는다.

## Q. Chunk/Range/encoding — IMPLEMENTED / VERIFIED

규범 chunking은 POST body의 offset/length다. HTTP Range/별도 chunk endpoint/재개 token은 추가하지 않았다. 응답은 bounded buffering 후 identity JSON/base64다. Request Content-Encoding은 identity만 받는다. HTTP 압축은 이번 구현에 포함하지 않았으며 canonical hash는 압축/JSON framing bytes가 아니라 원 immutable bytes의 domain hash다. Compression 후보는 R1/별도 검증 경계다.

검증: 1MiB보다 큰 schema-valid Unicode singleton을 두 요청 이상으로 조립하여 실제 SQLite object bytes와 hash가 정확히 같음.

## R. Version/engine artifact — IMPLEMENTED / VERIFIED

`ArtifactContract.current()`는 지원 Versions exact C1와 financial-engine hash를 app 구성 시 고정하고 Target와 재대조한다. Manifest의 Base/Versions required fields를 확인하고, 알 수 없는 여덟 version은 현재 contract로 Base를 hash하기 전에 422 UNSUPPORTED_CONTRACT로 거부한다. 손상 lineage의 BASE_INVALID/full_resync로 오분류하지 않는다. 실제 synthetic Base의 self-consistent domain hash를 별도 `hashlib` oracle로 만든 8개 HTTP 부정 테스트가 이를 검증한다.

`release_bundle()`는 raw schema, 12-projection schema, policy registry, engine source-hash descriptor의 exact bytes/SHA-256을 packaging한다. 커밋한 specimen을 재계산한 bundle 및 실제 HTTP Target와 비교한다. Engine artifact에는 code file hashes만 있으며 실제 code execution, DB 내용, credentials가 없다.

§4는 build-embedded 검증 allow-list를 규정하고 executable engine download API를 규정하지 않는다. 따라서 generic artifact/local-file endpoint를 만들지 않았다. T6.6E는 이 artifact exact bytes와 호환 allow-list를 review하여 자기 build에 포함해야 한다. Packaging 파일은 새 sync wire 메시지가 아니다. R1 대용 capability를 광고하지 않는다.

## S. Cross-principal 격리 — IMPLEMENTED / VERIFIED

실제 synthetic user/session A/B와 원 token 교체를 사용한다. A의 원 관측과 writer 후 B의 새 generation을 만들고, B의 정확한 manifest/path/hash를 알아도 A가 B의 관측 또는 A의 root에 붙인 B의 새 child를 취득하지 못함을 검증했다. B의 올바른 원 credential은 자기 관측에 접근한다. 물리적 content deduplication은 인가를 대신하지 않는다.

## T. 민감 데이터 — PRESERVED / VERIFIED

`share_pin_hash`, `share_pin_is_default`의 synthetic secret은 raw/public facts에서 제외되고 input proof는 내부 pin으로만 남는다. 모든 공개 root/descendant를 HTTP로 취득해 decoded bytes 안에 synthetic secret이 없음을 확인했다. Manifest와 오류도 원 credential이나 SQL 값을 포함하지 않는다. 이름/descriptor marker와 실제 setting value를 구분한다.

## U. Writer/transfer 동시성 — IMPLEMENTED / VERIFIED

관측 R의 immutable path를 취득한 뒤 D2b writer가 새 T를 commit해도 R은 R의 bytes를 유지한다. Response 준비 완료 후 별도 writer가 commit할 수 있고 마지막 재검사 후에도 원 R의 전송은 일관된다. Writer lock 대기 중 원 credential 폐기/epoch 변경은 terminal admission에서 거부된다. 두 manifest/object retry, 5 creators의 4 success+1 quota rejection, SQLITE_BUSY 후 retry도 검증했다.

## V. 중단/crash/retry — VERIFIED

인증 이후, object bytes 준비 이후, 직렬화 이후, terminal 경계에서 fault를 주입해 보호 body가 나오지 않음을 확인했다. 실제 SIGKILL 3개 경계 후 **죽은 process가 사용하던 실제 file-backed DB**를 fresh connection으로 열어 accepted generation과 5 pins를 검사했다. 동일 read-only 요청의 retry bytes가 일치했다. 이는 process interruption 증거이며 hardware power-loss 증거가 아니다. Observation 생성 자체의 6개 crash 경계는 기존 D3a 회귀로 유지한다.

## W. 전체 generation 복원 — VERIFIED

테스트의 독립 graph walker가 SQLite 원 object bytes에서 규범 edge를 읽고 hash를 `hashlib`로 계산한다. 이 graph의 모든 object를 실제 HTTP의 64-item/1MiB budget 안에서 취득한다. 모든 chunk를 조립해 exact bytes/hash를 비교하고, 11개 table row를 direct SQLite SELECT와 C1 bytes로 비교한다. 누락/중복을 row count만으로 판단하지 않는다. Facts 전체를 full `build_facts()` oracle와 비교하고 새 `Index.build()`의 canonical Patricia root를 Target index_ref와 비교한다.

Oracle의 graph/row/hash 비교는 HTTP path 인가 구현과 독립이다. Full facts/Patricia reference는 D2a C1/Fact 정의를 공유하므로 완전히 별개의 canonicalizer라는 주장은 하지 않는다. 이 O(N) 작업은 테스트에만 있으며 handler는 호출하지 않는다. History-dependent B+tree는 새 rebuild root equality가 아니라 실제 complete row/graph equality로 검증한다.

## X. SQL 접근 경로 — VERIFIED

Root 한 개 전송 SQL trace에서 ledger/cash/allocation/raw-row/reverse/object-edge 전체 조회가 없음을 확인했다. Object lookup은 PK hash point query다. 성능 harness는 실행한 SELECT template를 fresh connection의 EXPLAIN QUERY PLAN으로 확인하며 actual returned rows와 VM steps도 기록한다. Schema admission의 고정 sqlite_master/column/profile 검사는 매 connection 수행되며 latency 상수 비용에 포함된다. 이를 제거한 수치처럼 보고하지 않는다.

## Y. 성능 — VERIFIED

최종 요약은 [summary.json](../../../benchmarks/t66d3b/summary.json)에 둔다. 376/1k/5k/10k × observation create/manifest retry/root/leaf/deep Patricia/changed tree objects/unchanged retry/concurrent의 32 cell이며 각 3 warmups +20 measurements다. Bootstrap, 전체 graph oracle/path discovery, writer 준비는 timing 밖이다. Concurrent cell은 두 요청의 완료 시간이며 다른 cell은 단일 요청이다. Changed-objects cell은 최대 3개 새 tree object의 HTTP batch이며 전체 초기 sync나 완전한 mutation+sync latency가 아니다.

Auth, admission, path resolution, terminal 검사, wire bytes, SQL statements/rows, object reads/bytes, path edges, VM steps, 누적 process peak RSS를 구분한다. 누적 RSS에는 bootstrap/reference graph도 들어가므로 요청별 heap peak로 해석하지 않는다. 최종 측정과 backend 회귀는 같은 HOST에서 겹쳐 실행했으며 CPU 전용 측정이나 배포/mobile latency가 아니다. 서로 다른 stage median을 합산한 transaction latency를 만들지 않는다. Diagnostic 전용 ContextVar 계측으로 object resolution, typed-path/shape validation, base64, JSON serialization도 분리했다. 이 값은 중첩된 inclusive timing이며 합산할 수 없다. Object resolution은 admission의 Store 조회도 포함하고 outer HTTP terminal lookup은 제외한다. 크기별 시간이 단조 증가하지 않는 것은 공유 HOST 측정의 변동을 포함하며 속도 개선으로 해석하지 않는다.

Mandatory history scan 검출은 0이다. 요청 비용은 실제 path depth와 방문 object bytes를 따른다. 깊은 Patricia path 및 10k의 더 높은 tree path는 더 많은 object를 읽을 수 있다. 초기 complete cold transfer의 총 O(N) 데이터까지 O(1)이라고 주장하지 않는다.

최종 HOST 측정(ms, median / p95), Intel Core i7-8750H, Python/SQLite 세부 버전은 summary에 기록했다.

| Ledger rows | 새 관측 | Manifest retry | Raw root | Ledger leaf | Deep Patricia |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 376 | 395.96 / 434.11 | 356.05 / 358.98 | 317.35 / 349.82 | 627.92 / 652.42 | 354.98 / 357.31 |
| 1,000 | 418.13 / 440.25 | 394.35 / 398.37 | 346.67 / 348.11 | 622.20 / 627.41 | 352.27 / 353.43 |
| 5,000 | 413.32 / 415.28 | 370.80 / 373.17 | 327.15 / 331.05 | 589.03 / 594.16 | 330.52 / 334.48 |
| 10,000 | 367.49 / 371.01 | 335.45 / 358.16 | 297.48 / 301.17 | 477.88 / 540.14 | 249.99 / 252.03 |

이 표의 latency 평탄성만으로 점근 복잡도를 증명하지 않는다. Root path의 object reads는 모든 크기에서 1이고, leaf는 tree height에 따라 3/3/3/4, deep Patricia는 15/17/20/21이었다. 이 수치는 path resolver reads이며 인증/D3a admission/terminal metadata reads는 별도의 전체 SQL 수에 포함된다. 고정 schema admission과 두 terminal lookup에 의한 상수 비용도 실제 HTTP 시간에 포함했다.

재현: `.venv/bin/python scripts/benchmarks/t66d3b.py --output /tmp/<new-name>.json`. 이 도구는 기존 출력 overwrite와 checkout/운영 경로 출력을 거부하며 CPU/address-space limit를 설정한다. 상세 samples와 plans는 `/tmp/mn-d3b-http-profiled.json`에 있고 임시 파일의 영구 보존은 보장하지 않는다.

## Z. D3a M01/M02 회귀 — PRESERVED / VERIFIED

수정된 initial/terminal expiry, durable sticky retirement, quota 계산 전 retirement와 savepoint 보존을 건드리지 않았다. 새 HTTP terminal·clock rollback 테스트와 기존 correction 테스트를 모두 실행했다. Retired 관측 4개와 replacement 4개에서 40 active pins를 유지하고 available은 4개다. Pins의 물리적 보존은 lease authorization 갱신이 아니다.

## AA. D1/D2a/D2b 회귀 — PRESERVED / VERIFIED

Capture/fence, canonical vectors/hash domains, tree/Patricia, migrated SQLite constraints, D2b coalescing/finalizer/aggregate/financial parity의 기존 테스트를 전체 backend suite로 실행했다. D3b는 해당 알고리즘이나 certificate 의미를 변경하지 않는다. 선택적 creation receipt는 HTTP 201/200 구분만 위한 process-local 값이다.

## AB. Snapshot v7 — UNCHANGED

Exporter/restore/canonical hashing/manifest/financial source schema의 product source diff가 없다. 전체 backend suite에 기존 Snapshot와 authoritative-state 회귀가 포함된다. Future v7 materialization adapter 또는 OfflineBaseline 형식을 구현했다고 주장하지 않는다.

## AC. Normal runtime — UNCHANGED / NOT ACTIVATED

`backend/app`의 모든 Python source에서 `isolated_sync` import가 없음을 검사한다. 정상 startup, migration 선택, schema admission, login/financial/Snapshot/authoritative-state routes는 그대로다. 정상 app route에 새 sync endpoint를 등록하지 않았다. 테스트는 TestClient/ASGI transport와 자가 소유 temporary SQLite만 사용하며 새 port/service를 시작하지 않았다.

## AD. D3c retention — DEFERRED TO D3c

다음 세 lifecycle 의무를 남긴다: (1) lease 종료·idempotent release와 직렬화 pin 해제, (2) current/previous/active observations 및 전체 descendants의 reachability-aware retention/GC, (3) retired record/metadata budget의 안전한 회수. D3b는 pin 삭제/감소, object 삭제, observation metadata 삭제를 하지 않는다. 전역 records 4096/64MiB budget은 GC가 없는 동안 결국 신규 관측을 제한할 수 있다. 이는 기존의 의도된 fail-closed lifecycle 경계다.

## AE. Mobile — DEFERRED TO T6.6E

Exact C1/raw-money/Unicode parser, artifact allow-list, complete graph/facts validation, staged chunks, durable generation publication, frozen Offline B/J·pending·reconciliation·legacy recovery adapter가 필요하다. 이번 구현은 해당 입력을 전송하며 mobile 재계산이나 저장 포맷을 추가하지 않는다. Server auth/hash/financial authority의 의미를 혼합하지 않는다.

## AF. 알려진 한계와 후속 검증

내부 검증에서 알려진 Critical/High/Medium D3b blocker는 없다. 독립 감사는 아직 수행되지 않았다. R1 large restore와 production resource proof 전에는 full v1 capability를 선택할 수 없다. HTTP compression, HTTP Range endpoint, inline-object optimization, production/multi-instance authentication generation 확장, D3c GC와 T6.6E publication은 구현 범위 밖이다. Requested giant object의 C1 검증은 전체 object size 비용을 가지며 production 최대 입력·peak memory 증거는 배포 전 필요하다.

## AG. 전체 회귀

최종 전체 backend 회귀는 **1,202 tests + 1,540 subtests PASS**(1,080.75초)다. D1/D2a/D2b, 기존 129개 D3a와 M01/M02, migration/schema, 금융 projection, Snapshot v7, authoritative-state endpoint를 포함한다. 새 D3b HTTP/typed/failure tests는 **120개 PASS**이며 별도 targeted 실행에서도 120개가 통과했다. 전체 suite가 시작된 뒤 보강한 multi-request old-leaf byte 비교는 별도 targeted 재실행으로 통과했다.

Repository safety/diagnostic **59개 PASS**, Backend Ruff **PASS**, compileall **PASS**, frontend build **PASS**, `git diff --check` **PASS**다. Backend에는 기존 FastAPI TestClient의 httpx deprecation warning 1개가 있으며 실패는 없다. 상세 임시 실행 근거는 `/tmp/mn-d3b-backend-final.log`, `/tmp/mn-d3b-version-targeted.log`, `/tmp/mn-d3b-multi-request.log`, `/tmp/mn-d3b-safety-final.log`, `/tmp/mn-d3b-ruff-last.log`, `/tmp/mn-d3b-compile-last.log`, `/tmp/mn-d3b-frontend-build.log`에 있다. 임시 파일의 영구 보존은 보장하지 않는다.

실행 명령:

```text
cd backend
../.venv/bin/python -m pytest -q --durations=10
cd ..
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts/tests scripts/benchmarks
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts/benchmarks
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
npm --prefix frontend run build
git diff --check
```

Frontend/Flutter/Android runtime source를 수정하지 않았다. Flutter/Android 실기기 테스트와 hardware power-loss 검증은 실행하지 않았다.

## AH. Production 안전성

Production DB/API/credentials/service에 접근하지 않았다. 배포 dry-run, migration, restart, APK 설치도 하지 않았다. 합성 self-owned SQLite와 in-process HTTP만 사용했다. 정상 API/모바일 acquisition은 불변이다. 안전한 배포 승인을 의미하지 않는다.

## AI. Commit/push

완료 gate가 모두 통과한 뒤 이 보고서와 구현·tests·artifacts를 `feat(backend): implement isolated authenticated segment transfer`로 commit하고 repository main workflow로 push한다. 최종 commit hash와 HEAD/main/origin/main/실제 remote equality는 최종 응답에 기록한다. Commit/push는 배포 허가가 아니다.

## AJ. 다음 단계

T6.6D3b의 독립 구현 감사를 요청한다. 감사 통과 전 D3c 착수와 production 활성화는 승인된 상태가 아니다.

## AK. D3B-M01 — Cancellation/Worker Lifetime Correction

### 감사 이력과 재현

첫 D3b 독립 감사는 `e97b1d7f54231e6cc21d7d2ec897f6fd150cbd32`에서
**FAIL — TARGETED D3b CORRECTION REQUIRED**였다. Critical/High/Medium은
0/0/1, blocker는 D3B-M01 하나였다. 위 최초 구현·내부 검증 기록을 독립 감사
PASS로 바꾸거나 삭제하지 않는다. 이 절은 그 뒤의 한정 수정이며 별도 targeted
재감사를 대신하지 않는다.

수정 시작 때 `main`, HEAD, local main, origin/main, 실제 remote main은 모두
위 commit과 같았고 working tree는 clean이었다. Parent는
`9f9a94c03ff43c6d87e77e1dc2c30a30080cf71b`였다.

수정 전 실제 ASGI `Task.cancel()`과 native barrier를 다시 실행했다. 기본 limit
2에서 동시에 미종료 worker 5개, 미취소 RequestTicket 5개를 재현했다.
ASGI start/body는 0건이고 금융 raw/revision/root/pin 상태는 불변이었다.
기존 `dispatch()`의 coroutine `finally`가 native 종료 전에 semaphore를 반환하며,
worker 안에서 만든 ticket은 `prepare()` 반환 전 dispatcher가 알 수 없는 것이
원인이다. Await 취소와 native 실행 종료는 다른 사건이다.

### 수정 범위 — IMPLEMENTED / NOT ACTIVATED

| 파일 | 한정 변경 |
| --- | --- |
| [workers.py](../../../../backend/isolated_sync/workers.py) | 기존 threadpool 위의 bounded worker lease, native 완료·미시작 abort, exact-once 반환 |
| [http.py](../../../../backend/isolated_sync/http.py) | 사전 cancellation Event, ticket 공유, lease dispatch와 격리 app shutdown 신호 |
| [transfer.py](../../../../backend/isolated_sync/transfer.py) | 기존 path 알고리즘 앞의 선택적 cancellation checkpoint와 response assembly 전 검사 |
| [test_isolated_sync_transfer_cancellation.py](../../../../backend/tests/test_isolated_sync_transfer_cancellation.py) | 실제 ASGI·SQLite·queue·shutdown·race·stress 회귀 |
| [t66d3b_cancellation.py](../../../../scripts/benchmarks/t66d3b_cancellation.py) | 합성 HTTP 전후·취소 cleanup·admission 측정 |
| [release artifacts](../../../specimens/t66d3b-release-artifacts.json) | 변경된 격리 source에 맞는 engine descriptor 재생성 |
| [수정 성능 요약](../../../benchmarks/t66d3b/cancellation.json) | 새 표본의 compact 요약; 최초 summary.json은 보존 |

D1/D2a/D2b/D3a, DB schema, 금융 공식, Judgment, Snapshot v7, OfflineBaseline,
pending/journal/reconciliation은 수정하지 않았다. 정상 `backend/app`, mobile,
frontend source와 router 등록도 그대로다. Engine artifact는 기존 규칙대로
source hash를 포함하므로 fingerprint만 갱신한다. 나머지 세 artifact와 version
규칙, Target canonicalization/domain은 바꾸지 않는다. 이전 build의 관측을 새
engine 관측으로 가장하거나 immutable Target를 재작성하지 않는다.

### Permit과 worker의 서로 다른 수명

`WorkerBudget.acquire()`는 body 수신 전에 기존 thread-safe
`BoundedSemaphore`를 nonblocking으로 얻는다. Admission queue·별도 executor·
overflow worker는 없다. 초과 요청은 기존 `503 ROOT_NOT_READY/retry_same`이다.

`WorkerLease.run()`이 각 native operation을 등록한 뒤 기존 Starlette/AnyIO
threadpool을 호출한다. 한 lease는 동시에 한 operation만 실행할 수 있다.
Prepare와 terminal은 같은 lease 아래 순차 실행한다. Supervisor Task는 strong
reference로 추적하고 `shield()`로 requester 취소와 분리한다. Shield만으로
완료를 증명하지 않는다.

반환 조건은 **requester 소유권 종료 AND 미종료 operation 0개**다.
Request 취소는 Event를 설정하고 requester 소유권만 닫는다. 이미 시작한
operation은 function의 정상·예외 반환과 모든 DB cleanup을 마친 native
`finally`에서 완료 처리한다. 여기서 종료란 **준비 operation의 종료**이며
재사용 가능한 threadpool OS thread의 소멸을 뜻하지 않는다.

`queued → running → finished`와 requester의 `open → closed`를 별도로 관리한다.
미시작 queued supervisor는 취소 후 done callback에서 abort를 확정한다.
Native start와 abort는 같은 Lock으로 직렬화한다. Abort가 먼저면 늦게 진입한
wrapper가 준비를 시작하지 않고, start가 먼저면 callback이 permit을 반환하지
않으며 native 완료가 책임진다. Semaphore 반환은 lease 집합 제거 조건과
finished flag로 정확히 한 번만 실행한다.

Worker exception은 done callback에서 회수한다. Coroutine 생성·Task 제출
실패도 미시작 job을 정리한다. Cancelled queued job은 기존 AnyIO limiter에서
빠져 capacity를 돌려주지만, 살아 있는 blocked worker는 계속 permit을 차지한다.
Supervisor/task/job 보유량은 admission으로 제한되며 무제한 재시도나 신규 queue가 없다.

### Cancellation handle·협력적 중단

Event는 credential 조회와 ticket 생성 **전** 존재한다. 생성된 RequestTicket은
같은 Event를 공유하고 원 request ID·credential·observation binding을 유지한다.
따라서 사전 취소도 ticket 생성 후 사라지지 않으며 cancelled ticket의 guard는
원 credential을 승인하지 않는다.

Native 시작 전, 인증 뒤, 방문 path object 사이, chunk response assembly 전,
직렬화 뒤, terminal 전·후에 안전한 checkpoint를 둔다. 기존 D3a guard도 그대로
호출한다. Cancelled live operation은 기존 인증 오류로 거부하며 실제 취소된
ASGI task는 CancelledError로 종료한다. 취소를 성공한 빈 응답으로 바꾸지 않는다.
Response는 여전히 모든 검증 뒤에만 반환하며 부분 batch를 send하지 않는다.

DB ownership을 다른 thread로 넘기거나 `Connection.interrupt()`를 쓰지 않는다.
취소 예외는 기존 rollback/close·sticky retirement scope를 통과한다. SQLite lock
대기나 긴 단일 C1 검증은 즉시 중단되지 않을 수 있다. 그동안 permit을 유지하고
다음 안전한 checkpoint에서 중단한다. 강제 thread 종료나 즉시 취소 latency 상한은
주장하지 않는다.

격리 app shutdown은 신규 admission을 닫고 기존 handle 및 미시작 job에 취소를
전달한다. Native completion은 threading semaphore를 사용하므로 닫힌 event loop에
release를 예약하지 않는다. Queued Task 취소 예약의 closed-loop 경우도 처리한다.
Shutdown된 app의 재사용은 새 `create_app()` 구성으로 해야 한다. SIGKILL을 graceful
cleanup이나 hardware power-loss 검증으로 해석하지 않는다.

### 결정적 회귀 — VERIFIED

신규 테스트는 **25개 PASS**다. Ordering은 asyncio/threading Event barrier로 고정하고
timeout은 deadlock 검출에만 사용한다. 임의 sleep으로 경계를 추정하지 않는다.

| 검증 | 테스트 |
| --- | --- |
| 실제 ASGI 취소·native permit 유지·응답 0·SQLite cleanup | `test_real_asgi_cancel_retains_native_permit_and_cleans_sqlite` × 4 |
| Ticket 전 취소, Event 전달 | `test_cancel_before_ticket_creation_is_not_forgotten` |
| Manifest partial pin rollback / commit 후 응답 유실 | `test_asgi_manifest_cancellation_leaves_absent_or_complete_pins` × 3 |
| Body 수신 중 취소 | `test_cancel_during_body_admission_has_no_worker_or_permit_leak` |
| 취소 이후 worker 정상/예외 종료와 exception 회수 | `test_cancelled_worker_late_result_or_exception_is_observed` × 2 |
| 완료·취소 순서 양방향 | `test_asgi_completion_cancellation_race_exact_once` × 2 |
| Task/Executor 제출 실패 | `test_submission_failure_releases_exactly_once` × 2 |
| 미시작/실행 중 supervisor shutdown | `test_supervisor_shutdown_cannot_release_a_running_worker` × 2 |
| 단일 lease 병렬 실행 금지 | `test_one_lease_cannot_dispatch_parallel_native_operations` |
| Queued 취소·실제 AnyIO limiter·native 시작 전 취소 | `test_cancelled_queued_worker_keeps_admission_bounded`, `test_cancel_while_real_anyio_executor_limiter_is_occupied`, `test_cancel_before_native_start_never_authenticates_or_returns_success` |
| 원 loop 종료 뒤 native 예외·capacity 회수 | `test_native_exit_after_original_loop_closed_returns_capacity` |
| Path checkpoint·shutdown·bounded stress | `test_path_checkpoints_stop_cancelled_batch_before_next_object`, `test_shutdown_signals_handles_without_releasing_live_capacity`, `test_bounded_cancellation_stress_never_overadmits_and_recovers` |

Stress는 기본 limit 2, 5개 wave, 실제 취소 10건, 과부하 거부 20건,
성공 요청 5건과 교대 worker exception을 포함한다. 최대 running worker는 **2**,
취소된 request의 ASGI start/body는 **0**이다. 각 wave 종료 때 leases/jobs/running/tasks는
모두 0이고 정확히 두 permit이 돌아온다. 단순 in-memory ticket 검사만이 아니라
worker 생존 중 busy, 종료 후 성공을 실제 ASGI로 관측한다.

추가 `/tmp` 합성 검증은 running request 2개와 overflow request 4개를
동시에 만들어 **실제 ASGI Task 6개**를 겹쳤다. 5개 wave에서 취소 10건,
busy 25건, 성공 5건을 실행해 최대 worker 2, cancelled ASGI event 0,
미회수 exception 0, 최종 leases/jobs/running/tasks 전부 0을 확인했다.
ASGI 진입 전 Task 취소도 별도로 실행했다. Fresh SQLite 상태는 불변이었다.
이는 신규 pytest 25개와 별도로 실행한 보강 증거이며 테스트 수에 중복 합산하지 않는다.

Fresh file-backed SQLite connection으로 11개 raw table, revision, accepted generation,
certificate, observation/pin/object bytes의 전후 동일성과 writer lock 획득을 검사한다.
Manifest pin 중간 취소는 전부 rollback한다. Commit 후 응답 유실은 complete
observation과 다섯 active root pin을 보존한다. 이번 수정에서 pin 해제·GC는 하지 않는다.

### 성능·복잡도

최종 측정값과 전체 회귀의 완료 결과를 아래에 기록한다. 376-row 합성 DB에서
manifest retry/raw-root/ledger-leaf/batch, 각 variant 3 warmup+20 표본을 교대로 측정한다.
기준선 HTTP만 Git의 감사 commit에서 읽고 금융/codec/artifact 의존성은 양쪽 현재
build로 맞춰 cancellation ownership 수정의 비용을 분리한다. 이전 full-build
benchmark나 실제 단말 측정으로 부르지 않는다. Bootstrap/path discovery는 측정 밖이다.

추가 취소 표본은 barrier 해제 후 cleanup과 permit 재취득을 측정한다. DB lock이나
단일 giant object 처리의 최악 시간 상한이 아니다. Admission primitive의 미세 측정도
전체 HTTP latency와 구분한다. Source/SQL trace에서 새 ledger/facts/graph scan이 없고
worker 관리의 비용은 최대 L개 lease와 각 bounded operation에만 의존한다.

최종 HOST 실측은 Intel Core i7-8750H / Python 3.12.3 / SQLite 3.45.1 /
Linux x86_64에서 **8개 HTTP cell × 20개 = 160개 measured sample**이다.
각 cell은 warmup 3개이며, 같은 HOST에서 backend 회귀도 진행했으므로 미세한
차이의 통계적 유의성이나 배포·단말 latency 개선을 주장하지 않는다.

| 요청 | 수정 전 median/p95 ms | 수정 후 median/p95 ms | 전후 동일 SQL 수 / object read 수 |
| --- | --- | --- | --- |
| manifest retry | 346.17 / 363.20 | 347.30 / 366.29 | 545 / 0 |
| raw-root | 295.56 / 318.36 | 282.57 / 318.39 | 422 / 1 |
| ledger-leaf | 581.37 / 626.14 | 579.06 / 624.24 | 424 / 3 |
| batch | 601.00 / 641.08 | 590.05 / 628.88 | 426 / 5 |

Native dispatch 합계 median은 전후 각각 manifest 0.444/0.438ms,
root 0.463/0.438ms, leaf 0.529/0.511ms, batch 0.546/0.517ms였다.
Admission primitive median은 기존 semaphore 0.740µs와 lease admission 2.736µs다.
이 값은 전체 요청이나 terminal guard 시간과 합산하지 않는다.

추가 20개 취소 표본에서 cancel→cleanup median/p95는 0.337/0.353ms,
barrier 해제→cleanup은 0.233/0.246ms, cleanup 뒤 permit 재취득은
0.0098/0.0105ms였다. 이는 인증 뒤 controlled barrier의 결과다. 강제로
지연시킨 worker가 막혀 있는 동안의 대기나 실제 SQLite busy 한계를 숨겨
즉시 thread 중단 보장으로 표현하지 않는다.

모든 전후 성공 body는 byte-identical이며 SQL 수·object read 수가 같다.
Bootstrap, Snapshot export, full facts/segment traversal을 측정 경로에 추가하지
않았다. 원 표본은 `/tmp/mn-d3b-m01-performance-release.json`, compact 요약은
위 `cancellation.json`이며 이전 `summary.json` 측정은 수정하지 않았다.

재현 명령:

```text
.venv/bin/python -m pytest -q backend/tests/test_isolated_sync_transfer_cancellation.py
.venv/bin/python scripts/benchmarks/t66d3b_cancellation.py --output /tmp/m01-new-output.json
cd backend
../.venv/bin/python -m pytest -q --durations=10
cd ..
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts/tests scripts/benchmarks
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts/benchmarks
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
npm --prefix frontend run build
git diff --check
```

### 경계·후속 조치

Cancelled request의 이미 완전하게 commit된 관측은 응답 유실과 같은 orphan이 될 수
있다. D3c가 안전하게 retire/release/GC할 후속 대상이며 cancellation 자체로 pin을
삭제하지 않는다. D3c/E/R1, production resource proof는 그대로 미구현·미승인이다.
배포·production 접근·정상 endpoint 활성화는 하지 않았다. M01 targeted 독립
재감사 통과 전 D3c 착수와 배포를 승인하지 않는다.

### 최종 회귀·수정 판정 — VERIFIED

확정 source/artifact로 완주한 전체 backend 회귀는 **1,227 tests + 1,540 subtests
PASS**, 963.03초다. 기존 D3b 120개, D3a 129개와 M01/M02, 신규 cancellation
25개 및 D1/D2a/D2b·migration/schema·금융 projection·Snapshot v7·authoritative-state
회귀를 포함한다. 신규 25개는 별도 targeted 실행에서도 PASS였다. 중간 개발 실행을
최종 완주 결과로 재사용하지 않는다.

Safety/diagnostic **59개 PASS**, 전체 Backend Ruff **PASS**, compileall **PASS**,
frontend build **PASS**, 문서 local link 9개 **PASS**, `git diff --check` **PASS**다.
기존 FastAPI TestClient의 httpx deprecation warning 1개가 있다. Flutter/Android
및 실기기 테스트는 실행하지 않았다. Product mobile/frontend source는 불변이다.

최종 로그는 `/tmp/mn-d3b-correction-regression-final.log`,
`/tmp/mn-d3b-correction-targeted-final.log`, `/tmp/mn-d3b-correction-safety-final.log`,
`/tmp/mn-d3b-correction-ruff.log`, `/tmp/mn-d3b-correction-compile-final.log`,
`/tmp/mn-d3b-correction-frontend.log`, `/tmp/mn-d3b-m01-extra.log`다.
임시 로그·표본의 영구 보존은 보장하지 않는다.

내부 수정 판정은 **T6.6D3b CORRECTION COMPLETE — READY FOR TARGETED RE-AUDIT**다.
새로 확인된 미해결 Critical/High/Medium은 0/0/0이다. 독립 재감사 PASS나 D3c
승인을 주장하지 않는다. 한정 8개 파일을
`fix(backend): retain transfer permits until worker termination`으로 commit/push하고,
최종 응답에서 HEAD/main/origin/main/실제 remote main 및 clean 상태를 확인한다.
Production 접근·배포·segmented endpoint 활성화·D3c 구현·pin 해제는 수행하지 않았다.
