# T6.6A — Authoritative bundle payload 귀속·전송·압축 특성화

## 1. 판정·범위·증거 구분

**T6.6A COMPLETE — READY FOR T6.6B DESIGN**

제품 런타임을 변경하지 않고 실제 backend와 모바일 parser/저장 API로 특성화를 완료했다. 압축 배포, hot/cold 또는 delta 구현, 금융 알고리즘 변경, T6.6B–E 구현을 뜻하지 않는다. 실기기 gate는 post-T6.6이며 아래 수치는 모두 HOST/synthetic이다.

- **이번 실측:** 새 migrated SQLite 6종, 실제 `GET /api/authoritative-state`, byte 구간 귀속, Python gzip/시스템 Brotli, 실제 Dart admission·OfflineStore, HTTP wrapper와 실제 Uvicorn의 HTTP 관측.
- **이전 증거 재검토:** 보존된 synthetic specimen과 B-3/B-4 독립 감사의 RTT=0 end-to-end 결과. 이번에 80-cell 감사를 다시 실행했다고 주장하지 않는다.
- **모델:** 주어진 처리량에서 body bits/throughput으로 계산한 전송 시간과 HOST codec 비용.
- **가정/설계 입력:** cold 분리·delta value budget. 유효한 미래 프로토콜 또는 복구 보증이 아니다.

시작 시 branch `main`, HEAD/main/origin/main/실제 remote main 모두 `597a936d8fc53f35c693705c320223686a657f0e`, working tree clean을 확인했다. 변경은 문서, 격리 진단 도구/테스트, compact aggregate뿐이다. 최종 문서 commit identity는 Git 및 최종 실행 보고서로 확인한다.

`AGENTS.md`, architecture의 서버 authority 계약, domain/project-state/known-issues, B-3 구현 보고서, Snapshot·Offline 복구 계약을 대조했다. backend가 확정 금융 계산을 소유한다. 모바일 A/B admission·Unicode·exact-money·복구 가능성·owner/generation·durable publication은 그대로다. OfflineProjection을 재계산 oracle로 쓰지 않았다.

## 2. 환경·재현 방법·fixture 구성

Intel Core i7-8750H, Linux 6.8.0-146 x86_64, RAM 약 23.3GiB, Python 3.12.3, SQLite 3.45.1, Flutter 3.47.4 / Dart 3.13.3 test JIT다. CPU 주파수·thermal 상태를 고정한 실험실이나 실기기가 아니다. 주 벤치마크와 전체 회귀는 순차 실행했다. 서버 계측은 실제 handler를 호출하는 TestClient 경계를 포함한다.

Seed 1234, 서버 평가일 2026-10-05, UTC+540분, synthetic owner ID 1, 현행 policy registry를 고정했다. Snapshot export는 2026-10-05T12:00:00Z, synthetic DB의 created/updated/confirmation timestamp도 고정했다. 생성 child의 UUID형 payment key는 DB 생성 단계에서 결정적 32자 key로 지정했다. 응답을 임의 재직렬화하거나 사후 reseal하지 않았다.

기존 rich backend fixture의 할인/0원 override/공과금/통행료 그룹·partial payment/Claim/Family/fixed/frozen/cash/NULL-date archived actual을 사용했다. 주 4종은 추가 current expense 100행을 동일하게 유지하고 archive만 늘린다. 다양성 control은 seed 고정 random hex와 한글·emoji를 더한 긴 title/merchant이며 실제 사용자 분포를 주장하지 않는다.

| fixture | ledger | current | archive | typed entries | confirmed source | policy binding | raw UTF-8 bytes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| current-like | 376 | 105 | 271 | 104 | 1 | 4 | 306,370 |
| 1k | 1,000 | 105 | 895 | 104 | 1 | 4 | 653,317 |
| 5k | 5,000 | 105 | 4,895 | 104 | 1 | 4 | 2,889,309 |
| 10k | 10,000 | 105 | 9,895 | 104 | 1 | 4 | 5,684,312 |
| confirmed-heavy 600 | 1,200 | 1,200 | 0 | 600 | 600 | 4 | 1,696,801 |
| 10k 다양성 control | 10,000 | 105 | 9,895 | 104 | 1 | 4 | 6,180,091 |

모두 HTTP 200, Content-Type `application/json`, Content-Encoding 없음이다. 정확한 body SHA-256·response headers는 [attribution.json](benchmarks/t66a/attribution.json), parameter/environment는 [environment.json](benchmarks/t66a/environment.json)에 있다. 6종 모두 실제 canonical Snapshot admission 및 migrated DB INSERT/relationship 복구 경로를 SAVEPOINT 안에서 통과했고 rollback했다. 같은 관측의 legacy 14-GET state/Snapshot과 동등함도 검사했다. 별도 fresh DB 두 개의 376 응답이 byte-identical함을 회귀 테스트로 고정했다.

주 fixture·codec·Dart 단계는 warmup 3회 + measured 20회다. p95는 nearest-rank 19번째 표본이며 보편적 tail 보증이 아니다. min/max/stdev와 모든 primary timing 표본은 [samples.csv](benchmarks/t66a/samples.csv)에 있다. RSS는 별도 child 1회, 50k는 제한된 one-shot으로 구분한다.

## 3. 실제 bundle 구조와 소유권

Top-level은 정확히 `bundle_version`, `principal`, `authority`, `snapshot`, `state`다.

- `authority`: revision, Snapshot state fingerprint, evaluation date, owner/family discount defaults.
- `snapshot`: v7, recurring ownership version, exported_at, all-range, card_charge_policy, data 11개 테이블, manifest, snapshot_id.
- `state`: Summary, entries, confirmed planned entries, panels, recent cash, detailed payment status, judgment, settings, month-close, owner/family month policy, transit profile의 12개 typed projection.
- 별도 최상위 archive projection은 없다. 과거 원장은 주로 Snapshot의 ledger rows에 있다. current_month_spendable은 Summary 안에 있다.

`authoritative_state._construct`는 하나의 금융 read transaction과 고정 date/context로 만들며 `_prepare`가 model/금액/JSON response를 준비한다. 새 terminal guard 후에만 성공한다. 이 코드를 변경하지 않았다. Snapshot은 canonical UTF-8 SHA-256을 사용하나 hash는 서명 또는 독립 금융 정확성 증명이 아니다. HTTP JSONResponse의 field 순서/표현과 Snapshot의 sort-key hash canonicalization을 혼동하지 않았다.

## 4. 정확한 byte accounting

`JsonBytes`는 실제 응답 bytes의 원래 offset을 읽는다. UTF-8 한글/emoji, escaped quote/backslash/NUL, 공백, 원문 number lexeme를 보존한다. JSON 재직렬화 추정이나 String.length를 사용하지 않는다. 선택한 value span은 서로 겹치지 않으며 그 밖의 key/colon/comma/bracket/공백 bytes는 `json_structure`로 정확히 한 번 센다.

| fixture | 선택한 disjoint value bytes | 외곽 구조 bytes | 합계 = 실제 body |
| --- | --- | --- | --- |
| current-like | 305,365 | 1,005 | 306,370 |
| 1k | 652,312 | 1,005 | 653,317 |
| 5k | 2,888,304 | 1,005 | 2,889,309 |
| 10k | 5,683,307 | 1,005 | 5,684,312 |
| confirmed-heavy 600 | 1,695,796 | 1,005 | 1,696,801 |
| 10k 다양성 control | 6,179,086 | 1,005 | 6,180,091 |

각 row object 안의 field 이름·delimiter도 해당 table/projection payload에 이미 포함된다. 따라서 외곽 구조만 1,005바이트라는 것을 전체 JSON overhead가 작다는 뜻으로 읽으면 안 된다. 이 규칙으로 6종 모두 exact reconciliation PASS다. 포괄적인 Snapshot/typed/history share는 별도 분석 view이며 disjoint 합계에 다시 더하지 않는다.

| fixture | Snapshot bytes / share | state bytes / share | 그 밖의 최상위 bytes |
| --- | --- | --- | --- |
| current-like | 218,421 / 71.29% | 87,661 / 28.61% | 288 |
| 1k | 565,368 / 86.54% | 87,661 / 13.42% | 288 |
| 5k | 2,801,359 / 96.96% | 87,661 / 3.03% | 289 |
| 10k | 5,596,362 / 98.45% | 87,661 / 1.54% | 289 |
| confirmed-heavy 600 | 716,501 / 42.23% | 980,012 / 57.76% | 288 |
| 10k 다양성 control | 6,087,031 / 98.49% | 92,771 / 1.50% | 289 |

## 5. Snapshot table 귀속

아래는 10k의 전체 11개 테이블이다. 행 payload는 원문 array의 row object와 array delimiter를 포함한다. manifest nonhash에는 columns/row_count/field 이름 등이 있고 hash는 SHA-256 string token 66바이트다. 부모 key·delimiter는 위 외곽 구조에서 센다. 다른 fixture의 같은 상세 지표는 JSON과 부록에 모두 보존했다.

| table | rows | row payload | manifest nonhash | hash | 귀속 합계 | Snapshot % | bundle % | 행 avg / median / p95 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ledger_entries | 10,000 | 5,586,627 | 391 | 66 | 5,587,084 | 99.83 | 98.29 | 557.7 / 558.0 / 558.0 |
| app_labels | 18 | 1,611 | 65 | 66 | 1,742 | 0.03 | 0.03 | 88.4 / 87.0 / 109.0 |
| monthly_panels | 4 | 1,336 | 256 | 66 | 1,658 | 0.03 | 0.03 | 332.8 / 331.5 / 337.0 |
| cash_flows | 5 | 910 | 138 | 66 | 1,114 | 0.02 | 0.02 | 180.8 / 178.0 / 193.0 |
| card_payment_events | 1 | 293 | 169 | 66 | 528 | 0.01 | 0.01 | 291.0 / 291.0 / 291.0 |
| app_settings | 5 | 371 | 64 | 66 | 501 | 0.01 | 0.01 | 73.0 / 73.0 / 74.0 |
| card_payment_batch_items | 3 | 298 | 97 | 66 | 461 | 0.01 | 0.01 | 98.0 / 97.0 / 100.0 |
| card_payment_deferrals | 0 | 2 | 244 | 66 | 312 | 0.01 | 0.01 | — |
| card_payment_allocations | 1 | 117 | 109 | 66 | 292 | 0.01 | 0.01 | 115.0 / 115.0 / 115.0 |
| card_payment_batches | 1 | 110 | 87 | 66 | 263 | 0.00 | 0.00 | 108.0 / 108.0 / 108.0 |
| notification_candidate_registrations | 0 | 2 | 112 | 66 | 180 | 0.00 | 0.00 | — |

