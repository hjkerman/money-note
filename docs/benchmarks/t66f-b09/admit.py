"""B09의 exact admission/직접 artifact/test 변경만 격리 후보에 적용한다."""
import pathlib,json,hashlib,base64,subprocess,os,gzip,difflib
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=pathlib.Path('/tmp/money-note-t66f-b09-20261026');C=W/'candidate';sha=lambda b:hashlib.sha256(b).hexdigest();NEW='5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c';OLD='f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3'
paths=['mobile/lib/src/segmented/protocol.dart','mobile/assets/segmented/isolated-release-artifacts.json','docs/specimens/t66d3b-release-artifacts.json','mobile/test/segmented_adapter_isolation_test.dart','mobile/test/segmented_engine_admission_b05a_test.dart']
assert not(E/'admission-consistency.json').exists();before={p:(C/p).read_bytes()if(C/p).exists()else None for p in paths};policy={p:(R/p).read_bytes()for p in paths}
for p,b in policy.items():q=C/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
for p in ['docs/benchmarks/t66f-b05a/source-lock-review.json','docs/benchmarks/t66f-b05a/mutation-witness.json']:
 q=C/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes((R/p).read_bytes())
code='import json;from isolated_sync.artifacts import release_bundle;print(json.dumps(release_bundle()))'
def bundle(T):return json.loads(subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=T,env={**os.environ,'PYTHONPATH':str(T/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},text=True))
new=bundle(C);assert new==bundle(C);old=bundle(W/'baseline');assert new['artifacts']['financial_engine']['sha256']==NEW
for k in ['raw_schema','projection_schema','policy_registry']:assert new['artifacts'][k]==old['artifacts'][k]
assert new['versions']==old['versions']
proto=policy[paths[0]].decode();fragments=[{'before':"  static const financialEngine =\n      '"+OLD+"';",'after':"  static const financialEngine =\n      '"+NEW+"';\n  static const b05FinancialEngine =\n      '"+OLD+"';"},{'before':'(context.engine != financialEngine &&','after':'(context.engine != financialEngine &&\n            context.engine != b05FinancialEngine &&'}]
for f in fragments:assert proto.count(f['before'])==1;proto=proto.replace(f['before'],f['after'],1)
preserved=[OLD,'7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c','afe26b70856b5a3fa06477641d91e8e1784e9184906281843f0a39a9c99cbdf5','f34aef259c801ada33ccb88cfb103ee6654fb4467c49a66ce509f2239ffe449d'];assert all(v in proto for v in preserved)
review={'authorization':'사용자 B09 §3: 검증 exact B08 추가와 직접 artifact/검사 전이만; isolated candidate only','protocol_before_sha256':sha(policy[paths[0]]),'protocol_sha256':sha(proto.encode()),'changes':fragments,'preserve_engines':preserved,'new_exact_engine':NEW,'previous_review':'docs/benchmarks/t66f-b05a/source-lock-review.json','no_other_exception':True};(E/'source-lock-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');q=C/'docs/benchmarks/t66f-b09';q.mkdir(parents=True);(q/'source-lock-review.json').write_bytes((E/'source-lock-review.json').read_bytes())
artifact=(json.dumps(new,ensure_ascii=False,separators=(',',':'))+'\n').encode();after={paths[0]:proto.encode(),paths[1]:artifact,paths[2]:artifact}
guard=policy[paths[3]].decode();needle="    expect(hash('mobile/lib/src/segmented/protocol.dart'),\n        admission['protocol_sha256']);\n    var restoredProtocol = read('mobile/lib/src/segmented/protocol.dart');"
replacement="""    final b09Admission = jsonDecode(read(
        'docs/benchmarks/t66f-b09/source-lock-review.json')) as Map;
    expect(hash('mobile/lib/src/segmented/protocol.dart'),
        b09Admission['protocol_sha256']);
    var restoredProtocol = read('mobile/lib/src/segmented/protocol.dart');
    for (final change in b09Admission['changes'] as List) {
      final after = change['after'] as String;
      expect(after.allMatches(restoredProtocol).length, 1);
      restoredProtocol = restoredProtocol.replaceFirst(after, change['before'] as String);
    }
    expect(sha256.convert(utf8.encode(restoredProtocol)).toString(),
        admission['protocol_sha256']);"""
assert guard.count(needle)==1;after[paths[3]]=guard.replace(needle,replacement).encode()
test=policy[paths[4]].decode();needle='  const accepted=[\n';assert test.count(needle)==1;test=test.replace(needle,needle+"    '"+NEW+"',\n",1);test=test.replace("for(final engine in ['0'*64,", "for(final engine in ['a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94','1'*64,'0'*64,");after[paths[4]]=test.encode()
for p,b in after.items():(C/p).write_bytes(b)
(E/'before').mkdir()
for i,p in enumerate(paths):
 for label,body in [('B08',before[p]),('current-policy',policy[p])]:
  if body is not None:(E/'before'/f'{i}-{label}.gz').write_bytes(gzip.compress(body,mtime=0))
(E/'admission.patch').write_text(''.join(''.join(difflib.unified_diff(policy[p].decode().splitlines(True),after[p].decode().splitlines(True),fromfile=p,tofile=p))for p in paths))
result={'status':'APPLIED — pending runtime tests','isolated_only':True,'baseline_engine':old['artifacts']['financial_engine']['sha256'],'B08_engine':NEW,'preserved_previous_engines':preserved,'accepted_after':[NEW]+preserved,'artifact_generation':'isolated_sync.artifacts.release_bundle; same compact JSON serialization as A02/B05A; twice deterministic','artifact_sha256':sha(artifact),'unchanged_artifacts':['raw_schema','projection_schema','policy_registry','versions'],'files':{p:{'B08_before':sha(before[p])if before[p]is not None else None,'current_policy_before':sha(policy[p]),'after':sha(after[p]),'reason':'exact admission'if p==paths[0]else'direct generated release artifact'if p in paths[1:3]else'direct exact SHA/source guard expectation'}for p in paths},'backend_delta':'only B08 app/db_migrations.py; observation.py original B03 bytes','B03_instrumentation_changed':False,'binding_changed':False,'live_source_changed':False};(E/'admission-consistency.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'applied_paths':paths,'engine':NEW,'artifact_sha':sha(artifact),'prior_engines_preserved':4}))
