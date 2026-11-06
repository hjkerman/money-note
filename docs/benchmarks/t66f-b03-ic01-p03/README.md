# P03 실제 취득 경로·관측 lease 검증

원 IC01/P01/P02 파일과 index를 바꾸지 않고 새 경로에 측정·회귀 증거를 보존한다.
제품 구현, 규범, source-SHA 기대값 및 역사 finding은 수정하지 않는다.

`run.py backend-targeted`, `run.py flutter-targeted`, `run.py small-http`는 현재 교정
동작을 먼저 확인한다. 원 결함 존재 assertion을 현재 source에서 PASS로 고쳐 쓰지 않는다.
IA07은 원 `direct-experiments.md`의 실제 cursor delegate를 그대로 현재 구현에 실행한다.

`run.py real-path`는 원 B02 seed와 독립 graph oracle를 사용하는 폐기용 TLS 서버에서
24-packet warmup 한 쌍, 160-packet cold prefix 세 쌍, 48번째 packet 뒤 clock 만료를
유발하는 80-packet renewal 한 쌍을 고정 실행한다. 상세 사전 설계는 `plan.json`이다.
각 prefix는 제품 fetcher의 실제 HTTP·검증·E1 transaction을 수행한 뒤 다음 요청 전에
명시 `P03_PREFIX_END`로 종료한다. 이 의도된 중단을 full acquisition 실패로 세지 않는다.
새 DB는 비어 있고 모드 사이 공유하지 않는다. backend root는 같은 서버 내에서 고정된다.

TTL은900초이고 최대 관측3회를 유지한다. 갱신 시험의 +901초는 기존 repository clock
주입 경계이며 wall/CPU/HTTP/SQL 실행을 생략하지 않는다. 이 비용이900초를 실제 기다린
증거이거나 전체100k 완료 증거인 것은 아니다.

논리 bytes는 실제 hash 입력·primary validation span·NEW SQL TEXT/BLOB payload다.
HTTP bytes, SQL bind, SQL 호출 수, 원문 object bytes 및 physical I/O를 구별한다.
SQL timer는 E1의 DB API 구간이며 C1·hash를 포함한 전체 E1 시간으로 이름 붙이지 않는다.
잔여 E2 timer는 parser CPU만이 아닌 순회·검증·cooperation·control의 합이다.
TEMP row callback timer는 SQL에 포함된 observer 시간의 하한이다.

모든 snapshot과 peak는 HOST 진단이다. p95·Android·VFS·전원 손실·Phase B 비용 grid의
PASS를 주장하지 않는다. 상세 실행 판정 및 full-run 여부는 상위 P03 보고서와
`evidence/summary.json`을 따른다. 실패나 미완료면 원 index와 미커밋 구현을 보존하며
완료 명의 commit/push를 하지 않는다.

첫 준비 시도는 원 seed의 `CURRENT_TIMESTAMP` 때문에 역사 raw-value digest 대조에서
실제 HTTP acquisition 전에 실패했다. `evidence/fixture-attempt-1/`에 실행 source·log·
bootstrap counter·fixture를 보존했다. `fixture.py`는 원 seed의 금융 열이 원 보존 G1과
정확히 같음을 확인한 뒤, G1의 각 행 timestamp와 준비 revision만 복원한다. 전100,035행의
canonical VALUE digest assertion을 유지하며 uniform timestamp로 바꾸거나 실패를 skip하지 않는다.
`check_fixture.py`가 비싼 bootstrap 전에 같은 복원을 독립 실행한다. 새 NS/epoch에 따른
객체 identity와 원 raw 값의 byte equality를 구별한다.

교정된 실행은 prefix·renewal 자료를 완성한 뒤 최대600초 동안 `evidence/decision.json`을
기다린다. 별도 유한 분석에서 GO가 확정되어야 `full_run.dart`를 한 번 호출한다.
이 경우 서버 clock offset을0으로 복원하고 별도의 빈 `full-client`를 만든다.
`full-attempt.json`의 존재 guard가 재시도를 금지한다. `full-result.json`이 실제 full 판정이며
prefix 성공·모델·테스트 runner의 상태를 대신 사용하지 않는다. HTTP native response를
그대로 돌려주므로 full driver의 timer는 header 수신까지만 측정한다. entity·완료 시점은
backend 원 trace와 실제 transport 검증으로 대조하고 이 두 시간 경계를 혼동하지 않는다.

최종 실제 전체 시도는1회이며2699.957907초에 관측3의 `OBSERVATION_EXPIRED`로 실패했다.
397146개/259743775B가 durable하고3386개가 남았다. E3/E4는 미도달,accepted null,
pending B/J는 보존됐다. 재실행·완료 commit·push는 하지 않았다. 원 index와 기존 파일은
그대로이며 최종 판정은 FAILED다. `full-analysis.json`은 full group만 따로 집계한다.
`failed-store-fresh-process.json`은 종료 후 새 process의 read-only 상태 대조다.
`finish_analysis.py` 다음 `enrich_analysis.py` 순서로 원 trace를 재집계할 수 있다.
새 전체 실행을 다시 시작하는 명령은 복구 절차가 아니며 이번 작업에서 허용하지 않는다.
