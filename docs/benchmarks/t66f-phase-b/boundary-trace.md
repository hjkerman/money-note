# D→E 경계와 현재 증명 범위

규범은 `docs/t66/c/t66c-delta-sync-protocol.md`다. 아래 표는 새 합성 실행과 source inspection을
연결한다. `coverage.md`의 사전 계획을 현재 통과 결과로 바꾸지 않는다.

| 경계 | 입력→출력·canonical identity | 인증·integrity | persistence·다음 소유자 | 실패·재시도·경쟁 |
|---|---|---|---|---|
| D1 capture | 실제 authoritative SQL 변경→old/new typed cells·revision | schema/33개 trigger event·deferred fence | source와 capture가 같은 TX, D2b가 finalize | finalize 누락 COMMIT 거부; rollback은 source도 보존; writer 직렬화 |
| D2a/b generation | capture→C1 raw/index/input roots·certificate | namespace/epoch/version·SHA·F(raw)/Patricia | 같은 TX에서 current roots, D3a가 관측 | atomic old/new; localized tree path 변경; fresh complete oracle는 측정 밖 |
| D3a observation | original Bearer+request UUID+base→Target/manifest/lease | exact session/principal/epoch·same coherent view | Available lease/root pins, E2가 소비 | 같은 nonce 201→200, 409 epoch/410 expiry/429 budget/503 retry_same; bounded workers/lock |
| D3b transfer | lease+typed path/offset/length→base64 C1 bytes | 원 credential·lease·authorized root path | server immutable store는 불변, E2 verifier 소유 | wrong path/context/expiry 거부, network retry bounded; per-request resource cleanup |
| D3c retirement | release/expiry/maintenance→Retired 및 live retention | durable observation 상태와 owned DB FD | root pin 삭제/GC transaction, 이후 lease는 복구 권위 아님 | release retry/idempotence; clock reversal로 retired를 살리지 않음; permit/DB identity 기존 반례 재실행 |
| E2→E1 | authenticated manifest/expected Ref+실제 body→verified object/staging | C1/hash/type/namespace·verified parent edges | immutable object writer TX와 durable staging; E3가 검증 | malformed/partial/quota/schema 실패 시 accepted 불변; valid cached bytes는 re-read 검증 |
| E3 publication | original ticket+verified candidate/base/seq→receipt/accepted | complete F/raw/hot + final AppState/session fence | BEGIN IMMEDIATE→pins/receipt/base fence→동기 COMMIT/readback; E4가 소비 | stale/conflict는 rollback; COMMIT 후 readback 실패는 불확실 상태로 invalidation; final guard 후 await 없음 |
| E4 read | accepted/frozen generation+read scope→logical pages/materialization | exact receipt/namespace/roots·required pins | SQLite read snapshot, caller가 범위 해제 | DELETE journal에서 competing writer COMMIT은 scope 종료 전 BUSY; 혼합 generation read 금지 |
| E4 install | original ticket+materialization+current durable previous source→installed source/lineage | 현재 AppState/session, source UUID/seq·SQL owner·필수 predecessor | SQLite + source/B/J 파일의 recovery protocol; Frozen-B가 소비 | RA01 provenance 부족은 fail closed; A01 stale recovery는 newer owner 복원 금지; 별개 stores를 단일 TX라고 부르지 않음 |
| Frozen B/J | exact v7/v4 baseline lineage+input journal→read/projection | Frozen receipt/pins·원 lineage·input identity | durable frozen owner는 accepted/read-scope owner와 별도 | unchanged reuse는 full graph 재검증 없음; reopen/external change는 full fallback; GET/content matching은 ACK가 아님 |

## 현재 binding mapping

새 사례별 원문·실제 결과는 `cases.json`, 실제 SQLite/HTTP/Fresh-process 관찰은 `evidence/`,
전체 회귀의 실행 수와 실패는 `summary.json`에 기록한다. 아래는 그 증거의 적용 범위다.

