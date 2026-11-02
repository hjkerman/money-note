# Money Note — G2-N02 독립 규범·안전성 검토

**판정: PASS — G2 EXCEPTION PACKAGE READY FOR EXACT OWNER DECISION**

고정 N01 예외 패키지는 NC01–NC08의 보호 손실, 네 규범 목적지의 우선순위, 보상 통제와 필수 증거, 항목별 소유자 결정 및 후속 승인 경계를 충분히 명시했다. 차단 finding **0건**, 비차단 finding **0건**이다. 소유자의 명시적 잔여 위험·규범 결정에 제시할 준비가 됐다는 판단이다.

이 PASS는 G2 승인·위험 수용·규범 적용·기술 증명 수용 또는 기기 실행 허가가 아니다. 실제 S23 FE의 SC10 적용성, 최종 APK, 새 runner/relay·durable claim, 실제 자원 threshold와 C/D/E 수용은 미확보·미수용 상태다. 해당 필수 근거를 세울 수 없으면 캠페인은 **terminal BLOCKED**로 끝나며 실기기 시험 가능성을 약속하지 않는다.

**독립성 및 검토 범위**

새 독립 N02 세션으로 수행했다. 이 세션은 G2-P01 제안, SC10 수정 또는 N01 개정안 작성에 참여하지 않았다. 독립성은 SATISFIED이며, 외부 인간 검증이나 구현·실행 증거의 기술적 수용을 수행했다고 주장하지 않는다. 소유자가 의뢰한 고정 패키지에 대한 문서 검토 1회로 한정하고 하위 agent를 사용하지 않았다.

AGENTS.md, 산출물 위생 규칙, project-state/domain-model/known-issues 및 architecture의 서버 authority·클라이언트 신뢰 경계를 읽었다. N01 보고서·JSON **13개 전체**·통합 patch의 네 파일별 redline·네 후보·미서명 양식, 원 P01·R01·R02·수정 후보를 대조했다. 원 PREP01 물리 기기 계약, PREP03 원 F01, PREP09 거부 경계/반례, PREP10·유효 G1과 해시로 편입한 PR/phase/admission/RJ, 기존 G1 적용 승인·효력 사건, A01/정적 플랫폼 재평가, FS1 독립 감사 및 관련 현재 소스를 근거로 삼았다.

저자의 READY나 검증 boolean을 승인으로 승계하지 않았다. [출처·신원 검증](benchmarks/real-device-gate-g2-n02/source-and-identity-verification.json)은 N01 전체 패키지 **20개 파일**의 실제 해시, 출처/인계/역사 manifest·S7·X9의 해시 대조 **189건**, 지배 원문 발췌 **18개**, P01 수치 출처 **12개**를 기록한다. 대조에 중복 출처가 있으며 이 수를 기술 proof 수로 집계하지 않는다. N01 시작 보존목록의 기존 8,285개 내용 해시도 현재 bytes와 일치했다.

| 핵심 검토 산출물 | 검증한 SHA-256 |
| --- | --- |
| SC10 수정 G2 후보 | `1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb` |
| 현재 유효 G1 | `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0` |
| N01 보고서 | `3f1967900920c4a5519758cb76f23edd9dcb0bc19d6d6cb79053260c143aca52` |
| N01 개정 무결성 명세 | `1a1f66249aa92a535f39eb8eb15ed51ddd0cfff0cf85995274337de9ffb4aef4` |
| N01 통합 exact redline | `4d5e611c42558a5fd3cc2fc39555432908a2410853fb479cf98fb3678b79e605` |
| N01 위험 고지 | `94d2e165682ce5f178d41d0f9fed0d607b87c138bd2bac0e7c1dfe796160be30` |
| 미서명 owner JSON 양식 | `d1a3a49b9f8ee5567a577f483b5793d34bf35e996ffa1dd7aa29b7fed5110655` |
| 편입 SC10 증거·수용 명세 | `8b86ae470e7bea9a7d409b16a129720fb7e9b548852544f4b6f82f21adfa5922` |

