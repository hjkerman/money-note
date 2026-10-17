# T6.6F Phase B 후속 독립 검증

## 01. 대상과 판정

**INCONCLUSIVE — T6.6F PHASE B VERIFICATION STILL BLOCKED**.
Backend의 의무 N 5개 지점에서 고정 H/D 반복·오프라인 full 압축 비교를 완료했고,
새 binding 기능/부정/권한/DB identity 사례는 **33 PASS**다. 규범 밖 Content-Type 거부 진단은
**1 FAIL**이며 그대로 보존했다. Backend 전체 **1,315 tests / 1,540 subtests PASS**,
Flutter 전체 **1503 PASS / 0 FAIL / 2 SKIP**다.

그러나 현재 E2의 지원 상한은 100,000 objects이고 실제 50k/100k generation은 각각
200,331/400,532 objects다. 따라서 전체 D→E 및 E3 I25/storage/resource의 의무 grid를
완료했다고 선언할 수 없다. 추가로 전층 논리 hash/validate/write byte accounting, actual Android proof와
R1 상위 exit 증거가 남는다. 확정 Critical/High/Medium 제품 correctness 결함은 새로 발견하지 않았다.
증거 부재를 제품 결함이나 PASS로 바꾸지 않는다.

원시 자료는 [manifest](benchmarks/t66f-phase-b-continuation/evidence/manifest.json), 전체 mapping은
[coverage-final.json](benchmarks/t66f-phase-b-continuation/coverage-final.json)에 있다.
**IMPLEMENTATION-SIDE CLAIM**은 구현 보고서의 완료·성능 요약이며 독립 raw evidence 없는 값으로
gate를 통과시키지 않았다. **UNVERIFIED REQUIREMENT**은 남은 의무 grid와 hash/write/resource proof다.
아래 **PRIOR INDEPENDENT EVIDENCE**와 **NEW PHASE B CONTINUATION EVIDENCE**를 구분한다.

## 02. 저장소 identity

시작 HEAD/main/origin/main/실제 remote main은 모두
`a08b91d9625ad685cea9ab8d0e977849a097f0ab`였다. clean worktree를 확인한 뒤 새 감사 자료만 만들었다.
시작 tree는 `e6b8c3cbe4f544a81147c2f1a0911f18d662a62f`다. 현재 제품은
`af9525e20e6df1dd7dfc152d3db79c1eb07925d2`와 같다. `c479a379..a08b91d`의 제품 경로
`backend/app`, `backend/isolated_sync`, `mobile/lib`, `frontend/src` diff는 없다.
시작 및 commit 전 refs·tree·actual remote와 보호 파일 SHA는 `repository.json`과
`preservation.json`, `protected-hashes.json`에 보존한다. push 뒤 종료 refs/clean은 최종 응답에서 별도 확인한다.
감사 commit은 이 보고서를 추가한 commit이며
`git log -1 --format=%H -- docs/t66f-phase-b-continuation.md`로 정확히 식별한다.

## 03. Phase A closure

**PRIOR INDEPENDENT EVIDENCE**: `a7d045f3`의 최종 RA01 재감사 29 PASS와 원 세 반례 PASS,
E4-A01/E4-RA01 CLOSED를 이월한다. `docs/t66e4-independent-audit.md` 및 A01 재감사의
역사적 FAIL은 수정하지 않았다. 이번 전체 Flutter에는 mobile/test 아래 E4·A01/RA01 구현의
authority·monetary·pin·lineage 회귀가 포함된다. docs 아래 원 독립 45개/29개 및 Python crash wrapper
전부를 이번 full Flutter가 재실행했다고 주장하지 않는다. 이월은 원 증거의 감사 범위에 한정한다.

## 04. B01 closure

**PRIOR INDEPENDENT EVIDENCE**: B01의 15개 독립 사례, 두 전체 backend PASS,
test-local supported 5초와 production 1초 불변을 이월한다. 이번에도 원 backend 전체가 PASS다.
기존 독립 Python 14개와 별도 Flutter quota I10을 다시 실행했고 새 독립 수에 합산하지 않는다.
원 assertion `assert sorted(r.status_code for r in results) == [201]*4+[429]`는 그대로이며
503을 허용하지 않는다. 두 역사적 Phase B 실패의 HTTP body는 여전히 없다.
이번 결과로 그 두 실패의 원인을 소급 확정하지 않는다.

## 05. 이전 Phase B 증거

**PRIOR INDEPENDENT EVIDENCE**: `c479a379`의 새 독립 49 PASS, 실제 child SIGKILL 7 PASS,
권한/race 10 PASS, 실제 TLS D3a/manifest/D3b/E1–E4/full financial oracle,
Frozen B/J 및 A01/RA01 보존을 원 범위로 이월한다. 제품과 원 harness가 불변이므로 모든 49개를
다시 실행해 새 case로 부풀리지 않았다. 기존 실제 HTTP 3개와 B01 quota 1개는 선택 재검증했다.
원 보고서의 backend FAIL 및 INCONCLUSIVE를 지우거나 새 PASS로 덮지 않았다.
실제 문서 inventory에서 D1–D3b는 `docs/t66/d/implementation/`의 구현 보고서이며,
전용 독립 감사 문서가 있다고 꾸미지 않는다. 별도 backend 독립 보고서는 실제 존재하는
`docs/t66/d/audits/`의 D3c/A01와 원 Phase B 독립 HTTP/SQL 증거를 구분해 사용한다.

## 06. 적용 규범

