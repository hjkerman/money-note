# B05-A 집중 독립 인계

판정은 **PASS — ADMISSION AND REAL-PATH QUALIFICATION COMPLETE**다. 모든 모드·규모의 성능 이득을 입증한 판정이 아니다. N1k OFF/ON 중앙값은5.75%/5.15% 감소했고 N5k OFF는7.12% 감소했으나 N5k ON은0.38% 증가했다. N50k는 현재 권고하지 않으며 N100k NO-GO를 유지한다. production은 허가되지 않았다.

정확한 source:

- 원 B03 payload `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`, baseline engine `7ad114bc3ca9c06f56ffca2c5efdc9a026a665feada99ece7c90cdf0d0208d6c`.
- 원 B05 payload `d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae`, engine `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`.
- 새 B05-A payload `29bef95314c24d3f573328aaf60f5e7cc2987824e7ff39f35bfea4a2b38e3542`, 같은 optimized engine `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`.
- 새 archive SHA `b239b9d277e5fd747c2f85c5577f42e203ad7a737b29317f0e23581d6b13b0f1`.
- current release JSON 두 개의 SHA `8a2734c48f9355ba8930f75cf779d0da7c8fcdd19f297a8c3f78004e653da092`.

payload digest를 engine allowlist에 넣지 않았다. backend의 actual source SHA map을 stdlib JSON C1로 독립 구성하고 product `engine_artifact()` bytes와 일치시켰다. 입력은 backend/app의 Python, isolated_sync의 Python, judgment message YAML다. 두 source 사이 바뀐 engine 입력은 observation.py 하나이며 `_lookup` 재사용 자체는 B05-A에서 손대지 않았다.

`admission.patch`는 exact SHA 하나 추가 및 old3 유지, current artifact2개, 직접 source-lock 테스트 전이만 다룬다. `source-lock-review.json`은 변경된 두 fragment를 원복했을 때 이전 protocol SHA와 같다는 증거다. 역사 review와 일곱 보호 source, B03 instrumentation을 변경하지 않았다. unknown·1문자 변조·변조 source manifest·B05 payload hash를 engine으로 넣는 경우는 거부됐다.

집중 backend25 PASS, 전체 backend1904 PASS/1540 subtests PASS, 영향 Flutter205 PASS다. B05의 이전41실패 이름 모두 현재 통과했다. 이전 raw는 입장40건·집계1건과 같은 사례의 후속 teardown35 event로 분류했고 수정 전 N16 최소 재현도 실제 UNSUPPORTED_CONTRACT였다. 독립 기능 회귀가 남았다고 관측하지 않았다.

실제 Flutter N1k8건/N5k4건이 E2/E1→실제 AppState E3→bounded E4 accepted read를 완료했다. UI/Offline-ready installation을 측정한 것은 아니다. 공통 template을 독립 SQLite backup으로 복제해 client는 모두 objects0/current null/sequence0에서 시작했다. 두 engine의 view는 API로 미리 만들었고 control 시각 정렬은 준비 중에만 사용했다. 실제 server는 기본 utc_now,900초/3attempt다. 원래 ROOT/financial raw와 engine별 hot만으로 일관된 target을 만들었다. 실제 새로운 lease를 발급받으며 만료·renewal은 없었다.

후속 검토는 exact admission diff, `_lookup` 로컬 map의 읽기 전용·오류 순서·수명, canonical 결과, 실제 줄어든 backend primary span, matched DB와 측정 provenance에 집중한다. 원래 B03 IR07은 원 source에서 CLOSED다. 새 source를 독립 IR07 통과라고 하지 않으며 설치·취소 전체 lifecycle 감사를 반복할 필요는 없다.

## 측정 해석

E2는 initial recovery를 포함한 시작부터 terminal release 후 첫 E3 metadata SQL까지의 envelope다. exact acquire API 단독 시간으로 표현하지 않는다. E1 SQL API는 E2/E3에 포함된다. E3 native transaction/readback은 원 product의 값이며 별도 E3 envelope도 기록했다. handler/lookup/hot decode/HTTP는 겹쳐서 합산할 수 없다. 전체 semantic/graph oracle는 primary timing과 collector close 뒤 실행했다. client CPU tick은 후속 검증까지 포함하므로 primary CPU 비교에 사용하지 않는다. peak RSS도 이전 repetition·검증을 포함하는 process 값이다.

N5k ON에서 handler는100.496→94.166초로 감소했지만 SQL API는19.533→25.315초로 늘었다. 이것은 동반 관측이며 SQL observer CPU나 fsync가 단독 원인이라는 증거가 아니다. singleton·JIT/cache·host 변동 한계 때문에 N50k보다 **같은 동결 source의 N5k ON A/B를 반대 순서로 한 쌍 독립 재현**하는 것이 다음 작은 작업이다. 유리한 결과를 얻으려 이번 계획12건을 추가 반복하지 않았다.

## 복원과 증거

새 snapshot은 freeze.json 경로의 source-only archive다. 빈 task scratch에 baseline commit을 git archive로 풀고 source905개를 mode대로 적용한다. tracked deletion은0이다. 파일 SHA/bytes/mode와 canonical entries digest를 검증한다. 나머지 baseline2010파일의 Git blob/exec mode도 대조했다. 실제 복원에서 release_bundle이 두 JSON과 같고 engine이 f84dac…94b3임을 확인했다. venv/build/DB/.env는 source archive에 없다.

source-lock-review.json 및 mutation-witness.json도 payload에 포함한다. `_lookup` 테스트의 B05_EVIDENCE는 복원 docs/benchmarks/t66f-b05를 가리키게 한다. 실험 driver와 원시 결과는 B05-A evidence의 SHA256SUMS로 고정한다. 재실행은 독립 task 출력 경로를 사용하며 기존 plan/raw를 덮어쓰지 않는다. 경로 수정이 필요하면 path-only adapter와 그 diff를 보존한다.

run-manifest.json과 timing-comparison.json이12개의 개인 실행·순서·source/client/fixture digest·성공 scope·accepted UUID·시간을 연결한다. 각 raw 디렉터리의 independent-verification.json 및 client/backend-consistent.sqlite.gz가 matched evidence다. 실제 E4 raw row/financial state와 별도 Python oracle가 일치하고 native accepted pointer도 확인했다. OFF 비용 counter를0으로 만들지 않았다. ON은 objects committed BLOB이 actual body bytes와 같고 backend primary span만 lookup당87,364B 줄었다. SQL committed metric은 원 helper의 metric/committed 키 순서를 따라 추출했다. B03 source를 수정한 것이 아니다.
