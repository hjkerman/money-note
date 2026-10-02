# T5 호환성 inventory

Exact monetary domain closure는 이전 signed-64-bit nominal 허용 범위를 `±(2^53−1)원`으로 명시적으로 축소한다. full-int64 외부 제품 호환 요구는 없으며 웹 Number/historical REAL/API/mobile의 공통 exact 정수 범위를 사용한다. v7 금액은 원문 JSON 및 정규화 전에 lossless 검증한다. fractional/non-finite/잘못된 문자열·범위 초과·NULL 금액 설정은 거부하며 v4~v6의 기존 REAL/소수 절삭 호환도 이 범위 안의 해당 버전에만 보존한다. 과거 잃은 정밀도를 추정하지 않는다. 일반 REAL의 fingerprint와 API/Offline journal body·reconciliation identity는 재작성하지 않는다.

confirmed recurring의 actual 연결은 nullable archive 발생일과 무관하다. current의 NULL 발생일 PATCH는 기존대로 거부한다. 실제 생성 지출이 없거나 유일하지 않으면 template 금액 fallback으로 감추지 않는다. 웹·모바일의 구 payload fallback surface는 삭제하지 않으며 current 서버 응답은 완전한 `confirmed_*` 실제 금액을 제공한다. schema/version/protocol 및 dead surface 제거는 없다.

batch에 소유된 일반 카드 원장도 NULL 원금은 유효하지 않다. current/archive 위치와 무관하게 PATCH·read·export·restore에서 검증하며, 관계 없는 과거 nullable 행 전체를 새로 제한하지 않는다.

영속 금융 관계 closure는 파일/API/DB surface를 제거하지 않는다. 카드 원장 key의 batch 소유는 유일하며 `(event, key)` 배분과 실제 출금 소유도 유일해야 한다. Historical unbatched 이벤트는 그대로 읽고 사후 batch를 추측하지 않는다. 명시적 recurring 생성 지출은 유효한 정수 원금(0 허용)을 필수로 갖고 current/archive 어느 위치든 source/epoch로 소유한다. old/current + active/archive는 정상, 같은 논리 row/epoch 중복은 손상이다. v4~v6 정규화와 REAL-affinity 정수 표현은 지원하며 NULL 원금을 추측 생성하지 않는다.

최종 blocker closure에서도 legacy monetary discount 입력(`discount_override`/`aux_amount_value`, 패널 `discount_amount`)은 KEEP이다. 공과금 기본값보다 explicit 의미가 우선하며 API/journal 필드를 삭제하거나 확장하지 않는다. 구 Snapshot의 증명 가능한 recurring 관계는 source ID와 확인 epoch로 결합하고 기존 v7 컬럼으로 보존한다. Explicit identity/epoch를 mutable 발생월로 재판정하지 않는다. Fixed timestamp는 offset hour/minute 범위도 검증한다. 모바일 ONLINE pending marker는 Snapshot과 별도인 로컬 복구 metadata다.

이 표는 현재 source import, HTTP/serialized shape, Git 이력과 Snapshot 테스트를 대조한 것이다. 삭제 목록이 아니다. DB·Snapshot·재시도 identity가 포함된 항목은 내부 Python import보다 보수적으로 유지한다.

재감사 closure는 Snapshot v4~v7/version 3을 유지한다. 원본 recurring epoch의 부분 누락은 거부하고, 기존 legacy normalization의 증명 가능한 absence는 그대로 지원한다. 확정 조회도 immutable source/epoch를 사용한다. Claim/Family의 accepted boolean-only false는 explicit exclusion이며 구 monetary 입력을 지우지 않는다. 로컬 manual retry v3는 기존 한 파일에 owner만 결합하고 구 v1/v2의 증거를 보존한다. owner 없는 artifact는 현재 login으로 추측해 재전송하지 않는다. API/DB surface retirement는 수행하지 않는다.

최종 recurring closure는 v4~v6의 증명 가능한 정규화 뒤에도 활성 원본 확인이 완전한 source/epoch로 생성 지출 정확히 한 건을 소유해야 함을 검사한다. 불명확한 legacy 활성 관계는 취소 시점까지 미루지 않고 restore 전에 거부한다. v7의 epoch 전체 누락 또는 생성 지출 누락은 손상이며, 과거 epoch 미보존 v7 fixture도 그대로 보존한 rejection 테스트다. 현재 exporter와 runtime 조회·수정·삭제·재확인도 같은 계약을 사용한다. 기존 파일 버전 지원은 손상된 모든 파일의 자동 복구를 뜻하지 않는다.

