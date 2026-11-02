# T6.9-PRE03 — 보존 자료에 의한 N=100k accepted baseline 복구 가능성 정적 조사

**판정은 PARTIAL, 선택지는 C다. 현재 확인한 보존 입력과 원 B03의 지원 절차로는 새 취득 없이 적법한 N=100k accepted baseline을 확보할 경로가 없다.** 실제 복구·DB 개방·취득은 수행하지 않았다. 저장소에 로컬 복구 기능이 없다는 뜻이나, 조사하지 않은 외부 백업까지 존재하지 않는다는 뜻은 아니다.

세 명제를 분리한다. **B02의 역사적 N100k 기능 완료는 확인했다. 현재 사용할 수 있는 원 B03 호환·완전·epoch-authorized baseline은 확보되지 않았다. 필수 계측 증거의 독립 수용은 계속 0/8이다.** 원 B03의 N100k instrumented Cold 비용은 입증되지 않았고, 실패한 옛 P03 시간을 복구 상태의 측정값으로 대체할 수 없다. 승인 개정은 새 instrumented full Cold 성공을 별도 MUST로 추가하지 않는다. 적법한 baseline이 있다면 정상 증거를 수용할 수 있다는 허용과, 실제 그 baseline을 복구할 수 있다는 사실은 별개다.

## 1. 범위와 보존 기준

이 새 세션은 PRE01 계획·PRE02 감사·이전 구현에 참여하지 않은 정적 조사다. 다른 agent에게 위임하지 않았다. 외부 개인 신원이나 UI reasoning 설정을 인증한 것은 아니다. 사용자가 허용한 새 보고서·무결성 목록만 작성했다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. staged 변경은 0개이며 전체 index는 2,693개 path/mode/blob/stage 항목이다. index 원문 SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, 항목 직렬화 SHA는 `8df943cd1934be9aaa6f1f5b9a0dcc1a796e255019c8936e52c50ab414d535b8`다. 기존 tracked·비무시 untracked 6,532개 파일, 791,886,800B의 SHA·크기·mode를 [시작 목록](benchmarks/t69-pre03/preservation-start.json)에 기록했다. 기존 dirty 구현과 역사 evidence를 모두 보존 대상으로 삼았다.

조사 범위는 관련 `docs/benchmarks/`, `work/t66f-b03-ic06/`, 관련 이름의 `/tmp` 디렉터리, 역사 inventory가 지정한 exact 경로, 외부 frozen source다. [탐색 목록](benchmarks/t69-pre03/discovery-file-list.json)에 DB·압축 DB·WAL/SHM 264개 경로가 있으며 탐색 오류는 0개다. 그 목록에서 N100k 원 사본은 발견되지 않았다. 별도로 대조한 역사 N100k SQLite 경로 6개도 모두 부재다. production·`work/dev-data`·의존성/build cache·무관 `/tmp`·미제공 외부 저장장치는 조사하지 않았다. 호스트 전체의 백업 부재를 주장하지 않는다.

SQLite 연결은 **0회**다. tar/gzip는 메모리에서만 해제해 원 bytes를 해시했고 DB 파일을 생성·복사·체크포인트·복구하지 않았다. 원 source archive도 실행 working tree로 추출하지 않았다. 실제 제품 import·API·npm/backend/Flutter 시험·Cold·장치 작업은 모두 0회다. 명시된 정적 무실행 범위가 AGENTS의 일반 build/backend 검증 규칙보다 우선한다. 기본 sandbox의 bwrap loopback 초기화 오류 뒤 승인 검토된 읽기·자기 산출물 쓰기 명령을 사용했으며 자동 승인 거부는 없었다.

## 2. 승인된 규범 근거

[승인 결정](benchmarks/t66f-b11-application/authorization-decision.json)의 원 제안 보고서 SHA `11fd8fc6d0f97dabe6570da9dce1f5190f6ca93287ca50a5e3b408fc3a871569`, 원 개정 기록 SHA `21babe57c9fb6ce617a7a81e48fb40c8e488b708f55158c2e720f5b208d409db`, 책임 보충안 SHA `08a19797823c5bffb8b2abd99be0397e9ba6663425d37514de1b9e55c4b42844`를 실제 파일과 대조했다. GOV01/GOV02/REF01을 반영한 승인 추가문 AM01–05도 현재 구속 문서에 정확히 한 번씩 존재한다. [정적 검증](benchmarks/t69-pre03/source-static-verification.json)에 개별 검사를 남겼다. 과거 초안의 개인 기명 요구를 다시 적용하거나 승인 시각을 발명하지 않았다.

