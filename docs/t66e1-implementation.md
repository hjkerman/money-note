# T6.6E1 — Flutter segmented client store 구현

## A. 시작 commit과 격리 범위

시작점은 `9ee495e970a02c9810b4519eb0730612fa4f6349`이다. 수정 전 branch `main`, HEAD, local main, origin/main, `git ls-remote origin refs/heads/main`이 모두 같았고 working tree는 clean이었다. D3C-A01 독립 재감사 기록은 수정하지 않았다.

E1은 protocol model, 개별 immutable object 검증, durable object/staging 저장과 복구만 구현한다. E2 transport/auth/download scheduler, E3 complete generation 검증·게시, E4 통합은 구현하지 않았다. `STAGED`는 `ACTIVE`가 아니며 기존 앱이 읽을 accepted pointer가 없다.

변경 파일:

- `mobile/lib/src/segmented/{c1,protocol,object,store}.dart`
- `mobile/pubspec.yaml`, `mobile/pubspec.lock`
- `mobile/assets/segmented/isolated-release-artifacts.json`
- `mobile/test/segmented_{protocol,store,crash}_test.dart`
- `mobile/test/support/segmented_{fixture,crash_worker}.dart`
- `mobile/test/fixtures/segmented_server_golden.json`
- `scripts/benchmarks/t66e1_fixture.py`, 이 문서

기존 Flutter runtime source, backend source, Android 설정, 금융 공식, 배포 script는 변경하지 않았다. 앱 버전은 `2.4.0+15` 그대로다.

## B. Binding server protocol 대조

규범은 `docs/t66c-delta-sync-protocol.md` §7–15, §23–27, §30, §38과 `docs/architecture.md`의 서버 authority/클라이언트 신뢰 경계다. `docs/offline-mode.md`, `docs/domain-model.md`, `docs/project-state.md`, `docs/known-issues.md`, D3C-A01 재감사도 확인했다.

실제 source를 대조했다:

| 계약 | 서버 source | E1 대응 |
| --- | --- | --- |
| C1, NS, domain hash | `backend/isolated_sync/canonical.py` | `c1.dart` |
| 11개 raw table, key/leaf/node/descriptor | `raw.py`, `segments.py`, `roots.py` | `object.dart` |
| Patricia/fact-key | `patricia.py` | `object.dart` |
| Target, Context, Versions, lease | `observation.py`, `observation_schema.py` | `protocol.dart` |
| immutable store와 complete authority | `store.py`, `finalization.py` | integrity와 authority의 구분 |
| transferable kinds, Ref, chunk | `transfer.py`, `http.py` | object/chunk model만 구현 |
| 네 release artifact | `artifacts.py`, `docs/specimens/t66d3b-release-artifacts.json` | exact asset와 allow-list |

별도 wire format, hash domain, 금융 해석을 추가하지 않았다. protocol error envelope의 HTTP 처리와 recovery action 실행은 E2다. E1의 `SegmentedException.code`는 로컬 parsing/integrity/persistence 오류이며 HTTP status로 가장하지 않는다.

## C. 기존 Flutter 구조

`AppState`/기존 API consumer는 기존 authoritative bundle을 사용한다. `OfflineStore`는 `offline-mode/baseline.json`, `state.json`, `journal.ndjson`과 기존 recovery 파일을 관리한다. `LocalSnapshotRepository`는 기존 Snapshot backup 파일과 30개 보관 규칙을 관리한다. 기존 persistence는 `dart:io`/`path_provider` 중심이며 SQLite repository는 없었다.

규범의 `segmented-store/1` 단일 SQLite 선택에 맞춰 `sqlite3: 3.7.0`을 고정했다. ORM이나 새 application state framework는 도입하지 않았다. `crypto`는 기존 dependency를 재사용한다. native build용 transitive dependency 변화는 lockfile에 명시되어 있다. 기존 lockfile의 effective SDK 하한은 변경되지 않았다.

## D. Persistent layout

