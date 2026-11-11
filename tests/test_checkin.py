#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 签到模块的最小回归测试：python tests/test_checkin.py
# 只测纯逻辑，不发真实网络请求
import os, sys, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import checkin as K


class CheckinLogic(unittest.TestCase):
    def test_from_config_empty(self):
        self.assertEqual(K.from_config({}), ("", "", ""))

    def test_from_config_full(self):
        cfg = {"checkin": {"token": " t ", "uid": "u1", "enterprise_id": "e1"}}
        self.assertEqual(K.from_config(cfg), ("t", "u1", "e1"))

    def test_from_config_missing_section(self):
        self.assertEqual(K.from_config({"primary": "CN"}), ("", "", ""))

    def test_pick_prefers_first(self):
        self.assertEqual(K._pick({"a": 1, "b": 2}, "b", "a"), 2)
        self.assertEqual(K._pick({"a": 1}, "b", "a"), 1)
        self.assertIsNone(K._pick({}, "x"))

    def test_describe_failure(self):
        self.assertTrue(K.describe({"ok": False, "error": "401"}).startswith("查询失败"))

    def test_describe_not_checked(self):
        s = K.describe({"ok": True, "today": False, "streak_days": 3,
                        "daily_credit": 10, "total_credits": 120})
        self.assertIn("未签到", s)
        self.assertIn("连续 3 天", s)
        self.assertIn("累计 120", s)

    def test_describe_checked(self):
        s = K.describe({"ok": True, "today": True})
        self.assertIn("已签到", s)

    def test_endpoint_shape(self):
        # 端点常量与上游一致（checkin.rs / config.rs）
        self.assertEqual(K.CN_BASE, "https://www.codebuddy.cn")
        self.assertEqual(K.API, "/v2/billing/meter")


if __name__ == "__main__":
    unittest.main(verbosity=2)
