# IC06 동결 후보: 다음 단계는 구현 비참여자의 직접 독립 감사

이 후보는 구현 측 교정·회귀 결과다. IA04와 B03은 독립 OPEN이다. 별도 일반 준비 검토를 반복하지 말고 아래 경계부터 독립 oracle로 검사한다. 원 IR06 FAIL·finding은 보존했다. 승인 범위는 B03 계측 정확성·소유권·유한 자원과 실제 D→E 회귀다. N=100k cold, five-point cost grid, I25 large-N, Android VFS/power loss, 배포는 포함하지 않는다.

후보 payload: `@PAYLOAD@` / archive SHA-256: `@ARCHIVE@` / base: `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`.

## 무결성과 재구성

아래 repo는 고정 Git object와 runtime 의존성만 제공한다. 시험 source는 archive에서 복원한다. audit_tree와 audit_scratch는 존재하지 않는 새 작업 소유 경로를 쓴다. VENV는 CPython 3.12.3과 repository requirements lock의 기존 runtime이다.

```bash
repo=/home/hjkerman/codex/money-note
snapshot=@SNAPSHOT@
VENV="$repo/.venv"
audit_scratch="$repo/work/ic06-independent-audit"
audit_tree="$audit_scratch/tree"
mkdir -p "$audit_scratch"
(cd "$snapshot" && sha256sum -c SHA256SUMS)
"$VENV/bin/python" - "$snapshot" "$audit_scratch/freeze.py" <<'PY'
import hashlib,json,pathlib,sys,tarfile
s=pathlib.Path(sys.argv[1]); m=json.loads((s/'source-manifest.json').read_text())
p='docs/benchmarks/t66f-b03-ic06/freeze.py'
e=next(e for e in m['entries'] if e['path']==p)
with tarfile.open(s/'candidate.tar.gz') as t:b=t.extractfile('source/'+p).read()
assert hashlib.sha256(b).hexdigest()==e['sha256']
pathlib.Path(sys.argv[2]).write_bytes(b)
PY
IC06_BASE_REPOSITORY="$repo" "$VENV/bin/python" "$audit_scratch/freeze.py" verify "$snapshot" "$audit_tree"
ln -s "$VENV" "$audit_tree/.venv"
cd "$audit_tree"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$audit_tree/backend" IR06_TREE="$audit_tree"
```

verify는 payload canonical UTF8 JSON(entries), 파일 수·bytes·mode, 삭제, untracked source, archive SHA, metadata, untouched baseline blob까지 검사한다. SHA256SUMS는 archive와 별도 manifest·freeze·HANDOFF도 고정한다. 읽기 전용 권한은 WORM이 아니다.

## 원 IR06 네 실패: assertion 변경 없이 먼저 실행

```bash
"$VENV/bin/python" docs/benchmarks/t66f-b03-ir06/tests/pep669_released_tool_probe.py
"$VENV/bin/python" docs/benchmarks/t66f-b03-ir06/tests/monitoring_matrix_probe.py instrument 8
"$VENV/bin/python" docs/benchmarks/t66f-b03-ir06/tests/monitoring_matrix_probe.py instrument_workers 8
"$VENV/bin/python" docs/benchmarks/t66f-b03-ir06/tests/monitoring_matrix_probe.py stage 8
"$VENV/bin/python" docs/benchmarks/t66f-b03-ic06/semantics.py
"$VENV/bin/python" -m pytest -q -p no:cacheprovider backend/tests/test_logical_cost_ic06.py --basetemp="$audit_scratch/pytest-monitoring" --junitxml="$audit_scratch/monitoring.xml"
```

CPython 3.12.3은 free 후 get_tool=None, local/global mask 유지·callback 유지·실제 전달이 관측된다. 3.13 규약도 동일하다. 3.14 규약은 free 시 clear_tool_id를 호출한다. 3.14 정상 free 후 활성 잔존은 문서상 NOT REACHABLE이며 3.14 실행 성공을 주장하지 않는다. 원 재현은 실제 감사 runtime 3.12.3에서 실행한다. 상세 계약은 source `docs/benchmarks/t66f-b03-ic06/monitoring-contract.md`, 175개 새 검사 mapping은 `monitoring-state-matrix.json`이다.

