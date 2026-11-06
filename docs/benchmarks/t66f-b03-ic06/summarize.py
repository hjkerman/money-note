"""실행 원문에서 IC06 gate·원 반례 ledger·후보 동결 전 요약을 만든다."""
import ast,gzip,hashlib,json,re,sys
from pathlib import Path
import xml.etree.ElementTree as ET
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent/'evidence';H=Path(__file__).parent

def data(label):return json.loads((O/(label+'.json')).read_text())
def source_record(record):return {k:v for k,v in record['source_before'].items() if k!='backend/tests/test_logical_cost_ic06.py'}
def build():
 gates=['ir06-primary-after','ir06-instrument-after','ir06-workers-after','ir06-stage-after','focused-backend-final','historical-python','ir06-lifecycle','flutter-affected','integration-oracle-verified','source-locks','differential-supported','backend-supported-complete','frontend-build','python-static-final','python-format-final','compile','diff-check']
 results={label:data(label) for label in gates}
 for label,d in results.items():
  assert d['exit_code']==0,label
  assert source_record(d)=={k:v for k,v in d['source_after'].items() if k!='backend/tests/test_logical_cost_ic06.py'},label
  for p,h in source_record(d).items():assert hashlib.sha256((R/p).read_bytes()).hexdigest()==h,(label,p)
 assert results['focused-backend-final']['source_unchanged'] and results['backend-supported-complete']['source_unchanged']
 assert results['flutter-affected']['done'] and results['flutter-affected']['flutter_counts']==dict(PASS=110,FAIL=0,SKIP=0)
 assert results['focused-backend-final']['junit_counts']==dict(PASS=606,FAIL=0,SKIP=0)
 assert results['historical-python']['junit_counts']==dict(PASS=67,FAIL=0,SKIP=0)
 log=gzip.open(O/'backend-supported-complete.log.gz','rt').read()
 match=re.search(r'(\d+) passed',log)
 assert match,log[-1000:]
 subtest_match=re.search(r'(\d+) subtests passed',log)
 assert subtest_match,'subtest summary missing'
 tests=int(match[1]);subtests=int(subtest_match[1])
 assert tests==1880 and subtests==1540,(tests,subtests)
 root=ET.parse(O/'backend-supported-complete.xml');cases=root.findall('.//testcase')
 assert len(cases)==tests and not any(c.find(t) is not None for c in cases for t in ['failure','error','skipped'])
 ledger=[]
 for case in ['primary','instrument','workers','stage']:
  pair={}
  for phase in ['before','after']:
   label=f'ir06-{case}-{phase}';record=data(label)
   raw=json.loads(gzip.open(O/(label+'.log.gz'),'rt').readline())
   pair[phase]=dict(record=label+'.json',exit_code=record['exit_code'],observed=raw,python='CPython 3.12.3',tool_id=json.loads((O/f'metadata-{case}-{phase}-metadata.json').read_text())['tool_id'],previously_allocated_and_released=True,currently_allocated=False,global_events=0,entry_local_event=4,registered_callback='PY_RETURN의 원 RuntimeError callback',effective_preflight='이름 없음으로 검사 생략' if phase=='before' else 'active mask 확인 뒤 획득 전 explicit incomplete',exception_kind='RuntimeError',actual_parse_calls=raw.get('native_calls',0),actual_parse_input_bytes=sum(len(bytes.fromhex(v)) for v in raw.get('native_inputs_hex',[])),callbacks_delivered=raw.get('callback_fired',len(raw.get('at_return',[]))))
   assert record['exit_code']==(1 if phase=='before' else 0)
  ledger.append(dict(case=case,**pair))
 (O/'reproduction-ledger.json').write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
 # IA06's unbounded original script intentionally stops at owner33. Strict
 # independent tests separately verify pre-execution rejection and weakref0.
 ia6=gzip.open(O/'direct-IA06.log.gz','rt').read();assert data('direct-IA06')['exit_code']==1
 assert 'rollback 뒤 retained: 0' in ia6 and 'transaction owner capacity exceeded; measurement incomplete' in ia6
 assert ast.literal_eval(gzip.open(O/'direct-IA07.log.gz','rt').readline())==[dict(stage='setup',returned_rows=176),dict(stage='setup',returned_rows=185)]
 paths=['docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b03/server.py','backend/tests/test_logical_cost_ic04.py','backend/tests/test_logical_cost_ic05.py','backend/tests/test_logical_cost_ic06.py','mobile/test/support/logical_cost_sqlite.dart']
 d=dict(task='T6.6F-B03-IC06',implementation_verdict='PASS',independent_B03='OPEN — 새 독립 감사 필요',head='ebcbd54d90eeee194a04b9eea6367f446ee2fd28',runtime='CPython 3.12.3',new_deterministic_tests=dict(PASS=175,FAIL=0,SKIP=0),focused_backend=results['focused-backend-final']['junit_counts'],historical_python=results['historical-python']['junit_counts'],ir06_lifecycle=results['ir06-lifecycle']['junit_counts'],flutter_affected=results['flutter-affected']['flutter_counts'],full_backend=dict(tests=tests,subtests=subtests,FAIL=0,SKIP=0,seconds=results['backend-supported-complete']['seconds']),full_backend_korean=f'새 전체 backend 한 회: {tests:,} tests / {subtests:,} subtests PASS, 실패0·skip0, exit0. 정확한 command/source SHA·JUnit·gzip raw는 context의 backend-supported-complete.json/xml/log.gz에 있다.',final_source_sha256={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in paths},gate_records={k:k+'.json' for k in gates},source_binding_note='초기 focused/Flutter 실행 중 IC06 test 파일에 preflight 실제 callback6건 및 미사용 import 제거만 추가됐다. counters/server/제품 source는 실행 전후 동일하다. 최종 focused606과 전체 backend1880은 최종 test SHA에서 재검증했다. 통과한 Flutter 제품 suite는 반복하지 않았다.',intermediate_failures_preserved=['수정 전 원 IR06 네 실패','python-static: 신규 test의 미사용 import1개, 최종 제거·재검증','첫 전체 backend5건은 checkout 내부 tmp_path를 기존 harness가 거부; /tmp 단일 scratch로 이동 후 focused5건과 전체 회귀를 다시 실행'],original_expected_exit1=['direct-IA06'],new_full_100k_cold_runs=0,cost_grid='미실행',required_finalization=['freeze-reconstruction.json','frozen-smoke.json','preservation-final.json','cleanup.json'])
 (O/'summary.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:d[k] for k in ['implementation_verdict','full_backend','focused_backend','flutter_affected','new_deterministic_tests']},ensure_ascii=False))
if __name__=='__main__':build()