10k ledger array만 5,586,627바이트다. per-row hash 목록은 없고 table별 hash/columns/count가 있으므로 manifest는 주로 고정 크기이며 row_count 자릿수 정도만 증가한다. 핵심 증가는 manifest가 아니라 원문 row다.

| 10k ledger 표현 | bytes | ledger array % |
| --- | --- | --- |
| 반복 field-name string tokens | 3,260,000 | 58.35 |
| 모든 value tokens | 1,826,626 | 32.70 |
| row/array 구두점 | 500,001 | 8.95 |
| 위 value 중 null (중복 집계 금지) | 519,924 | 9.31 |

Field 이름 326만 바이트가 반복되므로 lossless compression의 효과가 크다. 그렇다고 Snapshot column을 삭제할 권한이 생기는 것은 아니다.

## 6. Typed projection과 실제 성장 경계

주 376/1k/5k/10k에서 state는 모두 87,661바이트, entries 104행이다. 이는 fixture의 hot 구성을 고정했기 때문이지 모든 제품 projection에 row-count 상한이 있다는 증거가 아니다.

| state section | 376 bytes | 1k bytes | 5k bytes | 10k bytes | heavy600 bytes |
| --- | --- | --- | --- | --- | --- |
| month_close_status | 367 | 367 | 367 | 367 | 307 |
| entries | 78,593 | 78,593 | 78,593 | 78,593 | 477,049 |
| panels | 2,024 | 2,024 | 2,024 | 2,024 | 2 |
| summary | 492 | 492 | 492 | 492 | 470 |
| card_payment_status | 2,848 | 2,848 | 2,848 | 2,848 | 394 |
| judgment | 1,164 | 1,164 | 1,164 | 1,164 | 1,183 |
| confirmed_planned_entries | 774 | 774 | 774 | 774 | 476,926 |
| cash_flows | 452 | 452 | 452 | 452 | 2 |
| settings | 116 | 116 | 116 | 116 | 116 |
| owner_discount_month | 312 | 312 | 312 | 312 | 23,044 |
| family_discount_month | 244 | 244 | 244 | 244 | 244 |
| transit_discount_profile | 53 | 53 | 53 | 53 | 53 |

실제 query/consumer 경계:

- entries는 `book_section=current`이며 해당 달 confirmed planned source를 제외한다. 미마감 과거 current도 남을 수 있어 calendar current-month에 무조건 bounded라고 말할 수 없다.
- confirmed는 평가월에 확인된 active planned source 수, panels는 fixed configuration과 미삭제 Claim/Family/frozen 큐 수에 의존한다. 이 큐는 월이 바뀌어도 보존된다.
- cash typed projection은 직전월 1일~당월 말일 범위지만 그 기간의 row 수에는 상한이 없다. Snapshot cash는 미래 날짜까지 전체 보존한다.
- payment는 active batch 중심이나 batch member/event 수에 상한을 두지 않는다. 단순히 historical ledger N과 같이 증가하지 않는 이번 fixture와 구별한다.
- settings는 비민감 설정 전체이므로 월별 policy/profile key 이력이 증가할 수 있다. registry binding/covered_through도 영원히 고정이라고 가정하지 않는다.
- Summary/judgment는 작은 결과이나 이를 계산하는 backend 입력/전체 scan 비용이 작은 것은 아니다.

## 7. 중복 표현: byte 동일성과 의미 중첩의 구별

Stable ID를 사용해 Snapshot raw row와 typed row의 겹침을 센다. 아래 token bytes는 같은 entity/동명 field의 **원문 token이 실제로 동일한** 부분만 센다. 이 합계가 곧 제거 가능한 protocol bytes는 아니다.

| 10k projection | 동일 ID records | 동일 value-token bytes | 완전히 동일한 row bytes |
| --- | --- | --- | --- |
| entries | 104 | 13,581 | 0 |
| confirmed_planned_entries | 1 | 145 | 0 |
| panels | 4 | 219 | 0 |
| cash_flows | 4 | 119 | 0 |

전체 row의 byte-identical 중복은 0이며 typed fields/순서/derived 값이 다르다. 동명 raw value-token 중복은 합계 14,064바이트다. 반복 field 이름/리터럴과 별개다. 현재 10k의 주된 문제는 같은 history의 여러 사본이 아니라 **현재 UI와 관계없이 raw history 전체 한 벌을 매번 보내는 것**이다.

Confirmed-heavy는 source 600 + child 600의 raw Snapshot과 typed child/confirmed source가 필요해 state 비중이 57.76%다. 확인 원금/표시 할인/실부담과 raw template를 같은 뜻으로 합쳐 제거할 수 없다. Snapshot은 Apply(B,J)/restore, typed state는 현재 UI와 Offline display를 위한 계약이다. 잠재 절감은 미래 표현/동기화 설계에서 별도 증명해야 한다.

## 8. 서로 다른 10k specimen의 차이

보존 synthetic 자료를 원문 byte span으로 다시 읽었다. 모두 bundle v1/Snapshot v7 및 같은 top-level/state key 집합이며 protocol을 축소한 결과가 아니다.

| 출처 | body | Snapshot | typed state | typed entries | current / archive |
| --- | --- | --- | --- | --- | --- |
| 통합 audit | 5,684,312 | 5,596,362 | 87,661 | 104 | 105 / 9,895 |
| B-3 초기 specimen | 5,635,112 | 5,547,479 | 87,344 | 104 | 105 / 9,895 |
| 이전 7.48MB audit | 7,479,394 | 5,525,277 | 1,953,828 | 2,502 | 2,503 / 7,497 |
| 이번 고정 fixture | 5,684,312 | 5,596,362 | 87,661 | 104 | 105 / 9,895 |

7,479,394-byte generator는 rich state에 약 4분의 1 current / 4분의 3 archive를 추가하고 payment key·금액·sort/title 구성이 다르다. typed entries 2,502행과 약 1.89MB의 entries가 핵심 차이다. 통합 audit는 current 추가 100행을 고정한다. B-3 초기 5,635,112와 통합 5,684,312 차이는 title/merchant·sort_order 자릿수 등 실제 raw 문자열/숫자와 작은 projection 차이다.

이번 current-like 306,370과 5k 2,889,309는 통합 audit의 306,369 / 2,889,308보다 1바이트 크다. Synthetic timestamp/key 고정에 따른 UPDATE가 revision을 각각 4/5자리로 늘렸기 때문이다. Snapshot/state 크기는 동일하고 1k/10k는 revision 자릿수가 이미 같아 body 크기도 같다. SHA는 고정 timestamp/key 내용 때문에 과거 SHA와 달라지는 것이 정상이다. [specimen-comparison.json](benchmarks/t66a/specimen-comparison.json)에 출처·SHA·구성을 보존했다.

이번 실제 legacy 14 response body 합계(재직렬화한 assembled old JSON이 아님)는 10k 11,280,605바이트다. 보존된 old assembled JSON의 11,280,839바이트를 실제 14 response의 11,280,605와 혼용하지 않았다.

## 9. Hot / cold / shared / control

아래는 10k의 물리적으로 겹치지 않는 분할이다. Snapshot data의 row array를 SHARED로 놓고, archive에서 active batch member 및 active recurring child를 제외한 9,891개 row object를 잠재 COLD로 분리했다. 이 분류는 **향후 transport/cache 경계 후보**이지 authoritative B에서 삭제 가능한 데이터가 아니다.

| 분류 | bytes | bundle % | 정상 refresh / Offline·recovery 의미 |
| --- | --- | --- | --- |
| COLD 후보 | 5,516,500 | 97.05 | 일반 현재 UI에는 대체로 불필요; 전체 B 복구/조정에는 여전히 필요 |
| SHARED raw remainder | 75,177 | 1.32 | 현재 원장·active 관계·설정·배열 구조; 동일 authority 아래 복구에 필요 |
| HOT typed values | 87,439 | 1.54 | 현재 화면/상태 설치; 서버 계산 결과 그대로 소비 |
| CONTROL + 외곽 구조 | 5,196 | 0.09 | policy/manifest/revision/fingerprint/identity/schema/date 및 key·delimiter |
| 합계 | 5,684,312 | 100.00 | 원문 body와 정확히 일치 |

Archive 전체 row bytes는 5,518,683이며 cold 후보와 다르다. NULL-date archived confirmed child와 active payment member를 무조건 cold로 빼면 안 된다. 역사 row를 매번 내려주지 않더라도 cached cold와 hot을 같은 revision/fingerprint의 **완전한 recoverable B**로 재구성·원자적으로 게시해야 한다. 기존 Offline epoch의 B는 고정이고 J는 input-only다.

## 10. 성장 모델

동일 hot 구성의 4종에 대한 기술적 least-squares fit:

- body ≈ 95265 + N × 558.882 bytes
- Snapshot ≈ 7316 + N × 558.882 bytes
- typed state = 87,661 bytes (이번 고정 fixture에 한함)

최대 absolute fit residual은 약 966바이트다. ID/title/sort/count 자릿수 변화가 있어 완벽한 직선이 아니다. 임의 사용자 문자열·current 비율·active payment·confirmed 밀도까지 이 식으로 일반화하지 않는다. 다양성 control과 7.48MB specimen이 그 반례다. [growth.json](benchmarks/t66a/growth.json)에 식과 residual을 기록했다.

역사 row와 metadata의 증가를 분리하면 다음과 같다. archive/cold는 row object 자체의 원문 bytes이며 array delimiter는 포함하지 않는다. manifest 및 non-data는 앞의 disjoint value span 합계로, 부모 key·delimiter는 외곽 구조에 있다. 두 metadata 열은 서로 포함 관계이므로 더하지 않는다.

