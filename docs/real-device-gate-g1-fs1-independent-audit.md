# Money Note — G1-FS1 독립 보안·정확성 감사

**PASS — FS1 INDEPENDENTLY VERIFIED**

2026-10-29, 새 독립 Codex 감사 세션. 구현·명세·기존 fixture 작성에 참여하지 않았다. 이번 권한은 소스 검토, 안전한 host-only 검사와 감사 문서 작성에 한정했다. 구현 코드, 규범, 기존 시험·증거, source lock은 수정하지 않았다. 소유자 승인·G1 기술 proof 수용·기기 실행 권한을 발급하지 않았다.

FS1은 유효 기술 명세에 부합하며, 검토한 기존 안전 경계는 보존됐다. 새 blocking/nonblocking finding은 **0건**이다. 이 PASS는 **FS1 구현의 독립 감사만 종결**한다. G1 mandatory technical proof는 계속 **0/12 수용**, 원 F01은 **BINDING — UNRESOLVED**, 운영 ADB dispatch는 **BLOCKED**다.

**권위와 후보 신원**

테스트 전에 실제 파일 bytes와 적용 권위를 확인했다. AGENTS.md, 개발 산출물 위생, project-state/domain-model/known-issues, architecture의 서버 authority·클라이언트 신뢰 경계, 원 PREP01 물리 기기 계약, PREP09 독립 감사·F01 결정, 후속 G1 문서 적용·주석 검토, P01, FS1 명세와 인계 자료를 대조했다. 상위 B §27/29 및 C §26/34/34-B11/35/35-T69/38의 단계·보존·실기기 요구도 유지한다.

| 감사 대상 | 실제 SHA-256 |
| --- | --- |
| 유효 G1 계약 | `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0` |
| FS1 technical spec | `2ae1c27bdd6c72664190063c507b2820f1c7a3a40eba7b8d3fcfb9a6322adfda` |
| 고정 test-vectors.json | `68199f4f55f9467fb1906256ed5df0c6ae1ce8eb75ab5782984f9f468e30da59` |
| trusted-test-digests.json | `4e2db7f21ea92e02b21d923eb9687fdff2de77b48cb54d02769542eb575f5c9a` |
| 현재 guards.py | `005be5c2d9f55ecde81e93dbf626e62bbb0e61b45d1984b88f5d5dc094fe79a7` |
| 현재 test_safety.py | `a943a150bcc528b6cb0a2479933d57b5fa8c62bdf8fec43c91b04749ae1d6ead` |
| 불변 dispatch.py | `63af7b01dedec4242b990bffed1a5c81b241d5fe8728c04ef3a4ce65b8d08293` |
| 불변 smoke.py | `36dde3d1407703048e79dbb20e8764e9b7d28c5c8804611d9d45142541669a10` |

N3/N4/N5 완료 사건 `G1-N3-N4-N5-DOCUMENT-APPLICATION-COMPLETE-01`의 직접 참조 해시를 대조했다. 현재 계약의 상태 주석 한 행을 제거하면 과거 승인본 `967e6b07…` bytes가 정확히 복구된다. S7의 12개 고정 참조와 FS1 handoff의 6개 자료 pin을 포함해 37개 해시 검사를 독립 수행했다. 과거 후보의 미적용 문구나 O2 대체 제안을 현행 계약보다 우선하지 않았다. [권위·소스 검사](benchmarks/real-device-gate-g1-fs1-independent-audit/source-and-authority-verification.json).

**구현의 명세 대조**

