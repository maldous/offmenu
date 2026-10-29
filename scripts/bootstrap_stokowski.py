#!/usr/bin/env python3
"""Install/check the approved pinned Stokowski package in an ignored environment."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

PIN = '339cbf4f3f6d9acdf808f9ba4c639d029cdd8e16'
ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT/'.delivery/stokowski'


def verify_source(source):
    record = json.loads((ROOT/'tools/delivery/stokowski-source.json').read_text())
    if record['source_revision'] != PIN:
        raise SystemExit('Unreviewed source pin')
    for name, expected in record['files'].items():
        path = source/name
        if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise SystemExit('Pinned upstream source mismatch: '+name)
    # Added Python/build files could change installation even when tracked files
    # still match. Only pip-generated build metadata may appear subsequently.
    extras = [p for p in source.rglob('*') if p.is_file()
              and str(p.relative_to(source)) not in record['files']
              and not any(x in p.relative_to(source).parts for x in
                          ('build','stokowski.egg-info','__pycache__','.pytest_cache'))]
    if extras:
        raise SystemExit('Unexpected upstream source files')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    python = RUNTIME/'venv/bin/python'
    if args.check:
        verify_source(RUNTIME/'source')
        code = "import importlib.metadata as m,json;print(json.dumps({d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()}))"
        installed = json.loads(subprocess.check_output([str(python), '-c', code], text=True))
        expected = {'stokowski':'1.1.0'}
        for line in (ROOT/'tools/delivery/stokowski-requirements.lock').read_text().splitlines():
            if line and not line.startswith('#'):
                name, version = line.split('==')
                expected[name.lower().replace('_','-')] = version
        if any(installed.get(k) != v for k, v in expected.items()):
            raise SystemExit('Pinned dependency mismatch')
        subprocess.run([str(python), '-m', 'pip', 'check'], check=True)
        print(json.dumps({'status':'passed','upstream_revision':PIN,'packages':len(expected)}))
        return
    if sys.version_info[:2] != (3, 12):
        raise SystemExit('Use Python 3.12 for the verified Stokowski environment')
    RUNTIME.mkdir(parents=True, exist_ok=True, mode=0o700)
    source = RUNTIME/'source'
    if not source.exists():
        source.mkdir(mode=0o700)
        with tempfile.TemporaryDirectory(prefix='offmenu-stokowski-fetch-') as temporary:
            checkout = Path(temporary)/'source'
            subprocess.run(['git','clone','--no-checkout','--filter=blob:none',
                            'https://github.com/Sugar-Coffee/stokowski.git',str(checkout)],check=True)
            archive = subprocess.check_output(['git','-C',str(checkout),'archive',PIN])
            archive_path = Path(temporary)/'source.tar'
            archive_path.write_bytes(archive)
            with tarfile.open(archive_path) as tar:
                tar.extractall(source, filter='data')
    if not python.exists():
        subprocess.run([sys.executable,'-m','venv',str(RUNTIME/'venv')],check=True)
    verify_source(source)
    subprocess.run([str(python),'-m','pip','install','-r',
                    str(ROOT/'tools/delivery/stokowski-requirements.lock')],check=True)
    subprocess.run([str(python),'-m','pip','install','--no-deps',str(source)],check=True)
    code = "import stokowski,pathlib,json,hashlib; p=pathlib.Path(stokowski.__file__).parent;print(json.dumps({str(f.relative_to(p)):hashlib.sha256(f.read_bytes()).hexdigest() for f in p.rglob('*.py')}))"
    hashes = json.loads(subprocess.check_output([str(python),'-c',code],text=True))
    record = {'source_revision':PIN,'installed_source_sha256':hashes}
    (RUNTIME/'installation.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'status':'installed','revision':PIN,'global_install':False}))


if __name__ == '__main__':
    main()
