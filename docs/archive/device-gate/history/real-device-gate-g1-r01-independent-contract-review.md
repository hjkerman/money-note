# Real-Device Gate G1-R01 — G1 안전 계약 제안 독립 검토

**최종 판정: PARTIAL — SPECIFIC CONTRACT CORRECTIONS REQUIRED. 제안서 수용 전 특정 문서 수정이 필요하다.** 차단 지적은 3개이며 G1은 승인·적용하지 않았다. 세 필수 보장의 요구 속성은 정의돼 있으나 실제 구현·강제·독립 proof 수용은 모두 미완료다. 원 F01은 계속 유효하고 미해결이며, 운영 ADB dispatch·기기 연결·설치·실행은 계속 차단한다.

## 1. 독립성·권한·검토 범위

새 G1-R01 검토 세션은 G1 제안 작성 및 PREP02–PREP08 구현에 참여하지 않았다. 이번 세션에서도 구현·측정·운영에 참여하지 않았으며 문서 판정 권한만 사용했다. 검토자 독립성은 **SATISFIED**다. 이는 별도 인물의 실명이나 전자서명을 검증했다는 주장이 아니다. 저장소 근거를 읽었다는 사실은 과거 작성 참여를 뜻하지 않는다.

AGENTS·개발 산출물 관리·프로젝트 상태·도메인 모델·알려진 이슈와 architecture의 서버 authority 경계를 확인했다. 규범 근거는 [B §27/29](../../../t66/b/t66b-hot-cold-design.md), [C §26/38](../../../t66/c/t66c-delta-sync-protocol.md), [B11 적용](../../../t66f-b11-approved-amendment-application.md)과 [종결 재판정](../../../t66f-b11-post-amendment-closure-readjudication.md), [PREP01 연결 전 계약](../../../benchmarks/real-device-gate-prep01/physical-device-safety-contract.json), 원 [PREP03 F01](../../../benchmarks/real-device-gate-prep03/finding-register.json) 및 [PREP09 F01 결정](../../../benchmarks/real-device-gate-prep09/f01-architectural-blocker.json)이다. G1 제안은 이들 규범을 이미 바꾼 문서로 취급하지 않았다.

검토는 문서·JSON·hash·정적 source/AST·고정 공식 source 사본에 한정했다. 제품/시험/devicegate 모듈 import, 실제 ADB 호출(도움말/버전 포함), emulator, 물리 기기, APK 설치, backend/API 기동·요청은 0이다. G1 V1/V2 모형·lab도 실행하지 않았다. 이 세션의 정적 결과를 PR12의 기술 수용으로 사용하지 않는다.

## 2. 심사한 정확한 문서 신원

| 대상 | 정확 신원 |
| --- | --- |
| 제안서 | docs/real-device-gate-g1-safety-contract-proposal.md |
| 문서/계약 ID | G1-PROPOSAL-01 / F01-G1-DRAFT-01 |
| 제안서 SHA-256 | 2630cbc850c3c66fb2283160315691f656335e3d5c2681d71e54c9a747218b5a |
| 규범 초안 JSON SHA-256 | 71e149e1c38b5c38bdaf1f24a2fffd2635aefbd3a6c8d4970e21c79d9bf556ea |
| 미서명 승인 양식 SHA-256 | 60c06a7b406858b41c345cd10fe3107abfcf27994908435d9279f2f69c69cfb8 |
| 증거 manifest SHA-256 | 83b60029a97522f2e6978448e7bb050ad36a07d51f5b0750d0dd1f817b212bfd |
| 시작 HEAD | ebcbd54d90eeee194a04b9eea6367f446ee2fd28 |

정확 규범 초안은 [g1-contract-proposal.json](../../../benchmarks/real-device-gate-g1-proposal/g1-contract-proposal.json)의 `normative_clauses_if_separately_adopted`다. 본문 요약을 대신 승인 대상으로 만들지 않았다. 승인 양식 pinned input 12개, 제안 manifest 참조 25개, 카탈로그 52개와 제안 JSON 19개를 새로 대조했고 hash 불일치는 0이다. 승인자·시각·선택·범위는 공란이며 G1 채택/적용·후속 실행 권한은 false다. 이 형식 검증은 기술 보장이나 owner 서명이 아니다. [정확 신원 대조](../../../benchmarks/real-device-gate-g1-r01/proposal-identity-validation.json).

PREP05–PREP10 manifest 6개의 참조 523개도 일치했다. 이는 523개 독립 안전 보장이라는 뜻이 아니다. 현재 보호 source 9개는 제안 dossier와 동일하며 역사적 검증을 이번에 재실행했다고 집계하지 않았다. [정적 source·역사 대조](../../../benchmarks/real-device-gate-g1-r01/static-source-and-history-validation.json).

## 3. 원 F01과 보존해야 할 독립 종결

원 F01은 검증한 대상 신원과 실제 mutation 수신자의 원자적 결합 및 연결/server 세대 변경 때 권한 비승계를 요구한다. PREP03은 같은 serial의 transport 재등록과 마지막 조회 뒤 변화 모델을 발견했고, PREP05는 재등록 거부의 보강과 마지막 probe 반례의 존속을 구분했다. 원 반례는 모든 OS/ADB가 모의된 상태의 `changed-after-last-probe` 수신자에 모의 install이 도달한 기록이다. 실제 물리 단말 치환·공격 성공으로 확대하지 않는다. [보존 반례](../../../benchmarks/real-device-gate-prep09/regression/prior/f01-unclosed-interface-counterexample.json).

| 이력 | 안전 finding과 처분 |
| --- | --- |
| PREP05 | F01 OPEN; F02 고정 HTTP/redirect 경계 및 F03 최종 APK 구조/봉인 bytes 독립 종결. 취소 정리 중 실제 자식 잔존 N01 발견. |
| PREP06 | N01 수정 자체검증; F01 아키텍처 차단과 device authority 거부. 자체검증을 독립 수용으로 집계하지 않음. |
| PREP07 | N01 독립 종결. run/start basename 분류의 alias/wrapper 우회 FC01 발견; F01 원자 결합 미해결. fixture T01은 별도 낮은 심각도. |
| PREP08 | 중앙 무조건 거부와 시험 어댑터 격리 자체검증; FC01 독립 수용은 미부여. 원 F01 반례 존속. |
| PREP09 | FC01 독립 종결·N01/F02/F03 보존·T01 회귀 종결. F01과 실제 기기 실행 차단 유지. |
| PREP10 | 현재 보장을 확립한 운영 대안 없음; 조건부 B+C를 별도 계약 심의 후보로만 제시. |

[PREP05](real-device-gate-prep05-independent-remediation-reaudit.md), [PREP06](real-device-gate-prep06-adb-lifecycle-remediation.md), [PREP07](real-device-gate-prep07-independent-fail-closed-review.md), [PREP08](real-device-gate-prep08-adb-dispatch-boundary-remediation.md), [PREP09](real-device-gate-prep09-independent-dispatch-audit.md), [PREP10](../../../real-device-gate-prep10-f01-architecture-decision.md)의 판정과 범위를 그대로 보존한다.

G1은 원 F01을 이미 만족한다는 주장이 아니라 신뢰 가정·독립 초기 결합·실제 자원 수명·OS 도달 제한에 의한 조건부 계약으로 바꿀지 심의하는 제안이다. 이 차이는 명시돼 있다. GR05/06/07과 모든 PR의 면제 불가 설정 때문에 잔여 위험 서명이 초기 결합·channel·OS proof를 대신하는 문구는 발견하지 못했다. 원 계약의 대체는 미래의 exact 승인·redline·규범 적용 없이는 효력이 없다.

