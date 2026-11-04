# T6.6F-B03-IR04 독립 최종 재감사

**FAIL — B03 계측 교정 필요.** IC02 후보를 정확히 동결·재구성했으며 원 IR03 N01/N02는 독립 재현에서 통과했다. 그러나 이전 설치 종료와 다음 설치 시작이 겹치면 실제 parser 1회를 2회로 계수하는 잔존 결함 **B03-IR04-N01 · LOW**를 확인했다. IA04와 B03 정확성은 OPEN이다. XML 분실이나 index metadata 사고를 이 FAIL의 원인으로 대체하지 않는다.

## 1. 감사자 독립성

**LIMITED.** 이 대화의 작업자는 이전 IR03 독립 감사를 수행했다. 요청의 “새 세션” 조건은 충족하지 않는다. B03 구현, IC01 교정, P01–P05 구현·교정, IC02 N01/N02 구현 및 감사 대상 source 수정에는 참여하지 않았다. 구현 비관여와 새 세션 여부를 구별한다. 이번에도 기존 bytes의 동결과 독립 시험만 수행했고 자기 수정·자기 인증은 하지 않았다. 이 제한을 숨긴 완전 독립 PASS는 주장하지 않는다. 재현된 결함에 대한 FAIL은 별도 수치·source·native oracle로 입증했다.

## 2. 실제 저장소 상태

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. staged 변경은 없고 2,693개의 stage-0 path/mode/blob entry가 HEAD tree와 동일하다. tracked unstaged 변경은 `AGENTS.md`, B02 benchmark server, B03 counter/server, Dart diagnostic SQL wrapper의 5개였다. required untracked candidate source는 142개다. 기존 source·보고서·증거 4,038개의 bytes/mode를 시작과 끝에 대조했다. [초기 상태](../../benchmarks/t66f-b03-ir04/starting-state.json.gz), [최종 후보 대조](../../benchmarks/t66f-b03-ir04/final-candidate-integrity.json), [보존 대조](../../benchmarks/t66f-b03-ir04/final-preservation.json)를 참조한다. `GIT_OPTIONAL_LOCKS=0`으로 읽었고 stage/reset/stash/checkout/commit/push를 하지 않았다.

## 3. 역사 IR03 FAIL 보존

IR02의 819개·9,085,052B·payload `645fd4d8…`와 archive `87b1e689…`, 원 IA 판정 및 IR03 N01/N02 source·raw evidence는 그대로 보존했다. 원 IR03 FAIL을 현재 결과로 다시 쓰지 않았다. 현재 후보에서의 원 반례 통과는 새 증거이며 과거 오계수를 없던 일로 만들지 않는다. 이전 동결본의 6개 파일도 IR03에 기록된 SHA와 모두 일치한다.

## 4. IC02 후보 provenance

IC02 manifest는 원 IR02 payload의 두 진단 파일만 교체하고 검증 source 6개를 추가한다. `backend/app`, `backend/isolated_sync`, `mobile/lib`의 추가 교정은 없다. live inventory와 각 bytes·SHA·mode를 먼저 대조한 뒤 그 기존 source를 동결했다. [교정 후보 manifest](../../benchmarks/t66f-b03-ir04/corrected-candidate-manifest.json)와 [검증 기록](../../benchmarks/t66f-b03-ir04/candidate-verification.json)이 근거다. 구현 측 PASS는 독립 기대값으로 사용하지 않았다.

## 5. P02 XML 사고 판정

분실 경로는 `docs/benchmarks/t66f-b03-ic01-p02/evidence/backend-full.xml`이다. 당시 full pytest의 **생성 JUnit 보고서**였고 Git에서 untracked·not ignored이며 해당 path의 reachable history가 없다. 원 SHA는 `bd2b7e4d306707df1ab10f6c76535b96b1a47cd33158748416215561e203c8b8`, 원 크기는 221,431B다. 현재 overwritten XML은 다른 SHA이며 원본이라고 부르지 않는다.

P02/IC02/IR03/IR02 및 기존 관련 scratch의 한정된 1,810개 후보 파일·압축 XML, IR02 archive와 기존 Git object metadata 7,608개를 확인했다. Git에도 원 크기의 blob 후보가 없었고 exact bytes는 **UNAVAILABLE**다. filesystem 전체 복구나 Git 내부 수정은 하지 않았다.

판정은 **EVIDENTIARY SUBSTITUTE AVAILABLE**이다. 원 실행 JSON·압축 로그·summary와 assertion source가 남아 있다. 당시 로그의 1,436 tests/1,540 subtests, exit0을 확인했고 P02 collector가 XML을 참조한 역할도 기록했다. 이 XML은 현재 B03 필수 주장 어느 것의 유일한 근거도 아니다. prepared-cache·SQL·scope·actual D→E는 새 독립 시험으로 검증할 수 있었고 실제 실행했다. exact 역사 XML의 손실은 남지만 현재 correctness를 자동 INCONCLUSIVE로 만들 물질적 공백은 없다. [사고 판정](../../benchmarks/t66f-b03-ir04/xml-incident-adjudication.json), [검색](../../benchmarks/t66f-b03-ir04/xml-forensics.json), [Git object 검색](../../benchmarks/t66f-b03-ir04/xml-git-object-search.json)을 보존했다. 새 XML을 옛 XML로 재명명·재생성하지 않았다.

