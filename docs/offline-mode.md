# 모바일 Offline Mode

이 문서는 모바일 Offline Mode Phase 1/1.5의 저장 경계, 상태 머신, 표시용 projection과 Phase 2 atomic reconciliation 계약을 설명한다. 금융 도메인의 단일 진실 원천은 계속 서버 DB와 서버 API 계산 결과다.

## Phase 1 상태 머신

상태는 앱 전용 문서 저장소의 `offline-mode/state.json`에 원자적으로 보존한다.

- `ONLINE`: 서버가 authoritative하다. foreground refresh, pull-to-refresh, 정상 상태 동기화가 성공하면 offline baseline을 교체한다.
- `OFFLINE`: 마지막 정상 baseline과 append-only journal로 제한된 로컬 화면을 만든다. foreground와 pull-to-refresh는 `/health`만 호출하며 서버 state/snapshot을 fetch하거나 적용하지 않는다.
- `RECONCILIATION_REQUIRED`: health check로 서버 복구를 확인했지만 어느 상태를 사용할지 결정·실행하지 않은 read-only 상태다. 앱 재시작 뒤에도 유지한다.

정상 API operation의 transport 실패, timeout 또는 HTTP 5xx는 사용자에게 Offline Mode 사용 여부를 묻는다. HTTP 4xx와 같은 application validation 오류는 연결 실패로 분류하지 않는다. 사용자가 Offline Mode를 거절하면 앱을 종료한다. 사용자는 설정 탭에서도 서버 연결 없이 의도적으로 Offline Mode를 시작할 수 있지만, 검증된 baseline이 없으면 온라인에서 한 번 동기화하라는 안내만 표시한다.

서버 복구는 자동 동기화의 허가가 아니다. `OFFLINE -> RECONCILIATION_REQUIRED` 전이만 수행하며 journal이나 로컬 view를 서버 state로 덮어쓰지 않는다.

## 로컬 persistence

새 generic sync framework나 mutable Snapshot DB를 도입하지 않는다. 기존 `path_provider` 기반 앱 전용 저장소에 다음 세 파일만 둔다.

- `baseline.json`: 마지막으로 완성된 서버 상태 한 벌과 `synced_at`. 세션 토큰은 저장하지 않는다.
- `journal.ndjson`: 한 줄에 한 operation인 append-only journal.
- `state.json`: connectivity mode와 Phase 2가 사용할 reconciliation choice.

baseline 후보는 Summary, card payment status, Judgment, month status, settings, 할인 월/프로필, 원장, 정기결제 확인 목록, 패널, 현금흐름이 모두 정상 응답한 뒤 임시 파일에 flush·JSON 검증하고 rename한다. 도중 요청이나 후처리가 실패하면 기존 baseline은 유지한다. area refresh는 갱신 대상 응답이 모두 성공하고 나머지 in-memory state가 이미 완성된 baseline에서 온 경우에만 새 한 벌을 만든다.

journal row의 schema version은 1이며 다음을 가진다.

- 안정적인 `operation_id`
- `operation_type`
- 원래 서버 endpoint에 전달할 authoritative input `payload`
- UTC `created_at`
- 단조 증가 `sequence`
- Phase 1에서는 `pending`만 허용하는 `status`

journal payload에는 `remaining_liquidity`, `card_total`, 서버가 계산한 할인액·실결제액 같은 derived value를 넣지 않는다. 다만 사용자가 카드 사용 등록 시 직접 입력한 실결제액은 authoritative input이며, 기존 online API와 losslessly 호환되는 수동 할인 입력 `discount_override_amount = 원금 - 사용자 입력 실결제액`으로 보존한다. 마지막 append가 crash로 잘린 경우 완성되지 않은 마지막 줄만 무시하고 다음 append 전에 그 꼬리를 잘라내며, 그 이전 줄의 손상·중복 id·순서 역전은 오류로 취급한다. Phase 1에는 baseline, journal, recovery metadata cleanup을 실행하는 경로가 없다.

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

모든 row는 `sequence`, `created_at`, `pending` status를 가진다. Phase 2는 이 input을 하나의 server transaction과 idempotency 경계에서 검증·적용해야 하며 Phase 1.5에는 replay나 임시 sequential sync를 추가하지 않는다.

## Phase 2 reconciliation interface

`OfflineStore.loadReconciliationBundle()`은 다음 read-only bundle을 제공한다.

- baseline과 마지막 정상 sync metadata
- sequence 순 pending operations
- 사용자가 선택한 `APPLY_TO_SERVER` 또는 `DISCARD_AND_USE_SERVER`

Phase 1 UI는 두 선택을 저장하지만 replay, discard, partial apply, automatic retry를 실행하지 않는다. Phase 2는 operation별 idempotency와 server validation, 실패 위치 보존, fresh authoritative sync를 설계해야 한다. cleanup은 reconciliation 전체 성공과 fresh server sync가 모두 끝난 뒤에만 별도 API로 추가한다.

## Snapshot subsystem 재사용 계획

Snapshot은 Offline Mode의 mutable database나 journal이 아니다. Phase 2에서 reconciliation 직전에 server/mobile 양쪽 recovery artifact를 만드는 용도로 기존 subsystem을 그대로 재사용한다.

현재 server Snapshot 특성은 다음과 같다.

- `GET /api/admin/snapshot`은 하나의 SQLite read transaction에서 전체 장부 운용 테이블과 비민감 설정을 export한다.
- 현재 생성 형식은 schema v7이고 restore는 v4, v5, v6, v7을 지원한다. v3 이하는 거부한다.
- 파일명은 `money-note-snapshot-<UTC timestamp>.money-note-snapshot.json`이다.
- canonical manifest는 테이블/컬럼, 상단 metadata와 card charge policy를 SHA-256으로 검증한다. v4는 원문 manifest 검증 뒤 과거 유동성 key를 정규화한다.
- restore는 현재 schema의 in-memory SQLite에 dry-run하여 foreign key와 금융 관계를 검사한다.
- 실제 restore는 `IMMEDIATE` transaction을 확보한 뒤 같은 transaction 상태의 mandatory `pre_restore-<UTC timestamp>[-N].money-note-snapshot.json`을 `snapshot-backups/`에 원자적으로 생성·재검증하고 테이블을 교체한다.
- 모바일은 서버 Snapshot 파일을 별도 앱 저장소에 최대 30개 보관하며 자동 restore하지 않는다.

Phase 2는 replay 시작 전에 기존 export/validation으로 server artifact를 만들고, baseline+journal+선택 metadata를 별도 mobile recovery artifact로 보존해야 한다. Snapshot schema에 journal을 섞거나 Snapshot restore 결과를 offline derived state로 취급하지 않는다.
