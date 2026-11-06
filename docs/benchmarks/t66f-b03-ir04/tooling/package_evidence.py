from pathlib import Path
import shutil,gzip,json,hashlib
A=Path('/tmp/money-note-ir04-20261024');R=Path('/home/hjkerman/codex/money-note');dest=R/'docs/benchmarks/t66f-b03-ir04';assert not dest.exists(),'preserve any existing IR04 evidence';assert not (R/'docs/t66f-b03-ir04-independent-final-reaudit.md').exists();dest.mkdir()
items=[]
for root,prefix in [(A/'evidence',''),(A/'tests','tests'),(A/'tooling','tooling')]:
 for p in sorted(root.rglob('*')):
  if not p.is_file() or p.is_symlink() or '__pycache__' in p.parts:continue
  rel=Path(prefix)/p.relative_to(root)
  compress=p.suffix in ['.json','.xml','.log','.txt'] and p.stat().st_size>200000
  q=dest/(str(rel)+'.gz' if compress else rel);q.parent.mkdir(parents=True,exist_ok=True)
  if compress:
   with p.open('rb') as f,q.open('xb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as z:shutil.copyfileobj(f,z)
  else:
   with q.open('xb') as out:out.write(p.read_bytes())
  items.append({'scratch':str(p),'retained':str(q.relative_to(R)),'sha256':hashlib.sha256(q.read_bytes()).hexdigest(),'uncompressed_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'compressed':compress})
(dest/'packaging.json').write_text(json.dumps({'items':items,'scratch_kept':'소형 원자료·재현 source·tooling만 보존. /tmp는 재부팅 영속 보관이 아니므로 이 저장소 사본과 새 동결본을 지속 증거로 사용한다.'},ensure_ascii=False,indent=2)+'\n')
(dest/'HANDOFF.md').write_text('''# IR04 감사 인계\n\n판정은 **FAIL**이다. 보존 사고는 별도 판정됐으며 FAIL의 원인은 재현 가능한 Python 설치 수명 중복 계수다. 제품 구현은 수정하지 않았다.\n\n- 후보 source digest: `27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3`\n- archive SHA-256: `4655111c579503ef2c0969f82b5dca4830c06ac1123002cd6e8887109728b012`\n- 새 동결 경로: `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3/`\n- 신규 차단 finding: `B03-IR04-N01` · LOW. `findings.json`과 `rollover-native-2.json`/`rollover-native-9.json` 참조.\n\n최소 재현 source는 `tests/test_ir04_rollover_native.py`다. 기준 commit `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`의 git archive에 새 동결 archive의 `source/`를 overlay하고 manifest bytes/mode를 확인한다. 원 도구의 `/tmp/money-note-ir04-20261024/candidate` 경로를 재구성하거나 root 경로만 새 감사 공간으로 치환한 뒤 원 pytest 명령을 실행한다. numeric 기대값·scope 경계·parser는 변경하지 않는다. 실제 하위 parser 1회에 대해 2B 입력이 4B, 9B 입력이 18B로 보고된다. trace는 line343의 preemption만 강제한다.\n\n원 IR03 N01/N02는 현재 후보에서 PASS이고 IA04 원 nested 사례도 3회/6B다. 다만 새로운 설치 세대 교대 결함으로 IA04 전체 closure는 FAIL이다. parent IR02에서도 같은 결함이 재현되므로 IC02가 새로 만들었다고 단정하지 않는다.\n\n별도 구현 세션은 delegate 캡처와 설치 reference/teardown 소유권 경계만 최소 교정해야 한다. 교정 후 새 source identity에서 보존된 독립 재현과 직접 영향 회귀를 검증한다. 현재 read-only snapshot이나 역사 보고서·기대 SHA·Git index는 수정하지 않는다. 새로운 N=100k cold, 비용 grid, R1 및 배포는 허가되지 않았다.\n''')
print(json.dumps({'files':len(items)+2,'retained_bytes':sum(p.stat().st_size for p in dest.rglob('*') if p.is_file()),'path':str(dest)}))
