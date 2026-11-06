"""B05: 원 함수와 독립 기대값을 사용한 함수 로컬 decode 재사용 회귀."""
import collections
from concurrent.futures import ThreadPoolExecutor
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import patch
from uuid import uuid4
import weakref

import pytest
from isolated_sync import observation, canonical
from isolated_sync.canonical import Object, encode, CanonicalError
from isolated_sync.observation import ObservationRepository, ObservationError
from isolated_sync.roots import sync_root
from tests.test_isolated_sync_observation import sandbox, repository, create, CREDENTIAL

E = Path(os.environ.get('B05_EVIDENCE', '/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b05'))
namespace = {}
exec(compile((E/'lookup_before.py').read_text(), str(E/'lookup_before.py'), 'exec'), observation.__dict__, namespace)
BEFORE = namespace['_lookup']
AFTER = ObservationRepository._lookup

def call(db, manifest, function=AFTER, **kwargs):
    with patch.object(ObservationRepository, '_lookup', function):
        return repository(db).lookup(manifest['observation_id'], CREDENTIAL, guard=kwargs.get('guard', lambda:CREDENTIAL))

def outcome(db, manifest, function):
    try:return ('ok',call(db,manifest,function))
    except ObservationError as e:return ('error',e.code,e.action)

def immutable(db):
    with sqlite3.connect(db.path) as c:
        return list(c.execute('SELECT hash,kind,body FROM sync_objects ORDER BY hash'))

def test_success_cold_exact_bytes_and_decode_counts(sandbox):
    m=create(repository(sandbox)); before=immutable(sandbox); counts=[]
    original=Object.body
    for fn,expected in [(BEFORE,3),(AFTER,2)]:
        tally=collections.Counter()
        def body(obj):
            tally[obj.kind]+=1
            return original(obj)
        with patch.object(Object,'body',body):assert call(sandbox,m,fn)==m
        assert tally['hot']==expected
        counts.append(tally)
    assert counts[0]-counts[1]=={'hot':1}
    assert immutable(sandbox)==before
    for h,kind,raw in before:
        assert hashlib.sha256(b'money-note.sync.v1/'+kind.encode()+b'\0'+raw).hexdigest()==h
        assert encode(json.loads(raw))==raw

@pytest.mark.parametrize('role', ['hot','control'])
@pytest.mark.parametrize('corruption', ['missing','hash','json','noncanonical','type'])
def test_missing_corrupt_invalid_type(sandbox,role,corruption):
    m=create(repository(sandbox));h=m['target'][role+'_ref']['hash']
    with sqlite3.connect(sandbox.path) as c:
        if corruption=='missing':c.execute('DELETE FROM sync_objects WHERE hash=?',(h,))
        else:
            raw={'hash':b'{"kind":"control"}', 'json':b'{', 'noncanonical':b'{ "kind":"hot" }','type':b'[]'}[corruption]
            c.execute('UPDATE sync_objects SET body=? WHERE hash=?',(raw,h))
    expected=('error','OBSERVATION_INCOMPLETE','new_observation') if corruption=='missing' else ('error','REQUIRED_METADATA_INVALID','blocked')
    assert outcome(sandbox,m,BEFORE)==expected
    assert outcome(sandbox,m,AFTER)==expected

@pytest.mark.parametrize('field', ['context','projection_schema'])
def test_rejected_hot_metadata_and_short_circuit(sandbox,field):
    m=create(repository(sandbox));t=m['target'];h=t['hot_ref']['hash']
    with sqlite3.connect(sandbox.path) as c:
        body=json.loads(c.execute('SELECT body FROM sync_objects WHERE hash=?',(h,)).fetchone()[0])
        body[field] = {} if field=='context' else '0'*64
        obj=Object.make(body);t['hot_ref']=obj.ref();t['sync_root']=sync_root({k:v for k,v in t.items() if k!='sync_root'})
        c.execute('INSERT INTO sync_objects VALUES (?,?,?)',(obj.hash,obj.kind,obj.raw))
        c.execute("UPDATE sync_observation_pins SET hash=? WHERE observation_id=? AND role='hot'",(obj.hash,m['observation_id']))
        c.execute('UPDATE sync_observations SET target=?,response=? WHERE id=?',(encode(t),encode(m),m['observation_id']))
    counts=[];original=Object.body
    for fn in [BEFORE,AFTER]:
        tally=collections.Counter()
        def body(obj):tally.update([obj.kind]);return original(obj)
        with patch.object(Object,'body',body):
            assert outcome(sandbox,m,fn)==('error','REQUIRED_METADATA_INVALID','blocked')
        counts.append(tally['hot'])
    assert counts==([2,2] if field=='context' else [3,2])

