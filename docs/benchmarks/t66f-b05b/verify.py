"""종료한 두 cold의 실제 graph·native accepted·금융 body와 B03 accounting을 독립 확인."""
import contextlib,gzip,hashlib,importlib.util,json,pathlib,shutil,sqlite3,time
from datetime import datetime
from prepare import R,E,W,H,sha,save
spec=importlib.util.spec_from_file_location('b05b_retained_independent_oracle',R/'docs/benchmarks/t66f-b02-independent/oracle.py');oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
def counters(d):
 cl=d['logical_counters'];be=d['backend']['counters'];sq=d['sql_counters']
 return {'client_hash_input_bytes':sum(int(v) for k,v in cl.items() if k.endswith('/hashInputBytes')),'client_primary_validation_input_bytes':sum(int(v) for k,v in cl.items() if k.endswith('/submittedBytes')),'backend_hash_input_bytes':sum(int(v) for k,v in be.items() if k.endswith('/sha256/hash_input_bytes')),'backend_primary_validation_input_bytes':sum(int(v) for k,v in be.items() if k.endswith('/json/submitted_bytes')),'SQL_logical':{kind:{metric:sum(int(v) for k,v in sq.items() if (('/'+kind+'/' in k and k.endswith('/'+metric)) if kind!='committed' else k.endswith('/'+metric+'/committed'))) for metric in ['textBytes','blobBytes','scalarValues','nullValues']} for kind in ['attempted','effective','committed']},'objects_committed_blob_bytes':sum(int(v) for k,v in sq.items() if '/objects/INSERT/blobBytes/committed' in k),'client_by_stage':cl,'SQL_by_stage':sq,'backend_by_stage':be}

