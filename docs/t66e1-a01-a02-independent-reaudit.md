# T6.6E1 E1-A01/A02 독립 targeted 재감사

## 1. 대상 commit과 감사 기준

교정 구현은 `98f0bfaeb5b454796eb9dc40290ae1e340ce80ca`, 교정 전 감사는
`133391242b44573cfe3c1efb9950fa526be0b7f8`, 원래 E1 구현은
`141e01186d589a9071ae6a3d0c0023a6472c014d`다. 감사일은 2026-10-12다.

**PASS — T6.6E1-A01/A02 INDEPENDENT TARGETED RE-AUDIT COMPLETE**

E1-A01과 E1-A02는 모두 CLOSED다. 원래 실패 6건을 포함한 73개 독립 사례, 새 38개
사례와 4,755개 금액 차분, 필수 전체 회귀가 통과했다. 추가로 허용되지 않은 committed
객체는 0개이고 미해결 correctness blocker는 없다. **E2 구현을 시작할 수 있다.**

구현 측 PASS 주장을 이번 감사의 결과로 전용하지 않았다. 실제 교정 diff 검토,
변경하지 않은 원래 반례 재실행, 추가 독립 corpus, 별도 SQLite 연결의 committed-state
검사를 함께 사용했다. 구현 파일은 수정하지 않았다.

## 2. Repository와 remote 검증

시작 branch는 `main`이며, `HEAD = main = origin/main = 실제 remote main`이 모두
대상 교정 hash와 일치했다. 시작 working tree는 clean이었다. `git ls-remote`는
로컬 tracking ref와 별도로 실제 remote를 확인했다.

```sh
git status --porcelain=v1
git rev-parse --abbrev-ref HEAD
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git diff --stat 1333912..98f0bfa
git diff --name-status 1333912..98f0bfa
```

`AGENTS.md`, project-state/domain-model/known-issues, architecture의 서버 authority와
클라이언트 신뢰 경계, offline-mode, T6.6C binding protocol, 구현 보고서의 X 교정
addendum 및 원래 독립 감사 보고서를 읽었다. 원래 FAIL 보고서와 반례 결과는
역사적 증거로 보존했다. 감사 종료 Git 검증 방법과 commit은 24절에 기록한다.

## 3. 교정 diff inventory

완전한 `1333912..98f0bfa` diff는 **10 files, +695/-1**이다.

| 파일 | 변경과 감사 결론 |
|---|---|
| `mobile/lib/src/segmented/object.dart` | 검증용 Python whitespace 집합 추가 및 `.trim()` 1곳 교체 |
| `mobile/lib/src/segmented/store.dart` | open/write/health에 정확한 schema 정의 검사 추가 |
| `mobile/test/segmented_money_correction_test.dart` | 166개 금액 회귀 |
| `mobile/test/segmented_schema_correction_test.dart` | 45개 schema 회귀 |
| `mobile/test/segmented_store_test.dart` | 기존 corruption fixture에서 immutable trigger 원래 정의 복원; assertion 유지 |
| `mobile/test/fixtures/segmented_money_vectors.json` | 서버에서 유도한 165개 금액 vector |
| `scripts/benchmarks/t66e1_money_vectors.py` | 실제 backend validator를 사용하는 vector 생성 |
| `scripts/benchmarks/test_t66e1_money_vectors.py` | 재생성 일치 확인 |
| `docs/benchmarks/t66e1-correction/summary.json` | 구현 측 결과와 제한된 측정 |
| `docs/t66e1-implementation.md` | 교정 원인·정책·증거 addendum |

Dependency/lockfile, backend 구현, 금융 공식, 기존 app startup/DI, UI, production
schema, Snapshot/Offline 저장 구현 변경은 없다. supporting change는 두 finding에
한정된다. 기존 corruption test의 준비 단계 변경은 schema 손상과 payload 손상을
분리하며, 검출 assertion을 완화하지 않았다.

## 4. 원래 findings

원래 감사는 73개 중 **67 PASS, 6 FAIL**, MEDIUM 2건이었다.

- **E1-A01:** Python `str.strip()`과 Dart `trim()`의 차이로 U+001C~001F를 포함한
  정상 monetary string을 거부하고, 서버가 거부한 U+FEFF를 수락했다.
