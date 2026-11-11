#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CI 构建产物静态校验：版本资源 / manifest / 未压缩 / 文件大小。
# 不依赖本机 WorkBuddy、Qoder 或任何绝对路径，可在 GitHub runner 上运行。
import os, sys, hashlib
import pefile

root = sys.argv[1] if len(sys.argv) > 1 else "dist"
exes = []
for base, dirs, files in os.walk(root):
    for f in files:
        if f.lower().endswith(".exe"):
            exes.append(os.path.join(base, f))

if not exes:
    print("FAIL: no exe found under " + root)
    sys.exit(1)

zips = [os.path.join(root, f) for f in os.listdir(root)
        if f.lower().endswith(".zip")]
if not zips:
    print("FAIL: portable zip missing")
    sys.exit(1)

ok = True
for p in sorted(exes):
    b = open(p, "rb").read()
    pe = pefile.PE(p)
    secs = [s.Name.rstrip(b"\x00").decode(errors="ignore") for s in pe.sections]
    upx = any("UPX" in s.upper() for s in secs)
    vs = {}
    for fi in getattr(pe, "FileInfo", []) or []:
        for f in fi:
            if f.Key == b"StringFileInfo":
                for st in f.StringTable:
                    for k, val in st.entries.items():
                        vs[k.decode(errors="ignore")] = val.decode(errors="ignore")
    need = ("ProductName", "ProductVersion", "CompanyName", "FileDescription")
    missing = [k for k in need if not vs.get(k)]
    man = all(x in b for x in (b"asInvoker", b"dpiAware", b"longPathAware"))
    good = (not upx) and (not missing) and man and len(b) > 500000
    ok = ok and good
    print(("PASS " if good else "FAIL ") + p)
    print("     size=%d  sha256=%s" % (len(b), hashlib.sha256(b).hexdigest()))
    print("     ProductVersion=%s  UPX=%s  manifest=%s  missing=%s" %
          (vs.get("ProductVersion"), upx, man, missing))

for z in zips:
    print("ASSET zip: %s (%d bytes)" % (z, os.path.getsize(z)))

print("RESULT:", "OK" if ok else "FAILED")
sys.exit(0 if ok else 1)
