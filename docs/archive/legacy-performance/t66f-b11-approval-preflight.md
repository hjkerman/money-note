# T6.6F-B11 — 소유자 승인 접수와 적용 전 책임 지정 충돌 검토

**소유자 승인은 접수했다. 구속 개정은 적용하지 않았다.** 원 B11 개정문의 책임 지정 형식과 이번 승인의 역할 지정 사이에 충돌이 있어, 사용자가 지정한 ‘충돌 시 적용 전에 중단하고 별도 명시 결정 요청’ 절차를 따른다. 승인 권한이 없어서 중단한 것은 아니다. 현재 승인 권한자는 이번에 명시적으로 승인한 프로젝트 소유자다.

## 1. 승인 범위와 현재 상태

변경 ID는 `T66F-B11-TRANSFER-01`, 선택은 Option 3이다. 실행 책임은 T6.9 구현·측정 워크스트림, 독립 수용 책임은 해당 구현·측정에 관여하지 않은 별도 T6.9 감사 세션이며 최종 승인 권한은 프로젝트 소유자다. 개인 이름을 만들지 않았다. 승인 원칙과 8개 이관 의무는 [authorization-received.json](../../benchmarks/t66f-b11-approval-preflight/authorization-received.json)에 기록했다.

이전 B11의 미승인/미적용 표시는 그 당시의 역사 기록으로 보존한다. 이번 소유자 승인 기록으로 덮어쓰지 않았다. 현재 상태는 ‘승인 접수, 책임 형식 충돌 해소 전 적용 보류’다. 행정 종결은 아직 발급하지 않았다.

## 2. exact redline 대조

B11 JSON의 AM01–05 모두 현재 대상 문서의 원문과 정확히 일치한다. 5개 추가문 모두 B11 보고서에 정확히 들어 있으며 B11 산출물 manifest의 12개 항목도 보존돼 있다. 원문 drift가 원인은 아니다. [redline-check.json](../../benchmarks/t66f-b11-approval-preflight/redline-check.json)에 원문·제안 해시와 검사를 기록했다.

- B11 보고서 SHA-256: `11fd8fc6d0f97dabe6570da9dce1f5190f6ca93287ca50a5e3b408fc3a871569`
- B11 제안 JSON SHA-256: `21babe57c9fb6ce617a7a81e48fb40c8e488b708f55158c2e720f5b208d409db`

## 3. 중대한 충돌과 제한 수정안

[B11 AM01](/home/hjkerman/codex/money-note/docs/t66f-b11-normative-deferral-proposal.md:135)은 ‘기명 책임자’를, [AM05](/home/hjkerman/codex/money-note/docs/t66f-b11-normative-deferral-proposal.md:262)는 ‘기명 owner’를 요구한다. [B11 §10](/home/hjkerman/codex/money-note/docs/t66f-b11-normative-deferral-proposal.md:289)도 개인 이름이 비어 있는 승인 필드를 채우도록 설명했다. 이번 승인은 역할을 분명히 지정했지만 이름을 발명하지 말라고 지시했다. 역할 배정만으로 원 기명 조건이 충족됐다고 임의 판정하지 않는다.

권고 보충 결정 ID는 `T66F-B11-TRANSFER-01-RESPONSIBILITY-SUPPLEMENT`다. 다음 세 부분만 고치는 안이며 아직 적용하지 않았다.

### GOV01 — AM01

사유: 소유자가 지정한 실재 역할에 책임을 결합하고 개인 이름을 발명하지 않는다. 분류: 책임 지정 형식의 제한 규범 수정 — 별도 명시 결정 필요.

기존 제안:

> T6.9-E 기명 책임자와 독립 증거 수용자

교체 제안:

> T6.9-E 실행 책임 역할과 독립 증거 수용 역할(실행: T6.9 구현·측정 워크스트림, 수용: 해당 구현·측정에 관여하지 않은 별도 T6.9 감사 세션, 최종 승인: 프로젝트 소유자)

### GOV02 — AM05

사유: AM01의 역할 지정과 AM05의 수집 entry 조건을 일치시킨다. 분류: 동일 책임 요건의 상위 도식 문구 정합 수정 — 별도 명시 결정 필요.

