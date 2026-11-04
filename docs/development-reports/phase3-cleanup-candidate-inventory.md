# Phase 3 dead code·중복 정리 후보 inventory

**D01–D03 scoped 구현·검증 완료 / 독립 감사 대기. Claim 무기한 유지, D04–D06 구현 보류.** 기준: `phase2/mobile-network / bb718029887143c65f95eab7a4f58806f55f31fc`, 실제 working tree 포함. 이 문서의 AUDIT은 독립 후보 감사 추천이며 삭제 승인·성능 개선 판정이 아니다.

§1~10은 감사 기준의 discovery 기록이다. 이후 승인 범위와 Claim 유지 결정·실행 결과는 §11을 따른다. 과거 AUDIT 추천은 현재 삭제 승인이 아니다.

## 1. 요약·진입 상태

12개 항목을 처분했다. **A3 / B3 / C6**, category D01×5·D02×1·D03×1·D04×2·D05×1·D06×2다. A만 우선 감사하고, B는 현재 삭제 대상으로 확정하지 않는다. 불필요 dependency·전체 widget·대형 subsystem 삭제를 입증한 결과는 없다. 작은 유지보수 이득을 위해 금융/복구 계약을 재설계하지 않는다.

Phase1은 [장부](phase1-mitigation-plan.md)의 C1에서 CLOSED다. Phase2는 [N01 최종 수용 §12](phase2-mobile-network-optimization-candidates.md)와 [N02 DEFER](phase2-n02-snapshot-reuse-investigation.md)가 기록돼 있다. **불일치:** 조사 시작 roadmap §2의 일부 현재 표는 아직 N01 PARTIAL이고 §9는 Phase2 IN PROGRESS, Phase3 진입 전으로 남아 있었다. Phase2 전체 CLOSED 선언은 기존 기록에 없다. 이번 owner의 **Phase3 후보 조사만** 승인을 근거로 조사했으며, Phase2 종료를 소급 선언하지 않는다. roadmap의 현재 표·링크만 현 처분으로 맞추고 과거 PARTIAL·REWORK·감사 이력은 보존한다.

운영 접근·DB 사용·빌드/시험·코드 삭제·dependency 변경·Android/ADB/Flutter CLI는 수행하지 않았다. 기존 tracked dirty13개(AGENTS, isolated_sync 계측, B03 counter/server, segmented protocol/build/artifact/test 등)와 미추적 test/devicegate/benchmark 상태는 task-owned manifest에 경로·내용 SHA·링크 target·Git porcelain로 기록해 변경 전후 대조했다. index는 처음부터 비어 있었고 관련 문서만 게시한다.

## 2. Repository inventory·경계

| 영역 | 실제 진입점·규모 | 정리 시 주의 |
| --- | --- | --- |
| Backend Python3.12+ | `backend/app/main.py:app` router 등록, app74 py·tests76 py·isolated_sync22 py·backend/scripts2 py | financial authority는 `services/card_charge/`, transaction/presenter·auth·migration·Snapshot·restore는 별도 책임. isolated sync는 정상 API 활성화와 구별 |
| Flutter/Dart | `mobile/lib/main.dart → MoneyNoteApp → AppState/HomeShell`, lib69 dart·test102 dart | callback/DI·private library part·MethodChannel/native 등록·pubspec assets 확인. OfflineStore는 JSON 파일이며 sqlite3는 별도 격리 store |
| Web TS/React | `frontend/index.html → src/main.tsx → App.tsx → hooks/components`, src54 ts/tsx(시험6 포함) | Vite 앱, package private=true, library mode/공개 npm exports 없음. API/type/compat facade와 JSX callback은 보존 |
| Scripts/운영 설정 | scripts36 py/sh/dart, `deploy-server.sh/release-mobile.sh → local_deploy.py`, `dev-server.sh`, canonicalization CLI | CLI는 내부 import가 없어도 독립 entrypoint. dry-run도 production 검사 가능하므로 실행하지 않음 |
| Build/native/generated | `.github/workflows/ci.yml`, backend Dockerfile/Compose, frontend Vite/tsconfig/ESLint, mobile pubspec/lock/Gradle·manifest·native25 kt/xml | JVM/Android/devicegate는 파일·등록만 inventory. asset/icon·package-generated/native callback 소비는 텍스트 함수 참조와 다름 |
| Historical data/contracts | docs/benchmarks·T6/G1/G2·Snapshot v4~v7 fixtures·source locks | evidence와 compatibility 자료는 삭제량 목표에 포함하지 않음. generated build cache 정리는 별도 위생 정책 |

Dependency 검토: backend FastAPI/router·Pydantic 간접 API, Uvicorn(Docker/Compose/dev launch), PyYAML(`judgment/common.py:_load_domain_messages → resources.files → yaml.safe_load`); dev pytest/httpx/ruff는 CI·tests가 소비한다. Dart 직접 dependency는 Flutter·crypto·archive·http·secure_storage·intl·path_provider·share_plus·shared_preferences·sqlite3이며 각 lib/native/backup/formatting/legacy session/격리 store 소비가 있다. flutter_test와 flutter_lints는 test/include 계약이다. npm runtime2(React/ReactDOM)·dev9는 entry·type resolution·Vite plugin·ESLint parser/hooks·TypeScript·Vitest가 사용한다. **import 문이 없다는 이유로 type/plugin/CLI dependency를 제거하지 않는다.**

## 3. 방법·한계

