"""B05-B 독립 출처·보존·동결 복원. 제품/과거 증거는 읽기만 한다."""
import gzip,hashlib,io,json,os,pathlib,shutil,stat,subprocess,tarfile,time,sqlite3,contextlib
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05b';W=pathlib.Path('/tmp/money-note-t66f-b05b-20261026');H=R/'docs/benchmarks/t66f-b05a'
sha=lambda b:hashlib.sha256(b).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def git(*a):return subprocess.check_output(['git','--no-optional-locks','-C',str(R),*a],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'})
def inventory():
 paths=set(git('ls-files','-z').split(b'\0'))|set(git('ls-files','--others','--exclude-standard','-z').split(b'\0'));d={}
 for b in sorted(paths):
  if not b:continue
  p=b.decode()
  if p.startswith('docs/benchmarks/t66f-b05b/') or p=='docs/t66f-b05b-independent-5k-on-ab-replication.md':continue
  q=R/p
  if q.is_file():d[p]={'sha256':sha(q.read_bytes()),'mode':format(stat.S_IMODE(q.stat().st_mode),'04o'),'bytes':q.stat().st_size}
 return d
if __name__=='__main__':
 assert not W.exists();W.mkdir()
 for p in ['raw','disposable','runtime','fixtures-n5000']:(W/p).mkdir()
 index=R/git('rev-parse','--git-path','index').decode().strip();index_bytes=index.read_bytes();(E/'original-index.bin').write_bytes(index_bytes)
 save(E/'preservation-before.json',{'head':git('rev-parse','HEAD').decode().strip(),'index_sha256':sha(index_bytes),'staged_entries_sha256':sha(git('ls-files','--stage','-z')),'staged_entries':git('ls-files','--stage','-z').decode().split('\0'),'files':inventory(),'disk':shutil.disk_usage(W)._asdict(),'time_unix':time.time(),'implementation_participation_in_supplied_session':'NONE','delegation':False})
 assert git('rev-parse','HEAD').decode().strip()=='ebcbd54d90eeee194a04b9eea6367f446ee2fd28'
 snapshots=[('B03',pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/candidate.tar.gz'),'fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5','8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8'),('B05',R/'docs/benchmarks/t66f-b05/experimental-source.tar.gz','745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e','d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae'),('B05A',pathlib.Path(json.loads((H/'freeze.json').read_text())['archive']),'b239b9d277e5fd747c2f85c5577f42e203ad7a737b29317f0e23581d6b13b0f1','29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542')]
 verified={};manifests={};sources={};base=git('archive','HEAD');baseline_inventory=json.loads((snapshots[0][1].parent/'freeze.json').read_text())['baseline_inventory']
 for name,archive,digest,payload in snapshots:
  assert sha(archive.read_bytes())==digest
  with tarfile.open(archive) as t:
   names=t.getnames();assert len(names)==len(set(names));m=json.loads(t.extractfile('metadata/source-manifest.json').read());entries=m['entries'];assert sha(json.dumps(entries,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode())==payload
   src={}
   for a in entries:
    p=pathlib.PurePosixPath(a['path']);assert not p.is_absolute() and '..' not in p.parts
    member=t.getmember('source/'+a['path']);assert member.isfile();b=t.extractfile(member).read();assert sha(b)==a['sha256'] and len(b)==a['bytes'] and member.mode==int(a['mode'],8);src[a['path']]=b
   assert len(src)==len(entries)
  manifests[name]=m;sources[name]=src
  if name in ['B03','B05A']:
   T=W/('baseline' if name=='B03' else 'candidate');T.mkdir()
   with tarfile.open(fileobj=io.BytesIO(base)) as t:t.extractall(T,filter='data')
   for a in entries:
    q=T/a['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(src[a['path']]);q.chmod(int(a['mode'],8))
   for a in entries:
    q=T/a['path'];assert sha(q.read_bytes())==a['sha256'] and stat.S_IMODE(q.stat().st_mode)==int(a['mode'],8)
   remainder=0
   for a in baseline_inventory:
    if a['path'] in src:continue
    q=T/a['path'];b=q.read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==a['git_blob'];remainder+=1
   (T/'.venv').symlink_to(R/'.venv',target_is_directory=True)
  verified[name]={'archive':str(archive),'archive_sha256':digest,'payload_sha256':payload,'files':len(entries),'bytes_modes':'PASS','remaining_baseline_verified':remainder if name!='B05' else None}
 # B05-A source archive metadata와 별도 manifest도 직접 일치한다.
 assert manifests['B05A']==json.loads((H/'candidate-source-manifest.json').read_text())
 changes={}
 for left,right in [('B03','B05'),('B05','B05A'),('B03','B05A')]:
  a=sources[left];b=sources[right];changes[left+'_'+right]=[{'path':p,'before':sha(a[p]) if p in a else None,'after':sha(b[p]) if p in b else None} for p in sorted(set(a)|set(b)) if a.get(p)!=b.get(p)]
 engine_diffs=[x for x in changes['B03_B05A'] if x['path'].startswith(('backend/app/','backend/isolated_sync/')) and x['path'].endswith(('.py','.yaml'))];assert [x['path'] for x in engine_diffs]==['backend/isolated_sync/observation.py']
 for p in ['docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b03/server.py','mobile/lib/src/diagnostics/logical_cost.dart','mobile/test/support/logical_cost_sqlite.dart']:
  assert sources['B03'].get(p)==sources['B05A'].get(p),(p,'instrumentation mismatch')
 save(E/'source-integrity.json',{'status':'PASS','frozen_candidate':'VERIFIED','archives':verified,'differences':changes,'engine_input_differences':engine_diffs,'B03_instrumentation':'UNCHANGED','implementation_modified':False})
 # 역사 retained fixture를 checksum 검증 후 그대로 복원한다. 현재 lease는 새 서버가 실제 UTC로 발급한다.
 retained=next(x for x in json.loads((H/'retained-fixtures.json').read_text()) if x['N']==5000);compressed=(H/retained['compressed_path']).read_bytes();assert sha(compressed)==retained['compressed_sha256'];data=gzip.decompress(compressed);assert sha(data)==retained['source_sha256'];(W/'fixtures-n5000/template-combined.sqlite').write_bytes(data)
 fixture=json.loads((H/'fixture-n5000.json').read_text());assert fixture['template_sha256']==sha(data);save(W/'fixtures-n5000/fixture.json',fixture)
 lib=gzip.decompress((H/'client-sqlite-library.so.gz').read_bytes());assert sha(lib)=='0f947ebe629e8d9d02d7f408bef36e056bfc63ea47e02e0d45a7bae454f04ace';(W/'runtime/libsqlite3.so').write_bytes(lib)
 original=json.loads((H/'run-manifest.json').read_text());old=sorted([r for r in original['runs'] if r['N']==5000 and r['on']],key=lambda r:r['ordinal']);assert [r['variant'] for r in old]==['B','A'];assert old[0]['end_utc']<old[1]['start_utc']
 for r in old:
  raw=json.loads((R/r['raw']).read_text());assert raw['start_utc']==r['start_utc'] and raw['end_to_end_with_bounded_E4_us']/1e6==r['end_to_end_s']
 # 기존 드라이버는 제품/계측을 바꾸지 않고 그대로 사용; plan의 출력/서버 경로만 task-owned다.
 client_paths=sorted((W/'candidate/mobile/lib').rglob('*.dart'))+[W/'candidate/mobile/assets/segmented/isolated-release-artifacts.json'];ci={p.relative_to(W/'candidate').as_posix():sha(p.read_bytes()) for p in client_paths};cs=sha(json.dumps(ci,sort_keys=True,separators=(',',':')).encode());assert cs==original['runs'][0]['client_source_digest']
 runs=[]
 for ordinal,v in enumerate(['A','B']):
  T=W/('baseline' if v=='A' else 'candidate');runid=f'n5000-{ordinal}-{v}-on';runs.append({'id':runid,'ordinal':ordinal,'N':5000,'variant':v,'on':True,'rep':0,'engine_sha':manifests['B05A']['baseline_engine' if v=='A' else 'optimized_engine'],'backend_tree':str(T),'fixture':str(W/'fixtures-n5000'),'out':str(W/'raw'/runid),'client_source_digest':cs,'backend_observation_sha256':sha((T/'backend/isolated_sync/observation.py').read_bytes())})
 save(E/'plan.json',{'N':5000,'scratch':str(W),'server':str(H/'server.py'),'runs':runs,'client_source_digest':cs,'original_order':[r['id'] for r in old],'reversed_order':['A','B'],'lease_seconds':900,'attempts':3,'max_full_cold_runs':2,'additional_repeats':0,'OFF_runs':0,'N10k_50k_100k':0,'client_component_inventory':ci,'historical_fixture':retained,'historical_raw':[r['raw'] for r in old]})
 save(E/'driver-identities.json',{str(p.relative_to(R)):sha(p.read_bytes()) for p in [H/'cold_test.dart',H/'server.py',R/'docs/benchmarks/t66f-b02-independent/oracle.py']})
 print(json.dumps({'source_integrity':'PASS','order':'historical B→A; new A→B','fixture_sha256':sha(data),'client_component_digest':cs,'disk_free':shutil.disk_usage(W).free}))
