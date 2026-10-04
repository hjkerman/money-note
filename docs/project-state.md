# 프로젝트 상태

이 문서는 새 개발자나 새 작업 세션이 Money Note의 현재 기준선과 문서 읽기 순서를 빠르게 파악하기 위한 체크포인트다. 상세 도메인 규칙, API, 스키마, 운영 절차를 대신하지 않는다.

마지막 기능 코드 대조: 2026-10-04, Owner-approved explicit canonicalization 개발 checkout (운영 배포 기준 아님)

## 현재 기준선

- Owner-approved one-time canonicalization: 소유자 R01–R11 YES 11은 private explicit manifest에만 적용한다. 별도 offline 도구가 pinned approval/backup/receipt, 전체 DB·relationship fingerprint, 기준 날짜, 한 transaction, metadata field allowlist와 정확한 금융 차이 0원을 요구한다. 보존 사본의 dry-run/폐기용 apply, strict startup 및 current v7 round-trip을 검증했다. Actual manifest는 Git 밖 비공개 `/tmp`에 있고 자동 compatibility는 변경하지 않았다. Live DB/service/master/recovery는 불변이며 별도 독립 재감사·fresh live backup/admission/운영 승인이 남는다. [운영 계약](owner-recurring-canonicalization.md).

- Compatibility witness completeness closure: same-key NULL-source witness를 conflict 집합에서 버리지 않는다. 전체 relevant grouping 뒤 partial/상충 epoch·child-kind conflict를 거부하고, 지원 v4~v6 recovery도 negative constraint로 보존한다. NULL-source는 positive ownership proof가 아니며 absent/matching epoch도 별도 완전한 canonical proof가 필요하다. Startup/restore helper와 version 4 atomic checkpoint를 유지한다. Production-derived 11개는 계속 blocked, recovery 23개는 5 허용/18 거부이며 운영 수정·배포 없이 독립 재감사 대기다.

- Historical recurring proof hardening: timestamp 일치/유일 후보는 old archive를 새 확인에 연결할 수 있어 proof에서 제외했다. 이미 보존된 완전한 canonical payment-key/source-instance/child-epoch 관계만 missing metadata를 채우며 v4~v6/역사적 v7도 같은 proof를 요구한다. Startup은 모든 이전 checkpoint 변경 전 read-only preflight를 하고 version 4에서 원자적으로 재검증·기록한다. Runtime edit는 content/time으로 source를 결합하지 않는다. 보존된 사본의 11개 관계는 현재 evidence로 증명 불가하여 거부/수동 조사 대상으로 분류했고, recovery 23개는 5 허용/18 거부였다. 허용된 사본의 금융 차이 0원, master 불변은 자동 배포 허가가 아니다. Live 운영 접근·수정·배포 없이 독립 재감사 대기다.

- Exact monetary domain closure: 단일-owner 개인 가계부와 웹 Number의 공통 계약은 `±(2^53−1)원`이다. 이전 int64 nominal 허용 범위를 명시적으로 축소하고 입력·historical/current startup admission·v7/legacy 범위·export·클라이언트/local journal을 정렬한다. Summary/배분/event 누계는 Python 정수로 계산하며 노출 합계 범위 초과는 controlled 422다. 중간값은 넓게 계산해 상쇄한다. REAL 컬럼 rebuild, DB/Snapshot version, 금융 공식, reconciliation protocol은 변경하지 않는다. 실제 운영 값/합계의 predeploy 점검·배포는 이번 작업에서 수행하지 않는다.

