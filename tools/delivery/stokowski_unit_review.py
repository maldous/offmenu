"""Fixed incoming-only local review transport, JSON stdin/stdout (1 MiB).

Adoption contract: the authenticated gateway owner supplies reviewedCurrentUnit;
never accept it from a coding child/report. It pins source_head/source_sha256,
python_sha256, actor_uid, runtime, runtime_root, workspace_roots, claim_root,
controller_directory, issue, unit_binding and validation_receipt. Paths/hashes
are admitted out of band by that owner. Existing Controller binding/state/claim
and its final graph checkpoint must already exist. No new owner receipt schema
or OAuth transfer is asserted. Same-UID malicious actors are outside the private
owner boundary. Requested model/provider remain review evidence fields; unknown
observations must be recorded as unknown by the review source, never inferred.
The retained review must additionally bind requested_model, requested_provider,
resolved_model and resolution_status (observed/unknown) in its evidence hash.

Wire v2 is {version:2, mode:"status"|"write", payload:<JSON string>,
evidence:<JSON string>}. payload contains exactly {context,envelope}; evidence
contains the packet projection. request_sha256 and evidence_sha256 hash those
EXACT UTF-8 strings (no BOM/newline), independently of order/number spelling.
The complete outer input/output is bounded to 1 MiB. The JSON domain is bounded
to depth <64, Unicode scalar strings, finite fractions and safe integers
(abs <= 2**53-1); negative zero and nonfinite/unsafe integers are rejected.
Original Python int/float distinctions are restored ONLY from the typed graph
observation and original receipt JSON. context.validation_receipt_source is an
owner-pinned {path,sha256} to a private regular original artifact inside the task
runtime, in addition to the unchanged validation_receipt projection. Its bytes
must pass the original Journal receipt digest. Review/qualification/native and
packet digests remain Python v1, never recomputed from JS-normalized values.
legacy_evidence_sha256 reports that original packet digest; it is not the v2
transport evidence hash. Unversioned/v1 transport is rejected; existing v1
incoming records remain byte-identical and are accepted only by the original
packet checks, without upgrades or rewrites.
"""
import hashlib
import math
import json
import os
from pathlib import Path
import sqlite3
import struct
import sys

from stokowski_adapter import CurrentWork, SOURCE, file_sha, read_record
from symphony_capacity import AdmissionError, digest

LIMIT = 1024 * 1024
PYTHON = Path('/home/user/src/offmenu/.delivery/stokowski/venv/bin/python')
REQUIRED = {'tools/delivery/stokowski_unit_review.py',
            'tools/delivery/integration-gateway.mjs',
            'tools/delivery/stokowski_operations.py',
            'tools/delivery/stokowski_stage.py',
            'src/offmenu/delivery/integration.py'}


def require(ok):
    if not ok:
        raise AdmissionError('local_review_binding')


def wire_value(value, depth=0):
    """v2 JSON domain. Legacy digest() remains completely unchanged.

    Safe integral numbers and finite fractions only; reject negative zero,
    nonfinite, unsafe integral values, surrogate codepoints and deep trees.
    Original Python int/float distinctions come only from retained artifacts.
    """
    require(depth < 64)
    if value is None or type(value) is bool:
        return
    if type(value) in (int, float):
        require(math.isfinite(value) and not (value == 0 and math.copysign(1, value) < 0)
                and (value % 1 != 0 or abs(value) <= 9007199254740991))
    elif isinstance(value, str):
        require(not any(0xd800 <= ord(c) <= 0xdfff for c in value))
    elif isinstance(value, list):
        for item in value:
            wire_value(item, depth+1)
    elif isinstance(value, dict):
        for key, item in value.items():
            require(isinstance(key, str))
            wire_value(key, depth+1)
            wire_value(item, depth+1)
    else:
        require(False)


def same_wire(a, b):
    """Compare projections without Python's bool/int equality ambiguity."""
    wire_value(a)
    wire_value(b)
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same_wire(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same_wire(x,y) for x,y in zip(a,b))
    return a == b


def decode(raw):
    def unique(pairs):
        out = {}
        for k, v in pairs:
            require(k not in out)
            out[k] = v
        return out
    return json.loads(raw, object_pairs_hook=unique,
                      parse_constant=lambda _: require(False))


def canonical(value):
    p = Path(value)
    require(p.is_absolute() and p == p.resolve())
    return p


def custody(path, uid, *, private=False):
    path = canonical(str(path))
    st = path.stat()
    require(st.st_uid == uid and not st.st_mode & (0o077 if private else 0o022))
    return path


