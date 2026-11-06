import importlib.util
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');spec=importlib.util.spec_from_file_location('ir03_overhead',r/'candidate/docs/benchmarks/t66f-b03-independent/overhead.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.HERE=r;m.main()
