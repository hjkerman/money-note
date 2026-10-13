# T6.6E3 합성 실행 증거

**최신 통합 결과: COMPLETE — 독립 E3 구현 감사 대기.** 최종 회귀는 Flutter 1,094 PASS /
2 SKIP, backend 1,315 tests + 1,540 subtests PASS다. 원래 미완료 판정/측정은 아래에
역사 기록으로 보존하며 최신 수치는 별도 after artifact와 `i25-final-summary.json`에 둔다.

현재 판정은 **INCOMPLETE**다. authority-fenced publisher와 구조 검증의 회귀는
통과했지만, complete accepted validation provenance의 세션 내 증분 재사용과 I25의
steady-state 비용 보완이 남는다. 독립 E3 감사 PASS나 배포 승인이 아니다.

> 이 문단과 `summary.json`은 교정 전 판정을 보존한 것이다. 아래의
> **승인 후 실제 publisher 통합** 절과 별도 after artifact가 후속 교정을 기록한다.

## 재현

checkout의 기존 Flutter/Dart, `.venv` 및 Python dependencies를 사용한다.
새 temporary synthetic SQLite/store와 local ASGI pipe만 열며 production 설정이나
데이터를 읽지 않는다. APK는 빌드만 하고 설치하지 않는다.

```sh
cd mobile
flutter test --no-pub --reporter expanded \
  test/segmented_publication_test.dart \
  test/segmented_authority_test.dart \
  test/segmented_publication_crash_test.dart \
  test/segmented_diff_integration_test.dart
flutter test --no-pub --reporter expanded
flutter analyze --no-pub
flutter build apk --debug --no-pub
```

`segmented_diff_integration_test.dart`는 260개의 합성 archive history와 기존 34개 raw
행을 사용한다. 실제 서버의 mutation/finalizer/observation이 만든 canonical bytes를
수집하고, backend 직접 SQL source로 expected row diff를 확인한다. update/260-row
insert/delete/unchanged를 수행하며 각 publication 뒤 fresh accepted recovery와 별도
SQLite integrity/FK/pin 검사를 실행한다.

회귀 실행의 metrics 원본은 `/tmp/money-note-e3-measurements.json`에 생성된다.
`summary.json`의 `measurements`는 최종 full suite 실행에서 얻은 단일 HOST 표본이다.
전체 회귀와 동시 실행되므로 median/p95나 production latency로 해석하지 않는다.
object_requests는 실제 fixture transport payload 요청 수이며 observation metadata를
포함한 전체 network 요청 수가 아니다. 실제 authenticated D3a/D3b ASGI 경로는 별도의
AppState authority suite와 기존 E2 integration suite에서 시험한다.

## 단위와 해석

- `verification_us`: E3 full verification 및 base 검증, diff, receipt 구성 시간.
- `publication_us`: BEGIN IMMEDIATE부터 synchronous COMMIT까지. graph 검증은 제외한다.
- `readback_us`: COMMIT 뒤 accepted-reference readback 시간.
- `recovery_us`: accepted/current previous 검증과 prepared-only metadata 정리 시간.
- `store_*_bytes`: SQLite usage의 logical charge이며 실제 DB/WAL/RSS 크기가 아니다.
- `diff_objects_examined`는 frontier 알고리즘만 센다. E3 전체의 읽은 객체 수가 아니다.

무변경 payload 0, diff root read 2, reused subtree 11을 local O(1)로 확대 해석하지 않는다.
현재 full verification/recovery와 per-object pin preparation은 N에 의존한다. I25 보완 전에는
history-independent scaling gate, peak memory, Android power-loss를 PASS로 주장하지 않는다.

## process-crash oracle

별도 Dart child가 deterministic ready barrier에서 멈추면 부모가 SIGKILL한다.
fresh store와 독립 SQLite connection으로 complete G1 또는 G2, sequence, FK/integrity,
required pinned object 존재를 확인한다. E3 8개 경계는 summary에 기록했다.
예외 injection과 실제 process termination을 구별하며 hardware power-loss는 시험하지 않았다.

전체 구현과 잔여 보완은 [E3 구현 기록](../../t66e3-implementation.md)에 있다.

## I25 교정 조사 — 원본 보존 및 검증기 단독 결과

2026-10-13의 추가 조사다. 위 `summary.json` 및 원래 INCOMPLETE 기록은 덮어쓰지
않았다. 아래 결과는 **전체 publisher I25 완료 증거가 아니다.** 실제 AppState 경로의
healthy-session recovery 재사용, connection-bound accepted provenance, 증분 pin publication은
아직 연결하지 않았다. receipt `/2`도 기존 v3 publisher가 허용하지 않는다.

