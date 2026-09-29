"""Versioned SQLite schema upgrades; no operation here owns a business transaction."""

from collections.abc import Callable, Iterator
from functools import lru_cache
import re
import sqlite3

from app.services.liquidity_names import (
    LEGACY_LIQUIDITY_LABEL_KEYS,
    LEGACY_LIQUIDITY_SETTING_KEYS,
    LIQUIDITY_LABEL_DEFAULTS,
    LIQUIDITY_SETTING_DEFAULTS,
    normalized_legacy_label_value,
)

CURRENT_SCHEMA_VERSION = 3


def _statements(schema: str) -> Iterator[str]:
    pending = ""
    for line in schema.splitlines(keepends=True):
        pending += line
        if sqlite3.complete_statement(pending):
            yield pending.strip()
            pending = ""
    if pending.strip():
        raise RuntimeError("incomplete database schema SQL")


def _apply_schema(conn: sqlite3.Connection, schema: str, kinds: set[str]) -> None:
    for statement in _statements(schema):
        kind = statement.split(None, 2)[:2]
        if len(kind) == 2 and " ".join(kind).upper() in kinds:
            conn.execute(statement)
        elif "all" in kinds:
            conn.execute(statement)


@lru_cache(maxsize=1)
def _expected_tables_and_columns(schema: str) -> dict[str, set[str]]:
    # SCHEMA is the current column contract; build it once per process.
    with sqlite3.connect(":memory:") as reference:
        _apply_schema(reference, schema, {"CREATE TABLE"})
        names = [row[0] for row in reference.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )]
        return {
            name: {row[1] for row in reference.execute(f"PRAGMA table_info({name})")}
            for name in names
        }


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    )}


# Only these columns were absent from recognized pre-versioned schemas and
# have a defined migration-001 addition. Every other current column, including
# financial values and identities, must already be present in an existing DB.
LEGACY_ADDITIVE_COLUMNS = {
    "ledger_entries": {"discount_override", "source_planned_entry_id"},
    "monthly_panels": {"discount_override", "confirmed_cash_flow_id", "confirmed_month"},
    "card_payment_events": {"batch_id", "idempotency_key", "request_fingerprint"},
    "offline_reconciliations": {"fingerprint_version", "request_fingerprint"},
}


def _legacy_required_columns(expected: dict[str, set[str]]) -> dict[str, set[str]]:
    return {
        table: columns - LEGACY_ADDITIVE_COLUMNS.get(table, set())
        for table, columns in expected.items()
    }


def _admit_unversioned_legacy(conn: sqlite3.Connection, schema: str) -> None:
    expected = _expected_tables_and_columns(schema)
    present = _table_names(conn)
    required = _legacy_required_columns(expected)
    historical_core_tables = {
        "ledger_entries", "monthly_panels", "cash_flows", "app_settings", "app_labels",
        "users", "auth_sessions", "share_sessions", "card_payment_events",
        "card_payment_allocations", "card_payment_deferrals", "audit_logs",
    }
    if not historical_core_tables.issubset(present):
        raise RuntimeError("unknown unversioned database schema: missing historical core tables")
    if present - set(expected) - {"installments"}:
        raise RuntimeError("unknown unversioned database schema: unfamiliar tables")
    # A revision table identifies the current unversioned era: its schema was
    # already complete, so missing newer columns cannot be treated as legacy.
    current_era = "authoritative_state_revision" in present
    for table in present & set(expected):
        actual = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        allowed = expected[table] | ({"discount_checked"} if table in {"ledger_entries", "monthly_panels"} else set())
        required_columns = expected[table] if current_era else required[table]
        if not actual.issubset(allowed) or not required_columns.issubset(actual):
            raise RuntimeError(f"unknown unversioned database schema: {table} columns")
    if "card_payment_batch_items" in present and "card_payment_batches" not in present:
        raise RuntimeError("unknown unversioned database schema: orphan payment batch items")
    if "offline_reconciliation_operations" in present and "offline_reconciliations" not in present:
        raise RuntimeError("unknown unversioned database schema: orphan reconciliation operations")


