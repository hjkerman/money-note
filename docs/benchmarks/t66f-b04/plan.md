# B04 실행 전 계약·측정 행렬

2026-10-26. 제품·규범·B03 계측 source 수정 없이 IC06 동결 복원본을 실행한다. IR07 correctness는 CLOSED다.

|구분|원본 요구|실행·판정 경계|
|---|---|---|
|바인딩|§35 H/D 고정, N=1000/5000/10000/50000/100000 no-change/card/cash 반복|아래 네 하위 N에서 순차 실행, 100000 제외. 숫자 H/D·반복 횟수·절대 latency 합격선은 규범에 없음|
|기존 실험 설정|seed662602, 평가일2026-10-05, current ledger105, 다른10개 table35행|N label은 ledger 총수, 전체 authoritative N+35. archive N−105. no-change hot87364B/control3178B 기준, 실제 각 target 크기도 보존|
|실험 설정|no-change D=0, 카드1002 또는 cash101의 고정 폭 amount UPDATE D=1|카드·현금은 각각 한 행 변경. 두 mode에 동일하게 확정된 target 전달|
|바인딩|§35 cold O(N) 허용|각 mode 빈 client DB의 실제 cold를 별도 계측. 정상 비용과 합치지 않음. backend bootstrap은 별도 ON 단일 측정|
|바인딩/계측 정의|실제 hash sink 입력, primary UTF8/JSON/C1 submitted/completed span|실제 B03 collector, 반복 입력은 반복 계수. structured visits는 별도 operation|
|바인딩/계측 정의|SQL NEW TEXT UTF8/BLOB payload, attempted/effective/committed/rollback|DELETE 신규 payload0, UPDATE NEW 전체; API bind·파일 성장·VFS와 별도|
|바인딩|§35 정상 full history fetch/hash/serialize/write0; flat P control 목록 없음|D3 및 E2/E3/E4 실제 counter, SQL table·stage 귀속과 source 경계로 확인|
|바인딩|§36 I25 steady-state full N 작업 MUST NOT|E3Verify/Prepare/Commit과 E2·cold 분리. 작은 N 성공은 large-N closure가 아님|
|바인딩|§16 Available부터 TTL 최대900초|실제 clock, 기존 fetch attempts3/observations3 및 packet64/1MiB 유지|
|바인딩|§25 exact accepted base·동일 coherent Target·원 ticket/final guard→COMMIT|원 AppState entry 실행. E4 actual accepted read, DB·generation/root/sequence 원문 보존|
|실험 진단|ON/OFF perturbation|동일 backend·TLS route·credential·runtime·target 및 별도 client DB. mode별 cold에서 같은 generation을 실제 취득. OFF 논리 counter는 null|
|추가 선호|순서 효과 파악|N별 cold 순서 반전, 정상 pair는 trial별 반전. OS cache 강제 flush 없음. backend cache는 oracle 후 warm 상태를 공통 사용|
|바인딩 미완료|rows read, HTTP/RTT, memory, median/p95·압축 대조|반환 rows/기존 work, HTTP entity·요청 수, HOST RSS 보존. 3회 표본 p95는 nearest-rank 기술 통계일 뿐 population 보증 아님|

## 규모와 제한

|N|실행 전 분류|근거|
|---:|---|---|
|1000|지금 안전하게 실행|별도 smoke 역할도 수행. cold1쌍, 정상3종×3쌍 목표|
|5000|직전 규모 feasibility 확인 필요|완료율·900초 관측·disk·scope closure 검사 후 시작|
|10000|직전 규모 feasibility 확인 필요|같음|
|50000|직전 규모 feasibility 확인 필요|현 환경 100GB 이상 여유; 기존 bounded profile 사용. 예측이900초×기존 최대3회 내 불가능하면 시작하지 않음|
|100000|명시 제외|이번 작업 새 full cold0회. 별도 승인 필요|

기존 raw는 방법·역사 비교에만 사용하며 현 동결 source의 완성 grid cell로 재사용하지 않는다. 비바인딩 중간 규모를 추가하지 않는다.

