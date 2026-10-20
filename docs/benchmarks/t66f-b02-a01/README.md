# T6.6F-B02-A01 조사 재현

기존 dirty B02 제품·테스트·보고서는 변경하지 않는다. 모든 서버는 자가 소유 합성 SQLite와
loopback TLS를 사용한다. Production 접근, commit/push, APK 설치, R1 및 활성화는 없다.

## 보호 기준

`inventory.py`는 최초 HEAD/main/origin/main/actual remote와 staged diff, index의 논리 entries,
기존 tracked/untracked 파일 SHA를 기록했다. 다시 실행하여 최초 기준을 덮어쓰지 않는다.
`source_evidence.py`는 현재 제품과 최초 SHA를 비교하고 원 SHA guard를 읽기만 한다.

## 실제 50k 실행

저장소 root에서 `.venv/bin/python docs/benchmarks/t66f-b02-a01/run.py`를 실행한다.
`run.py`는 새로운 `/tmp/mn-b02-a01-<시각>` 경로를 만든다. 같은 원 fixture seed와 50k행,
V200331/E200327을 실제 backend walker로 확인한다. 실제 E2/E1 및 AppState isolated E3
entry를 호출하고, 성공했을 때만 원 E4 bounded page read에 도달한다. Backend BLOB를
Flutter store로 복사하거나 accepted pointer를 조립하지 않는다.

`server.py`는 기존 B02 합성 서버에 위임한다. 계측 wrapper는 원 함수에 항상 위임하며
권한·lease·transaction·worker budget을 변경하지 않는다. ContextVar로 요청별 inclusive
wall/thread CPU 시간과 명시 SQL 호출을 수집한다. 중첩 함수 시간은 합산하지 않는다.
Wire에는 credential/body 전체를 남기지 않고 status, entity bytes, typed hash 재전송 여부,
manifest identity와 실패 body를 기록한다. 합성 credential은 원 private pipe 안에서만 이동한다.

`cold_test.dart`의 IOClient는 원 IOStreamedResponse를 그대로 반환한다. Native response
stream/cleanup/detachSocket을 교체하지 않는다. E1 기존 fault hook은 insert/commit 경계만
관측한다. 30초 read-only SQLite snapshot은 actual usage/상태를 본다. 계측 오버헤드는 latency에
포함되며 exact CPU profile·physical I/O 또는 전층 logical byte 계수로 과장하지 않는다.

TTL900초, observations3, request attempts3, timeout15초, batch64/decoded1MiB와 원 guard는
불변이다. 외부80분 guard가 동작하면 normal expiry와 구분한다. 이번 조사에서는 두 번째 확인
실행만 최종3-attempt 자료로 사용한다. N100k는 실행하지 않는다.

처음 실행의 `IOSink.flush()` 비대기 상태는 동시 로그 쓰기를 거부할 수 있었다. 원 하네스는
`cold-first.dart.txt`로 보존했다. `sink_probe.dart` 및 `sink_transport_probe.dart`가 각각
StateError와 동일 TRANSPORT_FAILED mapping을 재현한다. 첫 lease의 실제410과 작업량은
관측 사실이나, 이후 terminal TRANSPORT_FAILED를 제품 결함 또는3회 만료라고 부르지 않는다.
최종 하네스는 조사 trace만 동기 append로 바꿨다. 제품 파일은 그대로다.

## 관측 및 후속 검사

- `monitor.py`: 조사 child process의 `/proc` CPU/RSS/I/O/FD를30초 간격으로 읽는다.
- `analyze.py <out>`: 원 request/commit trace의 경계별 요약을 생성한다.
- `reconcile.py <out>`: 관측별 새 durable 객체, 재전송, packet 분포와 서로 중첩되지 않는
  lookup/connect/resolve 비용을 정리한다.
- `postcheck.py`: 실제 cold가 종료된 뒤에만 fresh process reopen, 기존 targeted Flutter와
  backend, npm build/Ruff/compileall/diff check를 순차 실행한다. Full Flutter/backend는 아니다.
- `forensics.py`: 보존된 이전 machine logs에서 정확한4개 실패를 추출한다. 역사 파일은 불변이다.

## 작은 component와 오류 진단

`sample.py`는 최초50k 실행의 자기 소유 backend DB에서141개 작은 객체만 read-only로 읽었다.
독립 hashlib/JSON 검증을 거친 부표본이며 backend→E1 preload 또는 complete D→E의 대체가 아니다.
`backend_component.py <first-out>`는 원 PathResolver를 read-only memory DB의64개 경로로
재생하며 검증을 생략/캐시하지 않는다. 별도 count-only hook의 hash/C1 입력 bytes는 이 작은
component만의 경계다. 전층 logical bytes로 사용하지 않는다.

`e1_component.dart <first-out>`는 같은 부표본의 실제 hash/검증 및64개 이하의 기존 batch API를
별도의 새 disposable store에서 부른다. Full graph/accepted publication을 시도하지 않는다.
`reuse_diagnostic_test.dart`는 최초 cache 사본에 실제 E2/IOClient를 사용하지만 manifest와422는
명시 mock이다. Fresh-process cached-prefix reuse와 진단용이며 실제 backend 전체 재개 PASS가 아니다.
초기 mock Map 타입 오류 로그도 보존하며 제품 결함으로 분류하지 않는다.

예시 명령은 root의 `.venv/bin/python`과 `mobile/` cwd의 Flutter를 구분한다.

```bash
.venv/bin/python docs/benchmarks/t66f-b02-a01/analyze.py /tmp/<조사-output>
.venv/bin/python docs/benchmarks/t66f-b02-a01/reconcile.py /tmp/<조사-output>
/home/hjkerman/.flutter/bin/dart --packages=mobile/.dart_tool/package_config.json \
  docs/benchmarks/t66f-b02-a01/e1_component.dart /tmp/<최초-output>
```

증거 수집 때 `.pem`, SQLite DB, credential은 저장소 자료에 포함하지 않는다. 원시 로그는
압축하여 보존하고 terminal 실패·실제 exit code를 별도로 남긴다. 기존 원본·Git index는
수정하지 않으며 최종 working tree는 기존 B02와 새 조사 자료 때문에 dirty인 상태가 정상이다.
