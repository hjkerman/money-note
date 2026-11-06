"""IC06 source-only 후보의 원자 동결과 고정 Git object 기반 재구성."""
import argparse
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2] if len(HERE.parents)>2 else HERE
REPOSITORY=Path(os.environ.get('IC06_BASE_REPOSITORY',str(ROOT)))
OUT=HERE/'evidence'
BASE='ebcbd54d90eeee194a04b9eea6367f446ee2fd28'
PARENT='47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5'
DEST=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03')

def sha(b):return hashlib.sha256(b).hexdigest()
def canon(entries):return json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def git(*args):return subprocess.check_output(['git','--no-optional-locks','-C',str(REPOSITORY),*args],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def describe(p):
 f=ROOT/p;assert f.is_file() and not f.is_symlink(),p
 b=f.read_bytes();return dict(path=p,mode=oct(stat.S_IMODE(f.stat().st_mode)),bytes=len(b),sha256=sha(b))
def source_paths():
 parent=json.loads((HERE.parent/'t66f-b03-ic05/corrected-candidate-manifest.json').read_text())
 paths={e['path'] for e in parent['entries']}
 paths.update(str(p.relative_to(ROOT)) for p in HERE.iterdir() if p.suffix=='.py' or p.name in ['monitoring-contract.md','monitoring-state-matrix.json','handoff-template.md'])
 paths.update('docs/benchmarks/t66f-b03-ir06/tests/'+n for n in ['pep669_released_tool_probe.py','monitoring_matrix_probe.py','test_ir06_lifecycle.py'])
 paths.update(['backend/tests/test_logical_cost_ic06.py','docs/benchmarks/t66f-b03-ic05/evidence/protected-source-check.json','docs/benchmarks/t66f-b03-ic05/corrected-candidate-manifest.json'])
 return sorted(paths)

def safe_path(p):
 p=Path(p);assert not p.is_absolute() and '..' not in p.parts,p
 return p

def verify(snapshot,workspace):
 assert not workspace.exists(),'새 폐기용 경로가 필요하다'
 manifest=json.loads((snapshot/'source-manifest.json').read_text())
 frozen=json.loads((snapshot/'freeze.json').read_text())
 entries=manifest['entries']; digest=sha(canon(entries));archive=sha((snapshot/'candidate.tar.gz').read_bytes())
 assert digest==manifest['candidate_source_digest_sha256']==frozen['payload_sha256']
 assert snapshot.name==digest or snapshot.name.startswith('.ic06-')
 assert manifest['files']==len(entries) and manifest['source_bytes']==sum(e['bytes'] for e in entries)
 assert [e['path'] for e in entries]==sorted(set(e['path'] for e in entries))
 for line in (snapshot/'SHA256SUMS').read_text().splitlines():
  h,p=line.split();assert sha((snapshot/safe_path(p)).read_bytes())==h,p
 assert git('rev-parse',BASE).decode().strip()==frozen['base_commit']==BASE
 assert git('rev-parse',BASE+'^{tree}').decode().strip()==frozen['base_tree']
 workspace.mkdir(parents=True)
 with tarfile.open(fileobj=io.BytesIO(git('archive',BASE))) as t:t.extractall(workspace,filter='data')
 for p in frozen['tracked_deletions']:(workspace/safe_path(p)).unlink()
 with tarfile.open(snapshot/'candidate.tar.gz') as t:
  names=[m.name for m in t.getmembers()];assert len(names)==len(set(names))==len(entries)+len(frozen['context'])+2
  assert json.loads(t.extractfile('metadata/source-manifest.json').read())==manifest
  assert json.loads(t.extractfile('metadata/freeze.json').read())==frozen
  for e in entries:
   member=t.getmember('source/'+e['path']);assert member.isfile() and member.mode==int(e['mode'],8)
   body=t.extractfile(member).read();assert len(body)==e['bytes'] and sha(body)==e['sha256']
   f=workspace/safe_path(e['path']);f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(body);f.chmod(member.mode)
  for e in frozen['context']:
   member=t.getmember('context/'+e['path']);body=t.extractfile(member).read()
   assert member.isfile() and member.mode==int(e['mode'],8) and len(body)==e['bytes'] and sha(body)==e['sha256']
 baseline=[];untouched=0;selected={e['path'] for e in entries}
 for record in git('ls-tree','-r','-z',BASE).split(b'\0'):
  if not record:continue
  meta,p=record.split(b'\t');mode,kind,oid=meta.split();name=p.decode()
  baseline.append(dict(path=name,git_mode=mode.decode(),git_blob=oid.decode()))
  if name in selected or name in frozen['tracked_deletions']:continue
  f=workspace/safe_path(name);assert f.read_bytes()==git('cat-file','blob',oid.decode()),name
  assert bool(f.stat().st_mode&0o111)==(mode==b'100755'),name
  untouched+=1
 assert baseline==frozen['baseline_inventory']
 for e in entries:
  f=workspace/e['path'];assert describe_workspace(f,e)
 assert all(not (workspace/p).exists() for p in frozen['tracked_deletions'])
 return dict(payload_sha256=digest,archive_sha256=archive,snapshot=str(snapshot),workspace=str(workspace),files=len(entries),bytes=sum(e['bytes'] for e in entries),baseline_files=len(baseline),baseline_other_files_verified=untouched,tracked_deletions=frozen['tracked_deletions'],required_untracked_verified=len(frozen['required_untracked']),reconstruction='PASS',mutable_worktree_source_used=False)

def describe_workspace(f,e):return f.is_file() and sha(f.read_bytes())==e['sha256'] and len(f.read_bytes())==e['bytes'] and oct(stat.S_IMODE(f.stat().st_mode))==e['mode']

def freeze(workspace):
 summary=json.loads((OUT/'summary.json').read_text());assert summary['implementation_verdict']=='PASS'
 assert git('rev-parse','HEAD').decode().strip()==BASE
 start=json.loads(gzip.open(OUT/'starting-state.json.gz','rt').read())
 assert git('ls-files','--stage').decode()==start['staged'] and sha((REPOSITORY/'.git/index').read_bytes())==start['index_sha256']
 for p,h in summary['final_source_sha256'].items():assert describe(p)['sha256']==h,p
 paths=source_paths();entries=[describe(p) for p in paths];digest=sha(canon(entries));destination=DEST/digest
 assert not destination.exists() and digest!=PARENT
 tracked=set(git('ls-files','-z').decode().split('\0'))-{''}
 modifications=sorted(set(git('diff','--name-only','-z').decode().split('\0'))-{''})
 deletions=sorted(p for p in tracked if not (ROOT/p).exists())
 assert set(modifications)<=set(paths)|set(deletions),'목록 밖 tracked 변경'
 baseline=[]
 for record in git('ls-tree','-r','-z',BASE).split(b'\0'):
  if not record:continue
  meta,p=record.split(b'\t');mode,kind,oid=meta.split();baseline.append(dict(path=p.decode(),git_mode=mode.decode(),git_blob=oid.decode()))
 context_paths=sorted(str(p.relative_to(ROOT)) for p in OUT.rglob('*') if p.is_file())
 context_paths += ['docs/t66f-b03-ir06-independent-lifecycle-closure.md','docs/benchmarks/t66f-b03-ir06/findings.json','docs/t66f-b03-ic05-ownership-entry-handoff-correction.md','docs/benchmarks/t66f-b03-ic05/evidence/handoff-transition-matrix.json','docs/t66/c/t66c-delta-sync-protocol.md']
 context=[describe(p) for p in sorted(set(context_paths))]
 manifest=dict(schema_version=1,kind='IC06 구현 측 동결; 독립 감사 대기',base_commit=BASE,starting_ic05_payload_sha256=PARENT,candidate_source_digest_sha256=digest,digest_definition="SHA256(UTF8 JSON(entries), path sorted, ensure_ascii=False, sort_keys=True, separators=(',',':'))",files=len(entries),source_bytes=sum(e['bytes'] for e in entries),entries=entries)
 frozen=dict(base_commit=BASE,base_tree=git('rev-parse',BASE+'^{tree}').decode().strip(),payload_sha256=digest,tracked_deletions=deletions,tracked_modifications=modifications,required_untracked=sorted(set(paths)-tracked),staged_logical_sha256=sha(git('ls-files','--stage')),baseline_inventory=baseline,context=context,independence='구현 측 검증; 독립 closure 아님',immutability='읽기 전용과 checksum; WORM 아님',source_selection='IC05 전체 관련 source + IC06 코드/계약/전이표 + 원 IR06 재현; 나머지 committed source는 고정 base inventory로 재구성. 최종 보고·동결 이후 증거는 payload 밖 행정 산출물이다.')
 stage=Path(tempfile.mkdtemp(prefix='.ic06-',dir=DEST))
 archive=stage/'candidate.tar.gz'
 with archive.open('wb') as raw,gzip.GzipFile(fileobj=raw,mode='wb',filename='',mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as t:
  def add(name,body,mode=0o444):
   h=tarfile.TarInfo(name);h.size=len(body);h.mode=mode;h.mtime=0;t.addfile(h,io.BytesIO(body))
  for prefix,e in [('source/',e) for e in entries]+[('context/',e) for e in context]:
   assert describe(e['path'])==e,'동결 도중 source 변경'
   add(prefix+e['path'],(ROOT/e['path']).read_bytes(),int(e['mode'],8))
  add('metadata/source-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
  add('metadata/freeze.json',json.dumps(frozen,ensure_ascii=False,indent=2).encode())
 for e in entries+context:assert describe(e['path'])==e,'최종화 전 source 변경'
 for name,value in [('source-manifest.json',manifest),('freeze.json',frozen)]:
  (stage/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 handoff=(HERE/'handoff-template.md').read_text().replace('@PAYLOAD@',digest).replace('@ARCHIVE@',sha(archive.read_bytes())).replace('@SNAPSHOT@',str(destination)).replace('@BACKEND@',summary['full_backend_korean'])
 (stage/'HANDOFF.md').write_text(handoff)
 (stage/'SHA256SUMS').write_text(''.join(sha((stage/n).read_bytes())+'  '+n+'\n' for n in ['candidate.tar.gz','source-manifest.json','freeze.json','HANDOFF.md']))
 record=verify(stage,workspace)
 for p in stage.iterdir():p.chmod(0o444)
 stage.chmod(0o555);stage.rename(destination)
 record['snapshot']=str(destination)
 (OUT/'freeze-reconstruction.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
 (HERE/'corrected-candidate-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(record,ensure_ascii=False))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['create','verify']);p.add_argument('paths',nargs='+');a=p.parse_args()
 if a.mode=='create':assert len(a.paths)==1;freeze(Path(a.paths[0]))
 else:assert len(a.paths)==2;print(json.dumps(verify(Path(a.paths[0]),Path(a.paths[1])),ensure_ascii=False))
