"""독립 IR06 oracle: 실제 parser 입력, 외부 소유자 ledger, 유한 전이."""
import asyncio
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import signal
import sqlite3
import sys
from threading import Event
from unittest.mock import _patch
import weakref

import pytest

TREE = Path(os.environ['IR06_TREE'])
OUT = Path(os.environ['IR06_EVIDENCE'])
sys.path.insert(0, str(TREE / 'backend'))
from isolated_sync import canonical
from isolated_sync.workers import NativeJob, WorkerBudget, WorkerLease

def emit(name, data):
    (OUT / (name + '.json')).write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')

@pytest.fixture
def cost():
    spec = importlib.util.spec_from_file_location('ir06_cost', TREE/'docs/benchmarks/t66f-b03/counters.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    delegates = (canonical._parse_json, canonical.encode, hashlib.sha256, sqlite3.connect, NativeJob.__init__, NativeJob._finish, WorkerLease.run)
    patches = list(_patch._active_patches)
    handler = signal.getsignal(signal.SIGINT)
    yield m
    assert sys.gettrace() is None and sys.getprofile() is None
    assert not m.INSTALLATIONS and m.ACTIVE.get() is None
    assert delegates == (canonical._parse_json, canonical.encode, hashlib.sha256, sqlite3.connect, NativeJob.__init__, NativeJob._finish, WorkerLease.run)
    assert list(_patch._active_patches) == patches
    assert signal.getsignal(signal.SIGINT) is handler

def cancelled_entry(m, context, observer='trace', sig=False, capture=None):
    fired = []
    def hook(frame, event, arg):
        if event == 'return' and frame.f_code is m.OwnershipContext.__enter__.__code__ and frame.f_locals.get('self') is context and not fired:
            fired.append(True)
            if capture is not None: capture()
            if sig: signal.raise_signal(signal.SIGINT)
            else: raise RuntimeError('IR06 return observer fault')
        return hook
    setter = sys.settrace if observer == 'trace' else sys.setprofile
    setter(hook)
    try:
        with pytest.raises(KeyboardInterrupt if sig else RuntimeError):
            with context:
                pytest.fail('취소된 진입의 본문은 실행 불가')
    finally:
        setter(None)
    assert fired == [True]

def parse_witness(raws):
    native = canonical._parse_json
    while hasattr(native, '__wrapped__'): native = native.__wrapped__
    seen = []
    def profile(frame, event, arg):
        if event == 'call' and frame.f_code is native.__code__: seen.append(bytes(frame.f_locals['raw']))
    sys.setprofile(profile)
    try:
        for raw in raws:
            try: canonical.decode_c1(raw)
            except canonical.CanonicalError: pass
    finally: sys.setprofile(None)
    assert seen == raws
    return seen

@pytest.mark.parametrize('family', ['primitives','workers','connections','stage','authentication'])
@pytest.mark.parametrize('observer', ['trace','profile'])
@pytest.mark.parametrize('sig', [False,True])
def test_failed_entry_preserves_existing_owner(cost, family, observer, sig):
    m=cost; outer=m.Collector(); rejected=m.Collector(); acquired=[]
    factory={'primitives':m.instrument,'workers':m.instrument_workers,'connections':m.instrument_connections,'stage':lambda:rejected.stage('transfer'),'authentication':m.authentication_hashes}
    with m.instrument(),m.instrument_workers(),m.instrument_connections(),outer.stage('generation'):
        previous=m.ACTIVE.get(); delegates=(canonical._parse_json,NativeJob.__init__,sqlite3.connect)
        def capture():
            acquired.append({'refs':{k:v['refs'] for k,v in m.INSTALLATIONS.items()},'stage_is_rejected':m.ACTIVE.get()[0] is rejected})
            assert acquired[-1]['refs'].get(family,1)==(2 if family in {'primitives','workers','connections'} else 1)
            if family=='stage': assert acquired[-1]['stage_is_rejected']
        cancelled_entry(m,factory[family](),observer,sig,capture)
        assert m.ACTIVE.get() is previous
        assert {k:v['refs'] for k,v in m.INSTALLATIONS.items()} == {'primitives':1,'workers':1,'connections':1}
        assert delegates==(canonical._parse_json,NativeJob.__init__,sqlite3.connect)
        raws=[b'{}',b'{}','"한😀"'.encode()]
        parse_witness(raws)
        assert outer.values['generation/json/calls']==3
        assert outer.values['generation/json/submitted_bytes']==sum(map(len,raws))
        assert rejected.snapshot()=={}
    emit('entry-'+family+'-'+observer+'-'+str(sig),{'boundary_exercised':acquired,'outer':outer.snapshot(),'cancelled':rejected.snapshot(),'final_refs':0,'final_stage':None})

def test_failure_after_successful_entry_and_failed_cleanup_recovery(cost,monkeypatch):
    m=cost; native=canonical._parse_json; c=m.Collector(); reached=[]
    with pytest.raises(ValueError,match='first body'):
        with m.instrument(),c.stage('transfer'):
            reached.append(canonical._parse_json is not native)
            raise ValueError('first body')
    assert reached==[True] and not m.INSTALLATIONS and canonical._parse_json is native
    original=m.RecoveryPatch.stop; failures=[]; failing=[True]
    def broken(p):
        if failing[0] and p.target is canonical and p.name=='_parse_json':
            failures.append(True);raise OSError('IR06 persistent restoration fault')
        return original(p)
    monkeypatch.setattr(m.RecoveryPatch,'stop',broken)
    context=m.instrument(); context.__enter__()
    with pytest.raises(OSError): context.__exit__(None,None,None)
    retained=m.INSTALLATIONS['primitives']
    assert retained['refs']==0 and retained['status']=='RECOVERING'
    for _ in range(3):
        with pytest.raises(OSError):
            with m.instrument():pytest.fail('복원 실패를 성공으로 반환 불가')
        assert len(m.INSTALLATIONS)==1 and m.INSTALLATIONS['primitives'] is retained
    failing[0]=False
    with m.instrument(),c.stage('observation'):parse_witness([b'{}',b'{}'])
    assert c.values['observation/json/calls']==2 and c.values['observation/json/submitted_bytes']==4
    assert not m.INSTALLATIONS and canonical._parse_json is native
    emit('cleanup-recovery',{'failures':len(failures),'retained_generations':1,'silent_success':False,'after':c.snapshot(),'baseline_restored':True})

def test_async_cancel_one_owner_native_tail_and_closed_scope(cost):
    m=cost; started=Event(); resume=Event(); a=m.Collector(); b=m.Collector(); calls=[]; completed=[]
    async def scenario():
        budget=WorkerBudget(1);lease=budget.acquire()
        def work():
            started.set();assert resume.wait(10)
            canonical.decode_c1(b'{}');calls.append(b'{}');return 19
        async def owner_a():
            with m.instrument(),m.instrument_workers(),a.stage('transfer'):
                return await lease.run(work)
        task=asyncio.create_task(owner_a())
        try:
            for _ in range(2000):
                if started.is_set():break
                await asyncio.sleep(.001)
            assert started.is_set() and a.pending==1
            task.cancel()
            with pytest.raises(asyncio.CancelledError):await task
            lease.close();a.finish_when_idle(lambda c:completed.append(c.snapshot()))
            assert a.pending==1 and not a.closed and completed==[]
            with m.instrument(),b.stage('observation'):parse_witness([b'{}',b'{}'])
            assert b.values['observation/json/calls']==2
            # 실제 native 완료까지 hold가 살아 있고, 명시 close 뒤 값은 고정된다.
            a.close();before=a.snapshot();resume.set()
            for _ in range(2000):
                if not budget.snapshot()['tasks']:break
                await asyncio.sleep(.001)
            assert calls==[b'{}'] and a.snapshot()==before
            assert a.pending==0 and len(completed)==1
            assert budget.snapshot()==dict(leases=0,jobs=0,running=0,tasks=0)
        finally:
            resume.set();lease.close()
            if not task.done():task.cancel()
    asyncio.run(scenario())
    emit('async-native-tail',{'native_parse_events':len(calls),'a':a.snapshot(),'b':b.snapshot(),'completion_count':len(completed),'final_pending':a.pending})

@pytest.mark.parametrize('mode',['disabled','local_entry','global_entry'])
def test_pep669_rejection_is_preacquisition_and_preserves_other_thread(cost,mode):
    m=cost; tool=next(i for i in range(6) if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(tool,'IR06 independent monitor');events=[];waiting=Event();resume=Event();survivor=m.Collector()
    native=canonical._parse_json
    def valid():
        with m.instrument(),survivor.stage('generation'):
            waiting.set();assert resume.wait(10);canonical.decode_c1(b'{}');canonical.decode_c1(b'{}')
    def callback(*args): events.append(args[0].co_name)
    with ThreadPoolExecutor(1) as pool:
        future=pool.submit(valid);assert waiting.wait(10)
        try:
            wrapper=canonical._parse_json
            sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,callback)
            if mode=='local_entry':sys.monitoring.set_local_events(tool,m.OwnershipContext.__enter__.__code__,sys.monitoring.events.PY_RETURN)
            elif mode=='global_entry':sys.monitoring.set_events(tool,sys.monitoring.events.PY_RETURN)
            for _ in range(8):
                c=m.Collector()
                if mode=='disabled':
                    with m.instrument(),c.stage('transfer'):canonical.decode_c1(b'{}')
                    assert c.values['transfer/json/submitted_bytes']==2
                else:
                    with pytest.raises(RuntimeError,match='monitoring entry observer unsupported; measurement incomplete'):
                        with m.instrument():pytest.fail('unsupported entry cannot acquire')
                    assert c.snapshot()=={}
                assert canonical._parse_json is wrapper and m.INSTALLATIONS['primitives']['refs']==1
            resume.set();future.result(timeout=10)
        finally:
            resume.set();sys.monitoring.set_events(tool,0)
            sys.monitoring.set_local_events(tool,m.OwnershipContext.__enter__.__code__,0)
            sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,None)
            sys.monitoring.free_tool_id(tool)
    assert survivor.values['generation/json/calls']==2 and survivor.values['generation/json/submitted_bytes']==4
    assert canonical._parse_json is native
    recovery=m.Collector()
    with m.instrument(),recovery.stage('transfer'):parse_witness([b'{}'])
    assert recovery.values['transfer/json/calls']==1
    emit('pep669-'+mode,{'attempts':8,'observer_events':len(events),'survivor':survivor.snapshot(),'recovery':recovery.snapshot(),'refs_after':0,'stage_after':None})

