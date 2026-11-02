# T6.6F-B11 — §35 비용·§36 I25 증거의 T6.9 이관 규범 개정 제안

**PASS — NARROW TRANSFER PROPOSAL READY FOR AUTHORIZATION. 권고는 Option 3, 보호 조건을 포함한 이관이다.** 이는 제안 심사의 완료이며 개정 승인·효력·실행 허가가 아니다. 현재 **B10 Option D — BLOCKED, Phase B INCONCLUSIVE, formal T6.6F closure NOT AUTHORIZED, R1 activation CLOSED, production NOT AUTHORIZED**를 유지한다.

변경 ID는 `T66F-B11-TRANSFER-01`다. 원 B03의 잔여 의무 8개만 T6.9의 증거 수집 전용 하위 단계 `T6.9-E`로 이관하는 미적용 추가문을 제안한다. T6.9-E는 이 제안이 신설하려는 이름이며 기존 규범 단계라고 주장하지 않는다. 전체 F 종결은 그 증거와 별도 R1/Android proof의 독립 수용 전까지 계속 차단한다. 새 source의 좋은 결과로 원 B03 결측을 없애지 않는 보수적 이관이다.

## 1. 독립성·시작 상태·작업 권한

이 세션의 제공 이력에는 B01–B09 구현·측정 또는 B10 종결 감사 관여가 없다. 독립성은 **SATISFIED**다. 다른 agent에게 위임하지 않았으며 외부 인적 정체나 UI reasoning 설정을 인증했다고 주장하지 않는다. 역할은 요구사항·규범 변경 검토와 초안 작성에 한정한다.

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`로 예상값과 일치한다. 실제 index의 2,693개 path/mode/blob/stage와 index bytes SHA를 [starting-state.json](benchmarks/t66f-b11/starting-state.json)에 기록했다. staged 변경은 0개였지만 작업 트리는 기존 tracked 수정 10개 및 untracked 증거·소스를 포함하므로 clean이라고 하지 않는다. 시작 시 visible tracked/nonignored 파일 6,440개, 777,689,520B의 SHA/크기/mode를 기록했다. Git index나 기존 소스·프로토콜·release·증거는 수정하지 않았다.

AGENTS.md와 project-state/domain-model/known-issues/development-artifact-hygiene, architecture의 서버 authority 경계를 적용했다. 도메인 모델과 backend 계산을 authority로 유지하며 모바일 독립 금융 계산을 추가하지 않는다. 본 요청의 엄격한 no-execution 범위에 따라 build·backend/Flutter regression·benchmark·실기기·emulator·API 요청은 실행하지 않았다. 일반 AGENTS 검증 권고를 이 문서 초안에 대한 실행 허가로 해석하지 않았다.

## 2. 실제 구속 조항과 규범 의존성

원문 해시·정확한 발췌는 [requirements-source-manifest.json](benchmarks/t66f-b11/requirements-source-manifest.json), 의존성은 [normative-dependency-map.json](benchmarks/t66f-b11/normative-dependency-map.json)에 있다. C 문서 §1의 역사적 PROPOSED 표시는 유지하되, 본 심사는 B10과 요청이 지정한 현재 구현 수용 기준으로 그 필수 조항을 적용한다. 문서의 과거 설계 상태를 현재 waiver로 사용하지 않는다.

|정확한 출처|현재 요구와 종결 의존성|
|---|---|
|[§4](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:68)|engine은 immutable release artifact identity다. 다른 semantics를 old hash로 광고할 수 없으며 payload/engine/archive는 서로 다르다.|
|[§16·16-S](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:321), [§17–18](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:386)|TTL 최대900초, Available 최대4와 client attempt 최대3을 구별한다. 초기·재시작 full O(N)은 허용하지만 정당한 complete provenance가 필요하다. 정상 refresh의 hidden scan은 금지다.|
|[§23–25](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:486)|표현·구조·완전성·raw 대응·변경 receipt/validator compatibility·same Target·최종 guard/동기 COMMIT·durable readback을 유지한다.|
|[§26](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:533), [§38.8](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:790)|실제 Android driver/VFS·commit fence·I/O/power-loss proof 없이 rollout 차단. HOST 증거가 대체하지 않는다. isolated Phase B 이전 배치 시점은 명문 없음.|
|[§31–33](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:612), [I23/I24](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:732), [§38.9–11](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:791)|큰 restore/MW·legacy/migration/rollback·30 backup/artifact/GC는 별도 whole-F 의무다. R1 할당은 면제가 아니다.|
|[§34](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:665)|R1→interop/full-resync/crash→performance→독립 F→명시 rollout 순서. bounded D/E 성과로 이 전체를 통과시킬 수 없다.|
|[§35](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:683) 특히 [702행](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:702)|H/D 고정, N=1k/5k/10k/50k/100k의 no-change/card/cash 반복, rows read·hash/validation/write bytes·HTTP entity/RTT·memory·median/p95. 정상 full fetch/hash/serialize/write 0, flat P 목록 없음, bounded paths/facts.|
|[§35 비교 문장](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:700), [§15.3](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:315), [§27](/home/hjkerman/codex/money-note/docs/t66/b/t66b-hot-cold-design.md:484)|base64/JSON framing·compression CPU·headers/RTT와 full gzip, 대표/덜 반복되는 문자열, network/CPU/write 구분. backend query plan/rows·mobile bytes/rows·durable/readback·warmup/n/IQR도 해당 계약으로 보존한다.|
|[§36 I25](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:734), [§38.7·12](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:789)|steady-state full-N MUST NOT; 실제 rows/bytes로 증명. lease/GC/refcount hidden O(N) 금지와 고정 H/D/full gzip/HTTP proof가 비용 종결과 연결된다.|
|[§35 마지막 문장](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:702), [§38.12](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:794)|기존 승인된 단계 분리는 post-T6.6 기기 성능뿐이다. Android durability·HOST §35/I25의 수집 이관은 현재 허용되지 않는다.|

§35가 five-point grid를 직접 수립한다. B 설계 §27도 같은 다섯 규모를 제안한다. §36 I25 자체의 행에는 N100k 숫자가 없지만 §35/§38.7·12의 scaling proof와 결합되어 다섯 번째 정상 경로 증거가 필요하다. 반대로 **N100k instrumented full cold 성공을 독립 MUST로 만드는 문장은 없다.** §18/35는 cold의 O(N)을 허용하며 필수 정상 비용은 적법 baseline 위에서 얻을 수 있다.

숫자 H/D·warmup 수·표본 수·p95 estimator·절대 ms 합격선은 C §35에 없다. 기존 실험의 105행·n3를 보편 규범으로 만들지 않는다. VM/pager 전수 방문·NAND·순수 heap peak·exclusive observer CPU도 새 필수 gate로 발명하지 않는다. 원 metric의 관측 한계는 반드시 표시한다.

## 3. B10 판정과 증거 출처

[B10 §3–7](/home/hjkerman/codex/money-note/docs/t66f-b10-independent-phase-b-closure-adjudication.md:51) 및 [closure-decision.json](benchmarks/t66f-b10/closure-decision.json)의 Option D를 그대로 유지한다. 다음은 과거 결과를 읽은 범위이며 B11 신규 실행이 아니다.

|구분|검증된 범위|현재 남는 한계|
|---|---|---|
|A. B02 N100k 기능|당시 source `1cabf319f0ac2c2069e804b47cb527b55e3374db`의 비계측 실제 D→E/E3/E4·delta/restart CLOSED. 400,532객체·261,543,083B|원 B03 ON 비용/계측 cold/I25 정량 전체로 승계할 수 없다.|
|B. 계측 cold|역사 IC01/P02→P03는 397,146/400,532·2,699.957907초·세 lease 만료·E3/E4 미완료 FAIL|최종 IR07 원 B03의 N100k 계측 full cold 성공은 UNVERIFIED. 기존 NO-GO 유지. 단독 재cold MUST로 추가하지 않는다.|
|C. B04 비용|원 B03의 1k/5k/10k/50k, 유효 통제80개/40쌍·정상 ON36개|N100k 정상 세 workload 및 rows/network/framing/full gzip 완결 비교의 결측 열.|
|D. E3 I25|네 N 정상 ON의 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds=0|N100k matched 직접 계측 미검증. 50k나 B02 one-row 보조 counter로 대체하지 않는다.|
|E. 실기기|기기 성능은 기존 post-T6.6 단계 분리|memory/VFS·전원·thermal·hardware 중단 미검증. 성능과 §26 durability는 서로 다른 의무다.|
|F. whole-F/R1|§26/31/32/33/34·I23/I24·§38.8–11 미완료 유지|비용 이관으로 formal F·R1 사용자 활성화·배포가 가능해지지 않는다.|

원 B03 IR07 correctness는 [IR07 보고서](/home/hjkerman/codex/money-note/docs/t66f-b03-ir07-independent-pep669-closure.md:1)와 [계측 환경 결정](benchmarks/t66f-b03-ir07/monitoring-contract-decision.json)의 지원 source/runtime에 대해 CLOSED다. 새 material 반증은 발견하지 않았고 재감사하지 않았다. B01/B02 CLOSED, B04 bounded PASS, B09 exact admission/real-path PASS·performance MIXED도 그 범위에서 유지한다. B05/B08은 EXPERIMENTAL — NOT ADOPTED다.

B02 원 근거는 [§17–20](/home/hjkerman/codex/money-note/docs/t66f-b02-independent-targeted-audit.md:272), [summary](benchmarks/t66f-b02-independent/summary.json), [execution-100000](benchmarks/t66f-b02-independent/execution-100000.json)다. P03는 [원 full-analysis](benchmarks/t66f-b03-ic01-p03/evidence/full-analysis.json), [당시 source review](benchmarks/t66f-b03-ic01-p03/evidence/ic01-p02-source-review.json), [B04 재구성](benchmarks/t66f-b04/historical-p03.json)을 보존한다. 최종 IR07 payload를 역사 P03에 붙이지 않는다. B10은 원 B02 scratch 소실과 evidence 내 DB 부재를 확인했으며 B11도 사용 가능한 N100k accepted DB를 인증하지 않는다. 전체 filesystem의 부재를 단정하지 않는다.

## 4. 남은 의무의 정확한 목록

아래 ID는 B11 추적 별칭이며 새로운 원 규범 ID가 아니다. 수용 단위는 8개이고 여러 B10 parent/metric/scale 별칭은 중복 추적이다. 모든 B10 미완료 행 **37개**를 원 열 그대로 [transfer-obligation-register.json](benchmarks/t66f-b11/transfer-obligation-register.json)의 coverage에 보존했다. 각 canonical 의무에는 원 criterion·정확한 조항·scale·source/runtime/fixture·existing/missing evidence·blocker·기존 deferral·제안 owner·milestone·검증·미완료 결과·semantics 변경 여부가 있다.

|이관 추적 ID|원 요구|정확한 결측과 future owner|
|---|---|---|
|T35-100K-NC|§35, §38.12|N100k 해당 정상 cell의 전체 지표·raw 반복·accepted generation E3/E4. 네 N의 실측을 외삽할 수 없음. 제안 owner=T6.9-E, 개인 미배정.|
|T35-100K-CARD|§35, §38.12|N100k 해당 정상 cell의 전체 지표·raw 반복·accepted generation E3/E4. 네 N의 실측을 외삽할 수 없음. 제안 owner=T6.9-E, 개인 미배정.|
|T35-100K-CASH|§35, §38.12|N100k 해당 정상 cell의 전체 지표·raw 반복·accepted generation E3/E4. 네 N의 실측을 외삽할 수 없음. 제안 owner=T6.9-E, 개인 미배정.|
|T35-ROWS|§35, §27|기존 제한 반환 행/SQL 증거를 source·workload별로 연결하고 미계측 열을 실제 증거로 보완한 완결 rows-read 표. VM/pager/NAND 전수 계수는 새 의무가 아님. 제안 owner=T6.9-E, 개인 미배정.|
|T35-NET|§15.3, §35, §38.12, §27|실측 HTTP entity/요청 수가 있는 하위 N도 headers/framing/대조군 연결 전체가 완결된 것으로 보지 않음. 다섯 N 비교의 결측 열과 N100k 정상 전체. 제안 owner=T6.9-E, 개인 미배정.|
|T35-GZIP|§35, §38.12, §27|과거 offline gzip6/Brotli4 다섯 점은 원 경계에 한정. 현재 segmented와 같은 source·fixture·Context의 full authoritative bytes 및 각 비교 열을 결합한 완결 증거. 제안 owner=T6.9-E, 개인 미배정.|
|I25-E3-100K|§36 I25, §35|원 B03 N100k 정상 세 workload의 E3Verify/Prepare/Commit counter 및 accepted publication/E4. 50k까지 36개 ON의 full-N 0으로 100k를 통과시킬 수 없음. 제안 owner=T6.9-E, 개인 미배정.|
|I25-BOOKKEEPING-100K|§38.7, §16, §16-S, §35|N100k 정상 D/E 계측에서 root pin/bookkeeping/transfer 경계까지 full scan 부재를 직접 귀속하는 증거. maintenance full 검증은 정상 표본 밖으로 분리. 제안 owner=T6.9-E, 개인 미배정.|

세 N100k 비용 cell은 hash/validation/write·memory·분포까지 포함한다. T35-ROWS/NET/GZIP는 하위 네 N에 남은 비교 결측도 포함하므로 N100k 한 점만 더하면 전체 비교가 자동 완료되는 것은 아니다. 기존 raw로 정확히 복구 가능한 열은 재집계할 수 있고, 없는 열은 실제 증거가 필요하다.

비이관 의무는 E-DEVICE-PERFORMANCE, F-ANDROID-DURABILITY, F-RECOVERY, F-MIGRATION, F-BACKUP, F-WHOLE-EXIT 및 SOURCE-REQUALIFICATION이다. B-COLD-100K는 역사 미검증 주장 보존 항목이며 독립 필수 gate가 아니다. A-B02-FUNCTIONAL은 closed provenance로 함께 남긴다. 어떠한 항목도 이관 때문에 사라지지 않는다.

## 5. T6.9의 실제 범위와 이관 실현성

[T6.6A §18](/home/hjkerman/codex/money-note/docs/t66/a/t66a-payload-attribution.md:370)은 full 50k/100k scalability 승인을 T6.9 범위로 기술한다. [T6.6B §27](/home/hjkerman/codex/money-note/docs/t66/b/t66b-hot-cold-design.md:484)은 fixed hot/seed/context/문자 다양성·다섯 N, no-change/card/cash·confirmed-heavy·한 달 hot 대량을 구분하는 PROPOSED F/T6.9 감사 방향이다. [§29](/home/hjkerman/codex/money-note/docs/t66/b/t66b-hot-cold-design.md:513)의 도식은 F 뒤에 post-T6.6 실기기/T6.9를 놓는다. C는 §33에서 T6.8 이후 dead API 별도 소비자 감사를 명시하지만 T6.9의 별도 상세 acceptance/owner/entry 계약은 확인되지 않았다. T6.7 UX를 시작할 독립 승인 규정도 이 검색으로 확보하지 못했다. 기존 범위의 방향을 없애거나 T6.9가 이미 잔여 8개를 소유한다고 주장할 수 없다.

따라서 **기술적·규범적 실현성은 CONDITIONAL**이다. 기존 D→TLS→Flutter/E3/E4 측정 수단과 원 B03 계측 인증이 있어 수집 역할을 맡길 구조는 있지만 N100k baseline·실행 성공은 미입증이다. 초안은 T6.9의 인수 acceptance와 prerequisites를 모두 새로 명시해야 한다. 상세 명세가 없다는 이유로 불완전 인계를 묵인하지 않고 C §35-T69를 인수 계약으로 제정하는 미적용 초안을 제공한다. 나중 별도 T6.9 문서가 생기면 이 의무와 원래 대규모 감사 범위를 함께 수록·대조해야 한다.

F 종결을 T6.9 수집의 전제로 그대로 두면 `F→T6.9 수집→F` 순환이 된다. 권고안은 F 전체 exit를 열지 않고 **T6.9-E collection-only entry**만 F 전에 허용하도록 C §34와 B §29의 관계를 함께 고친다. 기존 T6.9 전체 감사/최종 수용과 기기 gate에는 완료를 부여하지 않는다. 기존 문구는 현행 무승인 이관을 허용하지 않지만, §38 마지막 원칙은 실패 시 차단과 별도 명세 변경 감사를 요구하며 별도 명시 개정 제안 자체를 영구 금지하지는 않는다. 현재 예외를 발명하지 않고 이 문구를 정확히 제안하는 이유다.

T6.7/T6.8은 행정 종결을 근거로 unqualified source나 100k PASS를 사용하지 못한다. 이 초안은 해당 구현을 허가하지 않으며 legacy fallback/consumer 제거도 허가하지 않는다. T6.9-E 수집은 T6.7/8 완료를 전제로 삼지 않는다. 별도 R1 구현 작업의 선행 필요와 사용자 R1 활성화 CLOSED도 혼동하지 않는다.

## 6. source-version 한계와 재자격

원 기준은 payload `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`, engine `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c`, archive `fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5`다. [B04 source-identity](benchmarks/t66f-b04/source-identity.json)와 [B10 source 경계](benchmarks/t66f-b10/source-certification-boundaries.json)가 근거이며 B11은 archive를 복원·실행하지 않았다. live B05-A나 별도 B08/B09 engine은 이 기준이 아니다.

이관을 안전하게 좁히기 위해 **나중 다른 source의 측정만으로 원 B03 이관 의무를 수용하는 경로는 제안하지 않는다.** 미래 최적화/최종 제품 source는 그 source의 미래 주장만 검증한다. 원 B03 정상 비용 증거가 나중에 완결되면 새 B03 cold 없이도 적법 baseline/provenance를 통해 이관 수용은 가능하지만, 원 P03 실패나 과거 full cold 미검증은 그대로다. 원 source에서 더는 측정할 수 없다면 이 개정 아래 의무를 완료시킬 수 없으며 별도 인간 결정·독립 개정 심사가 필요하다.

미래 source 채택/검증은 별도 승인 대상이다. backend engine 입력·artifact/allowlist·validator/schema·instrumentation·runtime/monitoring·Android binary/driver가 달라지면 변경 inventory와 exact identity를 먼저 기록하고 영향받는 계측 byte/SQL/ownership/cancellation oracle, 구조·index/root parity, same-view/authority/fence, accepted provenance·legacy/recovery/durability를 재자격한다. §23의 호환 proof 없는 validator/schema 변경은 full revalidation 대상이다. 성능 인증은 그 source의 전체 다섯 점 곡선으로 수행하며 옛 네 점+새100k를 합치지 않는다. 무조건 B01–B03 전체 closed 시험을 반복하는 의무는 만들지 않는다. 원 금융 데이터의 semantic equality는 두 engine의 동등성 증명이 아니다.

## 7. 세 가지 처분 비교

|선택|효과·비용|판정|
|---|---|---|
|1. 현행 유지|8개 결측을 기존 Phase B 안에서 완결할 때까지 현재 차단. 새 규범/entry 계약 비용 없음. baseline·계측 실현성 및 지연은 남음.|거절 시 기본 경로. 최소 증거는 위 8개이며 새 full cold 자체를 추가하지 않음.|
|2. 좁은 조건부 이관|의무를 T6.9에 보내고 행정 종결만 구분.|상세 entry/source/owner/gate 없이는 순환·무기한 미이행·source 대체 위험이 있어 단독 채택 비권고.|
|3. 보호 조건부 이관|원 source 고정·기명 owner/독립 수용자·수집 전용 entry·hard milestone·새 source 불대체·whole-F 차단을 함께 명문화.|권고. 모든 의무와 거부 가능성을 유지하지만 실제 실행 성공/일정은 보장하지 않음.|

[option-comparison.json](benchmarks/t66f-b11/option-comparison.json)에 같은 판단을 기록했다. Option3도 현재 미승인이며 사람이 승인하지 않으면 Option1이 계속 구속한다.

## 8. 정확한 미적용 개정문

아래는 **삭제 없는 추가문 방식의 redline**이다. 각 `현재 원문`은 해당 줄의 exact repository text이며 `추가안`은 그 뒤에 넣자는 제안이다. 원 파일은 수정하지 않는다. 기계 원본은 [proposed-amendment-record.json](benchmarks/t66f-b11/proposed-amendment-record.json)이다. 승인 시 AM01–05를 일관된 한 변경으로 심사·적용해야 하며 일부만 적용해 guard 문구를 누락할 수 없다. 원문이 달라졌다면 exact context를 다시 대조하고 재심사한다.

### AM01. docs/t66/c/t66c-delta-sync-protocol.md §34

대상: [§34](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:665). 사유: 상태 이름과 수집 전용 entry·hard gate를 명문화하여 행정 종결 오독과 순환 방지. 증거 효과: 8개만 시점 이관; R1/Android/whole-F 그대로.

현재 원문 — 아래 내용은 유지:

````text
**IMPLEMENTATION DEPENDENCY:**

```text
D1 schema admission + epoch/bootstrap + writer fence
 → D2 capture coverage + sync pre-commit roots/index + exact maintained aggregates
 → D3 canonical objects + coherent observation/transfer + leases/GC
                         ↘