- **E1-A02:** `object_usage`가 없는데 open을 수락해 한도 1에서 서로 다른 객체
  2개/6,591 bytes를 COMMIT했다. usage는 0이었고 다음 reopen에서야 오류가 났다.

원래 재현은 `docs/benchmarks/t66e1-audit/reproduce_findings.py`, 원래 assertion은
같은 디렉터리의 `test_audit.py`다. 이번 감사에서는 이 파일과 과거 `findings.json`을
변경하지 않았다.

## 5. E1-A01 독립 검증

서버 authority는 `backend/isolated_sync/raw.py:80`의 `setting_money`다. 문자열의
앞·뒤 Python whitespace를 검증용으로 제거한 뒤 `[+-]?[0-9]+(?:\.0+)?` 전체 문법을
검사한다. Decimal finite/integral 및 절댓값 `≤9007199254740991`도 필요하다.

| 입력 특성 | 실제 서버 계약과 교정된 Dart 관측 |
|---|---|
| 부호 | 없음, ASCII `+` 또는 `-` 하나 허용 |
| 정수부 | ASCII digit 1개 이상; leading zero와 signed zero 허용 |
| 소수부 | 생략 또는 `.` 뒤 `0` 1개 이상; `1.`, `.0`, `1.01` 거부 |
| 경계 whitespace | 아래 29개를 앞·뒤에서만 무시; 원문은 보존 |
| 내부 whitespace | 거부 |
| BOM/zero-width/format | U+FEFF, U+200B, U+2060, U+180E 등 거부 |
| 빈 값 | empty/whitespace-only 거부 |
| 숫자처럼 보이는 다른 문법 | exponent/underscore/comma/NaN/Infinity/비ASCII digit 거부 |
| 범위 | 양·음 모두 2^53−1까지; 그 다음 값 거부 |

현재 backend Python의 전체 Unicode 공간을 열거한 `isspace()` 집합은 정확히
29개다: `0009–000D`, `001C–0020`, `0085`, `00A0`, `1680`, `2000–200A`,
`2028`, `2029`, `202F`, `205F`, `3000`.

`mobile/lib/src/segmented/object.dart:36`의 집합과 정확히 맞는다. 이들은 모두 BMP라
code-unit 경계 검사가 codepoint 검사를 빠뜨리지 않는다. `:261`의 문법은 ASCII
숫자와 zero fraction으로 제한되므로, 허용 문법에서 BigInt 정수부의 범위 검사는
서버 Decimal의 finite/integral/range와 같은 판정을 낸다. 미지의 non-BMP 문자는
whitespace로 제거되지 않고 숫자 문법에서도 거부된다.

## 6. Backend/Dart 독립 differential corpus

새 `make_corpus.py`는 교정된 Dart validator를 기대값 생성에 사용하지 않는다.
실제 backend `setting_money`로 승인 여부를 판정하고, 승인된 row는 서버의
`Row.make/leaf`로 생성한다. Python JSON 및 hashlib가 C1 bytes와 domain hash를
별도로 검증한다.

**4,755건 모두 일치: 3,816 승인, 939 거부, mismatch 0.** 구현 측 보고 vector
165개를 포함하되 backend에서 다시 판정했다. 추가 4,590건은 다음으로 구성된다.

- 29×29 앞·뒤 whitespace 조합 × 4개 금액 형태.
- whitespace 주변 및 BOM/format/NUL/non-BMP를 포함한 57개 경계 codepoint의 위치 변화.
- 29종 whitespace와 4개 invalid character의 조합, 금액 문법·범위 변형.
- 5,000자리 정수/zero prefix/소수부, 고정 seed `66010102`의 256개 혼합 사례.
- 5개 monetary setting key를 순회하고, 주변 synthetic record에 한글·emoji·combining
  Unicode 문자열을 포함한다.

전체 corpus SHA-256:
`59bd99165076a10104dbb4c80f3c77a9082b0f5eaa75ba933be637b7d2a584d6`.
재생성 코드와 축약 증거를 보존하고 전체 corpus는 `/tmp`에 생성한다. 유한 corpus만으로
모든 가능한 문자열의 언어 동등성을 증명했다고 주장하지 않는다. 5절의 문자 집합과
단순 문법 분석이 시험 결과를 보완한다. 향후 backend Unicode/문법 변경은 다시
호환 검증해야 한다.

