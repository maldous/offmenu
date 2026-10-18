"""Static historical handlers in a bounded offline subprocess, never a CLI plugin.

The audit hook protects trusted adapter mistakes; it is not a hostile-code sandbox.
"""
from contextlib import ExitStack
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys


# Independently reviewed implementation identity, never supplied by a bundle.
NATIONAL_ORIGIN_POLICY_SHA256 = "35141a082fe2048a432ecac9c9672d8224eaaffdc58a6e60e5189fa6dee67838"

def main():
    sys.dont_write_bytecode = True
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    # Each registered handler creates at most four files including our receipt.
    resource.setrlimit(resource.RLIMIT_FSIZE, (64 * 1024**2, 64 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    request = json.loads(sys.stdin.buffer.read(1024 * 1024 + 1))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from offmenu.refresh.execution import ADAPTERS, Admission, verify_contract, _release, MAX_OUTPUT
    entry = Admission(**request['entry'])
    bundle, destination, repository = map(Path, (request['bundle'], request['destination'], request['repository']))
    verify_contract(entry, bundle)
    destination.parent.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()

    def guard(event, args):
        if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in ('os.system', 'os.exec', 'os.posix_spawn', 'os.fork'):
            raise RuntimeError('offline-operation-denied')
        if event == 'open':
            name, mode, flags = args
            if isinstance(name, (str, bytes, os.PathLike)) and ((flags or 0) & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)):
                path = Path(os.fsdecode(name)).resolve()
                if not path.is_relative_to(root):
                    raise RuntimeError('write-outside-staging-denied')
        if event in ('os.remove', 'os.rename', 'os.rmdir', 'os.link', 'os.symlink'):
            raise RuntimeError('filesystem-mutation-denied')
        if event == 'os.mkdir' and not Path(args[0]).resolve().is_relative_to(root):
            raise RuntimeError('mkdir-outside-staging-denied')
    # Load the installed workbook runtime before forbidding subsequent native
    # library loads. Source adapters themselves remain under the offline guard.
    import openpyxl
    sys.addaudithook(guard)
    # Recheck implementation identities inside the worker immediately before import.
    from offmenu.refresh.execution import NATIONAL
    release = _release(entry.source_id)
    dependencies = ((release['handler']['path'], release['handler']['gitBlobSha']),) + ADAPTERS[entry.source_id]['dependencies']
    for name, expected in dependencies:
        body = (repository / name).read_bytes()
        if hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() != expected:
            raise ValueError('handler-pin-mismatch')
    # SourceFileLoader otherwise prefers timestamp-valid bytecode, which is not
    # covered by the verified Git source blob. Force exact source bytes for both
    # direct and nested legacy dependency loaders; ignore all scripts/*.pyc.
    import importlib.machinery
    loader = importlib.machinery.SourceFileLoader
    original_get_code = loader.get_code
    source_pins = {str((repository / name).resolve()): expected for name, expected in dependencies}
    def source_only_code(self, fullname):
        path = Path(self.path).resolve()
        if path.is_relative_to((repository / 'scripts').resolve()):
            expected = source_pins.get(str(path))
            if expected is None:
                raise ValueError('unreviewed-handler-dependency')
            body = path.read_bytes()
            if hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() != expected:
                raise ValueError('handler-source-pin-mismatch')
            return compile(body, str(path), 'exec', dont_inherit=True)
        return original_get_code(self, fullname)
    loader.get_code = source_only_code
    spec = ADAPTERS[entry.source_id]
    handler = repository / _release(entry.source_id)['handler']['path']
    module_spec = importlib.util.spec_from_file_location('reviewed_historical_handler', handler)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    from offmenu.refresh.national_tabular import ADAPTERS as TABULAR_ADAPTERS, preflight
    if entry.source_id in TABULAR_ADAPTERS:
        preflight(entry.source_id, bundle, module)
    if spec['mode'] == 'records':
        records = getattr(module, spec['function'])(bundle)
        destination.mkdir()
        with gzip.open(destination / 'normalized.jsonl.gz', 'wt', encoding='utf-8') as f:
            for row in records:
                f.write(json.dumps([row], ensure_ascii=False, allow_nan=False) + '\n')
    elif spec['mode'] == 'source-collect':
        module.collect(entry.source_id, bundle, destination)
    else:
        module.collect(bundle, destination)
    # Re-serialize all legacy timestamps using the acquisition evidence; check
    # identity, source, count and expanded size before a candidate can be reused.
    seen = set()
    expanded = 0
    output = destination / 'candidate.jsonl'
    with ExitStack() as stack:
        origins = None
        if entry.source_id in ('afcd', 'mext'):
            from offmenu.refresh.national_field_origins import NationalWorkbookOrigins
            origins = stack.enter_context(NationalWorkbookOrigins(
                entry.source_id, entry.release_id, bundle,
                {name: digest for name, size, digest in entry.inputs}, module,
                policy_pin=NATIONAL_ORIGIN_POLICY_SHA256))
        candidate_bytes = 0
        with gzip.open(destination / 'normalized.jsonl.gz', 'rt', encoding='utf-8') as source, output.open('w', encoding='utf-8') as target:
            while True:
                line = source.readline(min(8 * 1024**2, MAX_OUTPUT - expanded + 1))
                if not line:
                    break
                expanded += len(line.encode('utf-8'))
                if expanded > MAX_OUTPUT or not line.endswith('\n'):
                    raise ValueError('expanded-output-bound-exceeded')
                packet = json.loads(line)
                if not isinstance(packet, list) or len(packet) != 1:
                    raise ValueError('invalid-record-packet')
                row = packet[0]
                if row['kind'] != 'nutrientProfile' or row['schemaVersion'] != '1.0' or row['provenance']['sourceId'] != entry.source_id or row['id'] in seen:
                    raise ValueError('invalid-source-record')
                seen.add(row['id'])
                row['provenance']['fetchedAt'] = entry.acquired_at
                row['provenance']['releaseId'] = entry.release_id
                if origins is not None:
                    row = origins.annotate(row)
                    packet = [row]
                serialized = json.dumps(packet, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False) + '\n'
                serialized_bytes = len(serialized.encode('utf-8'))
                candidate_bytes += serialized_bytes
                if serialized_bytes > 8 * 1024**2 or candidate_bytes > MAX_OUTPUT:
                    raise ValueError('origin-expanded-output-bound-exceeded')
                target.write(serialized)
    if len(seen) != entry.expected_records or sum(p.stat().st_size for p in destination.iterdir()) > MAX_OUTPUT:
        raise ValueError('output-contract-mismatch')
    h = hashlib.sha256()
    with output.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    receipt = {'sourceId': entry.source_id, 'releaseId': entry.release_id,
               'normalizedRecords': len(seen), 'candidateSha256': h.hexdigest(),
               'candidateBytes': output.stat().st_size, 'acquiredAt': entry.acquired_at,
               'rightsEvidenceSha256': entry.rights_evidence_sha256,
               'scopeEvidenceSha256': entry.scope_evidence_sha256,
               'acceptedCount': None, 'acceptance': 'not-performed',
               'qualification': 'not-performed', 'publication': 'not-enabled'}
    if entry.source_id in ('afcd', 'mext'):
        receipt['fieldOriginPolicySha256'] = NATIONAL_ORIGIN_POLICY_SHA256
    # Legacy collectors advertise historical acceptance/count/scope assertions and
    # use wall-clock fetch times. Replace every legacy representation before the
    # directory can be returned, rather than exposing contradictory metadata.
    with (destination / 'normalized.jsonl.gz').open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as packed:
            with output.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    packed.write(block)
    manifest = {**receipt, 'schemaVersion': 'offmenu-historical-candidate/1',
                'inputFiles': [{'path': name, 'bytes': size, 'sha256': digest}
                               for name, size, digest in entry.inputs],
                'scope': 'Only the pinned input bundle and implemented source projection; companion completeness is unassessed',
                'counts': {'normalized': len(seen), 'accepted': None},
                'selectedScopeComplete': False, 'countryCoverageComplete': False}
    (destination / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True) + '\n')
    (destination / 'execution-receipt.json').write_text(json.dumps(receipt, sort_keys=True) + '\n')
    if sum(p.stat().st_size for p in destination.iterdir()) > MAX_OUTPUT:
        raise ValueError('combined-output-limit-exceeded')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        raise SystemExit(2)
