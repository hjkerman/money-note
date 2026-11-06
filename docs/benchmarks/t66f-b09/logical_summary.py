from pathlib import Path
import json,re
E=Path('/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b09');j=json.loads((E/'cold-ab-results.json').read_text());out=[]
def total(c,term):return sum(int(v)for k,v in c.items()if k.endswith(term))
def sql(c,outcome,backend=False):
 pat=rf'/{outcome}/(?:blob_bytes|text_bytes)$'if backend else rf'/{outcome}/(?:blobBytes|textBytes)$'if outcome in ['attempted','effective']else rf'/(?:blobBytes|textBytes)/{outcome}$'
 return sum(int(v)for k,v in c.items()if re.search(pat,k))
for r in j['runs']:
 if not r['on']:continue
 c=r['client_logical_cost'];b=r['backend_logical_cost'];s=r['sql_logical_cost']
 out.append({'id':r['id'],'backend_hash_input_bytes_including_auth':total(b,'hash_input_bytes'),'backend_JSON_submitted_bytes':total(b,'submitted_bytes'),'backend_JSON_completed_bytes':total(b,'completed_bytes'),'client_hash_input_bytes_including_checksum':total(c,'hashInputBytes'),'client_C1_submitted_bytes':total(c,'submittedBytes'),'client_C1_completed_bytes':total(c,'completedBytes'),'client_SQL_logical_text_blob_bytes':{o:sql(s,o)for o in ['attempted','effective','committed']},'backend_SQL_logical_text_blob_bytes':{o:sql(b,o,True)for o in ['attempted','effective','committed']},'boundary':'B03 collector measurement cohort only; C1/JSON primary submissions and retries repeat-counted; SQL stored text/BLOB logical payload, not disk IO or scalar storage estimate','raw':r['raw']})
assert len(out)==2
for k in out[0]:
 if k not in ['id','raw']:assert out[0][k]==out[1][k],k
(E/'logical-counter-summary.json').write_text(json.dumps({'ON_runs':out,'equivalent_B03_counters':'all backend/client/SQL keys exactly equal between A and B08 ON','OFF_values':None,'OFF_missing_is_not_zero':True,'B08_work_removed':'expected SQL trigger compilation only; no required current DB check removed'},ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
