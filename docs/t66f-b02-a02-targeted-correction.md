# T6.6F-B02-A02 최소 교정 — 구현·검증 기록

## 판정

**최종 구현 판정: COMPLETE — B02 독립 targeted audit 준비 완료.**
실제 50k·100k cold/delta/restart와 최종 전체 회귀를 완료했다. 독립 감사 PASS나 Phase B
PASS가 아니다. 아래 승인 전·실행 중 기록은 당시 상태를 보존한 이력이며 최종 결과는 끝 절을 따른다.
아래 첫 검증 기록의 artifact 승인 대기는 사용자 승인으로 해소됐다.
승인 전 실패 증거를 보존하고, 승인 후의 결과는 뒤의 재개 절에 분리한다.

### 승인 전 중간 기록

권고된 두 source 교정을 적용했다. C1 차분과 같은 실제 ASGI 요청의 결과 동등성·작업 감소는
확인했지만, 현재 허용되지 않은 새 engine hash에서 Flutter 검증이 차단된다.
100k 성공, B02 완료, 독립 감사 PASS 또는 Phase B PASS로 해석해서는 안 된다.

## 시작점과 원본 보존

시작 HEAD/main/origin/main/실제 remote main은 모두
`6282c1c3577c42bba9382d786745d583a5d88236`이었다. 원래 index에는 staged diff가 없었고,
B02/A01/A02 조사 작업은 정상적인 미커밋 입력이었다. 시작 시 현재 1,820개 파일의 SHA와
logical index·binary diff를 [initial-state.json](benchmarks/t66f-b02-a02-correction/initial-state.json)에
기록했다. A02 조사 시작의 1,766개와는 시점·새 조사 artifact 포함 여부가 다르다.
기존 조사·감사 보고서와 성공/실패 증거를 덮어쓰지 않았다. reset/stash/clean/checkout,
stage/commit/push, 배포·설치·activation은 수행하지 않았다.

## 근거와 범위

원 근거는 [A02 조사 보고서](t66f-b02-a02-100k-acquisition-investigation.md)다.
이전 실제 100k cold는 세 관측 2,700.166초 뒤 294,624/400,532 객체에서 만료됐다.
완료 모델은 이번 구현의 실제 성공 근거가 아니다.

제품 수정은 다음 두 파일뿐이다. 기존 B02/A01 제품 변경은 그대로 기반으로 사용했다.

|파일|이번 교정|
|---|---|
|`backend/isolated_sync/canonical.py`|strict JSON token parse를 내부 함수로 분리하고, `decode_c1`의 동일 value encode를 두 번에서 한 번으로 줄였다. 공개 `decode_json`은 여전히 nested encode validation을 수행한다.|
|`mobile/lib/src/segmented/fetch.dart`|명시 large profile·cold·새 active 호출·publication 가능한 기존 store에 한정하여 동일 Target 아래 suspended verifier를 이어간다. default·warm·resume 호출은 기존 loop를 사용한다.|

E1/store·graph verifier·E3/E4 제품·금융 계산·protocol·SQLite schema를 이번에 수정하지 않았다.
새 cache, persistent cursor, authorization token 또는 복구 엔진을 만들지 않았다.

## C1 교정과 직접 검증

`_parse_json`은 기존 bytes/UTF-8/duplicate key/int64/REAL/JSON 오류 경로 그대로다.
`decode_c1`의 한 번의 `encode`가 모든 nested string/key/type/domain admission과
canonical byte equality를 함께 수행한다. escaped surrogate 검증을 JSON parser에만 맡기지 않는다.

새 회귀 `backend/tests/test_isolated_sync_c1_single_encode.py`는 시작 시 보존한 실제
codec bytes를 별도 module로 실행해 byte/error oracle로 사용한다. supported/invalid corpus,
10,000개 고정 seed nested 값과 세 hash domain, 원문 monetary control fixture,
int64/REAL/Unicode/nesting/type 오류, 공개 `decode_json` 검증을 대조했다.
**25 PASS**이며 10,000개는 별도 pytest test 수에 더하지 않는다.
기존 canonical 회귀 **34 PASS**, 기존 prefix와 새 C1 결합 **53 PASS**다.
B01 원 strict quota assertion은 수정하지 않았고 별도 **1 PASS**다.

## 동일 요청 비용 — DIRECT OBSERVATION

[codec_benchmark.py](benchmarks/t66f-b02-a02-correction/codec_benchmark.py)는 동일한 합성
DB/관측/64-item 요청에서 보존한 codec과 새 codec을 교대로 사용한다.
실제 ASGI/auth/SQLite 경로이며 TCP/TLS·Flutter/E1 처리량 증거는 아니다.
조건별 warmup 제외 3회, 총 12개 측정 응답의 exact HTTP entity bytes가 동일했다.
각 terminal object bytes도 독립 graph oracle와 대조했다.