| 추가 artifact | 범위 |
| --- | --- |
| `i25-before.json` | 기존 publisher를 사용한 두 크기·각 9개 cold/identical/change/reopen/failure/retry 표본 |
| `i25-before-worktree.tgz` | 교정 전 계측 source·test의 작은 보존본; Git baseline과 함께 사용 |
| `i25-verifier-only.json` | 세 크기·각 6개 target에 대한 새 검증기와 별도 full oracle 비교 |

SHA-256:

```text
1909d3f2473aa096da1dbcbece63e7fb3e703e5d86a9a5511d8a75b491694420  i25-before.json
1ad514a7732c4307ed15c65122a085d1640c9bf0aea9e91f711bca29405693e5  i25-before-worktree.tgz
ed1935db90139d5bfe47033cc40e64dc2611a44f291e61afadc341afde7cdda1  i25-verifier-only.json
```

### 교정 전 실제 작업량

`segmented_i25_baseline_test.dart`는 원래 recovery/full verification/full pin 준비를
명시 호출한다. 원본 비용 재현용이며 최적화된 경로를 시험하는 테스트가 아니다.
object reads는 store의 성공한 hash-on-read 횟수, pin INSERT는 실행한 association
삽입 수다. transaction 계수는 시도 횟수이며 SQL statement 총수가 아니다.

| graph objects / raw rows | 시나리오 | recovery calls / 검사 객체 | object reads | full raw rows | pin INSERT |
| --- | --- | --- | --- | --- | --- |
| 190 / 50 | cold | 1 / 0 | 774 | 50 | 190 |
| 1,168 / 294 | cold | 1 / 0 | 4,688 | 294 | 1,168 |
| 190 / 50 | identical | 1 / 190 | 1,742 | 150 | 190 |
| 1,168 / 294 | identical | 1 / 1,168 | 10,548 | 882 | 1,168 |
| 190 / 50 | 세 번째 한 행 변경 | 1 / 380 | 2,138 | 200 | 190 |
| 1,168 / 294 | 세 번째 한 행 변경 | 1 / 2,336 | 12,904 | 1,176 | 1,168 |

identical 표본의 전체 시간/동기 publication 시간은 작은 graph 1,538,407/6,406µs,
큰 graph 11,222,396/2,521µs였다. 단일 HOST 표본이며 동시 회귀 부하를 포함한다.
원래 accepted pin을 동일 generation에서 지웠다 재삽입한 것은 아니다. 새 local UUID마다
전체 association을 복사하고, identical이면 그 임시 generation을 원래 cleanup으로
제거한다. 이 불필요한 INSERT가 N과 함께 증가한다.

pin DELETE/UPDATE, 모든 SQL 문장, recovery의 모든 metadata row, peak RSS는 별도
완전 계측하지 않았다. JSON에 없는 항목을 0이나 PASS로 해석하지 않는다.

### 검증기 단독 개선 — 전체 publisher와 구분

`segmented_incremental_verification_test.dart`는 실제 backend canonical target을 만든다.
old/new ordered frontier, changed row facts, canonical Patricia 경로 편집, hot/raw 검사를
실행하고 **재사용하지 않는 기존 complete verifier**와 roots·object/edge/fact counts·diff·
전체 graph 집합을 별도로 비교한다. 전체 집합 enumeration은 측정 구간 밖 oracle 작업이다.

| objects | identical object reads / index nodes | 한 행 변경 object reads / index nodes | hot/raw rows |
| --- | --- | --- | --- |
| 190 | 9 / 2 | 45 / 28 | 4 |
| 1,168 | 9 / 2 | 65 / 42 | 4 |
| 4,130 | 9 / 2 | 67 / 44 | 4 |

세 크기에서 동일 target, 한 행 변경, 8행 추가·삭제, 반복 변경의 full oracle가 일치했다.
큰 두 graph의 한 행 변경은 changed graph node 16개, tree frontier 검사 6개였다.
검증 bytes는 leaf 크기도 반영한다: identical에서 25,171 / 164,737 / 164,742 bytes다.
따라서 모든 크기에서 byte 비용이 상수라고 주장하지 않는다. I25의 changed bytes와
touched path 항목을 구분하며, 고정 H·유사 leaf profile에서의 단독 측정으로 한정한다.

재현 명령:

```sh
cd mobile
flutter test --no-pub --reporter expanded test/segmented_i25_baseline_test.dart
flutter test --no-pub --reporter expanded \
  test/segmented_incremental_verification_test.dart \
  test/segmented_root_pin_model_test.dart
```

