"""승인된 source/artifact 전이만 독립 stdlib C1/해시로 확인한다."""
import base64,hashlib,json
from pathlib import Path
import pytest
from isolated_sync.artifacts import ArtifactContract,release_bundle
from isolated_sync.observation import ObservationError,engine_artifact
R=Path(__file__).resolve().parents[2]
APPROVED='f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3'
def exact_json(value):return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def test_independent_actual_source_sha_and_declared_artifact():
 root=R/'backend';paths=sorted((root/'app').rglob('*.py'))+sorted((root/'isolated_sync').glob('*.py'))+sorted((root/'app/services/judgment/messages').glob('*.yaml'))
 raw=exact_json({'profile':'isolated-d3a/1','sources':{p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}})
 assert hashlib.sha256(raw).hexdigest()==APPROVED
 assert raw==engine_artifact()
 bundle=release_bundle();assert base64.b64decode(bundle['artifacts']['financial_engine']['data_base64'])==raw
 assert bundle==json.loads((R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes())
 assert (R/'docs/specimens/t66d3b-release-artifacts.json').read_bytes()==(R/'mobile/assets/segmented/isolated-release-artifacts.json').read_bytes()
@pytest.mark.parametrize('mutation',['0'*64,'d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae', 'a'+APPROVED[1:]])
def test_current_backend_contract_rejects_unknown_or_payload_hash(mutation):
 with pytest.raises(ObservationError,match='UNSUPPORTED_CONTRACT'):
  ArtifactContract.current().verify({'versions':release_bundle()['versions'],'context':{'financial_engine':mutation}})