- **A inventory:** source/package/config/CI/route·CLI·native/asset 등록 및 roadmap의 KEEP 항목을 읽었다. effective working source를 사용하고 HEAD와 같다고 가정하지 않았다.
- **B static:** Python AST만 파싱해 module-level private symbol·동일 AST body를 찾았다(모듈 import/DB 초기화 없음). Dart private-name 탐색은 후보 생성용이다. 설치된 TypeScript Compiler API로 `createProgram(noEmit:true, incremental:false)`와 alias 해석/identifier 소비를 조사했다. 54 source files·227 function declarations, pre-emit diagnostics0. emit·tsbuildinfo·lockfile 수정은 하지 않았다.
- **C manual:** 선언/전체 source 문자열/명시 imports·barrels·사용 루트·dynamic `eval/import/namespace`·callback·part·route·문서 소비를 대조했다. TS의 `handlePanelSubmit` 등은 shorthand return/property 심볼 때문에 자동 소비 계수가0으로 나온 오탐이었다. `usePanelHandlers → App` destructuring→JSX handler로 reachable이므로 후보로 올리지 않았다. Dart private 단일-file 결과도 D10에서 배제했다.
- **D ranking:** unreachable 증거·작은 변경·외부 계약·기능 위험·집중 검증 비용을 우선했다. “PROVEN UNREACHABLE”은 **현재 저장소의 지원 entrypoint/config/test graph 안에서**라는 범위를 갖는다. 임의 외부 shell/브라우저 console/미제공 harness의 미래 import까지 증명한 뜻은 아니다.
- Flutter analyzer/Android tooling, Python runtime import, full regression/build는 실행하지 않았다. analyzer 설치·upgrade도 없다. `dart analyze` 등의 cache 부수효과와 native 도구 실행을 피하고 source/part 경계를 직접 확인했다. 아래 명령·시험은 **향후 승인된 변경의 제안**이지 이번 PASS 결과가 아니다. production/외부 API/cron/실제 사용자 legacy 파일 소비는 관찰하지 않았다.

## 4. 후보 inventory

confidence는 해당 처분 근거의 강도이며, C의 HIGH는 “미사용”이 아니라 “보존 필요” 근거가 강하다는 뜻이다.

| ID | Category | 대상·symbol | Reachability | Group | Confidence / Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| P3-D01 | D01 | `frontend/src/api/client.ts:64 fileToBase64` | PROVEN UNREACHABLE | A | HIGH / LOW | AUDIT |
| P3-D02 | D01 | `frontend/src/utils.ts:239 daysBetween` | PROVEN UNREACHABLE | A | HIGH / LOW | AUDIT |
| P3-D03 | D02 | `mobile/lib/src/screens/month_entries_screen.dart:247 _MonthEntryCard._isTransport/_isToll` | REACHABLE | A | HIGH / LOW | AUDIT |
| P3-D04 | D01 | `backend/app/services/card_payments.py:798 _clear_owner_discounts_for_month` | PROVEN UNREACHABLE | B | HIGH / MEDIUM | AUDIT(조건부) |
| P3-D05 | D01 | `mobile/lib/src/app_state.dart:204 AppState.recentEntries` | LIKELY UNUSED | B | MEDIUM / HIGH | DEFER |
| P3-D06 | D04 | `frontend/src/api/panels.ts:51 deletePanelsByType` | UNKNOWN | B | MEDIUM / MEDIUM | DEFER |
| P3-D07 | D03 | `mobile/pubspec.yaml sqlite3`, `segmented/store.dart` | REACHABLE | C | HIGH / HIGH | REJECT |
| P3-D08 | D05 | `response_coding_client.dart:ResponseCodingClient.send`의 archive·SDK passes | REACHABLE | C | HIGH / HIGH | REJECT |
| P3-D09 | D04 | `repository.py`, Web facade, Snapshot/DB/session legacy 경계 | REACHABLE | C | HIGH / HIGH | REJECT |
| P3-D10 | D01 | `segmented/store*.dart` private helpers, `_PatriciaEdit` | REACHABLE | C | HIGH / HIGH | REJECT |
| P3-D11 | D06 | `backend/scripts/clean_panel_dates.py:main/_ensure_columns` | REACHABLE | C | LOW / HIGH | REJECT |
| P3-D12 | D06 | historical Snapshot·N01 regression/fixtures·benchmark/asset/build 등록 | REACHABLE | C | HIGH / HIGH | REJECT |

## 5. Group A — 독립 감사 shortlist

### P3-D01 — fileToBase64

- **이유/범위:** [client.ts:64](../../frontend/src/api/client.ts:64)의 약11줄 FileReader Promise 함수만 후보. module 자체·`getJson/postJson`·auth cleanup·API_BASE_URL은 계속 사용된다.
- **증거:** TS alias 소비0, source/시험/scripts의 해당 이름은 선언뿐이다. `index.html→main.tsx→App.tsx` 아래 static imports에서 함수 alias·namespace 호출·window 등록·문자열 registry가 없고, `api/index.ts`는 client를 re-export하지 않는다. FileReader listener 등록은 함수가 호출돼야 일어나며 top-level 등록이 아니다. 현재 snapshot restore는 `useSettingsHandlers.handleSnapshotRestore`의 text 읽기와 `api/admin.ts`의 snapshot_text POST를 쓴다.
- **숨은 소비/의무:** 외부 개발자가 internal source module을 import하는 경우는 미관찰. package는 private Vite 앱이며 이 함수의 supported public API/직렬화/route 계약은 찾지 못했다. audit에서 기존 가이드·변경 diff와 module side effect 보존을 재확인한다.
- **의존·검증:** File/FileReader DOM API 외 dependency 없음, wire/영속 형식 영향 없음. 기존 `frontend/src/utils.test.ts`, Settings restore handler를 읽고 `npm --prefix frontend run lint`, `npm --prefix frontend run build`, 관련 Vitest를 제안한다. dead 함수 자체를 되살리는 시험은 만들지 않으며 새 restore 동작을 도입하지 않는다.

### P3-D02 — daysBetween

- **이유/범위:** [utils.ts:239](../../frontend/src/utils.ts:239)의 Date 차이 계산 함수5줄. named export이나 현재 소비0이며 다른 날짜·금융 helper를 변경하지 않는다.
- **증거:** 같은 TS graph·source/test 전체 검색에서 선언 외 참조·alias·export-star·동적 registry가 없다. `utils.ts`의 다른 exports는 App·hooks·tests가 계속 사용한다. `utils.test.ts`도 이 함수를 호출하지 않는다. app 외 arbitrary internal-module import 가능성은 D01과 같은 한계다.
- **의존/호환:** JS Date/Math만 사용, 호출·module 초기화 부작용 없음. persisted 날짜·서버 월 계산·API contract는 영향받지 않는다. 다른 Date 계산을 이 함수로 합치는 작업은 포함하지 않는다.
- **검증:** 기존 `utils.test.ts`, `money.test.ts` 및 TS unused/type check·Vite build. 제거 후 symbol 잔존 소비·public export 약속이 발견되면 보류. 날짜 correctness 신규 감사/대체 구현은 불필요하다.