각 명령은 자체 temporary synthetic 환경을 만들며 JSON을 각각
`/tmp/money-note-e3-i25-before.json`, `/tmp/money-note-i25-verifier-only.json`에 쓴다.
원본 snapshot은 **다른 새 disposable checkout**에서만 비교하고 현재 uncommitted tree를
그 위에 덮어쓰지 않는다. Snapshot 안에 없는 committed E1/E2 files는 시작 Git baseline이
제공한다. 새 source로 baseline 명령을 실행해 원본 시점 source와 동일하다고 주장하지 않는다.
특히 교정 후 `recoverAcceptedGeneration`은 같은 세션에서 proof를 재사용하므로,
현재 tree의 baseline test는 legacy full verification/pin workload일 뿐 원래 recovery
반복 비용까지 재생하지 않는다. 교정 전 비용의 정확한 재현에는 위 snapshot의
`store_publication.dart`를 포함한 원본 source와 시작 Git baseline을 함께 사용한다.

### 미연결 경계와 안전 제한

검증기 단독 결과는 store-bound freshness나 pin COMMIT을 증명하지 않는다. 데이터 proof는
AppState authority가 아니며, graph summary는 schema/connection/accepted sequence/외부
COMMIT 변화에 결합된 적절한 유효성 경계 없이는 실제 publisher에서 재사용할 수 없다.
`PRAGMA data_version`만 복사한 영구 verified flag를 도입하지 않았다.

root 기반 pin의 독립 in-memory SQLite 모델 2건은 current/previous/shared descendants와
COMMIT/ROLLBACK을 검사한다. 이것은 앱 schema migration이나 실제 publisher의 증거가 아니다.
기존 v3 pin·receipt·trigger를 보존하는 additive 확장과 기존 cleanup 연결은 도구 안전
검토에서 별도 범위 승인을 요구해 적용하지 않았다. 보호 trigger를 DROP하거나 객체를
GC하는 변경으로 우회하지 않았다. 전체 publication의 before/after·pin write scaling은
미완료이며 I25 판정은 계속 INCOMPLETE다.

## 승인 후 실제 publisher 통합

소유자가 v3 pin/receipt/보호 DDL 보존을 전제로 additive root-pin 확장을 승인했다.
이후 owning store의 accepted data provenance와 E2/E3 경로를 연결하고 isolated publication
profile v4를 추가했다. 위의 미연결 상태는 중간 이력이다. production SQLite schema와
기존 OfflineBaseline/B/J/Snapshot 저장소를 migration하지 않는다.

현재 경로는 다음처럼 나눈다.

- 초기/restart/불확실한 저장 상태: complete accepted/current previous recovery.
- 정상 동일 handle: exact schema/profile/실제 pointer·receipt·data_version 검사 후 data proof 재사용.
- target 검증: complete frontier diff, canonical Patricia path edits, required hot/raw hash-on-read.
- 저장: owning connection에서 검증한 `/2` 후보에 root pin 4개만 준비한다.
- publication: 기존 AppState guard와 실제 accepted-base/sequence CAS 뒤 즉시 동기 COMMIT.
- cleanup: 원래 current/previous 제외 조건 유지; unaccepted/superseded metadata만 해제한다.

`segmented_i25_publication_test.dart`는 실제 backend fixture의 190/1,168/4,130 objects와
bounded changes로 cold/identical/mutate/8-row insert/delete/repeated/restart/rollback/retry를
실행한다. 독립 complete verifier, backend object sets, direct SQLite의 current/previous
recursive closure, 실제 pin-row counts와 indexed query plan을 비교한다. 교정 후 결과는
`i25-publication-after.json`에 따로 추가한다. 원본 `i25-before.json`은 절대 덮어쓰지 않는다.

동일 target에는 새 observation/terminal metadata 요청이 남는다. 0 object payload requests를
0 network traffic으로 표현하지 않는다. 새 root pin INSERT는 4회이며 identical의 임시
generation 해제도 4회다. superseded generation 정리가 함께 있으면 pin DELETE가 8회일 수
있다. 바뀌지 않은 수천 descendant pin rows를 지우고 다시 쓰지 않는다.

재현:

```sh
cd mobile
flutter test --no-pub --reporter expanded test/segmented_i25_publication_test.dart
flutter test --no-pub --reporter expanded \
  test/segmented_publication_test.dart \
  test/segmented_publication_crash_test.dart \
  test/segmented_authority_test.dart \
  test/segmented_diff_integration_test.dart
```

