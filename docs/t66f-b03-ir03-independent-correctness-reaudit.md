# T6.6F-B03-IR03 독립 정확성 재감사

**FAIL — B03 계측 교정 필요.** 동결 후보를 정확히 복원했고 원 IA01–IA07의 역사 실패를 재현했다. 원 중첩 설치 사례는 교정됐지만 IA04 교정에 새 동시 설치 누락이 존재한다. Python과 Dart의 스키마 변경 후 SQL payload 누락도 독립 재현했다. 이 판정은 금융 계산 오류나 B01/B02 재개방을 뜻하지 않는다.

## 1. 독립성과 감사 대상

이 세션은 B03 구현, IC01 교정, P01/P02/P03/P04/P05 구현·진단, IR01 범위 판단, IR02 후보 준비에 참여한 이력이 없다. 이번 세션에서도 제품·계측 source를 수정하지 않았다. 독립성은 **SATISFIED**다. 다른 세션의 정체나 인적 이력을 외부 인증했다는 주장은 하지 않는다. 구현 측 PASS는 배경 자료로만 사용했다.

실행 대상은 `/tmp/money-note-ir03-20261023/candidate`다. 원본 dirty checkout이나 read-only archive에서 제품 시험을 실행하지 않았다. 읽기 자료의 SHA는 [reading-manifest.json](benchmarks/t66f-b03-ir03/reading-manifest.json), 환경은 [environment.json](benchmarks/t66f-b03-ir03/environment.json)에 있다.

|식별 항목|독립 관측|
|---|---|
|committed baseline|`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`|
|archive SHA-256|`87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01`|
|payload SHA-256|`645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8`|
|source inventory|819개 / 9,085,052바이트|
|archive regular members|834개|
|tracked deletion / staged override|0개 / 없음|
|원본 index 파일 SHA-256|`d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`|

[reconstruct.py](benchmarks/t66f-b03-ir03/reconstruct.py)는 고정 Git object의 `git archive`에 archive의 819개 payload를 덮어 복원한다. 현재 working-tree source를 입력으로 사용하지 않는다. 모든 member의 경로·중복·regular-file 여부·길이·mode·SHA를 확인하고 entries의 `json.dumps(ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()`를 다시 hash했다. 고정 commit object와 삭제 목록, source mode를 확인했다. 제공된 verifier의 PASS를 독립 계산의 대용으로 사용하지 않았다. [integrity.json](benchmarks/t66f-b03-ir03/integrity.json)이 실행 전 identity다.

## 2. 구속력 있는 요구와 승인 범위

T6.6C §7은 실제 domain/NUL/canonical bytes의 identity를, §23은 받은 bytes의 admission을, §24–25는 완전 graph·동기 authority fence와 durable publication을 요구한다. §35는 고정 H/D의 다섯 N에서 실제 rows/hash/validation/write/HTTP/RTT/memory와 반복 통계를 요구하고 §36 I25는 정상 상태의 숨은 full-N 작업을 금지한다. 정확한 계측은 이 증명의 필요 수단이다.

해당 문구에서 모든 보조 timing observer를 동시에 켠 성공한 N=100k cold 실행을 별도 B03 도구 정확성 폐쇄의 선행 조건으로 찾지 못했다. IR02 및 이번 사용자의 승인 범위는 binding과 양립한다. 이 해석은 다섯 N·I25·full-scale feasibility 의무를 면제하지 않는다. §5의 epoch, §15–17의 실제 credential/TTL/최대 관측 수, §22/29의 fingerprint 분리와 Frozen B/J, §26/31/34/38의 장치·R1·rollout 요구는 유지한다.

## 3. 원 IA01–IA07 판정

원 보고서 전체, findings JSON, 원 SQL/native 재현 source, 원 raw 수치를 대조했다. 정확한 baseline 및 별도 역사 wrapper에서 결함 존재 assertion을 변경하지 않고 실행했다. 역사 assertion의 PASS는 해당 결함이 재현됐다는 뜻이다. 현재 source의 정확성 oracle와 수치에 합산하지 않는다. [direct-controls.json](benchmarks/t66f-b03-ir03/direct-controls.json), [findings.json](benchmarks/t66f-b03-ir03/findings.json)에 원 ID를 보존한다.

