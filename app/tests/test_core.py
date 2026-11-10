"""Core logic tests. Pure stdlib, so they run with unittest or pytest."""
import unittest

from reviewops.config import Settings
from reviewops.diffutil import added_lines
from reviewops.llm import FakeLLM
from reviewops.reviewer import decide_verdict, parse_llm_output, run_review
from reviewops.store import ReviewStore
from reviewops.ui import render_index

SETTINGS = Settings("test", "v1", "fake", "http://x", "m", 5)

SECRET_DIFF = """diff --git a/app/db.py b/app/db.py
--- a/app/db.py
+++ b/app/db.py
@@ -1,3 +1,4 @@
 import os
+DB_PASSWORD = "hunter2-prod"
 def connect():
     pass
"""

CLEAN_DIFF = """diff --git a/app/util.py b/app/util.py
--- a/app/util.py
+++ b/app/util.py
@@ -1,2 +1,4 @@
 def add(a, b):
     return a + b
+
+def sub(a, b):
+    return a - b
"""


class DiffTests(unittest.TestCase):
    def test_added_lines_have_file_and_line_numbers(self):
        added = list(added_lines(SECRET_DIFF))
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0].file, "app/db.py")
        self.assertEqual(added[0].line, 2)

    def test_bare_snippet_fallback(self):
        added = list(added_lines("+x = eval(user_input)\n y = 1\n"))
        self.assertEqual(len(added), 1)


class ReviewerTests(unittest.TestCase):
    def test_secret_is_blocked(self):
        result = run_review({"diff": SECRET_DIFF}, FakeLLM(), SETTINGS)
        self.assertEqual(result["verdict"], "block")
        self.assertEqual(result["comments"][0]["rule"], "hardcoded-secret")
        self.assertEqual(result["comments"][0]["line"], 2)

    def test_clean_diff_passes(self):
        result = run_review({"diff": CLEAN_DIFF}, FakeLLM(), SETTINGS)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["comments"], [])

    def test_high_scanner_finding_blocks_even_if_llm_is_silent(self):
        payload = {"diff": CLEAN_DIFF, "findings": [
            {"tool": "trivy", "rule": "CVE-2024-0001", "severity": "high", "message": "vulnerable lib"}]}
        result = run_review(payload, FakeLLM(), SETTINGS)
        self.assertEqual(result["verdict"], "block")
        self.assertEqual(result["comments"][0]["source"], "scanner:trivy")

    def test_duplicates_are_removed(self):
        payload = {"diff": SECRET_DIFF, "findings": [
            {"tool": "semgrep", "rule": "hardcoded-secret", "severity": "high",
             "file": "app/db.py", "line": 2, "message": "dup"}]}
        result = run_review(payload, FakeLLM(), SETTINGS)
        self.assertEqual(len(result["comments"]), 1)

    def test_sql_concat_with_inner_quote_is_flagged(self):
        diff = "@@ -1,1 +1,2 @@\n x = 1\n+cur.execute(\"SELECT * FROM t WHERE n = '\" + name + \"'\")\n"
        result = run_review({"diff": diff}, FakeLLM(), SETTINGS)
        self.assertEqual(result["verdict"], "block")
        self.assertEqual(result["comments"][0]["rule"], "sql-injection")

    def test_parameterized_sql_is_not_flagged(self):
        diff = "@@ -1,1 +1,2 @@\n x = 1\n+cur.execute(\"SELECT * FROM t WHERE n = %s\", (name,))\n"
        self.assertEqual(run_review({"diff": diff}, FakeLLM(), SETTINGS)["verdict"], "pass")

    def test_decide_verdict(self):
        self.assertEqual(decide_verdict([]), "pass")
        self.assertEqual(decide_verdict([{"severity": "low"}]), "warn")
        self.assertEqual(decide_verdict([{"severity": "critical"}]), "block")

    def test_parse_handles_wrapped_and_invalid_json(self):
        summary, comments = parse_llm_output('Sure! {"summary":"ok","comments":[{"severity":"HIGH","message":"m"}]} bye')
        self.assertEqual(summary, "ok")
        self.assertEqual(comments[0]["severity"], "high")
        summary, comments = parse_llm_output("not json at all")
        self.assertEqual(comments, [])
        self.assertIn("not json", summary)


class StoreAndUiTests(unittest.TestCase):
    def test_store_keeps_newest_first_and_caps_size(self):
        store = ReviewStore(max_items=2)
        for i in range(3):
            store.add({"i": i})
        self.assertEqual([r["i"] for r in store.recent()], [2, 1])

    def test_ui_shows_version_and_escapes_html(self):
        result = run_review({"diff": SECRET_DIFF, "repo": "<b>x</b>"}, FakeLLM(), SETTINGS)
        page = render_index(SETTINGS, [result])
        self.assertIn("version test", page)
        self.assertNotIn("<b>x</b>", page)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", page)


if __name__ == "__main__":
    unittest.main()
