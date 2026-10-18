"""Approved progress composition preserves the source-specific media transport."""
from copy import deepcopy
import io,unittest
from unittest.mock import patch
import test_known_asset_intake as fixture
from offmenu.refresh.collection_progress import ProgressReporter

g=fixture.g;a=g.a;k=g.intake
class MediaProgressTests(unittest.TestCase):
 def setUp(self):
  self.f=fixture.IntakeTests();self.f.setUp();self.addCleanup(self.f.tearDown)
  self.selected=deepcopy(self.f.base_selection);self.selected.update(sources=self.f.sources,maximumRequests=7,maximumTransferBytes=13*k.MiB,preparation=[])
  self.selected['privateOriginalDownload']=self.f.mode;self.selected['parallelism']={**g.DEFAULT_PARALLELISM,'minimumHostStartSpacingSeconds':0}
  self.manifest=deepcopy(self.f.base_manifest);self.manifest['assets']=[{'assetId':s['mediaIntake']['assetId'],'sourceKey':s['sourceKey'],'bindings':[],'disposition':'eligible','retainedOriginal':None,'preparationContract':None} for s in self.f.sources];self.manifest['statTargets']=[]
  for cell in self.manifest['cells']:cell['assetIds']=[]
 def test_specialized_transport_factory_is_preserved_with_terminal_and_reuse(self):
  output=io.StringIO();reporter=ProgressReporter(stream=output,interval=.05).start();self.addCleanup(reporter.stop)
  with patch.object(k,'BoundedHTTPSFileTransport',return_value=self.f.transport) as factory,patch.object(a,'HTTPSFileTransport',side_effect=AssertionError('legacy transport must not replace bounded media transport')),patch.object(g,'selection_config',return_value=self.selected),patch.object(g,'manifest_config',return_value=self.manifest):
   first=g.run_global(self.manifest,self.selected,terminal=reporter);g.sanitize_report(first)
   self.assertEqual(factory.call_count,5);self.assertTrue(all(call.args==(65536,) for call in factory.call_args_list));self.assertEqual(first['networkRequests'],7)
   state=reporter.snapshot();self.assertEqual(state['download_completed'],5);self.assertEqual(state['download_active'],0);self.assertEqual(state['network_bytes'],first['networkBytesRead']);self.assertIsNone(state['coverage_verified'])
   second_reporter=ProgressReporter(stream=io.StringIO()).start();self.addCleanup(second_reporter.stop)
   second=g.run_global(self.manifest,self.selected,terminal=second_reporter);g.sanitize_report(second)
   self.assertEqual(second['networkRequests'],0);self.assertEqual(second_reporter.snapshot()['download_reused'],5);self.assertEqual(second_reporter.snapshot()['download_active'],0)
  reporter.stop('finished');self.assertNotIn('X-Goog-',output.getvalue());self.assertNotIn('storage.googleapis',output.getvalue());self.assertNotIn('fixture@example',output.getvalue())

if __name__=='__main__':unittest.main()
