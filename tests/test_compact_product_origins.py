"""Authored synthetic provenance only: no producer, source IO or qualification."""
from dataclasses import replace
import copy
import json
import unittest

from offmenu.refresh.compact_product_origins import (
    Codec, CodecError, Context, InputPin, Limits, Member, PolicyPin, Resolver,
    audit_usda_profile, digest, usda_wire_bound,
)


H = 'a'*64
P = 'b'*64


def wire(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                       separators=(',', ':'), allow_nan=False)+'\n').encode()


def context():
    return Context('synthetic', 'fixture-only', (
        InputPin('fixture.zip', H, 'csv-logical-data-row', members=(
            Member('food.csv', 'food', 100, ('/id', '/zero', '/a~1b~0c')),
            Member('nested/food_nutrient.csv', 'food_nutrient', 99999999,
                   ('/id', '/amount')),
        )),
        InputPin('fixture.jsonl', 'c'*64, 'jsonl-line-json-pointer', rows=10,
                 fields=('/a~1b~0c/0', '/zero')),
    ), (PolicyPin(P, ('absent', 'zero'), ('join', 'scale')),),
        ('', '/id', '/zero', '/null', '/flag', '/empty', '/a~1b~0c/0', '/value'),
        'd'*64, 'e'*64)


def source(field='/id', row=1, member='food.csv', table='food'):
    return {'kind':'source', 'sourceId':'synthetic', 'releaseId':'fixture-only',
            'inputPath':'fixture.zip', 'inputSha256':H,
            'coordinateSystem':'csv-logical-data-row', 'archiveMember':member,
            'table':table, 'row':row, 'sourceRecordId':member+':row:'+str(row),
            'sourceField':field}


def constant(symbol='absent'):
    return {'kind':'constant', 'policySha256':P, 'symbol':symbol}


def derived(inputs, transform='join'):
    return {'kind':'derived', 'policySha256':P, 'transform':transform,
            'inputs':inputs}


