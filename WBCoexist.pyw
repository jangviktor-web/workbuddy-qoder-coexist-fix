#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 双版共存管家 v1.1 - 主程序（WorkBuddy / Qoder 各自的国内版与国际版）
# 双击启动 GUI；--daemon 无窗口后台守护；--selftest 自检
# 无窗口 CLI：--qoder-check / --qoder-fix / --qoder-clean
import sys, os, time, json, threading, queue
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wbcore as C
import qoder as Q

BG = "#f4f6f9"
CARD = "#ffffff"
TXT = "#1f2937"
SUB = "#6b7280"
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#ea580c"
BLUE = "#2563eb"
LINE = "#e5e7eb"

def _diff_state(old, cur):
    """返回「旧有且值变了」的键；首次见到的键不算变化，消失的键也不算。"""
    return [k for k in cur if old.get(k) and old.get(k) != cur[k]]


def _watch_installs():
    """检测程序文件是否刚被替换（安装/更新完成），返回变化的键列表。"""
    try:
        c = C.cfg_load()
        st = c.get("state") or {}
        cur = {}
        for t in ("CN", "AI"):
            p = C.exe_path(t)
            if p and os.path.isfile(p):
                try:
                    cur["wb-" + t] = str(int(os.path.getmtime(p)))
                except OSError:
                    pass
        try:
            qr = Q.check()
            for k in ("intl", "cn"):
                p = qr[k].get("exe")
                if p and os.path.isfile(p):
                    try:
                        cur["q-" + k] = str(int(os.path.getmtime(p)))
                    except OSError:
                        pass
        except Exception:
            pass
        changed = _diff_state(st, cur)
        if st != cur:
            c["state"] = cur
            C.cfg_save(c)
        return changed
    except Exception:
        return []

def accounts_cli(move=False):
    import accounts as A
    out = []
    if move:
        argv = sys.argv[1:]
        pos = [x for x in argv if not x.startswith("--")]
        if len(pos) < 2:
            out.append("用法: --move-sessions <源账号> <目标账号> [--apply]")
        else:
            f, t = A.resolve(pos[0]), A.resolve(pos[1])
            if not f or not t:
                out.append("账号无法解析: " + " / ".join(pos[:2]))
            elif f == t:
                out.append("源账号与目标账号相同")
            else:
                A.move(f, t, apply=("--apply" in argv), on_log=out.append)
    else:
        r = A.accounts()
        if not r["ok"]:
            out.append("错误: " + r["error"])
        else:
            out.append("数据库: " + r["db"])
            out.append("账号数: " + str(len(r["accounts"])))
            for a in r["accounts"]:
                out.append("  " + a["short"] + "  " + str(a["sessions"]) + " 条会话  " + a["user_id"])
            out.append("")
            out.append("迁移用法（先完全退出 WorkBuddy）:")
            out.append("  WBCoexist.exe --move-sessions <源账号前8位> <目标账号前8位> --apply")
    text = chr(10).join(out)
    try:
        print(text)
    except Exception:
        pass
    try:
        with open(os.path.join(C.ROOT, "accounts.txt"), "w", encoding="utf-8") as fh:
            fh.write(text + chr(10))
    except Exception:
        pass

def checkin_cli(do=False):
    import checkin as K
    import wbtoken as T
    out = []
    toks = T.fetch_tokens()
    if not toks:
        out.append("未发现可用 token（WorkDaddy 备份不可读，config.json 也未填）")
    for t in toks:
        st = K.status(t["token"], t["uid"], base=t["domain"])
        out.append(t["uid"][:8] + "  " + t.get("domain", "") + "  " + K.describe(st))
        if do and st.get("ok") and not st.get("today"):
            res = K.do_checkin(t["token"], t["uid"], base=t["domain"])
            ok = res.get("ok")
            out.append("    签到: " + ("成功" if ok else ("失败 " + str(res.get("error")))))
            if res.get("already"):
                out.append("    （服务端提示今日已签到）")
    text = chr(10).join(out)
    try:
        print(text)
    except Exception:
        pass
    try:
        with open(os.path.join(C.ROOT, "checkin.txt"), "w", encoding="utf-8") as fh:
            fh.write(text + chr(10))
    except Exception:
        pass

