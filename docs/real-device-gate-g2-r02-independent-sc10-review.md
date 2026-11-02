# Money Note — Real-Device Gate G2-R02 독립 SC10 재검토

**PASS — R01-B01 INDEPENDENTLY CLOSED; G2 READY FOR OWNER NORMATIVE DECISION**

R01-B01의 문서상 모호성을 독립 종결한다. 수정 후보는 E가 사전에 수용할 안전 속성·target 대응 근거·독립 판정 기준과 F/G 이후에만 수집할 실제 instance·통신 가용성 결과를 구별한다. 필요한 사전 안전 근거를 접촉 없이 마련할 수 없으면 **terminal BLOCKED**로 끝내므로 승인 순환이나 숨은 장치 접촉 경로가 없다. 새 차단 finding과 안전·권한 회귀는 각각 0건이다.

이 PASS는 **소유자 규범 결정 준비 상태만** 뜻한다. Galaxy S23 FE가 실제 SC10을 만족하는지, 구현·시험이 성공할지, E가 통과 가능한지를 수용하지 않았다. G2 승인·적용, 원 F01/G1 변경, 구현·에뮬레이터·연결·첫 mutation 권한 및 G1 기술 proof는 부여하지 않는다.

**독립성과 검토 범위**

기존 G2-R01 독립 검토 세션을 이어 사용했다. G2-P01 또는 G2-SC10의 저자 세션이 아니며 이번 후보·명확화 작성에도 참여하지 않았다. 검토자 독립성은 **SATISFIED**다. 원 R01-B01의 정적 trigger·최소 명확화·종료 기준에 한정해 변경을 대조했으며 전체 G2 위협 모델을 다시 열지 않았다.

AGENTS.md와 산출물 위생 규칙을 다시 읽었다. 기존 세션에서 읽은 project-state/domain-model/known-issues·architecture 신뢰 경계를 포함한 지배 출처 pin 37개가 그대로임을 재확인했다. 원 P01·R01, [SC10 명확화 보고서](real-device-gate-g2-sc10-clarification.md), 수정 후보·정확한 redline·변경 JSON·편입 명세·단계 의존 기록을 읽었다. 원 PREP03/PREP09 F01과 현행 G1 S1/S3/S4, 상위 B §27/29 및 C §26/34/34-B11/35/35-T69/38.8–12의 구속 관계는 이전 검토와 동일하다.

**후보 신원과 정확한 변경**

후보 경로는 SC10 보고서에서 직접 확인했다. 후보 내용을 검토하기 **전에** 요청 SHA-256과 실제 bytes를 대조했으며 일치했다.

| 대상 | 실제 SHA-256 |
| --- | --- |
| [수정 후보](benchmarks/real-device-gate-g2-sc10/corrected-proposal-candidate.md) | `1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb` |
| [현행 G1 계약](real-device-gate-g1-safety-contract.md) | `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0` |
| [편입 SC10 증거·수용 명세](benchmarks/real-device-gate-g2-sc10/sc10-evidence-and-acceptance.json) | `8b86ae470e7bea9a7d409b16a129720fb7e9b548852544f4b6f82f21adfa5922` |
| [정확한 redline](benchmarks/real-device-gate-g2-sc10/targeted-correction.redline.patch) | `a150efc2a4eefa546646bc26edda94ec0778f8d021a5aea1a36492dd573dd1f2` |

실제 before/after에서 변경을 독립적으로 발견했다. 후보 본문에는 **연속 삽입 1개, 6행·2,325바이트**만 있다. 이 삽입을 제거하면 원 P01의 bytes가 정확히 복구된다. 원 P01은 `d36ecef2941563178f17063aa16013c1008859223fbf171cccd84ff51330b7c8`로 보존됐다.

JSON을 재귀 비교한 결과 값 변경은 다음 **2개뿐**이다. key 추가·삭제, 배열 길이 변경, 다른 값 변경 또는 별도 형식 변경은 없다.

| 후보 JSON | 변경 pointer | 의미 |
| --- | --- | --- |
| [안전 통제 사본](benchmarks/real-device-gate-g2-sc10/candidate/safety-controls-and-residual-risks.json) | `/controls/9/qualification_ko` | SC10의 C/D 증거·E의 target 안전 수용·F/G 산출 및 근거 불가 시 종료를 명확화 |
| [유한 계획 사본](benchmarks/real-device-gate-g2-sc10/candidate/finite-authorization-and-validation-plan.json) | `/stages/4/objective_pass_criteria_ko/0` | 기존 E 전체 요건을 유지하면서 SP01–06/EC01–06의 사전 독립 수용과 F/G 비의존성을 추가 |

