"""검증 Git tree와 원 B03/B08 source overlay를 격리 복원한다."""
import pathlib,subprocess,os,hashlib,json,tarfile,io,stat,gzip,shutil
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=pathlib.Path('/tmp/money-note-t66f-b09-20261026');S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8');sha=lambda b:hashlib.sha256(b).hexdigest()
base=subprocess.check_output(['git','--no-optional-locks','archive','ebcbd54d90eeee194a04b9eea6367f446ee2fd28'],cwd=R,env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'});inventory=json.loads((S/'freeze.json').read_text())['baseline_inventory'];sources={};recs={}
for v,path,digest,payload in [('A',S/'candidate.tar.gz','fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5',S.name),('B',R/'docs/benchmarks/t66f-b08/experimental-source.tar.gz','cb89861bedaa998ce3c53789f76ba92a412c4eeff9a05f34a1f49d8b25067e22','a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94')]:
 assert sha(path.read_bytes())==digest;T=W/('baseline'if v=='A'else'candidate');T.mkdir()
 with tarfile.open(fileobj=io.BytesIO(base))as t:t.extractall(T,filter='data')
 with tarfile.open(path)as t:
  m=json.load(t.extractfile('metadata/source-manifest.json'));entries=m['entries'];assert sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==payload;src={}
  for a in entries:
   pp=pathlib.PurePosixPath(a['path']);assert not pp.is_absolute()and'..'not in pp.parts;member=t.getmember('source/'+a['path']);b=t.extractfile(member).read();assert sha(b)==a['sha256']and len(b)==a['bytes']and member.mode==int(a['mode'],8);q=T/a['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b);q.chmod(int(a['mode'],8));src[a['path']]=b
 for a in inventory:
  if a['path']not in src:
   data=(T/a['path']).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==a['git_blob']
 root=T/'backend';paths=sorted((root/'app').rglob('*.py'))+sorted((root/'isolated_sync').glob('*.py'))+sorted((root/'app/services/judgment/messages').glob('*.yaml'));mapping={p.relative_to(root).as_posix():sha(p.read_bytes())for p in paths};engine=sha(json.dumps({'profile':'isolated-d3a/1','sources':mapping},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode());expected='7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c'if v=='A'else'5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c';assert engine==expected
 (T/'.venv').symlink_to(R/'.venv',target_is_directory=True);sources[v]=src;recs[v]={'payload':payload,'engine':engine,'archive_sha256':digest,'files':len(entries),'engine_inputs':mapping,'source_manifest_entries':entries}
 assert sha((T/'backend/isolated_sync/observation.py').read_bytes())=='635e17038f4cc11d7db59dd6208aa1d1fbfd5a5750b04b20c40cc7714c399a3e'
delta=[k for k,h in recs['A']['engine_inputs'].items()if recs['B']['engine_inputs'][k]!=h];assert delta==['app/db_migrations.py']
for p in ['docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b03/server.py','mobile/lib/src/diagnostics/logical_cost.dart','mobile/test/support/logical_cost_sqlite.dart']:assert sources['A'][p]==sources['B'][p]
(E/'source-reconstruction.json').write_text(json.dumps({'verified':True,'variants':recs,'engine_delta':delta,'B05_lookup_not_included':True,'B03_instrumentation_identical':True,'Git_baseline_archive':True},ensure_ascii=False,indent=2)+'\n')
for n in [1000,5000]:
 d=W/f'fixtures-n{n}';d.mkdir();ret=next(v for v in json.loads((R/'docs/benchmarks/t66f-b05a/retained-fixtures.json').read_text())if v['N']==n);z=R/'docs/benchmarks/t66f-b05a'/ret['compressed_path'];assert sha(z.read_bytes())==ret['compressed_sha256'];raw=gzip.decompress(z.read_bytes());assert sha(raw)==ret['source_sha256'];(d/'original-template.sqlite').write_bytes(raw)
(W/'runtime').mkdir();raw=gzip.decompress((R/'docs/benchmarks/t66f-b05a/client-sqlite-library.so.gz').read_bytes());assert sha(raw)=='0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace';(W/'runtime/libsqlite3.so').write_bytes(raw)
print(json.dumps({'source':'VERIFIED','backend_delta':delta,'A_engine':recs['A']['engine'],'B_engine':recs['B']['engine'],'free_disk':shutil.disk_usage(W).free}))
