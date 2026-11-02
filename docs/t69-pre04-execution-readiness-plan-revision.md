# T6.9-PRE04 — N=100k 기준선 복구 거부 후 실행준비 계획 정적 수정

**최종 판정: PARTIAL — ESSENTIAL NORMATIVE OR RESOURCE DECISIONS UNRESOLVED.** PRE02의 독립 결론과 PRE03의 복구 경로 거부를 반영했다. 수정 문서는 독립 검토에 제출할 수 있으나 실행 가능한 최종 계획은 아니다. 필수 직접 관측의 원 source 무변경 가능성·독립 자격, 새 기준선 취득의 현 observation 규칙 내 완료 가능성과 자원 예산, 반복·비교 표본 설계가 미해결이다. **실행과 N=100k 취득은 허가되지 않았다.**

**NO IDENTIFIED RECOVERABLE, ELIGIBLE N=100K ACCEPTED BASELINE EXISTS IN THE CURRENTLY PRESERVED INPUTS.** 현재 확인한 보존 입력에는 복구 가능하고 적격인 N=100k accepted baseline이 없다. 향후 같은 원 B03의 정상 증거를 수집하려면 현재 입력 기준으로 **새 취득을 통한 기준선 확립이 선행되어야 한다.** 이는 취득의 실행 승인·완료 가능성·계측 성공을 뜻하지 않는다. 새 기준선 하나를 마련해도 이관 8개 의무의 수용은 자동으로 늘지 않는다.

## 1. 재구성 범위와 현재 승인 상태

