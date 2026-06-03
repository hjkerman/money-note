from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import re
import sqlite3

from app.config import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS ledger_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    book_section TEXT NOT NULL CHECK (book_section IN ('current', 'archive')),
    entry_kind TEXT NOT NULL DEFAULT 'expense',
    entry_date TEXT,
    date_label TEXT,
    group_label TEXT,
    title TEXT NOT NULL DEFAULT '',
    usage_place TEXT,
    usage_item TEXT,
    amount_value REAL,
    amount_expr TEXT,
    aux_amount_value REAL,
    aux_amount_expr TEXT,
    extra_value TEXT,
    sort_order INTEGER NOT NULL,
    due_day INTEGER,
    confirmed_at TEXT,
    spending_category TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS archive_rows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_row INTEGER NOT NULL,
    b_value TEXT,
    c_value TEXT,
    d_value REAL,
    e_value TEXT,
    f_value TEXT,
    merge_down INTEGER NOT NULL DEFAULT 0,
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monthly_panels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    panel_type TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    amount_value REAL,
    amount_expr TEXT,
    sort_order INTEGER NOT NULL,
    due_day INTEGER,
    confirmed_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS workbook_labels (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cash_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_on TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    amount_value REAL NOT NULL,
    sort_order INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS installments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL DEFAULT '',
    principal_amount REAL NOT NULL,
    fee_rate REAL NOT NULL DEFAULT 0,
    fee_amount REAL NOT NULL DEFAULT 0,
    months INTEGER NOT NULL,
    remaining_months INTEGER NOT NULL,
    start_month TEXT NOT NULL,
    sort_order INTEGER NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ledger_section_order
ON ledger_entries(book_section, sort_order);

CREATE INDEX IF NOT EXISTS idx_ledger_date
ON ledger_entries(entry_date);

CREATE INDEX IF NOT EXISTS idx_archive_rows_order
ON archive_rows(sort_order);

CREATE INDEX IF NOT EXISTS idx_panels_month_type_order
ON monthly_panels(month, panel_type, sort_order);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token
ON auth_sessions(session_token_hash);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
ON auth_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_cash_flows_order
ON cash_flows(occurred_on, sort_order, id);

CREATE INDEX IF NOT EXISTS idx_installments_active_order
ON installments(is_active, sort_order, id);

INSERT OR IGNORE INTO app_settings(key, value) VALUES
('base_next_month_liquidity', '400000'),
('interest_expense', '0'),
('liquidity_status', '0'),
('settlement_card_limit', '5800000');

INSERT OR IGNORE INTO workbook_labels(key, value) VALUES
('current_header_date', '날짜'),
('current_header_title', '적요'),
('current_header_amount', '금액'),
('archive_header_date', '날짜'),
('archive_header_title', '적요'),
('archive_header_amount', '금액'),
('panel_fixed_title', '현금성 고정지출'),
('panel_frozen_title', '동결'),
('panel_claim_title', '청구'),
('panel_settlement_title', '타인정산'),
('panel_header_title', '적요'),
('panel_header_amount', '금액'),
('summary_title', '요약'),
('summary_card_total_label', '카드대금'),
('summary_transfer_or_deposit_label', '송금/예치'),
('summary_interest_expense_label', '이자지출'),
('summary_frozen_asset_label', '동결자산'),
('summary_liquidity_status_label', '유동성 현황'),
('summary_next_month_liquidity_label', '익월 유동성');
"""


def connect() -> sqlite3.Connection:
    settings = get_settings()
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """서버 시작 시 필요한 테이블과 누락된 컬럼을 보강한다."""
    with connect() as conn:
        conn.executescript(SCHEMA)
        panel_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(monthly_panels)").fetchall()
        }
        if "confirmed_at" not in panel_columns:
            conn.execute("ALTER TABLE monthly_panels ADD COLUMN confirmed_at TEXT")
        if "due_day" not in panel_columns:
            conn.execute("ALTER TABLE monthly_panels ADD COLUMN due_day INTEGER")
        ledger_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(ledger_entries)").fetchall()
        }
        if "confirmed_at" not in ledger_columns:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN confirmed_at TEXT")
        if "due_day" not in ledger_columns:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN due_day INTEGER")
        if "spending_category" not in ledger_columns:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN spending_category TEXT")
        if "usage_place" not in ledger_columns:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN usage_place TEXT")
        if "usage_item" not in ledger_columns:
            conn.execute("ALTER TABLE ledger_entries ADD COLUMN usage_item TEXT")
        installment_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(installments)").fetchall()
        }
        if "fee_rate" not in installment_columns:
            conn.execute("ALTER TABLE installments ADD COLUMN fee_rate REAL NOT NULL DEFAULT 0")
        conn.execute(
            """
            UPDATE workbook_labels
            SET value = '현금성 고정지출', updated_at = CURRENT_TIMESTAMP
            WHERE key = 'panel_fixed_title' AND value = '고정지출'
            """
        )
        _backfill_planned_due_days(conn)


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


@contextmanager
def session() -> Iterator[sqlite3.Connection]:
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
