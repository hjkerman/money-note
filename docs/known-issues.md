# 알려진 이슈

## Historical recurring compatibility — 독립 재감사 대기

이전 배포 writer/exporter가 적법하게 만든 source 연결에는 생성 expense의 epoch가 없을 수 있다. DB version 4의 one-time checkpoint와 표식 없는 역사적 v7의 임시 restore normalization은 유일한 source ID·source 생성 시각·payment key 및 original confirmation evidence가 증명될 때만 epoch를 채운다. Current canonical invariant와 exact-money admission은 유지하며 금융 값을 추측/보정하지 않는다. 재확정·재복원한 retired 관계에는 검증된 recovery witness가 필요할 수 있다. Source 없는 파일·부분 epoch·경쟁 후보·상충 witness는 거부한다. 새 export는 manifest-bound `recurring_ownership_version=1`이며 strict 검증을 우회하지 않는다.

운영 DB/서비스는 수정하거나 배포하지 않는다. 격리 사본 검증 결과와 별개로 독립 read-only 재감사, fresh production backup 및 fresh admission이 이후 배포의 선행 조건이다. 아래 version 3 유지 설명은 과거 closure 이력이며 현재 checkpoint version은 4다.

## Exact monetary domain closure — 독립 재감사 대기

합성 pre_batch REAL DB에서 `2^53+1` API/restore 승인의 1원 손실, 개별/최종 값은 safe하지만 Summary float 중간값이 1원 달라지는 반례, SQLite SUM의 int64 overflow를 먼저 재현했다. 제품 범위는 명시적으로 `±(2^53−1)` 정수로 정렬한다. 과거 nominal int64 지원을 end-to-end exact 또는 arbitrary precision 지원으로 주장하지 않는다.

입력/영속 admission/v7 import는 범위 밖을 거부하며 금액 설정 backfill도 float를 쓰지 않는다. Summary/카드 배분·할인 이벤트 누계는 Python 정수이고 명명된 응답 합계는 범위를 검사해 controlled 422를 반환한다. 양수 누계가 int64를 넘은 뒤 상쇄되는 safe 행들의 최종 1원도 정확하다. 클라이언트 transport/local journal의 검사와 pre-append aggregate gate를 회귀로 고정한다. 정상 1.2% 정책·소유 관계·actual 7,000원 투영·말일/조기 fixed·reconciliation은 유지한다. 실제 운영 데이터의 범위/합계 확인과 배포는 미실행이며 runbook의 별도 predeploy gate가 필요하다.

같은 numeric surface의 자체 감사에서 API 시작 후 synthetic runtime 설정을 범위 밖으로 바꾸면 `/api/settings`가 200으로 내보내던 누락도 재현했다. `scheduled_income`·`cash_flow_balance`·`card_limit` 조회는 이제 무변경 controlled 422이며, 서버/웹/모바일의 현재·legacy 금액 설정 key 검사를 같은 계약으로 맞춘다. 입력 전 거부와 응답 수신 후 ambiguity의 기존 분류는 구별한다.

## Financial canonicalization / actual projection closure — 독립 재감사 대기

`test_financial_canonicalization.py`는 시작 구현의 v7 `amount_value=-0.5` 복원 승인(95,060→100,000원)과 archive actual 7,000원/NULL 날짜의 confirmed template 5,000원 fallback을 먼저 재현했다. v7은 손실 없는 금액 검증 뒤 정규화하며 confirmed 조회는 정확히 한 source/epoch child를 날짜 유무와 관계없이 투영한다. current 지출의 NULL 날짜 금지는 유지한다.

반복 self-audit에서 cash/panel/override/payment/설정의 fractional 승인, 큰 REAL의 문자열 변환(+216원), NULL 설정의 `None` 문자열 승인, 설정 float 파싱의 소수/underflow 승인 및 정수 정밀도 손실, JSON decoder에서 이미 소수가 0/정수로 바뀌는 Snapshot/command/journal sibling도 회귀로 고정했다. raw-token preflight는 원문 검증만 하며 financial body/hash/identity를 재작성하지 않는다. v4~v6의 명시된 절삭 호환은 유지하고 v7에는 적용하지 않는다. 일반 역사적 REAL의 fingerprint도 유지한다.

