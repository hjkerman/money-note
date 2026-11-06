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
