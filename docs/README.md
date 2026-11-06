# 문서 안내

현재 사이클: **Backend/Web 배포·Mobile 2.5.0(16) 게시·owner의 기기 업데이트 및 A/B 정리 완료**. [현재 기준선](project-state.md#2026-11-06-개발-사이클-종료-기준)을 우선한다. 아래 과거 단계의 미착수·배포 미승인 표시는 당시 이력이며 현재 release 상태를 뜻하지 않는다. T6.6 운영 활성화와 역사적 gate 종결은 별개다.

장기 유지 문서와 단계별 작업 기록을 구분한다.

## 현재 최적화·개선·감사 작업

[작업 기록 통합 목차](development-reports/README.md)에서 로드맵과 P1 결과, 이전 최적화·개선·감사 기록을 찾는다. 코드·동결 근거의 경로 의존성이 있는 원본은 기존 위치를 유지한다.

완료된 단계의 승인된 보관 자료는 [역사 기록 목차](archive/README.md)에 있다. 원문 판정과 음성 근거를 보존하며 현재 정책은 아래 규범 문서를 따른다.

Repository Hygiene는 **CLOSED**다. Batch 1·Batch 2 독립 감사 결과를 owner가 수용했고, 수동 push 성공과 원격 HEAD `25e9f5c74a1c7ed05082378391c673ee4679858c`를 확인했다. [종결 기록](archive/repository-hygiene/batch2-closure.md)에 최초 SSH 실패와 B2-M01/B2-I01 해결을 보존한다. 이는 해당 Batch 종결 당시 기록이다. 이후 Phase4 F01/F02/L01 수용·배포와 별도 A/B 삭제 승인은 현재 기준선에 기록하며, 당시 제외 후보 전부가 현재도 존재한다고 주장하지 않는다.

## 장기 유지 문서

- [현재 프로젝트 상태](project-state.md)
- [금융 도메인 기준](domain-model.md)
- [구조·서버 authority·신뢰 경계](architecture.md)
- [API](api.md)
- [DB](database.md)
- [Offline 계약](offline-mode.md)
- [운영·배포·복구](runbook.md)
- [보안](security.md)
- [알려진 이슈](known-issues.md)
- [검증 안내](test-plan.md)
- [개발 산출물 위생](development-artifact-hygiene.md)
