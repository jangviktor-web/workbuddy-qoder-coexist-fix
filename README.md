# WorkBuddy · Qoder 共存管家 v1.1


![WorkBuddy · Qoder 共存管家 v1.1 主界面](docs/screenshot.webp)

> 图中 8 盏状态灯全绿：WorkBuddy 侧（CN 版 / AI 版 / buddy-app 归属 / 更新器缓存）与
> Qoder 侧（国际版 / 中国版 / 共享连接器代际 / native messaging 注册）均无异常。
> 体检结果提示的是 Qoder 两版版本号不同（0.5.7 / 0.5.2），属信息提示而非故障。

解决「同一套代码、两个发行版」在更新后互相把对方资源抢走的问题：

- **WorkBuddy**：CN 5.9.3 与 AI 国际版 5.9.4
- **Qoder**：中国版 0.5.2 与国际版 0.5.7

## 一键用法

双击 WBCoexist.exe（或开始菜单 WBCoexist）→ 点「一键修复」→ 完事。
软件启动即自动体检，8 个状态灯全绿表示两套软件的四项共享资源都正常。

## 为什么需要它

### WorkBuddy：3 个全局资源没有按产品隔离

| 资源 | 冲突表现 | 软件的处理 |
|:---|:---|:---|
| 更新器缓存 %LOCALAPPDATA%\@genieworkbuddy-desktop-updater\installer.exe | 两版共用同一路径，更新时残留另一版安装包 → 竞态/装错版本 | 一键修复时归档到 D 盘（不删除，可回退） |
| URL 协议 buddy-app:// | 两版都注册同名 scheme，后更新者覆盖唤起目标 | 一键修复固定回约定版本；后台守护自动修回 |
| MSIX 分享目标 Identity 同名 | 只影响「分享到」功能 | 不在本软件处理范围 |

另有 ~/.workbuddy-key-fallback 共享凭证目录，只读观察，不改动。

### Qoder：共用一个 browser-connector

| 资源 | 冲突表现 | 软件的处理 |
|:---|:---|:---|
| 共享 manifest ~/.qoder/browser-connector/com.qoder.app.connector.json | 两版扩展 ID 都要用，manifest 的 path 指向单一 host | 固定指向「版本较新」那一版的 host 副本，同时保留两个 allowed_origins |
| host 副本 hosts/<启动器 sha256>/ | 两版启动器代际不同（CN 0.5.2 / 国际版 0.5.7），谁最后启动就写谁的 | 以两版版本号较大者为基准代际；缺失时自动补建副本 |
| Chrome / Edge NativeMessagingHosts 注册 | 指向错误 manifest 时浏览器扩展连不上 | 一键修复写回 HKCU 正确路径 |
| 中继记录 clients/qoder-<uuid>.json | 进程退出后留下失效记录 | 「清理孤儿」删除失效记录与旧代际 host |

版本不同期间（例如 CN 仍是 0.5.2）连接器会在两边启动时来回切换，属于**提示**而非错误；
两边都升到同一版本并各启动一次后自然收敛。

## 界面导览

| 区域 | 内容 |
|:---|:---|
| WorkBuddy 状态（4 灯） | CN 5.9.3 与 AI 5.9.4 的安装完整性、`buddy-app://` 归属、更新器缓存是否干净 |
| Qoder 状态（4 灯） | 国际版 / 中国版版本与运行状态、共享连接器当前指向的 host 代际、Chrome / Edge native messaging 注册 |
| 体检结果行 | 汇总待处理项与提示项；全绿即两套软件共存正常 |
| 选项行 | `buddy-app://` 归属（CN / AI）、后台守护、开机自启 |
| 主按钮 | **一键修复** —— 一次处理 WorkBuddy 协议与缓存、Qoder manifest / host 代际 / 浏览器注册 |
| 辅助按钮 | 重新体检、更新前准备、清理孤儿（删除前弹确认框） |
| 日志区 | 每次体检与修复的动作留痕，同时写入 `run.log` |

## 功能

- 一键修复：WorkBuddy 修 buddy-app 归属 + 归档陈旧缓存；Qoder 修 manifest / host 代际 / Chrome·Edge 注册，完成后自动复检并弹结果
- 重新体检：刷新 8 盏状态灯
- 更新前准备：检查另一版是否完全退出、缓存是否干净，并列出 Qoder 两版版本与运行状态
- 清理孤儿：删除 Qoder 旧代际 host 副本与失效中继记录（先弹确认框）
- buddy-app 归属：单选 CN / AI 国际版，决定协议由谁接管（默认 CN）
- 后台守护：窗口开着时每 8 秒同时检测 WorkBuddy 与 Qoder，被抢占自动修回（只修共享指向，不碰缓存、不做清理）
- 开机自启：写 HKCU Run，开机以无窗口守护模式常驻，更新完不用手动点

