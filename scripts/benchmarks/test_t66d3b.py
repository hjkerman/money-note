"""No listener/configured DB/output overwrite in the D3b diagnostics."""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t66d2b import check_output  # noqa: E402


@pytest.mark.parametrize('path', ['docs/benchmarks/t66d3b/summary.json', '/opt/money-note/synthetic.json', '/var/tmp/diagnostic.json'])
def test_diagnostic_output_requires_new_tmp(path):
    with pytest.raises(ValueError):
        check_output(Path(path))


def test_diagnostic_cannot_overwrite(tmp_path):
    path = tmp_path/'existing.json'
    path.write_text('{}')
    with pytest.raises(ValueError):
        check_output(path)


def test_d3b_normal_startup_isolation():
    root = Path(__file__).resolve().parents[2]
    source = (root/'backend/isolated_sync/http.py').read_text()
    benchmark = (root/'scripts/benchmarks/t66d3b.py').read_text()
    assert 'uvicorn' not in source and 'app.main' not in benchmark
    assert 'ObservationSandbox()' in benchmark
    assert 'resource.setrlimit' in benchmark
