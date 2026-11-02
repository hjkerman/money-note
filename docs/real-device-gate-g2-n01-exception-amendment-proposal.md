# Real-Device Gate G2-N01 — 단일 S23 FE 한정 규범 예외 초안

**READY — G2 SCOPE-LIMITED EXCEPTION AMENDMENT READY FOR INDEPENDENT N02 REVIEW.** NC01–NC08 각각의 적용 예외·보호 손실·필수 통제·증거·개별 owner 결정을 담은 한 개정 패키지를 작성했다. 이는 **독립 리뷰 준비 상태만** 뜻한다. owner 위험 수용·예외 승인·규범 적용·구현·Android 검증/접근 권한은 없다. N02는 **PENDING**이다.

유효 [G1](real-device-gate-g1-safety-contract.md)의 SHA-256은 `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`, [SC10 수정 G2 후보](benchmarks/real-device-gate-g2-sc10/corrected-proposal-candidate.md)는 `1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb`로 각각 일치한다. 두 신원을 먼저 확인한 뒤 초안을 작성했다. [R02](real-device-gate-g2-r02-independent-sc10-review.md)는 R01-B01의 문서 모호성만 독립 종결했고 실제 S23 FE SC10·E 수용이나 실행을 승인하지 않았다. 원 [P01](real-device-gate-g2-p01-restricted-campaign-proposal.md)·[SC10 보고서](real-device-gate-g2-sc10-clarification.md)·[R01](real-device-gate-g2-r01-independent-safety-review.md) 및 R02 dossier는 변경하지 않았다. 네 역사 manifest의 42개 항목을 현재 hash로 재대조했다. [출처 검증](benchmarks/real-device-gate-g2-n01/source-and-authority-verification.json).

**현재 규범 권한과 필요한 변경.** 원 F01은 “검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다”이며 PREP03/PREP09 finding 이력을 보존한다. 현재 **원 F01 AND 상위 B/C AND 유효 G1 전체 의무**가 누적된다. 세 비면제 보호·G1 전체 CP/IP gate를 일반 owner 위험 동의로 면제할 수 없다. 새 G2 파일만 만드는 방법도 효력이 없다.

지배 출처는 상위 B §27/29/31, C §26/34/34-B11/35/35-T69/38.8–12와 PREP01의 기기 안전 의무, PREP03/PREP09 F01, G1 S1–S7이다. domain-model/architecture의 서버 금융 authority와 필수 모바일 구조/복구 경계는 바꾸지 않는다. C §38은 구현 proof 실패 시 차단과 **별도 명세 변경 감사**를 요구한다. 과거 G1 N2/N3/N4/N5는 exact 문서 승인·지정 적용·비참여 대조·명시 효력 사건을 분리했다. 다만 그 승인은 SUPPLEMENT_NOT_REPLACE에 한정됐으므로 새 G2 완화 권한으로 승계할 수 없다. B11 승인 역시 지정 8개 증거 이관의 범위뿐이다.

따라서 이번 후보는 하위 보충 계약이 아니라 **B/C와 G1의 해당 적용 관계를 함께 명시 변경하는 한정 예외**다. 프로젝트 소유자의 새 개별 위험 결정과 이전 보충 한계 변경을 명시한 별도 exact 규범 승인이 필요하다. 작성/구현 비참여 N02는 그 변경 권한·우선순위·안전성부터 검토해야 한다. 검토한 상위 문서에서 소유자의 별도 정식 규범 변경 자체를 불변 금지하는 조항은 확인하지 못했다. 유효한 변경 경로가 없거나 다른 미해결 상위 충돌을 N02가 발견하면 **BLOCKED**다. 여기서 권한 분석의 VERIFIED는 출처/위계와 필요한 새 절차를 식별했다는 뜻이며, 현재 예외 권한이 있다는 뜻이 아니다. [규범 위계·목적지](benchmarks/real-device-gate-g2-n01/normative-authority-and-destinations.json).

**한 패키지의 정확한 목적지.** 아래는 모두 후보 사본이며 실제 목적지에 적용하지 않았다. 기존 binding 문서의 원문은 보존하고 명시 연결 조항만 제안했다. 각 변경은 새 예외 X1의 동일 전체 package 효력 조건을 요구하므로 단독/부분 적용으로 효력이 생기지 않는다.

