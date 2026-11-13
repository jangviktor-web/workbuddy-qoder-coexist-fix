#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 双版共存管家 v1.5 - 主程序（WorkBuddy / Qoder 各自的国内版与国际版）
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
    from tkinter import scrolledtext, messagebox, simpledialog, ttk
    root = tk.Tk()
    root.title("双版共存管家  v1.6")
    root.geometry("720x780")
    root.resizable(False, False)
    root.configure(bg=BG)
    cfg = C.cfg_load()
    q = queue.Queue()

    def add_log(s):
        for line in str(s).split(chr(10)):
            if line.strip():
                q.put(C.log(line))

    status_var = tk.StringVar(value="就绪")
    buttons = []
    busy = {"n": 0}

    def set_busy(on, text=None):
        busy["n"] = max(0, busy["n"] + (1 if on else -1))
        now = busy["n"] > 0
        for b in buttons:
            try:
                if hasattr(b, "set_state"):
                    b.set_state("disabled" if now else "normal")
                else:
                    b.config(state="disabled" if now else "normal")
            except Exception:
                pass
        try:
            root.config(cursor="watch" if now else "")
        except Exception:
            pass
        if text is not None:
            status_var.set(text)

    def task(label, fn, done=None):
        # 耗时操作放工作线程；结果回到 Tk 主线程收尾
        set_busy(True, label + "…")
        def work():
            res = err = None
            try:
                res = fn()
            except Exception as e:
                err = e
            def finish():
                set_busy(False, "就绪")
                if err is not None:
                    add_log("[" + label + "] 出错: " + str(err))
                    messagebox.showerror(label, str(err))
                    return
                if done:
                    try:
                        done(res)
                    except Exception as e:
                        add_log("[" + label + "] 收尾出错: " + str(e))
            q.put(finish)
        threading.Thread(target=work, daemon=True).start()

    def manual_token_dialog(title):
        # 自动发现失败时（无 WorkDaddy 备份 / 未装 WorkBuddy）允许手填
        how = ("自动获取未成功（需 WorkDaddy 账号备份，或装着 WorkBuddy）。" + chr(10) +
               "也可手动：WorkBuddy 里 F12 → Network → codebuddy.cn 请求 →" + chr(10) +
               "复制 Authorization（Bearer 后面那串）与 x-user-id")
        if not messagebox.askyesno(title, "未发现可用 token。手动填写？" + chr(10) + chr(10) + how):
            return False
        t = simpledialog.askstring("签到 token", "粘贴 Bearer 后面的那串：", show="*")
        u = simpledialog.askstring("签到账号", "粘贴 x-user-id（可留空）：")
        if not t:
            return False
        c = C.cfg_load()
        c.setdefault("checkin", {})
        c["checkin"]["token"] = t.strip()
        c["checkin"]["uid"] = (u or "").strip()
        C.cfg_save(c)
        add_log("[签到] token 已保存到 config.json")
        return True

    def lamp(parent):
        row = tk.Frame(parent, bg=CARD)
        row.pack(fill="x", pady=2)
        d = tk.Canvas(row, width=10, height=14, bg=CARD, highlightthickness=0)
        d.pack(side="left")
        dot = d.create_oval(1, 4, 9, 12, fill=SUB, outline="")
        lb = tk.Label(row, text="", bg=CARD, fg=TXT, font=("Microsoft YaHei", 9), anchor="w")
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
        sumdot.itemconfig(sumdot_i, fill=GREEN if n == 0 else ORANGE)
        return r, qr

    def on_fix():
        def work():
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
            return acts + qacts

        def done(allacts):
            refresh()
            messagebox.showinfo("完成", "一键修复已完成" + chr(10) + chr(10) + chr(10).join(allacts))

        task("一键修复", work, done)

    def on_migrate():
        import migrate as M
        r = M.scan()
        cand = [it for it in r["items"] if it["kind"] in ("app", "data") and not it["migrated"]]
        if not cand:
            messagebox.showinfo("迁移", "没有可迁移的项。" + chr(10) + "若数据目录已是指向其他盘的联接，则无需再迁。")
            return
        win = tk.Toplevel(root)
        win.title("无损迁移到其他磁盘")
        win.geometry("780x650")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.transient(root)
        state = {"running": False}

        def close():
            if state["running"]:
                messagebox.showwarning("迁移", "迁移正在进行，请等它结束后再关闭。", parent=win)
                return
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", close)

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

        prog = tk.Frame(win, bg=BG)
        prog.pack(fill="x", padx=16)
        state_var = tk.StringVar(value="")
        tk.Label(prog, textvariable=state_var, bg=BG, fg=SUB, anchor="w",
                 font=("Microsoft YaHei", 9)).pack(fill="x")
        bar = ttk.Progressbar(prog, mode="determinate", maximum=1, value=0)
        bar.pack(fill="x", pady=(4, 0))

        step_cn = {"copy": "复制中", "verify": "校验文件数", "rename": "原目录改名",
                   "link": "建立目录联接", "probe": "写入探针验证", "done": "完成"}

        def validate(target, plans):
            t = (target or "").strip().strip('"')
            if not t:
                return "请填写目标根目录（如 E:/MyData）"
            t = os.path.abspath(t)
            drive = os.path.splitdrive(t)[0]
            if not drive or not os.path.isdir(drive + os.sep):
                return "目标盘不存在：" + (drive or t)
            for p in plans:
                sd = os.path.splitdrive(os.path.abspath(p["src"]))[0]
                if sd and sd.lower() == drive.lower():
                    return "目标目录与源目录在同一磁盘（" + drive + "），迁移没有意义"
                sp = os.path.normcase(os.path.abspath(p["src"]))
                tp = os.path.normcase(os.path.abspath(p["dst"]))
                if tp == sp or tp.startswith(sp + os.sep) or sp.startswith(tp + os.sep):
                    return "目标目录不能与源目录互相包含：" + p["src"]
            try:
                os.makedirs(t, exist_ok=True)
                probe = os.path.join(t, ".__wb_write_probe__")
                with open(probe, "w", encoding="utf-8") as fh:
                    fh.write("ok")
                os.remove(probe)
            except OSError as e:
                return "目标目录不可写：" + str(e)
            return ""

        def start():
            keys = [it["key"] for it, v in vars_ if v.get()]
            if not keys:
                messagebox.showwarning("迁移", "请先勾选至少一项", parent=win)
                return
            plans = M.plan(keys, dv.get())
            err = validate(dv.get(), plans)
            if err:
                add_log("[迁移检查] " + err)
                messagebox.showerror("迁移", err, parent=win)
                return
            ok, lines = M.precheck(plans)
            for lv, m in lines:
                add_log("[迁移检查] " + ("[!] " if lv == "error" else "") + m)
            if not ok:
                messagebox.showerror("迁移", "前置检查未通过，已停止。详见日志区。", parent=win)
                return
            ask = ("将迁移 " + str(len(plans)) + " 项到 " + dv.get().strip() + chr(10) + chr(10) +
                   "不会删除文件；原目录改名 .bak 保留。" + chr(10) + "迁移期间请勿关闭本窗口。")
            if not messagebox.askyesno("确认迁移", ask, parent=win):
                return
            state["running"] = True
            start_btn.config(state="disabled", text="迁移中…")
            bar.configure(maximum=len(plans), value=0)
            state_var.set("准备中…")
            q.put(lambda: set_busy(True, "迁移中…"))

            def worker():
                done = 0
                fails = []
                try:
                    for i, p in enumerate(plans, 1):
                        label = p["product"] + " " + p["kind"]
                        q.put(lambda i=i, label=label: state_var.set(
                            "%d/%d  %s · 准备" % (i, len(plans), label)))
                        buf = []

                        def log1(msg, buf=buf):
                            buf.append(msg)
                            add_log("[迁移] " + msg)

                        def step(name, i=i, label=label):
                            ph = step_cn.get(name, name)
                            q.put(lambda: state_var.set(
                                "%d/%d  %s · %s" % (i, len(plans), label, ph)))

                        try:
                            good = M.migrate_one(p, apply=True, on_log=log1, on_step=step)
                        except Exception as e:
                            good = False
                            log1("异常: " + str(e))
                        if good:
                            done += 1
                        else:
                            fails.append((label, buf[-1] if buf else "未知原因"))
                        q.put(lambda i=i: bar.configure(value=i))
                except Exception as e:
                    add_log("[迁移] 线程异常: " + str(e))

                def summary():
                    state["running"] = False
                    start_btn.config(state="normal", text="关闭", command=close)
                    state_var.set("完成：成功 %d / %d 项" % (done, len(plans)))
                    bar.configure(value=len(plans))
                    set_busy(False, "就绪")
                    add_log("[迁移] 完成 %d/%d 项" % (done, len(plans)))
                    msg = "成功 " + str(done) + " / " + str(len(plans)) + " 项"
                    if fails:
                        msg += chr(10) + chr(10) + "失败：" + chr(10) + chr(10).join(
                            "· " + f[0] + " —— " + f[1] for f in fails)
                        msg += chr(10) + chr(10) + "未迁移成功的项原目录保持不变，可重试。"
                    if done:
                        msg += chr(10) + chr(10) + "迁移成功的项请重新启动对应软件后生效。"
                    messagebox.showinfo("迁移结果", msg, parent=win)
                    try:
                        refresh()
                    except Exception as e:
                        add_log("[迁移] 复检失败: " + str(e))

                q.put(summary)

            threading.Thread(target=worker, daemon=True).start()

        btnrow = tk.Frame(win, bg=BG)
        btnrow.pack(fill="x", padx=16, pady=(10, 6))
        start_btn = tk.Button(btnrow, text="开始迁移", command=start, bg=BLUE, fg="#ffffff",
                              font=("Microsoft YaHei", 10, "bold"), height=2, relief="flat",
                              cursor="hand2")
        start_btn.pack(side="left", fill="x", expand=True)
        tk.Button(btnrow, text="取消", command=close, bg="#e5e7eb",
                  font=("Microsoft YaHei", 10), height=2, relief="flat",
                  cursor="hand2").pack(side="left", padx=(8, 0))

    def on_accounts():
        import checkin as K

        def work():
            import accounts as A
            r = A.accounts()
            if not r["ok"]:
                return {"error": r["error"]}
            add_log("[账号] 数据库: " + r["db"])
            for a in r["accounts"]:
                add_log("[账号] " + a["short"] + "  " + str(a["sessions"]) + " 条会话")
            try:
                import wbtoken as T
                toks = T.fetch_tokens()
            except Exception:
                toks = []
            rows, need = [], []
            for t in toks:
                try:
                    st = K.status(t["token"], t["uid"], base=t["domain"])
                except Exception as e:
                    st = {"ok": False, "error": str(e)[:60]}
                desc = K.describe(st)
                add_log("[签到] " + t["uid"][:8] + "  " + t["domain"] + "  " + desc)
                rows.append("签到 " + t["uid"][:8] + "：" + desc)
                if st.get("ok") and not st.get("today"):
                    need.append(t)
            return {"r": r, "rows": rows, "need": need, "toks": toks}

        def done(res):
            if res.get("error"):
                add_log("[账号] " + res["error"])
                messagebox.showwarning("账号会话", res["error"])
                return
            r = res["r"]
            lines = [a["short"] + "   " + str(a["sessions"]) + " 条会话" for a in r["accounts"]]
            if res["rows"]:
                lines.append("")
                lines.extend(res["rows"])
            if not res["toks"]:
                lines.append("")
                lines.append("签到：未发现 token")
                if manual_token_dialog("签到"):
                    lines.append("签到：token 已保存到 config.json，可点「一键签到」")

            tips = ("迁移需先完全退出 WorkBuddy，再运行命令行（运行时数据库被占用）",
                    "用法: WBCoexist.exe --move-sessions <源账号> <目标账号> --apply")

            def final(extra=None):
                body = list(lines)
                if extra:
                    body.extend(extra)
                add_log("[账号] " + tips[0])
                add_log("[账号] " + tips[1])
                messagebox.showinfo("账号会话", chr(10).join(body) + chr(10) + chr(10) + chr(10).join(tips))

            if res["need"] and messagebox.askyesno(
                    "签到", "有 " + str(len(res["need"])) + " 个账号今日未签到，现在签到？"):
                def checkin_work():
                    out = []
                    for t in res["need"]:
                        try:
                            rr = K.do_checkin(t["token"], t["uid"], base=t["domain"])
                        except Exception as e:
                            rr = {"ok": False, "error": str(e)}
                        msg = "成功" if rr.get("ok") else ("失败：" + str(rr.get("error")))
                        if rr.get("already"):
                            msg = "服务端提示今日已签到"
                        add_log("[签到] " + t["uid"][:8] + "  " + msg)
                        out.append("签到 " + t["uid"][:8] + "：" + msg)
                    return out

                task("签到", checkin_work, final)
            else:
                final()

        task("账号会话", work, done)

    def on_checkin():
        import checkin as K

        def work():
            try:
                import wbtoken as T
                toks = T.fetch_tokens()
            except Exception:
                toks = []
            if not toks:
                return {"none": True}
            rows = []
            for t in toks:
                u = t["uid"][:8]
                try:
                    st = K.status(t["token"], t["uid"], base=t["domain"])
                except Exception as e:
                    st = {"ok": False, "error": str(e)[:60]}
                desc = K.describe(st)
                add_log("[签到] " + u + "  " + t["domain"] + "  " + desc)
                if not st.get("ok") or st.get("today"):
                    rows.append(u + "：" + desc)
                    continue
                try:
                    rr = K.do_checkin(t["token"], t["uid"], base=t["domain"])
                except Exception as e:
                    rr = {"ok": False, "error": str(e)}
                if not rr.get("ok"):
                    msg = "签到失败：" + str(rr.get("error"))
                elif rr.get("already"):
                    msg = "服务端提示今日已签到"
                else:
                    msg = "签到成功"
                add_log("[签到] " + u + "  " + msg)
                if rr.get("ok"):
                    try:  # 签到后复查，顺带把连续天数 / 累计积分带出来
                        st2 = K.status(t["token"], t["uid"], base=t["domain"])
                        if st2.get("ok"):
                            msg += "（" + K.describe(st2) + "）"
                    except Exception:
                        pass
                rows.append(u + "：" + msg)
            return {"rows": rows}

        def done(res):
            if res.get("none"):
                if manual_token_dialog("一键签到"):
                    add_log("[签到] 已保存 token，重新签到")
                    on_checkin()
                return
            messagebox.showinfo("一键签到", chr(10).join(res["rows"]))

        task("一键签到", work, done)

    def on_scan():
        def work():
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
            return ws, qs

        def done(res):
            ws, qs = res
            messagebox.showinfo("已安装检测",
                                "WorkBuddy " + str(len(ws)) + " 项 / Qoder " + str(len(qs)) + " 项" +
                                chr(10) + "明细见日志区")

        task("已安装检测", work, done)

    def on_clean():
        import cleaner as CL

        def scan_work():
            qr = Q.check()
            return {"qr": qr, "items": CL.scan(qr)}

        def run_clean(items, qr, with_residual):
            def do():
                r = CL.clean(items)
                acts = Q.clean(qr) if with_residual else []
                return {"r": r, "acts": acts}

            def done(res):
                r = res["r"]
                for it in r["cleaned"]:
                    add_log("[清理] " + it["group"] + " · " + it["label"] + "  " +
                            CL.fmt(it["freed"]))
                for a in res["acts"]:
                    add_log("[清理] " + a)
                for it in r["skipped"]:
                    add_log("[清理] 跳过（运行中）：" + it["group"] + " · " + it["label"])
                for e in r["errors"]:
                    add_log("[清理] 失败：" + e)
                add_log("[清理] 本次释放 " + CL.fmt(r["freed"]))
                refresh()
                body = "本次释放空间：" + CL.fmt(r["freed"])
                if r["skipped"]:
                    body += (chr(10) + "跳过 " + str(len(r["skipped"])) +
                             " 项（软件正在运行，退出后再清）")
                if r["errors"]:
                    body += chr(10) + str(len(r["errors"])) + " 项删除失败，详见日志区"
                if [a for a in res["acts"] if a.startswith("已归档")]:
                    body += chr(10) + "Qoder 残留已归档到 qoder-backups，可随时找回"
                messagebox.showinfo("清理完成", body)

            task("清理垃圾", do, done)

        def pick_dialog(items, residual, qr):
            groups, order = {}, []
            for it in items:
                g = it["group"]
                if g not in groups:
                    groups[g] = []
                    order.append(g)
                groups[g].append(it)

            dlg = tk.Toplevel(root)
            dlg.title("清理垃圾 · 选择要清理的项目")
            dlg.configure(bg=CARD)
            dlg.resizable(False, False)
            dlg.transient(root)

            hd = tk.Frame(dlg, bg=CARD)
            hd.pack(fill="x", padx=18, pady=(14, 0))
            tk.Label(hd, text="选择要清理的项目", bg=CARD, fg=TXT, anchor="w",
                     font=("Microsoft YaHei", 12, "bold")).pack(fill="x")
            tk.Label(hd, text="勾选后点「开始清理」，未勾选的保持不动。灰显项因软件正在运行暂时清不掉，退出后再清即可。",
                     bg=CARD, fg=SUB, anchor="w", justify="left", wraplength=600,
                     font=("Microsoft YaHei", 8)).pack(fill="x", pady=(4, 0))

            box = tk.Frame(dlg, bg=CARD, highlightbackground=LINE, highlightthickness=1)
            box.pack(fill="both", expand=True, padx=18, pady=(10, 0))
            cv = tk.Canvas(box, bg=CARD, highlightthickness=0)
            sb = ttk.Scrollbar(box, orient="vertical", command=cv.yview)
            cv.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")
            cv.pack(side="left", fill="both", expand=True)
            inner = tk.Frame(cv, bg=CARD)
            win = cv.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
            cv.bind("<Configure>", lambda e: cv.itemconfigure(win, width=e.width))

            picked = []

            def add_row(label, note, right, item, running=False):
                v = tk.BooleanVar(value=not running)
                row = tk.Frame(inner, bg=CARD)
                row.pack(fill="x", padx=14, pady=(4, 0))
                cb = tk.Checkbutton(row, text=label, variable=v,
                                    bg=CARD, fg=(SUB if running else TXT),
                                    activebackground=CARD, activeforeground=TXT,
                                    selectcolor=CARD, disabledforeground=SUB,
                                    highlightthickness=0, bd=0, anchor="w",
                                    font=("Microsoft YaHei", 9, "bold" if not running else "normal"))
                if running:
                    cb.config(state="disabled")
                cb.pack(side="left")
                tk.Label(row, text=right, bg=CARD, fg=SUB,
                         font=("Microsoft YaHei", 8)).pack(side="right")
                tk.Label(inner, text=note + ("；软件正在运行，暂时无法清理" if running else ""),
                         bg=CARD, fg=SUB, anchor="w", justify="left", wraplength=540,
                         font=("Microsoft YaHei", 8)).pack(fill="x", padx=(34, 14))
                picked.append((v, item, running))

            for g in order:
                arr = groups[g]
                gh = tk.Frame(inner, bg=CARD)
                gh.pack(fill="x", padx=14, pady=(12, 0))
                tk.Label(gh, text=g, bg=CARD, anchor="w",
                         fg=("#7c3aed" if g.startswith("Qoder") else "#1d4ed8"),
                         font=("Microsoft YaHei", 9, "bold")).pack(side="left")
                tk.Label(gh, text=CL.fmt(sum(x["size"] for x in arr)), bg=CARD, fg=SUB,
                         font=("Microsoft YaHei", 8)).pack(side="right")
                for it in arr:
                    add_row(it["label"] + ("（运行中）" if it["running"] else ""),
                            it["note"], CL.fmt(it["size"]), it, it["running"])

            if residual:
                gh = tk.Frame(inner, bg=CARD)
                gh.pack(fill="x", padx=14, pady=(12, 0))
                tk.Label(gh, text="Qoder 残留", bg=CARD, fg="#7c3aed", anchor="w",
                         font=("Microsoft YaHei", 9, "bold")).pack(side="left")
                tk.Label(gh, text="归档，不删除", bg=CARD, fg=SUB,
                         font=("Microsoft YaHei", 8)).pack(side="right")
                add_row(residual["label"], residual["note"], residual["detail"], residual)
            tk.Frame(inner, bg=CARD, height=10).pack()

            sel_var = tk.StringVar()

            def recalc():
                n, total = 0, 0
                for v, it, running in picked:
                    if running or not v.get():
                        continue
                    n += 1
                    total += it.get("size") or 0
                txt = "已选 " + str(n) + " / " + str(len(picked)) + " 项"
                if total:
                    txt += " · 预计释放 " + CL.fmt(total)
                sel_var.set(txt)
                b_go.config(state=("normal" if n else "disabled"),
                            bg=(BLUE if n else "#93b4f5"))

            def select_all(on):
                for v, it, running in picked:
                    if not running:
                        v.set(on)
                recalc()

            foot = tk.Frame(dlg, bg=BG)
            foot.pack(fill="x", padx=18, pady=12)
            tk.Label(foot, textvariable=sel_var, bg=BG, fg=SUB, anchor="w",
                     font=("Microsoft YaHei", 9)).pack(side="left")

            def mkb(text, cmd, primary=False):
                b = tk.Button(foot, text=text, command=cmd, bd=0, relief="flat",
                              padx=13, pady=5, cursor="hand2",
                              font=("Microsoft YaHei", 9, "bold" if primary else "normal"),
                              bg=(BLUE if primary else CARD), fg="#ffffff" if primary else TXT,
                              activebackground=("#1e40af" if primary else "#eef2f7"),
                              activeforeground="#ffffff" if primary else TXT,
                              highlightthickness=1, highlightbackground=LINE,
                              disabledforeground="#e0e7ff")
                b.pack(side="right", padx=(6, 0))
                return b

            def cancel():
                dlg.grab_release()
                dlg.destroy()
                add_log("[清理] 已取消，未做任何改动")

            def start():
                sel = [it for v, it, running in picked
                       if v.get() and not running and not it.get("residual")]
                res = any(v.get() and it.get("residual") for v, it, running in picked)
                dlg.grab_release()
                dlg.destroy()
                run_clean(sel, qr, res)

            b_go = mkb("开始清理", start, primary=True)
            mkb("取消", cancel)
            mkb("全不选", lambda: select_all(False))
            mkb("全选", lambda: select_all(True))

            def wheel(e):
                cv.yview_scroll(int(-e.delta / 120) * 3, "units")

            def bind_wheel(w):
                w.bind("<MouseWheel>", wheel)
                for c in w.winfo_children():
                    bind_wheel(c)

            bind_wheel(inner)
            cv.bind("<MouseWheel>", wheel)
            dlg.bind("<Escape>", lambda e: cancel())

            dlg.update_idletasks()
            w, h = 660, 620
            x = root.winfo_rootx() + (root.winfo_width() - w) // 2
            y = root.winfo_rooty() + max(16, (root.winfo_height() - h) // 2)
            dlg.geometry("%dx%d+%d+%d" % (w, h, x, y))
            dlg.grab_set()
            dlg.focus_set()
            recalc()

        def scan_done(res):
            qr, items = res["qr"], res["items"]
            orph = qr.get("orphans") or []
            dead = [x for x in qr.get("clients", [])
                    if (not x.get("alive")) and x.get("pid")]
            residual = None
            if orph or dead:
                residual = {"residual": True,
                            "label": "孤儿 host 副本 + 失效中继记录",
                            "note": "不改动安装目录、不删除记录，统一移动归档到 qoder-backups",
                            "detail": str(len(orph)) + " 个副本 · " + str(len(dead)) + " 条记录"}
            if not items and not residual:
                add_log("[清理] 没有可清理的缓存或残留")
                messagebox.showinfo("清理垃圾", "没有需要清理的项目")
                return
            add_log("[清理] 扫描到 " + str(len(items)) + " 项缓存/日志" +
                    ("，另有 Qoder 残留可归档" if residual else ""))
            pick_dialog(items, residual, qr)

        task("扫描垃圾", scan_work, scan_done)

    def on_prep():
        def work():
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
            return ok

        def done(ok):
            refresh()
            messagebox.showinfo("安装前检查",
                                ("可以开始安装。" if ok else "建议先处理注意事项。") + chr(10) + chr(10) +
                                "详细结果见日志区。")

        task("安装前检查", work, done)

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

    # ---------- 视觉组件 ----------
    def rrect(cv, x1, y1, x2, y2, r, **kw):
        pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
               x2, y2 - r, x2, y2, x2 - r, y2,
               x1 + r, y2, x1, y2, x1, y2 - r,
               x1, y1 + r, x1, y1]
        return cv.create_polygon(pts, smooth=True, splinesteps=18, **kw)

    def mix(c1, c2, t):
        a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
        b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
        return "#%02x%02x%02x" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    class Card(tk.Frame):
        # 圆角白卡片：Canvas 画底，内容放 body
        def __init__(self, parent, height=None, radius=12):
            tk.Frame.__init__(self, parent, bg=BG)
            if height:
                self.configure(height=height)
            self._radius = radius
            self._cv = tk.Canvas(self, bg=BG, bd=0, highlightthickness=0)
            self._cv.place(x=0, y=0, relwidth=1, relheight=1)
            self.body = tk.Frame(self, bg=CARD)
            self.body.place(x=12, y=8, relwidth=1, relheight=1, width=-24, height=-16)
            self.bind("<Configure>", self._paint)

        def _paint(self, e=None):
            w, h = self.winfo_width(), self.winfo_height()
            if w < 8 or h < 8:
                return
            self._cv.delete("bg")
            rrect(self._cv, 0.5, 0.5, w - 1.5, h - 1.5, self._radius,
                  fill=CARD, outline=LINE, tags="bg")
            self._cv.tag_lower("bg")

    class CardButton(tk.Canvas):
        # 圆角按钮，标题 + 一行小字说明，鼠标悬停/按下/禁用都有反馈
        def __init__(self, parent, title, hint, command, tone="light",
                     height=56, font_size=10):
            tk.Canvas.__init__(self, parent, height=height, bg=BG, bd=0,
                               highlightthickness=0, cursor="hand2", takefocus=1)
            self._title, self._hint, self._cmd = title, hint, command
            self._tone, self._fs = tone, font_size
            self._state, self._hover, self._pressed = "normal", False, False
            self.bind("<Configure>", self._paint)
            self.bind("<Enter>", lambda e: self._set_hover(True))
            self.bind("<Leave>", lambda e: self._set_hover(False))
            self.bind("<ButtonPress-1>", self._press)
            self.bind("<ButtonRelease-1>", self._release)
            self.bind("<Return>", lambda e: self._fire())
            self.bind("<space>", lambda e: self._fire())
            self.bind("<FocusIn>", lambda e: self._paint())
            self.bind("<FocusOut>", lambda e: self._paint())

        def set_state(self, st):
            self._state = st
            self.configure(cursor="hand2" if st == "normal" else "")
            self._paint()

        def _set_hover(self, on):
            self._hover = on
            self._paint()

        def _press(self, e):
            self.focus_set()
            self._pressed = True
            self._paint()

        def _release(self, e):
            was = self._pressed
            self._pressed = False
            self._paint()
            if was and 0 <= e.x <= self.winfo_width() and 0 <= e.y <= self.winfo_height():
                self._fire()

        def _fire(self):
            if self._state == "normal":
                self._cmd()

        def _paint(self, e=None):
            self.delete("all")
            w = max(self.winfo_width(), 40)
            h = max(self.winfo_height(), 24)
            disabled = self._state != "normal"
            if disabled:
                fill, line, fg, hfg = "#eef1f5", "#e5e7eb", "#9aa3af", "#b6bcc7"
            elif self._tone == "blue":
                fill = "#1e40af" if (self._hover or self._pressed) else BLUE
                line, fg, hfg = fill, "#ffffff", "#dbeafe"
            elif self._tone == "green":
                fill = "#15803d" if (self._hover or self._pressed) else GREEN
                line, fg, hfg = fill, "#ffffff", "#dcfce7"
            else:
                fill = "#f5f8ff" if self._hover else CARD
                line = "#93b4f5" if self._hover else LINE
                fg, hfg = TXT, SUB
            rrect(self, 1, 1, w - 2, h - 2, 10, fill=fill, outline=line)
            if self.focus_get() is self and not disabled:
                rrect(self, 2, 2, w - 3, h - 3, 9, fill="", outline="#93c5fd")
            cy = h // 2
            if self._hint:
                self.create_text(16, cy - 9, text=self._title, anchor="w", fill=fg,
                                 font=("Microsoft YaHei", self._fs, "bold"))
                self.create_text(16, cy + 9, text=self._hint, anchor="w", fill=hfg,
                                 font=("Microsoft YaHei", 8))
            else:
                self.create_text(16, cy, text=self._title, anchor="w", fill=fg,
                                 font=("Microsoft YaHei", self._fs, "bold"))
            if self._tone == "light" and not disabled:
                self.create_text(w - 14, cy, text="›", anchor="e", fill="#b8c1cf",
                                 font=("Segoe UI", 13))

    def card_head(card, letter, name, note, tint, color):
        row = tk.Frame(card.body, bg=CARD)
        row.pack(fill="x", pady=(0, 4))
        cv = tk.Canvas(row, width=20, height=20, bg=CARD, highlightthickness=0)
        cv.pack(side="left")
        rrect(cv, 1, 1, 19, 19, 6, fill=tint, outline="")
        cv.create_text(10, 10, text=letter, fill=color, font=("Segoe UI", 8, "bold"))
        tk.Label(row, text=name, bg=CARD, fg=TXT,
                 font=("Microsoft YaHei", 10, "bold")).pack(side="left", padx=(6, 5))
        tk.Label(row, text=note, bg=CARD, fg=SUB,
                 font=("Microsoft YaHei", 8)).pack(side="left", pady=(1, 0))

    # ---------- 顶部标题栏 ----------
    HEAD_H = 76
    head = tk.Canvas(root, height=HEAD_H, bg=BLUE, bd=0, highlightthickness=0)
    head.pack(fill="x")

    def paint_head(e=None):
        w = head.winfo_width()
        head.delete("all")
        for y in range(HEAD_H):
            head.create_line(0, y, w, y, fill=mix("#1d4ed8", "#0f2e63", y / (HEAD_H - 1)))
        head.create_text(22, 28, text="双版共存管家", anchor="w", fill="#ffffff",
                         font=("Microsoft YaHei", 17, "bold"))
        head.create_text(23, 53, text="WorkBuddy / Qoder 国内版 · 国际版共存修复",
                         anchor="w", fill="#c7d2fe", font=("Microsoft YaHei", 9))
        rrect(head, w - 84, 20, w - 22, 44, 12, fill="#1e40af", outline="#3b82f6")
        head.create_text(w - 53, 32, text="v1.6", fill="#dbeafe",
                         font=("Segoe UI", 9, "bold"))
        head.create_text(w - 22, 58, text="无需管理员 · 不删文件", anchor="e",
                         fill="#93c5fd", font=("Microsoft YaHei", 8))

    head.bind("<Configure>", paint_head)

    # ---------- 状态卡片 ----------
    stat = tk.Frame(root, bg=BG)
    stat.pack(fill="x", padx=16, pady=(12, 0))
    stat.columnconfigure(0, weight=1, uniform="status")
    stat.columnconfigure(1, weight=1, uniform="status")

    lamps = {}
    wbcard = Card(stat, height=158)
    wbcard.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    card_head(wbcard, "W", "WorkBuddy", "国内 + 国际", "#dbeafe", "#1d4ed8")
    for k in ("CN", "AI", "scheme", "cache"):
        lamps[k] = lamp(wbcard.body)

    qcard = Card(stat, height=158)
    qcard.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    card_head(qcard, "Q", "Qoder", "国内 + 国际", "#ede9fe", "#7c3aed")
    for k in ("qintl", "qcn", "qconn", "qreg"):
        lamps[k] = lamp(qcard.body)

    sumcard = Card(root, height=38)
    sumcard.pack(fill="x", padx=16, pady=(8, 0))
    sumdot = tk.Canvas(sumcard.body, width=10, height=20, bg=CARD, highlightthickness=0)
    sumdot.pack(side="left", padx=(0, 8))
    sumdot_i = sumdot.create_oval(1, 5, 9, 13, fill=SUB, outline="")
    summary = tk.Label(sumcard.body, text="正在体检…", bg=CARD, fg=SUB,
                       font=("Microsoft YaHei", 9), anchor="w")
    summary.pack(side="left", fill="x", expand=True)

    # ---------- 主操作 ----------
    top = tk.Frame(root, bg=BG)
    top.pack(fill="x", padx=16, pady=(10, 0))
    top.columnconfigure(0, weight=3, uniform="top")
    top.columnconfigure(1, weight=2, uniform="top")

    b_fix = CardButton(top, "一键修复", "修复更新后互相抢占的共享资源", on_fix,
                       tone="blue", height=62, font_size=13)
    b_fix.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
    b_ci = CardButton(top, "WorkBuddy 每日签到", "自动查询并领取今日积分", on_checkin,
                      tone="green", height=62, font_size=11)
    b_ci.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
    buttons.extend([b_fix, b_ci])

    grid = tk.Frame(root, bg=BG)
    grid.pack(fill="x", padx=16, pady=(8, 0))
    for i in range(3):
        grid.columnconfigure(i, weight=1, uniform="grid")

    def gbtn(r, c, title, hint, cmd):
        b = CardButton(grid, title, hint, cmd, height=54)
        b.grid(row=r, column=c, sticky="nsew",
               padx=(0 if c == 0 else 4, 0 if c == 2 else 4),
               pady=(0 if r == 0 else 6, 0))
        buttons.append(b)
        return b

    gbtn(0, 0, "刷新状态", "重新检测 8 项共享资源",
         lambda: (add_log("手动刷新状态"), refresh()))
    gbtn(0, 1, "安装前检查", "装新版本前先排查冲突", on_prep)
    gbtn(0, 2, "迁移到其他盘", "无损搬移，不删任何文件", on_migrate)
    gbtn(1, 0, "查看已安装", "列出本机全部版本与路径", on_scan)
    gbtn(1, 1, "清理垃圾", "缓存日志 + 失效残留", on_clean)
    gbtn(1, 2, "账号与 Token", "查看会话、签到、手动填写", on_accounts)

    # ---------- 行为选项 ----------
    opt = tk.Frame(root, bg=BG)
    opt.pack(fill="x", padx=16, pady=(10, 0))
    primary_var = tk.StringVar(value=cfg["primary"])
    tk.Label(opt, text="buddy-app 协议归属", bg=BG, fg=SUB,
             font=("Microsoft YaHei", 9)).pack(side="left")
    tk.Radiobutton(opt, text="国内版", variable=primary_var, value="CN", bg=BG,
                   activebackground=BG, selectcolor=CARD, highlightthickness=0, bd=0,
                   font=("Microsoft YaHei", 9),
                   command=on_primary).pack(side="left", padx=(4, 0))
    tk.Radiobutton(opt, text="国际版", variable=primary_var, value="AI", bg=BG,
                   activebackground=BG, selectcolor=CARD, highlightthickness=0, bd=0,
                   font=("Microsoft YaHei", 9),
                   command=on_primary).pack(side="left")
    guard_var = tk.IntVar(value=int(cfg["guard"]))
    tk.Checkbutton(opt, text="后台守护（自动修回）", variable=guard_var, bg=BG,
                   activebackground=BG, selectcolor=CARD, highlightthickness=0, bd=0,
                   font=("Microsoft YaHei", 9),
                   command=on_guard).pack(side="left", padx=(16, 0))
    auto_var = tk.IntVar(value=int(C.autostart_get()))
    tk.Checkbutton(opt, text="开机自启", variable=auto_var, bg=BG,
                   activebackground=BG, selectcolor=CARD, highlightthickness=0, bd=0,
                   font=("Microsoft YaHei", 9),
                   command=on_autostart).pack(side="left", padx=(10, 0))

    # ---------- 日志 ----------
    loghead = tk.Frame(root, bg=BG)
    loghead.pack(fill="x", padx=18, pady=(8, 2))
    tk.Label(loghead, text="运行日志", bg=BG, fg=SUB,
             font=("Microsoft YaHei", 9, "bold")).pack(side="left")
    tk.Label(loghead, textvariable=status_var, bg=BG, fg=BLUE,
             font=("Microsoft YaHei", 9)).pack(side="left", padx=(10, 0))
    clr = tk.Label(loghead, text="清空", bg=BG, fg=SUB,
                   font=("Microsoft YaHei", 8), cursor="hand2")
    clr.pack(side="right")

    logbox = scrolledtext.ScrolledText(root, height=6, bg="#0f172a", fg="#cbd5e1",
                                       insertbackground="#cbd5e1",
                                       font=("Consolas", 9), relief="flat", bd=0,
                                       padx=10, pady=8)
    logbox.pack(fill="both", expand=True, padx=16, pady=(0, 12))
    clr.bind("<Button-1>", lambda e: logbox.delete("1.0", tk.END))

    add_log("双版共存管家已启动；点「一键修复」处理更新导致的冲突")
    add_log("WorkBuddy：修 buddy-app 归属 + 归档陈旧更新缓存")
    add_log("Qoder：修共享 browser-connector（manifest / host 代际 / Chrome·Edge 注册）")
    add_log("「WorkBuddy 每日签到」自动发现 token → 查状态 → 未签到则直接签到")
    add_log("「清理垃圾」先列出勾选清单，只清缓存与日志，配置/会话/数据库不动")
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
                if callable(s):
                    try:
                        s()
                    except Exception as e:
                        add_log("[界面] 更新失败: " + str(e))
                elif s == "[refresh]":
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
