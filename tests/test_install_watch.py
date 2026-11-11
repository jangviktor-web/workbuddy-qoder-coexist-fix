#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 安装完成检测的最小回归测试：python tests/test_install_watch.py
# 只测纯逻辑，不依赖本机是否装了 WorkBuddy / Qoder
import os, sys, importlib.util, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def load_app():
    spec = importlib.util.spec_from_file_location("wbapp", os.path.join(ROOT, "WBCoexist.pyw"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class InstallWatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = load_app()

    def test_first_sight_is_not_change(self):
        # 冷启动首次看到不算「刚安装」
        self.assertEqual(self.app._diff_state({}, {"wb-CN": "123"}), [])

    def test_same_is_not_change(self):
        self.assertEqual(self.app._diff_state({"wb-CN": "1"}, {"wb-CN": "1"}), [])

    def test_changed_detected(self):
        self.assertEqual(self.app._diff_state({"wb-CN": "1"}, {"wb-CN": "2"}), ["wb-CN"])

    def test_removed_not_reported(self):
        # 旧有新无（卸载）不该被当成安装完成
        self.assertEqual(self.app._diff_state({"wb-CN": "1"}, {}), [])

    def test_multi_keys(self):
        old = {"wb-CN": "1", "q-intl": "5"}
        cur = {"wb-CN": "9", "q-intl": "5", "q-cn": "7"}
        self.assertEqual(self.app._diff_state(old, cur), ["wb-CN"])

    def test_watch_does_not_raise(self):
        # 无安装环境下也不能抛异常
        self.app._watch_installs()


if __name__ == "__main__":
    unittest.main(verbosity=2)
