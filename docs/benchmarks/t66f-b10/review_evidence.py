"""보존 JSON/JUnit/manifest만 재집계한다. 네트워크·제품 실행 없음."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as ET,collections,tarfile
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b10'
def load(p):return json.loads((R/p).read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def xml(p):
 r=ET.parse(R/p).getroot(); ts=list(r.iter('testcase'));return {'path':p,'sha256':sha((R/p).read_bytes()),'testcase_count':len(ts),'suite_total_including_subtests':sum(int(x.get('tests','0')) for x in r.iter('testsuite')),'failures':len(list(r.iter('failure'))),'errors':len(list(r.iter('error'))),'skips':len(list(r.iter('skipped')))}
inputs=set()
def used(p):inputs.add(p);return load(p)
b1=used('docs/benchmarks/t66f-b01-independent/summary.json'); b1xml=[xml('docs/benchmarks/t66f-b01-independent/evidence/full-'+str(i)+'.xml') for i in [1,2]]
for i,x in enumerate(b1xml,1):assert x['testcase_count']==1315 and x['suite_total_including_subtests']==2855 and not x['failures'] and not x['errors'];assert x['sha256']==b1['full-'+str(i)]['sha256'];assert b1['full-'+str(i)]['process']['exit']==0;inputs.add(x['path'])
for e in b1['evidence_manifest']:
 p='docs/benchmarks/t66f-b01-independent/'+e['file']; expected=e.get('sha256',e.get('persisted_sha256'));assert expected and sha((R/p).read_bytes())==expected;inputs.add(p)
b2=used('docs/benchmarks/t66f-b02-independent/summary.json');large=b2['large']['100000']; cold=large['cold_http'];assert cold['new_objects']==400532 and cold['object_payload_bytes']==261543083;assert len(cold['observations'])==3
final2=used('docs/benchmarks/t66f-b02-independent/final-state.json')['100000'];assert final2['status']=='PASS' and final2['sync_root_independently_verified'] and final2['receipt_target_matches']
execution2=used('docs/benchmarks/t66f-b02-independent/execution-100000.json');assert execution2['exit_code']==0 and execution2['ttl']==900 and execution2['max_observations']==3
used('docs/benchmarks/t66f-b02-independent/validation.json')
b3=used('docs/benchmarks/t66f-b03-ir07/evidence-manifest.json'); b3_count=0
for e in b3['files']:
 p=e['path'];expected=e.get('sha256',e.get('persisted_sha256'));assert expected and sha((R/p).read_bytes())==expected;inputs.add(p);b3_count+=1
used('docs/benchmarks/t66f-b03-ir07/test-results.json');used('docs/benchmarks/t66f-b03-ir07/integration-oracle.json');used('docs/benchmarks/t66f-b03-ir07/historical-finding-closure-matrix.json')
b4=used('docs/benchmarks/t66f-b04/run-manifest.json'); normal=[r for r in b4['runs'] if r.get('valid_for_binding_cost')];assert len(normal)==36
cells=[];zeros=['full_recoveries','full_verifications','full_raw_rows','full_fact_rows','canonical_full_builds']
for n in [1000,5000,10000,50000]:
 for op in ['no-change','card','cash']:
  matches=[r for r in normal if r['N']==n and r['workload'].replace('_','-')==op]
  # 원 manifest의 무변경 label은 identical이다.
  if op=='no-change' and not matches:matches=[r for r in normal if r['N']==n and r['workload'] in ['no_change','identical','unchanged']]
  assert len(matches)==3,(n,op,[r['workload'] for r in normal if r['N']==n])
  rawrecords=[]
  for m in matches:
   p=m['raw_path'];d=used(p);assert d['status']=='COMPLETED' and d['on'] and d['collector_closed'] and d['source_digest']==b4['source_digest'];assert all(d['stage_completion'][k] for k in ['E1','E2','E3','E4']);assert all(d['work'][k]==0 for k in zeros)
   assert d['backend']['measurement_complete'] and d['backend']['issued']==d['backend']['closed']
   rawrecords.append({'path':p,'run_id':m['run_id'],'trial':m['trial'],'elapsed_us':d['elapsed_us'],'accepted_id':d['accepted_after']['id'],'sequence':d['accepted_after']['sequence'],'full_N_counters':{k:d['work'][k] for k in zeros},'hot_raw_rows':d['work'].get('hot_raw_rows'),'tree_nodes_examined':d['work'].get('tree_nodes_examined'),'raw_entries_read':d['work'].get('raw_entries_read'),'backend_rows_counter_scope_ko':'실제 SQL 반환 행/계측 범위; VM/pager 전체 방문 행을 의미하지 않음'})
  cells.append({'N':n,'workload':op,'D':0 if op=='no-change' else 1,'ON_repetitions':3,'status':'PASS','scope_ko':'보존된 B04 정상 비용 cell; §35 전체 열 완료와 구분','raw':rawrecords})
for p in ['docs/benchmarks/t66f-b04/logical-costs.json','docs/benchmarks/t66f-b04/pairs.json','docs/benchmarks/t66f-b04/contract-matrix.json','docs/benchmarks/t66f-b04/fullscale-decision.json']:used(p)
p03=used('docs/benchmarks/t66f-b04/historical-p03.json');assert p03['staged']==397146 and p03['required']==400532 and not p03['E3_completed'] and not p03['E4_completed']
for key in ['source','full_analysis_source']:
 p=p03[key];assert sha((R/p).read_bytes())==p03['source_sha256' if key=='source' else 'full_analysis_sha256'];used(p)
b5=used('docs/benchmarks/t66f-b05/run-manifest.json');b5a=used('docs/benchmarks/t66f-b05a/run-manifest.json');b5b=used('docs/benchmarks/t66f-b05b/comparison-summary.json');used('docs/benchmarks/t66f-b05b/run-manifest.json')
for p in ['docs/benchmarks/t66f-b05a/raw/n5000-0-B-on/run.json','docs/benchmarks/t66f-b05a/raw/n5000-1-A-on/run.json','docs/benchmarks/t66f-b05b/raw/n5000-0-A-on/run.json','docs/benchmarks/t66f-b05b/raw/n5000-1-B-on/run.json']:used(p)
for p in ['docs/benchmarks/t66f-b06/critical-path-summary.json','docs/benchmarks/t66f-b06/measurement-inventory.json','docs/benchmarks/t66f-b07/run-manifest.json','docs/benchmarks/t66f-b07/call-path-attribution.json','docs/benchmarks/t66f-b07/verification.json','docs/benchmarks/t66f-b08/run-manifest.json','docs/benchmarks/t66f-b08/cache-safety-verification.json','docs/benchmarks/t66f-b08/post-verification.json']:used(p)
b8=used('docs/benchmarks/t66f-b08/packet-comparison.json');assert b8['A']['all_compilations']==46 and b8['B']['all_compilations']==1 and b8['A']['actual_DB_schema_inspections']==b8['B']['actual_DB_schema_inspections']==46
b9=used('docs/benchmarks/t66f-b09/run-manifest.json'); reg=used('docs/benchmarks/t66f-b09/regressions.json'); bx=xml(reg['backend']['xml']);inputs.add(bx['path']);assert bx['testcase_count']==1910 and bx['suite_total_including_subtests']==3450 and not bx['failures'] and not bx['errors'] and not bx['skips'];assert reg['backend']['passed']==1910 and reg['backend']['subtests_pass']==1540
flutter=[]
for label in ['flutter_affected','flutter_B08_mutated_source']:
 p=reg[label]['raw'];inputs.add(p);events=[json.loads(s) for s in (R/p).read_text().splitlines() if s.startswith('{')];done=[x for x in events if x.get('type')=='done'];assert done and done[-1]['success'];passed=[x for x in events if x.get('type')=='testDone' and x.get('result')=='success' and not x.get('hidden') and not x.get('skipped')];assert len(passed)==reg[label]['passed'];flutter.append({'path':p,'pass':len(passed),'done_success':True})
assert sum(x['pass'] for x in flutter)==209
runs=[]
for m in b9['runs']:
 p='docs/benchmarks/t66f-b09/raw/'+m['id']+'/run.json';d=used(p);o=used(str(Path(p).parent/'independent-verification.json'))
 assert d['valid_completed'] and all(d[x] for x in ['E1','E2','E3','E4']) and d['collector_closed'] and d['completed_objects']==4132 and d['accepted_after']['sequence']==1
 assert o['status']=='PASS' and o['matched_client_backend'] and o['objects']==4132 and o['accepted_native'][0]==d['accepted_after']['id']
 assert d['source_payload_sha']==m['source_payload_sha'] and d['engine_sha']==m['engine_sha']
 runs.append({'id':m['id'],'on':d['on'],'variant':d['variant'],'payload_sha256':d['source_payload_sha'],'engine_sha256':d['engine_sha'],'elapsed_us':d['end_to_end_with_bounded_E4_us'],'accepted_id':d['accepted_after']['id'],'objects':4132,'oracle_status':'PASS','raw':p})
perf=used('docs/benchmarks/t66f-b09/performance-disposition.json');assert perf['performance_label']=='MIXED' and perf['N5000_runs']==0
for pair in perf['basis']:
 a=next(r for r in runs if r['id']==pair['A']);b=next(r for r in runs if r['id']==pair['B']);value=100*(a['elapsed_us']-b['elapsed_us'])/a['elapsed_us'];assert abs(value-pair['improvement_pct'])<1e-10;assert pair['compilations_A_B']==[248,1] and pair['actual_inspections_A_B']==[248,248]
# source-lock의 정확한 역변환을 archive bytes에서 검증한다.
sources=load('docs/benchmarks/t66f-b10/source-certification-boundaries.json'); by={r['id']:r for r in sources['frozen_sources']}
def member(key,path):
 with tarfile.open(by[key]['archive']) as t:return t.extractfile('source/'+path).read()
pr='mobile/lib/src/segmented/protocol.dart';current=member('B09',pr).decode();r9=used('docs/benchmarks/t66f-b09/source-lock-review.json');assert sha(current.encode())==r9['protocol_sha256']
for fragment in reversed(r9['changes']):assert current.count(fragment['after'])==1;current=current.replace(fragment['after'],fragment['before'],1)
assert current.encode()==member('B05-A',pr)
r5=used('docs/benchmarks/t66f-b05a/source-lock-review.json')
assert sha(current.encode())==r5['protocol_sha256']
for fragment in reversed(r5['changes']):
 assert current.count(fragment['after'])==1;current=current.replace(fragment['after'],fragment['before'],1)
assert current.encode()==member('B03',pr)
for key in ['B05','B05-A','B08','B09']:
 for p in ['docs/benchmarks/t66f-b03/counters.py','mobile/test/support/logical_cost_sqlite.dart']:
  assert member(key,p)==member('B03',p)
result={'task':'T6.6F-B10','method_ko':'보존 archive/JSON/JUnit/Flutter 이벤트 재집계; 새 제품 시험·수집 없음','B01':{'status':'CLOSED','full_backend_XML':b1xml,'new_independent_pass':15,'source_ko':'당시 test-local lock 5초; production 1초와 strict [201]*4+[429] 보존'},'B02':{'status':'CLOSED','N100k_functional':'PASS','source_commit':'1cabf319f0ac2c2069e804b47cb527b55e3374db','raw_summary':'docs/benchmarks/t66f-b02-independent/summary.json','observations':len(cold['observations']),'cold_store_work':large['cold_store_work'],'publication_completed_s':large['publication_completed_s'],'cost_instrumentation_qualified':False},'B03_IR07':{'status':'CLOSED','retained_manifest_members_verified':b3_count,'new_material_contradiction':False,'retested':False},'B04':{'status':'PASS — BOUNDED','valid_ON_normal_raw_records':36,'measured_N':[1000,5000,10000,50000],'unmeasured_N':[100000],'cells':cells,'not_full_five_point_PASS':True},'historical_P03':p03,'B05':{'status':'EXPERIMENTAL — NOT ADOPTED','historical_artifact_failures':'보존; B05-A 별도 source에서 admission 자격 해결','system_benefit':'NOT ESTABLISHED','reversed_order_evidence':'docs/benchmarks/t66f-b05b/comparison-summary.json'},'B06_B07':{'status':'PASS — 해당 기존 자료 분석/제한 ASGI 귀속 범위','full_cold_proof':False},'B08':{'status':'EXPERIMENTAL — NOT ADOPTED','ASGI_compilations':[46,1],'actual_inspections':[46,46],'full_cold_proof':False},'B09':{'status':'PASS — ADMISSION AND REAL-PATH QUALIFICATION','backend_XML':bx,'backend_main_tests':1910,'backend_subtests':1540,'flutter_affected':flutter,'runs':runs,'performance':'MIXED','N5000':'NOT JUSTIFIED','source_lock_B09_inverse_to_B05A':True,'B03_core_instrumentation_identical':True},'tests_or_benchmarks_run_by_B10':0,'input_files':[{'path':p,'sha256':sha((R/p).read_bytes()),'bytes':(R/p).stat().st_size} for p in sorted(inputs)]}
(E/'evidence-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'B01_XML_runs':2,'IR07_manifest_files':b3_count,'B04_normal_ON_raw':len(normal),'B09_backend_entries':bx['testcase_count'],'B09_flutter':sum(x['pass'] for x in flutter),'B09_cold':len(runs),'new_runs':0}))