원본은 `docs/t66/c/t66c-delta-sync-protocol.md` 전체다. 별도 F 전용 규범은 발견하지 않았다.
§22/24/25/26/29/31/34/35와 I1–I25, §37 negative 34개, §38 proof 12개를 대조했다.
§34의 R1 → interoperability/full-resync/crash → fixed H/D·compression → F → rollout 순서를
임의로 축약하지 않는다. `sync_root`는 Snapshot v7 `state_fingerprint`가 아니다.

## 07. 전체 coverage matrix

`coverage-initial.json`은 대규모 실행 전 계획이다. `coverage-final.json`은 **39절/25 invariants/
34 negative 계획/12 implementation proofs**를 각각 A–F 중 하나로 분류한다.
A는 명시한 범위의 독립 이월·새 증거, B는 회귀 필요, C는 현재 F 필수 미검증,
D는 R1 소유, E는 환경/기기, F는 규범 충돌이다. 새로운 규범 충돌은 확인하지 않았다.
행이 존재한다는 사실이나 기존 구현 테스트 재실행을 새 독립 주입의 증거로 부르지 않는다.
기존 regression-only 및 shared implementation oracle의 한계도 각 scope에 유지한다.

## 08. F와 R1 소유권

현재 F는 구현된 D/E interop·authority·durability·incremental 성능을 검증한다.
Large Restore/MW, chunk/hash/bounded staging, backup/artifacts/retention, atomic apply/receipt,
migration/rollback은 §31/33/34의 R1/transition 소유다. 이를 E4 결함으로 분류하지 않는다.
다만 전체 F의 상위 dependency에서 제거하지도 않는다. R1 소유 코드나 대체 복구 proof를 만들지 않았다.

## 09. H/D/N 정의

규범 §35 그대로 **N=전체 역사 row**, **H=hot/참조 working set와 required control/policy descriptor 크기**,
**D=base 이후 changed rows**다. L은 영향 leaf, P는 전체 leaf, E는 영향 reverse/constraint facts,
B는 전송·검증된 changed bytes다. 정상 목표는 O(H+B+L log P+256E)이며 모든 연산 O(1)을 요구하지 않는다.
숫자 H/D, repetition·warmup 수, percentile 방식, 절대 latency threshold는 규범에 없다.
새로운 의무 수치로 만들지 않고 실험 설정을 공개했다.

## 10. 의무 grid와 완료 범위

N=1k/5k/10k/50k/100k **5개**다. Backend는 모두 실행했다. 아래는 각 최초 generation을
별도 SQL의 typed child walker·SHA로 재구성한 결과다. 클라이언트 자신의 object list를 expected로 쓰지 않았다.

|N|도달 객체|도달 bytes|full bundle|gzip6|Brotli4|
|---|---|---|---|---|---|
|1000|4132|2749721|649444|20761|11012|
|5000|20148|13146158|2877441|71847|29821|
|10000|40170|26160538|5663442|134823|52450|
|50000|200331|130710592|28103439|648149|230120|
|100000|400532|261543083|56154440|1288409|454351|

큰 두 N의 전체 D→E는 지원 E2 한도 때문에 미실행이다. Backend 5/5와 전체 D→E 3/5를
혼동하지 않는다. 3개 client grid는 별도 fixed H profile이며 backend H=105와 latency를 직접 합산하지 않는다.

## 11. fixture

Backend는 기존 `t66d2b_writers.py` seed 662602·평가일 2026-10-05와 current ledger 105행을 고정했다.
archive=N−105이고 cash/panel/settings/labels 및 descriptor도 고정했다. hot 87,364B,
control 3,178B가 모든 N의 no-change에서 같다. D=0 또는 단일 행 UPDATE D=1이다.
두 값 전환은 ABA 재사용이다. 삭제/split/여러 leaf·large delta correctness는 앞선 독립 G1–G7
및 기존 tree/property 회귀의 범위로 이월하고 이 ABA를 새로운 대규모 delta cost로 부르지 않는다.

Client unique fixture는 현재 ledger 1개와 고정 참조 profile, 정확한 전체 N=1k/5k/10k,
서로 다른 고정 폭 금액 D=1이다. 매회 새 immutable가 만들어지고 실제 object HTTP가 필요함을
별도 assertion으로 확인한다. 기존 history 인수 1k/5k/10k인 ABA 보조 실행은 실제 ledger
1,001/5,001/10,001임을 명시한다. 원 보고서의 N과 혼동하지 않는다.

## 12. cold

Backend bootstrap은 각 N 한 번의 실제 시간/DB size/RSS를 기록했다. 이것으로 median/p95를 만들지 않는다.
실제 cold Flutter 전송은 보조 1,001행의 기존 store-free 경로 1회다. 나머지 warm-cache fixture는
E1 개별 bytes 검증과 동일 스키마/trigger를 통과한 객체만 측정 밖에 준비한다. accepted/receipt/source/
pending을 직접 삽입하지 않고 실제 original-ticket E2/E3를 통해 최초 accepted를 만든다.
서버 fixture clock이 고정되어 긴 cold 실행은 실제 TTL 내 완료 성능 proof가 아니다.
대형 cold와 전체 resource grid는 미완료다.

## 13. 동일 generation

Backend no-change는 모든 N에서 1,120 execute와 4,528 반환 행으로 같았다. control은 flat P 목록이 아니다.
지원 client 세 N의 identical 반복은 실제 SQL 796, object HTTP 0, full verification 0이다.
새 accepted generation metadata의 root pin 4 INSERT/4 DELETE와 repeated Frozen의 pin write 0을 구별한다.
같은 root라도 새 observation identity에 해당하는 generation metadata 변경을 숨기지 않는다.

## 14. 작은 delta

