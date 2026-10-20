# T6.6F-B02-A01 한정 교정 — 구현·검증 진행 기록

이 문서는 구현자 기록이며 독립 감사 PASS가 아니다. 기존 조사·실패 보고서는 수정하지 않는다.
최종 판정과 실행 결과는 아래의 검증 갱신 절 및 새 evidence를 기준으로 한다.

## 01. 시작 상태와 보존

HEAD/main/origin/main/실제 remote main은 `6282c1c3577c42bba9382d786745d583a5d88236`이었다.
기존 B02 `app_state.dart`, `fetch.dart`, `store.dart` 변경 및 미추적 구현·조사·테스트가 존재했다.
index는 비어 있었고 보존했다. reset/restore/stash/clean/branch 변경은 하지 않았다.
[최초 inventory](benchmarks/t66f-b02-a01-correction/initial-state.json)는 기존 1,549개 파일의 SHA와
logical index/staged diff를 기록한다. 원 dirty diff와 교정 전 fetch/transfer를 gzip으로 별도 보존했다.

## 02. 원 조사와 병목

[원 조사](t66f-b02-a01-cold-acquisition-investigation.md)의 실제 50k는 고정900초 observation
3회를 소진하고 35,496개 객체만 저장했다. packet당 평균 약4.721개였다. E2는 검증된 부모의
나머지 child references를64개 임시 map에서 버리고 DFS callback마다 flush했으며,
D3c는 같은 packet의 각 path에서 공통 prefix를 다시 load/hash/C1/typed 검증했다.
E1 자체가 전체 시간의 주원인이라는 증거는 없었다. E1/E3/E4 추가 재설계는 범위 밖이다.

## 03. 제품 변경 범위와 기본값

기존 B02의 explicit `FetchLimits.largeGraphVerification` 및 E1 bounded staged batch를 재사용한다.
A01 제품 변경은 `mobile/lib/src/segmented/fetch.dart`, `backend/isolated_sync/transfer.py`와
사용자가 승인한 exact artifact 호환 갱신뿐이다. AppState/store의 기존 미커밋 B02 bytes는 보존한다.
원 protocol·C1·graph verifier·transport·E3/E4 제품 소스는 변경하지 않는다.

기본 E2는100,000 objects/200,000 edges, 기본 E1 metadata는32MiB 그대로다.
explicit host 검증 profile만500,000 objects/1,000,000 edges/384MiB metadata다.
object64MiB/payload512MiB/manifest8MiB/page262,144/stages128/chunk1MiB/path512/C1 depth128/
request3회/observation3회/lease900초는 그대로다. manifest가 profile을 고를 수 없다.
정상 startup·금융 read/write·Offline 경로에서 profile을 자동 선택하지 않는다.

## 04. Cold packet과 event loop

기존 frontier 내 cold branch만 parent-derived child cursor를 유지한다. 부모 bytes의 검증이 끝난
참조만 사용하며64개/1MiB packet 안에서 아직 필요한 eligible paths를 채운다. cursor는 payload를
보관하지 않고 path와 typed child references만 가진다. 깊이512×wave64의 명시적 상한을 둔다.
넘치면 fail-closed다. complete graph 검증은 기존 `verifyAcquisitionGraph` 한 곳에서 수행한다.
다운로드·progress의 중복을 durable indexed staging lookup과 최대64개 progress로 막는다.
packet이 byte cap에 걸린 경우 cursor를 되돌려 sibling을 잃지 않는다.

64개 work step 또는1MiB 처리 후 event loop에 협력적으로 제어를 돌리고 전후 cancellation/session을
검사한다. 유효한 accepted provenance가 있는 warm delta는 기존 branch를 유지한다. E3의 최종
authority guard→COMMIT에는 await를 추가하지 않았다. 새 ticket/authority owner는 없다.

## 05. D3c request-local typed prefix

원 authenticated lookup 뒤 동일 private BEGIN IMMEDIATE transaction에서 만든 resolver만 cache를
쓴다. path component tuple·Ref hash/bytes·kinds·table·descriptor height/count/min/max·root·Patricia
prefix/count/parent_count를 key로 사용한다. request의 Target/NS/versions/connection은 고정이다.
검증에 성공한 nonterminal prefix의 typed child map만 보관하며 terminal object는 매번 원 strict
hash/C1/type 검증을 한다. hash-only/string-prefix 승인이나 응답 object cache가 아니다.

