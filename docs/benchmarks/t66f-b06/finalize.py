"""입력 증거 목록과 최종 SHA 목록을 만든다. 기존 결과를 변경하지 않는다."""
import json,pathlib,hashlib,sys
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b06';report=R/'docs/t66f-b06-cold-acquisition-critical-path-analysis.md'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sys.argv[1]=='manifest':
 inv=json.loads((E/'measurement-inventory.json').read_text());paths={r['raw'] for r in inv['records']}
 paths.update(['AGENTS.md','docs/project-state.md','docs/domain-model.md','docs/known-issues.md','docs/development-artifact-hygiene.md','docs/t66/c/t66c-delta-sync-protocol.md','docs/t66f-b03-ir07-independent-pep669-closure.md'])
 paths.update(['docs/t66f-b04-phase-b-measurement-feasibility.md','docs/t66f-b05-lookup-hot-body-decode-optimization.md','docs/t66f-b05a-engine-admission-real-flutter-ab.md','docs/t66f-b05b-independent-5k-on-ab-replication.md'])
 paths.update([f'docs/benchmarks/{study}/run-manifest.json' for study in ['t66f-b04','t66f-b05','t66f-b05a','t66f-b05b']])
 paths.update(['docs/benchmarks/t66f-b04/environment.json','docs/benchmarks/t66f-b04/historical-p03.json','docs/benchmarks/t66f-b05/profile-baseline.json','docs/benchmarks/t66f-b05/profile-optimized.json','docs/benchmarks/t66f-b05a/environment.json','docs/benchmarks/t66f-b05a/fixture-n1000.json','docs/benchmarks/t66f-b05a/fixture-n5000.json','docs/benchmarks/t66f-b05a/runtime-and-reconstruction.json','docs/benchmarks/t66f-b05b/preflight.json','docs/benchmarks/t66f-b05b/comparison-summary.json','docs/benchmarks/t66f-b05b/driver-identities.json'])
 paths.update(['backend/isolated_sync/'+p+'.py' for p in ['http','transfer','retention_schema','finalization','observation','canonical','store']])
 paths.update(['mobile/lib/src/segmented/fetch.dart','mobile/lib/src/segmented/store.dart','docs/benchmarks/t66f-b03-ic01-p03/timing.dart','docs/benchmarks/t66f-b03/counters.py','docs/benchmarks/t66f-b05a/cold_test.dart','docs/benchmarks/t66f-b05a/server.py'])
 for r in inv['records']:
  if r['study'] in ['B05A','B05B']:paths.add(str(pathlib.Path(r['raw']).parent/'independent-verification.json'))
 inputs=[{'path':p,'sha256':sha(R/p),'bytes':(R/p).stat().st_size} for p in sorted(paths)]
 outputs=sorted([p.relative_to(R).as_posix() for p in E.iterdir() if p.is_file()]+['docs/benchmarks/t66f-b06/evidence-manifest.json','docs/benchmarks/t66f-b06/analysis-validation.json','docs/benchmarks/t66f-b06/SHA256SUMS','docs/t66f-b06-cold-acquisition-critical-path-analysis.md'])
 m={'schema_version':1,'task':'T6.6F-B06','verdict':'PASS — NEXT EXPERIMENT IDENTIFIED','next_choice':'B — TARGETED PROFILING','new_experiments':0,'source_edited':False,'inputs':inputs,'archive_identities':'source-identities.json','generated_outputs':sorted(set(outputs)),'analysis_code':[{'path':p.relative_to(R).as_posix(),'sha256':sha(p)} for p in sorted(E.glob('*.py'))],'source_preservation':'preservation-after.json','measurement_inventory':'measurement-inventory.json','critical_path':'critical-path-summary.json','ranking':'bottleneck-ranking.json','next_decision':'next-action-decision.json','cleanup':'cleanup.json','analysis_validation':'analysis-validation.json','output_sha256_manifest':'SHA256SUMS','reproduction':'identities.py → extract.py → decide.py → report.py → provenance.py check → finalize.py manifest → validate.py → finalize.py seal; preservation-before와 cleanup은 이번 execution 원문으로 재생성하지 않음'}
 (E/'evidence-manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'input_files':len(inputs),'new_experiments':0}))
else:
 assert sys.argv[1]=='seal'
 v=json.loads((E/'analysis-validation.json').read_text());assert v['status']=='PASS'
 p=json.loads((E/'preservation-after.json').read_text());assert not p['preexisting_changed'] and p['index_preserved'] and p['staged_entries_preserved']
 paths=sorted([p for p in E.iterdir() if p.is_file() and p.name!='SHA256SUMS']+[report]);lines=[sha(p)+'  '+p.relative_to(R).as_posix() for p in paths]
 (E/'SHA256SUMS').write_text('\n'.join(lines)+'\n');print(json.dumps({'sealed_output_files':len(paths),'evidence_bytes':sum(p.stat().st_size for p in E.iterdir() if p.is_file()),'report_bytes':report.stat().st_size,'verdict':v['status']}))