|64-item 표본|encode 호출 전→후|encoded output bytes 전→후|SQL 전→후|wall median 전→후|
|---|---:|---:|---:|---:|
|shared|1,165→583|1,957,162→1,008,948|566→566|0.2772→0.2080초|
|spread|3,067→1,534|2,924,011→1,491,468|883→883|0.4026→0.2940초|

encode output 길이는 test instrumentation이다. 전체 hash/validate/write bytes 또는
physical I/O가 아니며, 이 유한 표본의 약 25~27% 시간 감소를 100k 완료 보장으로 쓰지 않는다.

## E2 continuation의 구현 불변식 — 아직 동작 검증 미완료

- 관측 budget은 active 호출 하나의 단일 counter로 최대 3회다. lease 900초·request attempts 3,
  64 objects/1MiB packet, path 512, large 500k objects/1m edges/384MiB metadata를 늘리지 않았다.
- fresh observation에는 새 nonce/ID/manifest/stage를 사용한다. `Target.toJson()` 전체의 C1 bytes가
  정확히 같아야 기존 DFS/seen/frontier를 이어간다. 같은 roots 또는 revision만으로 허용하지 않는다.
- Target가 달라지면 이미 획득한 fresh 관측을 같은 budget 안에서 사용하되, verifier와 frontier를
  버리고 새 루트부터 검증한다. immutable bytes의 기존 E1 hash-on-read 재사용만 남는다.
- packet 410은 verifier Future를 unwind하기 전에 새 권한을 얻는다. 실패한 load는 전체를 재시도하므로
  oversized object의 부분 buffer는 unwind되고 다른 lease의 chunks와 합치지 않는다.
- graph 완료 뒤 terminal 410도 새 관측의 exact Target와 fresh terminal을 요구한다.
  완료되지 않은 graph를 `graph_verified`로 기록하지 않는다.
- old progress links를 fresh stage로 복사하지 않는다. old stage/root는 남고 새 stage는 fresh manifest를
  저장한다. E3의 실제 complete-store/F(raw)/hot/raw 검증과 accepted publication은 그대로다.
- 기존 store의 `publicationDataVersion`과 validator/profile 검사를 사용한다. 외부 SQLite commit,
  store close 또는 profile/validator 불일치는 renewal/완료 guard에서 fail-closed한다.
  자체 E1 transaction은 같은 connection의 data_version을 바꾸지 않는다. 새 persistent proof가 아니다.
- 현재 session/cancel 검사와 기존 cooperative yield는 유지한다. original AppState ticket을 새로 발급하지
  않으며 E3 final synchronous guard-to-COMMIT 경계를 수정하지 않았다.
- publication API가 없는 acquisition-only store와 resumeId 호출은 보수적인 원 root 재검증 경로다.
  신규 store API 또는 E1 계약을 추가하지 않기 위한 좁은 선택이며 restart cursor 복원은 하지 않는다.

새 Dart 테스트는 packet/terminal 만료 1·2회, budget 소진, exact Target revision 변경,
wrong principal/epoch, logout/cancel, external commit/corruption/trigger 누락,
stage transaction 실패의 durable oracle를 작성했다. **이 테스트들의 PASS는 아직 주장하지 않는다.**
현재 control 한 건은 acquisition 전에 `UNSUPPORTED_CONTRACT`로 실패했다.

## exact artifact와 source-lock 승인 경계

C1 source 변경은 engine artifact 입력을 바꾼다. 새 exact hash는
`7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c`다.
검토한 engine source 차이는 `isolated_sync/canonical.py` 하나이며 versions/raw_schema/
projection_schema/policy_registry/engine profile은 byte 동일하다.
상세는 [artifact-review-pending.json](benchmarks/t66f-b02-a02-correction/artifact-review-pending.json)이다.

현재 승인된 hash는 원 frozen
`f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d`와 A01
`afe26b70856b5a3fa06477641d91e8e1784e9184906281843f0a39a9c99cbdf5` 두 개다.
이 승인을 임의의 세 번째 hash 승인으로 해석하지 않는다. 이번 artifact/ReleaseContract/기존 source
guard를 변경하지 않았으며 승인 요청의 답을 기다린다. frozen golden과 역사 artifact는 원본이다.

default E2 source는 새 cold branch/helper와 기존 reviewed profile seam을 제외하면 과거 보호 SHA
`a1e6b4b549dcb5a11d5e0cabcb7806ff42eb831f4192c40b353a103698721253`와 정확히 일치한다.
[default-source-review.json](benchmarks/t66f-b02-a02-correction/default-source-review.json)은
구현 측 범위 검토이며 기존 extension exact lock의 PASS 또는 독립 감사로 부르지 않는다.

## 남은 검증과 제한

