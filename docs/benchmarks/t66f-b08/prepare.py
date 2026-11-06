"""원 B03 source와 보존 N1k fixture를 검증·복원한다. workload 실행 없음."""
import gzip,hashlib,json,os,pathlib,stat,tarfile,sqlite3,subprocess,shutil
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';W=pathlib.Path('/tmp/money-note-t66f-b08-20261026');T=W/'baseline'
S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8');sha=lambda b:hashlib.sha256(b).hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 assert not T.exists();T.mkdir()
 archive=S/'candidate.tar.gz';assert sha(archive.read_bytes())=='fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'
 with tarfile.open(archive) as tf:
  m=json.loads(tf.extractfile('metadata/source-manifest.json').read());assert sha(json.dumps(m['entries'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==S.name
  for a in m['entries']:
   rel=pathlib.PurePosixPath(a['path']);assert not rel.is_absolute() and '..' not in rel.parts
   tm=tf.getmember('source/'+a['path']);b=tf.extractfile(tm).read();assert tm.isfile() and sha(b)==a['sha256'] and len(b)==a['bytes'] and tm.mode==int(a['mode'],8)
   p=T/a['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(int(a['mode'],8))
 save(E/'baseline-source-manifest.json',m)
 h=R/'docs/benchmarks/t66f-b05a';ret=json.loads((h/'retained-fixtures.json').read_text())[0];b=gzip.decompress((h/ret['compressed_path']).read_bytes());assert sha((h/ret['compressed_path']).read_bytes())==ret['compressed_sha256'] and sha(b)==ret['source_sha256'] and len(b)==ret['source_bytes']
 fixture=W/'template-n1000.sqlite';fixture.write_bytes(b);f=json.loads((h/'fixture-n1000.json').read_text());assert f['N']==1000 and f['template_sha256']==sha(b)
 c=sqlite3.connect('file:'+str(fixture)+'?mode=ro',uri=True);assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('SELECT count(*) FROM ledger_entries').fetchone()[0]==1000;c.close()
 env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(T/'backend')}
 code="""import json,hashlib,sys,sqlite3,platform
from isolated_sync.observation import engine_artifact
from isolated_sync.artifacts import release_bundle
print(json.dumps(dict(engine_sha=hashlib.sha256(engine_artifact()).hexdigest(),python=sys.version,sqlite=sqlite3.sqlite_version,release_engine=release_bundle()['artifacts']['financial_engine']['sha256'],platform=platform.platform())))"""
 d=json.loads(subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=T,env=env,text=True));assert d['engine_sha']==d['release_engine']=='7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c' and d['python'].startswith('3.12.3') and d['sqlite']=='3.45.1'
 d.update({'payload_sha256':S.name,'archive':str(archive),'archive_sha256':sha(archive.read_bytes()),'files':len(m['entries']),'execution_tree':str(T),'fixture':{'N':1000,'H':{'current_ledger_rows':105,'other_authoritative_rows':35,'hot_bytes':87364,'control_bytes':3178},'D':None,'template_sha256':sha(b),'compressed_sha256':ret['compressed_sha256'],'preserved_manifest':'docs/benchmarks/t66f-b05a/fixture-n1000.json','preserved_database':'docs/benchmarks/t66f-b05a/'+ret['compressed_path'],'financial_raw_digest':sha(json.dumps(f['A']['graph']['raw_value_sha256'],sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()),'objects':f['A']['graph']['objects'],'body_bytes':f['A']['graph']['canonical_bytes']},'B03_counters_sha256':sha((T/'docs/benchmarks/t66f-b03/counters.py').read_bytes()),'free_disk':shutil.disk_usage(W).free,'product_source_changes':0})
 assert d['files']==899
 save(E/'preflight.json',d);print(json.dumps({'verified_source':d['payload_sha256'],'engine':d['engine_sha'],'fixture_sha256':sha(b),'N':1000,'new_packets':0}))