이 문서는 이전 대화나 세션 메모리 없이 저장된 PRE01 계획, 독립 PRE02 감사, PRE03 복구 조사와 B01–B11 원자료·승인 규범에서 재구성한 수정안이다. PRE01은 초안이며 PRE02/PRE03은 독립 판단이다. 어느 것도 측정 실행 허가가 아니다. PRE04는 계획 작성 역할이며 독립 관측기 감사나 실행 수용 역할을 수행하지 않았다. 외부 개인 신원이나 UI reasoning 설정을 인증하지 않는다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, 브랜치는 `main`으로 예상값과 같다. staged 변경은 0개이고 인덱스에는 기존 2,693개 path/mode/blob/stage 항목이 있다. 인덱스 원문 SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`로 PRE02/PRE03의 보존값과 같다. 기존 수정·미추적 파일을 포함한 6,553개 파일을 [시작 보존 기록](benchmarks/t69-pre04/initial-preservation.json)에 연결했다. dirty tree를 측정 source로 채택하지 않는다.

[B11 적용 보고서](t66f-b11-approved-amendment-application.md), [승인 결정](benchmarks/t66f-b11-application/authorization-decision.json), [책임 보충안](benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json), [적용 기록](benchmarks/t66f-b11-application/application-record.json), [종결 재판정](t66f-b11-post-amendment-closure-readjudication.md)을 대조했다. 승인된 Option 3와 GOV01/GOV02/REF01 보충안의 SHA 및 AM01–05 exact 추가문을 확인했다. 원 제안의 DRAFT 표시는 후속 승인을 무효화하지 않으며 개인 기명 책임이나 승인 시각을 새로 만들지 않았다.

| 구분 | 승인된 현재 상태 |
| --- | --- |
| B11 개정 | `T66F-B11-TRANSFER-01`, Option 3와 책임 보충안 VERIFIED |
| Phase B 행정 종결 | COMPLETE — EVIDENCE TRANSFERRED |
| 정량 증거 / 다섯 점 grid | INCONCLUSIVE / PARTIAL |
| 이관 8개 의무 | 필수 증거 유지, 독립 수용 **0/8** |
| formal T6.6F closure / 최종 T6.9 acceptance | NOT AUTHORIZED / BLOCKED |
| 실행 책임 / 독립 수용 / 최종 승인 | T6.9 구현·측정 워크스트림 / 해당 구현·측정 비참여 별도 T6.9 감사 세션 / 프로젝트 소유자 |
| 기한 | formal F exit 재심사와 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전 |
| R1 사용자 활성화 / 실기기 / production | CLOSED / DEFERRED / NOT AUTHORIZED |

구속 원본은 [C 프로토콜](t66/c/t66c-delta-sync-protocol.md)의 §5, §16/16-S, §18, §23–25, §34-B11, §35/35-T69, §36 I25, §38.7–12와 [B 설계](t66/b/t66b-hot-cold-design.md) §27/29다. 현재 C SHA는 `5d3f03a0e61c6d504cf8efd5de0c8ee446b9c0a0b4a45a367f6d366a4fbf94c9`, B SHA는 `e2d820ba71018414934ad4a9b3667961c209f93fe0b5b5dd2d0a3233ea76b279`다. 승인 전 역사 판단을 소급 PASS로 바꾸지 않는다. 실패·수행 불능은 근거와 함께 소유자에게 보고해야 하며 자동 연장·waiver는 없다. 승인 철회나 조건 위반의 원 gate 복원 규칙을 유지한다.

별도 승인 상세 T6.9 명세는 검토한 저장소 문서·참조에서 확인되지 않았다. 현재 이관 인수 계약은 C §35-T69다. B §27/29의 confirmed-heavy·한 달 hot 대량·initial/full/restore/crash 및 비이관 whole-F 의무는 계속 별개다. T6.9-E의 제한된 수집 진입을 전체 F PASS, T6.7/8 구현·cleanup, legacy 경로 제거, R1 활성화나 배포 승인으로 사용할 수 없다.

## 2. PRE03 거부를 고정 전제로 반영

PRE03의 정확한 결론은 **C — NO SUPPORTED RECOVERY PATH WITH IDENTIFIED PRESERVED INPUTS**다. [원 결정](benchmarks/t69-pre03/baseline-recovery-decision.json)과 [보존 입력 inventory](benchmarks/t69-pre03/preserved-artifact-inventory.json)를 [PRE04 영향 기록](benchmarks/t69-pre04/baseline-unavailability-impact.json)에 연결했다.

| 사실 | 현재 해석 |
| --- | --- |
| B02 N100k 기능 완료 | PASS — SOURCE-QUALIFIED. 독립 완료와 A02 구현 완료의 두 run manifest·raw가 남음 |
| 역사 N100k SQLite 경로 | 참조된 6개 main과 관련 WAL/SHM/journal 부재를 exact 경로로 재확인 |
| 현재 복구 가능한 적격 N100k accepted baseline | **0개** |
| accepted-generation provenance / epoch authority | PARTIAL / PARTIAL |
| 현재 immutable-object graph completeness | NOT ESTABLISHED |
| B02→B03 호환성 | CONDITIONAL. engine·저장 형식의 정적 호환과 현재 complete bytes·authority 적격성은 별개 |
| P03 | 미완료, accepted 없음, E3/E4 없음 |

다음 가정은 수정 계획에서 금지한다.

- 과거 B02 성공이면 현재 DB도 남아 있다는 가정.
- B02 manifest만으로 완전 accepted generation을 확보했다는 가정.
- P03의 partial object 상태를 accepted baseline으로 쓰는 가정.
- timing·객체 수·hash 목록에서 소실 SQLite bytes를 재구성할 수 있다는 가정.
- 보존된 epoch 문자열만으로 현재 복원 authority가 성립한다는 가정.
- canonical 금융 값이 같으면 exact persisted-state·Target·namespace도 호환된다는 가정.
- 복구 뒤 정상 incremental 실행을 measured full cold로 세는 가정.

B02 독립 G1과 P03 fixture의 11-table raw 값이 같아도 epoch와 sync_root가 달랐다는 PRE03 반례를 보존한다. B02의 두 run도 같은 N이라는 이유로 NS·raw digest·mutation history를 혼합하지 않는다. OfflineBaseline v4 보호 sentinel은 완전 N100k Snapshot v7 backup이 아니다. local recovery는 기존 complete graph의 검증 경로이지 manifest-only import가 아니다. C §16-S의 역사 certificate 보존은 실제 객체 보존과 다르다.

새 artifact가 나중에 발견되면 exact bytes·origin·source/runtime·완전 graph/receipt·epoch authority·같은 연결 provenance에 대해 **새 provenance·eligibility 심사**를 받아야 한다. 이 문서의 판정을 조용히 바꾸지 않는다. 조사하지 않은 외부 저장소까지 사본이 없다는 주장은 하지 않는다. 수동 accepted 필드 편집, old epoch 재활성화, startup 우회, 새 importer 또는 안전하지 않은 복원 절차를 제안하지 않는다.

## 3. source와 full 비교군의 정당성

| identity | 확인값 |
| --- | --- |
| 원 B03 base commit / tree | `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` / `af2aa70ce6a8cd27c18c134564e31702f0f54f8c` |
| payload SHA-256 | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| engine SHA-256 | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| archive SHA-256 | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |
| frozen 위치 | `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/` |
| 지원 runtime | CPython 3.12.3 / backend SQLite 3.45.1 / Flutter 3.47.4 / Dart 3.13.3 / client SQLite 3.53.4, IR07의 안정된 monitoring |

archive를 추출·실행하지 않고 source 899개, context 166개, metadata를 포함한 1,067개 member의 안전 경로·중복 부재·SHA·길이·mode를 확인했다. 정렬 entries의 명시 직렬화로 payload를 재계산하고, archive 안 `observation.py:76–86`의 실제 입력 규칙에 따라 98개 SHA map을 정적으로 구성해 9,587B engine artifact의 hash를 확인했다. 기준 Git inventory 2,693개도 일치한다. [source·승인 검증](benchmarks/t69-pre04/source-and-approval-validation.json)은 이러한 정적 검사이며 새 runtime admission은 아니다.

PRE02의 원 source 정당성 PASS는 유지한다. **C §35-T69가 원 B03를 직접 지정하므로 역사 reference source를 다시 선택할 규범 결정은 필요 없다.** §35 full 비교군에 별도 최적화 engine을 요구하는 문구도 없다. 비교군은 같은 frozen B03 backend authoritative presenter/serializer, 같은 DB read-view/state·Context·fixture를 사용해야 한다. identity/gzip6 전송과 원 full parser/validator·별도 폐기용 durable write를 재는 test-only facade는 별도 측정 harness로 식별·독립 자격을 받아야 한다. facade가 제품 gzip 구현이라고 주장하지 않는다. 현재 그 구현·자격과 실제 비교 입력은 없다.

payload, engine, archive, runtime/binary, harness SHA, DB generation은 서로 다른 identity다. 향후 loaded Python/Flutter/Dart·native SQLite/driver bytes와 monitoring 설정, command/cwd를 exact source에 연결해야 한다. B04가 보존한 client SQLite library SHA `0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace`도 실제 로드 bytes와 대조해야 한다. 버전 문자열이나 engine allowlist 통과만으로 실행 source·baseline을 admission할 수 없다.

제품·계측·SQL wrapper/trigger·monitoring ownership·stage 또는 runtime/driver가 달라지면 새 측정은 달라진 구성의 주장이다. 원 IR07 인증과 과거 성능을 자동 이전할 수 없다. 외부 harness만 새로 추가해도 그 harness의 자격과 교란 범위는 별도다. 과거 raw의 역사적 유효성은 보존하되 새 구성의 증거로 확대하지 않는다. B05/B08은 **EXPERIMENTAL — NOT ADOPTED**이며 도입·engine admission 변경을 하지 않는다.

향후 최종 T6.9에 다른 source를 채택하면 C §35-T69에 따라 별도 채택 승인·exact release/admission·변경 영향 계측 oracle/정확성/구조/provenance/authority fence/durability/legacy 복구 재자격과 **그 source 전체 다섯 점**이 필요하다. validator/schema 변경의 호환 proof가 없으면 §23 full revalidation 대상이다. 그 결과로 원 B03의 8개 결측을 없앨 수 없다. material 반증 없는 B01–B03 전체 closed 감사 재실행을 추가 의무로 만들지 않는다.

[source 결정 기록](benchmarks/t69-pre04/source-and-comparator-decisions.json)에 다음 결정 질문을 남긴다. 현재 필수 비교군의 source identity 자체는 규범으로 해소되어 있어 별도 identity 선택 질문을 발명하지 않았다.

| 질문 | 처분과 해결 근거 |
| --- | --- |
| D-R: N100k 각 workload의 r, warmup 제외, metric별 median/p95 estimator·IQR와 한계를 어떤 고정 설계로 수용할 것인가? | 미정. 비참여 검토자의 표본 설계 심사와 소유자의 exact campaign 범위 승인 필요. n=3을 규범으로 만들지 않음 |
| D-U: 실제 full 입력 SHA와 source/runtime/state/Context/serializer/codec/HTTP/cache·통계 주장을 고정한 뒤 어떤 비교를 공유하며 U는 몇 개인가? | 입력 의존 미정. 실제 identity에 대한 독립 대조 필요. 승인자가 근거 없이 숫자를 정하는 항목이 아님 |
| D-SOURCE-CONDITIONAL: 무변경 원 B03의 필수 E3/부기 직접 관측이 불가능하다고 별도 심사에서 확정되면, 원 의무를 차단 상태로 유지할 것인가, 별도 규범 개정 심의안을 요구할 것인가? | 조건부 규범 질문. 소유자/위임된 규범 승인권자만 처분 가능. 현 승인에는 대체 source로 원 8개를 수용할 권한이 없고 PRE04는 변경을 선택하지 않음 |

## 4. 이관 8개 의무의 수정 의존성

아래 모든 의무는 **현재 완결 불가·독립 수용 0**이다. 현재 확인 입력에서 N100k 부분을 완결하려면 모두 새 N100k 취득과 source-compatible accepted setup이 필요하다. 이 공통 전제는 별도 acquisition 8회를 뜻하지 않는다. 적법한 공유 범위와 trial 독립성 설계가 acquisition 수를 결정한다. 도구만 새로 만들면 끝나는 의무는 없다.

| 의무 | 기준선 부재의 효과 | 하위 N 재사용 | 기준선 외 추가 필수 증거·미결정 |
| --- | --- | --- | --- |
| T35-100K-NC | 새 취득·complete accepted admission 뒤 정상 no-change 반복 필요 | 이 N100k gate의 대체 없음 | rows/hash/validation/write·HTTP/RTT/memory·D1–E4·median/p95, ID/sequence 유지; r와 collector 미정 |
| T35-100K-CARD | 같은 전제 뒤 card D1 반복 | 대체 없음 | 실제 generation 전진과 같은 비용·단계; r·trial before/after와 collector |
| T35-100K-CASH | 같은 전제 뒤 cash D1 반복 | 대체 없음 | 실제 generation 전진과 같은 비용·단계; r·trial before/after와 collector |
| T35-ROWS | N100k 새 setup, 하위4점도 신규 측정용 admission 필요 | B04 동종 SQL/write/work·시간 일부 | 다섯 N×세 workload의 실제 SQL/반환행·raw/index lookup·query plan; n1 보완의 coverage 한계·필요시 해당 cell 반복 설계 |
| T35-NET | N100k 새 setup과 실제 matched FULL 필요 | 하위4점 entity/request 집계 일부 | 양방향 entity/canonical·실제 framing/headers·RTT dependency/cache·FULL; U·q와 교란 자격 |
| T35-GZIP | N100k 및 별도 다양성 setup, matched FULL 필요 | 역사 offline codec은 원 범위만 | 같은 source/state/Context full input, gzip6·버전/CPU·network/parse/validation/write·두 family; U·통계 주장 |
| I25-E3-100K | 정상 세 workload setup·반복을 공유하되 acquisition/recovery는 정상 밖 | 하위 N은 참고만 | E3Verify/Prepare/Commit 직접 rows/bytes·SQL/tree/index/pin/CAS/readback, 5종 full counters=0; 직접 seam 미입증, r 공유 |
| I25-BOOKKEEPING-100K | 같은 정상 setup·반복 공유 | 하위 N은 참고만 | lease/GC/refcount/root-pin/transfer의 직접 read/visit와 hidden full graph/history·flat P 부재; 직접 seam·r 공유 |

§35-T69 722–727행의 추적 ID와 §36 I25를 [의무별 JSON](benchmarks/t69-pre04/revised-obligation-dependencies.json)에 연결했다. baseline establishment는 입력 준비이며 listed cost/I25 acceptance가 아니다. 초기·재시작·명시 full recovery의 O(N)을 정상 counter 밖으로 분리해야 한다. 정상 full history fetch/hash/serialize/write 0과 bounded leaf/path/affected index, flat P 부재, 측정 완결성으로 평가하며 새 절대 ms 합격선을 만들지 않는다. wall-time가 평평하다는 이유만으로 I25를 통과시키지 않는다.

## 5. 기존 증거의 정확한 재사용 범위

| 보존 증거 | 재사용 가능한 범위 | 이번 계획에서 금지하는 확대 |
| --- | --- | --- |
| B04 하위1k/5k/10k/50k, 정상 ON36 | 실제 hash sink·primary span·stage SQL NEW write byte·operation work·원 HTTP 집계·시간/RSS·accepted/E4. cell별 원 n3 | SQL-read 완결, 직접 E3 stage work, 새 framing/header, N100k로 승격 불가 |
| 같은 정상 OFF36 | 원 ON/OFF timing·값/Target/상대 sequence 동등성 | 새 collector 교란으로 일반화 불가. counter null은0이 아님 |
| B04 cold ON4/OFF4 | 당시 cold 완료·교란·50k의 두 observation 사용 | 정상 반복이나 새 measured cold 성공으로 합산 불가 |
| B04 진단 publication26·prepare/discard6 | 각 진단 경계의 사실 | 정상 accepted 분포·실제 E3 accepted 시간의 대체 불가 |
| B04 하위4점 압축 DB12개와 manifests | 원 backup·SHA·역사 graph/value 검증 | 현재 epoch·same-connection accepted admission 또는 N100k 사본 아님 |
| phase-b-final/continuation 다섯 점 offline gzip6/Brotli4 n20 | 원 full input SHA·길이·압축 크기/CPU | 현 B03 matched HTTP/headers/parse/write로 전환 불가 |
| B02 독립·A02 N100k 완료 manifests/raw | 당시 source-qualified 기능·E3/E4·client reopen 완료 | 현재 복구 DB·B03 ON 정량/I25·현재 lease 내 feasibility 아님 |
| P03 원 full-result/full-analysis·raw | 실제 진행·만료·미완료·자원 관찰 | accepted baseline·matched tail·E3/E4 성공 아님 |

B04 통제 80개 raw와 B02/P03 raw gzip26개의 압축·해제 bytes hash를 정적으로 재대조했다. 두 B02 완료 run의 result/fixture raw도 실제로 읽었다. 기존 raw checksum의 확인은 새 measurement나 DB 개방이 아니다. 처음 조회한 `t66f-b02-implementation/summary.json`은 존재하지 않아 입력 목록에 오조회로 기록했고, 실제 A02 completed-run raw를 사용했다. 원 자료 부재 판정을 이 잘못된 이름으로 만들지 않았다.

새 metric n1과 역사 timing n3는 서로 다른 표본 집합이다. 새 n1에 역사 n3/p95/IQR을 빌려 붙이지 않는다. 동일 source/input/경계가 확인되는 동종 metric만 재사용하며, 실제 trial별 SQL/path/framing 차이가 드러나면 영향 cell만 보완 계획을 수정한다. 유효한 기존 lower-N 증거를 무조건 재실행하는 backlog는 추가하지 않는다.

## 6. 추가 관측기 자격 — PRE02 BLOCKED 유지

원 B03 IR07 correctness는 **CLOSED — ORIGINAL SOURCE AND SUPPORTED RUNTIME**로 유지한다. material 반증을 발견한 것이 아니다. 추가 필수 observer의 자격은 **BLOCKED**다. PRE04는 observer를 구현·활성화·시험하지 않았고 독립 observer audit를 수행하지 않았다. 아래 테스트는 향후 별도 범위·승인 아래 필요한 최소 자격 증거이며 실행 요청이 아니다. 각 metric의 event/경계·기존 독립 자격·gap·최소 oracle·source 영향은 [자격 결측 JSON](benchmarks/t69-pre04/instrumentation-qualification-gaps.json)에 개별 기록했다.

| metric | 필요한 직접 event·경계 | 기존 지원·독립 자격 | 결측과 최소 자격 증거 |
| --- | --- | --- | --- |
| SQL rows-read | Python cursor 실제 fetch/iteration, Dart native ResultSet 반환/소비와 raw/index query callsite; D1–E4 단계 귀속 | statement/bind/DML·NEW write bytes는 IR07 원 범위. 실제 SELECT 반환행 집계 없음 | 0/1/다중·부분 fetch·중복 읽기·NULL/TEXT/BLOB·실패/rollback literal/native 독립 oracle. 반환행과 VM/pager 방문 분리, EXPLAIN은 동일 state의 타이머 밖 |
| HTTP request/response bytes | 실제 TLS application endpoint의 양방향 entity/serialized headers·method/path, client send→complete-body·dependency/cache event | B04 server 집계와 client body 합만. 새 header/요청별 RTT 직접 자격 없음 | 알려진 UTF8 body/headers의 양끝 capture·재결합, empty/partial/error/retry/dependency oracle. server interval과 client RTT 중첩, TLS record/TCP 미관측 한계 공개 |
| framing overhead | 실제 entity의 base64 token·JSON delimiter/metadata·escaping/UTF8와 canonical payload association | entity/decoded/chunks 합만; token/body 미보존 | 길이 mod3=0/1/2·빈/다중chunk·escape/비ASCII 실제 capture의 부분 합과 원 bytes 대조. `4×ceil(decoded/3)`나 재직렬화 모델로 wire 대체 금지 |
| full gzip | 원 authoritative full 생성 bytes·gzip6 CPU·전송·decode·원 full parse/validation/durable write/readback | 역사 offline codec만. matched facade/consumer 미구현·미자격 | 작은 고정 입력의 SHA/길이·level/version/mtime·압축 bytes·identity/gzip decode parity·durable readback 독립 대조. replay는 backend 생성 비용 별도 |
| E3 full-N work | 실제 `SegmentedWork.add`의 5종 full counter 및 SQL/tree/index/pin/CAS/readback의 E3Verify/Prepare/Commit 직접 귀속 | stage byte/SQL은 존재하나 `work.dart:1–11`은 stage 없는 map, `store.dart:105`에서 내부 final 생성 | **무변경 외부 seam 가능성부터 정적 판정**. 가능할 때만 별도 작은 단계별 known-event·정상0/명시recovery 비0·실패/취소 oracle. aggregate subtraction·prepare/discard 대체 금지 |
| lease/GC/refcount bookkeeping | 정상 D/E pin/release·refcount·typed edge 실제 SELECT/visit/DML·query plan의 직접 callsite 귀속 | D3 read/path와 root-pin/GC DML 일부. 직접 정상 부기 read/visit 자격 없음 | callsite→event map, 작은 known graph의 affected path·명시 maintenance 대조, 반복 pin/release·cancel/expiry/rollback의 중복/누락 oracle |

공통 자격은 collector와 독립적으로 만든 예상값, exact harness SHA·원 payload 전후 불변, 중복/누락/미지원/실패/취소/late-event·nested owner/lifecycle·monitoring 안정성, native 결과와 bytes 일치, observer 자체 SQL·query plan·CPU/RSS/cache 교란 분리를 포함한다. 필요 matched OFF `q`도 이 자격 범위에서 결정한다. 기존 ON/OFF는 prepared cache 이득과 관측·Stopwatch 비용의 순효과이며 순수 callback CPU나 새 구성의 교란이 아니다.

외부 harness만으로 가능한지 입증되지 않았으므로 source identity 영향은 **미정**이다. 원 SQL wrapper/trigger·work 생성부·stage·monitoring ownership을 바꾸면 원 instrumentation payload의 결과라고 제출할 수 없다. 그런 변경이 필요하면 차단을 유지하고 별도 승인·재자격의 문제로 보고해야 한다. `store_publication.dart:437–440`의 최종 `finalAuthorityFence()`와 동기 `COMMIT` 사이에는 await/hook/callback/추가 observer callout을 넣을 수 없다. monitoring guard를 약화하거나 원 private connection을 변경해 자격을 얻는 경로를 제안하지 않는다.

## 7. baseline establishment의 필수 준비와 의존성

현재 입력으로 가능한 지원 복구 경로가 없으므로 다음 화살표는 **미래 별도 허가의 조건**이다. 실제 획득·복원 절차나 실행 명령은 아니다.

```text
원 source/runtime·exact fixture 확인
  + 무변경 관측 가능성·추가 observer 독립 자격
  + r/U/q·trial 설계·자원/중단 가능성 심사
    → 소유자의 별도 baseline establishment GO
    → 새 baseline establishment [현재 계획/실행 0, 비용 미정]
    → 실제 새 epoch·complete accepted generation·같은 연결 독립 admission
    → exact 측정 cell·campaign의 별도 명시 GO
        ├─ 정상 no-change/card/cash ON [13+3r 중 해당 cell]
        └─ 실제 matched FULL/gzip 비교 [U, acquisition과 별개]
    → §35/I25 원자료·표본·단계별 평가
    → 비참여 독립 수용자에 의한 각 8개 수용