E1 C1/shape/raw facts parity → E2 local store/durability/pins
 → E3 complete index + tree diff + publisher → E4 pending/Offline/legacy adapter
                         ↗
R1 large restore/MW + artifacts/retention + migration/rollback
 → isolated new-client interoperability/full-resync/crash suites
 → performance gates (H/D fixed, N increased; compression comparison)
 → T6.6F independent integrated audit → explicit rollout authorization
```
````

추가안 — DRAFT ONLY / NOT APPLIED:

````text
### 34-B11. 제한 Phase B 행정 종결과 증거 이관 — 승인된 경우에만 효력

이 예외는 T66F-B11-TRANSFER-01의 별도 유효 승인 기록이 있는 경우에만 적용한다(MUST). 대상은 원 B03 source의 T35-100K-NC, T35-100K-CARD, T35-100K-CASH, T35-ROWS, T35-NET, T35-GZIP, I25-E3-100K, I25-BOOKKEEPING-100K의 미완료 증거 수집뿐이다. 이 ID는 본 예외의 추적 ID이며 기존 I25 등 규범 ID를 대체하지 않는다.

승인자는 권한 근거와 실제 승인자·일시·승인 대상 exact 문서 SHA 및 8개 의무, T6.9-E 기명 책임자와 독립 증거 수용자, hard blocking milestone, 보고 책임·위험 수락 범위를 한 결정 기록에 명시해야 한다(MUST). 누락·pending·draft·이의 없는 침묵은 유효 승인이 아니다(MUST NOT). 승인 자체는 새 benchmark/최적화/기기 실행·소스 변경 허가가 아니며 실행은 별도 계획·기존 제한의 명시 GO를 필요로 한다.

유효 승인 뒤 bounded work package는 완료, Phase B 행정 상태는 ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED로 기록할 수 있다. 동시에 Phase B 정량 증거 상태는 INCONCLUSIVE, 다섯 점은 PARTIAL, N100k 정상/I25는 UNVERIFIED로 유지해야 한다(MUST). 이 상태는 quantitative PASS 또는 formal T6.6F CLOSED가 아니다.

§35-T69의 증거 수집 전용 T6.9-E에 한해 formal F exit 전에 진입하도록 순서를 조정한다. R1 구현 proof·interop/full-resync/crash 및 다른 선행 의무는 제거하지 않는다. 모든 이관 의무의 독립 수용과 나머지 §26/31/32/33/34, I23/I24, §38.8–11 whole-F proof가 충족될 때까지 formal T6.6F exit 재심사를 통과시킬 수 없다(MUST NOT). 최종 T6.9 수용도 그 전에 완료로 표시할 수 없다.

T6.7/T6.8 구현·cleanup은 행정 종결을 PASS나 자동 entry로 사용할 수 없다(MUST NOT). 본 예외는 그 작업을 승인하지 않으며, 기존 legacy full consumer/store와 복구 경로를 제거할 근거가 아니다. T6.9-E 수집은 T6.7/8 구현 완료나 사용자 활성화를 요구하지 않는 격리 subgate다. 독립적인 R1 구현 작업 단계와 R1 사용자 활성화는 별개이며, R1 활성화·segmented rollout·production deployment는 전체 proof와 별도 명시 승인이 있을 때까지 계속 차단한다.

이관 누락·실패·수행 불능을 이유로 요구를 소거하거나 자동 연장/수용할 수 없다(MUST NOT). 책임자는 차단 상태와 증거를 기록하고 승인권자에게 보고해야 한다. 철회/조건 위반이면 행정 종결 효력을 중단하고 원 종결 gate를 복원한다. 후속 결과는 그 날짜/source의 새 증거이며 과거 실패·미측정 상태를 다시 쓰지 않는다.
````

### AM02. docs/t66/c/t66c-delta-sync-protocol.md §35

대상: [§35](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:698). 사유: 현재 T6.9 상세 인수 계약 부재를 정확한 원 source 완료 계약으로 보충. 증거 효과: 다섯 점 및 모든 metric/비교 의무 유지; cold를 별도 MUST로 추가하지 않음.

현재 원문 — 아래 내용은 유지:

````text
조건부 정상 목표는 O(H + changed bytes + L log P + 256E)이며 단순 O(H+D)나 모든 operation O(1)을 주장하지 않는다. Current full financial validators/flat hash/lineage/full baseline encode가 남으면 정상 history-independent gate를 통과하지 못한다. No-change lease pin에 전체 graph 순회가 남아도 실패다. Network 단계는 tree miss 깊이/배치에 따라 늘 수 있어 B-3 1 GET/1 RTT를 무조건 유지한다고 약속하지 않는다. Inline/hints는 효율화일 뿐 완전성 근거가 아니다.

T6.6A HOST/synthetic 비교군은 10k raw **5,684,312B**, Snapshot **98.45%**, cold **97.05%**, gzip6 **108,916B**, Brotli4 **43,033B**, backend **1,348.5ms**, parser+typed **1,970.1ms**, publication **269.7ms**다. 서로 포함되는 timing을 더하지 않는다. New base64 framing·compression CPU·object HTTP headers/RTT도 비교에 포함한다. Hot raw 후보 167,812B가 full gzip보다 클 수 있다. 다양한 문자열 control gzip 568,847B와도 비교해야 한다.

Scaling 감사는 H/D 고정, N=1k/5k/10k/50k/100k에서 no-change/card/cash rebuild를 반복하고 rows read/bytes hashed·validated·written/HTTP entity/RTT/memory·median/p95를 측정한다. 정상 경로의 full history fetch/hash/serialize/write 횟수 **0**, control에 flat P 목록 없음, bounded leaf/hash-path/affected index 증가를 입증한다. Device 절대 latency 목표는 post-T6.6 gate 전 정하지 않는다.
````

추가안 — DRAFT ONLY / NOT APPLIED:

````text
### 35-T69. 이관 증거의 필수 완료 계약 — 승인된 경우에만 효력

§34-B11의 유효 승인 아래 T6.9-E는 아래 8개 미완료 의무를 인수하고 독립 수용 기록을 제출해야 한다(MUST). 수집 기한은 formal T6.6F exit 재심사 및 최종 T6.9 acceptance 중 먼저 도래하는 시점 이전이며, R1 활성화/rollout/production도 계속 차단한다. 날짜가 미정이라는 이유로 milestone 차단을 생략할 수 없다.

- T35-100K-NC/CARD/CASH: N=100000의 no-change/card/cash 정상 rebuild를 반복하여 §35의 rows read/bytes hashed·validated·written/HTTP entity/RTT/memory/median/p95를 실제 측정한다. D1–D3 generation/request, E1/E2, E3Verify/Prepare/Commit, E4 범위를 분리한다.
- T35-ROWS: N=1000/5000/10000/50000/100000의 세 정상 workload에 대해 실제 SQL/반환 행·raw/index lookup·query plan 경계의 결측 열을 보완하여 완결 비교를 제출한다. 반환 행을 모든 VM/pager 방문 행으로 표현하지 않는다.
- T35-NET: 동일 다섯 규모/workload에서 method/path·금융/auxiliary·request/response entity·decoded canonical bytes·base64/JSON framing·headers·RTT dependency/cache misses를 full 비교군과 결합한다. 4×ceil(decoded/3)의 산술은 실제 HTTP wire 관측의 대체가 아니다.
- T35-GZIP: 같은 source/DB state/Context·fixture의 full authoritative response를 full gzip 비교군으로 유지하고 representative/less-repetitive 문자열에서 network/codec CPU/parse·validation/write를 분리한다. 역사 gzip6과 대응하려면 codec level6·버전·입력 SHA/길이·압축 bytes/CPU를 기록한다. Brotli4 등 과거 비교 수치는 원 범위로 보존하며 새 matched wire 수치로 바꾸지 않는다. 오프라인 compression은 그렇게 표시하고 미관측 HTTP/RTT/headers를 채우지 못한다. 다양성 fixture의 규모·문자열 분포도 사전 계획에서 고정하며 서로 다른 family/입력을 한 곡선으로 합치지 않는다.
- I25-E3-100K: N100k 세 정상 workload의 E3Verify/Prepare/Commit rows/bytes·SQL·tree/index/pin/CAS/readback 귀속과 full_recoveries/full_verifications/full_raw_rows/full_fact_rows/canonical_full_builds=0을 직접 입증한다. 초기/재시작/명시 full recovery는 정상 counter 밖의 별도 workload다.
- I25-BOOKKEEPING-100K: 같은 N100k 정상 D/E 흐름의 lease/GC/refcount/root pin/transfer bookkeeping에 hidden full graph/history scan이 없고 control에 flat P 목록이 없음을 source와 직접 counter로 입증한다. 명시 maintenance O(N/P)를 정상 refresh 안으로 숨기지 않는다.

원 B03의 base commit ebcbd54d90eeee194a04b9eea6367f446ee2fd28, canonical payload 8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8, engine 7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c, archive fc53b16635610574ab32042b5c76e01369aba5e858fb43b51040f34b94eb59e5를 기준으로 한다. runtime은 IR07/B04 지원 CPython3.12.3/backend SQLite3.45.1/Flutter3.47.4/Dart3.13.3/client SQLite3.53.4 및 안정된 monitoring 설정이다. payload/engine/archive/runtime의 의미를 혼동하거나 live 실험 tree를 기준으로 선택하지 않는다(MUST NOT).

H/D 숫자·표본 수·절대 latency 상한은 기존 규범에 없으므로 발명하지 않는다. 원 B04 재사용 구성은 seed662602·평가일2026-10-05·offset540·current ledger105·다른 table35·초기 hot87364B/control3178B, no-change D0/card·cash UPDATE D1이다. N label=ledger 총 N, 전체 authoritative rows=N+35를 명시한다. 각 scale의 실제 fixture SHA/행/descriptor/NS/Target/변경 전후 입력을 freeze한다. 기존 4점과 이어 붙이는 N100k는 동일 H/D·문자열/descriptor·변경 규칙임을 독립 대조해야 한다. B04 raw에 실제 존재하는 동종 metric만 재사용하고 결측은 수용 전 보완한다. 새 fixture/다른 H/D가 필요하면 별도 곡선이며 원 이관 의무를 대체하지 못한다.

계측은 IR07 범위의 B03 ON이며 source-SHA·monitoring/lifecycle/ownership/byte/SQL guards를 유지해야 한다(MUST). hash 실제 sink(domain/NUL·반복 포함), primary submitted/completed/failed span, SQL NEW TEXT UTF8/BLOB attempted/effective/committed/rollback·scalar/row를 구별한다. 미지원 환경/불완전 collector·취소·실패를 성공 0으로 제출하지 않는다. OFF·backend-only·ASGI·prepare/discard·다른 source의 기능 PASS는 ON 완료 cell의 대체가 아니다. warmup/n/median/p95 estimator/IQR·계측 교란/메모리 관찰 한계를 공개한다.

수집 전 독립 admission은 source/runtime/fixture·instrumentation 지원과 완전 accepted baseline/provenance를 확인해야 한다(MUST). 이 개정은 사용할 수 있는 N100k DB가 이미 있음을 인증하지 않는다. §18/23–25에 따라 complete objects/11 tables/global index/receipt/NS/principal/Versions/Target/same-connection provenance/generation을 확인한다. 적법 baseline을 확보하지 못하면 수집 차단을 기록한다. 새로운 instrumented full cold 성공은 별도 MUST로 추가하지 않으며, 적법 baseline 위의 원 B03 정상 증거로 이관 의무를 수용할 수 있다. 새 cold가 필요해지면 기존 NO-GO를 별도 명시 계획/허가 없이 뒤집지 못한다.

실제 authenticated D3→HTTP/TLS→Flutter E2/E1→원 AppState guard의 E3 accepted publication/readback→E4가 완료되어야 한다(MUST). no-change에서 ID/sequence가 그대로인 정상 완료와 mutation의 실제 generation 전진을 구별한다. backend 실제 rows/presenters·native complete graph/값 digest·SQLite FK·hash/root·accepted before/after를 독립 대조한다. 모바일 canonical 금융 엔진을 추가하지 않는다. E3 마지막 authority guard 바로 다음의 동기 COMMIT 사이에 await/hook/callback을 넣지 않는다.

§16 TTL 최대900초, 기존 client attempts3/observations3와 principal Available 최대4의 서로 다른 제한을 보존한다. 관측 수명이나 횟수를 늘려 과거와 비교 가능한 실행을 만들지 않는다(MUST NOT). 50k를100k로 외삽하거나 부분 N을 다섯 점 PASS로 바꾸거나 uninstrumented 기능으로 실패 계측을 대체할 수 없다. B05/B08 실험 최적화 채택, 금융 canonical data·source guard·release/admission 변경은 이 예외에 포함되지 않는다.

command/cwd/exit/time·source/runtime/binary·fixture/Target/accepted before/after·stage 완료·raw samples/counters/HTTP·실패/취소·manifest SHA/mode/size를 보존해야 한다(MUST). 재검증에 필요한 일관 backend/client SQLite snapshot은 supported backup API로 보존하고 검증하기 전 유일한 matched 자료를 삭제하지 않는다. docs/development-artifact-hygiene.md에 따라 검증된 task-owned disposable만 정리한다.

다른 engine/source/runtime의 나중 결과는 해당 미래 source의 주장만 성립시키며 원 B03 8개 의무를 소거하지 못한다(MUST NOT). 새 source를 채택/인증하려면 별도 승인·exact release/admission·변경 영향 계측 oracle/정확성/구조·provenance·authority fence·durability/legacy 복구 재검증과 그 source의 전체 다섯 점 곡선이 필요하다. 호환 proof 없는 validator/schema 변경은 §23에 따라 full revalidation한다. 금융 데이터 동등성은 engine 동등성이 아니다. 원 closed B01/B02/B03 감사는 material 반증 없이 재개하지 않으며 IR07 인증을 새 source로 자동 이전하지 않는다.

모든 metric/workload/scale 및 8개 의무가 원 source·경계에 맞게 완결되고 독립 수용자가 근거/해시/한계를 기록해야 T6.9-E EVIDENCE ACCEPTED를 발급할 수 있다(MUST). 결측·불완전 실행은 PARTIAL/UNVERIFIED, 실제 full-N 위반은 귀속된 구현 거부/별도 수정·재자격 사유이며 자동 waiver가 아니다. 정량 비용은 새 ms 목표로 채점하지 않고 기존 full-N 금지/bounded 경로와 측정 완결성을 적용한다. 모든 결과는 그 날짜/source의 후속 판정이며 역사 P03 FAIL·B04 4/5·B10 Option D를 소급 PASS로 바꾸지 않는다. T6.9-E 수용은 formal F 재심사의 필요조건일 뿐 R1/Android proof·기기 gate·별도 rollout/deployment 승인의 충분조건이 아니다.
````

### AM03. docs/t66/c/t66c-delta-sync-protocol.md §36 I25

대상: [§36 I25](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:734). 사유: I25 불변과 증거 수집 시점 변경의 구별. 증거 효과: 금지/필수 counter/guard 불변.

현재 원문 — 아래 내용은 유지:

````text
| I25 steady-state full N 작업 MUST NOT | D/E integration | instrumented rows/bytes / hidden full scan | H/D fixed scaling, M |
````

추가안 — DRAFT ONLY / NOT APPLIED:

````text
I25의 steady-state full-N 작업 금지 및 D/E instrumented rows/bytes 의무는 계속 적용한다. §34-B11의 유효 승인이 있는 경우에만 §35-T69에 열거된 I25-E3-100K 및 I25-BOOKKEEPING-100K의 미완료 증거 수집 시점을 T6.9-E로 옮긴다. 이것은 I25 준수 의무의 일시 중지, 실제 위반 허용 또는 현재 PASS가 아니다. E3 즉시 guard-before-COMMIT, 필수 counters/귀속·proof 및 independent source-qualified acceptance를 유지한다.
````

### AM04. docs/t66/c/t66c-delta-sync-protocol.md §38.7–12 뒤

대상: [§38.7–12 뒤](/home/hjkerman/codex/money-note/docs/t66/c/t66c-delta-sync-protocol.md:789). 사유: 7/12와 8–11의 이관/비이관을 분리. 증거 효과: device 성능 기존 분리만 유지; Android proof/R1 면제 없음.

현재 원문 — 아래 내용은 유지:

````text
7. Lease/GC/refcount bookkeeping이 normal refresh에 hidden O(N)을 만들지 않음.
8. Android SQLite pragmas/VFS·commit fence·power-loss·I/O error·previous recovery.
9. Legacy v7/full baseline materialization·old B/J/pending·migration/rollback parity.
10. Chunk restore/MW resource limits·backup·idempotent receipt·one transaction·epoch 전이.
11. Backup/artifact 30개 보존·GC/storage exhaustion·frozen object repair 실패 처리.
12. 고정 H/D scaling·full gzip 비교·HTTP RTT/byte 계측·실기기 post-T6.6 gate.

현재 **BLOCKING PROTOCOL DECISION 0, 필수 제품 결정 0**이다. Restart epoch rotation, synchronous finalizer, B+tree leaves/Patricia facts, single local SQLite store, read-only observation POST, byte-preserving base64 transfer, explicit large-restore dependency를 선택하여 명세 공백을 남기지 않았다. 구현 증명이 실패하면 해당 구현/rollout을 차단하고 이 명세의 변경을 별도 감사받아야 한다. 완성 판정은 아직 구현되지 않은 알고리즘이 이미 안전하다는 주장이 아니다.
````

추가안 — DRAFT ONLY / NOT APPLIED:

````text
위 7·12의 필수 proof 중 §35-T69가 지정한 8개 의무의 아직 비어 있는 증거 수집 시점만 §34-B11의 유효 승인 아래 T6.9-E로 이관할 수 있다. 완전한 다섯 점·rows/bytes/HTTP/framing/full gzip 및 I25 증명을 없애거나 추정으로 채울 수 없다. 8–11의 Android durability·legacy/migration·recovery·30 backup/artifact/GC 의무는 이 예외의 대상이 아니며 기존 whole-F/rollout 차단을 유지한다. 12의 기존 post-T6.6 실기기 성능 단계 분리도 그대로다. 구현 proof 실패는 796행의 원칙대로 해당 구현/rollout 차단과 별도 명세 변경 감사를 필요로 한다.
````

### AM05. docs/t66/b/t66b-hot-cold-design.md §29 도식 뒤

대상: [§29 도식 뒤](/home/hjkerman/codex/money-note/docs/t66/b/t66b-hot-cold-design.md:513). 사유: F 이후 T6.9의 상위 도식과 수집 전용 예외의 관계 명확화. 증거 효과: 기존 T6.9 방향 유지·상세 인수/entry를 C 부록에 제정.

현재 원문 — 아래 내용은 유지:

````text
## 29. T6.6C/D/E 의존성 지도

```text
T6.6A 측정 → T6.6B 설계 → 별도 독립 설계 감사
                              │
                 T6.6C version/identity/root/전이·fallback 설계
                         ┌────┴────┐
                 T6.6D 변경 추적    T6.6E 저장/provenance/validation 설계
                 + root/aggregate   + atomic generation/legacy adapter
                         └────┬────┘
                    승인 후 transport/storage 통합 구현
                              ↓
                   T6.6F 독립 correctness/performance 감사
                              ↓
                   post-T6.6 실기기 gate / T6.9 큰 규모 검증