## 6. Git index 사고 판정

**INDEX BYTE IDENTITY CHANGED — STAGED CONTENT PRESERVED.** 역사 IR03의 물리 index SHA는 `d798903b…`, IR04 시작과 끝은 `33779f92…`다. IC02가 보고한 stat-cache 사고를 byte-identical 보존이라고 표현하지 않는다. 원 index 사본이 없으므로 바뀐 모든 offset을 stat 필드로 직접 역산했다고도 주장하지 않는다.

현재 전체 `ls-files --stage`의 SHA는 `8df943cd1934be9aaa6f1f5b9a0dcc1a796e255019c8936e52c50ab414d535b8`로 역사 IC02 기록과 같고, 모든 path/mode/blob/stage를 고정 HEAD tree `af2aa70ce6a8cd27c18c134564e31702f0f54f8c`와 직접 비교했다. 역사 IR03 상태도 staged 변경이 없었다. staged 내용 손실의 증거는 없다. IR04 중 물리 index bytes도 추가로 바뀌지 않았다. index 복원·재작성은 하지 않았다. [논리 내용 대조](../../benchmarks/t66f-b03-ir04/index-adjudication.json).

## 7. 정확한 source digest

확인한 payload는 **825개 / 9,129,332B**이며 digest는 `27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3`다. entries를 path 순서로 두고 `json.dumps(ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()`의 SHA-256을 재계산했다. archive bytes의 SHA와 혼동하지 않는다. tracked deletion은 0이고 현재 staged 내용은 committed baseline과 같다. 허용 목록에 없는 source 차이는 0이다.

## 8. 새 후보 동결

새 경로는 `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3/`다. archive SHA-256은 **`4655111c579503ef2c0969f82b5dca4830c06ac1123002cd6e8887109728b012`**다. 원 IR02 경로를 덮어쓰지 않았다. 별도 staging directory에서 source-only tar와 canonical manifest·base/deletion/mode/staged/untracked metadata·HANDOFF를 작성·검증한 뒤 rename으로 확정했다. SQLite·build cache·APK·실험 DB·비밀 설정은 포함하지 않았다. 5개 sidecar/archive는 mode0444, directory는0555다. owner/root에 대한 hardware WORM은 아니며 고정 SHA로 변조를 판별한다. [동결·재구성 증거](../../benchmarks/t66f-b03-ir04/freeze-reconstruction.json).

## 9. 독립 재구성

`git archive`의 고정 baseline에 새 frozen archive의 `source/`만 overlay했다. 실행 package root는 `/tmp/money-note-ir04-20261024/candidate`였다. 선택된 825개 bytes/mode와 나머지 baseline 2,010개의 Git blob·실행 비트를 시험 전후 확인했다. 현재 mutable source를 실행 대상으로 가져오지 않았다. 기존 Python runtime·node_modules 의존성만 별도로 사용했고 Flutter package config는 frozen pubspec/lock에서 offline 생성했다. 원 reproducer의 절대 import/output/root 경로만 바꾼 adapter는 source hash와 함께 보존했다. source나 숫자 assertion을 교정하지 않았다.

## 10. source-lock 무결성

현재 exact lock 6개가 모두 일치하고, 승인된 exact replacement를 역으로 적용한 역사 5개는 `da818648031e013e83dd6a680b1b1bde0fb6e0a1`의 실제 Git bytes와 동일하다. 현재 guard6 및 기존 adapter/source guard23도 fresh PASS다. 기대 SHA나 protocol/P0 함수를 바꾸지 않았다. [독립 대조](../../benchmarks/t66f-b03-ir04/source-lock-independent.json), [기존 guard 실행](../../benchmarks/t66f-b03-ir04/flutter-existing-source-guards.json).

## 11. N01 Python 독립 검증

원 IR03 ALTER와 DROP/recreate 반례를 경로만 바꿔 그대로 실행했다. 누적 committed는 각각 6B·4B로 native/literal oracle와 일치한다. 새 독립 schema 6개는 INSERT·UPDATE·DELETE·UPSERT, 새 table, DDL commit/rollback/savepoint, 동일 SQL의 native reprepare와 외부 schema 거부를 확인했다. BLOB/TEXT는 literal ledger로, 최종 rows/schema는 unwrapped SQLite로 OFF/ON 대조했다. [원 oracle](../../benchmarks/t66f-b03-ir04/tests/test_ir03_oracles.py), [새 oracle](../../benchmarks/t66f-b03-ir04/tests/test_ir04_schema.py), [결과](../../benchmarks/t66f-b03-ir04/schema-independent.xml).

