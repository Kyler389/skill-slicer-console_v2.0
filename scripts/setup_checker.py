#!/usr/bin/env python3
"""
Check slicer-console skill prerequisites and guide the user through setup.

Detects availability of all three execution methods:
  1. Direct — Slicer --no-splash --python-script
  2. PythonSlicer — headless interpreter
  3. Jupyter — Jupyter kernel via jupyter_client

Cross-platform: works on Windows, macOS, and Linux.

Usage:
    python setup_checker.py
    python setup_checker.py --kernel slicer-5.6
    python setup_checker.py --verbose    # show all detection strategies
    python setup_checker.py --fix        # auto-install missing dependencies
"""

import argparse
import os
import sys
import subprocess


# Import shared auto-detection module
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRIPT_DIR)
import slicer_detect


def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_jupyter_client():
    try:
        import jupyter_client  # noqa: F401
        return True
    except ImportError:
        return False


def find_kernelspec(kernel_name):
    ok, out, err = run_cmd("jupyter kernelspec list")
    if not ok:
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == kernel_name:
            return parts[1]
    return None


def print_result(name, ok, message=""):
    if ok:
        status = "[OK]"
    else:
        status = "[FAIL]"
    print(f"  {status} {name}", end="")
    if message:
        print(f" -- {message}")
    else:
        print()


def main():
    parser = argparse.ArgumentParser(description="Check slicer-console prerequisites")
    parser.add_argument("--kernel", default="slicer-5.6", help="Kernel name to check (default: slicer-5.6)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all detection strategies")
    parser.add_argument("--fix", action="store_true", help="Auto-install missing dependencies (pip install jupyter_client)")
    args = parser.parse_args()

    system = slicer_detect.get_system()
    slicer_name = slicer_detect.slicer_exe_name()
    ps_name = slicer_detect.pythonslicer_exe_name()

    print("=" * 60)
    print("slicer-console Skill Setup Checker")
    print(f"System: {system}")
    print("=" * 60)

    # ── Method 1: Direct Slicer.exe ──
    print(f"\n--- Method 1: Direct {slicer_name} (--python-script) ---")
    slicer_exe = slicer_detect.find_slicer(fast=not args.verbose)
    print_result(f"Slicer executable ({slicer_name}) found", slicer_exe is not None, slicer_exe or "not found")

    if args.verbose:
        print("\n  Detection strategy details:")
        for name, result in slicer_detect.find_slicer_detailed():
            status = result or "-"
            print(f"    [{name}]: {status}")

    # ── Method 2: PythonSlicer ──
    print(f"\n--- Method 2: {ps_name} (Headless) ---")
    pslicer = slicer_detect.find_pythonslicer(slicer_exe)
    print_result(f"PythonSlicer ({ps_name}) found", pslicer is not None, pslicer or "not found")

    # ── Method 3: Jupyter Kernel ──
    print("\n--- Method 3: Jupyter Kernel (Fallback) ---")
    has_jc = check_jupyter_client()
    print_result("jupyter_client Python package", has_jc)
    if not has_jc:
        print("      Fix: pip install jupyter_client")

    kernel_path = find_kernelspec(args.kernel)
    has_kernel = kernel_path is not None and os.path.isdir(kernel_path)
    print_result(f"Kernel spec '{args.kernel}' registered", has_kernel, kernel_path or "not found")

    # ── Quick setup hint ──
    print("\n--- Quick Setup ---")
    if not slicer_exe:
        print("  Set SLICER_PATH env var to point to your Slicer executable.")
        if system == "Windows":
            print('    set SLICER_PATH="D:\\slicer\\3D Slicer 5.10.0\\Slicer.exe"')
            print('  Or set SLICER_ROOT to the Slicer installation directory:')
            print('    set SLICER_ROOT="D:\\slicer\\3D Slicer 5.10.0"')
        elif system == "Darwin":
            print('    export SLICER_PATH="/Applications/Slicer.app/Contents/MacOS/Slicer"')
        else:
            print('    export SLICER_PATH="/opt/slicer/Slicer"')
    else:
        if system == "Windows":
            print(f'  Export current detection: set SLICER_PATH="{slicer_exe}"')
        else:
            print(f'  Export current detection: export SLICER_PATH="{slicer_exe}"')

    # ── Auto-fix ──
    if args.fix:
        print("\n--- Auto-Fix Mode ---")
        if not has_jc:
            print("[INFO] Installing jupyter_client...")
            ok, _, err = run_cmd(f"{sys.executable} -m pip install jupyter_client")
            if ok:
                print("  [OK] jupyter_client installed successfully.")
                has_jc = check_jupyter_client()
            else:
                print(f"  [FAIL] pip install failed: {err[:200]}")
        else:
            print("  [OK] jupyter_client already installed.")

        if not slicer_exe:
            print("  [WARN] Slicer not found. Cannot auto-fix.")
            print("         Please install Slicer or set SLICER_PATH env var manually.")
        else:
            print(f"  [OK] Slicer found at: {slicer_exe}")

        if has_jc:
            if not has_kernel:
                print("  [WARN] Kernel spec not registered. Cannot auto-fix.")
                print(f"         To register, start Slicer and install SlicerJupyter extension.")
            else:
                print(f"  [OK] Kernel '{args.kernel}' registered.")

        print("--- Auto-Fix Complete ---")

    # ── Summary ──
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    if slicer_exe:
        print(f"  [YES] Method 1 (Direct {slicer_name}) -- READY")
        if pslicer:
            print(f"  [YES] Method 2 ({ps_name}) -- READY")
        else:
            print(f"  [NO]  Method 2 ({ps_name}) -- NOT AVAILABLE")
    else:
        print(f"  [NO]  Method 1 (Direct {slicer_name}) -- NOT AVAILABLE")
        print(f"  [NO]  Method 2 ({ps_name}) -- NOT AVAILABLE")

    if has_jc and has_kernel:
        print("  [YES] Method 3 (Jupyter Kernel) -- READY")
    elif has_jc:
        print("  [WARN] Method 3 (Jupyter Kernel) -- jupyter_client OK, but kernel not registered")
    else:
        print("  [NO]  Method 3 (Jupyter Kernel) -- jupyter_client not installed")

    print()
    if slicer_exe:
        print(f"Recommended: Use Method 1 (Direct {slicer_name}) -- no extra setup needed.")
    else:
        print("Install Slicer or set SLICER_PATH env var, then re-run this checker.")

    # User hint for env var persistence
    print()
    print("Tip: To make the path permanent, add to your shell profile:")
    if system == "Windows":
        print(f'  setx SLICER_PATH "{slicer_exe or "<path-to-Slicer>"}"')
    else:
        print(f'  export SLICER_PATH="{slicer_exe or "/path/to/Slicer"}"')
    print("=" * 60)

    # Success = at least one method available
    all_ok = slicer_exe is not None or (has_jc and has_kernel)
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
