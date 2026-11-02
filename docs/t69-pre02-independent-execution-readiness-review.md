# T6.9-PRE02 — 이관 증거 실행 준비에 대한 독립 사전 감사

**최종 판정: PARTIAL — REQUIRED BASELINE OR METRIC QUALIFICATION UNRESOLVED. 실행 준비는 NOT READY, 실행 권한은 NOT GRANTED다.** 승인된 8개 의무와 원 B03 기준선은 확인했다. 현재 실행에서 적법한 N=100k accepted baseline을 만들 수 있는 지원 경로와 필수 직접 계측의 자격은 확인되지 않았다. 최소 표본의 정확한 수와 자원 상한 안의 완료 경로도 미확정이다. 문서 검증 성공은 측정 실행의 허가가 아니다.

## 1. 독립성·시작 상태·검토 범위

제공된 새 세션 이력상 PRE01 계획, B01–B09 구현, B11 작성·적용에 관여하지 않았다. 구현 비참여 독립성은 **SATISFIED**다. 외부 개인 신원이나 UI의 reasoning 설정을 인증하는 판정은 아니다. 다른 agent에게 위임하지 않았다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, 브랜치는 `main`으로 예상값과 같다. 시작 staged 변경은 0개지만 인덱스에는 2,693개 path/mode/blob/stage 항목이 있다. 그 전체 목록과 인덱스 원문 SHA `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`를 [시작 보존 기록](benchmarks/t69-pre02/preservation-start.json)에 저장했다. 이는 PRE01 종료 시점의 인덱스 SHA와도 같다. 기존 tracked·비무시 untracked 6,518개 경로의 내용·길이를 기록했다. 기존 dirty source와 미추적 증거는 그대로 보존 대상이다.

검토는 문서·JSON·고정 archive의 메모리 내 정적 읽기, 해시·구조 검사에 한정했다. 제품 import, DB 개방·복구·acquisition, API, 벤치마크, npm/backend/Flutter 시험, 장치 작업은 수행하지 않았다. 사용자 지정 무실행 범위가 AGENTS의 일반 build·backend 검증 권고보다 우선한다. 샌드박스의 bwrap loopback 초기화 오류 뒤 승인 검토된 문서 읽기·자기 산출물 쓰기만 사용했으며 자동 승인 거부는 없었다.

## 2. 적용할 규범과 승인 원문

규범은 [C 명세](t66/c/t66c-delta-sync-protocol.md)의 **§34-B11, §35, §35-T69, §36 I25, §38.7–12**와 [B 설계](t66/b/t66b-hot-cold-design.md)의 **§27 및 §29 승인 추가문**이다. 현재 C SHA는 `5d3f03a0e61c6d504cf8efd5de0c8ee446b9c0a0b4a45a367f6d366a4fbf94c9`, B SHA는 `e2d820ba71018414934ad4a9b3667961c209f93fe0b5b5dd2d0a3233ea76b279`다.

[승인 결정](benchmarks/t66f-b11-application/authorization-decision.json)의 원 제안 보고서 SHA `11fd8fc6d0f97dabe6570da9dce1f5190f6ca93287ca50a5e3b408fc3a871569`, 원 개정 기록 SHA `21babe57c9fb6ce617a7a81e48fb40c8e488b708f55158c2e720f5b208d409db`, 책임 보충안 SHA `08a19797823c5bffb8b2abd99be0397e9ba6663425d37514de1b9e55c4b42844`를 실제 파일로 재검증했다. 승인된 GOV01/GOV02/REF01을 반영한 AM01–05 각각의 exact 추가문과 현재 원문이 일치한다. 초안의 개인 기명 요구를 다시 적용하지 않는다. 보충안 파일의 당시 DRAFT 표시는 후속 명시 승인과 실제 적용 기록을 대체하지 않는다. 사용자 메시지 시각의 미기록 값을 새로 만들지 않았다.

[독립 검증 기록](benchmarks/t69-pre02/source-and-approval-verification.json)의 914개 검사는 source·승인 bytes·identity 검사다. runtime 성능이나 8개 의무의 독립 수용 검사 수가 아니다. [승인 적용 보고서](t66f-b11-approved-amendment-application.md)와 [승인 후 종결 재판정](t66f-b11-post-amendment-closure-readjudication.md)의 처분을 그대로 따른다.

| 구분 | 현재 구속 상태 |
| --- | --- |
| Phase B 행정 종결 | COMPLETE — EVIDENCE TRANSFERRED |
| Phase B 정량 증거·다섯 점 | INCONCLUSIVE / PARTIAL |
| 이관 8개 수용 | **0/8**, 모두 필수 증거 대기 |
| formal T6.6F closure·최종 T6.9 | NOT AUTHORIZED / BLOCKED |
| 실행·독립 수용·최종 승인 역할 | T6.9 구현·측정 워크스트림 / 해당 구현·측정 비참여 별도 T6.9 감사 세션 / 프로젝트 소유자 |
| 완료 기한 | formal F exit 재심사와 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전 |
| R1 사용자 활성화·rollout·production | 계속 차단, 별도 명시 승인 필요 |

저장소 문서명·관련 문서 참조 범위에서 별도 승인 상세 T6.9 명세를 확인하지 못했다. 이관 인수 계약은 C §35-T69다. B §27/29의 confirmed-heavy·한 달 hot 대량·initial/full/restore/crash 및 비이관 whole-F 의무를 이 8개에 흡수하거나 면제하지 않는다. B10의 S35/I25/P7/P12와 위험 RR01–RR08은 당시 판단으로 보존한다. 승인 이후 달라진 것은 행정 처분이며, B10의 당시 Option D나 정량 실패를 고치지 않는다.

