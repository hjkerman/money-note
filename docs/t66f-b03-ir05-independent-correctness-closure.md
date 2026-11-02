# T6.6F-B03-IR05 독립 정확성 재감사

**FAIL — B03 계측 교정 필요.** 정확한 IC03 frozen 후보에서 원 IR04-N01, IR03-N02 및 Python/Dart IR03-N01은 통과했다. 정상 설치 세대 교대도 독립 검증했다. 그러나 회복 가능한 취소가 patch 원복 소유권을 끊는 두 경계를 재현했다. 다음 정상 측정의 native parse1회/2B가2회/4B가 되며 worker의 native 자원0 뒤에도 진단 hold1개가 남는다. 두 신규 **MEDIUM** 결함 때문에 IA04와 B03은 OPEN이다.

## 1. 감사자 구현 독립성과 검토 이력

구현 비관여는 **SATISFIED**다. B03·IC01·IC02·IC03 및 이 후보의 source 수정에 참여하지 않았다. 같은 대화에서 IR03·IR04 독립 감사를 수행했으므로 요청의 별도 새 세션 조건은 충족하지 않는다. 이 검토 연속성을 숨기거나 완전한 새 감사자로 표현하지 않는다. 이번에도 구현을 수정한 뒤 자기 인증하지 않았다. 본 FAIL은 독립 native/literal oracle의 재현 가능한 결과이며 새 세션 한계를 실패 원인의 대용으로 쓰지 않는다.

## 2. 동결 후보 식별

|항목|독립 관측|
|---|---|
|committed baseline|`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`|
|source payload SHA-256|`dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370`|
|archive SHA-256|`145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21`|
|source inventory|850개 / 9,247,384B|
|archive regular member|860개: source850 + context8 + metadata2|
|tracked deletion|0|
|required untracked source|167개|

대상은 `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370/`다. archive bytes와 canonical entries JSON을 각각 SHA-256으로 계산했고 모든 source bytes/길이/POSIX mode, 안전한 경로·중복 부재·baseline Git tree를 확인했다. 제공된 구현 측 verifier PASS를 독립 증명의 대용으로 쓰지 않았다. [재구성 증거](benchmarks/t66f-b03-ir05/reconstruction.json), [source manifest](benchmarks/t66f-b03-ir05/candidate-source-manifest.json).

## 3. 격리 재구성과 live 보존

고정 commit의 Git archive에 frozen `source/`만 overlay했다. source850개와 나머지 baseline2,010개의 Git blob·실행 비트를 시험 전후 검증했다. 실행 root는 `/tmp/money-note-ir05-20261024/candidate`였고 Python/Flutter package source는 이 복원본을 사용했다. 기존 venv·node_modules는 runtime 의존성만 재사용하고 frozen pubspec/lock에서 offline package 설정을 만들었다. mutable live source나 production 데이터로 fixture를 대체하지 않았다.

