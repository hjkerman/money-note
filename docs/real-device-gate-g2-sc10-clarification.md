# Real-Device Gate G2-SC10 — R01-B01 한정 명확화

**READY — SC10 CLARIFICATION READY FOR TARGETED INDEPENDENT REVIEW.** SC10의 사전 안전 수용과 실제 통신 가용성을 구별한 수정 후보를 작성했다. 이는 저자의 finding 대응이며 독립 종결은 R02 대기다. 실제 Galaxy S23 FE 적용성·SC10 기술 적격성·E 수용은 **미입증/미수용**이다. G2는 승인·적용하지 않았다.

유효 [G1 계약](real-device-gate-g1-safety-contract.md)의 SHA-256은 `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`로 일치한다. 원 F01과 G1 S1의 최초 신원 결합·실제 승인 채널/수신자 결합·OS 강제 기기 격리는 계속 구속된다. 원 F01은 **BINDING — UNRESOLVED**, G1은 **BINDING — UNCHANGED**, G1 기술 proof는 **0/12**, 운영 dispatch는 **BLOCKED**다. 단일 기기 진술을 OS 독점으로 바꾸지 않는다.

**확인한 단일 finding.** [G2-R01 독립 리뷰](real-device-gate-g2-r01-independent-safety-review.md)와 [원 finding JSON](benchmarks/real-device-gate-g2-r01/independent-findings.json)의 정확한 ID는 **R01-B01**, severity는 **HIGH**, 유형은 `CONTRACT_QUALIFICATION_BOUNDARY_AMBIGUITY`다. 제목은 “SC10의 S23 FE 적용성에 대한 E 사전 수용 기준이 닫혀 있지 않다”다. 원 리뷰의 PARTIAL 및 finding은 역사 원문 그대로 보존했다.

원 trigger는 SC10(`/controls/9`)과 D의 최종 APK/ABI·peer/SELinux 증거 요구(`/stages/3`), E의 모든 SC 수용(`/stages/4/objective_pass_criteria_ko`) 사이에서 **Samsung target 대응 근거와 G 첫 launch에서 알게 되는 가용성 실패의 경계가 정해지지 않은 것**이다. R01은 미구현 자체나 정확 단말의 성공 통신 사전 실증을 새 의무로 삼지 않았다. 그 구분을 그대로 따른다. P01 manifest 항목 10개와 R01 항목 11개의 현재 bytes, 관련 출처 pin·G1 효력 의존성을 다시 대조했다. [출처·finding 확인](benchmarks/real-device-gate-g2-sc10/source-and-finding-verification.json).

**정확한 SC10 안전 속성.** 최종 격리 APK와 relay가 승인된 제한 stream/peer/session 및 소유 합성 backend 밖으로 네트워크 효과를 내지 않고, 인증·오류·한도 실패를 외부 효과 전에 거부하는 것이다. 이는 기존 G2의 정상 host/Android 신뢰 범위 안의 속성이며 원 F01의 원자적 물리 binding·OS 전역 독점·실제 사건 cutoff 증명이 아니다. 원래 SC10의 INTERNET 제거·같은 승인 transport의 제한 localabstract 경로·고정 `127.0.0.1:18081` 합성 backend·peer/session·route/bytes 제한·fallback 금지는 그대로다.

