# slicer-console

**Execute Python scripts in 3D Slicer from the command line.**  
A unified CLI tool with three execution backends, cross-platform auto-detection, and structured output capture.

```
python run_slicer_script.py --mode run --script task.py
```

---

## Features

- **Three backends** — Direct Slicer.exe, headless PythonSlicer, or Jupyter kernel fallback
- **Auto-detection** — 9 strategies across Windows, macOS, and Linux; no configuration needed
- **Two run modes** — `run` (execute + exit) or `launch` (open GUI, keep it open)
- **Structured output** — `$SLICER_RESULT_FILE` env var for reliable result capture
- **Auto-quit** — `slicer.app.quit()` appended automatically; override with `--no-quit`
- **Timeout & cleanup** — configurable timeout (default 300s) + automatic zombie process killing
- **Progress heartbeat** — live feedback every 15s during long-running scripts
- **Script templates** — segmentation, prediction, data import/export templates included
- **Diagnostics** — `setup_checker.py` validates your environment (`--verbose`, `--fix`)
- **Method persistence** — preferred backend saved to `config.json`, override via `--method`
- **Cross-platform** — works identically on Windows, macOS (Intel/Apple Silicon), and Linux

---

## Execution Methods

| # | Method | Command | Startup | GUI | Best For |
|---|--------|---------|---------|-----|----------|
| 1 | **Direct** (default) | `Slicer.exe --no-splash --python-script` | 20–40s | Brief flash | Most reliable, full Slicer environment |
| 2 | **PythonSlicer** | `PythonSlicer.exe` / `python-real` | 5–15s | None | Headless batch, lightweight scripts |
| 3 | **Jupyter** | `jupyter_client` KernelManager | 20–40s | None | Legacy; warm kernel between runs |

The tool auto-selects the best available method. Override with `--method direct|pythonslicer|jupyter` or save a preference to `config.json`.

---

## Quick Start

### 1. Check your environment

```bash
python setup_checker.py
```

Shows which methods are available. Pass `--verbose` for strategy-by-strategy detection details, `--fix` to automatically `pip install jupyter_client` if needed.

### 2. Write a script

```python
# task.py
import slicer, numpy as np

# List volumes
for vol in slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode"):
    dims = vol.GetImageData().GetDimensions() if vol.GetImageData() else (0, 0, 0)
    print(f"Volume '{vol.GetName()}': {dims}")

# Create a sample volume
node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "Sample")
voxels = slicer.util.arrayFromVolume(node)
voxels[:] = 100
slicer.util.arrayFromVolumeModified(node)
print("Done")
```

### 3. Run it

```bash
python run_slicer_script.py --mode run --script task.py
```

---

## Usage

### Run a script and exit (default)

```bash
python run_slicer_script.py --mode run --script ./.slicer_temp/task_001.py
```

### Launch Slicer GUI with a module loaded

```bash
python run_slicer_script.py --mode launch \
  --module-paths "F:/slicer_module/SlicerAgentController" \
  --select-module SlicerAgentController
```

### Headless execution (PythonSlicer)

```bash
python run_slicer_script.py --mode run --method pythonslicer --script task.py
```

### Jupyter kernel fallback

```bash
python run_slicer_script.py --mode run --method jupyter --script task.py --kernel slicer-5.6
```

### All command-line options

| Flag | Description | Default |
|------|-------------|---------|
| `--script PATH` | Python script to execute | — |
| `--mode run\|launch` | Run mode | `run` |
| `--method auto\|direct\|pythonslicer\|jupyter` | Execution method | `auto` |
| `--slicer-path PATH` | Override Slicer executable path | auto-detected |
| `--module-paths "p1;p2"` | Additional module search paths | — |
| `--select-module NAME` | Select a module on launch | — |
| `--kernel NAME` | Jupyter kernel name | `slicer-5.6` |
| `--timeout SEC` | Timeout in seconds | `300` |
| `--quit / --no-quit` | Auto-quit after script | `--quit` |
| `--kill-existing` | Kill running Slicer processes first | off |
| `--version` | Print Slicer version (no launch) | — |

> **Note:** `--quit` works when Qt event loop is active (e.g. when `selectModule` runs). For pure computation scripts, Slicer may not auto-exit — use `--kill-existing` or `taskkill`/`pkill` to clean up.

---

## Structured Output

The runner sets the `SLICER_RESULT_FILE` environment variable pointing to a temp file. Scripts can write structured results there for reliable capture:

```python
import os, json
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    with open(result_file, "w") as f:
        json.dump({"status": "ok", "volume": "Sample"}, f)
```

The runner reads and displays the contents after Slicer exits.

---

## Auto-Detection

The `slicer_detect.py` engine locates Slicer using 9 strategies, in order:

