"""명령·소스 SHA·종료 상태·압축 원문을 IC06 증거에만 기록한다."""
import gzip, hashlib, json, os, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[3]; O=Path(__file__).parent/'evidence'; S=R/'work/t66f-b03-ic06'
def hashes():
 paths=['docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b03/server.py','mobile/test/support/logical_cost_sqlite.dart','backend/tests/test_logical_cost_ic04.py','backend/tests/test_logical_cost_ic05.py','backend/tests/test_logical_cost_ic06.py']
 return {p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in paths if (R/p).exists()}
def run(label,cmd,cwd=None,extra=None):
 record=O/(label+'.json'); log=O/(label+'.log.gz'); assert not record.exists() and not log.exists(),label
 before=hashes(); start=time.monotonic();env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(R/'backend'),'IR06_TREE':str(R),'IC06_SCRATCH':str(S),**(extra or {})}
 with gzip.open(log,'wb') as f:
  p=subprocess.Popen(cmd,cwd=cwd or R,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  with p.stdout:
   while chunk:=p.stdout.read1(65536):f.write(chunk)
  p.wait()
 d=dict(label=label,command=cmd,cwd=str(cwd or R),environment={k:env[k] for k in ['PYTHONPATH','IR06_TREE','IC06_SCRATCH','PYTHONDONTWRITEBYTECODE']},exit_code=p.returncode,seconds=time.monotonic()-start,raw=log.name,source_before=before,source_after=hashes());d['source_unchanged']=d['source_before']==d['source_after']
 for a in cmd:
  if a.startswith('--junitxml=') and Path(a.split('=',1)[1]).exists():
   cases=ET.parse(a.split('=',1)[1]).findall('.//testcase'); d['junit_counts']={k:sum(pred(c) for c in cases) for k,pred in [('PASS',lambda c:not any(c.find(x) is not None for x in ['failure','error','skipped'])),('FAIL',lambda c:any(c.find(x) is not None for x in ['failure','error'])),('SKIP',lambda c:c.find('skipped') is not None)]}
 if '--machine' in cmd:
  counts=dict(PASS=0,FAIL=0,SKIP=0)
  for line in gzip.open(log,'rt'):
   try:e=json.loads(line)
   except ValueError:continue
   if isinstance(e,dict) and e.get('type')=='testDone' and not e.get('hidden'):counts['SKIP' if e.get('skipped') else 'PASS' if e.get('result')=='success' else 'FAIL']+=1
   if isinstance(e,dict) and e.get('type')=='done':d['done']=e.get('success')
  d['flutter_counts']=counts
 record.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:d.get(k) for k in ['label','exit_code','seconds','junit_counts','flutter_counts','done','source_unchanged']}),flush=True)
 if p.returncode:print(''.join(gzip.open(log,'rt').readlines()[-12:]),flush=True)
 return p.returncode
if __name__=='__main__':
 args=sys.argv[1:];label=args.pop(0);cwd=None
 if args[:1]==['--cwd']:args.pop(0);cwd=args.pop(0)
 if args[:1]==['--']:args.pop(0)
 raise SystemExit(run(label,args,cwd))
