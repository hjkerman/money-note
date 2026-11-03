# P2-N01 수용과 P2-N02 Snapshot GET 재사용 조사

**N01 ACCEPTED / N02 DEFER — 독립 Snapshot GET 유지(C) 권고.** 2026-11-03, 실제 working source `phase2/mobile-network / 13ef6e97590d27f32939409a2cc23d0d967263e2`. 조사·문서만 수행했고 생산 코드·N01 benchmark evidence·운영은 변경/접근하지 않았다. N02 구현은 미승인이다. Phase2 종료나 배포 준비 판정이 아니다.

## 1. N01 최종 수용

owner가 최종 독립 감사 **PASS — N01-A01-R1 RESOLVED**에 따라 수용했다. N01-A01·R1 CLOSED, blocking findings 없음이며 추가 구현 감사 없이 수용한다.

| 단계 | commit·처분 |
| --- | --- |
| 최초 N01 | `a5adff9f3e7c04ba0c2ab348d6dc4fff054ad309` — PARTIAL |
| 첫 감사 | REWORK — N01-A01 MAJOR |
| 첫 correction | `2d3351847b569efadbb330543b7dd92b418444bd` — 당시 COMPLETE·감사 대기 |
| targeted 재감사 | REWORK — CORRECTION INCOMPLETE, N01-A01-R1 |
| 최종 correction | `13ef6e97590d27f32939409a2cc23d0d967263e2` — 최종 독립 PASS, owner ACCEPTED |

[공유 이력 §9~12](phase2-mobile-network-optimization-candidates.md)와 [구현 raw](../benchmarks/p2-n01-implementation-evidence.json.gz)의 실패·수정·시험은 보존한다. gzip6 원문 SHA 호환, 두 독립 decoder 검사와 main-isolate/버퍼·지원 feature 한계는 기존 host 근거 그대로다. 운영 Snapshot 미압축은 owner 관찰이고 구 운영 revision의 Bundle 부재도 이미 기록했다. **Production deployment NOT AUTHORIZED / NOT PERFORMED, main merge 없음.** 수용은 실제 운영에 gzip이 배포됐다는 뜻이 아니다.

## 2. 실제 request-flow 지도

B = `/api/authoritative-state`, S = `/api/admin/snapshot`. 아래 수치는 성공한 해당 분기의 source-supported 행동당 호출 수다. 새로운 host interaction trace나 운영 빈도를 측정한 값은 아니다. B는 raw transport→strict admission→auth/lineage/request guard→JSON OfflineStore atomic baseline→pending retirement→UI 설치를 포함한다.

| 행동·소스 | 순서·동시성 | B / S | fresh admitted B·독립 backup 의미 |
| --- | --- | --- | --- |
| 로그인 `AppState.login` | health→login POST→await refresh→await saveLaunchSnapshot→알림 target | 1 / 1 | B durable 게시 후 S, 순차. 로그인 직후 별도 현재 서버 export |
| 온라인 cold bootstrap `bootstrap` | local workspace 복원 시도, 온라인 진행 시 health→me→B→S→target | 1 / 1 | 동일. `restorePersistedOfflineWorkspace`가 true면 온라인 취득 전 반환하므로 0/0 |
| 정상 온라인 resume `resumeFromBackground` | foreground single-flight→await refresh→S | 1 / 1 | 새 B 다음 별도 S. foreground guard는 외부 서버 write를 막지 않음 |
| resume 중 연결 복구 | health/retry·필요 me→B, 성공/로그인 상태면 바깥 resume가 S | 분기별 B, 최대1 S | 복구 자체와 resume를 구분. 종료 조건 불충족/예외면 S 없음 |
| 탭·pull·일반 area/manual refresh | 공통 B만 | 1 / 0 | S가 없으므로 제거할 GET 없음 |
| 정상 금융 mutation·수정·삭제 | pending→POST/PATCH/DELETE ack→호출자의 B→durable 게시·pending 정리 | 1 / 0 | 필수 post-mutation B는 유지. 매 mutation에 S를 붙이지 않음 |
| 자동 backup `saveLaunchSnapshot` | entry에서 ONLINE 검사→await downloadSnapshot→repository.save | 0 / 1 | 함수 자체는 B를 요구하지 않고 S에서 독립 export. 실패는 catch하여 실행을 막지 않음 |
| 모바일 현재 Snapshot 공유 `shareCurrentSnapshot` | local list, 있으면 최신 local 파일 공유 | 0 / 0 | 항상 새 export가 아님. 빈 목록일 때만 saveLaunchSnapshot으로 S1; 직전 fresh B 보장 없음 |
| 특정 local 공유·백업 화면 | safeFile/list/readText 기반 | 0 / 0 | 파일별 공유/삭제/복원 선택은 기존 복구점 사용. backup 화면 자체는 S를 호출하지 않음 |
| local Snapshot restore | local 파일·password→restore POST→B | 1 / 0 | 서버 pre_restore/검증/rollback 계약 별개. N02 대상 아님 |
| OFFLINE resume/pull | health 중심 복구 확인, baseline B+J 고정 | 0 / 0 | S/B 재취득·local 예상값으로 backup 생성 금지 |
| Server/Mobile Wins 조정 | 별도 server-recovery POST·local recovery artifact 검증→사용자 선택→finalization B | 별도 B / 0 S | server recovery export는 독립 transaction의 복구 artifact. 자동 S와 병합 불가 |
| auth/session/generation 전이 | login은 위 흐름, logout은 auth generation 증가·state 정리 | 전이별 | 이전 B의 보유만으로 새 auth의 backup을 승인할 수 없음 |
| standalone connectivity retry | 현재 auth/lineage 확인, 0/350/850ms recovery attempts, health→필요 me→B | attempt별 / 0 | 자체 S retry loop는 없음. API GET 실패 시 legacy/지난 B를 backup 성공으로 바꾸지 않음 |

