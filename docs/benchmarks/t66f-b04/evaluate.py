"""완료된 cold의 관측별 진행·CPU·D3 비용을 분석한다. 100k를 실행하지 않는다."""
import json,math,pathlib,statistics
E=pathlib.Path('/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b04')
result=[]
for n in (1000,5000,10000,50000):
 for on in (False,True):
  p=E/f'raw/n{n}-v3/cold-0-{"on" if on else "off"}.json'
  if not p.exists():continue
  d=json.loads(p.read_text())
  if d['status']!='COMPLETED':continue
  requests=d['backend']['requests'];windows={}
  for r in requests:
   if r['manifest']:
    a=r['manifest'];id=a['observation_id']
    if id not in windows:windows[id]={'id':id,'validated_at':a['validated_at'],'expires_at':a['expires_at'],'first_manifest_response_ns':r['end_ns'],'manifest_requests':0,'terminal_replays':0,'object_events':0,'packets':0,'backend_wall_ns':0,'backend_cpu_ns':0,'last_object_response_ns':None,'expired':False}
    windows[id]['manifest_requests']+=1;windows[id]['terminal_replays']+=int(r['status']==200)
   if '/observations/' in r['path']:
    id=r['path'].split('/')[5]
    if id not in windows:continue
    w=windows[id];w['backend_wall_ns']+=r['wall_ns'];w['backend_cpu_ns']+=r['process_cpu_ns']
    if r['chunks']:w['object_events']+=r['chunks'];w['packets']+=1;w['last_object_response_ns']=r['end_ns']
    w['expired']|=r['status']==410
  for w in windows.values():
   w['manifest_response_to_last_object_s']=(w['last_object_response_ns']-w['first_manifest_response_ns'])/1e9 if w['last_object_response_ns'] else None
   w['object_events_per_productive_second']=w['object_events']/w['manifest_response_to_last_object_s'] if w['manifest_response_to_last_object_s'] else None
  assert sum(w['object_events'] for w in windows.values())==d['db_after']['objects']
  first=min(w['first_manifest_response_ns'] for w in windows.values());last=max(w['last_object_response_ns'] for w in windows.values());transfer=(last-first)/1e9
  d3={}
  for field in ('auth_ms','admission_ms','resolution_ms','terminal_serialization_ms','total_ms','prepared_ms','terminal_http_ms','http_ms'):
   v=[x[field] for x in d['backend']['d3'] if field in x]
   d3[field]={'samples':len(v),'sum_seconds':sum(v)/1000,'median_ms':statistics.median(v)} if v else None
  result.append({'N':n,'on':on,'complete':True,'accepted':d['accepted_after'],'object_count':d['db_after']['objects'],'elapsed_s':d['elapsed_us']/1e6,'manifest_first_response_to_last_object_s':transfer,'backend_handler_s':sum(r['wall_ns'] for r in requests)/1e9,'backend_process_cpu_s':sum(r['process_cpu_ns'] for r in requests)/1e9,'HTTP_complete_body_s':d['http']['send_to_complete_body_us']/1e6,'E1_SQL_API_s':d['e1_sql_api_publication_us']/1e6,'row_callback_lower_bound_s':None if not on else d['sql_row_callback_publication_us_lower_bound']/1e6,'client_cpu_s_tick10ms':d['process_cpu_us_tick_10ms']/1e6,'windows':list(windows.values()),'D3':d3,'raw_path':str(p)})
large=[r for r in result if r['N']==50000];projection=[]
for r in large:
 # 같은 N당 처리량 가정은 진단 가정일 뿐이다. 실제100k object cardinality는 역사 fixed-H fixture에서 온다.
 estimate=r['manifest_first_response_to_last_object_s']*400532/r['object_count'];projection.append({'on':r['on'],'basis_N':50000,'historical_100k_object_count':400532,'assumption':'constant per-object transfer cost and same phase mix; NOT a validated 100k scaling model','simple_transfer_seconds':estimate,'nominal_active_lease_windows_900s':math.ceil(estimate/900),'policy_three_windows_seconds':2700,'ratio_to_nominal_active_lease_budget':estimate/2700,'exclusions':['N-dependent path depth','late DB/proof size','phase mix','terminal/release/renewal overhead','run-to-run variation'],'cannot_prove_100k_completion':True})
(E/'cold-analysis.json').write_text(json.dumps({'completed_cold_runs':result,'nonadditive_timings':True,'simple_projection_diagnostic_only':projection,'necessary_average_progress_for_historical_100k_objects_over_3x900s':400532/2700,'necessary_not_sufficient_or_latency_SLA':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'completed_cold_runs':len(result),'50k_modes':len(large),'diagnostic_projection':projection}))
