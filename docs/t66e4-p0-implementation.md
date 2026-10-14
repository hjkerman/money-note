# T6.6E4-P0 — monetary admission 선행 호환 교정

**E4-P0 COMPLETE — monetary admission 선행 교정 완료.**

Targeted 183 PASS, 전체 Flutter 1,277 PASS / 2 SKIP,
backend 1,315 tests / 1,540 subtests PASS를 실제 확인했다.
이 판정은 E4 adapter 구현 완료나 독립 E4 감사 PASS를 뜻하지 않는다.

## 1. 승인과 기준점

소유자는 E4 선행 작업으로 backend/E1 monetary admission 호환 교정만 승인했다.
shared 금융 parser의 임의 변경, frozen B/J 입력 확장, E4 adapter 통합은 승인 범위가 아니다.
시작 `HEAD = main = origin/main = actual remote main`은
`ab59d6bbc39f27c36beb059f984ef527ac7b0bef`였다. 기존 미커밋 5파일을 먼저 확인하고
hash를 기록했으며 reset/clean/stash를 하지 않았다.

규범은 T6.6C §7/22/23/25/29/31/34, domain-model의 exact won 및 Offline 원칙,
architecture의 서버 authority/클라이언트 신뢰 경계다. T6.6C를 수정하지 않는다.

## 2. 수정 전 call-site 전수 분류

`rg 'exactMoney\(|validateMoneyPayload\(' mobile --glob '*.dart'`로 직접 호출과
간접 payload admission을 찾고 caller의 실제 데이터를 확인했다. 다음 줄 번호는
수정 전 baseline 기준이며 경로는 `mobile/lib/src/` 아래다.

| 직접 `exactMoney` 호출 | 데이터 출처·역할 | P0 결정 |
|---|---|---|
| `money.dart:71,75` | 범용 payload의 setting row/value 및 named money; 읽기와 입력이 공유 | 함수와 원 validator 전체 보존 |
| `authoritative_snapshot_validation.dart:235,268,280,305,318,341,459` | 서버 raw 원금·배분·event·cash 관계의 숫자 검사 | 7곳 그대로, 금융 재계산 추가 없음 |
| `offline/offline_projection.dart:238,244` | input-only J의 display-only 예상 합계 안전 범위 | 2곳 그대로 |
| `offline/offline_projection.dart:324,329` | J payload와 표시용 기존 값의 정확한 정수 해석 | 2곳 그대로 |

직접 호출은 위 **13곳**이다. 함수 선언과 tests의 호출을 제품 call site에 세지 않았다.
Baseline 전체 `git grep`도 같은 13곳을 확인했다. 기존
`test/exact_money_domain_test.dart:16,18,20`의 3곳은 숫자 domain 회귀 oracle이며,
보존한 `docs/benchmarks/t66e4-contract/probe_test.dart:62`는 이전 input parser 차분
진단이다. 이 네 시험 call site는 authoritative publication이나 로컬 입력 저장을 하지 않는다.

| 기존 간접 entry | 분류 | P0 결정 |
|---|---|---|
| `models.dart`의 Summary, CardPaymentStatus, LedgerEntry, MonthlyPanel, PlannedChargePreview, CashFlow factories | 서버 금융 응답 및 legacy baseline typed 숫자 | 6곳 원 validator 유지 |
| `models.dart`의 AppSettings factory | 서버 settings 및 legacy baseline의 원문 문자열 | 다섯 monetary setting만 새 read 경계 |
| `authoritative_bundle.dart:39` | 완전한 서버 bundle/Snapshot | read 경계; raw-token/shape/hash/관계 검사 불변 |
| `api_client.dart:554` `_validateWriteMoney` | 온라인 입력, 기존 MW의 B+J wrapper | 일반 입력 불변; MW의 B만 read 경계, J/나머지는 원 validator |
| `api_client.dart:601` `_parseJson` | 서버 성공 응답 | nested settings/app_settings read 경계; GET/PATCH settings root는 명시 private 문맥 |
| `offline_data.dart:241` Journal factory | 영속 J 재시작 admission | 그대로 |
| `offline_data.dart:343` Baseline factory | legacy Snapshot/v4 B 재시작 읽기 | read 경계 |
| `offline_store.dart:290` append | durable 로컬 input publication | 그대로 |
| `offline_store.dart:733` atomic JSON writer | B, recovery artifact, pending/manual retry/state 공유 | B만 read 경계; artifact도 B 이외 전부 원 validator |
| `offline_projection.dart:62` | J payload estimate 전 검증 | 그대로 |