상한은 기존64 items×512 path의32,768 entries 및 canonical metadata charge1MiB이며 finite LRU다.
상한 밖 metadata는 원 검증으로 fallback한다. 이 charge는 Python heap 측정치와 같지 않다.
처음 검증 실패한 metadata를 성공 entry로 기록하지 않는다. transaction loss/local write 시
reject/clear하고, 성공·오류·취소 모두 finally에서 terminal guard/DB close 전에 clear한다.
global/persistent/cross-request·principal·observation cache는 없다.

원 credential/lease/actual DB identity/permit/quota/worker 취소/최종 응답 guard는 그대로다.
새 migration, production SQLite user_version 변경, response wire 변경은 없다.

## 06. Exact artifact와 source lock 승인

사용자는 현재 engine artifact 갱신과 **두 exact hash만** 유지하는 최소 호환 목록을 명시적으로 승인했다.
과거 engine은 `f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d`,
현재 engine은 `afe26b70856b5a3fa06477641d91e8e1784e9184906281843f0a39a9c99cbdf5`다.
engine source manifest에서 `isolated_sync/transfer.py`만 달라졌고 raw/projection/policy bytes와 versions는
완전히 동일하다. 다른 engine hash는 계속 거부한다. 현재 specimen/mobile asset만 새 bytes를 가지며
과거 artifact는 gzip으로 보존했고 frozen golden은 변경하지 않았다.
[검토 기록](benchmarks/t66f-b02-a01-correction/artifact-review.json).

현재 build의 engine artifact identity가 달라지므로 새 Target의 context/sync_root가 이전 build와
같다고 주장하지 않는다. 전후 resolver 비교는 **동일한 현재 Target/request** 아래에서만 수행했다.
변경된 build identity를 Snapshot v7 fingerprint로 대체하거나 과거 golden에 소급 적용하지 않는다.

기존 SHA failures는 source 변경 감지다. `protected-source.json`의 원 기대값은 변경하지 않았다.
기존 E4 seam 복원 방식처럼 검토된 B02/A01 explicit-profile 부분만 제거하면 fetch의 과거 SHA
`a1e6b4b549dcb5a11d5e0cabcb7806ff42eb831f4192c40b353a103698721253`가 정확히 복원된다.
AppState도 optional profile 인자/전달만 원대로 복원한 뒤 기존 E4 isolation 기대값을 검사한다.
새 extension revision은 [별도 exact SHA](benchmarks/t66f-b02-a01-correction/source-lock-review.json)로
동시에 잠근다. 검사를 skip/완화하거나 원 감사 증거를 다시 쓰지 않았다. 독립 재감사는 별도다.

## 07. 교정 전후 동일 fixture oracle

TEST-ONLY `before_fetch.dart`는 최초 gzip의 이전 E2 알고리즘에서 import 경로·설명·formatter만 바꾼 비교본이다.
old D3c도 최초 gzip에서 독립 module로 불러와 동일 request와 응답을 비교한다.
canonical bytes·status/error 의미·ordering 비교와 독립 SQLite body 검사를 사용한다.
새 테스트 작성 중 잘못된 BLOB fixture/API/accepted schema 이름 오류가 있었으며 해당 실패 로그를
보존한다. 이는 제품 PASS로 세지 않는다. 반복 검증의 cached fixture 준비는 계측 밖에서 기존64/1MiB
E1 batch로 바꿨다. 단일-object 준비의 불필요한 비용을 제품 성능으로 계산하지 않는다.

## 08. 직접 관측된 backend component 결과

원 investigation의 동일64-path/141-object sample에서 old와 new를 각각3회 실행했다.
shared-prefix SELECT/load/validation은1,206→141회, 실제 read/input object bytes는608,976→71,048B,
cache hits1,065회, peak77 entries/39,648 charged bytes였다. 모든 terminal bytes는 동일했다.
wall은 약0.54→0.071초였다. 이 수치는 host component 측정이며 전체 D→E/Android 처리량이나
완성된 logical hash/validate/write byte gate를 의미하지 않는다.
[직접 counter](benchmarks/t66f-b02-a01-correction/prefix-performance.json).

