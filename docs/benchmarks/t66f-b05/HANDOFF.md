# B05 실험 후보 인계 — 정식 채택 보류

이 후보는 `_lookup` 로컬 decode 재사용의 구현·성능 진단용이다. IR07은 원래 B03 후보에만 적용된다. 새 후보를 독립 감사 통과 또는 전체 Phase B PASS로 취급하지 않는다.

- 원본 payload: `8bd698368620394eece061f0b7b30b21172e814d2be92d153de40441a6f2a1f8`
- 새 실험 payload: `d0d9b35cefed5da51b08d77c3b7018d0a21318c0cdeb11a8418f2c1dde6232ae`
- 새 archive SHA-256: `745246e7d4bf6f945987e8043fe097e47056554d39a6e2f24d419d77f9aafe1e`
- 새 engine: `f84dacdf5da288611f32876a60766a398a830818d28fe438ccd41c4a2f8294b3`
- 제품 변경은 `backend/isolated_sync/observation.py` 한 파일의 hot 조건뿐이다. `optimization.patch`를 먼저 본다.

정상 hot 검사에서 같은 immutable raw를 두 번째 필드 검사 때문에 다시 C1 decode하던 것을 한 로컬 map으로 읽는다. constructor·namespace 검사는 그대로이며 context 불일치의 short circuit도 유지된다. map은 반환·저장·교차 요청 공유하지 않는다. B03의 parse와 canonical 재인코딩 한 회가 실제 제거되므로 primary 입력 span 감소는 정상이다. 해시 입력과 SQL 관측은 동일했다.

집중20건은 통과했다. 전체 backend는1,899 PASS/1 FAIL 및1,540 subtests PASS다. 실패는 미갱신 release artifact의 exact source hash gate다. 영향 Flutter117 PASS/41 ERROR는 새 engine의 `UNSUPPORTED_CONTRACT` 및 그 후속 정리·집계 실패를 포함한다. 기존 exact allowlist와 역사 source-lock 기대값은 손대지 않았다. **현재 후보는 엄격한 클라이언트에 입장할 수 없다.** 적용하지 않은 구체적 승인안은 `admission-proposal.json` 및 `.patch`다. 승인안은 새 exact SHA 하나만 추가하고 기존 세 SHA를 모두 보존하며 현재 artifact 두 개 및 직접 영향 테스트·새 검토 기록을 함께 다룬다. 일반적인 “continue”는 추가 파일 변경 승인으로 확장하지 않았다.

교차 순서 warm 진단은 OFF/ON 로컬 중앙값 개선15.08%/15.55%였다. 수정 N1k backend TLS 진단은 OFF7.01% 악화, ON15.65% 개선으로 일관되지 않았다. 조건당1회이며 client E2/E1/E3/E4를 실행하지 않는다. 최초 timestamp 불일치4건은 비교 무효로 분리했다. 전체 cold 이득·50k 개선·100k 가능성을 주장하지 않는다. `run-manifest.json`의 역할·유효성 필드를 따른다.

독립 후속 검토는 이 작은 diff의 decode 재사용, 오류·거부 순서, mutable alias 부재, bounded lifetime, canonical/금융 결과 동등성, 실제 줄어든 B03 span 및 측정 provenance에 집중하면 된다. 바뀌지 않은 instrumentation의 IR07 근거를 재사용하며 설치·취소 lifecycle 전체 감사를 새로 요구하지 않는다. 전체 시스템 성능·입장 자격은 아직 충족하지 않았다.

## 복원

1. 별도 빈 task scratch에 `git archive ebcbd54d90eeee194a04b9eea6367f446ee2fd28`을 푼다. 기존 dirty checkout에서 checkout/reset을 실행하지 않는다.
2. `experimental-source.tar.gz`의 `metadata/source-manifest.json`을 읽고 archive SHA 및 canonical entries payload digest를 검증한다. `experimental-freeze.json`의 tracked deletions는 빈 목록이다.
3. archive의 `source/` 이하901개 파일을 상대 경로·mode 그대로 덮어쓴다. 절대 경로와 `..`는 거부한다. 각각 SHA-256·bytes·mode를 대조한다. archive는 DB·`.env`·venv·빌드 출력을 포함하지 않는다.
4. CPython3.12.3와 기존 잠긴 의존성을 연결한다. 복원 `backend`를 `PYTHONPATH`로 지정해 `release_bundle()`의 financial engine이 위 새 exact SHA인지 검증한다. 현재 mobile artifact와 불일치는 알려진 미승인 상태이며 임의 수정하거나 이전 engine을 위조하지 않는다.
5. 집중 테스트는 `B05_EVIDENCE=<복원>/docs/benchmarks/t66f-b05`와 task 전용 `/tmp` basetemp를 지정해 `backend/tests/test_lookup_hot_body_b05.py`를 실행한다. 원 함수는 archive 안의 `lookup_before.py`다. 새 회귀/benchmark 출력은 기존 evidence를 덮어쓰지 않는 별도 task 경로를 사용한다.

실제 복원901파일의 bytes/mode와 engine 재계산은 PASS했다. 복원 workspace는 검증 후 삭제하고 source archive·manifest·원시 측정·8개 backend SQLite backup을 보존한다. backend backup은 지원되는 SQLite backup으로 만들고 quick_check 후 gzip했다. client DB는 생성하지 않았다.

backend-only 진단의 합성 시작 UTC를 실제 client cold 드라이버에 재사용하지 않는다. 그 후속 측정은 정상 실제 UTC·lease 정책으로 별도 구성해야 한다.

다음 작업은 제시한 exact engine 입장·artifact 범위를 명시적으로 승인한 뒤 N1k 실제 Flutter cold A/B부터 검증하는 것이다. N50k는 그 gate 결과를 다시 판단하고 N100k는 계속 별도 허가가 필요하다.
