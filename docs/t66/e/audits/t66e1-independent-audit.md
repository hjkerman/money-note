# T6.6E1 독립 구현 감사

## A. 감사 대상과 기준선

**FAIL — T6.6E1 CORRECTION REQUIRED**

대상은 `141e01186d589a9071ae6a3d0c0023a6472c014d`, 기준선은
`9ee495e970a02c9810b4519eb0730612fa4f6349`다. 감사 일자는 2026-10-12다.
구현을 변경하지 않고 **MEDIUM 2건**을 확인했다. 서버 금액 문자열 계약 불일치와
불완전한 SQLite schema 수락이 E1 및 E2 handoff를 차단한다.

기존 E1 **96개**, 전체 Flutter **635개 및 기존 skip 2개**, backend **1,315개 및
1,540 subtests**는 실제로 통과했다. 독립 감사의 실패는 기존 회귀의 통과와 별개의
증거다. 발견한 반례를 수정하거나 테스트 기대값을 완화하지 않았다.

## B. Git 및 remote 검증

시작 시 `main`, clean working tree였고 `HEAD = main = origin/main = 실제 remote
main = 141e01186d589a9071ae6a3d0c0023a6472c014d`를 확인했다. remote는
`git ls-remote origin refs/heads/main`으로 직접 조회했다. 감사 중에도 같은 상태를
재확인했다. 다른 revision을 대신 감사하거나 사용자 변경을 reset하지 않았다.

```sh
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --porcelain
git diff --stat 9ee495e..141e01186d589a9071ae6a3d0c0023a6472c014d
```

## C. 범위와 독립성

AGENTS, project-state, domain-model, known-issues, architecture의 신뢰 경계,
offline-mode, binding T6.6C, E1 구현 보고서, D3C-A01 재감사를 읽었다. 실제 서버의
`canonical.py`, `raw.py`, `segments.py`, `patricia.py`, `roots.py`, `store.py`,
`finalization.py`, `observation.py`, `transfer.py`, `http.py`, retention 경계를 대조했다.

새 감사 코드는 구현자의 테스트를 import하지 않는다. 선행 **독립** D3c 감사의
synthetic 11-table seed, 실제 서버 encoder/presenter, 별도 Python JSON/hashlib,
fresh SQLite connection, 별도 Dart process를 사용했다. 서버 helper로 생성한 자료,
직접 persisted state 검증, source-level 증거를 구분한다.

E2 transport, E3 closure/publication, rollout은 감사 대상이 아니다. 그 기능이 없다는
이유로 finding을 만들지 않았다. 금융 projection을 Dart에서 재계산하지 않았다.

## D. 구현 diff 목록

완전한 diff는 **15개 파일, +2,882/-4**다.

| 파일 | 확인한 변경 |
|---|---|
| `mobile/lib/src/segmented/c1.dart` | C1 decode/encode 및 domain hash, 295줄 |
| `mobile/lib/src/segmented/protocol.dart` | Target/manifest/chunk/cache model, 340줄 |
| `mobile/lib/src/segmented/object.dart` | 9종 개별 object 검증, 383줄 |
| `mobile/lib/src/segmented/store.dart` | 별도 SQLite object/staging store, 532줄 |
| `mobile/pubspec.yaml`, `mobile/pubspec.lock` | sqlite3 3.7.0, native build용 dependency 변경 |
| `mobile/assets/segmented/isolated-release-artifacts.json` | 비활성 release compatibility 자료 |
| `mobile/test/segmented_protocol_test.dart` | protocol/negative/golden 검사 |
| `mobile/test/segmented_store_test.dart` | 저장·복구·quota·격리 검사 |
| `mobile/test/segmented_crash_test.dart` | 실제 SIGKILL 7경계 |
| `mobile/test/support/segmented_fixture.dart`, `segmented_crash_worker.dart` | fixture와 child process |
| `mobile/test/fixtures/segmented_server_golden.json` | 서버 golden |
| `scripts/benchmarks/t66e1_fixture.py` | synthetic 서버 fixture 생성기 |
| `docs/t66/e/implementation/t66e1-implementation.md` | 구현 보고서 |

Lockfile에는 glob 2.2.0, native_toolchain_c 0.19.3, sqlite3 3.7.0 추가와 hooks
2.0.2→2.2.0, record_use 0.6.0→1.1.1 변경이 있다. 기존 Flutter runtime source,
backend source, Android 설정, 금융 공식, Snapshot v7, frozen B/J는 diff에 없다.

