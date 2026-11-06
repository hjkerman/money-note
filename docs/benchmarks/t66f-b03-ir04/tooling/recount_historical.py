from pathlib import Path
import json,gzip,re,xml.etree.ElementTree as ET,hashlib
R=Path('/home/hjkerman/codex/money-note');D=R/'docs/benchmarks/t66f-b03-ic02/evidence';E=Path('/tmp/money-note-ir04-20261024/evidence');r={'evidence_class':'historical implementation-side execution; raw independently recounted; not fresh IR04 independent full suite'}
root=ET.parse(D/'backend-guard-final.xml').getroot();s=list(root.iter('testsuite'));cases=list(root.iter('testcase'));elements={tag:len(list(root.iter(tag))) for tag in ['failure','error','skipped']};assert not any(elements.values())
raw=gzip.open(D/'backend-guard-final.log.gz','rt').read();summary=next(x for x in raw.splitlines() if re.search(r'1446 passed.*1540 subtests passed',x));assert len(cases)==1446 and sum(int(x.attrib['tests']) for x in s)==2986
r['backend']={'testcase_nodes':len(cases),'tests_attribute_including_subtests':2986,'tests':1446,'subtests':1540,'elements':elements,'summary':summary,'raw_sha256':hashlib.sha256((D/'backend-guard-final.log.gz').read_bytes()).hexdigest()}
r['flutter_parts']=[]
for n in range(3):
 name=f'flutter-guard-final-part-{n}';record=json.loads((D/(name+'.json')).read_text());counts={'PASS':0,'FAIL':0,'SKIP':0};done=None
 for line in gzip.open(D/record['raw'],'rt'):
  try:v=json.loads(line)
  except ValueError:continue
  if not isinstance(v,dict):continue
  if v.get('type')=='testDone' and not v.get('hidden'):counts['SKIP' if v.get('skipped') else 'PASS' if v.get('result')=='success' else 'FAIL']+=1
  if v.get('type')=='done':done=v.get('success')
 assert done is True and not counts['FAIL'] and record['exit_code']==0
 r['flutter_parts'].append({'name':name,'counts':counts,'done_success':done,'exit_code':record['exit_code'],'raw_sha256':hashlib.sha256((D/record['raw']).read_bytes()).hexdigest()})
r['flutter_total']={k:sum(p['counts'][k] for p in r['flutter_parts']) for k in ['PASS','FAIL','SKIP']};assert r['flutter_total']=={'PASS':1698,'FAIL':0,'SKIP':2}
(E/'historical-ic02-suite-recount.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print('historical backend 1446 / 1540; Flutter',r['flutter_total'],'raw recount matched')
