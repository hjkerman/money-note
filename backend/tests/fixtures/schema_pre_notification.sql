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
    amount_value INTEGER,
    amount_expr TEXT,
    aux_amount_value INTEGER,
    aux_amount_expr TEXT,
    extra_value TEXT,
    sort_order INTEGER NOT NULL,
    due_day INTEGER,
    confirmed_at TEXT,
    confirmed_month TEXT,
    source_planned_entry_id INTEGER REFERENCES ledger_entries(id) ON DELETE SET NULL,
    spending_category TEXT,
    payment_key TEXT,
    discount_override INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS monthly_panels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL,
    panel_type TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    spent_on TEXT,
    amount_value INTEGER,
    discount_amount INTEGER NOT NULL DEFAULT 0,
    discount_override INTEGER NOT NULL DEFAULT 0,
    amount_expr TEXT,
    sort_order INTEGER NOT NULL,
    due_day INTEGER,
    confirmed_at TEXT,
    confirmed_month TEXT,
    confirmed_cash_flow_id INTEGER REFERENCES cash_flows(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_labels (
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

CREATE TABLE IF NOT EXISTS share_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cash_flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_on TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    amount_value INTEGER NOT NULL,
    sort_order INTEGER NOT NULL,
    is_primary_income INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS card_payment_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER REFERENCES card_payment_batches(id) ON DELETE CASCADE,
    event_date TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('immediate', 'discount')),
    total_amount INTEGER NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    cash_flow_id INTEGER REFERENCES cash_flows(id) ON DELETE SET NULL,
    idempotency_key TEXT,
    request_fingerprint TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS card_payment_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usage_month TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'month_close',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS card_payment_batch_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES card_payment_batches(id) ON DELETE CASCADE,
    entry_id INTEGER NOT NULL REFERENCES ledger_entries(id) ON DELETE CASCADE,
    entry_payment_key TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(batch_id, entry_payment_key)
);

CREATE TABLE IF NOT EXISTS card_payment_allocations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_event_id INTEGER NOT NULL REFERENCES card_payment_events(id) ON DELETE CASCADE,
    entry_payment_key TEXT NOT NULL,
    amount_value INTEGER NOT NULL CHECK (amount_value >= 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS card_payment_deferrals (
    entry_payment_key TEXT PRIMARY KEY,
    from_payment_month TEXT NOT NULL,
    target_payment_month TEXT NOT NULL,
    original_book_section TEXT,
    original_entry_date TEXT,
    original_date_label TEXT,
    original_group_label TEXT,
    original_title TEXT,
    original_sort_order INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actor_username TEXT NOT NULL DEFAULT 'anonymous',
    method TEXT NOT NULL,
    path TEXT NOT NULL,
    status_code INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ledger_section_order
ON ledger_entries(book_section, sort_order);

CREATE INDEX IF NOT EXISTS idx_ledger_date
ON ledger_entries(entry_date);

CREATE INDEX IF NOT EXISTS idx_panels_month_type_order
ON monthly_panels(month, panel_type, sort_order);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_token
ON auth_sessions(session_token_hash);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
ON auth_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_share_sessions_token
ON share_sessions(session_token_hash);

CREATE INDEX IF NOT EXISTS idx_cash_flows_order
ON cash_flows(occurred_on, sort_order, id);

CREATE INDEX IF NOT EXISTS idx_card_payment_allocations_entry
ON card_payment_allocations(entry_payment_key);

CREATE INDEX IF NOT EXISTS idx_card_payment_events_date
ON card_payment_events(event_date, id);

CREATE INDEX IF NOT EXISTS idx_card_payment_batches_active
ON card_payment_batches(status, id);

CREATE INDEX IF NOT EXISTS idx_card_payment_batch_items_batch
ON card_payment_batch_items(batch_id, entry_id);

CREATE INDEX IF NOT EXISTS idx_card_payment_batch_items_key
ON card_payment_batch_items(entry_payment_key);

CREATE INDEX IF NOT EXISTS idx_card_payment_deferrals_target
ON card_payment_deferrals(target_payment_month);

CREATE INDEX IF NOT EXISTS idx_audit_logs_occurred
ON audit_logs(occurred_at DESC, id DESC);

INSERT OR IGNORE INTO app_settings(key, value) VALUES
('card_limit', '5800000'),
('owner_card_last4', ''),
('family_card_last4', '');

INSERT OR IGNORE INTO app_labels(key, value) VALUES
('current_header_date', '날짜'),
('current_header_title', '세부내역'),
('current_header_amount', '금액'),
('archive_header_date', '날짜'),
('archive_header_title', '세부내역'),
('archive_header_amount', '금액'),
('panel_fixed_title', '현금성 고정지출'),
('panel_frozen_title', '동결'),
('panel_claim_title', '청구'),
('panel_family_card_title', '가족카드'),
('panel_header_title', '세부내역'),
('panel_header_amount', '금액'),
('summary_title', '요약'),
('summary_card_total_label', '카드대금'),
('summary_transfer_or_deposit_label', '고정지출'),
('summary_frozen_asset_label', '동결자산');