1. 사용자 승인 뒤 정확히 세 engine hash만 허용하는 artifact 갱신을 검증한다. 나머지는 거부한다.
2. E2 신규 동작·negative·부분 chunk·stage failure·authority/crash·medium renewal work를 실행한다.
   default reconstruction과 신규 extension revision도 행동 회귀 후 명시적으로 review/lock한다.
3. 같은 fixed-H fixture의 실제 50k와 100k TLS D3a/D3b/D3c→E2/E1→E3→E4를 실행한다.
   cold·identical·delta·fresh process·all-table value digest와 자원 한도를 계수한다.
4. 최종 source에서 전체 Flutter/backend, E1–E4/P0/I25/A01/RA01/B01, static/build/format을 실행한다.
   이번에는 전체 suite·실제 50k/100k를 아직 재실행하지 않았다.

현재 한정 Dart analyze, Ruff, compileall, frontend npm build, 새 Python 파일·변경 Dart 파일 형식,
diff check는 통과했다. 첫 analyze의 unused import/style 경고는 새 테스트에서 수정했다.
실제 Android VFS/I/O·전원 손실·완전 100k memory·전체 logical byte gate는 미검증이다.
R1 CLOSED, general-user segmented Offline 미활성, Phase B INCONCLUSIVE를 유지한다.

## 다음 행동

새 exact engine hash와 기존 두 hash를 함께 유지하는 제한적 호환 갱신을 승인받은 뒤,
E2 만료·Target 변경 회귀와 medium work gate부터 진행한다.

## 사용자 승인 후 구현·검증 재개

사용자는 새 exact engine를 current build로 지정하고 기존 두 exact hash만 호환 목록에 유지하는
변경에 **“승인합니다.”**라고 답했다. 승인 범위대로 specimen·모바일 asset·`ReleaseContract`를
갱신했다. 새 current는 `7ad114bc…0208d6c`, 이전 `afe26b70…c99cbdf5`와 원 frozen
`f34aef25…ffe449d`를 유지한다. wildcard/그 외 hash 허용은 없다.
[artifact-review-approved.json](benchmarks/t66f-b02-a02-correction/artifact-review-approved.json)에
정확한 전체 hash·source 차이·동일 schema/policy/versions와 승인 전 artifact 보존을 기록했다.

새 continuation/negative/부분 chunk/정확한 세 engine 회귀 17개, 새 실제 SIGKILL 4개,
기존 A01 packet 14개·원 source guard 23개·HTTP cleanup 13개, 합계 **71 PASS/0 FAIL**다.
Signal은 새 관측의 stage 준비/commit과 새 관측 batch 준비/commit의 실제 E1 hook에서 보냈다.
별도 프로세스로 만든 DB를 다시 열어 integrity/FK·staging·accepted 없음·객체 bytes와
legacy baseline/온라인 unknown marker bytes를 확인하고 새 acquisition을 완료했다.
이 4개는 actual Frozen J 입력 journal 또는 hardware power-loss 증거로 부르지 않는다.
Frozen B/J 자체는 기존 전용·전체 회귀의 별도 검증 대상이다.

초기 확장 실행의 잘못된 cleanup 파일명은 loading error 1개로 별도 보존했다. 원 assertion을
바꾼 것이 아니며 정확한 실제 경로 `segmented_response_cleanup_test.dart`로 다시 실행한 위
71개 결과가 최종 한정 결과다. runtime에 필요한 package config가 없는 docs 대상 analyze 시도도
별도 runner 오류로 보존했고, 모바일 source/test에 대한 올바른 정적 분석은 통과했다.

### 동일 fixture 갱신 비용 — IMPLEMENTATION TEST RESULT

보존한 A01 fetch revision과 새 fetch를 같은 backend-produced fixtures에 사용했다.
controlled 410 한 번·조건별 두 회·총 12회이며 실제 HTTP lease 실험은 아니다.
모든 durable hash/BLOB 집합을 fixture closure와 직접 SQLite로 비교했고, accepted는 비어 있었다.

|객체 수|graph 방문 전→후|E1 object read 전→후|
|---:|---:|---:|
|126|145→126|388→331|
|926|1,188→926|2,900→2,391|
|4,130|5,950→4,130|12,516→10,169|

이는 graph root 재순회 감소를 보여준다. packet 재시도·fresh staging·cached lookahead의 모든
작업이 사라졌다는 뜻은 아니다. 독립 SQL trace가 아니라 E1 work counter이며 durable oracle와
교차 검증했다. 새 benchmark의 첫 상대 import/alias·실행 cwd 오류는 제품 실패와 구분해 보존했다.

### 실제 50k 전체 경로 — DIRECT OBSERVATION

원 fixed-H 50,000 ledger/50,035 authoritative rows, 200,331 reachable objects,
200,327 edges, depth 22, canonical 130,710,592 bytes를 그대로 사용했다.
다른 synthetic regression PID 없이 실제 TLS D3a/D3b/D3c→E2/E1→E3→E4를 실행했다.
**PASS_COLD_IDENTICAL_DELTAS_RESTART**, child CLI exit 0이다.

