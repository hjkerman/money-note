# Repository Hygiene Batch 2 — 구현 완료 / 게시 차단

기준선은 `phase2/mobile-network / 1ccef3149fa2c23dda7cb5a315da4584a0492b2e`다. owner가 별도 Batch1 독립 감사 완료·수용을 명시 확인한 뒤 Batch2를 진행했다. 이 세션은 구현 세션이며 독립 최종 위생 감사는 후속 단계다.

## 범위와 처분

| 그룹 | 승인 후보 | 완료 | 원위치 보류 |
| --- | ---: | ---: | ---: |
| H06 과거 T6.6F 보고서 | 40 | 보관31 | 9 |
| H07 과거 gate 보고서 | 21 | 보관11 | 10 |
| H10 legacy benchmark | 688 | 보관11 | 677 |
| H20 staging dependency | 4 staging | 3 staging, 16,775개 항목 정리 | 불완전 staging1개와 dependency lock metadata9개 |

H06/H07 목적지는 각각 `docs/archive/legacy-performance/`, `docs/archive/device-gate/history/`다. H10은 `docs/archive/legacy-performance/benchmarks/` 아래 원 scope·상대경로를 유지하고 11개 bytes가 원본과 같다. 모든 역사 verdict·금융/성능 수치·owner 예외·음성 결과를 유지했다. 문서는 실제 Markdown 탐색 링크만 재배치했고 fenced 재현 코드는 편집하지 않았다.

정확한 old/new 경로·SHA, 보류 파일별 소비자/고정 경로 사유, 정리 항목과 측정은 [단일 실행 근거](../../benchmarks/repository-hygiene-batch2.json)에 있다. 보류는 완료 실패를 숨기는 것이 아니라 조건부 승인 범위의 명시적 처분이다. 예외를 없애려고 frozen manifest나 코드의 파일 경로를 수정하지 않았다.

## 보존한 예외

- H06/H07: SHA로 참조되는 문서, benchmark 도구의 실제 소비 경로, 불변 문서·기존 dirty 문서·benchmark README의 inbound 링크 대상은 남겼다. 현재 G1 O2 문서/proof, F01/G1/G2 조건, B03 source lock, T6.9 의무는 바꾸지 않았다.
- H10: 실행 재현 코드의 `__file__`·부모 경로·import·출력 계약, glob/디렉터리 열거 소비자, 동결 압축 근거와 benchmark Markdown, 내장 상대 경로를 해소하지 못한 파일을 보존했다. 원 source/test/CI/metadata 소비자를 바꾸는 우회는 하지 않았다.
- H20: `9e7ea7afddd6-4nnntn8h`는 dist/image 기록이 없어 실패·중단 복구본일 수 있으므로 통째 보존했다. 정리한 staging은 `5d44ce318876-4ihpk5d_`, `5d44ce318876-9ytjp1ls`, `f93e2cf07d4f-idv04leh`다. source·dist·image 기록·lockfiles·복구 metadata는 그대로다. 운영 current/previous 배포를 조회하거나 변경하지 않았다.
- 로컬 기존 `.build.lock`을 생성/재작성하지 않고 비차단 배타 lock을 획득해 dependency 정리 동안 유지했다. current-user cwd/fd/maps 및 build/test 도구를 검사했다. OS 세션 서비스는 build/test와 구분하며 접근 제한 host 전체를 완전히 관측했다고 주장하지 않는다.
- symlink는 대상에 진입하지 않고 승인된 cache 안의 링크 자체만 제거했다. hardlink는 경로와 inode를 구분해 원본 데이터나 외부 링크를 수정하지 않았다.
- H11 비공개 최초 metadata와 R5, 기존 dirty/untracked 작업, 활성 fixture, P2-N01 gzip 검증, DB·자격 증명·기기 증거는 제외했다.

## 계측과 검증

삭제 경로별 할당량 합은 **358,313,984B**, hardlink 중복을 제외한 회수 대상 inode 할당량은 **324,939,776B**다. 실제 정리 직후 가용 공간 증가는 **311,623,680B**다. 디렉터리·새 검토 근거·동시 host 활동이 있어 세 수치를 동일시하지 않는다. 보관 이동은 용량 절감으로 세지 않는다.

사전 rebase guard가 불변 FS1 문서의 `P01.md:709` 참조를 발견해 해당 task-owned 이동을 verified before-image로 되돌리고 P01을 제외했다. 원문·고정 문서가 변경된 채 남지 않았다. dependency 정리 중 자체 hardlink unlink로 esbuild의 nlink가 2→1이 되어 엄격한 신원 검사가 중단됐다. 나머지 inode/mode/bytes/mtime가 같음을 확인한 뒤 자체 unlink 수만 정확히 반영해 같은 build lock 아래 완료했다. 관련 원인·확인·정리 목록을 근거에 보존한다.

보호 SHA·범위 밖 metadata·불변 문서·H10 원문 bytes·보류 항목·배포 산출물을 확인하고 baseline 대비 신규 링크/anchor 오류0을 요구한다. 검증기는 파일과 디렉터리 링크 및 fenced code를 구분하며 과거 검사기의 진단 수와 단순 비교하지 않는다. application source가 바뀌지 않아 build나 넓은 기능 suite는 실행하지 않는다. index의 기존 staged 항목은0개였고 사전 검증에서도0개다. index byte hash는 갱신되어 이를 초기 SHA와 함께 기록하며 staged 내용 보존과 구분한다.

실제 최종 검사: tracked 파일 SHA2,178개·범위 밖 metadata22,567개 대조, 불변 경로18개 보존, 링크2,209개·anchor34개에서 baseline/최종 신규 진단0개다. H10 자료11개는 byte-identical하며 dependency metadata9개·실패 가능 staging1개와 기존 dirty12개를 보존했다. runtime source/test/CI의 경로는 수정하지 않았다. task-only staged121개 old/new 경로 전체를 허용 목록 및 실제 파일 bytes와 대조하고 diff check를 통과했다.

## 최종 구조와 종결

현재 규범·운영·호환성 문서와 고정 경로 자료는 기존 위치를 유지한다. 완료 기록은 `archive/phase1`, `phase2`, `phase3`, `legacy-performance`, `device-gate/history`, `repository-hygiene`에서 찾는다. current indexes와 roadmap의 실제 탐색 링크를 갱신했다. 역사 JSON 안의 당시 경로·SHA 문자열은 보존하고 실행 근거의 대응표를 제공한다.

**구현 종료 조건 충족 / 최종 종결은 게시 대기:** 승인된 안전 작업을 완료하고 모든 조건부 예외·R5/H11을 보류/보호로 명시 처분했다. 구현 commit은 `75d09a75b2f9c83f026333b083edb78e15ee7128`이다. 원격 push와 이후 조회는 `Permission denied (publickey)`로 실패했고 SSH 인증 에이전트 연결도 없었다. 새 자격 증명을 취득하거나 인증 설정을 변경하지 않았다. 현재 원격 tip은 재검증하지 못했고 마지막 성공 조회는 기준선 `1ccef3149fa2c23dda7cb5a315da4584a0492b2e`였다. 기존 인증 복구 후 같은 개발 branch에 게시하고 원격 일치를 확인해야 최종 CLOSED로 기록한다. 다음은 독립 최종 위생 감사이며 Phase4·main 병합·운영 배포는 미착수다.