Snapshot backup repository는 `exactMoney`를 호출하지 않는다. Snapshot bytes/manifest,
normal read routing, AppState authority/coordinator와 J/replay/ack caller도 확인했지만
이들 알고리즘을 교체하지 않았다.

## 3. 기존 반례와 원인

실제 backend에서 `cash_flow_balance = "\u001c+0001000.00\u001f"`를 갖는 complete
Snapshot/bundle 및 segmented graph가 생성됐다. E1/E2/E3는 raw bytes를 저장하고 accepted
sequence=1 및 fresh recovery를 통과했다. 기존 bundle·OfflineBaseline parser만 거부했다.

원인은 Python `str.strip()`과 Dart `trim()`의 차이다. E1-A01은 segmented validator만
교정했으며 shared legacy/input helper는 별개였다. 원본 진단 12 vector 중 기존 parser와
server의 차이 7개는 경계 U+001C–001F/조합 입력 거부 5개와 edge BOM 수락 2개다.

원래 5파일과 과거 측정은 byte-identical로 보존한다. 원본 진단의 교정 후 **3 PASS /
2 FAIL**은 유효 원문을 이제 수락하여 과거의 거부 assertion이 실패한 것이다. 새 회귀는
수락 결과를 검증한다. 기존 진단을 수정하여 과거 FAIL/차단 이력을 지우지 않았다.

## 4. 채택한 grammar와 경계

원본은 `backend/isolated_sync/raw.py:80`의 `setting_money` 및 독립 E1 재감사 §5–6이다.
지원 Snapshot/B-2/E1의 setting string 문법을 채택하며 Python Decimal의 더 넓은
underscore/exponent 언어를 새로 허용하지 않는다.

- 앞·뒤에서만 Python whitespace 29개를 검증용으로 무시한다.
- 내부 문법은 ASCII `[+-]?[0-9]+(?:\.0+)?`다.
- 절댓값 `≤9007199254740991`, finite integral 의미를 유지한다.
- U+FEFF, U+200B, U+2060 등 format/BOM, 내부 whitespace, exponent/underscore,
  fractional 및 범위 밖 값을 거부한다.
- Unicode normalization, 원문 trim/replace 또는 floating-point 변환은 하지 않는다.

대상은 `scheduled_income`, `cash_flow_balance`, `card_limit`,
`base_next_month_liquidity`, `liquidity_status` 다섯 setting뿐이다. Numeric projection이나
일반 amount 필드에 호환 문자열을 새로 허용하지 않는다.

## 5. 실제 source 변경

| 파일 | 변경 |
|---|---|
| `money.dart` | 원래 파일을 그대로 prefix로 보존; 별도 exactAuthoritativeSettingMoney 및 두 read validator 추가 |
| `segmented/object.dart` | 기존 E1 whitespace/grammar 구현을 새 공통 helper로 이동·재사용; bytes/hash/error code 유지 |
| `authoritative_bundle.dart` | money 단계만 read validator로 연결 |
| `models.dart` | AppSettings 읽기만 연결; numeric factories 불변 |
| `offline/offline_data.dart` | Baseline 읽기만 연결; Journal factory 불변 |
| `api_client.dart` | settings 응답/root 및 nested authoritative settings 읽기; 기존 MW의 B만 source 구분 |
| `offline/offline_store.dart` | B 저장과 artifact의 B 부분만 구분; J/pending/state는 기존 input validator |

`_WriteMoneySource`, `_JsonMoneySource`, private `settingsResponse`는 데이터 문법 선택이다.
AppState 권한, publication permit, mode switch 또는 R1 proof가 아니다. 새 public
authorization flag/credential store/lineage token은 없다.

## 6. Frozen 입력과 publication 보존

