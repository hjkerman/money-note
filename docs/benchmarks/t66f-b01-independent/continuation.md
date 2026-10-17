# B01 이후 Phase B의 남은 gate

이 문서는 분류와 후속 checklist다. 아래 작업은 B01에서 실행하지 않는다.
원 Phase B §34의 한계를 변경하거나 없애지 않는다. 규범은 `docs/t66/c/t66c-delta-sync-protocol.md`다.

| 남은 항목 | 분류 | 실제 binding·현재 증거 | 후속 소유자·완료 gate |
|---|---|---|---|
| H/D 고정 N=1k/5k/10k/50k/100k | A | §35가 규모와 rows/bytes/HTTP/RTT/memory·median/p95를 명시. 이전 독립 두 크기는 전체 grid가 아님 | Phase B continuation: 독립 HTTP/SQL/object 계측으로 전체 grid 및 no-full-N 정상 경로 증명 |
| full gzip/Brotli 비교·framing/CPU/RTT | A | §34 성능 gate가 F 감사 앞에 있고 §35가 실제 비교 비용을 요구. 압축을 제품에 활성화하는 허가가 아님 | Phase B continuation: 고정 synthetic 비교군과 측정 단위/overlap·cold/steady-state 분리 |
| median/p95 | A | §35 scaling 감사 요구. 이전 single HOST sample로 충족하지 않음 | Phase B continuation: 반복 표본·환경·분포를 보존 |
| E3 I25 독립 cost closure | A | I25의 정상 full history fetch/hash/serialize/write 0과 changed-frontier bound. 이전 source·두 크기 증거는 보존 | Phase B continuation: 큰 grid, fallback·restart와 비용 단위까지 통합해 판정 |
| 전층 storage/resource cost | A | §35의 bytes hashed/validated/written, pin/graph accounting; 이전 두 크기와 Frozen 숫자는 한정 증거 | Phase B continuation: 전체 D→E workload·cold/steady/fallback 및 실제 SQL/pin/objects |
| 추가 authority race | A | I1/I14·§25 current authority/no-await·§29 Frozen 보호는 필수. 사용자 18-row matrix의 새 실제 HTTP 전수 구성은 기존 보고서에서 미완료 | Phase B continuation: 누락 조합을 직접 wire/SQL/legacy/pins oracle로 보완; B01의 기다림 중 auth/cancel 사례만으로 전체를 닫지 않음 |
| 독립 protocol negative 주입 | A | I3–I13/I22·§36 invariant와 §37 negative 계획. 단순 checklist 개수를 pass count로 바꿀 수 없음 | Phase B continuation: 기존 suite와 독립 주입의 공유 oracle·coverage gap을 구분하여 필수 invariant 증명 |
| 추가 backend DB identity | A/B | B01의 A/B HTTP 두 경계와 원 actual-open/ABA 6개는 새 회귀 증거. 전체 integrated identity/lifetime matrix를 대신하지 않음 | Phase B continuation: 이미 통과한 사례는 합치고 남은 경계만 보완 |
| 이전 real HTTP/금융 bytes·C1/closure·E4 source | B | 원 독립49·실제 SIGKILL7·authority/race10, Flutter1503/2 SKIP는 원 범위·한계 그대로. B01의 product tree diff는 0 | Phase B continuation: 보존 source identity와 case mapping을 연결하고 미검증만 보완; 기존 FAIL를 PASS로 재작성하지 않음 |
| backend 전체 회귀 | B, B01 완료 gate | 이번 두 full run의 실제 exit/JUnit/terminal이 PASS여야 이 항목만 닫을 수 있음 | B01 독립 검증; continuation이 추가 변경을 만들면 해당 새 source에서 다시 검증 |
| R1 Large Restore/MW | C | §31이 별도 chunk/hash/bounded staging/backup/atomic apply/receipt 계약과 activation prerequisite를 정함. §34 전체 F 의존성에도 R1이 포함됨 | 별도 R1 승인·구현·독립 검증. B01에서 구현하지 않으며 전체 F 완료·activation gate를 면제하지 않음 |
| migration/old-binary/server rollback | C/A | §33의 현재 isolated source/legacy parity 증거는 보존. R1/activation에 연결된 실제 migration·rollback proof는 남음 | R1/전환 담당 + continuation auditor: 적용 단계에 맞는 before/after-activation recovery 증명; silent old-B switch 금지 |
| Android VFS/pragmas/I/O error·power loss | D | §26은 실제 driver 대조와 power-loss 범위를 IMPLEMENTATION PROOF REQUIRED로 두고 미증명 시 rollout MUST 차단. HOST SIGKILL은 hardware power loss가 아님 | Android/device 담당 + 별도 독립 감사. 실기기 부재는 기록하고 rollout gate는 CLOSED로 유지 |
| 실기기 절대 latency | D | §35는 device 절대 latency 목표를 post-T6.6 gate 전에 정하지 않는다고 명시. 고정 절대 목표를 현재 F에 임의 추가하지 않음 | post-T6.6/device performance 담당. HOST 결과를 실기기 결과로 전용하지 않음 |

A는 현재 Phase B 요청의 필수 독립 증명, B는 기존 증거의 범위 보존·정리, C는 별도 R1/전환 소유,
D는 현 HOST 환경으로 충족할 수 없는 기기/activation 증명이다. 복합 항목은 표에서 관계를 명시했다.

§26은 미검증 Android proof가 **rollout을 차단한다**고 명시한다. 이를 B01 결함이나 실제
power-loss test 완료로 바꾸지 않는다. 규범에 별도 `Phase B`라는 이름의 독립 exit 정의는 없다.
전체 F 완료를 선언할 때에는 §26/31/33/34/35의 남은 proof를 승인 범위에 맞게 명시 판정해야 한다.
R1이 별도 소유라고 해서 §34의 전체 F 의존성을 생략할 수 없다.

B01 통과 시 허용되는 다음 작업은 별도 **T6.6F PHASE B CONTINUATION**뿐이다.
현재 Phase B/F는 미완료이며 R1·general-user segmented Offline·배포 gate는 열지 않는다.
