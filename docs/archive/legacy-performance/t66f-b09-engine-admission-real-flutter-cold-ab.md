# T6.6F-B09 — 정확한 엔진 입장 및 실제 Flutter cold 비교

판정은 **PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE**다. 성능 처분은 **MIXED — END-TO-END BENEFIT NOT ESTABLISHED**다. N=1k 네 조건 모두 E3 publication·E4 accepted read와 독립 금융 검증을 완료했다. 그러나 OFF는 개선되고 ON은 악화돼, 사전 gate에 따라 N=5k를 실행하지 않았다. B08을 기본 기준 엔진으로 채택하지 않고 실험 후보와 증거로 보존한다.

## 1. 기준 소스와 비교 격리

| 정체성 계층 | 검증값 |
| --- | --- |
| 시작 HEAD / branch | ebcbd54d90eeee194a04b9eea6367f446ee2fd28 / main |
| 원 B03 payload | 8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8 |
| 원 B03 engine | 7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c |
| B08 payload | a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94 |
| B08 engine | 5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c |
| B09 통합 후보 payload | beb2fe5ef2ab02feccd9ce0edc1f37e658bf10a47c9104aa1916627251b0149e |

원 B03 archive SHA `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5`, B08 archive SHA `cb89861bedaa998ce3c53789f76ba92a412c4eeff9a05f34a1f49d8b25067e22`를 실제 읽어 검증했다. 고정 Git commit 위에 각 source-only overlay를 적용하고 바이트·mode·나머지 Git blob을 대조했다. Engine SHA는 `app/**/*.py`, `isolated_sync/*.py`, judgment message YAML의 실제 경로→SHA map을 `isolated-d3a/1` C1으로 인코딩한 SHA다. Payload SHA와 다른 계층이다. [복원 및 전체 input map](../../benchmarks/t66f-b09/source-reconstruction.json).

A/B의 engine input 차이는 `backend/app/db_migrations.py` 하나다. 두 variant의 `observation.py`는 원 B03 SHA `635e17038f4cc11d7db59dd6208aa1d1fbfd5a5750b04b20c40cc7714c399a3e`로 같아 B05 `_lookup` 변경이 섞이지 않았다. Live dirty 소스와 staged 내용은 사용·교체하지 않았다. 새 admission은 격리 후보에만 적용했다. [격리 증명](../../benchmarks/t66f-b09/optimization-isolation.json).

## 2. 승인 범위와 exact admission

사용자 B09 §3의 검증된 engine 하나 추가·직접 artifact·exact 기대값 전이 권한만 적용했다. 보호를 해제하거나 protocol·연결 lifetime·거래 범위·cache 구현을 바꾸지 않았다. 다음 변경은 모두 별도 실험 후보 안에 있다.

| 기존 경로 | 직접 변경 |
| --- | --- |
| mobile/lib/src/segmented/protocol.dart | 현재 engine을 B08 exact SHA로 지정하고 B05 SHA를 별도 exact 항목으로 보존 |
| mobile/assets/segmented/isolated-release-artifacts.json | 실제 B08 source로 canonical generator 재생성 |
| docs/specimens/t66d3b-release-artifacts.json | mobile artifact와 바이트 동일한 재생성 |
| mobile/test/segmented_adapter_isolation_test.dart | B09→B05-A→기존 protocol 역변환 guard와 B08-only DB migration 역변환 guard |
| mobile/test/segmented_engine_admission_b05a_test.dart | 기존 승인 항목 보존 + B08 양성·payload/임의/변조 음성 검사 |

직접 추가한 테스트는 `backend/tests/test_engine_admission_b09.py`, `mobile/test/segmented_engine_admission_b09_test.dart`다. Source-lock review와 변조 witness는 해당 테스트의 고정 입력으로만 포함한다. 기존 보호 기록과 기대 SHA를 덮어쓰지 않았다. [정확한 변경 inventory·전후 SHA](../../benchmarks/t66f-b09/admission-consistency.json), [admission diff](../../benchmarks/t66f-b09/admission.patch), [추가 guard diff](../../benchmarks/t66f-b09/guard-dependent-update.patch), [source-lock 전이](../../benchmarks/t66f-b09/source-lock-review.json).

