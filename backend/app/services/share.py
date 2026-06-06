from __future__ import annotations

from html import escape

from app.repository import list_cash_flows, list_entries, list_labels, list_panels, list_settings
from app.services.discounts import effective_card_discount
from app.services.judgment import claim_ledger_note, format_won, shared_panel_subtitle
from app.services.month import calendar_month_label


PANEL_TITLES = {
    "claim": ("panel_claim_title", "청구"),
    "settlement": ("panel_settlement_title", "타인정산"),
}


def shared_panel(panel_type: str) -> dict:
    if panel_type not in PANEL_TITLES:
        raise ValueError("unknown shared panel type")
    month = calendar_month_label()
    rows = [
        panel
        for panel in list_panels(month)
        if panel.get("panel_type") == panel_type and panel.get("title")
    ]
    total = sum(_panel_net_amount(row) for row in rows)
    current_card_total = sum(row.get("amount_value") or 0 for row in list_entries("current"))
    settings = list_settings()
    card_limit = _float_setting(settings, "settlement_card_limit", 5_800_000)
    label_key, fallback = PANEL_TITLES[panel_type]
    title = list_labels().get(label_key, fallback)
    return {
        "month": month,
        "panel_type": panel_type,
        "title": title,
        "subtitle": shared_panel_subtitle(panel_type, rows, total, current_card_total, card_limit),
        "ledger_note": _ledger_note(panel_type, month),
        "rows": rows,
        "total": total,
    }


def shared_panel_html(panel_type: str) -> str:
    data = shared_panel(panel_type)
    rows_html = "\n".join(_row_html(row) for row in data["rows"])
    if not rows_html:
        rows_html = '<tr><td colspan="2" class="empty">표시할 항목이 없습니다.</td></tr>'
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(data["title"])} - money-note</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f7f7f4;
      color: #242424;
    }}
    body {{
      margin: 0;
      padding: 28px 16px;
    }}
    main {{
      max-width: 720px;
      margin: 0 auto;
      background: #fff;
      border: 1px solid #ddd8ce;
      border-radius: 8px;
      overflow: hidden;
    }}
    header {{
      padding: 20px 22px 14px;
      border-bottom: 1px solid #e8e3d8;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 24px;
      line-height: 1.25;
    }}
    .month {{
      color: #666;
      font-size: 14px;
    }}
    .subtitle {{
      margin-top: 12px;
      padding: 10px 12px;
      border-radius: 6px;
      background: #f7f2e8;
      color: #5d4b2f;
      font-size: 14px;
      line-height: 1.45;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 12px 14px;
      border-bottom: 1px solid #ece8df;
      vertical-align: top;
    }}
    th {{
      text-align: left;
      background: #faf8f2;
      font-size: 13px;
      color: #555;
    }}
    td.amount, th.amount {{
      text-align: right;
      white-space: nowrap;
      width: 140px;
    }}
    tfoot td {{
      font-weight: 700;
      background: #faf8f2;
      border-bottom: 0;
      font-size: 17px;
    }}
    .empty {{
      color: #777;
      text-align: center;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(data["title"])}</h1>
      <div class="month">{escape(data["month"])}</div>
      <div class="subtitle">{escape(data["subtitle"])}</div>
    </header>
    <table>
      <thead>
        <tr><th>내용</th><th class="amount">금액</th></tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
      <tfoot>
        <tr><td>합계</td><td class="amount">{format_won(data["total"])}</td></tr>
      </tfoot>
    </table>
    {_ledger_note_html(data["ledger_note"])}
  </main>
</body>
</html>
"""


def _row_html(row: dict) -> str:
    discount = _panel_discount_amount(row)
    amount_text = format_won(_panel_net_amount(row))
    if discount > 0:
        amount_text = f"{amount_text}<small>할인 -{format_won(discount)}</small>"
    return (
        "<tr>"
        f"<td>{escape(str(row.get('title') or ''))}</td>"
        f"<td class=\"amount\">{amount_text}</td>"
        "</tr>"
    )


def _panel_net_amount(row: dict) -> float:
    return max(0, float(row.get("amount_value") or 0) - _panel_discount_amount(row))


def _panel_discount_amount(row: dict) -> float:
    if row.get("panel_type") not in {"claim", "settlement"}:
        return 0.0
    settings = list_settings()
    scope = "family" if row.get("panel_type") == "settlement" else "owner"
    policy = settings.get(f"card_discount_policy:{scope}:{row.get('month')}", "undecided")
    return effective_card_discount(
        row.get("amount_value"),
        row.get("discount_amount"),
        bool(row.get("discount_override") or row.get("discount_amount")),
        policy,
    )


def _ledger_note_html(note: str | None) -> str:
    if not note:
        return ""
    return f'<div class="subtitle">{escape(note)}</div>'


def _ledger_note(panel_type: str, month: str) -> str | None:
    if panel_type != "claim":
        return None
    return claim_ledger_note(month, [*list_entries("archive"), *list_entries("current")], list_cash_flows())


def _float_setting(settings: dict[str, str], key: str, fallback: float) -> float:
    try:
        return float(settings.get(key, fallback))
    except (TypeError, ValueError):
        return fallback
