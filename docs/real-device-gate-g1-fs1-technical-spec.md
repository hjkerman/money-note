# G1-FS1-SPEC — 호스트 전용 manifest 검증기 기술 명세

**판정: READY — FS1 TECHNICAL SPEC COMPLETE.** 네 공백인 schema, action 모델, generation slot/경로, plan digest 결합을 모두 결정했다. 이 판정은 명세 준비 완료만 뜻한다. 이전에 별도 승인된 두 파일의 순수 FS1 구현은 아래 인계 범위 안에서 명세상 재개할 수 있다. 이번 턴에서는 구현하지 않았다.

P01의 설명은 구현자가 동일하게 해석할 wire schema·action kind·slot/path grammar·hash object를 충분히 고정하지 못했다. 사용자가 알린 구현 중단은 적절한 경계 준수이며, 이 문서는 그 네 공백만 보완한다. 역사 P01·FS1 보고서, 실행 코드, 유효 G1 계약은 수정하지 않는다. 원 F01은 **BINDING — UNRESOLVED**, 운영 ADB dispatch는 **BLOCKED**, G1 기술 proof 수용은 **0/12**다.

## 1. 권위·근거·호환성

유효 [G1 계약](real-device-gate-g1-safety-contract.md)의 실제 SHA-256은 지정값과 일치한다.

`679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0`

현 효력은 canonical 상태 주석과 N3/N5 완료 사건을 따른다. S7 고정 참조 12건도 bytes에서 재대조했다. 과거 O2 대체 제안은 현행 규범이 아니다. 원 F01 및 상위·G1 의무를 누적하며 등록/채널/OS 격리의 미입증 상태는 보존한다. [계약·소스 검증](benchmarks/real-device-gate-g1-fs1-spec/contract-and-source-verification.json).

AGENTS·개발 산출물 위생을 다시 읽고, 기존 세션에서 읽은 프로젝트 상태·도메인 모델·알려진 이슈·architecture 신뢰 경계가 P01 hash 그대로임을 확인했다. 서버 금융 authority·B03·Snapshot/Offline·기기 및 운영 경계는 변경하지 않는다. [P01 FS1 설명](real-device-gate-g1-p01-technical-proof-plan.md:709), [당시 첫 범위 JSON](benchmarks/real-device-gate-g1-p01/first-host-only-slice.json), `guards.py`와 `test_safety.py`를 현재 bytes로 확인했다.

| 구분 | 실제 근거와 처리 |
| --- | --- |
| 이미 구현된 동작 | `guards.py`의 APK/HTTP/자식 감독과 `test_safety.py`의 기존 5개 SafetyTest. 두 파일 hash는 P01 당시와 동일하다. FS1 validator·caller·생산자는 관련 소스 검색에서 발견되지 않았다. |
| 기존 manifest 생산/소비 | `smoke.save`의 context/command/APK검증/결과 JSON과 `apk-policy.json`의 schema_version1·manifest/xml은 각각 다른 형식이다. FS1 입력으로 자동 수용/변환하지 않는다. |
| P01에 있던 요구 | 합성 PLAN_ONLY·NOT_GRANTED·NOT_ACCEPTED, 실제 실행 없음, 순수 bytes 검증, 원 29개 freeze 필드 이름, 64KiB/depth16/action32·24개 고정 검사·두 파일 한도다. |
| G1이 부과하는 요구 | 별도 owner grant·CP/IP/POST 분리, 고정 argv/input/path/order/budget, 개인정보/production 금지, 원 F01·자원 결합·단방향 폐기·OS 집행·독립 수용이다. |
| 이번 새 engineering 결정 | version/profile·37/14개 필드의 타입/const/구조, 4개 모델 kind·ordinal1·slot 이름·path grammar, canonical ASCII JSON, 내부/외부 두 hash·API/거부 code다. G1 원문에 이미 있었던 규칙으로 주장하지 않는다. |

별도 FS1 중단의 로컬 보고서는 docs/scripts의 해당 이름 검색에서 발견되지 않았다. 사용자 진술을 중단 사건의 근거로 존중하며, 그 부재를 사건 부정이나 외부 세션 자료의 부재로 확대하지 않는다. 기존 FS1 wire 소비자와 충돌하는 변경은 발견되지 않았다. [소스 호환성](benchmarks/real-device-gate-g1-fs1-spec/source-compatibility.json).

이 명세는 **합성 PLAN_ONLY 자료 profile**이다. `fs1-model`은 예약한 비실행 모델 문자열이며 실제 프로그램이 아니다. install/launch kind도 모델 설명일 뿐 어떤 실행/설치 권한도 만들지 않는다. 실제 serial/USB/TCP/ADB argv·actual generation 값·owner grant를 이 형식으로 수용하지 않는다. 기존 executor와 연결하는 작업은 없다. 실제 기기용 형식/producer/consumer로 확장하려는 변경은 현재 FS1 밖에서 따로 판단해야 하며 이 명세가 그 권한을 발급하지 않는다.

## 2. Manifest schema

지원 wire 신원은 `manifest_type="G1_FS1_PLAN_ONLY"`, `schema_version=1` 하나뿐이다. `schema_version`은 JSON 정수1이며 bool·1.0·문자열"1"을 허용하지 않는다. [정확한 기계 schema](benchmarks/real-device-gate-g1-fs1-spec/manifest-schema.json)는 독립적인 필드 표다. 특정 JSON Schema 라이브러리나 미확인 기존 형식을 전제하지 않는다.