시작 HEAD/main은 위 baseline, staged 변경은0이고 물리 index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`다. optional lock 없이 Git을 읽었다. 기존 source·보고서·증거4,342개와 세 frozen directory를 대조했고 변화는0이다. [최종 후보 대조](benchmarks/t66f-b03-ir05/final-candidate-integrity.json), [최종 live 보존](benchmarks/t66f-b03-ir05/final-preservation.json).

초기 재구성 도구가 context 원본 mode0664와 archive의 read-only mode0444를 같게 취급해 중단됐다. 동결 `freeze.py`의 context 포장 규칙을 확인한 뒤 새 빈 실행본에서 다시 검증했다. **source850개 mode 검사는 완화하지 않았다.** 실패한 추출본에서는 제품 시험을 실행하지 않았다. [해석 수정](benchmarks/t66f-b03-ir05/reconstruction-tooling-correction.json). 역사 XML/index 사고는 재조사·복원하지 않았다.

## 4. IR04-N01 역사 재현의 원형

원 raw에서 ASCII2B는 native1회인데2회/4B, Unicode9B는2회/18B였다. 원 보존 source `test_ir04_rollover_native.py`의 trace는 A 설치가 살아 있을 때 B를 reference 획득 직전에 멈추고 A를 종료한 뒤 B를 재개한다. 원 source와 raw를 대조했으며 assertion을 바꾸지 않았다. frozen IC03 안의 원 독립 source에서 root/import/output 경로만 치환했다. [adapter 목록](benchmarks/t66f-b03-ir05/original-adapters.json).

## 5. IR04-N01 교정 결과

원 ASCII·Unicode 두 case는 각각 native1회/reported1회 및2B/9B로 **PASS**다. trace의 진입 Event와 재개 대기가 실제 실행됐고 A 종료→B 진입 순서를 유지했다. source의 현재 seam은322이며 delegate 캡처328보다 앞선다. 단순히 경합이 사라진 순차 호출을 PASS로 바꾸지 않았다. 새 teardown 전/후 시험은 old/new state·wrapper identity와 `__wrapped__ is native`도 따로 확인했다. [ASCII raw](benchmarks/t66f-b03-ir05/rollover-native-2.json), [Unicode raw](benchmarks/t66f-b03-ir05/rollover-native-9.json), [원 실행](benchmarks/t66f-b03-ir05/preserved-independent-python.xml).

## 6. delegate 캡처 분석

현재 `instrument()`는322에서 installation reference를 얻고 최초 owner만328에서 parser·344에서 encoder를 캡처한다. worker도266 reference 뒤272에서 원 method를 캡처한다. 이미 설치 중인/활성 세대의 다른 holder는 readiness를 기다린 뒤 기존 wrapper를 재사용한다. 정상 종료 뒤에는 원 delegate가 복원돼 캡처 깊이가1이다. 원 IR04의 선행 캡처 race는 교정됐다. 다만 취소가 원복을 끊으면 registry가 비었는데 실제 delegate는 wrapper인 불일치 상태가 생긴다. 다음 reference의 존재만으로는 그 delegate가 native임을 보증하지 못한다.

## 7. installation reference 소유권

세 종류의 registry key별 state 객체 identity가 세대를 구별한다. state는 `refs`, `stack`, `ready`, `error`를 소유한다. lock 안에서 reference를 예약하고, 최초 owner는 wrapper와 cleanup callback을 설치한다. 다른 holder는 준비 완료 뒤 본문에 들어간다. 정상 중간 release는 ref만 감소하고 마지막 holder가 원복을 수행한다. collector의 ACTIVE scope와 설치 reference는 별개이며 product authority/ticket을 대신하지 않는다.

## 8. teardown·세대 전이 모델

|현재 상태|사건|관측한 다음 상태|
|---|---|---|
|없음|lock 안 최초 acquire|설치 중, refs1/ready false|
|설치 중|다른 acquire|refs 증가, readiness 대기|
|설치 중|patch와 cleanup 등록 완료|ready 공개, 활성|
|활성|nested/acquire·중간 release|같은 wrapper 유지, ref만 변화|
|활성|마지막 release|동일 lock 안 원복→state 제거→없음|
|설치 중|적용 후 등록 전 취소|**state 없음 + 소유권 없는 wrapper** · N01|
|마지막 release|복원 중단|**state 없음 + 퇴역 wrapper 잔존** · N02|

정상 teardown은 같은 RLock 안에서 끝나므로 새 thread가 원복 중간에 lock을 얻는 interleaving은 불가능하다. 실제 새 acquire 시도까지 trace로 확인한 뒤 원복 전·후에서 멈추는 두 case를 실행했다. old release가 새 활성 wrapper를 제거하지 않았고 새 state identity도 달랐다. 실패 전이는 별도 취소 시험으로 재현했다. [상태 모델](benchmarks/t66f-b03-ir05/installation-state-model.json).

## 9. 새 독립 adversarial matrix

|경계|결과|
|---|---|
|최초3/7 holder, 서로 다른 UTF8 길이, 같은 bytes 두 실제 호출|PASS; 모든 holder의 native/counter2회 exact|
|기존 원 최초2/4 및 nested|PASS|
|원복 직전/직후 새 acquire, old release 뒤 새 holder 유지|PASS · 정상 경로|
|native parse 진행 중 다른 holder 종료|PASS; ref2→1, 같은 wrapper 유지|
|250세대와 nested holder|PASS; native 복원·registry 비움, weakref 보존0|
|세 설치 종류를 다른 순서로 쓰는3개 thread|PASS; connection-local SQL·worker ownership 유지|
|patch 적용 전 실제 SIGINT|PASS; clean 복원 및 다음 설치 exact|
|활성 async holder task 취소와 생존 holder|PASS|
|닫힌 context의 늦은 callback|PASS; 새 scope에 이전 event 혼입 없음|
|patch 적용 후 cleanup 등록 전 SIGINT|**FAIL · IR05-N01**|
|last-holder 복원 전 SIGINT|**FAIL · IR05-N02**|
|위 취소 후 worker accepted/rejected|**FAIL; native0인데 pending1/completion0**|
|설치 취소8회 반복|**FAIL; wrapper·handle1→8 누적**|

새 정상 matrix10개와 취소/resource7개를 구현 테스트에서 복사하지 않고 작성했다. barrier/trace로 순서를 고정했고 임의 sleep을 성공 조건으로 쓰지 않았다. [새 matrix source](benchmarks/t66f-b03-ir05/tests/test_ir05_lifecycle.py), [전체 matrix](benchmarks/t66f-b03-ir05/adversarial-matrix.json).

## 10. 실제 parser의 exactly-once

native parser code object의 `call` frame과 실제 raw buffer를 oracle로 삼았다. 정상 세대에서 native1회는 event1회이고 동일 bytes의 별개 두 호출은2회로 센다. payload content deduplication이나 사후 byte 차감은 source에 없다. 취소 후 재진입에서는 native1회가 event2회가 된다. 8회 취소 후 새 정상 설치에서는 native1회인데 event9회다. underlying parser를 여러 번 실행한 금융/파싱 오류로 과장하지 않는다.

## 11. validation 입력 bytes

입력 `{}`의 실제2B는 정상 원 반례에서2B다. 새 취소 두 경계에서는 submitted/completed가4B다. 반복 취소 후에는18B다. Unicode 원 반례9B도 정상 교대에서 정확히9B다. C1/backend JSON의 완료 의미를 구별하고 primary submitted span을 실제 buffer 길이로 비교했다. 전체 validation span 판정은 **FAIL**이다.

## 12. scope·stage attribution

정상 cohort3/7의 서로 다른 collector·stage는 자기 payload만 받았다. late closed context는 새 scope를 오염시키지 않았다. generation/oracle, E2가 호출하는 E1, E3 verify/prepare/commit, E4 read attribution도 관련 원 oracle와 실제 경로에서 통과했다. 새 결함은 타 stage로 옮겨진 event가 아니라 **같은 stage에 같은 실제 event가 중복 표현되는 오류**다. 전체 무중복 stage accounting은 FAIL이다. hash/validation/write/HTTP 또는 inclusive duration을 하나의 total로 더하지 않았다.

## 13. IR03-N02

원 first-install scheduling reproducer를 그대로 실행해 두 번째 scope의 parse1회/2B를 확인했다. 원 seam이 현재 준비 완료 뒤에 있다는 점을 감안해 원 IR04 pre-patch2/4와 새 실제 patch 진입 직전3/7 waiter도 검증했다. readiness 전에 본문이 실행되지 않았고 최초 event 누락은 재현되지 않았다. 원 IR03-N02는 PASS다.

## 14. 원 IA04

원 outer/inner/outer는 실제3회/6B로 통과한다. IR03-N02와 IR04-N01의 원 반례도 모두 통과했다. 그러나 신규 취소 경계가 설치 수명의 duplicate wrapping을 재현하므로 **IA04 전체 독립 수용은 FAIL**이다. 원 nested 결함이 그대로 재현됐다고 표현하거나 과거 판정을 다시 쓰지 않았다.

## 15. IR03-N01 Python/Dart

원 ALTER의 누적 payload6B와 DROP/recreate4B가 양 언어에서 일치했다. 별도 양 언어 schema6개씩의 literal/native oracle는 CREATE/ALTER/DROP, UPDATE·DELETE·UPSERT, commit/rollback/savepoint, 동일 SQL reprepare·cache reuse를 검증했다. 모든 attempted/effective/committed 분류가 유지됐다. 외부 연결의 관측 밖 DDL은 새 DML 전에 명시적 measurement incomplete로 거부하고 이전 committed 결과를 보존했다. 그 경계를 성공한0B 측정으로 보고하지 않았다. Dart SQL source는 IR04와 byte-identical이다.

## 16. IA01–IA07 독립 closure 표

|ID|원 조건·독립 기대|현재 관측|수용|
|---|---|---|---|
|IA01|같은 이름 savepoint: committed1/rollback2B|1/2B; quoted 이름도 일치|PASS|
|IA02|OR FAIL 앞선 성공 row 유지:3B|native/committed3B; ABORT/ROLLBACK/IGNORE 구별|PASS|
|IA03|첫 comment-DML2B|2B 계수|PASS|
|IA04|원 nested3회/6B와 인접 수명|원3/6·N02·IR04 통과, 새 취소에서2/4|FAIL|
|IA05|정상 설치의 closed lease 거부: pending0/completion1/native0|0/1/0|PASS · 원 재현; 설치 취소 후 hold 실패는 신규 finding|
|IA06|owner32 허용,33번째 실행 전 거부, rollback 뒤weakref0|동일|PASS|
|IA07|oracle SELECT는 generation0, setup176/185행|동일|PASS|

원 source/input·숫자 기대값을 유지했다. 원 결함존재를 기대하는 backend4개·Dart3개는 정확한 역사 wrapper에서 분리했고 그 PASS를 현재 correctness로 합산하지 않았다. 현재 후보에는 같은 원 SQL/native 기대 oracle를 실행했다. IA05–07 직접 원문도 실행했다. IA06 원 무제한 loop는33번째 guard로 명시 exit1이 되며 별도 row/weakref oracle가 실행 전 거부와 해제를 검증했다. IA07 stdout은 안전한 Python literal parser로 판독했다. [직접 결과](benchmarks/t66f-b03-ir05/original-direct-current.json).

## 17. hash input-byte oracle

literal domain+NUL+UTF8, 실제 native constructor/update 입력, 반복·chunk/copy·실패 update·닫힌 owner를 대조했다. Unicode·65,537B와 빈 입력도 포함한다. 실제 backend SHA/parser witness가 원 delegate의 입력과 일치했다. HTTP response 크기를 hash 기대값으로 쓰지 않았다. Dart object/manifest·P0와 E3/E4 경계도 원 component oracle 및 실제 경로로 확인했다. 검증한 hash byte oracle는 PASS다.

## 18. validation-span oracle

primary buffer의 submitted/completed/failed를 buffer bytes와 native parse entry로 비교했다. malformed UTF8/surrogate·중복 key·조기 실패·noncanonical·반복/중첩/동시 scope는 정상 설치에서 통과했다. 구조 검사 visits에 객체 크기를 곱하지 않았다. 새 취소 반례가 정확한 primary span을 중복하므로 전체 FAIL이며 구현 측 calibration PASS로 면제하지 않는다.

## 19. SQL logical write-byte oracle

실제 NEW TEXT의 UTF8/BLOB payload가 정의다. UPDATE는 NEW row 전체, DELETE는 신규 payload0과 별도 row event다. selector/bind 문자 수·WAL/DB 크기·physical writes를 대용하지 않았다. 원 SQL·schema·native trigger/cascade·batch·prepared 관련 oracle가 통과했다. 지원 SQL payload의 attempted/effective/committed는 PASS다. 이번 신규 finding을 미검증 SQL 오계수로 확대하지 않는다.

## 20. transaction/savepoint

nearest 같은 이름 savepoint, RELEASE/ROLLBACK TO, outer rollback, statement 부분 성공·iterator 실패, deferred FK의 failed COMMIT, collector close 뒤 settlement, transactional DDL 복귀를 확인했다. 양 언어 literal ledger에서 p INSERT attempted/effective6/3B, UPDATE7/7B, q INSERT5B가 native commit/rollback에 맞게 정산된다. cache가 schema를 재준비해도 row event를 중복하지 않았다. PASS다.

## 21. backend concurrency/TLS

fresh distinct-principal TLS와 valid/invalid auth의 실제 동시 요청, request-local native SHA/parser witness, 예외·완료 뒤 snapshot 고정이 통과했다. 원 started-worker cancellation도 정상 설치 session 내에서 통과했다. 이는 이미 설치된 정상 session의 요청 격리 증거다. SIGINT로 session 소유권이 깨진 뒤의 안전성까지 PASS로 확장하지 않는다.

## 22. Flutter async와 native worker

Flutter의 async/nested/closed context는 PASS다. Python의 정상 native worker cancel/late tail·rejected dispatch도 원 경로에서 PASS다. 하지만 두 새 취소 경계 뒤 accepted/rejected 재진입4개에서는 실제 NativeJob init1회·native leases/jobs/running/tasks 모두0인데 collector pending1·completion0·closed false다. 따라서 묶인 native 수명 판정은 **FAIL**이다. product worker permit leak와 진단 hold 고아화를 구분한다. [worker source](benchmarks/t66f-b03-ir05/tests/test_ir05_worker_interrupt.py), [결과](benchmarks/t66f-b03-ir05/interrupt-worker-resource.xml).

## 23. prepared-statement/cache

managed cache의 연결별 capacity32, reset/rebind·BLOB/NULL, 별도 connection ownership, eviction/finalization, exception/BUSY/use-after-close를 원 독립·P02 회귀로 검증했다. 독립80개 SQL의 peak32/eviction48 및 동일 cached SQL의 `1+(3+2 DEFAULT)+2=8B`가 일치한다. caller-owned 모든 handle의 전역 상한이나 elapsed time만으로 정확성을 주장하지 않는다. PASS다.

## 24. resource 수명과 유한성

정상 경로의 table128/savepoint32/owner32/cache32, registry 종류3·sample16은 source와 경계 시험에서 유지된다. 250 정상 세대의 wrapper weakref 보존은0이다. 그러나 `_patch.start()`는 실제 handle을 stdlib 전역 active list에 넣으며, cleanup 등록 전에 취소되면 그것을 제거할 callback이 없다. 반복 취소8회에서 wrapper 깊이와 active handle이 각각1→8로 늘고 native1회가9 event가 된다. 배열·closure의 보존 경로에 상한이 없다는 source와 실행 증거가 함께 있으므로 임의 작은 fixture만으로 유한성을 추정하지 않았다. **전체 유한 자원 판정은 FAIL**이다. [원 stdlib 보존 규칙](benchmarks/t66f-b03-ir05/stdlib-patch-lifetime.txt), [반복 결과](benchmarks/t66f-b03-ir05/interrupted-wrapper-growth.json).

## 25. 실제 D3→HTTP→E2→E1

실제 인증 TLS 통합6개가 PASS했다. 새 history3/current1 fixture의144 canonical objects는89,644B다. 각 object의 독립 domain/NUL SHA와 native durable BLOB, graph closure/FK, backend raw11 tables와 hot projection을 대조했다. 소형·중형 fixture는 최대 history260이며 새100k cold는0이다. [실제 실행](benchmarks/t66f-b03-ir05/real-sync-integration.json), [canonical/fixture 원자료](benchmarks/t66f-b03-ir05/tests/delta-integration.json.gz).

|실제 단계|accepted sequence|누적 committed object BLOB|
|---|---:|---:|
|cold|1|89,644B|
|no-change|1|89,644B|
|card 한 건 delta|2|104,672B|
|cash 한 건 delta|3|118,657B|
|corrupt object|3 유지|양쪽 OBJECT_HASH_INVALID, 이전 accepted 보존|

## 26. E3/E4

실제 publication과 accepted read의 root/sequence·전체 금융 raw/hot 결과가 OFF/ON 일치했다. authority 취소·stale-user guard도 통과했다. `store_publication.dart:439` final authority guard 바로 다음440에서 동기 COMMIT이며 사이 await/hook이 없다. diagnostic COMMIT wrapper도 동기다. E4 accepted provenance와 Frozen/file10개 회귀의 healthy read·reopen/fresh-process·pending 보존도 확인했다.

## 27. enabled/disabled 제품 동등성

검증한 정상·거부·authority 경로에서 canonical bytes, 금융 raw strings, snapshot/root/accepted 상태와 error 결과가 동일하다. Snapshot v7, OfflineBaseline v4, sync_root/legacy fingerprint 분리, Frozen B/J input-only 및 AppState ownership을 바꾸지 않았다. 모바일 금융 공식을 독립 재계산하지 않았다. 신규 실패의 파싱 결과와 worker 반환값도 정상이며 측정·진단 수명이 잘못된다. 정상 제품 동등성의 PASS가 그 결함을 면제하지 않는다.

## 28. source-lock·P0

current exact6개와 역사 inverse5개를 immutable `da818648031e013e83dd6a680b1b1bde0fb6e0a1`의 실제 Git bytes에 대조했다. 기존23/current6 guard도 fresh PASS다. P0 lineage source·Unicode/control/metadata/order goldens, 기존 baseline·Frozen 및 lineage4 회귀는 그대로 통과했다. SHA 기대값·binding·lineage 함수를 수정하지 않았다. [source-lock 증거](benchmarks/t66f-b03-ir05/source-lock-independent.json).

## 29. fresh 결과와 실행 방법

|범위|fresh 결과|
|---|---|
|원 IR03/IR04 Python 독립7개 file|50 PASS|
|보존된 독립 Dart oracle|23 PASS|
|최초 독립 감사 현재 oracle|backend14, Dart11, 실제 HTTP2 PASS|
|보존된 독립 delta|1 PASS|
|IR05 신규 normal matrix|10 PASS|
|IR05 신규 취소/resource|7 FAIL|
|독립 최종 고유 identity 합계|**111 PASS / 7 FAIL / 0 SKIP**|
|backend 영향 suite|118 PASS: 현재114 + 역사 control4|
|Flutter 영향 coverage|147 PASS: 주요127 + 원 현재11 + 역사3 + 실제HTTP6|
|정적·형식·build|Ruff check/format, compileall, Dart format, Flutter analyze, npm build exit0|

같은 case 재실행·parent control·역사 defect-control·구현 회귀를 신규 독립 합계에 더하지 않았다. 정확한 command/cwd/fixture/환경·candidate digest·raw 결과는 [실행 manifest](benchmarks/t66f-b03-ir05/execution-manifest.json), [고유 집계](benchmarks/t66f-b03-ir05/independent-test-results.json)에 있다. Python3.12.3/SQLite3.45.1, Flutter3.47.4/Dart3.13.3과 실제 import 경로를 기록했고 오케스트레이션 Python3.13.9를 구별했다. 기본 sandbox의 bwrap 초기화 실패 뒤 승인 검토된 실행 경로를 사용했으며 거절은 없었다.

IR05 내부 parent-control adapter가 output literal의 `evidence/` prefix를 빠뜨려 task-owned 두 raw 파일을 덮어썼다. 부모가 생성한 bytes를 명시적으로 보존하고 current/parent를 서로 다른 새 이름으로 다시 실행했다. 최종 finding은 `*-current-final.json`과 confirmed XML만 인용한다. 원 실패 logs는 남고 기존 역사 evidence는 바뀌지 않았다. [작업 내 사고·재검증 기록](benchmarks/t66f-b03-ir05/audit-output-path-incident.json). 과거 XML 조사를 다시 열거나 원 raw를 재현한 것처럼 꾸미지 않았다.

## 30. 역사 full regression과 fresh 범위 결정

IC03의 full backend1460 tests/1540 subtests는 역사 구현 측 결과다. 원 raw XML의 testcase1460·subtest 포함 tests3000·오류/실패/skip0과 log 요약을 독립 재집계하고 counter/SQL wrapper/IC03 test의 SHA를 이번 manifest와 연결했다. IC03 Flutter110 affected PASS/full not rerun, IC02 full Flutter1698 PASS/2 SKIP은 역사 보조 근거다. [IC03 연결](benchmarks/t66f-b03-ir05/historical-ic03-source-and-recount.json).

IR05 full backend/Flutter는 **NOT RERUN**이다. IC03의 IR04 대비 실행 코드 변경은 test-only counter 한 파일이며 Dart/product source는 동일하다. 직접 영향118·147 및 새 독립 matrix·실제 경로를 fresh 실행했다. 결정적인 취소 FAIL은 전체 기존 suite 반복으로 소거되지 않는다. 수시간의 동일 full suite 반복을 scoped verdict의 추가 근거로 요구하지 않았다.

## 31. 신규 finding과 최소 교정 경계

**B03-IR05-N01 · MEDIUM.** `counters.py:82–83`에서 patch 적용이 끝났는데 cleanup이 아직 등록되지 않은 순간 SIGINT를 전달한다. 설치 본문은 실행되지 않고 registry는 비지만 parser가 복원되지 않는다. 다음 정상 설치는 native parse1회/2B를2회/4B로 보고한다. 최소 재현은 [첫 번째 test](benchmarks/t66f-b03-ir05/tests/test_ir05_interrupt_final.py), 최종 raw는 [설치 중단](benchmarks/t66f-b03-ir05/interrupt-after-start-current-final.json)이다. 반복 취소의 무상한 wrapper 보존과 worker hold 고아화도 같은 root의 영향이다. 교정 경계는 공유 `install_patch`의 적용·원복 등록 소유권이다.

**B03-IR05-N02 · MEDIUM.** `counters.py:60–63`의 마지막 reference에서 복원 전 SIGINT를 전달한다. `finally`가 실제 wrapper 복원 여부와 무관하게 state를 제거한다. raw에서는 원복false·registry empty·patch3개 잔존이며 다음 scope가2회/4B를 기록한다. 같은 파일의 두 번째 test와 [해제 중단 raw](benchmarks/t66f-b03-ir05/interrupt-last-release-current-final.json)가 최소 재현이다. 교정 경계는 마지막 reference의 실제 복원과 registry 퇴역 사이 예외 소유권이다. N01의 미등록 callback과 별도 결함으로 기록했다.

두 건 모두 실제 SIGINT 한 번에 따른 KeyboardInterrupt를 포착한 뒤 정상 재진입한다. IC03도 기존 KeyboardInterrupt 시험 뒤 재설치 성공을 검사하므로 같은 복구 모델이다. trace는 시점만 정하고 제품/진단 delegate의 구현이나 canonical 입력을 바꾸지 않는다. 실제 native call frame1회와 literal2B, native job1개·budget0을 독립 oracle로 썼다. 원 source file 교정은 하지 않았고 raw 기록 뒤 audit child의 probe patch만 정리했다.

두 helper의 AST는 IR04와 동일하고 부모 exact counter에서도 두 primitive 반례가 재현됐다. 따라서 IC03가 새로 만든 regression이라고 단정하지 않는다. 새로 발견한 잔존 예외 경계다. [부모 비교](benchmarks/t66f-b03-ir05/parent-source-comparison.json), [부모 control](benchmarks/t66f-b03-ir05/parent-interrupt-confirmed.xml). 심각도는 진단 cohort가 완료되지 않고 측정이 조용히 중복되는 자원·정확성 영향에 대한 MEDIUM이며 금융/보안 사고로 확대하지 않는다.

## 32. 역사 P03 실패

**FAILED — 397,146 / 400,532**, remaining3,386과 세 관측 모두 만료·E3/E4 미도달 기록은 유지한다. 원 backend/client SQLite는 unavailable이다. 소형 새 성공을 full-scale 성공·원 Target 복구로 바꾸지 않는다. logical collector가 P03의 유일한 원인이었다고도 단정하지 않는다. 새 full N=100k cold는0회다.

## 33. 남은 Phase B 의무

§35는 H/D 고정 다섯 N에서 no-change/card/cash의 actual rows/hash/validation/write/HTTP/RTT/memory 반복 통계를, §36 I25는 정상 경로 숨은 full-N 작업 금지를 요구한다. scoped B03 correctness가 전체 비용 준수를 대체하지 않는다. full-scale feasibility·runtime perturbation, five-point grid/I25, Android memory/VFS·physical I/O·power loss, R1 large restore는 미검증/보류다. B01/B02 CLOSED, Phase B INCONCLUSIVE, R1 activation gate CLOSED 및 production NOT AUTHORIZED를 유지한다. 비용 grid·large cold·R1·배포를 실행하지 않았다.

## 34. artifact 정리와 보존

시작 free disk는103,984,615,424B였다. 단일 audit root에서 작업했고 기존 frozen·scratch·cache는 삭제하지 않았다. 완료 후 source850·base2010·기존4342개 및 frozen3개 directory의 bytes/mode를 다시 확인했다. 모든 audit test/build child가 끝났고 읽을 수 있는 동일 UID cwd/fd에서 삭제 대상 참조는 없었다. 일부 기존 daemon/Codex/sshd 등의 접근 제한은 기록하며 시스템 전체 가시성을 주장하지 않는다.

감사 소유 candidate·비실행 실패 추출본·context 복제·Flutter/pytest temp의7개 경로를 제거했다. 할당량 기준 **355,377,152B (약338.9MiB)**를 회수했고 관측 free 증가는 357,675,008B다. 외부 venv/node_modules symlink target은 따라 삭제하지 않았다. 독립 source·원자료·manifest는 새 증거 경로와 소형 `/tmp`에 남겼다. 지속 보존은 저장소 compact 증거와 원 frozen archive를 사용한다. [정리 기록](benchmarks/t66f-b03-ir05/cleanup.json), [보존 manifest](benchmarks/t66f-b03-ir05/retained-evidence.json).

## 35. 최종 B03 판정

**FAIL — B03 INSTRUMENTATION CORRECTION REQUIRED.** identity·재구성, 원 IR04/IR03 및 정상 수명 교정, SQL/hash·대표 실제 경로·제품 동등성의 긍정 증거를 확보했다. 그러나 두 취소 경계의 조용한 중복 계수·미회수 hold·wrapper 누적이 필수 exactly-once·수명·자원 조건을 위반한다. IA04와 B03은 OPEN이다. 재현된 결함을 INCONCLUSIVE로 완화하거나 역사 보존 사고를 실패 원인의 대용으로 쓰지 않는다. 제품·binding·Git index·역사 보고서는 수정하지 않았다.

## 36. 다음 행동

별도 구현 세션에서 patch 적용·cleanup 등록과 마지막 reference의 복원·퇴역을 예외 안전하게 교정한 뒤 새 source identity로 보존된 취소 재현을 재검증하세요. [최소 인계](benchmarks/t66f-b03-ir05/HANDOFF.md)에 두 boundary와 재현 명령의 근거가 있다. 추가 준비 감사나 full100k cold를 선행 작업으로 요구하지 않는다.

## 필수 최종 상태

```text
T6.6F-B03-IR05 INDEPENDENT CORRECTNESS RE-AUDIT:
FAIL

