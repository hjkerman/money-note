# P1-03 Snapshot 저장·목록·검증 성능 귀속 결과

**PARTIAL — B. MEASURABLE REDUNDANT WORK.** 비용 귀속은 완료했으나 초기 Flutter 자동 진단이 금지된 ADB 서버를 기동한 사실이 확인돼 전체 작업을 정상 COMPLETE로 보고하지 않는다. 저장 안의 두 전체 순회가 같은 보관 파일을 반복해서 읽고 decode·envelope 검사함을 소스와 계수로 확인했다. 비용은 크지만 필수 readback·새 취득 검증을 제거할 근거는 아니다. 아래 후보 하나만 남겼으며 **생산 변경·최적화 구현은 0개**다. P1-03 분석을 완료하고 멈춘다. 1단계 전체 종료나 운영 준비 판정은 아니다.

최종 판정: **PARTIAL — B. MEASURABLE REDUNDANT WORK; 자동 ADB 기동 경계 위반 후 종료**.

## 소스와 도구 기준

HEAD `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`과 현재 working source를 구분했다. 시작 index SHA-256은 `56aba5ca9506287cbe6a81dd5caebc246e3519c6e84b9680f4108358d50f5595`다. 기존 tracked13개 변경과 untracked 자료를 보존한다. 대상 repository는 P0 `protected-source.json`의 exact SHA와 일치하며 B03/P0 소스 잠금을 변경하지 않았다.

| 소스 | SHA-256 |
| --- | --- |
| `mobile/lib/src/local_snapshot_repository.dart` | `316c491e512873b500e5417a4b5dff4ebf8885d6a398d5a57cf63b2c28d25432` |
| `mobile/lib/src/app_state.dart` | `c46a87a8b68507214a85966c3cc2c4f46df0d040de75b74e18c7954dea9d14bc` |
| `mobile/lib/src/api_client.dart` | `2f5645a1e32971569862410aee0833c958bd65c7d8e44f0caba0d7551e91ae0b` |
| `mobile/lib/src/screens/snapshot_manager_screen.dart` | `29ce8c5acd5c959d9d235916128ba1a149a112236958ee7dd8351c70f31c27bd` |
| `mobile/test/local_snapshot_repository_test.dart` | `a9e9d41875fd7c075dae85cfb8c422eba1895740bff9fc2fa7d16e3437791652` |
| `backend/app/services/snapshot.py` | `92bba975d0c0e4776b6ef775a647009ad1de6887a36b5c0a9270ad2ba7bb5240` |
| `backend/app/routers/admin.py` | `9c934b2f09292851e48d1fdaad3e7e5cc58808c64b47e5dcf1dfacf18ce3d605` |
| `backend/app/db.py` | `378783da0a16e5af77a26e7b4534c5f210f90d49829f29ab1d4c748cae82e2c2` |
| `mobile/pubspec.lock` | `669da919f8110efd863187877d1990ead6d92dea6199ea77e3199edfce740988` |
| `docs/benchmarks/t66e4-p0-audit/protected-source.json` | `83e0c58bdc5a4f3bd16ba8753544e8bf59689d70229b4f5a88ffe1638a2153b9` |
| `docs/benchmarks/t66f-b03/source-lock-review.json` | `16412a813fd15c5f16dbf2502aee4db08140af7167084b179acb7c11dbe36ee4` |

Linux x86_64·Intel Core i7-8750H, Flutter3.47.4/Dart3.13.3, Python3.12.3, 단일 host flutter test debug JIT다. 네트워크 RTT·서버 export 시간·Android 파일시스템·단말 frame pacing은 측정하지 않았다. API·개인/운영 Snapshot·production DB·단말·에뮬레이터를 사용하지 않았다.

## 실제 호출 경로와 검증 책임

