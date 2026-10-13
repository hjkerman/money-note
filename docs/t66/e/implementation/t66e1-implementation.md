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

규범은 `docs/t66/c/t66c-delta-sync-protocol.md` §7–15, §23–27, §30, §38과 `docs/architecture.md`의 서버 authority/클라이언트 신뢰 경계다. `docs/offline-mode.md`, `docs/domain-model.md`, `docs/project-state.md`, `docs/known-issues.md`, D3C-A01 재감사도 확인했다.

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
git log -1 --format='%H %s' -- docs/t66/e/implementation/t66e1-implementation.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --porcelain
```

commit/push는 배포 허가가 아니다.

## W. 독립 E1 감사 준비

E1 구현·내부 검증은 완료했고 알려진 Critical/High/Medium blocker는 없다. 이는 독립 감사의 대체가 아니다. 다음 단계는 **T6.6E1 독립 구현 감사**다. 감사 전 E2 시작 또는 production rollout을 승인하지 않는다.

## X. E1-A01 / E1-A02 TARGETED CORRECTION — 2026-10-12

### 1. 시작점과 과거 감사 보존

위 A–W는 최초 구현의 내부 완료 기록이다. 이후 독립 감사는 **FAIL — T6.6E1 CORRECTION REQUIRED**, MEDIUM 2건, independent case 67 PASS/6 FAIL을 보고했다. 이번 수정으로 과거 보고서의 FAIL을 지우거나 독립 재감사 PASS를 선언하지 않는다. `docs/t66/e/audits/t66e1-independent-audit.md`와 그 원본 재현·fixture·결과는 변경하지 않았다.

수정 시작은 `133391242b44573cfe3c1efb9950fa526be0b7f8`이다. branch main, HEAD/main/origin/main/실제 remote main 일치와 clean working tree를 확인했다. audited implementation은 `141e01186d589a9071ae6a3d0c0023a6472c014d`다.

### 2. 수정 전 원본 재현

원본 `docs/benchmarks/t66e1-audit/test_audit.py`의 `-k 'money or trigger'` 실행은 **7 PASS/6 FAIL/60 deselected**였다. 원본 `reproduce_findings.py`도 실행했다. 과거 evidence를 덮지 않도록 `Path.write_text`의 `findings.json` 출력 목적지만 `/tmp/mn-e1-correction-before-findings.json`으로 redirect했다. 실행 로직·oracle·assertion은 바꾸지 않았다.

| 반례 | 서버/SQLite 직접 관측 | 수정 전 Dart |
| --- | --- | --- |
| `\u001c+0001000.00\u001c` | 실제 D2b bootstrap 및 인증 ASGI manifest 201/object 200 | MONEY_STRING_INVALID |
| 같은 문자열의 U+001D, U+001E, U+001F 변형 | 각각 201/200, 원문 및 별도 hashlib 일치 | 각각 MONEY_STRING_INVALID |
| `\ufeff1000\ufeff` | 실제 `setting_money`가 REJECT_SETTING_MONEY | hash-valid leaf 검증 성공 |
| 빈 정상 E1 store에서 `object_usage` DROP 뒤 limit=1로 서로 다른 두 정상 객체 put | 실제 objects=2, payload=6,591, usage.objects=0/payload=0, integrity ok/FK 오류 0 | 둘 다 COMMIT 성공; reopen 때야 STORE_METADATA_CORRUPT |

이 재현은 새 disposable SQLite만 사용했다. BOM negative leaf를 인증 서버가 전달했다고 주장하지 않는다.

### 3. E1-A01 원인·서버 문법·변경

authority는 `backend/isolated_sync/raw.py:setting_money`다. 서버는 검증용 `str.strip()` 뒤 `[+-]?[0-9]+(?:\.0+)?`를 **fullmatch**하고 Decimal로 finite/integral/절댓값 `≤9007199254740991`을 확인한다. `Row.make/admit_row`는 통과한 **원문**을 encode하며 trim한 문자열로 저장하지 않는다.

현재 서버 Python의 whitespace는 정확히 29개다:

`U+0009–000D`, `U+001C–0020`, `U+0085`, `U+00A0`, `U+1680`, `U+2000–200A`, `U+2028`, `U+2029`, `U+202F`, `U+205F`, `U+3000`.

앞·뒤에서만 이 문자를 제거한 검증 view를 사용한다. 내부 whitespace, U+FEFF, U+180E, U+200B, U+2060, NUL, ASCII 외 숫자는 numeric grammar에서 거부된다. empty/whitespace-only, exponent, underscore, fractional/nonfinite도 거부된다.

`mobile/lib/src/segmented/object.dart:_settingMoneyText`가 이 집합을 명시적으로 적용한다. `.trim()` 호출 하나를 교체했으며 grammar·BigInt range 검사는 유지한다. 입력 row/string/object bytes를 수정하지 않고 float 변환도 하지 않는다. C1 encoder/hash domain, backend grammar, 금융 공식은 변경하지 않았다.

### 4. 독립 differential oracle

`scripts/benchmarks/t66e1_money_vectors.py`는 실제 Python `isspace()`를 전체 Unicode codepoint 범위에서 열거하고 실제 `setting_money`, `Row.make`, `segments.leaf`를 호출한다. DB/API는 열지 않는다. 정상 객체의 C1을 별도 Python JSON으로 대조하고 hashlib로 expected Ref를 계산한다. negative 객체는 untrusted hash-valid 자료로 구분한다.

`mobile/test/fixtures/segmented_money_vectors.json`에는 **165 vectors: 서버 accept 98/reject 67**과 29개 whitespace 목록이 고정되어 있다. 기본 양수/음수/zero/large/sign/leading zero/`.0`, whitespace 각각의 leading/trailing/both/internal, BOM 세 위치, 다른 format/control 문자, 빈 문자열과 malformed grammar를 포함한다. Unicode synthetic `updated_at`도 보존한다.

`segmented_money_correction_test.dart`는 모든 vector의 서버 boolean, expected canonical length/hash, Dart 결과를 대조한다. accept 98개는 SQLite put→close→reopen→get과 직접 BLOB 조회에서 원문 문자열/bytes를 확인한다. 다섯 monetary setting key에도 동일 검사를 추가했다. 총 **166 Flutter tests**다. `scripts/benchmarks/test_t66e1_money_vectors.py`는 committed fixture를 현재 backend로 재생성해 직접 대조한다.

### 5. E1-A02 원인과 정의 검증

기존 open은 user_version/profile/8개 table/현재 usage만 검사했고 trigger의 미래 accounting 효과를 확인하지 않았다. `_transaction`은 trigger가 갱신했어야 할 usage만 믿었으므로, `object_usage`가 없으면 실제 insert가 counter에 반영되지 않아 잘못 COMMIT했다.

`mobile/lib/src/segmented/store.dart:_schemaDefinitions/_requireSchema`를 추가했다. 기존 `_schema` initialization DDL을 단일 원본으로 사용해 실제 `sqlite_master.sql`과 **8개 table + 1개 index + 11개 trigger**의 정의를 exact 비교한다. table의 FK/PK/CHECK 및 trigger의 event/table/WHEN/body까지 검사한다. 이름만 맞는 no-op, accounting 약화, 다른 event/table, 추가 trigger, table 변경도 거부한다. SQLite가 저장할 때 제거하는 마지막 semicolon만 trusted DDL에서 제외한다.

동일 의미의 다른 SQL formatting도 이 closed schema에서는 보수적으로 unsupported다. damaged schema는 `STORE_SCHEMA_CORRUPT`, 지원하지 않는 user_version은 기존 `UNSUPPORTED_STORAGE_SCHEMA`다. 자동 trigger 재생성/수리·schema migration·version bump는 없다. 정상 기존 E1 DB의 DDL 자체는 바뀌지 않았다.

### 6. Transaction/connection guarantee

검사는 open의 locked admission, **모든 `_transaction`에서 BEGIN IMMEDIATE 성공 직후·변경 SQL 전**, 명시 health scrub에 적용된다. connection-local PASS flag나 schema-cookie만 cache하지 않는다. 따라서 이미 열린 connection에서도 다음 write에 반드시 다시 확인한다. put/duplicate put/staging/progress/cleanup이 같은 경계를 공유한다.

SQLite는 write transaction을 직렬화하며 CREATE/DROP도 write다. 성공한 BEGIN IMMEDIATE 안에서 확인한 schema는 다른 정상 SQLite connection의 DDL COMMIT으로 중간에 교체되지 않는다. [SQLite transaction](https://www.sqlite.org/lang_transaction.html), [isolation](https://www.sqlite.org/isolation.html)의 계약과 실제 native driver 테스트를 대조했다.

`write transaction excludes concurrent DDL after schema validation`은 실제 별도 connection으로 validation 이후 `before_object_insert`에서 DROP을 시도해 SQLITE_BUSY(5)를 확인한다. 보호 transaction 뒤 DROP은 가능하지만 다음 write는 schema 오류로 거부한다. 이는 추측한 timing race가 아니라 동기 checkpoint다. schema DDL rollback 뒤 정상 duplicate write와 quota 초과 rollback도 확인한다.

검사 실패는 기존 transaction finally에서 ROLLBACK하며 lock/부분 Ref/receipt를 남기지 않는다. caller는 private connection을 직접 받지 않는다. 보장은 정상 SQLite API/locking 모델에 근거하며 raw filesystem 조작이나 `writable_schema`를 통한 임의 엔진 내부 변조까지 방어한다고 주장하지 않는다.

### 7. Committed-row 증거와 schema 정책

수정 후 원본 reproduction은 trigger 누락을 open에서 차단해 **actual objects=0**이다. 사용자 요청의 추가 조건인 “limit=1, 첫 객체 정상 COMMIT, 별도 connection에서 DROP, 열린 connection으로 두 번째 put”도 영구 회귀로 실행했다. 결과는 **actual objects=1, usage.objects=1, 추가 committed objects=0**이다.

`segmented_schema_correction_test.dart`의 `preserved`는 매 destructive test 뒤 fresh SQLite connection으로 원래 identity/BLOB, payload counter, exact staging manifest, 네 root/progress, integrity/FK, 새 write lock 획득을 확인한다. 총 **45 tests**다.

11개 trigger 각각의 before-open 누락, after-open 누락, correct-name/no-op 변조 33개와 weakened body/WHEN/event/table 4개, 재사용 write API 4개, DDL lock/rollback/extra trigger·table/version 경계 4개다. 기존 concurrent valid/conflicting isolate 회귀도 유지한다.

이미 열린 handle의 read는 원래 객체를 full reverify하여 읽을 수 있으나, schema가 손상된 DB의 **새 open은 차단**한다. 이는 원래 bytes를 삭제하지 않는 fail-closed 복구 정책이며 자동 repair를 제공하지 않는다. 별도 SQLite inspection으로 prior good data 보존을 확인한다.

기존 `segmented_store_test.dart`의 payload/kind/validator corruption setup은 임의 UPDATE를 위해 내린 `immutable_body`를 테스트 setup에서 원래 SQL로 복원한다. 기존 corruption assertion은 모두 그대로다. 이렇게 payload 손상과 새 schema 손상 검사를 분리하며, production 구현이 schema를 repair하는 것은 아니다.

### 8. 원본 실패 여섯 건의 수정 후 결과

원본 감사 코드/fixture를 변경하지 않고 전체 **73 PASS/0 FAIL**을 재실행했다. 수정 전/후 JUnit testcase name으로 다음 여섯 건을 개별 대조했다.

| 원본 case | finding | 수정 후 |
| --- | --- | --- |
| `test_every_server_admitted_money_string_is_accepted[setting-3]` — U+001C | E1-A01 | PASS |
| 같은 test의 `[setting-4]` — U+001D | E1-A01 | PASS |
| 같은 test의 `[setting-5]` — U+001E | E1-A01 | PASS |
| 같은 test의 `[setting-6]` — U+001F | E1-A01 | PASS |
| `test_server_rejected_bom_money_is_rejected` | E1-A01 | PASS |
| `test_missing_schema_trigger_is_rejected_before_writes` | E1-A02 | PASS |

원본 실제 ASGI reproduction도 네 문자열 모두 201/200→Dart 저장 성공, BOM→Dart 거부로 바뀌었다. 재실행 주체는 구현자이며 **독립 targeted 재감사 완료가 아니다**.

### 9. 회귀와 process crash

| 이번 수정 세션의 실행 | 결과 |
| --- | --- |
| 신규 correction Flutter | 211 PASS/0 FAIL: money 166 + schema 45 |
| 기존 E1 targeted | 96 PASS/0 FAIL |
| 전체 Flutter | 846 PASS/0 FAIL/기존 2 SKIP |
| 원본 독립 감사 코드 재실행 | 73 PASS/0 FAIL, 위 여섯 실패 모두 PASS |
| backend-derived oracle 재생성 | 1 PASS |
| safety/diagnostic + oracle | 60 PASS, 기존 deprecation warning 1 |
| Flutter analyze/format | PASS |
| Android debug APK build | PASS, 설치 없음 |
| backend full regression | **1,315 PASS + 1,540 subtests PASS**, 기존 warning 1, 1,657.12초 |
| Ruff/compileall/frontend npm build/diff check | PASS |

전체 Flutter에는 OfflineBaseline v4/frozen B/J/Snapshot과 기존 실제 SIGKILL **7개 경계**가 포함되고 기존 E1 targeted에서도 재실행했다. 원본 audit의 progress/cleanup 등 SIGKILL 8개 parameter도 전체 73개 실행에 포함된다. 새 schema 검사는 mutation 전 기존 transaction 안의 read-only 검사이므로 새로운 publication/COMMIT boundary는 없다. 이전 객체·staging 복구, no active generation을 계속 검증한다. OS crash/hardware power loss 보장은 추가하지 않는다.

재현 명령은 개발 checkout에서 다음과 같다. 원본 reproduction의 evidence 출력 redirect는 위 2절과 같으며 감사 `findings.json`을 덮어쓰지 않아야 한다.

```bash
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
PYTHONPATH=backend .venv/bin/python scripts/benchmarks/t66e1_money_vectors.py
cd mobile
flutter test test/segmented_money_correction_test.dart test/segmented_schema_correction_test.dart
flutter test test/segmented_protocol_test.dart test/segmented_store_test.dart test/segmented_crash_test.dart
flutter test
flutter analyze
flutter build apk --debug --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
cd ../backend
../.venv/bin/python -m pytest -q
cd ..
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts
git diff --check
```

### 10. Resource/performance 영향과 한계

기존 예산, parser depth, object format/size, journal/durability profile은 그대로다. 일반 write에 user_version query와 최대 21개 schema row 조회/20개 exact 정의 대조만 추가된다. 객체/BLOB/ledger 전체 scan을 추가하지 않았다. 기존 startup usage 검사와 explicit scrub의 O(N)은 유지한다. 금액 검증도 문자열 양끝을 선형 확인할 뿐 원문·금융 계산을 다시 만들지 않는다.

같은 host Dart JIT process에서 baseline store source와 수정 store를 별도 synthetic directory에 열어 동일 9종 객체를 저장한 뒤, 3 warmups/20 samples의 작은 비교를 실행했다. control object 기준이며 실제 mutation/운영 latency가 아니다.

| operation | 수정 전 median/p95 µs | 수정 후 median/p95 µs |
| --- | --- | --- |
| get | 4,179.5 / 4,777 | 2,166 / 3,998 |
| duplicate put | 3,711 / 4,289 | 3,793 / 4,080 |

4개 cell/80 samples의 순차 JIT microbenchmark이며 get source는 변경되지 않았다. JIT/병행 regression noise 때문에 get 개선이나 엄격한 overhead 상한을 주장하지 않는다. duplicate put은 이 표본에서 median 약 82µs 차이였다. full-dataset scaling/실기기 benchmark를 대신하지 않는다. 재현 전후의 committed-row 수, fixture digest, 회귀와 측정치는 [축약 수정 증거](../../../benchmarks/t66e1-correction/summary.json)에 보존한다.

equivalent DDL의 자동 호환·schema repair, 외부 임의 행 조작의 즉시 탐지, Android 실기기 power-loss, E2/E3는 여전히 범위 밖이다. object read는 매번 재검증하므로 이전 validator flag만으로 BOM 객체를 자동 수락하지 않는다.

### 11. Production 격리·commit·다음 gate

변경 source는 E1 `object.dart`/`store.dart`뿐이다. 기존 test setup 한 곳, focused tests/server-derived fixture·generator/oracle, 이 addendum과 compact evidence만 추가한다. 독립 audit source/report, backend runtime, normal Flutter startup/read/write/online sync/UI/navigation/Android 설정은 변경하지 않는다.

Production SQLite v4, Snapshot v7, OfflineBaseline v4, Android v2.4.0(15), frozen B/J publication, 금융 projection/공식/authority는 유지한다. production DB/API/credential/service/backup 접근, migration, restart, 배포, APK 설치, segmented 활성화는 없다.

이번 수정의 completion gate를 모두 내부 검증했다. `fix(flutter): correct T6.6E1 monetary validation and trigger integrity`로 commit/push하며, 실제 commit hash와 HEAD/main/origin/main/remote main/clean 결과는 최종 응답 및 위 V절 명령으로 확인한다. 구현 판정은 **E1-A01 AND E1-A02 FIXED — READY FOR INDEPENDENT TARGETED RE-AUDIT**다. 다음 gate는 **E1-A01/E1-A02 독립 targeted 재감사**이며, 그 PASS 전 E2 시작을 승인하지 않는다.
