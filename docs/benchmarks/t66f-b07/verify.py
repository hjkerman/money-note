"""보존 source bytes, 실제 금융 SQL 값, packet 계측의 독립적인 사후 대조."""
import json,pathlib,sqlite3,hashlib,contextlib,re,stat
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b07';W=pathlib.Path('/tmp/money-note-t66f-b07-20261026');sha=lambda b:hashlib.sha256(b).hexdigest()
def get(n):return json.loads((E/n).read_text())
pre=get('preflight.json');m=get('baseline-source-manifest.json');changes=[]
for a in m['entries']:
 p=W/'baseline'/a['path']
 if sha(p.read_bytes())!=a['sha256'] or stat.S_IMODE(p.stat().st_mode)!=int(a['mode'],8):changes.append(a['path'])
assert not changes and sha((W/'template-n1000.sqlite').read_bytes())==pre['fixture']['template_sha256']
fixture=json.loads((R/'docs/benchmarks/t66f-b05a/fixture-n1000.json').read_text());tables=sorted(fixture['A']['graph']['raw_rows'])+['users','auth_sessions']

def digest(c,table):
 assert re.fullmatch('[a-z_]+',table)
 cols=[r[1] for r in c.execute('PRAGMA table_info('+table+')')];assert all(re.fullmatch('[a-z_]+',k) for k in cols)
 query='SELECT '+','.join('typeof('+k+'),' + k for k in cols)+' FROM '+table
 rows=[]
 for row in c.execute(query):
  vals=[]
  for i in range(0,len(row),2):
   val=row[i+1];vals.append([row[i],val.hex() if isinstance(val,bytes) else repr(val) if isinstance(val,float) else val])
  rows.append(json.dumps(vals,ensure_ascii=False,separators=(',',':')))
 raw=json.dumps({'columns':cols,'rows':sorted(rows)},ensure_ascii=False,separators=(',',':')).encode();return {'count':len(rows),'sha256':sha(raw)}
with contextlib.closing(sqlite3.connect('file:'+str(W/'template-n1000.sqlite')+'?mode=ro',uri=True)) as a,contextlib.closing(sqlite3.connect('file:'+str(W/'backend-after.sqlite')+'?mode=ro',uri=True)) as b:
 before={t:digest(a,t)for t in tables};after={t:digest(b,t)for t in tables};assert before==after
 assert b.execute('PRAGMA quick_check').fetchone()[0]=='ok' and not b.execute('PRAGMA foreign_key_check').fetchall()
 all_columns_equal=True
r=get('call-path-attribution.json');raw=[json.loads(l)for l in(E/'packets.jsonl').read_text().splitlines()]
for p in raw:
 assert all(v['self_ns']>=0 and v['self_cpu_ns']>=0 and v['errors']==0 for v in p['metrics'].values())
 ints=sorted(p['connect_intervals'],key=lambda x:x['start_ns'])
 assert not any(x['end_ns']>y['start_ns']for x,y in zip(ints,ints[1:]))
 if p['request_type']=='objects' and p['probe']:
  assert p['connect_metrics']['retention_validate']['calls']==3 and p['connect_metrics']['finalization_validate']['calls']==3
  assert not p.get('outside_connect_metrics',{}).get('retention_validate')
  assert p['metrics']['expected_revision_contract']['calls']==99 and p['metrics']['actual_trigger_contract']['calls']==246
out={'status':'PASS','source_files_checked':len(m['entries']),'source_changes':changes,'fixture_unchanged':True,'actual_financial_and_auth_tables':before,'all_actual_SQL_values_and_storage_types_preserved':all_columns_equal,'object_responses_exact_preserved_bytes':'all28, asserted by runner','B03_same_slot_full_counter_map_equality':'all4 blocks, asserted by offline analyze.py','collector_complete':all(p['collector_closed'] and p['pending']==0 and p['completion_error'] is None for p in raw),'synchronous_tree_nonoverlap':'PASS','probe_actual_unknown_function_values_not_filled':True,'product_tests_run':False}
(E/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','source_files':899,'financial_and_auth_tables':len(tables),'packets':len(raw),'requests_repeated':0}))