1. bootstrap/foreground 등의 `AppState.saveLaunchSnapshot`: online일 때 `api.downloadSnapshot → GET /api/admin/snapshot → LocalSnapshotRepository.save → localSnapshots 대입`이다. 자동 백업 실패는 호출부에서 포착한다. HTTP status 검사 뒤 bodyBytes를 그대로 받으며 이 별도 다운로드가 정상 authoritative bundle의 strict admission을 다시 실행하는 것으로 표현하지 않는다.
2. 서버 admin handler는 실제 exporter의 v7 전체 Snapshot을 compact JSON으로 응답한다. manifest·금융 관계·복구 가능성의 서버 검증과 로컬 파일 envelope 검사는 다른 보증이다.
3. `save`: directory 준비→하루 지난 비활성 pending 정리→고유 pending exclusive create→`writeAsBytes(flush:true)`→새 파일 readback·expectedBytes 전체 일치·UTF-8/JSON/envelope 검사→rename→`_prune`→반환용 `list`다. 두 save의 활성 pending 보호 Set은 공유되지만 저장 전체를 직렬화하지 않는다.
4. `_prune`: `list`로 final 확장자 파일을 각각 다시 읽고 검사·stat→수정 시각 내림차순→30개 초과분만 exists/delete다. 반환용 `list`가 남은 final 파일을 다시 읽고 검사·stat·정렬한다. 임의 오래된 유효 파일을 삭제하는 별도 규칙은 없다.
5. `SnapshotManagerScreen.initState/_reload → AppState.listLocalSnapshots → repository.list`다. `safeFile`도 공개 `list`를 다시 거쳐 허용 filename을 확인하고 read/share/restore/delete에 사용한다. standalone 목록과 실제 파일 선택의 새 검증은 유지해야 한다.

`_validateSnapshotFile`은 UTF-8/JSON과 schema_version의 int 형태, range/data/policy/manifest/tables 구조, content_sha256의64자 소문자 hex 형태를 검사한다. manifest hash 재계산·금융 계산·서버 복구 dry-run과 동등하지 않다. 현재 역할을 새 결함이나 강화 계약으로 확장하지 않았다. 지원 Snapshot v4~v7과 서버 최종 복원 authority를 보존한다. 성능 workload는 v7이며 이전 버전 성능은 미측정이다.

## 소스 비용 모델

B는 한 파일의 실제 byte 수, C는 기존 유효 final 파일 수, K=min(C+1,30)이다. 아래 계수는 모든 유효 workload에서 실제 계측과 일치했다. 파일 내용이 깨지거나 읽기 실패가 있으면 이 식을 일반화하지 않는다.

| C | list 읽기/decode/검증 | save 읽기/decode/검증 | save 뒤 list 읽기/decode/검증 | save 뒤 보관 수/삭제 수 |
| ---: | ---: | ---: | ---: | --- |
| 0 | 0 | 3 | 4 | 1/0 |
| 1 | 1 | 5 | 7 | 2/0 |
| 10 | 10 | 23 | 34 | 11/0 |
| 30 | 30 | 62 | 92 | 30/1 |

list는 C회, save는 `1+(C+1)+K`회, save 뒤 공개 list는 여기에 K회를 더한다. 읽은 bytes는 해당 계수×B, 쓰기는 저장 시 B 한 번이다. save의 expectedBytes 동일성 검사는1회, flush1회·rename1회다. C30에서 prune 전31개를 검사하고 가장 오래된1개를 삭제한 뒤30개를 다시 검사한다. 새 파일 readback은 독립 내구성 검사다. 모든 검사를 단순 중복으로 묶지 않는다.

파일 read/write/stat/exists/create/rename/delete는 await하는 I/O다. directory 열거 `listSync`, UTF-8 decode, JSON decode, envelope/byte 비교와 목록 정렬은 호출 isolate의 동기 작업이다. 생산 경로에 이 작업을 옮기는 compute/Isolate.run은 없다. await가 동기 decode를 background로 옮겨 주지 않는다. 크기와 보관 개수가 함께 비용을 키운다.