별도 전체 T6.9 B §27/29 initial/full/restore/crash 의무
    → 해당 source/fixture·Cold/Full 별도 계획·예산·명시 GO
    → 별도 O(N) 측정 및 해당 gate 독립 수용
```

이관 8개에는 새 instrumented full cold 성공이 독립 MUST가 아니다. 그러나 현재 새 baseline 확립이 필요하다는 준비 비용·위험은 사라지지 않는다. baseline 준비를 cold evidence로 세려면 해당 fresh Cold의 처음부터 끝까지 유효한 source/collector/측정 구간·별도 허가·독립 수용이 있어야 하며, 이 계획에는 그런 실행을 편성하지 않았다. 복구·restart·full verification 시간을 제외한 incremental 실행을 cold로 부르지 않는다. B §27의 별도 O(N) workload 측정 의무도 이관 normal evidence로 대체하거나 면제하지 않는다.

baseline의 최소 admission 입력은 다음과 같다.

- 취득 source는 원 B03와 지원 runtime이어야 한다. 취득의 ON/OFF 구성은 아직 선택·승인하지 않았다. OFF preparation을 검토하더라도 ON 완료 cell이나 계측 feasibility를 대신할 수 없으며 ON 전환 뒤 같은 연결 provenance·collector 지원을 별도 입증해야 한다. B02나 B05/B08로 만든 상태의 호환을 가정하지 않는다.
- B04와 이어지는 대표 fixture는 seed662602·평가일2026-10-05·offset540, current ledger105·다른 authoritative rows35, initial hot87364B/control3178B를 기준으로 실제 SHA·문자열/관계/descriptor까지 대조한다. N은 ledger 총 N이고 전체 authoritative rows는 N+35, archive는 N−105다. H를105라는 숫자만으로 정의하지 않는다.
- no-change는 D0, card는 `ledger_entries.id=1002`, cash는 `cash_flows.id=101`의 amount UPDATE D1이다. PRE01의 세 회차 amount1001/1002/1003 및 −51/−52/−53은 역사 대응 제안이다. **r가 미정이므로 r>3의 값·회차 규칙은 발명하지 않고 실행 전 exact mutation schedule을 승인받아야 한다.** 순차 중간 변경과 L/E/B를 숨기지 않는다.
- 각 setup의 11-table 실제 row/value digest·schema/Versions·control/policy·trusted HTTPS origin/NS/principal/Context/Target, complete immutable objects/global index/receipt/root pins/current/previous와 source engine을 연결한다. 역사 initial N100k의400532 objects·261543083 canonical B를 미검증 새 Target의 count로 복사하지 않는다.
- C §5의 신규 dataset/서버 publisher lineage·새 epoch·fresh observation을 확인한다. 서버 cold startup과 physical restore의 새 epoch 의무를 old ID 보존으로 우회하지 않는다. 같은 native connection의 generation/data_version·provenance와 실제 accepted publication/readback/E4를 확인해야 한다.
- backend 실제 값/presenters와 native graph/값 digest·FK/hash/root·accepted before/after를 독립 대조한다. 서버 금융 authority를 유지하며 모바일 canonical 금융 엔진을 추가하지 않는다. Snapshot v7, OfflineBaseline v4, segmented 저장 형식, engine/payload와 generation을 혼동하지 않는다.
- 별도 허가된 실행에서는 지원 backup API의 일관 backend/client 증거를 확보·검증해야 한다. source/fixture generation·bootstrap·취득·admission·oracle·backup·실패 보존의 시간/공간을 모두 비용화한다. 현재 그러한 준비 실행은0이다.

다양성은 PRE01의 `less-repetitive-10k-v1` 알고리즘을 **미생성 제안**으로 유지한다. archive `title/usage_place`만 기존 UTF8 byte 길이의 deterministic hex stream으로 바꾸고 NULL/빈값·current105·나머지 table·금융/key/관계/timestamp를 보존하는 설정이다. 정확한 함수는 [행렬 JSON](benchmarks/t69-pre04/revised-execution-matrix.json)의 `diversity_fixture_proposal`에 보존했다. 대상 행/length histogram·distinct/반복도·전체 입력 SHA·hot/control·graph/leaf census를 사전에 고정하고 독립 admission해야 한다. reachable count는 null이며 fixture를 만들거나 원 product source를 바꾸지 않았다.

같은 accepted setup을 여러 정상 test에 공유하는 조건은 exact source/runtime/harness, 같은 trusted origin/NS/principal/Versions/Context, complete graph/pins와 유효한 같은 연결 provenance·generation/data_version, J/pending 없음, 통제된 cache와 before/after 기록이다. no-change는 ID/sequence 유지, mutation은 실제 새 generation으로 전진해야 한다. 연결 재개·서버 restart·epoch 변경·외부 write는 재admission과 별도 비용을 요구한다.

**card/cash 뒤의 mutable DB는 초기 상태의 독립 trial이 아니다.** 순차 설계를 채택하려면 값·R/generation·previous/history/cache 누적과 실제 D/L/E/B를 공개하고 주장 범위에 대한 독립 수용이 필요하다. 동일 초기 상태의 독립 trial이 필요하면 지원되는 reset 또는 독립 초기 setup의 별도 설계·예산·승인이 필요하며 취득 수가 늘 수 있다. 역 UPDATE는 R·tree shape·history/cache를 되돌리지 않으므로 reset으로 인정하지 않는다. 물리 DB/accepted pointer 복사를 trial 독립성 해법으로 제시하지 않는다.

## 8. 잠정 최소 측정 행렬

PRE02의 검토된 축소를 유지한다. `r`은 N100k workload별 반복 수, `U`는 exact 비교 identity와 통계 주장에 따른 미충족 고유 FULL 단위 수, `q`는 새 관측기 교란에 필요한 조건부 matched OFF 수다. **세 값 모두 null**이며 숫자 r/U를 만들지 않았다. 반복 의무를 단발로 충족할 수는 없고, n=3을 승인된 최소로 정하지도 않는다.

| class | 잠정 새 측정 수 | 고유 목적·제약 |
| --- | --- | --- |
| 하위1k/5k/10k/50k × no-change/card/cash ON | **12** | cell별 결측 metric n1 보완. 기존 동종 n3 비용 분포 보존. 새 stage 분포·trial path 차이가 필요하면 영향 cell만 별도 확대 심사 |
| N100k no-change/card/cash ON | **3r** | 세 정상 비용 의무와 ROWS/NET/GZIP·두 I25를 같은 run에서 공유. accepted baseline·새 collector 없음 |
| 다양성 N10k no-change ON | **1** | 두 문자열 family의 단일 matched 비교. tail 분포·모든 workload 효과 주장 불가 |
| FULL | **U** | 대표15 cell와 다양성 case의 같은 source/state/Context 비교는 필수. 모든 ON마다 fresh FULL 반복이라는 수 규정은 없음 |
| OFF | **무조건0, 조건부 q** | 새 observer 교란을 설명하는 필요한 경계만 독립 선정. 기존 OFF36은 원 구성만 |
| 하위 N 일괄 n3 추가 / 독립 I25 실행 | **0 / 0** | blanket +24나 별도 I25 acquisition을 만들지 않음 |
| planning 단계 새 measured full cold | **0** | baseline 준비 필요와 별도 whole-T69 O(N) 의무를 숨기지 않으면서 실행 편성·승인은0 |

정상 ON 식은 **13+3r**, FULL은 **U**, 조건부 OFF는 **q**다. prerequisite acquisition의 수·시간·공간은 이 식에 포함되지 않으며 별도 등록했다. N100k baseline setup은 현재0개이고 향후 최소1개의 새 accepted setup이 필요하지만, 동일 초기상태 trial·reset·family/epoch 설계에 따라 더 필요할 수 있어 `A100k`는 null이다. 한 acquisition이면 충분하다고 가정하지 않는다. 하위 backup과 다양성 setup도 현재 실행용 admission이 없으며 새 준비가 필요하면 규모와 무관하게 별도 승인 대상이다.

[기계 행렬](benchmarks/t69-pre04/revised-execution-matrix.json)은 12개 하위 cell, 3개 r-매개 N100k cell, 다양성1개를 **16개 template**으로 기록한다. 각 cell에 고유 목적·의무·source·N/H/D/family·mode·ON·규범 반복 규칙·기존/결측·baseline 종속성·collector·비용 null·제안 cap·abort ID·NOT AUTHORIZED를 기록했다. FULL도 각 template에 대응한 비교 후보16개를 별도로 기록했으며 후보 수를 U나 실측 수로 혼동하지 않는다. 조건부 OFF와 whole-T69 Cold 경계에도 같은 필드를 기록했다. 실제 mode별 실행은 모두0이다.

FULL 공유는 source/runtime·DB state/read-view·Context·fixture·실제 full input SHA·serializer·codec 설정·HTTP/cache 조건이 같고 통계 주장과 양립함을 독립 확인할 때만 가능하다. 같은 bytes의 크기 비교를 공유할 수 있어도 한 timing을 여러 독립 sample로 복제할 수 없다. 서로 다른 mutation 값의 비교는 합치지 않는다. PRE01 interleaving의 cash 뒤 다음 no-change는 같은 입력 후보일 뿐, 실제 SHA·cache 대조 없이 U 절감을 확정하지 않는다. identity+gzip 양쪽 leg를 유지하는 설계면 **2U response legs**이나 별도 규범 표본 수가 아니다. FULL latency/CPU 분포를 주장하려면 해당 표본 설계도 사전 결정한다.

raw/source 불일치·trial별 path 차이·새 분포 주장·collector 교란·FULL identity 차이·다양성 coverage 변화가 확인될 때만 해당 cell의 조건부 확대를 심사한다. baseline/collector 부재·full-N/authority 위반·lease/예산 소진은 확대 trigger가 아니라 중단·보존·차단 보고 사유다. r/U/q와 취득 비용이 미정인 상태의 숫자 총량·완주 가능성은 제시하지 않는다.

## 9. P03 실제 실패와 자원 근거

[P03 원 full-analysis](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json)와 [full-result](benchmarks/t66f-b03-ic01-p03/evidence/full-result.json)의 사실을 유지한다. 당시 source는 IC01/P02→P03이며 최종 IR07 payload 실행이 아니다.

| 역사 사실 | 값·경계 |
| --- | --- |
| 총 elapsed | **2,699.957907초** |
| completed immutable objects | **397,146 / 400,532**, 미취득3,386개 |
| observation 만료 | **3회**, 각각 실제900초, HTTP410 |
| E3 publication / E4 accepted read | 성공 없음 / 성공 없음 |
| resource-guard failure | 보고 없음 |
| functional correctness failure | 재현 없음 |
| 직접 종료 | `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)` |

남은 약0.85%가 허용 lease 안에 끝났을 것이라는 결론은 없다. 객체가 모두 도착해도 E3 publication/readback과 E4는 따로 완료해야 한다. observation expiry는 자원 고갈의 증명이 아니며 외부 watchdog의 선행 강제 종료나 금융 correctness 실패로 바꾸지 않는다. 기존/추가 instrumentation만이 원인이었다고도 단정하지 않는다.

원 backend handler 합1886.414804612초·CPU1883.257226036초는 큰 처리 비중을 보이지만 network/client/scheduler/observer의 순수 비용은 미분리다. client SQL API380.084418초와 callback 하한23.548612초는 full-analysis 전체 범위다. PRE01의380.069584초·23.548580초는 첫 observation 전 SQL14834μs·callback32μs를 제외한 범위다. callback은 SQL API에 포함되며 backend/HTTP/client 시간도 겹치므로 합산 분해하지 않는다.

B04 원 B03의 50k ON cold1573.537722초·transfer1399.633084초와 [기존 N100k cold NO-GO](benchmarks/t66f-b04/fullscale-decision.json)는 유지한다. 당시 단순2798.36초 외삽은 역사 NO-GO 산술 참고이며 현100k 예측값이나 보편적 불가능 증명이 아니다. B02 기능 성공의 다른 source·계측·범위도 현재 B03 ON+새 collector의 feasibility로 전용하지 않는다.

## 10. 자원·중단 예산 수정 판단

아래 숫자는 **역사 측정값이 아닌 PRE01의 미승인 정책 제안**이다. RSS8GiB·free disk10GiB는 B04의 guard를 가져온 제안이지만 미래 구성의 완료 보증은 아니다. [자원 JSON](benchmarks/t69-pre04/resource-and-abort-revision.json)은 각 bound마다 유형·역사 비교·강제 방법 제안·early-stop 보존·partial state·범위 밖 자원·명시 owner 승인 필요·유효 완료 충분성 미입증을 기록한다. 새 runtime/peak projection은 null이다.

| 제안 bound | 지원 근거와 새 기준선 필요의 영향 | 판단 |
| --- | --- | --- |
| 정상120초 | 하위 ON 최대10.959006초에는 관측 여유. acquisition/admission 제외였으며 N100k·추가 collector 미측정 | PARTIAL, 완료 충분성 미입증 |
| FULL300초 | qualified matched full 생성·codec·HTTP·parse/validation/write 비용 없음 | UNVERIFIED |
| admission1800초 | 과거 새 cold 제외안. 현재 baseline0이므로 establishment 비용을 대신할 수 없음 | REVISION REQUIRED |
| scale3600초 | 옛 r3 예시9×120+9×300=3780초, OFF9 포함4860초이며 준비도 별도였음 | REVISION REQUIRED |
| campaign14400초 | 옛30ON+30FULL 상한 합12600초, OFF 포함16200초. 6 admission×1800 포함23400/27000초였음. 새 취득은 추가 미정 | REVISION REQUIRED |
| scratch10GiB | initial canonical261543083B는 DB/index/previous/WAL/temp·backup 전후·FULL/raw/build/evidence의 동시·누적 peak가 아님 | UNVERIFIED |
| RSS8GiB | B04 50k group2951401472B, B02 100k tree5772578816B는 서로 다른 범위. 새 full/두 client/buffer/observer peak 미측정 | UNVERIFIED |
| free disk10GiB / 시작20GiB | 과거 free102982717440B는 순간값. 새 취득·실패 유일자료 보존 reserve·quota/경쟁 task 소비 미산정 | UNVERIFIED |
| 시작 MemAvailable10GiB | 과거22183784kB는 예약·cgroup/owned cap의 증거 아님 | UNVERIFIED |
| 한 campaign1회 | 실패 자동 재시도0이라는 유한 정책만 유지 가능. launcher·강제 종료수단·owner GO 없음 | UNAPPROVED |

실행비용 검토식은 `120×(13+3r) + 300×U + 120×q + 준비/취득/admission/oracle/backup/증거보존/cleanup`이다. N100k scale에도 `360r + 300U100k + 120q100k + T_fixture + A100k×T_establish + T_admission + T_oracle_backup_evidence_abort`를 보이게 넣어야 한다. 공유 setup 비용은 한 번 계상하되 누락하지 않는다. cap 합은 실제 runtime 예측이 아니며 nested deadline에 먼저 중단하는 것은 전체 완료 보증이 아니다. 이 문서는 cap을 올리거나 lease/attempt를 늘리지 않는다.

각 budget의 제안 강제 범위는 다음과 같다. 구현·자격 확인은 모두 미완료다.

- 정상은 실제 operation 시작부터 E4·collector close까지, FULL은 backend 생성·codec·전송·consumer write/readback까지 경계를 정한다. 준비·admission은 별도이고 상위 scale/campaign의 총비용에서는 빠질 수 없다.
- scale/family와 campaign deadline에는 fixture/epoch bootstrap·취득·검증·측정·FULL/OFF·oracle·supported snapshot·압축/manifest 검증·중단/cleanup을 배분해야 한다. observer qualification·빌드/runtime 취득 등 별도 작업도 범위 밖 비용으로 공개한다.
- owned 전체 process tree/group, task 경로의 allocated bytes와 임시/backup 증폭·증거 누적량·filesystem free/quota를 확인해야 한다. 1초 polling은 사이 RSS/disk peak나 native 호출 즉시 중단을 보장하지 않는다. 합산 RSS의 공유 page 중복과 kernel/socket/cache·다른 task 자원은 별도 한계다.
- cooperative cancel→제안 최대30초 cleanup→필요시 owned group 종료는 아직 자격 없는 제안이다. deadline이 grace·증거보존 시간을 포함하는지 소유자가 exact 상한으로 결정해야 하며30초를 자동 연장으로 붙이지 않는다. host/production·타 process 종료는 범위 밖이다.

C §16/§35-T69의 TTL≤900초, client attempts3/observations3, principal Available≤4는 서로 다른 제한이며 불변이다. 최대 active window2700초는 observation 재인가 gap을 포함한 wall 보증이 아니다. 전송 완료 뒤 local E3/E4 시간도 별도로 필요하다. **현재 unchanged observation 규칙과 미검증 budget 아래 N100k establishment의 타당한 완료 경로는 NOT ESTABLISHED**다. 그런 경로를 입증하지 못하면 실행 불가 상태를 유지한다. PRE04는 모든 미래 실행이 수학적으로 불가능하다고 단정하지 않지만, 현재 예산으로 실행준비 PASS를 발급할 수 없다.

## 11. 실패·중단과 증거 보존 계약

[자원 JSON](benchmarks/t69-pre04/resource-and-abort-revision.json)의 A-SOURCE/BASELINE/COLLECTOR/PATH/LEASE/RESOURCE/FAILURE를 모든 cell에 연결했다. 첫 no-change·동등성·collector·accepted/E3/E4 실패 뒤 card/cash·상위N·다음 campaign을 자동 시작하지 않는다. source/runtime drift, incomplete provenance, missing collector, 정상 full-N/flat P/hidden scan·authority 위반은 성공0으로 제출하지 않는다. 실제 정상 full-N 위반은 귀속 구현 거부·별도 수정/재자격 사유이며 이 계획이 최적화 작업을 시작하지 않는다.

early stop에는 command/cwd/exit/time·source/runtime/binary/harness·fixture/Target/epoch·accepted/generation 전후·stage별 partial counters/HTTP·마지막 observation/error·resource trace·manifest SHA/mode/size를 남겨야 한다. 취득 partial objects·staging, prepared/pending, WAL/SHM 또는 **COMMIT 후 readback 미완료**가 남을 수 있다. 종료를 rollback 완료나 accepted 성공으로 추정하지 않는다. current/previous/frozen B/J 및 유일 matched backend/client를 보존한다. 실패 보존 reserve와 crash 시에도 원자료를 확보할 강제수단을 preflight에서 검토해야 한다.

취득이 객체100%에 도달했다는 사실과 E3/E4 완료는 독립 조건이다. 낙관적 잔여 작업 하한조차 남은 유효 window를 넘는 명백한 불가능 조건, lease/attempt·승인된 자원 cap 소진, 보존 여유 부족은 중단 사유다. 자동 rerun/resume·cold 전환·새 observation 한도·자원 증액은 없다. 지원 backup 절차와 독립 검증이 끝나기 전 유일 자료를 삭제하지 않는다. 검증된 해당 task-owned disposable만 실험 경계에서 정리하며, 중단된 DB를 급히 파일복사하는 복원 recipe를 제시하지 않는다.

## 12. 실제 차단 준비와 독립 심사 인계

[차단 등록부](benchmarks/t69-pre04/preexecution-blocker-register.json)는 실제 실행 전 차단만 순위를 매긴다. 아래 A–E는 준비/수용 범주이며 일반 최적화·감사 backlog가 아니다.

| 범주 | 완료되어야 할 정확한 준비 | 현재 상태·차단 순위 |
| --- | --- | --- |
| A. 규범·표본 결정 | 원 B03·같은 full serializer는 이미 확정. r/warmup/estimator/IQR·주장 범위, actual input별 U 공유와 필요 q·trial 독립/순차 설계 고정 | OPEN, 3순위. 조건부 source 변경 문제가 확정될 때만 규범 승인권자 질문 |
| B. instrumentation qualification | 6 metric event/경계·무변경 seam 가능성·source 영향·독립 literal/native oracle·교란/guard qualification | **BLOCKED, 1순위**. 자격 없는 실행으로는 의무 수용 경로가 생기지 않음 |
| C. baseline establishment | exact 대표/다양성 fixture·origin/새 epoch·complete generation/receipt/index/pins·같은 연결 provenance 확보 경로, unchanged lease/자원·abort·실패 보존 | **BLOCKED, 2순위**. baseline0이며 새 acquisition 비용·완료 경로 미입증 |
| D. 실행 authorization | A–C의 독립 preflight 뒤 establishment용 및 measured cells/campaign용 exact 범위·횟수·hard cap·중단규칙의 소유자 명시 GO | NOT GRANTED, 4순위. 실제 baseline 확립 뒤 독립 admission을 재확인 |
| E. evidence acceptance | 실제 raw/경계/통계·source/fixture·E3/E4·자원/실패를 각8개별 source-qualified 독립 수용 | 0/8. 향후 수용 gate이며 실행 전 이미 있어야 하는 증거로 순환 요구하지 않음 |

미래 비참여 독립 preflight 검토자는 승인 B11 exact bytes·원 frozen source/runtime와 loaded artifact, PRE03/PRE04 baseline0과 새 취득의 별도 허가/비용, collector의 무변경 seam/자격과 원 guards, 각 cell의 fixture/epoch/provenance·mutation/trial 독립성, r/U/q와 FULL 공유, 준비부터 실패보존/cleanup까지 예산과 종료수단의 강제 가능성을 확인해야 한다. 원 TTL/attempt/principal 제한과 첫 실패 stop, 무조건 OFF/blanket 반복 금지, 비이관 whole-F·R1·기기·배포 gate도 대조해야 한다.

정적 preflight는 아직 만들어지지 않은 actual accepted generation을 선인증할 수 없다. establishment의 별도 GO 뒤 실제 epoch·complete graph/receipt·같은 연결 provenance를 독립 admission하고서야 측정 GO의 조건을 충족할 수 있다. 소유자가 조건부 campaign 범위를 미리 승인하더라도 actual admission 실패 시 측정은 차단이다. 이후 수용자는 실제 raw·명령·source/runtime/fixture·단계 완료/취소·통계·자원 trace와 SHA를 다시 대조한다. PRE04 작성자는 이 심사를 대신하거나 스스로 실행준비를 인증하지 않는다.

정적 수정안의 **독립 검토 제출 준비는 READY**다. 그러나 필수 source 입력은 존재해 BLOCKED 판정의 source-missing 조건에는 해당하지 않고, 직접 관측·자원·표본 결정이 미해결이므로 최종 판정은 **PARTIAL**이다. 문서의 완결성과 실행 가능성은 다른 판단이다. 8개가 나중에 모두 수용돼도 formal F·whole-T69·기기·R1·production gate는 따로 남는다.

## 13. 산출물·정적 검증·보존

필수 산출물은 이 보고서와 다음 8개 machine-readable 기록이다.

- [기준선 부재 영향](benchmarks/t69-pre04/baseline-unavailability-impact.json)
- [수정 의무·의존성](benchmarks/t69-pre04/revised-obligation-dependencies.json)
- [source·비교군 결정](benchmarks/t69-pre04/source-and-comparator-decisions.json)
- [관측기 자격 결측](benchmarks/t69-pre04/instrumentation-qualification-gaps.json)
- [수정 실행 행렬](benchmarks/t69-pre04/revised-execution-matrix.json)
- [자원·중단 수정](benchmarks/t69-pre04/resource-and-abort-revision.json)
- [실행 전 차단 등록부](benchmarks/t69-pre04/preexecution-blocker-register.json)
- [단일 후속작업 결정](benchmarks/t69-pre04/next-action-decision.json)

[입력 목록](benchmarks/t69-pre04/input-manifest.json), [source·승인 정적 검증](benchmarks/t69-pre04/source-and-approval-validation.json), [정적 내용 검증](benchmarks/t69-pre04/static-validation.json), [종료 보존](benchmarks/t69-pre04/final-preservation.json), [산출물 manifest](benchmarks/t69-pre04/evidence-manifest.json)을 함께 제공한다. 초기 source·승인·역사 raw 검사1,195개 성공은 bytes/구조의 정적 확인이며 새로운 성능·기능 시험 수가 아니다. 실제 source member가 없는 `engine_artifact.py`를 처음 조회한 도구 오류는 실제 `observation.py` 정의로 교정했다. 제품 실행이나 역사 source 수정으로 해결하지 않았다.

종료 보존은 시작6,553개 기존 파일의 SHA·크기·mode, HEAD/branch·인덱스 원문과 path/mode/blob/stage 전부, 원 B03 frozen5개와 B05/B08 실험 archive2개의 지문을 대조한다. 변경은 PRE04 보고서·전용 evidence에 한정한다. ignored runtime·production 전체 무결성이나 access-time 불변까지 주장하지 않는다. PRE01–PRE03·B01–B11·승인 구속 문서·기존 미커밋/미추적 작업을 덮어쓰지 않았다.

SQLite 연결·생성·복원·import, object-store 생성, acquisition, full cold/측정, observer 구현, 제품/B03 instrumentation/protocol/engine admission 변경, emulator/실기기, commit/push는 모두0이다. 정적 무실행이라는 사용자 범위에 따라 AGENTS의 일반 npm build/backend 검증은 실행하지 않고 JSON/해시/참조·규범/행렬 일관성 정적 검사로 확인했다. 샌드박스 bwrap 초기화 오류 뒤 승인 검토된 파일 읽기·PRE04 쓰기만 사용했으며 자동 승인 거부는 없었다. Git 읽기는 보존 지문 수집 이후 `GIT_OPTIONAL_LOCKS=0`으로 수행했고 인덱스는 PRE02/PRE03 지문과도 일치한다. reset/stash/clean/checkout/rebase/restage/commit/push는 하지 않았다.

대형 임시 실험 산출물 정리는 **NOT APPLICABLE**다. PRE04 보고서·JSON만 보존하며 disposable scratch 생성·삭제·회수는0B다. production DB/Snapshot/.env/API/서비스에는 접근하지 않았다.

## 14. 최종 기록과 단일 다음 작업

다음 작업은 **PRE04-NEXT-01 하나**다. 큰 기준선 취득 비용을 승인하기 전에 원 source가 필수 직접 증거를 낼 수 있는지부터 확인해야 한다. 이 후속 정적 심사도 acquisition·복원·DB 개방·observer 구현·제품/규범 변경·측정·기기 작업을 포함하지 않는다. 실행 일정을 자동으로 잡지 않는다.

```text
T6.9-PRE04 EXECUTION-READINESS PLAN REVISION:
PARTIAL

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