def checkpoint_json(raw):
    """Decode only JSON-compatible MessagePack from the existing saver schema.

    No pickle, extension objects, imports or arbitrary object constructors.
    Stokowski's pinned interpreter intentionally has no LangGraph dependency.
    """
    offset = 0
    def take(n):
        nonlocal offset
        require(0 <= n <= LIMIT and offset+n <= len(raw))
        value = raw[offset:offset+n]
        offset += n
        return value
    def unpack(depth=0):
        require(depth < 64)
        tag = take(1)[0]
        if tag <= 0x7f:
            return tag
        if tag >= 0xe0:
            return tag-256
        if 0xa0 <= tag <= 0xbf:
            return take(tag & 31).decode('utf8')
        if tag in (0xc0, 0xc2, 0xc3):
            return {0xc0:None, 0xc2:False, 0xc3:True}[tag]
        formats = {0xca:'>f',0xcb:'>d',0xcc:'>B',0xcd:'>H',0xce:'>I',0xcf:'>Q',
                   0xd0:'>b',0xd1:'>h',0xd2:'>i',0xd3:'>q'}
        if tag in formats:
            fmt = formats[tag]
            return struct.unpack(fmt,take(struct.calcsize(fmt)))[0]
        if tag in (0xd9,0xda,0xdb):
            n = int.from_bytes(take({0xd9:1,0xda:2,0xdb:4}[tag]),'big')
            return take(n).decode('utf8')
        if 0x90 <= tag <= 0x9f or tag in (0xdc,0xdd):
            n = tag & 15 if tag < 0xa0 else int.from_bytes(take(2 if tag==0xdc else 4),'big')
            require(n <= LIMIT)
            return [unpack(depth+1) for _ in range(n)]
        if 0x80 <= tag <= 0x8f or tag in (0xde,0xdf):
            n = tag & 15 if tag < 0x90 else int.from_bytes(take(2 if tag==0xde else 4),'big')
            require(n <= LIMIT)
            out = {}
            for _ in range(n):
                key = unpack(depth+1)
                require(isinstance(key,str) and key not in out)
                out[key] = unpack(depth+1)
            return out
        raise AdmissionError('local_review_checkpoint_type')
    value = unpack()
    require(offset == len(raw))
    return value