## 推荐的更新 SOP

1. 更新任一版前：另一版完全退出（不只是关窗口），点「更新前准备」检查
2. 正常更新
3. 更新完成后：点一次「一键修复」（若已开开机自启，守护会自动修回，可省略）
4. Qoder 两版都到同一版本后：各启动一次，让连接器代际收敛

## 文件

| 文件 | 作用 |
|:---|:---|
| WBCoexist.pyw | GUI 主程序（含 --daemon / --selftest / --qoder-* 命令行） |
| wbcore.py | WorkBuddy 核心逻辑 |
| qoder.py | Qoder 核心逻辑（检测 / 修复 / 清理 / 守护） |
| WBCoexist.bat | 双击启动 GUI |
| WBCoexist-FromSource.bat | 用本机 Python 直接跑源码（不经过 exe，杀软拦截时的备用入口） |
| WBCoexist-Daemon.bat | 直接启动无窗口后台守护 |
| WBCoexist-SelfTest.bat | 命令行自检 |
| version_info.txt | 打包用版本资源（公司/产品/版本号） |
| app.manifest | 打包用 manifest（asInvoker、Win10/11 兼容声明） |
| config.json | 配置 |
| run.log | 运行日志 |

无窗口命令行（结果同时写入文本文件）：

| 参数 | 作用 |
|:---|:---|
| --selftest | 两套软件的完整体检 + 修复预览（写 selftest.txt） |
| --qoder-check | Qoder 完整诊断 JSON（写 qoder-cli.txt） |
| --qoder-fix | 立即修复 Qoder 共享连接器 |
| --qoder-clean | 删除 Qoder 孤儿 host 与失效中继记录 |

## 运行环境与局限

- **独立 exe 不依赖本机 Python**，无需联网、无需管理员权限、无需安装；仅「用源码直接运行」时才需要 D:\Python310\pythonw.exe（3.10.6，自带 tkinter）。
- 修复只写 HKCU 注册表、用户目录与 D 盘文件，不动系统目录。
- WorkBuddy 属缓解而非根治：改不了应用内部硬编码的共享路径，所以更新后仍需修一次（或靠守护自动修）。
- Qoder 同理：manifest 会被任一版启动器按自己的代际重写，守护负责在 8 秒内纠回。
- MSIX 分享目标同名未处理，影响面仅限系统分享功能。
- WorkBuddy 归档安装包保存在 D:\Users\jiangviktor\WorkBuddy\Claw\.updater-archive\，需要时可放回。
- Qoder 旧 manifest 备份保存在 %LOCALAPPDATA%\WBCoexist\qoder-backups\。

## 杀毒软件误报

PyInstaller 单文件 exe 运行时会把自身解压到 %TEMP%\_MEIxxxx 再执行，这个行为是 360 等国产杀软启发式引擎的高发误报点；
文件又没有数字签名，容易被判为可疑。已做的加固与建议按顺序使用：

1. **优先用 onedir 版**：`portable\WBCoexist\WBCoexist.exe`，不再自解压，误报概率显著低于单文件。
   把整个 `portable\WBCoexist` 文件夹加入 360 信任区（木马查杀 → 信任区 → 添加信任目录），
   或直接在该文件夹内双击运行。onedir 版需要连同 `_internal` 文件夹一起移动，不能只拷 exe。
2. **单文件版被拦截时**：360 木马查杀 → 信任区 → 添加信任文件，选中 `D:\Apps\WBCoexist\WBCoexist.exe`；
   若已被隔离，先到「恢复区」恢复再添加。
3. **提交误报**：用 360 安全卫士内的「误报反馈」入口，说明用途（本机双版本软件共存修复工具、源码可查、
   只写 HKCU 与用户目录），附 SHA-256。注意每次重新打包哈希都会变，需要重新提交。

已做的降低误报措施：嵌入完整版本资源（公司/产品/描述/1.1.0.0）、自定义 manifest（asInvoker，不请求管理员）、
`--noupx` 禁用压缩，均不改变程序行为，只是让文件看起来像一个正常发布的软件。
本机验证：Defender 全量扫描两种构建均 `found no threats`；360 未拦截。

