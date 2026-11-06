from pathlib import Path
import json,hashlib
A=Path('/tmp/money-note-ir05-20261024');T=A/'candidate';S=A/'tests';E=A/'evidence'
assert json.loads((E/'reconstruction.json').read_text())['PASS']
(T/'.venv').symlink_to('/home/hjkerman/codex/money-note/.venv',target_is_directory=True);(T/'frontend/node_modules').symlink_to('/home/hjkerman/codex/money-note/frontend/node_modules',target_is_directory=True);(A/'flutter-tmp').mkdir()
names=['test_ir03_oracles.py','test_ir03_installation.py','test_ir03_tls.py','test_ir03_triggers.py','test_ir04_installation.py','test_ir04_rollover_native.py','test_ir04_schema.py','ir03_oracles_test.dart','ir04_schema_test.dart','integration_original_test.dart','ir03_delta_test.dart','original_IA05.py','original_IA06.py','original_IA07.py'];records=[]
for name in names:
 source=T/'docs/benchmarks/t66f-b03-ir04/tests'/name;body=source.read_text();changes=[]
 for old,new in [('/tmp/money-note-ir04-20261024',str(A)),('/tmp/money-note-ir03-20261023/candidate',str(T)),('/tmp/money-note-ir03-20261023/evidence',str(S))]:
  n=body.count(old)
  if n:body=body.replace(old,new);changes.append({'old':old,'new':new,'occurrences':n})
 target=S/name;target.write_text(body);records.append({'source':str(source.relative_to(T)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'adapter':str(target),'adapter_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'path_substitutions':changes,'assertions_unchanged':True})
(E/'original-adapters.json').write_text(json.dumps(records,indent=2));print('original independent adapters',len(records))
