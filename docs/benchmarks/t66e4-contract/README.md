# T6.6E4 — legacy handoff 계약 조사

## 판정과 범위

기준 commit은 `ab59d6bbc39f27c36beb059f984ef527ac7b0bef`다. **E4 구현 PASS가 아니다.**
실제 backend가 승인하고 E1/E2/E3가 accepted로 보존한 원문 monetary setting을
기존 legacy parser가 거부하는 사전 호환 제약을 확인했다. 제품 source는 변경하지 않았다.

## 재현

repository의 `mobile/`에서 실행한다.

```bash
flutter test --no-pub --reporter expanded ../docs/benchmarks/t66e4-contract/probe_test.dart
```

`probe.py`가 매번 새로운 `RetentionSandbox`를 생성한다. 실제 D3a observation,
server immutable objects, 금융 SQLite 직접 조회, 기존 `_construct`/`_prepare`의
complete Snapshot v7 및 bundle을 생성한다. 기존 D3a 회귀와 동일하게 isolated schema
version과 revision-trigger admission만 test scope에서 대체하며, money·Snapshot·projection
검증과 producer는 대체하지 않는다. 설정 파일·production DB·listener·credential을 읽지 않는다.
Fixture는 private process pipe에만 전달하며 stdout 원문을 문서나 로그에 저장하지 않는다.

`probe_test.dart`는 실제 E1 객체 저장, E2 graph acquisition, E3 full verification과
publication, 별도 SQLite connection의 committed rows/BLOB, close/reopen recovery를 확인한다.
여기서 publication은 storage-only 시험이며 AppState 설치 권한을 증명하는 시험이 아니다.
같은 backend bundle을 기존 `AuthoritativeBundle.decode` 및 `OfflineBaseline.fromJson`에
전달해 정확한 `FormatException`을 확인한다. 해당 거부가 발생해야 이 **진단** 시험은 통과한다.

## 관찰

| 원문 JSON 표현 | backend `setting_money` / `exact_money` | 기존 Dart `exactMoney` |
|---|---|---|
| `"1000"` | 수락 / 수락 | 수락 |
| `" 1000 "` | 수락 / 수락 | 수락 |
| `"\t1000\n"` | 수락 / 수락 | 수락 |
| `"\u00a01000\u00a0"` | 수락 / 수락 | 수락 |
| `"\u001c1000"` | 수락 / 수락 | 거부 |
| `"\u001d1000"` | 수락 / 수락 | 거부 |
| `"1000\u001e"` | 수락 / 수락 | 거부 |
| `"1000\u001f"` | 수락 / 수락 | 거부 |
| `"\u001c+0001000.00\u001f"` | 수락 / 수락 | 거부 |
| `"\ufeff1000"` | 거부 / 거부 | 수락 |
| `"1000\ufeff"` | 거부 / 거부 | 수락 |
| `"10\ufeff00"` | 거부 / 거부 | 거부 |

12개 vector 중 legacy Dart와 backend 판정 차이는 **7개**다. E1-A01 교정의
segmented validator를 기존 공용 legacy `money.dart`에 적용했다고 가정할 수 없다.

complete 관측에는 `cash_flow_balance = "\u001c+0001000.00\u001f"`를 사용했다.
서버 Snapshot/raw/hot에 원문이 그대로 남고 E3 accepted sequence=1, FK 오류=0,
재시작 complete recovery 성공을 관찰했다. 기존 full bundle parser와 OfflineBaseline v4
parser는 둘 다 `money must be an exact safe integer`로 거부했다. `sync_root`와 실제
서버 `state_fingerprint`는 서로 다르다.

최초 진단 준비에서는 같은 문자열을 `scheduled_income`에 사용했다. 이 경우 실제
server judgment의 `float(settings.get("scheduled_income"))`에서 `ValueError`가 발생해
관측을 만들지 못했다. 최초 run은 setUpAll 실패 1건이며 PASS로 세지 않는다.
이를 숨기거나 server projection을 mock하여 통과시키지 않았다. complete 관측을 만드는
`cash_flow_balance` 사례로 재실행했다. 최초 현상은 별도 backend 경계의 관찰이며
이번 E4 수정으로 해결됐다고 주장하지 않는다.

## 실행 결과

- 최종 재실행: **5 PASS / 0 FAIL**, reporter 기준 5초. 12개 vector의 기대 판정은 실제 backend에서 얻었다.
- 제한 Flutter 회귀: **271 PASS / 0 FAIL**.
- 제한 backend 회귀: **117 tests / 357 subtests PASS**, 37.01초.
- Flutter analyze, frontend npm build, Ruff, compileall, 새 Dart 파일 formatting,
  `git diff --check`: 실제 실행 PASS.
- E4 adapter/authority/crash 전체 시험, full Flutter/backend, APK build는 미실행이다.
  도구 부재가 아니라 사전 handoff 계약 결정이 필요하여 구현을 중단했다.

원본 전체 성공 로그는 출력하거나 커밋하지 않는다. 이번 세션의 `/tmp/money-note-e4-contract-*`
로그는 임시 증거이며 repository의 영속 실행 근거는 재현 코드와 이 요약이다.

## 필요한 결정

원문 정규화나 baseline schema 변경 없이, 기존 `money.dart.exactMoney()`의 문자열
검증을 **이미 감사된 backend/E1 monetary grammar와 정렬하는 최소 호환 교정**을
E4 선행 작업에 포함할지 소유자 결정이 필요하다. 공용 helper의 호출자는 legacy
bundle·OfflineBaseline·journal·normal input도 포함하므로 그 영향과 전체 회귀를 별도로
검증해야 한다. 현재 코드와 frozen 형식은 수정하지 않았다. R1 일반 사용자 gate는 계속 CLOSED다.
