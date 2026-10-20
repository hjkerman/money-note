# T6.6F-B02 명시적 대형 검증 profile — 구현측 증거

시작 commit은 `6282c1c3577c42bba9382d786745d583a5d88236`이다. 원
`../t66f-b02/` 조사·Phase B 감사 파일을 수정하지 않는다. 운영 DB/API/credential,
서비스, production configuration은 대상이 아니다. 모든 DB는 새 disposable directory다.

## 선택과 예산

`verification_profile.dart`는 이 검증 harness의 구성이다. 앱에서 import하지 않는다.
E1의 기존 `ClientStoreLimits`로 objectCount=500000, metadataBytes=384 MiB만 지정하고,
E2의 새 `FetchLimits.largeGraphVerification()`을 명시한다. AppState의 기존
`publishSegmentedForIsolatedUse`에만 `verificationLimits`를 전달한다. 원 ticket, coordinator,
session 및 final guard/COMMIT 경계를 재사용한다. 일반 startup/refresh·E4 legacy install은
이 profile을 선택하지 않는다. 원 E1 100000/32 MiB, E2 100000/200000 및 나머지 예산은 불변이다.

대형 profile의 최대값은 objects500000/edges1000000이다. 조사에서 관찰한 최대
V400532/E400528, G1+G2 union400558에 유한 여유를 둔다. Edge/object ceiling 비율2는
원 200000/100000과 같다. Metadata384 MiB는 100k graph의 약282 MB cold core charge와
추가 observation 두 번의 stage link charge 약102.5 MB를 수용한다. 모든500k graph가
동시에 이 metadata/payload/page 예산에 들어간다는 약속이 아니다. 각 guard를 독립 적용한다.
개별 object64 MiB/payload512 MiB/manifest8 MiB/pages262144/staging128/busy1000ms,
chunk1 MiB/path512/C1 depth128/attempts3/observations3는 바꾸지 않는다.
RSS/heap hard quota를 새로 구현하지 않았으며 Android 안전 한도로 해석하지 않는다.

## 실제 cold 실행

새 출력 directory에서 root 및 `mobile/` cwd를 구별한다. `$B02_OUT`은 전용 disposable
경로의 예시 변수이며 서버는 그 아래 `server`가 이미 존재하면 시작을 거부한다.

```bash
mkdir -p /tmp/mn-b02-example/n50000
cd mobile
/home/hjkerman/.flutter/bin/flutter test --no-pub --machine \
  --dart-define=B02_N=50000 \
  --dart-define=B02_OUT=/tmp/mn-b02-example/n50000 \
  --dart-define=B02_COMPLETE_PLAN=true \
  ../docs/benchmarks/t66f-b02-implementation/large_http_test.dart
```

100k는 별도의 새 directory와 `B02_N=100000`을 사용한다. backend는 기존 seed662602,
current105/H, 평가 context2026-10-05를 그대로 사용한다. Bootstrap/finalizer와 실제
`isolated_sync.http.create_app`을 loopback TLS로 실행한다. Lease/auth clock은 실제 시간이며
900초 lease를 고정하거나 늘리지 않는다. TLS 인증서 예외는 이 합성 listener의 정확한
loopback host/port 하나에만 적용한다. 합성 bearer는 private stdin/stdout으로만 전달하고
증거 파일에 저장하지 않는다. `.pem`·DB는 Git 증거에 넣지 않는다.

독립 backend SQL/SHA walker가 정확한11-table row 수, V/E/bytes/height/kind를 확인한다.
새 E1 store는 비어 있으며 backend 객체 BLOB를 복사하지 않는다. 실제 observation/manifest,
typed objects/release HTTP → E2 → E1 → original-ticket E3 → E4 read 순서다.
어느 단계라도 실패하면 전체 cold PASS가 아니며, graph/cache 조각을 accepted로 취급하지 않는다.
실패 시 legacy B/pending byte checksum과 accepted/receipt/pin 상태를 직접 확인한다.
`B02_COMPLETE_PLAN=true`는 cold 성공 뒤 identical/one-row/multiple/restart delta까지 진행한다.
현재 보존된 `bounded50000`/`bounded100000` 실행은 그 계획을 추가하기 전의 cold-only harness다.
실제 large cold가 실패하면 뒤의 delta를 수행한 것으로 세지 않는다. `complete1000`은 이 전체
계획의 작은 실동작 확인이며 필수 두 large grid point를 대체하지 않는다.

