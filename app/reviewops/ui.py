"""Minimal server-rendered status page (no template engine needed)."""
from html import escape

from .config import Settings

BADGE = {"pass": "#2e7d32", "warn": "#ed6c02", "block": "#c62828"}


def render_index(settings: Settings, reviews: list) -> str:
    rows = []
    for r in reviews:
        colour = BADGE.get(r["verdict"], "#555")
        rows.append(
            "<tr>"
            f"<td>{escape(r['created_at'])}</td>"
            f"<td>{escape(str(r['repo']))}#{escape(str(r['pr_number'] or '-'))}</td>"
            f"<td><span style='background:{colour};color:#fff;padding:2px 8px;border-radius:10px'>"
            f"{escape(r['verdict'])}</span></td>"
            f"<td>{len(r['comments'])}</td>"
            f"<td>{escape(r['summary'])}</td>"
            f"<td>{escape(r['prompt_version'])}</td>"
            "</tr>"
        )
    body = "\n".join(rows) or "<tr><td colspan='6'>No reviews yet. POST a diff to /review.</td></tr>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="10">
<title>ReviewOps</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:2rem;color:#222}}
 table{{border-collapse:collapse;width:100%}}
 th,td{{border-bottom:1px solid #ddd;padding:6px 10px;text-align:left;font-size:14px}}
 .badge{{display:inline-block;background:#1f4e79;color:#fff;padding:3px 10px;border-radius:12px;margin-right:6px;font-size:13px}}
</style></head><body>
<h1>ReviewOps</h1>
<p>
 <span class="badge">version {escape(settings.app_version)}</span>
 <span class="badge">prompt {escape(settings.prompt_version)}</span>
 <span class="badge">backend {escape(settings.llm_backend)}</span>
</p>
<h2>Recent reviews</h2>
<table><tr><th>Time (UTC)</th><th>PR</th><th>Verdict</th><th>Comments</th><th>Summary</th><th>Prompt</th></tr>
{body}
</table></body></html>"""
