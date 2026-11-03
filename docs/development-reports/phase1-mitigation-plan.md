# Phase 1 성능 완화 공유 계획·작업 장부

작성: 2026-11-03. **BATCH COMPLETE — R-01 NOT ADOPTED·원복, S DEFERRED·생산 미구현. 다음은 owner의 독립 Mitigation Audit다.** 이 문서는 계획 검토, 이후 승인된 구현, 감사 지적과 수정 결과를 계속 기록하는 단일 장부다. 현재 세션이 Implementation Session을 유지한다. 조건부 채택은 구현 승인이나 성능 개선 입증이 아니다.

## A. 범위와 기준선

### 현재 소스와 재사용 근거

- 실제 HEAD: `2b4e168ebf1d8ba8ce5c9a48d7257a24bbd0c8a7`. 작업 시작 tracked 변경 13개, staged 변경 0개, 기존 untracked 자료가 있다. HEAD 대신 아래 working-source를 설계 기준으로 삼았다.
- 시작 index SHA-256: `8f97ab0d1f8935e32fa23c6b3fb4827aaf830f1536da3e847f7915fc20879a9c`. 기존 7,943개 파일·symlink의 내용·mode·link를 보존 기준으로 기록했다. 기존 dirty `mobile/test/segmented_adapter_isolation_test.dart`도 작업 소유 파일로 간주하지 않는다.

| 현재 파일 | SHA-256 |
| --- | --- |
| `mobile/lib/src/screens/home_shell.dart` | `e2e4b53496b9950f27666377c6fae7543021cbf770ad412f31d6196b8aa4b5d4` |
| `mobile/lib/src/local_snapshot_repository.dart` | `316c491e512873b500e5417a4b5dff4ebf8885d6a398d5a57cf63b2c28d25432` |
| `mobile/lib/src/app_state.dart` | `c46a87a8b68507214a85966c3cc2c4f46df0d040de75b74e18c7954dea9d14bc` |
| `mobile/test/local_snapshot_repository_test.dart` | `a9e9d41875fd7c075dae85cfb8c422eba1895740bff9fc2fa7d16e3437791652` |
| `mobile/pubspec.lock` | `669da919f8110efd863187877d1990ead6d92dea6199ea77e3199edfce740988` |

현재 세 대상 생산 파일은 해당 P1 조사에 기록된 SHA와 일치한다. 조사 전체를 재실행하지 않았다.

| 근거 | 이번에 재사용하는 결론 |
| --- | --- |
| [로드맵](money-note-final-optimization-and-closure-roadmap.md), [P1-R](p1-r-mobile-refresh-performance-results.md) | 정상 14→1 GET 최적화 유지. 비인접 animation의 중간 refresh는 source-supported이며 실제 callback/HTTP 빈도는 미측정 |
| [P1-03](../p1-03-snapshot-save-validation-performance-results.md), [원시 근거](../benchmarks/p1-03-snapshot-performance.json.gz) | 합성 10k행·30개에서 save 7,866.068ms, 62회 read/decode/검증. 비용 귀속 B, 전체 **PARTIAL** 유지 |
| [P1-02](../p1-02-flutter-rebuild-derived-state-results.md), [원시 근거](../benchmarks/p1-02-flutter-rebuild-raw.json.gz) | 5k 변경 없는 알림의 필터·정렬 중앙값 2.2655~2.4900ms. 같은 build 안 중복은 없고 보호된 invalidation 경계와 연결됨 |
| [P1-01](../p1-01-monthly-expense-lazy-widget-results.md), [P1-04](p1-04-backend-sql-presenter-performance-results.md) | 각각 미채택·원복 / C·새 backend 구현 후보 0개. 다시 조사하지 않음 |
| [통합 근거](../benchmarks/final-optimization-and-closure-evidence.json) | 최초 경로 지도·역사 최적화·한계를 보존. C1 비용을 안전한 제거 후보로 자동 승격하지 않음 |

### 범위와 불변식

순서는 **1단계 UI·앱 처리 성능 → 2단계 모바일 전송량 → 3단계 dead code·중복 정리 → 4단계 최종 감사**, 다음은 별도 대형 Snapshot 확장성이다. 계획 작성 차수에는 문서·정적 확인만 수행했다. owner 구현 승인 뒤 실행 결과는 E와 milestone 기록에 누적한다. 운영 DB/API·배포는 계속 미승인이다.

금융 의미의 원본은 [domain-model](../domain-model.md), 신뢰·게시 경계는 [architecture](../architecture.md), pending/reconciliation은 [offline-mode](../offline-mode.md)다. 서버 금융 authority·exact money·strict admission·revision/generation/auth·durable pending·Offline reconciliation·원자적 baseline 교체·Snapshot 복구·UI 게시 순서·mutation 완료 의미를 유지한다. 정상 모바일 baseline은 **JSON 파일**이며 SQLite로 바꾸지 않는다. 모바일 독립 금융 재계산을 추가하지 않는다. Snapshot 작업은 [security](../security.md)·[runbook](../runbook.md)의 백업/복원 경계도 유지한다.

F01 BINDING—UNRESOLVED, 유효 G1, G2 미채택, operational ADB 차단, 실기기·에뮬레이터/T6.9 보류, formal T6.6F 미종결, R1 CLOSED·배포 미승인은 그대로다. Android/ADB/기기 탐색을 유발하는 CLI는 실행하지 않는다. P1-03의 Flutter 자동 진단에 의한 ADB 기동·작업 소유 PID 종료 사건은 원 보고서에 보존하며 새 gate 작업을 열지 않는다.

후속 구현 전 현재 SHA·diff·보호 규칙을 다시 확인한다. 이 문서와 다른 소스이면 해당 차이만 확인해 가정을 재판단하며, 기존 변경을 덮어쓰지 않는다. 검증된 host 전용 runner를 사용하고 Android 탐색을 피할 수 없으면 그 측정은 차단으로 기록한다. 임시 fixture는 작업 소유 디렉터리만 사용하고 [산출물 위생](../development-artifact-hygiene.md)을 따른다.

### 공통 측정·처분 원칙

