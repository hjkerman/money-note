"""원래 assertion·승인된 FD oracle·임시 복원 baseline을 분리 실행한다."""

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
BASE = "814eab506aa8457d10a7302241a26120b9389ff6"


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/mn-e2-a01-replay")
    out.mkdir(parents=True, exist_ok=True)
    source = subprocess.check_output(
        ["git", "show", f"{BASE}:docs/benchmarks/t66e2-audit/test_audit.py"],
        cwd=ROOT,
        text=True,
    )
    adapted = source.replace(
        "ROOT = Path(__file__).resolve().parents[3]", f"ROOT = Path({str(ROOT)!r})"
    ).replace(
        "HERE = Path(__file__).parent", 'HERE = ROOT / "docs/benchmarks/t66e2-audit"'
    )

    # 임시 위치의 resource lookup만 바꾸며 원래 두 test 함수의 AST는 그대로다.
    def assertions(text):
        return [
            ast.dump(node)
            for node in ast.parse(text).body
            if isinstance(node, ast.FunctionDef)
            and node.name.startswith("test_native_")
        ]

    assert assertions(source) == assertions(adapted)
    with tempfile.TemporaryDirectory(prefix="mn-e2-a01-original-") as temporary:
        original = Path(temporary) / "test_original.py"
        original.write_text(adapted)
        trials = [
            (
                "strict-original",
                [str(original), "-k", "native"],
                {"E2_AUDIT_OUTPUT": str(out / "strict-original")},
                4,
            ),
            (
                "original-strengthened",
                ["docs/benchmarks/t66e2-audit/test_audit.py", "-k", "native"],
                {"E2_AUDIT_OUTPUT": str(out / "original-strengthened")},
                0,
            ),
            (
                "correction-tcp",
                ["docs/benchmarks/t66e2-a01/test_cleanup.py"],
                {"E2_A01_OUTPUT": str(out / "correction-tcp")},
                0,
            ),
            (
                "baseline-tcp",
                ["docs/benchmarks/t66e2-a01/test_cleanup.py"],
                {
                    "E2_A01_OUTPUT": str(out / "baseline-tcp"),
                    "E2_A01_BASELINE_COMMIT": BASE,
                },
                4,
            ),
        ]
        results = {}
        for name, arguments, environment, failures in trials:
            start = time.monotonic()
            xml = out / (name + ".xml")
            with (out / (name + ".log")).open("w") as log:
                run = subprocess.run(
                    [
                        str(ROOT / ".venv/bin/python"),
                        "-m",
                        "pytest",
                        "-q",
                        *arguments,
                        "--junitxml=" + str(xml),
                    ],
                    cwd=ROOT,
                    env={**os.environ, **environment},
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=90,
                )
            suites = list(ET.parse(xml).getroot().iter("testsuite"))

            def count(key):
                return sum(int(s.get(key, 0)) for s in suites)

            result = dict(
                exit_code=run.returncode,
                tests=count("tests"),
                failed=count("failures"),
                errors=count("errors"),
                seconds=time.monotonic() - start,
            )
            results[name] = result
            print(name, json.dumps(result), flush=True)
            assert (
                result["tests"] == 5
                and result["failed"] == failures
                and not result["errors"]
            ), result
            assert run.returncode == (1 if failures else 0), result
        (out / "replays.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