## fixture와 측정 경계

서버의 task-owned 새 SQLite에 고정 ID·날짜·금액·payment key·한국어/emoji 지출을 만들고 실제 export를 사용했다. 각 workload는 financial ledger rows가 정확히376/1000/5000/10000개이며 나머지 금융 관계 테이블은 비어 있다. 비민감 설정·labels·정식 policy·전체 table manifest·column metadata는 실제 export 그대로다. parser와 `validate_reconciliation_snapshot`의 임시 복구 dry-run을 모두 통과했다. 정상 backend 관계 검사를 생략하는 축약 JSON은 만들지 않았다.

| 금융 행 수 | 실제 compact payload bytes | SHA-256 |
| ---: | ---: | --- |
| 376 | 228,687 | `8ba62be0f9bbe0b5bac7e85dfc9a55b14e478d66bf45ad123db01db7c5e6749c` |
| 1000 | 597,474 | `1e28afd3b594296d25d7b26e2151323ec2dbd405d82449f182dd92e3b0221b9a` |
| 5000 | 2,969,474 | `b3adaf23dc0040c4674019abc52eed151e824fc6b360e205948c59f68a1beac5` |
| 10000 | 5,934,477 | `e51365e052efc23264a653ab44b024ec9062bb6ba15bf82a461ba13c62a645ec` |

보관0/1/10/30개의 각각에 동일 byte payload를 독립 파일로 준비했다. 기존 파일의 mtime은2020년의 고정 증가 순서, 새 저장은 실제 production timestamp/random naming을 사용해 pruning 대상은 결정적으로 가장 오래된 파일이다. 초기화·반복 전 파일 복구·fixture 생성·assert·후처리는 timer 밖이다. `save 뒤 list`는 `save`가 내부에서 반환용 list를 완료한 뒤 공개 list를 한 번 더 호출한다. `_prune`와 readback은 save 안의 중첩 구간으로 별도 계측했다.

원 생산 파일은 수정하지 않았다. 임시 사본에 가역적인 timer/counter만 삽입해 JSON/UTF-8·동기 검증·list/prune/readback을 계측했고, 역치환하면 원 exact source로 복원됨을 확인했다. IOOverrides의 실제 File/Directory delegate로 read/write bytes·호출 수·await 시간을 센다. Dart SDK의 `readAsBytes→open`과 `writeAsBytes→open`에 따라 논리 read/write open을1:1로 센다. create/exclusive 호출·metadata/directory 작업은 별도 계수다. **OS syscall open 수, physical disk I/O나 page-cache miss 수는 계측하지 않았다.**

사전 보기용 JSON에서는1만 행·30개 목록 약5초·저장 약10.5초여서5 warmup+20표본 전체 설계는 약1750초로 추정했다. 서버 handler의 compact serializer와 맞춘 최종 fixture로 고정한 뒤 **48구성 각각 warmup1+측정3**, 추가 원 소스 무계측 대조4구성 각각 warmup1+측정2를 수행했다. 최종 측정은152표본·warmup52회이며 실행 시간은265.180초, 본 측정 soft480초/hard540초 안이다. n=3의 nearest-rank p95는 **최댓값**으로 tail 추정력이 낮다. 표본 수를 사후 늘리거나 유리한 표본만 고르지 않았다.

