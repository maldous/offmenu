import copy
import hashlib
import json
import math
import unittest
from dataclasses import replace
from offmenu.refresh.full_field_reader import FieldReader, FieldPageError, Limits, canonical, error_envelope
import runpy
from pathlib import Path
_fixture = runpy.run_path(str(Path(__file__).parent / 'fixtures/full-field-paging/generated_fixture.py'))
binding, reader, KEY = (_fixture[name] for name in ('binding', 'reader', 'KEY'))
from offmenu.refresh.source_field_presenter_adapter import selected_request, read_more, selected_node_request, read_page


class ReaderTests(unittest.TestCase):
    def error(self, code, call):
        with self.assertRaises(FieldPageError) as caught:
            call()
        self.assertEqual(caught.exception.code, 'field-page-' + code)

    def pages(self, subject, method='read'):
        cursor, output, seen = None, [], set()
        for _ in range(2000):
            page = getattr(subject, method)(cursor)
            self.assertLessEqual(len(canonical(page)), subject._limits.page_bytes)
            output.append(page)
            cursor = page['nextCursor']
            if cursor is None:
                return output
            self.assertNotIn(cursor, seen)
            seen.add(cursor)
        self.fail('Generated traversal failed to terminate')

    def reconstruct(self, subject, cursor=None):
        page = subject.read(cursor)
        content = page['content']
        if page['state'] == 'null':
            self.assertIsNone(content)
            return None
        if content['kind'] == 'text':
            chunks = [content['text']]
            while page['nextCursor']:
                end = page['content']['end']
                page = subject.read(page['nextCursor'])
                self.assertEqual(page['content']['start'], end)
                chunks.append(page['content']['text'])
            return ''.join(chunks)
        if content['kind'] in ('object', 'array'):
            children = []
            while True:
                children.extend(page['content']['children'])
                if not page['nextCursor']:
                    break
                page = subject.read(page['nextCursor'])
            keys = [child['key'] for child in children]
            self.assertEqual(len(keys), len(set(keys)))
            values = [self.reconstruct(subject, child['cursor']) for child in children]
            return dict(zip(keys, values)) if content['kind'] == 'object' else values
        if content['kind'] == 'number':
            return json.loads(content['jsonNumber'])
        return content['value']

    def test_long_unicode_text_reconstructs_exactly_without_normalizing(self):
        original = '😀e\u0301\r\n𐐷漢字\x00/URL:https://invalid.test/' * 1200
        r = reader(original)
        pages = self.pages(r)
        self.assertGreater(len(pages), 5)
        self.assertEqual(''.join(p['content']['text'] for p in pages), original)
        self.assertEqual(hashlib.sha256(original.encode()).digest(),
                         hashlib.sha256(self.reconstruct(r).encode()).digest())
        for before, after in zip(pages, pages[1:]):
            self.assertEqual(before['content']['end'], after['content']['start'])
        self.assertTrue(pages[-1]['nodeExhausted'])
        self.assertFalse(pages[-1]['valueCompleteInThisPage'])

    def test_complete_arrays_objects_unknown_keys_and_types(self):
        original = {'unknown/extension~': [None, False, 0, '', [], {}, 9007199254740993, -0.0],
                    '__proto__': {'constructor': 'inert'}, 'é': 'é', 'e\u0301': 'e\u0301',
                    'many': [{str(n): n} for n in range(75)]}
        self.assertEqual(self.reconstruct(reader(original)), original)

    def test_stable_object_order_independent_of_insertion_order(self):
        a, b = {'𐐷': 1, '😀': 2, 'é': 3, 'e\u0301': 4, 'Z': 5}, {}
        for key in reversed(list(a)):
            b[key] = a[key]
        x, y = reader(a).read(), reader(b).read()
        self.assertEqual(x, y)
        self.assertEqual([child['key'] for child in x['content']['children']], sorted(a))

    def test_container_pages_obey_item_and_byte_bounds(self):
        r = reader({str(n).zfill(4): n for n in range(120)}, limits=Limits(page_bytes=4096, max_items=3))
        pages = self.pages(r)
        self.assertEqual(len(pages), 40)
        self.assertEqual([c['key'] for p in pages for c in p['content']['children']],
                         [str(n).zfill(4) for n in range(120)])
        self.assertFalse(pages[-1]['valueCompleteInThisPage'])

    def test_walk_visits_all_descendants_and_parent_pages(self):
        data = {'a': [None, False, {'nested': '😀' * 3000}], 'b': {}, 'c': [], 'd': 'last'}
        pages = self.pages(reader(data, limits=Limits(page_bytes=4096, max_items=1)), 'walk')
        paths = {tuple(p['path']) for p in pages}
        self.assertEqual(paths, {(), ('a',), ('a', 0), ('a', 1), ('a', 2),
                               ('a', 2, 'nested'), ('b',), ('c',), ('d',)})
        self.assertEqual(''.join(p['content']['text'] for p in pages if p['path'] == ['a', 2, 'nested']), '😀' * 3000)
        self.assertTrue(pages[-1]['traversalExhausted'])
        self.assertTrue(all(not p['traversalExhausted'] for p in pages[:-1]))

    def test_every_cursor_binds_source_revision_field_path_metadata_and_generation(self):
        r = reader('x' * 20000)
        cursor = r.read()['nextCursor']
        for change in ['sourceId', 'assertion', 'revision', 'path', 'binding', 'attribution', 'generation', 'selectionRevision']:
            with self.subTest(change=change):
                context = binding()
                if change == 'sourceId': context['sourceObservationReference']['sourceId'] = 'another-source'
                if change == 'assertion': context['sourceObservationReference']['observationKey']['assertion_id'] = 2
                if change == 'revision': context['revisionSha256'] = '5' * 64
                if change == 'path': context['fieldPath'] = '/other'
                if change == 'binding': context['sourceBinding']['unknownExtension'] = {'keep': False}
                if change == 'attribution': context['attribution']['notice'] = 'another notice'
                if change == 'generation': context['generation'] += 1
                if change == 'selectionRevision':
                    context['selectionRevision'] = '6' * 64
                    context['sourceObservationReference']['detailSelectionSha256'] = '6' * 64
                self.error('cursor-binding-mismatch', lambda: reader('x' * 20000, context=context).read(cursor))

    def test_cursor_binds_content_limits_and_field_metadata(self):
        token = reader('x' * 20000).read()['nextCursor']
        self.error('cursor-binding-mismatch', lambda: reader('y' * 20000).read(token))
        self.error('cursor-binding-mismatch', lambda: reader('x' * 20000, limits=Limits(page_bytes=5000)).read(token))
        r = FieldReader(binding=binding(), field={'state': 'present', 'value': 'x' * 20000},
                        delivery='permitted', cursor_key=KEY, limits=Limits(page_bytes=4096))
        self.error('cursor-binding-mismatch', lambda: r.read(token))

    def test_cursor_tampering_wrong_key_malformed_and_wrong_mode(self):
        r = reader('x' * 20000)
        token = r.read()['nextCursor']
        for invalid in [token[:-2] + 'AA', 'x.y', token + '=', 'x' * 4097, 12, {'cursor': token}]:
            with self.subTest(invalid=str(invalid)[:10]):
                self.error('cursor-invalid', lambda: r.read(invalid))
        other = FieldReader(binding=binding(), field={'state': 'present', 'value': 'x' * 20000},
                            delivery='permitted', cursor_key=b'other-synthetic-fixture-key-only-00000')
        self.error('cursor-invalid', lambda: other.read(token))
        self.error('cursor-binding-mismatch', lambda: r.walk(token))
        self.error('cursor-binding-mismatch', lambda: r.read(r.walk()['nextCursor']))

    def test_missing_null_unknown_not_loaded_and_rights_held_are_distinct(self):
        for state in ['null', 'missing', 'unknown', 'not-loaded', 'rights-held']:
            with self.subTest(state=state):
                p = reader(None, state=state).read()
                self.assertEqual(p['state'], state)
                self.assertIsNone(p['content'])
                self.assertIsNone(p['nextCursor'])
                self.assertEqual(p['valueCompleteInThisPage'], state == 'null')
        self.assertEqual(reader(None, state='unknown', delivery='rights-held').read()['state'], 'rights-held')

    def test_held_values_cannot_enter_snapshot(self):
        class Poison:
            def __iter__(self): raise AssertionError('held body inspected')
        self.error('rights-held-value-supplied', lambda: reader(Poison(), delivery='rights-held'))
        self.error('rights-held-value-supplied', lambda: reader({'hidden': 'payload'}, state='rights-held'))
        self.error('rights-held-metadata', lambda: FieldReader(binding=binding(),
            field={'state': 'rights-held', 'value': None, 'unknownBodyKey': 'withheld'},
            delivery='rights-held', cursor_key=KEY))

    def test_field_state_value_mismatches_fail_typed(self):
        for value, state in [(None, 'present'), ('not-null', 'null'), ('body', 'missing'), ('body', 'unknown')]:
            self.error('state-value-mismatch', lambda: reader(value, state=state))
        self.error('field-state', lambda: reader('body', state={}))

    def test_input_and_output_mutation_cannot_change_snapshot(self):
        value, context = {'a': ['original']}, binding()
        r = reader(value, context=context)
        before = r.read()
        value['a'][0] = 'changed'; context['sourceBinding']['unknownExtension']['keep'] = False
        after = r.read()
        self.assertEqual(before, after)
        before['binding']['attribution']['notice'] = 'changed output'
        before['content']['children'].clear()
        self.assertEqual(r.read(), after)

    def test_unknown_metadata_source_pointer_and_attribution_preserved(self):
        p = reader('body').read()
        self.assertEqual(p['binding'], binding())
        self.assertEqual(p['field']['unknownMetadata'], ['kept', 'kept'])
        self.assertEqual(p['field']['fieldPointer'], '/0/data/unknown~1extension')
        self.assertEqual(p['field']['sourceFieldState'], 'unknown')

    def test_snapshot_byte_guard_includes_unicode_escaping_and_all_metadata(self):
        for value in ['x' * 262144, '😀' * 70000, '\x00' * 45000, ['x' * 10000] * 40]:
            self.error('snapshot-bound', lambda: reader(value))

    def test_depth_work_key_metadata_and_atomic_page_bounds(self):
        value = 'leaf'
        for _ in range(9): value = [value]
        self.error('depth-bound', lambda: reader(value))
        self.error('work-bound', lambda: reader('body', limits=Limits(max_nodes=5)))
        self.error('atomic-key-bound', lambda: reader({'k' * 1025: 'body'}))
        context = binding(); context['attribution'] = 'n' * 9000
        self.error('metadata-bound', lambda: reader('body', context=context))
        self.error('page-bound', lambda: reader(10 ** 3000).read())
        self.assertEqual(reader(10 ** 3000, limits=Limits(page_bytes=8192)).read()['content']['jsonNumber'], str(10 ** 3000))

    def test_no_empty_page_or_silent_truncation_when_envelope_cannot_fit(self):
        for value in ['text', {'key': 'text'}, [None], True]:
            self.error('page-bound', lambda: reader(value, limits=Limits(page_bytes=256)).read())

    def test_terminal_text_without_cursor_can_fit_when_nonterminal_would_not(self):
        original = 'abc😀'
        r = reader(original, limits=Limits(page_bytes=4096))
        size = len(canonical(r.read()))
        exact = reader(original, limits=Limits(page_bytes=size))
        self.assertEqual(exact.read()['content']['text'], original)
        self.assertIsNone(exact.read()['nextCursor'])

    def test_guard_limits_cannot_be_raised(self):
        for name, value in [('page_bytes', 262145), ('snapshot_bytes', 262145), ('metadata_bytes', 8193),
                            ('max_depth', 9), ('max_nodes', 100001), ('max_items', 1001),
                            ('max_seconds', 6), ('cursor_bytes', 4097), ('page_bytes', True)]:
            self.error('limits', lambda: reader('body', limits=replace(Limits(), **{name: value})))

    def test_only_plain_finite_json_and_well_formed_unicode(self):
        class CustomList(list): pass
        for value in [float('nan'), float('inf'), object(), CustomList([1]), '\ud800']:
            self.error('json-value', lambda: reader(value))
        self.error('json-key', lambda: reader({1: 'not a JSON object key'}))

    def test_typed_binding_rejections_not_accidental_python_exceptions(self):
        for change in ['sha', 'generation', 'unsafe-id', 'pointer', 'selection']:
            context = binding()
            if change == 'sha': context['revisionSha256'] = 12
            if change == 'generation': context['generation'] = True
            if change == 'unsafe-id': context['sourceObservationReference']['observationKey']['assertion_id'] = 9007199254740992
            if change == 'pointer': context['fieldPath'] = '/bad~escape'
            if change == 'selection': context['selectionRevision'] = '5' * 64
            self.error('binding', lambda: reader('body', context=context))

    def test_explicit_time_guard_without_sleep(self):
        class Clock:
            active, tick = False, 0
            def __call__(self):
                if self.active: self.tick += 1
                return self.tick
        clock = Clock()
        r = FieldReader(binding=binding(), field={'state': 'present', 'value': 'x' * 20000},
                        delivery='permitted', cursor_key=KEY, clock=clock)
        clock.active = True
        self.error('time-bound', lambda: r.read())

    def test_safe_error_envelope_does_not_claim_absence_or_completion(self):
        result = error_envelope(FieldPageError('page-bound'))
        self.assertEqual(result['state'], 'unavailable')
        self.assertFalse(result['nodeExhausted'])
        self.assertFalse(result['valueCompleteInThisPage'])
        self.assertNotIn('value', result)
        self.assertEqual(error_envelope(FieldPageError('untrusted secret/path text'))['reasonCode'],
                         'field-page-internal')

    def test_presenter_long_text_packs_final_envelope_and_echoes_only_validated_selection(self):
        original = '😀漢字e\u0301\r\n' * 3000
        r, cursor, chunks = reader(original), None, []
        for _ in range(2000):
            request = selected_request(r, opaque_cursor=cursor)
            p = read_more(r, request)
            self.assertLessEqual(len(canonical(p)), 4096)
            self.assertEqual(p['selectionKey'], request['selectionKey'])
            field = next(iter(p['sourceProducts'][0]['fields'].values()))
            if chunks: self.assertEqual(field['textRange']['start'], chunks[-1][1])
            chunks.append((field['value'], field['textRange']['end']))
            cursor = p['nextCursor']
            if cursor is None: break
        else: self.fail('presenter traversal did not terminate')
        self.assertEqual(''.join(text for text, _ in chunks), original)
        self.assertEqual(p['state'], 'available')

    def test_presenter_walk_keeps_all_paths_and_exact_large_numbers(self):
        data = {'z': [False, None, 9007199254740993], 'unknown/extension~': {'deep': 'verbatim'}}
        r, cursor, paths, numbers = reader(data), None, set(), []
        for _ in range(100):
            p = read_more(r, selected_request(r, opaque_cursor=cursor))
            product = p['sourceProducts'][0]
            self.assertEqual(product['sourceBinding'], binding()['sourceBinding'])
            field = next(iter(product['fields'].values()))
            paths.add(tuple(field['deliveryPath']))
            if field['deliveryKind'] == 'number': numbers.append(field['value'])
            cursor = p['nextCursor']
            if cursor is None: break
        self.assertEqual(paths, {(), ('z',), ('z', 0), ('z', 1), ('z', 2),
                                 ('unknown/extension~',), ('unknown/extension~', 'deep')})
        self.assertEqual(numbers, ['9007199254740993'])

    def test_presenter_rejects_every_selection_component_and_unvalidated_echo(self):
        r = reader('x' * 10000)
        request = selected_request(r)
        for key in ['sourceObservationReference', 'selectionRevision', 'sourceBinding', 'sourcePath', 'generation', 'selectionKey']:
            changed = copy.deepcopy(request)
            changed[key] = 1 if key == 'generation' else 'changed'
            self.error('presenter-binding-mismatch', lambda: read_more(r, changed))
        bad = dict(request, extra='not allowed')
        self.error('presenter-request', lambda: read_more(r, bad))

    def test_presenter_rights_held_unknown_and_missing_never_display_body_or_complete_value(self):
        for state in ['rights-held', 'unknown', 'not-loaded', 'missing']:
            r = reader(None, state=state)
            p = read_more(r, selected_request(r))
            self.assertEqual(p['state'], 'partial')
            self.assertFalse(p['hasMore'])
            field = next(iter(p['sourceProducts'][0]['fields'].values()))
            self.assertEqual(field['state'], state)
            self.assertIsNone(field['value'])

    def test_actual_node_presenter_callback_preserves_page_schema_and_all_children(self):
        r = reader({'unknown': [None, False, '😀' * 2000]})
        first = read_page(r, selected_node_request(r))
        self.assertEqual(first, r.read())
        child_cursor = first['content']['children'][0]['cursor']
        child = read_page(r, selected_node_request(r, opaque_cursor=child_cursor))
        self.assertEqual(child['path'], ['unknown'])
        self.assertEqual([c['key'] for c in child['content']['children']], [0, 1, 2])
        self.assertEqual(child['scope'], 'node-page-only')
        null_page = read_page(r, selected_node_request(r,
            opaque_cursor=child['content']['children'][0]['cursor']))
        self.assertEqual(null_page['state'], 'null')
        self.assertIsNone(null_page['content'])
        self.assertTrue(null_page['valueCompleteInThisPage'])

    def test_actual_node_presenter_rejects_generation_binding_and_cursor_changes(self):
        r = reader('text')
        for name in ['generation', 'binding']:
            request = selected_node_request(r)
            if name == 'generation': request[name] += 1
            else: request[name]['revisionSha256'] = 'f' * 64
            self.error('presenter-binding-mismatch', lambda: read_page(r, request))
        request = selected_node_request(r, opaque_cursor='not-a-cursor')
        self.error('cursor-invalid', lambda: read_page(r, request))

    def test_request_caps_are_not_raised_by_presenter_adapter(self):
        r = reader('text')
        request = selected_node_request(r)
        request['binding']['untrustedExtra'] = 'x' * 9000
        self.error('snapshot-bound', lambda: read_page(r, request))


if __name__ == '__main__':
    unittest.main(verbosity=2)