```

Backend change tracking/root가 정확히 만들어져야 incremental transport의 비용 이득을 주장할 수 있다. Mobile complete cold store/provenance가 있어야 unchanged validation 재사용이 안전하다. 두 쪽 contract를 먼저 함께 설계하고 producer·consumer를 순차 구현해야 한다. Alphabetical 순서대로 delta부터 활성화해서는 안 된다.
````

추가안 — DRAFT ONLY / NOT APPLIED:

````text
이 도식의 F 이후 T6.9 배치는 최종 수용 순서를 유지한다. 단, T6.6C §34-B11 및 §35-T69의 별도 유효 승인이 있는 경우 그 조항의 8개 원 B03 의무를 수집하는 격리 T6.9-E subgate에 한해 formal F exit 전에 진입할 수 있다. T6.9-E entry는 bounded 작업 인계·기명 owner/독립 수용자·source/fixture/runtime/계측·accepted provenance 사전심사와 별도 실행 GO를 요구한다. 전체 F PASS·R1 활성화·T6.7/8 완료를 수집의 전제로 요구하지 않지만 이들의 구현/활성화를 승인하지도 않는다. 최종 T6.9 acceptance, formal F exit 및 rollout/deployment에는 이관 증거의 독립 수용과 나머지 선행 gate가 여전히 필요하다. §27의 confirmed-heavy/한 달 hot 대량·initial/full/restore/crash 등 기존 T6.9 감사 방향은 이 8개 의무에 흡수하거나 면제하지 않는다. 상세 T6.9 명세가 별도로 제정되면 이 계약과 기존 범위를 명시적으로 수록·대조해야 하며, 현재 독립 상세 명세가 존재한다고 가정하지 않는다.
````

§4·16–18·23–26·31–33의 수신/identity·복구·R1 기준 자체는 개정할 필요가 없다. §38.8–11도 변경 대상에서 제외한다. 독립 T6.9 상세 명세의 현행 문구는 발견되지 않았으므로 만들어 낸 current quotation이나 가상 파일 경로를 쓰지 않는다. 위 AM02/AM05가 새 인수 계약과 entry 변경의 exact 제안이며, 기존 상세 명세를 수정했다고 주장하지 않는다.

## 9. 보존할 기준과 미래 증거 수용 계약

위 AM02와 JSON future_acceptance_contract가 동일 계약이다. reviewer가 전체 audit chain을 다시 열지 않고 다음을 확인할 수 있다.

|수용 요소|필수 계약|
|---|---|
|규모·입력|다섯 N의 세 정상 workload, 실제 H/control/policy/문자 bytes와 D 고정. B04 재사용 digest 4개는 JSON에 있고 N100k digest는 미발급/null이며 실행 전 freeze해야 함.|
|계측·source|원 B03/IR07 지원 runtime ON. 실제 sink/primary spans/SQL NEW payload와 실패·rollback·stage 귀속. exact source/release/admission guards 불변.|
|rows·network·gzip|기존 raw의 실제 열만 재사용, 결측 명시·보완. 다섯 N 비교·framing/headers/RTT·full gzip과 다양성 비교 의무 유지. offline compression을 actual wire로 부르지 않음.|
|I25|E3 full counters0와 hot/changed/tree/index 작업·pin/COMMIT/readback 귀속, D/E lease/GC hidden scan 부재. wall slope만으로 O(1) 증명하지 않음.|
|실제 accepted completion|정당한 baseline/receipt→실제 D3/TLS/Flutter/E3→accepted readback/E4. no-change sequence 유지 가능. prepare/discard는 수용 표본 아님.|
|독립 correctness|실제 backend raw/presenters·native graph/value digest/FK·source identity. 모바일 금융 재계산 gate 추가 없음.|
|raw·보존|실패 포함 command/exit/time/표본·Target·accepted·metric·HTTP·manifest SHA/mode/size; 필요한 일관 DB는 보존/검증 뒤 disposable만 정리.|
|판정|모든 8개와 scale/metric의 원 source 증거가 완결되어야 T6.9-E EVIDENCE ACCEPTED. 정량 기준은 그대로이며 단말 절대 ms 기준을 새로 만들지 않음.|
|실패|결측은 PARTIAL/UNVERIFIED, 실제 full-N 위반은 귀속된 구현 거부/수정·재자격 사유. timeout/expired를 성공으로 바꾸지 않음. 차단 지속.|

B03 measurement guards·E3 guard 바로 뒤 동기 COMMIT·I25 counters를 완화하지 않는다. 일부 규모·외삽100k·비계측 기능으로 결측을 채우지 않는다. TTL/attempt 연장, B05/B08 채택, canonical data/source-SHA guard/release/admission 변경, 미실행 device PASS, R1 활성화·production 배포를 허가하지 않는다. 원 source 인증과 역사 실패는 소급 변경하지 않는다.

## 10. 승인·거절·실패 시 처분

**APPROVAL AUTHORITY NOT ESTABLISHED — EXPLICIT USER/PROJECT OWNER DECISION REQUIRED.** AGENTS는 명시 배포 요청을 요구하고 C §34는 구현·rollout 승인을 요구하지만, 이 규범을 바꿀 개인/직함·상설 절차를 특정하지 않는다. C §16-S의 과거 소유자 승인도 현재 reviewer에게 포괄 권한을 주지 않는다. 이 요청은 drafting authority만 부여했으므로 승인으로 간주하지 않는다.

유효 결정은 권한 근거·실제 승인자/일시·변경 ID와 exact 초안 SHA·8개 의무·기명 T6.9-E 책임자·독립 수용자·blocking milestone/보고 의무·잔여 위험 수락을 명시해야 한다. 지금 개인 이름·날짜·권한자는 null이며 B11이 지명하지 않는다. 승인에 필요한 이 필드들을 채워야 효력이 생기는 조건부 문구는 완성되어 있다. 새 benchmark 실행은 이 승인에 자동 포함되지 않으며 별도 사전 계획/GO가 필요하다.

위험은 N100k baseline 부재·계측 overhead/시간·증거 확보 실패·행정 상태 오독·책임자 미지정·미래 source와 원 source의 이중 검증 비용이다. 이 위험을 수락해도 actual full-N 위반이나 미측정을 PASS로 승인하는 권한은 이 제안에 없다. 원 source 측정이 불가능하면 T6.9-E를 수용할 수 없고 formal F 등 차단을 유지한다.

거절/미승인은 현행 원문·Option1·B10 차단을 유지한다. 승인 뒤 조건 위반/철회가 발생하면 행정 종결 효력을 중단/철회하고 원 gate를 복원한다. 이미 얻은 유일 증거·실패 원문은 보존한다. 자동 기한 연장·blanket waiver는 없다. 후속 별도 적용 작업은 AM01–05와 실제 T6.9 문서 존재 여부를 다시 대조한 뒤 문서에 반영하며 이 작업에서 수행하지 않았다.

## 11. 승인 전후에 가능한 상태 표현

|서로 다른 상태|승인 전 현재|Option3가 유효 승인·별도 적용된 뒤, 증거 완료 전|
|---|---|---|
|bounded measurement work package|B04 범위 완료·PASS|같은 scoped 결과 유지|
|Phase B 행정 종결|허가되지 않음|ADMINISTRATIVELY CLOSED — EVIDENCE TRANSFERRED만 허용|
|Phase B 정량 증거 수용|INCONCLUSIVE; grid PARTIAL; 100k/I25 UNVERIFIED|동일. 후속 T6.9-E 독립 수용 이후에만 새 날짜·source의 수용 판정 가능|
|formal T6.6F closure|NOT AUTHORIZED|여전히 NOT AUTHORIZED. 8개와 나머지 whole-F proof 완료 후 새 독립 재심사 필요|
|whole-F release proof|미완료|R1/Android/legacy/recovery/backup 등 독립 의무 유지|
|R1 activation|CLOSED|CLOSED. R1 구현 stage 진척과 사용자 활성화는 다름|
|production deployment|NOT AUTHORIZED|NOT AUTHORIZED. proof 완료도 별도 명시 승인/운영 요청을 대체하지 않음|

B01/B02 CLOSED, 원 B03 IR07 CLOSED, B04 bounded PASS, B05/B08 미채택은 승인 전후 그대로다. 과거 B10 Option D가 소급 변경되는 것도 아니다. 승인 후 행정 상태는 새 결정으로만 기록한다.

## 12. 분석 검증·보존·최종 권고

B11 검증은 새 JSON 파싱/필수 필드·상호 ID/8개 의무·37개 B10 미완료 행 coverage, exact 원문 발췌·인용 경로, manifest SHA, index path/mode/blob와 실제 index bytes 및 시작 파일 SHA/mode 비교뿐이다. 제품 import/실행·full cold·build·backend/Flutter regression·real-device는 0회다. 검증 결과는 [validation-and-preservation.json](benchmarks/t66f-b11/validation-and-preservation.json), 산출물 해시는 [evidence-manifest.json](benchmarks/t66f-b11/evidence-manifest.json)에 남긴다. B11 전용 문서/JSON/분석 작성·검증 도구만 생성했다. 대형 임시 실험 산출물 정리는 NOT APPLICABLE, 삭제/회수0B이며 기존 파일과 ignored runtime artifacts에는 쓰지 않았다. 초기 bwrap loopback 초기화 오류는 명령 실행 전 실패했고 승인 검토된 도구 경로로 문서 읽기/작성만 계속했다. 자동 승인 거절은 없었다.

**최종 권고: Option 3 보호 조건부 이관안 T66F-B11-TRANSFER-01을 명시적 인간 승인 대상으로 제출한다.** 원 B03 증거의 장소/수집 시점과 행정 상태만 변경하고 수용 조건을 약화하지 않는다. 이것은 실제100k 성공이나 실행 실현성을 인증하는 PASS가 아니다.

정확한 다음 행동: 사용자 또는 프로젝트 소유자는 T66F-B11-TRANSFER-01의 보호 조건부 이관안과 승인 권한 근거·기명 책임자·독립 수용자·차단 마일스톤을 하나의 명시적 결정으로 승인하거나 거절하십시오.

## 필수 판정 기록

```text
T6.6F-B11 NORMATIVE DEFERRAL PROPOSAL:
PASS

