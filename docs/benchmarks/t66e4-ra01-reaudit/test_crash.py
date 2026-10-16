"""최초 native와 legacy/native 왕복 후 경계를 실제 child SIGKILL로 검증한다."""
import base64
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('independent_state_oracle',
                                           HERE.parent / 't66e4-audit/state_oracle.py')
oracle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)
OUT = Path(os.environ.get('NR_CRASH_OUTPUT', '/tmp/mn-e4-ra01-reaudit/new-crash'))


@pytest.mark.parametrize('boundary', [
    'first_before_commit', 'first_after_commit', 'alternating_legacy_before_native'])
def test_independent_native_provenance_crash(tmp_path, boundary):
    root = tmp_path / 'owned'
    root.mkdir()
    (root / 'owned').write_text('synthetic independent RA01')
    OUT.mkdir(parents=True, exist_ok=True)

    def command(mode):
        return ['/home/hjkerman/.flutter/bin/flutter', 'test', '--no-pub', '--machine',
                '--dart-define=NR_ROOT=' + str(root), '--dart-define=NR_MODE=' + mode,
                '--dart-define=NR_BOUNDARY=' + boundary, str(HERE / 'crash_child_test.dart')]

    with (OUT / (boundary + '.log')).open('w') as log:
        child = subprocess.Popen(command('crash'), cwd=ROOT / 'mobile', stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        try:
            until = time.monotonic() + 180
            while not (root / 'barrier.json').exists():
                assert child.poll() is None, 'child failed before boundary'
                assert time.monotonic() < until, 'boundary timed out'
                time.sleep(.03)
            pid = json.loads((root / 'barrier.json').read_text())['pid']
            os.kill(pid, signal.SIGKILL)
            assert child.wait(timeout=45) != 0
        finally:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    saved = json.loads((root / 'expected.json').read_text())
    before = oracle.inspect(Path(saved['store']))
    with (OUT / (boundary + '-reopen.log')).open('w') as log:
        result = subprocess.run(command('recover'), cwd=ROOT / 'mobile',
                                stdout=log, stderr=subprocess.STDOUT, timeout=180)
    assert result.returncode == 0
    workspace = root / 'segmented-e4-workspace'
    after = oracle.inspect(Path(saved['store']), workspace if saved['frozen'] else None)
    recovered = json.loads((root / 'recovered.json').read_text())
    assert recovered['readable'] and recovered['r1'] == 'CLOSED'
    expected_installed = None if boundary == 'first_before_commit' else saved['installed']
    actual = after['pointers'].get('installed')
    assert (actual['generation_id'] if actual else None) == expected_installed
    assert (workspace / 'offline-mode/online-write-1.json').read_bytes() == base64.b64decode(saved['pending'])
    baseline = workspace / 'offline-mode/baseline.json'
    assert (baseline.read_bytes() if baseline.exists() else None) == (
        base64.b64decode(saved['baseline']) if saved['baseline'] else None)
    if saved['frozen']:
        assert len(after['frozen']) == 1
        assert after['frozen'][0]['id'] == saved['frozen']
    (OUT / (boundary + '.json')).write_text(json.dumps({
        'boundary': boundary, 'saved': saved, 'before_reopen': before,
        'after_reopen': after, 'fresh_process': recovered,
    }, ensure_ascii=False, indent=2) + '\n')
