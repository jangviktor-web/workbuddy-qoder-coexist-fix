#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""破甲注入能力桥接层（WBCoexist 基础层，不依赖其它本地模块）。

把破甲的 pojia_core.py 当模块加载，进程内调用其 main(argv)，把输出捕获成字符串。
这样 WBCoexist 用一套 GUI / 一个 exe 就能操作破甲支持的全部目标。

约束：
  - pojia_core.py 随包放在 _internal/pojia/ 下；开发环境在 WBCoexist 目录下 pojia/。
  - 破甲的 STATE_DIR 由 __file__ 推导（非 frozen），因此状态落在贴着 core 的 state/，
    与破甲独立 exe 的 D:\Apps\pojia-modifier\state 不共用——这是刻意的隔离，
    避免两个程序互相覆盖护照/备份/清单。
  - 每次调用临时替换 sys.stdout/stderr 捕获输出，调用后无条件恢复。
"""
import os
import io
import sys
import contextlib

_mod = None
_mod_error = ""


def core_path():
    """pojia_core.py 的绝对路径；找不到返回空串。"""
    me = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
    here = os.path.dirname(me)
    candidates = [
        os.path.join(here, "pojia", "pojia_core.py"),
        os.path.join(getattr(sys, "_MEIPASS", here), "pojia", "pojia_core.py"),
        os.path.join(here, "_internal", "pojia", "pojia_core.py"),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return p
    return ""


def load():
    """加载破甲核心模块，返回 (module, error)。只加载一次。"""
    global _mod, _mod_error
    if _mod is not None:
        return _mod, ""
    if _mod_error:
        return None, _mod_error
    path = core_path()
    if not path:
        _mod_error = "找不到 pojia_core.py（应随程序放在 pojia/ 目录下）"
        return None, _mod_error
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("pojia_core_embedded", path)
        m = importlib.util.module_from_spec(spec)
        m.__file__ = path
        spec.loader.exec_module(m)
        _mod = m
        return m, ""
    except Exception as e:
        _mod_error = "%s: %s" % (type(e).__name__, e)
        return None, _mod_error


def _call(argv):
    """调用破甲 main(argv)，捕获 stdout+stderr，返回 (code, text)。"""
    m, err = load()
    if m is None:
        return 1, "破甲核心加载失败：" + err
    buf = io.StringIO()
    real_out, real_err = sys.stdout, sys.stderr
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                code = m.main(list(argv))
            except SystemExit as e:
                code = int(e.code or 0)
            except Exception as e:
                buf.write("[error] %s: %s\n" % (type(e).__name__, e))
                code = 1
    finally:
        sys.stdout, sys.stderr = real_out, real_err
    return int(code or 0), buf.getvalue()


def status_json(targets=None):
    """返回破甲各目标的结构化状态列表。targets=None 表示全部。"""
    argv = ["--status-json", "--no-update-check"]
    if targets:
        argv += ["--target", ",".join(targets)]
    code, text = _call(argv)
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#status "):
            try:
                import json
                rows = json.loads(line[len("#status "):])
            except Exception:
                pass
            break
    return code, rows, text


def apply(targets=None, yes=True):
    argv = ["--apply", "--yes", "--no-update-check"]
    if targets:
        argv += ["--target", ",".join(targets)]
    return _call(argv)


def revert(targets=None, yes=True):
    argv = ["--revert", "--yes", "--no-update-check"]
    if targets:
        argv += ["--target", ",".join(targets)]
    return _call(argv)


def diagnose(targets=None):
    argv = ["--diagnose", "--no-update-check"]
    if targets:
        argv += ["--target", ",".join(targets)]
    return _call(argv)


def version():
    m, err = load()
    if m is None:
        return "未加载：" + err
    return getattr(m, "DISPLAY_VERSION", "?")