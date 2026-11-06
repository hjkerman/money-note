"""B07 한정 경계 타이머. 디스크의 제품/B03 파일은 수정하지 않는다."""
import collections,contextvars,functools,threading,time
CTX=contextvars.ContextVar('B07_packet',default=None)
local=threading.local()
ORIGINALS=[]

def wrap(obj,name,label,*,phase=None,connect=False,opened=False,closed=False,sql=False):
 native=getattr(obj,name);ORIGINALS.append((obj,name,native))
 @functools.wraps(native)
 def measured(*a,**kw):
  row=CTX.get()
  if row is None:return native(*a,**kw)
  previous=getattr(local,'phase','other')
  if phase:local.phase=phase
  ph=getattr(local,'phase','other')
  if connect:row['connect_calls']+=1
  if opened:row['open_calls']+=1
  if closed:row['close_calls']+=1
  stack=getattr(local,'stack',None)
  do=row['probe'] and (not sql or bool(stack) and any(x['label'] in {'connect','retention_validate','finalization_validate'} for x in stack))
  if not do:
   try:return native(*a,**kw)
   finally:
    if phase:local.phase=previous
  if stack is None:stack=[];local.stack=stack
  tag=label
  if label=='revision_contract':
   tag='expected_revision_contract' if a[0].lstrip().startswith('CREATE TRIGGER IF NOT EXISTS revision_') else 'actual_trigger_contract'
  within_connect=connect or any(x['label']=='connect' for x in stack)
  start=time.perf_counter_ns();cpu=time.thread_time_ns();frame={'label':tag,'child_ns':0,'child_cpu_ns':0};stack.append(frame);error=None
  try:return native(*a,**kw)
  except BaseException as e:error=type(e).__name__;raise
  finally:
   endcpu=time.thread_time_ns();end=time.perf_counter_ns();wall=end-start;used=endcpu-cpu;assert stack.pop() is frame
   if stack:stack[-1]['child_ns']+=wall;stack[-1]['child_cpu_ns']+=used
   for group in ['metrics','connect_metrics' if within_connect else 'outside_connect_metrics']:
    value=row.setdefault(group,{}).setdefault(tag,dict(calls=0,wall_ns=0,thread_cpu_ns=0,self_ns=0,self_cpu_ns=0,errors=0))
    value['calls']+=1;value['wall_ns']+=wall;value['thread_cpu_ns']+=used;value['self_ns']+=wall-frame['child_ns'];value['self_cpu_ns']+=used-frame['child_cpu_ns'];value['errors']+=int(error is not None)
   if tag in {'connect','open','retention_validate','finalization_validate','current_schema_validate','revision_triggers_validate','critical_structure_validate','retention_metadata_contract'}:
    row.setdefault('function_intervals',[]).append({'function':tag,'phase':ph,'within_connect':within_connect,'start_ns':start,'end_ns':end,'wall_ns':wall,'thread_cpu_ns':used,'self_ns':wall-frame['child_ns'],'self_cpu_ns':used-frame['child_cpu_ns'],'thread':threading.get_ident(),'error':error})
   if connect:
    row['connect_intervals'].append({'phase':ph,'start_ns':start,'end_ns':end,'wall_ns':wall,'thread_cpu_ns':used,'thread':threading.get_ident(),'error':error})
   if opened:row['fresh_open_intervals']+=1
   if phase:local.phase=previous
 setattr(obj,name,measured)
 return native

def install():
 from isolated_sync import retention_schema as rs,finalization as fin,capture as cap,observation as obs,transfer as trans,http
 from app import db_migrations as mig
 wrap(http.Adapter,'credential','auth_phase',phase='authentication')
 wrap(trans.TransferRepository,'acquire','transfer_phase',phase='transfer_admission')
 wrap(http.Adapter,'terminal','terminal_phase',phase='outer_terminal')
 wrap(http.Adapter,'prepare_release','release_phase',phase='release')
 wrap(http.Adapter,'terminal_release','release_terminal_phase',phase='release_terminal')
 wrap(rs.RetentionSandbox,'connect','connect',connect=True)
 wrap(rs.RetentionSandbox,'_open','open',opened=True)
 wrap(rs.RetentionConnection,'close','close',closed=True)
 wrap(rs.RetentionConnection,'execute','owned_SQL_execute',sql=True)
 wrap(rs,'validate_schema','retention_validate')
 wrap(rs,'metadata_contract','retention_metadata_contract')
 wrap(fin,'validate_schema','finalization_validate')
 wrap(fin,'_validate_current_schema','current_schema_validate')
 wrap(mig,'_validate_critical_structure','critical_structure_validate')
 wrap(mig,'_validate_revision_triggers','revision_triggers_validate')
 wrap(mig,'_revision_trigger_contract','revision_contract')
 wrap(cap,'capture_schema','capture_schema')
 wrap(cap,'_trigger','expected_capture_trigger')
 wrap(cap,'_columns','capture_columns')
 wrap(obs.ObservationRepository,'_lookup','lookup')

def restore():
 for obj,name,native in reversed(ORIGINALS):setattr(obj,name,native)
 ORIGINALS.clear()
