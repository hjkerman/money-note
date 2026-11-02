# P1-R 불필요한 모바일 Refresh 조사 결과

**COMPLETE — B. SOURCE-SUPPORTED REDUNDANCY, MEASUREMENT LIMITED.** 하단 메뉴에서 먼 탭으로 이동할 때 중간 페이지까지 refresh하는 좁은 기회를 확인했다. 첫 구현 후보는 **비인접 하단 탭 선택을 직접 jump로 처리하고 최종 목적지 refresh는 유지하는 UI 실험** 하나다. 일반 navigation freshness를 없애거나 coordinator 전체를 합치는 제안이 아니다. **생산 변경·최적화 구현0개**로 조사를 마친다. 새 모바일 실행을 하지 않았으므로 실제 중간 callback/HTTP 빈도·단말 지연 개선을 입증했다는 판정은 아니다.

## 소스와 범위

분석 시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, index SHA-256은 `56aba5ca9506287cbe6a81dd5caebc246e3519c6e84b9680f4108358d50f5595`다. HEAD와 dirty working source를 구분했다. 이후 사용자 별도 요청으로 문서 정리·커밋·푸시가 승인됐으며 실행 코드 변경 승인은 아니다.

| 현재 source | SHA-256 |
| --- | --- |
| `mobile/lib/src/screens/home_shell.dart` | `e2e4b53496b9950f27666377c6fae7543021cbf770ad412f31d6196b8aa4b5d4` |
| `mobile/lib/src/app_state.dart` | `c46a87a8b68507214a85966c3cc2c4f46df0d040de75b74e18c7954dea9d14bc` |
| `mobile/lib/src/api_client.dart` | `2f5645a1e32971569862410aee0833c958bd65c7d8e44f0caba0d7551e91ae0b` |
| `mobile/lib/src/coherent_refresh_coordinator.dart` | `85cca7a72805c1355857691cc3bf5f3cdcb90dd554a82c02a65b8e0fbff3833a` |
| `mobile/lib/src/authoritative_bundle.dart` | `d94e9733fa39fcaefe8fd99d1df7524460d1a55f08545d86d2e33c8d668088df` |
| `mobile/lib/src/offline/offline_store.dart` | `907aa044b8205233b06e4ea081122e72d9b5803523a998a410850558c17e903f` |

SDK `page_view.dart`도 파일로만 읽었고 SHA는 근거에 보존했다. Flutter CLI·doctor·device discovery·Android·ADB·emulator는 실행하지 않았다. 별도 승인된 운영 row 집계 외에는 production DB/API를 사용하지 않았다.

## 재사용한 기존 근거

| 기존 최적화/보장 | 근거·revision | 현재 적용과 남은 점 |
| --- | --- | --- |
| coordinator 추출과 늦은 결과/로그아웃 경계 | `01125f4`, `7c0e601`; 현재 `offline_refresh_test.dart`의 두 응답 순서·logout 회귀 | 현재 ticket은 lineage/auth/request generation을 검사한다. 이것은 publication 보호이며 보통 HTTP single-flight가 아님 |
| legacy DAG 병렬화 | `ec96671`, [기존 구현 기록](../t65/implementation/t65b3-implementation.md) | legacy는 명시 진단 oracle에만 남음. 정상14 GET 문제를 다시 해결할 대상으로 삼지 않음 |
| strict bundle 지원·정상 채택 | `56909c9`→`597a936`, 같은 구현 기록 | 정상 refresh14→1, mutation+취득15→2 유지. 현재 coordinator는597a936과 byte 동일. AppState/API 전체는 후속 변경돼 현재 본문을 직접 확인함 |
| strict admission·JSON durable publication·pending | [architecture](../architecture.md), [offline-mode](../offline-mode.md), `authoritative_acquisition_test.dart`·`authoritative_rebuild_pending_test.dart` | decode 전후 authority, 원자적 baseline/readback, committed marker cleanup 뒤 UI 설치 유지. outcomeUnknown은 GET 성공으로 확정하지 않음 |
| navigation·resume의 실제 host 관측 | [P1-02](../p1-02-flutter-rebuild-derived-state-results.md), source8개가 현재와 byte 동일 | 이전640표본 중 관련 trace 재사용. navigation은 jump1→2→0이므로 이번 animate 중간 callback의 빈도 증거가 아님 |
| backend 비용 | [P1-04](p1-04-backend-sql-presenter-performance-results.md), 현재 source 동일성·payload 검증 근거 | backend context만 재사용. 모바일 완료 시간이나 요청 제거의 보장 절감량으로 바꾸지 않음 |

