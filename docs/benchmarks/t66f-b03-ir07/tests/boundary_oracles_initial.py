"""IR07 독립 경계 및 byte oracle. 기대값은 literal 입력/native SQL에서 정한다."""
import hashlib, importlib.util, json, os, pathlib, sqlite3, sys, threading
import pytest
T=pathlib.Path(os.environ['IR07_TREE']);E=pathlib.Path(os.environ['IR07_EVIDENCE']);sys.path.insert(0,str(T/'backend'))
from isolated_sync import canonical
from isolated_sync.workers import NativeJob,WorkerLease
from unittest.mock import _patch

@pytest.fixture
def cost():
 s=importlib.util.spec_from_file_location('ir07_boundary',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 original=(canonical._parse_json,canonical.encode,hashlib.sha256,sqlite3.connect,NativeJob.__init__,NativeJob._finish,WorkerLease.run);patches=list(_patch._active_patches)
 yield m
 assert not m.INSTALLATIONS and m.ACTIVE.get() is None
 assert original==(canonical._parse_json,canonical.encode,hashlib.sha256,sqlite3.connect,NativeJob.__init__,NativeJob._finish,WorkerLease.run)
 assert list(_patch._active_patches)==patches

def emit(name,value):(E/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')

def test_current_state_on_each_activation(cost):
 m=cost;mon=sys.monitoring;tool=2;code=m.OwnershipContext.__enter__.__code__;c=m.Collector();rows=[]
 mon.use_tool_id(tool,'IR07 전환')
 try:
  for active in [False,True,False,True,False,True,False]:
   mon.set_local_events(tool,code,mon.events.PY_RETURN if active else 0)
   mon.free_tool_id(tool)
   if active:
    with pytest.raises(RuntimeError,match='monitoring entry observer unsupported'):
     with m.instrument():pytest.fail('활성 상태의 본문')
   else:
    with m.instrument(),c.stage('transfer'):canonical.decode_c1('"한😀"'.encode())
   assert not m.INSTALLATIONS and m.ACTIVE.get() is None
   rows.append({'active':active,'recorded_calls':int(c.values['transfer/json/calls']),'recorded_bytes':int(c.values['transfer/json/submitted_bytes'])})
   mon.use_tool_id(tool,'IR07 재할당')
  assert c.values['transfer/json/calls']==4 and c.values['transfer/json/submitted_bytes']==36
 finally:mon.set_local_events(tool,code,0);mon.free_tool_id(tool)
 emit('activation-transitions',rows)

@pytest.mark.parametrize('scope',['global','local'])
def test_ready_observes_real_other_thread_change(cost,monkeypatch,scope):
 m=cost;mon=sys.monitoring;tool=3;code=m.OwnershipContext.__enter__.__code__;mon.use_tool_id(tool,'IR07 경쟁');published=threading.Event();changed=threading.Event();errors=[];old=m.install_patch;first=[True];snap=[]
 def mutate():
  try:
   assert published.wait(10)
   if scope=='global':mon.set_events(tool,mon.events.PY_RETURN)
   else:mon.set_local_events(tool,code,mon.events.PY_RETURN)
   mon.free_tool_id(tool);changed.set()
  except BaseException as e:errors.append(repr(e));changed.set()
 def barrier(*args):
  old(*args)
  if first[0]:
   first[0]=False;snap.append({k:v['refs'] for k,v in m.INSTALLATIONS.items()});published.set();assert changed.wait(10)
 monkeypatch.setattr(m,'install_patch',barrier);thread=threading.Thread(target=mutate);thread.start()
 try:
  with pytest.raises(RuntimeError,match='monitoring entry observer unsupported'):
   with m.instrument():pytest.fail('관측된 변경 뒤 본문')
  thread.join(10);assert not thread.is_alive() and errors==[]
  assert not m.INSTALLATIONS and m.ACTIVE.get() is None
 finally:
  if mon.get_tool(tool) is None:mon.use_tool_id(tool,'IR07 정리')
  mon.set_events(tool,0);mon.set_local_events(tool,code,0);mon.free_tool_id(tool)
 c=m.Collector()
 with m.instrument(),c.stage('generation'):canonical.decode_c1(b'{}')
 assert c.values['generation/json/calls']==1 and c.values['generation/json/submitted_bytes']==2
 emit('ready-change-'+scope,{'acquired_before_unsupported_change':snap,'final_refs':{},'recovery_calls':1,'recovery_bytes':2,'classification':'지원 밖 설정 변경을 ready에서 관측한 rollback; 원자 보장 아님'})

def test_partial_entry_and_body_exception_preserve_survivor(cost,monkeypatch):
 m=cost;outer=m.Collector();original=m.install_patch;fired=[];native=canonical._parse_json
 def fail_after_patch(stack,target,name,value):
  original(stack,target,name,value)
  if target is NativeJob and name=='__init__' and not fired:fired.append(True);raise ValueError('IR07 획득 중 실패')
 monkeypatch.setattr(m,'install_patch',fail_after_patch)
 with m.instrument(),outer.stage('generation'):
  binding=m.ACTIVE.get();wrapper=canonical._parse_json
  with pytest.raises(ValueError,match='IR07 획득 중 실패'):
   with m.instrument_workers():pytest.fail('실패한 entry 본문')
  assert m.ACTIVE.get() is binding and canonical._parse_json is wrapper
  assert {k:v['refs'] for k,v in m.INSTALLATIONS.items()}=={'primitives':1}
  for _ in range(2):canonical.decode_c1(b'{}')
  with pytest.raises(LookupError):
   with m.instrument():raise LookupError('IR07 정상 진입 뒤 실패')
  assert m.ACTIVE.get() is binding and canonical._parse_json is wrapper
 assert fired==[True] and canonical._parse_json is native
 assert outer.values['generation/json/calls']==2 and outer.values['generation/json/submitted_bytes']==4
 emit('entry-exception-oracle',{'partial_entry_exception':True,'body_exception':True,'surviving_calls':2,'surviving_bytes':4,'final_refs':{}})

def test_hash_and_validation_independent_buffers(cost,monkeypatch):
 m=cost;sha=hashlib.sha256;native=canonical._parse_json;inputs=[];parsed=[];c=m.Collector()
 class Witness:
  def __init__(self,data=b'',**kw):inputs.append(bytes(data));self.inner=sha(data,**kw)
  def update(self,data):self.inner.update(data);inputs.append(bytes(data))
  def copy(self):
   x=object.__new__(Witness);x.inner=self.inner.copy();return x
  def __getattr__(self,key):return getattr(self.inner,key)
 monkeypatch.setattr(m,'NATIVE_HASH',Witness)
 raws=[b'{}','"한😀"'.encode(),b'{"a":',b'{ }',b'\xff']
 def profiler(frame,event,arg):
  if event=='call' and frame.f_code is native.__code__:parsed.append(bytes(frame.f_locals['raw']))
 sys.setprofile(profiler)
 try:
  with m.instrument(),c.stage('observation'):
   assert canonical.hash_bytes('hot',raws[1])==sha(b'money-note.sync.v1/hot\0'+raws[1]).hexdigest()
   h=hashlib.sha256(b'ab');h.update(b'c');clone=h.copy();clone.update(b'de');assert clone.hexdigest()==sha(b'abcde').hexdigest()
   with pytest.raises(TypeError):h.update('x')
   for raw in raws:
    try:canonical.decode_c1(raw)
    except canonical.CanonicalError:pass
 finally:sys.setprofile(None)
 # literal preimage prefix22 + raw9, streamed2+1+2 = 36B. JSON2+9+5+3+1 = 20B.
 assert len(b'money-note.sync.v1/hot\0')==22
 expected_hash=22+9+2+1+2
 assert sum(map(len,inputs))==expected_hash==int(c.values['observation/sha256/hash_input_bytes'])
 assert parsed==raws and sum(map(len,parsed))==20
 assert c.values['observation/json/calls']==5 and c.values['observation/json/submitted_bytes']==20
 assert c.values['observation/json/completed_bytes']==14 and c.values['observation/json/failed_submitted_bytes']==6
 emit('independent-byte-oracle',{'hash_native_input_lengths':[len(x) for x in inputs],'hash_expected':expected_hash,'hash_recorded':int(c.values['observation/sha256/hash_input_bytes']),'validation_input_hex':[x.hex() for x in parsed],'validation_submitted_expected':20,'validation_completed_expected':14,'validation_failed_expected':6,'snapshot':c.snapshot()})

def test_sql_literal_new_row_payload(cost):
 m=cost;c=m.Collector();db=sqlite3.connect(':memory:',isolation_level=None,factory=m.observed_factory())
 db.execute('CREATE TABLE p(k TEXT PRIMARY KEY,b BLOB)')
 def value(op,outcome,metric='blob_bytes'):return int(c.values[f'generation/p/{op}/{outcome}/{metric}'])
 with c.stage('generation'):
  db.execute('BEGIN');db.execute("/* first */ INSERT INTO p VALUES('a',x'01')")
  db.execute("SAVEPOINT s");db.execute("INSERT INTO p VALUES('b',x'0203')")
  db.execute('SAVEPOINT s');db.execute("INSERT INTO p VALUES('c',x'040506')");db.execute('ROLLBACK TO s');db.execute('RELEASE s')
  db.execute("INSERT OR IGNORE INTO p VALUES('a',x'0708090a')")
  db.execute('COMMIT')
 assert db.execute('SELECT k,length(b) FROM p ORDER BY k').fetchall()==[('a',1),('b',2)]
 assert [value('INSERT',x) for x in ['attempted','effective','committed','rolled_back']]==[10,6,3,3]
 with c.stage('generation'):
  db.execute('BEGIN');db.execute('ALTER TABLE p ADD COLUMN extra BLOB')
  db.execute("UPDATE p SET b=x'010203',extra=x'0405' WHERE k='a'")
  db.execute('ROLLBACK')
 assert [x[1] for x in db.execute('PRAGMA table_info(p)')]==['k','b']
 assert value('UPDATE','attempted')==5 and value('UPDATE','effective')==5 and value('UPDATE','committed')==0 and value('UPDATE','rolled_back')==5
 with c.stage('generation'):
  db.execute('DELETE FROM p WHERE k=?',('b',))
 assert value('DELETE','committed')==0 and db.execute('SELECT k,length(b) FROM p').fetchall()==[('a',1)]
 db.close();emit('sql-literal-oracle',{'insert_attempted':10,'insert_effective':6,'insert_committed':3,'insert_rolled_back':3,'update_attempted':5,'update_effective':5,'update_committed':0,'update_rolled_back':5,'delete_new_payload':0,'snapshot':c.snapshot()})
