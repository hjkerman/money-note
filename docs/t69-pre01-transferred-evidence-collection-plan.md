# T6.9-PRE01 — 이관 증거 수집 계획과 독립 사전심사 패키지

**판정: PARTIAL — EXECUTION PLAN NEEDS SPECIFIC EVIDENCE.** 승인 규범과 원본 B03 source를 확인했고 8개 의무를 모두 수집·검증·중단 계획에 연결했다. 다만 적법한 accepted baseline, 추가 관측기의 직접 단계 귀속, 표본 결합 방식, matched full 비교 경로와 자원 상한 내 실행 가능성은 아직 입증되지 않았다. 이 패키지는 별도 PRE02의 **문서 심사에 제출할 수 있는 상태**이며 실행 준비 PASS나 N=100k 실행 허가가 아니다.

이 세션은 제공된 대화 이력상 B01–B11 구현·개정 적용과 분리된 새 계획 세션이다. 역할은 증거 계획 작성자이며 독립 실행 수용자가 아니다. 외부 개인 신원이나 UI의 reasoning 설정까지 인증했다는 주장은 하지 않는다. 새 벤치마크·cold·N=100k 재시도·제품 import·API 요청·기기 접근은 모두 0회다.

## 1. 현재 승인 상태와 적용 우선순위

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. 예상 HEAD와 일치한다. 작업 트리는 기존 수정·untracked 파일을 포함하며 깨끗하지 않다. 시작 staged 변경은 0개다. [시작 보존 목록](benchmarks/t69-pre01/preservation-before.json)은 기존 추적·비무시 untracked 파일 6,498개의 SHA·크기·mode와 실제 index bytes 및 path/mode/blob/stage 집합의 digest를 기록한다.

[승인 결정](benchmarks/t66f-b11-application/authorization-decision.json), [적용 기록](benchmarks/t66f-b11-application/application-record.json), [책임 지정 보충안](benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json)을 실제 C/B 문서와 대조했다. 원 제안·개정 기록·보충안의 승인 SHA, 현재 두 파일의 적용 후 SHA, 다섯 추가문의 exact bytes가 일치한다. 초안의 개인 기명 요구 대신 승인된 GOV01/GOV02의 역할 책임이 적용되며 REF01은 이동 줄번호 대신 논리 절을 가리킨다. 과거 보충안 파일의 DRAFT 표시는 당시 이력이며 후속 명시 승인과 현재 적용을 무효화하지 않는다.

| 항목 | 현재 상태와 의미 |
| --- | --- |
| B11 개정 | `T66F-B11-TRANSFER-01`, Option 3 및 책임 보충안 승인·적용 확인 |
| 독립 개정 정합성 검토 | [별도 역사 판정](benchmarks/t66f-b11-application-consistency/decision.json) PASS, material finding 0 |
| Phase B 행정 종결 | [별도 재판정](benchmarks/t66f-b11-closure-readjudication/closure-decision.json)에 따라 COMPLETE — EVIDENCE TRANSFERRED |
| Phase B 정량 증거 | INCONCLUSIVE; 다섯 점 비용 grid PARTIAL |
| 이관 증거 수용 | 0/8; 모두 필수 증거 대기 |
| formal T6.6F closure / 최종 T6.9 | NOT AUTHORIZED / BLOCKED |
| 원 B03 계측 정확성 | IR07 CLOSED — 원 source·지원 runtime 범위 |
| B05/B08 | EXPERIMENTAL — NOT ADOPTED |
| R1 사용자 활성화 / production | CLOSED / NOT AUTHORIZED |

