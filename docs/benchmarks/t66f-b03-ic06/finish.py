"""완결 gate 이후에만 후보 동결·복원본 검증·증거 정리를 순차 수행한다."""
import gzip,hashlib,importlib.util,json,os,subprocess,sys,tarfile
from pathlib import Path
R=Path(__file__).resolve().parents[3];H=Path(__file__).parent;O=H/'evidence';S=R/'work/t66f-b03-ic06';PY=R/'.venv/bin/python'
def module(name):
 spec=importlib.util.spec_from_file_location('ic06_'+name,H/(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def command(*args,env=None,cwd=None):
 subprocess.run(list(map(str,args)),env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1',**(env or {})},cwd=cwd or R,check=True)
def preserve():
 for name in ['originals','http','output-root']:
  p=S/name
  if not p.exists():continue
  a=O/(name+'-scratch.tar.gz');assert not a.exists()
  with tarfile.open(a,'w:gz') as t:
   for f in sorted(p.rglob('*')):
    if f.is_file() and not f.is_symlink():t.add(f,arcname=str(f.relative_to(p)),recursive=False)
  with tarfile.open(a) as t:
   for e in t.getmembers():assert hashlib.sha256(t.extractfile(e).read()).digest()==hashlib.sha256((p/e.name).read_bytes()).digest()
if __name__=='__main__':
 assert (O/'backend-supported-complete.json').exists(),'전체 회귀 완결 전 동결 금지'
 command(PY,H/'summarize.py')
 command(PY,H/'verify_state.py','preservation-before-freeze')
 preserve()
 # The user explicitly authorized a new sibling snapshot, never historical
 # replacement. freeze.py rejects any existing digest destination.
 command(PY,H/'freeze.py','create',S/'candidate')
 runner=module('run');tree=S/'candidate';(tree/'.venv').symlink_to(R/'.venv',target_is_directory=True)
 env={'PYTHONPATH':str(tree/'backend'),'IR06_TREE':str(tree)}
 audit_env=['env',*[k+'='+v for k,v in env.items()]]
 assert runner.run('reconstruction-provenance',audit_env+[str(PY),'-c',f'import isolated_sync.canonical as c; from pathlib import Path; assert Path(c.__file__).is_relative_to(Path({str(tree)!r})); print(c.__file__)'],cwd=tree)==0
 assert runner.run('frozen-smoke',audit_env+[str(PY),str(tree/'docs/benchmarks/t66f-b03-ic06/backend.py'),'-q','-p','no:cacheprovider',str(tree/'backend/tests/test_logical_cost_ic05.py'),str(tree/'backend/tests/test_logical_cost_ic06.py'),str(tree/'backend/tests/test_logical_cost_ic04.py')+'::test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage','--basetemp='+str(S/'pytest-smoke'),'--junitxml='+str(O/'frozen-smoke.xml')],cwd=tree)==0
 for label,args in [('primary',['pep669_released_tool_probe.py']),('instrument',['monitoring_matrix_probe.py','instrument','8']),('workers',['monitoring_matrix_probe.py','instrument_workers','8']),('stage',['monitoring_matrix_probe.py','stage','8'])]:
  assert runner.run('frozen-ir06-'+label,audit_env+[str(PY),str(tree/'docs/benchmarks/t66f-b03-ir06/tests'/args[0]),*args[1:]],cwd=tree)==0
 snap=Path(json.loads((O/'freeze-reconstruction.json').read_text())['snapshot'])
 # Recheck every source byte/mode after executing the reconstruction smoke.
 manifest=json.loads((snap/'source-manifest.json').read_text())
 verifier=module('freeze')
 for e in manifest['entries']:
  p=tree/e['path'];assert verifier.describe_workspace(p,e),e['path']
 (O/'reconstruction-post-smoke.json').write_text(json.dumps(dict(result='PASS',files=len(manifest['entries']),source_unchanged=True,source_payload=manifest['candidate_source_digest_sha256'],live_product_source_used=False),ensure_ascii=False,indent=2)+'\n')
 command(PY,H/'verify_state.py','preservation-final')
 command(PY,H/'cleanup.py')
 command(PY,H/'report.py')
 # Full final preservation after administrative report/cleanup as well.
 module('verify_state').verify()
 print('IC06 교정·동결·재구성·인계 완료')