## E. 서버 protocol 계약

T6.6C §7–15, §23–26과 실제 서버 코드를 대조했다. Object identity는 kind별
`SHA-256(ASCII("money-note.sync.v1/" + kind) + NUL + exact C1 bytes)`다.
서버의 NS/canon/raw schema, typed Ref, 11-table raw root, snapshot leaf/node,
Patricia local structure, hot/control, Target view hash, 900초 lease,
1 MiB chunk/inline 합계와 64-item 상한은 Dart model에 대응한다.

원문 JSON의 int/REAL, `-0.0`, Unicode scalar, escape 및 key 순서를 보존하는 C1
계층은 독립 corpus에서 일치했다. Outer manifest JSON은 비정규 whitespace를
허용하고 immutable object는 exact canonical bytes를 요구하는 구분도 맞다.
단, raw monetary setting의 whitespace admission은 **E1-A01로 불일치**한다.

실제 D3b는 네 transferable root만 허용하며 internal input-proof는 공개 download
capability가 아니다. E1의 9종 allow-list와 네 staging root는 이를 유지한다.
Capability 협상, credential/echo/path 확인, chunk 조립은 E2의 책임으로 남아 있다.

## F. 독립 C1/hash golden 증거

새 synthetic D2b/D3a generation에서 읽은 **29개 object, 9종, 177,465 payload
bytes**를 별도 JSON canonical encoding과 hashlib로 대조했다. 원문을 Dart로
만들어 기대 hash를 계산하지 않았다. 같은 NS의 raw/hot/control과 internal graph의
개별 object 자료이며 완전한 generation 다운로드 fixture라고 주장하지 않는다.

고정 seed `6601`의 **128개** C1 vector는 int64 양끝, 지원 REAL 최대값,
negative zero, 조합/분해 Unicode, 비 BMP 및 UTF-8 key 순서, NUL/control 문자를
포함한다. 모든 원문 byte 및 view-domain hash가 일치했다. 비정규 key 순서,
duplicate/escaped duplicate key, rounding/underflow REAL, 잘못된 UTF-8,
surrogate, int64 초과, NaN, depth 초과의 독립 거부 검사도 통과했다.

## G. Immutable identity

`object.dart:114`는 입력을 소유한 copy로 만든 뒤 길이, C1, kind/domain hash,
NS/version, shape를 검사한다. `store.dart:228`의 put은 이 검사 후 transaction에
들어간다. 중복 insert는 기존 bytes를 재검증하고 다른 bytes·truncation·epoch·canon
변경은 거부했다. `store.dart:262`의 read는 BLOB와 validator/edge catalog를 다시
검증한다. 직접 SQLite에서 읽은 bytes/hash도 일치했다.

`VERIFIED`가 hash 불일치 bytes를 반환하는 반례는 발견하지 않았다. 그러나 동일
whitespace 결함으로 서버가 거부하는 BOM 금액 row를 개별 검증 성공으로 반환했다.
이것은 hash 무결성의 실패가 아니라 **지원 row-format admission의 불일치**다.

## H. SQLite transaction과 영속성

별도 caller private root의 `segmented-store-v1/<cache.key>.sqlite`만 사용한다.
8개 table, user_version 1, profile discriminator, DELETE journal,
synchronous EXTRA, FK ON을 설정하고 readback한다. write는 BEGIN IMMEDIATE로
Ref/BLOB/edges/usage 또는 staging/roots/progress를 함께 COMMIT한다.

직접 SQLite 검사에서 실패한 insert의 부분 payload/edges, 누수 write lock,
다른 good object 손상은 없었다. 실제 64-page 한도의 SQLITE_FULL(13), busy 오류,
복구 후 다음 write도 확인했다. 다만 open은 table 이름과 현재 counter만 검사하고
필수 trigger 자체를 확인하지 않아 **E1-A02**가 발생한다.

## I. 실제 process-crash 복구

기존 E1 7개 SIGKILL 경계는 실제 child process 종료이며 exception injection만
사용한 검사가 아니다. 독립 child process로 8개 interleaving을 추가 실행했다.
그중 progress INSERT/COMMIT 및 staging cleanup COMMIT 전후 4개는 기존 7개에
없던 경계다. **구분되는 총 11개 경계**의 process-crash 증거가 있다.