| 검토 영역 | 소스 위치 | 독립 판단 |
| --- | --- | --- |
| 입력·오류 선행순서 | [guards.py:352](../scripts/devicegate/guards.py:352) | expected exact str/hex64 → raw exact bytes → 1..65,536 bytes → strict UTF-8/BOM → quote/escape를 구별하는 depth scan 순서를 준수한다. depth17은 parse 전에 거부한다. |
| JSON 문법·숫자·중복 | [guards.py:367](../scripts/devicegate/guards.py:367) | decoded key 중복을 모든 object에서 수집한다. 문법 오류가 먼저, 그다음 duplicate, numeric profile 위반이다. 음수/-0/float/exponent/nonfinite/31-bit 초과를 schema 진입 전에 거부한다. 긴 정수는 무제한 int 변환을 하지 않는다. |
| Schema·required/type | [guards.py:389](../scripts/devicegate/guards.py:389) | root 37개, build 3개, action 14개의 정확한 key 집합과 version/profile 상수를 검사한다. unknown/null/missing/빈 값·bool/int 혼동을 명세에 맞게 거부한다. input_bytes=0의 input_hex 빈 문자열만 허용한다. 강제 변환·기본값 보충이 없다. |
| Generation slots | [guards.py:412](../scripts/devicegate/guards.py:412) | 지정 8개 식별자와 순서가 정확히 일치해야 한다. 재정렬·추가·중복·live handle object가 허용되지 않는다. 실제 resource 세대나 identity proof를 생성하지 않는다. |
| 경로 | [guards.py:413](../scripts/devicegate/guards.py:413) | 전체 192/segment64 제한, lowercase ASCII segment 문법, app/host prefix, 정렬·유일성과 host=plan_id 관계를 검사한다. slash 외 구분자, 절대/traversal/빈 segment/percent/Unicode/control/NUL 등을 보정 없이 거부한다. |
| Actions | [guards.py:417](../scripts/devicegate/guards.py:417) | 1..32개, 4개 kind, ordinal 정확히 1..N, 유일 id, literal argv/profile·component/effect/bookkeeping, input hex/bytes/hash, attempts/evidence_count exact int1, timeout을 검사한다. 종류열은 정확히 R(?:IL)?C*다. |
| 교차 관계 | [guards.py:438](../scripts/devicegate/guards.py:438) | 시간 관계 → argv 목록 → sorted unique path 집합 → input byte 합의 순서를 준수한다. unsupported kind·callback/env/권한 필드를 통한 실행 의미 주입을 거부한다. |
| Canonical·digest | [guards.py:443](../scripts/devicegate/guards.py:443) | 전체 raw canonical equality → 내부 plan hash → 별도 외부 raw hash 순서다. 공백·key 재정렬·동등 escape·Unicode/path 정규화를 수용 경로로 사용하지 않는다. |
| 실패와 반환 | [guards.py:355](../scripts/devicegate/guards.py:355) | 정상 입력 거부는 데이터 없는 정확한 ValueError(code)다. 성공은 immutable `(bytes, str, str)` tuple이다. mutable parsed object·ALLOW·token·receipt·권한 상태가 없다. |

정적 대조는 각 필드의 타입·상수·범위와 검사 순서를 포함했다. 모든 필드 조합을 동적으로 전수 검사했다는 주장은 하지 않는다. 유효 schema의 container depth는 최대4다. depth16의 schema-invalid 자료가 parse 후 필드 단계에서 거부되는 것과 depth17이 자원 한도로 거부되는 것을 구별했다.

경로 검증은 문자열 검증이다. 파일 존재·symlink·mount·root confinement·교체 race를 입증하지 않으며 open/stat/resolve/readlink를 호출하지 않는다. 이 구현과 호출 경로에서 문자열 통과를 filesystem/OS confinement으로 승격하는 사용은 발견되지 않았다.

**Digest와 외부 신뢰 입력**

독립 재계산에서 내부 대상은 **top-level plan_sha256 한 key만 제거한 P의 C(P)**, 외부 대상은 **내부 digest를 포함한 전체 M의 raw=C(M)**였다. 구현의 json.dumps를 재사용하지 않는 직접 ASCII serializer로 V01/V02의 byte 순서·정수 표현·array 순서·마지막 LF 부재 및 SHA-256을 대조했다.

V01 내부 plan digest는 `9b0958df67bad593c2ce913f5037928c53466938bcafefe0f664322dd29b43ad`, 별도 전체 manifest pin은 `dc5b55685ed5f6a21e89b84c4ce8e4fb366f83a4accd51e72c0b1074c74688e2`이며 raw는 2,436 bytes다. 두 digest를 같은 것으로 취급하지 않는다.

