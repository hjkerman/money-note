# T6.6F-B03-IR01 재감사 범위 판정과 후보 식별

**PASS — SCOPED B03 INDEPENDENT RE-AUDIT IS CONTRACT-COMPATIBLE**

이 PASS는 제안한 **도구 정확성 재감사 범위의 계약 적합성**에 한정한다.
B03 correctness PASS, IA01–IA07 CLOSED, IC01 완료, Phase B 비용 PASS 또는 재개 승인이 아니다.
기존 100k 추가 완료 gate의 선행 관계를 변경하려면 사용자 승인이 필요하며 이번에 면제하지 않았다.

**검토자 provenance 한계:** 같은 대화에서 본 작업자는 P05 구현에 관여했다. 따라서 구현 비관여라는
인적 독립성은 성립하지 않는다. P05의 해석을 binding으로 사용하지 않고 원 계약과 현재 source를
새로 대조했지만, 이 문서는 별도 구현 비관여 검증자의 확인을 대신하지 않는다.
최종 correctness 재감사와 그 판단은 별도 독립 검증자가 수행해야 한다.

## 1. 저장소 식별

root는 `/home/hjkerman/codex/money-note`, branch는 `main`이다.
HEAD/main/origin/main/실제 remote main은 모두
`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이다.
`AGENTS.md`와 새 `docs/development-artifact-hygiene.md`를 읽었고 프로젝트 상태/domain-model/known-issues,
[architecture의 서버 authority와 클라이언트 신뢰 경계](architecture.md#서버-authority와-클라이언트-신뢰-경계)를
규범적 배경으로 적용했다. 금융 재계산 엔진이나 새 activation을 추가하지 않는다.

## 2. committed baseline

위 commit은 원 독립 B03 FAIL 이후의 committed baseline이며 **현재 교정 구현 자체를 식별하지 못한다**.
원 [B03 독립 감사](t66f-b03-independent-instrumentation-audit.md) §§30–36과
[findings.json](benchmarks/t66f-b03-independent/findings.json)은 그대로 남아 있다.
[원 B01](t66f-b01-independent-validation.md) 및 [B02 독립 결과](t66f-b02-independent-targeted-audit.md)의
closure도 새 재현 결함 없이 재개방하지 않았다.

## 3. dirty worktree와 index

시작 staged 변경은 0개다. unstaged tracked 변경은 다음 5개다.

- `AGENTS.md`: 사용자 정책 변경이며 B03 runtime 수정과 구별한다.
- `docs/benchmarks/t66f-b02-implementation/server.py`: P05 test-only lifecycle.
- `docs/benchmarks/t66f-b03/counters.py`: IC01 backend instrumentation.
- `docs/benchmarks/t66f-b03/server.py`: IC01 generation/oracle attribution.
- `mobile/test/support/logical_cost_sqlite.dart`: IC01 및 P02 diagnostic SQL wrapper.

관련 untracked IC01/P01–P05 source·test·문서도 후보에 포함했다. index SHA-256은
`d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`이며 stage/reset/stash/clean/
checkout/rebase/commit/push는 하지 않았다. 사용자 disk-cleanup 문서는 source 후보와 구별해 보존했다.
읽기 가능한 `/proc`에서 관련 experiment runtime은 관측되지 않았다. 확인 방법과 visibility 범위는
[evidence-review.json](benchmarks/t66f-b03-ir01/evidence-review.json)에 있다.

## 4. 현재 후보의 정확한 identity

[전체 source manifest](benchmarks/t66f-b03-ir01/candidate-source-manifest.json)와
[짧은 identity](benchmarks/t66f-b03-ir01/candidate-identity.json)를 생성했다.

```text
COMMITTED BASE:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

CURRENT CANDIDATE PAYLOAD SHA-256:
645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8

SOURCE/TEST/CONFIG/REVIEW INPUT ENTRIES:
819 files / 9,085,052 bytes

CURRENT TRACKED CONTENT:
683 entries

RELEVANT UNTRACKED CONTENT:
136 entries