공용 `exactMoney()`를 바꾸지 않았다. 원 `validateMoneyPayload()`의 재귀 동작도 그대로다.
실제 이전 commit과 SHA가 같은 parser archive를 별도 Dart process에서 실행하여 **4,755개 전부**를 현재
exactMoney, input payload와 Journal factory 결과에 대조한다.

Archive는 `mobile/test/fixtures/money_before_e4_p0.dart.txt`이며 실제 baseline Git object와
직접 SHA 일치를 확인했다. 시험은 pinned SHA도 검사하고 shallow checkout의 Git history를
필요로 하지 않는다. 새 parser를 베껴 기대 입력 판정을 만든 것이 아니다.

여기에는 기존 input parser의 edge BOM 수락도 포함한다. P0는 authoritative 읽기에서
BOM을 거부하지만 frozen input의 기존 수락·거부 언어를 임의로 바꾸지 않는다. 이 결과를
모든 금융 입력의 backend-compatible grammar 교정 완료라고 확대 해석하지 않는다.

B/J schema, operation ID/sequence/status, 순서, payload JSON, append framing, 중복 처리,
retry/receipt/acknowledgment 및 lineage는 변경하지 않았다. 실제 append 실패에서 J bytes
불변, 성공에서 원 input string·ID·sequence의 재개방 보존, pending marker bytes 불변을 확인한다.

Baseline writer는 validation 선택 이후 기존 temp write/flush/readback/guarded synchronous
rename/final cleanup 순서를 그대로 따른다. Guard 실패로 기존 committed B가 보존되는
시험을 추가했다. 새 durable transaction 경계나 metadata를 만들지 않았다.

Recovery artifact와 기존 MW wrapper는 B를 authoritative 읽기 문맥으로 검증하고 J와
나머지 필드는 원 input validator로 검사한다. `settings`라는 이름을 J 안에 넣어 우회하는
입력도 거부한다. MW endpoint/body/identity/password/confirmation, Apply(B,J), status 및
acknowledgment 흐름은 변경하지 않았다. R1 upload/large restore는 구현하지 않는다.

## 7. 원문·Snapshot·lineage·C1

검증 helper가 반환하는 integer는 validation/test용 해석이다. AppSettings/row/Snapshot의
원문 값을 그 integer나 stripped string으로 치환하지 않는다. 큰 정수도 BigInt로 검사한
뒤 safe range 안에서만 `.toInt()`한다.

실제 server bundle의 Snapshot·fingerprint를 그대로 통과시키고 기존 v4 serialization을
파일에 보존한다. 별도 Python JSON/hashlib로 v4 logical lineage hash를 대조한다.
Snapshot v7 hash helper와 OfflineBaseline v4 `toJson`/lineage 알고리즘은 불변이다.
`sync_root`와 서버 v7 fingerprint가 서로 다름도 확인한다.

4,755개 corpus의 server-produced C1 bytes/domain hash를 새 공통 helper를 사용하는
E1 verifier에 대조한다. Canonical encoder/hash domain·validator build·immutable BLOB·
SQLite trigger/schema·E2/E3 algorithms는 변경하지 않았다.

재생성한 corpus는 3,816 수락 / 939 거부이며 SHA-256은
`59bd99165076a10104dbb4c80f3c77a9082b0f5eaa75ba933be637b7d2a584d6`다.
기존 독립 재감사의 corpus identity와 일치한다.

## 8. 독립 증거와 신규 시험

`mobile/test/authoritative_money_compatibility_test.dart`의 **183개**는 다음을 포함한다.

- 165개 실제 server vector × 다섯 settings의 read boundary/원문 보존.
- 기존 독립 재감사에서 재생성한 4,755개 acceptance/integer/C1/hash 사례.
- 실제 이전 commit의 별도 process를 oracle로 한 4,755개 frozen input/Journal 비교.
- complete backend bundle 및 Baseline의 수락과 실제 파일 재개방, fingerprint/lineage.
- BOM·malformed·범위 밖 값 거부, numeric projection의 무관한 허용 범위 비확장.
- 실제 J append/reopen/순서/pending bytes, artifact B/J 분리 및 guard 실패 보존.
- settings GET/PATCH·baseline GET과 기존 MW wrapper의 request identity/원문 J 보존.

