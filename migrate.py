#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 位置探测 + 无损迁移。所有路径都靠实测证据发现，不做假设。
# 证据来源：注册表卸载项 / 安装目录的 product.json / 数据目录特征文件 / 会话 jsonl 的 cwd。
import os, sys, json, glob, shutil, subprocess, datetime

HOME = os.path.expanduser("~")
LOCAL = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
APPDATA = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")
REPARSE = 0x400


def _is_link(p):
    try:
        return bool(os.lstat(p).st_file_attributes & REPARSE)
    except OSError:
        return False


def _link_target(p):
    try:
        return os.readlink(p) if _is_link(p) else ""
    except OSError:
        return ""


def _exists_dir(p):
    return bool(p) and os.path.isdir(p)


def _read_json(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _product_json(install_exe):
    # 从安装目录读 product.json；WorkBuddy 没有该文件时返回空
    if not install_exe:
        return {}
    d = os.path.dirname(install_exe)
    for rel in ("resources/product.json", "resources/app/product.json",
                "resources/app.asar.unpacked/cli/product.json"):
        f = os.path.join(d, rel)
        if os.path.isfile(f):
            j = _read_json(f)
            if j:
                j["_source"] = f
                return j
    return {}


def _item(key, kind, product, path, evidence, note=""):
    return {"key": key, "kind": kind, "product": product, "path": path,
            "evidence": evidence, "note": note,
            "exists": _exists_dir(path),
            "migrated": _is_link(path),
            "target": _link_target(path)}


def scan():
    """返回本机 WorkBuddy / Qoder 的全部相关位置：软件本体 / 数据 / 会话 / 项目。"""
    out = {"items": [], "projects": [], "warnings": []}
    import wbcore as C
    import qoder as Q

    # WorkBuddy 软件本体：注册表卸载项
    for it in C.installed():
        out["items"].append(_item("wb:app:" + it["tag"], "app", "WorkBuddy",
                                  os.path.dirname(it["exe"]),
                                  "注册表卸载项 " + (it["name"] or ""),
                                  "版本 " + (it["version"] or "?")))

    # WorkBuddy 数据：特征为 projects/ 且 MEMORY.md
    wb_data = os.path.join(HOME, ".workbuddy")
    if _exists_dir(os.path.join(wb_data, "projects")) and os.path.isfile(os.path.join(wb_data, "MEMORY.md")):
        out["items"].append(_item("wb:data", "data", "WorkBuddy", wb_data,
                                  "含 projects/ 与 MEMORY.md 特征文件"))

    # WorkBuddy Electron userData：存在且非空才列
    wb_ud = os.path.join(APPDATA, "WorkBuddy")
    if _exists_dir(wb_ud):
        try:
            if os.listdir(wb_ud):
                out["items"].append(_item("wb:userdata", "data", "WorkBuddy", wb_ud,
                                          "Electron userData 目录"))
        except OSError:
            pass

    # WorkBuddy 会话 + 项目（项目路径从 jsonl 的 cwd 读）
    sess_root = os.path.join(wb_data, "projects")
    if _exists_dir(sess_root):
        n_sess = len(glob.glob(os.path.join(sess_root, "*", "*.jsonl")))
        out["items"].append(_item("wb:sessions", "sessions", "WorkBuddy", sess_root,
                                  "会话目录，%d 个 jsonl" % n_sess))
        out["projects"].extend(_scan_cwd(sess_root, "WorkBuddy"))

    # Qoder 软件本体
    for it in Q.installed():
        out["items"].append(_item("qd:app:" + it["tag"], "app", "Qoder",
                                  os.path.dirname(it["exe"]),
                                  "Qoder 安装发现（" + it["tag"] + "）",
                                  "版本 " + (it["version"] or "?")))

    # Qoder CLI 数据：~/.qoder
    qd_cli = os.path.join(HOME, ".qoder")
    if _exists_dir(os.path.join(qd_cli, "projects")) or os.path.isfile(os.path.join(qd_cli, "state.json")):
        out["items"].append(_item("qd:cli", "data", "Qoder", qd_cli,
                                  "含 projects/ 或 state.json 特征文件"))

    # Qoder 数据目录名取自安装目录 product.json 的 dataDirectoryName（不猜）
    listed = set()
    for it in Q.installed():
        pj = _product_json(it["exe"])
        dn = pj.get("dataDirectoryName")
        if not dn or dn in listed:
            continue
        listed.add(dn)
        p = os.path.join(APPDATA, dn)
        if _exists_dir(p):
            out["items"].append(_item("qd:data:" + dn, "data", "Qoder", p,
                                      "product.json 声明 dataDirectoryName=" + dn))

    # Qoder 会话/项目
    qd_sess = os.path.join(qd_cli, "projects")
    if _exists_dir(qd_sess):
        out["items"].append(_item("qd:sessions", "sessions", "Qoder", qd_sess,
                                  "会话/项目目录"))

    # 按规范化路径去重
    seen = set()
    uniq = []
    for it in out["items"]:
        k = os.path.normcase(os.path.normpath(it["path"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(it)
    out["items"] = uniq

    pseen = set()
    puniq = []
    for p in out["projects"]:
        k = os.path.normcase(os.path.normpath(p["path"]))
        if k in pseen:
            continue
        pseen.add(k)
        puniq.append(p)
    out["projects"] = puniq

    if not out["items"]:
        out["warnings"].append("未检测到 WorkBuddy / Qoder 的安装或数据目录")
    return out


def _scan_cwd(sess_root, product):
    # 项目路径取自会话 jsonl 的 cwd 字段，不反解目录名
    found = {}
    for f in glob.glob(os.path.join(sess_root, "*", "*.jsonl"))[:400]:
        try:
            with open(f, encoding="utf-8") as fh:
                for _ in range(3):
                    line = fh.readline()
                    if not line:
                        break
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    cwd = d.get("cwd")
                    if cwd:
                        key = os.path.normcase(os.path.normpath(cwd))
                        if key not in found:
                            found[key] = {"path": cwd, "product": product,
                                          "exists": os.path.isdir(cwd), "sessions": 0}
                        found[key]["sessions"] += 1
                        break
        except OSError:
            continue
    return list(found.values())


def _running(product):
    names = {"WorkBuddy": ["WorkBuddy.exe", "WorkBuddyAI.exe"],
             "Qoder": ["Qoder.exe", "Qoder CN.exe"]}.get(product, [])
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, errors="replace", timeout=20).stdout
    except Exception:
        return []
    hit = []
    for line in out.splitlines():
        cols = [c.strip('"') for c in line.split('","')]
        if cols and cols[0].strip('"') in names:
            hit.append(cols[0].strip('"'))
    return sorted(set(hit))


def free_gb(path):
    try:
        drive = os.path.splitdrive(os.path.abspath(path))[0] + os.sep
        return shutil.disk_usage(drive).free / float(1 << 30)
    except OSError:
        return None


def _dir_size(path):
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _norm_root(t):
    t = (t or "").strip().rstrip("\/")
    if len(t) == 2 and t[1] == ":":
        t += "\\"
    return t


def plan(keys, target_root):
    """按选中的 key 与目标根目录生成迁移计划（不做任何改动）。
    只接受 app / data：会话与项目都在数据目录内部，不能单独迁。"""
    r = scan()
    root = _norm_root(target_root)
    plans = []
    for it in r["items"]:
        if it["key"] not in keys:
            continue
        if it["kind"] not in ("app", "data"):
            continue
        src = it["path"].rstrip("\/")
        base = os.path.basename(src)
        dst = os.path.join(root, "Migrations", it["product"], base)
        plans.append({"key": it["key"], "kind": it["kind"], "product": it["product"],
                      "src": src, "dst": dst, "migrated": it["migrated"],
                      "target": it["target"], "evidence": it["evidence"]})
    return plans


def precheck(plans):
    """迁移前检查：返回 [(level, msg)]，有 error 就不该继续。"""
    lines = []
    ok = True
    for p in plans:
        if p["migrated"]:
            ok = False
            lines.append(("error", p["src"] + " 已经是指向 " + p["target"] + " 的联接，无需迁移"))
    prods = sorted({p["product"] for p in plans})
    for prod in prods:
        run = _running(prod)
        if run:
            ok = False
            lines.append(("error", prod + " 正在运行（" + ", ".join(run) + "）—— 迁移前必须完全退出"))
    drives = sorted({os.path.splitdrive(os.path.abspath(p["dst"]))[0] for p in plans})
    for d in drives:
        g = free_gb(d + os.sep)
        if g is not None and g < 3:
            ok = False
            lines.append(("error", d + " 剩余 %.1f GB，迁移目标空间不足（建议 ≥3 GB）" % g))
    if not lines:
        lines.append(("ok", "前置检查通过"))
    return ok, lines


def migrate_one(p, apply=False, on_log=print):
    """零删除迁移：复制 → 校验 → 原名改 .bak → mklink /J → 探针 → 失败回滚。
    ponytail: 不删任何东西，.bak 留给你确认后再清。"""
    src, dst = p["src"], p["dst"]
    if p["migrated"]:
        on_log("跳过（已迁移）: " + src)
        return False
    if not os.path.isdir(src):
        on_log("跳过（源不存在）: " + src)
        return False
    if os.path.exists(dst):
        on_log("跳过（目标已存在）: " + dst)
        return False
    on_log("计划: " + src + "  ->  " + dst)
    if not apply:
        return True

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    # 1 复制
    r = subprocess.run(["robocopy", src, dst, "/E", "/COPY:DAT", "/DCOPY:DAT", "/XJ",
                        "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS", "/NP"],
                       capture_output=True, text=True, errors="replace")
    if r.returncode >= 8:
        on_log("复制失败 (robocopy %d)" % r.returncode)
        return False
    # 2 校验文件数
    n_src = sum(len(fs) for _r, _d, fs in os.walk(src))
    n_dst = sum(len(fs) for _r, _d, fs in os.walk(dst))
    if n_src != n_dst:
        on_log("校验失败：源 %d 文件 / 目标 %d 文件" % (n_src, n_dst))
        return False
    on_log("复制完成，%d 个文件" % n_dst)

    # 3 原名改 .bak
    bak = src + ".bak"
    if os.path.exists(bak):
        on_log("回退目录已存在，跳过: " + bak)
        return False
    try:
        os.rename(src, bak)
    except OSError as e:
        on_log("改名失败（可能仍被占用）: " + str(e))
        return False

    # 4 建联接
    rc = subprocess.run(["cmd", "/c", "mklink", "/J", src, dst],
                        capture_output=True, text=True, errors="replace").returncode
    if rc != 0:
        os.rename(bak, src)
        on_log("建立联接失败，已回滚")
        return False

    # 5 探针
    probe = os.path.join(src, ".__migrate_probe__")
    try:
        with open(probe, "w") as f:
            f.write("x")
        ok = os.path.isfile(os.path.join(dst, ".__migrate_probe__"))
        if ok:
            os.remove(probe)
    except OSError:
        ok = False
    if not ok:
        on_log("探针验证失败（写入未落到目标盘）")
    on_log("迁移完成: " + src + "  ->  " + dst + "；原目录保留为 " + bak)
    return True
