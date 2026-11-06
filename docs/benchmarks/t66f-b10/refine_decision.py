"""혼합 요구의 원 인용을 보존하고 미승인 이관 결정안을 구체화한다."""
from pathlib import Path
import json
E=Path('/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b10')
def read(n):return json.loads((E/n).read_text())
def write(n,d):(E/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
M=read('requirements-evidence-matrix.json')
P=M['authority']['path'];lines=Path('/home/hjkerman/codex/money-note',P).read_text().splitlines()
for r in M['rows']:
 i=r['id']
 if i in ['S31','S33','I23','P10','N31','N32']:
  r['additional_authoritative_locations']=[r['authoritative_location']]
  text='## '+i[1:]+'.' if i.startswith('S') else '| '+i+' ' if i.startswith('I') else i[1:]+'. ' if i.startswith('P') else '| '+i[1:]+' |'
  after=0 if i.startswith(('S','I')) else 779 if i.startswith('P') else 736
  line=next(k for k,l in enumerate(lines,1) if k>after and l.startswith(text))
  clause='§'+i[1:] if i.startswith('S') else '§36 '+i if i.startswith('I') else '§38 증명 '+i[1:] if i.startswith('P') else '§37 사례 '+i[1:]
  r['authoritative_location']={'path':P,'section':clause,'line':line};r['requirement_id']=clause
 if i=='COLD-100K-INSTRUMENTED':
  r['source_identity']={'historical_stage':'IC01/P02 → P03','base_commit':'ebcbd54d90eeee194a04b9eea6367f446ee2fd28','canonical_IR07_payload_applies':False,'file_hash_manifest':'docs/benchmarks/t66f-b03-ic01-p03/evidence/ic01-p02-source-review.json'}
  r['execution_environment']='역사 P03 CPython3.12.3/Flutter3.47.4 HOST, IC01/P02 계측; 최종 IR07와 동일 소스라고 주장하지 않음'
write('requirements-evidence-matrix.json',M)
D=read('closure-decision.json')
D['baseline_availability_check']={'B02_documented_scratch':'/tmp/mn-b02-independent-100000-z6ux9y53','exists':False,'B02_evidence_directory_contains_SQLite_DB':False,'other_complete_100k_baseline_certified':False,'scope_ko':'명시된 scratch와 B02 증거 디렉터리만 확인; 전체 filesystem을 검색하거나 다른 자료 부재를 단정하지 않음. 사용 가능한 원 B03 100k accepted DB가 있다고 가정하지 않음'}
D['proposed_decision_not_adopted']['transfer_proposal']={'status':'DRAFT — NOT AUTHORIZED','authority_person':None,'authority_requirement_ko':'규범 변경 승인 권한의 근거와 실제 승인자를 별도로 명시하고 독립 검토를 기록해야 함; B10 감사자에게 waiver 권한 없음','clauses_to_amend':['§35 다섯 N의 completion 시점','§36 I25 및 §38.7·12의 해당 비용 증명 completion 시점','§34의 F/performance exit와 명시 예외의 관계'],'obligations_to_transfer_ko':['원 B03 기준으로 남은 N=100k no-change/card/cash 정상 instrumented cost/I25와 per-layer bytes·rows/HTTP/RTT/memory/분포','현재 미완결한 source/fixture 일치 rows-read 및 segmented framing/headers/RTT/full gzip 비교의 누락 열'],'proposed_target':'T6.9 별도 큰 규모 검증','conditions_ko':['다섯 규모 의무를 삭제하거나 추정으로 대체하지 않고 실행 시점만 옮김','승인 문구가 완성 상태를 허용하기 전까지 현재 Phase B INCONCLUSIVE/전체 F 종결 차단 유지','새로 선택된 source·runtime·binary는 원 B03와 identity를 분리하고 변경 영향 gate를 재검증','원 B01–B09 보고서·P03 실패·IR07 범위·B04 부분 범위를 소급 수정하지 않음','B05/B08 미채택·캠페인 종료, Android durability/R1/activation/production gate는 이관안의 면제 대상에서 제외','후속 evidence의 owner와 승인 권한은 실재 정책/명시 결정으로 지정되기 전 null 유지'],'source_reference':{'payload':'8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8','engine':'7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c'},'does_not_authorize_any_execution':True}
write('closure-decision.json',D)
print(json.dumps({'exact_citations_refined':6,'baseline_not_assumed':True,'proposed_exception':'NOT AUTHORIZED'}))