## 7. Raw monetary string 보존

승인된 입력을 trim/normalize/float 변환해서 저장하지 않는다. 3,816건의 승인 입력은
3,815개의 유일 객체로 저장됐다. 동일 identity 1건은 정상 deduplication이다.
별도 Python SQLite 연결로 모든 BLOB와 JSON의 원문 string, 실제 객체 집합 및 usage를
확인했다. Fresh process의 open/health도 통과했다.

U+001C~001F, sign/leading zeros/zero fraction 및 한글·조합형 Unicode가 원문 그대로
남았다. 검증용 substring은 숫자 판정에만 사용되고 row/body/C1 bytes를 교체하지 않는다.
Backend 금융 projection이나 기존 Flutter 계산 경로는 변경하지 않았다.

## 8. C1과 hash 호환

교정은 `c1.dart`, hash domain, codec 또는 서버 canonicalization을 변경하지 않았다.
새 승인 객체마다 원래 서버 bytes, Dart 반환 bytes, 실제 SQLite BLOB가 일치하며
Python hashlib SHA-256도 일치했다. 음성 vector는 hash-valid representation으로
구성했으나 승인된 서버 응답이라고 주장하지 않는다.

원래 독립 suite의 **128 C1 golden vectors**, 9종 server immutable objects,
Unicode non-normalization 및 malformed canonical input 사례도 그대로 통과했다.
원래 ASGI 재현은 실제 D2b bootstrap와 인증된 D3b manifest/object transfer를 거쳐
U+001C~001F 각각 **HTTP 201/200 → E1 저장 성공**을 확인했다.

## 9. E1-A02 독립 검증

주요 source는 `mobile/lib/src/segmented/store.dart:126`, `:183`, `:511`이다.
Open은 trusted 초기화 후 같은 write transaction에서 schema를 검사한다. 모든
일반 persistent mutation은 `_transaction`을 통과하며, `BEGIN IMMEDIATE` 직후
schema를 검사하고 body와 usage 한도 검사를 마친 뒤 COMMIT한다.

새 SQLite 시험은 장기 실행 Dart handle과 **별도 Python SQLite connection**을 사용했다.
SQLite native runtime은 Dart **3.53.4**, Python **3.45.1**이다. 단순 method return이나
예외만 검사하지 않고 8개 table의 실제 committed rows와 BLOB를 비교했다.

## 10. Trigger 정의 검증

이 schema는 **8 tables + 1 index + 11 triggers = 20 definitions**다. 사용자 정의
DDL의 정확한 SQL과 name을 trusted `_schema`에서 만든 정의와 비교한다. 자동 index의
`sql IS NULL` 항목은 catalog 비교 대상이 아니다. 추가 반환을 검출하도록 LIMIT은 21이다.

| 필수 trigger | 보존하는 불변식 |
|---|---|
| `object_usage` | object count, payload bytes, object metadata charge |
| `refs_usage`, `refs_release` | Ref 추가/삭제 metadata charge |
| `edge_usage` | immutable edge 추가 metadata charge |
| `staging_usage`, `staging_release` | stage count와 manifest/고정 metadata charge |
| `root_usage`, `root_release` | stage root metadata charge |
| `progress_usage`, `progress_release` | stage progress metadata charge |
| `immutable_body` | object row UPDATE 거부 |

이들은 quota를 직접 RAISE하는 trigger가 아니라 accounting 또는 immutability를
보장한다. 실제 quota 비교는 같은 transaction의 `:193`에서 수행한다.

기존 45개 correction test는 11종 각각의 open 전 누락/open 후 누락/no-op,
weakened increment, 다른 WHEN, 다른 event/target table, mutator 재사용 등을 검증한다.
모두 이번 full Flutter 실행에 포함해 통과했다. 추가 독립 11건은 모든 trigger의
조건을 `WHEN 0`으로 바꾸고 duplicate와 cleanup 모두의 거부를 확인했다.

정확한 schema identity는 구현 보고서 X.5와 `:500`에 명시된 계약이다. 동등하지만
재작성된 SQL formatting, 추가 view/index, 누락 index, 변경 table도 보수적으로 거부한다.
Semantic normalization을 보장한다고 주장하지 않으므로 이 거부는 결함이 아니다.
정상 원래 schema는 수락한다. Schema를 자동 복구하지 않는다.

