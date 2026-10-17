# C0 — 후속 검증 계획과 측정 계약

규범 §35의 H는 `hot/참조 working set와 required control/policy descriptor 크기`, D는
`base 이후 changed rows`, N은 `전체 역사 row`다. 의무 N grid는 1k/5k/10k/50k/100k다.
규범은 H/D의 숫자, warmup·반복 횟수, percentile estimator, latency 절대 한계를 지정하지 않는다.
따라서 아래 선택은 규범의 추가 threshold가 아닌 공개된 실험 설계다.

기존 `scripts/benchmarks/t66d2b_writers.py`의 seed 662602, 평가일 2026-10-05,
current ledger 105행 및 고정 관계 fixture를 재사용한다. N은 이 기존 명세와 같은 전체 ledger
행 수이며 archive N−105, 나머지 10개 table 크기는 별도 기록한다. H를 105라는 숫자 하나로
대신하지 않고 current/참조 행·hot/control canonical bytes를 기록한다. 동일 폭 값 사이의
card/cash UPDATE로 D=1을 유지하고 no-change는 D=0이다. cash create를 누적시켜 H를 늘리지 않는다.
대규모 변경·delete·split은 앞선 실제 HTTP 독립 증거와 구분한다.

독립 HOST grid는 3 warmups + 20 measured samples, monotonic perf_counter_ns,
statistics.median 및 nearest-rank ceil(.95*n)을 사용한다. 실패는 제외하지 않고 중단/증거 보존한다.
이는 전용 기기나 production throughput 증명이 아니다. Cold bootstrap은 1회 기술 표본이며
그 값으로 median/p95를 만들지 않는다. 정상 반복과 restart/full fallback을 별도 분류한다.
압축은 gzip6/Brotli4의 **오프라인 평가**이며 제품 HTTP Content-Encoding 추가가 아니다.
full 원본/segmented JSON entity/base64 decoded/response header 경계를 따로 기록한다.

`coverage-initial.json`은 전체 39절을 A–F 중 정확히 하나로 분류한 실행 전 matrix다.
I1–I25의 상세 기존 증거는 원 `t66f-phase-b/coverage.md`와 원 보고서에 연결한다.
이전 49/7/10개 및 B01 15개 결과는 이월 증거이며 새 case 수에 넣지 않는다.
R1은 별도 소유지만 §34 전체 F dependency에서 없어지지 않는다. §26 미증명 Android proof는
rollout을 차단하며 HOST SIGKILL을 실제 전원 손실 증명으로 쓰지 않는다.

실행 순서: C1 계측/fixture → C2 미검증 adversarial → C3 가능한 전체 grid·비용 →
C4 device/R1 원문 판정 → C5 최종 전체 회귀 → C6 exit reconciliation.
제품 correctness blocker가 확정되면 해당 경로의 비용 실행을 멈춘다. 원 assertion/제품/과거 보고서는 보존한다.