유지한 기존 engine은 `f84dacdf…94b3`, `7ad114bc…8d6c`, `afe26b70…bdf5`, `f34aef25…449d` 네 개다. 여기에 `5861d6d2…e3d2c`만 추가했다. 전체 SHA는 manifest에 있다. Prefix·wildcard·동적 응답 digest·경고 전환·개발 우회는 없다. 모든 real run에서 같은 새 client가 A 또는 B08을 각각 정확히 인정했다.

## 3. 원 artifact 실패 재현과 repair

수정 전 `test_release_artifact_hashes_exact_bytes_and_target`를 실행해 1 FAIL을 재현했다. 원 artifact는 B03 engine을 담았고, 실제 B08 `release_bundle()`과의 차이는 `financial_engine` 항목뿐이었다. `versions`, raw schema, projection schema, policy registry는 같다. Hash 기대값을 임의로 바꾸지 않고 `isolated_sync.artifacts.release_bundle()`을 두 번 실행해 결정성을 확인한 뒤 기존 compact JSON 형식으로 두 checked-in artifact를 갱신했다.

새 두 JSON의 공통 SHA는 `ca874b081b5feb524fedb6699f40ceb6f5f312d077f170c0ae87ce6568702731`다. 그 안의 financial engine 원문은 별도로 다시 해시해 B08 engine과 일치시켰다. 원 test는 수정 없이 PASS했다. 원 test를 그대로 호출하면서 artifact source bytes·declared hash·version을 각각 변조하는 음성 테스트도 세 건 모두 거부됐다. [원 실패](../../benchmarks/t66f-b09/artifact-before.log), [focused 결과](../../benchmarks/t66f-b09/backend-focused.xml).

## 4. source guard와 음성 경로

원 protocol guard는 B09 exact 두 조각을 되돌린 SHA를 B05-A SHA와 대조하고, 기존 B05-A 역변환과 기존 보호 SHA 검사를 계속 실행한다. DB migration guard도 B08의 실제 새 SHA를 먼저 확인한 뒤 검증된 함수 조각만 역변환하여 기존 `24c14452…390ea`와 비교한다. 관련 없는 소스 변경은 두 단계 중 하나에서 실패한다. 초기 Flutter focused의 이 보호 SHA 실패 1건을 보존하고, 직접 전이에 한정해 해소했다.

원 엔진·B05·이전 두 엔진·B08의 양성 입장, 한 글자 SHA 변조, 임의 64자 SHA, B08/B05 payload SHA 오용, 소스 manifest 변조 SHA의 음성 경로를 실제 테스트했다. B08 `db_migrations.py`의 manifest hash를 변경해 얻은 미승인 engine `7f0a7c9cbbd1cf2240d0941962499f9eadd926e2d88df138cf6c051895d5dae4`도 거부됐다. [B08 변조 입력](../../benchmarks/t66f-b09/B08-mutation-witness.json), [실제 음성 검사](../../benchmarks/t66f-b09/flutter-B08-mutation-after.jsonl).

## 5. 기능 및 회귀 결과

| 검사 | 새 결과 |
| --- | --- |
| B08 dedicated schema/cache | 22 PASS |
| Backend focused: B08 + B09 admission + 원 artifact | 31 PASS |
| 완전 backend, 1회 | 1910 PASS + 1540 subtest PASS; 0 FAIL/ERROR/SKIP |
| Flutter 영향 범위 | 208 PASS |
| 추가 B08 소스 변조 음성 검사 | 1 PASS |
| Flutter focused, 최종 | 93 PASS |
| Cold driver compile-only | 1 PASS, cold 요청 없음 |
| Frontend npm run build | PASS |

완전 backend는 CPython 3.12.3에서 1,268.798초(JUnit)였다. 명령·환경·JUnit·기존 historical reproducer assertion을 유지하는 출력 경로 adapter를 보존했다. Flutter 영향 범위는 admission/protocol/source guard, E2/E1 경계, I25/E3, E4 provenance, P0 lineage, B03 core/HTTP/IC01/IC02를 포함하며 554.870초였다. Full Flutter를 추가 반복하지 않았다. [회귀 요약과 정확한 명령](../../benchmarks/t66f-b09/regressions.json), [완전 backend JUnit](../../benchmarks/t66f-b09/backend-full.xml), [Flutter 원시 이벤트](../../benchmarks/t66f-b09/flutter-affected.jsonl).

