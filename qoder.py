#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Qoder 双版本共存核心逻辑（国际版 / 中国版共用浏览器连接器）
# 与 wbcore.py 相互独立，可单独导入；不依赖第三方库、不需要管理员权限。
import os, re, json, time, ctypes, hashlib, shutil, datetime, subprocess, winreg

HOST_NAME = "com.qoder.app.connector"
INTL_ORIGIN = "chrome-extension://gblapfbnbicdckfhkllcnfleiemhmgeb/"
CN_ORIGIN = "chrome-extension://oknkojfamnpljdfpinkhbibicojelkoj/"

HOME = os.path.expanduser("~")
CONNECTOR = os.path.join(HOME, ".qoder", "browser-connector")
MANIFEST = os.path.join(CONNECTOR, HOST_NAME + ".json")
HOSTS = os.path.join(CONNECTOR, "hosts")
CLIENTS = os.path.join(CONNECTOR, "clients")
LOCAL = os.environ.get("LOCALAPPDATA") or os.path.join(HOME, "AppData", "Local")
BACKUPS = os.path.join(LOCAL, "WBCoexist", "qoder-backups")

INTL_LAUNCHER_DIR = os.path.join(LOCAL, "Qoder", "Qoder Launcher")
CN_LAUNCHER_INI = os.path.join(
    os.environ.get("ProgramData", r"C:\ProgramData"),
    "Qoder CN", "Qoder CN Launcher", "install.ini")

CHROME_KEY = r"SOFTWARE\Google\Chrome\NativeMessagingHosts" + "\\" + HOST_NAME
EDGE_KEY = r"SOFTWARE\Microsoft\Edge\NativeMessagingHosts" + "\\" + HOST_NAME

_HEX64 = re.compile(r"^[0-9a-f]{64}$", re.I)


def _sha256(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _version(v):
    if not v:
        return None
    m = re.search(r"\d+(\.\d+){1,3}", str(v))
    if not m:
        return None
    parts = m.group(0).split(".")
    if len(parts) == 4 and parts[3] == "0":
        parts = parts[:3]
    return ".".join(parts)


def _vtuple(v):
    if not v:
        return ()
    return tuple(int(x) for x in re.findall(r"\d+", v))


def _path_eq(a, b):
    if not a or not b:
        return False
    try:
        return os.path.normcase(os.path.abspath(a)).rstrip("\\") == \
            os.path.normcase(os.path.abspath(b)).rstrip("\\")
    except OSError:
        return a.lower() == b.lower()


def _read_ini(path):
    if not os.path.isfile(path):
        return {}
    text = None
    for enc in ("utf-8-sig", "utf-16", "utf-8"):
        try:
            with open(path, encoding=enc) as f:
                text = f.read()
            break
        except (UnicodeError, OSError):
            continue
    if text is None:
        return {}
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in "[;#":
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _uninstall_entries():
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    out = []
    for hive, path in roots:
        try:
            key = winreg.OpenKey(hive, path)
        except OSError:
            continue
        i = 0
        while True:
            try:
                sub = winreg.EnumKey(key, i)
            except OSError:
                break
            i += 1
            try:
                sk = winreg.OpenKey(key, sub)
            except OSError:
                continue
            def val(name):
                try:
                    return winreg.QueryValueEx(sk, name)[0]
                except OSError:
                    return ""
            out.append((val("DisplayName"), val("DisplayVersion"), val("UninstallString")))
            winreg.CloseKey(sk)
        winreg.CloseKey(key)
    return out


def _install_dir(uninstall_string):
    if not uninstall_string:
        return None
    m = re.match(r'^"([^"]+)"', uninstall_string.strip())
    exe = m.group(1) if m else None
    if not exe:
        m = re.match(r"^(\S+?\.exe)", uninstall_string.strip(), re.I)
        exe = m.group(1) if m else None
    return os.path.dirname(exe) if exe else None


def _find_install_dir(cn):
    for dn, dv, us in _uninstall_entries():
        if not dn:
            continue
        is_cn = "qoder cn" in dn.lower()
        is_intl = (not is_cn) and dn.lower().startswith("qoder")
        if (cn and is_cn) or ((not cn) and is_intl):
            d = _install_dir(us)
            if d and os.path.isdir(d):
                return d, dv
    return None, None


def _tasklist_pids(names):
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True, errors="replace",
                             timeout=20).stdout
    except Exception:
        return {}
    wanted = set(n.lower() for n in names)
    res = {}
    for line in out.splitlines():
        cols = [c.strip('"') for c in line.split('","')]
        if len(cols) >= 2 and cols[0].strip('"').lower() in wanted:
            key = cols[0].strip('"').lower()
            try:
                res.setdefault(key, []).append(int(cols[1].strip('"')))
            except ValueError:
                pass
    return res


