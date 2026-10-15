"""실제 machine/JUnit 및 fresh-state 관찰을 감사 artifact로 축약한다."""
from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).parent


def read(path):
    return json.loads(path.read_text()) if path.exists() else None


def machine(path):
    counts, cases, tests, suites, errors = Counter(), [], {}, {}, []
    done = None
    if not path.exists():
        return dict(status="NOT RUN")
    for line in path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "suite":
            suites[event["suite"]["id"]] = event["suite"].get("path", "")
        if kind == "testStart":
            tests[event["test"]["id"]] = event["test"]
        if kind == "testDone" and event.get("hidden") is False:
            test = tests[event["testID"]]
            state = "skip" if event.get("skipped") else event["result"]
            counts[state] += 1
            cases.append(dict(name=test["name"], result=state,
                              file=Path(suites.get(test.get("suiteID"), "")).name))
        if kind == "error":
            errors.append(dict(name=tests.get(event.get("testID"), {}).get("name"),
                               error=event.get("error")))
        if kind == "done":
            done = event.get("success")
    by_file = {}
    for case in cases:
        by_file.setdefault(case["file"], Counter())[case["result"]] += 1
    return dict(done_success=done, counts=dict(counts), files={k: dict(v) for k, v in by_file.items()}, cases=cases, errors=errors)


def junit(path):
    if not path.exists():
        return dict(status="NOT RUN")
    root = ET.parse(path).getroot()
    suites = [s.attrib for s in root.iter("testsuite")]
    return dict(tests=sum(int(s["tests"]) for s in suites),
                failures=sum(int(s["failures"]) for s in suites),
                errors=sum(int(s["errors"]) for s in suites),
                seconds=sum(float(s["time"]) for s in suites),
                cases=[dict(name=t.attrib["name"], result="failure" if t.find("failure") is not None or t.find("error") is not None else "success") for t in root.iter("testcase")])


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compact_state(value):
    value = copy.deepcopy(value)
    for g in value.get("generations", {}).values():
        if "source" in g:
            source = g.pop("source")
            normalized = {t: sorted(rows, key=lambda r: json.dumps(r, ensure_ascii=False, sort_keys=True)) for t, rows in source.items()}
            g["source_sha256"] = digest(normalized)
            g["table_rows"] = {t: len(rows) for t, rows in source.items()}
        if "control" in g:
            g["control_sha256"] = digest(g.pop("control"))
    return value


def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main(folder):
    folder = Path(folder)
    summary = {}
    for key, file in [("independent", "independent-final.log"), ("extra", "independent-extra.log"),
                      ("strengthened_positive", "positive-final.log"),
                      ("stale_recovery", "stale-recovery-final.log"),
                      ("stale_recovery_first", "stale-recovery.log"),
                      ("cost", "cost-final/cost.log"), ("flutter_initial", "flutter.log"),
                      ("flutter_final", "flutter-final.log"), ("p0_flutter", "p0-integration.log"),
                      ("historical_diagnostic", "historical-diagnostic.log")]:
        summary[key] = machine(folder / file)
    for key in ["backend", "backend-final", "backend-focused", "crash", "p0", "p0-replay", "safety", "diagnostics", "e2-cleanup"]:
        summary[key] = junit(folder / (key + ".xml"))
    summary['backend_stdout'] = {}
    for key in ['backend','backend-final']:
        log = (folder / (key+'.log')).read_text(errors='replace')
        summary['backend_stdout'][key] = dict(
            tests_passed=re.findall(r"(?<!subtests )(\d+) passed",log)[-1:],
            subtests_passed=re.findall(r"(\d+) subtests passed",log)[-1:],
            failed=re.findall(r"(\d+) failed",log)[-1:])
    summary['checks'] = {p.name: read(p) for p in folder.glob('*-exit.json')}
    summary['format_full'] = read(folder / 'format-full-summary.json')
    summary['preservation_final'] = read(folder / 'preservation-final.json')
    summary['p0_differential'] = read(folder / 'p0-results/differential.json')
    summary['p0_original_replay'] = read(folder / 'p0-results/original-replay.json')
    summary['frontend'] = {k:v for k,v in (read(folder/'frontend.json') or {}).items() if k in ['success','numPassedTests','numFailedTests','numPendingTests']}
    cases = []
    for group in ['independent','extra','cost','crash','p0-replay','stale_recovery']:
        for case in summary[group].get('cases',[]):
            cases.append(dict(id=f'E4-I{len(cases)+1:02d}',group=group,**case))
    save('independent-cases.json',cases)
    summary['independent_counts'] = dict(Counter(c['result'] for c in cases))
    # Logs remain temporary; permanent summary keeps errors and exact per-file totals.
    for item in summary.values():
        if isinstance(item,dict):
            item.pop('cases',None)
    save('summary.json',summary)
    states = read(folder/'independent-persisted.json') or []
    for row in states:
        if 'persisted' in row:
            row['persisted']=compact_state(row['persisted'])
    save('persisted-state.json',states)
    costs=read(folder/'cost-final/cost.json') or []
    for row in costs:
        row['persisted']=compact_state(row['persisted'])
    save('cost.json',costs)
    crashes=[]
    for p in sorted(folder.glob('crash-*.json')):
        value=read(p)
        if 'immediate' not in value:
            continue
        value['immediate']=compact_state(value['immediate'])
        value['recovered']=compact_state(value['recovered'])
        crashes.append(value)
    save('crash.json',crashes)
    save('warm-query-plans.json',read(folder/'warm-query-plans.json'))
    evidence = []
    for name in ['stale-recovery.json', 'stale-recovery-final.json']:
        value = read(folder / name)
        if value is None:
            continue
        value['independent_graph'] = compact_state(value['independent_graph'])
        evidence.append(dict(run=name, evidence=value))
    save('finding-e4-a01.json', evidence)
    save('environment.json', read(folder / 'environment.json'))
    print(json.dumps(dict(independent=summary['independent_counts'],flutter=summary['flutter_final'].get('counts'),backend=summary['backend-final'].get('tests')),ensure_ascii=False))


if __name__ == '__main__':
    main(sys.argv[1])