| 근거 | 이 조사에서의 구속 효과 |
| --- | --- |
| [C §4–9](t66/c/t66c-delta-sync-protocol.md:53) | release engine·Versions, NS/principal, Target·sync_root의 서로 다른 identity와 exact 계약 |
| [C §5](t66/c/t66c-delta-sync-protocol.md:72) | 서버 cold startup 및 physical restore는 새 epoch·전체 bootstrap 필요; 실행 중 hot-swap·옛 epoch 재활성화 불가 |
| C §16-S | 역사 complete certificate는 객체의 영구 보관 root가 아님; digest만 남은 graph를 현재 재구성 가능한 authority로 광고 금지 |
| [C §18](t66/c/t66c-delta-sync-protocol.md:407), §23–27 | 완전 11 tables·F(raw) index·receipt/pins·recoverability·같은 연결 provenance와 E3 guard/동기 COMMIT/readback |
| [C §22–24](t66/c/t66c-delta-sync-protocol.md:461), §29 | Snapshot v7·OfflineBaseline v4·segmented-store/1 분리; legacy fingerprint와 sync_root 대체 금지 |
| [C §30–33](t66/c/t66c-delta-sync-protocol.md:595) | epoch 변경 시 new-NS complete full; exact repair·frozen 보존; 큰 restore/MW와 migration은 별도 계약 |
| [C §34-B11 및 §35-T69](t66/c/t66c-delta-sync-protocol.md:681) | 이관 8개는 원 B03의 독립 admission 뒤 정상 실제 ON 증거로 수용; baseline 부재 시 수집 차단; 개정은 실행 GO가 아님 |
| C §36 I25, §38.7–12; B §27/29 | 정상 full-N 금지·직접 계측 유지; whole-F·R1·기기·운영 gate 미면제 |
| [도메인 모델](domain-model.md), [신뢰 경계](architecture.md:14), [Offline 계약](offline-mode.md), [복원 운영 계약](runbook.md:968), [보안](security.md) | 서버 금융 authority·입력 전용 J·명시 복원·manifest/정책/임시 DB dry-run·mandatory pre_restore·rollback 보존 |

[승인 적용 보고서](t66f-b11-approved-amendment-application.md)와 [종결 재판정](t66f-b11-post-amendment-closure-readjudication.md)에 따라 Phase B 행정 종결은 **COMPLETE — EVIDENCE TRANSFERRED**, 정량 증거는 INCONCLUSIVE, formal T6.6F closure는 NOT AUTHORIZED다. 실행 책임은 T6.9 구현·측정 워크스트림, 독립 수용은 해당 구현·측정 비참여 별도 T6.9 감사 세션, 최종 승인은 프로젝트 소유자다. PRE03은 이 처분과 역할을 변경하지 않는다. PRE02 JSON 13개를 모두 읽고 hash 목록을 [입력 manifest](benchmarks/t69-pre03/input-manifest.json)에 연결했다.

## 3. 원 B03 source와 B02의 정확한 비교

| identity | 확인값 |
| --- | --- |
| 원 B03 base commit / tree | `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` / `af2aa70ce6a8cd27c18c134564e31702f0f54f8c` |
| 원 B03 payload SHA | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| 원 B03 engine SHA | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| 원 B03 archive SHA | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |
| frozen 위치 | `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/` |
| B02 독립 감사 실행 commit / tree | `1cabf319f0ac2c2069e804b47cb527b55e3374db` / `06b1526488020c54ebff63497e3c1ef407c4be9f` |
| B02 canonical payload SHA | 원 발급 기록 없음, **null**; commit/tree·원 inventory·실행 source SHA로 식별 |

원 B03은 manifest source 899개와 context·metadata를 포함한 archive 1,067개 member의 안전 경로·regular-file·중복 부재·SHA·길이·mode, baseline Git 항목 2,693개 및 SHA256SUMS를 대조했다. payload는 지정한 정렬 entries 직렬화로 재계산했다. archive metadata는 sidecar의 마지막 newline 한 개를 제외한 exact bytes와 일치한다. 최초 checker가 newline까지 같다고 가정한 두 실패는 [도구 교정 기록](benchmarks/t69-pre03/checker-correction.json)에 보존했고 정확한 규칙으로 교정했다. 역사 파일의 결함이나 수정으로 표현하지 않는다.

B02와 원 B03의 backend engine 입력 **98개가 동일**하다. 9,587B engine artifact의 SHA도 양쪽 모두 위 `7ad114…`다. 이는 금융 값 동등성 추론이 아니라 source bytes의 직접 대조다. backend/app·isolated_sync 및 mobile/lib 제품 경로 비교에서 158개 파일은 동일하고, 6개 모바일 경로가 다르다. 각 old/new 전체 SHA와 실제 변경은 [source 비교 JSON](benchmarks/t69-pre03/source-epoch-compatibility.json), [정적 diff](benchmarks/t69-pre03/b02-b03-product-comparison.diff)에 있다.