### P3-D03 — badge field forwarding wrappers

- **이유/범위:** [MonthEntryCard:247](../../mobile/lib/src/screens/month_entries_screen.dart:247)의 두 메서드는 각각 `return entry.isTransport`, `return entry.isToll`뿐이다. callsite95/97에서 같은 필드를 직접 읽는 표현으로 정리할 수 있다. dead function이 아니라 **동일 library의 순수 forwarding 중복**이다.
- **증거:** 화면은 HomeShell의 tab2에서 실제 사용되고 helper는 badge 조건에서 각각1회 호출된다. screen 파일은 part library가 아니며 private card/helper의 외부 override·callback registration·다른 참조가 없다. [models.dart:152](../../mobile/lib/src/models.dart:152)의 final bool은 서버 wire `is_transport/is_toll`에서 온다. 문자열로 교통 여부를 새로 추론하는 변경은 금지다.
- **범위/호환:** 약6줄 helper+2개 조건 표현만, state/identity/financial/model/parser/dependency 변경 없음. P1-01 lazy-widget 실험 재개나 성능 개선 주장도 없다. frozen artifact를 고치지 않고 현 screen의 scoped 허용 여부를 구현 승인 때 확인한다.
- **검증:** 기존 tracked `mobile/test/offline_widget_submit_test.dart`의 기존 row net edit·form 보존, model test를 직접 host runner로 수행할 수 있다. 기존 untracked `p1_01_month_entries_test.dart`는 소유자 자료로 보존하고 유일한 증거로 의존하지 않는다. 교통/통행/일반 row의 badge 유무 control이 현재 coverage에 부족하므로 승인된 작은 widget assertion이 필요하다. badge/row identity가 달라지면 reject한다.

## 6. Group B — 현재 삭제 확정 불가

### P3-D04 — 호출되지 않는 금융 reset helper

- **선언/증거:** [card_payments.py:798~825](../../backend/app/services/card_payments.py:798), module-level private function, decorator0. Python AST·지원 backend/scripts/tests·앱 route imports/export 전체에서 호출/alias/문자열 dispatch가 없다. `routers/card_payments.py`는 공개 services를 직접 등록하고 helper를 등록하지 않는다. 현재 `set_discount_month_policy`는 설정을 저장한 뒤 status를 반환하며 이 함수로 분기하지 않는다. `clear_entry_discount`는 별도의 `_delete_entry_discount_events`를 직접 사용하므로 그 내부 helper는 삭제 대상이 아니다. target module에 getattr/globals/importlib dispatch가 없다.
- **숨은 소비/side effects:** 외부 private-FQN 호출은 미관찰. [폐기된 과거 Claim 제거 계획](claim-removal-plan-superseded.md)에 미래 제거 경계로 이름이 남아 있다. 호출 시 discount event 삭제·원장/claim override UPDATE를 수행하는 금융 코드이므로 단순 grep 결과로 바꾸지 않는다.
- **범위·호환:** 독립 감사가 현재 지원 graph의 불도달과 가이드의 오래된 설명을 확인한 경우에만 함수28줄+해당 가이드 참조 정리가 가능하다. 금융 공식·active service·schema·endpoint·claim 기능 삭제는 금지다. source lock/운영 스크립트 소비 확인 전 구현 승인 아님.
- **검증:** `backend/tests/test_card_payments.py`의 `test_discount_policy_is_separate_for_owner_and_family_cards`, `test_current_entry_manual_discount_survives_disabled_month_policy` 등 할인/월 상태·claim 보존 회귀와 Ruff/import check를 최소 제안한다. 직접 이 unused helper를 실행하는 새 시험이나 DB 변경은 이번에 하지 않았다. A 뒤의 조건부 audit 대상이며 현재 안전 삭제로 확정하지 않는다.

### P3-D05 — recentEntries

- **선언/증거:** [app_state.dart:204](../../mobile/lib/src/app_state.dart:204)는 `expenseEntries.take(5).toList()`다. lib/test/scripts 직접 소비는 찾지 못했고 홈 [input_screen.dart:25](../../mobile/lib/src/screens/input_screen.dart:25)는 `expenseEntries.take(10)`을 사용한다. public getter이며 private symbol과 달리 외부 subclass/harness 소비를 닫아 증명할 수 없다.
- **범위/위험:** getter1줄 후보이나 protected AppState의 공개 면이며 `expenseEntries`의 filtering/sorting·invalidation·publication은 그대로 두어야 한다. P1-U나 파생 상태 성능 실험을 재개하지 않는다. 외부 harness·보호 source 허가가 먼저라 현재 DEFER다.
- **검증:** 장래 승인 시 직접 host AppState/acquisition 테스트, 외부 harness import/API surface 확인 필요. 현재 unreachable 단정·성능 절감 주장은 없다.

### P3-D06 — unused Web API wrapper와 호환 export

- **증거/호환:** [panels.ts:51](../../frontend/src/api/panels.ts:51)의 `deletePanelsByType`는 현재 Web source consumer가 없지만 `api/index.ts→api.ts`의 star export에 포함된다. roadmap §7은 facade를 MUST PRESERVE로 두고 [compatibility-inventory](../guides/compatibility-inventory.md)는 외부 import 계약을 신중히 다룬다. 개별 wrapper의 외부 consumer 범위는 미확인이다. 내부 zero-use를 public export의 안전 삭제로 확대하지 않는다.
- **side effects/범위:** 호출되면 실제 destructive DELETE `/api/month/current/panels/type/{type}`를 전송한다. wrapper 약3줄만 잠재 범위이고 backend route·모바일 API·패널 기능 삭제는 해당하지 않는다. hidden consumer/지원 export 철회 결정 전 UNKNOWN·DEFER다.
- **검증:** 장래 별도 승인 시 facade export·외부 imports 및 Web type check, `usePanelHandlers`·panels endpoint 테스트. 외부 호환을 증명 못하면 남긴다. 이번 네트워크 요청0개다.