|ID·원 등급|역사 반례|현재 독립 관측|finding 수용 판정|
|---|---|---|---|
|IA01 · MEDIUM|같은 이름의 중첩 savepoint에서 committed 0B / rollback 3B|nearest frame을 따라 committed 1B / rollback 2B; quoted 이름도 일치|PASS — 원 결함 독립 폐쇄|
|IA02 · MEDIUM|OR FAIL 성공 prefix를 버려 committed 1B|native에 prior 1B + a 2B 보존, committed 3B; ABORT/ROLLBACK/IGNORE도 구별|PASS — 원 결함 독립 폐쇄|
|IA03 · MEDIUM|첫 comment INSERT 2B를 오류 없이 0B로 보고|주석·줄 주석·선행 semicolon에서 2B 계수|PASS — 원 결함 독립 폐쇄|
|IA04 · LOW|실제 parse 3회/6B를 4회/8B로 중복|원 nested 사례는 3회/6B. 새 concurrent 설치에서는 1회/2B가 0으로 누락|**FAIL — 교정에 새 결함 존재**; N02 참조|
|IA05 · MEDIUM|등록 거부 뒤 pending 1 / completion 0|pending 0 / completion 1 / native leases·jobs·running·tasks 모두 0|PASS — 원 결함 독립 폐쇄|
|IA06 · LOW|닫힌 10/100/1000 owner가 50/500/5000 pending key로 보존|32개 한도, 33번째 실행 전 오류, rollback 뒤 weakref 보존 0|PASS — 원 결함 독립 폐쇄|
|IA07 · MEDIUM|oracle SELECT 두 번의 176/185행이 generation에 포함|동일 cursor 한 번 위임에서 둘 다 setup; generation의 oracle SQL 0|PASS — 원 결함 독립 폐쇄|

## 4. 새 결함 N01 — 스키마 변경 뒤 SQL payload 누락

**B03-IR03-N01 · MEDIUM · B03 폐쇄 차단.** 위치는 `docs/benchmarks/t66f-b03/counters.py:373` 및 `mobile/test/support/logical_cost_sqlite.dart:259`다. `_cost_tables`/`_tables`에 같은 이름이 있으면 다시 검사하지 않는다. ALTER의 새 column이 이전 TEMP trigger에 포함되지 않고, DROP이 trigger를 없앤 뒤에도 재생성한 같은 이름을 이미 관측 중이라고 간주한다.

|정확한 순서|독립 oracle|Python / Dart 실제|
|---|---:|---:|
|1B INSERT → ALTER ADD extra BLOB → b=2B,extra=3B INSERT|누적 attempted/effective/committed 각각 6B|각각 3B|
|1B INSERT → DROP/CREATE 같은 table → 3B INSERT|누적 attempted/effective/committed 각각 4B|각각 1B|

oracle는 counter가 아닌 실제 native SQLite 값의 BLOB 길이와 고정한 입력이다. DROP 전 이미 committed 1B도 누적 비용에 포함한다. row 데이터는 정상이며 조용한 수치 누락이 문제다. [test_ir03_oracles.py](benchmarks/t66f-b03-ir03/test_ir03_oracles.py), [ir03_oracles_test.dart](benchmarks/t66f-b03-ir03/ir03_oracles_test.dart), [ddl_native_probe.dart](benchmarks/t66f-b03-ir03/ddl_native_probe.dart)에 재현을 보존했다. [new-ddl-alter.json](benchmarks/t66f-b03-ir03/new-ddl-alter.json), [new-ddl-drop_recreate.json](benchmarks/t66f-b03-ir03/new-ddl-drop_recreate.json), [dart-ddl-native.json](benchmarks/t66f-b03-ir03/dart-ddl-native.json)이 원시 관측이다.