AUDITOR IMPLEMENTATION INDEPENDENCE:
SATISFIED — 구현 비관여; IR03·IR04와 같은 검토 세션이라는 한계 별도 공개

FROZEN CANDIDATE PAYLOAD SHA-256:
dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370

EXPECTED ARCHIVE SHA-256:
145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21

ARCHIVE INTEGRITY:
PASS

CANDIDATE RECONSTRUCTION:
PASS

CANDIDATE SOURCE INVENTORY:
850 / 9247384 bytes

ORIGINAL LIVE GIT INDEX:
UNCHANGED BY IR05

EXISTING UNCOMMITTED WORK:
PRESERVED

HISTORICAL IR02/IR04 FROZEN CANDIDATES:
PRESERVED

IR04-N01 ORIGINAL REPRODUCER:
PASS

IR04-N01 EXACTLY-ONCE PARSE:
PASS

IR04-N01 TWO-BYTE VALIDATION:
PASS

DELEGATE CAPTURE OWNERSHIP:
FAIL — 정상 순서 교정은 통과; 취소 후 퇴역 wrapper를 재캡처

INSTALLATION REFERENCE OWNERSHIP:
FAIL — 예외 뒤 registry와 실제 patch 소유권 불일치

TEARDOWN GENERATION HANDOFF:
FAIL — 정상 교대 통과; 중단된 복원 후 퇴역 경계 실패

