#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Qoder COSY 签名链路的 Python 复刻（零依赖：纯 Python AES-128，RSA 用 pow）。
# 算法来源：NextAgentX/qoder-trae-workbuddy-switch 的 modules/qoder/cosy.rs，含官方测试向量。
import base64, hashlib, json, secrets, time, uuid

CUSTOM_ALPHABET = "_doRTgHZBKcGVjlvpC,@aFSx#DPuNJme&i*MzLOEn)sUrthbf%Y^w.(kIQyXqWA!"
STD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_PAD = "$"
_TABLE = bytes.maketrans(STD_ALPHABET.encode(), CUSTOM_ALPHABET.encode())
_RTABLE = bytes.maketrans(CUSTOM_ALPHABET.encode(), STD_ALPHABET.encode())

SERVER_PUB_PEM_BODY = (
    "MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDA8iMH5c02LilrsERw9t6Pv5Nc"
    "4k6Pz1EaDicBMpdpxKduSZu5OANqUq8er4GM95omAGIOPOh+Nx0spthYA2BqGz+l"
    "6HRkPJ7S236FZz73In/KVuLnwI8JJ2CbuJap8kvheCCZpmAWpb/cPx/3Vr/J6I17"
    "XcW+ML9FoCI6AOvOzwIDAQAB")


def _pub_modulus():
    # 从 SPKI DER 解出 RSA modulus / exponent（纯 Python，不用 cryptography）
    import base64 as b
    der = b.b64decode(SERVER_PUB_PEM_BODY)
    i = der.find(bytes.fromhex("0282010181"))
    n_len = 129 if (i >= 0 and der[i + 3] == 0x81) else 128
    n = int.from_bytes(der[i + 4:i + 4 + n_len], "big")
    j = der.find(bytes.fromhex("0203010001"))
    e = int.from_bytes(der[j + 3:j + 5], "big")
    return n, e


_PUB_N, _PUB_E = _pub_modulus()


def qoder_encode(plain):
    std = base64.b64encode(plain).decode()
    b = std.encode()
    n = len(b)
    a = n // 3
    rearranged = b[n - a:] + b[a:n - a] + b[:a]
    out = rearranged.decode("ascii").translate(_TABLE)
    return out.replace("=", _PAD)


def qoder_decode(enc):
    std = enc.replace(_PAD, "=").encode().translate(_RTABLE).decode("ascii")
    b = std.encode()
    n = len(b)
    a = n // 3
    r1, rest = b[:a], b[a:]
    r2, r3 = rest[:n - 2 * a], rest[n - 2 * a:]
    return base64.b64decode(r3 + r2 + r1)


