"""실행 없이 동결 archive/source/engine 식별 층위를 확인한다."""
import base64,hashlib,json,pathlib,stat,subprocess,tarfile,os
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b06';sha=lambda b:hashlib.sha256(b).hexdigest()
S=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8');F=pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b05a/29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542')
cases=[('B03',S/'candidate.tar.gz',S.name,'fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5'),('B05',R/'docs/benchmarks/t66f-b05/experimental-source.tar.gz','d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae','745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e'),('B05A',F/'candidate.tar.gz',F.name,'b239b9d277e5fd747c2f85c5577f42e203ad7a737b29317f0e23581d6b13b0f1')]
records=[]
for name,path,payload,archiveSHA in cases:
 assert sha(path.read_bytes())==archiveSHA
 with tarfile.open(path) as t:
  m=json.loads(t.extractfile('metadata/source-manifest.json').read());entries=m['entries'];assert sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())==payload
  assert len(t.getnames())==len(set(t.getnames()))
  for a in entries:
   p=pathlib.PurePosixPath(a['path']);assert not p.is_absolute() and '..' not in p.parts;member=t.getmember('source/'+a['path']);b=t.extractfile(member).read();assert member.isfile() and member.mode==int(a['mode'],8) and sha(b)==a['sha256'] and len(b)==a['bytes']
  bundle=json.loads(t.extractfile('source/docs/specimens/t66d3b-release-artifacts.json').read());engineRaw=base64.b64decode(bundle['artifacts']['financial_engine']['data_base64']);engine=sha(engineRaw);assert engine==bundle['artifacts']['financial_engine']['sha256']
  engineValue=json.loads(engineRaw);sourceMap=engineValue['sources'];actualMap={};selected={a['path']:a for a in entries};gitSources=0
  for p,h in sourceMap.items():
   key='backend/'+p
   if key in selected:actualMap[p]=selected[key]['sha256']
   else:
    data=subprocess.check_output(['git','--no-optional-locks','-C',str(R),'show','ebcbd54d90eeee194a04b9eea6367f446ee2fd28:'+key],env={**os.environ,'GIT_OPTIONAL_LOCKS':'0'});actualMap[p]=sha(data);gitSources+=1
 actualEngine=sha(json.dumps({'profile':engineValue['profile'],'sources':actualMap},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode());mismatchedArtifactInputs=[p for p in actualMap if actualMap[p]!=sourceMap[p]]
 if name=='B05':assert mismatchedArtifactInputs==['isolated_sync/observation.py'] and actualEngine=='f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3'
 else:assert not mismatchedArtifactInputs and actualEngine==engine
 records.append({'name':name,'archive':str(path),'archive_sha256':archiveSHA,'payload_sha256':payload,'files':len(entries),'bytes':sum(a['bytes'] for a in entries),'actual_engine_sha256':actualEngine,'declared_release_engine_sha256':engine,'historical_B05_unadmitted_artifact':name=='B05','artifact_input_differences':mismatchedArtifactInputs,'engine_sha256':actualEngine,'engine_source_members_checked':len(sourceMap),'engine_source_baseline_git_fallback':gitSources,'verified':True})
root=R/'backend';paths=sorted((root/'app').rglob('*.py'))+sorted((root/'isolated_sync').glob('*.py'))+sorted((root/'app/services/judgment/messages').glob('*.yaml'));mapping={p.relative_to(root).as_posix():sha(p.read_bytes()) for p in paths};raw=json.dumps({'profile':'isolated-d3a/1','sources':mapping},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode();engine=sha(raw);assert engine==records[-1]['engine_sha256']
liveM=json.loads((F/'source-manifest.json').read_text());mismatch=[a['path'] for a in liveM['entries'] if not (R/a['path']).is_file() or sha((R/a['path']).read_bytes())!=a['sha256'] or stat.S_IMODE((R/a['path']).stat().st_mode)!=int(a['mode'],8)];assert not mismatch
result={'frozen':records,'live':{'candidate_payload':F.name,'matched_payload_files':905,'payload_mismatches':mismatch,'engine_sha256':engine,'optimization_file':'backend/isolated_sync/observation.py','optimization_sha256':sha((root/'isolated_sync/observation.py').read_bytes()),'admission_paths':['mobile/lib/src/segmented/protocol.dart','mobile/assets/segmented/isolated-release-artifacts.json','docs/specimens/t66d3b-release-artifacts.json'],'release_json_sha256':sha((R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes()),'experimental_not_adopted':True},'identity_layers_distinct':True,'product_import_or_execution':False,'original_B03_correctness':'CLOSED — IR07 original source; 재감사 없음'}
(E/'source-identities.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'archives_verified':len(records),'live_payload':F.name,'live_engine':engine,'product_executed':False}))
