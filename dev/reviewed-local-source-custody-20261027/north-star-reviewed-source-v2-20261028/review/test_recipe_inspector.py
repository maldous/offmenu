"""Finite independent tests for the corrected recipe diagnostic joins."""
import copy
import contextlib
import gzip
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'candidate/scripts'))
import inspect_recipe_relations as subject

TYPE = 'urn:offmenu:type:'; REL = 'urn:offmenu:relation:'; PROP = 'urn:offmenu:property:'
SCOPE = {'visibility': 'public', 'reuseScope': 'Synthetic only'}


def fixture(value=0):
    common = {'scope': copy.deepcopy(SCOPE), 'citationIds': ['urn:test:citation']}
    resources = [dict(common, id='urn:test:' + identifier, type=TYPE + typ, identityStatus='source-scoped', names=[])
                 for identifier, typ in [('recipe', 'RecipeVariant'), ('mention', 'IngredientMention'), ('step', 'RecipeStep')]]
    edges = [dict(common, id='urn:test:edge:' + pred, subjectId='urn:test:recipe', predicateId=REL + pred,
                  objectId='urn:test:' + target, status='source-asserted', sourcePath='synthetic.' + pred)
             for pred, target in [('usesIngredient', 'mention'), ('hasStep', 'step')]]
    amount = {'kind': 'quantity', 'value': value, 'unitId': 'urn:offmenu:unit:g', 'dimension': 'mass',
              'sourceValue': value, 'sourceUnit': 'g', 'qualifiers': []}
    facts = [dict(common, id='urn:test:amount', subjectId='urn:test:mention', propertyId=PROP + 'requiredQuantity',
                  value=amount, status='candidate', sourcePath='synthetic.quantity')]
    citation = dict(common, id='urn:test:citation', sourceId='synthetic', originalRecordId='test-only',
                    originalUrl='https://example.test/fixture', license='CC0', attribution='Synthetic')
    citation.pop('citationIds')
    return {'schemaVersion': 'offmenu-common/1', 'resources': resources, 'assertions': facts,
            'relations': edges, 'citations': [citation], 'translations': []}


class RecipeInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.package = self.root / 'package'; self.package.mkdir()
        self.schema = self.root / 'schema'; self.schema.mkdir()
        canonical = (ROOT / 'selected/package-contract/common-data.schema.json').read_bytes()
        assert hashlib.sha256(canonical).hexdigest() == '89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c'
        (self.schema / 'schema.json').write_bytes(canonical)

    def tearDown(self): self.tmp.cleanup()

    def inspect(self, packet=None):
        packet = fixture() if packet is None else packet
        raw = gzip.compress((json.dumps(packet) + '\n').encode()); (self.package / 'selected.jsonl.gz').write_bytes(raw)
        entry = {'key': 'selected.jsonl.gz', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'packets': 1}
        # This invalid native-format payload is intentionally NOT a packet asset
        # and must not be interpreted as a common graph.
        native = b'not a graph'; (self.package / 'native.jsonl.gz').write_bytes(native)
        manifest = {'releaseId': 'synthetic', 'files': [entry, {'key': 'native.jsonl.gz', 'bytes': len(native), 'sha256': hashlib.sha256(native).hexdigest()}]}
        raw = json.dumps(manifest).encode(); (self.package / 'manifest.json').write_bytes(raw)
        with contextlib.redirect_stdout(io.StringIO()):
            return subject.inspect(self.package, hashlib.sha256(raw).hexdigest(), self.schema, self.root / 'out')

    def test_correct_recipe_joins_and_selected_asset_filter(self):
        report = self.inspect(); q = report['queries']
        self.assertEqual(report['packetsSchemaValidated'], 1)
        self.assertEqual(q['recipeIngredientMentionsResolved']['count'], 1)
        self.assertEqual(q['ingredientQuantityJoins']['count'], 1)
        self.assertEqual(q['sourceRecipeStepJoins']['count'], 1)
        self.assertEqual(q['stepIngredientJoins']['count'], 0)

    def test_nonrecipe_subject_not_counted_as_recipe_join(self):
        p = fixture(); p['resources'][0]['type'] = TYPE + 'FoodProduct'; q = self.inspect(p)['queries']
        for key in ('recipeIngredientMentionsResolved', 'ingredientQuantityJoins', 'sourceRecipeStepJoins'):
            self.assertEqual(q[key]['count'], 0)

    def test_step_use_not_counted_as_recipe_quantity(self):
        p = fixture(); p['relations'][0]['subjectId'] = 'urn:test:step'; q = self.inspect(p)['queries']
        self.assertEqual(q['ingredientQuantityJoins']['count'], 0)
        self.assertEqual(q['stepIngredientJoins']['count'], 1)

    def test_superseded_edges_not_resolved(self):
        p = fixture()
        for edge in p['relations']: edge['status'] = 'superseded'
        q = self.inspect(p)['queries']
        for key in ('recipeIngredientMentionsResolved', 'ingredientQuantityJoins', 'sourceRecipeStepJoins'):
            self.assertEqual(q[key]['count'], 0)

    def test_private_citation_with_public_row_rejected(self):
        p = fixture(); p['citations'][0]['scope'] = {'visibility': 'private', 'ownerId': 'someone-else'}
        with self.assertRaisesRegex(ValueError, 'citation scope differs'): self.inspect(p)

    def test_public_quantity_scope_difference_not_joined(self):
        p = fixture(); c = copy.deepcopy(p['citations'][0]); c['id'] = 'urn:test:other-citation'
        c['scope'] = {'visibility': 'public', 'reuseScope': 'Different restriction'}; p['citations'].append(c)
        p['assertions'][0]['scope'] = copy.deepcopy(c['scope']); p['assertions'][0]['citationIds'] = [c['id']]
        self.assertEqual(self.inspect(p)['queries']['ingredientQuantityJoins']['count'], 0)

    def test_unknown_quantity_not_zero(self):
        q = self.inspect(fixture(None))['queries']
        self.assertEqual(q['ingredientUnknownQuantities']['count'], 1)
        self.assertEqual(q['ingredientZeroQuantities']['count'], 0)

    def test_zero_quantity_not_unknown(self):
        q = self.inspect(fixture(0))['queries']
        self.assertEqual(q['ingredientUnknownQuantities']['count'], 0)
        self.assertEqual(q['ingredientZeroQuantities']['count'], 1)


if __name__ == '__main__': unittest.main()
