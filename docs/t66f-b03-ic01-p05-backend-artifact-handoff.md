# T6.6F-B03-IC01-P05 backend artifact 인계 검증

**PASS — REPRODUCIBLE TEST-ONLY BACKEND ARTIFACT HANDOFF VERIFIED**

**NOT RUN — COMPATIBLE ORIGINAL TARGET UNAVAILABLE**

두 판정은 독립적이다. 작은 합성 backend의 일관 보존·종료·복원·인증된 D3 사용은 검증했다.
원 P03 backend는 삭제됐고, 사용자가 확인한 재부팅으로 원 client와 P04 clone의 `/tmp` 경로도
이번 환경에 없다. 원 Target tail을 실행하거나 P03 실패를 성공으로 바꾸지 않았다. 새 100k cold 실행은 0회다.
B03 독립 PASS·IC01 완료·Phase B 완료·배포 승인은 선언하지 않는다.

## 1. 시작 저장소

HEAD/main/origin/main/실제 원격 main은 모두 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이다.
개발 checkout에서만 작업했다. [시작 상태](benchmarks/t66f-b03-ic01-p05/evidence/starting-state.json)는
staged/unstaged/untracked, 기존 3,392개 파일의 SHA, index, 공간을 구분한다.
초기 index의 SHA는 `d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`다.
새 사용자 작업 `docs/money-note-disk-cleanup-audit.md`, `docs/money-note-disk-cleanup-candidates.json`도 보존했다.

## 2. 기존 작업과 index

IC01/P01/P02/P03/P04 source·tests·보고서·raw evidence를 보존했다. 기존 파일 중 유일한 추가 변경은
명시적으로 허용된 test-only `docs/benchmarks/t66f-b02-implementation/server.py`의 lifecycle 옵션이다.
시작 파일 3,392개를 다시 대조했고, 삭제 0개·index 불변이다. 원 구현은 Git의 원 source 및
[시작 diff](benchmarks/t66f-b03-ic01-p05/evidence/starting-unstaged.patch)로 재구성 가능하다.
reset/stash/clean/checkout/rebase/stage/commit/push를 하지 않았다.

## 3. P03 backend 삭제 원인

P03 child PID는 보존된 기록상 689332다. P03 wrapper가 B02 test server를 실행하고,
`RetentionSandbox`가 `CaptureSandbox`의 `TemporaryDirectory(prefix="money-note-d1-")`를 소유했다.
원 파일은 `/tmp/money-note-d1-<기록되지 않은 임의 suffix>/synthetic.sqlite3`였다.
정확한 임의 디렉터리 이름은 원 로그에 없어 복원 가능한 실제 절대 경로라고 주장하지 않는다.

서버 `finally`는 `should_exit`→`worker.join(15)`→종료 assertion을 수행했고, 바깥 context의
`CaptureSandbox.__exit__`가 임시 디렉터리를 정리했다. `RetentionSandbox.__exit__`는 마지막에
소유권 descriptor도 닫는다. 정상 SQLite connection 종료와 WAL 정리가 backup을 만들지는 않는다.
원 fixture/Target JSON·요청 로그는 남았으나 전체 backend DB/catalog 사본은 남지 않았다.

## 4. 원 backend 복구 조사

[복구·eligibility 기록](benchmarks/t66f-b03-ic01-p05/evidence/recovery-and-eligibility.json)의 Option A는 불가다.
알려진 원 P03 server/client·역사 G1·P04 clone 경로는 재부팅 뒤 없다. 보존된 저장소의
P03/P04/디스크 감사 metadata는 원 DB 파일의 사본이 아니다. 운영 DB·개인 데이터·홈 전체를 검색하거나
실험 입력으로 사용하지 않았다. 원 backend의 삭제와 재부팅 후 client 부재를 서로 다른 사건으로 기록한다.

## 5. 계약상 identity와 재사용 조건

§5의 durable client namespace는 HTTPS origin/server_id/dataset_id/epoch/principal/Versions다.
§6·§9의 Target에는 revision/Context/four refs/sync_root가 결합한다. 객체는 C1 body의 NS,
정확한 Ref 길이와 domain framing을 포함한 hash로 식별한다. 숫자 N이나 root만 같아서는 부족하다.
§15–17의 원 credential·principal·observation·TTL 및 실제 DB descriptor fence도 필요하다.
Receipt/완료 marker는 새 AppState ticket이나 accepted-generation 권한이 아니다(§24–25).