FREEZE EXECUTED:
NO
```

이는 capture 시점의 live worktree identity다. 실제 immutable snapshot이나 새 commit을 이미 만들었다는 뜻이 아니다.

## 5. manifest·일관성·제외

각 entry는 actual content SHA-256/길이/mode, committed base blob의 Git OID와 SHA-256,
staged index blob의 OID/SHA-256/stage, unstaged/staged flag를 따로 기록한다.
따라서 **COMMITTED BASE / CURRENT WORKTREE CONTENT / STAGED INDEX CONTENT /
UNTRACKED CANDIDATE FILE**을 혼동하지 않는다.

Python/Dart 진단 구현뿐 아니라 backend app/isolated_sync와 tests, mobile lib/tests/assets,
관련 benchmark sources, archived reproducers, dependency locks, C1/lineage golden,
source-lock review, binding/역사 보고서를 포함했다. 현재 B03의 committed mobile hook도 포함한다.
`historical/` wrapper 사본은 active corrected source와 별도 role이다.
초기 목록에 calibration fixture와 역사 identity 문서를 보강한 이력도 manifest에 명시했다.

두 번의 내용 SHA와 열린 descriptor/path의 inode/size/mtime/ctime, HEAD/index/status를 대조했다.
끝에서도 source를 다시 확인한다. candidate digest는 timestamp가 아닌 정렬된 entries의 명시된
canonical JSON encoding으로 계산하므로 독립적으로 재계산할 수 있다.

DB/build/SDK binary/cache/APK/credentials/운영 자료는 source manifest에서 제외했다.
변경 없는 frontend/Android source는 committed base tree로 식별하며 source override가 없다.
큰 SQLite를 재hash하거나 복사하지 않았고, artifact는 기존 evidence identity만 참조했다.
IR01 자신의 문서·manifest는 순환 digest를 피하려고 후보에서 제외한다. 구체적 exclusion은 manifest에 있다.

## 6. 원 IA01–IA07

원 분류·등급·SQL·expected/actual을
[finding-readiness.json](benchmarks/t66f-b03-ir01/finding-readiness.json)에 보존해 매핑했다.
원 finding은 **5 MEDIUM / 2 LOW**이며 새 독립 CLOSED 판정은 없다.

|ID|원 등급·분류|원 independent 반례|
|---|---|---|
|IA01|MEDIUM / INSTRUMENTATION DEFECT|동일 이름 savepoint에서 native committed1B/rollback2B인데 counter0B/3B|
|IA02|MEDIUM / INSTRUMENTATION DEFECT|OR FAIL 성공 prefix가 남아 native3B인데 counter committed1B|
|IA03|MEDIUM / MISSING MEASUREMENT COVERAGE|첫 comment-prefixed INSERT가 실제2B를 저장했으나 오류 없이 counter0B|
|IA04|LOW / INSTRUMENTATION DEFECT|중첩 설치의 실제 parser3회/6B를4회/8B로 계수|
|IA05|MEDIUM / INSTRUMENTATION DEFECT|미등록 native dispatch 거부 후 budget0인데 pending1/completion0|
|IA06|LOW / INSTRUMENTATION DEFECT|한 미완료 transaction의 closed owners10/100/1000 보존. rollback 뒤0이므로 영구 leak로 확대하지 않음|
|IA07|MEDIUM / INSTRUMENTATION DEFECT|독립 oracle SELECT2개·반환176/185행이 product generation 계수에 혼입|

근거는 [원 findings](benchmarks/t66f-b03-independent/findings.json),
[Python 원 재현](../backend/tests/test_logical_cost_independent_audit.py),
[Dart 원 재현](../mobile/test/segmented_logical_cost_independent_audit_test.dart),
[직접 실험 IA05–07](benchmarks/t66f-b03-independent/evidence/direct-experiments.md)다.

## 7. 구현 측 교정의 재감사 준비

|ID|현재 source의 의도된 교정|준비 판정|
|---|---|---|
|IA01|`counters.py:448`의 reversed frame, Dart `_call`의 lastIndexWhere|READY FOR INDEPENDENT RE-AUDIT|
|IA02|`preserves_failed_prefix`/`_preservesFailedPrefix`의 native error code, prefix·failed COMMIT 정산|READY FOR INDEPENDENT RE-AUDIT|
|IA03|`sql_words`/`costSqlWords`의 comment 처리와 첫 DML 설치|READY FOR INDEPENDENT RE-AUDIT|
|IA04|`installation` refcount·ExitStack teardown·부분 설치 실패 복원|READY FOR INDEPENDENT RE-AUDIT|
|IA05|`instrument_workers`의 미등록 job exact-once diagnostic hold 회수|READY FOR INDEPENDENT RE-AUDIT|
|IA06|owner32 상한·SQL 전 명시 오류·transaction 종료 정리|READY FOR INDEPENDENT RE-AUDIT|
|IA07|`server.py::generation_connection`만 generation, 독립 catalog 비교는 setup|READY FOR INDEPENDENT RE-AUDIT|

현재 [backend 교정 tests](../backend/tests/test_logical_cost_ic01.py)와
[Flutter 교정 tests](../mobile/test/segmented_logical_cost_ic01_test.dart)의 실제 native oracle를 읽었다.
현재 [counter source](benchmarks/t66f-b03/counters.py), [server](benchmarks/t66f-b03/server.py),
[SQL wrapper](../mobile/test/support/logical_cost_sqlite.dart)를 확인했다.
작은 결정적 반례를 실행하는 데 원 100k DB는 필요하지 않다.

원 frozen assertion은 결함 존재를 기대하므로 corrected source에 그대로 PASS를 요구하면 안 된다.
[원 backend router](benchmarks/t66f-b03-ic01/original_backend.py)와
[Flutter runner](benchmarks/t66f-b03-ic01/flutter_full.py)는 baseline defect-control과 current correctness를 나눈다.
역사 wrapper2개는 `historical/manifest.json` 및 Git baseline blob과 SHA가 일치했다.
후속 감사는 이 routing과 원 assertion 보존까지 검증하고, **새 감사 output 경로**를 써야 한다.
기존 runner를 무심코 실행해 과거 evidence를 덮어쓰면 안 된다.

이 source inspection에서 intended correction/fixture의 부재나 새 확정 반례를 찾지는 않았다.
이는 완전한 coverage 검증이 아니다. 실제 supported SQL 경계·미지원 복잡성의 명시 오류·모든 mandatory
D→E seam은 여전히 재감사 대상이며, 누락이 확인되면 scoped 재감사도 PASS할 수 없다.

## 8. binding §35

[§35 원문](t66/c/t66c-delta-sync-protocol.md)은 H/D/N/L/P/E/B를 정의하고 작업별 비용을 나눈다.
unchanged/card/historical update와 full sync/restart/epoch bootstrap은 같은 복잡도 목표가 아니다.
후자는 O(N) validation/build와 전체 저장을 허용한다. 이 허용을 정상 경로 full-N 면제로 확대할 수 없다.

마지막 문단은 **“H/D 고정, N=1k/5k/10k/50k/100k에서 no-change/card/cash rebuild”**의 반복 및
rows read/bytes hashed·validated·written/HTTP entity/RTT/memory·median/p95를 요구한다.
따라서 N100k를 포함한 정상 경로의 실제 비용 증거는 명시 의무다.
그러나 이 문단은 100k cold acquisition 전체를 모든 보조 observer ON으로 완주하라는 문구가 아니다.

## 9. binding §36 / I25

[§36 I25](t66/c/t66c-delta-sync-protocol.md)는 **“steady-state full N 작업 MUST NOT”**,
책임 D/E integration, proof `instrumented rows/bytes`, test `H/D fixed scaling`을 명시한다.
정확한 계측은 그 proof의 필요 수단이다. 정확한 counter의 소형 보정만으로 I25 scaling은 입증되지 않는다.
반대로 cold의 허용 O(N) 비용과 lease 실패만으로 steady-state I25 위반을 자동 확정할 수도 없다.

## 10. 다른 binding 조항과 hierarchy

- §5: restart/physical restore는 새 epoch다. 같은 N/root만으로 원 backend identity를 대체하지 않는다.
- §§7/9/11/23: exact canonical/hash/Target·global facts·primary input과 structural operation을 보존한다.
- §§15–17: TTL900초·flow observation 최대3·원 credential/path 인가·만료 분류를 유지한다.
- §16: 만료 전에 완전 취득·검증한 coherent 관측의 local publication은 가능하지만 ticket guards는 남는다.
- §§24–25/I13/I14: complete graph·receipt·pins·원 AppState guard와 COMMIT 전 authority를 보존한다.
- §22/§29: v7 fingerprint와 sync_root 분리, Frozen B/J input-only 및 no ACK/no rebase를 유지한다.
- §26/§38.8: Android driver/VFS·실기기 power-loss는 별도 필수 proof이며 rollout을 차단한다.
- §31/§34/§38.10: R1 및 통합 의존성은 취소되지 않는다. §34는 integrated audit와 명시 rollout 승인을 요구한다.

원 protocol의 역사적 design-status 표기를 바꾸지 않았다. 현 IR01 지시가 그 문서를 binding 원본으로
지정하므로 위 조항을 적용했다. B03/IC01라는 engineering task 이름은 §34–36의 별도 규범 단계명이 아니다.

## 11. 요구 소유권 matrix

정확한 요구·절·필요 증거·책임·현재 증거·confidence·상태·독립 감사 필요 여부·100k cold 필요 여부를
[22행 matrix](benchmarks/t66f-b03-ir01/requirement-ownership.json)에 기록했다.

|요구|구속력 있는 근거와 소유|현재 상태 / full instrumented cold 필요|
|---|---|---|
|hash input bytes|§7/§35, B03 도구 정확성·Phase B 실제 수집|재감사 필요 / NO|
|validation span|§23/§35, B03 정의의 정확한 parser 경계|재감사 필요 / NO|
|SQL logical payload|§24–25/§35, B03·E1/E3|재감사 필요 / NO|
|attempt/effective/commit|위 비용의 정확한 transaction 해석, 원 감사 §9|재감사 필요 / NO|
|rollback/savepoint|§24–25/§35의 신뢰 가능한 계수를 위한 derived 조건|IA01–02 재감사 / NO|
|stage·overlap|§35/I25, B03 및 Phase B reconciliation|IA07 포함 재감사 / NO|
|HTTP/TLS scope|§15–16/I1/I22 및 B03 소유권 요구|실제 동시 요청 재검증 / NO|
|async/native scope|§25/§16-S/I14 및 B03 수명 정산|거부·실제 시작 뒤 취소 재검증 / NO|
|유한 자원|§35 memory·B03 승인 계측 계약|table/savepoint/owner/cache 경계 재검증 / NO|
|기본 비활성|§34 미활성 지원·B03 test-only 약속|runtime/wire enable 경계 재검증 / NO|
|enabled/OFF 동등성|§2/§7/§22/§25/§29 invariant|전체 실제 소형·error/cancel 재검증 / NO|
|추가 제품 hash/parse/write 금지|B03 관찰-only 약속 및 §35/I25 비용 오염 금지|native 단일 위임·추가 await 부재 재검증 / NO|
|다섯 N 실제 비용|§35/§38.12, Phase B|NOT VERIFIED / N100k 정상 비용은 필수, 특정 cold는 아님|
|E3 I25 scaling|§25/§35/§36 I25, Phase B|NOT VERIFIED / NO, 실제 large-N warm 증거 필수|
|모든 observer ON 100k cold|IC01 §11·P03 추가 실험 gate|P03 FAILED / gate 자체의 성공 주장은 실제 실행 필요|
|runtime perturbation|§35 측정 타당성, B03 대표 overhead·Phase B full scale|UNRESOLVED / full cold가 유일한 방법이라고 확정 안 됨|
|Android VFS/physical IO|§26/§38.8 device·durability·rollout|NOT VERIFIED / 다른 증거 필요|
|hardware power-loss|§26/§38.8 device·durability|NOT VERIFIED / 다른 증거 필요|
|R1 large restore|§31/§34/§38.10|DEFERRED / B03 제외가 전체 의무 취소는 아님|
|activation|§26/§31/§34 explicit gate|NOT AUTHORIZED|
|P0/source locks|승인된 exact review와 §22/29 lineage|재감사 필요 / NO|
|Frozen/file coverage|§22–26/§29의 실제 E4 경계|재감사 필요 / full native R1/device 설치와 구별|

계약은 SQL savepoint 계수기나 특정 collector class를 이름으로 지정하지 않는다.
이 항목들은 실제 비용을 정확히 보고하는 데 필요한 derived 구현·감사 조건이다.
기존 추가 약속을 비규범이라는 이유로 몰래 버리지는 않는다.

## 12. 핵심 A/B/C/D 판정

[독립 명제 분리](benchmarks/t66f-b03-ir01/four-propositions.json)는 다음과 같다.

|명제|판정|이유|
|---|---|---|
|A 정확한 instrumentation으로 actual logical cost 보고|DERIVED NECESSITY|§35 actual 지표·I25 instrumented proof는 명시 의무. 특정 B03 도구 구현은 그 수단|
|B N100k를 포함한 성공한 실제 비용 실험|EXPLICITLY BINDING|§35 다섯 N의 no-change/card/cash·§38.12. 특정 cold 실행과 동일하지 않음|
|C 모든 logical·aux timing observer 동시 ON의 full cold|ADDITIONAL EXPERIMENTAL GATE|IC01/P03의 방법론·추가 gate. protocol literal 의무는 NOT ESTABLISHED|
|D C 성공이 B03 counter-correctness 폐쇄 선행 조건|ADDITIONAL EXPERIMENTAL GATE|이전 completion 조건에는 있으나 §34–36의 B03 binding precondition은 NOT ESTABLISHED|

C/D가 binding에 없다는 판단은 명시 지표를 빼거나 TTL을 늘려도 된다는 뜻이 아니다.
기존 engineering gate의 선행 관계 조정은 사용자 승인을 받아야 한다.

## 13. P03 실제 실패의 의미

[원 summary](benchmarks/t66f-b03-ic01-p03/evidence/summary.json)와
[raw full-result](benchmarks/t66f-b03-ic01-p03/evidence/full-result.json)를 대조했다.
raw의 `durable_objects`는 `{n,bytes}` 구조이며 n=397146, bytes=259743775다.
실제 elapsed는 2699957907µs, 오류는 `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)`다.

|관측|UTC 생성→만료|새 전송 객체|누적 durable|
|---|---|---:|---:|
|1|2026-10-22 07:06:30→07:21:30|129376|129376|
|2|07:21:30→07:36:30|137984|267360|
|3|07:36:30→07:51:30|129786|397146|

400532개 중3386개가 남았고 E3/E4는 도달하지 않았다. full-flow snapshot은 PARTIAL이다.
accepted before/after는 null, protected pending 상태는 unchanged로 기록됐다.
이번에 원 DB를 다시 열어 검증한 결과가 아니라 보존 raw 증거의 대조다.
900초 세 lease를 교환 가능한 연속2700초 예산으로 재해석하지 않는다.

|구분|P03가 입증한 것|
|---|---|
|lease exhaustion|실제 세 관측 만료·선택한 full-run 방법 실패는 확정|
|logical-byte 오계수|그 실패만으로 확정되지 않음. native oracle와 비교해야 함|
|instrumentation 단독 원인|미입증. auxiliary timing·backend/HTTP·환경·tail work 미분리|
|성능 중립|입증되지 않음. prefix나 역사 총시간으로 중립을 주장할 수 없음|
|protocol/금융 결함|불완전 게시·인가 우회 반례가 없음. 실패를 product defect로 자동 확대하지 않음|
|Phase B complete evidence|미완료. prefix counter와 미도달 stage를 whole-run 수치로 바꿀 수 없음|

P03 `sql_us`380084418에는 callback이 포함되고 `observer_callback_us`23548612는 하한 성분이다.
[P03 timing source](benchmarks/t66f-b03-ic01-p03/timing.dart)의 stopwatch 및 backend handler/HTTP 경계는 겹칠 수 있다.
23.55초를 빼면 성공한다고 단정하거나 겹치는 시간을 더해 인과 모델을 만들지 않았다.

## 14. 원 SQLite 부재의 영향

[현재 존재 여부](benchmarks/t66f-b03-ir01/evidence-review.json)를 확인했다. 원 client는 UNAVAILABLE이고
원 matching backend도 복구 증거가 없다. 재부팅 전 client SHA·P04 검증은 역사 증거다.
원 matched-tail replay/새 identity 검증/정확한 full-scale causal isolation은 막혀 있다.
정확한 counter의 local in-memory oracle·새 소형 authenticated fixture는 그 DB에 의존하지 않으므로
counter 재감사 자체가 unauditable해지지는 않는다. 가짜 epoch/root/auth나 새100k 대체 실행은 하지 않았다.

## 15. P05 인계 증거의 한계

[P05 보고서](t66f-b03-ic01-p05-backend-artifact-handoff.md) §§8–16/28과
[최종 raw JUnit](benchmarks/t66f-b03-ic01-p05/evidence/new-tests-final-format.xml)은 소형 lifecycle19개,
실제 TLS 성공·실패 종료, backup/WAL/manifest/restore·인증 D3를 보고한다.
canonical `run-final-format/artifacts/tls-normal/` 사본과 manifest는 존재하며 N1000 reachable4132개를 기록한다.
IR01은 큰 DB를 새로 hash/integrity 검사하지 않았다. 이 PASS는 **구현 측 소형 과거 결과**로 분류한다.
원 P03 backend나 matching tail이 복구됐다는 증거로 사용하지 않는다.
§5에 따라 복원 서버가 새 epoch를 발급하고 old 관측을 거부했다는 점도 원 Target 재사용과 다르다.

## 16. 허용 가능한 B03 counter-correctness 경계

제안 범위는 현재 exact candidate의 관찰 정확성·지원된 모든 mandatory D→E seam·stage 귀속·retry/cache/
transaction/scope/resource·default OFF·동등성·P0/source locks 및 최종 회귀다.
소형 counter가 nonzero라는 이유로 COMPLETE를 줄 수 없다. 실제 operation과 metric의 전수 mapping과
독립 oracle가 필요하다. 대표 overhead·수명·용량 검증도 B03에 남긴다.

전체 규모 measurement feasibility와 비용 compliance를 따로 검증하는 것은 §35/I25의 의무를 보존하면서 가능하다.
현재 도구가 최종 grid를 측정할 수 없으면 그 문제는 **구체적인 Phase B blocker**로 남는다.
원인 미분리 full-run 실패를 counter 오계수와 동치로 만들지 않으며, 운영 가능성 PASS로도 바꾸지 않는다.

별도 검증자가 scoped correctness를 통과시키더라도 반드시 다음 한계를 붙여야 한다.

> 계측 정확성 검증. 전체 규모 측정 가능성과 비용 준수는 미검증.
> `Instrument correctness verified; full-scale measurement feasibility and cost compliance not verified.`

이 한계 없이 “B03 PASS이므로 cost-grid ready”로 확대하면 본 제안 범위와 맞지 않는다.

## 17. 독립 counter oracle

[재감사 계획 RA01–RA22](benchmarks/t66f-b03-ir01/reaudit-plan.json)에 각 deterministic oracle를 적었다.

- hash: literal domain/NUL/raw·실제 constructor/update buffers와 독립 native SHA. 동일 bytes의 반복은 반복 계수한다.
- validation: valid/invalid/truncated/Unicode/duplicate buffers의 직접 길이. backend JSON complete와 Dart C1 complete를 구별한다.
- SQL: wrapper를 거치지 않은 native row/UTF8/BLOB/event/transaction 상태. final row 집합을 누적 write와 혼동하지 않는다.
- SQL 실패: nearest savepoint/OR FAIL/ABORT/FK/failed COMMIT/close rollback을 원 native 결과로 판정한다.
- retry/cache/overlap: 수행 operation ledger를 독립 계산하며 HTTP entity·hash·validation·write를 한 총합으로 더하지 않는다.
- oracle 계산은 제품 측정 scope 밖에서 수행한다. 단지 byte를 세려고 제품 hash/parse/write를 재실행하지 않는다.

raw span이 없는 typed-path/global fact/edge 검사는 operation/record visits로 남긴다.
객체 크기×edge 수로 validation bytes를 만들어서는 안 된다. file write completed/flush/rename을
physical committed I/O로 승격하지 않는다. 원 [계수 명세](benchmarks/t66f-phase-b-final/instrumentation.md)의 정의를 따른다.

## 18. 실제 D→E와 coverage 요구

새 disposable fixture의 실제 인증된 D3/TLS→E2→E1→E3→E4를 독립 재실행한다.
기존 [native witness server](benchmarks/t66f-b03-independent/server.py),
[실제 HTTP tests](benchmarks/t66f-b03-independent/http_test.dart),
[P05의 소형 assertions](benchmarks/t66f-b03-ic01-p05/small_http_test.dart)는 시작점이다.
기대값을 implementation snapshot에서 복사하지 말고 원 C1 buffers·실제 하위 primitive와 native SQL로 만든다.

|경계|확인할 실제 source/소유 scope|
|---|---|
|backend generation|`FinalizationSandbox.bootstrap`, `counters.py::ObservedHash/CostConnectionMixin`, `server.py::generation_connection`|
|D3|`http.py`/`transfer.py`, `ObservedWire`, actual canonical/typed-path primitive와 원 auth/worker scope|
|E2|`fetch.dart`의 acquire/verification/reuse, `c1.dart`; AppState의 명시 e2 scope|
|E1|`store.dart`와 staging SQL·TEMP NEW payload. E2 호출 중 E1 SQL은 활성 e2 stage임을 기록|
|E3|`app_state.dart:457–490`, `store_publication.dart`의 verification/prepare/commit/receipt/pins|
|E4|`store_read.dart`/`store_frozen.dart`·adapters 및 benchmark가 명시한 e4Read/e4Legacy/recovery scope|
|file/P0|`logical_cost_files.dart`, `offline_store.dart:476`의 실제 기존 SHA byte 입력|

모든 E4 호출이 제품에서 자동 stage-tag된다고 주장하지 않는다. 실제 benchmark scope의 coverage를 확인해야 한다.
Frozen 반복 read·file materialization 검증은 complete native Frozen installation/R1/device proof와 다르다.
E3 원 AppState ticket/final guard→native COMMIT 사이 await가 없고 diagnostic이 권한을 결정하지 않는지도 확인한다.

## 19. scope·자원·이전 PASS의 새 회귀

원 B03 감사 §§6–7/13–19/23/25의 이전 PASS를 무조건 이월하지 않는다.

|이전 PASS 영역|새 회귀가 필요한 이유|
|---|---|
|hash·validation·late imports|IC01의 shared installation refcount/복원/alias 소유권 변경|
|HTTP/TLS·native cancel/late finish|worker dispatch hold/release와 cohort completion 변경|
|Flutter async/closed scope|SQL pending owners·prepared handle·현재 Zone attribution의 결합 변경|
|P0·source SHA·금융 동등성|제품 함수가 같아도 통합 계측 infrastructure와 SQL 실행 방식이 바뀜|
|attempt/effective/commit|IA01–03 및 P02 실행 경로 변경의 직접 영향|

실제로 시작된 worker의 late completion, 등록 거부, nested installation, exception/teardown,
closed collector, 반복 초기화, 새 요청/새 run 오염을 검증한다.
유한 table128/savepoint32/owner32/cache32의 한계 전후·weakref·해제·overflow·긴 SQL bypass·BUSY·DDL
invalidation·failed bind·reset/rebind·connection ownership을 확인한다.
managed cache32를 caller-owned statements까지 포함한 모든 native handle의 전역 상한으로 해석하지 않는다.
근거는 [P02 source/test](../mobile/test/segmented_logical_cost_p02_test.dart)와
[현재 SQL wrapper](../mobile/test/support/logical_cost_sqlite.dart)다.

대표 small/medium ON/OFF는 동일 fixture·상태·runtime·profile로 유한하게 비교하고 overhead/초기화/종료와
추가 timing observer를 구별한다. 없는 허용 %를 발명하지 않는다. 이것으로 actual100k 성공을 예측 PASS하지 않는다.

## 20. P0와 source locks

[current exact source guards](../mobile/test/segmented_logical_cost_source_lock_test.dart), 역사 복원 helper와
[source-lock-review.json](benchmarks/t66f-b03/source-lock-review.json)을 대조했다.
IR01 읽기 전용 검사는 현재6개 SHA 및 historical 값이 있는5개 inverse 결과를 `da818648` Git blob과 비교해 일치했다.
이는 기능 재감사가 아니다. [read-only-checks.json](benchmarks/t66f-b03-ir01/read-only-checks.json)에 결과가 있다.

후속 감사는 기존23 guard와 현재6 guard, historical P0 함수·보존된 lineage goldens·Unicode·ordering·기존
compatibility fixture의 byte-for-byte enabled/OFF 동등성을 다시 실행해야 한다.
P0 hook/source SHA expected/policy를 수정하지 않는다.

## 21. 요구하는 최종 회귀와 IR01의 실행 한계

별도 재감사는 frozen 후보의 새 독립 tests를 추가한 **후** full backend/Flutter를 실행한다.
E1/E2/E2-A01/E3/I25/E4/E4-A01/E4-RA01/P0/Frozen B/J/Snapshot v7/OfflineBaseline v4/AppState/
B02 profile·D3c cache·B01 strict concurrency·DB identity·permit lifecycle도 포함한다.
full suites와 분리된 역사 defect-controls의 source/version·실제 case 수를 함께 보고한다.
기존 B01 assertion은 `assert sorted(r.status_code for r in results) == [201]*4+[429]` 그대로다.

full backend/Flutter, Ruff/compileall, Flutter analyze/debug build(지원 시), changed-file format,
`git diff --check`와 backend/frontend의 관련 기본 검증을 최종 source에서 수행한다.
역사 runner는 검토 후 새 output 경로를 쓰며 새로운 실패를 SKIP/XFAIL/옛 counter로 우회하지 않는다.

IR01은 read-only AST parse415개·SHA·원 자료 대조만 수행했다. 기능 tests·npm build·full suites·debug build는
재실행하지 않았다. source/config 변경이 없고 이번 지시는 audit report/manifest 이외 쓰기를 금지하며,
§17도 불필요한 expensive 회귀를 제한하므로 기존 build 산출물을 다시 쓰지 않았다.
P02의 backend1436/1540 subtests와 Flutter1690 PASS/2 SKIP, P05 focused214/73/소형TLS2 및 lifecycle19는
**구현 측 과거 결과**이지 IR01 fresh test 결과가 아니다.

## 22. full-scale 제외와 보존하는 한계

제안 correctness verdict는 fixed-H/D five-point PASS, large-N I25 PASS, 성공한 instrumented100k cold,
Android physical I/O/memory safety, hardware power-loss, R1, 일반 활성화·배포 준비를 입증하지 않는다.
이는 applicable requirement의 취소가 아니다. §26/§31/§34/§35/§36/§38의 전체 의무와 이전 gate는 남는다.

## 23. Phase B에 남는 의무

[Phase B closure](t66f-phase-b-final-evidence-closure.md) §§4–6/9/12/17의 동일 H/D 다섯 N,
실제 full history 정상 작업0·현재 bytes/SQL/HTTP/RTT/storage/memory·median/p95·압축 비교,
정확한 E3 I25·E4 비용 및 full-scale measurement feasibility를 해결해야 한다.
소형 calibration이나 B02의 성공한 두 역사 cold 실행을 이 곡선으로 합칠 수 없다.
P03 실패와 계측/aux observer의 인과 미분리는 계속 기록한다. 현재 grid 재개 승인은 NO다.

## 24. candidate freeze 권고

**Option B — IMMUTABLE SOURCE SNAPSHOT RECOMMENDED.** 현재 index 보존과 미커밋 정책상
Option A commit 권한이 없으며, 이전 완료 조건도 충족되지 않았다. 중립적인 AUDIT CANDIDATE commit은
나중에 새로 승인하면 가능하지만 이번에는 실행하지 않는다.

다음 별도 작업에서 committed base tree + manifest가 지정한 worktree override/untracked source를
보존하는 source-only overlay snapshot을 만든다. 디렉터리 구조와 mode, dependency locks,
reproducer/golden/정책·문서를 유지하고 staged/index/base/worktree 구분을 동봉한다.
DB/cache/build/credentials는 넣지 않고 기존 artifact identity를 참조한다.

완료 archive의 SHA-256과 본 candidate payload digest를 별도 승인/인계 기록에 고정하고,
구현 비관여 verifier에게 독립 사본을 넘겨 재hash하도록 한다. owner가 되쓸 수 있는 chmod만으로
immutable을 주장하지 않는다. digest 불일치나 관련 source 추가/변경이면 candidate를 새로 심사한다.
immutable archive는 scratch 실행 tree와 분리하고 audit evidence도 별도 저장한다.
**IR01은 archive·worktree copy·commit·index 조작을 실행하지 않았다.**

## 25. 필요한 사용자 승인

IR01 지시 §14의 “이전 정식 수락 완료 조건을 실질적으로 바꾸면 사용자 승인” 조건을 적용한다.
다음 승인이 필요하다: **100k 추가 실험 gate를 미완료로 보존하되, 그 성공을 도구 정확성 재감사 폐쇄의
별도 선행 조건으로 쓰지 않는 제안 경계**, 그리고 §15의 **source-only immutable snapshot 생성**이다.
승인 전 gate를 삭제하거나 IC01 완료·B03 PASS로 바꾸지 않는다. commit/push/배포 승인은 요청 범위에 없다.

## 26. 다음 독립 재감사 진입 조건

1. 위 범위·gate 선행 관계의 사용자 승인을 기록한다.
2. hash `645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8` 후보를 별도 승인된 snapshot으로 동결한다.
3. 구현에 관여하지 않은 verifier가 archive/manifest/base/index 구분을 검증한다.
4. 모든 mandatory D→E seam과 RA01–22의 exact oracle·새 output 경로·최종 전체 회귀를 준비한다.
5. 원 100k DB 복구를 가정하지 않고 artifact hygiene와 synthetic-only 경계를 유지한다.
6. full-scale caveat와 기존 Phase B·device·R1·activation 차단 상태를 인계한다.

## 27. 최종 scope 판정과 보존

**PASS — SCOPED B03 INDEPENDENT RE-AUDIT IS CONTRACT-COMPATIBLE.**
실제 bytes 측정과 five-point 비용 의무는 유지하면서 도구 정확성의 별도 검증 범위를 정의할 수 있다.
C/D를 binding B03 전제라고 만들 근거는 확인하지 못했다. 이전 engineering gate의 변경은 승인 대기다.
인적 독립성 한계를 공개했으며 이 문서는 별도 독립 검증자의 판단을 자칭하지 않는다.

새 파일은 IR01 보고서·JSON/text manifest뿐이다. 제품·진단 source·protocol·expected SHA·역사 결과·index는
변경하지 않았다. 새100k/성능 캠페인/SQLite clone/임시 source/build는0, 기존 파일 삭제0이다.
artifact hygiene의 대형 임시 산출물 정리는 NOT APPLICABLE이다. 시작 available은104071675904B였다.
최종 source/index 보존·공간·manifest 자체 SHA는
[candidate-consistency.json](benchmarks/t66f-b03-ir01/candidate-consistency.json)에 남긴다.

## 28. 한 가지 다음 행동

**제안 경계와 후보 `645fd4d8…6b582b8`의 source-only immutable snapshot 생성을 명시 승인받아,
구현 비관여 독립 검증자에게 인계할 후보를 동결한다.**

## 필수 최종 상태

```text
T6.6F-B03-IR01 INDEPENDENT SCOPE ADJUDICATION:
PASS — 계약 적합성 분석; 검토자의 P05 관여 이력 공개