최신 JSON은 `/tmp/money-note-i25-publication.json`에 생성한다. 여러 full/targeted 실행이
동시에 있으면 마지막 작성자를 혼동하지 않도록, final source의 단일 완료 실행 결과와
`accepted_metadata_reads` counter 및 phase timing fields를 확인한 뒤 보존한다.
complete oracle의 전체 graph 검사와 independent SQLite inspection은 실제 publisher의
작업량 측정 구간 밖이다.

`work.pin_inserts/deletes`는 실제 SQL 실행·cascade 대상의 시도 횟수이며 rollback에서
커밋되지 않은 쓰기도 포함할 수 있다. 성공 결과의 persisted roots/closure를 별도로 검사한다.
`object_reads/verified_bytes`는 E1 store의 hash-on-read 작업이며 transport의 모든 임시 hash
호출까지 합한 값은 아니다. `graph_nodes_examined`, `index_nodes_examined`, full raw/fact
rows 및 transferred bytes를 함께 사용한다. `transactions`는 attempts이며 모든 SQLite
statement 총수가 아니다. query plan과 source 검토로 정상 root lookup이 indexed search이고
legacy full pin COUNT가 valid frame에서 생략됨을 확인한다.

startup/restart full recovery, invalid provenance 및 one-time v3 migration/old pin retirement는
별도 fallback 비용이다. 다른 handle의 실제 COMMIT은 보수적으로 provenance를 무효화한다.
SQLite가 no-op UPDATE를 생략할 수 있어 외부 변경 test는 실제 새 staging row COMMIT을
사용한다. 읽지 않은 bitrot 즉시 탐지·peak RSS·hardware power-loss·production throughput은
이 결과로 주장하지 않는다. E4/R1 및 일반 사용자 활성화는 여전히 금지한다.

post-COMMIT readback 뒤에도 검증 때의 data_version을 다시 비교하고, frame에는 원래
counter만 저장한다. 외부 COMMIT 뒤 새 counter를 오래된 proof에 붙이지 않는다.
외부 valid staging COMMIT과 changed index-object corruption을 이 경계에 주입하는 2개
결정적 시험은 각각 committed 오류/complete recovery와 committed 오류/fail-closed를
요구한다. 이것은 clean rollback이나 이전 authority 복원으로 표현하지 않는다.

### 보존한 최종 before/after 수치

최종 source의 full suite 완료 후 생성된 `i25-publication-after.json`은 33개 표본이며
SHA-256은 `4760a0c5c63487c15f50c0fcfab84efc84d39c1de91cb4cd334851210cec31b4`다.
원래 3개 artifact의 checksum은 위와 같고 변경하지 않았다.

| objects | identical reads 전→후 | full raw rows 전→후 | pin INSERT 전→후 | 한 행 변경 reads / index nodes 후 |
| --- | --- | --- | --- | --- |
| 190 | 1,742 → 9 | 150 → 0 | 190 → 4 | 59 / 28 |
| 1,168 | 10,548 → 9 | 882 → 0 | 1,168 → 4 | 85 / 42 |
| 4,130 | 교정 전 미측정 → 9 | 교정 전 미측정 → 0 | 교정 전 미측정 → 4 | 87 / 44 |

정상 반복/작은 변경의 full recovery/full verification은 0이다. cold/restart/rollback 후
retry는 필요한 full 검증을 수행한다. 성공 publication의 actual accepted metadata read는
세 크기에서 7회이며 schema/pointer/receipt를 생략하지 않는다. root lookup은 실제
`SEARCH generation_roots USING PRIMARY KEY (generation_id=?)`였다.

4,130-object 표본은 cold 전체 237.359초, 동일 target 전체 236.514ms, 한 행 변경 전체
1,544.394ms다. 동일 target verification/critical/readback은 73.287/4.437/1.464ms,
한 행 변경 verification/critical은 164.813/28.430ms였다. restart recovery는
6,487.663ms에 retained objects 8,260개를 검사했고, 직후 반복은 다시 read 9회였다.
33개 단일 HOST 표본에서 observed critical 범위는 4.437–48.514ms다.

timer와 counter는 store open 뒤부터 측정한다. open의 기존 quick/FK/usage O(N) scan을
포함한 전체 startup latency를 측정했다고 주장하지 않는다. cold 비용의 많은 최초 object
transactions/fixture 전송과 독립 complete oracle 비용을 정상 incremental 경로와 구별한다.
이 수치를 median/p95, 최악 busy timeout, Android latency나 production 성능으로 외삽하지 않는다.
§35의 전체 대규모 integrated/device/압축 비교 matrix까지 완료한 증거는 아니다.