def _validate_current_schema(conn: sqlite3.Connection, schema: str) -> None:
    expected = _expected_tables_and_columns(schema)
    expected_tables = set(expected)
    present = _table_names(conn)
    if not expected_tables.issubset(present):
        raise RuntimeError("current database version has missing tables")
    for table, required in expected.items():
        actual = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        if not required.issubset(actual):
            raise RuntimeError(f"current database version has missing {table} columns")
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('index', 'trigger')")}
    required_objects = set(re.findall(
        r"CREATE (?:UNIQUE )?INDEX IF NOT EXISTS ([a-z_]+)|CREATE TRIGGER IF NOT EXISTS ([a-z_]+)",
        schema,
    ))
    required_names = {name for pair in required_objects for name in pair if name}
    required_names.update({"idx_ledger_payment_key", "idx_ledger_source_planned", "idx_card_payment_events_idempotency"})
    if not required_names.issubset(names):
        raise RuntimeError("current database version has missing critical indexes or triggers")
    for table, columns in (
        ("users", ("username",)),
        ("auth_sessions", ("session_token_hash",)),
        ("card_payment_batch_items", ("batch_id", "entry_payment_key")),
        ("offline_reconciliation_operations", ("reconciliation_id", "sequence")),
    ):
        unique = False
        for index in conn.execute(f"PRAGMA index_list({table})"):
            if index[2] and tuple(row[2] for row in conn.execute(f"PRAGMA index_info({index[1]})")) == columns:
                unique = True
                break
        if not unique:
            raise RuntimeError(f"current database version has missing {table} unique constraint")


def _extra_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_payment_key ON ledger_entries(payment_key) WHERE payment_key IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_source_planned ON ledger_entries(source_planned_entry_id) WHERE source_planned_entry_id IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_card_payment_events_idempotency ON card_payment_events(idempotency_key) WHERE idempotency_key IS NOT NULL")


