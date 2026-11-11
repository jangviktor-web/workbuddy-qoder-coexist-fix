#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 已安装检测的最小回归测试：python tests/test_installed.py
# 不依赖是否真的装了 WorkBuddy / Qoder
import os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import wbcore as C
import qoder as Q


class Installed(unittest.TestCase):
    def test_wb_returns_list(self):
        got = C.installed()
        self.assertIsInstance(got, list)

    def test_wb_no_duplicate_exe(self):
        keys = [C._pkey(it["exe"]) for it in C.installed()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_wb_item_shape(self):
        for it in C.installed():
            for k in ("tag", "name", "version", "exe", "running", "source"):
                self.assertIn(k, it)
            self.assertIn(it["tag"], ("CN", "AI"))

    def test_qoder_returns_list(self):
        got = Q.installed()
        self.assertIsInstance(got, list)

    def test_qoder_no_duplicate_exe(self):
        norm = lambda p: os.path.normcase(os.path.normpath(p))
        keys = [norm(it["exe"]) for it in Q.installed()]
        self.assertEqual(len(keys), len(set(keys)))

    def test_pkey_normalizes_separators(self):
        a = C._pkey("D:/WorkBuddy/WorkBuddy.exe")
        b = C._pkey("D:\WorkBuddy\WorkBuddy.exe")
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main(verbosity=2)
