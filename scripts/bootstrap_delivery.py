#!/usr/bin/env python3
"""Create/check the pinned project-local delivery environment (Python 3.12).

Never installs into the invoking Python environment. Existing environments are
synchronized to the committed lock; no credentials or services are configured.
"""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
ENVIRONMENT = ROOT / '.venv-delivery'
LOCK = ROOT / 'tools/delivery/requirements.lock'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Verify installed exact versions without network')
    args = parser.parse_args()
    if sys.version_info[:2] != (3, 12):
        parser.error('Use Python 3.12; the delivery lock was validated on that interpreter')
    interpreter = ENVIRONMENT / 'bin/python'
    if args.check:
        if not interpreter.is_file():
            parser.error('Delivery environment missing; run bootstrap without --check')
    else:
        if ENVIRONMENT.is_symlink():
            parser.error('Refuse a symlink environment')
        if ENVIRONMENT.exists() and not (ENVIRONMENT / 'pyvenv.cfg').is_file():
            parser.error('Existing path is not a virtual environment')
        if not interpreter.exists():
            venv.EnvBuilder(with_pip=True).create(ENVIRONMENT)
        subprocess.run([str(interpreter), '-m', 'pip', 'install', '--disable-pip-version-check',
                        '--no-input', '--retries', '1', '--timeout', '15', '-r', str(LOCK)], check=True)
    verify = '''import importlib.metadata as m, json, pathlib, sys
expected = dict(line.strip().split("==") for line in pathlib.Path(sys.argv[1]).read_text().splitlines() if line.strip() and not line.startswith("#"))
errors = {name: {"expected": version, "actual": m.version(name)} for name, version in expected.items() if m.version(name) != version}
print(json.dumps({"status": "failed" if errors else "passed", "pinned_packages": len(expected), "errors": errors}))
sys.exit(bool(errors))
'''
    result = subprocess.run([str(interpreter), '-c', verify, str(LOCK)], check=False)
    if result.returncode:
        return result.returncode
    subprocess.run([str(interpreter), '-m', 'pip', 'check', '--disable-pip-version-check'], check=True)
    # Install the src-layout project itself; locked dependencies/build tools are
    # already checked above, so this step needs neither resolution nor network.
    subprocess.run([str(interpreter), '-m', 'pip', 'install', '--disable-pip-version-check',
                    '--no-input', '--no-deps', '--no-build-isolation', '-e', str(ROOT)], check=True)
    subprocess.run([str(interpreter), '-I', '-c',
                    'import offmenu, offmenu_ciqual, offmenu_norway'], cwd=ROOT.parent, check=True)
    print(json.dumps({'environment': '.venv-delivery', 'python': str(interpreter),
                      'status': 'ready', 'services_started': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
