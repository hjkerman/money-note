# T6.6D1 — 격리된 transactional capture와 commit fence

## 1. 판정·범위

**IMPLEMENTED / NOT ACTIVATED:** 기존 runtime과 분리된 실제 SQLite capture foundation이다. `backend/isolated_sync/capture.py`와 직접 회귀 테스트만 추가했다. 기존 `app/`, migration 목록, Dockerfile, API, mobile 코드는 수정하지 않았다. 정상 DB checkpoint는 여전히 4다.

**DEFERRED TO D2:** epoch/bootstrap, segment/root/index/aggregate와 완전한 pre-commit finalizer, 정상 writer 연결, 운영 migration/activation이다. D1의 `capture_only` 기록은 금융 authority나 sync root가 아니며 이를 대신해서는 안 된다. 독립 D1 구현 감사는 별도다.

시작 상태: branch `main`, HEAD = local main = origin/main = 실제 remote main = `98950ebd52f5c5c3c5d562e844dc19578e962d56`, clean working tree. T6.6C 감사의 조건부 통과는 사용자 제공 결과이며 이번 내부 검증을 독립 감사로 표현하지 않는다.

## 2. C66-B01 명세 보완

[T6.6C §8, §35](t66c-delta-sync-protocol.md)의 관련 문단만 보완했다. v1은 logical raw state 변경 없이 root/representation만 바꾸는 선택적 maintenance compaction을 금지한다. 정상 committed mutation에 필요한 split/merge/rebalance는 허용한다. 동일 epoch·동일 revision의 root 불일치 거부는 유지한다. 향후 선택적 compaction은 안전한 epoch/bootstrap 등 별도 authority transition의 독립 검토가 필요하다. compaction 구현은 없다.

## 3. 격리·버전 경계

`CaptureSandbox`는 직접 생성한 `TemporaryDirectory(prefix="money-note-d1-")` 안의 새 synthetic DB만 소유한다. 기존 DB 경로를 받는 installer나 환경 변수 feature gate가 없다. `path`는 읽기 전용 property다. `install=False`는 실제 기존 initializer로 만든 checkpoint 4에 synthetic 값을 넣은 뒤 격리 migration을 시험할 때 사용한다.

격리 checkpoint는 `PRAGMA user_version=1000001`, profile version은 1이며 `isolated_capture_only`를 명시한다. 이는 **운영 next migration 번호가 아니다**. 기존 `initialize_database`와 authoritative-state `_construct`가 이 profile을 거부함을 검증했다. legacy checkpoint 4를 재해석하거나 runtime admission을 완화하지 않는다. 기존 Dockerfile은 `app`, `scripts`만 복사하므로 이 별도 package를 포함하지 않는다. 정상 startup은 이 package를 import하지 않는다.

설치 순서:

1. 자체 생성 DB를 기존 `initialize_database(conn, SCHEMA)`로 실제 checkpoint 4까지 초기화한다.
2. `BEGIN IMMEDIATE`에서 기존 money/recurring/schema admission을 재검사한다.
3. 격리 metadata와 같은 이름의 33개 replacement trigger를 설치한다.
4. profile/version과 정확한 새 schema contract를 검증한다.
5. 한 번에 commit한다. 중간 실패는 DDL·version·데이터를 함께 rollback한다.

동일 profile 재설치는 검증만 수행한다. 금융 행이나 revision을 다시 쓰지 않는다. 향후 정상 runtime migration은 별도 versioned 변경·리뷰가 필요하며 이 installer를 운영 DB에 연결하는 것으로 대체할 수 없다.

## 4. Transaction context와 metadata

| 격리 table | 구현 의미 |
| --- | --- |
| `sync_capture_profile` | 격리 schema version·비활성 상태 |
| `sync_tx_context` | singleton writer context, 새로운 UUID, base revision |
| `sync_changes` | trigger 후 revision, tx_id, table/op, old/new PK, 각 side의 포함 여부 |
| `sync_change_cells` | revision/side/column별 원래 SQLite storage class와 값 |
| `sync_tx_fence` | 같은 tx_id의 완료 certificate 없이는 COMMIT 불가인 deferred FK |
| `sync_capture_commits` | base/target R·change_count·`capture_only`; root 필드 없음 |