`SegmentedClientStore.open(privateRoot, cache)`는 호출자가 명시한 private directory 아래에만 다음 파일을 연다.

```text
<privateRoot>/segmented-store-v1/<CacheNamespace.key>.sqlite
```

기본 application directory provider, normal startup 등록, global singleton, UI 연결은 없다. namespace는 trusted HTTPS origin + server/dataset/epoch + principal + Versions의 로컬 checksum으로 구분한다. 이 checksum은 protocol object hash가 아니다.

`user_version=1`, discriminator `segmented-store/1`인 별도 DB의 8개 table:

| Table | 의미 |
| --- | --- |
| profile | discriminator, namespace, validator build |
| refs | hash/bytes, 아직 없는 child/root의 placeholder 포함 |
| objects | immutable exact BLOB, kind, validator build |
| edges | 검증된 parent의 순서 있는 typed child reference |
| staging | local UUID, canonical manifest metadata, checksum, UTC 생성 시각 |
| staging_roots | Target의 네 transferable root |
| staging_objects | 실제 저장된 object에 대한 recoverable progress |
| usage | transactionally maintained logical resource counters |

FK는 존재하는 객체/progress의 관계를 보호한다. placeholder는 verified object로 광고하지 않는다. `accepted`, `active`, `generations` table은 없다. 현재 schema가 다르면 자동 재해석·upgrade하지 않고 거부한다. production SQLite schema v4와 별개다.

## E. Protocol model

`protocol.dart`의 `SyncNamespace`, `ObjectRef`, `SyncVersions`, `FinancialContext`, `SyncTarget`, `ObjectChunk`, `ObservationManifest`, `CacheNamespace`는 factory validation 뒤에만 생성된다. 자유 JSON map을 validated model로 취급하지 않는다.

- NS/observation/request/local staging ID는 canonical UUIDv4다.
- hash는 lowercase SHA-256 64자리, Ref.bytes/revision/offset은 규범의 U64 decimal string이다.
- Versions 8개 field와 Target의 exact field set, positive principal, Context/date/offset/engine을 검사한다.
- Target의 `sync_root`는 그 field를 제외한 Target의 `view` domain hash로 확인한다.
- manifest는 `available`, change/base 관계, UTC timestamp, 최대 900초 lease, inline chunk 수/합계 제한을 검사한다. outer HTTP JSON의 whitespace는 허용하고 검증 후 local metadata를 C1으로 저장한다. inner object bytes는 재작성하지 않는다.
- chunk는 strict padded base64, exact decoded length, offset/Ref 범위, 최대 1 MiB를 검사한다. HTTP 호출이나 chunk download/assembly scheduler는 없다.

## F. Canonical byte/hash 검증

`decodeC1`은 strict UTF-8, duplicate/escaped duplicate key, 모든 string/key의 Unicode scalar, int64, REAL lexical exactness, 제한된 depth를 검사한다. REAL의 lexical coefficient/exponent를 binary64 변환 **전에** 확인하므로 underflow/rounding으로 fractional money를 정수로 고치지 않는다.

`encodeC1`은 UTF-8/scalar key 순서, 규범 escape, integral REAL의 `.0` 및 `-0.0`, Unicode 원문을 보존한다. 기존 B-2/bundle encoder는 바꾸지 않는다. 객체는 원본 bytes와 C1 재인코딩 bytes의 equality를 요구하고, 저장/hash 입력은 원본 bytes다.

`objectHash(kind, bytes)`는 `ASCII("money-note.sync.v1/" + kind) + NUL + exact bytes`의 SHA-256이다. chunked digest로 큰 preimage의 불필요한 결합 copy를 피한다. unsupported domain은 거부한다. plain SHA-256 local checksum 및 release artifact SHA와 protocol domain hash를 구분한다.

## G. Object identity와 context

`VerifiedObject.verify`는 length/local budget, exact C1, kind/domain hash, NS, canon/schema, kind별 exact shape를 검증한다. 9개 transferable kind만 허용한다:

`raw-root`, `snapshot-leaf`, `snapshot-node`, `index-root`, `index-empty`, `index-leaf`, `index-node`, `hot`, `control`.