- Financial canonicalization/projection closure: v7 금액은 원문 JSON과 normalization 전 lossless 정수로 검사하며 fractional 값을 0/정수로 바꾸지 않는다. 이후 Exact monetary domain closure가 범위를 safe integer로 제한한다. 일반 금융 command와 Offline journal의 accepted monetary 입력도 raw-token preflight 및 기존 money validator를 통과한다. 큰 정수형 REAL의 문자열 손실, NULL 금액 설정, 설정 float 파싱을 회귀로 고정했다. v4~v6의 명시된 절삭 호환과 일반 historical REAL fingerprint는 유지한다. archive actual의 NULL 발생일은 stable source/epoch 연결을 끊지 않으며 실제 7,000원을 template 5,000원으로 대체하지 않는다. DB version 3/Snapshot v7·financial formula·reconciliation identity·클라이언트 authority는 유지한다. 독립 재감사와 배포는 별도다.

- Persistent financial relationship closure: 카드 원장 key는 하나의 batch에만 소유되고 배분은 `(event,key)` 및 실제 출금 소유권이 유일해야 한다. 명시적 recurring 생성 지출은 유효한 정수 원금을 필수로 갖는다(0원 지원, NULL 거부). old/current + active/archive도 source/epoch가 유일하면 정상이며 export/restore/mandatory recovery의 계약을 일치시켰다. 금융 읽기와 commit 전 수정도 fail closed한다. 월마감 경고는 명시적 확인 identity를 사용한다. DB version 3/Snapshot v7·금융 계산·기존 클라이언트 및 reconciliation 의미는 유지하며 독립 재감사/배포는 별도다.

- Final recurring Snapshot closure: 활성 확인은 planned source와 완전한 확인 epoch로 생성 expense 정확히 한 건을 소유해야 한다. v4~v6은 증명 가능한 legacy 정규화 뒤 검사하고 v7의 전체/부분 epoch 누락이나 생성 행 누락은 보정하지 않는다. export 및 runtime 조회·수정·취소·재확인도 같은 소유 계약을 fail closed한다. 기존 말일/조기 fixed·할인·응답 atomicity·reconciliation 의미와 DB version 3/Snapshot v7은 유지한다. 불명확한 legacy 및 생성 epoch 미보존 과거 v7 파일은 자동 복구 대상이 아니다. 독립 재감사와 운영 배포는 별도다.

- Freeze 재감사 H1/H2/M1/M2/M3 closure: 금융/정책 HTTP 응답 body는 commit 전에 준비해 handler 후 재직렬화를 우회한다. status는 같은 transaction connection을 사용한다. source epoch는 부분 상태·미마감 orphan을 거부하고 confirmed projection도 source/epoch로 실제 수정 지출을 읽는다. Claim/Family의 boolean-only false는 authoritative 제외다. 모바일 DELETE 결과는 endpoint별 무변경 계약으로 분류한다. 단일-owner 제품 모델은 유지하되 실제 CLI/auth가 복수 principal을 허용하므로 기존 manual retry 파일에 owner ID를 결합해 재인증·재시작 안전성을 검증한다. 장부 격리나 신규 namespace는 추가하지 않는다. 독립 재감사와 배포는 별도다.

- Final Freeze P1–P5/L1 closure: 정기결제는 source+불변 확인 epoch로 취소하고 공과금 default가 구 monetary override를 덮지 않는다. 금융 생성 응답 검증·직렬화는 commit 전에 끝난다. 모바일은 서버 저장과 baseline 재구성을 구분해 pending을 durable하게 보존하고 stale Offline 시작을 차단한다. 현재 schema는 revision trigger의 event/대상/효과와 상쇄 trigger를 검사하며 Snapshot은 offset hour/minute 범위도 검증한다. Freeze 판정과 운영 배포는 별도 독립 감사/허가 대상이다.

- 월마감은 현재 달의 실제 말일에만 가능하며 달력을 앞당기지 않는다. 완료 후 익월 현금성 고정지출은 실제 송금일로 집행할 수 있지만 카드 정기결제는 실제 익월 진입을 기다린다. 서버 eligibility를 양쪽 UI와 Offline baseline이 보존한다. 조기 처리분은 현금 출금과 같은 reserve를 이중 차감하지 않으며, 기존 schema version 3/Snapshot v7로 금융 주기와 실제 날짜를 함께 보존한다.