exact 역사 Python wrapper도 같은 두 누락을 보인다. 이번에 발견한 잔존 결함이며 P02가 새로 만들었다고 주장하지 않는다. 현재 정상 D→E의 schema 변경 순서에서 재현됐다고 확대하지 않는다. 그러나 facade가 해당 DDL을 수용하고 DDL invalidation 회귀도 제공하면서 후속 지원 DML을 완결 수치로 보고하므로 B03 정확성 폐쇄는 차단한다. cache0/32의 서로 같은 오계수는 독립 oracle가 아니다. 최소 교정 경계는 진단 schema/trigger 유효성 관리 또는 실행 전 명시적 미지원 거부다.

## 5. 새 결함 N02 — 동시 최초 설치의 준비 완료 누락

**B03-IR03-N02 · LOW · B03 폐쇄 차단.** 위치는 `counters.py:28–36`, `instrument()`의 초기 설치 분기다. registry가 준비 중인 state를 먼저 공개하고 lock 밖에서 patch를 설치한다. 두 번째 caller는 refcount만 올리고 설치가 끝난 것으로 보고 본문에 진입한다.

독립 test는 A의 첫 `ExitStack.enter_context` 직전만 barrier로 멈추고 B가 `instrument()` 안에서 `decode_c1(b'{}')`를 한 번 수행하도록 한다. parser·hash·SQL delegate는 바꾸지 않는다. 실제 한 번 호출과 literal 2B가 oracle다. 현재 B의 snapshot은 `{}`이고 calls/span은 0이다. A 재개 뒤 registry는 정상 정리되므로 영구 registry leak로 확대하지 않는다. 같은 schedule의 exact 역사 wrapper는 B의 1회/2B를 계수했다. 따라서 IA04 원 nested 반례가 교정됐다는 사실과 별개로 교정 수용 판정은 FAIL이다.

[test_ir03_installation.py](benchmarks/t66f-b03-ir03/test_ir03_installation.py), [concurrent-installation-ir03_install.json](benchmarks/t66f-b03-ir03/concurrent-installation-ir03_install.json), [concurrent-installation-historical.json](benchmarks/t66f-b03-ir03/concurrent-installation-historical.json), `independent-installation-final.xml` / `installation-historical.xml`을 대조한다. 적용 범위는 겹치는 최초 test-only 설치다. 이미 설치된 한 session의 실제 TLS 요청 격리 실패나 금융 오류를 주장하지 않는다. 최소 교정 경계는 설치 준비 완료의 publication 또는 겹치는 최초 설치의 명시적 거부다.

## 6. 독립 byte oracle와 transaction 의미

새 Python oracle는 literal prefix `money-note.sync.v1/hot` + NUL + raw bytes 및 실제 하위 native constructor/update 입력을 독립 관찰한다. 빈 값·한글/emoji/결합 문자·256종 bytes·65,537B, 반복 hash·chunk/copy·실패 update·closed scope를 검사했다. 동일 native hash를 제품 operation마다 한 번만 위임했다. HTTP 크기나 메모리 객체 크기를 기대값으로 쓰지 않았다. Dart는 독립 crypto literal preimage와 결과를 대조한다.

validation은 primary UTF8/JSON/C1 submitted/completed/failed span을 실제 buffer 길이로 대조한다. 잘린 JSON·중복 key·잘못된 UTF8·surrogate·noncanonical spacing·Unicode·반복·다른 stage를 포함한다. backend JSON parse 완료와 Dart 전체 C1 완료는 다르다. 구조 검사의 visits에 객체 크기를 곱하지 않았다. 원 nested 설치는 통과하지만 N02가 실제 validation span을 누락하므로 전체 validation 판정은 FAIL이다.

