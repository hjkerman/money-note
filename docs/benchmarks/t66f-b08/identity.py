"""B08 source/engine/기존 release 선언을 서로 다른 신원 층으로 기록한다."""
import pathlib,json,hashlib,stat,copy,subprocess,os,tarfile,gzip,io
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08';W=pathlib.Path('/tmp/money-note-t66f-b08-20261026');sha=lambda b:hashlib.sha256(b).hexdigest()
def save(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
m=json.loads((E/'baseline-source-manifest.json').read_text());entries=copy.deepcopy(m['entries']);expected={x['path']:x for x in entries};changes=[]
for a in entries:
 p=W/'baseline'/a['path'];assert sha(p.read_bytes())==a['sha256'] and stat.S_IMODE(p.stat().st_mode)==int(a['mode'],8)
 p=W/'candidate'/a['path'];h=sha(p.read_bytes())
 if h!=a['sha256']:changes.append(a['path']);a['sha256']=h;a['bytes']=p.stat().st_size
assert changes==['backend/app/db_migrations.py']
new='backend/tests/test_expected_revision_contract_reuse.py';p=W/'candidate'/new;entries.append({'path':new,'mode':format(stat.S_IMODE(p.stat().st_mode),'04o'),'sha256':sha(p.read_bytes()),'bytes':p.stat().st_size});entries.sort(key=lambda x:x['path']);payload=sha(json.dumps(entries,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode())
engines={}
for v,t in [('A',W/'baseline'),('B',W/'candidate')]:
 root=t/'backend';paths=sorted((root/'app').rglob('*.py'))+sorted((root/'isolated_sync').glob('*.py'))+sorted((root/'app/services/judgment/messages').glob('*.yaml'));mapping={p.relative_to(root).as_posix():sha(p.read_bytes())for p in paths};raw=json.dumps({'profile':'isolated-d3a/1','sources':mapping},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode();actual=sha(raw);declared=json.loads((t/'docs/specimens/t66d3b-release-artifacts.json').read_text())['artifacts']['financial_engine']['sha256'];engines[v]={'engine_sha256':actual,'declared_release_engine':declared,'release_equals_current_engine':actual==declared,'members':len(mapping),'input_sha':mapping,'payload_sha256':m.get('canonical_payload_sha256','8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8') if v=='A' else payload}
assert engines['A']['engine_sha256']=='7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c' and engines['A']['release_equals_current_engine'] and not engines['B']['release_equals_current_engine']
assert [k for k,v in engines['A']['input_sha'].items()if engines['B']['input_sha'][k]!=v]==['app/db_migrations.py']
# 실제 product artifact 계산도 독립 source-map 결과와 대조한다.
code='from isolated_sync.observation import engine_artifact;import hashlib;print(hashlib.sha256(engine_artifact()).hexdigest())'
for v,t in [('A',W/'baseline'),('B',W/'candidate')]:assert subprocess.check_output([str(R/'.venv/bin/python'),'-c',code],cwd=t,env={**os.environ,'PYTHONPATH':str(t/'backend'),'PYTHONDONTWRITEBYTECODE':'1'},text=True).strip()==engines[v]['engine_sha256']
manifest={'status':'EXPERIMENTAL — NOT IR07 AUDITED, ENGINE NOT ADMITTED','baseline_commit':'ebcbd54d90eeee194a04b9eea6367f446ee2fd28','baseline_payload_sha256':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','payload_sha256':payload,'engine_sha256':engines['B']['engine_sha256'],'entries':entries,'file_count':len(entries),'bytes':sum(a['bytes']for a in entries),'product_changed':changes,'dedicated_tests':[new],'tracked_deletions':[],'release_artifacts':'unchanged original baseline; deliberate unadmitted experimental engine','reconstruction':'git archive baseline_commit → source/ overlay; verify entries; required unchanged baseline fixtures supplied by Git tree'}
save('candidate-source-manifest.json',manifest);save('source-identities.json',engines)
sumry=json.loads((E/'source-diff-summary.json').read_text());sumry.update(candidate_payload_sha256=payload,candidate_engine_sha256=engines['B']['engine_sha256'],dedicated_test_paths=[new],file_count=len(entries),candidate_only_in_scratch=True,live_product_source_changed=False);save('source-diff-summary.json',sumry)
print(json.dumps({'baseline_engine':engines['A']['engine_sha256'],'candidate_engine':engines['B']['engine_sha256'],'candidate_payload':payload,'files':len(entries),'engine_input_delta':changes,'release_guard':'baseline match; candidate exact mismatch preserved'}))
