"""Behavior checks: pinned RECORDs, complete imports, fixed copies and no replay."""
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
import native_harness_package as package
import protected_owner_install as protected


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o700)
        self.site = self.root / 'site'; self.site.mkdir()
        self.pins, self.locks = {}, []
        for name in package.ROOT_DISTRIBUTIONS:
            directory = name.replace('-', '_') + '-1.1.0.dist-info'
            files = {directory + '/METADATA': ('Name: ' + name + '\nVersion: 1.1.0\n').encode(),
                     name.replace('-', '_') + '/__init__.py': b'VALUE = 1\n'}
            if name == 'stokowski':
                files.update({'editable.pth': b'import evil\n',
                              'x.egg-link': b'/unsafe\n',
                              'stokowski/__pycache__/bad.pyc': b'not source'})
            for relative, raw in files.items():
                path = self.site / relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
            output = io.StringIO(); writer = csv.writer(output)
            for relative, raw in files.items():
                digest = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
                writer.writerow([relative, 'sha256=' + digest, str(len(raw))])
            writer.writerow(['../../../bin/command', '', ''])
            writer.writerow([directory + '/RECORD', '', ''])
            record = self.site / directory / 'RECORD'; record.write_text(output.getvalue())
            self.pins[directory + '/METADATA'] = package.sha(files[directory + '/METADATA'])
            self.pins[directory + '/RECORD'] = package.sha(record.read_bytes())
            self.locks.append(name + '==1.1.0')
        self.upstream = dict(version='1.1.0', source_revision='a'*40,
                             files={'stokowski/__init__.py': package.sha(b'VALUE = 1\n')})

    def projection(self):
        return package.selected_distribution_files(self.site, lock_bytes=['\n'.join(self.locks).encode()],
                    upstream=self.upstream, metadata_pins=self.pins)

    def test_only_exact_record_pinned_public_ca_resource_is_allowed(self):
        package.path_name('certifi/cacert.pem')
        package.closure('owner_venv',{package.PYTHON+'certifi/cacert.pem':b'public CA fixture'})
        for name in ('secret.pem','other/cacert.pem',package.PYTHON+'certifi/private.pem'):
            with self.assertRaises(ValueError):package.path_name(name)

    def test_record_projection_omits_bootstrap_scripts_and_bytecode(self):
        files, evidence = self.projection()
        self.assertEqual(len(evidence['versions']), 4)
        self.assertFalse(any(package.excluded_record(n) for n in files))
        self.assertTrue(any(n.endswith('stokowski/__init__.py') for n in files))
        self.assertEqual(len(evidence['omitted']), 7)

    def test_metadata_record_and_package_tamper_fail_before_output(self):
        path = self.site / 'stokowski/__init__.py'
        path.write_bytes(b'unreviewed')
        with self.assertRaises(ValueError): self.projection()
        path.write_bytes(b'VALUE = 1\n')
        metadata = next(self.site.glob('stokowski-*.dist-info/METADATA'))
        metadata.write_text('Name: stokowski\nVersion: 2.0\n')
        with self.assertRaises(ValueError): self.projection()

    def test_missing_unhashed_record_pin_and_upstream_mismatch_hold(self):
        del self.pins['stokowski-1.1.0.dist-info/RECORD']
        with self.assertRaises(ValueError): self.projection()
        self.pins['stokowski-1.1.0.dist-info/RECORD'] = package.sha((self.site/'stokowski-1.1.0.dist-info/RECORD').read_bytes())
        self.upstream['files']['stokowski/__init__.py'] = '0'*64
        with self.assertRaises(ValueError): self.projection()

    def test_link_and_duplicate_distribution_file_conflict_hold(self):
        path = self.site/'stokowski/__init__.py'
        raw=path.read_bytes(); path.unlink(); path.symlink_to(self.root/'elsewhere')
        with self.assertRaises((ValueError, OSError)): self.projection()
        path.unlink(); path.write_bytes(raw)
        # Conflicting duplicate RECORD rows cannot silently replace an accepted path.
        record=self.site/'stokowski-1.1.0.dist-info/RECORD'
        record.write_text(record.read_text()+'stokowski/__init__.py,,\n')
        self.pins['stokowski-1.1.0.dist-info/RECORD']=package.sha(record.read_bytes())
        with self.assertRaises(ValueError): self.projection()

    def source(self):
        source = {'src/offmenu/__init__.py': b'',
                  'src/offmenu/delivery/integration.py': b'from .engine import VALUE\n',
                  'src/offmenu/delivery/engine.py': b'VALUE = 1\n',
                  'tools/delivery/native_rpc.py': b'from native_lifecycle import VALUE\n',
                  'tools/delivery/native_lifecycle.py': b'from extra_dependency import VALUE\n',
                  'src/extra_dependency.py': b'VALUE = 2\n',
                  'tools/delivery/native_publisher_invocation.py': b'from native_rpc import VALUE\n',
                  'tools/delivery/windmill_runner.py': b'VALUE = 1\n',
                  'tools/delivery/protected_owner_install.py': b'VALUE = 1\n'}
        for name in ('github-app-publisher.mjs', 'github-app-adapter.mjs', 'integration-gateway.mjs'):
            source['tools/delivery/'+name]=b'export const value = 1;\n'
        for name in ('contracts/schemas/delivery-handoff-v1.schema.json',
                     'config/delivery-release-policy.json', 'config/release-validation-profile.json',
                     'tools/delivery/capacity-policy.json'):
            source[name]=b'{}\n'
        return source

    def test_import_closure_includes_rpc_lifecycle_and_transitive_source(self):
        source=self.source()
        selected=package.publisher_sources(source)
        self.assertIn('tools/delivery/native_rpc.py',selected)
        self.assertIn('tools/delivery/native_lifecycle.py',selected)
        self.assertIn('src/extra_dependency.py',selected)
        source['tools/delivery/native_rpc.py']=b'import importlib\nimportlib.import_module(chosen)\n'
        with self.assertRaises(ValueError): package.publisher_sources(source)
        source['tools/delivery/native_rpc.py']=b'from native_missing import value\n'
        with self.assertRaises(ValueError): package.publisher_sources(source)

    def build(self):
        repo=self.root/'repo';repo.mkdir()
        source=self.source()
        # Never execute this accepted payload while producing or materializing it.
        source['src/extra_dependency.py']=b"raise RuntimeError('PAYLOAD EXECUTED')\n"
        for name,raw in source.items():
            path=repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        def git(*args):
            return subprocess.check_output(['git','-C',str(repo),*args],stderr=subprocess.DEVNULL).decode().strip()
        git('init','-q');git('add','.')
        git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','source')
        head,tree=git('rev-parse','HEAD'),git('rev-parse','HEAD^{tree}')
        deps,evidence=self.projection()
        interpreter=b'fixed interpreter byte fixture'
        current=protected.encoded(dict(source_head=head,catalog='/etc/offmenu-stokowski-current/catalog.json',
                    source_sha256={'src/offmenu/delivery/integration.py':package.sha(source['src/offmenu/delivery/integration.py'])},
                    runtime_root='/home/user/src/offmenu/.delivery/stokowski'))
        catalog=protected.encoded(dict(version=1,entries=[]))
        publisher=protected.encoded(dict(sourceHead=head,publisherUid=984,publisherGid=976,repositoryId=1416253963,
                    pythonSha256=package.sha(interpreter),codePins={'tools/delivery/github-app-publisher.mjs':package.sha(source['tools/delivery/github-app-publisher.mjs'])}))
        stage=self.root/'package'
        result=package.prepare_coherent_package(stage,git_dir=repo/'.git',head=head,tree=tree,
                    dependencies=deps,dependency_evidence=evidence,
                    dependency_sha256=package.sha(protected.encoded({n:package.sha(raw) for n,raw in sorted(deps.items())})),
                    runtime='/home/user/src/offmenu/.delivery/stokowski/selected',
                    interpreter=interpreter,interpreter_sha256=package.sha(interpreter),
                    interpreter_custody={'path':'custody.json','sha256':'c'*64},
                    node_sha256='f'*64,node_custody={'path':'node-custody.json','sha256':'9'*64},
                    pyvenv_cfg=b'home = /usr/bin\ninclude-system-site-packages = false\nversion = 3.12.3\n',
                    owner_current=current,owner_catalog=catalog,publisher_config=publisher,
                    config_pins=dict(owner_current=package.sha(current),owner_catalog=package.sha(catalog),publisher_config=package.sha(publisher)),
                    acceptance=package.PackageAcceptance('root-owner',head,tree,{'path':'review.json','sha256':'b'*64}))
        return stage,result

    def host(self):
        root=self.root/'host';root.mkdir(mode=0o700)
        for name in ('opt/offmenu-stokowski-current','etc/offmenu-publisher',
                     'etc','var/lib/offmenu-publisher'):
            (root/name).mkdir(parents=True,exist_ok=True)
        for directory in root.rglob('*'):
            if directory.is_dir(): directory.chmod(0o755)
        # The real key is deliberately never parsed/read by the copier.
        (root/'etc/offmenu-publisher/existing.pem').write_text('untouched secret sentinel')
        return package.MaterializeHost(_synthetic=root)

    def admission(self, result):
        return package.MaterializeAdmission('root-owner',result['sha256'],'d'*64,'e'*64,time.time()+60)

    def test_exact_package_materializes_all_roles_without_payload_execution_or_key_access(self):
        stage,result=self.build();host=self.host()
        with patch.object(subprocess,'run',side_effect=AssertionError('payload command')):
            output=package.materialize(stage,expected_sha256=result['sha256'],admission=self.admission(result),_host=host)
        self.assertFalse(output['activated'])
        self.assertEqual(set(output['stages']),set(package.ROLES))
        config=output['stages']['publisher_config']
        self.assertEqual(config,'/etc/offmenu-publisher/.native-upgrade-'+'d'*64+'-publisher_config.new.json')
        self.assertEqual((host.root/'etc/offmenu-publisher/existing.pem').read_text(),'untouched secret sentinel')
        with self.assertRaises(ValueError):
            package.materialize(stage,expected_sha256=result['sha256'],admission=self.admission(result),_host=host)

    def test_tamper_extra_role_and_unknown_closure_fail_before_intent(self):
        stage,result=self.build();host=self.host()
        raw=json.loads((stage/'manifest.json').read_bytes())
        raw['roles']['extra']=raw['roles']['owner_config']
        manifest=protected.encoded(raw);(stage/'manifest.json').chmod(0o600);(stage/'manifest.json').write_bytes(manifest)
        with self.assertRaises(ValueError):
            package.materialize(stage,expected_sha256=package.sha(manifest),admission=package.MaterializeAdmission('root-owner',package.sha(manifest),'d'*64,'e'*64,time.time()+60),_host=host)
        self.assertFalse(list((host.root/'var/lib/offmenu-publisher').glob('*')))

    def test_shared_descriptor_binds_all_files_and_excludes_itself(self):
        stage,result=self.build()
        manifest,content=package.read_package(stage,result['sha256'])
        raw=content['publisher']['native-harness-closure.json']
        descriptor=protected.record(raw)
        self.assertEqual(set(descriptor),{'version','kind','source_head','source_tree','node_sha256','files'})
        self.assertEqual(descriptor['node_sha256'],'f'*64)
        self.assertNotIn('native-harness-closure.json',descriptor['files'])
        self.assertIn('tools/delivery/native_publisher_invocation.py',descriptor['files'])
        self.assertIn('tools/delivery/windmill_runner.py',descriptor['files'])
        self.assertEqual(descriptor['files']['venv/bin/python'],package.sha(content['owner_venv']['bin/python']))
        self.assertEqual(raw,protected.encoded(descriptor))
        missing=dict(content['publisher']);del missing['native-harness-closure.json'];del missing['tools/delivery/native_publisher_invocation.py']
        with self.assertRaises(ValueError):package.publisher_descriptor(missing,head=manifest['head'],tree=manifest['tree'],node_sha256='f'*64)

    def test_changed_payload_bytes_fail_before_materialization_intent(self):
        stage,result=self.build();host=self.host()
        manifest=json.loads((stage/'manifest.json').read_bytes())
        item=next(iter(manifest['roles']['owner_source']['files'].values()))
        payload=stage/'payload'/item['sha256']
        payload.chmod(0o600);payload.write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            package.materialize(stage,expected_sha256=result['sha256'],admission=self.admission(result),_host=host)
        self.assertFalse(list((host.root/'var/lib/offmenu-publisher').glob('*')))

    def test_payload_tamper_and_partial_stage_refuse_replay(self):
        stage,result=self.build();host=self.host()
        original=host.write
        count=[0]
        def partial(*args,**kwargs):
            count[0]+=1
            if count[0]==3:raise OSError('interrupted copy')
            return original(*args,**kwargs)
        with patch.object(host,'write',side_effect=partial):
            with self.assertRaises(OSError):
                package.materialize(stage,expected_sha256=result['sha256'],admission=self.admission(result),_host=host)
        self.assertTrue(list((host.root/'var/lib/offmenu-publisher').glob('*.intent.json')))
        with self.assertRaises(ValueError):
            package.materialize(stage,expected_sha256=result['sha256'],admission=self.admission(result),_host=host)

    def test_json_admission_and_wrong_owner_cannot_authorize_copy(self):
        stage,result=self.build()
        with self.assertRaises(ValueError):
            package.materialize(stage,expected_sha256=result['sha256'],admission={'package_sha256':result['sha256']})
        bad=package.MaterializeAdmission('other',result['sha256'],'d'*64,'e'*64,time.time()+60)
        with self.assertRaises(ValueError):
            package.materialize(stage,expected_sha256=result['sha256'],admission=bad,_host=self.host())

    def test_fixed_metadata_paths_and_file_directory_collisions(self):
        for role,files in [('owner_config',{'unexpected.json':b'x'}),('publisher_config',{'existing.pem':b'x'}),
                           ('owner_source',{'a':b'x','a/b':b'y'}),
                           ('owner_venv',{package.PYTHON+'unsafe.pth':b'import evil'}),
                           ('publisher',{'venv/bin/unsafe-script':b'evil'})]:
            with self.subTest(role=role), self.assertRaises(ValueError):package.closure(role,files)
        with self.assertRaises(ValueError): package.slots('../escape')


if __name__=='__main__':unittest.main()
