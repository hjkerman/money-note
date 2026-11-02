# P1-02 Flutter rebuild·파생 상태 성능 결과

**DEFERRED — PROTECTED OR HIGH-RISK PATH.** baseline gate는 **C**다. 5,000행의 변경 없는 알림에서 전체 expense 필터·정렬이 매번 재실행되고 약2.27~2.49ms를 차지했다. 같은 build 안의 중복 호출은 없었다. 이 측정으로 확인한 재평가를 제거하려면 보호된 AppState의 파생 view 수명·invalidation/publication 경계를 바꾸거나 알림 사이 상태를 캐시해야 한다. 이번 범위에서는 둘 다 허용되지 않으므로 **생산 코드 수정·후보 구현·전후 비교 없이 실험을 종료**했다. 이는 새 correctness 결함이나 개발 종료의 자동 blocker 판정이 아니다.

## 기준과 도구

- HEAD: `ebcbd54d90eeee194a04b9eea6367f446ee2fd28`. 현재 working source를 사용했으며 HEAD와의 동일성을 가정하지 않았다. 시작 인덱스 SHA-256은 `56aba5ca9506287cbe6a81dd5caebc246e3519c6e84b9680f4108358d50f5595`다.
- Intel Core i7-8750H / Linux x86_64, Flutter3.47.4·Dart3.13.3 host debug JIT, 단일 worker, viewport400×800/DPR1.0이다. 전체 framework build profiling을 켜고 SDK FlutterTimeline의 실제 monotonic clock을 수집했다. release·실기기 성능 수치가 아니다.

| 소스 | SHA-256 |
| --- | --- |
| `mobile/lib/src/app.dart` | `5874a68ccc37ca4a12d3d267a84a5e6283864eb6a71f6899e6d64e5ed367b87e` |
| `mobile/lib/src/app_state.dart` | `c46a87a8b68507214a85966c3cc2c4f46df0d040de75b74e18c7954dea9d14bc` |
| `mobile/lib/src/screens/home_shell.dart` | `e2e4b53496b9950f27666377c6fae7543021cbf770ad412f31d6196b8aa4b5d4` |
| `mobile/lib/src/screens/input_screen.dart` | `0c7830d69dd1a439891b9174bdf287bbc88dbe3fe91626b2cee2b03e5dfeb17a` |
| `mobile/lib/src/screens/month_entries_screen.dart` | `f876b19c0872f533e226ab366ff45a8ce61fb0af568672aad9bdcd130cac5e81` |

기존 B03/P0 보호 규칙·worktree inventory와 실제 AppState source를 대조했다. getter 본문을 복사하지 않고 테스트 subclass에서 super 호출 횟수와 경과 시간만 측정했다. 기존 P1-01 화면과 증거는 그대로이며 P1-01 실험을 재개하지 않았다.

## 전파 지도와 계수의 의미

1. `AppState.notifyListeners → app.dart`의 root AnimatedBuilder element → builder closure → 새 MaterialApp/theme/home widget → 기존 HomeShell State의 update/build로 이어진다. SDK `ListenableBuilder.build`는 해당 closure를 한 번 호출하므로 root element build와 builder 호출을 1:1로 계수했다. MoneyNoteApp 자체 State.build가 매 알림마다 호출된다는 뜻은 아니다.
2. HomeShell은 build당 화면 widget5개를 생성한다. PageView가 실제로 mount/update한 화면의 element만 build된다. 5개 생성이라는 값은 검증한 source와 HomeShell 호출 수의 곱이며 VM heap allocation 표본이 아니다.
3. 정착 홈/당월 화면의 각 build는 expenseEntries를1회 호출한다. 해당 원문은 where→toList→sort를 각각 실행하므로 호출당 전체 필터·정렬 각1회다. currentMonth는 이 fixture의 서버 calendar_month를 사용한다. 예정 내역 getter는 이 측정 경로에서0회였다.
4. 탭 이동은 PageView의 onPageChanged→HomeShell.setState라는 별도 진입점을 가진다. 그 뒤 실제 refresh 완료 알림이 root 경로를 추가한다. 이를 모두 notify의 결과로 세지 않는다.
5. element build·위젯 생성과 layout/paint는 별개다. LAYOUT/PAINT는 host pipeline flush 구간을 따로 수집했다. 개별 RenderObject 작업 수·GPU raster 시간은 측정하지 않았다. 특히 홈 busy의 5k layout/paint flush 중앙값은 각각0.001ms로, rebuild가 전체 화면 layout/paint를 뜻하지 않음을 보여준다.

아래 계수는 **각 표본의 측정 창 안**에서 모든 규모·20개 표본에 동일했다. busy/status의 준비·성공 cleanup 알림은 창 밖이다.