def _running_pids(names):
    found = _tasklist_pids(names)
    out = []
    for n in names:
        out.extend(found.get(n.lower(), []))
    return out


def _pid_alive(pid):
    if not pid or pid <= 0:
        return False
    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(0x1000, False, int(pid))  # QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == 259  # STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)


def _newest_version_exe(install_dir):
    if not install_dir:
        return None
    vroot = os.path.join(install_dir, ".qoder-versions")
    if not os.path.isdir(vroot):
        return None
    best, best_v = None, ()
    for name in os.listdir(vroot):
        exe = os.path.join(vroot, name, "Qoder.exe")
        if not os.path.isfile(exe):
            continue
        vt = _vtuple(name)
        if best is None or vt > best_v:
            best, best_v = exe, vt
    return best


def detect_intl(pids=None):
    d = {"id": "qoder", "name": "Qoder 国际版", "exe": None, "version": None,
         "launcher": None, "hash": None, "running": [], "state": ""}
    state_path = os.path.join(INTL_LAUNCHER_DIR, "state.ini")
    ini = _read_ini(state_path)
    d["state"] = ini.get("status", "")
    install_dir = ini.get("installDir")
    exe = None
    rel = ini.get("appExecutable")
    if install_dir and rel:
        exe = os.path.join(install_dir, rel)
    if not exe or not os.path.isfile(exe):
        exe = _newest_version_exe(install_dir)
    if not exe or not os.path.isfile(exe):
        reg_dir, _dv = _find_install_dir(False)
        if reg_dir:
            install_dir = reg_dir
            exe = os.path.join(reg_dir, "Qoder.exe")
    if exe and os.path.isfile(exe):
        d["exe"] = exe
    d["version"] = _version(ini.get("targetVersion"))
    if not d["version"]:
        reg_dir, dv = _find_install_dir(False)
        d["version"] = _version(dv)

    launcher = None
    if d["exe"]:
        launcher = os.path.join(os.path.dirname(d["exe"]), "resources", "launcher", "Qoder Launcher.exe")
    if not launcher or not os.path.isfile(launcher):
        launcher = os.path.join(INTL_LAUNCHER_DIR, "Qoder Launcher.exe")
    if os.path.isfile(launcher):
        d["launcher"] = launcher
        d["hash"] = _sha256(launcher)
    d["running"] = pids.get("qoder.exe", []) if pids is not None else _running_pids(["Qoder.exe"])
    return d


def detect_cn(pids=None):
    d = {"id": "qoder-cn", "name": "Qoder 中国版", "exe": None, "version": None,
         "launcher": None, "hash": None, "running": [], "state": ""}
    install_dir, display_version = _find_install_dir(True)
    ini = _read_ini(CN_LAUNCHER_INI)
    if not install_dir:
        install_dir = ini.get("installDir")
    d["state"] = ini.get("status", "")
    if install_dir:
        exe = os.path.join(install_dir, "Qoder CN.exe")
        if os.path.isfile(exe):
            d["exe"] = exe
        launcher = os.path.join(install_dir, "resources", "launcher", "Qoder CN Launcher.exe")
        if os.path.isfile(launcher):
            d["launcher"] = launcher
            d["hash"] = _sha256(launcher)
    d["version"] = _version(display_version) or _version(ini.get("targetVersion"))
    d["running"] = pids.get("qoder cn.exe", []) if pids is not None else _running_pids(["Qoder CN.exe"])
    return d


