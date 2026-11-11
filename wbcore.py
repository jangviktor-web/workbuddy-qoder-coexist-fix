#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# WorkBuddy 共存管家 - 核心逻辑（GUI 与守护模式共用）
import os, json, shutil, datetime, subprocess, winreg

BS = chr(92); Q = chr(34)
ROOT = "D:/Apps/WBCoexist"
H = "C:/Users/jangviktor"
D = "D:/Users/jangviktor"
CONFIG = ROOT + "/config.json"
LOGFILE = ROOT + "/run.log"
PYW = "D:/Python310/pythonw.exe"
APP = ROOT + "/WBCoexist.pyw"
DEFAULT = {"primary": "CN", "guard": False, "autostart": False}

EXE = {"CN": "D:/WorkBuddy/WorkBuddy.exe",
       "AI": "D:/Apps/WorkBuddyAI/WorkBuddyAI.exe"}
UB = BS.join(["Software", "Microsoft", "Windows", "CurrentVersion", "Uninstall"])
REG = {"CN": UB + BS + "BFD312E9-1019-4F57-9F44-F86246833B50",
       "AI": UB + BS + "C02C88CB-5DAE-4330-AEC1-572CFD048A59"}
DATA = {"CN": H + "/.workbuddy", "AI": H + "/.workbuddy-ai"}
DDATA = {"CN": D + "/.workbuddy", "AI": D + "/.workbuddy-ai"}
SM = H + "/AppData/Roaming/Microsoft/Windows/Start Menu/Programs"
LNK = {"CN": SM + "/WorkBuddy.lnk", "AI": SM + "/WorkBuddy AI.lnk"}
KEY = BS.join(["Software", "Classes", "buddy-app", "shell", "open", "command"])
CACHE = H + "/AppData/Local/@genieworkbuddy-desktop-updater/installer.exe"
ARCH = D + "/WorkBuddy/Claw/.updater-archive"
RUNKEY = BS.join(["Software", "Microsoft", "Windows", "CurrentVersion", "Run"])
RUNNAME = "WBCoexist"

def cfg_load():
    try:
        c = json.load(open(CONFIG, encoding="utf-8"))
        return dict(DEFAULT, **c)
    except Exception:
        return dict(DEFAULT)

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
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq " + e],
                       capture_output=True, text=True, errors="replace")
    return e.lower() in r.stdout.lower()

def check(primary="CN"):
    out = {"apps": {}, "owner": "?", "cmd": "", "cache": False,
           "cache_size": 0, "issues": []}
    for t in ("CN", "AI"):
        exe = EXE[t]
        u = qv(REG[t], "UninstallString")
        d = dict(exe=os.path.isfile(exe),
                 reg=exe.rsplit("/", 1)[0].lower() in u.replace(BS, "/").lower(),
                 lnk=os.path.isfile(LNK[t]),
                 data=islink(DATA[t]) and os.path.isdir(DDATA[t]),
                 running=running(exe.rsplit("/", 1)[1]))
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
        new = Q + EXE[primary].replace("/", BS) + Q + " " + Q + "%1" + Q
        acts.append("buddy-app 归属 -> " + primary + "  " + new)
        if apply:
            k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, KEY)
            winreg.SetValue(k, "", winreg.REG_SZ, new)
            winreg.CloseKey(k)
    if "cache" in bad and archive_cache:
        dst = ARCH + "/installer-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".exe"
        acts.append("更新器缓存归档 -> " + dst)
        if apply:
            os.makedirs(ARCH, exist_ok=True)
            shutil.move(CACHE, dst)
    for b in bad:
        if b.endswith((":exe", ":reg", ":lnk", ":data")):
            acts.append("需人工复核: " + b)
    if not acts:
        acts.append("无需修复，两版共存状态正常")
    return acts

def daemon_tick(c):
    # 后台守护只修 buddy-app，绝不碰更新缓存，避免打断正在进行的更新
    cur = qv(KEY)
    owner = "AI" if "workbuddyai.exe" in cur.lower() else ("CN" if "workbuddy.exe" in cur.lower() else "?")
    if owner != c["primary"]:
        rep = check(c["primary"])
        fix(rep, c["primary"], apply=True, archive_cache=False)
        return "检测到 buddy-app 被 " + owner + " 抢占，已自动修回 " + c["primary"]
    return ""

def autostart_get():
    return bool(qv(RUNKEY, RUNNAME))

def autostart_set(on):
    try:
        k = winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUNKEY)
        if on:
            exe = ROOT + "/WBCoexist.exe"
            if os.path.isfile(exe):
                val = Q + exe.replace("/", BS) + Q + " --daemon"
            else:
                val = Q + PYW.replace("/", BS) + Q + " " + Q + APP.replace("/", BS) + Q + " --daemon"
            winreg.SetValueEx(k, RUNNAME, 0, winreg.REG_SZ, val)
        else:
            try: winreg.DeleteValue(k, RUNNAME)
            except OSError: pass
        winreg.CloseKey(k)
        return True
    except Exception:
        return False