세 파일의 실제 before/after에서 unified redline을 메모리로 재생성했으며 제공된 patch와 **byte 단위로 동일**했다. patch는 적용하지 않았다. 후보가 편입 명세의 실제 hash를 본문에 고정한 것도 확인했다. P01·R01·SC10의 manifest 항목 각각 10·11·12개는 모두 실제 hash와 일치했다. 이 수는 신원 대조 항목이며 기술 proof 수가 아니다.

사본의 기존 상대 링크는 저자 metadata가 지정한 원 논리 목적지 `docs/` 기준으로 해석했다. SC10/E의 두 수정 값은 별도 후보 JSON과 고정 명세를 함께 대조했다. 역사 상태 문구나 사본을 현재 정본의 변경·적용으로 읽지 않았다. 정확한 before/after 값과 해시·삽입 위치는 [후보·redline 무결성](benchmarks/real-device-gate-g2-r02/candidate-and-redline-integrity.json)에 보존했다.

**R01-B01의 원 기준과 종결 근거**

원 finding은 [R01 finding 원장](benchmarks/real-device-gate-g2-r01/independent-findings.json)의 `/findings/0`, ID **R01-B01**, 원 severity **HIGH**다. 문제는 미구현 자체가 아니라, E에서 필요한 Samsung 안전 적용성 근거와 첫 승인 launch에서 알 수 있는 가용성 실패를 구별할 수용 기준이 없다는 점이었다. 정확 단말의 성공 통신을 사전에 실증하라는 새 의무를 부과한 finding도 아니었다.

수정은 그 원 기준을 충족한다. E는 사전 동결한 정확한 variant/build/API/선택 ABI 프로필에 대해 SP01–05의 안전성이 성립하는 근거를 판단한다. SP06은 각 OS/UID/credential/SELinux/ABI 전제를 해당 target 근거 또는 안전 비의존성 입증과 연결한다. vendor 차이가 안전 경계를 넓힐 수 있는데 영향이 미검증이면 안전 결측으로 거부한다. **그 차이가 오직 거부·기능 실패만 늘린다는 근거가 있는 경우에만** 가용성 미확정으로 남긴다.

| 요구 | 독립 판단 |
| --- | --- |
| 1. 안전 속성 | SP01–06으로 IP/우회 egress·peer/session·인증 전 전달·오류/fallback·한도·소유 backend·target 적용성을 특정했다 |
| 2. S23 FE 대응 근거 | SE04의 전제별 target 행렬과 인증 가능한 출처 또는 안전 비의존성 입증이 필요하다 |
| 3. 접촉 없는 증거 | SE01–04는 기존 식별 기록·C/D artifact/원자료·offline target 대응 자료다 |
| 4. 접촉이 필요한 증거 | SE06은 별도 F 등록, SE07은 별도 G 승인 launch의 산출물이며 E 입력이 아니다 |
| 5. 출처·캠페인 결합 | producer/role/시각·source/tool/APK/signer/manifest/ABI·정책·fixture·target·raw hash·수용 범위·plan digest에 결합한다 |
| 6. 객관적 E 기준 | EC01–06 전부 PASS만 허용하고 FAIL/MISSING/CONTRADICTED를 거부한다 |
| 7. 독립 책임 | 구현·실행 비참여 검토자가 SP/EC별 근거와 판정 범위를 기록한다 |
| 8. 만료·무효화 | exact scope·명시 시간창·단일 비갱신 세션과 변경/철회/상충/세대/만료 조건을 명시했다 |
| 9. 결측·상충 | unknown=safe·조건부 안전 PASS·미래 G 성공에 의한 보충을 금지한다 |
| 10. 근거 불가 시 종료 | offline 필수 안전 근거를 마련·수용할 수 없으면 terminal BLOCKED이며 새 사전 phone probe를 만들지 않는다 |

이는 “안전할 것”이라는 선언만으로 끝나지 않는다. 무엇을 고정하고 어떤 부정 입력·bytes·거부 경로를 대조할지, 어떤 근거가 빠지면 거부할지가 제시됐다. wrong/missing peer/session·credential 예외·재사용 입력·cap/cap+1·다른 backend/route·오류 시 fallback을 기존 C/D 범위의 검증 자료와 연결한다. 단, 그 자료를 **이번에 수집하거나 통과시킨 것은 아니다**. 기계 검사 통과와 비참여자의 증거 수용도 별도다.

