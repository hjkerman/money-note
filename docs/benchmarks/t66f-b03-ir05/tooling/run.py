from pathlib import Path
import json,subprocess,sys,os,time,gzip
A=Path('/tmp/money-note-ir05-20261024');E=A/'evidence';T=A/'candidate';name,mode=sys.argv[1:3];command=sys.argv[3:];cwd=T/'mobile' if mode=='flutter' else T/'backend' if mode=='backend' else T
assert not (E/(name+'.json')).exists() and command
start=time.monotonic();env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',PYTHONPATH=str(T/'backend'),TMPDIR=str(A/'flutter-tmp'),PATH='/home/hjkerman/.flutter/bin:'+os.environ['PATH'],IR05_ROOT=str(A));path=E/(name+'.log.gz')
with gzip.open(path,'wb') as log:
 p=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 last=start
 while b:=p.stdout.read1(65536):
  log.write(b)
  if time.monotonic()-last>=3:log.flush();last=time.monotonic()
 rc=p.wait()
r={'name':name,'command':command,'cwd':str(cwd),'pid':p.pid,'exit_code':rc,'seconds':time.monotonic()-start,'raw':path.name,'candidate_digest':os.environ.get('IR05_TARGET_DIGEST','dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370'),'host_product_digest':'dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370'}
if mode=='flutter' and 'test' in command:
 counts={'PASS':0,'FAIL':0,'SKIP':0};done=None;tests={};failures=[]
 for line in gzip.open(path,'rt'):
  try:v=json.loads(line)
  except ValueError:continue
  if not isinstance(v,dict):continue
  if v.get('type')=='testStart':tests[v['test']['id']]=v['test']['name']
  if v.get('type')=='testDone' and not v.get('hidden'):
   k='SKIP' if v.get('skipped') else 'PASS' if v.get('result')=='success' else 'FAIL';counts[k]+=1
   if k=='FAIL':failures.append(tests.get(v['testID'],v['testID']))
  if v.get('type')=='done':done=v.get('success')
 r.update(counts=counts,done=done,failures=failures)
(E/(name+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n');print(json.dumps(r,ensure_ascii=False),flush=True)
if rc:print(''.join(gzip.open(path,'rt').readlines()[-40:]),flush=True)
raise SystemExit(rc)
