#!/usr/bin/env python
import json
import argparse
import subprocess
import os
import signal
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIDFILE    = SCRIPT_DIR / "gatsim_backend.pid"

def is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True

def load_config(cfg_path: str) -> dict:
    # 1) Try absolute or relative to this script
    cfg_file = Path(cfg_path)
    if not cfg_file.exists():
        cfg_file = SCRIPT_DIR / cfg_path
    if not cfg_file.exists():
        print(f"❌  Config file not found: {cfg_path}", file=sys.stderr)
        sys.exit(1)

    # 2) Parse JSON
    try:
        cfg = json.loads(cfg_file.read_text())
    except Exception as e:
        print(f"❌  Failed to parse JSON ({cfg_file}): {e}", file=sys.stderr)
        sys.exit(1)

    # 3) Ensure required keys
    for key in ("fork", "name", "cmd"):
        if key not in cfg:
            print(f"❌  Missing '{key}' in config file", file=sys.stderr)
            sys.exit(1)
            
    # to handle commands with spaces
    for key, value in cfg.items():
        cfg[key] = '"' + value + '"'
    return cfg

def start_backend(cfg_path: str):
    # A) Stale‐PID cleanup
    if PIDFILE.exists():
        old_pid = int(PIDFILE.read_text())
        if is_running(old_pid):
            print(f"⚠️  Backend already running (PID={old_pid}).", file=sys.stderr)
            sys.exit(0)
        else:
            print(f"⚠️  Removing stale PID file (PID {old_pid} not found).", file=sys.stderr)
            PIDFILE.unlink()

    # B) Load & validate config
    cfg = load_config(cfg_path)

    # C) Locate your flat backend.py
    script_path = SCRIPT_DIR.parent /"gatsim" / "backend.py"
    if not script_path.exists():
        print(f"❌  Could not find backend script at {script_path}", file=sys.stderr)
        sys.exit(1)

    # D) Build & spawn
    cmd = [
        sys.executable,
        str(script_path),
        "--fork", str(cfg["fork"]),
        "--name",  cfg["name"],
        "--cmd",   cfg["cmd"],
    ]
  
    p = subprocess.Popen(cmd)
    PIDFILE.write_text(str(p.pid))
    print(f"✅  Started backend (PID={p.pid})")
    sys.exit(0)

def stop_backend():
    if not PIDFILE.exists():
        print("⚠️  No backend running (pidfile missing).", file=sys.stderr)
        sys.exit(0)

    pid = int(PIDFILE.read_text())
    if is_running(pid):
        os.kill(pid, signal.SIGTERM)
        print(f"✅  Sent SIGTERM to backend (PID={pid})")
    else:
        print(f"⚠️  Backend PID {pid} not running; cleaning up.", file=sys.stderr)

    PIDFILE.unlink()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="start/stop GATSim backend")
    parser.add_argument("--start", action="store_true", help="Begin running")
    parser.add_argument("--stop",  action="store_true", help="Halt simulation")
    parser.add_argument(
        "-c", "--config",
        default="frontend/backend_args.json",
        help="Path to JSON config (default: backend_args.json)"
    )
    args = parser.parse_args()

    if args.start:
        start_backend(args.config)
    elif args.stop:
        stop_backend()
    else:
        parser.print_usage()
        sys.exit(1)