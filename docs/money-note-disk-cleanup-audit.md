# Money Note 디스크 사용 감사 및 정리 제안

작성일: 2026-10-23 (KST). **Phase 1 완료. 삭제 0개.**
저장소의 할당량은 **73.225 GiB**이며, 원인은 대형 합성 DB보다 **Flutter 테스트 컴파일 캐시 66.393 GiB**다.
실험 SQLite를 건드리지 않고 생성물 다섯 그룹에서 **71.460 GiB (76,729,421,824 B)**를 회수할 수 있는 계획을 마련했다.
이는 삭제 전 추정치이며 이번 감사에서 공간을 회수하지 않았다. 별도 승인 전 Phase 2를 실행하지 않는다.

**1. 저장소 식별과 시작 상태**

현재 디렉터리와 `git rev-parse --show-toplevel`은 모두 `/home/hjkerman/codex/money-note`다.
HEAD는 `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`, branch는 `main`, origin은 `git@github.com:hjkerman/money-note.git`다.
예상 역사 HEAD와 같으며 reset·checkout·stash를 하지 않았다. local main, origin/main, origin/HEAD가 같은 HEAD를 가리킨다.
다른 branch와 원격 ref 및 Codex checkpoint ref까지 JSON의 `baseline.refs`에 기록했다. 원격 fetch는 하지 않았으므로 로컬 remote-tracking ref 관측이다.

시작 상태는 **staged 0 / unstaged 3 / untracked 개별 파일 697**이다.
일반 porcelain 출력에서는 untracked 디렉터리 묶음을 포함해 13행이며, 변경된 tracked 파일은 다음 세 개다.

- `docs/benchmarks/t66f-b03/counters.py`
- `docs/benchmarks/t66f-b03/server.py`
- `mobile/test/support/logical_cost_sqlite.dart`

IC01 및 P01–P04 구현·테스트·보고서·증거 디렉터리는 의도된 미커밋 작업으로 보호했다.
시작 porcelain 전체, ignored 경로 목록과 Git refs는 [후보 JSON](money-note-disk-cleanup-candidates.json)에 저장했다.
Git index SHA-256은 `d798903ba98422ba4904868943ca974b4ce71b264321bce4b1f362bd98ba3ff2`다.
기존 tracked/untracked regular 파일 집합의 내용 지문은 `3d9bed15162fa5a39a185decd7fba87ee2e01f2847b66f457ec070735676b236`다.
인덱스를 변경하는 명령, Git 객체 정리, commit/push는 실행하지 않았다.

**2. 측정 범위와 파일시스템**

`AGENTS.md`, `docs/project-state.md`, `docs/domain-model.md`, `docs/known-issues.md`, `docs/runbook.md` 및 IC01/P01/P02/P03/P04 보고서와 증거 manifest를 확인했다.
저장소는 같은 filesystem만 순회했고 symlink를 따라가지 않았다. 홈 전체를 검색하지 않았다.
외부는 보고서·소스가 실제 가리키는 `/tmp` 실험 루트 40개만 측정했다. 별도로 P05 관련 두 prefix만 확인했다.
`/opt/money-note`, 운영 DB/Snapshot/.env, Docker 저장소와 공유 시스템 캐시는 조사·변경하지 않았다.

| 측정 대상 | 할당량 | apparent 크기 또는 비고 |
|---|---:|---|
| 저장소 전체 | 78,624,788,480 B / 73.225 GiB | 78,439,180,602 B; 파일 52,632개 |
| mobile 전체 | 77,663,961,088 B / 72.330 GiB | 77,599,800,098 B |
| 참조된 외부 실험 40루트 | 10,553,577,472 B / 9.829 GiB | 저장소 합계에 포함하지 않음 |
| 저장소 + 위 외부 루트 | 89,178,365,952 B / 83.054 GiB | 서로 겹치지 않는 범위 |
| filesystem 전체 | 210,779,168,768 B | 시작 used 187,684,110,336 B (94%) |
| 시작 사용 가능 공간 | 13,393,235,968 B | reserved block을 제외한 available |
| 후속 사용 가능 공간 | 13,435,666,432 B | 호스트의 다른 작업으로 변동; 감사 회수량 아님 |
| Git 전체 | 70,123,520 B / 0.065 GiB | 모든 객체·refs 보호 |

