# 모바일 Offline Mode

이 문서는 모바일 Offline Mode Phase 1/1.5의 저장 경계와 Phase 2 atomic reconciliation·Snapshot-backed recovery 구현을 설명한다. 금융 도메인의 단일 진실 원천은 계속 서버 DB와 서버 API 계산 결과다.

## 상태 머신

상태는 앱 전용 문서 저장소의 `offline-mode/state.json`에 원자적으로 보존한다.

- `ONLINE`: 서버가 authoritative하다. foreground refresh, pull-to-refresh, 정상 상태 동기화가 성공하면 offline baseline을 교체한다.
- `OFFLINE`: 마지막 정상 baseline과 append-only journal로 제한된 로컬 화면을 만든다. foreground와 pull-to-refresh는 `/health`만 호출하며 서버 state/snapshot을 fetch하거나 적용하지 않는다.
- `RECONCILIATION_REQUIRED`: health check로 서버 복구를 확인했지만 어느 상태를 사용할지 결정·실행하지 않은 read-only 상태다. 앱 재시작 뒤에도 유지한다.
- `RECONCILIATION_FINALIZING`: authority 선택과 양쪽 recovery point 검증 뒤 실행 결과를 확정하거나 fresh authoritative sync를 기다리는 durable 상태다. commit 상태는 `UNKNOWN` 또는 `COMMITTED`로 별도 보존한다.


정상 API operation의 transport 실패, timeout 또는 HTTP 5xx는 사용자에게 Offline Mode 사용 여부를 묻는다. HTTP 4xx와 같은 application validation 오류는 연결 실패로 분류하지 않는다. 사용자가 Offline Mode를 거절하면 앱을 종료한다. 사용자는 설정 탭에서도 서버 연결 없이 의도적으로 Offline Mode를 시작할 수 있지만, 검증된 baseline이 없으면 온라인에서 한 번 동기화하라는 안내만 표시한다.

서버 복구는 자동 동기화의 허가가 아니다. `OFFLINE -> RECONCILIATION_REQUIRED` 전이만 수행하며 journal이나 로컬 view를 서버 state로 덮어쓰지 않는다.

## 로컬 persistence

새 generic sync framework나 mutable Snapshot DB를 도입하지 않는다. 기존 `path_provider` 기반 앱 전용 저장소에 상태 파일과 별도 recovery directory를 둔다.

- `baseline.json`: 마지막으로 완성된 서버 상태 한 벌, 같은 시점의 authoritative Snapshot B와 canonical server-state fingerprint, `synced_at`. 세션 토큰은 저장하지 않는다.
- `journal.ndjson`: 한 줄에 한 operation인 append-only journal.
- `state.json`: connectivity mode, reconciliation choice/ID/phase, server conflict와 commit/finalization 상태, recovery artifact identity.
- `recovery/`: 검증된 immutable mobile recovery bundle. 정상 성공 뒤에도 retention 대상으로 남긴다.

baseline 후보는 Summary, card payment status, Judgment, month status, settings, 할인 월/프로필, 원장, 정기결제 확인 목록, 패널, 현금흐름이 모두 정상 응답한 뒤 임시 파일에 flush·JSON 검증하고 rename한다. 도중 요청이나 후처리가 실패하면 기존 baseline은 유지한다. area refresh는 갱신 대상 응답이 모두 성공하고 나머지 in-memory state가 이미 완성된 baseline에서 온 경우에만 새 한 벌을 만든다.

journal row의 schema version은 1이며 다음을 가진다.

- 안정적인 `operation_id`
- `operation_type`
- 원래 서버 endpoint에 전달할 authoritative input `payload`
- UTC `created_at`
- 단조 증가 `sequence`
- Phase 1에서는 `pending`만 허용하는 `status`