STARTING HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

REVIEWER INDEPENDENCE:
SATISFIED

AUTHORITATIVE REQUIREMENTS:
T6.6C §4, §16–18, §23–26, §31–36, §38.7–12;
T6.6B §27·29; T6.6A §18

B10 CLOSURE ADJUDICATION:
OPTION D — BLOCKED

CURRENT PHASE B:
INCONCLUSIVE

CURRENT FORMAL T6.6F CLOSURE:
NOT AUTHORIZED

ORIGINAL B03 INDEPENDENT CORRECTNESS:
CLOSED — IR07, ORIGINAL SOURCE

B05 OPTIMIZATION:
EXPERIMENTAL — NOT ADOPTED

B08 OPTIMIZATION:
EXPERIMENTAL — NOT ADOPTED

§35 OPEN OBLIGATIONS:
T35-100K-NC, T35-100K-CARD, T35-100K-CASH,
T35-ROWS, T35-NET, T35-GZIP (B11 추적 ID)

I25 OPEN OBLIGATIONS:
I25-E3-100K, I25-BOOKKEEPING-100K (B11 추적 ID)

FIVE-POINT COST GRID:
PARTIAL

N=100K INSTRUMENTED COLD:
NOT SUCCESSFULLY VERIFIED

T6.9 TRANSFER FEASIBILITY:
CONDITIONAL

