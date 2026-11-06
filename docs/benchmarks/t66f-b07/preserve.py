"""B07은 analysis/report만 쓴다. 기존 source·Git·증거를 bytes/mode로 보존한다."""
import hashlib,json,os,pathlib,stat,subprocess,sys,time,shutil
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b07';W=pathlib.Path('/tmp/money-note-t66f-b07-20261026')
sha=lambda b:hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def inv():
 out={};paths=set(git('ls-files','-z').split(b'\0'))|set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'))
 for p in sorted(paths):
  if not p:continue
  p=p.decode()
  if p.startswith('docs/benchmarks/t66f-b07/') or p=='docs/t66f-b07-bounded-connect-schema-attribution.md':continue
  f=R/p
  if f.is_file():out[p]={'sha256':sha(f.read_bytes()),'mode':format(stat.S_IMODE(f.stat().st_mode),'04o'),'bytes':f.stat().st_size}
 return out
if sys.argv[1]=='before':
 assert not (E/'preservation-before.json').exists() and not W.exists();W.mkdir()
 d={'head':git('rev-parse','HEAD').decode().strip(),'branch':git('branch','--show-current').decode().strip(),'index_sha256':sha((R/'.git/index').read_bytes()),'staged_entries_sha256':sha(git('ls-files','--stage','-z')),'staged_entries':git('ls-files','--stage','-z').decode().split('\0'),'files':inv(),'disk':shutil.disk_usage(R)._asdict(),'time':time.time()}
 (E/'preservation-before.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'head':d['head'],'branch':d['branch'],'preexisting_files':len(d['files']),'index_sha256':d['index_sha256']}))
else:
 before=json.loads((E/'preservation-before.json').read_text());after=inv();changed=[p for p,v in before['files'].items() if after.get(p)!=v]
 d={'head':git('rev-parse','HEAD').decode().strip(),'branch':git('branch','--show-current').decode().strip(),'preexisting_changed':changed,'new_visible_outside_B07':[p for p in after if p not in before['files']],'index_sha256':sha((R/'.git/index').read_bytes()),'staged_entries_sha256':sha(git('ls-files','--stage','-z')),'index_preserved':sha((R/'.git/index').read_bytes())==before['index_sha256'],'staged_entries_preserved':sha(git('ls-files','--stage','-z'))==before['staged_entries_sha256'],'preexisting_files_checked':len(before['files']),'time':time.time()};(E/'preservation-after.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps(d));assert not changed and not d['new_visible_outside_B07'] and d['index_preserved'] and d['staged_entries_preserved'] and d['head']==before['head'] and d['branch']==before['branch']
