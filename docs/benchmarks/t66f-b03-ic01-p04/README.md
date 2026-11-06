# P04 후반 상태 진단

최종 판정은 **INCONCLUSIVE — PRESERVED STATE OR ESSENTIAL EVIDENCE UNAVAILABLE**다.
원 P03 client397146개는 보존돼 있지만 동일 Target의 완전 backend SQLite/catalog·증명은
원 sandbox cleanup으로 삭제됐다. 실제 D3 HTTP tail·E3·E4는 미실행이다.
historical 다른 NS 객체를 대체하거나 expired observation을 인가로 사용하지 않았다.

`prepare.py`는 원본을 읽기 전용으로 열어 SQLite backup API로6개 clone을 만들고,
실제 모든 SQL 값의 digest와 원 accepted/metadata/B/J를 대조했다.
원본은 `/tmp/mn-p03-real-RMZIIJ/full-client/segmented-store-v1/`에 남아 있다.
위치·SHA·clone 목록은 `evidence/clone-plan.json`에 있다. 이미 있는 clone은 다시 만들지 않는다.

고정 비교는128개 E1 smoke 한 쌍과2048개 E1 네 모드 두 반복뿐이다.
`component_test.dart`는 실제 E1 API로 **기존 객체를 local-only stage에 다시 연결**한다.
실제 missing-object acquisition 또는 새 observation/financial publication이 아니다.
expired manifest는 로컬 입력 fixture이며 transfer 권한을 부여하지 않는다.
mandatory counter ON/OFF와 추가 timing ON/OFF를 독립 선택했고,전체 DB 및 B/D counter가 같다.
실행은 끝났으며 표본을 늘리거나 새로운 full cold test를 실행하지 않는다.

`reconstruct.py`는 P03 원 trace/checkpoint를 읽어 세 관측과 마지막 처리율을 재집계한다.
`analyze.py`는 이미 실행된 보조 구간의 literal hash framing·primary parser span·SQL TEXT oracle를
독립 대조한다. `check_clones.py`와 `check_preservation.py`는 원본·clone·index 보존을 확인한다.
`check_ia07.py`는 역사 cursor delegate를 수정 없이 현재 source에 실행한다.

`run.py`에는 current targeted,small HTTP,namespace reject,E1 component 및frontend build만 있다.
새100k cold 명령은 없다. 과거 증거를 덮어쓰거나 index를 stage하지 않는다.
P04 보고서의 다음 행동은 test-only backend lifetime/handoff와 cleanup 전 일관 source 보존이다.
성능 최적화·counter 정의 변경·TTL 변경·R1·배포는 수행하지 않았다.