Backend no-change/card/cash 비용은 다음과 같다. 반환 행은 SQLite VM/pager 전체 read rows가 아니다.
EXPLAIN QUERY PLAN도 원시 자료에 남겼고 역사 행 전체 SELECT가 정상 경로에 새로 들어가지 않았다.

|N|no-change SQL/행|card SQL/행|cash SQL/행|
|---|---|---|---|
|1000|1120/4528|2385/8729|2439/8515|
|5000|1120/4528|2401/8745|2446/8522|
|10000|1120/4528|2410/8754|2449/8525|
|50000|1120/4528|2432/8776|2459/8535|
|100000|1120/4528|2435/8779|2465/8541|

지원 client에서 매회 새로운 금액으로 바꾼 결과는 다음과 같다. 실제 독립 SQLite delegate와
ASGI response capture를 사용한다. 각 정상 반복은 warmup 3개 제외 후 20개다.

|정확한 N|상태|no-change SQL|card SQL / object HTTP|cash SQL / object HTTP|Frozen SQL / bytes|
|---|---|---|---|---|---|
|1000|PASS|796|1727 / 16|1658 / 16|66 / 9703|
|5000|PASS|796|1999 / 21|1858 / 21|66 / 9703|
|10000|PASS|796|2079 / 23|1898 / 22|66 / 9703|

## 15. 큰 delta와 구조 변경

이전 실제 HTTP G1–G7의 여러 leaf/change/delete/구조 변경·canonical equality는 유지된다.
전체 suite의 B+tree/Patricia random/split/delete/reverse property도 PASS다. 이들은 모든 N에서
새 대규모 delta latency/메모리 표본을 만들었다는 뜻이 아니다. 두 큰 N의 정상 acquisition부터
지원되지 않으므로 해당 경로의 E3/E4 비용을 우회 삽입한 accepted pointer로 측정하지 않았다.

## 16. 압축

위 grid 표의 full bytes는 실제 backend authoritative bundle JSON bytes이고 gzip6/Brotli4는
각 3 warmups/20 samples, decompress exact equality와 SHA를 확인한 **오프라인 비교**다.
기존 T6.6A 10k full gzip 108,916B/Brotli 43,033B와 fixture가 달라 동일 수치라 주장하지 않는다.
새 10k full gzip 134,823B/Brotli 52,450B는 hot 단독 87,364B보다 작거나 비교할 만하며,
무압축 hot만으로 전송 개선을 주장할 수 없다. T6.6A 다양한 문자열 gzip 568,847B도
역사적 별도 control로 유지한다. 새 다양한 문자열 전체 N grid는 생성하지 않았다.
제품 Content-Encoding이나 request compression을 도입하지 않았다.

## 17. median/p95

모든 표본을 보존하고 실패를 조용히 제외하지 않는다. `perf_counter_ns`/Dart monotonic Stopwatch,
3 warmups, 측정 20개, arithmetic middle median, nearest-rank ceil(.95*n)을 사용한다.
이는 유한 표본의 empirical p95이며 모집단 tail의 신뢰 보장이 아니다. cold n=1과 fallback n=1은
따로 기록한다. Backend writer/finalizer+observation total의 host 분포는 아래와 같다.
generation/http 별도 분포와 min/max/stdev는 JSON에 있고 포함 관계가 있는 timing은 더하지 않는다.

|N|no-change median/p95 ms|card median/p95 ms|cash median/p95 ms|
|---|---|---|---|
|1000|1089.41/1170.34|3166.25/3606.21|1363.42/1786.8|
|5000|867.39/1069.65|3296.51/3622.39|1297.15/1743.94|
|10000|683.27/1143.15|2160.86/3032.23|1126.42/1818.34|
|50000|732.72/841.94|2207.21/2300.42|1094.33/1150.71|
|100000|582.97/612.45|1836.28/1957.35|906.26/995.32|

Client 분포는 `evidence/cost-summary.json`의 microseconds다. 해당 client total은 E2/E3와
generation-pinned E4 logical read를 포함하나 explicit legacy/frozen installation은 정상 반복 밖이다.
backend generation mutation은 client timer 밖이라 두 다른 H profile의 시간 합을 end-to-end latency라고
부르지 않는다. 단계별 단독 E1/E2/E3 시간은 전부 분리 관찰되지 않았으며 빈 값을 추정하지 않았다.

## 18. 환경

**SYNTHETIC HOST MEASUREMENT**다. Linux, Intel i7-8750H 2.20GHz/12 logical CPU,
Python 3.12.3/Backend SQLite 3.45.1, Dart native SQLite 3.53.4, Flutter 3.47.4/Dart 3.13.3,
메모리 약 23GiB, 같은 HOST ext4 임시 파일시스템이다. exact OS/runtime/fs와 version JSON은
`evidence/environment.json` 및 `native-environment.json`에 있다. Backend profile WAL 및 client DELETE/EXTRA/FK를 확인했다.
여러 회귀/측정이 병행했고 CPU affinity/thermal isolation이 없어 지연 역전도 N 성능 향상으로 해석하지 않는다.
Android device 또는 production throughput 주장이 아니다.

## 19. HTTP accounting

Backend grid는 실제 Uvicorn loopback TCP, client는 실제 TLS server와 실제 MoneyNoteApiClient/IOClient다.
ASGI receive/send에서 요청·response entity·status·decoded base64 object 크기 및 hash 목록을 관찰했다.
payload bytes와 header field 합을 IP/TCP/TLS packet bytes로 부르지 않는다.
no-change manifest entity는 1,534–1,536B, header fields 166B이며 request/RTT 횟수는 원시 자료에 있다.
client unique 정상 변경은 실제 object request가 존재하고 ABA warm repeat는 object request 0이다.
각각의 reuse/transfer 집합과 client object contents를 최종 별도 SQL/full oracle로 대조했다.

