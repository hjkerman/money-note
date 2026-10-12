# T6.6E1 독립 감사 증거

감사 대상은 `141e01186d589a9071ae6a3d0c0023a6472c014d`다. 이 디렉터리의
코드는 production 구현을 바꾸지 않으며, 새 임시 디렉터리와 synthetic SQLite만 쓴다.

## 실행

개발 checkout의 dependency가 준비된 환경에서 실행한다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66e1-audit/test_audit.py
.venv/bin/python docs/benchmarks/t66e1-audit/reproduce_findings.py
```

첫 명령은 현재 구현에서 **6개 normative assertion이 실패**한다. 5개는 금액 문자열의
whitespace 계약 불일치이고 1개는 필수 schema trigger 누락 뒤 quota 초과 COMMIT이다.
실패를 `xfail`로 숨기지 않았다. 구현 수정 뒤에는 모두 통과해야 한다.
둘째 명령은 반례의 관측값을 `findings.json`에 기록한다. 성공 exit code는 구현 PASS가
아니라 반례 증거 수집의 완료를 뜻한다. 관측값은 보고서의 기대값과 비교해야 한다.

`DART` 환경변수로 Dart executable을 지정할 수 있다. 기본값은 이 개발 서버의
`/home/hjkerman/.flutter/bin/dart`다. 감사 실행기는 mobile의 명시적
`.dart_tool/package_config.json`을 사용하므로 앱 startup에 등록되지 않는다.

## Oracle과 파일

| 파일 | 의미 |
|---|---|
| `make_fixture.py` | 실제 D2b/D3a synthetic generation에서 서버 객체를 읽고 별도 JSON/hashlib로 C1/hash를 대조 |
| `server-fixture.json` | 고정된 서버 객체 29개·9종, 금액 문자열 11종, Unicode leaf 6개, C1 vector 128개 |
| `worker.dart` | 검증 대상 API를 별도 Dart process에서 호출하는 감사 전용 실행기 |
| `test_audit.py` | fresh process, Python SQLite/hashlib, SIGKILL barrier, 다중 process 검사 |
| `reproduce_findings.py` | 실제 인증 ASGI 관측 201/object 전달 200과 직접 SQLite COMMIT 반례 |
| `findings.json` | 두 finding의 원문 bytes/hash, 서버/Dart 결과, 직접 읽은 usage/object 상태 |
| `results.json` | 실제 회귀 수, 독립 사례별 결과, 환경 및 작은 benchmark |

서버 fixture를 새로 만들 때만 다음 명령을 실행한다. UUID가 새로 생성되므로 원문과
해시는 달라진다. 검증 관계와 고정 seed `6601`의 C1 corpus는 동일한 방법으로 계산된다.
기존 구현자의 fixture 생성기를 import하지 않는다. 선행 독립 D3c 감사의 synthetic
11-table seed만 재사용한다.

```sh
.venv/bin/python docs/benchmarks/t66e1-audit/make_fixture.py
```

## 실제 process 종료

`worker.dart`는 대상 transaction의 synchronous checkpoint에서 stdout으로 준비를
알리고 stdin에서 대기한다. 부모는 그 알림을 확인한 뒤 SIGKILL한다. 임의 sleep으로
COMMIT 시점을 추측하지 않는다. 종료 뒤 다른 Python SQLite connection과 새 Dart
process가 payload, hash, FK, usage, staging 및 write lock을 확인한다.

기존 7개 경계에 더해 progress INSERT/COMMIT, staging cleanup COMMIT 전후를
독립적으로 검증한다. OS crash와 hardware power loss의 증거는 아니다.

## 범위

모든 bearer 값·계정·금융 행은 synthetic이다. ASGI 호출은 TestClient 안에서만
실행하며 외부 API에 연결하지 않는다. APK는 compile만 했으며 설치하지 않았다.
E2/E3 구현, production 접근, 배포, segmented sync 활성화는 수행하지 않았다.
