"""로그 전체 대신 실제 testDone/JUnit/SQL 관측과 보존 SHA를 기록한다."""
import base64
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


def machine(path):
    names, files, cases, errors = {}, defaultdict(Counter), [], []
    done = None
    if not path.exists():
        return {'state': 'NOT_RUN'}
    suites = {}
    for line in path.read_text(errors='replace').splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get('type')
        if kind == 'suite':
            suites[event['suite']['id']] = event['suite']['path']
        elif kind == 'testStart':
            names[event['test']['id']] = event['test']
        elif kind == 'testDone' and not event.get('hidden'):
            test = names.get(event['testID'], {})
            outcome = 'SKIP' if event.get('skipped') else 'PASS' if event['result'] == 'success' else 'FAIL'
            file = Path(suites.get(test.get('suiteID'), '?')).name
            cases.append({'name': test.get('name'), 'file': file, 'result': outcome})
            files[file][outcome] += 1
        elif kind == 'error':
            errors.append({'name': names.get(event.get('testID'), {}).get('name'),
                           'error': str(event.get('error'))[:1600]})
        elif kind == 'done':
            done = event['success']
    return {'counts': dict(Counter(c['result'] for c in cases)), 'done_success': done,
            'files': dict(files), 'cases': cases, 'errors': errors,
            'log_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def junit(path):
    if not path.exists():
        return {'state': 'NOT_RUN'}
    root = ET.parse(path).getroot()
    suites = list(root) if root.tag == 'testsuites' else [root]
    return {**{key: sum(int(s.get(key, 0)) for s in suites)
               for key in ['tests', 'failures', 'errors', 'skipped']},
            'seconds': sum(float(s.get('time', 0)) for s in suites),
            'cases': [{'name': t.get('name'), 'result': 'FAIL' if t.find('failure') is not None
                       or t.find('error') is not None else 'SKIP' if t.find('skipped') is not None else 'PASS'}
                      for s in suites for t in s.findall('testcase')]}


def compact(value, key=''):
    if key in ['B', 'J', 'pending', 'baseline'] and isinstance(value, str):
        raw = base64.b64decode(value)
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if key == 'source' and isinstance(value, str):
        try:
            raw = base64.b64decode(value, validate=True)
            record = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            return value
        return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'record': record}
    if key in ['objects', 'refs'] and isinstance(value, list):
        return {'count': len(value), 'digest': digest(value)}
    if isinstance(value, dict):
        if {'pointers', 'generations', 'frozen', 'objects', 'pins'} <= value.keys():
            return {
                'pointers': value['pointers'], 'frozen': value['frozen'],
                'objects': value['objects'], 'pins': value['pins'],
                'generations': {ident: {
                    'sync_root': g['sync_root'], 'objects': g['objects'],
                    'receipt': g['receipt'], 'closure_count': len(g['closure']),
                    'closure_digest': digest(sorted(g['closure'])),
                    'source_counts': {t: len(rows) for t, rows in g['source'].items()},
                    'source_digest': digest(g['source']), 'control_digest': digest(g['control']),
                } if 'closure' in g else g for ident, g in value['generations'].items()},
                **({'legacy': value['legacy']} if 'legacy' in value else {}),
            }
        return {k: compact(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [compact(v) for v in value]
    return value


def collect(folder, require_complete=False):
    out = Path(folder)
    summary, cases = {}, {}
    logs = {
        'original_three': 'original-three.log', 'previous_independent': 'previous-independent.log',
        'new_independent': 'new-independent-final.log', 'flutter_full': 'flutter-full.log',
        'new_provenance': 'provenance-final.log',
        'phase_a_dart': 'regressions/phase-a-dart.log', 'a01_concurrent': 'regressions/a01-concurrent.log',
        'p0_integration': 'regressions/p0-integration.log',
        'historical_diagnostic': 'historical-diagnostic.log',
        'correction_cost': 'correction-cost/cost.log',
        'phase_a_cost': 'phase-a-cost/cost.log',
        'independent_cost': 'independent-cost-final/cost.log',
        'harness_first_compile': 'new-independent.log',
        'harness_overbroad_retention': 'new-independent-rerun.log',
        'harness_cost_compile_1': 'independent-cost/cost.log',
        'harness_cost_compile_2': 'independent-cost-rerun/cost.log',
        'harness_provenance_compile': 'provenance.log',
    }
    for name, path in logs.items():
        result = machine(out / path)
        cases[name] = result.pop('cases', [])
        summary[name] = result
    for name, path in {
        'backend': 'backend-full.xml', 'new_crash': 'new-crash.xml',
        'phase_a_crash': 'regressions/phase-a-crash.xml', 'a01_crash': 'regressions/a01-crash.xml',
        'ra01_crash': 'regressions/ra01-crash.xml', 'e2_cleanup': 'regressions/e2-cleanup.xml',
        'p0_replay': 'regressions/p0-replay.xml', 'historical_p0': 'p0-historical.xml',
        'e2_independent': 'e2-independent.xml',
    }.items():
        result = junit(out / path)
        records = result.pop('cases', [])
        if name != 'backend':
            cases[name] = records
        summary[name] = result
    backend = (out / 'backend-full.log').read_text()
    count = re.findall(r'(\d+) passed.*?(\d+) subtests passed', backend)
    summary['backend_counts'] = {'tests': int(count[-1][0]), 'subtests': int(count[-1][1])} if count else None
    summary['checks'] = json.loads((out / 'checks/checks.json').read_text())
    summary['exits'] = {p.stem: p.read_text().strip() for p in sorted(out.glob('*.exit'))}
    if (out / 'regressions/exits.json').exists():
        summary['regression_exits'] = json.loads((out / 'regressions/exits.json').read_text())
    inventory = json.loads((HERE / 'inventory.json').read_text())
    summary['target_files_unchanged'] = all(
        hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256']
        for row in inventory['diff'])
    summary['historical_files_unchanged'] = all(
        hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() == row['sha256']
        for row in inventory['historical'])
    summary['product_diff_since_target'] = subprocess.check_output(
        ['git', 'diff', '--name-only', 'af9525e', '--', 'mobile/lib', 'backend', 'frontend'],
        cwd=ROOT, text=True).strip()
    if require_complete:
        required_counts = {
            'original_three': {'PASS': 3}, 'previous_independent': {'PASS': 18},
            'new_independent': {'PASS': 18}, 'new_provenance': {'PASS': 6},
            'independent_cost': {'PASS': 2}, 'correction_cost': {'PASS': 4},
            'phase_a_cost': {'PASS': 2}, 'phase_a_dart': {'PASS': 36},
            'a01_concurrent': {'PASS': 1}, 'p0_integration': {'PASS': 18},
            'flutter_full': {'PASS': 1503, 'SKIP': 2},
        }
        for name, expected in required_counts.items():
            assert summary[name]['counts'] == expected, name
            assert summary[name]['done_success'] is True and not summary[name]['errors'], name
        for name, count in [('new_crash', 3), ('phase_a_crash', 6), ('a01_crash', 6),
                            ('ra01_crash', 7), ('e2_cleanup', 5), ('e2_independent', 9), ('p0_replay', 1)]:
            assert summary[name]['tests'] == count, name
            assert summary[name]['failures'] == summary[name]['errors'] == 0, name
        assert summary['backend_counts'] == {'tests': 1315, 'subtests': 1540}
        assert summary['backend']['failures'] == summary['backend']['errors'] == 0
        assert summary['target_files_unchanged'] and summary['historical_files_unchanged']
        assert not summary['product_diff_since_target']
        assert all(r['exit'] == 0 for r in summary['checks'].values() if 'exit' in r)
        assert all(r['exit'] == 0 for r in summary['regression_exits'])
        for name in ['original-three', 'previous-independent', 'new-independent-final', 'provenance-final',
                     'flutter-full', 'backend-full', 'new-crash', 'independent-cost-final', 'correction-cost',
                     'phase-a-cost', 'regressions', 'checks', 'e2-independent']:
            assert summary['exits'][name] == '0', name
    summary['completion_guard'] = 'COMPLETE' if require_complete else 'PROVISIONAL'
    (HERE / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    # Full Flutter successes are represented by independent per-file counts.
    cases['flutter_full'] = [c for c in cases['flutter_full'] if c['file'] in
                             ['segmented_e4_ra01_test.dart', 'segmented_e4_a01_test.dart']]
    (HERE / 'cases.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n')
    for src, target in [
        ('original-three.json', 'original-three.json'),
        ('new-independent-final.json', 'independent-state.json'),
        ('provenance-final.json', 'provenance-state.json'),
        ('independent-cost-final/cost.json', 'independent-cost.json'),
        ('correction-cost/cost.json', 'previous-cost-rerun.json'),
        ('correction-cost/cost.json.handoff.json', 'native-cost-rerun.json'),
        ('p0-historical/differential.json', 'p0-differential.json'),
    ]:
        if (out / src).exists():
            data = compact(json.loads((out / src).read_text()))
            (HERE / target).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    crashes = {}
    for folder in ['new-crash', 'regressions/phase-a-crash', 'regressions/a01-crash', 'regressions/ra01-crash']:
        for path in sorted((out / folder).glob('*.json')):
            crashes[str(path.relative_to(out))] = compact(json.loads(path.read_text()))
    (HERE / 'crashes.json').write_text(json.dumps(crashes, ensure_ascii=False, indent=2) + '\n')
    if (out / 'format-baseline.json').exists():
        (HERE / 'format-baseline.json').write_text((out / 'format-baseline.json').read_text())
    print(json.dumps({k: v.get('counts', v) if isinstance(v, dict) else v for k, v in summary.items()
                      if k not in ['checks', 'regression_exits', 'exits']}, ensure_ascii=False)[:1800])


if __name__ == '__main__':
    collect(sys.argv[1], '--require-complete' in sys.argv[2:])