## 7. Group C — 정리 대상으로 추진하지 않음

### P3-D07 — sqlite3와 “import가 없는” dependency

- **실제 경로:** `mobile/pubspec.yaml:sqlite3 → segmented/store.dart:ClientStore`의 import/DB 접근은 part library와 isolated tests/adapters에 연결된다. 정상 JSON OfflineStore가 SQLite를 사용하지 않는다는 사실은 dependency 불필요 증거가 아니다. native packaging·tests·source locks에도 영향이 있다.
- **처분:** 제거 범위0, 관련 code/lock/native·experimental contract 보존. `crypto`, `archive`, http/plugins는 현재 N01/엄격 admission/backup에서 활성이고 `flutter_lints`는 analysis_options include로 사용된다. Python PyYAML·npm parser/types/plugin도 §2의 runtime/build 소비가 있어 unused dependency 확정0개다. 관련 기존 isolated-store/response-coding tests·build가 보호 증거이며 별도 실험 폐기 승인 없이는 제거 검증을 시작하지 않는다.

### P3-D08 — gzip 두 pass는 중복 제거 대상 아님

- `mobile/lib/src/response_coding_client.dart:send/_VerifiedOutput`는 API client의 두 GET에서 도달한다. archive는 trailer/CRC/ISIZE를, 독립 SDK는 reserved DEFLATE/final structure를 검증하며 output 비교까지 필요하다. 같은 검증 두 번이라는 가정은 N01-A01/R1 재발을 낳는다.
- side effects는 검증 실패 전 successful bytes 차단이다. 범위0·dependency/HTTP/admission 계약 유지, 기존 `response_coding_test.dart`, `response_coding_transport_test.dart`, `response_coding_deflate_test.dart`와 수용 근거를 보존한다. 성능 비용이 있다는 이유로 제거하지 않는다. N01 재감사/구현은 재개하지 않는다.

### P3-D09 — compatibility facade·historical schema·legacy acquisition

- `backend/app/repository.py:__all__`, `services/discounts.py`는 alias facade이고 `frontend/src/api.ts`, `components/LedgerTables.tsx`도 호환 export다. 중복 구현이 아니다. repository facade는 T5에서 DEPRECATE·테스트 소비, discounts shim은 UNKNOWN/DEFER·test_card_charge 소비이며 삭제는 별도 release 판단이다. LedgerTables는 현재 production imports가 있어 KEEP이다. 이 처분을 모두 같은 KEEP 규범으로 바꿔 쓰지 않는다.
- `services/snapshot.py:_normalized_snapshot_data`, `db_migrations.py:initialize_database/_admit_unversioned_legacy`의 versioned 경로, `api_client.dart:loadSession`의 SharedPreferences→secure storage migration, `CoherentRefreshCoordinator.acquireLegacyForDiagnostics`는 legacy 파일·외부 client·회귀 oracle로 도달한다. “현 앱이 새 형식을 쓰지 않음”은 제거 근거가 아니다.
- 형식/계정/DB/strict admission 영향이 커 범위0·KEEP다. 기존 snapshot/migration/auth/authoritative equivalence 시험과 compatibility inventory를 보존한다. legacy cutoff·외부 지원 종료가 승인되기 전 삭제 검증도 제안하지 않는다.

### P3-D10 — Dart part의 false unreachable

- `segmented/store.dart`의 part declarations가 `store_publication.dart`, `store_read.dart`, `store_frozen.dart`를 같은 library로 묶는다. `_acceptedChecksum`은 publication603에 선언되고 store187·frozen35/71·publication263/422에서 사용된다. `_PatriciaEdit`는 `patricia_edit.dart`에 선언되고 `incremental_verification.dart:289`에서 생성된다. verification 역시 part library다.
- 자동 파일별 private-name count의 오탐이며 registration/ownership/checksum side effects가 있다. 범위0·KEEP, 기존 segmented/adapter/isolation tests와 source lock을 보존한다. 해당 experimental 경로의 채택/삭제는 이번 discovery로 결정하지 않는다.

### P3-D11 — 드물게 쓰는 maintenance CLI

- `backend/scripts/clean_panel_dates.py:main`은 `if __name__=='__main__'`와 argparse `--db/--year`로 실제 도달 가능하다. `_ensure_columns`는 그 main에서 호출한다. default DB 경로·UPDATE·ALTER가 있어 discovery 중 실행하지 않았다. 코드 내 import consumer가 없다는 것은 dead 증거가 아니다.
- 실제 운영자의 과거/향후 사용·외부 cron은 **UNKNOWN**, 폐기된 과거 `claim-removal-plan-superseded.md`와 격리 maintenance 이력에도 언급된다. confidence LOW이며 안전 삭제 추천을 REJECT한다. 범위0, 향후 owner가 폐기를 별도 판단할 때 external runbook·compatibility 사용과 합성 DB 검증이 필요하다. `create_user.py`, deploy/release/dev/canonicalization scripts도 등록 CLI·운영 복구 책임 때문에 보존한다.

### P3-D12 — fixture·historical evidence·generated/asset 등록

- `backend/tests/fixtures/snapshot_v4_recurring.json` 등은 지원 format·restore tests의 입력이고 `mobile/test/response_coding_deflate_test.dart:storedWitness`·N01 raw payload/runner는 실제 실패를 재현한다. fixture가 현 export에서 생성되지 않거나 host 환경변수 없이는 skip된다는 사실로 obsolete라 할 수 없다.
- `scripts/benchmarks/*`, B03 source locks, 기존 미추적 devicegate 자료, pubspec assets·`frontend/index.html` icon·Gradle/native manifest 소비를 보존한다. dynamic asset loader와 외부 독립 감사가 hidden consumer다. 범위0, artifact integrity·호환 회귀 계약 때문에 제거 추천을 REJECT한다. cache·DB 용량 정리는 다른 위생 작업이며 source cleanup으로 섞지 않는다.

