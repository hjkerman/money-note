# 청구 기능 제거 가이드

`claim`은 사용자가 가족에게 돌려받을 금액을 관리하는 회수 예정 큐다. 제거 자체는 확정되어 있지만 시점은 정하지 않는다. 사용자가 일상 생활비뿐 아니라 예외적인 큰 지출까지 가족 지원 없이 자체 소득과 자산으로 감당할 수 있는 현실적 경제적 독립 상태가 되었을 때 제거한다. 그전까지는 정상적인 support/recovery 기능이다. 이 문서는 지금 기능을 제거하라는 지시가 아니라, 제거 당일 핵심 원장과 유동성을 건드리지 않고 작업하기 위한 경계 지도다.

## 현재 경계

- 저장: `monthly_panels.panel_type = 'claim'`. 전용 테이블이나 전용 외래키는 없다.
- 할인: 본인카드 정책을 재사용하지만 `DiscountCard.OWNER` 자체는 본인 원장에도 필요하므로 제거 대상이 아니다.
- API: 패널 CRUD/선택 삭제/일괄 처리, Summary의 `claim_original_total`·`claim_net_total`, `/api/share/claim`, `/share/claim`.
- 웹: 당월 `청구` 탭, 공유 링크, 선택/일괄 처리, 할인과 실청구액 수정, Summary 타입.
- 모바일: `정산` 화면의 청구 분기, 알림 후보의 `청구 사용` 경로, 회계감사 Markdown의 청구 절.
- Judgment: `judgment/claim.py`, claim 메시지 pool과 공유 subtitle·ledger note. 본인 앱의 소비·신용 압박 Judgment에는 Claim 금액을 넣지 않는다.
- 설정과 라벨: `panel_claim_title`. 별도의 claim 전용 민감 설정은 없다.
- Snapshot: `monthly_panels`의 claim 행과 `app_labels.panel_claim_title`이 일반 데이터로 포함된다.

Claim은 `ledger_entries`, 카드 결제 batch, 현금흐름, 잔여 유동성이나 본인 앱의 소비·신용 압박 Judgment에 직접 포함되지 않는다. `card_payments._clear_owner_discounts_for_month()`의 claim 할인 초기화와 공유 Judgment는 제거 시 함께 정리해야 하는 얕은 연결부다.

현재 단순 문자열 검색 기준 영향 범위는 60개 파일이다(백엔드 26, 웹 12, 모바일 8, 문서 14). 이 수에는 공용 패널·할인·문서 파일도 포함되므로 모두 삭제 대상이라는 뜻은 아니다. 제거 작업에서는 아래 경계별로 claim 분기만 걷어내고 `family_card`가 함께 쓰는 기반은 남긴다.

## 코드 위치 지도

- 백엔드 저장·API: `app/db.py`, `app/schemas.py`, `repositories/panels.py`, `routers/month.py`, `services/panels.py`, `services/presentation.py`
- 백엔드 공유: `routers/share.py`, `services/share.py`, `share_auth.py`. 공유 인증과 세션은 Family Card가 계속 사용한다.
- 백엔드 계산·판단: `services/summary.py`, `services/card_payments.py`, `services/card_charge/policies.py`, `services/judgment/claim.py`, `services/judgment/features.py`, claim 메시지 파일
- 백엔드 보조·테스트: `scripts/clean_panel_dates.py`와 panel/share/summary/presentation/judgment/snapshot 테스트
- 웹: `CurrentMonthView.tsx`, `PanelAppendForm.tsx`, `PanelTable.tsx`, `useAppDerivedState.ts`, `usePanelHandlers.ts`, 설정 handler, API/type/util/style와 관련 테스트
- 모바일: `family_screen.dart`, `notification_import_screen.dart`, `app_state.dart`, 모델, 회계감사 보고서·템플릿·테스트
- 데이터·문서: `monthly_panels`의 claim 행, `app_labels.panel_claim_title`, Snapshot manifest와 도메인/API/운영/보안 문서

## 제거 전 운영 준비