## 09. 구현자 테스트·실제 HTTP·대형 실행

교정 backend 신규28개가 통과했다. 기존 관련 auth/expiry/cancel/retention/database identity/
strict B01 및 독립 B01을 함께 실행한122개가 통과했다(그 실행에는 신규 마지막3개 추가 전25개 포함).
승인 artifact 반영 후 protocol/B02119개, 원본 source isolation23개가 통과했다.
아직 이 결과만으로 대형 cold/delta 또는 전체 suite PASS를 선언하지 않는다.

실제 D→E harness는 원 fixed-H seed/TLS D3a/b/c→Flutter E2→E1→원 AppState E3→E4를 그대로
쓰며 기존 A01 request 계측에 위임한다. fixture catalog를 E1으로 복사하지 않는다.
1000-row smoke,50k,100k 순서로 실행하며 대형 campaign은 각1회와 명시적 disk/외부시간 guard를 쓴다.
외부 guard와 실제 OBSERVATION_EXPIRED는 별도로 기록한다. 상세 결과는 후속 갱신에 기록한다.

## 10. 보존·회복·비용·한계

Incomplete graph는 게시할 수 없고 실패 시 원 accepted state/legacy B/J를 보호하는 기존 규칙을
유지한다. Object data proof는 원 ticket의 publication/installation permission이 아니다.
E4-A01 ownership fence/E4-RA01 previous_source/E4 frozen lineage/pins는 변경하지 않았다.
현재 소규모 proof만으로 large fresh-process recovery나 frozen retention의 실제 통과를 추정하지 않는다.
기존 full Flutter/backend, E3 I25, E4 repeated read, SIGKILL 회귀는 최종 소스로 재실행할 의무가 남는다.

Android RSS/VFS/I/O·하드웨어 전원 손실은 검증하지 않는다. 모든 DB/session은 폐기용 합성이며
production API/DB·서비스·migration·APK 설치·activation을 사용하지 않는다. R1은 미구현/CLOSED다.
Phase B의 포괄적 logical byte 및 나머지 independent cost/race 증거는 별도 후속 의무다.

## 11. 최종 검증 갱신 및 커밋

구현자 packet/yield/expiry/두 exact hash 회귀12개가 통과했다. 동일 backend fixture 비교는 다음과 같다.

|historical rows|reachable objects|이전 packets|교정 packets|이전 평균 items|교정 평균 items|
|---|---:|---:|---:|---:|---:|
|0|126|14|14|9.000|9.000|
|200|926|322|27|2.876|34.296|
|1000|4130|1122|78|3.681|52.949|

별도 원 fixed-H1000-row 실제 TLS fixture는4,132 objects로 구조가 다르다. 같은 fixture끼리만 비교했다.
이 실제 pipeline의 cold/전체 authoritative value digest, identical0개, 한 행18개, 다중32개,
fresh-process exit0, 재시작 delta18개가 모두 통과했다. 관측한 cold(read 포함)는41.089초,
전체 campaign113.202초였다. 50k/100k의 완료 증거로 확대하지 않는다.

Flutter analyze/Ruff/compileall/frontend build/debug APK build는 exit0이었다. APK 설치는 하지 않았다.
전체 Flutter/backend 및 기존 실제 wire 회귀는 실행 중이다. 대형 cold/delta 및 최종 전체 회귀가
모두 통과하기 전에는 COMPLETE·독립 감사 준비를 선언하거나 completion commit/push를 하지 않는다.
현재 새 commit/push는 없다.

전체 회귀의 과거 소요 시간은 backend약47분/Flutter약89분이었다. 이에50k는 실제 여유
RAM18GiB 이상/디스크40GiB를 확인하고 별도 DB의 회귀와 병행했다. 공유 host 부하는
`host-overlap-50000.json`에 기록한다. 대형 수치를 단독 host 처리량 보장으로 쓰지 않는다.
campaign은8GiB process-tree RSS/최소2GiB free disk/7200초 외부 guard를 두며,
guard 종료를 server의 실제900초 lease 만료와 혼동하지 않는다.