actual 관계가 없거나 모호하면 confirmed read는 template 금액으로 감추지 않는다. 실제 합성 API fixture로 웹·모바일 actual 7,000원/할인 84원/실부담 6,916원을 확인한다. 운영 접근·수선·배포와 format/migration/protocol/금융 계산 변경은 없다. 최종 freeze 판정은 독립 재감사에 남긴다.

## 영속 금융 관계 closure — 독립 재감사 대기

자기검증에서 발견한 직접 sibling도 회귀로 고정한다. 일반 archive 카드 지출이 batch에 소유된 경우 원금 NULL PATCH/restore로 채무가 사라지던 90,120→100,000원 반례를 거부한다. 관계 없는 과거 nullable 원장 행의 계약은 확대하지 않는다.

`test_persistent_financial_relationships.py`에 결제 1,000원의 중복 2,000원 집계(90,120→91,120원), archive 활성 recurring의 NULL 원금(95,060→100,000원), 정상 old/current + active/archive의 restore/recovery 거부 반례를 먼저 실패 테스트로 고정했다. 원장 key와 batch item의 동일 identity·유일 소유, 결제 배분/event/cash-flow 소유, 생성 recurring의 필수 원금을 canonical 검증한다. 정상 archive 관계는 위치에 상관없이 같은 source/epoch로 읽기·복원·recovery·취소한다. 잘못된 관계는 자동 수선하지 않는다.

같은 원인의 월마감 미확인 경고도 mutable 발생월 대신 명시적 확인 epoch를 사용한다. 기존 Snapshot 성공 테스트의 목적지 setup은 정상 payment 취소로 변경했고 기존 restore/auth/audit assertion은 유지한다. 별도 테스트가 원래 고아 배분 목적지의 export/mandatory backup/restore 거부를 검증한다. 금융 계산식, 말일/조기 fixed 규칙, migration/Snapshot version, reconciliation, 클라이언트 코드는 변경하지 않는다. 운영 데이터 접근·배포는 없으며 최종 freeze 판정은 독립 재감사에 남긴다.

## 최종 recurring Snapshot ownership closure

`test_recurring_snapshot_ownership.py`는 v7 epoch 전체 NULL과 생성 expense 누락을 각각 수정 전 90,060원·100,000원으로 재현한 반례를 거부/목적지 불변 회귀로 고정한다. 정상 5,000원 원금/60원 할인은 95,060원이며 취소 후 reserve 5,000원이 복원돼 95,000원이다. 활성 확인의 source ID와 양쪽 완전한 확인 epoch가 정확히 한 생성 지출을 소유해야 한다. export와 runtime 읽기·수정·취소·재확인도 같은 계약을 검사한다. 일반 생성/PATCH가 소유 불가능한 확인 메타데이터를 만들면 commit 전에 거부한다.

v4~v6은 원래 확인 증거로 소유권을 증명할 수 있을 때만 정규화한다. 모호하거나 증명할 수 없는 legacy 활성 관계는 restore 전에 거부한다. 이후 production compatibility checkpoint는 명시적 source/key와 유일한 original evidence를 갖춘 역사적 v7에만 metadata normalization을 허용하며 증거 없는 파일을 자동 수선하지 않는다. 원본 fixture를 바꾸지 않고 rejection 테스트로 보존했다. 형식/version bump·운영 데이터 변경·배포는 없으며 최종 freeze 판정은 다음 독립 재감사 대상이다.

자기검증에서 확인한 동일 원인의 archive 취소도 고정한다. 6월 생성 지출을 5월로 수정하고 5월을 마감해 archive로 옮긴 뒤 삭제해도 활성 6월 확인을 정확한 source/epoch로 해제한다. archive의 명시적 관계도 legacy 후보에서 제외하므로 같은 내용의 수동 지출 삭제를 가짜 legacy 관계로 막지 않는다. archive 여부는 확인 identity가 아니며 이전 종료 epoch를 삭제해 새 확인을 해제하지 않는다.