class CompactProductOriginsTests(unittest.TestCase):
    def setUp(self):
        self.ctx = context()
        self.codec = Codec(self.ctx)
        self.reader = Resolver(self.ctx, self.codec.dictionary_bytes,
                               self.codec.dictionary_sha256)

    def opened(self, entries, ordinal=0, record='record'):
        raw = self.codec.encode_chunk(record, ordinal, entries)
        return raw, self.reader.open_chunk(raw, digest(raw))

    def modified(self, raw, change):
        doc = json.loads(raw)
        change(doc)
        altered = wire(doc)
        return self.reader.open_chunk(altered, digest(altered))

    def test_roundtrip_preserves_exact_nested_order_and_repeated_inputs(self):
        first, second = source('/zero', 9), source('/a~1b~0c', 2)
        origin = derived([second, first, second, constant('zero'),
                          derived([constant(), first], 'scale')])
        raw, chunk = self.opened([('/data/value', origin)])
        self.assertEqual(chunk.resolve('/data/value'), origin)
        leaf = chunk.resolve('/data/value')
        leaf['inputs'][0]['row'] = 99
        self.assertEqual(chunk.resolve('/data/value'), origin)
        self.assertLess(len(chunk.nodes), 10)
        self.assertEqual(chunk.info[chunk.roots['/data/value']][2], len(wire(origin))-1)

    def test_jsonl_coordinates_and_optional_span_roundtrip(self):
        origin = {'kind':'source', 'sourceId':'synthetic', 'releaseId':'fixture-only',
                  'inputPath':'fixture.jsonl', 'inputSha256':'c'*64,
                  'coordinateSystem':'jsonl-line-json-pointer', 'line':3,
                  'sourceRecordId':'line:3', 'sourceField':'/a~1b~0c/0',
                  'sourceSpan':{'byteStart':0, 'byteEnd':0, 'sha256':'f'*64,
                                'coordinateSystem':'UTF8-bytes'}}
        raw, chunk = self.opened([('/data/value', origin)])
        self.assertEqual(chunk.resolve('/data/value'), origin)
        chunk.resolve('/data/value')['sourceSpan']['byteEnd'] = 500
        self.assertEqual(chunk.resolve('/data/value'), origin)
        with self.assertRaises(CodecError):
            audit_usda_profile(chunk)

    def test_data_null_zero_false_empty_and_escaped_pointer_coverage(self):
        data = {'zero':0, 'null':None, 'flag':False, 'empty':'', 'a/b~c':[0]}
        entries = [(p, constant()) for p in (
            '/data/zero', '/data/null', '/data/flag', '/data/empty', '/data/a~1b~0c/0')]
        before = copy.deepcopy(data)
        raw, chunk = self.opened(entries)
        result = self.reader.validate_record('record', data, [(raw,digest(raw))], expected_chunks=1)
        self.assertEqual(result['roots'], 5)
        self.assertFalse(result['accepted'])
        self.assertFalse(result['qualified'])
        self.assertEqual(data, before)
        self.assertEqual(list(chunk.iter_leaves()), sorted(entries))

    def test_dictionary_is_fixed_not_poisoned_by_failed_encode(self):
        original = self.codec.dictionary_bytes
        with self.assertRaises(CodecError):
            self.codec.encode_chunk('record',0,[('/data/value',constant('unknown'))])
        raw, _ = self.opened([('/data/value', source())])
        self.assertEqual(original, self.codec.dictionary_bytes)
        self.assertEqual(raw, self.codec.encode_chunk('record',0,[('/data/value',source())]))

    def test_dictionary_rejects_wrong_pin_context_and_added_authority(self):
        for ctx, raw, pin in (
            (self.ctx,self.codec.dictionary_bytes,'0'*64),
            (replace(self.ctx,release_id='other'),self.codec.dictionary_bytes,self.codec.dictionary_sha256),
            (self.ctx,self.codec.dictionary_bytes+b' ',digest(self.codec.dictionary_bytes+b' ')),
        ):
            with self.subTest(raw=raw[:20]), self.assertRaises(CodecError):
                Resolver(ctx,raw,pin)

    def test_invalid_trusted_registries_fail_closed(self):
        bad = [replace(self.ctx, inputs=()), replace(self.ctx, policies=[]),
               replace(self.ctx, suffixes=([],)), replace(self.ctx, inputs=({},)),
               replace(self.ctx, suffixes=('/bad~2',)),
               replace(self.ctx, rights_sha256='unknown'),
               replace(self.ctx, policies=self.ctx.policies*2)]
        inp = self.ctx.inputs[0]
        bad += [replace(self.ctx, inputs=(replace(inp,path='../fixture.zip'),)),
                replace(self.ctx, inputs=(replace(inp,coordinate_system='guessed'),)),
                replace(self.ctx, inputs=(replace(inp,members=(replace(inp.members[0],rows=True),)),))]
        for ctx in bad:
            with self.subTest(ctx=repr(ctx)[:100]), self.assertRaises(CodecError):
                Codec(ctx)

    def test_limits_can_only_be_lowered_and_are_enforced(self):
        for limits in (replace(Limits(),depth=9), replace(Limits(),nodes=0),
                       replace(Limits(),nodes=True), {}):
            with self.subTest(limits=limits), self.assertRaises(CodecError):
                Codec(self.ctx,limits=limits)
        with self.assertRaises(CodecError):
            Codec(self.ctx,limits=replace(Limits(),dictionary_bytes=1))
        low = Codec(self.ctx,limits=replace(Limits(),leaf_bytes=10))
        with self.assertRaises(CodecError):
            low.encode_chunk('record',0,[('/data/value',source())])

    def test_source_unknowns_pins_coordinates_and_record_ids_rejected(self):
        mutations = [{'sourceId':'other'}, {'releaseId':'other'}, {'inputSha256':'0'*64},
                     {'inputPath':'other.zip'}, {'archiveMember':'missing.csv'},
                     {'table':'other'}, {'row':0}, {'row':101}, {'row':True},
                     {'sourceField':'/not-registered'}, {'sourceRecordId':'food.csv:row:9'},
                     {'coordinateSystem':'physical-line'}, {'byteSpan':{}},
                     {'sourceSpan':{}}, {'sourceSpan':{'byteStart':2,'byteEnd':1,
                        'sha256':H,'coordinateSystem':'UTF8-bytes'}}]
        for change in mutations:
            with self.subTest(change=change), self.assertRaises(CodecError):
                self.codec.encode_chunk('record',0,[('/data/value',source()|change)])

    def test_policy_unknowns_and_missing_inputs_rejected(self):
        origins = [constant()|{'policySha256':'0'*64}, constant('unknown'),
                   derived([source()],'unknown'), derived([]),
                   constant()|{'extra':1}, {'kind':'guess'},
                   derived([source()])|{'policySha256':'0'*64},
                   derived([source()])|{'inputs':(source(),)}]
        for origin in origins:
            with self.subTest(origin=origin), self.assertRaises(CodecError):
                self.codec.encode_chunk('record',0,[('/data/value',origin)])

    def test_cycle_depth_fanin_and_encode_work_limits(self):
        cycle = derived([]);cycle['inputs'].append(cycle)
        deep = source()
        for _ in range(9):deep=derived([deep])
        for origin in (cycle,deep,derived([constant()]*257)):
            with self.assertRaises(CodecError):
                self.codec.encode_chunk('record',0,[('/data/value',origin)])
        low=Codec(self.ctx,limits=replace(Limits(),encode_visits=1))
        with self.assertRaises(CodecError):
            low.encode_chunk('record',0,[('/data/value',derived([source()]))])

    def test_pointer_scope_unknown_suffix_and_duplicate_roots(self):
        for entries in ([('/wrong/value',constant())], [('/data/bad~2',constant())],
                        [('/data/unknown',constant())],
                        [('/data/value',constant()),('/data/value',constant())], []):
            with self.assertRaises(CodecError):
                self.codec.encode_chunk('record',0,entries)

    def test_each_graph_budget_rejects_small_over_limit_fixture(self):
        complex_origin=derived([source(),constant()])
        entries=[('/data/value',complex_origin),('/data/id',constant())]
        for limits in (replace(Limits(),nodes=1),replace(Limits(),edges=1),
                       replace(Limits(),roots=1),replace(Limits(),fan_in=1),
                       replace(Limits(),leaf_visits=1),replace(Limits(),chunk_bytes=1)):
            with self.subTest(limits=limits),self.assertRaises(CodecError):
                Codec(self.ctx,limits=limits).encode_chunk('record',0,entries)
        with self.assertRaises(CodecError):
            Codec(self.ctx,limits=replace(Limits(),chunks=1)).encode_chunk('record',1,entries)
        raw,_=self.opened([('/data/value',constant()),('/data/id',constant())])
        reader=Resolver(self.ctx,self.codec.dictionary_bytes,self.codec.dictionary_sha256,
                        limits=replace(Limits(),record_roots=1))
        with self.assertRaises(CodecError):
            reader.validate_record('record',{'value':0,'id':'x'},[(raw,digest(raw))],expected_chunks=1)

    def test_reader_rejects_pin_tamper_noncanonical_duplicate_and_numbers(self):
        raw,_=self.opened([('/data/value',source())])
        for bad,pin in ((raw,'0'*64),(raw+b' ',digest(raw+b' ')),
                        (b'{"a":1,"a":2}\n',digest(b'{"a":1,"a":2}\n')),
                        (b'{"a":NaN}\n',digest(b'{"a":NaN}\n')),
                        (b'{"a":1.0}\n',digest(b'{"a":1.0}\n')),
                        (b'{"a":12345678901234}\n',digest(b'{"a":12345678901234}\n')),
                        (b'\xff',digest(b'\xff'))):
            with self.subTest(bad=bad[:30]), self.assertRaises(CodecError):
                self.reader.open_chunk(bad,pin)

    def test_reader_rejects_unknown_fields_versions_nodes_and_references(self):
        raw,_=self.opened([('/data/value',derived([source()]))])
        mutations = [lambda d:d.update(extra=True),
                     lambda d:d.update(schemaVersion='unknown'),
                     lambda d:d.update(dictionarySha256='0'*64),
                     lambda d:d['nodes'][0].__setitem__(0,9),
                     lambda d:d['nodes'][0].__setitem__(1,99),
                     lambda d:d['nodes'][0].__setitem__(2,0),
                     lambda d:d['nodes'][0].append(None),
                     lambda d:d['nodes'][1].__setitem__(3,[1]),
                     lambda d:d['nodes'][1].__setitem__(3,[-1]),
                     lambda d:d['nodes'][1].__setitem__(3,[True]),
                     lambda d:d['nodes'][1].__setitem__(3,[]),
                     lambda d:d['nodes'].append(d['nodes'][0]),
                     lambda d:d['groups'].append(d['groups'][0]),
                     lambda d:d['groups'][0][1][0].__setitem__(1,99)]
        for change in mutations:
            with self.subTest(change=change), self.assertRaises(CodecError):
                self.modified(raw,change)

    def test_decoder_repeated_edge_expansion_bomb_is_bounded_before_resolve(self):
        raw,chunk=self.opened([('/data/value',source())])
        doc=json.loads(raw)
        policy=0;label=self.codec._symbols.index('join')
        doc['nodes'].extend([[2,policy,label,[i]*256] for i in range(3)])
        doc['groups'][0][1][0][1]=3
        altered=wire(doc)
        with self.assertRaisesRegex(CodecError,'leaf-expansion-bound'):
            self.reader.open_chunk(altered,digest(altered))

    def test_validated_graph_and_roots_cannot_be_mutated(self):
        _,chunk=self.opened([('/data/value',derived([source()]))])
        with self.assertRaises(TypeError):chunk.nodes[1][3][0]=1
        with self.assertRaises(TypeError):chunk.roots['/data/value']=99
        with self.assertRaises(CodecError):chunk.resolve('/data/missing')

    def test_record_complete_chunk_sequence_pins_and_inventory(self):
        base,_=self.opened([('/data/id',source())])
        obs,_=self.opened([('/data/nutrients/usda:1:observation:1/value',source())],1)
        data={'id':'x','nutrients':{'usda:1:observation:1':{'value':0}}}
        chunks=[(base,digest(base)),(obs,digest(obs))]
        result=self.reader.validate_record('record',data,chunks,expected_chunks=2)
        self.assertEqual(result['roots'],2)
        for seq,count,rid,datum in ((chunks[:1],2,'record',data),
                                  (chunks,1,'record',data),
                                  (chunks[::-1],2,'record',data),
                                  (chunks,2,'other',data),
                                  (chunks,2,'record',{'id':'x'}),
                                  (chunks,2,'record',data|{'zero':0})):
            with self.assertRaises(CodecError):
                self.reader.validate_record(rid,datum,seq,expected_chunks=count)
        for malformed in ([None], [(None,'0'*64)], [(base,)]):
            with self.assertRaises(CodecError):
                self.reader.validate_record('record',data,malformed,expected_chunks=1)

    def test_record_rejects_split_groups_non_greedy_packing_and_late_base(self):
        first,_=self.opened([('/data/nutrients/a/value',constant())])
        second,_=self.opened([('/data/nutrients/b/value',constant())],1)
        data={'nutrients':{'a':{'value':0},'b':{'value':1}}}
        with self.assertRaisesRegex(CodecError,'non-greedy-packing'):
            self.reader.validate_record('record',data,[(first,digest(first)),(second,digest(second))],expected_chunks=2)
        mixed,_=self.opened([('/data/id',constant()),('/data/nutrients/a/value',constant())])
        with self.assertRaisesRegex(CodecError,'base-chunk-placement'):
            self.reader.validate_record('record',{'id':'x','nutrients':{'a':{'value':0}}},[(mixed,digest(mixed))],expected_chunks=1)

    def test_record_work_bounds_and_nonfinite_data(self):
        raw,_=self.opened([('/data/value',source())])
        for data in ({'value':float('nan')},{'value':object()}):
            with self.assertRaises(CodecError):
                self.reader.validate_record('record',data,[(raw,digest(raw))],expected_chunks=1)
        for limits in (replace(Limits(),record_bytes=1),
                       replace(Limits(),record_expanded_bytes=1),
                       replace(Limits(),record_visits=1)):
            reader=Resolver(self.ctx,self.codec.dictionary_bytes,self.codec.dictionary_sha256,limits=limits)
            if limits.record_visits==1:
                bigger,_=self.opened([('/data/value',derived([source()]))])
                pair=(bigger,digest(bigger))
            else:pair=(raw,digest(raw))
            with self.assertRaises(CodecError):
                reader.validate_record('record',{'value':0},[pair],expected_chunks=1)

    def test_greedy_sixteen_group_record_and_profile_counters(self):
        base,bc=self.opened([('/data/id',source())])
        entries=[(f'/data/nutrients/usda:{i}:observation:{i}/value',derived([source(),constant()])) for i in range(17)]
        a,ac=self.opened(entries[:16],1);b,cc=self.opened(entries[16:],2)
        data={'id':'x','nutrients':{f'usda:{i}:observation:{i}':{'value':i} for i in range(17)}}
        result=self.reader.validate_record('record',data,[(r,digest(r)) for r in (base,a,b)],expected_chunks=3)
        audits=[audit_usda_profile(c) for c in (bc,ac,cc)]
        self.assertEqual(sum(x['baseGroups'] for x in audits),1)
        self.assertEqual(sum(x['observations'] for x in audits),17)
        bound=usda_wire_bound(food_rows=1,observation_rows=17,expected_records=2)
        self.assertEqual(bound['maxChunks'],4) # two base records plus two observation chunks
        self.assertLess(len(self.codec.dictionary_bytes)+result['encodedBytes'],bound['graphAndDictionaryUpperBytes'])

    def test_usda_profile_rejects_span_fanin_base_and_observation_excess(self):
        span=source()|{'sourceSpan':{'byteStart':0,'byteEnd':1,'sha256':H,'coordinateSystem':'UTF8-bytes'}}
        for entries in ([('/data/value',span)],
                        [('/data/value',derived([constant()]*6))]):
            _,chunk=self.opened(entries)
            with self.assertRaises(CodecError):audit_usda_profile(chunk)
        suffixes=tuple('/x'+str(i) for i in range(33))
        codec=Codec(replace(self.ctx,suffixes=suffixes))
        for prefix,count in (('/data',33),('/data/nutrients/usda:1:observation:1',25)):
            raw=codec.encode_chunk('record',0,[(prefix+s,constant()) for s in suffixes[:count]])
            with self.assertRaises(CodecError):audit_usda_profile(codec.open_chunk(raw,digest(raw)))

    def test_source_bound_component_arithmetic_and_conditional_limitations(self):
        bound=usda_wire_bound(food_rows=2101279,observation_rows=27195013,expected_records=4202558)
        self.assertEqual(bound['nodeWireBounds'],{'source':len(wire([0,15,99999999,1023])),
            'constant':len(wire([1,7,1023])),'derived':len(wire([2,7,1023,[8191]*5]))})
        self.assertEqual(bound['graphAndDictionaryUpperBytes'],bound['dictionaryWireBound']+
            bound['maxChunks']*bound['frameWireBound']+4202558*bound['baseWireBound']+
            27195013*bound['observationWireBound'])
        escaped='/data/nutrients/usda:'+'\x00'*64+':observation:'+'~0'*64
        self.assertLessEqual(len(wire(escaped))-1,bound['prefixWireBound'])
        self.assertTrue(bound['conditional']);self.assertFalse(bound['fitClaim']);self.assertFalse(bound['admitted'])
        # Sparse observations may be spread across profiles as well as products.
        # F=1, R=2, O=2 needs two base plus two observation chunks, not three.
        self.assertEqual(usda_wire_bound(food_rows=1,observation_rows=2,expected_records=2)['maxChunks'],4)
        for args in ({'food_rows':1,'observation_rows':0,'expected_records':1},
                     {'food_rows':True,'observation_rows':0,'expected_records':2},
                     {'food_rows':1,'observation_rows':-1,'expected_records':2}):
            with self.assertRaises(CodecError):usda_wire_bound(**args)


if __name__=='__main__':
    unittest.main()