| 논리 목적지 | 제안 변경 | 현재 실제 파일 |
| --- | --- | --- |
| `docs/t66/b/t66b-hot-cold-design.md` | 새 §29-G2: formal F 전 소형 smoke entry만 예외·전체 성능/whole-F/T6.9 의무 보존 | 기존 bytes 그대로 |
| `docs/t66/c/t66c-delta-sync-protocol.md` | 새 §34-G2와 §38-G2: 한정 우선순위·entry/proof 수용 구별·비예외 의무 유지 | 기존 bytes 그대로 |
| `docs/real-device-gate-g1-safety-contract.md` | S1에 explicit exception 연결: exact scope의 EX-NC01–08만 누적/비면제·편입 gate 적용을 다르게 함 | 유효 hash 그대로 |
| `docs/real-device-gate-g2-restricted-campaign-exception.md` | X1–X9의 scope·8개 예외·12 SC·승인/만료/증거 정책 | **존재하지 않음** |

[새 예외 문서 후보](benchmarks/real-device-gate-g2-n01/candidate/docs/real-device-gate-g2-restricted-campaign-exception.md)와 세 연결 후보는 dossier 안에만 있다. 상대 링크는 각 논리 목적지 기준이다. [Exact redline](benchmarks/real-device-gate-g2-n01/normative-exception.redline.patch), [before/after 해시·삽입 기록](benchmarks/real-device-gate-g2-n01/amendment-candidate-integrity.json)을 독립 재구성할 수 있다. 원 F01 finding·G1 S7 고정 JSON·역사 승인/감사/source lock은 패치 대상이 아니다. 미래 canonical G1의 예상 hash가 달라지는 것은 후보의 명시 개정 결과이며 현재 유효 G1을 변경했다는 주장이 아니다.

- Exact redline SHA-256: `4d5e611c42558a5fd3cc2fc39555432908a2410853fb479cf98fb3678b79e605`
- 새 예외 payload SHA-256: `25e01630e369cfb6f0a103cc26511ed396fbc3e3d9b6718af3cb3f6f9ac017e1`

**NC01–NC08의 개별 적용.** [상세 mapping](benchmarks/real-device-gate-g2-n01/nc01-nc08-exception-mapping.json)은 각 ID마다 기존 원문/locator, exact 예외 문구, 완화 scope, 손실, 기술/운영 통제, 가정, 잔여 위험, 사전 증거, 독립 기준, 개별 owner 결정, 목적지/우선순위의 12개 항목을 기록한다. 여덟 변경은 모두 RELAXATION이며 동등 보호가 아니다.

| ID | 지배 요구와 한정 대체 | 잃는 보호·필수 대안·owner 결정 |
| --- | --- | --- |
| NC01 | 원 F01·G1-02/04·관련 PR: actual resource/receiver 원자 결합 대신 실물 통제·exact identity·단일 관측 target·고정 선택 | 관측 사이 오대상/다른 수신자 가능. SC02–04/07과 실제 guard 자료·등록 대조 필요. RR-NC01 |
| NC02 | G1 S1/02·PR03/RJ02/03/11: 설치 전 신뢰 bootstrap 대신 기존 owner 자료·visible 확인·고정 read-only 대조 | 초기 P→U/C 기술 결합 미보장. 새 trust·공란 보충·설치 후 소급 key 금지. RR-NC02 |
| NC03 | G1-02/05·PR04/06: OS 전역 reachable-set/전면 매개 대신 qualified runner 경계와 운영 책임 | 다른 process/FD/서버·기기 전역 배제 미보장. runner 우회/egress는 실제 검증. 단일 기기 진술은 OS proof 아님. RR-NC03 |
| NC04 | G1-06/09·S3·PR07: 실제 사건 뒤 새 write 0 대신 관측/취소 전달 뒤 새 controller admission 0·host 회수 | 관측/kill-reap 사이 미전송 bytes·remote 지속 가능. event/ACK/commit/종료 분리·UNKNOWN/위반 처분. RR-NC04 |
| NC05 | 누적 전체 PR01–12 CP/IP formal gate 대신 이 scope의 SC01–12 독립 수용과 별도 grants | G1 proof 0/12로 더 약한 모델 진입. 비예외 실질 보호와 새 SC는 면제 불가. RR-NC05 |
| NC06 | PREP01 emulator-only/현재 전면 DENY에서 qualified operational/validation profile의 한정 경로 제안 | 현재 무실행보다 넓은 admission. 구현 GO·실제 경계 감사·기본 DENY 유지. FS1 승격/flag/우회 금지. RR-NC06 |
| NC07 | B §29·C §34/38.12·G1 순서에서 pre-formal-F 소형 smoke entry만 예외 | 선행 F 순서 보호 약화. whole-F/Android·최종 T6.9/R1/배포 proof는 여전히 필수. RR-NC07 |
| NC08 | PREP01 resource cap·memory/app-data의 범위를 synthetic/host hard cap과 phone 전체 soft threshold로 분리 | 전체 phone RSS/app-data/PM/열/전력 hard cap 미제공. 실제 한도/감시 검증·초과 처분 필요. RR-NC08 |

