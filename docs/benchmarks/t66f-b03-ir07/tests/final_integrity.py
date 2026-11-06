"""시험 뒤 동결 payload와 나머지 고정 baseline 전체를 다시 검증한다."""
import hashlib,json,os,pathlib,stat,subprocess
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b03-ir07';W=pathlib.Path('/tmp/money-note-t66f-b03-ir07-20261025');T=W/'tree';S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8')
sha=lambda b:hashlib.sha256(b).hexdigest();m=json.loads((S/'source-manifest.json').read_bytes());f=json.loads((S/'freeze.json').read_bytes());selected={x['path'] for x in m['entries']}
for e in m['entries']:
 p=T/e['path'];assert sha(p.read_bytes())==e['sha256'] and stat.S_IMODE(p.stat().st_mode)==int(e['mode'],8),e['path']
other=0;diff=[]
for e in f['baseline_inventory']:
 p=e['path']
 if p in selected or p in f['tracked_deletions']:continue
 expected=subprocess.check_output(['git','--no-optional-locks','-C',str(R),'cat-file','blob',e['git_blob']],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
 if (T/p).read_bytes()!=expected or bool((T/p).stat().st_mode&0o111)!=(e['git_mode']=='100755'):diff.append(p)
 other+=1
assert diff==[],diff
assert sha((S/'candidate.tar.gz').read_bytes())=='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'
v={'result':'PASS','payload_sha256':m['candidate_source_digest_sha256'],'payload_files_verified':len(m['entries']),'other_baseline_files_verified':other,'differences':diff,'archive_unchanged':True,'source_and_executable_modes_preserved':True}
(E/'final-candidate-integrity.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print(v)
