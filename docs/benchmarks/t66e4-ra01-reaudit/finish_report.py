"""필수 실제 완료 guard가 통과한 뒤 새 감사 보고서의 집계와 footer를 확정한다."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPORT = HERE.parents[1] / 't66e4-ra01-independent-reaudit.md'


def main():
    data = json.loads((HERE / 'summary.json').read_text())
    assert data['completion_guard'] == 'COMPLETE'
    files = data['flutter_full']['files']
    assert files['segmented_e4_ra01_test.dart'] == {'PASS': 42}
    assert files['segmented_e4_a01_test.dart'] == {'PASS': 21}
    assert files['segmented_adapter_authority_test.dart'] == {'PASS': 16}
    assert files['segmented_e4_handoff_test.dart'] == {'PASS': 35}
    assert files['segmented_e4_handoff_crash_test.dart'] == {'PASS': 13}
    assert files['segmented_adapter_crash_test.dart'] == {'PASS': 4}
    table = '''| 검증 | 독립 실행 결과 |
|---|---|
| 원 RA16–18 선택 실행 | 3 PASS / 0 FAIL; 원 assertion 변경 없음 |
| 새 독립 감사 | **29 PASS / 0 FAIL / 0 INCONCLUSIVE** = Dart 18+6, 비용 2, 실제 SIGKILL 3 |
| 원 Phase A 45 | Dart 36 + 원 비용 2 + 실제 종료 6 + P0 compatible replay 1, 모두 PASS |
| 이전 targeted re-audit 20 | 원 Dart 18 + 원 비용 2, 모두 PASS |
| 이전 A01 교정 28 | unit 21 + concurrent 1 + 실제 종료 6, 모두 PASS |
| RA01 교정 51 | unit 42 + native 비용 2 + 실제 종료 7, 모두 PASS |
| E4 authority/race | 기존 grouping 51 PASS; 새 독립 경합은 위 29개와 구분 |
| E4 process-crash | 기존 grouping 36 PASS; 새 독립 SIGKILL 3개는 별도 |
| 전체 Flutter | **1,503 PASS / 0 FAIL / 2 SKIP**, done.success=true, exit 0 |
| E1/E2/E3·I25·Frozen B/J/v4/v7 | full Flutter 포함 suite별 counts/cases와 원 source 보존 확인 |
| E4-P0 구현 / 독립 integration | 183 / 18 PASS |
| P0 independent differential | 24,836 cases / mismatch 0 |
| 별도 E2-A01 socket | 원 5 + 독립 targeted 9 PASS; shared client/FD/C1/hash oracle |
| backend full | **1,315 tests / 1,540 subtests PASS**, failure/error 0, exit 0 |
| analyze / debug APK build | PASS / PASS; 설치 없음 |
| 변경 Dart 7파일·새 감사 4파일 format | PASS; 전체 format의 기존 10파일 차이 보존 |
| Ruff / compileall / diff check | PASS / PASS / PASS; 새 감사 Python도 검사 |
| frontend test/build / script safety | 21 PASS / PASS / 27 PASS |
| 원 monetary diagnostic | 3 PASS / 2 superseded assertion FAIL; 역사적 결과로 구분 |
| 원 P0 Python | 4 PASS / 1 Git baseline fixture FAIL; compatible replay 별도 PASS |
| target/historical SHA | 교정 29파일과 보호한 역사적 44파일 모두 최초와 동일; 제품 diff 없음 |'''
    findings = ('확인된 새 CRITICAL/HIGH/MEDIUM/LOW correctness finding은 **0**이다. '
                '미해결 correction blocker는 **0**이다. 원 RA01은 missing-required provenance를 성공으로 '
                '전달하지 않으며 정상 source 실패와 성공의 durable postconditions를 실제 DB/fresh process로 검증했다.')
    closure = ('**E4-A01: CLOSED. E4-RA01: CLOSED.** 원 stale-race 및 세 predecessor 반례를 변경 없이 재실행했고, '
               '직접 영향받는 source/SQL writer fence, current AppState/session, 정상 첫 설치, failed/committed recovery, '
               'Frozen/pending/lineage 및 incremental-cost 경계를 독립 검증했다.\n\n'
               '**PASS — E4-RA01 INDEPENDENT TARGETED RE-AUDIT COMPLETE**다. 원 Phase A FAIL과 이전 targeted FAIL은 '
               '역사적으로 그대로 남는다. 이 문서는 두 blocker에 대한 새로운 closure 결정이다.')
    phase = ('**PHASE A BLOCKER CLOSURE: PASS. SAFE TO START T6.6F PHASE B: YES.**\n\n'
             '최초 Phase A의 다른 PASS는 audited code/가정이 그대로 유지된 범위에서만 이어받는다. 교정된 세 제품 파일과 '
             '직접 영향 경로는 이번에 새로 검토했고 필수 회귀가 완료됐다. 다른 미해결 Phase A blocker는 발견되지 않았다. '
             '따라서 binding stage gate에 따라 Phase A를 progression 가능한 상태로 해제한다.\n\n'
             '**Phase B는 NOT STARTED**다. Phase A closure를 integrated Phase B PASS, R1 완료, 일반 사용자 '
             'segmented Offline 준비 또는 배포 승인으로 확대하지 않는다. Phase B는 별도 명시 호출이 필요하다.')
    fields = [
        ('T6.6E4-RA01 INDEPENDENT TARGETED RE-AUDIT', 'PASS'),
        ('FAILED PREVIOUS RE-AUDIT COMMIT', '5ad7bc8003e3799da63a912b700432bc48aa6471'),
        ('AUDITED CORRECTION COMMIT', 'af9525e20e6df1dd7dfc152d3db79c1eb07925d2'),
        ('AUDIT-ONLY COMMIT', '이 보고서를 처음 추가한 commit; §34 Git 명령과 최종 응답으로 식별'),
        ('REPOSITORY STATE', 'VERIFIED'), ('CORRECTION DIFF REVIEW', 'COMPLETE'),
        ('ORIGINAL THREE RA01 FAILURES', '3 PASS\n0 FAIL'), ('RA01 ROOT CAUSE', 'CONFIRMED'),
        ('PREVIOUS_SOURCE CONTRACT', 'PASS'), ('LEGITIMATE INITIAL INSTALLATION', 'PASS'),
        ('MISSING REQUIRED PREVIOUS_SOURCE', 'REJECTED'), ('INVALID PREVIOUS_SOURCE', 'REJECTED'),
        ('STALE PREVIOUS_SOURCE', 'REJECTED'), ('SAME-SOURCE DIFFERENT-OPERATION', 'PASS'),
        ('NATIVE INSTALL SUCCESS POSTCONDITIONS', 'PASS'), ('FAILED INSTALL SOURCE PRESERVATION', 'PASS'),
        ('FRESH-PROCESS FROZEN-B READ', 'PASS — 정상 source의 실패/성공·retained association; 사전 손상된 legacy 반례는 §05'),
        ('SOURCE/LINEAGE CONSISTENCY', 'PASS'), ('SOURCE OWNERSHIP FENCE', 'PASS'),
        ('SQL OWNERSHIP FENCE', 'PASS'), ('CHECK-TO-MUTATION ATOMICITY', 'PASS'),
        ('E4-A01 STALE RECOVERY REGRESSION', 'PASS'), ('CONCURRENT INSTALL/RECOVERY', 'PASS'),
        ('LEGITIMATE RECOVERY', 'PASS'), ('RECOVERY IDEMPOTENCE', 'PASS'),
        ('CROSS-STORE CRASH CONSISTENCY', 'PASS'), ('FROZEN PIN RETENTION', 'PASS'),
        ('IMMUTABLE OBJECT RETENTION', 'PASS'), ('PENDING B/J DURABILITY', 'PASS'),
        ('UNAUTHORIZED PENDING RETIREMENT', 'NONE'), ('ORIGINAL APPSTATE TICKET', 'PRESERVED'),
        ('AUTHORITY/SESSION GUARDS', 'PASS'), ('T01 REGRESSION', 'PASS'), ('T02 REGRESSION', 'PASS'),
        ('T03 REGRESSION', 'PASS'), ('E4-P0 MONETARY REGRESSION', 'PASS'), ('E3 I25 COST', 'PRESERVED'),
        ('FROZEN-B REPEATED READ COST', 'PASS'), ('INDEPENDENT SQL/OBJECT COUNTERS', 'PASS'),
        ('HISTORICAL DIAGNOSTIC CLASSIFICATION', 'COMPLETE'),
        ('NEW INDEPENDENT AUDIT CASES', '29 PASS\n0 FAIL\n0 INCONCLUSIVE'),
        ('EXISTING RA01 CORRECTION TESTS', '51 PASS\n0 FAIL'),
        ('ORIGINAL PHASE A AUDIT CASES', '45 PASS\n0 FAIL'),
        ('PREVIOUS E4-A01 CORRECTION TESTS', '28 PASS\n0 FAIL'),
        ('PREVIOUS TARGETED RE-AUDIT CASES', '20 PASS\n0 FAIL'),
        ('E4 AUTHORITY/RACE', '51 PASS\n0 FAIL'), ('E4 PROCESS CRASH', '36 PASS\n0 FAIL'),
        ('FULL FLUTTER TESTS', '1503 PASS\n0 FAIL\n2 SKIP'), ('FLUTTER ANALYZE', 'PASS'),
        ('FLUTTER BUILD', 'PASS'), ('CHANGED-FILE FORMATTING', 'PASS'),
        ('BACKEND REGRESSION', '1315 TESTS\n1540 SUBTESTS\nPASS'), ('RUFF', 'PASS'),
        ('COMPILEALL', 'PASS'), ('GIT DIFF CHECK', 'PASS'), ('SNAPSHOT V7', 'PRESERVED'),
        ('OFFLINE BASELINE V4', 'PRESERVED'), ('FROZEN B/J', 'PRESERVED'),
        ('SYNC_ROOT / V7 FINGERPRINT', 'SEPARATED'), ('R1 GENERAL-USER ACTIVATION GATE', 'CLOSED'),
        ('NEW CRITICAL', '0'), ('NEW HIGH', '0'), ('NEW MEDIUM', '0'), ('NEW LOW', '0'),
        ('UNRESOLVED CORRECTION BLOCKERS', '0'), ('E4-A01 FINDING', 'CLOSED'), ('E4-RA01 FINDING', 'CLOSED'),
        ('PHASE A BLOCKER CLOSURE', 'PASS'), ('SAFE TO START T6.6F PHASE B', 'YES'),
        ('T6.6F PHASE B', 'NOT STARTED'), ('SAFE TO START R1', 'NO — SEPARATE PREREQUISITES PENDING'),
        ('SAFE TO DEPLOY', 'NO'), ('FINAL VERDICT', 'PASS — E4-RA01 INDEPENDENT TARGETED RE-AUDIT COMPLETE'),
        ('NEXT ACTION', '별도 명시 호출로 T6.6F Phase B 통합 검증을 시작한다.'),
    ]
    footer = '```text\n' + '\n\n'.join(k + ':\n' + v for k, v in fields) + '\n```'
    source = REPORT.read_text()
    for key, replacement in [('__REGRESSION_TABLE__', table), ('__FINDINGS__', findings),
                             ('__CLOSURE__', closure), ('__PHASE_A__', phase), ('__FINAL_FOOTER__', footer)]:
        assert source.count(key) == 1, key
        source = source.replace(key, replacement)
    source = source.replace('최종 판정은 필수 회귀 완료 후 아래 집계·footer에서 확정한다.',
                            '**최종 판정: PASS — E4-RA01 INDEPENDENT TARGETED RE-AUDIT COMPLETE.**')
    REPORT.write_text(source)


if __name__ == '__main__':
    main()