## 12. N01 Dart 독립 검증

원 IR03 17개 assertion이 모두 PASS이며 두 DDL 원 반례도 포함한다. 새 독립 6개 schema case는 Python과 별도로 작성한 literal ledger와 native SQLite 상태를 사용한다. 같은 managed SQL의 `1 + (3+2 DEFAULT) + 2 = 8B`, cache hit2와 최종 finalization도 일치했다. [새 source](../../benchmarks/t66f-b03-ir04/tests/ir04_schema_test.dart), [최종 결과](../../benchmarks/t66f-b03-ir04/dart-schema-independent-final.json).

초기 새 감사 helper가 attempted/effective의 key 순서를 committed와 같게 조회해 6개가 실패했다. 원 v1 source와 raw 실패를 보존하고 **조회 key만 수정**했다. 6/3/7/8 등의 literal 기대값·실행 SQL·제품 구현은 바꾸지 않았다. [도구 수정 기록](../../benchmarks/t66f-b03-ir04/schema-tooling-correction.json)은 이 실패를 제품 결함 또는 최종 독립 실패 수에 넣지 않는 근거다.

## 13. N01 외부 DDL 제한

**ACCEPTABLE — 이번 승인된 지원 경계에 한정.** 관측 연결 밖의 ALTER 또는 DROP/recreate 뒤 DML을 반복하면 양 언어 모두 `external schema change; measurement incomplete`와 coverage flag를 남기고 새로운 write 전에 거부했다. 이전 committed 1B는 남고 후속 attempted/effective/committed payload는 늘지 않았다. 외부 연결의 최종 rows도 거부 전과 같다. 이를 외부 migration의 성공 측정·0B 성공 또는 일반 OFF/ON 동등성 PASS로 표현하지 않는다.

이 제한은 IC02 보고서·source에 명시돼 있다. 해당 wrapper는 명시적 test-only diagnostic이며 필수 대표 D→E는 같은 schema-owner 연결에서 schema를 준비하고 외부 concurrent DDL 성공을 요구하지 않는다. SQLite snapshot/metadata bypass를 써서 native 실패를 성공으로 바꾸지 않는다. §35 실제 측정 요구를 unsupported 표본까지 완결 수치로 보고할 허가로 바꾸지 않는다. 그런 workload는 불완전 측정으로 제외해야 한다. 이번 실제 경로에서는 이 오류가 발생하지 않았다. [Python 증거](../../benchmarks/t66f-b03-ir04/schema-external-False.json), [Dart 증거](../../benchmarks/t66f-b03-ir04/dart-schema-external-false.json).

## 14. N02 원 race와 강한 최초 설치 재현

원 IR03 `ExitStack.enter_context` schedule를 기대값 수정 없이 재실행해 PASS했다. 해당 seam이 현재 readiness 뒤에 있다는 점을 감안해 별도 독립 oracle는 실제 `_parse_json` patch 직전에 최초 caller를 멈췄다. 총 2개/4개 scope가 준비 완료 전 본문을 실행하지 못했고, 재개 뒤 각자 다른 UTF8 payload를 정확히 1회 계수했다. 부분 설치 실패 후 waiter 오류·원 primitive 복구·registry 해제·다음 설치 성공도 PASS다. [최초 설치 결과](../../benchmarks/t66f-b03-ir04/installation-adjacent.xml), [scope4 증거](../../benchmarks/t66f-b03-ir04/first-install-4.json).

## 15. N02 정확한 parse·byte attribution

원 두 번째 scope의 실제 `{}` 입력은 parse1회·validation2B다. 현재 원 N02에서는 1/2가 정확히 두 번째 observation scope에 귀속되고 임의 `+2` 보정이 없다. nested 원 사례는3회/6B다. 하지만 **다른 수명 순서**인 이전 세대 close→다음 세대 활성화에서는 1/2가2/4가 된다. N02 원 반례의 closure와 전체 설치 수명 안전성을 구별한다.

## 16. IA04 독립 closure

**FAIL.** 원 nested와 원 N02가 모두 통과해도 신규 IR04-N01은 같은 installation 경계의 중복 계수다. 따라서 IA04 전체 수용 조건은 충족하지 않는다. parent IR02 exact counter도 같은 trace oracle에서 실패하므로 이를 IC02가 새로 도입한 regression이라고 단정하지 않는다. 새로 발견한 잔존 인접 결함이다. 과거 IA04/IR03 판정은 수정하지 않았다.

## 17. IA01–IA07 행렬

