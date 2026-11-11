#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 从 CHANGELOG.md 提取指定版本段落，写入 release notes 文件。
# 用法：python tools/extract_changelog.py CHANGELOG.md v1.1.0 release-notes.md
import sys, re

def norm(v):
    return v.strip().lstrip("vV").strip("[]").strip()

def main():
    if len(sys.argv) < 4:
        print("usage: extract_changelog.py <CHANGELOG.md> <tag> <out.md>")
        return 2
    path, tag, out = sys.argv[1], sys.argv[2], sys.argv[3]
    ver = norm(tag)
    body = None
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        text = ""
    for part in re.split(r"(?m)^##\s+", text)[1:]:
        lines = part.splitlines()
        if not lines:
            continue
        head = norm(lines[0].split("-")[0].split("(")[0])
        if head == ver:
            body = "\n".join(lines[1:]).strip()
            break
    if not body:
        body = "版本 " + ver + " 的变更请见仓库根目录的 CHANGELOG.md。"
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body + "\n")
    print("WROTE " + out + " (" + str(len(body)) + " chars)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
