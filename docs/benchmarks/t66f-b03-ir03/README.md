# IR03 재현·증거 안내

이 자료는 payload `645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8`의 독립 감사다. 최종 판정은 FAIL이며 제품 교정 source는 없다.

- `findings.json`: 원 IA01–IA07의 수용 상태와 새 N01/N02.
- `integrity.json`, `final-candidate-integrity.json`: 실행 전후 동결 후보 identity.
- `execution-manifest.json`: 정확한 명령·환경·기대·관측·raw 결과와 고유 case 집계.
- `test_ir03_oracles.py`, `ir03_oracles_test.dart`, `ddl_native_probe.dart`: N01과 literal/native byte oracle.
- `test_ir03_installation.py`, `run_installation_control.py`: N02의 deterministic schedule 및 exact 역사 대조.
- `test_ir03_tls.py`, `test_ir03_triggers.py`, `ir03_delta_test.dart`: 독립 TLS principal·trigger event·실제 cold/no-change/card/cash/손상 객체 검증.
- `backend-full.xml.gz`, `flutter-full-*.log.gz`: 최초 전체 실행의 원자료. Flutter 최초8개 환경 실패를 보존한다.
- `flutter-native-rerun.log.gz`: native asset 준비 후 같은8개 assertion의 성공.
- `delta-integration.json.gz`: 새 소형 fixture의 canonical objects·source·Target·금융 oracle와 계수.
- `cleanup-manifest.json`, `final-preservation.json`: 감사 소유 삭제와 원본 보존.

실행용 candidate는 정리했다. 재현 시 sealed HANDOFF의 고정 baseline+payload 알고리즘으로 승인된 새 빈 workspace를 먼저 복원하고 819개 source와 mode를 검증한다. 기록된 시험의 기준 경로는 `/tmp/money-note-ir03-20261023/candidate`이며 외부 audit tooling의 root/import/output 경로만 새 격리 경로에 맞춘다. assertion·제품 canonical 경계·SHA 기대값은 유지한다. 기존 증거를 덮어쓰지 않는다. 실행 당시 source 사본과 경로 전용 adapter 변환을 함께 보존했다.

`reconstruct.py`는 시작 시 빈 output을 요구하므로 보존된 evidence 경로에 그대로 재실행하지 않는다. 역사 control과 현재 정확성 oracle를 섞지 않는다. `after_flutter.py`는 실제 시작한 버전이며 `after_flutter_launched.py`와 동일하다. 최초 no-index diff의 정상 차이 exit1을 오류로 해석한 결과는 별도 보존했고 literal control로 의미를 바로잡았다.

새 소형 P05 회귀의 SQLite·의도적 실패 fixture는 `/tmp/money-note-ir03-20261023/p05-scratch`에 보존했다. 저장소에는 작은 manifest만 넣었다. 이 새 자료를 원 P03 backend/client artifact로 부르지 않는다. `/tmp` 보존은 재부팅 후 유지 보장이 아니다.

새 전체100k cold는 0회다. 고정 H/D 다섯 N·I25 scaling·전체 규모 feasibility·Android·실제 전원 손실·R1·운영 배포는 검증하거나 실행하지 않았다.