| fixture | archive row bytes | cold 후보 row bytes | manifest value bytes | Snapshot non-data value bytes |
| --- | --- | --- | --- | --- |
| 376 | 150,368 | 148,185 | 2,662 | 3,966 |
| 1k | 496,690 | 494,507 | 2,663 | 3,967 |
| 5k | 2,728,681 | 2,726,498 | 2,663 | 3,967 |
| 10k | 5,518,683 | 5,516,500 | 2,664 | 3,968 |

주 구성의 376→10k 증가는 archive row object 5,368,315바이트와 metadata value 2바이트다. 이 구간에서 추가 역사 row당 archive object는 평균 약 557.8바이트이며 delimiter·자리수 등까지 포함한 전체 body의 회귀 기울기 558.9바이트와 구별한다.

## 11. 현재 compression 설정과 실제 HTTP

제품 FastAPI에는 gzip/Brotli middleware가 없고 API client도 별도 codec을 추가하지 않는다. **실제 IOClient request는 Accept-Encoding: gzip**이다. gzip을 지원한다는 것과 서버가 gzip으로 보낸다는 것은 다르다.

무변경 FastAPI를 실제 local Uvicorn으로 실행해 3회 raw HTTP로 확인했다. 매번 Content-Encoding 없음, Content-Type application/json, Content-Length 306370, SHA가 frozen 376과 동일했다. headers에는 Cache-Control no-store, Pragma, X-Content-Type-Options, Referrer-Policy, X-Frame-Options, Permissions-Policy가 보존됐다. [native-http.json](benchmarks/t66a/native-http.json)이 원문 header 관측이다.

저장소 runbook의 Apache 예시에는 compression 활성화가 명시되지 않는다. **실제 운영 Apache/TLS/proxy 설정은 접근하지 않았으므로 운영 compression 활성 여부를 주장하지 않는다.** 확인 범위는 이 local backend/transport다.

## 12. HTTP body / header / transport 층

| 층 | 방법과 포함 범위 | 결과 |
| --- | --- | --- |
| A | actual JSONResponse 원문 bytes | fixture SHA와 body 길이 실측 |
| B | wrapper/Uvicorn socket의 HTTP entity bytes | identity 및 gzip entity 실측 |
| C | raw request line/status line + 모든 header CRLF + entity | 실제 HTTP byte 수 실측 |
| D | packet capture의 TCP/IP/TLS/retransmit | 직접 측정하지 않음 |

실제 Uvicorn 376: request headers 194 + request entity 0, response headers 350 + entity 306370 = response HTTP 306720바이트, 양방향 HTTP 합 306914바이트다. HTTP/1.1, TLS 없음, chunking 없음, 이 raw probe는 Connection: close다.

Frozen wrapper의 실제 Dart 관측(각 mode/fixture connection 1개를 23 request 동안 재사용):

| fixture | identity body / header | gzip6 entity / header | request header identity / gzip | body available identity / gzip ms (median) |
| --- | --- | --- | --- | --- |
| current-like | 306,370 / 75 | 11,474 / 121 | 188 / 184 | 2.79 / 5.62 |
| 1k | 653,317 / 75 | 18,173 / 121 | 189 / 185 | 3.44 / 6.32 |
| 5k | 2,889,309 / 76 | 58,385 / 121 | 189 / 185 | 12.65 / 23.65 |
| 10k | 5,684,312 / 76 | 108,916 / 122 | 190 / 186 | 29.51 / 45.05 |
| confirmed-heavy 600 | 1,696,801 / 76 | 61,453 / 121 | 193 / 189 | 6.16 / 15.56 |

10k gzip response HTTP는 108916 + 122 = **109038바이트**다. request 186을 더하면 양방향 HTTP는 109224다. identity의 대응 값은 response 5684388, 양방향 5684578이다. 이 header 수에는 wrapper URL prefix와 synthetic credential 길이가 반영되어 실제 release request header와 같다고 주장하지 않는다. Wrapper header는 Uvicorn header와 별도로 기록한다. TLS/TCP/IP overhead, ACK, 재전송, 암호화 record는 포함하지 않는다.

추가 wrapper actual-handler probe 3회는 judgment RNG를 다시 seed하지 않아 306398–306421바이트로 달랐다. 이 exploratory 관측을 frozen-size/압축 비교에 섞지 않았다. 위 native Uvicorn probe는 RNG도 고정해 원문 SHA가 일치한다.

## 13. Gzip / Brotli 손실 없는 압축

정확히 같은 captured bytes를 gzip 1/6/9, Brotli 4/6/9로 반복했다. gzip은 mtime=0이며 JSON 재직렬화/정규화가 없다. Python Brotli package는 없지만 이미 설치된 `libbrotlienc.so.1` / `libbrotlidec.so.1`의 C API를 diagnostic ctypes로 사용했다. 새 도구/패키지는 설치하지 않았고 제품 의존성도 추가하지 않았다.

대표 gzip6 / Brotli4 결과:

| fixture | raw bytes | gzip6 bytes | gzip/raw % · 감소 % | Brotli4 bytes | Brotli/raw % · 감소 % |
| --- | --- | --- | --- | --- | --- |
| current-like | 306,370 | 11,474 | 3.75 · 96.25 | 8,014 | 2.62 · 97.38 |
| 1k | 653,317 | 18,173 | 2.78 · 97.22 | 10,339 | 1.58 · 98.42 |
| 5k | 2,889,309 | 58,385 | 2.02 · 97.98 | 25,792 | 0.89 · 99.11 |
| 10k | 5,684,312 | 108,916 | 1.92 · 98.08 | 43,033 | 0.76 · 99.24 |
| confirmed-heavy 600 | 1,696,801 | 61,453 | 3.62 · 96.38 | 31,976 | 1.88 · 98.12 |
| 10k 다양성 control | 6,180,091 | 568,847 | 9.20 · 90.80 | 477,248 | 7.72 · 92.28 |

10k와 다양성 control의 level 비교(시간은 HOST wall median, ms):

| fixture | codec / level | bytes | 압축 median / p95 | 해제 median / p95 |
| --- | --- | --- | --- | --- |
| 10k | gzip 1 | 136,750 | 12.45 / 12.52 | 3.47 / 3.51 |
| 10k | gzip 6 | 108,916 | 28.13 / 28.23 | 3.31 / 3.34 |
| 10k | gzip 9 | 107,179 | 59.13 / 65.13 | 3.63 / 3.75 |
| 10k | brotli 4 | 43,033 | 15.24 / 15.55 | 1.79 / 1.91 |
| 10k | brotli 6 | 47,811 | 38.91 / 39.16 | 1.93 / 1.98 |
| 10k | brotli 9 | 41,392 | 64.70 / 64.94 | 1.95 / 2.09 |
| 10k 다양성 control | gzip 1 | 641,459 | 23.56 / 23.70 | 7.35 / 7.49 |
| 10k 다양성 control | gzip 6 | 568,847 | 48.54 / 48.73 | 6.92 / 7.03 |
| 10k 다양성 control | gzip 9 | 566,044 | 73.09 / 73.73 | 6.96 / 7.19 |
| 10k 다양성 control | brotli 4 | 477,248 | 32.55 / 33.49 | 4.22 / 4.33 |
| 10k 다양성 control | brotli 6 | 511,774 | 94.46 / 95.70 | 6.74 / 6.97 |
| 10k 다양성 control | brotli 9 | 512,360 | 190.79 / 195.80 | 6.81 / 7.12 |

Brotli quality가 커졌다고 크기가 단조 감소하지 않았다. 이번 native encoder/내용에서 q4가 q6보다 작고 빠른 경우가 있으며 관측값을 그대로 보존했다. 극도로 반복되는 fixture의 98~99% 감소를 일반 보장으로 쓰지 않는다. 긴 random hex control은 raw도 49.6만 바이트 더 크므로 순수 entropy만 바꾼 실험이 아니라는 한계도 있다.

36개 fixture×codec 조합에서 최종 decompressed bytes == original bytes 및 SHA 동일성을 확인했다. 유효한 한글/emoji/combining 표현·money numeric tokens·Snapshot hash·principal을 바꾸지 않는다. 잘못된 표현을 sanitize하는 경로가 아니다.

## 14. CPU·메모리·실제 모바일 transport 실험

대표 codec CPU median은 다음과 같다. wall과 process CPU는 다르며 전체 통계는 [compression.csv](benchmarks/t66a/compression.csv)에 있다.

| fixture | gzip6 encode / decode CPU ms | Brotli4 encode / decode CPU ms |
| --- | --- | --- |
| current-like | 2.01 / 0.24 | 1.06 / 0.14 |
| 1k | 3.82 / 0.44 | 1.80 / 0.23 |
| 5k | 12.87 / 1.43 | 6.27 / 0.77 |
| 10k | 28.13 / 3.31 | 15.24 / 1.79 |
| confirmed-heavy 600 | 9.00 / 1.04 | 4.06 / 0.45 |
| 10k 다양성 control | 48.54 / 6.93 | 32.55 / 4.22 |

10k 별도 child RSS high-watermark: gzip 모든 level 28,800KiB, Brotli4 37,652KiB, Brotli6 38,372KiB, Brotli9 66,944KiB. 시작 high-watermark가 이미 28,800KiB라 gzip 추가 allocation이 0이라는 뜻은 아니다. coarse process RSS이고 codec allocator peak나 device peak memory가 아니다. 주 Python 생성/귀속 전체 peak는 372,036KiB, 50k probe는 646,140KiB다.

임시 wrapper에서만 gzip6 + Content-Encoding/Vary를 켰다. 실제 MoneyNoteApiClient/IOClient는 자동 해제했고 5종 × 2 mode × (3 warmup + 20 sample)의 **230개 body 모두 원문 byte와 같았으며 strict B-2 admission/candidate가 성공**했다. Diagnostic helper가 baseline을 게시한다고 표현하지 않았다. Frozen 단계 테스트가 실제 OfflineStore로 게시/읽기를 수행했다. Accept-Encoding 거부(`gzip;q=0`, identity) 및 허용은 별도 진단 단위 테스트로 검사했다.