## Freeze 재감사 H1/H2/M1/M2/M3 closure

`test_freeze_reaudit_closure.py`는 정책 status와 최종 HTTP JSON body 준비 실패의 rollback, source epoch 부분 누락·미마감 orphan epoch 거부, 수정된 생성 지출의 stable confirmed projection, boolean-only 할인 제외를 고정한다. `freeze_reaudit_outcome_test.dart`는 endpoint별 DELETE 거부, ambiguous 결과 보존, 같은 owner 재인증·구 retry 복구와 generation fence를 검증한다. Response bytes 준비까지 commit 전에 끝내며 이후 socket 유실은 ambiguous다. 실제 freeze 판정은 독립 재감사 대상이다.

단일-owner 제품 모델과 현재 인증 구현을 구분한다. synthetic CLI/login 검증에서 서로 다른 active principal 생성·로그인이 가능했으므로 H3를 단순 unsupported로 폐기하지 않았다. 기존 retry 한 파일에 owner ID만 결합하고 multi-user 장부·namespace는 추가하지 않는다. 운영 사용자 수는 확인하지 않았다. 구 owner 없는 retry에 유일한 durable request-marker 증거가 없으면 원문을 보존하고 재전송을 차단한다. 증명되지 않은 정상화나 운영 수선은 하지 않는다.

## Final Freeze P1–P5/L1 수정 경계

Cross-month recurring 취소의 정확한 확인 epoch, legacy explicit monetary 할인 우선순위, 금융 presenter/response model의 commit 전 검증, 모바일 committed/rebuild-pending durable 상태, revision trigger 의미 검증, malformed timezone offset 거부를 회귀 테스트로 고정한다. `test_freeze_blocker_closure.py`와 `authoritative_rebuild_pending_test.dart`가 원래 반례와 재시작·취소·재시도·Offline 차단을 보존한다. 금융 계산식·월마감·migration/Snapshot version·reconciliation protocol은 변경하지 않는다.

이미 수정돼 원래 확인 epoch를 증명할 수 없는 historical 행은 자동 수선하지 않는다. 비-idempotent ONLINE 요청의 응답 유실은 새 read만으로 commit을 추측하지 않고 금융 작업/Offline 시작을 차단한다. 동일 입력과 durable key가 있는 수동 정산만 기존 idempotent 확인 경로를 사용한다. 일반 생성 API에 새 exactly-once 보장을 선언하는 것이 아니다. 운영 수선이나 배포는 이 tranche에 포함되지 않는다.

## 예정 급여 선반영과 수동 중복 입력

현재 Summary는 전체 기간 실제 현금흐름 누계와 아직 들어오지 않은 다음 급여 `scheduled_income`을 함께 사용한다. 월마감은 사용자가 다음 카드대금에 쓸 자금을 실제로 꺼내는 사건이며, 예정액을 월마감 실행일의 실제 `급여` 현금흐름으로 즉시 확정한다. 설정값은 다시 그 이후 받을 다음 급여를 선반영한다. 이는 다음 급여를 담보로 현재 카드 사용을 감당하는 현행 운용에 맞춘 의도적인 계산이다.

화면의 `잔여 유동성`은 서버의 `current_month_spendable`이다. 내부 `remaining_liquidity`만 표시하면 이미 처리한 현금성 고정지출의 다음 발생분을 reserve하지 않아 현재 추가 사용 가능액처럼 오해할 수 있다. 새 표시값은 확인된 템플릿의 예정액만 보충 차감하며 이미 미확인 reserve에 든 금액을 이중 차감하지 않는다. 실제 은행 잔액은 별도의 `cash_flow_balance`이고, 이 값에는 아직 받지 않은 다음 급여가 들어가지 않는다. 다음 급여 선반영은 유동성 계산의 현행 과도기 모델이다.