## 4. 혼동하면 안 되는 신원과 권한

| 개념 | 보장 범위와 한계 |
| --- | --- |
| P* 물리 단말 | owner가 의도한 실제 phone. serial/build의 값 일치나 혼자 연결된 상태만으로 최초 결합되지 않는다. |
| ADB serial | 선택/관측 이름. 물리 신원이나 연결 연속성·실행 승인이 아니다. |
| T* transport ID | 같은 server 안의 객체 선택 번호. server 교체 때 재사용될 수 있고 일부 TCP reconnect는 같은 객체를 유지한다. |
| U*/S*/C*/R* 세대 | USB incarnation·server 자원·실제 전달 channel·receiver boot/adbd 수명은 각기 다르며 숫자/UUID 기록만으로 강제되지 않는다. |
| H* 및 OS 강제 접근 | principal/namespace/device handle/socket/후손/FD 권한을 실제 제한한다. private port·node mount·major/minor allowlist만으로 완결되지 않는다. |
| 앱 identity | package·signer·component·private storage·APK bytes를 식별한다. 최초 설치 대상의 P* 결합을 소급 증명하지 않는다. |
| 실행 authorization | owner의 exact 세션/action 승인. USB debugging host key 허용이나 독립 proof PASS로 자동 생기지 않는다. |

이 구분은 G1-02–08과 제안 §2/3/6/7에 적절히 반영돼 있다. 고정 AOSP revision `1be2b4ff0af15538f7d64ec52f5a5f2ce666efdc` 사본의 `NextTransportId`, `transport_destroy`, `acquire_one_transport`, client selector/자동 server lifecycle을 대조했다. -s/-t는 AND 신원 검사가 아니며 그 source가 설치 binary와 대응한다는 proof는 없다. 이번에는 최신 도구/host 기능을 조사하거나 설치 binary의 지원성을 새로 주장하지 않았다.

## 5. 12개 조항별 평가

다음 평가는 현재 기술 수용이 아니라 제안 요구의 타당성에 관한 것이다. 정확 원문과 전 항목 평가는 [clause-review.json](../../../benchmarks/real-device-gate-g1-r01/clause-review.json)에 함께 보존했다. 공통 수용 권한은 owner의 규범/실행 범위 결정과 비참여 reviewer의 기술 proof 수용으로 분리된다. 공통 실패 처분은 미승인·결측 DENY, 무효화 REVOKED/OUTCOME_UNKNOWN, 자동 복귀/재시도 금지다.

### G1-01 — 적용 범위와 효력

의도·보장: 단일 owner·정확한 개인 단말·한 세션으로 효력을 제한한다. 신뢰 경계: 소유자 결정→규범 적용. 강제 수단: 정확 해시·redline·효력 기록과 기본 거부. 필수 proof: PR01.

수용 기준: 별도 채택과 적용이 없으면 원 F01 및 실행 DENY가 유지돼야 한다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 제안 요구로서 적절.

### G1-02 — 조건부 안전 속성

의도·보장: 등록된 P*에만 실제 도달과 허용 효과를 한정한다. 신뢰 경계: 물리 단말↔USB/명령 채널. 강제 수단: 독립 등록과 OS 도달 집합 제한을 동시에 강제. 필수 proof: PR03, PR04, PR05, PR06, PR11.

수용 기준: 두 수신자의 독립 효과 관측과 자원 수명 논증으로 비허용 대상 도달이 없어야 한다. 단독 목록은 부족하다. 조건부 대체 보장의 제안이며 원 F01 충족 proof는 아니다. 현재 원 F01을 대체하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 제안 요구로서 적절.

### G1-03 — 사전 승인과 초기 등록

의도·보장: 사전 신원/plan 승인 뒤 read-only 등록을 거쳐 첫 설치도 별도 확인한다. 신뢰 경계: 독립 식별 기록↔실제 U*/C*↔소유자. 강제 수단: 사전값·고정 transcript·진행 확인을 각각 gate로 적용. 필수 proof: PR01, PR03, PR11, PR12.

수용 기준: 잘못된 유일 정상 단말과 사후 key bootstrap은 거부하고 설치/marker 쓰기는 등록 수용 전 0이어야 한다. G1-R01-F01의 시점 표 보완이 필요하다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 특정 문서 보완 필요 — G1-R01-F01.

### G1-04 — 권한의 resource 결합

의도·보장: 권한을 실제 host/server/channel/USB/receiver 수명과 동결 action에 결합한다. 신뢰 경계: 이름·숫자↔실제 커널/서버 자원. 강제 수단: 지원 handle/lifetime 강제 경계; 문자열·PID·polling만으로는 불가. 필수 proof: PR02, PR04, PR05, PR07.

수용 기준: 같은 PID/port/TID/USB 주소가 재사용돼도 권한 승계가 없어야 한다. 구체 primitive는 아직 미선정이다. 조건부 대체 보장의 제안이며 원 F01 충족 proof는 아니다. 현재 원 F01을 대체하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 제안 요구로서 적절.

### G1-05 — 전면 매개와 transport 선택

의도·보장: 모든 도달 경로를 최소 실행 경계가 매개하고 재선택/자동 server 수명을 금지한다. 신뢰 경계: wrapper·후손·FD·다른 client↔device/socket. 강제 수단: 전용 principal/정책/VM 등 실제 OS 경계와 no-fallback 분석. 필수 proof: PR04, PR05, PR06.

수용 기준: 허용 밖 USB/socket/TCP·FD/ptrace·후손 경로가 실제 sink에서 거부돼야 한다. -t는 물리 인증이 아니다. 조건부 대체 보장의 제안이며 원 F01 충족 proof는 아니다. 현재 원 F01을 대체하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 제안 요구로서 적절.

### G1-06 — 단방향 폐기

의도·보장: 단절·세대 변화·취소·예산/감독 상실에 같은 세션 권한을 영구 폐기한다. 신뢰 경계: 감독·세대 사건↔제출 권한. 강제 수단: 단방향 폐기와 자원 재취득 금지; watcher 후 kill만으로는 불가. 필수 proof: PR04, PR05, PR07, PR10.

수용 기준: 폐기 후 새 제출과 같은 세션 복구가 없어야 한다. 진행 중 작업과의 경계는 G1-R01-F02 보완 대상이다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 특정 문서 보완 필요 — G1-R01-F02.

### G1-07 — 고정 action과 재시도 금지

의도·보장: literal argv/bytes/순서/예산을 동결하고 host 시도≤1 및 앱 replay=0을 요구한다. 신뢰 경계: 승인 manifest↔호스트 전송↔앱 수명. 강제 수단: 소비된 시도 기록·봉인 bytes·앱 재생성에도 유지되는 재실행 방지. 필수 proof: PR02, PR07, PR08, PR11.

수용 기준: 중복 host 요청과 실제 앱 process 재생성/중복 intent가 논리 시험을 재실행하지 않아야 한다. G1-R01-F03의 실제 검증 경로가 필요하다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 특정 문서 보완 필요 — G1-R01-F03.

### G1-08 — 허용 효과와 개인 데이터

의도·보장: 개인/production 접근을 금지하고 선언한 시험 효과와 필수 OS 기록만 허용한다. 신뢰 경계: test UID/signer/backend↔개인·production. 강제 수단: 최종 APK admission·private storage·합성 endpoint 및 부수효과 allowlist. 필수 proof: PR02, PR08, PR09, PR11.

수용 기준: package/signer/backup/권한/route와 실제 허용 부수효과가 명시돼야 한다. OS bookkeeping은 광역 정책 예외가 아니다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 제안 요구로서 적절.

