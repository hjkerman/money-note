# IC01 계측 교정 증거

원 독립 finding과 [교정 보고서](../../t66f-b03-ic01-targeted-correction.md)를 함께 읽는다.
이 경로의 구현 측 결과는 독립 B03 재감사나 Phase B PASS가 아니다.

## 재현과 역사 보존

시작 commit은 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`다. 원 감사 테스트 두 파일,
findings와 과거 raw evidence를 수정하지 않는다. `baseline-*`는 수정 전 원 assertion 실행이다.
원 direct-experiments.md의 세 Python code block도 원문 그대로 별도 child에서 실행했다.
`reproductions.json`은 동일 실제 SQL·parser·closed lease 실험의 역사/현재 수치다.

사용자가 승인한 역사/현재 분리에 따라 backend defect-existence4개와 Dart3개는 exact 동결
wrapper로만 실행한다. `historical/manifest.json`의 SHA를 감사 commit에서 대조할 수 있다.
현재 계약 oracle와 새 교정 regression은 현재 wrapper로 실행한다. assertion 수정·SKIP/XFAIL은 없다.
`archive.py`는 원 assertion을 그대로 두고 역사 Dart 사본의 import/output 위치와
길어진 golden 경로의 setup 식 줄바꿈만 바꾼다. 원 package의 Dart3.3 formatter로 검사한다.
`prepare_probes.py`는 원 독립 TLS/overhead probe의 evidence 출력 위치만 바꾼다.

## 명령

저장소 root에서 `.venv/bin/python`을 사용한다. 기존 실행 파일이 있으면 bounded runner는 덮어쓰기를 거부한다.

```sh
.venv/bin/python docs/benchmarks/t66f-b03-ic01/archive.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01/prepare_probes.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01/run.py baseline-backend
.venv/bin/python docs/benchmarks/t66f-b03-ic01/run.py baseline-flutter
.venv/bin/python docs/benchmarks/t66f-b03-ic01/run.py baseline-direct
.venv/bin/python docs/benchmarks/t66f-b03-ic01/collect_reproductions.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01/server_probe.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01/run.py backend-sealed
.venv/bin/python docs/benchmarks/t66f-b03-ic01/run.py flutter-sealed
```

`original_backend.py --current --full --sealed`는 모든 backend test를 실행하며 역사4개에만 동결 helper를 적용한다.
`flutter_full.py --sealed`는 기본 tree의 모든 case를 세 명령으로 집계한다. 원 독립 파일을 제외한
전체 tree, 원 독립 현재 oracle11개, 동결 wrapper를 import한 원 역사 assertion3개다.
단순 원 default 명령은 의도적으로 defect-existence assertion이 교정 수치를 거부하므로 이 분리가 필요하다.
전체 결과에는 세 명령의 exit와 machine done을 모두 확인한다. 역사 PASS와 현재 정확성 PASS는 따로 표기한다.

최초 sealed runner의 part1은 SDK가 지원하지 않는 `--exclude-name` 때문에 exit64였다.
일반 tree1,666 PASS/2 SKIP와 역사3개는 이미 최종 source에서 통과했다. 원 FAIL을 보존하고
동일 source의 `run.py flutter-current-11`을 지원되는 negative-lookahead `--name`으로 실행했다.
전체 최종 집계는 **1,680 PASS/0 FAIL/2 SKIP**이며 원 runner exit를 소급 변경하지 않는다.
현재 `flutter_full.py`의 재현 명령에는 교정된 필터를 반영했다.

`after_flutter.py`는 공유 native-assets 충돌을 피하려고 전체 종료 후 TLS/authority/overhead/high-N/analyze/build를 순차 실행한다.
`backend-full`/`flutter-full` 및 `*-final`은 추가 경계 보정 전에 소유 process만 종료한 중간 실행이다.
이를 제품 failure나 관측 expiry, 최종 회귀 PASS로 전용하지 않는다. 원 로그와 intentional-stop 원인을 보존한다.
`sealed-source.json`은 최종 source5개의 exact SHA다. `freeze.py`를 다시 실행하면 불일치 때 실패한다.

## SQL 계측 범위

기존 실제 sync SQL의 INSERT/UPDATE/DELETE/REPLACE, 제어 statement와 고정 schema를 관측한다.
전 SQL 언어용 profiler가 아니다. 명시 OR FAIL과 native CHECK/NOTNULL/PRIMARYKEY/UNIQUE의
보존 semantics를 지원하며 FK/trigger ABORT는 별개다. schema FAIL/RAISE(FAIL), Dart의 다중
DML 입력은 실행 전 진단 오류다. 원 schema의 초기 DDL 묶음과 준비된 statement API는 유지한다.
read-only CTE에는 TEMP write observer를 설치하지 않는다. raw cursor/executescript/lazy/native-handle
우회 API나 arbitrary schema를 전체 계측했다고 주장하지 않는다. source의 actual D→E 경계와 별도로 취급한다.
savepoint32/table128/transaction owner32를 넘으면 명시 오류이며 자료를 조용히 버리지 않는다.
닫힌 collector의 snapshot은 불변이다. 정상 measurement는 transaction/native 작업을 마친 뒤 닫아야 한다.

## 비용과 한계

hash/validation/write는 별개의 연산 비용이다. committed row payload는 unique final bytes나 물리 I/O가 아니다.
oracle/fixture work는 setup으로 분리하고 제품 generation 합계에서 제외한다. per-object 무제한 trace는 추가하지 않는다.
원 overhead.py의3 warmup+20 alternating pair와 동일 probe를 현재 source에서 재실행한다.
동시 전체 회귀에 따른 HOST 부하도 함께 기록하며 작은 wall 비율을 device 보증으로 확대하지 않는다.

`high_n_sample_test.dart`는 보존된 합성 100k DB를 read-only로 읽어 종류별 유한 표본을 만든다.
새 폐기용 E1 store의 실제64-object/1MiB staging을 enabled/disabled 각각 수행하고 정확한 payload 합을 확인한다.
원 저장소/accepted/pending을 수정하지 않고 미완료 sample을 게시하지 않는다. 이는 HTTP/lease/E3/E4
전체100k cold가 아니다. 표본 projection이 있어도 실제 instrumented100k 완료 증거와 구별한다.
full fixed-H/D five-point grid·I25 proof·Android/VFS/power/R1은 별도 의무다.

최종 표본은 `run.py high-n-sample-final`의 exit0과 `high-n-sample-result.json`을 사용한다.
첫 `high-n-sample`의 acquisition-only/publication API 오용 실패는 보존했다.
`overhead.py --sealed`는 원 paired Python probe를 최종 source에 실행하고 별도 sealed-overhead에 기록한다.
`performance.py`는 최종 원 paired 통계와 실제 E1 표본을 기계 집계하며, 100k 환산값에는
**ANALYTICAL ESTIMATE**라고 명시한다. 약497초의 기계적 추가 비용 환산은 실제 완료/실패 proof가 아니다.
100k 활성 계측의 관측별 완료 가능성이 미확정이므로 IC01 최종 판정은 **INCOMPLETE**다.
완료 commit/push는 하지 않았고, 일곱 구현 측 교정 결과를 독립 finding closure로 선언하지 않는다.