[증거 수용 검토](benchmarks/real-device-gate-g2-r02/sc10-evidence-acceptance-review.json)에 10개 요구의 원문 locator, SP/EC 대응과 문서 판정 사례 9개를 기록했다. 사례는 규칙의 구별 가능성을 대조한 문서 검토이며 runtime 시험이나 실제 E 수용이 아니다.

소유자 선언은 기대 target scope의 입력이고, 단일 기기 운영 가정은 OS 독점 proof가 아니다. 저자의 hash·기계 검사·독립 수용·실제 owner 실행 권한은 서로 대체되지 않는다. SE01–05의 실제 target 자료·구현·원자료·독립 수용은 현재 미확보 또는 미수용이고, SE06/07도 미수집·미승인이다. 이 상태를 바꾸지 않은 채 **문서상 수용 경계만 충분히 정의됐다고** 판정한다.

원 R01 보고서와 finding JSON은 덮어쓰지 않았다. 당시 PARTIAL·OPEN 기록은 역사 원문으로 보존하며, 이번 종결 사건만 [독립 종결 기록](benchmarks/real-device-gate-g2-r02/r01-b01-independent-closure.json)에 추가했다. 원 F01의 기술 결함이나 실제 SC10 적격성을 종결한 것이 아니다.

**승인 순환 분석**

후보의 E 입력은 SE01–04이고 SE05는 E 판정 출력이다. SE05를 E 자신의 선행 증거로 요구하지 않는다. SE06은 F 연결/read-only grant 뒤의 기존 등록 결과이고 SE07은 G 첫 mutation grant·install checkpoint 뒤의 가용성 결과다. 어느 것도 E나 자기 단계의 최초 grant 선행 입력으로 소급 사용되지 않는다.

```text
기존 기록·별도 승인 C/D의 증거·offline target 행렬(SE01–04)
  → 비참여 E 판단(SE05)
  → 별도 owner F 연결/read-only grant
  → 기존 등록(SE06)·독립 보충 검토
  → 별도 owner G 첫 mutation grant
  → install 1회·독립 checkpoint·launch 1회(SE07)
```

화살표는 선행조건 관계이며 뒤 권한을 자동 발급하지 않는다. C/D의 증거 수집도 향후 B의 규범 효력과 각각의 별도 GO 뒤에만 가능하다. offline 자료 준비는 현재 phone을 관측했다는 뜻이 아니다. F는 사전 identity/build/ABI를 대조할 뿐 SC10 socket/네트워크/SELinux probe·marker·설치·launch를 추가하지 않는다. 불일치면 폐기하고 G를 거부한다.

E 필수 근거가 실제로는 사전 phone 접촉을 요구한다면, 후보는 그 접촉을 허용하지 않고 **BLOCKED로 종료**한다. 따라서 별도 사전 물리 증거 수집 절차가 빠져서 생기는 허가 순환이 없다. 필요한 새 절차나 trust/규범 변경을 원한다면 현재 후보 밖에서 별도 결정해야 하며 이번 검토는 이를 제안·승인하지 않는다.

도출한 의존 graph는 비순환이며 F/G의 산출물이 E로 들어가는 역방향 의존성은 없다. 이 결과는 문서의 의존성 검증이고 실행기의 동적 집행 증명이 아니다. [Stage E 권한 의존성](benchmarks/real-device-gate-g2-r02/stage-e-authorization-dependency.json).

**필요한 범위의 비회귀**

NC01–NC08의 원 JSON과 후보 본문 표 8행은 그대로다. R01의 **WEAKER 8 / EQUIVALENT 0 / STRONGER 0** 분류와 아직 효력 없는 예외 상태도 보존됐다. 다른 SC 11개와 D/F/G를 포함한 E 외 단계는 정확한 JSON 값으로 동일하다. 예산·고정 action·HC/EV 범위도 바뀌지 않았다. SC10의 원 요구와 `accepted_for_G2=false` 역시 유지된다.

명확화가 추가한 target 전제 비의존성 경로는 안전 증명의 면제가 아니다. 전제 값이 달라도 SP01–05가 유지된다는 근거의 독립 수용을 요구하며, 그 근거가 없으면 거부한다. 따라서 미검증 Samsung 차이를 운영 가정이나 가용성 항목으로 넘기는 새 예외가 아니다.