### G1-09 — 진행 중인 원격 작업

의도·보장: 폐기 뒤 새 제출은 막고 이미 제출된 고정 채널 작업의 불명확 결과는 UNKNOWN으로 보존한다. 신뢰 경계: host 예약/제출↔원격 수신/완료. 강제 수단: 예약만으로 전송 허용 금지·채널 이동 금지·자동 재시도/정리 금지. 필수 proof: PR07, PR10.

수용 기준: UNKNOWN을 성공으로 바꾸거나 자동 readback/clear/uninstall을 하지 않아야 한다. PR07과 공통 경계는 G1-R01-F02 보완 대상이다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 특정 문서 보완 필요 — G1-R01-F02.

### G1-10 — 예산과 증거

의도·보장: 시간·용량·메모리·증거 상한을 동결하고 부분 증거를 보존한다. 신뢰 경계: 기기/host 자원↔journal·수용 판정. 강제 수단: bounded journal·hard/soft limit 구분·증거 실패 시 안전 중단. 필수 proof: PR10, PR11.

수용 기준: oversize/저장 실패/timeout은 terminal이고 부분 증거가 남아야 한다. receipt만으로 다른 대상 무효과를 증명할 수 없다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 제안 요구로서 적절.

### G1-11 — 독립 proof와 수용

의도·보장: 작성/구현/측정/운영 비참여자가 exact 경계와 실제 sink의 proof를 수용한다. 신뢰 경계: 자체검증↔독립 수용. 강제 수단: 비참여 선언·증거 해시·수용 범위와 판정 기록. 필수 proof: PR12.

수용 기준: 문서/모형/emulator PASS나 위험 서명이 실제 USB proof로 승격되지 않아야 한다. G1-R01-F03의 완결된 수용 단계가 필요하다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 특정 문서 보완 필요 — G1-R01-F03.

### G1-12 — 실행 전 별도 결정

의도·보장: 규범·구현·검증·연결·첫 mutation을 각기 별도 범위로 승인한다. 신뢰 경계: 설계 결정↔구현 권한↔실행 권한. 강제 수단: 분리된 결정 기록·정확 승인 범위·무권한 기본 거부. 필수 proof: PR01, PR12.

수용 기준: 어느 단계 PASS도 다음 단계 권한을 자동 발급하지 않아야 한다. 권한 분리 의도는 적절하며 G1-R01-F01의 시점 정합화가 필요하다. 현재 원 F01과 차단을 보존한다. 이 조항 자체가 기존 보호의 묵시적 면제를 부여하지 않는다. 부당한 기존 보호 면제는 발견하지 못했다. 객관적 시험/대조가 가능하지만 현재 enforcement는 미입증이다. 판정: 특정 문서 보완 필요 — G1-R01-F01.

## 6. 12개 필수 proof별 평가

12개를 모두 검토했으며 **이번 기술 수용은 0/12**다. 모든 proof는 최초 설치를 포함한 mutation 전에 필요한 부분이 수용돼야 한다. 메커니즘 증명과 실제 세션 값은 구별한다. 아래 권장 시점은 감사 해석이며 현 제안 JSON의 새 binding 규칙으로 적용하지 않았다. 정확 원문·수집 안전성·관측 독립성·실패 가시성·identity·재시작 무효화는 [mandatory-proof-review.json](../../../benchmarks/real-device-gate-g1-r01/mandatory-proof-review.json)에 기록했다.

### PR01 — 승인 provenance·계약 우선순위

주장: 권한 provenance와 규범 효력을 수립한다. 수집: 문서·해시·redline·미부여 상태의 정적 대조로 수집 가능하다. 독립성: 직접 승인 기록과 독립 문서 대조; 저자 요약만 사용하지 않는다.. 실패 관측: 승인 부재/해시·범위 불일치/무권한 허용이 드러난다..

수용 기준: 정확 결정·적용 범위·권한 부재 시 DENY가 일치해야 한다. 시점: 연결 전; 세션 승인도 해당 단계 전에 필요. 무효화: 소유자 결정/규범/plan 변경 시 재수용. 현재 제안 상태: `CURRENT_DOCUMENTATION_ONLY`; 요구 정의는 적절하나 실행 증명 미수용.

### PR02 — artifact/tool 신원

주장: 실제 tool/source와 APK/서명/fixture/전송 bytes의 신원을 고정한다. 수집: 기기 없이 bytes·출처·봉인 및 selector/lifecycle 분석을 수집할 수 있다. 독립성: 독립 해시·빌드 대응 또는 해당 binary에 직접 적용되는 독립 수명 proof; hash만으로 source 대응을 가정하지 않는다.. 실패 관측: 치환·signer 불일치·source/binary 대응 결측이 드러난다..

수용 기준: 실제 사용할 binary 의미와 final APK/signer/fixture/봉인 bytes가 같은 manifest에 귀속돼야 한다. 시점: 메커니즘/아티팩트 수용은 연결 전. 무효화: 도구/APK/서명/fixture/source 변경 시 무효. 현재 제안 상태: `HISTORICAL_PARTIAL_ONLY`; 요구 정의는 적절하나 실행 증명 미수용.

### PR03 — 최초 등록과 bootstrap 결합

주장: 의도한 물리 P*를 실제 U*/C*와 최초 결합한다. 수집: 사전 독립 식별 근거와 수집 메커니즘은 기기 없이 검토한다. 실제 transcript는 별도 승인된 고정 read-only 등록에서만 가능하며 이번에는 수집하지 않는다. 독립성: owner-local 식별과 wire 대응·실제 자원 연속성을 독립 대조; 단독 목록/케이블/소유 진술만으로는 불가. 실패 관측: 같은 serial/build의 잘못된 유일 정상 단말 또는 대응 근거 결측이면 거부돼야 한다..

수용 기준: 설치/marker 없이 정확 P* 결합과 wrong-singleton 거부, probe 뒤 교체 차단을 입증해야 한다. qualified mechanism은 아직 없다. 시점: 메커니즘은 연결 전; 실제 transcript와 독립 수용은 첫 mutation 전. 무효화: USB/channel/server/boot/adbd 세대 변경·프로세스 재시작 후 세션 재사용 금지. 현재 제안 상태: `OPEN_NO_QUALIFIED_MECHANISM`; 특정 보완 G1-R01-F01.

### PR04 — USB incarnation 강제

주장: USB 재열거/주소 재사용이 권한을 승계하지 못함을 수립한다. 수집: 별도 승인된 비개인 lab에서만 실제 OS/resource 대조를 수집할 수 있다. 실제 phone 적합성은 별도다. 독립성: 두 target의 독립 effect sink와 열린 handle·driver/kernel 수명 관측. 실패 관측: 새 node/major-minor·주소 재사용·reset에서 새 자원 취득 또는 비허용 효과가 관측되면 실패.

수용 기준: 정확 정책/커널/backend에서 새 incarnation 취득과 비허용 target effect가 0이어야 한다. 음성 표본만으로 전면 증명을 대신하지 않는다. 시점: 일반 강제 경계는 연결 전; 해당 U* 연결은 첫 mutation 전. 무효화: 단절/reset/재열거/OS 정책 변경·executor 재시작 시 무효. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F01.

### PR05 — server/channel/transport 결합

주장: 확인한 server와 실제 service channel의 자원 세대가 같음을 수립한다. 수집: 고정 source/binary 분석 및 승인된 비개인 lab에서 socket 교체를 조사할 수 있다. 독립성: 실제 peer/socket/process resource 관측과 고정 binary no-fallback 분석; PID 조회와 독립. 실패 관측: 같은 PID/port/TID로 교체하거나 auto restart/reexec가 발생하면 실패.