raw-root의 11 table 순서, PK key 표현/정렬, descriptor count/range/height, leaf row count/size/oversized, node child 순서/count, Patricia local shape/fact digest를 확인한다. raw row와 12개 hot projection의 typed shape는 기존 공개 `validateBundleShape`를 재사용한다. partial object에 full legacy Bundle validator를 호출하지 않는다. 민감 설정은 raw leaf에서 거부한다. monetary setting string은 검증하되 trim/coercion한 값을 저장하지 않는다.

서버의 oversized 판정은 `oversized:false`일 때의 bytes를 기준으로 한다. `true`가 한 byte 짧은 정확한 256 KiB 경계도 테스트했다. 전체 object 크기를 1 MiB chunk 제한과 혼동하지 않는다.

`TypedObjectReference`는 실제 허용된 graph edge와 table/descriptor context를 보존한다. hash처럼 보이는 임의 문자열은 edge가 아니다. internal input-proof는 transferable kind도 staging root도 아니다.

**Object integrity ≠ generation membership ≠ observation authorization.** E1 receipt는 앞의 첫 항목만 증명한다. 부모/자식의 실제 object association, global closure, root별 completeness, hot/raw/context equality, root/non-root fanout 의미, 금융 authority의 최종 수락은 E3 책임이다. 다른 evaluation date의 raw object 재사용은 가능하지만 hot을 새 Target에 연결할 권한을 E1이 부여하지 않는다.

## H. Write transaction

`putVerifiedObject`는 bytes를 소유한 copy로 먼저 검증하고 `BEGIN IMMEDIATE` 안에서 Ref/BLOB/validator/edges/usage를 함께 저장한다. readback 검증 후 COMMIT한다. 같은 identity의 동일 bytes는 idempotent다. 다른 bytes는 hash/immutability 검증에서 거부한다. 기존 BLOB UPDATE는 trigger도 거부한다.

`DELETE journal + synchronous=EXTRA + foreign_keys=ON`을 readback 확인한다. I/O/SQLITE_FULL/lock 오류를 성공으로 반환하지 않는다. transaction 실패는 rollback하며, SQLITE_FULL이 이미 rollback한 경우 원래 오류를 가리지 않는다. COMMIT 뒤 caller가 결과를 잃어도 재시도는 기존 object를 검증한다.

동시 schema 생성은 write lock 획득 후 user_version을 다시 확인한다. independent isolate/connection 경합은 명시적 `STORE_BUSY`로 노출할 수 있다. concurrent test의 호출자는 최대 네 번의 **로컬** busy retry를 사용한다. 이는 E2 HTTP retry 정책 구현이 아니다.

## I. Read-time 검증

`getVerifiedObject`/`containsVerifiedObject`는 DB의 length를 먼저 제한하고 payload를 읽는다. C1/hash/shape/context/validator와 stored edge catalog를 매번 대조한다. filename/mtime/verified flag만 신뢰하지 않는다. `VerifiedObject.bytes/body`는 외부 변경이 저장 receipt를 바꾸지 못하도록 copy를 반환한다.

`listStoredObjectIdentities`는 keyset page(최대 1,024개)만 조회하며 BLOB를 가져오지 않는다. 저장 목록은 membership/completeness proof가 아니다. object가 없으면 null이고 손상/불일치는 명시 오류다.

## J. Staging metadata

`createStaging`은 local UUID와 exact validated manifest, Target/namespace, 네 expected roots, UTC 생성 시각을 atomic하게 저장한다. 같은 ID의 다른 manifest는 거부한다. `recordStagedObject`는 실제 저장되어 재검증 가능한 object만 progress로 연결한다. 이 연결은 membership proof가 아니다.

`loadStaging`/`listStagingIdentities`로 restart 후 staging을 복구한다. checksum, manifest/Target, root refs, 생성 시각을 다시 확인한다. 이미 만료한 lease의 metadata와 동일 immutable bytes를 보관할 수는 있지만 network authorization 또는 install 권한으로 사용하지 않는다.