## 11. Transaction 및 COMMIT 경계

실제 순서는 다음과 같다.

```text
동일 _db: BEGIN IMMEDIATE
  → PRAGMA user_version 및 sqlite_master 정의 검사
  → insert / staging / cleanup, trigger 실행
  → usage의 object/payload/staging/metadata 한도 검사
  → COMMIT
실패 시 finally ROLLBACK
```

SQLite의 실제 write ownership이 schema 검증 전에 획득된다. 다른 연결의 DDL도
write이므로 이 transaction이 끝나기 전에 schema를 변경해 COMMIT할 수 없다.
8개 barrier interleaving에서 이를 실제로 검증했다: object insert 전/후, edges 후,
object COMMIT 직전, duplicate COMMIT 직전, stage/progress insert 후, cleanup COMMIT
직전 모두 외부 `DROP TRIGGER`가 **SQLITE_BUSY(5)**였다. 보호된 COMMIT 뒤에는 DDL이
정상 실행됐고, 다음 write는 재검증하여 `STORE_SCHEMA_CORRUPT`로 거부했다.

반대로 DDL writer가 먼저 BEGIN하면 E1 write는 `STORE_BUSY`다. DDL rollback 후에는
정상 retry, DDL COMMIT 후에는 schema 거부가 관측됐다. SHARED reader가 E1 COMMIT을
막는 경우에는 object/Ref/edges/usage 전체가 rollback됐고 reader 종료 후 retry가
정상 COMMIT됐다. 따라서 검증 실패나 COMMIT busy 뒤 부분 성공은 없었다.

Schema 검증과 write는 별도 connection이나 별도 transaction이 아니다. 성공 여부를
영구 cache하지 않는다. 실제 sqlite3 driver 3.7.0의 `database.dart:493`은 select마다
prepare하고 finally statement를 close한다. 반복 성공 후 schema 변경에서도 검사
생략이 없었다. 이 결론은 지원 SQLite API의 locking 모델에 관한 것이다.
`writable_schema`, raw file overwrite, SQLite engine 내부 침해까지 방어했다고 주장하지 않는다.

## 12. 모든 영속 write 경로

| 경로 | 위치 | 보호와 관측 |
|---|---|---|
| open/초기화 | `store.dart:112` | write lock 안 trusted schema 생성 후 정의/metadata 검사 |
| new/duplicate object | `:232` | 둘 다 `_transaction`; duplicate도 schema 재검증 |
| conflicting object | `:232`, `:239` | hash/bytes 또는 기존 body conflict 거부; 허용 COMMIT 없음 |
| Ref/edge 쓰기 | `:223`, `:245` | object 또는 stage transaction 내부에서만 호출 |
| staging 생성/기존 stage 재사용 | `:327` | `_transaction` 안 manifest/roots 원자성 |
| progress 생성/중복 재사용 | `:361` | `_transaction`, stage/object 존재와 검증 필요 |
| staging 및 orphan Ref cleanup | `:434` | `_transaction`; cascade/release accounting 보호 |
| recovery | `:82`, `:444` | open 검증; health는 read-only scrub, 자동 schema repair 없음 |

E1은 object sweep/GC나 active-generation publication을 제공하지 않는다. Read/list는
persistent mutation이 없으므로 write schema gate가 필요하지 않다. 유효한 기존
object를 read할 때에도 payload/hash/context/edges를 다시 검사한다. 전체 table
snapshot으로 검사한 5개 mutator에서 누락 schema 이후 추가 변경은 0이었다.

## 13. 원래 object-limit 반례

원래 독립 재현 코드는 그대로 실행했다. 출력 목적지만 새 임시 경로로 돌렸고, 과거
`findings.json`의 SHA-256 불변을 확인했다.

| 상태 | 교정 전 역사적 관측 | 이번 독립 관측 |
|---|---|---|
| trigger 없는 빈 store reopen/두 insert | 성공 후 objects 2, usage 0 | open `STORE_SCHEMA_CORRUPT`, 실제 objects 0 |
| 한도 1에서 첫 valid insert 후 외부 trigger 제거 | 추가 검사 필요했던 경계 | 둘째 insert 거부, actual objects **1→1**, 추가 COMMIT **0** |
| 손상 후 health | 뒤늦은 counter 검출 | `healthy=false`, schema 오류 명시 |
| 손상 후 reopen | 불일치 metadata 오류 | write 전 schema 오류, 원래 committed BLOB 보존 |

