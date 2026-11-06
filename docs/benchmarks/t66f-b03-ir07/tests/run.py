"""IR07 실행 ledger: 매 배치 동결 payload 파일 identity와 명령/원문을 보존."""
import gzip, hashlib, json, os, pathlib, subprocess, sys, time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b03-ir07';W=pathlib.Path('/tmp/money-note-t66f-b03-ir07-20261025');T=W/'tree';S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
sha=lambda b:hashlib.sha256(b).hexdigest()
def check():
 m=json.loads((S/'source-manifest.json').read_bytes())
 for e in m['entries']:
  p=T/e['path'];assert sha(p.read_bytes())==e['sha256'] and p.stat().st_mode&0o777==int(e['mode'],8),p
 return m['candidate_source_digest_sha256']
label=sys.argv[1];cwd=T
if sys.argv[2:3]==['--cwd']:cwd=T/sys.argv[3];del sys.argv[2:4]
cmd=sys.argv[2:];assert not (E/(label+'.json')).exists(),label
payload=check();env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(T/'backend'),'IR06_TREE':str(T),'IR06_EVIDENCE':str(W/'ir06-evidence'),'IC06_SCRATCH':str(W),'IR07_TREE':str(T),'IR07_EVIDENCE':str(E),'GIT_OPTIONAL_LOCKS':'0'}
t0=time.monotonic();out=E/(label+'.log.gz')
with gzip.open(out,'wb') as log:
 p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
 while b:=p.stdout.read1(65536):log.write(b)
 code=p.wait()
rec=dict(label=label,command=cmd,cwd=str(cwd),payload_sha256=payload,source_verified_before=True,source_verified_after=check()==payload,exit_code=code,seconds=time.monotonic()-t0,raw=out.name,raw_sha256=sha(out.read_bytes()))
(E/(label+'.json')).write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n');print(json.dumps(rec,ensure_ascii=False))
if code:print(''.join(gzip.open(out,'rt').readlines()[-40:]))
sys.exit(code)
