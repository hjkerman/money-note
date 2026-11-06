# B03-IC01-P02 재현

제품 sync 알고리즘을 바꾸지 않는 진단 wrapper 교정이다. 모든 source/로그는 synthetic HOST 증거다.
원 IA01–IA07 역사 실패와 P01 shutdown FAIL은 기존 디렉터리에 그대로 남긴다.

## 실행

저장소 root에서 실행한다. Flutter test를 병렬로 두 번 시작하지 않는다.

```sh
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py new-tests-sealed
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py backend-targeted
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py flutter-targeted
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py current-independent
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py small-http-final
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py components-final
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py preparation-final
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py cleanup-open-final
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py cleanup-closed-final
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py independent-overhead
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py authority
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py backend-full
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/run.py flutter-full
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/static_checks.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/model.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p02/inventory.py --check
```

원 helper exact 사본 SHA는 `cafc733c252c42e1dc7ad518ccfc013878fe2683474a53e9be5de3be82e3c49b`다.
`original_sqlite.dart`는 P02 시작 IC01의 교정된 구현이다. 감사 commit의 **결함 있는** 동결 구현과
혼동하지 않는다. 후자는 기존 `t66f-b03-ic01/historical/`에서 역사 assertion에만 사용한다.
현재 회귀는 새 wrapper의 정확한 값을 검증한다. 원 independent tests를 skip/xfail하지 않는다.

성능 표본은 `/tmp/mn-b02-independent-100000-z6ux9y53`의 독립 B02 실제100k client store를
read-only로 사용한다. 원 cold graph400532개가 아니라, 후속 delta를 포함해400630개가 보존된
store에서 kind/hash 순으로 고른 동일4105개다. 표본은 complete graph가 아니고 accepted로 게시하지 않는다.
다른 재현 host에서는 해당 B02 synthetic fixture를 재생성한 후 `--dart-define=P02_SOURCE=<root>`를
직접 두 Dart test에 전달할 수 있다. 달라진 random namespace/delta 상태의 hash 순서가 표본 identity를
바꾸면 bytes 수치가 달라질 수 있으므로 원 보고서 시간과 같은 입력이라고 주장하지 않는다.
운영 DB나 credentials를 가져오면 안 된다.

## 해석

`*-data.json`은 측정 원자료, 같은 mode의 `.json`은 command/exit/resource runner 결과다.
둘을 덮어쓰지 않는다. 최초 preliminary 파일도 보존한다. `components-final-data.json`은
원 exact helper/비계측/재사용 3모드, warmup1+5회 표본과 SQL/primitive/work 완전 일치를 기록한다.
idle binding은 해제하며 cache의 최종 created/finalized 일치도 기록한다. profiler를 끈 native/callback
timer의0은 NOT INSTRUMENTED이지 비용0이 아니다.

cleanup-open은 원 server exit1을 재현하는 **역사 lifecycle 진단**이다. 이것의 PASS는 정상 종료
PASS가 아니다. cleanup-closed는 owned TLS client를 먼저 닫은 뒤 같은 원 join fence의 exit0을 요구한다.
두 시험은 N=1k/60 object packets/1 observation의 bounded lifecycle이며 새100k acquisition이 아니다.

`lease-model.json`은 각 역사 관측의 rate에 실제 표본 extra를 적용한 추정이다. 서로 다른 두 역사 실행,
E1/HTTP/backend wall의 중복, renewal/DB 성장 불확실성을 구분한다. full100k 시도 횟수는0이다.
전체 Phase B cost grid/I25/Android/power/R1/independent B03 PASS를 뜻하지 않는다.

재실행은 기존 증거를 보존한 별도 output 디렉터리 또는 새 mode로 수행한다. 완료 조건이 충족되지
않았으므로 현재 index는 보존하고 completion commit/push를 하지 않는다.
