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
