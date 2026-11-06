"""B04 유한 순차 실행. 새 N=100k 진입 불가."""
import hashlib,json,os,pathlib,resource,shutil,signal,subprocess,sys,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04';W=pathlib.Path('/tmp/money-note-t66f-b04-20261026');T=W/'tree'
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
for n in map(int,sys.argv[1:]):
 assert n in (1000,5000,10000,50000)
 cohort=f'n{n}-v3';out=E/'raw'/cohort;assert not out.exists()
 identity=subprocess.run([str(R/'.venv/bin/python'),str(E/'provenance.py'),'check'],capture_output=True,text=True);assert identity.returncode==0,identity.stdout+identity.stderr
 assert shutil.disk_usage(W).free>10*1024**3
 competing=subprocess.check_output(['ps','-eo','pid,comm,args'],text=True)
 assert 'flutter_tester' not in competing,'competing Flutter measurement'
 cmd=['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine','--concurrency=1',f'--dart-define=B04_N={n}',f'--dart-define=B04_OUT={out}',f'--dart-define=B04_SCRATCH={W}','../docs/benchmarks/t66f-b04/grid_test.dart']
 log=W/'raw'/f'{cohort}-flutter.jsonl';start=time.time();m={'N':n,'cohort':cohort,'command':cmd,'cwd':str(T/'mobile'),'start_unix':start,'source_digest':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','status':'RUNNING','timeout_seconds':{1000:900,5000:1500,10000:2400,50000:6600}[n],'http_pool':'fresh per publication, both modes','raw_log':str(log),'samples':[]}
 path=E/f'execution-{cohort}.json';assert not path.exists();save(path,m)
 with log.open('xb') as raw:
  p=subprocess.Popen(cmd,cwd=T/'mobile',env={**os.environ,'TMPDIR':str(W/'build'),'PYTHONDONTWRITEBYTECODE':'1'},stdout=raw,stderr=subprocess.STDOUT,start_new_session=True);m['pid']=p.pid
  while p.poll() is None:
   # 자기 process group만 10초마다 관찰한다. 외부 workload를 종료하지 않는다.
   proc=subprocess.check_output(['ps','-eo','pid,pgid,rss'],text=True).splitlines()[1:];rss=sum(int(a[2])*1024 for line in proc if len(a:=line.split())==3 and int(a[1])==p.pid)
   m['samples'].append({'elapsed_s':round(time.time()-start,3),'rss_process_group_bytes':rss,'free_disk_bytes':shutil.disk_usage(W).free});save(path,m)
   if time.time()-start>m['timeout_seconds'] or rss>8*1024**3 or shutil.disk_usage(W).free<10*1024**3:
    m['termination']='bounded task guard';os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=30);break
   time.sleep(10)
  m.update(exit_code=p.returncode,end_unix=time.time(),elapsed_seconds=time.time()-start,status='COMPLETED' if p.returncode==0 else 'ENVIRONMENT_OR_EXECUTION_FAILURE');save(path,m)
 print(json.dumps({k:m[k] for k in ('N','status','elapsed_seconds','exit_code')}),flush=True)
 if p.returncode!=0:break
 keep=subprocess.run([str(R/'.venv/bin/python'),str(E/'retain.py'),cohort],capture_output=True,text=True);save(E/f'retention-{cohort}.json',{'exit':keep.returncode,'stdout':keep.stdout,'stderr':keep.stderr});assert keep.returncode==0,keep.stderr
 # 다음 규모는 완료된 바로 앞 cold의 transfer 진행과3개 독립900초 window 내 타당성으로 사전 판정한다.
 cold=json.loads((out/'cold-0-on.json').read_text());requests=cold['backend']['requests'];observations=[v for v in requests if v['method']=='POST' and v['path'].endswith('/observations')];count=len({v['manifest']['observation_id'] for v in observations})
 save(E/f'feasibility-after-{n}.json',{'completed_N':n,'cold_elapsed_seconds':cold['elapsed_us']/1e6,'observations':count,'expired':cold['observation_expired'],'completed_objects':cold['db_after']['objects'],'next_size_projection_is_diagnostic_only':True,'source':str(out/'cold-0-on.json')})
 if count>=3 and cold['observation_expired']:break
