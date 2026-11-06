"""계측 counter와 독립된 canonical buffer 길이·domain SHA·객체 union oracle."""
from pathlib import Path
import base64
import hashlib
import json

out=Path(__file__).resolve().parent
scratch=out.parents[2]/'work/t66f-b03-ir06'
v=json.loads((scratch/'originals/tests/delta-integration.json').read_text())
seen={};rows=[]
assert v['equivalent'] is True and v['counter_closed'] is True
for name,sequence,total in [('cold',1,89644),('identical',1,89644),('card',2,104672),('cash',3,118657)]:
    p=v['phases'][name];objects=p['oracle']['objects'];body_bytes=0;preimage_bytes=0
    for obj in objects:
        raw=base64.b64decode(obj['data_base64'],validate=True)
        body=json.loads(raw)
        preimage=b'money-note.sync.v1/'+body['kind'].encode('ascii')+b'\0'+raw
        digest=hashlib.sha256(preimage).hexdigest()
        assert digest==obj['ref']['hash'] and len(raw)==int(obj['ref']['bytes'])
        body_bytes+=len(raw);preimage_bytes+=len(preimage);seen[digest]=raw
    assert len(objects)==144 and p['sequence']==sequence
    assert int(p['committed_object_bytes'])==total==sum(map(len,seen.values()))
    assert p['oracle']['expected_snapshot']['schema_version']==7
    assert p['root']!=p['oracle']['expected_fingerprint']
    sql_keys=[k for k in p['sql'] if '/objects/INSERT/blobBytes/committed' in k]
    assert sum(int(p['sql'][k]) for k in sql_keys)==total
    rows.append(dict(phase=name,objects=len(objects),current_body_bytes=body_bytes,minimum_object_hash_input_bytes=preimage_bytes,distinct_stored_body_bytes=sum(map(len,seen.values())),accepted_sequence=sequence,snapshot_version=7,sync_root_distinct_from_snapshot_fingerprint=True,native_SQL_committed_body_bytes=total))
p=v['phases']['rejected']
assert p['same_error']=='OBJECT_HASH_INVALID' and p['accepted_sequence']==3 and p['preserved'] is True
(out/'evidence/integration-independent-recheck.json').write_text(json.dumps(dict(source='originals.tar.gz:originals/tests/delta-integration.json',phases=rows,rejected=dict(error=p['same_error'],accepted_sequence=3,previous_accepted_preserved=True),on_off_equivalent=True),ensure_ascii=False,indent=2)+'\n')
print('D→E canonical/native committed oracle PASS:4 phases and rejected object')