입력은 exact `bytes`와 별도 trusted expected digest다. JSON은 strict UTF-8, BOM 없음, 단일 object만 허용한다. raw 길이는 **1–65,536 bytes**, object/array container depth는 **최대16**이다. root object가 depth1, 하위 object/array 진입마다 +1, scalar는 +0이며 문자열 안 bracket은 세지 않는다. 유효 schema의 실제 최대 depth는4다. depth16은 parse 전 자원 상한이며 depth16 자료를 schema가 수용한다는 뜻이 아니다.

모든 JSON number token은 `0` 또는 `[1-9][0-9]*`이고 값이 `2,147,483,647` 이하여야 한다. `-0`을 포함한 음수, 소수점, exponent, NaN/Infinity는 어떤 필드에서도 거부한다. bool은 정수가 아니다. 이후 각 필드의 min/max/const를 적용한다. coercion·기본값 보충·trim·대소문자 변환은 없다.

아래 **37개 root key 전부 필수**이며 나머지는 금지다. `android_build_identity`와 action도 정확한 key 집합만 허용한다. 어느 object의 decoded key도 중복될 수 없다. 예를 들어 escape로 같은 key가 되는 경우도 중복이다. 모든 null은 금지다. 빈 문자열·빈 배열도 거부하며, 유일한 빈 문자열 예외는 `input_bytes=0`인 action의 `input_hex=""`다.

| Root 필드 | 정확한 타입·값·관계 |
| --- | --- |
| `schema_version` | integer; 정확한 값 `1` |
| `manifest_type` | string; 정확한 값 `G1_FS1_PLAN_ONLY` |
| `contract_sha256` | string; 정확한 값 `679a16e030b7c0044bc834e7ce8557298da5ad6fd1f3e9d8453a1fef5f8920d0` |
| `scope` | string; 정확한 값 `PLAN_ONLY` |
| `authority` | string; 정확한 값 `NOT_GRANTED` |
| `proof_state` | string; 정확한 값 `NOT_ACCEPTED` |
| `plan_id` | string; fullmatch `fs1-[a-z0-9]+(?:-[a-z0-9]+)*`; 최대 길이 `64` |
| `plan_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `executor_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `apk_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `source_manifest_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `adb_binary_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `test_signing_certificate_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `synthetic_fixture_sha256` | string; fullmatch `[0-9a-f]{64}` |
| `adb_version` | string; 정확한 값 `FS1-SYNTHETIC` |
| `exact_serial` | string; fullmatch `FS1-SYNTHETIC-[0-9]{2}` |
| `transport_kind` | string; 정확한 값 `SYNTHETIC` |
| `android_build_identity` | object; 정확한 하위 필드 api, abi, fingerprint |
| `test_application_id` | string; 정확한 값 `kr.re.hjkerman.money_note.devicegate` |
| `activity_component` | string; 정확한 값 `kr.re.hjkerman.money_note.devicegate/com.example.money_note_mobile.DeviceGateActivity` |
| `backend_origin` | string; 정확한 값 `http://10.0.2.2:18081` |
| `test_account_identity` | string; 정확한 값 `fs1-synthetic` |
| `allowed_argv_templates` | array; 최소 항목 `1`; 최대 항목 `32`; 교차 조건 `same ordered value as actions[*].argv; literal complete argv only; no template expansion`; 각 항목: array; 최소 항목 `3`; 최대 항목 `4`; 각 항목: string; 최소 길이 `1`; 최대 길이 `192` |
| `allowed_app_relative_paths` | array; 최소 항목 `1`; 최대 항목 `32`; 교차 조건 `sorted unique set of actions[*].relative_path`; 각 항목: string; 경로 규칙 `APP_PATH` |
| `host_evidence_directory` | string; 경로 규칙 `HOST_PATH`; 교차 조건 `exactly evidence/fs1/ + plan_id` |
| `owner_approval_reference` | string; 정확한 값 `NOT_GRANTED` |
| `independent_preflight_reference` | string; 정확한 값 `NOT_ACCEPTED` |
| `generation_slots` | array; 정확한 값 `["HOST_BOOT","HOST_PRINCIPAL","ADB_SERVER","CLIENT_CHANNEL","USB_INCARNATION","TRANSPORT","RECEIVER_BOOT","RECEIVER_ADBD"]` |
| `actions` | array; 최소 항목 `1`; 최대 항목 `32` |
| `total_time_seconds` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `per_step_time_seconds` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `shutdown_or_stop_grace_seconds` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `max_app_data_bytes` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `max_log_bytes` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `max_host_evidence_bytes` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `minimum_device_free_bytes` | integer; 최솟값 `1`; 최댓값 `2147483647` |
| `maximum_process_memory_bytes` | integer; 최솟값 `1`; 최댓값 `2147483647` |

`android_build_identity`는 정확히 `api:36`, `abi:"x86_64"`, `fingerprint:"fs1.synthetic.api36"` 세 필드다. 이는 합성 identity 상수이며 개인 phone의 관측값이 아니다. 여섯 artifact/source/signer/fixture hash는 내용 신원 선언의 64자리 lowercase hex다. parser가 파일을 읽어 실제 artifact와 대응을 입증하지 않는다.

