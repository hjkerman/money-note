# T6.6F-B03 독립 계측 감사

**FAIL — T6.6F-B03 INSTRUMENTATION CORRECTION REQUIRED**

실제 SQLite와 다른 committed/rollback 수치 및 첫 DML의 조용한 누락을 Python과 Flutter에서
재현했다. backend 계측의 중첩 설치 중복과 거부된 native dispatch의 미회수 hold도 확인했다.
mutation 비교용 oracle SQL이 제품 generation scope에 들어가는 측정 격리 오류도 재현했다.
기존 회귀의 성공으로 이 반례를 면제하지 않는다. 제품 금융 오류로 확대하거나 제품을 수정하지 않았다.
B03은 OPEN이며 Phase B 최종 비용 grid 재개 승인은 NO다. B01/B02는 CLOSED를 유지한다.

증거의 성격은 다음과 같이 구분한다.

- **구현 측 결과**: B03 원 보고서·원 calibration 및 원 로그의 주장이다.
- **독립 감사 결과**: 이번 실행의 literal/native SHA/parser·역사 함수·실제 SQLite oracle와 fresh 회귀다.
- **대조한 역사 증거**: 이전 B01/B02/E1–E4 감사와 원 raw artifact를 현재 source와 대조한 결과다.
- **실험 추정**: 소형·중형 표본에서 산출한 비용 영향이며 100k 실행 결과가 아니다.
- **필수 증거 누락**: 미검증 비용/환경 경계다. 이를 제품 오류나 PASS로 바꾸지 않는다.

## 1. 시작 저장소 식별

개발 경로는 `/home/hjkerman/codex/money-note`, branch는 `main`이다. 최초 HEAD/main/origin/main 및
별도 `git ls-remote origin refs/heads/main`은 모두 `ea2c32ce75a5f6894f52dc1b8fb4e2b1ae6df478`,
작업 트리는 clean이었다. 원격은 `git@github.com:hjkerman/money-note.git`이다.
reset/clean/rebase/기존 파일 덮어쓰기는 수행하지 않았다.
[inventory](benchmarks/t66f-b03-independent/evidence/inventory.json)는 원 추적 2,595개 파일의
Git blob/SHA와 현재 원문을 비교하며 mismatch는 0이다. 관련 없는 시작 수정은 없었다.

AGENTS와 project-state/domain-model/known-issues, architecture의 서버 authority·신뢰 경계,
runbook의 개발·운영 분리, T6.6C 및 지정된 Phase B/B01/B02 보고서를 대조했다.
원 E1/E2의 FAIL과 교정 재감사, E3, E4-P0/A01/RA01의 실패·closure도 보존한다.

## 2. B03 구현 및 receipt commit

구현은 `a96e130682023522ec56ab6e2fc9f53ec8d77df6`, 문서 receipt는
`ea2c32ce75a5f6894f52dc1b8fb4e2b1ae6df478`, 비교 원본은
`da818648031e013e83dd6a680b1b1bde0fb6e0a1`이다. receipt의 변경은 보고서와 JSON receipt 2개뿐이다.
구현 source와 receipt source를 섞지 않았다. receipt의 footer를 독립 완료 증거로 사용하지 않는다.

## 3. 전체 diff 및 제품 파일 검토

실제 diff는 **284 files, +274,926/-35**다. backend 제품 변경은 0이다. 신규 backend test 1개,
제품 Dart 6개, 기존 source guard 1개, 신규 mobile test 6개, test support 4개와 문서·benchmark·raw evidence다.
전체 파일별 SHA·크기·형식 검사는 inventory의 `b03_changed`에 있다. 실행 코드·assertion은 source로,
JSON/gzip/JUnit은 원 자료의 독립 파싱·재집계 및 아래 oracle 대조로 검토했다.

|제품 파일|기존 동작 → 추가 관측|비활성·비동기·예외·할당·소유권 검토|
|---|---|---|
|`diagnostics/logical_cost.dart`|신규 Zone/enum/BigInt collector|기본 Zone 없음, 고정 462 category. 활성 scope/문자열/BigInt 할당. close 뒤 증가는 무시|
|`segmented/c1.dart`|기존 encode/decode/hash/checksum → 실제 span 관측|동기·동일 buffer·동일 SHA/parser. 실패 finally 분류. 호출자 stage 소유|
|`authoritative_bundle_validation.dart`|기존 bundle SHA → legacyHash|기존 UTF8 buffer 참조만 추가. 직렬화/hash 각 1회, 반환·오류 불변|
|`offline/offline_store.dart`|기존 lineage SHA → lineageHash|import 및 함수 한 곳만 변경. 동기·원 canonical/ordering/프레이밍 보존|
|`segmented/store.dart`|원 sqlite3.open → 명시 test factory 선택 가능|null이면 원 연결. 새 설정/await 없음. wrapper는 test support에만 존재|
|`app_state.dart`|원 recover/E2/E3 호출 → stage 부여|원 ticket·guard·await 수 유지. 새 authority state 없음. 동기 commit 유지|

각 파일의 원 동작, 추가 관측, 실제 primitive, 비활성 동작, lock, 새 상태, async/thread 경계,
예외, 할당, counter 소유권, 시험, 부작용 12항목은
[source-review.json](benchmarks/t66f-b03-independent/source-review.json)에 각각 기록했다.
test wrapper의 결함을 이 제품 파일의 금융 알고리즘 결함으로 분류하지 않는다.

## 4. 구속력 있는 계측 요구

