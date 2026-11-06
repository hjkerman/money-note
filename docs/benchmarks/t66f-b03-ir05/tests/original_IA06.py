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