수용 기준: 실제 전달 채널이 승인 server 자원에 결합되고 새 peer/ID 재사용으로 전달이 이어지지 않아야 한다. 시점: 일반 server/channel 경계는 연결 전; 실제 S*/C*/T*는 첫 mutation 전. 무효화: server/client/channel 교체·재시작·재연결 시 무효. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F01.

### PR06 — OS 전면 매개와 우회 불가

주장: 허용 장치 집합의 OS 강제 전면 매개를 수립한다. 수집: 정확 recipe 한 개의 승인된 lab에서만 수집한다. 무단 host 정책 변경은 금지다. 독립성: 독립 경계/FD/socket 관측과 허용·비허용 두 effect sink; wrapper 자기 보고로 대체 불가. 실패 관측: 다른 principal·ptrace/FD·다른 socket/TCP/mDNS·후손 우회가 실제 sink에 닿으면 실패.

수용 기준: 일반 process/후손의 허용 밖 자원 접근=0이고 신뢰 root와 정책 권한 범위가 명시돼야 한다. 시점: 메커니즘은 연결 전; 실제 세션 정책 상태는 첫 mutation 전에 재귀속. 무효화: principal/namespace/capability/mount/정책/열린 FD 집합 또는 프로세스 세대 변경 시 무효. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F01.

### PR07 — 폐기·host 1회 시도·감독 수명

주장: 폐기와 감독 수명이 새 제출을 막고 host action 시도≤1임을 수립한다. 수집: 기기 없는 모형과 별도 승인 lab에서 취소·감독 상실 이력을 수집할 수 있다. 독립성: 실제 sink·전송 사건·독립 자식/후손 수명과 marker 관측; 내부 revoked=true만으로는 부족. 실패 관측: 예약 후 전송·중복·죽은 supervisor 뒤 action·새 channel 전달이 드러나면 실패.

수용 기준: 다른 target 효과=0·폐기 후 새 제출=0·action 시도≤1. 이미 수신된 고정 action의 후속 완료는 UNKNOWN으로 분리하도록 PR07 문구 보완이 필요하다. 시점: 메커니즘 수용은 연결 전; 실제 세션 전 기간 강제. 무효화: 취소/timeout/감독·프로세스 상실/세대 변화는 terminal이며 복원 불가. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F02.

### PR08 — 앱 격리와 자동 재실행 방지

주장: 앱/package/signer/private store 격리와 process/intent replay 방지를 수립한다. 수집: 정적 APK 검사는 기기 없이 가능하다. 실제 lifecycle proof는 별도 승인된 격리 Android 경로가 필요하며 현재 유한 계획에는 없다. 독립성: 최종 APK 분석과 별도 관측자가 논리 시험 효과를 계수하는 실제 process 재생성/중복 intent 관측. 실패 관측: 허용 밖 component/권한/backup·signer 불일치·같은 시험의 자동 재실행을 관측하면 실패.

수용 기준: 최종 artifact의 격리·논리 replay=0, 승인 phone에서 fresh package 부재가 모두 필요하다. 실제 앱 proof 없이 model PASS로 수용할 수 없다. 시점: 앱 메커니즘/최종 artifact는 연결 전; fresh package 부재는 승인 등록 안에서 첫 설치 전. 무효화: 앱 bytes/서명/OS/lifecycle 정책 변경 시 증명 무효; process 재생성으로 one-shot 상태가 복원돼서는 안 됨. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F01, G1-R01-F03.

### PR09 — 합성 backend·네트워크

주장: phone/host 경로가 정확 합성 backend에만 도달함을 수립한다. 수집: 새 합성 환경과 비허용 decoy로만 수집한다. production sink에 실제 요청을 보내면 안 된다. 독립성: 비허용 합성 sink hit 계수·listener/accepted socket 소유와 route/egress 독립 관측. 실패 관측: redirect/다른 origin/생산 fallback·종단 소유 결측·예산 초과면 실패.

수용 기준: 고정 phone-compatible 경로와 host egress의 비허용 요청=0, no redirect/fallback이 exact artifact/route에서 입증돼야 한다. 기존 F02는 host HTTP 범위다. 시점: 일반 경로/아티팩트는 연결 전; 실제 세션 종단/route 귀속은 첫 mutation 전. 무효화: backend/네트워크 namespace/route/종단 process 또는 endpoint 변경 시 무효. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F01, G1-R01-F03.

### PR10 — 자원·증거·UNKNOWN 처분

주장: 유한 자원·증거·실패/UNKNOWN의 보수적 처분을 수립한다. 수집: host journal의 합성 oversize/쓰기 실패/응답 유실 모형·허용 lab에서 수집 가능하다. 독립성: 독립 byte/time/파일 계수와 결과 상태; app가 보고한 PASS만 사용하지 않는다.. 실패 관측: 부분 증거·저장 실패·timeout이 관측 가능해야 하며 결측은 성공 아님.

수용 기준: 고정 hard/soft 한계·partial evidence·UNKNOWN terminal·자동 재시도/cleanup=0이 필요하다. 실제 phone 수치는 사전 근거와 등록 내 확인을 구별해야 한다. 시점: 정책/예산은 연결 전; 승인 세션 실제 여유 확인은 첫 mutation 전. 무효화: 예산/증거 저장 실패는 즉시 terminal; 재시작 후 같은 세션 재실행 불가. 현재 제안 상태: `OPEN`; 특정 보완 G1-R01-F01, G1-R01-F02.

### PR11 — 명령·효과 allowlist 완결성

주장: 명령/bytes/효과 allowlist와 순서가 완결됨을 수립한다. 수집: 연결 전에 정적 manifest·artifact·literal argv·입력·경로를 대조할 수 있다. 독립성: 별도 reviewer가 source/bytes와 승인 manifest를 대조; template 공란을 실행 중 채우지 않는다.. 실패 관측: 미승인 명령/동적 probe·공란·부수효과 누락·계획 변경이 드러난다..

수용 기준: 고정 등록 조회/설치/시작/수집의 실제 argv·입력 bytes·경로·순서·예산과 OS bookkeeping이 모두 동결돼야 한다. cleanup은 제외한다. 시점: 모든 literal action/계획은 연결 전. 무효화: plan/source/argv/fixture/경로/예산 변경이면 새 결정 필요. 현재 제안 상태: `OPEN`; 요구 정의는 적절하나 실행 증명 미수용.

### PR12 — 독립 통합 수용

주장: 동일한 artifact/OS에서 모든 기술 증명과 기존 종결의 통합 독립 수용을 수립한다. 수집: 사전 증거 묶음은 기기 없이 심사 가능하다. 실제 U*/C* 등록 증거는 승인 read-only 등록 후 심사하며 첫 mutation을 보류한다. 독립성: 제안·구현·측정·운영 비참여 reviewer의 명시 판정; 구현 PASS와 별도. 실패 관측: 하나의 필수 proof/identity/독립성/실제 sink 근거가 없으면 미수용으로 드러나야 한다..

수용 기준: PR02–PR11의 exact artifact/OS 대응·proof 한계·N01/F02/F03/FC01 보존을 모두 수용해야 한다. Stage D와 연결 후 보충 수용의 출구가 G1-R01-F01·G1-R01-F03 보완 대상이다. 시점: 사전 통합 수용은 연결 전; 인스턴스 보충 수용은 첫 mutation 전. 무효화: 증거가 귀속된 source/artifact/OS/runtime 세대가 달라지면 종전 수용을 재사용하지 않음. 현재 제안 상태: `PENDING_INDEPENDENT_REVIEW`; 특정 보완 G1-R01-F01, G1-R01-F03.

