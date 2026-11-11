#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 迁移模块的最小回归测试：python tests/test_migrate.py
# 不依赖本机是否装了软件，也不做任何实际迁移
import os, sys, tempfile, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import migrate as M


class MigratePlan(unittest.TestCase):
    def test_norm_root_drive_only(self):
        self.assertEqual(M._norm_root("E:"), "E:" + os.sep)

    def test_norm_root_with_path(self):
        self.assertEqual(M._norm_root("E:/Data/"), "E:/Data")

    def test_norm_root_empty(self):
        self.assertEqual(M._norm_root(""), "")

    def test_is_link_false_for_plain_dir(self):
        d = tempfile.mkdtemp()
        try:
            self.assertFalse(M._is_link(d))
            self.assertEqual(M._link_target(d), "")
        finally:
            os.rmdir(d)

    def test_scan_shape(self):
        r = M.scan()
        self.assertIn("items", r)
        self.assertIn("projects", r)
        self.assertIsInstance(r["items"], list)
        self.assertIsInstance(r["projects"], list)
        for it in r["items"]:
            for k in ("key", "kind", "product", "path", "evidence", "migrated"):
                self.assertIn(k, it)
            self.assertIn(it["kind"], ("app", "data", "sessions"))

    def test_plan_excludes_sessions(self):
        r = M.scan()
        keys = [it["key"] for it in r["items"]]
        for p in M.plan(keys, "E:"):
            self.assertIn(p["kind"], ("app", "data"))

    def test_plan_target_under_root(self):
        r = M.scan()
        keys = [it["key"] for it in r["items"]]
        for p in M.plan(keys, "E:/Migrate"):
            self.assertTrue(p["dst"].startswith("E:/Migrate" + os.sep + "Migrations"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