- Money Note는 한 사용자가 실제 운용하는 개인 가계부다. FastAPI와 SQLite 서버가 영속 데이터와 계산 결과를 소유한다.
- 웹 프론트엔드와 백엔드는 안정화된 기준선이다. 오류, 보안, 데이터 무결성, 운영 실패를 고치는 변경 외의 기능 확장과 대규모 재구성은 기본적으로 보류한다.
- Android 앱은 빠른 입력, 현금흐름, 당월 내역, 정산, 운영 설정을 담당하는 실사용 클라이언트다. 웹의 축소판이 아니며 같은 서버 API를 사용한다.
- 웹은 전체 장부 관리, 카드 결제 작업함, 공유 화면, 통계, 백업·복원과 관리 기능을 제공한다.
- 우리카드와 고속도로 통행료+ 알림 수집은 실사용 중이지만 외부 앱의 알림 형식과 Android 리스너 상태에 의존한다. 원문·후보는 서버 데이터가 아니라 모바일 로컬 보조자료다.
- Android Offline Mode Phase 2는 검증된 authoritative Snapshot baseline B와 durable input journal J를 보존한다. 서버 복구 시 사용자가 Mobile Wins 또는 Server Wins를 명시적으로 확인하며, 양쪽 recovery artifact가 검증된 뒤에만 atomic `Apply(B, J)` 또는 fresh server rebuild를 실행한다.
- Offline baseline은 Snapshot fingerprint·단조 증가 서버 revision·서버 기준일을 함께 확인한 coherent refresh에서만 설치하고 offline epoch 동안 고정한다. 겹친 ONLINE refresh는 최신 요청만 설치하며 orphan B/J metadata는 fail closed한다. journal append는 byte-framed serial critical section이며 같은 알림 후보의 중복 append를 방지한다. committed reconciliation을 포함한 schema v4 baseline은 같은 J를 다시 projection하지 않는다.
- Mobile Wins reconciliation ID는 서버가 검증된 B와 ordered authoritative J에서 계산한 버전드 request fingerprint에 결합한다. committed 재시도도 baseline을 먼저 검증하고, legacy fingerprint 없는 row는 POST 재실행 없이 status 조회로 복구한다.
- 우리카드 알림의 할인 체크 기본값은 등록 대상과 독립적으로 원래 카드의 거래 사용월 정책을 따르며, 공과금 키워드가 있는 거래의 최초 선택만 할인 제외로 둔다. 명시적 선택이 우선한다. Claim/Family Card 알림의 최초 할인 제외 입력은 패널 생성과 한 transaction에서 처리한다. 서버 할인 계산의 소유권은 그대로 유지된다.
- 수동 Claim/Family Card의 최초 할인 의도도 생성 요청과 같은 transaction에 담는다. 정산 폼은 중복 제출과 늦은 응답으로 인한 새 draft 삭제를 막는다. 미확정 등록은 원래 authoritative 입력과 등록 key를 함께 보존해 명시적으로 확인하며, 다른 draft가 이전 key를 재사용하지 못한다. 오프라인 알림 후보는 pending J뿐 아니라 B의 확정 등록 identity를 검사한다. 재시작 시 reconciliation metadata는 mode/phase/commit/artifact 조합과 recovery bundle의 J까지 검증한다.
- 웹 즉시결제는 사용자별 로컬 재시도 기록에 원래 요청·입력 draft·idempotency key를 서버 요청 전에 저장한다. HTTP 응답 또는 후속 조회가 실패하면 성공으로 표시하거나 입력을 지우지 않고, 재시작 후 명시적 확인에서 같은 요청·key를 사용한다. 성공해도 사용자가 처리 중 새로 편집한 draft는 지우지 않는다. 서버가 명확히 400/422로 거절한 경우만 해당 key를 정리한다.
- T5의 기존 DB `user_version`은 구조를 식별했으며 현재 version 4는 명시적인 one-time recurring identity checkpoint도 기록한다. 구버전 Snapshot은 이미 현재 구조인 DB에 데이터를 다시 넣을 수 있으므로, v6의 확인된 현금성 고정지출 확인 월은 Snapshot import에서 유효한 처리일로 복원한다. 손상된 unversioned 금융 핵심 컬럼은 추측해 보강하거나 version 3으로 승인하지 않는다.
- 현재-unversioned admission은 알림 전/후를 포함한 시대별 필수 테이블·authoritative 컬럼과 PK/UNIQUE/FK·자동 ID rowid 의미를 migration의 `CREATE IF NOT EXISTS` 전에 검증한다. v4~v6 Snapshot 정기결제 원본 관계는 복원 또는 기존 행 수정 전에 원래 확인 증거로 유일하게 식별될 때 영속화하며, 취소 시 mutable 필드로 새 관계를 만들지 않는다. Snapshot fixed 확인 링크의 소유·날짜·timestamp 모순은 dry-run에서 거부한다.
- 현재 유지보수의 중심은 버그와 무결성, 보안·배포, 카드 정책 이력, Judgment 문구, Android 알림 형식 변화 대응과 문서 일치다.

