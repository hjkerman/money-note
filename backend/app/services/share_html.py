from __future__ import annotations

from html import escape

from app.services.judgment import format_won


def render_panel_row(
    *, row: dict, original: float, discount: float, net: float, deferable: bool
) -> str:
    row_class = ' class="deferable-row"' if deferable else ""
    return (
        f"<tr{row_class}>"
        f"<td class=\"content\">{escape(_content_label(row))}</td>"
        f"<td class=\"money\">{format_won(original)}</td>"
        f"<td class=\"money discount\">{_discount_text(discount)}</td>"
        f"<td class=\"money net\">{format_won(net)}</td>"
        "</tr>"
    )


def _content_label(row: dict) -> str:
    title = str(row.get("title") or "")
    date_label = _spent_on_short_label(row)
    return f"{date_label} {title}" if date_label else title


def _spent_on_short_label(row: dict) -> str:
    value = str(row.get("spent_on") or "")
    if len(value) >= 10:
        return f"[{value[5:7]}/{value[8:10]}]"
    return ""


def render_shared_panel_html(
    *,
    data: dict,
    rows_html: str,
    minimum_payment_label: str,
    net_total: float,
    discount_total: float,
    minimum_total: float,
    minimum_discount_total: float,
) -> str:
    """Render already calculated panel values without repository access."""
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
    .share-table-wrap {{
      width: 100%;
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
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
    th.content, td.content {{
      min-width: 280px;
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
      display: none;
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
        width: 96px;
        font-size: 14px;
      }}
      th.content, td.content {{
        min-width: 190px;
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
      <div class="minimum-total">{minimum_payment_label} 최소 결제 금액: {format_won(minimum_total)}</div>
    </div>
    <div class="share-table-wrap">
      <table>
        <thead>
          <tr>
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
    </div>
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


def _discount_text(discount: float) -> str:
    if discount <= 0:
        return "0원"
    return f"-{format_won(discount)}"


def _ledger_note_html(note: str | None) -> str:
    if not note:
        return ""
    return f'<div class="subtitle">{escape(note)}</div>'
