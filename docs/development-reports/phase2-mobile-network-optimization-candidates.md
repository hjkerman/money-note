# Phase 2 모바일 네트워크 전송량 조사·후보

**P2-N01 ACCEPTED — 최종 독립 감사 PASS, A01/R1 CLOSED. 과거 이력 보존.** Phase 1은 owner가 전달한 최종 독립 감사 **PASS — MITIGATION ACCEPTED**로 종료했다. R-01 채택·활성132 PASS·GET4→1·원110.37% 실패와1회 예외·거부/원복 기록을 보존한다. S/U는 DEFERRED이며 재개하지 않는다. 전체 개발 종료·배포 준비 판정이 아니다.

§1~7은 원 discovery 기록이며, §8은 당시 차단된 preflight, §9는 최초 구현, **§10은 승인된 A01 수정의 최신 상태**다.

## 1. 기준선·범위

- 조사 시작 `cd3f385c20c02897f484e9f77c1260b7859bdaf0` / `phase1/mitigations`. 종료 기록 commit **`e5726b6def26af3d2f8c46984b718ca51ee49a80`**를 게시한 뒤 같은 HEAD에서 인덱스·기존 dirty13개를 유지해 **`phase2/mobile-network`**를 생성했다. main merge·배포는 하지 않았다.
- 현재 생산 소스·backend schema·금융/인증/Offline/동기화 계약은 변경하지 않았다. 조사 도구는 disposable 작업 사본에만 두었다. Flutter CLI·Android·ADB·emulator·운영 DB/API·운영 proxy 설정을 사용하지 않았다.
- 데이터/계약의 원본은 [domain-model](../domain-model.md), [architecture](../architecture.md), [offline-mode](../offline-mode.md), [security](../security.md)다. 정상 OfflineStore는 JSON 파일이다. strict admission·Snapshot/관계·auth/revision/generation·durable pending/reconciliation·원자 게시·복구·mutation 완료 의미를 유지한다.
- [단일 raw/재현 근거](../benchmarks/phase2-mobile-network-evidence.json.gz)에 현재 source SHA·실제 응답·일관된 합성 DB·시나리오별 HTTP 계수·Dart/ Python 원문과 invocation을 둔다. Runtime은 Linux/i7-8750H, Python3.12.3, Flutter engine3.47.4/Dart3.13.3의 **직접 host runner debug JIT**다. 숫자는 운영·실기기 전송량이 아니다.

| 재사용한 근거 | 현재 대조·효력 |
| --- | --- |
| [T6.5B-3/현재 상태](../project-state.md) | 정상14→1 GET, mutation+취득15→2 유지. 이번 실제 AppState replay도 저장2회였다. 과거14 GET을 새 제거 후보로 취급하지 않음 |
| [T6.6A](../t66/a/t66a-payload-attribution.md) | 기존 gzip/IOClient·정확 byte 귀속 재사용. 새376/1k/10k Bundle SHA가 과거 attribution의 각 SHA와 **모두 동일**했다. codec campaign을 반복하지 않음 |
| [P1-04](../archive/phase1/p1-04-backend-sql-presenter-performance-results.md) | 보존된 합성 consistent DB3개를 검증·복원해 현재 endpoint를 호출. backend CPU ms는 bytes/절감량으로 환산하지 않음 |
| [공유 P1 장부](../archive/phase1/phase1-mitigation-plan.md) | R-01의 GET4→1은 이미 현재 baseline에 반영. 이번 Phase 2 절감에 다시 더하지 않음. 로컬 Snapshot 검증 CPU인 S도 네트워크 절감과 구분 |

## 2. 현재 네트워크 모델

`사용자/수명주기 → AppState → MoneyNoteApiClient → package:http IOClient/HttpClient → backend → JSON bytes → strict bundle admission → guarded JSON OfflineStore publication → UI`다. `notifyListeners`·widget rebuild·로컬 파일 read/decode를 HTTP 요청으로 세지 않는다. segmented sync는 `ForIsolatedUse` 경로로만 남아 있고 정상 앱에는 활성화하지 않았다.

`api_client.dart`의 **44개 route literal callsite**를 method/line과 함께 근거에 열거했다. 같은 path의 GET/PATCH/DELETE 및 위임 wrapper가 있어44개 서로 다른 endpoint나44회 실제 요청이라는 뜻은 아니다.

| 경로군 | 실제 path·trigger | 정상 전송 의미 |
| --- | --- | --- |
| 세션/연결 | `/health`, `/api/auth/me`, `/api/auth/mobile-login`, `/api/auth/logout` | startup은 secure session 복원 뒤 health/me. login/logout은 명시 행동. 토큰 저장은 local이며 매 알림에 로그인하지 않음 |
| authoritative | `GET /api/authoritative-state` | 초기/탭 목적지/pull/명시 refresh, 성공 mutation 뒤 취득, 정상 foreground. snapshot+typed state를 매번 완전 취득 |
| 읽기/관리·보조 | `/api/entries/current`, `/archive`, `/api/month/current/summary`, `/panels`, `/planned/confirmed`, `/status`, `/api/card-payments/current`, `/api/judgment/current`, `/api/settings`, `/api/cash-flows?from&to&limit`, `/api/card-discounts/months/{month}?scope`, `/profiles/transit/{month}` | 정상 bundle 취득이 각각을 호출하는 것은 아님. AI 자료 sheet는 summary/current/archive/cash/panels/confirmed **6 GET**, 지침 asset은 local. 과거월 할인/관리 preview 등은 해당 행동에서 호출 |
| 금융 명령 | `/api/entries` POST, `entries/{id}` PATCH/DELETE, planned POST/confirm/preview/DELETE, card-discounts entry PATCH/DELETE, panels POST/discount/type-complete/confirm-fixed/DELETE, cash POST/DELETE, current/close POST | 일반 명령은 작은 입력·서버 응답 뒤 required authoritative GET. mutation 응답을 이유로 후속 취득을 제거하지 않음 |
| 설정 명령 | `/api/settings/{key}` PATCH, `/api/card-discounts/profiles/transit/{month}` PATCH | 변경 후 해당 정상 refresh. 세부 endpoint는 inventory 참고 |
| Snapshot/APK | `/api/admin/snapshot` GET, `/snapshot/restore` POST, `/api/admin/apk` GET | Snapshot은 startup/login/정상 resume와 명시 백업·빈 로컬 공유 때 다운로드. restore는 전체 JSON text+password upload. APK는 사용자 명시 작업, 크기 미측정·APK 생성 안 함 |
| Offline 조정 | `/api/offline-reconciliation/server-recovery` POST, `/status` GET, `/mobile-wins` POST | 준비 응답은 fingerprint/서버 artifact filename 등의 metadata이며 Snapshot 다운로드가 아님. Mobile Wins는 전체 B Snapshot+J+인증 입력을 upload, 확정 뒤 fresh bundle. status는 결과 유실 복구용 |
| 진단·격리 | `/api/offline-reconciliation/baseline`, legacy typed 취득, `/api/sync/v1/*` | baseline의14 GET oracle·segmented는 정상 refresh에 합산하지 않음. 격리 path를 대안으로 활성화하지 않음 |

