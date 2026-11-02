# P1-04 backend SQL·presenter 성능 귀속 결과

**COMPLETE — C. LARGE COST REQUIRED BY CURRENT CORRECTNESS CONTRACT.** 5규모·7경로의 기준 시간700표본과 별도 귀속105표본을 수집했다. 큰 정상 bundle 비용은 이전 T6.6A에서 이미 관찰한 Snapshot·관계 검증·canonical JSON/hash 처리와 일치한다. 새로운 지배적 index/connection 병목이나 안전하게 제거 가능한 중복은 실증하지 못했다. **새 구현 추천 후보0개, 생산 코드·schema·index·잠금 변경0개**로 P1-04를 완료한다. 이 판정은 모든 비용이 영원히 최적화 불가능하다는 뜻도, 1단계 종료나 운영 준비 판정도 아니다.

## 현재 소스·실행 기준

HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, 시작 index SHA-256은 `56aba5ca9506287cbe6a81dd5caebc246e3519c6e84b9680f4108358d50f5595`다. 실제 working source를 읽었고 기존 tracked13개 변경과 모든 untracked 증거를 보존한다. 현재 정상 경로를 frozen B03 또는 실험 B05/B08 source와 동일시하지 않았다.

| 소스 | SHA-256 |
| --- | --- |
| `backend/app/db.py` | `378783da0a16e5af77a26e7b4534c5f210f90d49829f29ab1d4c748cae82e2c2` |
| `backend/app/db_migrations.py` | `24c1445294cddc08ddbdf69cc1a399d8c29276db9dc2842e00eeac06319390ea` |
| `backend/app/services/authoritative_state.py` | `e953aa895de993472f5d04159b9951cf901ca4cf0defc3af8672e2cc6c39daab` |
| `backend/app/services/snapshot.py` | `92bba975d0c0e4776b6ef775a647009ad1de6887a36b5c0a9270ad2ba7bb5240` |
| `backend/app/services/financial_relationships.py` | `fce7c71297a1d3a7642839ae4a685615ddfcb5aac5da0076f2d182e34c7ca850` |
| `backend/app/services/presentation.py` | `d2ac009ea06f166025dee719ad953279d141e6f2dfe551aa96fa281dd450ba87` |
| `backend/app/services/summary.py` | `75ad773d6649a36067ff14f90fdd070fc42e440e7a0614dddfb19a05212bb6a7` |
| `backend/app/routers/responses.py` | `0d6f677f3424d3f28a44daf0b2ff96f4b506444e3b7b4524141cc6dd74cc737b` |
| `scripts/benchmarks/t66a.py` | `c5a78e5ebecddc1c9f34e3b736a7a91d5554d055a9e288c1f5a41da6447d8431` |

나머지 router/auth/row 변환·fixture·보호 계약을 포함한24개 신원은 [단일 근거](../benchmarks/p1-04-backend-sql-presenter-performance.json.gz)에 있다. Python 3.12.3 / SQLite 3.45.1, Linux-6.8.0-147-generic-x86_64-with-glibc2.39, Intel Core i7-8750H다. 설치 패키지는 FastAPI 0.139.2, Starlette 1.3.1, Pydantic 2.13.4, httpx 0.28.1다. 실제 인증된 in-process TestClient를 사용했고 네트워크 socket·production API/DB는 사용하지 않았다. Flutter·Android·ADB·에뮬레이터·단말 도구는 전혀 실행하지 않았다.

## 이전 최적화·관측 재사용: 6개 근거 묶음