APPROVED B11 AMENDMENT:
VERIFIED

ORIGINAL B03 SOURCE:
VERIFIED

PRE02 INDEPENDENT READINESS REVIEW:
PARTIAL — HISTORICAL

PRE03 N=100K BASELINE RECOVERY:
NO SUPPORTED PATH

CURRENT RECOVERABLE N=100K ACCEPTED BASELINES:
0

HISTORICAL B02 N=100K FUNCTIONAL:
PASS — SOURCE-QUALIFIED

HISTORICAL P03 N=100K INSTRUMENTED:
INCOMPLETE — NO E3/E4

EIGHT TRANSFERRED OBLIGATIONS:
MAPPED

EIGHT TRANSFERRED OBLIGATIONS ACCEPTED:
0 / 8

BASELINE ESTABLISHMENT:
NEW ACQUISITION PREREQUISITE

SOURCE/COMPARATOR LEGITIMACY:
PARTIAL

OBSERVER QUALIFICATION:
BLOCKED

MINIMUM EXECUTION MATRIX:
잠정 ON 12 + 3r + 1 = 13+3r; FULL U; 무조건 OFF 0·조건부 q; 계획 단계 measured full cold 0; 별도 기준선 준비 비용·횟수 미정

UNRESOLVED SAMPLE PARAMETERS:
r, U, q — 모두 미정

