# B08 실험 후보 인계

원 B03 baseline에서 backend/app/db_migrations.py의 schema 전용 기대 계약 컴파일만 최대1항목의 불변 cache로 재사용했다. 실제 DB SQL/trigger/state 검사 본문은 그대로다. 전용22개 검사와 영향 기능 검사, 30 ASGI 요청의 source별 동등한 logical counters를 검증했다.

객체 요청13개씩에서 handler3.180023143→2.841368689초, 10.6494%의 국소 감소를 관측했다. 전체 Flutter cold 개선은 미검증이다. artifact exact equality 검사는 기존7ad 선언과 새5861 engine의 차이로 실패한 원문을 보존한다. release artifact/admission을 바꾸지 않았고 이 후보는 배포 가능한 release가 아니다. IR07 독립 감사 대상도 아니다.

재구성은 원 Git commit ebcbd54d90eeee194a04b9eea6367f446ee2fd28의 archive 위에 source/ 파일을 덮어 적용한 뒤 metadata/source-manifest.json의 bytes/mode/hash를 대조한다. baseline은 원 B03 overlay899파일을 별도로 복원한다. source payload와 engine SHA를 구분한다. 전용 테스트는 source에 포함된 원 함수 AST와 독립 literal 기대값을 사용한다. tests/fixtures 및 과거resolver gzip은 원 Git tree의 변경 없는 테스트 의존성이다.

원 archive/현 live dirty tree/과거 증거를 변경하지 않는다. 재측정은 새 task-owned evidence/scratch에서만 수행하며 B08의32합산 operation/120초 제한과 원900초 TTL/3attempt를 지킨다. 자세한 source diff·회귀 및 요청 순서·시간은 보존된 B08 evidence를 참조한다. 다음 단계는 별도 정확한 engine 입장·직접 artifact 승인 후 N1k 실제 Flutter cold A/B 자격 검증이다.