기존 제안:

> 기명 owner/독립 수용자

교체 제안:

> §34-B11 승인 기록에 명시된 실행 책임 역할/구현·측정 비참여 독립 수용 역할

### REF01 — AM04

사유: 원 규범 §38의 기존 원칙을 그대로 식별하며 새 줄번호를 추정하지 않는다. 분류: 줄 이동에 대한 편집상 참조 교정.

기존 제안:

> 796행의 원칙대로

교체 제안:

> 이 절의 구현 증명 실패 시 구현/rollout 차단 및 별도 명세 변경 감사 원칙에 따라

AM04의 ‘796행’은 앞 절에 추가문을 삽입하면 더는 해당 원칙을 가리키지 않는 편집상 문제다. REF01은 기존 §38 원칙의 의미를 바꾸지 않고 논리 절 참조로 바꾼다. AM02·AM03 및 그 밖의 모든 문장은 그대로다. 정확한 최종 추가문 5개와 전후 SHA는 [responsibility-supplement-proposal.json](../../benchmarks/t66f-b11-approval-preflight/responsibility-supplement-proposal.json)에 있다.

## 4. 그대로 유지할 의무와 차단

이관 목록은 T35-100K-NC, T35-100K-CARD, T35-100K-CASH, T35-ROWS, T35-NET, T35-GZIP, I25-E3-100K, I25-BOOKKEEPING-100K다. 이 보충안은 책임의 지정 형식과 줄 참조만 조정한다. 다섯 규모·비교 열·I25 기준·원 B03 소스 경계·독립 수용·최종 소유자 승인·실패 처분을 바꾸지 않는다.

formal F exit 재심사 및 최종 T6.9 수용 전의 증거 의무도 유지한다. 모든 이관 증거와 whole-F proof, 기기 gate 및 별도 승인 전 R1 활성화와 production 배포는 금지된다. B05/B08은 실험·미채택이다. benchmark·구현·기기 실행 허가는 추가하지 않는다.

적용하지 않았으므로 Phase B 증거 상태는 INCONCLUSIVE, formal T6.6F closure는 NOT AUTHORIZED, R1 activation은 CLOSED, production deployment는 NOT AUTHORIZED다. 이는 새 독립 F 종결 판정이 아니라 변경되지 않은 현재 상태의 확인이다.

## 5. 적용 이후 요청된 심사의 순서

보충 결정을 승인받아 구속 개정을 적용한 뒤에만 별도 독립 정합성 검토를 수행하고, 그 다음 별도 T6.6F 종결 재판정을 진행한다. 이번 적용 전 대조를 적용 후 독립 검토나 종결 재판정으로 바꾸어 부르지 않는다. 적용을 보류한 지금 두 후속 심사는 미실행이다.

## 6. 보존과 분석 검증

시작 HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이며 staged 변경은 0개다. 2,693개 index path/mode/blob/stage와 실제 index bytes SHA, 사전 파일 6,453개의 SHA/mode/길이를 기록했다. 새 파일은 이 보고서와 전용 증거 디렉터리뿐이다. 구속 문서·제품·계측·admission·release·source lock·원 B11 및 B01–B10 이력은 변경하지 않았다.

검증은 새 JSON·정확한 원문/제안 일치·단 세 부분 치환·필수 필드·기존 파일/index·동결 후보 해시 확인만 수행한다. npm build·backend/Flutter 회귀·full cold·실기기·API 요청은 실행하지 않는다. 대형 임시 산출물 정리는 해당 없음이며 삭제/회수는 0B다. 결과는 [validation-and-preservation.json](../../benchmarks/t66f-b11-approval-preflight/validation-and-preservation.json), 산출물 해시는 [evidence-manifest.json](../../benchmarks/t66f-b11-approval-preflight/evidence-manifest.json)에 보존한다.

권고하는 단일 다음 결정: 프로젝트 소유자는 위 GOV01·GOV02의 역할 기반 책임 지정과 REF01의 줄 참조 교정을 묶은 제한 보충안을 별도로 명시 승인하십시오.