| 구성 | notify | root builder | HomeShell | Home/당월/정산 element build | expense 필터·정렬 | panel 필터·정렬 | 알려진 화면 widget 생성 |
| --- | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 홈 busy/status·refresh·복귀 | 1 | 1 | 1 | 1/0/0 | 1 | 0 | 5 |
| 당월 busy/status | 1 | 1 | 1 | 0/1/0 | 1 | 0 | 5 |
| mutation+refresh | 2 | 2 | 2 | 2/0/0 | 2 | 0 | 10 |
| 연속 탭1→2→0 | 3 | 3 | 6 | 3/3/3 | 6 | 3 | 30 |

정착 상태의 inactive 탭 전체 rebuild는 관찰되지 않았다. navigation의 화면별 합계는 활성·이전 PageView element의 총 호출이며 각 호출을 활성/보존 화면으로 따로 나눈 값은 아니다. 계수와 timeline은 원시 표본에 모두 보존했다.

## 실제 시나리오와 측정 경계

- **busy:** 실제 updateExpenseCategory→_run의 busy 알림을 사용했다. test store gate로 pending 파일 생성 전 I/O 대기 창을 고정하고 pump했다. 임의 notify나 busy setter로 성능 기회를 만들지 않았다.
- **status:** 같은 실제 작업이 busy인 동안 두 번째 updateExpenseCategory를 호출해 기존 “이미 저장 중입니다.” 분기의 알림만 측정했다. 금융 데이터는 바뀌지 않는다.
- **refresh:** 사전 생성한 새 revision2 bundle을 실제 coordinator·strict parser·OfflineStore flush/readback/publication으로 받아 마지막 알림과 pump를 측정했다.
- **mutation:** 실제 category PATCH 경로의 _financialWrite→pending→새 bundle→baseline 완료를 호출하고 busy/완료 두 pump를 측정했다. API는 고정된 synthetic 응답이며 backend 금융 계산을 복제하지 않는다.
- **navigation — 부분 측정:** 기존 PageView를1→2→0으로 연속 전환하고 각 합성 refresh 완료 후 다음 탭으로 이동했다. 겹친 빠른 요청·실제 터치 animation/gesture 경로는 미측정이다.
- **foreground — host 범위:** 실제 WidgetsBindingObserver에 paused/resumed를 전달하고 AppState.resumeFromBackground의 refresh·임시 자동 Snapshot·완료 알림을 기다렸다. 실제 Android 복귀·권한/channel 지연·단말 I/O는 미측정이다.

fixture는 current expense50/500/1000/5000개, 고정 ID·2026-09-17 날짜·정렬 입력·category·표시 금액이다. 전후 fixture hash를 검증했고 fixture 생성·초기 seed와 native/API mock 준비는 측정 밖이다. API byte 응답은 사전 생성하여 네트워크 RTT는 없다. 실제 parser와 task-owned 파일 저장은 전체 전이 시간 안에 남겼다. Summary는 합성 서버 projection이며 금융 정합성 oracle가 아니다.

구성별 warmup5회+표본20회, 32구성의 측정640개와 warmup160회를 한 bounded baseline으로 수집했다(823.78초/사전900초 상한). 후보가 없어 교대 A/B3블록은 해당 없다. p95는20개 중19번째다. `pump`는 실제 tester.pump 호출들의 비중복 합, `전이`는 실제 public action 시작→대기→최종 pump까지다. getter 시간은 그 안의 동기 filter/toList/sort 경과 시간이며 독립 on-CPU 시간이 아니다. framework timeline의 widget 시간은 자식 build를 포함하는 element 구간이다. **중첩 시간들을 더해 새 end-to-end latency를 만들지 않았다.**

## baseline 시간

단위는 **ms**, 각 칸은 **중앙값/p95**다. 파생값은 expense/planned/panel 필터·정렬 구간의 합이며 작은 scalar currentMonth는 별도 원문에 남겼다.