## 깨뜨리면 안 되는 경계

- SQLite DB가 영속 데이터의 원본이고, 서버 API의 계산 결과가 런타임 단일 진실 원천이다.
- 할인 가능 여부, 할인액, 실결제액, 합계, 유동성, 기준 월을 웹이나 모바일에서 authoritative 값으로 다시 계산하지 않는다. Offline Mode의 허용 operation delta는 명시적인 `오프라인 예상값`으로만 투영하며 journal이나 서버 입력에 넣지 않는다.
- 카드 종류 분류와 할인 정책, 수동 override, 실결제액 계산의 소유자는 `backend/app/services/card_charge/`다.
- 모바일 로컬 알림 원문·후보·처리 이력은 관측과 입력 보조용이다. 사용자가 등록을 확정해 기존 API로 전송하기 전에는 장부 사실이 아니다.
- Snapshot은 서버 장부와 비민감 운영 설정의 이동·복구 형식이다. 모바일 로컬 후보, 사용자 계정, 인증 세션, 공유 세션, 감사 로그와 비밀번호·해시는 포함하지 않는다.
- Offline baseline과 journal은 Snapshot과 분리된 모바일 임시 작업 상태다. atomic commit 확인, fresh server sync, mobile rebuild와 fresh baseline 성공 전에는 삭제하지 않는다. retained recovery artifact와 durable server idempotency history는 성공 cleanup 대상이 아니다.
- `claim`과 `family_card`는 소비 원장이 아니라 회수 예정 큐다. 소비 통계와 유동성에 직접 넣지 않으며, 월 경계와 무관하게 처리 또는 삭제 전까지 남는다.
- `claim`과 `family_card`는 정상 운영 중인 비핵심 기능이며 제거 자체는 확정되어 있다. 특정 날짜가 아니라 사용자가 생활비와 예외적인 큰 지출까지 가족 지원 없이 감당할 수 있는 현실적 경제적 독립 상태가 제거 조건이다.
- 월마감은 자동 실행하지 않는다. 사용자의 명시적 실행이 결제 batch와 원장 이동의 기준이다.
- 화면의 `잔여 유동성`은 서버 Summary의 `current_month_spendable`을 표시한다. 기존 `remaining_liquidity`는 다음 급여 선반영과 미확인 고정지출 reserve까지만 담는 계산 단계이며, 새 표시값은 확인된 현금성 고정지출의 다음 발생분 예정액을 추가로 reserve한다. 두 클라이언트는 이를 재계산하지 않는다.
- 유동성 도메인과 일반 런타임 API·DB의 표준 이름은 `scheduled_income`, `cash_flow_balance`, `remaining_liquidity`다. 과거 key는 DB/Snapshot migration과 그 전용 테스트에만 남긴다.