월말 처리 후속 검증은 완료됐다(운영 배포 여부와 별개). 현재 달은 실제 달력 말일에만 마감하며, 같은 날 익월 현금 고정지출을 실제 송금일로 선처리할 수 있다. 카드 정기결제는 실제 익월 진입 전까지 닫힌다. `test_cash_fixed_early_execution.py`가 평년·윤년·30/31일 말일, 처리 월/실제 날짜 분리, reserve 교체·취소·익월 발생분, Snapshot과 DELETE/WAL 중단 복구를 고정한다. 월마감이 달력을 앞당기지는 않는다.

자동 생성된 `급여`와 같은 수입을 사용자가 수동 현금흐름으로 다시 입력하면 중복된다. 현재는 단일 사용자 운영 규칙으로 같은 급여를 수동 입력하지 않는다. 실제 급여가 예정액과 달라지는 운용이 시작되면 월마감 입력값 확인 또는 자동 생성 급여 보정 UX를 별도 설계해야 한다.

말일 월마감 급여는 닫힌 사용월에 기록되지만 활성 카드 결제 batch의 결제월은 다음 달이다. 따라서 현재 결제 압박 Judgment는 다음 달에 별도 `이달 기준 수입`이 없으면 `scheduled_income`을 fallback으로 사용한다. 미래 재무 건전화 전환 전에는 이 기준을 별도로 확정해야 한다.

다음 급여를 미리 담보로 쓰지 않게 되는 시점에는 월 주기나 누적 현금흐름을 바꾸지 않고 Summary의 `scheduled_income` 직접 선반영을 제거한다. Judgment 기준은 아직 결정하지 않았으며 [미래 재무 건전화 전환](future-financial-health-transition.md)을 따른다.

## Judgment 지속 개선

Judgment 문구는 현재 대부분 서버에서 완성된 문장으로 내려온다.

- 본체 웹앱의 예산심사위원회, 카드 한도 감시, 파산심사위원회 문구는 `backend/app/services/judgment/` 패키지에서 생성한다.
- 청구/가족카드 공유 페이지 상단 문구도 서버의 `shared_panel_subtitle()` 계열에서 생성한다.
- 프론트엔드는 대부분 서버가 준 `message`, `caption`, `subtitle`을 표시한다.
- 소비 통계 영역은 서버가 준 분류별 제목/문구에 프론트에서 계산한 금액을 붙여 보여준다.

본인 앱, 청구 공유, 가족카드 공유 문구 pool은 분리되어 있고 청구 공유 문구는 개인 카드 총액과 현금흐름 정확한 수치를 노출하지 않는다. 남은 작업은 기능 결함이 아니라 실사용 표본에 따라 분기 기준과 후보 문구를 계속 다듬는 일이다. 문구와 규칙의 단일 진실 원천은 `backend/app/services/judgment/`다.

문구 후보 파일의 관리 방식은 [Judgment 문구 관리](judgment-messages.md)를 따른다.

## 주의사항

- Snapshot restore는 장부 운용 데이터를 교체하는 위험 작업이다. 사용자 계정, 세션, 관리 로그, 공유 PIN 해시는 포함하거나 복원하지 않는다.
- Snapshot restore는 manifest 검증, 임시 DB dry-run, mandatory `pre_restore` 생성과 검증을 통과해야 실제 운영 DB를 수정한다.
- `pre_restore`는 설정 모달에서 목록 조회, 삭제, 되돌리기를 할 수 있으며, filename whitelist와 경로 검증으로 `snapshot-backups` 밖의 파일 접근을 막는다.
- Snapshot restore는 manifest 검증 후 현재 서버 스키마에 없는 컬럼을 무시한다. 새 필드가 생겨도 구버전 백업을 가능한 한 복원하기 위한 정책이며, 민감 설정이나 manifest 불일치까지 허용한다는 뜻은 아니다.
- 로그인/공유 PIN 실패 제한은 현재 단일 프로세스 메모리 기반이다. 다중 API 인스턴스로 확장하면 공용 저장소 기반 제한기로 바꿔야 한다.
- 공유 PIN은 네 자리라 강한 인증 수단이 아니다. 읽기 전용 범위와 실패 제한을 유지하고 기본 PIN `0000`은 운영 전에 바꾼다.
- 현재 export는 Snapshot v7이며 v4~v7 복원을 지원한다. v4~v6에서 v7의 nullable 관계·주기·idempotency 필드가 없는 것은 허용하지만, 과거 이벤트에 사후 idempotency를 추정하지는 않는다. v4 카드 정책 명세 v1 읽기 분기는 실제 보존 중인 지원 Snapshot 때문에 유지한다.