## 3. 8개 의무의 정확한 연결

아래 ID는 B11 추적명이며 원 규범 ID를 대체하지 않는다. 상세한 필수 상태·비교군·계측·실행 종속성·독립 수용 기준은 [의무별 검토 JSON](benchmarks/t69-pre02/normative-coverage-review.json)에 기록했다. 모든 행의 source는 §5의 원 B03, 정상 증거의 상태는 **B03 ON**이다. OFF는 ON 완료 cell의 대체가 아니다.

| ID | 정확한 현행 근거 | 필수 증거·규모 | 기존 적격 범위와 결측 |
| --- | --- | --- | --- |
| T35-100K-NC | C §35-T69 제1항, 722행; §35 | N100000 no-change 반복, rows·hash/validation/write bytes·HTTP/RTT·memory·median/p95, D1–D3/E1/E2/E3 각 단계/E4 분리 | B04 N100k cell 없음. 적법 base 위 정상 ON 완료·무변경 ID/sequence 유지와 E4 필요 |
| T35-100K-CARD | 같은 제1항 | 같은 N의 card D1 반복 및 실제 accepted generation 전진·모든 비용 | 미측정. B02 기능·다른 source·prepare/discard는 대체 불가 |
| T35-100K-CASH | 같은 제1항 | 같은 N의 cash D1 반복 및 accepted 전진·모든 비용 | 미측정. 같은 조건의 직접 정상 증거 필요 |
| T35-ROWS | C §35-T69 제2항, 723행 | 1k/5k/10k/50k/100k × 세 workload의 실제 SQL·반환 행·raw/index lookup·query plan 완결 | 하위 ON36의 byte/write·operation 일부 유효. SELECT 반환 event 및 완전한 read 경계 결측 |
| T35-NET | C §35-T69 제3항, 724행; §35 | 같은 15 cell의 method/path·금융/auxiliary·양방향 entity·decoded·실제 base64/JSON framing·headers·RTT dependency/cache와 full 비교 | 기존 entity/count/일부 시간 유효. 실제 header/body 분해·의존 경계·matched full 결측 |
| T35-GZIP | C §35-T69 제4항, 725행; B §27 | 같은 source/state/Context/fixture full authoritative gzip 비교, representative/less-repetitive, codec/network/parse/validation/write 분리 | 역사 offline codec 자료는 그 범위만. 새 matched 경로와 다양성 fixture admission 결측 |
| I25-E3-100K | C §35-T69 제5항, 726행; §36 I25; §25 | N100k 세 workload의 E3Verify/Prepare/Commit rows/bytes·SQL·tree/index/pin/CAS/readback 및 5종 full counters=0 직접 귀속 | stage byte 계수와 aggregate work는 존재. N100k 정상·직접 stage work 귀속 없음 |
| I25-BOOKKEEPING-100K | C §35-T69 제6항, 727행; §16; §38.7 | 같은 정상 D/E의 lease/GC/refcount/root-pin/transfer 직접 작업량과 hidden full scan·flat P 부재 | 원 DML/D3 일부 계수 존재. 정상 부기 read/visit·단계·N100k 증거 결측 |

각 행에 숫자로 정해진 최소 표본 수는 없다. **반복 의무 자체는 유지**된다. §35-T69 731행은 표본 수를 발명하지 말라고 명시하고, 733행은 warmup/n/median/p95 estimator/IQR와 교란·메모리 한계의 공개를 요구한다. 그러므로 n=3을 강제 최소라고 부르거나, N100k 단발 n=1을 반복 완료라고 부를 수 없다.

모든 의무에는 source/runtime/fixture·complete accepted baseline의 독립 admission, 실제 authenticated D3→HTTP/TLS→Flutter E2/E1→원 AppState E3 accepted publication/readback→E4가 필요하다(§35-T69 735·737행). rows/bytes의 일부 커버리지는 의무 전체의 독립 수용과 다르다. 정상 full history fetch/hash/serialize/write 0, flat P 부재, bounded leaf/path/affected index를 source와 직접 계수로 확인해야 한다. wall-time 곡선이 평평한 것만으로 I25를 수용하지 않는다.

## 4. 정확히 재사용할 수 있는 증거

[재사용 검증 기록](benchmarks/t69-pre02/evidence-reuse-verification.json)은 각 원 raw의 경로·SHA·길이·mode·N/workload/trial·계측 상태와 허용 범위를 개별 기록한다. PRE01의 필수 JSON 6개와 static-validation을 읽고 실제 raw로 재대조했다. PRE01 정적 검사 190개는 모두 성공 기록이지만 실행 수용이나 준비 완료 판정은 아니다.

