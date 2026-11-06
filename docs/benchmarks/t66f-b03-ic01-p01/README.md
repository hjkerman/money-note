# P01 한정 lease feasibility 증거

판정은 **PREFLIGHT NO-GO**다. full100k instrumented cold 실행은0회다.
[보고서](../../t66f-b03-ic01-p01-100k-lease-feasibility.md)와 `evidence/summary.json`을 함께 읽는다.

## 원문 보존과 범위

시작2852개 파일/index exact inventory는 `inventory.py`가 생성했다. `--check`는 보존만 검증한다.
기존 IC01 report/source/evidence·역사 audit·product source를 변경하지 않았다.
현재 source SHA와 전체 시작 diff·staged/unstaged/untracked 목록을 새 evidence에 기록했다.
원 B03 defect-existence7개는 이미 승인된 frozen helper에서만 실행한다.

## 재현 순서

repo root의 `.venv/bin/python`을 사용한다. 기존 runner evidence 이름을 덮어쓸 수 없다.
새 disposable checkout/output를 사용하거나 새 run ID를 정해야 한다. 기존 IC01 출력을 덮어쓰지 않는다.

```sh
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/inventory.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/prepare.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/baseline.py
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/run.py backend-targeted
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/run.py flutter-targeted
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/run.py current-independent
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/run.py small-http
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/run.py components-final
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p01/run.py components-no-profile
```

Flutter 프로세스는 순차 실행한다. components는 4105개 실제 보존 synthetic100k 객체를 읽는다.
원 `/tmp/mn-b02-independent-100000-z6ux9y53`가 없으면 중단하고 다른 fixture를 몰래 대체하지 않는다.
`components.json`은 timing-profiler 활성 표본, `components-no-profiling.json`은 실제 기존 wrapper 경로다.
후자의 native/count timing0은 비계측 경계이지 실제 작업0이 아니다.

`run.py packets`는 full cold가 아니라 원 B02 100k fixture의 유한 TLS 구간이다.
초기 bootstrap도 약8분이 필요했다. 현재 NO-GO 상태에서 자동 반복할 명령이 아니다.
실제 실행한 revision은 `packet-before-cleanup-fix.dart.txt.gz` 및 SHA receipt에 보존했다.
모든 packet/byte/cohort assertion 후 종료 fence에서 FAIL했다. 미래 adapter의 client-close 순서와
별도 output filename 보정은 작은 cleanup case로만 확인했으며 큰 실패를 PASS로 바꾸지 않았다.

`run.py cost-parts-final`, `preparation`, `cleanup`, `boundaries`, `historical-3`도 한정 calibration이다.
prepared 비교는 원 `CostDatabase.prepare`와 `execute`를 사용할 뿐 IC01 wrapper에 cache를 구현하지 않는다.
전체 field/counter 의미·SQL 결과를 엄격히 대조한다.

`model.py`는 관측별 독립900초 모델을 계산하며 실제 성공/expiry 결과가 아니다.
`collect.py`는 원 exit/FAIL과 현재 source 보존을 함께 기록한다. full suites는 P01 중 재실행하지 않았다.
모든 대상은 synthetic disposable/loopback이며 R1·배포·APK 설치·production 활성화는 없다.