| 최적화 또는 관측 | 기존 근거·측정 revision/범위 | 현재 소스 상태 | 다시 측정할 필요 |
| --- | --- | --- | --- |
| H1 동일 transaction의 ownership PASS | `ed7662d` T6.3, [도메인 계약](../domain-model.md#summary의-동일-읽기-뷰-검증-재사용), 기존 `test_card_ownership_read_view`. 동일 view에서6테이블 검증1회라는 기능 계수 근거이며 과거 latency 수치를 새로 만들지 않음 | file 전체는 후속 변경됨. AST 대조상 CardOwnershipReadView에 격리 FinancialInputScope hook이 추가됐고 일반 연결의 guard/PASS 재사용은 유지됨 | 과거 최적화 재구현 불필요. 현재 count와23개 기존 회귀로 적용 상태만 확인 |
| H2 borrowed connection·응답 commit 경계 | 현재 DB/session·[project-state](../project-state.md)의 backend refactoring/Freeze 기록. `9c94d7e`는 repository 응답 구성 위치에 대한 변경이며 현재 JSONResponse helper의 도입 commit으로 잘못 인용하지 않음 | 명시 conn 재사용과 금융 응답 bytes의 commit 전 준비 유지. 동작 보장이지 독립 latency 개선 측정은 아님 | 현재 connection/transaction 계수만 귀속. pooling·commit 경계 변경 없음 |
| H3 정상 bundle 취득 | [T6.5B-3](../t65/implementation/t65b3-implementation.md), 시작 `68aae70c…`, 합성376/1k/5k/10k·host warmup2/표본5. refresh14→1, mutation+취득15→2 HTTP | 정상 authoritative endpoint와 client topology 유지. 현재 서버 service는 T6.6A 기준 source와 동일 | HTTP 절감 실험·과거 Flutter campaign 재실행 불필요. mutation 이후 GET은 이번 endpoint timing에 넣지 않음 |
| H4 Snapshot·bundle 처리와 metadata | [T6.6A](../t66/a/t66a-payload-attribution.md#16-backend--client-latency-귀속), `597a936d…`, Python3.12.3/SQLite3.45.1, 같은 rich fixture·warmup3/표본20. 10k endpoint1348.5ms, export557.6ms, prepare191.1ms(각 포함 시간) | 정상 service/Snapshot/presenter/DB/migration5파일이 byte 동일. 이번4개 nonempty 응답도 과거 bytes·SHA와4/4 동일. schema metadata는 export당 canonical memory connection1개로 이미 묶임 | payload/압축·대형 전송 실험은 재실행하지 않음. 미분리 SQL/fetch/행 변환만 이번에 추가 귀속 |
| H5 격리 `_lookup` decode | [B05](../t66f-b05-lookup-hot-body-decode-optimization.md)의 원 B03 파생 후보. 국소 decode와 전체 취득 결과를 구분하며 qualified production 개선으로 보지 않음 | 기존 dirty observation 후보는 보존. native 일반 SQLite 연결은 FinancialInputScope가 아니므로 해당 입력 제공자를 정상 backend에 설치하지 않음 | 정상 API의 해결책으로 다시 발견하거나 격리 acquisition을 재측정하지 않음 |
| H6 격리 connect/schema·기대 계약 재사용 | [B07](../t66f-b07-bounded-connect-schema-attribution.md), [B08](../t66f-b08-expected-revision-contract-reuse.md). 원 B03 engine 기준, B08 작은 packet handler 국소10.65%·compile46→1, 실제 DB 검사46회 유지·전체 cold 이득 미검증 | 현재 일반 `db_migrations.py`는 T6.6A byte와 같고 B08 실험을 기본 코드에 이식하지 않음. 격리 schema/engine/gate와 정상 SCHEMA 입력이 다름 | 기존 B08 후보 재구현·T6.9 자격 실험 불필요. 정상 요청의 trigger 검사 비용만 현재 귀속 |

T6.6A10k1348.5ms와 이번1273.714ms 차이는 제품 최적화 효과가 아니다. source와 payload는 동일하지만 warmup·실행 순서·kernel·CPU/thermal 조건과 timing interval이 다르다. 이전에 끝난 문제를 재발견했다고 보고하지 않는다. 과거 deferred 항목인 full-history O(N), 격리 engine 입장·전체 cold/100k 정량·실기기 의무도 이번 결과로 해소하지 않는다.

## 실제 요청 호출 지도

- **authoritative-state:** `require_bundle_credential→require_user/current_user_from_request`가 선택한 token/principal을 인증하고 session last_seen을 갱신한다. `authoritative_state_response`는 DEFERRED/query_only 금융 read transaction 안에서 revision/schema/revision trigger 검사→고정 평가일·settings→Snapshot export·strict 검사→read-only ownership view의 entries/panels/Summary/payment/judgment/confirmed/cash/policy→fingerprint→`_prepare`의 raw money·Pydantic·dump·JSON bytes를 만든다. 금융 transaction을 끝낸 뒤 **새 연결의 terminal guard**가 동일 revision/schema·auth 만료·날짜/timezone을 확인한다. 충돌 시 최대3회 구성이나 이번 모든 상세 표본은 construct1회다. 새 terminal 검사를 오래된 read view로 대체하지 않는다.
- **대표 mutation4개:** `POST /api/entries`, `PATCH /api/entries/{id}`의 분류 수정, `DELETE /api/entries/{id}`, `POST /api/cash-flows`. 감사 middleware의 별도 principal 확인, raw lossless money body 검사와 endpoint 인증 후, IMMEDIATE 금융 transaction에서 실제 command·필수 read/check/write→서버 presenter/model·financial_response→commit을 수행한다. 감사 로그 저장은 별도다. create/update/delete의 조건부 recurring·batch 소유 검사를 유지한다. **네 연결은 보통 감사용 인증+endpoint 인증+금융 write+audit log**이며 풀링 부재만으로 중복 결함으로 분류하지 않는다.
- **클라이언트 후속 refresh:** mutation 응답 다음의 authoritative GET·strict admission·durable baseline·UI 설치는 AppState가 호출하는 별도 operation이다. 이번 각 mutation 표본은 HTTP1회·후속 refresh0회다. 실제 앱 저장 완료 지연을 mutation endpoint 값으로 축소하지 않는다.
- **서버 Snapshot:** `GET /api/admin/snapshot→require_user→export_snapshot(DEFERRED)→_SnapshotExportMetadata.read→11테이블 export·money/recurring/relationship→manifest→compact JSON`. 정상 bundle 내부 export도 같은 서버 데이터 경로다. P1-03의 모바일 파일30개 retention/list와 별개이며 모바일 비용을 다시 측정하지 않았다.
- **Summary control:** `GET /api/month/current/summary→current_summary_values→기존 DEFERRED transaction의 card_ownership_read_view`다. 이미 최적화된 정상 경로를 확인하는 한정 control이며 다른 API 전수 조사를 열지 않았다.

## 합성 workload와 절차

기존 `scripts/benchmarks/t66a.py:seed`와 `AuthoritativeStateTest`의 새 migrated SQLite/rich fixture를 그대로 사용했다. seed1234·평가일2026-10-05·timezone540, 고정 금융 timestamp와 payment key, 실제 할인·공과금·통행료·부분 payment·Claim/Family/fixed/frozen/cash·archive NULL-date actual 관계를 보존했다. 각 fixture는 실제 Snapshot canonical 검증·dry-run 복구를 통과했다. fixture 생성·인증 준비·일관 SQLite backup/복원·검사·EXPLAIN은 timer 밖이다. 사용자/운영 DB를 복사하지 않았다.

**N은 전체 금융 행 합이 아닌 ledger 행 수**다. nonempty는 current105개를 유지하고 archive만 늘려 과거 T6.6A와 정의를 맞췄다. 10k current UI workload나 confirmed-heavy600을 대표하지 않는다.

| ledger N | current | archive | panels | cash | batch/items/events/allocations | bundle bytes |
| ---: | ---: | ---: | ---: | ---: | --- | ---: |
| 0 | 0 | 0 | 0 | 0 | 0/0/0/0 | 10,145 |
| 376 | 105 | 271 | 4 | 5 | 1/3/1/1 | 306,370 |
| 1000 | 105 | 895 | 4 | 5 | 1/3/1/1 | 653,317 |
| 5000 | 105 | 4895 | 4 | 5 | 1/3/1/1 | 2,889,309 |
| 10000 | 105 | 9895 | 4 | 5 | 1/3/1/1 | 5,684,312 |

모든 규모에서 app_settings5·app_labels18이고 deferral/notification registration은0이다. nonempty의 그 밖 금융 행은 합15개다. empty의 update/delete만 실제 대상 행1개를 측정 전 추가했으며 raw before/after counts에 기록했다. mutation마다 일관된 task-owned baseline으로 복구해 행·순서·금액이 누적되지 않게 했다. 이 복구는 timer 밖이고 OS cache가 warm해질 수 있다.

사전1k 점검 후 예상150초·내부420초/외부480초·총600초 한도를 고정했다. **35구성×warmup5+기준20=700표본**, 별도 상세계측은 구성당 warmup1+3=105표본이다. 본 실행은170.779초에 끝났고 timeout은 작동하지 않았다. 기준20의 p95는 nearest-rank19번째다. 상세3의 p95는 최댓값이므로 tail 보증이 아니다. profiling 수집 경계를 설치된 FastAPI의 실제 dispatch에 맞추는 사전 오류는 준비 로그에 보존하고 최종 표본에 섞지 않았다.

기준 시간은 원 SQLite·원 FastAPI dispatch의 TestClient request→buffered response wall/process CPU다. 상세 계측만 sqlite3.Connection/Cursor subclass와 실제 route worker의 cProfile을 사용했다. 원 SQL·params·row_factory·transaction·응답을 바꾸지 않는다. auth/audit SQL은 request observer에 포함되지만 cProfile route 구간은 dependency/body admission 뒤이므로 auth/middleware Python의 전체 self time은 미분리다.

## 기준 endpoint 시간

단위 ms, 중앙값/p95다. fixture·warmup 이후의 host 처리 시간이며 실망 RTT·동시 요청·lock contention·OS cold I/O 값이 아니다.

| ledger N | bundle | Snapshot | Summary | 지출 create | 분류 update | 지출 delete | cash create |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 15.161/16.462 | 16.891/24.561 | 7.045/11.200 | 32.056/33.188 | 32.896/33.251 | 29.932/30.301 | 31.892/34.341 |
| 376 | 68.662/72.310 | 29.979/31.826 | 17.316/17.621 | 30.547/32.719 | 37.749/38.703 | 50.759/51.759 | 50.395/51.929 |
| 1000 | 157.058/187.682 | 70.607/83.705 | 24.717/27.687 | 48.540/49.696 | 53.722/55.383 | 51.236/53.200 | 48.711/49.491 |
| 5000 | 744.686/768.852 | 340.033/365.919 | 99.375/106.281 | 49.058/50.392 | 54.498/55.379 | 52.760/55.909 | 52.082/54.933 |
| 10000 | 1273.714/1462.058 | 639.346/688.415 | 203.061/218.901 | 50.308/51.088 | 44.028/55.303 | 52.340/58.055 | 52.417/56.194 |

## 10k SQL·연결 귀속

아래는 **별도 profiler 모집단(n3)**이다. 기준 표본과 섞어 개선율을 계산하지 않는다. SELECT 진입뿐 아니라 PRAGMA·transaction·savepoint·executescript API도 count에 포함된다.

| 경로 | SQL API 호출 | engine trace event | fetch 반환행 합 | disk+memory 연결 | execute ms | fetch ms | connect ms | transaction 포함 ms |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| bundle | 182 | 254 | 60,671 | 3+1 | 19.929 | 272.894 | 0.290 | 1859.261 |
| snapshot | 61 | 132 | 30,243 | 2+1 | 13.268 | 130.986 | 0.223 | 728.737 |
| summary | 64 | 67 | 20,178 | 2+0 | 2.050 | 84.889 | 0.137 | 252.412 |
| create | 15 | 24 | 8 | 4+0 | 8.648 | 0.154 | 1.645 | 29.832 |
| update | 18 | 27 | 115 | 4+0 | 9.124 | 2.374 | 1.041 | 36.159 |
| delete | 15 | 26 | 109 | 4+0 | 9.194 | 2.793 | 1.095 | 36.526 |
| cash_create | 12 | 21 | 3 | 4+0 | 8.269 | 0.082 | 1.643 | 30.196 |

bundle182회는 SELECT109·PRAGMA57·UPDATE1(auth last_seen)·BEGIN2·executescript1·SAVEPOINT6·RELEASE6이다. executescript1은 여러 canonical schema DDL을 포함한다. trace254는 그 DDL·implicit BEGIN/COMMIT·trigger 이벤트도 포함하므로182와 같은 단위가 아니다. fetch60,671은 동일 행의 반복 반환과 metadata를 포함하며 고유 금융 행 수나 실제 엔진 방문 행 수가 아니다.

execute는 prepare/최초 step 등 SQLite API 시간, fetch는 후속 step·sqlite3.Row 생성·자료 이동을 포함한다. profiler와 wrapper overhead도 있어 **순수 SQLite engine CPU로 부르지 않는다**. connect는 native 연결 생성, transaction은 Python 검증/JSON을 포함해 BEGIN→commit까지의 lifetime이다. 후자를 SQL 시간에 더하지 않는다. cursor iteration의 행 개별 계측도 상세 시간에 영향을 준다.

연결0.290ms와 revision trigger 검사2.095ms는 큰 bundle의 지배 비용이 아니다. metadata `_schema_connection`은 profiler에서 generator 재개2회로 표시되지만 실제 memory SQLite 연결은1개다. 이를2개 연결로 오인하지 않았다. 기존 auth·financial·fresh terminal의 연결 분리는 각각의 의미를 갖는다.

## 지배 query와 계획

10k bundle의 대표 상세 표본(sample1)에서 `SELECT * FROM ledger_entries`는4회·40,000행·execute+fetch185.211ms, planned/expense 후보 SELECT는1회·10,000행·47.313ms, Snapshot ledger export는1회·10,000행·45.249ms였다. 합은 SQL interface의 큰 부분이지만 row fetch/materialization과 각 독립 validator의 필수 입력이 섞여 있다. 이 값은 n20 기준 시간도, 인덱스로 제거 가능한 순수 search 비용도 아니다. 전체 query별 n3 분포와 원문 identity는 압축 근거에 있다.

| 실제 query 용도 | 합성 DB의 EXPLAIN QUERY PLAN | 해석 |
| --- | --- | --- |
| 전체 ledger 소유/관계 입력 | `SCAN ledger_entries` | 대부분/전체 행을 검증하므로 full scan 자체는 결함 아님 |
| Snapshot 정렬 export | `SCAN ... USING INDEX idx_ledger_section_order`, `USE TEMP B-TREE FOR RIGHT PART OF ORDER BY` | 현재 index는 전체 복합 정렬을 모두 만족하지 않지만 전체 데이터가 응답에 필요. sort 독립 CPU/개선 이득 미분리이므로 새 index 추천 안 함 |
| current 목록/confirmed planned | section index 사용, CASE/COALESCE 정렬의 임시 B-tree | 이 fixture의 current는105개로 고정. 10k current의 scroll/대형 정렬로 일반화하지 않음 |
| archive 월별 건수 | section index 검색·GROUP BY 임시 B-tree | 대표 interface3.960ms. 전체 bundle의 지배 query 아님 |
| cash 기간 조회 | `idx_cash_flows_order`의 날짜 range 검색 | 기존 index 적용 확인 |
| batch/원장 lookup | batch 항목은 `idx_card_payment_batch_items_batch`의 covering 검색, 원장 id는 INTEGER PRIMARY KEY. update의 OR 소유 조회는 항목3행 scan | 기존 인덱스 활용을 확인했고 작은 scan을 새 결함으로 분류하지 않음 |
| user/session 인증 | token UNIQUE autoindex·user PK | 인증 의미를 줄이거나 추가 cache로 대체할 근거 없음 |

EXPLAIN은 해당 fixture의 실제 SQL/parameter type으로 timer 밖에서 실행했다. 실제 auth hash 등 문자열은 근거에서 synthetic placeholder로 표기했고 계획은 동일 SQL 형태의 인덱스 선택 근거다. sqlite_stat/OS I/O·방문행 counter는 별도 계측하지 않았다. 반환행 실측과 접근 계획을 방문행 실측으로 바꾸어 말하지 않는다. 인덱스 추가의 write/storage/migration 비용을 지불할 새 근거는 없다.

## Python·presenter·검증·JSON 준비

10k bundle의 별도 cProfile n3 중앙값이다. 포함 시간과 self time을 함께 표시한다. 하위 구간은 여러 상위 구간 안에 들어가며 **서로 더해서 endpoint 시간을 만들 수 없다**.

| 함수/구간 | 호출 수 | 포함 ms | self ms |
| --- | ---: | ---: | ---: |
| `_construct` | 1 | 1467.736 | 2.388 |
| `_export_snapshot` | 1 | 727.081 | 0.050 |
| `_validate_financial_relationships` | 1 | 256.650 | 60.202 |
| `_validate_snapshot` | 1 | 250.298 | 1.182 |
| `_prepare` | 1 | 368.723 | 0.208 |
| `_build_manifest` | 2 | 496.580 | 6.881 |
| `_stable_hash` | 29 | 552.477 | 2.279 |
| `snapshot_state_fingerprint` | 1 | 76.515 | 0.004 |
| `iterencode` | 30 | 485.382 | 485.382 |
| `_validate_card_payment_rows` | 2 | 249.954 | 120.790 |
| `validate_card_payment_ownership` | 2 | 24.652 | 3.107 |
| `validate_runtime_card_payment_ownership` | 6 | 250.607 | 0.009 |
| `validate_recurring_ownership` | 4 | 68.570 | 35.283 |
| `validate_money_payload` | 20,884 | 275.422 | 124.023 |
| `_rows` | 11 | 104.920 | 57.836 |
| `row_to_dict` | 121 | 0.613 | 0.613 |
| `list_confirmed_planned_entries` | 1 | 132.277 | 60.155 |
| `present_ledger_entries` | 2 | 2.847 | 0.082 |
| `_complete_rows` | 4 | 4.470 | 0.302 |
| `_validate_revision_triggers` | 1 | 2.095 | 0.090 |

`_rows` self 약57.836ms는 Snapshot dict materialization과 루프를 포함하고, `row_to_dict`0.613ms만 전체 행 변환 비용으로 오인하지 않는다. `_validate_card_payment_rows`와 confirmed 후보 구성의 self에도 dict/iteration 비용이 있다. pure ownership validator24.652ms와 그 전체 입력 준비249.954ms를 구분한다. 실제 current presenter2.847ms와 complete-model4.470ms는 이 workload의 작은 비용이다. 상세 표본1의 Pydantic core validate_python114호출/2.322ms, to_python114호출/33.097ms도 raw에 있다. compile된 모델 호출·반환 row 수와 전체 반복 materialization을 혼동하지 않는다.

29회의 `_stable_hash`는 manifest2회×(table11+data1+policy1+content1)와 fingerprint1회다. 서로 다른 canonical hash 대상과 strict 재검증이며 단순히 같은 문자열을29번 낭비했다고 분류하지 않는다. encoder30회에는 최종 JSON response도 포함된다. `_prepare`368.723ms는 exact money·Pydantic/dump·최종 응답 bytes를 포함한다. 최종 render만의 시간은 이번 filter에서 따로 분리하지 않았으며 과거 T6.6A55.9ms를 현재 실측으로 쓰지 않는다.

runtime card 검사 요청6회지만 실제 raw6테이블 검사·canonical ownership은2회였다. Snapshot의 독립 검사1회와 downstream immutable view의1회이며, 기존 T6.3 재사용이 이미 효과를 내는 계수다. recurring4회는 Snapshot/runtime/confirmed 후보의 입력 범위·엄격성이 같다는 뜻이 아니다. 예를 들어 일반 runtime은 `require_execution_epoch=False`, confirmed 후보는 다른 기본 계약과 후보 집합을 사용한다. raw money의20,884호출도 재귀 노드 계수이며 whole-bundle pass20,884회가 아니다. 비슷한 이름만으로 검증을 제거하지 않는다.

## 분류와 구현 판단

| 요청된 분류 | 현재 판단 |
| --- | --- |
| MEASURED SQL BOTTLENECK | 지배적인 검색/인덱스 누락·연결 생성 병목은 실증되지 않음. 전량 fetch 비용은 측정됐으나 필수 입력 실체화가 포함됨 |
| MEASURED PYTHON/PRESENTER BOTTLENECK | 큰 Snapshot의 canonical encoding/hash·검증·행 materialization은 유의미. 현재 화면 presenter 자체는 작음. 과거 T6.6A와 같은 비용 계열이며 새 회귀/새 해결 문제로 보지 않음 |
| SOURCE-SUPPORTED REDUNDANCY, NOT YET MEASURED | 안전하게 제거 가능한 새 반복 후보는 확정하지 않음. 동일 SQL 재호출은 계측했지만 독립 Snapshot/runtime 보증을 지우는 근거가 아님 |
| ALREADY OPTIMIZED / NO MATERIAL BOTTLENECK | transaction-local card PASS, borrowed connection, 기존 lookup/range index와 export metadata 묶음이 유지됨. 작은 연결·presenter 비용을 새 캠페인으로 확대하지 않음 |
| INSUFFICIENT EVIDENCE | exclusive SQLite engine CPU·물리 방문행/IO, all-current10k·confirmed-heavy·경합·production/단말 end-to-end는 미측정 |

**최종 선택은 C다.** 전량 Snapshot의 현재 응답·manifest·exact-money/관계·prepared response/fresh terminal 계약을 보존하는 비용이 지배적이다. view의 입력 행 재사용, strict 검사/encoding 결합, schema/index·transaction 변경은 correctness 증명·보호 소스/engine 계약과 연결된다. 이번 결과만으로 안전한 이득을 입증하지 못했으므로 **신규 source-grounded 구현 추천 후보0개**다. B08 기존 실험 후보를 다시 새 후보로 제출하거나 다른 파일로 옮겨 source lock을 우회하지 않는다. 명시적 P0 보호에는 `db.py`, `db_migrations.py`, `snapshot.py`, `authoritative_state.py` 등이 포함된다. Summary·financial_relationships도 이번 생산 변경 금지 범위이며 어떤 source lock도 갱신하지 않았다.

모든 병목을 없애야 1단계를 끝낼 수 있다는 새 조건을 만들지 않는다. 측정된 선택적 성능 비용은 현 계약하의 C로 처분한다. 사용자 행동당 반복 취득의 비용은 독립 P1-R에서 검토할 수 있지만 freshness·mutation 완료·auth/generation·strict/durable 경계를 유지할 별도 승인 과제다. P1-S도 별도 미구현 상태다. P1-05·2~4단계·T6.9·Snapshot 확장성·배포를 시작하지 않았다.

## 집중 검증·보존·한계

기존 card ownership read-view23건과 authoritative-state3건, 합26건이 합성 DB에서 통과했고 npm build도 임시 사본에서 통과했다. 기준700·상세105개의 모든 요청은200이며 대상 id/category·생성/삭제 count·construct1회·connection close를 확인했다. 새 correctness 감사나 금융 알고리즘 검증 프로젝트를 열지 않았다. 이 한정 범위에서 새로운 치명적 금융·보안·영속 상태 결함은 실증되지 않았다.

프로파일러와 cursor wrapper는 비용을 늘리므로 상세 수치를 기준 latency에 합산하지 않는다. 단일 순차 요청과 warm page cache, 고정 archive 성장 fixture이고 CPU 주파수/thermal·GC·storage sync를 독립 통제하지 않았다. process CPU는 여러 TestClient worker의 합이지 DB thread의 exclusive CPU가 아니다. query plan은 다른 production 통계/데이터 분포의 보증이 아니다. 동시성 및 release gate는 기존 의무를 그대로 남긴다.

P1-03의 전체 PARTIAL 판정과 자동 ADB 기동·작업 소유 PID 종료 사건을 [원 보고서](../p1-03-snapshot-save-validation-performance-results.md)와 원 압축 근거 그대로 보존하고, 로드맵의 **P1-S**로 반복 검증 목표를 분리했다. 이를 PASS로 바꾸지 않았다. 이번에는 어떤 Flutter/Android/ADB 도구도 실행하거나 host 프로세스를 조작하지 않았다. F01/G1·G2 미채택·실기기/ADB·T6.9·formal T6.6F·R1·production 배포 제한은 유지한다.

Git이 열거한 기존 파일·symlink7,937개의 내용·mode·link를 대조해 허용된 로드맵 외 변경0개를 확인했다. HEAD·staged 항목·index SHA와 P1-03 원 보고서/근거를 보존했고, 로드맵의 기존 성능 지도·역사 근거·순위 표도 byte 동일하다. 활성 프로세스 부재와 일관 합성 DB5개의 압축 보존을 확인한 뒤 작업 소유 임시 파일/symlink109개(논리 크기14,609,345B, 관찰 할당량14,880,768B)를 정리했다. 기존 DB/WAL·cache·symlink 대상은 삭제하지 않았다. ignored dependency cache 전체의 무변경을 인증하는 범위는 아니다.

## 근거와 재현

[단일 압축 근거](../benchmarks/p1-04-backend-sql-presenter-performance.json.gz)에700개 기준·105개 상세 raw 표본, query별 집계·EXPLAIN, 실제 table counts·response bytes/SHA, 동일 source/과거 payload 대조, 일관된 합성 baseline DB5개, 관측 harness·계획·검사 로그를 함께 둔다. `main.samples/details`를 rows/operation/sample로 선택한다. fixture 생성·cleanup과 측정 구간을 분리했으며 외부 watchdog은 발동하지 않았다.

새 task-owned scratch에 근거의 Python harness와 plan을 복원하고 기존 backend venv로 `PYTHONDONTWRITEBYTECODE=1 TMPDIR=<새 scratch> .venv/bin/python <scratch>/benchmark.py main`을 실행한다. harness의 고정 T 경로를 새 경로로 맞추고 같은 recognized fixture/source identity를 확인한다. 서버 process를 띄우거나 production API를 호출하지 않는다. 재현에 Flutter·Android·ADB가 필요하지 않다.

**다음 행동:** 소유자가 P1-R의 별도 설계·측정 승인 여부를 결정한다.
