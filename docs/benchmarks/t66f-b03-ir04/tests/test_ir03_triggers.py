"""고정 operation ledger와 별도 native DB로 trigger/cascade/rollback 비용 대조."""
import importlib.util,json,sqlite3,sys
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');sys.path.insert(0,str(r/'candidate/backend'))
spec=importlib.util.spec_from_file_location('ir03_trigger_cost',r/'candidate/docs/benchmarks/t66f-b03/counters.py');cost=importlib.util.module_from_spec(spec);spec.loader.exec_module(cost)

def test_native_trigger_cascade_and_savepoint_event_payload():
 statements=[('PRAGMA foreign_keys=ON',()),('CREATE TABLE parent(k TEXT PRIMARY KEY,b BLOB)',()),('CREATE TABLE child(k TEXT REFERENCES parent(k) ON DELETE CASCADE,b BLOB)',()),("CREATE TRIGGER linked AFTER INSERT ON parent BEGIN INSERT INTO child VALUES(NEW.k,x'0a0b0c'); END",()),('BEGIN',()),('INSERT INTO parent VALUES(?,?)',('한😀',b'12')),('UPDATE parent SET b=? WHERE k=?',(b'abcd','한😀')),('SAVEPOINT s',()),('INSERT INTO parent VALUES(?,?)',('b',b'3')),('ROLLBACK TO s',()),('RELEASE s',()),('DELETE FROM parent WHERE k=?',('한😀',)),('COMMIT',())]
 c=cost.Collector();observed=sqlite3.connect(':memory:',isolation_level=None,factory=cost.observed_factory());native=sqlite3.connect(':memory:',isolation_level=None)
 try:
  with c.stage('generation'):
   for sql,args in statements:observed.execute(sql,args)
  for sql,args in statements:native.execute(sql,args)
  for table in ['parent','child']:
   assert native.execute('SELECT * FROM '+table).fetchall()==observed.execute('SELECT * FROM '+table).fetchall()==[]
  expected={'generation/parent/INSERT/committed/blob_bytes':2,'generation/child/INSERT/committed/blob_bytes':3,'generation/parent/UPDATE/committed/blob_bytes':4,'generation/parent/INSERT/rolled_back/blob_bytes':1,'generation/child/INSERT/rolled_back/blob_bytes':3,'generation/parent/INSERT/attempted/text_bytes':8,'generation/child/INSERT/attempted/text_bytes':8,'generation/parent/UPDATE/committed/text_bytes':7,'generation/parent/DELETE/effective/rows':1,'generation/child/DELETE/effective/rows':1}
  for key,value in expected.items():assert c.values[key]==value
  (r/'evidence/trigger-cascade.json').write_text(json.dumps({'expected':expected,'actual':c.snapshot(),'native_final_rows':0},indent=2)+'\n')
 finally:observed.close();native.close()
