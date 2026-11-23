#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WorkBuddy 系统提示词破甲引擎桥接层（WBCoexist 基础层，不依赖其它本地模块）。

把上游 WorkBuddy-Prompt-Patcher 的 batch_patch_prompts.py 当模块加载，进程内调用
其 main()（通过临时替换 sys.argv + 捕获 stdout/stderr），把结果交给 GUI / CLI。
与 pojia_bridge.py 同一套模式，状态与独立破甲、独立 patcher 均互相隔离。

引擎与 custom_input.txt 必须同目录随包分发：
  - 开发环境: <WBCoexist 目录>/promptpatcher/
  - onefile  : _MEIPASS/promptpatcher/
  - onedir   : _internal/promptpatcher/
"""
import os
import io
import sys
import contextlib

_mod = None
_mod_error = ""


def engine_dir():
    """引擎数据目录（含 batch_patch_prompts.py 与 custom_input.txt）。"""
    me = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
    here = os.path.dirname(me)
    candidates = [
        os.path.join(here, "promptpatcher"),
        os.path.join(getattr(sys, "_MEIPASS", here), "promptpatcher"),
        os.path.join(here, "_internal", "promptpatcher"),
    ]
    for p in candidates:
        if os.path.isfile(os.path.join(p, "batch_patch_prompts.py")):
            return p
    return candidates[0]


def core_path():
    p = os.path.join(engine_dir(), "batch_patch_prompts.py")
    return p if os.path.isfile(p) else ""


def buffer_path():
    return os.path.join(engine_dir(), "custom_input.txt")


def load():
    """加载引擎模块，返回 (module, error)。只加载一次。"""
    global _mod, _mod_error
    if _mod is not None:
        return _mod, ""
    if _mod_error:
        return None, _mod_error
    path = core_path()
    if not path:
        _mod_error = "找不到 batch_patch_prompts.py（应随程序放在 promptpatcher/ 目录下）"
        return None, _mod_error
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("wpp_engine_embedded", path)
        m = importlib.util.module_from_spec(spec)
        m.__file__ = path
        spec.loader.exec_module(m)
        _mod = m
        return m, ""
    except Exception as e:
        _mod_error = "%s: %s" % (type(e).__name__, e)
        return None, _mod_error


def _reset_globals(m):
    """引擎是单实例模块，重复调用前清空易累积的全局流水。"""
    for name, val in (("WRITE_ERRORS", []), ("V35_RAILS", []),
                      ("DRY_RUN", False), ("VERBOSE_OUTPUT", False)):
        if hasattr(m, name):
            setattr(m, name, val)


def _call_argv(argv):
    """以 argc 方式调用引擎 main()，捕获 stdout+stderr，返回 (code, text)。"""
    m, err = load()
    if m is None:
        return 1, "提示词破甲引擎加载失败：" + err
    _reset_globals(m)
    buf = io.StringIO()
    old_argv = sys.argv
    real_out, real_err = sys.stdout, sys.stderr
    try:
        sys.argv = [os.path.join(engine_dir(), "batch_patch_prompts.py")] + list(argv)
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            try:
                code = m.main()
            except SystemExit as e:
                code = e.code
                if code is None:
                    code = 0
                if not isinstance(code, int):
                    code = 0 if code in (None, False, "", 0) else 1
            except Exception as e:
                buf.write("[error] %s: %s\n" % (type(e).__name__, e))
                code = 1
    finally:
        sys.argv = old_argv
        sys.stdout, sys.stderr = real_out, real_err
    return int(code or 0), buf.getvalue()


def _call_fn(fn, *a, **kw):
    """进程内直接调用引擎函数，捕获输出，返回 (result, text)。"""
    m, err = load()
    if m is None:
        return None, "提示词破甲引擎加载失败：" + err
    _reset_globals(m)
    buf = io.StringIO()
    real_out, real_err = sys.stdout, sys.stderr
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            result = fn(*a, **kw)
    except Exception as e:
        buf.write("[error] %s: %s\n" % (type(e).__name__, e))
        result = None
    finally:
        sys.stdout, sys.stderr = real_out, real_err
    return result, buf.getvalue()


def _ensure_targets():
    """确保目标缓存已就绪；后续引擎调用点复用它，避免每次全盘探测。"""
    if _cached_targets is None:
        targets()


def version():
    m, err = load()
    if m is None:
        return "未加载：" + err
    return getattr(m, "PATCHER_VERSION", "?")


_cached_targets = None


def targets(refresh=False):
    """返回 (code, rows, text)。rows=[{key,label,path}]。

    首次检测较慢（引擎要枚举注册表/快捷方式/多盘符），结果缓存于进程内；
    同时把引擎模块的 find_all_templates_dirs 替换为返回同一份缓存，
    使后续 apply/verify/scan/restore 直接复用，不再重复慢探测。"""
    global _cached_targets
    m, err = load()
    if m is None:
        return 1, [], "提示词破甲引擎加载失败：" + err
    if _cached_targets is None or refresh:
        # 快速路径：优先用引擎持久化的已验证目录（毫秒级），避免每次都跑全盘探测
        found = []
        if not refresh:
            try:
                found = [d for d in (m.load_saved_templates_dirs() or [])
                         if m.is_valid_templates_dir(d)]
            except Exception:
                found = []
        if not found:
            found, text = _call_fn(m.find_all_templates_dirs)
        else:
            text = ""
        _cached_targets = list(found or [])
        # 让引擎内部所有调用点复用缓存
        m.find_all_templates_dirs = lambda: list(_cached_targets)
    else:
        text = ""
    found = _cached_targets
    rows = []
    for d in (found or []):
        rows.append({"key": d, "label": m.get_installation_label(d), "path": d})
    return 0, rows, text


def apply(templates_only=False, dry_run=False, require_closed=False):
    _ensure_targets()
    argv = ["--templates-only"] if templates_only else ["--auto"]
    if dry_run:
        argv.append("--dry-run")
    if require_closed:
        argv.append("--require-closed")
    return _call_argv(argv)


def verify(verbose=False):
    _ensure_targets()
    argv = ["--verify"]
    if verbose:
        argv.append("--verbose")
    return _call_argv(argv)


def scan():
    _ensure_targets()
    return _call_argv(["--scan"])


def restore(templates_only=False):
    _ensure_targets()
    return _call_argv(["--restore-templates"] if templates_only else ["--restore"])


def get_buffer():
    """返回 (ok, text)。"""
    p = buffer_path()
    try:
        if not os.path.isfile(p):
            return False, ""
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            return True, f.read()
    except Exception as e:
        return False, str(e)


def set_buffer(text):
    """原子写入 custom_input.txt，返回 (ok, msg)。"""
    p = buffer_path()
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        tmp = p + ".zwork-tmp"
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            f.write(text if text.endswith("\n") or text == "" else text + "\n")
        os.replace(tmp, p)
        # 引擎已加载时同步其内存中的缓冲常量（下次 main 会重新读盘，这里仅保持一致）
        m, _ = load()
        if m is not None:
            m.BUFFER_FILE_PATH = p
        return True, p
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)