Cache key는 DB 경로·connection·schema_version label이 아니라 기대 schema SQL의 정확한 전체 문자열이다. Cached 값은 연결·cursor·거래·mutable schema를 보유하지 않는 tuple/frozenset이며 cache capacity는 1이다. Actual DB의 PASS/FAIL은 저장하지 않는다. 전용 테스트는 exact SQL key 전이, cache 용량 1, 재귀적 불변 tuple/frozenset, DB 별 독립 조회, 실제 trigger 삭제·변조·추가, 잘못된 authoritative revision state, migration/user_version 전이, 오류 보존, 동시 서로 다른 key를 검증한다. Actual SQL 조회 순서도 원 B03 reference와 같았다. B03 instrumentation 파일은 바이트 그대로다. 새 후보의 독립 IR07 인증은 주장하지 않는다.

초기 task-owned 변조 테스트의 `c1.dart` import 누락과 guard 적용 도구의 cwd 실수도 원시 오류 로그에 남겼다. 제품 회귀로 분류하지 않았고, 직접 test/import·도구 경로만 수정한 뒤 focused PASS를 확인했다. 이 과정에서 cold 실행은 없었다. 전체 suite는 한 번만 수행했다.

## 6. Fixture·runtime·cold 조건

보존 N=1k template의 compressed/uncompressed SHA를 검증했다. 같은 금융 행 위에 B08 engine view만 준비해 만든 공통 template SHA는 `faa9c10e2b6474734f631f8373a803e1f8a8e7115208bd10ae4a8cc997aeed19`다. A/B raw/index/control 참조, financial hot state, reachable 4,132개와 canonical 2,749,721B는 같다. 각 variant는 같은 공통 template의 독립 disposable backend DB와 objects=0·accepted ID=null·sequence=0인 새 client DB를 사용했다. [fixture manifest](../../benchmarks/t66f-b09/fixture-n1000.json), [보존 template](../../benchmarks/t66f-b09/template-n1000.sqlite.gz).

N=1,000, 고정 workload는 current ledger 105행 + 기타 authority 35행, hot 87,364B/control 3,178B다. Binding에 별도 scalar H 숫자가 없으므로 이 실제 구성을 기록한다. Cold는 delta workload가 아니므로 D는 null이다. 이전 B04/B05-A 생성 규칙을 유지했다. Backend root/view 준비와 고정 control exported_at은 primary timing 밖이다. 측정은 **준비된 backend view에 대한 client cold acquisition**이며 미리 staged된 client를 사용하지 않았다.

CPython 3.12.3/backend SQLite 3.45.1, Flutter 3.47.4/Dart 3.13.3, client SQLite 3.53.4를 사용했다. Client native library SHA는 `0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace`다. 95.54GiB 이상의 측정 직전 여유 공간과 경쟁 benchmark 부재를 확인했다. 임시 loopback TLS만 사용하고 18080/18081에는 요청하지 않았다. [Preflight](../../benchmarks/t66f-b09/preflight-n1000.json).

순서는 결과를 보기 전 **A OFF → B08 OFF → B08 ON → A ON**으로 고정했다. 조건당 1회다. 같은 Flutter process에서 실행했으므로 JIT/allocator·OS cache 순서 효과를 통제한 독립 반복 표본은 아니다. Cache flush/CPU affinity/thermal 제어는 하지 않았다. N=5k 조건부 순서 A ON→B08 ON도 미리 고정했지만 실행하지 않았다. [계획](../../benchmarks/t66f-b09/plan-n1000.json), [사전 gate](../../benchmarks/t66f-b09/escalation-policy.json).

## 7. 계측 범위와 한계