| 다른 경로 | 원 B03의 차이와 저장 계약 영향 |
| --- | --- |
| `app_state.dart` | 기존 recovery/E2/E3 경계를 LogicalCost stage로 관측; 원 guard·동기 COMMIT 함수는 유지 |
| `authoritative_bundle_validation.dart` | 실제 legacy SHA 입력 길이 관측 |
| `diagnostics/logical_cost.dart` | 새 opt-in 관측 library; persisted authority가 아님 |
| `offline/offline_store.dart` | 기존 lineage hash 입력 길이 관측; baseline 직렬화는 동일 |
| `segmented/c1.dart` | 기존 encode/decode/SHA sink의 호출·bytes·실패 관측; domain/NUL/C1 표현 유지 |
| `segmented/store.dart` | 선택적 diagnostic native DB factory 인자; 기존 schema/receipt 계약 동일 |

`protocol.dart`, object·graph·verification/incremental·publication/read/frozen·adapters/workspace, `offline_data.dart`는 B02와 동일하다. 따라서 **기존 complete store의 저장 형식·validator를 원 B03가 읽는 정적 호환성은 확인**했다. B02→B03 자체 때문에 schema·receipt migration이 필요하다는 근거는 없다. 전체 payload가 같거나 현재 실행 baseline이 적법하다는 결론은 아니다. dirty live tree의 B05/B08은 채택하지 않았다.

B02 기록의 CPython3.12.3/backend SQLite3.45.1/Flutter3.47.4/Dart3.13.3은 승인된 원 B03 지원 조합과 같다([원 환경](benchmarks/t66f-b02-independent/environment.json)). client SQLite3.53.4를 포함한 원 IR07/B04 runtime 계약은 그대로이며, PRE03에서 새 runtime·binary·monitoring admission을 실행하지 않았다.

## 4. N100k 후보 inventory와 현재 bytes

[필수 inventory JSON](benchmarks/t69-pre03/preserved-artifact-inventory.json)은 각 후보의 path/run/source·engine·fixture raw digests·N/H/D·객체 수·NS/epoch·accepted ID·sync_root·E3/E4·format·DB/WAL/SHM·checksum·지원 경로·누락·규범을 분리한다. **현재 복구 가능한 N100k SQLite 후보는 0개**다. 아래 bytes는 별도 표시가 없으면 역사 파일 크기이며 현재 복구 가능한 파일 크기가 아니다.

| 후보 | 역사 사실 | 현재 확인·처분 |
| --- | --- | --- |
| B02 독립 완료 | initial 400,532객체/400,528 edges/261,543,083 canonical B; ledger100,000+다른35행; E3/E4·delta·새 client process 복구 PASS | 621,580,288B client DB의 exact path 부재. 원 metadata/raw 로그만 보존. **현재 baseline 부적격** |
| B02 A02 구현 완료 | 같은 initial 객체·canonical 크기; E3/E4·delta/restart 완료; final accepted sequence4 | 619,786,240B client DB path 부재. raw 값 digest·NS는 독립 B02와 다름. 독립 결과와 한 사본으로 합치지 않음 |
| B02 초기 model | `/tmp/mn-b02/100000/objects.sqlite` 365,887,488B 및 `layout-model.sqlite` 608,186,368B | 두 path 부재. 원 model은 raw/layout 용량 조사이며 accepted generation 복구 증거가 아님 |
| A01 partial | 294,624/400,532객체; accepted null/sequence0 | 500,199,424B DB path 부재. partial은 accepted가 아님 |
| P03 partial | 397,146/400,532객체; 3,386 missing; accepted null/sequence0; generations/root pins0 | 612,196,352B 원 client DB path 부재. 역사 SHA만 남음. **E3/E4 미완료** |
| B04 v3 압축 backup | 1k/5k/10k/50k 각각 backend/client-on/client-off, 총12개 | 압축·비압축 SHA/길이를 원 manifest와 대조해 모두 일치. 지원 backup API의 자료이나 **N100k 아님** |
| P05 보존 backup | `run-final-format/artifacts/tls-normal/backend.sqlite3`, N1000·4,132 reachable objects | 8,818,688B, SHA `00dad57f6e2af2252c126b6406b6657d5451d3a73981be9004d0a98e21f87cc3` 일치. 원 P03/100k 사본 아님 |

완료 B02의 정확한 누락 path는 다음과 같다. 두 main과 각각의 `-wal`, `-shm`, `-journal`도 현재 존재하지 않는다. checksum을 계산할 파일이 없으므로 현재 DB SHA는 **null**이다. historical DB checksum이 발급되지 않은 B02에는 값을 만들지 않았다.

- `/tmp/mn-b02-independent-100000-z6ux9y53/client/segmented-store-v1/fcf589b306ce8435db4b20c50d43c9322323d0b52ccf1c802f5d315f2f49db5c.sqlite`
- `/tmp/mn-a02-corrected-100000-9k9mr_4l/client/segmented-store-v1/425e64502cbd03c9218835f518d140a5a96fe34304a9b06f81023315772f42ff.sqlite`