- cold 관측 **2회**, 같은 exact Target 아래 continuation **1회**, graph 방문 **200,331회**.
- 최초 관측 요청부터 최종 terminal 응답 완료 **1,275.376초**.
  E3 게시 반환 **1,445.531초**, E4 전체 값 digest 비교 후 **1,456.827초**는 별도 경계다.
- 새 관측 manifest 뒤 첫 객체 요청까지 **0.021619초**. TTL/관측/packet budget 변경 없음.
- cold 객체 요청 3,175회, 완전 객체 200,331개, cross-observation retransfers 0.
  response entity **203,247,161 bytes**, decoded object **130,710,592 bytes**.
- 전체 테이블 canonical financial value digest가 backend oracle와 같았다. 동일 세대 전송 0,
  한 행 delta 26·localized multiple 42·restart delta 26개는 각각 backend reachable-set oracle와 같다.
- 별도 프로세스 recovery/health와 accepted 읽기 통과, 보호 baseline/online marker bytes 동일,
  최종 FK 오류 0. R1 CLOSED·general-user mode 미활성이다.
- cold E1 work: transactions **3,868**, object reads **889,046**, full verification **1**,
  full raw rows **50,035**, accepted writes **1**, root pin inserts **4**.
- 최종 client peak RSS **1,547,726,848 bytes**, E1 DB **310,841,344 bytes**.
  최종 payload **131,497,909**, metadata **146,785,679 bytes**, objects **200,425**.
  최종 수치는 delta/restart까지 포함하며 cold-only 수치와 혼합하지 않는다.
- backend bootstrap **217.405초**, 전체 캠페인 wall **2,618.937초**다. host 수치이며 Android 보증이 아니다.

실제 1k도 cold/identical/deltas/별도 process/restart 전체 통과했다. 100k는 같은 source hashes와
같은 한도로 별도 무경쟁 캠페인을 시작했다. 성공·실패 결과가 나오기 전에는 PASS로 기록하지 않는다.

### Source-lock 재검토

과거 `protected-source.json`, A01 review, frozen goldens·감사 보고서를 바꾸지 않았다.
현재 fetch helper/branch와 기존 profile seam만 제외하면 원 default SHA가 정확히 복원된다.
새 extension과 승인된 protocol revision은
[source-lock-review.json](benchmarks/t66f-b02-a02-correction/source-lock-review.json)에 exact hash로
별도 잠갔다. 원 보호 hash를 새 값으로 덮어쓰거나 검사·assertion을 비활성화하지 않았다.
23개 source guard가 통과했지만 독립 감사 승인을 대신하지 않는다.

### 실제 100k 전체 경로 — DIRECT OBSERVATION

앞 절의 대기 중이던 캠페인이 `PASS_COLD_IDENTICAL_DELTAS_RESTART`, child exit 0으로
완료됐다. 동일 최종 source SHA의 원 fixed-H fixture를 사용했고 ledger 100,000행,
authoritative 100,035행, **400,532 objects / 400,528 edges / depth 23**,
canonical **261,543,083 bytes**를 backend에서 확인했다. 수동 E1 복사나 accepted metadata
주입 없이 실제 TLS D3a/D3b/D3c→E2/E1→원 AppState/E3→E4를 통과했다.

|cold 관측|UTC 유효기간|새 완전 객체|객체 요청(410 포함)|성공 packet 평균 items|manifest→첫 객체 요청|
|---|---|---:|---:|---:|---:|
|1|2026-10-19 12:58:57→13:13:57|137,120|2,211|62.045|0.098409초|
|2|13:13:57→13:28:57|148,416|2,320|64.000|0.022530초|
|3|13:28:57→13:43:57|114,996|1,803|63.780|0.054627초|

세 exact Target가 같고 active DFS continuation은 두 번이다. 첫 두 lease의 실제 410은
관측을 새로 얻어 처리했으며, 만료된 관측을 연장하거나 네 번째 관측을 쓰지 않았다.
완전 객체 총 400,532개, 관측 사이 재전송 0, cold 객체 요청 6,334회다.
HTTP request entity **523,444,310 bytes**, response entity **406,693,862 bytes**,
decoded object **261,543,083 bytes**다. TCP/TLS framing·physical I/O와 다른 계수다.
기록된 request-local prefix peak는 132 entries / 68,135 canonical charged bytes로 상한 안이고,
성공·만료 요청의 기록된 permit은 모두 닫혔다.