원 B03 collector·SQL observer·sys.monitoring 구현을 변경하지 않았다. B09 task-owned harness만 connect/open/schema/finalization/revision/parser를 감싸고, `_statements` 호출과 실제 sqlite_master trigger 조회 수를 센다. Context-local row로 요청을 분리하고 monotonic clock을 사용한다. 이 wrapper는 IR07이 감사한 소스 자체가 아니며 양 variant와 양 mode에 동일하게 적용한 실험용 계측이다. DB 검사를 우회하거나 cache를 측정 편의상 clear하지 않았다.

각 서버 시작 시 B03 OFF의 짧은 순수 parser 64쌍으로 wrapper 추가 median 2,443.5–2,823.5ns를 관측했다. 이는 긴 SQL·ON 계측 비용의 상한이나 전체 observer CPU 추정이 아니다. Compilation 감소로 실행되지 않는 parser wrapper 비용도 일부 사라지므로, 세밀한 시간 절감 모두를 제품 CPU 절감으로 등치하지 않는다. [실험 probe](../../benchmarks/t66f-b09/probe.py), 각 raw의 `init.json` calibration.

Primary 총 시간은 `AppState.publishSegmentedForIsolatedUse` 진입부터 publication 반환 후 bounded E4 accepted read 완료까지다. UI/OfflineReady 완료가 아니다. 독립 전체 금융 oracle·SQLite backup은 primary 밖이다. E2 표기는 초기 recovery를 포함한 E3 시작 전 envelope이고, E1 SQL API는 그 안에 중첩된다. Handler는 HTTP transport 안에, schema/revision/parser는 connect 안에 중첩된다. 아래 행들을 더해 총 시간을 만들지 않는다. HTTP−handler도 순수 network 시간이 아니다.

## 8. 실제 cold 결과와 완료 증거

| 조건 | 총 cold(s) | Handler(s) | Compile | 실제 DB inspection | 상태 |
| --- | --- | --- | --- | --- | --- |
| n1000-0-A-off | 35.230866 | 21.904725 | 248 | 248 | E2/E1/E3/E4 완료 |
| n1000-1-B-off | 29.140462 | 16.563506 | 1 | 248 | E2/E1/E3/E4 완료 |
| n1000-2-B-on | 33.435903 | 21.710116 | 1 | 248 | E2/E1/E3/E4 완료 |
| n1000-3-A-on | 31.300743 | 19.886078 | 248 | 248 | E2/E1/E3/E4 완료 |

| 비교 | A(s) | B08(s) | 절감(s) | 개선율 |
| --- | --- | --- | --- | --- |
| OFF | 35.230866 | 29.140462 | 6.090404 | +17.287125% |
| ON | 31.300743 | 33.435903 | -2.135160 | -6.821436% |

계산은 `100 × (A − B08) / A`이며 양수는 B08이 빠름을 뜻한다. 조건당 한 값이므로 median도 그 값과 같고 표본 분산·신뢰구간·통계적 유의성을 제시하지 않는다. 과거 B04/B05-A/B05-B 값을 새 matched control로 사용하지 않았다. [모든 timing/counter와 pair](../../benchmarks/t66f-b09/cold-ab-results.json), [실제 실행 명령·watchdog](../../benchmarks/t66f-b09/cold-execution-n1000.json).

각 run은 실제 D3→TLS HTTP→E2→E1 경로에서 object 4,132개를 완료했다. 요청 82건은 manifest 2 + object packet 79 + release 1이다. Packet과 object는 같지 않다. 새 observation 하나와 같은 observation의 terminal 재검사이며 갱신/추가 attempt로 세지 않는다. 실제 UTC/900초 lease/기존 attempt 3을 유지했고 expiry는 없다. 서버 collector 82 issued/82 closed, pending=0 및 completion error 없음, client collector close 성공이다.

Connect는 모든 요청에서 3회, 총 246회다. Revision validation/실제 trigger inspection은 248회이며 두 manifest 요청에서 각각 1회가 추가된다. B08의 cache는 247 hit/1 miss, 측정 종료 currsize=1이다. 원 B03은 매번 compile 248회다. 실제 DB 검사 248회는 줄지 않았고, 원 PASS/FAIL 결과를 재사용하지 않았다.

## 9. 단계별 실제 시간

