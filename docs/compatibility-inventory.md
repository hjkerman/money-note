# T5 호환성 inventory

이 표는 현재 source import, HTTP/serialized shape, Git 이력과 Snapshot 테스트를 대조한 것이다. 삭제 목록이 아니다. DB·Snapshot·재시도 identity가 포함된 항목은 내부 Python import보다 보수적으로 유지한다.

| Surface | 판정 | 실제 usage 근거와 범위 |
| --- | --- | --- |
| `backend/app/repository.py` facade | DEPRECATE | production `backend/app` import는 0. 테스트의 `test_cash_flows`, `test_panels`, `test_summary`, `test_entry_constraints`, `test_month`가 기존 경로를 사용한다. 새 production 코드는 `app.repositories.*`를 직접 import한다. 삭제는 별도 release 판단으로 보류한다. |
| `frontend/src/components/LedgerTables.tsx` re-export | KEEP | `CurrentMonthView`, `MonthlyPanelsView`, `StatsModal`의 실제 import 경로다. 이 경로를 지우면 현재 frontend build가 깨진다. |
| `backend/app/services/discounts.py` shim | UNKNOWN / DEFER | production 내부 import는 0, `test_card_charge`가 사용하며 호환 public Python 함수를 내보낸다. 외부 Python 소비자를 증명하거나 배제할 자료가 없어 삭제하지 않는다. 새 계산은 `card_charge/`에만 둔다. |
| `ledger_entries.amount_expr`, `aux_amount_expr`, `monthly_panels.amount_expr` | KEEP | DB 컬럼, API schema/types, 웹·모바일 요청, notification request fingerprint, 월마감 copy, Snapshot manifest/restore에 나타난다. 표시용 과거 필드라 하더라도 현재 serialized 입력·저장 형식에 남아 있다. |
| `card_payment_events.event_type='discount'` | KEEP | 현재 서버는 할당·할인 계산/취소·Summary에 읽고 쓰며 frontend API 타입에도 있다. 호환 event라는 이름만으로 dead라고 볼 수 없다. |
| Snapshot v4/v5/v6 | KEEP | `SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS`가 명시한다. v4 유동성 key, v5까지 없는 fixed 현금흐름 연결, v6의 연결은 있지만 없는 확인 월을 구분한다. v4~v6 카드 정기결제 생성 지출에는 명시적 source ID가 없어 취소 시 유일하게 증명되는 legacy 관계만 같은 transaction에서 해제한다. 실제 과거 exporter의 합성 fixture로 확인된 fixed·recurring의 restore→재시작→후속 취소/월마감→v7 재복원을 검증한다. |
| Snapshot v7 | KEEP | 현재 export 형식. DB의 `user_version`과 독립이며, 연결된 fixed 확인 월·cash flow 소유·날짜가 모순되거나 중복된 v7은 추측해 보정하지 않고 거부한다. |
| `discount_checked` legacy 열 | INTERNAL MIGRATION ONLY + Snapshot KEEP | 구 DB에서는 numbered migration이 제거를 시도하고, 구 Snapshot에서는 manifest 검증 후 정규화한다. 새로운 authoritative 할인 필드로 쓰지 않는다. |
| 구 유동성 설정·라벨 key | INTERNAL MIGRATION ONLY + Snapshot KEEP | `base_next_month_liquidity`, `liquidity_status` 등은 legacy DB admission 뒤 backfill 및 v4 restore에서만 읽는다. 런타임 API의 이름은 현재 key다. |
| `installments` table 제거 | INTERNAL MIGRATION ONLY | `cfd047f` 시대 startup의 `DROP TABLE`을 migration 1에 한 번 보존한다. 현재 도메인·Snapshot 대상에는 없다. 더 오래된 DB 구조는 지원을 추측하지 않고 fail closed한다. |
| 초기 auth/session schema 호환 | INTERNAL MIGRATION ONLY | 역사적 unversioned core의 `users`, `auth_sessions`, `share_sessions` 존재와 기본 컬럼을 검사한다. 새 DB에서 현재 테이블을 만든다. 세션 자체와 UNIQUE token 제약은 현재 런타임에 필요해 KEEP한다. |
| legacy notification registration fingerprint | KEEP | `entries.py`, `panels.py`가 저장된 구 지문을 비교하고 일치할 때만 현재 지문으로 승격한다. 영속 등록 key를 임의로 다시 쓰면 중복 금융 입력 위험이 있다. |
| legacy reconciliation record의 fingerprint 부재 | KEEP | `offline_reconciliation.py`가 POST 재실행을 거부하고 status 조회만 허용한다. 과거 committed result의 idempotency 경계다. |

`PROVEN DEAD`로 분류해 삭제한 compatibility path는 이번 T5에 없다. `UNKNOWN / DEFER`는 사용 증거가 모자란 경로이며, 존재만으로 현재 런타임 필수라고 판단한 것은 아니다.
