"""필수 증거를 확인한 뒤 B05-B scratch만 정리하고 Git·역사 자료를 대조한다."""
import contextlib,gzip,json,os,pathlib,shutil,sqlite3,stat,subprocess,time
from prepare import R,E,W,H,sha,save,git,inventory
from campaign import check_sources
assert json.loads((E/'verification-summary.json').read_text())['status']=='PASS';assert json.loads((E/'execution.json').read_text())['exit_code']==0
# 후속 검증의 종료 summary까지 담은 원문을 별도 이름으로 보존한다.
(E/'verification-completed.log.gz').write_bytes(gzip.compress((W/'raw/verification.log').read_bytes(),mtime=0))
# 실제 bounded 실측 driver test 1건 안에 cold2건이다. compile/admission preflight10건과 구별한다.
def events(path):return [json.loads(s) for s in path.read_text().splitlines() if s.startswith('{')]
pf=events(W/'raw/preflight-flutter.jsonl');cold=events(W/'raw/cold.jsonl');assert any(x.get('type')=='done' and x.get('success') for x in pf);assert any(x.get('type')=='done' and x.get('success') for x in cold)
backend=(W/'raw/backend-admission.log').read_text();assert '4 passed' in backend
build=(W/'raw/frontend-build-with-runtime.log').read_text();assert 'built in' in build
save(E/'checks.json',{'backend_admission':{'command':'PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 ../.venv/bin/python -m pytest -q -p no:cacheprovider --basetemp=<scratch>/disposable/backend-admission tests/test_engine_admission_b05a.py','cwd':str(W/'candidate/backend'),'passed':4,'exit_code':0,'full_suite':False},'Flutter_preflight':{'passed':sum(x.get('type')=='testDone' and x.get('result')=='success' and not x.get('hidden') for x in pf),'exit_code':0,'admission_test':'test/segmented_engine_admission_b05a_test.dart','compile_only':'--dart-define=B05A_COMPILE_ONLY=true ../docs/benchmarks/t66f-b05a/cold_test.dart','cold_acquisitions':0},'real_Flutter':{'driver_tests':sum(x.get('type')=='testDone' and x.get('result')=='success' and not x.get('hidden') for x in cold),'cold_acquisitions':2,'exit_code':0},'frontend_build':{'command':'npm run build','cwd':str(W/'candidate/frontend'),'exit_code':0},'tooling_incidents':[{'phase':'사전 frontend build','first_exit':127,'cause':'격리 frontend에 기존 node_modules runtime symlink 누락으로 tsc 미발견','resolution':'기존 checkout node_modules symlink만 연결 후 build PASS','source_changes':0,'full_cold_started_before_resolution':0}],'full_backend':'NOT RERUN — HISTORICAL B05-A PASS','full_Flutter':'NOT RERUN — HISTORICAL B05-A AFFECTED PASS'})
check_sources('source-final.json')
# baseline 나머지 고정 Git blob와 실행 비트도 마지막에 확인한다.
freeze=json.loads(pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/freeze.json').read_text());import hashlib,tarfile
remainder={}
for v,T,arch in [('A',W/'baseline',pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz')),('B',W/'candidate',pathlib.Path(json.loads((H/'freeze.json').read_text())['archive']))]:
 with tarfile.open(arch) as t:m=json.loads(t.extractfile('metadata/source-manifest.json').read())
 selected={a['path'] for a in m['entries']};count=0
 for a in freeze['baseline_inventory']:
  if a['path'] in selected:continue
  p=T/a['path'];b=p.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==a['git_blob'];mode=a.get('mode',a.get('git_mode'));expected_exec=(str(mode)=='100755') if mode else bool(p.stat().st_mode & 0o111)
  assert bool(p.stat().st_mode & 0o111)==expected_exec,(a,p);count+=1
 remainder[v]={'baseline_files':count,'blob_and_executable_mode':'PASS'}
save(E/'remaining-baseline-final.json',remainder)
manifest=json.loads((E/'run-manifest.json').read_text())
for d in manifest['runs']:
 p=R/d['raw'];assert sha(p.read_bytes())==d['raw_sha256'];iv=json.loads((p.parent/'independent-verification.json').read_text())
 for role in ['client','backend']:
  compressed=(p.parent/(role+'-consistent.sqlite.gz')).read_bytes();data=gzip.decompress(compressed);assert sha(data)==iv['details'][role]['backup_sha256'] and sha(compressed)==iv['details'][role]['gzip_sha256']
for name,a in json.loads((E/'source-integrity.json').read_text())['archives'].items():assert sha(pathlib.Path(a['archive']).read_bytes())==a['archive_sha256']
processes=subprocess.check_output(['ps','-eo','pid,ppid,comm,args'],text=True).splitlines();active=[s for s in processes if str(W) in s and len(s.split())>=3 and s.split()[2] in ['flutter_tester','dartvm','dartaotruntime','python','python3','python3.12']];assert not active,active
# task-owned 실측 프로세스는 모두 종료했고 matched backups는 검증된 별도 evidence에 있다.
files=[p for p in W.rglob('*') if p.is_file() and not p.is_symlink()];allocated=sum(p.stat().st_blocks*512 for p in files);logical=sum(p.stat().st_size for p in files);free=shutil.disk_usage(W).free
assert W==pathlib.Path('/tmp/money-note-t66f-b05b-20261026') and not W.is_symlink();shutil.rmtree(W)
save(E/'cleanup.json',{'scratch':str(W),'removed':not W.exists(),'removed_files':len(files),'removed_allocated_bytes':allocated,'removed_logical_bytes':logical,'active_users':active,'matched_SQLite_backups_retained':4,'template_retained_reference':'docs/benchmarks/t66f-b05a/fixture-template-n5000.sqlite.gz','historical_source_snapshots_deleted':0,'preexisting_files_deleted':0,'external_cache_deleted':False,'active_DB_WAL_deleted':False,'free_before':free,'free_after':shutil.disk_usage('/tmp').free,'evidence_files_bytes':sum(p.stat().st_size for p in E.rglob('*') if p.is_file()),'remaining_review_candidates':[],'time_unix':time.time(),'note':'정리량은 task-owned 파일의 st_blocks 합계이며 filesystem free 변화와 다를 수 있다.'})
before=json.loads((E/'preservation-before.json').read_text());now=inventory();changed=[p for p,a in before['files'].items() if now.get(p)!=a];added=[p for p in now if p not in before['files']];assert not changed and not added,(changed,added)
index=R/git('rev-parse','--git-path','index').decode().strip();record={'head':git('rev-parse','HEAD').decode().strip(),'index_sha256':sha(index.read_bytes()),'index_preserved':sha(index.read_bytes())==before['index_sha256'],'original_index_copy_exact':index.read_bytes()==(E/'original-index.bin').read_bytes(),'staged_entries_preserved':sha(git('ls-files','--stage','-z'))==before['staged_entries_sha256'],'preexisting_changed':changed,'unexpected_added':added,'historical_evidence_preserved':not changed,'all_preexisting_files_verified':len(before['files']),'time_unix':time.time()};assert record['index_preserved'] and record['staged_entries_preserved'] and record['head']==before['head'];save(E/'preservation-after.json',record)
print(json.dumps({'cleanup':'PASS','removed_MiB':allocated/1024**2,'Git_index':'PRESERVED','preexisting_files_verified':len(before['files']),'retained_backups':4}))
