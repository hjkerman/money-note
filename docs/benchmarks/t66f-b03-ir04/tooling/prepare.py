from pathlib import Path
import json,hashlib,os,subprocess,sys
A=Path('/tmp/money-note-ir04-20261024');T=A/'candidate';E=A/'evidence';S=A/'tests';S.mkdir(exist_ok=True)
(T/'.venv').symlink_to('/home/hjkerman/codex/money-note/.venv',target_is_directory=True)
(T/'frontend/node_modules').symlink_to('/home/hjkerman/codex/money-note/frontend/node_modules',target_is_directory=True)
(A/'flutter-tmp').mkdir(exist_ok=True)
R=Path('/home/hjkerman/codex/money-note');records=[]
# The original independent IR03 tools are immutable evidence inputs. Only absolute root, import, output substitutions are permitted.
for name in ['test_ir03_oracles.py','test_ir03_installation.py','test_ir03_tls.py','test_ir03_triggers.py','ir03_oracles_test.dart','integration_original_test.dart','ir03_delta_test.dart']:
 p=R/'docs/benchmarks/t66f-b03-ir03'/name;s=p.read_text();new=s.replace('/tmp/money-note-ir03-20261023/candidate',str(T)).replace('/tmp/money-note-ir03-20261023/evidence',str(S))
 # Python output derives from __file__; keep all new output under private tests.
 target=S/name;target.write_text(new);records.append({'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'adapter':str(target),'adapter_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'changes':'absolute candidate and output/import paths only; test assertions unchanged'})
(E/'original-adapters.json').write_text(json.dumps(records,indent=2))
# Add dependencies only from immutable named baseline evidence when absent in selected payload.
required=['docs/benchmarks/t66f-b03-independent/lineage-goldens.json','docs/benchmarks/t66f-b03-independent/server.py']
for p in required:assert (T/p).is_file(),p
print('prepared',len(records))
