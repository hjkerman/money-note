import hashlib,io,json,os,re,subprocess,sys,tarfile
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');tree=r/'candidate';history=r/'historical';history.mkdir();repo=Path('/home/hjkerman/codex/money-note')
base='ebcbd54d90eeee194a04b9eea6367f446ee2fd28'
raw=subprocess.check_output(['git','--no-optional-locks','-C',str(repo),'archive',base])
with tarfile.open(fileobj=io.BytesIO(raw)) as tf:tf.extractall(history,filter='data')
original=(tree/'docs/benchmarks/t66f-b03-independent/evidence/direct-experiments.md').read_text();blocks=re.findall(r'```python\n(.*?)```',original,re.S);assert len(blocks)==3
results=[]
for finding,block in zip(['IA05','IA06','IA07'],blocks):
 source=r/'evidence'/('original-'+finding+'.py');source.write_text(block)
 p=subprocess.run([sys.executable,str(source)],cwd=history,capture_output=True,text=True,timeout=180)
 results.append(dict(finding=finding,version='historical baseline',exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
# IA07 current: original single-delegation cursor observer; input/control unchanged.
p=subprocess.run([sys.executable,str(r/'evidence/original-IA07.py')],cwd=tree,capture_output=True,text=True,timeout=180)
results.append(dict(finding='IA07',version='frozen candidate',exit_code=p.returncode,stdout=p.stdout,stderr=p.stderr))
(r/'evidence/direct-controls.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
for result in results:print(json.dumps(result,ensure_ascii=False))
assert all(x['exit_code']==0 for x in results)