핵심 근거: [bootstrap/login](../../mobile/lib/src/app_state.dart:237), [refresh publication/resume](../../mobile/lib/src/app_state.dart:953), [자동·수동 공유·restore](../../mobile/lib/src/app_state.dart:2466), [recovery](../../mobile/lib/src/app_state.dart:1184), [finalization](../../mobile/lib/src/app_state.dart:1740). 사용자 수동 웹 export도 S지만 Web 최적화는 범위 밖이며 유지한다.

## 3. B Snapshot과 S의 관계

- [공유 export](../../backend/app/services/snapshot.py:116)는 전체 장부 테이블·비민감 설정·라벨·정책·지원 schema·manifest·snapshot_id를 만든다. S는 `export_snapshot()`의 새 DEFERRED read transaction, B는 같은 exporter를 자기 read transaction에 넣어 `require_current_columns=True`와 full Snapshot/금융 metadata 검사를 추가한다. B는 typed projections와 Snapshot의 coherent view·terminal revision/auth guard까지 갖는다. S만의 금융 테이블이나 추가 비밀번호/별도 admin role은 없다. 둘 다 기존 로그인 필요, routine session last_seen 갱신·로그 등의 통상 처리는 가능하다. GET S는 restore나 서버 backup artifact 생성을 호출하지 않는다.
- B의 `snapshot`은 축약 요약이 아닌 완전한 Snapshot dictionary다. 모바일 [admission](../../mobile/lib/src/authoritative_bundle.dart:89)은 그것을 envelope.snapshot으로 전달하고 [AppState](../../mobile/lib/src/app_state.dart:1009)가 durable baseline의 authoritativeSnapshot에 저장한다. 전체 map을 변경 없이 JSON/UTF8 직렬화하면 기존 backup 형식으로 저장할 수 있으며 금융 테이블 재구축이나 manifest 재생성은 불필요하다. SDK별 직렬화 bytes가 동일하다는 보장은 별도이고, map→JSON의 lossless 정수/문자열·구조·서버 hash 호환 검증은 향후 필요하다. B 응답 raw JSON 전체를 S 파일로 저장할 수는 없다.
- `state_revision`, principal, evaluation_date는 B의 authority/주변 metadata다. S 내부에 이를 새로 주입하면 원 Snapshot format/hash를 바꾸므로 금지다. client generation은 wire Snapshot 필드가 아니라 게시 권한이다.
- exported_at은 exporter 호출 시 초 단위 UTC이고 manifest.content_sha256·snapshot_id에 영향을 준다. `snapshot_state_fingerprint`는 exported_at을 제외한다. 그러므로 같은 financial fingerprint/revision만으로 동일한 export 시점이나 동일 bytes를 증명할 수 없다.
- S의 Content-Disposition filename은 export 시간 기반이지만 모바일 repository는 이를 무시하고 **저장 시각+random suffix**로 이름을 붙인다. UI는 파일 mtime인 updatedAt으로 날짜·복원 확인 문구를 표시하며, newest30도 그 시각으로 선정한다. 저장 시각 T3에 오래된 T1 snapshot을 새 파일로 넣으면 목록의 최신 표시와 실제 exported_at이 더 벌어질 수 있다.

기존 [discovery evidence](../benchmarks/phase2-mobile-network-evidence.json.gz)의 SHA-256 `c31ee681b598380c06a6ecb108fffe1cfa4e0220216e15e9ca3f8538ad197b52`를 읽기 전용으로 재검산했다. 새로운 API/DB benchmark는 실행하지 않았다.

