# Real-Device Gate G1-N2 — 보충 개정안 독립 규범 검토

**판정: PASS — SUPPLEMENTARY AMENDMENT READY FOR EXACT OWNER APPROVAL. 차단 finding은 0개다.** 검토된 보충 후보는 별도 exact 소유자 N3 승인 결정에 제출할 수 있다. 이 판정은 소유자 승인이나 규범 적용, 구현·기술 proof 수용·기기 실행 허가가 아니다. 원 F01은 계속 구속되며 미해결이다.

이번 검토는 사용자가 지정한 신규 독립 세션에서 수행했다. G1 원안·O2/O3 정정·보충안 작성, 관련 구현·측정·적용에 참여하지 않았다. 원 입력을 수정하지 않고 실제 문서·JSON·패치·해시를 대조했으며 저자의 자체 PASS를 독립 판정으로 재사용하지 않았다. 문서 dossier 한 개의 N2 검토 한 회에 한정한다. 두 임시 디렉터리의 적용 재현은 같은 exact 패치에 대한 정적 신원 확인이다.

**검토 입력과 정확한 신원.** 아래 SHA-256은 실제 파일 바이트에서 계산했다. [전체 입력 목록](benchmarks/real-device-gate-g1-n2/input-inventory.json)에 99개 입력의 경로·크기·정확한 해시를 남겼다. 저장된 owner 원문 전사 hash는 로컬 전사 파일의 신원이며 메시지 전송 바이트·암호 서명·실명 인증을 뜻하지 않는다. 정확한 결정 시각의 null과 기록 생성 시각을 구별했다.

| 입력 | 검증된 SHA-256 |
| --- | --- |
| 심사 제안서 | `6a84c050b81e3e7b06541a65b1eb1f0fb945e17e2485d83572f22241b2ce2cb6` |
| 정확한 추가 패치 | `05141e21d61945703073b0c4afbcf24ba6eb8e2cdce020dc1fffbb66d7452d9c` |
| 독립 검토 인계 | `c31ff9d3fae4574a778b55c9c65d23599d288c82a74662cc40690bde856665e3` |
| 미적용 후보 전문 | `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e` |
| 두 조항 통합 패치 | `ab3da7a1c0525658459071f129974547bd8e5de98ba26b8d1f4f8760b5d5983b` |
| 승인 O2 후보 | `e376edf49db7fc19b2853625e7a5741864e72c4cdc5243605cac85807cba8279` |
| 승인 O3 계약 | `24d016b41e4d353a6771724cf10ba359009c0d8a74e915652407f990e1a1e499` |
| 승인 O3 PR07/G1-09 | `99dbfcfc26adb65d47cd91f7967054e5761d7fbda4a0e704de9c7f3969aa4338` |
| R03 독립 종결 보고서 | `4124782eeab267525b6009ab5c483df8005672f2ab2ea162f7341e6934032664` |
| 소유자 설계 채택 | `d1d29e565cba764ab1e8911d44ad9e4455c338f2afbcbf75c24817609ca0bb23` |
| 소유자 보충 결정 | `ab3a34986e9474eb6503e64763f4c5099e8b52c34ba48eaeeb0451160e84fe84` |
| 정확한 의존성 lock | `a14fb26d84df0b7774d42a953e129e7a4e09105b2f4c85e59a6706fc7bf3ba47` |
| B 상위 규범 | `e2d820ba71018414934ad4a9b3667961c209f93fe0b5b5dd2d0a3233ea76b279` |
| C 상위 규범 | `5d3f03a0e61c6d504cf8efd5de0c8ee446b9c0a0b4a45a367f6d366a4fbf94c9` |

승인 O2 MD와 O3 두 successor가 소유자 설계 채택의 세 exact 대상과 일치했다. 각 O3 successor는 O2 원본의 지정 pointer에서 `commit 전에`를 `무효화 전에`로 한 번 바꾼 결과이며 파일당 +3바이트다. 다른 바이트와 12개 조항 배열은 보존됐다. R03의 독립 문서 종결과 N01/F02/F03/FC01 종결 기록·보호 source 신원도 대조했다. 이 과거 종결을 새 보충안 검토나 기술 proof 수용으로 승계하지 않았다.

