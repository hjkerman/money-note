# T6.6E4 — 구현 전 계약 차단 보고서

**T6.6E4 BLOCKED — CONTRACT OR ARCHITECTURE DECISION REQUIRED**

E4 adapter를 완성하거나 독립 감사 PASS를 선언한 문서가 아니다. 실제 소스를 대조하고
합성 complete generation으로 legacy handoff 제약을 확인한 뒤 구현을 중단했다.
production source·설정·DB·서비스·금융 공식은 변경하지 않았다.

## 1. 시작 commit과 repository

시작점은 `ab59d6bbc39f27c36beb059f984ef527ac7b0bef`다. `HEAD`, `main`, `origin/main`,
실제 remote main이 일치했고 시작 working tree는 clean이었다. E3 독립 감사의
46 PASS와 전체 1,094/1,315 결과는 역사적 기준선이지 이번 실행 결과가 아니다.

## 2. Binding E4 범위

[T6.6C §22](t66/c/t66c-delta-sync-protocol.md#22-legacy-snapshot-v7의-정확한-materialization),
§24–26, §28–29, §31–35를 실제 source와 대조했다. E4는 Pending/Offline/Legacy adapter,
E3는 complete diff/publisher, R1은 large restore/MW다. stage 책임을 재정의하지 않는다.

E1/E2 보고서는 실제 `docs/t66/e/{implementation,audits}/` 경로에서 확인했고
E3 구현·독립 감사, architecture 신뢰 경계와 domain/offline 계약을 대조했다.

## 3. E4/R1 분리

| 분류 | 기능 | 현재 상태 |
|---|---|---|
| 격리 구현 가능 | accepted graph의 원문 읽기·논리 snapshot·typed hot 노출 | 구현하지 않음 |
| 선행 호환 결정 필요 | complete raw/control에서 legacy v7·v4 logical baseline 구성 | 아래 제약으로 BLOCKED |
| E4 소유, 일반 활성화 금지 | frozen B/J와 pending/replay를 기존 lineage로 연결 | 구현하지 않음 |
| R1 소유 | large restore/MW, 검증된 recovery capability와 rollout | DEFERRED |

R1이 없다는 사실만으로 모든 E4 기능을 차단한 것이 아니다. complete legacy
baseline에 필요한 **이미 존재하는 parser의 수락 언어 불일치**가 현재의 선행 제약이다.

## 4. E3 accepted-generation handoff

`mobile/lib/src/segmented/store_publication.dart`의 `recoverAcceptedGeneration`,
`acceptedGeneration`, receipt/manifest 검증을 확인했다. private accepted-session 증거는
owning connection의 data_version·namespace·pointer/sequence·schema·receipt에 결합된다.
staging의 `graph_verified`만으로 authority를 만들지 않는다. 진단에서는 store-owned full
proof와 durable accepted state 및 fresh reopen을 실제 확인했다.

## 5. Segmented identity

Target는 server/dataset/epoch, principal, Versions, revision, context와 네 root를 결합한다.
local generation UUID, observation ID, sync_root, accepted sequence는 서로 다르다.
receipt는 데이터 검증 증거이지 현재 AppState ticket/session 권한이 아니다.

## 6. Snapshot v7 identity

`backend/app/services/snapshot.py:194`의 기존 `snapshot_state_fingerprint`는
schema/range/policy/data의 flat SHA다. content SHA에는 원 export metadata도 들어간다.
§22에 따라 전체 11개 raw table을 exporter 순서·NULL/BINARY·REAL 표현 그대로
materialize해야 한다. sync_root 대입, 부분 Snapshot 또는 새 fingerprint 알고리즘은 금지다.

## 7. OfflineBaseline v4

`mobile/lib/src/offline/offline_data.dart:342`의 `OfflineBaseline.fromJson`은
먼저 `validateMoneyPayload`를 실행한다. baseline에는 complete Snapshot, 실제 legacy
fingerprint, user, synced_at, typed values/defaults와 optional resolved reconciliation ID가
별도로 들어간다. 이 형식이나 lineage 의미를 이번 작업에서 변경하지 않았다.

## 8. Frozen B/J lineage

`OfflineStore.recoveryLineageFingerprint`는 Snapshot fingerprint만이 아니라 **전체
serialized logical baseline**을 식별한다. `state.json`과 B/J의 consistency는
`offline_lineage_validator.dart`가 검사한다. 같은 raw rows 또는 표시 합계가 같다는
이유만으로 lineage equality를 만들 수 없다. §29/§33의 active frozen B/J/finalizing
migration 유예와 자동 rebase 금지는 유지한다.

## 9. Pending 소유권

`offline_store.dart`의 append serial queue가 operation ID·sequence·authoritative input과
알림 등록 중복을 보존한다. `online_write_state.dart`의 outcomeUnknown/committed marker,
manual retry identity는 J와도 별개다. E3 acceptance는 이들 acknowledgment가 아니다.

## 10. 확인된 legacy adapter 제약

E1-A01 교정은 `segmented/object.dart:36,261`의 server-compatible 검증용 whitespace
집합을 적용했다. 반면 기존 `mobile/lib/src/money.dart:50`은 Dart `trim()`을 사용하며
`authoritative_bundle.dart:39`, `offline_data.dart:343`이 이 helper를 공유한다.

`cash_flow_balance = "\u001c+0001000.00\u001f"`의 원문을 다음 경로로 재현했다.

1. 새 합성 금융 DB에서 실제 backend가 complete D3a 관측과 v7 Snapshot/bundle을 생성했다.
2. E1/E2/E3는 full graph/F(raw)/hot-raw 검증 후 accepted sequence=1을 COMMIT했다.
3. 별도 SQLite connection으로 원문 BLOB·accepted row·FK 오류 0을 확인했다.
4. store를 닫고 새로 열어 complete accepted recovery 성공을 확인했다.
5. 기존 bundle parser와 OfflineBaseline v4 parser는 동일 원문을
   `FormatException('money must be an exact safe integer')`로 거부했다.

12개 backend-derived vector에서 기존 legacy Dart와 판정 차이는 7개다. U+001C–001F
경계 공백 및 조합 입력 5개는 legacy에서 거부되고, edge BOM 2개는 legacy에서 수락된다.
중간 BOM은 양쪽 거부다. 자세한 입력과 독립 oracle는
[재현 README](benchmarks/t66e4-contract/README.md)에 보존했다.

처음 `scheduled_income`에 같은 값을 사용한 진단은 server judgment의 직접 `float()`
파싱에서 관측 생성 전 실패했다. 그 최초 setup failure는 보존하며 PASS로 세지 않는다.
해당 값을 float로 바꾸거나 금융 projection을 mock하지 않았다. 실제 complete 관측이
생성되는 cash_flow_balance 사례로 재실행했다. 첫 현상은 별도 backend 관찰이며 이
보고서가 그 원인이나 수정까지 검증했다고 주장하지 않는다.

## 11. 논리 읽기 일관성

구현 후보로 기존 synchronous SQLite read transaction을 검토했다. DELETE journal의
read snapshot은 writer COMMIT/cleanup과 잠금 경합하므로 long reader 동안 STORE_BUSY가
발생할 수 있다. 이는 lock-free reader pin과 같은 보장이 아니다.
[SQLite transaction](https://www.sqlite.org/lang_transaction.html),
[rollback locking](https://www.sqlite.org/lockingv3.html)의 계약도 확인했다.
미검증 reader 초안은 철회했고 source에 남기지 않았다. reader retention 구현 PASS를 주장하지 않는다.

## 12. Canonical 금융 mapping

`hot.state`는 기존 12개 projection이며 backend 금융 authority를 그대로 소비해야 한다.
raw table PK 순서는 legacy export 순서가 아니다. 원문 money/Unicode/REAL/null을
preserve해야 하므로 금액 문자열의 trim·strip·재직렬화 정규화로 위 제약을 우회할 수 없다.
v7 생성 가능성과 기존 v4 parser admission 가능성은 서로 다른 검사다.

## 13. AppState integration

`app_state.dart:423`의 명시 E3 진입점, `:497`의 기존 refresh authority,
`_withLineageLock`, credential getter를 사용하는 E2 session fence를 확인했다.
새 coordinator·authorization token·지속 permit을 만들지 않았다.
startup 또는 정상 AppState 경로에는 변경이 없다.

## 14. Pending/replay coexistence

기존 `_restoreOfflineProjection`은 frozen legacy B에 원래 ordered J를 표시용으로 적용한다.
E4에서 새 segmented G에 J를 자동 적용하는 것은 금지다. 동일 fingerprint 모양, 같은
거래 금액/날짜/문구, 새 accepted root를 acknowledgment나 rebase proof로 사용하지 않는다.
이 coexistence adapter는 아직 구현하지 않았다.

## 15. Acknowledgment authority

현재 `_refreshAuthoritativeState`는 durable baseline, guard, 해당 confirmed marker cleanup,
전체 candidate 설치 순서를 소유한다. Unknown은 GET만으로 retire하지 않는다.
Reconciliation은 기존 receipt/status·artifact·resolved ID를 따른다. 이번 조사에서
pending/J 삭제·retirement·acknowledgment를 호출하지 않았다.

## 16. Offline mode boundary

`enterOfflineMode()`는 기존 legacy baseline·owner·pending/J·lineage 검사를 유지한다.
E3 accepted만으로 이 경계를 통과시키지 않는다. segmented baseline의 신규 설치 또는
source 전환은 수행하지 않았고, legacy baseline을 빈 데이터로 대체하지 않았다.

## 17. R1 gate

§31의 일반 사용자 segmented Offline/recovery gate는 **CLOSED**다. developer flag,
작은 현재 dataset, E3 audit PASS 또는 이 진단 PASS를 capability proof로 사용하지 않는다.
새 gate API/임의 recovery boolean은 도입하지 않았다. R1 또는 동등한 verified recovery
계약이 구현·감사되기 전 일반 사용자 활성화는 불가하다.

## 18. Fallback

기존 legacy source를 그대로 유지한다. 잘못된 segmented input을 숨기며 legacy network
성공으로 전환하는 fallback은 추가하지 않았다. 기존 baseline·pending·J는 불변이다.
E4 실패를 authoritative empty state로 표시하는 동작도 없다.

## 19. Account/session isolation

E1 store namespace와 E3 expected base/current AppState authority는 별도 증거다.
재인증이나 logout 뒤 persisted receipt로 install 권한을 복원하지 않는다. 진단의 store-only
COMMIT은 AppState authorization 시험이 아님을 명시했다. E4 account/session race 시험은 미실행이다.

## 20. Concurrency

E3의 expected base/sequence, data_version, synchronous guard→COMMIT는 변경하지 않았다.
E4 reader/pending replay/source transition의 새 동시성 보장은 아직 구현·검증하지 않았다.
서로 다른 SQLite와 baseline/J 파일의 cross-store atomicity를 주장하지 않는다.

## 21. Process crash

진단은 clean close/reopen의 complete recovery를 실제 확인했다. E4 SIGKILL, durable
source transition 또는 frozen pin 전이 시험은 하지 않았다. E3의 과거 16개 process-kill
결과를 이번 E4 실행 결과로 재사용하지 않으며 power-loss 보장도 주장하지 않는다.

## 22. 성능과 자원

production/E3 알고리즘 변경이 없으므로 새 O(N) scan/pin rewrite를 정상 경로에 넣지 않았다.
진단에는 full initialization/verification/reopen O(N)을 사용했다. E4 cold/repeated read,
pending-heavy workload, generation switch 성능은 미측정이며 I25 통과를 새로 선언하지 않는다.

## 23. 합성 시험과 독립 oracle

[probe.py](benchmarks/t66e4-contract/probe.py)는 실제 backend validators/producer,
[probe_test.dart](benchmarks/t66e4-contract/probe_test.dart)는 기존 Dart parser와 E1/E2/E3를
실행한다. SQL BLOB/accepted/FK는 별도 connection에서 확인한다. 기존 parser의 **거부가
발생해야 통과하는 진단**이며 E4 implementation PASS 또는 independent audit PASS가 아니다.

## 24. 실제 검증 결과

| 이번 실행 | 관찰 |
|---|---|
| 최초 진단 setup | 0 PASS / setup failure 1, server judgment의 scheduled_income float 파싱 |
| 최종 contract 진단 | 5 PASS / 0 FAIL; server-derived vector 12개, legacy 판정 차이 7개 |
| 제한 Flutter 회귀 | 271 PASS / 0 FAIL |
| 제한 backend 회귀 | 117 tests / 357 subtests PASS, warning 1, 37.01초 |
| Flutter analyze | PASS |
| frontend npm build | PASS |
| Ruff / compileall / 새 Dart formatting / diff check | PASS |
| Full Flutter / backend / APK build | NOT RUN |
| E4 구현·race·process-crash / E3 I25 전체 회귀 | NOT RUN |

제한 Flutter 실행 파일은 `segmented_money_correction`, `segmented_schema_correction`,
`segmented_response_cleanup`, `exact_money_domain`, `offline_persistence`,
`offline_lineage_recovery`, `offline_state_projection`, `local_snapshot_repository`의 8개다.
Backend는 `test_exact_money_domain`, `test_snapshot`, `test_snapshot_export_metadata`,
`test_offline_reconciliation`의 4개다. Full regression 미실행은 도구 부재가 아니라
선행 compatibility 결정이 필요하여 E4 구현을 중단했기 때문이다.

## 25. E1/E2/E3 보호

세 단계의 product source는 모두 기존 commit과 동일하다. E1-A01/A02, E2-A01의 제한
회귀는 실제 실행했다. E3 complete proof/receipt/root pins와 fresh recovery는 진단에서
실행했지만, E3 authority/I25/crash 전체 회귀를 이번에 재실행했다고 주장하지 않는다.

## 26. Legacy/B/J 보호

Snapshot v7/OfflineBaseline v4/frozen B/J의 구현과 형식은 변경하지 않았다. 정상
financial read/write, startup, UI, sync와 backend source도 불변이다. 제한 legacy
회귀 8파일에 포함된 검사는 실제 통과했다. E4 transition 전후 byte comparison 또는
새 pending concurrency의 통과를 주장하지 않는다.

## 27. Deferred R1

Large restore/upload/MW·새 recovery endpoint·budget proof·migration/rollback rollout은
R1 및 후속 통합 감사에 남긴다. 현 계약의 Snapshot/hash/J를 대신하는 새 bridge나
복구 토큰을 발명하지 않는다.

## 28. 필요한 소유자 결정

권고 결정은 다음 한 가지다.

**기존 공용 `mobile/lib/src/money.dart.exactMoney()`의 문자열 admission을 이미 감사된
backend/E1 monetary grammar와 정렬하는 최소 선행 교정을 승인할 것인지 결정한다.**

이 변경은 새 금융 계산이 아니다. 다만 기존 bundle·v4 baseline·J·normal input
호출자에게 영향을 줄 수 있으므로 원문 보존, 기존 invalid/BOM 정책, 정확한 범위,
전체 legacy/B/J 회귀를 검증하고 영향 범위를 명시해야 한다. 현재 요청의 normal
read/write 불변 조건을 임의로 넓혀 해석하지 않았다. 원문 정규화나 일부 valid 입력의
무통보 제외는 대안으로 구현하지 않았다.

## 29. 독립 E4 감사 준비

**NO.** 현재는 implementation이 아니라 선행 compatibility 진단이다. E4 adapter,
authority/race/retention/crash, 실제 원문 legacy 왕복, full regressions가 남아 있다.
기존 E3 독립 PASS를 바꾸거나 취소한 것은 아니며 E3 안에서 발견된 결함이라고 주장하지 않는다.

## 30. Commit/push 및 production

완료 gate 미충족으로 **commit/push를 수행하지 않는다**. 새 보고서와 재현 evidence만
working tree에 보존한다. 기존 product 변경은 없고 미검증 reader 초안은 남기지 않았다.
production DB/API/credentials/services에 접근하지 않았고 배포·APK 설치·segmented
activation·R1 구현을 수행하지 않았다.