[guards.py:361](../scripts/devicegate/guards.py:361)은 expected 인자를 먼저 요구하고 [guards.py:446](../scripts/devicegate/guards.py:446)에서 실제 전체 raw hash와 비교한다. 누락·None·타입/hex 오류는 검사 생략으로 처리되지 않는다. manifest에 expected를 추가하면 unknown field다. 내부 digest를 외부 expected로 전달하면 거부된다. 내부 내용을 재해시해도 기존 외부 pin을 유지한 V24는 `FS1_EXPECTED_DIGEST_MISMATCH`다.

실제 존재하는 호출자는 시험 코드뿐이다. [test_safety.py:83](../scripts/devicegate/test_safety.py:83)은 고정 경로 catalogue의 hash를 신뢰 시험 소스의 literal로 검증하고, corpus의 expected 사본과 별도로 catalogue 값을 전달한다. manifest/raw가 catalogue 위치나 source pin을 선택하지 못한다. 새 운영 caller·승인 registry·`validator_pass` 권한 분기는 없다.

순수 함수는 caller가 준 expected의 provenance를 인증하지 않는다. 사전에 신뢰·동결한 외부 pin이라는 custody는 명시적 caller 전제이며 함수 주석과 명세가 유지한다. SHA 일관성은 owner 승인, 실제 artifact 대응, physical-device identity, 원 F01 binding 또는 mutation authorization의 증거가 아니다.

**독립 적대적 검증**

작성자의 결과를 재인용하는 데 그치지 않았다. 별도 [감사 harness](benchmarks/real-device-gate-g1-fs1-independent-audit/audit-host.py)에서 고정 corpus와 catalogue의 pin을 먼저 검증하고, 전체 raw bytes와 별도 expected를 메모리에 준비해 validator를 직접 호출했다. 작성자의 fixture/outcome/no_sinks helper를 사용하지 않았다. 추가 사례는 이번 감사 지시가 허용한 독립 시험이며 구현자의 동결 24개 corpus를 바꾸지 않았다.

추가 입력은 48개로 고정했고 전체 bytes·정확한 기대 code·실제 결과를 [독립 결과](benchmarks/real-device-gate-g1-fs1-independent-audit/independent-host-results.json)에 보존했다. 무작위 탐색·자동 retry·candidate 수정은 없다. 변조 입력에 맞춰 trusted expected를 새로 계산하지 않았으며, 기존 baseline pin을 유지했다. 내부-as-외부 및 malformed/missing expected는 명시적인 음성 통제다.

| 독립 사례 | 관측 |
| --- | --- |
| A01–A04 | build/action의 escaped decoded duplicate, duplicate와 NaN 동시 위반, 문법 오류 우선순위가 정확했다. |
| A05–A12 | 6,000자리 숫자의 controlled 거부, depth16/17, 문자열 내부 bracket/escaped quote, UTF-8/BOM, empty/65,537-byte 입력에서 기대 code를 냈다. |
| A13–A21 | mutable raw, bool version, -0/float/-Infinity/overflow, nested authorization·action callback·root env 주입을 거부했다. |
| A22–A29 | null argv, bool/중복/건너뜀/역순 ordinal, install 없는 launch, slot 재정렬·handle object를 거부했다. |
| A30–A40 | percent traversal, backslash, Unicode slash/fullwidth dot/NFD/lone surrogate, NUL, 반복 slash, leaf 부재, segment65/전체193 길이를 거부했다. |
| A41–A48 | 동등 ASCII escape, 내부 digest를 외부 pin으로 사용, missing/prefixed expected, bool input_bytes·attempts·budget 및 hex-size 불일치를 거부했다. |

