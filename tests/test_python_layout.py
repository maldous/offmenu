"""Prove src discovery and package resources survive an offline wheel install."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


class PythonLayout(unittest.TestCase):
    def test_wheel_imports_and_resources_without_checkout_on_path(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='offmenu-wheel-') as directory:
            root = Path(directory)
            artifacts = root/'artifacts'
            artifacts.mkdir()
            command = 'from setuptools.build_meta import build_wheel; build_wheel('+repr(str(artifacts))+')'
            result = subprocess.run([sys.executable, '-I', '-B', '-c', command], cwd=repository, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            wheel, = artifacts.glob('*.whl')
            installed = root/'installed'
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
                for name in ['offmenu/web.html', 'offmenu_ciqual/contract.json', 'offmenu_ciqual/native-contract-v1.json', 'offmenu_norway/contract.json']:
                    self.assertIn(name, names)
                self.assertFalse(any(name.startswith('src/') for name in names))
                archive.extractall(installed)
            script = '''
import importlib, importlib.resources as resources, json, pathlib, sys
sys.path.insert(0, sys.argv[1])
for name in ('offmenu', 'offmenu_ciqual', 'offmenu_norway'):
    module = importlib.import_module(name)
    assert pathlib.Path(module.__file__).is_relative_to(pathlib.Path(sys.argv[1]))
for name in ('offmenu_ciqual', 'offmenu_norway'):
    assert isinstance(json.loads(resources.files(name).joinpath('contract.json').read_text()), dict)
assert resources.files('offmenu').joinpath('web.html').is_file()
from offmenu.refresh import core
assert core.ROOT == pathlib.Path(sys.argv[1])
print('installed-wheel-imports-and-resources-pass')
'''
            result = subprocess.run([sys.executable, '-I', '-B', '-c', script, str(installed)], cwd=root, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('installed-wheel-imports-and-resources-pass', result.stdout)


if __name__ == '__main__':
    unittest.main()