1. 남은 청구를 모두 처리하거나, 삭제해도 된다는 운영 확인을 받는다.
2. 제거 직전 서버 Snapshot과 SQLite 하드카피를 각각 한 벌 만든다.
3. 공유 링크가 더 필요하지 않은지 확인한다.
4. 제거 릴리스와 웹·모바일 배포를 같은 작업으로 묶는다. 구버전 클라이언트가 제거된 API를 계속 호출하게 두지 않는다.

## 권장 제거 순서

1. `monthly_panels`의 claim 행과 `panel_claim_title` 라벨을 삭제하는 일회성 정리를 추가한다.
2. `/share/claim`과 `/api/share/claim`, claim 전용 공유 HTML·최소결제·ledger note를 제거한다. 공유 PIN과 `share_sessions`는 가족카드 공유에 계속 필요하므로 유지한다.
3. 패널 API의 허용 타입과 완료 처리 타입에서 `claim`을 제거한다.
4. Summary의 `claim_original_total`, `claim_net_total`과 Pydantic·TypeScript·Dart 응답 필드를 함께 제거한다.
5. 공유 Judgment의 claim feature, public re-export와 메시지 파일을 제거한다. 호환 응답의 `claim_categories`도 웹과 함께 제거한다.
6. 웹의 청구 탭, form/handler/type/CSS 분기와 공유 버튼을 제거한다.
7. 모바일 정산 화면을 가족카드 전용으로 단순화하고 알림 후보의 `청구 사용` 라우팅을 제거한다.
8. 모바일 회계감사 Markdown과 안내 문구에서 청구 데이터 조회·출력을 제거한다.
9. 본인카드 월 혜택 변경 시 claim 할인 override를 초기화하는 SQL을 제거한다. 본인 원장 할인 정책은 유지한다.
10. 문서와 테스트에서 Claim 도메인을 제거하고 전체 빌드·복원 검증을 수행한다.

## Snapshot 전환 정책

Claim 제거 릴리스에서는 Snapshot schema version을 올리는 편이 안전하다. 제거 전 버전 Snapshot은 원문 manifest를 먼저 검증한 뒤, 정규화 단계에서 claim 행과 `panel_claim_title`을 명시적으로 폐기해야 한다. 조용히 DB에 되살리거나 알 수 없는 패널 타입으로 남겨서는 안 된다.

복원 응답이나 운영 로그에는 폐기한 claim 행 수를 확인할 수 있게 하는 것이 좋다. 제거 이후 생성된 Snapshot에는 claim 데이터와 claim 전용 필드가 없어야 한다.

## 불변 조건

Claim 제거 전후에 다음 값과 동작은 같아야 한다.

- `ledger_entries` 행, 사용금액, 할인과 카드대금
- 소비 통계와 지출 분류
- 현금흐름과 현금성 고정지출 확인 상태
- 동결과 잔여 유동성
- 카드 결제 batch와 월마감
- Family Card 데이터, 공유 페이지와 할인
- 본인카드·통행료카드·교통카드 정책
- Claim을 제외한 Snapshot·Pre-restore 복원

위 핵심 계산을 수정해야 제거가 가능하다면, 제거 전에 Claim 경계가 다시 오염된 것이다.

## 제거 당일 검증

- DB에 `panel_type='claim'` 행이 없고 재시작 후에도 생기지 않는다.
- `/share/claim`, `/api/share/claim`은 404이며 Family Card 공유는 정상이다.
- 웹·모바일에 청구 입력, 목록, 합계, 공유, 알림 후보 경로가 남아 있지 않다.
- Summary와 Judgment 응답·클라이언트 타입이 일치한다.
- 제거 전 Snapshot 복원 시 claim만 명시적으로 폐기되고 나머지 row count와 금액 합계가 보존된다.
- 새 Snapshot에는 claim 행·라벨·응답 필드가 없다.

## 현재 평가

완전 제거는 중간 규모의 조정 작업이지만 스키마 재구축이나 핵심 계산 개편은 필요 없다. 가장 큰 위험은 DB가 아니라 구버전 웹·모바일·Snapshot이 제거된 claim 표면을 다시 호출하거나 복원하는 것이다. 따라서 단일 릴리스에서 서버, 웹, 모바일, Snapshot migration을 함께 전환하면 제거 비용은 통제 가능하다.
