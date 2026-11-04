# Money Note 최종 최적화·종료 로드맵

작성일: 2026-11-02. 완화 계획 갱신: 2026-11-03. **P1-01/P1-02 실험과 P1-03/P1-04/P1-R 조사를 완료했다. P1-01은 미채택·원복, P1-02는 보호 경로 보류, P1-03은 비용 귀속 B/전체 PARTIAL, P1-04는 C다. 1단계는 최종 독립 감사 PASS와 owner 승인으로 CLOSED이며 P1-R-01은 최초 미채택·원복 후 owner 한정 예외 승인과 활성132건 통과로 재채택, P1-S는 digest 비용 조건 실패로 보류, P1-U는 기존 보류, P1-05는 소유자 결정으로 제외했다. [공유 완화 장부](phase1-mitigation-plan.md)에 Planning Audit PASS·owner scoped 승인 뒤의 순차 실행을 기록했다. 최종 독립 Mitigation Audit는 PASS — MITIGATION ACCEPTED다. 2단계 조사·후보 감사 뒤 owner 승인으로 N01 한정 구현을 수행했다. 최종 독립 PASS와 owner 승인으로 N01 ACCEPTED(A01/R1 CLOSED)다. N02 조사는 DEFER·독립 Snapshot GET 유지 권고로 완료했다. 삭제·최종 감사는 미착수다.** 이 문서의 READY는 실행 가능한 계획이 준비됐다는 뜻이다. 단계 종료, formal T6.6F 완료 또는 운영 준비 판정이 아니다.

## 1. 현재 기준선과 보류 경계

