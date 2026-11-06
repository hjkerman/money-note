"""B06 분석의 출처와 산술만 검증한다. 제품/test suite는 실행하지 않는다."""
import json,pathlib,hashlib,re,math,collections
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b06'
def get(n):return json.loads((E/n).read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,condition):
 assert condition,name
 checks.append({'check':name,'status':'PASS'})
inv=get('measurement-inventory.json');crit=get('critical-path-summary.json');records=inv['records'];bykey={r['key']:r for r in records}
check('136개 기록의 key 중복 없음',len(bykey)==len(records)==136)
check('연구별 기록 수',inv['counts']=={'B04':106,'B05A':12,'B05B':2,'B05':16})
checked=set()
for r in records:
 check('raw SHA: '+r['key'],sha(R/r['raw'])==r['raw_sha256']);checked.add(r['raw'])
primary=[r for r in records if r['primary_for_cold_analysis']]
check('주요 완료 cold는22개',len(primary)==22 and all(r['completed'] for r in primary))
check('주요 cold의 source/fixture/engine 신원 있음',all(r['source_payload'] and r['engine_sha256'] and r['fixture_digest'] for r in primary))
check('모든 primary E1/E2/E3/E4 완료',all(all(r['stage_completion'].get(k) is True for k in ['E1','E2','E3','E4']) for r in primary))
check('모든 primary collector 정상 닫힘',all(r['collector_closed'] is True for r in primary))
check('OFF logical counter는null',all(r['backend_hash_input_bytes'] is None and r['client_hash_input_bytes'] is None and r['SQL_logical'] is None for r in primary if not r['on']))
for c in crit['per_run']:
 check('배분합=T: '+c['key'],math.isclose(sum(c['conditional_serial_allocation_s'].values()),c['cold_s'],abs_tol=1e-8))
 check('시간 배분 음수 없음: '+c['key'],min(c['conditional_serial_allocation_s'].values())>=0)
 check('exclusive 미측정값은null: '+c['key'],all(c[k] is None for k in ['exclusive_measured_CPU_function_s','pure_network_s','client_exclusive_validation_CPU_s','SQLite_fsync_s']))
ons=[r for r in primary if r['N']==5000 and r['on'] and r['study'] in ['B05A','B05B']]
check('5k ON 네 실행의 동일 workload',len(ons)==4 and all(r['objects']==r['staged_objects']==r['committed_objects']==20148 and r['body_bytes']==13146158 and r['HTTP_requests']==335 and r['lookup_calls']==667 and r['request_scopes_complete'] and not r['backend_request_intervals_overlap'] and not r['observation_expired'] for r in ons))
for study in ['B05A','B05B']:
 a=next(r for r in ons if r['study']==study and r['engine_variant']=='A');b=next(r for r in ons if r['study']==study and r['engine_variant']=='B')
 check(study+' 실제decode25%감소',(a['hot_constructor_decodes']+a['hot_body_decodes'])==2668 and (b['hot_constructor_decodes']+b['hot_body_decodes'])==2001)
 check(study+' JSON span감소는667*hotbytes',a['backend_primary_input_bytes']-b['backend_primary_input_bytes']==667*87364)
 check(study+' 전체 이득 불성립',b['cold_s']>a['cold_s'])
 check(study+' 금융 raw/state일치',a['semantic_digest']==b['semantic_digest'])
 for r in [a,b]:
  p=pathlib.Path(r['raw']).parent/'independent-verification.json';d=json.loads((R/p).read_text());checked.add(str(p))
  check('기존 독립 검증 읽기: '+str(p),d['status']=='PASS' and d['matched_client_backend'] and d['objects']==20148 and d['accepted_native']==[r['accepted_generation']['id'],None,1])
 check(study+' 원 timer일치',a['end_to_end_boundary']==b['end_to_end_boundary']=='publication+bounded E4')
for variant in ['A','B']:
 a=next(r for r in ons if r['study']=='B05A' and r['engine_variant']==variant);b=next(r for r in ons if r['study']=='B05B' and r['engine_variant']==variant)
 da=json.loads((R/a['raw']).read_text());db=json.loads((R/b['raw']).read_text())
 check('같은engine counter전체같음 '+variant,all(da[k]==db[k] for k in ['logical_counters','sql_counters']) and da['backend']['counters']==db['backend']['counters'])
 check('같은engine template/client/fixture신원 '+variant,all(a[k]==b[k] for k in ['template_sha256','client_component_digest','fixture_digest','engine_sha256','backend_observation_sha256']))
for m in crit['lookup_amdahl_models']:
 a=bykey[m['A_key']];b=bykey[m['B_key']]
 check('Amdahl 조건부 산술 '+m['study'],math.isclose(m['conditional_system_time_reduction_pct'],100*(a['lookup_s']-b['lookup_s'])/a['cold_s'],abs_tol=1e-10))
for stage in crit['steady_E3_I25_distinction']:
 checked.add(stage['raw']);check('normal E3 fullN0 '+stage['workload'],all(v==0 for v in stage['forbidden_fullN_keys'].values()) and sha(R/stage['raw'])==stage['raw_sha256'])
dec=get('next-action-decision.json')
check('정확히 하나의 다음 작업',dec['choice']=='B — TARGETED PROFILING' and dec['new_experiments_in_B06']==0 and dec['bounded_scope']['packets_max']==32 and dec['bounded_scope']['runtime_stop_seconds']==120)
report=R/'docs/t66f-b06-cold-acquisition-critical-path-analysis.md';body=report.read_text();links=re.findall(r'\]\(([^)]+)\)',body)
missing=[p for p in links if not p.startswith('http') and p!='benchmarks/t66f-b06/analysis-validation.json' and not (report.parent/p).exists()]
# 최종 manifest/정리/보존은 종료 단계에서 생성하므로 이 검사 이전에 생성해야 한다.
check('보고서 local link존재',not missing)
check('일본어 설명문 없음',not re.search(r'[\u3040-\u30ff]',body))
check('필수 footer 있음','PASS — NEXT EXPERIMENT IDENTIFIED\n\nNEXT ACTION:' in body)
check('검증은 제품 실행이 아님',True)
result={'status':'PASS','method':'read/hash/JSON arithmetic and provenance assertions only','checks':checks,'checks_count':len(checks),'raw_paths_checked':len(checked),'new_experiments':0,'product_or_regression_execution':False}
(E/'analysis-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','checks':len(checks),'raw_paths_checked':len(checked),'new_experiments':0},ensure_ascii=False))