`begin_capture()`는 기존 transaction/savepoint 안의 시작을 거부하고 `BEGIN IMMEDIATE`로 writer lock을 확보한 뒤 schema/context를 확인한다. 재사용된 완료 tx_id도 거부한다. metadata API 외 직접 수정, revision 직접 수정, DDL/ATTACH, FK/recursive trigger 비활성화와 `defer_foreign_keys=OFF`를 지원 connection의 authorizer가 거부한다. `cached_statements=0`으로 privileged metadata statement의 prepared-statement 재사용에 따른 guard 우회를 피한다.

이 authorizer는 악성 Python 코드에 대한 sandbox가 아니다. `set_authorizer(None)`, private metadata 권한 사용, 별도 privileged connection의 metadata 위조, FK OFF, DB 파일 변조는 지원 writer 계약 밖이다. 이는 [T6.6C §12](t66c-delta-sync-protocol.md)의 trusted backend 전제와 같다. 일반 direct SQL은 허용하며 capture는 Python writer 호출 횟수가 아니라 실제 DB trigger로 수행한다.

## 5. Capture contract와 33개 trigger

`_trigger(table, operation)`가 다음 11개 table의 INSERT/UPDATE/DELETE body를 생성한다. 이름은 `revision_<table>_<insert|update|delete>`이며 총 33개다. body 전체를 admission에서 비교한다. trigger 수만으로 완전성을 주장하지 않고 실제 before/after 재생 oracle을 사용했다.

| authoritative table | PK | capture 사건 |
| --- | --- | --- |
| `ledger_entries` | id | INSERT / UPDATE / DELETE |
| `monthly_panels` | id | INSERT / UPDATE / DELETE |
| `cash_flows` | id | INSERT / UPDATE / DELETE |
| `card_payment_batches` | id | INSERT / UPDATE / DELETE |
| `card_payment_batch_items` | id | INSERT / UPDATE / DELETE |
| `card_payment_events` | id | INSERT / UPDATE / DELETE |
| `card_payment_allocations` | id | INSERT / UPDATE / DELETE |
| `card_payment_deferrals` | entry_payment_key | INSERT / UPDATE / DELETE |
| `notification_candidate_registrations` | registration_key | INSERT / UPDATE / DELETE |
| `app_settings` | key | INSERT / UPDATE / DELETE, 민감 값 제외 |
| `app_labels` | key | INSERT / UPDATE / DELETE |

각 body는 context 없으면 ABORT → 기존과 같이 R+1 → 정확한 old/new PK·row capture → fence 보장을 수행한다. 변경된 column만이 아니라 양쪽 row의 모든 알려진 column을 기록한다. INSERT old/DELETE new는 없다. UPDATE는 PK 이동도 old/new로 기록한다. 같은 행 반복 변경, no-op UPDATE, 중간 DELETE/재삽입을 coalesce하지 않아 D2가 정확한 순서를 재구성할 수 있다.

값을 JSON1로 먼저 serialize하지 않는다. affinity 없는 `value` column에 원래 값을 저장하고 `typeof(value)=storage_type` CHECK를 둔다. INTEGER/REAL/TEXT/BLOB/NULL, 안전 정수 경계, NUL·한글·supplementary Unicode를 그대로 보존한다. fractional/BLOB 테스트는 capture 표현 손실 여부를 시험한 것이지 그러한 값의 금융 admission을 승인한 것이 아니다.

`share_pin_hash`, `share_pin_is_default`는 revision marker와 비민감 key/visibility만 남기고 해당 side의 **어떤 값 cell도 복사하지 않는다**. 포함↔제외 key 변경은 허용된 side만 남긴다. auth token/password는 authoritative 11개 table의 capture 대상이 아니다.