역사 [disk inventory](money-note-disk-cleanup-candidates.json)는 당시 위 경로를 PROTECTED로 기록했다. 그 당시 보존 처분과 지금의 path 부재는 다른 사실이다. 부재의 원인을 PRE03가 삭제나 특정 정리 작업으로 단정하지 않는다. P05의 재부팅 확인·P03 소실 기록도 해당 원 경로에 한정한다.

보존 B02 독립 N100k raw gzip 21개와 P03 actual-server raw gzip 5개, 총26개는 각 원 manifest의 압축 SHA·길이 계약에 맞는다. 비압축 SHA·길이도 새 inventory에 기록했다. B02 HTTP object 응답 로그는 chunk 개수·decoded 길이·수량 집계이며 `data_base64`/response body를 보존하지 않는다. 이 집계와 hash 목록을 원 canonical object bytes로 되돌릴 수 없다. 원 B03 archive는 source/context/metadata이며 금융 DB backup이 아니다.

## 5. Accepted generation과 epoch lineage

[원 B02 cold 독립 검증](benchmarks/t66f-b02-independent/evidence/100000/independent-cold.json.gz)은 accepted pointer·receipt·4개 root pin·reachable graph·11 tables 값 digest·FK를 대조한 당시의 완료 증거다. 현재 DB 검증을 실행한 결과가 아니다.

B02 독립 run의 server/dataset/epoch는 각각 `9068dc06-3609-495e-a883-595c684826b8`, `a265f35e-cad2-46d0-baf8-2272b23b6f94`, `f3b8b021-4799-46f6-b84d-d32886145622`다. principal은1, origin은 `https://127.0.0.1:42251`이다. 이 origin/NS/principal/Versions의 canonical checksum은 실제 DB filename stem `fcf589…`과 일치한다. 임의 새 TLS endpoint를 같은 namespace로 취급하지 않는다.

| 역사 단계 | accepted generation ID | sequence / revision |
| --- | --- | --- |
| cold 및 identical | `bacb167d-1927-4d1d-859d-c1cf0e27302e` | 1 / 100025 |
| one_row_delta | `2909e6c9-ee8e-47c1-92f8-f384890980da` | 2 / 100026 |
| multiple_localized | `825c4db2-6613-4e28-8cef-499270266a47` | 3 / 100028 |
| restart_delta | `fd41c2e8-266c-4fdd-8098-9019e8c599de` | 4 / 100029 |

initial sync_root는 `ba5cd469a0be95b686da44477192fd4f636dfe6f45c28d8cb57264985007e379`, 최종은 `a89584bb76abc3ae7fc2daa2c0eb793b8940b486eaf67beb08a4defb6c425f8f`다. 4단계 Target의 view hash를 정적으로 재계산해 일치했다. 최종 previous는 sequence3이다. `fresh-process.json.gz`의 accepted sequence3은 그 사이의 client reopen 검증이며 최종 sequence4와 모순이 아니다. **여기의 restart는 client/store reopen이다. 서버 restart 뒤 같은 epoch로 동작했다는 증거가 아니다.**

initial sorted reachable-hash-set SHA `9400cabdf082707b68b9f4247ba277ef6117ba9c64f75ec7813d40259bab3a89`, receipt의 object_set association `067e6b9cbc3a0cf2d1e536f60da2be7066fc55f4e7a85820e0838e8ffbf95170`, generation ID, sync_root, engine/payload SHA는 모두 다른 개념이다. 최종 store union400,630개와 한 Target의 reachable400,532개도 구별한다. 오래된 G1을 최종 accepted G4라고 바꾸지 않는다.

[원 P03 fixture](benchmarks/t66f-b03-ic01-p03/evidence/fixture.json)는 B02 G1과 11 tables raw value digest·type/크기/count가 같지만 새 NS의 sync_root는 `bb0463c6a959b0fb27d5cdfeb780624bd62ef9d0071dc5462020e06f2491aeeb`임을 기록한다. P03 epoch는 `848bc874-91c2-4c2c-8e3f-7f67af4294dd`다. **동일 raw 금융 내용조차 Target/epoch 동등성을 보장하지 않는 직접 반례**다. 구현 완료 A02의 raw digest도 독립 B02와 같지 않아 같은 N·engine·크기로 사본을 혼합할 수 없다.

## 6. 객체 완전성의 증명 한계

B02 당시 E3 receipt는 400,532 objects·400,528 edges·200,057 facts·100,035 changed rows를 기록한다. 독립 oracle는 11 tables의 전체 실제 값과 reachable digest를 대조했다. 따라서 **역사 graph 완전성은 source-qualified PASS**다. 현재 object bodies·edges·pins·current/previous manifests가 담긴 완전 SQLite bytes는 확인되지 않아 **현재 immutable object completeness는 NOT ESTABLISHED**다.

