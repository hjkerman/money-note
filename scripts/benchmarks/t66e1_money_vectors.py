"""Deterministic server-derived E1-A01 vectors; stdout only, no DB or network."""

import base64
import hashlib
import json
from pathlib import Path

from isolated_sync.canonical import CanonicalError, Context, Namespace, encode
from isolated_sync.raw import Row, setting_money
from isolated_sync.segments import leaf


def vectors():
    root = Path(__file__).resolve().parents[2]
    golden = json.loads((root / "mobile/test/fixtures/segmented_server_golden.json").read_text())
    target = json.loads(base64.b64decode(golden["manifest_base64"]))["target"]
    context = Context(Namespace(**target["ns"]), target["versions"]["raw_schema"])
    # Enumerate actual Python whitespace, not Dart's validator or a hand oracle.
    whitespace = [chr(c) for c in range(0x110000) if chr(c).isspace()]
    cases = [("ordinary-" + str(i), text) for i, text in enumerate([
        "1000", "-1000", "0", "-0.0", "+0001000.00", "9007199254740991",
        "-9007199254740991.000", "+0009007199254740991.00000",
        " +0001000.00 ", "\t-1000\n", "\r\n0\t", "한글 😀 e\u0301",
        "", " ", "\t\n", "9007199254740992", "-9007199254740992",
        "1.1", "1.", ".0", "1e3", "1_000", "NaN", "Infinity", "++1", "1-",
        "１２３", "١٢٣", "1\x00", "1\n2", "--1", "+", "1.0001"
    ])]
    for char in whitespace:
        label = f"U+{ord(char):04X}"
        cases.extend((label + "-" + role, text) for role, text in (
            ("leading", char + "+0001000.00"),
            ("trailing", "+0001000.00" + char),
            ("both", char + "+0001000.00" + char),
            ("internal", "10" + char + "00")))
    for char in ["\ufeff", "\u180e", "\u200b", "\u2060", "\x08"]:
        label = f"U+{ord(char):04X}"
        cases.extend((label + "-" + role, text) for role, text in (
            ("leading", char + "1000"), ("middle", "10" + char + "00"),
            ("trailing", "1000" + char)))
    cases.append(("all-python-whitespace", "".join(whitespace)))
    template = json.loads(leaf(context, "app_settings", [Row.make("app_settings", {
        "key": "scheduled_income", "value": "0", "updated_at": "한글 😀 e\u0301"
    })]).object.raw)
    result = []
    for label, text in cases:
        row = dict(key="scheduled_income", value=text, updated_at="한글 😀 e\u0301")
        try:
            setting_money(text)
            raw = leaf(context, "app_settings", [Row.make("app_settings", row)]).object.raw
            accepted = True
        except CanonicalError:
            # Hash-valid negative bytes are NOT claimed as an authorized response.
            template["rows"][0]["value"] = row
            raw = encode(template)
            accepted = False
        independent = json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False).encode()
        assert raw == independent
        result.append(dict(id=label, value=text, accepted=accepted, ref=dict(
            hash=hashlib.sha256(b"money-note.sync.v1/snapshot-leaf\0" + raw).hexdigest(),
            bytes=str(len(raw)))))
    return dict(source="actual backend setting_money + Row.make + segments.leaf; negative bytes are untrusted",
                whitespace=[f"U+{ord(c):04X}" for c in whitespace], vectors=result)


if __name__ == "__main__":
    print(json.dumps(vectors(), ensure_ascii=False, separators=(",", ":")))
