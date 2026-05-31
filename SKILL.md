---
name: slicer-console
description: >
  Execute Slicer Python scripts via Jupyter kernel.
  Triggered when user mentions "slicer console", "slicer python", "slicer 脚本",
  "在 slicer 里运行", "slicer 计算", or similar.
---

# slicer-console

Execute Slicer Python scripts via Jupyter kernel.

## Trigger

User mentions any of the following (or similar):
- "slicer console"
- "slicer python console"
- "用 slicer 的 console 执行"
- "slicer python"
- "slicer 脚本"
- "slicer 计算"
- "在 slicer 里运行"

## Action

1. **Write a Python script** that solves the user's request using `slicer`, `vtk`, `mrml`, and related Slicer APIs.
2. **Save the script** to `./.slicer_temp/task_<timestamp>.py`. Create the `.slicer_temp` directory if it does not exist.
3. **Run the script** using the provided connector:
   ```bash
   python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --script ./.slicer_temp/task_<timestamp>.py
   ```
   Do NOT use `jupyter run` or `jupyter console` directly, because Slicer's GUI startup takes 20–40 seconds and will exceed their default timeout.
4. **Return the output** to the user and report the script path.

Use `print("RESULT:", ...)` in the script for easy parsing of key results.

## Execution

Slicer takes 20–40 seconds to start, so standard `jupyter run` (1-second timeout) and `jupyter console` (requires interactive TTY) will fail.

The skill provides a custom connector with `jupyter_client` that handles long timeouts and collects all output:

```bash
python ~/.claude/skills/slicer-console/scripts/run_slicer_script.py --script <path> [--kernel slicer-5.6] [--timeout 60]
```

- `--script` — required, path to the Python file to execute.
- `--kernel` — optional, kernel name (default `slicer-5.6`).
- `--timeout` — optional, seconds to wait for kernel ready (default 60).

The connector prints stdout/stderr live, captures execution results and tracebacks, and shuts down the kernel automatically.

## Manual Setup (One-Time)

The following steps must be performed by the user inside the Slicer GUI. Claude cannot automate these.

### Step 1: Install SlicerJupyter Extension

1. Open **3D Slicer**.
2. Go to **View → Extension Manager**.
3. Search for **SlicerJupyter** and install it.
4. **Restart Slicer** when prompted.

### Step 2: Install the Jupyter Kernel Spec

1. In Slicer, open **View → Python Interactor**.
2. Run the following command (adjust the path if your Slicer version differs):
   ```python
   jupyter-kernelspec install "<SlicerExtPath>/SlicerJupyter/share/Slicer-5.6/qt-loadable-modules/JupyterKernel/Slicer-5.6" --replace --user
   ```
   - `<SlicerExtPath>` is usually under your Slicer settings directory, e.g.:
     - Windows: `%LOCALAPPDATA%\NA-MIC\Slicer 5.6.1\` or similar
3. Verify the kernel is registered:
   ```bash
   jupyter kernelspec list
   ```
   You should see `slicer-5.6` in the list.

### Step 3: Install IPython inside Slicer Python

The SlicerJupyter xeus kernel requires IPython:

```bash
"<SlicerDir>/bin/PythonSlicer.exe" -m pip install ipython
```

- Example on Windows: `"D:\slicer\Slicer 5.6.1\bin\PythonSlicer.exe" -m pip install ipython`

### Step 4: Verify Everything

Run the diagnostic script:

```bash
python ~/.claude/skills/slicer-console/scripts/setup_checker.py
```

It checks:
- `jupyter` CLI availability
- `jupyter_client` package
- `slicer-5.6` kernel registration
- Slicer executable location
- PythonSlicer location

If anything is missing, the script prints the exact fix.

## Environment Prerequisites

| Component | Requirement | Checked By |
|-----------|-------------|------------|
| 3D Slicer | Installed and runnable | `setup_checker.py` |
| SlicerJupyter | Installed via Extension Manager | Manual (Step 1) |
| Kernel spec | `slicer-5.6` registered with Jupyter | Manual (Step 2) + `setup_checker.py` |
| IPython | Installed inside Slicer Python | Manual (Step 3) + `setup_checker.py` |
| `jupyter_client` | Installed in the external Python env | `setup_checker.py` |

## Scripting Conventions

- **Absolute paths**: always use absolute paths for input/output files inside the script.
- **Result printing**: use `print("RESULT:", value)` so the caller can easily parse key outputs.
- **API fallback**: if a direct Slicer API method raises `AttributeError`, fall back to `slicer.modules.<moduleName>.logic()` methods or export to labelmap/volume nodes first, rather than relying on obscure internal C++ APIs.
- **No GUI interaction**: scripts run in a headless kernel context — do not open dialog boxes or rely on the render window.

## Example

See [`references/example_script.py`](references/example_script.py) for a minimal working script that lists scene volumes or creates a sample volume.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `NoSuchKernel: No such kernel named slicer-5.6` | Kernel spec not installed | Follow Manual Setup Step 2 |
| `ModuleNotFoundError: No module named 'IPython'` | IPython missing inside Slicer Python | Follow Manual Setup Step 3 |
| `ModuleNotFoundError: No module named 'jupyter_client'` | Connector env missing package | `pip install jupyter_client` |
| Kernel hangs at "Starting kernel..." | Slicer executable not found or blocked | Check Slicer path and antivirus |
| `AttributeError` on Slicer API | Using an internal C++ method that moved | Fall back to `slicer.modules.*.logic()` |

## Notes

- Assume kernel `slicer-5.6` is already installed and registered after the one-time setup above.
- The connector script handles the long startup time and TTY issues that break `jupyter run` / `jupyter console`.
- On Windows, if the kernel path was copied manually, ensure the JSON file inside it points to the correct Slicer executable path.