요구된 후보와 유효 G1 신원에 불일치가 없어 신원 차이로 인한 BLOCKED 조건은 발생하지 않았다. 현 G1의 작성 당시 미적용 문구는 주석·N3/N4/N5 완료 사건과 함께 해석했다. 과거 승인본과 현 주석 포함본을 혼동하지 않았다.

**규범 변경 권한과 네 목적지**

원 F01의 지배 요구는 다음과 같다.

> 검증한 Android 대상의 신원과 실제 mutation 수신자를 원자적으로 결합하고 연결·server 세대 변경 시 이전 권한을 넘기지 않아야 한다.

현재 원 F01·상위 B/C·PREP01·유효 G1은 누적 구속된다. G1 S1의 세 비면제 보호와 전체 CP/IP gate는 일반 위험 동의나 하위 G2 문서만으로 면제할 수 없다. 기존 G1-N3의 조건 4–6은 원 F01·12개 proof·세 비면제·상위 종속 보존에 한정하며 이번 완화 권한으로 재사용할 수 없다. B11의 승인 역시 지정 증거 이관에 한정된다.

상위 C §38은 구현 증명 실패 시 구현/rollout 차단과 **별도 명세 변경 감사**를 요구한다. 검토한 문서에는 프로젝트 소유자의 새 정식 규범 개정 자체를 불변 금지한 조항이 없었다. 따라서 N01처럼 B/C와 G1을 함께 명시 변경하고, 독립 N02·실제 개별 위험 결정·새 exact 규범/적용 승인·지정 적용·비참여 일치 검증·명시 완료 사건을 요구하는 변경 경로는 문서상 정합하다. 이 권한 분석의 PASS는 현재 예외 권한 발급이나 과거 승인의 확대가 아니다.

실제 목적지와 사본 적용 결과는 다음과 같다. 세 기존 목적지는 현재 bytes를 보존했고 새 목적지는 여전히 존재하지 않는다.

| 정확한 논리 목적지 | 현재 기준선 SHA-256 | 사본 적용 결과 SHA-256 |
| --- | --- | --- |
| `docs/t66/b/t66b-hot-cold-design.md` | `e2d820ba71018414934ad4a9b3667961c209f93fe0b5b5dd2d0a3233ea76b279` | `d0cdb4650035f53187c06dbdeccac83245a6e45a70b35100d6dfd386e5de9bf9` |
| `docs/t66/c/t66c-delta-sync-protocol.md` | `5d3f03a0e61c6d504cf8efd5de0c8ee446b9c0a0b4a45a367f6d366a4fbf94c9` | `f9efad30e4d324755a17bd892d4522a2a44c41ca3f8cd7a440630adacf277661` |
| `docs/real-device-gate-g1-safety-contract.md` | `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0` | `b11b600cd250705591ce2dab97c35597823b5513d4817ad2e01b5f49b8b289a8` |
| `docs/real-device-gate-g2-restricted-campaign-exception.md` | `ABSENT` | `25e01630e369cfb6f0a103cc26511ed396fbc3e3d9b6718af3cb3f6f9ac017e1` |

B의 §29-G2는 소형 smoke의 pre-F entry만, C의 §34-G2/§38-G2는 상위 적용 예외와 entry/proof 수용 구별을, G1 S1은 누적·비면제·S7 편입 gate의 지정 부분 우선순위를 연결한다. 새 G2 X1–X9는 그 연결이 부여한 여덟 예외의 세부 내용이다. 원 finding·역사 승인·S7의 원 JSON bytes를 다시 쓰지 않는다. 편입 자료의 과거 G1 hash는 기준선 신원으로 남으며 새 G1 after hash와 완료 기록을 별도로 대조해야 한다.

네 문서는 **한 조정된 효력 단위**다. 네 파일 write의 filesystem 원자성을 주장하지 않는다. 모든 연결 조항과 X1이 전체 승인 bytes·독립 일치 PASS·완료 사건 이전에는 효력을 금지한다. 15개 불완전 부분집합을 문서 의미로 대조했으며 모두 DENY다. 네 파일이 모두 존재해도 owner 결정·범위/시간창·효력 사건이 없으면 DENY다. 부분 적용은 승인하지 않으며 일부 파일의 문구만으로 요구가 약해지는 해석도 허용되지 않는다. [네 목적지 검토](benchmarks/real-device-gate-g2-n02/four-destination-amendment-review.json).

