# D3C-A01 독립 재감사 재현 자료

대상은 `3e54d6992872aba9589b1a34c3ebe4316c70d646`이다. 실제 삭제 실험은 매번
새로 만든 폐기용 synthetic SQLite DB만 사용한다. 외부 DB 경로를 입력받지 않는다.
구현 source와 기존 FAIL 보고서는 변경하지 않는다.

`test_review.py`는 수정 구현자의 테스트를 import하지 않는다. 기존 독립 감사의 seed,
직접 SQLite/C1/SHA-256/typed-edge/reachability/Patricia/ASGI oracle을 재사용하고,
새 connection으로 **모든 테이블의 전체 행**, integrity/FK 검사와 pre/post 객체 집합을
비교하는 별도 persisted-state checker를 추가했다. 기대 삭제 집합을 production GC의
eligibility/reachability helper에서 가져오지 않는다.

41개 시나리오는 open 전후/ABA 원자 교체와 symlink, batch 사이 교체, 같은 inode alias,
main FD/close/reuse, DELETE 뒤 rollback, 마지막 검사 뒤 원본 FD COMMIT, 병렬 TLS,
WAL snapshot/checkpoint, 정상 actual GC와 HTTP 복원, 12개 fail-closed 조건,
9개 SIGKILL 경계, steady FD/compile 계수, 실제 public ABI, ATTACH 거부,
동시 최초 초기화, 실제 다른 SQLite runtime을 검증한다.

## 실행

프로젝트 `.venv`의 Linux/Python 3.12.3/SQLite 3.45.1/default Unix VFS와 `/usr/bin/cc`를
사용했다. ABI 검사에만 공식 3.45.1 헤더가 필요하다. 구현 helper 자체는 이 헤더가
필요 없다. 다음 준비 명령은 공식 공개 파일의 고정 SHA-256을 확인한 뒤 `/tmp`에만
헤더를 저장한다. 이미 해당 헤더가 있으면 `AUDIT_SQLITE_INCLUDE`로 디렉터리를 지정할 수 있다.

```sh
.venv/bin/python docs/benchmarks/t66d3c-a01-reaudit/prepare_header.py
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-a01-reaudit/test_review.py
```

실제 미지원 SQLite 검사에는 별도 interpreter를 사용한다. 이 호스트에서는
`/home/hjkerman/anaconda3/bin/python3`의 Python 3.13.9/SQLite 3.51.0이었다.
다른 호스트는 `AUDIT_UNSUPPORTED_PYTHON`을 지정한다. 없으면 해당 1건을 skip하며
실제 미지원 runtime 검증을 수행했다고 주장할 수 없다. 나머지 OS/컴파일러 오류 등은
각 결과에 `MOCKED_FAILURE_INJECTION`으로 표시했다. 실제 VFS 교체, 실제 다른
SQLite library image, hook 변경, SIGKILL은 별도 process에서 수행했다.

원래 독립 반례는 원본 그대로 실행했다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py -k D3C_A01
.venv/bin/python -m pytest -q backend/tests/test_isolated_sync_retention_ownership.py
```

원래 감사 script의 `/tmp/mn-d3c-audit/D3C-A01.json`에는 실패 상태 label을 무조건 쓰는
과거 진단 문구가 남아 있다. 수정 전 역사적 증거를 덮어쓰지 않았다. 이번 결과는
pytest의 `assert after == before`, 새 41개 사례와 새 `results.json`을 기준으로 한다.

## 보존 증거

`results.json`은 최종 단일 41개 실행과 기존 31개 ownership/원래 반례/관련 회귀,
실제 backend·safety·frontend·정적 검사 결과를 보존한다. 중간 harness 오류와 재실행을
새 사례 수에 더하지 않았다. 원본 성공 로그와 임시 DB, compiled helper/header는
Git에 넣지 않았다. 개별 실행 JSON/JUnit/log는 `/tmp/mn-d3c-a01-reaudit/`에 남는다.

같은 DB에 대한 pre/post 비교는 경로 교체를 복원하고 모든 실험 연결을 정리한 뒤
새 연결로 수행한다. `/proc/self/fd`로 열린 실제 inode와 현재 pathname inode를 구분한다.
기존 DB의 WAL/SHM 파일을 수동 교체하는 실험은 수행하지 않았다.

최종 판정과 근거는 [재감사 보고서](../../t66d3c-a01-independent-reaudit.md)에 있다.
