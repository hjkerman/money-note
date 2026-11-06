"""완료된 IR07 배치의 원문·adapter·oracle만 압축 보존한다."""
import hashlib,json,pathlib,tarfile
W=pathlib.Path('/tmp/money-note-t66f-b03-ir07-20261025');E=pathlib.Path('/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b03-ir07');out=E/'scratch-evidence.tar.gz';assert not out.exists()
paths=['originals','ir06-evidence','http','tree/docs/benchmarks/t66f-b03-ic06/evidence','tree/work'];records=[]
with tarfile.open(out,'w:gz',dereference=False) as tar:
 for name in paths:
  p=W/name
  if not p.exists():continue
  for f in sorted(p.rglob('*')):
   if f.is_symlink():
    records.append({'path':str(f.relative_to(W)),'kind':'symlink','target':str(f.readlink())})
   elif f.is_file():
    records.append({'path':str(f.relative_to(W)),'kind':'file','bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
  tar.add(p,arcname=name,recursive=True)
with tarfile.open(out) as tar:
 for r in records:
  p=tar.getmember(r['path'])
  if r['kind']=='file':assert p.isfile() and hashlib.sha256(tar.extractfile(p).read()).hexdigest()==r['sha256']
  else:assert p.issym() and p.linkname==r['target']
v={'archive':out.name,'archive_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'archive_bytes':out.stat().st_size,'members':records,'all_members_verified':True,'frozen_source_duplicate_archived':False}
(E/'scratch-evidence-manifest.json').write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');print({'members':len(records),'archive_bytes':out.stat().st_size})
