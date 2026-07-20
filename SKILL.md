---
name: slicer-console
description: >
  Execute Slicer Python scripts via direct Slicer.exe --python-script,
  PythonSlicer.exe headless, or Jupyter kernel fallback.
  Triggered when user mentions "slicer console", "slicer python", "slicer 脚本",
  "在 slicer 里运行", "slicer 计算", or similar.
---

# slicer-console

Execute Slicer Python scripts via multiple backends. The skill auto-selects the best available method.

## Execution Methods

| # | Method | Command | Speed | GUI | Requires |
|---|--------|---------|-------|-----|----------|
| 1 | **Direct Slicer.exe** (Primary) | `Slicer.exe --no-splash --python-script <path>` | 20–40s | Brief flash | Slicer installed |
| 2 | **PythonSlicer.exe** (Headless) | `PythonSlicer.exe <path>` | 5–15s | None | Slicer installed |
| 3 | **Jupyter Kernel** (Fallback) | `jupyter_client` KernelManager | 20–40s | None | Kernel spec + jupyter_client |

The runner script auto-detects which method to use:
- **Method 1** (default): Most reliable, full Slicer environment, proven by SlicerAgentController project.
- **Method 2**: For lightweight scripts that only need Slicer Python APIs without GUI.
- **Method 3**: When you need headless + don't want a new Slicer process each time.

## 核心流程准则 (Core Workflow Guidelines)

为提升执行效率，使用本 skill 时**必须**遵循以下流程：

### 1. 先启动 Slicer，再执行脚本

**禁止**每次需要执行命令时都重新启动一个新 Slicer 进程（20–40s 启动时间浪费严重）。

| 阶段 | 操作 | 说明 |
|------|------|------|
| **首次** | `--mode launch` 启动 Slicer 并保持打开 | Slicer GUI 启动后保持运行 |
| **后续** | 利用**同一 Slicer 实例**的 Python Console 执行脚本 | 避免重复启动开销 |
| **收尾** | 执行完毕清理临时脚本（除非可复用） | 见下方清理规则 |

### 2. Python Console 执行方式

脚本通过 **Slicer Python Console**（Slicer 内置交互式 Python 解释器）执行：

- **`--python-script`（推荐）**：通过 `Slicer.exe --python-script <script>` 将脚本送入 Python Console 执行。首次用 `--mode launch` 启动 Slicer，后续对于需要大量交互的新会话再用 `run` 模式（但仍会启动新进程——属于第二阶段优化目标）。
- **Jupyter kernel**：对于已启动的 Slicer，若安装了 SlicerJupyter 扩展，可通过 `--method jupyter` 向运行中的 Python Console 发送代码，**完全免重启**。（最佳效率，但需额外配置）

> 目标：**一次启动，多次执行**。后续版本可考虑为运行中的 Slicer 添加 socket/IPC 监听机制，实现真正的免重启脚本注入。

### 3. 临时脚本清理规则

所有写入 `.slicer_temp/` 的脚本**执行完毕后必须清理**，除非标记为可复用：

| 条件 | 处理方式 |
|------|----------|
| 一次性任务（计算/转换/查询） | 执行后**立即删除** `.slicer_temp/task_*.py` |
| 可复用模板（通用流程/工具函数） | **迁移**到 `scripts/templates/` 并命名意义明确 |
| 用户明确要求保留 | 保留并告知用户路径 |

清理命令示例：
```bash
# 清理所有临时脚本
rm -f ./.slicer_temp/task_*.py
# 或清理单个
rm -f ./.slicer_temp/task_<timestamp>.py
```

### 4. 关于 `--mode launch` 的正确使用

- `--mode launch` 用于**长期保持 Slicer 运行**，适合需要多次执行脚本的会话
- `--mode run` 用于**执行脚本后自动退出**，适合单次一次性任务
- 建议：skill 被调用时如果预期会执行多次命令**优先使用 launch 模式启动**

---

## Action

### 0. Method Selection (First-Time Only)

Before executing any script, check the saved configuration:

1. **Read** `config.json` at `~/.claude/skills/slicer-console/scripts/config.json`
2. **If config exists** with a `"method"` key → use it silently
3. **If no config** → present the user with method options:

   | # | Method | Speed | GUI | Reliability | Best For |
   |---|--------|-------|-----|------------|----------|
   | 1 | **direct** — `Slicer --no-splash --python-script` | 20–40s | Brief flash | ★★★★★ | Default, most compatible |
   | 2 | **pythonslicer** — `PythonSlicer.exe` / `python-real` | 5–15s | None | ★★★★☆ | Headless batch processing |
   | 3 | **jupyter** — Jupyter kernel via `jupyter_client` | 20–40s | None | ★★★☆☆ | Legacy, requires kernel setup |

   Ask the user to pick one, then **save** to `config.json`:
   ```json
   {"method": "direct", "updated": "2026-07-19T..."}
   ```

   The user can override their saved choice at any time with `--method <name>`.

### 1. Write Script

1. **Write a Python script** that solves the user's request using `slicer`, `vtk`, `mrml`, and related Slicer APIs.
2. **Save the script** to `./.slicer_temp/task_<timestamp>.py`. Create the `.slicer_temp` directory if it does not exist.
3. **Run the script** using the unified connector:
   ```bash
   python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --mode run --script ./.slicer_temp/task_<timestamp>.py
   ```
   The runner reads the saved method from `config.json` automatically. Optional overrides:
   - `--mode run` — execute script and auto-quit (default)
   - `--mode launch` — start Slicer GUI and keep open (e.g. for module testing)
   - `--method direct` — `Slicer --python-script` (default for new installs)
   - `--method pythonslicer` — `PythonSlicer` / `python-real` headless
   - `--method jupyter` — Jupyter kernel fallback
   - `--slicer-path "D:/path/to/Slicer.exe"` — override Slicer executable
   - `--module-paths "path1;path2"` — additional module search paths (for external modules)
   - `--select-module "ModuleName"` — select a module on startup (for --mode launch)
   - `--quit` / `--no-quit` — auto-quit Slicer after script (default: --quit)
   - `--kernel slicer-5.6` — kernel name for jupyter method (default: slicer-5.6)
   - `--timeout 300` — timeout in seconds (default: 300)
   - `--version` — detect and print Slicer version (without launching Slicer)
   - `--kill-existing` — kill running Slicer processes before starting
4. **Return the output** to the user and report the script path.

### Examples

```bash
# Default: execute script and auto-quit (recommended)
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --mode run --script ./.slicer_temp/task_001.py

# Launch Slicer GUI with an external module loaded
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --mode launch --module-paths "F:\slicer_module\SlicerAgentController" --select-module SlicerAgentController

# Headless method (no GUI)
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --mode run --method pythonslicer --script ./.slicer_temp/task_001.py

# Jupyter kernel fallback
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --mode run --method jupyter --script ./.slicer_temp/task_001.py --kernel slicer-5.6
```

## Scripting Conventions

Based on learnings from the SlicerAgentController project and Slicer 5.10 Python 3.12 environment:

### Absolute paths
Always use absolute paths for input/output files inside the script — Slicer's working directory may differ from yours.

### Result printing
Use `print("RESULT:", value)` so the caller can easily parse key outputs.

### Structured output via `$SLICER_RESULT_FILE`
For reliable output capture (especially on Windows where GUI app stdout can be lost),
the runner sets the `SLICER_RESULT_FILE` environment variable pointing to a temp file.
Scripts can write structured results there, and the runner will read and display them
after Slicer exits:

```python
import os, json
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    with open(result_file, "w") as f:
        f.write(json.dumps({"status": "ok", "volume": "Sample"}))
```

### API fallback patterns
If a direct Slicer API method raises `AttributeError`, fall back to `slicer.modules.<moduleName>.logic()` methods, or export to labelmap/volume nodes first.

### No GUI interaction
For `--python-script` mode: scripts run with a briefly visible Slicer window — do not open dialog boxes (`qt.QMessageBox`, file dialogs) as they will block execution.

For `PythonSlicer.exe` mode: no GUI at all. VTK render window operations will fail.

### Templates

Ready-to-use script templates are at `scripts/templates/`:

| Template | Description |
|----------|-------------|
| `segmentation.py` | Load volume, create segmentation, export `.seg.nrrd` |
| `prediction.py` | ML inference pipeline (placeholder) |
| `data_io.py` | List/nodes, export/import volumes |

Usage: `python run_slicer_script.py --mode run --script templates/segmentation.py`

### Slicer Python 3.12 specifics (Slicer 5.10)
- Slicer 5.10 ships Python 3.12.10
- `slicer.util` methods for array access: `arrayFromVolume()`, `arrayFromVolumeModified()`
- `PythonQt` vs `PyQt` differences: `QScrollBar.maximum`, `QTreeWidgetItem.childCount`, `QSpinBox.value`, `QLabel.text` are **properties not methods** — check with `callable()` before calling
- `slicer.modules` attribute names are **lowercase module names**
- `QWidget.layout` is a **property** — do not call `self.layout()`, store layout as `self._layout = qt.QVBoxLayout(self)` instead
- For custom QWidget subclasses: **never override virtual functions** (`resizeEvent`, `mouseDoubleClickEvent`), use `installEventFilter(self)` instead
- Avoid `setParent(None) + deleteLater()` on Python QWidget subclasses — causes double-free crash. Use `layout.removeWidget(w) + w.hide()` instead

### Worker thread safety
If the script spawns threads, worker threads must **never** directly touch Qt/VTK/Slicer nodes. Marshal all GUI/scene operations to the main thread (e.g., via `slicer.app.processEvents()` or custom event queues).

### Example
```python
import slicer

# List all volumes
for vol in slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode"):
    name = vol.GetName()
    dims = vol.GetImageData().GetDimensions() if vol.GetImageData() else (0, 0, 0)
    print(f"  Volume '{name}': dimensions = {dims}")

# Create a sample volume
import numpy as np
node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "Sample")
voxels = slicer.util.arrayFromVolume(node)
voxels[:] = 100
slicer.util.arrayFromVolumeModified(node)
print("RESULT: done")
```

## Auto-Detection

The skill includes a multi-strategy auto-detection engine (`scripts/slicer_detect.py`) that locates Slicer on any machine without configuration.

### Detection Strategies (in order)

| # | Strategy | Speed | Platforms | Description |
|---|----------|-------|-----------|-------------|
| 1 | `SLICER_PATH` env var | Instant | All | Full path to Slicer executable |
| 2 | `SLICER_ROOT` env var | Instant | All | Directory containing Slicer executable |
| 3 | Common install paths | Instant | Win/Mac/Linux | Well-known paths for all Slicer versions |
| 4 | Windows Registry | Fast | Win | Queries `HKLM\SOFTWARE\Slicer` and related keys |
| 5 | `PATH` scan | Fast | All | Checks if Slicer is on system PATH |
| 6 | Unix dirs + AppImage + /Volumes scan | Slow | Linux/Mac | Scans `/opt/`, `/usr/local/`, `/Applications/`, `~/`; Linux `*Slicer*.AppImage` in `~/Downloads/`; macOS `/Volumes/` for mounted .dmg |
| 7 | Program Files scan | Slow | Win | Walks `%PROGRAMFILES%` looking for `*Slicer*` dirs |
| 8 | Drive root scan | Slow | Win | Checks `C:\`, `D:\`, etc. for Slicer directories |
| 9 | macOS Spotlight | Slow | Mac | Uses `mdfind` to locate Slicer.app bundles |

**Fast mode** (strategies 1–5) runs by default. Slow fallbacks only activate when fast mode can't find Slicer.

**Cross-platform**: The same skill works on Windows, macOS, and Linux without modification. Platform-specific strategies are guarded by `platform.system()` and only activate on the relevant OS.

### Setting a Permanent Path

If auto-detection doesn't find Slicer on your machine, set one of these env vars:

```bash
# Windows (Command Prompt)
setx SLICER_PATH "D:\slicer\3D Slicer 5.10.0\Slicer.exe"

# Windows (PowerShell)
[Environment]::SetEnvironmentVariable("SLICER_PATH", "D:\slicer\3D Slicer 5.10.0\Slicer.exe", "User")