STARTING COMMITTED HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

ACTUAL HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

GIT INDEX:
PRESERVED

UNCOMMITTED IC01/P01–P05:
PRESERVED

CURRENT AUDIT CANDIDATE:
IDENTIFIED — 아직 동결하지 않음

CANDIDATE SOURCE MANIFEST:
docs/benchmarks/t66f-b03-ir01/candidate-source-manifest.json

CANDIDATE PAYLOAD SHA-256:
645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8

CANDIDATE SOURCE HASHES:
VERIFIED — 819개 / 9085052B

BINDING PROTOCOL:
UNCHANGED

BINDING §35:
REVIEWED

BINDING §36 / I25:
REVIEWED

B03 COUNTER CORRECTNESS SCOPE:
CONTRACT-COMPATIBLE

ACTUAL HASH BYTE REQUIREMENT:
B03 — 도구 정확성; Phase B 실제 수집과 구별

ACTUAL VALIDATION BYTE REQUIREMENT:
B03 — 명시한 primary input span

ACTUAL WRITE BYTE REQUIREMENT:
B03 — SQL logical payload; physical IO와 구별

EXACT COUNTER INDEPENDENT ORACLES:
REQUIRED

IA01–IA07:
READY FOR RE-AUDIT — 독립 CLOSED 아님