## 빌드 도구 경고

- Android 빌드는 Kotlin Gradle Plugin `2.2.20`, Android Gradle Plugin `8.11.1`, Gradle `8.14.3`, JDK 17 조합을 사용한다. Flutter `3.44.8`에서 Gradle 9 계열은 설정 초기화 단계의 `The settings are not yet available for build` 오류가 재현되어, 빈 Flutter 앱에서도 APK 생성이 확인된 호환 조합으로 고정했다. 기존 Kotlin `2.2.10` 지원 종료 경고는 재현되지 않는다.
- 앱 모듈은 `org.jetbrains.kotlin.android`를 직접 적용하지 않는다. 다만 일부 Flutter 플러그인이 아직 이 플러그인을 적용하므로 루트에서 버전만 선언하고 `android.builtInKotlin=false`를 유지한다. AGP 내장 Kotlin을 켜면 현재 플러그인 구성에서 빌드가 실패하므로, 플러그인 생태계가 내장 Kotlin을 지원한 뒤 다시 전환한다.
- `android.newDsl=false`도 Flutter 호환을 위해 유지한다. 이 두 호환 플래그를 제거할 때는 `flutter clean`, 정적 분석, 테스트, debug/release APK 빌드를 모두 다시 수행한다.
- 프론트엔드 운영 의존성 audit은 깨끗하다. 개발 도구 의존성에서만 낮은 등급 경고가 남는 경우에는 Vite/Vitest 상류 수정과 함께 갱신하며, 운영 번들 취약점과 구분한다.

## 구조상 남은 큰 파일과 결합 경계

