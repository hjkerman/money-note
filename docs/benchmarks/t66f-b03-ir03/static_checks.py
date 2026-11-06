import json,os,subprocess,time,hashlib
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');tree=r/'candidate';out=r/'evidence';python=tree/'.venv/bin/python';ruff=tree/'.venv/bin/ruff'
commands=[('ruff',tree,[str(ruff),'check','backend/app','backend/isolated_sync','backend/tests','scripts','docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b03/server.py']),('compileall',tree,[str(python),'-m','compileall','-q','backend/app','backend/isolated_sync','backend/tests','scripts']),('python-format',tree,[str(ruff),'format','--check','docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b03/server.py','docs/benchmarks/t66f-b02-implementation/server.py']),('frontend-build',tree/'frontend',['npm','run','build'])]
(tree/'frontend/node_modules').symlink_to('/home/hjkerman/codex/money-note/frontend/node_modules',target_is_directory=True)
results=[]
for name,cwd,cmd in commands:
 started=time.monotonic();p=out/(name+'.log')
 with p.open('w') as log:result=subprocess.run(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=900)
 row=dict(name=name,invocation=cmd,cwd=str(cwd),exit_code=result.returncode,seconds=time.monotonic()-started);results.append(row)
 if result.returncode:print(name,p.read_text()[-4000:])
(out/'static-checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results))
