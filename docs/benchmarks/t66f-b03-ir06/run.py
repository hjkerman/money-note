"""IR06 전용 실행 기록. 후보 소스와 역사 결과를 수정하지 않는다."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
SCRATCH = ROOT / 'work/t66f-b03-ir06'
TREE = SCRATCH / 'candidate'
OUT = Path(__file__).parent / 'evidence'

def hashes():
    manifest = json.loads((SCRATCH / 'source-manifest.json').read_text())
    return {e['path']: hashlib.sha256((TREE / e['path']).read_bytes()).hexdigest() for e in manifest['entries']}

def main():
    label = sys.argv[1]
    config = json.loads(Path(sys.argv[2]).read_text())
    target = OUT / (label + '.json')
    log = OUT / (label + '.log.gz')
    assert not target.exists() and not log.exists()
    before = hashes()
    started = time.monotonic()
    env = {**os.environ, 'PYTHONPATH': str(TREE / 'backend'), 'PYTHONDONTWRITEBYTECODE': '1', **config.get('env', {})}
    with gzip.open(log, 'wb') as output:
        p = subprocess.Popen(config['command'], cwd=config.get('cwd', str(TREE)), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        with p.stdout:
            while chunk := p.stdout.read1(65536): output.write(chunk)
        p.wait()
    record = dict(label=label, **config, exit_code=p.returncode, seconds=time.monotonic()-started, raw=log.name, source_payload='47edb4face776900018a82904cba9c41f184019473e0fe8900cb582da9f922b5', source_hashes_before=before, source_hashes_after=hashes())
    record['source_unchanged'] = record['source_hashes_before'] == record['source_hashes_after']
    if config.get('xml') and Path(config['xml']).exists():
        cases = ET.parse(config['xml']).findall('.//testcase')
        record['counts'] = {'PASS': sum(not any(c.find(x) is not None for x in ['failure','error','skipped']) for c in cases), 'FAIL':sum(c.find('failure') is not None or c.find('error') is not None for c in cases), 'SKIP':sum(c.find('skipped') is not None for c in cases)}
    if '--machine' in config['command']:
        counts = dict(PASS=0, FAIL=0, SKIP=0)
        events = []
        for line in gzip.open(log,'rt'):
            try: e=json.loads(line)
            except ValueError: continue
            if not isinstance(e,dict): continue
            if e.get('type')=='testStart': events.append(e)
            if e.get('type')=='testDone' and not e.get('hidden'):
                counts['SKIP' if e.get('skipped') else 'PASS' if e.get('result')=='success' else 'FAIL']+=1
            if e.get('type')=='done':record['done']=e.get('success')
        record['counts']=counts
        record['test_start_events']=events
    target.write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:record.get(k) for k in ['label','exit_code','seconds','counts','done','source_unchanged']},ensure_ascii=False),flush=True)
    if p.returncode:
        print(''.join(gzip.open(log,'rt').readlines()[-45:]),flush=True)
    return p.returncode

if __name__=='__main__':raise SystemExit(main())
