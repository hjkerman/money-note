"""기존 assertion을 바꾸지 않고 합성 회귀를 새 출력 폴더에서 실행한다."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
FLUTTER = '/home/hjkerman/.flutter/bin/flutter'
PYTHON = str(ROOT / '.venv/bin/python')


def main(folder):
    out = Path(folder).resolve()
    out.mkdir(parents=True, exist_ok=True)
    tasks = []

    def dart(name, paths, defines=()):
        tasks.append((name, [FLUTTER, 'test', '--no-pub', '--machine',
                            *defines, *paths], ROOT / 'mobile', {}))

    dart('phase-a-dart', ['../docs/benchmarks/t66e4-audit/independent_test.dart',
                          '../docs/benchmarks/t66e4-audit/stale_recovery_test.dart'])
    dart('a01-concurrent', ['../docs/benchmarks/t66e4-a01/concurrent_recovery_test.dart'])
    dart('p0-integration', ['../docs/benchmarks/t66e4-p0-audit/integration_test.dart'])
    for name, path, env in [
        ('phase-a-crash', 't66e4-audit/test_crash.py', 'E4_AUDIT_OUTPUT'),
        ('a01-crash', 't66e4-a01/test_crash.py', 'E4_A01_OUTPUT'),
        ('ra01-crash', 't66e4-ra01/test_crash.py', 'E4_RA01_OUTPUT'),
        ('e2-cleanup', 't66e2-a01/test_cleanup.py', 'E2_A01_OUTPUT'),
        ('p0-replay', 't66e4-audit/test_p0_replay.py', 'E4_P0_AUDIT_OUTPUT'),
    ]:
        tasks.append((name, [PYTHON, '-m', 'pytest', '-q',
                            str(ROOT / 'docs/benchmarks' / path),
                            '--junitxml=' + str(out / (name + '.xml'))], ROOT,
                      {env: str(out / name)}))
    results = []
    for name, command, cwd, extra in tasks:
        started = time.monotonic()
        with (out / (name + '.log')).open('w') as log:
            process = subprocess.run(command, cwd=cwd, env=os.environ | extra,
                                     stdout=log, stderr=subprocess.STDOUT, timeout=3600)
        row = dict(name=name, command=command, exit=process.returncode,
                   seconds=time.monotonic() - started)
        results.append(row)
        (out / 'exits.json').write_text(json.dumps(results, indent=2) + '\n')
        print(name, process.returncode, flush=True)
        if process.returncode:
            print('\n'.join((out / (name + '.log')).read_text().splitlines()[-12:]), flush=True)
    return int(any(r['exit'] for r in results))


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1]))
