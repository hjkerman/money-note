"""총32 operation 예산의 유일한 campaign. 실제 ASGI 30 + 준비 repository 2."""
import pathlib,subprocess,os,json,time,sys
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';W=pathlib.Path('/tmp/money-note-t66f-b08-20261026');START=time.monotonic();PY=str(R/'.venv/bin/python');env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(W/'disposable'),'PYTHONPATH':str(E)}
workers={};errs={};attempts=[]
def read(p):
 line=p.stdout.readline()
 if not line:raise RuntimeError('worker ended before response')
 return json.loads(line)
def send(v,op,**kw):
 assert len(attempts)<30 and time.monotonic()-START<110
 d={'op':op,**kw,'global_sequence':len(attempts)+3};attempts.append({'variant':v,**d});journal.write(json.dumps(attempts[-1])+'\n');p=workers[v];p.stdin.write(json.dumps(d)+'\n');p.stdin.flush();reply=read(p);assert reply['complete'] and reply['global_sequence']==d['global_sequence']
try:
 # 새 common template은 보존 fixture의 금융 원문과 구조를 그대로 두고 engine별 view만 준비한다.
 with (E/'preparation.stdout').open('x')as out,(E/'preparation.stderr').open('x')as err:
  prep=subprocess.run([PY,str(E/'worker.py'),'prepare','B'],cwd=W,env=env,stdout=out,stderr=err,check=True)
 for v in ['A','B']:
  errs[v]=(E/f'worker-{v}.stderr').open('x');workers[v]=subprocess.Popen([PY,str(E/'worker.py'),'serve',v],cwd=W,env=env,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errs[v],text=True,bufsize=1)
 for v,p in workers.items():assert read(p)['ready']
 journal=(E/'requests.jsonl').open('x',buffering=1)
 send('A','manifest');send('B','manifest')
 for v,block,slots in [('A','A1',range(7)),('B','B1',range(7)),('B','B2',range(6)),('A','A2',range(6))]:
  for slot in slots:send(v,'objects',slot=slot,block=block)
 send('B','release');send('A','release');journal.close()
 for p in workers.values():p.stdin.write('{"op":"finish"}\n');p.stdin.flush()
 for v,p in workers.items():assert read(p)['finished'];assert p.wait(timeout=8)==0;errs[v].close()
 assert len(attempts)==30
 print(json.dumps({'status':'COMPLETED','actual_ASGI_requests':30,'preparatory_repo_operations':2,'conservative_count':32,'inside_wall_s':time.monotonic()-START}),flush=True)
finally:
 for p in workers.values():
  if p.poll()is None:p.kill();p.wait(timeout=2)
