#!/usr/bin/env python3
"""Audit tests - these guard the two mistakes this tool exists to catch."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from md2audio import audit

CLEAN = """@@P0|开场
这项研究发表于二零一五年，样本量十六人，餐后血糖峰值下降约百分之二十五。
"""

DIRTY = """@@P0|开场
这项研究发表于二零二五年，样本量十六人。
这里的占位符是 откр 和 valuable，还有一个 all in 没翻完。
"""


class AuditTest(unittest.TestCase):
    def test_spelled_years_are_listed(self):
        self.assertIn("二零一五年", audit.spelled_years(CLEAN))

    def test_cyrillic_and_english_runs_flagged(self):
        runs = audit.latin_runs(DIRTY)
        self.assertIn("откр", runs)
        self.assertIn("valuable", runs)

    def test_whitelisted_terms_are_not_flagged(self):
        self.assertFalse(audit.latin_runs("每周测一次 AI 模型的 MP3 输出。"))

    def test_cyrillic_characters_are_surfaced(self):
        self.assertIn("о", audit.non_cjk_characters("这里有一个 откр 残留"))

    def test_ordinary_chinese_punctuation_is_not_flagged(self):
        self.assertEqual(audit.non_cjk_characters(CLEAN), set())

    def test_numbers_absent_from_source_are_surfaced(self):
        script_text = "这项研究发表于 2026 年，样本量 16 人。"
        source_text = "样本量 16 人，发表于 2015 年。"
        diff = audit.diff_against_source(script_text, source_text)
        # 文稿里凭空出现的年份必须被列出来，由人确认它是推算还是写错了
        self.assertEqual(diff["unmatched_numbers"], ["2026"])

    def test_chinese_years_are_counted(self):
        self.assertEqual(audit.spelled_years(CLEAN)["二零一五年"], 1)

    def test_audit_reports_problems_on_dirty_script(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(DIRTY)
            report = audit.audit(path)
            self.assertEqual(report["chapters"], 1)
            self.assertTrue(report["problems"])

    def test_clean_script_has_no_flagged_tokens(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "s.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(CLEAN)
            report = audit.audit(path)
            self.assertEqual(report["latin_runs"], {})
            self.assertEqual(report["non_cjk_characters"], [])


if __name__ == "__main__":
    unittest.main()
