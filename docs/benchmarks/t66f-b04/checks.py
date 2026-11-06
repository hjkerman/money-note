"""성능 window 종료 뒤에만 수행할 제한 회귀·build."""
import json,os,pathlib,subprocess,time,xml.etree.ElementTree as ET
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04';W=pathlib.Path('/tmp/money-note-t66f-b04-20261026');T=W/'tree';records=[]
def run(name,cmd,cwd):
 log=W/'raw'/f'check-{name}.log';start=time.perf_counter();
 with log.open('xb') as f:r=subprocess.run(cmd,cwd=cwd,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(W/'disposable'),'npm_config_cache':str(W/'build/npm-cache')},stdout=f,stderr=subprocess.STDOUT)
 v={'name':name,'command':cmd,'cwd':str(cwd),'exit':r.returncode,'elapsed_s':time.perf_counter()-start,'log':str(log)};records.append(v)
 if r.returncode:print(log.read_text()[-2500:]);raise RuntimeError(name)
 return v
# 측정 process가 모두 종료된 뒤만 허용한다.
assert all(json.loads(p.read_text())['status']!='RUNNING' for p in E.glob('execution-*.json'))
assert not (E/'checks.json').exists() and not (E/'backend.xml').exists()
run('source-locks',[str(R/'.venv/bin/python'),str(T/'docs/benchmarks/t66f-b03-ic06/source_locks.py')],T)
pytest=[str(R/'.venv/bin/python'),'-m','pytest','-q','-p','no:cacheprovider','tests/test_isolated_sync_observation.py::test_forbids_full_history_and_graph_rebuild','tests/test_isolated_sync_observation.py::test_all_twelve_legacy_projection_parity','tests/test_isolated_sync_observation.py::test_no_runtime_import_or_new_routes','tests/test_isolated_sync_retention.py::test_normal_http_requests_do_not_scan_history_or_gc_graph',f'--basetemp={W}/disposable/pytest-backend',f'--junitxml={E}/backend.xml']
run('backend',pytest,T/'backend')
run('flutter-source-lock',['/home/hjkerman/.flutter/bin/flutter','test','--no-pub','--machine','--concurrency=1','test/segmented_logical_cost_source_lock_test.dart'],T/'mobile')
p=T/'frontend/node_modules';assert p.is_symlink() and p.resolve()==R/'frontend/node_modules';p.unlink();p.mkdir()
for q in (R/'frontend/node_modules').iterdir():
 if q.name in ('.tmp','.cache','.vite','.vite-temp'):(p/q.name).mkdir()
 else:(p/q.name).symlink_to(q,target_is_directory=q.is_dir())
for n in ('.tmp','.cache','.vite','.vite-temp'):(p/n).mkdir(exist_ok=True)
run('frontend-build',['npm','run','build'],T/'frontend')
run('preservation',[str(R/'.venv/bin/python'),str(E/'provenance.py'),'check'],R)
x=ET.parse(E/'backend.xml').getroot();suites=list(x.iter('testsuite'));backend={k:sum(int(s.attrib.get(k,0)) for s in suites) for k in ('tests','failures','errors','skipped')};events=[]
for line in (W/'raw/check-flutter-source-lock.log').read_text().splitlines():
 try:v=json.loads(line)
 except ValueError:continue
 if isinstance(v,dict):events.append(v)
flutter={'passed':sum(v.get('type')=='testDone' and v.get('result')=='success' and not v.get('hidden') for v in events),'done_success':any(v.get('type')=='done' and v.get('success') is True for v in events)}
summary=f"새 backend 영향 회귀 {backend['tests']}개 통과(실패{backend['failures']}, 오류{backend['errors']}, skip{backend['skipped']}), Flutter source-SHA {flutter['passed']}개 통과, 보호 source7개 SHA·frontend npm build 통과다. 실제 bounded grid의 case4개와 각 operation 원자료는 별도다. 전체 suite를 새 PASS로 주장하지 않았다."
(E/'checks.json').write_text(json.dumps({'records':records,'backend':backend,'flutter':flutter,'summary_ko':summary},ensure_ascii=False,indent=2)+'\n');print(summary)
