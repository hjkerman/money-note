# Architecture

## Goals

- Keep the existing one-workbook habit: current month plus full history in one `.xlsx`.
- Make current-month editing possible from macOS and Android clients.
- Keep the database as the source of truth to avoid workbook locking and sync conflicts.
- Export an `.xlsx` snapshot on demand and on a schedule.

## Workbook Findings

The source workbook has two visible sheets:

- `당월 기록`: current-month operating board.
- `전체 기록(본인)`: archived ledger.

`당월 기록` is not a single table. It has several panels:

- `B:D`: planned/current card spending.
- `F:G`: fixed, frozen, claims, and settlement panels.
- `I:J`: summary and liquidity calculations.

`전체 기록(본인)` is mostly a ledger in `B:D`, with occasional auxiliary values in `E:F`. Date cells in `B` are often merged over multiple rows.

## Data Model

The server stores ledger rows as structured records while preserving original workbook expressions:

- `amount_value`: computed amount when known.
- `amount_expr`: original formula/expression such as `=4800-57`.
- `aux_amount_value` and `aux_amount_expr`: optional `E` column data.
- `extra_value`: optional `F` column data.
- `group_label`: non-date labels such as `나갈 돈`, `청구`, or `미룬이`.

## Export Policy

Exports regenerate the two-sheet workbook:

1. Write `당월 기록` from current entries and monthly panels.
2. Write `전체 기록(본인)` from archived entries.
3. Merge repeated date labels in the archive sheet.
4. Preserve formulas when `amount_expr` or `aux_amount_expr` is present.

The first implementation favors structural fidelity over pixel-perfect styling. A template workbook can be mounted at `data/template.xlsx` for future style preservation.

