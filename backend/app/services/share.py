from __future__ import annotations

from html import escape

from app.repository import list_labels, list_panels
from app.services.month import current_month_label


PANEL_TITLES = {
    "claim": ("panel_claim_title", "청구"),
    "settlement": ("panel_settlement_title", "타인정산"),
}


def shared_panel(panel_type: str) -> dict:
    if panel_type not in PANEL_TITLES:
        raise ValueError("unknown shared panel type")
    month = current_month_label()
    rows = [
        panel
        for panel in list_panels(month)
        if panel.get("panel_type") == panel_type and panel.get("title")
    ]
    total = sum(row.get("amount_value") or 0 for row in rows)
    label_key, fallback = PANEL_TITLES[panel_type]
    title = list_labels().get(label_key, fallback)
    return {
        "month": month,
        "panel_type": panel_type,
        "title": title,
        "subtitle": _subtitle(panel_type, rows, total),
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
        <tr><td>합계</td><td class="amount">{_format_won(data["total"])}</td></tr>
      </tfoot>
    </table>
  </main>
</body>
</html>
"""


def _row_html(row: dict) -> str:
    return (
        "<tr>"
        f"<td>{escape(str(row.get('title') or ''))}</td>"
        f"<td class=\"amount\">{_format_won(row.get('amount_value') or 0)}</td>"
        "</tr>"
    )


def _subtitle(panel_type: str, rows: list[dict], total: float) -> str:
    if panel_type == "claim":
        if not rows:
            return "이달은 평온했습니다. 이런 달도 있어야 사람이 삽니다."
        if total >= 200000:
            return "이달은 아팠습니다. 몸도 지갑도 같이 진료를 받았습니다."
        if any("치과" in str(row.get("title") or "") for row in rows):
            return "이달은 치아가 자본주의와 정면 충돌했습니다."
        return "생활은 계속되고, 영수증은 조용히 증언합니다."
    if not rows:
        return "이번 달 정산은 고요합니다. 평화가 숫자로 증명되었습니다."
    return "형제자매 간 평화를 위한 숫자 보고서입니다."


def _format_won(value: float) -> str:
    return f"{round(value):,}원"
