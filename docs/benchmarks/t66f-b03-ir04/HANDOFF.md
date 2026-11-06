# IR04 감사 인계

판정은 **FAIL**이다. 보존 사고는 별도 판정됐으며 FAIL의 원인은 재현 가능한 Python 설치 수명 중복 계수다. 제품 구현은 수정하지 않았다.

- 후보 source digest: `27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3`
- archive SHA-256: `4655111c579503ef2c0969f82b5dca4830c06ac1123002cd6e8887109728b012`
- 새 동결 경로: `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/27d31eadc2958df67c319acd32393e69d74e703d1f4643588c79213391b7d7e3/`
- 신규 차단 finding: `B03-IR04-N01` · LOW. `findings.json`과 `rollover-native-2.json`/`rollover-native-9.json` 참조.

최소 재현 source는 `tests/test_ir04_rollover_native.py`다. 기준 commit `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`의 git archive에 새 동결 archive의 `source/`를 overlay하고 manifest bytes/mode를 확인한다. 원 도구의 `/tmp/money-note-ir04-20261024/candidate` 경로를 재구성하거나 root 경로만 새 감사 공간으로 치환한 뒤 원 pytest 명령을 실행한다. numeric 기대값·scope 경계·parser는 변경하지 않는다. 실제 하위 parser 1회에 대해 2B 입력이 4B, 9B 입력이 18B로 보고된다. trace는 line343의 preemption만 강제한다.

원 IR03 N01/N02는 현재 후보에서 PASS이고 IA04 원 nested 사례도 3회/6B다. 다만 새로운 설치 세대 교대 결함으로 IA04 전체 closure는 FAIL이다. parent IR02에서도 같은 결함이 재현되므로 IC02가 새로 만들었다고 단정하지 않는다.

별도 구현 세션은 delegate 캡처와 설치 reference/teardown 소유권 경계만 최소 교정해야 한다. 교정 후 새 source identity에서 보존된 독립 재현과 직접 영향 회귀를 검증한다. 현재 read-only snapshot이나 역사 보고서·기대 SHA·Git index는 수정하지 않는다. 새로운 N=100k cold, 비용 grid, R1 및 배포는 허가되지 않았다.