`removeUnreferencedStagingData`는 명시적으로 버린 staging/progress와 무참조 placeholder만 제거한다. immutable object GC, accepted/frozen pin release는 없다.

## K. Crash/restart recovery

open 시 discriminator/version/namespace/validator, exact table inventory, quick_check, FK, 실제 행에 근거한 usage counter를 검사한다. `inspectStoreHealth`는 명시적 scrub으로 모든 object/staging/progress를 검사한다. startup/scrub의 O(N)은 허용하지만 일반 put/get에 전체 scan을 넣지 않았다. E2는 매 object마다 store를 재open하는 대신 적절한 장기 handle/coordinator 수명을 선택해야 한다.

실제 child Dart process를 synchronous barrier에서 SIGKILL한 7개 경계:

1. object INSERT 전
2. object INSERT 뒤
3. edges INSERT 뒤
4. COMMIT 직전
5. object COMMIT 직후
6. staging INSERT 뒤, COMMIT 전
7. staging COMMIT 직후

fresh connection으로 원래 good object, 새 object/staging의 전체 존재 또는 부재, 네 staging roots, FK/integrity, 추가 write lock 획득을 직접 확인한다. COMMIT된 staging도 `staged`, progress 0이며 활성화되지 않는다. SQLite 자체 journal은 수동 삭제하지 않는다. E1은 별도 payload temporary file을 생성하지 않으며 알 수 없는 `.pending` 파일을 검증된 object로 채택하지 않는다.

## L. Corruption/failure 처리

저장된 BLOB, kind, validator, edge, 누락 payload, staging checksum, usage counter 손상은 open/read/scrub 단계에서 거부한다. 자동 sanitize, silent repair, 다른 identity로 대체, legacy 성공 fallback은 없다. 이전 good object와 기존 offline 파일은 보존한다.

대표 로컬 오류는 `CANONICAL_INVALID`, `OBJECT_HASH_INVALID`, `OBJECT_LENGTH_INVALID`, `UNSUPPORTED_CONTRACT`, `CACHE_CONTEXT_MISMATCH`, `STAGING_CORRUPT`, `STORE_CORRUPT`, `STORE_METADATA_CORRUPT`, `STORE_BUSY`, `PERSISTENCE_FAILED`, `LOCAL_*_BUDGET`이다. persistence 예외는 SQLite numeric code만 노출하고 SQL/bound financial values를 오류 문자열에 넣지 않는다.

## M. Resource limits

| 로컬 기본 예산 | 값 |
| --- | --- |
| 한 object | 64 MiB |
| 전체 object payload | 512 MiB |
| object 수 | 100,000 |
| 한 manifest | 8 MiB |
| logical metadata | 32 MiB |
| staging 수 | 128 |
| SQLite max_page_count | 262,144 |
| busy timeout | 1,000 ms, 설정 가능 상한 10,000 ms |
| parser depth | 128 |
| enumeration page | 최대 1,024 |

이는 configurable client resource policy이며 서버 wire maximum을 새로 정의하지 않는다. 초과는 incompatibility와 구분한 local budget 오류다. max_page_count는 physical page budget이고 logical metadata charge는 행 종류별 보수적 accounting이지 실제 파일 byte 수가 아니다. 실제 64-page DB에서 큰 valid singleton을 넣어 SQLITE_FULL(13), rollback, prior good object/usage 보존을 확인했다.

put/get은 해당 object와 bounded metadata만 처리한다. 전체 dataset, immutable descendants, ledger, Snapshot hash를 읽지 않는다. E1은 모바일 GC 정책이나 chunk spool을 구현하지 않았으므로 예산을 넘는 작업의 cleanup/retry 조정은 후속 단계다.

## N. Frozen Offline B/J 격리

`normal OfflineBaseline v4 B/J Snapshot files unchanged` 테스트는 기존 `OfflineStore`로 baseline/state/J를 먼저 저장한 후 E1 동작 전후 bytes를 비교한다. 기존 schema v4, journal publication, pending/reconciliation 의미는 그대로다. E1 DB에는 이 파일들을 가리키거나 변경하는 코드가 없다.

