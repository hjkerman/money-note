# T6.9-PRE05 — 원 B03의 E3·보관 부기 직접 관측 경계 독립 정적 검토

**PASS — EXTERNAL OBSERVER FEASIBLE, QUALIFICATION REQUIRED.** 판정 선택은 **B**다. 기존에 자격을 얻은 B03 합계만으로 I25 두 의무를 수용할 수는 없다. 그러나 원본의 공개 단계 조회·진단 DB factory·기존 fault 경계와 지원 runtime의 공개 실행 관측 API를 조합하면 제품 파일이나 B03 계측을 고치지 않는 별도 collector의 정적 설계가 가능하다. 아래 경로는 새 관측기의 정확성·완전성·교란이 검증됐다는 뜻이 아니다. **추가 관측기 자격은 계속 미획득이며 실행 허가와 I25 수용은 발급하지 않는다.**

이 세션에 제공된 이력에는 B03 구현·이전 계측 제작·PRE01–04 수행 참여가 없다. 저장소와 frozen archive에서 새로 재구성했으며 위임하지 않았다. 검토자 독립성은 **SATISFIED**다. 외부 개인 신원이나 UI reasoning 설정을 인증하는 주장은 아니다. 역할은 정적 경계 검토에 한정하며 구현·실행·승인 권한을 행사하지 않았다.

## 1. 원 B03 source identity

| 항목 | 독립 정적 확인 |
| --- | --- |
| 시작 HEAD / branch | `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` / `main` |
| frozen 기준 tree | `af2aa70ce6a8cd27c18c134564e31702f0f54f8c` |
| payload SHA-256 | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| engine SHA-256 | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| archive SHA-256 | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |
| 원본 위치 | `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/` |
| archive 검사 | source 899개·9,801,906B, context 166개, metadata 2개, 총 1,067 regular member의 SHA·길이·mode·안전 경로·중복 부재 |
| engine 재구성 | 원 `observation.py:76–86`의 98개 입력 SHA map을 정적 직렬화, 9,587B artifact의 SHA 일치 |
| index | 2,693개 path/mode/blob/stage를 frozen baseline inventory와 전부 대조; 모두 stage 0, staged 변경 0개 |
| runtime 계약 | CPython 3.12.3 / backend SQLite 3.45.1 / Flutter 3.47.4 / Dart 3.13.3 / client SQLite 3.53.4, 안정된 monitoring |

[source-identity.json](benchmarks/t69-pre05/source-identity.json)에 전체 source manifest와 index identity를 보존했다. Archive를 추출하거나 제품 module을 import·실행하지 않았다. 현재 SDK의 `version` 및 공개 Zone API source를 읽어 해시를 남겼지만, 실제 로드 binary·새 build·실행 환경을 인증한 것은 아니다. 이후 qualification에는 interpreter/SDK/compiler/native driver 및 collector/harness binary 해시가 별도로 필요하다.

아래 **`F:경로:행`은 이 검증된 archive의 `source/경로`**를 뜻한다. live checkout의 같은 이름 파일을 원본 근거로 혼합하지 않는다. 특히 live `observation.py` 및 engine admission 변경, B05/B08 최적화는 이 검토의 실행 source가 아니다. `S:`는 위 runtime 계약과 구별하여 읽은 로컬 SDK `/home/hjkerman/.flutter/bin/cache/dart-sdk/lib/async/` 파일이다.

승인 B11도 독립 대조했다. [승인 기록](benchmarks/t66f-b11-application/authorization-decision.json)의 원 제안·amendment record·책임 보충안 SHA가 실제 파일과 같고, AM01–05는 보충안 및 적용 기록과 exact 일치한다. 현재 C/B 문서에서 그 추가문만 제거하면 보존된 적용 전 SHA가 복구된다. C SHA는 `5d3f03a0e61c6d504cf8efd5de0c8ee446b9c0a0b4a45a367f6d366a4fbf94c9`, B SHA는 `e2d820ba71018414934ad4a9b3667961c209f93fe0b5b5dd2d0a3233ea76b279`다. [독립 정합성 검토](t66f-b11-applied-amendment-independent-consistency-review.md:15)와 [종결 재판정](t66f-b11-post-amendment-closure-readjudication.md:3)의 행정 종결·0/8·formal F 차단을 유지한다. 원 보충안의 역사적 DRAFT 표시는 후속 승인 기록과 구별했다.

## 2. 정확한 I25 수용 기준

규범 원본은 [C §35](t66/c/t66c-delta-sync-protocol.md:697), [§35-T69](t66/c/t66c-delta-sync-protocol.md:718), [§36 I25](t66/c/t66c-delta-sync-protocol.md:777)다. B11은 수집 시점만 옮겼다. 금융 authority는 [architecture의 신뢰 경계](architecture.md:14)와 [domain-model 원칙 5·6](domain-model.md:107)을 따른다. 별도 모바일 금융 재계산 의무는 추가하지 않는다.

