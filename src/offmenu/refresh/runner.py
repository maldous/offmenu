"""Isolated trusted-adapter worker. The audit guard is not a hostile-code sandbox."""
import importlib.util
import json
from pathlib import Path
import resource
import sys


def deny_network(event, args):
    if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in {
        'os.system', 'os.exec', 'os.posix_spawn', 'os.fork', 'os.forkpty'}:
        raise RuntimeError('offline-adapter-operation-denied')


def pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('duplicate-json-key')
        result[key] = value
    return result


def constant(_):
    raise ValueError('nonfinite-json-number')


def main():
    sys.dont_write_bytecode = True
    resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, 1024 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_FSIZE, (256 * 1024 * 1024, 256 * 1024 * 1024))
    resource.setrlimit(resource.RLIMIT_CPU, (110, 110))
    sys.addaudithook(deny_network)
    if sys.argv[1] == 'fixture':
        # Only a code-selected static entry is accepted, never a module/command.
        # -I omits the source root; add exactly this worker's own package root.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from offmenu.refresh import core, registry
        if len(sys.argv) != 7 or not core.HEX.fullmatch(sys.argv[5]) or sys.argv[6] not in ('0', '1'):
            raise ValueError('invalid-fixture-worker-arguments')
        entry = registry.fixture(sys.argv[2], repin_runtime=sys.argv[6] == '1')
        bundle, destination = core.safe_path(sys.argv[3]), core.safe_path(sys.argv[4])
        if {p.name for p in bundle.iterdir()} != {i['path'] for i in entry.lock['inputs']}:
            raise ValueError('unexpected-bundle-assets')
        assets = registry.render(entry, bundle, sys.argv[5])
        if set(assets) != set(entry.output_files) or sum(len(v) for v in assets.values()) > registry.MAX_OUTPUT:
            raise ValueError('invalid-fixture-output-assets')
        destination.mkdir()
        for name, body in assets.items():
            with (destination / name).open('xb') as stream:
                stream.write(body)
        registry.validate_candidate(destination, entry, sys.argv[5])
        return
    source, destination, acquired = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    if source.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('input-too-large')
    rows = json.loads(source.read_bytes(), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(rows, list):
        raise ValueError('expected-recipe-array')
    # Reject malformed shapes rather than silently claim a successful normalization.
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError('invalid-recipe-shape')
        data = item.get('recipe_data')
        if data is not None and not isinstance(data, dict):
            raise ValueError('invalid-recipe-shape')
        if data:
            for key in ('url', 'title'):
                if data.get(key) is not None and not isinstance(data[key], str):
                    raise ValueError('invalid-recipe-shape')
            if data.get('infobox') is not None and not isinstance(data['infobox'], dict):
                raise ValueError('invalid-recipe-shape')
            lines = data.get('text_lines') or []
            if not isinstance(lines, list):
                raise ValueError('invalid-recipe-shape')
            for line in lines:
                if not isinstance(line, dict) or any(line.get(k) is not None and not isinstance(line[k], str) for k in ('text', 'section', 'line_type')):
                    raise ValueError('invalid-recipe-shape')
    del rows
    adapter = Path(__file__).resolve().parents[3] / 'tools/data-processing/collect_wikibooks.py'
    spec = importlib.util.spec_from_file_location('pinned_wikibooks_adapter', adapter)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    manifest = module.collect(source, destination, fetched_at=acquired)
    counts = manifest['counts']
    if counts['raw'] != sum(counts[k] for k in ('accepted', 'duplicates', 'quarantined', 'excluded')):
        raise ValueError('unreconciled-input-counts')
    import gzip
    seen = set()
    with gzip.open(destination / 'normalized.jsonl.gz', 'rt', encoding='utf-8') as stream:
        for line in stream:
            packet = json.loads(line, object_pairs_hook=pairs, parse_constant=constant)
            if not isinstance(packet, list) or len(packet) != 1:
                raise ValueError('invalid-normalized-packet')
            row = packet[0]
            if (row['schemaVersion'] != '1.0' or row['kind'] != 'recipe' or row['countries'] != []
                    or row['data']['automaticPlanningEligible'] is not False or row['data']['reviewStatus'] != 'unreviewed'
                    or row['provenance']['archiveSha256'] != manifest['archiveSha256']
                    or row['provenance']['fetchedAt'] != acquired
                    or row['provenance']['license'] != manifest['license']
                    or row['id'] in seen):
                raise ValueError('invalid-normalized-record')
            seen.add(row['id'])
    if len(seen) != counts['accepted'] or counts['records'] != counts['accepted']:
        raise ValueError('unreconciled-output-counts')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        # The parent emits an allowlisted error code; never print source content or paths.
        raise SystemExit(2)
