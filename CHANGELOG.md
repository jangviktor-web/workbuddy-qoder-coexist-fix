# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

发版时 CI 会自动从本文件提取对应版本段落，作为 GitHub Release 的正文。

## [1.4.0] - 2026-11-11

### 新增

- **已安装检测**：一键扫描本机所有 WorkBuddy / Qoder 安装，列出产品名、版本号、安装路径、是否正在运行。
  - WorkBuddy：遍历注册表卸载项（读 `DisplayVersion`）+ 常见默认路径兜底，同一路径自动去重（正反斜杠写法视为同一条）
  - Qoder：除在用两版外，还会列出 `<安装根>/.qoder-versions/` 下**未被使用**的历史版本目录
- GUI 新增「已安装」按钮，明细写日志、摘要弹窗
- `tests/test_installed.py`：6 个用例（返回类型、去重、字段完整、路径规范化）

## [1.3.0] - 2026-11-11

### 新增

- **安装前检查**（原「更新前准备」升级）：一次检查两套软件 —— 另一版是否仍在运行、更新器缓存是否残留、Qoder 共享 manifest 与 Chrome/Edge 注册是否完好、系统盘与软件盘剩余空间、各版当前版本与安装位置。给出「可以安装 / 建议先处理」的结论。
- **安装完成自动修复**：守护每 8 秒比对程序文件 mtime，发现安装器替换过 exe（即安装/更新完成）后，自动执行一次全量修复（协议归属 + 缓存归档 + Qoder 连接器），不用手动点。
- `tests/test_install_watch.py`：3 个用例覆盖基线建立、变化检测、冷启动不误报。

### 变更

- 按钮「更新前准备」更名为「安装前检查」，检查项由 2 项扩展到 6 项以上。
- `cfg_load` / `cfg_save` 改用 `with open()`，消除文件句柄未关闭告警。

## [1.2.1] - 2026-11-11

### 修复

- **Qoder host 代际选择不再隐性偏向国际版**：原逻辑已按版本号选高者，但版本并列时取列表首位（国际版在前），属隐性国别优先。改为确定性规则：当前 manifest 指向 > host 副本已存在 > 正在运行 > 哈希序，并在并列时给出提示。中国版版本反超（如 0.6.0 > 0.5.7）也能正确选择。

### 新增

- `tests/test_pick_target.py`：7 个用例覆盖版本高低、并列确定性、缺版本号、manifest 优先、运行中优先；CI 流水线增加测试步骤。

## [1.2.0] - 2026-11-11

### 变更

- **安装位置不再硬编码**：WorkBuddy 侧改为三级发现 —— 配置覆盖（`config.json` 的 `paths`）→ 注册表卸载项（按 DisplayName 匹配 `WorkBuddy` / `WorkBuddy AI`，读 `InstallLocation` / `DisplayIcon`）→ 常见默认路径兜底。装在 `%LOCALAPPDATA%\Programs\WorkBuddy` 或任意自定义目录都能识别。
- **数据与归档目录通用化**：数据目录用 `~/.workbuddy` / `~/.workbuddy-ai`；归档默认跟随 exe 所在目录（`<软件目录>/.updater-archive`），可用 `archive_dir` 覆盖。
- **GUI 去掉本机绝对路径**：`sys.path`、`selftest.txt`、`qoder-cli.txt` 全部改为相对软件目录。
- 开机自启命令指向软件自身（exe 或源码），不再写死 Python 路径。
- 配置新增 `paths`（CN / AI 的 exe 路径覆盖）与 `archive_dir` 两个可选字段。

## [1.1.1] - 2026-11-11

### 修复

- **修复 Qoder 未运行时启动即崩溃**：`detect_intl` / `detect_cn` 对进程字典使用硬索引，Qoder 完全退出时抛 `KeyError: 'qoder.exe'`，导致 GUI 启动瞬间退出（表现为「下载的 exe 打不开」）。改为 `.get(key, [])`。

## [1.1.0] - 2026-11-11

### 新增

- **Qoder 双版本共存**：新增 `qoder.py`，处理中国版 0.5.2 与国际版 0.5.7 共用的 browser-connector 冲突
  - 共享 manifest 固定指向较新版本的 host 副本，同时保留两个 `allowed_origins`
  - host 副本按启动器 SHA-256 分代，缺失时自动补建
  - Chrome / Edge `NativeMessagingHosts` 注册写回 HKCU 正确路径
  - 「清理孤儿」删除旧代际 host 与失效中继记录（删除前弹确认）
- GUI 从 4 盏状态灯扩展到 8 盏（WorkBuddy 4 + Qoder 4）
- 新增命令行：`--qoder-check` / `--qoder-fix` / `--qoder-clean` / `--smoke`
- 新增 GitHub Actions 自动构建发版：推 `v*` 标签即构建单文件 exe 与便携版 zip 并发布 Release
- 新增 `tools/verify_build.py`：校验版本资源、manifest、未压缩、大小与 SHA-256

### 变更

- 产品更名为「双版共存管家」，明确是**同一软件的国内版与国际版共存**，而非两个不同软件之间共存
- README 重排：首屏价值主张、徽章、目录、适用/不适用判断表、FAQ 折叠
- 发布加固：完整版本资源 1.1.0.0、`asInvoker` manifest（不请求管理员）、`--noupx` 禁用压缩、onedir 便携版、源码启动备用入口

### 修复

- 修复 CI 中 PyInstaller 因 `--specpath` 指向子目录、导致 `--manifest` 相对路径解析失败的 `FileNotFoundError`
- 修正 README 状态灯数量表述（WorkBuddy 侧 4 盏 + Qoder 侧 4 盏）

### 已知限制

- MSIX 分享目标 Identity 同名未处理，仅影响系统「分享到」功能
- 源码中的安装路径与用户目录为本机硬编码，换机器或对外分发前需先参数化
- CI 只做构建与静态校验，不运行 `--selftest` / `--smoke`

## [1.0.0] - 2026-11-09

### 新增

- WorkBuddy CN 5.9.3 与 AI 国际版 5.9.4 双版本共存支持
  - `buddy-app://` 协议归属修复
  - 更新器缓存 `installer.exe` 陈旧包归档
- Tkinter GUI：4 盏状态灯、一键修复、重新体检、更新前准备
- 后台守护（8 秒轮询，自动纠回被抢占的协议）与开机自启
- PyInstaller 单文件 exe：免安装、无需本机 Python、无需管理员权限

[1.4.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.2.1...v1.3.0
[1.2.1]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.2.0...v1.2.1
[1.2.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.0.0