| 합성 N | frozen-clock B.snapshot == S | Python compact 재직렬화 == S bytes | clock만 변경 | mutation 후 |
| --- | --- | --- | --- | --- |
| 376 | true | true | data/fingerprint 같음, manifest 다름 | ledger376→377, Snapshot 다름 |
| 1k | true | true | 동일 | ledger1000→1001, Snapshot 다름 |
| 10k | true | true | 동일 | ledger10000→10001, Snapshot 다름 |

각 fixture의 records `bundle`, `snapshot`, `bundle-later-clock`, `bundle-mutated`와 SHA-keyed `response_body_blobs`의 기존 raw를 JSON 비교했다. 이는 보존된 합성 관찰이며 현재 운영 빈도나 실제 T1→T3 latency가 아니다. frozen 일치가 일반 recovery 동등성의 증거는 아니다.

## 4. 복구 시점과 reachable race

현재 순서는 **T1 B의 read view/응답·admission → durable baseline 게시 → notification 설정 등 await → T3 S의 별도 read view**다. 그 사이 T2에 다른 웹/모바일 client의 정상 mutation이 commit할 수 있다. 같은 앱의 다른 async 진입도 코드상 모든 구간에 공통 server write barrier를 갖지 않지만, 특정 UI 경합의 실제 빈도는 측정하지 않았다. 외부 client의 T2만으로도 반례는 성립한다. B terminal guard는 B 반환 전까지만 보장하며 미래 T3까지 서버 상태를 동결하지 않는다.

S는 **S read transaction 시점**의 recovery point이지 download 완료 시점 전체의 최신성을 보장하는 것이 아니다. 그래도 T1보다 뒤의 독립 read point이며 T2 변경을 포함할 수 있다. 이를 B 재사용으로 대체하면 T3 backup에서 T1 backup으로 바뀔 수 있다. byte 중복과 recovery 의미 중복은 다르다. 같은 초·같은 state라 실제로 같은 파일이 될 수 있으나, client가 S를 생략하기 전에 그 사실을 일반적으로 증명하는 현 계약은 없다.

[domain-model](../domain-model.md:792)과 [runbook](../runbook.md:1105)은 실행/복귀 때 서버 전체 Snapshot을 새 파일로 누적하고30개를 보관하도록 한다. 엄밀한 T3 SLA를 따로 정의한 것은 아니지만 **기존 별도 export가 더 뒤의 state를 포함할 수 있다는 observable 동작**은 보존해야 한다. 시간 기준을 바꾸는 것은 문구 정리 수준의 무의미한 변경이 아니다.

## 5. Offline·pending·auth·복구 보존 조건

- JSON OfflineStore baseline은 이미 admitted B를 저장하지만, 자동 local Snapshot archive와 같은 역할은 아니다. B+input journal J가 reconciliation lineage를 보존하고 local backup30개는 사용자 선택 restore를 돕는다. server pending과 Offline J를 B나 S에 임의 합쳐서는 안 된다. **현재 S도 미확정 local/pending 변경을 포함하지 않는다.** N02가 그 문제를 해결하거나 journal을 버리는 근거가 될 수 없다.
- 로그인·lineage/request generation 변경·logout·OFFLINE/finalizing·pending·실패 acquisition 이후에 예전 B를 재사용하면 stale/wrong-context backup이 될 수 있다. 현재 guarded B publication 권한을 archive용 캐시 유효성으로 자동 연장해서는 안 된다. `saveLaunchSnapshot` 자체는 ONLINE entry check와 독립 authenticated GET을 갖고 B ticket을 전달받지 않는다. 이 사실만으로 새 치명적 결함을 선언하지 않으며, 재사용 시 필요한 guard 범위를 식별한 것이다.
- repository의 임시 write/readback·rename·fresh list·retention과 서버 restore의 full manifest/compatibility/pre_restore/rollback은 유지해야 한다. 로컬 repository는 envelope/저장 bytes 검사이며 서버 금융 검증 엔진이 아니다. 재사용은 서버 recovery artifact나 mandatory pre_restore를 대체할 수 없다.
- 기존 auto S가 실패하면 조용히 백업 없이 계속한다. 오래된 B를 그 실패의 성공 fallback으로 저장하면 실패 의미·현재 백업 시점·세션 재검사를 바꾸므로 허용하지 않는다. 동일 B를 반복 새 파일로 저장하면 유용한 이전 시점30개를 밀어낼 수 있어 event별 이름·retention도 검증해야 한다.

## 6. N01 적용 후 추가 절감량

N01은 **수용된 개발 기준선**이며 아직 운영에 배포하지 않았다. 아래는 그 gzip-enabled baseline에서, 재사용 조건이 승인/충족될 경우의 **S entity bytes만**이다. HTTP header·TLS·실사용 일/월 빈도·운영 latency는 계산하지 않는다.

