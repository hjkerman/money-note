"""직접 trace/소형 실험과 단순 lease-capacity 모델을 분리한다."""

from pathlib import Path
from statistics import median
import json
import platform
import sqlite3
import subprocess
import time
import os

HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


tr = load("trace-analysis.json")
req = load("request-cost.json")
codec = load("codec-cost.json")
ren = load("renewal-cost.json")
ratios = []
for fixture in req["results"]:
    for shape in ("shared", "spread"):
        for count in (1, 8, 32, 64):
            rows = [
                r
                for r in fixture["rows"]
                if r["shape"] == shape and r["count"] == count
            ]
            ratios.append(
                median(r["wall_s"] for r in rows if r["instrumented"])
                / median(r["wall_s"] for r in rows if not r["instrumented"])
            )
codec_fraction = [
    r["trace"]["ns"]["encode_from.decode_json.inner_c1"] / r["trace"]["wall_ns"]
    for r in codec["results"][0]["rows"]
    if r["instrumented"]
]
renew = []
for n in (0, 200, 1000):
    a = [r for r in ren["results"] if r["n"] == n and not r["renew"]]
    b = [r for r in ren["results"] if r["n"] == n and r["renew"]]
    renew.append(
        {
            "n": n,
            "V": a[0]["reachable_objects"],
            "control_median_s": median(r["elapsed_us"] / 1e6 for r in a),
            "renew_median_s": median(r["elapsed_us"] / 1e6 for r in b),
            "control_work": a[0]["store_work"],
            "renew_work": b[0]["store_work"],
            "durable_at_renew": list(b[0]["attempts"].values())[1]["inserted_at_birth"],
            "first_new_request_gap_median_s": median(
                list(r["attempts"].values())[1]["before_first_new_request_us"] / 1e6
                for r in b
            ),
            "control_commit_boundary_s": median(
                r["commit_boundary_ns"] / 1e9 for r in a
            ),
            "renew_commit_boundary_s": median(r["commit_boundary_ns"] / 1e9 for r in b),
        }
    )
a = tr["100000"]["attempts"]
new = [r["new_objects"] for r in a]
gaps = [r["post_manifest_gap_s"] for r in a]
unit = (900 - gaps[2]) / new[2]
extra = 900 - gaps[0] - new[0] * unit
slope = (gaps[2] - gaps[1]) / new[1]
intercept = gaps[1] - slope * new[0]
handler_unit = a[2]["request_wall_s"]["sum"] / new[2]


def simulate(fraction, reuse):
    c = 0
    steps = []
    remaining_extra = extra
    for i in range(3):
        gap = 0 if reuse or not c else intercept + slope * c
        cost = unit - fraction * handler_unit
        capacity = max(0, (900 - gap - remaining_extra) / cost)
        added = min(400532 - c, capacity)
        elapsed = gap + remaining_extra + added * cost
        remaining_extra = 0
        c += added
        steps.append(
            {
                "attempt": i + 1,
                "renewal_gap_s": gap,
                "new_objects_estimate": added,
                "elapsed_s": elapsed,
            }
        )
        if c >= 400532:
            break
    return {
        "completed_objects_estimate": c,
        "missing_objects_estimate": 400532 - c,
        "within_three_estimate": c >= 400532,
        "wall_seconds_estimate": sum(s["elapsed_s"] for s in steps),
        "steps": steps,
    }


model = {
    "scope": "MODEL-BASED ESTIMATE; 새 product/full100k 성공 증거가 아님",
    "fixed_ttl_s": 900,
    "max_observations": 3,
    "target_objects": 400532,
    "calibration_tail_wall_s_per_new_object": unit,
    "calibration_first_attempt_extra_s": extra,
    "renewal_gap_intercept_s": intercept,
    "renewal_gap_s_per_cached_object": slope,
    "tail_handler_s_per_new_object": handler_unit,
    "assumptions": [
        "같은 Target와 작은 Patricia object tail 처리량 유지",
        "첫 raw-heavy overhead를 codec 개선 후에도 그대로 남기는 보수적 단순화",
        "codec 감소율은 microbenchmark의 실제 중복 encode 시간 share와 같다고 가정; 실제 수정 효과는 미검증",
        "same-target private traversal continuation이 재순회 gap을 제거한다고 가정; auth/manifest 검사는 제거하지 않음",
        "추가 stage/terminal guard 몇 초 및 host variance는 별도 불확실성",
        "E3/E4는 E2 terminal 후 수행되므로 observation-transfer 모델 밖",
    ],
    "scenarios": {},
}
for f in (0, 0.20, 0.25, 0.28):
    for reuse in (False, True):
        model["scenarios"][f"codec_fraction_{f}_same_target_continuation_{reuse}"] = (
            simulate(f, reuse)
        )
summary = {
    "classification": "독립 조사; 제품 교정/대형 성공 증거 아님",
    "new_request_cost_measured_responses": sum(len(v["rows"]) for v in req["results"]),
    "new_codec_measured_responses": sum(len(v["rows"]) for v in codec["results"]),
    "new_renewal_runs": len(ren["results"]),
    "actual_protocol_ttl_changed": False,
    "full_50k_rerun": False,
    "full_100k_rerun": False,
    "request_timer_overhead_ratios": ratios,
    "request_timer_overhead_median_ratio": median(ratios),
    "codec_duplicate_encode_share_of_handler": codec_fraction,
    "codec_duplicate_encode_share_median": median(codec_fraction),
    "renewal": renew,
    "limitations": [
        "client native sqlite3_sql/trace symbols 미노출; per-SQL client profile 미측정. OMIT_TRACE라고 추정하지 않음",
        "store.work는 구현 counter다; durable closure/새 insert fault/외부 clock으로 교차확인했지만 independent client SQL trace로 바꾸어 부르지 않음",
        "cProfile은 native CPU 순위용이며 absolute latency 모델에 쓰지 않음",
        "microbenchmark n0/200/1000은 backend bridge fixture, fixed-H large grid와 다른 shape다",
        "반복2회/조건; micro p95 일반화 없음",
    ],
}
(HERE / "completion-model.json").write_text(
    json.dumps(model, indent=2, ensure_ascii=False) + "\n"
)
(HERE / "summary.json").write_text(
    json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
)
env = {
    "date_utc": time.time(),
    "platform": platform.platform(),
    "python": platform.python_version(),
    "python_sqlite": sqlite3.sqlite_version,
    "cpu_count": os.cpu_count(),
    "uname": subprocess.check_output(["uname", "-a"]).decode(),
    "lscpu": subprocess.check_output(["lscpu"]).decode(),
    "proc_meminfo": Path("/proc/meminfo").read_text(),
    "proc_self_cgroup": Path("/proc/self/cgroup").read_text(),
    "disk": subprocess.check_output(["df", "-B1", "/tmp"]).decode(),
    "dart": subprocess.check_output(
        ["/home/hjkerman/.flutter/bin/dart", "--version"], stderr=subprocess.STDOUT
    ).decode(),
}
(HERE / "environment.json").write_text(
    json.dumps(env, indent=2, ensure_ascii=False) + "\n"
)
print(
    "counts",
    summary["new_request_cost_measured_responses"],
    summary["new_codec_measured_responses"],
    summary["new_renewal_runs"],
    "codec fraction",
    summary["codec_duplicate_encode_share_median"],
    "timer overhead",
    summary["request_timer_overhead_median_ratio"],
)
print(
    *[
        (k, round(v["missing_objects_estimate"]), round(v["wall_seconds_estimate"], 2))
        for k, v in model["scenarios"].items()
    ],
    sep="\n",
)