C §16-S는 historical certificate/digest의 보존과 실제 object retention을 명시적으로 분리한다. manifest의 선언 수, financial semantic digest, FK오류0이라는 역사 기록만으로 현재 모든 referenced bytes가 복구 가능하다고 결론 내리지 않는다. source/fixture 생성 코드와 seed도 원 UUID·epoch·control timestamp·mutation history·전체 object bytes의 backup이 아니다.

P03는 일부가 아니라 구체적으로3,386개가 부족했다. `failed-store-fresh-process.json`의 quick_check=ok와 FK오류0은 부분 store의 무결성이고 accepted 없음의 기록이다. missing bytes를 수동 입력하거나 accepted fields를 편집할 수 있다는 허가가 아니다. P04 clone도 그 미완료 상태의 파생 자료이며 원 P05 기록상 경로가 소실됐다. 현재 accepted baseline 후보로 승격하지 않는다.

## 7. 기존 구현이 지원하는 복구 경로

아래 line은 mutable live tree가 아니라 **확인한 원 archive의 `source/` member**다. 파일별 SHA와 실제 발췌는 [source 계약 근거](benchmarks/t69-pre03/source-contract-excerpts.json), 10가지 지원 여부는 [복구 경로 JSON](benchmarks/t69-pre03/supported-recovery-paths.json)에 있다.

| 기존 경로 | 지원 범위와 이번 입력에서의 한계 |
| --- | --- |
| `store_publication.dart:521–591`의 `recoverAcceptedGeneration` | 같은 CacheNamespace의 기존 완전 current/previous graph를 전수 검증한다. 객체를 새로 복원하거나 manifest만 import하는 함수가 아니다. N100k main bytes가 없어 호출 입력이 없다. |
| `store_publication.dart:157–280` | manifest/receipt checksum·Target·validator·pin·accepted checksum·previous base_sync_root를 대조한다. 과거 receipt는 새 ticket이 아니다. |
| `verification.dart:374–455` | 모든 object·11 tables·raw/hot 구조·독립 F(raw)와 canonical index root를 확인한다. 지원 full recovery O(N)이며 정상 I25 counter 밖의 별도 workload다. |
| `store_frozen.dart:97–123`, `workspace.dart:479–563` | installed/frozen·source binding의 data 복구다. UI 설치·J replay·pending retirement·Offline 권한을 복원하지 않는다. |
| `finalization.py:361–402` 및 C §5.4 | physical restore는 quiescent maintenance/cold bootstrap·새 UUIDv4 epoch를 요구한다. NS-bound trees/index·Target를 다시 만든다. 옛 epoch 보존은 지원 회복 절차가 아니다. |
| `adapters.dart:109–181` | complete read와 원 control metadata에서 정확한 v7를 materialize한다. v7→accepted graph import가 아니며 기본 budget은26,214,400B다. |
| 기존 backend `snapshot.restore_snapshot` | manifest/정책/관계·임시 DB dry-run·mandatory backup·원자 금융 raw 교체 계약이다. accepted/object-store/old auth metadata 복구와 다르다. N100k 완전 v7 입력도 없다. |
| `adapters.dart:21–24`, `isolated_sync/http.py:277–297` | `R1_RECOVERY_CONTRACT_REQUIRED`, capabilities404를 유지한다. §31 large recovery contract의 존재를 구현 완료·범용 import 허가로 해석할 수 없다. |
| 옛 `P03/fixture.py:restore` | 당시 실제 B02 G1 objects에서 합성 seed의 raw timestamps/값을 맞춘 preparation이다. 원 B02 DB를 필요로 했고 새 bootstrap은 P03의 다른 identity를 만들었다. 새로운 accepted 복구 절차로 전용할 수 없다. |
| C §15.3/§30 exact Ref repair | 유효한 fresh observation에서 missing bytes를 취득하는 지원 경로다. 과거 lease를 살리지 않으며 **새 취득0**이라는 이번 조건의 우회로가 아니다. |

`SegmentedClientStore.open`은 원 소스110–220행에서 directory 생성, writable `sqlite3.open`, PRAGMA 변경, BEGIN IMMEDIATE 및 opt-in schema 작업을 한다. `recoverAcceptedGeneration`도 `_pruneUnselected`를 통해 쓰기/정리할 수 있다. 함수 이름에 recovery가 있다는 이유로 PRE03의 읽기 전용 검증 도구로 사용하지 않았다. B02 independent oracle는 역사적으로 `mode=ro`였으나 그 문자열만으로 임의 WAL 상태에서 생성·복구 부작용이 없다는 보증을 만들지 않는다.

독립 후검증 방법 자체는 존재한다. 원 B02 `inspect_client.py`/`oracle.py`가 receipt/hash/root/전체 raw 값/FK를 대조했고 native verifier도 complete proof를 만든다. 그러나 현재 bytes 없이 이를 실행할 수 없다. 추후 검증에도 실제 파일 상태에 맞는 immutable 일관 사본 또는 엄격한 읽기 전용 안전성이 먼저 필요하다. 이번에 안전한 read-only DB 열기를 확보하지 못한 파일을 시험 삼아 열지는 않았다.

