#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 安装完成检测的最小回归测试：python tests/test_install_watch.py
import os, sys, json, tempfile, importlib.util, unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import wbcore as C


def load_app():
    spec = importlib.util.spec_from_file_location("wbapp", os.path.join(ROOT, "WBCoexist.pyw"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class InstallWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mktemp(suffix=".json")
        self.old_cfg = C.CONFIG
        C.CONFIG = self.tmp
        self.app = load_app()

    def tearDown(self):
        C.CONFIG = self.old_cfg
        if os.path.isfile(self.tmp):
            os.remove(self.tmp)

    def test_baseline_then_idle(self):
        self.app._watch_installs()          # 建立基线
        self.assertEqual(self.app._watch_installs(), [])

    def test_change_detected(self):
        self.app._watch_installs()
        cfg = json.load(open(self.tmp, encoding="utf-8"))
        cfg["state"]["wb-CN"] = "1"          # 伪造「刚被安装替换」
        json.dump(cfg, open(self.tmp, "w", encoding="utf-8"))
        self.assertIn("wb-CN", self.app._watch_installs())

    def test_empty_state_no_false_positive(self):
        # 首次运行不应把「第一次看到」当成变化
        self.assertEqual(self.app._watch_installs(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
