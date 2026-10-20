"""A02: historical strict codec is an independent byte/error oracle."""

import gzip
from pathlib import Path
import random
import sys
import types
from unittest.mock import patch

import pytest

from isolated_sync import canonical as codec


@pytest.fixture(scope="module")
def previous():
    path = (
        Path(__file__).resolve().parents[2]
        / "docs/benchmarks/t66f-b02-a02-correction/canonical.py.before.gz"
    )
    module = types.ModuleType("_a02_previous_canonical")
    sys.modules[module.__name__] = module
    exec(compile(gzip.decompress(path.read_bytes()), str(path), "exec"), module.__dict__)
    yield module
    del sys.modules[module.__name__]


def outcome(fn, raw):
    try:
        value = fn(raw)
        return "value", codec.encode(value)
    except ValueError as error:
        return "error", str(error)


@pytest.mark.parametrize(
    "raw",
    [
        b'{"x":1,"x":2}',
        b'"\\ud800"',
        b'{"\\udfff":1}',
        b"9223372036854775808",
        b"-9223372036854775809",
        b"9007199254740992.0",
        b"0.00000000000000000001",
        b"1e-400",
        b"NaN",
        b"Infinity",
        b'{"x":01}',
        b"\xff",
        b"[1, 2]",
        b'{"z":0,"a":1}',
        b"1e0",
        b"1.00",
        b"\xef\xbb\xbf{}",
        b'"\\u001c+0001000.00\\u001f"',
        b"null",
        b"true",
        b"-0.0",
        '{"😀":"한글é\\n","𐀀":0,"\ue000":1}'.encode(),
    ],
)
def test_exact_value_and_error_differential(previous, raw):
    for name in ("decode_json", "decode_c1"):
        assert outcome(getattr(codec, name), raw) == outcome(getattr(previous, name), raw)


def test_nested_corpus_identical_bytes_and_hashes(previous):
    rng = random.Random(660202)
    scalars = [
        None,
        True,
        False,
        0,
        -1,
        -(1 << 63),
        (1 << 63) - 1,
        0.0,
        -0.0,
        9007199254740991.0,
        "",
        "😀é한글",
        "\x1c+0001000.00\x1f",
    ]

    def value(depth):
        if depth == 0 or rng.randrange(3) == 0:
            return rng.choice(scalars)
        if rng.randrange(2):
            return [value(depth - 1) for _ in range(rng.randrange(5))]
        return {f"{i}😀": value(depth - 1) for i in range(rng.randrange(5))}

    for _ in range(10000):
        raw = previous.encode(value(4))
        assert codec.encode(codec.decode_c1(raw)) == raw
        assert previous.encode(previous.decode_c1(raw)) == raw
        for kind in ("row", "snapshot-leaf", "view"):
            assert codec.hash_bytes(kind, raw) == previous.hash_bytes(kind, raw)


def test_one_encode_not_two_and_public_json_still_validates(previous):
    raw = b'{"a":[1,2.0,"raw"]}'
    for module, count in ((previous, 2), (codec, 1)):
        with patch.object(module, "encode", wraps=module.encode) as encode:
            module.decode_c1(raw)
            assert encode.call_count == count
    with patch.object(codec, "encode", wraps=codec.encode) as encode:
        codec.decode_json(b' { "a": 1 } ')
        assert encode.call_count == 1
    with pytest.raises(codec.CanonicalError, match="REJECT_UNICODE"):
        codec.decode_json(b'["\\ud800"]')


def test_type_and_nesting_errors_unchanged(previous):
    for raw in (None, "{}", bytearray(b"{}"), b"[" * 2000 + b"0" + b"]" * 2000):
        for name in ("decode_json", "decode_c1"):
            assert outcome(getattr(codec, name), raw) == outcome(getattr(previous, name), raw)
