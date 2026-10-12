# D3C-A01 독립 targeted 재감사

## A. 최종 판정

**PASS — D3C-A01 INDEPENDENT TARGETED RE-AUDIT COMPLETE**

원래 반례는 닫혔다. 실제 열린 main DB FD를 승인 identity에 결합한 뒤 유지보수 변경을
수행하며, 독립 검증에서 승인되지 않은 DB의 committed deletion은 **0건**이었다.
새 Critical/High/Medium blocker는 발견되지 않았다. 새 41개 독립 사례와 전체 backend
**1,315 tests + 1,540 subtests**가 통과했다. 정상 synthetic GC도 동작한다.

## B. 감사 대상

- 수정 commit: `3e54d6992872aba9589b1a34c3ebe4316c70d646`.
- 수정 전 감사 commit: `6434d5e24cff316ff9a611b27b1d6cfc83e63d5c`.
- 최초 D3c 구현: `bcb0c47d42c5fb770ce40b70b0c14ad30d0c15f5`.
- 감사 일자: 2026-10-12, 개발 checkout `/home/hjkerman/codex/money-note`.

구현자의 31개 테스트와 보고서를 먼저 검토한 뒤, 원래 독립 반례와 새 41개 사례를
실행했다. 새 테스트는 구현자의 테스트를 import하지 않는다. 기존 독립 감사의 raw-state,
C1/SHA-256, typed graph, Patricia, ASGI oracle을 재사용한다.

## C. 저장소 상태

시작 시 branch는 `main`, working tree는 clean이며 `HEAD = main = origin/main =
실제 remote main = 3e54d6992872aba9589b1a34c3ebe4316c70d646`임을 확인했다.
`git ls-remote origin refs/heads/main`으로 remote를 직접 조회했다. 다른 revision을
대체하여 감사하지 않았다. 사용자 변경을 reset하거나 버리지 않았다.

감사 중 기존 tracked 파일의 diff는 0이었다. 이 보고서와 새 감사 전용 디렉터리만
추가한다. 원래 [FAIL 보고서](t66d3c-independent-audit.md)는 역사적 증거로 보존한다.
감사 commit은 이 보고서를 최초 추가한 commit으로 확인할 수 있다.

```sh
git log -1 --format=%H -- docs/t66d3c-a01-independent-reaudit.md
```

## D. 원래 D3C-A01

원래 finding은 MEDIUM이었다. `assert_owned()`가 pathname의 inode를 확인한 뒤
`sqlite3.connect()`가 별도 inode의 사본을 열 수 있었다. `Collector.sweep()`는 그
사본에서 객체 1개를 DELETE/COMMIT한 후 다음 mark의 ownership 오류를 반환했다.
**COMMIT 뒤 예외는 승인되지 않은 삭제를 복구하지 못한다.**

기존 반례는 별도 synthetic DB A/B의 symlink 교체를 open 직전에 삽입하고 B의 직접
SQLite 조회를 비교한다. 원본 테스트를 수정하지 않고 실행해 `assert after == before`가
통과했다. 새 사례는 이 비교를 객체뿐 아니라 모든 테이블의 전체 행으로 확장했다.

## E. 수정 diff 목록

`git diff --stat 6434d5e24cff316ff9a611b27b1d6cfc83e63d5c
3e54d6992872aba9589b1a34c3ebe4316c70d646` 결과는 **6개 파일, +930/-11**이다.

| 파일 | 실제 변경 |
|---|---|
| `backend/isolated_sync/owned_sqlite.py` | actual SQLite FD를 관측하는 native witness와 admission |
| `backend/isolated_sync/retention_schema.py` | exclusive 생성, 공통 open, connection binding, COMMIT guard |
| `backend/tests/test_isolated_sync_retention_ownership.py` | 31개 ownership 회귀 |
| `docs/benchmarks/t66d3c-a01/summary.json` | 구현자의 측정 자료 |
| `docs/specimens/t66d3b-release-artifacts.json` | source 변경에 따른 engine artifact 갱신 |
| `docs/t66d3c-implementation.md` | correction addendum |

전체 source/test diff와 addendum을 검토했다. `retention.py`의 mark/sweep/retention SQL,
schema version, certificate 의미, production app, 금융 공식, Snapshot v7, mobile은
수정되지 않았다. Release bundle의 versions와 raw/projection/policy artifact는 동일하며,
변경 항목은 `financial_engine` 하나다. 현재 source에서 생성한 bundle과 저장 artifact의
일치 및 각 payload의 길이/SHA-256도 별도로 확인했다.