원 client stopwatch의 E3 publication 반환은 **2,982.185초**, E4 전체 테이블 value digest
비교 완료는 **3,009.140초**다. 이는 전송 TTL 시간이 아니다. 마지막 관측의 객체 전송과
원 nonce terminal 확인은 lease 안에서 완료됐으며, 이후 local 검증/게시에는 §16의
완전 수신 observation 규칙과 여전히 유효한 원 AppState ticket을 적용했다.
동일 server monotonic trace의 최초 observation 시작→최종 terminal 응답 완료는
**2,590.048631초**다. 세 번째 lease의 만료 시점 이전임을 actual UTC/trace로도 대조했다.
E4 전체 11-table canonical value digest는 backend oracle와 동일했다. financial projection을
단말에서 다시 계산하지 않았다.

|후속 단계|HTTP 전송 객체|backend 실제 새 객체 oracle|원 client elapsed|full verification|
|---|---:|---:|---:|---:|
|identical|0|같은 Target|2.636초|0|
|one-row delta|27|27|9.585초|0|
|multiple localized|44|44|9.973초|0|
|fresh-process reopen 뒤 delta|27|27|785.549초|2|

restart 행에는 기존 complete recovery가 포함된다. 이를 healthy-session delta 비용 또는
상수 시간 복구라고 표현하지 않는다. 정상 delta의 graph 방문 27/44, pin inserts 각 4,
full recovery/verification 0이며 기존 E3 I25 프로토콜을 수정하지 않았다. 50k의 실제 한 행
26개와 100k의 27개는 조사 때 25/26개와 다르다. 현재 정확한 engine artifact/context로 생성한
실제 backend Target의 reachable-set 차집합과 일치하며 임의 고정 개수를 기대값으로 쓰지 않았다.

별도 fresh process의 health/accepted 읽기는 exit 0, 400,603 objects / 6 stages 확인으로
통과했다. 최종 delta 뒤 objects **400,630**, stages **7**, payload **262,335,489 bytes**,
metadata **293,089,307 bytes**, E1 DB **619,786,240 bytes**, FK 오류 0이다.
이 최종 수치는 cold-only가 아니라 deltas/restart까지 포함한다. client OS peak RSS
**3,137,257,472 bytes**, 전체 process-tree sampled peak **5,746,802,688 bytes**,
backend bootstrap **554.075초**, 전체 캠페인 **5,421.440초**다. 7,200초/8GiB guard에
의한 종료가 아니며 상한을 늘리지 않았다. Host RSS는 Dart heap·Android 안전성 증명이 아니다.

legacy baseline/online outcomeUnknown marker bytes가 전후 동일하고 R1은 CLOSED다.
이 보호 집합은 actual Frozen J journal이 아니다. 대형 legacy native installation이나
Frozen-B lineage/R1 증명을 새로 만들지 않았다. 실제 B/J·영구 pin·A01/RA01의 전용 회귀는
전체 suite에서 별도로 확인한다.

이전 A01의 실제 100k `FAIL_COLD`와 A02의 승인 전 실패·잘못된 runner 경로 로그는
그대로 남는다. 이번 성공으로 과거 보고서의 FAIL/INCONCLUSIVE를 지우지 않는다.

### 최종 회귀·Git 완료 gate

대형 실행을 반복하지 않고 같은 최종 source에서 전체 Flutter/backend 및 실제 HTTP·독립 P0·
B01 회귀, analyze/build/format 검사를 수행 중이다. 종료된 실제 결과와 보존 check를 확인하기
전에는 완료 commit/push를 하지 않는다. Phase B의 전층 logical hash/validate/write bytes,
Android VFS/I/O·hardware power-loss·R1 증거는 별도 의무로 남는다.

### 완료 대상 전체 B02/A01/A02 diff의 소유권

이번 A02의 두 소스 교정과 앞서 미커밋 상태로 받은 B02/A01을 합쳐 검토한다.
기존 B02/A01 구현을 HEAD 버전으로 덮어쓰거나 다시 만들지 않았다.

|파일|단계·역할|정상 경로 경계|
|---|---|---|
|`mobile/lib/src/segmented/fetch.dart`|B02 finite profile/batch 경계, A01 cold packet/yield, A02 same-Target active continuation|명시 large profile만 선택; 원 default 알고리즘 exact SHA 복원|
|`mobile/lib/src/segmented/store.dart`|B02 기존 immutable write/readback을 64 entries/1MiB transaction에 공유|기존 단일 insert와 schema/trigger/quotas 유지|
|`mobile/lib/src/app_state.dart`|B02 기존 isolated publication에 기본값 유지 budget 인자만 전달|원 coordinator/ticket/session/final guard 재사용, startup caller 추가 없음|
|`backend/isolated_sync/transfer.py`|A01 request-local verified typed-prefix 재사용|64×512 entries와 1MiB canonical charge 이내, terminal object·auth/TTL/FD/permit 불변|
|`backend/isolated_sync/canonical.py`|A02 동일 value encode 중복만 제거|strict parse·nested validation·C1 equality·hash domain 유지|
|`mobile/lib/src/segmented/protocol.dart`와 두 release artifact|사용자 승인 exact engine 세 revision만 허용|schema/policy/version 의미·원 golden 불변; 그 외 hash 거부|
|`mobile/test/segmented_adapter_isolation_test.dart`|현재 확장을 exact revision으로 추가 검토하고 원 default source를 재구성|과거 protected SHA/golden을 덮어쓰지 않음|

