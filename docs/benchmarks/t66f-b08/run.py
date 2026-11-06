"""합산 120초를 보장하는 외부 fail-stop watchdog; 재시도 없음."""
import pathlib,subprocess,os,time,signal,json,sys
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';W=pathlib.Path('/tmp/money-note-t66f-b08-20261026')
def save(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def bounded(cmd,seconds,out,err):
 t=time.monotonic();p=subprocess.Popen(cmd,cwd=W,stdout=out,stderr=err,start_new_session=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});expired=False
 try:
  try:rc=p.wait(timeout=max(.001,seconds-(time.monotonic()-t)))
  except subprocess.TimeoutExpired:expired=True;os.killpg(p.pid,signal.SIGKILL);rc=p.wait(timeout=.75)
 finally:
  if p.poll()is None:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=.75)
 return {'pid':p.pid,'returncode':rc,'watchdog_fired':expired,'wall_s':time.monotonic()-t,'hard_deadline_s':seconds}
if len(sys.argv)>1 and sys.argv[1]=='selftest':
 with open(os.devnull,'w')as f:d=bounded([str(R/'.venv/bin/python'),'-c','import time; time.sleep(2)'],.1,f,f)
 assert d['watchdog_fired'] and d['returncode']==-9 and d['wall_s']<1;save('watchdog-selftest.json',d);print(json.dumps({'watchdog':'PASS','D3_requests':0}));sys.exit(0)
assert not(E/'execution-budget.json').exists()and not(E/'requests.jsonl').exists()and(E/'watchdog-selftest.json').exists()
save('measurement-plan.json',{'baseline':'original B03 7ad','candidate':'B08 only expected compilation reuse','original_fixture':'preserved N1k aba6a044...','derived_common_template':'same original raw and same fixed control export timestamp; both engine views; prepared in watchdog scope','actual_ASGI_requests':30,'preparatory_repo_operations':2,'combined_budget_count':32,'budget_s':120,'hard_watchdog_s':119,'order':'A manifest, B manifest, A1 slots0..6, B1 slots0..6, B2 slots0..5, A2 slots0..5, B release, A release','matched_object_requests_per_engine':13,'calibration':'64 pure parser pairs per engine, no D3 requests, inside watchdog','instrumentation':'same B03 ON and lightweight B08 wrappers for paired ASGI; preparation separate OFF','retries':0,'no_full_cold':True})
with(E/'execution.stdout').open('x')as out,(E/'execution.stderr').open('x')as err:d=bounded([str(R/'.venv/bin/python'),str(E/'coordinator.py')],119,out,err)
count=lambda n:len((E/n).read_text().splitlines())if(E/n).exists() else 0
d.update(actual_ASGI_attempts=count('requests.jsonl'),preparatory_repo_attempts=count('preparation-attempts.jsonl'),closed_ASGI_records=count('packets-A.jsonl')+count('packets-B.jsonl'),retries=0);d['conservative_count']=d['actual_ASGI_attempts']+d['preparatory_repo_attempts'];d['within_limits']=d['wall_s']<120 and d['conservative_count']<=32;save('execution-budget.json',d);print(json.dumps(d))
if d['returncode']!=0:
 for n in ['execution.stderr','preparation.stderr','worker-A.stderr','worker-B.stderr']:
  if(E/n).exists():print(n+'\n'+'\n'.join((E/n).read_text().splitlines()[-14:]))
 sys.exit(1)
assert d['within_limits'] and not d['watchdog_fired']