| Surface | 판정 | 실제 usage 근거와 범위 |
| --- | --- | --- |
| `backend/app/repository.py` facade | DEPRECATE | production `backend/app` import는 0. 테스트의 `test_cash_flows`, `test_panels`, `test_summary`, `test_entry_constraints`, `test_month`가 기존 경로를 사용한다. 새 production 코드는 `app.repositories.*`를 직접 import한다. 삭제는 별도 release 판단으로 보류한다. |
| `frontend/src/components/LedgerTables.tsx` re-export | KEEP | `CurrentMonthView`, `MonthlyPanelsView`, `StatsModal`의 실제 import 경로다. 이 경로를 지우면 현재 frontend build가 깨진다. |
| `backend/app/services/discounts.py` shim | UNKNOWN / DEFER | production 내부 import는 0, `test_card_charge`가 사용하며 호환 public Python 함수를 내보낸다. 외부 Python 소비자를 증명하거나 배제할 자료가 없어 삭제하지 않는다. 새 계산은 `card_charge/`에만 둔다. |
| `ledger_entries.amount_expr`, `aux_amount_expr`, `monthly_panels.amount_expr` | KEEP | DB 컬럼, API schema/types, 웹·모바일 요청, notification request fingerprint, 월마감 copy, Snapshot manifest/restore에 나타난다. 표시용 과거 필드라 하더라도 현재 serialized 입력·저장 형식에 남아 있다. |
| `card_payment_events.event_type='discount'` | KEEP | 현재 서버는 할당·할인 계산/취소·Summary에 읽고 쓰며 frontend API 타입에도 있다. 호환 event라는 이름만으로 dead라고 볼 수 없다. |
| Snapshot v4/v5/v6 | KEEP | `SUPPORTED_SNAPSHOT_SCHEMA_VERSIONS`가 명시한다. v4 유동성 key, v5까지 없는 fixed 현금흐름 연결, v6의 연결은 있지만 없는 확인 월을 구분한다. 카드 정기결제 source ID가 없으면 복원 시 변경되지 않은 확인 증거와 유일한 후보가 있을 때만 현행 source ID로 결합한다. 수정/삭제 후 mutable 필드 재매칭은 하지 않고, 불명확한 관계는 취소 전에 거부한다. 실제 과거 exporter의 합성 fixture로 fixed·recurring restore→재시작→수정/취소/월마감→v7 재복원을 검증한다. |
| Snapshot v7 | KEEP | 현재 export 형식. DB의 `user_version`과 독립이며, 연결된 fixed 확인 월·cash flow 소유·날짜가 모순되거나 중복된 v7은 추측해 보정하지 않고 거부한다. fixed `confirmed_at`은 지원 timestamp 형식과 실제 달력 날짜·시각을 검증한다. 명시적 recurring source는 legacy 추론에 다시 넣지 않는다. |
| `discount_checked` legacy 열 | INTERNAL MIGRATION ONLY + Snapshot KEEP | 구 DB에서는 numbered migration이 제거를 시도하고, 구 Snapshot에서는 manifest 검증 후 정규화한다. 새로운 authoritative 할인 필드로 쓰지 않는다. |
| 구 유동성 설정·라벨 key | INTERNAL MIGRATION ONLY + Snapshot KEEP | `base_next_month_liquidity`, `liquidity_status` 등은 legacy DB admission 뒤 backfill 및 v4 restore에서만 읽는다. 런타임 API의 이름은 현재 key다. |
| `installments` table 제거 | INTERNAL MIGRATION ONLY | `cfd047f` 시대 startup의 `DROP TABLE`을 migration 1에 한 번 보존한다. 현재 도메인·Snapshot 대상에는 없다. 더 오래된 DB 구조는 지원을 추측하지 않고 fail closed한다. |
| 초기 auth/session schema 호환 | INTERNAL MIGRATION ONLY | 역사적 unversioned core의 `users`, `auth_sessions`, `share_sessions` 존재와 기본 컬럼을 검사한다. 새 DB에서 현재 테이블을 만든다. 세션 자체와 UNIQUE token 제약은 현재 런타임에 필요해 KEEP한다. |
| legacy notification registration fingerprint | KEEP | `entries.py`, `panels.py`가 저장된 구 지문을 비교하고 일치할 때만 현재 지문으로 승격한다. 영속 등록 key를 임의로 다시 쓰면 중복 금융 입력 위험이 있다. |
| legacy reconciliation record의 fingerprint 부재 | KEEP | `offline_reconciliation.py`가 POST 재실행을 거부하고 status 조회만 허용한다. 과거 committed result의 idempotency 경계다. |

`PROVEN DEAD`로 분류해 삭제한 compatibility path는 이번 T5에 없다. `UNKNOWN / DEFER`는 사용 증거가 모자란 경로이며, 존재만으로 현재 런타임 필수라고 판단한 것은 아니다.