규범 원본은 현재 [C §34-B11](t66/c/t66c-delta-sync-protocol.md#34-b11-제한-phase-b-행정-종결과-증거-이관--승인된-경우에만-효력), C §35·§35-T69·I25·§38 및 B §27/29다. 현재 C SHA는 `5d3f03a0e61c6d504cf8efd5de0c8ee446b9c0a0b4a45a367f6d366a4fbf94c9`, B SHA는 `e2d820ba71018414934ad4a9b3667961c209f93fe0b5b5dd2d0a3233ea76b279`다. [규범 참조 목록](benchmarks/t69-pre01/normative-references.json)은 각 측정의 실제 행·문구·파일 SHA를 보존한다. 역사 B10/B11의 이전 줄번호는 현행 위치로 위장하지 않는다.

별도 독립 상세 T6.9 명세 파일은 저장소 문서 목록에서 확인되지 않았다. 현행 C §35-T69가 이관 인수 계약이다. B §27/29의 confirmed-heavy·한 달 hot 대량·initial/full/restore/crash 등 기존 전체 T6.9 감사 범위는 이 8개에 흡수되거나 면제되지 않는다. 이 보고서는 그 명세를 새로 제정하지 않는다.

실행 책임은 **T6.9 구현·측정 워크스트림**, 독립 수용은 **해당 구현·측정 비참여 별도 T6.9 감사 세션**, 최종 승인자는 **프로젝트 소유자**다. 기한은 formal F exit 재심사와 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전이다. 달력 기한 미정은 연장이나 waiver가 아니다. 승인 철회·조건 위반 시 행정 종결 효력 중단과 원 gate 복원 규칙도 유지한다.

## 2. 원 B03 source와 인증 경계

| identity | 확인한 값 |
| --- | --- |
| base commit | `ebcbd54d90eeee194a04b9eea6367f446ee2fd28` |
| base tree | `af2aa70ce6a8cd27c18c134564e31702f0f54f8c` |
| payload SHA-256 | `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8` |
| engine SHA-256 | `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c` |
| archive SHA-256 | `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5` |
| 원 archive | `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz` |
| 지원 runtime | CPython 3.12.3 / backend SQLite 3.45.1 / Flutter 3.47.4 / Dart 3.13.3 / client SQLite 3.53.4 |

archive를 **추출·실행하지 않고** sidecar checksum, metadata 일치, member 중복/경로 안전성, source 899개·9,801,906B의 SHA·길이·mode, context, 기준 Git inventory 2,693개를 검증했다. manifest의 정렬된 entries를 지정 JSON 직렬화로 해시해 payload를 확인했다. archive 내부 `engine_artifact`의 고정 application/isolated_sync/YAML 입력 SHA map을 정적으로 재구성해 engine hash도 확인했다. [source 무결성 기록](benchmarks/t69-pre01/source-integrity.json)이 근거다. 원 후보의 read-only 설정을 WORM으로 표현하지 않는다.

payload는 선택 source 집합, engine은 금융 engine artifact 입력, archive는 포장 파일, runtime/binary는 실행 환경의 identity다. 서로 대체하지 않는다. 현재 dirty tree에는 B05/B08 관련 변경이 있으므로 측정 source로 복사하지 않는다. 미래 실행본은 고정 Git base와 검증된 archive로 별도 task 영역에 재구성하고 원 source와 mode를 전후 대조해야 한다.

원 IR07의 [monitoring 지원 경계](benchmarks/t66f-b03-ir07/monitoring-contract-decision.json)는 유지한다. 안정된 CPython monitoring 환경, 원 소유권·취소·SQL·byte guards가 전제다. 현재 실행 binary·native library와 새 관측기의 지원성은 PRE01에서 인증하지 않았다. B04가 보존한 client SQLite library SHA `0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace`와 실제 향후 로드 library도 대조해야 한다.

다른 source/engine/runtime·Android binary/driver로 얻은 결과는 그 source의 새 주장이다. 별도 채택 승인, exact release/admission, 영향 계측 oracle·구조/provenance·authority fence·durability/legacy 복구 재자격과 그 source 전체 다섯 점 곡선이 필요하다. §23의 compatibility proof 없는 validator/schema 변경에는 full revalidation이 필요하다. 원 B03 8개 결측을 미래 source 결과로 소거할 수 없다. 원 B01–B03 전체 correctness를 material 반증 없이 다시 실행하지 않는다.

## 3. 8개 요구에서 수용 증거까지의 연결

아래 ID는 B11 추적명이다. 원 규범을 대체하지 않는다. 모든 행의 source/runtime은 §2, fixture는 §5, 필수 원자료는 §8, 실패·release 처분은 §9/11을 공통 적용한다. [기계 행렬](benchmarks/t69-pre01/transferred-obligation-matrix.json)은 각 행에 exact 규범, 모든 규모/workload, 계측, 재사용·결측, raw artifacts, 독립 수용, 실패 및 release 의존성을 담는다.

| ID | 현행 exact 근거 | 필수 완료 증거 | 기존/결측과 계획 |
| --- | --- | --- | --- |
| `T35-100K-NC` | C §35-T69 722행; §35 716행 | N100000 no-change 반복의 rows/hash·validation·write bytes, HTTP/RTT, memory, median/p95와 D1–E4 분리 | UNVERIFIED. 기존 B04 상위 점 없음. `REP-N100000-no_change-T0/1/2-ON` |
| `T35-100K-CARD` | 같은 722·716행 | 같은 N의 card D1 정상 rebuild, 실제 accepted generation 전진과 전체 비용 | UNVERIFIED. `REP-N100000-card-T0/1/2-ON` |
| `T35-100K-CASH` | 같은 722·716행 | 같은 N의 cash D1 정상 rebuild와 전체 비용 | UNVERIFIED. `REP-N100000-cash-T0/1/2-ON` |
| `T35-ROWS` | C §35-T69 723행 | 다섯 N×세 정상 workload의 실제 SQL/반환 행·raw/index lookup·query plan 완결 | PARTIAL. 하위 네 N operation/SQL 일부 재사용, SQL read 결측은 `REP-*`에서 직접 보완 |
| `T35-NET` | C §35-T69 724행; §35 714행 | 같은 다섯 N/workload의 method/path·금융/auxiliary·양방향 entity·decoded·base64/JSON·headers·RTT dependency/cache miss와 full 비교 | PARTIAL. B04 entity/요청 자료 재사용, 실제 headers/framing/full 경로는 `REP-*`+`FULL-*` |
| `T35-GZIP` | C §35-T69 725행; §35 714행; B §27 | 같은 source/DB/Context의 full authoritative gzip6, representative/less-repetitive의 network/codec CPU/parse·validation/write | PARTIAL. 과거 offline 20표본은 원 범위만 재사용. `FULL-*`, 별도 `DIV-N10000-*` |
| `I25-E3-100K` | C §35-T69 726행; §36 I25 777·779행 | N100k 세 workload의 E3Verify/Prepare/Commit rows/bytes·SQL·tree/index/pin/CAS/readback, 5개 full counters=0 직접 입증 | UNVERIFIED. N100k 위 9회에 동시 수집. E2·recovery·operation 전체 counter에서 추론 금지 |
| `I25-BOOKKEEPING-100K` | C §35-T69 727행; §16 325행; §38.7 834행 | 같은 정상 D/E의 lease/GC/refcount/root pin/transfer 직접 작업량, hidden graph/history scan 부재·flat P 목록 부재 | UNVERIFIED. 같은 9회에 동시 수집. 별도 maintenance 비용을 normal timer 안에 숨기지 않음 |

수용은 비용의 절대 ms 상한으로 채점하지 않는다. 고정 H/D에서 정상 full history fetch/hash/serialize/write 0회, flat P control 부재, changed leaf/path/affected facts의 bounded 증가 및 측정 완결성을 적용한다. wall-time가 평평하다는 이유만으로 I25를 통과시키지 않는다. 실제 full-N 위반은 귀속 구현 거부·별도 수정/재자격 사유다. 누락은 PARTIAL/UNVERIFIED다.

## 4. 기존 증거의 재사용 판정

[전체 inventory](benchmarks/t69-pre01/existing-evidence-inventory.json)는 N 다섯 점×세 정상 workload/cold×ON/OFF의 40개 cell, 각 원 raw SHA, accepted before/after, stage, collector, 원 fixture digest를 기록한다. `ACCEPTED EXISTING EVIDENCE`도 **지정된 metric 범위의 수용**이며 8개 의무 전체 PASS가 아니다.

| N | B04 정상 세 workload | cold | 판정 |
| ---: | --- | --- | --- |
| 1,000 | 각 ON3·OFF3 | ON1·OFF1 | 실제 동종 byte/비용·기능 완료 재사용; 전체 요구는 PARTIAL |
| 5,000 | 각 ON3·OFF3 | ON1·OFF1 | 같음 |
| 10,000 | 각 ON3·OFF3 | ON1·OFF1 | 같음 |
| 50,000 | 각 ON3·OFF3 | ON1·OFF1 | 같음; cold는 각 두 관측을 사용한 완료 |
| 100,000 | B04 없음 | B04 없음 | MISSING; P03 실패·B02 기능은 별도 역사 분류 |

B04 통제 cohort는 80개/40쌍이다. 이 중 정상 ON36개는 실제 hash sink, primary span, SQL 논리 payload, 단계별 byte key, operation work, accepted/E4, 시간·HTTP entity/요청·HOST RSS 범위에서 재사용한다. 정상 OFF36개는 paired timing·equivalence 범위다. OFF 논리 counter는 null이며 0 비용이 아니다. cold8개는 cold/교란 범위에서만 재사용한다. 최초 1k timeout 교란 등을 포함한 진단 publication26개, 50k prepare/discard stage6개를 정상 accepted 완료 cell에 섞지 않는다.

B04 raw의 `logical_counters`는 `e3Verify/e3Prepare/e3Commit` 등 byte stage를 구분하지만 `work`는 operation 전체 map이다. 두 자료의 scope를 동일시하지 않는다. SQL statement/bind/write 수, D3 object/path read는 SQL 실제 반환 행과 전체 query-plan 증명의 대용이 아니다. `prepare/discard` 시간도 accepted 경로의 E3Verify/Prepare 시간을 대신하지 못한다.

B04 [artifact manifest](benchmarks/t66f-b04/artifacts/) 네 cohort의 backend/client-ON/client-OFF 압축 사본 12개는 현재 실제 파일 SHA가 기록과 같다. 지원 backup API로 보존된 일관 DB라는 역사 기록과 graph/value oracle는 재사용한다. PRE01은 압축 DB를 열거나 새 실행의 complete-store/provenance로 admission하지 않았다.

과거 [다섯 점 grid](benchmarks/t66f-phase-b-final/evidence/five-point-grid.json)와 [원 raw](benchmarks/t66f-phase-b-continuation/evidence/grid/)의 backend 분포 및 offline full gzip6/Brotli4 입력 SHA·길이·20 timing은 원 method에서만 유효하다. 원 full JSON/gzip6는 N 순서대로 649444/20761, 2877441/71847, 5663442/134823, 28103439/648149, 56154440/1288409B다. 현 B03 matched full HTTP·parse/write 비교로 승격하지 않는다. T6.6A의 다른 다양성 fixture gzip568847B도 같은 곡선으로 합치지 않는다.

B02 독립 N100k 기능 PASS는 당시 complete400532 객체, 실제 D→E/E3/E4·delta/restart의 CLOSED 기능 증거다. [당시 raw](benchmarks/t66f-b02-independent/summary.json)에서 terminal HTTP2463.561424초, E3 반환2856.089초, E4 전체 oracle2910.719초다. 전송은900초×3 범위에서 끝났고 후속 local E3/E4는 별도였다. 이 수치나 기능 counter는 원 B03 ON 정량/I25 성공 자료가 아니다. B05/B08/B09 결과는 원 source와 incompatible하며 실험 미채택·admission 범위만 보존한다.

## 5. fixture와 baseline의 사전 적법성

원 B04 재사용 설정은 seed662602·평가일2026-10-05·offset540, current ledger105·다른 table35, 초기 hot87364B/control3178B다. no-change D0, card `ledger_entries.id=1002`, cash `cash_flows.id=101`의 amount UPDATE D1이다. 회차별 card1001/1002/1003원, cash−51/−52/−53원을 사용한다. N label은 ledger 총 N, 전체 authoritative rows는 N+35, archive는 N−105다. H는 실제 hot·관계·policy/control descriptor와 문자열 bytes까지 포함한다. 숫자105만으로 H 전체를 정의하지 않는다.

| N | 역사 initial reachable 객체 | 역사 initial canonical B |
| ---: | ---: | ---: |
| 1,000 | 4,132 | 2,749,721 |
| 5,000 | 20,148 | 13,146,158 |
| 10,000 | 40,170 | 26,160,538 |
| 50,000 | 200,331 | 130,710,592 |
| 100,000 | 400,532 | 261,543,083 |

이는 해당 fixture의 **역사 initial** count다. 정상 mutation 뒤 target 전체 객체와 신규 객체 count는 같지 않다. D0는 admitted base의 exact count, D1은 실제 source/문자열/NS/Target별 independent census를 timer 밖에서 freeze한다. 새 다양성 family의 count는 아직 null이다. 확인하지 않은 leaf/tree count를 400532로 채우지 않는다.

각 실행 전에는 11개 table의 실제 row/value digest, schema/Versions, control/policy/문자열 분포, NS/principal/Context, raw/index/hot/control refs와 Target, complete graph/global index/receipt, accepted current/previous/sequence, owner/auth lineage, native connection 및 generation/data_version 증거가 필요하다. native FK/hash/root·회복 가능성과 원 backend presenters 결과를 독립 대조한다. 모바일 금융 공식을 새로 구현하지 않는다.

**가장 큰 실행 전제는 legal accepted baseline의 미확인이다.** C §5는 물리 backup 복원·서버 cold startup에서 새 epoch와 bootstrap을 요구한다. B04 압축 사본이 있다는 사실만으로 현재 실행에서 옛 NS/accepted pointer/receipt가 유효해지지 않는다. 원 identity를 주입하거나 startup을 우회하거나 complete marker를 만들어서는 안 된다. 기존 complete immutable 객체의 재사용도 fresh NS/observation 및 지원 복구 경로가 맞는지 별도 admission이 필요하다. 원 P03 matched DB 부재를 호스트 전체 N100k 사본 부재의 증명으로 확대하지 않는다.

새 instrumented full cold 성공은 C §18/§35-T69의 독립 MUST가 아니다. 적법한 complete accepted baseline 위에서 원 B03 정상 ON 비용을 모을 수 있다. 그러나 그런 경로가 없으면 **수집 차단**이다. 현재 계획에는 빈 store 초기화용 cold나 OFF cold 뒤 ON 정상으로 전환하는 acquisition을 포함하지 않는다. 새 cold가 필요하면 기존 NO-GO를 유지한 채 별도 계획·명시 승인으로만 처분한다.

## 6. P03 N100k 실패와 재발 방지

[역사 분석](benchmarks/t69-pre01/historical-100k-analysis.json)은 [원 full-analysis](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json), 실제 결과·request trace·계측 SHA, [P05 복구/적법성 기록](benchmarks/t66f-b03-ic01-p05/evidence/recovery-and-eligibility.json)에 연결한다.

- 실제 오류는 `AcquisitionFailure(OBSERVATION_EXPIRED,new_observation)`이다. 2699.957907초,397146/400532객체에서 중단됐고3386개가 남았다. 세 Available 관측은 각각900초였고 마지막 만료 뒤 client 한도가 소진됐다. accepted before/after는 null, E3/E4 미완료다.
- 관측 수명 안의 취득 완료 실패가 직접 원인이다. 원 분석은 외부 실험 강제 종료 없음, resource guard 실패 없음, product correctness failure 미재현으로 기록한다. instrumentation 단독 원인과 추가 timing observer의 순수 비용은 입증되지 않았다. source는 당시 IC01/P02→P03이며 최종 IR07 payload가 아니다.
- backend handler 합1886.414804612초·process CPU1883.257226036초, client SQL API380.069584초·row callback 하한23.54858초가 관측됐다. backend 처리 비중이 크다. SQL에 callback이 포함되고 handler는 HTTP 대기와 겹치므로 합산해 총시간 분해를 만들지 않는다. 순수 network/parser/hash/observer CPU 비용은 미분리다.
- 원 backend는 당시 임시 sandbox 종료에서 삭제됐고 client는 후속 재부팅 뒤 알려진 경로에서 unavailable이다. 남은 Target/fixture JSON은 원 matched DB 사본이 아니다. 원 실패의 진행·비용·만료 증거만 재사용할 수 있고 matched tail이나 성공 cell은 만들 수 없다.

[B04 NO-GO](benchmarks/t66f-b04/fullscale-decision.json)의 최종 원 B03 50k ON은 full cold1573.537722초, transfer1399.633084초였다. backend953.533246초 안에 admission285.69·resolution260.03·terminal HTTP290.76초 등의 중첩 경계가 있다. 역사와 동일 per-object/phase mix라는 단순 진단조차 100k에 약2798.36초여서 세 최대 window2700초보다 길었다. 이 값은 **새 비용 예상치가 아니라 역사 NO-GO 근거**다. 50k→100k 외삽으로 성공·실패를 새로 판정하지 않는다.

향후 고비용 시작 전에는 exact source/graph/phase, legal baseline, 완전한 계측, 남은 허용 window·terminal 여유와 자원 상한을 입증해야 한다. 그 근거가 없으면 시작하지 않는다. 첫 no-change 실패·counter 누락·자원 초과·normal full recovery가 나오면 후속 card/cash·상위 N으로 자동 진행하지 않는다. 새 cold가 별도 제안되더라도 낙관적 잔여 작업의 하한이 남은 허용 window를 넘는 명백한 불가능 조건에서는 중단해야 한다. timeout·TTL·retries·hardware 증설은 이 계획의 해결책이 아니다.

## 7. 최소 수집 행렬과 조건부 실행 순서

[실행 계획 JSON](benchmarks/t69-pre01/proposed-execution-plan.json)은 개별 run ID·목적·N/H/D·source/runtime·ON/OFF·incremental 상태·fixture 검증·expected count 규칙·metric·artifact·자원·lease·runtime/storage cap·abort·필수/조건부를 지정한다. 실행 launcher는 만들지 않았다. 아직 미제출인 runner/facade의 command/SHA를 있는 것으로 발명하지 않는다.

원 규범은 숫자 H/D·반복 수·warmup 수·p95 estimator를 정하지 않는다. 아래 n3는 B04와의 비교를 위해 선택한 **실험 설정**이며 새 binding 최소 표본 수가 아니다. 아직 실행 가능한 단일 최솟값을 증명한 것은 아니며, 기존 raw를 최대한 재사용하는 조건부 최소안이다.

| 계획 단위 | 규모·표본 | 새 정상 ON | 목적·공유 |
| --- | --- | ---: | --- |
| `REP-N{N}-{workload}-T0-ON` | 하위 네 N, 세 workload 각1 | 12 | 기존 n3 시간/byte를 재사용하고 SQL/NET·단계 결측만 보완 |
| `REP-N100000-{workload}-T{0,1,2}-ON` | N100k, 세 workload 각3 | 9 | 세 T35-100K와 두 I25를 **동일한 실제 accepted 정상 실행**에서 수집 |
| `DIV-N10000-{workload}-T{0,1,2}-ON` | 별도 다양성10k, 세 workload 각3 | 9 | representative10k와 같은 source/규모·고정 H에서 문자열 영향 비교 |
| `FULL-*` | 위30개 각 Target/input에 대응 | segmented 실행 아님 | full authoritative build·gzip6·identity/gzip HTTP 각1회·full parse/validation/write |
| `*-OFF` | 위 ON과 동일 Target·이전 상대 sequence | 조건부30 | 새 관측기 교란을 기존 B04로 한정할 수 없으면 생략 불가 |

기본안은 정상 ON30개, matched full 비교30단위(실제 identity/gzip HTTP 응답60개), 조건부 OFF30개다. I25만을 위한 독립 full-N acquisition은0, 새 full cold도0이다. ON/OFF 대조는 같은 Target를 한 번 생성하여 두 admitted client에 전달하며 generation ON 자체를 ON/OFF pair라고 부르지 않는다. mode별 local UUID는 독립 발급하므로 Target·상대 sequence·실제 값과 bytes를 대조한다.

실행 순서는 representative N오름차순, 각 trial의 no-change→card→cash다. 선택된 ON/OFF와 matched FULL은 같은 불변 Target/input에서 완료하고 다음 mutation으로 간다. mode 순서는 scale/trial별 반전, 양쪽 operation마다 같은 설정의 fresh HTTP pool을 사용한다. 초기 cold 이후 warmup이라고 부를 작업을 몰래 추가하지 않는다. warmup은0으로 계획하고 이를 공개한다. 변경된 cache/OS/JIT·TLS handshake·같은 process RSS 공유의 한계를 기록한다.

기존 lower-N n3 분포와 신규 n1 read/network 결측을 **각 metric별 다른 sample 집합**으로 제시하는 것이 반복 요구에 맞는지는 PRE02의 명시 심사 항목이다. n1을 n3로 부풀리거나 새 단계의 p95로 쓰지 않는다. PRE02가 결측 metric도 n3를 요구하면 lower-N ON24개와 matched FULL24개 및 필요한 OFF24개의 **수정 계획을 먼저 확정**해야 한다. 자동 실행·예산 확대는 없다. 기존 norm에 mandatory ON/OFF run 수는 없지만 새 관측기가 교란을 바꾸는 경우 qualified matched OFF를 생략하지 않는다.

다양성 family는 `less-repetitive-10k-v1`로 고정한다. archive ledger의 `title/usage_place`만 PK/column/block·seed662602로 domain-separated SHA256 hex stream을 만들어 원 UTF8 byte 길이만큼 자른 ASCII로 대체한다. NULL/빈 값, current105행, 다른 table, 금액/key/관계/timestamp와 hot/policy working-set 입력은 유지한다. NS/Target·내용주소 descriptor는 원 규칙으로 재생성하고 실제 hot/control 크기를 대조한다. 상세 결정식은 JSON에 있다. 이는 **향후 합성 fixture 입력 계획**이며 실제 데이터 변경은0회다. 시작 전 length histogram·distinct/repetition·행수/전체 SHA·leaf 분포·금융 필드 동등성을 freeze한다. 새로운 graph count는 실측 전 null이다.

C §35-T69는 다양성 규모/분포의 사전 고정을 요구하며 독립 다섯 점 다양성 곡선을 명시하지 않는다. 이 계획은10k 별도 matched 비교를 선택한다. 원 representative 다섯 점을 대체하지 않는다. PRE02가 더 넓은 다양성 범위가 구속된다고 판단하면 반려·확장해야 하며 그 판단을 요구 면제로 바꾸지 않는다.

FULL 비교는 같은 DB read-view/Context의 원 backend authoritative presenter/serializer가 만든 **실제 full 응답**을 SHA로 고정한다. test-only TLS facade에서 그 identity entity와 gzip6 entity를 실제 전송하고 원 full parser/validator 및 별도 폐기용 legacy durable 저장의 경계를 잰다. codec level6·compile/runtime 버전·mtime·입출력 SHA/길이·CPU/wall, 압축 해제·parse·validation·write를 분리한다. response 생성/저장·wire replay·compression의 시간도 각각 구분한다. 미구현 facade/runner는 독립 자격 대상이며 production 압축 채택이나 프로토콜 변경이 아니다. offline compression만 확보되면 wire/headers/RTT 열은 계속 결측이다.

## 8. 필수 계측·원자료·독립 수용 방식

[계측 계약](benchmarks/t69-pre01/instrumentation-contract.json)의 M01은 아직 구현·인증되지 않았다. 원 IR07 계측이 정확하다는 사실만으로 이 추가 관측기의 지원성을 주장하지 않는다.

| 경계 | 반드시 직접 남길 관측과 제한 |
| --- | --- |
| D1/D2 generation | capture/finalize/commit의 ON hash/primary/SQL·CPU/wall; oracle/seed 준비는 timer 밖 |
| D3 request | auth/admission/resolution/serialization/terminal 및 request serial·stage·반환 rows·object/path reads; 금융/auxiliary 분리 |
| bookkeeping | lease 생성/renew/release·root pin·GC/refcount/typed edge의 실제 SQL·returned rows·방문 작업량; table cardinality/query plan과 callsite map |
| E1/E2 | 실제 신규 저장 payload, raw/index lookup, strict wire/C1 bytes, E2 inclusive wall·HTTP dependency/cache |
| E3Verify/Prepare/Commit/readback | 단계별 hash/primary/SQL rows·bytes·tree/index/pin/CAS/readback 및 `full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds` 직접 counter |
| E4 | 실제 accepted read의 ledger/cash/hot 값·provenance 및 비용; standalone full oracle는 별도 timer |
| FULL/gzip | 실제 input/codec/압축 bytes·HTTP headers/entity/decoded/framing·codec/parse/validation/write·HOST RSS |

hash는 실제 sink의 domain/NUL·반복·실패/skip 포함 입력이다. primary는 submitted/completed/failed span이며 structured visits에 row 크기를 곱하지 않는다. Python JSON 완료와 Dart 전체 C1 완료를 구별한다. SQL은 NEW TEXT UTF8/BLOB의 attempted/effective/committed/rollback과 scalar/NULL/row event를 분리한다. UPDATE는 NEW row 전체, DELETE 신규 payload0이다. SQL API bind, DB 증가, WAL, 물리 I/O/NAND를 이 bytes의 대용으로 쓰지 않는다.

SQL read 계수는 실제 delegate cursor의 fetch/iteration 또는 native ResultSet 반환 event를 중복 없이 관측하는 별도 bounded observer 설계를 요구한다. statement 수·DML row event만으로 채우지 않는다. EXPLAIN은 같은 immutable DB state에서 timer 밖 별도로 수집하며 returned rows를 모든 VM/pager 방문 행으로 부르지 않는다. 명시 maintenance/독립 oracle의 O(N)와 refresh 내 O(N)를 구분한다. 정상 active refresh에 full graph/history scan을 숨기면 실패다.

**E3의 operation 전체 work map을 E2와 나눠 빼서 직접 stage counter로 만들지 않는다.** 기존 stage byte key, prepare/discard 진단, operation 전체 counter는 각각 원 범위만 사용한다. 원 source에서 필요한 직접 관측 seam을 안전하게 얻을 수 없다면 해당 원 source 증거는 차단이다. 제품/B03 계측 source를 수정하고 원 IR07 인증이 그대로 적용된다고 주장하지 않는다. absent key·미지원·collector 미완료를 기본0으로 만들지 않는다.

원 `store_publication`의 최종 `finalAuthorityFence(); _db.execute('COMMIT');` 순서를 보존한다. 그 사이에 새 await/callback/hook/SQL observer callout/스케줄링을 추가하지 않는다. private native connection·동기 COMMIT·readback을 그대로 사용한다. 이 경계를 침범해야만 얻을 수 있는 관측은 수용하지 않는다.

각 timing은 interval ID/parent/start/end/clock와 inclusive 여부를 기록한다. AppState wall·HTTP body wait·backend handler/D3·SQL API·row callback은 중첩이므로 더하지 않는다. 동일 clock의 완전한 interval union을 증명한 경우만 exclusive 차집합을 제시한다. CPU와 wall, 요청 실패 send와 성공 body, E4 포함 여부도 구분한다. median·nearest-rank p95·IQR 방식과 n/warmup을 공개한다. n3 p95는 표본 최대값이며 모집단 tail 보증이 아니다.

HTTP headers는 실제 serializer가 송수신한 application HTTP bytes로 기록한다. base64 token/decoded canonical/JSON framing은 실제 captured body에 분해·재결합 대조한다. `4×ceil(decoded/3)` 산술만으로 채우지 않는다. HTTP application bytes·TLS records·TCP packets는 서로 다른 지표다. 전체 암호화 wire를 관측하지 않았다면 그 사실을 명시한다.

모든 run은 command/cwd/exit/time, source/runtime/binary/runner SHA, fixture/Context/Target, accepted before/after, stage completion, raw counters/samples/HTTP/실패·취소, resource trace를 남긴다. backend/client 일관 SQLite 사본은 지원 backup API로 보존한다. 압축·비압축 SHA/크기·mode, 11-table 값 digest·FK/hash/root/complete graph 및 E4 비교가 완료되기 전 유일 matched 자료를 정리하지 않는다.

독립 수용자는 원자료를 읽어 source·input·stage 경계와 sample 집합을 다시 연결하고 graph/11-table/native 결과와 실제 backend presenter 값을 대조한다. 새 모바일 canonical 금융 엔진을 만들지 않는다. OFF/backend-only/ASGI/prepare-discard/실패·취소·다른 source의 기능 PASS는 정상 ON 완료 증거가 아니다. 8개 전체가 완결되기 전에는 `T6.9-E EVIDENCE ACCEPTED`를 발급하지 않는다.

## 9. Gate A–E, 자원·runtime 상한과 abort

| gate | 실행 전 증거 | PRE01 상태 |
| --- | --- | --- |
| A — source/artifact | 원 archive·runtime/binary·fixture·instrumentation·release 일치 및 complete accepted provenance | archive VERIFIED; 나머지 PARTIAL |
| B — reuse compatibility | 각 metric source/input/scale/workload/stage·원 raw/manifest 대조 | inventory 확보; 새 결합은 독립 심사 대기 |
| C — resources | 실제 disk/RSS/시간·lease 한도와 필요한 peak·예약 여유 | NOT ESTABLISHED |
| D — small-scale validity | IR07 원 계측 유효성 + 새 M01/비교 facade의 별도 bounded qualification | 원 IR07 CLOSED, 추가 관측기 미인증 |
| E — N100k authorization | owner가 exact plan SHA·run IDs·상한·최대 attempts·abort를 별도 명시 승인 | NOT GRANTED |

모든 gate는 실행 역할의 주장만으로 통과하지 않는다. PRE02도 문서 계획 심사이며 원자료가 없는 baseline/M01/resource PASS를 대신 발급할 수 없다. 작은 qualification조차 이 PRE01에서 실행하지 않았으며 후속 별도 bounded 허가가 필요하다. N100k는 A–D 독립 admission과 **별도 E 승인 모두** 없으면 실행할 수 없다. 하위 N도 새 benchmark GO가 필요하다.

[자원·중단 예산](benchmarks/t69-pre01/resource-and-abort-budget.json)의 다음 수치는 **미승인 안전 상한 제안**이다. 성능 예상치·완주 보증·새 latency 합격선이 아니다.

| 항목 | 제안 상한/진입 조건 |
| --- | --- |
| normal sync 1회 |120초 |
| FULL 비교 1단위(identity/gzip·codec/parse/write 전체) |300초 |
| scale/family baseline admission |1800초; 새 cold 제외 |
| 한 scale cohort / 전체 campaign |3600초 /14400초, 먼저 도래한 상한에서 중단 |
| task scratch·증거·DB·build 전체 추가 할당 |10GiB 이내 |
| 최소 free disk / 시작 free disk |실행 중10GiB / 시작20GiB 이상 및 실제 peak 계산 충족 |
| 자가 process-group RSS / 시작 MemAvailable |8GiB 이하 /10GiB 이상 및 host 예약 확인 |
| resource sample |1초 간격, 관측 간 peak 누락 한계 공개 |
| 전체 campaign attempt |최대1; 실패 campaign 자동 재시도0 |
| observation |TTL≤900초, client attempts3·observations3·principal Available4 각각 유지 |

RSS8GiB·free disk10GiB는 역사 B04가 쓴 guard를 계획 상한으로 재사용한 것이다. 추가 runtime·scratch cap은 PRE01의 보수적 제안이며 기존 규범 수치가 아니다. 이 cap 안에서 실행이 가능하다는 근거가 없으므로 Gate C를 통과시키지 않았다. 자원 확대를 전제하지 않는다.

B04 50k의 sampled process-group peak는2951401472B, backend/client 두 사본의 비압축 DB 합은1017720832B였다. B02 독립100k 전체 cold/delta/restart process-tree peak5772578816B·outer5408.551164초는 다른 source/계측·작업 범위다. 새 정상 delta/full comparator의 peak·실행비용 추정치로 전용하지 않는다. 현재 host의 disk/memory 읽기 전용 순간값은 [host snapshot](benchmarks/t69-pre01/host-readonly-snapshot.json)에 있으며 미래 자원 예약이나 지원 binary 인증이 아니다.

필요 disk는 backend+admitted client 각 사본+journal/WAL/temp+일관 backup+gzip/raw+재구성/build의 실제 크기와 상한을 합산한다. `free ≥ 예상 추가 peak + 보존 여유10GiB` 및 task allocation≤10GiB를 동시에 만족해야 한다. canonical261543083B는 이 전체 peak가 아니다. 모르는 항목을0으로 두거나50k DB를 두 배 해 N100k 예산을 확정하지 않는다. 새 N100k 시간·storage 예상치는 **null/근거 부족**이다.

중단 규칙은 다음과 같다.

1. source/runtime/fixture/Context/NS/Target·admission drift, 미지원 monitoring, collector pending/미종료·stage 미귀속이면 시작하지 않거나 즉시 중단한다.
2. 정상 full-N counter>0, full history/graph query·flat P 목록, authority/FK/hash/root/readback 오류면 해당 cell을 거부하고 상위 N을 중단한다. 숫자 null과 실제 위반을 구별한다.
3. 최초 no-change 또는 ON/OFF 동등성 실패면 card/cash를 자동 진행하지 않는다. 같은 실패의 campaign 재시도는 하지 않는다.
4. 기존 lease/attempt 한도 소진은 terminal failure다. 네 번째 observation, 시간 조작, TTL/timeout/retry 연장으로 성공을 만들지 않는다. 2700초는 세 최대 window의 산술일 뿐 재인가 gap을 포함한 보장 wall이 아니다. 완전 취득 뒤 local E3/E4는 transfer TTL과 별개다.
5. 자원·task time cap에서는 자가 process group에 cooperative cancel, cleanup 최대30초 뒤 필요 시 자기 group만 종료한다. native 완료·DB 일관성이 불확실하면 보존·INCOMPLETE 처리한다. COMMIT 뒤 readback 실패는 rollback했다고 가정하지 않는다.
6. 종료·취소·불완전 counter·raw/backup을 보존하고 차단 근거를 실행 역할이 owner에게 보고한다. 자동 waiver·정량 수용·기한 연장은 없다.

경쟁 대형 작업은 시작 차단 조건이지 다른 세션 process를 종료할 근거가 아니다. 격리 synthetic loopback TLS ephemeral endpoint만 후속 계획에서 사용하며18080/production DB·Snapshot·`.env`를 입력으로 사용하지 않는다. 정상 개발 API 정책과 기존 검증 harness의 격리 포트를 구별한다.

적법 baseline이나 원 source 관측 경로가 확보되지 않으면 선택 가능한 후속 결정은 차단 유지, source 변경 없는 별도 bounded 증거 자격 조사, 별도 cold 계획의 명시 심사, 또는 별도 규범 변경 심사다. 어느 것도 PRE01이 승인하지 않는다. 다른 source 최적화·증설·규칙 완화로 원 B03 결측을 조용히 대체하지 않는다.

## 10. PRE02 독립 심사와 아직 필요한 구체적 증거

[PRE02 checklist](benchmarks/t69-pre01/independent-prereview-checklist.json)의 모든 심사 결과는 PENDING이다. PRE01 작성자가 자신의 실행 readiness를 PASS로 만들지 않았다. PRE02에는 이 보고서, 필수6개 JSON, 규범 exact 발췌/SHA, source integrity, 재사용 inventory/raw 연결, P03 분석, 계측 계약, 자원·abort, 입력/보존/산출물 manifest를 함께 제공한다.

별도 비참여 심사자는 특히 다음 미해결 사항을 판단해야 한다.

- 각 규모/family/mode의 legal complete accepted baseline과 새 epoch/같은 연결 provenance 경로가 실제로 가능한가. B04 backup의 존재와 원 P03 사본의 부재를 정확히 구별했는가.
- 원 source/guard를 바꾸지 않고 SQL 반환 행·부기·E3 full counter를 직접 귀속할 수 있는 M01 및 matched full comparator 설계·qualification 근거가 있는가.
- lower-N 기존 n3+결측 n1 보완과 다양성10k 단일 별도 family가 해당 요구를 충족하는가. 미충족이면 어떤 추가 run과 예산이 필요한가.
- 실제 peak·시간 자료가 제안 cap 내 source-qualified 수집을 뒷받침하는가. 현재 여유 자원만으로 feasibility를 인정하지 않았는가.

실제 실행 전에는 runner/facade·명령/cwd/binary·source locks·fixture 및 admitted baseline manifest와 자원 증거의 exact SHA까지 확정해야 한다. 그 전에는 command를 추정해 campaign launcher를 만들지 않는다. 이 미해결 상태 때문에 PRE01 판정은 PASS 대신 **PARTIAL**이다. essential 승인 규범과 원 source는 확보돼 있어 BLOCKED — NORMATIVE OR SOURCE PREREQUISITE MISSING은 아니다. 금지된 실행이나 규칙 완화를 계획의 성공 경로로 넣지 않았으므로 FAIL 판정도 발급하지 않는다.

## 11. 실기기·release 경계와 보존 검증

host에서 수집할 항목은 §35/I25의 synthetic D/E 비용·논리 bytes/rows·HTTP/framing·full gzip 및 정상 bookkeeping이다. 실제 Android의 native driver/PRAGMA/VFS·flush·I/O 오류·process death/power-loss·previous recovery는 C §26/§38.8의 별도 증거다. 단말 latency·heap/LMK·UFS·전력/배터리/thermal은 기존 post-T6.6 기기 성능 단계다. HOST RSS·loopback·SIGKILL·APK build로 대체하지 않는다.

PRE01은 Android SDK/Emulator 설치·KVM membership 변경·ADB·Galaxy S23 FE 연결/검사·기기 성능 측정을 하지 않았다. Real-Device Gate는 DEFERRED다. host 의무를 device 자료로 대체하도록 허용된 개정도 확인되지 않았다.

8개 독립 수용 외에도 C §26/31–34, I23/I24, §38.8–11의 Android durability, 큰 restore/MW·receipt/Apply(B,J), legacy/migration/rollback, 30개 backup/artifact·pin/GC·storage exhaustion과 whole-F 통합 proof는 남는다. T6.9-E는 필요조건이며 R1/기기/rollout/deployment 충분조건이 아니다. R1 활성화 CLOSED, production NOT AUTHORIZED를 유지한다. 행정 종결은 T6.7/8 cleanup·legacy full consumer/store 제거의 자동 entry도 아니다.

PRE01이 쓴 경로는 이 보고서와 `docs/benchmarks/t69-pre01/`뿐이다. source/protocol/guard/allowlist/release artifact, 기존 staged·unstaged·untracked 및 frozen 후보·역사 증거는 쓰지 않았다. [종료 보존 검증](benchmarks/t69-pre01/preservation-after.json)은 시작6,498개 파일의 SHA/크기/mode와 HEAD/branch/index를 대조한다. ignored runtime/production 전체 파일을 전수 검증했다는 주장은 아니다. [산출물 manifest](benchmarks/t69-pre01/evidence-manifest.json)는 이번 보고서/JSON/정적 준비 도구만 추적한다.

문서 전용 정적 검증 190개가 통과했다. 검증은 JSON 구조·8개 추적·exact 승인/규범·archive/source hash·기존 raw/압축 사본 hash·run 수·cap·참조·보존에 한정했다. 처음에는 검증 도구가 아직 생성하지 않은 종료 manifest 링크를 먼저 확인해 중단했으며, 생성 후 확인하도록 순서를 고쳤다. 이 도구 사건과 원인은 [기록](benchmarks/t69-pre01/tooling-incidents.json)에 보존했다. npm/backend/Flutter build·시험은 planning-only/no-execution 요청에 따라 실행하지 않았다. closed correctness를 반복하거나 제품을 실행하지 않았다. 첫 sandbox 시작은 bwrap loopback 초기화 오류로 실패했고 승인 검토된 정적 읽기/자기 문서 작성 경로로 진행했다. 자동 승인 거절은 없었다.

대형 임시 실험 산출물 정리는 NOT APPLICABLE, 삭제·회수0B다. manifest가 참조하는 과거 증거와 유일 matched DB, 활성 DB/WAL/SHM, 기존 cache를 정리하지 않았다. 후속 실험에서도 검증된 task-owned·비활성·처분 가능한 파일만 각 실험 경계에서 정리하고 삭제 receipt를 보존해야 한다.

## 12. 단일 다음 행동과 최종 판정

**PARTIAL — EXECUTION PLAN NEEDS SPECIFIC EVIDENCE.** 독립 문서 검토용 패키지는 준비됐고 실제 실행은 계속 차단돼 있다.

다음 행동: **구현·측정에 참여하지 않은 별도 PRE02 감사 세션에 이 PRE01 패키지를 제출하여 baseline 적법성·관측기 귀속·자원 상한의 미해결 조건과 실행 계획을 독립 심사받는다.**

```text
T6.9-PRE01 TRANSFERRED EVIDENCE COLLECTION PLAN:
PARTIAL

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

APPROVED B11 AMENDMENT:
VERIFIED

INDEPENDENT B11 CONSISTENCY REVIEW:
PASS — HISTORICAL

T6.6F PHASE B ADMINISTRATIVE CLOSURE:
COMPLETE — EVIDENCE TRANSFERRED

T6.6F QUANTITATIVE EVIDENCE:
INCONCLUSIVE

FORMAL T6.6F CLOSURE:
NOT AUTHORIZED

TRANSFERRED OBLIGATIONS:
8

TRANSFERRED OBLIGATIONS ACCEPTED:
0 / 8 — 새 권위 증거 없음

ORIGINAL B03 SOURCE:
VERIFIED

EXISTING EVIDENCE REUSE:
B04 하위 네 N 정상 ON36·OFF36 및 cold8의 원 metric만 재사용; 진단/과거 offline·B02 기능은 별도 범위

MISSING §35 EVIDENCE:
T35-100K-NC, T35-100K-CARD, T35-100K-CASH, T35-ROWS, T35-NET, T35-GZIP

MISSING I25 EVIDENCE:
I25-E3-100K, I25-BOOKKEEPING-100K

FIVE-POINT COST GRID:
PARTIAL

N=100K HISTORICAL FAILURE:
역사 IC01/P02→P03에서 OBSERVATION_EXPIRED; 2699.957907초·397146/400532·세 관측 만료·E3/E4 미완료; resource guard 실패 없음·정확성 실패 미재현

N=100K CURRENT EXECUTION FEASIBILITY:
NOT ESTABLISHED

PROPOSED REQUIRED RUNS:
대표 lower-N ON12 + N100k ON9 + 별도 다양성10k ON9; matched FULL30단위(HTTP60응답), 조건부 OFF30; lower-N n3 요구 시 추가ON24/FULL24·필요OFF24 계획 재심사

REQUIRED MEASUREMENT INSTRUMENTATION:
원 IR07 B03 ON + SQL read/HTTP framing·E3/부기 직접 귀속 M01 별도 자격 필요; 원 guard→동기 COMMIT 유지

RESOURCE AND ABORT BUDGET:
미승인 cap 제안: normal120초/FULL300초, scale3600초/전체14400초, scratch10GiB·RSS8GiB·free disk10GiB, campaign1회; lease900초/attempts3/observations3/Available4 유지

INDEPENDENT PRE-EXECUTION REVIEW:
READY — PRE02 문서 심사용; 실제 실행 readiness 미인증

N=100K EXECUTION AUTHORIZATION:
NOT GRANTED

NEW FULL COLD RUNS:
0

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

ENGINE ADMISSION MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY PRE01:
NO

HISTORICAL EVIDENCE:
PRESERVED

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

PLAN REPORT:
docs/t69-pre01-transferred-evidence-collection-plan.md

EVIDENCE DIRECTORY:
docs/benchmarks/t69-pre01/

FINAL VERDICT:
PARTIAL — EXECUTION PLAN NEEDS SPECIFIC EVIDENCE

NEXT ACTION:
구현·측정에 참여하지 않은 별도 PRE02 감사 세션에 이 PRE01 패키지를 제출하여 baseline 적법성·관측기 귀속·자원 상한의 미해결 조건과 실행 계획을 독립 심사받는다.
```
