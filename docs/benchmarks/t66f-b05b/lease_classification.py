"""사후 manifest 응답 수와 실제 lease 갱신을 구분한다. raw 실측은 바꾸지 않는다."""
import gzip,json
from prepare import E,sha,save
assert not (E/'run-manifest.pre-lease-classification.json.gz').exists()
(E/'run-manifest.pre-lease-classification.json.gz').write_bytes(gzip.compress((E/'run-manifest.json').read_bytes(),mtime=0))
rows=[]
for p in sorted((E/'raw').glob('*/independent-verification.json')):
 (p.parent/'verification.pre-lease-classification.json.gz').write_bytes(gzip.compress(p.read_bytes(),mtime=0));d=json.loads(p.read_text());raw=json.loads((p.parent/'run.json').read_text());responses=[r for r in raw['backend']['requests'] if r.get('manifest')];leases=[]
 for r in responses:
  lease={k:r['manifest'][k] for k in ['observation_id','validated_at','expires_at']}
  if lease not in leases:leases.append(lease)
 assert len(leases)==1 and [r['status'] for r in responses]==[201,200]
 assert responses[0]['manifest']['request_id']==responses[1]['manifest']['request_id'];assert responses[0]['manifest']==responses[1]['manifest']
 d.update(observation_leases=leases,renewals=0,manifest_response_count=2,idempotent_terminal_rechecks=1);save(p,d);rows.append({'id':raw['id'],'leases':leases,'new_observations':1,'idempotent_terminal_rechecks':1,'renewals':0,'expires':0,'old_observation_renewal_field':1})
save(E/'analysis-method-notes.json',{'lease_classification':'최초 집계는 manifest 응답2개를 renewal1로 오분류했다. raw를 확인해 동일 request_id·observation_id·validated_at·expires_at의 201 생성+200 terminal 재확인임을 구분했다. 실제 갱신0이며 원 측정·counter·timing은 불변이다. 초기 파생 metadata는 별도 gzip에 보존했다.','acquisitions_repeated':0,'runs':rows})
print(json.dumps({'lease_handling':'VALID','new_observations_per_run':1,'renewals':0,'terminal_rechecks_per_run':1,'raw_modified':False}))
