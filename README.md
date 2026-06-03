# money-note

Personal money ledger service that preserves the current Excel workbook workflow while making the current month editable from desktop and mobile clients.

The intended source of truth is the server database. Excel files are imported as seed data and exported as portable snapshots.

## Current Plan

- Backend: FastAPI, SQLite, openpyxl
- Deployment: Docker Compose on Ubuntu 24.04
- Clients: Flutter for macOS and Android, after the API stabilizes
- Workbook shape:
  - `당월 기록`: current month operating sheet
  - `전체 기록(본인)`: archived ledger

## Quick Start

Copy the current workbook into `data/template.xlsx`, then import it:

```bash
mkdir -p data exports
cp /path/to/금전사용기록.xlsx data/template.xlsx
docker compose run --rm api python scripts/import_xlsx.py /app/data/template.xlsx --replace
```

Start the server:

```bash
docker compose up --build
```

The API will be available at `http://localhost:8080`.

## Useful API Calls

Detailed Korean specifications:

- [API 명세](docs/api.md)
- [DB 명세](docs/database.md)

```bash
curl http://localhost:8080/health
curl http://localhost:8080/api/month/current/summary
curl http://localhost:8080/api/entries/current
curl http://localhost:8080/api/month/current/panels
curl http://localhost:8080/api/share/claim
curl http://localhost:8080/api/share/settlement
curl -X POST http://localhost:8080/api/export
curl -O http://localhost:8080/api/export/latest.xlsx
```

Read-only browser views:

- `http://localhost:8080/share/claim`
- `http://localhost:8080/share/settlement`

Close the current month:

```bash
curl -X POST http://localhost:8080/api/month/current/close
```

The close operation appends non-planned current entries to the dynamic archive and leaves planned `나갈 돈` rows in the current month.

Append a planned `나갈 돈` item:

```bash
curl -X POST http://localhost:8080/api/month/current/planned \
  -H 'Content-Type: application/json' \
  -d '{"title":"[매월 n일] 새 예정 지출","amount_value":12345}'
```

Reorder current or planned entries:

```bash
curl -X POST http://localhost:8080/api/month/current/reorder \
  -H 'Content-Type: application/json' \
  -d '{"ordered_ids":[3,1,2]}'

curl -X POST http://localhost:8080/api/month/current/planned/reorder \
  -H 'Content-Type: application/json' \
  -d '{"ordered_ids":[28,23,24]}'
```

## Data Directories

- `data/`: SQLite database and optional workbook template
- `exports/`: generated `.xlsx` snapshots

These directories are intentionally ignored by git.
