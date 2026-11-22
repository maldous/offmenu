"""Generated originals/evidence/DBs only, never retained or live source paths."""
from copy import deepcopy
from dataclasses import asdict, replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import off_native_policy as policy
from offmenu.refresh import off_native_binding as binding
from offmenu.refresh import product_adapters as adapters
from offmenu.refresh.acceptance import Asset, SourceContract, accept, canonical, fingerprint, ids_digest, qualify
from offmenu.refresh.core import RefreshError
from offmenu.refresh.product_qualification import qualify_product_candidate


class OffNativeBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.inputs=self.root/'originals';self.inputs.mkdir()
        self.bundle=self.root/'evidence';self.bundle.mkdir();self.normalized=self.root/'normalized'
        self.rows=[{'code':'00012345','product_name':'Authored A','ingredients_text':'Water / oat ~ salt',
                    'nutriments':{'proteins_100g':'1.25','sodium_100g':0},'rev':7},
                   {'code':'9999','product_name':'Authored B','nutriments':{},'countries_tags':None}]
        raw=gzip.compress(b''.join(canonical(r)+b'\n' for r in self.rows),mtime=0)
        self.source=Asset('off-2026-10-12.jsonl.gz',len(raw),hashlib.sha256(raw).hexdigest())
        (self.inputs/self.source.path).write_bytes(raw)
        # Explicit synthetic test substitution only. Production API adds no source
        # override, fixture toggle, real witness/count or resource constructor.
        self.override=patch.object(policy,'SOURCE',self.source);self.override.start()
        policy._validators.cache_clear()
        self.addCleanup(self.override.stop);self.addCleanup(policy._validators.cache_clear)
        def asset(name,value):
            raw=canonical(value);(self.bundle/name).write_bytes(raw)
            return Asset(name,len(raw),hashlib.sha256(raw).hexdigest())
        rights=asset('rights.json',{'fixture':True,'purpose':'authored test only'})
        scope_id='authored-off-binding-fixture'
        clock=asset('clock.json',{'schemaVersion':'offmenu-retained-clock-evidence/1',
            'sourceId':'off','releaseId':policy.RELEASE,'scopeId':scope_id,'status':'unknown-retained',
            'originalAcquiredAt':None,'basisEvidenceSha256':'f'*64,
            'rightsEvidenceSha256':rights.sha256,'inputFiles':[asdict(self.source)]})
        scope=asset('scope.json',{'sourceId':'off','releaseId':policy.RELEASE,'scopeId':scope_id,
            'acquisitionClock':{'status':'unknown-retained','evidenceSha256':clock.sha256}})
        self.context=adapters.ProductContext('off',policy.RELEASE,None,policy.LICENSE,policy.ATTRIBUTION,
            rights.sha256,scope.sha256,acquisition_clock_status='unknown-retained',clock_evidence_sha256=clock.sha256)
        schemas=policy.native_schemas()
        self.contract=SourceContract('off',policy.RELEASE,scope_id,None,
            (self.source,rights,scope,clock),4,
            ids_digest(['off:'+kind+':'+r['code'] for r in self.rows for kind in ('product','nutrientProfile')]),
            schemas,fingerprint(schemas),policy.UnboundOffSemantics(self.context),
            fingerprint({'fixture':'OFFbinding'}),rights,scope,frozenset(('retain','parse','transform')),
            fixture=True,acquisition_clock_status='unknown-retained',clock_evidence=clock)
        self.limits=adapters.ProductLimits()
        self.original=adapters.normalize_products(self.context,
            {'products':self.inputs/self.source.path},self.normalized,limits=self.limits)
        self.manifest=self.qualified_manifest(self.original)
        self.select_independent_fixture_pins()
        self.records=[json.loads(line)[0] for line in (self.normalized/'candidate.jsonl').read_bytes().splitlines()]

    def select_independent_fixture_pins(self):
        # Trusted fixture setup knows which authored original was actually parsed.
        # This models a separately reviewed application selection, NOT a production
        # cache-to-authority helper. The forged-cache regression does not call it.
        pins=binding.DerivationPins(self.manifest['normalizationManifestSha256'],
            self.manifest['outputHashes']['source.sqlite'],
            self.manifest['outputHashes']['candidate.jsonl'],'e'*64)
        semantic=binding.PinnedOffSemantics(self.context,pins)
        self.contract=replace(self.contract,semantic_validator=semantic,
            policy_sha256=binding.derivation_policy_sha256(semantic))

    def qualified_manifest(self,original):
        return {**deepcopy(original),'inputFiles':[asdict(a) for a in sorted(self.contract.inputs,key=lambda a:a.path)],
            'normalizationManifestSha256':hashlib.sha256((self.normalized/'manifest.json').read_bytes()).hexdigest(),
            'inputRoleMap':{'products':self.source.path}}

    def bind(self,contract=None,manifest=None,limits=None):
        return binding.bind_normalized_semantics(self.contract if contract is None else contract,
            self.normalized,self.manifest if manifest is None else manifest,self.limits if limits is None else limits)

    def repin_db_in_fixture_metadata(self):
        original=json.loads((self.normalized/'manifest.json').read_bytes())
        original['outputHashes']['source.sqlite']=hashlib.sha256((self.normalized/'source.sqlite').read_bytes()).hexdigest()
        (self.normalized/'manifest.json').write_bytes(canonical(original))
        self.manifest=self.qualified_manifest(original)
        self.select_independent_fixture_pins()

    def test_bound_both_kinds_qualify_accept_and_expire_without_mutation(self):
        files={p.name:p.read_bytes() for p in self.normalized.iterdir()}
        with self.bind() as checked:
            for row in self.records:self.assertEqual(checked.semantic_validator(row),[])
            result=qualify(checked,self.bundle,self.normalized/'candidate.jsonl',self.manifest,input_root=self.inputs)
            self.assertTrue(result['qualified'],result['errors'])
            receipt=accept(checked,self.bundle,self.normalized/'candidate.jsonl',self.manifest,input_root=self.inputs)
            self.assertEqual(receipt['status'],'accepted-fixture-scope')
            self.assertFalse(receipt['productionAccepted'])
        self.assertEqual(checked.semantic_validator(self.records[0]),['off-native-source-authority-expired'])
        self.assertEqual(files,{p.name:p.read_bytes() for p in self.normalized.iterdir()})

    def test_unbound_direct_qualification_stays_held(self):
        result=qualify(self.contract,self.bundle,self.normalized/'candidate.jsonl',self.manifest,input_root=self.inputs)
        self.assertFalse(result['qualified'])
        self.assertIn('off-native-source-authority-required',result['errors'])

    def test_category_projection_stamp_is_required_and_exact_in_bound_manifest(self):
        for value in (None, 'unreviewed-category-projection'):
            manifest = deepcopy(self.manifest)
            if value is None:
                del manifest['contract']['offCategoryFieldProjectionVersion']
            else:
                manifest['contract']['offCategoryFieldProjectionVersion'] = value
            with self.subTest(value=value), self.assertRaisesRegex(RefreshError, 'manifest-context'):
                with self.bind(manifest=manifest):
                    self.fail('stale or changed category projection must not bind')

    def test_optional_projection_stamp_is_required_and_exact_in_bound_manifest(self):
        key = 'offOptionalNutritionNamesProjectionVersion'
        self.assertEqual(self.manifest['contract'][key], adapters.OFF_OPTIONAL_PROJECTION_VERSION)
        with self.bind() as checked:
            for row in self.records:
                self.assertEqual(checked.semantic_validator(row), [])
        for value in (None, 'unreviewed-optional-projection'):
            manifest = deepcopy(self.manifest)
            if value is None:
                del manifest['contract'][key]
            else:
                manifest['contract'][key] = value
            with self.subTest(value=value), self.assertRaisesRegex(RefreshError, 'manifest-context'):
                with self.bind(manifest=manifest):
                    self.fail('stale or changed optional projection must not bind')

    def test_bridge_hook_qualifies_and_retries_same_frozen_inputs(self):
        for _ in range(2):
            output=qualify_product_candidate(self.contract,self.bundle,{'products':self.source.path},self.normalized,
                license=policy.LICENSE,attribution=policy.ATTRIBUTION,limits=self.limits,input_root=self.inputs)
            self.assertTrue(output['qualification']['qualified'],output['qualification']['errors'])
        self.assertIsInstance(self.contract.semantic_validator,policy.UnboundOffSemantics)

    def test_wrong_context_contract_holds_operations_and_inputs_reject(self):
        bad=[replace(self.contract,holds=('held',)),
             replace(self.contract,permitted_operations=frozenset(('retain',))),
             replace(self.contract,source_id='prices'),replace(self.contract,release_id='other'),
             replace(self.contract,expected_records=2),replace(self.contract,output_visibility='public'),
             replace(self.contract,inputs=self.contract.inputs[1:]),
             replace(self.contract,scope_evidence=replace(self.contract.scope_evidence,sha256='f'*64)),
             replace(self.contract,semantic_validator=policy.UnboundOffSemantics(replace(self.context,scope_evidence_sha256='f'*64)))]
        for contract in bad:
            with self.subTest(contract=contract.source_id),self.assertRaises(RefreshError):
                with self.bind(contract):pass

    def test_missing_wrong_manifest_and_db_pins_reject(self):
        for name in ('manifest.json','source.sqlite'):
            path=self.normalized/name;raw=path.read_bytes()
            path.unlink()
            with self.assertRaises(RefreshError):
                with self.bind():pass
            path.write_bytes(raw)
            path.write_bytes(raw+b'changed')
            with self.assertRaises(RefreshError):
                with self.bind():pass
            path.write_bytes(raw)
        for field,value in (('normalizationManifestSha256','f'*64),('outputHashes',{'source.sqlite':'f'*64}),
                            ('inputFiles',[]),('inputRoleMap',{'products':'other.gz'})):
            manifest=deepcopy(self.manifest);manifest[field]=value
            with self.assertRaises(RefreshError):
                with self.bind(manifest=manifest):pass

    def test_normalization_context_role_source_limit_and_version_drift_reject(self):
        for key,value in (('adapterVersion','other'),('clockPolicySha256','f'*64),
                          ('inputFiles',[{'role':'products','path':'wrong','bytes':1,'sha256':'f'*64}]),
                          ('context',{}),('limits',{})):
            manifest=deepcopy(self.manifest);manifest['contract'][key]=value
            with self.assertRaises(RefreshError):
                with self.bind(manifest=manifest):pass
        with self.assertRaises(RefreshError):
            with self.bind(limits=replace(self.limits,max_rows=self.limits.max_rows+1)):pass
        manifest=deepcopy(self.manifest)
        manifest['contract']['context']['cache_seconds']=float(self.context.cache_seconds)
        with self.assertRaises(RefreshError):
            with self.bind(manifest=manifest):pass

    def test_updated_caller_pin_cannot_substitute_inconsistent_disk_manifest(self):
        original=json.loads((self.normalized/'manifest.json').read_bytes());original['rawRows']=3
        raw=canonical(original);(self.normalized/'manifest.json').write_bytes(raw)
        manifest=deepcopy(self.manifest);manifest['normalizationManifestSha256']=hashlib.sha256(raw).hexdigest()
        with self.assertRaises(RefreshError):
            with self.bind(manifest=manifest):pass
        manifest=self.qualified_manifest(original)
        with self.assertRaises(RefreshError):
            with self.bind(manifest=manifest):pass

    def test_db_lookup_rejects_missing_identity_wrong_ordinal_and_forged_source_code(self):
        row=deepcopy(self.records[0]);row['provenance']['recordId']='1111'
        with self.bind() as checked:
            self.assertEqual(checked.semantic_validator(row),['off-native-source-row-required'])
            wrong=deepcopy(self.records[0]);wrong['provenance']['sourceRow']=2
            self.assertTrue(checked.semantic_validator(wrong))
        db=sqlite3.connect(self.normalized/'source.sqlite')
        body=json.loads(db.execute('SELECT body FROM raw WHERE ordinal=1').fetchone()[0]);body['code']='1111'
        db.execute('UPDATE raw SET body=? WHERE ordinal=1',(canonical(body).decode(),));db.commit();db.close()
        self.repin_db_in_fixture_metadata()
        with self.bind() as checked:
            self.assertEqual(checked.semantic_validator(self.records[0]),['off-native-source-identity-invalid'])

    def test_db_duplicate_identity_and_out_of_extent_ordinal_reject(self):
        db=sqlite3.connect(self.normalized/'source.sqlite');db.execute('DROP INDEX identity_idx')
        db.execute('UPDATE raw SET identity=? WHERE ordinal=2',('00012345',));db.commit();db.close()
        self.repin_db_in_fixture_metadata()
        with self.bind() as checked:
            self.assertEqual(checked.semantic_validator(self.records[0]),['off-native-source-row-required'])
        db=sqlite3.connect(self.normalized/'source.sqlite');db.execute('DELETE FROM raw WHERE ordinal=2')
        db.execute('UPDATE raw SET ordinal=99 WHERE ordinal=1');db.commit();db.close()
        self.repin_db_in_fixture_metadata()
        with self.bind() as checked:
            self.assertEqual(checked.semantic_validator(self.records[0]),['off-native-source-row-invalid'])

    def test_db_missing_schema_sidecars_symlinks_and_fifo_reject(self):
        path=self.normalized/'source.sqlite';raw=path.read_bytes()
        for suffix in ('-wal','-shm','-journal'):
            sidecar=path.with_name(path.name+suffix);sidecar.write_bytes(b'held')
            with self.assertRaises(RefreshError):
                with self.bind():pass
            sidecar.unlink()
        saved=self.normalized/'saved.sqlite';path.rename(saved);path.symlink_to(saved)
        with self.assertRaises((RefreshError,ValueError)):
            with self.bind():pass
        path.unlink();os.mkfifo(path)
        with self.assertRaises(RefreshError):
            with self.bind():pass
        path.unlink();saved.rename(path)
        db=sqlite3.connect(path);db.execute('DROP TABLE raw');db.commit();db.close()
        self.repin_db_in_fixture_metadata()
        with self.assertRaisesRegex(RefreshError,'off-source-authority-db-schema'):
            with self.bind():pass

    def test_same_bytes_replacement_and_mid_lifetime_changes_reject(self):
        for name in ('source.sqlite','manifest.json'):
            path=self.normalized/name;before=path.read_bytes()
            with self.assertRaisesRegex(RefreshError,'off-source-authority-changed'):
                with self.bind():
                    replacement=path.with_suffix('.replacement');replacement.write_bytes(before);replacement.replace(path)
            # Rebind to the unchanged byte pins in the next lifetime; identity is per-open.
            with self.bind() as checked:self.assertEqual(checked.semantic_validator(self.records[0]),[])

    def test_changed_db_manifest_or_sidecar_during_callback_lifetime_reject(self):
        for name in ('source.sqlite','manifest.json','source.sqlite-wal'):
            path=self.normalized/name;before=path.read_bytes() if path.exists() else None
            with self.assertRaisesRegex(RefreshError,'off-source-authority-changed'):
                with self.bind() as checked:
                    self.assertEqual(checked.semantic_validator(self.records[0]),[])
                    path.write_bytes((before or b'')+b'changed')
            if before is None:path.unlink()
            else:path.write_bytes(before)

    def test_original_input_tamper_during_qualification_is_held_by_existing_boundary(self):
        path=self.inputs/self.source.path
        with self.bind() as checked:
            original=checked.semantic_validator;changed=False
            def semantic(row):
                nonlocal changed
                if not changed:path.write_bytes(path.read_bytes()+b'changed');changed=True
                return original(row)
            result=qualify(replace(checked,semantic_validator=semantic),self.bundle,
                self.normalized/'candidate.jsonl',self.manifest,input_root=self.inputs)
            self.assertFalse(result['qualified'])
            self.assertIn('input-custody-changed-during-qualification',result['errors'])

    def test_connection_read_only_and_exception_closes_escaped_callback(self):
        real=sqlite3.connect;connections=[]
        def connect(*args,**kwargs):
            self.assertIn('?mode=ro&immutable=1',args[0]);self.assertTrue(kwargs['uri'])
            db=real(*args,**kwargs);connections.append(db);return db
        with patch.object(binding.sqlite3,'connect',side_effect=connect):
            with self.assertRaisesRegex(RuntimeError,'fixture abort'):
                with self.bind() as checked:
                    self.assertEqual(checked.semantic_validator(self.records[0]),[])
                    with self.assertRaises(sqlite3.OperationalError):connections[0].execute('DELETE FROM raw')
                    raise RuntimeError('fixture abort')
        self.assertEqual(checked.semantic_validator(self.records[0]),['off-native-source-authority-expired'])
        with self.assertRaises(sqlite3.ProgrammingError):connections[0].execute('SELECT 1')

    def test_non_off_policy_is_not_reinterpreted(self):
        legacy=replace(self.contract,semantic_validator=lambda row:[])
        with self.bind(legacy) as checked:self.assertIs(checked,legacy)

    def test_bare_or_altered_derivation_authority_is_refused(self):
        bare=replace(self.contract,semantic_validator=policy.UnboundOffSemantics(self.context))
        with self.assertRaisesRegex(RefreshError,'off-source-derivation-required'):
            with self.bind(bare):pass
        altered=replace(self.contract.semantic_validator,derivation=replace(
            self.contract.semantic_validator.derivation,independent_review_sha256='f'*64))
        with self.assertRaisesRegex(RefreshError,'off-source-derivation-policy-pin'):
            with self.bind(replace(self.contract,semantic_validator=altered)):pass

    def test_rehashed_forged_cache_cannot_authenticate_original_derivation(self):
        # Original gzip and trusted application contract remain unchanged.
        db=sqlite3.connect(self.normalized/'source.sqlite')
        changed=deepcopy(self.rows);changed[0]['product_name']='Forged cache value'
        db.execute('UPDATE raw SET body=? WHERE ordinal=1',(canonical(changed[0]).decode(),))
        db.commit();db.close()
        packets=[]
        for ordinal,source in enumerate(changed,1):
            for row in adapters._off(self.context,source):
                row['provenance'].update(sourceRow=ordinal,sourceRevision=source.get('rev'),
                    sourceLastModified=source.get('last_modified_t'),sourceLastUpdated=source.get('last_updated_t'),
                    inputSha256={'products':self.source.sha256})
                packets.append(adapters.canonical([row]))
        candidate=b''.join(packets);(self.normalized/'candidate.jsonl').write_bytes(candidate)
        original=json.loads((self.normalized/'manifest.json').read_bytes())
        original.update(candidateBytes=len(candidate),candidateSha256=hashlib.sha256(candidate).hexdigest())
        original['outputHashes']={name:hashlib.sha256((self.normalized/name).read_bytes()).hexdigest()
                                  for name in ('source.sqlite','candidate.jsonl')}
        (self.normalized/'manifest.json').write_bytes(adapters.canonical(original))
        self.manifest=self.qualified_manifest(original)
        with self.assertRaises(RefreshError):
            qualify_product_candidate(self.contract,self.bundle,{'products':self.source.path},self.normalized,
                license=policy.LICENSE,attribution=policy.ATTRIBUTION,limits=self.limits,input_root=self.inputs)

    def test_corrupt_but_rehashed_fixture_db_is_a_fixed_storage_failure(self):
        (self.normalized/'source.sqlite').write_bytes(b'not a SQLite database')
        self.repin_db_in_fixture_metadata()
        with self.assertRaisesRegex(RefreshError,'off-source-authority-db$'):
            with self.bind():pass

    def test_oversized_db_text_is_limited_inside_read_only_connection(self):
        db=sqlite3.connect(self.normalized/'source.sqlite')
        db.execute('UPDATE raw SET body=? WHERE ordinal=1',('x'*(self.limits.max_line_bytes+2048),))
        db.commit();db.close();self.repin_db_in_fixture_metadata()
        with self.bind() as checked:
            self.assertEqual(checked.semantic_validator(self.records[0]),['off-native-source-row-invalid'])


if __name__=='__main__':unittest.main()