| 측정 구간(s) | A OFF | B08 OFF | A ON | B08 ON |
| --- | --- | --- | --- | --- |
| backend handler, inclusive | 21.904725 | 16.563506 | 19.886078 | 21.710116 |
| backend process CPU, inclusive | 21.800306 | 16.509820 | 19.848238 | 21.668441 |
| HTTP send→body 완료, inclusive | 22.336887 | 16.903891 | 20.193587 | 22.043296 |
| E2 + 초기 recovery envelope | 31.057852 | 24.934824 | 27.509718 | 29.752643 |
| E1 SQL API, E2/E3/E4에 중첩 | 5.152978 | 4.817730 | 3.953696 | 4.032524 |
| E3 envelope | 4.087330 | 4.120641 | 3.705878 | 3.598705 |
| E3 native transaction | 0.015764 | 0.017276 | 0.005686 | 0.006520 |
| E3 readback | 0.002010 | 0.001699 | 0.001648 | 0.001684 |
| bounded E4 | 0.082304 | 0.083145 | 0.082298 | 0.082506 |
| connect, inclusive | 6.140642 | 3.493112 | 6.198693 | 5.007745 |
| schema, inclusive | 6.013239 | 3.357918 | 6.071352 | 4.849600 |
| revision validation, inclusive | 4.246959 | 1.787107 | 3.651497 | 2.112458 |
| expected parser만 | 1.699356 | 0.005866 | 1.468490 | 0.006034 |
| cache gate, miss compile 포함 | 0.000000 | 0.008046 | 0.000000 | 0.008220 |

Backend manifest generation의 자체 total metric은 실행 순서대로 239.758498/157.322625/214.019980/221.025161ms다. 이는 준비된 view의 실제 요청 내 생성/확인 부분이며 backend cold root 생성 O(N) 전체 시간이 아니다. 각 원래 validation/financial/pin/commit metric도 run manifest에 보존했다. Inclusive total과 자식 metric을 합산하지 않았다.

## 10. 실제 금융·publication·read 동등성

| Run | Accepted generation ID | Sequence |
| --- | --- | --- |
| n1000-0-A-off | e46781ee-e781-409e-a6d5-adf541f7c1fb | 1 |
| n1000-1-B-off | 2eab671b-d847-4390-a3b0-5a1cb18c99a8 | 1 |
| n1000-2-B-on | 11159714-5c6e-4317-ac0e-910e35d799a0 | 1 |
| n1000-3-A-on | 7924fe77-cf21-405a-95a9-17321b5cce63 | 1 |

각 DB의 native accepted row와 4,132개 committed generation object를 읽어 검증했다. 종료 시 staging row도 4,132개로 기록돼 있으며 이를 0으로 바꿔 보고하지 않는다. Client/backend의 지원 SQLite backup 8개를 보존했고 graph hash set·raw SQL 값·foreign_key_check·quick_check를 독립 oracle로 확인했다. 모든 run의 금융 hot state digest는 `6174fac48d00c00cf015d8dbfdfaddea67bec633c0aa099ac7b932f6a423ad22`다. [독립 검증 예](../../benchmarks/t66f-b09/raw/n1000-3-A-on/independent-verification.json).

A의 sync_root는 `892ddfa9d2b5b314867b02a0658db2adf50c1d1a1ad848e8f53507b802796002`, B08은 `922e827aa8c3ba5e8b2392402e18f63f2785cc89c263844f330ba7de9a9719d9`다. Engine-dependent hot hash/context 차이로 설명되며 동일 engine의 ON/OFF target와 금융 digest는 각각 같다. Raw/index/control 참조와 사용자 금융 값은 engine 간 동일하다. 다른 engine의 raw hot hash를 무리하게 같다고 주장하거나 금융 차이를 normalize하지 않았다.

## 11. B03 논리 비용 해석

ON에서 backend/client/SQL의 **모든 counter key/value가 A와 B08 간 정확히 같았다**. 사라진 작업은 immutable expected SQL 계약의 반복 compilation이고 actual DB validation·필수 canonical 검사는 그대로다. OFF counter는 수집하지 않았으므로 null이며 논리 비용 0을 뜻하지 않는다.

