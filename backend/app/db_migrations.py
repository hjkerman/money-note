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


# Git's supported unversioned schemas introduce these families at distinct
# times. The absence of a column is safe to migrate only in an era where it
# never existed; a lost financial input or relationship must not get a default.
CORE_TABLES = frozenset({
    "ledger_entries", "monthly_panels", "cash_flows", "app_settings", "app_labels",
    "users", "auth_sessions", "share_sessions", "card_payment_events",
    "card_payment_allocations", "card_payment_deferrals", "audit_logs",
})
BATCH_TABLES = frozenset({"card_payment_batches", "card_payment_batch_items"})
NOTIFICATION_TABLES = frozenset({"notification_candidate_registrations"})
RECONCILIATION_TABLES = frozenset({"offline_reconciliations", "offline_reconciliation_operations"})
REVISION_TABLES = frozenset({"authoritative_state_revision"})

ERA_TABLES = {
    "pre_batch": CORE_TABLES,
    "card_batches": CORE_TABLES | BATCH_TABLES,
    "fixed_expenses": CORE_TABLES | BATCH_TABLES,
    "pre_notification": CORE_TABLES | BATCH_TABLES,
    "notification": CORE_TABLES | BATCH_TABLES | NOTIFICATION_TABLES,
    "offline_phase2": CORE_TABLES | BATCH_TABLES | NOTIFICATION_TABLES | RECONCILIATION_TABLES,
    "current": CORE_TABLES | BATCH_TABLES | NOTIFICATION_TABLES | RECONCILIATION_TABLES | REVISION_TABLES,
}
ERA_FUTURE_COLUMNS = {
    "pre_batch": {
        "ledger_entries": {"source_planned_entry_id"},
        "monthly_panels": {"confirmed_cash_flow_id", "confirmed_month"},
        "card_payment_events": {"batch_id", "idempotency_key", "request_fingerprint"},
    },
    "card_batches": {
        "ledger_entries": {"source_planned_entry_id"},
        "monthly_panels": {"confirmed_cash_flow_id", "confirmed_month"},
        "card_payment_events": {"idempotency_key", "request_fingerprint"},
    },
    "fixed_expenses": {
        "ledger_entries": {"source_planned_entry_id"},
        "monthly_panels": {"confirmed_month"},
        "card_payment_events": {"idempotency_key", "request_fingerprint"},
    },
    "pre_notification": {},
    "notification": {},
    "offline_phase2": {
        "offline_reconciliations": {"fingerprint_version", "request_fingerprint"},
    },
    "current": {},
}

# Identity and relationships present in every supported era in which their
# table/column exists. Migration 001 adds the later source/link columns.
PRIMARY_KEYS = {
    "ledger_entries": ("id",), "monthly_panels": ("id",),
    "cash_flows": ("id",), "app_settings": ("key",),
    "app_labels": ("key",), "users": ("id",),
    "auth_sessions": ("id",), "share_sessions": ("id",),
    "card_payment_events": ("id",), "card_payment_allocations": ("id",),
    "card_payment_deferrals": ("entry_payment_key",), "audit_logs": ("id",),
    "card_payment_batches": ("id",), "card_payment_batch_items": ("id",),
    "notification_candidate_registrations": ("registration_key",),
    "offline_reconciliations": ("reconciliation_id",),
    "offline_reconciliation_operations": ("operation_id",),
    "authoritative_state_revision": ("id",),
}
UNIQUE_IDENTITIES = {
    "users": (("username",),),
    "auth_sessions": (("session_token_hash",),),
    "share_sessions": (("session_token_hash",),),
    "card_payment_batch_items": (("batch_id", "entry_payment_key"),),
    "offline_reconciliation_operations": (("reconciliation_id", "sequence"),),
}
FOREIGN_KEYS = {
    "auth_sessions": (("user_id", "users", "id", "CASCADE"),),
    "card_payment_allocations": (("payment_event_id", "card_payment_events", "id", "CASCADE"),),
    "card_payment_events": (
        ("cash_flow_id", "cash_flows", "id", "SET NULL"),
        ("batch_id", "card_payment_batches", "id", "CASCADE"),
    ),
    "card_payment_batch_items": (
        ("batch_id", "card_payment_batches", "id", "CASCADE"),
        ("entry_id", "ledger_entries", "id", "CASCADE"),
    ),
    "monthly_panels": (("confirmed_cash_flow_id", "cash_flows", "id", "SET NULL"),),
    "ledger_entries": (("source_planned_entry_id", "ledger_entries", "id", "SET NULL"),),
    "offline_reconciliation_operations": (
        ("reconciliation_id", "offline_reconciliations", "reconciliation_id", "RESTRICT"),
    ),
}


