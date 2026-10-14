# T6.6E4-P0 독립 targeted 감사 재현

대상은 `ab59d6bbc39f27c36beb059f984ef527ac7b0bef` 위에 있는 **미커밋 P0 교정**이다.
감사 시작 시 tracked 7개와 untracked 11개를 기록했다. 전체 경로·크기·SHA-256은
`worktree-targets.json`, 보호된 원본 source 29개의 hash는 `protected-source.json`에 있다.
기존 교정·진단 파일을 변경하거나 stage/commit/push하지 않는다.

판정과 한계는 [감사 보고서](../../t66e4-p0-independent-audit.md)에 기록한다.
이 도구는 E4 adapter/R1/배포를 구현하거나 승인하지 않는다.

## 재현

현재 호스트의 `.venv`와 Flutter/Dart SDK, 준비된 mobile package config를 사용한다.
SDK는 `/home/hjkerman/.flutter/bin`, 실행 당시 Flutter 3.47.4/Dart 3.13.3이다.
다른 환경에서는 도구의 SDK 경로를 해당 환경에 맞게 지정해야 한다.
아래 경로는 기존 데이터가 없는 **새 임시 경로**로 선택한다. pytest `--basetemp`는
지정 경로를 정리하므로 기존 작업이나 사용자 데이터 경로를 지정하면 안 된다.

```bash
E4_P0_AUDIT_OUTPUT=/tmp/mn-e4-p0-rerun-results \
  .venv/bin/python -m pytest -q docs/benchmarks/t66e4-p0-audit/test_audit.py \
  --basetemp=/tmp/mn-e4-p0-rerun --junitxml=/tmp/mn-e4-p0-rerun.xml

cd mobile
E4_P0_INTEGRATION_OUTPUT=/tmp/mn-e4-p0-integration-rerun.json \
  /home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  ../docs/benchmarks/t66e4-p0-audit/integration_test.dart \
  > /tmp/mn-e4-p0-integration-rerun.log 2>&1
```

첫 명령은 Python 5개, 두 번째는 Flutter 18개다. 총 **23개 새 독립 case**다.
24,836개 differential vector를 Flutter/Python test 개수에 더하지 않는다.
성공 로그 전체를 출력하지 않는다. 합성 DB·fixture·credential을 커밋하지 않는다.
새 backend fixture는 보존된 `docs/benchmarks/t66e4-contract/probe.py`의 private pipe에서 얻는다.
이 probe는 새 RetentionSandbox만 사용하며 설정 DB·production listener·`.env`를 읽지 않는다.
isolated schema/version gate만 test scope에서 대체하고 money/Snapshot/producer 검사는 실제 코드다.

## 독립 oracle

- `make_corpus.py`: 수정된 Dart validator를 기대값 생성에 사용하지 않는다. 실제 backend
  `isolated_sync.raw.setting_money`로 수락·정수 값을 판정한다. 유효 leaf는 서버 `Row.make/leaf`,
  C1와 domain SHA는 별도 Python JSON/hashlib로 대조한다.
- `differential.dart`: 실제 authoritative reader·AppSettings·nested setting payload·E1
  byte verifier를 호출한다. frozen `exactMoney`/payload/Journal 및 non-setting money도 대조한다.
- `test_audit.py`: Git baseline의 **원본 money.dart**를 별도 Dart process에서 실행해 frozen
  input 기대값을 얻는다. 원래 다섯 파일 hash와 frozen parser prefix도 확인한다.
- `legacy_read.dart`: 동일한 실제 synthetic server wire를 교정 전 source copy와 현재 source에
  각각 전달한다. 임시 copy만 `git show`로 채우며 shared working tree를 checkout/restore하지 않는다.
- `integration_test.dart`: 실제 OfflineStore의 B/J 파일, reopen, guarded rename 실패,
  ordered replay request, pending token acknowledgment, recovery artifact, nested J 거부를 검사한다.
- `inspect_state.py`: auditor-owned marker가 있는 임시 workspace의 실제 파일을 fresh Python
  process에서 읽는다. Snapshot v7 flat fingerprint와 전체 v4 logical lineage를 독립 재계산한다.

새 corpus는 seed **2026101404**, Unicode **15.0.0**, 문자 집합 **358개**다. ASCII/C1 controls,
현재 Python의 전체 Unicode `isspace()` 29개, 전체 `Cf` 170개 및 추가 Unicode 문자를 포함한다.
문자 위치·문법·범위·29×29 whitespace 조합·BOM/format 혼합·8,192자리 문자열·고정 seed의
malformed 문자열을 사용하고 동일 문자열은 deduplicate한다.

최종 **24,836개: backend 수락 4,903 / 거부 19,933**, 모든 mismatch 0이다.
교정 전 frozen input 수락은 3,866개다. 두 계약은 의도적으로 다르다. 교집합 3,748,
authoritative-only 1,155, input-only 118, 양쪽 거부 19,815이며 input-only의 기존 BOM 정책을
새 authoritative 계약으로 변경하지 않았다. finite corpus만으로 전체 언어 동등성을 주장하지
않으며 보고서의 whitespace·ASCII grammar·safe-integer source 논증을 함께 사용한다.

## 원래 진단 보존

다음 명령은 원래 다섯 파일 중 시험 파일을 **수정 없이** 실행한다.

```bash
cd mobile
flutter test --no-pub --machine ../docs/benchmarks/t66e4-contract/probe_test.dart
```

현재 결과는 **3 PASS / 2 FAIL**이다. 두 FAIL은 유효 원문을 bundle/Baseline이 계속
거부해야 한다는 역사적 assertion이다. 이를 PASS로 바꾸거나 원래 파일을 수정하지 않았다.
새 별도 positive 재현은 교정 전 `bundle=false, baseline=false`, 현재 `true,true`,
양쪽 frozen input `false`, raw codepoints 불변을 확인했다.

## 영속 근거와 제한

`results.json`은 실행·회귀·원래 diagnostic 결과를 구분한다. `differential.json`은 새 corpus의
실제 수락/거부/mismatch, `original-replay.json`은 전후 원래 반례,
`persisted-state.json`은 fresh process의 파일 hash·fingerprint·lineage 증거다.
원시 로그/DB는 `/tmp/mn-e4-p0-audit`에 두었고 영구 가용성을 전제하지 않는다.
기존 구현 측 4,755 corpus도 별도 재생성해 개수·hash를 확인하고, 전체 Flutter에서
183개 P0 tests와 기존 SIGKILL 26개가 실제 통과했음을 machine event로 확인했다.

이번 감사는 기존 process-crash 회귀를 실행했으며 OS crash/power loss를 새로 입증하지 않는다.
E4 cross-store adapter, reader/pin lifecycle, 일반 사용자 Offline activation, R1 large restore,
production rollout은 검증·구현하지 않았다. working tree는 의도적으로 미커밋 상태로 보존한다.
