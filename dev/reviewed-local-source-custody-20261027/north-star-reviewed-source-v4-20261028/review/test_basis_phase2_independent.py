import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'review'),str(ROOT/'candidate/scripts'),str(ROOT/'candidate/tests')]
import measure_basis_phase2 as M
from test_basis_restoration import inputs,producer
from test_basis_runner import prepare


class IndependentPhaseTwoEstimateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.native,self.bulk,self.output,self.kw=prepare(self.tmp.name)
        M.R.run('index',self.native,self.bulk,self.output,**self.kw)
        self.manifest=self.output/'native-index-manifest.json'
        self.pin=M.R.sha_file(self.manifest)
    def tearDown(self):self.tmp.cleanup()
    def test_loaded_implementation_must_match_pinned_native_producer(self):
        meta=json.loads(self.manifest.read_bytes());meta['selection']['codePins']['north_star_basis_restoration.py']='0'*64
        self.manifest.write_bytes(M.R.encoded(meta))
        with self.assertRaisesRegex(ValueError,'LoadedDerivationCodePinMismatch'):
            M.measure(self.bulk,self.output,M.R.sha_file(self.manifest))
    def test_selected_asset_change_refused_after_matching_manifest(self):
        (self.bulk/'part.jsonl.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'InputAssetDigestMismatch'):
            M.measure(self.bulk,self.output,self.pin)
    def test_elapsed_final_deadline_cannot_emit_success(self):
        with patch.object(M.time,'monotonic',side_effect=[0,0,0,601]):
            with self.assertRaisesRegex(TimeoutError,'MeasurementDeadline'):
                M.measure(self.bulk,self.output,self.pin)
    def test_unknown_state_and_zero_are_measured_without_rewriting_inputs(self):
        r,e,p=inputs(value=None,state=None)
        r2,e2,p2=inputs(value=0,state='as-sold');r2['id']='synthetic:profile:2';r2['provenance']['recordId']='second-record';p2=producer.packet(r2,'off',e2)
        with tempfile.TemporaryDirectory() as temp:
            n,b,o,kw=prepare(temp,records=[r,r2],packets=[p,p2]);M.R.run('index',n,b,o,**kw)
            paths=[o/'native-index.sqlite',b/'part.jsonl.gz'];before=[M.R.sha_file(x) for x in paths]
            report=M.measure(b,o,M.R.sha_file(o/'native-index-manifest.json'))
            self.assertEqual(report['sampleCounts']['matchedProfiles'],2)
            self.assertEqual(report['sampleCounts']['basisTargets'],4)
            self.assertEqual(report['fullNativeProfiles'],2)
            self.assertEqual(before,[M.R.sha_file(x) for x in paths])
            self.assertEqual(report['measurementHelperSha256'],M.R.sha_file(Path(M.__file__)))
            self.assertEqual(report['loadedDerivationCodePins'],report['sourceSelection']['codePins'])
            self.assertTrue(report['measurementOnly']);self.assertFalse(report['rawValuesExported'])


if __name__=='__main__':unittest.main()
