"""사전 visible 파일, Git index 및 historical archive bytes를 그대로 대조한다."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,time
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';before=json.loads((E/'preservation-before.json').read_text());sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
changed=[]
for p,v in before['files'].items():
 q=R/p
 actual={'sha256':sha(q.read_bytes()),'mode':format(stat.S_IMODE(q.stat().st_mode),'04o'),'bytes':q.stat().st_size} if q.is_file() else None
 if actual!=v:changed.append({'path':p,'before':v,'after':actual})
head=git('rev-parse','HEAD').decode().strip();branch=git('branch','--show-current').decode().strip();index=sha((R/'.git/index').read_bytes());staged=sha(git('ls-files','--stage','-z'))
record={'status':'PASS' if not changed and index==before['index_sha256'] and staged==before['staged_entries_sha256'] and head==before['head'] and branch==before['branch'] else 'FAIL','verified_preexisting_files':len(before['files']),'changed_preexisting':changed,'HEAD':head,'branch':branch,'index_before':before['index_sha256'],'index_after':index,'staged_before':before['staged_entries_sha256'],'staged_after':staged,'live_product_changes':False,'historical_evidence_preserved':not changed,'commit':'NONE','push':'NOT PERFORMED','time_unix':time.time()}
for path,h in [(Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz'),'fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'),(R/'docs/benchmarks/t66f-b08/experimental-source.tar.gz','cb89861bedaa998ce3c53789f76ba92a412c4eeff9a05f34a1f49d8b25067e22')]:assert sha(path.read_bytes())==h
(E/'preservation-after.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in record.items() if k!='changed_preexisting'}));assert record['status']=='PASS',changed
