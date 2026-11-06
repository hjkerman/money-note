"""동결 source 안의 기존 보호 기대 SHA를 변경 없이 대조한다."""
import hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[3]
d=json.loads((R/'docs/benchmarks/t66f-b03-ic05/evidence/protected-source-check.json').read_text())
for p,h in {**d['six_exact_protected_sources'],'mobile/test/support/logical_cost_sqlite.dart':d['Dart_helper_sha256']}.items():
 assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,p
print('보호 source 7개 SHA PASS')