|ID·원 등급|현재 독립 관측|판정|
|---|---|---|
|IA01 · MEDIUM|같은 이름·quoted savepoint의 native committed1/rollback2B 일치|PASS|
|IA02 · MEDIUM|부분 OR FAIL native3B 보존; ABORT/ROLLBACK/IGNORE 구별|PASS|
|IA03 · MEDIUM|첫 comment/line comment/선행 semicolon DML의2B 계수|PASS|
|IA04 · LOW|원 nested3/6 및 N02 1/2는 통과; 세대 교대2/4 반례|FAIL|
|IA05 · MEDIUM|원 closed-lease dispatch에서 pending0/closed true/completion1, native state0|PASS|
|IA06 · LOW|owner32까지 수용,33번째 실행 전 명시 거부, rollback 후 weakref0|PASS|
|IA07 · MEDIUM|원 single-delegation cursor의176/185행 oracle SELECT가 setup, generation0|PASS|

원 backend 결함존재4개와 Dart3개는 정확한 역사 wrapper에서 원 assertion을 유지해 별도 실행했다. 그 PASS를 현재 정확성 PASS로 합산하지 않는다. IA05–07 직접 코드도 원문으로 실행했다. IA06 원 무제한 반복은33번째 guard로 exit1이 되며, 이 명시 거부를 오계수 실패로 분류하지 않는다. 별도 native/weakref oracle가 실행 전 거부와 해제를 확인했다. [직접 결과](../../benchmarks/t66f-b03-ir04/original-direct-current.json), [IA07](../../benchmarks/t66f-b03-ir04/ia07-independent-assertion.json).

## 18. hash input-byte oracle

literal domain+NUL+UTF8 preimage, 실제 native SHA constructor/update witness, Unicode·빈 입력·65,537B·반복·chunk/copy·실패 update·닫힌 scope를 대조했다. 실제 D3 HTTP의 SHA는 하위 native 입력 관측과 일치한다. response 크기를 hash oracle로 사용하지 않았다. Dart도 독립 crypto preimage와 actual canonical bytes를 비교했다. product hashing을 진단 목적으로 한 번 더 실행하지 않았으며 opaque TLS/PBKDF2 내부 비용을 application SHA total로 확장하지 않는다. 검증 범위는 PASS다.

## 19. validation span oracle

primary JSON/C1의 실제 submitted buffer 길이와 성공/실패 span을 대조했다. Unicode, 중복 key, invalid UTF8/surrogate, noncanonical/early failure, 반복·nested·concurrent scope를 포함한다. backend JSON parse 완료와 Dart 전체 C1 완료는 서로 다른 완료 의미다. 원 N02는 닫혔지만 세대 교대에서 실제1회가2회로 중복되어 전체 **FAIL**이다.

## 20. SQL logical write-byte oracle

지표는 실제 NEW TEXT UTF8/BLOB payload다. UPDATE는 NEW row 전체, DELETE 신규 payload는0이며 row operation은 따로 센다. selector/bind 문자 수·DB/WAL 크기·SQLite page write를 대용하지 않았다. 원 SQL defects, Unicode/UPSERT/IGNORE/trigger/cascade/부분 batch·실패 및 schema 재설치가 독립 oracle와 일치한다. 지원 범위 SQL 계수는 PASS다.

## 21. attempted/effective/committed

새 양 언어 ledger에서 `p INSERT`의 attempted/effective는6B/3B, UPDATE는7B/7B다. INSERT conflict의 시도와 실제 UPDATE를 구별해 같은 underlying input을 임의로 하나의 총량으로 합치지 않는다. commit 때는 p INSERT3B·UPDATE7B·q INSERT5B가 committed다. rollback 때는 초기 p INSERT1B만 committed이고 p INSERT2B·UPDATE7B·q INSERT5B가 rollback이다. savepoint 복귀 뒤6B INSERT를 추가하면 p INSERT committed7B다. TEXT의 한글3B·emoji4B도 별도 exact 대조했다. 모든 분류가 native 결과와 일치한다.

## 22. transaction/savepoint

명시 transaction, nearest same-name savepoint, RELEASE/ROLLBACK TO, outer rollback, OR FAIL 성공 prefix, 실패 COMMIT 뒤 rollback, iterator 예외 전 batch 성공, collector close 뒤 settlement를 검증했다. DDL rollback 이후 원 schema로 observer가 복귀하고 prepared reprepare 때문에 중복 row event가 생기지 않는다. 원 schema DEFAULT로 합성된 과거 row를 새 INSERT 비용으로 발명하지 않는다. PASS다.

## 23. stage attribution와 overlap

generation/oracle SQL 분리는 원 실제 cursor로 PASS다. 실제 E2→E1과 E3 verify/prepare/commit, E4 read, P0의 호출자 stage도 유지된다. hash·validation·write·HTTP 또는 inclusive readback duration을 겹침 없는 하나의 total로 합치지 않는다. 다만 신규 설치 교대에서 같은 transfer scope의 실제 event가 두 번 표현되어 전체 무중복 accounting은 **FAIL**이다. 타 scope로 이동한 사건으로 잘못 설명하지 않는다.

## 24. backend concurrency/TLS