상세 의미는 [도메인 모델](domain-model.md), 계산·모듈 경계는 [아키텍처](architecture.md)를 따른다.

## T0 리팩터링 correctness 계약

다음은 새 설계 제안이 아니라 현재 구현의 회귀 방지 경계다. 파일을 분리하거나 책임을 옮기기 전에 관련 실패·재시작·동시성 테스트로 같은 의미를 고정한다. 금융 의미는 [도메인 모델](domain-model.md), 상태와 저장 세부사항은 [Offline Mode](offline-mode.md), 복원 안전성은 [실행 방법](runbook.md)을 따른다.

- **서버 권위:** DB와 서버 API의 할인·실결제액·Summary·기준일 계산이 authoritative하다. 모바일 Offline projection과 서버가 제공한 표시용 정책 descriptor는 화면 예상값일 뿐 journal, reconciliation payload 또는 서버 금융 원본이 아니다.
- **coherent baseline:** ONLINE refresh의 화면 상태와 authoritative Snapshot은 같은 server fingerprint·단조 revision·기준일 generation이어야 한다. 오래된 비동기 응답과 불완전한 refresh는 valid baseline을 교체하지 못하며, OFFLINE epoch의 B는 끝까지 고정된다.
- **journal과 lineage:** authoritative user input만 stable operation ID와 순서로 durable append한다. 유효한 EOF record와 앞선 정상 기록을 보존하고 append 전체를 직렬화한다. 손상·누락된 B/J/state나 모순된 reconciliation metadata는 ONLINE으로 fail-open하지 않고 금융 mutation·cleanup을 차단한다.
- **조정과 복구:** 양쪽 recovery point의 생성·검증 및 명시적 선택·확인 없이는 destructive reconciliation을 시작하지 않는다. Mobile Wins는 서버의 단일 transaction에서 `Apply(B, J)`를 적용하고 실패 시 S로 rollback하며, Server Wins는 J를 replay하지 않는다.
- **재시도와 응답 유실:** stable reconciliation ID는 검증된 B와 ordered J의 logical fingerprint에 결합되고 operation ID 중복은 거부한다. commit 뒤 HTTP 응답을 잃으면 같은 ID의 status/result로 결과를 확인하고 재적용하지 않는다. fresh authoritative rebuild·새 baseline 설치 전에는 committed journal과 복구 metadata를 버리거나 정상 ONLINE으로 가장하지 않는다.
- **금융 입력의 원자성:** 카드 사용 생성과 최초 사용자 할인/실결제 override, 정산 패널 생성과 최초 할인 의도, 정기지출 확인, 카드 결제·월마감 상태 전이는 각 서버 business transaction 경계를 유지한다. 사용자의 한 입력만 부분 commit되거나 같은 요청이 중복 금융 기록을 만들면 안 된다.
- **비동기 draft:** 버튼·키보드 등 동일 제출은 single-flight이며, 실패한 draft와 이전 요청 중 사용자가 새로 쓴 draft를 보존한다. 성공한 바로 그 입력과 현재 draft가 같을 때만 지운다. 응답 유실의 retry identity와 원래 authoritative 입력은 결과 확인 전까지 유지한다.
- **Snapshot:** manifest·카드 정책 호환성·지원 schema 검증과 임시 DB dry-run, 위험 작업 직전 `pre_restore` 생성·검증, transaction rollback 및 복구 artifact 보존을 약화하지 않는다. 모바일 recovery bundle은 서버 Snapshot이나 display projection을 임의의 restore 입력으로 바꾸지 않는다.

## 주요 설계 결정