SQLite `REPLACE`의 implicit DELETE도 기록하려고 모든 지원 connection에서 `recursive_triggers=ON`을 검증한다. 외부 UPSERT/FK action의 conflict 정책은 trigger 안 `OR IGNORE`를 덮을 수 있다. 실제 실패 재현 후 fence INSERT를 `WHERE NOT EXISTS`로 구현하여 이 의존성을 제거했다.

## 6. Revision·fence·실패 원자성

기존 R 의미는 보존한다: 한 transaction의 row 사건마다 증가하고 no-op UPDATE도 증가한다. 임의의 transaction 하나가 R을 한 번만 증가한다는 가정은 없다. finalization 전 `base+1..target`의 모든 marker가 중복·누락 없이 존재해야 하고 모든 visible old/new row의 column 집합이 완전해야 한다.

`sync_tx_fence.finalized_tx_id`는 NOT NULL·tx_id 일치 CHECK와 `sync_capture_commits(tx_id)`에 대한 `DEFERRABLE INITIALLY DEFERRED` FK를 갖는다. context 생성 때 fence를 만들고 각 trigger도 존재를 보장한다. `finalize_capture()`는 coverage/schema를 검증하고 **savepoint 안에서** certificate 삽입+context 삭제를 완료한다. 두 작업 사이 실패도 certificate를 rollback하여 fence가 계속 commit을 거부하게 한다. savepoint 복구 자체가 실패하면 전체 transaction을 rollback한다.

finalize 후 raw write는 context 부재로 ABORT한다. 내부 `RELEASE`는 외부 BEGIN의 COMMIT이 아니므로 미완료 fence를 통과시키지 않는다. finalization 자체를 savepoint rollback하면 certificate 삭제·context 복원이 함께 일어나 다시 capture할 수 있다. 실패한 COMMIT은 완료로 처리하지 않는다. SQLite가 transaction을 유지한 경우 정상 finalization 뒤 재commit하거나 rollback할 수 있고, 다른 connection은 그 전 변경을 보지 못한다.

native COMMIT이 금융 FK와 fence를 모두 검사한다. D1 finalizer가 모든 역사 행을 다시 `foreign_key_check`하는 pass는 넣지 않았다. D2의 global structural closure/root 보증을 이 certificate가 대신하지 않는다. capture/coverage 비용은 transaction의 사건 수·row 폭에 비례하며 동일 행의 반복 사건도 포함한다. scaling benchmark나 root/index의 O(log N) 성능은 이번에 입증한 것이 아니다.

## 7. 실제 FK action coverage

| parent 삭제 | 실제 action / child |
| --- | --- |
| ledger_entries | SET NULL: ledger.source_planned_entry_id; CASCADE: batch_items.entry_id |
| cash_flows | SET NULL: panels.confirmed_cash_flow_id, events.cash_flow_id |
| card_payment_batches | CASCADE: events.batch_id, batch_items.batch_id |
| card_payment_events | CASCADE: allocations.payment_event_id |

모두 child의 동일 audited trigger에서 기록한다. 현재 schema에 ON UPDATE CASCADE는 없다. 참조 중인 PK의 허용되지 않는 이동은 기존 SQLite FK가 거부한다. 별도 비참조 PK 이동은 테스트했다. SQL FK가 아닌 payment_key·source/epoch 관계의 변경은 원래 row 값으로 남으며 D2 global index/reverse-reference 검증이 필요하다.

## 8. 실제 writer inventory와 연결 상태

**모든 정상 writer는 NOT ACTIVATED다.** 아래 “capture 대상”은 그 SQL이 **격리 profile의 authorized connection**에서 실행될 때의 DB-level coverage다. 정상 `app.db.session()`이 D1에 연결되었다는 뜻이 아니다.