RESOURCE/ABORT BUDGET:
REVISION REQUIRED

STATIC PLAN REVIEW READINESS:
READY

EXECUTION READINESS:
NOT AUTHORIZED

N=100K ACQUISITION AUTHORIZATION:
NOT GRANTED

NEW ACQUISITIONS:
0

NEW FULL COLD RUNS:
0

PRODUCT SOURCE MODIFIED:
NO

B03 INSTRUMENTATION MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

ENGINE ADMISSION MODIFIED:
NO

HISTORICAL DATABASES MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY PRE04:
NO

HISTORICAL EVIDENCE:
PRESERVED

T6.6F PHASE B ADMINISTRATIVE CLOSURE:
COMPLETE — EVIDENCE TRANSFERRED

T6.6F QUANTITATIVE EVIDENCE:
INCONCLUSIVE

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

PRE04 REPORT:
docs/t69-pre04-execution-readiness-plan-revision.md

PRE04 EVIDENCE:
docs/benchmarks/t69-pre04/

FINAL VERDICT:
PARTIAL — ESSENTIAL NORMATIVE OR RESOURCE DECISIONS UNRESOLVED

NEXT ACTION:
원 B03를 변경하지 않고 E3·부기 작업을 단계별로 직접 관측할 수 있는지 구현·측정 비참여 검토자가 단일 정적 seam 심사로 판정한다.
```
