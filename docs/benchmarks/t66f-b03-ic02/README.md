# IC02 — N01/N02 교정 검증

이 디렉터리는 구현 측 검증과 미동결 source inventory다. 원 IR02 archive와 IR03 FAIL finding은 변경하지 않는다. 새 N=100k cold 실행은 하지 않는다.

- 보고서: `../../t66f-b03-ic02-ir03-n01-n02-correction.md`
- 원 IR02 대비 구현 diff: `implementation.diff`
- 다음 freeze 검토용 source inventory: `corrected-candidate-manifest.json`
- 원 IR03 Dart assertion의 경로 adapter: `ir03_oracles_adapter.dart`
- 현재 원자료와 정확한 명령/exit/source SHA: `evidence/`

다음 명령은 이미 존재하는 task-owned scratch를 지정해 저장소 root에서 실행한다. `run_verification.py`는 `backend`/`mobile` cwd와 evidence 경로를 설정한다. 기존 scratch를 임의로 재사용하거나 삭제하지 않는다.

```bash
IC02_SCRATCH=/path/to/new/task-owned/scratch .venv/bin/python docs/benchmarks/t66f-b03-ic02/run_verification.py backend-full
IC02_SCRATCH=/path/to/new/task-owned/scratch .venv/bin/python docs/benchmarks/t66f-b03-ic02/run_verification.py flutter-full
```

backend 전체는 승인된 원 IC01 plugin으로 역사 결함-existence 네 assertion만 historical collector에서 실행한다. Flutter 전체는 일반 current suite, 원 독립 current oracle 11개, 원 historical defect-existence 3개를 실행한다. 경로 adapter의 원 source/hash/치환 목록을 저장하며 assertion은 바꾸지 않는다. 실제 실패를 SKIP/XFAIL하지 않는다.

원 IR03 Python N01/N02는 source가 byte-identical한 복사본에서 실행했다. `/tmp/money-note-ir03-20261023/candidate` 경로를 요구하는 원 source 때문에, 이 작업이 새로 만든 symlink를 소유한 동안만 동결/교정 disposable tree를 연결했다. 타 작업의 기존 경로나 archive를 바꾸는 방식으로 재현하지 않는다. 정확한 source와 command는 `evidence/original-reproduction.json` 및 `original-*-final` 원자료를 사용한다.

독립 감사 재현의 FAIL은 의도적으로 실패한 동결판 결과다. 교정판의 실제 결과와 분리해서 해석한다. `pre-fix/python-concurrent-install.json`은 실패판 자료로 잘못 분류된 초기 파일이므로 원 N02 실패 증거로 사용하지 않는다.

보존 절차 위반 두 건을 숨기지 않는다. P02 raw XML의 exact 사본 손실과 Git index stat cache 갱신은 보고서 및 `evidence/evidence-preservation-incident.json`, `evidence/preservation-review.json`을 확인한다. staged entry, 원 IR02 archive, 원 IR03 retained evidence, source lock은 별도 hash로 검증한다. 구현 테스트의 통과만으로 전체 작업을 PASS 처리하지 않는다.
