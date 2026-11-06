# IR05 최소 교정 인계

**FAIL — B03 정확성 OPEN.** 원 IR04-N01·IR03-N02·IR03-N01은 IC03 후보에서 통과했다. 별도 새 예외 경계 두 개가 B03 폐쇄를 막는다.

- payload: `dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370`
- archive: `145f26c17d87276da054225d4149c30c76c74eb9505ef8f034b3237fabfe0a21`
- frozen: `/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/dcaf0eef55c6205d768c3274fb0174cc8e3be984a389d719b793f0d5c2d9e370/`

`B03-IR05-N01`은 counters.py:82의 patch 적용과83의 cleanup 등록 사이 취소다. `B03-IR05-N02`는60의 마지막 복원이 중단돼도63에서 registry를 삭제하는 경계다. 두 건 모두 MEDIUM이며 실제 SIGINT 한 번을 잡은 뒤 재진입하면 native parse1회/2B가2회/4B다. worker도 native 자원0인데 diagnostic pending1/completion0이 남는다.

최소 독립 source는 `tests/test_ir05_interrupt_final.py`다. `tests/test_ir05_worker_interrupt.py`, `tests/test_ir05_interrupted_growth.py`가 hold와 반복 누적을 입증한다. 최종 raw는 `interrupt-after-start-current-final.json`, `interrupt-last-release-current-final.json`과 worker JSON이다. parent control 및 작업 중 출력명 충돌은 `audit-output-path-incident.json`에 명시돼 있으며 최종 current/parent는 다른 새 경로에서 재실행했다.

재현은 고정 baseline `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`의 git archive에 frozen source/를 overlay하고 source-manifest를 검증한 독립 실행본에서 한다. 도구의 `/tmp/money-note-ir05-20261024/candidate`를 재구성하거나 audit root/import/output 경로만 새 scratch로 바꾸고 execution-manifest의 pytest 명령을 실행한다. 기존 원 재현의 assertion은 수정하지 않는다. SIGINT는 audit child 자신에게만 전달한다. 실패값 기록 뒤 probe의 patch만 정리하며 이는 구현 교정이 아니다.

별도 구현 세션에서 공유 install_patch·installation의 두 예외 원복 소유권 경계만 교정하고 새 source identity에서 보존된 독립 취소 oracle를 검증한다. parser/금융/원 native-worker 실행 알고리즘·protocol·TTL·SHA 기대값을 바꿀 근거는 없다. 기존/새 frozen candidate·역사 보고서·Git index는 수정하지 않는다. 새로운100k cold·cost grid·R1·배포는 미승인이다.
