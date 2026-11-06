# P05 합성 backend artifact 인계

제품 설정·API·일반 backup 기능이 아니다. 기존 기본 서버는 보존 옵션을 사용하지 않는다.
다음 명령은 작은 새 합성 backend를 만들며 stdout에는 private credential pipe가 있으므로
그 내용을 로그로 저장하지 않는다. `wire`와 `backend` 경로는 모두 새 경로여야 한다.

```sh
.venv/bin/python docs/benchmarks/t66f-b03-ic01-p05/server.py 1000 <wire> <backend>
```

HTTP client를 닫고 private stdin에 `{"command":"exit"}`를 보내면 서버 thread를 join한 뒤
SQLite backup API로 검증한 사본과 manifest를 게시하고 원 임시 환경을 정리한다.
예외 종료에도 같은 경계를 사용한다. SIGKILL·재부팅 전에 backup 실행을 보장하지 않는다.
보존 디렉터리는 재부팅 후에도 남을 저장소 증거 경로를 지정한다. `/tmp`는 장기 보존소가 아니다.

`manifest.json`이 완료 표식이다. `failure.json`이나 partial SQLite만 있는 디렉터리는
완료 artifact가 아니다. 기존 디렉터리는 덮어쓰지 않는다. `verify_artifact()`는 digest,
SQL integrity/FK, 현재 generation, canonical graph와 Target root를 다시 검사한다.
검증은 수신한 immutable 객체의 byte 길이·literal domain framing으로 수행하며
제품 계수를 예상 oracle로 사용하지 않는다. 서버의 재해 복구·physical power-loss proof는 아니다.

보존본은 자체 완결 DELETE-journal 파일이다. 새 **자가 소유** `RetentionSandbox`의 새 inode로
SQLite backup API를 사용해 복원하고 기존 WAL profile을 설정한다. 기존 schema admission과
§5의 `bootstrap()`을 통과시킨 후 새 인증된 observation을 만들어 실제 D3를 사용한다.
서버·dataset은 보존되지만 epoch와 Target root는 바뀐다. 사본의 old observation을
살아 있는 권한으로 광고하거나 원 P03 client에 결합하지 않는다.

반복 시험은 새 case 경로를 사용한다. 이전 결과를 덮어쓰지 않는다.

```sh
mkdir -p docs/benchmarks/t66f-b03-ic01-p05/evidence/<새case>/artifacts
P05_CASE_ROOT=<새case> PYTHONPATH=backend:docs/benchmarks/t66f-b03-ic01-p05 \
  .venv/bin/python -m pytest -q --tb=short docs/benchmarks/t66f-b03-ic01-p05/test_handoff.py
```

현재 최종 원시 결과는 `evidence/new-tests-final-format.xml`, 보존 artifact는
`evidence/run-final-format/artifacts/`에 있다. `manifest-tamper`는 의도된 거부 fixture다.
정상 canonical 인계 fixture는 `tls-normal/`이며 original P03 artifact가 아니다.
DB에는 폐기용 synthetic session 해시만 있고 토큰 원문은 manifest에 없다.
이 사본은 일반 Snapshot v7 export가 아니며 실제 사용자 DB에 적용하면 안 된다.

`cleanup_p05.py`는 이번 실행의 등록 대상만 처리하는 일회성 영수증 도구다.
이미 영수증이 있으면 재실행하지 않으며 디렉터리·기존 파일·retained DB를 지우지 않는다.