- **FastAPI + SQLite 유지**: 단일 사용자와 현재 데이터 규모에는 별도 DB 서버보다 배포, 트랜잭션, 파일 백업과 복구가 단순한 구성이 더 적합하다.
- **서버 계산 집중**: 웹과 Android에서 같은 금융 규칙을 따르게 하고, 카드 교체나 정책 변경을 한 곳에서 처리하기 위해 도메인 계산을 백엔드에 둔다.
- **별도 모바일 정보구조**: 모바일은 5~10초 입력과 현장 확인에 집중한다. 전체 운영 기능을 웹 화면 그대로 옮기지 않는다.
- **카드 정책 이력 보존**: 카드별 계산식은 효력 시작월을 가진 binding으로 추가한다. 교통카드의 `자동 할인 없음`/`본인카드와 동일` 선택도 월별 설정 이력으로 보존한다. 과거 binding이나 설정월을 덮어쓰지 않아 Snapshot 복원과 과거 계산의 의미를 보호한다.
- **보수적인 파일 분리**: 상태 전이와 트랜잭션을 공유하는 큰 모듈은 파일 크기만 줄이기 위해 쪼개지 않는다. 먼저 특성 테스트와 명확한 경계가 있어야 한다.
- **검증 가능한 Snapshot**: canonical JSON 기반 manifest와 SHA-256을 사용하고, 실제 restore 전 dry-run과 mandatory `pre_restore` 생성을 거친다. export 전체는 단일 read transaction이며 위험 작업은 write transaction 안에서 pre_restore와 변경을 연속 수행한다. 구버전 Snapshot은 호환 기본값이 있는 신규 필드의 누락을 허용하고 현재 스키마에 없는 필드는 무시하되, manifest나 필수 테이블·컬럼 오류는 허용하지 않는다.
- **정기지출 실제액 확정**: 현금성 고정지출과 카드 정기결제의 등록 금액은 다음 주기에도 유지되는 reserve/예정 원금이다. 확인 시 이번 주기의 실제 출금액 또는 실제 원금을 따로 입력한다. 현금 지출은 실제액의 음수 현금흐름으로, 카드 지출은 실제 원금에 서버 할인 정책을 적용한 원장 expense로 전환한다. template 자체는 바꾸지 않는다.
- **미확인 정기지출 월마감 경고**: 월마감 상태와 transaction 안에서 대상 주기의 미확인 현금성 고정지출·카드 정기결제를 검사한다. 기본 월마감은 중단하고, Web/Mobile에서 항목을 확인한 뒤 명시적으로 override한 경우만 진행한다.
- **월마감·즉시결제 재시도 안전성**: Web과 Mobile은 월마감 대상 월을 명시하고, 즉시결제 기능을 가진 Web은 결제 idempotency key를 보낸다. 서버는 SQLite write transaction 안에서 최신 상태를 다시 확인하여 archive·급여·batch 중복과 동시 초과결제를 막는다.
- **정기결제 원본 관계**: 확인으로 생성된 원장 지출은 planned 템플릿 id를 명시적으로 참조한다. 동일 제목·금액의 수동 지출을 승인 내역으로 오인하지 않는다.
- **월마감 급여 확정**: 월마감 성공 시 기본 예정 수입을 월마감 실행일의 실제 `급여` 현금흐름으로 기록해 Active 계좌 잔액에 즉시 반영한다. 현행 Summary는 그 누계와 별도로 그 이후 받을 다음 급여 예정액을 한 번 선반영한다.
- **Active 계좌 잔액**: `cash_flow_balance`는 수동 보정값과 서버 기준일까지 실제 발생한 현금흐름 누계다. 월마감 급여는 실행일에 즉시 포함하며, 사용자가 입력한 미래 날짜 현금흐름은 발생일 전 잔액에 포함하지 않는다.
- **AI 회계감사의 현행 모델 의존성**: 모바일 감사 Markdown은 서버 Summary의 `scheduled_income`, `cash_flow_balance`, 화면용 `current_month_spendable`을 현재 재무 상태로 제공하고 다음 급여 선반영을 과도기 운용 모델로 설명한다. 재무 건전화 전환 시 [미래 재무 건전화 전환](future-financial-health-transition.md)의 절차에 따라 같이 갱신한다.
- **카드 의무의 단일 반영**: 카드 사용은 월마감 전 `card_total`, 월마감 후 활성 결제 batch의 이월 제외 미결제액으로 잔여 유동성에 이어서 반영된다. 즉시결제는 현금과 미결제액을 함께 줄이고, 결제일 후 수동 잔액 보정 완료는 이미 실제 잔액에 반영된 batch 채무의 Summary 재차감을 멈춘다.
- **결제 이력 보호**: 즉시결제가 만든 현금흐름은 일반 현금흐름 삭제로 지울 수 없고 결제 이벤트 취소만 허용한다. 일부라도 즉시결제된 원장 행도 일반 원장 삭제를 거부해 실제 은행 출금 이력을 사후 재작성하지 않는다.
- **Summary 읽기 일관성**: Summary의 예정 수입, 실제 잔액, 카드 의무, 고정 의무, 동결과 잔여 유동성은 하나의 SQLite read transaction에서 계산한다.
- **빈 예산 주기 월마감**: 원장 지출이 0건이어도 `last_closed_month`에서 이어지는 다음 예산 주기를 정상 마감한다. 급여, 반복 템플릿 reset, 결제 batch와 idempotency 의미는 지출이 있는 달과 같다.
- **제거가 확정된 정산 기능**: Claim과 Family Card는 제거 시점만 미정이다. 날짜 경과가 아니라 현실적 경제적 독립 여부로 결정하며, 현재 경계와 전환 순서는 각각 [청구 기능 제거 가이드](claim-removal.md)와 [가족카드 제거 가이드](family-card-removal.md)에 고정한다.

