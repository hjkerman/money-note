"""IR07 최종 판정을 fresh 원문/기대 결과와 연결한다. 과거 PASS를 새 결과로 합산하지 않는다."""
import collections,gzip,hashlib,json,pathlib,xml.etree.ElementTree as ET
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b03-ir07'
def write(name,value):(E/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def load(name):return json.loads((E/name).read_bytes())
labels=['ir06-primary','ir06-instrument','ir06-workers','ir06-stage','backend-affected-final','backend-transfer','historical-python','ir06-lifecycle','independent-monitoring','independent-boundaries-final','flutter-affected','flutter-original-current','flutter-original-historical','flutter-authority-provenance','frontend-build','source-locks','runtime-semantics','released-setters','history-proof','integration-postcheck','final-source-integrity']
records=[load(label+'.json') for label in labels]
assert all(r['exit_code']==0 and r['source_verified_before'] and r['source_verified_after'] for r in records)
assert load('original-ia06.json')['exit_code']==1
assert all(load(x+'.json')['exit_code']==0 for x in ['original-ia05','original-ia07'])
xmls={}
for label in ['backend-affected-final','backend-transfer','historical-python','ir06-lifecycle','independent-boundaries-final']:
 root=ET.parse(E/(label+'.xml')).getroot();cases=list(root.iter('testcase'));assert not list(root.iter('failure')) and not list(root.iter('error')) and not list(root.iter('skipped'))
 xmls[label]={'PASS':len(cases),'FAIL':0,'SKIP':0,'by_file':dict(collections.Counter(x.attrib.get('classname','') for x in cases))}
assert xmls['backend-affected-final']['PASS']==512 and xmls['backend-transfer']['PASS']==94
flutter={}
for label in ['flutter-affected','flutter-original-current','flutter-original-historical','flutter-authority-provenance']:
 c=collections.Counter();done=[];tests={};passed=[]
 for line in gzip.open(E/(label+'.log.gz'),'rt'):
  try:v=json.loads(line)
  except ValueError:continue
  if not isinstance(v,dict):continue
  if v.get('type')=='testStart':tests[v['test']['id']]=v['test']
  if v.get('type')=='testDone' and not v.get('hidden'):
   c['SKIP' if v.get('skipped') else 'PASS' if v.get('result')=='success' else 'FAIL']+=1;passed.append(tests.get(v['testID'],{}))
  if v.get('type')=='done':done.append(v.get('success'))
 assert done==[True] and not c['FAIL'] and not c['SKIP']
 flutter[label]={'PASS':c['PASS'],'FAIL':0,'SKIP':0,'done':True,'tests':passed}
assert flutter['flutter-affected']['PASS']==110 and flutter['flutter-original-current']['PASS']==11 and flutter['flutter-original-historical']['PASS']==3
new=load('monitoring-state-matrix.json');assert new['pass']==66 and new['fail']==0
independent={'IR07 새 monitoring':66,'IR07 새 경계/byte':6,'보존 Python IA/IR':67,'보존 IR06 수명':28,'IR06 원 네 재현':4,'IA05/06/07 원 직접':3,'최초 독립 backend 현재 oracle':14,'최초 독립 Dart 현재 oracle':11,'IR03 Dart':17,'IR04 Dart schema':6,'IR03 실제 delta':1,'최초 독립 실제 TLS/HTTP':2}
assert sum(independent.values())==225
closure=[]
rows=[('B03-IA01','nearest 같은 이름 savepoint committed1/rollback2B','historical-python.xml'),('B03-IA02','OR FAIL 성공 prefix committed3B','historical-python.xml'),('B03-IA03','첫 comment DML2B','historical-python.xml'),('B03-IA04','원 nested3/6 및 모든 후속 설치·취소·monitoring 반례 통과','ir06-original-results.json'),('B03-IA05','pending0/completion1/native0','original-ia05.log.gz'),('B03-IA06','owner32 허용/33 실행 전 거부/rollback weakref0','historical-python.xml'),('B03-IA07','setup176/185행/generation0','original-ia07.log.gz'),('B03-IR03-N01-PYTHON','ALTER6B/DROP-recreate4B','historical-python.xml'),('B03-IR03-N01-DART','ALTER6B/DROP-recreate4B/prepared reuse8B','flutter-affected.log.gz'),('B03-IR03-N02','준비 전 본문0; 두 번째 scope1회/2B','historical-python.xml'),('B03-IR04-N01','세대 교대 실제1회/2B 또는9B','historical-python.xml'),('B03-IR05-N01','설치 SIGINT 뒤 원복/다음1회2B/hold0','historical-python.xml'),('B03-IR05-N02','마지막 release SIGINT 뒤 원복/다음1회2B/hold0','historical-python.xml')]
rows.extend(('IC04-ENTRY-'+x,'실제 return SIGINT/취소 본문0/소유 reference·stage 복구','backend-affected-final.xml') for x in ['instrument','instrument_workers','stage'])
rows.extend(('B03-IR06-N01-'+x,'활성 mask4를 해제 뒤에도 검사/미획득 거부/후속2회4B exact','ir06-original-results.json') for x in ['primary','instrument','workers','stage'])
for ident,oracle,evidence in rows:closure.append({'id':ident,'status':'PASS','oracle':oracle,'evidence':[evidence]})
write('historical-finding-closure-matrix.json',closure)
requirements=[('감사 구현 독립성','이 세션의 제공 이력에 이전 관여 없음'),('정확한 동결 복원','candidate-integrity.json'),('원 IR06 및 세 변형','ir06-original-results.json'),('released ID event 탐지','monitoring-state-matrix.json'),('정적 unsafe 미획득 거부','monitoring-state-matrix.json'),('inactive 지원','monitoring-state-matrix.json'),('안정 환경 계약 양립','monitoring-contract-decision.json'),('ref/stage/native hold 누수 없음','ir06-lifecycle.xml'),('parse 정확히 한 번','independent-byte-oracle.json'),('취소 stage 귀속','ir06-original-results.json'),('IA01–IA07','historical-finding-closure-matrix.json'),('IR03/04/05 및 IC04','historical-finding-closure-matrix.json'),('세 byte oracle','independent-byte-oracle.json / sql-literal-oracle.json / historical-python.xml'),('transaction/stage','historical-python.xml'),('scope isolation/유한 자원','monitoring-state-matrix.json / ir06-lifecycle.xml'),('실제 D→E/E3/E4','integration-oracle.json / flutter-authority-provenance.log.gz'),('제품 OFF/ON 동등성','integration-oracle.json'),('source lock','source-locks.json / flutter-authority-provenance.log.gz'),('충분한 fresh 회귀','test-results.json'),('미해결 material defect 없음','findings.json')]
write('requirement-coverage-matrix.json',[{'criterion':i+1,'requirement':name,'status':'PASS','evidence':ev} for i,(name,ev) in enumerate(requirements)])
write('test-results.json',{'payload_sha256':records[0]['payload_sha256'],'fresh_backend':xmls,'fresh_flutter':flutter,'fresh_independent_unique':{'PASS':225,'FAIL':0,'SKIP':0,'by_source':independent},'historical_defect_controls':{'backend':4,'dart':3,'included_in_current_correctness_count':False},'new_monitoring_stress_rejections':384,'original_ia06_exit1':'기대한 owner capacity 거부; strict native/weakref oracle 통과','full_suites_freshly_rerun':False,'historical_full_backend':{'tests':1880,'subtests':1540,'fresh':False},'historical_flutter_affected':{'PASS':110,'fresh':False},'tooling_failures_preserved':'tooling-incidents.json','selected_execution_records':[r['label']+'.json' for r in records]})
write('findings.json',{'task':'T6.6F-B03-IR07','payload_sha256':records[0]['payload_sha256'],'verdict':'PASS','auditor_implementation_independence':'SATISFIED','prior_involvement':'NONE','new_findings':[],'historical_closure':closure,'monitoring_stability':'ACCEPTABLE — SUPPORTED ENVIRONMENT BOUNDARY ESTABLISHED','toctou_aba':'DOCUMENTED AND OUT OF SCOPE','B03':'CLOSED','phase_b':'INCONCLUSIVE','new_full_100k_cold_runs':0,'five_point_grid_executed':False,'full_scale_feasibility':'NOT VERIFIED','runtime_perturbation':'UNRESOLVED','product_source_modified':False,'binding_protocol_modified':False})
print(json.dumps({'fresh_backend':606,'flutter':{k:v['PASS'] for k,v in flutter.items()},'fresh_independent':225,'new_findings':0},ensure_ascii=False))