## F. 실제 SQLite FD identity

`retention_schema.py:240`의 `_open()`은 새 private directory의 파일을
`O_CREAT|O_EXCL|O_RDWR|O_NOFOLLOW|O_CLOEXEC`와 mode `0600`으로 생성한다.
예상 identity는 이 exclusive-create FD의 `fstat()`에서 얻는다. 이 anchor FD는 sandbox
수명 동안 열려 있으므로 pathname 교체 후에도 원래 inode가 재사용되지 않는다.

`owned_sqlite.py:139`의 `opened_identity()`는 **동일 thread의 실제
`sqlite3.connect()` 호출**을 감싼다. 공개 Unix VFS syscall hook으로 SQLite가 전달한
main FD를 관측한다. Native witness는 dev/inode 불일치, fstat 실패, 서로 다른 FD의
모호한 관측을 거부한다(`:62`). 관측 없음도 거부한다(`:159`). Python이 별도로 연
anchor FD를 SQLite FD로 오인하지 않는다.

`retention_schema.py:253`은 `(sandbox, 실제 관측 FD, 예상 identity)`를 실제 반환된
`RetentionConnection`에 저장하고 반환 전에 검사한다. 별도 connection의 승인 결과를
재사용하지 않는다. Path 검사는 보조적인 거부 조건이며 FD 검증을 대신하지 않는다.

## G. Native helper와 SQLite ABI

`owned_sqlite.py:25`는 공개 `sqlite3_vfs` v3만 ctypes로 표현한다. 비공개 CPython
connection 또는 `unixFile` 구조체 offset을 읽지 않는다. `:42`의 C source 전체를
검토했다. 원래 fstat delegate를 호출한 뒤 thread-local witness를 갱신하며, 실패한
fstat의 buffer를 읽지 않는다. SQLite inode mutex 안에서 Python callback을 실행하지 않는다.

