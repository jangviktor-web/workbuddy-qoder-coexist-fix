#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# _pick_target 的最小回归测试：python tests/test_pick_target.py
import os, sys, unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import qoder as Q


def node(name, version, h, running=False):
    return {"name": name, "version": version, "hash": h,
            "running": [1] if running else []}


class PickTarget(unittest.TestCase):
    def test_intl_newer(self):
        a = node("Qoder 国际版", "0.5.7", "a" * 64)
        b = node("Qoder 中国版", "0.5.2", "b" * 64)
        self.assertEqual(Q._pick_target([a, b])["name"], "Qoder 国际版")

    def test_cn_newer(self):
        # 中国版反超：不能再假设国际版更新
        a = node("Qoder 国际版", "0.5.7", "a" * 64)
        b = node("Qoder 中国版", "0.6.0", "b" * 64)
        self.assertEqual(Q._pick_target([a, b])["name"], "Qoder 中国版")

    def test_tie_deterministic(self):
        # 版本并列时不按国别，按哈希序，且与传入顺序无关
        a = node("Qoder 国际版", "0.5.7", "z" * 64)
        b = node("Qoder 中国版", "0.5.7", "a" * 64)
        self.assertEqual(Q._pick_target([a, b])["hash"], "a" * 64)
        self.assertEqual(Q._pick_target([b, a])["hash"], "a" * 64)

    def test_manifest_wins_on_tie(self):
        a = node("Qoder 国际版", "0.5.7", "z" * 64)
        b = node("Qoder 中国版", "0.5.7", "a" * 64)
        self.assertEqual(Q._pick_target([a, b], "z" * 64)["name"], "Qoder 国际版")

    def test_missing_version_loses(self):
        a = node("Qoder 国际版", None, "a" * 64)
        b = node("Qoder 中国版", "0.5.2", "b" * 64)
        self.assertEqual(Q._pick_target([a, b])["name"], "Qoder 中国版")

    def test_running_wins_on_tie(self):
        a = node("Qoder 国际版", "0.5.7", "z" * 64)
        b = node("Qoder 中国版", "0.5.7", "a" * 64, running=True)
        # 哈希序会让 a 胜出，但 b 正在运行 -> 应选 b？ 规则顺序：哈希存在 > 运行 > 哈希序
        # 两者 host 目录都不存在，故走到「正在运行」这一档
        self.assertEqual(Q._pick_target([a, b])["name"], "Qoder 中国版")

    def test_empty(self):
        self.assertIsNone(Q._pick_target([]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
