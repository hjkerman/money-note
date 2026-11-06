"""B07 보고서·증거의 출처, 제한, 산술을 검증하고 해시 목록을 만든다."""
import pathlib,json,hashlib,re,math,gzip
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b07';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def get(n):return json.loads((E/n).read_text())
def save(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
a=get('call-path-attribution.json');m=get('run-manifest.json');rows=get('packet-timings.json')['packets'];p=get('preservation-after.json');budget=get('execution-budget.json');pre=get('preflight.json')
assert m['attempted_packets']==m['complete_packets']==30 and m['incomplete_packets']==0 and budget['returncode']==0 and budget['wall_s']<120 and not budget['watchdog_fired']
assert not p['preexisting_changed'] and not p['new_visible_outside_B07'] and p['index_preserved'] and p['staged_entries_preserved']
assert get('verification.json')['status']=='PASS' and not get('verification.json')['source_changes']
assert not pathlib.Path('/tmp/money-note-t66f-b07-20261026').exists()
assert all(r['connect_calls']==r['open_calls']==3 and r['close_calls']==5 and r['collector_closed'] and r['pending']==0 and r['completion_error'] is None for r in rows)
assert all(abs(sum(x[k]for k in ['connect_s','lookup_s','resolution_s','handler_other_s'])-x['handler_s'])<1e-9 for x in a['per_packet_handler_nonoverlapping_parts'])
assert a['object_probe_metrics']['expected_revision_contract']['calls']==42*33
assert m['baseline_engine']==pre['engine_sha']=='7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c'
for row in rows:
 if not row['probe']:assert not row['metrics'] and not row['connect_intervals']
 for event in row.get('function_intervals',[]):assert event['wall_ns']==event['end_ns']-event['start_ns'] and event['self_ns']>=0 and event['self_cpu_ns']>=0
ret=get('retained-database.json');db=R/ret['path'];assert sha(db)==ret['compressed_sha256'] and hashlib.sha256(gzip.decompress(db.read_bytes())).hexdigest()==ret['uncompressed_sha256']
# wrapper가 사용한 원시 source/candidate 층과 실험 tooling 층을 분리한다.
m['tooling']={v.name:sha(v)for v in E.glob('*.py')};m['measurement_tooling']={name:m['tooling'][name]for name in ['probe.py','experiment.py','run.py']};m['B07_measurement_tooling_digest']=hashlib.sha256(json.dumps(m['measurement_tooling'],sort_keys=True,separators=(',',':')).encode()).hexdigest();m['preservation']='preservation-after.json';m['cleanup']='cleanup.json';save('run-manifest.json',m)
paths=['AGENTS.md','docs/development-artifact-hygiene.md','docs/project-state.md','docs/domain-model.md','docs/known-issues.md','docs/t66/c/t66c-delta-sync-protocol.md','docs/t66f-b03-ir07-independent-pep669-closure.md','docs/t66f-b04-phase-b-measurement-feasibility.md','docs/t66f-b05b-independent-5k-on-ab-replication.md','docs/t66f-b06-cold-acquisition-critical-path-analysis.md','docs/benchmarks/t66f-b06/evidence-manifest.json','docs/benchmarks/t66f-b06/critical-path-summary.json','docs/benchmarks/t66f-b05a/fixture-n1000.json','docs/benchmarks/t66f-b05a/retained-fixtures.json','docs/benchmarks/t66f-b05a/fixture-template-n1000.sqlite.gz','docs/benchmarks/t66f-b05a/raw/n5000-1-A-on/run.json','docs/benchmarks/t66f-b05b/raw/n5000-0-A-on/run.json','docs/benchmarks/t66f-b05b/comparison-summary.json']
inputs=[{'path':v,'sha256':sha(R/v),'bytes':(R/v).stat().st_size}for v in paths]
source_archive=pathlib.Path(pre['archive']);assert sha(source_archive)==pre['archive_sha256']
manifest={'task':'T6.6F-B07','verdict':a['classification'],'engineering_decision':a['engineering_decision'],'inputs':inputs,'external_original_archive':{'path':str(source_archive),'sha256':sha(source_archive)},'source_manifest':'baseline-source-manifest.json','preflight':'preflight.json','environment':'environment.json','run_manifest':'run-manifest.json','raw_attempts':'requests.jsonl','raw_packet_times':'packets.jsonl','attribution':'call-path-attribution.json','decision':'next-action-decision.json','verification':'verification.json','cleanup':'cleanup.json','preservation':'preservation-after.json','retained_db':'retained-database.json','measurement_tooling_digest':m['B07_measurement_tooling_digest'],'output_sha_manifest':'SHA256SUMS','no_new_optimized_candidate':True,'actual_execution_count':1,'packets':30,'wall_seconds':budget['wall_s']}
save('evidence-manifest.json',manifest)
report=R/'docs/t66f-b07-bounded-connect-schema-attribution.md';body=report.read_text();missing=[x for x in re.findall(r'\]\(([^)]+)\)',body)if not x.startswith('http') and not (report.parent/x).exists()];assert not missing,missing
assert not re.search(r'[\u3040-\u30ff]',body)
for v in E.iterdir():
 if v.suffix in ['.py','.json','.jsonl','.txt']:assert not re.search(r'[\u3040-\u30ff]',v.read_text()),v.name
save('analysis-checks.json',{'status':'PASS','scope':'offline JSON/source/SQLite/hash/limit assertions; no new packets','packet_rows':30,'within_32_and_120':True,'all_incomplete_counts_zero':True,'nonoverlap_arithmetic_valid':True,'all_raw_timings_retained':True,'source_and_git_preserved':True,'missing_report_links':missing,'report_korean_kana_check':'PASS','new_measurement_attempts':0})
files=sorted([v for v in E.iterdir()if v.is_file() and v.name!='SHA256SUMS']+[report]);(E/'SHA256SUMS').write_text('\n'.join(sha(v)+'  '+v.relative_to(R).as_posix()for v in files)+'\n')
print(json.dumps({'status':'PASS','outputs_sealed':len(files),'input_identities':len(inputs),'packets':30,'wall_s':budget['wall_s'],'index_preserved':True,'new_packets':0,'evidence_bytes':sum(v.stat().st_size for v in E.iterdir()if v.is_file())}))