카드 교체 절차는 [카드 정책 변경](card-policy-change.md), 가족카드 경계는 [가족카드 제거](family-card-removal.md), 백업 안전성은 [실행 방법](runbook.md)과 [보안 운영](security.md)에 상세히 적혀 있다.
예산 주기는 현재도 매월 1일~말일이다. 미래 재무 건전화 시에는 실제 급여 현금흐름을 유지하면서 다음 급여 예정액의 직접 선반영만 제거한다. 결제 압박 Judgment 기준은 아직 보류하며 [미래 재무 건전화 전환](future-financial-health-transition.md)에 둔다.

## 의도적으로 하지 않는 것

- 클라이언트에 서버 금융 계산식을 복제하지 않는다.
- 자동 월마감이나 날짜만 보고 결제 batch를 임의 생성하지 않는다.
- `family_card`를 핵심 원장 모델에 흡수하거나 범용 정산 프레임워크로 승격하지 않는다.
- 현재 단일 사용자 규모에 맞지 않는 다중 인스턴스, 외부 DB, 분산 세션 저장소를 선제 도입하지 않는다.
- 관측되지 않은 외부 앱 알림 형식을 추측해 자동 등록하지 않는다.
- 동작 근거와 테스트 없이 큰 파일을 일괄 분할하거나 공개 API·DB 의미를 바꾸지 않는다.

## 기술 부채와 제한

- `backend/app/services/card_payments.py`는 결제·이월·취소의 transaction command를 유지하고, read model은 `card_payment_reads.py`가 소유한다. `mobile/lib/src/app_state.dart`는 영역별 새로고침과 Offline lineage 조율을 계속 담당한다. 추가 분리는 선행 특성 테스트가 필요하다.
- DB startup은 [versioned migration](database-migrations.md)의 `PRAGMA user_version` 계약을 따르며, 구 DB/Snapshot 지원 판정은 [호환성 inventory](compatibility-inventory.md)에 둔다.
- 로그인·공유 PIN 실패 제한은 단일 API 프로세스 메모리에 있다. 현재 배포에는 맞지만 다중 인스턴스에는 적합하지 않다.
- Android 알림 수집은 리스너가 끊긴 동안 알림창에서 사라진 원문을 복구할 수 없고, 외부 앱 문구 변경에 파서 보강이 필요할 수 있다.
- 카드 정책 이력은 현재 월 단위라 같은 달 안의 설정 시각 전후 거래나 서로 다른 범용카드 동시 사용을 구분하지 못한다.
- 자세한 현재 이슈와 이미 해결된 항목은 [알려진 이슈](known-issues.md)에만 유지한다.