Dart HOST의 별도 gzip 해제 median/p95: 10k 5.04 / 5.29ms. Python decode와 동일 수치로 취급하지 않는다. HTTP body-available에는 socket read·서버 압축·자동 해제가 포함되며 이 값에서 decode만 정확히 분리했다고 주장하지 않는다. Loopback에서는 gzip의 CPU 비용 때문에 10k body-available이 약 29.51→45.05ms로 오히려 늘었다. 대역폭 제한이 없는 local 관측과 느린 망 모델은 별개다.

기본 Dart IO transport는 Brotli를 광고하지 않는다. Brotli의 offline 이점이 현재 모바일 자동 해제 지원 또는 배포 준비 완료를 뜻하지 않는다. 추가 capability/호환성 검토가 필요하다.

## 15. 대역폭 손익분기 모델

Decimal Mbps, body bits/throughput, 지속 goodput가 일정하다는 가정이다. RTT/handshake/TLS/header/loss/streaming overlap은 제외했다. HOST encode+Python decode wall median을 별도 차감한 단순 직렬 모델이며 phone latency가 아니다.

| 10k Mbps | raw 전송 s | gzip6 전송 s | Brotli4 전송 s | gzip net 절감 ms | Brotli net 절감 ms |
| --- | --- | --- | --- | --- | --- |
| 1 | 45.474 | 0.871 | 0.344 | 44571.7 | 45113.2 |
| 5 | 9.095 | 0.174 | 0.069 | 8889.2 | 9009.0 |
| 10 | 4.547 | 0.087 | 0.034 | 4428.9 | 4496.0 |
| 50 | 0.909 | 0.017 | 0.007 | 860.6 | 885.6 |
| 100 | 0.455 | 0.009 | 0.003 | 414.6 | 434.3 |

10k의 HOST encode+decode는 gzip6 약 31.44ms, Brotli4 약 17.03ms다. 동일 가정의 break-even은 각각 약 1419 / 2651Mbps다. gzip decode를 실제 Dart HOST 5.04ms로 바꾸면 net 절감은 약 1.73ms 줄어든다. 실제 이동통신 latency·배터리·thermal·memory 측정은 아니다. 모든 fixture의 모델은 [bandwidth-model.json](benchmarks/t66a/bandwidth-model.json)에 있다.

gzip1→6의 10k 추가 절감은 27,834바이트, encode wall 증가는 약 15.68ms다. 느린 망에는 level6, 빠른 망/CPU budget에는 level1을 검토할 근거이며 고정 배포 level을 여기서 정하지 않는다. q9는 작은 추가 byte 절감에 큰 CPU 비용을 지불한다.

## 16. Backend / client latency 귀속

이번 actual handler 관측(각 warmup 3 + 20, median/p95 ms):

| fixture | backend 요청 경계 | construct (inclusive) | Snapshot export (construct 내부) | prepare (inclusive) | JSON render (prepare 내부) |
| --- | --- | --- | --- | --- | --- |
| current-like | 72.1 / 79.4 | 53.2 / 57.9 | 23.6 / 24.6 | 11.1 / 13.0 | 2.7 / 3.2 |
| 1k | 164.7 / 177.5 | 133.4 / 140.5 | 59.6 / 66.2 | 24.7 / 26.2 | 6.2 / 6.5 |
| 5k | 760.0 / 864.2 | 642.2 / 734.1 | 301.6 / 340.1 | 106.6 / 117.6 | 31.3 / 34.7 |
| 10k | 1348.5 / 1670.9 | 1138.2 / 1417.6 | 557.6 / 683.9 | 191.1 / 233.4 | 55.9 / 68.2 |
| confirmed-heavy 600 | 438.4 / 492.8 | 349.5 / 396.9 | 86.4 / 97.4 | 78.6 / 88.4 | 15.4 / 17.4 |
| 10k 다양성 control | 1665.4 / 1802.8 | 1423.1 / 1542.2 | 677.6 / 743.7 | 225.4 / 243.3 | 74.8 / 80.9 |

Snapshot export를 construct에 더하거나 JSON render를 prepare에 다시 더하지 않는다. prepare는 JSON뿐 아니라 model/money validation·dump를 포함한다. 요청 경계에는 auth/TestClient/middleware/terminal guard도 있다. terminal guard median은 약 0.8–0.9ms다. Compression은 이 read/검증/financial 계산을 줄이지 않는다.

이번 client 단계 median(ms); p95/min/max/stdev는 client-summary와 raw CSV에 있다.

| 단계 | 376 | 1k | 5k | 10k | heavy600 |
| --- | --- | --- | --- | --- | --- |
| utf8 | 1.664 | 3.482 | 15.325 | 34.850 | 10.749 |
| raw_money | 24.486 | 52.316 | 233.379 | 538.226 | 157.248 |
| json_decode | 4.033 | 8.663 | 40.191 | 103.559 | 25.684 |
| unicode | 0.865 | 1.817 | 13.700 | 18.599 | 5.466 |
| presence_types | 9.195 | 19.468 | 90.478 | 202.508 | 86.019 |
| money | 0.521 | 1.058 | 5.000 | 11.148 | 3.133 |
| snapshot_authority_relationships | 32.736 | 87.395 | 419.760 | 985.407 | 176.688 |
| freeze | 2.377 | 5.579 | 25.875 | 71.162 | 14.618 |
| typed_models | 0.300 | 0.313 | 0.328 | 0.429 | 2.729 |
| candidate | 0.007 | 0.007 | 0.008 | 0.009 | 0.009 |

10k parser+typed는 1970.1 / 2002.0ms다. 약 985ms의 Snapshot/authority/relationship, 538ms raw-money scan, 203ms presence/type 등이 남는다. Unicode 약 18.6ms를 없애는 방식으로 안전성을 희생하지 않는다. 재직렬화된 decoded JSON을 받으면 exact-money raw-token 보증이 약해지므로 transport compression만 lossless로 해제해 원문 bytes를 전달해야 한다.

이전 독립 B-3/B-4 RTT=0 refresh end-to-end reference(이번 재실행 아님):

| fixture | 이전 integrated audit total median / p95 ms |
| --- | --- |
| 376 | 187.3 / 204.4 |
| 1000 | 421.6 / 458.7 |
| 5000 | 1932.0 / 2090.0 |
| 10000 | 3996.0 / 4311.7 |

출처 원본 SHA와 20개 observation ID를 [reference-latency.json](benchmarks/t66a/reference-latency.json)에 보존했다. 이번 개별 단계 median들을 더해 새 AppState end-to-end 실측이라고 주장하지 않는다. Fixture timestamp/revision과 HOST 실행 상태가 달라 과거 1740.7ms backend와 이번 1348.5ms 차이를 제품 최적화 효과로 해석하지 않는다.

## 17. OfflineBaseline 크기와 durable 비용

| fixture | HTTP body | baseline serialized = durable bytes | encode median / p95 ms | publication median / p95 ms | 추가 readback median / p95 ms |
| --- | --- | --- | --- | --- | --- |
| current-like | 306,370 | 290,225 | 4.35 / 5.60 | 13.95 / 20.84 | 6.96 / 8.51 |
| 1k | 653,317 | 637,172 | 9.17 / 12.62 | 31.29 / 34.96 | 14.12 / 19.84 |
| 5k | 2,889,309 | 2,873,163 | 43.01 / 46.66 | 128.64 / 136.88 | 72.18 / 84.87 |
| 10k | 5,684,312 | 5,668,166 | 97.32 / 100.34 | 269.73 / 273.64 | 177.66 / 182.69 |
| confirmed-heavy 600 | 1,696,801 | 1,483,861 | 30.28 / 32.15 | 79.92 / 81.98 | 41.82 / 50.11 |
| 10k 다양성 control | 6,180,091 | 6,163,945 | 100.08 / 105.75 | 281.18 / 291.84 | 165.26 / 171.04 |

OfflineBaseline은 bundle의 복사본이 아니라 기존 schema v4의 user/synced_at/typed state/authoritative Snapshot/fingerprint/defaults 표현이다. 10k durable 파일 5,668,166바이트로 HTTP보다 16,146바이트 작지만 역사 Snapshot을 여전히 거의 전부 보존한다. raw Snapshot과 일부 typed raw 정보의 중첩도 남는다. HTTP 압축을 켜더라도 이 저장 크기/JSON encode/hash/readback 비용은 자동으로 줄지 않는다.

실제 replaceBaseline의 임시 flush·JSON readback·atomic rename을 사용했고, 별도 loadBaseline 후 모든 field 및 고정 timestamp의 serialized bytes가 같음을 확인했다. 이는 desktop filesystem 결과이며 실제 Android UFS write나 physical device latency가 아니다. 메모리의 logical object footprint는 직접 측정하지 않았다.

진단 total에는 standalone baseline encode와 추가 typed readback을 넣었으므로 normal AppState total과 다르다. 10k 진단 total 2514.7ms를 제품 operation latency로 쓰지 않는다. 별도 per-sample parser+baseline construction+publication은 median 2239.8ms이며 network/backend는 포함하지 않는다.

## 18. 선택적 50k / 100k

50k는 2GiB address-space / 90 CPU-second / 외부 120초 제한 아래 한 번 관측했다. Body 28,164,304, Snapshot 28,076,353, typed 87,661바이트, route 7265.8ms, process peak RSS 646,140KiB다. gzip6 509,817, Brotli4 183,764바이트다. Compression의 주 결과 20회 통계와 달리 이 probe는 warmup 3 + 관측 1회이며 tail 통계가 아니다. Mobile pipeline은 실행하지 않았다.

이 Snapshot alone이 25MiB(26,214,400바이트)를 넘는다. 현재 config/security의 Snapshot restore 및 Mobile Wins request limit과 충돌할 수 있으므로 future 규모 설계의 명시적 gate다. 실제 50k restore HTTP의 413을 이번에 실행했다고 주장하지 않는다. HTTP 압축만으로 decoded request/restoreability 계약을 해결했다고 간주하지 않는다.

100k는 수행하지 않았다. 50k에서 드러난 recoverability size 상한과 2GiB 진단 budget을 먼저 검토해야 하며, full 50k/100k scalability 승인은 T6.9 범위다.

## 19. Delta 설계 입력: 실제 한 건의 카드 입력

