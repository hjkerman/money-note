"""cold 직전 source/runtime/fixture/동시 작업/디스크를 읽기 검증한다."""
from pathlib import Path
import ctypes,hashlib,json,os,platform,shutil,subprocess,sys,time
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=Path('/tmp/money-note-t66f-b09-20261026');N=int(sys.argv[1]);sha=lambda b:hashlib.sha256(b).hexdigest()
plan=json.loads((E/f'plan-n{N}.json').read_text());src=json.loads((E/'source-reconstruction.json').read_text());C=W/'candidate'
for v,n in [('A','baseline'),('B','candidate')]:
 T=W/n;paths=sorted((T/'backend/app').rglob('*.py'))+sorted((T/'backend/isolated_sync').glob('*.py'))+sorted((T/'backend/app/services/judgment/messages').glob('*.yaml'));mapping={p.relative_to(T/'backend').as_posix():sha(p.read_bytes()) for p in paths}
 assert mapping==src['variants'][v]['engine_inputs']
for p,h in plan['client_component_inventory'].items():assert sha((C/p).read_bytes())==h
f=json.loads((W/f'fixtures-n{N}/fixture.json').read_text());assert sha((W/f'fixtures-n{N}/template-combined.sqlite').read_bytes())==f['template_sha256']
assert f['A']['graph']['raw_value_sha256']==f['B']['graph']['raw_value_sha256'];assert f['A']['graph']['objects']==f['B']['graph']['objects']
for v in ['A','B']:assert f[v]['manifest']['target']['context']['financial_engine']==src['variants'][v]['engine']
lib=ctypes.CDLL(str(W/'runtime/libsqlite3.so'));lib.sqlite3_libversion.restype=ctypes.c_char_p;assert lib.sqlite3_libversion().decode()=='3.53.4'
assert sha((C/'mobile/.dart_tool/lib/libsqlite3.so').read_bytes())==sha((W/'runtime/libsqlite3.so').read_bytes())
usage=shutil.disk_usage(W);assert usage.free>10*1024**3
ps=subprocess.check_output(['ps','-eo','pid,comm,args'],text=True);active=[l for l in ps.splitlines() if ('backend_regression.py -q' in l or '/flutter_tester --' in l or 'flutter_tools.snapshot test ' in l) and not ('preflight.py' in l or 'bash' in l or 'ps -eo' in l)]
assert not active,active
import sqlite3
out={'N':N,'status':'PASS','time_unix':time.time(),'platform':platform.platform(),'python':sys.version,'backend_SQLite':sqlite3.sqlite_version,'Flutter':json.loads(Path('/home/hjkerman/.flutter/bin/cache/flutter.version.json').read_text()),'client_SQLite':'3.53.4','client_library_sha256':sha((W/'runtime/libsqlite3.so').read_bytes()),'fixture_sha256':f['template_sha256'],'reachable_objects':f['A']['graph']['objects'],'disk':usage._asdict(),'competing_test_processes':active,'backend_RLIMIT_AS':8*1024**3,'authorization':'preserved synthetic token expires 2026-12-31; actual UTC','observation_lease_seconds':900,'observation_attempts':3,'network':'ephemeral isolated loopback TLS; no18080/18081','native_limits':'original client foreign_keys ON; synchronous EXTRA; DELETE journal; original limits','OS_cache_flush':False,'thermal_or_CPU_affinity_control':False,'B03_source_and_instrumentation_unchanged':True,'B09_probe':'external task-owned wrappers; not IR07 audited; symmetric policy; calibration recorded per server init','cold':'client objects0 accepted null sequence0; backend prepared views; process-startup excluded','boundary':'AppState publication + bounded accepted E4; UI/OfflineReady not claimed'}
(E/f'preflight-n{N}.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'N':N,'status':'PASS','free_GiB':round(usage.free/1024**3,2),'objects':out['reachable_objects']}))