초기 package root 설정 오류와 보기용 JSON 사전 측정·compact 전 중단 수집은 준비 기록으로 보존하며 최종 표에 합치지 않았다. 초기 Flutter 도구 crash reporting의 자동 doctor 요약에는 Linux desktop만 표시됐지만, 종료 전 프로세스 확인에서 실제 `adb -L tcp:5037 fork-server server --reply-fd 4` PID434154 자동 기동을 확인했다. 이는 이 작업의 ADB 금지 경계 위반이다. 생성 시각이 작업 기준선 뒤이고 cwd·stdout/stderr가 이 작업 임시 경로임을 확인했다. 종료 직전 연결된 TCP 세션과 열린 USB 기기 파일은 없었으며, 해당 작업 소유 PID만 OS SIGTERM으로 종료했다. 정리에는 별도의 ADB 명령이나 일반 kill-server를 사용하지 않았다. 초기 전 기간의 USB/네트워크 탐색을 역으로 보증하지 않는다. 기기 성능 시험·명시 운영 dispatch는 없었고 기존 차단을 유지한다. 원시 근거에 프로세스·연결·정리 기록을 보존한다. 최종 비교는 최적화 A/B가 아니므로 교대3블록·개선율·채택 판정은 적용하지 않는다.

## 작업별 전체 시간

단위 ms, **중앙값/p95(소표본 최댓값)**다. 같은 행 수에서도 실제 파일 수가 달라지며 반환 목록은 실제 검사한 유효 final 파일만 포함한다.

| 금융 행 수 | 시작 보관 수 | list | save | save 뒤 list |
| ---: | ---: | ---: | ---: | ---: |
| 376 | 0 | 0.250/0.306 | 21.529/26.994 | 25.417/27.948 |
| 376 | 1 | 7.531/8.191 | 28.899/30.060 | 39.229/43.850 |
| 376 | 10 | 45.464/50.369 | 121.786/123.766 | 171.403/174.062 |
| 376 | 30 | 157.761/157.965 | 329.298/330.599 | 485.709/489.417 |
| 1000 | 0 | 0.161/0.179 | 45.059/49.558 | 56.161/61.568 |
| 1000 | 1 | 14.203/15.684 | 73.279/75.010 | 98.200/100.541 |
| 1000 | 10 | 132.576/133.900 | 306.818/308.618 | 420.879/429.233 |
| 1000 | 30 | 346.389/353.727 | 729.039/736.370 | 1197.774/1200.226 |
| 5000 | 0 | 0.146/0.149 | 194.076/195.385 | 252.885/253.992 |
| 5000 | 1 | 61.404/61.850 | 314.784/319.370 | 432.701/439.803 |
| 5000 | 10 | 598.269/599.081 | 1391.929/1393.381 | 2051.163/2055.393 |
| 5000 | 30 | 1798.264/1800.883 | 3340.941/3633.698 | 4915.490/5184.420 |
| 10000 | 0 | 0.141/0.152 | 397.298/415.171 | 524.918/526.895 |
| 10000 | 1 | 124.942/129.611 | 727.989/734.847 | 890.712/906.360 |
| 10000 | 10 | 1230.350/1236.869 | 2871.318/2874.560 | 4235.607/4629.397 |
| 10000 | 30 | 4199.247/4214.044 | 7866.068/7886.011 | 11566.156/12221.840 |

## 1만 행·30개 비용 귀속

| 작업 | 읽기=논리 read open=decode=검증 | 읽은 bytes | 쓴 bytes | 동기 검증 누계 ms | 그중 JSON decode ms | 그중 UTF-8 ms | read await 누계 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 목록 | 30 | 178,034,310 | 0 | 4044.729 | 3161.719 | 881.804 | 148.369 |
| 저장 | 62 | 367,937,574 | 5,934,477 | 7517.904 | 5768.683 | 1720.726 | 322.071 |
| 저장 뒤 목록 | 92 | 545,971,884 | 5,934,477 | 11056.489 | 8529.386 | 2553.820 | 462.926 |

이 표의 시간은 각 누계의 중앙값이다. JSON/UTF-8 시간은 동기 검증 안에 있고, readback/list/prune도 전체 save 안에 있다. **서로 중첩하는 수치를 합해 end-to-end latency를 만들지 않는다.** 동기 검증은 Stopwatch 경과 시간이며 독립적인 exclusive CPU 샘플러가 아니다. test isolate에서 관찰한 동기 작업의 합이고 await 사이에 나뉘므로 단일 연속 frame block이나 실제 Android UI 정지 시간으로 환산하지 않는다.