P1-03의 PARTIAL·자동 ADB 기동/작업 소유 PID 종료 사건은 원문 그대로 보존했다. P1-S 재조사나 기기 gate 작업은 열지 않았다.

## 정상 refresh와 A/B/C/D의 차이

`AppState.refresh/refresh*Area → _refreshAuthoritativeState → pending JSON read·mode/auth 확인 → coordinator.begin → 필요 시 알림 permission → coordinator.acquire → MoneyNoteApiClient.authoritativeStateBytes → GET /api/authoritative-state → ticket 확인 → AuthoritativeBundle.decode/strict admission·typed conversion → ticket 확인 → _withLineageLock → OfflineBaseline → OfflineStore.replaceBaseline → pending 완료 확인 → UI state 대입 → 필요 시 알림/inbox → notify`다.

- **A 실제 취득:** 현재 HTTP 메서드는 인증 header를 붙여 GET 한 번을 명시 dispatch한다. `_request` 자체에 자동 재시도/재인증 loop는 없다. 새 retry는 상위 recovery 또는 사용자 동작이다.
- **B 취득 요청이 있지만 dispatch 없음:** write-in-flight/mode/auth에서 AppState가 중단하거나, 더 최신 ticket이 `acquire`의 network 전 검사에서 이전 ticket을 막는다. stale 요청이 이미 출발한 경우의 비용을 되돌리지는 않는다.
- **C 로컬 처리:** persisted Offline baseline·journal 복원, strict decode·모델 변환·baseline encode/flush/readback·pending cleanup. 보통 UI isolate의 동기 decode와 await 파일 I/O다. 정상 baseline은 **SQLite가 아닌 JSON 파일**이다.
- **D UI 알림:** busy/status·draft·알림 inbox/permission 변화에 대한 notify/rebuild는 authoritative GET과 같지 않다.

API는 raw bytes를 반환하고 strict parser가 presence/type·exact money·Unicode·Snapshot hash/복구·principal을 확인한다. 서버 revision/date/timezone도 admission과 baseline에 들어간다. 새 값이 서버 authority이며 모바일 금융 재계산을 제안하지 않는다. lineage lock은 설치를 직렬화하지만 HTTP 취득을 합치지 않는다. JSON 임시 파일은 flush→readback parse→마지막 동기 authority 검사와 renameSync를 통과한 후에만 유효 baseline을 대체한다.

## 사용자 동작과 trigger 지도: 20개

아래 GET 수는 `/api/authoritative-state`의 **소스상 정상 성공 경로(S)**다. 별도 표시한 **H는 이전 synthetic host 관측**이며 실제 backend HTTP 수가 아니다. native plugin 지연·경합·중간 프레임이 있는 새 단말 trace를 만들지 않았다.