stdout 준비 알림 뒤 SIGKILL하며 임의 delay로 시점을 추측하지 않는다. 이후 fresh
Python connection과 새 Dart process에서 원래 good object, 신규 object/staging의
전부 존재 또는 부재, usage, FK/integrity, 추가 write lock 획득을 확인했다. 활성
generation은 생성되지 않았다. OS crash 및 hardware power loss는 검증하지 않았다.

## J. 동시성

독립 Dart process 4개를 open barrier에서 동기화한 동일 write는 단일 object로
수렴했다. valid/conflicting 2+2 write에서는 valid만 성공하고 원문이 보존됐다.
미COMMIT writer와 이미 열린 reader의 interleaving에서는 reader가 기존 object만
보고 신규 payload를 보지 않았다. writer COMMIT 뒤 fresh read는 신규 object를
확인했다. SQLite write lock 경합은 STORE_BUSY로 거부되고 lock 해제 뒤 복구됐다.

## K. Staging metadata

`store.dart:323`의 create와 `:357`의 progress는 atomic하다. 실제 payload가 없는
Ref는 progress로 기록되지 않는다. 같은 object의 중복 progress는 idempotent이며
restart 뒤 count/manifest/네 root가 유지됐다. checksum 및 root-role 손상은 거부했다.
명시적인 cleanup은 staging/progress와 무참조 placeholder만 제거하고 기존 object를
보존했다. cleanup 뒤 staging quota도 다시 사용할 수 있었다.

`loadStaging`은 progress count를 반환하므로 E2는 그것만으로 재사용을 승인하면
안 된다. 재사용 object는 get의 hash/shape 검사와 새 observation/path 조건을 거쳐야
한다. `inspectStoreHealth`는 별도로 progress payload까지 검사한다.

## L. 신뢰 경계의 분리

Object integrity, generation membership, observation authorization은 API에서
분리돼 있다. `VerifiedObject`에는 complete/active/authorized flag가 없다.
`StagingSession.validationState`는 항상 `staged`이며 accepted/active/generations
table 및 pointer가 없다. 일부 raw root만 저장해도 개별 integrity receipt는 생성되지만
graph completeness나 설치 권한으로 광고하지 않는다.

E2는 auth/lease/request/path/transport, E3는 complete closure·11-table association·
global Patricia·hot/control/raw/context·publication fence를 담당해야 한다. 이 유보는
현 단계의 결함으로 분류하지 않았다.

## M. Corruption과 오류 처리

직접 변경한 BLOB, kind, validator, edge, payload 누락, usage, staging checksum,
staging root의 손상은 open/read/health에서 거부됐다. 알 수 없는 `.pending` 파일은
읽어 들이거나 삭제하지 않았다. user_version 99는 유지한 채 open을 거부했다.
SQLITE_FULL과 busy 뒤 기존 good object가 보존됐고 fresh connection의 transaction이
가능했다. 임의 I/O 장치 고장과 OS filesystem failure 전체를 검증하지는 않았다.

schema trigger 누락은 예외다. 쓰기 전에는 수락하고 성공 COMMIT 뒤 다음 open에서
counter 손상으로 거부하므로 fail-closed 시점이 늦다.

## N. Resource bounds

기본 object 64 MiB, 전체 payload 512 MiB, object 100,000개, manifest 8 MiB,
metadata 32 MiB, staging 128개, parser depth 128, enumeration page 1,024개는
명시적 local policy다. 1 MiB는 chunk 상한이며 전체 object 상한과 다르다.
독립 검사에서 1 MiB를 넘는 정상 oversized singleton을 저장했고 작은 object 예산,
count/metadata 예산 및 실제 SQLite page limit 초과는 rollback됐다.

정상 schema에서는 이 제한이 작동하지만 누락 trigger의 schema admission이
counter를 무력화하므로 전체 resource-bound 판정은 FAIL이다. 기본 한도를 전부
소진하는 stress나 64 MiB 최대 object의 peak memory는 측정하지 않았다.

## O. 기존 application 격리

새 segmented 디렉터리를 제외한 `mobile/lib`에는 E1 import/생성 경로가 없다.
startup/AppState/기존 repository/API/offline/screen에는 diff가 없다. 실제 기존
OfflineStore와 Snapshot repository를 사용한 격리 테스트도 통과했다. 독립 검사에서는
같은 private root의 synthetic baseline/J/Snapshot opaque bytes가 그대로 보존됐다.

