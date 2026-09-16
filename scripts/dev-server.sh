#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [[ "${1:-}" == --help ]]; then
  printf 'Usage: scripts/dev-server.sh\nIsolated API: 127.0.0.1:18081; database: work/dev-data/money-note.sqlite3\n'
  exit 0
fi
[[ $# -eq 0 ]] || exit 2
[[ "$ROOT_DIR" != /opt/money-note && "$ROOT_DIR" != /opt/money-note/* ]] || exit 1
[[ -x "$ROOT_DIR/.venv/bin/python" ]] || { printf 'Prepare .venv using docs/runbook.md first.\n' >&2; exit 1; }
# Never inherit production application settings into the developer process.
for name in ${!MONEY_NOTE_@}; do unset "$name"; done
export MONEY_NOTE_DB_PATH="$ROOT_DIR/work/dev-data/money-note.sqlite3"
export MONEY_NOTE_CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
export MONEY_NOTE_TRUST_PROXY_HEADERS=false
export MONEY_NOTE_COOKIE_SECURE=false
export MONEY_NOTE_APK_PATH=
"$ROOT_DIR/.venv/bin/python" - "$ROOT_DIR" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
target = root / 'work/dev-data'
if target.resolve() != target or Path(target / 'money-note.sqlite3').is_symlink():
    raise SystemExit('Developer data path must not contain symlinks')
target.mkdir(parents=True, exist_ok=True, mode=0o700)
PY
umask 077
cd "$ROOT_DIR/backend"
exec "$ROOT_DIR/.venv/bin/python" -m uvicorn app.main:app --host 127.0.0.1 --port 18081
