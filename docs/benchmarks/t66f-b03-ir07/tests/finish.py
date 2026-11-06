"""완료된 IR07 증거를 확인한 뒤 검증된 작업 소유 scratch만 정리한다."""
import hashlib,json,os,pathlib,shutil,tarfile
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b03-ir07';W=pathlib.Path('/tmp/money-note-t66f-b03-ir07-20261025')
assert json.loads((E/'findings.json').read_bytes())['B03']=='CLOSED'
assert json.loads((E/'final-candidate-integrity.json').read_bytes())['result']=='PASS'
for name in ['scratch-evidence-manifest.json','http-evidence-manifest.json']:
 m=json.loads((E/name).read_bytes());archive=E/m['archive'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['archive_sha256']
 with tarfile.open(archive) as tar:
  for rec in m['members']:
   if rec.get('kind')=='symlink':continue
   member=rec.get('member',rec.get('path'));assert hashlib.sha256(tar.extractfile(member).read()).hexdigest()==rec['sha256']
known={'context','http-concurrent.json','http-frozen.json','http-n260.json','http-n9.json','ir06-evidence','originals','report-template.md','tree'}
assert {p.name for p in W.iterdir()}==known
active=[]
for proc in pathlib.Path('/proc').iterdir():
 if not proc.name.isdigit():continue
 try:cwd=pathlib.Path(os.readlink(proc/'cwd'))
 except OSError:continue
 if cwd.is_relative_to(W):active.append(int(proc.name))
assert not active,active
files=[p for p in W.rglob('*') if p.is_file() and not p.is_symlink()];size=sum(p.lstat().st_size for p in files)
stage1=json.loads((E/'cleanup-stage1.json').read_bytes());total=size+stage1['removed_bytes']
cleanup_text=f'물리 IR07 scratch 하나에서 복원 source·단일 Flutter build·소형 합성 자료를 사용했다. 원문/adapter/수치 증거는 두 압축본과 member별 SHA로 검증·보존했다. 종료된 작업 소유 scratch의 논리 파일 {total:,}B를 제거했다. 기존 cache·과거 증거·동결 archive를 삭제하지 않았다. 물리 디스크 회수량과 논리 파일 길이를 같은 수치로 주장하지 않는다.'
text=(W/'report-template.md').read_text().replace('@@AUTH@@','72').replace('@@CLEANUP@@',cleanup_text)
assert '@@' not in text
text+='\n```text\n'+(E/'final-verdict.txt').read_text()+'```\n'
report=R/'docs/t66f-b03-ir07-independent-pep669-closure.md';assert not report.exists();report.write_text(text)
shutil.rmtree(W)
p=pathlib.Path('/tmp/ir07-index-before.txt')
assert p.read_bytes()==(E/'starting-index.txt').read_bytes();index_copy_size=p.stat().st_size;p.unlink()
record={'result':'PASS','scratch':str(W),'scratch_removed':not W.exists(),'active_processes_before_removal':active,'verified_owned_children':sorted(known),'logical_file_bytes_removed_final':size,'logical_file_bytes_removed_stage1':stage1['removed_bytes'],'logical_file_bytes_removed_total':total,'scratch_files_removed_final':len(files),'temporary_index_copy_removed':True,'temporary_index_copy_bytes':index_copy_size,'retained':['scratch-evidence.tar.gz','scratch-evidence-manifest.json','http-evidence.tar.gz','http-evidence-manifest.json','모든 IR07 원문/명령/SHA/결과/독립 test source'],'preexisting_cache_removed':False,'historical_evidence_removed':False,'historical_frozen_archive_removed':False,'report':str(report)}
(E/'cleanup.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n');print({'logical_bytes_removed':total,'scratch_removed':True,'report':str(report)})
