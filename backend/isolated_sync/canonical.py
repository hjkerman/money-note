"""T6.6C C1, not the legacy Snapshot v7 encoder. No runtime side effects.

The codec admits int64 scalars; domain admission remains a separate obligation.
REAL is restricted to exact, finite integral money in the supported safe range.
JSON tokens are checked before conversion to binary64. No Unicode repair occurs.
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import re
from uuid import UUID


MAX_MONEY = (1 << 53) - 1
MIN_I64, MAX_I64 = -(1 << 63), (1 << 63) - 1
HASH = re.compile(r"[0-9a-f]{64}\Z")
KINDS = frozenset({"row", "snapshot-leaf", "snapshot-node", "raw-root", "hot", "control",
                   "index-empty", "index-leaf", "index-node", "index-root", "view", "fact-key"})


class CanonicalError(ValueError):
    """Stable classifications, deliberately never include input values/secrets."""


def fail(code):
    raise CanonicalError(code)


def text_bytes(value):
    if type(value) is not str:
        fail("REJECT_TYPE")
    try:
        return value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        fail("REJECT_UNICODE")


def integer(value):
    if type(value) is not int or not MIN_I64 <= value <= MAX_I64:
        fail("REJECT_INTEGER")
    return value


def money(value):
    if type(value) not in (int, float) or abs(value) > MAX_MONEY:
        fail("REJECT_MONEY")
    if not math.isfinite(value):
        fail("REJECT_MONEY")
    if abs(value) > MAX_MONEY or value != int(value):
        fail("REJECT_MONEY")
    return int(value)


def encode(value):
    """Return exact C1 UTF-8, preserving REAL .0, -0.0 and scalar distinctions."""
    parts = []

    def emit(v):
        if v is None:
            parts.append("null")
        elif type(v) is bool:
            parts.append("true" if v else "false")
        elif type(v) is int:
            parts.append(str(integer(v)))
        elif type(v) is float:
            money(v)
            parts.append(repr(v))  # supported integral REAL == Snapshot Python format
        elif type(v) is str:
            text_bytes(v)
            parts.append(json.dumps(v, ensure_ascii=False))
        elif type(v) is list:
            parts.append("[")
            for i, item in enumerate(v):
                if i:
                    parts.append(",")
                emit(item)
            parts.append("]")
        elif type(v) is dict:
            for key in v:
                text_bytes(key)
            parts.append("{")
            for i, key in enumerate(sorted(v)):  # Python scalar order, NOT UTF-16
                if i:
                    parts.append(",")
                emit(key)
                parts.append(":")
                emit(v[key])
            parts.append("}")
        else:
            fail("REJECT_TYPE")

    try:
        emit(value)
        return "".join(parts).encode("utf-8")
    except RecursionError:
        fail("REJECT_NESTING")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("REJECT_DUPLICATE_KEY")
        result[key] = value
    return result


def _real(token):
    # Decimal sees the original token BEFORE binary64 rounding/underflow.
    try:
        exact = Decimal(token)
    except InvalidOperation:
        fail("REJECT_NUMBER")
    if not exact.is_finite() or exact.copy_abs() > MAX_MONEY or exact != exact.to_integral_value():
        fail("REJECT_NUMBER")
    value = float(token)
    if Decimal(repr(value)) != exact:
        fail("REJECT_NUMBER")
    return value


def _int_token(token):
    if len(token) > 20:
        fail("REJECT_INTEGER")
    return integer(int(token))


def decode_json(raw):
    """Strict admission (noncanonical JSON is allowed only for vector/input use)."""
    if type(raw) is not bytes:
        fail("REJECT_TYPE")
    try:
        contents = raw.decode("utf-8", errors="strict")
        value = json.loads(contents, object_pairs_hook=_pairs, parse_float=_real,
                           parse_int=_int_token,
                           parse_constant=lambda _: fail("REJECT_NUMBER"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        fail("REJECT_JSON")
    encode(value)  # includes ALL nested strings and map keys, not just row fields
    return value


def decode_c1(raw):
    value = decode_json(raw)
    if encode(value) != raw:
        fail("REJECT_CANONICAL")
    return value


def hash_bytes(kind, raw):
    """Domain framing only. Callers must admit raw bytes before trusting a Ref."""
    if kind not in KINDS or type(raw) is not bytes:
        fail("REJECT_HASH_DOMAIN")
    return hashlib.sha256(b"money-note.sync.v1/" + kind.encode("ascii") + b"\0" + raw).hexdigest()


@dataclass(frozen=True)
class Namespace:
    server_id: str
    dataset_id: str
    epoch: str

    def __post_init__(self):
        for value in (self.server_id, self.dataset_id, self.epoch):
            try:
                uuid = UUID(value)
                valid = uuid.version == 4 and str(uuid) == value
            except (ValueError, AttributeError, TypeError):
                valid = False
            if not valid:
                fail("REJECT_NAMESPACE")

    def wire(self):
        return dict(server_id=self.server_id, dataset_id=self.dataset_id, epoch=self.epoch)


@dataclass(frozen=True)
class Context:
    ns: Namespace
    raw_schema: str

    def __post_init__(self):
        if not isinstance(self.ns, Namespace) or type(self.raw_schema) is not str or not HASH.fullmatch(self.raw_schema):
            fail("REJECT_CONTEXT")

    def fields(self):
        return dict(ns=self.ns.wire(), canon=1, raw_schema=self.raw_schema)


@dataclass(frozen=True)
class Object:
    """Immutable exact bytes; decoded views are copies, not mutable hash inputs."""

    kind: str
    raw: bytes
    hash: str = field(init=False)

    def __post_init__(self):
        value = decode_c1(self.raw)
        if type(value) is not dict or value.get("kind") != self.kind or self.kind not in KINDS:
            fail("REJECT_OBJECT_KIND")
        object.__setattr__(self, "hash", hash_bytes(self.kind, self.raw))

    @classmethod
    def make(cls, body):
        return cls(body["kind"], encode(body))

    def ref(self):
        return dict(hash=self.hash, bytes=str(len(self.raw)))

    def body(self):
        return decode_c1(self.raw)


@dataclass(frozen=True)
class Key:
    value: int | str

    def __post_init__(self):
        if type(self.value) is int:
            integer(self.value)
        else:
            text_bytes(self.value)

    def wire(self):
        return ["i", str(self.value)] if type(self.value) is int else ["t", self.value]

    def order(self):
        return self.value if type(self.value) is int else text_bytes(self.value)

    @classmethod
    def parse(cls, wire):
        if type(wire) is not list or len(wire) != 2 or type(wire[1]) is not str:
            fail("REJECT_KEY")
        if wire[0] == "t":
            return cls(wire[1])
        if wire[0] != "i" or not re.fullmatch(r"0|-?[1-9][0-9]*", wire[1]):
            fail("REJECT_KEY")
        return cls(_int_token(wire[1]))


def row_hash(context, table, key, value):
    # §11 explicitly specifies a row preimage, not an Object body with kind/canon.
    return hash_bytes("row", encode(dict(ns=context.ns.wire(), raw_schema=context.raw_schema,
                                          table=table, key=key.wire(), value=value)))