현재 앱은 INTERNET과 emulator 전용 HTTP 경로를 사용하며 제한 relay가 없다. 이 사실을 새 증거로 포장하지 않는다. INTERNET API나 connected UNIX socket의 peer credential API 존재는 일반 지원 근거일 뿐, Samsung build의 정책·승인 session 결합 증명이 아니다. peer credential 조회는 예외를 낼 수 있으므로 결측 시 허용할 수 없다. [INTERNET API](https://developer.android.com/reference/android/Manifest.permission#INTERNET), [LocalSocket API](https://developer.android.com/reference/android/net/LocalSocket). 제조사별 SELinux 정책이 있으므로 emulator 성공을 Samsung 정책 수용으로 옮기지 않는다는 판단을 유지한다. [AOSP SELinux 정책 설명](https://source.android.com/docs/security/features/selinux/customize).

**E에서 판단할 대상과 증거.** E는 소유자 단말의 현재 상태를 미리 관측했다고 주장하지 않고, **사전에 동결한 정확한 목표 variant/build/API/ABI 프로필의 안전성**을 판단한다. E의 수용 범위는 이후 기존 F 등록이 그 사전 프로필과 일치하는 instance에만 적용된다. F에서 예상 값을 보충·변경하지 않는다. 제품명·소유자 진술만으로 기술 대응을 수용하지 않는다.

| 구분 | 필요한 증거와 수용 단계 | 지금의 상태 |
| --- | --- | --- |
| SE01 예상 target 프로필 | 소유자가 이미 보유한 식별 기록, exact serial/variant/build/API/선택 ABI와 필요한 보안 전제. E에서 scope를 대조하며 실제 instance는 F에서 확인 | 실제 단말 자료 미제공. owner assertion은 technical proof 아님 |
| SE02 고정 구현·artifact | 별도 C에서 source/tool/dependency/APK/signer/merged manifest/host 정책/fixture와 enforcement 경로. C 감사 후 E 동일성 대조 | 구현·수용 없음 |
| SE03 기계 검사 원자료 | 별도 C/D의 기존 HC10·EV07/08/12 안에서 IP 금지, wrong/missing peer/session, 오류/fallback 0, cap/cap+1, backend 이탈 거부. 실행 범위별 독립 검토 후 E 대조 | 수집·수용 없음. 새 campaign 아님 |
| SE04 Samsung OS/ABI 대응 행렬 | 각 안전 전제의 해당 build 대응 출처, emulator와 차이 및 안전 영향. E의 필수 독립 판정 | 해당 target 행렬 미확보·미수용 |
| SE05 독립 E 판정 | SE01–04와 SP/EC별 근거·결론·scope/만료를 비참여자가 기록 | 미수용. 본 문서로 대체 불가 |
| SE06 실제 instance 대조 | E 이후 별도 owner F grant의 기존 read-only 등록과 독립 보충 검토 | 접촉 필요·현재 미승인. E 입력 아님 |
| SE07 첫 launch 가용성 결과 | F 수용·별도 owner G grant·기존 install checkpoint 뒤 고정 launch 1회와 사후 처분 | mutation 필요·현재 미승인. E 입력 아님 |

SE04의 객관 기준은 보안에 필요한 **모든** target 전제를 해당 build에 대응하는 인증 가능한 OEM/firmware/정책/ABI·source 근거로 지원하거나, 특정 전제가 달라도 고정 코드와 C/D 증거상 안전 경계는 유지되고 거부/기능 실패만 늘어남을 입증하는 것이다. 출처·서명 체인이 없는 임의 mirror의 hash를 공식 증거로 부르지 않는다. generic AOSP/API/emulator나 소유자의 “동작할 것”이라는 진술만으로 행을 닫을 수 없다. vendor 차이가 허용 peer·egress 권한을 넓힐 가능성이 미검증이면 **안전 결측**이다. 성공 통신만 미확정이고 모든 안전 경계가 입증된 경우에만 가용성 항목을 남긴다. 현재 이러한 OEM 자료를 확보·인증했다는 주장은 없다.

[증거·수용 명세](benchmarks/real-device-gate-g2-sc10/sc10-evidence-and-acceptance.json)는 SP01–06을 IP egress 금지, peer/session 결합, 오류 시 fallback 0, 한도, 소유 backend 제한, target OS/ABI 대응으로 정의한다. E는 아래 여섯 기준을 **전부 PASS**로 독립 수용해야 한다.

| 기준 | PASS 조건 |
| --- | --- |
| EC01 | 사전 target/plan/선택 ABI가 구체적이고 artifact/runtime과 scope가 일치한다. 실제 phone 확인과 구별한다 |
| EC02 | SP01–05의 고정 구현·compiled artifact·C/D 부정 원자료·독립 수용이 모두 있고 상반 증거가 없다 |
| EC03 | 모든 보안 관련 Samsung/ABI/SELinux 전제에 지원 근거 또는 안전 비의존성 입증이 있다. 미검증 안전 전제 0 |
| EC04 | 남은 항목은 가용성뿐이며 오류 시 terminal 거부·fallback/추가 시도 0이 근거로 닫힌다 |
| EC05 | 출처·hash·역할·scope·만료가 완전하고 독립 승인 기록의 expected digest와 일치한다 |
| EC06 | 구현/실행 비참여 E 검토자가 EC01–05와 SP01–06을 수용한다. 나머지 SC·기존 E 요건도 모두 유지한다 |

한 항목이라도 FAIL/MISSING/CONTRADICTED면 **E REJECTED, 캠페인 BLOCKED**다. 조건부 안전 PASS·unknown=safe·첫 phone 실행으로 안전 결측을 보충하는 경로는 없다. 필요한 안전 근거가 접촉 없이 성립하지 않으면 이 범위에서 끝낸다. 사전 기기 조회나 다른 신뢰/위험 가정이 있어야 해소된다면 별도 owner·규범 결정이 필요한 BLOCKED 사안이며 이번 명확화에 포함하지 않는다.

**순환 권한이 없는 순서.** E의 입력은 SE01–04이고 SE05는 판정 산출물이다. SE06은 F grant 뒤 등록 산출물, SE07은 별도 G grant 뒤 결과다. 두 물리 산출물은 E 선행 요건이 아니다. F grant 전제에 F 자체의 미수집 산출물을 넣지도 않는다. [단계 의존 확인](benchmarks/real-device-gate-g2-sc10/stage-e-dependency-check.json).

F는 기존 고정 identity/build/ABI 대조만 허용하고 SC10 socket/네트워크/SELinux probe·설치·marker·launch를 추가하지 않는다. 불일치하면 세션 폐기와 G 거부다. G의 첫 승인 launch에서 안전성이 유지되는 기능/연결 실패를 처음 알 수 있다. 그때는 재시도·fallback·권한/정책 변경 없이 종료하고 이미 받은 증거만 처분한다. 원격 결과/종료 불명은 **UNKNOWN_QUARANTINED**, 승인 밖 forwarding/효과는 **FAIL_VIOLATION**이다. 실패를 해석하기 위한 추가 readback/reconnect는 없다. G의 성공도 E 결측을 소급 수용하지 않는다.

**증거 신원과 만료.** 각 증거는 생성 주체/역할·시각·source/tool/APK/signing/compiled manifest·선택 ABI·relay/host 정책·합성 fixture·expected target·raw 입출력·독립 수용·plan digest 참조를 묶는다. expected hash는 후속 독립 승인 기록에서 받아야 하며 manifest나 저자의 hash만으로 출처·승인을 주장하지 않는다. C/D 결과는 해당 exact 범위에만 유효하고 E 수용은 명시 승인 시간창/단일 비갱신 세션에만 유효하다. 새 시간 예산을 추가하지 않는다. 범위/만료 결측·source/target/권한/세대 변화·상반 증거·철회·기존 만료에서 폐기하며 late ACK로 복구하지 않는다.

소유자 진술, 한 기기 운영 가정, 기계 검사, 비참여 독립 수용, owner 실행 권한은 서로 다른 상태다. 이번에는 문서·hash·정합 검사만 했고 후속 C/D/E의 기술 수용을 수행하지 않았다. E PASS나 향후 R02 PASS도 F 연결 또는 G 최초 mutation grant가 아니다. 현재 binding F01/G1을 일반 위험 동의로 면제할 수 없다.

**최소 수정과 정확한 신원.** 원본 P01/R01 문서와 JSON은 덮어쓰지 않았다. 수정 후보는 원 P01 전체 사본의 SC10 블록 삽입 1개, SC10 qualification 한 값, E objective 한 값만 바꾼 새 bundle이다. D 및 다른 SC/기준·예산·단계·NC01–08 변경은 0이다. [적용하지 않는 redline](benchmarks/real-device-gate-g2-sc10/targeted-correction.redline.patch), [전후 값·해시·변경 pointer](benchmarks/real-device-gate-g2-sc10/targeted-correction-and-hashes.json).

- 원본 `docs/real-device-gate-g2-p01-restricted-campaign-proposal.md`: `d36ecef2941563178f17063aa16013c1008859223fbf171cccd84ff51330b7c8`
  새 후보 `docs/benchmarks/real-device-gate-g2-sc10/corrected-proposal-candidate.md`: `1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb`

- 원본 `docs/benchmarks/real-device-gate-g2-p01/safety-controls-and-residual-risks.json`: `556eb32926162c7ff94662f2483c7cab27c136a2593a7b5ef80c822ef69674ab`
  새 후보 `docs/benchmarks/real-device-gate-g2-sc10/candidate/safety-controls-and-residual-risks.json`: `e64de552e48ca94535b603200e8b812e591cd2602eeff952b33d5e8693489c2f`

- 원본 `docs/benchmarks/real-device-gate-g2-p01/finite-authorization-and-validation-plan.json`: `3fa684c20dea2178179595c1eb325ecefcaf78d78dd5f4f2cfd52c4bb4b9c640`
  새 후보 `docs/benchmarks/real-device-gate-g2-sc10/candidate/finite-authorization-and-validation-plan.json`: `1d144429b3ac432554de355ecce2416790b74a34eca2efa96f529361addb470a`

대표 [수정 제안 후보](benchmarks/real-device-gate-g2-sc10/corrected-proposal-candidate.md)의 SHA-256은 `1735d0c4cdf1b6996ea4fa08379d291b36510dd191e1763090e3c6179c0b4beb`다. 후보는 편입하는 SC10 증거 명세의 hash도 본문에 고정한다. 사본의 기존 상대 링크는 원 목적지 `docs/` 기준이며, SC10/E의 두 값만 새 JSON 사본과 편입 명세로 읽는다. 원본에서 복사한 나머지 상태/검사 이력은 P01 당시 기록이다. 후보 또는 redline을 원 목적지에 적용하지 않았다.

**독립 검토 인계와 보존.** [R02 인계](benchmarks/real-device-gate-g2-sc10/r02-independent-review-handoff.json)는 R01-B01 한 건의 targeted 독립 검토 1회만 정의한다. 현재 독립 검토는 수행하지 않았다. R02는 원문·최소 diff·SP/EC·출처/만료·순환 부재·기존 제한 보존을 대조해야 하며, PASS해도 문서 명확화 수용만 뜻한다. 새 구현·기기 캠페인·자동 재감사는 없다.

종료 대조에서 기존 8,262개 경로·외부 frozen sidecar 5개·source lock 27개와 HEAD/index/staged가 보존됐다. 결과는 [보존·정적 검증](benchmarks/real-device-gate-g2-sc10/validation-and-preservation.json), 새 자료의 hash는 [증거 manifest](benchmarks/real-device-gate-g2-sc10/evidence-manifest.json)에 기록한다. 코드·binding 규범·B03·dispatch 변경 0, ADB/help/version·emulator·USB/physical 접촉·APK 설치·production 접근·기술 proof 수용 0이다. 정적 문서 작업만 수행했으므로 npm/backend/Flutter/Android runtime 검증을 실행하지 않았고 과거 PASS를 새 증거로 집계하지 않았다. 임시 DB/build/cache 생성·삭제는 없으며 정리는 NOT APPLICABLE이다. N01/F02/F03/FC01 독립 종결·T6.9 DEFERRED·R1 CLOSED·production 미승인·commit/push 없음도 유지한다.

다음 조치는 **비참여 독립 검토자가 고정된 수정 후보와 redline을 대상으로 R01-B01 한 건의 R02 검토 1회만 수행하는 것**이다.
