"""실측 JSON에 연결된 한국어 B08 보고서."""
import pathlib,json,statistics
R=pathlib.Path('/home/hjkerman/codex/money-note');E=R/'docs/benchmarks/t66f-b08'
def get(n):return json.loads((E/n).read_text())
p=get('packet-comparison.json');a=p['A'];b=p['B'];ids=get('source-identities.json');freeze=get('candidate-freeze.json');budget=get('execution-budget.json')
def table(h,vs):return '\n'.join(['|'+'|'.join(h)+'|','|'+'|'.join(['---']*len(h))+'|']+['|'+'|'.join(str(v)for v in row)+'|'for row in vs])
text='''# T6.6F-B08 — 불변 기대 revision 계약의 제한적 재사용

**PASS — SAFE REUSE AND LOCAL BENEFIT VERIFIED.** 원 B03의 기대 계약 컴파일만 최대 1항목의 불변 cache로 재사용한 실험 후보를 검증했다. 객체 요청 13개씩의 handler 합은 3.180023143→2.841368689초로 10.6494% 줄었고 A→B/B→A 두 block에서 같은 방향이었다. 실제 DB inspection은 양쪽 46회로 같고 기대 계약 컴파일은 46→1회였다. **실제 Flutter cold 전체 이득은 NOT VERIFIED**다.

기존 release artifact exact 비교 1건은 새 engine이 미입장 상태이므로 **FAIL 원문을 보존**했다. 이 gate나 expected hash를 바꾸지 않았고 전체 backend PASS를 주장하지 않는다. 판정은 기대 계약 재사용의 기능 안전성과 제한된 backend 국소 이득에 한정한다. 후보는 **EXPERIMENTAL / AWAITING QUALIFICATION**이며 배포용 release가 아니다.

[실행 manifest](benchmarks/t66f-b08/run-manifest.json), [cache 안전성](benchmarks/t66f-b08/cache-safety-verification.json), [packet 비교](benchmarks/t66f-b08/packet-comparison.json), [다음 결정](benchmarks/t66f-b08/next-action-decision.json)에 원자료를 연결했다.

## 기준 소스와 실험 후보

시작/종료 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`이다. live dirty tree의 B05 `_lookup` 최적화를 기준으로 사용하지 않았다. 원 B03 archive SHA `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5`를 검증한 뒤 899 source 파일의 bytes/mode와 payload digest를 대조했다. 이후 별도 candidate를 만들었다.

'''
text+=table(['신원 층','기준 A','후보 B'],[
['source payload SHA-256','`8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`','`'+freeze['payload_sha256']+'`'],
['실제 engine SHA','`'+ids['A']['engine_sha256']+'`','`'+ids['B']['engine_sha256']+'`'],
['source 파일 수',899,900],
['checked-in release engine','원 7ad…','원 7ad… 보존 — 새 engine 미입장']])
text+='''

engine 입력 98개 중 차이는 `backend/app/db_migrations.py` 하나다. 새 source 파일은 전용 `backend/tests/test_expected_revision_contract_reuse.py`다. tracked 삭제나 mode 전이는 없다. 기존 `_lookup`/canonical/관측/금융 계산 구현과 B03 counters는 원 B03 bytes다. payload SHA와 engine SHA를 혼용하지 않았다. [신원 계산](benchmarks/t66f-b08/source-identities.json), [정확한 diff](benchmarks/t66f-b08/optimization.patch), [변경 요약](benchmarks/t66f-b08/source-diff-summary.json).

원 IR07 독립 정확성은 원 B03 source에 대해 CLOSED다. 새 helper와 B08 실험 timer를 IR07 감사 완료라고 부르지 않는다. 원 동결 archive·B05/B05-A 후보와 기존 live 미커밋 소스는 수정하지 않았다.

## 정확한 재사용 경계와 key 증명

원 호출자는 일반 startup/migration, authoritative-state 검증, Snapshot 복구, 격리 capture/finalization/retention이다. D3 객체 요청은 `Adapter.credential`→fresh connect, `TransferRepository.acquire`→repository connect, 최종 `Adapter.terminal`→repository connect의 세 경로에서 검증한다. connect는 retention version의 `retention_schema.validate_schema`→`finalization.validate_schema`→`app.db_migrations._validate_current_schema`→`_validate_revision_triggers`를 호출한다. 첫 manifest는 writer lock 뒤 추가 schema 검사도 수행한다. 이 호출 수와 transaction/PRAGMA를 바꾸지 않았다.

기존 `_validate_revision_triggers`는 매 호출마다 전체 기대 schema의 `_statements(schema)`를 순회해 `CREATE TRIGGER IF NOT EXISTS revision_` 문을 고르고 `_revision_trigger_contract`로 기대 tuple을 만든다. 그 뒤 현재 DB의 trigger SQL을 읽어 실제 계약을 파싱하고, 이름/대상 table/본문 token을 비교하며 authoritative revision 상태의 단일 행·integer·비음수 조건을 확인한다.

|데이터|의존성과 소유|
|---|---|
|기대 계약 sequence|전달된 정확한 schema SQL과 고정 parser 구현의 순수 결과; DB를 읽지 않음|
|기대 이름/대상 table 집합|기대 sequence에서 파생|
|실제 trigger rows/실제 파싱 값|현재 호출의 conn에서 매번 읽음; cache에 넣지 않음|
|revision state|현재 conn의 실제 행과 typeof를 매번 검사|
|version/경로/connection|기대 컴파일 입력이 아니며 key로 사용하지 않음|

**key는 schema SQL 전체의 정확한 str 값**이다. whitespace만 달라도 다시 컴파일한다. 동일 경로·동일 `user_version`에서도 다른 SQL은 다른 key다. 지원 호출자는 신뢰된 `app.db.SCHEMA`/격리 `capture_schema()` 문자열을 넘긴다. `_statements`/parser 코드와 SQLite/re 모듈은 해당 process의 고정 구현이며 hot swap하는 제품 API는 없다. 코드/runtime 교체는 process 재시작과 새 engine identity 전이에 해당한다. DB의 mutable schema cookie나 validation PASS를 key/값으로 삼지 않았다.

새 `_expected_revision_contract(schema)`는 기존 `lru_cache(maxsize=1)`만 사용한다. 반환값은 `(expected_tuple, expected_names_frozenset, revision_tables_frozenset)`이고 각 계약은 문자열·불변 token tuple 또는 기존 invalid-parse sentinel `None`이다. conn/cursor/transaction/가변 dict/list/set을 보관하지 않는다. 전용 검사에서 반환 구조를 재귀 확인하고 변경 시도를 거부함을 검증했다.

현재 DB 조회 이후의 원 검사 block은 기대 이름/집합 구성 두 줄을 이동한 부분 외에 **bytes 그대로**다. SQL·거부 메시지·actual 파싱·상태 검사 순서는 유지한다. 기대 순서도 list→tuple 변환으로 보존한다. 불완전 schema의 컴파일 예외는 cache에 저장되지 않는다. `None`을 포함한 불변 기대값이 cache에 있어도 매번 actual DB를 읽고 원 오류를 낸다.

동시 호출에서는 stdlib LRU의 coherent 단일 retained entry를 사용한다. 다른 key의 miss가 동시에 발생하면 중복 계산은 가능하지만 각 호출은 자신의 key로 계산한 불변 결과를 받는다. 공유 "마지막 값"을 따로 읽지 않는다. cache 밖의 호출-local 결과와 retained capacity 1을 구분한다. 8 thread의 다른 schema/DB 각각 16회 검증에서도 오염 없이 `currsize<=1`이었다. 별도 lock framework나 connection pooling은 없다.

## 기능 검사와 남은 artifact gate

전용 **22 PASS**는 literal token 기대값과 원 B03 함수의 동일 AST를 복사한 독립 oracle를 함께 사용한다. optimized 함수의 출력만으로 기대값을 만들지 않았다. 캐시를 채운 뒤 trigger 삭제·본문 변경·추가 trigger, missing/negative/REAL/TEXT/multiple revision state, 별도 DB의 손상, 같은 version의 기대 SQL 교체, malformed/incomplete SQL, 실제 SELECT 순서와 동시 호출을 검사했다. cache hit 뒤에도 원 SQL 두 개가 호출됨을 직접 기록했다. [최종 전용 JUnit](benchmarks/t66f-b08/focused-final.xml), [전용 테스트 source](benchmarks/t66f-b08/test_expected_revision_contract_reuse.py), [oracle AST 대조](benchmarks/t66f-b08/oracle-portability.json).

영향 범위는 startup/versioned migrations, migration characterization, offline revision, authoritative state, Snapshot, 격리 capture/finalization/observation/transfer/prefix/retention/ownership 및 B03 core였다. 실제 DB 검사 본문과 상위 caller가 unchanged이고 전용 negative/concurrency와 이 caller 계열을 직접 검사하므로 전체 backend suite를 추가 실행하지 않았다. [사전 검사 계획](benchmarks/t66f-b08/regression-plan.json).

|검사 단계|실제 결과와 해석|
|---|---|
|최초 전용 검사|22 PASS|
|영향 검사 최초 수집|과거 resolver gzip 누락으로 collection ERROR 1; 실행 전 중단|
|Git gzip 복원 후 영향 검사|pytest summary: 694 PASS, 348 FAIL(13 fixture 누락 관련 parent/다수 subfailure와 artifact 비교 1건 포함), 104 subtests PASS|
|추가 Git SQL/JSON fixture 복원|실패한 13 node만 재실행: 13 PASS, 338 subtests PASS|
|최종 전용 검사|oracle의 scratch 의존성을 제거하고 원 AST 동일성을 확인한 뒤 22 PASS|
|남은 exact artifact 비교|1 FAIL — 새 engine와 바꾸지 않은 원 release의 exact identity 차이|
|AGENTS frontend build|원 Git frontend의 누락 cross-tree JSON fixture를 복원한 뒤 `npm run build` PASS; 성능 campaign 밖의 변경 없는 frontend QA|

앞선 fixture 복원에서 source-only overlay 밖 테스트 의존성을 모두 확인하지 못했다. 원 실패 로그/JUnit을 보존했고 cache 제품 코드를 바꾸거나 실패 기대값을 수정하지 않았다. 변경 없는 Git baseline blob의 SHA/원 경로를 확인해 필요한 fixture만 복원했다. source-only payload와 unchanged baseline test context를 구분한다. 위 단계의 PASS/subtests를 합산해 중복 없는 전체 suite 결과로 바꾸지 않는다. [처음 영향 결과](benchmarks/t66f-b08/affected2.xml), [fixture 복구 결과](benchmarks/t66f-b08/fixture-recovery.xml), [추가 test context](benchmarks/t66f-b08/additional-test-context.json), [frontend build](benchmarks/t66f-b08/frontend-build2.json).

남은 test는 `test_release_artifact_hashes_exact_bytes_and_target`다. 실제 artifact를 따로 계산해 차이가 **financial_engine 한 항목뿐**임을 확인했다. 원 A는 기존 artifact와 일치하고 B는 새 source SHA 때문에 다르다. 원 exact guard의 거부를 성공으로 바꿔 부르지 않는다. Flutter/배포 전에 별도 admission·artifact 전이 승인이 필요하다. B08은 release JSON, allowlist, source-SHA 기대값을 수정하지 않았다. [artifact gate 분리](benchmarks/t66f-b08/artifact-gate-analysis.json).

## 보존 fixture와 공정한 초기화

원 N1k template SHA는 `aba6a044985f9f148e770fcd484e554373b12cc20f1d48ee441814ed8b7318d2`, 압축 SHA는 `e9d805a03399bd4f940e7af2416dc13f7e7dd962525e986db1810980c897550d`다. 원 fixture를 보존했다. N=ledger 1,000행, H=current ledger 105·기타 authority 35, hot 87,364B/control 3,178B, D는 해당 없음(null)이다. source 변경 때문에 engine별 hot identity는 달라지지만 금융 값/serialization 규칙은 그대로다.

두 engine의 backend 준비 상태를 맞추려고 원 template의 금융/구조 데이터를 그대로 유지한 **파생 common template**에 새 engine view만 지원 repository API로 준비했다. 이를 원 template와 byte-identical이라고 부르지 않는다. 준비 시 control exported_at만 역사 fixture와 맞췄고 실제 ASGI는 정상 UTC와 새 900초 lease/기존 3 attempts를 사용했다. 실제 두 source 모두 같은 파생 SHA의 common template에서 독립 SQLite backup으로 초기화했다. [정확한 두 fixture 층과 Target](benchmarks/t66f-b08/prepared-fixture.json).

준비는 repository create/release 2작업이며 성능 비교용 B03 ON sample은 아니다. 이 두 작업도 watchdog과 보수적 32작업 예산에 포함했다. raw/source/실제 금융 SQL 저장 타입·값은 원 template, common template, 두 사후 DB의 네 상태에서 모두 같았다. Target 차이는 `context.financial_engine`, `hot_ref.hash`, `sync_root` 세 경로이며 raw/index/control refs와 graph 4,132개·2,749,721B는 같다. 금융 hot `state`도 같았다. [사후 독립 대조](benchmarks/t66f-b08/post-verification.json).

## 32작업·120초 제한 실행

유일 campaign은 **실제 ASGI 30요청(A15/B15) + 준비 repository 2작업 = 보수적 32작업**이었다. 전용 preflight HTTP 요청은 없었다. 각각 manifest 1, 객체 요청 13, release 1이며 모든 attempt를 요청 전에 journal에 남겼다. 객체 packet은 B07의 hot/control/raw/index root, 큰 raw leaf, 64 index leaves, 64 index nodes의 같은 일곱 유형이다. 한 packet은 한 객체와 같지 않다. 처음 여섯 slot은 2반복, 마지막 slot은 1반복이다.

순서는 A manifest→B manifest→A1(7)→B1(7)→B2(6)→A2(6)→B release→A release다. source별 process/DB/TestClient를 유지했고 실제 native WorkerBudget·D3 handler를 사용했다. socket/TLS나 Flutter는 실행하지 않았다. B03 ON과 같은 B08 thin timer를 사용했다. pure parser 64쌍/engine의 유한 overhead 진단도 watchdog 안에 넣었고 D3 요청으로 세지 않았다.

parent fail-stop watchdog은 119초에 소유 process group 전체를 SIGKILL하도록 사전 검증했다. source 준비·두 process startup·요청·종료·backup·overhead 진단을 포함해 **10.835783초**였고 watchdog 발동·retry·미완료·scope error는 0이었다. [예산 기록](benchmarks/t66f-b08/execution-budget.json), [사전 계획](benchmarks/t66f-b08/measurement-plan.json), [원 요청 순서](benchmarks/t66f-b08/requests.jsonl), [원 A timing](benchmarks/t66f-b08/packets-A.jsonl), [원 B timing](benchmarks/t66f-b08/packets-B.jsonl).

## 작업 감소와 국소 시간

다음 count는 비교 대상인 실제 ASGI 15요청씩에 한정한다. 준비 repository 2작업은 혼합하지 않았다. 첫 manifest의 lock 뒤 추가 검사를 포함해 schema/actual query가 46회다.

'''
text+=table(['실제 ASGI count','기준 A','후보 B'],[
['요청',15,15],['fresh connect',a['connections'],b['connections']],['schema validation',46,46],['actual DB trigger inspection',46,46],['실제 trigger 계약 파싱',3772,3772],['기대 계약 컴파일',46,1],['기대 계약 parser 호출',1518,33],['cache hits/misses','해당 없음','45 / 1'],['object 단계 cache miss','cache 없음',0]])
text+='''

컴파일과 parser 호출은 97.8261% 줄었다. 실제 DB query나 actual trigger parse는 그대로다. 동일 유형의 실제 요청들에 대해 **B03 counter map 전체가 정확히 같았다**. 실제 필요한 C1/hash/SQL work가 빠진 것을 속도 이득으로 세지 않았다. 이 cache 대상은 모니터링된 C1/SQL 작업을 제거하는 변경이 아니므로 이 범위의 counter equality를 확인했다.

아래는 동일 유형 객체 요청 13개씩의 누적·분포다. manifest/release는 raw에 따로 남겼고 서로 중첩하는 행을 더하지 않는다. Stopwatch 단위는 ns지만 오차가 없다는 뜻은 아니다.

'''
forTable=[]
for key,label in [('object_handler','handler'),('object_connect','connect 포함'),('object_schema','schema 포함'),('object_revision_validation','revision validator 포함')]:
 aa=a[key];bb=b[key];forTable.append([label,f"{aa['total_s']:.9f}",f"{bb['total_s']:.9f}",f"{aa['median_s']*1000:.3f} / {bb['median_s']*1000:.3f}",f"{aa['min_s']*1000:.3f}–{aa['max_s']*1000:.3f} / {bb['min_s']*1000:.3f}–{bb['max_s']*1000:.3f}"])
