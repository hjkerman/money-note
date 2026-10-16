# T6.6F Phase B — B0 binding coverage matrix

이 표는 대규모 회귀 실행 전에 작성한 검증 계획이다. 행을 나열한 사실은 PASS 증거가 아니다.
규범 원본은 `docs/t66/c/t66c-delta-sync-protocol.md` 전체 39개 절이다. 별도의 F 전용 규범 문서는
현재 문서 지도와 검색에서 발견하지 않았다. §34는 R1, interoperability/full-resync/crash,
고정 H/D scaling·압축 비교, 독립 F 감사, 명시 rollout 승인의 순서를 구별한다.

| binding 요구 | backend / Flutter | 기대 동작 | 독립 방법 | 이전 증거 | 새 증거·완료 gate |
|---|---|---|---|---|---|
| I1, §5/15/25 principal | D3 auth / E2 transport, AppState | 원 credential·principal 일치, 재인증 취소 | 실제 TLS HTTP·session barrier·별도 SQL | D3a/b, E3/E4 감사 | current request 및 durable state 비교 |
| I2, §5 epoch | D1 bootstrap / cache namespace | cold startup 새 epoch, old lease 거부·Frozen 보존 | disposable DB reopen/identity 변경 | D1/D3c 감사 | 실제 server/client context negative |
| I3, §6/19 accepted base | D3 base echo / E3 provenance | exact base, same-R roots, seq fence | 독립 target/SQLite 대조 | E3 audit | stale/mixed candidate rejection |
| I4, §9/15 coherent target | D2b/D3a / E2 manifest | 한 R/context/root, terminal auth | 실제 HTTP와 backend SQL oracle | D3a/b | concurrent writer·관측 binding |
| I5, §8/9 11 tables | D2 trees / E2/E3/E4 | 누락 없는 complete graph | backend source SQL→독립 reachability→client SQL | E1–E4 | empty/small/structural fixture equality |
| I6, §7/23 C1 | canonical/raw / c1/object/money | exact bytes·Unicode·money, no normalization | 독립 SHA/C1 및 raw SQL/HTTP bytes | E1/P0 | 필수 U+001C/+0001000.00/U+001F 전층 보존 |
| I7, §8/11 roots | B+tree/Patricia / graph/verify | type/hash/count/range/order | independent decoder 및 부정 payload | D2a/E3 | missing/corrupt/wrong root fail closed |
| I8, §19 diff | D2b capture / E3 tree diff | old/new frontier 완전, 삭제·이동 | G1–G7 source row/set oracle | E3 | localized/deletion/structural changes |
| I9, §10/11 F(raw) | facts/Patricia / verifier | 독립 F와 certified index 일치 | 기존 독립 oracle + 새 실제 HTTP graph | D2/E3 | wrong index/raw negative |
| I10 reverse closure | capture/finalizer / structural verifier | FK/unique/reverse completeness | synthetic related tables 및 SQL fixture | D1/D2b | existing backend property regressions + cross-layer closure |
| I11, §9/14 hot/raw | maintained inputs/presenters / verification | backend same context, shared fields 일치 | server-produced hot/control/raw exact compare | D2b/D3a/E3 | wrong hot/context negative |
| I12 Category C 금지 | financial services / E4 adapter | backend projections 소비, 재계산 없음 | source call graph + backend oracle | architecture/E4 | full financial object equality |
| I13, §24/25 incomplete publication | D3 paths / E1/E3 | durable complete receipt만 accepted | failed acquire/COMMIT 후 independent SQL | E1/E3 | no partial accepted/install |
| I14, §25 authority | authenticated view / AppState E3/E4 | original ticket, final session·mode fence | deterministic authority barrier + SQL | E3/E4 | acquisition→install cross-layer races |
| I15, §28 GET≠receipt | financial receipts / pending handoff | unknown pending 유지·content matching ACK 금지 | exact pending bytes/ID/order before/after | E4 | real sync + similar pending transaction |
| I16, §29 Frozen B/J | old contract / workspace/frozen | lineage·input bytes 보존, 자동 rebase 없음 | B/J golden + source/pins independent SQL | E4/A01/RA01 | retained G1 during G2 and rejection |
| I17, §26/27 crash | DB finalizer / store/workspace | old complete 또는 new complete, authority 복원 금지 | 실제 child SIGKILL·fresh process SQL/read | D3c/E1–E4 | selected established boundaries 명시 |
| I18, §16-S/32 retention | D3c GC / refs/frozen/read scopes | 모든 live owner 보호 | actual pins/objects·maintenance races | D3c/E4 | G1 reader+G2 publish, frozen closure |
| I19, §17/18/30 recovery | lease/restart / fetch/recovery | fresh auth·exact reuse 또는 blocked, J 삭제 없음 | expiry/churn/interruption/fresh process | E2/E4 | real HTTP resume·old source preservation |
| I20, §22 materialization | Snapshot exporter / E4 adapters | exact v7 order/hash/control·v4 lineage | backend-produced v7 + independent validator | E4/P0 | real backend generation full materialization |
| I21, §12/13 tracking | D1/D2b fence / E1 schema | source/capture/roots 같은 commit | direct SQL rollback, missing finalizer/trigger | D1/E1-A02 | existing + selected integrated malformed state |
| I22, §15–17 transfer | D3a/b/c / E2 | credential/path/TTL, bounded retry/resources | real TLS requests/bytes/TCP FD | D3b/M01/E2-A01 | rejection then valid same client |
| I23, §31 large restore | R1 / recovery adapter | chunk/hash/backup/one apply·receipt | 미구현 여부 확인, 현재 limit 보존 | prior deferred evidence | R1 미구현: 전체 F/activation closure 불가, 제품 결함으로 꾸미지 않음 |
| I24, §32 backup 30 | legacy backups / existing artifact store | standalone 30 의미 유지 | source isolation + legacy regression | existing snapshots/offline | baseline unchanged, R1 별도 |
| I25, §35 cost | D2 inputs/D3 root pins / E2–E4 | 정상 full N scan/hash/rewrite 없음 | actual HTTP + temporary-copy SQL/object observer | E3 I25/E4 cost | cold/identical/small/large/restart/fallback 계측 |
| §4/15 version·wire | artifact allowlist / protocol/transport | unsupported reject, legacy API 불변 | real endpoints/methods/status/header/C1 | D3/E2 | actual wire evidence |
| §26 Android proof | SQLite/VFS / sqlite3 | DELETE/EXTRA/FK, IO fail closed | HOST pragmas/crash, build inspection | E1/E3 | 실기기 power loss 미검증을 명시, rollout 차단 |
| §31/33/34 activation | no normal mount / isolated entry only | startup/read/write defaults 불변·R1 closed | source references/default startup+regression | prior audits | no activation/deploy, full F gate 별도 |
| §35 scaling·compression | full D→E | H/D fixed N=1k/5k/10k/50k/100k; median/p95·gzip comparison | bounded campaign 가능 범위부터 계측 | D2/E3 scenario evidence | 미수행 규모/실기기 gate를 SATISFIED로 표시하지 않음 |

## 실제 책임 배치

`backend/isolated_sync`: D1 capture/schema/epoch, D2a canonical B+tree/Patricia,
D2b finalization/maintained inputs, D3a observation, **D3b HTTP object transfer**,
**D3c observation retirement/retention/GC**다. 관측 응답 자체가 manifest이며 별도 manifest GET은 없다.
capabilities는 R1을 허위 광고하지 않도록 명시 404다. 이 isolated subset를 전체 capability/R1 완료로
해석하지 않는다. Flutter E1 object store → E2 acquisition → E3 receipt/publication → E4 read/handoff는
normal startup에서 호출되지 않는 opt-in 경로다.

## 판정 분리

Phase B는 실제 구현된 D1–D3c/E1–E4 통합의 correctness와 해당 cost를 검증한다. R1 미구현,
§35 전체 scaling/compression, §26 실기기 durability 등 필수 상위 exit proof가 남으면
전체 T6.6F 완료·일반 사용자 activation·deployment를 승인할 수 없다. 확정 correctness 또는 I25
위반은 FAIL, 필수 증거 부재는 INCONCLUSIVE로 기록한다. 이전 PASS는 새 cross-layer 실행 수에 넣지 않는다.