def handle(request):
    # No v1 transport is accepted: its numeric/key canonicalization was unsafe.
    # Existing incoming packets/state retain their original legacy identities.
    require(set(request) == {'version','mode','payload','evidence'}
            and type(request['version']) is int and request['version'] == 2
            and request['mode'] in ('status', 'write'))
    require(all(isinstance(request[k],str) and len(request[k].encode('utf8')) <= LIMIT
                for k in ('payload','evidence')))
    payload = decode(request['payload'])
    require(set(payload) == {'context','envelope'})
    wire_value(payload)
    c, envelope = payload['context'], payload['envelope']
    require(set(c) == {'source_head', 'source_sha256', 'python_sha256', 'actor_uid',
        'runtime', 'runtime_root', 'workspace_roots', 'claim_root', 'controller_directory',
        'issue', 'unit_binding', 'validation_receipt', 'validation_receipt_source'})
    uid = c['actor_uid']
    require(type(uid) is int and os.getuid() == os.geteuid() == uid)
    # Kernel parent identity, not a caller-provided authenticated/owner string.
    parent = Path('/proc')/str(os.getppid())
    require(parent.stat().st_uid == uid)
    require(file_sha(PYTHON.resolve()) == c['python_sha256'])
    require(Path('/proc/self/exe').resolve() == PYTHON.resolve())
    root = custody(c['runtime_root'], uid, private=True)
    runtime = custody(c['runtime'], uid, private=True)
    claim = custody(c['claim_root'], uid, private=True)
    directory = custody(c['controller_directory'], uid, private=True)
    require(root.name == 'stokowski' and root.parent.name == '.delivery'
            and runtime.is_relative_to(root) and directory.is_relative_to(claim)
            and claim.name == 'integration' and claim.parent == root.parent)
    # Only exact consumed files: no runtime traversal, refresh, chmod or repair.
    for p in (runtime/'current.json', runtime/'current-owner.json',
              runtime/'installation.json', runtime/'workflow.yaml',
              runtime/'capacity-policy.json', directory/'binding.json',
              directory/'state.json', directory/'graph.sqlite',
              claim/'repository-claim.json'):
        custody(p, uid, private=True)
    current = CurrentWork(runtime, read_only=True)
    require(current.root == root and current.config['source_head'] == c['source_head']
            and current.config['source_sha256'] == c['source_sha256']
            and REQUIRED.issubset(c['source_sha256']))
    # guard() checks every source hash against exact accepted Git bytes.
    for p in (SOURCE, *[SOURCE/n for n in c['source_sha256']]):
        custody(p, uid)
    entry = current.entries[c['issue']]
    task_runtime, _, source = current.context(c['issue'], review=True)
    custody(task_runtime, uid, private=True)
    for name in ('current-admission.json','manifest.json','capacity-policy.json',
                 'installation.json','provider-proof.json','validation-bindings.json',
                 'operations/operations.sqlite','requests/'+c['issue']+'.json',
                 *['attempts/'+c['issue']+'/'+n for n in
                   ('intent.json','dispatch-intent.json','receipt.json')]):
        custody(task_runtime/name, uid, private=True)
    custody(current.catalog, uid, private=True)
    roots = [custody(p, uid, private=True) for p in c['workspace_roots']]
    require(roots and any(source.is_relative_to(p) for p in roots))
    b = read_record(directory/'binding.json')
    decision = read_record(directory/'state.json')
    owner_claim = read_record(claim/'repository-claim.json')
    require(owner_claim == dict(binding_sha256=digest(b), directory=str(directory), owner=b['owner']))
    require(b['owner'] == current.config['owner'] and b['issue_id'] == entry['issue_id'])
    # Read the existing controller's final checkpoint through SQLite RO. Avoid
    # SqliteSaver setup (DDL/PRAGMA writes) and Controller construction entirely.
    with sqlite3.connect((directory/'graph.sqlite').as_uri()+'?mode=ro', uri=True) as db:
        row = db.execute("SELECT type,checkpoint FROM checkpoints WHERE thread_id=? AND checkpoint_ns='' ORDER BY checkpoint_id DESC LIMIT 1", (digest(b),)).fetchone()
    require(row is not None)
    require(row[0] == 'msgpack' and len(row[1]) <= LIMIT)
    channels = checkpoint_json(row[1])['channel_values']
    require(same_wire(channels['result'], decision)
            and same_wire(decision, envelope['decision'])
            and same_wire(channels['observation'], envelope['snapshot']))
    # Read the pinned original receipt, preserving 1.0 versus 1 for legacy
    # Journal digest verification. The authenticated owner's pin is additional
    # custody; _check_unit_review still verifies the original journal hash.
    receipt_source = c['validation_receipt_source']
    require(set(receipt_source) == {'path','sha256'})
    receipt_path = custody(receipt_source['path'], uid, private=True)
    require(receipt_path.is_relative_to(task_runtime) and receipt_path.is_file()
            and receipt_path.stat().st_size <= LIMIT)
    receipt_raw = receipt_path.read_bytes()
    require(len(receipt_raw) <= LIMIT
            and hashlib.sha256(receipt_raw).hexdigest() == receipt_source['sha256'])
    receipt = decode(receipt_raw)
    require(same_wire(receipt, c['validation_receipt']))
    packet = dict(issue=c['issue'], unit_binding=c['unit_binding'], integration_binding=b,
                  snapshot=channels['observation'], decision=decision,
                  validation_receipt=receipt)
    require(same_wire(decode(request['evidence']), packet))
    current._check_unit_review(packet)
    gate = current.state['tasks'][c['issue']].get('unit_gate', {})
    require(gate.get('binding') == packet['unit_binding']
            and gate.get('disposition') in ('waiting','approved')
            and gate.get('accepted_delivery', False) is False)
    review = packet['snapshot']['review']
    require(review.get('requested_model') and review.get('requested_provider')
            and review.get('resolution_status') in ('observed','unknown')
            and ((review['resolution_status'] == 'unknown' and review.get('resolved_model') is None)
                 or (review['resolution_status'] == 'observed' and review.get('resolved_model'))))
    for name in b['outputs']:
        custody(task_runtime/'workspaces'/c['issue']/name, uid, private=True)
    incoming = runtime/('unit-review-' + c['issue'] + '.json')
    raw = json.dumps(packet, sort_keys=True, separators=(',', ':')).encode()
    if incoming.exists():
        custody(incoming, uid, private=True)
        require(incoming.read_bytes() == raw)
        status = 'retained'
    elif request['mode'] == 'status':
        status = 'absent'
    else:
        current.unit_review_writer(lambda _: packet)(envelope)
        status = 'retained'
    return dict(version=2, status=status,
                request_sha256=hashlib.sha256(request['payload'].encode('utf8')).hexdigest(),
                evidence_sha256=hashlib.sha256(request['evidence'].encode('utf8')).hexdigest(),
                legacy_evidence_sha256=digest(packet), operation_key=b['validation_operation_key'],
                issue=c['issue'], source_head=c['source_head'], unit_binding=c['unit_binding'])


def main():
    try:
        raw = sys.stdin.buffer.read(LIMIT + 1)
        require(len(raw) <= LIMIT)
        result = handle(decode(raw))
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    except Exception:
        # No payloads, paths, logs, credentials or exception strings escape.
        print('{"error":"local_review_refused"}')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