text+=table(['객체 요청 경계','A 합 초','B 합 초','A/B 중앙값 ms','A/B 관측 범위 ms'],forTable)
text+='''

handler은 0.338654454초(10.6494%), connect는 0.333541381초, schema는 0.333023594초, revision validator는 0.333830132초 줄었다. 이 값들은 포함 관계이므로 합산하지 않는다. handler 감소 중 connect 밖 차이는 0.005113073초였다. 감소가 대상 경계에 집중된 관측이지만 다른 변동의 인과 배제를 완성한 것은 아니다.

'''
text+=table(['matched block','순서','A 초','B 초','관측 감소율'],[[x['rep'],x['order'],f"{x['A_s']:.9f}",f"{x['B_s']:.9f}",f"{x['reduction_pct']:.4f}%"]for x in p['paired_blocks']])
text+='''

baseline 기대 parser 누적은 객체 단계 0.259607955초이고 후보는 0회다. 후보의 warm cache gate는 39회·0.000096324초였다. gate는 native cache lookup/return과 clock 읽기를 포함하고 caller의 tuple unpack 및 wrapper 후처리는 제외하므로 순수 cache CPU라고 부르지 않는다. 첫 schema 전이 시 필수 compile miss의 gate는 0.008751977초였다. 정상 process 초기화의 일반 SCHEMA entry 뒤 격리 schema로 key가 바뀐 한 번이며 인위적으로 cache를 비우지 않았다.

baseline은 `_statements` 순회와 기대 집합 생성도 반복하지만 parser 개별 timer에는 그 전체가 들어가지 않는다. 후보 gate에는 lookup/최초 컴파일을 포함한다. 따라서 두 열을 완전히 같은 전체 compiler timer라고 주장하지 않는다. revision validator 감소 중 parser 관련 예산 밖 0.074318501초에는 제거된 statement 순회/집합 구성, actual parse 변동과 나머지 bookkeeping이 섞인다. 별도 exclusive CPU라고 단정하지 않는다. SQL timing은 계측 교란을 줄이려고 수집하지 않았고 null로 남겼다.

### 계측 교란과 확신의 한계

같은 B03 ON/thin wrapper 정책을 적용했지만 제거된 parser 호출에 붙은 B08 wrapper도 사라진다. 짧은 pure trigger의 64쌍 진단에서 wrapper 중앙 차이는 A 3,198ns/B 3,269.5ns였다. 이를 없어진 객체 단계 1,287회에 단순 적용하면 약 4.21ms로 338.65ms handler 차이보다 작지만, 긴 schema에 대한 엄격한 상한이나 통계 보정값은 아니다. raw timing을 보정해 새 결과로 만들지 않았다.

source당 process 1개·일곱 slot의 작은 표본이다. CPU 주파수/OS cache/실행 순서를 완전히 통제하지 못했고 신뢰구간·통계적 유의성을 주장하지 않는다. 두 block의 일관된 방향, 실제 compile 46→1과 actual inspection 유지가 **대상 작업 감소와 국소 이득**을 지지한다. socket·E2/E1·E3/E4·UI 완료는 측정하지 않았으므로 전체 cold 이득과 독립 실기기 자격은 남아 있다.

## 규모 관련성·채택 결정

기존 N5k baseline ON raw의 object 요청 수 332, 요청당 connect 3회를 사용했다. 5,000행이나 reachable 객체 20,148개를 곱하지 않았다. 새로운 객체 단계 parser 관련 예산에서 warm gate 비용을 뺀 값은 packet당 약 19.962ms다. 이를332회로 환산하면 6.627528초이며 최초 필수 compile gate 8.752ms를 한 번 더 보수적으로 남겨두면 **약 6.618776초**다. 기존 cold149.744–152.688초의 약4.33–4.42%에 해당하는 조건부 작업 예산이다.

국소 handler 차이 자체를 packet 수로 환산하고 같은 최초 비용을 남기는 다른 모델은 약8.640초다. 이 두 값은 신뢰/보장 범위가 아니라 다른 포함 경계의 진단 모델이다. 같은 schema·runtime·직렬 임계 경로 및 다른 비용 고정을 가정하며 실제5k/Flutter에서 검증하지 않았다. 기존 B07의6.572초 예측을 실현된 전체 speedup으로 바꾸지 않았다. [원 raw 참조와 모델](benchmarks/t66f-b08/packet-comparison.json)의 projection에 가정을 기록했다.

**결정은 실험 후보 유지, 별도 실제 경로 자격 검증 권고**다. 국소 절감이 실제 요청에서도 양 순서로 관측되어 N1k 실제 Flutter 비교를 할 근거가 있다. 다음 승인 범위는 engine `5861d6d2…`를 원 `7ad114bc…`와 함께 정확히 인정하는 `mobile/lib/src/segmented/protocol.dart`, 직접 연동 `docs/specimens/t66d3b-release-artifacts.json`과 `mobile/assets/segmented/isolated-release-artifacts.json`, 그 전이에만 의존함이 입증된 exact-hash 검사로 좁혀야 한다. B08에서 이 파일을 바꾸지 않았다. 기존 engine 삭제·wildcard·검사 완화는 없다.

새 engine을 live의 B05 source에 섞으면 다른 source identity가 되므로 보존 B08 archive 자체를 사용해야 한다. 원 IR07 감사와 새 cache 구현 검증을 구분하고, 더 넓은 채택 전 diff 수준의 기대값/실제값 분리·오류·동시성·bounded lifetime와 measurement provenance 검토를 재사용 가능한 증거와 함께 제공한다. 전체 B03 lifecycle 재감사나 50k/100k 재실행을 자동 요구/실행하지 않는다.

100k instrumented cold는 NO-GO다. 다섯 N grid/large-N I25는 미완료이고 Phase B는 INCONCLUSIVE다. B01/B02 및 원 B03는 CLOSED, B04 bounded PASS, B05 experimental only, B05-A/B05-B PASS, B06 PASS, B07 material attribution PASS를 유지한다. Real-Device Gate는 DEFERRED, Android memory/VFS/power는 NOT VERIFIED, R1 activation은 CLOSED, production은 NOT AUTHORIZED다.

## 후보 보존과 정리

새 source-only archive는 [experimental-source.tar.gz](benchmarks/t66f-b08/experimental-source.tar.gz)다. source900파일을 다시 복원해 bytes/mode/payload digest를 검증했다. 원 Git baseline 위에 source overlay를 적용하는 절차와 테스트 context는 [HANDOFF](benchmarks/t66f-b08/HANDOFF.md)에 있다. [freeze 기록](benchmarks/t66f-b08/candidate-freeze.json)에 archive SHA와 source/engine 층을 구분했다. 기존 B03/B05/B05-A archive를 수정하지 않았다.

파생 common fixture와 두 고유 post-run DB는 SQLite backup API/압축 roundtrip 검증 뒤 보존했다. 기존19?개 자료를 복사해 새 측정이라 부르지 않았다. 재현에 필요한 source/원 fixture hashes, raw logs/JUnit, packet timing/counters, actual DB digest와 [보존 DB manifest](benchmarks/t66f-b08/retained-databases.json)를 남겼다. [최종 증거 manifest](benchmarks/t66f-b08/evidence-manifest.json)를 기준으로 raw 출처를 추적할 수 있다.

기존 visible 파일 6,199개의 bytes/mode/크기와 staged path/mode/blob/stage, 원 index bytes를 보존했다. index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`로 같다. live product·B03 counters·engine allowlist·release·binding protocol·source lock 변경, reset/stash/checkout/restage/commit/push는 없다. [시작](benchmarks/t66f-b08/preservation-before.json)과 [종료](benchmarks/t66f-b08/preservation-after.json) 대조를 보존했다.

B08 단일 scratch의 source A/B/재구성, 테스트 DB·output, QA build와 task-owned symlink만 소유/비활성을 확인해 정리했다. 외부 node_modules package symlink의 대상은 삭제하지 않는다. 원 fixture·historical DB/WAL/cache에는 손대지 않았다. [정리 기록](benchmarks/t66f-b08/cleanup.json)에 실제 파일 수·할당량·보존 항목을 기록한다.

다음 행동: **별도 좁은 engine 입장·직접 artifact 승인 범위에서 B08 후보와 원 B03의 N=1k 실제 Flutter cold A/B를 수행해 전체 이득을 검증한다.**

## 최종 상태

'''
text=text.replace('기존19?개 자료를 복사해 새 측정이라 부르지 않았다.','기존 자료를 복사해 새 측정이라 부르지 않았다.')
footer=f'''T6.6F-B08 EXPECTED-REVISION CONTRACT REUSE:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

ORIGINAL B03 SOURCE:
PRESERVED

ORIGINAL B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL SOURCE ONLY

BASELINE ENGINE SHA:
7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c

B08 CANDIDATE SOURCE IDENTITY:
PAYLOAD {freeze['payload_sha256']}
ENGINE {ids['B']['engine_sha256']}

AUTHORIZED OPTIMIZATION:
ONE-ENTRY IMMUTABLE EXPECTED-CONTRACT REUSE

EXACT CACHE KEY:
전달된 기대 schema SQL 전체의 정확한 str 값

CACHE CAPACITY:
1

EXPECTED CONTRACT IMMUTABILITY:
PASS

SCHEMA KEY TRANSITION:
PASS

ACTUAL DATABASE INSPECTION:
PRESERVED

INVALID SCHEMA REJECTION:
PASS

DATABASE ISOLATION:
PASS

MIGRATION BEHAVIOR:
PASS

CONCURRENCY SAFETY:
PASS

AFFECTED BACKEND TESTS:
전용22 PASS; 영향 pytest694 PASS 및 fixture 복구13 PASS;
기존 release exact identity1 FAIL 분리·보존, 전체 backend PASS 주장 없음

BASELINE MEASURED PACKETS:
15

OPTIMIZED MEASURED PACKETS:
15

TOTAL MEASURED PACKETS:
30 actual ASGI / 32 MAX; 준비 repository2까지 보수적 합계32

MEASUREMENT WALL TIME:
10.835783 s / 120 s MAX

BASELINE CONTRACT COMPILATIONS:
46 — 실제 ASGI sample

OPTIMIZED CONTRACT COMPILATIONS:
1 — 실제 ASGI sample

CACHE HITS / MISSES:
45 / 1 — sample delta

SCHEMA VALIDATION EXECUTIONS:
A46 / B46; actual DB inspection도46 / 46

BASELINE CONNECT/SCHEMA TIME:
객체13요청: 1.019198065 / 0.995423251초 — 포함 시간

OPTIMIZED CONNECT/SCHEMA TIME:
객체13요청: 0.685656684 / 0.662399657초 — 포함 시간

BASELINE HANDLER TIME:
3.180023143초 — 객체13요청

OPTIMIZED HANDLER TIME:
2.841368689초 — 객체13요청

NET LOCAL PERFORMANCE:
0.338654454초·10.6494% 감소; 두 block 10.5805%/10.7312%

N=5K CONDITIONAL SAVINGS:
parser 관련 반복 작업 모델 약6.619초;
동일 runtime/332 object packets/다른 비용 고정 가정, 실제 이득 미검증

REAL FLUTTER COLD A/B:
NOT RUN

END-TO-END SPEEDUP:
NOT VERIFIED

OPTIMIZATION ADOPTION:
EXPERIMENTAL — AWAITING QUALIFICATION

PRODUCT ORIGINAL SOURCE:
PRESERVED

B03 INSTRUMENTATION:
UNCHANGED

ENGINE SHA ALLOWLIST:
UNCHANGED

RELEASE ARTIFACTS:
UNCHANGED — 새 engine 미입장

BINDING PROTOCOL:
UNCHANGED

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B08:
NO

HISTORICAL EVIDENCE:
PRESERVED

N=50K FULL COLD RUNS:
0

N=100K FULL COLD RUNS:
0

N=100K INSTRUMENTED FEASIBILITY:
NO-GO

B01:
CLOSED

B02:
CLOSED

B03:
CLOSED FOR ORIGINAL IR07-AUDITED SOURCE

B04:
PASS — BOUNDED

B05:
EXPERIMENTAL ONLY

B05-A:
PASS

B05-B:
PASS

B06:
PASS

B07:
PASS — MATERIAL COST ATTRIBUTED

T6.6F PHASE B:
INCONCLUSIVE

REAL-DEVICE GATE:
DEFERRED

ANDROID MEMORY/VFS/POWER:
NOT VERIFIED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

B08 REPORT:
docs/t66f-b08-expected-revision-contract-reuse.md

B08 EVIDENCE:
docs/benchmarks/t66f-b08/

TEMPORARY ARTIFACT CLEANUP:
단일 task scratch 정리; source archive·raw·JUnit·고유 DB backup 보존

FINAL VERDICT:
PASS — SAFE REUSE AND LOCAL BENEFIT VERIFIED

NEXT ACTION:
별도 좁은 engine 입장·직접 artifact 승인 범위에서 B08 후보와 원 B03의 N=1k 실제 Flutter cold A/B를 수행해 전체 이득을 검증한다.
'''
(E/'final-footer.txt').write_text(footer);(R/'docs/t66f-b08-expected-revision-contract-reuse.md').write_text(text+'```text\n'+footer+'```\n');print(json.dumps({'report_written':True,'classification':p['classification']}))
