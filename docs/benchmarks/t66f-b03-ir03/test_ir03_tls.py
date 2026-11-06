"""실제 overlapping TLS·서로 다른 승인 principal, native delegate oracle."""
from concurrent.futures import ThreadPoolExecutor
import json,subprocess,sys,uuid
from pathlib import Path
import httpx
TREE=Path('/tmp/money-note-ir03-20261023/candidate');OUT=Path(__file__).parent

def test_distinct_authorized_principals_tls_native_witness():
 p=subprocess.Popen([str(TREE/'.venv/bin/python'),str(TREE/'docs/benchmarks/t66f-b03-independent/server.py'),'3'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,cwd=TREE)
 clients=[]
 def command(v):p.stdin.write(json.dumps(v)+'\n');p.stdin.flush();return json.loads(p.stdout.readline())
 try:
  init=json.loads(p.stdout.readline());other=command({'command':'other_principal'})['token'];origin=init['origin'];assert origin.startswith('https://127.0.0.1:')
  def call(token):
   client=httpx.Client(verify=False,timeout=35);clients.append(client)
   raw=json.dumps(dict(protocol=1,request_id=str(uuid.uuid4()),base=None,inline_bytes=0),separators=(',',':')).encode()
   response=client.post(origin+'/api/sync/v1/observations',content=raw,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json','X-B03-Barrier':'pair'})
   return dict(status=response.status_code,principal=response.json().get('target',{}).get('principal_id'),request_span=len(raw),token_span=len(token.encode()))
  with ThreadPoolExecutor(2) as pool:results=list(pool.map(call,[init['token'],other]))
  assert [x['status'] for x in results]==[201,201]
  assert {x['principal'] for x in results}=={1,2}
  measured=command({'command':'cost','after_requests':2});assert measured['completed_requests']==2 and measured['measurement_complete']
  for sample in measured['request_samples']:
   values=sample['counters']
   for key,value in values.items():
    if '/audit_' in key:assert values.get(key.replace('/audit_','/'),'0')==value
   assert int(values['observation/authentication_sha256/calls'])==1
   assert int(values['observation/authentication_sha256/hash_input_bytes']) in {x['token_span'] for x in results}
  # 잘못된 credential도 새 request-local collector에서 끝나며 이전 snapshot을 바꾸지 않는다.
  prior=measured['request_samples'];bad=clients[0].post(origin+'/api/sync/v1/observations',content=b'{}',headers={'Authorization':'Bearer invalid','Content-Type':'application/json'})
  assert bad.status_code in {400,401,422}
  after=command({'command':'cost','after_requests':3});assert after['completed_requests']==3;assert after['request_samples'][:2]==prior
  for client in clients:client.close()
  assert command({'command':'cost'})['counters']==after['counters']
  (OUT/'tls-distinct-principals.json').write_text(json.dumps(dict(results=results,measurement=after,prior_scopes_immutable=True),indent=2)+'\n')
 finally:
  for client in clients:client.close()
  if p.poll() is None:
   command({'command':'exit'});p.stdin.close()
   code=p.wait(timeout=30)
   if code:raise AssertionError(p.stderr.read())
  p.stdout.close();p.stderr.close()
