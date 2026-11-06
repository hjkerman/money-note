"""단일 실행 parent watchdog. 119초에 B07 자식 process group을 SIGKILL한다."""
import os,pathlib,sys,subprocess,time,signal,json,hashlib
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b07';W=pathlib.Path('/tmp/money-note-t66f-b07-20261026')
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def wait_bounded(command,deadline,stdout,stderr,env):
 start=time.monotonic();p=subprocess.Popen(command,cwd=W/'baseline',env=env,stdout=stdout,stderr=stderr,start_new_session=True);expired=False
 try:
  try:rc=p.wait(timeout=max(.001,deadline-(time.monotonic()-start)))
  except subprocess.TimeoutExpired:
   expired=True;os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=.75)
 finally:
  if p.poll() is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=.75)
 return {'pid':p.pid,'returncode':rc,'watchdog_fired':expired,'wall_s':time.monotonic()-start,'deadline_s':deadline,'group_owned':True}
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='selftest':
  with open(os.devnull,'w') as f:d=wait_bounded([str(R/'.venv/bin/python'),'-c','import time; time.sleep(2)'],.1,f,f,os.environ.copy())
  assert d['watchdog_fired'] and d['returncode']==-signal.SIGKILL and d['wall_s']<1
  save(E/'watchdog-selftest.json',d);print(json.dumps({'watchdog':'PASS','D3_packets':0,'wall_s':d['wall_s']}));sys.exit(0)
 assert (E/'watchdog-selftest.json').exists() and not (E/'execution-budget.json').exists() and not (E/'packets.jsonl').exists()
 scratch=W/'disposable';scratch.mkdir()
 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(scratch),'PYTHONPATH':str(E)}
 plan={'source':'original B03 only','payload':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','engine':'7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c','N':1000,'planned_total_packets':30,'max_total_packets':32,'budget_s':120,'parent_hard_watchdog_s':119,'child_no_new_request_after_s':110,'all_attempts_counted':True,'outer_includes':'child startup/import/setup/all requests/shutdown/backup; no retry','sequence':['manifest probe','control1 7 object packets','probe1 7 object packets','probe2 7 object packets','control2 7 object packets','release probe'],'B03_instrumentation':'ON all packets','control':'same wrapper dispatch; detailed ns timers off','transport':'Starlette TestClient in-process ASGI; full real D3 route/workers, no socket/network timing','new_full_cold':0}
 save(E/'plan.json',plan)
 with (E/'execution.stdout').open('x') as out,(E/'execution.stderr').open('x') as err:d=wait_bounded([str(R/'.venv/bin/python'),str(E/'experiment.py')],119,out,err,env)
 d.update(attempted_packets=len((E/'requests.jsonl').read_text().splitlines()) if (E/'requests.jsonl').exists() else 0,closed_packet_records=len((E/'packets.jsonl').read_text().splitlines()) if (E/'packets.jsonl').exists() else 0,retries=0)
 d['within_limits']=d['wall_s']<=120 and d['attempted_packets']<=32
 save(E/'execution-budget.json',d);print(json.dumps(d))
 if d['returncode']!=0:
  print('\n'.join((E/'execution.stderr').read_text().splitlines()[-22:]));sys.exit(1)
 assert d['within_limits'] and not d['watchdog_fired']