## 20. Backend object/SQLite accounting

`Meter`는 실제 ObservationConnection.execute를 delegate하여 SQL 종류·fetch 반환 행·반환 BLOB을 센다.
관찰값은 제품 counter가 아니다. SHA/domain/declared size/typed descendants는 별도 SQL oracle로 확인했다.
다만 bound BLOB 길이는 실제 bytes written·unique dirty pages가 아니고 SQL 횟수는 VM instruction이 아니다.
계측기의 `sync_pins` 문자열은 실제 observation pin table 이름을 포괄하지 않아 pin 수 근거로 쓰지 않았다.
Backend grid 표의 active 구간은 writer/finalizer와 observation POST이며 이후 lease DELETE와 full oracle는 제외한다.
반면 client total은 E2의 terminal observation retry와 release를 포함한다. 두 경계를 중복 합산하지 않는다.
backend 전체 hashing 입력과 실제 논리적 insert/update bytes의 독립 accounting은 미완료다.
이 필수 byte 증거를 wall-clock으로 대체하지 않았다. 물리 pager write/I/O는 별도의 추가 관찰 한계이며,
§35의 논리 bytes written을 넘어서는 새 HOST F 필수 threshold로 만들지 않는다.

## 21. E1/E2 저장

native SQLite delegate는 statements, returned rows, object BLOB bytes, raw/index 접근,
objects/edges/staging/generation root mutations를 실제 실행 경계에서 관찰한다. store와 accepted 참조는
별도 연결로 검사한다. warm cache 초기 생성은 공개된 test fixture이며 저장 성능 표본에 포함하지 않는다.
실제 cold 보조 실행은 모든 object가 E1 validation을 통과한다. 한도를 올려 50k/100k를 강제로
허용하거나 partial graph를 complete로 게시하지 않았다. `FetchLimits(graphObjects:100001)` 자체가
`FETCH_LIMIT_INVALID`이며 실제 graph walker도 maxObjects를 적용한다.

## 22. E3 I25

§36 I25의 정확한 요구는 **steady-state full N 작업 MUST NOT**이며, §25/35는 accepted provenance와
changed frontier를 사용해 정상 whole graph 재검증·hash·full rewrite를 피하도록 요구한다.
cold/restart/epoch와 필수 recovery full fallback은 정상 반복과 다르다. 이전 142→1,728 objects,
237 SQL/4 pin INSERT는 특정 fixture의 historical evidence다.

새 실제 D→E 측정의 supported 세 N에서 identical SQL 796과 full verify 0,
localized unique delta의 bounded SQL/object HTTP, root pin I/D 각 4가 확인된다.
이 수치를 E3 verifier 단독 237과 직접 비교하지 않는다. E2/E3/E4를 포함하는 다른 경계다.
추가 E3 current publication 중 Frozen G1 유지, fresh handle fallback도 관찰했다.
하지만 큰 두 N과 전층 hash/write byte 증거가 없어 **전체 I25 grid verdict는 INCONCLUSIVE**다.
실행 가능한 세 점의 bounded 증거를 전체 N의 증명으로 확대하지 않는다.

## 23. Frozen-B 반복

보조 ABA 세 N의 repeated Frozen은 **66 SQL / 9,529B**, unique fixture는 위 client 표와 같다.
기존 64/9,451은 다른 lineage/fixture의 수치다. 새 safety metadata와 문자열 길이를 포함한 실제 관찰값을 쓴다.
20개 healthy 반복에서 raw/index 접근·full verify·full frozen recovery·legacy full read·lineage hash 및
pin I/D/U는 모두 0이다. unrelated E3 acceptance 뒤에도 Frozen G1을 유지한다.
새 SQLite handle에서는 필수 full fallback이 발생하며 정상 반복과 별도 기록한다.
이는 fresh-process 비용 표본이 아니라 fresh-handle 비용이다. 실제 fresh-process readability는
이번 negative/이전 crash 사례의 별도 child 결과를 이월한다. 50k/100k 비용은 미측정이다.

## 24. 전층 resource와 storage

Backend와 client SQL은 서로 다른 포함 경계를 표시하고 단순 합으로 읽기/쓰기 byte 총량을 만들지 않는다.
per-process ru_maxrss, Dart currentRss, DB/main/WAL/SHM 크기를 기록했다. client RSS에는 test fixture와
oracle도 포함되고 high-water isolation·physical I/O·temporary peak disk 전체 추적은 아니다.
cold와 restart full verification, normal changed frontier, explicit legacy materialization 비용을 구별한다.
HOST 보조 cold 1회 및 warm cache 세 N을 production 최대 resource 안전성으로 일반화하지 않는다.
전층 필수 accounting의 미관찰 부분과 두 큰 N은 여전히 미완료다.

## 25. 새 권한·경합

**NEW PHASE B CONTINUATION EVIDENCE**: 실제 D3a 응답 barrier 뒤 same-user reauth,
different user, financial mutation, newer segmented request, Offline, credential replacement, logout 7개와
E3 acceptance/legacy materialization 뒤 mutation/Offline/token 6개, 원 lineage lock 대기 중
principal 변경 1개로 **14 PASS**다. 취소 Future만 보지 않고 accepted/source/B/pending/installed/frozen
SQL 및 파일을 비교했다. legitimate financial mutation의 journal 추가는 허가된 변화로 별도 확인한다.
E3 accepted는 integrity cache로 남아도 설치 authority를 대신하지 못한다.

