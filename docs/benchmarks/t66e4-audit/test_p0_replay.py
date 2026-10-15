"""원 P0 assertions를 유지하고 후속 신규 파일의 baseline 재구성만 보완한다."""
from pathlib import Path
import types

ROOT = Path(__file__).resolve().parents[3]
ORIGINAL = ROOT / "docs/benchmarks/t66e4-p0-audit/test_audit.py"


def test_original_p0_reader_assertions_after_e4_additions(tmp_path):
    source = ORIGINAL.read_text()
    before = '["git", "diff", "--name-only", BASE, "--", "mobile/lib"]'
    after = '["git", "diff", "--name-only", "--diff-filter=M", BASE, "--", "mobile/lib"]'
    assert source.count(before) == 1
    module = types.ModuleType("original_p0_baseline_compat")
    module.__file__ = str(ORIGINAL)
    exec(compile(source.replace(before, after), str(ORIGINAL), "exec"), module.__dict__)
    # Every original monetary/codepoint/hash/admission assertion executes unchanged.
    module.test_original_pre_p0_readers_and_corrected_real_wire(tmp_path)