실행 중의 file device/inode는 소유권 fence의 관측값이지 영구 global database ID가 아니다.
삭제된 inode 번호는 재사용될 수 있다. 새 살아 있는 artifact와 새 sandbox의 독립 소유권을 검사했다.

## 6. 결정적 재구성 가능성

Option B의 지원 경로는 확인하지 못했다. 기존 seed는 금융 입력을 만들 수 있지만 UUIDv4 발급,
epoch bootstrap, 원 timestamp/Context까지 원 Target을 재현하지 않는다. P03 `fixture.restore()`도
지금 사라진 역사 `/tmp` G1 객체를 입력으로 요구했다. 생성되는 비슷한 새 graph를 원 graph라고 부를 수 없다.
§5는 physical backup 복원도 quiescent cold startup과 새 epoch를 요구한다. 옛 identity를 강제로
주입하거나 client를 수정하지 않았다. 100k 재구성 실행도 0회다.

## 7. 원본·재구성·새 artifact 분류

원 P03 backend: **DELETED**. 원 P03 client: **현재 UNAVAILABLE**, 과거 독립 SHA·397,146행 증거만 존재한다.
P05가 보존한 것은 **새 작은 합성 backend의 ORIGINAL_SYNTHETIC_SNAPSHOT**이다.
P03 원본 복구나 P03 matching reconstruction이 아니다. Option C를 선택했다.

## 8. test-only lifecycle 변경

[기존 서버](benchmarks/t66f-b02-implementation/server.py)의 `main(*, artifact_destination=None)`은
기본값에서 기존 `RetentionSandbox`와 cleanup을 그대로 쓴다. 명시적으로 지정할 때만 새
[artifact_handoff.py](benchmarks/t66f-b03-ic01-p05/artifact_handoff.py)를 import한다.
[P05 server.py](benchmarks/t66f-b03-ic01-p05/server.py)는 이 옵션을 노출하는 benchmark 진입점이다.
제품 import/API·영구 설정·telemetry·동기화 알고리즘을 추가하지 않았다.
[사용 방법](benchmarks/t66f-b03-ic01-p05/README.md)은 stdout private credential pipe를 로그에 남기지 않도록 한다.

## 9. SQLite snapshot 일관성

소유권을 확인한 실제 sandbox connection의 SQLite backup API를 사용한다. 원 DB를 통째로 파일 복사하지 않는다.
backup progress에는 60초 종료 한계를 두며, 완료 후 integrity/FK·현재 generation·Target root·현재 Target의
전체 reachable canonical graph를 독립 literal SHA/C1 oracle로 검사한다. obsolete catalog 전체의 의미 검증,
제품 admission engine 대체, 하드웨어 내구성 보장은 아니다.

## 10. WAL 처리

원 retention runtime은 WAL이며, 보존본은 `journal_mode=DELETE`의 자체 완결 파일이다.
살아 있는 reader와 committed WAL frame, 별도 uncommitted username 변경을 동시에 만든 시험에서
committed 값만 보존했다. source WAL/SHM을 나란히 파일 복사하지 않았다.
복원 시 새 자가 소유 inode에 backup한 뒤 WAL profile을 설정하고 기존 schema admission을 통과했다.
제품 user_version 4나 실제 SQLite schema는 변경하지 않았다. 보존 profile은 기존 isolated 1,000,005다.

## 11. 종료·실패·정리 경계

정상 종료, 잘못된 backend 요청, acquisition 요청 실패, faithful test clock의 901초 만료,
body exception, 명시적 async task cancellation, 반복 생성/종료를 검사했다.
clock 이동은 해당 소형 expiry 시험만의 기존 test clock이며 production TTL은 900초 그대로다.
실제 TLS child의 정상 exit 0과 의도된 ValueError exit 1에서도 artifact를 검증했다.
실제 서버 thread/ASGI lifespan/native worker 종료 후 보존·원 임시 자원 정리가 이어진다.
SIGKILL·host reboot 이전에 backup 코드가 실행된다는 보장은 하지 않는다.

## 12. artifact manifest