기본 E2 100,000 objects/200,000 edges, 기본 E1 32MiB metadata는 그대로다.
명시 host 검증 profile만 500,000 objects/1,000,000 edges/384MiB metadata를 사용한다.
100k 실제 V400,532/E400,528/payload261,543,083B와 final metadata293,089,307B가 이
finite envelope 안에 있음을 확인했다. 추가 stages/union에 대한 여유이지 ceiling 아래의
임의 graph가 모든 독립 budget을 무조건 통과한다는 약속은 아니다.
개별 object64MiB, payload512MiB, manifest8MiB, pages262,144, stages128, chunk1MiB,
path512, C1 depth128, request attempts3, observations3, lease900초는 늘리지 않았다.
production `user_version=4`와 별도 isolated store 형식을 혼동하지 않는다.

원 A01 small/medium benchmark의 같은 926-object cold fixture는 packet 322→27,
평균 items 2.876→34.296이었다. shared64 resolver의 실제 object/metadata read·SELECT는
1,206→141, prefix cache hit 1,065로 canonical validation calls도 같은 폭으로 감소했다.
이는 보존된 A01 직접 계수이고 이번 A02 실측과 합쳐 새 반복 표본 수로 세지 않는다.
이번 A02의 encode 단일화·같은 Target 순회 유지 측정과 최종 실제 50k/100k 성공을
각각 별도 증거로 연결한다. 전역 cache나 새 scheduler/storage/protocol은 추가하지 않았다.

### 역사적 실패와 형식 검사 분리

최종 static gate에서 mobile analyze, debug APK build, frontend npm build, Ruff, compileall이
통과했다. APK 설치·배포는 없다. 넓은 최초 Dart 형식 검사에는 보존용
`before_fetch.dart`까지 들어가 그 파일 한 개의 원 스타일 차이로 exit 1이었다.
원 byte oracle를 포맷해 바꾸지 않고 나머지 **32개 Dart 파일은 exit 0**으로 대조했다.
`canonical.py`/`transfer.py`의 기존 전체 Ruff-format 차이도 before/current 모두 존재하고
formatter AST가 같음을 확인했다. 새 Python 파일의 형식 검사는 별도로 통과했다.

원 독립 P0 Python suite는 **4 PASS/1 fixture FAIL**이었다. 정확한 실패는 E4 이후 새로
생긴 `segmented/adapters.dart`를 그 파일이 없었던 E3 commit에서 `git show`하려는 것이다.
monetary assertion 이전의 이미 기록된 enumeration 오류이며 원 파일을 수정하지 않았다.
기존 독립 `test_p0_replay.py`의 `--diff-filter=M` 보완본은 동일한 원 monetary/codepoint/
hash assertions로 **1 PASS**였다. 원 corpus의 24,836 vectors와 나머지 네 case는 별도다.
역사적 pre-P0 probe의 obsolete 기대와 이 fixture 오류를 current-contract 제품 FAIL 또는
전체 PASS로 바꿔 기록하지 않는다.

### 추가 continuation 회귀의 실제 실패 분류

기존 real-HTTP integration와 B01 quota smoke는 합계 **34 PASS**, 독립 P0 Flutter는
**18 PASS**였다. 기존 continuation 전체 실행은 **23 PASS / 1 diagnostic FAIL**이다.
실패 이름은 `C-N-content_type real handler response mutation preserves installed Frozen B`이며,
유효한 body의 MIME만 `text/html`로 바꾼 뒤 반드시 거부해야 한다는 기대에서 `error=null`이었다.
이는 원 continuation 보고서 §35의 **F-BC02 / INFORMATIONAL — 비규범 MIME 거부 diagnostic**과
동일하다. 그 보고서가 이미 binding보다 엄격한 기대라고 분류한 원 assertion이며, 이번에
기대값을 느슨하게 바꾸거나 skip하지 않았다. protocol·E2 default source·제품 parser도 바꾸지 않았다.
원 strict diagnostic과 실제 before/after/Frozen fingerprint/wire 증거는 새 gzip으로 보존한다.
23개 binding negative/authority PASS와 이 diagnostic FAIL을 합쳐 모두 PASS라고 쓰지 않는다.

추가 lineage 최초 실행은 source가 요구하는 `C_LINEAGE_OUTPUT` 대신 README의 일반
`CONTINUATION_OUTPUT`을 넘긴 runner 오류였다. durable authority assertions 뒤 결과 파일
기록에서 `PathNotFoundException(path='')`로 실패했다. 원 테스트·assertion·제품은 그대로 두고
정확한 인자로 다시 실행해 **1 PASS / CLI exit 0**을 확인했다. 최초 실패도 별도 보존했다.
이 둘 때문에 새로운 제품 결함을 추정하거나 허용 status/timeout을 바꾸지 않았다.