동일 fixture/도구/host와 동일 관측 코드를 양쪽에 적용한다. 초기화·fixture 생성·warmup은 측정 밖이다. 실제 Stopwatch wall time과 작업 수를 기록하며 중첩 타이머를 합산하지 않는다. debug JIT·가상 frame 간격을 release/단말 frame 성능으로 표현하지 않는다. 원 표본·fixture/source/toolchain SHA·실행 순서는 후속 단일 `docs/benchmarks/phase1-mitigation-evidence.json.gz`의 R/S 항목에 누적하고 여기서 연결한다. M1부터 생성하며 결과 보고서를 과제마다 만들지 않는다. 기존 원시 근거는 수정하지 않는다.

원칙은 warmup5·표본20·교대3블록이다. 고비용 P1-S는 아래 사전 축소 설계를 사용한다. 이 차이는 결과를 본 뒤 기준을 낮추는 것이 아니다. 중앙값은 각 블록에서 비교하고 p95는 nearest-rank로 계산한다. 소표본 p95는 최댓값임을 표시한다. 시간 예산·표본을 충족하지 못하거나 결과가 혼재하면 미채택/보류로 끝낸다. 성공 기준을 사후 완화하거나 다음 후보를 새로 찾지 않는다.

## B. 완화 backlog

검토 후보는 **3개**다. 계획 당시 조건부 R/S·보류 U였으며, 실행 후 R은 미채택·원복, S는 비용 조건 실패로 보류, U는 기존 보류를 유지했다. 생산 채택0개다.

| ID | 결정 | 우선순위 | 대상 | 상태 | 감사 |
| --- | --- | --- | --- | --- | --- |
| P1-R-01 | NOT ADOPTED | 완료 | 비인접 하단 탭 선택만 직접 이동 | 3블록 p95 기준 미달·UI 원복 | Planning Audit PASS, batch 감사 대기 |
| P1-S | DEFER | 완료 | 한 save 안의 SHA content receipt | digest 비용 조건 실패·생산 미구현 | Planning Audit PASS, batch 감사 대기 |
| P1-U | DEFER | 후속 구현 없음 | expenseEntries invalidation/파생 view | 위험·이득 대비 보류 | owner 유지 |

순서는 **Planning Audit → 소유자 범위 승인 → P1-R-01 측정/처분 → P1-S 조건 확인·측정/처분 → 변경분 Mitigation Audit**다. R 미채택은 S의 착수를 막지 않으며, S에는 독립적인 보호 소스 승인이 필요하다. U를 대신할 새 후보는 찾지 않는다.

## C. 구현 명세

### P1-R-01 — 비인접 하단 탭의 중간 refresh 방지

1. **문제·근거:** `_selectTab → animateToPage → 중간 onPageChanged → _handlePageChanged → refresh*Area → 전체 bundle`이다. 0→4에는 최대3개 중간 진입 기회가 있으나 HTTP가 실제 전송되는지는 미측정이다. P1-02의 jump 1→2→0 약5.55초를 중복량·절감량으로 쓰지 않는다.
2. **사용자 이득:** 선택하지 않은 중간 화면의 실제 취득을 줄이고 목적지 도달·fresh 상태 게시를 앞당길 가능성이다. 비인접 메뉴 선택의 이동 animation이 없어지는 UX 변경을 승인 범위에 명시한다.
3. **구현 방향:** baseline 조건이 통과한 경우에만 `_selectTab`에서 `abs(value - index) > 1`에 `jumpToPage(value)`를 사용한다. 현재 탭 선택의 no-op, 인접 탭의 기존 240ms animation, 수동 swipe와 최종 `onPageChanged` refresh는 그대로 둔다. refresh 차단 flag·목적지 외 callback 무시·TTL·일반 coalescing은 추가하지 않는다. 빠른 상호작용에서 이 작은 분기만으로 불변식을 유지하지 못하면 설계를 확대하지 않고 거부한다.
4. **대상:** `mobile/lib/src/screens/home_shell.dart:_selectTab`. 직접 관련 host widget 회귀/계측은 신규 `mobile/test/p1_r_navigation_test.dart` 하나에 둔다. `offline_widget_submit_test.dart`, `offline_refresh_test.dart`, `authoritative_acquisition_test.dart`, `authoritative_rebuild_pending_test.dart`의 기존 관련 회귀를 재사용한다. 과거 P1 실험 파일·근거를 편집하지 않는다.
5. **보호 영향:** HomeShell은 확인한 명시 P0 보호 목록 밖이다. AppState/coordinator/OfflineStore/API·source-lock 변경은 불허다. 테스트는 실제 이 경로를 호출하고 HTTP client 경계만 관측하며 별도 fake refresh 구현으로 대체하지 않는다.
6. **불변식:** 목적지에 실제 진입하면 필요한 authoritative refresh를 수행하고 최종 index/화면이 일치한다. 인접 이동·swipe·동일 탭 재선택, 명시 refresh, mutation 완료, pending/reconciliation·인증/세대·실패 후 재시도·durable 게시를 유지한다. 기존 행 identity·draft/focus의 수명도 유지한다.
7. **baseline:** 기존 유효 금융 bundle fixture로 current expense **50/1,000행**, viewport400×800·text scale1.0을 고정한다. synthetic HTTP transport와 임시 JSON OfflineStore를 사용한다. 각 표본은 정착한 0번에서 메뉴 **0→4→0**을 선택하며 각 leg의 최종 취득/게시 완료를 기다린다. 16ms씩 명시적으로 pump하여 240ms animation 전체를 관측한다. 한 번의 큰 pump로 중간 callback을 건너뛰지 않는다. 기본 응답은 무지연이며 고정 지연150ms 조건은 겹침 계수 확인용 별도 1회로 제한한다. 가상 지연을 wall time에 더하지 않는다.

   `onPageChanged` 값/시각, refresh 진입, coordinator acquire, 실제 `http.Client.send`의 GET URI·요청 ID, admission, baseline 교체, UI 게시·종료를 별개로 기록한다. API fake 호출 수만으로 실제 GET 수라 부르지 않는다. 계측은 test subclass/transport·테스트 전용 observer로만 한다. 각 leg 시작→목적지 baseline 게시 후 settled pump까지 실제 wall time을 잰다. startup/이전 leg를 측정 창에 섞지 않는다.

   첫 A 블록은 **생산 코드 변경 전에** warmup5+측정20이다. 두 규모의 양 방향에서 각20표본 모두 목적지 외 실제 GET이 적어도1회 있어야 구현 조건을 통과한다. 충족하지 못하면 **NOT ADOPTED**로 기록하고 변경하지 않는다. 실제 앱 입력·비용과 다른 전이를 만들어 조건을 맞추지 않는다.
