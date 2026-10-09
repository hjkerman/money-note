# T6.5B-3 구현 결과 — 독립 통합 감사 대기

## A. 최종 구현 판정

`READY FOR INDEPENDENT B-3/B-4 INTEGRATED AUDIT`를 위한 구현 및 내부 검증을 완료했다. 독립 감사 승인, 실기기 성능 승인, 운영 배포 완료를 뜻하지 않는다. 아래 측정은 HOST/synthetic 환경의 구현 sanity 결과다.

## B. 시작 Git 상태

`main`에서 HEAD/main/origin/main/실제 remote main 모두 `68aae70c31c23b262f257d03aa4f56076d654e06`, working tree clean을 확인한 뒤 시작했다. 커밋 직전에도 실제 remote main이 이 기준선인 것을 확인했다.

## C. 승인된 신뢰 경계

`AGENTS.md`, architecture의 서버 authority 경계, domain/project-state/known-issues, Offline/recovery 및 security/runbook 계약을 확인했다. 금융 계산은 서버 소유다. 모바일은 A/B admission·identity·복구 가능성·generation·durable publication을 지킨다. OfflineProjection, 서버 금융 계산, protocol 및 persistence format은 변경하지 않았다.

## D. 기존 정상 취득

기존 경로는 B0 → 8개 독립 core GET → status 후 cash 및 core join 후 3개 정책 GET → B1이다. Cash와 정책 branch는 겹치며 마지막 join 뒤 B1을 읽는다. 따라서 refresh 14회/4개 RTT 단계, 성공 mutation은 mutation 한 번이 앞서 15회/5개 단계다. 기존 canonical 계산을 모바일에서 재실행하는 구조는 아니었다.

## E. 전체 authoritative call-site

모든 아래 call-site는 하나의 `_refreshAuthoritativeState`와 정상 coordinator를 공유한다.

| 호출 | 기존 경계 및 이번 처리 |
|---|---|
| `refresh`, bootstrap, login, foreground | 전체 candidate 취득만 bundle로 전환; health/auth/launch Snapshot은 유지 |
| `refreshInputArea`, `refreshCashArea`, `refreshEntriesArea` | Online 전체 취득; Offline이면 health-only |
| `refreshSettlementArea`, `refreshPanelManagementArea` | Online 전체 취득; Offline이면 health-only |
| `refreshPlannedManagementArea` | 정기 area도 같은 전체 취득 경계 |
| `refreshSettingsArea` | 설정 PATCH/정책 변경 뒤 동일 취득 경계 |
| connectivity recovery | health, 필요 시 me, 그 뒤 동일 취득 경계 |
| `rebuildAfterOnlineWrite` | read-only rebuild; unknown marker는 읽기 성공만으로 제거하지 않음 |
| `_finalizeCommittedMobileWins`, `_finalizeServerWins` | `allowBaselineWhileFinalizing`을 유지한 같은 bundle 취득; resolved reconciliation ID 보존 |

## F. Coordinator 변경

정상 `acquire`와 diagnostic helper가 `_acquireBundle` 하나를 공유한다. Network 전후와 candidate 반환 직전에 owner/ticket/auth/lineage/mode를 재검증한다. 같은 검증된 응답에서 candidate/envelope를 만들며 acquisition 자체는 게시·설치·pending 정리를 하지 않는다. 기존 구현은 `acquireLegacyForDiagnostics`라는 명시적 회귀 oracle로 보존했으며 runtime fallback이 아니다.

## G. API-client 통합

기존 diagnostic byte transport를 `authoritativeStateBytes`로 승격하고 이전 이름은 alias로 보존했다. 기존 `_request` timeout, `_headers`의 Bearer 인증, configured base URL, HTTP 오류 분류를 사용한다. 성공 body는 원문 bytes로 strict parser에 전달한다. Generic JSON parse로 raw numeric token을 잃지 않는다.