| 행 | 구성 | 파생 필터·정렬 | 전체 pump | 전체 전이 |
| ---: | --- | --- | --- | --- |
| 50 | 홈 busy | 0.0405/0.0580 | 14.9905/19.1440 | 15.3030/19.4620 |
| 50 | 홈 status | 0.0300/0.0360 | 10.9285/12.9640 | 11.0085/13.0550 |
| 50 | 당월 busy | 0.0210/0.0340 | 20.5815/23.5950 | 20.8470/23.9480 |
| 50 | 당월 status | 0.0200/0.0380 | 16.2945/19.1990 | 16.3440/19.2530 |
| 50 | 정상 refresh | 0.0220/0.0250 | 9.5585/11.3350 | 37.3245/40.3370 |
| 50 | 분류 수정+refresh | 0.0485/0.0580 | 18.2990/21.0420 | 54.4020/66.1970 |
| 50 | 탭1→2→0 | 0.1475/0.1630 | 118.7145/134.8690 | 199.0800/214.8580 |
| 50 | host 복귀 | 0.0290/0.0360 | 18.0100/22.0610 | 61.4905/66.3620 |
| 500 | 홈 busy | 0.2230/0.2600 | 7.7245/10.2260 | 7.9075/10.4290 |
| 500 | 홈 status | 0.2155/0.2360 | 7.6925/9.7930 | 7.7440/9.8490 |
| 500 | 당월 busy | 0.1865/0.2030 | 17.2330/20.5120 | 17.4435/20.7130 |
| 500 | 당월 status | 0.1765/0.2050 | 13.7585/17.6940 | 13.8030/17.7380 |
| 500 | 정상 refresh | 0.1955/0.2440 | 10.0830/11.0680 | 210.5865/213.8000 |
| 500 | 분류 수정+refresh | 0.4260/0.4820 | 17.5525/20.4290 | 228.7190/232.1720 |
| 500 | 탭1→2→0 | 1.1495/1.2150 | 103.5035/107.4610 | 676.8325/695.6390 |
| 500 | host 복귀 | 0.1840/0.2040 | 8.6500/9.9170 | 250.4870/257.8030 |
| 1000 | 홈 busy | 0.4150/0.4880 | 7.4470/9.3050 | 7.6680/9.4850 |
| 1000 | 홈 status | 0.4205/0.4600 | 7.0325/8.8640 | 7.0850/9.6180 |
| 1000 | 당월 busy | 0.3845/0.5240 | 15.4030/16.2550 | 15.5970/16.4980 |
| 1000 | 당월 status | 0.4100/0.5050 | 13.1595/15.4150 | 13.2035/15.4590 |
| 1000 | 정상 refresh | 0.3910/0.4270 | 8.3585/10.7680 | 370.6915/400.4250 |
| 1000 | 분류 수정+refresh | 0.8480/0.8940 | 15.8125/17.8670 | 413.6460/425.2890 |
| 1000 | 탭1→2→0 | 2.7685/7.4590 | 130.8860/136.1090 | 1301.5385/1309.1890 |
| 1000 | host 복귀 | 0.4665/0.4810 | 8.7225/9.2570 | 493.2260/499.9610 |
| 5000 | 홈 busy | 2.3415/2.4530 | 9.3060/9.7370 | 9.4895/9.9110 |
| 5000 | 홈 status | 2.4900/2.5540 | 9.7350/12.3630 | 9.7925/12.4160 |
| 5000 | 당월 busy | 2.2655/2.5240 | 15.4000/21.9510 | 15.5850/22.2000 |
| 5000 | 당월 status | 2.3500/2.5030 | 16.9475/19.5260 | 16.9925/19.5670 |
| 5000 | 정상 refresh | 2.3990/2.5240 | 10.6335/10.8870 | 1912.8220/1966.2640 |
| 5000 | 분류 수정+refresh | 4.6105/4.8460 | 18.6890/19.0690 | 1685.0370/1816.6160 |
| 5000 | 탭1→2→0 | 14.2235/15.3330 | 118.5010/126.7170 | 5551.8040/6028.0730 |
| 5000 | host 복귀 | 2.4350/2.5500 | 11.3705/11.5980 | 2400.7015/2432.5910 |

## widget build 귀속과 판단

| 5k 구성 | HomeShell 포함 구간 | 실제 홈/당월 element 포함 구간 | 파생/전체 pump 비율의 중앙값 |
| --- | --- | --- | ---: |
| 홈 busy | 5.1990/5.5030 | 4.4530/4.7030 | 25.06% |
| 홈 status | 5.4455/5.7400 | 4.6970/4.8350 | 25.53% |
| 당월 busy | 9.5175/14.5370 | 8.7450/13.7580 | 14.39% |
| 당월 status | 11.0245/13.3890 | 10.2450/12.6160 | 14.21% |
| 정상 refresh | 5.5880/5.7340 | 4.7780/4.9200 | 22.38% |
| 분류 수정+refresh | 10.2250/10.5760 | 8.7545/9.0160 | 24.80% |
| 탭1→2→0 | 36.8485/39.5070 | 11.7170/12.6490 | 12.18% |
| host 복귀 | 6.2100/6.5140 | 5.3710/5.6740 | 21.52% |