| 현재 source / 함수군 | authoritative 변경·경계 | 이번 증거 / 후속 의존성 |
| --- | --- | --- |
| [db.py](../backend/app/db.py) `connect/session/borrowed_or_new_session` | 기존 transaction 소유·commit, 33 revision triggers | 원본 불변; normal wrapper 변경은 D2 이후 |
| [entries.py](../backend/app/repositories/entries.py) create/update/delete/reorder/append_planned/confirm | ledger, 관련 payment·registration, recurring source/child | 33개 event 재생 + 실제 borrowed recurring writer 동등성; 전체 정상 연결 유보 |
| [panels.py repository](../backend/app/repositories/panels.py) create/update/delete/delete_by_type | panels·registration | table 재생 + 실제 fixed create/confirm; 자체 session 경로 연결 유보 |
| [cash_flows.py](../backend/app/repositories/cash_flows.py) create/delete | cash·fixed panel unlink | 실제 create/readback·동등성 + FK SET NULL |
| [notification_registration.py](../backend/app/repositories/notification_registration.py) save_registration, entries/panels의 registration rewrite | registration identity/fingerprint | full old/new 재생; target은 logical reference로 D2 index 필요 |
| [card_payments.py](../backend/app/services/card_payments.py) event/create/delete, discount, late entry, defer/cancel, batch/reset/policy | events/allocations/items/batches/deferrals/ledger/cash/settings | 모든 raw table 사건·cascade 재생; 전체 service 연결과 maintained aggregate는 D2 이후 |
| [card_charge/profiles.py](../backend/app/services/card_charge/profiles.py) set_transit_discount_profile | app_settings UPSERT | 실제 borrowed policy writer 동등성, 금융 함수 불변 |
| [operations.py](../backend/app/routers/operations.py) patch_setting, [labels.py](../backend/app/repositories/labels.py) upsert_label | settings/labels UPSERT, own session | UPSERT 및 두 table coverage; own-session integration 유보 |
| [services/panels.py](../backend/app/services/panels.py) confirm_fixed_panel / complete_panels_by_type | panel+cash, Claim/Family bulk delete+필수 backup | 실제 fixed writer + raw bulk/cascade; backup gate 불변 |
| [month.py](../backend/app/services/month.py) close_current_month | archive 새 ID INSERT/current DELETE, registration, source/fixed reset, income·batch | old/new ID와 다중 table 재생; 실제 month-close 정상 회귀, profile top-level 통합 유보 |
| [snapshot.py](../backend/app/services/snapshot.py) restore/_replace_snapshot_tables | 11개 교체, 비민감 settings만 교체, mandatory backup/dry-run | 실제 raw replacement+v7 roundtrip; 전체 restore adapter는 아래 의존성 |
| [reset.py](../backend/app/services/reset.py) reset_ledger_data | 운용 8 table bulk delete + mandatory backup | raw DELETE/cascade coverage; epoch rotation·정상 reset 통합 유보 |
| [offline_reconciliation.py](../backend/app/services/offline_reconciliation.py) apply_mobile_wins | B 교체+순서 J+receipt를 한 IMMEDIATE transaction | 원본 불변, 기존 전체 suite; 정상 wrapper·epoch/root integration 유보 |
| [share_auth.py](../backend/app/share_auth.py) ensure_default_share_pin/set_share_pin | 민감 settings 2개 | 두 key 양방향 visibility/비복사 테스트; startup/own session 연결 유보 |
| [db_migrations.py](../backend/app/db_migrations.py), [recurring_compatibility.py](../backend/app/services/recurring_compatibility.py) upgrade/_write_epoch | default/backfill/recurring checkpoint | 기존 정상 4까지 먼저 초기화; profile 설치의 전후 보존·원자 rollback; future bootstrap 필요 |
| [recurring_canonicalization.py](../backend/app/services/recurring_canonicalization.py) execute(apply), [clean_panel_dates.py](../backend/scripts/clean_panel_dates.py) main | 별도 SQLite maintenance writes | 이번에 실행하지 않음. 향후 audited wrapper 또는 quiescent epoch/bootstrap; context 없는 profile write는 거부 |
| auth/create_user, audit, startup maintenance, reconciliation receipt table | Snapshot 11개 밖 users/sessions/audit/receipt | 금융 row capture 밖; 원 transaction의 원자성은 유지, future control/receipt review 필요 |

