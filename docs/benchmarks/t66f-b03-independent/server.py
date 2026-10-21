"""B03 TLS 서버의 실제 native SHA/parser 입력을 별도 oracle로 관찰한다.

기존 delegate를 한 번 호출하고 byte span만 합산한다. 추가 hash/parse는 없다.
"""

from collections import Counter
import functools
import importlib.util
from pathlib import Path
import sys
from threading import Lock
from weakref import WeakKeyDictionary

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "t66f-b03"))
spec = importlib.util.spec_from_file_location(
    "independent_tls_subject", HERE.parent / "t66f-b03/server.py"
)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
import counters as cost  # noqa: E402
from isolated_sync import canonical  # noqa: E402

native_sha, native_parse = cost.NATIVE_HASH, canonical._parse_json
observations, lock = WeakKeyDictionary(), Lock()


def add(owner, key, value):
    if owner is None:
        return
    collector, stage = owner
    with lock:
        if collector not in observations:
            observations[collector] = Counter()
        observations[collector][f"{stage}/{key}"] += value


class NativeWitness:
    def __init__(self, data=b"", **kwargs):
        self.inner = native_sha(data, **kwargs)
        self.owner = cost.ACTIVE.get()
        self.purpose = "audit_" + cost.HASH_PURPOSE.get()
        add(self.owner, f"{self.purpose}/calls", 1)
        add(self.owner, f"{self.purpose}/hash_input_bytes", memoryview(data).nbytes)

    def update(self, raw):
        self.inner.update(raw)
        add(self.owner, f"{self.purpose}/hash_input_bytes", memoryview(raw).nbytes)

    def copy(self):
        other = object.__new__(NativeWitness)
        other.inner, other.owner, other.purpose = (
            self.inner.copy(),
            self.owner,
            self.purpose,
        )
        return other

    def __getattr__(self, name):
        return getattr(self.inner, name)


@functools.wraps(native_parse)
def parse(raw):
    owner = cost.ACTIVE.get()
    span = len(raw) if type(raw) is bytes else 0
    add(owner, "audit_json/calls", 1)
    add(owner, "audit_json/submitted_bytes", span)
    try:
        result = native_parse(raw)
    except BaseException:
        add(owner, "audit_json/failed_submitted_bytes", span)
        raise
    add(owner, "audit_json/completed_bytes", span)
    return result


snapshot = cost.Collector.snapshot


def witnessed_snapshot(self):
    result = snapshot(self)
    with lock:
        for key, amount in observations.get(self, {}).items():
            result[key] = str(amount)
    return result


if __name__ == "__main__":
    cost.NATIVE_HASH = NativeWitness
    canonical._parse_json = parse
    cost.Collector.snapshot = witnessed_snapshot
    subject.main()
