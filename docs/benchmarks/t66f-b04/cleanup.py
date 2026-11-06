"""종료된 B04 소유 scratch만 정리. 원 source/외부 cache는 보존한다."""
import gzip,hashlib,json,os,pathlib,shutil,subprocess,time
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b04';W=pathlib.Path('/tmp/money-note-t66f-b04-20261026');T=W/'tree'
assert W.resolve()==pathlib.Path('/tmp/money-note-t66f-b04-20261026') and W.is_dir()
assert all(json.loads(p.read_text())['status']!='RUNNING' for p in E.glob('execution-*.json'))
assert (E/'checks.json').exists() and not (E/'cleanup.json').exists()
ps=subprocess.check_output(['ps','-eo','pid,comm,args'],text=True).splitlines();active=[s for s in ps if str(W) in s and len(s.split())>1 and s.split()[1] in ('flutter_tester','dartvm','dartaotruntime','python','python3')];assert not active,active
r=subprocess.run([str(R/'.venv/bin/python'),str(E/'provenance.py'),'check'],capture_output=True,text=True);assert r.returncode==0,r.stdout+r.stderr
# 실제 실행된 최종 driver와 분석 adapter를 남긴다.
shutil.copyfile(T/'docs/benchmarks/t66f-b04/grid_test.dart',E/'grid_test.dart')
shutil.copyfile(T/'mobile/test/b04_stage_analysis.dart',E/'driver-history/stage-analysis-adapter.dart')
runtime=E/'runtime';runtime.mkdir(exist_ok=False)
for rec in json.loads((E/'client-sqlite-runtime.json').read_text()):
 p=pathlib.Path(rec['library']);data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==rec['sha256']
 with (runtime/'libsqlite3.so.gz').open('xb') as f:
  with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:g.write(data)
 rec['retained_library']='docs/benchmarks/t66f-b04/runtime/libsqlite3.so.gz'
 (runtime/'manifest.json').write_text(json.dumps(rec,ensure_ascii=False,indent=2)+'\n')
logs=E/'logs';logs.mkdir(exist_ok=False);archive=[]
for p in sorted((W/'raw').iterdir()):
 if not p.is_file():continue
 out=logs/(p.name+'.gz');data=p.read_bytes()
 with out.open('xb') as f:
  with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as g:g.write(data)
 with gzip.open(out,'rb') as g:assert g.read()==data
 archive.append({'path':str(out.relative_to(R)),'source':str(p),'uncompressed_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
# emergency link가 정상 backend backup과 같은 최종 logical state임을 검증한 기록이 필요하다.
if (E/'failure-retention.json').exists():assert (E/'failure-retention-final.json').exists()
files=[];seen=set();allocated=logical=0
for base,dirs,names in os.walk(W,followlinks=False):
 for name in names:
  p=pathlib.Path(base)/name
  if p.is_symlink():continue
  s=p.stat();key=(s.st_dev,s.st_ino)
  files.append({'path':str(p),'bytes':s.st_size,'allocated_bytes':s.st_blocks*512,'inode':s.st_ino})
  logical+=s.st_size
  if key not in seen:allocated+=s.st_blocks*512;seen.add(key)
  if p.suffix in ('.sqlite','.sqlite3') or p.name.endswith(('-wal','-shm')):
   v=subprocess.run(['fuser',str(p)],capture_output=True,text=True);assert v.returncode==1 and not v.stdout and not v.stderr,(p,v.stdout,v.stderr)
# task 외부 symlink 대상은 os.walk와 rmtree 모두 따라가지 않는다.
previous=[]
for p in (E/'artifacts').glob('*/manifest.json'):previous.extend(json.loads(p.read_text()).get('cleanup',[]))
pre_free=shutil.disk_usage(W).free
record={'scratch':str(W),'scope':'B04-owned only; all workload processes exited','source_checked_before_cleanup':True,'preserved_logs':archive,'removed_scratch_files':files,'scratch_logical_bytes':logical,'scratch_unique_inode_allocated_bytes':allocated,'prior_boundary_cleanup':previous,'prior_boundary_allocated_bytes':sum(x['allocated_bytes'] for x in previous),'preexisting_deleted':0,'frozen_candidates_deleted':0,'external_cache_deleted':0,'removed':False}
(E/'cleanup-receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
shutil.rmtree(W);record.update(removed=True,free_disk_before=pre_free,free_disk_after=shutil.disk_usage('/tmp').free);(E/'cleanup-receipt.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
retained=sum(p.stat().st_size for p in E.rglob('*') if p.is_file());total=allocated+record['prior_boundary_allocated_bytes']
summary=f"규모별 matched SQLite backup·gzip·SHA·독립 graph/value oracle 뒤 비활성 task DB를 정리했다. 종료 scratch {len(files)}개 파일과 앞선 경계 정리의 관찰 할당량 합은 {total/1024**2:.1f}MiB다(중간 SQLite/WAL 생성 I/O 전체 추정 아님). 증거는 약 {retained/1024**2:.1f}MiB 보존했다. 기존 파일·동결 후보·외부 cache 삭제0, 활성 DB/WAL 삭제0이다. 실제 free-disk 변화는 호스트의 다른 쓰기와 섞이므로 이 할당량 합과 같다고 주장하지 않는다."
(E/'cleanup.json').write_text(json.dumps({'summary_ko':summary,'footer_ko':f'B04 scratch 및 검증된 DB 정리; 관찰 할당량 {total/1024**2:.1f}MiB, matched 증거 보존; 기존 삭제0','total_observed_removed_allocated_bytes':total,'retained_bytes_at_cleanup':retained},ensure_ascii=False,indent=2)+'\n');print(summary)
