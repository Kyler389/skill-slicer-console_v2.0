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
| **检索** | 执行前检索 Error Collection + Script Registry（Step 0.5） | 避免重复错误，复用成功经验 |
| **执行** | 编写脚本 → 运行脚本 | 利用**同一 Slicer 实例**的 Python Console 执行 |
| **注册** | 执行后注册结果到 Script Registry / Error Collection（Step 2.5） | 成功记录复用，失败记入错题集 |
| **收尾** | 先注册 → 再清理临时脚本（除非可复用） | 见下方清理规则 |

### 2. Python Console 执行方式

脚本通过 **Slicer Python Console**（Slicer 内置交互式 Python 解释器）执行：

- **`--python-script`（推荐）**：通过 `Slicer.exe --python-script <script>` 将脚本送入 Python Console 执行。首次用 `--mode launch` 启动 Slicer，后续对于需要大量交互的新会话再用 `run` 模式（但仍会启动新进程——属于第二阶段优化目标）。
- **Jupyter kernel**：对于已启动的 Slicer，若安装了 SlicerJupyter 扩展，可通过 `--method jupyter` 向运行中的 Python Console 发送代码，**完全免重启**。（最佳效率，但需额外配置）

> 目标：**一次启动，多次执行**。后续版本可考虑为运行中的 Slicer 添加 socket/IPC 监听机制，实现真正的免重启脚本注入。

### 3. 临时脚本清理规则

所有写入 `.slicer_temp/` 的脚本**执行注册后延迟清理**，避免占用用户交互通道：

| 阶段 | 操作 | 说明 |
|------|------|------|
| **0.5 (执行前)** | **检索** Error Collection + Script Registry | 避免重复错误，复用成功经验 |
| **1–2** | **编写 → 运行** 脚本 | 标准执行流程 |
| **2.5 (执行后)** | **注册** 结果 | 成功 → Script Registry；失败 → Error Collection |
| **3 (清理)** | **延迟清理** 临时脚本 | 见下方条件表 |

| 条件 | 处理方式 |
|------|----------|
| 一次性任务（计算/转换/查询） | 执行后告知用户"已完成"，**先注册 → 再设 300s 延迟删除** `.slicer_temp/task_*.py` |
| 成功 + 可复用模板 | **注册到 Script Registry** + **迁移**到 `scripts/templates/` |
| 失败/调试中 | **注册到 Error Collection** + 保留 `.slicer_temp/errors/` 副本 |
| 用户明确要求保留 | 保留并告知用户路径 |

> 原则：**跑完脚本 → 告知用户完成 → 注册（成功/失败）→ 设延迟清理 → 暂停等反馈**。不占用通道做额外操作。

清理命令示例：
```bash
# 延迟 300s 后清理所有临时脚本
(at +300s) rm -f ./.slicer_temp/task_*.py
# 或立即清理
rm -f ./.slicer_temp/task_*.py
# 清理单个
rm -f ./.slicer_temp/task_<timestamp>.py
```

### 4. 关于 `--mode launch` 的正确使用

- `--mode launch` 用于**长期保持 Slicer 运行**，适合需要多次执行脚本的会话
- `--mode run` 用于**执行脚本后自动退出**，适合单次一次性任务
- 建议：skill 被调用时如果预期会执行多次命令**优先使用 launch 模式启动**

### 5. 进度反馈与后台执行

对于耗时操作（DICOM 导入、批量分割等），**禁止**阻塞等待不反馈。必须遵循以下规则：

| 场景 | 操作 |
|------|------|
| **预计 < 15s 的短任务** | 直接 `--mode run` 同步执行，等待完成 |
| **预计 ≥ 15s 的长任务** | **必须**用 `run_in_background=true` 启动 runner，然后通过 TaskOutput 轮询进度 |
| **用户看到 Slicer 窗口后询问** | 立即告知当前进度，不要让用户对着窗口干等 |

脚本内建议写入进度文件供轮询读取：
```python
import json, os, time
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "progress.json")

def report_progress(current, total, stage=""):
    data = {"current": current, "total": total, "stage": stage}
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f)
    pct = current / total * 100 if total > 0 else 0
    print(f"[进度] {stage}: {current}/{total} ({pct:.0f}%)")
```

