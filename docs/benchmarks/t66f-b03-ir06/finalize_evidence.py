"""IR06 증거 집계. 과거 보고서·후보·index를 쓰지 않는다."""
from pathlib import Path
import gzip
import json
import tarfile

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
SCRATCH=ROOT/'work/t66f-b03-ir06'
E=OUT/'evidence'

def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

rows=[]
conditions={
    'IA01':'동일 이름 SAVEPOINT의 nearest rollback: committed1/rollback2B',
    'IA02':'OR FAIL 성공 prefix: committed3B',
    'IA03':'첫 comment DML:2B',
    'IA04':'원 nested3회/6B는 통과하지만 IR06-N01이 전체 수명을 차단',
    'IA05':'closed dispatch 거부: pending0/completion1/native0',
    'IA06':'owner32/33 실행 전 거부 및 rollback 후 weakref0',
    'IA07':'원 oracle SELECT setup176/185행, generation0',
}
for k,oracle in conditions.items():
    rows.append(dict(id='B03-'+k,original_reproducer_status='PASS',status='FAIL' if k=='IA04' else 'PASS',independent_oracle=oracle,evidence=['historical-python.xml','original-direct.json','backend-affected.xml','flutter-affected-recovered.json']))
for k,oracle in [
    ('IR03-N01-PYTHON','ALTER6B/DROP-recreate4B 및 schema invalidation'),
    ('IR03-N01-DART','ALTER6B/DROP-recreate4B 및 prepared reuse8B'),
    ('IR03-N02','동시 first-install ready 전 본문0, 이후 parse1회/2B'),
    ('IR04-N01','원 rollover ASCII2B/Unicode9B: native1/reported1'),
    ('IR05-N01','원 SIGINT patch 직후 cleanup 예약·다음 parse1/2B·worker hold0'),
    ('IR05-N02','원 SIGINT last reference 복원·다음 parse1/2B·worker hold0'),
]:rows.append(dict(id='B03-'+k,status='PASS',original_reproducer_status='PASS',independent_oracle=oracle,evidence=['historical-python.xml','flutter-affected-recovered.json','backend-affected.xml']))
for family in ['instrument','instrument_workers','stage']:
    rows.append(dict(id='IC04-OPEN-HANDOFF/'+family,status='PASS',original_reproducer_status='PASS',source_sha256='0337cdf6daa6410e9cb454f64d57f0d71ccbc26aa2c02b070081158b16b2cd22',evidence=['original-ic04-three.xml','outer-enter-return-'+family+'.json']))

new={
    'id':'B03-IR06-N01','severity':'MEDIUM','status':'FAIL','blocks_ia04':True,'blocks_b03':True,
    'title':'해제된 PEP669 tool ID의 활성 event를 건너뛰어 진입 반환 중단 후 reference와 stage가 잔존',
    'source':[
        {'path':'docs/benchmarks/t66f-b03/counters.py','line':127,'boundary':'EntryHandoff.check_monitoring의 get_tool(tool) is not None 조건'},
        {'path':'docs/benchmarks/t66f-b03/counters.py','line':280,'boundary':'OwnershipContext.__enter__ 반환 observer와 caller cleanup 인계'},
    ],
    'runtime':'CPython3.12.3',
    'schedule':[
        '미사용 ID를 use_tool_id로 확보',
        'PY_RETURN callback 등록 및 OwnershipContext.__enter__ code의 local event 활성화',
        'free_tool_id; get_tool=None이나 local mask4와 callback 유지',
        'with context의 실제 PY_RETURN callback이 RuntimeError 발생',
        'caller body/exit 미실행; reference 및 stage 관찰',
        'monitor 설정 해제 후 실제 native parse 두 번과 귀속 관찰',
    ],
    'expected':{'preacquisition_rejection':'B03 monitoring entry observer unsupported; measurement incomplete','minimal_refs_after':0,'wrapper_restored':True,'repeated_primitive_refs_including_survivor':1,'repeated_worker_refs':0,'cancelled_stage_calls':0,'cancelled_stage_bytes':0,'survivor_calls':2,'survivor_bytes':4},
    'actual':{'minimal_refs_after':1,'wrapper_restored':False,'callback_fired':1,'body_executions':0,'repeated_rounds':8,'repeated_primitive_refs_including_survivor':9,'repeated_worker_refs':8,'cancelled_stage_calls':2,'cancelled_stage_bytes':4,'survivor_calls_in_stage_case':0,'survivor_bytes_in_stage_case':0,'real_native_calls':2,'real_native_bytes':4,'native_hold_after':0,'native_budget_after':{'leases':0,'jobs':0,'running':0,'tasks':0}},
    'oracle':'문서화된 sys.monitoring API와 실제 callback/frame/input. 진단 registry는 추가 불변식이며 expected를 registry에서 유도하지 않음. 같은 bytes 두 native 호출은2회/4B다.',
    'product_impact':'금융/파싱 결과 변경은 재현되지 않음. 진단 사전 거부·정확한 귀속·취소 자원 수명 실패.',
    'contract_adjudication':'custom PEP669 지원을 추가 요구하지 않는다. 명시된 unsupported configuration의 pre-acquisition rejection이 실제 활성 observer를 놓치는 결함이다.',
    'restriction_classification':'FAIL — REJECTION LEAVES PARTIAL DIAGNOSTIC STATE (해당 상태에서는 사전 거부 자체가 누락됨)',
    'minimum_correction_boundary':'EntryHandoff.check_monitoring에서 tool 이름과 실제 활성 global/local events를 구분하는 탐지 경계 및 획득 전 거부 보장. 감사에서 수정하지 않음.',
    'minimal_reproducer':'tests/pep669_released_tool_probe.py',
    'evidence':['pep669-released-tool-confirmed.json','pep669-released-tool-confirmed.log.gz','monitoring-instrument.json','monitoring-instrument_workers.json','monitoring-stage.json','monitoring-matrix-results.json'],
    'primary_reference':'https://docs.python.org/3.12/library/sys.monitoring.html#sys.monitoring.free_tool_id',
}
records={}
for label in ['pep669-released-tool-confirmed','monitoring-instrument','monitoring-instrument_workers','monitoring-stage']:
    log=gzip.open(E/(label+'.log.gz'),'rt').read()
    records[label]=json.loads(next(x for x in log.splitlines() if x.startswith('{')))
