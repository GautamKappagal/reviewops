"""LLM backends. Both return a JSON string: {"summary": str, "comments": [..]}."""
import json
import re
import urllib.request
from typing import Protocol

from .config import Settings
from .diffutil import added_lines

# (rule id, severity, pattern, advice) applied to each ADDED line.
RULES = [
    ("hardcoded-secret", "high",
     re.compile(r"""(?i)(password|passwd|secret|api[_-]?key|token)\s*=\s*['"][^'"]{4,}['"]"""),
     "Possible hard-coded credential. Load it from Vault or an environment variable instead."),
    ("dangerous-eval", "high",
     re.compile(r"\b(eval|exec)\s*\("),
     "eval/exec on dynamic input allows code injection. Use a safe parser instead."),
    ("shell-injection", "high",
     re.compile(r"subprocess\.\w+\(.*shell\s*=\s*True|os\.system\("),
     "Running shell commands built from strings risks command injection. Pass an argument list instead."),
    ("sql-injection", "high",
     re.compile(r"""(?i)(["'])\s*(select|insert|update|delete)\b.*?\1\s*\+|\bf["']\s*(select|insert|update|delete)\b[^"']*\{"""),
     "SQL assembled from strings is injectable. Use parameterized queries."),
    ("tls-verify-disabled", "medium",
     re.compile(r"verify\s*=\s*False"),
     "Disabling TLS certificate verification exposes the connection to interception."),
    ("weak-hash", "medium",
     re.compile(r"hashlib\.(md5|sha1)\("),
     "MD5/SHA-1 are weak for security purposes. Use SHA-256 or a password hash such as bcrypt/argon2."),
]


class LLMClient(Protocol):
    name: str

    def complete(self, prompt: str, diff: str) -> str: ...


class FakeLLM:
    """Deterministic rule-based stand-in. Used for CI, tests and the benchmark."""

    name = "fake-llm"

    def complete(self, prompt: str, diff: str) -> str:
        comments = []
        for added in added_lines(diff):
            for rule, severity, pattern, advice in RULES:
                if pattern.search(added.text):
                    comments.append({
                        "file": added.file, "line": added.line, "severity": severity,
                        "rule": rule, "message": advice, "source": "llm",
                    })
        if comments:
            summary = f"Found {len(comments)} potential issue(s) in the changed lines."
        else:
            summary = "No issues found in the changed lines."
        return json.dumps({"summary": summary, "comments": comments})


class OllamaLLM:
    """Talks to a local Ollama server (https://ollama.com)."""

    def __init__(self, url: str, model: str, timeout: int = 120):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def complete(self, prompt: str, diff: str) -> str:
        payload = json.dumps({
            "model": self.model, "prompt": prompt, "stream": False,
            "format": "json", "options": {"temperature": 0},
        }).encode()
        req = urllib.request.Request(
            f"{self.url}/api/generate", data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())["response"]


def get_llm(settings: Settings) -> LLMClient:
    if settings.llm_backend == "ollama":
        return OllamaLLM(settings.ollama_url, settings.ollama_model)
    return FakeLLM()