| 증거 | 재사용 범위 | 수용하지 않는 확대 해석 |
| --- | --- | --- |
| B04 `raw/n1000-v3`, `n5000-v3`, `n10000-v3`, `n50000-v3` 정상 ON36 | 실제 hash sink·primary span·stage SQL NEW payload·operation work·기존 HTTP 집계·HOST 시간/RSS·원 accepted/E4. 각 cell n3 | SELECT read 완결·새 header/framing·직접 E3 full-work 단계·N100k 수용으로 승격 불가 |
| 같은 정상 OFF36 | 원 구성의 paired timing·값/Target/상대 sequence 동등성 | 새 observer 비용이나 ON 논리 counter의 대체 불가; OFF null은 0 비용 아님 |
| B04 cold ON4/OFF4 | 당시 initial/cold 범위와 교란·완료, 50k의 두 observation 사용 | 정상 반복에 합산하거나 새 cold 의무를 만드는 근거 아님 |
| B04 기타 publication26·stage discard6 | 진단·각 원 경계의 참고 | 통제 normal accepted 분포에 합산 불가 |
| B04 `artifacts/n*-v3/manifest.json`와 backend/client-ON/client-OFF 압축 사본12 | 현재 압축 파일 SHA 일치, 역사 backup API·graph/value 검증 기록 | 현재 실행의 accepted/provenance admission 아님; DB를 새로 열거나 복원하지 않음 |
| `t66f-phase-b-final/evidence/five-point-grid.json`와 continuation grid | 역사 full 입력 SHA·offline gzip6/Brotli4 각 n20·당시 backend 비용 | 원 B03 matched HTTP·headers·parse/write 비교로 승격 불가 |
| `t66f-b02-independent/summary.json` | 당시 N100k complete400532 객체·D→E/E3/E4·delta/restart의 비계측 기능 완료 | B03 ON 정량·I25 또는 현재 완주 가능성 아님 |
| P03 full-result/full-analysis와 보존 raw5종 | 당시 진행·비용·lease 만료·미완료·자원 사실 | E3/E4 PASS·현재 baseline·matched tail 성공으로 전환 불가 |

정상 72개와 cold8개 모두 원 source digest·완료·collector 종료를 확인했다. 정상 no-change의 ID/sequence 유지, mutation의 sequence +1도 원자료로 확인했다. B04 과거 4점의 통계는 해당 metric의 표본에만 재사용한다. 새 n1 metric과 다른 실행의 시간을 합친 가짜 n3·end-to-end 표본을 만들지 않는다.

## 5. 원본·full 비교군·미래 source의 적법성

| identity | 독립 확인값 |
| --- | --- |
| base commit / tree | `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` / `af2aa70ce6a8cd27c18c134564e31702f0f54f8c` |
| payload | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| engine | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| archive | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |
| 고정 archive 위치 | `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz` |
| 규범 runtime | CPython3.12.3 / backend SQLite3.45.1 / Flutter3.47.4 / Dart3.13.3 / client SQLite3.53.4, 안정된 monitoring |

899개 source의 bytes·길이·mode, 1,067개 archive member의 경로 안전성·중복, baseline Git inventory2,693개를 확인했다. 정렬 entries의 지정 JSON 직렬화로 payload를 재계산했고 archive 내 engine_artifact의 고정 입력98개 SHA map으로 engine을 재계산했다. 원 후보를 추출하거나 실행하지 않았다. 현재 dirty tree를 측정 source로 채택하지 않는다.

**역사 측정 source로서 원 B03의 정당성은 PASS다.** C §35-T69 729행이 이 identity를 직접 지정한다. engine allowlist의 허용 여부로 측정 기준선을 승인한 것이 아니다. B05/B08 최적화는 계속 EXPERIMENTAL — NOT ADOPTED다.

§35의 full 비교에는 같은 원 B03 backend authoritative presenter/serializer와 같은 DB read-view/Context·fixture가 필요하다. 별도 최적화 source/engine으로 바꿀 필요는 없다. 실제 full 응답의 identity/gzip6 전송과 full parser/validator·durable write를 재는 test-only facade는 새로운 **측정 harness**로 독립 자격을 받아야 한다. 전송 replay, 원 backend 응답 생성, codec CPU, parse/validation/write의 시간을 각각 공개해야 한다. facade의 동작을 production gzip 구현으로 표현할 수 없다. 현재 그 구현·자격·runtime binary admission은 없다.

**실행 baseline의 정당성은 PARTIAL이며 N100k admission은 차단 상태다.** 압축 사본이나 금융 값 동등성은 complete accepted/provenance를 증명하지 않는다. §5는 physical backup 복원 및 server cold startup마다 새 epoch를 요구한다. §18/23–25와 §35-T69 735행에 따라 complete objects·11 tables·global index·receipt·NS/principal/Versions/Target·같은 연결의 provenance/generation을 다시 연결해야 한다. 오래된 epoch·accepted pointer·receipt 주입이나 startup 우회는 허용되지 않는다. B04의 하위 4점 backup도 현재 실행에 자동 적법하지 않으며 N100k와 새 다양성 family의 적법 baseline은 제출되지 않았다.

새 instrumented full cold 성공은 독립 MUST가 아니다. 합법 baseline을 확보할 수 있으면 그 위의 원 B03 정상 ON 증거를 수용할 수 있다. 경로가 없으면 수집 차단이며, 새 cold는 기존 NO-GO 및 별도 계획·명시 GO의 대상이다. P05의 원 P03 matched pair 소실 기록을 현재 호스트 전체의 모든 N100k 사본 부재 증명으로 넓히지 않았다.

미래 최종 T6.9 source가 달라지면 해당 source도 평가해야 한다. §35-T69 743행에 따라 별도 채택 승인·exact release/admission·변경 영향 계측 oracle/정확성/구조·provenance·authority fence·durability/legacy 재자격 및 **그 source의 전체 다섯 점**이 필요하다. 호환 proof 없는 validator/schema 변경에는 §23 full revalidation이 적용된다. 미래 결과는 미래 source의 주장만 지지하며 원 B03 8개 결측과 P03 실패를 소거하지 못한다. PRE02가 최종 source 채택이나 변경을 요구·승인하지 않는다.

원 B03를 측정 기준으로 선택할지에 대한 새 재량 결정은 필요 없다. 이미 승인된 기준이다. 미결정은 보존 자료·지원 복구 경로·직접 계측의 사실과 자격이다. 대체 source/runtime이나 원 source 수정이 필요하다는 결론이 나오면 별도 명시 결정과 재자격이 필요하며, 원 8개 의무를 대체할 권한은 현 승인에 없다.