| ON 측정 cohort, 두 engine 동일 | 실제 값(B) |
| --- | --- |
| Backend hash 입력(auth 포함) | 27561928 |
| Backend JSON 제출/완료 | 81972017 / 81972017 |
| Client hash 입력(checksum 포함) | 22880416 |
| Client C1 제출/완료 | 37516845 / 37516845 |
| Client SQL text/BLOB attempted | 4701048 |
| Client SQL text/BLOB effective/committed | 4424134 / 4424134 |
| Backend SQL text/BLOB attempted/effective/committed | 9583 / 9583 / 9583 |

SQL 표는 B03의 logical text/BLOB payload를 outcome별로 합친 값이며 scalar의 물리 저장 크기를 만들어 더하지 않았다. C1/JSON 제출·완료 값은 collector의 실제 입력 accounting이고 재방문도 센다. Disk 성장·HTTP bytes·VFS I/O와 다르며 미완성 §35 grid 열을 새로 채운 것으로 간주하지 않는다. [논리 counter 계산·범위](../../benchmarks/t66f-b09/logical-counter-summary.json).

## 12. 시간 변화와 인과 한계

OFF에서 connect는 2.647530초, schema는 2.655320초 줄었다. ON에서도 connect는 1.190949초, schema는 1.221752초 줄었다. 반복 expected parser 작업 제거와 실제 schema 검사 보존은 국소 수준에서 재확인됐다.

그러나 ON에서 handler 전체는 1.824038초 늘었다. 순차 요청과 비중첩 connect 경계로 계산한 handler−connect 부분이 3.014986초 증가했다. 같은 원 `_lookup`의 inclusive 시간도 8.414787→10.396167초로 변했다. Lookup과 schema 경계의 모든 관계를 exclusive로 입증하지 않았으므로 이 둘을 더해 잔여 시간을 맞추지 않는다. Lookup 코드/호출 수는 같아 이 차이를 B08의 함수 변경 탓으로 단정할 수 없다.

A의 ON/OFF 총 시간 비는 0.888447, B08은 1.147405다. A에서 ON이 OFF보다 빨랐다는 사실 자체가 이 작은 순서 표본의 변동 한계를 보여준다. Observer CPU, JIT, host scheduling, SQLite, network 중 어느 것이 원인인지 분리되지 않았다. Cache gate 자체 0.008046/0.008220초는 miss compile을 포함하며 순수 cache 관리 overhead로 부르지 않는다. 전역 원인 결론이나 유의성 주장은 하지 않는다.

N=5k의 과거 6.619초 조건부 parsing 예산은 실측 절감값이 아니다. 이번 object packet은 79개로 5k의 332개와 다르고, ON 전체 시간이 개선되지 않았다. 이를 5k 또는 100k end-to-end 속도로 곱셈 외삽하지 않는다.

## 13. N=5k gate와 실행 상한

N=1k 4/4 완료, cache compilation 감소, actual DB 검사 보존, schema 단계 개선, 기능·자원 무결성은 통과했다. 하지만 ON handler와 전체 cold는 악화됐고 OFF/ON의 큰 방향 차이에 대한 인과 설명이 없다. 실용적인 end-to-end 확대 근거와 discrepancy 조건을 충족하지 못해 **NOT JUSTIFIED**다. N=5k B08 fixture 준비나 cold pair를 시작하지 않았다. Planned JSON은 실행 증거가 아니다. 추가 반복도 없다. [gate 판단](../../benchmarks/t66f-b09/escalation-decision.json).

실제 새 full cold는 N=1k 4건, N=5k 0건, N=10k/50k/100k 0건이다. 총 상한 6 중 4를 사용했다. Cold runner outer watchdog 1,200초를 실제 설치했고 149.384989초의 전체 cohort 시간은 정확한 execution manifest를 기준으로 한다. Watchdog는 observation TTL/attempt를 연장하지 않는다. Android emulator·기기는 사용하지 않았다.

## 14. 성능 처분과 채택