규범은 T6.6C §7/12–20/22–26/29/31/34–36 및 §36 I25다. 원 Phase B 최종 감사 §5/6/9와
`t66f-phase-b-final/instrumentation.md`의 operation 단위·실패·중복·소유권 정의를 적용했다.
I25는 정상 steady state의 숨은 full-N fetch/hash/serialize/write를 금지한다.
목표는 `O(H + changed bytes + L log P + 256E)`이며 모든 작업 O(1)을 요구하지 않는다.
초기 취득·restart/fallback·명시 legacy materialization의 허용된 O(N)을 warm 비용으로 숨기지 않는다.
검증을 위해 모바일 금융 엔진이나 새 authorization을 만들지 않는다.

## 5. 독립 counter 정의 및 test-only 경계

|지표|이 감사에서 검증한 정의|별도로 유지하는 것|
|---|---|---|
|HASH_INPUT_BYTES|실제 SHA constructor/update/add에 전달한 입력 길이의 합|domain/NUL 포함, 반복은 반복 계수, cache skip은 0|
|VALIDATION_INPUT_BYTES|명시된 primary UTF8/JSON/C1 admission의 submitted span|완료 span·실패 span·정확한 소비 prefix를 구별|
|LOGICAL_WRITE_BYTES|실제 NEW TEXT UTF8/BLOB payload 및 별도 file write input|bind/selector·숫자 개수·DELETE·physical I/O와 구별|

collector와 DB factory/IO override 선택은 신뢰하는 test code의 명시 호출뿐이다.
원 startup/사용자 action/wire record에 켜는 분기·persistent setting·telemetry 업로드가 없다.
`LogicalCost`는 release에서 호출 불가능한 타입이 아니라 공개 Dart 진단 타입이지만, 현재 제품의
외부 입력이 이를 선택하는 경로는 없다. 비활성 실행에는 collector가 필요 없다.
counter는 검증 성공/실패·ticket·receipt·commit 허가를 결정하지 않는다.

## 6. Hash 입력 독립 보정

독립 Python 4개 literal(빈 입력, `{}`, Unicode, 4,097B)에서 native SHA oracle와 동일했다.
직접 hash와 chunked update를 함께 수행해 `2 × (23 + raw.length)`가 정확히 계수됐다.
원 B03의 framing/copy/reuse/실패 보정도 새로 통과했다. Flutter의 기존 SHA 보정과 독립 역사
lineage golden도 exact다. native hash를 oracle 때문에 다시 수행하는 제품 hook은 없었다.
별도 TLS native witness는 counter에 입력한 길이를 기대값으로 재사용하지 않고 실제 하위 SHA
delegate가 받은 buffer 길이를 관찰한다. 대상은 application SHA256이며 TLS/OS crypto,
PBKDF2 내부 round 등 opaque library 전체를 포함한다고 주장하지 않는다.

## 7. Validation span 독립 보정

독립 6입력 × 반복 2회에서 submitted는 `2 × len(raw)`다. `{ }`와 escaped surrogate는
backend JSON parse가 완료된 후 C1/nested admission에서 실패하므로 JSON completed에 포함된다.
잘린 JSON·invalid UTF8·중복 key는 parse completed가 0이다. Flutter `decodeC1`의 completed는
전체 C1 admission 성공을 뜻하므로 backend JSON completed와 동일 성공 지표로 합치지 않는다.
typed/raw/facts/prefix/graph 방문은 기존 operation counter이며 object 크기를 곱해 bytes로 만들지 않았다.
아래 중첩 설치 반례는 정의가 아니라 구현의 중복 계수 오류다.

## 8. Logical write 독립 보정

실제 SQLite NEW TEXT/BLOB 길이를 별도 SELECT로 대조했다. 한글+emoji key는 UTF8 7B,
신규 BLOB 2B, 무시된 duplicate 시도 7B로 INSERT attempted 9B/effective 2B/committed 2B다.
기존-row UPDATE·receipt·pin INSERT/DELETE 및 고유 이름 nested savepoint는 정상 대조됐다.
실제 E1 put의 body는 별도 reopened connection에서 canonical fixture bytes와 동일하다.
반면 동일 이름 savepoint, `OR FAIL`, 첫 comment-DML은 아래 확정 반례를 만든다.
따라서 write counter 전체 정확성은 **FAIL**이다.

## 9. Attempted/effective/committed 구별

BEFORE는 진입한 row 시도, AFTER는 실제 effective row event다. ignored INSERT는 durable 신규
object가 아니다. UPDATE 지표는 전체 NEW row payload이며 바뀐 column 차분이 아니다.
DELETE는 row count를 남기고 신규 payload bytes는 0이다. SQL bind에는 WHERE/SELECT selector가
들어가며 TEXT bind의 Python 문자 수/Dart code-unit 수를 UTF8 bytes로 보고하지 않는다.
committed는 성공한 native SQL commit에 정산한 논리 payload이며 유일한 최종 row 집합이나
hardware durability가 아니다. file completed/flush/rename은 committed bytes의 증거가 아니다.

## 10. Rollback 및 savepoint

고유 이름 nested rollback·ABORT·명시 rollback·connection close rollback·실제 process kill은
보정한 범위에서 유지됐다. 동일 이름의 중첩 `SAVEPOINT s`에서 SQLite는 가장 최근 `s`를
선택하지만 두 wrapper는 첫 `s`를 선택한다. `a=1B,b=2B` 중 b만 되돌려 a가 남았는데
counter는 committed 0B/rollback 3B다. 실패한 `INSERT OR FAIL`은 앞선 성공 row를 보존하지만
wrapper는 이를 statement rollback으로 정산한다. 두 경우 모두 독립 DB oracle와 불일치다.

## 11. Counter overlap 및 독립 reconciliation

