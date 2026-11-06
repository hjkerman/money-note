import json,subprocess,time,os
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');tree=r/'candidate';ev=r/'evidence';d=ev/'flutter-adapters';d.mkdir(exist_ok=True)
src=tree/'mobile/test/segmented_logical_cost_independent_audit_test.dart';text=src.read_text();transforms=[]
for name,historical in [('current',False),('historical',True)]:
 s=text
 for rel,target in [('support/logical_cost_sqlite.dart',tree/('docs/benchmarks/t66f-b03-ic01/historical/logical_cost_sqlite.dart' if historical else 'mobile/test/support/logical_cost_sqlite.dart')),('support/offline_mode_fixtures.dart',tree/'mobile/test/support/offline_mode_fixtures.dart')]:s=s.replace("'"+rel+"'","'"+target.as_uri()+"'")
 output=ev/('flutter-original-'+name);output.mkdir(exist_ok=True)
 s=s.replace("'${Directory.current.parent.path}/docs/benchmarks/t66f-b03-independent/evidence'",repr(str(output)))
 s=s.replace("'${auditOut.parent.path}/lineage-goldens.json'",repr(str(tree/'docs/benchmarks/t66f-b03-independent/lineage-goldens.json')))
 path=d/(name+'_test.dart');path.write_text(s);transforms.append({'source':str(src),'adapter':str(path),'changes':'import/output/golden path only; assertions unchanged'})
(ev/'flutter-adapters.json').write_text(json.dumps(transforms,indent=2))
files=sorted(str(p.relative_to(tree/'mobile')) for p in (tree/'mobile/test').rglob('*_test.dart') if p!=src)
commands=[['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine','--concurrency=4',*files],['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine',str(d/'current_test.dart'),'--name',r'^(?!.*independent SQL defect reproducer).*$'],['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine',str(d/'historical_test.dart'),'--plain-name','independent SQL defect reproducer']]
results=[]
for i,cmd in enumerate(commands):
 start=time.monotonic();path=ev/f'flutter-full-{i}.log'
 with path.open('w') as out:p=subprocess.run(cmd,cwd=tree/'mobile',stdout=out,stderr=subprocess.STDOUT,env={**os.environ,'TMPDIR':str(r/'flutter-tmp')})
 result={'invocation':cmd,'exit_code':p.returncode,'seconds':time.monotonic()-start,'output':str(path)};results.append(result);(ev/'flutter-full-results.json').write_text(json.dumps(results,indent=2))
 if p.returncode:print(path.read_text()[-6000:],flush=True)
print(json.dumps([{k:v for k,v in a.items() if k!='invocation'} for a in results]))
raise SystemExit(int(any(a['exit_code'] for a in results)))