8. **성능·기능 수용:** 동일 runner로 A/B, B/A, A/B 3블록, 각 variant warmup5+측정20. 비교 사본은 검증한 before-image에서 만들며 git checkout/reset을 쓰지 않는다. 전체 측정 상한 **600초**다. 측정하는 정상 온라인·pending 없는 fixture에서는 매 표본 중간 GET0·최종 목적지 GET1, 관련 admission/게시가 목적지 상태에 연결되어야 한다. 양 방향·두 규모의 전체 leg wall 중앙값이 **모든 블록에서 감소**해야 한다. 0→1/1→0 인접 이동·동일 탭 대조도 같은 표본 수로 측정하고 wall p95는 각 baseline의110% 이하여야 한다. 요청 감소와 latency 감소는 따로 보고하고 실제 RTT·단말 성능 개선으로 확대하지 않는다.
9. **회귀:** 정방향/역방향 비인접 이동, 인접 이동, 수동 swipe, 동일 탭, 이동 중 재선택·0→4→0 연타와 animation 도중 탭 선택, dispose, 부모 notify 후 selectedIndex/실제 화면 일치를 확인한다. 명시 새로고침/실패 후 retry·로딩/오류 표시, 입력 draft·focus/편집 상태, 행 category/net/delete 대상, Offline disabled·예상값을 기존 focused 테스트로 확인한다. mutation/auth/generation/durable 경계의 기존 직접 관련 회귀도 통과해야 한다. 비인접에서 새로 중간 화면/요청이 끼거나 기존 인접·swipe 의미가 바뀌면 실패다.
10. **거부·복구:** HTTP 조건 미충족, 목적지 freshness/identity 회귀, 혼재/불확실한 시간 결과, p95 초과, 보호 소스 변경 필요 시 미채택 또는 권한상 보류다. 이미 구현했다면 현재 파일과 task diff를 대조해 **해당 UI 변경만** verified before-image로 복구하고 관련 기능 회귀를 재확인한다. 다른 변경을 덮어쓰거나 무관한 staged 항목을 조작하지 않는다. owner가 승인한 명시 경로 stage·commit·push만 수행한다.
11. **의존·순서:** 계획 감사·소유자 UI 실험 승인 이후 첫 과제다. 검증된 host runner/유효 fixture가 없으면 BLOCKED로 처분한다. 네트워크 설계나 S/U 구현을 선행 조건으로 추가하지 않는다.

### P1-S — 한 save 안의 내용 기반 검증 결과 재사용

1. **문제·근거:** 현재 `save → pending 쓰기/독립 readback → rename → _prune(list) → 반환 list`에서 보관 파일을 두 번 읽고 UTF-8/JSON/envelope 검사한다. 합성 v7 10k행·5,934,477B·기존30개에서 save 중앙값7,866.068ms, save+공개 list 11,566.156ms였다. 62회/92회 검사는 같은 이름만으로 모두 중복인 것이 아니다. P1-03 n3·host JIT·계측 overhead·전체 PARTIAL 한계를 유지한다.
2. **사용자 이득:** 보관량이 많을 때 자동/수동 Snapshot 저장의 동기 decode 부담을 낮출 가능성이다. startup 전체·Android UI 정지·큰 Snapshot 전송 비용 개선을 미리 주장하지 않는다.
3. **구현 방향·수명:** 생존 `LocalSnapshotInfo` 목록을 그대로 반환하는 안은 채택하지 않는다. **마지막 directory 열거·파일 전체 read·새 stat·정렬을 유지**하고, 동일 save의 첫 prune 순회에서 검증한 내용과 같을 때만 UTF-8/JSON/envelope 해석을 재사용한다.

   첫 순회에서 기존 full validation과 stat이 모두 성공한 파일에 한해 실제 전체 경로·byte 길이·검증한 bytes의 SHA-256을 작업 로컬 receipt로 기록한다. digest는 **첫 검사에 사용한 바로 그 bytes**로 계산하고 stat까지 성공한 뒤 등록한다. 나중에 다시 읽은 미검증 bytes에서 receipt를 만들지 않는다. 기존 `crypto` 의존성을 사용하며 parsed tree·payload bytes를 보관하지 않는다. receipt는 최대31개만 받는다. 더 많은 파일은 정상 검증하되 receipt 없이 처리하고, prune 뒤 삭제된 항목을 제거하여 생존 receipt만 최대30개 남긴다. 이 상한은 후보 선택/retention 정렬을 바꾸지 않는다. cap 때문에 receipt가 없는 생존 파일은 마지막 순회에서 정상 검증한다.

   마지막 순회는 **새로 열거한 파일을 다시 전체 읽고**, 길이와 SHA-256이 같은 경로의 receipt와 모두 같을 때만 이미 성공한 해석 결과를 쓴다. miss·새 파일·다른 directory·다른 내용이면 현재 canonical validator로 full validation한다. 이후 fresh stat으로 metadata를 구성하고 기존 순서로 정렬한다. 같은 크기/mtime만으로 hit를 인정하지 않는다. symlink/rename·삭제 후 재생성도 실제 읽은 내용으로 판단한다. receipt는 그 save 반환/실패와 함께 폐기하고 다른 save/list/세대/프로세스에 공유하지 않는다.

   새 pending의 expectedBytes 전체 동일성/readback·검증은 별도이며 이 receipt로 대체하지 않는다. 첫 prune 검증도 생략하지 않는다. 공개 `list`, `safeFile`, share/read/delete/restore 호출은 매번 기존 full validation을 수행한다. 검증 로직을 private helper로 공유할 수 있으나 envelope/형식·예외 규칙을 바꾸거나 금융 검사를 복제하지 않는다. 해시 일치는 기존 SHA-256 내용 식별 가정에 따른 해석 재사용 근거이며 서버 출처나 금융 진실의 증명이 아니다.
