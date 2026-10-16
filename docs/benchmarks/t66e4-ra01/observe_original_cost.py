"""원 assertions/주입 SQL은 유지하고 폐기용 시험 복사본에서 선택된 손상 대상만 관찰한다."""
import importlib.util
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ORIGINAL = HERE.parent / "t66e4-a01-reaudit"


def main(output):
    spec = importlib.util.spec_from_file_location("original_cost_observer", ORIGINAL / "measure.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    source = (ORIGINAL / "cost_test.dart").read_text()
    needle = "        final immutable =\n"
    assert source.count(needle) == 1
    diagnostic = """
        print(jsonEncode({
          'audit': 'frozen_corruption_target', 'history': size,
          'selected_hash': raw['hash'], 'frozen_generation': frozen.generationId,
          'reachable_from_frozen': injection.select(
            'WITH RECURSIVE closure(hash) AS (SELECT hash FROM generation_roots WHERE generation_id=? '
            'UNION SELECT e.child FROM edges e JOIN closure c ON e.parent=c.hash) '
            'SELECT hash FROM closure WHERE hash=?', [frozen.generationId, raw['hash']]).isNotEmpty
        }));
"""
    source = source.replace(needle, diagnostic + needle)
    for name in ["e4_targeted_fixture.dart", "offline_mode_fixtures.dart", "segmented_e2_fixture.dart"]:
        source = source.replace("../../../mobile/test/support/" + name,
                                (ROOT / "mobile/test/support" / name).as_uri())
    with tempfile.TemporaryDirectory(prefix="mn-ra01-observed-cost-") as directory:
        # Runtime diagnostic copy only. Shared product/original audit bytes never change.
        folder = Path(directory)
        (folder / "cost_test.dart").write_text(source)
        runner.HERE = folder
        return runner.main(output)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