ADVERSARIAL INSTALLATION INTERLEAVINGS:
FAIL

IR03-N02:
PASS

IR03-N01 PYTHON:
PASS

IR03-N01 DART:
PASS

IA01:
PASS

IA02:
PASS

IA03:
PASS

IA04:
FAIL — 원 반례는 통과; 신규 인접 취소 결함

IA05:
PASS — 원 정상 설치 재현; 취소 후 hold 실패는 신규 finding

IA06:
PASS

IA07:
PASS

NEW INDEPENDENT FINDINGS:
2 / B03-IR05-N01, B03-IR05-N02 / MEDIUM 각각

HASH INPUT BYTE ORACLES:
PASS

VALIDATION INPUT SPAN ORACLES:
FAIL

SQL LOGICAL WRITE BYTE ORACLES:
PASS — 문서화된 지원 범위

ATTEMPTED/EFFECTIVE/COMMITTED:
PASS — 지원 SQL의 세 분류

TRANSACTION/SAVEPOINT ACCOUNTING:
PASS

STAGE ATTRIBUTION:
FAIL — 취소 후 같은 scope의 event 중복; 정상 stage 격리는 통과

BACKEND CONCURRENCY/TLS:
PASS — 정상 설치 세션의 실제 요청 격리

FLUTTER ASYNC/NATIVE LIFETIMES:
FAIL — Flutter async는 통과, Python native 진단 hold가 취소 경계에서 잔존