4. **대상:** 보호된 `mobile/lib/src/local_snapshot_repository.dart`의 `save/_prune/list/_validateSnapshotFile` 내부 연결과 private receipt/helper만이다. 공개 API는 유지한다. 기존 `mobile/test/local_snapshot_repository_test.dart`의 IOOverrides fault fixture를 확장하고 신규 `mobile/test/p1_s_snapshot_performance_test.dart` 하나에 계측을 둔다. 보호 검사 조정은 다음 항목의 파일/범위에 한정한다. AppState·SnapshotManager·OfflineStore·서버·schema·Snapshot 형식은 변경하지 않는다.
5. **보호 영향·사전 조건:** Planning Audit와 **소유자의 보호 파일 scoped 구현 승인 후에만** 바꾼다. 현재 `segmented_adapter_isolation_test.dart`는 protected-source의 과거 exact SHA를 직접 요구하므로 생산 파일 승인만으로 이 검사를 무시할 수 없다. 승인 범위에 이 파일의 **P1-S 대상 한 곳에 대한 현행 reviewed SHA 검사 조정**도 포함해야 한다. 기존 dirty 부분을 보존하고 새 소스 SHA와 과거 원본 보존을 함께 확인한다. `protected-source.json`·B03 lock/archive·과거 승인 hash는 수정하지 않고 다른 파일의 보호도 풀지 않는다. 이 좁은 조정을 허용하지 않으면 구현을 DEFER한다. 별도 gate 체계를 만들지 않는다.
6. **불변식·무효화:** 쓰기 flush·exclusive pending·독립 byte readback·rename·finally 정리·활성 pending 보호·retention30·오래된 파일 삭제 순서를 유지한다. 마지막 열거/새 read/새 stat이 있으므로 동시 save/delete, 내용 변경, 읽기/JSON/stat 실패를 기존과 같이 관측한다. 내용 변경은 digest miss 후 full validation, 파일 부재/접근 실패는 기존 FileSystemException 경로, malformed 내용은 기존 FormatException 경로다. 유효한 새 내용은 새 검사와 metadata를 사용한다. 내용이 같은 재생성 파일은 fresh stat을 사용한다. 전역 lock이나 persistent cache를 추가하지 않는다. 현재도 read와 stat 사이에 변경될 수 있는 관측창을 더 강한 원자적 directory snapshot 보장으로 표현하지 않는다.
7. **baseline·구현 전 비용 조건:** P1-03 근거의 유효 서버 v7 fixture와 생성기·관계·서로 다른 ID를 그대로 재사용한다. 보관0/1/10/30개 ×376/1k/5k/10k행, payload228,687/597,474/2,969,474/5,934,477B를 SHA로 확인한다. 과거 시간은 참고이며 현재 A를 새로 잰다. 설치된 도구를 시작하지 않고 파일로 toolchain을 확인한다.

   생산 변경 전 같은 bytes로 SHA-256·UTF-8/JSON/envelope의 동기 비용을 구분해 한정 교정한다(상한60초). C30의 추가 digest 약61회와 부수 비용이 제거 예정30회 full decode/envelope보다 작아야 한다. 이 부등식이 5k·10k에서 재현되지 않으면 전체 구현·캠페인 없이 **NOT ADOPTED**다. micro 결과는 전체 save 개선 증거가 아니다.

   원 구현의 A baseline을 먼저 확보한다. full matrix는 각 operation(`list`, `save`, `save+공개 list`) 1회씩 count/bytes/동작을 확인한다. 통계는 C30의5k save·10k save·10k save+list 세 구성에 한정하여 variant별 warmup1+측정3, 교대 A/B·B/A·A/B 세 블록으로 수집한다. p95는 n3 최댓값이다. 작은 대조는 376/1k ×C0/C1의 save와 공개 list에 warmup5+측정20을 같은 세 블록에 적용한다. 매 표본 전에 작업 소유 fixture directory를 원래 C로 재구성하고 준비 시간은 제외한다. 후속 별도 공개 list를 save 내부 반환과 혼동하지 않는다.

   교정 이후 전체 비교 상한은 **900초**, 기존 시간에 따른 예상은 약10~15분이다. 원 구현 A와 B를 별도 작업 사본에서 같은 계측으로 교대한다. 예산이 모자라면 결과를 INCONCLUSIVE/미채택으로 남기고 임의 표본 축소·추가 대규모 측정을 하지 않는다.
8. **성능·기능 수용:** 다음 계수는 모든 파일이 유효하고 변하지 않으며 receipt를 확보한 경우의 기대값이다. read 수를 줄인 것으로 보고하지 않는다.

   | 기존 C | save read 전/후 | full JSON/envelope 전/후 | save+공개 list full JSON 전/후 |
   | ---: | --- | --- | --- |
   | 0 | 3 / 3 | 3 / 2 | 4 / 3 |
   | 1 | 5 / 5 | 5 / 3 | 7 / 5 |
   | 10 | 23 / 23 | 23 / 12 | 34 / 23 |
   | 30 | 62 / 62 | 62 / 32 | 92 / 62 |

   C30의 save는 새 readback1+첫 순회31의 full validation32회와 마지막30회의 content receipt 확인을 갖는다. **총 무결성 확인이32회라는 뜻이 아니다.** 읽기367,937,574B·쓰기5,934,477B는 10k/C30에서 유지되어야 하며 반복 decode CPU만 줄인다. digest miss 시 full decode 증가가 정상이다. 다른 파일이 바뀐 사례에 이 고정 계수를 강요하지 않는다.

   채택하려면 두 큰 save의 median이 세 블록 모두 **15% 이상 감소**, 10k save+list median은 모두 감소하고, 작은 대조(save·공개 list)의 p95는 baseline110% 이하여야 한다. 모든 matrix의 반환 metadata·정렬·보관/삭제 수가 동등하고 fault 회귀가 통과해야 한다. 새 파일의 무작위 filename·실제 생성 시각은 역할로 정규화해 비교하되 기존 파일의 filename·size·mtime·삭제 대상 일치는 그대로 검사한다. hash/read/JSON/sync 구간은 inclusive 관계를 표시하며 전체 wall과 합산하지 않는다. 메모리에는 receipt 최대31개와 기존 1파일 처리 버퍼만 유지하고 전체 파일/parsed tree 집합을 cache하지 않는다.
