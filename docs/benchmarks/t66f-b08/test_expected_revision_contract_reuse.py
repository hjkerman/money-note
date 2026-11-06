"""기대 계약 재사용이 실제 DB 검사를 가리지 않는지 독립 기대값으로 검증한다."""
import ast
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
import re
import sqlite3
import pytest
from app import db_migrations as m

assert Path(m.__file__).resolve() == Path(__file__).resolve().parents[1]/'app/db_migrations.py'
# 원 B03 함수의 동일 AST를 독립 oracle로 보존한다.
_statements=m._statements
_revision_trigger_contract=m._revision_trigger_contract
def reference(conn: sqlite3.Connection, schema: str) -> None:
    expected = [_revision_trigger_contract(statement) for statement in _statements(schema)
                if re.match(r"CREATE TRIGGER IF NOT EXISTS revision_", statement)]
    trigger_rows = conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'").fetchall()
    actual = {row[0]: (row[1], _revision_trigger_contract(row[2] or "")) for row in trigger_rows}
    expected_names = {contract[0] for contract in expected if contract is not None}
    revision_tables = {contract[2] for contract in expected if contract is not None}
    for name, table, sql in trigger_rows:
        if name not in expected_names and (
            table in revision_tables or "authoritative_state_revision" in str(sql).lower()
        ):
            raise RuntimeError("current database version has unexpected authoritative revision trigger")
    for contract in expected:
        if contract is None or actual.get(contract[0]) != (contract[2], contract):
            raise RuntimeError("current database version has invalid authoritative revision trigger")
    state = conn.execute("SELECT id, revision, typeof(revision) FROM authoritative_state_revision").fetchall()
    if len(state) != 1 or state[0][0] != 1 or state[0][2] != "integer" or state[0][1] < 0:
        raise RuntimeError("current database version has invalid authoritative revision state")

def schema(table='t',step=1):
 return f'''CREATE TABLE authoritative_state_revision(id INTEGER, revision);
CREATE TABLE {table}(v INTEGER);
CREATE TABLE unrelated(v INTEGER);
CREATE TRIGGER IF NOT EXISTS revision_{table}_insert AFTER INSERT ON {table} BEGIN
UPDATE authoritative_state_revision SET revision=revision+{step} WHERE id=1;
END;
'''
A=schema();B=schema(step=2)
LITERAL=('revision_t_insert','INSERT','t',('update','authoritative_state_revision','set','revision','=','revision','+','1','where','id','=','1',';'))
class Recorded(sqlite3.Connection):
 def execute(self,sql,*a,**kw):
  if not hasattr(self,'reads'):self.reads=[]
  self.reads.append(sql)
  return super().execute(sql,*a,**kw)

def db(s=A):
 c=sqlite3.connect(':memory:',factory=Recorded);c.executescript(s);c.execute('INSERT INTO authoritative_state_revision VALUES(1,0)');c.reads=[];return c

def outcome(fn,c,s):
 try:fn(c,s);return None
 except Exception as e:return type(e),str(e)

def equal(c,s=A,error=None):
 expected=outcome(reference,c,s);actual=outcome(m._validate_revision_triggers,c,s)
 assert actual==expected
 if error is None:assert actual is None
 else:assert actual and error in actual[1]
 return actual

@pytest.fixture(autouse=True)
def empty_cache():
 m._expected_revision_contract.cache_clear()
 yield
 m._expected_revision_contract.cache_clear()

def test_literal_contract_and_recursive_immutability():
 value=m._expected_revision_contract(A)
 assert value==((LITERAL,),frozenset({'revision_t_insert'}),frozenset({'t'}))
 def frozen(v):
  assert type(v) in [str,tuple,frozenset,type(None)]
  if isinstance(v,(tuple,frozenset)):
   for child in v:frozen(child)
 frozen(value)
 with pytest.raises(TypeError):value[0][0][3][0]='drop'
 with pytest.raises(AttributeError):value[1].add('unknown')
 assert m._expected_revision_contract.cache_parameters()['maxsize']==1

def test_same_contract_reduces_real_expected_parser_invocations():
 with db() as c,patch.object(m,'_revision_trigger_contract',wraps=m._revision_trigger_contract) as spy:
  m._validate_revision_triggers(c,A);m._validate_revision_triggers(c,A);m._validate_revision_triggers(c,A)
  expected=[call for call in spy.call_args_list if call.args[0].startswith('CREATE TRIGGER IF NOT EXISTS revision_')]
  assert len(expected)==1
  assert sum('FROM sqlite_master' in q for q in c.reads)==3
  assert sum('SELECT id, revision' in q for q in c.reads)==3
 info=m._expected_revision_contract.cache_info();assert (info.hits,info.misses,info.currsize)==(2,1,1)

@pytest.mark.parametrize('changed',[B,A+'\n',schema(table='other')])
def test_exact_full_sql_key_changes_compile_even_same_version(changed):
 first=m._expected_revision_contract(A);second=m._expected_revision_contract(changed)
 info=m._expected_revision_contract.cache_info();assert info.misses==2 and info.currsize==1
 assert m._expected_revision_contract(A)==first
 assert m._expected_revision_contract.cache_info().misses==3
 if changed==A+'\n':assert first==second