owner가 이 위험을 수용해도 승인 외 target·개인/production data mutation을 허용하는 것은 아니다. 실제 이탈은 FAIL_VIOLATION이다. 원 F01 보증을 제공했다고 주장하거나 G1 proof를 늘릴 수 없다. 정당한 예외 효력 이전에는 이 모든 의무가 원래대로 적용돼 운영은 계속 DENY다.

**Campaign·시간·자원 경계.** 제안 campaign ID는 `G2-RESTRICTED-S23FE-C01`, 부속 validation ID는 `G2-RESTRICTED-S23FE-C01-VAL1`이며 둘 다 미발급/미승인이다. 한 owner의 한 S23 FE, 한 비갱신 physical 연결/세션 시도만 대상으로 한다. 규범 결정에서 exact owner/device binding과 UTC 유효 시간창이 없으면 효력이 없다. 후속 E 전에 exact serial/variant/build/API/ABI, source/tool/APK/signer, argv/input/path/order·전체 budget·외부 trusted expected digest를 완성·독립 수용해야 한다. 현재 없는 값이나 owner 결정을 꾸미지 않았다.

격리 application ID·독립 test signer·봉인된 동일 APK bytes·private synthetic data·소유 synthetic/local backend를 함께 요구한다. 별도 F grant의 고정 read-only 등록→별도 G first-mutation grant의 install 1회→독립 post-install checkpoint→기존 grant의 launch 1회→고정 bounded evidence만 허용할 수 있다. 이는 operation 분류이며 실제 실행 manifest가 아니다. 범용 shell·adaptive 생성·자동 retry/복구·추가 readback·새 trust/pairing·device-wide 정책 변경·production/개인/공유 데이터 접근은 금지다. 현 코드/FS1/기존 종결은 이 norm 적용만으로 변하지 않는다.

연결~새 admission 종료 600초, 첫 mutation grant age120초, APK 256MiB, 합성 요청 12개·response별 256KiB·body64KiB, synthetic output1MiB·result16KiB, host evidence10MiB, 동시 action1·install/launch 각 최대1은 **P01 제안 ceiling의 재사용**이다. 각 수치의 원 JSON pointer를 [scope·만료 명세](benchmarks/real-device-gate-g2-n01/campaign-scope-and-expiration.json)에 기록했다. owner 승인 값이 아니며 이 이하의 실제 예산과 per-action timeout·grace·공간/메모리/열 threshold, host/emulator 검증 자체의 예산은 후속 별도 결정이 필요하다. 새 시간/메모리/보존 일수를 만들지 않았다. output1MiB는 전체 app-data hard cap이 아니고 600/120초도 remote hard stop이 아니다.

만료·철회·scope/hash drift·필수 검증 실패·연결 시도 소진·identity/세대/감독/증거/한도 이상은 새 grant/action을 원 DENY로 돌린다. 같은 ID·late ACK로 재개/갱신하지 않는다. 이미 admission한 단일 유한 action의 host 회수/remote 잔여와 확보된 증거 처분만 EX-NC04/X7이 계속 다루며 새 command 권한을 만들지 않는다. host 종료·transport 단절·remote 종료·durable commit/rollback은 별개다. 불명 결과는 UNKNOWN_QUARANTINED이며 실제 위반은 별도 실패다.

정상도 자동 uninstall/clear/force-stop이나 개인 자료 backup/restore를 하지 않는다. APK/private synthetic·PM/cache·기존 trust와 공유 자원 영향이 남을 수 있다. 추후 정리는 별도 owner 결정이며 완전 복구를 보장하지 않는다. bounded journal·partial 실패·승인/판정 원자료를 보존하고 cap에서 덮어쓰기·결측 성공 처리를 금지한다. 기존/유일 증거와 source lock은 자동 삭제하지 않으며 검증된 host task-owned disposable만 hygiene 규칙에 따라 정리할 수 있다.

**개별 위험 수용과 승인 분리.** [위험·owner 선택](benchmarks/real-device-gate-g2-n01/residual-risk-and-owner-decisions.json)은 RR-NC01–08 외에 RD01(APK 공급망/검토 누락), RD02(OS/개인 데이터 무피해·복구 한계), RD03(네트워크 구현/신뢰 한계), RD04(설치/PM/캐시·기존 trust 잔류)를 각각 별도 고지한다. 추가 네 항목은 기존 G2 잔여 위험을 특정한 것이며 아홉 번째 norm 완화가 아니다. 12개 결정과 AS01–04의 운영 책임은 전부 **NOT GRANTED**다. 일반적인 위험 수용 문장·무응답·저자 template로 채울 수 없다. 미검증 SC10 target 안전 전제나 새 필수 SC를 owner 위험 동의로 면제할 수 없다.

