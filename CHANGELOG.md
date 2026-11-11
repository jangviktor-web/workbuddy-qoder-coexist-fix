# 更新日志

本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/)，格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)。

发版时 CI 会自动从本文件提取对应版本段落，作为 GitHub Release 的正文。

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

[1.1.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/jangviktor-web/workbuddy-qoder-coexist-fix/releases/tag/v1.0.0