write(E/'monitoring-matrix-results.json',records)
write(OUT/'findings.json',dict(schema_version=1,task='T6.6F-B03-IR06',payload_sha256='47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5',auditor_implementation_independence='SATISFIED',prior_audit_involvement='NONE',verdict='FAIL',b03_correctness='OPEN — FAIL',prior_findings=rows,new_findings=[new],new_full_100k_cold_attempts=0,phase_b='INCONCLUSIVE'))

matrix=[]
for scenario,result,evidence in [
    ('entry 내부 예외','PASS','backend-affected.xml / IC04 transitions'),
    ('진입 반환 및 caller handoff','FAIL','legacy20 PASS; monitoring-stage.json FAIL'),
    ('성공 entry 직후 본문 실패','PASS','cleanup-recovery.json'),
    ('중첩 entry 실패와 외부 scope','PASS','entry-stage-trace-True.json 등20개'),
    ('동시 활성화 중 한 task 취소','PASS','async-native-tail.json / historical-python.xml'),
    ('teardown과 새 activation','PASS','historical-python.xml / IR04·IR05 lifecycle'),
    ('마지막 reference release 중단','PASS','historical-python.xml / IR05-N02'),
    ('cleanup 예외의 명시 실패·복구','PASS','cleanup-recovery.json'),
    ('취소 entry 반복','FAIL','monitoring-instrument.json / monitoring-instrument_workers.json'),
    ('후속 성공 entry의 exact 계수','PASS','stateful-6606.json 등3개 / legacy 경계'),
    ('native hold 획득 뒤 실패','PASS','backend-affected.xml / IC04 native hold transitions'),
    ('late native completion와 close','PASS','async-native-tail.json'),
    ('동일 bytes의 두 실제 parse','PASS','monitoring-matrix-results.json 및 stateful ledger'),
    ('취소된 stage 뒤 실제 parse','FAIL','monitoring-stage.json'),
]:matrix.append(dict(scenario=scenario,result=result,evidence=evidence))
write(OUT/'cancellation-matrix.json',dict(rows=matrix,not_reachable=[
    dict(scenario='동기 entry 임의 명령 사이에 ordinary Task.cancel 전달',reason='entry에 await가 없으며 이벤트 루프 전달은 다음 실제 suspension에서 발생; 실제 await cancel과 return-hook request를 구별해 검증'),
    dict(scenario='INSTALL_LOCK을 다른 thread가 동시에 소유하며 teardown 중간 delegate 캡처',reason='동일 RLock이 복원과 신규 reference/capture를 직렬화; lock 대기/해제 전후 실제 barrier 시험은 별도 PASS'),
    dict(scenario='worker thread에서 Python SIGINT handler 직접 실행',reason='Python signal handler는 main thread에서 실행; worker ordinary exception/native completion은 별도 검증'),
]))
for sub in ['originals','dart-originals']:
    with tarfile.open(E/(sub+'.tar.gz'),'w:gz') as tar:tar.add(SCRATCH/sub,arcname=sub)
for fn in ['http-n9.json','http-n260.json','http-concurrent.json','http-frozen.json']:
    with gzip.open(E/(fn+'.gz'),'wb') as g:g.write((SCRATCH/fn).read_bytes())
print(json.dumps({'new_findings':1,'severity':'MEDIUM','prior_entries':len(rows),'transition_rows':len(matrix)}))