Corpus 수를 Flutter test 수로 더하지 않는다. Fixture의 expected acceptance/amount/hash를
수정된 Dart code만으로 생성하지 않았다. 기존 backend probe, 독립 E1 corpus, 이전
native Dart parser, 직접 persisted JSON 및 별도 Python hash가 서로 다른 oracle다.

## 9. 검증 기록

| 검증 | 현재 실행 결과 |
|---|---|
| 최종 P0 targeted | 183 PASS / 0 FAIL, portable archive 재실행 reporter 12초 |
| authoritative/server corpus | 4,755 비교 통과 |
| frozen input/pre-P0 corpus | 4,755 비교 통과 |
| 원본 historical 진단 | 3 PASS / 2 FAIL — 교정 후 수락을 거부하던 과거 assertion |
| Flutter analyze | PASS, 최종 source 기준 |
| 변경 파일 formatting | 8개 PASS |
| frontend build | PASS |
| Ruff / compileall / diff check | PASS |
| Full Flutter | 1,277 PASS / 0 FAIL / 2 SKIP, reporter 13분 34초 |
| 기존 E1/E2/E3 SIGKILL 별도 재실행 | 26 PASS / 0 FAIL / 0 SKIP: E1 7, E2 3, E3 16 |
| Backend full | 1,315 tests / 1,540 subtests PASS, warning 1, 1,808.12초 |
| Debug APK build | 최종 MW 변경 포함 PASS, 설치하지 않음 |

개발 중 잘못된 test public signature, UTF-8 header 없는 mock, package root 밖 analyze를
수정했다. 이는 product 반례로 계수하지 않는다. 마지막 MW 문맥 수정 전 full Flutter run은
중단했으며, 종료 code만으로 PASS로 계수하지 않는다. 최종 source로 전체 suite를 새로 시작했다.

## 10. 한계와 금지된 후속 작업

이 교정은 지원된 authoritative **setting** 읽기와 그 원문 B의 보존에 한정된다.
모든 arbitrary numeric string/parser, 금융 계산 엔진 또는 새로운 B/J input grammar를
구현한 것이 아니다. 원래 server scheduled_income judgment의 직접 float 파싱 관찰은
이번 범위 밖이며 backend source를 바꾸거나 이를 해결했다고 주장하지 않는다.

E4 adapter/source selection, segmented-native reader lifecycle, frozen segmented pins,
lineage handoff, general-user Offline activation은 구현하지 않았다. 기존 AppState
startup/read/write routing과 E3 final guard→COMMIT seam은 불변이다. R1 gate는 CLOSED다.
OS crash/hardware power loss 보장을 추가하지 않았다. 기존 process-crash 회귀의 이번 실행
결과는 전체 suite 및 machine-readable 별도 실행으로 확인했다. 기존 SIGKILL 시험은
26 PASS(E1 7/E2 3/E3 16)이며 새 P0 SIGKILL 경계를 발명하지 않는다.

## 11. 보존·Git·다음 단계

원본 5파일의 SHA는
`docs/benchmarks/t66e4-p0/preserved-history.sha256`에 기록했다. 전체 backend runtime,
T6.6C, SQLite production user_version 4, Snapshot v7와 OfflineBaseline v4 형식은 불변이다.
production DB/API/credentials/services에 접근하지 않았다. 배포·APK 설치·segmented
activation을 수행하지 않는다.

최종 완료 gate는 승인된 8개 결과에만 적용했다. Reported U+001C/U+001F 원문과 유효
server setting은 적절한 legacy read에서 수락되고 invalid/BOM은 거부된다. 원문·정확한
해석·frozen input/replay/ack·Snapshot/lineage·C1/hash·floating-point 비도입을 source와
회귀로 확인했다. 새 P0 correctness blocker는 확인되지 않았으며 독립 감사 판정은 별개다.

이번 요청은 P0만 별도 완료하는 범위이므로 broader E4 adapter 통합을 재개하지 않는다.
E4 완료 조건을 충족하지 않은 상태에서 repository를 clean하게 만들기 위한 commit/push도
수행하지 않는다. 기존 역사적 진단과 P0 교정·시험·보고서를 working tree에 함께 보존한다.
독립 E4 감사 PASS 또는 전체 E4 readiness는 주장하지 않는다.
