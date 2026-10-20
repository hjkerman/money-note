"""C1 알고리즘 변경 없이 현재 encode 호출의 실제 caller별 작업 시간을 계수한다."""

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
import json
import sys
import time
import request_cost as rc
from isolated_sync import canonical

rc.COUNT_CHOICES = [64]
rc.TRACED_CHOICES = [False, True, False, True]
original = canonical.encode


# encode의 recursive emit은 원래 함수 안에서 그대로 실행된다.
def encode(value):
    row = rc.CURRENT.get()
    if row is None:
        return original(value)
    caller = sys._getframe(1).f_code.co_name
    if caller == "decode_json":
        caller += "." + (
            "inner_c1"
            if sys._getframe(2).f_code.co_name == "decode_c1"
            else "outer_json"
        )
    t = time.perf_counter_ns()
    try:
        return original(value)
    finally:
        row["ns"]["encode_from." + caller] += time.perf_counter_ns() - t
        row["calls"]["encode_from." + caller] += 1


with ExitStack() as stack:
    stack.enter_context(patch.object(canonical, "encode", encode))
    for owner, names in [
        (rc.http.Adapter, ["credential", "prepare", "terminal"]),
        (rc.observation.ObservationRepository, ["_lookup", "_view_object"]),
        (rc.observation, ["versions"]),
        (rc.retention_schema.RetentionSandbox, ["connect"]),
        (rc.transfer.PathResolver, ["resolve"]),
    ]:
        for name in names:
            rc.instrument(stack, owner, name)
    results = [rc.run(1000)]
Path(__file__).with_name("codec-cost.json").write_text(
    json.dumps(
        {
            "scope": "실제 ASGI/auth/typed 경로; encode caller별 aggregate. 알고리즘 수정 없음. 프로파일 시간은 직접 latency 추정에서 제외",
            "results": results,
        },
        indent=2,
        ensure_ascii=False,
    )
    + "\n"
)
print("PASS codec caller measurements")