@pytest.mark.parametrize('action,error',[
 ('drop','invalid authoritative revision trigger'),
 ('change','invalid authoritative revision trigger'),
 ('extra_tracked','unexpected authoritative revision trigger'),
 ('extra_authority','unexpected authoritative revision trigger'),
 ('empty_state','invalid authoritative revision state'),
 ('negative_state','invalid authoritative revision state'),
 ('real_state','invalid authoritative revision state'),
 ('text_state','invalid authoritative revision state'),
 ('multiple_state','invalid authoritative revision state'),
 ('missing_state','no such table: authoritative_state_revision'),
])
def test_current_db_changes_are_rejected_after_cached_pass(action,error):
 c=db()
 try:
  equal(c);c.reads=[]
  if action=='drop':c.execute('DROP TRIGGER revision_t_insert')
  elif action=='change':
   c.execute('DROP TRIGGER revision_t_insert');c.executescript(B[B.index('CREATE TRIGGER'):])
  elif action=='extra_tracked':c.execute('CREATE TRIGGER shadow AFTER INSERT ON t BEGIN SELECT 1; END;')
  elif action=='extra_authority':c.execute('CREATE TRIGGER shadow AFTER INSERT ON unrelated BEGIN UPDATE authoritative_state_revision SET revision=revision+1; END;')
  elif action=='empty_state':c.execute('DELETE FROM authoritative_state_revision')
  elif action=='negative_state':c.execute('UPDATE authoritative_state_revision SET revision=-1')
  elif action=='real_state':c.execute('UPDATE authoritative_state_revision SET revision=1.5')
  elif action=='text_state':c.execute("UPDATE authoritative_state_revision SET revision='0'")
  elif action=='multiple_state':c.execute('INSERT INTO authoritative_state_revision VALUES(2,0)')
  elif action=='missing_state':c.execute('DROP TABLE authoritative_state_revision')
  c.reads=[];equal(c,error=error);equal(c,error=error)
  assert sum('FROM sqlite_master' in q for q in c.reads)==4
  assert m._expected_revision_contract.cache_info().currsize==1
 finally:c.close()

def test_distinct_database_instances_are_always_inspected():
 good,bad=db(),db()
 try:
  equal(good);bad.execute('DROP TRIGGER revision_t_insert');bad.reads=[]
  equal(bad,error='invalid authoritative revision trigger')
  assert any('FROM sqlite_master' in q for q in bad.reads)
  equal(good)
 finally:good.close();bad.close()

def test_schema_migration_and_version_label_cannot_mask_wrong_expectation():
 with db() as c:
  c.execute('PRAGMA user_version=4');equal(c)
  c.execute('DROP TRIGGER revision_t_insert');c.executescript(B[B.index('CREATE TRIGGER'):])
  assert c.execute('PRAGMA user_version').fetchone()[0]==4
  equal(c,B);equal(c,A,error='invalid authoritative revision trigger')
  c.execute('PRAGMA user_version=5');equal(c,B)

def test_invalid_expected_contract_is_not_a_cached_validation_failure():
 malformed=A+'CREATE TRIGGER IF NOT EXISTS revision_bad BEFORE INSERT ON t BEGIN SELECT 1; END;\n'
 with db() as c:
  equal(c,malformed,error='invalid authoritative revision trigger');c.reads=[]
  equal(c,malformed,error='invalid authoritative revision trigger')
  assert sum('FROM sqlite_master' in q for q in c.reads)==2
 assert None in m._expected_revision_contract(malformed)[0]

def test_incomplete_schema_error_is_preserved_and_not_cached():
 with db() as c:
  incomplete=A+'CREATE TABLE unfinished('
  equal(c,incomplete,error='incomplete database schema SQL');equal(c,incomplete,error='incomplete database schema SQL')
  assert not c.reads
 assert m._expected_revision_contract.cache_info().currsize==0

def test_empty_expectation_does_not_reuse_prior_contract():
 with db() as c:
  equal(c)
  equal(c,A[:A.index('CREATE TRIGGER')],error='unexpected authoritative revision trigger')

def test_actual_inspection_sql_sequence_identical_to_original():
 with db() as c:
  reference(c,A);original=list(c.reads);c.reads=[]
  m._validate_revision_triggers(c,A);first=list(c.reads);c.reads=[]
  m._validate_revision_triggers(c,A);hit=list(c.reads)
  assert original==first==hit==["SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'","SELECT id, revision, typeof(revision) FROM authoritative_state_revision"]

def test_concurrent_keys_databases_and_cache_bounds():
 barrier=Barrier(8)
 def worker(i):
  sql=schema(table='left' if i%2 else 'right',step=1+i%2)
  c=db(sql)
  try:
   barrier.wait(timeout=10)
   for _ in range(16):
    equal(c,sql)
    expected,names,tables=m._expected_revision_contract(sql)
    assert names==frozenset({'revision_left_insert' if i%2 else 'revision_right_insert'})
    assert tables==frozenset({'left' if i%2 else 'right'})
    assert m._expected_revision_contract.cache_info().currsize<=1
   return True
  finally:c.close()
 with ThreadPoolExecutor(max_workers=8) as pool:assert all(pool.map(worker,range(8)))
 assert m._expected_revision_contract.cache_info().currsize==1