새 destination을 배타적으로 예약하여 기존 evidence/partial을 덮어쓰지 않는다.
`backend.partial.sqlite3`의 backup·검증·digest가 끝나면 파일을 확정하고, 원 cleanup 결과와 함께
`manifest.partial.json`을 fsync한 뒤 `manifest.json`을 마지막 완료 표식으로 게시한다.
디렉터리도 fsync한다. 실패는 `failure.json`이며 partial 존재만으로 성공으로 판정하지 않는다.
manifest에는 schema/run/fixture/source SHA, 원 path/device/inode, namespace/principal,
revision/tx/Target/sync_root, 예상/실제 reachable 수, catalog 수, SQLite schema/user_version,
integrity/FK, 파일 digest·크기·시각·cleanup·한계를 기록한다.

토큰 원문·password·운영 credential은 manifest에 없다. 실제 보존본은 0600/디렉터리 0700이며
합성 DB의 one-way session hash만 포함한다. 일반 Snapshot v7 export와 다른 test-only 증거다.

## 13. 현재 검증한 canonical 인계 artifact

정상 canonical 경로는
`docs/benchmarks/t66f-b03-ic01-p05/evidence/run-final-format/artifacts/tls-normal/`이다.
그 안의 `manifest.json`과 `backend.sqlite3`를 함께 사용한다. N=1,000의 실제 seed graph
4,132개를 보존했고 expected count와 독립 closure count가 같다. backend 전체 catalog 수는
reachable 수와 별도 필드다. sibling `tls-exception/`도 실패한 실행의 증거로 남긴다.
`manifest-tamper/`는 의도된 거부 fixture이므로 canonical 인계본으로 사용하면 안 된다.

## 14. backup 실패 처리

연결 실패, backup 이후 검증 실패, 잘못된 expected count, setup 실패는 성공 manifest를 만들지 않았다.
원 body exception과 backup 실패가 겹치면 원 예외를 보존하고 preservation 실패 note를 붙였다.
manifest/파일 변조는 digest 또는 실제 SQL/Target 대조에서 거부했다. 기존 destination은 factory 생성 전에 거부했다.
초기 새 시험의 가정 오류와 수정 결과는 아래 §28처럼 별도 raw 로그에 보존한다.

## 15. cleanup 후 복원 사용성

원 sandbox가 정리된 뒤 saved DB를 독립 read-only로 열어 재검증했다. 다른 새
`RetentionSandbox`에 supported backup-into-owned-inode 방식으로 넣고 기존 WAL/admission을 적용했다.
§5대로 bootstrap하여 server/dataset은 보존하고 epoch/root는 새로 발급했다.
인증된 실제 ASGI D3는 200, 잘못된 credential은 401, old observation은 409,
다른 dataset의 잘못된 base는 409였다. 실제 내려받은 raw-root SHA를 literal framing으로 검사했고
11개 금융 table의 값은 bootstrap 전후 같았다.
[복원 D3 증거](benchmarks/t66f-b03-ic01-p05/evidence/restored-d3.json)는 old/fresh Target을 분리한다.

## 16. Target compatibility 판정

사본이 old Target bytes를 보존했다는 offline integrity와 old Target을 다시 download할 권한은 다르다.
§5는 재시작 후 old epoch의 관측 재사용을 금지한다. 복원 서버가 새 Target을 정상 제공한다는
검증을 old client와의 matching proof로 바꾸지 않았다. 살아 있는 원 publisher/namespace/credential을
검증할 수 없으므로 원 P03 matching은 **INCONCLUSIVE**, matched tail eligibility는 **NO**다.

## 17. 원 P03 client DB

현재 원 path 및 WAL/SHM은 모두 없다. 따라서 이번 SQL integrity 재검증은 **UNAVAILABLE**다.
기존 디스크 감사는 재부팅 전 SHA
`9adbc6bb6f4df2d756dedb4825450a540ee490e64f48e9f5d803e08094729ce6`,
397,146개 객체, accepted current/previous null·sequence 0, integrity/FK 정상, sidecar 없음을 기록했다.
이는 **CORROBORATED HISTORICAL EVIDENCE**이며 fresh verification으로 세지 않는다.
P05는 원 client/P04 clone을 수정·삭제·재생성하지 않았다.

## 18. matched-tail 실행 여부

**NOT RUN — COMPATIBLE ORIGINAL TARGET UNAVAILABLE.** 원 client와 compatible backend 모두 없다.
matched ON/OFF pair 0, fresh 원 Target observation 0, 실제 원 tail의 graph closure/E3/E4 미실행이다.
남은 3,386개를 새 fixture의 3,386개로 대체하지 않았다. 원 P03 결과는
397,146/400,532·세 관측 만료·2,699.957907초·E3/E4 미도달의 **FAILED** 그대로다.