def verify():
 execution=json.loads((E/'execution.json').read_text());assert execution['status']=='COMPLETED' and execution['exit_code']==0
 plan=json.loads((E/'plan.json').read_text());fixture=json.loads((H/'fixture-n5000.json').read_text());runs=[];hashsets={};costs=[]
 historical=json.loads((H/'run-manifest.json').read_text());historic={x['variant']:json.loads((R/x['raw']).read_text()) for x in historical['runs'] if x['N']==5000 and x['on']}
 assert len(plan['runs'])==2
 for cfg in plan['runs']:
  out=pathlib.Path(cfg['out']);d=json.loads((out/'run.json').read_text());completion=json.loads((out/'completion.json').read_text());assert completion=={'status':'COMPLETED','server_exit':0};assert d['status']=='COMPLETED' and d['valid_completed'] and all(d[k] for k in ['E1','E2','E3','E4']);assert d['engine_sha']==cfg['engine_sha']==d['accepted_after']['target']['context']['financial_engine']
  target=d['accepted_after']['target'];assert target==fixture[cfg['variant']]['manifest']['target'];assert d['accepted_before']=={'id':None,'sequence':0,'previous_id':None,'target':None};assert d['db_before']['objects']==d['db_before']['body_bytes']==d['db_before']['generations']==0;assert d['accepted_after']['sequence']==1 and d['accepted_after']['previous_id'] is None
  assert d['completed_objects']==d['staged_objects']==d['committed_generation_objects']==fixture[cfg['variant']]['graph']['objects']==20148
  assert d['semantic_digest']==historic[cfg['variant']]['semantic_digest'];assert d['fixture_digest']==historic[cfg['variant']]['fixture_digest'] and d['template_sha256']==historic[cfg['variant']]['template_sha256']
  assert d['collector_closed'] and d['backend']['measurement_complete'] and d['backend']['issued']==d['backend']['closed'];reqs=d['backend']['requests'];assert all(x['collector_closed'] and x['pending']==0 and x['completion_error'] is None and x['error'] is None and x['status']<400 for x in reqs);assert not d['observation_expired'];assert d['HTTP']['errors']==0 and d['HTTP']['issued']==d['HTTP']['complete_bodies']==len(reqs)
  manifests=[x['manifest'] for x in reqs if x.get('manifest')];leases=[]
  for m in manifests:
   seconds=(datetime.fromisoformat(m['expires_at'].replace('Z','+00:00'))-datetime.fromisoformat(m['validated_at'].replace('Z','+00:00'))).total_seconds();assert seconds==900;lease={k:m[k] for k in ['observation_id','validated_at','expires_at']}
   if lease not in leases:leases.append(lease)
  assert 1<=len({m['observation_id'] for m in manifests})<=3;assert all(status=='retired' for status,n in d['backend_final']['observations']);assert d['backend_final']['quick_check']==[['ok']] and not d['backend_final']['foreign_key_check']
  detail={};sets={};client=pathlib.Path(d['client_db_path']);assert client.is_relative_to(W/'disposable')
  for role,path in [('client',client),('backend',out/'server/backend-final.sqlite')]:
   with contextlib.closing(sqlite3.connect('file:'+str(path)+'?mode=ro',uri=True)) as c:
    assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not c.execute('PRAGMA foreign_key_check').fetchall()
    hashes,graph=oracle.walk(c,target,client=role=='client',sql_values=role=='backend');sets[role]=hashes;assert graph['raw_value_sha256']==fixture[cfg['variant']]['graph']['raw_value_sha256'];assert graph['objects']==20148 and graph['canonical_bytes']==13146158
    table='objects' if role=='client' else 'sync_objects';body=c.execute(f'SELECT body FROM {table} WHERE hash=?',(target['hot_ref']['hash'],)).fetchone()[0];financial=sha(oracle.encode(json.loads(body)['state']));assert financial==d['semantic_digest']['financial_state_sha256']
    if role=='client':
     accepted=c.execute('SELECT current_id,previous_id,sequence FROM accepted WHERE id=1').fetchone();assert accepted==(d['accepted_after']['id'],None,1);assert c.execute('SELECT count(*) FROM objects').fetchone()[0]==20148;assert c.execute('SELECT sum(length(body)) FROM objects').fetchone()[0]==13146158
    backup=out/(role+'-consistent.sqlite');assert not backup.exists()
    with contextlib.closing(sqlite3.connect(backup)) as dst:c.backup(dst)
   raw=backup.read_bytes();compressed=gzip.compress(raw,mtime=0);(out/(role+'-consistent.sqlite.gz')).write_bytes(compressed);backup.unlink();detail[role]={'graph':graph,'financial_state_sha256':financial,'backup_sha256':sha(raw),'backup_bytes':len(raw),'gzip_sha256':sha(compressed)}
  assert sets['client']==sets['backend'];hashsets[cfg['variant']]=sets['client']
  lc=counters(d);lc['id']=d['id'];lc['variant']=cfg['variant'];assert lc['objects_committed_blob_bytes']==d['db_after']['body_bytes']==13146158
  old=counters(historic[cfg['variant']]);diff={key:{'historical':old[key],'new':lc[key]} for key in old if old[key]!=lc[key]};assert not diff,diff
  lookup=d['backend']['lookup'];calls=lookup['lookup_calls'];assert calls==667 and lookup['hot_constructor_calls']==calls and lookup['hot_body_calls']==calls*(3 if cfg['variant']=='A' else 2)
  lc['total_actual_hot_decodes']=lookup['hot_body_calls']+lookup['hot_constructor_calls'];lc['within_engine_historical_exact_counter_maps']='PASS';costs.append(lc)
  save(out/'independent-verification.json',{'status':'PASS','matched_client_backend':True,'accepted_native':list(accepted),'objects':len(sets['client']),'details':detail,'E4_semantics':d['semantic_digest'],'scopes_closed':True,'request_count':len(reqs),'observation_leases':leases,'renewals':len(leases)-1,'manifest_response_count':len(manifests),'idempotent_terminal_rechecks':len(manifests)-len(leases),'expired_response_count':sum(x['status']==410 for x in reqs),'within_engine_counter_map_differences':diff})
  runs.append(d)
 assert runs[0]['variant']=='A' and runs[1]['variant']=='B';assert runs[0]['end_utc']<runs[1]['start_utc'];assert runs[0]['semantic_digest']==runs[1]['semantic_digest']
 a,b=costs;removed=a['backend_primary_validation_input_bytes']-b['backend_primary_validation_input_bytes'];assert removed==667*87364
 for key in ['client_hash_input_bytes','client_primary_validation_input_bytes','backend_hash_input_bytes','SQL_logical','objects_committed_blob_bytes']:assert a[key]==b[key]
 ta,tb=[x['accepted_after']['target'] for x in runs];assert all(ta[k]==tb[k] for k in ['ns','principal_id','versions','revision','raw_ref','index_ref','control_ref']);assert hashsets['A']-hashsets['B']=={ta['hot_ref']['hash']} and hashsets['B']-hashsets['A']=={tb['hot_ref']['hash']}
 save(E/'logical-counters.json',{'status':'PASS','runs':costs,'removed_backend_primary_bytes':removed,'removed_parse_calls':667,'actual_total_hot_decodes':{'A':a['total_actual_hot_decodes'],'B':b['total_actual_hot_decodes']},'decode_reduction_pct':25,'hash_client_validation_SQL_equal':True,'within_engine_historical_counter_maps_exact':True,'physical_IO_measured':False})
 save(E/'verification-summary.json',{'status':'PASS','completed_runs':2,'E3_E4':True,'financial_semantic_equivalence':True,'historical_fixture_semantics_identical':True,'source_engine_dependent_hash_difference':'hot object one per engine plus Target context/sync_root; raw/index/control identical','reachable_object_set_differences':{'A_only':sorted(hashsets['A']-hashsets['B']),'B_only':sorted(hashsets['B']-hashsets['A'])},'within_engine_counters':'PASS','new_runs':[(x['id'],x['end_to_end_with_bounded_E4_us']/1e6) for x in runs]})
 # 원시 JSON/로그와 matched backups만 별도 evidence로 복사한다. scratch의 원본 DB는 종료 후 cleanup까지 유지한다.
 for d in runs:
  src=pathlib.Path(d['out']);dst=E/'raw'/d['id'];assert not dst.exists();dst.mkdir(parents=True)
  for p in src.rglob('*'):
   if not p.is_file() or p.name=='backend-final.sqlite' or p.suffix in ['.pem']:continue
   q=dst/p.relative_to(src);q.parent.mkdir(parents=True,exist_ok=True)
   if p.name=='requests.jsonl':q=q.with_suffix(q.suffix+'.gz');q.write_bytes(gzip.compress(p.read_bytes(),mtime=0))
   else:shutil.copyfile(p,q)
 for p in (W/'raw').iterdir():
  if p.is_file():q=E/(p.name+'.gz');assert not q.exists();q.write_bytes(gzip.compress(p.read_bytes(),mtime=0))
 print(json.dumps({'status':'PASS','full_cold_completed':2,'E3_E4':'PASS','semantic_equivalence':'PASS','counter_maps':'exact historical match within each engine','decode_counts':[a['total_actual_hot_decodes'],b['total_actual_hot_decodes']]}))
if __name__=='__main__':verify()