새 파일 readback 중앙값은140.065ms, prune 포함 구간은3928.529ms, write/flush await는6.890ms였다. 후속 반환용 순회가 이 readback의 독립 쓰기 확인을 대신하는 것은 아니다. 모든 sync 시간은 계측 overhead를 포함한다.

최대·최소 payload의 현재 원 소스 무계측 대조는 다음과 같다. 순서를 교대한 성능 비교가 아니며 JIT/GC/thermal·run 순서 차이가 있어 계측 overhead를 정밀 보정하지 않는다. 최적화 효과는 주장하지 않는다.

| 행 수 | 작업(C30) | 계측 중앙값 ms(n3) | 원 소스 중앙값 ms(n2) |
| ---: | --- | ---: | ---: |
| 376 | list | 157.761 | 139.213 |
| 376 | save | 329.298 | 283.836 |
| 10000 | list | 4199.247 | 3740.938 |
| 10000 | save | 7866.068 | 8515.344 |

## B 판정과 유일한 후속 후보

**후보 하나: save 안에서 prune용 전체 검증을 마친 생존 파일 목록을 반환에 재사용해, 반환만을 위한 두 번째 전체 list 순회를 줄이는 것.** 새 pending의 readback·byte 동등성·flush·rename, 첫 전체 파일 검증과 retention30, standalone `list`와 `safeFile`의 실제 재검증은 그대로 둔다. 두 번째 순회에는 별도 write flush나 서버 admission이 없으며, 동일 파일을 다시 해석해 반환 metadata를 구성한다. 따라서 측정 가능한 반복 작업 후보 B로 분류했다. 모든 JSON 검증이 불필요하다는 뜻은 아니다.

예상 작업 감소는 C30 저장의62회 중 최대30회 read/decode, C10의23회 중 최대11회다. 이는 소스의 count 상한이고 실제 latency 개선율이 아니다. 원시 표본에 list 단계와 decode 비용이 있으나 최적화 실행 전 이득을 확정하지 않는다.

이 재사용이 안전하려면 동일 저장 안에서 재사용한 파일 identity·내용·mtime과 동시 삭제/저장 관측을 보존해야 한다. `_activeTemporaryPaths`만으로 동시 repository save/delete·외부 파일 변경을 배제할 수 없다. 이 보장이 없으면 마지막 재관측이 독립 의미를 가질 수 있어 단순히 두 번째 list를 지울 수 없다. 동시 변경/손상 시 새 검증으로 돌아가거나 후보를 포기해야 한다. metadata만으로 검증을 대체하거나 TTL·세대 간 cache를 두지 않는다. 현재 근거는 안전한 제거 구현이 증명됐다는 판정이 아니다.

예상 수정 범위는 **보호된 `local_snapshot_repository.dart`의 save/_prune 반환 경계 한 곳**이다. 별도 source-lock·구현 권한과 동시성/무결성 보존 설계가 필요하며 AppState·금융·Offline·authoritative admission을 변경하지 않는다. 권한과 보증이 충족되지 않으면 위험 대비 이득이 작은 후보로 보류할 수 있다. 새 Snapshot transport/storage architecture나 후속 확장성 과제를 열지 않는다.

향후 승인된 비교는 같은16조합·byte fixture로 원본/후보 교대 블록을 예산 내 계획하고 read/decode 감소와 전체 save latency를 함께 확인해야 한다. 필수 회귀는 중단/부분 write·readback 불일치·invalid JSON/손상 final·가장 오래된 prune·30개 보존·active pending과 stale cleanup·동시 두 repository save/delete·재시작·share/restore filename 선택이다. 동시 손상·변경 시 stale 결과 재사용이 없는지도 확인해야 한다. 혼재한 결과나 안전 보증 부족이면 미채택한다. **이번에는 구현·비교를 시작하지 않는다.**