PREPARED STATEMENT CACHE:
PASS

FINITE RESOURCE BOUNDS:
FAIL — 정상 상한은 유지; 중단된 설치의 wrapper·handle 누적

REAL D3→HTTP→E2→E1:
PASS

E3 PUBLICATION:
PASS

E4 ACCEPTED READ:
PASS

DISABLED/ENABLED PRODUCT EQUIVALENCE:
PASS — 검증한 정상·거부·authority 경로의 금융/canonical 결과

P0 RECOVERY LINEAGE:
PASS

SOURCE-SHA GUARDS:
PASS

FRESH INDEPENDENT TESTS:
111 PASS / 7 FAIL / 0 SKIP — IR05 신규만 10/7/0

FRESH BACKEND REGRESSION:
PASS — 기존 영향 subset118개; 신규 독립7 FAIL은 별도

FRESH FLUTTER REGRESSION:
PASS — 영향 subset147개; 전체 새 실행 없음

HISTORICAL IC03 BACKEND:
1460 TESTS / 1540 SUBTESTS PASS — 역사 구현 측 실행

HISTORICAL IC03 FLUTTER:
110 AFFECTED TESTS PASS; FULL SUITE NOT RERUN

HISTORICAL P03 N=100K COLD:
FAILED — 397146 / 400532

NEW FULL N=100K COLD RUNS:
0

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

B03 INDEPENDENT INSTRUMENTATION CORRECTNESS:
OPEN — FAIL

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

TEMPORARY ARTIFACT CLEANUP:
감사 소유7개 경로 삭제, 할당량 355377152바이트 회수; 재현·원자료·모든 frozen 후보 보존

PRE-EXISTING EVIDENCE:
PRESERVED — 기존4342개 파일 대조; IR05 내부 출력명 충돌은 별도 기록·재검증

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL VERDICT:
FAIL — B03 INSTRUMENTATION CORRECTION REQUIRED

NEXT ACTION:
별도 구현 세션에서 patch 적용·cleanup 등록과 마지막 reference의 복원·퇴역을 예외 안전하게 교정한 뒤 새 source identity로 보존된 취소 재현을 재검증하세요.
```