## 8. Snapshot v7·OfflineBaseline v4·source 호환성

B02와 원 B03는 `segmented-store/1`, `segmented-e1/1`, E3 receipt `/1`·root-association `/2`, opt-in SQLite schema 단계1–5, Snapshot7·recurring_ownership1·OfflineBaseline4를 같은 소스로 해석한다. **DB user_version, OfflineBaseline schema_version, Snapshot schema_version을 서로 바꾸지 않는다.** B02 persisted metadata를 원 B03로 해석할 때 새로운 migration이나 engine allowlist 수정이 필요하다는 근거는 찾지 못했다.

반면 보존된 `client-offline-mode-baseline.json.gz`는 v4 wrapper 안에 **Snapshot schema2, registration table만 든 소형 보호 sentinel**을 포함한다. 이 파일의 v4 라벨을 N100k 완전 Snapshot v7 backup으로 해석할 수 없다. 실제 accepted data는 별도 segmented SQLite에 있었다. [원 sentinel](benchmarks/t66f-b02-independent/evidence/100000/client-offline-mode-baseline.json.gz)의 checksum과 판별 필드를 inventory에 기록했다.

C §33의 migration은 ONLINE·J/pending 없음·완전 old B 검증·old pin·exact legacy parity·첫 observation base=null·complete new generation publication을 요구한다. old v4만으로 새 server epoch/R을 만들 수 없다. 현재 source에서 이 누락 입력을 해소하는 범용 v4/v7→새 NS accepted import API는 확인되지 않았다. legacy materialization과 handoff recovery를 그 API로 간주하지 않는다.

따라서 종합 **B02→B03 SOURCE COMPATIBILITY는 CONDITIONAL**이다. engine/표현/저장 형식의 정적 동일성은 VERIFIED지만, 실제 완전 bytes·origin·server epoch·independent full verification·same-connection provenance·원 B04 fixture/H/D/문자열·mutation 입력 admission은 미충족이다. source 재해석 없이 old NS를 새 NS로 쓰거나 receipt를 새 authority로 고치는 절차는 없다. 그런 importer·epoch 우회를 만들면 기존 지원 복구가 아니라 별도 변경·승인·재자격 대상이며 PRE03 권한 밖이다. B05/B08 도입은 해법으로 채택하지 않는다.

## 9. E3/E4와 측정 구간의 경계

원 B03 `store_publication.dart:367–468`은 prepared proof의 연결 identity·data_version·실제 durable accepted CAS를 검증하고,439–440행의 **최종 authority guard 바로 다음에 동기 COMMIT**한다. callback/await/hook을 그 사이에 넣지 않는다. commit 뒤 persisted pointer/Target readback을 검증한다. local full recovery 성공만으로 이 새 요청의 E3 publication/readback·E4 accepted read가 완료되지는 않는다.

B02의 source-qualified 기능 PASS는 당시 비계측 D→E/E3/E4 및 client reopen이다. 필수 B03 ON 직접 비용과 단계별 I25 귀속을 충족하지 않는다. B02의 기존 operation counter에 정상 full work0이 기록되어 있어도 그것을 최종 B03 ON E3별·부기별 직접 증거로 전용하지 않는다. IR07 correctness CLOSED도 이 미계측 규모의 자동 수용이 아니다.

적법한 complete baseline이 별도로 마련된다면 복구·restart·전체 검증 O(N)을 명시 admission 작업으로 분리하고, 같은 연결에서 그 뒤의 no-change/card/cash 정상 workload를 측정할 수 있다는 규범상 가능성은 있다. 복구 시간을 빼고 Cold라고 부르거나 옛 uninstrumented Cold 시간을 필수 instrumented 값으로 채울 수 없다. 현재는 그 baseline의 지원 확보 경로부터 없으므로 정상 수집을 시작할 수 없다.

## 10. 이관 8개 의무별 기준선 적격성

판정 대상은 **이번에 확인한 보존 후보를 원 B03의 현재 N100k baseline으로 재사용하는 것**이다. 아래 모두 NOT ELIGIBLE이며 evidence acceptance도0이다. 이는 recovery를 규범상 일괄 금지한다는 뜻이 아니다. 적법한 복구가 독립 admission된다면 정상 workload의 baseline 사용은 CONDITIONAL이며 그 조건은 [의무별 JSON](benchmarks/t69-pre03/obligation-eligibility-matrix.json)에 별도 기록했다.

