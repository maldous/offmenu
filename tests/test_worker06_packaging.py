"""Owned fixed catalogue packaging, using generated code artifacts only."""
import ast
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from offmenu.refresh import worker06_bindings as binding

# Canonical SHA256 of the exact reviewed predecessor JSON, including every pin,
# applicability declaration, unknown, timestamp and hold. No source payloads.
REVIEWED_LITERAL_SHA256 = '84eafaf4197b1164bb70c5650e123cacd49ade84670a0f189616e5e9b1d922cb'


class Worker06PackagingTests(unittest.TestCase):
    def test_literal_equivalence_and_defensive_copy_without_resource_reads(self):
        catalog_path = Path(binding.__file__).with_name('worker06_catalog.py')
        tree = ast.parse(catalog_path.read_bytes())
        self.assertEqual(len(tree.body), 2)
        self.assertIsInstance(tree.body[1], ast.Assign)
        self.assertEqual(tree.body[1].targets[0].id, 'CONFIGURATION')
        literal = ast.literal_eval(tree.body[1].value)
        self.assertEqual(binding.fingerprint(literal), REVIEWED_LITERAL_SHA256)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('resource/metadata read forbidden')):
            first = binding.load_config()
            self.assertEqual(binding.fingerprint(first), REVIEWED_LITERAL_SHA256)
            first['bindings'][0]['metadataAsset']['sha256'] = '0' * 64
            first['bindings'][0]['blockers'].clear()
            self.assertEqual(binding.fingerprint(binding.load_config()), REVIEWED_LITERAL_SHA256)

    def test_offline_sdist_to_wheel_installed_catalog(self):
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'source'
            source.mkdir()
            shutil.copytree(repository / 'src/offmenu', source / 'src/offmenu',
                            ignore=shutil.ignore_patterns('__pycache__'))
            shutil.copy2(repository / 'pyproject.toml', source / 'pyproject.toml')
            artifacts = root / 'artifacts'
            artifacts.mkdir()
            run = subprocess.run([sys.executable, '-I', '-B', '-c',
                'from setuptools.build_meta import build_sdist; build_sdist(' + repr(str(artifacts)) + ')'],
                cwd=source, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            archive, = artifacts.glob('*.tar.gz')
            extracted = root / 'sdist'
            extracted.mkdir()
            with tarfile.open(archive, 'r:gz') as tar:
                names = tar.getnames()
                self.assertTrue(any(n.endswith('/offmenu/refresh/worker06_catalog.py') for n in names))
                # Extract only generated ordinary code files/directories. No
                # publisher archive, package install or network is involved.
                for member in tar.getmembers():
                    parts = Path(member.name).parts
                    self.assertFalse(Path(member.name).is_absolute())
                    self.assertNotIn('..', parts)
                    target = extracted / member.name
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        self.assertTrue(member.isfile())
                        target.parent.mkdir(parents=True, exist_ok=True)
                        target.write_bytes(tar.extractfile(member).read())
            rebuilt_source, = extracted.iterdir()
            run = subprocess.run([sys.executable, '-I', '-B', '-c',
                'from setuptools.build_meta import build_wheel; build_wheel(' + repr(str(artifacts)) + ')'],
                cwd=rebuilt_source, capture_output=True, text=True, timeout=60)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            wheel, = artifacts.glob('*.whl')
            installed = root / 'installed'
            with zipfile.ZipFile(wheel) as archive:
                self.assertIn('offmenu/refresh/worker06_catalog.py', archive.namelist())
                archive.extractall(installed)
            script = '''import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from offmenu.refresh import worker06_bindings as module
assert Path(module.__file__).is_relative_to(Path(sys.argv[1]))
with patch.object(Path, 'read_bytes', side_effect=AssertionError('no resource or metadata reads')):
    config = module.load_config()
    assert module.fingerprint(config) == sys.argv[2]
    assert len(config['bindings']) == 13
    assert all(row['blockers'] and not row['permittedPayloadOperations'] for row in config['bindings'])
    config['bindings'].clear()
    assert module.fingerprint(module.load_config()) == sys.argv[2]
print('sdist-wheel-installed-catalog-pass; retained-reads=0')
'''
            run = subprocess.run([sys.executable, '-I', '-B', '-c', script,
                                  str(installed), REVIEWED_LITERAL_SHA256],
                                 cwd=root, capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('sdist-wheel-installed-catalog-pass; retained-reads=0', run.stdout)


if __name__ == '__main__':
    unittest.main()
