"""Run portfolio binding diagnostics in a bounded, offline child process."""
from pathlib import Path
import subprocess
import sys


def main():
    worker = Path(__file__).with_name('worker.py')
    try:
        p = subprocess.run([sys.executable, '-I', '-B', str(worker), *sys.argv[1:]],
                           capture_output=True, timeout=20)
    except subprocess.TimeoutExpired:
        print('{"code":"metadata-worker-timeout","status":"failed"}')
        return 2
    if p.returncode not in (0, 2) or len(p.stdout) > 2 * 1024**2:
        print('{"code":"metadata-worker-process-failed","status":"failed"}')
        return 2
    sys.stdout.buffer.write(p.stdout)
    # Never pass arbitrary source tracebacks to the caller.
    if not p.stdout and p.returncode:
        print('{"code":"metadata-worker-failed","status":"failed"}')
    return p.returncode


if __name__ == '__main__':
    raise SystemExit(main())
