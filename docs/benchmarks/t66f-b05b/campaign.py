"""사전 고정된 N5k ON A→B 한 쌍. 실패·불리한 결과에 재시도하지 않는다."""
import hashlib,json,os,pathlib,shutil,signal,stat,subprocess,tarfile,time
from prepare import R,E,W,H,sha,save

def check_sources(name):
 records={}
 for variant,T,archive in [('A',W/'baseline',pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz')),('B',W/'candidate',pathlib.Path(json.loads((H/'freeze.json').read_text())['archive']))]:
  with tarfile.open(archive) as t:m=json.loads(t.extractfile('metadata/source-manifest.json').read())
  differences=[]
  for a in m['entries']:
   p=T/a['path']
   if not p.is_file() or sha(p.read_bytes())!=a['sha256'] or stat.S_IMODE(p.stat().st_mode)!=int(a['mode'],8):differences.append(a['path'])
  assert not differences,differences
  records[variant]={'files':len(m['entries']),'differences':differences,'payload_entries_SHA':sha(json.dumps(m['entries'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())}
 save(E/name,records);return records
if __name__=='__main__':
 assert not (E/'execution.json').exists();check_sources('source-before-measurement.json')
 plan=json.loads((E/'plan.json').read_text());assert [(x['variant'],x['N'],x['on']) for x in plan['runs']]==[('A',5000,True),('B',5000,True)]
 ps=subprocess.check_output(['ps','-eo','pid,ppid,pcpu,rss,comm,args'],text=True);assert not any(s.split()[4] in ['flutter_tester','dartvm','dartaotruntime'] for s in ps.splitlines()[1:] if len(s.split())>=5);assert shutil.disk_usage(W).free>10*1024**3
 cmd=['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine','--concurrency=1',f'--dart-define=B05A_PLAN={E}/plan.json','../docs/benchmarks/t66f-b05a/cold_test.dart']
 rec={'command':cmd,'cwd':str(W/'candidate/mobile'),'start_unix':time.time(),'start_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'status':'RUNNING','timeout_seconds':1200,'rss_guard_bytes':8*1024**3,'disk_guard_bytes':10*1024**3,'max_planned_full_cold_runs':2,'order':['A','B'],'pre_run_processes':ps,'samples':[],'source_unchanged_after_unfavorable_result':True}
 with (W/'raw/cold.jsonl').open('xb') as out,(W/'raw/cold.stderr').open('xb') as err:
  p=subprocess.Popen(cmd,cwd=W/'candidate/mobile',env={**os.environ,'TMPDIR':str(W/'disposable'),'PYTHONDONTWRITEBYTECODE':'1'},stdout=out,stderr=err,start_new_session=True);rec['pid']=p.pid;save(E/'execution.json',rec)
  while p.poll() is None:
   proc=subprocess.check_output(['ps','-eo','pid,pgid,rss,comm'],text=True).splitlines()[1:];rss=sum(int(a[2])*1024 for line in proc if len(a:=line.split())==4 and int(a[1])==p.pid);elapsed=time.time()-rec['start_unix'];free=shutil.disk_usage(W).free
   rec['samples'].append({'elapsed_s':elapsed,'rss_process_group_bytes':rss,'free_disk_bytes':free,'load_average':os.getloadavg()});save(E/'execution.json',rec)
   if elapsed>1200 or rss>8*1024**3 or free<10*1024**3:
    rec['termination']='bounded task guard';os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=30);break
   time.sleep(10)
  rec.update(exit_code=p.returncode,end_unix=time.time(),end_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),elapsed_seconds=time.time()-rec['start_unix'],status='COMPLETED' if p.returncode==0 else 'INCOMPLETE');save(E/'execution.json',rec)
 check_sources('source-after-measurement.json');print(json.dumps({k:rec[k] for k in ['status','exit_code','elapsed_seconds','order']}))