Native sqlite3 dependency와 비활성 asset은 APK에 추가되지만 정상 금융 read/write나
segmented endpoint를 활성화하지 않는다. Backend source diff는 0이다.

## P. 금융 데이터 보존

양수/음수/zero/큰 금액, leading sign/zero/소수부 `.0` 문자열과 Unicode의 원문 byte
보존을 확인했다. E1은 서버가 준 값의 shape/domain을 검사하며 할인·합계·projection을
재계산하지 않는다. 다만 일부 지원 금액 문자열을 거부하는 E1-A01 때문에 모든 유효한
서버 자료를 저장할 수 있다는 보장은 성립하지 않는다. 금융 값 변경이나 손실이
발생했다는 증거는 없으며 모든 실험 데이터는 synthetic이다.

## Q. 독립 scenario matrix

아래 34개 필수 항목은 새 실행·직접 oracle·source proof 및 필요한 기존 회귀를
명시적으로 구분한다. 개별 parameter 실행 결과는 `results.json`에 보존한다.

| 번호·scenario | 기대값 | 관측값·독립 oracle | 판정 |
|---|---|---|---|
| 01 서버 C1 golden | exact bytes | 서버 encode + 별도 JSON, 128개 일치 | PASS |
| 02 서버 hash | domain SHA-256 일치 | hashlib와 29개 원문 일치 | PASS |
| 03 malformed input | 명시 거부 | 중복 key/UTF-8/REAL 등 12개 거부 | PASS |
| 04 unsupported version | 거부 | rehash한 canon/manifest version 거부 | PASS |
| 05 write/reopen/read | 동일 payload | fresh process + 직접 BLOB/hash | PASS |
| 06 duplicate | 단일 객체 | 직접 object/usage/edges | PASS |
| 07 conflict | 기존 객체 보존 | altered bytes 거부 + 직접 조회 | PASS |
| 08 stored corruption | 검증 성공 금지 | 직접 BLOB 변경 후 read 거부 | PASS |
| 09 truncation | 거부 | 원문 마지막 byte 제거 후 거부 | PASS |
| 10 missing payload | 검증 성공 금지 | 직접 DELETE 후 open/read 거부 | PASS |
| 11 context | epoch 혼용 거부 | 독립 재hash epoch 변경 object 거부 | PASS |
| 12 Unicode | 정규화 금지 | 6종 leaf의 exact persisted bytes | PASS |
| 13 monetary string | 서버 admission과 일치 | control 4종 거부/BOM 수락 | FAIL |
| 14 insert 중단 | 원자적 부재 | SIGKILL + fresh SQLite/Dart | PASS |
| 15 staging 중단 | 원자적 부재 | INSERT 뒤 SIGKILL + 네 root 확인 | PASS |
| 16 COMMIT 직후 | 전체 상태 복구 | object/stage/progress/cleanup 직접 조회 | PASS |
| 17 fresh recovery | 이전 good 객체 보존 | 새 process hash/read/write lock | PASS |
| 18 동일 concurrent write | 단일 identity | 4개 process + 직접 행 검사 | PASS |
| 19 conflicting concurrent write | valid만 성공 | 2+2 process와 BLOB 비교 | PASS |
| 20 reader/writer | dirty read 금지 | deterministic pre-COMMIT barrier | PASS |
| 21 invalid staging | 거부, 활성화 금지 | checksum/role 손상 후 explicit error | PASS |
| 22 orphan temp | 자동 수락/삭제 금지 | opaque `.pending` bytes 보존 | PASS |
| 23 storage full/write error | rollback, good 보존 | 실제 SQLITE_FULL(13)/busy + 직접 조회 | PASS |
| 24 schema incompatibility | 쓰기 전 거부 | version 99 거부, trigger 누락은 수락 | FAIL |
| 25 size limit | 예산 거부/대형 정상 허용 | local budget 및 1 MiB 초과 singleton | PASS |
| 26 membership | integrity와 분리 | 부분 root 저장, complete flag/table 없음 | PASS |
| 27 authorization | E1이 부여하지 않음 | source/API에 credential·authorized flag 없음 | PASS |
| 28 active publication | 없어야 함 | schema 직접 조회 및 source | PASS |
| 29 OfflineBaseline v4 | 불변 | 기존 실제 fixture test + 독립 byte 검사 | PASS |
| 30 frozen B/J | 불변 | source diff/전체 offline 회귀/byte 검사 | PASS |
| 31 Snapshot v7 | 불변 | source diff/실제 repository test/회귀 | PASS |
| 32 startup | 비활성 | import inventory + full Flutter | PASS |
| 33 Flutter read/write | 기존 경로 유지 | 기존 runtime diff 0 + full suite | PASS |
| 34 backend runtime | 불변 | backend diff 0 + full backend | PASS |

