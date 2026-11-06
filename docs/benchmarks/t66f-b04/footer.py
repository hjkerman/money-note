"""검증된 B04 수치로 요청 footer를 생성한다."""
import json,pathlib
E=pathlib.Path('/home/hjkerman/codex/money-note/docs/benchmarks/t66f-b04')
def read(n):return json.loads((E/n).read_text())
m=read('run-manifest.json');d=read('fullscale-decision.json');t=read('timing-summary.json');c=read('cleanup.json');scales=sorted({r['N'] for r in m['runs'] if r['role']=='binding-lower-N' and r['valid_completed']});s='/'.join(str(n) for n in scales)
normal=[r for r in t if r['workload']!='cold'];cold=[r for r in t if r['workload']=='cold']
def interval(rows,key):return f"{min(r[key]['median'] for r in rows):.3f}–{max(r[key]['median'] for r in rows):.3f}배" if rows else '미측정'
text=f'''```text
T6.6F-B04 PHASE B MEASUREMENT FEASIBILITY:
{d['B04_verdict']}

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07

B03 FROZEN PAYLOAD SHA-256:
8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8

MEASURED SOURCE IDENTITY:
VERIFIED

SUPPORTED MEASUREMENT RUNTIME:
CPython 3.12.3 / backend SQLite 3.45.1 / client SQLite 3.53.4 / Flutter 3.47.4 / Dart 3.13.3

BINDING H:
숫자 미지정; 실험 current ledger105 + 참조/control/policy, 초기 hot87364B/control3178B

BINDING D:
숫자 미지정; 이번 no-change0 / one-card1 / one-cash1

BINDING FIVE N POINTS:
1000 / 5000 / 10000 / 50000 / 100000

EXECUTED N POINTS:
{s}

UNEXECUTED N POINTS:
100000 — 이번 task 명시 제외, 별도 승인 필요

NO-CHANGE MEASUREMENTS:
{len(scales)}/5 지점; 각3회 ON + 3회 OFF

ONE-CARD DELTA MEASUREMENTS:
{len(scales)}/5 지점; 각3회 ON + 3회 OFF

ONE-CASH DELTA MEASUREMENTS:
{len(scales)}/5 지점; 각3회 ON + 3회 OFF

COLD BASELINE MEASUREMENTS:
{len(scales)*2}/{len(scales)*2} 하위 규모 계획; client cold, backend bootstrap은 별도 ON

VALID COMPLETED MEASUREMENTS:
{m['valid_controlled_completed_runs']}개 통제 측정 + {m['diagnostic_completed_runs']}개 기타 publication 진단 + {len(m['stage_diagnostic_files'])}개 stage 진단

INCOMPLETE/EXPIRED MEASUREMENTS:
{m['incomplete_workload_runs']}개 미완료; 완료된50k cold2개에서 각각1회 lease 만료 후 갱신; 도구 오류 별도

INSTRUMENTATION ON/OFF PAIRS:
{m['valid_controlled_pairs']}쌍 통제 비교 + {m['diagnostic_publication_pairs']}쌍 publication 진단 + {len(m['stage_diagnostic_files'])//2}쌍 stage 진단

END-TO-END PERTURBATION:
정상 쌍별 비율 중앙값 {interval(normal,'ratio')}; cold {interval(cold,'ratio')}; n1/n3 한계, 실제 UI 완료 미측정

BACKEND PERTURBATION:
정상 handler 쌍별 비율 중앙값 {interval(normal,'backend_ratio')}; generation ON만 측정

E1/E2 PERTURBATION:
SQL API 정상 중앙 비율 {interval(normal,'E1_SQL_ratio')}; 50k E2 API 별도 실측, 순수 parser CPU 아님

E3/E4 PERTURBATION:
transaction 정상 중앙 비율 {interval(normal,'E3_transaction_ratio')}, E4 {interval(normal,'E4_read_ratio')}; 50k verify/prepare 별도

LOGICAL HASH INPUT BYTES:
실제 sink 입력과 stage별 exact 합계 보존; OFF는 null

PRIMARY VALIDATION INPUT BYTES:
실제 submitted/completed/failed span 분리; 구조 방문 수와 별도

SQL LOGICAL WRITE BYTES:
NEW TEXT UTF8/BLOB; objects committed BLOB=독립 DB body 증가량

ATTEMPTED/EFFECTIVE/COMMITTED:
세 계수·rollback 별도 보존; scalar/NULL 개수와 물리 I/O 구분

COLD VERSUS STEADY STATE:
SEPARATED

E3 I25 MEASURED COVERAGE:
{s} 정상 경로 full-N counter0; source·stage 증거 보존

LOWER-N BINDING COST COMPLIANCE:
PARTIAL — 실제 논리 비용 근거 확보, 전체 §35 계측 열은 일부 미완료

FULL FIVE-POINT H/D/N COST GRID:
PARTIAL

LARGE-N E3 I25:
PARTIAL — 100k 미검증

RUNTIME PERTURBATION:
{d['perturbation_short']}

N=100K FULL-SCALE FEASIBILITY:
{d['decision']}

N=100K FULL COLD RUNS IN B04:
0

HISTORICAL P03 N=100K:
FAILED — 397146 / 400532

MEASUREMENT ENVIRONMENT:
LIMITATIONS RECORDED

ON/OFF PRODUCT EQUIVALENCE:
PASS — exact Target/상대 sequence/DB bytes/E4 및 최종 raw graph 일치

SOURCE-SHA GUARDS:
PASS

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED

T6.6F PHASE B:
INCONCLUSIVE

ANDROID MEMORY SAFETY:
NOT VERIFIED

ANDROID VFS/I-O:
NOT VERIFIED

HARDWARE POWER LOSS:
NOT VERIFIED

R1 LARGE RESTORE:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B04:
NO

PRODUCT SOURCE MODIFIED:
NO

BINDING PROTOCOL MODIFIED:
NO

COMMIT:
NONE

PUSH:
NOT PERFORMED

BENCHMARK MANIFEST:
docs/benchmarks/t66f-b04/run-manifest.json

B04 REPORT:
docs/t66f-b04-phase-b-measurement-feasibility.md

TEMPORARY ARTIFACT CLEANUP:
{c['footer_ko']}

FINAL VERDICT:
{d['B04_verdict']}

NEXT ACTION:
{d['next_action_ko']}
```'''
(E/'footer.txt').write_text(text+'\n')