|같은 실행의 구간|독립 expected|관측·판정|
|---|---|---|
|backend 두 SHA 입력|`2 × (23 + raw byte length)`|exact PASS|
|backend 반복 JSON submitted|`2 × raw byte length`|단일 설치 exact PASS|
|고유 savepoint INSERT|attempted 9B/effective 2B/committed 2B|exact PASS|
|동일 이름 savepoint|committed 1B/rollback 2B|0B/3B, FAIL|
|부분 성공 OR FAIL|최종 committed BLOB 3B|1B, FAIL|
|첫 comment INSERT|committed BLOB 2B|0B 및 coverage error 없음, FAIL|

hash/validation/write와 encoding output·HTTP entity는 서로 겹치는 별개 연산 비용이다.
한 unique-byte 총합으로 합치지 않는다. effective/rollback/retry와 cache reuse도 별도 열이다.
동일 run의 cumulative snapshot 차분만 새 작업으로 계산한다.

## 12. Stage 소유권

backend setup/generation/observation/transfer는 ContextVar, Flutter recovery/E2/E3 verify/prepare/
commit/E4 read/legacy는 Zone을 따른다. shared E1 primitive를 E2가 호출하면 e2가 한 번 소유한다.
E3 readback은 e3Commit의 inclusive 구간이며 e3Readback을 다시 합산하지 않는다.
HTTP/E2/E3의 호출자 attribution은 source와 실제 TLS로 보정했다. 그러나 stdin mutation의
전후 독립 catalog SELECT까지 generation에 귀속된다. 각각 176/185행인 두 oracle read는
제품 작업이 아니며 예상 제품 계수는 0이다. 중첩 instrumentation session의 validation 중복도
발생하므로 전체 stage/측정 격리 판정은 FAIL이다.

## 13. Backend 동시 scope

원 thread/async 보정과 독립 started-worker 실험에서 collector가 다른 task/thread로 섞이지 않았다.
동일 bytes가 아닌 두 TLS 요청도 별도 collector/request 번호로 분리됐다. normal server는
이 test-only monkeypatch를 import하지 않는다. process/isolate 자동 전파는 지원한다고 주장하지 않는다.
진행 중 native worker는 원 scope를 유지하지만 dispatch 이전 거부의 hold 누락은 §16 finding이다.

## 14. 실제 HTTP/TLS 격리

독립 Python TLS 실험은 실제 Uvicorn handler에 barrier로 겹친 두 요청을 보냈다.
정상/잘못된 token의 실제 SHA 입력은 각각 **43B/25B**, 응답은 201/401이다.
각 request의 모든 native SHA/parser witness 값과 원 counter가 exact 일치했고, 연결 종료 후
후속 cost snapshot도 불변이었다. 인증 문자열은 artifact에 저장하지 않았다.
[원 증거](benchmarks/t66f-b03-independent/evidence/python-real-tls-independent.json).
TLS 내부 crypto는 이 application byte 정의에서 제외한다. 실제 지원 transport를 실행했으므로
thread-only 시험으로 HTTP 격리를 대체하지 않았다.

## 15. Flutter async scope

독립 시험은 작업 시작→yield→owner close→다른 run 시작→원 callback 재개/예외를 실제 수행했다.
닫힌 collector snapshot은 고정되고 새 run은 11B 및 nested e4Read 1B만 소유한다.
원 retry/observation renewal/cancel/logout/supersession 회귀도 전체 suite에 포함됐다.
진단 context는 AppState ticket이나 publication authorization을 대신하지 않는다.

## 16. Native worker의 취소 및 늦은 완료

독립 worker가 3B를 hash한 뒤 Event에서 대기하도록 했다. started 확인 후 ASGI task를 취소하고
다른 run을 실행한 다음 worker를 풀어 7B를 추가 hash하고 예외를 내게 했다.
원 collector는 2 calls/56B, 새 collector는 32B이며 completion 1회, pending 0, native lease/job/task 0이다.
worker가 시작하기 전 취소한 시험으로 이 결과를 대체하지 않았다.

별도 실험에서 이미 닫힌 lease의 `run()`은 원래대로 거부되지만 `NativeJob.__init__`의 diagnostic
hold가 회수되지 않는다. native budget은 전부 0인데 collector pending=1/closed=false,
finish callback=0이다. measurement cohort가 완결되지 않는 **계측 수명 결함**이다.
제품 permit leak나 authority revival로 분류하지 않는다.

## 17. Late import 및 반복 설치

기존 alias·활성화 후 import·teardown 후 새 reference는 원 B03 보정에서 통과했다.
순차 설치/복구는 원 primitive로 돌아온다. 그러나 `instrument()` 안에서 다시 설치하면
`decode_c1(b'{}')` 실제 3회에 JSON 4 calls/8B가 기록된다(expected 3 calls/6B).
원 parser를 두 번 실행한 것은 아니며 observer가 겹쳐 한 호출을 두 번 센다.
명시 거부나 session refcount 없이 재진입을 완전 지원한다고 볼 수 없다.

## 18. P0 recovery-lineage exact 동등성

역사 원문은 `da818648`에서 읽었고 전체 SHA는
`a8d767e509881a1a8e9d3196d1fd955b1b4cf793a36f3ffd593b869b686bf8c2`다.
원 함수/원 canonical helper를 독립 test에 보존하여 현재 disabled/enabled와 hex byte-by-byte 비교했다.
6개 golden은 빈 hash 입력·Unicode/control·중첩 metadata·BMP/supplementary key order·array order를
포함한다. 별도 Python golden 및 기존 baseline 4종도 일치한다. 호출마다 toJson/encoding/hash는 각각 1회다.
미니멀 hash vector를 valid 전체 recovery baseline이라고 표현하지 않는다.
실제 Frozen v7/v4 설치·reopen/fresh process는 별도 회귀로 검증한다.