Agent 侧轮询示例：
```python
# 后台执行长任务
bash(..., run_in_background=true)

# 每 15s 检查进度
task_output(...)  # 查看进度文件内容
```

### 6. `--kill-existing` 默认行为

`--mode run` 时，runner 默认对已有 Slicer 进程执行 `--kill-existing`（避免前次异常退出导致新进程挂起）。

`--mode launch` 时保持默认不杀。

如果用户显式传 `--no-kill-existing` 则跳过。

---

## Action

### 0. 存储检测（Storage Detection）

**自动检测用户是否有知识库（知识库默认 Obsidian vault），没有则回退到本地文件存储。**

执行任何操作之前，先确定成长模块的存储后端：

```bash
# Step 1: 检查是否有 Obsidian vault
VAULT_PATH="${OBSIDIAN_VAULT_PATH:-}"
if [ -z "$VAULT_PATH" ]; then
  # OBSIDIAN_VAULT_PATH 未设置，尝试通过 obmem 检测
  OBMEM_VAULT=$(obmem show-vault 2>/dev/null) && VAULT_PATH="$OBMEM_VAULT"
fi

# Step 2: 根据检测结果设置 GROWTH_BASE
if [ -n "$VAULT_PATH" ] && [ -d "$VAULT_PATH" ]; then
  GROWTH_BASE="$VAULT_PATH/Project Memory/slicer-console"
  echo "[成长] 存储后端: Obsidian vault ($GROWTH_BASE)"
else
  GROWTH_BASE="$HOME/.claude/projects/slicer-console-skill/growth"
  mkdir -p "$GROWTH_BASE/Script Registry" "$GROWTH_BASE/Error Collection"
  echo "[成长] 存储后端: 本地文件 ($GROWTH_BASE)"
  echo "[提示] 如需启用 Obsidian 知识库，请设置环境变量 OBSIDIAN_VAULT_PATH 或安装 obmem"
fi
```

> **$GROWTH_BASE** 是成长模块的根目录，以下所有检索和注册操作均以此为基准。
> - 有 Obsidian vault → `$OBSIDIAN_VAULT_PATH/Project Memory/slicer-console/`
> - 无 vault → `~/.claude/projects/slicer-console-skill/growth/`

#### 目录结构（自动创建）

```
$GROWTH_BASE/
├── Script Registry/       # 成功脚本索引
│   ├── INDEX.md           # 标签索引
│   └── {date}-{slug}.md   # 单条脚本记录
└── Error Collection/      # 错题集
    ├── INDEX.md           # 标签索引
    └── {date}-{slug}.md   # 单条错误记录
```

### 0a. Method Selection (First-Time Only)

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

### 0b. 知识检索（Retrieve）

Before writing any new script, check existing knowledge for precedents.
**搜索方式根据存储后端自动切换**：

```bash
# 统一检索脚本
SEARCH_GROWTH() {
  local query="$1"
  local registry="$2"  # "Script Registry" 或 "Error Collection"
  local base="$GROWTH_BASE"

  if command -v obmem &>/dev/null && [ -n "$OBSIDIAN_VAULT_PATH" ]; then
    # Obsidian vault 后端：使用 obmem 语义搜索
    obmem search --project "slicer-console" --query "$query" 2>/dev/null \
      | grep -i "$registry" || true
  else
    # 本地文件后端：直接 grep 标题和标签
    grep -ril --include="*.md" \
      -e "$query" \
      "$base/$registry/" 2>/dev/null || true
  fi
}
```

1. **Search Error Collection** first — check for similar past mistakes:
   ```bash
   ERROR_HITS=$(SEARCH_GROWTH "<task_keywords>" "Error Collection")
   ```
   - If hits found: **read the best-matching entry** for root cause and fix.
   - Apply the fix before proceeding.
   - Log: `[成长] 发现类似历史错误: <entry_path> — 已应用推荐修复`
   - If unresolved error (frontmatter `resolved: false`), **skip** Script Registry search.

2. **Search Script Registry** (skip if unresolved error found above):
   ```bash
   SCRIPT_HITS=$(SEARCH_GROWTH "<task_keywords>" "Script Registry")
   ```
   - If hits found: **read the most relevant entry**.
     - Direct match → copy script to `.slicer_temp/` and reuse with minor tweaks.
     - Partial match → use as template, extend for current task.
   - Log: `[成长] 发现类似历史脚本: <entry_path> — 已复用/参考`