원 독립 distinct-principal TLS와 valid/invalid credential의 실제 동시 요청, native SHA/parser witness, 실패 요청 후 closure·이전 snapshot 고정을 fresh 실행했다. 원 시작한 native worker의 취소·late exception도 재실행했다. 이미 설치된 세션의 요청 격리는 PASS다. 이 결과가 세션 자체의 동시 installation/teardown 결함을 면제하지 않는다.

## 25. Flutter async/native 수명

concurrent Future, async context propagation, nested stage, close 후 callback·예외, native dispatch 거부·실제 시작 후 requester 취소와 worker 종료를 구별했다. pending/hold가 균형을 이루고 닫힌 collector는 새 event를 받지 않는다. 새 run으로 late event가 넘어가지 않는다. 원 independent 및 IC01의 직접 영향 assertion이 통과했다. Android isolate·실기기 메모리 전체를 증명한 것은 아니다.

## 26. prepared-statement cache

연결별 managed handle capacity32, reset/rebind·BLOB/NULL, 별도 연결 소유권, eviction/finalization, 예외 cleanup·BUSY·use-after-close를 원 독립 및 P02 회귀로 검사했다. 독립80개 SQL에서 peak32/eviction48이고 같은 SQL이 ALTER/DROP 후 재준비되어 ledger8B와 native data가 일치했다. caller가 직접 소유한 모든 prepare까지 전역32라고 주장하지 않는다. 경과 시간만으로 정확성을 판정하지 않았다. PASS다.

## 27. 유한 진단 state

source와 실제 경계 시험으로 table128, savepoint32, transaction-owner32, managed cache32, 고정 설치 종류3, request sample16을 확인했다. capacity 오류가 새 write 전에 발생하고 transaction/connection 종료 후 owner/frame/cache가 정리된다. scalar schema cookie와 readiness Event는 연결/설치 수명에 속한다. 이는 native bytecode·RSS의 절대 byte 상한이나 임의 사용자 미종료 scope의 시간 상한을 증명한 것이 아니다. 신규 반례에서도 registry는 비고 parser가 복구되므로 영구 leak를 추가 finding으로 만들지 않았다.

## 28. 실제 D3→HTTP→E2→E1

실제 인증 TLS 통합 **6개 PASS**, 약359초다. 새 delta fixture는 history3/current1, cold144 objects/89,644 canonical B다. 각 object의 독립 domain/NUL SHA, backend raw11 tables·hot projection, native durable BLOB와 FK 상태를 OFF/ON 비교했다. fixture/oracle 전체는 [delta 원자료](../../benchmarks/t66f-b03-ir04/tests/delta-integration.json.gz), [요약](../../benchmarks/t66f-b03-ir04/delta-integration-summary.json)에 있다. 소형·중형 지원 회귀 최대 history260을 사용했으며 새100k cold는 없다.

|실제 단계|accepted sequence|누적 committed object BLOB|
|---|---:|---:|
|cold|1|89,644B|
|무변경|1|89,644B|
|card 한 건 delta|2|104,672B|
|cash 한 건 delta|3|118,657B|
|손상 객체 거부|3 유지|양 모드 동일 OBJECT_HASH_INVALID, 이전 accepted 보존|

## 29. E3 publication과 E4 accepted read

실제 E3/E4에서 accepted sequence/root와 durable state가 일치했다. 최종 authority 취소·stale-user guard 회귀도 통과했다. source의 `store_publication.dart:439` final guard 바로 다음440에서 동기 COMMIT을 호출하며 사이에 await/hook이 없다. 진단 wrapper도 동기이고 새 authorization을 만들지 않는다. E4는 accepted provenance로 읽고 Frozen/file 경계10개가 healthy read·reopen/fresh process·pending 보존을 확인했다.

## 30. disabled/enabled 제품 동등성

지원 경로에서 canonical bytes·금융 raw strings·sync_root/sequence·native rows·error outcome이 OFF/ON 동일하다. Snapshot v7, OfflineBaseline v4, frozen B/J input-only, AppState ticket/authority, sync_root와 v7 fingerprint 분리는 source-lock·관련 회귀·실제 통합으로 보존됐다. 모바일 금융 공식을 독립 재계산하지 않았다. 외부 concurrent DDL은 앞서 명시한 unsupported measurement이며 그 예외를 일반 동등성 성공으로 숨기지 않는다.

## 31. P0 recovery lineage

P0 source의 현재 exact SHA와 역사 함수 inverse bytes가 일치한다. 원 독립 Unicode/control·metadata/ordering goldens, disabled/enabled 및 실제 Frozen/reopen 경로와 lineage4개 회귀가 PASS다. lineage hash preimage는 HTTP/file 크기와 동일하다고 가정하지 않는다. fingerprint와 sync_root를 혼동하지 않았다.

## 32. fresh 독립·회귀·정적 결과