def json_sorted_compact(obj):
    def norm(v):
        if v is None:
            return ""
        if isinstance(v, dict):
            return {k: norm(x) for k, x in v.items()}
        return v
    return json.dumps(norm(obj), ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def strip_algo_prefix(path):
    return path[5:] if path.startswith("/algo") else path


# ---------------- GF(2^8) 工具与纯 Python AES-128（加密方向） ----------------
def _xt(a):
    a <<= 1
    return (a ^ 0x1B) & 0xFF if a & 0x100 else a


def _gmul(a, b):
    r = 0
    for _ in range(8):
        if b & 1:
            r ^= a
        a = _xt(a)
        b >>= 1
    return r


def _gen_sbox():
    # 标准 AES S-box：乘法逆元 + 仿射变换
    sbox = [0] * 256
    for i in range(256):
        inv = 0
        if i:
            for j in range(1, 256):
                if _gmul(i, j) == 1:
                    inv = j
                    break
        x = inv
        s = x ^ ((x << 1) | (x >> 7)) ^ ((x << 2) | (x >> 6)) ^ \
            ((x << 3) | (x >> 5)) ^ ((x << 4) | (x >> 4))
        sbox[i] = (s & 0xFF) ^ 0x63
    return sbox


_SBOX = _gen_sbox()
_RCON = [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36]


def _expand(key):
    w = [list(key[4 * i:4 * i + 4]) for i in range(4)]
    for i in range(4, 44):
        t = w[i - 1][:]
        if i % 4 == 0:
            t = [_SBOX[t[1]], _SBOX[t[2]], _SBOX[t[3]], _SBOX[t[0]]]
            t[0] ^= _RCON[i // 4 - 1]
        w.append([a ^ b for a, b in zip(w[i - 4], t)])
    return w


def _shift_rows(s):
    # 列主序：state[r][c] = s[4*c + r]；第 r 行左移 r
    out = list(s)
    for r in range(1, 4):
        for c in range(4):
            out[4 * c + r] = s[4 * ((c + r) % 4) + r]
    return out


def _mix_columns(s):
    out = list(s)
    for c in range(4):
        a, b, cc, d = s[4 * c:4 * c + 4]
        out[4 * c + 0] = _gmul(a, 2) ^ _gmul(b, 3) ^ cc ^ d
        out[4 * c + 1] = a ^ _gmul(b, 2) ^ _gmul(cc, 3) ^ d
        out[4 * c + 2] = a ^ b ^ _gmul(cc, 2) ^ _gmul(d, 3)
        out[4 * c + 3] = _gmul(a, 3) ^ b ^ cc ^ _gmul(d, 2)
    return out


def _ark(s, w, off):
    round_key = []
    for c in range(4):
        round_key.extend(w[off + c])
    return [x ^ y for x, y in zip(s, round_key)]


def _pad_pkcs7(data):
    n = 16 - len(data) % 16
    return data + bytes([n]) * n


def _aes_encrypt_block(block, w):
    s = _ark(list(block), w, 0)
    for rnd in range(1, 10):
        s = [_SBOX[x] for x in s]
        s = _shift_rows(s)
        s = _mix_columns(s)
        s = _ark(s, w, rnd * 4)
    s = [_SBOX[x] for x in s]
    s = _shift_rows(s)
    s = _ark(s, w, 40)
    return bytes(s)


def aes_cbc_encrypt(data, key, iv):
    w = _expand(key)
    data = _pad_pkcs7(data)
    out = b""
    prev = iv
    for i in range(0, len(data), 16):
        block = bytes(x ^ y for x, y in zip(data[i:i + 16], prev))
        enc = _aes_encrypt_block(block, w)
        out += enc
        prev = enc
    return out


# ---------------- COSY 会话与签名 ----------------
COSY_VERSION = "1.1.64"
DEFAULT_USER_TYPE = "personal_professional_trial"
COSY_CLIENT_IP = "169.254.198.161"


def derive_id(uid, salt):
    # MD5("{salt}:{uid}")，32 位十六进制（与官方客户端同构，盐在前）
    return hashlib.md5((salt + ":" + uid).encode()).hexdigest()


def machine_identity(uid):
    digest = hashlib.sha512(("machinetoken:" + uid).encode()).digest()
    machine_token = base64.urlsafe_b64encode(digest).decode().rstrip("=")[:43]
    return {"machine_id": derive_id(uid, "machine"),
            "machine_token": machine_token,
            "machine_type": derive_id(uid, "machinetype")[:18],
            "session_id": derive_id(uid, "session")}


def rsa_pkcs1v15_encrypt(plain):
    # PKCS#1 v1.5 type 2（随机非零填充）；纯 Python，pow() 完成 RSA 运算
    n_len = (_PUB_N.bit_length() + 7) // 8
    ps_len = n_len - len(plain) - 3
    ps = b""
    while len(ps) < ps_len:
        ps += bytes(b for b in secrets.token_bytes(ps_len) if b)
    ps = ps[:ps_len]
    k = int.from_bytes(b"\x00\x02" + ps + b"\x00" + plain, "big")
    return pow(k, _PUB_E, _PUB_N).to_bytes(n_len, "big")


def signature(payload_b64, cosy_key, date, body, path):
    # 五行 md5：payload \n cosyKey \n date \n body \n path（path 先剥 /algo 前缀）
    raw = chr(10).join([payload_b64, cosy_key, date, body, strip_algo_prefix(path)])
    return hashlib.md5(raw.encode()).hexdigest()


def new_session(uid, nickname, access_token, refresh_token, org_id="", org_name="", user_type=None):
    # temp_key = UUIDv4 hex 前 16 字节（协议对齐，不要换随机字节）
    temp_key = uuid.uuid4().hex[:16].encode()
    cosy_key = base64.b64encode(rsa_pkcs1v15_encrypt(temp_key)).decode()
    identity_json = {"name": nickname, "aid": uid, "uid": uid, "yx_uid": "",
                     "organization_id": org_id, "organization_name": org_name,
                     "user_type": user_type or DEFAULT_USER_TYPE,
                     "security_oauth_token": access_token,
                     "refresh_token": refresh_token}
    plain = json_sorted_compact(identity_json)
    info = base64.b64encode(aes_cbc_encrypt(plain, temp_key, temp_key)).decode()
    mid = machine_identity(uid)
    return {"uid": uid, "machine_id": mid["machine_id"], "machine_token": mid["machine_token"],
            "machine_type": mid["machine_type"], "cosy_key": cosy_key, "info": info}


def bearer(session, body, raw_path):
    payload = {"cosyVersion": COSY_VERSION, "ideVersion": "", "info": session["info"],
               "requestId": str(uuid.uuid4()), "version": "v1"}
    payload_b64 = base64.b64encode(json_sorted_compact(payload)).decode()
    date = str(int(time.time()))
    sig = signature(payload_b64, session["cosy_key"], date, body, raw_path)
    return payload_b64, date, "Bearer COSY." + payload_b64 + "." + sig


def headers(session, body, raw_path, sse=False, model_key=None):
    _payload, date, auth = bearer(session, body, raw_path)
    hs = [("cosy-data-policy", "AGREE"),
          ("content-type", "application/json"),
          ("cosy-machinetype", session["machine_type"]),
          ("cosy-clienttype", "5"),
          ("cosy-date", date),
          ("cosy-user", session["uid"]),
          ("cosy-key", session["cosy_key"]),
          ("accept", "text/event-stream" if sse else "application/json"),
          ("cosy-clientip", COSY_CLIENT_IP),
          ("authorization", auth),
          ("accept-encoding", "identity"),
          ("cosy-version", COSY_VERSION),
          ("cosy-machineid", session["machine_id"]),
          ("cosy-machinetoken", session["machine_token"]),
          ("login-version", "v2"),
          ("user-agent", "Go-http-client/2.0")]
    if sse:
        hs.append(("cache-control", "no-cache"))
    if model_key:
        hs.append(("x-model-key", model_key))
        hs.append(("x-model-source", "system"))
    return hs