SQL은 NEW TEXT UTF8/BLOB payload이고 숫자·NULL은 값 count다. UPDATE는 NEW row 전체이며 DELETE 신규 bytes는 0이다. INSERT/UPDATE/DELETE/UPSERT/IGNORE, 실패 전 성공 prefix, explicit transaction, 같은 이름·quoted savepoints, ROLLBACK TO/RELEASE, outer rollback, partial executemany iterator 예외, deferred FK의 failed COMMIT 뒤 rollback, collector close를 대조했다. 유효 event와 native commit에 살아남은 event를 구별했다. file/WAL 크기·physical writes·변경 row 수를 payload byte oracle로 사용하지 않았다. 정상 정산 사례가 통과해도 N01 때문에 SQL attempted/effective/committed 전체 정확성은 FAIL이다.

## 7. stage·scope·자원·prepared cache

backend generation과 oracle SQL은 실제 cursor 위임으로 분리됐다. HTTP transport/entity, hash, validation, SQL bytes는 겹치는 별개 operation이므로 합산 총량을 만들지 않는다. E2 호출 중 E1 SQL은 e2 소유이고 E3 verify/prepare/commit, E4 read, P0/legacy는 별도 scope다. readback은 e3Commit에 포함되므로 다시 더하지 않는다. N02는 stage 혼합이 아니라 stage event 소실이며 전체 scope 안전성 수용을 막는다.

실제 TLS에서 승인 principal 1/2가 각각 201을 받았고 request-local native SHA/parser witness가 일치했다. 잘못된 요청 뒤에도 이전 두 snapshot은 불변이고 모든 request가 완료됐다. 기존 원 independent started-worker cancellation 시험과 새 rejected-dispatch oracle는 requester 취소와 실제 native tail 종료를 구분한다. 닫힌 scope는 새 계수를 받지 않는다. Flutter의 concurrent Future/yield, nested scope와 late exception도 별도 검증한다.

source에는 table128, savepoint32, transaction-owner32, managed prepared handle32, 고정 세 설치 registry와 request sample16의 제한이 있다. 상한 초과의 실행 전 오류와 종료 해제를 검사했다. 이는 native bytecode·RSS의 절대 byte 상한이나 caller-owned prepare까지 모든 handle32라는 주장이 아니다. SqlCosts의 Expando와 closed collector 수명도 connection 소유권과 구분했다.

cache의 정확 SQL key, connection-local ownership, reset/rebind·idle BLOB NULL/debug 참조 해제, eviction/finalization·실패 cleanup·BUSY·use-after-close·긴 SQL bypass를 검토했다. 새 독립 cache32 test는 80개 SQL로 peak32/eviction48을 확인하고 다른 연결·반복 BLOB/NULL bind를 대조한다. 기존 P02 10개 회귀는 보조 증거다. SQL 데이터/handle 수명과 N01의 schema observer 오계수를 별도로 보고한다.

## 8. 실제 D→E, E3/E4, P0와 제품 보존

새 history3 합성 fixture에서 원 independent TLS oracle 2개와 새 실제 OFF/ON delta 시험 1개가 통과했다. cold의 144개 canonical object는 89,644B이며 literal domain/NUL을 포함한 독립 최소 preimage는 93,985B다. 실제 E1 committed body는 native SQLite 및 backend canonical bytes와 정확히 일치한다. 새 delta 시험은 각 object의 native SHA·byte identity, 11-table raw 값과 backend hot 결과, accepted sequence와 FK 상태를 비교한다. [delta-integration-summary.json](benchmarks/t66f-b03-ir03/delta-integration-summary.json)에 실제 roots가 있고 원 fixture·전체 oracle는 `delta-integration.json.gz`에 보존했다.

|새 실제 단계|accepted sequence|누적 committed object BLOB|
|---|---:|---:|
|cold|1|89,644B|
|무변경|1|89,644B|
|카드 한 건 title delta|2|104,672B|
|현금 한 건 title delta|3|118,657B|
|실제 HTTP 손상 객체|3 유지|양쪽 `OBJECT_HASH_INVALID / blocked`, 이전 accepted 유지|