## 8. 독립 감사·향후 검증 shortlist

1. **P3-D01 → P3-D02:** 현재 Web graph가 닫혀 있고 public compatibility 약속이 없다는 판단을 확인한다. 승인 시 두 작은 unused 함수만 제거, 모듈/다른 export/handler는 유지. `npm --prefix frontend run lint`, `npm --prefix frontend test -- src/utils.test.ts src/money.test.ts`, `npm --prefix frontend run build`를 task-owned 사본/허용 cache에서 수행한다.
2. **P3-D03:** source의 bool field forwarding·private scope를 확인한다. 승인 시 직접 field 표현과 badge positive/negative controls 및 기존 row edit/submit 회귀를 **직접 host engine runner**로 검증한다. recipe는 N01 implementation evidence의 host_runner와 SDK package config를 재사용할 수 있다. Flutter CLI·ADB 대체 실행이나 P1 lazy-widget 재실험은 금지한다.
3. **P3-D04는 별도 조건부:** 금융 helper의 caller 부재와 guide 소비·source 권한을 확인한 뒤에만 다음 소규모 삭제 대상으로 판단한다. 예시 host 명령 `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 TMPDIR=TASK_SCRATCH .venv/bin/python -m unittest tests.test_card_payments`, 이후 ruff check(사용 가능할 때 `--no-cache`, fix 없음). 실제 DB/운영·금융 로직 수정 없이 검증한다.

A가 모두 통과해도 삭제 자동 승인은 아니다. 새 consumer·registration·compat 요구가 나오면 해당 후보를 내려놓는다. 삭제 함수 자체를 실행하는 형식적 테스트, full audit, broad 성능 campaign을 요구하지 않는다. B05/06과 C는 shortlist에 넣지 않는다.

## 9. 미해결 질문·명시 제외·정지

- D04의 문서상 미래 기능 제거와 외부 private CLI 사용 여부, D05 외부 harness/보호 AppState 권한, D06 supported export consumer cutoff는 미확인이다. 이를 확인하지 않고 안전 삭제로 승격하지 않는다.
- Phase2 전체 closure 문서가 없는 점은 §1에 기록했다. 현재 authorizing message는 Phase3 후보 조사만 허용하므로 cleanup 구현·Phase4·Production으로 전환하지 않는다.
- P1-S/U·P2-N02 DEFER는 새 근거가 없어 재개하지 않았고 N03/04/05·Web 성능·Snapshot 확장성도 제외했다. claim/family의 제거 시점·금융 알고리즘·old Snapshot/DB 지원·독립 gzip 검증을 바꾸지 않는다.
- runtime profiling, Flutter analyzer/빌드, 운영/외부 consumer 확인은 이번에 수행하지 않았다. TS diagnostic0은 기능 회귀 PASS가 아니다. 자동 검사 결과와 유력 항목의 수동 검증을 넘어서 전 repository의 dead-code 부재를 증명한 결과도 아니다.

**다음 행동 하나: Independent Phase3 Candidate Audit — A3개를 우선, D04를 조건부 검토.** 구현·삭제·dependency 조정은 owner의 별도 승인 뒤에만 가능하다.

## 10. 시작 상태·source identity 증거

시작 index staged0, tracked dirty13개. git porcelain의 directory-collapsed untracked entry는91개이며 별도 clean/stash하지 않았다. 전체 시작 porcelain SHA-256은 `f0dd9bebf21810a7c94fc53995c60054c3ef79e1ec49b38d7e348aa8d4e435d4`다. 기존 미추적 devicegate/벤치마크/시험은 후보 삭제 승인에 포함되지 않는다. 원래 tracked dirty 경로:

```text
AGENTS.md
backend/isolated_sync/observation.py
docs/benchmarks/t66f-b02-implementation/server.py
docs/benchmarks/t66f-b03/counters.py
docs/benchmarks/t66f-b03/server.py
docs/specimens/t66d3b-release-artifacts.json
docs/t66/b/t66b-hot-cold-design.md
docs/t66/c/t66c-delta-sync-protocol.md
mobile/android/app/build.gradle.kts
mobile/assets/segmented/isolated-release-artifacts.json
mobile/lib/src/segmented/protocol.dart
mobile/test/segmented_adapter_isolation_test.dart
mobile/test/support/logical_cost_sqlite.dart
```

주요 후보의 실제 working-source SHA-256(HEAD 동일을 가정하지 않고 직접 계산):

| 파일 | SHA-256 |
| --- | --- |
| `frontend/src/api/client.ts` | `270ea2bd6d76c7c02ffdd5c89202a76a1a4ba39f2d444e7a5ee5ff8d48d1b09d` |
| `frontend/src/utils.ts` | `33de397bac33d4efbd1ac5e4d38913f3b0c158f898a70a62e13110713df2ff0c` |
| `mobile/lib/src/screens/month_entries_screen.dart` | `f876b19c0872f533e226ab366ff45a8ce61fb0af568672aad9bdcd130cac5e81` |
| `backend/app/services/card_payments.py` | `434526deec871f58a638b7153a8515ed6575174bac15c254fb11454459be332b` |
| `mobile/lib/src/app_state.dart` | `c46a87a8b68507214a85966c3cc2c4f46df0d040de75b74e18c7954dea9d14bc` |
| `frontend/src/api/panels.ts` | `39992e5431a71e3e1eef8c96600cc96be4d288040d9b120357eaf08317fee1d6` |

<details>
<summary>비변경 TypeScript 후보 생성 진단의 재현 코드</summary>

아래를 task-owned `.cjs`에 저장해 repository root에서 Node로 실행한다. source 수정·emit·캐시 변경이 없는 Compiler API 검사다. callback/shorthand 오탐은 §3처럼 수동 배제해야 한다.