def daemon_main():
    C.log("后台守护已启动（WorkBuddy + Qoder）")
    while True:
        try:
            c = C.cfg_load()
            ch = _watch_installs()
            if ch:
                try:
                    C.fix(C.check(c["primary"]), c["primary"], apply=True)
                    Q.daemon_tick()
                    C.log("检测到安装/更新完成：" + ", ".join(ch) + "，已自动全量修复")
                except Exception as e:
                    C.log("安装后自动修复失败: " + str(e))
            msg = C.daemon_tick(c)
            if msg:
                C.log(msg)
            qm = Q.daemon_tick()
            if qm:
                C.log(qm)
        except Exception as e:
            C.log("守护异常: " + str(e))
        time.sleep(8)

def selftest():
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        c = C.cfg_load()
        r = C.check(c["primary"])
        print("CONFIG:", json.dumps(c, ensure_ascii=False))
        print("CHECK:", json.dumps(r, ensure_ascii=False))
        print("FIX_PREVIEW:", C.fix(r, c["primary"], apply=False))
        print("DAEMON_TICK:", C.daemon_tick(c) or "无动作")
        print("AUTOSTART:", C.autostart_get())
        qr = Q.check()
        print("QODER_CHECK:", json.dumps(qr, ensure_ascii=False))
        print("QODER_FIX_PREVIEW:", Q.fix(qr, apply=False))
        print("QODER_DAEMON_TICK:", Q.daemon_tick() or "无动作")
        print("QODER_ORPHANS:", json.dumps(qr["orphans"], ensure_ascii=False))
    out = buf.getvalue()
    try:
        open(os.path.join(C.ROOT, "selftest.txt"), "w", encoding="utf-8").write(out)
    except Exception:
        pass
    try:
        sys.stdout.write(out)
    except Exception:
        pass

def qoder_cli(mode):
    qr = Q.check()
    out = []
    if mode == "check":
        out.append(json.dumps(qr, ensure_ascii=False, indent=2))
    elif mode == "fix":
        for a in Q.fix(qr, apply=True):
            out.append("[FIX] " + a)
        out.append("ISSUES_AFTER: " + str(len(Q.check()["issues"])))
    elif mode == "clean":
        for a in Q.clean(qr):
            out.append("[CLEAN] " + a)
    text = chr(10).join(out)
    try:
        open(os.path.join(C.ROOT, "qoder-cli.txt"), "w", encoding="utf-8").write(text)
    except Exception:
        pass
    try:
        sys.stdout.write(text + chr(10))
    except Exception:
        pass