allocated는 `st_blocks × 512` 및 `du -x -B1`, apparent는 파일의 논리 크기다.
저장소 allocated와 apparent 차이는 **185,607,878 B**다. 파일/디렉터리 블록 반올림과 metadata가 반영된다.
디렉터리 합계는 하위 디렉터리를 포함하므로 아래 상위 20개를 다시 합산하면 안 된다.
hard link는 dev/inode로 중복 계상하지 않았다. 후보 G01–G05의 regular file에는 hard link·symlink가 없다.
`work/deploy`에는 symlink 80개와 hard link가 있는 regular 경로 8개가 있으므로 그 크기를 단순 파일 크기 합으로 판단하지 않았다.
실제 회수량은 열린 삭제 파일, filesystem metadata와 다른 프로세스의 동시 쓰기에 따라 df 차이와 달라질 수 있다.

**3. 상위 경로 분포**

| 경로 | 할당량 | 파일 수 |
|---|---:|---:|
| `mobile/` | 77,663,961,088 B / 72.330 GiB | 13,605 |
| `work/` | 557,326,336 B / 0.519 GiB | 23,228 |
| `docs/` | 122,585,088 B / 0.114 GiB | 3,152 |
| `frontend/` | 112,201,728 B / 0.104 GiB | 5,671 |
| `.venv/` | 87,625,728 B / 0.082 GiB | 2,206 |
| `.git/` | 70,123,520 B / 0.065 GiB | 4,126 |
| `backend/` | 9,707,520 B / 0.009 GiB | 524 |
| `scripts/` | 892,928 B / 0.001 GiB | 61 |
| `.ruff_cache/` | 204,800 B / 0.000 GiB | 47 |
| `.pytest_cache/` | 114,688 B / 0.000 GiB | 5 |
| `.github/` | 16,384 B / 0.000 GiB | 2 |

`docs/benchmarks`는 119,955,456 B / 0.112 GiB로 원시 로그·독립 감사·historical source-SHA·재현 스크립트를 포함한다.
`work/dev-data`는 83,927,040 B / 0.078 GiB이며 개발 DB와 T6.4 독립 감사 before/after/seed를 보호한다.
선택한 생성물·의존성·staging 10루트의 합계는 **78,332,362,752 B / 72.953 GiB**다.
이 수치는 삭제 가능 합계가 아니다. 경로별 원자료는 JSON `measurements.generated_roots`에 있고, 작은 기타 Python 캐시는 합산에서 제외했다.

**4. 저장소 최대 디렉터리 20개**

| 경로 | 할당량 | 하위 파일 수 |
|---|---:|---:|
| `mobile` | 77,663,961,088 B / 72.330 GiB | 13605 |
| `mobile/build` | 76,158,214,144 B / 70.928 GiB | 12812 |
| `mobile/build/test_cache` | 71,289,323,520 B / 66.393 GiB | 1082 |
| `mobile/build/test_cache/build` | 71,289,319,424 B / 66.393 GiB | 1082 |
| `mobile/build/app` | 4,751,925,248 B / 4.426 GiB | 3411 |
| `mobile/build/app/intermediates` | 3,950,055,424 B / 3.679 GiB | 2753 |
| `mobile/build/app/intermediates/merged_native_libs` | 2,462,355,456 B / 2.293 GiB | 46 |
| `mobile/.dart_tool` | 1,470,107,648 B / 1.369 GiB | 533 |
| `mobile/build/app/intermediates/merged_native_libs/debug` | 1,389,346,816 B / 1.294 GiB | 15 |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs` | 1,389,342,720 B / 1.294 GiB | 15 |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out` | 1,389,338,624 B / 1.294 GiB | 15 |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib` | 1,389,334,528 B / 1.294 GiB | 15 |
| `mobile/.dart_tool/flutter_build` | 1,332,572,160 B / 1.241 GiB | 423 |
| `mobile/build/app/intermediates/incremental` | 733,179,904 B / 0.683 GiB | 619 |
| `mobile/build/app/outputs` | 716,673,024 B / 0.667 GiB | 24 |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib/arm64-v8a` | 646,057,984 B / 0.602 GiB | 5 |
| `mobile/build/app/intermediates/merged_native_libs/profile` | 559,194,112 B / 0.521 GiB | 17 |
| `mobile/build/app/intermediates/merged_native_libs/profile/mergeProfileNativeLibs` | 559,190,016 B / 0.521 GiB | 17 |
| `mobile/build/app/intermediates/merged_native_libs/profile/mergeProfileNativeLibs/out` | 559,185,920 B / 0.521 GiB | 17 |
| `mobile/build/app/intermediates/merged_native_libs/profile/mergeProfileNativeLibs/out/lib` | 559,181,824 B / 0.521 GiB | 17 |