def _admit_unversioned_legacy(conn: sqlite3.Connection, schema: str) -> None:
    expected = _expected_tables_and_columns(schema)
    present = _table_names(conn)
    if not CORE_TABLES.issubset(present):
        raise RuntimeError("unknown unversioned database schema: missing historical core tables")
    if present - set(expected) - {"installments"}:
        raise RuntimeError("unknown unversioned database schema: unfamiliar tables")
    revision_triggers = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'revision_%' LIMIT 1"
    ).fetchone()
    if revision_triggers is not None and "authoritative_state_revision" not in present:
        raise RuntimeError("unknown unversioned database schema: missing revision state table")
    columns = {
        table: {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
        for table in present & set(expected)
    }
    # Choose the newest independently evidenced family. A missing member of
    # that family then fails admission instead of being recreated empty.
    modern_financial_marker = any((
        "source_planned_entry_id" in columns["ledger_entries"],
        "confirmed_month" in columns["monthly_panels"],
        "idempotency_key" in columns["card_payment_events"],
        "request_fingerprint" in columns["card_payment_events"],
    ))
    fixed_marker = "confirmed_cash_flow_id" in columns["monthly_panels"] or (
        {"panel_type", "confirmed_at"}.issubset(columns["monthly_panels"])
        and conn.execute(
            "SELECT 1 FROM monthly_panels WHERE panel_type = 'fixed' "
            "AND confirmed_at IS NOT NULL LIMIT 1"
        ).fetchone() is not None
    )
    batch_marker = bool(present & BATCH_TABLES) or "batch_id" in columns["card_payment_events"]
    if "authoritative_state_revision" in present:
        era = "current"
        # This era already had the complete runtime schema. Do not let the
        # numbered CREATE IF NOT EXISTS path repair away evidence of damage.
        try:
            _validate_current_schema(conn, schema)
        except RuntimeError as exc:
            raise RuntimeError(f"unknown unversioned database schema: {exc}") from exc
    elif present & RECONCILIATION_TABLES:
        era = "offline_phase2"
    elif present & NOTIFICATION_TABLES:
        era = "notification"
    elif modern_financial_marker:
        era = "pre_notification"
    elif fixed_marker:
        era = "fixed_expenses"
    elif batch_marker:
        era = "card_batches"
    else:
        era = "pre_batch"
    era_tables = ERA_TABLES[era]
    if not era_tables.issubset(present):
        raise RuntimeError("unknown unversioned database schema: missing era-required tables")
    for table in present & set(expected):
        actual = columns[table]
        allowed = expected[table] | ({"discount_checked"} if table in {"ledger_entries", "monthly_panels"} else set())
        required_columns = expected[table] - ERA_FUTURE_COLUMNS[era].get(table, set())
        if not actual.issubset(allowed) or not required_columns.issubset(actual):
            raise RuntimeError(f"unknown unversioned database schema: {table} columns")
    _validate_critical_structure(conn, era_tables, columns, "unknown unversioned database schema")


def _has_unique_columns(conn: sqlite3.Connection, table: str, columns: tuple[str, ...]) -> bool:
    return any(
        index[2] and not index[4]
        and tuple(row[2] for row in conn.execute(f"PRAGMA index_info({index[1]})")) == columns
        for index in conn.execute(f"PRAGMA index_list({table})")
    )


def _validate_critical_structure(
    conn: sqlite3.Connection, tables: set[str] | frozenset[str],
    columns: dict[str, set[str]], error_prefix: str,
) -> None:
    for table in tables:
        actual_pk_rows = sorted(
            (row for row in conn.execute(f"PRAGMA table_info({table})") if row[5]),
            key=lambda row: row[5],
        )
        actual_pk = tuple(row[1] for row in actual_pk_rows)
        if actual_pk != PRIMARY_KEYS[table] or any(
            row[2].upper() != ("INTEGER" if row[1] == "id" else "TEXT")
            for row in actual_pk_rows
        ):
            raise RuntimeError(f"{error_prefix}: {table} primary key")
        if actual_pk == ("id",) and table != "authoritative_state_revision":
            # INTEGER PRIMARY KEY DESC looks identical in table_info, but has
            # a separate PK index: INSERT.lastrowid is then not the stored id.
            indexes = conn.execute(f"PRAGMA index_list({table})").fetchall()
            table_sql = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)
            ).fetchone()[0]
            try:
                conn.execute(f"SELECT rowid FROM {table} LIMIT 0")
            except sqlite3.OperationalError as exc:
                raise RuntimeError(f"{error_prefix}: {table} primary key") from exc
            if any(index[3] == "pk" for index in indexes) or not re.search(
                r"\bid\s+INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b", table_sql, re.IGNORECASE,
            ):
                raise RuntimeError(f"{error_prefix}: {table} primary key")
        for unique_columns in UNIQUE_IDENTITIES.get(table, ()):
            if not _has_unique_columns(conn, table, unique_columns):
                raise RuntimeError(f"{error_prefix}: {table} unique identity")
        expected_fks = {
            relationship for relationship in FOREIGN_KEYS.get(table, ())
            if relationship[0] in columns[table]
        }
        actual_fks = {
            (row[3], row[2], row[4], row[6])
            for row in conn.execute(f"PRAGMA foreign_key_list({table})")
        }
        if actual_fks != expected_fks:
            raise RuntimeError(f"{error_prefix}: {table} foreign keys")
    if "idempotency_key" in columns["card_payment_events"]:
        indexes = {
            row[1]: row for row in conn.execute("PRAGMA index_list(card_payment_events)")
        }
        index = indexes.get("idx_card_payment_events_idempotency")
        if index is not None and (
            not index[2] or not index[4]
            or tuple(row[2] for row in conn.execute(
                "PRAGMA index_info(idx_card_payment_events_idempotency)"
            )) != ("idempotency_key",)
            or not re.search(
                r"\bWHERE\s+idempotency_key\s+IS\s+NOT\s+NULL\s*$",
                str(conn.execute(
                    "SELECT sql FROM sqlite_master WHERE type = 'index' AND name = ?",
                    ("idx_card_payment_events_idempotency",),
                ).fetchone()[0]),
                re.IGNORECASE,
            )
        ):
            raise RuntimeError(f"{error_prefix}: card payment idempotency index")


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
    _validate_critical_structure(conn, expected_tables, expected, "current database version has invalid")
    names = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('index', 'trigger')")}
    required_objects = set(re.findall(
        r"CREATE (?:UNIQUE )?INDEX IF NOT EXISTS ([a-z_]+)|CREATE TRIGGER IF NOT EXISTS ([a-z_]+)",
        schema,
    ))
    required_names = {name for pair in required_objects for name in pair if name}
    required_names.update({"idx_ledger_payment_key", "idx_ledger_source_planned", "idx_card_payment_events_idempotency"})
    if not required_names.issubset(names):
        raise RuntimeError("current database version has missing critical indexes or triggers")
    _validate_revision_triggers(conn, schema)
    # The named partial index is checked for uniqueness, columns and predicate
    # above; unlike table-level identity constraints it is intentionally partial.


