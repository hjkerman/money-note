"""최종 source의 한정 회귀/정적 검사. 원 감사 파일은 읽기 전용이다."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PY = str(ROOT / ".venv/bin/python")
FLUTTER = "/home/hjkerman/.flutter/bin/flutter"
DART = "/home/hjkerman/.flutter/bin/cache/dart-sdk/bin/dart"
phase = sys.argv[1]
out = Path(tempfile.mkdtemp(prefix=f"mn-a02-{phase}-"))
rows = []


def run(name, argv, cwd=ROOT, env=None):
    log = Path("/tmp") / f"mn-a02-{name}.log"
    started = time.monotonic()
    with log.open("w") as stream:
        result = subprocess.run(
            argv,
            cwd=cwd,
            env={**os.environ, **(env or {})},
            stdout=stream,
            stderr=subprocess.STDOUT,
        )
    row = dict(
        name=name,
        args=argv,
        cwd=str(cwd),
        synthetic_outputs=env or {},
        log=str(log),
        exit=result.returncode,
        elapsed_seconds=time.monotonic() - started,
    )
    rows.append(row)
    (HERE / f"validation-{phase}.json").write_text(
        json.dumps(dict(out=str(out), commands=rows), indent=2) + "\n"
    )
    print(json.dumps(row), flush=True)
    if result.returncode:
        print(log.read_text()[-4000:], flush=True)  # failures only


if phase == "compatibility":
    run(
        "p0-compatible-replay",
        [
            PY,
            "-m",
            "pytest",
            "-q",
            "docs/benchmarks/t66e4-audit/test_p0_replay.py",
            f"--junitxml={out}/p0-compatible.xml",
        ],
        env={"E4_P0_AUDIT_OUTPUT": str(out / "p0-compatible")},
    )
    run(
        "historical-p0-probe",
        [
            FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            "../docs/benchmarks/t66e4-contract/probe_test.dart",
        ],
        ROOT / "mobile",
    )
elif phase == "external-backend":
    run(
        "backend-related",
        [
            PY,
            "-m",
            "pytest",
            "-q",
            "tests/test_isolated_sync_observation.py",
            "tests/test_isolated_sync_transfer.py",
            "tests/test_isolated_sync_transfer_failures.py",
            "tests/test_isolated_sync_transfer_cancellation.py",
            "tests/test_isolated_sync_retention_ownership.py",
            "-k",
            "concurrent or busy or identity or cancel or ownership or quota",
        ],
        ROOT / "backend",
    )
    run(
        "independent-backend",
        [
            PY,
            "-m",
            "pytest",
            "-q",
            "docs/benchmarks/t66f-b01/test_b01.py",
            "docs/benchmarks/t66f-b01-independent/test_independent.py",
            "docs/benchmarks/t66f-phase-b/test_backend.py",
            "docs/benchmarks/t66f-phase-b/test_http_concurrency.py",
            f"--junitxml={out}/backend.xml",
        ],
        env={
            "B01_OUTPUT": str(out / "b01"),
            "B01_INDEPENDENT_OUTPUT": str(out / "b01-independent"),
            "F_BACKEND_OUTPUT": str(out / "phase-b-backend"),
            "F_HTTP_OUTPUT": str(out / "phase-b-http"),
        },
    )
    run(
        "p0-independent-backend",
        [
            PY,
            "-m",
            "pytest",
            "-q",
            "docs/benchmarks/t66e4-p0-audit/test_audit.py",
            f"--junitxml={out}/p0.xml",
        ],
        env={"E4_P0_AUDIT_OUTPUT": str(out / "p0")},
    )
elif phase == "external-flutter":
    for name, files, env in (
        (
            "wire-regression",
            [
                "t66f-phase-b/integration_test.dart",
                "t66f-b01-independent/http_quota_test.dart",
            ],
            {
                "F_PHASE_B_OUTPUT": str(out / "wire.json"),
                "B01_HTTP_OUTPUT": str(out / "quota.json"),
            },
        ),
        (
            "p0-independent-flutter",
            ["t66e4-p0-audit/integration_test.dart"],
            {"E4_P0_INTEGRATION_OUTPUT": str(out / "p0.json")},
        ),
        (
            "continuation-negative-authority",
            ["t66f-phase-b-continuation/adversarial_test.dart"],
            {"CONTINUATION_OUTPUT": str(out / "negative-authority.json")},
        ),
        (
            "continuation-lineage",
            ["t66f-phase-b-continuation/lineage_test.dart"],
            {"CONTINUATION_OUTPUT": str(out / "lineage.json")},
        ),
    ):
        defines = [
            f"--dart-define={k}={v}"
            for k, v in env.items()
            if k != "E4_P0_INTEGRATION_OUTPUT"
        ]
        run(
            name,
            [
                FLUTTER,
                "test",
                "--no-pub",
                "--machine",
                "--concurrency=2",
                *defines,
                *["../docs/benchmarks/" + f for f in files],
            ],
            ROOT / "mobile",
            env=env,
        )
elif phase == "lineage-fixed":
    # Source contract is C_LINEAGE_OUTPUT, not the old README's generic name.
    # Keep the original failed output/log; assertions and product are untouched.
    run(
        "continuation-lineage-fixed",
        [
            FLUTTER,
            "test",
            "--no-pub",
            "--machine",
            f"--dart-define=C_LINEAGE_OUTPUT={out}/lineage.json",
            "../docs/benchmarks/t66f-phase-b-continuation/lineage_test.dart",
        ],
        ROOT / "mobile",
    )
elif phase == "lint":
    run("last-ruff", [str(ROOT / ".venv/bin/ruff"), "check", "backend", str(HERE)])
    run("last-compileall", [PY, "-m", "compileall", "-q", "backend", str(HERE)])
    run(
        "last-python-format",
        [
            str(ROOT / ".venv/bin/ruff"),
            "format",
            "--check",
            *[str(p) for p in HERE.glob("*.py")],
            "backend/tests/test_isolated_sync_c1_single_encode.py",
            "backend/tests/test_isolated_sync_prefix_reuse.py",
        ],
    )
    run("last-diff-check", ["git", "diff", "--check"])
elif phase == "format":
    # The broad first check also included the archived pre-correction codec
    # oracle. Preserve its original style/bytes, just like canonical/transfer.
    prior = json.loads((HERE / "validation-checks.json").read_text())
    argv = next(
        c["args"] for c in prior["commands"] if c["name"] == "dart-format-final"
    )
    frozen = "docs/benchmarks/t66f-b02-a02-correction/before_fetch.dart"
    assert argv.count(frozen) == 1
    run("changed-dart-format-final", [a for a in argv if a != frozen])
elif phase == "checks":
    run("flutter-analyze-final", [FLUTTER, "analyze", "--no-pub"], ROOT / "mobile")
    run(
        "flutter-build-final",
        [FLUTTER, "build", "apk", "--debug", "--no-pub"],
        ROOT / "mobile",
    )
    run("npm-build-final", ["npm", "run", "build"], ROOT / "frontend")
    run(
        "ruff-final-check",
        [
            str(ROOT / ".venv/bin/ruff"),
            "check",
            "backend",
            "docs/benchmarks/t66f-b02-a02-correction",
        ],
    )
    run(
        "compileall-final-check",
        [
            PY,
            "-m",
            "compileall",
            "-q",
            "backend",
            "docs/benchmarks/t66f-b02-a02-correction",
        ],
    )
    dart_files = subprocess.check_output(
        ["git", "diff", "--name-only"], cwd=ROOT, text=True
    ).splitlines()
    dart_files += subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True
    ).splitlines()
    dart_files = sorted({p for p in dart_files if p.endswith(".dart")})
    run(
        "dart-format-final",
        [DART, "format", "--output=none", "--set-exit-if-changed", *dart_files],
    )
    py_files = [str(p.relative_to(ROOT)) for p in HERE.glob("*.py")]
    py_files += [
        "backend/tests/test_isolated_sync_c1_single_encode.py",
        "backend/tests/test_isolated_sync_prefix_reuse.py",
    ]
    run(
        "new-python-format-final",
        [str(ROOT / ".venv/bin/ruff"), "format", "--check", *py_files],
    )
    run("original-format-deviations", [PY, str(HERE / "format_review.py")])
    run("git-diff-check-final", ["git", "diff", "--check"])
else:
    raise ValueError(phase)

sys.exit(1 if any(row["exit"] for row in rows) else 0)