newer segmented 요청은 같은 store E2 single-flight 때문에 먼저 `ACQUISITION_BUSY/retry_same`이며
old ticket은 이미 stale이다. old가 끝난 뒤 fresh 원 request로만 새 취득한다. 초기 fixture가 B의 즉시
성공을 잘못 기대한 FAIL/뒤따른 cleanup error도 보존했고, 이 정확한 contract로 별도 결정적 재실행했다.
old candidate에 fresh ticket을 붙이지 않는다. 전체 18-row 모든 조합을 새 real HTTP case로 전수 증명했다는
주장은 하지 않는다. 기존 51 authority/race 및 source guard proof는 전체 Flutter에서 회귀했다.

## 26. 새 부정 protocol

dataset, unsupported canon, base echo, invalid context, ref size, invalid base64, chunk length,
duplicate chunk, unexpected 206, missing descendant의 **10 PASS**다. 실제 backend의 올바른 출력을
ASGI 경계에서 독립 변조했다. 정상 backend가 그런 bytes를 생산한다고 주장하지 않는다.
각 rejection 뒤 accepted/source/pending/legacy/pins를 exact 비교하고 같은 client의 후속 valid 취득과
기존 Frozen의 fresh child read를 확인했다. 원시 ID→injection→error→durable state→wire는
`evidence/cases.json`, `negative-final.json` 및 gzip machine 로그에 있다.

Content-Type 하나는 별도 진단 **1 FAIL**이다. 실제 valid canonical JSON을 text/html로 보낸 결과
client가 받아들였다. §4/15의 버전/body 규칙에 MIME 거부 의무가 없고 기존 E2-A01 문서도
Content-Type acceptance rule을 새로 만들지 않았다고 명시한다. 본문 hash·typed 검증이 유효하며
old Frozen/pending/lineage가 보존된 상세 before/after/wire를 따로 남겼다.
거부를 요구했던 감사 assertion을 PASS로 고치거나 그 FAIL을 숨기지 않는다.

## 27. DB identity

새 **7 PASS**: A에서 시작한 manifest retry/object/release가 authentication·serialization 또는
실제 release terminal barrier에서 같은 logical namespace의 물리 B로 교체된다. A의 오래된
요청은 500 STORAGE_FAILED로 거부되고 B의 행·financial digest가 불변이다. A를 복원하거나
B의 새 정당한 요청을 보내면 정상 동작하고 actual permit capacity가 복구된다.
old pinned manifest를 유지한 채 new generation을 만든 별도 case는 old bytes/target coherent,
active pin 5/inactive pin 5를 확인한다. inactive marker를 active retention owner로 세지 않았다.
예전 backend identity/permit corrections와 B01 source는 변경하지 않았다.

초기 감사 fixture는 release에 존재하지 않는 serialized hook을 기다렸고, total pin 10개를 active
5개와 혼동했다. 이 **초기 5 PASS/2 FAIL**도 보존한다. 실제 terminal hook과 active/inactive 각각의
정확한 assertion으로 고친 새 감사 fixture는 7 PASS이며 제품 correctness assertion을 완화하지 않았다.

## 28. crash/recovery

이전 독립 Phase B의 실제 SIGKILL 7개와 E4 process crash 36개 증거를 이월한다.
이 중 backend after_finalize와 실제 TLS native_before_commit 두 boundary를 선택해 다시 실행했다.
실제 child 종료와 별도 process의 durable roots/source/pins/B/pending/read를 검사한 기존 시나리오의
회귀 2 PASS이며 새 독립 crash 시나리오로 세지 않는다.
이번 비용 측정의 h.reopen은 actual process kill로 세지 않는다. 새로 설계한 child SIGKILL 시나리오는 0이다.
새 negatives는 fresh-process read를 수행하지만 crash 주입 자체는 아니다.
임시 source compilation을 중단한 개발용 SIGINT도 crash test 수에 넣지 않는다.
host SIGKILL로 hardware power-loss proof를 만들지 않는다. 큰 N의 complete path가 없으므로
그 범위의 crash matrix 역시 새로 완료하지 않았다.

## 29. Frozen B/J

Unknown pending을 가진 기존 G1 Frozen을 먼저 설치하고 negative/권한 실패/새 acceptance를 실행했다.
pending bytes·ID·순서/source·frozen lineage를 보존했다. 서버 transaction과 비슷한 pending만으로
ACK/retire하지 않는 이전 독립 시나리오와 이번 원 handoff 회귀도 유지한다.
원 RefreshCoordinator/ticket과 session/mutation/mode guard, E4-A01 recovery ownership SQL CAS,
RA01 previous_source의 durable 조건은 제품 source가 같다. 자동 B/J rebase·암묵적 ACK는 없다.

## 30. v7/v4·금융 의미

필수 `"\u001c+0001000.00\u001f"`를 실제 backend monetary validator와 E1 C1 literal/hash oracle로
확인했다. authoritative reader는 1000으로 해석하면서 raw codepoint를 보존하고 local exactMoney는
원래대로 거부한다. client 금융 projection을 재계산하지 않았다. 실제 backend exporter의 full 내용과
Snapshot v7/OfflineBaseline v4 별도 lineage oracle를 이월했다. `sync_root` 대입/normalize,
floating point monetary conversion, fabricated baseline envelope를 추가하지 않았다.

## 31. Android/device

§26/§38 proof 8의 actual Android driver/VFS/pragmas·I/O failure·power-loss 증거는 없다.
rollout을 차단한다는 규범을 유지한다. host SQLite DELETE/EXTRA나 debug APK build가 이를 대신하지 않는다.
§35의 device 절대 latency는 post-T6.6 gate 전 정하지 않으므로 임의 threshold 미달이라는 defect도 만들지 않는다.
실기기 성능은 later environment gate다. 현재 전체 F proof를 모두 완료했다고 주장할 수 없다.
APK 설치·physical device 접근은 하지 않았다.

