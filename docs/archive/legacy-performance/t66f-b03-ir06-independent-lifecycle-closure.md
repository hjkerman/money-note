**T6.6F-B03-IR06 독립 수명·계측 정확성 감사: FAIL — B03 교정 필요**

정확한 IC05 동결 후보에서 **B03-IR06-N01 · MEDIUM**을 독립 재현했다. `free_tool_id()` 뒤에도 살아 있는 PEP 669 event/callback을 사전 검사가 놓친다. 실제 진입 반환 callback이 예외를 내면 본문은 실행되지 않지만 installation reference와 stage가 남는다. 취소 8회 뒤 primitives reference는 기준 1에서 9로, workers reference는 0에서 8로 늘었다. 이후 실제 parse 두 번·4바이트가 취소된 stage에 귀속되는 변형도 확인했다. **IA04 및 B03 독립 계측 정확성은 OPEN — FAIL**이다. 후보 구현은 수정하지 않았다.

원 IC04 세 실패와 모든 보존 IA/IR 재현의 통과를 신규 결함과 구분한다. 전체 finding 상태는 [기계 판정](../../benchmarks/t66f-b03-ir06/findings.json), 실제 관측은 [monitoring 결과](../../benchmarks/t66f-b03-ir06/evidence/monitoring-matrix-results.json)에 있다.

**1. 감사자 독립성.** 이 대화의 제공된 이력에는 B03 구현, IC01–IC05 교정, IC05 후보 준비, 이전 IA/IR 감사 참여가 없다. 이번 작업에서도 감사 대상 구현을 변경하지 않았다. 구현 독립성은 SATISFIED, 이전 감사 관여는 NONE이다. 세션 UI의 reasoning 설정값을 조회하는 수단은 없으므로 XHigh 설정을 외부 인증했다고 주장하지 않는다. 구현 측 PASS와 이전 감사 판정은 보조 자료로만 사용했다. 다른 agent에게 감사나 구현을 위임하지 않았다.

**2. 동결 후보 검증.** 대상은 `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5/`다. 다음 값들을 실제 bytes에서 독립 계산했다.

|항목|결과|
|---|---|
|committed baseline|`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`|
|canonical payload SHA-256|`47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5`|
|archive SHA-256|`970c195b817d6ec8811b7a35bc1db547f65cdcdca84428fcffda126d8f7ec1f7`|
|payload inventory|876개 / 9,502,954바이트|
|tracked deletion|0개|
|archive·payload·source mode|PASS|

path 정렬 entries를 UTF-8 JSON의 `ensure_ascii=False, sort_keys=True, separators=(',', ':')`로 인코딩해 hash했다. archive의 중복 member 부재, regular source member의 bytes·길이·mode, manifest와 metadata의 일치를 확인했다. archive SHA와 payload SHA를 혼용하지 않았다. HANDOFF와 [고정 manifest](../../benchmarks/t66f-b03-ir06/evidence/frozen-source-manifest.json)를 보존했다.

**3. 격리 복원 및 실행 출처.** 먼저 archive에서 `freeze.py`를 추출하고 manifest의 SHA `6a1b3ef05bac03484aedf24ffcc5db1c8c04ac04252b45b1b752f0a16e4f2441`과 대조했다. 그 도구의 읽기 전용 verify와 별도 member 검사를 수행했다. 고정 Git object의 `git archive`에 frozen source만 overlay하여 `/home/hjkerman/codex/money-note/work/t66f-b03-ir06/candidate`에 복원했다. mutable live 구현을 복사하지 않았다. 선택된 876개와 나머지 baseline 2,010개의 실제 Git blob·실행 mode를 시험 후에도 전부 대조했다. [복원 증거](../../benchmarks/t66f-b03-ir06/evidence/reconstruction.json), [최종 무결성](../../benchmarks/t66f-b03-ir06/evidence/final-integrity-preservation.json).

모든 backend·Flutter·frontend 실행 대상은 복원본이었다. 새 독립 test와 adapter는 외부 감사 경로에서 그 복원본을 import했다. HANDOFF에 따라 `.venv`는 기존 interpreter/package 경로로만 연결했고 frontend도 의존성 `node_modules`만 연결했다. Flutter package 설정은 동결 pubspec/lock에서 `flutter pub get --offline`으로 생성했다. payload source bytes는 변하지 않았다.

