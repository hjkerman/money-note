"""B10 읽기 전용 source/archive 식별 검사. 제품 import·압축 해제·실행 없음."""
from pathlib import Path, PurePosixPath
import base64, hashlib, json, stat, subprocess, tarfile
ROOT=Path('/home/hjkerman/codex/money-note'); OUT=ROOT/'docs/benchmarks/t66f-b10'
BASE='ebcbd54d90eeee194a04b9eea6367f446ee2fd28'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def git(*args):return subprocess.check_output(['git','--no-optional-locks',*args],cwd=ROOT)
def engine_path(p):return (p.startswith('backend/app/') and p.endswith('.py')) or (p.startswith('backend/isolated_sync/') and p.count('/')==2 and p.endswith('.py')) or (p.startswith('backend/app/services/judgment/messages/') and p.endswith('.yaml'))
paths=[x.decode() for x in git('ls-tree','-r','--name-only',BASE).splitlines()]
engine_paths={p for p in paths if engine_path(p)}
A='8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8'
A5='29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542'
cases=[('B03',Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03')/A/'candidate.tar.gz',A,'fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5','7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c'),('B05',ROOT/'docs/benchmarks/t66f-b05/experimental-source.tar.gz','d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae','745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e','f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3'),('B05-A',Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b05a')/A5/'candidate.tar.gz',A5,'b239b9d277e5fd747c2f85c5577f42e203ad7a737b29317f0e23581d6b13b0f1','f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3'),('B08',ROOT/'docs/benchmarks/t66f-b08/experimental-source.tar.gz','a857d22d83d21bba28c5f0531ab55e8b7cddce9e960e7ec3d918a241215b9b94','cb89861bedaa998ce3c53789f76ba92a412c4eeff9a05f34a1f49d8b25067e22','5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c'),('B09',ROOT/'docs/benchmarks/t66f-b09/integration-source.tar.gz','beb2fe5ef2ab02feccd9ce0edc1f37e658bf10a47c9104aa1916627251b0149e','8b4079ebe0445ceefa905837c1e557b0efeefda91c0ab95fefef4aa760f20433','5861d6d29f5a8d1b7e63d5d279c06f19c2158f40915527c1b6c76a3a09ee3d2c')]
records=[]; baseline_map=None
for name,path,payload,archive_sha,expected_engine in cases:
 assert sha(path.read_bytes())==archive_sha
 with tarfile.open(path) as tar:
  assert len(tar.getnames())==len(set(tar.getnames()))
  manifest=json.loads(tar.extractfile('metadata/source-manifest.json').read()); entries=manifest['entries']; em={x['path']:x for x in entries}
  assert list(em)==sorted(em) and len(em)==len(entries) and sha(canonical(entries))==payload
  for e in entries:
   p=PurePosixPath(e['path']); assert not p.is_absolute() and '..' not in p.parts
   m=tar.getmember('source/'+e['path']); raw=tar.extractfile(m).read()
   assert m.isfile() and m.mode==int(e['mode'],8) and len(raw)==e['bytes'] and sha(raw)==e['sha256']
  mapping={}
  for p in sorted(engine_paths|{p for p in em if engine_path(p)}):
   mapping[p[8:]]=em[p]['sha256'] if p in em else sha(git('show',BASE+':'+p))
  engine=sha(canonical({'profile':'isolated-d3a/1','sources':mapping}));assert engine==expected_engine
  release_raw=tar.extractfile('source/docs/specimens/t66d3b-release-artifacts.json').read()
  assert release_raw==tar.extractfile('source/mobile/assets/segmented/isolated-release-artifacts.json').read()
  bundle=json.loads(release_raw); component_results={}
  for key,val in bundle['artifacts'].items():
   data=base64.b64decode(val['data_base64'],validate=True); assert sha(data)==val['sha256']; component_results[key]=val['sha256']
  declared=component_results['financial_engine']; stale=name in ('B05','B08');assert (declared!=engine)==stale
  original_b03=name=='B03'
  if original_b03:baseline_map=mapping; frozen_entries=entries
  difference=[p for p in mapping if mapping[p]!=baseline_map[p]]
  expected_diff=[] if name=='B03' else ['isolated_sync/observation.py'] if name in ('B05','B05-A') else ['app/db_migrations.py']
  assert difference==expected_diff
  records.append({'id':name,'archive':str(path),'archive_sha256':archive_sha,'payload_sha256':payload,'engine_sha256':engine,'files':len(entries),'bytes':sum(x['bytes'] for x in entries),'archive_member_sha_mode_verified':True,'engine_input_count':len(mapping),'engine_sources':mapping,'engine_input_delta_from_B03':difference,'declared_release_engine':declared,'release_json_sha256':sha(release_raw),'artifact_component_hashes':component_results,'historical_pre_admission_mismatch':stale,'certification_ko':'IR07 독립 계측 정확성 CLOSED — 원 소스와 지원 runtime 한정' if original_b03 else '실험 후보; IR07 인증의 자동 이전 없음','adopted_by_B10':False,'reference_selected':original_b03,'base_commit':BASE})
live_paths=sorted([p for p in paths if engine_path(p)]); lm={p[8:]:sha((ROOT/p).read_bytes()) for p in live_paths}; live_engine=sha(canonical({'profile':'isolated-d3a/1','sources':lm}));assert live_engine==records[1]['engine_sha256']
with tarfile.open(cases[2][1]) as t:le=json.loads(t.extractfile('metadata/source-manifest.json').read())['entries']
mismatch=[e['path'] for e in le if not (ROOT/e['path']).is_file() or sha((ROOT/e['path']).read_bytes())!=e['sha256'] or stat.S_IMODE((ROOT/e['path']).stat().st_mode)!=int(e['mode'],8)];assert not mismatch
live={'engine_sha256':live_engine,'candidate_subset_payload':A5,'subset_files':len(le),'subset_mismatches':mismatch,'full_dirty_tree_payload_claimed':False,'observation_py_sha256':sha((ROOT/'backend/isolated_sync/observation.py').read_bytes()),'db_migrations_py_sha256':sha((ROOT/'backend/app/db_migrations.py').read_bytes()),'release_json_sha256':sha((ROOT/'docs/specimens/t66d3b-release-artifacts.json').read_bytes()),'B05_present':True,'B08_present':False,'certification_ko':'기존 B05-A 미커밋 상태; B10이 채택·복구·재인증하지 않음'}
result={'schema_version':1,'task':'T6.6F-B10','original_B03_verified':True,'source_layers_distinct':True,'product_imported_or_executed':False,'archive_extracted':False,'frozen_sources':records,'live_dirty_worktree':live,'IR07_supported_runtime':'CPython 3.12.3 / SQLite 3.45.1 / Flutter 3.47.4 / Dart 3.13.3','future_reverification_ko':['제품/backend engine 입력 변경: 새 engine·immutable artifact·exact admission·직접 source-lock 전이 검토와 영향 회귀/금융·구조 oracle 필요','계측·Python runtime/monitoring 환경 변경: 영향받는 계측 정확성·지원 환경·귀속 재검증 필요','client validator/schema/provenance 변경: §23–25에 따른 재검증·receipt 수명 재평가 필요','향후 Android binary/plugin/driver/VFS는 원 HOST 인증과 다른 환경이며 실제 gate 검증 필요'],'historical_correctness_reopened':False,'experimental_adoption_authorized':False}
(OUT/'source-certification-boundaries.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'archives_verified':len(records),'payload_files':[r['files'] for r in records],'engines_verified':True,'live_engine':live_engine,'product_executed':False}))
