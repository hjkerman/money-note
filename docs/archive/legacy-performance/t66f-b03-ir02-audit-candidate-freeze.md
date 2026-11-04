# T6.6F-B03-IR02 감사 후보 동결·인계

**PASS — 승인된 IR01 source 후보의 동결·복원 검증 및 독립 세션 인계 준비 완료.**

이 결과는 snapshot 준비의 PASS다. B03 독립 정확성 재감사, IA01–IA07 폐쇄, IC01 완료,
Phase B 비용 준수나 production 승인은 수행하거나 선언하지 않았다.
IR02 사용자가 IR01 scoped B03 경계를 다음 독립 세션에 명시 승인했다. 같은 승인을 다시 요청하지 않는다.

## 1. 시작 상태와 승인 후보

저장소는 `/home/hjkerman/codex/money-note`, HEAD/main/origin/main/실제 remote main은
`ebcbd54d90eeee194a04b9eea6367f446ee2fd28`이었다. index SHA-256은
`d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`로 유지했다.
기존 dirty 상태를 허용했으며 staged0·unstaged tracked5와 관련 untracked136개를 보존했다.
생산/진단/test source·protocol·expected SHA·역사 보고서·SQLite evidence를 변경하지 않았다.

[IR01 source manifest](../../benchmarks/t66f-b03-ir01/candidate-source-manifest.json)의 actual entries는
819개 / 9,085,052B다. 문서화한 `JSON UTF8, sort_keys=True, ensure_ascii=False,
separators=(comma,colon)`의 entries digest를 다시 계산했다.

```text
IR01 PAYLOAD SHA-256:
645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8
```

모든 파일의 실제 내용·mode, base/index/worktree/untracked 구분이 일치했다. 차이는0개다.
[preflight.json](../../benchmarks/t66f-b03-ir02/preflight.json)에 signature와 current/historical lock 대조를 기록했다.
승인 baseline을 바꾸거나 source를 옛 버전으로 복구하지 않았다.

## 2. authoritative snapshot

활성 repository 밖에 하나의 authoritative archive를 보존했다.

```text
/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8/candidate.tar.gz

ARCHIVE SHA-256:
87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01

ARCHIVE BYTES:
2527708
```

payload digest는 source inventory identity다. archive digest는 gzip/TAR framing과 supplemental metadata까지
포함하므로 서로 다른 값이다. archive는 2,527,708B이며 대형 DB/build 사본이 아니다.

같은 디렉터리에 다음 파일이 있다.

- `snapshot-integrity.json`: 834개 archive member의 path/길이/mode/SHA와 source/base identity.
- `verify_snapshot.py`: original working-tree 파일을 읽지 않는 standalone verifier.
- `HANDOFF.md`: 새 구현 비관여 Codex XHigh 세션용 감사 인계.
- `SEAL.json`: 완료 표식·각 파일 digest·승인 범위·보호 한계.
- `SHA256SUMS`: archive·integrity·verifier·handoff·seal의 별도 checksum 목록.

경로·digest·file mode는 [snapshot.json](../../benchmarks/t66f-b03-ir02/snapshot.json)에 있다.

## 3. 포함·제외와 base 의존성

archive의 `source/`는 **IR01이 지정한819개 파일만** 담는다. 전체 working tree를 archive하지 않았다.
추가15개 `metadata/` 파일은 원 IR01 manifest/판정·oracles/계획, pinned base commit object,
이번 freeze provenance와 verifier다. candidate source 수는 여전히819개다.
mode·실행 비트, tracked content/mode override, staged/unstaged·untracked·deletion 상태를 보존했다.

선택된819개 source의 내용 검증은 **자체 완결**이다. snapshot만으로 파일·mode·payload를 검증할 수 있다.
**전체 checkout 재구성과 역사 Git 검사는 위 base commit 및 그 history를 요구한다.**
누락된 변경 없는 파일은 base에서 가져오며, original mutable working-tree 내용은 검증·복원의 입력이 아니다.

Flutter/Dart/Gradle/build cache, APK, SQLite/benchmark clone, 실제 credential/비밀설정 파일과 무관한 파일은
포함하지 않았다. 승인 tests의 synthetic token/placeholder source는 실제 운영 credential 파일과 구별했다.
source 경로는 directory FD의 `O_NOFOLLOW`로 열었고 모든 TAR member는 regular file이다.
symlink·hardlink·device·외부 경로 추적은 허용하지 않았다.

## 4. 일관성·source locks

