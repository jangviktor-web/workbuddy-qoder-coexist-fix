#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 双版共存管家 - WorkBuddy 侧核心逻辑（GUI 与守护模式共用）
# 安装位置不硬编码：配置覆盖 -> 注册表卸载项 -> 常见默认路径
import os, sys, json, shutil, datetime, subprocess, winreg

BS = chr(92); Q = chr(34)
HOME = os.path.expanduser("~")
LOCAL = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
APPDATA = os.environ.get("APPDATA") or os.path.join(HOME, "AppData", "Roaming")

def app_root():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))

ROOT = app_root()
CONFIG = os.path.join(ROOT, "config.json")
LOGFILE = os.path.join(ROOT, "run.log")
DEFAULT = {"primary": "CN", "guard": False, "autostart": False,
           "paths": {"CN": "", "AI": ""}, "archive_dir": ""}

EXENAME = {"CN": "WorkBuddy.exe", "AI": "WorkBuddyAI.exe"}
CANDIDATES = {
    "CN": [os.path.join(LOCAL, "Programs", "WorkBuddy"),
           os.path.join(LOCAL, "Programs", "WorkBuddy CN"),
           "C:/Program Files/WorkBuddy",
           "C:/Program Files (x86)/WorkBuddy",
           "D:/WorkBuddy"],
    "AI": [os.path.join(LOCAL, "Programs", "WorkBuddy AI"),
           os.path.join(LOCAL, "Programs", "WorkBuddyAI"),
           "C:/Program Files/WorkBuddy AI",
           "C:/Program Files (x86)/WorkBuddy AI",
           "D:/Apps/WorkBuddyAI"],
}

UB = BS.join(["Software", "Microsoft", "Windows", "CurrentVersion", "Uninstall"])
WOW = BS.join(["Software", "WOW6432Node", "Microsoft", "Windows", "CurrentVersion", "Uninstall"])
SM = os.path.join(APPDATA, "Microsoft", "Windows", "Start Menu", "Programs")
LNK = {"CN": os.path.join(SM, "WorkBuddy.lnk"), "AI": os.path.join(SM, "WorkBuddy AI.lnk")}
DATA = {"CN": os.path.join(HOME, ".workbuddy"), "AI": os.path.join(HOME, ".workbuddy-ai")}
KEY = BS.join(["Software", "Classes", "buddy-app", "shell", "open", "command"])
CACHE = os.path.join(LOCAL, "@genieworkbuddy-desktop-updater", "installer.exe")
RUNKEY = BS.join(["Software", "Microsoft", "Windows", "CurrentVersion", "Run"])
RUNNAME = "WBCoexist"
EXE = {"CN": "", "AI": ""}


def cfg_load():
    try:
        c = json.load(open(CONFIG, encoding="utf-8"))
        d = dict(DEFAULT)
        d.update(c)
        if not isinstance(d.get("paths"), dict):
            d["paths"] = {"CN": "", "AI": ""}
        return d
    except Exception:
        return dict(DEFAULT, paths={"CN": "", "AI": ""})


def cfg_save(c):
    try:
        os.makedirs(ROOT, exist_ok=True)
        json.dump(c, open(CONFIG, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def log(msg):
    line = datetime.datetime.now().strftime("%H:%M:%S") + "  " + msg
    try:
        with open(LOGFILE, "a", encoding="utf-8") as f:
            f.write(line + chr(10))
    except Exception:
        pass
    return line


def qv(k, v=""):
    try:
        a = winreg.OpenKey(winreg.HKEY_CURRENT_USER, k)
        r = winreg.QueryValueEx(a, v)[0] if v else winreg.QueryValue(a, "")
        winreg.CloseKey(a)
        return r
    except OSError:
        return ""


def islink(p):
    try:
        return bool(os.lstat(p).st_file_attributes & 0x400)
    except OSError:
        return False


def running(e):
    if not e:
        return False
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + e],
                       capture_output=True, text=True, errors="replace")
    return e.lower() in r.stdout.lower()