@pytest.mark.parametrize('mode', ['missing_observation','revoked_guard','terminal_guard'])
def test_exceptional_early_and_terminal_returns(sandbox,mode):
    m=create(repository(sandbox))
    if mode=='missing_observation':
        m['observation_id']=str(uuid4())
        assert outcome(sandbox,m,BEFORE)==outcome(sandbox,m,AFTER)==('error','OBSERVATION_INCOMPLETE','new_observation')
    else:
        for fn in [BEFORE,AFTER]:
            steps=iter([None] if mode=='revoked_guard' else [CREDENTIAL,None])
            with pytest.raises(ObservationError) as err:call(sandbox,m,fn,guard=lambda:next(steps))
            assert err.value.code=='PRINCIPAL_OR_SESSION_CHANGED'


def test_distinct_same_size_and_identical_content_instances():
    a=Object.make({'kind':'hot','title':'a'});b=Object.make({'kind':'hot','title':'b'})
    assert len(a.raw)==len(b.raw) and a.hash!=b.hash
    clone=Object('hot',a.raw)
    assert clone is not a and clone.hash==a.hash and clone.body()=={'kind':'hot','title':'a'}
    # 동일 C1 내용의 다른 유효 content hash는 불가능하다. 다른 직렬화는 거부한다.
    with pytest.raises(CanonicalError):Object('hot',b'{"title":"a", "kind":"hot"}')
    first=a.body();first['title']='mutated'
    assert a.body()=={'kind':'hot','title':'a'} and b.body()=={'kind':'hot','title':'b'}


def test_repeated_references_no_retained_objects_or_mutable_alias(sandbox):
    m=create(repository(sandbox));refs=[];original=Object.body
    def body(obj):refs.append(weakref.ref(obj));return original(obj)
    with patch.object(Object,'body',body):
        a=call(sandbox,m);a['target']['context']['today']='mutation'
        b=call(sandbox,m);assert b==m
    gc.collect();assert all(x() is None for x in refs)
    with sqlite3.connect(sandbox.path) as c:
        raw=c.execute('SELECT body FROM sync_objects WHERE hash=?',(m['target']['hot_ref']['hash'],)).fetchone()[0]
    one=Object('hot',raw);two=Object('hot',raw)
    assert one is not two and one.body()==two.body() and one.raw==two.raw


def test_concurrent_invocations_and_generation_states(sandbox):
    old=create(repository(sandbox))
    with sandbox.connect() as c:
        c.begin_capture();c.execute("UPDATE ledger_entries SET title='b05-changed' WHERE id=100");c.finalize();c.commit()
    new=create(repository(sandbox),base=old['target'])
    assert new['target']['revision']!=old['target']['revision']
    assert new['target']['raw_ref']!=old['target']['raw_ref']
    for fn in [BEFORE,AFTER]:
        with patch.object(ObservationRepository,'_lookup',fn),ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda m:repository(sandbox).lookup(m['observation_id'],CREDENTIAL,guard=lambda:CREDENTIAL),[old,new]))
        assert results==[old,new]


def test_b03_real_operation_reduction_exact_remaining_accounting(sandbox):
    m=create(repository(sandbox));spec=importlib.util.spec_from_file_location('b05_cost',Path(__file__).resolve().parents[2]/'docs/benchmarks/t66f-b03/counters.py')
    cost=importlib.util.module_from_spec(spec);spec.loader.exec_module(cost)
    results=[]
    # ref 함수의 globals는 현재 모듈이므로 계측 alias도 원 함수와 동일하게 적용된다.
    for fn in [BEFORE,AFTER]:
        c=cost.Collector()
        with cost.instrument(),cost.instrument_connections(),c.stage('transfer'):
            assert call(sandbox,m,fn)==m
        c.close();results.append(dict(c.values))
    a,b=results;span=int(m['target']['hot_ref']['bytes'])
    for metric in ['json/submitted_bytes','json/completed_bytes']:
        assert a['transfer/'+metric]-b['transfer/'+metric]==span
    assert a['transfer/json/calls']-b['transfer/json/calls']==1
    assert {k:v for k,v in a.items() if '/sha256/' in k}=={k:v for k,v in b.items() if '/sha256/' in k}
    # _lookup의 SQL은 읽기뿐이다. 연결 준비의 별도 SQL 비용과 혼동하지 않는다.
    if os.environ.get('B05_RECORD_COUNTERS'):
        (E/'lookup-counter-comparison.json').write_text(json.dumps({'baseline_algorithm':a,'optimized_algorithm':b,'removed_primary_span':span,'same_current_release_engine':m['target']['context']['financial_engine']},indent=2)+'\n')
