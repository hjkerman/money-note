from __future__ import annotations

from html import escape

from app.repository import list_cash_flows, list_entries, list_labels, list_panels, list_settings
from app.services.discounts import effective_card_discount, normalize_discount_policy
from app.services.judgment import claim_ledger_note, format_won, shared_panel_subtitle
from app.services.month import calendar_month_label


PANEL_TITLES = {
    "claim": ("panel_claim_title", "청구"),
    "family_card": ("panel_family_card_title", "가족카드"),
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
    discount_total = sum(_panel_discount_amount(row) for row in rows)
    minimum_rows = [row for row in rows if _is_minimum_payment_row(row, month)]
    minimum_total = sum(_panel_net_amount(row) for row in minimum_rows)
    minimum_discount_total = sum(_panel_discount_amount(row) for row in minimum_rows)
    current_card_total = sum(row.get("amount_value") or 0 for row in list_entries("current"))
    settings = list_settings()
    card_limit = _float_setting(settings, "card_limit", 5_800_000)
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
        "discount_total": discount_total,
        "minimum_total": minimum_total,
        "minimum_discount_total": minimum_discount_total,
    }


def shared_panel_html(panel_type: str) -> str:
    data = shared_panel(panel_type)
    rows_html = "\n".join(_row_html(row, data["month"]) for row in data["rows"])
    if not rows_html:
        rows_html = '<tr><td colspan="5" class="empty">표시할 항목이 없습니다.</td></tr>'
    net_total = sum(_panel_net_amount(row) for row in data["rows"])
    discount_total = sum(_panel_discount_amount(row) for row in data["rows"])
    minimum_rows = [row for row in data["rows"] if _is_minimum_payment_row(row, data["month"])]
    minimum_total = sum(_panel_net_amount(row) for row in minimum_rows)
    minimum_discount_total = sum(_panel_discount_amount(row) for row in minimum_rows)
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
      max-width: 860px;
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
    .share-actions {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 12px 22px;
      border-bottom: 1px solid #e8e3d8;
      background: #fffdfa;
    }}
    .share-actions button {{
      border: 1px solid #a7b899;
      border-radius: 999px;
      background: #eef5e9;
      color: #2f4b27;
      padding: 8px 13px;
      font-weight: 700;
      cursor: pointer;
    }}
    .minimum-total {{
      color: #5d4b2f;
      font-size: 13px;
      font-weight: 700;
      text-align: right;
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
    th.date, td.date {{
      white-space: nowrap;
      width: 104px;
    }}
    th.content, td.content {{
      min-width: 220px;
      width: auto;
    }}
    td.money, th.money {{
      text-align: right;
      white-space: nowrap;
      width: 104px;
    }}
    td.discount {{
      color: #7b5a2a;
    }}
    td.net {{
      font-weight: 700;
    }}
    tr.deferable-row {{
      transition: opacity 0.15s ease, color 0.15s ease;
    }}
    body.minimum-mode tr.deferable-row {{
      color: #9a958b;
      opacity: 0.45;
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
    @media (max-width: 640px) {{
      body {{
        padding: 12px 8px;
      }}
      main {{
        border-radius: 8px;
      }}
      th, td {{
        padding: 10px 8px;
      }}
      .share-actions {{
        padding: 10px 12px;
        align-items: flex-start;
        flex-direction: column;
      }}
      .minimum-total {{
        text-align: left;
      }}
      td.money, th.money {{
        width: auto;
        font-size: 14px;
      }}
      th.content, td.content {{
        min-width: 150px;
      }}
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
    <div class="share-actions">
      <button type="button" id="minimumToggle">최소 결제</button>
      <div class="minimum-total">최소 {format_won(minimum_total)} 결제 필요</div>
    </div>
    <table>
      <thead>
        <tr>
          <th class="date">사용일</th>
          <th class="content">내용</th>
          <th class="money">원금</th>
          <th class="money">할인액</th>
          <th class="money">할인 후 금액</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
      </tbody>
      <tfoot>
        <tr>
          <td>합계</td>
          <td class="money"></td>
          <td
            id="discountTotal"
            class="money discount"
            data-full="{escape(_discount_text(discount_total))}"
            data-minimum="{escape(_discount_text(minimum_discount_total))}"
          >{_discount_text(discount_total)}</td>
          <td
            id="netTotal"
            class="money net"
            data-full="{escape(format_won(net_total))}"
            data-minimum="{escape(format_won(minimum_total))}"
          >{format_won(net_total)}</td>
        </tr>
      </tfoot>
    </table>
    {_ledger_note_html(data["ledger_note"])}
  </main>
  <script>
    const button = document.getElementById("minimumToggle");
    const discountTotal = document.getElementById("discountTotal");
    const netTotal = document.getElementById("netTotal");
    button?.addEventListener("click", () => {{
      document.body.classList.toggle("minimum-mode");
      const minimumMode = document.body.classList.contains("minimum-mode");
      button.textContent = minimumMode ? "전체 보기" : "최소 결제";
      if (discountTotal) {{
        discountTotal.textContent = minimumMode ? discountTotal.dataset.minimum ?? "" : discountTotal.dataset.full ?? "";
      }}
      if (netTotal) {{
        netTotal.textContent = minimumMode ? netTotal.dataset.minimum ?? "" : netTotal.dataset.full ?? "";
      }}
    }});
  </script>
</body>
</html>
"""


def _row_html(row: dict, current_month: str) -> str:
    discount = _panel_discount_amount(row)
    original = float(row.get("amount_value") or 0)
    net = _panel_net_amount(row)
    row_class = "" if _is_minimum_payment_row(row, current_month) else ' class="deferable-row"'
    return (
        f"<tr{row_class}>"
        f"<td class=\"date\">{escape(_spent_on_label(row))}</td>"
        f"<td class=\"content\">{escape(str(row.get('title') or ''))}</td>"
        f"<td class=\"money\">{format_won(original)}</td>"
        f"<td class=\"money discount\">{_discount_text(discount)}</td>"
        f"<td class=\"money net\">{format_won(net)}</td>"
        "</tr>"
    )


def _spent_on_label(row: dict) -> str:
    value = str(row.get("spent_on") or "")
    if len(value) >= 10:
        return f"{value[:4]}.{value[5:7]}.{value[8:10]}."
    return value


def _is_minimum_payment_row(row: dict, current_month: str) -> bool:
    title = str(row.get("title") or "")
    if "이자" in title:
        return True
    spent_on = str(row.get("spent_on") or "")
    if not spent_on:
        return True
    spent_month = spent_on[:7]
    return spent_month < current_month


def _discount_text(discount: float) -> str:
    if discount <= 0:
        return "0원"
    return f"-{format_won(discount)}"


def _panel_net_amount(row: dict) -> float:
    return max(0, float(row.get("amount_value") or 0) - _panel_discount_amount(row))


def _panel_discount_amount(row: dict) -> float:
    if row.get("panel_type") not in {"claim", "family_card"}:
        return 0.0
    settings = list_settings()
    scope = "family" if row.get("panel_type") == "family_card" else "owner"
    policy = normalize_discount_policy(
        settings.get(f"card_discount_policy:{scope}:{row.get('month')}", "disabled" if scope == "family" else "enabled"),
        scope,
    )
    return effective_card_discount(
        row.get("amount_value"),
        row.get("discount_amount"),
        bool(row.get("discount_override") or row.get("discount_amount")),
        policy,
        row.get("title"),
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
