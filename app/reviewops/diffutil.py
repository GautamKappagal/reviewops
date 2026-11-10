"""Tiny unified-diff parser that yields only the lines a diff adds."""
import re
from typing import Iterator, NamedTuple, Optional

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@")


class AddedLine(NamedTuple):
    file: Optional[str]
    line: int
    text: str


def added_lines(diff: str) -> Iterator[AddedLine]:
    lines = diff.splitlines()

    # Fallback: a bare snippet with no hunk headers. Treat '+' lines as added.
    if not any(HUNK_RE.match(x) for x in lines):
        for idx, raw in enumerate(lines, start=1):
            if raw.startswith("+") and not raw.startswith("+++ "):
                yield AddedLine(None, idx, raw[1:])
        return

    current_file: Optional[str] = None
    new_line = 0
    in_hunk = False
    for raw in lines:
        if raw.startswith("diff --git"):
            in_hunk = False
            continue
        match = HUNK_RE.match(raw)
        if match:
            new_line = int(match.group(1))
            in_hunk = True
            continue
        if not in_hunk:
            if raw.startswith("+++ "):
                path = raw[4:].strip()
                if path.startswith("b/"):
                    path = path[2:]
                current_file = None if path == "/dev/null" else path
            continue
        if raw.startswith("+"):
            yield AddedLine(current_file, new_line, raw[1:])
            new_line += 1
        elif raw.startswith("-") or raw.startswith("\\"):
            continue
        else:  # context line
            new_line += 1
