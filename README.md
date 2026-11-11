<div align="center">

<img width="110" src="docs/icon.webp" alt="双版共存管家">

# 双版共存管家

**让 WorkBuddy 与 Qoder 的国内版、国际版在同一台电脑上和平共处**

**🛠️ 一键修复更新后的资源抢占 ｜ 🛡️ 后台守护自动纠回 ｜ 📦 免安装单文件 exe**

Windows 10 / 11 · 免安装 · 无需管理员 · 不联网

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)]()
[![Version](https://img.shields.io/badge/Version-1.4.0-2563eb?style=for-the-badge)]()
[![Runtime](https://img.shields.io/badge/Runtime-Standalone%20EXE-16a34a?style=for-the-badge)]()
[![Python](https://img.shields.io/badge/Python-3.10-3776AB?style=for-the-badge&logo=python&logoColor=white)]()

<br/>

**[📥 下载最新版](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/latest)** · **[🚀 快速开始](#-快速开始)** · **[🧩 冲突清单](#-冲突从哪来)** · **[❓ FAQ](#-faq)** · **[📜 更新日志](CHANGELOG.md)**

</div>

---

## 📖 这是什么

> 同一个软件装两个版本，本来是为了分别登录两个账号；结果每次更新，后更新的那个就把前一个的资源抢走。

**双版共存管家** 是面向「同一款软件的国内版与国际版共存」场景的修复工具，目前覆盖两套软件：

- **WorkBuddy**：CN 5.9.3 与 AI 国际版 5.9.4
- **Qoder**：中国版 0.5.2 与国际版 0.5.7

它做三件事：**体检**（8 盏灯看清哪里被抢）→ **一键修复**（按约定归属写回）→ **后台守护**（8 秒轮询，被抢占自动纠回）。

> [!NOTE]
> **先说清楚边界**：本工具**不是**让 WorkBuddy 与 Qoder 互相共存 —— 两者本来就互不相干。
> 它解决的是 **WorkBuddy 的国内版 ↔ 国际版**、**Qoder 的国内版 ↔ 国际版** 这两组「同门兄弟」互相抢资源的问题。

### 核心价值主张

| 维度 | 说明 |
|:---|:---|
| 🎯 **只改该改的** | 只写 HKCU 注册表与用户目录，不碰系统目录、不删用户数据；陈旧安装包是**移动归档**而不是删除 |
| 🔍 **先看清再动手** | 启动即体检，8 盏灯分列 WorkBuddy 侧与 Qoder 侧，红灯项一目了然 |
| 🛡️ **守护兜底** | 更新器每次都会重写共享指向，手动修一次不够；开机守护在 8 秒内纠回 |
| 📦 **零依赖** | 单文件 exe，自带 Python 与 tcl/tk 运行时，免安装、无需管理员、不联网 |
| ♻️ **可回退** | 归档包与旧 manifest 备份都保留，需要时放回即可 |

---

## 🧩 冲突从哪来

两版是**同一套代码、不同发行版**，但有若干**全局资源没有按产品隔离**，谁最后写谁生效。

### WorkBuddy：3 个共享资源

| 资源 | 冲突表现 | 本工具的处理 |
|:---|:---|:---|
| 更新器缓存<br>`%LOCALAPPDATA%\@genieworkbuddy-desktop-updater\installer.exe` | 两版共用同一路径，更新时残留另一版安装包 → 竞态 / 装错版本 | 归档到 D 盘（不删除，可回退） |
| URL 协议<br>`buddy-app://` | 两版都注册同名 scheme，后更新者覆盖唤起目标 | 固定回约定版本；守护自动修回 |
| MSIX 分享目标 Identity | 两版同名 `WorkBuddyShareTarget`，后装覆盖 | 仅影响「分享到」，不在处理范围 |

另有 `~/.workbuddy-key-fallback` 共享凭证目录，只读观察，不改动。

### Qoder：共用一个 browser-connector

| 资源 | 冲突表现 | 本工具的处理 |
|:---|:---|:---|
| 共享 manifest<br>`~/.qoder/browser-connector/com.qoder.app.connector.json` | 两版扩展 ID 都指向同一个 host，`path` 只能写一个 | 指向版本较新那版的 host 副本，同时保留两个 `allowed_origins` |
| host 副本<br>`hosts/<启动器 sha256>/` | 两版启动器代际不同（CN 0.5.2 / 国际版 0.5.7），谁最后启动写谁 | 以版本号较大者为基准代际，缺失时自动补建 |
| Chrome / Edge<br>`NativeMessagingHosts` 注册 | 指向错误 manifest 时浏览器扩展连不上 | 写回 HKCU 正确路径 |
| 中继记录<br>`clients/qoder-<uuid>.json` | 进程退出后留下失效记录 | 「清理孤儿」删除失效记录与旧代际 host |

> [!TIP]
> 两版版本号不同期间，连接器会在两边启动时来回切换，这是**提示**而不是错误；两边升到同一版本并各启动一次后自然收敛。

## 📷 界面

<div align="center">

<img width="72%" src="docs/screenshot.webp" alt="双版共存管家主界面">

</div>

8 盏灯分左右两组：左列 WorkBuddy（两个发行版的安装完整性、`buddy-app://` 归属、更新器缓存），右列 Qoder（两版版本与运行状态、连接器 host 代际、Chrome / Edge 注册）。全绿即共存正常；图中那条提示是 Qoder 两版版本号不同（0.5.7 / 0.5.2），属信息提示。

| 区域 | 内容 |
|:---|:---|
| 主按钮 | **一键修复** —— 一次处理 WorkBuddy 协议与缓存、Qoder manifest / host 代际 / 浏览器注册 |
| 辅助按钮 | 重新体检、更新前准备、清理孤儿（删除前弹确认框） |
| 选项行 | `buddy-app://` 归属（CN / AI）、后台守护、开机自启 |
| 日志区 | 每次动作留痕，同时写入 `run.log` |

---

## ✨ 功能一览

| 功能 | 说明 |
|:---|:---|
| **一键修复** | WorkBuddy 修协议归属 + 归档陈旧缓存；Qoder 修 manifest / host 代际 / 浏览器注册；完成后自动复检并弹结果 |
| **重新体检** | 刷新 8 盏状态灯 |
| **已安装检测** | 扫描本机所有 WorkBuddy / Qoder 安装，列出产品名、版本、路径、是否运行；Qoder 还会列出 `.qoder-versions` 下未在用的历史版本 |
| **安装前检查** | 两套软件一次查完：另一版是否仍在运行、更新器缓存是否残留、Qoder manifest 与 Chrome/Edge 注册、系统盘与软件盘剩余空间、各版当前版本与安装位置；给出「可以安装 / 建议先处理」结论 |
| **清理孤儿** | 删除 Qoder 旧代际 host 副本与失效中继记录（先弹确认框） |
| **协议归属** | 单选 CN / AI，决定 `buddy-app://` 由谁接管（默认 CN） |
| **后台守护** | 窗口开着时每 8 秒检测两套软件各自的共享指向，被抢占自动修回（只修指向，不碰缓存、不做清理） |
| **开机自启** | 写 HKCU Run，开机以无窗口守护常驻，更新完不用手动点 |

---

## 🚀 快速开始

1. **下载**：从 [Releases](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/latest) 取 `WBCoexist-v*.exe`（单文件），或 `WBCoexist-portable-*.zip`（便携版）
2. **运行**：双击。启动即自动体检，看 8 盏灯
3. **修复**：有红灯就点「一键修复」，完成后自动复检

无需安装、无需管理员权限、无需联网。

### 两种发行版

| 版本 | 说明 | 适用 |
|:---|:---|:---|
| **单文件 exe** | 约 9.6 MB，双击即用 | 图省事；个别杀软会误报（见 FAQ） |
| **便携版 zip** | 约 9.9 MB，解压后**整个文件夹**一起用 | 杀软环境；不自解压，误报明显更少 |

> [!WARNING]
> 便携版必须连同 `_internal` 文件夹一起移动，**只拷 exe 会启动失败**。

---

## 🎯 适用与不适用

| 适合 | 不适合 |
|:---|:---|
| 同时装了 WorkBuddy CN + AI 国际版 | 只装了一个版本 |
| 同时装了 Qoder 中国版 + 国际版 | macOS / Linux |
| 更新后扩展连不上、深度链接跳错版本、装错包 | 期望从根上消除冲突（根因在应用内部，本工具是自动纠偏） |

## ⚙️ 命令行

无窗口运行，结果同时写入文本文件：

| 参数 | 作用 |
|:---|:---|
| `--selftest` | 两套软件的完整体检 + 修复预览（写 `selftest.txt`） |
| `--qoder-check` | Qoder 完整诊断 JSON（写 `qoder-cli.txt`） |
| `--qoder-fix` | 立即修复 Qoder 共享连接器 |
| `--qoder-clean` | 删除 Qoder 孤儿 host 与失效中继记录 |
| `--daemon` | 无窗口后台守护（开机自启用的就是它） |
| `--smoke` | 构建 GUI 后自动关闭，用于打包后自检 |

---

## 🔄 更新 SOP

1. **安装前**：点「安装前检查」—— 查另一版是否还在跑、缓存是否残留、manifest / 浏览器注册是否完好、磁盘够不够，给出「可以安装 / 建议先处理」
2. **安装 / 更新**：正常走安装器，另一版务必先**完全退出**
3. **安装后**：守护在 8 秒内检测到程序被替换，自动全量修复；也可手动点「一键修复」
4. **Qoder 两版同版本后**：各启动一次，让连接器代际收敛

---

## ❓ FAQ

**会删我的文件吗？**
不会。修复只写 HKCU 注册表与用户目录；陈旧的更新器安装包是**移动归档**到 D 盘，不是删除。「清理孤儿」只删 Qoder 旧代际 host 与失效中继记录，且删除前弹确认框。

**需要管理员权限吗？**
不需要。全部操作在 HKCU 与用户目录内完成。

**更新后还要再点一次吗？**
开了「开机自启」（后台守护常驻）就不用。否则更新后点一次「一键修复」即可。

**为什么不能彻底根治？**
共享路径写在应用内部，改不了。本工具做的是「每次被抢走就自动纠正」，属于缓解而非根治。

**支持哪些系统？**
Windows 10 / 11 x64。macOS、Linux 不适用。

**杀软报毒怎么办？**

<details>
<summary>展开：为什么会被报，以及三种处理方式</summary>

PyInstaller 单文件 exe 运行时会把自身解压到 `%TEMP%\_MEIxxxx` 再执行，这个行为是国产杀软启发式引擎的高发误报点；文件又没有数字签名，容易被判可疑。

按顺序试：

1. **优先用便携版**：`portable\WBCoexist\WBCoexist.exe`，不再自解压，误报概率显著低于单文件。把整个 `portable\WBCoexist` 文件夹加进信任目录，或直接在该目录内双击运行。
2. **单文件被拦截时**：把 `WBCoexist.exe` 加进「信任区」；若已被隔离，先到「恢复区」恢复再添加。
3. **提交误报**：说明用途（本机双版本共存修复工具、源码可查、只写 HKCU 与用户目录），附 SHA-256。每次重新打包哈希都会变，需要重新提交。

已做的降低误报措施：嵌入完整版本资源（1.1.0.0）、自定义 manifest（`asInvoker`，不请求管理员）、`--noupx` 禁用压缩。

实在被拦又不想加白，可直接跑源码（不产生 exe）：双击 `WBCoexist-FromSource.bat`。

</details>

## 🏗️ 技术栈

| 层 | 选型 |
|:---|:---|
| GUI | Python 3.10 + Tkinter（无第三方 UI 依赖） |
| 打包 | PyInstaller 6.22.3，onefile + onedir，`--noupx`，嵌入版本资源与 `asInvoker` manifest |
| 注册表 | `winreg`，只写 HKCU |
| 进程检测 | `tasklist` |
| CI | GitHub Actions（`windows-latest`），tag 触发构建与发版 |

## 📁 项目结构

```
WBCoexist/
├── WBCoexist.pyw            GUI 主程序（--daemon / --selftest / --qoder-* / --smoke）
├── wbcore.py                WorkBuddy 核心逻辑
├── qoder.py                 Qoder 核心逻辑（检测 / 修复 / 清理 / 守护）
├── WBCoexist.bat            双击启动 GUI
├── WBCoexist-FromSource.bat 用本机 Python 跑源码（杀软拦截时的备用入口）
├── WBCoexist-Daemon.bat     直接启动无窗口后台守护
├── WBCoexist-SelfTest.bat   命令行自检
├── version_info.txt         打包用版本资源
├── app.manifest             打包用 manifest（asInvoker）
├── app.ico                  图标
├── config.json              配置（primary / guard / autostart）
├── CHANGELOG.md             更新日志
├── docs/                    截图与 logo
├── tools/
│   ├── verify_build.py      CI 产物静态校验
│   └── extract_changelog.py 从 CHANGELOG 提取 Release note
└── .github/workflows/       自动构建发布流程
```

### 本地打包

在仓库根执行，参数全部相对路径：

```bat
python -m PyInstaller --noconsole --onefile --clean --noupx --name WBCoexist ^
  --icon app.ico --version-file version_info.txt --manifest app.manifest ^
  --paths . --hidden-import wbcore --hidden-import qoder ^
  --distpath dist/onefile --workpath build/onefile --specpath . WBCoexist.pyw
```

> [!IMPORTANT]
> `--specpath` 必须指向仓库根（`.`）。PyInstaller 按 spec 所在目录解析 `--icon` / `--version-file` / `--manifest` 的相对路径，spec 放进子目录会 `FileNotFoundError`。

### 自动发版

推 `v*` 标签即触发：构建 onefile + onedir → 打包 zip → `tools/verify_build.py` 静态校验 → 从 `CHANGELOG.md` 提取对应版本作为 Release 正文 → 发布。

```bash
git tag v1.1.1 && git push origin v1.1.1
```

> CI 只构建与静态校验，**不跑 `--selftest` / `--smoke`** —— 源码里的安装路径是本机的，runner 上不存在。

---

## 🗺️ Roadmap

| 计划 | 说明 |
|:---|:---|
| 路径参数化 | 把用户目录、归档目录、两版安装路径改为可配置，便于他人复用 |
| MSIX 分享目标 | 处理 `WorkBuddyShareTarget` 同名冲突（需动 Appx 包注册，评估中） |
| 英文 README | 公开后补 `README.en.md` 与语言切换 |
| 配置界面 | 归档目录、检测间隔等在 GUI 内可改 |

---

## 🤝 贡献

Issue 与 PR 都欢迎。提交前请：

- 跑一遍 `python tools/verify_build.py dist`（如动了打包）或 `--selftest`（如动了检测逻辑）
- 改动行为请同步 `CHANGELOG.md`
- 提交信息用 `feat:` / `fix:` / `docs:` / `refactor:` 前缀

## 📄 许可

当前仓库为**私有**，尚未声明开源协议。如需对外分发，建议先补 `LICENSE`（MIT 与当前用法最匹配）。

## ⚠️ 免责声明

本工具会修改 HKCU 注册表并移动用户目录下的文件，虽已做归档而非删除，**使用前仍建议自行备份相关配置**。所有改动均可手工回退：归档包在 `D:\Users\jiangviktor\WorkBuddy\Claw\.updater-archive\`，Qoder 旧 manifest 在 `%LOCALAPPDATA%\WBCoexist\qoder-backups\`。因使用本工具造成的任何损失，作者不承担责任。

## 📜 更新日志

当前版本 **1.4.0**。完整记录见 [CHANGELOG.md](CHANGELOG.md)，发版时 CI 自动取对应版本段落作为 Release 正文。

| 版本 | 日期 | 要点 |
|:---|:---|:---|
| [1.4.0](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.4.0) | 2026-11-11 | 新增「已安装检测」，列出本机全部安装与 Qoder 历史版本目录 |
| [1.3.0](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.3.0) | 2026-11-11 | 新增安装前检查（6+ 项）与安装完成自动修复（mtime 检测） |
| [1.2.1](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.2.1) | 2026-11-11 | Qoder host 选择改为确定性规则，不再隐性偏向国际版；新增回归测试 |
| [1.2.0](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.2.0) | 2026-11-11 | 安装位置自动发现（配置 → 注册表 → 默认路径），不再绑定本机路径 |
| [1.1.1](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.1.1) | 2026-11-11 | 修复 Qoder 未运行时启动崩溃（`KeyError: 'qoder.exe'`） |
| [1.1.0](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.1.0) | 2026-11-11 | 新增 Qoder 双版本共存；8 盏灯；CI 自动发版；更名「双版共存管家」 |
| [1.0.0](https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.0.0) | 2026-11-09 | 首次发布：WorkBuddy CN / AI 双版本共存、一键修复、后台守护 |
