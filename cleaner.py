#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 缓存/日志清理：只清白名单目录里的内容，保留目录本身；不碰配置、会话、数据库。
# 路径全部实测：WorkBuddy 数据目录按版本映射再用 migrate 的发现结果补充，
# Qoder 数据目录名取自安装目录 product.json 的 dataDirectoryName。
import os, shutil
import wbcore as C
import qoder as Q
import migrate as M

WB_SPEC = [("运行日志", ("logs",), "应用运行与沙箱日志，排查问题才需要，删除后自动重建"),
           ("产品缓存", ("cache",), "接口与资源缓存，删除后联网重新拉取"),
           ("渲染缓存", ("app", "cache"), "界面渲染缓存，删除后首次启动稍慢")]
WB_LOCAL = [("Electron 日志", ("logs",), "Electron 框架日志，仅用于排查启动问题")]

QODER_SPEC = [("浏览器缓存", ("Cache",), "内嵌浏览器的网页缓存，删除后首次打开页面稍慢"),
              ("代码缓存", ("Code Cache",), "网页脚本编译缓存，删除后自动重建"),
              ("GPU 缓存", ("GPUCache",), "显卡着色器缓存，删除后自动重建"),
              ("Dawn 缓存", ("DawnGraphiteCache",), "WebGPU 中间层缓存，删除后自动重建"),
              ("Dawn WebGPU 缓存", ("DawnWebGPUCache",), "WebGPU 着色器缓存，删除后自动重建"),
              ("崩溃转储", ("Crashpad",), "崩溃时的内存转储，提交问题反馈前请先保留"),
              ("运行日志", ("logs",), "主进程与扩展日志，排查问题才需要")]
# 浏览器分区里只清缓存类，Local Storage / IndexedDB / Network 是登录态，不动
QODER_PART = [("浏览器缓存", ("Cache",), "内嵌浏览器的网页缓存，删除后首次打开页面稍慢"),
              ("代码缓存", ("Code Cache",), "网页脚本编译缓存，删除后自动重建"),
              ("GPU 缓存", ("GPUCache",), "显卡着色器缓存，删除后自动重建"),
              ("Dawn 缓存", ("DawnGraphiteCache",), "WebGPU 中间层缓存，删除后自动重建"),
              ("Dawn WebGPU 缓存", ("DawnWebGPUCache",), "WebGPU 着色器缓存，删除后自动重建")]
QODER_FALLBACK = {"intl": "com.qoder.app.stable", "cn": "com.qodercn.app.stable"}


def dir_size(p):
    total = 0
    for root, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if not C.islink(os.path.join(root, d))]
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def fmt(n):
    return "%.1f GB" % (n / 1073741824.0) if n >= 1073741824 else "%.1f MB" % (n / 1048576.0)


def targets(group, root, spec, running):
    out = []
    for label, rel, note in spec:
        p = os.path.join(root, *rel)
        if os.path.isdir(p) and not C.islink(p):
            n = dir_size(p)
            if n > 0:
                out.append({"group": group, "label": label, "note": note, "path": p,
                            "size": n, "running": bool(running)})
    return out


def _wb_targets():
    items = []
    seen = set()
    for tag, label in (("CN", "WorkBuddy 国内版"), ("AI", "WorkBuddy 国际版")):
        isrun = C.running(C.EXENAME[tag])
        root = C.DATA[tag]
        key = os.path.normcase(os.path.abspath(root))
        if os.path.isdir(root) and key not in seen:
            seen.add(key)
            items += targets(label, root, WB_SPEC, isrun)
        la = os.path.join(C.LOCAL, "WorkBuddy" if tag == "CN" else "WorkBuddy AI")
        if os.path.isdir(la):
            items += targets(label, la, WB_LOCAL, isrun)

    # migrate 实测到的自定义数据目录（用户可能把数据挪过位置）
    anyrun = C.running(C.EXENAME["CN"]) or C.running(C.EXENAME["AI"])
    try:
        mr = M.scan()
    except Exception:
        mr = {"items": []}
    for it in mr.get("items", []):
        if it.get("product") != "WorkBuddy" or it.get("kind") != "data":
            continue
        root = it.get("path") or ""
        key = os.path.normcase(os.path.abspath(root))
        if not os.path.isdir(root) or key in seen:
            continue
        seen.add(key)
        items += targets("WorkBuddy（自定义位置）", root, WB_SPEC, anyrun)
    return items


def _qoder_targets(qr):
    items = []
    seen = set()
    for k in ("intl", "cn"):
        d = (qr or {}).get(k) or {}
        exe = d.get("exe")
        root = ""
        if exe:
            dn = (M._product_json(exe) or {}).get("dataDirectoryName")
            if dn:
                root = os.path.join(C.APPDATA, dn)
        if not root or not os.path.isdir(root):
            root = os.path.join(C.APPDATA, QODER_FALLBACK[k])
        key = os.path.normcase(os.path.abspath(root))
        if key in seen or not os.path.isdir(root):
            continue
        seen.add(key)
        name = d.get("name") or ("Qoder 国际版" if k == "intl" else "Qoder 中国版")
        isrun = bool(d.get("running"))
        items += targets(name, root, QODER_SPEC, isrun)
        part = os.path.join(root, "Partitions")
        if os.path.isdir(part):
            try:
                subs = sorted(os.listdir(part))
            except OSError:
                subs = []
            for sub in subs:
                psub = os.path.join(part, sub)
                if os.path.isdir(psub) and not C.islink(psub):
                    items += targets(name + " · " + sub, psub, QODER_PART, isrun)
    return items


def scan(qr=None):
    """返回可清理项 [{group,label,note,path,size,running}]，只含白名单且非空的目录。"""
    if qr is None:
        try:
            qr = Q.check()
        except Exception:
            qr = {}
    return _wb_targets() + _qoder_targets(qr)


def purge(p):
    """清空目录内容但保留目录；返回 (释放字节, 错误列表)。"""
    freed, errors = 0, []
    try:
        names = os.listdir(p)
    except OSError as e:
        return 0, [p + "：" + str(e)]
    for name in names:
        full = os.path.join(p, name)
        if C.islink(full):
            continue
        try:
            if os.path.isdir(full):
                n = dir_size(full)
                shutil.rmtree(full)
            else:
                n = os.path.getsize(full)
                os.remove(full)
            freed += n
        except OSError as e:
            errors.append(full + "：" + str(e))
    return freed, errors


def clean(items):
    """软件运行中的项跳过（文件被占用，清不干净）。"""
    freed, cleaned, skipped, errors = 0, [], [], []
    for it in items:
        if it.get("running"):
            skipped.append(it)
            continue
        p = it.get("path") or ""
        if not os.path.isdir(p) or C.islink(p):
            continue
        n, errs = purge(p)
        freed += n
        errors.extend(errs)
        cleaned.append({"group": it["group"], "label": it["label"], "freed": n})
    return {"freed": freed, "cleaned": cleaned, "skipped": skipped, "errors": errors}