현재 원 F01은 **BINDING — UNRESOLVED**, G1은 **BINDING — UNCHANGED**다. 최초 단말 신원 결합·실제 승인 채널/수신자 결합·OS 강제 기기 격리의 세 비면제 보호와 상위 누적 요구를 유지한다. 고정 plan·외부 trusted digest·격리 test 앱/독립 signer/private synthetic·소유 합성 backend·fail-stop·자동 retry 금지·UNKNOWN_QUARANTINED·실제 위반 FAIL_VIOLATION과 F/G 별도 grant도 보존됐다. 제안된 G2 예외를 현재 유효한 규범으로 취급하지 않았다. [NC01–NC08 비회귀](benchmarks/real-device-gate-g2-r02/nc01-nc08-nonregression.json).

**소유자 결정 준비 상태와 한계**

결론은 **READY**다. 소유자는 검증한 수정 후보와 변함없는 여덟 규범 완화를 대상으로 한정 규범 결정·개정안 작성 여부를 판단할 수 있다. 이것은 G2 채택이나 적용을 대신하지 않는다. 향후 정확한 규범 승인·지정 적용·독립 일치 검증·효력 기록, C/D의 별도 승인·구현·수집·독립 수용, E 판단과 F/G grants가 각각 남는다. 실제 target 근거를 마련할 수 없다면 명세가 정한 BLOCKED 분기가 그대로 적용된다. [소유자 결정 준비 기록](benchmarks/real-device-gate-g2-r02/owner-decision-readiness.json).

**보존과 수행 범위**

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. 기존 tracked 수정 13개는 시작 상태로 보존했다. [시작 기준선](benchmarks/real-device-gate-g2-r02/preservation-before.json)은 기존 8,275개 경로·외부 frozen sidecar 5개를 기록한다. source lock 27개도 포함하며, 종료 대조에서 기존 bytes/mode/symlink·HEAD·Git index·staged 항목을 보존했다. index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged 항목 SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. [보존·정적 검증](benchmarks/real-device-gate-g2-r02/validation-and-preservation.json), [새 증거 manifest](benchmarks/real-device-gate-g2-r02/evidence-manifest.json).

이 보고서와 R02 dossier만 추가했다. 후보·binding 규범·실행 코드·B03·과거 finding·source lock을 변경하지 않았고, patch 적용·ADB(help/version 포함)·server socket 요청·USB/Android 열거·emulator·물리 기기 접근·APK 설치·production 접근은 모두 0이다. 원문/JSON/해시/의존성·보존만 검증했고 문서 한정 지시에 따라 npm/backend/Flutter runtime 빌드·테스트나 새 기술 proof 수용을 수행하지 않았다. T6.9를 재개하지 않았으며 R1/production 상태도 변경하지 않았다. 대형 임시 DB/build/cache 생성·삭제가 없어 산출물 정리는 NOT APPLICABLE이고 기존 파일을 삭제하지 않았다. reset/stash/clean/checkout/rebase/restage/commit/push는 없다. 보존 범위는 기록한 경로이며 ignored runtime/cache/production 전체 전수 감사를 뜻하지 않는다.

```text
REAL-DEVICE GATE G2-R02:
PASS

REVIEWER INDEPENDENCE:
SATISFIED

ORIGINAL G2 PROPOSAL:
PRESERVED

CORRECTED G2 CANDIDATE SHA-256:
1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb

R01-B01:
INDEPENDENTLY CLOSED

SC10 EVIDENCE REQUIREMENTS:
SUFFICIENTLY DEFINED

STAGE E ACCEPTANCE:
SUFFICIENTLY DEFINED

CIRCULAR AUTHORIZATION:
ABSENT

NC01-NC08:
PRESERVED

OWNER DECISION READINESS:
READY

G2 APPROVAL:
NOT GRANTED

G2 APPLICATION:
NOT PERFORMED

ORIGINAL F01:
BINDING — UNRESOLVED

EFFECTIVE G1:
BINDING — UNCHANGED

G1 TECHNICAL PROOFS ACCEPTED:
0 / 12

ADB OPERATIONAL DISPATCH:
BLOCKED

LIVE ADB CALLS:
0

EMULATOR OPERATIONS:
0

PHYSICAL DEVICE ACCESSED:
NO

REAL-DEVICE EXECUTION AUTHORIZATION:
NOT GRANTED

GIT INDEX:
PRESERVED

HISTORICAL EVIDENCE:
PRESERVED

COMMIT:
NONE

PUSH:
NOT PERFORMED

REPORT:
docs/real-device-gate-g2-r02-independent-sc10-review.md

FINAL VERDICT:
PASS — R01-B01 INDEPENDENTLY CLOSED; G2 READY FOR OWNER NORMATIVE DECISION

NEXT ACTION:
소유자는 고정된 수정 후보와 NC01–NC08에 대한 한정 규범 개정안 작성 여부를 별도로 결정하십시오.
```
