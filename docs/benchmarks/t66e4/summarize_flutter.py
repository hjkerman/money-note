"""Flutter machine event 집계. 성공 종료와 hidden loader를 구별한다."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import sys


def summarize(path):
    suites, tests = {}, {}
    counts = Counter()
    files = defaultdict(Counter)
    done = None
    for line in Path(path).read_text().splitlines():
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
            test = event["test"]
            tests[test["id"]] = suites.get(test.get("suiteID"), "")
        if kind == "testDone" and event.get("hidden") is False:
            state = "skip" if event.get("skipped") else event["result"]
            counts[state] += 1
            files[Path(tests.get(event["testID"], "unknown")).name][state] += 1
        if kind == "done":
            done = event.get("success")
    return dict(done_success=done, totals=dict(counts),
                files={k: dict(v) for k, v in sorted(files.items())})


if __name__ == "__main__":
    result = summarize(sys.argv[1])
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
