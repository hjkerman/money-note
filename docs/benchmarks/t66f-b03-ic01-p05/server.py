"""기존 실제 TLS benchmark의 명시적인 artifact 보존 진입점.

python server.py 1000 <새 wire-evidence 디렉터리> <새 artifact 디렉터리>
stdout의 private credential pipe를 로그에 저장하지 않는다.
"""

import importlib.util
from pathlib import Path
import sys

if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location(
        "original_b02_test_server",
        Path(__file__).resolve().parent.parent / "t66f-b02-implementation/server.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main(artifact_destination=Path(sys.argv[3]))