**패치의 독립 정적 적용**

현재 목적지 bytes와 후보에서 unified diff를 독립 재생성해 통합 patch와 byte 단위로 일치함을 확인했다. 기존 세 문서의 변화는 삽입뿐이며 원문 bytes는 유지된다. N02 전용 폐기용 디렉터리에 세 기준선 문서만 복사한 뒤 `patch --batch --fuzz=0 --no-backup-if-mismatch -p1`의 dry-run과 사본 적용을 수행했다. 두 종료 코드는 0이며 offset·fuzz를 사용하지 않았다. 네 결과는 후보 bytes와 정확히 같고 위 해시로 재현됐다.

실제 저장소 목적지나 Git index에 패치를 적용하지 않았다. 문서 사본 정적 적용은 규범 효력·실행기 집행·기기 안전 증명이 아니다. 작업 소유 임시 문서 사본은 정리했으며 결과 hash·구간별 diff hash·방법은 [패치 무결성·시뮬레이션](benchmarks/real-device-gate-g2-n02/patch-integrity-and-simulation.json)에 보존했다. 임시 디렉터리 최종 문서 크기는 261,990바이트였고 기존 파일·cache·DB는 삭제하지 않았다.

**NC01–NC08의 개별 판단**

[독립 충돌 검토 JSON](benchmarks/real-device-gate-g2-n02/nc01-nc08-independent-review.json)에 각 항목의 정확한 기존 원문/경로/locator/hash, exact 예외 문장, 보호 처분, 손실, 통제, 운영 가정, 잔여 위험, 필수 증거, 독립 수용 기준, owner 결정 및 목적지·우선순위를 각각 기록했다. 여덟 항목 모두 명시적 완화이며 동등 보호로 분류하지 않았다.

| ID | 독립 판단 및 잃는 보호 | 보상 통제·필수 판정 | 개별 owner 결정 |
| --- | --- | --- | --- |
| NC01 | 실제 channel/receiver의 원자 결합 대신 관측 기반 선택. 관측 사이 오대상/다른 수신자 가능성이 남는다. | SC02–04/07, actual binary·selector/세대 부정 자료와 등록·각 action guard. 불일치 시 admission 0, 실제 승인 밖 효과는 FAIL_VIOLATION. | RR-NC01 |
| NC02 | 설치 전 P→U/C 신뢰 결합 대신 기존 owner 자료·가시 확인·고정 조회. 초기 오등록 위험이 남는다. | SC02/03/07/12, 사전 자료 출처와 F 독립 등록 대조. 공란·새 trust·설치 후 소급 key 인증 금지. | RR-NC02 |
| NC03 | OS 전역 reachable-set 독점 대신 runner 경계와 운영 책임. 다른 process/FD/server·기기 경로의 전역 배제를 보장하지 않는다. | SC01/03/04/10, actual runner/OS·FD/IPC/egress 부정 자료와 D USB 비노출 수용. 단일 기기 진술은 기술 proof가 아니다. | RR-NC03 |
| NC04 | 실제 무효화 뒤 모든 새 write 0 대신 관측/취소 전달 뒤 controller admission 0. 기존 child 회수 전 미전송 bytes와 remote 지속이 남는다. | SC08/09/11/12, event/observe/latch/실제 제출/kill/reap/task/commit/ACK 분리. UNKNOWN과 실제 위반 구별·추가 명령 금지. | RR-NC04 |
| NC05 | 기존 전체 CP/IP 독립 수용 진입 gate 대신 새 SC01–12의 범위별 수용. G1 proof 없이 더 약한 모델로 진입한다. | SC 전부 필수, 비예외 PR 실질 보호·범위별 독립 수용·별도 grants 유지. 새 SC 결측은 위험 서명으로 면제 불가. | RR-NC05 |
| NC06 | 현재 전면 DENY·emulator-only에서 새 operational/validation profile을 한정 허용할 미래 경로. 새 실행 경로 결함 위험이 생긴다. | 별도 구현 GO·중앙 기본 DENY·literal plan·trusted digest와 C/D 수용. 현 코드/FS1 승격·flag·wrapper 우회 금지. | RR-NC06 |
| NC07 | formal F 이후 진입을 소형 smoke 한 번에만 앞당긴다. 해당 entry의 선행 순서 보호를 약화한다. | 네 목적지 정합·격리 목적·결과 재사용 금지. whole-F/Android·최종 T6.9/R1/rollout/배포 의무 유지. | RR-NC07 |
| NC08 | phone 전체 memory/app-data/PM·열·전력 hard cap 대신 일부 soft threshold. 감시 사이 초과와 원격 소비가 남는다. | SC09/11/12, cap/cap+1·감시/초과 처분과 실제 E 예산. 전체 phone hard cap을 계속 요구하면 사용 불가. | RR-NC08 |