# macOS / Linux
export SLICER_PATH="/Applications/Slicer.app/Contents/MacOS/Slicer"
```

Or set the directory:
```bash
setx SLICER_ROOT "D:\slicer\3D Slicer 5.10.0"
```

### Prerequisites (External Python)
The runner script runs in your external Python (not Slicer's Python). It needs:
- **Python 3.8+** — any environment
- **`jupyter_client`** — only needed for `--method jupyter` fallback

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Slicer not found` | Not installed or path not detected | Pass `--slicer-path`, set `SLICER_PATH` env var, or run `setup_checker.py` |
| Slicer exits with code 0 but no output | Script may have syntax error in Slicer's Python | Check script for Python 3.12 compatibility |
| `ModuleNotFoundError: No module named 'IPython'` | Jupyter method without IPython in Slicer's Python | Use `--method direct` instead, or install IPython in Slicer Python |
| `NoSuchKernel: No such kernel named slicer-5.6` | Jupyter kernel not registered | Use `--method direct` instead (recommended) |
| Script hangs after execution | Slicer window stays open | Use `--mode run` (auto-quits). Or pass `--no-quit` to keep open intentionally. |
| Qt errors about `setParent` / `deleteLater` | PythonQt teardown double-free | Use `layout.removeWidget(w) + w.hide()` instead |
| `--additional-module-paths` has no effect on Linux | AppImage is read-only filesystem | Extract AppImage first: `./Slicer*.AppImage --appimage-extract && ./squashfs-root/AppRun` |
| `AttributeError` on slicer API | Using C++ method that moved | Fall back to `slicer.modules.*.logic()` or `slicer.util.*` |
| `QWidget.layout` call crashes | Layout accessed as method not property | Use `self._layout` member variable instead |

## Diagnostics

Run the setup checker to verify your environment:

```bash
python ~/.claude/skills/slicer-console/scripts/setup_checker.py
```

For detailed strategy-by-strategy detection results:
```bash
python ~/.claude/skills/slicer-console/scripts/setup_checker.py --verbose
```

It checks:
- Slicer executable (auto-detected via 8 strategies, or overridable via `SLICER_PATH` env var)
- PythonSlicer executable
- `jupyter_client` (for jupyter fallback method)
- `slicer-5.6` kernel registration (optional fallback)

### Diagnostic: Test detection directly

```bash
python ~/.claude/skills/slicer-console/scripts/slicer_detect.py
```

## Method Details

### Method 1: Direct Slicer.exe (--python-script)

The most reliable method. Launches Slicer with `--python-script` flag — Slicer starts, executes the script, and exits.

```bash
# Equivalent manual command:
"D:\slicer\3D Slicer 5.10.0\Slicer.exe" --no-splash --python-script "<absolute_path_to_script>"
```

**Pros**: Full Slicer environment, all modules available, no extra setup.
**Cons**: Brief GUI flash, 20–40s startup, creates new Slicer process each run.

**Note**: On Windows, the `--no-splash` flag suppresses the splash screen but the Slicer window still briefly appears. This is normal.

If you need to load additional modules:
```bash
"D:\slicer\3D Slicer 5.10.0\Slicer.exe" --no-splash --additional-module-paths "F:/path/to/module" --python-script "<script>"
```

### Method 2: PythonSlicer.exe (Headless)

Lighter weight — just Slicer's Python interpreter without the GUI application.

```bash
# Equivalent manual command:
"D:\slicer\3D Slicer 5.10.0\bin\PythonSlicer.exe" "<absolute_path_to_script>"
```

**Pros**: No GUI, faster startup (5–15s), good for batch processing.
**Cons**: Some Slicer modules that require GUI/app initialization may not work. `import slicer` should still work for data access APIs.

### Method 3: Jupyter Kernel (Fallback)

Original method — communicates with a running Slicer Jupyter kernel via `jupyter_client`.

**Pros**: Headless, kernel stays warm between runs.
**Cons**: Requires `SlicerJupyter` extension + kernel spec setup, may not be configured.

## References

- SlicerAgentController project (`F:\slicer_module\SlicerAgentController\`) — source of direct `--python-script` method and scripting conventions
- Slicer Python API: `slicer.util`, `slicer.modules`, `vtk`, `mrml`
- [3D Slicer Documentation](https://slicer.readthedocs.io/)