| 요구 | 직접 필요한 증거와 판정 단위 |
| --- | --- |
| `I25-E3-100K`, §35-T69 726행 | N100k no-change/card/cash 정상 작업의 E3Verify/Prepare/Commit별 rows/bytes·SQL·tree/index/pin/CAS/readback 귀속, 다섯 full counter의 정상 구간 증가량 0 |
| 다섯 counter | `full_recoveries`, `full_verifications`는 실행 횟수, `full_raw_rows`, `full_fact_rows`는 행/fact 수, `canonical_full_builds`는 전체 구성 횟수다. 이 조건은 elapsed time=0 또는 모든 bytes=0이 아니다 |
| `I25-BOOKKEEPING-100K`, 727행 | 같은 정상 D/E의 lease/GC/refcount/root-pin/transfer read·visit·write를 source와 직접 counter로 결합하여 hidden full graph/history scan 및 control의 flat P 목록 부재 입증 |
| 정상 full-N 금지, §35 699–716행 | 전체 역사 fetch/hash/serialize/write 횟수 0. 고정 H/D에서 changed bytes·영향 leaf/path/index의 제한된 증가를 확인. no-change lease pin의 전체 graph 순회도 위반 |
| 허용 예외, §5·18·23–24·32 | initial/restart/명시 full recovery·maintenance의 O(N/P)는 별도 workload. 정상 refresh에 숨길 수 없음 |
| 부기 의미, §16 323–329행 | typed incoming edge와 외부 root pin의 실제 증감, credential/TTL/epoch 확인, release/retirement. 서버는 네 transferable root 외 내부 input-proof pin도 실제 source에서 관측해야 함 |
| maintenance, §16-S 370–384행·§32 649행 | 전체 reachability mark/sweep는 명시 maintenance. 정상 요청에서 실행되지 않았다는 관측과 요청 밖 실제 실행을 분리 |
| 독립 수용, §35-T69 729–745행 | 원 source·지원 runtime·fixture·완전 accepted baseline/provenance 사전 admission, 원 AppState accepted/readback→E4 실제 완료, 오류·취소·raw·교란 공개, 비참여 독립 수용 |

N은 ledger 총 N이고 authoritative 전체 행은 N+35인 원 B04 계열을 구별한다(§35-T69 731행). 표본 수·r/U/q·절대 ms 기준을 새로 정하지 않았다. 기존 정상 grid와 추가 metric의 표본을 섞지 않으며 낮은 N이나 prepare/discard를 N100k accepted 결과로 승격하지 않는다.

`work` key가 없는 snapshot은 그 자체로 직접 관측된 0이 아니다. collector의 전 구간 포착, source에서 해당 counter의 실제 증가 지점, 정상 완료, scope 보존이 모두 증명될 때만 차분 0을 주장할 수 있다. 실패 도중 아직 도달하지 않은 후행 counter는 미완결로 표시해야 한다. E3 wall time, SQL bind bytes, 물리 I/O, SQL 반환행과 VM/pager 방문행도 각각 다르다. 전체 규범 매핑은 [i25-normative-requirements.json](benchmarks/t69-pre05/i25-normative-requirements.json)에 있다.

정상 entry도 매번 `recoverAcceptedGeneration`을 호출한다. 그 부분의 이름이 `recovery`라는 이유로 정상 workload에서 제외할 수 없다. 정상 반복에서 실제 full recovery가 발생하면 해당 정상 작업의 full-N 증거로 기록해야 한다. 초기 기준선 확립·재시작·명시 복구의 별도 workload와 구별하며, 정상에서는 same-connection provenance 재사용 여부까지 관측해야 한다.

## 3. E3 publication 호출 그래프

| 단계 | 실제 caller → callee와 원본 근거 |
| --- | --- |
| 준비·복구 | `AppState.publishSegmentedForIsolatedUse` → `LogicalCost.at(recovery, recoverAcceptedGeneration)` (`F:mobile/lib/src/app_state.dart:423–459`) |
| E2 / 내부 E1 | 같은 entry → `IncrementalFetcher.acquire` (`app_state.dart:460–468`) → transport·검증·store write. 기존 recovery와 E2를 E3에서 차감하여 배분하지 않음 |
| E3Verify | `LogicalCost.at(e3Verify)` → `verifyPublicationCandidate` (`app_state.dart:469–474`, `store_publication.dart:104–133`) → 유효한 same-connection proof면 `verifyIncrementalGeneration`; 그렇지 않으면 `verifyCompleteGeneration` |
| 실제 검증 작업 | `incremental_verification.dart:141–147,211,310,385,410`의 tree/row/fact/relation/hot counter, `graph.dart:197–212` 및 `patricia_edit.dart:15,50`의 실제 node counter |
| 전체 검증 경로 | `verification.dart:374–379,427–432,437–455`의 실제 full counter, `store_publication.dart:528–552`의 full recovery와 recursive closure. 정상 경로에서 관측되면 예외 workload와 구별하여 평가 |
| E3Prepare | `LogicalCost.at(e3Prepare)` → `prepareGeneration` → `_transaction` → manifest/receipt INSERT → incremental이면 네 root만 pin → `_generation` readback (`app_state.dart:475–484`, `store_publication.dart:284–364`) |
| E3Commit | `_withLineageLock` → `requireAuthority` → `LogicalCost.at(e3Commit)` → `commitPreparedGeneration` (`app_state.dart:486–493,2598–2609`) |
| transaction·CAS | BEGIN IMMEDIATE → schema/data-version/base ID·sequence 확인 → prepared manifest/receipt 확인 → no-change면 기존 ID/sequence 유지, 변화면 accepted pointer UPDATE (`store_publication.dart:369–424`) |
| 마지막 publication | usage/budget → 기존 `before_publication_commit` fault → `finalAuthorityFence()` → 바로 동기 `_db.execute('COMMIT')` (`store_publication.dart:426–440`) |
| COMMIT 후 | committed 표시 → 기존 `after_publication_commit`/`during_publication_readback` fault → 실제 accepted storage readback/data-version/proof association (`store_publication.dart:441–468`) |
| 실패·후처리 | COMMIT 전 rollback, COMMIT 후 `PublicationCommittedException` (`store_publication.dart:469–488`); AppState 재검사 및 finally의 e3Prepare discard (`app_state.dart:495–511`). E4는 후속 별도 경계 |