이는 금융 공식이나 다섯 N scaling을 독립 재계산한 결과가 아니다. source raw와 backend projection을 그대로 소비해 OFF/ON 결과를 대조했다. 원 independent HTTP의 실제 native SHA/parser witness는 전체 audited metric과 일치했고 distinct TLS principal 및 실패 요청의 scope 종료도 통과했다. E3 final cancel/stale-user probe 2개가 accepted sequence0과 native rollback을 확인했다. Frozen/file 경계의 fresh 회귀10개는 literal7B·native file 길이·Python lineage preimage·healthy reuse·reopen/fresh-process와 pending 보존을 포함한다.

AppState와 store publication source에서 원 ticket/authority 검사를 확인했다. 최종 `finalAuthorityFence(); _db.execute('COMMIT');` 사이 await나 사용자 callback은 없고 진단 COMMIT wrapper도 동기다. diagnostic은 authority를 결정하지 않는다. 금융 projection은 backend 원본과 비교하며 모바일 금융 계산 엔진을 만들지 않았다. Snapshot v7, OfflineBaseline v4, sync_root/v7 fingerprint 분리, Frozen B/J input-only와 pending/reconciliation 경계는 source와 관련 회귀로 확인한다.

현재 6개 source SHA와 5개 inverse를 immutable `da818648`의 실제 Git bytes에 대조해 모두 일치했다. [source-lock-git.json](benchmarks/t66f-b03-ir03/source-lock-git.json)이 근거다. 기존23/current6 실행 결과와 P0의 역사 함수·Unicode/metadata/ordering goldens 및 기존 baseline fixture 결과는 아래 fresh 회귀에 구분한다. SHA 기대값·binding·P0 함수를 수정하지 않았다.

## 9. fresh 회귀·정적 검사와 실행 한계

실제 runtime은 backend Python3.12.3 / SQLite3.45.1, Flutter3.47.4 / Dart3.13.3, Node22.22.3 / npm12.0.1이다. 오케스트레이션 Python3.13.9는 별도로 기록한다.

|fresh 검증|관측과 해석|
|---|---|
|새 독립 고유 oracle|**51 PASS / 5 FAIL / 0 SKIP**, 56개: Python38·Dart17·새 실제 delta1. 실패5개는 N01의 양 언어 두 변형4개 및 N02 1개다.|
|원 독립 재현|backend 원18개 중 결함 존재4개는 exact 역사 wrapper, 나머지14개는 현재. Dart 원 현재11개와 역사3개 분리. IA05–07 원 직접 실험도 별도 재현.|
|backend focused|logical-cost68개: 현재64 + 역사4. D3 authorization·cancel·retention·B01·DB identity/permit도 full에 포함.|
|Flutter focused|primitive/IC01/P02/boundary/lineage/source-lock73 PASS, 실제 HTTP3·기존 overhead1·원 현재11·역사3은 구분한다. 기존23/current6 source guards PASS.|
|전체 backend|**1436 tests / 1540 subtests PASS**, 실패·오류·SKIP0, exit0, 1728.56초. 역사 control4개를 정확성 PASS로 전용하지 않는다.|
|전체 Flutter 최초 3-part|**1682 PASS / 8 FAIL / 2 SKIP**. 일반 현재 part1668/8/2, 원 현재11/0/0, 역사3/0/0. 일반 part exit1과 machine done.success=false, 전체 약46분의 실제 실패를 보존한다.|
|환경 준비 뒤 8개 재검증|동일 source/assertion의 E4 SIGKILL4 + A02 continuation SIGKILL4가 **8 PASS**, exit0/done.success=true. 처음 실패한 raw child의 native asset 미해결 이후, 공식 `dart run` 준비와 최소 SQLite raw/run probe가 모두 통과한 상태에서 재실행했다.|
|전체 Flutter 수용 범위|중복을 제거한 모든 고유 case는 **1690 PASS / 2 SKIP**의 coverage를 확보했다. 오류 없는 전체 3-part 재실행은 하지 않았으므로 **PARTIAL**로 보고한다. 최초8개 실패를 삭제하거나 처음부터 전체 PASS였다고 보고하지 않는다.|
|P05 소형 lifecycle|19 PASS, 0 FAIL/SKIP; 새 DB·backup·TLS 종료·새 epoch/인가·오류 경계. 원 P03 복구 증거가 아니다.|
|기타 실제 독립 HTTP/authority|원 independent HTTP2 PASS, 새 distinct-principal TLS1 PASS, 새 delta1 PASS, 기존 final-authority2 PASS. 신규 고유56개와 중복 합산하지 않는다.|
|정적·빌드|Ruff, compileall, 변경 Python format, Flutter analyze, 변경 Dart format, npm build, debug APK build 모두 exit0. APK 설치·배포 없음.|