## 19. 소형 실제 ON/OFF 기능 대조

원 tail과 별도로 원 독립 native witness assertions를 P05 증거 경로로 실행했다.
실제 TLS→Flutter E2→E1→E3→E4에서 144 reachable objects, canonical 89,644B를 확인했다.
Flutter cold 계측 OFF/ON wall은 24.090058/22.789290초다. 각 mode의 cold/reuse를 포함한
HTTP 150건, request entity 83,390B, response entity 165,060B, decoded 89,644B였다.
이 한 쌍은 calibration/금융·durable equivalence용이며 tail 성능 대조나 유의한 속도 차이 증거가 아니다.
backend instrumentation은 공통 활성 상태이고 E4의 독립 read collector는 두 mode 모두 명시 실행했다.
전체 workload의 완전 OFF/ON benchmark라고 부르지 않는다.

## 20. 추가 timing observer

원 Target의 A/B/C matched 비교를 못 했으므로 추가 timing observer와 논리 계수의 인과 비용은
**INCONCLUSIVE**다. P03 callback 약23.55초는 전체 observer 비용이 아닌 하한 성분이었다.
P04의 E1 보조 4-mode 비교도 부호가 반복마다 달랐다. 이번 소형 wall 차이로 그 결론을 뒤집지 않는다.
52.07초 요청 gap이나 P03와 역사 100k의 총 시간 차이를 전부 계측 탓으로 돌리지 않았다.

## 21. HTTP/E2/E1 계측 경계

소형 HTTP handler 합은 OFF/ON 22.286837/21.333572초다. ASGI handler 경계이며 client 전체 wall,
네트워크 대기, E2, E1과 겹칠 수 있다. E2·E1 전용 wall/CPU와 SQL observer time은 이번에 독립 측정하지 않았다.
그 값을 0으로 기록하지 않는다. 원 tail HTTP/E2/E1 비용은 **NOT MEASURED**다.
[작은 HTTP 요약](benchmarks/t66f-b03-ic01-p05/evidence/small-http-summary.json)과 실제 raw counters를 구분한다.

## 22. graph closure·E3/E4

소형 기능 fixture에서는 complete graph, atomic accepted publication, 동일 raw monetary/Unicode 값의
E4 read가 통과했다. 원 P03 resumed-terminal path는 미실행이다.
§16에 따라 transfer lease 만료는 이미 완전 취득·검증한 coherent 관측의 local publication을 자동 무효화하지 않는다.
그러나 mid-download expiry의 incomplete graph를 게시할 수 없고 §25의 원 ticket/final guard/COMMIT가 필요하다.
원 실패를 단순 3,386개 추가 download만으로 해결했다고 가정하지 않았다.

## 23. counter 정확성

fresh Python/Flutter native/literal oracle 회귀와 소형 실제 native witness가 통과했다.
소형 새 객체의 committed BLOB은 **89,644B**, effective additions는 **144행**으로 독립 SQL state와 같다.
새 객체마다 한 번의 hash를 가정한 독립 최소 preimage는 **93,985B**다. 실제 E2 object hash
**569,645B**, primary validation submitted span **1,190,360B**는 반복 검사·metadata를 포함한다.
이 차이는 HTTP entity나 unique object bytes와 같은 값이어야 하는 것이 아니다.
E1 SQL은 실제 호출을 감싼 활성 E2 stage에 귀속되며 E3 prepare/verify/commit과 E4는 별도 stage다.
failed/attempted/effective/committed/rollback·savepoint·cache reuse는 기존 corrected native oracle로 대조했다.
물리 SQLite/VFS I/O나 parser의 정확한 consumed memory bytes라고 표현하지 않는다.

## 24. 자원·디스크·opportunistic 정리

시작 available **25,017,950,208B**, repo allocated **78,625,124,352B**였다.
대형 100k 생성/clone은 없고 소형 보존 bundle만 새 증거 디렉터리에 남겼다. 원 source sandbox는
기존 lifecycle로 정리됐다. process-wide backup 후 peak RSS는 별도로 측정하지 않았으며 child의
pre-backup ru_maxrss를 전체 capture peak로 광고하지 않는다. 기본 서버의 기존 8GiB AS 제한도 그대로다.