## 32. R1

capabilities는 기존 isolated subset의 404를 유지한다. full R1 지원을 광고하지 않는다.
Large Restore/MW/chunk/hash/bounded staging/backup/apply/receipt/migration/rollback은 DEFERRED다.
현재 legacy restore budget을 우회하거나 segmented B를 Offline-ready로 표시하지 않는다.
R1 구현 승인은 이 감사의 범위가 아니며 시작하려면 실제 stage prerequisites와 별도 명시 작업이 필요하다.

## 33. Backend 전체

명령은 backend cwd의 `../.venv/bin/python -m pytest -q --junitxml=...`이며 새 process의 실제 exit 0이다.
**1,315 tests / 1,540 subtests PASS**, JUnit testcases 합 2,855, failures/errors/skips 0,
2,796.29s다. Starlette/httpx 기존 deprecation warning 1개가 있다. 원 concurrency assertion과
test-local 5초가 그대로 포함된다. 이번에는 full backend 1회, B01의 이미 검증된 두 전체 실행은
historical evidence로 구분한다. 새 DB identity 7개 및 B01 독립 Python 14개는 docs 경로라 이 수에 자동 합산되지 않는다.

## 34. Flutter 및 기타 회귀

`flutter test --no-pub --machine --concurrency=2`: **1503 PASS/0 FAIL/2 SKIP**, exit 0.
machine의 visible success 1,505에는 skipped 2개가 포함돼 이를 성공 1,505개로 부풀리지 않았다.
기존 E1/A01/A02·E2/A01·E3/I25·E4/P0/A01/RA01·Snapshot/offline/coordinator 회귀가 포함된다.
Flutter analyze, debug APK build(설치 없음), npm frontend build, Ruff, compileall은 실제 exit 0이다.
새 Python/Dart 파일만 formatter를 적용했고 실행된 이전 버전도 gzip 보존했다.
기존 파일의 알려진 format 차이를 일괄 수정하지 않았다. 최종 changed-file formatting과
`git diff --check` 결과를 마지막 preservation 자료에 기록한다.

## 35. Findings

**F-BC01 / INFORMATIONAL — 의무 큰 N과 현 지원 object budget의 불일치.**
위치 `mobile/lib/src/segmented/fetch.dart:28,47,347`, `graph.dart:206,263`; 요구 §35/I25의 전체 grid.
50k actual SHA/typed SQL oracle는 raw/index 200,329 및 hot/control 포함 최소 200,331을 보여주지만
FetchLimits는 100,000 초과를 configuration 단계에서 거부한다. 100k graph도 400,532다.
`profile_test.dart`와 `evidence/budget-50000.json`로 독립 재현한다. 의도된 resource rejection 자체를
데이터 corruption/권한 결함으로 부르지 않는다. 영향은 필수 두 grid의 통합 비용 proof 미완료다.
최소 후속 조치는 지원 profile/필수 규모의 정합성에 대한 별도 승인된 검토와 필요한 제품 변경의 재감사,
그 후 같은 grid 재측정이다. 이번 감사에서 제한을 올리거나 스펙을 축소하지 않았다. Phase B PASS를 차단한다.

**F-BC02 / INFORMATIONAL — 비규범 MIME 거부 diagnostic.**
위치 `adversarial_test.dart` C-N-content_type, 기존 E2-A01 implementation 문서 372행.
valid body와 text/html을 주입했을 때 rejection을 기대한 감사 assertion이 실패했다.
before/after/wire/기존 Frozen fingerprint를 별도 gzip에 보존한다. 기대가 기존 binding contract보다 엄격하므로
새 제품 correctness blocker는 아니다. minimal action은 진단 범위를 명시하는 것이며 제품 parser 변경이 아니다.
기존 strict diagnostic assertion은 그대로다. Phase B 미완료의 근거는 F-BC01과 필수 미확인 proof다.

새 Critical 0/High 0/Medium 0/Low 0, INFORMATIONAL 2다. B01 및 A01/RA01은 OPEN으로 되돌리지 않는다.

## 36. 한계와 실패 기록

새 고유 ID **33 PASS / 1 비규범 diagnostic FAIL**이며, 14 authority/10 binding negative/7 DB/2 profile다.
샘플 반복과 기존 implementation tests를 새 case로 세지 않는다. benchmark profile은 현재
**11 PASS / 2 INCOMPLETE**이며 이것이 전체 cost gate PASS라는 뜻은 아니다.
초기 compile/fixture 오류, supersession single-flight 오류 및 뒤따른 cleanup error는 raw logs로 보존한다.
자동 승인 검토가 한 차례 fingerprint exact oracle를 느슨한 존재 검사로 바꾸는 제안을 거부했다.
그 제안은 적용하지 않았고 원 Frozen fingerprint의 exact equality를 사용해 해결했다.
형식 정리 전 source, 실제 실행 명령/exit/JUnit/machine 및 raw JSON은 `evidence/manifest.json`로 해시 결합한다.
유한 schedule·입력 언어 전부, production 자원 규모, Android durability를 증명했다고 주장하지 않는다.

## 37. 이전 INCONCLUSIVE 재조정