원 PREP01/P01의 29개 frozen field 이름은 모두 root 필드로 보존했다. `allowed_argv_templates`는 역사 이름만 보존하며 여기서는 완성된 literal argv 배열 목록이다. 동적 template 확장은 금지다. `owner_approval_reference="NOT_GRANTED"`, `independent_preflight_reference="NOT_ACCEPTED"`는 합성 상태 표기이며 실제 receipt가 아니다. 실제 approved manifest 공란을 허용한 것이 아니다.

알 수 없는 key는 값이 안전해 보이더라도 거부한다. 예를 들어 token/grant/authorization/callback/shell/executable/env/retry, CP/IP/POST 집계값, actual resource handle/generation 값은 들어갈 수 없다. 성공 결과가 어느 권한 상태를 변경하지도 않는다.

Root 교차 관계는 다음 순서로 검사한다.

1. `shutdown_or_stop_grace_seconds <= per_step_time_seconds <= total_time_seconds`.
2. `allowed_argv_templates`가 action 순서의 `argv` 목록과 값/순서가 정확히 같음.
3. `allowed_app_relative_paths`가 action 상대 경로의 sorted unique 집합과 정확히 같음.
4. action `input_bytes` 합이 `max_app_data_bytes` 이하임.

`host_evidence_directory`의 정확한 값은 아래 경로 단계에서 먼저 검사한다. 시간/용량 숫자는 합성 계획 자료이며 실제 deadline·disk reserve·장치 상태를 강제하거나 owner 예산을 승인하지 않는다.

## 3. Action 모델

`actions`는 1–32개의 object 배열이다. 각 object에는 아래 **14개 key 전부**가 있어야 하며 다른 key는 금지다. array 위치가 곧 순서이고 ordinal은 **1부터 N까지 공백·중복·역순 없이 정확히 연속**한다. id는 fullmatch `[a-z][a-z0-9_-]{0,31}`이며 전체 action에서 유일하다.

| Action 필드 | 정확한 타입·값·관계 |
| --- | --- |
| `id` | string; fullmatch `[a-z][a-z0-9_-]{0,31}` |
| `kind` | string; 허용값 `["REGISTER_READONLY","INSTALL_TEST_APK","LAUNCH_TEST_APP","COLLECT_TEST_RESULT"]` |
| `ordinal` | integer; 교차 조건 `exactly 1 + zero-based array index` |
| `argv` | array; 교차 조건 `exact literal list in action_profile, no substitution`; 각 항목: string |
| `input_hex` | string; fullmatch `(?:[0-9a-f]{2}){0,1024}` |
| `input_sha256` | string; fullmatch `[0-9a-f]{64}`; 교차 조건 `SHA-256 of hex-decoded input_hex, lower-case hex` |
| `input_bytes` | integer; 최솟값 `0`; 최댓값 `1024`; 교차 조건 `len(input_hex)/2` |
| `component` | string; 정확한 값 `kr.re.hjkerman.money_note.devicegate/com.example.money_note_mobile.DeviceGateActivity` |
| `relative_path` | string; 경로 규칙 `APP_PATH` |
| `effect` | string; 교차 조건 `exact action_profile effect` |
| `os_bookkeeping` | array; 교차 조건 `exact action_profile os_bookkeeping` |
| `evidence_count` | integer; 정확한 값 `1` |
| `timeout_seconds` | integer; 최솟값 `1`; 최댓값 `2147483647`; 교차 조건 `<= per_step_time_seconds` |
| `attempts` | integer; 정확한 값 `1` |

| Kind | 완성된 literal argv와 고정 효과 자료 |
| --- | --- |
| `REGISTER_READONLY` (R) | `["fs1-model","register", exact_serial]`; effect=`MODEL_READONLY`; bookkeeping=`["NONE_MODEL"]` |
| `INSTALL_TEST_APK` (I) | `["fs1-model","install", test_application_id, apk_sha256]`; effect=`MODEL_TEST_INSTALL`; bookkeeping=`["PACKAGE_MANAGER_RECORD_MODEL"]` |
| `LAUNCH_TEST_APP` (L) | `["fs1-model","launch", activity_component, plan_id]`; effect=`MODEL_TEST_LAUNCH`; bookkeeping=`["APP_LIFECYCLE_MODEL"]` |
| `COLLECT_TEST_RESULT` (C) | `["fs1-model","collect", action.relative_path]`; effect=`MODEL_RESULT_READ`; bookkeeping=`["NONE_MODEL"]` |

위 표의 이름 참조는 검증 비교식만 뜻한다. 실제 입력 argv는 이미 완성된 문자열 배열이어야 하며 object·placeholder·slot 치환 문법을 받지 않는다.

종류열은 정확히 `R(?:IL)?C*`다. R 하나로 시작하고, 선택적으로 I/L 쌍을 한 번 넣은 뒤 C만 둘 수 있다. R 단독/R+C는 등록 결과를 모델링한다. I 또는 L의 단독 삽입·뒤늦은 R·두 번째 설치/launch는 불가다. 모든 action의 `attempts`와 `evidence_count`는 exact int1, `timeout_seconds`는 양의 정수이면서 root의 `per_step_time_seconds` 이하다.

