# E2-A01 독립 targeted 재감사

감사 대상은 `7a09384058bb7b8d8984ac5894167d0645925e64`다. 원래 감사와 구현 교정의
자료를 덮어쓰지 않는다. 제품 구현을 수정하지 않으며 새 loopback HTTPS 서버,
시험용 인증서와 disposable SQLite만 사용한다.

## 새 독립 TCP oracle

Repository root에서 실행한다. 설치된 Python/Dart/http dependencies만 사용한다.

```sh
E2_REAUDIT_OUTPUT=/tmp/mn-e2-a01-reaudit/new .venv/bin/python -m pytest -q docs/benchmarks/t66e2-a01-reaudit/test_reaudit.py --junitxml=/tmp/mn-e2-a01-reaudit/new.xml
```

`probe.dart`는 제품 `AuthenticatedSegmentedTransport`와 실제 `IOClient`를 사용한다.
테스트 wrapper는 모드를 나타내는 header를 추가하고 auth 사례에서 수신 직후
시험용 credential getter를 바꿀 뿐, 응답을 다른 stream으로 포장하지 않는다.
자동 인증서 우회는 이 전용 loopback 시험 client에만 적용한다.

Python HTTPS 서버는 Dart worker와 다른 process에 있다. 각 API 완료 후 worker를
stdin command 경계에서 멈춘 채 `/proc/<pid>/fd`의 실제 `socket:[inode]`와
`/proc/<pid>/net/{tcp,tcp6}`의 destination port를 교차 확인한다. `net/tcp`에만 남은
TIME_WAIT, 서버 소유 FD, 다른 endpoint의 socket은 client 자원으로 세지 않는다.
`ss`나 제품 내부 active counter를 기대값으로 재사용하지 않는 별도 oracle다.
검사 전에 client를 닫거나 교체하지 않는다. 정상 요청 뒤 idle pooled FD 1개는 허용한다.

9개 pytest case는 다음을 검증한다.

| 사례 | 기대 |
|---|---|
| auth 변경 6회 | 오류 보존, 매번 client FD 0, 같은 pool=1에서 golden object 성공 |
| 307 redirect 6회 | 같은 기대 |
| 한도보다 1B 큰 declared length 6회 | 같은 기대 |
| 1TiB declared length 6회 | body 1KiB만 보내도 빠른 거부, 같은 기대 |
| Content-Length 없는 chunked redirect 6회 | body 미완료에서도 같은 기대 |
| 0B redirect 6회 | 이미 끝난 body에서도 같은 기대 |
| 다른 정상 응답과 동시 redirect | 거부 socket만 닫히고 다른 응답은 완전히 검증됨 |
| 손상 C1 | `REPRESENTATION_INVALID`, 같은 client의 다음 정상 객체 성공 |
| canonical C1지만 다른 hash | `OBJECT_HASH_INVALID`, 같은 client의 다음 정상 객체 성공 |

서버 body는 `Event`로 보류한다. Header/API 완료 및 정상 응답 barrier를 사용하며
임의 sleep 뒤 FD가 없어졌다고 판정하지 않는다. 1초 request timeout, 3초 거부
assertion, 8초 worker 응답 상한과 fixture cleanup 상한은 시험의 자원 제한이다.

Golden은 기존 실제 합성 서버 산출물 `mobile/test/fixtures/segmented_server_golden.json`의
`raw-root`다. Python JSON canonical bytes 및 `hashlib.sha256(domain + NUL + bytes)`로
독립 확인하고, HTTPS로 받은 Dart bytes/hash/VerifiedObject 결과와 대조한다.
이 시험은 새 인증된 graph 전체를 수집했다는 주장이 아니다.

## 원래 반례와 oracle 보강 분리

```sh
.venv/bin/python docs/benchmarks/t66e2-a01-reaudit/replay.py /tmp/mn-e2-a01-replay
```

다음 네 실행을 구분한다. 모두 새 합성 fixture를 만든다.

1. 원래 server-active assertion을 그대로 둔 교정 코드: **1 PASS / 4 FAIL 예상**.
   임시 원본 test module에서 ROOT/HERE 경로만 바꾸며 두 native test 함수의 AST가
   동일한지 검사한다. 이 결과를 제품이 계속 누수한다는 근거로 쓰지 않는다.
2. 승인된 client-FD oracle를 적용한 원래 5시나리오: **5 PASS 예상**.
3. 교정의 TCP/별도 SQLite 검사: **5 PASS 예상**.
4. 원래 library를 임시 복원한 동일 FD oracle: **1 PASS / 4 FAIL 예상**.

원래 서버의 미완료 response 상태는 client socket 종료 뒤에도 `_ACTIVE`로 남는다.
원래 FAIL 이력과 현재 server-active 수치를 보존하면서 실제 FD와 pool 가용성을
판정한다. 대조군에서 누수/timeout을 탐지하고 교정에서 해소됨을 확인한다.

## 회귀 명령

```sh
cd mobile
flutter test --no-pub --machine test/segmented_response_cleanup_test.dart test/segmented_transport_test.dart test/segmented_http_integration_test.dart
flutter test --no-pub --machine
flutter analyze --no-pub
flutter build apk --debug --no-pub --dart-define=MONEY_NOTE_API_BASE_URL=https://independent.synthetic
```

```sh
cd backend
../.venv/bin/python -m pytest -q --junitxml=/tmp/mn-e2-a01-reaudit/backend.xml
```

Root의 Ruff/compileall, `scripts/tests scripts/benchmarks`, frontend test/build,
변경 Dart formatting과 `git diff --check`도 검사한다. 성공 로그 전체는 출력하지 않는다.
실행 로그/JUnit/시험 DB는 `/tmp`에 두고 요약은 `summary.json`에 보존한다.

## 범위와 한계

Linux host의 실제 local TLS/FD 검사다. Android 설치, production API, 외부 network,
실기기 성능, OS/power-loss durability를 주장하지 않는다. 2초 fallback cleanup과
late socket 처리는 기존 교정 unit tests의 controlled injection으로 확인하며,
실제 native stalled-body 검증과 구분한다. 임의 custom client의 계약 위반까지
transport가 강제로 종료한다고 주장하지 않는다. E3 구현/배포/활성화는 하지 않는다.
