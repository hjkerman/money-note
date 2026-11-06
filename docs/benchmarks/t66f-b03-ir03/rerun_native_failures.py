import json,os,subprocess,time
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');ev=r/'evidence'
while not (ev/'flutter-final-results.json').exists():time.sleep(3)
while len(json.loads((ev/'flutter-final-results.json').read_text()))<2:time.sleep(3)
cmd=['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine','--concurrency=2','test/segmented_adapter_crash_test.dart','test/segmented_cold_continuation_crash_test.dart'];started=time.monotonic()
with (ev/'flutter-native-rerun.log').open('w') as log:p=subprocess.run(cmd,cwd=r/'candidate/mobile',stdout=log,stderr=subprocess.STDOUT,timeout=900,env={**os.environ,'TMPDIR':str(r/'flutter-tmp')})
record=dict(invocation=cmd,cwd=str(r/'candidate/mobile'),exit_code=p.returncode,seconds=time.monotonic()-started,reason='최초 native asset 생성 전 실패한 두 파일의 8개 case. dart run으로 생성된 runtime asset 준비 후 source/assertion 변경 없이 재검증.')
(ev/'flutter-native-rerun.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
if p.returncode:print((ev/'flutter-native-rerun.log').read_text()[-5000:])
print(json.dumps(record,ensure_ascii=False))