## 12. 첫 실제50k에서 확인한 cursor 수명 결함과 후속 교정

첫 campaign은 **FAIL_COLD**였다. 정상 첫900초 만료 뒤 두 번째 observation에서
`AcquisitionFailure(GRAPH_DEPTH_BUDGET,blocked)`가 발생했다. 70,423 objects/65,058,499 payload B,
metadata58,061,118B/stages2가 저장됐고 accepted/generations는 비어 있었다. 실제 backend depth는22다.
따라서 path512·metadata384MiB·object500k의 실제 초과가 아니었다. cached-only DFS load가
이미 방문한 모든 internal parent를 prefetch queue에 계속 넣어32,768 cursor guard에 도달한 결함이다.
해당 원 source와 SHA는 `fetch.dart.failed-cursor.gz`/`cursor-failure-source.json`에 보존했다.

교정은 상한을 올리지 않는다. packet lookahead cursor와 실제 DFS ancestor의 수명을 분리한다.
실제 DFS가 떠난 subtree의 ancestor를 즉시 제거하고 pathDepth 이하로 유지한다. missing packet은
prefetch queue와 이 ancestor의 아직 필요한 siblings를 사용하므로, cached internal nodes 아래의
leaf packet도 계속 채울 수 있다. cached-only 전체 순회는 prefetch cursor를 추가하지 않는다.
원 graph verifier·canonical/hash·staging·authority·observation 규칙은 그대로다.

작은 동일 backend fixture에서 실패 revision의 cursor COUNT guard만16으로 주입해 같은 실패를
재현했다(PATH512는 그대로). 교정 후 cached1000의 실제 ancestor peak는16이고 prefetch enqueue는0,
추가 HTTP는0이었다. internal parents만 cached인 경우 이전1,316 packets→36 packets,
평균1.574→57.556 items로 개선됐고 canonical SQLite bytes/closure가 동일했다.
새 compact 재현·partial-cache 검증을 포함한14개가 통과했다. 이는 실패 revision을 skip한 것이 아니다.

실패 store를 별도 Dart process로 다시 열어 **70,423 immutable objects/stages2 healthy**, accepted=null,
legacy/pending bytes 동일, R1=CLOSED를 확인했다. full graph 읽기 성공으로 표현하지 않는다.
기존 전체 Flutter 실행은 이 교정 전 실행이므로 중단해 별도 로그로 보존했으며 최종 전체 PASS로 세지 않는다.
중단 과정의 `Cannot close sink while adding stream` loading 오류도 그대로 보존한다.
Backend 제품 소스는 이 후속 E2 교정에서 바뀌지 않았고 최종 backend1,343 tests/1,540 subtests는 PASS다.
기존 실제 TLS 회귀33개도 PASS다.

이후 cold/delta 검증은 `cursor-lifetime` suffix의 별도 campaign이며 원 실패 pointer·압축 로그를
덮어쓰지 않는다. 실제 관측한 특정 결함을 고친 소스의 재검증이지, 원인 없는 대형 반복이 아니다.
최종 Flutter 전체 회귀와50k/100k 실제 cold/delta는 이 소스로 다시 확인해야 한다.

## 13. 최종 소스 회귀와50k 완료 갱신

**IMPLEMENTATION TEST RESULT**: 위 cursor 수명 교정을 포함한 최종 Flutter 전체 실행은
`flutter test --no-pub --machine --concurrency=2`, **1,578 PASS/0 FAIL/2 SKIP**, 최종 done.success=true,
CLI exit0이었다. 중단된 이전828개 실행과 합산하지 않는다. Backend는 원 full 명령의
**1,343 tests/1,540 subtests PASS**다. Backend 최종 제품 SHA는 이후 바뀌지 않았다.
신규 backend28개는 test formatter 전후 AST 동일성을 검증한 뒤 최종 소스로 다시28 PASS였다.
기존 실제 TLS D3↔E2 회귀33개와 최종 source guard/B02 회귀71개도 PASS다.

