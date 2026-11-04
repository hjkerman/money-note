# T6.6F-B03-IC05 — 소유권 진입 반환 경계 교정

이 문서는 구현 측 교정·회귀·후보 동결 기록이다. 독립 B03 closure가 아니다. **최종 구현 측 판정은 PASS — 교정·회귀·후보 동결·재구성이 완료됐다.** 새 N=100k cold 실행과 Phase B cost grid는 실행하지 않는다.

## 1. 시작 저장소와 작업본

HEAD/main/origin/main/실제 remote main은 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 main이다. 의도된 dirty worktree를 유지했다. index의 staged path/mode/blob/stage 식별자는 `8df943cd1934be9aaa6f1f5b9a0dcc1a796e255019c8936e52c50ab414d535b8`, 이번 작업 시작 시 index 파일 SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`다. 과거 stat-cache 사건과 이번 작업의 무변경 검증을 구분한다.

[시작 기록](../../benchmarks/t66f-b03-ic05/evidence/starting-state.json.gz)은 기존 4,712개 소스·증거의 bytes/mode, status, snapshot, 여유 공간과 task scratch를 보관한다. 시작 여유 공간은 약 96.5 GiB다. production 데이터·API를 사용하지 않았다.

## 2. IC04 소스와 비교

IC04의 미동결 manifest `821d64e5e9e530cbda3f54f08fef32072a91c36e829f928a75b534da8b03f709`의 872개/9,431,849B를 실제 파일과 전부 대조했으며 차이는 없었다. 과거 IC03·IR02·IR04 snapshot을 수정하지 않았다. 변경 전 counter/server bytes도 별도 gzip으로 고정했다.

## 3. 원 실패 세 건

원본은 `backend/tests/test_logical_cost_ic04.py::test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage`의 instrument, instrument_workers, stage다. 원 테스트 SHA는 `0337cdf6daa6410e9cb454f64d57f0d71ccbc26aa2c02b070081158b16b2cd22`다.

교정 전 세 건 모두 FAIL을 재현했다. CPython의 실제 trace return callback이 대상 `OwnershipContext.__enter__` frame에서 SIGINT를 발생시킨다. 내부 generator는 이미 reference/stage를 얻었지만 caller는 반환을 완료하지 못했다. instrument/worker는 설치 reference와 wrapper가 남았고, stage는 취소된 ACTIVE binding이 남아 이후 실제 parser 1회/2B를 잘못 소유했다. [원 실패](../../benchmarks/t66f-b03-ic05/evidence/original-three-before.xml)와 gzip raw를 보존했다. 원 assertion은 수정하지 않았다.

역사 파일의 출력 덮어쓰기를 피하려고 동일 bytes의 테스트 사본 또는 module 출력 경로만 IC05 scratch로 보냈다. full-suite adapter도 assertion·ROOT·계측 대상은 유지하며 마지막 세 JSON의 출력용 `__file__`만 격리한다.

## 4. 정확한 원인

IC04는 generator resume와 Python 본문 예외를 보호했으나, 메서드의 exception table 밖에서 실행되는 interpreter return observer까지 rollback 책임을 유지하지 못했다. 따라서 내부 획득은 성공하고 외부 진입은 실패하는 사이에 cleanup 책임이 사라졌다. caller가 `ExitStack.enter_context`로 cleanup을 등록하는 경우에도 등록은 성공 반환 뒤이므로 같은 경계가 존재했다.

## 5. context manager와 취소 도달성

CPython 3.12.3에서 검증했다. 일반 `with`는 `__enter__`가 오류 없이 반환한 뒤에야 `__exit__` 실행을 보장한다. `as` 대상 대입 실패는 이미 body cleanup의 보호를 받는다. [`with` 규약](https://docs.python.org/3.12/reference/compound_stmts.html#the-with-statement), [trace/profile 규약](https://docs.python.org/3.12/library/sys.html#sys.settrace), [실제 RETURN 구현](https://github.com/python/cpython/blob/v3.12.3/Python/bytecodes.c)을 소스·bytecode·실행으로 대조했다.

동기 진입에는 await가 없으므로 임의의 각 줄을 asyncio cancellation point라고 부르지 않는다. return callback에서 `Task.cancel()`만 요청하면 실제 전달은 다음 await이며 그 전 유효 parse는 정상 계수한다. 반면 실제 SIGINT/observer 예외가 return을 실패시키는 원 재현은 도달 가능하다. opcode callback은 CPython 3.12에서 기존 frame의 opcode tracing을 먼저 활성화해야 하므로 그 조건을 실제로 갖춘 시험만 coverage에 포함했다.

## 6. 호출부 조사

[call-sites.json](../../benchmarks/t66f-b03-ic05/evidence/call-sites.json)에 explicit enter/exit, ExitStack, 공용 factory와 과거 fixture를 분류했다. product application에 직접 OwnershipContext caller는 없다. 공용 8개 factory는 같은 소유권 경계를 사용한다. 현재 B03 server의 instrument/connections/workers/setup stage 네 호출을 획득 전 예약 구조로 바꿨다. 과거 P01·독립 IR05 fixture는 원본을 보존하고 현재 benchmark caller와 구분했다. 수동 entry는 caller finally를 entry 이전에 확립해야 한다.

## 7. 교정된 소유권 계약

|상태|cleanup 책임|
|---|---|
|미획득|context 객체만 존재하며 resource는 없다. caller stack은 먼저 release gate를 예약할 수 있다.|
|내부 획득|동일 context가 generator와 rollback을 소유한다. 기존 return observer가 완료될 때까지 유지한다.|
|caller 소유|return observer가 정상 완료되면 structured with 또는 사전 예약 stack이 같은 release 의무를 수행한다.|
|해제 중/해제 완료|기존 idempotent close가 자신의 generator만 닫고 reference/stage를 복구한다. native job의 실제 hold 수명은 별도다.|

새 resource owner registry나 finalizer를 만들지 않았다. 하나의 context release gate를 정상 exit와 실패 rollback이 공유한다.

## 8. 최소 구현 변경

`counters.py`에 frame/thread 한정 `EntryHandoff`를 추가했다. 이미 존재한 local trace/profile callback을 원래 순서로 전달하고, callback이 반환을 실패시키면 context를 닫은 뒤 원 예외·취소를 재전파한다. 정상 반환 시 guard의 frame/delegate/owner 참조와 임시 hook을 제거한다. 원 profile이 없으면 profile hook을 새로 설치하지 않는다. 사용자 body에 signal router를 남기지 않는다.

`OwnershipContext.enter(stack)`은 `stack.push(self)`를 획득보다 먼저 수행한다. `RecoveryStack.enter_context`와 B03 server 네 호출이 이를 사용한다. stack 등록 자체가 실패하면 아직 획득한 resource가 없다. 내부 entry가 실패한 뒤 stack이 다시 exit해도 동일 idempotent gate이므로 다른 소유자의 reference를 감소시키지 않는다.

## 9. 전이 매트릭스

[handoff-transition-matrix.json](../../benchmarks/t66f-b03-ic05/evidence/handoff-transition-matrix.json)은 20개 coverage 행과 실제 test ID, source SHA, 도달 불가능한 경계를 담는다. [entry-bytecode.json](../../benchmarks/t66f-b03-ic05/evidence/entry-bytecode.json)은 return과 exception table을 보존한다. 새 IC05 76건과 원 IC04 세 건의 coverage를 별도로 표시했다.

## 10. 실패·취소 주입

reference·stage·observer 준비 실패, trace/profile return의 RuntimeError와 실제 SIGINT, 양 observer 동시 사용, native profile restoration 실패, caller stack 등록 실패, 첫 body operation 실패, 중첩 진입 실패, exit return 실패를 검증했다. 기존 observer의 local trace 교체·해제, `frame.f_trace`를 반환하는 callback, 실제 opcode, child profile 예외도 원 동작과 예외를 보존한다.

custom PEP669 monitoring이 entry code를 관찰하면 획득 전에 measurement-incomplete 오류로 명시 거부한다. 획득 중 profile/trace의 최초 활성화나 교체도 silent success로 처리하지 않는다. 이전에 hook이 없던 경우까지 실제 frame/profile 상태를 획득 전 상태와 비교한다. 이는 무계수 성공이나 임의 보정이 아니다. mandatory benchmark는 해당 제어를 사용하지 않는다. 다음 독립 감사가 이 제한과 계약의 양립성을 별도로 판단해야 한다.

## 11. 귀속 oracle

실제 native parser frame 진입과 입력 bytes를 독립 ledger로 센다. 취소 A는 0회/0B, 살아 있는 B의 동일 입력 parse 두 번은 2회/4B이며 두 이벤트를 합치거나 삭제하지 않는다. A의 종료가 B를 닫지 않고 stage ContextVar의 이전 binding identity가 복구되는지도 확인한다.

## 12. 반복 취소와 자원

GC를 비활성화한 48회 취소/성공 반복에서 reference·stage·wrapper·native hold를 매 회 baseline과 비교한다. 임시 guard의 weak reference도 소멸해야 한다. GC나 `__del__`을 cleanup 근거로 사용하지 않는다. 실제 Task.cancel 전달은 await에서 검증하며 pending native job은 실제 완료 때 정확히 한 hold를 해제한다.

## 13. 역사 IA/IR 재현

원 IA01–IA07, IR03-N01/N02, IR04-N01, IR05-N01/N02를 보존된 assertion으로 실행했다. root/import/output만 별도 adapter로 옮겼으며 원·adapter SHA와 치환 위치를 남긴다. IA07은 원 script exit0만 인정하지 않고 setup 반환행 176/185, generation 0을 별도 strict oracle로 확인했다. 과거 결함존재형 backend 4개/Dart 3개는 기존 사용자 승인에 따른 동결 역사 구현에서 원 assertion 그대로 실행하며 현재 strict oracle와 분리한다.

## 14. native hold

원 rejected/accepted dispatch·late completion·cancelled worker entry와 IC04 전체 interruption test를 재실행한다. NativeBudget 상태와 diagnostic hold를 각각 확인한다. collector를 강제 닫아 hold leak를 감추지 않는다.

## 15. SQL·hash 계수 보존

[AST 비교](../../benchmarks/t66f-b03-ic05/evidence/source-ast-comparison.json)에서 기존 top-level 변경은 OwnershipContext/RecoveryStack뿐이다. SQL observer, prepared cache, schema invalidation, hash byte 경계는 동일하다. attempted/effective/committed·same-name savepoint·partial success·comment DML·owner32/33·external DDL explicit-incomplete 의미를 바꾸지 않았다. 계측 때문에 추가 product hash/parse/write를 실행하지 않는다.

## 16. 실제 D→E 및 E3/E4

Flutter affected 묶음은 실제 인증 HTTP cold/no-change/card delta/cash delta/corrupt reject를 포함한다. native parser/hash witness, E1 durable canonical bytes, E3 publication, E4 accepted read, OFF/ON 금융 동등성을 확인한다. Flutter production source는 수정하지 않았다. Frozen B/J·Snapshot v7·OfflineBaseline v4·sync_root/v7 구분과 E3 guard→COMMIT를 유지한다.

## 17. 집중 회귀

최종 source SHA에 묶인 새 테스트 76 PASS, backend diagnostic 337 PASS, 보존 독립 Python 67 PASS다. diagnostic 337에는 IC04 전체 169와 원 실패 세 건이 포함되며 합산 시 중복으로 세지 않는다. 정확한 command/cwd/exit/XML/gzip은 각 evidence에 저장한다.

중간 개발 실패도 보존한다. guard metadata cycle, opcode prearm 누락, self-trace 반환 recursion과 callback 순서에 대한 잘못된 새 test 가정을 확인·교정했다. 원 IC04/독립 expected assertion은 바꾸지 않았다. 실제 파일 경로를 잘못 지정한 집중 실행(exit4), root package.json 없는 npm 실행(exit254)은 무검증 실행으로 기록하고 올바른 경로에서 다시 실행한다.

## 18. 전체 backend

첫 전체 실행은 유효한 self-trace callback에서 추가 호환성 결함을 발견해 710 tests/839 subtests 시점에 의도적으로 중단(exit2)했다. 이를 full PASS로 부르지 않는다. 이 소스 차이를 교정한 다음 실행도 진입 중 최초 profiler 활성화에 대한 인접 probe가 reference1을 남기는 것을 확인해 773 tests/839 subtests 시점에 중단(exit2)했다. 기존 observer의 교체뿐 아니라 None→새 observer의 전이도 readiness가 검사하도록 보완했다. 이 경계의 stage/instrument·trace/profile·ordinary error/SIGINT 12건을 더해 76건이 됐다. 집중 검증을 다시 통과한 최종 source에서 clean complete backend 한 회를 실행한다. 최종 결과는 아래 기록과 `backend-complete.json/xml/log.gz`를 따른다.

## 19. Flutter 및 정적 검사

최종 source에 연결한 affected 110건을 실행한다. full Flutter는 Python 소유권만 변경했고 Dart/제품 source가 동일하므로 반복하지 않는다. 과거 complete 1698 PASS/2 SKIP은 역사적 지원 증거다. Flutter analyze, Ruff, compileall, 변경 Python formatting, frontend build, diff check는 별도 결과를 보관한다. debug APK를 만들거나 설치하지 않는다.

## 20. source lock

[보호 검사](../../benchmarks/t66f-b03-ic05/evidence/protected-source-check.json)에서 current exact source 6개와 Dart helper가 동일하다. P0 lineage·AppState·store·validation·C1 source와 SHA 기대값은 변경하지 않았다. 과거 SHA 증거를 갱신하지 않았다.

## 21. Git과 역사 증거 보존

최종 staged path/mode/blob/stage와 index 파일 bytes를 시작 기록에 대조한다. 기존 4,712개 소스·증거에서 허용된 counter/server 두 파일만 달라야 한다. IR02/IR04/IC03 및 기존 IC04 snapshot의 전체 파일 identity도 대조한다. XML 복구·과거 stat-cache 사건을 다시 조사하지 않는다. commit/push/restage는 하지 않는다.

## 22. 전체 후보 manifest

IC04의 전체 872개 source에 IC05 test/verify/matrix/freeze 네 파일을 더한다. 신규 후보는 876개다. base commit, tracked 변경/삭제, 필요한 untracked, mode, bytes, SHA를 기록한다. path 정렬 entries의 UTF8 JSON(ensure_ascii=False, sort_keys=True, separators=(',',':')) SHA-256이 payload 식별자다. archive SHA와 구분한다. 소스 목록 밖의 생성 log·DB·cache는 제외한다.

## 23. 새 snapshot

집중·전체 backend gate가 PASS인 경우에만 새 digest 디렉터리에 원자적으로 최종화한다. 기존 snapshot을 덮어쓰지 않는다. source-only archive와 manifest/base/deletion/mode, compact context evidence, SHA256SUMS, HANDOFF를 보관한다. 0444/0555는 checksum과 함께 사용한 읽기 전용 장치이며 WORM 보장이 아니다.

## 24. 재구성

고정 base Git object와 새 archive만으로 별도 task scratch를 재구성한다. source inventory의 bytes/mode/hash, untouched baseline blob, 삭제 의미, payload/archive SHA를 모두 확인한다. mutable live implementation을 참조하지 않는 reconstructed source에서 작은 집중 smoke를 실행하고 source identity를 다시 확인한다.

## 25. 산출물 정리

하나의 IC05 scratch에 원 test 사본/adapters·pytest DB·재구성본을 모았다. 종료 후 unique oracle·재현 source·JSON·실행 로그를 compact evidence로 보존하고, 종료된 task-owned disposable scratch만 제거한다. 기존 build cache나 다른 작업 산출물은 삭제하지 않는다. 실제 제거량·보존량은 cleanup record에 기록한다.

## 26. 독립 감사 handoff

새 snapshot의 HANDOFF는 원 세 실패, 새 전이 oracle, 모든 IA/IR, native hold, affected HTTP/Flutter, source lock와 완결 backend 결과의 정확한 경로·명령을 제공한다. 다음 작업은 준비 검토나 freeze 반복이 아니라 구현에 참여하지 않은 별도 auditor의 실제 B03 correctness 재감사다. custom observer 제한과 전체 ownership lifecycle도 독립 평가한다.

## 27. 최종 결과

최종 판정은 **PASS — IC05 CORRECTION AND FREEZE COMPLETE**다. 이는 구현 측 결과이며 독립 B03 closure가 아니다.

|검증|최종 결과|
|---|---|
|원 IC04 세 실패|3 PASS, 원 assertion·source 그대로|
|신규 소유권 전이|76 PASS / 0 FAIL / 0 SKIP|
|집중 backend|337 PASS, 원 IC04 전체 169 포함|
|보존 독립 Python|67 PASS 및 IA07 strict oracle PASS|
|완결 전체 backend|1,705 tests / 1,540 subtests PASS, exit0, 1077.388s|
|Flutter affected / 실제 HTTP|110 PASS / 0 FAIL / 0 SKIP, exit0, 447.487s|
|재구성본 smoke|312 PASS / 0 FAIL / 0 SKIP|
|source lock·P0·Ruff·compileall·formatting·analyze·frontend build|PASS|
|index·staged 내용·기존 4,712개 소스/증거·과거 snapshot|보존, 허용된 계측 두 파일만 변경|

backend JUnit의 3,245는 test 1,705와 subtest 1,540의 합이다. 별도 두 full 부분 실행과 source-only 첫 smoke의 환경 오류를 최종 실패 수에 섞거나 감추지 않는다. 실제 command/cwd/source SHA/exit/raw는 [summary.json](../../benchmarks/t66f-b03-ic05/evidence/summary.json), 최종 종합 기록은 [final-summary.json](../../benchmarks/t66f-b03-ic05/evidence/final-summary.json)이다.

- payload SHA-256: `47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5`
- source inventory: 876 files / 9,502,954 bytes
- 새 snapshot: `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5`
- archive SHA-256: `970c195b817d6ec8811b7a35bc1db547f65cdcdca84428fcffda126d8f7ec1f7`
- [원자적 동결·재구성 증거](../../benchmarks/t66f-b03-ic05/evidence/freeze-reconstruction.json), [테스트 후 무결성](../../benchmarks/t66f-b03-ic05/evidence/snapshot-integrity-final.json), [고정된 다음 감사 HANDOFF](/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5/HANDOFF.md)

고정 archive만 재구성해 876개 bytes/mode와 미변경 base 2,010개를 대조했고, archive에서 추출한 standalone helper로 별도 재구성도 통과했다. 최초 frozen smoke는 runtime 경로 부재로 311 PASS/1 환경 FAIL이었다. 원 IR03 TLS fixture가 `candidate/.venv/bin/python`을 실행하므로 source-only 재구성에는 runtime 준비가 필요하다. source 수정 없이 외부 venv symlink만 추가한 뒤 **전체 312 PASS**를 얻었다. [환경 기록](../../benchmarks/t66f-b03-ic05/evidence/frozen-runtime-setup.json)에 그 사실과 실제 import 경로를 남겼다. 다음 auditor는 frozen HANDOFF의 명령에 앞서 `.venv`가 없는 새 재구성본에서만 다음을 실행한다.

```bash
ln -s "${audit_venv}" "${audit_tree}/.venv"
```

이는 Python interpreter/package 준비이며 mutable live 구현을 가져오지 않는다. native canonical/workers가 재구성본에서 import됨을 확인했다. [frozen smoke](../../benchmarks/t66f-b03-ic05/evidence/frozen-smoke.xml) 이후 876개 source와 archive가 그대로임을 재확인했다.

새 snapshot은 읽기 전용 0444/0555이고 WORM은 아니다. 기존 IR02/IR04/IC03 및 기존 중간 snapshot은 변경하지 않았다. stage/index의 과거 사고나 P02 XML 복구를 다시 조사하지 않았다.

최종 cleanup은 task-owned source/oracle 138개를 530,429B archive로 보존한 뒤 종료된 fixture·재구성 scratch를 제거했다. 합계 약 202.22 MiB의 파일 할당량을 회수했다. 외부 runtime·live source·기존 cache·모든 과거/새 snapshot은 유지했다. [cleanup-final.json](../../benchmarks/t66f-b03-ic05/evidence/cleanup-final.json)을 따른다. 증거의 옛 scratch 경로는 실행 당시 provenance이며, 현재 재현에는 고정 archive와 HANDOFF를 사용한다.

B03 독립 correctness는 **OPEN — INDEPENDENT RE-AUDIT REQUIRED**다. B01/B02 CLOSED, Phase B grid/I25 large-N/full-scale feasibility/Android 미검증, R1 activation CLOSED, 배포 미승인을 유지한다. 새100k cold는0이며 commit/push는 없다.

다음 조치: 구현에 참여하지 않은 새 독립 auditor가 위 동결 후보의 전체 소유권·취소 lifecycle과 IA/IR 재현기를 실제 재감사한다.

추가 소형 bytecode cache 정리는 자동 승인 검토에서 전체 디렉터리의 생성 소유권 입증 부족으로 거부됐다. 삭제를 재시도하거나 우회하지 않고 233239B를 보존했다. 이는 정확성·후보 동결 blocker가 아니다. [보존 기록](../../benchmarks/t66f-b03-ic05/evidence/retained-bytecode-review.json)을 따른다.