10k 기준 revision 30076에서 synthetic 카드 지출 POST가 HTTP 200으로 확인되고 bundle revision 30077이 됐다. 이번 mutation만으로 정확히 +1이었으며 모든 미래 mutation에 이를 일반화하지 않는다.

- 새 raw ledger row 605바이트, typed entry 809바이트.
- 기존 ledger 10,000행은 모두 동일하다. Snapshot table은 ledger_entries만 바뀐다.
- 실제 변한 typed section은 entries, summary, owner_discount_month다. judgment/payment 등은 이 fixture에서 그대로였다.
- Snapshot table/data/content hash, Snapshot ID, authority revision/fingerprint가 변한다.
- full body는 5,684,312→5,685,766바이트이며 old history를 다시 보낸다.
- 변한 typed section을 통째로 보내면 value만 80,245바이트다.
- 새 row/entry + 바뀐 비-entry projection + 현재 manifest/authority value의 합은 **5,531바이트의 가상 budget**이다. 이것은 작동하는 delta wire format·최소 충분 증거·복구 가능성 증명이 아니다. framing/base identity/deletion/transaction/새 hash 방식 등의 비용은 설계 전이다.

향후 delta는 base fingerprint와 owner 일치, 순서 있는 revision 전이, 삭제/tombstone, transaction 원자성, 완전한 Snapshot 재구성·무결성·복구, auth/request/mutation generation, pending/outcomeUnknown 구분, Offline frozen B와 reconciliation Apply(B,J), full resync fallback을 유지해야 한다. 서버 commit 영수증을 delta GET으로 대체하지 않는다.

## 20. T6.6B–E 우선순위

| 단계 | 이번 증거가 요구하는 다음 설계 | 보존할 경계 |
| --- | --- | --- |
| T6.6B | hot/cold + 작은 transport-compression 구현 후보를 명시적으로 검토. 10k의 97.05%가 잠재 cold raw row이고 gzip도 충분히 큰 wire 절감 | cold를 버리지 않고 coherent recoverable B 유지; active archived 관계·정책 이력 보존 |
| T6.6C | 단일 변경 대비 full-history 재전송 제거. base-ID/revision/deletion/atomic reconstruction/full resync 설계 | pending receipt와 GET 관측 분리, Offline/J/reconciliation/generation 불변 |
| T6.6D | Snapshot export·반복 full-ledger scan·상당한 construct 비용, backend duplicate detailed-payment 등 계측 후 개선 | 금융 source-of-truth·same-read-view·strict validator·terminal guard |
| T6.6E | Snapshot/authority/hash 관계 pass와 raw-money/presence/freeze가 주 client 비용. 변경 없는 검증 결과 재사용/선형 identity lookup 등을 별도 증명 | required/type/exact-money/duplicate-key/Unicode/N4/복구·publication 검사를 무조건 생략하지 않음 |

Compression은 변경 폭이 작고 기본 IOClient gzip과 호환될 가능성이 높지만 **이번에 activation하지 않았다**. Brotli는 byte/CPU 실험 결과가 좋더라도 모바일 capability/다른 client·proxy/decode-memory를 먼저 검토해야 한다. 빠른 loopback에서는 오히려 CPU 비용이 늘었으므로 “항상 latency 감소”를 약속하지 않는다.

RTT를 4→1 단계로 줄인 T6.5의 효과는 이미 달성했다. 큰 N에서는 남은 1회에서도 backend와 client의 O(N) CPU·full B 저장이 수 초를 차지해 RTT 절감의 상대 비중이 작아진다. 압축은 bandwidth 병목에는 효과적이나 이 계산 병목, full-history hashing, durable encoding을 해결하지 않는다.

## 21. 검증·자체 sanity·범위 확인

이번 실제 실행:

- `python -m pytest -q scripts/benchmarks`: 15 passed. UTF-8/escape 원문 offsets, disjoint reconciliation, 중복 key·overlap 거부, codec lossless controls, negotiation, 새 migrated DB 두 개의 byte 재현성.
- backend cwd `../.venv/bin/python -m pytest -q`: 606 passed + 1540 subtests, warning 1.
- authoritative-state/Snapshot/migration 관련 targeted 재실행: 103 passed + 134 subtests, warning 1.
- `flutter test --reporter expanded`: 539 passed, opt-in 진단 2 skip. 별도 opt-in 실행에서 frozen admission/publication 1 test와 actual IOClient 1 test를 실제 통과했다.
- `flutter analyze`: No issues found.
- frontend `npm test -- --run`: 6 files / 21 tests; `npm run lint`, `npm run build`: PASS.
- `ruff check backend/app backend/tests scripts`: PASS.
- `pytest -q scripts/tests`: 27 passed; 격리 deployment safety만 수행.
- shell syntax와 `git diff --check`: PASS. ShellCheck는 설치되지 않아 skip.

마지막 Git 검증은 최종 실행 보고서에 별도 기록한다. 초기 진단 smoke에서 실제 manifest key 및 POST 필수 field 누락을 발견해 도구를 수정하고 최종 측정을 전부 다시 했다. targeted 실행의 첫 venv 상대경로 오기는 backend cwd에 맞게 바로잡아 재실행했다. 제품 검증 실패를 숨기거나 이전 감사 수를 새 결과로 재사용하지 않았다.

Warmup 제외, fixed bytes 동일성, inclusive stage 중복 합산 방지, wire layer 구분, implicit decompression, 높은 synthetic 반복성, byte count와 character count, 과거 specimen 차이, 원문 numeric/Unicode 보존을 점검했다. Snapshot manifest가 per-row hash를 담는다고 잘못 설명하지 않았다. 이번 in-scope 새 Critical/High/Medium은 0이다. 이것은 독립 감사 승인 주장이 아니다.

Android native/APK/physical device는 이번 characterization-only 변경에서 실행하지 않았다. 제품 native/runtime 변경이 없고 APK 설치·배포도 없다. Backend warning은 기존 Starlette/httpx deprecation, Flutter dependency newer-version 안내는 upgrade 없이 기록했다. 알려진 auth-session SQLite database-is-locked, 미래 registry drift는 해결하지 않았다.

## 22. 재현 명령·산출물·한계

재현 절차는 [scripts/benchmarks/README.md](../scripts/benchmarks/README.md)에 있다. 큰 원문은 `/tmp/mn-t66a-9WAluE`에만 두었으며 body-*.json, 원시 로그·측정 JSON을 재부팅 뒤 보존한다고 보장하지 않는다. 동일 seed/context/key/timestamp로 재생성할 수 있다. 과거 선택적 specimen 비교는 해당 /tmp 원본이 있어야 하지만 주 6종 생성·압축·admission 검증은 거기에 의존하지 않는다.

Tracked artifacts는 총 약 0.6MB이며 multi-MB body, DB, credential이 없다.

| 파일 | 내용 |
| --- | --- |
| attribution.json / attribution.csv | 6종 원문 범주·Snapshot table·row size·overlap·SHA/headers; CSV에는 성장/분류 |
| compression.csv | 36개 codec 조건의 bytes·CPU/wall median/p95/min/max/stdev/n |
| samples.csv | backend/codec/client/HTTP primary raw timing 표본 |
| environment.json | 시작 commit, fixed parameters, HOST/runtime/자원 메타데이터 |
| client-summary / dart-gzip-summary | 단계·baseline·Dart decode 통계 |
| http-summary / native-http | 실제 entity/header/encoding/connection 계층 증거 |
| growth / bandwidth-model | 단순 descriptive fit 및 가정 있는 transfer 모델 |
| delta / large-probe | actual one-mutation diff와 제한된 50k one-shot |
| specimen-comparison / reference-latency | 이전 synthetic 자료의 출처·SHA 및 이전 감사 reference |

Whole body compressed size와 독립 section 압축 크기는 합이 같지 않다. Section 사이의 dictionary 중첩, gzip/Brotli framing을 포함하기 때문이다. 부록 json_structure 압축은 원문에서 선택하지 않은 byte 조각을 순서대로 이어 압축한 값이며 유효한 독립 JSON 응답이 아니다. 각 SHA/meta hash token의 길이는 무결성 보증의 강도가 아니라 byte 기여다.

Physical wire/TLS, live Apache, 실 사용자 workload, 실기기 frame/GC/UFS/peak memory, Brotli mobile transport는 측정하지 않았다. OS socket/HTTP wrapper의 local 결과는 실제 이동통신 성능 보장이 아니다. Optional 100k·전체 RTT matrix·독립 재감사는 수행하지 않았다.

## 23. Production 안전성과 다음 gate

Production DB/API/credential/.env/서비스·artifact를 읽거나 수정하지 않았다. 모든 DB는 새 synthetic migrated 임시 DB다. local server는 loopback 18081만 사용하고 종료했다. 운영 restart/restore/migration/deploy/APK 설치는 없다.

Backend/mobile/frontend runtime, bundle/Snapshot/baseline/journal/pending version·format, 금융 공식, normal acquisition graph는 불변이다. 정상 refresh 1회 bundle / 성공 submit POST+bundle 2회의 기존 T6.5 계약을 유지한다. 진단은 opt-in이고 startup/배포에서 호출되지 않는다.

다음 gate는 **T6.6B 설계**다. 이 보고서의 cold 후보·압축 feasibility와 복구 상한을 사용해 transport/cache 경계를 먼저 결정하고, delta는 T6.6C 별도 설계에서 증명한다.

## 부록 — fixture별 전체 disjoint category

각 value 범주의 실제 원문 bytes와 독립 gzip6/Brotli4 압축 크기다. count는 array 원소 수, object 직접 member 수, scalar 1이다. 따라서 manifest object의 count=3은 table row_count가 아니라 columns/row_count/sha256의 member 수다. 실제 table rows는 snapshot.data와 5절/JSON 상세를 본다.

성장 표기: N=전체 보존 row; 활성=현재/미마감 또는 configuration/queue/batch 수; 제어=현 schema/정책에 주로 일정하나 숫자 자릿수·registry 이력에 변동 가능. HOT은 현재 typed 소비, SHARED는 완전한 복구 B의 raw state, CONTROL은 호환성·identity·hash와 구조다. SHARED 안의 COLD 후보 분리는 9절의 별도 view다.

### current-like