[cleanup manifest](benchmarks/t66f-b03-ic01-p05/evidence/cleanup-manifest.json)는 추가 정리 등록분의
정확한 path·생성 근거·inode·할당량·digest·fuser 결과·삭제 직전 재검증·회수량을 기록한다.
검증된 canonical backend를 먼저 다시 열어 확인한 뒤 P05 새 compiler cache 1개, 폐기용 calibration
SQLite 2개, 종료된 TLS child의 임시 private key 8개와 최종 compileall 뒤의 P05 bytecode 6개만 unlink했다. 총 **17개 / 50,057,216B**,
관측된 실제 available 증가도 **50,057,216B = 0.046619 GiB**다. 기존 파일 삭제·수동 디렉터리 삭제는 0개다.
보존 backend/원 보고서/과거 cache/원 P03·P04 artifact를 삭제하지 않았다. 승인 필요 후보는 없다.

이는 추가 정리 registry의 수치이며 SQLite backup 중간 rename 횟수나 library 기본 sandbox의 총 생성 I/O를
포괄하는 척하지 않는다. 첫 fuser 호출의 CLI 구문 오류는 삭제 0개였고 영수증을 보존했다.
인자를 바로잡은 최종 검사는 사용 PID 없음·stderr 없음이었다. 사본과 필요한 결과가 남는 소유 파일만 정리했다.
최종 측정 available은 **24,890,404,864B**, repo allocated는 **78,747,631,616B**이며,
retained evidence는 **244개 / 0.113422 GiB**다.
시작·종료 공간 차이는 새 증거/빌드와 호스트의 다른 쓰기도 포함하므로 회수량과 동일시하지 않는다.
마지막 공간·retained evidence 개수/크기는 [disk-final.json](benchmarks/t66f-b03-ic01-p05/evidence/disk-final.json)에 기록한다.

## 25. B03·Phase B 요구 소유권

[기계 판독 matrix](benchmarks/t66f-b03-ic01-p05/evidence/requirement-ownership.json)의 요지는 다음과 같다.

|요구|구속력 있는 원본|소유·현재 상태|
|---|---|---|
|실제 hash/validation/write bytes|§35, §36 I25 및 B03의 계수 정의|B03은 측정 도구의 정확성·coverage. 독립 calibration/재감사 OPEN|
|scope·유한 collector·native 수명|§34 verification ownership, §25 authority 보존 및 B03 감사 §§13–17/23|B03 계측의 정확성·자원 조건. 구현 측 focused PASS|
|고정 H/D, 1k/5k/10k/50k/100k no-change/card/cash|§35 마지막 scaling 문단|Phase B 최종 실제 비용 증거. NOT RUN|
|정상 full-N 작업 0·E3 I25 scaling|§25, §35, §36 I25|Phase B D/E integration. 미확인|
|모든 보조 observer ON의 100k cold 성공|binding의 §35 cold O(N) 허용·§15–17 lease, 별도 IC01 §11·P03 실행 지시|이전 작업에서 추가한 실험 gate. P03 실제 FAIL 보존|
|Android driver/VFS·physical power-loss|§26, §38 proof 8|durable/device·rollout 차단 gate. NOT VERIFIED|
|실기기 절대 latency|§35, §38 proof 12|post-T6.6 gate. threshold 새로 정하지 않음|
|R1 large restore/MW|§31, §34|R1 및 전체 exit dependency. DEFERRED, activation CLOSED|

Android/VFS·전원 손실의 rollout 차단은 §26에 명시돼 있다. 그것을 B03의 logical byte 정의와 혼동하지 않는다.
과거 Phase B closure §3이 기록한 세부 단계 배치의 ambiguity도 승인 없이 해소했다고 주장하지 않는다.

§35는 **“Scaling 감사는 H/D 고정, N=1k/5k/10k/50k/100k에서 no-change/card/cash rebuild를 반복”**하도록 요구한다.
§36 I25는 **“steady-state full N 작업 MUST NOT”**, proof는 **“instrumented rows/bytes”**다.
반면 binding에는 B03라는 task 이름이나 “모든 보조 timing observer ON인 100k cold가 B03 폐쇄의
별도 전제”라는 문구가 없다. 원 cold의 O(N) 허용은 비용 면제나 incomplete publication 허가가 아니다.