9. **회귀:** 기존 repository7건(보관30·filename 무시, 경로 제한, partial write, 잘못된 다운로드/partial final, stale pending, 다른 repository의 active pending 보호, cleanup 실패)을 모두 재사용한다. 첫 순회와 마지막 read 사이에서 (a) 같은 크기·복원한 mtime의 손상/유효 변경, (b) atomic rename 교체·삭제/재생성, (c) 동시 두 save·delete 및 새 파일 출현, (d) read/stat 실패를 IOOverrides의 제어된 pause로 확인한다. 변경된 유효 파일은 full 검사·fresh metadata, 손상/부재 파일은 기존 제외/오류 의미여야 한다. 공개 list/safeFile은 직전 save receipt를 재사용하지 않는지 확인한다. pending readback mismatch·실패 후 이전30개 보존, 지원 형식의 기존 호환 fixture도 유지한다. 모든 동시성 순열 증명을 요구하지 않고 이 변경의 hit/miss·publication 경계에 집중한다.
10. **거부·복구:** digest 비용 조건·권한·보호 검사 해결 실패, 파일 변경 누락·독립 readback 약화·retention/동시성 회귀, 큰 save 기준 미달·작은 대조 초과·불확실한 결과면 미채택/보류다. 승인되지 않은 metadata-only hit, 전역 직렬화, persistent cache, 해시 검사 완화로 방향을 바꾸지 않는다. task-owned repository/test 변경만 before-image와 3-way 대조로 되돌리고 관련 집중 회귀·보호 검사를 재확인한다. 기존 dirty 테스트는 덮어쓰지 않는다.
11. **의존·순서:** R 처분 뒤 진행하되 R의 성능 성공에는 의존하지 않는다. S 자체의 계획 감사·보호 소스/검사 scoped 승인·host runner·사전 비용 조건이 필요하다. SHA 내용 식별이 해당 경계에 부적합하다는 구체적 감사 지적이 있으면 raw payload 무제한 보관이나 검증 생략으로 우회하지 않고 이 후보를 DEFER한다. 대형 Snapshot architecture/전송 설계는 별도 과제다.

## D. 보류·미선정·제외

| 대상 | 처분과 근거 |
| --- | --- |
| **P1-U** | **DEFER.** 현재 `expenseEntries`는 where/toList/sort 각1회이며 Home/당월 화면도 build당 getter1회다. 같은 build 안에서 재사용할 중복 결과가 없다. 50행 알림 비용0.020~0.0405ms, 5k 약2.27~2.49ms이므로 비용을 부정하지 않지만 지금 protected AppState 수명 설계를 넓힐 이득은 작다. `entries`는 public mutable List이며 초기화/로그아웃, isolated consumer, authoritative candidate, Offline baseline, 임시 projection 등 대입 경로가 있다. 단순 List identity나 한 publication 지점만으로 cache를 무효화하면 누락 위험이 있다. 안전하게 하려면 쓰기 경로·세대·복원까지 명시적 파생 view 계약을 정비해야 한다. root 경계 축소만의 독립 이득도 입증되지 않았다. UI로 정렬을 옮기거나 cross-generation cache를 추가하지 않으며 이번 구현 대상에서 제외한다. 이 처분 자체로 P1-U를 남은 필수 구현으로 만들지 않는다. |
| P1-01 | **NOT ADOPTED**, 원복·기능 회귀 통과 이력 유지. lazy widget 실험을 재개하지 않음 |
| P1-04 | **COMPLETE — C**, SQL/index/presenter 신규 구현0개. 필수 관계·Snapshot/terminal 비용을 제거 대상으로 바꾸지 않음 |
| C1 bundle admission | **이번 mitigation 미선정(NOT ADOPTED).** 비용은 알려졌으나 strict parsing/admission·baseline·권한/복구 검사를 안전하게 줄일 국소 변경이 기존 조사에서 입증되지 않았다. B05/B08 재개나 새 조사·후보 추가 없음 |
| 일반 navigation refresh 생략·일반 coalescing | 범위 밖. freshness·auth/generation·pending 완료 계약 변경을 R-01에 끼워 넣지 않음 |
| P1-05 | **SKIPPED BY OWNER DECISION.** 웹 성능은 만족스럽다는 결정으로 종료 처분. optional 실행 대기 항목으로 남기지 않음 |
| C8 등 다른 최초 지도 항목 | 기존 근거만으로 concrete/material/safe 국소 구현 조건을 충족하지 않아 새 후보로 추가하지 않음 |
| 2·3·4단계 / Next | 모바일 전송량·정리·통합 최종 감사·대형 Snapshot 확장성은 이번 범위 밖이며 미착수 |

추가 후보는 **0개**다. 알려진 비용 전부를 제거하거나 보류 후보를 강제로 채택하는 것을 종료 조건으로 삼지 않는다.

## E. 공유 구현 로그와 운영 순서

승인된 baseline·구현·비교를 아래 행과 milestone 기록에 누적하며 별도 mitigation 보고서를 만들지 않는다.

| ID | 상태 | 실제 변경 파일·구현 요약 | baseline / 변경 후 | 실행 테스트·결과 | 한계·commit/source |
| --- | --- | --- | --- | --- | --- |
| P1-R-01 | COMPLETE — NOT ADOPTED | UI 4행 trial을 정확히 원복, R 테스트/근거 보존 | 모든 블록 GET4→1·durable1, 대조p95 한 구성110.37% | 후보 탐색1건·원복 후 focused132건 PASS | 최종 HomeShell SHA=A 표, M2 게시 준비 |
| P1-S | COMPLETE — DEFERRED | 새 CPU gate 테스트·근거만, repository/보호 검사 변경0 | CPU240표본에서61H/30V가1.51~1.85 / 후보 없음 | calibration1건·기존 Snapshot7건 PASS | scoped 승인은 있었으나 비용 gate 실패 |
| P1-U | DEFERRED | 없음 | 과거 P1-02 재사용 | 새 실행 없음 | D의 이득·위험 처분 |

**승인 뒤 Implementation Session:** 이 문서와 owner의 승인 범위를 읽고 다음 승인 과제 하나를 선택한다. 현재 소스/불변식·before-image를 확인한 뒤 필요한 baseline을 먼저 측정한다. 조건을 통과하면 최소 변경·집중 회귀·성능 비교를 수행한다. 위 행에 실제 파일, 전후 source SHA, raw sample 위치, count/median/p95, 테스트 이름·결과, 한계·rollback 유무를 기록하고 `IMPLEMENTED` 또는 `NOT ADOPTED`로 표시한다. 과제별 commit은 승인될 때만 하며 없으면 working-source SHA로 식별한다. 이후 다음 **이미 승인된** 과제로 진행한다. 미승인 과제를 자동 시작하지 않는다.

