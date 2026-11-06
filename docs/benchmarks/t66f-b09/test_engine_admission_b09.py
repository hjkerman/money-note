"""B09 exact source/release consistency: no product guard bypass."""
import base64,copy,hashlib,json
from pathlib import Path
from unittest.mock import patch
import pytest
from isolated_sync.artifacts import ArtifactContract,release_bundle
from isolated_sync.observation import engine_artifact
from tests import test_isolated_sync_transfer as original
pytest_plugins=('tests.test_isolated_sync_transfer',)
ENGINE='5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c'
def test_exact_source_and_checked_in_release():
 b=release_bundle();root=Path(__file__).resolve().parents[2]
 assert hashlib.sha256(engine_artifact()).hexdigest()==ENGINE
 for p in ['docs/specimens/t66d3b-release-artifacts.json','mobile/assets/segmented/isolated-release-artifacts.json']:
  assert json.loads((root/p).read_bytes())==b
 for v in b['artifacts'].values():
  raw=base64.b64decode(v['data_base64']);assert hashlib.sha256(raw).hexdigest()==v['sha256'];assert str(len(raw))==v['bytes']
def test_backend_exact_contract_accepts_own_engine():
 b=release_bundle();ArtifactContract.current().verify({'versions':b['versions'],'context':{'financial_engine':ENGINE}})
@pytest.mark.parametrize('unknown',['0'+ENGINE[1:],'1'*64,'a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94'])
def test_backend_rejects_mutation_unrelated_and_payload(unknown):
 assert unknown!=ENGINE
 with pytest.raises(Exception) as exc:ArtifactContract.current().verify({'versions':release_bundle()['versions'],'context':{'financial_engine':unknown}})
 assert 'UNSUPPORTED_CONTRACT' in str(exc.value)
@pytest.mark.parametrize('mutation',['source','declared_hash','version'])
def test_original_exact_artifact_guard_rejects_inconsistency(db,mutation):
 b=copy.deepcopy(release_bundle())
 if mutation=='source':b['artifacts']['financial_engine']['data_base64']=base64.b64encode(b'changed source').decode()
 elif mutation=='declared_hash':b['artifacts']['financial_engine']['sha256']='0'*64
 else:b['versions']['raw_schema']='0'*64
 target=Path(__file__).resolve().parents[2]/'docs/specimens/t66d3b-release-artifacts.json';read=Path.read_bytes
 def replaced(p):return json.dumps(b).encode() if p==target else read(p)
 with patch.object(Path,'read_bytes',replaced):
  with pytest.raises(AssertionError):original.test_release_artifact_hashes_exact_bytes_and_target(db)