journal payload에는 `remaining_liquidity`, `card_total`, 서버가 계산한 할인액·실결제액 같은 derived value를 넣지 않는다. 다만 사용자가 카드 사용 등록 시 직접 입력한 실결제액은 authoritative input이며, 기존 online API와 losslessly 호환되는 수동 할인 입력 `discount_override_amount = 원금 - 사용자 입력 실결제액`으로 보존한다. 마지막 append가 crash로 잘린 경우 완성되지 않은 마지막 줄만 무시하고 다음 append 전에 그 꼬리를 잘라내며, 그 이전 줄의 손상·중복 id·순서 역전은 오류로 취급한다. Phase 2 cleanup은 reconciliation commit/authoritative rebuild/fresh baseline이 모두 끝난 뒤에만 journal을 삭제한다.

## 지원 operation matrix

| 기능 | ONLINE | OFFLINE | RECONCILIATION_REQUIRED |
| --- | --- | --- | --- |
| 카드 사용 기록(할인 선택·사용자 실결제 override 포함) | 서버 write | `CREATE_CARD_EXPENSE` journal | 금지 |
| 현금 입금/출금 | 서버 write | `CREATE_CASH_FLOW` journal | 금지 |
| 현금성 고정지출 확인 | 서버 write | `CONFIRM_FIXED_EXPENSE` journal | 금지 |
| 카드 정기결제 확인 | 서버 write | `CONFIRM_PLANNED_CARD_EXPENSE` journal | 금지 |
| 월마감, 카드 이월/결제 전이, 기존 항목의 할인·실결제 수정, 삭제·취소, 정산 완료, 설정 변경, Snapshot restore | 서버 write | 금지 | 금지 |

알림 후보의 본인카드 원장 등록은 카드 사용 기록과 같은 journal 경로를 쓴다. Claim과 Family Card 등록은 server-only다.

## Display-only estimate

OFFLINE 화면은 baseline에 journal을 sequence 순으로 투영한다. 이 결과는 `오프라인 예상값`으로 항상 표시하며 server authoritative 값이나 reconciliation payload가 아니다.

최소 projection은 다음 delta만 적용한다.

- 카드 사용: baseline의 마지막 authoritative 할인 월 상태를 신규 입력의 기본 할인 의도로 사용한다. 사용자가 실결제액을 직접 입력했다면 그 값을 가장 정확한 입력으로 투영한다. 직접 입력이 없고 할인 의도가 켜져 있으면 baseline에 서버가 포함한 버전드 `projection_policy` descriptor를 해석해 표시용 할인액을 계산한다. 모바일은 할인율·카드 분류·정책 선택 규칙을 자체 보유하지 않으며 descriptor가 없거나 schema, 정책 종류, 반올림 방식 또는 rate를 이해할 수 없으면 gross amount를 쓰는 보수적 fallback으로 표시한다.
- 현금 입출금: server clock을 사용할 수 없으므로 projection 시점의 device-local date를 기준으로 `occurred_on <= local today`인 signed amount만 현금흐름 반영액과 잔여 유동성에 더한다. 미래 날짜 건은 목록에는 보이지만 그 날짜 전까지 합계에 반영하지 않는다.
- 현금성 고정지출 확인: pending reserve를 제거하고 실제 출금액을 반영하여 잔여 유동성에 `reserve - actual`을 더한다.
- 카드 정기결제 확인: template reserve를 제거하고 할인 미반영 gross 실제 원금을 반영하여 잔여 유동성에 `reserve - actual`을 더한다.

서버 날짜, 할인 정책 또는 다른 transition을 확실히 재현할 수 없는 부분은 stale/estimated 표시를 유지한다. 기기 clock/timezone을 서버와 맞추는 subsystem은 두지 않는다. journal에는 위 계산 결과를 쓰지 않으며 reconciliation 후 서버 날짜와 기존 정책으로 Summary를 다시 계산해야 한다.

`projection_policy`는 마지막 동기화 당시의 표시 정확도를 높이는 서버 소유 descriptor일 뿐 서버의 authoritative 계산 결과가 아니다. journal과 Phase 2 replay payload에는 descriptor나 그 계산 결과를 넣지 않는다.

