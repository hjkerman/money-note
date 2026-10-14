# T6.6E3 독립 감사 재현 도구

대상은 `de1eb7c956aa0aaaec2bb5b9d031e0948dd1887d`, baseline은
`9a53b139cbb99d40020ba0635cf6b44730f3ca51`이다. 전체 E3 구현과 I25 교정을 함께
검사했다. 판정과 제한은 [독립 감사 보고서](../../t66e3-independent-audit.md)에 있다.

## 실행 조건과 격리

개발 checkout의 `.venv`, Flutter/Dart SDK, `mobile/.dart_tool/package_config.json`,
`native_assets.yaml`을 사용한다. 이 실행의 Flutter는 3.47.4, Dart는 3.13.3이었다.
SDK 경로는 현재 호스트의 `/home/hjkerman/.flutter/bin`이다. 다른 환경에서는 시험
스크립트의 SDK 경로를 그 환경에 맞게 지정해야 한다.

`scripts/benchmarks/t66e2_server.py`는 `RetentionSandbox`로 새 synthetic DB를 만들고
stdin/ASGI bridge로 D1/D2b/D3a/D3b/D3c를 실행한다. 운영 설정·DB·`.env`를 읽지 않는다.
시험용 credential은 비공개 process pipe 안에서만 사용하며 저장 artifact에 포함하지 않는다.
기존 DB 경로를 시험 대상으로 전달하지 말아야 한다. 아래 임시 경로는 매 재실행마다 새로
선택한다. `--basetemp`는 pytest가 해당 경로를 정리하므로 재사용 데이터 경로를 지정하면 안 된다.

## 재현 명령

저장소 root에서 새 경로를 사용한다.

```bash
E3_AUDIT_OUTPUT=/tmp/mn-e3-rerun-results \
  .venv/bin/python -m pytest -q docs/benchmarks/t66e3-audit/test_e3_audit.py \
  --basetemp=/tmp/mn-e3-rerun --junitxml=/tmp/mn-e3-rerun.xml

cd mobile
E3_AUTH_CORPUS=/tmp/mn-e3-rerun/e3-independent-corpus0 \
  /home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  ../docs/benchmarks/t66e3-audit/authority_test.dart \
  > /tmp/mn-e3-authority-rerun.log 2>&1
```

첫 명령은 Python 31개, 두 번째는 Flutter 15개를 실행한다. 총 46개이며, 비용 시험 안의
여러 publication과 full/incremental 두 경로를 별도 시험으로 부풀려 세지 않는다.
감사 당시 Python 실행은 28개와 추가 3개로 나뉘었다. 마지막 비용 2개 재실행은 중복이다.
`E3_AUDIT_CORPUS`는 **이 도구가 새로 생성한 fixture**를 재사용할 때만 사용한다.
fixture 재사용 때에도 C1/hash/typed closure/F(raw)/Patricia를 다시 검증한다.

## 독립 oracle와 계측 범위

- `oracle.py`: Python JSON/C1, SHA-256 domain, typed edge, 11-table raw state,
  F(raw) fact families와 Patricia를 독립 계산한다. 제품의 graph/facts helper를 호출하지
  않는다. SQLite는 새 read-only 연결로 pointer/receipt checksum, current/previous closure,
  persisted edge, root pin을 검사한다.
- `test_e3_audit.py`: synthetic source mutation, 96행 삽입/삭제, 반복 한 행 변경, hash-valid
  부정 target, corruption, stale base, 실제 SQLITE_BUSY, 실제 SIGKILL을 제어한다.
- `probe.dart`: E1/E2/E3의 실제 API를 호출한다. 검증 알고리즘은 수정하지 않는다.
- `audit_trace.dart`: 폐기용 source copy의 `sqlite3.open()` 결과만 proxy로 감싼다.
  제품 `work` counter 대신 실제 SQL 호출·반환 행·BLOB bytes·object identity를 센다.
  pin INSERT/UPDATE는 native `updatedRows`, cascade DELETE는 삭제 직전 독립 조회로
  해당 generation의 실제 pin 수를 센다. observer 자체의 보조 조회는 제품 SQL 수에서
  제외하며 그 조회와 JSON 관찰 비용은 wall-clock에 포함된다. SQLite VM step/page 수를
  계측한 것은 아니다. 알 수 없는 DB API는 허용하지 않고 시험을 실패시킨다.
- `authority_test.dart`: 계측하지 않은 실제 AppState/API/session 경로를 검사한다.
  pre-COMMIT hook와 acquisition barrier에서 authority를 바꾸고 별도 SQLite 연결로
  accepted pointer/sequence를 읽는다. 기존 OfflineStore 파일 bytes도 비교한다.
- `before_probe.dart`: 보존된 `i25-before-worktree.tgz`를 안전하게 읽어 최초 E3 source를
  임시 copy에 복원한다. archive에 없는 `graph.dart`/`fetch.dart`는 base commit에서 가져온다.
  나머지는 현재 checkout의 변경 없는 source다. 이것은 별도 커밋을 실행한 것이 아닌
  **보존 source를 조립한 counterfactual 재현**이다. 같은 SQL observer로 전체 작업을 센다.

전체 graph enumeration과 독립 persisted oracle는 측정 phase 밖이다. 비용 표의 cold
latency는 최초 store open 뒤부터이고, reopen 시나리오는 open/recovery를 포함한다.
HTTP payload 수는 fixture transport의 실제 exchange 호출을 센 것으로, 실제 TCP RTT
benchmark가 아니다. 실제 socket 회귀는 별도로 기존 E2-A01 native 5개를 실행했다.

## 보존 결과

| 파일 | 내용 |
|---|---|
| `summary.json` | Git 초기 상태, 실제 회귀 개수·시간, 독립 case 이름, 정적 검사, query plan, 원본 archive/hash 보존 |
| `cost-before.json` | 142/1,728-object 교정 전 source의 실제 SQL·pin 작업량 |
| `cost-after.json` | 교정 후 모든 측정 phase, SQL histogram, body/row/unique-object/pin 수 |
| `case-evidence.json` | 부정 target, corruption, rollback/readback, stale base, SIGKILL, BUSY 결과 |
| `fresh-persisted.json` | 실행 종료 뒤 새 연결 6개로 다시 확인한 current/previous graph·receipt·pins |

합성 DB, credential, 전체 성공 로그, generated fixture payload는 커밋하지 않는다.
원시 로그는 이번 호스트의 `/tmp/mn-e3-audit`에 남겼지만 영구 가용성을 전제하지 않는다.
재현 스크립트와 요약 근거를 저장소에 보존한다. 기존 `docs/benchmarks/t66e3/`의 모든
측정 및 archive는 수정하지 않았고 hash를 `summary.json`에 기록했다.

첫 독립 시험은 계약에 없는 `body_bytes_read < 100000` 가정을 사용해 19 PASS/1 FAIL이었다.
큰 fixture의 동일 generation은 bounded leaf/H 확인 때문에 164,737 bytes를 읽었다.
임의 상한을 제거하고 실제 leaf/object/SQL/bytes와 규모 비교를 기록하도록 감사 harness를
수정했다. 기존 제품 assertion이나 구현은 수정하지 않았다. 최종 판정에 이 이력을 숨기지 않는다.

이 결과는 호스트 process-crash 검증이며 OS crash나 실제 Android power-loss 시험이 아니다.
RSS·device p95·50k/100k 전체 성능·E4/R1의 reader/legacy 설치는 이번 범위 밖이다.