## 6. 계측 자격과 원자료 복원 한계

[계측 결측 검토](benchmarks/t69-pre02/instrumentation-gap-review.json)의 판정은 **BLOCKED — 추가 필수 collector 미자격**이다. 원 B03 IR07 correctness는 CLOSED로 유지한다. material 반증은 없으며 closed 감사 전체를 다시 열지 않는다.

아래 source 참조는 고정 archive 내부의 `source/` 경로다. 현재 live tree의 변경 파일을 인증 근거로 사용하지 않았다.

| metric | 원 source·raw에 존재하는 것 | 복원 가능 범위·남은 자격 |
| --- | --- | --- |
| hash/primary/SQL write | `docs/benchmarks/t66f-b03/counters.py` 990–1088행, `mobile/lib/src/diagnostics/logical_cost.dart` 4–71행, `mobile/test/support/logical_cost_sqlite.dart` 248–340행 | IR07 범위의 실제 sink·span·NEW payload/rollback·stage key 재사용. SQL write를 SQL read나 NAND로 바꾸지 않음 |
| SQL rows read | Python execute의 statement/bind, Dart wrapper select() 435–440행의 ResultSet 반환 | 실제 cursor fetch/iteration·ResultSet 반환 행 집계는 없음. 원 statement/DML 수로 SELECT 행 복원 불가. 신규 관측 설계·독립 literal/native oracle 필요 |
| HTTP | B04 server.py 58–82행의 method/path·양방향 entity·decoded/chunks·server interval, grid_test.dart 61–110행의 client complete-body 집계 | 기존 집계·라벨별 분류 재계산 가능. `header_us`는 header bytes가 아님. client 요청별 body RTT·의존 관계·실제 serialized headers는 결측 |
| framing | 실제 entity 합계와 decoded 합계·chunk 수 | body 원문·각 token/packet 분해를 보존하지 않음. `4×ceil(decoded/3)`나 재직렬화 모델로 실제 captured framing/wire를 대체할 수 없음 |
| full gzip | 역사 입력 SHA·codec bytes/시간 | 현 matched source/state·transport/headers·full parse/write는 없음. 새 facade/codec/consumer 자격 필요 |
| E3 direct full-work | LogicalCost의 e3Verify/Prepare/Commit/readback 및 SQL byte stage, SegmentedWork의 5종 full-work operation 합계 | `work.dart` 1–11행은 stage 없는 map. `store.dart` 105행에서 내부 final work를 생성한다. stage byte key는 work add event의 직접 stage 귀속이 아님. 원 source 무변경 관측 seam은 미입증 |
| lease/GC/refcount/root-pin | 원 DML payload와 D3 object/path 계수 | 부기 read/edge 열거·query plan·정상 단계별 hidden scan 부재는 별도 직접 계측 필요 |

`app_state.dart` 470–493행에는 E3 원 stage 경계가 있으나 임의 observer callback을 받을 API라는 증거는 없다. operation aggregate0의 차감·배분이나 E2와의 subtraction으로 E3 direct0을 만들 수 없다. prepare/discard stopwatch는 실제 accepted E3Verify/Prepare의 시간 대용이 아니다. 필요한 seam이 원 source에 없으면 그 원 source 증거는 계속 차단이다.

`store_publication.dart` 437–440행의 최종 `finalAuthorityFence(); _db.execute('COMMIT');` 사이에는 새 await/hook/callback/SQL observer callout을 넣지 않는다. 기존 native SQL dispatch 계측의 정확한 범위와 새로 삽입하는 callout을 구별해야 한다.

추가 qualification에는 exact harness SHA, 원 source 전후 불변, source callsite·native 결과 독립 oracle, 중복/누락/실패/취소/late event·ownership/lifecycle·monitoring 안정성, byte/SQL 경계, timer와 observer 자체 query의 분리가 필요하다. 코드가 그럴듯하다는 이유로 자격을 발급하지 않았다. 실제 반환 행과 VM/pager 방문 행도 구별한다. query plan은 동일 state의 timer 밖 자료로 얻어야 하며 실제 read event를 대신하지 못한다.

새 cursor wrapper·행 callback·body copy/retention·timestamp·trace·압축 버퍼는 CPU/RSS·SQL cache·스케줄링·응답 대기를 바꿀 수 있다. B04 ON/OFF는 prepared cache의 이득과 관측 비용·추가 Stopwatch의 순효과다. 순수 callback CPU로 해석하거나 새 collector의 교란으로 이전할 수 없다. 새 구성은 그 영향과 메모리 관찰 한계를 공개하고 필요한 대조 범위를 독립 검토해야 한다.

제품·B03 계측/SQL wrapper·trigger·stage·monitoring ownership을 바꾸면 원 IR07 scope의 자동 적용이 끝난다. engine SHA가 같아도 instrumentation payload/harness가 다를 수 있다. 외부 harness만 추가해도 그 harness의 자격은 별도다. 원 source를 수정한 후보의 결과를 원 B03 결과라고 부를 수 없다. qualification 전에는 T35-ROWS/NET/GZIP 완결, N100k E3/I25/bookkeeping 수용, 새 collector 순수 비용 및 실행 준비 PASS를 발급할 수 없다.

## 7. 최소 계약 준수 계획 A

이 계획은 **논리적 최소 범위**이며 실행 가능한 최종 수치 계획은 아니다. `r`은 N100k 각 workload의 반복 수, `U`는 미충족 고유 full 비교 identity 수, `q`는 자격 범위에서 필요한 matched OFF 수다. 숫자 `r/U/q`는 현재 미정이다. 이 미정을 표본 감축 허가나 실제 실행으로 해석하지 않는다.