## Phase 2 replay completeness

| Operation | stable target/identity와 authoritative input |
| --- | --- |
| 카드 사용 | operation id, 사용일, 사용처·내용, 원금, 분류, 할인 적용 의도, optional 수동 할인 입력, optional 알림 후보 key |
| 현금 입출금 | operation id, 발생일, 제목, signed amount, primary-income 여부 |
| 현금성 고정지출 확인 | operation id, baseline panel id, 발생일, 실제 금액 |
| 카드 정기결제 확인 | operation id, baseline planned-entry id, 발생일, 실제 원금 |

모든 row는 `sequence`, `created_at`, `pending` status를 가진다. 서버는 이 input을 하나의 transaction과 idempotency 경계에서 검증·적용하며 sequential endpoint replay는 사용하지 않는다.

## Phase 2 reconciliation interface

`OfflineStore.loadReconciliationBundle()`은 baseline B, sequence 순 journal J, durable reconciliation metadata를 함께 제공한다. 사용자는 recovery artifact 준비 전에는 실행 선택만 할 수 있고, 실제 destructive action에는 별도 최종 확인이 필요하다.

### 공통 recovery gate

Mobile Wins와 Server Wins 모두 다음 순서를 통과해야 한다.

1. stable `reconciliation_id`와 선택을 `state.json`에 `PREPARING`으로 저장한다.
2. 현재 서버 S를 기존 Snapshot export/manifest/dry-run 검증으로 `snapshot-backups/pre_reconcile_server-<UTC timestamp>[-N].money-note-snapshot.json`에 보존한다.
3. B, ordered J, reconciliation metadata와 identity를 앱 저장소의 `offline-mode/recovery/pre_reconcile_mobile-<UTC timestamp>-<reconciliation_id>.money-note-offline-recovery.json`에 보존한다.
4. mobile bundle의 canonical SHA-256을 다시 계산해 manifest와 일치하는지 확인한 뒤 `READY`를 저장한다.

둘 중 하나라도 실패하면 server financial replacement나 journal 폐기는 시작하지 않는다. server artifact는 기존 `pre_restore` 목록과 `MONEY_NOTE_PRE_RESTORE_KEEP_COUNT` retention에 참여한다. mobile artifact는 앱 전용 recovery directory에서 최근 30개를 보존하며 reconciliation 성공 직후 삭제하지 않는다.
Phase 2 도입 전에 이미 OFFLINE이었던 schema v1 baseline에는 authoritative Snapshot B와 server fingerprint가 없다. 이를 추정해 Mobile Wins로 승격하지 않는다. 대신 legacy baseline과 J를 mobile bundle에 losslessly 보존하고 server artifact를 만든 뒤 Server Wins만 허용한다.


### Mobile Wins

`B`는 Offline 진입 직전 authoritative Snapshot, `J`는 ordered authoritative-input journal, `S`는 실행 직전 서버 상태다. Mobile Wins 결과는 정확히 `Apply(B, J)`이며 `Apply(S, J)`나 mobile projection 업로드가 아니다.

서버는 하나의 `BEGIN IMMEDIATE` transaction에서 다음을 수행한다.

1. B의 Snapshot manifest, schema compatibility, policy compatibility와 in-memory restore를 검증한다.
2. 현재 S fingerprint가 준비 때 확인한 fingerprint와 일치하는지 검사하고, `S != B`이면 추가 confirmation을 요구한다.
3. transaction에서 본 S의 검증된 `pre_reconcile_server` artifact를 다시 만든다.
4. Snapshot의 authoritative table만 B로 교체한다.
5. J를 sequence 순으로 기존 online domain/service 함수에 같은 SQLite connection을 전달해 적용한다.
6. foreign key와 금융 관계 invariant, Summary를 검증하고 durable reconciliation result와 operation identity를 기록한다.
7. 모두 성공하면 commit하고 하나라도 실패하면 S로 rollback한다.