전체 Flutter 최초 환경 오류8개는 제품 source를 수정해 없앤 결과가 아니다. raw log와 최소 native 준비 probe를 함께 보존했다. `execution-manifest.json`은 최초 전체 실패와 focused 재실행, 신규5개 실제 정확성 실패를 별개로 기록한다. frozen archive와 고정 Git blob의 141개 변경·신규 파일을 별도 작은 사본에서 `git diff --no-index --check`로 검사해 whitespace 진단이 없었다. no-index의 정상 차이 exit1을 처음 오류로 해석한 도구 판정은 literal clean/오류 control(0/1/3)로 바로잡았고 최초 raw 결과도 보존했다. 이 과정에서 source를 수정하지 않았다. 작은 diff/control 임시 사본은 자동 정리했으며 큰 scratch 회수량과 별도로 기록한다.

정확한 command/cwd/환경·fixture·candidate digest·expected/observed·raw 결과는 [execution-manifest.json](benchmarks/t66f-b03-ir03/execution-manifest.json)에 연결한다. 새 독립 test 수에는 구현 측 회귀, 역사 defect-existence control, 같은 case 재실행, child 보조 probe를 더하지 않는다. 원 assertion을 SKIP/XFAIL하거나 기대값을 관측값으로 바꾸지 않았다.

기본 sandbox는 `bwrap: loopback: Failed RTM_NEWADDR`로 shell 시작 전에 실패했다. 승인 검토 경로에서 격리 workspace 명령을 실행했다. plain Dart의 native asset 매핑 누락은 별도 실행 환경 문제다. 초기 진단의 bundled-library preload는 symbol 오류/exit139, 구 VM flag는 unsupported였고 raw log를 남겼다. canonical source를 고치지 않고 공식 `dart run --packages=...` 경로에서 N01을 교차 재현했다. 이 실패한 환경 probe를 B03 제품 결함으로 집계하지 않았다.

## 10. perturbation과 미완료 의무

새 Python 동일 process의 3 warmup + 20 alternating pairs에서 small primitive OFF/ON 중앙값은 5.171/8.326ms, SQL은 0.114/2.489ms였다. medium primitive는 159.979/194.931ms, SQL은 1.317/17.197ms였다. raw CPU/RSS/초기화/종료와 p95는 `overhead-independent-python-complete.json`에 있다. 동시 전체 회귀가 있는 HOST 표본이며 임의 허용 threshold나 전체100k 시간 증가로 환산하지 않는다. RSS 차분은 heap allocation이 아니다.

새 Dart 동일 조건의 20쌍에서 small primitive OFF/ON 중앙값은 2.233/2.751ms, SQL은 0.460/2.338ms였다. medium primitive는 534.840/537.682ms, SQL은 1.656/5.427ms였다. `overhead-independent-flutter-complete.json`에 각 sample·process CPU tick·RSS·초기화·close가 있다. 표본 순서·VM/cache·다른 검증의 host load를 통제한 기기 성능 실험으로 주장하지 않는다. 소형 SQL의 계측 부담이 관찰됐으며 전체 규모 runtime perturbation은 여전히 미확정이다.

역사 P03은 **FAILED — 397,146 / 400,532**, 세 관측 모두 만료, 남은 3,386개, E3/E4 미도달이다. 원 client/backend SQLite는 현재 unavailable이며 이 감사에서 복구하거나 대체하지 않았다. P05의 소형 artifact PASS와 이번19개 회귀로 그 실패를 지우지 않는다. 추가 timing observer의 단독 원인도 입증하지 않았다. 새 N=100k cold 실행은 **0회**다.