**4. 실제 Python 및 실행 환경.** CPython **3.12.3**, SQLite **3.45.1**, pytest **9.1.1**, FastAPI **0.139.2**, httpx **0.28.1**, uvicorn **0.51.0**이었다. Flutter **3.47.4**, Dart **3.13.3**을 사용했다. import된 `canonical.py`, `workers.py`의 실제 경로와 runtime 전용 link, Node/npm 버전은 [환경 기록](../../benchmarks/t66f-b03-ir06/evidence/environment.json)에 있다. 기본 sandbox는 `bwrap` 초기화에서 실패해 승인 검토된 실행 경로를 사용했다. production API·DB·환경 파일은 사용하지 않았다.

**5. entry/exit 소유권 모델.** source에서 확인한 정상 전이와 cleanup 책임은 다음과 같다. installation reference, ACTIVE stage, native hold는 서로 다른 수명이다.

|전이|cleanup 책임 및 검증|
|---|---|
|context 생성|아직 자원 없음. context가 generator를 보유한다.|
|entry 시작·observer 검사|`EntryHandoff`가 실패 rollback을 보유한다. 정상 거부는 inner acquisition 이전이다.|
|reference 획득|`installation`의 state·held flag와 generator finally가 자기 reference를 소유한다.|
|delegate 캡처|reference 획득 후에만 수행한다. 이전 세대 복원이 먼저 끝나야 한다.|
|wrapper 준비·공개|`RecoveryStack.reserve`가 patch 적용 전에 복원 의무를 보유한다. ready 이전에는 waiter 본문이 진행하지 않는다.|
|stage 생성|`scoped_value`의 token과 이전 binding identity를 generator가 보유한다.|
|정상 entry 반환|기존 trace/profile observer 완료까지 handoff가 rollback 책임을 유지한다.|
|caller 인계|structured `with` 또는 획득 전에 예약한 `context.enter(stack)`이 같은 exit gate를 보유한다.|
|본문·실제 await|caller cleanup이 유효하다. 동기 signal router는 본문에 남지 않는다.|
|예외·취소 unwind|같은 generator를 닫아 자신이 획득한 의무만 해제한다. 중복 close는 다른 holder를 해제하지 않는다.|
|마지막 reference 해제|동일 lock에서 복원한다. 실패 callback은 journal에 남고 RECOVERING 한 세대가 명시적 복구 책임을 보유한다.|
|복원·퇴역|실제 복원과 journal 소진 후 registry를 제거한다.|
|실제 native 완료|instance에 결합된 finish가 원 collector hold를 반환한다. session patch 종료와 독립이다.|
|해제된 ID의 PEP 669 반환 예외|**FAIL. 검사 우회 후 entry가 실패하지만 caller exit는 등록되지 않으며, reference/stage rollback도 실행되지 않는다.**|

수동 `__enter__()` caller는 entry 이전에 finally를 확립해야 한다. 현재 benchmark의 네 stack 진입은 획득 전 cleanup 예약을 사용한다. 정상·legacy observer 전이는 통과했지만 마지막 행 때문에 전체 소유권 모델은 FAIL이다.

**6. 원 IC04 세 실패.** 원 `backend/tests/test_logical_cost_ic04.py::test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage`를 변경 없이 먼저 실행했다. 원 source SHA는 `0337cdf6daa6410e9cb454f64d57f0d71ccbc26aa2c02b070081158b16b2cd22`다.

|family|실제 SIGINT·본문|취소 후 reference·binding·delegate|취소 stage 계수|판정|
|---|---|---|---|---|
|instrument|발생 / 본문 0|기준 0 복원 / identity 복원|0회 / 0B|PASS|
|instrument_workers|발생 / 본문 0|기준 0 복원 / identity 복원 / hold 0|0회 / 0B|PASS|
|stage|발생 / 본문 0|외부 primitives ref 1 유지 / 이전 binding 복원|후속 native parse 1회·2B에도 0회 / 0B|PASS|

[원 3건 XML](../../benchmarks/t66f-b03-ir06/evidence/original-ic04-three.xml)과 `outer-enter-return-*.json`이 실제 failure boundary 실행을 증명한다. 신규 독립 20개 조합에서는 반환 callback 안에서 실제 refs·ACTIVE owner·delegate identity도 관찰했다. 원 세 failure의 통과는 새 monitoring 변형의 안전성까지 보장하지 않는다.