| 요구 | 새 Phase B 증거 | 기존 suite 재실행 | 현재 한계·gate |
|---|---|---|---|
| I1·I14 principal/authority | FB-A 5개, FB12/14, source-preserving FB05 | E3 authority·E4 authority/race·원 RA01 | 일부 scheduling의 결정적 증명이며 모든 가능한 schedule의 전수 검사가 아님 |
| I2 epoch | FB19 실제 명시 bootstrap·409, old Frozen 보존·별도 new namespace | D1/D3c restart·identity 회귀 | FB19를 실제 backend process restart의 410 증거로 부르지 않음 |
| I3·I4 base/coherence | FB01/03/11, old lease와 new root 혼용 거부 | E3 base/seq/publication·D3 concurrent duplicate | 전체 backend 회귀의 status assertion 실패 gate가 남음 |
| I5·I7·I8 graph | FB01 G1–G7/FB10 empty, backend 독립 closure·client SQL SHA/bytes | D2 trees/property·E2/E3 diff | 유한 synthetic graph, 누락된 모든 미지 구조를 증명하지 않음 |
| I6 C1/money | FB01/08, mandatory U+001C/+0001000.00/U+001F 원문 | E1 correction·P0183·golden tests | monetary grammar 연구를 새로 전수 실행했다고 주장하지 않음 |
| I9·I10 F/reverse | 독립 F(raw)/Patricia complete oracle, actual unfinalized COMMIT 거부 | D1/D2b property 및 E3 negative verification | 새 fault 8개는 모든 reverse-closure 오류의 독립 주입을 대신하지 않음 |
| I11·I12 hot/financial | 실제 backend 11 table/12 projection 및 v7 equality | 기존 presenters/financial·E3 hot/raw | client 금융 재계산을 추가하지 않음; oracle가 backend 금융 코드를 공유함을 명시 |
| I13·I21 storage | FB15 trigger/FB16 quota/FB18 partial, backend kill 3 | E1-A02·E3 receipt/crash/rollback | 임의 외부 filesystem 공격이나 모든 I/O failure mode를 주장하지 않음 |
| I15·I16 pending/Frozen | FB02/03/04/05/12/17 및 fresh child | 원 Phase A/A01/RA01/B/J | installation 성공은 implicit ACK나 R1 proof가 아님 |
| I17 durability | backend actual SIGKILL 3 + Flutter actual SIGKILL 4 | E1/E3/E4 실제 child suites | HOST process crash 범위, Android hardware power loss 미검증 |
| I18 retention | actual Frozen G1 during G2 +pins/closure/fresh read | D3c live roots/GC·E4 pins | R1 reader/recovery lifecycle을 구현한 것으로 간주하지 않음 |
| I19 resume | FB06 durable4개 이후 재개, FB11 expiry/churn, fresh-process reads | E2 crash·E4 handoff/recovery | restart는 data repair일 뿐 이전 ticket의 authorization 복원이 아님 |
| I20 materialization | FB02 actual backend v7 oracle·source/lineage check | E4 original materialization/P0 | 테스트 profile의 legacy admission adapter를 normal runtime integration으로 확대하지 않음 |
| I22 HTTP | 실제 TLS +FB09 TCP/proc +FB18 truncation +2 TLS concurrency | E2-A01 independent9·correction5 | TLS rejection status 하나만으로 resource release를 판단하지 않음 |
| I23 R1 | 실제 capabilities404·FB08 gate | 기존 closed-gate tests | **미완료**: R1 Large Restore/MW는 별도 prerequisite이며 구현하지 않음 |
| I24 backup30 | product source/configuration 불변 +legacy suites | 기존 backup/Snapshot regression | >25MiB R1 backup/atomic restore는 새로 증명하지 않음 |
| I25 incremental | 실제 HTTP/SQL/object/pin 관찰, graph160/1,158 | E3 I25·원 Phase A/RA01 cost | 정상 bounded 경로의 증거, **§35 전체 5-scale·compression grid 미완료** |
| §26·31·34·35 exit | default routing/source hash/build·no activation | 일반 앱·legacy regression | 실기기 durability/R1/full performance gate를 통과시킨 것으로 표시하지 않음 |

전체 backend 회귀 두 번의 미해결 실패 때문에 Phase B 최종 판정은 INCONCLUSIVE다.
추가 상위 증명도 남아 있으므로 전체 T6.6F completion·R1 readiness·일반 사용자 activation·배포를 승인하지 않는다.
