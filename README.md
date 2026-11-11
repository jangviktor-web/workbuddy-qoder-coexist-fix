# WorkBuddy 共存管家 v1.0

解决 WorkBuddy CN 5.9.3 与 WorkBuddy AI 5.9.4 更新后互相不可用的问题。

## 一键用法

双击 WBCoexist.bat（或开始菜单 WBCoexist）→ 点「一键修复」→ 完事。
软件启动即自动体检，四个状态灯全绿表示两版共存正常。

## 为什么需要它

两版是同一套代码、不同 productName 配置，但有 3 个全局资源没按产品隔离：

| 资源 | 冲突表现 | 软件的处理 |
|:---|:---|:---|
| 更新器缓存 %LOCALAPPDATA%\@genieworkbuddy-desktop-updater\installer.exe | 两版共用同一路径，更新时残留另一版安装包 → 竞态/装错版本 | 一键修复时归档到 D 盘（不删除，可回退） |
| URL 协议 buddy-app:// | 两版都注册同名 scheme，后更新者覆盖唤起目标 | 一键修复固定回约定版本；后台守护自动修回 |
| MSIX 分享目标 Identity 同名 | 只影响「分享到」功能 | 不在本软件处理范围 |

另有 ~/.workbuddy-key-fallback 共享凭证目录，只读观察，不改动。

## 功能

- 一键修复：修 buddy-app 归属 + 归档陈旧更新缓存，完成后自动复检并弹结果
- 重新体检：刷新四盏状态灯
- 更新前准备：检查另一版是否完全退出、缓存是否干净，给出 SOP 提示
- buddy-app 归属：单选 CN / AI 国际版，决定协议由谁接管（默认 CN）
- 后台守护：窗口开着时每 8 秒检测，被抢占自动修回（只修协议，不碰缓存）
- 开机自启：写 HKCU Run，开机以无窗口守护模式常驻，更新完不用手动点

## 推荐的更新 SOP

1. 更新任一版前：另一版完全退出（不只是关窗口），点「更新前准备」检查
2. 正常更新
3. 更新完成后：点一次「一键修复」（若已开开机自启，守护会自动修回，可省略）

## 文件

| 文件 | 作用 |
|:---|:---|
| WBCoexist.pyw | GUI 主程序（含 --daemon / --selftest） |
| wbcore.py | 核心逻辑 |
| WBCoexist.bat | 双击启动 GUI |
| WBCoexist-Daemon.bat | 直接启动无窗口后台守护 |
| WBCoexist-SelfTest.bat | 命令行自检 |
| config.json | 配置 |
| run.log | 运行日志 |

## 运行环境与局限

- 依赖 D:\Python310\pythonw.exe（3.10.6，自带 tkinter），无需联网、无需管理员权限、无需安装。
- 修复只写 HKCU 注册表与 D 盘文件，不动系统目录。
- 属缓解而非根治：改不了应用内部硬编码的共享路径，所以更新后仍需修一次（或靠守护自动修）。
- MSIX 分享目标同名未处理，影响面仅限系统分享功能。
- 归档的安装包保存在 D:\Users\jiangviktor\WorkBuddy\Claw\.updater-archive\，需要时可放回。

## 独立 EXE（推荐）

`WBCoexist.exe` 已用 PyInstaller 6.22.3 打包为单文件、无控制台窗口，自带 Python 3.10 与 tcl/tk 运行时，
**不依赖本机 Python、无需安装、无需管理员权限**，双击即可运行（约 9.1 MB）。
启动器 WBCoexist.bat、后台守护 bat、开始菜单入口均已改为指向该 exe。

验证记录：exe --selftest 输出正确；exe --smoke（GUI 构建后自动关闭）退出码 0，确认 tkinter 运行时完整。
命令行自检结果写入 selftest.txt（noconsole 无控制台输出）。

重新打包命令（如需改代码后重建）：
TEMP/TMP 指向 D 盘构建目录，然后
python -m PyInstaller --noconsole --onefile --clean --name WBCoexist --icon app.ico --paths D:/Apps/WBCoexist --hidden-import wbcore --distpath D:/Apps/WBCoexist --workpath _build/work --specpath _build WBCoexist.pyw