복사 전 두 번의 내용 대조, 복사 중 열린 FD signature, 복사 후 전체 source/index/HEAD/Git 상태를 확인했다.
파일이 달라지면 BLOCKED하고 승인 digest를 갱신하지 않는 방식이다. 이번 source 차이는 없었다.
IR01 supplemental 문서도 복사 전후 SHA를 확인했다.

현재 exact lock6개와 historical inverse5개는 기존 review 값 및 pinned Git blob과 일치했다.
추출 verifier도 archive 안의 review/source만으로 current SHA와 historical inverse를 재검사했다.
이 PASS는 **동결 integrity/static source-lock 대조**이며, 다음 감사의 기존23 guard·현재6 guard·P0
fingerprint 동작 회귀를 대체하지 않는다. expected SHA나 승인 정책을 변경하지 않았다.

## 5. 두 가지 복원 검증

[archive-reconstruction.json](../../benchmarks/t66f-b03-ir02/archive-reconstruction.json):
원 repository 밖의 새 private 경로에서 standalone verifier를 실행했다. interpreter의 Python import
환경을 정리하고 source code/SQLite는 실행하지 않았다. 834개 member inventory/content/mode와
819 source·baseline commit object·payload·source locks가 일치했다.

[base-overlay-reconstruction.json](../../benchmarks/t66f-b03-ir02/base-overlay-reconstruction.json):
683개 selected tracked 파일을 pinned Git blob에서 만들고, archive의 captured content/mode와
untracked136개를 적용했다. 재구성819개 모두 같은 payload였다. live working-tree 파일 내용은 쓰지 않았다.

Git content 변경은5개지만 full POSIX mode 차이는682개다. 원 working files의 group-write 등 전체 mode와
Git의 normalized mode 차이도 보존하기 때문에 content/mode union override는682개다.
이는682개 금융/진단 알고리즘 변경이라는 뜻이 아니다. 실제 Git staged/unstaged 상태도 별도로 보존했다.
tracked deletion은0이며 `metadata/freeze.json`에 빈 deletion 목록을 명시했다.

## 6. 봉인과 독립 검증

archive·manifests·verifier·handoff·seal은0444, authoritative directory는0555로 봉인했다.
mutable source와 hardlink를 공유하지 않는다. 봉인 후 원 working tree 밖에서 verifier와
`sha256sum -c SHA256SUMS`를 다시 실행해 통과했다.
[sealed-verification.json](../../benchmarks/t66f-b03-ir02/sealed-verification.json)에 결과가 있다.

보호는 **read-only permissions + content-addressed archive + 별도 고정 SHA**다.
관리자/owner가 권한을 다시 바꿀 수 없는 hardware WORM이나 power-loss 보장은 주장하지 않는다.
그래서 새 verifier는 문서에 고정된 SHA를 먼저 확인하고, 바뀐 파일을 같은 후보로 받아들여서는 안 된다.

## 7. 새 독립 세션 handoff

정확한 handoff 경로:

```text
/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8/HANDOFF.md
```

[handoff.json](../../benchmarks/t66f-b03-ir02/handoff.json)은 문서와 archive digest를 함께 식별한다.
다음 세션은 **P05 및 IC01을 구현하지 않은 새 Codex XHigh 세션**이어야 한다.
원 findings/source/reproducers, independent native/literal oracles, SQL attempt/effective/commit/
rollback·savepoint·partial FAIL, hash/validation spans, generation attribution, 실제 HTTP/TLS→E1–E4,
async/native late completion·rejected dispatch·resource bounds, P02 cache lifecycle, P0/source guards,
최종 full regressions와 artifact hygiene를 인계했다. 기대값으로 구현 counter 자체를 쓰지 않는다.

다음 감사는 frozen source를 사용한다. 새 working-tree lib/test나 Python/Flutter package root를
자동 참조하지 않도록 별도 실행 tree를 구성하고 그 source를 전후 재검증해야 한다.
기존 historical defect-controls와 current-correctness 결과는 source 버전별로 구별하고 역사 evidence를 덮어쓰지 않는다.
correction이 필요하면 후보를 FAIL/보류하고 **새 candidate identity·새 freeze·영향 동작의 독립 재검증**으로 진행한다.
현재 archive를 수정하거나 기존 source-lock expected를 바꾸는 방식으로 통과시키지 않는다.

## 8. 이번에 승인된 경계와 남는 의무

IR02 Mission/§7의 명시 승인으로, 다음 독립 B03 correctness audit는 새 binding 증거가 없는 한
**성공한 모든-observer-ON N100k cold를 추가 B03-only 선행 조건으로 요구하지 않는다.**
정확성·coverage·isolation·resource safety·금융/authority 동등성 결함으로 FAIL할 권한은 그대로다.
이 준비 작업은 다음 감사 결과를 정하지 않는다.