custom ID0..5의 global mask nonzero 또는 entry code local mask nonzero는 할당 이름과 무관하게 획득 전에 `B03 monitoring entry observer unsupported; measurement incomplete`로 거부한다. inspection unavailable은 `B03 monitoring state unavailable; measurement incomplete`다. inactive 등록 callback, 이름만 있는 ID, 무관한 코드의 local event는 허용한다. B03 자체 custom ID는 없다. legacy trace/profile은 IC05 인계를 유지한다. callback introspection을 위해 callback을 교체하거나 타 tool의 mask를 바꾸지 않는다.

외부 monitoring 설정은 동기 entry 동안 안정적이어야 한다. ready 재검사는 획득 도중 관측 가능한 변경을 rollback하지만 검사/획득을 원자화하지 않는다. 마지막 검사 뒤 외부 변경·ABA·reentrant 변경의 완전한 차단을 주장하지 않는다. Python public API에는 이를 위한 협력 없는 원자 snapshot/lock이 없다. 실제 callback이 preflight 시작 자체를 실패시키면 원 예외를 보존하고 아직 owner를 획득하지 않아야 한다.

## 원 IC04·IC05와 reference/stage/native hold

```bash
"$VENV/bin/python" docs/benchmarks/t66f-b03-ic06/backend.py -q -p no:cacheprovider backend/tests/test_logical_cost_ic04.py::test_cancelled_outer_enter_return_transfers_no_unowned_reference_or_stage --basetemp="$audit_scratch/pytest-original-three" --junitxml="$audit_scratch/original-three.xml"
"$VENV/bin/python" docs/benchmarks/t66f-b03-ic06/backend.py -q -p no:cacheprovider backend/tests/test_logical_cost_ic04.py backend/tests/test_logical_cost_ic05.py backend/tests/test_logical_cost_ic06.py --basetemp="$audit_scratch/pytest-owner" --junitxml="$audit_scratch/owners.xml"
mkdir -p "$audit_scratch/ir06-evidence"
IR06_EVIDENCE="$audit_scratch/ir06-evidence" "$VENV/bin/python" -m pytest -q -p no:cacheprovider docs/benchmarks/t66f-b03-ir06/tests/test_ir06_lifecycle.py --basetemp="$audit_scratch/pytest-ir06"
```

backend.py는 IC04의 마지막 세 JSON 출력용 module.__file__만 재구성본의 폐기 가능한 work로 보낸다. assertion/ROOT/계측 source는 그대로다. static preflight 거부는 inner.__enter__ 호출0, reference0, stage0, wrapper 원 identity, native pending0이어야 한다. GC 비활성24회×6 조합과 실제 parse 입력 buffer를 독립 profile witness로 대조한다. 정상 nested scope 각각1회·원 UTF8 bytes, 취소 scope0회·0B, 후속 parse 누락/중복0이어야 한다. 고정 seed IR06 model과 native finish/late tail은 위 보존 suite에 있다.

## IA01–IA07·IR03/IR04/IR05

```bash
"$VENV/bin/python" docs/benchmarks/t66f-b03-ic05/verify.py prepare-originals "$audit_scratch/originals"
"$VENV/bin/python" -m pytest -q -p no:cacheprovider "$audit_scratch/originals/tests" --basetemp="$audit_scratch/pytest-preserved" --junitxml="$audit_scratch/preserved.xml"
"$VENV/bin/python" "$audit_scratch/originals/tests/original_IA05.py"
"$VENV/bin/python" "$audit_scratch/originals/tests/original_IA06.py"
"$VENV/bin/python" "$audit_scratch/originals/tests/original_IA07.py"
```