```javascript
const ts=require(process.cwd()+'/frontend/node_modules/typescript');
const path=require('path');const fs=require('fs');
const root=path.resolve('frontend');const config=ts.readConfigFile(root+'/tsconfig.json',ts.sys.readFile);
const parsed=ts.parseJsonConfigFileContent(config.config,ts.sys,root);
const program=ts.createProgram(parsed.fileNames,{...parsed.options,noEmit:true,incremental:false});const checker=program.getTypeChecker();
const sources=program.getSourceFiles().filter(f=>f.fileName.startsWith(root+'/src/'));
const decls=[];const usages=new Map();
function resolve(sym){if(sym&&(sym.flags&ts.SymbolFlags.Alias)){try{return checker.getAliasedSymbol(sym);}catch{}}return sym;}
for(const f of sources){function walk(n){
 if(ts.isIdentifier(n)){
  const s=resolve(checker.getSymbolAtLocation(n));
  const parent=n.parent;
  const isDecl=(parent.name===n&&(ts.isFunctionDeclaration(parent)||ts.isVariableDeclaration(parent)||ts.isClassDeclaration(parent)||ts.isInterfaceDeclaration(parent)||ts.isTypeAliasDeclaration(parent)||ts.isParameter(parent)||ts.isBindingElement(parent)))||ts.isImportSpecifier(parent)||ts.isImportClause(parent)||ts.isExportSpecifier(parent);
  if(s&&!isDecl){usages.set(s,(usages.get(s)||[]).concat(f.fileName+':'+(f.getLineAndCharacterOfPosition(n.getStart()).line+1)));}
 }
 if(ts.isFunctionDeclaration(n)&&n.name){decls.push([f,n,resolve(checker.getSymbolAtLocation(n.name))]);}
 ts.forEachChild(n,walk);
}walk(f);}
for(const [f,n,s]of decls){if(!(usages.get(s)||[]).length&&!f.fileName.includes('.test.'))console.log('TS_FN_NO_USE',path.relative(process.cwd(),f.fileName),f.getLineAndCharacterOfPosition(n.getStart()).line+1,n.name.text);}
console.log('TS_SOURCE_FILES',sources.length,'DECLARATIONS',decls.length);
console.log('TS_DIAGNOSTIC_COUNTS',ts.getPreEmitDiagnostics(program).reduce((a,d)=>(a[d.code]=(a[d.code]||0)+1,a),{}));
```

</details>

최종 보존 확인: 허용된 기존 문서2개 외 기존7,956개 파일 내용/링크가 동일하고 index는 staging 전 동일했다. 새 파일은 본 inventory 하나뿐이다. 재현 코드를 위에 보존하고 task runner0개 확인 후 이번 임시3개 파일(1,084,918B)을 정리했다. 기존 DB/cache·미추적 작업은 정리하지 않았다. A의 maintenance 이득은 unused export·단순 forwarding 제거이며 bundler가 이미 tree-shake할 수 있어 runtime 속도/bytes 이득은 주장하지 않는다.


## 11. D01–D03 scoped 구현 + Claim 유지 결정 — 독립 감사 인계

**구현·focused 검증 완료 / 독립 Audit 대기 / stage·commit·push 없음.** owner가 독립 후보 감사 기준 `phase2/mobile-network / efd1486aaab55ce87a11aa3d9eecd168300f8d4d`의 D01/D02/D03만 승인했다. 실제 branch/HEAD 일치, 대상3개 모두 audited SHA·HEAD와 동일하고 선행 수정0개였다. 기존 dirty13·untracked91와 index hash를 작업 시작에 기록했다.

| 항목 | 실제 변경·처분 |
| --- | --- |
| P3-D01 | `frontend/src/api/client.ts`에서 fileToBase64 선언만 제거. auth·다른 exports·Snapshot 동작 유지 |
| P3-D02 | `frontend/src/utils.ts`에서 daysBetween 선언만 제거. 다른 날짜/금융 utility 무변경 |
| P3-D03 | `month_entries_screen.dart` 두 badge callsite를 `entry.isTransport/isToll`로 직접 표현하고 pure forwarding 두 메서드만 제거. JSON/model defaults·분류 규칙 무변경 |
| P3-D04 | **DEFER, 구현 미승인.** Claim 유지 결정 아래 근거를 다시 평가하기 전 새로운 삭제 제안/구현으로 승격하지 않음. 과거 제거 예정이라는 사유는 더 이상 유효하지 않음 |
| P3-D05/D06 | DEFER, 구현·변경 없음 |

### Claim 문서 조정

