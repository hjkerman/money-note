"""보존된 실제 B02 G1 raw bytes의 timestamp만 원 seed에 복원한다."""

import hashlib
import json
from pathlib import Path
import sqlite3

HISTORICAL = Path("/tmp/mn-b02-independent-100000-z6ux9y53")
HERE = Path(__file__).resolve().parent


def restore(sandbox):
    fixture = json.loads((HISTORICAL / "server/backend-fixture.json").read_text())
    path = next((HISTORICAL / "client/segmented-store-v1").glob("*"))
    src = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    dst = sqlite3.connect(sandbox.path)
    dst.row_factory = sqlite3.Row
    dst.execute("PRAGMA foreign_keys=ON")

    def read(ref):
        kind, body = src.execute(
            "SELECT kind,body FROM objects WHERE hash=?", (ref["hash"],)
        ).fetchone()
        assert len(body) == int(ref["bytes"])
        assert (
            hashlib.sha256(
                b"money-note.sync.v1/" + kind.encode() + b"\0" + body
            ).hexdigest()
            == ref["hash"]
        )
        return json.loads(body)

    def values(ref):
        value = read(ref)
        if value["kind"] == "snapshot-node":
            for child in value["children"]:
                yield from values(child["ref"])
        else:
            assert value["kind"] == "snapshot-leaf"
            yield from (r["value"] for r in value["rows"])

    root = read(fixture["manifest"]["target"]["raw_ref"])
    proof = {}
    try:
        dst.execute("BEGIN IMMEDIATE")
        for entry in root["tables"]:
            table = entry["name"]
            primary = (
                "entry_payment_key"
                if table == "card_payment_deferrals"
                else "registration_key"
                if table == "notification_candidate_registrations"
                else "key"
                if table in ("app_settings", "app_labels")
                else "id"
            )
            columns = [r["name"] for r in dst.execute(f"PRAGMA table_info({table})")]
            volatile = [
                c for c in ["created_at", "updated_at", "confirmed_at"] if c in columns
            ]
            count = 0
            changed = 0
            digest = hashlib.sha256()
            for expected in values(entry["root"]["ref"]):
                current = dict(
                    dst.execute(
                        f"SELECT * FROM {table} WHERE {primary}=?", (expected[primary],)
                    ).fetchone()
                )
                assert set(current) == set(expected), (table, "schema")
                assert all(
                    current[k] == expected[k] for k in current if k not in volatile
                ), (table, expected[primary], "non-timestamp difference")
                if any(current[k] != expected[k] for k in volatile):
                    dst.execute(
                        f"UPDATE {table} SET "
                        + ",".join(c + "=?" for c in volatile)
                        + f" WHERE {primary}=?",
                        (*[expected[k] for k in volatile], expected[primary]),
                    )
                    changed += 1
                actual = dict(
                    dst.execute(
                        f"SELECT * FROM {table} WHERE {primary}=?", (expected[primary],)
                    ).fetchone()
                )

                def encode(v):
                    return json.dumps(
                        v, sort_keys=True, ensure_ascii=False, separators=(",", ":")
                    ).encode()

                assert encode(actual) == encode(expected), (
                    table,
                    expected[primary],
                    "exact canonical value",
                )
                digest.update(
                    hashlib.sha256(encode(actual)).hexdigest().encode() + b"\n"
                )
                count += 1
            assert dst.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == count
            expected = fixture["graph"]["raw_value_sha256"][table]
            assert {"count": count, "sha256": digest.hexdigest()} == expected
            proof[table] = {
                "count": count,
                "timestamp_rows_restored": changed,
                "sha256": digest.hexdigest(),
            }
        revision = int(fixture["manifest"]["target"]["revision"])
        dst.execute(
            "UPDATE authoritative_state_revision SET revision=? WHERE id=1", (revision,)
        )
        dst.commit()
    except BaseException:
        dst.rollback()
        raise
    finally:
        src.close()
        dst.close()
    (HERE / "evidence/fixture-raw-restoration.json").write_text(
        json.dumps(
            {
                "source": "actual preserved independent B02 G1 immutable raw objects, read-only",
                "tables": proof,
                "non_timestamp_changes": 0,
                "revision": str(revision),
                "boundary": "synthetic preparation before isolated sync schema/epoch bootstrap; no live request/capture/publication bypass",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n"
    )
