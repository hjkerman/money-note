"""B05-A 사용자 명시 승인 범위만 적용. engine은 실제 source로 독립 재계산한다."""
import base64,difflib,gzip,hashlib,json,pathlib,subprocess,os
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05a';W=pathlib.Path('/tmp/money-note-t66f-b05a-20261026');sha=lambda b:hashlib.sha256(b).hexdigest()
def encoded(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def source_engine(tree):
 root=tree/'backend';paths=sorted((root/'app').rglob('*.py'))+sorted((root/'isolated_sync').glob('*.py'))+sorted((root/'app/services/judgment/messages').glob('*.yaml'))
 value={'profile':'isolated-d3a/1','sources':{p.relative_to(root).as_posix():sha(p.read_bytes()) for p in paths}}
 raw=encoded(value);return value,raw,sha(raw)
def bundle(tree):
 return json.loads(subprocess.check_output([str(R/'.venv/bin/python'),'-c','import json;from isolated_sync.artifacts import release_bundle; print(json.dumps(release_bundle()))'],env={**os.environ,'PYTHONPATH':str(tree/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},cwd=tree))
assert not (E/'admission-review.json').exists()
a,rawA,engineA=source_engine(W/'baseline');b,rawB,engineB=source_engine(W/'candidate');old=bundle(W/'baseline');new=bundle(W/'candidate')
assert sha(base64.b64decode(new['artifacts']['financial_engine']['data_base64']))==engineB and base64.b64decode(new['artifacts']['financial_engine']['data_base64'])==rawB
proposal=json.loads((R/'docs/benchmarks/t66f-b05/admission-proposal.json').read_text());assert engineB==proposal['new_exact_engine'];assert engineA==proposal['preserve_existing_exact_engines'][0]
changes={k:{'before':a['sources'].get(k),'after':b['sources'].get(k)} for k in a['sources'].keys()|b['sources'].keys() if a['sources'].get(k)!=b['sources'].get(k)};assert changes==proposal['changed_engine_sources']
assert new==bundle(W/'candidate') and new==json.loads((R/'docs/benchmarks/t66f-b05/proposed-release-bundle.json').read_text())
assert old['versions']==new['versions']
for k in ['raw_schema','projection_schema','policy_registry']:assert old['artifacts'][k]==new['artifacts'][k]
paths=['mobile/lib/src/segmented/protocol.dart','mobile/assets/segmented/isolated-release-artifacts.json','docs/specimens/t66d3b-release-artifacts.json','mobile/test/segmented_adapter_isolation_test.dart']
assert paths[:3]==proposal['proposed_additional_files'][:3]
before={p:(R/p).read_bytes() for p in paths};assert json.loads(before[paths[1]])==json.loads(before[paths[2]])==old
for p,body in before.items():
 dest=E/'before'/p;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(gzip.compress(body,mtime=0))
protocol=before[paths[0]].decode();fragments=[{'before':"  static const financialEngine =\n      '"+engineA+"';",'after':"  static const financialEngine =\n      '"+engineB+"';\n  static const b04FinancialEngine =\n      '"+engineA+"';"},{'before':'(context.engine != financialEngine &&','after':'(context.engine != financialEngine &&\n            context.engine != b04FinancialEngine &&'}]
for f in fragments:assert protocol.count(f['before'])==1;protocol=protocol.replace(f['before'],f['after'],1)
for old_engine in proposal['preserve_existing_exact_engines']:assert old_engine in protocol
review={'authorization':'사용자 T6.6F-B05-A §0·§5·§6·§20: 검증된 exact engine 추가와 직접 artifact/기대값만','baseline_engine':engineA,'optimized_engine':engineB,'protocol_before_sha256':sha(before[paths[0]]),'protocol_sha256':sha(protocol.encode()),'changes':fragments,'original_review':'docs/benchmarks/t66f-b02-a02-correction/source-lock-review.json','original_review_sha256':sha((R/'docs/benchmarks/t66f-b02-a02-correction/source-lock-review.json').read_bytes()),'no_other_lock_exception':True}
(E/'source-lock-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
artifact=(json.dumps(new,ensure_ascii=False,separators=(',',':'))+'\n').encode()
isolation=before[paths[3]].decode();needle="    expect(hash('mobile/lib/src/segmented/protocol.dart'),\n        reviewed['protocol_sha256']);"
replacement="""    final admission = jsonDecode(read(
        'docs/benchmarks/t66f-b05a/source-lock-review.json')) as Map;
    expect(hash('mobile/lib/src/segmented/protocol.dart'),
        admission['protocol_sha256']);
    var restoredProtocol = read('mobile/lib/src/segmented/protocol.dart');
    for (final change in admission['changes'] as List) {
      final after = change['after'] as String;
      expect(after.allMatches(restoredProtocol).length, 1);
      restoredProtocol = restoredProtocol.replaceFirst(
          after, change['before'] as String);
    }
    expect(sha256.convert(utf8.encode(restoredProtocol)).toString(),
        reviewed['protocol_sha256']);"""
assert isolation.count(needle)==1;isolation=isolation.replace(needle,replacement)
after={paths[0]:protocol.encode(),paths[1]:artifact,paths[2]:artifact,paths[3]:isolation.encode()}
for p,body in after.items():
 (R/p).write_bytes(body);(W/'candidate'/p).write_bytes(body)
q=W/'candidate/docs/benchmarks/t66f-b05a';q.mkdir(parents=True,exist_ok=True);(q/'source-lock-review.json').write_bytes((E/'source-lock-review.json').read_bytes())
(E/'authorized-change-inventory.json').write_text(json.dumps({'existing_paths':paths,'new_paths':['mobile/test/segmented_engine_admission_b05a_test.dart','backend/tests/test_engine_admission_b05a.py','docs/benchmarks/t66f-b05a/'],'allowed_product_source_change':'정확한 engine 상수/동등 비교 항목만; _lookup/B03 변경 없음','proposal_reviewed':True},ensure_ascii=False,indent=2)+'\n')
(E/'admission-review.json').write_text(json.dumps({'baseline_engine':engineA,'optimized_engine':engineB,'baseline_payload':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','B05_payload':'d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae','source_changes':changes,'engine_procedure':'SHA256(C1({profile:isolated-d3a/1,sources:path→SHA256(actual source bytes)})); backend/app/**/*.py + isolated_sync/*.py + judgment/messages/*.yaml','independent_stdlib_encoder_matches_backend':True,'deterministic_generation':True,'unchanged':['versions','raw_schema','projection_schema','policy_registry'],'preserved_engines':proposal['preserve_existing_exact_engines'],'files':{p:{'before':sha(before[p]),'after':sha(after[p]),'class':'checked-in release-facing' if 'artifacts.json' in p else 'exact admission' if p==paths[0] else 'direct source-lock test'} for p in paths},'generator':'isolated_sync.artifacts.release_bundle + 기존 A02 exact JSON serialization','runtime':'CPython3.12.3 / Flutter3.47.4 / Dart3.13.3; 합성 isolated protocol 전용, production 활성화 없음'},ensure_ascii=False,indent=2)+'\n')
(E/'admission.patch').write_text(''.join(''.join(difflib.unified_diff(before[p].decode().splitlines(True),after[p].decode().splitlines(True),fromfile=p,tofile=p)) for p in paths))
mutated=json.loads(rawB);mutated['sources']['isolated_sync/observation.py']='0'*64;unknown=sha(encoded(mutated));(E/'mutation-witness.json').write_text(json.dumps({'mutated_source_engine_sha':unknown,'approved_engine':engineB,'different':unknown!=engineB,'mutation':'source manifest 내 observation.py SHA를 변경; 제품 파일은 수정하지 않음'})+'\n')
print(json.dumps({'baseline_engine':engineA,'optimized_engine':engineB,'authorized_existing_paths':paths,'artifacts_sha256':sha(artifact)}))