## H. B-2 admission

`AuthoritativeBundle.decode(...).toCoherentBundle(...)`을 그대로 사용한다. Bundle/parser/contract/Unicode/Snapshot/canonical admission 파일 및 generated registry는 시작 commit 대비 변경하지 않았다. Raw-money, duplicate JSON key, required/type/version, Unicode scalar, hash/fingerprint, N4 및 A/B 검사를 우회하거나 대체하지 않았다.

## I–J. Principal·auth·request·mutation generation

정상 transport 통합 테스트로 wrong principal, logout, 같은 ID 재로그인, 다른 ID 재로그인, selectedUser 변경, 뒤늦은 refresh, 새 mutation, mode 전환을 검증했다. Request ticket의 세 generation을 network 전후와 publication까지 유지한다.

집중 검토에서 직접 user ID 변경이 generation 증가 없이 일어나는 두 같은-root 반례를 먼저 실패 테스트로 재현했다. (1) baseline publication 대기 중 owner 교체, (2) native permission 대기 중 owner 교체 후 새 principal bundle을 받는 경우다. Publication guard를 최초 `authenticatedUser`, 현재 user, candidate user 모두의 일치로 보강했다. 이전 owner marker를 새 owner 취득으로 정리하지 못한다. 금융 알고리즘 변경은 없다.

## K. Durable publication 순서

검증된 bundle → 현재 ticket/owner/lineage 확인 → 완전한 OfflineBaseline → 기존 `replaceBaseline(beforePublish: guard)` → 재검증 → 확정 pending만 cleanup → 재검증 → 전체 application state 설치 → 완료 알림 순서다. Baseline·pending·journal format은 불변이다. 기존 OfflineStore의 임시 파일 flush/readback·원자적 rename 경계를 재사용했다.

## L–M. 성공 mutation과 실패/unknown

정상 카드·cash·Claim·Family·fixed/planned 확인·settings는 기존 mutation 응답을 받은 뒤 bundle을 취득한다. 카드 실측은 POST+GET, 설정은 PATCH+GET이다. POST의 전송/응답 유실을 GET 성공으로 확정하지 않는다. Confirmed POST 뒤 bundle timeout/401/403/500/connection failure/partial JSON/invalid JSON/version/money/Unicode/hash/principal 실패는 committed rebuild marker를 유지하고 UI 성공을 내지 않는다. Definite 422에는 GET을 보내지 않는다.

## N. Pending recovery

| 상태/진입 | HTTP 및 안전성 |
|---|---|
| manual committed rebuild | bundle GET 1회; durable publication 후 같은 marker cleanup |
| manual unknown rebuild | bundle GET 1회가 성공해도 marker 유지, 재등록·Offline 차단 |
| authenticated connectivity 복구 | 성공 attempt는 health + bundle; 금융 취득은 1회 |
| user 없는 connectivity 복구 | health + me + bundle; 실패 시 기존 bounded probe 정책 |
| foreground committed 복구 | bundle 뒤 별도 launch Snapshot 요청 유지; mutation 재전송 없음 |
| 같은 input/key의 idempotent panel 확인 | 기존 explicit POST receipt + bundle; 다른 marker를 retire하지 않음 |
| reconciliation 결과 미확정 | 기존 health/status 확인; bundle만으로 committed 판정하지 않음 |

Connectivity/foreground의 부가 요청은 소스상 기존 동작이며 아래 성공 submit/refresh 측정에서 숨긴 요청이 아니다. 실패 테스트의 자동 probe는 test delay로 분리했고, 기존 recovery 회귀 suite도 별도로 통과했다.

## O–P. Offline/reconciliation·mode

Offline에서는 frozen B와 input-only J를 유지하고 health만 확인한다. Finalizing 특별 publication 권한, resolved reconciliation ID, 양쪽 recovery artifact, Mobile Wins의 Apply(B,J), Server Wins, journal cleanup 및 unknown/committed 구분을 그대로 보존했다. 일반 refresh가 finalizing 또는 recovery-blocked mode를 우회하지 못한다.

