"""실측 전에 exact source→engine→artifact와 bounded runtime 검증."""
import base64,contextlib,ctypes,gzip,hashlib,json,os,pathlib,platform,shutil,sqlite3,subprocess,sys,time
from prepare import R,E,W,H,sha,save
results={}
code='''import base64,hashlib,json,pathlib,sys,sqlite3
from isolated_sync.observation import engine_artifact
from isolated_sync.artifacts import release_bundle
R=pathlib.Path.cwd();root=R/'backend';paths=sorted((root/'app').rglob('*.py'))+sorted((root/'isolated_sync').glob('*.py'))+sorted((root/'app/services/judgment/messages').glob('*.yaml'))
raw=json.dumps({'profile':'isolated-d3a/1','sources':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
assert raw==engine_artifact();b=release_bundle();checked=json.loads((R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes());assert b==checked
assert (R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes()==(R/'mobile/assets/segmented/isolated-release-artifacts.json').read_bytes()
for a in b['artifacts'].values():
 data=base64.b64decode(a['data_base64']);assert len(data)==int(a['bytes']) and hashlib.sha256(data).hexdigest()==a['sha256']
print(json.dumps({'engine_sha':hashlib.sha256(raw).hexdigest(),'python':sys.version,'backend_SQLite':sqlite3.sqlite_version,'release_artifact_sha256':hashlib.sha256((R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes()).hexdigest(),'artifacts':{k:v['sha256'] for k,v in b['artifacts'].items()}}))
'''
plan=json.loads((E/'plan.json').read_text())
for v,T in [('A',W/'baseline'),('B',W/'candidate')]:
 d=json.loads(subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=T,env={**os.environ,'PYTHONPATH':str(T/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},text=True));assert d['engine_sha']==next(x for x in plan['runs'] if x['variant']==v)['engine_sha'];assert d['backend_SQLite']=='3.45.1' and d['python'].startswith('3.12.3');results[v]=d
for k in ['raw_schema','projection_schema','policy_registry']:assert results['A']['artifacts'][k]==results['B']['artifacts'][k]
# template은 정적 합성 source backup이며 expired historical observations는 새 실행의 accepted generation이 아니다.
f=W/'fixtures-n5000/template-combined.sqlite'
with contextlib.closing(sqlite3.connect('file:'+str(f)+'?mode=ro',uri=True)) as c:
 assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();results['fixture_SQLite']={'quick_check':'ok','FK_errors':0,'ledger_rows':c.execute('SELECT count(*) FROM ledger_entries').fetchone()[0],'observations':c.execute('SELECT status,count(*) FROM sync_observations GROUP BY status').fetchall()};assert results['fixture_SQLite']['ledger_rows']==5000
lib=ctypes.CDLL(str(W/'runtime/libsqlite3.so'));lib.sqlite3_libversion.restype=ctypes.c_char_p;assert lib.sqlite3_libversion().decode()=='3.53.4'
results['environment']={'python_executable':os.path.realpath(R/'.venv/bin/python'),'platform':platform.platform(),'cpu':platform.processor(),'logical_cpus':os.cpu_count(),'client_SQLite':'3.53.4','client_library_sha256':sha((W/'runtime/libsqlite3.so').read_bytes()),'flutter':json.loads(pathlib.Path('/home/hjkerman/.flutter/bin/cache/flutter.version.json').read_text()),'disk_before':shutil.disk_usage(W)._asdict(),'backend_RLIMIT_AS_bytes':8*1024**3,'observation_lease_seconds':900,'attempts':3,'network':'ephemeral loopback TLS; no production/development API','profile':'unchanged B04 explicit HOST largeGraphVerification','client_SQLite_config':'foreign_keys=ON; synchronous=EXTRA(3); journal_mode=DELETE; existing store limits','OS_cache_flush':False,'thermal_CPU_affinity_control':False,'source_code_edits':False,'same_Flutter_process_for_pair':True}
assert results['environment']['flutter']['frameworkVersion']=='3.47.4';assert results['environment']['flutter']['dartSdkVersion'].startswith('3.13.3')
# 원 driver의 bytes를 격리 workspace의 같은 상대 경로에만 설치한다. 제품 payload에 없는 파일이다.
p=W/'candidate/docs/benchmarks/t66f-b05a/cold_test.dart';assert not p.exists();shutil.copyfile(H/'cold_test.dart',p)
results['driver']={'source':str(H/'cold_test.dart'),'execution':str(p),'sha256':sha(p.read_bytes()),'path_only_adapter':False}
results['competing_processes_before']=subprocess.check_output(['ps','-eo','pid,ppid,pcpu,rss,comm,args'],text=True);assert not any(s.split()[4] in ['flutter_tester','dartvm','dartaotruntime'] for s in results['competing_processes_before'].splitlines()[1:] if len(s.split())>=5)
save(E/'preflight.json',results);print(json.dumps({'status':'PASS','engine_A':results['A']['engine_sha'],'engine_B':results['B']['engine_sha'],'runtime':'CPython3.12.3 Flutter3.47.4 Dart3.13.3 SQLite3.53.4','free_disk':results['environment']['disk_before']['free']}))