def _migration_001_add_tables_and_columns(conn: sqlite3.Connection, schema: str) -> None:
    _apply_schema(conn, schema, {"CREATE TABLE"})
    conn.execute("DROP TABLE IF EXISTS installments")
    panel_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(monthly_panels)").fetchall()
    }
    if "confirmed_at" not in panel_columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN confirmed_at TEXT")
    if "due_day" not in panel_columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN due_day INTEGER")
    if "discount_amount" not in panel_columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN discount_amount INTEGER NOT NULL DEFAULT 0")
    if "discount_override" not in panel_columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN discount_override INTEGER NOT NULL DEFAULT 0")
    if "spent_on" not in panel_columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN spent_on TEXT")
    if "confirmed_cash_flow_id" not in panel_columns:
        conn.execute(
            """
            ALTER TABLE monthly_panels
            ADD COLUMN confirmed_cash_flow_id INTEGER REFERENCES cash_flows(id) ON DELETE SET NULL
            """
        )
    if "confirmed_month" not in panel_columns:
        conn.execute("ALTER TABLE monthly_panels ADD COLUMN confirmed_month TEXT")
    conn.execute(
        """
        UPDATE monthly_panels
        SET confirmed_month = substr(spent_on, 1, 7)
        WHERE panel_type = 'fixed'
          AND confirmed_cash_flow_id IS NOT NULL
          AND confirmed_month IS NULL
          AND spent_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'
        """
    )
    _drop_legacy_column(conn, "monthly_panels", "discount_checked")
    ledger_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(ledger_entries)").fetchall()
    }
    if "confirmed_at" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN confirmed_at TEXT")
    if "confirmed_month" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN confirmed_month TEXT")
    if "source_planned_entry_id" not in ledger_columns:
        conn.execute(
            """
            ALTER TABLE ledger_entries
            ADD COLUMN source_planned_entry_id INTEGER REFERENCES ledger_entries(id) ON DELETE SET NULL
            """
        )
    if "due_day" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN due_day INTEGER")
    if "spending_category" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN spending_category TEXT")
    if "usage_place" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN usage_place TEXT")
    if "usage_item" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN usage_item TEXT")
    if "payment_key" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN payment_key TEXT")
    if "discount_override" not in ledger_columns:
        conn.execute("ALTER TABLE ledger_entries ADD COLUMN discount_override INTEGER NOT NULL DEFAULT 0")
    _drop_legacy_column(conn, "ledger_entries", "discount_checked")
    conn.execute(
        """
        UPDATE ledger_entries
        SET payment_key = lower(hex(randomblob(16)))
        WHERE payment_key IS NULL AND entry_kind != 'planned'
        """
    )
    conn.execute(
        """
        UPDATE ledger_entries
        SET confirmed_month = strftime('%Y-%m', 'now')
        WHERE entry_kind = 'planned' AND confirmed_at IS NOT NULL AND confirmed_month IS NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ledger_payment_key
        ON ledger_entries(payment_key)
        WHERE payment_key IS NOT NULL
        """
    )
    cash_flow_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(cash_flows)").fetchall()
    }
    if "is_primary_income" not in cash_flow_columns:
        conn.execute("ALTER TABLE cash_flows ADD COLUMN is_primary_income INTEGER NOT NULL DEFAULT 0")
    deferral_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(card_payment_deferrals)").fetchall()
    }
    event_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(card_payment_events)").fetchall()
    }
    if "batch_id" not in event_columns:
        conn.execute(
            """
            ALTER TABLE card_payment_events
            ADD COLUMN batch_id INTEGER REFERENCES card_payment_batches(id) ON DELETE CASCADE
            """,
        )
    if "idempotency_key" not in event_columns:
        conn.execute("ALTER TABLE card_payment_events ADD COLUMN idempotency_key TEXT")
    if "request_fingerprint" not in event_columns:
        conn.execute("ALTER TABLE card_payment_events ADD COLUMN request_fingerprint TEXT")
    reconciliation_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(offline_reconciliations)").fetchall()
    }
    if "fingerprint_version" not in reconciliation_columns:
        conn.execute("ALTER TABLE offline_reconciliations ADD COLUMN fingerprint_version INTEGER")
    if "request_fingerprint" not in reconciliation_columns:
        conn.execute("ALTER TABLE offline_reconciliations ADD COLUMN request_fingerprint TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_card_payment_events_idempotency
        ON card_payment_events(idempotency_key)
        WHERE idempotency_key IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_ledger_source_planned
        ON ledger_entries(source_planned_entry_id)
        WHERE source_planned_entry_id IS NOT NULL
        """
    )
    for column, column_type in {
        "original_book_section": "TEXT",
        "original_entry_date": "TEXT",
        "original_date_label": "TEXT",
        "original_group_label": "TEXT",
        "original_title": "TEXT",
        "original_sort_order": "INTEGER",
    }.items():
        if column not in deferral_columns:
            conn.execute(f"ALTER TABLE card_payment_deferrals ADD COLUMN {column} {column_type}")
    _apply_schema(conn, schema, {"INSERT OR"})


def _migration_002_backfill_domain_data(conn: sqlite3.Connection, schema: str) -> None:
    del schema
    conn.execute(
        """
        UPDATE app_labels
        SET value = '현금성 고정지출', updated_at = CURRENT_TIMESTAMP
        WHERE key = 'panel_fixed_title' AND value = '고정지출'
        """
    )
    conn.execute(
        """
        UPDATE app_labels
        SET value = '세부내역', updated_at = CURRENT_TIMESTAMP
        WHERE key IN ('current_header_title', 'archive_header_title', 'panel_header_title')
          AND value = '적요'
        """
    )
    conn.execute(
        """
        UPDATE app_labels
        SET value = '고정지출', updated_at = CURRENT_TIMESTAMP
        WHERE key = 'summary_transfer_or_deposit_label' AND value = '송금/예치'
        """
    )
    conn.execute("DELETE FROM app_settings WHERE key = 'family_card_limit'")
    conn.execute("DELETE FROM app_settings WHERE key = 'interest_expense'")
    conn.execute("DELETE FROM app_labels WHERE key = 'summary_interest_expense_label'")
    _normalize_domain_names(conn)
    _normalize_money_settings(conn)
    _migrate_liquidity_names(conn)
    _backfill_planned_due_days(conn)


def _migration_003_install_secondary_schema(conn: sqlite3.Connection, schema: str) -> None:
    _apply_schema(conn, schema, {"CREATE INDEX", "CREATE TRIGGER"})
    _extra_indexes(conn)


MIGRATIONS = (
    _migration_001_add_tables_and_columns,
    _migration_002_backfill_domain_data,
    _migration_003_install_secondary_schema,
)


def initialize_database(conn: sqlite3.Connection, schema: str) -> None:
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 0:
        raise RuntimeError(f"invalid database schema version: {version}")
    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f"unsupported future database schema version: {version}")
    if version == CURRENT_SCHEMA_VERSION:
        _validate_current_schema(conn, schema)
        return
    if version == 0:
        if not _table_names(conn):
            conn.execute("BEGIN IMMEDIATE")
            try:
                _apply_schema(conn, schema, {"all"})
                _extra_indexes(conn)
                _migration_002_backfill_domain_data(conn, schema)
                _validate_current_schema(conn, schema)
                conn.execute(f"PRAGMA user_version = {CURRENT_SCHEMA_VERSION}")
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            return
        _admit_unversioned_legacy(conn, schema)
    for next_version in range(max(version, 0) + 1, CURRENT_SCHEMA_VERSION + 1):
        conn.execute("BEGIN IMMEDIATE")
        try:
            MIGRATIONS[next_version - 1](conn, schema)
            if next_version == CURRENT_SCHEMA_VERSION:
                _validate_current_schema(conn, schema)
            conn.execute(f"PRAGMA user_version = {next_version}")
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def _normalize_domain_names(conn: sqlite3.Connection) -> None:
    """기존 settlement/타인정산 표기를 가족카드 도메인으로 통일한다."""
    conn.execute(
        """
        UPDATE monthly_panels
        SET panel_type = 'family_card', updated_at = CURRENT_TIMESTAMP
        WHERE panel_type = 'settlement'
        """
    )
    conn.execute(
        """
        UPDATE app_labels
        SET key = 'panel_family_card_title', updated_at = CURRENT_TIMESTAMP
        WHERE key = 'panel_settlement_title'
          AND NOT EXISTS (SELECT 1 FROM app_labels WHERE key = 'panel_family_card_title')
        """
    )


def _migrate_liquidity_names(conn: sqlite3.Connection) -> None:
    """1단계 저장 key를 최종 중립 이름으로 원자적이고 반복 가능하게 옮긴다."""
    for legacy_key, current_key in LEGACY_LIQUIDITY_SETTING_KEYS.items():
        _migrate_named_value(
            conn,
            "app_settings",
            legacy_key,
            current_key,
            LIQUIDITY_SETTING_DEFAULTS[current_key],
        )
    for legacy_key, current_key in LEGACY_LIQUIDITY_LABEL_KEYS.items():
        _migrate_named_value(
            conn,
            "app_labels",
            legacy_key,
            current_key,
            LIQUIDITY_LABEL_DEFAULTS[current_key],
            normalize_legacy=lambda value, key=legacy_key: normalized_legacy_label_value(key, value),
        )


def _migrate_named_value(
    conn: sqlite3.Connection,
    table: str,
    legacy_key: str,
    current_key: str,
    default_value: str,
    normalize_legacy: Callable[[str], str] | None = None,
) -> None:
    rows = {
        row["key"]: row["value"]
        for row in conn.execute(
            f"SELECT key, value FROM {table} WHERE key IN (?, ?)",
            (legacy_key, current_key),
        ).fetchall()
    }
    legacy_value = rows.get(legacy_key)
    if legacy_value is not None and normalize_legacy is not None:
        legacy_value = normalize_legacy(legacy_value)
    current_value = rows.get(current_key)
    if legacy_value is not None and current_value is not None and legacy_value != current_value:
        raise RuntimeError(
            f"conflicting {table} values for {legacy_key} and {current_key}",
        )
    if current_value is not None:
        conn.execute(f"DELETE FROM {table} WHERE key = ?", (legacy_key,))
        return
    if legacy_value is not None:
        conn.execute(
            f"UPDATE {table} SET key = ?, value = ?, updated_at = CURRENT_TIMESTAMP WHERE key = ?",
            (current_key, legacy_value, legacy_key),
        )
        return
    conn.execute(
        f"INSERT INTO {table}(key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
        (current_key, default_value),
    )


def _drop_legacy_column(conn: sqlite3.Connection, table: str, column: str) -> None:
    """현재 스키마에서 제거된 컬럼은 가능할 때만 물리적으로 정리한다."""
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in columns:
        return
    try:
        conn.execute(f"ALTER TABLE {table} DROP COLUMN {column}")
    except sqlite3.OperationalError:
        return


def _normalize_money_settings(conn: sqlite3.Connection) -> None:
    """돈 단위 설정값은 기존 소수 표기를 정수 문자열로 정리한다."""
    keys = {
        "scheduled_income",
        "base_next_month_liquidity",
        "cash_flow_balance",
        "liquidity_status",
        "card_limit",
    }
    rows = conn.execute(
        f"SELECT key, value FROM app_settings WHERE key IN ({','.join('?' for _ in keys)})",
        tuple(keys),
    ).fetchall()
    for row in rows:
        try:
            amount = float(row["value"])
        except ValueError:
            continue
        if amount.is_integer():
            conn.execute(
                """
                UPDATE app_settings
                SET value = ?, updated_at = CURRENT_TIMESTAMP
                WHERE key = ?
                """,
                (str(int(amount)), row["key"]),
            )


def _backfill_planned_due_days(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT id, title
        FROM ledger_entries
        WHERE book_section = 'current'
          AND entry_kind = 'planned'
          AND due_day IS NULL
        """
    ).fetchall()
    for row in rows:
        match = re.search(r"매월\s*(\d{1,2})\s*일", row["title"] or "")
        if not match:
            continue
        due_day = int(match.group(1))
        if 1 <= due_day <= 31:
            conn.execute(
                """
                UPDATE ledger_entries
                SET due_day = ?, date_label = '카드 정기결제', group_label = '카드 정기결제',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (due_day, row["id"]),
            )