**감사 전달:** 구현 batch 처분 후 owner가 이 문서와 실제 diff/source 정보를 같은 persistent Audit Session에 수동 전달한다. Implementation/Audit Session은 동시에 작업하지 않는다. owner가 actionable findings를 돌려주면 같은 Implementation Session이 확정된 material 문제를 수정·집중 회귀하고 E/F를 갱신한다. 같은 Audit Session이 영향 변경만 재검사한다. task/finding마다 새 세션을 만들지 않는다.

이번 계획 작성의 최종 보존 검사는 아래와 같다. ignored cache 전체를 인증하는 의미는 아니다.

- 기존7,943개 파일의 내용·mode·link를 대조했다. 허용된 roadmap·목차2개 외7,941개는 동일하며, 신규 파일은 이 공유 계획1개뿐이다. 이전 dirty13개·역사 근거·source-lock과 HEAD/index/staged를 보존했다.
- 세 문서의 상대 링크167개, A~G 구조, 조건부 명세 각11항목, 기존 성능 지도·역사 근거·순위(roadmap §3~5)의 byte 동일성, whitespace 정적 검사가 통과했다. 미래 테스트 경로2개는 아직 존재하지 않는다. runtime/성능 테스트 결과를 새로 주장하지 않는다.
- 큰 임시 산출물은 해당 없다. 검증에만 쓴 작업 소유 비교 JSON2개(논리1,398,156B·관찰 할당량1,404,928B, 약1.34MiB)는 결과를 이 장부에 남긴 뒤 정리했다. 기존 자료·DB/WAL·cache는 삭제하지 않았다.

## F. 감사 지적과 수정

**Planning Audit(바로 다음):** 실행 가능한 범위·baseline·채택/거부 기준·보호 소스 승인·내용 receipt의 안전성과 비용 조건·U 보류를 검토한다. 생산 구현이나 개선이 완료됐다고 감사하지 않는다. source-level 실패 기전이 있는 지적에 집중한다.

**Mitigation Audit(구현 batch 뒤):** 독립적으로 실제 source/diff를 보고 변경이 유발한 correctness·durability·직접 영향 회귀를 확인한다. 구체적 실패는 가능한 범위에서 재현한다. **4단계 Final Audit**의 앱 전체 adversarial 감사는 나중에 한 번 수행하며 여기에 앞당기지 않는다.

| Finding ID | 대상 | 심각도 | 재현/소스 근거 | 필요한 수정 | 구현 응답 | 재검사 | 최종 처분 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 계획 감사 결과 수령 | 계획 전체 | BLOCKER/MAJOR 없음(owner 전달) | PASS — READY FOR OWNER APPROVAL | owner scoped 구현 승인 완료 | R부터 순차 실행 | 독립 Mitigation Audit는 batch 뒤 | 구현 감사 미실시 |

P0(유실·보안·돌이킬 수 없는 손상)/P1(중대한 기능·영속 오류)은 해당 작업 종료 전에 수정·집중 회귀하거나 명시 차단한다. P2는 변경에 material하면 수정하고 아니면 근거 있는 보류를 기록한다. P3는 기록/기회성 수정으로 처분하며 반복 수정 루프의 근거로 삼지 않는다. 성능 이득을 이유로 계약을 약화하지 않는다. 근거 없는 가상 blocker·모든 동시성 순열 증명·과거 gate 재개를 요구하지 않는다. 사소한 수정마다 전면 재감사하지 않고 관련 변경만 재검사한다.

## G. 1단계 완료 확인표

- [x] 완료된 조사 결과를 보존하고 현재 3개 후보·추가 미선정/제외 항목을 명시했다.
- [x] 조건부 후보의 파일·불변식·baseline·수용/거부·복구·순서를 정의했다.
- [x] 독립 Planning Audit PASS — READY FOR OWNER APPROVAL, BLOCKER/MAJOR 없음이라는 owner 전달을 수령했다. owner가 R-01과 S repository·직접 SHA/무결성 검사의 scoped 구현을 승인했다.
- [x] 승인된 R/S 각각을 구현·측정·채택 또는 미채택/보류로 최종 처분했다. R 미채택·원복, S 비용 조건 보류이며 모든 후보 성공은 요구하지 않는다.
- [x] 채택 생산 변경은 없다. R rollback 후 focused132건·Snapshot7건·backend3건·웹 build·새 테스트2파일 정적 분석이 통과했다. 원 표본·환경·계측은 단일 근거에 보존했다.
- [ ] 변경분 Mitigation Audit의 P0/P1을 해결하거나 명시 차단했고 P2/P3를 처분했다. 미해결 P0/P1이 있으면 해당 작업·단계 종료를 선언하지 않는다.
- [x] 기존7,944개 파일을 대조해 허용 문서3개 외7,941개·역사 근거·잠금·무관한 index 엔트리를 보존했고 기기/배포 제한과 한계를 기록했다.
- [ ] U 보류·P1-05 제외 등 남은 처분을 roadmap에 반영하고 owner가 1단계 exit 충족을 확인했다. 그 뒤에만 별도 승인된 2단계로 진행한다.

**2026-11-03 owner 승인으로 R-01부터 순차 실행한다. S는 R 처분 뒤에만 착수하며 다음 독립 감사는 구현 batch 뒤 Mitigation Audit다.** 1단계 전체 종료·개발 종료·production readiness를 선언하지 않는다.

### 구현 승인·게시 기록 — 2026-11-03

- owner 전달 Planning Audit: **PASS — READY FOR OWNER APPROVAL**, BLOCKER/MAJOR 없음. 계획 감사는 반복하지 않는다.
- 구현 시작 HEAD `2b4e168ebf1d8ba8ce5c9a48d7257a24bbd0c8a7`, `main`에서 같은 HEAD의 `phase1/mitigations`를 생성했다. 생성 직후 index/staged가 동일함을 확인했다. 이전 tracked dirty15개(계획 roadmap/목차 포함)·untracked 자료를 보존했다.
- owner가 explicit-path stage·중간 commit·개발 브랜치 push를 승인했다. unrelated 변경은 포함하지 않는다. production 접근·배포·merge/tag는 미승인이다.
- Flutter CLI는 호출하지 않으며 설치된 compiler/host engine을 직접 사용하는 runner만 검증한다. CI가 Android 작업을 자동 시작하지 않도록 이번 milestone 메시지에 `[skip ci]`를 사용하고 실제 host 검증을 장부에 기록한다.
- M0: `f46a6ffb7ffdc01e55a12a79fa1bed27c55ea137` — 승인된 공유 계획·roadmap·목차를 `origin/phase1/mitigations`에 push 성공. main/production은 변경하지 않았다.
- host runner smoke: 직접 frontend compiler + flutter_tester + 기존 test_api lifecycle로 widget1건 PASS. Flutter CLI/Android 도구 호출0회. 최초 R pilot의 root-zone stale 예외 계측 오류는 handler를 같은 zone에 붙여 수정했으며 pilot은 판정 표본에서 제외한다.