`e3Readback` enum 이름(`F:mobile/lib/src/diagnostics/logical_cost.dart:11`)만으로 readback stage event가 있다고 주장하지 않는다. 실제 원 경로의 readback은 **e3Commit scope 안**이다. post-COMMIT fault 경계와 실제 query를 이용해 외부 subregion으로 분리할 수 있을 뿐 기존 enum이 자동 계수한 것은 아니다. `SegmentedPublication.transactionMicroseconds/readbackMicroseconds`는 제품 Stopwatch 값이며 작업량 counter가 아니다.

## 4. lease·GC·refcount 호출 그래프

| 경로 | 실제 처리 및 부기 범위 |
| --- | --- |
| lease 발급 | HTTP `Adapter.dispatch` → worker `prepare` → `ObservationRepository.create` (`F:backend/isolated_sync/http.py:134–168,178–213`) → 같은 `_connection` metadata transaction → credential/current/versions/expiry/quota → observations·5개 pin INSERT·budget·lifecycle → 마지막 guard·commit (`observation.py:260–287,384–507`) |
| pin/refcount | `sync_observation_pins` trigger → `sync_retention_roots` INSERT/DELETE → `sync_gc_counts.pins` 증감. object/edge INSERT/DELETE → incoming 증감 및 fence 변경 (`retention_schema.py:44–105`). 금융 row refcount나 Python 객체 reference count가 아님 |
| generation 부기 | `FinalizationConnection.finalize` → changed tree/index persist·row/edge write·current switch (`finalization.py:223–318`, `store.py:46–67`) → 같은 root/edge/count trigger. D1/D2와 D3 request 합계를 합쳐 단일 요청 비용으로 만들지 않음 |
| transfer | HTTP worker → `TransferRepository.acquire` → `_lookup`·원 lease 검사 → `PathResolver.resolve`의 실제 path별 Store.get/view read → 응답 materialize → prefix 정리 → terminal lease/auth 검사 (`transfer.py:170–224,341–389`) |
| terminal 재검사 | `Adapter.terminal` → 별도 `repo.lookup` (`http.py:170–176`); prepare 단계 성공 metrics만으로 이 추가 lookup 비용까지 포착했다고 하지 않음 |
| release | client `IncrementalFetcher.release` → DELETE → `dispatch_release/prepare_release` → `RetentionRepository.release/_release` → idempotent retired·5개 pin 비활성화·lifecycle (`fetch.dart:236–248,412–446`; `http.py:230–274`; `retention.py:59–112`) |
| expiry | `_check_lease` → `_retire_expired`의 UPDATE RETURNING (`observation.py:307–328`). retirement는 즉시 pin release와 다름. 오류 시 `_connection`이 attempt를 rollback하고 확정 retirement만 재기록할 수 있음 (`260–287`) |
| renewal | 같은 lease TTL을 연장하는 API가 아님. cold continuation의 `renew`는 새 observation·명시 Ref 재사용과 기존 release를 수행 (`fetch.dart:479–609`), attempts/observations 최대3 유지 |
| 명시 lifecycle maintenance | `RetentionRepository.maintain` → lifecycle/replay 조회·release/reclaim·prune (`retention.py:114–176`). release 개수 limit이 있다고 선행 fetchall의 읽기까지 같은 크기로 제한됐다고 추정하지 않음 |
| 명시 immutable GC | `Collector.collect` → `mark` → 전체 objects/rows/edges/counts와 reachability 검증 → `sweep` → bounded delete·후속 mark (`retention.py:201–397`). 실제 visited_objects/traversed_edges·mark/sweep 시간은 이 호출의 진단값 |
| mobile pin/cleanup | prepare root pin, discard generation cascade·pin_deletes (`store_publication.dart:343–357,491–519`), recovery의 `_pruneUnselected` (`581–591`), 명시 staging cleanup의 NOT IN SQL (`store.dart:655–664`). recursive DELETE 보호 trigger (`store_publication.dart:638–650`)도 검토 범위 |

