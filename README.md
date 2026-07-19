# slicer-console

A [Claude Code Skill](https://claude.ai/code) that lets you execute Python scripts inside **3D Slicer** from the command line.

It provides a unified runner with three execution backends, cross-platform auto-detection, structured output capture, and ready-to-use templates for segmentation, inference, and data I/O.

---

## Install this skill in your Claude Code agent

### 1. Clone into your skills directory

```bash
# macOS / Linux
git clone git@github.com:Kyler389/skill-slicer-console_v2.0.git \
  ~/.claude/skills/slicer-console

# Windows (PowerShell)
git clone git@github.com:Kyler389/skill-slicer-console_v2.0.git `
  "$env:USERPROFILE\.claude\skills\slicer-console"
```

> **Note:** The directory name under `~/.claude/skills/` must be `slicer-console` so Claude Code recognizes the skill.

### 2. Verify your environment

```bash
cd ~/.claude/skills/slicer-console/scripts
python setup_checker.py
```

This checks whether 3D Slicer is detected and which execution methods are available. Use `--verbose` for per-strategy details or `--fix` to auto-install optional dependencies.

### 3. Choose your default execution method (first time only)

The runner will ask you to pick a backend on first use, or you can create `scripts/config.json` manually:

```json
{"method": "direct", "updated": "2026-07-19T00:00:00"}
```

Allowed values: `direct`, `pythonslicer`, `jupyter`. You can always override with `--method <name>`.

---

## How to use

Once installed, mention Slicer in Claude Code and the skill will be activated, for example:

> "Run a Slicer script that lists all volumes in the scene."
> "Use slicer python to threshold this volume and save the segmentation."

Claude Code will then:

1. Write a Python script to `./.slicer_temp/task_<timestamp>.py` in your current working directory.
2. Invoke `scripts/run_slicer_script.py` with the configured backend.
3. Return the script output and the script path.

### Manual CLI usage

```bash
# Run a script and exit
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py \
  --mode run --script ./.slicer_temp/task_001.py

# Launch Slicer GUI with a custom module
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py \
  --mode launch \
  --module-paths "F:/slicer_module/SlicerAgentController" \
  --select-module SlicerAgentController

# Headless batch execution
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py \
  --mode run --method pythonslicer --script task.py
```

### Common CLI options

| Flag | Description | Default |
|------|-------------|---------|
| `--script PATH` | Python script to execute | — |
| `--mode run\|launch` | Run mode | `run` |
| `--method auto\|direct\|pythonslicer\|jupyter` | Execution backend | `auto` |
| `--slicer-path PATH` | Override Slicer executable | auto-detected |
| `--module-paths "p1;p2"` | Extra module search paths | — |
| `--select-module NAME` | Select module on launch | — |
| `--kernel NAME` | Jupyter kernel name | `slicer-5.6` |
| `--timeout SEC` | Timeout in seconds | `300` |
| `--quit` / `--no-quit` | Auto-quit after script | `--quit` |
| `--kill-existing` | Kill running Slicer processes first | off |
| `--version` | Print detected Slicer version | — |

---

## Execution methods

| # | Method | Command | Startup | GUI | Best for |
|---|--------|---------|---------|-----|----------|
| 1 | **Direct** (default) | `Slicer.exe --no-splash --python-script` | 20–40s | Brief flash | Most reliable, full Slicer environment |
| 2 | **PythonSlicer** | `PythonSlicer.exe` / `python-real` | 5–15s | None | Headless batch processing |
| 3 | **Jupyter** | `jupyter_client` KernelManager | 20–40s | None | Legacy; warm kernel between runs |

The runner auto-selects the best available backend. Override anytime with `--method <name>`.

---

## Structured output

For reliable result capture (especially on Windows where GUI-app stdout may be lost), the runner sets `$SLICER_RESULT_FILE`:

```python
import os, json
result_file = os.environ.get("SLICER_RESULT_FILE")
if result_file:
    with open(result_file, "w") as f:
        json.dump({"status": "ok", "volume": "Sample"}, f)
```

The runner reads and displays this file after Slicer exits.

---

## Auto-detection

`slicer_detect.py` locates Slicer using 9 strategies in order:

| # | Strategy | Platforms | Description |
|---|----------|-----------|-------------|
| 1 | `SLICER_PATH` env var | All | Full path to Slicer executable |
| 2 | `SLICER_ROOT` env var | All | Directory containing Slicer executable |
| 3 | Common install paths | Win/Mac/Linux | Well-known default paths |
| 4 | Windows Registry | Win | `HKLM\SOFTWARE\Slicer` keys |
| 5 | `PATH` scan | All | Slicer on system `PATH` |
| 6 | Unix dirs + AppImage + `/Volumes` | Linux/Mac | Scans `~/Downloads/`, `/Applications/`, mounted `.dmg` |
| 7 | Program Files scan | Win | Walks `%PROGRAMFILES%` |
| 8 | Drive root scan | Win | Checks `C:\`, `D:\`, etc. |
| 9 | macOS Spotlight | Mac | `mdfind` to locate `Slicer.app` |

Fast mode (strategies 1–5) runs by default. Slow fallbacks activate only when needed.

Set a permanent path if detection fails:

```bash
# Windows
setx SLICER_PATH "D:\slicer\3D Slicer 5.10.0\Slicer.exe"

# macOS
export SLICER_PATH="/Applications/Slicer.app/Contents/MacOS/Slicer"

# Linux (AppImage)
export SLICER_PATH="$HOME/Downloads/Slicer-5.10.0-linux-amd64.AppImage"
```

---

## Script templates

Located in `scripts/templates/`:

| Template | File | Description |
|----------|------|-------------|
| Segmentation | `segmentation.py` | Load volume, threshold segmentation, export `.seg.nrrd` |
| Prediction | `prediction.py` | ML inference pipeline placeholder with volume I/O |
| Data I/O | `data_io.py` | Scene listing, volume export/import |

```bash
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py \
  --mode run --script ~/.claude/skills/slicer-console/scripts/templates/segmentation.py
```

---

## Scripting conventions

- **Absolute paths** for input/output files.
- **Print with `RESULT:` prefix** for easy parsing.
- **Write structured results** to `$SLICER_RESULT_FILE`.
- **API fallback:** if a direct Slicer API raises `AttributeError`, try `slicer.modules.<moduleName>.logic()`.
- **No GUI dialogs** in `--python-script` mode — they block execution.
- **PythonQt properties:** in Slicer 5.10 / Python 3.12, attributes like `QWidget.layout`, `QSpinBox.value`, and `QLabel.text` are properties, not methods.
- **Avoid `setParent(None) + deleteLater()`** on Python `QWidget` subclasses — use `layout.removeWidget(w) + w.hide()` to prevent double-free crashes.

---

## Diagnostics & troubleshooting

```bash
# Quick environment check
python ~/.claude/skills/slicer-console/scripts/setup_checker.py

# Detailed detection report
python ~/.claude/skills/slicer-console/scripts/setup_checker.py --verbose

# Test auto-detection directly
python ~/.claude/skills/slicer-console/scripts/slicer_detect.py
```

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `Slicer not found` | Not installed or not detected | Set `SLICER_PATH`, pass `--slicer-path`, or run `setup_checker.py` |
| Slicer exits with code 0 but no output | Python 3.12 syntax error | Check script compatibility |
| Script hangs | Slicer window stays open | Use `--mode run` or `--kill-existing` |
| Jupyter `NoSuchKernel` | Kernel not registered | Use `--method direct` |
| Qt `setParent`/`deleteLater` crash | PythonQt double-free | Use `layout.removeWidget(w) + w.hide()` |
| `QWidget.layout()` crash | Layout is a property | Store layout as `self._layout = qt.QVBoxLayout(self)` |
| Linux AppImage module paths ignored | AppImage is read-only | Extract first: `./Slicer*.AppImage --appimage-extract` |

---

## Project structure

```
~/.claude/skills/slicer-console/
├── README.md                         # This file
├── skill.md                          # Claude Code skill manifest
├── .gitignore
├── references/
│   ├── CHANGELOG.md                  # Version history
│   └── example_script.py             # Example usage
└── scripts/
    ├── run_slicer_script.py          # Main CLI entry point
    ├── slicer_detect.py              # 9-strategy auto-detection engine
    ├── setup_checker.py              # Environment diagnostics
    ├── config.json                   # Saved backend preference
    └── templates/
        ├── segmentation.py           # Volume segmentation template
        ├── prediction.py             # ML inference template
        └── data_io.py                # Data import/export template
```

---

## Requirements

- **Python 3.8+** (the runner runs in your external Python, not Slicer's)
- **3D Slicer** (any recent version; auto-detected)
- **`jupyter_client`** — only required for the Jupyter fallback method

---

## License

MIT — see [LICENSE](LICENSE) (or contact the project owner).

---

## Related

- [SlicerAgentController](https://github.com/Kyler389/SlicerAgentController) — Slicer module that inspired the direct `--python-script` approach
- [3D Slicer Documentation](https://slicer.readthedocs.io/)
