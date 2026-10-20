"""Standalone, fail-closed provenance wire codec. No mapper, IO or admission.

The caller supplies trusted source/policy metadata and chunk pins. Wire metadata
never constructs authority. Legacy producers, schemas and qualifiers are untouched.
"""
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
from types import MappingProxyType


class CodecError(ValueError):
    """Fixed diagnostic codes; no source values in exception messages."""


def _fail(code):
    raise CodecError(code)


def _wire(value):
    try:
        return (json.dumps(value, sort_keys=True, ensure_ascii=False,
                           separators=(',', ':'), allow_nan=False)+'\n').encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _fail('json-invalid')


def digest(raw):
    if type(raw) is not bytes:
        _fail('bytes-required')
    return hashlib.sha256(raw).hexdigest()


def _sha(value):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
        _fail('digest-invalid')


def _text(value, limit, empty=False):
    if type(value) is not str or (not empty and not value):
        _fail('text-invalid')
    try:
        if len(value.encode('utf-8')) > limit:
            _fail('text-bound')
    except UnicodeError:
        _fail('text-invalid')


def _uint(value, maximum, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        _fail('integer-bound')


def _relative(value):
    _text(value, 512)
    path = PurePosixPath(value)
    if (path.is_absolute() or not path.parts or '..' in path.parts or '\\' in value
            or path.as_posix() != value or any(ord(c) < 32 for c in value)):
        _fail('path-invalid')


def _pointer(value, limit=1024, empty=False):
    _text(value, limit, empty)
    if value == '' and empty:
        return
    if not value.startswith('/') or re.search('~(?![01])', value):
        _fail('pointer-invalid')


def _prefix(pointer):
    _pointer(pointer)
    if pointer != '/data' and not pointer.startswith('/data/'):
        _fail('pointer-scope')
    return '/'.join(pointer.split('/')[:4]) if pointer.startswith('/data/nutrients/') else '/data'


@dataclass(frozen=True)
class Member:
    path: str
    table: str
    rows: int
    fields: tuple


@dataclass(frozen=True)
class InputPin:
    path: str
    sha256: str
    coordinate_system: str
    rows: int = 0                 # JSONL; CSV row bounds are member-specific.
    fields: tuple = ()
    members: tuple = ()


@dataclass(frozen=True)
class PolicyPin:
    sha256: str
    symbols: tuple
    transforms: tuple


@dataclass(frozen=True)
class Context:
    source_id: str
    release_id: str
    inputs: tuple
    policies: tuple
    suffixes: tuple
    rights_sha256: str
    scope_sha256: str
    clock_sha256: str | None = None


@dataclass(frozen=True)
class Limits:
    dictionary_bytes: int = 1024**2
    chunk_bytes: int = 4*1024**2
    record_bytes: int = 16*1024**2
    nodes: int = 8192
    edges: int = 32768
    roots: int = 1024
    record_roots: int = 131072
    chunks: int = 8192
    depth: int = 8
    fan_in: int = 256
    leaf_bytes: int = 65536
    leaf_visits: int = 8192
    record_expanded_bytes: int = 512*1024**2
    record_visits: int = 2_000_000
    encode_visits: int = 131072

    def validate(self):
        ceiling = Limits()
        for f in fields(self):
            _uint(getattr(self, f.name), getattr(ceiling, f.name), 1)


def _tuple(value, cap):
    if type(value) is not tuple or len(value) > cap:
        _fail('registry-invalid')
    try:
        if len(set(value)) != len(value):
            _fail('registry-invalid')
    except TypeError:
        _fail('registry-invalid')


def _compile(context, limits):
    if type(context) is not Context:
        _fail('trusted-context-required')
    _text(context.source_id, 64);_text(context.release_id, 64)
    for pin in (context.rights_sha256, context.scope_sha256):
        _sha(pin)
    if context.clock_sha256 is not None:
        _sha(context.clock_sha256)
    _tuple(context.inputs, 8);_tuple(context.policies, 8);_tuple(context.suffixes, 128)
    if not context.inputs or not context.policies or not context.suffixes:
        _fail('registry-empty')
    symbols, headers, paths, policies = set(context.suffixes), [], set(), set()
    for suffix in context.suffixes:
        _pointer(suffix, 256, True)
    for inp in context.inputs:
        if type(inp) is not InputPin:
            _fail('input-registry-invalid')
        _relative(inp.path);_sha(inp.sha256)
        if inp.path in paths:
            _fail('input-registry-duplicate')
        paths.add(inp.path)
        if inp.coordinate_system == 'csv-logical-data-row':
            if inp.rows or inp.fields:
                _fail('csv-registry-invalid')
            _tuple(inp.members, 16)
            if not inp.members:
                _fail('csv-registry-empty')
            names = set()
            for member in inp.members:
                if type(member) is not Member:
                    _fail('member-registry-invalid')
                _relative(member.path);_text(member.table, 64)
                if PurePosixPath(member.path).stem != member.table or member.path in names:
                    _fail('member-registry-invalid')
                names.add(member.path);_uint(member.rows, 99999999)
                _tuple(member.fields, 128)
                if not member.fields:
                    _fail('field-registry-empty')
                for field in member.fields:
                    _pointer(field, 256)
                    if len(field.split('/')) != 2 or field == '/':
                        _fail('csv-field-invalid')
                symbols.update(member.fields);headers.append((inp, member))
        elif inp.coordinate_system == 'jsonl-line-json-pointer':
            if inp.members:
                _fail('jsonl-registry-invalid')
            _uint(inp.rows, 99999999);_tuple(inp.fields, 128)
            if not inp.fields:
                _fail('field-registry-empty')
            for field in inp.fields:
                _pointer(field, 256)
            symbols.update(inp.fields);headers.append((inp, None))
        else:
            _fail('coordinate-system-unknown')
    for policy in context.policies:
        if type(policy) is not PolicyPin:
            _fail('policy-registry-invalid')
        _sha(policy.sha256)
        if policy.sha256 in policies:
            _fail('policy-registry-duplicate')
        policies.add(policy.sha256)
        _tuple(policy.symbols, 256);_tuple(policy.transforms, 128)
        for label in (*policy.symbols, *policy.transforms):
            _text(label, 1024)
        symbols.update(policy.symbols);symbols.update(policy.transforms)
    if len(headers) > 16 or len(symbols) > 1024:
        _fail('dictionary-count-bound')
    # Cheap escaped-string budget precedes full serialization of trusted metadata.
    cost = sum(len(_wire(s)) for s in symbols)
    if cost > limits.dictionary_bytes:
        _fail('dictionary-byte-bound')
    value = {'schemaVersion':'offmenu-product-origin-dictionary/1', 'context':asdict(context)}
    raw = _wire(value)
    if len(raw) > limits.dictionary_bytes:
        _fail('dictionary-byte-bound')
    return raw, tuple(headers), tuple(sorted(symbols))


def _span(value):
    if type(value) is not dict or set(value) != {'byteStart','byteEnd','sha256','coordinateSystem'}:
        _fail('span-invalid')
    _uint(value['byteStart'], 1024**4);_uint(value['byteEnd'],1024**4)
    if value['byteStart'] > value['byteEnd'] or value['coordinateSystem'] != 'UTF8-bytes':
        _fail('span-invalid')
    _sha(value['sha256'])
    if len(_wire(value)) > 512:
        _fail('span-bound')


def _parse(raw, pin, maximum):
    if type(raw) is not bytes or len(raw) > maximum:
        _fail('wire-byte-bound')
    _sha(pin)
    if digest(raw) != pin:
        _fail('wire-pin-mismatch')
    def integer(s):
        if len(s) > 13:
            _fail('integer-bound')
        return int(s)
    def invalid(_):
        _fail('json-number-invalid')
    def unique(pairs):
        result = {}
        for k,v in pairs:
            if k in result:
                _fail('json-duplicate-key')
            result[k] = v
        return result
    try:
        obj = json.loads(raw.decode('utf-8'), parse_int=integer, parse_float=invalid,
                         parse_constant=invalid, object_pairs_hook=unique)
    except CodecError:
        raise
    except (ValueError, UnicodeError, RecursionError):
        _fail('json-invalid')
    if _wire(obj) != raw:
        _fail('wire-not-canonical')
    return obj


class Codec:
    """Stateless chunk encoder with a presealed trusted-metadata dictionary."""
    def __init__(self, context, *, limits=Limits()):
        if type(limits) is not Limits:
            _fail('limits-invalid')
        limits.validate()
        self.context, self.limits = context, limits
        self.dictionary_bytes, self._headers, self._symbols = _compile(context, limits)
        self.dictionary_sha256 = digest(self.dictionary_bytes)
        self._symbol_ids = {v:i for i,v in enumerate(self._symbols)}
        self._policy_ids = {v.sha256:i for i,v in enumerate(context.policies)}

    def _source(self, origin):
        common = {'kind','sourceId','releaseId','inputPath','inputSha256','sourceRecordId','sourceField','coordinateSystem'}
        if origin.get('sourceId') != self.context.source_id or origin.get('releaseId') != self.context.release_id:
            _fail('source-identity-mismatch')
        span = origin.get('sourceSpan')
        if 'sourceSpan' in origin:
            _span(span)
        for index,(inp,member) in enumerate(self._headers):
            if (origin.get('inputPath'),origin.get('inputSha256'),origin.get('coordinateSystem')) != (inp.path,inp.sha256,inp.coordinate_system):
                continue
            if member is not None:
                if origin.get('archiveMember') != member.path or origin.get('table') != member.table:
                    continue
                allowed,coordinate,maximum,record = member.fields,'row',member.rows,member.path+':row:'
                extras = {'archiveMember','table','row'}
            else:
                allowed,coordinate,maximum,record = inp.fields,'line',inp.rows,'line:'
                extras = {'line'}
            if set(origin) != common | extras | ({'sourceSpan'} if 'sourceSpan' in origin else set()):
                _fail('source-fields-unknown')
            _uint(origin[coordinate],maximum,1)
            if origin['sourceRecordId'] != record+str(origin[coordinate]) or origin['sourceField'] not in allowed:
                _fail('source-coordinate-mismatch')
            node = [0,index,origin[coordinate],self._symbol_ids[origin['sourceField']]]
            if 'sourceSpan' in origin:
                node.append(dict(span))
            return node
        _fail('source-pin-or-member-mismatch')

    def _source_leaf(self, node):
        if len(node) not in (4,5):
            _fail('source-node-invalid')
        inp,member = self._headers[_index(node[1],len(self._headers))]
        field = self._symbols[_index(node[3],len(self._symbols))]
        coordinate,maximum,allowed = ('row',member.rows,member.fields) if member else ('line',inp.rows,inp.fields)
        _uint(node[2],maximum,1)
        if field not in allowed:
            _fail('source-field-unknown')
        leaf = {'kind':'source','sourceId':self.context.source_id,'releaseId':self.context.release_id,
                'inputPath':inp.path,'inputSha256':inp.sha256,'sourceField':field,'coordinateSystem':inp.coordinate_system}
        leaf[coordinate] = node[2]
        if member:
            leaf.update(archiveMember=member.path,table=member.table,sourceRecordId=member.path+':row:'+str(node[2]))
        else:
            leaf['sourceRecordId'] = 'line:'+str(node[2])
        if len(node) == 5:
            if type(node[4]) not in (dict,tuple):
                _fail('span-invalid')
            span = dict(node[4])
            _span(span);leaf['sourceSpan'] = span
        return leaf

    def _label(self, node, kind):
        if len(node) != (3 if kind == 1 else 4):
            _fail('policy-node-invalid')
        policy = self.context.policies[_index(node[1],len(self.context.policies))]
        label = self._symbols[_index(node[2],len(self._symbols))]
        if label not in (policy.symbols if kind == 1 else policy.transforms):
            _fail('policy-symbol-unknown')
        return policy.sha256,label

    def encode_chunk(self, record_id, chunk_ordinal, entries):
        _text(record_id,256);_uint(chunk_ordinal,self.limits.chunks-1)
        nodes,intern,info,roots,groups = [],{},[],{},{}
        visits = 0
        def node(origin, depth=0, active=None):
            nonlocal visits
            visits += 1
            if visits > self.limits.encode_visits or depth > self.limits.depth or type(origin) is not dict:
                _fail('encode-work-bound')
            active = set() if active is None else active
            if id(origin) in active:
                _fail('origin-cycle')
            active.add(id(origin))
            try:
                kind = origin.get('kind')
                if kind == 'source':
                    value = self._source(origin)
                elif kind in ('constant','derived'):
                    expected = {'kind','policySha256','symbol' if kind=='constant' else 'transform'}
                    if kind == 'derived':expected.add('inputs')
                    if set(origin) != expected or origin['policySha256'] not in self._policy_ids:
                        _fail('origin-policy-invalid')
                    label = origin['symbol' if kind=='constant' else 'transform']
                    if label not in self._symbol_ids:
                        _fail('policy-symbol-unknown')
                    value = [1 if kind=='constant' else 2,self._policy_ids[origin['policySha256']],self._symbol_ids[label]]
                    self._label(value if kind=='constant' else value+[[]],value[0])
                    if kind == 'derived':
                        if type(origin['inputs']) is not list or not 1 <= len(origin['inputs']) <= self.limits.fan_in:
                            _fail('derived-fanin')
                        value.append([node(child,depth+1,active) for child in origin['inputs']])
                else:_fail('origin-kind-unknown')
                key = _wire(value)
                if key not in intern:
                    if len(nodes) >= self.limits.nodes:_fail('node-bound')
                    info.append(_node_info(self,value,len(nodes),info))
                    intern[key] = len(nodes);nodes.append(value)
                return intern[key]
            finally:
                active.remove(id(origin))
        try:
            for entry in entries:
                if type(entry) not in (tuple,list) or len(entry) != 2:_fail('entry-invalid')
                pointer,origin = entry
                prefix = _prefix(pointer);_text(prefix,512)
                suffix = pointer[len(prefix):]
                if suffix not in self.context.suffixes:_fail('suffix-unknown')
                if pointer in roots:_fail('pointer-duplicate')
                if len(roots) >= self.limits.roots:_fail('root-bound')
                roots[pointer] = node(origin)
                groups.setdefault(prefix,[]).append([self._symbol_ids[suffix],roots[pointer]])
                if len(groups) > 17:_fail('group-bound')
        except CodecError:raise
        except Exception:_fail('entries-invalid')
        if not roots:_fail('empty-chunk')
        raw = _wire({'schemaVersion':'offmenu-product-origin-chunk/1','dictionarySha256':self.dictionary_sha256,
            'recordId':record_id,'chunkOrdinal':chunk_ordinal,'nodes':nodes,
            'groups':[[p,sorted(v)] for p,v in sorted(groups.items())]})
        # Use the same strict validator as the reader, including orphan/edge caps.
        self.open_chunk(raw,digest(raw))
        return raw

    def open_chunk(self, raw, expected_sha256):
        return LeafResolver(self,raw,expected_sha256)


def _index(value, size):
    _uint(value,size-1)
    return value


def _node_info(codec, node, index, previous):
    if type(node) is not list or not node or type(node[0]) is not int:
        _fail('node-invalid')
    kind = node[0]
    if kind == 0:
        leaf = codec._source_leaf(node);depth,visits,size = 0,1,len(_wire(leaf))-1
    elif kind == 1:
        policy,label = codec._label(node,kind)
        depth,visits,size = 0,1,len(_wire({'kind':'constant','policySha256':policy,'symbol':label}))-1
    elif kind == 2:
        policy,label = codec._label(node,kind)
        if type(node[3]) is not list or not 1 <= len(node[3]) <= codec.limits.fan_in:_fail('derived-fanin')
        children = [previous[_index(ref,index)] for ref in node[3]]
        depth,visits = 1+max(c[0] for c in children),1+sum(c[1] for c in children)
        size = len(_wire({'kind':'derived','policySha256':policy,'transform':label,'inputs':[]}))-1
        size += sum(c[2] for c in children)+len(children)-1
    else:_fail('node-kind-unknown')
    if depth > codec.limits.depth or visits > codec.limits.leaf_visits or size > codec.limits.leaf_bytes:
        _fail('leaf-expansion-bound')
    return depth,visits,size


class Resolver:
    """Dictionary bytes must equal the trusted compilation and supplied SHA."""
    def __init__(self, context, dictionary_bytes, expected_sha256, *, limits=Limits()):
        self.codec = Codec(context,limits=limits)
        _sha(expected_sha256)
        if (type(dictionary_bytes) is not bytes or len(dictionary_bytes)>limits.dictionary_bytes
                or digest(dictionary_bytes)!=expected_sha256 or dictionary_bytes!=self.codec.dictionary_bytes):
            _fail('dictionary-pin-or-context')

    def open_chunk(self, raw, expected_sha256):
        return self.codec.open_chunk(raw,expected_sha256)

    def validate_record(self, record_id, data, chunks, *, expected_chunks):
        """Structural/pin coverage only; caller still needs source-value semantics."""
        _text(record_id,256);_uint(expected_chunks,self.codec.limits.chunks,1)
        expected = _data_pointers(data,self.codec.limits.record_roots)
        if not expected:_fail('empty-data-scope')
        seen,prefixes,encoded,expanded,visits = set(),set(),0,0,0
        previous_observations = None
        count = 0
        for pair in chunks:
            if type(pair) not in (tuple,list) or len(pair) != 2:
                _fail('chunk-pair-invalid')
            raw,pin = pair
            if type(raw) is not bytes:
                _fail('bytes-required')
            if count >= expected_chunks:_fail('extra-chunk')
            encoded += len(raw)
            if encoded > self.codec.limits.record_bytes:_fail('record-wire-bound')
            chunk = self.open_chunk(raw,pin)
            if chunk.record_id!=record_id or chunk.ordinal!=count:_fail('chunk-sequence')
            if previous_observations is not None and previous_observations != 16:
                _fail('non-greedy-packing')
            if chunk.base and (count != 0 or chunk.observations):_fail('base-chunk-placement')
            previous_observations = None if chunk.base else chunk.observations
            for prefix in chunk.prefixes:
                if prefix in prefixes:_fail('group-split-or-duplicate')
                prefixes.add(prefix)
            for pointer,ref in chunk.roots.items():
                if pointer not in expected or pointer in seen:_fail('pointer-inventory')
                seen.add(pointer)
                visits += chunk.info[ref][1];expanded += chunk.info[ref][2]
                if visits>self.codec.limits.record_visits or expanded>self.codec.limits.record_expanded_bytes:
                    _fail('record-expansion-bound')
            count += 1
        if count!=expected_chunks or seen!=expected:_fail('incomplete-record')
        return {'recordId':record_id,'chunks':count,'roots':len(seen),'encodedBytes':encoded,
                'expandedBytes':expanded,'expandedVisits':visits,'qualified':False,'accepted':False}


class LeafResolver:
    def __init__(self, codec, raw, pin):
        self.codec = codec
        doc = _parse(raw,pin,codec.limits.chunk_bytes)
        if type(doc) is not dict or set(doc)!={'schemaVersion','dictionarySha256','recordId','chunkOrdinal','groups','nodes'}:
            _fail('chunk-fields')
        if doc['schemaVersion']!='offmenu-product-origin-chunk/1' or doc['dictionarySha256']!=codec.dictionary_sha256:
            _fail('chunk-dictionary-or-version')
        _text(doc['recordId'],256);_uint(doc['chunkOrdinal'],codec.limits.chunks-1)
        self.record_id,self.ordinal = doc['recordId'],doc['chunkOrdinal']
        nodes,groups = doc['nodes'],doc['groups']
        if type(nodes) is not list or not 1<=len(nodes)<=codec.limits.nodes:_fail('node-bound')
        if type(groups) is not list or not 1<=len(groups)<=17:_fail('group-bound')
        info,edges = [],0
        for i,node in enumerate(nodes):
            info.append(_node_info(codec,node,i,info))
            if node[0]==2:edges+=len(node[3])
            if edges>codec.limits.edges:_fail('edge-bound')
        roots,prefixes = {},set()
        for group in groups:
            if type(group) is not list or len(group)!=2:_fail('group-invalid')
            prefix,items = group;_pointer(prefix,512)
            if prefix in prefixes or type(items) is not list or not items:_fail('group-invalid')
            prefixes.add(prefix)
            for item in items:
                if type(item) is not list or len(item)!=2:_fail('root-invalid')
                suffix=codec._symbols[_index(item[0],len(codec._symbols))]
                pointer=prefix+suffix
                if suffix not in codec.context.suffixes or _prefix(pointer)!=prefix:_fail('root-scope')
                if pointer in roots or len(roots)>=codec.limits.roots:_fail('pointer-duplicate-or-bound')
                roots[pointer]=_index(item[1],len(nodes))
        observations=sum(p!='/data' for p in prefixes)
        if observations>16:_fail('observation-group-bound')
        used=set();pending=list(roots.values())
        while pending:
            ref=pending.pop()
            if ref not in used:
                used.add(ref)
                if nodes[ref][0]==2:pending.extend(nodes[ref][3])
        if used!=set(range(len(nodes))):_fail('orphan-node')
        # Keep validated references immutable. Returned leaves are fresh trees.
        frozen = []
        for node in nodes:
            if node[0] == 2:
                frozen.append(tuple(node[:3])+(tuple(node[3]),))
            elif node[0] == 0 and len(node) == 5:
                frozen.append(tuple(node[:4])+(tuple(sorted(node[4].items())),))
            else:
                frozen.append(tuple(node))
        self.nodes,self.info = tuple(frozen),tuple(info)
        self.roots,self.prefixes = MappingProxyType(roots),frozenset(prefixes)
        self.base,self.observations = '/data' in prefixes,observations

    def resolve(self, pointer):
        """Return one fresh expanded leaf, bounded before materialization."""
        if pointer not in self.roots:_fail('pointer-missing')
        def expand(ref):
            node=self.nodes[ref]
            if node[0]==0:return self.codec._source_leaf(node)
            policy,label=self.codec._label(node,node[0])
            if node[0]==1:return {'kind':'constant','policySha256':policy,'symbol':label}
            return {'kind':'derived','policySha256':policy,'transform':label,'inputs':[expand(r) for r in node[3]]}
        return expand(self.roots[pointer])

    def iter_leaves(self):
        for pointer in sorted(self.roots):
            yield pointer,self.resolve(pointer)


def _data_pointers(data, maximum):
    result=set();stack=[(data,'/data',0)];visited=0
    while stack:
        value,pointer,depth=stack.pop();visited+=1
        if depth>32 or visited>262144:_fail('data-work-bound')
        _pointer(pointer)
        if type(value) is dict:
            if len(value)>maximum:_fail('data-work-bound')
            for key,child in value.items():
                _text(key,512,True)
                stack.append((child,pointer+'/'+key.replace('~','~0').replace('/','~1'),depth+1))
        elif type(value) is list:
            if len(value)>maximum:_fail('data-work-bound')
            stack.extend((child,pointer+'/'+str(i),depth+1) for i,child in enumerate(value))
        elif value is None or type(value) in (str,int,float,bool):
            if type(value) is float and not math.isfinite(value):
                _fail('data-number-invalid')
            if len(result)>=maximum:_fail('data-root-bound')
            result.add(pointer)
        else:_fail('data-type-invalid')
    return result


def audit_usda_profile(chunk):
    """Check shape assumptions used by the conditional size theorem, not values."""
    if type(chunk) is not LeafResolver:_fail('chunk-resolver-required')
    result={'baseGroups':0,'observations':0}
    for prefix in chunk.prefixes:
        pending=[ref for pointer,ref in chunk.roots.items() if _prefix(pointer)==prefix];root_count=len(pending);used=set()
        while pending:
            ref=pending.pop()
            if ref in used:continue
            used.add(ref);node=chunk.nodes[ref]
            if node[0]==0:
                if len(node)!=4 or chunk.codec._headers[node[1]][1] is None:_fail('usda-profile-source')
            elif node[0]==2:
                if len(node[3])>5:_fail('usda-profile-fanin')
                pending.extend(node[3])
        counts=[sum(chunk.nodes[r][0]==kind for r in used) for kind in (0,1,2)]
        if prefix=='/data':
            if root_count>32 or len(used)>128:_fail('usda-profile-base')
            result['baseGroups']+=1
        else:
            # 64UTF8-byte nutrient and row IDs, escaped as JSON pointers and JSON:
            # <=6 bytes per original byte plus fixed namespace/suffix framing.
            prefix_bound=len(_wire('/data/nutrients/usda:'))-1+6*128+len(':observation:')
            if len(_wire(prefix))-1>prefix_bound or root_count>24 or counts[0]>17 or counts[1]>4 or counts[2]>20:
                _fail('usda-profile-observation')
            result['observations']+=1
    return result


def usda_wire_bound(*, food_rows, observation_rows, expected_records):
    """Proved wire-only upper bound IF every record/chunk passes profile audit.

    Also requires exactly one base group per native record and exactly one
    complete nutrient group per witnessed food_nutrient row. Counters and these
    obligations need future mapper/wrapper verification; this function admits none.
    """
    _uint(food_rows,99999999,1);_uint(observation_rows,99999999)
    if type(expected_records) is not int or expected_records!=2*food_rows:_fail('native-count-mismatch')
    source=len(_wire([0,15,99999999,1023]))
    constant=len(_wire([1,7,1023]))
    derived=len(_wire([2,7,1023,[8191]*5]))
    root=len(_wire([1023,8191]))
    prefix=len(_wire('/data/nutrients/usda:'))-1+6*128+len(':observation:')
    observation=17*source+4*constant+20*derived+prefix+6+24*root
    base=128*max(source,constant,derived)+len(_wire('/data'))-1+6+32*root
    frame=len(_wire({'schemaVersion':'offmenu-product-origin-chunk/1','dictionarySha256':'f'*64,
        'recordId':'\0'*256,'chunkOrdinal':8191,'groups':[],'nodes':[]}))
    # Any of the native records may own observations. Do not assume that only
    # product records (rather than profiles too) contain them. For k nonempty
    # records, sum ceil(o_i/16) <= floor((O+15*k)/16), k <= min(O,R).
    chunks=expected_records+(observation_rows+15*min(observation_rows,expected_records))//16
    upper=Limits().dictionary_bytes+chunks*frame+expected_records*base+observation_rows*observation
    return {'sourceRows':food_rows,'observations':observation_rows,'nativeRecords':expected_records,
        'maxChunks':chunks,'nodeWireBounds':{'source':source,'constant':constant,'derived':derived},
        'rootWireBound':root,'prefixWireBound':prefix,'frameWireBound':frame,
        'observationWireBound':observation,'baseWireBound':base,'dictionaryWireBound':Limits().dictionary_bytes,
        'graphAndDictionaryUpperBytes':upper,'conditional':True,'fitClaim':False,'admitted':False,
        'excluded':'Native/ref candidate bytes, DB, indexes, staging, virtual expansion work, RAM/CPU and capacity. Spans/non-USDA shapes not covered.'}
