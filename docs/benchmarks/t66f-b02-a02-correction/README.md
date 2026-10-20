# B02/A01/A02 최종 구현 측 검증 자료

최종 판정과 한계는 [교정 보고서](../../t66f-b02-a02-targeted-correction.md)를 따른다.
이 자료는 독립 감사 PASS가 아니다. R1 및 기본 segmented 활성화는 포함하지 않는다.

## 재현 경계

개발 checkout의 `.venv`, 준비된 mobile package config와 host Flutter SDK를 사용한다.
임시 DB·TLS 인증서는 각 runner가 새 `/tmp/mn-a02-*` 아래 생성한다. production DB·서비스·
credentials는 입력하지 않는다. APK 빌드만 허용하며 설치하지 않는다.

```sh
.venv/bin/python -m pytest -q backend/tests/test_isolated_sync_c1_single_encode.py
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine --concurrency=2 \
  test/segmented_cold_continuation_test.dart \
  test/segmented_cold_continuation_crash_test.dart \
  test/segmented_cold_packet_test.dart \
  test/segmented_adapter_isolation_test.dart \
  test/segmented_response_cleanup_test.dart
```

`codec_benchmark.py`는 같은 ASGI/auth/SQLite 응답에서 보존 codec과 현재 codec을 대조한다.
`renewal_benchmark.dart`는 backend-produced fixture와 controlled 410으로 전후 DFS 작업을
비교한다. 둘 다 실제 대형 cold 성공의 대체물이 아니다. `before_fetch.dart`는 교정 전 알고리즘의
TEST-ONLY 사본이며 runtime fallback/두 번째 제품 verifier가 아니다. 그 원 스타일은 보존한다.

## 실제 대형 실행

`run_http.py 1000`, `run_http.py 50000`, `run_http.py 100000` 순서로 실행했다.
같은 이름의 campaign pointer가 있으면 무근거 재실행을 거부한다. 재검증자는 기존 pointer나
실패 기록을 지우지 말고, 새 evidence 경로와 disposable output을 명시하여 `full_http_test.dart`를
실행해야 한다. 50k가 통과하기 전 100k를 시작하지 않는다.

외부 guard는 7,200초/8GiB process-tree RSS/최소 free disk 2GiB다. protocol lease 900초와
관측 세 번은 별개이며 늘리지 않는다. `full_http_test.dart`는 기존 실제 server/typed protocol을
사용하고 E3의 원 AppState ticket으로 게시한다. E4 모든 table의 canonical value digest는
backend oracle와 비교한다. oracle가 전달한 객체를 E1에 직접 복사하지 않는다.

`active-http-N.json`/`http-N-execution.json`은 실행 provenance다. `http-N-*.gz`는 actual
wire trace, manifests, generated graph identity, canonical record digest, independent SQLite
snapshot, fresh-process 결과를 보존한다. raw DB·TLS private key·APK는 Git에 넣지 않는다.
`post-reads`는 accepted logical read의 bounded work 계수이며 native Frozen-B 설치나 R1 증명이 아니다.

## 최종 회귀와 이력

`validate.py external-backend`, `external-flutter`, `checks`는 새 임시 output에서 기존 테스트를
수정 없이 실행한다. 원 P0의 후속 신규-file enumeration fixture 오류와 pre-P0 historical probe
기대는 원본 그대로 실행·분리한다. `validate.py compatibility`의 기존 compatible replay는
원 monetary/codepoint/hash assertions를 그대로 유지한다. 예상된 역사 FAIL을 current PASS에
더하지 않는다. `validate.py format`은 보존 oracle 한 파일만 빼고 나머지 변경 Dart를 검사한다.
일반 제품 source/새 회귀의 형식 검사를 생략하지 않는다.

`validation-*.json`은 command/cwd/exit/elapsed의 실제 기록이다. `final_evidence.py`는 새
output만 압축 수집하여 `final-summary.json`을 만든다. 승인 전 `summary.json`과 이전
B02/A01/A02 조사·실패 artifact는 불변이다. `preserve.py final`은 completion staging 전에
원 1,820개 파일 및 index를 대조한다. completion commit 뒤 index가 바뀌는 것은 정상이다.

Host RSS는 순수 Dart heap이나 Android memory proof가 아니다. file/WAL 크기는 physical
write bytes가 아니며 codec/store work counter는 전층 hash/validate/write accounting을 닫지 않는다.
Phase B 전체 비용·Android VFS/I/O·hardware power-loss 및 R1의 나머지 gate는 별도다.