## R. 전체 회귀 결과와 명령

| 독립 실행 | 관측 결과 |
|---|---|
| 기존 E1 Flutter | 96 PASS, 0 FAIL |
| 전체 Flutter | 635 PASS, 0 FAIL, 기존 diagnostic 2 SKIP |
| 독립 audit corpus | 67 PASS, 6 FAIL, 0 INCONCLUSIVE; finding은 2건 |
| Flutter analyze | PASS, no issues |
| 기존 E1 Dart format | PASS, 9 files, 0 changed |
| Android debug build | PASS, APK compile만 수행 |
| Backend full | 1,315 PASS + 1,540 subtests PASS, 1 warning, 1,626.32초 |
| Safety/diagnostic | 59 PASS, 1 warning |
| Ruff 및 compileall | PASS, backend/scripts 및 감사 Python |
| 감사 Dart analyze/format | PASS |
| Frontend npm build | PASS |
| git diff --check | PASS |

Backend JUnit의 `tests=2855`는 1,315 tests와 1,540 subtests의 합이다. 두 수를
별도 full tests로 중복 계수하지 않았다. Starlette/httpx deprecation warning과 기존
Android toolchain 경고가 있었으나 build/test 실패는 없었다.

```sh
cd mobile
flutter test --no-pub --machine test/segmented_protocol_test.dart test/segmented_store_test.dart test/segmented_crash_test.dart
flutter test --no-pub --machine
flutter analyze --no-pub
dart format --output=none --set-exit-if-changed lib/src/segmented test/segmented_protocol_test.dart test/segmented_store_test.dart test/segmented_crash_test.dart test/support/segmented_fixture.dart test/support/segmented_crash_worker.dart
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=http://10.0.2.2:18081
cd ../backend
../.venv/bin/python -m pytest -q --durations=10 --junitxml=/tmp/mn-d3c-a01-reaudit/backend.xml
cd ..
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py
.venv/bin/python docs/benchmarks/t66e1-audit/reproduce_findings.py
git diff --check
```

Backend runner의 출력 경로 이름은 선행 감사 임시 디렉터리를 재사용했지만, current
commit에서 새로 실행한 process의 종료와 파일 timestamp를 확인한 뒤 E1 evidence
디렉터리로 복사했다. 과거 실행 결과를 현재 실행으로 계수하지 않았다.

## S. Findings

### E1-A01 — MEDIUM: 서버와 다른 monetary whitespace admission

**CONFIRMED FAILURE. E2 차단: YES.**

Source: `mobile/lib/src/segmented/object.dart:235`–239,
`backend/isolated_sync/raw.py:80`–90 및 `:120`–122.
Binding: T6.6C §7/§23의 raw monetary contract와 exact byte 보존.

서버는 Python `str.strip()` 뒤 금액 문자열 문법을 검사한다. Dart `String.trim()`은
동일한 whitespace 집합이 아니다. 서버가 제거하는 U+001C~U+001F를 Dart는 남기며,
서버가 남기는 U+FEFF를 Dart는 제거한다. Hash/C1 자체가 맞아도 row admission은
양방향으로 불일치한다.

최소 재현은 `reproduce_findings.py`다. 새 synthetic DB의
`base_next_month_liquidity`에 `U+001C + "+0001000.00" + U+001C`를 보존하고
실제 D2b bootstrap, 인증된 D3b observation POST 및 typed-path object POST를
수행한다. **201/200**, 원문 SQLite 값 및 hashlib identity가 모두 정상인데 E1
put은 `MONEY_STRING_INVALID`로 거부한다. U+001D/E/F도 동일했다. 별도 11종
server Row.make/leaf corpus에서는 정상 control 4종이 실패했다.

반대 방향으로 서버 `setting_money("\uFEFF1000\uFEFF")`는
`REJECT_SETTING_MONEY`지만 같은 문자열을 가진 hash-valid leaf는 E1에서 성공한다.
이 negative object는 인증된 서버가 전달했다고 주장하지 않는다.