|원 항목|이번 증거|최종 범위/상태|
|---|---|---|
|전체 backend 실패|B01 독립 closure + 이번 1,315/1,540 exit 0|PASS; 원 FAIL 역사 보존|
|fixed H/D 전체 N|backend 5/5 실제 측정, client supported 3/5|전체 D→E INCONCLUSIVE|
|compression/median/p95|5개 full bundle offline gzip/Brotli, 3+20 실측|해당 HOST 경계 PASS; cold/device로 확대 안 함|
|추가 authority/negative|14 race, 10 binding negative, 독립 SQL/fresh child|선택 추가 경계 PASS; 비규범 MIME FAIL 분리|
|backend DB identity|새 7개 + B01 회귀|검증한 replacement/permit 경계 PASS|
|E3 I25|세 supported N의 native SQL/object/root-pin 및 fallback|큰 N·전층 hash/write 미완료, INCONCLUSIVE|
|E4 repeated Frozen|세 supported N의 20 repeats 및 unrelated acceptance|관찰한 범위 PASS; 큰 N INCONCLUSIVE|
|전층 resource/storage|실제 HTTP/SQL/BLOB/DB sizes/RSS|큰 N과 전층 논리 byte accounting 미완료, INCONCLUSIVE; physical I/O/pure peak는 추가 한계|
|Android VFS/I/O/power|새 증거 없음|필수 rollout proof 미확보; HOST 대체 금지|
|R1/migration/rollback|제품 미변경/closed gate|DEFERRED; 상위 전체 F exit 미충족|

## 38. 전체 F 결정

Phase B는 INCONCLUSIVE다. 현재 필수 미검증을 3개 묶음으로 명시한다:
① 50k 전체 D→E/I25/storage/resource, ② 100k 같은 경계,
③ 전체 정상 경로의 논리 bytes hashed/validated/written에 대한 독립 accounting.
§35의 memory는 HOST RSS로 보고했으나 큰 두 N의 client resource는 미관찰이다.
물리 I/O 또는 fixture와 분리된 순수 peak를 관찰하지 못한 사실만으로 새 필수 F gate를 추가하지 않는다.
아울러 §38 actual Android proof와 §31/33/34 R1 dependency는 전체 F/activation exit에서 미충족이다.
따라서 **SAFE TO DECLARE T6.6F COMPLETE: NO**다. 정상 작은 fixture 기능 PASS만으로 상위 exit를
SATISFIED로 만들지 않는다. 확정 correctness/cost violation이 없다는 사실도 missing proof를 대체하지 않는다.

## 39. 기본 앱·activation

제품 source/config 변경 0, default startup/financial reads/writes/authentication/legacy refresh가 그대로다.
production SQLite user_version 4, Snapshot v7, OfflineBaseline v4, Frozen B/J 입력-only 및 backend 금융
authority를 보존한다. synthetic direct entry points를 ordinary read path에 연결하지 않았다.
R1 gate CLOSED, general-user segmented Offline NOT ACTIVATED, production segmented activation
NOT PERFORMED, deployment/APK installation NOT PERFORMED다. 운영 DB/API/service를 조사하지 않았다.

## 40. 감사 commit/push

새 `docs/benchmarks/t66f-phase-b-continuation/` 및 이 보고서만 명시 stage한다.
제품과 과거 자료 보호 SHA를 다시 확인하고 staged name allowlist 및 diff check 후 audit-only commit을
main에 push한다. force push/history rewrite는 없다. 실제 마지막 refs/remote/clean 상태는
감사 완료 메시지 및 `git log`로 검증한다. commit/push는 deployment 승인이 아니다.

## 필수 최종 상태