**빈도는 행동당 값이다. 일/월 사용 빈도·실제 사용자 데이터는 조사하지 않았다.** 일반 refresh Future는 전체 공통 single-flight가 아니지만, foreground·connectivity recovery·submission에는 각 기존 가드가 있다. connectivity 오류 때만 zero/350/850ms의 최대3개 recovery attempt가 있으며 상시 periodic 금융 polling은 확인되지 않았다. pending/auth/mode에 막힌 진입은 HTTP0회일 수 있다. Offline foreground/pull은 health만 호출하고 조정 완료 전 B를 교체하지 않는다. HTTP 오류가 모든 POST의 안전한 자동 재전송 근거가 되지는 않는다.

## 3. 계층·측정 방법

1. 기존 P1-04 합성 DB3개를 작업 소유 사본으로 복원하고 현재 **무변경 backend TestClient**로 health/me/Bundle/Snapshot/반복/clock 변화/정상 create 전후 응답을 캡처했다. date2026-10-05·Snapshot clock·judgment RNG를 고정했다. 인증은 합성 owner/session뿐이다.
2. 캡처한 원문을 disposable loopback HTTP/1.1 fixture가 identity 또는 **Bundle/Snapshot만 gzip6**으로 제공했다. 이는 압축 구현 배포가 아닌 관측 대조다. 실제 모바일 API·AppState·IOClient·임시 JSON OfflineStore를 실행했다. startup/nav 목적지/repeated refresh/resume/일반 mutation/Offline local input/복구 health를 replay했다. nav는 승인된 목적지 refresh 진입점을 호출했으며 gesture를 재측정하지 않았다.
3. 헤더 parser가 읽은 실제 request line/header CRLF와 body, fixture가 쓴 status/header/entity bytes를 따로 세었다. 아래 HTTP 합계는 **upload+compressed/identity response entity+양쪽 line/header**다. TCP/IP·TLS·ACK/재전송·운영 proxy/HTTP2 header coding은 포함하지 않는다. synthetic token 길이도 실제 운영과 다르다.
4. 실제 IOClient는 **Accept-Encoding:gzip**을 전송했다. 추가6 GET에서 API가 받은 길이/SHA가 원 Bundle과 같고 strict admission이 통과함을 확인했다. gzip entity 크기를 `response.bodyBytes` 길이로 오해하지 않는다. 모든6개 AppState bootstrap은 정상 admission·durable baseline과 자동 로컬 Snapshot을 완료했다.
5. Mobile Wins/restore는 **실제 API의 요청 직렬화/전송만** 계측했고 fixture 응답을 사용했다. backend reconciliation/restore commit을 실행한 결과가 아니다. password는 합성값, Mobile Wins artifact SHA는64자 placeholder이며 서버 recovery handshake·증빙 검증을 통과했다고 주장하지 않는다. upload gzip은 원문을 오프라인 gzip한 **잠재 크기**이며 실제 upload는 모두 무압축이다. runtime J의 UUID/시각 때문에 재현 시 작은 byte/압축 차이가 날 수 있다.

본 wire replay는 **84 requests, 46.25초**였고 byte-exact control6개를 별도로 실행했다. bytes/count 연구이므로5+20 latency campaign을 하지 않았다. fixture 생성·backend 캡처·compile·local I/O를 임의로 endpoint latency나 통신 지연에 더하지 않는다. 초기 widget fake-async 설정 대기는 정확한 task-owned engine만 중단하고 제외했으며, 최종 실행은 기존 T6.6A의 ordinary async host 방식이다.

## 4. 기준 바이트

N은 **ledger row 수**이며 전체 테이블 row 수나 화면 표시 row 수가 아니다. 세 fixture 모두 current105개(typed entries104개), 나머지는 archive다. panels4·cash5·payment batch1 등 관계는 실제 기존 rich fixture에서 보존했다. all-current10k·실사용 분포를 대표하지 않는다.

| ledger N / current | Bundle 원문 / gzip6 B | Bundle entity 감소 | 별도 Snapshot 원문 / gzip6 B |
| --- | --- | --- | --- |
| 376 / 105 | 306,370 / 11,474 | 96.25% | 218,421 / 7,369 |
| 1,000 / 105 | 653,317 / 18,173 | 97.22% | 565,368 / 13,859 |
| 10,000 / 105 | 5,684,312 / 108,916 | 98.08% | 5,596,362 / 104,537 |


### 행동별 요청 수와 필수성

| 행동 | 측정 요청 | 요구되는 경계/해석 |
| --- | --- | --- |
| 빈 workspace·세션 startup | health + me + Bundle + Snapshot =4 | 로그인/최초 authority와 독립 자동 백업. 저장된 Offline workspace startup은 소스상 local 복원 후 반환하며 이 fixture의 온라인 startup과 다름 |
| R-01 이후 탭 목적지 | Bundle1 | 최종 목적지 freshness 유지. 중간 GET 제거는 이미 Phase1 baseline |
| 변경 없는 명시 refresh2회 | Bundle2 | 같은 bytes라도 요청이 불필요하다는 증거가 아님 |
| 정상 foreground | Bundle+Snapshot =2 | 기존 resume 가드·백업 의미 유지 |
| 일반 지출 생성 | POST1+Bundle1 =2 | durable pending→ack→fresh admission/publication 후 완료 |
| Offline 로컬 지출1건 | 0 | input-only J의 local append·예상 view |
| Offline 서버복구 확인 | health1, Bundle0 | RECONCILIATION_REQUIRED로 전환하고 사용자 조정을 기다림 |
| connectivity 실패/재시도 | 소스 확인, 본 wire 미실행 | 최대3회 health와 필요시 me/fresh 취득, auth/lineage 가드. blanket 재전송 아님 |
| Mobile Wins/restore upload 구성 | POST 각1 | 인증 입력을 포함한 대용량 요청. 실제 commit/recovery 전체 완료는 미측정 |

아래는 **전체 HTTP 바이트 B**의 `identity / gzip 대조`다. 일반 저장에는401B upload가 포함된다.

| ledger N | startup4회 | 목적지 refresh1회 | foreground2회 | mutation+refresh2회 |
| --- | --- | --- | --- | --- |
| 376 | 526,779 / 20,922 | 306,882 / 12,032 | 525,917 / 20,060 | 310,016 / 13,954 |
| 1,000 | 1,220,673 / 34,112 | 653,829 / 18,731 | 1,219,811 / 33,250 | 656,966 / 20,668 |
| 10,000 | 11,282,664 / 215,535 | 5,684,825 / 109,475 | 11,281,802 / 214,673 | 5,687,965 / 111,362 |


10k startup의 논리 다운로드는 **11,280,804B**, gzip 대조 entity는 **213,583B**였다. health/me를 제외한 foreground의11,280,674B 중 Snapshot만5,596,362B다. 10k 변경 없는 refresh2회의 전체 HTTP는11,369,650B /218,950B다. 반복 GET을 줄이지 않아도 encoding만으로 bytes가 크게 줄지만 JSON decode·local 검증 작업이 그 비율로 줄어드는 것은 아니다. Offline recovery health는 두 mode 모두 HTTP250B(body15B)였고 Offline local input은0B였다.

### Upload

다음은 실제 upload body / 오프라인 gzip6 추정 B다. gzip upload를 전송하거나 backend 지원을 구현하지 않았다.

