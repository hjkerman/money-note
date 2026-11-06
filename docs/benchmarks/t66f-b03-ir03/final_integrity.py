import hashlib,json,os,stat,subprocess
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');tree=r/'candidate';repo=Path('/home/hjkerman/codex/money-note');evidence=r/'evidence';m=json.loads((r/'metadata/ir01/candidate-source-manifest.json').read_text());selected={e['path']:e for e in m['entries']};differences=[]
for path,e in selected.items():
 p=tree/path;actual={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'mode':oct(stat.S_IMODE(p.stat().st_mode))}
 if any(e['worktree'][k]!=v for k,v in actual.items()):differences.append(path)
baseline=[];unselected=0;mode_errors=[]
raw=subprocess.check_output(['git','--no-optional-locks','-C',str(repo),'ls-tree','-r','-z','ebcbd54d90eeee194a04b9eea6367f446ee2fd28'])
for item in raw.split(b'\0'):
 if not item:continue
 header,path=item.split(b'\t',1);mode,kind,oid=header.decode().split();path=os.fsdecode(path)
 if path in selected:continue
 unselected+=1;p=tree/path
 if not p.is_file():baseline.append(path);continue
 b=p.read_bytes();actual=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
 if actual!=oid:baseline.append(path)
 if bool(p.stat().st_mode & 0o111)!=(mode=='100755'):mode_errors.append(path)
initial=json.loads((evidence/'integrity.json').read_text());frozen=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8');frozen_diff=[]
for path,expected in initial['frozen_files'].items():
 p=frozen/path
 if hashlib.sha256(p.read_bytes()).hexdigest()!=expected or stat.S_IMODE(p.stat().st_mode)!=0o444 or p.stat().st_nlink!=1:frozen_diff.append(path)
result={'selected_source_files':len(selected),'selected_source_differences':differences,'unselected_baseline_files':unselected,'unselected_baseline_differences':baseline,'unselected_executable_mode_differences':mode_errors,'frozen_differences':frozen_diff,'frozen_directory_mode':oct(stat.S_IMODE(frozen.stat().st_mode)),'payload_sha256':hashlib.sha256(json.dumps(m['entries'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
(evidence/'final-candidate-integrity.json').write_text(json.dumps(result,indent=2)+'\n');assert not differences and not baseline and not mode_errors and not frozen_diff;print(json.dumps(result))