## 19. 역사 SHA와 현재 exact lock

현재 6파일의 exact SHA가 실제 committed source와 일치한다. 기존 5파일의 승인된 exact hunk만
되돌린 원문은 `da818648`의 전체 bytes 및 역사 SHA와 동일하다. 기존 23 guard와 신규 6 guard를
새로 실행했고 skip/xfail·기대 hash 수정은 없다. manifest와 구현 보고서는 C1/AppState 및 P0 한정
승인을 기록한다. 저장소 정책에는 별도 외부 서명 증거 의무가 없다. 외부 대화 원문을 새로 확인했다고
주장하지 않으며 이 감사가 새 source-lock 승인을 발급하지 않는다. 보호 diff 자체도 §3/18에서 검토했다.

## 20. E1/E2/E3/E4 교차계층 coverage

|경계와 source|실제 관측|stage·보정·제한|
|---|---|---|
|backend `canonical.py:131,161,202`, D2 finalization/Store|SHA constructor/update, JSON span, NEW row TEXT/BLOB|generation; literal/native witness. SQL 반례로 전체 정산 FAIL|
|backend `http.py:85`, `transfer.py:130`, observation/retention|request C1 admission, typed-prefix/terminal object hash/decode, 기존 edges/cache/response metrics|observation/transfer; 실제 TLS. structural visits는 bytes가 아님|
|Flutter `object.dart:113,127`, `fetch.dart:226,743`, `c1.dart`|새 object·실패·반복 hash/C1 span, provenance/cache/graph 방문|e2; literal 및 TLS의 독립 하한/전체 BLOB oracle|
|Flutter `store.dart:open`, immutable put 및 SQL|실제 INSERT attempt/effective, TEMP NEW payload/trigger/cascade|caller stage+table; supported 정상 경로 exact, failure/SQL 분류 반례 존재|
|Flutter `verification.dart`, `incremental_verification.dart`, `store_publication.dart`|검증 C1/SHA, receipt/metadata/pin/accepted SQL 및 원 work|e3Verify/e3Prepare/e3Commit; final guard 불변. committed 정산 전체 FAIL|
|Flutter `store_read.dart`, `store_frozen.dart`, `workspace.dart`, `adapters.dart`|hash-on-read/checksum/legacy/lineage, file UTF8 span/write/flush/rename|e4Read/recovery/e4Legacy; healthy reuse와 full fallback 구별|

각 단계의 nonzero 값만으로 COMPLETE를 선언하지 않는다. primary byte primitive의 도달성은
확인했지만 지원 SQL의 실패/정산/초기 설치와 native admission 경계가 전체 완결성을 차단한다.
opaque crypto·정확한 실패 소비 prefix·byte 입력 없는 구조 검사·물리 I/O는 명시 제외다.
backend raw cursor/executescript와 Dart custom/lazy/native-handle 우회 API는 이 observer의 검증된
계약으로 수용하지 않는다. 현재 isolated D1–D3 및 segmented store에는 그런 호출이 없으며,
Snapshot restore/operation_stats의 executescript를 R1/전체 앱 coverage로 확대하지 않는다.

## 21. Frozen 및 file 경계

실제 Frozen 설치, healthy 반복 read, reopened handle 및 fresh process fallback을 원 B03 assertion으로
새로 실행해 통과했다. file write는 기존 encoding을 한 번 위임하고 submitted/completed/failed를 나눈다.
healthy read의 lineage 재hash·full recovery·pin rewrite가 0인지 별도 work/SQL로 확인한다.
이번 healthy4회에서 object reads8/verified37,804B/provenance reuse8, full recovery0/pin write0/
lineage SHA0이다. baseline file 완료 payload는14,637B, source는341B이며 설치 lineage는
3calls/44,112B, reopen/fresh process는 각각2calls/29,408B다. 한 lineage 입력14,704B는
baseline file 크기와 다른 wrapper preimage다. pending B/J 원문·source ownership/previous-source 계약은 유지된다.
소형 실제 설치의 coverage를 native 100k Frozen installation proof로 확대하지 않는다.
큰 legacy restore/materialization budget 및 R1/activation 책임은 그대로다.

## 22. 작은 실제 HTTP 독립 reconciliation

독립 `http_test.dart`는 새 TLS backend의 deterministic history 3 fixture에서 실제 E2/E1/E3/E4를
disabled/enabled 두 client에 수행한다. 각 stored canonical BLOB와 직접 backend source rows,
accepted sync_root/sequence 및 전체 E4 금융 값을 비교한다. cold 고유 object payload 합은 exact,
E2 hash는 각 신규 object의 domain+NUL+raw 합 이상, validation은 raw 합 이상이어야 한다.
하한은 fixture buffer와 source의 필수 admission에서 도출하며 counter를 oracle로 사용하지 않는다.
각 실제 backend hash/parser는 native witness와 exact 비교한다. 동일 generation retry에는 신규
object bytes가 늘지 않아야 한다. HTTP entity·timing은 기존 Wire의 실제 request/response와 별도로 남긴다.
독립 fixture의 실제 ledger N은4(history3+current1), 전체 authoritative rows는40이다.
H=null인 소형 profile로 규범 fixed-H grid와 구별한다. 144 objects/89,644 canonical B이며 최소 hash preimage는93,985B다.
실제 e2 hash569,645B/validation submitted1,190,360B는 정당한 반복·outer admission을 포함해
각 하한 이상이고, cold E1 committed body89,644B는 exact다. cold+identical+E4의 두 모드는
각150 HTTP requests/request entity83,390B/response entity165,060B로 일치했다.
전체 root·sequence1·모든 object BLOB·11-table 금융 raw 값도 같았다. cold wall 단일 표본은
비활성25.340s/활성21.888s다. 순서·cache·host 잡음이 있으므로 speedup/오버헤드 비율로 쓰지 않는다.
실제 backend witness는 모든 audited SHA/parser 계수와 exact 일치했다.
원 별도 real TLS9/260 및 Frozen 포함 calibration은71 PASS, final authority 두 probe도2 PASS다.