**UNAUTHORIZED ADDITIONAL COMMITTED OBJECTS = 0.** Audit fixture에서 원래 DDL을
수동 복원한 positive control은 duplicate를 허용하고 quota 초과 둘째 insert를
`LOCAL_STORAGE_BUDGET`으로 rollback했다. 이것은 제품의 자동 repair 기능이 아니다.

## 14. 독립 SQLite committed-state 증거

새 suite는 다른 connection의 직접 SQL로 다음을 확인했다.

- 전체 `objects.hash/kind/body` 집합과 독립 hashlib identity.
- 실제 count/payload 합과 usage 일치, 8-table snapshot 보존.
- `integrity_check=ok`, foreign-key 오류 0, 새 BEGIN IMMEDIATE 가능.
- 기존 object, staging manifest, roots 및 progress의 실패 전후 보존.
- 실제 schema 정의의 변화, COMMIT/ROLLBACK 결과와 다음 write의 재검증.

증거는 [cases.json](benchmarks/t66e1-a01-a02-reaudit/cases.json),
[original-replay.json](benchmarks/t66e1-a01-a02-reaudit/original-replay.json),
[results.json](benchmarks/t66e1-a01-a02-reaudit/results.json)에 있다. 예외가 났다는
이유만으로 안전하다고 판정하지 않았다. Temporary DB 경로는 해당 실행의 disposable
fixture이며 지속적인 보존 또는 production 데이터 경로가 아니다.

## 15. Recovery 및 실제 process crash

이번 full Flutter에서 기존 **7개 실제 SIGKILL 경계**가 통과했다: object insert 전/후,
edges 후, COMMIT 전/후, staging insert 후/COMMIT 후. 원래 독립 suite의 **8개 SIGKILL
interleaving**도 변경 없이 통과했다. 중복을 제거하면 object 5개, stage 2개,
progress 2개, cleanup 2개의 **11개 operation/boundary**다.

Fresh process와 독립 SQLite에서 COMMIT 전 변경의 rollback, COMMIT 후 데이터 지속,
기존 valid object·staging/usage/FK의 일치 및 후속 write를 확인했다. Unsupported schema,
invalid staging/checksum, payload corruption, SQLITE_FULL 및 busy도 원래 suite와 기존
E1 tests에서 통과했다. 새 payload corruption test는 trigger를 exact 원래 정의로
복원한 뒤 bytes 손상을 읽어 schema 오류와 구분한 무결성 거부를 확인했다.

교정이 추가한 것은 기존 write transaction 안의 read-only 검증이며, 새로운 payload
publication이나 별도 COMMIT이 없다. 따라서 별도의 새로운 crash boundary는 만들지
않았다. 자동 schema repair는 요구하지 않으며, 손상된 schema의 open/write 거부와
이미 committed된 정상 데이터 보존이 관측됐다. OS crash나 hardware power-loss
내구성을 SIGKILL 시험에서 증명했다고 주장하지 않는다.

## 16. 성능과 resource 영향

구현 summary의 80개 순차 JIT 표본은 참고 자료다. get source가 같은데도 latency가
크게 달라지므로 그 수치로 교정에 의한 성능 향상을 단정할 수 없다.

독립 bounded 측정은 현재 host, Dart 3.13.3 JIT, native SQLite 3.53.4,
DELETE journal/EXTRA sync, disposable store에서 수행했다. Duplicate warmup 20회 후
실제 E1 write를 200회씩, 비교 transaction을 번갈아 200회씩 측정했다.

| cell | n | median µs | p95 µs |
|---|---:|---:|---:|
| intact-store 새 object insertion | 200 | 4,450 | 15,344 |
| duplicate insertion | 200 | 934 | 1,633 |
| BEGIN IMMEDIATE/ROLLBACK | 200 | 18 | 29 |
| 같은 transaction + schema 2 queries/20 definitions 비교 | 200 | 96 | 179 |

