"""고정 literal SQL ledger와 native SQLite 최종 상태를 사용하는 새 독립 oracle."""
from pathlib import Path
import importlib.util,json,sqlite3,sys
import pytest
A=Path('/tmp/money-note-ir04-20261024');T=A/'candidate';sys.path.insert(0,str(T/'backend'))
spec=importlib.util.spec_from_file_location('ir04_schema',T/'docs/benchmarks/t66f-b03/counters.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def get(c,t,op,phase,metric='blob_bytes'):return c.values[f'generation/{t}/{op}/{phase}/{metric}']
def dump(name,v):(A/'evidence'/(name+'.json')).write_text(json.dumps(v,ensure_ascii=False,indent=2))
@pytest.mark.parametrize('outcome',['commit','rollback','savepoint'])
def test_schema_literal_attempt_effect_commit(outcome):
 results=[]
 for observed in (False,True):
  d=sqlite3.connect(':memory:',isolation_level=None,factory=m.observed_factory() if observed else sqlite3.Connection);c=m.Collector()
  try:
   d.execute('CREATE TABLE p(id INTEGER PRIMARY KEY,b BLOB)')
   with c.stage('generation'):
    d.execute('INSERT INTO p VALUES(?,?)',(1,b'1'));d.execute('BEGIN')
    if outcome=='savepoint':d.execute('SAVEPOINT x')
    d.execute("ALTER TABLE p ADD COLUMN t TEXT DEFAULT '한'")
    d.execute('INSERT INTO p(id,b) VALUES(?,?)',(2,b'23'))
    d.execute('UPDATE p SET b=? WHERE id=2',(b'4567',))
    d.execute('INSERT INTO p VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET b=excluded.b,t=excluded.t',(2,b'890','😀'))
    d.execute('DELETE FROM p WHERE id=2')
    d.execute('CREATE TABLE q(b BLOB)');d.execute('INSERT INTO q VALUES(?)',(b'12345',))
    if outcome=='savepoint':
     d.execute('ROLLBACK TO x');d.execute('RELEASE x');d.execute('INSERT INTO p VALUES(?,?)',(3,b'123456'));d.execute('COMMIT')
    else:d.execute('COMMIT' if outcome=='commit' else 'ROLLBACK')
   native=lambda sql:sqlite3.Connection.execute(d,sql).fetchall()
   tables=native("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name");state={'tables':tables,'p':native('SELECT * FROM p'),'q':native('SELECT * FROM q') if tables==[('p',),('q',)] else None}
   results.append(repr(state))
   if observed:
    extra=6 if outcome=='savepoint' else 0
    assert get(c,'p','INSERT','attempted')==6+extra
    assert get(c,'p','INSERT','effective')==3+extra
    assert get(c,'p','INSERT','committed')==(3 if outcome=='commit' else 1+extra)
    assert get(c,'p','INSERT','attempted','text_bytes')==7 and get(c,'p','INSERT','effective','text_bytes')==3
    assert get(c,'p','UPDATE','attempted')==7 and get(c,'p','UPDATE','effective')==7
    assert get(c,'p','UPDATE','committed')==(7 if outcome=='commit' else 0)
    assert get(c,'p','UPDATE','attempted','text_bytes')==7 and get(c,'p','UPDATE','effective','text_bytes')==7
    assert get(c,'q','INSERT','attempted')==5 and get(c,'q','INSERT','effective')==5
    assert get(c,'q','INSERT','committed')==(5 if outcome=='commit' else 0)
    assert get(c,'p','DELETE','effective')==0 and get(c,'p','DELETE','effective','rows')==1
    if outcome!='commit':
     assert get(c,'p','INSERT','rolled_back')==2 and get(c,'p','UPDATE','rolled_back')==7 and get(c,'q','INSERT','rolled_back')==5
    dump('schema-ledger-'+outcome,{'state':repr(state),'counters':c.snapshot(),'expected_insert_attempt_effect': [6+extra,3+extra], 'outcome':outcome})
  finally:d.close()
 assert results[0]==results[1]

def test_same_cached_sql_native_reprepare():
 c=m.Collector();d=sqlite3.connect(':memory:',isolation_level=None,factory=m.observed_factory());d.execute('CREATE TABLE p(b BLOB)');sql='INSERT INTO p(b) VALUES(?)'
 try:
  with c.stage('generation'):
   d.execute(sql,(b'1',));d.execute("ALTER TABLE p ADD COLUMN extra BLOB DEFAULT x'0102'");d.execute(sql,(b'123',));d.execute('DROP TABLE p');d.execute('CREATE TABLE p(b BLOB)');d.execute(sql,(b'12',))
  assert sqlite3.Connection.execute(d,'SELECT b FROM p').fetchall()==[(b'12',)]
  for phase in ('attempted','effective','committed'):assert get(c,'p','INSERT',phase)==8
  dump('schema-cached-native',{'literal_ledger':[1,5,2],'counters':c.snapshot()})
 finally:d.close()

@pytest.mark.parametrize('replace',[False,True])
def test_external_ddl_explicit_incomplete_and_no_write(tmp_path,replace):
 path=tmp_path/'audit.sqlite';c=m.Collector();d=sqlite3.connect(path,isolation_level=None,factory=m.observed_factory());other=sqlite3.connect(path,isolation_level=None)
 try:
  d.execute('CREATE TABLE p(b BLOB)')
  with c.stage('generation'):d.execute("INSERT INTO p VALUES(x'01')")
  if replace:other.execute('DROP TABLE p');other.execute('CREATE TABLE p(b BLOB)')
  else:other.execute('ALTER TABLE p ADD COLUMN extra BLOB')
  before=other.execute('SELECT * FROM p').fetchall();prior=c.snapshot()
  with c.stage('generation'):
   for _ in range(2):
    with pytest.raises(RuntimeError,match='external schema change; measurement incomplete'):d.execute('INSERT INTO p(b) VALUES(?)',(b'123',))
  assert other.execute('SELECT * FROM p').fetchall()==before
  assert get(c,'p','INSERT','committed')==1 and get(c,'p','INSERT','attempted')==1 and get(c,'p','INSERT','effective')==1
  assert c.values['generation/coverage/external_schema_change']==2
  dump('schema-external-'+str(replace),{'native_before_after':repr(before),'prior':prior,'after':c.snapshot(),'rejected_before_new_row':True,'measurement_incomplete':True})
 finally:d.close();other.close()