| CATEGORY | COUNT | RAW BYTES | TOTAL % | GZIP6 | BROTLI4 | GROWTH | CLASS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bundle_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `principal` | 1 | 13 | 0.00 | 33 | 17 | 제어 | CONTROL |
| `authority` | 4 | 208 | 0.07 | 176 | 152 | 제어 | CONTROL |
| `state.month_close_status` | 11 | 367 | 0.12 | 215 | 202 | 활성 | HOT |
| `state.entries` | 104 | 78,593 | 25.65 | 1,699 | 1,100 | 활성 | HOT |
| `state.panels` | 4 | 2,024 | 0.66 | 339 | 319 | 활성 | HOT |
| `state.summary` | 17 | 492 | 0.16 | 250 | 234 | 활성 | HOT |
| `state.card_payment_status` | 16 | 2,848 | 0.93 | 899 | 883 | 활성 | HOT |
| `state.judgment` | 6 | 1,164 | 0.38 | 643 | 648 | 활성 | HOT |
| `state.confirmed_planned_entries` | 1 | 774 | 0.25 | 380 | 356 | 활성 | HOT |
| `state.cash_flows` | 4 | 452 | 0.15 | 197 | 166 | 활성 | HOT |
| `state.settings` | 5 | 116 | 0.04 | 104 | 91 | 활성 | HOT |
| `state.owner_discount_month` | 6 | 312 | 0.10 | 202 | 195 | 활성 | HOT |
| `state.family_discount_month` | 6 | 244 | 0.08 | 173 | 154 | 활성 | HOT |
| `state.transit_discount_profile` | 3 | 53 | 0.02 | 69 | 54 | 활성 | HOT |
| `snapshot.data.ledger_entries` | 376 | 208,688 | 68.12 | 4,643 | 2,504 | N | SHARED |
| `snapshot.data.monthly_panels` | 4 | 1,336 | 0.44 | 243 | 226 | N | SHARED |
| `snapshot.data.cash_flows` | 5 | 910 | 0.30 | 238 | 209 | N | SHARED |
| `snapshot.data.card_payment_batches` | 1 | 110 | 0.04 | 112 | 96 | N | SHARED |
| `snapshot.data.card_payment_batch_items` | 3 | 298 | 0.10 | 131 | 110 | N | SHARED |
| `snapshot.data.card_payment_events` | 1 | 293 | 0.10 | 222 | 210 | N | SHARED |
| `snapshot.data.card_payment_allocations` | 1 | 117 | 0.04 | 116 | 98 | N | SHARED |
| `snapshot.data.card_payment_deferrals` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.notification_candidate_registrations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.app_settings` | 5 | 371 | 0.12 | 150 | 127 | N | SHARED |
| `snapshot.data.app_labels` | 18 | 1,611 | 0.53 | 397 | 371 | N | SHARED |
| `snapshot.manifest.tables.ledger_entries` | 3 | 455 | 0.15 | 281 | 270 | 제어 | CONTROL |
| `snapshot.manifest.tables.monthly_panels` | 3 | 322 | 0.11 | 218 | 211 | 제어 | CONTROL |
| `snapshot.manifest.tables.cash_flows` | 3 | 204 | 0.07 | 175 | 155 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batches` | 3 | 153 | 0.05 | 145 | 123 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batch_items` | 3 | 163 | 0.05 | 146 | 129 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_events` | 3 | 235 | 0.08 | 190 | 176 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_allocations` | 3 | 175 | 0.06 | 158 | 137 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_deferrals` | 3 | 310 | 0.10 | 206 | 186 | 제어 | CONTROL |
| `snapshot.manifest.tables.notification_candidate_registrations` | 3 | 178 | 0.06 | 158 | 140 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_settings` | 3 | 130 | 0.04 | 131 | 105 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_labels` | 3 | 131 | 0.04 | 132 | 106 | 제어 | CONTROL |
| `snapshot.manifest.algorithm` | 1 | 8 | 0.00 | 28 | 12 | 제어 | CONTROL |
| `snapshot.manifest.data_sha256` | 1 | 66 | 0.02 | 73 | 50 | 제어 | CONTROL |
| `snapshot.manifest.card_charge_policy_sha256` | 1 | 66 | 0.02 | 72 | 51 | 제어 | CONTROL |
| `snapshot.manifest.content_sha256` | 1 | 66 | 0.02 | 74 | 51 | 제어 | CONTROL |
| `snapshot.schema_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.recurring_ownership_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.exported_at` | 1 | 22 | 0.01 | 40 | 26 | 제어 | CONTROL |
| `snapshot.range` | 1 | 15 | 0.00 | 35 | 19 | 제어 | CONTROL |
| `snapshot.card_charge_policy` | 5 | 1,199 | 0.39 | 482 | 478 | 제어 | CONTROL |
| `snapshot.snapshot_id` | 1 | 66 | 0.02 | 74 | 51 | 제어 | CONTROL |
| `json_structure` | — | 1,005 | 0.33 | 354 | 339 | 제어 | CONTROL |

원문 합계: 306,370바이트. Whole-body gzip6 / Brotli4: 11,474 / 8,014바이트. 독립 범주 압축 합계와 비교해 합산하지 않는다.

### 1k

| CATEGORY | COUNT | RAW BYTES | TOTAL % | GZIP6 | BROTLI4 | GROWTH | CLASS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bundle_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `principal` | 1 | 13 | 0.00 | 33 | 17 | 제어 | CONTROL |
| `authority` | 4 | 208 | 0.03 | 175 | 155 | 제어 | CONTROL |
| `state.month_close_status` | 11 | 367 | 0.06 | 215 | 202 | 활성 | HOT |
| `state.entries` | 104 | 78,593 | 12.03 | 1,699 | 1,100 | 활성 | HOT |
| `state.panels` | 4 | 2,024 | 0.31 | 339 | 319 | 활성 | HOT |
| `state.summary` | 17 | 492 | 0.08 | 250 | 234 | 활성 | HOT |
| `state.card_payment_status` | 16 | 2,848 | 0.44 | 899 | 883 | 활성 | HOT |
| `state.judgment` | 6 | 1,164 | 0.18 | 643 | 648 | 활성 | HOT |
| `state.confirmed_planned_entries` | 1 | 774 | 0.12 | 380 | 356 | 활성 | HOT |
| `state.cash_flows` | 4 | 452 | 0.07 | 197 | 166 | 활성 | HOT |
| `state.settings` | 5 | 116 | 0.02 | 104 | 91 | 활성 | HOT |
| `state.owner_discount_month` | 6 | 312 | 0.05 | 202 | 195 | 활성 | HOT |
| `state.family_discount_month` | 6 | 244 | 0.04 | 173 | 154 | 활성 | HOT |
| `state.transit_discount_profile` | 3 | 53 | 0.01 | 69 | 54 | 활성 | HOT |
| `snapshot.data.ledger_entries` | 1,000 | 555,634 | 85.05 | 10,983 | 4,781 | N | SHARED |
| `snapshot.data.monthly_panels` | 4 | 1,336 | 0.20 | 243 | 226 | N | SHARED |
| `snapshot.data.cash_flows` | 5 | 910 | 0.14 | 238 | 209 | N | SHARED |
| `snapshot.data.card_payment_batches` | 1 | 110 | 0.02 | 112 | 96 | N | SHARED |
| `snapshot.data.card_payment_batch_items` | 3 | 298 | 0.05 | 131 | 110 | N | SHARED |
| `snapshot.data.card_payment_events` | 1 | 293 | 0.04 | 222 | 210 | N | SHARED |
| `snapshot.data.card_payment_allocations` | 1 | 117 | 0.02 | 116 | 98 | N | SHARED |
| `snapshot.data.card_payment_deferrals` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.notification_candidate_registrations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.app_settings` | 5 | 371 | 0.06 | 150 | 127 | N | SHARED |
| `snapshot.data.app_labels` | 18 | 1,611 | 0.25 | 397 | 371 | N | SHARED |
| `snapshot.manifest.tables.ledger_entries` | 3 | 456 | 0.07 | 282 | 271 | 제어 | CONTROL |
| `snapshot.manifest.tables.monthly_panels` | 3 | 322 | 0.05 | 218 | 211 | 제어 | CONTROL |
| `snapshot.manifest.tables.cash_flows` | 3 | 204 | 0.03 | 175 | 155 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batches` | 3 | 153 | 0.02 | 145 | 123 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batch_items` | 3 | 163 | 0.02 | 146 | 129 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_events` | 3 | 235 | 0.04 | 190 | 176 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_allocations` | 3 | 175 | 0.03 | 158 | 137 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_deferrals` | 3 | 310 | 0.05 | 206 | 186 | 제어 | CONTROL |
| `snapshot.manifest.tables.notification_candidate_registrations` | 3 | 178 | 0.03 | 158 | 140 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_settings` | 3 | 130 | 0.02 | 131 | 105 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_labels` | 3 | 131 | 0.02 | 132 | 106 | 제어 | CONTROL |
| `snapshot.manifest.algorithm` | 1 | 8 | 0.00 | 28 | 12 | 제어 | CONTROL |
| `snapshot.manifest.data_sha256` | 1 | 66 | 0.01 | 74 | 51 | 제어 | CONTROL |
| `snapshot.manifest.card_charge_policy_sha256` | 1 | 66 | 0.01 | 72 | 51 | 제어 | CONTROL |
| `snapshot.manifest.content_sha256` | 1 | 66 | 0.01 | 74 | 51 | 제어 | CONTROL |
| `snapshot.schema_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.recurring_ownership_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.exported_at` | 1 | 22 | 0.00 | 40 | 26 | 제어 | CONTROL |
| `snapshot.range` | 1 | 15 | 0.00 | 35 | 19 | 제어 | CONTROL |
| `snapshot.card_charge_policy` | 5 | 1,199 | 0.18 | 482 | 478 | 제어 | CONTROL |
| `snapshot.snapshot_id` | 1 | 66 | 0.01 | 74 | 51 | 제어 | CONTROL |
| `json_structure` | — | 1,005 | 0.15 | 354 | 339 | 제어 | CONTROL |

원문 합계: 653,317바이트. Whole-body gzip6 / Brotli4: 18,173 / 10,339바이트. 독립 범주 압축 합계와 비교해 합산하지 않는다.

### 5k