원 G1 PR02·PR08–11의 artifact/tool 대응, 최종 앱 격리·fresh package·replay 금지, 소유 synthetic backend, 고정 literal 효과·순서·예산, bounded journal·UNKNOWN 처분은 유지된다. 바뀌는 것은 열거된 보증과 formal admission 관계뿐이다. 어느 위험 수용도 원 F01 기술 proof가 아니며 G1 proof 수는 **0/12**다.

**캠페인 제한과 원칙 보존**

예외는 제안 ID `G2-RESTRICTED-S23FE-C01`의 한 owner·한 Galaxy S23 FE·한 비갱신 physical 연결/세션 시도와, 별도 승인할 `G2-RESTRICTED-S23FE-C01-VAL1`의 고정 검증 범위뿐이다. 현재 두 ID는 미승인이다. 규범 결정에 exact owner/device binding·UTC 시작/종료 시간창이 없으면 무효다. 최종 serial/variant/build/API/ABI·source/tool/APK/cert·모든 실제 argv/input/path/order·외부 신뢰 expected digest와 예산은 P01.E 전에 완성·동결·독립 수용해야 한다. 현재 없는 값을 추정하거나 연결 뒤 채울 수 없다.

별도 연결 grant의 고정 read-only 등록, 별도 첫 mutation grant의 install 최대 1회, 사전 고정 post-install 확인·독립 checkpoint, 이미 지정된 launch 최대 1회와 bounded 증거 수신만 허용할 수 있다. operation 분류 자체는 실행 manifest가 아니다. 범용 shell·자동 retry/복구·새 trust/pairing·device-wide 변경·개인/production/공유 데이터 접근·추가 probe는 금지다.

600초 연결 시계·120초 mutation grant age와 APK/요청/응답/합성 output·result·host evidence ceiling은 P01 제안 수치와 일치한다. 실제 승인값은 아니며 증가할 수 없다. 실제 action deadline·회수 grace·공간/RSS/app-data/열 threshold·validation 예산은 별도 GO/E에서 완성해야 한다. 미정 값은 실행 거부 조건이며 현 단계에서 승인값을 발명하지 않았다.

시간창 종료·철회·시도 소진·필수 검증 실패·동결 hash drift·identity/세대/감독/자원/증거 이상은 새 grants/admission을 DENY로 돌린다. 이미 admission한 단일 유한 action의 host 회수·remote 잔여·확보된 증거 처분에만 EX-NC04/X7이 남는다. 이 규칙은 새 command·갱신·late ACK에 의한 재개 권한이 아니다. 범위 밖 원 F01/G1, 금융 authority와 모바일 필수 wire/구조/복구/generation/Offline 경계, B03·whole-F·B11 이관·T6.9·R1/production 의무는 유지된다.

**Galaxy S23 FE의 기기·데이터 위험**