전체 규모 measurement feasibility, 고정 H/D의 다섯 N 비용, E3 I25 large-N scaling은 미검증이다. Android memory/VFS/I/O·hardware power loss·R1 large restore는 미검증/별도 의무이고 activation gate는 닫혀 있다. B01/B02는 새 제품 반례가 없어 CLOSED다. Phase B는 INCONCLUSIVE이고 segmented production activation은 승인되지 않았다.

## 11. 원본 보존·artifact hygiene

시험 종료 후 819개 selected source의 SHA/길이/전체 POSIX mode와 나머지 baseline 파일2,010개의 Git blob·실행 mode가 모두 동일했다. authoritative frozen 파일의 SHA·0444 mode·link count와 directory0555도 일치했다. [final-candidate-integrity.json](benchmarks/t66f-b03-ir03/final-candidate-integrity.json)에 차이0을 기록했다.

모든 감사 runner와 실제 test/build child 종료 뒤 task root의 열린 FD/cwd 참조를 검사했다. 시스템의 기존 `(sd-pam)`/`sshd` 두 process FD는 권한상 읽을 수 없어 시스템 전체 FD 사용0이라고 주장하지 않는다. 감사 process 종료와 새 private root 소유권, 읽기 가능한 process의 참조0을 근거로 정리했다. 기존 evidence·cache·frozen archive·production은 제거하지 않았다.

[cleanup-manifest.json](benchmarks/t66f-b03-ir03/cleanup-manifest.json)의 세 owned directory만 제거했다. candidate4791개·historical2768개·Flutter scratch3개 파일의 할당량 합은 **4,490,203,136B(약4.18GiB)**이며 관측 가용량 증가는4,498,108,416B다. directory metadata·동시 host 쓰기로 수치가 다를 수 있다. `.venv`/`node_modules` symlink의 외부 대상은 삭제하지 않았다. debug build의 중간물/APK도 task-owned 복제본과 함께 정리했고 원 SDK/공용 cache는 보존했다.

독립 재현 source·counter/fixture oracle·전체 raw log의 압축본·원시 JUnit·findings·무결성·명령/환경 manifest를 새 IR03 evidence에 보존한다. 유일한 새 소형 P05 DB와 의도적 실패 fixture는 **`/tmp/money-note-ir03-20261023/p05-scratch`**에 그대로 남긴다. 이는 새 소형 회귀 자료이며 원 P03 artifact가 아니다. 재부팅에 영구적인 보관을 보장하지 않는다. 원본 사전 파일3,607개와 Git index의 최종 SHA/mode 대조는 `final-preservation.json`에 기록한다. report/evidence 외 제품·계측·기존 test/protocol/SHA expectation 변경은 없다.

## 12. 최종 판정과 다음 행동

**FAIL — B03 INSTRUMENTATION CORRECTION REQUIRED.** 후보 무결성과 독립성은 성립하지만 N01/N02가 재현돼 B03 정확성을 폐쇄할 수 없다. 일부 필수 회귀의 환경상 불완전성은 별도로 공개하며, 입증된 결함을 INCONCLUSIVE로 바꾸지 않는다. 새 Critical/High 금융·authorization 결함을 주장하지 않는다.

**별도 구현 세션에서 N01의 schema observer와 N02의 최초 설치 준비 경계만 교정한 뒤, 새 source identity로 동결하여 같은 독립 재현을 다시 검증한다.** 이번 감사에서는 교정·최적화·배포·R1·commit·push를 수행하지 않았다.

