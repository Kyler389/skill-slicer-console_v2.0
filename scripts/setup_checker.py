#!/usr/bin/env python3
"""
Check slicer-console skill prerequisites and guide the user through setup.

Usage:
    python setup_checker.py
    python setup_checker.py --kernel slicer-5.6
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys


def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, shell=True, encoding="utf-8", errors="replace")
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_jupyter_cli():
    ok, out, err = run_cmd("jupyter --version")
    return ok


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


def find_slicer_executable():
    system = platform.system()
    candidates = []
    if system == "Windows":
        candidates += [
            r"D:\slicer\Slicer 5.6.1\Slicer.exe",
            r"D:\slicer\Slicer 5.6.2\Slicer.exe",
            r"C:\Program Files\Slicer 5.6.1\Slicer.exe",
            r"C:\Program Files\Slicer 5.6.2\Slicer.exe",
            r"C:\Program Files\Slicer\Slicer.exe",
        ]
    elif system == "Darwin":
        candidates += [
            "/Applications/Slicer.app/Contents/MacOS/Slicer",
            "/Applications/Slicer-5.6.1.app/Contents/MacOS/Slicer",
            "/Applications/Slicer-5.6.2.app/Contents/MacOS/Slicer",
        ]
    else:
        candidates += [
            "/opt/slicer/Slicer",
            "/usr/local/bin/Slicer",
            os.path.expanduser("~/Slicer/Slicer"),
        ]

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def get_pythonslicer_path(slicer_exe):
    if not slicer_exe:
        return None
    base = os.path.dirname(slicer_exe)
    candidates = [
        os.path.join(base, "bin", "PythonSlicer.exe"),
        os.path.join(base, "..", "bin", "PythonSlicer.exe"),
        os.path.join(base, "bin", "python-real"),
        os.path.join(base, "..", "bin", "python-real"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def print_result(name, ok, message=""):
    if ok:
        status = "[OK]"
    else:
        status = "[FAIL]"
    print(f"  {status} {name}", end="")
    if message:
        print(f" — {message}")
    else:
        print()


def main():
    parser = argparse.ArgumentParser(description="Check slicer-console prerequisites")
    parser.add_argument("--kernel", default="slicer-5.6", help="Kernel name to check (default: slicer-5.6)")
    args = parser.parse_args()

    print("=" * 60)
    print("slicer-console Skill Setup Checker")
    print("=" * 60)

    # 1. jupyter CLI
    has_jupyter = check_jupyter_cli()
    print_result("jupyter CLI available", has_jupyter)

    # 2. jupyter_client
    has_jc = check_jupyter_client()
    print_result("jupyter_client Python package", has_jc)
    if not has_jc:
        print("      Fix: pip install jupyter_client")

    # 3. Kernel spec
    kernel_path = find_kernelspec(args.kernel)
    has_kernel = kernel_path is not None and os.path.isdir(kernel_path)
    print_result(f"Kernel spec '{args.kernel}' registered", has_kernel, kernel_path or "not found")
    if not has_kernel:
        print("      Fix: See 'Manual Setup' section in SKILL.md to install the SlicerJupyter kernel.")

    # 4. Slicer executable
    slicer_exe = find_slicer_executable()
    print_result("Slicer executable found", slicer_exe is not None, slicer_exe or "not found in common paths")

    # 5. PythonSlicer
    pslicer = get_pythonslicer_path(slicer_exe)
    print_result("PythonSlicer found", pslicer is not None, pslicer or "not found")

    print("\n" + "=" * 60)
    if has_jupyter and has_jc and has_kernel and slicer_exe and pslicer:
        print("All checks passed! You are ready to use the slicer-console skill.")
    else:
        print("Some prerequisites are missing. Follow the fixes above.")
        print("\nNext steps:")
        print("  1. Open Slicer GUI")
        print("  2. Install the 'SlicerJupyter' extension (View -> Extension Manager)")
        print("  3. Restart Slicer")
        print("  4. In Slicer Python Interactor (View -> Python Interactor), run:")
        print(f"     jupyter-kernelspec install '<SlicerExtPath>/SlicerJupyter/share/Slicer-5.6/qt-loadable-modules/JupyterKernel/Slicer-5.6' --replace --user")
        if pslicer:
            print(f"  5. Install IPython into Slicer Python:")
            print(f'     "{pslicer}" -m pip install ipython')
        print("  6. Re-run this checker to verify.")
    print("=" * 60)

    sys.exit(0 if (has_jupyter and has_jc and has_kernel and slicer_exe and pslicer) else 1)


if __name__ == "__main__":
    main()