50행의 변경 없는 알림은 파생 구간 중앙값0.020~0.0405ms로 작았으나, 5k에서는2.2655~2.4900ms로 커졌고 profiled pump의 약14~26%였다. 따라서 비용이 전혀 중요하지 않다는 A 판정은 선택하지 않았다. 가장 큰 C5 합계는5k navigation의14.2235ms(p95 15.333ms)이며, 전체 전이5.551804초에는 세 번의 bundle 취득·임시 저장과 여러 pump가 포함된다. 나머지를 parser 전용 CPU나 network latency로 명명하지 않는다.

**C 판정:** 같은 build 안에 재사용할 중복 중간 결과는 없고 getter는 화면 build당1회였다. 알림 사이 재평가를 없애려면 protected AppState의 파생값 invalidation/publication 계약과 관련 source-lock 변경의 별도 권한이 필요하다. UI가 직접 entries를 정렬하거나 새 cache를 둬 같은 변경을 우회하지 않았다. root의 더 작은 재빌드 경계가 독립적으로 충분한 이득을 준다는 근거도 이 측정에서 분리하지 못했으므로 추가 후보로 확대하지 않았다. 보호 경로 권한을 이번에 요청하거나 구현하지 않는다. C5의 이 비용은 선택적 성능 개선 항목으로 남기며 새 필수 금융 검증이나 formal release gate를 추가하지 않는다.

## 직접 검사와 한계

- baseline parameterized host test1건에서32구성·800회 실행(측정+warmup)의 busy/status·새 Summary·mutation identity·navigation·복귀 완료 조건과 Flutter 예외 부재를 확인했다.
- 기존 UI6/6, 기존 B03/P0/adapter 보호29/29, npm build, backend 합성 기능3/3이 통과했다. 전용 test 정적 분석도 통과했다. 생산 코드가 바뀌지 않아 별도 새 금융 감사나 전체 회귀를 열지 않았다.
- 사전 계측 준비의 VM timeline 접근·test async gate·profiling flag 정리 오류는 raw 로그에 보존했다. 최종 수집은 VM service 없이 SDK 직접 FlutterTimeline으로 완료했으며 미완결·실패 시도를 성공 표본에 합치지 않았다. 측정 후 변경한 test import/중괄호 정리는 원 측정 test와 별도 SHA로 보존했다.
- profiling과 getter 타이머 overhead, host JIT/GC·CPU 주파수·thermal·규모별 실행 순서는 독립 통제하지 않았다. root builder closure의 순수 시간, filter와 sort 각각의 exclusive CPU, heap allocation, 개별 RenderObject layout/paint 수는 미분리다.
- 실제 단말 frame pacing/GPU/heap·native lifecycle, 중첩 탭 연타, 일반 backend/API RTT와 금액 정확성은 이 결과의 보증 범위 밖이다. 기존 G2·ADB·T6.9·formal T6.6F·R1·배포 보류/차단은 그대로다. 새로운 critical 데이터 무결성·금융·보안 결함은 이 범위에서 실증되지 않았다.

기존 파일7,932개의 내용·모드와 HEAD·staged 항목·Git index SHA-256을 대조했다. 허용된 기존 로드맵·compact 근거 두 파일 외의 변경은 없었고, 기존 성능 inventory·역사 근거·순위 표와 compact 근거의 이전 값은 보존됐다. task-owned 임시 파일·symlink319개(논리 크기105,075,227바이트)를 정리했으며 기존 산출물은 삭제하지 않았다. 원시 표본·계측 코드·검사 로그는 압축 근거 파일에 남겼다.

## 근거와 재현

- [전용 test](../mobile/test/p1_02_rebuild_test.dart), [원시 표본·계측 원문·실행 로그](benchmarks/p1-02-flutter-rebuild-raw.json.gz), [기존 compact 근거의 p1_02](benchmarks/final-optimization-and-closure-evidence.json)를 사용한다. 원시 `samples`를 rows/scenario/sample로 선택하면 모든 계수·getter 시간·widget/flush 시간·API 호출 수를 확인할 수 있다.
- task-owned mobile 사본에 현재 lib/test/assets·pubspec/lock·기존 package_config/package_graph를 준비하고 `P102_OUTPUT=<새 파일> TMPDIR=<task scratch> flutter --no-version-check test --no-pub --concurrency=1 --reporter=json test/p1_02_rebuild_test.dart`를 실행한다. `P102_SMOKE=1`은50행1회씩의 사전 검사만 수행하므로 본640개 표본과 구분한다. 운영 파일·기기·ADB는 사용하지 않는다.

**다음 행동:** 남은 후보를 자동 시작하지 않고, 현재 로드맵 기준으로 1단계 종료 여부를 한 번 검토한다.