따라서 **정확히 보정된 counter·유한 scope/resource·대표 실제 전층 시험의 B03 재감사와,
전체 규모 실행 perturbation/고정 H/D 실제 grid의 Phase B 검증을 분리하여 심사하도록 요청하는 것은 계약과 양립한다.**
이는 독립 검증자에게 제안하는 범위다. 이전 IC01 보고서의 추가 gate를 삭제하거나 스스로 승인하지 않았다.
B03 전체 mandatory seam의 coverage도 여전히 독립 검증 대상이다.

후속 방법론 후보는 정당하게 취득·검증·게시한 accepted 초기 상태와 측정하는 정상 refresh의 경계를
명시하고, 실제 no-change/card/cash 작업 전체에서 mandatory 계수를 빠짐없이 수집하는 것이다.
비필수 evidence formatting은 scope 밖으로 분리할 수 있지만 mandatory generation/validation/write를
setup 이름으로 숨기거나 샘플링할 수 없다. 이번에는 방법론 승인·실행·grid 재개를 하지 않았다.

## 26. IC01·P02·금융 보존

IA01–IA07 원 independent findings/frozen reproducers는 그대로다. corrected same-name savepoint,
OR FAIL partial SQL success, comment DML, nested install, rejected native dispatch, owner32,
generation/oracle 분리를 fresh 회귀로 확인했다. IA07 원 snippet은 바꾸지 않고 repo cwd에서
실행하여 setup 반환176/185행·제품 generation oracle query0을 확인했다.
P02 cache32/connection ownership/reset-rebind/finalization·정확 counter와 durable state도 통과했다.
B01 strict concurrency assertion 및 B02 profile/TTL/시도·packet 한도는 변경하지 않았다.
B01/B02/E4-A01/E4-RA01은 CLOSED다. P03 만료를 새 금융 correctness 결함으로 재분류하지 않았다.

P0 lineage, E3 원 AppState ticket/final guard→COMMIT, Snapshot v7, OfflineBaseline v4,
sync_root/legacy fingerprint 분리, Frozen B/J input-only·no ACK/no rebase는 제품 source 불변이다.
재부팅으로 사라진 원 pending 파일을 fresh read로 검증했다고 주장하지 않는다.

## 27. source-lock 정책

제품 source·binding protocol·expected SHA·역사 보고서·원 independent tests는 시작 fingerprint와 같다.
현재 exact source guard 6개와 그 역사 복원 검사를 Flutter에서 fresh 통과했다.
[보존 증거](benchmarks/t66f-b03-ic01-p05/evidence/preservation.json)는 실제 SHA 대조 결과를 기록한다.
역사 23개 전체 회귀를 이번에 별도 전부 실행했다고 주장하지 않는다. 새 protected 변경이나 SHA 갱신은 없다.

## 28. fresh focused 회귀

최종 source의 새 Python lifecycle **19 PASS / 0 FAIL / 0 SKIP**, P05 경로의 소형 실제 TLS/Flutter
기존 assertions 재실행 **2 PASS**다. fresh 기존 backend **214 PASS / 0 FAIL**,
Flutter IC01/P02/primitive/boundary/lineage/source-lock **73 PASS / 0 FAIL / 0 SKIP**다.
backend의 원 결함을 기대하는 `test_reproduce_` 4개는 frozen historical assertion으로 별도 보존했고,
corrected native oracle를 실행했다. 현재 실패를 SKIP/XFAIL로 숨기지 않았다.

초기 P05 새 시험에는 committed WAL 없이 양수 WAL을 기대한 오류, 해제된 inode 번호의 재사용을
허용하지 않은 오류, DELETE 보존본을 WAL로 되돌리지 않은 시험 setup, 기존 stderr 경로 재사용,
wire field를 `data`로 잘못 읽은 오류가 있었다. 초기 로그·XML을 보존하고 기대를 완화하지 않은 채
실제 protocol의 `data_base64`, WAL profile·fresh 소유권·새 evidence 경로로 수정했다.
첫 pytest fixture repr의 종료된 임시 token 원문은 redaction 영수증과 함께 제거했다.
IA07의 첫 실행도 잘못된 backend cwd 때문에 실패했으며 원 snippet을 바꾸지 않고 올바른 repo cwd에서 통과했다.

최종 Python format/Ruff/compileall, Dart changed-file format, `git diff --check`, frontend build를 통과했다.
원 로그는 `new-tests-final-format.xml`, `backend-targeted.xml`, `flutter-targeted-summary.json`,
`small-http.jsonl`, `ia07-current.json`, `static-checks.json`을 참조한다.