```text
T6.6F PHASE B CONTINUATION:
INCONCLUSIVE

STARTING B01 AUDIT COMMIT:
a08b91d9625ad685cea9ab8d0e977849a097f0ab

ORIGINAL PHASE B AUDIT:
c479a379b54e196439c522c1fdf56eca713ca8ad

FINAL AUDIT-ONLY COMMIT:
이 보고서를 추가한 commit: git log -1 --format=%H -- docs/t66f-phase-b-continuation.md

REPOSITORY STATE:
VERIFIED

PHASE A:
PASS

B01 INDEPENDENT VALIDATION:
PASS

B01 FINDING:
CLOSED

PRIOR PHASE B EVIDENCE:
PRESERVED

COMPLETE F COVERAGE MATRIX:
PASS

MANDATORY F GATES:
ALL IDENTIFIED

H DEFINITION:
hot/참조 working set와 required control/policy descriptor 크기

D DEFINITION:
base 이후 changed rows

N DEFINITION:
전체 역사 row

FIXED H/D CONFIGURATION:
VERIFIED

FULL REQUIRED N GRID:
INCOMPLETE

GRID POINTS REQUIRED:
5

GRID POINTS EXECUTED:
Backend 5; 전체 D→E supported profile 3

GRID CORRECTNESS:
INCONCLUSIVE

GRID COST:
INCONCLUSIVE

COLD SYNC:
PASS — 관찰한 1,001행 보조 fixture; 전체 grid 아님

IDENTICAL GENERATION:
PASS — 실행한 범위

SMALL DELTA:
PASS — 실행한 범위

LARGE DELTA:
PASS — 이전 독립 correctness 증거 이월

COMPRESSION MEASUREMENT:
PASS

COMPRESSION BOUNDARY:
VERIFIED

MEDIAN MEASUREMENT:
PASS — 완료된 HOST workload

P95 MEASUREMENT:
PASS — 완료된 HOST workload의 empirical p95

SAMPLE COUNT:
workload별 3 warmups + 20 samples; cold/fallback은 단일 기술 표본

MEASUREMENT ENVIRONMENT:
DOCUMENTED

REAL BACKEND-FLUTTER HTTP:
PASS

CANONICAL FINANCIAL EQUIVALENCE:
PASS

RAW MONETARY VALUES:
PRESERVED

UNICODE:
PRESERVED

BACKEND FINANCIAL AUTHORITY:
PRESERVED

GRAPH CLOSURE:
PASS — 관찰한 graph와 기존 독립 증거

INDEPENDENT PROTOCOL NEGATIVE:
PASS — binding 추가 10건; 비규범 MIME 진단 1 FAIL 별도

INDEPENDENT CROSS-LAYER AUTHORITY:
PASS

BACKEND DATABASE IDENTITY:
PASS

BACKEND PERMIT LIFECYCLE:
PASS

B01 STRICT ASSERTION:
PRESERVED

E1 DURABLE STORE:
PASS

E2 ACQUISITION:
PASS — 지원 범위; 큰 grid의 unsupported 한도 별도

E2-A01 RESOURCE CLEANUP:
PASS

E3 ATOMIC PUBLICATION:
PASS

E3 ORIGINAL APPSTATE TICKET:
PASS

E3 I25 INCREMENTAL COST:
INCONCLUSIVE

E4 GENERATION-CONSISTENT READ:
PASS

E4 SOURCE/LINEAGE:
PASS

E4-A01:
CLOSED

E4-RA01:
CLOSED

E4 FROZEN-B REPEATED READ COST:
PASS — 세 supported N의 관찰 범위; 큰 grid 미측정

FROZEN PIN RETENTION:
PASS

FROZEN B/J:
PRESERVED

IMPLICIT B/J ACK:
NONE

AUTOMATIC B/J REBASE:
NONE

SNAPSHOT V7:
PRESERVED

OFFLINE BASELINE V4:
PRESERVED

SYNC_ROOT / V7 FINGERPRINT:
SEPARATED

CROSS-STORE CRASH CONSISTENCY:
PASS — 이전 실제 crash 및 현재 회귀 범위

FRESH-PROCESS RECOVERY:
PASS

END-TO-END INCREMENTAL TRANSFER:
INCONCLUSIVE

END-TO-END INCREMENTAL STORAGE:
INCONCLUSIVE

END-TO-END RESOURCE BOUNDEDNESS:
INCONCLUSIVE

INDEPENDENT HTTP COUNTERS:
PASS

INDEPENDENT SQLITE COUNTERS:
PASS

INDEPENDENT OBJECT COUNTERS:
PASS

INDEPENDENT PIN COUNTERS:
PASS — native client generation-root pins; backend pin counter 한계 별도

NEW CONTINUATION FUNCTIONAL CASES:
2 PASS
0 FAIL
0 INCONCLUSIVE

NEW CONTINUATION NEGATIVE CASES:
10 PASS
1 FAIL — 비규범 Content-Type 진단
0 INCONCLUSIVE

NEW CONTINUATION AUTHORITY/RACE CASES:
14 PASS
0 FAIL
0 INCONCLUSIVE

NEW BACKEND DB IDENTITY CASES:
7 PASS
0 FAIL
0 INCONCLUSIVE

NEW BENCHMARK CASES:
11 PASS — 각 profile의 제한된 경계
0 FAIL
2 INCONCLUSIVE — 지원되지 않는 50k/100k 통합 지점 포함, 미실행을 PASS로 세지 않음

FULL BACKEND TESTS:
1315 TESTS
1540 SUBTESTS
PASS

FULL FLUTTER TESTS:
1503 PASS
0 FAIL
2 SKIP

FLUTTER ANALYZE:
PASS

FLUTTER BUILD:
PASS

RUFF:
PASS

COMPILEALL:
PASS

CHANGED-FILE FORMATTING:
PASS

GIT DIFF CHECK:
PASS

PRODUCT SOURCE MODIFIED:
NO

DEFAULT FLUTTER STARTUP:
UNCHANGED

NORMAL FINANCIAL READ/WRITE:
UNCHANGED

PRODUCTION SQLITE USER_VERSION:
UNCHANGED

ANDROID VFS/I/O EVIDENCE:
REQUIRED BUT MISSING — actual implementation/rollout proof

POWER-LOSS EVIDENCE:
REQUIRED BUT MISSING — HOST SIGKILL 대체 불가

DEVICE PERFORMANCE:
DEFERRED — post-T6.6 gate

R1 LARGE RESTORE/MW:
DEFERRED

R1 MIGRATION/ROLLBACK:
DEFERRED

R1 ACTIVATION GATE:
CLOSED

GENERAL-USER SEGMENTED OFFLINE:
NOT ACTIVATED

PRODUCTION SEGMENTED ACTIVATION:
NOT PERFORMED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

NEW LOW:
0

UNRESOLVED PHASE B BLOCKERS:
3개 필수 증거 묶음: 50k D→E, 100k D→E, 전층 논리 hash/validate/write byte accounting

MANDATORY F REQUIREMENTS UNVERIFIED:
위 3개 묶음 및 상위 Android proof/R1 dependency; coverage-final.json 참조

PHASE B FINAL VERDICT:
INCONCLUSIVE

BINDING T6.6F EXIT CRITERIA:
NOT SATISFIED

SAFE TO DECLARE T6.6F COMPLETE:
NO

SAFE TO START R1:
NO — 이 감사는 별도 R1 prerequisites 충족이나 구현 시작을 승인하지 않음

SAFE FOR GENERAL-USER ACTIVATION:
NO

SAFE TO DEPLOY:
NO

FINAL VERDICT:
INCONCLUSIVE — T6.6F PHASE B VERIFICATION STILL BLOCKED

NEXT ACTION:
지원 object budget과 의무 50k/100k grid의 정합성을 별도로 검토하고 승인된 경로에서 남은 비용·기기·복구 증거를 확보한다.
```
