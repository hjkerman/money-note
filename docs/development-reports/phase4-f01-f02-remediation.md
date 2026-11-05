# Phase 4 F01/F02 한정 수정 — 독립 검증 대기

기준선: `phase2/mobile-network / dda412bac3430abc422ad8a2c35b533063251ae3`.
owner의 확정 MAJOR F01·MINOR F02만 수정했다. checkout에서 별도 Phase 4 Final Correctness Audit 보고서 파일을 찾지 못해 owner 요청의 결함 명세를 사용했다. 새 전역 감사는 수행하지 않았다. 두 finding은 **IMPLEMENTED / INDEPENDENT AUDIT PENDING**이며 CLOSED로 판정하지 않는다.

## F01 — 유효 수동 할인 상한

- 일반 POST/PATCH는 `routers/entries.py` → `repositories/entries.py`의 create/update를 사용한다. Offline reconciliation의 일반 생성도 create를 공유한다. PATCH는 기존 행과 입력을 합친 상태를 검증한다.
- `card_charge/evaluator.py`에 쓰기용 `validate_manual_discount`를 두고 일반 원장 검증 및 기존 전용 `set_entry_discount`에서 재사용한다. 계산 evaluator·Summary 공식·Snapshot 형식은 변경하지 않는다.
- 명시된 override의 aux 금액이 원금을 넘으면 거부한다. 생성의 `discount_override_amount`/할인 제외 intent 우선순위를 보존한다. PATCH에서는 명시적 aux override가 없을 때 legacy discount event allocation 합계도 검사한다. 할인 없는 legacy 행에는 추가 상한 제약을 적용하지 않는다.
- 생성/수정 rejection은 기존 transaction rollback을 사용한다. 일반 HTTP 테스트에서 audit/auth 로그를 제외한 전체 DB dump(원장·관계·등록·revision 포함)가 같음을 확인했다. HTTP 실패 요청의 기존 audit logging은 유지된다.
- 다른 지원 경로: planned append/confirm, late card entry, month close의 원장 복사, Snapshot restore는 별도 도메인 경로다. 이번 수정으로 재설계하지 않았다. 전용 할인 명령의 기존 음수/상한 계약은 유지한다.
- 새 회귀: POST/PATCH 초과, 원금 감소, 정상/0/동일 경계 할인, 동시 원금·할인 PATCH, archive, 초기 intent, legacy event 감소, rejection 원자성, per-entry net 합과 Summary card_total, 유효 Bundle/standalone Snapshot 검증.
- 기존 불법 저장 행은 **별도 읽기 안전 정책 결정 필요**: evaluator의 개별 순액 0 하한과 Summary의 전체 차감이 불일치할 수 있다. 과거 데이터 자동 clamp/수정/정리, startup/restore의 신규 정책은 구현하지 않았다. 실제 운영 데이터 존재 여부는 조사하지 않았다. 독립 감사 및 owner가 별도 정책을 결정해야 한다.

## F02 — 새 draft 보존

- `useEntryHandlers.ts`의 일반 지출 및 정기결제 제출은 제출 시 객체 identity를 기억한 함수형 state updater를 사용한다. 현재 draft가 같은 객체일 때만 초기화한다. React의 기존 immutable draft 갱신과 맞물리며, 값을 바꿨다가 되돌려도 새 객체는 보존한다.
- 각 폼에 별도 in-flight ref를 두어 mutation 및 후속 refresh가 끝나기 전 같은 폼 재제출을 막는다. 성공·실패 후 finally로 해제하며 자동 재전송은 추가하지 않는다.
- 요청 실패 시 setter가 실행되지 않는다. 서버 mutation 성공 후 refresh 실패의 기존 처리/완료 의미는 변경하지 않는다. CurrentMonthView의 기존 setter/폼 연결은 그대로 사용하며 파일 수정이 필요하지 않았다.
- 실제 hook을 server renderer로 실행하고 지연 Promise와 함수형 setter로 async 순서를 검증했다. expense/planned 각각 새 draft 보존·동시 제출 차단, 미수정 draft 초기화, 실패 보존·명시 재시도 총 6개다. 실제 브라우저 DOM·포커스 E2E를 실행한 결과는 아니다.

## 검증

- `.venv/bin/python -m pytest -q backend/tests/test_p4_discount_writes.py backend/tests/test_entry_constraints.py backend/tests/test_utility_discount.py backend/tests/test_authoritative_state.py backend/tests/test_response_coding.py backend/tests/test_snapshot.py`: **130 PASS / 115 subtests PASS**. 이후 할인 없는 legacy 행의 검사 조건을 좁히고 새 focused 파일 **4 PASS** 재확인.
- `cd frontend && npm test`: **27 PASS / 7 files** (새 6개 포함).
- `cd frontend && npm run lint`: PASS (ESLint 및 TypeScript noEmit).
- `cd frontend && npm run build`: PASS (TypeScript build 및 Vite).
- backend 기존 Starlette/httpx deprecation warning 1개는 유지. dependency 설치/업그레이드는 하지 않았다.
- 최종 task-only diff 및 `git diff --check` 확인. 기존 dirty/untracked 파일과 staged 내용은 포함하지 않는다. source 변경은 entries repository, card_charge evaluator, card_payments service, Web entry hook만이다. 관련 새 테스트 2개와 이 인계 문서만 추가했다.

초기 테스트에서 fixture의 필수 sort_order 누락 및 정상 audit log 추가까지 전체 DB 불변으로 비교해 실패했다. fixture와 비교 범위를 금융 transaction 대상으로 바로잡았으며 validation assertion을 제거하지 않았다. 공유 unittest fixture의 중복 수집도 모듈 import로 수정했다. 위 수치는 최종 수집 기준이다.

## 게시 및 인계

F01 첫 수정 commit: `74fe9d9` (`Reject excessive effective manual discounts on ledger writes`). F01 legacy 검사 범위 보완과 F02는 별도 commit이며 실제 SHA는 이 문서의 Git 이력과 최종 보고에서 확인한다. 개발 branch에만 게시한다. Production 접근·배포, main 병합, schema/Claim/Offline protocol 변경은 수행하지 않았다.

다음 작업은 **독립 F01/F02 한정 수정 감사**다. 기존 불법 행 읽기 정책의 후속 결정 필요성을 포함해 인계하며 이 구현 세션에서 독립 감사를 시작하지 않는다.