def _pick_target(cands, host_hash=None):
    # 按版本号选基准代际：版本高者胜；并列时依次看 当前 manifest > host 副本存在 > 正在运行 > 哈希序
    # ponytail: 哈希序只是确定性兜底，不代表内容更优；真要按内容选得比启动器签名
    if not cands:
        return None
    newest = max(_vtuple(p.get("version")) for p in cands)
    tied = [p for p in cands if _vtuple(p.get("version")) == newest]
    for p in tied:
        if host_hash and host_hash == (p.get("hash") or "").lower():
            return p
    for p in tied:
        if p.get("hash") and os.path.isdir(os.path.join(HOSTS, p["hash"])):
            return p
    for p in tied:
        if p.get("running"):
            return p
    return sorted(tied, key=lambda x: (x.get("hash") or ""))[0]


def _hash_from_host_path(path):
    if not path:
        return None
    name = os.path.basename(os.path.dirname(path))
    return name.lower() if _HEX64.match(name or "") else None


def _reg_value(key_path):
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, key_path) as k:
                v = winreg.QueryValueEx(k, "")[0]
                if v:
                    return v
        except OSError:
            continue
    return ""


def _reg_set(key_path, value):
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
        winreg.SetValueEx(k, "", 0, winreg.REG_SZ, value)


def _scan_clients():
    out = []
    if not os.path.isdir(CLIENTS):
        return out
    for name in os.listdir(CLIENTS):
        if not name.lower().endswith(".json"):
            continue
        path = os.path.join(CLIENTS, name)
        rec = {"file": name, "path": path, "product": "", "name": "", "pid": 0,
               "userDataPath": "", "alive": False}
        try:
            with open(path, encoding="utf-8") as f:
                o = json.load(f)
            rec["product"] = o.get("product", "")
            rec["name"] = o.get("name", "")
            rec["pid"] = int(o.get("pid") or 0)
            rec["userDataPath"] = o.get("userDataPath", "")
            rec["alive"] = _pid_alive(rec["pid"])
        except Exception:
            rec["alive"] = False
            rec["pid"] = 0
        out.append(rec)
    return out