## 23. 정수·메모리·capacity

Python 임의 정밀도와 Dart BigInt는 overflow 없이 검증했다. Dart의 462개 enum 조합 각각에서
signed64 상한 두 번 합은 `18446744073709551614`다. SQL table 129번째·savepoint 33번째는
명시 오류를 반환한다. 일반 unsupported API도 오류로 거부하지만 comment-DML은 조용히 빠진다.

primitive category·table·savepoint·request sample의 수치 제한과 전체 collector 수명은 다르다.
같은 미완료 SQL transaction에서 닫힌 collector 10/100/1000개는 pending key 50/500/5000개를
남겼고 weakref로 각각 전부 보존됐다. rollback 뒤 0으로 해제된다. per-transaction owner 수를
제한하거나 closed owner를 정리하지 않으므로 무조건적인 고정 메모리 주장에는 반례가 있다.
현재 보정한 단일 run에서는 원문/per-object event를 보관하지 않는다. 기존 Wire의 HTTP trace
보관량까지 상수 메모리라고 주장하지 않는다.

## 24. Enabled/disabled overhead

독립 `overhead.py`/`overhead_test.dart`는 동일 process·fixture·runtime에서 3 warmup 뒤
20 alternating pair를 사용한다. small은 primitive 200회/64-character payload/SQL20행,
medium은 2,000회/4,096-character payload/SQL200행이다. 실제 raw 길이는 JSON 프레이밍을 포함해 기록한다.
Python은 wall/CPU/설치·해제·RSS 차분, Flutter는 wall/process CPU tick/collector·DB observer 생성·close/RSS 차분을 분리한다.
SQL은 실제 TEMP 관측 overhead를 포함한다. RSS 차분을 heap allocation으로 표현하지 않는다.
호출당 활성 key string/BigInt 생성은 source로 확인했으며 exact VM allocation은 미측정이다.
Flutter CPU는100 ticks/s(10ms 분해능)의 process 전체값이다. 작은 구간의0 tick을 CPU 작업0으로 해석하지 않는다.
Python max RSS는29,032,448B, Flutter max RSS는193,687,552B였으며 medium RSS median 차분은
Python off/on 모두0B, Flutter266,240/270,336B다. GC·메모리 재사용 영향으로 allocation 합계가 아니다.
아래는20쌍의 실제 median/p95(ms)다. 임의 허용 threshold는 없다.

|runtime/작업|small off|small on|medium off|medium on|
|---|---:|---:|---:|---:|
|Python primitive|2.658/2.991|4.190/4.516|77.850/79.573|94.339/95.212|
|Python SQL|0.056/0.066|0.911/0.953|0.701/0.851|5.833/6.185|
|Flutter primitive|2.163/4.491|2.296/5.226|468.686/472.124|470.329/474.392|
|Flutter SQL|0.423/0.573|2.931/3.887|1.060/1.885|10.424/13.484|

medium Flutter primitive CPU median은 off/on 모두48 ticks(480ms), SQL은0/1 tick이다.
medium Python observer 설치/해제 median은64.018/48.628µs, native DB+observer 생성은
45.556µs(off37.598µs), DB close111.126µs(off58.913µs)다. Flutter observer 생성은
17µs, DB close49.5µs(off30µs), primitive aggregate key는6개다. 원20개 samples와 CPU/p95는 summary에 보존한다.
최초 Python overhead fixture에서 필수kind를 누락해 REJECT_OBJECT_KIND로 실패했다.
그 로그를 보존하고 감사 fixture에만kind를 추가해 재실행했다. 이후 CPU/DB observer 비용을 추가한
최종 complete 실행도 별도 파일로 보존했다. 제품 source나 counter를 수정하지 않았다.

역사 100k는 cold terminal 2,463.561s, 세 번째 observation 마지막 object의 남은 시간 236.81s였다.
새 overhead를 이 여유에 무조건 선형 환산해 100k 성공으로 판정하지 않는다. 실제 활성 계측의 대형
lease perturbation 증거는 없으므로 readiness의 이 부분은 **INCONCLUSIVE**다. TTL/attempt는 늘리지 않았고
새 100k cold는 실행하지 않았다. SQL observer 비용을 일반 무계측 앱 latency로 보고하지 않는다.

## 25. Disabled/enabled 제품 동등성

source diff·literal/golden·실제 TLS의 object 및 금융 값·전체 회귀를 함께 사용한다.
C1 원문/hash/typed identity, v7 fingerprint/lineage, backend graph root, accepted sync_root/sequence,
E4 raw 값은 검증한 입력에서 동일하다. 서로 다른 실행의 새 UUID/nonce/timestamp 및 SQLite physical
file를 byte-identical하다고 주장하지 않는다. source-lock 복원 및 실제 authority 회귀는 error/cancel 경계를 보완한다.
계측만을 위해 추가 product hash·parse·persistent DML을 수행한 경로는 발견하지 않았다.
TEMP trigger 설치·UDF 계산은 명시 진단 overhead이며 제품 persistence가 아니다.

## 26. B01 보존

