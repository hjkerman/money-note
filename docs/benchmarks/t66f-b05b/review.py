"""재취득 없이 checksum·요약·raw·Git 보존을 최종 대조한다."""
import gzip,json,pathlib,re,tarfile
from prepare import R,E,H,sha,save,git,inventory
m=json.loads((E/'run-manifest.json').read_text());c=json.loads((E/'comparison-summary.json').read_text());p=json.loads((E/'preservation-before.json').read_text());report=R/'docs/t66f-b05b-independent-5k-on-ab-replication.md'
assert m['completed_cold']==m['planned_cold']==2 and all(r['E1'] and r['E2'] and r['E3'] and r['E4'] for r in m['runs']);assert m['actual_reversed_order']==list(reversed(m['original_order']));assert m['OFF_cold']==m['N10k_cold']==m['N50k_cold']==m['N100k_cold']==0
assert c['new_B05B']['baseline_s']=='149.743978' and c['new_B05B']['optimized_s']=='155.002541';assert c['performance_classification']=='NO MATERIAL SYSTEM BENEFIT OBSERVED' and c['N50k_followup']=='NOT JUSTIFIED';assert not c['order_sign_change']
for r in m['runs']:
 raw=R/r['raw'];iv=R/r['independent_verification'];assert sha(raw.read_bytes())==r['raw_sha256'];assert sha(iv.read_bytes())==r['independent_verification_sha256'];assert r['renewals']==0 and len(r['observation_leases'])==1
 d=json.loads(raw.read_text());assert d['accepted_after']==r['accepted_after'];v=json.loads(iv.read_text())
 for role in ['client','backend']:
  data=gzip.decompress((raw.parent/(role+'-consistent.sqlite.gz')).read_bytes());assert sha(data)==v['details'][role]['backup_sha256']
# 역사 checksum은 원 bundle의 상대 경로 규칙을 직접 해석한다.
historical=[]
for line in (H/'SHA256SUMS').read_text().splitlines():
 if not line.strip():continue
 expected,name=line.split(maxsplit=1);name=name.lstrip('*');path=H/name
 if not path.exists():path=R/name
 assert path.is_file(),name
 assert sha(path.read_bytes())==expected,name;historical.append(str(path.relative_to(R)))
# driver는 역사 lock와 대조된 그 파일을 사용했고 측정 전 digest와 지금도 같다.
for name,digest in json.loads((E/'driver-identities.json').read_text()).items():assert sha((R/name).read_bytes())==digest
for filename in ['server.py','cold_test.dart']:assert any(pathlib.Path(x).name==filename for x in historical)
now=inventory();changes=[s for s,v in p['files'].items() if now.get(s)!=v];added=[s for s in now if s not in p['files']];assert not changes and not added
index=R/git('rev-parse','--git-path','index').decode().strip();assert sha(index.read_bytes())==p['index_sha256'];assert sha(git('ls-files','--stage','-z'))==p['staged_entries_sha256'];assert git('rev-parse','HEAD').decode().strip()==p['head']
assert not re.search('[\u3040-\u30ff]',report.read_text());assert '149.743978' in report.read_text() and '155.002541' in report.read_text();assert (E/'final-footer.txt').read_text() in report.read_text();assert not pathlib.Path('/tmp/money-note-t66f-b05b-20261026').exists()
save(E/'final-review.json',{'status':'PASS','historical_B05A_checksum_files_verified':len(historical),'driver_historical_lock':'PASS','two_cold_only':True,'raw_manifest_report_consistency':'PASS','matched_SQLite_backups':4,'Japanese_explanatory_prose':False,'Git_index_preserved':True,'staged_content_preserved':True,'preexisting_files_verified':len(p['files']),'preexisting_changed':changes,'unexpected_added':added,'scratch_removed':True,'no_additional_acquisition':True})
# checksum 파일은 repository root에서 검증하도록 경로를 고정한다.
files=sorted([q for q in E.rglob('*') if q.is_file() and q.name!='SHA256SUMS']+[report]);(E/'SHA256SUMS').write_text(''.join(sha(q.read_bytes())+'  '+q.relative_to(R).as_posix()+'\n' for q in files))
for line in (E/'SHA256SUMS').read_text().splitlines():expected,name=line.split(maxsplit=1);assert sha((R/name).read_bytes())==expected
print(json.dumps({'status':'PASS','artifact_checksum_files':len(files),'historical_checksum_files':len(historical),'Git_index':'PRESERVED','cold_runs':2,'extra_acquisitions':0,'report_Korean':True}))