## O. Snapshot v7 격리

기존 `LocalSnapshotRepository`로 synthetic Snapshot을 저장하고 E1 동작 뒤 exact file bytes를 확인한다. Snapshot materialization/export/restore와 backup 보관 정책을 변경하지 않았다. 전체 backend/Flutter Snapshot 회귀도 실행했다. segmented object를 단순히 이어 붙여 Snapshot이라고 광고하지 않는다.

## P. Synthetic tests와 independent oracle

`scripts/benchmarks/t66e1_fixture.py`는 disposable `ObservationSandbox` 안에서 실제 D2b bootstrap/D3a presenter로 생성한 manifest와 9종 object bytes/hash를 stdout에 출력한다. configured DB/API는 열지 않는다.

```bash
PYTHONPATH=backend .venv/bin/python scripts/benchmarks/t66e1_fixture.py
cd mobile
flutter test test/segmented_protocol_test.dart test/segmented_store_test.dart test/segmented_crash_test.dart --reporter expanded
```

committed fixture는 실제 서버 UUID/bytes/hash를 고정한 golden이며 모든 generation descendants를 포함한 download fixture는 아니다. regenerated UUID와 randomized Judgment 때문에 재생성 결과 전체 equality를 요구하지 않는다.

독립성 구분:

- **INDEPENDENT ORACLE:** 기존 T6.6C scalar vector 정상 8개/invalid 3개, 실제 서버 9종 object, 별도 SHA preimage 계산, 네 artifact exact bytes/length/SHA.
- **PERSISTED-STATE VALIDATION:** 직접 SQLite BLOB/count/FK/PRAGMA/schema 검사, fresh connection, 실제 SIGKILL 후 reopen, 기존 offline/Snapshot 파일 비교.
- **STRUCTURAL INVARIANT:** no accepted pointer, typed refs, atomic payload/edges/progress, resource budgets, independent 8-isolate valid/conflicting write.
- **SELF-CONSISTENCY ONLY:** Dart로 변형하고 재hash한 negative fixture는 golden 독립성 증거가 아니라 malformed shape/context 거부 증거다.

## Q. 실제 회귀 결과

검증 환경: Linux x86_64, Flutter 3.47.4 stable, Dart 3.13.3, Python 3.12, Android JDK 17. 테스트 DB/directory는 모두 disposable synthetic이다.

| 실행 | 실제 결과 |
| --- | --- |
| 신규 E1 targeted | **96 passed**, 실패 0 |
| 전체 Flutter | **635 passed, 2 skipped**, 실패 0 |
| 기존 Flutter 부분 | **539 passed**, 기존 diagnostic skip 2개 유지 |
| Flutter analyze | PASS, no issues |
| 신규 Dart format check | PASS, changed 0 |
| `flutter build apk --debug --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081` | PASS, APK 빌드만 수행 |
| backend 전체 pytest | **1,315 passed + 1,540 subtests passed**, 1 warning, 1,477.93초 |
| `scripts/tests scripts/benchmarks` pytest | **59 passed**, 1 warning |
| backend/scripts Ruff | PASS |
| backend/scripts compileall | PASS |
| frontend `npm run build` | PASS |
| `git diff --check` | PASS |

전체 backend 실행은 `backend`에서 `../.venv/bin/python -m pytest -q --junitxml=/tmp/money-note-e1-backend.xml`로 수행했다. D1/D2a/D2b/D3a/M01/M02/D3b/M01/D3c, schema/migration, 12 financial projections, Snapshot, authoritative-state 회귀가 포함된다. 새 E1은 backend 알고리즘을 변경하지 않았다.

기존 skip은 `mobile/test/diagnostics/t66a_payload_test.dart`의 opt-in 출력/HTTP 진단 2개다. backend/safety warning은 Starlette httpx deprecation이다. Android build는 기존 Gradle 8.14.3/AGP 8.11.1/Kotlin 2.2.20의 향후 지원 종료 warning을 냈지만 bypass flag 없이 성공했다. 이 작업에서 unrelated toolchain upgrade는 하지 않았다.