|fresh 범위|결과와 집계 원칙|
|---|---|
|IR04 신규 독립18개|15 PASS / 3 FAIL / 0 SKIP; 실패3개 모두 IR04-N01의 seam 재현1개와 무수정 trace2개|
|원 IR03 독립56개 재검증|Python38, Dart17, delta1 모두 PASS|
|최초 독립 감사 현재 oracle|backend14, Dart11, 실제 HTTP2 모두 PASS|
|독립 고유 test identity 합계|**98 PASS / 3 FAIL / 0 SKIP**; 동일 재실행·역사 control·도구 오류·구현 회귀 제외|
|backend 영향 회귀|104 PASS; 현재100 + 역사 결함존재4. 원 assertion 변경 없음|
|Flutter 영향 coverage|주요88·보완 boundaries10·원 현재11·역사3·실제 HTTP6·새 schema6·기존 guard23 PASS. 독립/구현/역사를 별도 집계|
|정적·build|Ruff check/format, compileall, Dart format, Flutter analyze, npm build 모두 exit0|

최초 Flutter 명령의 단수 `boundary_test.dart` 오기로 loader1 FAIL·done=false를 남겼다. 실제 기존 `boundaries_test.dart`10개를 별도 실행해 모두 PASS했고 최초 로그를 보존했다. 전체88개를 다시 반복하지 않았다. 새 Dart helper 오류와 이 loader 오류는 [검사 요약](../../benchmarks/t66f-b03-ir04/independent-test-results.json)에 별도 기록했다. 숫자 기대값을 관측 counter에 맞춰 낮춘 사실은 없다. 모든 실제 invocation/cwd/환경/source identity·raw 출력은 [실행 manifest](../../benchmarks/t66f-b03-ir04/execution-manifest.json)에 연결한다.

환경은 Python3.12.3/SQLite3.45.1, Flutter3.47.4/Dart3.13.3, Node22.22.3/npm12.0.1이다. 오케스트레이션 Python3.13.9는 분리 기록했다. 기본 sandbox의 bwrap 초기화 실패 뒤 승인 검토된 실행 경로를 사용했고 거절은 없었다. live/production 테스트 요청은 하지 않았다.

## 33. 역사 full-suite 증거와 재실행 결정

IC02 backend **1446 tests/1540 subtests PASS**, Flutter **1698 PASS/0 FAIL/2 SKIP**는 역사 구현 측 실행이다. four source SHA가 새 manifest와 일치함을 확인하고 원 압축 로그·XML·세 Flutter part의 `done.success=true`를 독립 재집계했다. backend XML은 testcase 노드1446개, subtest 포함 tests 속성2986이다. [재집계](../../benchmarks/t66f-b03-ir04/historical-ic02-suite-recount.json), [source 연결](../../benchmarks/t66f-b03-ir04/historical-ic02-suite-source-link.json).

IR04 full backend/Flutter는 **NOT RERUN**이다. 변경 범위가 두 test-only diagnostic 파일로 식별됐고 필요한 직접 영향·독립·실제 경로는 fresh 실행했다. 새 결함은 위 좁은 수명 경계에서 결정적으로 입증됐다. 동일 전체 suite의 수시간 반복으로 이 FAIL을 판별할 추가 근거는 필요하지 않다. 과거 full PASS를 새 full PASS로 표현하거나 구현 주장만으로 closure를 주지 않았다. 새 APK/Android build도 반복하지 않았다.

## 34. 신규 finding의 최소 재현과 교정 경계

**B03-IR04-N01 · LOW · B03 차단.** 위치는 `counters.py:318`, `:334`, `:343`이다. parse/encode delegate를 installation reference 획득 전에 잡는다. A가 설치 중일 때 B가 A의 observer를 캡처하고343 직전에 멈춘다. A가 종료·복구한 뒤 B가 새 최초 owner가 되면 이전 observer를 다시 감싼다.

|실제 native parser 입력|독립 expected|관측|
|---|---|---|
|`{}` 2B, native1회|reported1회/2B|2회/4B|
|`"한😀"` 9B, native1회|reported1회/9B|2회/18B|

[무수정 trace 재현](../../benchmarks/t66f-b03-ir04/tests/test_ir04_rollover_native.py)은 제품/진단 함수를 patch하지 않고343의 preemption만 강제한다. 실제 native parser의 code 진입과 raw buffer를 별도로 관찰해1회임을 확인했다. 파싱 결과는 정상이고 registry도 종료 뒤 비며 parser가 복구된다. encoding observer도 중복된다. [2B raw](../../benchmarks/t66f-b03-ir04/rollover-native-2.json), [9B raw](../../benchmarks/t66f-b03-ir04/rollover-native-9.json), [실패 XML](../../benchmarks/t66f-b03-ir04/rollover-native.xml)이 증거다. parent IR02 counter의 동일 두 실패는 별도 역사 control이며 IC02 발생 원인으로 오인하지 않는다.

최소 교정 경계는 **설치 reference 획득·delegate 캡처·이전 세대 teardown 소유권의 결합**이다. 전체 금융/SQLite 제품 구현, protocol, TTL, P02 최적화를 수정할 근거는 없다. 별도 구현 세션을 권고하며 이번에는 source를 고치지 않았다. 실제 장부·보안 오류나 다른 설치 종류의 미검증 결함까지 확대하지 않는다.