## 운영 및 배포

- 서버 개발 Git working copy는 `/home/hjkerman/codex/money-note`다. `/opt/money-note`는 별도 production deployment 영역이며, 남아 있는 Git 메타데이터로 개발하거나 pull/build하지 않는다.
- API는 Docker Compose로 `127.0.0.1:18080`에만 바인딩하고, Apache가 HTTPS 정적 웹과 `/api`, `/share` reverse proxy를 담당한다.
- 서버 배포 진입점은 개발 checkout의 `scripts/deploy-server.sh`다. 기본 dry-run, `--stage-only`는 격리 빌드, 명시적 `--apply`만 production을 변경한다. push 없이 로컬의 깨끗한 커밋을 배포하며 운영 설정과 DB는 제자리에 보존한다.
- Android release 진입점은 `scripts/release-mobile.sh`다. 같은 local 모드로 검증·서명 빌드 후 `--apply`에서만 운영 APK를 원자적으로 교체한다. 도구 설치와 배포 사본 보관 정책은 runbook에만 유지한다.
- 운영 DB, Snapshot 파일, `.env`, `.env.deploy`, 서명키와 SSH 키는 Git에 넣지 않는다.
- 첫 배포, 장애 복구, Snapshot restore, 수동 검증 명령은 [실행 방법](runbook.md)이 운영 절차의 단일 기준이다.

## 기억이 없는 상태에서 재개하기

1. [Agent 작업 규칙](../AGENTS.md)을 읽는다.
2. 이 문서에서 현재 기준선과 금지 경계를 확인한다.
3. [도메인 모델](domain-model.md)과 [알려진 이슈](known-issues.md)를 읽는다.
4. 작업 영역에 따라 [아키텍처](architecture.md), [실행 방법](runbook.md), [보안 운영](security.md), [API 명세](api.md), [DB 명세](database.md)를 읽는다.
5. 관련 코드와 테스트를 읽고 문서가 아닌 현재 구현도 대조한다.
6. 필요할 때만 최근 Git 이력으로 변경 배경을 보완한다. Git 이력 자체를 현재 규칙의 원본으로 삼지 않는다.

## 문서별 책임

| 책임 | 문서 |
| --- | --- |
| 현재 프로젝트 체크포인트와 읽기 지도 | `docs/project-state.md` |
| 도메인 의미와 계산 원칙 | `docs/domain-model.md` |
| 런타임 구성, 모듈 소유권과 데이터 흐름 | `docs/architecture.md` |
| 배포, 운영, 백업·복원과 장애 대응 | `docs/runbook.md` |
| 인증, 비밀정보, 공개 경계와 위협 대응 | `docs/security.md` |
| HTTP 계약 | `docs/api.md` |
| SQLite 스키마와 컬럼 의미 | `docs/database.md` |
| 향후 결제 압박 기준과 재무 건전화 전환 조건 | `docs/future-financial-health-transition.md` |
| 손검증과 회귀 시나리오 | `docs/test-plan.md` |
| 현재 기술 부채와 외부 제약 | `docs/known-issues.md` |
| 모바일 Offline Mode 상태 머신, 로컬 저장과 reconciliation 경계 | `docs/offline-mode.md` |
| Android 화면·UX 기준 | `docs/mobile-design.md` |
| 카드 교체 시 정책 이력 변경 절차 | `docs/card-policy-change.md` |
| 가족카드 제거 경계와 절차 | `docs/family-card-removal.md` |
| Agent가 지켜야 할 작업·검증·배포 규칙 | `AGENTS.md` |
