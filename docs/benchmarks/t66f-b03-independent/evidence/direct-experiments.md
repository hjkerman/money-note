# 직접 실행한 추가 반례의 재현 명령

아래는 이번 감사에서 이미 실행한 세 실험의 source를 보존한 것이다. 제품 파일은 수정하지 않는다.
출력 수치는 각각 `closed-lease-native-lifetime.json`, `pending-owner-retention.json`,
`generation-oracle-scope-contamination.json`에 있다. 이 세 실험을 pytest 신규 사례 수에 더하지 않았다.
저장소 root 및 `.venv/bin/python`에서 실행한다.

## IA05 — worker 등록 이전 거부

```python
import asyncio
import sys
sys.path[:0] = ['backend', 'docs/benchmarks/t66f-b03']
from counters import Collector, instrument_workers
from isolated_sync.workers import WorkerBudget

async def main():
    collector = Collector()
    budget = WorkerBudget(1)
    lease = budget.acquire()
    lease.close()
    completions = []
    with instrument_workers(), collector.stage('transfer'):
        try:
            await lease.run(lambda: None)
        except RuntimeError as error:
            assert str(error) == 'closed worker lease'
    collector.finish_when_idle(lambda value: completions.append(value.snapshot()))
    print(collector.pending, collector.closed, len(completions), budget.snapshot())
    # 관측: 1, False, 0, leases/jobs/running/tasks 모두0
    # 올바른 diagnostic 정산 기대: pending0 및 completion1회

asyncio.run(main())
```

## IA06 — 동일 transaction의 닫힌 owner 보존

```python
import gc
import sqlite3
import sys
import weakref
sys.path[:0] = ['backend', 'docs/benchmarks/t66f-b03']
from counters import Collector, observed_factory

for scopes in [10, 100, 1000]:
    db = sqlite3.connect(':memory:', isolation_level=None, factory=observed_factory())
    db.execute('CREATE TABLE t(k TEXT,b BLOB)')
    db.execute('BEGIN')
    references = []
    for n in range(scopes):
        collector = Collector()
        references.append(weakref.ref(collector))
        with collector.stage('generation'):
            db.execute('INSERT INTO t VALUES (?,?)', (str(n), b'x'))
        collector.close()
    del collector
    gc.collect()
    print(scopes, len(db._cost_pending), sum(r() is not None for r in references))
    # 관측: 10/50/10, 100/500/100, 1000/5000/1000
    db.execute('ROLLBACK')
    gc.collect()
    print('rollback 뒤 retained:', sum(r() is not None for r in references))
    # 관측: 모두0. transaction 종료 후 영구 leak로 주장하지 않는다.
    db.close()
```

## IA07 — 실제 mutation의 oracle SQL 귀속

실제 cursor를 한 번 위임해 반환된 row 수만 센다. 추가 SELECT/hash/parse를 실행하지 않는다.

```python
import json
import subprocess
import sys

child = r'''
import json
import sys
sys.path[:0] = ['backend', 'docs/benchmarks/t66f-b03']
import server
import counters
observed = []
execute = counters.CostConnectionMixin.execute
class Cursor:
    def __init__(self, inner, record):
        self.inner, self.record = inner, record
    def __iter__(self):
        for row in self.inner:
            self.record['returned_rows'] += 1
            yield row
    def __getattr__(self, name):
        return getattr(self.inner, name)
def spy(self, sql, parameters=()):
    result = execute(self, sql, parameters)
    if sql == 'SELECT hash FROM sync_objects':
        active = counters.ACTIVE.get()
        record = {'stage': active[1] if active else None, 'returned_rows': 0}
        observed.append(record)
        return Cursor(result, record)
    return result
counters.CostConnectionMixin.execute = spy
sys.argv = ['server.py', '3']
server.main()
print(json.dumps(observed), flush=True)
'''
process = subprocess.Popen([sys.executable, '-c', child], stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
def command(value):
    process.stdin.write(json.dumps(value) + '\n')
    process.stdin.flush()
    return json.loads(process.stdout.readline())
try:
    initial = json.loads(process.stdout.readline())  # 합성 token은 private pipe에만 유지
    command({'command': 'cost'})
    command({'command': 'mutate', 'op': 'update'})
    command({'command': 'cost'})
    command({'command': 'exit'})
    process.stdin.close()
    print(json.loads(process.stdout.readline()))
    assert process.wait(timeout=30) == 0
    # 관측: generation scope에서176/185행을 읽는 두 oracle SELECT
    # 제품 generation 작업으로 포함해야 하는 oracle SELECT 수의 기대는0이다.
finally:
    if process.poll() is None:
        process.kill()
        process.wait()
    process.stdout.close()
    process.stderr.close()
```
