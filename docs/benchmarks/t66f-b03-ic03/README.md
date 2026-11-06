# IC03 설치 세대 교대 교정

이 디렉터리는 구현 측 교정·검증·동결 증거다. 독립 B03 PASS를 선언하지 않는다. 원 IR03/IR04 재현·실패 기록과 과거 동결 후보는 변경하지 않는다.

- `implementation.diff`: IR04 동결 source 대비 유일한 진단 구현 변경.
- `verify.py`: IC03 전용 gzip 원문·명령·exit·source SHA 기록. 기존 label을 덮어쓰지 않는다.
- `freeze.py`: source-only manifest, atomic snapshot, 고정 Git base 재구성과 byte/mode 검증.
- `corrected-candidate-manifest.json`: 검증 완료 후 만들어지는 새 후보 inventory.
- `evidence/summary.json`: 완료된 구현 측 결과; 실패한 역사 control과 도구 오류를 별도 분류한다.
- `evidence/original-adapters.json`: 원 assertion을 유지한 절대 경로 치환만 기록한다.

원 trace reproducer는 `docs/benchmarks/t66f-b03-ir04/tests/test_ir04_rollover_native.py`다. 설치 진입 전 정지를 실제 Python trace로 강제하고 native parser 진입을 직접 센다. 새 `backend/tests/test_logical_cost_ic03.py`는 별도의 실제 delegate/frame·generation·hold oracle이다. 같은 bytes의 두 실제 호출을 합치지 않는다.

```bash
.venv/bin/python docs/benchmarks/t66f-b03-ic03/verify.py LABEL -- .venv/bin/python -m pytest -q -p no:cacheprovider backend/tests/test_logical_cost_ic03.py
```

새로운 작업 소유 scratch와 새 label을 사용한다. backend 전체 회귀는 `IC03_SCRATCH`를 지정한 `verify.py backend-inner`를 backend cwd에서 실행한다. 네 역사적 defect-existence assertion은 이미 승인된 IC01 historical collector로, 현재 oracle은 현재 collector로 실행한다. 원 expectation의 수정·SKIP/XFAIL은 없다.

동결은 `evidence/summary.json`의 구현 검증 PASS 뒤에만 가능하다. 새 digest 경로에 atomic rename하며 기존 후보를 덮어쓰지 않는다. 다음 구현 미참여 XHigh auditor의 실제 재감사는 새 snapshot의 `HANDOFF.md`를 따른다. 새100k cold·Phase B grid·R1·배포는 실행하지 않는다.