## 집중 검사·보존·한계

기존 Snapshot 회귀7/7(30개 보존·잘못된 경로·부분 write·invalid 파일·stale pending·동시 active pending·cleanup 실패), 보호 소스 검사23/23, backend 합성 authoritative-state 회귀3/3, 네 fixture의 서버 parser·dry-run 복구 검증, npm build가 통과했다. 최종 parameterized benchmark1건도 모든 계수·보관 수·prune 대상·pending 부재 assertion을 통과했다. 웹 최초 임시 사본에는 backend fixture 상대경로가 빠져 빌드가 실패했고, 사본 레이아웃만 맞춘 뒤 통과했다. 생산 변경이 없어 새 금융 감사나 광범위 회귀를 열지 않았다. 새로운 치명적 금융/보안/영속 상태 결함을 이 범위에서 실증하지 않았다. 포괄적 correctness 감사는4단계에 남긴다.

합성 payload는 원장 위주의 유효 v7이며 실제 여러 관계·archive·정책 이력 조합의 분포를 대표하지 않는다. OS cache를 비우거나 CPU/thermal/GC를 통제하지 않았고 개인 파일·저장 공간 압박·cold disk는 측정하지 않았다. network/download와 서버 export는 비용에서 제외됐다. 필수 readback·손상 탐지·호환성 검증을 희생할 근거는 없다. 실기기·에뮬레이터·G2 채택·ADB·T6.9 정량·formal T6.6F·R1·배포 경계는 그대로다.

기존 파일7,935개의 내용·mode·symlink를 대조해 허용된 로드맵 외 변경0개를 확인했고 HEAD·staged 항목·index SHA도 동일했다. 이전 성능 지도·역사 근거·순위 표는 byte 동일하다. 자동 기동한 작업 소유 ADB PID 종료와 활성 프로세스 부재를 확인한 뒤 task-owned 임시 파일/symlink377개(논리 크기256,196,100B, 관찰 할당량257,011,712B)를 정리했다. 고유 표본·계측 코드·검사/오류 기록은 압축 근거에 보존했고 ADB 임시 로그는 byte 수·SHA를 보존했다. 기존 파일·cache·DB/WAL·symlink 대상은 삭제하지 않았다.

## 근거와 재현

[단일 압축 근거](benchmarks/p1-03-snapshot-performance.json.gz)에152개 원시 표본,48구성 요약과4개 무계측 대조, 실제 fixture bytes·hash, 가역 계측 patch·원문·실행 harness·fixture 생성기·도구 버전·검사 로그를 함께 보존한다. `main.samples`의 rows/retained/op/traced/sample로 선택하며 summary의 raw_sample_indices로 대응한다. 각 표본에는 before/after/pruned와 read/open/decode/validation/byte/metadata 계수가 있다.

재현 시 압축 근거에서 합성 payload와 test용 소스·plan을 새 task-owned 임시 mobile 사본에 복원하고, 기존 dependency 설정을 해당 사본으로 맞춘다. `P103_SCRATCH=<새 임시 경로> P103_PHASE=main TMPDIR=<같은 경로> flutter --no-version-check --suppress-analytics test --no-pub --concurrency=1 --reporter=json test/p103_benchmark_test.dart`를 실행한다. 필요 경로·명령·SHA는 근거의 reproduction에 남긴다. 이 명령만으로 ADB 비실행이 보장되지는 않는다. 초기 오류의 자동 doctor 기동 이력 때문에 기기 탐색이 차단된 별도 허용 환경 없이 재실행하지 않는다. 이번에 새 device-gate 구현이나 예외를 만들지는 않았다.

**다음 행동:** 소유자가 자동 ADB 기동·정리 기록을 포함한 P1-03 결과를 검토하고 P1-04 실행 승인 여부를 결정한다.