| ledger N | 일반 create | Mobile Wins B+J | Snapshot restore(text JSON) |
| --- | --- | --- | --- |
| 376 | 401 / 238 | 219,903 / 7,869 | 243,020 / 7,510 |
| 1,000 | 401 / 238 | 566,852 / 14,395 | 628,655 / 13,961 |
| 10,000 | 401 / 238 | 5,597,848 / 105,119 | 6,217,649 / 104,562 |


Snapshot restore는 JSON 문자열의 따옴표 escaping 때문에 원 Snapshot보다 커진다. 실제 restore/조정 endpoint는 password·권한·digest·raw-money·보호된 apply/rollback을 따로 검증하므로 byte 구성이 그 검증 통과를 증명하지 않는다. 일반401B 입력에 codec/header 복잡도를 추가하기보다 반복되는 큰 다운로드를 우선한다.

## 5. 후보 비교·권고

| ID | 분류 | 절감 근거/상한 | 위험·복잡도 | 현재 권고 |
| --- | --- | --- | --- | --- |
| **P2-N01** | **HIGH PRIORITY** | B/S entity96.25~98.13% 감소(합성기본). 10k startup HTTP11,282,664→215,535B 대조 | byte-preserving HTTP coding, 작음~중간. 운영이 이미 압축하면 추가 절감0일 수 있음 | backend 구현·검증 PARTIAL, §9 |
| **P2-N02** | **CONDITIONAL** | 자동 S GET당218,421~5,596,362B 또는 N01 후7,369~104,537B entity | 백업 시점·auth/generation·복구 호환/보호 AppState, 중간~높음 | 의미 확인 후에만2순위 |
| P2-N03 | DEFER | 이상적304이면 B 대부분. 현재 bytes는 clock만 바뀌어도 달라져 달성률 미입증 | raw cache·freshness·304·generation 계약 변경, 높음 | 현재 구현 순서 제외 |
| P2-N04 | DEFER | 큰 upload의 오프라인 gzip 추정96.4~98.3%. 실제 upload 지원없음 | decoded size limit·인증 입력·money parsing·POST outcome, 높음 | 실제 빈도/필요 확인 후 별도 설계 |
| P2-N05 | NOT RECOMMENDED | 필드/history 제거의 안전한 절감 미입증 | full B·Snapshot/관계/복구·호환 훼손 | 현 단계에서 제외 |

T6.6A의 긴 random hex/한글 다양성10k control은 gzip 감소90.80%였다. 이 과거 entropy control을 현재 운영 보장으로 바꾸지 않는다. 기본 fixture의98%를 보편적 약속으로 쓰지 않는다.

### P2-N01 — 협상형 gzip 응답, Bundle/Snapshot allowlist

1. **문제:** 매 refresh는 큰 full Bundle, startup/resume은 별도 full Snapshot까지 무압축인 격리 backend 결과를 전송한다.
2. **소스 원인:** `backend/app/main.py`에 gzip middleware 없음. API는 `_headers`에 별도 codec을 넣지 않아도 IOClient가 gzip을 요청하고 해제를 지원한다. repo Apache 예시에도 활성 명시는 없다. **실제 운영 edge 압축 상태는 미확인**이다.
3. **baseline:** 표4의 실제 JSON/fixture wire와6개 byte-exact controls. 캡처된 두 route 원문의 gzip roundtrip은 byte/SHA 동일하다. 모바일 Bundle API body SHA는6개 HTTP control에서 확인했고 Snapshot download/save도 성공했다. Snapshot API의 직접 SHA 대조는 향후 구현 검증에 포함한다.
4. **기대 절감:** 10k B5,684,312→108,916B, S5,596,362→104,537B. HTTP header 증가까지 표에 반영했다. 운영이 이미 gzip이면 이 추가 이득을 청구할 수 없다.
5. **범위:** 향후 `backend/app/main.py`와 좁은 GET response coding wrapper/관련 tests. 우선 `/api/authoritative-state`, `/api/admin/snapshot`만 대상으로 검토. 본 턴 변경0개. 기존 명시 P0 두 목록에서 main은 보호 대상이 아니지만 이것이 구현 승인은 아니다. 다른 binding 잠금은 구현 승인 때 다시 확인하며 역사 hash를 고쳐 우회하지 않는다.
6. **호환성:** gzip 수락 클라이언트만, identity fallback·기존 Vary와Accept-Encoding 병합·Content-Length/Content-Disposition·no-store 유지. login/credential·APK/stream·mutation 응답·이미 인코딩된 응답은 제외해 범위를 한정한다. Web 변경은 하지 않는다.
7. **정확성/Offline 위험:** 해제된 원문을 strict admission에 그대로 전달한다. financial JSON 재직렬화·manifest 변경·캐시·검사 생략 없음. 인코딩 실패/잘린 stream이 publication으로 이어지지 않아야 한다. 인증 응답 압축 범위/side channel은 한정 검토하되 새 전면 감사를 만들지 않는다.
8. **검증:** 원문 SHA/길이·strict rejection corpus·서버↔모바일 compatibility, gzip/q=0/identity·기존 Vary·no-store·중복 encoding·에러/큰 파일·손상 stream을 검증. 동일 B/S wire bytes 감소와 요청 수/저장 결과 보존, bounded CPU/메모리 비용도 별도로 확인한다. payload byte 감소를 CPU 개선으로 채택하지 않는다.
9. **복잡도:** 작음~중간. 최소 크기·level·한 압축 경계는 후보 감사/승인 때 확정한다. proxy와 app 이중 압축을 피한다.
10. **권고:** **첫 후보**. 독립 후보 감사 후 owner가 구현 범위를 승인해야 한다. 운영 설정 확인/배포는 별도 명시 운영 승인 없이는 하지 않는다.

### P2-N02 — 자동 로컬 백업에서 이미 취득한 Snapshot 재사용 가능성

1. **문제:** `bootstrap/login/resume → refresh → saveLaunchSnapshot → GET /api/admin/snapshot`으로 이미 Bundle에 있는 full Snapshot과 별도의 백업 전송이 발생한다.
2. **원인:** `AppState.saveLaunchSnapshot`은 매번 download 후 repository.save를 호출한다. 이 관측은 **P1-S의 local file 검증 CPU와 다른 문제**다.
3. **baseline:** startup/resume에서 S GET1회가 실측됐다. 같은 frozen fixture의 S는 Bundle.snapshot 내용과 같은 서버 v7이다. 현재 서로 다른 호출은 시간 차이가 있을 수 있다.
4. **기대 절감:** 허용될 때 자동행동당 GET1회와 S payload 전부. N01 후의 추가 절감은 예를 들어10k104,537B이지5.60MB가 아니다. 실제 빈도는 모른다.
5. **범위:** 향후 보호 `AppState.saveLaunchSnapshot`와 현재 게시된 baseline의 snapshot 전달 연결/집중 tests. repository의 readback·검증·retention은 변경하지 않는다. 보호 변경에는 별도 scoped owner 승인이 필요하다.
6. **호환성:** 기존 Snapshot 파일 형식·모든 독립 share/manual download·실제 서버 restore 호환을 보존해야 한다. 검증된 Map을 새 파일로 직렬화하는 호환성도 먼저 확인한다.
7. **위험:** Bundle 취득 뒤 다른 서버 write가 있었을 수 있어 별도 S는 더 늦은 recovery point일 수 있다. **지금은 불필요 요청이라고 확정하지 않는다.** 인증/세대가 바뀐 baseline, Offline epoch, pending/finalizing 중의 재사용은 금지돼야 한다.
8. **검증:** owner가 자동 백업 시점 의미를 확인한 뒤, 현재 성공 게시와 같은 authority의 recoverable Snapshot인지 확인하고 local save/readback→서버 dry-run 복구, logout/generation/mutation 경합·실패·수동 fresh 동작을 집중 검증한다. 독립 시점이 필수면 후보를 버린다.
9. **복잡도:** 중간~높음. 별도 HTTP를 없어도 된다는 correctness 조건이 먼저다. wrapper로 보호 코드를 우회하지 않는다.
10. **권고:** **조건부2순위**, 추가 구현 승인 아님. P1-S/U를 재개하거나 TTL backup skip으로 바꾸지 않는다.