### M1 — P1-R-01 구현 전 baseline

- 생산 HomeShell SHA는 A 표와 동일하다. warmup5+표본20 ×50/1k행 ×양 방향, 측정80개/준비20개, 실행90.017초를 수집했다. 모든 측정에서 callback에 따른 index 전환4·refresh 진입4·실제 authoritative GET4, 최종 durable replacement1·notify1이었다. 각 요청의 trigger_page는 `[1,2,3,4]` / `[3,2,1,0]`이며 dispatch 당시 화면과 별도로 기록했다. 따라서 목적지 외 GET3개가 반복되는 baseline 조건을 통과했다.
- 50행 0→4/4→0 median261.2055/255.321ms, 1k행1466.7165/1472.654ms. 실제 host wall이고 가상16ms frame 간격을 시간에 더하지 않았다. 첫 pilot은 warmup 이전 관측이며 통계에서 제외했다.
- callback 수는 HomeShell onPageChanged가 동기 설치한 index의 ScrollUpdateNotification 관측이다. 실제 GET은 `BaseClient.send`에서 세었다. strict admission 자체 counter와 coordinator 내부 counter는 별도 분리하지 않았으며 성공한 durable 게시와 동일하다고 부르지 않는다. 중간 stale exception은 test-only handler에서 기록하고 원래 authority 검사를 그대로 실행했다.
- fixture50/1k payload75,553/1,317,671B, SHA는 compact evidence에 보존했다. 미추적 P1-02 테스트 의존성을 없애기 위해 같은 fixture class를 새 R 테스트 안에 포함했으며 두 payload SHA 동일성을 재확인했다. 측정 구간·계측은 동일하다.
- 직접 host runner smoke1건·R pilot/본 측정 각각1건 PASS. 다음은 UI 최소 변경과 교대 비교다. M1 commit/push는 다음 갱신에 기록한다.

- M1 게시: `7ad6c88f6e018acf1b985e71fc6e347043271172` — `origin/phase1/mitigations` push 성공. 현재 R 교대 비교 진행 중이며 S는 미착수다.

### M2 — P1-R-01 최종 처분: NOT ADOPTED / UI 원복

- 3교대 블록, warmup5+표본20, 측정840개/준비210개, 전체404.343초로600초 한도 안에 종료했다. 비인접50/1k 양 방향에서 baseline4 GET→후보1 GET, callback/index 전환4→1·refresh 진입4→1·최종 durable 게시1/notify1을 모든 표본에서 확인했다.

| 블록 | 50행 0→4 A/B ms | 50행 4→0 A/B ms | 1k행 0→4 A/B ms | 1k행 4→0 A/B ms | 작은 대조 최대 p95 B/A |
| --- | --- | --- | --- | --- | --- |
| 1 | 261.206 / 88.088 | 255.321 / 82.722 | 1466.717 / 420.875 | 1472.654 / 411.391 | 103.76% |
| 2 | 266.250 / 84.617 | 261.192 / 76.635 | 1462.671 / 416.409 | 1467.733 / 417.441 | 106.07% |
| 3 | 277.607 / 83.086 | 273.240 / 77.016 | 1572.298 / 432.370 | 1571.833 / 423.493 | **110.37% — FAIL** |

- 블록3의 50행 인접0→1 p95는 A139.158ms/B153.590ms, 허용 상한153.0738ms를0.5162ms 넘었다. 잡음 가능성을 이유로 재시험/기준 변경하지 않았다. count·주 latency 개선은 확인했지만 **최종 NOT ADOPTED**다. 프로덕션 HomeShell은 검증한 before-image와 byte 동일한 `e2e4b53496b9950f27666377c6fae7543021cbf770ad412f31d6196b8aa4b5d4`로 복구했다. 실제 앱에 요청 감소를 남겼다고 주장하지 않는다.
- 후보 탐색 회귀1건의10개 체크(양 방향·동일탭·인접·swipe·빠른 반전·animation 중 재선택·notify/authoritative refresh의 draft/focus·dispose)가 통과했다. 원복 후 새 탐색1 + 기존 widget13 + offline refresh27 + authoritative acquisition57 + rebuild pending11 + 보호23 = **132 PASS, 실패/skip0**이다. 초기 두 실패는 각각 입력 카드가 없는 홈을 찾은 새 테스트 finder 오류와 직접 runner의 shader assets 누락이었다. 실제 당월 입력 탭·기존 host assets 경로로 수정한 검증만 최종 합계에 넣었다. 성공 로그 전문은 출력하지 않았다.
- 계측은 host debug JIT·합성 HTTP/파일이다. 가상16ms pump 간격을 wall에 가산하지 않았다. GET의 목적은 zone trigger와 dispatch 당시 페이지를 따로 기록했다. admissions/내부 coordinator 수는 분리 미측정이다. 실제 150ms 지연 진단은 최종 수용 기준 실패로 실행하지 않았다. 기존 device/Android 제한은 그대로다.
- 초기 A/B는 직접 메뉴 callback과 host test fonts로 실행했고(명시 assets 경로 없음), 기존 버튼 회귀는 shader/font assets 경로를 연결해 별도로 검증했다. invocation마다 정확한 flags를 raw 근거에 보존하며 조건이 다른 회귀를 A/B 시간으로 합치지 않는다. 실기기 발생률·RTT·GPU 효과는 미검증이다.
- 새 R 테스트는 환경변수 없는 일반 실행에서 기능 회귀만 수행하며, 긴 benchmark는 명시적인 P1R_OUTPUT 설정 때만 실행한다. 이전 untracked P1-02 파일이나 다른 dirty 소스는 커밋하지 않았다.
- M2 commit/push 결과는 다음 갱신에서 실제 SHA로 기록한다. R 처분이 완료됐으므로 이후 S 사전 조건을 확인할 수 있다.

