"""Reference candidates use native, independently pinned fixture contracts only."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh import acceptance as q
from offmenu.refresh import reference_adapters as a


class ReferenceAcceptanceTests(unittest.TestCase):
    def test_native_fixture_acceptance_and_operation_hold(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'; bundle.mkdir()
            payload = json.dumps([{'pageid': 1, 'title': 'Cookbook:Authored fixture',
                'revisions': [{'revid': 2, 'slots': {'main': {'content': '== Ingredients ==\n* example'}}}]}]).encode()
            source = 'wikibooks'; release = a.CONTRACTS[source][0]
            acquired_at = '2026-10-13T12:00:00Z'
            assets = []
            for name, content in [('revisions-0.json', payload),
                                  ('rights.json', b'{"scope":"authored fixture","operations":["retain","parse","transform"]}'),
                                  ('scope.json', b'{"expectedPageIds":[1],"expectedCount":1}')]:
                (bundle / name).write_bytes(content)
                assets.append(q.Asset(name, len(content), hashlib.sha256(content).hexdigest()))
            rows = a.normalize_reference(source, release, payload, acquired_at=acquired_at)
            candidate = root / 'candidate.jsonl'; candidate.write_bytes(a.candidate_bytes(rows))
            schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/reference-candidate.schema.json').read_text())
            schemas = {'recipe-discovery-reference': schema}
            contract = q.SourceContract(source_id=source, release_id=release,
                scope_id='authored-reference-fixture-only', acquired_at=acquired_at,
                inputs=tuple(assets), expected_records=1,
                expected_ids_sha256=q.ids_digest([row['id'] for row in rows]),
                schemas=schemas, schemas_sha256=q.fingerprint(schemas),
                semantic_validator=a.reference_semantics,
                policy_sha256=hashlib.sha256(b'authored-reference-policy-v1').hexdigest(),
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
            manifest = a.candidate_manifest(source, release, rows, acquired_at=acquired_at,
                input_files=[{'path': x.path, 'bytes': x.bytes, 'sha256': x.sha256} for x in assets],
                rights_evidence_sha256=assets[1].sha256, scope_evidence_sha256=assets[2].sha256)
            receipt = q.accept(contract, bundle, candidate, manifest)
            self.assertTrue(receipt['accepted'], receipt['errors'])
            self.assertFalse(receipt['productionAccepted'])
            self.assertFalse(receipt['countryCoverageComplete'])
            held = q.accept(replace(contract, permitted_operations=frozenset(('retain',))), bundle, candidate, manifest)
            self.assertFalse(held['accepted'])
            self.assertIn('operation-rights-missing', held['errors'])
            promoted = q.accept(replace(contract, output_visibility='public'), bundle, candidate, manifest)
            self.assertFalse(promoted['accepted'])
            self.assertIn('publication-operation-rights-required', promoted['errors'])


if __name__ == '__main__':
    unittest.main()