`backend/tests/test_isolated_sync_transfer.py:504`의
`assert sorted(r.status_code for r in results) == [201]*4+[429]`는 원문 그대로다.
해당 test의 supported 5,000ms local budget, production 1,000ms 기본 budget, DB opened-FD identity fence,
permit lifecycle source는 변경되지 않았다. 새 full backend에 원 strict case가 포함되어 PASS다.
새 계측 반례로 B01 correctness를 재개방하지 않는다. 과거 두 실패의 개별 원인을 새로 추정하지 않는다.

## 27. B02 보존

default E2 objects100000/edges200000, E1 metadata32MiB, explicit large500000/1000000/384MiB,
packet64/1MiB, TTL900초, observations3/attempts3는 불변이다. large profile은 기본 비활성이다.
request-local D3 prefix cache, canonical/typed path, continuation·HTTP cleanup·incremental reuse 알고리즘도
이번 B03에서 변경되지 않았다. full backend/Flutter에 관련 회귀를 포함했다. 재현된 B02 제품 regression은
없으며 CLOSED를 유지한다. 이미 닫힌 100k functional cold를 비용 누락 보완용으로 재실행하지 않았다.

## 28. 전체 backend 회귀

최종 독립 backend test 추가 후 `backend` cwd에서 full pytest를 실행했다.
**1,410 tests / 1,540 subtests PASS**, failures/errors/skips 0, 실제 exit0/외부 종료 없음이다.
pytest 시간 1,812.21s, bounded runner 시간 1,814.159s다. 기존 deprecation warning 1개다.
신규 독립 18 + 기존 B03 24 + 원 calibration16의 별도 실행도 **58 PASS**다.
D1–D3c/C1/B01/prefix reuse/DB identity/permit 회귀가 포함됐다. JUnit와 원 gzip은 독립 evidence에 있다.
결함 재현 assertion의 PASS는 해당 계측의 정확성 PASS가 아니다.

## 29. 전체 Flutter 및 정적 회귀

최종 `mobile/test` 독립 14개 추가 후 `flutter test --no-pub --machine --concurrency=4`를 실행했다.
**1,662 PASS / 0 FAIL / 2 SKIP**, `done.success=true`, exit0/외부 종료 없음, 2,555.540s다.
기존 E1/E2/E2-A01/E3/I25/E4/A01/RA01/P0/Frozen/v7/v4/AppState/B02/source-SHA를 포함한다.
docs 아래 별도 독립 HTTP/authority probe는 default full suite 수에 합산하지 않고 별도 최종 실행한다.

최초 별도 HTTP 프로세스는 full Flutter와 동시에 native-assets manifest를 생성하다 시작 실패했다.
이는 감사 실행 환경의 충돌로 로그를 보존하고 순차 재실행한다. full suite는 위와 같이 정상 완료했다.
Ruff·compileall·frontend build, 전체 Flutter analyze, debug APK build(audit.invalid, 설치 없음),
외부 독립 probe analyze는 exit0다. changed-file format/diff의 최종 실제 결과는 기계 summary와 footer에 기록한다.
전체 source regression은 mobile/test 및 backend/tests에 추가한 최종18/14 cases를 포함한다.
그 뒤 default suite source는 수정하지 않았으며 docs의 별도 probe는 해당 범위의 최종 소스를 별도 실행했다.

## 30. 새 독립 findings

모든 확정 반례는 **INSTRUMENTATION DEFECT** 또는 **MISSING MEASUREMENT COVERAGE**다.
새 제품 correctness/source-lock 위반은 확인하지 않았다. source 위치·재현·expected/actual·독립 oracle·
비용 영향·최소 교정·B03 차단·B01/B02 영향은 [findings.json](benchmarks/t66f-b03-independent/findings.json)에 있다.

|ID|등급·source|재현 expected → actual|최소 별도 교정·B03 영향|
|---|---|---|---|
|B03-IA01|MEDIUM, `counters.py:324`, `logical_cost_sqlite.dart:149`|동일 이름 nested savepoint: committed1/rollback2B → 0/3B|가장 가까운 savepoint semantics 적용 또는 중복 이름 명시 거부. 차단|
|B03-IA02|MEDIUM, `counters.py:347`, `logical_cost_sqlite.dart:175`|부분 성공 OR FAIL: committed3B → 1B|오류별 native transaction/statement 결과 보존 또는 미지원 복잡성 명시 거부. 차단|
|B03-IA03|MEDIUM, `counters.py:295`, `logical_cost_sqlite.dart:134`|첫 comment INSERT: 실제2B → row metric0/오류없음|지원 SQL 식별 또는 실행 전 coverage 실패. 조용한 누락 제거. 차단|
|B03-IA04|LOW, `counters.py:161`|nested install의 실제3 parse/6B → 4/8B|중첩 설치 명시 거부 또는 한 observer만 소유. 중복 계수 차단 필요|
|B03-IA05|MEDIUM, `counters.py:133`, `workers.py:92`|closed lease dispatch 거부: pending0/완료1회 → pending1/완료0회|실제 등록 성공/실패와 hold/release를 결합. cohort 수명 차단|
|B03-IA06|LOW, `counters.py:242`, `logical_cost_sqlite.dart:57`|Python에서 닫힌1000 scope가5000 pending key로 유지|transaction owner 수 제한/closed owner 정리 또는 명시 unsupported. 전체 고정 메모리 인증 차단|
|B03-IA07|MEDIUM, `server.py:150`, 원 harness `server.py:419,468`|제품 oracle SQL 0개 → generation SQL 2개, 176/185행|oracle 비교를 측정 scope/타이밍 밖으로 분리. generation 비용 격리 차단|