| # | Strategy | Speed | Platforms | Description |
|---|----------|-------|-----------|-------------|
| 1 | `SLICER_PATH` env var | Instant | All | Full path to Slicer executable |
| 2 | `SLICER_ROOT` env var | Instant | All | Directory containing Slicer |
| 3 | Common install paths | Instant | Win/Mac/Linux | Well-known paths for all Slicer versions |
| 4 | Windows Registry | Fast | Win | `HKLM\SOFTWARE\Slicer` keys |
| 5 | `PATH` scan | Fast | All | Checks system PATH |
| 6 | Unix dirs + AppImage + /Volumes | Slow | Linux/Mac | AppImage in `~/Downloads/`, /Volumes for macOS .dmg |
| 7 | Program Files scan | Slow | Win | Walks `%PROGRAMFILES%` for Slicer directories |
| 8 | Drive root scan | Slow | Win | Checks `C:\`, `D:\` etc. for Slicer |
| 9 | macOS Spotlight | Slow | Mac | `mdfind` to locate Slicer.app |

**Fast mode** (strategies 1–5) runs by default. Slow fallbacks activate automatically when fast mode fails.

Set a permanent path:

```bash
# Windows
setx SLICER_PATH "D:\slicer\3D Slicer 5.10.0\Slicer.exe"

# macOS
export SLICER_PATH="/Applications/Slicer.app/Contents/MacOS/Slicer"

# Linux (AppImage)
export SLICER_PATH="$HOME/Downloads/Slicer-5.10.0-linux-amd64.AppImage"
```

Run the diagnostic tool to test detection:

```bash
python slicer_detect.py
```

---

## Script Templates

Ready-to-use templates in `scripts/templates/`:

| Template | File | Description |
|----------|------|-------------|
| **Segmentation** | `segmentation.py` | Load volume, create threshold-based segmentation, export `.seg.nrrd` |
| **Prediction** | `prediction.py` | ML inference pipeline placeholder with volume I/O |
| **Data I/O** | `data_io.py` | Scene listing, volume export/import |

```bash
python run_slicer_script.py --mode run --script scripts/templates/segmentation.py
```

---

## Slicer 5.10 (Python 3.12) Notes

- Slicer 5.10 ships Python 3.12.10
- `slicer.util` methods: `arrayFromVolume()`, `arrayFromVolumeModified()`
- `PythonQt` vs `PyQt`: `QScrollBar.maximum`, `QTreeWidgetItem.childCount`, `QSpinBox.value`, `QLabel.text` are **properties, not methods** — check with `callable()` before calling
- `slicer.modules` attribute names are **lowercase**
- `QWidget.layout` is a **property** — never override, use `installEventFilter(self)` instead
- Avoid `setParent(None) + deleteLater()` on Python `QWidget` subclasses — causes double-free crash. Use `layout.removeWidget(w) + w.hide()`

---

## Diagnostics

```bash
# Quick check
python setup_checker.py

# Detailed + auto-fix
python setup_checker.py --verbose --fix
```

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Slicer not found` | Not installed or path not detected | Pass `--slicer-path`, set `SLICER_PATH`, or run `setup_checker.py` |
| Slicer exits with code 0 but no output | Script syntax error in Slicer's Python 3.12 | Check Python 3.12 compatibility |
| Script hangs after execution | Slicer window stays open | Use `--mode run` (auto-quit) or `--kill-existing` |
| `--additional-module-paths` no effect on Linux | AppImage is read-only | Extract AppImage: `./Slicer*.AppImage --appimage-extract && ./squashfs-root/AppRun` |
| Qt `setParent` / `deleteLater` crash | PythonQt teardown double-free | `layout.removeWidget(w) + w.hide()` instead |
| `QWidget.layout()` crash | Layout accessed as method | Use `self._layout` member variable |

---

## Project Structure

```
slicer-console/
├── README.md
├── skill.md                          # Skill documentation (Claude Code)
├── .gitignore
├── references/
│   └── CHANGELOG.md                  # Version history
├── scripts/
│   ├── run_slicer_script.py          # Main CLI entry point
│   ├── slicer_detect.py              # 9-strategy auto-detection engine
│   ├── setup_checker.py              # Environment diagnostics
│   ├── config.json                   # User method preference
│   └── templates/
│       ├── segmentation.py           # Volume segmentation template
│       ├── prediction.py             # ML inference template
│       └── data_io.py               # Data import/export template
```

---

## Requirements

- **Python 3.8+** (the runner runs in *your* Python, not Slicer's)
- **3D Slicer** (any recent version; auto-detected)
- **`jupyter_client`** — only needed for Jupyter fallback method

---

## License

MIT — see [LICENSE](LICENSE) (or contact the project owner).

---

## Related

- [SlicerAgentController](https://github.com/Kyler389/SlicerAgentController) — Slicer module for AI-assisted segmentation; source of direct `--python-script` method
- [3D Slicer Documentation](https://slicer.readthedocs.io/)
