"""새 실제 HTTP 취득의 canonical body/domain hash/SQL durable bytes를 대조한다."""
import base64,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent/'evidence'
p=R/'work/t66f-b03-ic06/originals/tests/delta-integration.json';v=json.loads(p.read_text())
seen={};rows=[]
assert v['equivalent'] is True and v['counter_closed'] is True
for name,sequence,total in [('cold',1,89644),('identical',1,89644),('card',2,104672),('cash',3,118657)]:
 phase=v['phases'][name];objects=phase['oracle']['objects'];body_bytes=0;hash_bytes=0
 for obj in objects:
  raw=base64.b64decode(obj['data_base64'],validate=True);body=json.loads(raw)
  preimage=b'money-note.sync.v1/'+body['kind'].encode('ascii')+b'\0'+raw
  digest=hashlib.sha256(preimage).hexdigest()
  assert digest==obj['ref']['hash'] and len(raw)==int(obj['ref']['bytes'])
  seen[digest]=raw;body_bytes+=len(raw);hash_bytes+=len(preimage)
 assert len(objects)==144 and phase['sequence']==sequence
 assert int(phase['committed_object_bytes'])==total==sum(map(len,seen.values()))
 assert phase['oracle']['expected_snapshot']['schema_version']==7
 assert phase['root']!=phase['oracle']['expected_fingerprint']
 sql=sum(int(phase['sql'][k]) for k in phase['sql'] if '/objects/INSERT/blobBytes/committed' in k)
 assert sql==total
 rows.append(dict(phase=name,objects=len(objects),current_canonical_body_bytes=body_bytes,minimum_object_hash_input_bytes=hash_bytes,stored_distinct_body_bytes=total,native_SQL_committed_body_bytes=sql,sequence=sequence,snapshot_version=7,sync_root_distinct=True))
p= v['phases']['rejected'];assert p['same_error']=='OBJECT_HASH_INVALID' and p['accepted_sequence']==3 and p['preserved'] is True
(O/'integration-oracle-results.json').write_text(json.dumps(dict(result='PASS',source='originals-scratch.tar.gz:tests/delta-integration.json',phases=rows,on_off_equivalent=True,rejected_accepted_preserved=True),ensure_ascii=False,indent=2)+'\n')
print('실제 D→E canonical/native SQL 독립 재검사 PASS')