모든 증거는 PR02 source/tool/APK/fixture hash와 정확 OS/kernel/driver/backend/정책, 관련 U*/S*/C*/T*/R* 및 관측자에 귀속돼야 한다. 현재는 보존 source hash만 대조했고 live runtime·OS/device identity는 수집하지 않았다. 이런 identity가 없는 실험이나 실제 sink와 분리된 구현 내부 flag는 안전 보장 proof로 수용할 수 없다. 반복 probe·watcher·사후 kill은 완전 매개나 실제 전달 전 권한 폐기의 대체물이 아니다.

## 7. 면제 불가 보장 세 가지

| 보장 | 요구 정의 | 현재 기술 근거 | 계속 닫을 gate |
| --- | --- | --- | --- |
| 최초 물리 단말 결합 | DEFINED | qualified bootstrap mechanism·실제 transcript·독립 수용 없음 | 현재는 연결/등록부터 차단. 미래 사전 메커니즘 수용/owner 연결 승인을 얻더라도 인스턴스 PR03 미수용이면 첫 APK 설치·marker·launch 등 모든 mutation 차단 |
| 승인 채널과 실제 명령 수신자 결합 | DEFINED | actual peer/resource lifetime·no fallback·USB 재열거 차단·폐기 enforcement proof 없음 | 운영 ADB dispatch와 기기 연결/첫 mutation 차단; PR07 판정 경계 정합화도 필요 |
| 허용 기기 집합의 OS 강제 격리 | DEFINED | 현 host에 자격검증된 recipe·정책/권한/자원 신원·실제 두 sink 관측 없음 | 기기 노출/연결과 운영 dispatch 차단; 기존 FC01의 Python 지원 경로 거부를 host OS sandbox로 간주하지 않음 |

세 항목의 **DEFINED는 요구 속성의 정의만 의미하며 구현·입증·수용 완료를 뜻하지 않는다.** 초기 P* 식별, actual channel 수신자 결합, 허용 기기 집합의 OS 강제를 어느 하나라도 확립하지 못하면 운영 dispatch·기기 노출/연결·첫 mutation은 열 수 없다. 미래에 사전 메커니즘과 연결 범위만 별도 승인됐더라도 실제 등록 proof가 없으면 설치부터 금지다. GR01–04의 한정 위험 결정을 GR05/06의 필수 증명 결측에 전용할 수 없다. [비면제 보장 평가](../../../benchmarks/real-device-gate-g1-r01/nonwaivable-safety-review.json).

## 8. 14개 거부 기준 평가

아래는 [원 RJ01–14](../../../benchmarks/real-device-gate-g1-proposal/approval-and-rejection-options.json)의 실제 문구에 대한 평가다. 직접 명시한 항목과 다른 기존 조항/proof가 보완하는 항목을 구별했다. 모든 조건은 해당 시 차단 유지이며, 이번 검토가 실행 예외를 부여하지 않는다.

| ID | 원 거부 조건 | 평가·범위 |
| --- | --- | --- |
| RJ01 | proposal-only 지시를 계약 채택/실행 승인으로 사용 | 현재 proposal-only 지시를 채택/실행 권한으로 사용하는 경우를 직접 거부한다. 충분 |
| RJ02 | 실제 USB incarnation/최초 P* 등록이 불명확하거나 설치 뒤 key로 소급 bootstrap 인증 | 초기 P*/USB incarnation 불명확과 사후 key bootstrap을 직접 거부한다. 충분 |
| RJ03 | -s/-t·one-device·단일 목록·PID polling을 원자적 binding/OS isolation으로 수용 | serial/ID/one-device/단독 목록/PID polling의 잘못된 동치화를 직접 거부한다. 모든 stale/ambiguous 상태를 별도로 열거한 조항은 아니다. 부분 명시; G1-03/04·PR03–PR06으로 보완 |
| RJ04 | 서버/USB 주소/ID/receiver 세대가 바뀌어도 기존 승인 재사용 | server/USB 주소/ID/receiver 세대 변경 뒤 권한 재사용을 직접 거부한다. 단절/reset/재열거의 명시는 G1-06에 있다. 충분한 관련 기준; 사건별 직접 명시는 G1-06 |
| RJ05 | auto server start/restart/reexec·TCP reconnect·fallback·부모 밖 후손 ADB 경로 허용 | 자동 server 수명·TCP reconnect·fallback·부모 밖 후손의 ADB 경로를 직접 거부한다. 모든 잔존 자식 자체의 금지는 명시하지 않는다. N01 자식 잔존은 PR07/PR12·기존 종결과 함께 판정 |
| RJ06 | OS 강제 경계 대신 저장된 boolean/UUID/검사 후 kill만 사용 | OS 강제 경계를 boolean/UUID/kill로 대체하면 직접 거부한다. namespace/capability/ptrace/FD escape 목록은 PR06/V2에 있다. 탈출·추가 장치 도달은 G1-05·PR06과 함께 판정 |
| RJ07 | 명령/bytes/manifest/budget 미정 또는 연결 후 source/APK/계획 변경 | 미정 명령/bytes/manifest/budget와 연결 후 source/APK/plan 변경을 직접 거부한다. 처음부터 잘못된 signer를 별도 문구로 열거하지 않는다. 서명/초기 신원 불일치는 PR02/PR08·F03을 함께 적용 |
| RJ08 | 첫 mutation 전 owner 확인 없음·앱 재생성/중복 intent 자동 replay | 첫 mutation owner 확인 결측과 앱 재생성/중복 intent replay를 직접 거부한다. 충분; 실제 증거 경로는 G1-R01-F03 보완 |
| RJ09 | production/개인 데이터/광역 로그/공유 저장소·특별 권한/기기 정책 변경 필요 | production/개인 자료·광역 로그·공유 저장소·특별 권한/정책 변경 필요를 직접 거부한다. 비생산 decoy로의 모든 네트워크 이탈을 따로 열거하지 않는다. backend/네트워크 이탈은 PR09·F02와 함께 판정 |
| RJ10 | UNKNOWN을 성공 처리하거나 retry·clear/uninstall·추가 probe로 자동 회복 | UNKNOWN의 성공 승격·자동 retry/cleanup/probe 회복을 직접 거부한다. 취소 뒤 모든 host 자식의 잔존 문제를 직접 명시한 것은 아니다. 충분한 UNKNOWN 기준; N01 보존을 별도 대조 |
| RJ11 | 등록/강제 경계/전면 매개 proof 결측을 residual-risk 서명으로 면제 | 등록/강제 경계/전면 매개 proof 결측을 위험 서명으로 면제하면 직접 거부한다. 그 밖의 모든 증거 결측을 이 한 조항이 열거하지는 않는다. 모든 PR 결측의 거부는 전체 proof gate 및 G1-10/11로 판단 |
| RJ12 | 문서/모형 PASS나 저자 self-review를 독립 OS/phone 검증으로 집계 | 문서/모형/저자 검토를 독립 OS/phone 검증으로 집계하면 직접 거부한다. diagnostic adapter를 실제 활성화하는 행위의 명시 항목은 아니다. 실행 어댑터 우회는 G1-05·PR06·FC01 보존과 함께 판정 |
| RJ13 | hard realtime remote stop·exactly-once·개인 데이터 손실 0의 미입증 주장 | 미입증 hard realtime stop·exactly-once·손실 0 주장을 직접 거부한다. 충분; PR07/G1-09 경계 정합화는 G1-R01-F02 |
| RJ14 | 기존 F01/역사 증거/source locks/index를 수정하거나 문구 변경을 기술적 수정 완료로 표현 | 원 F01/역사 증거/source lock/index 변경과 문서 변경의 기술 해결 포장을 직접 거부한다. 충분 |