전체 suite 안에서 E4-A01 21개/E4-RA01 42개, handoff35개/frozen19개/provenance11개,
E4 process-crash4+13개, E3 publication36개/I25 publication30개/I25 baseline1개,
E2 cleanup13개, B02 profile39개/batch13개/authority5개/crash4개가 모두 PASS였다.
이 수치를 독립 감사의 별도 case 수나 새 독립 감사 PASS로 바꾸어 표현하지 않는다.

**DIRECT OBSERVATION**: 교정50k는 실제50,035 rows/200,331 objects/200,327 edges/depth22였다.
원 deterministic fixture의 backend canonical value digest와 E4 전체11-table read digest가 같았다.
Cold→E3 공개는2,624.557초, 전체 E4 digest를 포함하면2,637.065초였고,
전체 cold/identical/delta/fresh-process/restart-delta campaign은4,226.441초였다.
고정900초 lease3회를 사용했고 처음 두 번410/new_observation을 정상 처리했다.

|Cold observation|새 객체|객체 HTTP 요청|성공 packet 평균 items|응답 entity B|
|---|---:|---:|---:|---:|
|1|81,751|1,317|62.121|106,190,145|
|2|80,064|1,252|64.000|65,453,279|
|3|38,516|607|63.453|31,603,909|

총200,331개 객체를 한 번씩 전송했다. Observation 사이 같은 객체의 재전송은0개였으며
모든 cold Target sync_root가 같았다. 응답 entity203,247,333B/request entity248,414,282B,
decoded canonical130,710,592B다. entity bytes는 TLS framing/물리 I/O가 아니다.
request-local peak는127 entries/65,468 canonical charged B였고 기록된 permit은 모두 종료됐다.
전체 cold resolver read511,009회/prefix cache hit3,080,068회였으며 이를 full-layer hash/validate
byte accounting의 완성으로 간주하지 않는다. 원 trace에서 `summarize_campaign.py`로 재현한다.

Identical은HTTP object0개/complete verification0회였다. 한 행(`id=1002`, amount123456) 변경은
독립 backend reachable-set 차분26개와 실제 전송26개가 일치했고200,305개를 재사용했다.
기존 조사25개를 억지로 맞추지 않는다. 현재 engine artifact·NS·정확한 mutation이 결합된
authoritative graph 차분이 oracle이다. 다중 localized는42개, fresh-process 뒤 delta는26개였다.
Healthy-session 한 행 delta는full recovery/verification/canonical full build0회였고
E3 COMMIT transaction22.934ms였다. Restart는 보수적인 full recovery를 수행하므로 이를
healthy-session O(1) 비용으로 표현하지 않는다. 별도 프로세스 reopen exit0/FK 오류0,
최종 accepted sequence4/E3 generation_roots12이며 보호 파일 원 bytes는 그대로다.
이12개는 accepted generation retention용 root rows이며 새 영구 Frozen-B 설치의 증거가 아니다.

Host client process peak RSS1,554,739,200B, sampler1,526,132,736B,
campaign process-tree sampler peak3,683,598,336B였다. E1 DB334,491,648B,
최종 logical metadata172,344,910B/payload131,497,909B다. E1 cold transaction7,049회,
new object insert200,331회였다. 전체 fixture·단계별 counter·raw trace는 새 summary 및 gzip에 있다.
Shared host에서 full regression과 일부 중첩됐으므로 Android/독점 host 처리량 보장은 아니다.

100k는50k 전체 통과 확인 뒤 원 fixture로 단 한 번 시작했다. 그 결과 없이 B02 COMPLETE를
선언하지 않는다. Lease900초/observations3/resource ceilings는 유지한다.

추가50k fresh-process oracle도 PASS였다. Backend hot/control root hash와 값이 같고,
20회16-row accepted read에서 full recovery/verification/canonical full build/pin write0회,
80 object reads/3,180,540 verified B/1,333,981µs였다. SQL root rows와 baseline/pending bytes도
그대로였다. 이 추가 프로세스 peak RSS는1,649,856,512B였다. 이는 accepted read 측정이며
legacy Frozen-B 설치/검증 receipt나 R1 recovery proof를 생성하지 않는다.

