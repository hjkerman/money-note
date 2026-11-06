"""실제 표본 통계와 비증명 projection을 명시적으로 분리한다."""

import json
from pathlib import Path
import statistics

HERE = Path(__file__).resolve().parent
OUT = HERE / "evidence"


def distribution(values):
    return {
        "count": len(values),
        "median": statistics.median(values),
        "max": max(values),
        **({"p95": sorted(values)[18]} if len(values) == 20 else {}),
    }


def main():
    python = json.loads(
        (
            HERE / "sealed-overhead/evidence/overhead-independent-python-complete.json"
        ).read_text()
    )
    flutter = json.loads(
        (OUT / "overhead-independent-flutter-complete.json").read_text()
    )
    sample = json.loads((OUT / "high-n-sample-result.json").read_text())
    http = json.loads((OUT / "independent-real-http.json").read_text())
    summary = {}
    for runtime, raw, keys, scale in [
        (
            "python",
            python,
            ["primitive_wall_ns", "primitive_cpu_ns", "sql_wall_ns", "sql_cpu_ns"],
            1e6,
        ),
        ("flutter", flutter, ["primitive_us", "sql_us"], 1e3),
    ]:
        summary[runtime] = {
            label: {
                mode: {
                    key.rsplit("_", 1)[0] + "_ms": distribution(
                        [v[key] / scale for v in values]
                    )
                    for key in keys
                }
                for mode, values in r["samples"].items()
            }
            for label, r in raw["results"].items()
        }
        summary[runtime]["max_rss_bytes"] = raw["maxrss_bytes"]
    samples = {
        "enabled" if enabled else "disabled": distribution(
            [
                s["microseconds"] / 1e6
                for s in sample["samples"]
                if s["enabled"] == enabled
            ]
        )
        for enabled in [False, True]
    }
    extra = samples["enabled"]["median"] - samples["disabled"]["median"]
    value = {
        "schema_version": 1,
        "unit_small_medium": "milliseconds",
        "direct_observation": summary,
        "actual_high_n_e1_sample": {
            "objects": sample["objects"],
            "canonical_bytes": sample["payload_bytes"],
            "distribution": sample["distribution"],
            "seconds": samples,
            "extra_median_seconds": extra,
            "max_rss_bytes": sample["max_rss_bytes"],
            "counter_keys_enabled": max(len(s["sql"]) for s in sample["samples"]),
        },
        "single_small_real_http_pair": {
            k: {"cold_seconds": http[k]["cold_wall_us"] / 1e6}
            for k in ["disabled", "enabled"]
        },
        "historical_b02_independent_100k": {
            "objects": 400532,
            "observation_new_objects": [140256, 161152, 99124],
            "terminal_seconds": 2463.561,
            "third_observation_last_object_remaining_seconds": 236.81,
            "source": "docs/t66f-b02-independent-targeted-audit.md §18",
        },
        "analytical_estimate_not_observed_100k": {
            "mechanical_linear_extra_e1_seconds": extra / sample["objects"] * 400532,
            "assumptions": [
                "2061개 표본의 per-object E1 overhead가 모든 400532개에 동일하다는 검증되지 않은 가정",
                "backend D3/HTTP 및 E2 closure/renewal 비용은 이 환산에 포함되지 않음",
                "표본은 100k의 전 객체가 아니며 종류별 분포도 원 full graph와 다름",
                "관측 만료 후 frontier 재사용·새 request 인가·phase별 진행은 단순 2700초 합산으로 검증할 수 없음",
            ],
            "interpretation": "상당한 lease 교란 위험. PASS나 실제 OBSERVATION_EXPIRED의 증거는 아님",
        },
        "lease_readiness": "INCONCLUSIVE",
        "missing_experiment": "동일 100k 실제 D3→E2→E1 경로의 활성 계측으로 관측별 전송/잔여시간·reuse·완결 snapshot을 확인할 유한 실행. 단위/표본 결과만으로 준비도 PASS 금지",
        "full_grid": "NOT RUN — independent Phase B pending",
    }
    (OUT / "performance-summary.json").write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {"high_n_sample": value["actual_high_n_e1_sample"], "lease": "INCONCLUSIVE"}
        )
    )


if __name__ == "__main__":
    main()