```text
T6.6F-B03-IR03 INDEPENDENT CORRECTNESS RE-AUDIT:
FAIL

AUDITOR INDEPENDENCE:
SATISFIED — 이 세션의 사전 구현·교정·후보 준비 참여 없음

FROZEN ARCHIVE SHA-256:
87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01

ARCHIVE INTEGRITY:
PASS

FROZEN PAYLOAD SHA-256:
645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8

CANDIDATE RECONSTRUCTION:
PASS

CANDIDATE FILE INVENTORY:
819

ORIGINAL GIT INDEX:
PRESERVED

ORIGINAL UNCOMMITTED WORK:
PRESERVED

BINDING PROTOCOL:
UNCHANGED

IA01:
PASS

IA02:
PASS

IA03:
PASS

IA04:
FAIL — 원 중첩 재현은 교정됐지만 N02가 새로 발생

IA05:
PASS

IA06:
PASS

IA07:
PASS

NEW FINDINGS:
2 — B03-IR03-N01 MEDIUM / B03-IR03-N02 LOW

HASH INPUT BYTE ORACLES:
PASS — 설치 완료 scope의 실제 입력 경계

VALIDATION INPUT SPAN ORACLES:
FAIL — N02

LOGICAL SQL WRITE BYTE ORACLES:
FAIL — N01

ATTEMPTED/EFFECTIVE/COMMITTED:
FAIL — 스키마 변경 뒤 세 분류 모두 누락

TRANSACTION/SAVEPOINT ACCOUNTING:
PASS — 독립 정산 사례 범위

STAGE ATTRIBUTION:
FAIL — N02에서 두 번째 scope의 event 소실

BACKEND CONCURRENCY/TLS:
PASS — 설치 완료 session의 실제 요청 격리

FLUTTER ASYNC/NATIVE LIFETIMES:
PASS — 검증한 Zone·closed scope·native worker 경계

PREPARED STATEMENT CACHE:
PASS — managed handle·bind·데이터 의미; observer의 N01은 별도 FAIL

FINITE RESOURCE BOUNDS:
PASS — 명시한 개수 상한·거부·해제 범위

ACTUAL D3→HTTP→E2→E1:
PASS

E3 PUBLICATION:
PASS

E4 ACCEPTED READ:
PASS

DISABLED/ENABLED PRODUCT EQUIVALENCE:
PASS — 소형 cold·무변경·카드·현금·손상 객체 및 authority 사례

P0 RECOVERY LINEAGE:
PASS

SOURCE-SHA GUARDS:
PASS — 기존23·현재6 및 역사 Git bytes 대조

FRESH INDEPENDENT TESTS:
51 PASS
5 FAIL
0 SKIP

FULL BACKEND REGRESSION:
PASS — 1436 tests / 1540 subtests; 역사 control4개 구분

FULL FLUTTER REGRESSION:
PARTIAL — 최초 1682 PASS / 8 FAIL / 2 SKIP; 환경 준비 후 8개 재검증 PASS

HISTORICAL P03 N=100K COLD:
FAILED — 397146 / 400532

NEW N=100K FULL COLD RUNS:
0

FULL-SCALE MEASUREMENT FEASIBILITY:
NOT VERIFIED

INSTRUMENTATION RUNTIME PERTURBATION:
PARTIALLY CHARACTERIZED — 소형·중형 HOST 비교만 수행

PHASE B FIVE-POINT COST GRID:
NOT VERIFIED

E3 I25 LARGE-N SCALING:
NOT VERIFIED

B01:
CLOSED

B02:
CLOSED

B03 INDEPENDENT CORRECTNESS:
FAIL

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY SAFETY:
NOT VERIFIED

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION SEGMENTED ACTIVATION:
NOT AUTHORIZED

TEMPORARY AUDIT ARTIFACTS:
감사 소유 복원·build·cache 약 4.49GB 제거; 재현·원자료와 새 소형 P05 DB 보존

PRE-EXISTING EVIDENCE:
PRESERVED

FROZEN SNAPSHOT:
UNCHANGED

PRODUCT SOURCE CHANGES:
NONE

GIT INDEX CHANGES:
NONE

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
FAIL — B03 CORRECTION REQUIRED

NEXT ACTION:
별도 구현 세션에서 N01·N02의 진단 경계를 교정하고 새 후보를 동결해 같은 독립 재현을 다시 실행한다.
```

