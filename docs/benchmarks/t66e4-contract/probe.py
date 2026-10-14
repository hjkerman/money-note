"""Read-only E4 contract investigation using newly owned synthetic databases.

stdout is a private fixture pipe. Never open a configured DB, .env or listener.
"""
import json
from pathlib import Path
import sys
from unittest.mock import patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts" / "benchmarks"))

from app.money import exact_money  # noqa: E402
from app.services.authoritative_state import _construct, _prepare  # noqa: E402
from isolated_sync.canonical import CanonicalError  # noqa: E402
from isolated_sync.raw import MONEY_SETTINGS, setting_money  # noqa: E402
from isolated_sync.retention import RetentionRepository  # noqa: E402
from isolated_sync.retention_schema import RetentionSandbox  # noqa: E402
from t66e2_server import oracle  # noqa: E402
from tests.test_isolated_sync_capture import ROWS, insert  # noqa: E402
from tests.test_isolated_sync_observation import (  # noqa: E402
    CREDENTIAL, EVAL, NOW, auth_seed,
)


def accepted(validate, value):
    try:
        validate(value)
        return True
    except (ValueError, CanonicalError):
        return False


def main():
    text = "\x1c+0001000.00\x1f"
    cases = ["1000", " 1000 ", "\t1000\n", "\xa01000\xa0",
             "\x1c1000", "\x1d1000", "1000\x1e", "1000\x1f",
             text, "\ufeff1000", "1000\ufeff", "10\ufeff00"]
    vectors = [dict(value=value, segmented=accepted(setting_money, value),
                    legacy_server=accepted(exact_money, value)) for value in cases]
    with RetentionSandbox() as db:
        with db.connect() as conn:
            for table, source in ROWS.items():
                row = dict(source)
                if table == "cash_flows":
                    row["amount_value"] = -50
                insert(conn, table, row)
            for key in MONEY_SETTINGS:
                conn.execute("INSERT OR REPLACE INTO app_settings(key,value) VALUES (?,?)",
                             (key, text if key == "cash_flow_balance" else "0"))
            auth_seed(conn)
        db.install()
        db.bootstrap()
        with patch("app.services.judgment.common._MESSAGE_RANDOM.randrange", return_value=0):
            repo = RetentionRepository(db, clock=lambda: NOW, evaluation=lambda: EVAL)
            manifest = repo.create(CREDENTIAL, request_id=str(uuid4()), guard=lambda: CREDENTIAL)
            fixture = oracle(db, manifest)
            with db.connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                # Only the isolated schema/version gate differs from CURRENT.
                # Raw/Snapshot/money/projection validation and serialization
                # remain the actual server implementations, as in D3a tests.
                with patch("app.services.authoritative_state.CURRENT_SCHEMA_VERSION",
                           conn.execute("PRAGMA user_version").fetchone()[0]), \
                     patch("app.services.authoritative_state._validate_revision_triggers"), \
                     patch("app.services.authoritative_state.app_today", return_value=EVAL.today):
                    bundle, _, _ = _construct(conn, CREDENTIAL)
                    wire = json.loads(_prepare(bundle).body)
                conn.rollback()
        assert wire["state"]["settings"]["cash_flow_balance"] == text
        assert next(r["value"] for r in wire["snapshot"]["data"]["app_settings"]
                    if r["key"] == "cash_flow_balance") == text
        assert wire["authority"]["state_fingerprint"] != manifest["target"]["sync_root"]
        print(json.dumps(dict(vectors=vectors, fixture=fixture, wire=wire), ensure_ascii=True))


if __name__ == "__main__":
    main()
