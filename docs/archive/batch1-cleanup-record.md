# Repository Hygiene Batch 1

기준선: `phase2/mobile-network / e6a84d2aa39f36e0d7e52d956f1cc6d19d3845d0`. owner가 H01–H05/H08–H09/H17–H19만 승인했다. Phase3 CLOSED·Phase4 미착수, Claim 무기한 유지 정책은 그대로다.

- H01: APK 중복3개를 각각 보존 정본과 SHA-256 재대조 후 삭제했다. `flutter-apk/` 정본·APK metadata·mapping은 보존했다.
- H02: P1-02 harness1개는 Git에 보존된 `final_test_source`와 byte-identical함을 확인한 뒤 삭제했다. 정확한 원문은 [보관된 압축 근거](phase1/evidence/p1-02-flutter-rebuild-raw.json.gz)에서 복원한다. 원래 source로 향하던 보고서 링크도 이 근거로 바꿨다. P1-01의 기능 시험은 보존했다.
- H03/H04/H05/H08/H09: 문서10개·압축 근거5개를 [보관 목차](README.md)의 위치로 이동했다. 압축 근거 bytes는 그대로다. 역사 본문의 판정·수치·음성 결과는 유지하고 Markdown 상대 링크만 재배치했다.
- H17: test cache71개 정리. H18: 재생성 build 중간물1,359개 정리. H19: 원소스가 존재하는 Python cache와 Web 중간물697개 정리.
- 제외219개: H18의 native asset·devicegate 관련/불명확 중간물216개, H19의 보호 관련2개·원소스 미확인 cache1개. dependency·unit_test_assets·canonical APK·기기 증거·DB·키·기존 미게시 작업은 보존했다. H20 staging 정리는 미승인·미실행이다.

삭제 파일은 총2,131개, 해당 파일 할당량은 **5,066,301,440B**다. 삭제 직후 같은 filesystem의 가용 공간은 **5,051,772,928B** 늘었다. 후자는 다른 host 활동의 영향도 받을 수 있어 두 수치를 구분한다. 보관 이동은 용량 절감으로 계산하지 않는다.

각 작업 전에 정확한 경로·신원·symlink 경계와 current-user 열린 handle/mapping을 확인했다. 활성 build/test 도구는 없었다. OS 세션 서비스 systemd/sd-pam/sshd는 build/test 사용 검사와 구분했다. 관련 도구나 다른 프로세스를 실행·중지하지 않았다. 전체 시스템의 접근 제한 프로세스를 완전히 관측했다는 주장은 하지 않는다.

검증은 보호 파일 SHA·기존 파일 metadata·동결 문서·링크/anchor·index 보존 및 scoped diff를 대상으로 한다. 기존 링크 문제는 수정 범위를 넓히지 않고 신규 오류와 구분한다. application runtime source가 바뀌지 않아 build·기능 suite는 반복하지 않는다. 상세 경로·그룹별 크기·실제 검증 결과는 [compact 실행 근거](../benchmarks/repository-hygiene-batch1.json)에 둔다.

실제 확인: 보호 파일 SHA2,651개·범위 밖 파일 metadata39,384개 동일, 링크2,200개·Markdown anchor34개 검사에서 신규 오류0개다. 기존 진단20개는 이전 상태와 동일하며 이번 정리에서 감추거나 수정하지 않았다. 압축 근거5개는 byte-identical, index는 staging 전까지 byte-identical이다.

Git 게시 대상은 승인된 이동과 필요한 링크/목차 및 이 실행 기록뿐이다. 역사 JSON 안의 source 경로와 동결 hash는 재작성하지 않았다. 현재 G1의 O2 고정 문서·B03 source lock·P2-N01 결함/수정 근거·회귀 fixture는 원위치 보존한다. main 병합·운영 배포·Batch2·Phase4는 수행하지 않는다.