마지막 cell은 같은 SQL/정의 비교의 독립 분리 측정이며 private helper의 직접 profiling은
아니다. 두 transaction median 차이는 약 78µs다. JIT, filesystem sync, 병행 backend
회귀 noise를 포함하므로 고정 overhead 상한이나 실기기 결과로 해석하지 않는다.
측정 원자료는 [performance.json](benchmarks/t66e1-a01-a02-reaudit/performance.json)에 있다.

새 schema 검사는 user_version 1 query와 catalog 1 query이며, 지원 schema의 20개
정의만 비교한다. 객체·금융 행·과거 generation의 전체 scan을 추가하지 않는다.
`_schemaDefinitions`는 trusted DDL에서 한 번 만든 fixed map이다. 기존 open/명시 health의
O(N) scrub은 유지되며 normal put/get에 새 full-dataset scan은 없다. 새로운 subprocess,
파일 또는 SQLite connection을 write마다 만들지 않는다. 임의 성능 threshold를
발명하지 않았고 correctness blocker는 발견하지 않았다.

## 17. 원래 실패 6건

원래 test assertion을 약화하거나 대신 작성하지 않고 73개 suite에서 모두 실행했다.

| 원래 test와 입력 | 원래 실패 | 교정된 관측 | 독립 오라클 | 결과 |
|---|---|---|---|---|
| `test_every_server_admitted_money_string_is_accepted[setting-3]`, `"\u001c+0001\u001c"` | client 거부 | 승인, exact bytes 유지 | 기존 server leaf/hash | PASS |
| 같은 test `[setting-4]`, `"\u001d-0001\u001d"` | client 거부 | 승인, exact bytes 유지 | 기존 server leaf/hash | PASS |
| 같은 test `[setting-5]`, `"\u001e0.00\u001e"` | client 거부 | 승인, exact bytes 유지 | 기존 server leaf/hash | PASS |
| 같은 test `[setting-6]`, `"\u001f1000\u001f"` | client 거부 | 승인, exact bytes 유지 | 기존 server leaf/hash | PASS |
| `test_server_rejected_bom_money_is_rejected`, `"\ufeff1000\ufeff"` | client 승인 | `MONEY_STRING_INVALID` | 실제 backend `REJECT_SETTING_MONEY` | PASS |
| `test_missing_schema_trigger_is_rejected_before_writes` | 한도 1에서 objects 2 COMMIT | schema 거부, objects 0 | fresh SQLite committed rows | PASS |

네 server-admitted 원래 fixture hash는 순서대로 `e76f8182…`, `a85858b5…`,
`62a02dac…`, `79786fda…`이며 원래 `server-fixture.json`의 exact reference/bytes와
일치한다. 새 ASGI replay는 별도의 synthetic DB에서 원래 `+0001000.00` 입력을
검증했다. 임의로 원래 6개를 더 쉬운 대체 사례로 바꾸지 않았다.

## 18. 원래 독립 감사 suite

`.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py`를 실제 실행했다.
**73 PASS, 0 FAIL, 0 SKIP**, 326.801초다. 원래의 67개 정상 사례도 그대로 통과했다.
Canonical vectors, hash, namespace, malformed object/manifest, durable put/reopen,
concurrent writers, corruption, staging, SIGKILL, disk-full/busy 및 격리 검증이 포함된다.

새 suite는 **38 PASS, 0 FAIL, 0 SKIP**, 126.984초다. 4,755개 문자열은 이 중 1개
differential test에 포함된 vector 수이므로 pytest case 수에 다시 더하지 않았다.
자세한 38개 시나리오/기대값/실제값/오라클은 새 artifact README와 `cases.json`에 있다.

## 19. 전체 회귀

아래는 구현 보고서의 수치를 인용한 것이 아니라 이번 실행의 실제 결과다.

| 검사 | 결과 |
|---|---|
| 기존 E1 | 96 PASS: protocol 58, store 31, crash 7 |
| 교정 Flutter tests | 211 PASS: monetary 166, schema 45 |
| Flutter 전체 | **846 PASS, 0 FAIL, 기존 2 SKIP** |
| 원래 독립 감사 | 73 PASS, 0 FAIL |
| 새 독립 targeted 감사 | 38 PASS, 0 FAIL; 4,755 differential vectors 별도 |
| Flutter analyze | PASS, no issues |
| 교정 관련 Dart formatting | PASS, 11 files, 0 changed |
| 새 감사 Dart analyze/format | PASS, mobile package 설정으로 분석 |
| Android debug APK build | PASS, compile만 수행 |
| backend 전체 | **1,315 PASS + 1,540 subtests PASS**, 0 FAIL, 1 warning, 1,628.90초 |
| safety/diagnostic | 60 PASS, 0 FAIL |
| Ruff | PASS |
| compileall | PASS |
| frontend `npm run build` | PASS |
| `git diff --check` | PASS |