| 요청된 위험 | 직접 관련 RJ | 다른 기존 요구 | 실제 포함 범위 |
| --- | --- | --- | --- |
| 신원 결측/불일치 | RJ02 | G1-03/04, PR03 | 직접 명시 |
| stale/ambiguous transport | RJ03/04 | G1-04/06, PR04/05 | 세대/오인 규칙은 있으나 모든 ambiguous 상태를 직접 열거하지 않음 |
| ADB server 재시작 | RJ04/05 | G1-05/06, PR05 | 직접 명시 |
| USB 단절/재열거 | RJ02/04 | G1-06, PR04 | 단절/reset 사건은 조항/증명에 명시 |
| 추가 비허용 장치 | RJ06 관련 | G1-02/05, PR06, V2 음성 1 | 14개 자체에는 명시적 추가 장치 항목 없음 |
| OS 격리 실패 | RJ06 | G1-05, PR06 | 대체 수단 거부는 직접 명시 |
| privilege/namespace escape | RJ06 관련 | PR06, V2 음성 4 | 14개 자체에는 구체 탈출 항목 없음 |
| diagnostic adapter 우회 | RJ05/06/12 관련 | G1-05, PR06/12, FC01 | RJ12는 증거 집계 오류이며 런타임 어댑터 금지와 구별 |
| 취소 후 자식 생존 | RJ05/10 관련 | PR07/12, N01 | 14개 자체에는 자식 생존 금지의 명시 항목 없음 |
| network/backend 격리 실패 | RJ09 관련 | PR09, F02 | production 필요 거부와 모든 비허용 endpoint 이탈은 구별 |
| APK 신원/signing 불일치 | RJ07 관련 | PR02/08, F03 | 14개 자체에는 초기 signer 불일치 명시 항목 없음 |
| 증거 결측 | RJ11/12 | G1-10/11 및 모든 PR gate | 직접 열거된 것은 핵심 proof 결측/부정 집계; 전체 결측은 합성 gate |
| 미승인 명령 | RJ07 | G1-07, PR11 | 직접 명시 |
| 필수 초기 증명 실패 | RJ02/11 | PR03 및 GR05 | 직접 명시 |

추가 장치·권한/namespace 탈출·진단 adapter의 runtime 우회·취소 후 자식 생존·비허용 비생산 endpoint·처음부터 잘못된 signer·모든 증거 결측이 RJ14개에 각각 직접 열거돼 있다고 주장하지 않는다. 전체 G1 조항과 모든 PR의 합성 gate는 이들을 별도로 요구하므로 곧바로 허용된 상태라는 뜻도 아니다. 관련 RJ에 기존 PR/FC01/N01/F02/F03 교차참조를 넣는 것은 선택적 편집 개선이며 새 차단 finding으로 세지 않았다. [전체 평가](../../../benchmarks/real-device-gate-g1-r01/rejection-criteria-review.json).

## 9. 승인 권한과 유한 단계

| 단계 | 기존 대응 | 진입→출구 | 권한 | 평가 |
| --- | --- | --- | --- | --- |
| A 계약 검토와 소유자 결정 | D0 + O1/O2/O3/O4 | 정확 dossier·독립성·원 F01 우선순위 → 독립 문서 판정 1개와 소유자의 별도 결정; 수정본 hash/redline/목적지 없는 O4 적용 불가 | 검토자는 문서 판정, 소유자는 선택/규범 범위 결정. 구현·검증·기기 접근 권한 없음 | PASS |
| B 별도 승인된 아키텍처 구현 | G1-12 + 승인 양식 implementation | 별도 exact 구현 범위·source/artifact/OS recipe/예산 승인 → 한 구현 후보와 증거 신원 동결; 기술 proof 수용과 구별 | 소유자 구현 범위 승인; 구현자는 결과 제출만. 계약 채택은 구현 승인 아님; 구현 PASS는 독립 수용 아님 | PASS |
| C 호스트와 격리 Android 검증 | V1 + V2; 실제 앱 lifecycle 경로 결측 | 검증 범위와 host/lab 변경을 별도 승인; 기존 F01/FC01 보존 → V1 모형 1/12 trace/3600초/10MiB, V2 recipe 1/음성 8/5400초/20MiB. 실제 PR08 증거 경로의 유한 상한은 미정 | 소유자 별도 검증 승인; 구현 PASS와 독립 관측/수용 구별. V1/V2 PASS는 phone/USB proof 및 기기 접근 승인 아님 | PARTIAL |
| D 독립 기술 proof 수용 | G1-11 + PR12; 유한 계획에 별도 결과 경계 연결 부족 | PR02–PR11의 동일 artifacts/OS/실제 sink 증거와 비참여 선언 → 연결 전 기술 수용과 등록 후 인스턴스 보충 수용을 구별한 명시 판정·hash 필요 | 제안/구현/측정/운영 비참여 기술 검토자. 독립 PASS는 owner 연결/실행 권한을 자동 발급하지 않음 | PARTIAL |
| E 명시적 실기기 세션과 첫 mutation 승인 | V3 + 연결/등록 및 첫 mutation의 두 인간 gate | 유효한 규범·사전 독립 수용·정확 manifest·owner 연결 승인; 등록 후 실제 P*/U*/C* 증명과 별도 첫 mutation 확인 → 고정 세션 1회, 자동 retry 0; 완료/폐기/UNKNOWN 중 하나로 종료 | 소유자만 연결/첫 mutation 허용; 실제 등록 proof 수용은 별도 검토자. 현재 연결·등록·첫 설치·실행은 모두 미승인 | PARTIAL |

**권한 분리: PASS. 유한 검증 계획 완결성: PARTIAL.** 설계 승인→구현 허용, 구현 PASS→독립 proof 수용, 독립 PASS→기기 접근의 자동 전환은 제안 문구에 없다. G1-12와 미서명 양식의 별도 권한 필드는 적절하다. G1-R01-F01 지적은 이 권한 분리가 이미 무너졌다는 판정이 아니라 proof 시점/기계 gate의 정밀도 결함이다.

D0는 1회·최대 2시간, V1은 모형 1개·12 trace·1시간·10MiB, V2는 recipe 1개·음성 8개·90분·20MiB, V3는 고정 세션 1개·자동 retry 0으로 상한이 있다. 실패/불확실/시간초과는 종료이고 자동 수정·추가 trace·다른 recipe·재감사를 예약하지 않는다. 단, 실제 앱 lifecycle proof와 독립 통합 수용의 입력/출구/한도 연결은 G1-R01-F03 보완 전에는 완결되지 않는다. 제안서의 V2를 emulator 단계라고 부르는 것은 사실과 다르다.

필수 지원 primitive나 OS recipe를 한정 범위에서 확립하지 못하면 후보를 BLOCKED/기각으로 반환해야 한다. 추가 PREP 감사의 무한 열이나 개인 단말에서 먼저 시도한 뒤 보완하는 경로는 요구하지 않는다. 최소 보완은 기존 proof를 단계별로 배치하고 빠진 실제 앱 증거 경로 하나와 독립 수용 기록을 유한 범위로 명시하는 것이다. 기존 12개 proof나 기본 아키텍처를 새 프로젝트로 확대하지 않는다. [단계 평가](../../../benchmarks/real-device-gate-g1-r01/authority-and-stage-review.json).