BACKEND D3 AND FLUTTER E1–E4 MEASUREMENT:
READY FOR RE-AUDIT — coverage PASS 아님

PREPARED-STATEMENT REUSE:
READY FOR RE-AUDIT

SCOPE AND RESOURCE BOUNDS:
READY FOR RE-AUDIT

P0 RECOVERY LINEAGE:
READY FOR RE-AUDIT

SOURCE LOCKS:
READY FOR RE-AUDIT — 읽기 전용 current6/historical5 대조 일치

P03 INSTRUMENTED 100K COLD:
FAILED — 397146 / 400532

P03 FAILURE EVIDENCE:
PRESERVED

ORIGINAL P03 SQLITE:
UNAVAILABLE

P05 ARTIFACT HANDOFF:
PASS — SMALL SYNTHETIC FIXTURE; 구현 측 과거 결과

INSTRUMENTED 100K COLD COMPLETION:
ADDITIONAL IC01 EXPERIMENTAL GATE

BINDING JUSTIFICATION:
§35는 다섯 N의 no-change/card/cash 실제 비용을 요구하고 cold O(N)을 허용한다. §36 I25는 steady-state full-N을 금지한다. 모든 aux observer ON cold 성공을 B03의 별도 선행 조건으로 명시하지 않는다. 이전 추가 gate의 조정에는 사용자 승인이 필요하다.