def _uninstall_entries():
    # 返回 [(displayName, installLocation, displayIcon)]
    out = []
    for hive, path in ((winreg.HKEY_CURRENT_USER, UB),
                       (winreg.HKEY_LOCAL_MACHINE, UB),
                       (winreg.HKEY_LOCAL_MACHINE, WOW)):
        try:
            k = winreg.OpenKey(hive, path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(k, i)
            except OSError:
                break
            i += 1
            try:
                sk = winreg.OpenKey(k, sub)
            except OSError:
                continue
            def val(n):
                try:
                    return str(winreg.QueryValueEx(sk, n)[0])
                except OSError:
                    return ""
            name = val("DisplayName")
            if "workbuddy" in name.lower():
                out.append((name, val("InstallLocation"), val("DisplayIcon")))
            winreg.CloseKey(sk)
        winreg.CloseKey(k)
    return out


def _clean(p):
    p = (p or "").strip().strip(Q).strip()
    if p.lower().endswith(",0"):
        p = p[:-2]
    return p


def _match(name, tag):
    n = (name or "").lower()
    if "workbuddy" not in n:
        return False
    has_ai = (" ai" in n) or ("ai " in n) or n.endswith("ai")
    return has_ai if tag == "AI" else not has_ai


def find_install(tag):
    # 返回 (exe路径, 来源)：config / registry / default / notfound
    ov = _clean((cfg_load().get("paths") or {}).get(tag))
    if ov and os.path.isfile(ov):
        return ov, "config"
    exe = EXENAME[tag]
    for name, loc, icon in _uninstall_entries():
        if not _match(name, tag):
            continue
        for cand in (_clean(loc), os.path.dirname(_clean(icon))):
            if not cand:
                continue
            f = os.path.join(cand, exe)
            if os.path.isfile(f):
                return f, "registry"
    for d in CANDIDATES[tag]:
        f = os.path.join(d, exe)
        if os.path.isfile(f):
            return f, "default"
    return "", "notfound"


def exe_path(tag):
    if EXE.get(tag):
        return EXE[tag]
    p, _ = find_install(tag)
    EXE[tag] = p
    return p


def archive_dir():
    d = _clean(cfg_load().get("archive_dir"))
    return d or os.path.join(ROOT, ".updater-archive")


def check(primary="CN"):
    out = {"apps": {}, "owner": "?", "cmd": "", "cache": False,
           "cache_size": 0, "issues": [], "sources": {}, "paths": {}}
    entries = _uninstall_entries()
    for t in ("CN", "AI"):
        f, src = find_install(t)
        EXE[t] = f
        out["sources"][t] = src
        out["paths"][t] = f
        has_reg = any(_match(n, t) for n, loc, icon in entries)
        d = dict(exe=bool(f), reg=has_reg, lnk=os.path.isfile(LNK[t]),
                 data=os.path.isdir(DATA[t]), running=running(EXENAME[t]))
        out["apps"][t] = d
        for k in ("exe", "reg", "lnk", "data"):
            if not d[k]:
                out["issues"].append(t + ":" + k)
    cur = qv(KEY)
    out["cmd"] = cur
    out["owner"] = "AI" if "workbuddyai.exe" in cur.lower() else ("CN" if "workbuddy.exe" in cur.lower() else "?")
    if out["owner"] != primary:
        out["issues"].append("buddy-app")
    if os.path.isfile(CACHE):
        out["cache"] = True
        out["cache_size"] = os.path.getsize(CACHE)
        out["issues"].append("cache")
    return out


def fix(rep, primary="CN", apply=False, archive_cache=True):
    acts = []
    bad = rep["issues"]
    if "buddy-app" in bad:
        target = exe_path(primary)
        if not target:
            acts.append("找不到 " + primary + " 版程序，跳过协议修复")
        else:
            new = Q + target.replace("/", BS) + Q + " " + Q + "%1" + Q
            acts.append("buddy-app 归属 -> " + primary + "  " + new)
            if apply:
                k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY)
                winreg.SetValue(k, "", winreg.REG_SZ, new)
                winreg.CloseKey(k)
    if "cache" in bad and archive_cache:
        dst = os.path.join(archive_dir(), "installer-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".exe")
        acts.append("更新器缓存归档 -> " + dst)
        if apply:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(CACHE, dst)
    for b in bad:
        if b.endswith((":exe", ":reg", ":lnk", ":data")):
            acts.append("需人工复核: " + b)
    if not acts:
        acts.append("无需修复，两版共存状态正常")
    return acts


def daemon_tick(c):
    # 守护只修 buddy-app 归属，不碰更新缓存，避免打断正在进行的更新
    cur = qv(KEY)
    owner = "AI" if "workbuddyai.exe" in cur.lower() else ("CN" if "workbuddy.exe" in cur.lower() else "?")
    if owner != c["primary"]:
        target = exe_path(c["primary"])
        if not target:
            return ""
        new = Q + target.replace("/", BS) + Q + " " + Q + "%1" + Q
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY)
        winreg.SetValue(k, "", winreg.REG_SZ, new)
        winreg.CloseKey(k)
        return "检测到 buddy-app 被 " + owner + " 抢占，已自动修回 " + c["primary"]
    return ""


def autostart_get():
    return bool(qv(RUNKEY, RUNNAME))


def autostart_set(on):
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUNKEY)
        if on:
            exe = os.path.join(ROOT, "WBCoexist.exe")
            if os.path.isfile(exe):
                val = Q + exe.replace("/", BS) + Q + " --daemon"
            else:
                pyw = sys.executable
                if pyw.lower().endswith("python.exe"):
                    pyw = pyw[:-10] + "pythonw.exe"
                val = Q + pyw.replace("/", BS) + Q + " " + Q + os.path.join(ROOT, "WBCoexist.pyw").replace("/", BS) + Q + " --daemon"
            winreg.SetValueEx(k, RUNNAME, 0, winreg.REG_SZ, val)
        else:
            try:
                winreg.DeleteValue(k, RUNNAME)
            except OSError:
                pass
        winreg.CloseKey(k)
        return True
    except Exception:
        return False
