"""IR03 독립 기대값: literal preimage와 native SQLite 결과; 제품 source 변경 없음."""
import asyncio, gc, hashlib, importlib.util, json, sqlite3, sys, weakref
from collections import Counter
from pathlib import Path
import pytest
TREE=Path('/tmp/money-note-ir04-20261024/candidate');sys.path.insert(0,str(TREE/'backend'))
from isolated_sync import canonical
spec=importlib.util.spec_from_file_location('ir03_cost',TREE/'docs/benchmarks/t66f-b03/counters.py');cost=importlib.util.module_from_spec(spec);spec.loader.exec_module(cost)
OUT=Path(__file__).parent

def emit(name,data): (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def db(observed=True):
 d=sqlite3.connect(':memory:',isolation_level=None,factory=cost.observed_factory() if observed else sqlite3.Connection)
 d.execute('PRAGMA foreign_keys=ON');d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');return d

def get(c,op,outcome,metric='blob_bytes',table='payload',stage='generation'):return c.values[f'{stage}/{table}/{op}/{outcome}/{metric}']

@pytest.mark.parametrize('raw',[b'',b'{}','한😀e\u0301'.encode(),bytes(range(256)),b'x'*65537])
def test_native_hash_witness(raw,monkeypatch):
 events=[];native=hashlib.sha256
 class Witness:
  def __init__(self,data=b'',**kw):
   self.inner=native(data,**kw);events.append(bytes(data))
  def update(self,data):self.inner.update(data);events.append(bytes(data))
  def copy(self):
   result=object.__new__(Witness);result.inner=self.inner.copy();return result
  def __getattr__(self,name):return getattr(self.inner,name)
 monkeypatch.setattr(cost,'NATIVE_HASH',Witness)
 c=cost.Collector();expected=native(b'money-note.sync.v1/hot\0'+raw).hexdigest()
 with cost.instrument(),c.stage('generation'):
  assert canonical.hash_bytes('hot',raw)==expected
  h=hashlib.sha256(b'money-note.sync.v1/hot\0');h.update(memoryview(raw)[:2]);clone=h.copy();clone.update(memoryview(raw)[2:]);assert clone.hexdigest()==expected
  with pytest.raises(TypeError):h.update('invalid')
 assert sum(map(len,events))==2*(len(b'money-note.sync.v1/hot\0')+len(raw))
 assert c.values['generation/sha256/hash_input_bytes']==sum(map(len,events))
 before=c.snapshot();c.close()
 with c.stage('transfer'):cost.ObservedHash(b'late')
 assert c.snapshot()==before

@pytest.mark.parametrize('raw,parse_ok,c1_ok',[(b'{}',1,1),(b'{ }',1,0),('"한😀"'.encode(),1,1),(b'{"a":',0,0),(b'"\\ud800"',1,0),(b'\xff',0,0),(b'{"a":1,"a":2}',0,0),(b'{"a":1e999}',0,0),(b'[1,2,3]',1,1)])
def test_validation_literal_spans(raw,parse_ok,c1_ok):
 c=cost.Collector();other=cost.Collector()
 with cost.instrument(),c.stage('observation'):
  for _ in range(3):
   if c1_ok:canonical.decode_c1(raw)
   else:
    with pytest.raises(canonical.CanonicalError):canonical.decode_c1(raw)
  with other.stage('transfer'):canonical.decode_c1(b'{}')
 assert c.values['observation/json/submitted_bytes']==3*len(raw)
 assert c.values['observation/json/completed_bytes']==3*len(raw)*parse_ok
 assert c.values['observation/json/failed_submitted_bytes']==3*len(raw)*(1-parse_ok)
 assert other.values['transfer/json/submitted_bytes']==2
 assert not any(k.startswith('transfer/') for k in c.values)

@pytest.mark.parametrize('quoted',['s','"MiXeD"',"'a b'",'`a``b`','[a b]'])
def test_ia01_nearest_savepoint(quoted):
 c=cost.Collector();d=db()
 with c.stage('generation'):
  for sql in ['BEGIN',f'SAVEPOINT {quoted}',"INSERT INTO payload VALUES('a',x'01')",f'SAVEPOINT {quoted}',"INSERT INTO payload VALUES('b',x'0203')",f'ROLLBACK TO {quoted}',f'RELEASE {quoted}','COMMIT']:d.execute(sql)
 assert d.execute('SELECT k,length(b) FROM payload').fetchall()==[('a',1)]
 assert get(c,'INSERT','committed')==1;assert get(c,'INSERT','rolled_back')==2;d.close()

@pytest.mark.parametrize('mode,expected,stmt_rollback',[('FAIL',3,0),('ABORT',1,2),('ROLLBACK',0,0),('IGNORE',3,0)])
def test_ia02_conflicts_and_prefix(mode,expected,stmt_rollback):
 c=cost.Collector();d=db()
 with c.stage('generation'):
  d.execute('BEGIN');d.execute("INSERT INTO payload VALUES('prior',x'01')")
  try:d.execute(f"INSERT OR {mode} INTO payload VALUES('a',x'0203'),('prior',x'040506')")
  except sqlite3.IntegrityError:assert mode!='IGNORE'
  if d.in_transaction:d.execute('COMMIT')
 rows=d.execute('SELECT k,length(b) FROM payload ORDER BY k').fetchall()
 assert sum(n for _,n in rows)==expected
 assert get(c,'INSERT','committed')==expected
 assert get(c,'INSERT','statement_rolled_back')==stmt_rollback;d.close()

@pytest.mark.parametrize('prefix',['/* independent audit */ ','-- audit\n','; /* INSERT */ -- UPDATE\n '])
def test_ia03_first_comment(prefix):
 c=cost.Collector();d=db()
 with c.stage('generation'):d.execute(prefix+"INSERT INTO payload VALUES('a',x'0102')")
 assert d.execute('SELECT length(b) FROM payload').fetchone()==(2,);assert get(c,'INSERT','committed')==2;d.close()

def test_ia04_nested_install():
 c=cost.Collector()
 with cost.instrument(),c.stage('transfer'):
  canonical.decode_c1(b'{}')
  with cost.instrument():canonical.decode_c1(b'{}')
  canonical.decode_c1(b'{}')
 assert c.values['transfer/json/calls']==3;assert c.values['transfer/json/submitted_bytes']==6

def test_ia05_rejected_dispatch():
 from isolated_sync.workers import WorkerBudget
 async def run():
  c=cost.Collector();budget=WorkerBudget(1);lease=budget.acquire();lease.close();completed=[]
  with cost.instrument_workers(),c.stage('transfer'):
   with pytest.raises(RuntimeError,match='closed worker lease'):await lease.run(lambda:None)
  c.finish_when_idle(lambda x:completed.append(x.snapshot()))
  assert (c.pending,c.closed,len(completed))==(0,True,1)
  assert budget.snapshot()==dict(leases=0,jobs=0,running=0,tasks=0)
  emit('ia05-current',dict(pending=c.pending,closed=c.closed,completions=len(completed),native=budget.snapshot()))
 asyncio.run(run())

def test_ia06_owner32_before_execution_and_release():
 c=cost.Collector();d=db();d.execute('BEGIN');refs=[]
 for i in range(32):
  owner=cost.Collector();refs.append(weakref.ref(owner))
  with owner.stage('generation'):d.execute('INSERT INTO payload VALUES(?,?)',(str(i),b'x'))
  owner.close()
 del owner;gc.collect();assert sum(r() is not None for r in refs)==32
 with c.stage('generation'):
  with pytest.raises(RuntimeError,match='owner capacity'):d.execute("INSERT INTO payload VALUES('blocked',x'01')")
 assert d.execute('SELECT count(*) FROM payload').fetchone()==(32,)
 d.execute('ROLLBACK');gc.collect();assert sum(r() is not None for r in refs)==0
 emit('ia06-current',{'accepted_owners':32,'rejected_before_write':True,'retained_after_rollback':0});d.close()

def test_utf8_upsert_ignore_update_delete_and_rollback():
 c=cost.Collector();d=db()
 with c.stage('generation'):
  d.execute('BEGIN');d.execute('INSERT INTO payload VALUES(?,?)',('한😀',b'12'))
  d.execute('INSERT OR IGNORE INTO payload VALUES(?,?)',('한😀',b'ignored'))
  d.execute('INSERT INTO payload VALUES(?,?) ON CONFLICT(k) DO UPDATE SET b=excluded.b',('한😀',b'abc'))
  d.execute('UPDATE payload SET b=? WHERE k=?',(b'12345','한😀'))
  d.execute('DELETE FROM payload WHERE k=?',('한😀',));d.execute('COMMIT')
 assert get(c,'INSERT','attempted')==12
 assert get(c,'INSERT','effective')==2 and get(c,'INSERT','committed')==2
 assert get(c,'UPDATE','effective')==8 and get(c,'UPDATE','committed')==8
 assert get(c,'UPDATE','committed','text_bytes')==14
 assert get(c,'DELETE','effective')==0 and get(c,'DELETE','effective','rows')==1
 assert d.execute('SELECT count(*) FROM payload').fetchone()==(0,);d.close()

def test_partial_executemany_iterator_error():
 c=cost.Collector();d=db()
 def rows():
  yield ('a',b'1');yield ('b',b'23');raise ValueError('iterator')
 with c.stage('generation'):
  d.execute('BEGIN')
  with pytest.raises(ValueError):d.executemany('INSERT INTO payload VALUES(?,?)',rows())
  d.execute('COMMIT')
 assert d.execute('SELECT sum(length(b)) FROM payload').fetchone()==(3,)
 assert get(c,'INSERT','committed')==3;d.close()

def test_failed_deferred_commit_then_rollback():
 c=cost.Collector();d=db();d.execute('CREATE TABLE child(k TEXT REFERENCES payload(k) DEFERRABLE INITIALLY DEFERRED,b BLOB)')
 with c.stage('generation'):
  d.execute('BEGIN');d.execute("INSERT INTO child VALUES('absent',x'0102')")
  with pytest.raises(sqlite3.IntegrityError):d.commit()
  assert d.in_transaction;assert get(c,'INSERT','committed',table='child')==0;d.rollback()
 assert get(c,'INSERT','rolled_back',table='child')==2;d.close()

def test_closed_collector_snapshot_does_not_reopen_on_commit():
 c=cost.Collector();d=db()
 with c.stage('generation'):d.execute('BEGIN');d.execute("INSERT INTO payload VALUES('a',x'0102')")
 c.close();before=c.snapshot();d.commit();assert c.snapshot()==before;d.close()

@pytest.mark.parametrize('operation',['alter','drop_recreate'])
def test_ddl_observer_reinstallation(operation):
 c=cost.Collector();d=db()
 with c.stage('generation'):
  d.execute("INSERT INTO payload VALUES('initial',x'01')")
  if operation=='alter':
   d.execute('ALTER TABLE payload ADD COLUMN extra BLOB');d.execute("INSERT INTO payload VALUES('next',x'0203',x'040506')");expected=6
   oracle=d.execute('SELECT sum(length(b))+sum(COALESCE(length(extra),0)) FROM payload').fetchone()[0]
  else:
   d.execute('DROP TABLE payload');d.execute('CREATE TABLE payload(k TEXT PRIMARY KEY,b BLOB)');d.execute("INSERT INTO payload VALUES('next',x'020304')");expected=4
   oracle=1+d.execute('SELECT sum(length(b)) FROM payload').fetchone()[0]
 actual=get(c,'INSERT','committed');emit('new-ddl-'+operation,dict(expected=expected,native_payload_oracle=oracle,actual=actual,counters=c.snapshot()))
 assert oracle==expected;assert actual==expected
 d.close()