## 35. 역사 P03 full cold 실패

**FAILED — 397,146 / 400,532**, remaining3,386, 세 observation 모두 만료, E3/E4 미도달이라는 기록을 유지한다. 원 backend/client SQLite artifacts는 unavailable이다. 작은 새 통합 성공을 이 실패의 복구 또는 full-scale 성공으로 바꾸지 않는다. logical collector가 유일한 원인이었다고 단정하지 않는다. 새 full N=100k cold는0회다.

## 36. 유지하는 Phase B 의무

binding §35는 고정 H/D의 N1k/5k/10k/50k/100k와 no-change/card/cash 실제 비용·반복 통계를 요구한다. §36 I25는 steady-state의 숨은 full-N 작업을 금지한다. 이 문구는 모든 보조 observer를 켠100k cold를 B03-only 필수 보정으로 명시하지 않으므로 scoped correctness 검증과 양립하지만, five-point grid/I25를 면제하지 않는다. [요구 coverage](../../benchmarks/t66f-b03-ir04/requirement-coverage.json).

full-scale feasibility·runtime perturbation, Android memory/VFS·physical I/O·hardware power loss, R1 large restore는 미검증/보류다. 이번 추가 schema cookie read의 full-scale 영향도 미해결이다. 작은 wall time을 성능 중립이나 임의 threshold PASS로 쓰지 않는다. B01/B02는 CLOSED 유지, Phase B는 INCONCLUSIVE, R1 activation gate는 CLOSED, production은 NOT AUTHORIZED다.

## 37. 디스크·임시 산출물

시작 `/tmp` free는104,137,871,360B였고 별도 bounded audit root를 사용했다. 종료 후 source identity를 다시 확인하고 감사 소유 candidate·Flutter temp·pytest temp의4개 경로만 삭제했다. 회수한 파일 할당량은 **234,504,192B (약223.6MiB)**이며 관측 free delta는 235,769,856B다. 외부 `.venv`/node_modules symlink target이나 기존 scratch/cache를 따라 삭제하지 않았다.

이번 실행 child는 모두 완료됐다. 읽을 수 있는 동일 UID cwd/fd에서 삭제 대상의 활성 참조는 없었다. 일부 선행 Python/Uvicorn/systemd/Codex/sshd 등의 `/proc` 접근 제한은 [cleanup 기록](../../benchmarks/t66f-b03-ir04/cleanup.json)에 남기며 시스템 전체 가시성을 주장하지 않는다. 소형 독립 재현 source·raw output·도구는 저장소 증거와 `/tmp`에 남겼다. 새 동결본과 이전 동결본은 보존했다. `/tmp`가 재부팅 영속 증거라고 가정하지 않도록 compact 저장소 사본을 만들었다.

## 38. 최종 B03 판정

**FAIL — B03 INSTRUMENTATION CORRECTION REQUIRED.** 후보 identity·재구성, N01/N02 원 반례, SQL·hash·실제 경로·자원 관련 긍정 증거는 확보했다. 그러나 설치 세대 교대의 중복 event가 필수 validation span·무중복 scope accounting을 위반한다. IA04와 B03은 닫을 수 없다. 이 결과를 INCONCLUSIVE로 완화하거나 XML 사고를 correctness 실패의 대용으로 쓰지 않는다. 새 세션 조건의 독립성 제한도 별도로 남긴다. 제품 source·binding·index·역사 evidence를 IR04가 수정한 사실은 없다.

## 39. 다음 행동

별도 구현 세션에서 delegate 캡처와 설치 reference·teardown 소유권 경계만 교정하고 새 source identity로 보존된 세대 교대 재현을 재검증하세요. [최소 인계](../../benchmarks/t66f-b03-ir04/HANDOFF.md)에 정확한 재현과 correction boundary가 있다. full100k cold·전체 suite 반복·새 준비 감사가 이 결함 교정의 선행 조건은 아니다.

## 필수 최종 상태