| CATEGORY | COUNT | RAW BYTES | TOTAL % | GZIP6 | BROTLI4 | GROWTH | CLASS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bundle_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `principal` | 1 | 13 | 0.00 | 33 | 17 | 제어 | CONTROL |
| `authority` | 4 | 209 | 0.01 | 177 | 156 | 제어 | CONTROL |
| `state.month_close_status` | 11 | 367 | 0.01 | 215 | 202 | 활성 | HOT |
| `state.entries` | 104 | 78,593 | 2.72 | 1,699 | 1,100 | 활성 | HOT |
| `state.panels` | 4 | 2,024 | 0.07 | 339 | 319 | 활성 | HOT |
| `state.summary` | 17 | 492 | 0.02 | 250 | 234 | 활성 | HOT |
| `state.card_payment_status` | 16 | 2,848 | 0.10 | 899 | 883 | 활성 | HOT |
| `state.judgment` | 6 | 1,164 | 0.04 | 643 | 648 | 활성 | HOT |
| `state.confirmed_planned_entries` | 1 | 774 | 0.03 | 380 | 356 | 활성 | HOT |
| `state.cash_flows` | 4 | 452 | 0.02 | 197 | 166 | 활성 | HOT |
| `state.settings` | 5 | 116 | 0.00 | 104 | 91 | 활성 | HOT |
| `state.owner_discount_month` | 6 | 312 | 0.01 | 202 | 195 | 활성 | HOT |
| `state.family_discount_month` | 6 | 244 | 0.01 | 173 | 154 | 활성 | HOT |
| `state.transit_discount_profile` | 3 | 53 | 0.00 | 69 | 54 | 활성 | HOT |
| `snapshot.data.ledger_entries` | 5,000 | 2,791,625 | 96.62 | 51,199 | 19,447 | N | SHARED |
| `snapshot.data.monthly_panels` | 4 | 1,336 | 0.05 | 243 | 226 | N | SHARED |
| `snapshot.data.cash_flows` | 5 | 910 | 0.03 | 238 | 209 | N | SHARED |
| `snapshot.data.card_payment_batches` | 1 | 110 | 0.00 | 112 | 96 | N | SHARED |
| `snapshot.data.card_payment_batch_items` | 3 | 298 | 0.01 | 131 | 110 | N | SHARED |
| `snapshot.data.card_payment_events` | 1 | 293 | 0.01 | 222 | 210 | N | SHARED |
| `snapshot.data.card_payment_allocations` | 1 | 117 | 0.00 | 116 | 98 | N | SHARED |
| `snapshot.data.card_payment_deferrals` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.notification_candidate_registrations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.app_settings` | 5 | 371 | 0.01 | 150 | 127 | N | SHARED |
| `snapshot.data.app_labels` | 18 | 1,611 | 0.06 | 397 | 371 | N | SHARED |
| `snapshot.manifest.tables.ledger_entries` | 3 | 456 | 0.02 | 282 | 270 | 제어 | CONTROL |
| `snapshot.manifest.tables.monthly_panels` | 3 | 322 | 0.01 | 218 | 211 | 제어 | CONTROL |
| `snapshot.manifest.tables.cash_flows` | 3 | 204 | 0.01 | 175 | 155 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batches` | 3 | 153 | 0.01 | 145 | 123 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batch_items` | 3 | 163 | 0.01 | 146 | 129 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_events` | 3 | 235 | 0.01 | 190 | 176 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_allocations` | 3 | 175 | 0.01 | 158 | 137 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_deferrals` | 3 | 310 | 0.01 | 206 | 186 | 제어 | CONTROL |
| `snapshot.manifest.tables.notification_candidate_registrations` | 3 | 178 | 0.01 | 158 | 140 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_settings` | 3 | 130 | 0.00 | 131 | 105 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_labels` | 3 | 131 | 0.00 | 132 | 106 | 제어 | CONTROL |
| `snapshot.manifest.algorithm` | 1 | 8 | 0.00 | 28 | 12 | 제어 | CONTROL |
| `snapshot.manifest.data_sha256` | 1 | 66 | 0.00 | 71 | 50 | 제어 | CONTROL |
| `snapshot.manifest.card_charge_policy_sha256` | 1 | 66 | 0.00 | 72 | 51 | 제어 | CONTROL |
| `snapshot.manifest.content_sha256` | 1 | 66 | 0.00 | 73 | 50 | 제어 | CONTROL |
| `snapshot.schema_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.recurring_ownership_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.exported_at` | 1 | 22 | 0.00 | 40 | 26 | 제어 | CONTROL |
| `snapshot.range` | 1 | 15 | 0.00 | 35 | 19 | 제어 | CONTROL |
| `snapshot.card_charge_policy` | 5 | 1,199 | 0.04 | 482 | 478 | 제어 | CONTROL |
| `snapshot.snapshot_id` | 1 | 66 | 0.00 | 73 | 50 | 제어 | CONTROL |
| `json_structure` | — | 1,005 | 0.03 | 354 | 339 | 제어 | CONTROL |

원문 합계: 2,889,309바이트. Whole-body gzip6 / Brotli4: 58,385 / 25,792바이트. 독립 범주 압축 합계와 비교해 합산하지 않는다.

### 10k

| CATEGORY | COUNT | RAW BYTES | TOTAL % | GZIP6 | BROTLI4 | GROWTH | CLASS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bundle_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `principal` | 1 | 13 | 0.00 | 33 | 17 | 제어 | CONTROL |
| `authority` | 4 | 209 | 0.00 | 177 | 154 | 제어 | CONTROL |
| `state.month_close_status` | 11 | 367 | 0.01 | 215 | 202 | 활성 | HOT |
| `state.entries` | 104 | 78,593 | 1.38 | 1,699 | 1,100 | 활성 | HOT |
| `state.panels` | 4 | 2,024 | 0.04 | 339 | 319 | 활성 | HOT |
| `state.summary` | 17 | 492 | 0.01 | 250 | 234 | 활성 | HOT |
| `state.card_payment_status` | 16 | 2,848 | 0.05 | 899 | 883 | 활성 | HOT |
| `state.judgment` | 6 | 1,164 | 0.02 | 643 | 648 | 활성 | HOT |
| `state.confirmed_planned_entries` | 1 | 774 | 0.01 | 380 | 356 | 활성 | HOT |
| `state.cash_flows` | 4 | 452 | 0.01 | 197 | 166 | 활성 | HOT |
| `state.settings` | 5 | 116 | 0.00 | 104 | 91 | 활성 | HOT |
| `state.owner_discount_month` | 6 | 312 | 0.01 | 202 | 195 | 활성 | HOT |
| `state.family_discount_month` | 6 | 244 | 0.00 | 173 | 154 | 활성 | HOT |
| `state.transit_discount_profile` | 3 | 53 | 0.00 | 69 | 54 | 활성 | HOT |
| `snapshot.data.ledger_entries` | 10,000 | 5,586,627 | 98.28 | 101,336 | 36,522 | N | SHARED |
| `snapshot.data.monthly_panels` | 4 | 1,336 | 0.02 | 243 | 226 | N | SHARED |
| `snapshot.data.cash_flows` | 5 | 910 | 0.02 | 238 | 209 | N | SHARED |
| `snapshot.data.card_payment_batches` | 1 | 110 | 0.00 | 112 | 96 | N | SHARED |
| `snapshot.data.card_payment_batch_items` | 3 | 298 | 0.01 | 131 | 110 | N | SHARED |
| `snapshot.data.card_payment_events` | 1 | 293 | 0.01 | 222 | 210 | N | SHARED |
| `snapshot.data.card_payment_allocations` | 1 | 117 | 0.00 | 116 | 98 | N | SHARED |
| `snapshot.data.card_payment_deferrals` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.notification_candidate_registrations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.app_settings` | 5 | 371 | 0.01 | 150 | 127 | N | SHARED |
| `snapshot.data.app_labels` | 18 | 1,611 | 0.03 | 397 | 371 | N | SHARED |
| `snapshot.manifest.tables.ledger_entries` | 3 | 457 | 0.01 | 282 | 272 | 제어 | CONTROL |
| `snapshot.manifest.tables.monthly_panels` | 3 | 322 | 0.01 | 218 | 211 | 제어 | CONTROL |
| `snapshot.manifest.tables.cash_flows` | 3 | 204 | 0.00 | 175 | 155 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batches` | 3 | 153 | 0.00 | 145 | 123 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batch_items` | 3 | 163 | 0.00 | 146 | 129 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_events` | 3 | 235 | 0.00 | 190 | 176 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_allocations` | 3 | 175 | 0.00 | 158 | 137 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_deferrals` | 3 | 310 | 0.01 | 206 | 186 | 제어 | CONTROL |
| `snapshot.manifest.tables.notification_candidate_registrations` | 3 | 178 | 0.00 | 158 | 140 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_settings` | 3 | 130 | 0.00 | 131 | 105 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_labels` | 3 | 131 | 0.00 | 132 | 106 | 제어 | CONTROL |
| `snapshot.manifest.algorithm` | 1 | 8 | 0.00 | 28 | 12 | 제어 | CONTROL |
| `snapshot.manifest.data_sha256` | 1 | 66 | 0.00 | 73 | 51 | 제어 | CONTROL |
| `snapshot.manifest.card_charge_policy_sha256` | 1 | 66 | 0.00 | 72 | 51 | 제어 | CONTROL |
| `snapshot.manifest.content_sha256` | 1 | 66 | 0.00 | 72 | 50 | 제어 | CONTROL |
| `snapshot.schema_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.recurring_ownership_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.exported_at` | 1 | 22 | 0.00 | 40 | 26 | 제어 | CONTROL |
| `snapshot.range` | 1 | 15 | 0.00 | 35 | 19 | 제어 | CONTROL |
| `snapshot.card_charge_policy` | 5 | 1,199 | 0.02 | 482 | 478 | 제어 | CONTROL |
| `snapshot.snapshot_id` | 1 | 66 | 0.00 | 72 | 50 | 제어 | CONTROL |
| `json_structure` | — | 1,005 | 0.02 | 354 | 339 | 제어 | CONTROL |

원문 합계: 5,684,312바이트. Whole-body gzip6 / Brotli4: 108,916 / 43,033바이트. 독립 범주 압축 합계와 비교해 합산하지 않는다.