**5. 저장소 최대 파일 20개**

아래 파일은 모두 Git ignored인 빌드 출력이며 tracked 파일이 아니다. 접근 가능한 프로세스에서 열린 사용은 관측되지 않았다.
mtime은 UTC다. 정확한 ns 시각·dev/inode·nlink·symlink 여부는 JSON에 기록했다.
APK 출력은 배포 경로에서 사용될 수 있어 R01로 남겼고, 나머지 행은 G02/G03 안의 재생성 가능한 중간 파일이다.

| 경로 | apparent B | 할당 B | 수정 시각 |
|---|---:|---:|---|
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib/arm64-v8a/libflutter.so` | 395,316,440 | 395,321,344 | 2026-10-12 02:12:59 UTC |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib/x86_64/libflutter.so` | 390,001,840 | 390,008,832 | 2026-10-12 02:12:59 UTC |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib/armeabi-v7a/libflutter.so` | 348,884,936 | 348,889,088 | 2026-10-12 02:12:58 UTC |
| `mobile/build/app/intermediates/merged_native_libs/debug/mergeDebugNativeLibs/out/lib/arm64-v8a/libVkLayer_khronos_validation.so` | 248,644,248 | 248,651,776 | 2026-10-12 02:12:58 UTC |
| `mobile/build/app/outputs/apk/debug/app-debug.apk` | 202,521,677 | 202,526,720 | 2026-10-21 00:58:56 UTC |
| `mobile/build/app/outputs/flutter-apk/app-debug.apk` | 202,521,677 | 202,526,720 | 2026-10-22 01:19:32 UTC |
| `mobile/build/app/intermediates/incremental/debug-mergeJavaRes/zip-cache/JbmPVncrtqJtisMXDas_JSoY5o8=` | 180,591,519 | 180,596,736 | 2026-09-17 13:23:46 UTC |
| `mobile/build/app/intermediates/merged_native_libs/profile/mergeProfileNativeLibs/out/lib/x86_64/libflutter.so` | 174,422,960 | 174,428,160 | 2026-10-07 15:04:50 UTC |
| `mobile/build/app/intermediates/merged_native_libs/profile/mergeProfileNativeLibs/out/lib/arm64-v8a/libflutter.so` | 173,880,304 | 173,887,488 | 2026-10-07 15:04:50 UTC |
| `mobile/build/app/intermediates/merged_native_libs/release/mergeReleaseNativeLibs/out/lib/x86_64/libflutter.so` | 165,996,904 | 166,002,688 | 2026-10-01 00:26:37 UTC |
| `mobile/build/app/intermediates/merged_native_libs/release/mergeReleaseNativeLibs/out/lib/arm64-v8a/libflutter.so` | 165,164,528 | 165,171,200 | 2026-10-01 00:26:37 UTC |
| `mobile/build/app/intermediates/merged_native_libs/profile/mergeProfileNativeLibs/out/lib/armeabi-v7a/libflutter.so` | 158,892,120 | 158,900,224 | 2026-10-07 15:04:50 UTC |
| `mobile/build/app/intermediates/merged_native_libs/release/mergeReleaseNativeLibs/out/lib/armeabi-v7a/libflutter.so` | 151,593,280 | 151,601,152 | 2026-10-01 00:26:36 UTC |
| `mobile/build/app/intermediates/incremental/debug-mergeJavaRes/zip-cache/BhrqqQu3ezb1FC0Wt6Aagjrt57w=` | 119,914,343 | 119,918,592 | 2026-09-17 13:23:47 UTC |
| `mobile/build/app/intermediates/incremental/debug-mergeJavaRes/zip-cache/HxAb5vDlkH29cm6HE1F0D5nRJwE=` | 114,678,064 | 114,683,904 | 2026-09-17 13:23:46 UTC |
| `mobile/build/app/outputs/apk/profile/app-profile.apk` | 77,732,703 | 77,733,888 | 2026-10-07 15:04:52 UTC |
| `mobile/build/app/outputs/flutter-apk/app-profile.apk` | 77,732,703 | 77,733,888 | 2026-10-07 23:44:38 UTC |
| `mobile/build/app/intermediates/flutter/debug/flutter_assets/kernel_blob.bin` | 74,409,208 | 74,416,128 | 2026-10-21 00:58:50 UTC |
| `mobile/build/app/intermediates/assets/debug/mergeDebugAssets/flutter_assets/kernel_blob.bin` | 74,409,208 | 74,416,128 | 2026-10-22 01:19:30 UTC |
| `mobile/.dart_tool/flutter_build/cdbf80ee24d1e29854acca7bab1c0887/app.dill` | 74,409,208 | 74,416,128 | 2026-10-21 00:58:47 UTC |

전체 조사 범위에서는 저장소 밖의 100k SQLite 파일들이 더 크다. 예를 들어 원 독립 100k client DB는 621,584,384 B 할당이고 P03 원본은 612,200,448 B다.
외부 상위 파일은 JSON의 `protected_external_groups`와 `sqlite_inventory`에서 구분된다.

**6. SQLite 인벤토리**

확장자 검색 뒤 `SQLite format 3\0` 헤더를 확인했다. JavaScript 파일명 등에 포함된 `.db` 문자열은 DB로 세지 않았다.

| 범위 | 파일 수 | SQLite/sidecar 할당량 |
|---|---:|---:|
| 저장소 `work/dev-data` | 58 | 83,841,024 B / 0.078 GiB |
| 보고서 참조 외부 실험 | 109 | 10,053,861,376 B / 9.363 GiB |
| 합계 | 167 | 10,137,702,400 B / 9.441 GiB |
| 이번 조사에서 발견한 WAL/SHM/journal | 0 | sidecar 개별 삭제 후보 없음 |

167개 모두 JSON에 절대경로와 identity를 기록했고 **PROTECTED**다.
저장소 안 `mobile/`에는 SQLite 파일이 없었다. 큰 E1 store와 synthetic fixture는 외부 실험 경로에 있다.
live DB 복사·backup 생성·VACUUM·checkpoint·migration·WAL 제거를 하지 않았다.

외부 실험의 큰 소유 그룹은 다음과 같다. 아래 나머지 30루트도 JSON에서 모두 보호했다.

| 실험 루트 | 전체 할당량 | SQLite 파일 수 |
|---|---:|---:|
| `/tmp/mn-p04-late-ybr2mat5` | 3,674,288,128 B / 3.422 GiB | 6 |
| `/tmp/mn-b02` | 2,041,147,392 B / 1.901 GiB | 16 |
| `/tmp/mn-p03-real-RMZIIJ` | 1,182,478,336 B / 1.101 GiB | 11 |
| `/tmp/mn-a02-corrected-100000-9k9mr_4l` | 645,484,544 B / 0.601 GiB | 1 |
| `/tmp/mn-b02-independent-100000-z6ux9y53` | 624,541,696 B / 0.582 GiB | 1 |
| `/tmp/mn-a01-corrected-100000-uo97rtfi` | 518,873,088 B / 0.483 GiB | 1 |
| `/tmp/mn-a01-corrected-50000-cursor-lifetime-8h2c68uy` | 347,688,960 B / 0.324 GiB | 1 |
| `/tmp/mn-a02-corrected-50000-1myuwv_o` | 323,997,696 B / 0.302 GiB | 1 |
| `/tmp/mn-b02-independent-50000-lqzk7mdo` | 312,102,912 B / 0.291 GiB | 1 |
| `/tmp/mn-b02-a01-20261018-220659` | 174,260,224 B / 0.162 GiB | 3 |

**7. P03 원본과 T6.6F 증거 보호**

원본은 `/tmp/mn-p03-real-RMZIIJ/full-client/segmented-store-v1/f5c0796c0a144c198b70925f5ba95a3bf1005986eba3b7f677fbbda85258005f.sqlite`다.
파일 크기 612,196,352 B, 할당 612,200,448 B, objects **397,146개**, accepted current/previous는 null, sequence는 0이다.
WAL/SHM/journal이 없음을 먼저 확인하고 `mode=ro&immutable=1` 연결로만 읽었다.
`quick_check=ok`, foreign_key_check 위반 0, SHA-256은 기존 P04 clone-plan의
`9adbc6bb6f4df2d756dedb4825450a540ee490e64f48e9f5d803e08094729ce6`와 정확히 같았다.
원본 파일의 크기와 mtime도 검사 전후 같았다. 레코드 전체를 RAM에 올리거나 DB를 재작성하지 않았다.

P04의 [prepare.py](benchmarks/t66f-b03-ic01-p04/prepare.py), [clone-plan.json](benchmarks/t66f-b03-ic01-p04/evidence/clone-plan.json),
[보고서](t66f-b03-ic01-p04-late-stage-differential-diagnosis.md)는 smoke A/B 및 A/B/C/D clone의 각 비교 역할을 명시한다.
여섯 파일은 모두 유지한다. 원 P03와 P04 결과는 stage 변경이 있어 같은 증거로 대체하지 않는다.
동일 Target backend catalog 부재라는 기존 P04 한계는 그대로이며, 이번 저장공간 감사가 그 실험을 복구하거나 검증 완료한 것은 아니다.

원 N=100k source fixture `/tmp/mn-b02-independent-100000-z6ux9y53`, B02 synthetic layout-model,
A01/A02의 50k/100k client, P03 warm/prefix/renew 상태도 전부 보존한다.
`docs/benchmarks`, 독립 audit raw evidence, IA01–IA07 reproducers, historical source-SHA, P01/P02 준비/계측 스크립트와 기존 미커밋 소스는 모두 보호한다.
IC01-P05 보고서/코드 참조와 `/tmp/mn-p05*`, `/tmp/mn-ic01-p05*`는 발견하지 못했다.
다른 이름의 P05가 존재하지 않는다고 단정하지 않으며, 외부 실험 자료 자체를 삭제 범위에서 제외했다.

보호 실험 범위를 `docs/benchmarks + work/dev-data + 참조 외부 루트`로 잡으면
**10,757,459,968 B / 10.019 GiB**다. 소스와 Git 등 다른 보호 대상을 포함한 총 보호량과 구별한다.

**8. 중복 확인 결과**

비슷한 크기의 후보를 먼저 좁힌 뒤 P04 여섯 파일과 P03 원본에 한해 전체 SHA-256을 순차 계산했다.
다른 DB를 전부 해시하거나 논리값 동등성만으로 삭제 가능하다고 판단하지 않았다.

| 그룹 | 실파일 | 합계 할당량 | 해시/역할 | 이번 회수 가능 |
|---|---|---:|---|---:|
| D01 | P04 smoke-A, smoke-B | 1,224,425,472 B | SHA-256 `281fee03…71b70` 일치; 각 smoke 실행의 증거 | 0 B |
| D02 | P04 A, B, C, D | 2,449,735,680 B | SHA-256 `64a86b72…15de` 일치; 네 모드 matched 결과 | 0 B |
| APK-debug | outputs/apk/debug 및 outputs/flutter-apk | 405,053,440 B | 전체 SHA 일치; 별도 inode, nlink=1 | 0 B, R01 |
| APK-profile | outputs/apk/profile 및 outputs/flutter-apk | 155,467,776 B | 전체 SHA 일치; 별도 inode, nlink=1 | 0 B, R01 |
| APK-release | outputs/apk/release 및 outputs/flutter-apk | 112,439,296 B | 전체 SHA 일치; 별도 inode, nlink=1 | 0 B, R01 |

DB 중복 그룹 저장량은 **3,674,161,152 B / 3.422 GiB**다.
각 그룹 하나씩만 남긴다는 가상의 초과 복사본은 4개, **2,449,514,496 B / 2.281 GiB**지만 이들은 보호 증거이므로 회수 추정에 포함하지 않았다.
남겨야 할 counterpart는 **그룹의 모든 구성원**이다. 서로 다른 실험 identity는 파일 hash가 같아도 폐기 근거가 되지 않는다.
원본 P03의 사용 가능성만 이번에 native 검사로 확인했고, clone 전체의 fresh 무결성 검사를 반복하지 않았다.
clone의 논리값 동등성은 기존 P04 기록이고 새 claim으로 확장하지 않았다.
**SAFE_DUPLICATE로 승인 가능한 항목은 0개**다. APK 중복 수치는 R01 크기에 이미 포함되어 별도로 더하지 않는다.

**9. 실행 프로세스와 한계**

`ps`와 접근 가능한 `/proc/<pid>/fd`, `map_files`, cwd를 읽었다.
저장소를 cwd로 쓰는 Codex PID 8451/271577/273916이 있으나 후보를 연 fd/mapping은 관측되지 않았다.
Dart/Flutter/Gradle/SQLite/benchmark writer도 관측되지 않았다.
PID 2007 Python과 2014 uvicorn은 `/app`에서 동작 중이며 운영 서비스일 수 있으므로 접속·중지·변경하지 않았다.
**관측된 후보 충돌은 0건**이지만 시스템 PID 255개의 fd/map_files는 접근 제한이었다.
다른 mount namespace의 경로 사용도 완전히 배제하지 못한다. 권한 제한을 무시하고 시스템 전체 open-file 안전을 확정하지 않았다.
Phase 2 직전에 다시 검사하고, 사용 중이거나 사용 여부를 확인할 수 없는 후보는 보류해야 한다.
unlink된 열린 파일은 프로세스가 닫을 때까지 블록이 회수되지 않을 수 있다.

**10. 정리 후보와 분류**

| 경로 또는 그룹 | 할당량 | 분류 | 폐기 또는 보호 이유 | 예상 회수량 |
|---|---:|---|---|---:|
| `mobile/build/test_cache/build` (G01) | 71,289,319,424 B / 66.393 GiB | SAFE_GENERATED | 생성물; 원 소스·실험 증거를 보존하고 재생성 가능 | 71,289,319,424 B / 66.393 GiB |
| `mobile/build/app/intermediates` (G02) | 3,950,055,424 B / 3.679 GiB | SAFE_GENERATED | 생성물; 원 소스·실험 증거를 보존하고 재생성 가능 | 3,950,055,424 B / 3.679 GiB |
| `mobile/.dart_tool/flutter_build` (G03) | 1,332,572,160 B / 1.241 GiB | SAFE_GENERATED | 생성물; 원 소스·실험 증거를 보존하고 재생성 가능 | 1,332,572,160 B / 1.241 GiB |
| `mobile/.dart_tool/hooks_runner` (G04) | 135,688,192 B / 0.126 GiB | SAFE_GENERATED | 생성물; 원 소스·실험 증거를 보존하고 재생성 가능 | 135,688,192 B / 0.126 GiB |
| `work/npm-cache/_cacache` (G05) | 21,786,624 B / 0.020 GiB | SAFE_GENERATED | 생성물; 원 소스·실험 증거를 보존하고 재생성 가능 | 21,786,624 B / 0.020 GiB |
| `mobile/build/app/outputs` (R01) | 716,673,024 B / 0.667 GiB | REVIEW_REQUIRED | APK/배포 복구 역할 추가 검토 | 현재 0 B |
| `work/deploy` (R02) | 451,551,232 B / 0.421 GiB | REVIEW_REQUIRED | APK/배포 복구 역할 추가 검토 | 현재 0 B |
| `docs/benchmarks + work/dev-data + 참조 외부 루트` | 10,757,459,968 B / 10.019 GiB | PROTECTED | 원 실험·독립감사·재현·복구 증거 | 0 B |
| `.git`, 기존 소스·설정·credential 및 기타 제외 경로 | 전체 분류의 나머지 | PROTECTED | 역사·미커밋 작업·운영 및 개발 baseline 보존 | 0 B |

**VERIFIED SAFE:** G01–G05는 ignored라는 사실 외에 생성자·파일 형식·구성·소스/결과 분리·보고서 정확 경로 참조 부재·관측 사용 여부를 확인했다.
G01은 1,082개 모두 Dart kernel magic `90abcdef`이고 71,283,594,384 B apparent에 71,289,319,424 B allocated다.
현재 Flutter SDK의 `packages/flutter_tools/lib/src/test/test_compiler.dart:110`에서 test_cache 경로와 증분 dill 재사용을 확인했다.
역사적 assertion·원시 JSON/XML/log·동결 소스는 이 캐시 안에 있지 않으며 모두 별도 보호된다.
G02/G03는 Gradle/Flutter 중간 출력이고 최종 APK 및 원 소스/lockfile이 남는다.
G04는 hook 컴파일 캐시, G05는 저장소 전용 npm 다운로드 캐시다.
재생성 가능성은 과거 실행의 byte-identical 바이너리나 과거 timing 수치를 재현한다는 보장은 아니다.

**PROBABLE BUT UNVERIFIED:** R01/R02 **1.088 GiB**.
R01은 signed APK·mapping·출력 로그의 필요 retained counterpart를 정하지 않았다.
R02는 runbook의 현재+직전 성공 배포 및 실패 복구 보관 정책과 관련되어, 운영 marker 확인 없는 삭제는 보류했다.
이들은 G01–G05 승인에 포함되지 않는다. 이번 수치에서 조건부 상한과 검증된 회수량을 혼합하지 않았다.

**PROTECTED:** 저장소 나머지 **0.677 GiB**와 외부 **9.829 GiB**,
합계 **10.506 GiB**.
이는 조사 범위에 대한 보존 분류이며 전부가 기술적으로 재생성 불가능하다는 뜻은 아니다.
단순 크기·tmp 명칭·ignored 여부·hash 일치 때문에 데이터 보존 의무를 완화하지 않았다.

**11. 물리 회수량과 권장 순서**

검증된 회수 제안은 **76,729,421,824 B / 71.460 GiB**다. 리뷰 대상 **1,168,224,256 B / 1.088 GiB**는 추가 절차 없이는 0 B로 취급한다.
저장소 분류는 검증 후보 + 리뷰 + 보호 = 78,624,788,480 B로 정확히 일치한다.
외부 10,553,577,472 B는 전부 보호하므로 저장소 회수량에 섞지 않았다.
디렉터리 metadata를 포함한 추정이며 사용 중인 블록·filesystem reserved block·다른 프로세스 쓰기에 따른 df 차이는 보장하지 않는다.

우선 G01 (66.393 GiB), 이어 G02 (3.679 GiB), G03 (1.241 GiB)을 검토하면
**71.313 GiB**의 큰 공간을 확보하는 계획이 된다. G04/G05 추가는 0.147 GiB다.
작은 캐시 수천 개를 별도로 쫓거나 실험 SQLite를 지울 필요가 없다.
새 benchmark·무결성 실험·성능 비교·압축·hard-link dedup·filesystem 변경은 실행하지 않았다.

**12. Phase 2 승인 경계와 manifest 사용**

JSON의 G01–G05 각각은 **정확한 절대경로·identity·크기·파일 수·mtime/ctime(ns 문자열)·지문·Git tracked/ignored·symlink/hard-link·관측 프로세스·폐기 이유·재생성 방법·보호 counterpart·위험**을 포함한다.
이는 삭제 실행 스크립트가 아니다. `approved=false`, `deletion_authorized=false`다.
승인할 때 group ID와 manifest SHA-256을 고정하고 이후 후보를 몰래 추가·변경하지 않는다.
G01 승인으로 `mobile/build` 전체를, G03 승인으로 `mobile/.dart_tool` 전체를 제거할 수 없다.

Phase 2에서는 **삭제 직전** 다음을 다시 확인한다.

1. root/조상 realpath·dev/inode·symlink·mount 상태와 전체 metadata tree 지문이 동일해야 한다.
2. 각 파일의 ns 시각·크기·mode·nlink·할당량·파일 목록이 바뀌면 해당 그룹을 보류한다.
3. Git 추적·현재 보고서 참조·관련 writer·fd/mapping/cwd 사용을 다시 확인한다. 확인 불가 상태도 보류한다.
4. writer가 새로 시작하지 않는 안정 구간을 확보한다. 프로세스를 강제 종료하지 않는다.
5. R01/R02·모든 DB 및 sidecar·외부 실험·Git·기존 소스는 삭제 범위에 넣지 않는다.
6. 회수 후 df 및 Git index/기존 source digest를 비교해 실제 결과를 기록한다.

metadata 지문은 내용 전체 해시가 아니다. 재생성 가능 파일에 한정한 저비용 identity fence이며,
변화 감지 시 재분류해야 한다. 정밀 시각 직렬화 규칙은 JSON `fingerprint_spec`에 고정했다.

**13. 명시적 보호 파일과 보존 검증**

`.git` 전체, 기존 tracked/untracked 구현·테스트·보고서 전체, 모든 SQLite 및 companion,
`docs/benchmarks`, `work/dev-data`, 원 P03, P04 여섯 clone, 역사 50k/100k fixtures,
`frontend/.env.development.local`, `mobile/android/key.properties`, `mobile/android/local.properties`를 보호한다.
credential 내용은 보고서에 출력하지 않았다.
원 실험 데이터/증거의 파일 내용은 변경하지 않았고 원 P03 해시는 manifest와 같았다.

보고서 작성 직전 HEAD·기존 porcelain·Git 인덱스 hash·기존 regular source 집합 hash는 시작 값과 모두 같았다.
새 감사 산출물 두 개를 제외한 최종 보존 검사는 아래에 기록한다.

최종 보존 검사: **PASS — Git 인덱스·HEAD/refs·기존 porcelain·기존 tracked/untracked source 지문 보존. 후보 7그룹 metadata 지문과 P03 원본 SHA-256 불변. 새 untracked 감사 산출물 2개만 추가.**

사용자의 Phase 1 읽기 전용 제한이 이번 작업의 우선 조건이므로 `npm build`, backend 테스트, Flutter 테스트는 실행하지 않았다.
이 명령은 캐시·임시 DB·보고서를 생성/변경하므로 이번 감사 목적과 충돌한다.
대신 JSON 구문·합계·후보 identity·Git/source 보존을 검증한다.
읽기는 filesystem 정책에 따라 atime을 갱신할 수 있으나 파일 내용·mtime/ctime을 의도적으로 변경하는 작업은 하지 않았다.
기본 샌드박스가 `bwrap: loopback ... Operation not permitted`로 기동 실패하여, 허용된 실행 경로에서 동일한 읽기 명령을 수행했다.
최종 산출물 경로는 기존 파일과 충돌하지 않았으며 두 파일을 새로 만들었다.

권고는 **생성 캐시 G01–G03부터 별도 승인해 큰 공간을 확보하고, 실험 DB와 역사 증거는 계속 유지하는 것**이다.
Phase 1은 이 문서와 manifest 작성으로 종료한다.

```text
MONEY NOTE DISK CLEANUP AUDIT:
COMPLETE

