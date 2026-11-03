# Phase 2 모바일 네트워크 전송량 조사·후보

**DISCOVERY COMPLETE — 후보 감사 대기, 구현0개.** Phase 1은 owner가 전달한 최종 독립 감사 **PASS — MITIGATION ACCEPTED**로 종료했다. R-01 채택·활성132 PASS·GET4→1·원110.37% 실패와1회 예외·거부/원복 기록을 보존한다. S/U는 DEFERRED이며 재개하지 않는다. 전체 개발 종료·배포 준비 판정이 아니다.

## 1. 기준선·범위

- 조사 시작 `cd3f385c20c02897f484e9f77c1260b7859bdaf0` / `phase1/mitigations`. 종료 기록 commit **`e5726b6def26af3d2f8c46984b718ca51ee49a80`**를 게시한 뒤 같은 HEAD에서 인덱스·기존 dirty13개를 유지해 **`phase2/mobile-network`**를 생성했다. main merge·배포는 하지 않았다.
- 현재 생산 소스·backend schema·금융/인증/Offline/동기화 계약은 변경하지 않았다. 조사 도구는 disposable 작업 사본에만 두었다. Flutter CLI·Android·ADB·emulator·운영 DB/API·운영 proxy 설정을 사용하지 않았다.
- 데이터/계약의 원본은 [domain-model](../domain-model.md), [architecture](../architecture.md), [offline-mode](../offline-mode.md), [security](../security.md)다. 정상 OfflineStore는 JSON 파일이다. strict admission·Snapshot/관계·auth/revision/generation·durable pending/reconciliation·원자 게시·복구·mutation 완료 의미를 유지한다.
- [단일 raw/재현 근거](../benchmarks/phase2-mobile-network-evidence.json.gz)에 현재 source SHA·실제 응답·일관된 합성 DB·시나리오별 HTTP 계수·Dart/ Python 원문과 invocation을 둔다. Runtime은 Linux/i7-8750H, Python3.12.3, Flutter engine3.47.4/Dart3.13.3의 **직접 host runner debug JIT**다. 숫자는 운영·실기기 전송량이 아니다.

| 재사용한 근거 | 현재 대조·효력 |
| --- | --- |
| [T6.5B-3/현재 상태](../project-state.md) | 정상14→1 GET, mutation+취득15→2 유지. 이번 실제 AppState replay도 저장2회였다. 과거14 GET을 새 제거 후보로 취급하지 않음 |
| [T6.6A](../t66/a/t66a-payload-attribution.md) | 기존 gzip/IOClient·정확 byte 귀속 재사용. 새376/1k/10k Bundle SHA가 과거 attribution의 각 SHA와 **모두 동일**했다. codec campaign을 반복하지 않음 |
| [P1-04](p1-04-backend-sql-presenter-performance-results.md) | 보존된 합성 consistent DB3개를 검증·복원해 현재 endpoint를 호출. backend CPU ms는 bytes/절감량으로 환산하지 않음 |
| [공유 P1 장부](phase1-mitigation-plan.md) | R-01의 GET4→1은 이미 현재 baseline에 반영. 이번 Phase 2 절감에 다시 더하지 않음. 로컬 Snapshot 검증 CPU인 S도 네트워크 절감과 구분 |

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
| **P2-N01** | **HIGH PRIORITY** | B/S entity96.25~98.13% 감소(합성기본). 10k startup HTTP11,282,664→215,535B 대조 | byte-preserving HTTP coding, 작음~중간. 운영이 이미 압축하면 추가 절감0일 수 있음 | 첫 구현 후보 감사 |
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

현재 단계는 **조사·후보 선정 COMPLETE / 구현 NOT AUTHORIZED**다. 다음은 owner가 별도 시작하는 **Independent Phase 2 Candidate Audit**이며 감사 후 owner가 범위·수용 기준을 승인할 때만 구현한다. Phase3/4·확장성·Production 작업은 시작하지 않는다. 게시·보존·임시 정리 결과는 이 문서 마지막에 갱신한다.

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