### 대형 ordinary accepted read 비용 — DIRECT OBSERVATION

각 완료 store를 별도 Dart process로 다시 열어 기존 complete recovery를 수행한 **뒤**,
20회 × 첫 16행 logical read를 측정했다. actual pins/보호 파일 checksum과 backend hot/control
root hash도 대조했다. 두 process 모두 CLI exit 0이다.

|N|반복 object reads|반복 verified bytes|full recovery/verification/rebuild|transaction/pin 변경|
|---:|---:|---:|---:|---:|
|50k|80|3,180,540|0 / 0 / 0|0 / 0|
|100k|80|3,200,460|0 / 0 / 0|0 / 0|

각 20 read snapshots/40 accepted metadata reads이며 hot/control hash·pin rows·legacy marker bytes는
불변이다. loop 시간 1.903/1.978초는 병행 synthetic 회귀가 있던 host 표본이므로 throughput
보증으로 쓰지 않는다. 처음 full recovery의 시간·메모리는 loop에 포함되지 않았다.
이 scope는 accepted read이며 native Frozen-B 설치/새 R1 proof가 아니다. 기존 Frozen-B
T03 provenance 비용·A01/RA01 ownership의 보존은 전용 원 회귀와 해당 소스 불변으로 별도 평가한다.

### 현재 완료된 최종 backend 회귀

최종 제품 source에서 전체 backend **1,368 tests / 1,540 subtests PASS**, CLI exit 0,
1 warning, 1,782.86초였다. 새 prefix 28개·새 C1 25개를 원 1,315개에 각각 한 번만 더한
개수다. 10,000 differential samples를 pytest case 수로 더하지 않았다.
기존 동시성 family **90 PASS**, B01 구현·독립·Phase B backend/실제 TLS 외부 회귀
**26 PASS**도 별도 완료했다. 원 B01 strict `[201]*4+[429]` assertion과 5초 fixture budget,
production lock timeout은 수정하지 않았다. 구현자 결과이며 B01/Phase B 독립 PASS 재선언이 아니다.

## 최종 구현 gate — 완료

최종 제품 소스에서 전체 Flutter **1,599 PASS / 0 FAIL / 2 SKIP**, machine `success=true`,
CLI exit 0, 4,290.411초였다. backend **1,368 tests / 1,540 subtests PASS**, CLI exit 0이다.
전체 실행 이후 제품 코드를 변경하지 않았다. 실제 1k/50k/100k 실행 시의 canonical/transfer/
fetch/protocol SHA가 현재 소스와 모두 같음을 collector에서 재검사한다.

|검증|실제 결과·경계|
|---|---|
|신규 B02 Flutter profile/budget/batch/authority|57 PASS|
|신규 B02 실제 child-process crash|4 PASS|
|신규 A01 packet/yield/cache lifetime|14 PASS|
|신규 A02 continuation/negative/세 exact engine|17 PASS|
|신규 A02 실제 renewed-stage/batch SIGKILL|4 PASS|
|위 고유 신규 Flutter 합계|96 PASS; 원 1,503개에 추가, 중복 실행을 새 case로 세지 않음|
|신규 backend prefix/C1|28 + 25 = 53 PASS|
|최종 targeted Flutter|71 PASS; 전체 suite와 중복되는 별도 실행|
|기존 E4-P0 구현|`authoritative_money_compatibility_test.dart` 183 PASS|
|기존 E3 publication / native crash|36 / 16 PASS|
|기존 E3 I25 publication / baseline|30 / 1 PASS|
|기존 E1/E2/E3 actual process-crash 회귀|7 + 3 + 16 = 26 PASS|
|기존 E4 handoff / adapter authority-race|35 + 16 = 51 PASS|
|기존 E4 adapter / handoff process-crash|4 + 13 = 17 PASS|
|기존 Frozen pin / provenance / A01 / RA01 unit|19 / 11 / 21 / 42 PASS|
|실제 대형 D→E 새 campaign|1k·50k·100k 각 1 PASS; cold/identical/deltas/restart 포함|
|기존 실제 HTTP 상호운용·quota|34 PASS|
|기존 P0 독립 integration / compatible replay|18 / 1 PASS|
|기존 continuation binding negative/authority + lineage|23 + 1 PASS; 원 비규범 MIME diagnostic FAIL 별도|
|전체 Flutter|1,599 PASS / 0 FAIL / 2 SKIP|
|전체 backend|1,368 tests + 1,540 subtests PASS|
|analyze / debug APK build / frontend build|PASS / PASS / PASS; 설치·배포 없음|
|Ruff / compileall / 새 Python formatting|PASS / PASS / PASS|
|변경 Dart formatting|32 PASS; 원 source 비교용 byte oracle의 알려진 style 차이는 별도 보존|
|원 canonical/transfer 전체 formatter 차이|before/current 모두 존재; 원 스타일 보존, AST 동일 대조|
|git diff --check|PASS|