| 동작 | 실제 entry | bundle GET | 조건·분류 |
| --- | --- | --- | --- |
| 01 Online cold startup | app.initState→bootstrap | S1 | health·me·bundle·launch Snapshot은 별개. 초기 인증·복구 후 새 authority 필요(R1) |
| 02 유효 Offline/finalizing workspace 복원 | restorePersistedOfflineWorkspace | S0 또는 finalization의 별도1 | 로컬 baseline/journal 설치 후 startup return. normal bundle로 Offline을 덮지 않음(R1/C) |
| 03 로그인·session 교체 | login→refresh | S1 | health/login POST·Snapshot 별도, auth generation 변경(R1) |
| 04 인접 탭·일반 도착 탭 | HomeShell._handlePageChanged | S1/callback | 모든 area가 전체 bundle. 외부 변경·기준일 freshness를 임의로 없애지 않음(R1) |
| 05 비인접 하단 탭 선택 | _selectTab→animateToPage→onPageChanged | S 가변, 단조0→4는 최대4 | 중간 페이지 callback도 area refresh. 중간은 별도 사용자 선택이 아님(R2/R4 후보) |
| 06 현재 탭 재선택 | _selectTab의 value==index | S0 | 이미 early return. 새 최적화 대상 아님 |
| 07 secondary route push/pop | input/management Navigator | 보통 S0 | 일반 뒤로 복귀 hook만으로 refresh하지 않음. 초기화·저장 동작은 별도 |
| 08 지출 편집 dialog 열기/취소 | MonthEntryCard dialog | S0 | 독립 거래 detail route는 없음. 실제 저장은 아래09(R1) |
| 09 지출 create/category/net/delete | _run→_financialWrite→refresh*Area(false) | S1, H mutation API1 | durable pending→commit acknowledgment→bundle→baseline→cleanup 완료. mutation 응답만으로 제거 불가(R1) |
| 10 현금·정산·정기·설정·월마감 command | 각 command→금융 write→해당 area | S1/성공 rebuild | 단일 논리 저장에서 중복 post-mutation GET은 발견하지 못함(R1) |
| 11 pull/명시 refresh | RefreshIndicator·state.refresh | S1 | 사용자의 fresh-state 요청 유지(R1) |
| 12 연속 실제 탭1→2→0 | PageView callback→각 area | H API3/notify3, S 정상GET3 | 각각의 도착 요청. 과거5k5.55초 전부를 낭비로 보지 않음(R6) |
| 13 겹친 정상 refresh | 두 refresh→두 begin/acquire | S 이미 출발했다면2 | 일반 Future reuse 없음. 최신 ticket만 설치, 시작 시점이 달라 일반 공유 안전성 미입증(R4/D) |
| 14 실패 후 사용자 재시도 | refresh 실패→다시 refresh | S1+1 | 실패/불완전 취득의 새 시도이며 필요한 복구(R1) |
| 15 foreground 복귀 | resumed→resumeFromBackground | S1, H API1 | guard가 동시 resume 진입 차단, 이후 별도 launch Snapshot. server 날짜/권한 freshness 유지(R1) |
| 16 Online 재연결 | recoverConnectivity | 성공시 S1, 오류시 가변 | `_connectivityRecovery` Future 공유가 이미 있음. health 최대3회 및 실패한 constituent 취득 retry는 분리(R1) |
| 17 Offline 서버 복구/조정 | checkServerRecovery·finalizeMobile/ServerWins | 보통 health만0, finalizing 취득1/시도 | 명시 조정·recovery artifact·resolved ID·pending 경계 유지(R1) |
| 18 Snapshot save/share/restore | saveLaunchSnapshot·restoreLocalSnapshot | save0, restore성공1 | 별도 `/api/admin/snapshot` 요청과 구분. restore mutation 뒤 fresh baseline 필수(R1) |
| 19 알림 target/import·archive 열기 | consumeLaunchTarget→HomeShell | archive0, import의 home jump는 조건부1 | notification_import는 index!=0이면 jump0. 앞선 resume 성공 여부·foreground handler가 달라 일괄 생략 후보로 삼지 않음(R6) |
| 20 busy/status·permission/inbox | notify·refreshNotification* | H busy/status API0 | native/local 작업 및 UI-only 알림. bundle reload가 아님(D) |

날짜/timezone 전환의 전용 Timer refresh는 확인하지 못했다. 새 server evaluation은 실제 취득/복귀 때 설치된다. 따라서 일반 탭 최종 refresh를 TTL이나 byte 동일성만으로 생략할 근거는 없다.

## 기존 coalescing과 로컬 반복 처리

일반 coordinator는 요청마다 `++_requestGeneration`을 발급하며 `_inFlight Future`를 보관하지 않는다. 출발한 A 뒤 B가 시작되면 둘 다 backend에 도달할 수 있고, A는 응답 후 authority 검사에서 decode 전 폐기될 수 있다. A가 이미 decode한 뒤 B가 시작됐다면 final publication guard가 다시 막는다. HTTP cancellation을 수행한다는 근거는 없다. pre-dispatch stale 차단·최신 승자 정책과 in-flight 공유를 구분한다.

