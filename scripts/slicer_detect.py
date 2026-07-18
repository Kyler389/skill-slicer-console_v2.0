"""
Slicer installation auto-detection module.

Provides multi-strategy detection for all three supported platforms.
Used by run_slicer_script.py and setup_checker.py.

Detection strategies (in order):
  1. SLICER_PATH  environment variable
  2. SLICER_ROOT   environment variable (Slicer directory)
  3. Common hardcoded paths (per-platform)
  4. Windows Registry (HKLM/HKCU)
  5. PATH scan
  6. Unix common dirs + AppImage + /Volumes scan (Linux / macOS)
  7. Program Files scan (Windows)
  8. Drive root scans (Windows)
  9. macOS Spotlight (macOS)
"""

import glob
import os
import platform
import subprocess
import sys


def get_system():
    return platform.system()


def _run_cmd(cmd):
    """Run a shell command, return (ok, stdout)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=True,
        )
        return result.returncode == 0, result.stdout
    except Exception:
        return False, ""


# ── Per-platform Slicer executable name ──

def slicer_exe_name():
    if get_system() == "Windows":
        return "Slicer.exe"
    return "Slicer"


def pythonslicer_exe_name():
    if get_system() == "Windows":
        return "PythonSlicer.exe"
    return "python-real"


# ── Strategy 1: Environment variable ──

def _from_env():
    """Check SLICER_PATH and SLICER_ROOT env vars."""
    # SLICER_PATH = full path to Slicer executable
    exe = os.environ.get("SLICER_PATH")
    if exe and os.path.isfile(exe):
        return os.path.abspath(exe)

    # SLICER_ROOT = directory containing Slicer.exe
    root = os.environ.get("SLICER_ROOT")
    if root:
        candidate = os.path.join(root, slicer_exe_name())
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
        # Try bin/ subdirectory
        candidate2 = os.path.join(root, "bin", slicer_exe_name())
        if os.path.isfile(candidate2):
            return os.path.abspath(candidate2)

    return None


# ── Strategy 2: Common hardcoded paths ──

def _from_common_paths():
    system = get_system()
    if system == "Windows":
        program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        program_files_x86 = os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))

        # Slicer version numbering variants
        versions = [
            "5.10.0", "5.10", "5.6.2", "5.6.1", "5.6", "5.4.0", "5.4",
            "5.2.2", "5.2.1", "5.2", "5.0.3", "5.0.2", "5.0.1", "5.0",
            "4.11", "4.10",
        ]
        dir_names = []
        for v in versions:
            dir_names.append(f"3D Slicer {v}")
            dir_names.append(f"Slicer {v}")
        dir_names += [
            "Slicer",
            "3D Slicer",
            "NA-MIC",
        ]

        candidates = []

        # Helper: add both flat and nested patterns for a given base directory
        def _add_candidates(base_dir):
            base_dir = os.path.abspath(base_dir)
            # Flat: D:\3D Slicer 5.10.0\Slicer.exe
            for name in dir_names:
                candidates.append(os.path.join(base_dir, name, slicer_exe_name()))
            # Nested under "slicer": D:\slicer\3D Slicer 5.10.0\Slicer.exe
            for sub in ["slicer", "Slicer", "NA-MIC", "Kitware"]:
                sub_dir = os.path.join(base_dir, sub)
                for name in dir_names:
                    candidates.append(os.path.join(sub_dir, name, slicer_exe_name()))

        # Program Files
        for base in [program_files, program_files_x86]:
            _add_candidates(base)
        # Local AppData
        _add_candidates(os.path.join(local_appdata, "NA-MIC"))
        _add_candidates(local_appdata)
        # AppData (Slicer config may hint at install dir)
        appdata = os.environ.get("APPDATA", os.path.expanduser("~\\AppData\\Roaming"))
        _add_candidates(os.path.join(appdata, "slicer.org"))
        # Drive roots: C:\, D:\, etc.
        for drive_letter in "CDEFGH":
            _add_candidates(f"{drive_letter}:\\")

    elif system == "Darwin":
        candidates = [
            "/Applications/Slicer.app/Contents/MacOS/Slicer",
        ]
        for v in ["5.10.0", "5.10", "5.6.2", "5.6.1", "5.6", "5.4", "5.2", "5.0"]:
            candidates.append(f"/Applications/Slicer-{v}.app/Contents/MacOS/Slicer")
            candidates.append(f"/Applications/3D Slicer-{v}.app/Contents/MacOS/Slicer")
        candidates += [
            os.path.expanduser("~/Applications/Slicer.app/Contents/MacOS/Slicer"),
            os.path.expanduser("~/Slicer/Slicer"),
        ]

    else:  # Linux
        candidates = [
            "/opt/slicer/Slicer",
            "/opt/slicer-5.10/Slicer",
            "/opt/slicer-5.6/Slicer",
            "/opt/3D-Slicer/Slicer",
            "/usr/local/bin/Slicer",
            os.path.expanduser("~/Slicer/Slicer"),
        ]

    for c in candidates:
        if os.path.isfile(c):
            return os.path.abspath(c)
    return None


# ── Unix common directory scan (Linux fallback) ──

def _from_unix_common_dirs():
    """Scan common Unix directories for Slicer installations (Linux/macOS fallback)."""
    system = get_system()
    if system == "Windows":
        return None

    exe_name = slicer_exe_name()
    scan_roots = []

    # ── macOS: /Volumes scan (mounted .dmg) ──
    if system == "Darwin":
        try:
            for entry in os.listdir("/Volumes"):
                if entry.startswith(".") or entry.startswith("MobileBackups"):
                    continue
                # Try Slicer.app directly in volume
                for app_candidate in [
                    os.path.join("/Volumes", entry, "Slicer.app"),
                    os.path.join("/Volumes", entry, f"{entry}.app"),
                ]:
                    if os.path.isdir(app_candidate):
                        app_binary = os.path.join(app_candidate, "Contents", "MacOS", exe_name)
                        if os.path.isfile(app_binary):
                            return os.path.abspath(app_binary)
        except (PermissionError, FileNotFoundError):
            pass

    # ── Linux: AppImage scan ──
    if system == "Linux":
        for search_dir in [
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Desktop"),
            "/opt",
            "/usr/local/bin",
        ]:
            try:
                for entry in os.listdir(search_dir):
                    # Match *Slicer*.AppImage / *slicer*.appimage
                    lower = entry.lower()
                    if lower.endswith(".appimage") and "licer" in lower:
                        full_path = os.path.join(search_dir, entry)
                        if os.path.isfile(full_path) and os.access(full_path, os.X_OK):
                            return os.path.abspath(full_path)
            except (PermissionError, FileNotFoundError):
                continue

    # ── Common: scan directories for Slicer ──
    if system == "Darwin":
        scan_roots = [
            "/Applications",
            os.path.expanduser("~/Applications"),
            "/usr/local",
            "/opt",
        ]
    else:  # Linux
        scan_roots = [
            "/opt",
            "/usr/local",
            "/usr/lib",
            "/snap/bin",
            os.path.expanduser("~"),
        ]

    for root_dir in scan_roots:
        try:
            for entry in os.listdir(root_dir):
                if "licer" in entry.lower() or "Slicer" in entry:
                    full_path = os.path.join(root_dir, entry, exe_name)
                    if os.path.isfile(full_path):
                        return os.path.abspath(full_path)
                    # Check bin/ subdirectory
                    bin_path = os.path.join(root_dir, entry, "bin", exe_name)
                    if os.path.isfile(bin_path):
                        return os.path.abspath(bin_path)
                    # On macOS, check .app bundle structure
                    if system == "Darwin" and entry.endswith(".app"):
                        app_binary = os.path.join(root_dir, entry, "Contents", "MacOS", exe_name)
                        if os.path.isfile(app_binary):
                            return os.path.abspath(app_binary)
        except PermissionError:
            continue
        except FileNotFoundError:
            continue

    return None


# ── Strategy 3: Windows Registry ──

def _from_registry():
    """Query Windows Registry for Slicer install path."""
    if get_system() != "Windows":
        return None

    reg_paths = [
        r"HKLM\SOFTWARE\Slicer",
        r"HKCU\SOFTWARE\Slicer",
        r"HKLM\SOFTWARE\Kitware\Slicer",
        r"HKLM\SOFTWARE\NA-MIC\Slicer",
    ]

    for reg in reg_paths:
        ok, out = _run_cmd(f'reg query "{reg}" /v "InstallDir" 2>nul')
        if ok:
            for line in out.splitlines():
                # Typical output: "    InstallDir    REG_SZ    D:\slicer\3D Slicer 5.10.0"
                parts = line.split()
                if len(parts) >= 3 and parts[-1].endswith(("\\",)):
                    dir_path = parts[-1].strip()
                    exe = os.path.join(dir_path, slicer_exe_name())
                    if os.path.isfile(exe):
                        return os.path.abspath(exe)

    return None


# ── Strategy 4: Program Files directory scan ──

def _from_programfiles_scan():
    """Scan %PROGRAMFILES% for *Slicer*/Slicer.exe."""
    if get_system() != "Windows":
        return None

    searched = []
    for var_name in ["PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"]:
        base = os.environ.get(var_name)
        if not base:
            continue

        # Search for Slicer directories
        for root, dirs, files in os.walk(base):
            # Limit depth to 3 levels to avoid deep scans
            depth = root.replace(base, "").count(os.sep)
            if depth > 3:
                dirs.clear()
                continue

            if slicer_exe_name() in files:
                return os.path.join(root, slicer_exe_name())

            # Prune non-Slicer directories at level 1
            if depth == 0:
                # Only descend into dirs that might contain Slicer
                dirs[:] = [d for d in dirs if "licer" in d.lower() or "NA-MIC" in d or "Kitware" in d]

    return None


# ── Strategy 5: Drive root quick scan ──

def _from_drive_roots():
    """Scan drive roots for Slicer directories (Windows)."""
    if get_system() != "Windows":
        return None

    # Get available drives
    ok, out = _run_cmd("wmic logicaldisk get name 2>nul")
    if not ok:
        # Fallback: check common drives
        drives = ["C:", "D:", "E:", "F:"]
    else:
        drives = [line.strip() for line in out.splitlines()[1:] if line.strip() and line.strip()[-1] == ":"]

    for drive in drives:
        root = drive + "\\"
        # Look for Slicer directories at root level
        try:
            for entry in os.listdir(root):
                if "licer" in entry.lower() or "NA-MIC" in entry:
                    exe_path = os.path.join(root, entry, slicer_exe_name())
                    if os.path.isfile(exe_path):
                        return os.path.abspath(exe_path)
                    # Try bin/ subdirectory
                    exe_path2 = os.path.join(root, entry, "bin", slicer_exe_name())
                    if os.path.isfile(exe_path2):
                        return os.path.abspath(exe_path2)
        except PermissionError:
            continue
        except FileNotFoundError:
            continue

    return None


# ── Strategy 6: macOS Spotlight ──

def _from_mdfind():
    """Use mdfind (macOS Spotlight) to locate Slicer."""
    if get_system() != "Darwin":
        return None
    ok, out = _run_cmd('mdfind "kMDItemFSName == Slicer" 2>/dev/null | head -5')
    if ok:
        for line in out.splitlines():
            line = line.strip()
            if line.endswith("/Slicer") and os.path.isfile(line):
                return line
    return None


# ── Strategy 7: PATH scan ──

def _from_path():
    """Search %PATH% for Slicer executable."""
    exe_name = slicer_exe_name()
    for path_dir in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(path_dir, exe_name)
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    return None


# ── Public API ──

def find_slicer(fast=True):
    """
    Auto-detect Slicer executable path using multiple strategies.

    Args:
        fast: If True, stop at first successful strategy (recommended).
              If False, try all strategies and return the first match from
              the most reliable strategies.

    Returns:
        Absolute path to Slicer executable, or None if not found.
    """
    strategies = [
        ("SLICER_PATH / SLICER_ROOT env var", _from_env, False),
        ("Common install paths", _from_common_paths, False),
        ("Windows Registry", _from_registry, False),
        ("PATH scan", _from_path, False),
        ("Unix dirs + AppImage + /Volumes scan", _from_unix_common_dirs, True),
        ("Program Files scan", _from_programfiles_scan, True),
        ("Drive root scan", _from_drive_roots, True),
        ("macOS Spotlight", _from_mdfind, True),
    ]

    for name, strategy, is_slow in strategies:
        if fast and is_slow:
            continue
        result = strategy()
        if result:
            return result

    return None


def find_slicer_detailed():
    """
    Run all detection strategies and return results for diagnostic display.

    Returns:
        List of (strategy_name, path_or_None) tuples.
    """
    strategies = [
        ("SLICER_PATH / SLICER_ROOT env var", _from_env),
        ("Common install paths", _from_common_paths),
        ("Windows Registry", _from_registry),
        ("PATH scan", _from_path),
        ("Unix dirs + AppImage + /Volumes scan", _from_unix_common_dirs),
        ("Program Files scan", _from_programfiles_scan),
        ("Drive root scan", _from_drive_roots),
        ("macOS Spotlight", _from_mdfind),
    ]

    results = []
    for name, strategy in strategies:
        try:
            result = strategy()
            results.append((name, result))
        except Exception as e:
            results.append((name, f"ERROR: {e}"))
    return results


def find_pythonslicer(slicer_exe=None):
    """
    Derive PythonSlicer.exe path from a known Slicer.exe path,
    or auto-detect by looking alongside the found Slicer.

    Args:
        slicer_exe: Known Slicer.exe path. If None, auto-detect.

    Returns:
        Absolute path to PythonSlicer, or None.
    """
    if slicer_exe is None:
        slicer_exe = find_slicer(fast=True)
        if slicer_exe is None:
            return None

    base = os.path.dirname(os.path.abspath(slicer_exe))
    exe_name = pythonslicer_exe_name()

    # Candidates relative to Slicer.exe location
    candidates = [
        os.path.join(base, "bin", exe_name),
        os.path.join(base, "..", "bin", exe_name),
        os.path.join(base, exe_name),
        os.path.join(base, "..", exe_name),
        os.path.join(base, "..", "..", "bin", exe_name),
    ]

    # On macOS, the Python is inside the .app bundle
    if get_system() == "Darwin" and "Slicer.app" in base:
        # Slicer.app/Contents/MacOS/  ->  Slicer.app/Contents/bin/
        candidates.insert(0, os.path.join(base, "..", "bin", exe_name))

    visited = set()
    for c in candidates:
        resolved = os.path.normpath(os.path.abspath(c))
        if resolved not in visited and os.path.isfile(resolved):
            return resolved
        visited.add(resolved)

    return None


# ── CLI entry point (for testing) ──

if __name__ == "__main__":
    print("=" * 60)
    print("Slicer Auto-Detection Diagnostic")
    print(f"System: {get_system()}")
    print(f"Platform: {platform.platform()}")
    print("=" * 60)

    print("\nQuick scan result:")
    exe = find_slicer(fast=True)
    if exe:
        print(f"  Slicer:      {exe}")
        ps = find_pythonslicer(exe)
        if ps:
            print(f"  PythonSlicer: {ps}")
        else:
            print(f"  PythonSlicer: not found")
    else:
        print("  Not found.")

    print("\nDetailed strategy results:")
    for name, result in find_slicer_detailed():
        status = result or "—"
        print(f"  [{name}]: {status}")
    print("=" * 60)