[미서명 exact-hash 양식](benchmarks/real-device-gate-g2-n01/unsigned-exact-hash-owner-decision-template.json)과 [사람이 읽는 양식](benchmarks/real-device-gate-g2-n01/unsigned-exact-hash-owner-decision-template.md)은 package/patch/목적지·고지 hash를 고정하고 모든 실제 선택·서명·시간/기기·N02 결과를 비워 뒀다. 그대로는 적용 불가다. 원본을 보존하고 실제 owner 응답으로 새 기록/hash를 만들어 C 위험 결정과 D 규범·적용 결정을 각각 검증해야 한다.

| 승인 단계 | 내용 | 후속 권한 |
| --- | --- | --- |
| A | 이번 N01 drafting-only | 문서만 |
| B | 새 비참여 N02 규범·안전 검토 1회 | 현재 PENDING, owner 결정 아님 |
| C | 12개 개별 위험과 AS01–04 책임의 실제 owner 결정 | 규범 적용 아님 |
| D | owner exact 4개 목적지 승인→지정 bytes 적용→비참여 일치→명시 완료 사건 | 구현·기기 GO 아님 |
| E | 별도 host-only 구현 승인·기존 P01.C | 실제 validation GO 아님 |
| F | 각각 별도 host 검증/emulator GO와 독립 수용·기존 P01.C/D | physical 접근 아님 |
| G | 독립 preflight·원 P01.E | 연결 grant 아님 |
| H | 별도 owner 연결/read-only grant·원 P01.F | mutation grant 아님 |
| I | 별도 owner 첫 mutation grant·원 P01.G와 checkpoint/사후 처분 | 재시도/추가 권한 없음 |

부속 emulator 진입은 C의 host qualification·physical USB 비노출 조건과 별도 GO를 요구하며, 아직 수집할 D 결과나 미래 SE05를 먼저 요구하지 않는다. 새 구현 후보를 별도 GO 범위에서 최초 작성하는 행위와 동결 이후 미승인 source drift도 구별했다. 규범 package는 불변이며 C/D/E 동결 뒤 임의 수정·rebuild로 같은 campaign을 계속할 수 없다.

[승인 경계 전문](benchmarks/real-device-gate-g2-n01/authorization-stage-boundaries.json). SC10의 SE01–04→SE05(preflight)→별도 F/SE06→별도 G/SE07 의존성은 R02가 검토한 그대로다. offline 안전 근거를 확보·수용할 수 없으면 terminal BLOCKED이며 새 사전 phone probe를 끼워 넣지 않는다. 가용성 미확정과 안전 결측을 구별한다.

**N02의 한정 검토와 종료 조건.** [독립 인계](benchmarks/real-device-gate-g2-n01/independent-n02-handoff.json)는 정확한 후보·NC01–08·4개 redline·권한/우선순위·잔여 위험·예산/보존·A–I 및 SC10·owner 선택 대안을 대상으로 한 번의 독립 검토를 준비한다. 현재 의뢰/검토/자동 승인/적용은 수행하지 않았다. N02가 상위 권한 또는 본질적 안전 충돌을 찾으면 BLOCKED로 보고해야 한다. 새/더 넓은 예외를 이 후보에서 자동 보충하지 않는다. 실제 SC나 새 구현의 기술 증명을 못 세우면 후속 단계도 BLOCKED이며, 실기기 시험 가능성을 약속하지 않는다.

**보존·실제 수행 범위.** 새 보고서와 N01 dossier만 작성했다. binding 문서·실행 코드·원 후보/리뷰·B03·source locks·Git index를 수정하지 않았다. ADB/help/version·server socket 요청·USB/device 명령·emulator·physical 접근·APK 설치·production 기록 접근·기술 proof 수용은 모두 0이다. 정적 문서/해시/패치·의존/권한 분석만 했고 npm/backend/Flutter/Android runtime 검증을 실행하지 않았으며 과거 PASS를 새 기술 proof로 세지 않았다. 임시 DB/build/cache 생성·삭제가 없어 정리는 NOT APPLICABLE이다.

종료 대조에서 기존 8,285개 경로·외부 frozen sidecar 5개·source lock 27개와 HEAD/index/staged가 보존됐다. 결과는 [보존·정적 검증](benchmarks/real-device-gate-g2-n01/validation-and-preservation.json), 새 자료 hash는 [증거 manifest](benchmarks/real-device-gate-g2-n01/evidence-manifest.json)에 기록한다. 기존 N01/F02/F03/FC01 독립 종결·T6.9 DEFERRED·R1 CLOSED·production 미승인·commit/push 없음은 유지한다.

다음 최소 결정은 **소유자가 이 고정 package에 대한 비참여 N02 독립 규범·안전 검토 1회만 별도로 의뢰하는 것**이다.