반면 foreground guard, connectivity Future, mutation `_run` busy·write-in-flight는 이미 작동한다. 기존 overlap 회귀 두 응답 순서도 최신 baseline/UI 설치를 확인한다. 이번에는 이를 다시 실행하거나 바꾸지 않았다. 새 R5 로컬 불필요 admission/publication은 확정하지 않았다. raw-token/decoded 구조 검사와 durable readback은 서로 다른 보증이며 JSON pass 수만으로 중복이라 하지 않는다.

## 유일한 추천: P1-R-01 비인접 하단 탭 직접 이동

검증한 source 순서는 다음과 같다.

1. `HomeShell._selectTab(value)`는 현재 index와 다르면240ms `animateToPage`를 호출한다.
2. 현재 SDK는 offset animation의 ScrollUpdate마다 `metrics.page.round()`가 바뀌면 onPageChanged를 호출한다.
3. `_handlePageChanged`는 중간 값도 index에 설치하고 해당 area/full refresh를 시작한다. 목적지와 중간 페이지를 구분하지 않는다.

**제안:** 하단 메뉴에서 거리2 이상인 탭을 고를 때는 기존 `jumpToPage` 경로로 목적지에 직접 이동하고, 인접 선택 animation과 수동 swipe는 유지한다. 실제 목적지 onPageChanged의 refresh도 유지한다. 중간 페이지를 보여 놓고 검증을 생략하는 방식이나 AppState/coordinator rewrite가 아니다. notification import와 기존 P1-02 host fixture에서도 jump API 자체는 이미 사용된다.

0→4에서 제거 가능한 것은 **최대3개의 중간 refresh 진입과 조건부 HTTP dispatch**다. 실제 프레임이 중간 center를 건너뛰거나 오래된 ticket이 dispatch 전에 막히면 제거할 HTTP는0일 수 있다. 실제 발생률·CPU/latency 절감은 미측정이므로 A 판정이나 요청4→1 실측을 주장하지 않는다.

정확한 수정 대상은 `mobile/lib/src/screens/home_shell.dart:_selectTab` 하나다. 확인한 P0 protected-source/worktree-target에 HomeShell은 없고 **추천 경로는 protected AppState/coordinator/OfflineStore 변경을 요구하지 않는다**. frozen source archive·source lock을 변경할 권한을 뜻하지는 않는다. 비인접 전환의 animation을 없애는 UX 변화는 다음 작업 승인 범위에 명시해야 한다. 복잡도는 작으며 일반 요청 공유보다 위험이 낮다.

다음 승인된 실험은 기존 widget fixture에서 비인접0→4/4→0의 실제 callback·API dispatch baseline부터 확인한다. 중간 중복이 없으면 구현을 보류한다. 최종 목적지 refresh1·중간0, 인접/수동 swipe·빠른 재선택/중단·pull·mutation 완료·Offline·날짜/auth 전환, draft/focus/row identity/disposal을 집중 확인한다. 조건부 지연 절감과 총 operation을 측정하고 작은 workload가 회귀하면 미채택한다. 이번에는 구현·신규 Flutter 실행을 시작하지 않는다.

일반 탭 refresh 전면 제거는 새로운 freshness 계약이 필요하고, 일반 in-flight 공유는 요청 시작의 신선도 barrier·auth/generation·pending/commit ordering을 바꾸므로 protected/high-risk다. 이 두 방향을 추가 추천 후보로 확대하지 않는다.

## 비용 근거와 측정 한계

P1-04의 host TestClient context(중앙값/p95 ms, n20)는 다음과 같다. client parse·durable baseline·UI·RTT는 포함하지 않는다.

| ledger 행 | backend bundle ms | 실제 payload bytes |
| ---: | ---: | ---: |
| 376 | 68.662/72.310 | 306,370 |
| 1000 | 157.058/187.682 | 653,317 |
| 5000 | 744.686/768.852 | 2,889,309 |
| 10000 | 1273.714/1462.058 | 5,684,312 |

