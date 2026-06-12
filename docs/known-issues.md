# 알려진 이슈

현재 구조 리팩토링 기준으로 기능을 막는 알려진 이슈는 없다.

## 주의사항

- Snapshot restore는 장부 운용 데이터를 교체하는 위험 작업이다. 사용자 계정, 세션, 관리 로그, 공유 PIN 해시는 포함하거나 복원하지 않는다.
- Snapshot restore는 manifest 검증, 임시 DB dry-run, mandatory `pre_restore` 생성과 검증을 통과해야 실제 운영 DB를 수정한다.
- `pre_restore`는 설정 모달에서 목록 조회, 다운로드, 되돌리기를 할 수 있으며, filename whitelist와 경로 검증으로 `snapshot-backups` 밖의 파일 접근을 막는다.

## 해결됨

- 정기결제 등록 후 200 OK인데 화면에 반영되지 않던 문제는 `confirmed_month IS NULL` 조회 조건 문제였고, 현재 테스트로 회귀를 막는다.