3. **If no matches**: proceed fresh — the result will become a new entry after execution.

> **关键词提取**：从用户请求中提取 2–4 个核心技术名词（如 `"segmentation"`、`"NIfTI"`），
> 用空格分隔。本地文件后端使用大小写不敏感的 grep 匹配。

---

### 1. Write Script

1. **Write a Python script** that solves the user's request using `slicer`, `vtk`, `mrml`, and related Slicer APIs.
   - 对于预计 ≥ 15s 的**长任务**，脚本内必须写入进度反馈（见上方第 5 节），并支持 `SLICER_RESULT_FILE` 输出。
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
   - `--kill-existing` — kill running Slicer processes before starting (--mode run 时默认启用)
   - `--no-kill-existing` — 跳过杀掉已有 Slicer 进程
4. **Return the output** to the user and report the script path.
   - 如果 runner 输出被截断，优先展示 `SLICER_RESULT_FILE` 的结构化结果（如果有）。
   - 告知用户执行结果和脚本路径，然后进入 **Step 2.5** 进行知识注册。
   - **不要立即清理脚本** — 先注册，再清理。

### 2.5. 知识记录（Register）

After returning results, record the outcome before cleaning up the temp script.
Determine success vs. failure from the script exit code AND user feedback:

> **判断标准**：
> - `exit code 0` + 输出符合预期 = **成功** → Script Registry
> - `exit code != 0` 或输出含错误 / 用户表示需要修改 = **失败/调试中** → Error Collection

#### ✅ If Task Succeeded

1. **Create Script Registry entry** at `$GROWTH_BASE/Script Registry/<YYYY-MM-DD>-<slug>.md`:
   ```bash
   mkdir -p "$GROWTH_BASE/Script Registry"
   cat > "$GROWTH_BASE/Script Registry/$(date +%F)-<slug>.md" << REGEOF
   ---
   type: "script-registry"
   project: "slicer-console"
   created: "$(date -Iseconds)"
   tags: ["slicer-console", "script", "<task_type>", "<api_keywords>"]
   title: "<brief description>"
   task_type: "<type>"
   slicer_method: "<direct|pythonslicer|jupyter>"
   duration_sec: <seconds>
   exit_code: 0
   ---

   ## Task
   <description>

   ## Key APIs Used
   - <api_list>

   ## Script Summary
   \`\`\`python
   <extracted core logic>
   \`\`\`

   ## Notes
   - <useful_details>
   REGEOF
   ```

   > **Obsidian vault 后端**：自动生成的文件会被 Obsidian 识别并建立双向链接。
   > **本地文件后端**：文件存储在 `$GROWTH_BASE/Script Registry/`，通过 grep 检索。

2. **Copy the script** to `scripts/templates/` if it's reusable as a pattern:
   ```bash
   cp ./.slicer_temp/task_<timestamp>.py ./scripts/templates/<meaningful_name>.py
   ```

3. **Update INDEX.md** — append a row to the tag table in `$GROWTH_BASE/Script Registry/INDEX.md`:
   ```bash
   echo "| <task_type> | [[$(date +%F)-<slug>]] |" >> "$GROWTH_BASE/Script Registry/INDEX.md"
   ```

4. **Log**: `[成长] ✅ 已注册脚本到 Script Registry: <title>`

#### ❌ If Task Failed or Required Debugging

1. **Create Error Collection entry** at `$GROWTH_BASE/Error Collection/<YYYY-MM-DD>-<slug>.md`:
   ```bash
   mkdir -p "$GROWTH_BASE/Error Collection"
   cat > "$GROWTH_BASE/Error Collection/$(date +%F)-<slug>.md" << ERREOF
   ---
   type: "error-collection"
   project: "slicer-console"
   created: "$(date -Iseconds)"
   tags: ["slicer-console", "error", "<error_category>", "<task_type>"]
   title: "<error description>"
   task_type: "<type>"
   slicer_method: "<direct|pythonslicer|jupyter>"
   error_category: "<timeout|api-error|script-error|import-error|other>"
   severity: "<low|medium|high>"
   resolved: false
   ---

   ## What Was Attempted
   <what the script intended to do>

   ## Error
   <error message / traceback>

   ## Root Cause
   <analysis of what went wrong>

   ## Resolution Attempted
   <what was tried to fix>

   ## Recommended Fix
   <actionable steps for next time>

   ## Related Errors
   - <wikilinks or paths to similar Error Collection entries>
   ERREOF
   ```