## 타이밍·표본

각 N에서 cold OFF/ON 한 쌍 후 no-change→카드→현금을3회 순차 반복한다. pair는 같은 확정 target, 같은 이전 target/sequence의 독립 DB를 사용한다. 둘의 로컬 generation UUID는 독립 생성되므로 UUID 자체 equality 대신 target·accepted 상대 sequence·원문 기록으로 비교한다. 두 mode의 authorityHistory request 카운터도 같은 횟수다.

backend generation은 mutation capture/finalize/commit과 bootstrap을 별도 ON 단일 측정한다. 동일 target을 두 번 생성하지 않으므로 generation ON/OFF pair로 오인하지 않는다. request handling 전체, CPU, D3 하위 경계, HTTP complete-body, SQL API·row callback 하한, publication transaction/readback, E4 read, 실제 AppState 반환 wall을 수집한다. E2 전용 wall과 exclusive Python callback CPU가 분리되지 않으면 미측정이라고 기록한다. 겹치는 구간을 더하지 않는다.

## 보존·중단

scratch `/tmp/money-note-t66f-b04-20261026/`: tree(동결 복원), disposable(DB), build, raw. 영구 evidence는 이 디렉터리의 raw/manifests/artifacts 하위에 보존한다. backend/client matched SQLite는 backup API로 보존 후 gzip하고 SHA를 기록한다. 활성 DB/WAL 삭제 금지.

각 규모 시작 전 source/fixture/runtime/auth/lease/disk/process/포트/collector/accepted 상태/새 로그 경로 확인. 경쟁 대형 작업·source 차이·scope 누락·환경 변화·안전 여유10GiB 미만이면 중단한다(10GiB는 운영 규범이 아닌 이번 task의 보수적 disk guard). 한 작은 N의 재현 실패면 자동 확대하지 않는다. 관측 만료는 기존3회 범위에서만 처리한다. 상위 task timeout은 N별 cold2회×기존관측2700초+setup/정상 여유의 유한 상한이며 observation 정책을 늘리지 않는다. 같은 실패 반복 금지.

## 1k 진단 뒤 실행 조건 보정

첫 1k cohort는 실제20 operation을 완료했으나 ON의9개 정상 실행 중8개에서 HTTP timeout/retry1건과 약15초 대기가 발생했다. backend 첫 요청 이전이며 순수 observer CPU가 아니다. 후속 비교에서는 양 mode 모두 operation 시작 전에 HTTP pool을 닫고 동일 TLS 설정의 새 pool을 사용한다. handshake는 실제 publish timer 안이다. warm 분류는 accepted DB/objects/provenance가 warm이고 transport 연결은 fresh임을 뜻한다. 기존 cohort는 진단 전용으로 보존하고 보정된 1k를 한 번만 실행한다. 각 trial 카드1001/1002/1003원·현금−51/−52/−53원으로 신규 내용 delta를 사용하며, 첫 cohort의 되돌림 cache 재사용과 섞지 않는다. 마지막 namespace BLOB 직렬화 오류는 B04 artifact 코드만 hex 보존으로 수정했다. 제품/B03 source와 관측 정책은 불변이다.

## 마지막 허용 규모의 추가 stage 진단

50k 정상 grid 뒤, 같은 두 accepted DB에서 no-change/card/cash 공개 API 진단을 각각 한 쌍 수행한다. E2 `acquire`의 API wall/기존 verification timer와 E3 `verifyPublicationCandidate` API/proof timer, `prepareGeneration` API wall을 직접 잰다. Prepare 뒤 discard하고 accepted identity/sequence 불변을 assertion한다. Guarded COMMIT를 수동 복제하지 않는다. 각 진단 target은 이후 원 AppState로 게시하되, 사전 취득으로 warm한 이 publication은 별도 진단으로만 기록한다. 정상 grid·cold 결과에는 포함하지 않는다. 실제 UI 설치 완료는 inactive segmented entry에서 제공하지 않으므로 미측정으로 남긴다.
