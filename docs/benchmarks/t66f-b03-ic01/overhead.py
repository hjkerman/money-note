"""원 독립 paired oracle를 현재 source에 재실행하고 출력만 IC01에 분리."""

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "ic01_original_overhead", HERE.parent / "t66f-b03-independent/overhead.py"
)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
subject.HERE = HERE / "sealed-overhead" if "--sealed" in sys.argv else HERE
(subject.HERE / "evidence").mkdir(parents=True, exist_ok=True)
subject.main()