2. **Archive the failed script** for later reference:
   ```bash
   mkdir -p .slicer_temp/errors
   cp ./.slicer_temp/task_<timestamp>.py ./.slicer_temp/errors/<timestamp>_<slug>.py
   ```

3. **Update Error Collection INDEX.md**:
   ```bash
   echo "| <error_category> | [[$(date +%F)-<slug>]] — <title> |" >> "$GROWTH_BASE/Error Collection/INDEX.md"
   ```

4. **Log**: `[成长] ❌ 已记录错误到 Error Collection: <title>`

#### 🔁 What Happens Next

| Outcome | Next Step |
|---------|-----------|
| **Success** → Script Registry ✅ | 设延迟清理 → **暂停等用户反馈** |
| **Failed + can fix quickly** | 修改脚本 → 回到 Step 1 重新运行 |
| **Failed + needs user input** | 设延迟清理 → **暂停等用户反馈**（保留脚本供后续修复） |

### 2.6. 清理（Cleanup）

After registration:

- **成功脚本**：设 300s 延迟删除 `.slicer_temp/task_<timestamp>.py`
- **失败脚本**：`.slicer_temp/task_<timestamp>.py` 延迟删除，但保留 `.slicer_temp/errors/` 中的副本
- **可复用脚本**：已迁移到 `scripts/templates/` 的副本不予删除
- **用户要求保留**：保留并告知路径

**无论成功还是失败**，完成后都必须暂停等待用户反馈：

> **告知用户结果 → 注册 → 清理 → **暂停等用户反馈****。不要继续做额外操作（检查、轮询、清理等）。

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

# 长任务后台执行（避免阻塞）
bash(description="Slicer DICOM import", run_in_background=true, timeout=600)  # 用 Bash 的 run_in_background
# 之后轮询进度
task_output(task_id="...", block=false)  # 非阻塞查看 stdout + progress.json
task_output(task_id="...", block=true)   # 阻塞等待完成
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
after Slicer exits. **Runner 会在 stdout 最前面展示 result 文件内容**（而非混在冗长输出中间）。

```python
import os, json
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    with open(result_file, "w") as f:
        f.write(json.dumps({"status": "ok", "volume": "Sample"}))
```

### Progress reporting for long tasks

对于预计 ≥ 15s 的耗时操作，脚本内应写入进度文件以供轮询：

```python
import json, os, time

PROGRESS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "progress.json")

def report_progress(current, total, stage=""):
    data = {"current": current, "total": total, "stage": stage}
    with open(PROGRESS_PATH, "w") as f:
        json.dump(data, f)
    pct = current / total * 100 if total > 0 else 0
    print(f"[进度] {stage}: {current}/{total} ({pct:.0f}%)")
    time.sleep(0.05)  # 确保文件 flush

# 使用示例
items = [list of something]
for i, item in enumerate(items):
    process(item)
    report_progress(i + 1, len(items), "正在导入 DICOM 系列")
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
| **Runner 超时，Slicer 窗口还在** | 任务耗时超过 `--timeout` | **Slicer 可能仍在运行**，去任务管理器手动关闭 Slicer.exe。下次调大 `--timeout` |
| Qt errors about `setParent` / `deleteLater` | PythonQt teardown double-free | Use `layout.removeWidget(w) + w.hide()` instead |
| `--additional-module-paths` has no effect on Linux | AppImage is read-only filesystem | Extract AppImage first: `./Slicer*.AppImage --appimage-extract && ./squashfs-root/AppRun` |
| `AttributeError` on slicer API | Using C++ method that moved | Fall back to `slicer.modules.*.logic()` or `slicer.util.*` |
| `QWidget.layout` call crashes | Layout accessed as method not property | Use `self._layout` member variable instead |

> 💡 **首次遇到新错误？** 如果是新的错误模式，执行完毕后它会自动被记录到 **Error Collection（错题集）**。
> 下次检索时系统会自动匹配，避免重蹈覆辙。也可以通过索引手动查阅：
> `$GROWTH_BASE/Error Collection/INDEX.md`

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
