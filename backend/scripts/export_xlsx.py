from __future__ import annotations

import argparse
from pathlib import Path

from app.db import init_db
from app.config import get_settings
from app.repository import list_archive_rows, list_entries, list_labels, list_panels, list_settings
from app.services.workbook import export_workbook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--template", type=Path)
    args = parser.parse_args()

    init_db()
    hard_archive_rows = list_archive_rows()
    archive_entries = list_entries("archive")
    current_entries = list_entries("current")
    panels = list_panels()
    labels = list_labels()
    settings = list_settings()

    template_path = args.template or get_settings().template_path
    export_workbook(
        hard_archive_rows,
        archive_entries,
        current_entries,
        panels,
        labels,
        settings,
        args.output,
        template_path=template_path,
    )
    print(f"exported {args.output}")


if __name__ == "__main__":
    main()
