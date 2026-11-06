"""IR07 실제 취득 결과를 raw body와 literal 누적 SQL payload로 재검사한다."""
import base64,hashlib,json,os,pathlib
T=pathlib.Path(os.environ['IR07_TREE']);E=pathlib.Path(os.environ['IR07_EVIDENCE']);W=T.parent
p=W/'originals/tests/delta-integration.json';v=json.loads(p.read_text());assert v['equivalent'] and v['counter_closed']
seen={};result=[]
for phase,seq,total in [('cold',1,89644),('identical',1,89644),('card',2,104672),('cash',3,118657)]:
 q=v['phases'][phase];oracle=q['oracle'];objects=oracle['objects'];current=[];preimages=[]
 for ob in objects:
  raw=base64.b64decode(ob['data_base64'],validate=True);kind=json.loads(raw)['kind'];preimage=b'money-note.sync.v1/'+kind.encode('ascii')+b'\0'+raw
  h=hashlib.sha256(preimage).hexdigest();assert h==ob['ref']['hash'] and len(raw)==int(ob['ref']['bytes'])
  assert h not in seen or seen[h]==raw
  seen[h]=raw;current.append(len(raw));preimages.append(len(preimage))
 assert len(objects)==144 and q['sequence']==seq and q['root']==oracle['manifest']['target']['sync_root']
 assert sum(map(len,seen.values()))==total==int(q['committed_object_bytes'])
 sql=sum(int(value) for key,value in q['sql'].items() if key.endswith('/objects/INSERT/blobBytes/committed'))
 assert sql==total
 assert oracle['expected_snapshot']['schema_version']==7 and q['root']!=oracle['expected_fingerprint']
 assert len(oracle['source'])==11
 result.append({'phase':phase,'sequence':seq,'objects':len(objects),'raw_canonical_current_bytes':sum(current),'minimum_object_hash_preimage_bytes':sum(preimages),'literal_cumulative_distinct_bytes':total,'native_SQL_committed_bytes':sql,'snapshot_v7':True,'sync_root_separate':True,'source_tables':11})
q=v['phases']['rejected'];assert q['same_error']=='OBJECT_HASH_INVALID' and q['accepted_sequence']==3 and q['preserved']
text=(T/'mobile/lib/src/segmented/store_publication.dart').read_text();assert "finalAuthorityFence();\n      _db.execute('COMMIT');" in text
source=p.read_bytes();record={'result':'PASS','input_sha256':hashlib.sha256(source).hexdigest(),'phases':result,'rejection':q['same_error'],'accepted_sequence_after_rejection':3,'on_off_equivalence':True,'closed_scope_fixed':True,'final_authority_fence_directly_before_sync_COMMIT':True,'oracle_interpretation':'별도 raw/domain SHA 및 literal 누적 object bytes. 최소 object hash preimage는 전체 SHA operation 합계의 대용이 아니다.'}
(E/'integration-oracle.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print(json.dumps(record,ensure_ascii=False))