Flutter machine 결과의 hidden loader 37개는 tests로 계수하지 않았다. SKIP 2개는
기존 `T6.6A frozen bytes admission and actual durable HOST pipeline` 및
`T6.6A actual IOClient content encoding and byte-exact admission`이다.
E1/C1/SQLite correction tests는 SKIP하지 않았다.

Full Flutter는 OfflineBaseline v4, frozen B/J, 정상 AppState/읽기·쓰기 및 Snapshot
회귀를 포함한다. Full backend는 D1/D2a/D2b/D3a/D3b/D3c, schema, authoritative
state 및 Snapshot v7 회귀를 포함한다. 실제 실행 명령은 새 artifact README에 보존했다.
Backend JUnit의 `tests=2855`는 정규 tests 1,315와 subtests 1,540의 합이다.
Subtests를 정규 tests로 중복 계수하지 않았다. Android toolchain/Starlette의 기존
deprecation 경고는 통과와 구분한다.

## 20. Findings와 심각도

**신규 CRITICAL 0 / HIGH 0 / MEDIUM 0 / LOW 0.**

원래 E1-A01은 서버/Dart의 실제 금액 admission 및 원문 저장 증거로 **CLOSED**다.
원래 E1-A02는 정확한 schema 정의, 동일 transaction의 validation-to-COMMIT 보호,
실제 committed rows 및 모든 mutator 검증으로 **CLOSED**다.

새 correction blocker 또는 assertions를 완화해야만 통과하는 사례는 발견하지 않았다.
의도적으로 E2/E3에 유보된 auth/network/graph-closure/publication은 E1 결함으로
분류하지 않았다. 금융 projection 독립 재계산을 새로운 mobile 의무로 추가하지 않았다.

## 21. 남은 한계

- 차분 corpus는 유한하다. 현재 backend Python의 whitespace/문법에 대한 source 분석과
  함께 해석하며, 미래 Unicode 또는 protocol 변경의 자동 호환성을 보증하지 않는다.
- SQLite 시험은 Linux host의 실제 native engine에서 수행했다. APK compile은 통과했지만
  Android 실기기 설치·시험이나 OS/power-loss 시험은 하지 않았다.
- 임의 raw file/`writable_schema`/SQLite engine 침해는 이 schema locking 증명의 범위 밖이다.
  정상 SQLite DDL과 다중 연결의 interleaving은 실제로 시험했다.
- Exact schema identity는 다른 formatting과 추가 객체를 거부한다. 손상 schema의 자동
  repair를 제공하지 않으며 fail-closed로 데이터를 보존한다.
- Integrity 검증은 membership, authenticated observation, complete generation 또는 활성
  앱 데이터의 증명이 아니다. E2/E3의 독립 graph/auth/publication gate가 계속 필요하다.
- 벤치마크는 제한된 host 측정이다. 모바일 latency/장기 workload/scaling 상한을 주장하지 않는다.

위 한계에서 이번 두 finding의 미해결 correctness blocker는 확인되지 않았다.

## 22. E2 readiness

**SAFE TO START T6.6E2: YES.** 두 MEDIUM finding이 해소됐고 필수 회귀도 통과했다. Source에서
`StagingSession.validationState`는 항상 `staged`이며 accepted/active pointer는 없다.
객체 무결성과 generation membership을 혼동하거나 observation authorization을
미리 수락하는 새 API/flag는 추가되지 않았다.

E2의 실제 HTTP 취득과 E3의 generation activation은 이번 감사에서 구현하지 않았다.
재감사 PASS는 이후 구현을 시작할 수 있다는 뜻이며 rollout 또는 배포 승인이 아니다.

## 23. Production 격리

모든 추가 destructive/schema/insert 시험은 새 disposable SQLite와 pytest temporary
storage만 사용했다. 원래 ASGI replay도 in-process synthetic backend만 사용한다.
Production DB/API/credential/service/사용자 금융 자료에는 접근하지 않았다.

