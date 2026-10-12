# E2-A01 교정 재현 및 response 소유권 oracle

기준 commit은 `814eab506aa8457d10a7302241a26120b9389ff6`이다. 실제 loopback
HTTPS, 새 임시 인증서, disposable E1 SQLite만 사용한다. production 접속·설치·배포는 없다.

## 실행

Repository root에서 기존 Python/Dart dependencies와 Linux `ss`, `openssl`을 사용한다.

```sh
E2_AUDIT_OUTPUT=/tmp/money-note-e2-a01-native .venv/bin/python -m pytest -q docs/benchmarks/t66e2-audit/test_audit.py -k native
E2_A01_OUTPUT=/tmp/money-note-e2-a01-tcp .venv/bin/python -m pytest -q docs/benchmarks/t66e2-a01/test_cleanup.py
```

수정 전 library를 별도 임시 디렉터리에 복원하는 비교 명령이다. working tree를 바꾸지
않으며, **결함 재현을 뜻하는 1 PASS / 4 FAIL이 예상값**이다. baseline의 tracked Dart
library와 현재 설치된 동일 dependencies/native SQLite asset만 사용한다.

```sh
E2_A01_BASELINE_COMMIT=814eab5 E2_A01_OUTPUT=/tmp/money-note-e2-a01-before-tcp .venv/bin/python -m pytest -q docs/benchmarks/t66e2-a01/test_cleanup.py
```

Flutter의 직접 교정 회귀는 다음 명령으로 실행한다.

```sh
cd mobile
flutter test --no-pub test/segmented_response_cleanup_test.dart test/segmented_transport_test.dart
```

## 원본 재현 및 계측 보강

원본 감사 보고서와 `t66e2-audit/summary.json`의 FAIL 이력은 변경하지 않았다. 원래
reproducer는 수정 전 직접 실행하여 1 PASS / 4 FAIL을 재현했다. header 오류 뒤
`maxConnectionsPerHost=1`의 후속 정상 요청은 timeout이었고, 6회 public acquisition에서
서버 active 계수는 `[1,2,3,4,5,6]`이었다.

교정 후에는 후속 정상 요청이 성공하지만, 원본 서버가 일부러 끝내지 않는 response의
`connectionsInfo().active`는 여전히 같은 수치를 낸다. Dart 3.13.3의
`lib/_http/http_impl.dart`에서 `_HttpConnection`은 outgoing response 완료까지 parser를
pause하며, `connectionsInfo()`는 그 application 상태를 센다. 이 수치는 원격 client의
현재 FD 소유권과 같지 않다. 기존 assertion을 그대로 실행한 중간 결과도 1 PASS /
4 FAIL로 기록했다. 예외만 확인하거나 서버 수치를 숨기는 것으로 교정을 판정하지 않았다.

프로젝트 소유자의 명시적 승인에 따라 `native_transport.dart`에 독립 계측을 추가하고
해당 native assertions를 보강했다. 요청·header·body 보류·오류·pool 한도는 유지한다.
원래 server active 수치도 계속 출력한다. `ss`의 destination을 새 synthetic server port로
제한하고 worker PID가 소유한 client TCP FD만 센다. 같은 process의 server 측 socket이나
FD가 없는 TCP 잔여 상태는 client 소유권으로 세지 않는다. 정상 body 이후의 재사용 가능한
idle FD 1개는 허용하지만, 거부 응답 반환 뒤 client FD는 반드시 0이어야 한다.

## 실제 비교

| 원본 시나리오 | 수정 전 client FD | 수정 후 client FD | pool=1 후속 정상 요청 |
|---|---:|---:|---|
| header 직후 credential 변경 | 1 | 0 | TIMEOUT → HTTP_200 |
| 302 redirect | 1 | 0 | TIMEOUT → HTTP_200 |
| 과대한 Content-Length | 1 | 0 | TIMEOUT → HTTP_200 |
| public acquire 6회 | 1,2,3,4,5,6 | 0,0,0,0,0,0 | 별도 위 세 제한-pool 사례로 검증 |

정상 대조군은 전후 모두 HTTP_200 두 번, 실제 connection 1개 재사용, client idle FD 1개다.
각 거부 오류 code는 전후 동일하다. 새 SQLite connection으로 objects/staging/acquisition
각 0개, integrity/FK 정상도 확인했다. 테스트가 끝난 뒤 전용 client/server를 정리한다.

`test_cleanup.py`는 같은 원본 시나리오를 실행하고 별도 SQLite 연결로 persisted state를
확인한다. baseline 선택 옵션은 반례 비교용이며 제품 경로·검증·staging을 대체하지 않는다.
계측 command 실패는 PASS가 아니며 fixture 오류다. `summary.json`은 현재 실행의
요약으로, 과거 감사 verdict를 대체하지 않는다.

## 한계

Linux host의 native IOClient에 대한 시험이다. Android 설치·production throughput·외부
네트워크 측정을 주장하지 않는다. 보류한 원격 server response의 완료를 client가 보장하지
않는다. 기준은 client 소유권 해제와 pool 가용성이다. 임의 주입 client는 기존 abort 및
stream cancellation 계약을 지켜야 한다. 독립 targeted 재감사는 별도로 필요하다.