```bash
/home/hjkerman/.flutter/bin/dart \
  --packages=mobile/.dart_tool/package_config.json \
  docs/benchmarks/t66f-b02-implementation/reopen.dart /tmp/mn-b02-example/n50000
.venv/bin/python docs/benchmarks/t66f-b02-implementation/collect.py /tmp/mn-b02-example
```

`reopen.dart`는 별도 프로세스에서 실제 E1 open/recovery/hash-on-read를 실행한다. 허위 accepted
metadata를 넣지 않는다. 실패한 cold의 fresh-process 안전한 staged cache 확인을 성공한 대형
accepted generation의 restart 증거로 바꾸지 않는다.

## 측정 의미와 한계

`server.py`의 counters는 실제 ASGI 요청/entity·decoded chunk bytes다. TLS/TCP framing,
physical network bytes, hash/validation 논리 bytes와 같지 않다. 객체별 로그를 무한 보유하지 않고
유한 counter와 주기적 snapshot만 남긴다. `store.work`는 기존 제품 operation instrumentation이며
독립 SQLite statement/VM instruction 계수라고 부르지 않는다. 별도 SQLite 연결은 실제 usage,
accepted/receipt/pins/FK/DB 크기를 관찰한다. Physical writes/rollback journal peak는 미검증이다.
`ProcessInfo.maxRss`와 주기적 RSS는 host client process 값이며 Dart pure heap 측정은 아니다.
Bootstrap/backend와 Flutter full/backend full 회귀 일부가 같은 host에서 겹치므로 latency는
무부하 median/p95 또는 기기 성능으로 제시하지 않는다.

HASH/VALIDATE/WRITE 논리 byte campaign은 여기서 새로 완성하지 않는다. Canonical 총합,
전송 bytes, `verified_bytes`, DB 파일 증가를 임의로 그 세 counter로 치환하지 않는다.
원 E3 I25·E4 Frozen-B/A01/RA01·P0·frozen B/J 회귀는 별도로 기록한다. R1 gate는 CLOSED다.
이 증거는 독립 targeted audit나 전체 Phase B PASS가 아니다.

## 실행 순서와 보존된 실패

`evidence/n50000`, `evidence/n100000`은 profile-only 실행의 첫 실제900초 만료 및 그 뒤
의도적 client SIGKILL/reopen 기록이다. Exit79를 정상 acquisition retry 소진으로 해석하지 않는다.
그 실패 뒤에만 기존64-item/1 MiB packet과 같은 크기의 E1 atomic object/progress batch를
추가했다. `evidence/bounded50000`, `evidence/bounded100000`은 그 후속 실험이다. 동일
complete closure/hash/type/F(raw)/hot/raw/session 검사와900초 lease/유한3 observations를 유지했다.
`evidence/complete1000`은 real cold/identical/deltas/별도 process reopen을 성공한 작은 graph다.

새 unit/authority/SIGKILL tests의 최종 결과와 초기 oracle 실수의 실패 로그를 함께 보존한다.
기존 전체 회귀의 source-SHA assertion 실패도 제외하지 않는다. Product source diff는
`app_state.dart`, `fetch.dart`, `store.dart` 세 파일뿐이며 원 protocol/financial/P0/E4 source와
모든 기존 test/fixture/report의 SHA 동일성은 `evidence/preservation.json`에 기록한다.
수집기는 허용된 JSON/log만 복사하며 bearer, TLS private key, SQLite DB, APK는 넣지 않는다.
