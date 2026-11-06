from pathlib import Path
import json,hashlib,gzip,os,subprocess,stat,re,tarfile
A=Path('/tmp/money-note-ir04-20261024');R=Path('/home/hjkerman/codex/money-note');D=R/'docs/benchmarks/t66f-b03-ir04';E=A/'evidence';report=R/'docs/t66f-b03-ir04-independent-final-reaudit.md';env=dict(os.environ,GIT_OPTIONAL_LOCKS='0')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
pre=json.loads((E/'preexisting-files.json').read_text());bad=[]
for x in pre:
 p=R/x['path']
 if not p.is_file() or sha(p)!=x['sha256'] or oct(stat.S_IMODE(p.stat().st_mode))!=x['mode']:bad.append(x['path'])
assert not bad
start=json.loads((E/'starting-state.json').read_text());git=lambda *a:subprocess.check_output(['git',*a],cwd=R,env=env).decode()
assert git('rev-parse','HEAD').strip()==start['head'] and git('symbolic-ref','--short','HEAD').strip()==start['branch'];assert sha(R/'.git/index')==start['index_sha256'] and git('ls-files','--stage')==start['staged']
status=git('status','--porcelain=v1','--untracked-files=all');own=lambda line:line[3:]=='docs/t66f-b03-ir04-independent-final-reaudit.md' or line[3:].startswith('docs/benchmarks/t66f-b03-ir04/')
assert '\n'.join(x for x in status.splitlines() if not own(x))=='\n'.join(start['status'].splitlines())
state={'preexisting_files_verified':len(pre),'differences':bad,'head':start['head'],'branch':start['branch'],'head_preserved':True,'index_sha256':sha(R/'.git/index'),'index_byte_identity_unchanged_during_ir04':True,'staged_logical_content_unchanged':True,'old_status_preserved_after_filtering_only_ir04_additions':True,'original_uncommitted_source_preserved':True,'historical_evidence_preserved_during_ir04':True,'authorized_new_paths_only':True,'commit':None,'push':'NOT PERFORMED','production_source_changes':0}
(D/'final-preservation.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n');(E/'final-preservation.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
s=report.read_text();changes=[]
for target in re.findall(r'\]\(([^)]+)\)',s):
 p=report.parent/target
 if not p.exists():
  alt=Path(str(p)[:-3]) if str(p).endswith('.gz') else Path(str(p)+'.gz')
  assert alt.exists(),('missing report link',target)
  new=str(alt.relative_to(report.parent));s=s.replace(']('+target+')',']('+new+')');changes.append({'before':target,'after':new})
report.write_text(s);assert all((report.parent/p).exists() for p in re.findall(r'\]\(([^)]+)\)',s));assert not re.search('[\u3040-\u30ff]',s)
(D/'report-link-check.json').write_text(json.dumps({'adjusted_to_retained_compression_names':changes,'all_links_exist':True,'japanese_explanatory_prose':False},indent=2)+'\n')
root=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03');new=root/'27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3';old=root/'645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8'
with tarfile.open(new/'candidate.tar.gz') as t:
 names=t.getnames();assert len(names)==827 and len(names)==len(set(names));assert all(x.isfile() for x in t)
 m=json.load(t.extractfile('metadata/source-manifest.json'));entries=m['entries'];assert entries==sorted(entries,key=lambda x:x['path'])
 for x in entries:
  assert not Path(x['path']).is_absolute() and '..' not in Path(x['path']).parts
  h=t.getmember('source/'+x['path']);b=t.extractfile(h).read();assert len(b)==x['bytes'] and hashlib.sha256(b).hexdigest()==x['sha256'] and h.mode==int(x['mode'],8)
 assert hashlib.sha256(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==new.name
 assert json.loads((new/'source-manifest.json').read_text())==m
with tarfile.open(old/'candidate.tar.gz') as t:
 oldm=json.load(t.extractfile('metadata/ir01/candidate-source-manifest.json'));oldentries={x['path']:x['worktree'] for x in oldm['entries']}
modified=[];added=[];deleted=sorted(set(oldentries)-{x['path'] for x in entries})
for x in entries:
 if x['path'] not in oldentries:added.append(x['path'])
 elif any(x[k]!=oldentries[x['path']][k] for k in ['bytes','mode','sha256']):modified.append(x['path'])
assert modified==sorted(['docs/benchmarks/t66f-b03/counters.py','mobile/test/support/logical_cost_sqlite.dart']) and not deleted and sorted(added)==sorted(m['added_source_files'])
proof=json.loads((E/'final-candidate-integrity.json').read_text())
for name,v in proof['new_snapshot_files'].items():p=new/name;assert sha(p)==v['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==v['mode']
(D/'final-archive-independent-check.json').write_text(json.dumps({'archive_members':827,'unique_regular_safe_paths':True,'source_entries_verified':825,'sidecar_embedded_manifest_equal':True,'parent_modified_paths':modified,'parent_added_paths':added,'parent_deleted_paths':deleted,'archive_sha256':sha(new/'candidate.tar.gz'),'read_only_snapshot_files_unchanged':True},indent=2)+'\n')
# Newly authored delivery tools are evidence too; never replace any existing copy.
for name in ['write_report.py','final_verify.py']:
 p=A/'tooling'/name;q=D/'tooling'/name
 with q.open('x') as out:out.write(p.read_text())
# Keep the requested footer in a compact independently readable file.
(D/'final-footer.txt').write_text((A/'footer.txt').read_text())
# Final retention inventory avoids circular self-hash.
files=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='retained-evidence.json']
(D/'retained-evidence.json').write_text(json.dumps({'report':{'path':str(report.relative_to(R)),'bytes':report.stat().st_size,'sha256':sha(report)},'files':files,'total_files_excluding_this_manifest':len(files),'total_bytes_excluding_this_manifest':sum(x['bytes'] for x in files),'frozen_snapshot':str(new)},ensure_ascii=False,indent=2)+'\n')
for x in files:
 p=R/x['path'];assert sha(p)==x['sha256']
 if p.suffix=='.gz':
  with gzip.open(p,'rb') as z:
   while z.read(65536):pass
assert sha(R/'.git/index')==start['index_sha256']
versions=json.loads((D/'environment.json').read_text());flutter=json.loads(versions['flutter']['stdout']);print(json.dumps({'report':str(report),'report_bytes':report.stat().st_size,'retained_files':len(files)+1,'retained_bytes':sum(x['bytes'] for x in files)+(D/'retained-evidence.json').stat().st_size,'preserved_preexisting_files':len(pre),'index_preserved':True,'all_links_valid':True,'archive_verified':True,'backend_runtime':versions['backend']['stdout'].splitlines(),'flutter':flutter['frameworkVersion'],'dart':flutter['dartSdkVersion'],'link_name_adjustments':changes},ensure_ascii=False))