## 29. full regression 상태

제품·계측 semantics를 변경하지 않아 full backend/Flutter는 **NOT RERUN**이다.
P02의 **1,436 tests / 1,540 subtests PASS**, Flutter **1,690 PASS / 2 SKIP**는
raw summary와 대조한 **HISTORICAL RESULT**다. fresh 숫자로 복사하지 않았다.
Flutter 전체 analyze/debug build도 NOT RERUN이다. 새 100k cold, 다섯 N grid, R1·배포·APK 설치는 실행하지 않았다.

## 30. 남은 blocker와 두 판정

Artifact handoff는 small synthetic 범위에서 **PASS**다. 삭제된 P03 backend의 복구와
재부팅으로 사라진 원 client/P04 clone은 이번 PASS의 전제가 아니다.
Original matched tail은 **NOT RUN**이다. 원 규모 tail 비용·timing observer 인과 비용·full cold logical snapshot,
고정 H/D grid·I25 scaling·Android/VFS/physical power loss·R1은 미확인/미완료로 남는다.
계측 semantics의 구현 측 PASS를 독립 B03 승인으로 바꾸지 않으며 IC01 combined 상태는 INCOMPLETE다.

## 31. 한 가지 다음 행동

**독립 검증자에게 IA01–IA07·정확 계수·scope·유한 자원·대표 실제 D→E를 대상으로 하는 B03 재감사 범위를
심사하도록 요청하고, 100k 계측 시간 영향과 다섯 N grid는 별도 미완료 증거로 제시한다.**

“scoped 재감사 요청 가능”은 scope 심사 요청의 안전성 판단이다. 재감사 결과나 이전 추가 gate의 면제 승인이 아니다.

## 32. 최종 Git·증거

최종 HEAD/main/origin/main/실제 remote main은 시작 commit 그대로이며 index SHA도 같다.
변경은 허용된 test-server lifecycle와 새 P05 source·evidence·보고서뿐이다.
작업 트리는 의도적으로 DIRTY, commit NONE, push NOT PERFORMED다.
[summary.json](benchmarks/t66f-b03-ic01-p05/evidence/summary.json),
[final-state.json](benchmarks/t66f-b03-ic01-p05/evidence/final-state.json)에 마지막 검증을 남긴다.

## 필수 최종 상태