다음 분류는 제안된 예방·탐지·회수 요구와 남은 위험을 평가한 것이다. 실제 기기에서 예방·탐지를 입증하거나 복구 가능성을 수용한 결과는 아니다. [위험 평가 JSON](benchmarks/real-device-gate-g2-n02/device-data-risk-assessment.json)에 각 위험의 기존 객관 근거·미검증 부분·필수 후속 증거·owner 고지를 구별했다.

| 위험 | 예방·탐지 요구와 현재 근거 | 복구·수용 한계 |
| --- | --- | --- |
| 잘못된 APK 설치 | 외부 승인 digest·최종 compiled APK/ABI·봉인 stream·독립 checkpoint. 기존 admission은 부분 근거이며 최종 phone APK는 없다. | 맞는 bytes도 공급망 결함·오대상을 배제하지 못한다. 설치 뒤 자동 교체/삭제 없음. |
| 서명 불일치 | 독립 test cert와 prod signer 분리, 최종 APK·설치 instance 대조. 실제 최종 cert/custody는 미수용. | signer 일치는 안전한 코드·물리 신원 proof가 아니다. |
| 앱 격리 실패 | 독립 ID/signer·일반 UID·private synthetic·backup 제외·최종 permission/component allowlist. 현재 flavor 소스는 일부 근거. | package 이름·다른 계정만으로 격리 불가. 최종 merged APK와 runtime 검증 필요. |
| production/개인 데이터 접근 | 소유 backend/DB/fixture·exact route·private 경로, 실제 host egress/negative sink 검증. 현재 emulator URL 제한은 G2 proof가 아님. | 실제 금지 접근은 FAIL_VIOLATION이며 owner 수용으로 허용할 수 없다. OS/코드 결함 무피해 보장 없음. |
| 예상 밖 권한·지속 변경 | 최종 compiled allowlist·새 trust/특별 권한/정책 변경 금지. 현 manifest의 일부 제거 설정 확인. | PM/cache·APK/private·기존 trust 잔류는 예상 가능하며 원상 복원 미보장. |
| 합성 backend 이탈 | SC10 SP01–06/EC01–06, INTERNET 제거·peer/session·고정 relay·소유 socket/instance와 한도. 현재 relay는 없다. | target 안전 근거 결측은 BLOCKED다. RD03으로 면제 불가. |
| 저장·배터리 소비 | synthetic/host hard cap·여유/시간 threshold·cap 초과 거부. 실제 기기 여유·소비량은 미측정. | output 1MiB는 전체 app-data 상한이 아니다. 저장 고갈·소모·remote 소비 지속 가능. |
| 발열 | thermal 감시/중단 threshold·유한 입력/작업. 실제 threshold와 반응은 후속 검증 대상. | 관측 사이 과열·shared 부하를 막는 전체 phone hard cap이 없다. |
| host 취소 뒤 remote 지속 | latch 뒤 새 admission 0·host stop/reap·bounded 작업. 기존 host 회수 종결은 원격 종료 proof가 아님. | 미전송 bytes·PM/앱의 부분/durable 완료·종료 불명은 남는다. 600/120초는 remote hard stop이 아니다. |
| 부분 완료·ACK 유실 | 효과 전 durable claim·중복/재생성 replay 금지·독립 checkpoint. 현재 앱은 시작마다 smoke를 호출해 새 구현이 필요. | UNKNOWN은 성공·rollback이 아니다. 추가 readback/retry 없이 증거 고정. |
| 정리 실패·불확실 | 정상/실패 모두 자동 uninstall/clear/force-stop 금지, 확보 증거의 독립 사후 처분. | 잔류 수용과 추후 정리는 별도 owner 판단이며 완전 복구 미보장. |
| OS·공급망 결함 | source/dependency/tool·actual binary·최소 권한·target 대응 근거와 침해/상충 시 거부. | hash·서명·문서 PASS로 결함 부재/손실 0을 증명하지 못한다. 사고율·수치 확률 증거 없음. |