보호 범위를 엄밀히 구분하면, 이 대형 하네스의 `protected_legacy_before/after`는
`baseline.json`과 `online-write-1.json`이다. 후자는 `beginOnlineWrite`가 만든
`PendingOnlineWrite(outcomeUnknown)` marker이며 Frozen B/J input journal 자체가 아니다.
일부 증거 key의 `legacy_pending`은 이 보호 파일 집합을 뜻한다. 실제 B/J 입력 ID·bytes·순서 및
영구 Frozen-B lineage/pins는 기존 회귀와 source 무변경으로 확인했고, 대형 native Frozen-B
설치나 새 R1 proof까지 시험한 것으로 확대하지 않는다.

## 14. 원 네 Flutter 실패·형식 검사 취급

원 pin_inserts0 기대/실제4 및 cached3×524288B 거부 누락은 이전 B02 최종 편집 전 실행이었다.
해당 원 로그·주장·후속 조사·현재 B02 파일 bytes를 모두 보존했다. 현재 batch/authority 회귀와
전체 suite가 통과했다. 나머지fetch/AppState SHA 두 건은 승인 범위 diff를 검토하고 원 default
hash 복원 검사+새 extension exact hash 검사를 함께 유지한23개 isolation 회귀로 해결했다.
원 protected-source.json/golden/감사 보고서 기대값은 수정하지 않았다.

Ruff/compileall, 변경 Dart 파일과 신규 Python 파일의 형식 검사, diff check는 통과했다.
`ruff format --check transfer.py`의 파일 전체 재포맷 요구는 **교정 전 원본도 동일하게 실패**한다.
기존 style의 source 전체를 재포맷하면 승인된 engine artifact까지 불필요하게 달라지므로 하지 않았다.
이 알려진 원본 형식 차이를 숨기거나 전체 파일 formatter PASS로 보고하지 않는다.
최종 analyze/debug build는cursor 교정 뒤 exit0이고 frontend build도 exit0다. APK 설치는 없다.

## 15. 100k 실제 종료 — 필수 시험 실패

**DIRECT OBSERVATION**: 원100k fixture는 ledger100,000/전체100,035행,
V400,532/E400,528/depth23/261,543,083 canonical B로 확인됐다.
Bootstrap702.091초 뒤 실제 TLS D3a/b/c→E2→E1 경로를 단 한 번 실행했으며,
고정900초 observation3회를 소진하고 **FAIL_COLD**로 끝났다.
Client cold2,700.166286초, 전체 campaign3,445.879655초, Flutter child exit1이었다.
외부7200초/메모리8GiB/여유 disk guard 종료가 아니다. Wrapper CLI가0으로 끝나는 것과
내부 Flutter 실패를 혼동하지 않는다. 전체100k E3 공개/E4 읽기/one-row delta는 **NOT RUN**이다.

|관측|validated_at → expires_at (UTC)|새 객체|객체 HTTP 요청|성공 packet 평균 items|응답 entity B|
|---|---|---:|---:|---:|---:|
|1|2026-10-19T05:33:33Z → 05:48:33Z|101,472|1,654|61.387|161,825,749|
|2|2026-10-19T05:48:33Z → 06:03:33Z|102,400|1,601|64.000|83,801,264|
|3|2026-10-19T06:03:33Z → 06:18:33Z|90,752|1,419|64.000|74,275,554|

세 번 모두 실제 HTTP410 body의 `error.code=OBSERVATION_EXPIRED`,
`error.action=new_observation`, `current_ns=null`, `retry_after_ms=null`이었다.
정확한 request/observation ID와 body는 `http-100000-server-http-failures.json.gz` 및 trace에 있다.
200 응답4,671 packets/만료3건, 관측 생성201 3건/해제204 3건이며 기타 HTTP 오류는 없었다.
미도달 native client attempt를 별도로 계수하지 않았으므로 이를 native 실패0회로 확대하지 않는다.

