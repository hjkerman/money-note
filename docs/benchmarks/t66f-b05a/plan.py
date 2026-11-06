"""회귀 gate 후의 유한 real-path 계획. source A/B 및 공유 client identity를 고정한다."""
import hashlib,json,pathlib,sys
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b05a';W=pathlib.Path('/tmp/money-note-t66f-b05a-20261026');N=int(sys.argv[1]);assert N in [1000,5000]
engines={'A':'7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c','B':'f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3'}
order=[('A',False,0),('B',False,0),('B',True,0),('A',True,0),('B',False,1),('A',False,1),('A',True,1),('B',True,1)] if N==1000 else [('B',True,0),('A',True,0),('A',False,0),('B',False,0)]
client_paths=sorted((W/'candidate/mobile/lib').rglob('*.dart'))+[W/'candidate/mobile/assets/segmented/isolated-release-artifacts.json'];inventory={p.relative_to(W/'candidate').as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in client_paths};client_sha=hashlib.sha256(json.dumps(inventory,sort_keys=True,separators=(',',':')).encode()).hexdigest()
runs=[]
for ordinal,(v,on,rep) in enumerate(order):
 name=f'n{N}-{ordinal}-{v}-'+('on' if on else 'off')
 runs.append({'id':name,'ordinal':ordinal,'N':N,'variant':v,'on':on,'rep':rep,'engine_sha':engines[v],'backend_tree':str(W/('baseline' if v=='A' else 'candidate')),'fixture':str(W/f'fixtures-n{N}'),'out':str(W/'raw'/name),'client_source_digest':client_sha,'backend_observation_sha256':hashlib.sha256((W/('baseline' if v=='A' else 'candidate')/'backend/isolated_sync/observation.py').read_bytes()).hexdigest()})
plan={'N':N,'scratch':str(W),'server':str(E/'server.py'),'runs':runs,'client_component_inventory':inventory,'client_source_digest':client_sha,'boundary':'실제 AppState segmented-internal publication 반환 및 bounded E4 accepted read. UI/Offline-ready 아님','phase_boundaries':{'E2':'초기 recovery 포함 envelope: 시작→terminal release 완료 뒤 첫 E3 metadata SQL. 정확한 acquire API 단독 시간은 아님','E1':'native SQL API 누적; E2 envelope에 포함, stage별 분리는 ON만 가능','E3':'첫 E3 metadata SQL→AppState 반환; 원래 native transaction/readback 시간 별도','E4':'bounded accepted read. 전체 semantic oracle는 primary timing 밖'},'lease':900,'attempts':3,'max_N':5000,'N1k_planned':8,'N5k_planned':4,'N10k_50k_100k_cold':0}
p=E/f'plan-n{N}.json';assert not p.exists();p.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'N':N,'planned_runs':len(runs),'client_source_digest':client_sha}))