RR-NC01–08 외에 RD01(공급망), RD02(OS/개인 데이터·복구 한계), RD03(검증된 네트워크 구현의 잔여 결함), RD04(잔류)와 AS01–04의 운영 책임이 각각 고지되어 있다. 소유자의 한 기기 약속은 기술적 물리 독점 proof가 아니다. 새 필수 통제 결측이나 미검증 Samsung 안전 전제는 수용 가능한 일반 잔여 위험으로 옮기지 않는다. **위험 0·개인 데이터 손실 0·완전 복원·즉시 remote stop을 주장하지 않는다.**

**아홉 승인 경계와 SC10 의존성**

| N01 단계 | 별도 결정/수행 범위 | 다음 단계로 넘기지 않는 권한 |
| --- | --- | --- |
| A | N01 예외 초안 작성 | 독립 검토·위험/규범 승인 없음 |
| B | 이번 N02 독립 검토 1회 | owner 위험 수용·적용·기술 proof 없음 |
| C | 실제 owner의 12개 위험·AS01–04 개별 결정 | D 규범/적용 승인 없음 |
| D | exact 4개 목적지 승인·지정 적용·독립 일치·효력 사건 | 구현·검증·기기 GO 없음 |
| E | 별도 host 구현 승인, 원 P01.C | host 시험·emulator·기기 GO 없음 |
| F | 각각 별도 host/에뮬레이터·앱 lifecycle 검증과 독립 수용 | physical 접근·phone proof 수용 없음 |
| G | 원 P01.E 독립 preflight | owner 연결 grant 없음 |
| H | 원 P01.F 별도 연결/read-only grant·등록 보충 수용 | install/marker/launch 없음 |
| I | 원 P01.G 별도 첫 mutation grant·install checkpoint·고정 launch | retry·추가 command·자동 복구 없음 |

N01 단계 문자와 원 P01 C/D/E/F/G를 혼동하지 않았다. SC10의 E 입력은 SE01–04, SE05는 독립 판정 출력, SE06은 별도 F 등록 산출물, SE07은 별도 G grant·install checkpoint 뒤 launch 결과다. 자기 산출물·미래 F/G 결과를 선행 입력으로 요구하는 순환은 없다. D emulator 진입도 C host qualification·별도 GO·physical USB 비노출을 먼저 요구하고 아직 수집할 D 결과/SE05를 선행 요구하지 않는다.

R02는 R01-B01의 문서상 모호성만 종결했다. 실제 SC10 target 안전 적용성·C/D/E 수용을 발급하지 않았다. 접촉 없는 사전 안전 근거를 마련할 수 없으면 terminal BLOCKED이며 새 사전 phone probe를 끼워 넣을 수 없다. 첫 승인 launch에서만 남을 수 있는 가용성 실패도 retry/fallback/정책 변경 없이 종료한다.

[미서명 양식](benchmarks/real-device-gate-g2-n01/unsigned-exact-hash-owner-decision-template.json)의 12개 위험 선택·AS 책임·owner 출처/신원/서명·시간창·device binding·D 결정은 모두 미기입이다. N02는 양식을 채우거나 소유자 대신 서명하지 않았다. 파일 존재·해시·침묵·검토 PASS는 owner 결정이 아니다. [승인 경계 검토](benchmarks/real-device-gate-g2-n02/authorization-boundary-review.json).

**Finding과 종료 판정**

차단/비차단 finding은 각각 **0건**이다. 의도된 여덟 완화 자체를 결함으로 처리하지 않았고, 실제 필수 통제의 미구현·미검증을 비차단 편집 문제로 낮추지도 않았다. 그것들은 문서가 이미 유지한 후속 실행 blocker다. 이번 판정은 그 조건과 위험·권한이 결정 가능한 정도로 명시됐는지에 한정한다. [독립 finding 기록](benchmarks/real-device-gate-g2-n02/independent-findings.json).

권고하는 소유자 행동은 한 가지다. **소유자는 검증된 고정 패키지의 12개 잔여 위험과 AS01–04를 항목별로 수용·거부·보류하십시오.** 일반적인 위험 동의는 부족하며 어느 항목이라도 거부·보류·미결정이면 적용/사용은 DENY다. 전부 수용하더라도 D의 별도 exact 규범/적용 결정이 필요하다. 이번 리뷰는 이 판단을 대신하지 않는다. [결정 준비도](benchmarks/real-device-gate-g2-n02/owner-decision-readiness.json).