GC를 동시 실행했다는 근거가 없는 정상 interval에 임의의 maintenance 비용이나 interpreter `gc.callbacks`·Python reference count 비용을 붙이지 않는다. 반대로 collector가 요청 handler만 추적하고 maintenance나 native tail을 놓치면 ‘GC 0’을 제출할 수 없다. 명시 cleanup이 실제 정상 경로에서 호출되는지는 event로 식별해야 하며 SQL 이름만 보고 무조건 bounded라고 판정하지 않는다.

## 5. 이용 가능한 관측 경계

[existing-seam-inventory.json](benchmarks/t69-pre05/existing-seam-inventory.json)에 각 경계의 caller/callee·빈도·context·counter/clock·직접 귀속·sampling·source/certification 영향·동시성·교란을 기록했다.

| 경계 | 분류 | 정확한 지원과 한계 |
| --- | --- | --- |
| 기존 LogicalCost/SQL-write | **AVAILABLE AND SUPPORTED** | `F:mobile/lib/src/diagnostics/logical_cost.dart:37–72`, `mobile/test/support/logical_cost_sqlite.dart:94–154,312–440`; 단계별 실제 hash/primary span·SQL statement/bind·NEW row payload. work.add/SELECT read 계수는 없음 |
| SegmentedWork 공개 snapshot | **AVAILABLE AND SUPPORTED** | `work.dart:1–11`, `store.dart:105`; 실제 operation 합계의 비변경 조회만 지원. work가 내부 final이므로 교체·subclass 주입 seam은 없음 |
| Dart 외부 Zone 경계 | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION** | 원 `LogicalCost.run/at`가 공개 `runZoned`를 사용. 외부 부모 Zone의 `run/runUnary/runBinary`에서 실제 단계의 동기 실행 조각을 감쌀 수 있음. 기존 collector에 임의 callback 등록 API가 있다는 주장은 아님 |
| 진단 DB factory | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION** | `store.dart:111–129`가 명시적으로 `Database` factory를 받음. 원 CostDatabase를 유지한 select 측정 확장은 외부 파일에서 가능. COMMIT execute 경로를 새로 감싸는 방식은 채택하지 않음 |
| 기존 StoreFault | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION** | `store.dart:57,113`, `store_publication.dart:332–359,389–446`; 특히 COMMIT 후 두 지점의 동기·비변경 snapshot으로 readback을 분리할 수 있음. fault로 authority/cache/DB를 바꾸는 collector는 허용하지 않음 |
| backend B03 context·SQL-write | **AVAILABLE AND SUPPORTED** | `F:docs/benchmarks/t66f-b03/counters.py:605–681,951–979,1063–1144`; request-local ACTIVE 및 worker hold. SELECT 반환행·루프 방문 수는 수집하지 않음 |
| D3 metrics callback | **AVAILABLE AND SUPPORTED** | `http.py:200–212`, `transfer.py:384–389`; successful prepare의 object/path/byte·구간 시간. 실패 전 partial 작업이나 별도 terminal lookup·GC의 완전한 경계가 아님 |
| repository.metrics | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION** | `observation.py:258,396,497–502`의 공유 mutable dict는 동시 create마다 재설정됨. 이를 request-local 완전 증거로 사용하지 않음 |
| GC 반환 진단 | **AVAILABLE AND SUPPORTED** | `retention.py:319–320,374–397`의 명시 maintenance 결과. 요청 밖 결과를 E3에 귀속하지 않음 |
| Python legacy trace/profile | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION** | `counters.py:108–258`가 기존 trace/profile의 entry 인계·실패 복구를 명시 지원. 새 read-only `sys.settrace` collector의 event 완전성과 thread/ContextVar 귀속은 별도 자격 필요 |
| PEP 669 local-only | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION** | global mask=0·소유권 entry code local mask=0이고 다른 product code에만 local event를 설정한 안정 구성이 preflight와 양립. 이번 선택 경로에는 새 PEP 669 tool이 필요하지 않음 |
| global/entry PEP 669 observer | **UNSUPPORTED** | 모든 ID0..5를 이름과 무관하게 검사하여 global 또는 entry-local 활성 mask면 거부 (`counters.py:123–140`). 이를 끄거나 getter를 바꾸어 우회할 수 없음 |
| SQL trace/authorizer/progress | **AVAILABLE BUT REQUIRES INDEPENDENT QUALIFICATION / UNSUPPORTED** | 공개 trace는 statement 사건일 뿐 행/edge 방문 증거가 아님. 새 callback 설치·기존 hook 보존은 별도 설계 필요. 기존 authorizer 교체나 native handle 사적 변경은 지원 경로로 인정하지 않음 |
| 내부 work event/stage·새 trigger | **REQUIRES NEW INSTRUMENTATION** | `work.add`에 callback/stage를 추가하거나 생성부·B03 UDF/trigger를 바꾸면 원 payload가 달라짐. 외부 경로가 있으므로 현재 필수라고 결론 내리지 않음 |

