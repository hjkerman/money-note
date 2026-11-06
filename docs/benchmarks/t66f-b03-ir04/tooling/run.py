import os,sys,json,subprocess,time,gzip
from pathlib import Path
A=Path('/tmp/money-note-ir04-20261024');E=A/'evidence';T=A/'candidate'
name=sys.argv[1];mode=sys.argv[2];command=sys.argv[3:];cwd=T/'mobile' if mode=='flutter' else T/'backend' if mode=='backend' else T
assert command and not (E/(name+'.json')).exists(),name
start=time.monotonic();env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',PYTHONPATH=str(T/'backend'),TMPDIR=str(A/'flutter-tmp'),IR04_ROOT=str(A),PATH='/home/hjkerman/.flutter/bin:'+os.environ['PATH'])
log=E/(name+'.log.gz')
with gzip.open(log,'wb') as f:
 p=subprocess.Popen(command,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 while b:=p.stdout.read(65536):f.write(b)
 rc=p.wait()
r={'name':name,'command':command,'cwd':str(cwd),'exit_code':rc,'seconds':time.monotonic()-start,'raw':log.name,'candidate_digest':'27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3'}
if mode=='flutter':
 counts={'PASS':0,'FAIL':0,'SKIP':0};done=None;failures=[];tests={}
 for line in gzip.open(log,'rt'):
  try:v=json.loads(line)
  except ValueError:continue
  if not isinstance(v,dict):continue
  if v.get('type')=='testStart':tests[v['test']['id']]=v['test']['name']
  if v.get('type')=='testDone' and not v.get('hidden'):
   k='SKIP' if v.get('skipped') else 'PASS' if v.get('result')=='success' else 'FAIL';counts[k]+=1
   if k=='FAIL':failures.append(tests.get(v['testID'],v['testID']))
  if v.get('type')=='done':done=v.get('success')
 r.update(counts=counts,done=done,failures=failures)
(E/(name+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False),flush=True)
if rc:print(''.join(gzip.open(log,'rt').readlines()[-45:]),flush=True)
raise SystemExit(rc)