| run class | PRE01 | 최소 계획에서의 처분·고유 의무 |
| --- | ---: | --- |
| 하위 4N 정상 ON | 12 | **12회 n1 보완 계획 유지**. 기존 각 n3 비용을 다시 측정하지 않고 SQL/NET·단계 결측을 공동 보완. 새 metric의 n1과 과거 timing n3는 별개 집합으로 표시 |
| N100k 정상 ON | 9 | **3r회, r 미정**. 세 workload 반복 필수. 기존 대체 증거 없음. T35 세 항목·ROWS/NET/GZIP·I25 두 항목을 같은 실행에서 수집. n3/9회는 비교 편의 설정이지 규범 최소 아님 |
| 별도 다양성10k ON | 9 | **1회 matched no-change case 계획**. 같은 규모 대표군과 비교하고 분포·H/금융 입력 고정 및 baseline을 별도 admission. 8회는 무조건 최소에서 제외. 다양성 3workload×n3나 독립 5점 곡선의 명문 없음 |
| FULL | 30 | **U단위**. 대표 15 cell와 다양성 case의 실제 matched 근거는 필수. 매 ON마다 fresh FULL을 반드시 반복하라는 수 규정 없음. exact 비교 identity 및 통계 주장 범위에 따라 공유·분리 |
| OFF | 조건부30 | **무조건 필수 0, 조건부 q**. ON 완료와 교란 공개는 필수이나 매 ON별 OFF 규정 없음. 새 관측기 교란의 자격 근거가 부족하면 필요한 matched 대조를 선정하며 blanket30으로 확정하지 않음 |
| 하위 N n3 추가 | 조건부24 | **무조건 필수 0**. 새 metric마다 n3라는 규범 없음. 실제 trial/path 차이·분포 주장 문제를 해소할 해당 cell만 확대 가능 |
| 새 full cold / 별도 I25 acquisition | 0 / 0 | **0 / 0 유지**. cold는 새 MUST가 아니고 별도 NO-GO/GO 대상. I25는 정상 run과 공유 |

하위 n1 보완은 기존 반복 증거를 보존하면서 결측 열만 추가하는 방식으로 허용할 수 있다. 단, metric별 sample provenance와 입력·경계를 분리하고, 결측 metric에 존재하지 않는 n3/p95/IQR 분포를 만들어서는 안 된다. trial마다 SQL/path·bytes가 다르거나 새 단계의 분포가 필요하다는 구체적 사실이 확인되면 해당 범위를 더 측정해야 한다. 이는 모든 하위 cell에 +24를 자동 부과하는 근거가 아니다.

다양성1회는 §35-T69 제4항의 두 문자열 family 비교를 위한 최소 case 설계다. 단일 비교의 codec/network/parse/validation/write 값을 제출할 수 있지만 모집단 tail이나 세 workload 모두의 다양성 효과를 주장할 수 없다. 대표 다섯 점·N100k 세 workload 반복은 그대로 필수다. 다양성 fixture의 적법 baseline도 없으므로 이 1회조차 현재 실행할 수 없다.

정상 ON의 계획식은 **12+3r+1=13+3r**이다. 원 제안의 r=3을 별도로 선택하면 ON22가 된다. 이 숫자는 비교용 구성 예이며 확정된 규범 최소값이 아니다. 현재 표본 결정으로 단일 숫자 최솟값을 발급하지 않는다.

FULL 공유에는 source/runtime·DB state·Context·fixture·실제 full input SHA·serializer·codec 설정·HTTP/cache 조건의 독립 일치 확인이 필요하다. 같은 bytes의 크기/framing 비교는 한 자료를 여러 관련 case에 연결할 수 있지만, 같은 timing을 복제해 독립 n이나 p95 표본을 늘릴 수 없다. 서로 다른 mutation 입력에는 별도 비교가 필요하다. FULL 시간/CPU 분포를 주장한다면 그 분포의 표본도 별도로 결정한다.

PRE01 interleaving에서 cash T0 뒤 no-change T1, cash T1 뒤 no-change T2는 같은 DB state의 full 입력 후보다. 실제 input SHA와 HTTP/cache 조건이 아직 없으므로 절감 수를 확정하지 않는다. r=3 구성에서는 ON22에 대응한 FULL 최대22개 후보를 검토할 수 있으나 U는 exact 입력 freeze 뒤 결정한다. PRE01식 identity+gzip 양쪽 전송을 유지하면 응답 leg 수는 2U다. 두 leg 수를 규범상 독립 표본 수로 혼동하지 않는다. full 반복 비용을 줄여도 필수 matched 비교 열을 지울 수 없다.

## 8. 조건부 확장 계획 B

[최소 행렬 JSON](benchmarks/t69-pre02/minimum-execution-matrix.json)은 다음 객관적 trigger만 확장 사유로 둔다. 조건 발생은 자동 실행 허가가 아니며 exact 수정 계획·독립 검토·필요한 GO가 먼저다.