def gui_main():
    import tkinter as tk
    from tkinter import scrolledtext, messagebox, simpledialog
    root = tk.Tk()
    root.title("双版共存管家  v1.1")
    root.geometry("720x800")
    root.resizable(False, False)
    root.configure(bg=BG)
    cfg = C.cfg_load()
    q = queue.Queue()

    def add_log(s):
        for line in str(s).split(chr(10)):
            if line.strip():
                q.put(C.log(line))

    def lamp(parent, text):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", padx=14, pady=3)
        d = tk.Canvas(row, width=12, height=12, bg=CARD, highlightthickness=0)
        d.pack(side="left", padx=(2, 8))
        dot = d.create_oval(2, 2, 10, 10, fill=SUB, outline="")
        lb = tk.Label(row, text=text, bg=CARD, fg=TXT, font=("Microsoft YaHei", 10), anchor="w")
        lb.pack(side="left", fill="x", expand=True)
        return d, dot, lb

    def set_lamp(w, ok, note):
        d, dot, lb = w
        d.itemconfig(dot, fill=GREEN if ok else RED)
        lb.config(text=note, fg=TXT if ok else RED)

    def refresh():
        c = C.cfg_load()
        r = C.check(c["primary"])
        qr = Q.check()
        for t in ("CN", "AI"):
            a = r["apps"][t]
            bad = [k for k in ("exe", "reg", "lnk", "data") if not a[k]]
            set_lamp(lamps[t], not bad,
                     ("CN 版 5.9.3" if t == "CN" else "AI 国际版 5.9.4") +
                     "   " + ("正常" if not bad else "异常: " + ",".join(bad)) +
                     ("   [运行中]" if a["running"] else "   [未运行]"))
        set_lamp(lamps["scheme"], r["owner"] == c["primary"],
                 "buddy-app://  归属 " + r["owner"] + "（约定 " + c["primary"] + "）")
        set_lamp(lamps["cache"], not r["cache"],
                 "更新器缓存  " + ("干净" if not r["cache"] else
                                  "有 " + str(r["cache_size"] // 1048576) + " MB 陈旧安装包"))
        qi = qr["intl"]
        qc = qr["cn"]
        set_lamp(lamps["qintl"], bool(qi["exe"] and qi["hash"]),
                 Q.qoder_line(qi) + ("" if qi["hash"] else "   缺启动器"))
        set_lamp(lamps["qcn"], bool(qc["exe"] and qc["hash"]),
                 Q.qoder_line(qc) + ("" if qc["hash"] else "   缺启动器"))
        m = qr["manifest"]
        exp = qr["expected"]
        conn_ok = bool(m["valid"] and exp["hash"] and
                       (m["host_hash"] or "") == exp["hash"].lower() and m["origins_ok"])
        note = "共享连接器 → " + (exp["hash"][:12] if exp["hash"] else "?") + \
               ("（" + exp["source"] + "）" if exp["source"] else "")
        if not m["exists"]:
            note += "   manifest 缺失"
        elif not m["valid"]:
            note += "   manifest 损坏"
        elif not m["origins_ok"]:
            note += "   缺少扩展来源"
        set_lamp(lamps["qconn"], conn_ok, note)
        reg = qr["registry"]
        set_lamp(lamps["qreg"], reg["chrome_ok"] and reg["edge_ok"],
                 "native messaging  Chrome " + ("OK" if reg["chrome_ok"] else "异常") +
                 " / Edge " + ("OK" if reg["edge_ok"] else "异常"))
        n = len(r["issues"]) + len(qr["issues"])
        w = len(qr["warnings"])
        text = "体检结果：" + ("全部正常，无需处理" if n == 0 else str(n) + " 项待处理")
        if w:
            text += "；" + str(w) + " 条提示"
        summary.config(text=text, fg=GREEN if n == 0 else ORANGE)
        return r, qr

    def on_fix():
        c = C.cfg_load()
        r = C.check(c["primary"])
        acts = C.fix(r, c["primary"], apply=True)
        for a in acts:
            add_log("[WorkBuddy 修复] " + a)
        try:
            qacts = Q.fix(Q.check(), apply=True)
        except Exception as e:
            qacts = ["Qoder 修复异常: " + str(e)]
        for a in qacts:
            add_log("[Qoder 修复] " + a)
        add_log("--- 修复完成，正在复检 ---")
        refresh()
        allacts = acts + qacts
        messagebox.showinfo("完成", "一键修复已完成" + chr(10) + chr(10) + chr(10).join(allacts))

    def on_migrate():
        import migrate as M
        r = M.scan()
        cand = [it for it in r["items"] if it["kind"] in ("app", "data") and not it["migrated"]]
        if not cand:
            messagebox.showinfo("迁移", "没有可迁移的项。" + chr(10) + "若数据目录已是指向其他盘的联接，则无需再迁。")
            return
        win = tk.Toplevel(root)
        win.title("无损迁移到其他磁盘")
        win.geometry("760x560")
        win.configure(bg=BG)
        tk.Label(win, text="勾选要迁移的项（路径均来自实测：注册表 / product.json / 特征文件）",
                 bg=BG, fg=SUB, font=("Microsoft YaHei", 9)).pack(anchor="w", padx=16, pady=(12, 4))
        box = tk.Frame(win, bg=BG)
        box.pack(fill="x", padx=16)
        vars_ = []
        for it in cand:
            v = tk.IntVar(value=0)
            tk.Checkbutton(box, text="[" + it["kind"] + "] " + it["product"] + "   " + it["path"],
                           variable=v, bg=BG, anchor="w",
                           font=("Microsoft YaHei", 9)).pack(fill="x")
            vars_.append((it, v))
        drives = [d + ":" + chr(92) for d in "CDEFGHIJ" if os.path.exists(d + ":" + chr(92))]
        dv = tk.StringVar(value=drives[-1] if drives else "")
        row = tk.Frame(win, bg=BG)
        row.pack(fill="x", padx=16, pady=10)
        tk.Label(row, text="目标根目录", bg=BG, fg=SUB,
                 font=("Microsoft YaHei", 9)).pack(side="left")
        tk.Entry(row, textvariable=dv, width=24, font=("Consolas", 10)).pack(side="left", padx=6)
        tk.Label(row, text="（如 E:/MyData）", bg=BG, fg=SUB,
                 font=("Microsoft YaHei", 8)).pack(side="left")
        tip = "流程：复制 → 校验文件数 → 原目录改名 .bak → 建立目录联接 → 写入探针验证。"
        tip2 = "不会删除任何文件；失败自动回滚；.bak 保留，确认无误后可自行清理。"
        tk.Label(win, text=tip + chr(10) + tip2, bg=BG, fg=SUB, justify="left",
                 font=("Microsoft YaHei", 9)).pack(anchor="w", padx=16, pady=(0, 8))

        def run():
            keys = [it["key"] for it, v in vars_ if v.get()]
            if not keys:
                messagebox.showwarning("迁移", "请先勾选至少一项")
                return
            plans = M.plan(keys, dv.get())
            ok, lines = M.precheck(plans)
            for lv, m in lines:
                add_log("[迁移检查] " + ("[!] " if lv == "error" else "") + m)
            if not ok:
                messagebox.showerror("迁移", "前置检查未通过，已停止。详见日志区。")
                return
            ask = "将迁移 " + str(len(plans)) + " 项到 " + dv.get() + chr(10) + chr(10) + "不会删除文件；原目录改名 .bak 保留。"
            if not messagebox.askyesno("确认迁移", ask):
                return
            win.destroy()

            def worker():
                done = 0
                for p in plans:
                    try:
                        if M.migrate_one(p, apply=True, on_log=add_log):
                            done += 1
                    except Exception as e:
                        add_log("[迁移] 异常: " + str(e))
                add_log("[迁移] 完成 " + str(done) + "/" + str(len(plans)) + " 项")
                q.put("[refresh]")

            threading.Thread(target=worker, daemon=True).start()

        btnrow = tk.Frame(win, bg=BG)
        btnrow.pack(fill="x", padx=16)
        tk.Button(btnrow, text="开始迁移", command=run, bg=BLUE, fg="#ffffff",
                  font=("Microsoft YaHei", 10, "bold"), height=2, relief="flat",
                  cursor="hand2").pack(side="left", fill="x", expand=True)

    def on_accounts():
        import accounts as A, checkin as K
        c = C.cfg_load()
        token, uid, ent = K.from_config(c)
        r = A.accounts()
        if not r["ok"]:
            add_log("[账号] " + r["error"])
            messagebox.showwarning("账号会话", r["error"])
            return
        add_log("[账号] 数据库: " + r["db"])
        lines = []
        for a in r["accounts"]:
            add_log("[账号] " + a["short"] + "  " + str(a["sessions"]) + " 条会话")
            lines.append(a["short"] + "   " + str(a["sessions"]) + " 条会话")
        # 签到（自动发现 token：WorkDaddy 备份 + config 手填）
        try:
            import wbtoken as T
            toks = T.fetch_tokens()
        except Exception:
            toks = []
        if toks:
            lines.append("")
            need = []
            for t in toks:
                try:
                    st = K.status(t["token"], t["uid"], base=t["domain"])
                except Exception as e:
                    st = {"ok": False, "error": str(e)[:60]}
                desc = K.describe(st)
                add_log("[签到] " + t["uid"][:8] + "  " + t["domain"] + "  " + desc)
                lines.append("签到 " + t["uid"][:8] + "：" + desc)
                if st.get("ok") and not st.get("today"):
                    need.append(t)
            if need:
                if messagebox.askyesno("签到", "有 " + str(len(need)) + " 个账号今日未签到，现在签到？"):
                    for t in need:
                        res = K.do_checkin(t["token"], t["uid"], base=t["domain"])
                        msg = "成功" if res.get("ok") else ("失败：" + str(res.get("error")))
                        if res.get("already"):
                            msg = "服务端提示今日已签到"
                        add_log("[签到] " + t["uid"][:8] + "  " + msg)
        else:
            lines.append("")
            how = ("自动获取未成功（需 WorkDaddy 账号备份，或装着 WorkBuddy）。" + chr(10) +
                   "也可手动：WorkBuddy 里 F12 → Network → codebuddy.cn 请求 →" + chr(10) +
                   "复制 Authorization（Bearer 后面那串）与 x-user-id 填入 config.json")
            lines.append("签到：未发现 token")
            if messagebox.askyesno("签到", "未发现 token。手动填写？" + chr(10) + chr(10) + how):
                t = simpledialog.askstring("签到 token", "粘贴 Bearer 后面的那串：", show="*")
                u = simpledialog.askstring("签到账号", "粘贴 x-user-id（可留空）：")
                if t:
                    c.setdefault("checkin", {})
                    c["checkin"]["token"] = t.strip()
                    c["checkin"]["uid"] = (u or "").strip()
                    C.cfg_save(c)
                    add_log("[签到] token 已保存到 config.json")
        tip = "迁移需先完全退出 WorkBuddy，再运行命令行（运行时数据库被占用）"
        add_log("[账号] " + tip)
        add_log("[账号] 用法: WBCoexist.exe --move-sessions <源> <目标> --apply")
        messagebox.showinfo("账号会话", chr(10).join(lines) + chr(10) + chr(10) + tip)

    def on_scan():
        ws = C.installed()
        qs = Q.installed()
        add_log("===== 已安装检测 =====")
        add_log("WorkBuddy：" + ("未检测到安装" if not ws else str(len(ws)) + " 项"))
        for it in ws:
            add_log("  " + it["tag"] + "  v" + (it["version"] or "?") + "  " + it["exe"] +
                    ("  [运行中]" if it["running"] else ""))
        add_log("Qoder：" + ("未检测到安装" if not qs else str(len(qs)) + " 项"))
        for it in qs:
            add_log("  " + it["name"] + "  v" + (it["version"] or "?") + "  " + it["exe"] +
                    ("  [在用]" if it["active"] else "  [历史]"))
        messagebox.showinfo("已安装检测",
                            "WorkBuddy " + str(len(ws)) + " 项 / Qoder " + str(len(qs)) + " 项" +
                            chr(10) + "明细见日志区")

    def on_clean():
        qr = Q.check()
        orph = qr["orphans"]
        dead = [x for x in qr["clients"] if (not x["alive"]) and x["pid"]]
        if not orph and not dead:
            add_log("[清理] 没有孤儿 host 副本或失效中继记录")
            messagebox.showinfo("清理", "没有需要清理的项目")
            return
        msg = "将删除：" + chr(10) + \
              "  孤儿 host 副本 " + str(len(orph)) + " 个" + chr(10) + \
              "  失效中继记录 " + str(len(dead)) + " 条" + chr(10) + chr(10) + "继续吗？"
        if not messagebox.askyesno("确认清理", msg):
            add_log("[清理] 已取消")
            return
        for a in Q.clean(qr):
            add_log("[清理] " + a)
        refresh()

    def on_prep():
        pr = C.preflight()
        qp = Q.preflight()
        add_log("===== 安装前检查：WorkBuddy =====")
        for lv, txt in pr["lines"]:
            add_log(("  [注意] " if lv == "warn" else "  - ") + txt)
        add_log("===== 安装前检查：Qoder =====")
        for lv, txt in qp["lines"]:
            add_log(("  [注意] " if lv == "warn" else "  - ") + txt)
        ok = pr["ok"] and qp["ok"]
        add_log("===== 结论：" + ("可以开始安装" if ok else "建议先处理上面的 [注意] 项再安装") + " =====")
        refresh()
        messagebox.showinfo("安装前检查",
                            ("可以开始安装。" if ok else "建议先处理注意事项。") + chr(10) + chr(10) +
                            "详细结果见日志区。")

    def on_primary():
        c = C.cfg_load()
        c["primary"] = primary_var.get()
        C.cfg_save(c)
        add_log("buddy-app 约定归属改为 " + c["primary"])
        refresh()

    def on_guard():
        c = C.cfg_load()
        c["guard"] = bool(guard_var.get())
        C.cfg_save(c)
        add_log("后台守护（本窗口内）" + ("已开启，每 8 秒自动修回" if c["guard"] else "已关闭"))

    def on_autostart():
        c = C.cfg_load()
        on = bool(auto_var.get())
        ok = C.autostart_set(on)
        c["autostart"] = on
        C.cfg_save(c)
        add_log("开机自启后台守护 " + ("已开启" if on else "已关闭") + ("  [OK]" if ok else "  [失败]"))

    head = tk.Frame(root, bg=BLUE, height=64)
    head.pack(fill="x")
    head.pack_propagate(False)
    tk.Label(head, text="双版共存管家", bg=BLUE, fg="#ffffff",
             font=("Microsoft YaHei", 16, "bold")).pack(side="left", padx=18)
    tk.Label(head, text="CN / AI 双版本 · 国内 / 国际版 · 更新冲突一键处理", bg=BLUE, fg="#dbeafe",
             font=("Microsoft YaHei", 9)).pack(side="left", padx=4, pady=(6, 0))

    card = tk.Frame(root, bg=CARD, highlightbackground=LINE, highlightthickness=1)
    card.pack(fill="x", padx=16, pady=(12, 8))

    tk.Label(card, text="WorkBuddy 状态", bg=CARD, fg=SUB,
             font=("Microsoft YaHei", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 2))
    lamps = {"CN": lamp(card, ""), "AI": lamp(card, ""),
             "scheme": lamp(card, ""), "cache": lamp(card, "")}

    tk.Frame(card, bg=LINE, height=1).pack(fill="x", padx=14, pady=(8, 0))
    tk.Label(card, text="Qoder 状态", bg=CARD, fg=SUB,
             font=("Microsoft YaHei", 9, "bold")).pack(anchor="w", padx=14, pady=(8, 2))
    lamps["qintl"] = lamp(card, "")
    lamps["qcn"] = lamp(card, "")
    lamps["qconn"] = lamp(card, "")
    lamps["qreg"] = lamp(card, "")
    summary = tk.Label(card, text="", bg=CARD, fg=SUB, font=("Microsoft YaHei", 9))
    summary.pack(anchor="w", padx=14, pady=(8, 10))

    opt = tk.Frame(root, bg=BG)
    opt.pack(fill="x", padx=16)
    primary_var = tk.StringVar(value=cfg["primary"])
    tk.Label(opt, text="buddy-app 归属", bg=BG, fg=SUB,
             font=("Microsoft YaHei", 9)).pack(side="left")
    tk.Radiobutton(opt, text="CN 版", variable=primary_var, value="CN", bg=BG,
                   font=("Microsoft YaHei", 9), command=on_primary).pack(side="left", padx=(6, 0))
    tk.Radiobutton(opt, text="AI 国际版", variable=primary_var, value="AI", bg=BG,
                   font=("Microsoft YaHei", 9), command=on_primary).pack(side="left")
    guard_var = tk.IntVar(value=int(cfg["guard"]))
    tk.Checkbutton(opt, text="后台守护", variable=guard_var, bg=BG,
                   font=("Microsoft YaHei", 9), command=on_guard).pack(side="left", padx=(14, 0))
    auto_var = tk.IntVar(value=int(C.autostart_get()))
    tk.Checkbutton(opt, text="开机自启", variable=auto_var, bg=BG,
                   font=("Microsoft YaHei", 9), command=on_autostart).pack(side="left")

    btns = tk.Frame(root, bg=BG)
    btns.pack(fill="x", padx=16, pady=10)
    tk.Button(btns, text="一 键 修 复", command=on_fix, bg=BLUE, fg="#ffffff",
              activebackground="#1d4ed8", font=("Microsoft YaHei", 12, "bold"),
              height=2, relief="flat", cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 6))
    tk.Button(btns, text="体 检", command=lambda: (add_log("手动体检"), refresh()),
              bg="#e5e7eb", font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)
    tk.Button(btns, text="安装前", command=on_prep, bg="#e5e7eb",
              font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)
    tk.Button(btns, text="清孤儿", command=on_clean, bg="#e5e7eb",
              font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)
    tk.Button(btns, text="已装", command=on_scan, bg="#e5e7eb",
              font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)
    tk.Button(btns, text="迁 移", command=on_migrate, bg="#e5e7eb",
              font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)
    tk.Button(btns, text="账号", command=on_accounts, bg="#e5e7eb",
              font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)

    logbox = scrolledtext.ScrolledText(root, height=9, bg="#111827", fg="#d1fae5",
                                       font=("Consolas", 9), relief="flat")
    logbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    add_log("双版共存管家已启动；点「一键修复」处理更新导致的冲突")
    add_log("WorkBuddy：修 buddy-app 归属 + 归档陈旧更新缓存")
    add_log("Qoder：修共享 browser-connector（manifest / host 代际 / Chrome·Edge 注册）")
    add_log("勾选「后台守护」后，每 8 秒自动修回被抢占的归属")

    def guard_loop():
        while True:
            c = C.cfg_load()
            if c.get("guard"):
                ch = _watch_installs()
                if ch:
                    try:
                        C.fix(C.check(c["primary"]), c["primary"], apply=True)
                        Q.daemon_tick()
                        q.put(C.log("[守护] 检测到安装/更新完成：" + ", ".join(ch) + "，已自动全量修复"))
                        q.put("[refresh]")
                    except Exception as e:
                        q.put(C.log("[守护] 安装后自动修复失败: " + str(e)))
                m = C.daemon_tick(c)
                if m:
                    q.put(C.log("[守护] " + m))
                    q.put("[refresh]")
                qm = Q.daemon_tick()
                if qm:
                    q.put(C.log("[守护] " + qm))
                    q.put("[refresh]")
            time.sleep(8)

    def drain():
        try:
            while True:
                s = q.get_nowait()
                if s == "[refresh]":
                    refresh()
                else:
                    logbox.insert(tk.END, s + chr(10))
                    logbox.see(tk.END)
        except queue.Empty:
            pass
        root.after(200, drain)

    threading.Thread(target=guard_loop, daemon=True).start()
    refresh()
    drain()
    if "--smoke" in sys.argv:
        root.after(600, root.destroy)
    root.mainloop()

def main():
    if "--daemon" in sys.argv:
        daemon_main()
    elif "--selftest" in sys.argv:
        selftest()
    elif "--qoder-check" in sys.argv:
        qoder_cli("check")
    elif "--qoder-fix" in sys.argv:
        qoder_cli("fix")
    elif "--qoder-clean" in sys.argv:
        qoder_cli("clean")
    elif "--accounts" in sys.argv:
        accounts_cli()
    elif "--move-sessions" in sys.argv:
        accounts_cli(move=True)
    elif "--checkin-status" in sys.argv:
        checkin_cli()
    elif "--checkin" in sys.argv:
        checkin_cli(do=True)
    else:
        gui_main()

if __name__ == "__main__":
    main()
