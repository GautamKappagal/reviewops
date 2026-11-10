"""Request validation for the HTTP API (the only place pydantic is used)."""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["info", "low", "medium", "high", "critical"]


class Finding(BaseModel):
    tool: str = "scanner"
    rule: str
    severity: Severity = "medium"
    message: str = ""
    file: Optional[str] = None
    line: Optional[int] = None


class ReviewRequest(BaseModel):
    repo: str = "unknown/repo"
    pr_number: Optional[int] = None
    diff: str = Field(min_length=1)
    findings: List[Finding] = Field(default_factory=list)
