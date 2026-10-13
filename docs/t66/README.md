# T6.6 문서 지도

규범 계약, 단계별 구현 기록, 독립 감사, 실험 자료를 단계별로 모았습니다.
단계의 상태와 현재 읽기 순서는 [프로젝트 상태](../project-state.md)를 기준으로 합니다.

| 단계 | 설계·계약 | 구현 기록 | 독립 감사 | 측정·fixture |
| --- | --- | --- | --- | --- |
| T6.6A | [payload attribution](a/t66a-payload-attribution.md) | 해당 없음 | 해당 없음 | [benchmarks](../benchmarks/t66a) |
| T6.6B | [hot/cold 설계](b/t66b-hot-cold-design.md) | 해당 없음 | 해당 없음 | [benchmarks](../benchmarks) |
| T6.6C | [delta sync protocol](c/t66c-delta-sync-protocol.md) | 해당 없음 | 해당 없음 | [protocol specimens](../specimens) |
| T6.6D | T6.6C 계약을 따름 | [implementation](d/implementation) | [audits](d/audits) | [benchmarks](../benchmarks) |
| T6.6E | T6.6C 계약을 따름 | [implementation](e/implementation) | [audits](e/audits) | [benchmarks](../benchmarks) |

각 단계 폴더는 관련 문서와 감사 결과를 담습니다. benchmark와 protocol specimen은 기존
`docs/benchmarks/`, `docs/specimens/` 경로에 유지합니다.
