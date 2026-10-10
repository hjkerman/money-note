"""Committed C1 vectors are an oracle independent of the new formatter."""

import hashlib
import json
from pathlib import Path
import base64
import shutil
import subprocess

import pytest


VECTORS = json.loads((Path(__file__).resolve().parents[2] /
                     "docs/specimens/t66c-canonical-vectors.json").read_text())


@pytest.mark.parametrize("vector", VECTORS["valid"], ids=lambda v: v["id"])
def test_committed_c1_vectors(vector):
    from isolated_sync.canonical import decode_json, encode

    actual = encode(decode_json(vector["input_json"].encode()))
    assert actual == vector["expected_c1"].encode()
    assert len(actual) == vector["utf8_bytes"]
    assert hashlib.sha256(actual).hexdigest() == vector["sha256_c1"]


@pytest.mark.parametrize("vector", VECTORS["invalid"], ids=lambda v: v["id"])
def test_committed_invalid_c1_vectors(vector):
    from isolated_sync.canonical import CanonicalError, decode_json

    with pytest.raises(CanonicalError, match=vector["expected"]):
        decode_json(vector["input_json"].encode())


@pytest.mark.parametrize("body", [b'{"x":1,"x":2}', b'{"x":1,"\\u0078":2}',
                                  b'{"x":-1e-400}', b'{"x":1000.00000000000001}',
                                  b'{"x":NaN}', b'{"x":1.5}', b'{"x":1e309}',
                                  b'{"x":1e1000000}', b'{"x":' + b'1'*5000 + b'}'])
def test_raw_inputs_fail_closed(body):
    from isolated_sync.canonical import CanonicalError, decode_json

    with pytest.raises(CanonicalError):
        decode_json(body)


def test_hash_framing_and_received_bytes():
    from isolated_sync.canonical import CanonicalError, decode_c1, encode, hash_bytes

    body = {"kind": "snapshot-leaf", "x": "한글\x00😀"}
    raw = encode(body)
    assert hash_bytes("snapshot-leaf", raw) == hashlib.sha256(
        b"money-note.sync.v1/snapshot-leaf\0" + raw).hexdigest()
    assert hash_bytes("row", raw) != hash_bytes("snapshot-leaf", raw)
    for noncanonical in (raw + b"\n", b'{"n":-0}', b'{"n":1e0}', b'{"x":"\\u0061"}'):
        with pytest.raises(CanonicalError, match="REJECT_CANONICAL"):
            decode_c1(noncanonical)


def test_dart_independent_formatter_parity():
    from isolated_sync.canonical import decode_json, encode

    dart = shutil.which("dart")
    if dart is None:
        pytest.skip("Dart CLI unavailable; add Flutter bin to PATH for explicit parity gate")
    controls = [0, -(2**63), 2**63-1, 1000.0, -0.0, 9007199254740991.0, None, False,
                ["é", "é", "😀", "\0", "日本語"], {"😀": 1, "\ue000": 2},
                {"amount_value": 1000.0, "aux_amount_value": None, "id": 12, "title": "한글"}]
    inputs = [v["input_json"] for v in VECTORS["valid"]] + [json.dumps(v, ensure_ascii=False) for v in controls]
    inputs += [v["input_json"] for v in VECTORS["invalid"]]
    verifier = Path(__file__).resolve().parents[2] / "scripts/benchmarks/t66d2a_c1.dart"
    result = subprocess.run([dart, str(verifier)], input=json.dumps(inputs), text=True,
                            capture_output=True, check=True, timeout=40)
    output = json.loads(result.stdout)
    for raw, actual in zip(inputs[:-3], output[:-3], strict=True):
        assert base64.b64decode(actual) == encode(decode_json(raw.encode()))
    assert output[-3:] == [{"error": "REJECT_UNICODE"}] * 3


@pytest.mark.parametrize("kind", ["row", "snapshot-leaf", "snapshot-node", "raw-root", "hot", "control",
                                  "index-empty", "index-leaf", "index-node", "index-root", "view", "fact-key"])
def test_all_hash_domains_independent_digest(kind):
    from isolated_sync.canonical import hash_bytes
    for raw in (b"", b"[]", b'{"n":1}', b'{"n":1.0}', '"é"'.encode(), '"é"'.encode()):
        assert hash_bytes(kind, raw) == hashlib.sha256(b"money-note.sync.v1/" + kind.encode() + b"\0" + raw).hexdigest()