```text
T6.6F-B03-IC01-P05:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

IC01/P01/P02/P03/P04 WORK:
PRESERVED

ORIGINAL GIT INDEX:
PRESERVED

WORKTREE:
DIRTY — INTENTIONAL

COMMIT:
NONE

PUSH:
NOT PERFORMED

BINDING PROTOCOL:
UNCHANGED

PRODUCT SOURCE:
UNCHANGED

TEST-ONLY SERVER LIFECYCLE:
CHANGED

ORIGINAL P03 BACKEND:
DELETED

ORIGINAL P03 CLIENT DATABASE:
FAILED — 이번 재검증 불가: 재부팅 후 원 경로 부재; 손상 판정 아님

ORIGINAL STAGED OBJECTS:
397146 — 역사 증거

ORIGINAL REMAINING OBJECTS:
3386 — 역사 증거

BACKEND ARTIFACT PRESERVATION:
PASS — 소형 새 합성 fixture

CONSISTENT SQLITE BACKUP:
PASS

WAL CONSISTENCY:
PASS

ARTIFACT MANIFEST:
PASS

BACKEND DATABASE IDENTITY:
VERIFIED — 소형; 원 P03은 UNAVAILABLE

DATASET/EPOCH/TARGET IDENTITY:
VERIFIED — 소형; 원 P03은 UNAVAILABLE

GENERATION/SYNC_ROOT:
VERIFIED — 소형; 원 P03은 UNAVAILABLE

ORIGINAL VS RECONSTRUCTED:
새 P05 소형 원 backend의 사본; P03 복구·재구성 없음

RESTORED BACKEND AUTHENTICATED D3:
PASS — 정상 새 epoch; 옛 관측 409 거부

NORMAL SERVER CLEANUP:
PASS

FAILED-RUN ARTIFACT RETENTION:
PASS

CLIENT/BACKEND MATCH:
INCONCLUSIVE — 원 P03 실물 부재

MATCHED TAIL ELIGIBILITY:
NO

MATCHED TAIL RUN:
NOT RUN

MATCHED TAIL ON/OFF PAIRS:
0

FULL NEW 100K COLD RUNS:
0

ACTUAL HTTP COST:
소형 handler 합 OFF 22.286837s / ON 21.333572s; 원 tail 미측정

E2 COST:
독립 wall 미측정; 소형 실제 계수 검증

E1 COST:
독립 wall 미측정; 소형 실제 SQL payload 검증

EXTRA TIMING OBSERVER COST:
INCONCLUSIVE

LOGICAL COUNTER COST:
INCONCLUSIVE

HASH BYTE COUNTERS:
PASS — 실행한 보정 범위

VALIDATION BYTE COUNTERS:
PASS — 실행한 보정 범위

WRITE BYTE COUNTERS:
PASS — 실행한 보정 범위

GRAPH CLOSURE:
NOT EXERCISED — 원 tail; 소형 기능 시험 PASS

E3 RESUMED TERMINAL PATH:
NOT EXERCISED

E4 RESUMED TERMINAL PATH:
NOT EXERCISED

PREVIOUS ACCEPTED STATE:
PRESERVED — 역사 증거; P05 변경 0, 원 파일 현재 부재

PENDING FROZEN B/J:
PRESERVED — 역사 증거; P05 변경 0, 원 파일 현재 부재

IA01–IA07:
IMPLEMENTATION CORRECTIONS PRESERVED

P02 STATEMENT CACHE:
PRESERVED

SOURCE-SHA GUARDS:
PASS — 현재 6개 및 역사 복원 fresh 검사

SOURCE-LOCK POLICY:
COMPLIANT

B01:
CLOSED

B02:
CLOSED

NEW P05 TESTS:
21 PASS — 새 lifecycle 19개 + 기존 TLS assertions 재실행 2개
0 FAIL
0 SKIP

FULL BACKEND:
NOT RERUN — 역사 1436 tests / 1540 subtests PASS; fresh focused 214 PASS

FULL FLUTTER:
NOT RERUN — 역사 1690 PASS / 2 SKIP; fresh focused 73 PASS 및 소형 TLS 2 PASS

B03 INSTRUMENTATION CORRECTNESS REQUIREMENTS:
§35·§36 I25 측정 도구의 구현 측 보정 PASS; 독립 재감사 OPEN

PHASE B FULL-SCALE COST REQUIREMENTS:
§35 고정 H/D 다섯 N·§36 I25 실제 비용 증거 미완료

INSTRUMENTED 100K COLD COMPLETION REQUIREMENT OWNER:
IC01 §11·P03의 추가 실험 gate; binding §35 정상 경로 scaling과 구분; 면제 승인 없음

SAFE TO REQUEST SCOPED B03 RE-AUDIT:
YES — 범위 심사 요청만; 독립 PASS 아님

IC01 IMPLEMENTATION:
INCOMPLETE

SAFE TO RESUME FULL PHASE B COST GRID:
NO — INDEPENDENT VERIFICATION PENDING

T6.6F PHASE B:
STILL INCONCLUSIVE

ANDROID MEMORY SAFETY:
NOT VERIFIED

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

P05 TEMPORARY ARTIFACTS CREATED:
17개 / 0.046619 GiB — 추가 정리 registry 범위

P05 TEMPORARY ARTIFACTS DELETED:
17개 / 0.046619 GiB

ACTUAL DISK SPACE RECLAIMED:
0.046619 GiB

RETAINED P05 EVIDENCE:
244개 / 0.113422 GiB — 측정 시점의 evidence 디렉터리

PRE-EXISTING FILES DELETED:
0

ORIGINAL SQLITE ARTIFACTS:
재부팅 후 UNAVAILABLE — P05 변경·삭제 0

CLEANUP CANDIDATES REQUIRING APPROVAL:
NONE

P05 INFRASTRUCTURE VERDICT:
PASS — REPRODUCIBLE TEST-ONLY BACKEND ARTIFACT HANDOFF VERIFIED

ORIGINAL P03 MATCHED-TAIL VERDICT:
NOT RUN — COMPATIBLE ORIGINAL TARGET UNAVAILABLE

NEXT ACTION:
독립 검증자에게 IA01–IA07·정확 계수·scope·유한 자원·대표 실제 D→E의 B03 재감사 범위 심사를 요청하고, 100k 계측 시간 영향과 다섯 N grid는 별도 미완료 증거로 제시한다.
```