실제 불필요 GET 한 번을 없애면 이와 같은 backend 작업·payload가 줄어들 수 있다. 병렬 실행·경합·서버 상태가 달라 전체 endpoint 시간이 그대로 사용자 latency에서 빠진다고 보장하지 않는다. P1-02의5k navigation 중앙값5.551804초는 jump1→2→0·합성 API·client admission/JSON I/O·pump가 포함된 과거 관측이며 이번 후보의 비인접 animation 측정이 아니다. backend 값과 합산하거나5.55초 전부를 낭비로 계산하지 않는다.

새 성능 캠페인은 수행하지 않았다. 정적 trigger 분석과 source가 동일한 이전 trace로 후보 선택에 충분했으며, 실제 frame/HTTP 빈도의 남은 한계는 다음 승인된 host 실험의 판정 항목으로 한정한다. 압축·delta·segmented·2단계 전송량 조사나 최종 감사로 확대하지 않았다.

## 상태와 다음 결정

P1-01 미채택, P1-02/P1-U 보호 경로 보류, P1-03 조사/P1-S 구현 대기, P1-04 C·새 구현 없음, P1-05 선택·미승인을 보존한다. P1-R은 현재 합의된 마지막 주요 조사이며 이후 mitigation 구현 또는 보류를 선택한다. 구현 승인·1단계 종료를 자동 선언하지 않는다. 원 F01 BINDING—UNRESOLVED, 유효 G1, G2 미채택, ADB 차단·실기기/T6.9 보류·formal T6.6F 미종결·R1 CLOSED·배포 미승인도 유지한다.

문서 재배치·커밋·푸시는 사용자의 별도 후속 승인 범위다. 분석 시작의 인덱스/HEAD와 구분해 문서 변경만 반영하고 기존 실행 코드·stage를 보존한다. source/역사 근거와 문서 경로 보존 내역·검사·임시 산출물 정리는 [단일 근거](../benchmarks/p1-r-mobile-refresh-trace.json.gz)에 연결한다.

기존 backend 합성 회귀3건과 임시 사본 npm build가 통과했다. 모바일 widget/animation 실행이나 새 성능 캠페인은 하지 않았다. 초기 웹 사본 준비의 작업 경로 오류는 사본에서 바로잡았으며 생산 변경은 없었다.

문서 정리는 [통합 목차](README.md)로 모았다. 활성 문서3개를 이동하고 기존 도구/동결 근거가 참조하는102개 원본은 내용·경로를 보존했다. 이번 문서 전용 push가 Android build를 시작하지 않도록 커밋에 `[skip ci]`를 사용할 계획이며 workflow 파일은 변경하지 않는다([GitHub 규칙](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs)). 이는 release/device gate 면제나 mitigation 구현 승인이 아니다.

기존 파일7,939개와 실행 source14개를 대조했고 승인된 문서 이동·갱신 외 변경은 없었다. 기존 source·동결 원본·초기 staged 항목은 보존했다. 고유 분석/이동 before-image·검사 로그를 압축 근거에 보존하고 활성 프로세스 부재를 확인한 뒤 작업 소유 임시 파일/symlink93개(논리 크기3,529,764B, 관찰 할당량3,764,224B)를 정리한다. 기존 cache·DB/WAL·symlink 대상과 다른 host 프로세스는 정리하지 않는다.

**다음 행동:** 비인접 하단 탭 직접 이동(P1-R-01)의 한정 host 검증·구현 실험 승인 여부를 결정한다.

## 운영 DB 규모 — 별도 승인된 읽기 전용 집계

2026-11-03 00:15:46 KST 기준, 실행 중 API의 실제 data mount와 DB 경로를 확인한 뒤 `mode=ro`·`query_only`·read-only authorizer·한 read transaction으로 count만 조회했다. 개인 금융 행 내용·사본은 읽거나 만들지 않았고 생산 DB를 시험에 쓰지 않았다.

- **ledger468행 = current23 + archive445. 10K ledger benchmark의4.68%, 약1/21.4 규모**다.
- 금융9테이블 합994행, auth/audit/설정 등을 포함한 전체 사용자 테이블 합2,264행이다. 전체 합을10K ledger와 같은 척도로 비교하지 않는다.
- current/archive·관계 테이블 분포가 합성 fixture와 달라 row 비율을 응답 시간 비율로 환산할 수 없다. 집계 연결의 total_changes는0이다.