## 10. 채택 준비를 차단하는 구체 지적

### G1-R01-F01 — 연결 전 자격검증과 연결 후 개별 증명의 수용 시점을 기계 판정에서 분리하지 않음


근거: required-proof-matrix.json#/proofs; device-admission-conditions.json#/preconnection_conditions_ko/1; approval-and-rejection-options.json#/execution_admission_rule; 제안서 §9. §9는 기기 없는 메커니즘 자격검증과 승인 연결 내 실제 값을 구별한다. 그러나 12개 proof의 execution_gate는 모두 MUST_PASS_OR_DEVICE_ACCESS_DENIED이고 PR03에는 아직 존재하지 않는 U*/C* transcript가 포함된다. 접근 조건은 연결 전 가능한 proof라는 부분집합을 열거하지 않고, 단일 실행식은 첫 mutation 확인까지 요구한다. 이 실행식을 연결 허가식으로 사용하면 순환하고, 연결 전 가능한 항목을 구현자가 임의 선택하면 증명을 누락할 수 있다.

정적 반례: 정상적인 연결 후 PR03 transcript를 수집하려 해도 전체 PR03 미수용으로 DEVICE_ACCESS_DENIED가 된다. 반대로 이 값을 임의 예외 처리하면 PR04–PR06 미수용 상태까지 등록 허가로 잘못 취급할 수 있다. 두 경우 모두 문서/기계 판정 간 모호성의 정적 사례이며 실제 우회 관측이 아니다.

최소 수정: 12개 ID를 늘리지 않고 각 proof에 연결 전 메커니즘 수용 부분과 연결 후 첫 mutation 전 인스턴스 수용 부분, 증거·수용자·무효화 조건을 명시한다. 연결/고정 read-only 등록 허가식과 설치 포함 첫 mutation 허가식을 별도로 명명한다. §9의 구별을 JSON에도 그대로 반영하고 최종 실행식의 적용 범위를 첫 mutation으로 한정한다.

종료 기준: 모든 PR01–PR12에 수용 시점과 책임이 존재하고, 필요한 사전 증거 하나라도 결측이면 연결 거부, 인스턴스 증거 하나라도 결측이면 모든 mutation 거부로 판정돼야 한다. 연결 전에 U*를 관측했다는 허위 증거를 요구하지 않는다. G1-12의 권한 분리가 이미 무너졌다는 finding이 아니다. 본문의 안전 의도는 인정하며 현재 차단은 유효하다.

### G1-R01-F02 — PR07의 효과 전 폐기와 G1-09의 이미 제출된 작업 허용에 공통 판정 경계가 부족함


근거: required-proof-matrix.json#/proofs/6/obligation_ko; required-proof-matrix.json#/proofs/6/required_evidence_ko; g1-contract-proposal.json#/normative_clauses_if_separately_adopted/8; 제안서 §8; bounded-validation-plan.json#/V1/traces/9. PR07은 취소에서도 새 effect 전달 금지와 실제 effect 전 권한 소멸을 요구한다. G1-09와 §8은 폐기 전 제출/버퍼링된 bytes 및 원격 작업의 이후 완료를 허용한다. 새 effect가 새 action의 effect인지, 이미 제출된 action이 나중에 발생시킨 effect까지 포함하는지 proof 원문만으로 판정이 달라진다. §8의 RESERVED/실제 제출 구별은 유용하지만 PR07 및 T10 수용 기준에 일관되게 연결되지 않았다.

정적 반례: 취소 전에 승인된 고정 수신자가 설치 요청을 받았고 취소 후 package-manager 기록이 생성되는 단일 이력은 G1-09에서 허용 가능한 UNKNOWN이다. PR07을 모든 후속 effect=0으로 읽으면 같은 이력을 실패 처리한다. 반대로 RESERVED만으로 이미 제출된 작업이라 인정하면 미전송 action을 취소 뒤 전송하는 잘못된 허용이 생긴다.

최소 수정: 이미 시작된 동일 action/동일 receiver/channel의 허용 잔여 bytes와 이후 새 제출을 구분하는 하나의 판정 시점을 PR07·G1-06/09·T10에 연결한다. RESERVED는 예외가 아니며 새 channel/receiver로 이동한 bytes는 항상 금지한다. 다른 대상 effect=0과 취소 후 새 제출=0을 독립 수용 기준으로 쓰고 기존 수신 작업의 이후 완료는 UNKNOWN 처분으로 따로 기록한다.

종료 기준: 제출 전 취소, 예약 후 미전송 취소, 이미 수신된 action의 취소 후 완료를 같은 판정 정의로 구별할 수 있어야 한다. 어떤 경우에도 다른 대상 전달이나 새 자원 취득을 허용하지 않는다. 하드 실시간 원격 중단을 새로 요구하지 않는다. 이미 수신한 작업의 완료 허용 자체가 F01 위반이라는 finding이 아니다. PREP10도 같은 한계를 명시했다.

### G1-R01-F03 — 실제 앱 수명 증명과 독립 수용까지 닫히는 유한 검증 경로가 불완전함


근거: bounded-validation-plan.json#/V1; bounded-validation-plan.json#/V2/scope_ko; bounded-validation-plan.json#/V3/scope_ko; required-proof-matrix.json#/proofs/7; required-proof-matrix.json#/proofs/11; mobile/lib/main_devicegate.dart:16. V1의 T12는 모형이며 V2는 Android와 emulator를 명시적으로 제외한다. V3는 선행 proof 수용 뒤의 개인 단말 한 세션이다. PR08이 요구하는 최종 APK의 process 재생성/중복 intent 자동 replay 금지에 대한 실제 앱 수명 증거를 개인 단말 이전에 수집할 단계가 없다. PR12는 별도 독립 수용을 요구하지만 각 단계 결과를 어떤 완결된 증거 묶음으로 수용하는지 유한 계획에 연결하지 않았다. 모형 PASS나 기존 PREP02 정상 smoke로 채울 수 없는 공백이다.

정적 반례: V1 모형과 V2 비Android lab가 모두 PASS해도 실제 APK가 main 재호출 때 시험을 다시 시작할 수 있다. 현재 source의 main→_smoke 호출은 이 차이를 보여 주는 근거이지, 미래 구현의 재실행 결함을 이미 재현한 증거는 아니다.

최소 수정: 기존 구조 안에서 별도 승인 대상인 기기 없는 검증 단계에 최종 앱 lifecycle을 검증하는 격리 emulator 또는 동등한 실제 Android 실행 증거 경로를 유한 범위로 명시하고, Stage D의 비참여 수용 기록·입출력·예산·종료점을 연결한다. emulator 경로도 원 F01/FC01 차단을 우회할 수 없으며 안전한 검증 경로를 마련하지 못하면 BLOCKED로 종료한다. 채택 전에 검증을 실행하라는 요구가 아니다.

종료 기준: 개인 단말을 첫 실험 장소로 삼지 않고 PR08의 실제 APK·OS lifecycle proof를 수집할 별도 승인 범위, 횟수/시간/bytes 상한과 독립 수용자를 지정해야 한다. 이 증거와 PR02–PR11의 exact artifact/OS 대응이 없으면 PR12는 미수용이며 Stage E에 진입하지 못한다. emulator 결과가 물리 USB/개인 phone의 PR03–PR06을 증명한다는 뜻이 아니다. 새 executor 또는 검증 캠페인을 이번 검토가 승인하지 않는다.