67건 mapping: IA01–06은 test_ir03_oracles.py의 test_ia01_nearest_savepoint/test_ia02_conflicts_and_prefix/test_ia03_first_comment/test_ia04_nested_install/test_ia05_rejected_dispatch/test_ia06_owner32_before_execution_and_release. IA07은 setup176/185행·generation0을 직접 확인한다. IA06 원 무상한 script는 owner33에서 documented capacity 오류(exit1)가 맞고 현재 strict test가 실행 전 거부·rollback weakref0을 검사한다. 이 기대된 exit1을 suite 실패로 합치지 않는다.

IR03-N01: test_ir03_oracles.py::test_ddl_observer_reinstallation 및 test_ir04_schema.py. IR03-N02: test_ir03_installation.py와 test_ir04_installation.py. IR04-N01: test_ir04_rollover_native.py. IR05-N01/N02: test_ir05_interrupt_final.py, test_ir05_worker_interrupt.py, test_ir05_interrupted_growth.py. historical defect-existence backend4/Dart3은 원 assertion을 승인된 역사 wrapper에서 실행하며 현재 strict oracle와 구분한다.

## 실제 D3→인증 HTTP→E2→E1, E3/E4, source lock

mobile 의존성만 준비하고 source는 live에서 복사하지 않는다. 같은 Flutter SDK·pubspec.lock을 사용한다. frontend의 node_modules와 Python .venv만 runtime link로 쓸 수 있다.

```bash
cd "$audit_tree/mobile"
flutter pub get --offline
flutter test --no-pub --machine --concurrency=1 --dart-define=B03_OUTPUT="$audit_scratch/http" test/segmented_logical_cost_ic01_test.dart test/segmented_logical_cost_ic02_test.dart test/segmented_logical_cost_p02_test.dart test/segmented_logical_cost_test.dart test/segmented_logical_cost_boundaries_test.dart test/segmented_logical_cost_lineage_test.dart test/segmented_logical_cost_source_lock_test.dart "$audit_scratch/originals/tests/ir03_oracles_test.dart" "$audit_scratch/originals/tests/ir04_schema_test.dart" "$audit_scratch/originals/tests/ir03_delta_test.dart" "$audit_scratch/originals/tests/integration_original_test.dart" test/segmented_logical_cost_http_test.dart
cd "$audit_tree"
"$VENV/bin/python" docs/benchmarks/t66f-b03-ic06/source_locks.py
```

cold/no-change/card/cash/corrupt rejection·native hash/parser·canonical body 실제 길이/SQL BLOB·E1 durable publication·E3 guard→COMMIT·E4 accepted read·P0 lineage·OFF/ON 동등성을 검증한다. 보호6개와 Dart helper, binding protocol을 바꾸면 안 된다. source_locks.py는 archive 내부 이전 IC05 SHA 기대값을 읽는다. 전체 snapshot integrity 검사가 다른 product source의 동일성도 확인한다.

## 새 전체 backend 근거와 바로 재실행할 명령

@BACKEND@

첫 전체 실행의5건은 checkout 내부 tmp_path를 기존 t66d2a harness가 거부해 실패했다. 단일 IC06 scratch를 /tmp로 옮긴 뒤 같은5건과 전체 suite를 다시 실행했다. 최초 실패 기록은 backend-complete.json/xml/log.gz로 보존했다. 제품 source나 원 assertion은 바꾸지 않았다.

```bash
cd "$audit_tree/backend"
"$VENV/bin/python" ../docs/benchmarks/t66f-b03-ic06/backend.py -q -p no:cacheprovider --basetemp="$audit_scratch/pytest-backend" --junitxml="$audit_scratch/backend.xml"
```

archive `context/docs/benchmarks/t66f-b03-ic06/evidence/`에 command/source SHA·exit·JUnit·gzip raw와 시작/보존 검사가 있다. 새 full N=100k cold0, Phase B grid 미실행이다. 새 material defect면 원 expected/actual을 보존하고 FAIL한다. 모두 독립 통과하면 B03 correctness만 별도로 닫을 수 있다. 본 구현 작업은 독립 closure를 선언하지 않는다.