实在被拦又不想加白时，可直接跑源码（不产生任何 exe）：
`D:\Python310\pythonw.exe D:\Apps\WBCoexist\WBCoexist.pyw`，或双击 `WBCoexist-FromSource.bat`。

## 独立 EXE（推荐）

`WBCoexist.exe` 已用 PyInstaller 6.22.3 打包为单文件、无控制台窗口，自带 Python 3.10 与 tcl/tk 运行时，
**不依赖本机 Python、无需安装、无需管理员权限**，双击即可运行（约 9.5 MB）。
启动器 WBCoexist.bat、后台守护 bat、开始菜单入口均已改为指向该 exe。

同时提供 onedir 发行包 `portable\WBCoexist\`（约 23 MB，exe 1.2 MB + `_internal`），不自解压、误报更少。

验证记录：exe --selftest 输出正确（含 QODER_CHECK / QODER_FIX_PREVIEW / QODER_DAEMON_TICK）；
exe --smoke（GUI 构建后自动关闭）退出码 0；portable 版 --smoke 退出码 0；GUI 截图确认 8 盏灯渲染正常。
命令行自检结果写入 selftest.txt（noconsole 无控制台输出）。

重新打包命令（如需改代码后重建）：
TEMP/TMP 指向 D 盘构建目录，然后

单文件：
python -m PyInstaller --noconsole --onefile --clean --noupx --name WBCoexist --icon D:/Apps/WBCoexist/app.ico --version-file D:/Apps/WBCoexist/version_info.txt --manifest D:/Apps/WBCoexist/app.manifest --paths D:/Apps/WBCoexist --hidden-import wbcore --hidden-import qoder --distpath D:/Apps/WBCoexist --workpath _build/work --specpath _build WBCoexist.pyw

onedir：
python -m PyInstaller --noconsole --onedir --clean --noupx --name WBCoexist --icon D:/Apps/WBCoexist/app.ico --version-file D:/Apps/WBCoexist/version_info.txt --manifest D:/Apps/WBCoexist/app.manifest --paths D:/Apps/WBCoexist --hidden-import wbcore --hidden-import qoder --distpath D:/Apps/WBCoexist/portable --workpath _build/work-dir --specpath _build-dir WBCoexist.pyw

## GitHub Actions 自动构建与发布

仓库内置 `.github/workflows/build-release.yml`，在 `windows-latest` runner 上用 Python 3.10 + PyInstaller 6.22.3 构建，产物自动发到 Release。

**触发方式（二选一）**

1. 打标签推送（推荐）：`git tag v1.1.0 && git push origin v1.1.0`
2. GitHub → Actions → `Build and Release` → Run workflow，填 tag 后手动运行

**每次发布的两个资产**

| 资产 | 说明 |
|:---|:---|
| `WBCoexist-<tag>.exe` | 单文件版，双击即用 |
| `WBCoexist-portable-<tag>.zip` | onedir 便携版；解压后需整个文件夹一起移动，不能只拷 exe |

**流水线**：checkout → setup-python 3.10 → 安装 PyInstaller / pefile → `py_compile` 语法检查 → onefile 构建 → onedir 构建 → 打包 zip → `tools/verify_build.py` 静态校验（版本资源、manifest、未压缩、文件大小、SHA-256）→ 发布 Release（自动生成 notes）。

**限制与注意**

- CI **只做构建与静态校验，不跑 `--selftest` / `--smoke`**：源码里 WorkBuddy / Qoder 的安装路径是作者本机的，runner 上不存在；运行时自检请在本机完成。
- 打包命令在 CI 内全部使用相对路径，不依赖任何本机绝对路径：`--icon app.ico --version-file version_info.txt --manifest app.manifest --paths .`。上面「重新打包命令」里的绝对路径版本仅供本机使用，在仓库根目录运行时可整套替换为相对路径。
- 私有仓库使用 GitHub Actions 会消耗额度：Free 账号每月 2000 分钟，Windows runner 按 2 倍计费；单次构建约 3–6 分钟，折合约 6–12 分钟额度。
- 本地可模拟校验：`python tools/verify_build.py dist`（需先把两种构建的 exe 与 zip 放进 `dist/`）。
- **分发限制**：源码里的用户目录、D 盘归档路径与两版安装路径仍是作者本机硬编码。CI 能成功构建出可执行的 exe，但他人机器上的路径布局不同时，配置保存与检测会退化；若要真正对外分发，需先把这些路径参数化。
