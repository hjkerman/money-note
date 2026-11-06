from pathlib import Path
import json,hashlib,gzip,os,subprocess,stat,re,tarfile
A=Path('/tmp/money-note-ir05-20261024');R=Path('/home/hjkerman/codex/money-note');E=A/'evidence';D=R/'docs/benchmarks/t66f-b03-ir05';report=R/'docs/t66f-b03-ir05-independent-correctness-closure.md';env=dict(os.environ,GIT_OPTIONAL_LOCKS='0');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();git=lambda *a:subprocess.check_output(['git',*a],cwd=R,env=env).decode()
pre=json.loads((E/'preexisting-files.json').read_text());bad=[]
for x in pre:
 p=R/x['path']
 if not p.is_file() or sha(p)!=x['sha256'] or oct(stat.S_IMODE(p.stat().st_mode))!=x['mode']:bad.append(x['path'])
assert not bad
s=json.loads((E/'starting-state.json').read_text());assert git('rev-parse','HEAD').strip()==s['head'] and git('symbolic-ref','--short','HEAD').strip()==s['branch'];assert sha(R/'.git/index')==s['index_sha256'] and git('ls-files','--stage')==s['staged']
status=git('status','--porcelain=v1','--untracked-files=all');own=lambda line:line[3:]=='docs/t66f-b03-ir05-independent-correctness-closure.md' or line[3:].startswith('docs/benchmarks/t66f-b03-ir05/')
assert '\n'.join(x for x in status.splitlines() if not own(x))=='\n'.join(s['status'].splitlines())
proof={'preexisting_files_verified':len(pre),'differences':bad,'head':s['head'],'branch':s['branch'],'index_sha256':sha(R/'.git/index'),'index_bytes_unchanged_by_ir05':True,'staged_entries_unchanged':True,'previous_status_preserved_excluding_only_ir05_additions':True,'existing_historical_evidence_modified':False,'binding_protocol_modified':False,'product_source_modified':False,'commit':None,'push':'NOT PERFORMED'};(D/'final-preservation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
frozen=json.loads((E/'starting-frozen-identities.json').read_text())
expected={'645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8':'87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01','27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3':'4655111c579503ef2c0969f82b5dca4830c06ac1123002cd6e8887109728b012','dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370':'145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21'}
for folder,v in frozen.items():
 p=Path(folder);assert oct(stat.S_IMODE(p.stat().st_mode))==v['directory_mode'];assert sha(p/'candidate.tar.gz')==expected[p.name]
 for name,x in v['files'].items():q=p/name;assert sha(q)==x['sha256'] and oct(stat.S_IMODE(q.stat().st_mode))==x['mode']
F=Path('/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370');m=json.loads((F/'source-manifest.json').read_text());entries=m['entries'];assert hashlib.sha256(json.dumps(entries,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==F.name
with tarfile.open(F/'candidate.tar.gz') as t:
 names=t.getnames();assert len(names)==860 and len(names)==len(set(names)) and all(h.isfile() for h in t)
 assert json.load(t.extractfile('metadata/source-manifest.json'))==m
 for x in entries:
  h=t.getmember('source/'+x['path']);b=t.extractfile(h).read();assert hashlib.sha256(b).hexdigest()==x['sha256'] and len(b)==x['bytes'] and h.mode==int(x['mode'],8)
(D/'final-archive-check.json').write_text(json.dumps({'archive_sha256':sha(F/'candidate.tar.gz'),'payload_sha256':F.name,'regular_members':860,'source_files':850,'source_bytes':sum(x['bytes'] for x in entries),'all_three_frozen_directories_preserved':True},indent=2)+'\n')
old='IC03 대비 실제 변경은 test-only counter 한 파일이며';new='IC03의 IR04 대비 실행 코드 변경은 test-only counter 한 파일이며';text=report.read_text();assert old in text or new in text;text=text.replace(old,new)
p=A/'tooling/write_report.py';src=p.read_text();assert old in src or new in src;p.write_text(src.replace(old,new))
adjustments=[]
for link in re.findall(r'\]\(([^)]+)\)',text):
 p=report.parent/link
 if not p.exists() and p==D/'retained-evidence.json':continue
 if not p.exists():
  alt=Path(str(p)[:-3]) if str(p).endswith('.gz') else Path(str(p)+'.gz');assert alt.exists(),('missing report evidence',link)
  replacement=str(alt.relative_to(report.parent));text=text.replace(']('+link+')',']('+replacement+')');adjustments.append({'before':link,'after':replacement})
report.write_text(text);assert not re.search('[\u3040-\u30ff]',text);assert all((report.parent/x).exists() or report.parent/x==D/'retained-evidence.json' for x in re.findall(r'\]\(([^)]+)\)',text))
(D/'report-check.json').write_text(json.dumps({'all_links_valid':True,'compression_name_adjustments':adjustments,'japanese_explanatory_prose':False,'report_provenance_phrase':'IC03의 IR04 대비 변경 한 파일; IR05 자체 source 수정 없음'},ensure_ascii=False,indent=2)+'\n')
for name in ['write_report.py','final_verify.py']:
 p=A/'tooling'/name;q=D/'tooling'/name
 with q.open('x') as out:out.write(p.read_text())
with (D/'final-footer.txt').open('x') as out:out.write((A/'footer.txt').read_text())
files=[{'path':str(p.relative_to(R)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(D.rglob('*')) if p.is_file() and p.name!='retained-evidence.json']
manifest={'report':{'path':str(report.relative_to(R)),'bytes':report.stat().st_size,'sha256':sha(report)},'files':files,'total_files_excluding_this_manifest':len(files),'total_bytes_excluding_this_manifest':sum(x['bytes'] for x in files),'frozen_candidate':str(F),'ephemeral_scratch':'/tmp의 소형 원자료 사본; authoritative source는 frozen archive, 지속 audit evidence는 이 manifest의 저장소 파일'}
(D/'retained-evidence.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
for x in files:
 p=R/x['path'];assert sha(p)==x['sha256']
 if p.suffix=='.gz':
  with gzip.open(p,'rb') as z:
   while z.read(65536):pass
assert sha(R/'.git/index')==s['index_sha256']
assert all((report.parent/x).exists() for x in re.findall(r'\]\(([^)]+)\)',report.read_text()))
print(json.dumps({'report':str(report),'report_bytes':report.stat().st_size,'retained_files':len(files)+1,'retained_bytes':sum(x['bytes'] for x in files)+(D/'retained-evidence.json').stat().st_size,'preexisting_preserved':len(pre),'index_preserved':True,'all_frozen_preserved':True,'report_links_valid':True,'gzip_integrity':True,'independent_results':json.loads((D/'independent-test-results.json').read_text())['fresh_independent']},ensure_ascii=False))