**중요한 통합 의존성:** 기존 `restore_snapshot`/`validate_reconciled_financial_state`의 전체 FK 검사는 pre-finalize fence의 의도적인 미해결 FK도 오류로 본다. D1은 이를 숨기거나 기존 validator를 수정하지 않았다. 이번 raw replacement 시험은 validate v7 → authorized replacement → capture finalize → native FK/commit 순서의 **격리 증거**다. 정상 restore/Mobile Wins를 activate하기 전, 기존 필수 backup·금융 검사·epoch rotation을 보존하고 오직 검증된 현재 fence만 구분하는 audited adapter와 D2 root finalizer가 필요하다. 이 작업은 현재 runtime에 영향이 없는 명시적 후속 prerequisite이며, 정상 경로를 이미 지원한다고 주장하지 않는다.

## 9. Schema admission

기존 `_validate_current_schema`에 변경된 trigger contract를 전달하고 원래 PK/UNIQUE/FK/critical-index 검사를 그대로 실행한다. 여기에 모든 33 trigger SQL의 정확한 일치, metadata table/index/constraint SQL 전체 일치, profile/version, 금융 column 집합의 정확한 일치를 추가한다. `table_xinfo`로 generated/hidden sibling column도 놓치지 않는다. unknown/missing/altered trigger, metadata 변경, 미캡처 raw column을 거부한다.

legacy initializer의 trigger admission을 완화하지 않았다. D1 schema는 기존 authority endpoint와 legacy initializer가 거부하는 별도 checkpoint다. financial table DDL, N4 partial UNIQUE index, FK action과 Snapshot table 목록은 바꾸지 않는다. 역사적 REAL affinity의 값을 읽을 때도 capture cell이 실제 저장 class/value를 보존한다. 이번 격리 installer의 migration source는 현재 checkpoint 4이며 모든 과거 schema에 직접 profile을 설치하는 기능은 없다.

## 10. TESTED — 독립 synthetic oracle과 실패 주입

환경: Python 3.12.3, SQLite 3.45.1, host Linux. 실제 migrated SQLite 임시 파일을 사용했다. 원래 행의 전체 dict를 capture old/new 순서로 재생한 결과와 실제 DB의 11개 table 전체를 비교했다. 예상 trigger 수나 exception 문구만 비교한 것이 아니다.

- 구현 전 3개 핵심 fence 테스트가 module 부재로 실패했다.
- 11×3 table/op 검증, 11개 무context 쓰기 거부, PK 이동, 두 민감 key의 양방향·같은 side 변경.
- 모든 실제 CASCADE/SET NULL action, 같은 행의 반복 쓰기·no-op·REPLACE·UPSERT, ABORT/FAIL/ROLLBACK/IGNORE/REPLACE conflict 정책.
- 고정 seed 6601의 200개 label 작업과 660102의 150개 mixed-table 작업·cascade·statement rollback을 전체 재생 비교.
- 미finalize COMMIT, nested RELEASE, savepoint rollback 뒤 재finalize, writer contention, failed COMMIT 후 안전한 finalize/rollback, native FK 위반 유지.
- 미완료/완료 후 rollback과 connection close, 별도 subprocess `os._exit(37)` 뒤 DB 재개 시 데이터·capture·R 불변.
- revision marker hole, payload cell hole, certificate INSERT와 context DELETE 사이 실패 주입. 실패 certificate 누출을 먼저 재현한 뒤 savepoint 원자성으로 수정.
- generated column과 tx_id 재사용도 failing test를 먼저 확인하고 차단했다.
- fresh/기존 4→격리 설치, 반복 설치, 설치 도중 admission 실패의 `iterdump()` 완전 불변, schema 손상 거부.
- 실제 cash/recurring/fixed/policy borrowed writer의 normal vs isolated 비교. 저장·export 시각과 난수 identity를 명시적으로 고정하고 Summary/payment/entries/panels·Snapshot v7·fingerprint를 비교했다. 실제 commit/reopen 비교도 포함한다.
- Snapshot raw 11개 교체를 capture한 뒤 actual legacy v7 validation/복구 및 readback 동등성. 정상 endpoint가 격리 profile을 거부하는 것도 확인했다.