def check():
    pids = _tasklist_pids(["Qoder.exe", "Qoder CN.exe"])
    rep = {"intl": detect_intl(pids), "cn": detect_cn(pids),
           "expected": {"hash": None, "path": None, "version": None, "source": None},
           "manifest": {"exists": False, "valid": False, "host_path": "", "host_hash": None,
                        "origins": [], "origins_ok": False, "error": ""},
           "registry": {"chrome_ok": False, "edge_ok": False,
                        "chrome_value": _reg_value(CHROME_KEY), "edge_value": _reg_value(EDGE_KEY)},
           "issues": [], "warnings": [], "orphans": [], "clients": []}
    m = rep["manifest"]
    m["exists"] = os.path.isfile(MANIFEST)
    if m["exists"]:
        try:
            with open(MANIFEST, encoding="utf-8") as f:
                data = json.load(f)
            m["valid"] = True
            m["host_path"] = data.get("path", "") or ""
            m["origins"] = [o for o in (data.get("allowed_origins") or []) if isinstance(o, str)]
            m["host_hash"] = _hash_from_host_path(m["host_path"])
        except Exception as e:
            m["error"] = str(e).splitlines()[0][:160] if str(e) else "JSON 解析失败"
    m["origins_ok"] = any(o.lower() == INTL_ORIGIN.lower() for o in m["origins"]) and \
        any(o.lower() == CN_ORIGIN.lower() for o in m["origins"])
    rep["registry"]["chrome_ok"] = _path_eq(rep["registry"]["chrome_value"], MANIFEST)
    rep["registry"]["edge_ok"] = _path_eq(rep["registry"]["edge_value"], MANIFEST)

    cands = [p for p in (rep["intl"], rep["cn"]) if p["launcher"] and p["hash"]]
    target = _pick_target(cands, m["host_hash"])
    if target:
        rep["expected"] = {"hash": target["hash"], "path": os.path.join(HOSTS, target["hash"], "Qoder Browser Connector.exe"),
                           "version": target["version"], "source": target["name"]}
        newest = max(_vtuple(p.get("version")) for p in cands)
        tied = [p for p in cands if _vtuple(p.get("version")) == newest]
        if len(tied) > 1:
            rep["warnings"].append("两版启动器版本号相同或无法比较，已按确定性规则选定 " + target["name"] + " 的 host；扩展异常时可手动切换")

    exp = rep["expected"]
    if not exp["hash"]:
        rep["issues"].append("未找到任一产品的启动器副本，无法定位正确的连接器 host")
    elif not os.path.isfile(exp["path"]):
        rep["issues"].append("最新代际的 host 副本缺失")
    if not m["exists"]:
        rep["issues"].append("共享 manifest 缺失")
    elif not m["valid"]:
        rep["issues"].append("共享 manifest 无法解析: " + m["error"])
    else:
        if exp["path"] and not _path_eq(m["host_path"], exp["path"]):
            rep["issues"].append("manifest 指向的不是最新代际 host")
        if not m["origins_ok"]:
            rep["issues"].append("manifest 缺少两个扩展来源")
    if not rep["registry"]["chrome_ok"]:
        rep["issues"].append("Chrome native messaging 注册缺失或指向错误")
    if not rep["registry"]["edge_ok"]:
        rep["issues"].append("Edge native messaging 注册缺失或指向错误")

    iv, cv = rep["intl"]["version"], rep["cn"]["version"]
    if iv and cv and _vtuple(iv) != _vtuple(cv):
        rep["warnings"].append("两版版本不同（国际版 %s / 中国版 %s），升级完成前连接器可能在两边启动时来回切换" % (iv, cv))

    if os.path.isdir(HOSTS):
        keep = set()
        for p in (rep["intl"], rep["cn"]):
            if p["hash"]:
                keep.add(p["hash"].lower())
        if exp["hash"]:
            keep.add(exp["hash"].lower())
        for name in os.listdir(HOSTS):
            full = os.path.join(HOSTS, name)
            if os.path.isdir(full) and name.lower() not in keep:
                rep["orphans"].append(full)

    rep["clients"] = _scan_clients()
    return rep


def needs_fix(rep):
    return bool(rep["issues"]) and bool(rep["expected"]["hash"])