지적 3개는 이번 감사 산출물에서만 기록했다. 제안서·승인 양식·원 F01·B03/B11 규범을 직접 고치지 않았다. 구체 enforcement 미구현 자체를 계약의 정의 부재로 자동 판정하지 않았고, 필수 proof를 위험 서명으로 면제한다는 문구도 없으므로 BLOCKED/FAIL을 선택하지 않았다. 반면 수집/수용 경로와 판정 문구가 일관되지 않아 PASS로 채택 준비 완료를 선언할 수 없다. [finding 원문](../../../benchmarks/real-device-gate-g1-r01/independent-findings.json).

## 11. 소유자 선택 대안

| 원 ID·라벨 | 검토 결과 |
| --- | --- |
| O1 G1 기각·원 F01과 차단 유지 | 원 F01 유지와 G1 기각을 표현한다. 필수 보장이 확립되지 않아서 기각하는 이유도 O1 아래 별도 결정 사유로 기록할 수 있다. 새 O5가 이미 존재한다고 만들지 않는다. |
| O2 특정 조항 수정 요청 | 이번 세 차단 finding에 한정한 문서 수정 요청을 표현할 수 있다. 본 검토는 요청 자체를 승인하거나 수정하지 않는다. |
| O3 기기 없는 한정 mock만 별도 승인 | 계약 비채택 상태의 추가 한정 mock 선택지다. 의무 proof를 면제하지 않고 구현 범위/plan hash를 별도 승인해야 한다. |
| O4 exact G1 규범 채택을 별도 승인 | 조건부 설계 규범 채택 대안이며 구현·검증·실행 권한은 없다. 현재는 세 문서 결함과 redline/목적지/효력 미정으로 채택 준비가 되지 않았다. |

필수 보장을 확립할 수 없어서 기각하는 선택은 O1의 결정 사유로 기록할 수 있다. 별도 이름의 O5가 제안서에 존재한다고 만들지 않았다. O4는 조건부 설계 계약 채택에 대응하지만 현재 규범 목적지·redline·효력 시점은 미정이며 세 지적도 미수정이다. 따라서 **OWNER DECISION READINESS: NOT READY**는 미수정 제안서의 규범 채택 준비에 대한 판정이다. 소유자가 지금 O1 기각 또는 O2 수정 여부를 판단할 수 없다는 뜻이 아니다.

소유자의 대안을 대신 선택하지 않았다. O3 mock이나 O4 채택을 승인하지 않았고 exact-hash 서명/승인 ledger도 만들지 않았다. O1 문안의 짧은 `G1-DRAFT-01` 표기는 정확 계약 ID `F01-G1-DRAFT-01`과 별도 결정에서 일치시키는 편이 좋지만, 고정 hash로 대상은 식별되므로 별도 차단 지적으로 세지 않았다. [선택 준비 평가](../../../benchmarks/real-device-gate-g1-r01/owner-decision-readiness.json).

## 12. 현재 운영 차단과 보존 검증

현재 `dispatch.spawn_process`와 `require_host_confinement`는 AST에서 각각 한 개의 무조건 raise 본문이다. 보호 source 9개가 기존 hash와 일치하며 운영 네 모듈에서 test adapter import가 없다. 문서 승인·boolean/token/환경 설정으로 이 경계를 열 수 있다는 근거는 없다. 정적 보존 결과를 호스트 전체 임의 코드에 대한 OS sandbox proof로 확대하지 않았다. N01 자식 감독, F02 합성 backend HTTP, F03 최종 APK/서명/봉인 bytes, FC01 중앙 거부의 독립 종결 범위를 보존한다.

제품·실행기·테스트·signing source와 B03 금융/동기화·E3 guard/COMMIT·Snapshot·Offline/pending/reconciliation 의미는 바꾸지 않았다. production 서명 secret·DB·Snapshot·설정·API에는 접근하지 않았다. T6.9는 DEFERRED, formal T6.6F closure는 NOT AUTHORIZED, R1은 CLOSED, production deployment는 NOT AUTHORIZED다.

이번 사용자가 허용한 작업은 읽기 전용 source 검사·정적 제안/근거 검증·문서 출력뿐이므로 일반 AGENTS의 npm build/backend 실행 요구는 이 범위에서 수행하지 않았다. 과거 제안 작업의 npm exit 0 및 backend 72개/44 subtests 기록은 manifest/hash로만 확인했으며 이번 실행 결과로 재기재하지 않는다. 새 테스트·benchmark·임시 DB·build 산출물은 없다. 정적 JSON/참조/ID/hash/AST/보존 대조만 새로 수행했다.

시작 시 기존 tracked 변경 13개와 미추적 자료를 그대로 인계했다. HEAD·branch·Git index 원문/staged path/mode/blob, 기존 파일 7,502개(830,011,718바이트) 및 외부 frozen B03 sidecar 5개의 내용·mode·symlink를 기록한 뒤 종료 시 동일함을 확인했다. 파일 보존 결과와 감사 산출물의 최종 정합 검사 결과는 [preservation.json](../../../benchmarks/real-device-gate-g1-r01/preservation.json), [final-validation.json](../../../benchmarks/real-device-gate-g1-r01/final-validation.json)에 기록했다. 기존 source lock·과거 증거·SDK/AVD/APK/cache를 정리하지 않았다.

큰 임시 산출물 생성·삭제/회수 용량은 NOT APPLICABLE이다. 보존한 새 항목은 이 보고서, 필수 JSON 7개와 신원·정적 대조·전후 보존·manifest·문서 작성 helper뿐이다. reset·stash·clean·checkout·rebase·restage·commit·push는 수행하지 않았다.

## 13. 단 하나의 다음 행동

소유자는 기존 차단을 유지한 채 G1-R01-F01·F02·F03에 한정한 O2 문서 수정 요청 여부를 결정한다.

## 14. 필수 최종 상태

```text
REAL-DEVICE GATE G1-R01:
PARTIAL

REVIEWER INDEPENDENCE:
SATISFIED

G1 PROPOSAL:
VERIFIED

PROPOSED CLAUSES:
12 / 12

MANDATORY PROOFS:
12 / 12

REJECTION CRITERIA:
14 / 14

INITIAL DEVICE BINDING:
DEFINED

ACTUAL CHANNEL BINDING:
DEFINED

OS-ENFORCED ISOLATION:
DEFINED

AUTHORITY SEPARATION:
PASS

FINITE VALIDATION PLAN:
PARTIAL

BLOCKING FINDINGS:
3

OWNER DECISION READINESS:
NOT READY

G1 APPROVAL:
NOT GRANTED

ORIGINAL F01:
BINDING — UNRESOLVED

OPERATIONAL ADB DISPATCH:
BLOCKED

PHYSICAL DEVICE ACCESSED:
NO

REAL-DEVICE EXECUTION AUTHORIZATION:
NOT GRANTED

N01 / F02 / F03 / FC01:
INDEPENDENT CLOSURES PRESERVED

B03 SYNCHRONIZATION SEMANTICS:
UNCHANGED

GIT INDEX:
PRESERVED

HISTORICAL EVIDENCE:
PRESERVED

T6.9:
DEFERRED

FORMAL T6.6F CLOSURE:
NOT AUTHORIZED

R1 ACTIVATION:
CLOSED

PRODUCTION DEPLOYMENT:
NOT AUTHORIZED

COMMIT:
NONE

PUSH:
NOT PERFORMED

REPORT:
docs/real-device-gate-g1-r01-independent-contract-review.md

FINAL VERDICT:
PARTIAL — SPECIFIC CONTRACT CORRECTIONS REQUIRED

NEXT ACTION:
소유자는 기존 차단을 유지한 채 G1-R01-F01·F02·F03에 한정한 O2 문서 수정 요청 여부를 결정한다.
```
