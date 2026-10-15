# E4-A01 독립 targeted re-audit 증거

대상 `37293dc8b26ca08f94e240408354a6ab6f3d98ac`, 기준 `7fc5420`.
판정과 지원 범위는 [감사 보고서](../../t66e4-a01-independent-reaudit.md)에 둔다.
제품·원 FAIL 보고서·원 반례·구현 측 benchmark를 수정하지 않는다.
모든 DB/root/credential은 새 synthetic fixture다. Phase B/R1/운영 활성화 도구가 아니다.

## 새 독립 사례

`independent_test.dart`의 RA01–RA18와 `cost_test.dart`의 두 규모가 새 20개다.
**17 PASS / 3 FAIL**이며 RA16–RA18은 E4-RA01 MEDIUM의 보존 반례다.
원 45개 Phase A 및 구현 correction 28개, child 호출·재실행은 새 사례로 세지 않는다.

RA01은 같은 SQL operation의 prepared→installed 전환, RA02는 exact source ABA replay,
RA03은 두 handle/네 recovery, RA04는 선행 실제 SQL writer, RA05는 await 뒤 mandatory
trigger 손상, RA06은 await 뒤 B 변경, RA07은 유효 J 추가, RA08은 잘못된 null installed
기대값, RA09는 native 마지막 hook의 source 변경, RA10은 같은 checksum/다른 UUID,
RA11은 추가 metadata 비교, RA12는 반복 합법적 복구·재개방, RA13은 SQL 검사 뒤 경쟁
connection, RA14는 실제 COMMIT BUSY의 보상 중 source 교체, RA15는 최신 AppState 설치
실패 뒤 오래된 recovery를 검사한다. RA16/17은 현재 SQL owner가 있는데 predecessor가 없는
legacy/native recovery, RA18은 그 상태의 실제 AppState native 성공 뒤 Frozen-B 연결 유실이다.
한 metadata 필드만 변경하며 object/receipt/checksum을 재해시하지 않는다.
source/B/pending·SQL rows를 별도 연결로 읽는다.

새 비용 시험은 원 독립 SQL observer를 임시 source copy에 연결한다. stale conflict, 합법적
owned rollback, 그 뒤 warm read, 실제 fresh-process cold read를 두 규모에서 측정한다.
제품 supplied counters를 판정 oracle로 읽지 않는다. `fresh_cost_test.dart`는 임시 copy에만
있는 audit_trace.dart를 필요로 하므로 `measure.py`를 통해서만 실행한다.

`observe_request.py`는 원 반례의 assertion을 유지한 임시 copy에서 coordinator begin의 실제
ticket 정수와 A source를 추가 관찰한다. 제품에는 logger나 ticket API를 추가하지 않는다.
원 uninstrumented reproduction은 별도 실행했고 이 관찰을 새 case로 계수하지 않는다.

## 실행

새 출력 디렉터리를 사용한다. production 경로를 입력하지 않는다.

```bash
mkdir -p /tmp/mn-e4-a01-independent-rerun
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=REAUDIT_OUTPUT=/tmp/mn-e4-a01-independent-rerun/new.json \
  ../docs/benchmarks/t66e4-a01-reaudit/independent_test.dart \
  > /tmp/mn-e4-a01-independent-rerun/new.log 2>&1
# 위 전체 새 시험은 E4-RA01 미교정 제품에서 3 FAIL / exit 1이 예상된다.
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=AUDIT_E4_STALE_OUTPUT=/tmp/mn-e4-a01-independent-rerun/original.json \
  ../docs/benchmarks/t66e4-audit/stale_recovery_test.dart \
  > /tmp/mn-e4-a01-independent-rerun/original.log 2>&1
cd ..
python3 docs/benchmarks/t66e4-a01-reaudit/measure.py /tmp/mn-e4-a01-independent-rerun/cost
python3 docs/benchmarks/t66e4-a01-reaudit/observe_request.py /tmp/mn-e4-a01-independent-rerun/ticket
E4_A01_OUTPUT=/tmp/mn-e4-a01-independent-rerun/crash .venv/bin/python -m pytest -q \
  docs/benchmarks/t66e4-a01/test_crash.py
```

원 Phase A suite, 원 cost/6 crash/P0 compatible replay, correction unit21/concurrent1/crash6,
full Flutter/backend와 static checks도 별도 실행한다. 실제 이번 실행의 각 log 이름은 collect.py에
명시돼 있다. 완료된 결과만 사용하며 `collect.py <출력 경로> --require-complete`는 필요한
완료 수·done 상태·exit·backend 결과와 문서화한 3 FAIL이 없으면 거부한다.
이 guard는 감사 완료 여부를 검사하며 verdict를 PASS로 바꾸지 않는다. harness 오류·초기 formatting 차이를
최종 PASS로 덮어쓰지 않는다. 성공 로그, 실제 DB, APK, credential은 commit하지 않는다.

## 증거 해석

`inventory.json`과 `preservation.json`은 최초 refs/22파일 및 원 69파일·원 반례 보존이다.
`cases.json`, `summary.json`은 실제 실행 결과, `persisted.json`은 direct SQL/file 관찰,
`original-reproducer.json`, `operation-observation.json`은 A/B source와 원 ticket,
`original-cost.json`, `new-cost.json`은 actual SQL/BLOB/function-entry 관찰이다.
`crashes.json`은 실제 SIGKILL 직후와 fresh-process recovery의 독립 graph/lineage 결과다.
`finding-e4-ra01.json`은 RA16–RA18의 source unlink, SQL owner 보존과 native 성공 이후
Frozen-B read 실패를 별도로 보존한다. 원 stale-race 반례가 통과해도 이 새 결함 때문에
최종 verdict는 FAIL이며 Phase B는 차단된다.

영구 artifact는 raw 금융 synthetic rows 대신 source/table/control/closure digest와 root/receipt,
file SHA-256/operation metadata를 보존한다. 원 graph oracle는 실제 모든 bytes/typed edges를
확인한 뒤에만 이를 축약한다. 값의 단순 표시 동등성으로 lineage/hash를 승인하지 않는다.

SQL count는 실제 calls, bytes는 object BLOB이다. 반환 rows를 VM scan count로 바꾸지 않는다.
sql_texts는 unique statement 목록이므로 statement별 frequency라고 부르지 않는다.
metadata/J 파일·물리 I/O·Android peak memory는 bytes 수치 밖이다. fresh-process cold O(N)과
합법적 interruption recovery의 full B 읽기는 normal warm cost와 구분한다.

지원 파일 writer는 기존 owning AppState/isolate다. SQLite의 별도 connection writer는 실제로
시험한다. 임의 process의 비협력 파일 rename에 대한 전역 CAS나 power-loss 보장을 주장하지 않는다.
일반-user segmented Offline/R1 gate는 계속 닫혀 있다.