### P2-N03 — 조건부 GET/304

1. **문제:** 변경 없는 명시 refresh도 full B를 전송한다.
2. **원인:** 현재 ETag/If-None-Match 없음, no-store 정책, API는200 full bytes만 정상 admission한다.
3. **baseline:** frozen 반복은 동일 SHA지만 clock을1초 바꾸면 **authority/state는 같아도 전체 body가 달라졌다**(`snapshot.exported_at`). 실제 judgment 변동도 과거 근거에 있다.
4. **기대 절감:** 같은 representation을304로 검증할 수 있을 때 B 대부분이 상한이나 실제 적중률/절감은 미입증이다. revision/fingerprint만 같다는 이유로 body 동일성을 가정하지 않는다.
5. **범위:** backend representation validator와 보호 API client/coordinator/AppState·raw B 보관·재게시 경계의 명시 변경이 필요할 수 있다.
6. **호환성:** 현재304는 API의 비2xx 오류이며 body가 없어 strict parser에 넘길 수 없다. 원래 JSON baseline은 완전한 원문 B HTTP cache와 같지 않다.
7. **위험:** date/policy·auth/generation·pending/mutation barrier·freshness·privacy no-store, old cache의 authority 재사용. 로컬 금융 계산이나 캐시 재조립으로 fresh 서버 검사를 대체하면 안 된다.
8. **검증:** 동일/변경 representation, date·세대·auth·입력 확정 뒤·네트워크 실패·cache 손상/미존재·304 재시도와 원자 게시를 증명해야 한다.
9. **복잡도:** 높음, 좁은 header 추가로 끝나지 않는다.
10. **권고:** **DEFER**. generic TTL·무조건 stale reuse는 제안하지 않는다.

### P2-N04 — 큰 upload의 request gzip

1. **문제:** Mobile Wins는 B+J 전체, restore는 큰 JSON string을 upload한다.
2. **원인:** `_post`는 `jsonEncode` 문자열을 identity로 보내고 backend JSON/body-limit 경로에는 request decompression이 없다.
3. **baseline:** 표Upload의 실제 API 직렬화/전송. 일반 생성401B, 10k Mobile Wins5,597,848B/restore6,217,649B다. 실제 조정/restore commit 검증은 아니다.
4. **기대 절감:** 해당 예시의 offline gzip 크기는105,119/104,562B. 사용 빈도·운영 uplink·CPU 이득은 미측정이다.
5. **범위:** 보호 API client의 endpoint별 coding, backend `ApiBodyLimitMiddleware`/raw request·인증/restore/reconciliation 호환. middleware 위치를 바꿔 limit를 우회하지 않는다.
6. **호환성:** 기존 server는 gzip JSON을 자동 해석하지 않는다. 명시 capability/version과 backward compatibility가 먼저다. 일반 small POST 전체에 적용하지 않는다.
7. **위험:** compressed/decompressed 크기 제한·bomb·정확 money raw token·인증 password·digest/idempotency·응답 유실/ambiguous POST. 지원 오류/timeout 뒤 identity로 무조건 재전송하지 않는다.
8. **검증:** 같은 해제 bytes와 금융/identity/digest, 압축/해제 한도·손상/미지원 encoding, commit 응답 유실·재시도·pending 보존·기존 definite/unknown 분류를 집중 검증한다.
9. **복잡도:** 높음. 송신 헤더 하나만 붙이는 변경은 불충분하다.
10. **권고:** **DEFER**. 실제 대용량 업로드가 중요한지 확인한 뒤 별도 후보 설계로 한정한다.

### P2-N05 — raw history/필드 제거·분할 sync로 대체

1. **문제:** Snapshot은10k Bundle의 약98.45%이고 history가 크다.
2. **원인:** 현재 full B는 Offline Apply/restore와 typed UI의 공통 일관성 계약이다.
3. **baseline:** T6.6A의 바이트 귀속·현재 byte-identical B. 같은 entity의 raw/typed 중첩은 의미가 달라 전체 row byte 중복과 같지 않았다.
4. **기대 절감:** 안전하게 제거 가능한 양은 입증하지 않았다. logical cold 비율을 compressed 절감률로 제시하지 않는다.
5. **범위:** wire/schema/admission·관계·generation·atomic reconstruction·cache/recovery를 바꾸는 별도 protocol 작업이다.
6. **호환성:** legacy·Snapshot version·JSON Offline baseline·서버 계약에 광범위 영향.
7. **위험:** 필드/NULL/history를 빼면 required presence·manifest·복구/조정·active 관계를 약화할 수 있다.
8. **검증:** 새 일관성/복구 protocol 증명이 필요하며 본 조사로 면제할 수 없다.
9. **복잡도:** 높음, 현 mission의 국소 최적화가 아니다.
10. **권고:** **NOT RECOMMENDED**. experimental segmented는 켜지 않고, Next 대형 Snapshot 확장성 과제도 착수하지 않는다.

## 6. 제외·미측정과 한정 확인

- P1-R 이후 대표 정상 행동에서 추가 중복 GET은 입증하지 않았다. 다른 명시 refresh·mutation barrier를 단순 중복으로 지우거나 Phase1의 generic coalescing/파생값 작업을 다시 열지 않는다.
- Brotli는 과거 압축률이 더 좋았지만 현재 IOClient 자동 해제 경계는 gzip이며 새 모바일 decoder·실패/호환 검증이 필요해 첫 후보로 고르지 않았다. HTTP2·헤더 미세 조정도 큰 body 절감보다 먼저 추진할 근거가 없다.
- AI 자료의6 GET·전체 archive, 명시 APK 다운로드는 source inventory에 보존하지만 실제 빈도/bytes를 측정하지 않아 우선 구현 후보로 올리지 않았다. 월별 자료로 축소하면 month 목록·과거자료 의미를 따로 확인해야 한다. Web은 조사하지 않았다.
- N01 구현 승인 전 확인할 유한 질문은 ① 추후 별도 운영 승인하에서 실제 edge의 Content-Encoding 상태1회 확인, ② app/edge 중 단일 coding 경계 선택, ③ auth/no-store·Vary·기존 client와 큰 raw-byte rejection tests 보존이다. 현 턴에서는 운영 확인을 하지 않는다.
- N02는 자동 백업이 “마지막 admitted 시점”이어도 되는지 owner 계약 확인1회와 복구 호환 proof가 먼저다. 독립 late Snapshot이 필요하면 즉시 제외한다. N03의 validator 의미·N04의 빈도/한도는 후순위이며 새 조사 캠페인을 자동 시작하지 않는다.
- F01/G1·G2 미채택·실기기/ADB·T6.9·formal T6.6F·R1/배포 제약은 그대로다. 이번 문서는 독립 candidate Audit 입력이며 구현·릴리스 승인이 아니다.