| trigger | 허용할 최소 수정 |
| --- | --- |
| 기존 raw/source/fixture 불일치 또는 누락 발견 | 해당 metric/cell만 결측 재분류·보완. 유효한 나머지 증거 재실행 금지 |
| n1 보완으로 trial별 SQL/query-plan/path/framing 차이를 설명하지 못함 | 영향 trial·workload만 추가. 하위 모든 cell의 n3를 새 규범으로 만들지 않음 |
| FULL·새 단계 median/p95/IQR 비교를 주장함 | 해당 metric의 n·estimator·주장 범위 사전 결정 후 독립 raw 추가. 다른 metric의 표본을 빌리지 않음 |
| 새 collector의 교란을 기존 증거·자격으로 한정하지 못함 | 필요한 stage/cache/workload를 덮는 matched OFF q 설계. Target·상대 sequence·값/bytes·pool 순서 동등성 검증. N100k OFF도 별도 GO 필요 |
| full input SHA·source/Context·codec·HTTP/cache identity 차이 | 공유 해제 후 해당 FULL 추가, 서로 다른 family/곡선 유지 |
| 다양성 변경이 hot/control/금융 입력을 바꾸거나 추가 workload 민감성이 드러남 | 먼저 fixture/coverage 판정 후 필요한 case만 추가 계획. 대표 곡선 대체 금지 |
| baseline 부재, collector 미지원, full-N/authority 위반, lease·budget 소진 | 확대 대신 **중단·보존·차단 보고**. TTL/attempt/cold/자원 자동 확대 금지 |

## 9. 역사 N100k 실패의 독립 확인

원 [P03 full-analysis](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json), [full-result](benchmarks/t66f-b03-ic01-p03/evidence/full-result.json)와 압축 raw5종의 해제를 메모리 내에서 검증했다. 각 보존 raw의 비압축 SHA·길이가 원 manifest와 같다. 신규 workload를 실행한 것은 아니다.

| 사실 | 검증 결과 |
| --- | --- |
| source | 당시 IC01/P02→P03, 최종 IR07 payload의 실행 아님 |
| 종료 | FAIL, `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)` |
| 시간·객체 | 2699.957907초, 397146/400532개, 3386개 미취득 |
| 수신 canonical bytes | 259743775B, complete target 아님 |
| 관측 | 실제900초 3개, 각410 만료. 수신129376/137984/129786개 |
| accepted·E3/E4 | before/after null, E3/E4 미완료 |
| 외부 종료·resource guard | 원 기록상 없음 |
| 금융 correctness 실패 | 재현되지 않음. 미실행 E3/E4의 성공을 뜻하지 않음 |

직접 실패는 **실제 protocol observation lease 안에 transfer를 완료하지 못하고 기존 한도를 소진한 것**이다. 측정 watchdog이 먼저 잘라낸 실패로 바꿀 수 없다. backend handler 합1886.414804612초와 process CPU1883.257226036초는 큰 처리 비중을 보여준다. 그러나 backend 자체 비용, client throughput, scheduler/network, 기존 계측과 P03 추가 observer의 순수 비용은 분리되지 않았다. source/fixture incompatibility가 직접 원인이라는 증거도 없다. 따라서 instrumentation 단독 원인이나 제품 금융 결함을 단정하지 않는다.

원 full-analysis의 client SQL API380.084418초·callback 하한23.548612초와 PRE01의380.069584초·23.548580초는 scope가 다르다. 첫 observation 직전 SQL14834μs·callback32μs를 빼면 PRE01 값과 일치한다. 이를 같은 경계의 상충 수치나 material corruption으로 판정하지 않았다. callback은 SQL API에 포함되고 handler/HTTP/client interval도 겹치므로 합산 총시간 분해를 만들지 않는다.

P05 기록은 당시 원 backend 삭제와 재부팅 뒤 알려진 client 경로의 부재를 설명한다. 남은 Target·fixture JSON은 원 matched DB 사본이 아니다. 99% 근접 진행은 E3/E4 PASS, tail 성공, 현재 source의 full-scale feasibility가 아니다.

B04 최종 원 B03 50k ON의 cold1573.537722초·transfer1399.633084초와 기존100k cold NO-GO도 유지한다. 당시 조건부2798.36초 외삽은 최대2700초 active-window 산술보다 길었던 역사 판단 근거다. 현재100k 예측치나 완료/실패 판정으로 전용하지 않는다. B02 기능 성공 역시 현재 B03 ON·추가 collector 구성의 완료 가능성을 입증하지 못한다.

## 10. 자원·lease·abort 예산

[자원 검토 JSON](benchmarks/t69-pre02/resource-feasibility-review.json)의 전체 판정은 **REVISION REQUIRED / N100k FEASIBILITY NOT ESTABLISHED**다. 모든 수치는 미승인 제안이다. 안전 중단 상한과 예상 runtime·완료 보증·latency 합격선을 구별한다.

| 제안 | 증거와 한계 | 판정 |
| --- | --- | --- |
| 정상120초 | B04 하위 정상 ON raw 최대10.959006초에는 여유. N100k·추가 collector는 미측정이며 legal base 확보가 먼저 | PARTIAL |
| FULL300초 | qualified full 생성·codec·전송·parse/validation/write 비용 없음. 역사 offline 압축으로 보증 불가 | UNVERIFIED |
| baseline admission1800초 | 새 cold 제외. 지원 복구 경로·complete recovery 비용 미제출 | UNVERIFIED |
| scale3600초 | PRE01 N100k9×120+FULL9×300=3780초. OFF9 포함4860초이며 admission 별도 | REVISION REQUIRED |
| campaign14400초 | 원30ON+30FULL의 상한 합12600초, OFF30 포함16200초. 6개 scale/family admission×1800 포함 시23400/27000초 | REVISION REQUIRED |
| scratch10GiB | canonical 크기와 달리 DB/index·previous·WAL/temp·backup 압축 전후·full raw·build/runtime·누적 증거 동시 peak 미산정 | UNVERIFIED |
| RSS8GiB | 역사 B04 50k process-group peak2951401472B, B02 100k process-tree peak5772578816B는 다른 범위. 새 full/두 client/collector peak 아님 | UNVERIFIED |
| free disk10GiB, 시작20GiB·MemAvailable10GiB | PRE01 순간 snapshot의 disk free102982717440B, MemAvailable22183784kB는 예약·quota·미래 여유 보증 아님 | PARTIAL |
| campaign1회 | 실패 자동 재시도0의 유한 정책은 유지 가능. launcher·독립 자격·owner GO 없음 | UNAPPROVED |

