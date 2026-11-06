"""B09 실험 경량 timer. B03 모듈/제품 파일은 수정하지 않는다."""
import contextvars,functools,threading,time
CTX=contextvars.ContextVar('B09_request',default=None)
REV=contextvars.ContextVar('B09_revision',default=False)
TLS=threading.local();ORIGINALS=[];CACHE=None;PARSER=None

def wrap(obj,name,label,*,counter=None,parser=False,sql=False):
 native=getattr(obj,name);ORIGINALS.append((obj,name,native))
 @functools.wraps(native)
 def measured(*args,**kw):
  row=CTX.get()
  if row is None:return native(*args,**kw)
  if counter:row[counter]+=1
  if sql:
   if args[1]=="SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'":row['actual_schema_inspections']+=1
   return native(*args,**kw)
  tag=label
  if parser:
   tag='expected_parser' if args[0].lstrip().startswith('CREATE TRIGGER IF NOT EXISTS revision_') else 'actual_parser'
  t=time.perf_counter_ns();cpu=time.thread_time_ns()
  try:return native(*args,**kw)
  finally:
   used=time.thread_time_ns()-cpu;elapsed=time.perf_counter_ns()-t
   item=row['timings'].setdefault(tag,{'calls':0,'ns':0,'cpu_ns':0});item['calls']+=1;item['ns']+=elapsed;item['cpu_ns']+=used
 setattr(obj,name,measured);return native

def install():
 global CACHE,PARSER
 from isolated_sync import retention_schema as rs,finalization as f
 from app import db_migrations as m
 wrap(rs.RetentionSandbox,'connect','connect',counter='connections')
 wrap(rs.RetentionSandbox,'_open','open',counter='opens')
 wrap(rs.RetentionConnection,'close','close',counter='closes')
 wrap(rs.RetentionConnection,'execute','SQL_inspection_counter',sql=True)
 wrap(rs,'validate_schema','schema')
 wrap(f,'validate_schema','finalization')
 native_revision=wrap(m,'_validate_revision_triggers','revision_validation')
 measured_revision=m._validate_revision_triggers
 @functools.wraps(measured_revision)
 def revision(*a,**kw):
  token=REV.set(True)
  try:return measured_revision(*a,**kw)
  finally:REV.reset(token)
 m._validate_revision_triggers=revision
 original_statements=m._statements
 @functools.wraps(original_statements)
 def statements(*a,**kw):
  row=CTX.get()
  if row is not None and REV.get():row['contract_compilations']+=1
  return original_statements(*a,**kw)
 m._statements=statements
 PARSER=wrap(m,'_revision_trigger_contract','parser',parser=True)
 if hasattr(m,'_expected_revision_contract'):CACHE=wrap(m,'_expected_revision_contract','expected_cache_gate')

def cache_info():return CACHE.cache_info()._asdict() if CACHE is not None else None

def calibration():
 # D3 요청이 아닌 유한 계측 overhead 진단이며 outer deadline에 포함된다.
 from app import db_migrations as m
 import statistics
 sql='CREATE TRIGGER IF NOT EXISTS revision_probe AFTER INSERT ON t BEGIN UPDATE authoritative_state_revision SET revision=revision+1 WHERE id=1; END;'
 direct=[];observed=[]
 row={'timings':{}};token=CTX.set(row)
 try:
  for _ in range(64):
   t=time.perf_counter_ns();PARSER(sql);direct.append(time.perf_counter_ns()-t)
   t=time.perf_counter_ns();m._revision_trigger_contract(sql);observed.append(time.perf_counter_ns()-t)
 finally:CTX.reset(token)
 return {'pairs':64,'D3_packets':0,'direct_total_ns':sum(direct),'wrapped_total_ns':sum(observed),'median_delta_ns':statistics.median(observed)-statistics.median(direct),'not_confidence_bound':True,'policy':'B03 OFF server-start calibration; isolated pure short trigger; not ON/long-schema timing upper bound'}
