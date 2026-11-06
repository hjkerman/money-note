"""보존된 counter의 stage·SQL payload를 추가 집계한다. 새 실측 없음."""
import collections,json,subprocess,platform,pathlib
from prepare import R,E,sha,save
p=E/'logical-counters.json';d=json.loads(p.read_text())
for r in d['runs']:
 be=r['backend_by_stage'];cl=r['client_by_stage'];sq=r['SQL_by_stage']
 r['backend_SQL_logical']={kind:{metric:sum(int(v) for k,v in be.items() if '/'+kind+'/' in k and k.endswith('/'+metric)) for metric in ['text_bytes','blob_bytes','scalar_values','null_values']} for kind in ['attempted','effective','committed']}
 r['client_committed_text_blob_payload_bytes']=r['SQL_logical']['committed']['textBytes']+r['SQL_logical']['committed']['blobBytes'];r['backend_committed_text_blob_payload_bytes']=r['backend_SQL_logical']['committed']['text_bytes']+r['backend_SQL_logical']['committed']['blob_bytes']
 stages={}
 for stage in sorted({k.split('/')[0] for k in be}|{k.split('/')[0] for k in cl}|{k.split('/')[0] for k in sq}):
  stages[stage]={'client_hash_input_bytes':sum(int(v) for k,v in cl.items() if k.startswith(stage+'/') and k.endswith('/hashInputBytes')),'client_primary_input_bytes':sum(int(v) for k,v in cl.items() if k.startswith(stage+'/') and k.endswith('/submittedBytes')),'backend_hash_input_bytes':sum(int(v) for k,v in be.items() if k.startswith(stage+'/') and k.endswith('/sha256/hash_input_bytes')),'backend_primary_input_bytes':sum(int(v) for k,v in be.items() if k.startswith(stage+'/') and k.endswith('/json/submitted_bytes')),'client_SQL_committed_text_blob_bytes':sum(int(v) for k,v in sq.items() if k.startswith(stage+'/') and (k.endswith('/textBytes/committed') or k.endswith('/blobBytes/committed'))),'backend_SQL_committed_text_blob_bytes':sum(int(v) for k,v in be.items() if k.startswith(stage+'/') and '/committed/' in k and (k.endswith('/text_bytes') or k.endswith('/blob_bytes')))}
 r['stage_attribution']=stages
save(p,d)
c=json.loads((E/'comparison-summary.json').read_text());c['performance_classification']='NO MATERIAL SYSTEM BENEFIT OBSERVED';c['followup_classification']='NOT JUSTIFIED';save(E/'comparison-summary.json',c)
save(E/'environment-after.json',{'platform':platform.platform(),'lscpu':json.loads(subprocess.check_output(['lscpu','-J'],text=True)),'memory':pathlib.Path('/proc/meminfo').read_text(),'filesystem':subprocess.check_output(['stat','-f','-c','%T','/home/hjkerman/codex/money-note'],text=True).strip(),'post_measurement_only':True})
print(json.dumps({'SQL_payload':[(r['variant'],r['client_committed_text_blob_payload_bytes'],r['backend_committed_text_blob_payload_bytes']) for r in d['runs']],'cold_runs_added':0}))
