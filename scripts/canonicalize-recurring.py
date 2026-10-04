#!/usr/bin/env python3
"""Explicit owner-approved offline operation. Default is non-mutating dry-run."""

import argparse
import json
import os
from pathlib import Path
import sys
import sqlite3

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from app.services.recurring_canonicalization import encode_document, execute  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--approved-manifest-sha256', required=True)
    parser.add_argument('--verified-backup', type=Path, required=True)
    parser.add_argument('--backup-sha256', required=True)
    parser.add_argument('--dry-run-receipt', type=Path)
    parser.add_argument('--receipt-sha256')
    parser.add_argument('--report', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--dry-run', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    # Exclusive private report creation prevents overwriting any artifact,
    # target, manifest or backup, including through a symlink/hardlink alias.
    try:
        fd = os.open(args.report, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as report:
            result = execute(args.db, args.manifest.read_bytes(), args.approved_manifest_sha256,
                args.verified_backup, args.backup_sha256, apply=args.apply,
                receipt=args.dry_run_receipt.read_bytes() if args.dry_run_receipt else None,
                receipt_sha256=args.receipt_sha256)
            report.write(encode_document(result))
            report.flush()
            os.fsync(report.fileno())
        print(json.dumps({'mode': result['mode'], 'mapping_count': result['mapping_count'],
                          'financial_difference_won': 0, 'report': str(args.report)}))
        return 0
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
        # A report filesystem/transport failure after apply can be ambiguous:
        # do not imply rollback, rerun or invent a new manifest automatically.
        print(f'operation not confirmed: {exc}; inspect DB/report before retry', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
