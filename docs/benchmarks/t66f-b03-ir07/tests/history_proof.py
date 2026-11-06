"""IR07에서 구현 측 과거 증거의 source 연결과 원문 집계만 검증한다."""
import ast,gzip,hashlib,json,pathlib,xml.etree.ElementTree as ET
R=pathlib.Path('/home/hjkerman/codex/money-note');W=pathlib.Path('/tmp/money-note-t66f-b03-ir07-20261025');T=W/'tree';E=R/'docs/benchmarks/t66f-b03-ir07';C=W/'context/docs/benchmarks/t66f-b03-ic06/evidence'
sha=lambda b:hashlib.sha256(b).hexdigest()
old=json.loads((T/'docs/benchmarks/t66f-b03-ic05/corrected-candidate-manifest.json').read_bytes());new=json.loads(pathlib.Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8/source-manifest.json').read_bytes());n={x['path']:x for x in new['entries']};changed=[x['path'] for x in old['entries'] if x['sha256']!=n[x['path']]['sha256'] or x['mode']!=n[x['path']]['mode']];assert changed==['docs/benchmarks/t66f-b03/counters.py']
a=ast.parse(gzip.open(C/'baseline-counters.py.gz','rt').read());b=ast.parse((T/'docs/benchmarks/t66f-b03/counters.py').read_text())
def nodes(t):return {x.name:ast.dump(x,include_attributes=False) for x in t.body if hasattr(x,'name')}
x,y=nodes(a),nodes(b);assert x.keys()==y.keys();assert [k for k in x if x[k]!=y[k]]==['EntryHandoff']
a=next(x for x in a.body if getattr(x,'name',None)=='EntryHandoff');b=next(x for x in b.body if getattr(x,'name',None)=='EntryHandoff');x,y=nodes(a),nodes(b);assert [k for k in x if x[k]!=y[k]]==['check_monitoring']
rec={'changed_from_ic05':changed,'changed_ast_methods':['EntryHandoff.check_monitoring'],'product_source_changed_from_ic05':False,'source_lock_expectations_changed':False}
v=json.loads((C/'backend-supported-complete.json').read_text());assert v['exit_code']==0
for p,h in v['source_after'].items():assert sha((T/p).read_bytes())==h
xml=ET.parse(C/'backend-supported-complete.xml').getroot();cases=list(xml.iter('testcase'));assert len(cases)==1880 and not list(xml.iter('failure')) and not list(xml.iter('error')) and not list(xml.iter('skipped'))
footer=gzip.open(C/'backend-supported-complete.log.gz','rt').read().splitlines()[-1];assert '1880 passed' in footer and '1540 subtests passed' in footer
rec['historical_backend']={'testcases':1880,'subtests':1540,'exit_code':0,'footer':footer,'source_matches_frozen':True,'fresh':False}
v=json.loads((C/'flutter-affected.json').read_text());done=[];counts={'PASS':0,'FAIL':0,'SKIP':0}
for line in gzip.open(C/'flutter-affected.log.gz','rt'):
 try:ev=json.loads(line)
 except ValueError:continue
 if not isinstance(ev,dict):continue
 if ev.get('type')=='testDone' and not ev.get('hidden'):counts['SKIP' if ev.get('skipped') else 'PASS' if ev.get('result')=='success' else 'FAIL']+=1
 if ev.get('type')=='done':done.append(ev.get('success'))
assert counts=={'PASS':110,'FAIL':0,'SKIP':0} and done==[True]
for p,h in v['source_before'].items():
 if p!='backend/tests/test_logical_cost_ic06.py':assert sha((T/p).read_bytes())==h
rec['historical_flutter']={'counts':counts,'done':done,'fresh':False,'test_source_change_during_run':'IC06 Python test에 callback 검사6건 추가; Dart/실행 구현의 전후 SHA 동일'}
(E/'historical-regression-traceability.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
(E/'tooling-incidents.json').write_text(json.dumps({'initial_backend_collection':{'result':'실행 환경 오류','cause':'복원본 IC06/evidence 디렉터리 부재','tests_executed':0,'recovered':'출력 디렉터리 준비 후 backend-affected-final 512건 통과'},'initial_new_byte_oracle':{'result':'감사 도구의 literal 길이 오류','expected_before':22,'literal_prefix_bytes':23,'corrected_hash_total':37,'product_or_preserved_assertions_changed':False,'initial_source':'tests/boundary_oracles_initial.py','raw':'independent-boundaries.log.gz','final':'independent-boundaries-final.xml'},'historical_machine_log_parser':{'result':'일반 JSON 배열 출력을 event dict로 취급한 집계 도구 오류','correction':'dict event만 집계; suite 반복 없음'},'original_ia06_exit1':{'result':'예상한 지원 한도 거부','reason':'owner33을 SQL 실행 전에 명시 거부; historical-python strict oracle가 rollback weakref0 확인'}},ensure_ascii=False,indent=2)+'\n')
print({'source_change':changed,'historical_backend':1880,'historical_subtests':1540,'historical_flutter':counts})
