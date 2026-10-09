"""Standalone diagnostic gates; no application runtime imports."""

import json

import pytest

from payload_bytes import Brotli, JsonBytes, accepts_gzip, gzip_bytes, partition


@pytest.mark.parametrize("ensure_ascii", [True, False])
def test_exact_utf8_ranges_and_accounting(ensure_ascii):
    value = {"한글😀": ["é", "é", "a\x00b", 'quote"\\'], "nested": {"zero": 0, "nil": None}}
    for separators in [(",", ":"), (", ", ": ")]:
        body = json.dumps(value, ensure_ascii=ensure_ascii, separators=separators).encode()
        tree, spans, overhead = partition(body, [("한글😀",), ("nested", "zero"), ("nested", "nil")])
        assert sum(span.size for _, span in spans) + overhead == len(body)
        assert json.loads(tree.slice(tree.get("한글😀"))) == value["한글😀"]
        assert tree.root.size == len(body)
        assert tree.root.key_bytes == len(json.dumps("한글😀", ensure_ascii=ensure_ascii).encode()) + len(b'"nested"')


def test_reject_double_counting_and_duplicate_keys():
    with pytest.raises(ValueError, match="overlapping"):
        partition(b'{"a":{"b":1}}', [("a",), ("a", "b")])
    with pytest.raises(ValueError, match="duplicate"):
        JsonBytes(b'{"a":0,"a":1}')


def test_original_numeric_lexemes_not_reserialized():
    body = b'{ "a":1.00e+0,"b":-0.0,"c":"\\ud83d\\ude00" }'
    tree = JsonBytes(body)
    assert tree.slice(tree.get("a")) == b"1.00e+0"
    assert tree.slice(tree.get("b")) == b"-0.0"
    assert tree.slice(tree.get("c")) == b'"\\ud83d\\ude00"'


@pytest.mark.parametrize("header,accepted", [("", False), ("identity", False), ("gzip", True),
                                           ("gzip;q=0, br", False), ("br, gzip;q=.5", True),
                                           ("*;q=1, gzip;q=0", False)])
def test_isolated_negotiation(header, accepted):
    assert accepts_gzip(header) == accepted


@pytest.mark.parametrize("body", [b"", b"hello", '한글😀\x00é'.encode(), bytes(range(256)) * 30])
def test_lossless_codecs(body):
    import gzip

    for level in (1, 6, 9):
        assert gzip.decompress(gzip_bytes(body, level)) == body
    try:
        brotli = Brotli()
    except RuntimeError:
        pytest.skip("system Brotli unavailable")
    for quality in (4, 6, 9):
        assert brotli.decompress(brotli.compress(body, quality), len(body)) == body
