"""Run both real development servers; stop siblings when one exits."""
import argparse
from pathlib import Path
import os
import signal
import subprocess
import time

parser = argparse.ArgumentParser()
parser.add_argument("--uv", default="uv")
parser.add_argument("--pnpm", default="pnpm")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
processes = []
environment = dict(os.environ, NEXT_TELEMETRY_DISABLED="1")
def cleanup():
    for process in processes:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
    for process in processes:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)

def stop(*_):
    cleanup()
    raise SystemExit(0)

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)
try:
    processes.append(subprocess.Popen([args.uv, "run", "--directory", "apps/api", "--env-file", "../../.env", "uvicorn", "mealforge.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-proxy-headers", "--no-access-log", "--reload"], cwd=root, env=environment, start_new_session=True))
    processes.append(subprocess.Popen([args.pnpm, "dev"], cwd=root, env=environment, start_new_session=True))
    while all(process.poll() is None for process in processes):
        time.sleep(1)
    exit_code = next((process.returncode for process in processes if process.returncode), 1)
finally:
    cleanup()
raise SystemExit(exit_code)