FULL FIVE-POINT H/D/N COST GRID:
NOT VERIFIED

E3 I25 LARGE-N SCALING:
NOT VERIFIED

MEASUREMENT RUNTIME PERTURBATION:
UNRESOLVED

PROPOSED INDEPENDENT B03 RE-AUDIT:
PERMITTED — 기술적 범위 적합; 사용자 승인·후보 동결·별도 독립 검증자 필요

AUDIT CANDIDATE FREEZE:
IMMUTABLE SNAPSHOT RECOMMENDED

CANDIDATE FREEZE EXECUTED:
NO

NEW FULL 100K COLD RUNS:
0

PRODUCT SOURCE MODIFIED:
NO

SOURCE LOCKS MODIFIED:
NO

FULL BACKEND:
NOT RERUN

FULL FLUTTER:
NOT RERUN

B01:
CLOSED

B02:
CLOSED

IC01 IMPLEMENTATION:
UNCOMMITTED — INDEPENDENT RE-AUDIT PENDING

B03 INDEPENDENT AUDIT:
OPEN

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

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

FINAL SCOPE VERDICT:
PASS — SCOPED RE-AUDIT CONTRACT-COMPATIBLE

NEXT ACTION:
IR01 §14·15에 따라 제안 경계와 위 후보의 source-only immutable snapshot 생성을 명시 승인받아, 구현 비관여 독립 검증자에게 인계할 후보를 동결한다.
```