| 의무 | 현재 기준선 판정 | 복구와 별도로 남는 필수 증거 |
| --- | --- | --- |
| T35-100K-NC | NOT ELIGIBLE | 원 B03 ON no-change 반복·ID/sequence 유지·실제 E3/E4와 rows/각 bytes/HTTP·RTT/memory·median/p95 |
| T35-100K-CARD | NOT ELIGIBLE | card D1 반복·실제 accepted 전진·같은 필수 비용/단계 |
| T35-100K-CASH | NOT ELIGIBLE | cash D1 반복·실제 accepted 전진·같은 필수 비용/단계 |
| T35-ROWS | NOT ELIGIBLE | 다섯 N×세 workload의 SQL·반환행·raw/index lookup·query plan 결측 완결; 반환행≠VM/pager 전체 방문 |
| T35-NET | NOT ELIGIBLE | 다섯 N×세 workload의 실제 entity/canonical/base64·JSON framing/headers/RTT·의존성/cache 및 matched full |
| T35-GZIP | NOT ELIGIBLE | 같은 source/state/Context의 full 입력·gzip6 버전/SHA/CPU·실제 network/parse/validation/write·두 문자열 family 비교 |
| I25-E3-100K | NOT ELIGIBLE | 세 정상 workload E3Verify/Prepare/Commit의 직접 rows/bytes·SQL/tree/index/pin/CAS/readback 및 full counters5종=0 |
| I25-BOOKKEEPING-100K | NOT ELIGIBLE | 정상 D/E lease/GC/refcount/root-pin/transfer의 직접 귀속·hidden full graph/history 부재·flat P 없음 |

ROWS/NET/GZIP의 유효한 하위 네 N 기존 증거를 철회하지 않았다. N100k 한 baseline 확보도 다섯 점·collector·matched full/다양성 결측의 자동 완결이 아니다. PRE02의 추가 collector 미자격·r/U/q 미정·자원 예산 미입증도 이번 정적 조사로 해소되지 않았다.

## 11. 역사적 결측과 실패의 구별

[P03 full-analysis](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json)의 직접 실패는 `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)`,2699.957907초, 실제900초 observation3개 소진이다. 완전 취득 전에 끝났으며 E3/E4는 미도달이다. 이를 외부 watchdog 실패나 금융 correctness 실패로 바꾸지 않는다. 계측 단독 원인이라고도 단정하지 않는다.

최종 원 IR07 payload의 N100k 정상 B03 ON/Cold·필수 E3/부기 귀속은 **미측정 또는 미수용**이다. 옛 P03 실패에 최종 payload SHA를 소급 부착하지 않는다. 현재 파일 부재는 지금 복구 입력의 결측이며, B02 역사 기능 PASS를 FAIL로 바꾸는 반증이 아니다. 반대로 B02 PASS나 P03의 약99% 진척을 현재 accepted baseline PASS로 승격하지 않는다. B01/B02/B03의 closed 감사를 새 material 반증 없이 재개하지 않았다.

## 12. 가능성 결론과 최소 후속 조치

**C — NO SUPPORTED RECOVERY PATH WITH IDENTIFIED PRESERVED INPUTS.** 필수 source·규범·역사 manifest는 확보했으므로 이 조사 범위에서는 단순 규범 불명확에 따른 D 판정이 아니다. 기존 local recovery에는 complete 입력이 필요하나 확인된 N100k main은 없고, P03은 원래 accepted가 없으며, physical/server restore는 새 epoch를 요구하고 현재 원 source에 그 전이를 새 취득 없이 accepted로 만드는 범용 import가 확인되지 않았다. source·호환성·권한을 가정해야만 성립하는 경로를 A나 B로 인증하지 않는다.

가장 먼저 부족한 것은 **실제 완전 N100k client graph/receipt와 authoritative backend provenance를 담은 일관 보존 bytes**다. 그 bytes가 나중에 발견되어도 §5의 새 epoch와 origin·현재 authority·same-connection admission을 다시 증명해야 한다. 전역 미접근 저장소에 사본이 없다고 단정하지 않으며, 새 자료 발견은 새 provenance 심사의 근거일 뿐 현재 GO가 아니다. 기존 source를 우회하는 수동 DB 조작·새 importer·old epoch 재사용을 제안하지 않는다.

새 취득이나 복원 rehearsal을 자동 권고·승인하지 않는다. 후속 실행에는 exact 입력·지원 경로·원 source/runtime·계측·자원·실패 보존의 별도 계획과 독립 admission 및 명시 GO가 필요하다. 이번 결과는 그 GO를 발급하지 않는다. §35/I25 요구를 소거하거나 cold NO-GO·formal F/R1/기기/배포 gate를 뒤집지 않는다.

**다음 작업은 PRE03-NEXT-01 하나다.** PRE03의 기준선 재사용 불가 근거를 반영하여 새 취득·복원 실행을 제외한 T6.9-E 실행준비 수정안을 별도 정적 문서로 작성한다.

## 13. 산출물·정적 검증·Git 보존

