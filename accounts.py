#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 账号会话归属：WorkBuddy 的会话文件按工作区存（projects/<slug>/<id>.jsonl），
# 账号归属只记录在 <数据根>/workbuddy.db 的 sessions.user_id 字段。
# 因此「跨账号迁移」= 改 sessions.user_id，不需要搬文件。
import os, glob, shutil, sqlite3, datetime

DB_NAME = "workbuddy.db"


def find_db():
    """实测定位 workbuddy.db：从已探测到的 WorkBuddy 数据目录里找，校验表结构。"""
    import migrate as M
    try:
        r = M.scan()
    except Exception:
        r = {"items": []}
    cands = []
    for it in r.get("items", []):
        if it.get("product") == "WorkBuddy" and it.get("kind") == "data":
            cands.append(os.path.join(it["path"], DB_NAME))
    home_db = os.path.join(os.path.expanduser("~"), ".workbuddy", DB_NAME)
    if home_db not in cands:
        cands.append(home_db)
    for p in cands:
        if not os.path.isfile(p):
            continue
        try:
            con = _conn(p, True)
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
            ok = cur.fetchone() is not None
            con.close()
            if ok:
                return p, os.path.dirname(p)
        except Exception:
            continue
    return "", ""


def _conn(path, readonly=True):
    if readonly:
        uri = "file:" + path.replace(chr(92), "/") + "?mode=ro"
        return sqlite3.connect(uri, uri=True, timeout=5)
    return sqlite3.connect(path, timeout=10)


def accounts():
    """返回本机各账号的会话数（只读）。"""
    db, root = find_db()
    if not db:
        return {"ok": False, "error": "未找到 workbuddy.db（WorkBuddy 可能未安装或数据目录未初始化）", "accounts": []}
    out = []
    try:
        con = _conn(db, True)
        cur = con.cursor()
        cur.execute("SELECT user_id, COUNT(*), MAX(updated_at) FROM sessions "
                    "WHERE deleted_at IS NULL GROUP BY user_id ORDER BY 2 DESC")
        for uid, n, mx in cur.fetchall():
            out.append({"user_id": uid or "", "short": (str(uid)[:8] if uid else "(空)"),
                        "sessions": n, "last_at": mx})
        con.close()
    except Exception as e:
        return {"ok": False, "error": "读取失败: " + str(e), "accounts": []}
    return {"ok": True, "db": db, "root": root, "accounts": out}


def sessions_of(uid, limit=50):
    """列出某账号的会话（只读）。"""
    db, _root = find_db()
    if not db:
        return []
    out = []
    try:
        con = _conn(db, True)
        cur = con.cursor()
        cur.execute("SELECT id, title, custom_title, cwd, status, updated_at FROM sessions "
                    "WHERE user_id = ? AND deleted_at IS NULL ORDER BY updated_at DESC LIMIT ?",
                    (uid, limit))
        for sid, t, ct, cwd, st, up in cur.fetchall():
            out.append({"id": sid, "title": ct or t or "(无标题)", "cwd": cwd,
                        "status": st, "updated_at": up})
        con.close()
    except Exception:
        pass
    return out


def preview_move(from_uid, to_uid, limit=20):
    """预览迁移影响（只读）。"""
    db, _root = find_db()
    if not db:
        return {"ok": False, "error": "未找到 workbuddy.db"}
    if not from_uid or not to_uid or from_uid == to_uid:
        return {"ok": False, "error": "源账号与目标账号必须不同"}
    try:
        con = _conn(db, True)
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ? AND deleted_at IS NULL", (from_uid,))
        n_from = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ? AND deleted_at IS NULL", (to_uid,))
        n_to = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ? AND deleted_at IS NOT NULL", (from_uid,))
        n_del = cur.fetchone()[0]
        con.close()
    except Exception as e:
        return {"ok": False, "error": "读取失败: " + str(e)}
    return {"ok": True, "db": db, "from": from_uid, "to": to_uid,
            "count_from": n_from, "count_to": n_to, "deleted": n_del,
            "moving": n_from}


def resolve(short):
    """把短 ID（前 8 位）解析成完整 user_id；也接受完整 ID。"""
    r = accounts()
    if not r["ok"]:
        return ""
    for a in r["accounts"]:
        uid = a["user_id"]
        if uid == short or uid.startswith(short):
            return uid
    return ""


def move(from_uid, to_uid, apply=False, on_log=print):
    """把 from_uid 名下未删除的会话改归属到 to_uid。
    WorkBuddy 运行时数据库被占用，写入会失败——请先完全退出。"""
    db, root = find_db()
    if not db:
        on_log("未找到 workbuddy.db")
        return False
    pv = preview_move(from_uid, to_uid)
    if not pv.get("ok"):
        on_log(pv.get("error", "预览失败"))
        return False
    on_log("数据库: " + db)
    on_log("源账号 " + from_uid[:8] + " 现有 " + str(pv["count_from"]) + " 条未删除会话（另有 "
           + str(pv["deleted"]) + " 条已删除不计入）")
    on_log("目标账号 " + to_uid[:8] + " 现有 " + str(pv["count_to"]) + " 条")
    on_log("将迁移 " + str(pv["moving"]) + " 条：把 sessions.user_id 改为目标账号")
    if not apply:
        on_log("（预演，未改动。加 --apply 执行）")
        return True

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = db + ".bak-" + ts
    try:
        shutil.copy2(db, bak)
    except OSError as e:
        on_log("备份失败，已中止: " + str(e))
        return False
    on_log("已备份数据库 -> " + bak)

    try:
        con = _conn(db, False)
        con.execute("BEGIN IMMEDIATE")
        cur = con.execute("UPDATE sessions SET user_id = ?, updated_at = ? "
                          "WHERE user_id = ? AND deleted_at IS NULL",
                          (to_uid, int(datetime.datetime.now().timestamp() * 1000), from_uid))
        n = cur.rowcount
        con.commit()
        con.close()
    except Exception as e:
        on_log("写入失败（WorkBuddy 可能仍在运行）: " + str(e))
        on_log("数据库未改动；备份保留在 " + bak)
        return False

    chk = preview_move(from_uid, to_uid)
    if chk.get("ok"):
        on_log("完成：源账号剩 " + str(chk["count_from"]) + " 条，目标账号现 " + str(chk["count_to"]) + " 条")
    on_log("实际更新 " + str(n) + " 行；回滚可用: copy /Y \"" + bak + "\" \"" + db + "\"")
    return n > 0