B01/B02 closure는 7건 모두 영향 없음이다. 미지원 SQL을 모두 범용 지원하도록 확장하라는 권고가 아니다.
필요한 최소 경계를 정확히 계측하거나 지원하지 않는 복잡성을 명시 거부하면 된다. 감사자가 교정하지 않았다.

## 31. 남은 정확한 measurement 경계

현재 normal D→E의 C1/SHA/NEW payload seam 도달성은 확인했다. 그러나 nested rollback/부분 성공
SQL/첫 DML/재진입 설치/dispatch 거부/closed-owner 수명과 generation oracle 분리는 완결 계수로 수용할 수 없다.
후속 교정은 위 반례를 보존하고 정상 path와 미지원 경계의 coverage error를 함께 증명해야 한다.
정확한 실패 parser 소비 prefix, SQLite record encoding·physical WAL/VFS I/O, file hardware committed
bytes, opaque TLS/PBKDF2 내부 비용은 이 primary logical metric의 주장 범위 밖이다.

## 32. 고정 H/D 다섯 N 및 I25 준비

N=1000/5000/10000/50000/100000의 동일 H/D, no-change/card/cash, 새 hash/validation/write,
rows/SQL/HTTP/RTT/resource/storage 및 median/p95가 최종 Phase B 의무다. 이번 grid는 **NOT RUN**이다.
작은 예제의 H=null/current ledger1과 큰 profile의 current105를 한 scaling 곡선으로 합치지 않았다.
측정 API 존재와 aggregate 출력만으로 I25 완결·grid readiness를 PASS로 하지 않는다.
committed/rollback 반례와 수명 오류를 별도 최소 교정·독립 재감사하기 전 **재개 NO**다.
대형 계측 lease perturbation은 별도 미검증이며 이미 닫힌 B02 correctness와 구별한다.

## 33. Android 및 device 한계

HOST native SQLite/process crash/debug build는 actual Android memory/VFS/I/O/power-loss의 증거가 아니다.
§26/§38의 장치·rollout 의무는 남는다. 임의 device latency threshold를 만들거나 physical I/O 부재만으로
제품 오류를 선언하지 않는다. APK를 설치하지 않았고 실기기·전원 손실 시험을 수행하지 않았다.

## 34. R1 및 activation 분리

R1 large restore/MW/chunks/artifact/retention/atomic apply/receipt/migration/rollback은 DEFERRED다.
§31/§34 dependency와 activation gate CLOSED를 유지한다. B03 교정을 위해 legacy Snapshot 예산을
늘리거나 일반 사용자 segmented Offline을 켜지 않는다. production deployment/activation은 수행하지 않았다.

## 35. 독립 B03 판정

**FAIL — T6.6F-B03 INSTRUMENTATION CORRECTION REQUIRED**.
독립 DB와 어긋나는 계측이 재현되므로 단순 환경 INCONCLUSIVE로 끝내지 않는다.
원 B03 75 tests 및 full regressions의 성공은 이 반례의 반증이 아니다. B03 finding은 OPEN이다.
hash primary semantics와 P0 exact 동등성의 PASS 범위, 실패한 write/scope 경계를 구별해 수용한다.
Phase B 전체는 여전히 INCONCLUSIVE, T6.6F exit는 NOT SATISFIED다.

## 36. Phase B continuation 권한

최종 cost grid를 검증 완료로 선언할 수 없고 B03 기반 재개 승인은 NO다.
다음 조치는 **별도 교정에서 B03-IA01~07의 계측 경계를 최소 수정하고 같은 독립 반례를 재검증하는 것**이다.
금융 authority·protocol·TTL·source-SHA 기대값을 변경할 필요가 있다는 결론은 내리지 않았다.
B01/B02는 CLOSED이며 R1·device·deployment 승인은 별도다.

## 37. Audit-only commit/push 증거

새 독립 test 2개, `docs/benchmarks/t66f-b03-independent/`, 본 보고서만 stage한다.
원 제품·protocol·source locks·역사 reports·원 tests 2,595개 tracked 원문의 동일성을 재검사한다.
CI workflow는 test/build만 수행하며 push를 deployment 허가로 취급하지 않는다.
정상 commit/push 뒤 HEAD/main/origin/main/실제 remote와 clean worktree를 최종 응답에서 확인한다.
자기 SHA를 넣기 위한 amend/history rewrite는 하지 않는다. 이 보고서 추가 commit은
`git log -1 --format=%H -- docs/t66f-b03-independent-instrumentation-audit.md`로 식별한다.

최종 [기계 집계](benchmarks/t66f-b03-independent/evidence/summary.json)는 원 B03 **75 PASS**,
신규 독립 **35 PASS**(backend18/mobile14/별도HTTP2/overhead1), 위 전체 회귀 및 모든 최종 정적 검사의
실제 exit를 확인했다. 7개의 결함 재현 pytest 사례와 직접 실험3종을 정확성 PASS로 전용하지 않는다.
원 23 source guard와 현재6 exact guard는 모두 PASS다. 최종 동작 source가 같은 default full suite와
docs의 최종 별도 probe 실행을 구별했다. 최종 snapshot·모든 코드와 protected 원문을 보존한 뒤
audit-only commit/push한다. 실제 commit/remote/clean 종료 증거는 최종 응답과 Git history로 식별한다.

## 필수 최종 상태

