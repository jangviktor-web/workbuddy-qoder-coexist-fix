#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 从 WorkBuddy / WorkDaddy 的本地数据实测提取签到用的 accessToken。
# WorkBuddy 安装位置靠 wbcore.installed() 实测（注册表卸载项 -> 标准位置兜底），不做盘符假设。
import os, sys, json, glob, base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import wbcore as _C

WD_DATA = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming"), "WorkDaddy")

_KEY_JS_CODE = r"""try {
  const binding = process._linkedBinding('electron_browser_workbuddy_storage');
  const payload = JSON.parse(binding.loggerGet());
  if (payload && payload.version === 1 && typeof payload.atRestSecretKey === 'string') {
    const crypto = require('crypto');
    const key = crypto.createHash('sha256').update(payload.atRestSecretKey, 'utf8').digest();
    process.stdout.write('WD_KEY ' + key.toString('base64') + '\n');
    process.exit(0);
  }
  process.stderr.write('payload schema mismatch');
  process.exit(4);
} catch (e) {
  process.stderr.write(String(e));
  process.exit(4);
}"""


def _wb_exes():
    # 实测发现 WorkBuddy 可执行文件：注册表卸载项优先，标准安装位置兜底
    exes = []
    try:
        import wbcore as C
        for it in C.installed():
            exes.append(it["exe"])
    except Exception:
        pass
    local = os.environ.get("LOCALAPPDATA") or ""
    for d in (os.path.join(local, "Programs", "WorkBuddy"),
              os.path.join(local, "Programs", "WorkBuddy AI"),
              "C:/Program Files/WorkBuddy",
              "C:/Program Files/WorkBuddy AI"):
        for name in ("WorkBuddy.exe", "WorkBuddyAI.exe"):
            p = os.path.join(d, name)
            if os.path.isfile(p) and p not in exes:
                exes.append(p)
    return exes


def at_rest_key():
    # ELECTRON_RUN_AS_NODE 子进程经内部绑定拿 atRestSecretKey -> sha256，32 字节
    env = dict(os.environ, ELECTRON_RUN_AS_NODE="1")
    for exe in _wb_exes():
        try:
            r = _C.run_hidden([exe, "-e", _KEY_JS_CODE], env=env,
                              capture_output=True, text=True, timeout=20)
            for line in (r.stdout or "").splitlines():
                if line.startswith("WD_KEY "):
                    return base64.b64decode(line[7:].strip())
        except Exception:
            continue
    return None


def _aad(env):
    def lp(s):
        b = s.encode()
        return len(b).to_bytes(4, "big") + b
    u32 = lambda n: n.to_bytes(4, "big")
    return (b"WB-AAD\x00" + bytes([1]) + lp("WBEV1") + lp("sym-v1")
            + u32(env.get("suite") or 1) + lp(env.get("keyId") or "")
            + bytes([2]) + bytes([0]) + bytes([0]))


def _open_env(env, key):
    nonce = base64.b64decode(env.get("nonce") or "")
    tag = base64.b64decode(env.get("authTag") or "")
    ct = base64.b64decode(env.get("ciphertext") or "")
    return AESGCM(key).decrypt(nonce, ct + tag, _aad(env))


def _is_env(v):
    return isinstance(v, dict) and v.get("$wbEncrypted") == 1 and isinstance(v.get("envelope"), str)


def _decrypt_wb_envelopes(obj, key):
    # 递归解密 $wbEncrypted 信封；失败字段保留原值
    def walk(node):
        if isinstance(node, list):
            for i, x in enumerate(node):
                node[i] = walk(x)
            return node
        if not isinstance(node, dict):
            return node
        for k in list(node.keys()):
            v = node[k]
            if _is_env(v):
                try:
                    env = json.loads(base64.b64decode(v["envelope"]).decode())
                    node[k] = _open_env(env, key).decode("utf-8")
                except Exception:
                    pass
            elif isinstance(v, dict):
                node[k] = walk(v)
            elif isinstance(v, list):
                node[k] = walk(v)
        return node
    return walk(obj)


def _read_accounts_from_workdaddy():
    # 从 WorkDaddy 的账号备份提取 accessToken（经 WorkBuddy 运行时解密）
    if not os.path.isdir(WD_DATA):
        return []
    key = at_rest_key()
    if not key:
        return []
    out = []
    for f in glob.glob(os.path.join(WD_DATA, "accounts", "*.info")):
        try:
            data = json.loads(open(f, encoding="utf-8").read())
            data = _decrypt_wb_envelopes(data, key)
            acc = data.get("account") or {}
            auth = data.get("auth") or {}
            uid = acc.get("uid") or ""
            token = auth.get("accessToken") or ""
            if uid and token and isinstance(token, str):
                domain = auth.get("domain") or ""
                if domain and not domain.startswith("http"):
                    domain = "https://" + domain
                out.append({"uid": uid, "token": token, "domain": domain,
                            "nickname": acc.get("nickname") or uid})
        except Exception:
            continue
    return out


def fetch_tokens():
    # 可用 token 清单：WorkDaddy 备份自动发现 + config 手填合并（按 uid/token 去重）
    tokens = []
    try:
        tokens = _read_accounts_from_workdaddy()
    except Exception:
        tokens = []
    try:
        import checkin as K
        import wbcore as C
        t, u, e = K.from_config(C.cfg_load())
        if t:
            tokens.append({"uid": u, "token": t, "domain": "https://www.codebuddy.cn",
                           "nickname": "手动配置"})
    except Exception:
        pass
    seen = set()
    uniq = []
    for t in tokens:
        k = (os.path.normcase(t.get("uid") or ""), str(t.get("token"))[:24])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return uniq