기대값은 서버가 지원하는 정확한 row 문법을 같은 방식으로 판정하면서 원문 bytes를
그대로 저장하는 것이다. 영향은 유효한 retained raw state의 E2 취득/저장 실패와
잘못된 row-format receipt다. 금융 재계산·무단 설치·데이터 유출의 증거는 없다.

최소 수정은 검증용 whitespace 판정을 서버 계약과 일치시키는 것이다. 저장 문자열을
trim/normalize하거나 지원 서버 값을 변경해서는 안 된다. U+001C~U+001F, U+FEFF,
기존 Unicode whitespace, 부호/zero/`.0` 및 원문 hash 보존을 회귀로 고정해야 한다.

### E1-A02 — MEDIUM: 필수 schema trigger 누락 뒤 quota 초과 COMMIT

**CONFIRMED FAILURE. E2 차단: YES.**

Source: `mobile/lib/src/segmented/store.dart:133`–155의 schema admission,
`:189`–197의 counter 기반 budget, `:521`의 `object_usage` trigger.
Binding: 지원 schema의 fail-closed 복구와 저장 resource accounting 불변식.

최소 조건은 local DB의 user_version/profile/table inventory/현재 usage가 맞지만
`object_usage` trigger가 빠진 상태다. synthetic DB를 만든 뒤 닫고, 별도 SQLite
connection에서 `DROP TRIGGER object_usage` 후 다시 연다. 이 schema 변형은
`integrity_check=ok`, FK 오류 0이며 open이 수락한다.

`ClientStoreLimits(objectCount:1)`로 서로 다른 정상 object 2개를 저장하면 둘 다
COMMIT되고 API는 성공한다. Fresh SQLite의 실제 관측은 **objects=2,
payload=6,591 bytes**, `usage.objects=0`, `usage.payload=0`이다. 다음 reopen은
그제야 `STORE_METADATA_CORRUPT`로 거부한다. `findings.json`에 이 상태와 결과를
보존했다. 단순 예외 injection이나 API 결과만으로 판정하지 않았다.

기대값은 필요한 schema 구조가 없으면 쓰기 **전에** 거부하는 것이다. 현재 방식은
반복 insert에서 count/payload quota를 우회하고, 성공 반환 뒤 재시작이 차단되는
영속성·가용성 결함이다. 전제는 malformed local schema이며 정상 앱 경로가 trigger를
삭제하거나 원격 공격자가 DB를 변경할 수 있다고 주장하지 않는다. Physical page
limit은 남아 있으므로 무한 저장이나 금융 행 손실로 분류하지 않았다.

최소 수정은 open의 locked schema admission에서 counter·immutability·FK에 필요한
trigger와 constraints의 실제 정의를 검증하고 누락/변조를 거부하는 것이다. 현재
counter equality만으로 앞으로의 write accounting을 보증해서는 안 된다. 자동 수리로
증거를 덮지 말고 누락 및 no-op으로 변조된 required trigger, quota 초과 rollback,
재시작 뒤 prior good object 보존을 회귀로 추가해야 한다.

## T. 한계와 미검증 가정

환경은 Linux x86_64, Flutter 3.47.4, Dart 3.13.3, Python 3.12.3다. Dart 실행에서
SQLite **3.53.4**, Python fresh-read/backend 환경에서 SQLite **3.45.1**을 확인했다.
호스트 process-crash와 Android debug compile의 증거이며 실기기 VFS/flush,
OS crash, power loss, hardware I/O failure 전체의 증거는 아니다. 이 rollout proof는
T6.6C §26/§38의 후속 gate로 유지한다.

작은 benchmark는 29개 object/177,465 payload bytes의 store에서 control object를
200회 read, 100회 duplicate put했다. 관측 평균은 **get 1,875.37 µs**,
**duplicate put 2,996.30 µs**, open **71,987 µs**다. Linux Dart JIT와 다른 회귀
process가 있는 단일 실행이며 cold/warm 전체 scaling 결과가 아니다. RSS 272,973,824,
max RSS 311,160,832 bytes는 Dart process 전체이고 object allocation만의 값이 아니다.