실험 완료와 성능 처분을 분리한다. Exact admission·release artifact·회귀·네 실제 경로·E3/E4·금융 oracle가 통과했으므로 B09의 자격 검증은 PASS다. OFF +17.287125%, ON −6.821436%의 서로 다른 방향 때문에 성능 처분은 MIXED다. B08은 **EXPERIMENTAL**로 보존하고 선호 성능 기준은 원 B03으로 유지한다. 기본 채택·production·R1 승인을 권고하지 않는다. [최종 처분](../../benchmarks/t66f-b09/performance-disposition.json).

## 15. 통합 후보와 재구성

907파일의 새 source-only 통합 후보 payload는 `beb2fe5ef2ab02feccd9ce0edc1f37e658bf10a47c9104aa1916627251b0149e`다. Engine은 B08 `5861d6d2…e3d2c`로 유지된다. Archive SHA는 `8b4079ebe0445ceefa905837c1e557b0efeefda91c0ab95fefef4aa760f20433`다. 기존 B03/B08 archive는 그대로 두었다. 새 Git archive + source overlay를 별도 workspace에서 재구성해 모든 바이트/mode, engine, 두 artifact의 source 일치를 PASS했다. [후보 manifest](../../benchmarks/t66f-b09/candidate-source-manifest.json), [source archive](../../benchmarks/t66f-b09/integration-source.tar.gz), [재구성 결과](../../benchmarks/t66f-b09/candidate-reconstruction.json).

재현 시 manifest의 base commit을 별도 경로에 풀고 archive의 `source/` overlay를 적용한다. `metadata/source-manifest.json`의 정렬 entries C1-compatible JSON SHA 및 각 파일 SHA/mode를 대조한 뒤 `release_bundle()`과 두 artifact를 다시 비교한다. 회귀 명령은 regressions.json, 고정 순서·fixture·driver는 plan/fixture/probe/server/cold_test에 있다. 기존 archive나 dirty worktree 위에 덮어쓰지 않는다. 재구성 성공은 독립 IR07 재감사를 뜻하지 않는다.

## 16. Source·Git·역사 증거 보존

사전 visible 파일 6,276개의 SHA/mode/bytes를 종료 시 다시 대조해 변경 0개다. HEAD·main branch·staged path/mode/blob/stage와 index bytes를 보존했다. Index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged 목록 SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. Live B05 uncommitted optimization/admission과 기존 모든 증거는 그대로다. 제품·allowlist·release에 대한 새 수정은 격리 B09 source archive에만 있다. [시작](../../benchmarks/t66f-b09/preservation-before.json), [종료](../../benchmarks/t66f-b09/preservation-after.json).

## 17. Artifact 정리

한 scratch root `/tmp/money-note-t66f-b09-20261026`만 사용했다. 완료한 focused/build 산출물은 단계 경계에서 정리했다. 이후 모든 서버 종료·matched client/backend backup 8개 및 SHA·source archive 재구성을 확인하고 task-owned scratch 626,454,871B를 제거했다. B09 분석 pycache도 제거했다. Native library는 기존 B05-A 보존본을 검증하여 재사용했고 큰 Flutter build tree는 하나만 만들었다. Raw timing/counters, 8개 일관 DB gzip, fixture, source archive, 회귀와 재현 도구는 보존했다. 과거 DB/WAL/cache는 삭제하지 않았다. [정리 기록](../../benchmarks/t66f-b09/cleanup.json).

## 18. 남은 gate와 다음 행동

원 B03 독립 correctness는 IR07 CLOSED로 유지한다. B01/B02 CLOSED, B04 bounded PASS, B05 experimental, B05-A/B05-B PASS, B07 material attribution PASS, B08 local safety/benefit PASS를 유지한다. 이번 host N=1k 결과로 Phase B five-point grid나 large-N E3 I25를 완료하지 않았다. Phase B는 INCONCLUSIVE, N=100k instrumented cold는 NO-GO다. 역사 P03 397,146/400,532 staging 실패를 성공으로 바꾸지 않으며 새 100k는 없다. Real-Device Gate는 DEFERRED, Android memory/VFS/power는 NOT VERIFIED, R1 activation CLOSED, deployment NOT AUTHORIZED다.

**다음 행동: B08을 실험 후보와 증거로만 보존하고 추가 B08 성능 캠페인을 종료한다.**

## 최종 상태

