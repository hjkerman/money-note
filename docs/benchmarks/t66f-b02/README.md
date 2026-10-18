# T6.6F-B02 조사 재현

실행 위치는 저장소 root다. 모든 DB는 `/tmp/mn-b02` 및 `RetentionSandbox`의 새 disposable
경로다. 운영 DB·API·credential은 사용하지 않는다. 제품 source와 protocol은 수정하지 않는다.

```bash
.venv/bin/python docs/benchmarks/t66f-b02/generate.py 1000 /tmp/mn-b02/1000
.venv/bin/python docs/benchmarks/t66f-b02/run_generations.py /tmp/mn-b02
.venv/bin/python docs/benchmarks/t66f-b02/run_probes.py
.venv/bin/python docs/benchmarks/t66f-b02/run_simulations.py
```

`generate.py`는 기존 fixed-H 금융 fixture seed 662602를 사용한다. namespace·observation
UUID는 각 실행의 새로운 synthetic identity다. 따라서 같은 금융 rows/count/byte-size를
재현하지만 namespace hash가 서로 다른 실행의 digest까지 동일하다고 주장하지 않는다.
각 실행의 manifest와 입력 DB SHA를 증거에 결합한다. producer는 실제 backend bootstrap,
bounded writer/finalizer, observation repository다. HTTP 측정기는 아니다.

`objects.sqlite`는 backend의 object catalog를 복제한 **offline 분석 입력**이다. E1 client
DB가 아니며 accepted/pin/receipt를 직접 삽입하지 않는다. 독립 walker는 reachable closure와
catalog 전체(bootstrap 중간 객체 포함)를 구별한다. source oracle의 child extractor는 기존
독립 `scripts/benchmarks/t66e2_server.py`를 공유한다. SHA는 Python 표준 구현으로 별도 계산한다.

`probe.dart graph`는 실제 `verifyAcquisitionGraph`/`VerifiedObject.verify`를 기본
100000/200000 예산으로 호출한다. HTTP·staging·E3 publication 성공을 의미하지 않는다.
`boundary`는 작은 실제 graph의 V−1/V/V+1에서 cold와 provenance 재사용을 모두 검사한다.
제품 `FetchLimits` 또는 `ClientStoreLimits.objectCount`를 올리지 않는다.

```bash
/home/hjkerman/.flutter/bin/dart --packages=mobile/.dart_tool/package_config.json \
  docs/benchmarks/t66f-b02/probe.dart boundary /tmp/mn-b02/1000 /tmp/mn-b02/boundary.json
/home/hjkerman/.flutter/bin/dart --packages=mobile/.dart_tool/package_config.json \
  docs/benchmarks/t66f-b02/probe.dart store /tmp/mn-b02/15000 \
  /tmp/mn-b02/actual-client-store /tmp/mn-b02/store.json
/usr/bin/time -v -o /tmp/mn-b02/sample-time.txt \
  /home/hjkerman/.flutter/bin/dart --packages=mobile/.dart_tool/package_config.json \
  docs/benchmarks/t66f-b02/probe.dart sample /tmp/mn-b02/1000 \
  /tmp/mn-b02/sample-store /tmp/mn-b02/sample.json
```

새 store directory만 사용한다. `store`는 기본 E1 guard를 실제 통과하는 각 put/progress
transaction을 실행하다 budget 초과로 멈춘다. prefix만 저장된 상태를 complete라고 하지 않는다.
`sample`은 1000개만 저장하고 같은 staging 및 새 staging의 cached progress를 분리한다.

`facts`는 실제 공개 F(raw)/Patricia component의 offline 실행이다. `simulation`은 독립적인
요약 목록을 보유한 채 그 component를 실행하는 메모리 모델이다. 제품 GraphClosure 또는
CompleteGenerationProof를 만들지 않는다. 모델의 600000개/8GiB 한도는 조사 프로세스의 별도
안전장치이며 제품 cap을 변경한 것이 아니다. 모델 자료구조/GC가 실제 E3와 달라 그 RSS를
제품 전체 peak나 Android heap 한도로 해석하지 않는다.

`layout.py`는 core table/index DDL을 공유하는 bulk SQLite **footprint 모델**이다. 제품의
guard/trigger/accepted semantics를 흉내 내어 E1 성공을 주장하지 않는다. 한 bulk transaction의
시간을 객체별 실제 durable commit 시간과 비교하여 속도 개선이 구현됐다고 주장하지 않는다.

각 process 결과, 실제 exit, `/usr/bin/time -v`, fixture/manifest SHA와 JSON을 보존한다.
실험은 warmup 없는 단회 기술 표본이다. median/p95 또는 Android/production 성능이 아니다.
JIT RSS에는 compiler·VM·native SQLite가 포함된다. AOT 초기 실행은 native asset 미포함으로
실패했으며 별도 초기 harness 오류로 보존했다. 후속 측정은 기존 지원 JIT 경로다.

큰 SQLite payload 자체는 Git에 넣지 않는다. 재현 script, 각 실행 manifest, 결과와 입력 SHA를
보존한다. 실제 HTTP 큰 grid 및 논리 hash/validate/write byte campaign은 후속 F의 책임이다.

`executed-sources/`는 format 직전 snapshot이다. 모든 장기 process의 시작 시점 source SHA를
소급 증명하는 자료는 아니다. 조사 중 sample/simulation mode와 출력 field를 추가했으나 기존
store의 put/progress loop와 제품 예산은 바꾸지 않았다. 초기 harness 오류와 재실행은 원시 로그로
구분한다. 현재 script로 같은 정책/fixture의 측정을 재현할 수 있으나 추가 output field가 있을 수 있다.

원 monetary/cap 회귀의 실제 실행 명령은 다음과 같다. `mobile/`에서 실행했다.

```bash
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --dart-define=C_BUDGET_WITNESS=/home/hjkerman/codex/money-note/docs/benchmarks/t66f-phase-b-continuation/evidence/budget-50000.json --dart-define=C_MONEY_GOLDEN=/home/hjkerman/codex/money-note/docs/benchmarks/t66f-phase-b-continuation/evidence/money-golden.json /home/hjkerman/codex/money-note/docs/benchmarks/t66f-phase-b-continuation/profile_test.dart
```