아래는 줄 수 순위나 결함 목록이 아니라 현재 책임이 집중된 대표 경계다. 파일 크기와 영향 범위는 각 리팩터링 시작 커밋에서 다시 측정한다. 분리 자체보다 [T0 correctness 계약](project-state.md#t0-리팩터링-correctness-계약)과 실패·동시성 특성 테스트 유지가 우선이다.

- `backend/app/services/card_payments.py`는 결제·취소·이월 command의 금융 transaction을 여전히 소유한다. 활성 batch 조회·행 투영·통행료 그룹화는 `card_payment_reads.py`로 분리했다. `backend/app/services/offline_reconciliation.py`는 B 복원·ordered J 적용·idempotency record를 하나의 write transaction에 묶는다. 이 transaction 소유권은 추가 분리의 대상이 아니다.
- `backend/app/services/snapshot.py`는 Snapshot manifest·호환성·복구를 소유한다. `backend/app/db_migrations.py`는 versioned startup migration을 소유한다. `pre_restore`, 지원 Snapshot 버전 또는 rollback 의미를 바꾸지 않는다.
- `mobile/lib/src/app_state.dart`는 coherent refresh generation, OFFLINE lineage, 조정 finalization과 화면 상태를 조율하고 `mobile/lib/src/offline/offline_store.dart`는 baseline·journal·recovery artifact의 durable 파일 경계를 맡는다. 분리 전에 stale response, crash/restart, 손상 tail, commit-response-loss 반례를 고정한다.
- `mobile/lib/src/screens/management_screen.dart`와 `mobile/lib/src/screens/notification_import_screen.dart`에는 여러 입력·확인 흐름이 모여 있다. 화면을 나누더라도 single-flight 제출, 새 draft 보존, 할인 의도·알림 후보 identity를 서버에 전달하는 계약을 widget 테스트로 유지한다.

## 카드 정책 이력의 현재 한계

- 카드 정책과 교통카드 프로필 이력은 월 단위다. 같은 달에 설정을 바꾸면 설정 시각 이전 거래까지 그 달 전체가 새 프로필로 계산된다.
- 같은 달에 혜택이 다른 범용카드를 동시에 쓰는 경우를 식별할 거래별 카드 ID가 없다. 현재 제목·가맹점 문자열은 교통/통행 분류용이지 여러 범용카드를 구분하는 안정 키가 아니다.
- 설정 시각 이후 거래만 바꾸거나 동시 사용 카드를 구분해야 할 때는 거래에 카드/정책 ID를 고정하고 시각 단위 이력을 도입해야 한다. 실제 필요가 생기기 전까지는 월 단위 모델을 유지한다.

## 알림 수집 후속 작업

- 고속도로 통행료+ `com.ex.hipass_app`은 하이패스 이용내역 알림을 제공하지만 정확한 알림 본문 규격이 공개되어 있지 않다.
- 현재 파서는 관측한 표본의 날짜·시각, 금액, 구간과 요금 확인 불가 문구를 강한 표식 단위로 읽는다. 향후 앱 문구가 크게 바뀌면 `failed` 원문을 기준으로 파서 표식을 보강한다.
- 금액을 알 수 없는 통행료 알림은 빈 금액의 `partial` 후보로 남기므로 사용자가 직접 금액을 확인해야 한다.
- 리스너 연결 공백 중 게시된 알림은 재연결 시 Android 알림창에 아직 남아 있어야 회수할 수 있다. 카드사 알림이 이미 지워진 뒤에는 앱이 사후 복원할 원문이 없다.
- 후불 하이패스카드나 차량 하이패스 단말기를 직접 읽는 방식은 폐쇄형 통신 규격, 별도 하드웨어, 카드 보안과 차량 장치 개조 가능성 때문에 현재 구현 후보에서 제외한다.

## 해결됨

- T5 N1–N5/L1: v4~v6 정기결제 생성 지출의 source 관계는 복원 또는 기존 미결합 행 수정 전에 원래 확인 시각·변경 전 행·유일성을 확인해 영속화한다. 삭제 시 mutable 필드로 새 관계를 추측하지 않고, 현행 명시적 source를 legacy 후보에서 제외한다. 알림 도입 전/후와 Offline Phase 2의 실제 historical schema를 별도 era로 인정하되 시대별 필수 금융 컬럼 누락은 복구값을 추측하지 않고 거부한다. 자동 ID 표의 rowid alias/AUTOINCREMENT 계약과 Snapshot fixed 확인 timestamp의 실제 날짜·시각도 검증한다. 합성 historical fixture, 손상 컬럼 매트릭스, 삭제/수정·복원 lifecycle 및 강제 종료 회귀로 고정한다.
- T5 최종 독립 감사 R1–R4: `user_version=0`의 세대별 필수 테이블·PK/UNIQUE/FK 계약을 CREATE 전에 검증해 손상된 current-looking DB의 자동 빈 테이블 재생성·승격을 막는다. 과거 v4~v6 카드 정기결제 생성 지출은 관계를 유일하게 증명할 때만 원본 confirmation과 같은 transaction에서 취소하고, 모호한 경우 fail closed한다. Snapshot dry-run은 고정지출 cash-flow 링크 중복·날짜·역할 모순을 복원 전 거부한다. 실제 과거 exporter의 합성 fixture와 손상 schema/restore rollback 회귀로 고정했다.
- T5 독립 감사 F1/F2: 실제 v6 Snapshot의 연결된 현금성 고정지출은 import 경계에서 확인 월을 검증·복원하여 다음 월마감 reserve를 유지한다. 모든 지원 era에서 존재한 금융 컬럼이 빠진 unversioned DB와 version 3의 누락 컬럼은 승격/기동을 거부한다. 실제 v6 exporter fixture, v4~v7 lifecycle, 손상 DB, migration crash 회귀로 고정했다.
- T4.5 감사의 Low: 일반 모바일 Snapshot 저장 중인 `.pending` 경로를 프로세스 내 active set으로 추적하고, 다른 save의 하루 경과 cleanup에서 제외한다. 중단된 과거 `.pending` 정리와 실패한 cleanup의 정상 save 비차단은 그대로 유지한다. 두 repository 인스턴스가 겹치는 테스트로 고정했다.
- 웹 즉시결제에서 서버 응답 유실 시 공용 refresh wrapper가 오류를 삼킨 뒤 화면이 성공으로 표시하고 재시도 key를 버리는 경로를 재현·수정했다. 사용자별 브라우저 저장소에 원래 요청·draft·key를 먼저 보존하고, 응답·새 조회가 성공한 뒤에만 정리한다. 처리 중 사용자가 새로 편집한 draft는 늦게 완료된 요청이 지우지 않는다. 재시작 후 명시적 확인은 같은 key로 재시도하며, 저장소 오류 시 결제를 시작하지 않는다. 명확한 HTTP 400/422 거절은 미commit이므로 key를 해제한다.
- 최종 재감사의 수동 Claim/Family Card 등록·정산 draft·lineage·baseline/J 알림 중복·legacy 할인 fingerprint·Flutter 정산 화면 assertion 경로를 닫았다. 수동 패널 최초 할인 제외는 한 생성 transaction에 저장되고, 구버전 원장 등록 fingerprint는 저장된 금융 입력을 확인할 수 있을 때만 안전하게 승격한다. 오프라인 baseline에 이미 확정된 후보는 J나 예상값에 재반영하지 않는다. 기존 finding과 검증 반례는 테스트에 보존한다.
- 후속 final audit에서 미확정 수동 정산 key가 별개의 새 draft에 붙는 반례와 최초 HTTP 400 검증 거절 뒤 key가 남아 입력 수정이 막히는 반례를 재현했다. schema v2는 원래 입력을 보존하며 새 입력을 fail-closed로 막고, 정산 화면에서 원래 요청을 명시적으로 확인한 뒤 key를 정리한다. 최초 400/422 거절은 key를 정리하되 이전 결과가 모호한 경우는 보존한다. schema v1의 digest-only 기록은 원래 입력을 복원할 수 없으므로 정확한 재입력 또는 수동 복구가 필요하다.

- N1–N6 final freeze blocker 수정: pending J와 유실·손상된 state/B 조합은 복구 차단하고, 알림 할인 기본값은 거래 사용월·원래 카드 기준으로 가져온다. Claim/Family Card 알림의 최초 할인 입력은 생성과 원자적으로 저장하고 등록 key가 그 입력을 식별한다. 서버 단조 revision과 기준일은 A→B→A mixed refresh를 거부하며 최신 refresh 요청만 baseline을 설치한다. 오프라인 알림 후보는 durable J에서 key와 payload를 비교해 중복 투영을 막는다. 각 감사 반례는 backend/Flutter 회귀 테스트로 고정했다.
- Offline freeze audit의 L1: committed reconciliation POST 재시도에서도 baseline Snapshot manifest·compatibility와 실제 state fingerprint를 먼저 검증한다. 서버 계산 버전 1 request fingerprint가 같은 ID의 authoritative B/J에 결합되며, 다른 요청은 `409`다. 기존 fingerprint 없는 committed row는 POST replay를 거절하고 `/status` 조회로 commit 결과를 복구한다.
- 가족카드 알림의 할인 체크 기본값은 `가족 사용`/`본인 사용` 등록 대상이 아니라 알림에 매칭된 가족카드 정책을 따른다. 후보별 명시적 체크 변경은 등록 대상과 탭 전환에도 유지한다.
- 카드 즉시결제로 자동 생성된 현금흐름은 일반 현금흐름 삭제로 지울 수 없고, 일부라도 실제 결제된 원장 행도 일반 삭제를 거부한다. 결제 이벤트 취소만 현금흐름과 allocation을 함께 되돌린다.
- 고속도로 통행료+ 원문 표본을 바탕으로 별도 파서와 로컬 후보 생성 경로를 추가했다. 후보 등록 전 서버에는 아무 것도 전송하지 않는다.
- 네이버 지도 통행료 수집 실험은 가계부가 내비게이션 유지보수팀으로 전직하기 직전에 명예롭게 철수했다.
- `share_plus`의 Kotlin Gradle Plugin 경고는 `13.2.1`로 갱신한 현재 빌드에서 재현되지 않는다.
