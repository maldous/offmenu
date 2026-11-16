import hashlib,json,sys,unittest,fcntl
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'review'),str(ROOT/'candidate/scripts'),str(ROOT/'candidate/tests')]
import measure_basis_phase2 as M
import test_source_scoped_consumer as F

class MeasurementTests(unittest.TestCase):
    def setUp(self):
        self.f=F.SourceConsumerTests('test_actual_value_context_and_restored_basis');self.f.setUp()
        self.pin=hashlib.sha256((self.f.basis/'native-index-manifest.json').read_bytes()).hexdigest()
    def tearDown(self):self.f.tearDown()
    def measure(self,pin=None):return M.measure(self.f.source,self.f.basis,pin or self.pin)
    def test_counts_no_values_and_original_index_unchanged(self):
        path=self.f.basis/'native-index.sqlite';before=hashlib.sha256(path.read_bytes()).hexdigest();r=self.measure()
        self.assertEqual(r['sampleCounts'],{'packets':2,'resources':2,'matchedProfiles':1,'sidecars':1,'basisTargets':2})
        self.assertEqual(before,hashlib.sha256(path.read_bytes()).hexdigest())
        self.assertGreater(r['suggestedAbsoluteTotalBudgetBytes'],r['retainedNativeIndexBytes']+r['estimatedAdditionalNamedTotalBytes'])
        text=json.dumps(r)
        for value in ('001234','Synthetic product','as-sold','source-product'):self.assertNotIn(value,text)
    def test_changed_index_manifest_refused(self):
        with self.assertRaisesRegex(ValueError,'NativeIndexManifestPinMismatch'):self.measure('0'*64)
    def test_strict_deadline_bounds(self):
        for value in (0,1201,True,'600'):
            with self.assertRaisesRegex(ValueError,'StrictMeasurementDeadlineRequired'):M.measure(self.f.source,self.f.basis,self.pin,seconds=value)
    def test_active_writer_refused(self):
        with (self.f.basis/'.writer.lock').open('rb') as lock:
            fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):self.measure()

if __name__=='__main__':unittest.main()