## 7. 구현 순서 제안과 인계

**추천 shortlist는 N01 → N02(조건 통과 시에만)**다. N01로 압축을 먼저 검토한 뒤 N02의 추가 byte 이득을 그 baseline에서 평가한다. N03/N04는 DEFER, N05는 제외한다. 후보를 모두 구현해야 Phase2가 끝나는 것으로 정하지 않는다.

조사 완료 당시 단계는 **조사·후보 선정 COMPLETE / 구현 NOT AUTHORIZED**였다. 다음은 owner가 별도 시작하는 **Independent Phase 2 Candidate Audit**이며 감사 후 owner가 범위·수용 기준을 승인할 때만 구현한다. Phase3/4·확장성·Production 작업은 시작하지 않는다. 게시·보존·임시 정리 결과는 이 문서 마지막에 갱신한다.

### 조사 검증 기록

- host scenario test1건(84 wire transactions), Bundle byte-exact control test1건(6 GET), captured response blob gzip roundtrip이 통과했다. backend 합성 smoke3건 PASS(기존 warning1), 격리 사본의 npm build PASS다. Phase1의132건/성능 campaign은 다시 실행하지 않았다.
- 모든 측정용 server/client·DB·파일은 disposable synthetic 환경이었다. 실제 Mobile Wins/restore commit·실기기·운영 proxy는 검증하지 않았다. 본문에 표시한 upload 증빙 placeholder와 runtime J 변동 한계를 유지한다.

### 보존·게시 준비

- 시작7,947개 기존 파일 중 허용 문서3개 외7,944개는 SHA/mode 동일, 삭제0개다. 신규는 후보 문서와 단일 근거2개뿐이며 생산 코드·schema·잠금·P1 원시 근거·기존 dirty13개는 보존했다. staging은 비어 있었고 관련 경로만 게시한다. roadmap의 기존 성능 지도·역사·순위도 byte 동일하다.
- 후보5개×각10항목, Phase1 종료 체크리스트, 상대 문서 링크를 정적으로 확인했다. 실제 게시 commit과 push, 작업 소유 임시 정리 결과는 다음 기록에 갱신한다.

### 게시·정리·감사 인계

- Phase1 종료 `e5726b6def26af3d2f8c46984b718ca51ee49a80`는 origin/phase1/mitigations, Phase2 조사 **`41c608ff030a40ee27d7e70663664b2da695e680`**는 **origin/phase2/mobile-network push SUCCESS**이며 두 원격 tip을 확인했다. 이 후속 문서 commit은 게시/정리 내역만 기록한다. force-push·main merge·배포는 하지 않았다.
- 합성 DB3개·current raw response blob·harness/실제 invocation·84개 wire/6개 control·초기 준비 실패와 최종 검증·source hash를 단일 근거에 보존했다. task runner0개 확인 뒤 이번 작업 소유 임시303개 파일/링크(논리207,126,536B·관찰할당208,044,032B, 약198.4MiB)를 정리했다. dependency symlink138개는 대상을 따라가지 않고 제거했으며 기존 DB/WAL/cache·dirty source·역사 증거는 건드리지 않았다.
- 재현은 새 작업 소유 scratch에 `reproduction` 원문을 복원하고 ROOT/RUN을 맞춘다. backend fixture는 포함된 `synthetic_consistent_baseline_databases`를 입력으로 쓰거나, `backend_capture` SHA를 `response_body_blobs`에 연결해 payloads-N/name.json을 복원한다. 과거 P1-04 근거를 덮어쓰지 않는다. 내장 host_runner를 사용하며 run_network의과거 근거 읽기 부분은 task 사본에서 내장 runner로 연결할 수 있다. 정확한 실제 실행은 invocation에 있다. Flutter CLI/Android/운영 도구는 사용하지 않는다.
- **Phase1 CLOSED / Phase2 DISCOVERY COMPLETE / Phase2 IMPLEMENTATION NOT AUTHORIZED.** 다음은 독립 Phase2 Candidate Audit다. 생산 최적화0개, schema 변경0개다.

## 8. P2-N01 운영 압축 사전 점검 — 인증 문맥 부재로 차단

- **2026-11-03 / BLOCKED — AUTHENTICATION REQUIRED.** 독립 후보 감사의 `B — CONDITIONAL IMPLEMENTATION READINESS` 후 owner가 승인한 것은 두 endpoint의 identity/gzip GET 최대4회와 헤더 확인뿐이며, 구현·설정 변경·배포 승인이 아니다. 기준선은 `phase2/mobile-network / 70c84f5f07c8da78ec262b08fa76f2fdaf48e600`이다.
- 요청 전 [runbook](../runbook.md), [보안 운영](../security.md), 두 router와 인증 처리 소스를 확인했다. 문서상 HTTPS origin은 `https://money.hjkerman.re.kr`이다. 두 GET은 authoritative 조회와 Snapshot export이며 restore·reconciliation·mutation endpoint를 호출하지 않는 경로다. 다만 정상 인증 처리의 `last_seen_at` 갱신·서버 로그 등 통상 처리가 가능하므로, 실제 GET에 서버 측 효과가 전혀 없다고 주장하지 않는다. 배포된 동작은 이번에 관찰하지 못했다.
- 이 세션에 전달된 Money Note 세션/token/cookie 환경은 없으며, runbook이 지정한 기존 cookie jar도 존재하지 않았다. 연결 도구에도 기존 인증 브라우저 문맥이 제공되지 않았다. 임의의 credential 저장소·운영 DB·운영 `.env`를 탐색하지 않았고 로그인·새 자격 증명 취득·인증 우회도 하지 않았다.
- **실제 HTTP 요청0/4회.** 인증 없는401/403·HEAD·별도 health 요청으로 대체하지 않았다. 응답 본문·credential·PII는 수신·출력·저장하지 않았으며, 관찰한 응답 헤더도 없다.

| Endpoint | identity GET | gzip GET | 분류 |
| --- | --- | --- | --- |
| `/api/authoritative-state` | 미실행 | 미실행 | **INCONCLUSIVE** |
| `/api/admin/snapshot` | 미실행 | 미실행 | **INCONCLUSIVE** |

두 endpoint 모두 status·Content-Encoding·Vary·Content-Length·Transfer-Encoding·Cache-Control·본문 전송 여부·intermediary 변환 여부는 **미관찰**이다. 현재 N01 구현 적격성은 **INCONCLUSIVE**이며, 기존 합성 gzip 절감치로 운영의 미압축을 추정하지 않는다. Production·인증·backend/mobile 소스 변경0개다. 이 차단 기록만 문서에 추가하며 Phase1·다른 후보 조사는 재개하지 않는다.

**다음 행동 하나:** 소유자가 승인한 기존 인증 세션을 비밀값 노출 없이 사용할 경로를 지정한 뒤, 같은 두 endpoint·최대4회 한도에서 헤더 점검을 재개한다. N01 구현에는 이후 별도 owner 승인이 필요하다.


## 9. P2-N01 한정 구현 — IMPLEMENTED / VERIFICATION PARTIAL

