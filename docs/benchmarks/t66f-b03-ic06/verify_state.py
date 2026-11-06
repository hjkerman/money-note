"""보호 SHA·Git index·기존 증거·역사 후보와 최소 AST 변경 경계를 검증한다."""
import ast, gzip, hashlib, json, os, stat, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent/'evidence'
def sha(b):return hashlib.sha256(b).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks',*a],cwd=R,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def verify():
 start=json.loads(gzip.open(O/'starting-state.json.gz','rt').read());changed=[]
 for e in start['preexisting']:
  p=R/e['path'];assert p.is_file(),e['path']
  if sha(p.read_bytes())!=e['sha256'] or oct(stat.S_IMODE(p.stat().st_mode))!=e['mode']:changed.append(e['path'])
 assert changed==['docs/benchmarks/t66f-b03/counters.py'],changed
 assert git('ls-files','--stage').decode()==start['staged']
 assert sha((R/'.git/index').read_bytes())==start['index_sha256']
 frozen=Path(start['historical_candidate'])
 for e in start['frozen_files']:
  p=frozen/e['path'];assert sha(p.read_bytes())==e['sha256'] and oct(stat.S_IMODE(p.stat().st_mode))==e['mode']
 locked=json.loads((R/'docs/benchmarks/t66f-b03-ic05/evidence/protected-source-check.json').read_text())
 for p,h in locked['six_exact_protected_sources'].items():assert sha((R/p).read_bytes())==h,p
 assert sha((R/'mobile/test/support/logical_cost_sqlite.dart').read_bytes())==locked['Dart_helper_sha256']
 before=ast.parse(gzip.open(O/'baseline-counters.py.gz','rt').read());after=ast.parse((R/'docs/benchmarks/t66f-b03/counters.py').read_text())
 def nodes(tree):return {n.name:ast.dump(n,include_attributes=False) for n in tree.body if hasattr(n,'name')}
 old,new=nodes(before),nodes(after);assert old.keys()==new.keys()
 assert [n for n in old if old[n]!=new[n]]==['EntryHandoff']
 oldclass=next(n for n in before.body if getattr(n,'name',None)=='EntryHandoff');newclass=next(n for n in after.body if getattr(n,'name',None)=='EntryHandoff')
 a,b=nodes(oldclass),nodes(newclass);assert [n for n in a if a[n]!=b[n]]==['check_monitoring']
 d=dict(head=git('rev-parse','HEAD').decode().strip(),staged_sha256=sha(git('ls-files','--stage')),index_sha256=start['index_sha256'],preexisting_verified=len(start['preexisting']),changed_preexisting_paths=changed,historical_frozen_files_verified=len(start['frozen_files']),source_locks=locked['six_exact_protected_sources'],Dart_helper_sha256=locked['Dart_helper_sha256'],changed_AST_methods=['EntryHandoff.check_monitoring'],source_lock_updates=[],binding_protocol_unchanged=True,product_sources_unchanged=True,result='PASS')
 return d
if __name__=='__main__':
 import sys
 label=sys.argv[1] if len(sys.argv)>1 else 'preservation';p=O/(label+'.json');assert not p.exists();d=verify();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:d[k] for k in ['preexisting_verified','changed_preexisting_paths','changed_AST_methods','result']}))