**7. IR05-N01/N02.** 보존 `test_ir05_interrupt_final.py`, `test_ir05_worker_interrupt.py`, `test_ir05_interrupted_growth.py`를 원 assertion으로 실행했다. patch 직후 SIGINT, last release SIGINT, accepted/rejected worker, 반복 취소 모두 통과했다. 다음 parse의 native 1회/진단 1회·2B, native 자원 0 뒤 pending 0·completion 1을 확인했다. 두 원 finding은 PASS다. [보존 Python 실행](../../benchmarks/t66f-b03-ir06/evidence/historical-python.xml).

**8. IR04-N01.** 원 `test_unmodified_installation_generation_rollover_native_parse_once`의 ASCII·Unicode scheduling과 native witness를 그대로 실행했다. 각각 native 1회/진단 1회 및 2B/9B였다. teardown 전후의 새 activation과 wrapper identity 회귀도 통과했다. PASS다.

**9. IR03-N01/N02.** 원 ALTER 누적 6B·DROP/recreate 누적 4B가 Python/Dart에서 정확했다. prepared reuse, transactional DDL·rollback·savepoint·외부 schema 변경의 실행 전 incomplete 거부도 통과했다. 원 first-install schedule와 실제 pre-patch waiter에서 첫 event 누락이 없었다. N01 양 언어와 N02의 원 finding은 PASS다.

**10. IA01–IA07.** 최초 감사의 원 defect-existence assertion은 승인된 frozen 역사 wrapper에서 유지하고 현재 strict oracle와 분리했다. backend 역사 4개·Dart 역사 3개의 성공을 현재 정확성 성공으로 합산하지 않았다. 원 직접 IA05–07도 실행했다. IA06 원 무상한 loop는 33번째 owner의 명시적 capacity 오류로 exit 1이었으며, 별도 native/weakref oracle가 실행 전 거부와 rollback 후 해제를 검증했다. [직접 결과](../../benchmarks/t66f-b03-ir06/evidence/original-direct.json).

|finding|현재 독립 관측|최종 수용|
|---|---|---|
|IA01|nearest savepoint committed 1B / rollback 2B|PASS|
|IA02|OR FAIL 성공 prefix 포함 committed 3B|PASS|
|IA03|첫 comment DML 2B|PASS|
|IA04|원 nested 3회/6B와 원 후속 IA/IR 반례 통과|**FAIL — 신규 IR06-N01이 전체 수명을 차단**|
|IA05|거부 dispatch pending 0 / completion 1 / native 자원 0|PASS|
|IA06|owner 32 허용 / 33번째 실행 전 거부 / rollback weakref 0|PASS|
|IA07|oracle SELECT 둘은 setup 176/185행, generation 0|PASS|

원 Python/Dart source, path-only adapter와 변경 목록은 [원 재현 보관본](../../benchmarks/t66f-b03-ir06/evidence/originals.tar.gz), [최초 Dart adapter](../../benchmarks/t66f-b03-ir06/evidence/original-dart-adapters.json)에 있다. 기대 수치를 관측값으로 바꾸지 않았다.

**11. 독립 취소 전이 검증.** 새 [독립 test](../../benchmarks/t66f-b03-ir06/tests/test_ir06_lifecycle.py)는 구현 IC05의 기대값을 복사하지 않고 실제 native parser frame/raw bytes와 별도 caller ledger를 사용한다. 정상·SIGINT, trace/profile, 5개 factory, surviving owner, entry 직후 본문 실패, 지속 cleanup 실패·명시 거부·복구, 실제 async 취소와 native tail을 포함한다. 최종 28건 PASS다. 전체 요구 14행은 [취소 전이 matrix](../../benchmarks/t66f-b03-ir06/cancellation-matrix.json)에 있다.