`mobile/lib`에서 `SegmentedClientStore`의 참조는 격리된 구현 자체뿐이다. Normal
startup/DI/financial read-write/online sync/UI가 이를 import하거나 구성하지 않는다.
교정 diff는 backend source를 바꾸지 않는다. Production `user_version 4`, Snapshot v7,
OfflineBaseline v4, frozen B/J 및 Android v2.4.0(15)은 변경하지 않았다.
Segmented sync/endpoint/normal-runtime GC를 활성화하지 않았다. APK는 빌드만 했고
설치하지 않았다. Deploy/restart/migration을 실행하지 않았다.

## 24. Audit-only commit과 push

감사 변경은 이 보고서와 `docs/benchmarks/t66e1-a01-a02-reaudit/`의 독립 test,
실행법 및 synthetic evidence뿐이다. 교정 구현과 과거 원래 FAIL 보고서/반례는
그대로 보존했다. Audit commit은 이 보고서를 추가한 commit이며 다음 명령으로
재귀적인 self-hash 없이 정확히 식별한다.

```sh
git log -1 --format=%H -- docs/t66e1-a01-a02-independent-reaudit.md
git show --stat --oneline HEAD
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --porcelain=v1
```

최종 commit/push 및 ref/clean 검증은 완료 후 최종 응답에 실제 hash와 함께 기록한다.
Commit/push는 배포 허가가 아니다.

## 필수 최종 footer

```text
T6.6E1 TARGETED INDEPENDENT RE-AUDIT:
PASS

AUDITED CORRECTION COMMIT:
98f0bfaeb5b454796eb9dc40290ae1e340ce80ca

AUDIT COMMIT:
git log -1 --format=%H -- docs/t66e1-a01-a02-independent-reaudit.md

REPOSITORY STATE:
VERIFIED

CORRECTION DIFF REVIEW:
COMPLETE

E1-A01:
CLOSED

E1-A02:
CLOSED

ORIGINAL SIX FAILED CASES:
6 PASS
0 FAIL
0 INCONCLUSIVE

ORIGINAL INDEPENDENT AUDIT SUITE:
73 PASS
0 FAIL

SERVER/DART MONETARY VALIDATION:
PASS

INDEPENDENT DIFFERENTIAL CASES:
4755 PASS
0 FAIL

WHITESPACE COMPATIBILITY:
PASS

BOM REJECTION:
PASS

RAW MONETARY STRING PRESERVATION:
PASS

C1 CANONICAL BYTE COMPATIBILITY:
PASS

INDEPENDENT HASH GOLDEN VECTORS:
PASS

MANDATORY SQLITE TRIGGER INTEGRITY:
PASS

MISSING-TRIGGER WRITE REJECTION:
PASS

WEAKENED-TRIGGER REJECTION:
PASS

ORIGINAL OBJECT-LIMIT REPRODUCTION:
PASS

UNAUTHORIZED ADDITIONAL COMMITTED OBJECTS:
0

VALIDATION-TO-COMMIT SAFETY:
PASS

ALL RELEVANT WRITE PATHS:
COVERED

PREVIOUSLY VALID OBJECT PRESERVATION:
PASS

INTACT-STORE NORMAL WRITES:
PASS

SCHEMA CHECK PERFORMANCE:
MEASURED

PROCESS CRASH REGRESSION:
PASS

IMMUTABLE OBJECT STORE:
PRESERVED

STAGING METADATA:
PRESERVED

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

NORMAL FLUTTER READ/WRITE:
UNCHANGED

BACKEND RUNTIME:
UNCHANGED

NEW INDEPENDENT AUDIT CASES:
38 PASS
0 FAIL
0 INCONCLUSIVE

FULL FLUTTER TESTS:
846 PASS
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
0

NEW LOW:
0

UNRESOLVED BLOCKERS:
0

SAFE TO START T6.6E2:
YES

SAFE TO DEPLOY:
NO

FINAL VERDICT:
PASS — T6.6E1-A01/A02 INDEPENDENT TARGETED RE-AUDIT COMPLETE

NEXT ACTION:
이 감사의 PASS를 기준으로 별도 작업에서 T6.6E2 구현을 시작한다.
```
