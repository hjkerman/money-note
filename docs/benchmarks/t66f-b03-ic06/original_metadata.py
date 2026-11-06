"""원 재현 bytes를 그대로 실행하고 종료 뒤 남은 namespace에서 tool ID를 기록한다."""
import hashlib,json,os,sys,traceback
from pathlib import Path
R=Path(__file__).resolve().parents[3];O=Path(__file__).parent/'evidence'
label,tree,name,*arguments=sys.argv[1:]
source=R/'docs/benchmarks/t66f-b03-ir06/tests'/name
body=source.read_bytes();before=hashlib.sha256(body).hexdigest()
os.environ['IR06_TREE']=tree;sys.argv=[str(source),*arguments]
namespace={'__name__':'__main__','__file__':str(source)}
error=None
try:
 exec(compile(body,str(source),'exec'),namespace)
except BaseException as caught:
 error=caught;traceback.print_exc()
finally:
 assert hashlib.sha256(source.read_bytes()).hexdigest()==before
 m=namespace.get('m');tool=namespace.get('tool')
 d=dict(source=str(source.relative_to(R)),source_sha256=before,subject_tree=tree,subject_counter_sha256=hashlib.sha256((Path(tree)/'docs/benchmarks/t66f-b03/counters.py').read_bytes()).hexdigest(),execution='원 source bytes compile/exec; sys trace/profile 및 monitoring API를 교체하지 않음',python=sys.version,monitoring_available=hasattr(sys,'monitoring'),tool_id=tool,initial_id_selection='원 next(get_tool is None) 식의 실제 namespace 값',original_result=namespace.get('result'),outer_assertion_error=type(error).__name__ if error else None,refs_after_original_cleanup={k:v['refs'] for k,v in m.INSTALLATIONS.items()} if m else None,stage_after_original_cleanup=m.ACTIVE.get() is not None if m else None)
 p=O/(label+'-metadata.json');assert not p.exists();p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
raise SystemExit(1 if error else 0)