2026-11-04 owner 결정 기록: Claim은 낮은 빈도의 정당한 비용 회수/가계 청구 기능으로 **새로운 명시적 결정 전까지 무기한 유지, 제거 일정·deprecation 없음**이다. 코드 활성화·UI 복원·개발·금융/할인 수정 승인이 아니다. 규범은 [domain-model의 유지 정책](../domain-model.md#claim-유지-정책), 현재 결정 기록은 [project-state](../project-state.md)다. Family Card의 별도 정책은 바꾸지 않는다.

`docs/guides/claim-removal.md`는 현재 가이드에서 제거하고, 기술 경계·당시 검토 자료를 잃지 않도록 원문 전체를 [claim-removal-plan-superseded.md](claim-removal-plan-superseded.md)에 **폐기된 역사 자료** banner 뒤에 byte-identical하게 보존했다. 과거 audit verdict를 수정하지 않았다. 현재 guides index·project/domain·Judgment 가이드·미래 재무 건전화 문서·roadmap은 Claim 제거를 승인된 미래 작업으로 제시하지 않는다. discovery 본문의 원 판단은 역사 기록으로 표시하고 이동한 가이드 참조만 연결했다. USB/device-interface의 `claim`이나 일반 사용자 청구 항목 삭제 API 설명은 제품 제거 정책과 달라 그대로다.

### 실행한 검증

| 검증 | 실제 명령·경계 | 결과 |
| --- | --- | --- |
| Web lint/TypeScript | task-owned frontend 사본에서 `npm run lint` (`eslint src`+`tsc --noEmit --noUnusedLocals --noUnusedParameters`) | PASS |
| Web focused tests | 같은 사본 `npm test -- src/utils.test.ts src/money.test.ts` | 2파일·7 PASS |
| Web Vite production build | 같은 사본 `npm run build` | PASS, 배포 없음 |
| Dart 분석 | SDK `dart analyze lib/src/screens/month_entries_screen.dart`, `dart analyze test/month_entry_badge_test.dart`, task-owned mobile context | 두 파일 No issues found |
| Badge control | 기존 직접 host engine runner, `month_entry_badge_test.dart` | 7 PASS: transport/toll/ordinary, 키워드+false, 누락/null defaults, 두 flag true |
| 기존 UI 회귀 | 같은 직접 runner `offline_widget_submit_test.dart` | 13 PASS: 기존 net edit·submit single-flight·draft·오프라인/오류 관련 기존 assertion 유지 |
| Backend panel 회귀 | `PYTHONPATH=backend PYTHONDONTWRITEBYTECODE=1 TMPDIR=TASK_SCRATCH .venv/bin/python -m unittest tests.test_panels` | 합성 임시 DB19 PASS |
| 문서·범위 | 이동 원문 bytes·Markdown inbound/links·Claim 정책 검색, task-only diff·SHA·index 비교 | 옛 filename의 Markdown inbound0, 현행 정책 및 archive links 정상 |

준비 단계에서 SDK가 지원하지 않는 `--no-fatal-infos` 옵션으로 첫 분석 명령이 exit64였다. source 분석이 시작되지 않은 CLI 준비 오류이며 수정된 명령의 두 분석은 통과했다. 이를 source failure나 PASS로 섞지 않는다. 실행 불가/새 회귀 실패는 없다. host debug widget 시험이 Android 실기기 검증을 대신한다는 주장은 하지 않는다. Flutter CLI/Android/ADB/emulator·운영 접근·배포는0이다.

사본의 package config와 writable build cache만 사용했다. 실제와 test source SHA를 대조했으며 original dependency/cache·기존 dirty 작업은 수정하지 않았다. 신규 badge 테스트는 row/action을 바꾸지 않고 화면에서 서버 bool을 소비하는 결과를 확인한다. Claim runtime source·backend/schema·AppState·D04/D05/D06은 무변경이다.

[검증 근거와 task-only review diff](../benchmarks/p3-d01-d03-validation.json.gz)에 시작 상태·대상 before/after SHA·실제 commands/runner·logs·scoped textual diff를 보존한다. source diff는 HEAD 기준의 관련 경로만이며 새 untracked test/archive도 포함한다. 원래 dirty13개는 diff에 포함하지 않는다. **Git index byte 보존, stage/commit/push 없음**을 최종 확인하고 owner가 독립 Audit Session에 이 장부와 실제 working diff를 전달한다. 다음은 독립 scoped implementation audit이며 새 후보/Phase4는 시작하지 않는다.

최종 범위 확인: 허용된 기존12개 경로 외 기존7,947개 파일/링크와 index bytes가 동일했다. 원 가이드 원문은 archive에 보존했다. raw·diff를 먼저 보존하고 task runner0개 확인 뒤 이번 scratch 파일/링크449개(논리324,990,657B, symlink139개)를 정리했다. dependency 링크 대상을 따라가 삭제하지 않았고 기존 cache/DB/미추적 작업은 삭제하지 않았다. production 코드3개 변경량은 **+2/-28**, 신규 badge 시험7건이며 그 밖의 수정은 정책·장부·목차·근거뿐이다.

## 12. Phase 3 수용·안전 게시

2026-11-04 owner는 D01–D03·Claim 무기한 유지 정책과 독립 scoped 감사 결과를 **ACCEPTED**로 승인했다. BLOCKER/MAJOR는 없고 유일한 MINOR **P3-A01**은 로드맵 §9의 4단계 상태를 **NOT STARTED — 별도 owner 승인 필요**로 고쳐 해결했다. §11의 감사 전·미게시 기록과 원 판정은 역사로 보존한다. D04–D06은 **DEFERRED**이며 D04는 Claim 유지 정책 아래 재평가하기 전 구현하지 않는다. 이 수용은 Phase4 시작·기기 gate 종결·main 병합·운영 배포 승인이 아니다.

### 게시 범위와 제외

시작 branch/HEAD는 `phase2/mobile-network / efd1486aaab55ce87a11aa3d9eecd168300f8d4d`, 기존 index는 비어 있었다. 현재 작업 시작 시 tracked 변경25개와 untracked 파일5,164개를 개별 경로로 목록화했다(일반 status에서는 미추적94개 파일/디렉터리 항목). 이 중 Phase3 승인15개 경로와 독립 검토된 기존 `AGENTS.md` 위생 지침1개, 로드맵이 직접 연결한 기존 합성 측정 요약5개를 포함한다. 추가 게시 검토 manifest1개를 합친 총22개 경로이며, 옛 가이드 삭제와 역사 archive 추가는 각각 센다. 다섯 요약은 B05 microbenchmark·B05A timing-comparison·B07 packet-timings·B08 packet-comparison·B09 cold-ab-results이며 원래 수치·한계·음성 결과를 수정하지 않는다. 원시 실행 자료 전체를 공개하거나 새 실험을 실행했다는 뜻은 아니다.

| 제외 사유 | 파일 경로 수 | 처분 |
| --- | ---: | --- |
| owner가 제외를 선택한 devicegate 보안 설정·연관 소스/근거 | 1,314 | 원위치 보존, staging 안 함 |
| segmented source·release lock·관련 시험의 결합된 기존 변경 | 20 | 부분 게시하지 않음. 보호 계약·의존 근거를 함께 확인하는 별도 게시 검토 필요 |
| 내용·재현 의존성 검토가 끝나지 않은 역사 실험 소스/근거 | 3,271 | 안전한 공개 여부를 추정하지 않고 보존 |
| 원시 로그·생성 산출물 | 418 | 민감정보 부재를 보장하지 않고 제외 |
| 키·인증서 자료 | 30 | 합성 여부와 무관하게 이번 공개에서 제외 |
| 시험 DB·압축 DB·WAL/SHM | 112 | DB에 연결·조회하거나 복사하지 않고 제외 |
| 로컬 host 파일시스템 목록 | 1 | 운영·로컬 상세 메타데이터 공개 불필요 |
| 기존 P1 계측용 시험 | 2 | 전용 환경변수/runner와 역사 소스 조건 검토 전 일반 시험으로 게시하지 않음 |
| **합계** | **5,168** | **원본 bytes·mode 보존 확인 후 게시** |

제외는 삭제·결함 판정이 아니며, 이 파일들을 새로 검증하거나 기존 gate 작업을 재개하지 않았다. 일반적인 비밀 패턴 검색만으로 모든 과거 증거를 공개 가능하다고 간주하지 않았다. [경로별 게시/제외 목록](../benchmarks/phase3-publication-review.json.gz)은 경로·사유·초기 해시/크기/모드만 담고 본문·키·DB·금융 자료를 담지 않는다. 기존 독립 검증 근거는 그대로 보존한다.

### 게시 전 확인

- D01–D03와 신규 badge 시험4개 source SHA가 §11의 실제 실행 근거 `after_sha256`와 일치한다. 해당 소스는 추가 수정하지 않았다. Web lint/TS·7 tests·Vite build, Dart 분석2개·badge7·Offline submit13·backend panel19 PASS는 **이전 실행을 재사용한 근거**이며 이번 게시 작업에서 새로 실행했다고 주장하지 않는다.
- Claim 원 가이드 body는 역사 archive 끝부분에 byte-identical하게 남고, 현재 규범은 domain-model의 무기한 유지 정책이다. Claim runtime 코드는 변경하지 않는다.
- 이번 추가 변경은 P3-A01·수용/게시 장부·목차 상태 및 기존 위생 지침뿐이다. 최종 stage를 경로별 허용 목록과 대조하고 전체 staged 내용(압축 근거의 내부 JSON 포함)을 검토한다. 비밀/개인정보·DB·키·예상치 못한 바이너리는 게시 대상에서 배제한다.
- 문서 링크·P3-A01·원문 보존·초기 제외 파일 해시/모드와 기존 index 항목 보존을 집중 확인한다. source가 달라지지 않았으므로 전체 회귀나 Phase4 감사는 반복하지 않는다.

### 게시 진행

안전 검토 후 Phase3 수용 작업과 기존 위생 지침을 논리적으로 나누어 commit/push한다. 원격 성공·SHA를 아래에 후속 기록한 뒤 Phase3를 CLOSED로 갱신한다. 현재는 **ACCEPTED / PUBLICATION PENDING**이며 Phase4는 미착수다.

### 최종 수용·종결 기록

위 문단은 게시 전 상태다. 두 게시 milestone의 실제 push 성공을 확인한 뒤 **Phase3 CLOSED**로 갱신한다.

| commit | 목적 | 원격 게시 |
| --- | --- | --- |
| `b8d07d096b5d70def4b1e59e75e2039e0d999c4b` | D01–D03·badge 시험·Claim 유지 정책/역사 archive·P3-A01·게시 검토 근거 | `origin/phase2/mobile-network` push SUCCESS, 당시 tip 일치 |
| `eb25f6b482e16b72afac209e573ea8904ab369d3` | 검토된 기존 위생 지침과 합성 측정 요약5개 | 같은 branch push SUCCESS, 당시 tip 일치 |

원래 D01–D03 source와 badge 시험의 SHA 일치를 확인해 독립 감사의 기존 PASS 근거를 재사용했다. 이번 실제 추가 검증은 **문서 상대 경로230개 정상·게시 제외 자료를 가리키는 신규 링크0·원 가이드 body 보존·P3-A01 수정·비밀 패턴 검출0·5,168개 제외 파일 bytes/mode 보존·전체 staged 내용/허용 경로 대조·diff check PASS**다. 링크 검사에서 source 링크의 `:줄번호`를 filename으로 취급한 첫 검사 오류를 수정했고, 미게시였던 역사 요약5개는 별도 내용 검토 후 두 번째 commit에 포함했다. source/test를 고쳐 검사를 통과시킨 것이 아니다. 초기 index 항목0개였고, 검토한 경로만 명시 staging/commit하여 unrelated 항목을 섞지 않았다.

종결 기록 반영 뒤에는 상대 경로 **231개**, 범위 밖 기존 파일 **7,941개**의 bytes/mode/링크 보존을 추가 확인했다. 게시 제외5,168개가 이 보존 집합에 포함된다. 게시 대상 전체22개 경로는 허용 목록과 일치하고 기존 staged 항목은 없었다. 같은 compact 게시 근거에 후속 검증 결과·검증 스크립트·두 push SHA를 덧붙여 scratch 정리 뒤에도 확인할 수 있게 했다.

Claim 정책은 무기한 유지, D04–D06은 보류이며 수용 작업의 검증·문서·게시가 완료되어 Phase3 한정 종료 조건을 충족했다. 모든 과거 조사·음성 근거·감사 판정은 유지한다. 남은 dirty/untracked 작업은 삭제하지 않았고 이번 종결의 수용 대상으로 주장하지 않는다. 이 후속 종결 문서도 같은 branch에 별도로 게시한다. 최종 원격 SHA는 게시 완료 보고와 Git commit 기록으로 확인한다.

**다음 행동은 별도 owner 승인에 따른 독립 Phase4 포괄 감사다. Phase4·main 병합·운영 배포는 미착수다.** 실기기/ADB·T6.9·formal T6.6F·G2/R1 등 기존 제한을 해제하지 않는다. 이번 작업은 대용량 시험 DB/build 산출물을 만들지 않았다. task-owned 소규모 검토 scratch만 필요한 경로/해시·검증 결과를 보존한 뒤 정리하며 기존 파일은 정리하지 않는다.