반복 호출·실패 뒤 정상 호출, 외부 mutable 객체/bytearray 변경, bytes/str subclass의 비평가, tuple/bytes 불변성도 독립 확인했다. guards 모듈과 함수 상태는 변하지 않았고 예상 밖 예외는 관측되지 않았다. 기존 H02에서는 두 parser 호출의 concurrency/reentrancy도 통과했다.

**Purity·회귀·제외 범위**

validator의 전체 AST와 호출을 검토했다. 추가 코드는 함수 정의 하나이며 runtime import나 문서/정책 파일 읽기가 없다. 허용된 bytes/str·JSON·regex·정수·SHA 연산만 사용한다. action 실행, 동적 import/eval/exec, subprocess/ADB, network, filesystem/device 변경, 환경·clock·USB 조회, 외부 callback, 전역 authority 상태 변경 경로가 없다.

독립 호출 중 process/network/file/environment/clock 진입점을 실패시키는 guard와 별도 Python audit hook을 무장했다. process/network 호출이 가능한 기존 시험도 실행 전에 전체 함수·선택 경로·adapter를 읽었고, 추가 외부 process/network guard 아래 명시적으로 선택했다. 시험 setup의 fixture 읽기와 감사 증거 쓰기는 validator 호출 전후에만 수행했다.

| 이번 실행 | 결과 |
| --- | --- |
| 독립 fixed specification vectors | **24/24** |
| 추가 독립 adversarial 입력 | **48/48** |
| 기존 FS1ManifestTest 재실행 | **27/27**: 같은 24개 벡터 replay + H01/H02/H04 3개; H03 sink 감시는 호출마다 적용 |
| 기존 BoundaryTests 명시 선택 | **26/26**, 세부 denial 관측87건, process/network 생성 시도0 |
| 기존 SafetyTest 메모리 전용 4개 | **4/4** |
| npm run build | **exit 0**, task-owned frontend 사본과 기존 합성 JSON fixture |
| backend targeted regression | **72 passed + 44 subtests**, JUnit **116**, failure/error/skip0 |

고정 벡터의 독립 실행과 기존 FS1 replay를 서로 다른 48개 사양 벡터로 합산하지 않았다. 이 분모는 실행 건수이며 G1 proof 개수나 독립 보안 불변식 개수가 아니다. [선택·회귀 결과](benchmarks/real-device-gate-g1-fs1-independent-audit/reviewed-regression-results.json), [제품 검증 명령·결과](benchmarks/real-device-gate-g1-fs1-independent-audit/repository-validation.json), 압축 로그와 JUnit을 보존했다.

`test_diagnostic_authority_patch_cannot_enable_terminal_boundary`는 confinement 함수를 patch하므로 제외했다. `SafetyTest.test_cli_rejection_nonzero_before_harness`, 전체 PREP08 driver·legacy_worker/run_legacy_tests·PREP06 lifecycle·test_remediation의 network/APK/자식 실행 suites도 실행하지 않았다. suite discovery나 기기 driver main을 호출하지 않았다. 26개 선택 중 test-only synthetic adapter 거부 시험은 모든 입력이 거부되고 원 경계가 복원됨을 확인했으며 실제 자식을 만들지 않았다. 운영 dispatch/confinement를 여는 patch는 수행하지 않았다.

N01 host 자식 회수, F02 합성 HTTP/redirect, F03 APK 봉인/admission은 관련 기존 함수의 **bytes와 AST 보존** 및 PREP09 역사 증거 보존으로 비회귀를 판단했다. 해당 OS/network/APK 효과 시험 전체를 새로 실행했다고 주장하지 않는다. FC01은 중앙 거부 source 불변과 위26개 실행으로 확인했다. 기존 diagnostic alias·wrapper·환경 flag·합성 adapter가 운영 권한이 되는 경로는 추가되지 않았다.

**범위와 보존**

Git HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `refs/heads/main`이다. Git diff --stat의 기존 tracked 수정13개는 시작부터 있던 변경이다. devicegate 소스가 미추적 상태여서 HEAD diff만으로 FS1 범위를 판단하지 않고, 명세 작성 전 [보존 기준선](benchmarks/real-device-gate-g1-fs1-spec/preservation-before.json) 8,155개 경로와 실제 bytes/mode를 대조했다.

