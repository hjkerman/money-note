from pathlib import Path
import json,hashlib
R=Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b09';W=Path('/tmp/money-note-t66f-b09-20261026');C=W/'candidate'
# B08의 이미 시험한 task-owned context-local probe만 재사용. 제품 파일 변경 없음.
probe=(R/'docs/benchmarks/t66f-b08/probe.py').read_text().replace('B08 공통 경량 timer','B09 실험 경량 timer').replace("ContextVar('B08_request'","ContextVar('B09_request'")
# actual compilation calls counted by _statements only while validating revision expectations.
probe=probe.replace("TLS=threading.local();ORIGINALS=[]", "REV=contextvars.ContextVar('B09_revision',default=False)\nTLS=threading.local();ORIGINALS=[]")
needle=" wrap(m,'_validate_revision_triggers','revision_validation')"
rep=""" native_revision=wrap(m,'_validate_revision_triggers','revision_validation')
 measured_revision=m._validate_revision_triggers
 @functools.wraps(measured_revision)
 def revision(*a,**kw):
  token=REV.set(True)
  try:return measured_revision(*a,**kw)
  finally:REV.reset(token)
 m._validate_revision_triggers=revision
 original_statements=m._statements
 @functools.wraps(original_statements)
 def statements(*a,**kw):
  row=CTX.get()
  if row is not None and REV.get():row['contract_compilations']+=1
  return original_statements(*a,**kw)
 m._statements=statements"""
assert needle in probe;probe=probe.replace(needle,rep)
(E/'probe.py').write_text(probe)
s=(R/'docs/benchmarks/t66f-b05a/server.py').read_text();s=s.replace('B05A 전용 실제 TLS fixture','B09 전용 실제 TLS fixture')
s=s.replace('import counters as cost','import counters as cost\nfrom probe import CTX,install,cache_info,calibration\ninstall()')
s=s.replace("  start=time.perf_counter_ns();cpu=time.process_time_ns();error=None", "  schema_profile={'timings':{},'connections':0,'opens':0,'closes':0,'actual_schema_inspections':0,'contract_compilations':0,'cache_before':cache_info()}\n  schema_token=CTX.set(schema_profile)\n  start=time.perf_counter_ns();cpu=time.process_time_ns();error=None")
s=s.replace("   end=time.perf_counter_ns();cpu_ns=time.process_time_ns()-cpu", "   end=time.perf_counter_ns();cpu_ns=time.process_time_ns()-cpu\n   schema_profile['cache_after']=cache_info();CTX.reset(schema_token)")
s=s.replace("row={'serial':serial", "row={'schema_profile':schema_profile,'serial':serial")
s=s.replace("  print(json.dumps(init),flush=True)","  init['B09_probe_calibration']=calibration()\n  print(json.dumps(init),flush=True)")
(E/'server.py').write_text(s)
# Preserve authoritative init/calibration metadata separately, outside primary timing.
s=(R/'docs/benchmarks/t66f-b05a/cold_test.dart').read_text().replace('B05-A 실제 Flutter cold','B09 실제 Flutter cold').replace("expect(ReleaseContract.financialEngine,'f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3')","expect(ReleaseContract.financialEngine,'5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c')")
s=s.replace("final init=jsonDecode(lines.current) as Map;", "final init=jsonDecode(lines.current) as Map;save('$out/init.json',init);")
(E/'cold_test.dart').write_text(s)
p=C/'docs/benchmarks/t66f-b09';p.mkdir(parents=True,exist_ok=True);(p/'cold_test.dart').write_text(s)
# Source graph oracle unchanged. ON/OFF claim only if OFF is actually present.
s=(R/'docs/benchmarks/t66f-b05a/verify_runs.py').read_text().replace("E=R/'docs/benchmarks/t66f-b05a';W=pathlib.Path('/tmp/money-note-t66f-b05a-20261026')","E=R/'docs/benchmarks/t66f-b09';W=pathlib.Path('/tmp/money-note-t66f-b09-20261026')")
s=s.replace("'within_engine_ON_OFF':'PASS'", "'within_engine_ON_OFF':'PASS' if N==1000 else 'NOT MEASURED — ON only'")
(E/'verify_runs.py').write_text(s)
sha=lambda b:hashlib.sha256(b).hexdigest()
ci={p.relative_to(C).as_posix():sha(p.read_bytes()) for p in sorted((C/'mobile/lib').rglob('*.dart'))+[C/'mobile/assets/segmented/isolated-release-artifacts.json']};cs=sha(json.dumps(ci,sort_keys=True,separators=(',',':')).encode())
orders={1000:[('A',False),('B',False),('B',True),('A',True)],5000:[('A',True),('B',True)]};engines={'A':'7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c','B':'5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c'}
for N,order in orders.items():
 runs=[]
 for i,(v,on) in enumerate(order):
  rid=f'n{N}-{i}-{v}-'+('on' if on else 'off');T=W/('baseline' if v=='A' else 'candidate')
  runs.append({'id':rid,'ordinal':i,'N':N,'variant':v,'on':on,'rep':0,'engine_sha':engines[v],'source_payload_sha':{'A':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','B':'a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94'}[v],'backend_tree':str(T),'fixture':str(W/f'fixtures-n{N}'),'out':str(W/'raw'/rid),'client_source_digest':cs,'backend_observation_sha256':sha((T/'backend/isolated_sync/observation.py').read_bytes())})
 plan={'N':N,'scratch':str(W),'server':str(E/'server.py'),'runs':runs,'client_component_inventory':ci,'client_source_digest':cs,'boundary':'AppState segmented publication 반환 + bounded E4 accepted read; UI/OfflineReady 아님','lease_seconds':900,'attempts':3,'predeclared_before_measurement':True,'conditional':N==5000,'max_cold_runs_total':6,'stage_boundaries':json.loads((R/'docs/benchmarks/t66f-b05a/plan-n1000.json').read_text())['phase_boundaries']}
 (E/f'plan-n{N}.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
(E/'escalation-policy.json').write_text(json.dumps({'N1k_order':['A OFF','B08 OFF','B08 ON','A ON'],'conditional_N5k_order':['A ON','B08 ON'],'conditions':['N1k 4/4 complete + E3/E4 + independent financial oracle','expected compile reduction with identical actual DB inspections','relevant backend handler/schema improvement','no resource/integrity/correctness defect','coherent practically useful end-to-end effect; local handler gain alone insufficient','ON/OFF discrepancy small or supported explanation','verified N5k source/fixture/environment before pair'],'N1k_full_runs_max':4,'N5k_full_runs_max':2,'no_favorable_result_retry':True,'no_binding_performance_threshold_invented':True},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'drivers':'prepared','N1k_runs':4,'conditional_N5k_runs':2,'client_digest':cs}))
