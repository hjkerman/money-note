import hashlib,json,os,subprocess,time
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');tree=r/'candidate';ev=r/'evidence'
# 같은 package의 native-assets를 생성하는 Flutter 도구는 순차 실행한다.
while not (ev/'flutter-full-results.json').exists():time.sleep(5)
while len(json.loads((ev/'flutter-full-results.json').read_text()))<3:time.sleep(5)
commands=[('independent-dart',['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine',str(ev/'ir03_oracles_test.dart')]),('independent-http',['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine',str(ev/'integration_original_test.dart')]),('independent-delta',['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine',str(ev/'ir03_delta_test.dart')]),('authority',['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine','--dart-define=B03_STALE_OUTPUT='+str(ev/'authority'),str(tree/'docs/benchmarks/t66f-b03/authority_test.dart')]),('analyze',['/home/hjkerman/.flutter/bin/flutter','analyze','--no-pub']),('dart-format',['/home/hjkerman/.flutter/bin/dart','format','--output=none','--set-exit-if-changed','test/support/logical_cost_sqlite.dart','test/segmented_logical_cost_ic01_test.dart','test/segmented_logical_cost_p02_test.dart'])]
results=[]
for name,cmd in commands:
 start=time.monotonic();p=ev/(name+'.log')
 with p.open('w') as log:result=subprocess.run(cmd,cwd=tree/'mobile',stdout=log,stderr=subprocess.STDOUT,timeout=1800,env={**os.environ,'TMPDIR':str(r/'flutter-tmp')})
 row=dict(name=name,invocation=cmd,cwd=str(tree/'mobile'),exit_code=result.returncode,seconds=time.monotonic()-start);results.append(row);(ev/'flutter-additional-results.json').write_text(json.dumps(results,indent=2)+'\n')
 if result.returncode:print(name,p.read_text()[-4500:],flush=True)
print(json.dumps([{k:v for k,v in a.items() if k!='invocation'} for a in results]))
