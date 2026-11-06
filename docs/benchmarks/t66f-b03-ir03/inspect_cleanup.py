import json,os
from pathlib import Path
r=Path('/tmp/money-note-ir03-20261023');targets=[r/x for x in ['candidate','historical','flutter-tmp','p05-scratch','p05-pytest']];ancestors=set();pid=os.getpid()
while pid and pid not in ancestors:
 ancestors.add(pid)
 try:pid=int(Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()[1])
 except OSError:break
hits=[];denied=[]
for proc in Path('/proc').iterdir():
 if not proc.name.isdigit() or int(proc.name) in ancestors:continue
 try:
  if proc.stat().st_uid!=os.getuid():continue
  entries=[proc/'cwd',*(proc/'fd').iterdir()];refs=[]
  for entry in entries:
   try:value=os.readlink(entry)
   except OSError:continue
   if any(value==str(t) or value.startswith(str(t)+'/') for t in targets):refs.append({'kind':entry.name,'target':value})
  if refs:hits.append({'pid':int(proc.name),'cmdline':(proc/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace'),'references':refs})
 except (OSError,PermissionError) as error:denied.append({"pid":proc.name,"error":str(error)})
out={'targets':[str(t) for t in targets if t.exists()],'active_references':hits,'visibility_denied':denied,'method':'동일 UID /proc cwd·FD 검사; 자신의 ancestor는 제외'}
(r/'evidence/cleanup-preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False))