동기 entry 내부의 임의 명령 사이에 ordinary `Task.cancel()`이 전달된다고 가정하지 않았다. 실제 await 취소, 반환 hook의 취소 요청, 동기 observer 예외·실제 SIGINT를 구분했다. 정상 반환 뒤 body/대입 예외는 caller cleanup이 보장한다. 반환 자체가 실패한 경우는 내부 rollback이 필요하다. 이 구분은 실제 CPython 3.12.3 시험 및 [Python with 규약](https://docs.python.org/3.12/reference/compound_stmts.html#the-with-statement), [task 취소 규약](https://docs.python.org/3.12/library/asyncio-task.html#task-cancellation)과 일치한다.

**12. 독립 stateful oracle.** seed **6606 / 4705 / 90210**, 각 180개 유한 action과 최종 정리를 실행했다. enter/nest/cancel/parse/release/close/retry/native acquire/complete를 합법적 상태에서만 선택했다. active owners·reference 의무·stage stack·closed collectors·실제 입력·native hold를 별도 model에서 계산한 뒤 실제 결과와 대조했다. registry는 추가 불변식 확인에만 썼다.

|seed|검사 상태|실제 parse|collector|생성 guard / 최종 보존|
|---|---:|---:|---:|---:|
|6606|181|46|19|144 / 0|
|4705|181|32|20|176 / 0|
|90210|181|30|20|162 / 0|

GC를 비활성화한 실행에서 마지막 reference·hold·ACTIVE와 guard weakref가 baseline으로 돌아왔다. sequence·expected·observed는 `stateful-<seed>.json`에 보존했다. 이 정상·legacy model의 PASS가 별도 PEP 669 결정적 실패를 면제하지 않는다.

**13. PEP 669 제한 판정.** 후보 `counters.py:123–133`은 이름이 할당된 tool의 global events 또는 entry-code local events가 nonzero이면 획득 전에 명시적 incomplete 오류를 낸다. 검사는 getter만 호출하며 다른 tool 설정을 변경하지 않는다. default runtime, ID만 확보하고 monitoring을 끈 실행, 이름이 있는 local/global entry monitoring, 8회 거부, 거부와 병행하는 기존 유효 thread, monitoring 해제 후 정상 재진입은 모두 통과했다. 기본 pytest와 실제 D3→E 경로의 monitoring ID들은 비어 있었다.

제한은 HANDOFF와 IC05 설명·전이 matrix에 명시되어 있다. binding §35–36은 custom PEP 669 observer 지원을 요구하지 않는다. 따라서 명확한 사전 거부 자체는 계약과 양립한다. 그러나 실제 구현은 **tool 이름이 없음 ⇒ 활성 observer도 없음**으로 취급한다. Python의 `free_tool_id()`는 global/local events나 callback을 해제하지 않으며 PY_RETURN은 실제 반환 직전에 실행된다. 이는 [Python 공식 monitoring 규약](https://docs.python.org/3.12/library/sys.monitoring.html#sys.monitoring.free_tool_id)에 명시된 동작이고 실제 3.12.3에서도 재현됐다.

최종 분류는 **FAIL — REJECTION LEAVES PARTIAL DIAGNOSTIC STATE**다. 정확히는 이 유효한 API 상태에서 사전 거부 자체가 누락된다. 모든 hypothetical monitoring 환경 지원을 새로 요구하는 것이 아니다. 이미 선언한 unsupported observer의 안전한 pre-acquisition rejection과 취소 후 무잔존 조건이 실패한 것이다.

**14. installation reference와 stage 수명.** 최소 재현은 본문 0회, 실제 반환 callback 1회, refs 1 잔존·wrapper 미복원이다. 생존 owner가 있는 반복 변형은 취소 8회 뒤 primitives refs 9, workers refs 8이다. stage 변형은 이전 binding으로 복귀하지 않는다. 수동 `context.close()`로 정상화한 것은 실패 상태를 기록한 뒤의 감사 child 정리이며 PASS 근거가 아니다.

**15. native hold.** 원 accepted/rejected dispatch·constructor/hold 중단·instance finish·late tail과 새 실제 취소 시험은 pending·native budget·completion의 균형을 지켰다. 새 monitoring workers 변형에서도 실제 leases/jobs/running/tasks와 diagnostic pending은 모두 0이었다. **native hold leak는 관측되지 않았다.** workers installation reference leak와 native hold leak를 혼동하지 않는다.

**16. exactly-once 및 validation bytes.** 정상·legacy lifecycle과 새 monitoring 반례에서도 실제 동일한 `{}` parse 두 번은 두 event·4B로 기록됐다. native parse 자체의 중복이나 payload 내용에 따른 임의 차감은 재현되지 않았다. 입력 buffer 기준 길이 oracle는 정확했다. 그러나 취소된 stage의 기대 0회/0B가 실제 2회/4B이고 살아 있는 generation은 기대 2회/4B를 받지 못한다. 따라서 raw parse exactly-once는 PASS지만 **취소 scope를 포함한 validation byte 정확성은 FAIL**이다.

**17. scope/stage 귀속.** generation/setup, request-local D3 observation/transfer, E2가 수행하는 E1 SQL, E3 verify/prepare/commit, E4 accepted read, recovery/P0는 원 실제 경로에서 일치했다. 신규 stage 반례 때문에 전체 per-scope/stage 판정은 FAIL이다. hash·validation·SQL·HTTP와 겹치는 duration을 하나의 총량으로 합치지 않았다.

**18. 유한 자원.** 정상 경로의 table 128, savepoint 32, transaction owner 32, 연결별 managed cache 32, installation 종류 3, 복원 journal 256, request sample 16을 source와 경계 시험으로 확인했다. caller가 직접 소유한 모든 native statement까지 전역 32라고 주장하지 않는다. 해제된 monitoring ID의 취소마다 reference가 증가하고 자동 rollback이 없으므로 **전체 수명 자원 상한은 FAIL**이다. 단순히 작은 반복에서 RSS가 안정적이라는 이유로 유한성을 선언하지 않았다.

**19. hash·SQL 독립 oracle.** literal domain/NUL/raw, native constructor/update, 빈 입력·Unicode·65,537B·chunk/copy·실패 update·closed owner를 대조했다. SQL은 NEW TEXT UTF-8/BLOB payload, UPDATE의 NEW row 전체, DELETE 신규 payload 0과 별도 row event다. selector 길이·HTTP 크기·DB/WAL 크기·physical I/O를 대용하지 않았다. 지원 SQL의 attempted/effective/committed는 PASS다.

**20. transaction/savepoint.** nearest same-name savepoint, RELEASE/ROLLBACK TO, outer rollback, OR FAIL/ABORT/ROLLBACK/IGNORE, partial batch·iterator 오류, deferred FK failed COMMIT, close 뒤 settlement, schema invalidation과 prepared reuse를 fresh 실행했다. 원 SQL/native 결과가 일치했다. PASS다.

**21. backend 동시 요청/TLS 및 Flutter 수명.** 보존된 distinct-principal TLS, 실제 동시 valid/invalid credential 요청, request-local native SHA/parser witness, scope 완료 뒤 snapshot 고정이 통과했다. Flutter Zone의 async/nested/closed owner 및 Python 실제 native tail의 별도 release도 통과했다. 제품의 한 owner·한 장부 의미를 복수 장부 격리 보장으로 확대하지 않았다. Android 실기기 수명 전체의 증거로 사용하지 않는다.

**22. 실제 D3→인증 HTTP→E2→E1.** 보존된 실제 독립 delta/HTTP 3건과 영향 suite의 실제 TLS·중형 경로를 실행했다. 별도 [integration 재검사](../../benchmarks/t66f-b03-ir06/integration_recheck.py)는 실제 전송 canonical bytes의 domain SHA·길이 및 누적 객체 union을 다시 계산해 native SQL BLOB 계수와 비교했다. [결과](../../benchmarks/t66f-b03-ir06/evidence/integration-independent-recheck.json).

|실제 단계|accepted sequence|누적 고유 canonical 저장 bytes|
|---|---:|---:|
|cold · 144 objects|1|89,644|
|no-change|1|89,644|
|card 한 건 delta|2|104,672|
|cash 한 건 delta|3|118,657|
|손상 object|3 유지|OBJECT_HASH_INVALID, 이전 accepted 보존|

소형 history 3 및 지원 회귀 history 9/260을 사용했다. fixed-H/D 다섯 N grid 표본으로 합치지 않았다. canonical fixture·backend raw 11 tables·projection·native durable BLOB 자료는 `originals.tar.gz`와 `http-*.json.gz`에 있다.

**23. E3/E4.** 실제 authority cancellation과 stale-user 직전 fence는 accepted sequence 0·rollback을 유지했다. 정상 E3 publication과 E4 accepted-generation read, Frozen pin·reopen·lineage·pending 회귀도 통과했다. 현재 보호 source의 `finalAuthorityFence();` 바로 다음 동기 `_db.execute('COMMIT');` 사이에는 await/hook이 없다. accepted provenance와 최종 AppState authority를 diagnostic이 대신 결정하지 않는다.

**24. ON/OFF 제품 동등성.** 정상 취득·무변경·card/cash delta·잘못된 object·authority 거부에서 canonical bytes, 금융 raw strings, backend projection, root/sequence·error 결과가 일치했다. Snapshot v7, OfflineBaseline v4, sync_root와 v7 fingerprint 구분, Frozen B/J input-only와 pending/reconciliation 의미를 유지했다. 모바일 금융 계산 엔진을 추가하지 않았다. 새 결함의 실제 parser 반환 결과도 유지된다. 금융 동등성 PASS는 diagnostic 자원·귀속 FAIL을 면제하지 않는다.

**25. source-SHA와 P0.** current exact 6개와 exact inverse 5개를 immutable `da818648031e013e83dd6a680b1b1bde0fb6e0a1`의 실제 Git bytes에 직접 대조했다. 기존 보호/source guard 23개와 현재 guard 6개를 fresh 실행했다. P0 lineage의 역사 goldens·Unicode/metadata/order, baseline compatibility, Frozen/recovery 검증도 통과했다. SHA 기대값·source-lock 정책·binding은 수정하지 않았다. [독립 source lock 대조](../../benchmarks/t66f-b03-ir06/evidence/source-lock-independent.json).

**26. fresh 실행 결과.** 명령·cwd·환경·source identity·XML·raw는 [실행 manifest](../../benchmarks/t66f-b03-ir06/evidence/execution-manifest.json)와 [전체 command 설정](../../benchmarks/t66f-b03-ir06/evidence/execution-configs.json)에 있다.

|범위|최종 fresh 결과|
|---|---|
|보존 독립 Python|67 PASS|
|원 IC04 세 실패 · 별도|3 PASS|
|IR06 신규 legacy/default/stateful|28 PASS|
|IR06 신규 monitoring 반례|**4 FAIL**, 동일 신규 finding의 최소·반복 세 변형|
|backend 영향 회귀|431 PASS: 현재 427 + 역사 defect-control 4|
|Flutter 영향·실제 HTTP|110 PASS, machine `done.success=true`|
|Flutter 추가 보호/Frozen/lineage/authority|52 PASS, exit 0|
|최초 독립 Dart 현재 / 역사 control|11 PASS / 3 PASS, 각각 exit 0|
|frontend build|PASS, exit 0|
|독립 고유 oracle 합계|**146 PASS / 4 FAIL / 0 SKIP**|

독립 합계는 보존 Python 67, 최초 backend 현재 14, 보존 Dart 23, 실제 독립 HTTP/delta 3, 최초 Dart 현재 11, 신규 28/4다. 구현 작성 IC04 세 건·회귀·역사 defect-control·같은 case 재실행은 이 합계에서 제외했다. 원 재현 통과와 신규 계측 실패를 모두 보존했다.

감사 도구 오류도 구분했다. 첫 runner가 gzip 객체의 file descriptor를 child stdout으로 넘겨 압축을 우회했다. 원 stdout 뒤의 빈 gzip member를 확인해 원시 파일을 보존하고 손실 없이 올바른 압축본을 만들었다. 이후 runner는 PIPE에서 압축한다. 110건 Flutter 실행은 정상 완료 event가 있으나 후처리 runner는 exit 1이었고 child OS exit code는 별도 저장되지 않았다. 이를 child exit 0으로 꾸미지 않는다. [복구 기록](../../benchmarks/t66f-b03-ir06/evidence/flutter-affected-recovered.json), [로그 사고 기록](../../benchmarks/t66f-b03-ir06/evidence/runner-log-incident.json).

신규 cleanup probe의 두 초기 실패는 저장된 bound callback과 fault 해제 방법을 잘못 가정해 생겼다. 초기 test source·XML·로그를 보존하고 실제로 등록되는 callback의 fault flag만 제어해 최종 검증했다. PEP 최소 probe의 첫 cleanup도 ID 재확보 없이 설정을 해제하려 해 실패했으며, 최종 재현은 관측 후 ID를 재확보해 정리한다. JSON 집계의 decimal-string 변환도 바로잡았다. 제품 source나 금융 기대값은 변경하지 않았다. 이 감사 도구 오류들을 신규 제품 finding 수에 넣지 않았다.

**27. 역사 full-suite 근거.** frozen context의 backend XML 1,705 testcase와 log의 **1,705 tests / 1,540 subtests PASS**, 오류·실패·skip 0을 재집계했다. IC05 Flutter affected 110 PASS와 reconstructed 312 PASS는 구현 측 역사 결과다. IR06 새 full-suite라고 주장하지 않는다. [역사 재집계](../../benchmarks/t66f-b03-ir06/evidence/historical-ic05-recount.json).

IC05의 변경 경계는 Python 소유권과 benchmark 호출부이고 SQL/hash 및 Dart/금융 제품 source는 보존돼 있다. fresh 직접 영향 431건, Flutter 110+52+11건, 독립 원 oracle와 새 취소/stateful·실제 경로를 확보했다. 전체 backend/Flutter를 다시 반복할 만큼 source provenance가 빠지거나 광범위한 제품 변경은 없었다. 결정적 monitoring 실패는 전체 suite 재실행으로 소거되지 않는다. 따라서 **full backend/Flutter는 NOT RERUN**이며 필수 영향 검증을 별도 준비 작업으로 미루지 않았다.

**28. 신규 finding 및 최소 재현.** `B03-IR06-N01 · MEDIUM`의 정확한 교정 경계는 `docs/benchmarks/t66f-b03/counters.py:127`의 tool-name gate 및 획득 전 실제 global/local event 탐지다. `OwnershipContext.__enter__`가 실패했을 때 caller cleanup이 없는 반환 경계가 직접 영향받는다. 원 IA04의 재진입·취소 수명과 B03 폐쇄를 차단한다. 원 IR05 두 결함이 그대로 남았다고 표현하지 않는다.

실제 source와 ID 할당·callback 등록·free 순서, expected/actual은 [최소 재현](../../benchmarks/t66f-b03-ir06/tests/pep669_released_tool_probe.py), [세 반복 변형](../../benchmarks/t66f-b03-ir06/tests/monitoring_matrix_probe.py), [finding manifest](../../benchmarks/t66f-b03-ir06/findings.json)에 있다. 다음 명령은 새로운 격리 복원본에서 최소 반례를 실행한다. `audit_tree`는 기존 경로를 재사용하지 않는 새 경로다.

```bash
repo=/home/hjkerman/codex/money-note
snapshot=/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5
audit_tree=/tmp/money-note-ir06-reproduce-candidate
IC05_BASE_REPOSITORY="$repo" "$repo/.venv/bin/python" \
  "$repo/docs/benchmarks/t66f-b03-ir06/evidence/frozen-verifier.py" \
  verify "$snapshot" "$audit_tree"
IR06_TREE="$audit_tree" "$repo/.venv/bin/python" \
  "$repo/docs/benchmarks/t66f-b03-ir06/tests/pep669_released_tool_probe.py"
```

최종 명령의 assertion 실패가 반례다. source나 monitoring API를 monkeypatch하지 않는다. 실패를 기록한 뒤 해당 context를 수동 정리한다. 감사에서는 교정을 구현하지 않았다.

**29. 역사 P03 대형 cold.** **FAILED — 397146 / 400532**, 남은 3,386개, 세 observation 만료·E3/E4 미도달을 유지한다. 원 matching SQLite의 부재를 새 소형 성공으로 대체하지 않았다. 계측이 유일한 실패 원인이라고 단정하지 않았다. 새 full N=100k cold는 **0회**다.

**30. 남은 Phase B.** full-scale measurement feasibility, 고정 H/D의 다섯 N no-change/card/cash 비용 grid, E3 I25 large-N scaling, 계측 runtime perturbation은 미검증·미해결이다. Android memory/VFS/I/O·hardware power loss는 미검증, R1 large restore는 DEFERRED, R1 activation은 CLOSED다. B01/B02 CLOSED, Phase B INCONCLUSIVE, production deployment NOT AUTHORIZED를 유지한다.

**31. 산출물 정리와 보존.** 하나의 감사 전용 scratch를 사용했다. source 876개·baseline 2,010개, 기존 live source/evidence **4,937개**, index bytes와 전체 staged path/mode/blob/stage가 모두 보존됐다. 과거 XML/index 사고를 재조사하거나 수정하지 않았다. frozen 파일 26개도 읽기 전용으로 확인했다. Git reset/stash/clean/checkout/commit/push는 없었다.

모든 감사 test/build child 종료와 읽을 수 있는 `/proc` cwd/FD의 scratch 참조 0을 확인했다. 권한상 조회하지 못한 `/proc` 접근은 507건으로 기록해 시스템 전체 가시성을 주장하지 않는다. 종료된 IR06 root의 3,086개 regular file만 제거했고 할당량 기준 **377,741,312바이트, 약 360.24MiB**를 회수했다. 외부 venv/node_modules target·기존 cache·모든 frozen 후보·역사 증거는 보존했다. 원 재현 source/adapters, 실제 canonical/native 자료, XML/log, oracle, integrity와 findings는 새 IR06 경로에 남았다. [정리 기록](../../benchmarks/t66f-b03-ir06/evidence/cleanup.json).

**32. 최종 B03 판정.** **FAIL — B03 CORRECTION REQUIRED.** 재구성과 원 finding 교정, 정상·legacy 취소 복구, hash/SQL 및 대표 실제 제품 경로의 긍정 증거는 확보했다. 하지만 문서화된 PEP 669 API 상태에서 사전 거부가 누락되고, 실패 entry의 reference와 stage가 남으며 후속 실제 작업의 귀속이 틀린다. 필수 자원·귀속 조건의 재현된 실패이므로 INCONCLUSIVE로 완화하지 않는다. B03 독립 계측 정확성은 **OPEN — FAIL**이다.

**33. 다음 행동.** 별도 구현 세션에서 `EntryHandoff.check_monitoring`의 해제된 tool ID 활성 event 탐지를 교정하고 보존된 `B03-IR06-N01` 최소 재현과 세 반복 변형을 재검증하세요.

```text
T6.6F-B03-IR06 INDEPENDENT LIFECYCLE CLOSURE:
FAIL

AUDITOR IMPLEMENTATION INDEPENDENCE:
SATISFIED

AUDITOR PRIOR AUDIT INVOLVEMENT:
NONE

FROZEN PAYLOAD SHA-256:
47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5

EXPECTED ARCHIVE SHA-256:
970c195b817d6ec8811b7a35bc1db547f65cdcdca84428fcffda126d8f7ec1f7

ARCHIVE INTEGRITY:
PASS

CANDIDATE RECONSTRUCTION:
PASS

SOURCE INVENTORY:
876 FILES / 9502954 BYTES

ORIGINAL GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY IR06:
NO

IA01:
PASS

IA02:
PASS

IA03:
PASS

IA04:
FAIL

IA05:
PASS

IA06:
PASS

IA07:
PASS

IR03-N01 PYTHON:
PASS

IR03-N01 DART:
PASS

IR03-N02:
PASS

IR04-N01:
PASS

IR05-N01:
PASS

IR05-N02:
PASS

IC04 THREE ORIGINAL FAILURES:
3 PASS

OWNERSHIP ENTRY/CALLER HANDOFF:
FAIL

OWNERSHIP TRANSFER MODEL:
FAIL

ADVERSARIAL CANCELLATION:
FAIL

PEP 669 CUSTOM ENTRY MONITORING RESTRICTION:
FAIL

PEP 669 PRE-ACQUISITION REJECTION:
FAIL

CANCELLED STAGE RETENTION:
DETECTED

INSTALLATION REFERENCE LEAK:
DETECTED

NATIVE HOLD LEAK:
NONE

EXACTLY-ONCE PARSE EVENTS:
PASS

VALIDATION INPUT BYTE ACCURACY:
FAIL

PER-SCOPE/STAGE ATTRIBUTION:
FAIL

FINITE RESOURCE BOUNDS:
FAIL

HASH INPUT BYTE ORACLES:
PASS

SQL LOGICAL WRITE BYTE ORACLES:
PASS

ATTEMPTED/EFFECTIVE/COMMITTED:
PASS

TRANSACTION/SAVEPOINT:
PASS

BACKEND CONCURRENCY/TLS:
PASS

FLUTTER ASYNC/NATIVE:
PASS

REAL D3→HTTP→E2→E1:
PASS

E3 PUBLICATION:
PASS

E4 ACCEPTED READ:
PASS

DISABLED/ENABLED PRODUCT EQUIVALENCE:
PASS

P0 RECOVERY LINEAGE:
PASS

SOURCE-SHA GUARDS:
PASS

FRESH INDEPENDENT TESTS:
146 PASS / 4 FAIL / 0 SKIP

FRESH BACKEND REGRESSION:
PASS

FRESH FLUTTER REGRESSION:
PASS

HISTORICAL IC05 BACKEND:
1705 TESTS / 1540 SUBTESTS PASS

HISTORICAL IC05 FLUTTER:
110 AFFECTED PASS

HISTORICAL IC05 RECONSTRUCTED:
312 PASS

NEW INDEPENDENT FINDINGS:
1 / B03-IR06-N01 / MEDIUM

HISTORICAL P03 N=100K COLD:
FAILED — 397146 / 400532

NEW FULL N=100K COLD ATTEMPTS:
0

B03 INDEPENDENT INSTRUMENTATION CORRECTNESS:
OPEN — FAIL

FULL-SCALE MEASUREMENT FEASIBILITY:
NOT VERIFIED

PHASE B FIVE-POINT H/D/N COST GRID:
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
단일 scratch 생성·삭제, 377741312B 회수, 재현·원자료·compact 증거 보존

PRE-EXISTING EVIDENCE:
PRESERVED

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
FAIL

NEXT ACTION:
별도 구현 세션에서 EntryHandoff.check_monitoring의 해제된 tool ID 활성 event 탐지를 교정하고 보존된 B03-IR06-N01 최소 재현과 세 반복 변형을 재검증하세요.
```
