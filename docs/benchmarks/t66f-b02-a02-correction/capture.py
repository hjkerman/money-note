"""한정 실행과 pending exact-artifact review. 제품 artifact/guard는 쓰지 않는다."""

import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync.artifacts import release_bundle  # noqa: E402


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    old = json.loads(
        (ROOT / "docs/specimens/t66d3b-release-artifacts.json").read_bytes()
    )
    new = release_bundle()

    def engine(b):
        return json.loads(
            base64.b64decode(b["artifacts"]["financial_engine"]["data_base64"])
        )

    a, b = engine(old), engine(new)
    changes = {
        k: {"before": a["sources"].get(k), "after": b["sources"].get(k)}
        for k in a["sources"].keys() | b["sources"].keys()
        if a["sources"].get(k) != b["sources"].get(k)
    }
    assert set(changes) == {"isolated_sync/canonical.py"}
    assert old["versions"] == new["versions"]
    assert a["profile"] == b["profile"]
    for k in ("raw_schema", "projection_schema", "policy_registry"):
        assert old["artifacts"][k] == new["artifacts"][k]
    artifact = dict(
        status="APPROVAL PENDING — artifacts/allow-list NOT modified",
        previous_engine=old["artifacts"]["financial_engine"]["sha256"],
        proposed_engine=new["artifacts"]["financial_engine"]["sha256"],
        historical_engine="f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d",
        changed_sources=changes,
        unchanged=[
            "versions",
            "raw_schema",
            "projection_schema",
            "policy_registry",
            "engine profile",
        ],
    )
    (HERE / "artifact-review-pending.json").write_text(
        json.dumps(artifact, indent=2) + "\n"
    )
    source = (ROOT / "mobile/lib/src/segmented/fetch.dart").read_text()
    restored = re.sub(
        r"\n    // A02 cold continuation: begin\.[\s\S]*?    // A02 cold continuation: end\.\n",
        "\n",
        source,
    )
    restored = re.sub(
        r"\n  // A02 active-call helper: begin\.[\s\S]*?  // A02 active-call helper: end\.\n",
        "",
        restored,
    )
    restored = re.sub(r"\nclass _ColdTargetChanged[\s\S]*?\n}\n", "", restored)
    restored = restored.split("\ntypedef _FrontierPath")[0]
    restored = re.sub(
        r"\n      : _largeGraphVerification = false;[\s\S]*?  final bool _largeGraphVerification;",
        ";",
        restored,
        count=1,
    )
    restored = restored.replace(
        "(_largeGraphVerification ? 500000 : 100000)", "100000", 1
    ).replace("(_largeGraphVerification ? 1000000 : 200000)", "200000", 1)
    restored = re.sub(
        r"          final frontier = limits\._largeGraphVerification[\s\S]*?              : null;\n",
        "",
        restored,
        count=1,
    )
    restored = restored.replace(
        "            if (frontier != null) return frontier.load(edge, path);\n", "", 1
    ).replace("          frontier?.finish();\n", "", 1)
    expected = json.loads(
        (ROOT / "docs/benchmarks/t66e4-p0-audit/protected-source.json").read_text()
    )["mobile/lib/src/segmented/fetch.dart"]["sha256"]
    review = dict(
        actual_default_sha256=sha(restored.encode()),
        expected_default_sha256=expected,
        exact_default_restored=sha(restored.encode()) == expected,
        extension_sha256=sha(source.encode()),
        note="교정 범위 검토용; 기존 historical source-lock artifact는 변경하지 않음; 신규 behavior/guard gate는 미완료",
    )
    (HERE / "default-source-review.json").write_text(
        json.dumps(review, indent=2) + "\n"
    )
    rows = json.loads((HERE / "codec-benchmark.json").read_text())["rows"]
    cost = {}
    for shape in ("shared", "spread"):
        cost[shape] = {}
        for mode in ("before", "after"):
            subset = [r for r in rows if r["shape"] == shape and r["mode"] == mode]
            cost[shape][mode] = dict(
                median_seconds=statistics.median(r["seconds"] for r in subset),
                encode_calls=subset[0]["encode_calls"],
                encoded_output_bytes=subset[0]["encoded_output_bytes"],
                sql=subset[0]["sql"],
                exact_response_sha256=subset[0]["response_sha256"],
            )
    for name in (
        "codec-tests",
        "backend-targeted",
        "canonical-regression",
        "codec-bench",
        "b01-strict",
        "flutter-control.jsonl",
        "flutter-control.err",
        "analyze",
        "static",
        "npm-build",
        "compileall",
    ):
        path = Path("/tmp") / (
            f"mn-a02-{name}"
            if name.endswith((".jsonl", ".err"))
            else f"mn-a02-{name}.log"
        )
        if path.exists():
            (HERE / (name + ".gz")).write_bytes(
                gzip.compress(path.read_bytes(), mtime=0)
            )
    summary = dict(
        classification="INCOMPLETE — exact artifact approval/Flutter runtime gates pending",
        backend_new_c1_tests=25,
        nested_differential_cases=10000,
        backend_new_plus_prefix=53,
        existing_canonical=34,
        strict_b01=1,
        targeted_backend_unique_tests=88,
        flutter_control=dict(
            passed=0,
            failed=1,
            reason="UNSUPPORTED_CONTRACT — new exact engine not approved, before E2 acquisition",
        ),
        cost=cost,
        full_suites_rerun=False,
        real_50k_rerun=False,
        real_100k_rerun=False,
        source_lock_modified=False,
        artifact_modified=False,
        static_checks={
            "changed_dart_analyze": "PASS",
            "ruff": "PASS",
            "compileall": "PASS",
            "npm_build": "PASS",
            "changed_file_format": "PASS",
            "git_diff_check": "PASS",
        },
        commit=None,
        push=False,
    )
    (HERE / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                default_restored=review["exact_default_restored"],
                cost=cost,
                artifact=artifact,
            )
        )
    )


if __name__ == "__main__":
    main()
