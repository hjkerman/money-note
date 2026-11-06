"""유한 N=1k D3/TLS 전송 A/B. Flutter E2/E1/accepted publication은 실행하지 않는다."""
import base64,gzip,hashlib,json,os,pathlib,sqlite3,subprocess,sys,time
from uuid import uuid4
import httpx
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05';W=pathlib.Path('/tmp/money-note-t66f-b05-20261026')
assert not (E/'backend-http-diagnostic.json').exists()
rows=[]
for ordinal,(variant,on) in enumerate([('A',False),('B',False),('B',True),('A',True)]):
 tree=W/('baseline' if variant=='A' else 'optimized');name=f'backend-n1000-{ordinal}-{variant}-{"on" if on else "off"}';out=W/'raw'/name;out.mkdir();worker=out/'server'
 with (out/'stderr.log').open('w') as errors:
  p=subprocess.Popen([str(R/'.venv/bin/python'),str(E/'diagnostic_server.py'),'1000',str(worker)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,env={**os.environ,'B05_TREE':str(tree),'TMPDIR':str(W/'disposable'),'PYTHONDONTWRITEBYTECODE':'1'})
  def command(v):
   p.stdin.write(json.dumps(v)+'\n');p.stdin.flush();line=p.stdout.readline();assert line,('worker ended',p.poll());return json.loads(line)
  value={'run_id':name,'ordinal':ordinal,'N':1000,'variant':variant,'on':on,'status':'RUNNING','role':'BACKEND_HTTP_DIAGNOSTIC_ONLY','valid_for_full_cold_acquisition':False,'E2':False,'E1':False,'E3':False,'E4':False,'accepted_generation':None,'source_file_sha256':hashlib.sha256((tree/'backend/isolated_sync/observation.py').read_bytes()).hexdigest()}
  try:
   line=p.stdout.readline();assert line,('startup',p.poll());init=json.loads(line)
   # 원본 immutable 그래프에서 독립 child shape로 typed path를 작성. 취득 측정 밖이다.
   with sqlite3.connect(init['fixture']['db_path']) as db:
    objects={};paths=[]
    def visit(ref,path):
     if ref['hash'] in objects:return
     raw=db.execute('SELECT body FROM sync_objects WHERE hash=?',(ref['hash'],)).fetchone()[0];body=json.loads(raw)
     assert len(raw)==int(ref['bytes']) and hashlib.sha256(b'money-note.sync.v1/'+body['kind'].encode()+b'\0'+raw).hexdigest()==ref['hash']
     objects[ref['hash']]=raw;paths.append((ref,path))
     kind=body['kind'];children=[]
     if kind=='raw-root':children=[a['root']['ref'] for a in body['tables']]
     elif kind=='snapshot-node':children=[a['ref'] for a in body['children']]
     elif kind=='index-root':children=[body['facts']]
     elif kind=='index-node':children=[body[k] for k in ['left','right']]
     for child in children:visit(child,path+[child['hash']])
    for role in ['raw','index','hot','control']:
     ref=init['fixture']['manifest']['target'][role+'_ref'];visit(ref,[ref['hash']])
   assert len(objects)==init['fixture']['graph']['objects']
   command({'command':'mode','on':on,'label':name});received={};http_rows=[]
   with httpx.Client(verify=False,trust_env=False,timeout=60,headers={'Authorization':'Bearer '+init['token']}) as client:
    started=time.time();wall=time.perf_counter_ns()
    t=time.perf_counter_ns();response=client.post(init['origin']+'/api/sync/v1/observations',json={'protocol':1,'request_id':str(uuid4()),'base':None,'inline_bytes':0});http_rows.append({'kind':'manifest','elapsed_ns':time.perf_counter_ns()-t,'status':response.status_code});assert response.status_code==201,response.text[:200];m=response.json()
    assert m['target']==init['fixture']['manifest']['target']
    for begin in range(0,len(paths),64):
     selected=paths[begin:begin+64];items=[{'path':path,'offset':'0','length':int(ref['bytes'])} for ref,path in selected]
     t=time.perf_counter_ns();response=client.post(init['origin']+'/api/sync/v1/observations/'+m['observation_id']+'/objects',json={'protocol':1,'request_id':str(uuid4()),'items':items});http_rows.append({'kind':'objects','elapsed_ns':time.perf_counter_ns()-t,'status':response.status_code});assert response.status_code==200,response.text[:200]
     for chunk in response.json()['chunks']:
      h=chunk['ref']['hash'];raw=base64.b64decode(chunk['data_base64']);assert raw==objects[h] and chunk['offset']=='0';received[h]=raw
    elapsed=time.perf_counter_ns()-wall;ended=time.time()
   assert received==objects
   snapshot=command({'command':'snapshot'});final=command({'command':'finish'})
   hot=json.loads(objects[m['target']['hot_ref']['hash']]);assert isinstance(hot['state'],dict)
   value.update(status='COMPLETED',valid_for_backend_diagnostic=True,start_unix=started,end_unix=ended,download_elapsed_ns=elapsed,http=http_rows,backend=snapshot,fixture=init['fixture'],completed_objects=len(received),completed_bytes=sum(map(len,received.values())),target=m['target'],financial_state_sha256=hashlib.sha256(json.dumps(hot['state'],sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest(),object_set_sha256=hashlib.sha256('\n'.join(sorted(received)).encode()).hexdigest(),database_state=final,collector_closed=snapshot['issued']==snapshot['closed'],observation_expired=any(a['status']==410 for a in snapshot['requests']))
  except BaseException as err:
   value.update(status='INCOMPLETE',valid_for_backend_diagnostic=False,error=type(err).__name__+': '+str(err)[:400]);raise
  finally:
   if p.poll() is None:
    try:command({'command':'exit'})
    finally:p.stdin.close();p.wait(timeout=30)
   assert p.returncode==0
   (E/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');rows.append(value)
   for f in ['fixture.json','bootstrap.json','requests.jsonl','final-state.json']:
    if (worker/f).exists():(E/(name+'-'+f+'.gz')).write_bytes(gzip.compress((worker/f).read_bytes(),mtime=0))
   backup=worker/'backend-terminal.sqlite'
   if backup.exists():
    with sqlite3.connect('file:'+str(backup)+'?mode=ro',uri=True) as c:assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
    (E/(name+'-backend.sqlite.gz')).write_bytes(gzip.compress(backup.read_bytes(),mtime=0))
  print(json.dumps({'run':name,'status':value['status'],'elapsed_s':value.get('download_elapsed_ns',0)/1e9,'objects':value.get('completed_objects')}),flush=True)
assert len({x['fixture']['fixture_sha256'] for x in rows})==1
assert len({x['target']['raw_ref']['hash'] for x in rows})==1
assert len({x['target']['index_ref']['hash'] for x in rows})==1
assert len({x['target']['control_ref']['hash'] for x in rows})==1
assert len({x['financial_state_sha256'] for x in rows})==1
for v in ['A','B']:
 pair=[x for x in rows if x['variant']==v];assert pair[0]['object_set_sha256']==pair[1]['object_set_sha256']
(E/'backend-http-diagnostic.json').write_text(json.dumps({'status':'COMPLETED','role':'BACKEND_HTTP_DIAGNOSTIC_ONLY','N':1000,'runs':[x['run_id']+'.json' for x in rows],'A_B_pairs':2,'full_cold_acquisition_pairs':0,'product_equivalence':'raw/index/control refs and hot financial state identical; hot context engine/ref/sync_root legitimately source-specific','limitation':'fresh source A/B; one run/condition, all conditions include lightweight per-lookup decode/count timers; OS caches not reset; backend-only precomputed typed paths, no Flutter E2/E1/E3/E4'},ensure_ascii=False,indent=2)+'\n')
