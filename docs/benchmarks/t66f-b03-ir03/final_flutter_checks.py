import json,os,subprocess,time
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');tree=r/'candidate';ev=r/'evidence'
while not (ev/'flutter-additional-results.json').exists():time.sleep(5)
while len(json.loads((ev/'flutter-additional-results.json').read_text()))<6:time.sleep(5)
commands=[('overhead-dart',['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine',str(ev/'overhead_reference_test.dart')]),('debug-apk',['/home/hjkerman/.flutter/bin/flutter','build','apk','--debug','--no-pub','--dart-define=MONEY_NOTE_API_BASE_URL=https://audit.invalid'])]
results=[]
for name,cmd in commands:
 start=time.monotonic();p=ev/(name+'.log');code=None;reason=None
 try:
  with p.open('w') as log:proc=subprocess.run(cmd,cwd=tree/'mobile',stdout=log,stderr=subprocess.STDOUT,timeout=900,env={**os.environ,'TMPDIR':str(r/'flutter-tmp'),'ANDROID_HOME':'/home/hjkerman/.android-sdk'})
  code=proc.returncode
 except subprocess.TimeoutExpired:reason='900초 실행 한도'
 row=dict(name=name,invocation=cmd,cwd=str(tree/'mobile'),exit_code=code,termination=reason,seconds=time.monotonic()-start);results.append(row);(ev/'flutter-final-results.json').write_text(json.dumps(results,indent=2)+'\n')
 if code:print(name,p.read_text()[-4500:],flush=True)
print(json.dumps(results))