`offline_reconciliations`는 `reconciliation_id`, logical request digest, baseline/pre-server/result fingerprint, artifact 이름, status/result와 commit 시각을 보존한다. 같은 ID와 같은 digest의 재시도는 저장된 committed result를 반환하고 replay하지 않는다. 같은 ID와 다른 digest는 거부한다. `offline_reconciliation_operations.operation_id`는 reconciliation 간에도 전역 중복을 거부한다.

요청 응답이 유실되면 모바일은 `RECONCILIATION_FINALIZING`과 `UNKNOWN` commit 상태를 유지하고 `/status`에서 같은 ID를 조회한다. committed면 replay 없이 fresh sync만 수행한다. 미commit이면 저장된 같은 선택·ID·payload만 재시도할 수 있으며 authority 선택 화면으로 돌아가지 않는다.

commit 뒤 fresh state fetch, mobile rebuild 또는 새 baseline 저장이 실패하면 `MOBILE_COMMITTED` finalizing 상태와 journal/recovery metadata를 유지한다. 서버 반영 완료를 UI에 표시하되 ONLINE으로 가장하지 않고, 재시작이나 연결 회복 때 fresh sync/finalization만 재시도한다.

### Server Wins

Server Wins는 server financial state를 쓰거나 J를 replay하지 않는다. 양쪽 artifact를 검증한 뒤 current server state 전체를 fetch·검증하고 모바일 상태와 fresh offline-ready baseline을 교체한다. fetch/rebuild/baseline 저장 중 하나라도 실패하면 기존 offline projection, journal, metadata와 artifacts를 보존하고 `SERVER_WINS_FINALIZING`에서 재시도한다.

### 성공과 cleanup 경계

Mobile Wins는 atomic server commit 확인, fresh authoritative fetch, mobile rebuild와 fresh baseline 저장까지 성공해야 완료다. Server Wins도 fresh fetch/rebuild/baseline 저장까지 성공해야 한다. 그 뒤에만 journal을 삭제하고 transient reconciliation metadata를 ONLINE으로 교체한다. crash가 baseline 저장과 journal 삭제 사이, journal 삭제와 ONLINE metadata 저장 사이에 발생해도 committed/finalizing identity 때문에 journal을 replay하지 않는다. retained recovery artifacts와 server idempotency history는 cleanup 대상이 아니다.

## Snapshot subsystem 재사용

Snapshot은 Offline Mode의 mutable database나 journal이 아니다. reconciliation 직전에 server recovery artifact를 만드는 용도로 기존 export/validation/compatibility/restore-safety semantics를 그대로 재사용한다.

현재 server Snapshot 특성은 다음과 같다.

- `GET /api/admin/snapshot`은 하나의 SQLite read transaction에서 전체 장부 운용 테이블과 비민감 설정을 export한다.
- 현재 생성 형식은 schema v7이고 restore는 v4, v5, v6, v7을 지원한다. v3 이하는 거부한다.
- 파일명은 `money-note-snapshot-<UTC timestamp>.money-note-snapshot.json`이다.
- canonical manifest는 테이블/컬럼, 상단 metadata와 card charge policy를 SHA-256으로 검증한다. v4는 원문 manifest 검증 뒤 과거 유동성 key를 정규화한다.
- restore는 현재 schema의 in-memory SQLite에 dry-run하여 foreign key와 금융 관계를 검사한다.
- 실제 restore는 `IMMEDIATE` transaction을 확보한 뒤 같은 transaction 상태의 mandatory `pre_restore-<UTC timestamp>[-N].money-note-snapshot.json`을 `snapshot-backups/`에 원자적으로 생성·재검증하고 테이블을 교체한다.
- 모바일은 서버 Snapshot 파일을 별도 앱 저장소에 최대 30개 보관하며 자동 restore하지 않는다.

Mobile recovery bundle은 Snapshot schema로 변환하지 않는다. Snapshot schema에 journal을 섞거나 mobile projection을 restore/replay input으로 취급하지 않는다.