정상 put/get에는 full object/financial history scan이 추가되지 않았다. open의 usage
recovery와 explicit health scrub은 O(N)이다. E2가 매 object마다 reopen해서는 안 된다.
Staging progress의 COUNT와 explicit cleanup은 metadata 크기에 영향을 받으므로 후속
scheduler의 비용 측정 대상이다. 이 한계를 새 correctness finding으로 부풀리지 않았다.

## U. E2 준비 판정

**SAFE TO START T6.6E2: NO.** E1-A01과 E1-A02를 최소 범위로 수정한 뒤 이 독립
반례와 기존 회귀를 재검증해야 한다. E2/E3의 auth/closure/publication 유보 자체는
타당하며 이번 감사에서 그 기능을 구현하거나 protocol을 변경하지 않았다.

## V. Production 및 배포 안전

Production DB/API/서비스/credential/사용자 데이터 접근은 **NONE**이다. 모든 추가
DB·계정·금융 행은 새 disposable synthetic 자료다. ASGI는 TestClient 내부에서만
실행했다. 배포, restart, APK 설치, segmented sync/endpoint 활성화는 수행하지 않았다.
정상 앱의 금융 계산, OfflineBaseline v4, frozen B/J, Snapshot v7 및 backend runtime은
변경하지 않았다. **SAFE TO DEPLOY: NO.**

## W. 감사 전용 commit과 push 증거

추가 대상은 이 보고서와 `docs/benchmarks/t66e1-audit/`의 독립 코드·fixture·측정
자료뿐이다. 구현 source와 기존 테스트/보고서는 수정하지 않는다. 감사 commit은
자기 참조 hash를 본문에 넣는 대신 아래 명령과 최종 응답의 실제 hash로 식별한다.
Commit/push는 배포 허가가 아니다.

```sh
git log -1 --format='%H %s' -- docs/t66/e/audits/t66e1-independent-audit.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --porcelain
```

```text
T6.6E1 INDEPENDENT AUDIT:
FAIL

AUDITED IMPLEMENTATION COMMIT:
141e01186d589a9071ae6a3d0c0023a6472c014d

AUDIT COMMIT:
이 보고서를 최초 추가한 commit; 위 git log와 최종 응답으로 확인

REPOSITORY STATE:
VERIFIED

IMPLEMENTATION DIFF REVIEW:
COMPLETE

SERVER PROTOCOL CONTRACT:
FAIL

INDEPENDENT C1 GOLDEN VECTORS:
PASS

INDEPENDENT HASH VERIFICATION:
PASS

IMMUTABLE OBJECT IDENTITY:
PASS

SQLITE TRANSACTION SAFETY:
FAIL

PERSISTENT RESTART RECOVERY:
FAIL

REAL PROCESS CRASH COVERAGE:
11 BOUNDARIES VERIFIED

CONCURRENT WRITE SAFETY:
PASS

STAGING METADATA SAFETY:
PASS

CORRUPTION DETECTION:
FAIL

RESOURCE BOUNDS:
FAIL

OBJECT INTEGRITY VS MEMBERSHIP:
SEPARATED

OBSERVATION AUTHORIZATION:
CORRECTLY DEFERRED

ACTIVE GENERATION:
NOT IMPLEMENTED

OFFLINE BASELINE V4:
UNCHANGED

FROZEN OFFLINE B/J:
UNCHANGED

SNAPSHOT V7:
UNCHANGED

NORMAL FLUTTER STARTUP:
UNCHANGED

NORMAL FLUTTER READ/WRITE:
UNCHANGED

BACKEND RUNTIME:
UNCHANGED

INDEPENDENT AUDIT CASES:
67 PASS
6 FAIL
0 INCONCLUSIVE

E1 FLUTTER TESTS:
96 PASS
0 FAIL

FULL FLUTTER TESTS:
635 PASS
0 FAIL
2 SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

BACKEND REGRESSION:
1315 TESTS
1540 SUBTESTS
PASS

RUFF:
PASS

COMPILEALL:
PASS

GIT DIFF CHECK:
PASS

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
2

NEW LOW:
0

UNRESOLVED BLOCKERS:
2 — E1-A01, E1-A02

SAFE TO START T6.6E2:
NO

SAFE TO DEPLOY:
NO

FINAL VERDICT:
FAIL — T6.6E1 CORRECTION REQUIRED

NEXT ACTION:
금액 문자열 admission과 필수 SQLite schema 검증을 수정한 뒤 독립 반례를 재검증한다.
```