시간/통계 sampling은 한 번의 금지 full scan이나 rollback 경로를 놓칠 수 있다. 직접 0·완전성 주장에는 대상 경계의 **전수 포착**이 필요하다. stack sampling, process CPU/RSS, E3 Stopwatch만으로 직접 작업량을 대체할 수 없다.

## 6. 직접 귀속 coverage와 외부 관측의 정적 설계

선택 경로는 **원 계측 유지 + Dart 공개 Zone 경계 + 기존 post-COMMIT fault + 공개 factory의 SELECT 관측 + Python legacy trace**다. 새 collector는 작성하지 않았다. 정적 연결 근거는 `F:logical_cost.dart:47–55`, `S:zone_api.dart:159–165`, `S:zone_specification.dart:28–39,162–245`, `S:future_impl.dart:218–243`이다. 해당 SDK의 Future value/error callback은 Zone의 unary/binary 실행을 사용한다. 이것을 실제 compiled async continuation 전체의 실험적 보증으로 확대하지 않는다.

1. Dart 관측기는 특정 store와 collector에 결합한 외부 부모 Zone을 소유한다. 세 실행 handler의 **target zone 안에서 위임된 동기 body**를 감싸고 공개 `LogicalCost.activeStage/activeCollector`와 `store.work.snapshot()`을 읽는 설계다. handler 자체의 `Zone.current`를 target으로 오인하거나 private `_key/_CostScope`를 읽고 바꾸지 않는다. SDK도 handler에서는 전달된 zone/delegate를 사용하도록 명시한다.
2. 각 동기 조각의 시작/종료 counter 차분을 그 조각의 실제 stage에 귀속한다. await 대기 동안 다른 요청이 한 작업을 포함하는 긴 Future interval 차분을 사용하지 않는다. 중첩 조각은 stack으로 구별하여 자식 증가량을 이중 합산하지 않는 보존식이 필요하다. 이것은 operation 전체에서 E2·recovery를 빼는 잔차 추론과 다른, 실제 실행 경계에서 읽은 counter다. 보존식과 전수 포착을 입증하기 전에는 직접 E3 0을 주장할 수 없다.
3. 원 `CostDatabase.execute`·TEMP UDF·transaction 처리를 그대로 사용한다. 공개 factory에서 원 class의 execute를 상속하고 SELECT 결과의 이미 반환된 길이·query 분류만 추가 관측하는 외부 형식은 가능하다. 이 경로는 새 SELECT collector 자격을 얻었다는 뜻이 아니며 일반 SQL rows-read 도구를 구현하는 작업도 아니다. prepared/native 우회가 대상 경로에 나타나면 미관측으로 표시해야 한다.
4. `after_publication_commit`와 `during_publication_readback`의 기존 post-COMMIT callback에서 비변경 counter 경계를 잡는다. 원 e3Commit 내부의 readback query·work·bytes를 외부 subregion으로 표시할 수 있다. readback 완료는 동기 commit body의 정상 반환으로 확인한다. 예외면 post-COMMIT 실패를 기록하고 성공0으로 바꾸지 않는다.
5. backend는 공개 `sys.settrace`의 call/line/return/exception 사건과 공개 frame 조회를 이용해 **실제로 실행된** pin/release·lease 검사·Store read·GC 진입 및 루프/이미 materialize된 행 집합의 경계를 source별로 분류할 수 있다. product 함수나 `_cost_row`를 monkeypatch하지 않는다. SQL 내부 native VM 행 방문은 이 방식이 제공하지 않으며 별도 T35-ROWS 자격을 수용했다고 하지 않는다. [Python 공식 trace 계약](https://docs.python.org/3.12/library/sys.html#sys.settrace)과 원 entry handoff가 이 후보의 근거다.
6. trace는 새 worker가 생기기 전에 공개 thread trace 설정을 고정하고 B03 ACTIVE의 owner/stage 및 실제 thread별 집계에 연결해야 한다. 요청 취소 뒤에도 원 `finish_when_idle()`까지 기다려 native tail을 포함한다. runtime에서 thread나 event가 누락되면 미완결이며 현재 세션은 이러한 설정을 수행하지 않았다.

| 증거 항목 | 기존만으로 수용 | 외부 경로의 정적 coverage |
| --- | --- | --- |
| E3 단계 hash/primary/SQL NEW bytes | 해당 metric 범위는 있음; 의무 전체는 불가 | 원 stage 계수 유지, SELECT·work를 별도 연결 |
| E3 다섯 full counter·tree/index/row work | operation aggregate만 있음 | 동기 Zone 조각의 stage-counter 경계로 **조건부 가능** |
| pin/CAS/actual readback | 원 DML·work·storage 검사·시간 존재 | 기존 post-COMMIT 경계와 SELECT·원 DML 결합으로 **조건부 가능** |
| lease 발급/검사/retirement/release/새 observation | D3 성공 지표·SQL-write 일부 | 실제 Python 경로/반환·실패·sticky retirement와 trigger 결과 결합으로 **조건부 가능** |
| GC와 refcount의 정상 귀속 | 명시 GC 결과·trigger DML 일부 | 요청·maintenance 별 실행 진입/방문과 기존 DML을 연결하면 **조건부 가능** |
| flat P 부재 | 원 control 생성 source로 확인 가능 | actual control의 구조·길이와 해당 경로 방문을 결합; 새 field/불명 경로면 fail-closed |
| 정상 N100k / 독립 acceptance | 없음 | 여전히 없음. source/runtime/baseline·자격·실행 GO가 별개 |

원 control 생성은 `F:backend/isolated_sync/observation.py:426–440`의 고정 descriptor/metadata 구조다. bytes 크기만 작다는 이유로 flat P 부재를 증명하지 않는다. [direct-attribution-coverage.json](benchmarks/t69-pre05/direct-attribution-coverage.json)은 현재 결측과 후보 경계를 분리한다.

## 7. E3 guard-to-COMMIT 안전성

**PRESERVED — STATIC.** 원본 `store_publication.dart:439–440`은 마지막 guard 반환 직후 같은 동기 stack에서 COMMIT을 실행한다. 원 AppState lineage lock의 대기는 action 진입 전이며 action 결과에 대한 await는 동기 commit/readback이 끝난 뒤다(`app_state.dart:486–493,2598–2609`). guard의 session 확인도 원 동기 getter다(`transport.dart:92–95`).

선택 설계의 Zone observer는 동기 body 진입 전과 반환/예외 후에만 실행한다. 이 두 문장 사이에는 별도 Zone 진입, await, store fault 지점이 없다. readback 경계 callback은 이미 COMMIT 뒤에 있다. 새 database execute override·commit hook·UDF·progress handler·query/lock·authority callback 감싸기는 선택 경로에서 제외한다. 따라서 새 관측을 넣기 위해 그 critical sequence를 바꿀 정적 필요가 없다.

원 B03 `CostDatabase.execute/_call` 자체의 기존 계수·native dispatch는 IR07 범위의 원 경로다. 이를 새 SQL observer callout을 추가할 허가로 해석하지 않는다. private connection의 authorizer/UDF/transaction 설정도 바꾸지 않는다. `before_publication_commit`은 guard 이전이라 기존 위치에서 기록은 가능하지만, 선택 경로는 그 callback을 새 lock/DB 접근에 사용하지 않는다.

비변경 관측도 CPU·할당·JIT·GC·TTL·lock 대기 시간을 바꿀 수 있다. Zone snapshot과 trace 때문에 timeout 또는 guard 실패가 늘면 그 실패가 실제 결과다. guard를 생략하거나 TTL을 연장하지 않으며 observer 시간을 사후 임의 차감해 성공을 만들지 않는다. runtime qualification에서 실제 sync commit 경로에 새 scheduling/callback이 없고 원 authority 반례가 유지되는지 확인해야 한다.

## 8. PEP 669와 외부 관측기 양립

원 preflight는 `F:docs/benchmarks/t66f-b03/counters.py:123–140,246–257`에 있다. ID 이름과 무관하게 global mask 또는 현재 ownership entry code의 local mask가 nonzero이면 명시 미완결로 거부한다. [IR07 34–44행](t66f-b03-ir07-independent-pep669-closure.md:34)은 안정 구성에서 다른 code에만 있는 local events와 기존 legacy trace/profile 인계를 구별해 검증했다. `free_tool_id`는 event/callback 해제가 아니다. [Python 공식 monitoring 문서](https://docs.python.org/3.12/library/sys.monitoring.html#sys.monitoring.free_tool_id)도 이 점을 명시한다. 현재 온라인 3.12 분기 문서는 3.12.16이며 원 실행 자격인 3.12.3과 구별했다.

선택 설계는 **새 custom PEP 669 tool을 요구하지 않는 legacy trace**다. B03는 legacy trace/profile을 reserved interpreter 경로로 구별하며 entry return callback이 실패하면 획득·stage를 복구한다(`counters.py:108–258`). 이것은 임의의 새 trace collector가 IR07에서 검증됐다는 뜻이 아니다. 설치 시점·thread 전달·기존 hook 복원·callback 예외·중첩·native tail의 새 독립 qualification이 필요하다.

다른 product code에만 안정된 PEP 669 local event를 두는 대안도 API 수준에서는 가능하지만 선택하지 않았다. global event나 entry-local event를 활성화하는 관측기는 원 preflight에서 거부된다. local-only 후보도 global-only exception/unwind 사건을 조용히 요구해서는 안 된다. 실패 coverage를 입증하지 못하면 이 대안의 증거는 미완결이다. getter 교체, ID 해제로 활동 은폐, 진입 후 설정 변경, ABA를 안전한 지원 seam으로 제안하지 않는다.

새 외부 collector의 source/harness identity·monitoring 설정은 원 B03 payload와 **별도로** 기록해야 한다. IR07는 원 source와 지원 환경의 원 계측만 인증했다. 원 byte/SQL 지표의 역사적 정확성을 폐쇄 상태로 유지하면서 새 observer의 추가 지표와 overhead는 독립 심사한다. B01–B03 전체 감사를 다시 여는 근거는 발견하지 않았다.

## 9. blind spot과 필요한 자격 증명

| 경우 | 놓칠 수 있는 내용 | 이후 소형 oracle가 입증해야 할 것 |
| --- | --- | --- |
| E3Verify의 await/중첩 | Future 전체 차분의 다른 stage 혼입, unary/binary 누락 | sync·async success/error·중첩 continuation에서 각 실제 증가를 한 번만 귀속; 관측되지 않은 구간은 명시 미완결 |
| COMMIT 전 guard/SQLite 실패 | partial tree/fact 작업·rollback, finally discard | 시도/효과/rollback과 미도달 counter 구별; accepted 불변 및 e3Prepare cleanup 별도 귀속 |
| COMMIT 후 readback/authority 실패 | 이미 durable한 publication을 rollback으로 오기록 | 원 `PublicationCommittedException`·accepted pointer/pins 보존·readback 실패 상태 유지 |
| no-change | accepted_writes=0을 publication 실패로 오인 | 정상 완료와 기존 ID/sequence 보존, temporary prepared pin/discard의 실제 작업을 따로 포착 |
| lease expiry/새 observation | retirement와 pin release 혼동, retry 누락 | sticky retirement replay, 반복 release idempotency, 새 lease의 identity·원래 한도와 이전 비용 모두 보존 |
| 요청 밖 maintenance/GC | handler trace에 없어 GC0으로 오판 | 실제 maintenance 진입·full graph 방문은 별도 scope에서 비0; 정상 scope의 미호출을 전수 확인 |
| secondary refcount | edge/root/current switch·cascade trigger의 변경 누락 | known graph의 insert/delete/repeated pin/release·rollback을 native 상태와 원 SQL DML로 독립 대조 |
| native 취소·exception cleanup | HTTP 종료 후 worker rollback/release·trace tail 누락 | 원 job hold와 `finish_when_idle`, failure/late event·scope 종료를 실제 완료까지 대조 |
| concurrent 요청·store | repository.metrics 공유, owner 혼동·중복 | 두 owner/thread/store의 서로 다른 literal 입력이 섞이지 않고 nested 보존식이 성립; observer 상태는 task-owned·유한·종료 후 고정 |
| SQL/native 우회 | SELECT ResultSet 포착으로 내부 VM scan까지 주장 | 실제 반환/이미 소비된 행·source loop와 native VM/pager 미관측을 구별; 지원 밖 API면 거부 |
| control/cleanup | fixed-shape 가정, recursive DELETE/NOT IN 경로 누락 | actual control 구조·query 경로 분류, 명시 cleanup과 정상 경로를 구별; 금지 경로가 나타나면 성공0 제출 거부 |
| observer 자체 실패·메모리 | snapshot/trace 예외·재진입·무한 frame 보존 | callback에서 DB·authority 변경 없음, raw/frame 보존 없이 유한 집계, collector 실패는 별도 미완결, 원 예외를 숨기지 않음 |

Python trace는 thread별 콜백이며 ContextVar를 무시한 process-global current request로 바꿀 수 없다. 이벤트에서 collector의 lock을 재진입하거나 native worker lock을 잡는 설계도 채택하지 않는다. frame/원문을 계속 저장하면 수명과 메모리를 바꾸므로 해시·숫자 집계만 남기는 유한 설계가 필요하다. elapsed time의 겹침은 inclusive 구간으로 공개하며 중첩 시간을 더해 순수 CPU로 표현하지 않는다.

## 10. source 인증 영향

| 구분 | 처분 |
| --- | --- |
| A. 기존 B03만 사용 | 원 자격은 유지하나 두 I25 의무의 직접 coverage는 불충분 |
| B. 외부 collector | 원 파일·제품 source·engine은 유지 가능. 별도 harness/build·runtime 구성·추가 event 의미와 overhead에 대한 독립 자격 필수 |
| C. 기존 DB/structured seam | 원 UDF/trigger·transaction을 그대로 활용할 수 있으나 새 SELECT 관측은 별도 자격. SQL trace만으로 모든 행/graph 방문을 증명할 수 없음 |
| D. 수정 실험 source | 현재 필요하다고 확정되지 않았고 구현 권한도 없음. work callback/stage·원 wrapper·trigger·guard 변경 시 새 payload SHA, backend 입력 변경이면 새 engine SHA, 실제 collector/build identity 및 영향 재자격 필요 |

다른 source의 결과는 [§35-T69 743행](t66/c/t66c-delta-sync-protocol.md:743)에 따라 그 source의 주장만 성립시킨다. 원 B03 의무를 대체하지 못한다. 원 source 무변경 외부 경로의 qualification이 실패하더라도 즉시 내부 hook을 구현하거나 규범을 바꾸는 권한은 생기지 않는다. 해당 실패 증거로 차단을 유지해야 한다. 인증 범위는 [qualification-boundaries.json](benchmarks/t69-pre05/qualification-boundaries.json)에 명시했다.

## 11. 정적 가능성 판정

**B — EXTERNAL OBSERVER FEASIBLE — QUALIFICATION REQUIRED.** 함수명이나 wall time만을 근거로 한 판정이 아니다. 원 public snapshot·activeStage·DB factory·기존 post-COMMIT hook과 실제 SDK의 위임 경로, 원 Python legacy trace 인계 구현을 확인한 결과다. 이 조합은 critical sequence 안에 새 관측을 넣지 않고 필요한 실제 경계에 접근할 수 있으므로 C의 ‘새 source 계측이 필수’나 D의 ‘source/규범 불명으로 판단 불가’에 해당하지 않는다.

**기존 자격만으로 충분하다는 A는 거부한다.** `SegmentedWork`는 event subscriber가 없고 기존 합계에는 직접 stage가 없다. 원 SELECT wrapper는 반환행을 세지 않는다. 성공 prepare metrics는 실패·terminal lookup·maintenance 전부를 포함하지 않는다. 새 관측기의 구현·오라클·실제 완전성을 만들지 않았으므로 E3/lease/GC/refcount 직접 관측은 모두 **CONDITIONAL**, 두 I25는 **UNACCEPTED**다.

이 정적 PASS는 PRE04의 B1 중 **무변경 seam의 가능성**만 진전시킨다. observer qualification, N100k baseline0·취득/자원 가능성 미확립, r/U/q와 실행 GO 차단은 남는다. 식별된 보존 입력에서 N100k accepted baseline은 복구 불가라는 [PRE03 판정](t69-pre03-100k-baseline-recovery-feasibility.md:176)을 유지한다. 다른 여섯 이관 의무도 수용하지 않았고 총 **0/8**이다. [next-action-decision.json](benchmarks/t69-pre05/next-action-decision.json)은 정적 가능성과 실행 권한을 별도 필드로 기록한다.

## 12. 하나의 좁은 다음 행동

**PRE05-Q01: 원 B03을 유지하는 외부 경계 관측기의 소형 합성 oracle·단계별 보존식·guard 보존·실패 완전성만을 대상으로 한 독립 자격검증 계획을 별도 정적 심사에 제출한다.**

이 한 작업의 범위는 위 선택 경로로 고정한다. 계획은 literal counter가 알려진 작은 sync/async 중첩 구간, 작은 fixed graph의 pin/edge/release, 명시 recovery/maintenance의 비0 대조, COMMIT 전후 실패·취소·두 owner/native tail, 원 byte/SQL oracle와 source 전후 SHA를 연결해야 한다. 전체 benchmark·N100k·취득·복원·HTTP/framing·gzip·일반 SQL rows-read 도구 제작은 포함하지 않는다. 실행 자격 시험의 실제 구현·실행에는 별도 범위와 허가가 필요하며 PRE05는 이를 부여하지 않는다. 이 계획이 요구한 runtime 사건을 포착하지 못하면 불완전 결과로 차단하는 종료 조건도 고정해야 한다.

## 13. Git·source·artifact 보존

시작 index 원문 SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, `git ls-files --stage -z` SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. 시작 staged diff는 비어 있다. 기존 수정 12개 및 기존 미추적 자료를 포함한 6,568개 파일의 SHA/mode를 시작점과 종료점에서 대조했다. 전후 결과와 원 index identity는 [preservation.json](benchmarks/t69-pre05/preservation.json)에 있다. 원 frozen sidecar·archive도 전후 일치한다.

PRE05의 새 파일은 이 한국어 보고서와 `docs/benchmarks/t69-pre05/` 안의 JSON 증거뿐이다. 필수 6개 JSON 외 source identity·보존·정적 검증 기록을 추가했다. report/schema·참조·정적 source/승인 hash 대조만 수행했다. 사용자 지정 정적 전용 범위에 따라 npm build·backend/Flutter suite·benchmark·profiling·acquisition·restore는 실행하지 않았다. 새로운 observer 코드·제품 import·SQLite 연결·측정 run은 모두 0이다.

기본 sandbox는 `bwrap: loopback: Failed RTM_NEWADDR`로 명령 실행 전에 실패하여 승인 검토된 셸 경로로 정적 파일 검사를 수행했다. 자동 승인 거부는 없었다. Git reset/stash/clean/checkout/rebase/restage/commit/push, production 접근·restart/migration/deploy는 하지 않았다. 임시 파일은 정적 archive reader·문서 hash 검증기·시작 보존 snapshot뿐이며 영구 JSON으로 필요한 증거를 옮긴 뒤 task-owned 파일만 정리했다. 큰 실험 산출물 정리는 **NOT APPLICABLE**이다. 검증 결과는 [static-validation.json](benchmarks/t69-pre05/static-validation.json)에 있다.

Phase B 행정 종결은 COMPLETE — EVIDENCE TRANSFERRED, formal T6.6F closure는 NOT AUTHORIZED, real-device gate는 DEFERRED, R1 activation은 CLOSED, production deployment는 NOT AUTHORIZED를 유지한다.