def _revision_trigger_contract(sql: str) -> tuple[str, str, str, tuple[str, ...]] | None:
    # Ignore layout/case, identifier quoting and comments, not semantic clauses.
    sql = re.sub(r"/\*.*?\*/|--[^\n]*", " ", sql, flags=re.DOTALL)
    sql = re.sub(r'["`\[\]]', "", sql)
    match = re.fullmatch(
        r"\s*CREATE\s+TRIGGER\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+"
        r"AFTER\s+(INSERT|UPDATE|DELETE)\s+ON\s+(\w+)\s+BEGIN\s+(.*?)\s*END\s*;?\s*",
        sql, re.IGNORECASE | re.DOTALL,
    )
    if match is None:
        return None
    return (match[1].lower(), match[2].upper(), match[3].lower(),
            tuple(re.findall(r"\w+|[^\w\s]", match[4].lower())))


def _validate_revision_triggers(conn: sqlite3.Connection, schema: str) -> None:
    expected = [_revision_trigger_contract(statement) for statement in _statements(schema)
                if re.match(r"CREATE TRIGGER IF NOT EXISTS revision_", statement)]
    trigger_rows = conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='trigger'").fetchall()
    actual = {row[0]: (row[1], _revision_trigger_contract(row[2] or "")) for row in trigger_rows}
    expected_names = {contract[0] for contract in expected if contract is not None}
    revision_tables = {contract[2] for contract in expected if contract is not None}
    for name, table, sql in trigger_rows:
        if name not in expected_names and (
            table in revision_tables or "authoritative_state_revision" in str(sql).lower()
        ):
            raise RuntimeError("current database version has unexpected authoritative revision trigger")
    for contract in expected:
        if contract is None or actual.get(contract[0]) != (contract[2], contract):
            raise RuntimeError("current database version has invalid authoritative revision trigger")
    state = conn.execute("SELECT id, revision, typeof(revision) FROM authoritative_state_revision").fetchall()
    if len(state) != 1 or state[0][0] != 1 or state[0][2] != "integer" or state[0][1] < 0:
        raise RuntimeError("current database version has invalid authoritative revision state")


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