```text
T6.6F-B03 INDEPENDENT INSTRUMENTATION AUDIT:
FAIL

AUDITED B03 IMPLEMENTATION COMMIT:
a96e130682023522ec56ab6e2fc9f53ec8d77df6

B03 DOCUMENT RECEIPT COMMIT:
ea2c32ce75a5f6894f52dc1b8fb4e2b1ae6df478

STARTING PHASE B AUDIT COMMIT:
da818648031e013e83dd6a680b1b1bde0fb6e0a1

FINAL AUDIT-ONLY COMMIT:
본 보고서 추가 commit — §37의 git log 명령으로 식별하며 최종 응답에 실제 SHA를 기록한다.

REPOSITORY STATE:
VERIFIED

PRODUCT SOURCE MODIFIED BY AUDITOR:
NO

BINDING PROTOCOL:
UNCHANGED

COMPLETE B03 DIFF:
REVIEWED

INSTRUMENTATION DEFAULT:
DISABLED

INSTRUMENTATION SCOPE:
EXPLICIT TEST-ONLY

SINGLE-USER DESIGN:
PRESERVED

HASH INPUT BYTE DEFINITION:
VERIFIED

VALIDATION INPUT-SPAN DEFINITION:
VERIFIED

LOGICAL WRITE BYTE DEFINITION:
VERIFIED

HASH COUNTER CALIBRATION:
PASS

VALIDATION COUNTER CALIBRATION:
FAIL

WRITE COUNTER CALIBRATION:
FAIL

ACTUAL HASH INPUT BYTES:
CORRECT

ACTUAL VALIDATION INPUT SPANS:
INCORRECT

ACTUAL SQL LOGICAL WRITE BYTES:
INCORRECT

ATTEMPTED WRITE ACCOUNTING:
FAIL

EFFECTIVE WRITE ACCOUNTING:
FAIL

COMMITTED WRITE ACCOUNTING:
FAIL

ROLLBACK/SAVEPOINT ACCOUNTING:
FAIL

RETRY ACCOUNTING:
PASS

CACHE REUSE ACCOUNTING:
PASS

STAGE ATTRIBUTION:
FAIL

COUNTER OVERLAP:
DOCUMENTED

BACKEND CONCURRENT HTTP:
PASS

BACKEND TLS SCOPE ISOLATION:
PASS

FLUTTER ASYNC SCOPE:
PASS

CLOSED SCOPE BEHAVIOR:
PASS

LATE NATIVE WORKER:
PASS

LATE IMPORT COVERAGE:
PASS

COUNTER OVERFLOW:
PASS

COUNTER MEMORY BOUND:
FAIL

P0 RECOVERY LINEAGE FUNCTION:
REVIEWED

P0 FINGERPRINT EXACT EQUIVALENCE:
PASS

P0 HASH INPUT BYTE COUNT:
PASS

HISTORICAL SOURCE-SHA:
PRESERVED

CURRENT EXACT SOURCE-SHA:
PASS

SOURCE-LOCK POLICY:
PASS

BACKEND GENERATION COVERAGE:
FAIL

BACKEND D3 COVERAGE:
INCONCLUSIVE

FLUTTER E2 COVERAGE:
PASS

FLUTTER E1 COVERAGE:
FAIL

FLUTTER E3 I25 COVERAGE:
FAIL

FLUTTER E4 COVERAGE:
PASS

FROZEN/FILE COVERAGE:
PASS

CROSS-LAYER RECONCILIATION:
INCONCLUSIVE

SMALL REAL HTTP MEASUREMENT:
PASS

EXTRA HASHING FOR MEASUREMENT:
NONE

EXTRA VALIDATION FOR MEASUREMENT:
NONE

EXTRA PRODUCT PERSISTENCE:
NONE

INSTRUMENTATION OVERHEAD:
INCONCLUSIVE

DISABLED-PATH EQUIVALENCE:
PASS

ENABLED-PATH FINANCIAL EQUIVALENCE:
PASS

E3 FINAL AUTHORITY GUARD:
PRESERVED

E3 GUARD-TO-COMMIT:
PASS

E4-A01:
CLOSED

E4-RA01:
CLOSED

B01:
CLOSED

B02:
CLOSED

ORIGINAL B03 TESTS:
75 PASS
0 FAIL

NEW INDEPENDENT B03 TESTS:
35 PASS
0 FAIL
0 SKIP

FULL BACKEND:
1410 TESTS
1540 SUBTESTS
PASS

FULL FLUTTER:
1662 PASS
0 FAIL
2 SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

RUFF:
PASS

COMPILEALL:
PASS

CHANGED-FILE FORMATTING:
PASS

GIT DIFF CHECK:
PASS

FULL FIVE-POINT N COST GRID:
NOT RUN — SEPARATE PHASE B

FIXED H/D GRID READINESS:
FAIL

E3 I25 COST MEASUREMENT READINESS:
FAIL

MANDATORY B03 COVERAGE GAPS:
동일 이름 savepoint 정산, 부분 성공 SQL 정산, 첫 comment-DML 관측, 중첩 설치 중복 방지, 거부된 native dispatch의 hold 회수, transaction owner 보존 상한, generation과 oracle SQL 분리, 활성 계측의 100k lease 영향 증거.

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
5

NEW LOW:
2

UNRESOLVED B03 BLOCKERS:
7

B03 FINDING:
OPEN

SAFE TO RESUME PHASE B FINAL COST GRID:
NO

T6.6F PHASE B:
STILL INCONCLUSIVE

BINDING T6.6F EXIT CRITERIA:
NOT SATISFIED

ANDROID MEMORY SAFETY:
NOT VERIFIED

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

PRODUCTION SEGMENTED ACTIVATION:
NOT PERFORMED

SAFE TO DEPLOY:
NO

FINAL VERDICT:
FAIL — T6.6F-B03 INSTRUMENTATION CORRECTION REQUIRED

NEXT ACTION:
별도 교정에서 B03-IA01~07의 계측 경계를 최소 수정한 뒤 독립 재감사를 수행하세요.
```