아래는 보존한 미확인 의무다.

- §35 five-point fixed-H/D N cost grid와 실제 §36 I25 scaling.
- full-scale measurement feasibility 및 runtime perturbation characterization.
- Android memory/VFS/physical IO와 hardware power-loss.
- R1 large restore·activation 및 통합 exit·production 승인.

P03은 **HISTORICAL FAIL —397146/400532**, remaining3386,900초 세 관측 만료,
2699.957907초, E3/E4 미도달·partial snapshots다. 원 SQLite는 UNAVAILABLE이며 복구하지 않았다.
이번 full100k 실행은0회다. P05의 소형 handoff PASS를 원 Target 복구나 독립 correctness PASS로 바꾸지 않았다.
B03 audit는 OPEN, Phase B는 INCONCLUSIVE, R1 activation은 CLOSED, deployment는 NOT AUTHORIZED다.

## 9. artifact hygiene와 능동 repository 보존

검증용 추출834개와 base-overlay819개, 합 **1653개 파일**을 일관된 task-owned private root에 만들었다.
권위 있는 archive의 검증 후 모든 verifier/Git child 종료·descriptor 사용0을 확인하고 정확한 파일과
빈 owned directory를 정리했다. 검증 root가 제거됐음을 확인했다.
[cleanup-manifest.json](../../benchmarks/t66f-b03-ir02/cleanup-manifest.json)은 매 path/inode/size/할당량과 결과를 기록한다.
삭제된 파일 할당량은 **22,806,528B**, 관측 available 증가는 **23,535,616B**다.
filesystem metadata·동시 호스트 쓰기로 두 수치가 다를 수 있다. 기존 파일 삭제는0개다.

archive와 검증에 필요한 작은 metadata만 보존했다. 새 다중 GiB backup/build/DB는 없다.
full Flutter build·N100k sync·backend/Flutter 기능 재감사·R1·배포·APK 설치는 수행하지 않았다.
이번 실행의 검증은 snapshot integrity와 재구성에 한정한다.

## 10. 최종 결과와 다음 행동

IR01 승인 payload와 현재 source는 일치하고, snapshot 재구성·inventory·locks·cleanup은 PASS다.
기존 source/index/dirty work와 historical evidence는 보존했다. commit/push는 없다.
최종 보존 대조와 저장 공간은 [final-state.json](../../benchmarks/t66f-b03-ir02/final-state.json)에 기록한다.

**새 구현 비관여 Codex XHigh 세션에서 sealed HANDOFF를 읽고, 동결 후보의 scoped B03 독립 정확성 재감사를 수행한다.**

## 필수 최종 상태

```text
T6.6F-B03-IR02 CANDIDATE FREEZE:
PASS

HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

GIT INDEX:
PRESERVED

EXISTING UNCOMMITTED WORK:
PRESERVED

IR01 CANDIDATE FILES:
819

IR01 PAYLOAD SHA-256:
645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8

CURRENT PAYLOAD MATCH:
PASS

IMMUTABLE SNAPSHOT:
/home/hjkerman/codex/audit-candidates/money-note/t66f-b03/645fd4d883cecbf617d7d9c8e1a771efe9a9e88fac4b3ae646337adfb6b582b8/candidate.tar.gz

SNAPSHOT SHA-256:
87b1e68975ce1c0682f7b7954d322734181aeb56dae1c123a29767132f266d01

SNAPSHOT RECONSTRUCTION:
PASS

SNAPSHOT SOURCE INVENTORY:
PASS

SOURCE LOCKS:
PASS — 동결 integrity/static 대조; 기능 재감사 아님

INDEPENDENT AUDIT HANDOFF:
READY

SCOPED B03 AUDIT:
AUTHORIZED FOR NEXT INDEPENDENT SESSION

PHASE B FIVE-POINT GRID:
NOT VERIFIED

E3 I25 SCALING:
NOT VERIFIED

P03 FULL 100K COLD:
HISTORICAL FAIL — NOT REPEATED

NEW FULL 100K COLD RUNS:
0

PRODUCT SOURCE CHANGES:
NONE

GIT INDEX CHANGES:
NONE

COMMIT:
NONE

PUSH:
NOT PERFORMED

TEMPORARY ARTIFACT CLEANUP:
COMPLETE

B03 INDEPENDENT AUDIT:
OPEN

FINAL VERDICT:
PASS

NEXT ACTION:
새 구현 비관여 Codex XHigh 세션에서 sealed HANDOFF를 읽고 동결 후보의 scoped B03 독립 정확성 재감사를 수행한다.
```