**실제 지배 규범과 목적지.** [문서 책임표](project-state.md#문서별-책임), [T6.6 지도](t66/README.md), B/C의 실제 현행 절, PREP01의 물리 단말 안전 기록, PREP03→PREP09 F01을 확인했다. B/C가 Real-Device Gate의 상위 요구를 정하며 G1 전용 목적지를 이미 지정한 것은 아니다. 기존 [N0–N5 계획](benchmarks/real-device-gate-g1-conditional-adoption/normative-application-plan.json)은 새 `docs/real-device-gate-g1-safety-contract.md`를 후보 경로로 제안한다. 소유자의 보충 결정은 exact 후보 준비를 허용하며 이 경로의 현재 구속 권한을 승인한 것이 아니다.

목적지는 시작·모의 적용 뒤·최종 보존 확인 시 모두 **ABSENT**다. before SHA는 null이고, 기대 after SHA는 `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e`다. 별도 문서를 상위 규범에 종속시키고 기존 문서를 수정하지 않는 방식은 저장소의 책임·변경관리 구조와 정합한다. 새 파일명만으로 규범 authority를 추론하지 않았다.

| 실제 지배 절 | 독립 정합 판단 | 후보 근거 |
| --- | --- | --- |
| B §27 | 기존 성능·스케일·gzip 비교 및 host/phone 구별을 유지한다. 새 절대 지연 합격선을 만들지 않는다. | S1/S6 |
| B §29 | 구현 승인·F 독립 감사·post-T6.6 기기 gate 순서를 유지한다. B11의 제한 T6.9-E 이관이 G1 실행 GO가 되지 않는다. | S1/S6 |
| C §26 | 실제 Android driver PRAGMA/VFS·native fence·I/O·power-loss proof와 rollout 차단이 남는다. 문서 또는 emulator PASS가 이를 대체하지 않는다. | S1/S4/S6 |
| C §34·§34-B11 | 명시 구현·rollout 승인, 8개 증거 이관의 한정 범위와 whole-F/R1 차단을 유지한다. | S1/S6 |
| C §35·§35-T69 | 원 B03 신원·다섯 점 실측·직접 귀속·독립 수용 및 별도 실행 GO를 보존한다. T6.9를 재개하지 않는다. | S1/S6 |
| C §38.8–12·실패 처리 | Android 내구성·legacy·복구·30 backup/artifact/GC·post-T6.6 기기 증명은 계속 필수다. 구현 proof 실패의 차단 및 별도 명세 변경 감사도 보존한다. | S1/S6 |

8개 실제 절의 제목·행 범위·전체 파일 SHA·절 바이트 SHA를 독립 대조했다. [권한 검토 JSON](benchmarks/real-device-gate-g1-n2/normative-authority-review.json)에 정확한 위치와 해시를 보존한다. 원 F01의 실제 요구는 다음과 같고 후보 S1의 인용과 정확히 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

후보의 허가 관계는 **원 F01 AND 상위 적용 의무 AND 모든 적용 G1 의무**다. 충돌 또는 정합성 미입증이면 BLOCKED이며 더 약한 요구를 고를 수 없다. no-other-target·transport ID·반복 probe·조건부 격리 또는 위험 서명만으로 원 F01을 대신하지 못한다. 원 F01 강제 메커니즘이 미입증이면 다른 G1 증거가 있어도 mutation은 DENY다. O3의 과거 `delta_ko`·O4 대체 대안·미서명 metadata는 S7이 역사 provenance로 한정하며 이번 보충 관계를 덮지 못한다.

**정확한 redline과 12개 조항.** 패치는 `/dev/null`에서 목적지 하나를 만드는 순수 추가 164행이다. 기존 binding 문서 수정·삭제 hunk는 없다. 직접 추가행을 복원한 바이트, 후보 전문, 원 조항 대비 통합 diff를 각각 대조했다. 원 ID·title 12개를 모두 보존하고 G1-01/G1-12의 두 변경만 명시했다. 다른 10개 조항은 O3 승인 object와 정확히 같다.

| 조항 | 정확한 차이 | 의미 보존 판단 |
| --- | --- | --- |
| G1-01 | 명시 통합 변경 | G1-01의 조건부 대체를 하위 보충으로 바꾸고 원 F01 변경·대체·면제를 금지한다. |
| G1-02 | 원 object와 정확히 동일 | 동일 P*/U*와 승인 도달 집합·효과 범위를 유지한다. |
| G1-03 | 원 object와 정확히 동일 | CP+연결 grant와 IP+첫 mutation grant를 구별하고 설치/marker/launch의 선행 mutation을 금지한다. |
| G1-04 | 원 object와 정확히 동일 | 승인·host/server/USB/channel/receiver 실제 자원 세대 결합을 유지한다. |
| G1-05 | 원 object와 정확히 동일 | 전면 매개·우회 차단·자동 server/restart/reexec/fallback 금지를 유지한다. |
| G1-06 | 원 object와 정확히 동일 | 진행 중에도 영구 REVOKED·새 제출 금지·미확인 remote 격리를 유지한다. |
| G1-07 | 원 object와 정확히 동일 | 고정 argv/bytes/artifact·action별 한 번 시도·앱 replay 금지를 유지한다. |
| G1-08 | 원 object와 정확히 동일 | test package/private synthetic·합성 endpoint와 개인/production 데이터 금지를 유지한다. |
| G1-09 | 원 object와 정확히 동일 | 실제 제출·무효화·ACK·remote task·UNKNOWN 처분과 추가 readback/reconnect 금지를 유지한다. |
| G1-10 | 원 object와 정확히 동일 | CP/IP 예산·실제 세대와 POST 이력 수용을 구별한다. |
| G1-11 | 원 object와 정확히 동일 | 독립 CP/IP/POST·상태 분리·최종 APK 실제 lifecycle 및 적용성 증명을 유지한다. |
| G1-12 | 명시 통합 변경 | 기존 별도 gate·유한 실패 종료는 그대로이며 마지막 문장만 이번 문서 작성 권한으로 갱신한다. |

G1-01의 강화는 소유자의 SUPPLEMENT 방향에 해당하고 G1-12는 작성 권한의 이력 갱신이다. 나머지 보증을 줄이거나 운영 dispatch를 여는 문장은 없다. S1/S3/S6의 누적 조건이 모든 조항·편입 gate에 적용된다. 후보는 boolean/token·환경 변수나 구현된 gate가 아니며 실제 `dispatch.spawn_process`와 `require_host_confinement`의 본문이 무조건 예외를 발생시키는 상태임을 AST로만 확인했다. 이 모듈을 import하거나 호출하지 않았다.

**12개 필수 proof·14개 거부 기준·세 비면제 보호.** S4/S7은 원 required-proof-matrix와 phase matrix의 의무·필수 증거·execution_gate·phase_acceptance·비면제 조건을 정확한 해시로 편입한다. 단순 ID 보존만으로 PASS를 부여하지 않았다. 각 PR의 CP/IP/POST object가 두 원 matrix에서 일치하고 모든 독립 수용은 PENDING, authority는 NOT_GRANTED, 증거 참조는 null이다.

| proof | 원 의무 | 독립 보존 판단 |
| --- | --- | --- |
| PR01 | 승인 provenance·계약 우선순위 | 설계·문서 적용·기술 수용·실행 권한을 분리한다. |
| PR02 | artifact/tool 신원 | 정확 binary/source/APK/signer/fixture와 봉인 바이트의 증거 의무를 유지한다. |
| PR03 | 최초 등록과 bootstrap 결합 | 설치/marker 없이 최초 P*↔U*/C*를 독립 입증한다. 잘못된 유일 정상 단말을 가정으로 제외하지 않는다. |
| PR04 | USB incarnation 강제 | 실제 USB incarnation 수명과 재열거·주소 재사용 차단을 요구한다. |
| PR05 | server/channel/transport 결합 | actual server/channel/transport peer 자원 결합이 필수다. PID/ID/직전 probe가 대체하지 않는다. |
| PR06 | OS 전면 매개와 우회 불가 | OS 전면 매개가 wrapper·후손·FD·다른 socket/TCP/mDNS 우회를 차단해야 한다. |
| PR07 | 폐기·host 1회 시도·감독 수명 | 실제 무효화 사건을 cutoff로 유지하고 새 제출/write/자원 취득=0·host 시도≤1·자식 회수와 UNKNOWN을 분리한다. |
| PR08 | 앱 격리와 자동 재실행 방지 | 최종 APK의 실제 Android lifecycle·replay 방지와 phone 적용성 증거를 유지한다. 첫 설치 전 설치 영수증을 요구하지 않는다. |
| PR09 | 합성 backend·네트워크 | 단말 경로와 host egress의 합성 origin·route 소유권, redirect/production fallback 거부를 보존한다. |
| PR10 | 자원·증거·UNKNOWN 처분 | 시간·bytes·journal의 고정 한도와 hard/soft 한계, 미확인 결과의 격리를 유지한다. |
| PR11 | 명령·효과 allowlist 완결성 | 연결 전 literal argv/input/경로/순서·허용 효과가 동결돼야 하며 adaptive 명령을 허용하지 않는다. |
| PR12 | 독립 통합 수용 | 각 단계 비참여 수용과 source/runtime/OS 적용성, 기존 종결 보존을 요구한다. proof 자체는 owner grant가 아니다. |

RJ01–RJ14의 거부 조건 원문과 `REJECT_OR_REQUEST_PRECISE_REVISION; KEEP_BLOCK` 처분은 후보 표와 모두 일치한다. 허가 오인, 초기 등록/실제 채널/OS 경계 결측, 세대 승계, 우회/자동 재시작, 미동결 계획, 첫 mutation 확인 부재, 개인/production 접근, UNKNOWN 자동 복구, 위험 서명 면제, self-review 승격, 미입증 보증 및 역사/index 변경을 계속 거부한다. 기존 거부 조건은 최소 요건이며 이번 문서 작성 권한을 exact 적용·실행 권한으로 확대하는 것도 거부한다.

세 면제 불가 보호인 **최초 단말 신원 결합·실제 승인 채널과 수신자 결합·OS 강제 기기 격리**를 각각 PR03/04/12, PR03/05/07/12, PR04/06/12와 대조했다. AS01–AS06과 GR01–GR07은 항목별 미수용이며 어느 위험 수용도 원 F01·필수 proof·세 보호를 면제하지 못한다. 원 유한 검증 단계 A/B/C1–C5/D/E0–E4의 제한·독립 수용·실패 종료도 편입돼 있다.

연결 전 CP는 메커니즘·적용성이고 실제 U*/C*는 연결 후 IP다. 모든 CP+D·사전 exact 신원/동결 manifest·별도 owner 연결/read-only grant가 있어야 고정 등록만 가능하다. 모든 IP+E2·원 F01의 실제 결합·별도 owner 첫 mutation grant 전에는 최초 설치·marker·launch도 금지다. 첫 설치로만 생기는 receipt나 POST를 선행 요구하는 순환은 없다. 후속 action은 사전 checkpoint와 필요한 비참여 보충 수용을 유지하고 POST는 종료 이력 분류만 한다.

PR07/G1-09의 cutoff는 실제 **무효화 사건**이며 제출 시작·원격 task 시작·durable commit·ACK·host 관측/집행과 구별된다. 무효화 전 동일 action/receiver/channel에 실제 제출된 bounded 작업만 잔여 범위이고 미확인 종료/결과는 UNKNOWN_QUARANTINED다. 지연된 관측/집행은 새 제출/write/자원 취득의 유예가 아니다. 실제 위반은 FAIL_VIOLATION이며 UNKNOWN으로 면제하지 못한다. host stop/reap은 remote 정지·실패·commit·rollback을 증명하지 않고 늦은 ACK도 폐기 세션을 복구하지 않는다. 추가 mutation/readback/reconnect/자동 cleanup 없이 확보된 증거만 비참여자가 처분한다. [보존 JSON](benchmarks/real-device-gate-g1-n2/proof-and-rejection-preservation.json)에 12개 proof 전문 귀속·14개 거부 기준·8개 문서 해석 이력을 기록했다. 실행한 기기 시험은 아니다.

**소유자 권한 분리.** 기록된 조건부 설계 채택과 SUPPLEMENT 결정을 검증했다. 이전 계획의 미선택 상태와 R03 당시의 미승인 상태는 각 시점의 역사이며 새 기록과 구별한다.

| 단계 | 현재 상태 | 필요한 별도 권한 |
| --- | --- | --- |
| 설계 채택 | 세 exact 설계 산출물의 조건부 채택만 확인 | 향후 계획·proof 자격검증의 기준 |
| 규범 개정 승인·적용 | 미승인·미적용 | N3 exact 목적지/후보/패치/의존성·가정/위험·역할/효력 결정, N4 적용, N5 독립 PASS·완료 기록 |
| 아키텍처 구현·각 검증 | 미승인 | 지정 구현 후보와 mock/OS/lab/emulator/app/interruption별 별도 승인 |
| 독립 기술 proof 수용 | **0/12** | 실제 source/runtime/OS/artifact 증거의 CP/IP/POST별 비참여 수용 |
| 기기 실행 | **차단·미허가** | 해당 gate와 별도 exact owner 연결/read-only·첫 mutation 승인 |

N2 PASS는 N3 승인이 아니고, 미래 N3 승인도 코드 변경·ADB·emulator·물리 기기 접근을 자동 허가하지 않는다. 미서명 양식의 owner 승인·적용·모든 later grant는 false이며 전사나 문서 PASS를 실행 token으로 사용하지 않는다. [권한 분리 JSON](benchmarks/real-device-gate-g1-n2/owner-authority-boundaries.json).

**독립된 정적 적용 모의.** 실제 저장소 밖 task 소유 `/tmp`의 빈 디렉터리 두 곳에서 `git apply --no-index --check`와 `git apply --no-index`를 각각 실행했다. 상속 Git 변수를 제거하고 별도 미존재 `GIT_INDEX_FILE`과 설정 격리를 지정했다. 네 명령의 exit code는 모두 0이고 두 결과 모두 `docs/real-device-gate-g1-safety-contract.md` 하나만 생성했다. 두 파일은 전문 21,639바이트로 검토 후보와 정확히 같으며 SHA-256은 `967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e`로 재현됐다. 실제 checkout에는 패치를 적용하지 않았고 실제 목적지·임시 index도 생성하지 않았다. [모의 결과·명령·환경](benchmarks/real-device-gate-g1-n2/static-application-simulation.json).

**판정 범위와 보존.** 독립 정적 검사 318개, 패키지 참조 100건을 포함한 path/SHA 참조 총178건에 불일치가 없었다. 이는 문서/신원 검사 수이며 기술 proof 분모가 아니다. [재검증기](benchmarks/real-device-gate-g1-n2/verify-inputs.py)와 [정적 결과](benchmarks/real-device-gate-g1-n2/static-verification.json), [참조 대조](benchmarks/real-device-gate-g1-n2/reference-validation.json)를 보존했다. N2의 문서 전용 범위와 handoff의 제품 실행 0 제한에 따라 npm/backend/Flutter 시험은 실행하지 않았고 과거 시험 결과도 이번 proof로 집계하지 않았다. 새 구현·모형·OS·emulator·기기 캠페인은 없다.

기존 tracked/untracked 및 모든 기존 docs 증거 8,009개(966,789,224바이트), 읽기 전용 외부 B03 sidecar 5개와 HEAD·branch·Git index 원문·staged entries를 시작/종료 대조했다. 변경·누락은 0개다. index SHA-256은 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`로 보존됐다. 무시된 런타임·production 파일 전체를 전수 감사했다고 주장하지 않는다. 새 저장소 파일은 본 보고서와 N2 증거 디렉터리에만 있다. [보존 결과](benchmarks/real-device-gate-g1-n2/preservation.json).

작업 소유 정적 모의 scratch는 필수 baseline·결과를 증거로 보존한 뒤 정리했다. 기존 파일·cache·DB·증거는 삭제하지 않았다. 대형 build/DB/benchmark 산출물은 없으며 대형 임시 산출물 관리 항목은 NOT APPLICABLE이다. 정확한 task scratch 삭제 항목·회수 바이트는 [정리 기록](benchmarks/real-device-gate-g1-n2/artifact-cleanup.json)에 남긴다. 첫 일반 sandbox 호출은 bwrap loopback 초기화 오류로 문서를 읽기 전에 실패했고 정적 읽기/허용된 보고서 작성만 승인 검토 경로로 수행했다. 자동 승인 거절은 없었다. 최종 링크 검사가 정리 기록 생성보다 먼저 실행된 helper 순서 오류로 한 번 중단됐다. 생성 후 링크를 검사하도록 바로잡았고 [도구 이력](benchmarks/real-device-gate-g1-n2/tooling-incidents.json)에 원인·영향·수정 범위를 기록했다.

규범·제품·executor·B03·production configuration은 변경하지 않았다. ADB는 도움말 포함 호출 0, emulator 작업 0, 물리 단말 접근 0, APK 설치 0이며 T6.9는 재개하지 않았다. reset·stash·clean·checkout·rebase·restage·commit·push도 수행하지 않았다.

**필수 산출물.**

- [normative-authority-review.json](benchmarks/real-device-gate-g1-n2/normative-authority-review.json)
- [amendment-redline-review.json](benchmarks/real-device-gate-g1-n2/amendment-redline-review.json)
- [proof-and-rejection-preservation.json](benchmarks/real-device-gate-g1-n2/proof-and-rejection-preservation.json)
- [owner-authority-boundaries.json](benchmarks/real-device-gate-g1-n2/owner-authority-boundaries.json)
- [static-application-simulation.json](benchmarks/real-device-gate-g1-n2/static-application-simulation.json)
- [independent-findings.json](benchmarks/real-device-gate-g1-n2/independent-findings.json)
- [exact-approval-readiness.json](benchmarks/real-device-gate-g1-n2/exact-approval-readiness.json)

정확한 소유자 승인 준비 상태는 **READY**이며 차단 finding은 **0개**다. 필수 기술 증명의 미수집·미수용은 이번 문서 준비의 결함으로 바꾸지 않았고 실제 구현·기기 실행의 차단으로 유지했다. N3에서는 목적지·후보·패치·dependency lock·필수 review inputs·본 N2 보고서의 exact 해시, 항목별 가정/위험, 적용/비참여 검토 역할과 효력 사건·완료 기록을 명시 결정해야 한다. 본 보고서 해시는 순환 참조를 피하도록 [산출물 manifest](benchmarks/real-device-gate-g1-n2/evidence-manifest.json)의 `report`에 고정한다.

```text
REAL-DEVICE GATE G1-N2:
PASS

INDEPENDENT REVIEW:
SATISFIED

SUPPLEMENT DECISION:
VERIFIED

PROPOSED DESTINATION:
docs/real-device-gate-g1-safety-contract.md

PATCH SHA-256:
05141e21d61945703073b0c4afbcf24ba6eb8e2cdce020dc1fffbb66d7452d9c

SIMULATED DESTINATION SHA-256:
967e6b07a66cdc88aaa037d1965fc0aac63d0a7069a4f39af005043ad64b201e

ORIGINAL F01:
BINDING — UNRESOLVED

G1 SUBORDINATION:
PASS

12 CLAUSES:
PRESERVED

12 MANDATORY PROOFS:
PRESERVED

14 REJECTION CRITERIA:
PRESERVED

THREE NON-WAIVABLE SAFEGUARDS:
PRESERVED

SUPERIOR PROTOCOL CONSISTENCY:
PASS

AUTHORITY SEPARATION:
PASS

BLOCKING FINDINGS:
0

EXACT OWNER APPROVAL READINESS:
READY

G1 NORMATIVE APPLICATION:
NOT PERFORMED

TECHNICAL PROOFS ACCEPTED:
0 / 12

ADB OPERATIONAL DISPATCH:
BLOCKED

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

FINAL VERDICT:
PASS — SUPPLEMENTARY AMENDMENT READY FOR EXACT OWNER APPROVAL

NEXT ACTION:
소유자는 검증된 목적지·후보·패치·의존성 해시와 N2 보고서를 지정해 N3의 별도 규범·문서 적용 승인 여부를 결정한다.
```