개발 경로는 `/home/hjkerman/codex/money-note`다. 최초 계획의 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, 시작 인덱스 SHA-256은 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`였다. 2026-11-03 완화 계획의 실제 HEAD는 문서 정리 commit `2b4e168ebf1d8ba8ce5c9a48d7257a24bbd0c8a7`, 인덱스 SHA-256은 `8f97ab0d1f8935e32fa23c6b3fb4827aaf830f1536da3e847f7915fc20879a9c`다. HEAD와 working source는 동일하다고 가정하지 않는다. 기존 tracked 변경13개·untracked 자료와 staged0개를 보존하며 대상 source SHA는 공유 계획 A에 기록한다. 이번 계획에서는 commit·push하지 않는다.

현재 기능 경로는 [project-state](../project-state.md), 금융 의미는 [domain-model](../domain-model.md), 신뢰 경계는 [architecture](../architecture.md)의 소유다. 정상 Flutter 취득은 `CoherentRefreshCoordinator.acquire → GET /api/authoritative-state → strict admission → OfflineStore.replaceBaseline → 화면 설치`다. segmented 경로는 `*ForIsolatedUse` 진입점에 격리돼 있다. 새 일반 최적화 로드맵을 과거 T6.7/8 진입이나 legacy 제거 승인으로 해석하지 않는다.

| 보류 항목 | 현재 효력과 처리 |
| --- | --- |
| Galaxy S23 FE 실기기 시험 | 보류. 단말 접근·ADB 실행·에뮬레이터 운영 모두 이번 범위 밖 |
| F01·G1 | 기존 효력 유지. [G1 적용 기록](../real-device-gate-g1-n3-exact-normative-application.md)과 후속 상태 주석 유지 |
| G2 | [G2-N02](../real-device-gate-g2-n02-independent-exception-review.md)는 소유자 결정에 제출할 준비 판정이다. 예외 채택·규범 적용 미승인 |
| operational ADB dispatch | 차단 유지. Real-Device Gate 구현·계약 작성 재개 없음 |
| T6.9와 정량 의무 | 보류. 아래 8개 의무를 소거·대체·수용하지 않음 |
| formal T6.6F | [B11 재판정](../t66f-b11-post-amendment-closure-readjudication.md)에 따라 미승인·필수 증거 대기. Phase B 행정 종결은 `ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED`, 정량 판정은 `INCONCLUSIVE` |
| R1·운영 배포 | R1 activation CLOSED, production NOT AUTHORIZED 유지 |

이관 의무는 `T35-100K-NC`, `T35-100K-CARD`, `T35-100K-CASH`, `T35-ROWS`, `T35-NET`, `T35-GZIP`, `I25-E3-100K`, `I25-BOOKKEEPING-100K`이며 독립 수용은 **0/8**이다. 원 B03 source·다섯 N·정상 workload의 요구를 이번 UI 과제로 대체하지 않는다. 원 B03 계측 정확성은 **IR07 원 source에 대해 CLOSED**다. N100k instrumented full cold 성공은 미검증, 기존 재시도는 NO-GO다. [PRE05](../t69-pre05-independent-e3-bookkeeping-seam-review.md)는 외부 관측기의 정적 가능성만 인정하며 실행 자격·GO를 발급하지 않았다. Android durability·R1·whole-F 등 비이관 의무도 남는다.

서버 금융 authority, 필수 wire/구조/identity·Snapshot 복구·generation·durable publication·pending·Offline/reconciliation 계약을 유지한다. 금융 검사를 생략하거나 모바일에 서버 금융 알고리즘을 복제하지 않는다. 성능 작업 중 데이터 유실·오계산·보안 침해·잘못된 영속 동기화·중대한 기능 회귀가 실증되면 해당 작업을 중단하거나 허용 범위 안에서 즉시 수정한다. 그 밖의 의심은 §8의 한정 목록으로 넘긴다.

## 2. 실행 순서와 작업량 제한

**1단계 UI·앱 처리 성능 → 2단계 모바일 네트워크 데이터 사용량 → 3단계 dead code·중복 구현 정리 → 4단계 통합 최종 감사·한정 수정·종료** 순서를 고정한다. Snapshot 확장성은 개발 종료 후 별도 과제로 다루며, 이번에는 착수하지 않는다.

| 단계 | 실행 범위 | 자동 확대 방지 |
| --- | --- | --- |
| 1단계 | 이 성능 지도와 과거 근거·공유 완화 계획으로 승인된 국소 과제만 측정·구현 | 아래 P1 작업표로 범위 한정. R-01/S는 계획 감사·owner 승인과 각 조건 이후 구현, U 보류·P1-05 제외. 모든 병목 제거를 종료 조건으로 삼지 않음 |
| 2단계 | 1단계 종료 승인 뒤 모바일 다운로드·업로드 전송량 조사·최적화 | N01 ACCEPTED·N02 DEFER. 전체 Phase2 CLOSED 선언은 기록에 없으며 다른 후보는 미구현 |
| 3단계 | 2단계 종료 확인 뒤 §7의 좁은 정리 목록 검증·삭제 | 파일 수·크기만으로 분할/삭제하지 않음. 호환 경로와 역사 증거는 정리 대상에서 제외 |
| 4단계 | 3단계 종료 확인 뒤 §8의 단일 감사표를 한 번 수행하고 필요한 수정 | 수정별 집중 회귀, 관련 영향만 재검토. 사소한 수정마다 전면 감사를 반복하지 않음 |

이 문서 자체는 구현 승인이 아니다. 각 단계의 결과·남은 항목을 이 문서에 갱신하고 §9의 종료 조건을 확인한 다음 다음 단계에 진입한다. 새 계약 초안·반복 승인 문서 묶음을 만들지 않는다. 별도 권한이 필요한 소스 잠금·운영·기기 경계는 유지한다.

### 2.1 소유자 갱신 한정 실험 계획

기존 “추가 후보 최대1회” 제한은 다음 표로 대체한다. 무제한 최적화 캠페인 승인이 아니다. P1-03/P1-04 비용 조사와 P1-R 조사를 재개하지 않으며 후속 구현의 단일 장부는 [공유 완화 계획](phase1-mitigation-plan.md)이다. P1-05는 웹 성능이 만족스럽다는 소유자 결정으로 제외했다.

| 작업 | 범위 | 상태 |
| --- | --- | --- |
| P1-01 | 당월 지출 widget 지연 생성 | COMPLETE — NOT ADOPTED |
| P1-02 | Flutter rebuild·반복 파생값 계산 | COMPLETE — DEFERRED |
| P1-03 | Snapshot save/list/validation 비용 귀속 | 분석 완료 B / 전체 PARTIAL — 자동 ADB 기동 위반·종료 기록 보존 |
| P1-04 | backend SQL/query/presenter 비용 귀속 | COMPLETE — C, 구현0개 |
| P1-05 | 웹 Refresh·archive 취득 비용 귀속 | SKIPPED BY OWNER DECISION |
| P1-R | 불필요한 모바일 Refresh·반복 authoritative bundle 취득 | 원래110.37% 실패·미채택 보존 / 거부 검토 A·owner1회 예외 후 동일 B 재복원·활성132 PASS·ADOPTED |
| P1-S | Snapshot save/list 내부 반복 검증 최적화 | DEFER — 240 CPU표본에서 추가SHA 비용 조건 실패, 생산 미구현 |
| P1-U | P1-02 UI 파생값·rebuild 구현 후보 | DEFER — 현재 이득 대비 protected invalidation 변경 위험으로 구현 제외 |

### 2.2 P1-R — 조사 B 보존, R-01 owner 예외 재채택

[결과 보고서](p1-r-mobile-refresh-performance-results.md)의 판정은 **B — SOURCE-SUPPORTED REDUNDANCY, MEASUREMENT LIMITED**다. 정상 경로의14→1 HTTP·strict admission·JSON baseline/pending 경계는 유지되며, 일반 coordinator는 in-flight Future를 공유하지 않는다. foreground·connectivity·mutation single-flight의 기존 가드는 따로 보존한다.

유일한 첫 후보 **P1-R-01**은 하단 메뉴의 비인접 탭 선택을 직접 jump로 처리해 animateToPage의 중간 onPageChanged refresh를 없애는 UI 실험이다. 최종 목적지 refresh·인접 animation·수동 swipe는 유지한다. 0→4에서 source상 최대3개 중간 진입/조건부 GET 기회가 있으나 실제 발생률·절감 시간은 미측정이다. 새 Flutter/Android/ADB 실행은 하지 않았고 AppState/coordinator/OfflineStore 변경·TTL·세대 간 cache·검증 생략을 제안하지 않는다. HomeShell 한 곳의 animation UX 변경을 포함한 별도 승인 뒤 기존 widget fixture의 실제 중복 baseline부터 확인한다. 중복이 없으면 구현을 보류한다.

일반 탭 refresh 전면 생략과 일반 in-flight 공유는 freshness·auth/generation·mutation 완료 의미를 바꾸므로 이 후보와 구분한다. 명시 refresh·post-mutation·reconciliation/recovery·JSON durable publication·server authority와 날짜/인증 전환은 그대로 유지한다. P1-02의5k jump1→2→0 약5.55초 전체를 낭비로 계산하지 않는다. Phase2 전송량·압축·프로토콜 조사는 미착수다.

현재 주요 조사는 P1-R로 마무리했다. 후속 P1-R-01은 실제 중간 callback/HTTP baseline을 먼저 확인하는 조건부 계획이며, [공유 계획 C](phase1-mitigation-plan.md#c-구현-명세)에 승인 범위·측정·회귀·거부 기준을 둔다. R-01 최초 실험은 미채택·원복됐고, 이후 독립 거부 검토 A·owner 한정 예외로 동일 B를 재복원해 활성132건 통과 후 채택했다. 해당 최종 독립 감사는 PASS — MITIGATION ACCEPTED로 수용됐고 Phase1은 CLOSED다. 현재 다음은 N01 독립 변경 감사다. P1-05는 소유자 결정으로 제외했으며 필수 선행 조사로 추가하지 않는다. 1단계 종료는 별도 exit 확인이며 자동 선언하지 않는다.

### 2.3 P1-S — Snapshot 반복 검증 최적화 목표 보존

[P1-03 결과](../p1-03-snapshot-save-validation-performance-results.md)의 비용 귀속은 B지만 전체 판정은 **PARTIAL — 자동 ADB 기동 경계 위반 후 종료**다. 이를 PASS로 바꾸지 않는다. 현재 보호된 LocalSnapshotRepository에서 보관 파일을 save의 prune용 list와 반환용 list가 각각 읽고 decode·검증한다. v7 합성10k행·파일5,934,477B·기존30개에서 save는62회 read/decode/검증·367,937,574B 읽기·중앙값7.866초였고, 뒤의 공개 list까지는92회·중앙값11.566초였다. host JIT·구성별 n3(p95=최댓값), 계측 overhead·실기기 미측정 한계를 유지한다.

유일한 당시 후보는 같은 save 안에서 검증 완료한 prune 생존 결과를 반환에 재사용하는 것이다. 완화 계획은 이를 더 좁혀 **마지막 열거·전체 read·fresh stat을 유지하고, 작업 로컬 content receipt와 내용이 같은 파일의 decode/envelope 결과만 재사용**하는 조건부 안으로 구체화했다. 새 pending readback·byte 동일성·flush/rename·retention30, 공개 list/safeFile과 동시 변경 관측은 보존한다. 정확한 수명·miss fallback·최대31개 receipt·비용/채택 기준은 공유 계획 C에 있다. digest 비용이 이득을 지우거나 안전성/보호 소스·검사 변경 승인이 충족되지 않으면 미채택/보류한다. 생산 최적화는0개다. P1-S는 현 저장 동작의 반복 비용이며 **개발 종료 후 대형 Snapshot 확장성 architecture 과제와 별개**다. 후속 CPU 조건 측정에서 digest 비용이 더 커 보류했으며 구현0개다. 전체 save 전후 비교는 수행하지 않았다.

P1-03 자동 진단의 ADB 서버 기동과 작업 소유 PID 종료 사실은 원 보고서/근거에 보존한다. 이번에는 Flutter·Android·ADB 도구나 기기 탐색을 실행하지 않으며 Real-Device Gate 조사도 재개하지 않는다.

### 2.4 완화 구현·감사 단일 장부

[phase1-mitigation-plan.md](phase1-mitigation-plan.md)에 후보3개의 결정, 두 조건부 명세, 구현 로그와 감사 지적/수정란을 통합했다. P1-U는 같은 build 안 중복이 없고 5k 약2.27~2.49ms 재평가를 없애려면 public mutable entries·authoritative/Offline/세대 게시의 invalidation을 정비해야 하므로 현재 구현에서 보류한다. C1은 알려진 비용만으로 안전한 국소 변경이 입증되지 않아 추가 mitigation으로 선정하지 않았다. P1-01·P1-04는 재개하지 않는다.

순서는 **독립 Planning Audit → owner의 task·보호 소스 scoped 승인 → R-01 baseline/처분 → S 비용 조건·전후 검증/처분 → 실제 변경분 Mitigation Audit**다. 같은 Implementation/Audit Session을 번갈아 사용하고 owner가 장부를 전달한다. 자동 구현이나 4단계 전면 감사의 선행 착수는 없다. 보류/미채택도 완료된 처분이며 모든 비용 제거를 요구하지 않는다.

## 3. 1단계 성능 경로 지도

분석 단위는 **UI 경로 15개, 처리 경로 12개**다. 아래 지도는 최초 정적 호출 경로와 기존 측정의 대조 기록이며 전체 앱 runtime profile이 아니다. P1-01의 별도 host 실측은 §6에 연결한다. 아래 파일명은 특별한 표시가 없으면 `mobile/lib/src/` 기준이다. `M`은 Flutter main isolate, `I/O`는 await하는 파일·HTTP 작업이다. await 이후 동기 JSON·정렬·hash·FFI 작업이 자동으로 background isolate로 이동하지 않는다. 관련 경로에 명시적 `Isolate.run`/`compute` 전환은 확인되지 않았다.

### 3.1 UI·상호작용 15개

| ID·실제 진입점 | 핵심 파일·순차/비동기 의존성과 데이터 접근 | 반복 비용·계측·측정 한계 |
| --- | --- | --- |
| U01 cold startup | `main.dart → app.dart:initState → AppState.bootstrap`: 알림 권한 → secure session → Offline workspace 복원 → health → me → refresh → launch Snapshot 저장 → launch target → bootstrap 해제 | HTTP/I/O는 await, 복원 파싱·bundle admission은 M. 정상 인증 startup에는 bundle 외 health/me/Snapshot 요청도 있음. 첫 Flutter frame과 사용 가능한 첫 화면을 구분해야 하며 launch 실측 없음 |
| U02 foreground 복귀 | `app.dart:didChangeAppLifecycleState → resumeFromBackground`: refresh 또는 connectivity recovery → 별도 launch Snapshot → launch target. foreground 중복 진입 가드 있음 | 정상 refresh와 자동 백업이 직렬. 알림 channel과 파일 검증도 경유. 복귀 frame·단말 I/O 미측정 |
| U03 탭·push navigation | `screens/home_shell.dart`: 5개 PageView, `_handlePageChanged → refresh*Area`; 설정 탭은 `refresh`. 관리·알림은 MaterialPageRoute push | 240ms는 코드의 animation 설정이지 측정 latency가 아님. 탭별 refresh도 전체 bundle과 baseline 저장을 수행. 탭 연타 시 시작 요청 수·폐기 요청 비용 미측정 |
| U04 홈·최근 내역 | `screens/input_screen.dart:HomeScreen.build → state.expenseEntries.take(10)`; 서버 Summary/Judgment 표시 | 10건 표시 전 전체 current expense 필터·정렬. 화면 build는 M, 자체 DB/HTTP 없음. root 알림에 따른 재호출 수 미측정 |
| U05 당월 목록 취득·대량 스크롤 | `screens/month_entries_screen.dart:build → expenseEntries → ListView(children: ...rows.map)`; pull refresh는 U03 경로 | 전체 행의 `_MonthEntryCard` 위젯 객체를 build마다 선생성. ListView는 element build/layout을 지연하므로 모든 행이 즉시 layout된다고 주장하지 않음. 행 수별 생성 비용·스크롤 frame 미측정 |
| U06 필터·검색·정렬 | 모바일: expense/planned kind, 정산 claim/family 전환, 알림 출처, AI 자료 월 선택. `AppState` getters, `family_screen.dart`, 알림 화면, `ai_audit_sheet.dart` | 기존 목록에 대한 M의 where/toList/sort. 모바일 자유문자 거래 검색이나 독립 archive 검색 화면은 확인되지 않아 가상 경로를 추가하지 않음. 웹 월별 필터는 U14 |
| U07 거래 상세·수정 | 별도 거래 상세 route 대신 `_MonthEntryCard`의 분류 dropdown·할인 버튼·실결제액 dialog·삭제 확인. `AppState.updateExpenseCategory/updateEntryNetAmount/deleteExpense` | 표시값은 서버 projection. 수정 HTTP → fresh bundle → durable baseline → 완료. dialog 파싱 자체와 서버 완료 지연 구분. 관련 실패 경계 기존 검사 재사용, 화면 시간 미측정 |
| U08 입력 검증·저장 | `ExpenseInputCard._submit`, `CashFlowScreen._submit`, `FamilyScreen._submit → AppState._run/_financialWrite → create* → refresh*Area` | 로컬 문자열/금액 입력 검사·single-flight·draft 비교 → durable pending → HTTP → committed marker → bundle/baseline → unlock. 정상 단순 저장은 mutation+bundle 2회이며 보조 요청 별도. `submit_latency_diagnostic_test.dart`는 host 계측 수단, 현 시점 값 없음 |
| U09 정산 큐 | `screens/family_screen.dart:panelsByType → ListView`, claim/family 전환·일괄 완료·실결제 dialog·공유 | 선택 큐 필터·정렬·위젯 선생성. 해당 큐 전체가 도메인상 유효하며 월 기준 잘라내기를 최적화로 제안하지 않음. backend action 뒤 rebuild, 큐 규모별 미측정 |
| U10 고정·정기·월마감 | `management_screen.dart`와 part인 `management_panel.dart`, `management_planned.dart`, `management_month_close.dart`; preview/confirm/cancel/close → AppState | 관리 목록 변환 + 일부 preview 요청 + mutation/rebuild. eligibility와 기준월은 서버. 월마감·recovery backup transaction을 쪼개지 않음. UI/backup별 소요 미측정 |
| U11 알림 후보·원문 | `NotificationImportScreen._load`의 Future.wait → bridge 후보/두 출처 로그; `_CandidateList` 정렬·grouping·전체 카드 생성. archive 화면은 출처 탭·FutureBuilder | 네이티브 JSON 읽기/전달 뒤 Dart decode·필터. 후보별 과거월 할인 조회는 기존 캐시 사용. 등록 후 후보 삭제·재조회도 별도 측정 필요. host fake는 실제 Android channel 지연을 증명하지 못함 |
| U12 설정·Snapshot·공유·APK | `status_screen.dart`, `snapshot_manager_screen.dart`, `management_settings.dart`, `ai_audit_sheet.dart`; Snapshot list/read/share/restore, `AiAuditReportData.load`, APK controller | Snapshot 파일 검증·AI 자료 다중 조회/Markdown 생성·다운로드 진행 알림. 일반 금융 refresh와 별개. restore는 서버 검증/명시 확인 유지. plugin·설치·네이티브 공유 시간 미측정 |
| U13 웹 최초 조회·전환 | `frontend/src/App.tsx`, `useAppRefresh.ts`, `useLedgerSnapshot.ts`: month status 1회 뒤 Promise.all 13개 | 현재 웹은 14 GET이며 모바일 bundle 1 GET과 다름. 전체 archive 취득 포함. React render는 브라우저 main thread. 요청 trace·commit 시간 없음 |
| U14 웹 월별 기록·통계·대량 표 | `useAppDerivedState.ts`: current/archive 합침 → 선택 월 filter/sort → stats; `components/ledger/EntryTable.tsx` 등 map 렌더 | useMemo 존재. 입력이 바뀌면 전역 목록 재처리·표 DOM 생성. 자유 검색이 있다고 가정하지 않음. 브라우저 Profiler·heap·layout 측정 없음 |
| U15 웹 카드 결제·금융 저장 | `useCardPaymentHandlers.ts`, `PendingPaymentStore.ts`, API wrappers → 서버 command → `useAppRefresh` | durable retry 입력과 identity → command → 14 GET rebuild. 저장 응답과 화면 완료를 분리. 기존 응답 유실 회귀는 보존하며 추가 round-trip 제거 효과는 미측정 |

### 3.2 처리 경로 12개

| ID·경계 | 실제 함수·DB/네트워크·실행 위치 | 비용 요인·기존 계측·한계 |
| --- | --- | --- |
| A01 HTTP·인증·취득 | `api_client.dart:_request/authoritativeStateBytes`, `coherent_refresh_coordinator.dart:_acquireBundle`; HTTP await → authority 검사 → decode | 기본 1 bundle, 일반 mutation 별도 1회. health/auth/backup·명시 legacy oracle은 따로 센다. 요청 중복은 ticket으로 설치가 거부돼도 이미 쓴 비용이 사라지지 않음 |
| A02 strict decode·검증 | `authoritative_bundle.dart:decode`, `authoritative_bundle_validation.dart`, `authoritative_snapshot_validation.dart`: UTF-8 → raw money → JSON → Unicode/type/money → Snapshot/관계 | 모두 호출 isolate의 동기 CPU. `BundleStageObserver`가 단계 시간을 제공. raw-token과 decode 이후 검사는 보증이 달라 단순 중복으로 제거 불가. 과거 M1, 현재 latency 없음 |
| A03 freeze·모델 변환 | `AuthoritativeBundle._fromDecoded/_freeze/toCoherentBundle`, `models.dart`, `offline/offline_data.dart:OfflineBaseline` | map/list의 immutable 복사와 typed rows 생성, 저장 시 재직렬화. baseline constructor만 빠르다고 전체 decode가 빠른 것은 아님. 할당량·GC 최신 측정 없음 |
| A04 정상 로컬 baseline | `AppState._refreshAuthoritativeState → _withLineageLock → OfflineStore.replaceBaseline/_writeJsonAtomic` | **일반 baseline은 SQLite가 아닌 JSON 파일**. M에서 money 검사·toJson/encode, I/O flush/read, M jsonDecode, 마지막 동기 authority 검사→rename. lock 대기·I/O·CPU를 분리해야 함. readback/guard 생략 금지 |
| A05 자동·수동 Snapshot 저장 | `saveLaunchSnapshot → downloadSnapshot → LocalSnapshotRepository.save → _validateSnapshotFile → _prune/list` | 새 파일 readback 외 `_prune`의 list와 반환 list가 기존 보관 파일을 다시 읽고 JSON 검사. listSync도 호출 isolate에서 실행. 최대 30개 보관이지만 데이터 크기에 비례. 파일 metadata만으로 안전성을 대체하지 않음 |
| A06 상태 파생·전체 rebuild | `app.dart:AnimatedBuilder`, `HomeShell.build`, `AppState.expenseEntries/plannedEntries/panelsByType`, cash 화면 정렬 | notifyListeners가 앱 root builder를 다시 실행. 이것이 전 화면 layout 실행과 동의어는 아님. filter/sort·위젯 할당의 반복 여부는 build 계수와 프로파일로 확인. cross-generation cache는 미제안 |
| A07 알림 channel·로컬 캐시 | `notification_bridge.dart`, `MainActivity.kt:configureFlutterEngine`, `NotificationCandidateStore`; MethodChannel → native store → JSON → Dart models | 별도 background TaskQueue를 지정하지 않은 handler에서 저장소 함수를 직접 호출. 실제 Android 시간은 미측정. 과거월 policy cache는 이미 `AppState`에 있으며 새 중복 cache를 선제 추가하지 않음 |
| A08 Offline append·예상 view | `OfflineStore.appendOperation`의 직렬 tail·검증·flush, `OfflineProjection.from(B,J)`, `AppState._appendOfflineOperation` | input-only journal의 재검사/투영은 M, 파일은 await. J 증가에 따른 전체 순회·materialization 가능성. 현재 계측 없이 제곱 비용이나 결함으로 단정하지 않음. canonical 금융 engine으로 확장 금지 |
| A09 조정·재시작 복구 | AppState reconciliation prepare/submit/finalize → `backend/app/services/offline_reconciliation.py:apply_mobile_wins` | recovery·사용자 선택·한 서버 IMMEDIATE transaction의 B 복원/ordered J/receipt → fresh bundle/baseline → cleanup. 일반 sync의 임의 merge와 다름. 복구 확인을 지연 은폐로 UI 성공 처리할 수 없음 |
| A10 backend bundle·SQLite 읽기 | `routers/authoritative_state.py → services/authoritative_state.py:_construct/_prepare/_terminal_guard`; sync handler의 서버 worker, 하나의 financial read view 후 새 terminal view | 전체 Snapshot export/검증·typed projections·JSON 준비를 수행. `entries.py`/`panels.py`/`cash_flows.py`의 fetchall·정렬·presenter와 여러 validator가 경유. SQLite index는 section/order, date, month/type/order, cash date/order/id 등 이미 있음. 실제 EXPLAIN/visited rows·CPU attribution 없이 index 누락을 확정하지 않음 |
| A11 write transaction·공유 계산 | `db.py:session/borrowed_or_new_session`, 금융 router prepared response, `summary.py`, `financial_relationships.py:card_ownership_read_view` | response bytes까지 commit 전 준비, 같은 연결을 재사용. ownership PASS는 read-only 동일 transaction 범위에서만 재사용. Python exact 정수 계산·Snapshot 검증·auth를 한 전역 PASS cache로 합치지 않음. lock wait·SQL plan·presenter 비용 최신 측정 없음 |
| A12 격리 segmented 취득·SQLite | `AppState.publishSegmentedForIsolatedUse → segmented/fetch.dart → store.dart/store_publication.dart/store_read.dart`, `backend/isolated_sync/{observation,transfer,retention}.py` | packet 순차 취득·C1/object decode/hash·동기 SQLite FFI·batch transaction·E3 verify/prepare/commit/readback·E4 read. body/cache/staging/accepted/frozen 역할 분리. B03 logical counters·SQL observer는 지원 source/runtime에 한정. M2/M3의 역사 범위이며 일반 앱 UI 완료가 아님 |

## 4. 과거 성능 근거의 재검증

**검증한 최적화 계열은 3개(O1–O3)**다. 성과가 없거나 혼재한 후속 결과도 포함하며, 채택 또는 최신 HEAD의 성능 향상을 뜻하지 않는다. 측정된 비용 묶음은 **3개(M1–M3), 이번 현재 소스 신규 timing은 0개**다. 아래의 포함 시간은 서로 합산하지 않는다.

| 자료·분류 | 소스·환경·workload·방법 | baseline → 후보 / 관측 | 통계 한계·현재 적용성 |
| --- | --- | --- | --- |
| O1 T6.5B-3 bundle | [구현 기록 §Y](../t65/implementation/t65b3-implementation.md). 시작 `68aae70c…`, 보존 before/구현 after. Linux x86_64, Flutter 3.47.4 test JIT, Python 3.12.3/SQLite 3.45.1, 합성 bridge. 초기 ledger 376/1k/5k/10k, paired 입력으로 증가. warmup 2+표본 5, 교대 실행 | 정상 refresh HTTP 14→1, mutation+rebuild 15→2. 376행 refresh median 517.269→205.689ms, 10k 4547.149→3913.511ms. HTTP부터 durable baseline/pending 완료까지의 host operation | 작은 표본 p95=max, 다른 검사와 자원 공유. 요청 구조는 현재 source에서 재확인. 현재 startup 전체 시간·단말 시간·현재 수치로 재사용 불가. project-state의 과거 독립 감사 대기 표기를 새 판정으로 덮지 않음 |
| M1 T6.6A bundle 처리 비용 — MEASURED BOTTLENECK(과거 한정) | [보고서](../t66/a/t66a-payload-attribution.md), [client-summary](../benchmarks/t66a/client-summary.json), [원 표본](../benchmarks/t66a/samples.csv). 시작 `597a936d…`; i7-8750H/Linux, 위 Python/Flutter, warmup 3+표본 20. 10k ledger/current105/archive9895, 실제 frozen bundle 5,684,312B | 비교 최적화 없음. 10k parser+typed median 1970.082ms, raw money 538.2255ms, Snapshot/관계 985.407ms, baseline publish 269.733ms. 별도 readback 포함 diagnostic pipeline 2514.715ms | micro/로컬 pipeline이며 네트워크·UI 전체 sync가 아님. p95 nearest-rank, host JIT·thermal 미고정. 현재 parser/validator/OfflineStore의 SHA가 당시와 달라 숫자 전용 불가. backend authoritative service·LocalSnapshotRepository는 당시 source와 동일하나 runtime 성능 동등성은 미입증 |
| O2·M2 B05 `_lookup` hot decode — MEASURED BOTTLENECK(과거 한정) | [B05](../t66f-b05-lookup-hot-body-decode-optimization.md), [microbenchmark](../benchmarks/t66f-b05/microbenchmark.json). 원 B03 payload `8bd69836…`/engine `7ad114bc…` 대비 B05 payload `d0d9b35c…`/engine `f84dacdf…`. Python 3.12.3, SQLite 3.45.1, N1k/hot87,364B, 같은 DB warm 2순서 block·variant당 20호출 | hot constructor 포함 decode 4→3/lookup. OFF median 50.091808→42.538985ms, ON 50.918436→43.002099ms | 독립 반복 20개가 아님. 전체 cold가 아닌 함수 개선. 현재 observation.py SHA가 B05와 동일함을 archive 대조했지만 현재 통합 성능은 미측정. 정식 채택 상태는 여전히 실험 후보 |
| O2 후속 B05-A/B | [A 비교](../benchmarks/t66f-b05a/timing-comparison.json), [B 독립 재현](../t66f-b05b-independent-5k-on-ab-replication.md). B05-A payload `29bef953…`; 같은 새 exact-admission client, Flutter 3.47.4/Dart 3.13.3/client SQLite 3.53.4, loopback TLS, 준비 backend view+빈 client. H=current105+기타35, D=null | publication+bounded E4: N1k 조건당2회 OFF 31.4592015→29.6487245s, ON 33.2712705→31.5584355s. N5k 1회씩 OFF 152.966598→142.070529s, ON 152.688187→153.265907s. 역순 독립 ON 149.743978→155.002541s | N5k ON은 양 순서 모두 전체 이득 미관찰. 표본·JIT/cache/순서 영향, 통계적 유의성 없음. UI/Offline-ready 완료가 아님. 국소 decode 절감을 전체 sync 개선으로 표현하지 않음 |
| M3 B07 연결·schema 귀속 — MEASURED BOTTLENECK(과거 한정) | [B07](../t66f-b07-bounded-connect-schema-attribution.md), [packet 원자료](../benchmarks/t66f-b07/packet-timings.json). 원 B03, CPython3.12.3/SQLite3.45.1, N1k 동일 H, B03 ON·실제 ASGI, 30요청 중 상세 객체 probe14개 | handler 합3.458826s 안에 connect1.193978169s, 그 안의 기대 revision 계약 파싱0.278446196s. 요청당 fresh connect3회. 개선 비교는 없음 | socket/TLS/client 없음. timer wrapper 교란, 한 캠페인. schema 전체를 불필요 작업으로 분류할 근거가 아님. 현재 shared validator의 반복 구조는 있으나 live engine은 원 B03와 다름 |
| O3 B08 기대 계약 재사용 | [B08](../t66f-b08-expected-revision-contract-reuse.md), [비교](../benchmarks/t66f-b08/packet-comparison.json). 원 B03 대비 B08 payload `a857d22d…`/engine `5861d6d2…`; N1k, ASGI/B03 ON, source당 process1·AB/BA, 객체13개씩 | handler 합3.180023143→2.841368689s. compiler46→1, actual DB inspection46→46. 기대 parser 호출1518→33 | 국소 handler 10.6494% 감소 관측. 계측 비용 일부도 사라지며 신뢰구간 없음. 실제 Flutter cold 이득 미검증. 현재 db_migrations.py는 B08이 아닌 원 SHA `24c14452…`로 cache 미적용 |
| O3 후속 B09 | [B09](../t66f-b09-engine-admission-real-flutter-cold-ab.md), [raw 연결 비교](../benchmarks/t66f-b09/cold-ab-results.json). 통합 payload `beb2fe5e…`, 원/B08 backend만 비교하고 B05 변경 배제. 위 Python/Flutter/native SQLite, N1k/4,132객체, 조건당1회 A OFF→B OFF→B ON→A ON | publication+bounded E4 OFF35.230866→29.140462s, ON31.300743→33.435903s. compiler248→1, 실제 inspection248 유지. 입장·실제 경로 자격 PASS, 성능 MIXED | N5k 미실행. 한 Flutter process의 순서·JIT/cache 영향. 기본 엔진 채택 없음. live의 B05 변경과 합친 결과로 취급하지 않음 |

이번 근거 확인은 B03/B05/B08 archive SHA와 선택 source bytes 대조, B07 packet 합·B08 handler/count 재집계, B09 raw 두 비교 쌍의 완료 시간 대조, T6.6A CSV 중앙값 대조다. 전체 과거 감사나 모든 실험의 독립 재현을 다시 수행하지 않았다. source payload·engine·archive SHA를 서로 바꾸어 쓰지 않는다. 정확한 식별자와 확인 범위는 [단일 보조 근거](../benchmarks/final-optimization-and-closure-evidence.json)에 기록한다.

## 5. 우선순위 backlog

**계획 시점의 미측정 후보 8개(C1–C8)**다. C3의 P1-01 실측·미채택과 C5의 P1-02 실측·보호 경로 보류 결과는 §6에 연결하며 아래 순위는 보존한다. S는 `SOURCE-SUPPORTED BOTTLENECK CANDIDATE`, H는 `HYPOTHESIS REQUIRING MEASUREMENT`다. 아래 순위는 예상 사용자 영향·근거·비용·회귀 위험을 함께 고려한다. 가장 큰 과거 비용이 바로 수정 가능한 첫 과제라는 뜻은 아니다.

공통 host 비교는 동일 fixture·소스/도구 identity, 준비와 측정 구간 분리, warmup 5회 뒤 표본20회씩의 교대 block 3개를 기본 제안으로 한다. median/p95·원 표본·행/요청/작업 수를 함께 기록한다. 타이밍 채택 기준은 각 block의 paired median 개선과 작은 workload p95 10% 이내 비회귀다. 이는 향후 국소 과제의 제안 기준이며 기존 계약·기기 SLA·T6.9 수용 기준을 바꾸지 않는다. 변동으로 판정 불가능하면 이득 미입증으로 종료한다.

| 순위·후보 | 영향·근거·공수/위험·잠금 | 구체적 host 측정과 수용 조건 |
| --- | --- | --- |
| 1 C1 bundle admission·baseline CPU(S) | 모든 refresh/save에 영향, 과거 M1 강함. 구현 중간~큼/위험 높음. parser/store/AppState가 보호 목록에 있으므로 현재 수정 제외 | 현재 exact source의 stage observer+replaceBaseline으로 ledger376/1k/5k/10k, current105 고정. parse·할당·encode·publish를 분리. 후속 변경은 동일 rejection/bytes·authority/durability를 유지하고 대상 작업 수와 전체 operation 모두 공통 기준 충족해야 채택 |
| 2 C2 탭별 전체 refresh 반복(S) | 빈번한 navigation의 network·parse·저장 비용 후보. source 직접 근거, 이득 크기 미측정. 중간/위험 높음, AppState/coordinator 보호 | fake transport로 고정 탭 sequence와 빠른 전환의 request/retired ticket 수, 합성 지연0/150ms에서 화면 요청→fresh 설치 측정. request 수 감소와 명시 refresh·mutation·auth/generation·baseline 의미 보존이 함께 필요. TTL cache·조회 생략은 현재 미승인 |
| 3 C3 당월 위젯 선생성(S) — 첫 과제 | 큰 current 목록에서 build당 O(N) 위젯 할당. source 근거 명확, 사용자 효과 크기는 미측정. 작음/낮음~중간. 확인한 명시 보호 목록 밖 | §6. 0/50/500/1k/5k current expense로 초기 build·고정 스크롤·재build. 행 위젯 선생성 제거, 표시/입력/수정 동등성, 시간 공통 기준 충족 |
| 4 C4 Snapshot 보관 목록의 반복 decode(S) | startup/resume·목록 진입에 영향, save에서 list 반복이 명확. 중간/위험 중간~높음. LocalSnapshotRepository 보호 | 합성 Snapshot0/1/30개×376/10k행, 파일 open/read/decode count·총 byte·save/list 시간. 파일 변조/동시 save·readback/prune 계약을 유지하면서 반복 전체 검증을 제거한 횟수와 전체 시간이 감소해야 함. 안전한 invalidation 증명 없는 metadata cache 제외 |
| 5 C5 root rebuild와 반복 정렬(S) | 일반 notify마다 홈·목록 파생 작업 후보. 직접 근거, 실제 rebuilt subtree 미측정. 작음~중간/위험 중간. root UI는 별도 검토, AppState는 보호 | 동일 immutable state에 상태메시지·busy·금융 응답을 각각 변경해 build/정렬 횟수·할당 계수. 무관한 갱신의 작업 수 감소, 금융/Offline/로그아웃의 화면 갱신 누락0, 공통 timing 기준 |
| 6 C6 웹 전체 reload·archive(S) | 14 GET과 전체 archive 취득, table map 근거. 사용자 빈도/통신비 미측정. 중간/위험 중간~높음 | request recording+합성 장부376/10k의 초기/일반 저장/월 전환, React commit·DOM 수 측정. 불필요 요청/DOM 작업 감소, labels/history/retry·draft 보존과 공통 시간 기준. 모바일 bundle을 웹에 즉시 대입하지 않음 |
| 7 C7 SQL/presenter 세부 귀속(H) | 기존 index·fetchall/COALESCE 정렬은 확인, 지배 query 미확정. 중간/위험 높음, backend schema/service 보호 | 폐기용 합성 migrated DB에서 실제 SELECT의 EXPLAIN QUERY PLAN·query 수·반환행·wall/CPU 기록. 지배 query를 먼저 입증한 경우에만 검토. 결과/order 동등, query/방문량 감소와 endpoint 시간 기준 충족. index 추가·transaction 분할 선제 시행 없음 |
| 8 C8 native 알림 JSON 처리(H) | UI handler의 저장소 직접 호출 근거, 실제 stall 미입증. 중간/위험 중간 | host Kotlin/Dart의 0/100/512개 합성 decode/grouping count와 시간으로 CPU 후보만 좁힘. source별 내용·중복 identity 보존 필요. 실제 channel/UI 시간 수용은 기기 보류라 현재 host 결과로 완료 선언 불가 |

B05/B08의 추가 확대 실험은 첫 후보에서 제외한다. 이미 전체 경로 이득이 미입증/혼재하고, source lock·engine 입장·정량 이관과 연결된다. 이번 backlog는 원 B03를 고치거나 T6.9를 재개하는 우회 경로가 아니다.

## 6. 정확히 하나의 첫 최적화 과제

**P1-01: `mobile/lib/src/screens/month_entries_screen.dart:MonthEntriesScreen.build`의 `...rows.map(_MonthEntryCard)` 선생성을 지출 행의 지연 생성으로 전환하는 실험을 완료했다.** [실측 결과](../p1-01-monthly-expense-lazy-widget-results.md)는 **NOT ADOPTED — PERFORMANCE CRITERIA NOT MET**다. 선생성 N→0을 확인했지만 1k build 중앙값이 1·3블록, 5k가 1블록에서 개선되지 않아 원복했다. 최종 화면 SHA는 아래 기준과 같다. 다음 후보는 자동 착수하지 않는다.

기준 source SHA-256은 `f876b19c0872f533e226ab366ff45a8ce61fb0af568672aad9bdcd130cac5e81`이다. B03 archive의 같은 파일과도 동일하다. B03 source-lock-review, P0 protected-source/worktree-targets와 adapter isolation의 명시 보호 목록을 확인했으며 이 화면은 포함되지 않는다. 이것이 frozen archive를 수정할 권한은 아니다. 착수 시 현재 SHA·보호 목록을 다시 확인하고 변화가 있으면 재판단한다.

허용 구현 범위는 이 화면의 행 delegate·필요한 안정 identity와 직접 host benchmark/widget 회귀 파일 하나다. 헤더·ExpenseInputCard의 위치와 생명주기·draft를 유지하며 행 생성만 지연한다. AppState의 정렬·API·bundle admission·DB·Offline/segmented·source-lock 기대값·금융 계산은 건드리지 않는다. 기존 ListView의 element/layout 지연과 새 위젯 객체 생성 지연을 구분한다. API payload나 current 목록 수를 줄이는 작업도 아니다.

다음 과제의 재현·수용 절차는 다음으로 한정한다.

1. 현재 소스의 **구현 전 baseline을 먼저 측정**한다. Flutter host widget 환경에서 fake API와 메모리 AppState로 동일 날짜·id·길이의 current expense 0/50/500/1k/5k개를 만든다. 네트워크와 디스크는 측정 밖에 둔다. 고정 logical viewport 400×800, text scale1.0, 동일 Flutter/Dart를 사용한다. archive N과 화면 current 행 수를 혼동하지 않는다.
2. `MonthEntriesScreen.build`의 host 실제 벽시계와 반환 list delegate가 보유한 선생성 지출 카드 수를 기록한다. 기존에는 N개다. 전체 widget pump와 고정 10회 scroll의 실제 벽시계·mounted 행 수·rebuild도 따로 기록한다. test binding의 가상 frame duration을 실측 frame time으로 쓰지 않는다. full sort 비용은 양쪽에 그대로 포함한다.
3. 같은 fixture와 §5의 교대 block으로 변경 전후를 비교한다. **초기 전체 N개 지출 카드 선생성은 0개**, viewport/cache 범위에서만 생성돼야 한다. 1k/5k의 화면 build median은 세 block 모두 감소하고, 0/50개의 pump/scroll p95는 baseline의 110% 이하여야 한다. 실패·불확실이면 미채택으로 처분하며 다른 최적화를 섞지 않는다.
4. 0건·동일 날짜 정렬·긴 한글/emoji·첫/마지막 행 접근, 스크롤 후 분류/할인/실결제액·삭제 대상 identity, 서버 표시 금액, pull refresh를 확인한다. 입력 중 스크롤/일반 notify/성공·실패 응답에도 draft·focus·single-flight가 기존 의미를 유지해야 한다. Offline disabled/예상 표시와 재정렬 후 dropdown 연결도 검사한다. 기존 `offline_widget_submit_test.dart` 등 직접 영향 회귀를 사용한다.
5. host 위젯 비용 감소만 판정한다. 실제 raster/GPU·120Hz/thermal·Android heap·앱 startup·전체 sync 개선은 주장하지 않는다. 증거는 이 로드맵과 단일 보조 근거를 갱신한다. 추가 기기·대규모 source qualification 프로젝트는 열지 않는다.

### P1-02 — 두 번째 실험 완료, C5 보호 경로 보류

[결과 보고서](../p1-02-flutter-rebuild-derived-state-results.md)의 판정은 **DEFERRED — PROTECTED OR HIGH-RISK PATH**, baseline gate는 C다. 50/500/1k/5k행과 8개 host 구성에서 warmup5회·표본20회(측정640개)를 수집했다. busy/status의 정착 화면은 notify/root builder/HomeShell/활성 화면 build/getter가 각각1회였으며, 모든 탭이 함께 build되지는 않았다. 5k의 변경 없는 알림에서 필터·정렬 중앙값2.27~2.49ms가 측정돼 비용을 무시하지 않는다. 다만 같은 build 안의 중복은 없고 알림 사이 재평가 제거는 protected AppState의 invalidation/publication 또는 금지된 cross-generation cache와 연결된다. UI 파일로 같은 정렬을 옮기지 않았으며 생산 코드는 수정하지 않았다.

빠른 navigation은 각 합성 refresh 완료 후 연속 탭 전환으로만 측정했다. 겹친 요청과 실제 OS/device 복귀는 미측정이다. 이 선택적 성능 개선을 새로운 correctness blocker나 formal release gate로 만들지 않는다. P1-02는 완료했지만 1단계 전체 완료는 아니다. **당시 남은 후보 최대1회 제한은 §2.1의 소유자 갱신 계획으로 대체됐다. P1-01/P1-02 결과는 재개·변경하지 않는다.**

### P1-03 — Snapshot 비용 귀속 완료, B 판정·미구현

[결과 보고서](../p1-03-snapshot-save-validation-performance-results.md)와 [단일 압축 근거](../benchmarks/p1-03-snapshot-performance.json.gz)에 현재 보호 소스·서버 v7 합성 fixture의 비용을 보존했다. 보관0/1/10/30개×376/1k/5k/10k행의 list/save/save 뒤 list를 측정했다. 큰 비용 때문에5+20 전체 반복 대신 구성별 warmup1+표본3, 원 소스 대조4구성은1+2를 사용했다. 최종152표본은265.18초에 수집했으며 p95는 소표본 최댓값이다.

10k payload는5,934,477B다. C30의 저장은 read/decode/검증62회·읽기367,937,574B·쓰기5,934,477B, 중앙값7866.068ms였다. 저장 뒤 추가 list까지는92회다. 새 파일 readback과 보관 파일 검증을 독립 안전 경계로 보존한다. 유일한 후보는 save 내부 prune의 검증 완료 생존 목록을 반환에 재사용해 마지막 전체 순회를 줄이는 것이다. 다만 동시 저장/삭제·파일 변경/손상 재관측을 보존해야 하고 대상 repository는 보호 소스이므로 별도 권한과 안전성 입증 없이 구현하지 않는다. 생산 수정0개, Snapshot 확장성 후속 과제는 미착수다. 초기 Flutter crash 자동 진단이 ADB 서버를 기동한 경계 위반을 종료 확인에서 발견해, 작업 소유·활성 TCP/USB 부재를 확인한 해당 PID만 OS 신호로 종료했다. 비용 귀속은 완료했으나 전체 작업 판정은 PARTIAL이며 상세 기록은 결과 보고서에 남긴다. 다음 작업은 소유자가 정하며 P1-04/P1-05/P1-R을 자동 시작하지 않는다.

### P1-04 — backend SQL·presenter 귀속 완료, C 판정·미구현

[결과 보고서](p1-04-backend-sql-presenter-performance-results.md)와 [단일 압축 근거](../benchmarks/p1-04-backend-sql-presenter-performance.json.gz)에 과거 최적화6개 묶음·현재 source 대조와 5규모/7경로의 기준700·상세105표본을 보존했다. T6.6A의 정상 service/Snapshot/presenter/DB/migration5파일과 nonempty payload4종의 SHA가 현재와 동일해 과거 결과를 재사용했다. 본 실행170.779초, 원 SQLite 기준10k bundle 중앙값1273.714ms/p95 1462.058ms다. 별도 profiler에서는 SQL execute19.929ms/fetch272.894ms, 연결 생성0.290ms, current presenter2.847ms였고 Snapshot·관계 검증·canonical JSON/hash가 컸다. profiler 포함 시간을 기준 latency에 합산하지 않는다.

기존 transaction-local ownership PASS는 runtime 검사 요청6회에 실제 raw6테이블 검사2회(Snapshot1+view1)로 유지됐다. 기존 인덱스 사용과 필요한 full scan을 구분했으며 지배적 인덱스/connection 결함은 입증하지 못했다. 새 안전한 제거 후보0개·추천 구현0개, **C — 현재 correctness 계약에 필요한 큰 비용**으로 처분한다. 모든 비용 제거를 1단계 종료의 새 조건으로 만들지 않는다. 기존 source lock·schema/transaction·금융/인증·authoritative/Offline 계약과 P1-03 PARTIAL 사건을 보존했다. Flutter·Android·ADB는 사용하지 않았다. 조사 당시 P1-R/P1-S는 계획·미구현, P1-05는 선택·미승인이었으며 후속 결정은 §2.1에 반영했다. 다음 과제를 자동 시작하지 않는다.

## 7. 3단계 정리 전략

2단계 종료 후 아래 inventory만 의존성을 확인한다. **이번에는 수정·삭제 0개**다. 텍스트 참조가 없다는 사실만으로 dead code를 선언하지 않는다.

| 분류 | 구체적 후보·범주 | 제거/보존 근거와 필요한 확인 |
| --- | --- | --- |
| SAFE CLEANUP CANDIDATE | `month_entries_screen.dart`의 `_MonthEntryCard._isTransport/_isToll` 단순 getter 전달 wrapper | 같은 library의 private 직접 호출 각1개와 본문 `entry.isTransport/isToll`을 확인. 금융 재계산 없이 getter로 직접 표현 가능. 1단계 변경 후 여전히 존재할 때만 검사·정리하며 badge 동작 회귀 확인 |
| REQUIRES DEPENDENCY VERIFICATION | `AppState.recentEntries` getter | lib/test 검색상 직접 소비가 보이지 않고 홈은 expenseEntries.take(10)을 사용. public API·외부 harness와 source lock이 있으므로 현재 dead 판정/삭제 불가 |
| REQUIRES DEPENDENCY VERIFICATION | 사용되지 않는 Flutter widget/helper, 이전 navigation·state branch, 중복 API convenience wrapper와 `NotificationBridge` 별칭, unused local query | Dart analyzer·전체 import/export·Navigator builder·part/library·fake subclass·테스트와 외부 harness 호출까지 함께 확인. MethodChannel 문자열·native callback 등록도 조회. 현재 특정 widget/query의 dead 확정은 없음 |
| REQUIRES DEPENDENCY VERIFICATION | 옛 실험 switch·feature flag·중복 serialization/DB adapter·test fixture | build flavor, dart-define, devicegate entrypoint, pubspec assets, generated code, fixture manifest, 환경변수 및 전용 시험 consumer를 추적. 사용이 없고 source lock·외부 계약도 없는 항목만 정리 |
| MUST PRESERVE | `acquireLegacyForDiagnostics`, legacy full consumer/store·Snapshot v4~v7·DB migration·historical normalizer | 명시 regression oracle·복구·이관/whole-F 의무를 소유. Phase B 행정 종결은 제거 승인 아님 |
| MUST PRESERVE | `backend/app/repository.py`, `frontend/src/api.ts`, `components/LedgerTables.tsx` 등 호환 re-export | [compatibility-inventory](../guides/compatibility-inventory.md)의 import 계약. 중복 구현과 facade를 구별 |
| MUST PRESERVE | claim/family, judgment YAML registry, `management_*.dart` part, 등록 asset, 지원 flag, server API response 필드 | 현재 기능·동적 registry·persisted wire 계약. Claim은 무기한 유지·제거 예정 아님. 낮은 빈도로 기능을 dead로 분류하지 않음 |
| MUST PRESERVE | B03 계측/source locks·archive·역사 실패 로그·유일 SQLite 증거·devicegate/G1/G2 자료 | 일반 dead-code 정리 권한으로 역사 증거/계약/호환 자격을 지우지 않음 |

확인 순서는 analyzer/컴파일 → import/export 및 route·DI·dynamic registry·generated/asset 확인 → 테스트/실험·migration·외부 API consumer 확인 → 작은 삭제 단위 → 관련 회귀와 build다. Python importlib/getattr·YAML name과 router 등록, Dart part·native method 이름, JS barrel export를 포함한다. 안전성이 입증되지 않는 항목은 남기고 4단계에 짧게 처분한다. 기존 캐시·실험 DB의 용량 정리는 별도 위생 정책 대상이며 dead-code 삭제와 섞지 않는다.

## 8. 4단계 단일 최종 감사와 한정 수정

**아래는 계획이며 현재 감사 결과가 아니다.** [known-issues](../known-issues.md)의 기존 수정·독립 재검토 대기와 과거 반례를 입력으로 재사용한다. server financial oracle와 mobile 구조/저장/authority oracle의 책임을 나눈다. 새 모바일 금융 재계산 의무를 추가하지 않는다.

| 한 번의 통합 감사 영역 | 확인할 결과·우선 회귀 근거 |
| --- | --- |
| 금액·할인·반올림·Summary | exact ±(2^53−1), raw token/REAL 경계, Decimal/floor·override·중간 상쇄·노출 합계 overflow. card_charge·exact_money·canonicalization 회귀 |
| 관계·중복·누락·영속성 | payment key/batch/allocation/event/cash-flow의 소유, recurring source/epoch, fixed 실제액, 중복 요청·누락 행·revision. persistent_relationships와 기존 실패 반례 |
| SQLite migration·하위호환 | 빈/인정 unversioned/DB v4, 지원 Snapshot v4~v7, immutable historical ownership proof·checkpoint rollback, index/trigger 실제 계약. fixture 원문 유지 |
| sync·멱등성·복구 | late generation, auth 교체, outcomeUnknown/rebuildPending, journal tail/중복, Mobile/Server Wins·response loss·partial operations·restart. 서버 단일 transaction과 mobile durable cleanup 순서 |
| backend API·인증·접근 경계 | raw/typed compatibility·prepared response·status, principal/session·share read-only·Origin/HTTPS·secret/artifact 노출. 변경 전 security/runbook 확인 |
| Flutter 기능·lifecycle | 폼 single-flight·draft/focus·dropdown identity·목록/empty·탭·dispose·resume·알림 후보 등록. host fake로 증명하지 못하는 native 동작은 기기 보류 목록 유지 |
| 성능 회귀 | 채택한 1단계 slice의 고정 baseline·요청/작업 count·host 분포를 한 번 재확인. micro 결과와 전체 완료 시간을 구분. T6.9 별도 의무는 보존 |
| build·의존성·artifact | 재현 명령·lockfile·runtime/source identity, npm build·관련 웹/Flutter/backend suite, 생성 artifact hash·환경/서명 분리. 역사 source-lock 판정을 새 소스로 위장하지 않음 |
| 운영 준비 | runbook의 staging/rollback·백업/복원·정확 금액·historical admission 조건과 남은 formal gates를 문서로 판정. 운영 DB 조회·migration·restart·배포는 별도 명시 권한 필요 |

| 심각도 | 처분과 종료 효력 |
| --- | --- |
| P0 — 데이터 유실·보안 침해·돌이킬 수 없는 손상 | 즉시 중단/격리. 수정과 집중 회귀가 끝나기 전 종료 차단 |
| P1 — 중대한 기능·영속 상태 오류 | 수정과 집중 회귀 필수. 미해결이면 종료 차단 |
| P2 — 복구 가능한 결함·상당한 사용성 문제 | 근거·영향·복구 방법·수정 또는 정당한 보류 이유를 이 문서에 처분. 설명 없는 누락 불가 |
| P3 — 작은 문제·유지보수 우려 | 기록 후 비차단 처분 가능 |

모든 수정은 원 반례를 고정하는 집중 회귀를 갖는다. 한 감사표에 finding→수정→검증을 연결하고, 변경한 영역만 재검토한 뒤 **최종 통합 검증 1회**로 종료 준비를 판정한다. 통합 검증이 실패하면 해당 실패의 수정·영향 재검증만 추가한다. 미해결 P0/P1을 남겨 둔 채 보류 명칭으로 종료하지 않는다. 사전에 정한 수정 예산(기본 한정 수정 2회)을 소진하면 자동 연장하지 않고 남은 blocker를 보고한다. 횟수 제한은 결함 면제나 자동 완료가 아니다.

현 단계의 비중요 correctness 이월 목록은 다음 세 묶음으로 고정한다. 새 증거가 생기지 않으면 별도 감사 프로젝트를 만들지 않는다.

- 기존 known-issues의 exact money·canonicalization·persistent/recurring ownership·freeze 수정에 대한 독립 종결 확인, 운영 compatibility/admission 준비. 기존 수정 반례와 테스트를 유지한다.
- 대량 목록의 dropdown/element identity·draft·focus·foreground 재진입 및 상태 알림 범위. 현재 source만으로 새 결함이나 severity를 확정하지 않는다. 첫 slice에 직접 영향을 주면 그 과제에서 필요한 회귀만 수행한다.
- SQL plan·allocation/GC·notification native 지연·웹 request fan-out의 현재 미측정 부분과 3단계 의존성 미확정 항목. 기능 결함과 성능 불확실성을 구별한다.

이번 범위에서 **새로 실증한 치명적 금융·보안·영속 상태 결함은 없다.** read-only 발견과 기능 smoke의 결론이며, 전체 안전성 인증이나 기존 release blocker 해소를 뜻하지 않는다.

## 9. 단계별 명시 종료 조건

| 단계 | 종료에 필요한 유한 조건 | 현재 상태 |
| --- | --- | --- |
| 1단계 | UI15/처리12 지도, 근거별 우선순위, §2.1 조사와 공유 계획 G의 승인된 완화 작업·감사 지적 처분 완료. 모든 병목 제거는 불필요하며 권한/위험상 보류 가능. 채택 변경의 기능·성능 회귀 통과·미해결 신규 P0/P1 없음·잔여 불확실성 §8 이월 | P1-01 미채택·원복, P1-02 보호 경로 보류, P1-03 B/전체 PARTIAL·미구현, P1-04 C 완료. R-01 최초 실패 보존·owner1회 예외 재채택·활성132 PASS, S/U 보류, P1-05 소유자 제외. **CLOSED — 최종 독립 감사 PASS·owner 종료 승인, S/U 보류 유지** |
| 2단계 | 별도 승인된 모바일 전송량 분석·최적화와 전후 측정·채택/미채택 처분 완료, 안전 계약과 기능 회귀 유지, 남은 불확실성 §8 이월 | **IN PROGRESS — N01 ACCEPTED(PASS, A01/R1 CLOSED), N02 조사 DEFER·독립 GET 유지 권고. 최초 PARTIAL/REWORK 보존. N02~N05 미구현** |
| 3단계 | 좁은 inventory의 고신뢰 dead/redundant 항목만 정리, 동적/호환 consumer 보존, 관련 Flutter/backend/web 회귀·build 통과, 미확정 비중요 항목 처분 | **D01–D03·Claim 유지 정책 ACCEPTED, 독립 감사 BLOCKER/MAJOR 없음. P3-A01 수정 완료. 안전 게시 진행, D04–D06 보류** |
| 4단계 | 단일 감사표 완료, P0/P1 해결 또는 명시 차단, P2/P3 처분, 집중 회귀와 최종 통합 suite 통과, source locks·역사 증거 보존, 기기/배포 제약 명시 | **NOT STARTED — 별도 owner 승인 필요** |

각 종료 시 수행자가 결과를 기록하고 이전 단계의 exit 충족을 확인해야 다음 단계에 진입한다. 새 범위의 구현은 해당 작업 요청으로만 시작한다. 단순 보고서 작성이나 표의 READY로 다음 단계가 자동 시작되지 않는다.

## 10. 유한 프로젝트 종료 기준

개발 유지보수 종료는 ① §9의 네 단계 완료, ② 미해결 P0/P1 없음, ③ 모든 P2/P3의 처분과 남은 책임 명시, ④ 채택 최적화의 재현 가능한 host 근거 및 회귀/build 통과, ⑤ 데이터/도메인·source locks·증거·인덱스 보존, ⑥ 실기기/G2/ADB/T6.9/formal F/R1/배포 보류를 소유자에게 명시적으로 인계한 경우에만 판정한다. 네 단계가 끝나도 새 기능·끝없는 문서 재검토를 종료 조건으로 추가하지 않는다.

이 판정은 **기존 runtime의 개발 유지보수 범위 종료**로 한정할 수 있다. 미충족 formal F/T6.9/R1/실기기 gate를 가진 segmented 전환 전체 완료·release 완료·production readiness는 선언할 수 없다. 이관 의무의 면제·흡수·수용은 이 로드맵의 권한 밖이다. 운영 readiness 또는 rollout은 기존 필수 증거 수용과 별도 명시 배포 승인이 모두 충족된 뒤 판단한다. 현 단계에서는 개발 종료도 아직 선언하지 않는다.

## 11. 최초 계획 세션 검증·보존

- 실행 코드·테스트·binding 계약·과거 보고서 수정 및 dead code 삭제는 0개다. 신규 문서는 이 로드맵과 단일 compact JSON 근거뿐이다.
- `npm run build`는 현재 frontend 소스의 task-owned 임시 사본과 기존 node_modules를 사용해 통과했다. Node22.22.3/npm12.0.1. 기존 build/cache와 운영 파일은 교체하지 않았다.
- Python3.12.3에서 기존 authoritative-state 기능 smoke 3건(빈 상태의 legacy 동등성, rich state 동등성, Snapshot/Summary/payment·연결 경계)을 새 합성 임시 DB로 실행해 **3 PASS, 실패/오류/skip 0**이었다. 전체 backend/Flutter 최종 회귀를 실행한 결과로 확대하지 않는다. 성능 timing 표본도 아니다.
- 저장소에서 Git이 열거한 기존 tracked/untracked 일반 파일·symlink **7,927개**의 내용·mode와 인덱스·staged entry를 전후 대조해 변화 **0개**를 확인했다. frozen 외부 B03 archive도 SHA를 재확인했다. 구체적 결과·집계 hash·한계는 [보조 근거](../benchmarks/final-optimization-and-closure-evidence.json)에 남겼다. ignored cache 전체의 무변경을 인증하는 범위는 아니다.
- task-owned `/tmp`의 frontend 사본·합성 테스트 DB·build 중간물 **72개 파일/symlink, 관찰 할당량 2,756,608B(약 2.63MiB)**를 검증 후 정리했다. 성공 로그 전문 대신 결과와 로그 hash를 보조 근거에 보존했다. 기존 증거·DB/WAL/cache와 symlink 대상은 삭제하지 않았다. 새 benchmark·ADB·운영 API 요청·production 접근·Git index 조작·commit·push는 수행하지 않았다.

**P1-01 후속 기록:** baseline을 먼저 수집한 뒤 3블록·600개 측정 표본으로 비교했다. 후보 기능 13건, 원복 후 기능 13건·보호 검사 29건, npm build·backend 기능 3건이 통과했다. [원시 근거](../benchmarks/p1-01-monthly-expense-lazy-widget-raw.json.gz)와 기존 compact JSON의 `p1_01`에 판정을 보존한다. **다음 행동은 미채택 결과를 기준으로 다음 1단계 과제를 별도로 선정하는 것이다.** 2단계 모바일 데이터 사용량 분석은 이번에 시작하지 않았다.

**P1-02 후속 기록:** 생산 수정0개, baseline32구성 수집 완료, 기존 UI6건·보호 검사29건·웹 build·backend 기능3건 통과. 원문과 [원시 근거](../benchmarks/p1-02-flutter-rebuild-raw.json.gz)는 기존 compact JSON의 `p1_02`에 연결한다. **다음 행동은 후보를 자동 시작하지 않고 현재 기준으로 1단계 종료 여부를 한 번 검토하는 것이다.** 2~4단계와 Snapshot 확장성은 시작하지 않았다.

**완화 구현 승인(2026-11-03):** owner가 P1-R-01, P1-S repository와 직접 SHA/무결성 검사 변경을 승인했다. R 처분 뒤 S를 실행하고 P1-U는 보류한다. dirty worktree를 보존하며 `phase1/mitigations`에 한정된 중간 결과를 commit/push한다. 다음 독립 감사는 구현 batch의 Mitigation Audit이며 배포·다음 단계는 미승인이다. 실제 결과·commit/push는 [공유 장부](phase1-mitigation-plan.md)에 누적한다.

**R-01 구현 처분:** 승인된 3블록 측정840개에서 중간 GET3개 감소·주 latency 감소를 확인했지만 작은 인접 대조p95가110% 기준을 넘었다. NOT ADOPTED로 HomeShell을 원래 SHA로 복구했고 직접 host focused132건이 통과했다. raw·한계·다음 S 조건 확인은 공유 장부/단일 mitigation 근거에 보존한다. 1단계는 진행 중이다.

**S 구현 처분:** R 처분·push 뒤 동일 P1-03 payload로 측정한 추가SHA61회 비용은 제거decode30회의1.51~1.85배였다. 비용 조건 실패로 DEFER·repository/보호 검사 변경0개다. 원래 P1-03의 PARTIAL/B와 반복 검증 기회는 보존하지만 이 receipt 안의 이득을 주장하지 않는다. 다음은 owner의 독립 Mitigation Audit이며 1단계 종료·다음 단계 착수는 선언하지 않는다.

**P1-R-01 재채택:** 독립 거부 검토 A와 owner의 P1-R-01 한정1회 p95 예외 승인으로 보존된 B 화면 전체와 byte 동일한4행을 복원했다. 활성 소스 SHA `b48dc5975cd1018b6f705aaffcbe2028b2856fbe023ebb4ebdb7437324fb93c7`에서 focused132건이 새로 통과했다. 원래110.37% 초과·NOT ADOPTED/rollback과 모든 음성 측정은 보존하며 원 실험PASS로 바꾸지 않는다. 신규 성능 campaign 없이 이전 GET4→1·median 근거를 재사용했다. S/U 보류·다른 수용 기준 불변, 1단계 종료는 선언하지 않는다. 현재 결정과 게시/재현은 공유 장부 RS1과 단일 근거 `r01_reinstatement`에 있다.

**Phase 1 종료 승인:** 최종 독립 P1-R-01 감사 **PASS — MITIGATION ACCEPTED**, 활성132/132 PASS·GET4→1·기존 host median 근거·원110.37% 실패와 한정 예외·거부/원복을 보존하고 1단계 mitigation work를 CLOSED로 기록한다. S/U는 DEFERRED다. 기존 formal/기기/배포 gate는 그대로이며 개발 전체 종료가 아니다. 다음은 별도 승인된 Phase 2 모바일 네트워크 조사·후보 감사이고 구현은 하지 않는다.

**Phase 2 조사 완료:** [모바일 네트워크 후보 문서](phase2-mobile-network-optimization-candidates.md)와 단일 압축 근거에 현재 source·합성3규모·실제 IOClient84개 전송/6개 byte-exact 대조를 보존한다. 우선 N01 Bundle/Snapshot 응답 gzip, N02 자동 백업 Snapshot 재사용은 계약 확인 조건부다. 304·request gzip은 보류, 필드/history 삭제·segmented 활성화는 제외다. Phase1은 CLOSED이며 재개하지 않는다. 다음은 독립 Phase2 Candidate Audit이고 구현·Phase3/4·확장성·배포는 미착수다.

**P2-N01 scoped 구현:** owner 승인으로 두 GET route의 완성 JSON gzip helper를 구현했다. backend139·기존 모바일91 PASS, 신규 모바일5 PASS/1 FAIL(trailer 거부 미충족), 자원·bytes 근거와 조건부 상태는 [후보 문서 §9](phase2-mobile-network-optimization-candidates.md#9-p2-n01-한정-구현--implemented--verification-partial)에 둔다. 검증 PARTIAL이며 다음은 독립 변경 감사다. 다른 Phase2 후보·Phase3/4·배포는 미착수다.

**N01-A01 correction:** owner 승인 후 모바일 raw gzip transport와 archive3.6.1을 연결했다. 기존 trailer 거부 포함 신규10·기존91 host PASS, backend7 PASS. [후보 문서 §10](phase2-mobile-network-optimization-candidates.md)에 자원 한계·단일 member 정책·검증·재감사 인계를 기록했다. 최종 수용·Phase2 종료·운영 배포는 선언하지 않는다.

**N01-A01-R1:** targeted REWORK 후 독립 SDK DEFLATE pass를 추가했다. exact witness 포함 모바일103·backend7 PASS, 추가 CPU/wall 한계는 후보 문서 §11에 있다. 의존성/서버/금융 변경 없음. 다음은 독립 targeted 재감사이며 최종 채택·배포는 미승인이다.

**Phase2 현재 처분:** owner 최종 PASS·N01 ACCEPTED, A01/R1 CLOSED·blocking findings 없음. 채택 commit13ef6e9, 과거 이력 보존. [N02 조사](phase2-n02-snapshot-reuse-investigation.md)는 T3→T1 복구점 변경을 일반적으로 배제할 수 없어 **DEFER/C 유지 권고**다. 10k 추가 이득의 잠재 상한은 gzip104,537B/자동event1GET이며 확정 제거 event는0이다. N01 배포·main merge·N02 구현·Phase2 전체 종료는 승인/수행하지 않는다.

**Phase3 후보 조사:** owner 승인으로 [inventory](phase3-cleanup-candidate-inventory.md)를 작성했다(A3/B3/C6). Phase2 전체 종료 미기록·기존 현재 표의 stale PARTIAL은 inventory §1에 명시했고 현재 표만 개별 처분으로 맞췄다. N01 이력·N02 DEFER는 보존하며 Phase2 종료를 소급 선언하지 않는다. 다음은 독립 후보 감사이며 코드 삭제·Phase4·운영은 미착수다.

**D01–D03 scoped cleanup 승인:** owner가 독립 후보 감사 뒤 세 항목만 승인했다. Claim은 [무기한 유지](../domain-model.md#claim-유지-정책)하며 과거 제거 계획은 폐기된 역사 자료로 보존한다. D04–D06 구현은 보류이며 특히 D04는 변경된 Claim 정책 아래에서 다시 평가하기 전 구현하지 않는다. 진행·검증은 inventory §11에 기록하고 staging/commit은 하지 않는다.

**Phase 3 수용·게시 결정(2026-11-04):** 위 구현 당시의 미게시 기록은 보존한다. 후속 독립 scoped 감사에서 BLOCKER/MAJOR 없음, owner는 D01–D03·Claim 유지 정책과 감사 결과를 수용했다. MINOR P3-A01의 잘못된 4단계 상태를 **미착수·별도 승인 필요**로 수정했다. 이번에는 검토된 경로만 commit/push하며 devicegate 보안 설정·연관 소스는 owner 결정에 따라 제외한다. 미확인 과거 실험·DB·키·원시 로그도 원위치 보존한다. 상세 게시 범위와 최종 종결은 [inventory §12](phase3-cleanup-candidate-inventory.md#12-phase-3-수용안전-게시)에 기록한다. Phase4·운영 배포·main 병합은 승인하지 않는다.