REPOSITORY:
/home/hjkerman/codex/money-note

HEAD:
ebcbd54d90eeee194a04b9eea6367f446ee2fd28

GIT INDEX:
PRESERVED

UNCOMMITTED IC01 WORK:
PRESERVED

ORIGINAL EXPERIMENTAL SQLITE:
PRESERVED

HISTORICAL AUDIT EVIDENCE:
PRESERVED

TOTAL REPOSITORY SIZE:
78,624,788,480 B / 73.225 GiB

MOBILE DIRECTORY SIZE:
77,663,961,088 B / 72.330 GiB

SQLITE AND DATABASE ARTIFACTS:
10,137,702,400 B / 9.441 GiB (저장소 + 참조된 외부 실험)

BUILD AND CACHE ARTIFACTS:
78,332,362,752 B / 72.953 GiB (측정한 생성물·의존성·staging)

DUPLICATE CANDIDATES:
DB 2그룹·6개 / 3.422 GiB; APK 3쌍 / 0.627 GiB — 삭제 가능 판정 아님

VERIFIED SAFE RECLAIMABLE:
71.460 GiB

REVIEW REQUIRED:
1.088 GiB (저장소 내 R01/R02)

PROTECTED:
10.506 GiB (저장소 0.677 + 외부 9.829)

TOP 5 CLEANUP CANDIDATES:
G01 mobile/build/test_cache/build — 66.393 GiB
G02 mobile/build/app/intermediates — 3.679 GiB
G03 mobile/.dart_tool/flutter_build — 1.241 GiB
G04 mobile/.dart_tool/hooks_runner — 0.126 GiB
G05 work/npm-cache/_cacache — 0.020 GiB

ACTIVE PROCESS CONFLICTS:
관측된 충돌 없음; 시스템 PID 255개의 fd/map_files 접근 제한

FILES DELETED:
0

FILES MODIFIED:
ONLY NEW AUDIT MANIFEST/REPORT

COMMIT:
NONE

PUSH:
NOT PERFORMED

READY FOR PHASE 2:
YES (G01–G05에 대한 별도 명시 승인과 직전 재검증 필요)

NEXT ACTION:
G01–G03의 71.313 GiB 회수 계획을 먼저 검토하고 승인할 그룹 ID를 지정한다.
```