```text
T6.6F-B03-IR04 INDEPENDENT FINAL RE-AUDIT:
FAIL

AUDITOR INDEPENDENCE:
LIMITED — 이전 IR03 감사와 같은 세션; 구현·교정 소스 수정에는 비관여

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

HISTORICAL IR02 ARCHIVE:
PRESERVED

HISTORICAL IR03 FAIL:
PRESERVED

IC02 CORRECTED SOURCE:
VERIFIED

EXPECTED IC02 CANDIDATE DIGEST:
27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3

ACTUAL CORRECTED CANDIDATE DIGEST:
27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3

NEW FROZEN CANDIDATE:
/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3/

NEW ARCHIVE SHA-256:
4655111c579503ef2c0969f82b5dca4830c06ac1123002cd6e8887109728b012

NEW CANDIDATE RECONSTRUCTION:
PASS

NEW SOURCE INVENTORY:
825 / 9129332 bytes

P02 XML INCIDENT:
EVIDENTIARY SUBSTITUTE

P02 XML EXACT ORIGINAL:
UNAVAILABLE

P02 XML EFFECT ON B03 CORRECTNESS:
MITIGATED BY INDEPENDENT TEST

GIT INDEX BYTE IDENTITY:
CHANGED — HISTORICAL STAT CACHE INCIDENT

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY IR04:
NO

EXISTING UNCOMMITTED SOURCE:
PRESERVED

N01 ORIGINAL INDEPENDENT REPRODUCER:
PASS

N01 PYTHON:
PASS

N01 DART:
PASS

N01 ATTEMPTED/EFFECTIVE/COMMITTED:
PASS

N01 EXTERNAL DDL LIMITATION:
ACCEPTABLE — 지원 범위 밖 측정을 실행 전 명시적으로 거부

N02 ORIGINAL INDEPENDENT REPRODUCER:
PASS

N02 CONCURRENT FIRST INSTALL:
PASS

N02 EXACT PARSE EVENTS:
PASS

N02 TWO-BYTE VALIDATION INPUT:
PASS

N02 PER-SCOPE ATTRIBUTION:
PASS

IA01:
PASS

IA02:
PASS

IA03:
PASS

IA04:
FAIL — 새 설치 세대 교대 결함

IA05:
PASS

IA06:
PASS

IA07:
PASS

NEW AUDIT FINDINGS:
1 / B03-IR04-N01 / LOW

HASH INPUT BYTE ORACLES:
PASS

VALIDATION INPUT SPAN ORACLES:
FAIL

SQL LOGICAL WRITE BYTE ORACLES:
PASS — 지원 범위

TRANSACTION/SAVEPOINT ACCOUNTING:
PASS

STAGE ATTRIBUTION:
FAIL — 설치 교대 scope의 실제 event 중복; 정상 stage 격리는 통과

BACKEND CONCURRENCY/TLS:
PASS — 이미 설치된 세션의 실제 요청 격리

FLUTTER ASYNC/NATIVE LIFETIMES:
PASS

PREPARED STATEMENT CACHE:
PASS

FINITE RESOURCE BOUNDS:
PASS — 문서화된 진단 state 개수 상한

REAL D3→HTTP→E2→E1:
PASS

E3 PUBLICATION:
PASS

E4 ACCEPTED READ:
PASS

DISABLED/ENABLED PRODUCT EQUIVALENCE:
PASS — 지원 경로의 관측 범위

P0 RECOVERY LINEAGE:
PASS

SOURCE-SHA GUARDS:
PASS

FRESH INDEPENDENT TESTS:
98 PASS / 3 FAIL / 0 SKIP — 최종 고유 test identity; IR04 신규는 15/3/0

FRESH BACKEND REGRESSION:
PASS — 영향 subset 104개; 전체는 새로 실행하지 않음

FRESH FLUTTER REGRESSION:
PASS — 필요한 영향 subset 보완 완료; 최초 loader 오류 별도 보존, 전체 새 실행 없음

HISTORICAL IC02 FULL BACKEND:
1446 TESTS / 1540 SUBTESTS PASS — 역사 구현 측 실행, raw 독립 재집계

HISTORICAL IC02 FULL FLUTTER:
1698 PASS / 0 FAIL / 2 SKIP — 역사 구현 측 실행, raw 독립 재집계

HISTORICAL P03 N=100K COLD:
FAILED — 397146 / 400532

NEW FULL N=100K COLD ATTEMPTS:
0

B03 INDEPENDENT INSTRUMENTATION CORRECTNESS:
OPEN — FAIL

FULL-SCALE MEASUREMENT FEASIBILITY:
NOT VERIFIED

PHASE B FIVE-POINT COST GRID:
NOT VERIFIED

E3 I25 LARGE-N SCALING:
NOT VERIFIED

INSTRUMENTATION RUNTIME PERTURBATION:
UNRESOLVED

B01:
CLOSED

B02:
CLOSED

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

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

TEMPORARY AUDIT ARTIFACTS:
감사 소유 실행본·캐시 4개 경로 삭제, 234504192바이트 회수; 독립 재현·원자료와 새/이전 동결본 보존

NEW AUDIT REPORT:
/home/hjkerman/codex/money-note/docs/t66f-b03-ir04-independent-final-reaudit.md

NEW FINDINGS MANIFEST:
/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b03-ir04/findings.json

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

EXISTING HISTORICAL EVIDENCE MODIFIED:
NO — IR04 기준; IC02의 기존 XML 손실은 별도 기록

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
FAIL — B03 INSTRUMENTATION CORRECTION REQUIRED

NEXT ACTION:
별도 구현 세션에서 delegate 캡처와 설치 reference·teardown 소유권 경계만 교정하고 새 source identity로 보존된 세대 교대 재현을 재검증하세요.
```
