#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# WorkBuddy 每日签到（仅国内版）。
# 接口与字段来自 NextAgentX/qoder-trae-workbuddy-switch 的 checkin.rs 实测：
#   base = https://www.codebuddy.cn ，前缀 /v2/billing/meter
#   状态 checkin-activity-status（失败回退 checkin-status）、签到 daily-checkin，均为 POST
#   认证 Authorization: Bearer <token> + X-User-Id: <uid>
import json, urllib.request

CN_BASE = "https://www.codebuddy.cn"
API = "/v2/billing/meter"
TIMEOUT = 15


def _post(path, token, uid="", ent=""):
    url = CN_BASE + API + "/" + path
    req = urllib.request.Request(url, data=b"{}", method="POST")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Accept", "application/json")
    req.add_header("Content-Type", "application/json")
    if uid:
        req.add_header("X-User-Id", uid)
    if ent:
        req.add_header("X-Enterprise-Id", ent)
        req.add_header("X-Tenant-Id", ent)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def _pick(data, *names):
    for n in names:
        if n in data:
            return data[n]
    return None


def status(token, uid="", ent=""):
    """查询今日签到状态与积分。"""
    last = "未知错误"
    for path in ("checkin-activity-status", "checkin-status"):
        try:
            d = _post(path, token, uid, ent)
        except Exception as e:
            last = str(e)
            continue
        code = d.get("code")
        if code in (0, 200):
            data = d.get("data") or {}
            return {"ok": True, "endpoint": path,
                    "today": bool(_pick(data, "today_checked_in", "todayCheckedIn")),
                    "daily_credit": _pick(data, "daily_credit"),
                    "today_credit": _pick(data, "today_credit"),
                    "total_credits": _pick(data, "total_credits"),
                    "streak_days": _pick(data, "streak_days"),
                    "streak_bonus": _pick(data, "streak_bonus_credit"),
                    "dates": _pick(data, "checkin_dates")}
        last = d.get("message") or d.get("msg") or ("code=" + str(code))
    return {"ok": False, "error": last}


def do_checkin(token, uid="", ent=""):
    """执行签到；服务端提示已签到时按成功处理。"""
    try:
        d = _post("daily-checkin", token, uid, ent)
    except Exception as e:
        return {"ok": False, "error": str(e)}
    if d.get("code") in (0, 200):
        return {"ok": True, "data": d.get("data") or {}}
    msg = d.get("message") or d.get("msg") or ("code=" + str(d.get("code")))
    if "已签到" in msg or "repeat" in str(msg).lower():
        return {"ok": True, "already": True, "message": msg}
    return {"ok": False, "error": msg}


def from_config(cfg):
    """从 config.json 的 checkin 段取 token / uid / enterprise_id。"""
    c = (cfg or {}).get("checkin") or {}
    return (c.get("token") or "").strip(), (c.get("uid") or "").strip(), (c.get("enterprise_id") or "").strip()


def describe(st):
    """把状态结果压成一行中文。"""
    if not st.get("ok"):
        return "查询失败：" + str(st.get("error"))
    parts = ["今日" + ("已签到" if st["today"] else "未签到")]
    if st.get("streak_days") is not None:
        parts.append("连续 %s 天" % st["streak_days"])
    if st.get("daily_credit") is not None:
        parts.append("单日 %s" % st["daily_credit"])
    if st.get("total_credits") is not None:
        parts.append("累计 %s" % st["total_credits"])
    return "，".join(parts)