공개 VFS의 `xGetSystemCall`/`xSetSystemCall` 인터페이스와 3.45.1 Unix source의
`unixOpen → fillInUnixFile → findInodeInfo → osFstat(main FD)` 경로를 대조했다.
재사용된 UnixUnusedFd도 해당 경로를 거친다. 이는 버전별로 검증해야 하는 실제 호출
관계다. [SQLite 공개 VFS 정의](https://www.sqlite.org/c3ref/vfs.html),
[SQLite 3.45.1 Unix source](https://github.com/sqlite/sqlite/blob/version-3.45.1/src/os_unix.c).

`_install()`은 `_sqlite3.__file__`에서 실제 extension이 연결한 SQLite symbol을 가져온다
(`:93`). 고정 `/usr/bin/cc`와 고정 인자, 최소 PATH, 30초 한도를 사용하며 source는 stdin으로
전달한다(`:110`). 새 helper directory의 실제 mode는 `0700`이었다. 컴파일/로드 오류는
삭제를 허용하지 않는다. Library와 원 pointer는 `_installed`가 유지하며, atexit에서는 자기
hook인 경우 원 pointer를 복원한다(`:129`). 정상 호출 중 재컴파일하거나 hook을 교체하지 않는다.

## H. 지원 환경의 실측

| 항목 | 관측 |
|---|---|
| 실행 환경 | Linux x86_64, Python 3.12.3, `.venv/bin/python` |
| SQLite | Python API·실제 SQL·native symbol 모두 3.45.1 |
| source ID | `2024-01-30 16:01:20 e876e51a0ed5c5b3126f52e532044363a014bc594cfefa87ffb5b82257ccalt1` |
| 실제 native symbol library | `/lib/x86_64-linux-gnu/libsqlite3.so.0` (`dladdr`로 확인) |
| VFS | default `unix`, public interface v3 |
| ABI | 공식 3.45.1 header의 `sizeof(sqlite3_vfs)=168`, 22개 field offset 모두 ctypes와 일치 |
| host identity 폭 | `st_dev` 8 bytes, `st_ino` 8 bytes |
| 실제 FD | `/proc/self/fd`의 dev/inode가 승인 identity와 동일, exclusive-create anchor와 다른 FD |

버전 문자열만으로 ABI가 같다고 가정하지 않았다. 공식 header는 공개 배포 파일의
고정 SHA-256을 검증해 `/tmp`에만 추출했다. Header/archive hash는 결과 JSON에 보존했다.
해당 호스트에서 SQLite FD, 실제 library와 SQL connection의 source ID를 함께 확인했다.
다른 아키텍처·다른 배포판의 동작을 직접 실행했다고 주장하지 않는다.

## I. 미지원 환경 및 실패 시 거부

새 12개 실패 시나리오와 실제 별도 runtime 사례에서 모든 persisted rows가 유지됐다.

| 조건 | 검증 방식 | 결과 |
|---|---|---|
| 미지원 OS | MOCKED_FAILURE_INJECTION | open/admission 거부 |
| 미지원 version | MOCKED_FAILURE_INJECTION | open/admission 거부 |
| SQLite 3.51.0 / Python 3.13.9 | REAL_EXECUTION | DB open 0, platform 거부 |
| default VFS `unix-dotfile` | 실제 VFS 교체, 격리 child process | 거부 |
| compiler 없음·실행 거부·컴파일 오류·timeout | 각각 MOCKED_FAILURE_INJECTION | 거부 |
| helper load 실패 | MOCKED_FAILURE_INJECTION | 거부 |
| 설치된 hook 불일치 | 실제 syscall pointer 교체, 격리 child process | 거부 |
| 유효 FD 없음 | MOCKED_FAILURE_INJECTION | 거부 |
| 다른 SQLite library image | 실제 별도 image 로드, connection은 원 library 사용 | witness 없음으로 거부 |
| 동시 초기화 실패 | 4 thread, compiler 오류 주입 | 모두 거부 |
| ATTACH | 실제 disposable DB의 ATTACH 시도 | authorizer 거부, main 하나 유지 |

Compiler의 실제 삭제/OS 변경을 수행하지 않았다. 실제 macOS/Windows 검증도 아니다.
지원 불가 시 `stat()`만으로 승인하는 fallback은 없다.

## J. 원래 반례 재실행

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py -k D3C_A01
```

원래 독립 테스트는 수정하지 않은 상태에서 PASS했다. 기존 31개 ownership과 admission
marker 사례를 함께 선택한 실제 실행은 **33 PASS / 0 FAIL**, JUnit 123.181초다.
원래 테스트의 B 객체 집합 비교가 통과한 것을 확인했다.

기존 script가 쓰는 임시 `D3C-A01.json`에는 과거 `CONFIRMED FAILURE` 문구가 무조건
남는다. 이번 판정은 그 label에 의존하지 않는다. 새로운 실행 기록과 실제 `assert after ==
before`, 새 fresh-connection checker를 기준으로 한다. 과거 FAIL artifact는 변경하지 않았다.

## K. Pre-open 교체

새 6개 open 교체 사례는 before/after/ABA 각각에 atomic replacement와 symlink를 적용한다.
Before-open에서는 사본 B를 실제로 열려고 하지만 native fstat의 identity 불일치로 거부한다.
ABA에서는 Python connect 반환 전에 원 pathname을 복구해도 거부한다. 따라서 단순한
pre/post pathname 검사를 통과시키는 방식으로 connection을 승인할 수 없다.

대표 DB의 원본/사본 객체 수는 각각 283이었다. A/B의 dev/inode는 다르며, 검사 후 B의
삭제 객체 집합은 빈 집합이었다. 모든 테이블의 전체 pre/post 행도 동일했다. 각 실제
identity와 예외는 `results.json`의 `swap_*`에 보존했다.

## L. Post-open 교체

SQLite가 A를 연 다음 pathname을 B로 바꾸면 열린 FD는 A를 계속 가리킨다. 최초 반환
guard가 path 불일치를 발견해 연결을 닫는다. B에 DELETE가 실행됐다고 pathname만으로
추정하지 않았다. 실제 FD inode와 교체 복원 후의 A/B persisted state를 각각 확인했다.
기존 연결을 재사용하는 기존 regression도 같은 원본 FD를 확인하고 COMMIT을 거부했다.

## M. Batch 사이 교체

첫 정상 batch의 A 객체 1개 삭제/COMMIT을 확인한 후, 다음 batch 전에 경로를 B로
교체했다. 후속 sweep과 새 connection 모두 거부됐고 B 전체 행은 그대로였다.
이미 승인된 A의 이전 COMMIT을 승인되지 않은 B의 삭제로 집계하지 않았다.

Mark plan의 owner/fence 검사와 batch마다 새 connection을 여는 구조는 불변이다.
새 연결마다 실제 FD 승인을 다시 받아야 하며 이전 batch의 승인으로 대체할 수 없다.

## N. Symlink·inode·사본

Symlink substitution과 동일 pathname의 다른 inode로의 원자 교체 모두 거부했다.
DB schema/profile/marker/certificate까지 복사해도 A collector의 소유권이 B로 이전되지
않는다. 다른 새 sandbox가 자기 exclusive-create inode를 소유하는 것과 구별했다.

같은 owned private directory 안의 hardlink alias는 같은 dev/inode라는 positive control을
통과했다. Symlink는 정책상 거부되며 임의의 외부 path를 소유권 대상으로 인수하지 않는다.
초기 생성 시 기존 파일/symlink를 심는 경우도 기존 31개 회귀에서 거부됐다.

## O. Connection 재사용과 FD 수명

Actual SQLite FD는 connection이 닫힐 때까지 관측된 main inode를 유지했다. 단독 연결을
닫은 후 해당 FD의 fstat는 실패했고 exclusive anchor는 계속 유효했다. 닫힌 connection의
SQL은 `ProgrammingError`였다. Kernel이 다른 disposable file에 FD 번호를 재사용한
경우 identity 검사가 거부했다. 활성 SQLite FD를 `dup2` 등으로 강제로 탈취하지 않았다.

동시 GC 두 건은 서로 다른 새 DB와 TLS witness를 사용했고 각각 자기 DB의 승인된
후보만 삭제했다. VFS hook의 process-wide 상태가 DB별 승인 정보를 혼합하지 않았다.
SQLite의 내부 pending FD 재사용은 기존 WAL 다중 연결 회귀에서도 확인했다.

## P. WAL 및 다중 connection

Main DB FD가 인가 anchor다. WAL reader가 이전 snapshot을 유지한 채 다른 승인
connection이 GC COMMIT을 수행할 수 있었다. PASSIVE checkpoint 뒤에도 실제 main FD
identity가 동일했고 새 연결에서 올바른 삭제 집합과 current graph를 확인했다.
기존 WAL reader/교체/동시 writer 사례도 통과했다.

Path가 같은 두 connection을 같은 DB로 추정하지 않는다. 새 connection은 별도의 FD
관측이 필요하다. ATTACH는 일반 경로에서 authorizer가 거부하며 destructive SQL은 main의
수정된 connection을 사용한다. WAL/SHM 파일을 별도로 교체하거나 섞는 조작은 수행하지
않았다. 임의 파일 변조에 대한 일반 저장장치 무결성 보장을 이 결과로 주장하지 않는다.

## Q. 인가와 COMMIT 순서

실제 순서는 `exclusive-create identity → path 보조 검사 → SQLite native open/FD 관측 →
connection binding → schema/profile → 기존 BEGIN/fence → DELETE → FD/path 재검사 →
COMMIT`이다. SQLite C context manager가 Python `commit()` override를 호출하지 않기
때문에 `RetentionConnection.__exit__()`도 독립적으로 guard한다(`retention_schema.py:159`).
실패하면 COMMIT 전에 rollback한다(`:151`).

| 유지보수 경로 | 실제 연결 및 commit 경계 |
|---|---|
| 객체/edge/cache 삭제 | `retention.py:322` sweep, `:349/:350/:358` DELETE, `:367` guarded commit |
| pin release/metadata 회수 | `retention.py:98/:114`, `ObservationRepository._connection()`의 guarded context/commit |
| explicit root protect/unprotect | `retention.py:399/:419`, 같은 sandbox의 guarded context |
| isolated migration | `retention_schema.py:271` 공통 `_open()`, `:318` guarded commit |

DELETE 뒤 마지막 COMMIT 전에 교체하면 원본 A의 삭제도 rollback된다. 별도로 **마지막
검사가 끝난 직후 경로를 바꾼** 사례에서는 A의 actual FD로 승인된 삭제 1개가 COMMIT됐고,
B의 전체 행은 유지됐다. 이후 path 오류는 발생했으나 승인되지 않은 COMMIT은 아니었다.
Actual modified inode를 기준으로 판단해야 하는 이유를 이 사례로 직접 확인했다.

## R. 독립 persisted-state oracle

새 `snapshot()`은 maintenance helper를 거치지 않는 fresh SQLite connection으로
`BEGIN IMMEDIATE`, 전체 table/row SELECT, integrity/FK 검사를 수행하고 rollback/close한다.
실험 연결 정리 뒤 이 조회가 성공하여 남은 write lock도 없음을 확인했다. 교체 실험은
원본과 사본을 별도로 복원·재조회한다. 승인 identity, actual opened inode, 현재 visible
inode, 객체 집합 차이와 예외를 따로 기록했다.

Reachability 기대값은 기존 **독립** C1 decoder/SHA-256/typed-edge/root oracle에서 계산했다.
Production GC의 후보 계산 또는 eligibility helper를 기대값으로 사용하지 않았다.

## S. 승인되지 않은 committed deletion

**UNAUTHORIZED COMMITTED DELETIONS = 0.**

새 41개 최종 사례 모두 PASS이며 새 음성 사례의 다른 DB 전체 행은 불변이었다.
예외 발생만으로 PASS 처리하지 않았다. 이미 승인된 A의 정상 COMMIT, B의 committed
deletion, rollback된 DELETE를 구별했다. 현재 retention obligation 밖의 객체만 정상
positive control에서 삭제됐다.

## T. 정상 synthetic GC

Active historical observation을 유지하고 mutation 3회 후 actual GC를 실행했다.
직접 계산한 unreachable set과 실제 삭제 집합이 정확히 같았고 **22개 객체가 삭제**됐다.
263개 reachable 객체, 11개 금융 table, current/fence/certificate/observation/pin 상태는
보존됐다. 정상 GC 전체를 차단하는 수정이 아님을 확인했다. 두 번째 실행의 객체/행
추가 삭제는 0이었다.

## U. Retained graph 보존

새 positive control은 유지된 observation을 실제 인증 D3b HTTP 경로로 복원해
14개 요청, 222개 수신 객체, 11개 테이블, 104개 facts와 Patricia를 검증했다.
Current graph는 direct raw-state/Patricia/input-proof oracle로 다시 검사했다.

이와 별개로 이전 독립 감사의 관련 **17개 사례**를 재실행했다. GC 뒤 old/current
observation의 HTTP 복원, internal input-proof 다운로드 거부, wrong principal 거부,
writer/observation/epoch stale mark, WAL mark/publication, shared roots와 concurrent
release, 실제 ASGI Task.cancel/native worker/GC 경계가 모두 PASS했다. 전체 원래 감사의
74개를 다시 수행했다고 주장하지 않는다. 전체 backend는 별도로 실행한다.

## V. Crash/restart

새 disposable file-backed DB에서 다음 9개 실제 SIGKILL 경계를 실행했다.

| 경계 | 재시작 후 committed deletion |
|---|---:|
| 실제 SQLite open 전 | 0 |
| helper 초기화 중, compiler 호출 직전 | 0 |
| actual open 후 witness 종료 전 | 0 |
| witness 확보 후 connection binding 전 | 0 |
| destructive SQL 직전 | 0 |
| DELETE transaction 중 | 0 |
| COMMIT 직전 | 0 |
| COMMIT 직후 | 승인된 원본 객체 1 |
| connection close 직후 cleanup | 승인된 원본 객체 1 |

각 restart에서 fresh connection, integrity/FK, current 11-table/Patricia/input-proof,
dry mark 및 새 connection의 actual FD를 확인했다. Batch 사이 실패 경계는 M절의
경로 교체·후속 거부로 검증했다. 기존 crash 회귀도 backend suite에 포함된다.
SIGKILL 결과를 hardware power-loss durability 증명으로 확대하지 않는다.

## W. 실제 회귀 결과

| 검증 | 독립 실행 결과 |
|---|---|
| 수정 ownership 31개 + 원래 독립 반례 + 기존 admission marker | 33 PASS |
| 새 독립 targeted 사례 | 41 PASS, 0 FAIL, 0 SKIP; 40.404초 |
| 기존 독립 D3c 관련 사례 | 17 PASS, 0 FAIL; 38.668초 |
| 전체 backend | 1,315 tests + 1,540 subtests PASS, 0 FAIL; 1,511.44초, warning 1 |
| safety/diagnostic (`scripts/tests scripts/benchmarks`) | 59 PASS |
| frontend Vitest | 21 PASS, 6 files |
| frontend build | PASS |
| Ruff | PASS |
| compileall | PASS |
| git diff --check | PASS |

주요 명령은 다음과 같다. 성공 로그 전체를 보고서에 복사하지 않았다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-a01-reaudit/test_review.py
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py -k 'post_gc_http_eleven or native_cancel_transfer_gc or cancelled_two_natives or materialized_network_cancel or shared_principal or release_concurrent or stale_mark or mark_snapshot'
# backend working directory
../.venv/bin/python -m pytest -q --durations=10 --junitxml=/tmp/mn-d3c-a01-reaudit/backend.xml
# repository root
.venv/bin/python -m pytest -q scripts/tests scripts/benchmarks
npm --prefix frontend test
npm --prefix frontend run build
.venv/bin/python -m ruff check backend/app backend/isolated_sync backend/tests scripts/tests scripts/benchmarks docs/benchmarks/t66d3c-a01-reaudit
.venv/bin/python -m compileall -q backend/app backend/isolated_sync backend/tests scripts/tests scripts/benchmarks docs/benchmarks/t66d3c-a01-reaudit
git diff --check
```

JUnit와 최종 단일 실행의 개별 결과는 [results.json](benchmarks/t66d3c-a01-reaudit/results.json)에
집계했다. Backend JUnit의 2,855개 testcase는 1,315 tests와 1,540 subtests를 합친 수다.
D3c admission/retention/mark/sweep/concurrency/crash, D3B-M01, D3a, D2b, isolated schema,
Snapshot v7을 포함한 전체 backend를 실제 실행했다. 중간 감사 harness 수정 전 실행과
같은 사례의 재실행은 독립 사례 수에 더하지 않았다. Backend와 safety의 warning은
기존 Starlette/httpx TestClient deprecation이며 이번 수정의 실패가 아니다.

## X. 성능과 자원 영향

소스상 helper initialization/컴파일은 `_install()` lock 아래 process당 한 번이며 정상
app import/startup에서 호출되지 않는다. 격리 child의 initialization cache를 비우고 실제
컴파일 호출을 계측한 4 thread·8 connection 실행에서는 컴파일 1회였다. 이후
3 warmup + 40 measured open/close에서 추가 compile 0회, FD 수 29→29였다.
측정 중앙값 **0.283 ms**, p95 **0.309 ms**이며 개별 sample을 결과 JSON에 보존했다.
이 측정에는 감사자의 fstat/proc 확인도 포함되며 before/after 개선율 측정이 아니다.

수정 경로에는 새로운 SQL/history/object scan이 없다. `backend/app`과 금융 route의
diff도 없다. 유지보수의 기존 graph 검증 비용은 이번 수정으로 바뀌지 않았으며,
10k 전체 GC 벤치마크를 재실행하지 않았다. 구현자의 240-sample/GC 성능 자료를
독립 측정 결과로 인용하지 않는다. 초기 compiler 실행은 DB write transaction 밖이다.

## Y. Findings와 severity

이번 수정에서 새 Critical **0**, High **0**, Medium **0**, Low **0**이다.
재현 가능한 ownership bypass, 승인되지 않은 committed deletion, required root 삭제,
worker lifetime regression을 발견하지 못했다. 미확인 가설을 confirmed finding으로
만들지 않았다. 원래 **D3C-A01은 CLOSED**로 판정한다.

## Z. 잔여 한계

확인한 환경은 위 Linux x86_64/SQLite 3.45.1/Unix VFS다. Upgrade와 다른 ABI/VFS는
별도 검증 대상이며 현재 gate의 거부를 portability 결함으로 분류하지 않는다.
같은 process의 임의 native code가 live SQLite FD를 강제 close/replace하거나 VFS/guard를
악의적으로 해제하는 경우의 sandbox 보안을 증명하지 않는다. Main/WAL/SHM을 외부에서
임의로 섞는 저장소 파괴도 정상 지원 시나리오로 취급하지 않는다.

Bounded deterministic 실행이 가능한 모든 OS schedule의 수학적 증명은 아니다. 다만
실제 열린 FD의 source 경로, connection binding, COMMIT 경계와 독립 persisted-state
검증이 서로 일치한다. 기존 전체 D3c 감사의 다른 합격 영역을 새로 전면 재감사하지 않았다.

## AA. Production 격리

모든 actual deletion은 이번 테스트가 새로 만든 disposable DB에 한정했다. Production
DB/API/service/credential/user data에 접근하지 않았다. 금융 입력 변경은 synthetic
fixture의 통제된 mutation뿐이며 authoritative production 금융 행은 다루지 않았다.
기존 구현 파일과 정상 startup/route/segmented activation은 불변이다. Snapshot v7,
OfflineBaseline v4, frozen journal도 불변이다. 배포·서비스 재시작·운영 migration·
normal-runtime GC 활성화·T6.6E/R1 구현을 수행하지 않았다.

## AB. 최종 판정과 후속 단계

**PASS — D3C-A01 INDEPENDENT TARGETED RE-AUDIT COMPLETE**

원래 반례가 닫혔고 승인되지 않은 committed deletion은 0이다. 기존 D3c 독립 감사에서
확인된 유일한 blocker가 해소됐으며 해당 독립 감사 상태를 PASS로 갱신할 근거가 있다.
T6.6E 구현을 시작할 수 있다. 이번 감사에서 구현을 시작하지 않았으며 배포 허가도 아니다.

## AC. 다음 조치

감사 전용 artifact를 보존하고 별도 작업으로 T6.6E 구현을 시작한다.

---

```text
D3C-A01 INDEPENDENT TARGETED RE-AUDIT:
PASS

AUDITED COMMIT:
3e54d6992872aba9589b1a34c3ebe4316c70d646

AUDIT COMMIT:
이 보고서를 최초 추가한 감사 전용 commit; C절의 git log 명령으로 확인

REPOSITORY STATE:
VERIFIED

ORIGINAL FINDING:
D3C-A01

ORIGINAL SEVERITY:
MEDIUM

ORIGINAL COUNTEREXAMPLE:
CLOSED

ACTUAL SQLITE FD IDENTITY:
VERIFIED

CONNECTION-BOUND OWNERSHIP:
PASS

SQLITE ABI / NATIVE HELPER:
PASS

SUPPORTED ENVIRONMENT:
VERIFIED

UNSUPPORTED ENVIRONMENT FAIL-CLOSED:
PASS

PRE-OPEN SWAP:
PASS

POST-OPEN SWAP:
PASS

BETWEEN-BATCH SWAP:
PASS

SYMLINK SUBSTITUTION:
PASS

SAME-PATH INODE REPLACEMENT:
PASS

COPIED DB OWNERSHIP:
PASS

CONNECTION REUSE:
PASS

FD LIFETIME:
PASS

WAL / MULTI-CONNECTION:
PASS

AUTHORIZATION BEFORE DESTRUCTIVE COMMIT:
PASS

UNAUTHORIZED COMMITTED DELETIONS:
0

INDEPENDENT PERSISTED-STATE ORACLE:
PASS

LEGITIMATE SYNTHETIC GC:
PASS

CURRENT COMPLETE GENERATION:
PROTECTED

HISTORICAL CERTIFICATE EVIDENCE:
PRESERVED

ACTIVE OBSERVATIONS:
PROTECTED

IN-FLIGHT TRANSFERS:
PROTECTED

D3B-M01:
PRESERVED

MARK/SWEEP:
PRESERVED

WRITER/GC CONCURRENCY:
PRESERVED

OBSERVATION/GC CONCURRENCY:
PRESERVED

TRANSFER/GC CONCURRENCY:
PRESERVED

CRASH/RESTART:
PASS

NORMAL REQUEST O(N) REGRESSION:
NONE FOUND

INDEPENDENT RE-AUDIT TESTS:
41 PASSED
0 FAILED

BACKEND FULL REGRESSION:
1315 TESTS
1540 SUBTESTS
PASS

RUFF:
PASS

COMPILEALL:
PASS

GIT DIFF CHECK:
PASS

SNAPSHOT V7:
UNCHANGED

FINANCIAL FORMULAS:
UNCHANGED

NORMAL BACKEND RUNTIME:
UNCHANGED

SEGMENTED ENDPOINTS:
NOT ACTIVATED

PRODUCTION ACCESS:
NONE

DEPLOYMENT:
NOT PERFORMED

NEW CRITICAL:
0

NEW HIGH:
0

NEW MEDIUM:
0

NEW LOW:
0

D3C-A01 STATUS:
CLOSED

D3c INDEPENDENT AUDIT STATUS:
PASS

SAFE TO START T6.6E:
YES

SAFE TO DEPLOY:
NO

FINAL VERDICT:
PASS — D3C-A01 INDEPENDENT TARGETED RE-AUDIT COMPLETE

NEXT ACTION:
감사 전용 artifact를 보존하고 별도 작업으로 T6.6E 구현을 시작한다.
```