원 P0 diagnostic **3 PASS/2 obsolete expectation FAIL**, 원 Python P0 **4 PASS/1 기존 fixture FAIL**,
continuation **23 PASS/1 비규범 diagnostic FAIL**은 그대로 기록한다. 초기 runner 인자·경로 오류와
승인 전 artifact 실패도 지우지 않는다. 이 실패들을 current-contract 성공 count에 섞지 않는다.
현재 계약의 미해결 Critical/High/Medium correctness blocker를 새로 확정한 것은 없다.

## 남은 한계와 다음 독립 gate

- 측정은 HOST/synthetic이다. Android heap/RSS 안전성·VFS/I/O·실기기 latency·hardware
  power-loss는 입증하지 않았다. debug APK 빌드는 설치/운영 허가가 아니다.
- 대형 테스트의 보호 파일은 legacy baseline과 online outcomeUnknown marker다. 실제 Frozen J와
  large native Frozen-B installation을 시험했다고 확대하지 않는다. B/J·Frozen source 자체는
  원 전용 회귀로 보존했으며 E4 제품·lineage·recovery 소스는 바꾸지 않았다.
- cold/restart O(N) 검증을 제거하지 않았다. 정상 delta의 full verification/build/recovery는 0이며
  E3 원 I25 regression을 보존했다. 하지만 Phase B 전체 fixed-H/D grid의 반복 median/p95와
  전층 hash/validate/write byte·SQL rows-scanned·physical I/O accounting을 이 문서로 닫지 않는다.
- MIME diagnostic의 강한 기대는 비규범이라는 원 감사 분류를 유지한다. 원 assertion을 새로
  완화하지 않았다. 정확한 wire·Frozen fingerprint와 정상 typed-byte 검증은 별도로 남는다.
- 다음 단계는 독립 B02 targeted audit다. 구현자가 독립 감사 PASS나 T6.6F Phase B PASS를
  선언하지 않는다. R1 Large Restore/MW는 구현하지 않았고 gate는 CLOSED다.
- 기본 startup·financial read/write·production SQLite user_version 4·Snapshot v7·OfflineBaseline v4·
  frozen B/J·`sync_root != state_fingerprint`는 유지한다. production segmented activation은 없다.

## 원본 보존과 완료 commit/push 절차

완료 staging 직전 원 1,820개 파일을 다시 대조했다. 승인된 여섯 파일의 추가 교정만 있고
나머지 원 B02/A01/조사·역사 report·golden·진단 bytes는 그대로다. 원 logical index와 staged
diff도 유지했다. 기존 `store.dart`·`app_state.dart`·`transfer.py`의 미커밋 B02/A01 구현을
잃지 않았다. 본 완료에서는 그 기존 작업과 새 A02 교정·검증 자료만 함께 checkpoint한다.

staging 대상은 명시한 여섯 제품 소스, 두 approved release artifacts, source guard, 새 tests/support,
다섯 B02/A01/A02 report 및 해당 benchmark 디렉터리뿐이다. source archive의 파일 목록과
untracked 목록에 DB·private key·`.env`·APK가 없음을 확인했다. protocol과 원 감사 보고서는
변경하지 않았다. 원 P0 checkpoint·E4 audit Git history를 재작성하지 않는다.

시작 HEAD/main/origin/main/actual remote는 `6282c1c3577c42bba9382d786745d583a5d88236`다.
완료 소스·최종 report·실제 raw 로그의 SHA 및 실행 exit는
`benchmarks/t66f-b02-a02-correction/final-summary.json`, `process-results.json`,
`validation-*.json`, `preservation-final.json`에서 확인한다. 이 보고서를 포함하는 구현 checkpoint는
다음 명령으로 식별한다. 자기 자신의 commit hash를 본문에 다시 넣는 self-reference는 피한다.

```sh
git log -1 --format=%H -- docs/t66f-b02-a02-targeted-correction.md
git rev-parse HEAD main origin/main
git ls-remote origin refs/heads/main
git status --short
```

검증 gate 통과 뒤 전체 staged diff를 확인하고 정상 main history로 commit/push한다.
실제 최종 commit hash·push/refs/clean tree 확인 결과는 최종 응답에 기록한다.
commit/push는 배포·APK 설치·segmented 활성화 허가가 아니다.

**최종 구현 판정: T6.6F-B02-A01 CORRECTION COMPLETE — B02 READY FOR INDEPENDENT TARGETED AUDIT.**
이번 A02 권고 교정까지 포함한 구현자 판정이다. Phase B는 STILL INCONCLUSIVE,
R1·일반 사용자 segmented Offline gate는 CLOSED, SAFE TO DEPLOY는 NO다.