상한 합계는 모든 작업이 실제 최대 시간만큼 걸린다는 예상이 아니다. nested cap에서 먼저 중단하도록 설계하는 것은 가능하다. 다만 그 경우 계획 전체 완료가 보장되지 않는다. admission·generation·FULL·OFF·증거 압축·검증·cleanup이 어느 상한에 포함되는지 명시하고, 선택한 최소 행렬의 credible 비용과 대조해야 한다. PRE02가 3600/14400초를 올리거나 새 자원 예산을 승인하지 않는다.

역사 B04 50k의 matched 비압축 DB 합은1017720832B다. N100k initial400532 객체·canonical261543083B는 DB/page/index/receipt/previous·WAL/temp·backup·raw의 총 peak가 아니다. 50k를 두 배로 하거나 B02 cold/delta/restart 전체5408.551164초를 새 정상 campaign 비용으로 쓰지 않는다. 새 N100k runtime·scratch peak 예상값은 **null**이다.

기록된 호스트 순간값은 2026-10-27 05:03:51 UTC 자료다. cgroup/CPU·메모리·disk quota와 자원 예약, 경쟁 작업의 미래 영향은 이 자료에 없다. host MemAvailable이 충분해 보여도 owned process-group8GiB의 측정·강제 상한을 인증하지 않는다. RSS 합에는 공유 page 중복이 있을 수 있고 1초 sampling은 사이의 peak를 놓칠 수 있다.

기존 policy인 TTL≤900초, client attempts3·observations3, principal Available4는 서로 다른 제한이며 그대로다(C §16, §35-T69 739행). 세 최대 window의2700초는 재인가 gap을 포함한 wall 보증이 아니다. 완전 취득 뒤의 local E3/E4는 transfer TTL과 별개다. TTL·attempt·retry를 바꾸는 처방은 승인하지 않는다.

현재 제안은 cooperative cancel→최대30초 cleanup→필요 시 자기 process group만 종료하는 방식이나 실제 watchdog의 enforceability는 미입증이다. native 호출 즉시 중단, sampling 사이 자원 peak, COMMIT 이후 readback 미완료는 별도 한계다. deadline이 grace를 포함하는지와 실패 증거를 남길 공간·시간을 먼저 정해야 한다. COMMIT 여부가 불확실하면 rollback 완료로 간주하지 않고 DB/WAL·receipt·pending·old/frozen/previous를 보존한다. 첫 no-change·동등성/collector 실패 뒤 card/cash·상위 N 자동 진행은 금지한다.

## 11. 독립 수용 조건·남은 준비·단 하나의 다음 작업

| 준비 차단 | 구속 근거 | 빠진 사실·최소 준비와 독립 검토 |
| --- | --- | --- |
| 적법 baseline | C §5/§18/§23–25, §35-T69 735행 | 보존 사본과 지원 복구 경로의 exact identity·새 epoch·같은 연결 accepted provenance 연결이 필요. 우선 무실행 정적 경로 판정 |
| 필수 collector | C §35-T69 733·737행, §36 I25 | SQL-return·E3 direct work·부기·HTTP/framing/full 경로 가능성 및 자격 없음. baseline 판정 뒤 원 source seam map을 심사하고, 별도 작은 oracle 계획·GO 전 구현·실행 금지 |
| 숫자 최소 행렬 | C §35-T69 731·733행 | r·metric별 분포 주장·U 입력 공유·q 교란 범위를 exact 계획으로 확정. 이 결정을 규범 n3로 위장하지 않음 |
| 자원·완료 가능성 | C §16, §35-T69 739·741행, artifact hygiene | admitted source/최소 행렬 뒤 동시·누적 저장량과 deadline/grace 계산, 자원/lease 내 완료·중단 가능성 및 실패 보존 검토 |

나중 수용자는 실제 raw·command/cwd/exit/time·source/runtime/binary·fixture/Target·accepted 전후·stage 완료·실패/취소·resource trace와 SHA/mode/size를 다시 연결해야 한다. backend 실제11-table 값·presenter, native complete graph/FK/hash/root와 E4를 독립 대조하되 모바일 금융 계산 엔진을 추가하지 않는다. same-connection provenance와 마지막 authority fence를 유지한다. 결측·미지원·취소를 성공0으로 채우지 않고, 정상 full-N 위반은 해당 구현 거부·별도 수정/재자격으로 처분한다. 8개 모두 수용되어도 나머지 whole-F 및 R1/기기/rollout/deployment 승인은 별개다.

**즉시 다음 작업은 NEXT-01 하나뿐이다.** 원 B03의 보존 manifest와 epoch·accepted 복구 소스만 정적으로 대조하여 **새 취득 없이 N=100k 적법 baseline을 확보할 지원 경로의 존재 여부**를 판정한다. 결과 한 문서/JSON에 보존 경로·SHA, §5 새 epoch 영향, complete11 tables/index/receipt·NS/principal/Versions/Target·generation·같은 연결 요구별 충족/미충족과 source callsite를 적는다. 구현·측정 비참여 검토자가 이 경로의 적법성을 심사해야 하며 실제 runtime admission 완료와는 구별한다.