## Q–R. 실제 정상 HTTP topology

정상 AppState를 real API client와 request-recording transport로 실행했다. Synthetic 실제 FastAPI와의 HOST trace도 같은 결과다.

| 동작 | 전체 operation HTTP | 금융 mutation/취득 HTTP | 요청 |
|---|---:|---:|---|
| explicit refresh | 1 | 1 | GET `/api/authoritative-state` |
| card | 2 | 2 | POST `/api/entries` → bundle GET |
| cash | 2 | 2 | POST `/api/cash-flows` → bundle GET |
| Claim/Family | 각각 2 | 2 | POST `/api/month/current/panels` → bundle GET |
| fixed | 2 | 2 | POST `/api/month/current/panels/4/confirm-fixed` → bundle GET |
| planned | 2 | 2 | POST `/api/month/current/planned/10/confirm` → bundle GET |
| settings | 2 | 2 | PATCH `/api/settings/card_limit` → bundle GET |

직접 payment-event mutation을 수행하는 모바일 AppState command는 없다. Existing 할인/삭제/월마감 command도 같은 refresh 경계를 공유하며 별도 API를 삭제하지 않았다.

Login trace는 health + mobile-login POST + bundle GET + admin Snapshot GET의 4회다. Logged-in foreground는 bundle + launch Snapshot의 2회 구조를 유지한다. Native permission/inbox/configuration은 HTTP가 아닌 channel 호출이다. 독립 policy 조회/preview/backup/reconciliation business request는 금융 refresh graph에서 제거하는 대상이 아니다.

성공 정상 금융 취득의 legacy B0/B1, summary, entries, panels, cash, payment, judgment, policy GET은 0회다. Legacy tests와 명시적 oracle 외 production caller가 없음을 source search로 확인했다. Backend legacy endpoint는 변경/삭제하지 않았다.

## S–T. Error·race 검증

새 통합 테스트는 empty/existing store 모두에서 오류를 주입하고 기존 baseline bytes, UI summary, pending status를 확인한다. No implicit fallback이다. Refresh A/B의 역순 완료, mutation 시작, Offline 전환, logout/relogin, publication 대기 중 owner 변화에서 늦은 결과가 이전 authority를 덮지 못한다. Admission 실패는 `invalid_authoritative_bundle`, acquisition generation 실패는 `stale_authoritative_bundle`이며 기존 HTTP/transport 분류를 유지한다.

## U. Crash/durability 경계

실제 임시 durable 파일과 새 AppState/Store를 사용한 failure injection 및 restart 검증이다. 모바일 process의 13개 instruction 위치마다 물리 SIGKILL을 수행했다고 주장하지 않는다.

| 중단 경계 | 남는 durable 상태와 재개 계약 |
|---|---|
| POST 전 marker 저장 실패 | HTTP 미실행, 새 mutation 가능 |
| POST in-flight/commit 응답 유실 | unknown marker, 자동 POST replay 금지 |
| confirmed receipt 뒤 committed marker 저장 실패 | disk unknown 유지; 같은 process는 known receipt, restart는 unknown 취급 |
| committed marker 뒤 bundle 시작 전/대기/invalid response | committed marker 유지; read-only rebuild |
| validated candidate 뒤 publication 실패 | old B 유지, candidate 미설치, marker 유지 |
| temp baseline flush 뒤 guard 실패 | 기존 원자적 publication 회귀로 rename·UI 차단 |
| durable baseline 뒤 marker cleanup 실패 | fresh B는 존재하나 UI 완료/Offline gated; 다음 read-only rebuild |
| marker cleanup 뒤 UI/최종 notification 전 | B가 이미 durable하며 journal replay하지 않음; UI는 restart 시 재구성 |

