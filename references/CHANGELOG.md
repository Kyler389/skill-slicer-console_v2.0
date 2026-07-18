---
type: session-note
project: slicer_module
title: slicer-console skill 自动检测部署
created: "2026-07-19"
tags:
  - session-note
  - slicer-module
  - slicer-console
  - auto-detection
---

# slicer-console skill 自动检测部署

## 完成内容

1. **创建 `slicer_detect.py`** — 8 策略自动检测引擎（env var → 常见路径 → 注册表 → PATH → Program Files → 驱动器根 → Spotlight）
2. **重写 `run_slicer_script.py`** — 导入 `slicer_detect` 替代硬编码路径，支持 `SLICER_PATH`/`SLICER_ROOT` 环境变量
3. **重写 `setup_checker.py`** — 显示检测结果、环境变量提示、`--verbose` 模式展示全部策略
4. **更新 `skill.md`** — 新增 Auto-Detection 章节，文档化 8 种策略和环境变量设置方法

## 检测结果

部署到本机（Windows 10）：
- `D:\slicer\3D Slicer 5.10.0\Slicer.exe` — ✅ 策略 3（Common install paths）
- `D:\slicer\3D Slicer 5.10.0\bin\PythonSlicer.exe` — ✅ 自动推导

## 相关笔记

- [[SlicerAgentController 开发环境]] — Slicer 5.10 路径和启动方式
- [[Python Console — 内置插件]] — PythonConsoleTask 实现

---

## 2026-07-20: P0+P1 修复

### P0 阻塞修复
1. **超时处理** — `subprocess.TimeoutExpired` 捕获 + `_kill_slicer()` 自动清理僵尸进程
2. **Slicer 自动退出** — 脚本末尾注入 `slicer.app.quit()`，`--no-quit` 可禁用
3. **默认超时** 120s → 300s

### P1 自动化升级
4. **run/launch 模式拆分** — `--mode run`（执行脚本+退出）和 `--mode launch`（启动 GUI）
5. **`$SLICER_RESULT_FILE`** — 环境变量支持可靠的文件式输出捕获
6. **`--select-module`** — launch 模式下自动加载并选中指定模块
7. **`--module-paths`** — 外部模块搜索路径（文档完善）

## 2026-07-20: P2 跨平台补全

8. **Linux AppImage 扫描** — `_from_unix_common_dirs()` 新增 `~/Downloads/`、`~/Desktop/`、`/opt/` 下的 `*Slicer*.AppImage` 可执行文件检测
9. **macOS /Volumes 扫描** — 检测挂载的 .dmg 中的 `Slicer.app` bundle
10. **文档 update** — skill.md 策略表 + AppImage 注意事项（`--appimage-extract` 需要）

## 2026-07-20: P3 健壮性

11. **`--kill-existing`** — 启动前自动 `_kill_slicer()` 清理旧进程 + 1.5s 等待锁释放
12. **config.json 校验** — `_validate_config()` 确保 method 字段值有效，无效自动回退 auto-detect
13. **setup_checker `--fix`** — 自动 `pip install jupyter_client` + 检测结果汇总

## 2026-07-20: P4 体验

14. **进度心跳** — Slicer 启动时每 15s 打印 `[INFO] Slicer still running... (Ns / Ns)`
15. **脚本模板** — `scripts/templates/segmentation.py`（分割）、`prediction.py`（推理）、`data_io.py`（导入导出）
16. **`--version`** — 从安装目录名解析版本号（不启动 Slicer） + Windows 二进制版本回退
