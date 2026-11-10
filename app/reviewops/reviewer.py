"""Core review logic. Plain dicts in, plain dicts out (no web framework needed)."""
import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .config import Settings
from .llm import LLMClient

SEVERITIES = ("info", "low", "medium", "high", "critical")
BLOCKING = {"high", "critical"}
PROMPT_DIR = Path(__file__).parent / "prompts"


def load_prompt_template(version: str) -> str:
    return (PROMPT_DIR / f"{version}.txt").read_text(encoding="utf-8")


def build_prompt(template: str, diff: str, findings: list) -> str:
    if findings:
        lines = [f"- [{f.get('severity', 'medium')}] {f.get('tool', 'scanner')}:{f.get('rule', '?')} "
                 f"{f.get('file') or ''}:{f.get('line') or ''} {f.get('message', '')}" for f in findings]
        finding_text = "\n".join(lines)
    else:
        finding_text = "(none)"
    return template.replace("{{FINDINGS}}", finding_text).replace("{{DIFF}}", diff)


def parse_llm_output(text: str):
    """Return (summary, comments). Tolerates models that wrap JSON in extra text."""
    data = None
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            try:
                data = json.loads(text[start:end + 1])
            except ValueError:
                data = None
    if not isinstance(data, dict):
        return (str(text).strip()[:500] or "No review produced."), []

    comments = []
    for raw in data.get("comments") or []:
        if not isinstance(raw, dict):
            continue
        severity = str(raw.get("severity", "low")).lower()
        comments.append({
            "file": raw.get("file"),
            "line": raw.get("line") if isinstance(raw.get("line"), int) else None,
            "severity": severity if severity in SEVERITIES else "low",
            "rule": str(raw.get("rule", "llm-comment")),
            "message": str(raw.get("message", "")),
            "source": "llm",
        })
    return str(data.get("summary", "")).strip() or "Review complete.", comments


def decide_verdict(comments: list) -> str:
    """Policy lives in code, not in the model: the LLM cannot approve a blocker."""
    severities = {c["severity"] for c in comments}
    if severities & BLOCKING:
        return "block"
    return "warn" if comments else "pass"


def _scanner_comments(findings: list) -> list:
    return [{
        "file": f.get("file"), "line": f.get("line"),
        "severity": f.get("severity", "medium"),
        "rule": f.get("rule", "scanner-finding"),
        "message": f.get("message", ""),
        "source": f"scanner:{f.get('tool', 'scanner')}",
    } for f in findings]


def run_review(payload: dict, llm: LLMClient, settings: Settings) -> dict:
    started = time.perf_counter()
    diff = payload.get("diff", "")
    findings = payload.get("findings") or []

    prompt = build_prompt(load_prompt_template(settings.prompt_version), diff, findings)
    summary, llm_comments = parse_llm_output(llm.complete(prompt, diff))

    comments, seen = [], set()
    for c in _scanner_comments(findings) + llm_comments:  # scanner facts first
        key = (c["file"], c["line"], c["rule"])
        if key not in seen:
            seen.add(key)
            comments.append(c)

    return {
        "review_id": uuid.uuid4().hex[:12],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repo": payload.get("repo", "unknown/repo"),
        "pr_number": payload.get("pr_number"),
        "verdict": decide_verdict(comments),
        "summary": summary,
        "comments": comments,
        "model": llm.name,
        "prompt_version": settings.prompt_version,
        "app_version": settings.app_version,
        "latency_ms": int((time.perf_counter() - started) * 1000),
    }