| N | gzip S entity B / 제거 가능 event당 | 제거 GET | identity 수치는 추가 이득 아님 |
| --- | --- | --- | --- |
| 376 | 7,369 | 1 | 218,421B |
| 1k | 13,859 | 1 | 565,368B |
| 10k | **104,537 (약102.1KiB)** | 1 | 5,596,362B |

온라인 login/startup은 전체4요청→3, 정상 resume는 B+S2→B1이 잠재 상한이다. 현재 contract-preserving 제거가 증명된 event는 없어 **확정 절감0**이다. 탭·mutation·OFFLINE·일반 retry·조정에는 기존 S가 없고 수동 빈-list 공유에는 직전 B 보장이 없어 제거0이다. UI share가 이미 local 파일을 쓰면 역시0이다.

local backup 파일 수와 disk readback·prune 비용은 그대로이며 embedded map의 JSON 문자열+UTF8 bytes(10k 약5.60MB)를 생성하는 일시 메모리/CPU가 생긴다. 네트워크 압축 bytes와 JSON 메모리 크기를 혼동하지 않는다. 추가 B cache 없이 현재 operation의 Snapshot을 전달해야 하며, full data clone이나 disk baseline 재파싱이 필요하면 이득을 다시 평가해야 한다.

## 7. 대안과 판정

| 대안 | 기존 계약 보존 여부 | 처분 |
| --- | --- | --- |
| A 무조건 automatic B 재사용 | T2와 auth/실패 전이에서 T3를 T1으로 대체. 같은 데이터/같은초라는 가정 필요 | **권고하지 않음** |
| B freshness/revision fencing | 현재 B의 동일 owner/auth/lineage·성공 durable publication·pending 정리·immutable full Snapshot·명시 backup event를 확인해야 함. local fence만으로 외부 T2는 배제할 수 없음 | 현재 실행 가능한 contract-preserving 후보로 추천하지 않음 |
| C 독립 S 유지 | 기존 read point·실패·공유 fallback·retention 의미 유지, 후속 강한 guard 재설계 불필요 | **현재 권고** |

B를 다시 검토하려면 owner가 자동 backup을 **“그 event에서 방금 admitted/published된 T1 state의 복사”**로 정의해도 되는지 먼저 결정해야 한다. 외부 변경을 포함하는 후속 S의 의미를 유지하려면 실제 서버 freshness barrier가 필요하며 local revision equality나 TTL만으로는 부족하다. 그런 새 서버 계약·N03식 validation 설계는 이번 범위가 아니다.

owner가 T1 의미를 명시적으로 승인할 경우에만, 보호 `AppState`의 bootstrap/login/resume와 per-operation publication 결과 전달을 한정 구현 후보로 재정의할 수 있다. 기존 `refresh()`는 void이므로 `_offlineBaseline`을 임의 cross-generation cache처럼 읽는 방식은 피해야 한다. whole Snapshot lossless 직렬화와 pending/auth/mode guard, 실패 시 독립 S 유지 조건, 기존 저장·서버복원 호환 회귀가 필요하다. OfflineStore·repository·schema를 바꾸는 승인은 포함되지 않으며 수동 download/empty-share·recovery artifact는 독립 유지한다. **현재는 구현 scope 제안만이며 코드 수정 승인이나 구현 추천이 아니다.**

**N02 VERDICT: DEFER.** gzip 후 event당 약7~105KB의 가능 이득보다, 현재 backup 시점 변경과 보호 상태 전이의 위험/승인 비용을 우선한다. **C 유지**가 구체적 권고다. owner가 T1 backup 의미를 원하지 않으면 추가 설계/측정 없이 이 처분을 유지한다. 새로운 owner 결정은 현재 보류에 필요 없고, 미래 B 재개에만 필요하다.

## 8. 한계와 다음 행동

source/callsite와 보존된3개 합성 response 비교로 판단했다. 새로운 runtime 사용자 시나리오·race 빈도·현재 운영 traffic·실기기 성능·Dart 재직렬화 복원 roundtrip은 측정하지 않았다. 이 한계를 채우려고 새 감사/benchmark 캠페인을 시작하지 않는다. N01 코드·raw 근거는 불변이며 다음 단계/후보 구현도 하지 않는다.

**다음 행동 하나:** owner가 N02 DEFER·독립 S 유지(C) 처분을 검토해 확정한다. Phase2 전체 종료는 별도 판단이다.

문서 검증: 기존 합성 raw의 frozen/clock-only/post-mutation 비교3규모·상대 링크13개를 확인했다. 허용된 기존 문서3개 외 기존7,954개 파일 SHA와 staged index를 보존했다. 새 production/test/build 코드는 없고 새로운 runtime 성능/회귀 시험을 수행했다고 주장하지 않는다. 유일한 작업용 manifest는 검증 후 정리했다.