## 11. 검증 명령과 결과

저장소 root에서 실행하며 backend 명령만 `cd backend` 기준이다. 전체 성공 로그는 `/tmp/money-note-d1-*.log`에 두고 요약만 확인했다. 임시 log/DB를 Git에 넣지 않는다.

```bash
# backend/에서
../.venv/bin/python -m pytest -q tests/test_isolated_sync_capture.py
../.venv/bin/python -m pytest -q tests/test_authoritative_state.py tests/test_versioned_migrations.py tests/test_snapshot.py
../.venv/bin/python -m pytest -q
../.venv/bin/python -m ruff check app tests isolated_sync

# root에서
.venv/bin/python -m pytest -q scripts/tests
.venv/bin/python -m ruff check scripts/local_deploy.py scripts/tests
npm --prefix frontend test
npm --prefix frontend run lint
npm --prefix frontend run build
bash -n scripts/dev-server.sh
bash -n scripts/deploy-server.sh
bash -n scripts/release-mobile.sh
git diff --check
```

| 검증 | 실제 결과 |
| --- | --- |
| 최종 D1 targeted | 113 passed; 기존 Starlette/httpx deprecation warning 1개 |
| authoritative-state / versioned migration / Snapshot targeted | 122 passed, 430 subtests passed; warning 1개 |
| 최종 전체 backend | 719 passed, 1,540 subtests passed; warning 1개 |
| 격리 deployment safety | 27 passed |
| Ruff app/tests/isolated_sync + scripts | PASS |
| frontend tests | 6 files / 21 tests PASS |
| frontend lint / production build | PASS |
| shell 3개 syntax / diff whitespace | PASS |
| ShellCheck | 미설치로 미실행 |
| Flutter/Android | mobile/runtime 변경이 없어 미실행; 기존 결과를 재실행했다고 주장하지 않음 |

## 12. 한계·D2 이후 prerequisite

1. 실제 SQLite 파일·transaction/process-crash 증거다. 갑작스러운 전원 손실·Android durable publication 검증은 아니다.
2. 운영 DB용 migration/epoch bootstrap/정상 transaction wrapper는 미구현·미활성이다. 기존 writer 전체를 정상 runtime에서 이 경로로 실행했다는 주장은 없다.
3. `sync_capture_commits`는 capture coverage만 인증하는 **격리 내부 기록**이다. root/index 완료를 의미하는 향후 `sync_commits`와 혼용할 수 없다.
4. D2는 epoch에 결합한 capture identity, exact coalescing, global UNIQUE/FK/reverse-reference closure, synchronous roots/index/aggregates, 금융 response 준비 뒤 pre-commit 완료를 추가해야 한다. root 없는 상태를 advertise해서는 안 된다.
5. restore/reset/Mobile Wins/startup/CLI와 앞서 설명한 FK gate adapter를 검증해야 한다. 모든 앱·operator writer의 future wrapper 전환을 확인하기 전에는 activate 불가다.
6. log retention/GC, large-restore staging, client segmented storage, protocol endpoint, scalability benchmark는 이번 구현 범위 밖이다. UUID·revision coverage는 이를 대신하지 않는다.
7. 현재 FULL backend suite는 정상 legacy 금융 동작을 보존하는 증거이고, 미래 D2 root/index 완전성의 증거가 아니다.

다음 gate는 실제 D1 구현의 별도 독립 감사다. 감사는 capture/fence/admission/격리 증거를 대상으로 하며 구체적인 새 모순 없이 T6.6B/C 전체 설계를 다시 시작할 필요는 없다. 이 문서는 운영 활성화나 D2 구현을 승인하지 않는다.

## 13. Production 안전성

production DB/API/credential/service에 접근하지 않았다. 기존 서버 runtime·금융 공식·인증·bundle v1·Snapshot v7·OfflineBaseline v4·pending/J·모바일 취득은 불변이다. 자체 생성 synthetic DB 외 migration은 적용하지 않았고 배포 dry-run, restart, APK 설치도 수행하지 않았다. 커밋/push는 배포 허가가 아니다.