### M3 — P1-S 사전 조건: DEFER / 생산 미구현

- M2 `b2cbeb1b324457a530758f8022af2e4a1c23404c`가 origin/phase1/mitigations에 push 성공한 뒤 S에 착수했다. repository SHA는 A 표와 동일했고, P1-03의 유효 서버 v7 fixture5k/10k(2,969,474/5,934,477B·동일 SHA)를 재사용했다.
- 생산 변경 전에 원 `_validateSnapshotFile`의 UTF-8/JSON/envelope 본문을 그대로 추출한 CPU gate와 같은 bytes의 SHA-256을 비교했다. warmup5+측정20·3교대 블록, 측정240개/준비60개,26.056초로60초 한도 안에 종료했다. I/O·경로 lookup·receipt 관리 비용을 제외한 SHA의 낙관적 하한 비교다.

| 블록 | 5k decode / SHA median ms | 5k 추가61H / 제거30V | 10k decode / SHA median ms | 10k 추가61H / 제거30V |
| --- | --- | --- | --- | --- |
| 1 | 56.171 / 51.024 | 1.847배 | 129.986 / 102.736 | 1.607배 |
| 2 | 56.945 / 51.406 | 1.836배 | 130.854 / 102.998 | 1.600배 |
| 3 | 57.063 / 51.737 | 1.844배 | 139.986 / 103.851 | 1.508배 |

- 모든 블록·규모에서 `61H < 30V`가 실패했다. 현재 host JIT에서는 decode30회를 아껴도 SHA 추가61회가 더 비싸다. 이것은 전체 save의 실측 악화율이나 실기기 결과가 아닌 비용 조건 실패다. latest owner 지시에 따라 **DEFER — DIGEST COST PRECONDITION FAILED**로 처분한다.
- repository·보호된 SHA/무결성 검사·retention/readback/변경 감지·독립 공개 list/safeFile은 수정하지 않았다. 승인된 범위라도 불리한 조건에서 강제로 구현하지 않았다. full matrix/save 전후 비교와 새로운 동시성·fault 테스트는 후보 미구현으로 실행하지 않았다. 15% save 개선을 달성했다는 주장은 없다. 기존 Snapshot7건으로 현 동작을 확인하며 persistent cache·다른 무효화 설계로 전환하지 않는다.
- 새 S 테스트는 명시 P1S_OUTPUT 설정 때만 CPU gate를 실행한다. fixture·raw 표본·timing 경계·source 본문과 실제 invocation을 동일 compact evidence에 보존한다. M3 최종 검증·commit/push는 다음 기록에 갱신한다.

### M3 최종 검증·인계

- 기존 Snapshot7건 PASS, 최종 포맷 후 탐색1건 PASS, 새 두 테스트의 `dart analyze --fatal-infos`는 **No issues found**다. 초기 brace lint3개만 해당 테스트에서 수정했다. 생산 코드는 어느 파일도 유지 변경하지 않았다. S의 새 동시 변경/SHA miss·fault 비교는 구현이 없어 미실행이며 기존7건보다 넓은 검증을 주장하지 않는다.
- 필수 `npm run build`는 작업 소유 frontend 사본에서 PASS했다. 첫 사본에서 backend 합성 fixture 상대경로가 누락돼 실패했고 동일 기존 fixture만 연결해 재확인했다. dependency symlink 대상은 편집하지 않고 build/cache는 작업 사본에 썼다. Backend는 기존 authoritative empty/rich/equivalence·Snapshot/Summary/payment 경계3건이 새 임시 DB에서 PASS(기존 warning1)했다. 운영 DB/API는 사용하지 않았다.
- CPU gate의 exact 측정 원문은 compiled kernel의 embedded source에서 복구해 SHA `d5dff6d0de797ceb8bed5711a80e27754b96ee8ab74a245e4a00d320ed54d79f`로 보존했다. 이후 source identity assert·포맷은 측정 밖의 변경이다. micro p95·원 표본과 두 합성 payload 원문도 같은 근거에 있다.
- 원격 게시 대상은 승인된 계획/roadmap/목차·R/S 테스트·단일 evidence뿐이다. 기존 dirty/untracked 구현은 일괄 커밋하지 않았다. 기록된 working-source·캐시된 SDK/의존성 조건의 재현이며 clean clone·단말/정식 Flutter CLI 전체 suite 재현을 보장하지 않는다.
- [단일 원시/재현 근거](../benchmarks/phase1-mitigation-evidence.json.gz)의 `r`/`comparison`, `s`/`s-decision`, `reproduction`, `invocations`, `validation`을 사용한다. 각 실제 실행 flags가 authoritative하며 baseline용 무자산 runner와 회귀용 assets runner를 구분했다. 감사 재현 시 새 작업 소유 scratch에 원문/fixture를 복원하고 ROOT/RUN·package config를 현재 경로로 맞춘다. Flutter CLI/Android/ADB는 실행하지 않는다.
- M3 게시·보존 대조/임시 정리는 마지막 기록에 남긴다. 독립 Mitigation Audit는 아직 수행하지 않았으며 owner가 이 장부와 실제 diff/근거를 같은 Audit Session에 전달한다. 2~4단계·대형 Snapshot 작업은 미착수다.

### 최종 보존 확인

- 구현 시작7,944개 파일 전수 SHA/mode 대조에서 허용된 계획·roadmap·목차3개 외 **7,941개 동일**, 삭제0개다. 새 파일은 R 테스트·S CPU gate·단일 evidence3개뿐이다. HomeShell·Snapshot repository·AppState·기존 dirty 보호 테스트와 과거 근거는 시작 bytes를 그대로 유지했다.
- 원래 staged0개를 보존했고 명시 owner 승인 경로만 stage/commit했다. 초기 HEAD의 모든 무관한 index blob/mode가 그대로임을 확인했다. index 파일 자체의 SHA는 승인된 commit 때문에 바뀌며 과거 “index byte 불변”을 주장하지 않는다. main/production은 변경하지 않는다.
- 상대 링크169개와 roadmap §3~5의 기존 성능 지도·역사 근거·순위 byte 동일성이 통과했다. task-owned 임시782여개 파일/링크·약2.09GiB는 보존할 근거를 원격 게시한 뒤 활성 사용을 확인하여 정리한다. 실제 정리 결과는 다음 인계 기록에 남긴다.
