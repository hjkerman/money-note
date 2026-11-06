"""완료/진단/미완료를 분리한 B04 결과·pair·논리비용 manifest."""
import collections,hashlib,json,math,pathlib,re,statistics,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04';DIGEST='8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8'
def read(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def summ(v):
 return {'n':len(v),'median':statistics.median(v),'nearest_rank_p95':sorted(v)[math.ceil(.95*len(v))-1],'min':min(v),'max':max(v)} if v else None
def values(c,term,prefix=''):
 return sum(int(v) for k,v in (c or {}).items() if k.endswith(term) and k.startswith(prefix))
def sql(c,outcome,prefix='',backend=False):
 if backend:pat=rf'/{outcome}/(?:blob_bytes|text_bytes)$'
 elif outcome in ('attempted','effective'):pat=rf'/{outcome}/(?:blobBytes|textBytes)$'
 else:pat=rf'/(?:blobBytes|textBytes)/{outcome}$'
 return sum(int(v) for k,v in (c or {}).items() if k.startswith(prefix) and re.search(pat,k))
runs=[];groups={};cohorts=[];logical=[];errors=[];pairs=[]
for root in sorted((E/'raw').glob('*')):
 if not root.is_dir():continue
 rows=[]
 for p in root.glob('*.json'):
  d=read(p)
  if 'run_id' not in d:continue
  controlled=root.name.endswith('-v3');complete=d['status']=='COMPLETED';counters_closed=d.get('collector_closed') and d.get('backend',{}).get('measurement_complete') and all(x['collector_closed'] and x['pending']==0 and x['completion_error'] is None for x in d.get('backend',{}).get('requests',[]))
  normal=controlled and not d['workload'].startswith('diagnostic_')
  role='binding-lower-N' if normal else 'diagnostic-only'
  row={'cohort':root.name,'run_id':d['run_id'],'N':d['N'],'H':{**d['H'],'initial_hot_bytes':read(root/'fixture.json')['hot_bytes'],'initial_control_bytes':read(root/'fixture.json')['control_bytes']},'D':d['D'],'workload':d['workload'],'trial':d['trial'],'on':d['on'],'status':d['status'],'role':role,'valid_completed':bool(complete and counters_closed),'valid_for_binding_cost':bool(normal and complete and counters_closed and d['workload']!='cold' and d['on']),'valid_for_perturbation':bool(normal and complete and counters_closed and d['http']['errors']==0),'fixture_digest':d['fixture_digest'],'source_digest':d['source_digest'],'raw_path':str(p.relative_to(R)),'accepted_before':d['accepted_before'],'accepted_after':d.get('accepted_after'),'start_utc':d['start_utc'],'end_utc':d.get('end_utc'),'elapsed_us':d.get('elapsed_us'),'http_errors':d.get('http',{}).get('errors'),'observation_expired':d.get('observation_expired'),'collector_closed':bool(counters_closed),'completed_object_count':d.get('db_after',{}).get('objects'),'new_immutable_objects':d.get('new_immutable_objects'),'stage_completion':d.get('stage_completion')}
  runs.append(row);rows.append(d)
  if complete and counters_closed and controlled:
   assert d['source_digest']==DIGEST
   if d['on']:
    client=d['logical_counters'];back=d['backend']['counters'];s=d['sql_counters'];item={'cohort':root.name,'N':d['N'],'workload':d['workload'],'trial':d['trial'],'new_immutable_objects':d['new_immutable_objects'],'db_object_blob_delta':d['db_after']['body_bytes']-d['db_before']['body_bytes'],'client_hash_input_bytes':values(client,'hashInputBytes'),'client_validation_submitted_bytes':values(client,'submittedBytes'),'client_validation_completed_bytes':values(client,'completedBytes'),'client_failed_submitted_bytes':values(client,'failedSubmittedBytes'),'backend_hash_input_bytes':values(back,'hash_input_bytes'),'backend_validation_submitted_bytes':values(back,'submitted_bytes'),'backend_validation_completed_bytes':values(back,'completed_bytes'),'client_SQL_logical_payload':{o:sql(s,o) for o in ('attempted','effective','committed','rolledBack','statementRolledBack','rolledBackOnClose')},'backend_SQL_logical_payload':{o:sql(back,o,backend=True) for o in ('attempted','effective','committed','rolled_back','statement_rolled_back','rolled_back_on_close')},'E1_objects_BLOB':{o:values(s,f'/objects/INSERT/{o}/blobBytes') if o in ('attempted','effective') else values(s,f'/objects/INSERT/blobBytes/{o}') for o in ('attempted','effective','committed')},'stages':{},'work':d['work'],'backend_D3':d['backend']['d3'],'raw_path':str(p.relative_to(R))}
    for st in ('recovery','e2','e3Verify','e3Prepare','e3Commit','e4Read'):
     item['stages'][st]={'hash_input_bytes':values(client,'hashInputBytes',st+'/'),'validation_submitted_bytes':values(client,'submittedBytes',st+'/'),'validation_completed_bytes':values(client,'completedBytes',st+'/'),'sql_payload':{o:sql(s,o,st+'/') for o in ('attempted','effective','committed','rolledBack','statementRolledBack','rolledBackOnClose')}}
    assert item['E1_objects_BLOB']['committed']==item['db_object_blob_delta']
    assert item['client_failed_submitted_bytes']==0
    if d['workload']!='cold':
     assert all(d['work'].get(k,0)==0 for k in ('full_recoveries','full_verifications','full_raw_rows','full_fact_rows','canonical_full_builds'))
    logical.append(item)
 for kind in sorted({d['workload'] for d in rows}):
  for trial in range(1 if kind=='cold' else 3):
   candidates={d['on']:d for d in rows if d['workload']==kind and d['trial']==trial and d['status']=='COMPLETED'}
   if len(candidates)!=2:continue
   off,on=candidates[False],candidates[True]
   same={k:off[k]==on[k] for k in ('expected_target','fixture_digest','source_digest','db_before','db_after','e4_values')}
   same['accepted_before_target']=off['accepted_before']['target']==on['accepted_before']['target'];same['relative_sequence']=off['accepted_before']['sequence']==on['accepted_before']['sequence'] and off['accepted_after']['sequence']==on['accepted_after']['sequence']
   assert all(same.values()),(root.name,kind,trial,same)
   def metric(d):
    b=d['backend']['requests'];return {'end_to_end_us':d['elapsed_us'],'backend_handler_us':sum(r['wall_ns'] for r in b)/1000,'backend_process_cpu_us':sum(r['process_cpu_ns'] for r in b)/1000,'HTTP_complete_body_us':d['http']['send_to_complete_body_us'],'HTTP_failed_send_us':d['http'].get('failed_send_us'),'E1_SQL_API_us':d['e1_sql_api_publication_us'],'publication_transaction_us':d['publication_transaction_us'],'publication_readback_us':d['publication_readback_us'],'E4_read_us':d['e4_elapsed_us'],'client_process_cpu_us_tick10ms':d['process_cpu_us_tick_10ms']}
   a,b=metric(off),metric(on);pair={'cohort':root.name,'N':on['N'],'workload':kind,'trial':trial,'role':'controlled' if root.name.endswith('-v3') and not kind.startswith('diagnostic_') else 'diagnostic-only','equivalence':same,'order':'OFF→ON' if off['start_utc']<on['start_utc'] else 'ON→OFF','OFF':a,'ON':b,'difference':{k:b[k]-a[k] if a[k] is not None and b[k] is not None else None for k in a},'ratio':{k:b[k]/a[k] if a[k] else None for k in a},'HTTP_errors':{'OFF':off['http']['errors'],'ON':on['http']['errors']},'completed_objects':on['db_after']['objects'],'valid':root.name.endswith('-v3') and not kind.startswith('diagnostic_') and off['http']['errors']==on['http']['errors']==0}
   pairs.append(pair)
 for f in ('failure.json','summary.json'):
  if(root/f).exists():cohorts.append({'cohort':root.name,'file':str((root/f).relative_to(R)),'data':read(root/f)})
summary=[]
for n in (1000,5000,10000,50000):
 for kind in ('cold','no_change','card','cash'):
  p=[x for x in pairs if x['N']==n and x['workload']==kind and x['valid']]
  if not p:continue
  summary.append({'N':n,'workload':kind,'pairs':len(p),'OFF_seconds':summ([x['OFF']['end_to_end_us']/1e6 for x in p]),'ON_seconds':summ([x['ON']['end_to_end_us']/1e6 for x in p]),'ratio':summ([x['ratio']['end_to_end_us'] for x in p]),'difference_seconds':summ([x['difference']['end_to_end_us']/1e6 for x in p]),'backend_OFF_seconds':summ([x['OFF']['backend_handler_us']/1e6 for x in p]),'backend_ON_seconds':summ([x['ON']['backend_handler_us']/1e6 for x in p]),'backend_ratio':summ([x['ratio']['backend_handler_us'] for x in p]),'E1_SQL_ratio':summ([x['ratio']['E1_SQL_API_us'] for x in p]),'E3_transaction_ratio':summ([x['ratio']['publication_transaction_us'] for x in p]),'E4_read_ratio':summ([x['ratio']['E4_read_us'] for x in p])})
manifest={'schema_version':1,'generated_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'source_digest':DIGEST,'elapsed_boundary':'AppState.publishSegmentedForIsolatedUse return: segmented-internal accepted publication; actual UI/Offline-ready completion NOT MEASURED','binding_N':[1000,5000,10000,50000,100000],'binding_numeric_H':None,'binding_numeric_D':None,'experimental_H':{'current_ledger':105,'other_rows':35,'initial_hot_bytes':87364,'control_bytes':3178},'experimental_D':{'no_change':0,'card':1,'cash':1},'N100k_cold_attempts':0,'runs':runs,'cohort_records':cohorts,'valid_controlled_completed_runs':sum(x['valid_completed'] and x['role']=='binding-lower-N' for x in runs),'valid_controlled_pairs':sum(x['valid'] for x in pairs),'diagnostic_completed_runs':sum(x['valid_completed'] and x['role']=='diagnostic-only' for x in runs),'incomplete_workload_runs':sum(x['status']!='COMPLETED' for x in runs),'unexecuted_binding_points':[n for n in (1000,5000,10000,50000,100000) if not any(x['N']==n and x['valid_for_binding_cost'] for x in runs)],'limitations':['generation ON only, not paired','E2 wall and E3Verify/Prepare exclusive wall not directly isolated','SQL API is inclusive of observer callback lower bound','no physical IO or Android measurements','n=3 p95 is sample maximum, no population confidence bound']}
manifest['diagnostic_publication_pairs']=sum(p['role']=='diagnostic-only' for p in pairs)
manifest['stage_diagnostic_files']=[str(p.relative_to(R)) for p in sorted((E/'raw').glob('*/stage-*.json')) if 'diagnostic_id' in read(p)]
save(E/'run-manifest.json',manifest);save(E/'pairs.json',pairs);save(E/'logical-costs.json',logical);save(E/'timing-summary.json',summary)
print(json.dumps({k:manifest[k] for k in ('valid_controlled_completed_runs','valid_controlled_pairs','diagnostic_completed_runs','incomplete_workload_runs','unexecuted_binding_points')}))