총294,624개가 전송되고 같은 수가 실제 E1에 저장됐다. 필요한105,908개 객체가 남았다.
관측 간 이미 받은 객체의 재전송은0개, 세 Target는 같았다. Response entity319,902,567B,
request entity384,953,287B/decoded canonical207,943,893B다. Backend 실제 resolver read756,161회,
nonterminal prefix validation461,537회/cache hit4,817,684회였다. 모든 terminal object 검증은
엄격히 유지됐다. Cache actual peak131 entries/67,666 canonical charged B로 한도 안이다.
기록된 permit은 성공·만료 모두 종료됐고 B01 strict 단언도 최종 회귀에서 그대로 통과했다.

독립 SQLite는 objects294,624/payload207,943,893B/metadata246,545,216B/stages3,
E1 DB500,199,424B, FK 오류0을 확인했다. 세 acquisition은 모두 interrupted/OBSERVATION_EXPIRED다.
accepted current/previous=null/sequence0, generations0/generation_roots0이므로 incomplete graph나
가짜 accepted receipt를 게시하지 않았다. E1 INSERT294,624회/transaction9,565회,
graph_nodes_examined599,176회/object reads1,199,415회/verified bytes960,490,674B였다.
마지막 두 수치는 중복 처리도 포함한 store 계수이지 전층 logical byte 총량이 아니다.

Host client sampled peak RSS563,261,440B/OS process peak562,999,296B,
campaign process-tree sampler peak2,193,469,440B였다. **부분 획득의 peak**이므로 full100k의
E3 canonical rebuild/E4 materialization peak나 Android 안전성으로 해석하지 않는다.
전체 임시 디렉터리 최종 크기·DB/journal 파일 크기는 독립 durable snapshot에 있으며 transient
physical pager write/peak disk/순수 Dart heap은 미측정이다.

Backend manifest 송신 종료→첫 objects request 도착 간격은 각0.080/114.228/207.178초였다.
이는 같은 monotonic trace의 직접 관찰이며 순수 E1 시간이나 순수 network 지연이 아니다.
원 코드상 갱신된 stage에서 cached typed closure/progress를 다시 처리하지만, 정확한 client CPU
분할은 계측하지 않았다. 모든 갱신에서 strict provenance·원 authority 경계를 그대로 유지했다.

## 16. 결론·남은 한정 작업·증거 수준

**IMPLEMENTATION TEST RESULT**: cold packet 충전과 request-local prefix 재사용은 같은
small/medium fixture에서 redundant work를 줄였고50k 실제 cold/delta/read/restart도 통과했다.
그러나 mandatory100k가 실패했으므로 **B02/B02-A01 COMPLETE가 아니다**.
단순히 budget 상수만 올리거나 warm component PASS를 full100k PASS로 바꾸지 않는다.

**ANALYTICAL ESTIMATE**: 이 host의 관측된 packet/고정 metadata 작업과 갱신 후 재순회 비용은
남은 조사의 후보다. 특정 추가 subsystem 변경이 반드시 정답이라고 확정하지 않았다.
해당 비용의 정확한 분할과 계약상 재사용 가능한 증거를 별도 한정 조사에서 먼저 확인해야 한다.
lease/observation 확대, 검증 생략, 전역 prefix cache, 새 storage/graph architecture는 구현하지 않았다.
원인이 입증되지 않은 추가 대형 재실행도 하지 않았다.

실패 store를 별도 Dart process에서 다시 열어 exit0/healthy=true,
objects_checked294,624/stages_checked3/accepted=null, 보호 파일 SHA 동일을 확인했다.
검사 과정의 object reads894,430회/verified bytes688,239,410B/full_recoveries1회는
cold 재개 건강 검사 비용이며 ordinary read 비용으로 표현하지 않는다. 완전한100k 금융 read나
R1 복구 준비 증거가 아니다. 실행 당시 latency는 별도 stopwatch로 계수하지 않았다.

**UNVERIFIED CLAIM**: full100k cold/delta/read 지원, large native Frozen-B 설치/영구 lineage retention,
Android memory/VFS/I/O 및 hardware power-loss 안전성을 주장할 수 없다. 기존 E3 I25 tests와
50k1행 bounded delta는 보존됐으나 요구된100k I25 grid는 INCONCLUSIVE다.
E4 Frozen-B/provenance/ownership/previous_source 회귀는 PASS이며 제품 코드는 그대로다.
대형 accepted logical read 검증과 Frozen-B 검증을 같은 것으로 표현하지 않는다.

