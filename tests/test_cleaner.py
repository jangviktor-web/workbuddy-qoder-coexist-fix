# -*- coding: utf-8 -*-
import os, sys, json, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import cleaner as CL
import wbcore as C


class CleanerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _file(self, rel, n):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb") as fh:
            fh.write(b"x" * n)
        return p

    def test_targets_only_existing_nonempty(self):
        self._file(os.path.join("logs", "a.log"), 1024)
        self._file(os.path.join("cache", "b.bin"), 2048)
        os.makedirs(os.path.join(self.root, "app", "cache"))
        got = {t["label"]: t for t in CL.targets("P", self.root, CL.WB_SPEC, False)}
        self.assertEqual(sorted(got), ["产品缓存", "运行日志"])
        self.assertEqual(got["运行日志"]["size"], 1024)
        self.assertEqual(got["产品缓存"]["size"], 2048)
        self.assertIn("日志", got["运行日志"]["note"])

    def test_every_spec_has_note(self):
        for spec in (CL.WB_SPEC, CL.WB_LOCAL, CL.QODER_SPEC, CL.QODER_PART):
            for label, rel, note in spec:
                self.assertTrue(note.strip(), label)
                self.assertTrue(isinstance(rel, tuple) and rel, label)

    def test_purge_keeps_dir_and_reports_freed(self):
        self._file(os.path.join("logs", "a.log"), 1000)
        self._file(os.path.join("logs", "sub", "b.log"), 500)
        p = os.path.join(self.root, "logs")
        freed, errs = CL.purge(p)
        self.assertEqual((freed, errs), (1500, []))
        self.assertTrue(os.path.isdir(p))
        self.assertEqual(os.listdir(p), [])
        self.assertEqual(CL.purge(p), (0, []))

    def test_clean_skips_running(self):
        a = self._file(os.path.join("logs", "a.log"), 100)
        b = self._file(os.path.join("cache", "b.bin"), 200)
        items = [
            {"group": "G", "label": "运行日志", "path": os.path.dirname(a), "size": 100, "running": True},
            {"group": "G", "label": "产品缓存", "path": os.path.dirname(b), "size": 200, "running": False},
        ]
        r = CL.clean(items)
        self.assertEqual(r["freed"], 200)
        self.assertEqual([x["label"] for x in r["skipped"]], ["运行日志"])
        self.assertTrue(os.path.isfile(a))
        self.assertFalse(os.path.isfile(b))

    def test_qoder_data_dir_from_product_json(self):
        exe_dir = os.path.join(self.root, "app")
        os.makedirs(os.path.join(exe_dir, "resources"))
        with open(os.path.join(exe_dir, "resources", "product.json"), "w", encoding="utf-8") as fh:
            json.dump({"dataDirectoryName": "com.test.qoder"}, fh)
        exe = os.path.join(exe_dir, "Qoder.exe")
        open(exe, "wb").close()
        roaming = os.path.join(self.root, "roaming")
        os.makedirs(os.path.join(roaming, "com.test.qoder", "Cache"))
        with open(os.path.join(roaming, "com.test.qoder", "Cache", "c"), "wb") as fh:
            fh.write(b"x" * 4096)
        old = C.APPDATA
        C.APPDATA = roaming
        try:
            items = CL._qoder_targets({"intl": {"exe": exe, "name": "Qoder X",
                                               "running": []}, "cn": {}})
        finally:
            C.APPDATA = old
        self.assertEqual(len(items), 1)
        self.assertEqual((items[0]["group"], items[0]["label"]), ("Qoder X", "浏览器缓存"))
        self.assertEqual(items[0]["size"], 4096)

    def test_fmt(self):
        self.assertEqual(CL.fmt(1048576), "1.0 MB")
        self.assertEqual(CL.fmt(1073741824), "1.0 GB")


if __name__ == "__main__":
    unittest.main(verbosity=2)