def fix(rep=None, apply=True):
    if rep is None:
        rep = check()
    acts = []
    exp = rep["expected"]
    if not exp["hash"]:
        return ["无法修复：未找到任一产品的启动器副本"]

    src = None
    for p in (rep["intl"], rep["cn"]):
        if p["hash"] and p["hash"].lower() == exp["hash"].lower():
            src = p["launcher"]
            break
    if not os.path.isfile(exp["path"]):
        if not src or not os.path.isfile(src):
            return ["无法修复：缺少启动器源文件"]
        acts.append("补建 host 副本 hosts\\" + exp["hash"][:12] + "\\")
        if apply:
            os.makedirs(os.path.dirname(exp["path"]), exist_ok=True)
            shutil.copy2(src, exp["path"])
    else:
        acts.append("host 副本已存在，跳过")

    m = rep["manifest"]
    need = (not m["exists"]) or (not m["valid"]) or \
        (not _path_eq(m["host_path"], exp["path"])) or (not m["origins_ok"])
    if need:
        if m["exists"]:
            acts.append("备份旧 manifest 到 qoder-backups")
            if apply:
                os.makedirs(BACKUPS, exist_ok=True)
                dst = os.path.join(BACKUPS, "manifest-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
                try:
                    shutil.copy2(MANIFEST, dst)
                except OSError:
                    pass
        origins = list(m["origins"])
        if not any(o.lower() == INTL_ORIGIN.lower() for o in origins):
            origins.append(INTL_ORIGIN)
        if not any(o.lower() == CN_ORIGIN.lower() for o in origins):
            origins.append(CN_ORIGIN)
        acts.append("manifest 已指向最新代际 host（" + exp["hash"][:12] + "）")
        if apply:
            os.makedirs(CONNECTOR, exist_ok=True)
            data = {"name": HOST_NAME, "description": "Qoder Browser Connector",
                    "path": exp["path"], "type": "stdio", "allowed_origins": origins}
            with open(MANIFEST, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        acts.append("manifest 已正确，跳过")

    if rep["registry"]["chrome_ok"]:
        acts.append("Chrome 注册已正确，跳过")
    else:
        acts.append("已校正 Chrome native messaging 注册")
        if apply:
            _reg_set(CHROME_KEY, MANIFEST)
    if rep["registry"]["edge_ok"]:
        acts.append("Edge 注册已正确，跳过")
    else:
        acts.append("已校正 Edge native messaging 注册")
        if apply:
            _reg_set(EDGE_KEY, MANIFEST)
    return acts


def clean(rep=None):
    if rep is None:
        rep = check()
    acts = []
    for d in rep["orphans"]:
        try:
            shutil.rmtree(d)
            acts.append("已删除孤儿 host 副本 hosts\\" + os.path.basename(d)[:12] + "\\")
        except OSError as e:
            acts.append("删除失败 " + os.path.basename(d)[:12] + ": " + str(e))
    for c in rep["clients"]:
        if c["alive"] or not c["pid"]:
            continue
        try:
            os.remove(c["path"])
            acts.append("已删除失效中继记录 " + c["file"])
        except OSError as e:
            acts.append("删除中继记录失败: " + str(e))
    return acts or ["没有可清理的项"]


def daemon_tick():
    # 只修共享连接器指向，不主动清理，避免打断正在进行的更新
    try:
        rep = check()
        if not needs_fix(rep):
            return ""
        acts = fix(rep, apply=True)
        return "Qoder 连接器被改写，已自动纠回: " + "; ".join(acts)
    except Exception as e:
        return "Qoder 守护异常: " + str(e)


def qoder_line(p):
    state = "运行中" if p["running"] else "未运行"
    ver = p["version"] or "?"
    return "%s %s  [%s]" % (p["name"], ver, state)


def preflight():
    # 安装/更新前只读检查，不改任何东西
    lines = []
    rep = check()
    for k in ("intl", "cn"):
        d = rep[k]
        if d.get("running"):
            lines.append(("info", d["name"] + " 正在运行 —— 安装该版前请完全退出（不只是关窗口）"))
        lines.append(("info", "%s 当前版本 %s，host 代际 %s"
                      % (d["name"], d.get("version") or "未知", (d.get("hash") or "")[:8] or "无")))
    m = rep["manifest"]
    if not m["exists"]:
        lines.append(("warn", "共享 manifest 不存在 —— 两版各启动一次即可生成，建议装完再检查"))
    elif not m["origins_ok"]:
        lines.append(("warn", "manifest 的 allowed_origins 不完整 —— 建议先点「一键修复」"))
    else:
        lines.append(("ok", "共享 manifest 正常，两个扩展 ID 都在"))
    if rep["registry"]["chrome_ok"] and rep["registry"]["edge_ok"]:
        lines.append(("ok", "Chrome / Edge 注册指向正确"))
    else:
        lines.append(("warn", "Chrome / Edge 注册指向不正确 —— 建议先点「一键修复」"))
    if rep["orphans"]:
        lines.append(("info", "存在 %d 个旧代际 host 副本，可点「清理孤儿」" % len(rep["orphans"])))
    lines.append(("info", "安装完成后守护会自动纠回被改写的连接器指向"))
    return {"ok": not needs_fix(rep), "lines": lines}