```text
T6.6F-B09 EXACT ADMISSION AND REAL FLUTTER COLD A/B:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

BASELINE B03 PAYLOAD SHA:
8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8

BASELINE ENGINE SHA:
7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c

B08 CANDIDATE PAYLOAD SHA:
a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94

B08 ENGINE SHA:
5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c

B08-ONLY SOURCE DELTA:
VERIFIED

EXACT ENGINE ADMISSION:
PASS

PREVIOUS ENGINE IDENTITIES:
PRESERVED

UNKNOWN ENGINE REJECTION:
PASS

RELEASE ARTIFACT CONSISTENCY:
PASS

ORIGINAL EXACT IDENTITY FAILURE:
RESOLVED

BACKEND REGRESSION:
1910 PASS + 1540 subtest PASS

FLUTTER AFFECTED REGRESSION:
209 PASS

CONTRACT COMPILATION REDUCTION:
각 ON/OFF 248 → 1; cache 247 hit / 1 miss

ACTUAL DB INSPECTION:
PRESERVED — 각 248 → 248

INVALID SCHEMA REJECTION:
PASS

N=1K BASELINE OFF:
35.230866 s

N=1K B08 OFF:
29.140462 s

N=1K OFF IMPROVEMENT:
+17.287125%

N=1K BASELINE ON:
31.300743 s

N=1K B08 ON:
33.435903 s

N=1K ON IMPROVEMENT:
−6.821436%

N=1K REAL FLUTTER COLD:
4 / 4

N=5K ESCALATION:
NOT JUSTIFIED

N=5K BASELINE ON:
NOT RUN

N=5K B08 ON:
NOT RUN

N=5K ON IMPROVEMENT:
NOT VERIFIED

N=5K REAL FLUTTER COLD:
0 / 2 MAX

TOTAL NEW FULL COLD RUNS:
4 / 6 MAX

ACTUAL E3 PUBLICATION:
PASS

ACTUAL E4 ACCEPTED READ:
PASS

FINANCIAL SEMANTIC EQUIVALENCE:
PASS

WITHIN-ENGINE ON/OFF EQUIVALENCE:
PASS

ENGINE-DEPENDENT OBJECT HASH DIFFERENCES:
EXPLAINED

MEASUREMENT COMPARABILITY:
LIMITED — 동일 fixture·source 격리, 조건당 1회·순서/JIT/host 변동 한계

REAL-PATH PERFORMANCE DECISION:
MIXED

B08 OPTIMIZATION ADOPTION:
EXPERIMENTAL

ORIGINAL B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL SOURCE ONLY

B05 OPTIMIZATION:
EXPERIMENTAL — SYSTEM BENEFIT NOT ESTABLISHED

B07:
PASS — MATERIAL COST ATTRIBUTED

B08:
PASS — SAFE REUSE AND LOCAL BENEFIT VERIFIED

N=50K FULL COLD RUNS:
0

N=100K FULL COLD RUNS:
0

N=100K INSTRUMENTED FEASIBILITY:
NO-GO

PHASE B FIVE-POINT COST GRID:
PARTIAL

E3 I25 LARGE-N:
PARTIAL

T6.6F PHASE B:
INCONCLUSIVE

REAL-DEVICE GATE:
DEFERRED

ANDROID MEMORY/VFS/POWER:
NOT VERIFIED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

PRODUCT SOURCE CHANGES:
B08 ORIGINAL OPTIMIZATION ONLY — NO NEW OPTIMIZATION

B03 INSTRUMENTATION:
UNCHANGED

BINDING PROTOCOL:
UNCHANGED

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B09:
NO

HISTORICAL EVIDENCE:
PRESERVED

COMMIT:
NONE

PUSH:
NOT PERFORMED

B09 REPORT:
docs/t66f-b09-engine-admission-real-flutter-cold-ab.md

B09 EVIDENCE:
docs/benchmarks/t66f-b09/

TEMPORARY ARTIFACT CLEANUP:
B09 scratch 626,454,871B 제거; DB backup 8개·source/fixture·raw 보존

FINAL VERDICT:
PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE

NEXT ACTION:
B08을 실험 후보와 증거로만 보존하고 추가 B08 성능 캠페인을 종료한다.
```