2026-11-03. owner가 협상형 gzip의 개발 구현·host 검증·게시만 승인했다. 시작은 `phase2/mobile-network / 741e053c49bbbd3b6eaf9ff268e525af0b2f8a35`다. 이전 §8의 인증 부재 기록은 당시 사실로 보존한다. 이후 owner가 Snapshot의 인증200·Accept-Encoding:gzip·응답 Content-Encoding 부재를 확인했다. 별도 승인된 읽기 전용 대조에서 운영 image와 기록의 immutable ID가 일치했고, 기록된 `5d44ce318876927515047d4490fa2c186426ae4f`에는 Bundle router가 없었다. **이번 구현에서는 운영 접근0회**이며 Bundle의 운영 압축은 계속 미검증이다. 두 endpoint를 압축하는 개발 변경을 운영에 배포했다는 뜻이 아니다.

### 변경과 협상 계약

- `backend/app/routers/response_coding.py`를 추가하고 `admin.py:get_snapshot`, `authoritative_state.py:get_authoritative_state`의 완성된 응답에만 연결했다. 전역 middleware·Apache·모바일/웹 생산 코드 변경은 없다.
- 정확한 두 path의 GET·200·완성된 JSON bytes만 대상이다. 1,024B 이상을 gzip level6/mtime0으로 압축한다. 기존 serialization·금융 계산·Snapshot/manifest/SHA·admission·transaction·요청 수는 바꾸지 않는다. streaming·기존 Content-Encoding·오류·인증 실패·mutation·APK·다른 path는 제외한다.
- q-value의 높은 가중치를 선택하며 동률이면 gzip을 선택한다. gzip 명시 거부는 wildcard보다 우선한다. 미지정 identity는 wildcard의 명시적0 제외가 없으면 허용한다. header 없음/빈 값은 identity다. 중복 항목은 최저 가중치, 잘못된 q/parameter는 해당 항목0으로 보수 처리한다. 작은 응답을 포함해 허용 표현이 없으면 **빈406**이며 금지된 identity 본문을 강제하지 않는다.
- Vary에 기존 값과 Accept-Encoding을 병합한다(`*`는 이미 전체를 포함). Content-Disposition/no-store를 보존하고 압축 Content-Length를 설정한다. 원문 재직렬화·cross-request cache·추가 stream buffering은 없다. 압축이 끝나기 전 응답을 전송하지 않는다. 압축 실패 시 identity 허용이면 원문, 금지면 **빈503**이다.

### 전송량과 자원 비용

[독립 구현 근거](../benchmarks/p2-n01-implementation-evidence.json.gz), [재현 benchmark](../benchmarks/p2-n01-response-coding.py). 이전 discovery 근거는 덮어쓰지 않았다. N은 ledger row 수이며 all-current N이나 운영 분포가 아니다. 이전의 정확한6개 합성 원문 SHA·gzip 크기를 재사용/대조했다.

| N | 응답 | identity → gzip entity B | 단일 wall median / p95 ms | 단일 CPU median ms | 동시2개 batch wall / CPU median ms |
| --- | --- | --- | --- | --- | --- |
| 376 | Bundle | 306,370 → 11,474 | 1.842 / 1.877 | 1.843 | 2.195 / 4.146 |
| 376 | Snapshot | 218,421 → 7,369 | 1.097 / 1.100 | 1.099 | 1.441 / 2.783 |
| 1k | Bundle | 653,317 → 18,173 | 3.335 / 3.411 | 3.336 | 3.840 / 7.356 |
| 1k | Snapshot | 565,368 → 13,859 | 2.875 / 2.906 | 2.876 | 3.030 / 5.814 |
| 10k | Bundle | 5,684,312 → 108,916 | 27.157 / 27.330 | 27.159 | 28.176 / 55.814 |
| 10k | Snapshot | 5,596,362 → 104,537 | 23.741 / 24.445 | 23.742 | 28.364 / 55.887 |

- Python3.12.3/Linux,각24 configuration에5 warmup+20측정, 총480 batch·최종측정6.05초. fixture 생성·원문 read는 시간 밖이고 helper와 Response 준비만 잰다. identity 단일 median 약0.009~0.010ms다. CPU는 process time, 동시2개는 두 thread의 합산 CPU와 batch wall이다. 서로 더해 endpoint latency로 제시하지 않는다.
- worker 자체 `/proc` VmHWM은 gzip 단일27,484~32,924KiB, 동시27,940~33,664KiB였다. 측정 전 VmRSS 대비 최고 증가 단일196~396KiB, 동시572~1,080KiB다. 입력 bytes·Python runtime을 포함한 worker RSS이며 production 전체 메모리나 정확한 allocator 증분이 아니다. `ru_maxrss`가 부모의 이전 최고치를 물려받는 초기 관찰은 비용 근거에서 제외하고 raw에 별도 남겼다. 동시 응답은 메모리상 같은 합성 원문을 공유하는 두 요청의 coding 비용이며 실제 server 부하 시험이 아니다.
- entity 감소96.25~98.13%이며 TCP/TLS·운영 latency 개선은 주장하지 않는다. 다양한 실제 데이터의 압축률·운영 CPU는 미측정이다.

### 검증 결과와 미충족 조건

- backend **139 PASS**: 신규7건(협상20 subcase 포함), 기존 Bundle·Snapshot·export metadata·auth·freeze 완료 경계. 실제 두 endpoint의 raw wire gzip 해제 바이트 동일, 압축 길이·헤더·Snapshot `_validate_snapshot` 통과,401/422·관계없는 GET 보존, helper의 streaming/중복 압축 제외·406·압축 실패 fallback을 검증했다. 기존 deprecation warning1개다.
- 기존 모바일 **91 PASS**: authoritative acquisition57, Snapshot repository7, Bundle admission27. 직접 host runner 사용, Flutter CLI/Android/ADB는 실행하지 않았다. 격리 frontend 사본의 npm build도 PASS다.
- 신규 모바일 **6개 중5 PASS / 1 FAIL**: 실제 IOClient의6개 원문/SHA 동일·Bundle admission·Snapshot durable readback, 손상 magic·본문 중간 절단·CRC 오류 거부, 정상 gzip 안의 잘못된 Bundle digest/잘못된 Snapshot envelope 거부가 통과했다. 초기 raw-byte API 자체가 항상 throw해야 한다는 테스트는 실제 역할과 달라, 반환된 bytes의 **실제 admission까지 포함**해 판정했다. 로컬 Snapshot 저장소는 envelope/저장 바이트를 검사하고 full manifest 검증은 서버 restore의 책임이므로 독립 금융 검증 의무를 추가하지 않았다.
- **미충족: gzip 마지막8B trailer만 제거하면 현 Dart IOClient가 원문 bytes를 그대로 반환하고 Bundle/Snapshot 경계가 수용한다.** trailer 거부 테스트는 실패 상태 그대로 보존한다. 해제 내용은 원문 SHA와 동일하며, 금융 내용 손상·잘못된 mutation 게시가 관찰된 것은 아니다. transport framing의 엄격한 거부 조건을 충족했다고 주장하지 않는다. SDK/client 수정은 별도 승인 범위이므로 하지 않았다. 이 제한을 기존 SHA/admission 검사 완화로 해결하지 않는다.
- malformed/truncated gzip의 초기 실패·최종 matrix·runner·측정 raw와 source SHA는 구현 근거에 보존한다. 실패를 skip/성공으로 바꾸거나 역사 측정치를 재해석하지 않는다. 실제 HTTP 수 감소를 주장하지 않으며 정상 새 gzip control은 API당 GET1회다.