`input_hex`는 lowercase 두 hex 문자씩 0–1,024 byte를 나타낸다. `input_bytes=len(input_hex)/2`, `input_sha256=SHA256(hex-decoded bytes)`가 맞아야 한다. empty bytes의 hash는 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`다. 이 bytes는 opaque 모델 payload이며 실행/해석하지 않는다. artifact APK와 실제 wire install input의 일치나 안전성까지 입증한 것으로 간주하지 않는다.

금지 능력은 모든 실제 subprocess/ADB/USB/Android·파일/네트워크·OS 정책 접근, grant/receipt 발급, shell/interpreter wrapper, 실제 install/launch, root/reset/reboot/bootloader·clear/uninstall, 개인/공유/production 경로 접근, runtime 명령 생성·fallback·retry다. 모델 kind 이름의 수용은 이 금지를 해제하지 않는다. 새로운 mutation capability나 규범 변경을 요구하는 선택은 이번 명세에 포함하지 않았다.

## 4. Generation slot과 경로

`generation_slots`는 다음 **정확한 순서의 8개 문자열 배열**이다. 누락·중복·재정렬·추가·값 object/handle은 모두 거부한다.

`["HOST_BOOT","HOST_PRINCIPAL","ADB_SERVER","CLIENT_CHANNEL","USB_INCARNATION","TRANSPORT","RECEIVER_BOOT","RECEIVER_ADBD"]`

이는 미래 resource 종류를 식별하는 신규 engineering 이름이다. 실제 U*/S*/C*/T*/R*나 그 세대 값은 담지 않는다. 미리 개인 기기에 연결해 값을 채우도록 요구하지 않고, owner/신원·계획 공란을 나중에 보충하는 통로로도 쓰지 않는다. slot을 argv·경로·input에 치환하지 않는다. 단순 문자열은 G1-04의 actual resource handle이나 F01 binding proof가 아니다.

모든 경로는 다음 공통 규칙을 만족해야 한다.

- ASCII lowercase, 전체 1–192 문자, 각 segment 1–64 문자, `/`만 separator.
- 각 segment fullmatch는 `[a-z0-9_-]+(?:\.[a-z0-9_-]+)*`다. 빈 segment·`.`·`..`·반복 dot·leading/trailing slash는 허용하지 않는다.
- backslash·colon·percent·control/NUL·공백·non-ASCII·quote·wildcard·shell metacharacter는 금지다. Windows drive/UNC·POSIX 절대 경로·percent-encoded traversal도 통과할 수 없다.
- `allowed_app_relative_paths`와 action path는 `files/fs1/` 뒤 최소 한 segment가 있어야 한다. root 배열은 ASCII 오름차순·중복 없음이다.
- `host_evidence_directory`는 정확히 `evidence/fs1/` + `plan_id`다. 실제 checkout 절대 경로를 지정하지 않는다.
- `normpath`, Unicode 정규화, URL decode, case fold, slash collapse, trim을 하지 않는다. 애매한 표현을 고쳐 수용하지 않는다.

이 검사는 **문자열 자료만** 검사한다. 파일이 없거나 symlink인지, mount/root 아래인지, 부모/파일 교체 race가 없는지 알 수 없다. symlink 선언 필드도 허용하지 않고 parser는 open/stat/resolve/readlink를 호출하지 않는다. 후속 실제 filesystem 소비자는 별도의 승인·자격 범위에서 신뢰 root/열린 자원·link/mount/교체 수명을 검증해야 한다. 경로 문자열 통과를 filesystem confinement 또는 OS 격리 proof로 주장할 수 없다.

## 5. Canonical 표현과 두 digest의 결합

두 digest의 대상은 다르다. 같은 값이어야 한다고 비교하지 않는다.

| 구분 | Hash 대상 bytes | 포함 여부 |
| --- | --- | --- |
| 내부 `plan_sha256` | `P = M`에서 **top-level plan_sha256 한 key만 제외**한 object의 `C(P)` | 자기 자신 제외 |
| 외부 `expected_manifest_sha256` 인자 | 내부 digest를 포함한 **전체 M**의 raw bytes=`C(M)` | 내부 plan_sha256 포함 |

`C`는 `FS1_ASCII_JSON_V1`이다. object key를 ASCII byte 순서로 정렬한다. object는 `{key:value,...}`, array는 원래 순서의 `[value,...]`, separator는 comma/colon이며 whitespace·BOM·LF를 추가하지 않는다. 유효 profile의 key/string은 quote/backslash/control/non-ASCII가 없으므로 double quote로 감싸되 escape 없이 그대로 쓴다. slash도 escape하지 않는다. 정수는 최소 무부호 10진수다. UTF-8로 encode하며 마지막 LF가 없다. 이 정의는 별도의 JCS/RFC canonicalizer 채택 주장이 아니다.

raw는 `C(M)`과 byte 단위로 같아야 한다. pretty JSON·key 순서 변경·leading/trailing whitespace·동등한 escape도 보정하지 않고 거부한다. 따라서 입력 bytes가 바뀌면 canonical 비교나 내부/외부 hash 비교에서 거부된다. hash는 SHA-256의 32 bytes를 prefix/separator/LF 없는 **64자리 lowercase ASCII hex**로 표현한다. uppercase/공백을 normalize하지 않는다.

비순환 작성 순서는 P 확정 → `h_plan=SHA256(C(P))` → M에 `plan_sha256=h_plan` 추가 → `raw=C(M)` → 전체 raw의 외부 hash를 별도 신뢰 경계에 고정이다. 검증 순서는 schema/관계 → raw canonical equality → 내부 h_plan 비교 → 외부 전체 raw hash 비교다.

외부 expected 인자는 **입력 M과 별도로 이미 신뢰·동결한 pin**에서 와야 한다. manifest의 plan_sha256, manifest가 제시한 expected/receipt/boolean, 입력이 고른 경로·환경·URL, 호출 직전 untrusted raw를 hash한 값은 신뢰 원천이 아니다. parser는 그 값을 스스로 취득하거나 그 출처를 암호 인증하지 않는다. 이 custody는 호출자의 명시적인 선행 조건이며, 현재 운영 caller/승인 registry를 새로 구현하지 않는다.

시험에서는 [별도 trusted catalogue](benchmarks/real-device-gate-g1-fs1-spec/trusted-test-digests.json)의 파일 hash를 신뢰된 test source에 literal로 pin하거나 그 24개 값을 코드 상수로 고정한다. raw corpus가 catalogue 위치/pin을 선택할 수 없다. `test-vectors.json`의 expected 사본을 자동 신뢰하지 않고, 입력을 변조한 뒤 expected를 다시 계산하지 않는다. 같은 catalogue를 위조하면서 신뢰 source pin까지 바꾸는 침해에 대한 OS 보증은 이 순수 검증기의 범위가 아니다.

내부 필드 누락은 exact key-set 오류, 내부 형식 오류는 `FS1_PLAN_DIGEST_FORMAT`, 내부 내용 불일치는 `FS1_PLAN_DIGEST_MISMATCH`다. 외부 인자 누락/None/빈 값/타입/hex 오류는 `FS1_EXPECTED_DIGEST_FORMAT`, 잘못된 유효 hex pin은 `FS1_EXPECTED_DIGEST_MISMATCH`다. 내부 내용을 재해시해 일관되게 바꿔도 고정 외부 pin과 다르면 거부한다. [정확한 algorithm·API·우선순위](benchmarks/real-device-gate-g1-fs1-spec/canonicalization-and-digest.json).

기준 입력의 실제 계산값은 다음과 같다.

- 내부 plan SHA-256: `9b0958df67bad593c2ce913f5037928c53466938bcafefe0f664322dd29b43ad`
- 별도 전체 manifest pin: `dc5b55685ed5f6a21e89b84c4ce8e4fb366f83a4accd51e72c0b1074c74688e2`
- raw 길이: `2436` bytes. [전체 canonical 기준 입력](benchmarks/real-device-gate-g1-fs1-spec/baseline-manifest.json)은 LF 없는 실제 wire bytes다.

## 6. API와 거부의 결정성

제안 API는 `guards.validate_fs1_manifest(raw, *, expected_manifest_sha256=None)`다. raw는 exact bytes, 유효 expected는 exact str이다. None default는 검사 생략이 아니라 누락을 같은 정확한 code로 거부하기 위한 것이다. 성공은 `(raw: bytes, computed_plan_sha256: str, computed_manifest_sha256: str)` tuple이며 ALLOW/grant/token/receipt나 mutable parsed object가 아니다. 실패는 아래 code만 담은 `ValueError(code)`다. 데이터·credential·원문을 오류 메시지에 넣지 않는다.

정확한 단계 우선순위는 다음과 같다. 먼저 실패한 단계의 code 하나만 발생시킨다.

1. expected 인자 형식 → raw exact type → byte 길이 → strict UTF-8/BOM → 문자열/escape를 고려한 container-depth scan(16초과 즉시 중단). scan은 quote 안 bracket을 세지 않으며 음수 balance/mismatched closer는 JSON_INVALID, 미종료/불균형은 JSON parse에서 INVALID.

2. 단일 JSON 문법 parse. object의 decoded pair를 보존/검사하고 numeric token spelling을 검사한다. 문법이 틀리면 JSON_INVALID. 문법이 맞으면 duplicate flag 우선, 다음 numeric-profile flag. duplicate/invalid number는 parse 중 수집하며 임시 값은 어떤 schema/hash 성공에도 사용하지 않는다.

3. root object 및 root exact key set; android_build_identity가 object인 경우 exact key set. schema_version → plan_sha256 형식 → 다른 root 필드(ASCII key 오름차순, generation_slots/actions/경로 필드는 해당 전용 단계로 미룸).

4. generation_slots exact array → root path 규칙(allowed_app_relative_paths 먼저, host_evidence_directory 다음) → actions count.

5. 각 action을 입력 순서로: exact object/key set → kind → ordinal → id 및 이전 id 중복 → argv → input_hex/input_sha256/input_bytes → relative_path → 나머지 고정값/timeout/evidence/attempts.

6. 전체 action 종류열 → root cross relation(시간, argv 배열, path 집합, 합계 bytes 순) → raw canonical equality → 내부 plan digest → 외부 manifest digest. 같은 단계의 오류는 동일 code를 사용하며 실행·보정·fallback 없음.

Syntax parse 중에는 duplicate/numeric-profile 위반을 기록하되 임시 값으로 성공하지 않는다. 문법이 틀리면 JSON_INVALID, 문법이 맞으면 decoded duplicate flag, 다음 numeric flag 순이다. 같은 단계는 공통 code라 object key 입력 순서가 진단을 바꾸지 않는다. NaN/Infinity/-Infinity는 수용값이 아니라 numeric 위반을 기록하는 진단 token으로만 인지한다. 다른 JSON 문법 오류(선행0·후행 garbage 등)가 있으면 JSON_INVALID를 우선한다. root object 여부는 duplicate/numeric flag 다음에 검사한다. code 표나 root 관계 목록의 배열 순서 대신 위 단계 순서가 최종 우선순위다. metadata 숫자를 받아 준 다음 hash로만 거부하는 구현은 이 규칙을 만족하지 못한다. MemoryError 같은 환경 예외를 성공으로 바꾸지 않으며 예상 밖 예외는 후속 구현 검증 실패다.

| Code | 정확한 거부 이유 |
| --- | --- |
| `FS1_EXPECTED_DIGEST_FORMAT` | 외부 expected 인자 누락/None/타입·64자리 lowercase hex 오류 |
| `FS1_INPUT_TYPE` | raw가 exact bytes 타입이 아님 |
| `FS1_INPUT_SIZE` | raw 길이 1..65536 밖 |
| `FS1_JSON_ENCODING` | strict UTF-8 decode 실패 또는 leading UTF-8 BOM |
| `FS1_INPUT_DEPTH` | 문자열 밖 object/array 중첩 16 초과 |
| `FS1_JSON_INVALID` | JSON 문법/단일 root/후행 garbage 오류 또는 root가 object가 아님 |
| `FS1_JSON_DUPLICATE_KEY` | decoded key 중복: 어느 object에서도 금지 |
| `FS1_JSON_NUMBER` | 음수/-0/float/exponent/non-finite/31-bit 초과 숫자 token |
| `FS1_MANIFEST_FIELDS` | root 또는 android_build_identity의 key 집합 불일치 |
| `FS1_SCHEMA_VERSION` | schema_version exact int1 아님 |
| `FS1_PLAN_DIGEST_FORMAT` | plan_sha256 타입 또는 lowercase hex64 형식 오류 |
| `FS1_FIELD_VALUE` | 나머지 root scalar/array/build 값·타입·범위 불일치 |
| `FS1_GENERATION_SLOTS` | 정확한 고정 slot 식별자·순서·중복 금지 불일치 |
| `FS1_RELATIVE_PATH` | root/action path 문법·prefix·순서/중복·host 경로 불일치 |
| `FS1_ACTION_COUNT` | actions가 list가 아니거나 1..32 밖 |
| `FS1_ACTION_FIELDS` | action key 집합 또는 object 타입 오류 |
| `FS1_ACTION_KIND` | 허용한 4종 밖 kind |
| `FS1_ACTION_ORDINAL` | exact int 1..N과 array 위치 불일치 |
| `FS1_ACTION_ID` | action id 문법/중복 오류 |
| `FS1_ACTION_ARGV` | 문자열 배열·literal profile 비교 불일치 |
| `FS1_ACTION_INPUT` | input hex/hash/byte type·크기·합의 실패 |
| `FS1_ACTION_VALUE` | component/effect/bookkeeping/evidence_count/timeout/attempts 불일치 |
| `FS1_ACTION_ORDER` | 종류열 R(?:IL)?C* 불일치 |
| `FS1_MANIFEST_RELATION` | root budget/argv/path 집합과 action 사이 교차 관계 불일치 |
| `FS1_NONCANONICAL` | 입력 raw bytes와 canonical full M bytes가 다름 |
| `FS1_PLAN_DIGEST_MISMATCH` | C(M minus top-level plan_sha256)의 hash와 내부 digest 불일치 |
| `FS1_EXPECTED_DIGEST_MISMATCH` | 전체 raw canonical M hash와 trusted expected 인자 불일치 |

## 7. 정확히 24개 고정 벡터

[전체 test-vectors.json](benchmarks/real-device-gate-g1-fs1-spec/test-vectors.json)에는 **정확히 24개**의 독립 항목이 있다. 각 `input.raw_base64`는 생략·상속·patch 없이 **전체 입력 bytes**를 담는다. 각 항목에 길이/raw hash, complete expected 인자 또는 미전달 표시, 수용 tuple hash 또는 정확한 거부 code, 적용 요구 ID가 있다. malformed 자료도 base64가 지정하는 bytes 그대로다. 랜덤 입력/fixture generator/숨은 추가 벡터는 없다. 이 자료를 작성·hash 대조했을 뿐 FS1 검증기를 구현하거나 실행한 결과가 아니다.

| 벡터 | 사례 | 완전한 trusted expected 인자 | 지정 결과 |
| --- | --- | --- | --- |
| V01 | 최소 R 단독 유효 baseline; 반복·불변성·순수성 관찰의 기준 | `dc5b55685ed5f6a21e89b84c4ce8e4fb366f83a4accd51e72c0b1074c74688e2` | 자료만 수용 |
| V02 | R/I/L/C 4종·action32 및 canonical raw65536 bytes의 유효 경계 | `056ba3fd292a9097480fc1bd54f1622262990b27132b23826c74123e98167052` | 자료만 수용 |
| V03 | 지원하지 않는 정수 schema_version2 | `610d6e540744d6540892a4b3ba5404972b59294c622194b2ad70c559aff01e51` | `FS1_SCHEMA_VERSION` |
| V04 | 필수 executor_sha256 누락 | `78f0f5661a36b15d1ce856b6702425ee1cbb90ddea6cd8efd87cd1bd611c0923` | `FS1_MANIFEST_FIELDS` |
| V05 | 알 수 없는 grant 필드와 자기 권한 주장 | `74f894e1c0dd0057e572a6f2cfb55f455eaae826d3bc0ae699267213a3e808b8` | `FS1_MANIFEST_FIELDS` |
| V06 | 필수 nested object의 null | `0a05066ea4d388bd40649fbd8fd8d5dc351e58fc0e8756dfe3dde63dccc69a02` | `FS1_FIELD_VALUE` |
| V07 | decoded root key 중복 | `f9bc389a5731f99ee0e7a3b5934901c4eda893c76267fda02ded408c1e0f942c` | `FS1_JSON_DUPLICATE_KEY` |
| V08 | 수치가 같아도 exponent token 거부 | `bbb8e5e422bef1e554bf19fb271e7897062bf3762dc8722b58682c0837959f37` | `FS1_JSON_NUMBER` |
| V09 | caller가 전체 bytes를 pin해도 비canonical 공백을 거부 | `40bb2e7e1dfb9694aba4181827d7972c6162c9dae48baea7a171537ca550b598` | `FS1_NONCANONICAL` |
| V10 | 65537 bytes는 parse 전에 거부 | `de44833ed2354326826d1ea23ceb21b3292a963c68884cefd6891efbe97dd07c` | `FS1_INPUT_SIZE` |
| V11 | root1+array16으로 container depth17 | `d62ea2ab089b087745ae9b3899cd5e62ff90f9c539f8aaa251effc633c173871` | `FS1_INPUT_DEPTH` |
| V12 | actions33을 count 단계에서 거부; root 목록은 기존1개를 보존 | `0896e0ff1e8669ff833b3718835c3886c41388e4373c018f3c9ddf772ca7d58c` | `FS1_ACTION_COUNT` |
| V13 | clear mutation kind 거부 | `27fdc4402522863aa2f39a528ced485384862f7e842af5aa8f38cee5d2f568c5` | `FS1_ACTION_KIND` |
| V14 | ordinal 시작값0 거부 | `23f382fd9d4a77d5f1db874e5045d3afc606a05b75c1ac038b556bb5282683ac` | `FS1_ACTION_ORDINAL` |
| V15 | 연속 ordinal이라도 duplicate action id 거부 | `e6c70a6c563335779541c8fa23ec47badf15f7dec07aef637038fbe0b26861b8` | `FS1_ACTION_ID` |
| V16 | shell/interpreter argument shape 거부 | `881848cc919f9a36fdb07f7f352dfa2e69d7f9353031a4e25616bf065c63f0da` | `FS1_ACTION_ARGV` |
| V17 | 허용하지 않은 generation slot | `e81633dfecfe87ea17926c1ab52c08d8c4eb487381f47515c6304d4b3f2d0582` | `FS1_GENERATION_SLOTS` |
| V18 | 절대 host evidence path 거부 | `c030f35315300ae9ec1d2f23abcf7acf59f15851f6db2eeb74debfb79923ee67` | `FS1_RELATIVE_PATH` |
| V19 | dot-dot traversal app path 거부 | `53acf5e63b6db80a2a54095bdaa531940cc9ccedae910ed42769e0b2ff0fc585` | `FS1_RELATIVE_PATH` |
| V20 | expected keyword 누락은 default None으로 명시 거부 | 미전달(default None) | `FS1_EXPECTED_DIGEST_FORMAT` |
| V21 | expected digest uppercase를 normalize하지 않고 거부 | `DC5B55685ED5F6A21E89B84C4CE8E4FB366F83A4ACCD51E72C0B1074C74688E2` | `FS1_EXPECTED_DIGEST_FORMAT` |
| V22 | 내부 plan_sha256 형식 오류 | `bbe6d16124916f1037a1d215771575898a50676bed85da85226fa50b69c50522` | `FS1_PLAN_DIGEST_FORMAT` |
| V23 | 내부 plan_sha256가 유효 형식이어도 내용 불일치 | `4b354f9eeab0c37c589a77abd8f877280e0066af7a76b32552ee404116db3078` | `FS1_PLAN_DIGEST_MISMATCH` |
| V24 | 내용과 내부 hash를 함께 재작성해도 외부 baseline pin 불일치 | `dc5b55685ed5f6a21e89b84c4ce8e4fb366f83a4accd51e72c0b1074c74688e2` | `FS1_EXPECTED_DIGEST_MISMATCH` |

V02는 네 허용 kind를 모두 포함하며 action32/raw65,536 bytes를 정확히 만족한다. V10은 그 입력 뒤 공백1 byte를 붙인65,537 bytes라 size 단계에서 먼저 거부된다. V11의 root1+array16은 depth17이다. V12는 actions33의 count 오류를 고립하기 위해 root의 선언 목록은 기존1개를 유지한다. 이후 관계 오류까지 도달했다고 주장하지 않는다. V24는 내용과 내부 hash를 함께 바꾸되 외부 baseline pin을 유지한 자기 인증 방지 사례다.

H01–H04는 새 입력 벡터가 아닌 같은 corpus에 대한 통제 assertion이다. V01/V02의 immutable 반환·반복 결과, V01/V23/V24의 재진입/동시 호출에서 권한 상태 없음, 모든 호출의 I/O sink0, 기존 함수·중앙 거부·운영 caller0·두 파일/행 한도·index/source lock 보존을 확인한다. fixture/cataloque bytes 준비는 parser의 금지 sink 감시를 무장하기 전에 끝내고, 감시 중에는 실제 process/socket/device 호출 전에 실패시킨다.

24개가 모든 field 조합/모든 오류 분기를 exhaustive하게 실행하는 것은 아니다. UTF-8/BOM·빈 문자열·모든 int/bool/nonfinite·중복 ordinal 변형은 위 전체 명세에 따라 결정되며 이 corpus에서 각각 실행했다고 주장하지 않는다. 기존 P01 요구를 waiver하거나 기계 수용으로 바꾸지 않는다. [요구·P01 항목·벡터·통제 assertion 추적성](benchmarks/real-device-gate-g1-fs1-spec/traceability-map.json)에 적용 규칙과 대표 입력의 한계를 구분했다.

## 8. 구현 인계와 재개 범위

[implementation-handoff.json](benchmarks/real-device-gate-g1-fs1-spec/implementation-handoff.json)은 schema/digest/corpus/trusted catalogue/traceability/compatibility의 정확한 hash와 API·두 소스의 before hash를 고정한다. 이전 구현 허가가 이미 있다는 사용자의 현 지시를 존중한다. 이 문서는 재허가를 요구하거나 새 권한을 만들지 않고 명세 장애만 제거한다.

- `scripts/devicegate/guards.py`: 순수 parser와 immutable 자료 반환만 추가. 기존 HTTP/APK/자식 감독 함수·거부 경계는 보존한다.
- `scripts/devicegate/test_safety.py`: 새 class와 동결 corpus의 메모리 입력 시험만 추가. 기존 test/fixture를 바꾸거나 자동 선택하지 않는다.
- 두 기존 파일·새 runtime 파일0·추가240행(parser100/test140)·후보1·고정24 벡터·시험300초/증거10MiB·자동 retry0을 유지한다.
- 새 runtime 함수/모듈은 문서/정책 JSON을 읽지 않는다. 시험 setup에서만 고정 data file을 pin 검증 후 메모리로 준비할 수 있다. 이 JSON들은 시험 자료이며 추가 runtime source가 아니다.
- API가 순수하다는 이유로 source lock·closure를 새 전체 source에 자동 이전하지 않는다. 새 후보 source hash·기존 함수 불변·효과 경로 없음의 별도 검토가 필요하다.

한도 안에서 구현할 수 없거나 기존 거부/함수 변경·새 I/O/운영 caller/OS/ADB/Android·새 scope가 필요하면 검사를 삭제하거나 조용히 확장하지 말고 중단해야 한다. 이번 READY는 행 수 안에서 구현됐다는 증명이나 후속 독립 수용이 아니다. 실제 함수 구현·시험·review는 후속 허가 범위의 작업이며 이번 턴에서는 하지 않았다.

## 9. 이번 작업의 확인과 보존

새 실행 코드·새 validator·devicegate 실행기 import·FS1 runtime 시험은0이다. ADB(help/version 포함)·ADB server 요청·emulator·physical device·APK 설치·production 접근/OS 변경도0이다. 기존 세션의 npm build와 backend72 tests+44 subtests 통과 자료는 P01 역사 결과로 보존한다. 그 후 코드가 그대로인 문서 전용 작업이므로 제품 검증을 반복하거나 그 결과를 FS1 검증/기술 proof 수용으로 집계하지 않는다.

기본 shell sandbox의 bwrap 초기화 오류 후 승인 검토된 host shell에서 읽기·문서 작성·자료 hash 계산만 수행했다. corpus 조립의 shared-list 및 인계 경로 표현 오류는 발행 전 신규 자료 안에서 정정하고 [작성 기록](benchmarks/real-device-gate-g1-fs1-spec/authoring-notes.json)에 남겼다. 기존 파일을 고치거나 실행 권한을 우회하지 않았다.

시작 시 기존8,155개 경로·외부 원 B03 sidecar5개·HEAD·Git index/staged 신원을 고정했다. 종료 대조와 source lock/P01 증거 보존은 [preservation-verification.json](benchmarks/real-device-gate-g1-fs1-spec/preservation-verification.json), 정적 명세/corpus 신원 검사는 [document-validation.json](benchmarks/real-device-gate-g1-fs1-spec/document-validation.json)에 둔다. [최종 evidence manifest](benchmarks/real-device-gate-g1-fs1-spec/evidence-manifest.json)는 새 산출물 bytes만 고정한다. 대형 임시 산출물·DB/build/cache 생성/삭제는 NOT APPLICABLE이다. commit/push는 없고 규범·역사 보고서·기존 실행 코드·Git index를 수정하지 않았다.

**네 공백의 최종 상태:** manifest schema RESOLVED, action 모델 RESOLVED, generation-slot/경로 규칙 RESOLVED, plan digest 결합 RESOLVED.

**기존 두 파일 FS1 구현은 원래 승인된 순수 호스트 범위 안에서 안전하게 재개할 수 있다. 이번 턴에서는 재개하지 않았으며 운영 ADB와 모든 기기 실행은 계속 BLOCKED다.**