여기서 지정된 N02 검토 1회를 종료한다. 자동 수정·재심사·구현·검증·추가 감사 sequence를 시작하지 않았다. B03/T6.9 작업으로 범위를 넓히지 않았다.

**실제 수행과 보존**

이번 변경은 이 보고서와 새 N02 dossier뿐이다. 시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, index SHA-256은 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged 항목 SHA-256은 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`다. 기존 수정/미추적 파일을 기준선으로 보존했고 reset/stash/clean/checkout/rebase/restage/commit/push는 없다.

[시작 보존 기록](benchmarks/real-device-gate-g2-n02/preservation-before.json)의 기존 **8,307개** 내용 해시·외부 frozen sidecar **5개**, 역사 목록의 source lock **27개** 및 HEAD/index/staged를 종료 시 대조했다. 결과는 [보존·정적 검증](benchmarks/real-device-gate-g2-n02/validation-and-preservation.json), 새 산출물 신원은 [증거 manifest](benchmarks/real-device-gate-g2-n02/evidence-manifest.json)에 기록한다. 기록한 경로의 보존 확인이며 ignored cache/runtime·production 전체 전수 감사가 아니다.

샌드박스는 bwrap loopback 초기화 오류로 실행 전에 실패했다. 자동 검토를 거친 host shell에서 로컬 읽기·N02 문서 작성·폐기용 문서 사본의 정적 적용만 수행했다. 이를 기기 실행 경계나 G1 적격성 proof로 사용하지 않는다.

ADB(help/version 포함)·ADB server socket 요청·USB/Android 열거·접근·emulator 동작·물리 기기 접근·APK 설치·운영 API/데이터 접근·서비스/OS 정책 변경은 모두 0이다. 규범 원본·후보·실행 코드·기존 증거를 수정하지 않았다. 사용자 지시의 읽기 전용 문서 검토 범위에 따라 일반 AGENTS 검증 지침의 npm/backend/Flutter/Android build·runtime 시험은 실행하지 않았고 과거 PASS를 새 proof로 세지 않았다. 임시 DB/build/cache 생성·삭제도 없다. 소형 사본 정리만 산출물 위생 규칙에 따라 수행했다.

```text
REAL-DEVICE GATE G2-N02:
PASS

REVIEWER INDEPENDENCE:
SATISFIED

G2 CANDIDATE SHA-256:
1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb

G1 CONTRACT SHA-256:
679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0

NC01-NC08:
8 / 8

NORMATIVE DESTINATIONS:
4 / 4

PATCH INTEGRITY:
PASS

STATIC APPLICATION SIMULATION:
PASS

NORMATIVE AUTHORITY:
PASS

EXCEPTION SCOPE:
BOUNDED

COMPENSATING CONTROLS:
SUFFICIENTLY SPECIFIED

RESIDUAL RISK DISCLOSURE:
SUFFICIENT

AUTHORIZATION SEPARATION:
PASS

BLOCKING FINDINGS:
0

NONBLOCKING FINDINGS:
0

OWNER DECISION READINESS:
READY

OWNER RISK ACCEPTANCE:
NOT GRANTED

G2 EXCEPTION APPROVAL:
NOT GRANTED

G2 NORMATIVE APPLICATION:
NOT PERFORMED

ORIGINAL F01:
BINDING — UNRESOLVED

EFFECTIVE G1:
BINDING — UNCHANGED

G1 TECHNICAL PROOFS ACCEPTED:
0 / 12

OPERATIONAL ADB DISPATCH:
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

REPORT:
docs/real-device-gate-g2-n02-independent-exception-review.md

FINAL VERDICT:
PASS — G2 EXCEPTION PACKAGE READY FOR EXACT OWNER DECISION

NEXT ACTION:
소유자는 검증된 고정 패키지의 12개 잔여 위험과 AS01–04를 항목별로 수용·거부·보류하십시오.
```