**판정: backend 구현 완료 / 검증 PARTIAL / 채택 확정 아님 / 운영 배포 금지.** 미충족 trailer 거부 조건과 byte-exact 정상 호환을 함께 독립 변경 감사에 전달한다. P2-N02~N05·Phase3/4·확장성·Phase1은 시작/재개하지 않는다.

**다음 행동 하나:** 독립 change-scoped implementation audit에서 변경과 미충족 trailer 거부 조건을 검토하고, client 수정이 필요하면 그 한정 범위를 owner가 별도 승인한다.

검증 종료 후 task runner0개를 확인하고 이번 작업 소유 scratch의 파일/링크304개(논리523,574,977B, symlink139개)를 정리했다. raw 측정·로그·host runner는 단일 구현 근거에 보존하고 기존 dependency 링크 대상을 따라가 삭제하지 않았다. 관련10개 경로만 개발 브랜치에 게시하며, 기존 dirty13개·미추적 작업·역사 근거와 source lock은 보존했다.


## 10. N01-A01 scoped correction — 구현 완료 / 독립 재감사 대기

owner가 독립 감사 **REWORK / N01-A01 MAJOR**의 모바일 transport 수정을 승인했다. 기준은 `phase2/mobile-network / a5adff9f3e7c04ba0c2ab348d6dc4fff054ad309`다. §9의 PARTIAL·5/6 PASS·trailer 수용과 원 audit 이력은 그대로 보존한다. 이번 수정은 구현 완료이며 P2-N01 최종 수용·배포 판정이 아니다.

- **원인:** dart:io autoUncompress는 incomplete member를 해제된 bytes로 반환할 수 있다. 완전한 JSON이면 후속 SHA/admission이 gzip framing 누락을 판별할 수 없다.
- **수정:** 새 `mobile/lib/src/response_coding_client.dart`를 API client에 연결했다. 두 GET만 `IOClient(HttpClient()..autoUncompress=false)`를 사용해 raw body를 끝까지 읽고 Content-Length를 검사한다. 원래 package:http/IOClient stack·인증 header·status·request·redirect·connection metadata·timeout/abort·retry 정책을 유지하고, 다른 endpoint는 기존 자동 해제 client로 보낸다. injected client도 raw coding 선언을 지켜야 하며 이미 해제된 본문에 gzip을 선언하면 이중 해제 대신 거부한다.
- **decoder:** cached `archive 3.6.1`, SDK ^3.0.0은 프로젝트 >=3.3.0 <4.0.0과 호환된다. SDK `dart pub get --offline` 결과 **archive 하나 추가**, 기존 crypto/path를 재사용하고 다른 upgrade는 없다. library `GZipDecoder.decodeBuffer(InputStream, verify:true)`가 framing/종료/trailer CRC32·ISIZE를 검사하고 최종 input.position이 원문 길이와 같은지 확인한다. 자체 inflate/parser·SDK fork는 없다.
- **명시 정책:** 단일 표준 member만 허용. library3.x가 검증하지 않는 FHCRC 등을 피하도록 optional/reserved flags가 있는 header는 거부한다. trailing garbage·concatenated members·unsupported/빈/복수 Content-Encoding도 거부한다. gzip body에 identity/누락 metadata가 있는 명백한 magic 조합은 거부하고 인코딩을 추측해 해제하지 않는다. identity는 그대로 호환된다. 해제 후 Content-Encoding/Transfer-Encoding을 제거하고 decoded Content-Length를 설정한다. 실패 시 성공 bytes·identity fallback·자동 재요청은 없다.
- **자원:** 압축 입력과 decoded 출력이 검증 완료까지 메모리에 존재하며 library 출력 capacity와 HTTP Response의 decoded bytes 사본이 일시적으로 겹칠 수 있다. 이전 전체 JSON admission의 문자열·모델 메모리는 그대로이며 cross-request cache가 없다. 임의의 작은 크기 상한을 추가하지 않았다. decoder는 main isolate에서 동작하므로 CPU/GC 비용이 있다. 기존 AppState에는 전역 동시 취득 상한이 없어 실제 in-flight 수는 겹친 호출에 따라 달라지고, 메모리도 응답 크기·동시 수에 비례한다. 두 connection pool은 endpoint별 기존 IOClient 동작을 유지하며 새 concurrency gate는 추가하지 않았다.
- **bounded 관찰:** 기존 376/1k/10k 두 응답6개를 실제 loopback으로 각1회 수신했다. 10k Bundle/Snapshot의 request+검증 wall 관찰은 약56.5/48.1ms, 전체 host VM/누적 테스트의 최고 RSS는 약255.4MiB였다. cold376은93.4ms였다. 반복통계·decoder 단독 CPU·isolated allocation·Android 메모리 수치가 아니며 이전 backend gzip CPU와 비교/합산하지 않는다. 상세 원시 수치는 구현 evidence의 `a01_correction.resources`에 있다. 최적화 캠페인을 새로 열지 않았다.
- **결과:** 기존 trailer 거부 테스트를 포함한6건 **6/6 PASS**. 추가4건 PASS: 두 endpoint×15 wire 시나리오(정상gzip/identity·누락 metadata·unsupported·ISIZE·trailer·CRC·magic·중간절단·garbage·다중member·flags·잘못된길이·조기종료·401), decoded header·cancel·15초 API timeout, 실제 AppState mutation 후 failure 보존. 정상6개는 원문 길이/SHA 동일. 잘못된 gzip은 transport 완료 전에 거부했고 Snapshot 임시/성공 backup도 게시하지 않았다.
- **application safety:** 실제 HTTP에서 정상 baseline 게시 후 POST1회→불완전 gzip GET1회 실패를 주입해 durable baseline 파일 bytes·기존 UI summary identity·pending 보존을 확인했다. POST 재전송 없음. 기존 authoritative acquisition57·Snapshot7·Bundle admission27도 **91 PASS**이며 owner/auth/generation·pending·publication·strict rejection corpus를 포함한다. 총 모바일 **101 PASS**, backend coding smoke7 PASS, 격리 npm build PASS다. Flutter CLI·Android·ADB·운영 접근은 없다.
- **한계:** optional gzip header/다중member는 의도적으로 미지원이며 서버의 현 gzip level6 단일member 응답과 호환된다. 현재 최신 archive version이나 전면 dependency 보안 감사를 수행한 것은 아니다. 실기기·실제 proxy·실제 대용량 동시 사용과 decoder CPU의 정량 수용은 미검증이다. 금융/admission·AppState·OfflineStore·backend·웹·인증 계약은 수정하지 않았다.

**현재 처분:** N01-A01 구현·focused 검증 완료, 독립 correction re-audit 대기. 원래 PARTIAL/REWORK를 과거 PASS로 바꾸지 않는다. 다음 행동은 **독립 N01-A01 correction re-audit** 하나다. 다른 후보·Phase3/4·배포는 시작하지 않는다.

A01 증거 보존 후 task runner0개를 확인하고 이번 scratch의 파일/링크304개(논리865,187,473B)를 정리했다. 기존 cache·dependency symlink 대상은 삭제하지 않았다. correction 관련10개 경로만 개발 브랜치에 게시하고 원래 dirty13개와 역사 source lock을 보존한다.


## 11. N01-A01-R1 — 두 번째 correction / 독립 targeted 재감사 대기

