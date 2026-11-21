"""
Email edition of the daily brief.

Writes public/email/<date>.html (table layout + inline styles, which is what email
clients render reliably), a plain-text twin, and latest.html / latest.txt. Pith
does not send mail itself: point any newsletter service that imports HTML or
RSS (or a script of your own) at these files.

    python3 -m pipeline.email_edition
"""

import html
import os
from typing import Optional

from core.db import Database
from core.ledger import LedgerEngine

SITE_URL = os.environ.get("PITH_SITE_URL", "https://pith.news").rstrip("/")

INK, MUTED, RULE, BG, GILT = "#111111", "#5b5b5b", "#e4e2dc", "#faf9f6", "#8a6a2f"


def _e(text: Optional[str]) -> str:
    return html.escape(text or "", quote=True)


def _ledger_line(stats: dict) -> str:
    if stats["resolved_count"] == 0:
        return f"Forecast record: {stats['open_count']} open, none resolved yet."
    return (f"Forecast record: {stats['correct_count']} of {stats['resolved_count']} resolved forecasts correct, "
            f"Brier {stats['brier_score']:.3f}" + (" (preliminary)" if stats["is_preliminary"] else "") + ".")


def render_email(issue, stats: dict) -> tuple:
    """Returns (html, text) for one issue."""
    date_str = issue.date
    rows, text = [], [f"PITH · {date_str}", "The five shifts that matter today.", ""]
    for i, c in enumerate(issue.cards, 1):
        p = c.prediction
        forecast_html = (
            f'<p style="margin:10px 0 0;font:14px/1.5 Georgia,serif;color:{INK};">'
            f'<strong style="font-family:Menlo,monospace;color:{GILT};">{int(p.probability * 100)}%</strong> '
            f'{_e(p.statement)} <span style="color:{MUTED};">Resolves {_e(p.resolves_at)}.</span></p>'
        ) if p else ""
        rows.append(f"""
        <tr><td style="padding:22px 0;border-top:1px solid {RULE};">
          <p style="margin:0 0 4px;font:600 11px/1.4 Helvetica,Arial,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:{MUTED};">{i} · {_e(c.signal_level)} signal</p>
          <h2 style="margin:0 0 8px;font:700 19px/1.3 Georgia,serif;color:{INK};"><a href="{SITE_URL}/#{_e(c.id)}" style="color:{INK};text-decoration:none;">{_e(c.headline)}</a></h2>
          <p style="margin:0;font:15px/1.55 Georgia,serif;color:{INK};">{_e(c.what_happened)}</p>
          <p style="margin:8px 0 0;font:15px/1.55 Georgia,serif;color:{INK};"><strong>Why it matters:</strong> {_e(c.why_it_matters)}</p>
          {forecast_html}
        </td></tr>""")
        text += [f"{i}. {c.headline}", c.what_happened, f"Why it matters: {c.why_it_matters}"]
        if p:
            text.append(f"Forecast ({int(p.probability * 100)}%): {p.statement} Resolves {p.resolves_at}.")
        text += [f"{SITE_URL}/#{c.id}", ""]

    ignore_html = ""
    if issue.not_included_today:
        items = "".join(
            f'<li style="margin:0 0 6px;"><strong>{_e(n.headline)}</strong> <span style="color:{MUTED};">{_e(n.reason)}</span></li>'
            for n in issue.not_included_today
        )
        ignore_html = f"""
        <tr><td style="padding:22px 0;border-top:1px solid {RULE};">
          <h3 style="margin:0 0 8px;font:700 14px/1.4 Helvetica,Arial,sans-serif;color:{INK};">Safely ignore today</h3>
          <ul style="margin:0;padding-left:18px;font:14px/1.5 Georgia,serif;color:{INK};">{items}</ul>
        </td></tr>"""
        text += ["SAFELY IGNORE TODAY"] + [f"- {n.headline}: {n.reason}" for n in issue.not_included_today] + [""]

    ledger = _ledger_line(stats)
    text += [ledger, f"Full record: {SITE_URL}/ledger"]

    body = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pith · {_e(date_str)}</title></head>
<body style="margin:0;padding:0;background:{BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{BG};">
<tr><td align="center" style="padding:24px 16px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;">
    <tr><td style="padding:0 0 14px;">
      <p style="margin:0;font:700 22px/1.2 Georgia,serif;color:{INK};">Pith</p>
      <p style="margin:4px 0 0;font:13px/1.4 Helvetica,Arial,sans-serif;color:{MUTED};">{_e(date_str)} · {_e(issue.beat)} · the shifts that matter, nothing else</p>
    </td></tr>
    {"".join(rows)}
    {ignore_html}
    <tr><td style="padding:22px 0;border-top:1px solid {RULE};font:13px/1.5 Helvetica,Arial,sans-serif;color:{MUTED};">
      {_e(ledger)} <a href="{SITE_URL}/ledger" style="color:{INK};">See the full record</a>.
    </td></tr>
  </table>
</td></tr></table>
</body></html>
"""
    return body, "\n".join(text) + "\n"


def build_email_edition(db_path: str = "brief.sqlite3", output_dir: str = "public") -> Optional[str]:
    db = Database(db_path)
    issue = db.get_latest_issue()
    if not issue:
        return None
    stats = LedgerEngine.calculate_statistics(db.get_all_predictions())
    html_body, text_body = render_email(issue, stats)
    out = os.path.join(output_dir, "email")
    os.makedirs(out, exist_ok=True)
    for name in (issue.date, "latest"):
        with open(os.path.join(out, f"{name}.html"), "w", encoding="utf-8") as f:
            f.write(html_body)
        with open(os.path.join(out, f"{name}.txt"), "w", encoding="utf-8") as f:
            f.write(text_body)
    return os.path.join(out, f"{issue.date}.html")


if __name__ == "__main__":
    path = build_email_edition()
    print(f"Wrote {path}" if path else "No issue found.")