재현 명령:

```bash
cd mobile
flutter test --reporter expanded
flutter analyze
dart format --output=none --set-exit-if-changed lib/src/segmented test/segmented_protocol_test.dart test/segmented_store_test.dart test/segmented_crash_test.dart test/support/segmented_fixture.dart test/support/segmented_crash_worker.dart
flutter build apk --debug --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
cd ../backend
../.venv/bin/python -m pytest -q
cd ..
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts
git diff --check
```

## R. 알려진 한계

검증 범위는 host native SQLite/process crash와 Android debug compile이다. Android 실기기 저장 동작·전원 손실·OS crash·hardware flush를 검증했다고 주장하지 않는다. `EXTRA`는 SQLite VFS/OS/storage 가정에 의존한다. 배포 전 §26/§38의 driver/VFS/commit fence/실기기 proof가 추가로 필요하다.

현재 4개 release artifact만 지원하며 미래 schema/policy/engine은 명시적 업데이트 없이 수락하지 않는다. 검토한 exact artifact bytes를 비활성 asset으로 포함했지만 engine을 실행하거나 production capability를 광고하지 않는다. storage schema upgrade, object GC, cross-namespace migration, large object disk streaming은 미구현이다. 동기 API를 UI hot path에 바로 연결하는 것은 이 단계의 결정이 아니다.

읽지 않은 bitrot를 즉시 찾아낸다고 보장하지 않는다. hash-on-read 또는 명시적 scrub에서 fail-closed한다. local checksum은 authenticity signature가 아니다. full generation reconstruction/acceptance는 E1의 완료 주장에 포함하지 않는다.

## S. E2 handoff

E2는 authenticated response를 `ObservationManifest.fromBytes`/`ObjectChunk.parse`로 해석하고, 완성한 exact object bytes를 `putVerifiedObject`에 넘길 수 있다. `loadStaging`, paged identities, `recordStagedObject`는 중단된 progress 복구용이다. E2가 credential/ticket/lease/retry/typed-path authorization을 책임지며 hash나 local staging ID를 인증 수단으로 사용해서는 안 된다.

## T. E3에 명시적으로 유보한 책임

complete 11-table coverage, typed graph membership/closure, global Patricia facts/root, cross-object descriptor equality, hot/control/raw association, complete validation receipt, accepted/previous/frozen pins, native installation fence, pointer publication, B/J 및 reconciliation integration은 E3 이후다. E1에는 이 기능을 성공처럼 보이는 stub으로 만들지 않았다.

## U. Production isolation

normal startup/AppState/API/offline/screen/navigation에서 E1을 import하지 않는 source 검사와 테스트가 있다. 새 DB는 테스트/명시 호출로만 열린다. production DB/API/credential/service/.env에는 접근하지 않았다. segmented endpoint/sync는 활성화하지 않았다. 배포·APK 설치·production migration은 수행하지 않았다.

## V. Commit/push 확인 방법

모든 completion gate를 통과한 뒤 이 문서를 포함한 E1 변경만 `feat(flutter): add T6.6E1 segmented immutable client store`로 commit하고 origin/main에 push한다. 자기 참조 hash를 문서에 고정하지 않는다. 실제 최종 hash/원격 일치/clean 확인은 최종 작업 보고서에 기록하고 다음 명령으로 재확인할 수 있다.

```bash
git log -1 --format='%H %s' -- docs/t66e1-implementation.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --porcelain
```

commit/push는 배포 허가가 아니다.

## W. 독립 E1 감사 준비

E1 구현·내부 검증은 완료했고 알려진 Critical/High/Medium blocker는 없다. 이는 독립 감사의 대체가 아니다. 다음 단계는 **T6.6E1 독립 구현 감사**다. 감사 전 E2 시작 또는 production rollout을 승인하지 않는다.