기준 `phase2/mobile-network / 2d3351847b569efadbb330543b7dd92b418444bd`. owner는 targeted audit **REWORK — CORRECTION INCOMPLETE / N01-A01-R1 MAJOR**를 받아 남은 DEFLATE 완전성 수정만 승인했다. §9 원 PARTIAL → 첫 REWORK → §10 첫 correction COMPLETE·감사 대기 → targeted REWORK → 본 두 번째 correction 순서를 보존한다. 과거 판정을 성공으로 바꾸지 않는다.

- **원인 재현:** archive3.6.1의 reserved BTYPE3 처리에서 false 반환이 정상 종료처럼 해석됐다. 정확한 JSON을 non-final stored blocks로 보내고 `0x07`로 끝내 CRC/ISIZE를 붙인 입력을 archive/구 transport가 수용했다. 수정 전 두 실제 API GET도 SHA가 같은 bytes를 성공 반환했다. 사용자 지정 감사 디렉터리가 실제 존재해 합성 witness를 읽기 전용 복사했으며, 테스트 generator로 재구성한 Bundle 반례 SHA `4f94389bcc067b4e756cc0e94f65ef8be9f2f8e04116add5fb83da93d0574e5e`가 감사자의 bad.gz와 정확히 일치한다. Python과 SDK는 이를 거부했다.
- **선택 B:** 가용 cached decoder는 archive3.6.1뿐이다. dependency/lockfile을 바꾸지 않고 기존 archive verify:true·완전한 trailer·CRC/ISIZE·전체 입력 소비 검사 뒤에 SDK의 독립 zlib validation pass를 추가했다. SDK가 BTYPE3/잘못된 final block 구조를 거부하고, SDK만으로 부족했던 trailer 보장은 archive가 담당한다. **둘 다 성공해야** bytes를 반환한다. SDK output을 chunk별로 archive output과 길이·바이트 대조하고 close 완료를 확인한다. 같은 결함 parser의 자기 검증이 아니며 자체 DEFLATE parser·SDK fork·서버 출력 변경은 없다.
- 단일 member·flags0 정책, trailing/concat 거부, identity·인증·status·timeout/abort·헤더 정합성·자동 재시도 없음은 그대로다. 비교 Sink는 출력 비교만 하며 압축 문법을 해석하지 않는다. SDK 출력의 두 번째 전체 body를 저장하지 않지만 native chunk/buffer는 추가된다. 기존 archive decoded body·압축 input·HTTP decoded representation의 일시 중복과 동시 요청에 따른 메모리 증가는 남으며 새 cache·작은 크기 상한·concurrency 정책은 추가하지 않았다.
- **회귀:** 수정 전 reserved witness의 두 endpoint 수용을 별도 로그/JSON으로 보존하고, 같은 assertion이 수정 후 통과했다. 실제 loopback → ResponseCodingClient → MoneyNoteApiClient에서 valid-final은 수용, reserved/missing-final/non-final-empty는 두 endpoint 모두 거부(GET 각1회). 기존 matrix의 trailer·CRC·ISIZE·본문절단·header/encoding·길이·조기종료·garbage/concat 거부와 정상 identity/gzip·SHA를 유지했다. 기존 테스트 삭제·skip·기대 완화는 없다.
- 모바일 **103 PASS**(coding6·transport4·신규 witness/resource2·기존 취득57/backup7/admission27), backend coding smoke7 PASS, 격리 npm build PASS. 실제 mutation 후 transport 실패에서 durable baseline·기존 summary·pending 보존, POST 재전송 없음 및 실패 Snapshot 게시 없음도 기존 focused tests로 확인했다. AppState/OfflineStore·금융·schema·auth·backend·웹 생산 코드는 변경하지 않았다.

추가 SDK pass의 bounded 관찰(각5 warmup+20표본, archive decode·fixture read는 측정 밖, SDK+동일 역할 streaming 비교 probe):

| ledger N | 응답 | 추가 wall median ms | CPU batch/20 ms |
| --- | --- | --- | --- |
| 376 | bundle | 1.329 | 1.000 |
| 376 | snapshot | 1.019 | 1.000 |
| 1000 | bundle | 2.555 | 2.500 |
| 1000 | snapshot | 2.200 | 2.500 |
| 10000 | bundle | 22.036 | 21.500 |
| 10000 | snapshot | 21.742 | 22.000 |

CPU는 Linux process utime+stime tick batch 차분이며 개별 median이 아니다. wall raw20개와 RSS는 구현 evidence의 `a01_r1_correction`에 있다. 전체 host VM/선행 witness의 RSS·GC를 포함하므로 RSS 차이를 독립 allocation 비용으로 보지 않는다. streaming probe는 production 비교와 같은 역할의 benchmark helper로, 서버·HTTP·archive 전체 latency 측정이 아니다. 실기기/운영 성능 개선은 주장하지 않는다. 두 번의 독립 decode로 CPU가 추가되는 trade-off이며 SDK 단독으로 trailer가 검증된다고 주장하지 않는다.

**현재 처분: R1 수정·focused 검증 완료 / 독립 targeted 재감사 대기.** 남은 지원 제한은 optional gzip header·연결 members 미지원과 buffered main-isolate 비용이다. 새 관찰 실패는 없지만 P2-N01 최종 수용·배포·Phase2 종료는 선언하지 않는다. 다음 행동은 **Independent N01-A01-R1 targeted re-audit** 하나다.

R1 raw evidence 보존 뒤 task runner0개 확인, 이번 scratch 파일/링크296개(논리610,466,660B)를 정리했다. 원 감사 디렉터리와 기존 dependency 링크 대상·dirty13개·historical source lock은 보존했다. 관련6개 경로만 개발 브랜치에 게시한다.


## 12. P2-N01 최종 수용 — ACCEPTED

owner가 최종 독립 감사 **PASS — N01-A01-R1 RESOLVED**를 수령하고 N01을 명시적으로 수용했다. N01-A01과 N01-A01-R1은 CLOSED·blocking findings 없음이다. 최초 구현 `a5adff9f3e7c04ba0c2ab348d6dc4fff054ad309`, 첫 correction `2d3351847b569efadbb330543b7dd92b418444bd`, 최종 수용 correction `13ef6e97590d27f32939409a2cc23d0d967263e2`를 기록한다. 추가 구현 감사 없이 수용하며 과거 PARTIAL→REWORK→첫 correction→targeted REWORK→두 번째 correction 이력은 §9~11과 immutable/raw evidence에 보존한다.

bytes·CPU·메모리 근거는 host-only 합성 관찰이며 운영 latency나 실기기 보장은 아니다. 운영 Snapshot의 미압축 관찰과 구 배포 revision의 Bundle 부재도 유지한다. **Production deployment NOT AUTHORIZED / NOT PERFORMED, main merge 없음.** 본 수용에서 N01 소스·benchmark evidence는 변경하지 않는다. N02는 별도 조사만 승인됐고 구현하지 않는다.

**N02 조사 완료 — DEFER, C 독립 Snapshot GET 유지 권고.** 실제 순서·T1/T3 복구 의미·post-gzip entity 절감(10k104,537B)과 대안 비교는 [N02 조사](../archive/phase2/phase2-n02-snapshot-reuse-investigation.md)에 둔다. 구현0개, N01 코드·benchmark evidence 변경0개다.
