"""Diagnostic-only JSON byte spans and lossless host compression codecs."""

import ctypes
import ctypes.util
from dataclasses import dataclass
import gzip
import json
import math
import statistics


@dataclass(slots=True)
class Span:
    start: int
    end: int
    children: object = None
    key_bytes: int = 0

    @property
    def size(self):
        return self.end - self.start


class JsonBytes:
    """Offsets refer to original bytes, never characters or reserialized JSON.

    Diagnostic input is first validated by Python's JSON decoder. This is not
    an alternative product admission parser. Object duplicates are rejected.
    """

    def __init__(self, body):
        json.loads(body)
        self.body = body
        self.at = 0
        self.root = self.value()
        self.space()
        if self.at != len(body):
            raise ValueError("trailing bytes")

    def space(self):
        while self.at < len(self.body) and self.body[self.at] in b" \t\r\n":
            self.at += 1

    def string(self):
        start = self.at
        self.at += 1
        while True:
            char = self.body[self.at]
            self.at += 1
            if char == 92:
                self.at += 1
            elif char == 34:
                return Span(start, self.at)

    def value(self):
        self.space()
        start = self.at
        char = self.body[self.at]
        if char == 34:
            return self.string()
        if char in (123, 91):
            is_map = char == 123
            children = {} if is_map else []
            key_bytes = 0
            self.at += 1
            self.space()
            closing = 125 if is_map else 93
            while self.body[self.at] != closing:
                if is_map:
                    key_span = self.string()
                    key_bytes += key_span.size
                    key = json.loads(self.slice(key_span))
                    if key in children:
                        raise ValueError("duplicate JSON key")
                    self.space()
                    assert self.body[self.at] == 58
                    self.at += 1
                    children[key] = self.value()
                else:
                    children.append(self.value())
                self.space()
                if self.body[self.at] == 44:
                    self.at += 1
                    self.space()
                else:
                    break
            assert self.body[self.at] == closing
            self.at += 1
            return Span(start, self.at, children, key_bytes)
        while self.at < len(self.body) and self.body[self.at] not in b",]} \t\r\n":
            self.at += 1
        return Span(start, self.at)

    def get(self, *path):
        node = self.root
        for key in path:
            node = node.children[key]
        return node

    def slice(self, node):
        return self.body[node.start:node.end]


class Brotli:
    """Existing system libbrotli C API; no new package or runtime dependency."""

    def __init__(self):
        encoder = ctypes.util.find_library("brotlienc")
        decoder = ctypes.util.find_library("brotlidec")
        if not encoder or not decoder:
            raise RuntimeError("system Brotli library unavailable")
        self.enc = ctypes.CDLL(encoder)
        self.dec = ctypes.CDLL(decoder)
        self.enc.BrotliEncoderMaxCompressedSize.argtypes = [ctypes.c_size_t]
        self.enc.BrotliEncoderMaxCompressedSize.restype = ctypes.c_size_t
        self.enc.BrotliEncoderCompress.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                                 ctypes.c_size_t, ctypes.c_void_p,
                                                 ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]
        self.dec.BrotliDecoderDecompress.argtypes = [ctypes.c_size_t, ctypes.c_void_p,
                                                   ctypes.POINTER(ctypes.c_size_t), ctypes.c_void_p]

    def compress(self, body, quality=4):
        size = ctypes.c_size_t(self.enc.BrotliEncoderMaxCompressedSize(len(body)))
        output = ctypes.create_string_buffer(size.value)
        if not self.enc.BrotliEncoderCompress(quality, 22, 0, len(body), body,
                                            ctypes.byref(size), output):
            raise ValueError("Brotli compression failed")
        return output.raw[:size.value]

    def decompress(self, body, raw_size):
        size = ctypes.c_size_t(raw_size)
        output = ctypes.create_string_buffer(raw_size)
        if self.dec.BrotliDecoderDecompress(len(body), body, ctypes.byref(size), output) != 1:
            raise ValueError("Brotli decompression failed")
        return output.raw[:size.value]


def gzip_bytes(body, level=6):
    return gzip.compress(body, compresslevel=level, mtime=0)


def accepts_gzip(header):
    """Small negotiation rule for the isolated gzip experiment only."""
    qualities = {}
    for item in header.lower().split(","):
        parts = [part.strip() for part in item.split(";")]
        quality = 1.0
        for parameter in parts[1:]:
            if parameter.startswith("q="):
                try:
                    quality = float(parameter[2:])
                except ValueError:
                    quality = 0.0
        qualities[parts[0]] = quality if 0 <= quality <= 1 else 0.0
    return qualities.get("gzip", qualities.get("*", 0)) > 0


def stats(values):
    ordered = sorted(values)
    n = len(ordered)
    return {"n": n, "median": statistics.median(ordered),
            "p95": ordered[math.ceil(n * .95) - 1], "min": ordered[0], "max": ordered[-1],
            "stdev": statistics.pstdev(ordered)}


def partition(body, paths):
    """Disjoint selected value spans plus all unassigned bytes exactly once."""
    tree = JsonBytes(body)
    spans = [(path, tree.get(*path)) for path in paths]
    ordered = sorted((span.start, span.end) for _, span in spans)
    for previous, current in zip(ordered, ordered[1:]):
        if previous[1] > current[0]:
            raise ValueError("overlapping byte attribution")
    overhead = len(body) - sum(span.size for _, span in spans)
    return tree, spans, overhead