새 테스트의 publication/cleanup/committed-marker 실패와 restart를 모두 통과했다. 기존 pre-request/response-loss, late temp-flush logout, foreground recovery, reconciliation cleanup-boundary restart 회귀도 최종 전체 suite에서 재실행했다.

## V–W. Candidate·baseline 동등성

13개 state를 다시 실행했다: 저장소 보존 fixture 8개, 이번 실제 backend에서 생성한 current-like/1k/5k/10k 4개, 보존된 synthetic confirmed-heavy 600 1개다. Legacy coordinator 14회와 정상 bundle coordinator 1회를 비교하고 actual AppState의 publication/readback을 비교했다. 모든 baseline field·Snapshot·policy·financial values·ordering·null/false·revision/evaluation/fingerprint가 논리적으로 같았다. Volatile `synced_at`만 고정/제어했다. 고정 timestamp의 old/new baseline은 durable bytes도 동일했다. 보존 fixture 8개는 새 committed normal AppState regression에 포함한다.

Unavailable 과거 `/tmp` 원본 corpus를 그대로 재실행했다고 주장하지 않는다. 현재 8개 fixture에서 4,594개 required-field omission을 재구성해 직접 presence 실패를 확인했으며, committed 전체 admission/Unicode/N4/trust-boundary 공격 suite도 통과했다. 이전 감사의 4,626이나 소실된 원본 4,650을 이번 재실행 수로 재사용하지 않는다.

## X. UI 완료 경계

Store publication gate에서 submit이 busy이고 UI summary가 아직 설치되지 않았으며 committed marker가 남아 있음을 확인했다. Gate 해제와 durable publication/cleanup 뒤에만 success와 전체 candidate 설치가 이뤄진다. `lastSuccessfulSyncAt`, conservative estimate reset, network prompt, listeners의 기존 설치 코드는 변경하지 않았다.

## Y. HOST/synthetic 성능 sanity

Linux x86_64, Flutter 3.47.4 test JIT, Python 3.12.3, SQLite 3.45.1. 정확한 시작 commit의 모바일 소스를 별도 archive해 before로 사용했다. Loopback `127.0.0.1:18081`의 threaded bridge가 실제 FastAPI TestClient와 migrated 임시 DB를 호출했다. 운영 데이터/credential을 사용하지 않았다. Before/after를 교대했고 각 dataset/operation에서 warmup 2회 + sample 5회다. +150ms는 warmup 1회 + sample 3회다.

아래 total은 AppState의 HTTP·admission·candidate·durable baseline·pending 완료를 포함한다. 외부 backend reset/metrics 요청은 benchmark 관리용이며 application operation의 HTTP에 섞지 않았다. Dataset은 376/1k/5k/10k로 시작하고 paired zero-amount card 입력으로 14행 증가했다(current-like +150ms까지는 총 22행 증가). 일부 다른 회귀 작업과 HOST 자원을 공유했다. 작은 sample의 p95는 max와 같으며 보편적인 tail 개선을 약속하지 않는다. 실기기 성능이 아니다.

| 초기 ledger rows | refresh before median/p95 ms | refresh after median/p95 ms | card before median/p95 ms | card after median/p95 ms |
|---:|---:|---:|---:|---:|
| 376 | 517.269 / 551.259 | 205.689 / 268.738 | 488.316 / 501.037 | 296.828 / 363.857 |
| 1k | 849.361 / 914.434 | 445.844 / 689.678 | 876.348 / 1474.828 | 557.263 / 1243.739 |
| 5k | 3008.588 / 3141.194 | 1959.126 / 2244.021 | 3110.942 / 3988.025 | 2022.468 / 2139.304 |
| 10k | 4547.149 / 6250.245 | 3913.511 / 4180.892 | 5122.044 / 6307.794 | 4148.563 / 4495.773 |

