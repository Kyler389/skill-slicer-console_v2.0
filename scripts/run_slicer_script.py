#!/usr/bin/env python3
"""
Execute a Python script via the Slicer Jupyter kernel.

Usage:
    python run_slicer_script.py --script ./task.py
    python run_slicer_script.py --script ./task.py --kernel slicer-5.6 --timeout 120
"""

import argparse
import sys
import os


def main():
    parser = argparse.ArgumentParser(description="Run a Python script in Slicer via Jupyter kernel")
    parser.add_argument("--script", required=True, help="Path to the Python script to execute")
    parser.add_argument("--kernel", default="slicer-5.6", help="Jupyter kernel name (default: slicer-5.6)")
    parser.add_argument("--timeout", type=int, default=60, help="Seconds to wait for kernel ready (default: 60)")
    args = parser.parse_args()

    script_path = os.path.abspath(args.script)
    if not os.path.isfile(script_path):
        print(f"ERROR: Script not found: {script_path}", file=sys.stderr)
        sys.exit(1)

    with open(script_path, "r", encoding="utf-8") as f:
        code = f.read()

    try:
        from jupyter_client import KernelManager
    except ImportError as e:
        print(f"ERROR: jupyter_client is not installed. {e}", file=sys.stderr)
        print("Fix: pip install jupyter_client", file=sys.stderr)
        sys.exit(1)

    km = KernelManager(kernel_name=args.kernel)
    kc = None
    exit_code = 0

    try:
        print(f"[INFO] Starting kernel '{args.kernel}'...")
        km.start_kernel()

        kc = km.client()
        kc.start_channels()
        kc.wait_for_ready(timeout=args.timeout)
        print(f"[INFO] Kernel ready. Executing: {script_path}")

        msg_id = kc.execute(code)

        # Collect iopub messages until execution is idle
        while True:
            try:
                msg = kc.get_iopub_msg(timeout=10)
            except Exception:
                continue

            msg_type = msg["header"]["msg_type"]
            content = msg["content"]

            if msg_type == "status" and content.get("execution_state") == "idle":
                parent = msg.get("parent_header", {})
                if parent.get("msg_id") == msg_id:
                    break

            if msg_type == "stream":
                text = content.get("text", "")
                stream_name = content.get("name", "stdout")
                if stream_name == "stderr":
                    print(text, end="", file=sys.stderr)
                else:
                    print(text, end="")

            elif msg_type == "execute_result":
                data = content.get("data", {})
                text = data.get("text/plain", "")
                if text:
                    print(text)

            elif msg_type == "error":
                ename = content.get("ename", "Error")
                evalue = content.get("evalue", "")
                traceback = content.get("traceback", [])
                print(f"\nERROR: {ename}: {evalue}", file=sys.stderr)
                for line in traceback:
                    print(line, file=sys.stderr)
                exit_code = 1

        print(f"\n[INFO] Execution finished. Exit code: {exit_code}")

    except Exception as e:
        print(f"ERROR: Kernel execution failed: {e}", file=sys.stderr)
        exit_code = 1

    finally:
        if kc:
            kc.stop_channels()
        try:
            km.shutdown_kernel(now=True)
            print("[INFO] Kernel shutdown.")
        except Exception:
            pass

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
