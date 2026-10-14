"""미커밋 product를 수정하지 않고 새로운 corpus를 독립 대조한다."""

import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
DART = "/home/hjkerman/.flutter/bin/dart"
BASE = "ab59d6bbc39f27c36beb059f984ef527ac7b0bef"
OUTPUT = Path(os.environ.get("E4_P0_AUDIT_OUTPUT", "/tmp/mn-e4-p0-audit/independent"))


@pytest.fixture(scope="session")
def differential(tmp_path_factory):
    temporary = tmp_path_factory.mktemp("e4-p0-independent")
    corpus_path = temporary / "corpus.json"
    generated = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(HERE / "make_corpus.py"),
            str(corpus_path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert generated.returncode == 0, generated.stderr[-3000:]
    corpus = json.loads(corpus_path.read_text())
    old = subprocess.check_output(
        ["git", "show", BASE + ":mobile/lib/src/money.dart"], cwd=ROOT
    )
    assert (ROOT / "mobile/lib/src/money.dart").read_bytes().startswith(old)
    assert (
        ROOT / "mobile/test/fixtures/money_before_e4_p0.dart.txt"
    ).read_bytes() == old
    driver = temporary / "frozen_oracle.dart"
    driver.write_text(
        "import 'dart:io';\nimport 'dart:convert';\n"
        + old.decode()
        + r"""
void main() {
  final values = jsonDecode(File(Platform.environment['AUDIT_VALUES']!).readAsStringSync()) as List;
  stdout.write(jsonEncode(values.map((value) {
    try { exactMoney(value); return true; } on FormatException { return false; }
  }).toList()));
}
"""
    )
    values = temporary / "values.json"
    values.write_text(
        json.dumps([c["value"] for c in corpus["cases"]], ensure_ascii=True)
    )
    original = subprocess.run(
        [DART, str(driver)],
        env={**os.environ, "AUDIT_VALUES": str(values)},
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert original.returncode == 0, original.stderr[-3000:]
    oracle = temporary / "legacy.json"
    oracle.write_text(original.stdout)
    run = subprocess.run(
        [
            DART,
            "--packages=" + str(ROOT / "mobile/.dart_tool/package_config.json"),
            str(HERE / "differential.dart"),
            str(corpus_path),
            str(oracle),
            str(ROOT / "mobile/test/fixtures/segmented_server_golden.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert run.returncode == 0, run.stderr[-4000:]
    result = json.loads(run.stdout)
    result.update(
        seed=corpus["seed"],
        unicode_version=corpus["unicode_version"],
        python_whitespace=corpus["python_whitespace"],
        tested_characters=corpus["tested_characters"],
        all_unicode_format_characters=corpus["all_unicode_format_characters"],
        corpus_sha256=hashlib.sha256(corpus_path.read_bytes()).hexdigest(),
        frozen_source_sha256=hashlib.sha256(old).hexdigest(),
    )
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "differential.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    return result


def test_independent_backend_authoritative_and_e1_admission(differential):
    assert differential["cases"] > 4755
    assert differential["accepted"] > 0 and differential["rejected"] > 0
    assert not differential["mismatches"]["authoritative"]
    assert not differential["mismatches"]["e1"]


def test_pre_correction_input_oracle_and_journal_admission(differential):
    assert not differential["mismatches"]["frozen"]
    assert not differential["mismatches"]["non_setting"]


def test_raw_c1_and_hashes_against_python_server_bytes(differential):
    assert not differential["mismatches"]["raw"]
    assert not differential["mismatches"]["c1_hash"]


def test_original_five_diagnostics_and_frozen_source_are_intact():
    for line in (
        (ROOT / "docs/benchmarks/t66e4-p0/preserved-history.sha256")
        .read_text()
        .splitlines()
    ):
        expected, path = line.split(maxsplit=1)
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    old = subprocess.check_output(
        ["git", "show", BASE + ":mobile/lib/src/money.dart"], cwd=ROOT
    )
    assert (ROOT / "mobile/lib/src/money.dart").read_bytes().startswith(old)


def test_original_pre_p0_readers_and_corrected_real_wire(tmp_path):
    probe = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / "docs/benchmarks/t66e4-contract/probe.py"),
        ],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=120,
    )
    assert probe.returncode == 0, probe.stderr[-3000:]
    evidence = tmp_path / "actual-wire.json"
    evidence.write_text(probe.stdout)
    decoded = json.loads(probe.stdout)
    original = "\x1c+0001000.00\x1f"
    vector = next(v for v in decoded["vectors"] if v["value"] == original)
    assert vector["segmented"] and vector["legacy_server"]
    mobile = tmp_path / "baseline/mobile"
    shutil.copytree(ROOT / "mobile/lib", mobile / "lib")
    modified = subprocess.check_output(
        ["git", "diff", "--name-only", BASE, "--", "mobile/lib"], cwd=ROOT, text=True
    ).splitlines()
    for path in modified:
        assert path.startswith("mobile/lib/")
        (tmp_path / "baseline" / path).write_bytes(
            subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)
        )
    current = ROOT / "mobile/.dart_tool/package_config.json"
    config = json.loads(current.read_text())
    for package in config["packages"]:
        if ":" not in package["rootUri"]:
            package["rootUri"] = (
                current.parent / package["rootUri"]
            ).resolve().as_uri() + "/"
        if package["name"] == "money_note_mobile":
            package["rootUri"] = mobile.as_uri() + "/"
    old_config = mobile / ".dart_tool/package_config.json"
    old_config.parent.mkdir()
    old_config.write_text(json.dumps(config))
    results = {}
    for label, location in [("before", old_config), ("after", current)]:
        run = subprocess.run(
            [
                DART,
                "--packages=" + str(location),
                str(HERE / "legacy_read.dart"),
                str(evidence),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert run.returncode == 0, run.stderr[-3000:]
        results[label] = json.loads(run.stdout)
        assert results[label]["legacy_input"] is False
        assert results[label]["wire_unchanged"]
        assert results[label]["source_codepoints"] == list(map(ord, original))
    assert (
        results["before"]["bundle"] is False and results["before"]["baseline"] is False
    )
    assert results["after"]["bundle"] and results["after"]["baseline"]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "original-replay.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n"
    )