+150ms refresh: 1135.967/1151.660 → 351.528/379.858ms. Card: 1357.582/1391.076 → 602.486/628.176ms. Financial RTT DAG는 refresh 4→1, submit 5→2다. 전체 RTT slope fit/RTT matrix/독립 contention 감사는 이후 세션이다.

| rows | refresh old/new body bytes median | new endpoint duration median ms | new baseline publication median ms |
|---:|---:|---:|---:|
| 376 | 537755 / 316094 | 95.330 | 23.396 |
| 1k | 1226681 / 660561 | 175.698 | 39.300 |
| 5k | 5658663 / 2876552 | 858.813 | 142.052 |
| 10k | 11198693 / 5646571 | 1671.454 | 295.831 |

Body bytes는 UTF-8 JSON body이며 header/TLS bytes가 아니다. 이 bridge 측정에는 compression을 추가하지 않았다. 본 fixture의 크기는 다른 specimen의 7MB 숫자와 다르며 payload contract를 좁힌 결과가 아니다.

10k frozen initial body의 별도 stage median: UTF-8 32.051ms, raw money 456.220ms, JSON decode 88.311ms, Unicode 12.414ms, presence/type 176.057ms, money 9.554ms, Snapshot/authority/relationship 906.589ms, freeze 65.092ms, typed candidate 0.468ms. 이 stage 측정은 actual pipeline에 추가 work를 넣은 것이 아니라 별도 frozen-body 진단이다. Stage median의 합을 total의 정확한 분해로 취급하지 않는다. 큰 validation/serialization 비용은 남아 있다.

모든 기록된 operation HTTP는 200이었지만 알려진 auth-session `database is locked` 결함이 해결됐다는 증거는 아니다. SQL/lock exposure의 전체 통제 matrix는 이번 sanity 범위가 아니며 backend runtime은 불변이다.

## Z. B-2/Unicode/N4 회귀

기존 full admission tests와 actual backend Unicode/N4 migrated-DB tests를 재실행했다. Category C-only 허용과 A/B fail-closed 계약은 그대로다. 금융 계산 재검증·Unicode normalization·storage format 변경은 없다.

## AA. 전체 regression 및 실제 명령

성공 로그 전체 대신 결과와 artifact를 기록한다. 모든 테스트는 개발 checkout/임시 DB만 사용했다.

| 실행 명령 | 이번 실제 결과 |
|---|---|
| backend에서 `../.venv/bin/python -m pytest -q` | 606 passed, 1540 subtests passed, warning 1 |
| backend에서 `../.venv/bin/python -m pytest -q tests/test_authoritative_state.py tests/test_bundle_unicode.py tests/test_bundle_idempotency_constraint.py tests/test_snapshot.py tests/test_versioned_migrations.py` | 125 passed, 493 subtests passed, warning 1 |
| root에서 `.venv/bin/python -m ruff check backend/app backend/tests scripts` | PASS |
| mobile에서 `flutter test --reporter expanded` | 539 passed |
| mobile에서 `flutter test --reporter expanded test/authoritative_acquisition_test.dart` | 57 passed |
| mobile에서 `flutter analyze` | No issues found |
| frontend에서 `npm test -- --run`, `npm run lint`, `npm run build` | 6 files/21 tests, lint/build PASS |
| mobile/android에서 `./gradlew :app:testDebugUnitTest --rerun-tasks` | 실제 재실행 22 tests, failures/errors 0 |
| mobile에서 `flutter build apk --debug` | PASS; 기기 설치/배포 없음 |
| root에서 `.venv/bin/python -m pytest -q scripts/tests` | 27 passed; 대역/임시 파일만 사용 |
| root에서 `.venv/bin/python scripts/generate_bundle_policy.py --check` | PASS |
| `bash -n scripts/deploy-server.sh scripts/release-mobile.sh scripts/dev-server.sh`, `git diff --check` | PASS |