기존 경로 중 변경은 정확히 `scripts/devicegate/guards.py`와 `scripts/devicegate/test_safety.py` 두 개다. 신규 경로16개는 FS1 명세·시험 JSON·보존 자료이며 새 runtime 파일은0이다. 원 guards 전체14739 bytes와 기존 AST 노드 전부, 원 test_safety 전체3436 bytes를 독립 복원해 before hash와 대조했다. 추가는 guards98행/test117행, 합계215행으로 각100/140·전체240행 한도 안이다. [범위 비교](benchmarks/real-device-gate-g1-fs1-independent-audit/scope-comparison.json).

이번 감사 시작 시 고정한 기존 **8,171개 경로**, 외부 원 B03 frozen sidecar5개, source-lock 관련27개는 종료 대조에서 변경/누락0이다. Git index SHA는 `33779f92417c7e6f7ab927847236336e5ce84e89260a66777e44295b782c943b`, staged entries SHA는 `9edd6a43e183de8f084f6fff420204a5222ac4684b11b6592fca9675d4760e4f`로 전후 동일하다. [보존 결과](benchmarks/real-device-gate-g1-fs1-independent-audit/preservation-verification.json).

B03 동기화·E3 guard-to-COMMIT·금융 의미·Snapshot/Offline/pending/reconciliation, 이전 수용 자료와 source locks는 불변이다. guards 전체 파일의 새 hash를 과거 whole-module 수용 hash로 재기록하지 않았다. 기존 함수와 효과 경로에 대한 이번 변경 영향 검토만 새 후보에 귀속한다. ignored runtime/cache/production 전체를 전수 검사했다는 뜻은 아니다.

기본 shell sandbox는 bwrap loopback 초기화 오류로 명령 실행 전에 실패했다. 자동 검토를 거친 host shell로 저장소 읽기·감사 증거 작성·위 host 검증만 수행했으며 이를 G1 confinement 자격이나 실행 권한으로 사용하지 않았다. ADB는 help/version 포함0회, ADB server socket 요청0회, USB/physical-device 접근·열거0회, emulator 동작0회, APK 설치0회다. backend는 새 합성 임시 DB와 in-process TestClient를 사용했다. 운영 API/데이터·서비스·OS 정책 변경은0이다.

이번 소유 scratch·frontend 사본/build·합성 임시 자원은 검증과 증거 보존 뒤 소유 표식·활성 process 부재를 확인해 정리했다. 기존 파일/cache/DB는 삭제하지 않았다. 별도 py_compile이 만든 감사 전용 pyc도 제거했다. 크기와 보존 항목은 [artifact-cleanup.json](benchmarks/real-device-gate-g1-fs1-independent-audit/artifact-cleanup.json), 최종 산출물 신원은 [evidence-manifest.json](benchmarks/real-device-gate-g1-fs1-independent-audit/evidence-manifest.json)에 있다.

**Finding 처분과 수용의 한계**

새 finding register는 빈 배열이다. 따라서 새 finding ID·severity·trigger/reproducer·correction·FS1 blocking 여부를 부여할 항목은 없다. 방어 경계를 완화하거나 발견한 결함을 문서 수정으로 해소한 사례도 없다. 기존 HIGH 원 F01은 기존 ID·원 수용 기준 그대로 미해결이며 FS1이 해결한 것으로 분류하지 않았다.

**PASS — FS1 INDEPENDENTLY VERIFIED.** 구현은 완료된 FS1 명세에 부합하고 검토한 기존 보호는 보존됐다. 이 보고서는 mandatory G1 technical proof, CP/IP/POST, owner 연결/read-only·첫 mutation grant, 실제 Android/물리 기기 qualification을 수용하지 않는다. T6.9는 DEFERRED, R1은 CLOSED, production deployment는 NOT AUTHORIZED다. 구현·규범 변경, commit·push·배포는 수행하지 않았다.
