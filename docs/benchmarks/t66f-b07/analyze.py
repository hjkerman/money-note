"""한 번의 bounded 실행을 분석한다. 새 packet이나 제품 함수를 실행하지 않는다."""
import json,pathlib,collections,statistics,hashlib,math
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b07';W=pathlib.Path('/tmp/money-note-t66f-b07-20261026')
def read(n):return json.loads((E/n).read_text())
def save(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[json.loads(l) for l in (E/'packets.jsonl').read_text().splitlines()];budget=read('execution-budget.json');execution=read('execution.json');pre=read('preflight.json')
obj=[r for r in rows if r['request_type']=='objects'];probed=[r for r in rows if r['probe']];po=[r for r in obj if r['probe']];co=[r for r in obj if not r['probe']]
assert len(rows)==30==budget['attempted_packets']==budget['closed_packet_records'] and budget['returncode']==0 and budget['within_limits'] and budget['wall_s']<120
assert all(r['collector_closed'] and r['pending']==0 and r['completion_error'] is None and r['error'] is None for r in rows)
assert all(r['connect_calls']==3 and r['open_calls']==3 and r['close_calls']==5 for r in rows)
assert all(all(v['self_ns']>=0 and v['self_cpu_ns']>=0 for v in r['metrics'].values()) for r in probed)
for slot in range(7):
 sample=[r for r in obj if r['slot']==slot]
 assert len(sample)==4 and all(r['counters']==sample[0]['counters'] for r in sample)
 # request UUID가 다르므로 전체 response hash 동일을 요구하지 않는다.
 assert len({r['response_bytes'] for r in sample})==1

def stat(ns):
 if not ns:return None
 vs=[n/1e9 for n in ns];order=sorted(vs)
 return {'count':len(vs),'total_s':sum(vs),'median_s':statistics.median(vs),'min_s':min(vs),'max_s':max(vs),'p90_nearest_rank_s':order[math.ceil(.9*len(order))-1]}
def distribution(sample):
 out={}
 for key in sorted({f['function'] for r in sample for f in r.get('function_intervals',[])}):
  events=[f for r in sample for f in r.get('function_intervals',[]) if f['function']==key]
  out[key]={'inclusive_wall':stat([f['wall_ns']for f in events]),'inclusive_thread_CPU':stat([f['thread_cpu_ns']for f in events]),'exclusive_wall':stat([f['self_ns']for f in events]),'exclusive_thread_CPU':stat([f['self_cpu_ns']for f in events])}
 return out

def agg(sample,group='metrics'):
 out={}
 for r in sample:
  for k,v in r.get(group,{}).items():
   d=out.setdefault(k,collections.Counter());d.update(v)
 return {k:dict(v) for k,v in out.items()}
A=agg(po);T=sum(r['handler_ns']for r in po)/1e9
connect=A['connect']['wall_ns']/1e9;schema=agg(po,'connect_metrics')['retention_validate']['wall_ns']/1e9
# 동기 함수 tree만 다룬다. SQL timer는 execute만 포함하고 fetch는 제외한다.
parts={'open_s':A['open']['wall_ns']/1e9,'schema_s':schema,'connect_other_s':connect-A['open']['wall_ns']/1e9-schema}
assert min(parts.values())>=0 and abs(sum(parts.values())-connect)<1e-9
residuals=[]
for r in po:
 lookup=r['metrics']['lookup']['wall_ns']/1e9
 # resolution은 제품 D3 callback의 응답별 값이며 lookup/connect와 겹치지 않는다.
 # 시간 순서 대응은 실제 실행 순서와 d3 objects 순서를 사용한다.
 d3obj=[d for d in execution['d3'] if d.get('operation')=='objects'];index=obj.index(r);d3=d3obj[index]
 resolution=d3['resolution_ms']/1000
 residuals.append({'sequence':r['sequence'],'handler_s':r['handler_ns']/1e9,'connect_s':r['metrics']['connect']['wall_ns']/1e9,'lookup_s':lookup,'resolution_s':resolution,'handler_other_s':r['handler_ns']/1e9-r['metrics']['connect']['wall_ns']/1e9-lookup-resolution})
assert len(d3obj)==28 and all(v['handler_other_s']>=0 for v in residuals)
control_total=sum(r['handler_ns']for r in co)/1e9;probe_total=T
slots=[]
for slot in range(7):
 c=[r['handler_ns']/1e9 for r in co if r['slot']==slot];p=[r['handler_ns']/1e9 for r in po if r['slot']==slot]
 slots.append({'slot':slot,'control_s':c,'probe_s':p,'probe_minus_control_mean_s':statistics.mean(p)-statistics.mean(c),'probe_over_control_mean':statistics.mean(p)/statistics.mean(c)})
expected=A['expected_revision_contract']['wall_ns']/1e9
expected_per_packet=stat([r['metrics']['expected_revision_contract']['wall_ns']for r in po])
projection=[]
for study,path in [('B05A','docs/benchmarks/t66f-b05a/raw/n5000-1-A-on/run.json'),('B05B','docs/benchmarks/t66f-b05b/raw/n5000-0-A-on/run.json')]:
 d=json.loads((R/path).read_text());n=sum(r['path'].endswith('/objects') for r in d['backend']['requests']);assert n==332
 c_med=statistics.median(r['metrics']['connect']['wall_ns']/1e9 for r in po);e_med=expected_per_packet['median_s'];cold=d['end_to_end_with_bounded_E4_us']/1e6
 projection.append({'study':study,'raw':path,'raw_sha256':sha(R/path),'known_object_packets':n,'historical_total_requests':len(d['backend']['requests']),'historical_cold_s':cold,'B07_median_connect_per_object_packet_s':c_med,'B07_median_expected_parse_per_object_packet_s':e_med,'conditional_connect_for_332_packets_s':n*c_med,'conditional_expected_parse_for_332_packets_s':n*e_med,'conditional_expected_parse_share_cold':n*e_med/cold,'historical_compatible_call_count_from_source':3*n,'scope':'object packets only; firstmanifest/recheck/release excluded; N5k not executed','assumptions':['same repeated baseline connect/schema path and schema text','perpacket CPU frequency/cache/B03/probe overhead comparable','hypothetical expected parsing elimination only; cache cost and actualchecks still required'],'not_actual_speedup':True})

summary={'classification':'PASS — MATERIAL COST ATTRIBUTED','engineering_decision':'A — CONFIRMED MATERIAL TARGET','source':pre['payload_sha256'],'engine':pre['engine_sha'],'N':1000,'populations':{'all_packets':len(rows),'all_handler_s':sum(r['handler_ns']for r in rows)/1e9,'probe_packets':len(probed),'control_object_packets':len(co),'probe_object_packets':len(po),'object_probe_handler_s':T,'all_connect_calls':sum(r['connect_calls']for r in rows),'all_open_calls':sum(r['open_calls']for r in rows),'close_invocations':sum(r['close_calls']for r in rows),'close_note':'credential 1회, repository의 with/finally에서 각각 2회. close 호출 수는 고유 연결 수가 아니다.'},'object_probe_metrics':A,'object_probe_connect_metrics':agg(po,'connect_metrics'),'object_probe_outside_connect_metrics':agg(po,'outside_connect_metrics'),'all_probed_metrics':agg(probed),'distributions_all_probed':distribution(probed),'distributions_object_probed':distribution(po),'handler_object_probe':stat([r['handler_ns']for r in po]),'connect_nonoverlapping_parts':parts,'connect_share_handler':connect/T,'schema_share_handler':schema/T,'expected_revision_parse_s':expected,'expected_revision_parse_share_handler':expected/T,'expected_revision_parse_share_connect':expected/connect,'expected_revision_parse_packet_distribution':expected_per_packet,'per_packet_handler_nonoverlapping_parts':residuals,'nonoverlap_status':'VALID for synchronous function trees and serial handler budgets; owned SQL execute incomplete coverage, nested timings not additive','control_probe':{'control_handler_total_s':control_total,'probe_handler_total_s':probe_total,'delta_s':probe_total-control_total,'ratio':probe_total/control_total,'per_slot':slots,'causal_probe_overhead':'not isolated CPU; same slot counter equivalence, two repeats each, order/frequency noise remains','shared_branch_overhead_unmeasured':True},'projection':projection,'SQL_limit':'owned connection execute only; cursor fetch/inmemory SQL and observer exclusive CPU not fully measured','materiality':'no binding threshold invented; directly timed repeated schema >1/3 handler, pure expected parse ~8% handler; safe net implementation benefit not established','first_request':rows[0],'source_never_edited':True}
save('call-path-attribution.json',summary)
save('packet-timings.json',{'schema_version':1,'source':pre['payload_sha256'],'engine':pre['engine_sha'],'fixture':pre['fixture'],'measurement':'B07 experimental runtime wrappers + unchanged B03 ON; IR07 did not audit these timers','packets':rows,'unmeasured_values':'control function timings absent, not zero; SQL fetch/native I/O unavailable','raw':'packets.jsonl'})
decision={'execution_verdict':'PASS — MATERIAL COST ATTRIBUTED','engineering_decision':'A — CONFIRMED MATERIAL TARGET','hypothesis':'repeated connect/schema confirmed; not all connect work removable','removable_candidate':'backend/app/db_migrations.py:_validate_revision_triggers의 schema 전용 기대 계약 컴파일','measured_candidate':{'calls':A['expected_revision_contract']['calls'],'wall_s':expected,'object_packets':len(po),'calls_per_connect':A['expected_revision_contract']['calls']/A['connect']['calls'],'share_handler':expected/T,'share_connect':expected/connect},'safe_net_avoidable_fraction':'NOT ESTABLISHED — candidate work subset measured, cache replacement/invalidation/safety tests and actual net gain not executed','credible_removable_work':'same immutable schema argument yields same immutable expected parser tuple; compile expectation once with bounded exact-schema key. This is source reasoning, not implemented validation bypass','proposed_minimal_direction':'maxsize=1 exact-schema keyed immutable expected revision trigger contracts/names/tables; keep current actual DB trigger parsing/comparison and revision-state validation on every fresh connection','invariants':['do not cache actual DB validation PASS or actual trigger contents','fresh auth/lease/ownership/schema/current trigger checks remain','same exceptions/ordering/canonical/financial behavior; no connection pooling/PRAGMA edits','schema key and engine source changes invalidate expected compilation; immutable return and bounded retention'],'source_SHA_impact':'shared backend/app/db_migrations.py is engine source; new engine/artifact/exact admission and relevant source guards need separately authorized consistent update','implementation_in_B07':False,'N5k_actual_run':False,'N100k':'NO-GO','future_validation_bound':{'N':1000,'packets_max':32,'execution_seconds_max':120,'full_5k_10k_50k_100k':0},'next_action_ko':'별도 승인된 과제에서 원 B03의 _validate_revision_triggers에 정확한 schema 키·최대 1항목의 불변 기대 계약 컴파일 재사용 후보를 구현하고 실제 DB 검사 보존과 N=1k·32 packet/120초 성능을 검증한다.'}
save('next-action-decision.json',decision)
manifest={'schema_version':1,'classification':summary['classification'],'engineering_decision':decision['engineering_decision'],'baseline_payload':pre['payload_sha256'],'baseline_engine':pre['engine_sha'],'fixture':pre['fixture'],'B03_instrumentation':'original audited bytes, ON','B07_instrumentation':'task-owned runtime wrappers, separately identified, not IR07 audited','tooling_digest_capture':'offline after completed run; runtime probe/experiment/run source unchanged after execution','tooling':{p.name:sha(p) for p in E.glob('*.py')},'planned_packets':30,'maximum_packets':32,'attempted_packets':len(rows),'complete_packets':len(rows),'incomplete_packets':0,'errors':0,'wall_s':budget['wall_s'],'max_wall_s':120,'watchdog':budget,'calls_per_packet':{'fresh_connect':3,'fresh_open':3,'close_invocations':5,'inside_connect_schema':3},'semantics':{'all30_responses_successful':True,'all28object_responses_exact_preserved_bytes':True,'same_slot_B03_counters_all4blocks_equal':True,'fixture_graph_unchanged':execution['fixture_graph_unchanged'],'source_function_behavior_not_bypassed':True,'first_request_extra_schema_validation':rows[0]['metrics']['retention_validate']['calls']-rows[0]['connect_calls']},'no_full_cold':{'N1000_Flutter':0,'N5000':0,'N10000':0,'N50000':0,'N100000':0},'packet_timings':'packet-timings.json','raw_attempts':'requests.jsonl','raw_packets':'packets.jsonl','attribution':'call-path-attribution.json','decision':'next-action-decision.json','historical_comparison':'B06 residual is not assumed connect cost','new_product_source_identity':None}
save('run-manifest.json',manifest)
print(json.dumps({'verdict':summary['classification'],'packets':len(rows),'wall_s':budget['wall_s'],'object_probe_handler_s':T,'connect_s':connect,'connect_share':connect/T,'schema_s':schema,'expected_parse_s':expected,'expected_share':expected/T,'control_probe_ratio':probe_total/control_total,'projection':projection},ensure_ascii=False))