필수 산출물은 이 보고서와 다음 JSON5개다. source·archive·승인·epoch·lineage·raw checksum·호환성·복구 함수·의무 판정의 근거는 각각 연결되어 있다.

- [보존 아티팩트 inventory](benchmarks/t69-pre03/preserved-artifact-inventory.json)
- [source·epoch 호환성](benchmarks/t69-pre03/source-epoch-compatibility.json)
- [지원 복구 경로](benchmarks/t69-pre03/supported-recovery-paths.json)
- [8개 의무 기준선 적격성](benchmarks/t69-pre03/obligation-eligibility-matrix.json)
- [최종 복구 결정](benchmarks/t69-pre03/baseline-recovery-decision.json)

[정적 검사](benchmarks/t69-pre03/static-validation.json)는 JSON/참조·source/승인·원 manifest 해시·선택지/의무 일치·금지된 실행0·한국어/필수 footer를 점검한다. [종료 보존](benchmarks/t69-pre03/preservation-final.json)은 시작6,532개 파일과 Git index 원문·전체 항목·HEAD/branch, frozen5개 파일을 재대조한다. 기존 파일 내용·크기·mode와 index의 차이는0개이며 새 경로는 PRE03 보고서·전용 evidence뿐이다. ignored runtime·production 전수 무결성이나 파일 access-time 불변을 주장하지 않는다. 타임스탬프/소유자/권한 변경·DB 연결·WAL/SHM 쓰기 명령은 수행하지 않았다.

[산출물 manifest](benchmarks/t69-pre03/evidence-manifest.json)에 새 파일의 SHA·크기·mode를 기록했다. 제품·원 instrumentation·binding protocol·approved amendments·engine admission·B01–B11/PRE01/PRE02·역사 DB를 수정하지 않았다. reset/stash/clean/checkout/rebase/restage/commit/push·production 작업은0이다. 대형 임시 실험 산출물 정리는 NOT APPLICABLE, 삭제·회수0B이며 보존한 task 산출물만 남겼다.

## 14. 필수 최종 기록

```text
T6.9-PRE03 N=100K ACCEPTED-BASELINE RECOVERY FEASIBILITY:
PARTIAL

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

APPROVED B11 AMENDMENT:
VERIFIED

ORIGINAL B03 SOURCE:
VERIFIED

BASELINE ENGINE SHA:
7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c

B02 HISTORICAL N=100K FUNCTIONAL:
PASS — SOURCE-QUALIFIED

P03 HISTORICAL INSTRUMENTED N=100K:
INCOMPLETE — NO E3/E4

PRESERVED N=100K CANDIDATE ARTIFACTS:
완료 B02 2개 run의 manifest·raw 기록 보존, 역사 SQLite 경로 6개 부재, 현재 복구 가능한 N100k DB 0개

ACCEPTED GENERATION PROVENANCE:
PARTIAL

EPOCH AUTHORITY:
PARTIAL

IMMUTABLE OBJECT COMPLETENESS:
NOT ESTABLISHED

B02→B03 SOURCE COMPATIBILITY:
CONDITIONAL

SUPPORTED RECOVERY PATH:
NONE

ACTUAL RECOVERY EXECUTED:
NO

T35-100K-NC BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 보존 후보

T35-100K-CARD BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 보존 후보

T35-100K-CASH BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 보존 후보

T35-ROWS BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 N100k 후보; 하위 N 증거 보존

T35-NET BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 N100k 후보; 하위 N 증거 보존

T35-GZIP BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 N100k 후보; 하위 N 증거 보존

I25-E3-100K BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 보존 후보

I25-BOOKKEEPING-100K BASELINE ELIGIBILITY:
NOT ELIGIBLE — 현재 보존 후보

TRANSFERRED OBLIGATIONS ACCEPTED:
0 / 8

N=100K CURRENT EXECUTION FEASIBILITY:
NOT ESTABLISHED

NEW ACQUISITIONS:
0

SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

ENGINE ADMISSION MODIFIED:
NO

HISTORICAL DATABASES MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY PRE03:
NO

HISTORICAL EVIDENCE:
PRESERVED

T6.6F PHASE B ADMINISTRATIVE CLOSURE:
COMPLETE — EVIDENCE TRANSFERRED

FORMAL T6.6F CLOSURE:
NOT AUTHORIZED

REAL-DEVICE GATE:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

PRE03 REPORT:
docs/t69-pre03-100k-baseline-recovery-feasibility.md

PRE03 EVIDENCE:
docs/benchmarks/t69-pre03/

FINAL VERDICT:
C — NO SUPPORTED RECOVERY PATH WITH IDENTIFIED PRESERVED INPUTS

NEXT ACTION:
PRE03의 기준선 재사용 불가 근거를 반영하여 새 취득·복원 실행을 제외한 T6.9-E 실행준비 수정안을 별도 정적 문서로 작성한다.
```
