"""Backend C1 sink와 제한된 INSERT 관측기. 전층 비용 계측기가 아니다."""

from collections import Counter
from contextlib import contextmanager
import hashlib
import re
import sqlite3
import threading
from types import SimpleNamespace
from unittest.mock import patch

from isolated_sync import canonical


class Counters:
    def __init__(self):
        self.values = Counter()
        self.lock = threading.Lock()

    def add(self, **values):
        with self.lock:
            self.values.update(values)


@contextmanager
def observe_c1(counter):
    """원 SHA/decoder로 그대로 delegate한다. 입력을 저장하거나 재인코딩하지 않는다."""
    native_hash = hashlib.sha256
    native_parse = canonical._parse_json

    class Hash:
        def __init__(self, raw=b"", **kwargs):
            self.inner = native_hash(raw, **kwargs)
            counter.add(hash_calls=1, hash_input_bytes=len(raw))

        def update(self, raw):
            self.inner.update(raw)
            counter.add(hash_input_bytes=len(raw))

        def __getattr__(self, name):
            return getattr(self.inner, name)

    def parse(raw):
        counter.add(validation_calls=1, validation_submitted_bytes=len(raw))
        try:
            value = native_parse(raw)
        except Exception:
            counter.add(
                validation_failed_calls=1, validation_failed_submitted_bytes=len(raw)
            )
            raise
        # 성공 반환은 전체 UTF-8 입력/JSON을 소비한 경우만 가능하다.
        counter.add(validation_completed_input_bytes=len(raw))
        return value

    with (
        patch.object(canonical, "hashlib", SimpleNamespace(sha256=Hash)),
        patch.object(canonical, "_parse_json", parse),
    ):
        yield counter


class InsertConnection(sqlite3.Connection):
    """INSERT VALUES의 실제 bytes/TEXT bind만 계수한다. SQL literal/숫자는 제외한다.

    UPDATE/DELETE·trigger 파생 writes의 payload는 미관측이다. 전층 logical-write
    completeness를 주장하지 않는다. COMMIT 성공도 물리 전원 손실 증명은 아니다.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.meter = Counters()
        self.pending = Counter()

    def execute(self, sql, parameters=()):
        verb = sql.lstrip().split()[0].upper()
        insert = re.fullmatch(
            r"\s*INSERT(?: OR IGNORE)? INTO (\w+) VALUES\s*\([?,\s]+\)\s*", sql, re.I
        )
        observed = Counter()
        if insert:
            if isinstance(parameters, dict):
                raise ValueError("이 관측기는 positional INSERT VALUES만 지원한다")
            for value in parameters:
                if isinstance(value, bytes):
                    observed["blob_bytes"] += len(value)
                elif isinstance(value, str):
                    observed["text_utf8_bytes"] += len(value.encode("utf-8"))
                else:
                    observed["nonbyte_bind_values"] += 1
            self.meter.add(
                insert_attempts=1, **{"attempted_" + k: v for k, v in observed.items()}
            )
        elif verb in {"INSERT", "UPDATE", "DELETE", "REPLACE"}:
            self.meter.add(unobserved_dml=1)
        result = super().execute(sql, parameters)
        if insert:
            self.meter.add(effective_insert_rows=result.rowcount)
            effective = observed if result.rowcount else Counter()
            if self.in_transaction:
                self.pending.update(effective)
            else:
                self.meter.add(**{"committed_" + k: v for k, v in effective.items()})
        if verb in {"COMMIT", "ROLLBACK"}:
            prefix = "committed_" if verb == "COMMIT" else "rolled_back_"
            self.meter.add(**{prefix + k: v for k, v in self.pending.items()})
            self.pending.clear()
        return result
