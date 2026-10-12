"""서버 validator가 판정하는 독립 finite differential corpus를 생성한다."""

import base64
import hashlib
import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync.canonical import CanonicalError, Context, Namespace, encode  # noqa: E402
from isolated_sync.raw import Row, setting_money  # noqa: E402
from isolated_sync.segments import leaf  # noqa: E402


def build():
    golden = json.loads((ROOT / "mobile/test/fixtures/segmented_server_golden.json").read_text())
    target = json.loads(base64.b64decode(golden["manifest_base64"]))["target"]
    context = Context(Namespace(**target["ns"]), target["versions"]["raw_schema"])
    whitespace = [chr(c) for c in range(0x110000) if chr(c).isspace()]
    reported = json.loads((ROOT / "mobile/test/fixtures/segmented_money_vectors.json").read_text())
    assert reported["whitespace"] == [f"U+{ord(c):04X}" for c in whitespace]
    candidates = [("reported-" + v["id"], v["value"], "scheduled_income", v) for v in reported["vectors"]]
    extras = []
    for left in whitespace:
        for right in whitespace:
            for core in ["0", "-0.00", "+0001000.000", "-9007199254740991.000"]:
                extras.append(left + core + right)
    boundary = sorted({c + offset for c in map(ord, whitespace) for offset in [-1, 0, 1]} |
                      {0, 0xFEFF, 0x200B, 0x200C, 0x200D, 0x2060, 0x180E, 0x034F, 0x061C, 0x10FFFF})
    for point in boundary:
        char = chr(point)
        extras.extend([char + "0", "-0.00" + char, char + "+0001.000" + char,
                       "1" + char + "0", "+" + char + "1", "1." + char + "0", char])
    for white in whitespace:
        for invalid in ["\ufeff", "\u200b", "\u2060", "\0"]:
            extras.extend([white + invalid + "1" + white, white + "1" + invalid + white,
                           invalid + white + "1", "1" + white + invalid])
    grammar = ["", "+", "-", "00", "-000", "1.", ".0", "1.00", "1.00001", "1e0", "0e100",
               "1_000", "1,000", "NaN", "Inf", "Infinity", "１２３", "١٢٣", "−1", "＋1",
               "1/1", "0x1", "++0", "+-0", "-+0", "--0", "1..0", "9007199254740991.00",
               "9007199254740992", "-9007199254740992", "한글", "😀", "e\u0301", "é"]
    for text in grammar:
        extras.extend([text, "\x1c\t" + text + "\u3000\r\n", "\ufeff" + text])
    extras.extend(["+" + "0" * 5000 + "1.000", "-" + "0" * 5000 + ".00", "9" * 5000,
                   "1." + "0" * 5000, "1." + "0" * 4999 + "1"])
    rng = random.Random(66010102)
    for _ in range(256):
        text = rng.choice(["", "+", "-"]) + "0" * rng.randrange(20) + str(rng.randrange(9007199254740993))
        if rng.randrange(2):
            text += "." + "0" * rng.randrange(1, 20)
        extras.append("".join(rng.choices(whitespace, k=3)) + text + "".join(rng.choices(whitespace, k=2)))
    keys = ["scheduled_income", "cash_flow_balance", "card_limit", "base_next_month_liquidity", "liquidity_status"]
    candidates.extend(("new-" + str(i), text, keys[i % 5], None) for i, text in enumerate(extras))
    cases = []
    for label, text, key, old in candidates:
        try:
            amount = setting_money(text)
            accepted = True
        except CanonicalError:
            amount, accepted = None, False
        row = dict(key=key, value=text, updated_at="한글 😀 e\u0301")
        if accepted:
            raw = leaf(context, "app_settings", [Row.make("app_settings", row)]).object.raw
        else:
            body = dict(kind="snapshot-leaf", **context.fields(), table="app_settings", height=0,
                        count="1", min=["t", key], max=["t", key], oversized=False,
                        rows=[dict(key=["t", key], value=row)])
            raw = encode(body)
        independent = json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True,
                                 separators=(",", ":"), allow_nan=False).encode()
        assert raw == independent
        reference = dict(hash=hashlib.sha256(b"money-note.sync.v1/snapshot-leaf\0" + raw).hexdigest(), bytes=str(len(raw)))
        if old is not None:
            assert accepted == old["accepted"] and reference == old["ref"]
        cases.append(dict(id=label, value=text, key=key, accepted=accepted, amount=amount,
                          ref=reference, data_base64=base64.b64encode(raw).decode()))
    return dict(whitespace=[ord(c) for c in whitespace], boundary_codepoints=boundary,
                reported_count=165, additional_count=len(extras), seed=66010102, cases=cases)


if __name__ == "__main__":
    destination = Path(sys.argv[1])
    result = build()
    destination.write_text(json.dumps(result, ensure_ascii=True, separators=(",", ":")))
    print(json.dumps(dict(total=len(result["cases"]), accepted=sum(v["accepted"] for v in result["cases"]))))
