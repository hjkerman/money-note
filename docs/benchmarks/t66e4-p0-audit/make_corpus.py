"""새 문자·위치 matrix를 실제 backend setting_money로 판정한다."""

import base64
import hashlib
import json
from pathlib import Path
import random
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
from isolated_sync.canonical import CanonicalError, Context, Namespace, encode  # noqa: E402
from isolated_sync.raw import Row, setting_money  # noqa: E402
from isolated_sync.segments import leaf  # noqa: E402

SEED = 2026101404
KEYS = (
    "scheduled_income",
    "cash_flow_balance",
    "card_limit",
    "base_next_month_liquidity",
    "liquidity_status",
)


def build():
    golden = json.loads(
        (ROOT / "mobile/test/fixtures/segmented_server_golden.json").read_text()
    )
    target = json.loads(base64.b64decode(golden["manifest_base64"]))["target"]
    context = Context(Namespace(**target["ns"]), target["versions"]["raw_schema"])
    whitespace = [chr(c) for c in range(0x110000) if chr(c).isspace()]
    format_chars = [
        chr(c) for c in range(0x110000) if unicodedata.category(chr(c)) == "Cf"
    ]
    chars = sorted(
        set(map(chr, range(160)))
        | set(whitespace)
        | set(format_chars)
        | set("\u034f\u180e\u200b\u2060\ufeff\u0301\uff11\u0661\u2212\uff0b한글😀é")
    )
    values = {}

    def add(text, family):
        values.setdefault(text, family)

    cores = [
        "0",
        "-0",
        "+001007.000",
        "9007199254740991",
        "-9007199254740991.0",
        "9007199254740992",
        "-9007199254740992",
        "1.0",
        "1.01",
        "1e3",
        ".0",
        "0.",
        "+",
        "",
        "١٠",
        "１",
        "1_000",
    ]
    for char in chars:
        for core in cores:
            for text in (char + core, core + char, char + core + char):
                add(text, "character-boundary")
        for text in (
            "+" + char + "3",
            "1" + char + "2",
            "1." + char + "0",
            "-0" + char + ".00",
        ):
            add(text, "internal-character")
    for left in whitespace:
        for right in whitespace:
            for core in [
                "-0000.00",
                "+0001007.0000",
                "-37",
                "9007199254740991.000",
                "0.00000",
            ]:
                add(left + core + right, "whitespace-cross-product")
    for white in whitespace:
        for noise in ["\ufeff", "\u2060", "\u200b", "\u180e", "\x00"]:
            for text in [
                white + noise + "+001007.00" + white,
                white + "+001007.00" + noise + white,
                noise + white + "+001007.00",
                "+001007.00" + white + noise,
            ]:
                add(text, "whitespace-format-mixed")
    for sign in ["", "+", "-"]:
        for digits in [
            "0",
            "00",
            "1007",
            "9007199254740990",
            "9007199254740991",
            "9007199254740992",
            "9223372036854775807",
            "9" * 128,
        ]:
            for ending in [
                "",
                ".0",
                ".000000",
                ".",
                ".0001",
                "e0",
                "E+0",
                "_0",
                ",0",
                "\n0",
            ]:
                add(sign + digits + ending, "grammar-and-range")
    for text in [
        "",
        "NaN",
        "Infinity",
        "-Inf",
        "--1",
        "+-1",
        "0x10",
        "−1",
        "＋1",
        "\x1c+0001000.00\x1f",
        "+" + "0" * 8192 + "7.000",
        "-" + "0" * 8192 + ".00",
        "1." + "0" * 8192,
        "1." + "0" * 8191 + "1",
        "9" * 8192,
    ]:
        add(text, "explicit-regression")
    rng = random.Random(SEED)
    alphabet = "0123456789+-.eE_ ,\x00\x1c\x1f\ufeff\u00a0\u2060"
    for _ in range(512):
        add(
            "".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 48))),
            "seeded-malformed",
        )
    cases = []
    for index, (text, family) in enumerate(values.items()):
        try:
            amount, accepted = setting_money(text), True
        except CanonicalError:
            amount, accepted = None, False
        key = KEYS[index % len(KEYS)]
        row = dict(key=key, value=text, updated_at="독립 합성 한글 e\u0301 😀")
        if accepted:
            raw = leaf(
                context, "app_settings", [Row.make("app_settings", row)]
            ).object.raw
        else:
            raw = encode(
                dict(
                    kind="snapshot-leaf",
                    **context.fields(),
                    table="app_settings",
                    height=0,
                    count="1",
                    min=["t", key],
                    max=["t", key],
                    oversized=False,
                    rows=[dict(key=["t", key], value=row)],
                )
            )
        independent = json.dumps(
            json.loads(raw),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
        assert raw == independent
        ref = dict(
            hash=hashlib.sha256(
                b"money-note.sync.v1/snapshot-leaf\0" + raw
            ).hexdigest(),
            bytes=str(len(raw)),
        )
        cases.append(
            dict(
                id=index,
                family=family,
                value=text,
                key=key,
                accepted=accepted,
                amount=amount,
                ref=ref,
                data_base64=base64.b64encode(raw).decode(),
            )
        )
    return dict(
        seed=SEED,
        python_whitespace=[ord(c) for c in whitespace],
        unicode_version=unicodedata.unidata_version,
        tested_characters=[ord(c) for c in chars],
        all_unicode_format_characters=len(format_chars),
        cases=cases,
    )


if __name__ == "__main__":
    result = build()
    Path(sys.argv[1]).write_text(
        json.dumps(result, ensure_ascii=True, separators=(",", ":"))
    )
    print(
        json.dumps(
            dict(
                cases=len(result["cases"]),
                accepted=sum(c["accepted"] for c in result["cases"]),
            )
        )
    )
