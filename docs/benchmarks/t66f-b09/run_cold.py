"""유한 real Flutter 실행. 기존 run path가 있으면 재시작하지 않음; outer watchdog."""
import datetime,json,os,pathlib,signal,subprocess,sys,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=pathlib.Path('/tmp/money-note-t66f-b09-20261026');N=int(sys.argv[1]);assert N in (1000,5000)
plan=E/f'plan-n{N}.json';runs=json.loads(plan.read_text())['runs'];assert len(runs)==(4 if N==1000 else 2)
if N==5000:assert json.loads((E/'escalation-decision.json').read_text())['gate_open'] is True
for r in runs:assert not pathlib.Path(r['out']).exists()
log=E/f'cold-n{N}.jsonl';err=E/f'cold-n{N}.stderr';assert not log.exists() and not err.exists()
cmd=['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--reporter=json','--dart-define=B05A_PLAN='+str(plan),'../docs/benchmarks/t66f-b09/cold_test.dart']
start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();timed_out=False
with log.open('x') as out,err.open('x') as errors:
 p=subprocess.Popen(cmd,cwd=W/'candidate/mobile',env={**os.environ,'TMPDIR':str(W/'disposable')},stdout=out,stderr=errors,start_new_session=True)
 try:code=p.wait(timeout=1200)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(p.pid,signal.SIGTERM)
  try:code=p.wait(timeout=20)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);code=p.wait()
d={'N':N,'command':cmd,'cwd':str(W/'candidate/mobile'),'start_utc':utc,'end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'wall_s':time.monotonic()-start,'exit_code':code,'outer_deadline_s':1200,'timeout':timed_out,'retry':False,'planned_full_cold_runs':len(runs),'started_full_cold_runs':sum(pathlib.Path(r['out']).exists()for r in runs)}
(E/f'cold-execution-n{N}.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d));raise SystemExit(code)