Phase B의 전층 logical hash/validate/write byte gate는 PARTIAL이며 독립 최종 accounting이 남는다.
§38 실제 Android proof와 §31/34 R1 dependency도 별도다. R1은 구현하지 않았고 gate는 CLOSED,
normal startup/financial read-write/SQLite user_version4/Snapshot v7/OfflineBaseline v4/Frozen B/J는
변경하지 않았다. 배포·APK 설치·production segmented activation은 없다.

## 17. 구현자 판정과 Git 정책

현재 판정은 **T6.6F-B02-A01 CORRECTION INCOMPLETE — FURTHER TARGETED WORK REQUIRED**다.
미해결 Critical/High/Medium correctness finding을 새로 확정한 것은 없지만100k feasibility 및
후속100k delta/read 필수 gate가 열려 있다. 첫50k의 cursor 수명 결함은 교정·재검증했고 원 실패
source와 evidence를 보존했다. 이것은 독립 targeted audit PASS나 Phase B PASS가 아니다.

완료 조건이 충족되지 않아 stage/commit/push를 하지 않는다. 원 index와 staged diff를 보존하며
최종 worktree는 원 B02·조사·이번 교정 때문에 의도적으로 DIRTY다. 원 protocol·historical audit
report·원 조사·golden·진단을 덮어쓰지 않았다. 최종 refs/보존 check는 새 evidence에 기록한다.
독립 B02 완료 감사 준비는 NO이며 Phase B 재개/T6.6F 완료/R1/배포를 승인하지 않는다.

## 18. 최종 검증 행렬

|검사|최종 구현자 결과|한계|
|---|---|---|
|신규 E2 packet/yield/context|14 PASS|동일 fixture 비교·cached-parent 두 case 포함|
|신규 D3c prefix|28 PASS|원 strict resolver와 동일 current Target 비교|
|source isolation 최종 재검사|23 PASS|과거 SHA 기대값 유지, 새 helper는 독립 재감사 전|
|현재 source/B02 선택 회귀|71 PASS|full suite에도 포함|
|기존 실제 TLS wire 회귀|33 PASS|mock-only가 아님|
|신규 실제 D→E grid|1k PASS/50k PASS/100k FAIL|별도 harness, full Flutter 집계와 별개|
|전체 Flutter|1,578 PASS/0 FAIL/2 SKIP|최종 executable source, 기존 중단 실행 제외|
|전체 backend|1,343 tests/1,540 subtests PASS|신규28개 포함, 원 strict B01 단언 유지|
|Flutter analyze/debug APK build|PASS|cursor 교정 뒤 source, APK 설치 안 함|
|frontend npm build|PASS|frontend source 무변경|
|Ruff/compileall|PASS|backend 및 새 evidence helpers|
|변경 Dart/신규 Python 형식|PASS|기존 transfer.py 전체 재포맷 차이는 §14의 알려진 예외|
|git diff --check|PASS|stage/commit/push 없음|

원 packet12개 실행은 새 cached-parent 두 case 추가 전의 역사이며, 최종14개와 합산하지 않는다.
최종 test source의14개만 신규 E2 결과로 보고한다. 중단된 Flutter의
828 PASS/2 SKIP/loading error3개 및 최초50k FAIL은 원본 gzip/별도 key로 보존한다.

마지막 `HEAD/main/origin/main/git ls-remote origin refs/heads/main`은 모두
`6282c1c3577c42bba9382d786745d583a5d88236`로 일치했다. 새 commit은 NONE/push는
NOT PERFORMED다. 최초1,549개 파일 중 의도된6개 변경만 있으며 원 B02 AppState/store와
기존 B02 tests·보고서·조사 증거는 SHA가 같다. 원 index/staged diff도 동일하다.
상세 refs와 현재 source SHA/dirty 목록은 `repository-final.json`/`preservation-final.json`에 있다.
새 증거는 약6.4MiB이며 secret/TLS private key/DB 사본을 추가 보관하지 않는다.
