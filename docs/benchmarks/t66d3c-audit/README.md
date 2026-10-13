# T6.6D3c 독립 감사 재현 자료

감사 대상은 `bcb0c47d42c5fb770ce40b70b0c14ad30d0c15f5`다. 판정은
**FAIL — TARGETED D3c CORRECTION REQUIRED**다. 구현 파일은 수정하지 않았다.

`test_audit.py`는 기존 구현자 테스트를 import하지 않고 자체 fixture, SQLite oracle,
C1/SHA-256 검사, typed graph 순회, fact 및 Patricia encoder, ASGI event capture를 사용한다.
직접 만든 폐기용 `RetentionSandbox`만 사용하며 외부 DB 경로를 받지 않는다.

최종적으로 서로 다른 **74개 사례 중 73 PASS / 1 FAIL**을 실행했다. 72개 사례의 전체 실행
뒤 historical-root blocker 두 사례를 추가 실행했다. 중간 harness 수정 전 결과나 같은 사례의
재실행을 이 수에 더하지 않았다. `results.json`에 각 사례와 실제 회귀 결과를 보존했다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py
```

위 명령은 감사 대상에서 `test_D3C_A01_open_inode_race_must_not_delete_other_database`가
실패해야 한다. `xfail`로 숨기지 않았다. 일반 backend suite 밖에 둔 독립 안전 회귀다.
실패만 좁게 재현하려면 다음 명령을 사용한다.

```sh
.venv/bin/python -m pytest -q docs/benchmarks/t66d3c-audit/test_audit.py -k D3C_A01
```

이 사례는 마지막 소유권 검사와 SQLite open 사이에 파일 교체를 결정적으로 삽입한다.
두 DB 모두 이번 실행이 만든 synthetic DB다. 다른 DB에서 객체 한 개가 COMMIT 삭제된
뒤 소유권 오류가 발생하는지를 직접 SQLite 재조회로 확인한다. Production 경로를 사용하지 않는다.

```sh
.venv/bin/python docs/benchmarks/t66d3c-audit/benchmark_audit.py
```

성능 측정도 새 synthetic DB 두 개만 만들며 376/10,000 ledger 행으로 제한된다.
10k는 immutable 객체 수가 아니라 `ledger_entries` 행 수다. 오래된 observation과 현재
observation을 유지한 채 중간 세대 객체를 회수한다. 결과와 임시 실행 기록은
`/tmp/mn-d3c-audit/`에 기록한다. 실행 후 DB는 폐기한다.

보존한 결과:

- `results.json`: 74개 독립 사례, backend 1,284/1,540 subtests, safety 59,
  frontend 21개, 정적 검사와 build의 실제 결과.
- `performance.json`: 두 DB의 독립 reachability 대조, 실제 GC, 두 번째 GC,
  파일·WAL·freelist 측정, HTTP 30개 측정 sample과 SQL access plan.
- `release-artifact-check.json`: baseline/target engine manifest와 artifact 일치 검증.
- `limit-zero-bytecode.json`: `LIMIT 0` schema probe가 행 순회 전에 종료하는 SQLite bytecode.

성능 값은 개발 호스트에서 다른 감사 사례와 겹쳐 측정했다. Production latency, hardware
power-loss durability, 전체 default quota의 최대 부하를 입증하지 않는다. 상세 판정과 수정
범위는 [독립 감사 보고서](../../t66/d/audits/t66d3c-independent-audit.md)에 있다.