초기 root cwd의 backend pytest는 crash subprocess가 `app`을 import하지 못해 4개 subtest가 실패했다. 문서 지정 backend cwd에서 전체 재실행해 위 결과를 확인했다. Registry 도구 이름의 첫 오기도 실제 `generate_bundle_policy.py`로 바로잡아 성공했다. 성공 결과로 이 초기 실행 실패를 숨기지 않는다.

Backend warning은 기존 Starlette/httpx deprecation이다. Android는 기존 Kotlin/Gradle/AGP 지원·SDK XML·deprecated feature 경고가 있다. Dependency version upgrade는 수행하지 않았다. ShellCheck는 미설치여서 생략했다. Production-reading deployment dry-run, physical device, APK 설치, 독립 감사는 실행하지 않았다.

## AB. 변경 파일과 diff

Runtime은 `api_client.dart`, `coherent_refresh_coordinator.dart`, `app_state.dart`의 취득/guard만 변경했다. 새 `authoritative_acquisition_test.dart`, test-only `support/bundle_fake_response.dart`, 기존 legacy/equivalence/pending/offline/submit test double을 수정했다. Architecture/API/Offline/project-state 설명과 이 구현 보고서만 문서에 반영했다. Backend/frontend/Android runtime 및 B-2 parser/OfflineStore/OfflineProjection/DB migration은 변경하지 않았다.

기존 state-machine double은 legacy model methods로 합성 서버 body를 만들어 strict parser를 통과한다. 내부 fake의 14 method invocation은 실제 application HTTP가 아니다. 별도 실제 transport 및 실제 backend trace로 1/2회를 검증했으므로 fake count를 성능 근거로 사용하지 않는다. 역사적 DAG/fence 테스트는 삭제하지 않고 명시적 legacy oracle 대상으로 유지했다.

## AC. 집중 자체 감사

숨은 legacy dependency/fallback, 두 응답 혼합, wrong owner/session/generation, ambiguous POST 확정, durable publication 앞 UI 성공, confirmed marker 손실, finalizing cleanup, invalid mode, parser bypass를 검토했다. 두 owner guard 반례를 test-first로 보강했으며 내부 검증에서 남은 in-scope Critical/High/Medium은 0이다. 이 자체 검토를 독립 승인으로 표현하지 않는다.

## AD–AE. 잔여 위험·T6.6 이관

큰 full-history payload, raw-money/형식/해시의 O(N) 다중 pass, client main-isolate stall 가능성, full Snapshot resend·hot/cold/delta/compression 설계, backend full-ledger scan·duplicate detailed-payment 및 auth-session SQLite lock 위험은 해결하지 않았다. 미래 registry drift도 이번 전환으로 해결되지 않는다. 실기기 gate는 post-T6.6이다.

운영 backend가 B-1 endpoint를 제공하는지는 확인하지 않았다. 향후 release에는 검증된 B-1 지원 backend가 선행되어야 한다. 구 서버 404에 legacy fallback을 만드는 것으로 호환성을 숨기지 않는다.

## AF–AH. Commit·production·최종 Git

검증이 끝난 이번 구현/테스트/문서만 조건부 커밋·push한다. 최종 commit과 HEAD/main/origin/main/실제 remote 일치 및 clean 상태는 최종 응답에 기록한다. Production DB/API/credential/artifact/service에 접근하거나 deploy/restart/restore하지 않았다. Debug artifact는 개발 build 디렉터리에만 있다. 다음 단계는 별도 B-3/B-4 통합 correctness·RTT·scaling·HOST 독립 감사다.

이번 임시 증거 디렉터리는 `/tmp/mn-b3-RJT6qM`이다. `acquisition-benchmark.json`에 각 요청 method/path/start/end/body bytes와 server elapsed, `equivalence-results.json`에 13개 state, `omission-results.json`에 재구성 개수가 있다. 이 디렉터리는 재부팅 시 소실될 수 있고 repository의 영속 회귀 테스트를 대신하지 않는다.
