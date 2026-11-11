#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# WorkBuddy 共存管家 v1.0 - 主程序
# 双击启动 GUI；--daemon 无窗口后台守护；--selftest 自检
import sys, os, time, json, threading, queue
sys.path.insert(0, "D:/Apps/WBCoexist")
import wbcore as C

BG = "#f4f6f9"
CARD = "#ffffff"
TXT = "#1f2937"
SUB = "#6b7280"
GREEN = "#16a34a"
RED = "#dc2626"
ORANGE = "#ea580c"
BLUE = "#2563eb"

def daemon_main():
    C.log("后台守护已启动")
    while True:
        try:
            c = C.cfg_load()
            msg = C.daemon_tick(c)
            if msg:
                C.log(msg)
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
    out = buf.getvalue()
    try:
        open("D:/Apps/WBCoexist/selftest.txt", "w", encoding="utf-8").write(out)
    except Exception:
        pass
    try:
        sys.stdout.write(out)
    except Exception:
        pass

def gui_main():
    import tkinter as tk
    from tkinter import scrolledtext, messagebox
    root = tk.Tk()
    root.title("WorkBuddy 共存管家  v1.0")
    root.geometry("640x560")
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
        n = len(r["issues"])
        summary.config(text="体检结果：" + ("全部正常，无需处理" if n == 0 else str(n) + " 项待处理"),
                       fg=GREEN if n == 0 else ORANGE)
        return r

    def on_fix():
        c = C.cfg_load()
        r = C.check(c["primary"])
        acts = C.fix(r, c["primary"], apply=True)
        for a in acts:
            add_log("[一键修复] " + a)
        add_log("--- 修复完成，正在复检 ---")
        refresh()
        messagebox.showinfo("完成", "一键修复已完成" + chr(10) + chr(10) + chr(10).join(acts))

    def on_prep():
        c = C.cfg_load()
        other = "AI" if c["primary"] == "CN" else "CN"
        run = C.running(C.EXE[other].rsplit("/", 1)[1])
        r = C.check(c["primary"])
        add_log("[更新前准备] 另一版 " + other + " " + ("仍在运行，请先完全退出" if run else "未运行 OK"))
        add_log("[更新前准备] 更新器缓存 " + ("存在，建议点一键修复归档" if r["cache"] else "干净 OK"))
        add_log("[更新前准备] 更新完成后再点一次 一键修复")
        refresh()

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
    tk.Label(head, text="WorkBuddy 共存管家", bg=BLUE, fg="#ffffff",
             font=("Microsoft YaHei", 16, "bold")).pack(side="left", padx=18)
    tk.Label(head, text="CN / AI 双版本 · 更新冲突一键处理", bg=BLUE, fg="#dbeafe",
             font=("Microsoft YaHei", 9)).pack(side="left", padx=4, pady=(6, 0))

    card = tk.Frame(root, bg=CARD, highlightbackground="#e5e7eb", highlightthickness=1)
    card.pack(fill="x", padx=16, pady=(14, 8))
    tk.Label(card, text="当前状态", bg=CARD, fg=SUB,
             font=("Microsoft YaHei", 9, "bold")).pack(anchor="w", padx=14, pady=(10, 4))
    lamps = {"CN": lamp(card, ""), "AI": lamp(card, ""),
             "scheme": lamp(card, ""), "cache": lamp(card, "")}
    summary = tk.Label(card, text="", bg=CARD, fg=SUB, font=("Microsoft YaHei", 9))
    summary.pack(anchor="w", padx=14, pady=(6, 10))

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
    btns.pack(fill="x", padx=16, pady=12)
    tk.Button(btns, text="一 键 修 复", command=on_fix, bg=BLUE, fg="#ffffff",
              activebackground="#1d4ed8", font=("Microsoft YaHei", 12, "bold"),
              height=2, relief="flat", cursor="hand2").pack(side="left", fill="x", expand=True, padx=(0, 6))
    tk.Button(btns, text="重新体检", command=lambda: (add_log("手动体检"), refresh()),
              bg="#e5e7eb", font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)
    tk.Button(btns, text="更新前准备", command=on_prep, bg="#e5e7eb",
              font=("Microsoft YaHei", 9), height=2, relief="flat",
              cursor="hand2").pack(side="left", padx=3)

    logbox = scrolledtext.ScrolledText(root, height=9, bg="#111827", fg="#d1fae5",
                                       font=("Consolas", 9), relief="flat")
    logbox.pack(fill="both", expand=True, padx=16, pady=(0, 14))
    add_log("WorkBuddy 共存管家已启动；点「一键修复」处理更新导致的冲突")
    add_log("勾选「开机自启」后，后台守护会自动修回被抢占的 buddy-app")

    def guard_loop():
        while True:
            c = C.cfg_load()
            if c.get("guard"):
                m = C.daemon_tick(c)
                if m:
                    q.put(C.log("[守护] " + m))
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
        root.after(400, root.destroy)
    root.mainloop()

def main():
    if "--daemon" in sys.argv:
        daemon_main()
    elif "--selftest" in sys.argv:
        selftest()
    else:
        gui_main()

if __name__ == "__main__":
    main()