### confirmed-heavy 600

| CATEGORY | COUNT | RAW BYTES | TOTAL % | GZIP6 | BROTLI4 | GROWTH | CLASS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bundle_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `principal` | 1 | 13 | 0.00 | 33 | 17 | 제어 | CONTROL |
| `authority` | 4 | 208 | 0.01 | 176 | 155 | 제어 | CONTROL |
| `state.month_close_status` | 11 | 307 | 0.02 | 176 | 163 | 활성 | HOT |
| `state.entries` | 600 | 477,049 | 28.11 | 16,861 | 13,717 | 활성 | HOT |
| `state.panels` | 0 | 2 | 0.00 | 22 | 6 | 활성 | HOT |
| `state.summary` | 17 | 470 | 0.03 | 234 | 213 | 활성 | HOT |
| `state.card_payment_status` | 16 | 394 | 0.02 | 222 | 192 | 활성 | HOT |
| `state.judgment` | 6 | 1,183 | 0.07 | 633 | 643 | 활성 | HOT |
| `state.confirmed_planned_entries` | 600 | 476,926 | 28.11 | 5,203 | 2,647 | 활성 | HOT |
| `state.cash_flows` | 0 | 2 | 0.00 | 22 | 6 | 활성 | HOT |
| `state.settings` | 5 | 116 | 0.01 | 104 | 91 | 활성 | HOT |
| `state.owner_discount_month` | 6 | 23,044 | 1.36 | 12,165 | 10,708 | 활성 | HOT |
| `state.family_discount_month` | 6 | 244 | 0.01 | 173 | 154 | 활성 | HOT |
| `state.transit_discount_profile` | 3 | 53 | 0.00 | 69 | 54 | 활성 | HOT |
| `snapshot.data.ledger_entries` | 1,200 | 709,819 | 41.83 | 22,005 | 16,952 | N | SHARED |
| `snapshot.data.monthly_panels` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.cash_flows` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.card_payment_batches` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.card_payment_batch_items` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.card_payment_events` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.card_payment_allocations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.card_payment_deferrals` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.notification_candidate_registrations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.app_settings` | 5 | 371 | 0.02 | 150 | 127 | N | SHARED |
| `snapshot.data.app_labels` | 18 | 1,611 | 0.09 | 397 | 371 | N | SHARED |
| `snapshot.manifest.tables.ledger_entries` | 3 | 456 | 0.03 | 281 | 270 | 제어 | CONTROL |
| `snapshot.manifest.tables.monthly_panels` | 3 | 322 | 0.02 | 219 | 210 | 제어 | CONTROL |
| `snapshot.manifest.tables.cash_flows` | 3 | 204 | 0.01 | 174 | 155 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batches` | 3 | 153 | 0.01 | 146 | 122 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batch_items` | 3 | 163 | 0.01 | 147 | 130 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_events` | 3 | 235 | 0.01 | 188 | 176 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_allocations` | 3 | 175 | 0.01 | 157 | 133 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_deferrals` | 3 | 310 | 0.02 | 206 | 186 | 제어 | CONTROL |
| `snapshot.manifest.tables.notification_candidate_registrations` | 3 | 178 | 0.01 | 158 | 140 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_settings` | 3 | 130 | 0.01 | 131 | 105 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_labels` | 3 | 131 | 0.01 | 132 | 106 | 제어 | CONTROL |
| `snapshot.manifest.algorithm` | 1 | 8 | 0.00 | 28 | 12 | 제어 | CONTROL |
| `snapshot.manifest.data_sha256` | 1 | 66 | 0.00 | 72 | 52 | 제어 | CONTROL |
| `snapshot.manifest.card_charge_policy_sha256` | 1 | 66 | 0.00 | 72 | 51 | 제어 | CONTROL |
| `snapshot.manifest.content_sha256` | 1 | 66 | 0.00 | 72 | 50 | 제어 | CONTROL |
| `snapshot.schema_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.recurring_ownership_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.exported_at` | 1 | 22 | 0.00 | 40 | 26 | 제어 | CONTROL |
| `snapshot.range` | 1 | 15 | 0.00 | 35 | 19 | 제어 | CONTROL |
| `snapshot.card_charge_policy` | 5 | 1,199 | 0.07 | 482 | 478 | 제어 | CONTROL |
| `snapshot.snapshot_id` | 1 | 66 | 0.00 | 72 | 50 | 제어 | CONTROL |
| `json_structure` | — | 1,005 | 0.06 | 354 | 339 | 제어 | CONTROL |

원문 합계: 1,696,801바이트. Whole-body gzip6 / Brotli4: 61,453 / 31,976바이트. 독립 범주 압축 합계와 비교해 합산하지 않는다.

### 10k 다양성 control

| CATEGORY | COUNT | RAW BYTES | TOTAL % | GZIP6 | BROTLI4 | GROWTH | CLASS |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `bundle_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `principal` | 1 | 13 | 0.00 | 33 | 17 | 제어 | CONTROL |
| `authority` | 4 | 209 | 0.00 | 177 | 155 | 제어 | CONTROL |
| `state.month_close_status` | 11 | 367 | 0.01 | 215 | 202 | 활성 | HOT |
| `state.entries` | 104 | 83,703 | 1.35 | 6,303 | 5,335 | 활성 | HOT |
| `state.panels` | 4 | 2,024 | 0.03 | 339 | 319 | 활성 | HOT |
| `state.summary` | 17 | 492 | 0.01 | 250 | 234 | 활성 | HOT |
| `state.card_payment_status` | 16 | 2,848 | 0.05 | 899 | 883 | 활성 | HOT |
| `state.judgment` | 6 | 1,164 | 0.02 | 643 | 648 | 활성 | HOT |
| `state.confirmed_planned_entries` | 1 | 774 | 0.01 | 380 | 356 | 활성 | HOT |
| `state.cash_flows` | 4 | 452 | 0.01 | 197 | 166 | 활성 | HOT |
| `state.settings` | 5 | 116 | 0.00 | 104 | 91 | 활성 | HOT |
| `state.owner_discount_month` | 6 | 312 | 0.01 | 202 | 195 | 활성 | HOT |
| `state.family_discount_month` | 6 | 244 | 0.00 | 173 | 154 | 활성 | HOT |
| `state.transit_discount_profile` | 3 | 53 | 0.00 | 69 | 54 | 활성 | HOT |
| `snapshot.data.ledger_entries` | 10,000 | 6,077,296 | 98.34 | 557,185 | 462,256 | N | SHARED |
| `snapshot.data.monthly_panels` | 4 | 1,336 | 0.02 | 243 | 226 | N | SHARED |
| `snapshot.data.cash_flows` | 5 | 910 | 0.01 | 238 | 209 | N | SHARED |
| `snapshot.data.card_payment_batches` | 1 | 110 | 0.00 | 112 | 96 | N | SHARED |
| `snapshot.data.card_payment_batch_items` | 3 | 298 | 0.00 | 131 | 110 | N | SHARED |
| `snapshot.data.card_payment_events` | 1 | 293 | 0.00 | 222 | 210 | N | SHARED |
| `snapshot.data.card_payment_allocations` | 1 | 117 | 0.00 | 116 | 98 | N | SHARED |
| `snapshot.data.card_payment_deferrals` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.notification_candidate_registrations` | 0 | 2 | 0.00 | 22 | 6 | N | SHARED |
| `snapshot.data.app_settings` | 5 | 371 | 0.01 | 150 | 127 | N | SHARED |
| `snapshot.data.app_labels` | 18 | 1,611 | 0.03 | 397 | 371 | N | SHARED |
| `snapshot.manifest.tables.ledger_entries` | 3 | 457 | 0.01 | 281 | 273 | 제어 | CONTROL |
| `snapshot.manifest.tables.monthly_panels` | 3 | 322 | 0.01 | 218 | 211 | 제어 | CONTROL |
| `snapshot.manifest.tables.cash_flows` | 3 | 204 | 0.00 | 175 | 155 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batches` | 3 | 153 | 0.00 | 145 | 123 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_batch_items` | 3 | 163 | 0.00 | 146 | 129 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_events` | 3 | 235 | 0.00 | 190 | 176 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_allocations` | 3 | 175 | 0.00 | 158 | 137 | 제어 | CONTROL |
| `snapshot.manifest.tables.card_payment_deferrals` | 3 | 310 | 0.01 | 206 | 186 | 제어 | CONTROL |
| `snapshot.manifest.tables.notification_candidate_registrations` | 3 | 178 | 0.00 | 158 | 140 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_settings` | 3 | 130 | 0.00 | 131 | 105 | 제어 | CONTROL |
| `snapshot.manifest.tables.app_labels` | 3 | 131 | 0.00 | 132 | 106 | 제어 | CONTROL |
| `snapshot.manifest.algorithm` | 1 | 8 | 0.00 | 28 | 12 | 제어 | CONTROL |
| `snapshot.manifest.data_sha256` | 1 | 66 | 0.00 | 73 | 52 | 제어 | CONTROL |
| `snapshot.manifest.card_charge_policy_sha256` | 1 | 66 | 0.00 | 72 | 51 | 제어 | CONTROL |
| `snapshot.manifest.content_sha256` | 1 | 66 | 0.00 | 74 | 51 | 제어 | CONTROL |
| `snapshot.schema_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.recurring_ownership_version` | 1 | 1 | 0.00 | 21 | 5 | 제어 | CONTROL |
| `snapshot.exported_at` | 1 | 22 | 0.00 | 40 | 26 | 제어 | CONTROL |
| `snapshot.range` | 1 | 15 | 0.00 | 35 | 19 | 제어 | CONTROL |
| `snapshot.card_charge_policy` | 5 | 1,199 | 0.02 | 482 | 478 | 제어 | CONTROL |
| `snapshot.snapshot_id` | 1 | 66 | 0.00 | 74 | 51 | 제어 | CONTROL |
| `json_structure` | — | 1,005 | 0.02 | 354 | 339 | 제어 | CONTROL |

원문 합계: 6,180,091바이트. Whole-body gzip6 / Brotli4: 568,847 / 477,248바이트. 독립 범주 압축 합계와 비교해 합산하지 않는다.