SOURCE-VERSION REQUALIFICATION:
변경 source/runtime의 exact identity·영향 계측/구조/authority/복구 재검증;
미래 source 성능은 독립 다섯 점으로 검증, 원 B03 결측 대체 불가

RECOMMENDED OPTION:
TRANSFER WITH SAFEGUARDS

PROPOSED AMENDMENT:
DRAFT ONLY — NOT APPLIED

ACCEPTANCE CRITERIA WEAKENED:
NO

FUTURE EVIDENCE OBLIGATIONS:
위 8개 의무 전부: 100k 정상 3 workload 비용,
다섯 N rows/network/framing/full gzip 완결 비교,
E3·lease/GC/refcount I25 직접 계측·독립 수용

BLOCKING RELEASE/ACTIVATION GATES:
이관 8개 독립 수용; §26·§31–34·I23/I24·§38.8–11 whole-F proof;
formal T6.6F 재심사·최종 T6.9 수용·기기 gate·별도 명시 승인

APPROVAL AUTHORITY:
NOT ESTABLISHED — EXPLICIT USER/PROJECT OWNER DECISION REQUIRED

EXPLICIT APPROVAL:
NOT GRANTED

BINDING PROTOCOL MODIFIED:
NO

T6.9 SPECIFICATION MODIFIED:
NO

PRODUCT SOURCE MODIFIED:
NO

ENGINE ADMISSION MODIFIED:
NO

GIT STAGED CONTENT:
PRESERVED

GIT INDEX MODIFIED BY B11:
NO

HISTORICAL EVIDENCE:
PRESERVED

NEW FULL COLD RUNS:
0

REAL-DEVICE GATE EXECUTION:
DEFERRED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

B11 REPORT:
docs/t66f-b11-normative-deferral-proposal.md

B11 EVIDENCE:
docs/benchmarks/t66f-b11/

FINAL VERDICT:
PASS — NARROW TRANSFER PROPOSAL READY FOR AUTHORIZATION

NEXT ACTION:
사용자 또는 프로젝트 소유자는 T66F-B11-TRANSFER-01의 보호 조건부 이관안과 승인 권한 근거·기명 책임자·독립 수용자·차단 마일스톤을 하나의 명시적 결정으로 승인하거나 거절하십시오.
```