제안한 후속 정적 조사 범위는 최대1800초, benchmark/API/DB open/product import/cold acquisition/새 계측 모두0회다. 이1800초는 승인된 campaign 예산이 아니며 못 찾으면 차단 판정으로 끝낸다. 새 source artifact는 필요 없다. 원 archive·계측·인덱스는 그대로 보존한다. 경로가 cold 또는 source 수정을 요구한다면 그 사실만 기록하고, 기존 NO-GO·별도 source 승인/재자격 경계를 넘지 않는다.

대규모 benchmark는 baseline의 적법성을 시간으로 증명하지 못한다. 자격 없는 collector로 실행해도 필요한 수용 증거가 생기지 않는다. 따라서 지금 full/partial N100k, 다른 규모 full cold, TTL 변경이나 다중 계측 구현을 시작할 이유가 없다.

## 12. 분리 판정과 보존

| 항목 | 독립 판정 |
| --- | --- |
| A 규범 coverage | **PASS — 8/8 MAPPED**, 수용0/8 |
| B baseline legitimacy | **PARTIAL** — 원 source PASS, 현재 N100k accepted admission 차단 |
| C instrumentation qualification | **BLOCKED** — 원 IR07 CLOSED, 추가 필수 metric 미자격 |
| D measurement minimality | **PARTIAL** — 필수/조건부 분리, r/U/q·새 단계 분포 범위 미정 |
| E operational feasibility | **PARTIAL** — 현재100k 미입증·예산 수정 필요 |
| F execution authorization | **NOT GRANTED** |

PRE01은 결측·NO-GO·별도 GO 필요를 공개했으므로 제안 자체를 실제 binding 위반 실행으로 판정하지 않는다. 무결성 대조에서 material source/승인/evidence 결함도 발견하지 않았다. 그러나 핵심 baseline·metric 자격이 미해결이므로 corrective preparation의 완료 가능성까지 PASS로 인증할 근거는 부족하다. 최종 분류는 **PARTIAL — REQUIRED BASELINE OR METRIC QUALIFICATION UNRESOLVED**다.

산출물은 이 한국어 보고서와 PRE02 전용 JSON뿐이다. [종료 보존 검증](benchmarks/t69-pre02/preservation-final.json)은 시작6,518개 경로의 내용·길이와 인덱스 bytes·전체 path/mode/blob/stage, HEAD/branch, 원 B03 frozen sidecar/archive를 다시 비교한다. staged mode/blob는 인덱스로 검증하며 모든 기존 파일의 POSIX mode를 시작 시점에 별도 전수 기록했다는 주장은 하지 않는다. 입력 manifest에는 읽은 자료의 현재 mode도 남긴다. ignored runtime·production 전체 전수 검증의 주장은 아니다.

[입력 목록](benchmarks/t69-pre02/input-manifest.json), [정적 검증](benchmarks/t69-pre02/static-validation.json), [산출물 목록](benchmarks/t69-pre02/evidence-manifest.json)에 근거를 연결한다. 기존 B01–B11/PRE01 보고서·측정·B05/B08 실험 archive, approved amendment, 미커밋·미추적 작업을 수정·삭제하지 않았다. reset/stash/clean/checkout/rebase/restage/commit/push는 하지 않았다. 대형 실험 임시물 정리는 NOT APPLICABLE, 삭제·회수0B다.

```text
T6.9-PRE02 INDEPENDENT EXECUTION READINESS REVIEW:
PARTIAL

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

AUDITOR INDEPENDENCE:
SATISFIED

APPROVED B11 AMENDMENT:
VERIFIED

T6.6F PHASE B ADMINISTRATIVE CLOSURE:
COMPLETE — EVIDENCE TRANSFERRED

T6.6F FORMAL CLOSURE:
NOT AUTHORIZED

EIGHT TRANSFERRED OBLIGATIONS:
MAPPED

EIGHT TRANSFERRED OBLIGATIONS ACCEPTED:
0 / 8

ORIGINAL B03 SOURCE:
VERIFIED

BASELINE LEGITIMACY:
PARTIAL

INSTRUMENTATION QUALIFICATION:
BLOCKED

MEASUREMENT MINIMALITY:
PARTIAL

MINIMUM CONTRACT-COMPLIANT RUNS:
하위 N 보완 ON12 + N100k ON3r(r 미정) + 다양성 ON1; FULL U 미정; 무조건 OFF0; 새 cold0

CONDITIONAL EXPANSION:
trial별 coverage 차이·새 분포 주장·FULL 입력 불일치·새 collector 교란 근거 부족 시 해당 cell만 수정 계획 후 확대

HISTORICAL N=100K FAILURE:
2699.957907초, 397146/400532개, observation3개 만료, E3/E4 미완료; resource guard 실패 보고 없음

CURRENT N=100K FEASIBILITY:
NOT ESTABLISHED

RESOURCE BUDGET:
REVISION REQUIRED

EXECUTION READINESS:
NOT READY

N=100K EXECUTION AUTHORIZATION:
NOT GRANTED

NEW FULL COLD RUNS:
0

PRODUCT SOURCE MODIFIED:
NO

B03 INSTRUMENTATION MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

ENGINE ADMISSION MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY PRE02:
NO

HISTORICAL EVIDENCE:
PRESERVED

REAL-DEVICE GATE:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

PRE02 REPORT:
docs/t69-pre02-independent-execution-readiness-review.md

PRE02 EVIDENCE:
docs/benchmarks/t69-pre02/

FINAL VERDICT:
PARTIAL — REQUIRED BASELINE OR METRIC QUALIFICATION UNRESOLVED

NEXT ACTION:
원 B03의 보존 manifest와 epoch·accepted 복구 소스만 정적으로 대조하여 새 취득 없이 N=100k 적법 baseline을 확보할 지원 경로의 존재 여부를 판정한다.
```