@pytest.mark.parametrize('seed',[6606,4705,90210])
def test_stateful_external_ownership_ledger(cost,seed):
    m=cost;rng=random.Random(seed);contexts=[];stages=[];owners=[];expected=[];closed=set();jobs=[];native_seen=[];expected_native=[];steps=[];weak=[]
    native=canonical._parse_json
    original=m.EntryHandoff
    class Guard(original):
        def __init__(self,*a):super().__init__(*a);weak.append(weakref.ref(self))
    m.EntryHandoff=Guard
    def witness(frame,event,arg):
        if event=='call' and frame.f_code is native.__code__:native_seen.append(bytes(frame.f_locals['raw']))
    def check(action):
        for i,c in enumerate(owners):
            for suffix in ['calls','submitted_bytes','completed_bytes','failed_calls','failed_submitted_bytes']:
                for stage in ['generation','transfer','observation']:
                    key=stage+'/json/'+suffix
                    assert c.values[key]==expected[i][key],(seed,len(steps),action,i,key,expected[i],c.snapshot())
            assert c.pending==sum(j[2]==i for j in jobs)
        assert sum(v['refs'] for k,v in m.INSTALLATIONS.items() if k=='primitives')==len(contexts)
        assert (canonical._parse_json is native)==(not contexts)
        assert m.ACTIVE.get()==((owners[stages[-1][1]],stages[-1][2]) if stages else None)
        assert native_seen==expected_native
        steps.append({'action':action,'valid_references':len(contexts),'active_scope_owners':[v[1] for v in stages],'closed':sorted(closed),'native_holds':len(jobs),'native_events':len(native_seen)})
    enabled=gc.isenabled();gc.disable();sys.setprofile(witness)
    try:
        for iteration in range(180):
            legal=['enter','cancel','stage']
            if contexts:legal+=['parse','parse','release','native_acquire']
            if stages:legal+=['unstage','close']
            if jobs:legal+=['native_complete']
            action=rng.choice(legal)
            if action=='enter':
                context=m.instrument();context.__enter__();contexts.append(context)
            elif action=='release':contexts.pop().__exit__(None,None,None)
            elif action=='stage':
                i=len(owners);c=m.Collector();owners.append(c);expected.append(Counter());stage=rng.choice(['generation','transfer','observation']);context=c.stage(stage);context.__enter__();stages.append((context,i,stage))
            elif action=='unstage':stages.pop()[0].__exit__(None,None,None)
            elif action=='close':
                i=stages[-1][1];owners[i].close();closed.add(i)
            elif action=='cancel':
                # 이미 설치된 profiler는 native 입력만 관찰한다. 별도 local trace가 실제 return을 실패시킨다.
                cancelled_entry(m,m.instrument(),'trace',bool(iteration%2))
            elif action=='parse':
                raw=rng.choice([b'{}',b'{}','"한😀"'.encode(),b'['])
                expected_native.append(raw)
                if stages and stages[-1][1] not in closed:
                    _,i,stage=stages[-1];ledger=expected[i];ledger[stage+'/json/calls']+=1;ledger[stage+'/json/submitted_bytes']+=len(raw)
                    if raw==b'[':ledger[stage+'/json/failed_calls']+=1;ledger[stage+'/json/failed_submitted_bytes']+=len(raw)
                    else:ledger[stage+'/json/completed_bytes']+=len(raw)
                try:canonical.decode_c1(raw)
                except canonical.CanonicalError:assert raw==b'['
            elif action=='native_acquire' and stages:
                budget=WorkerBudget(1);lease=budget.acquire();i=stages[-1][1]
                with m.instrument_workers():
                    job=NativeJob(lease)
                    with budget._lock:lease._jobs.add(job)
                lease.close();jobs.append((job,budget,i))
            elif action=='native_complete':
                job,budget,i=jobs.pop(rng.randrange(len(jobs)));job.settled(None)
                assert budget.snapshot()==dict(leases=0,jobs=0,running=0,tasks=0)
            check(action)
        while jobs:
            job,budget,i=jobs.pop();job.settled(None)
        while stages:stages.pop()[0].__exit__(None,None,None)
        while contexts:contexts.pop().__exit__(None,None,None)
        check('final_release')
    finally:
        sys.setprofile(None);sys.settrace(None);m.EntryHandoff=original
        if enabled:gc.enable()
    assert not any(w() for w in weak)
    emit('stateful-'+str(seed),{'seed':seed,'steps':steps,'expected':[dict(v) for v in expected],'observed':[c.snapshot() for c in owners],'native_inputs':[x.hex() for x in native_seen],'guards_created':len(weak),'guards_retained':0,'final_references':0,'final_holds':0})
