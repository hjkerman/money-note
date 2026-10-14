# T6.6E4-P0 — authoritative monetary admission 교정 증거

이 문서는 E4 adapter 구현·독립 감사 PASS가 아니라, 소유자가 별도로 승인한
**E4-P0 선행 호환 교정**만 다룬다. 시작 commit은
`ab59d6bbc39f27c36beb059f984ef527ac7b0bef`다.

## 재현과 oracle

`mobile/`에서 실행한다.

```bash
flutter test --no-pub --reporter expanded test/authoritative_money_compatibility_test.dart
```

- 기존 `t66e4-contract/probe.py`를 수정 없이 실행하여 실제 새 backend DB의 complete
  D3a generation과 Snapshot v7/bundle을 얻는다. production/listener/실제 credential은 없다.
- 기존 독립 E1 재감사의 `make_corpus.py`로 **4,755개** server-derived 사례를 다시 생성한다.
  실제 `isolated_sync.raw.setting_money`가 기대 수락 여부와 정확한 integer 해석을 결정한다.
  원 canonical bytes와 domain hash는 Python JSON/hashlib와 실제 server leaf에서 얻는다.
- `git show ab59d6b:mobile/lib/src/money.dart`와 SHA가 같은
  `mobile/test/fixtures/money_before_e4_p0.dart.txt`를 임시 파일에 그대로 넣고 별도 Dart
  process로 실행한다. 이것이 frozen 입력 acceptance의 독립 pre-P0 oracle다.
  현재 파일이 기존 원문 전체를 byte-identical prefix로 보존하는지도 검사한다.
  Archive SHA는 `9f1aef7d287f6c9c321f8d4e2fb5b9a33b4f62df9a1270820aed2a814889a02e`이며
  시험 실행에 과거 Git object나 network fetch를 요구하지 않는다.
- 실제 파일의 baseline/J/marker bytes, 새 OfflineStore handle, 별도 Python lineage hash를
  사용한다. API 반환 boolean이나 새 validator의 자체 기대값만 사용하지 않는다.

**마지막 targeted 실행: 183 PASS / 0 FAIL.** 그 안에 165개 고정 server vector,
4,755개 authoritative/E1 byte·hash 비교, 같은 4,755개 frozen 입력/J 비교가 포함된다.
Vector 수를 Flutter test 수에 더하지 않는다. 전체 회귀 결과는 최종 P0 보고서에 기록한다.

실제 전체 회귀: Flutter **1,277 PASS / 2 SKIP**, backend **1,315 tests /
1,540 subtests PASS**. 기존 E1/E2/E3 실제 SIGKILL 별도 재실행도 **26 PASS**다.
Analyze·debug APK build·frontend build·변경 파일 format·Ruff·compileall·diff check가
통과했다. APK 설치·배포는 하지 않았다.

## 원본 다섯 파일 보존

기존 `docs/t66e4-implementation.md`와 `t66e4-contract/`의 네 파일은 수정하지 않는다.
repository root에서 다음으로 확인한다.

```bash
sha256sum -c docs/benchmarks/t66e4-p0/preserved-history.sha256
```

원래 진단은 교정 전 5 PASS였으며, legacy parser가 **거부해야 한다**는 역사적 assertion을
포함한다. 교정 후 그 파일을 변경하지 않고 재실행하면 **3 PASS / 2 FAIL**이다.
실패 두 건은 `AuthoritativeBundle` 및 `OfflineBaseline`이 이제 유효 원문을 수락하기
때문이다. 이를 regression PASS로 바꾸지 않는다. 새 positive 회귀가 교정 후 수락과
원문 보존, invalid/BOM 거부를 검증한다.

## 범위

원래 `exactMoney`/`validateMoneyPayload`는 그대로다. authoritative setting 읽기만
이미 감사된 E1 문법을 공통 사용한다. Baseline·recovery artifact·기존 MW 요청에서는
**B 부분만** 호환 경계, J와 나머지 입력은 원래 validator다. API path/body, replay,
acknowledgment, resolved reconciliation ID와 lineage/hash 알고리즘은 변경하지 않는다.

E4 adapter, segmented read/source switch, 새 R1 endpoint 또는 activation gate는 구현하지
않았다. full E4 readiness·독립 감사·배포를 이 교정 결과에서 추론하지 않는다.
