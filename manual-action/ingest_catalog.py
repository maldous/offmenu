#!/usr/bin/env python3
"""Bounded offline discovery of retained OffMenu assets, not an acquisition tool.

All returned paths and the resume cursor are PRIVATE local operational metadata.
Never upload this catalog or use historical counters as current completion proof.
Only selected roots and narrow, trusted report references are explored. Sources
are not executed; symlinks, credentials and private household data are excluded.
Unknown licences are reported, not fabricated or used as a global ingest gate.
"""
from __future__ import annotations
from runner_paths import resolve_layout

import collections
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

from ingest_api import DOMAINS

DEFAULT_ROOT = '/home/user/src/offmenu-data'
# Published source-purpose-audit/REPORT.md names this exact metadata entrypoint.
DEFAULT_PROJECT_REPORTS = (
    '/home/user/Documents/Codex/2026-10-22/worker56-recipe-retention-audit/TERMINAL-HANDOFF.json',
)
# Documentary bindings, not a claim that the files currently exist or are loaded.
KNOWN_COLLECTIONS = {
    'off-2026-10-12-lf': ('open-food-facts', ('barcodes', 'ingredients', 'dietary', 'citations')),
    'usda-2026-04': ('usda', ('barcodes', 'ingredients', 'dietary', 'citations')),
    'prices-2026-10-12': ('open-prices', ('suppliers', 'citations')),
    'afcd-3': ('afcd', ('ingredients', 'dietary', 'citations')),
    'cofid-2021': ('cofid', ('ingredients', 'dietary', 'citations')),
    'germany-bls-4.0': ('bls', ('ingredients', 'dietary', 'citations')),
    'frida-5.5': ('frida', ('ingredients', 'dietary', 'citations')),
    'wikidata-businesses-20261013-native': ('wikidata', ('suppliers', 'citations')),
    'dietary-guidelines-20261013': ('dietary-guidelines', ('dietary', 'citations')),
    'wikibooks-2026-10-13-live': ('wikibooks', ('recipes', 'citations')),
    'cnf-2015': ('cnf', ('ingredients', 'dietary', 'citations')),
    'mext-2023-main': ('mext', ('ingredients', 'dietary', 'citations')),
    'overture-food-places-2026-09-23.1': ('overture', ('suppliers', 'citations')),
    'fineli-20.0': ('fineli', ('recipes', 'ingredients', 'dietary', 'citations')),
    'foodfiles-2024-v01': ('foodfiles', ('ingredients', 'dietary', 'citations')),
    'sweden-food-2026-07-01': ('sweden', ('ingredients', 'dietary', 'citations')),
    'recipe-research-20261013': ('world-recipes', ('recipes', 'ingredients', 'citations')),
    'recipe-wikis-20261013': ('wikibooks', ('recipes', 'ingredients', 'citations')),
    'world-recipes-common-input-20261014': ('world-recipes', ('recipes', 'ingredients', 'citations')),
    'curated-world-recipes-common-20261014': ('world-recipes', ('recipes', 'ingredients', 'citations')),
}
KNOWN_FULL_IDENTIFIER_DB = DEFAULT_ROOT + '/barcode-identifiers-worker57-full-retained-v1/identifiers.sqlite'
KNOWN_IDENTIFIER_HINT = {'barcode_keys': 5242597, 'fdc_keys': 2101279,
                         'source_audits': 9010221, 'assertions': 8908507,
                         'bytes': 19989794816, 'historical_only': True}
FORMATS = {'.jsonl': 'jsonl', '.ndjson': 'jsonl', '.json': 'json', '.jsonld': 'json',
           '.csv': 'csv', '.tsv': 'tsv', '.sqlite': 'sqlite', '.sqlite3': 'sqlite',
           '.db': 'sqlite', '.parquet': 'parquet', '.html': 'html', '.htm': 'html',
           '.pdf': 'pdf', '.txt': 'text', '.md': 'markdown', '.xml': 'xml',
           '.ttl': 'rdf', '.owl': 'rdf', '.rdf': 'rdf', '.pbf': 'osm-pbf',
           '.osm': 'osm-xml', '.zip': 'archive', '.tar': 'archive', '.xlsx': 'xlsx',
           '.xls': 'xls'}
CODE_EXTENSIONS = {'.py', '.pyc', '.js', '.mjs', '.ts', '.tsx', '.jsx', '.sh', '.sql',
                   '.toml', '.yaml', '.yml', '.lock', '.css', '.scss', '.c', '.h'}
SKIP_DIRS = {'.git', '.hg', '.svn', '.ssh', '.aws', '.codex', '.agents',
             'node_modules', '__pycache__', '.venv', 'venv', '.pytest_cache'}
SECRET = re.compile(r'(^|/)(?:\.env(?:\..*)?|credentials?|secrets?|id_rsa|id_ed25519|authorized_keys)(?:/|$)|\.(?:pem|key|p12|pfx|keystore)$', re.I)
KNOWN_HELD_PATH = re.compile(r'parsed-source-faithful-20261020|au-eatforhealth|mf-calmos|mf-ocean82|recipe1m|cooklikehoc|alt[._-]?gourmand|usenet-cookbook|rec[._-]food[._-]recipes|adambouhmad--open-recipe-archive', re.I)
PRIVATE = re.compile(r'(?:^|[/_.-])(?:user[_-]?profiles?|user[_-]?state|household|kitchens?|pantry|personal|private|inventory)(?:[/_.-]|$)', re.I)
META_NAME = re.compile(r'(^|[-_.])(?:manifest|receipt|handoff|inventory|catalog|summary|report|decisions|progress|provenance|custody|evidence|metadata|audit)(?:[-_.]|$)', re.I)
RESTRICTED = re.compile(r'private research|research only|local custody only|noncommercial|non-commercial|no derivatives|rights[- ]unresolved|licen[cs]e unverified|not (?:for )?redistribut', re.I)
PATH_KEYS = {'path', 'localpath', 'originalpath', 'retainedpath', 'sourcepath', 'inputpath',
             'databasepath', 'dbpath', 'storepath', 'nativedatabase', 'nativeconfigpath',
             'manifestpath', 'receiptpath', 'inventorypath', 'reportpath', 'directory',
             'root', 'research', 'wikioriginals', 'normalized', 'curated', 'filename',
             'custodypath', 'actualpath', 'expectedpath', 'normalizedpath', 'parsedpath',
             'cacheroot', 'dataroot', 'originalroot', 'inventoryfile', 'reportfile', 'outputdirectory',
             'file', 'localpaths', 'originals', 'cachepath'}
REF_KEYS = {'sources', 'assets', 'files', 'sourcefiles', 'inputs', 'outputs', 'artifacts',
            'reports', 'manifests', 'inventories', 'localpaths', 'stores', 'databases',
            'paths', 'originalpaths', 'retainedpaths', 'sourcepaths'}
CANON = lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower())


def _opaque(value):
    return hashlib.sha256(str(value).encode('utf-8', 'surrogateescape')).hexdigest()[:24]


def _absolute(path):
    return Path(os.path.abspath(os.fspath(path)))


def _inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _open_dir(path):
    """Descriptor-anchored walk, refusing symlink parents as well as leaves."""
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in _absolute(path).parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _stat(path):
    parent = _open_dir(path.parent)
    try:
        return os.stat(path.name, dir_fd=parent, follow_symlinks=False)
    finally:
        os.close(parent)


def _read_prefix(path, maximum, compressed=False):
    """Small metadata/sample only; no whole large-file digest or archive expansion."""
    parent = _open_dir(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    finally:
        os.close(parent)
    with os.fdopen(fd, 'rb') as f:
        before = os.fstat(f.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError('not_regular_file')
        if compressed:
            with gzip.GzipFile(fileobj=f) as stream:
                data = stream.read(maximum + 1)
        else:
            data = f.read(maximum + 1)
        after = os.fstat(f.fileno())
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('source_changed')
    return data[:maximum], len(data) > maximum, before


def _format(path):
    name = path.name.lower()
    compression = None
    if name.endswith(('.gz', '.bz2', '.xz', '.zst')):
        compression = name.rsplit('.', 1)[1]
        name = name.rsplit('.', 1)[0]
    return FORMATS.get(Path(name).suffix, 'unknown'), compression


def _provider(raw):
    value = str(raw or '').lower()
    patterns = [('offmenu-identifiers', r'barcode-identifiers'), ('open-food-facts', r'open.?food.?facts|(?:^|[/_.-])off(?:[/_.-]|$)'),
                ('usda', r'usda|fooddata|fdc'), ('open-prices', r'open.?prices|(?:^|/)prices-'),
                ('wikidata', r'wikidata'), ('overture', r'overture'), ('osm', r'openstreetmap|(?:^|[/_.-])osm(?:[/_.-]|$)|planet.*pbf'),
                ('unitools', r'unitools'), ('wikibooks', r'wikibooks|recipe-wikis'),
                ('world-recipes', r'world-recipes|recipe-research|historical.*recipe|based.cooking|howtocook|tacofancy|openrecipe'),
                ('fineli', r'fineli'), ('foodon', r'foodon'), ('qudt', r'qudt|measurement-terminology'),
                ('dietary-guidelines', r'dietary-guidelines')]
    for provider, pattern in patterns:
        if re.search(pattern, value):
            return provider
    for provider in ('afcd', 'ciqual', 'cofid', 'frida', 'cnf', 'mext', 'foodfiles', 'sweden', 'matvaretabellen', 'bls'):
        if re.search(r'(?:^|[/_.-])' + provider + r'(?:[/_.-]|$)', value):
            return provider
    return None


def _domains(provider, path, fields=()):
    name = str(path).lower()
    fields = {CANON(x) for x in fields}
    if PRIVATE.search(name) and not META_NAME.search(path.name):
        if re.search(r'user.?profile|user.?state|household|kitchen', name):
            return ['user_profiles']
        if re.search(r'inventory|pantry', name):
            return ['inventory']
    if provider == 'offmenu-identifiers':
        return ['barcodes', 'citations']
    if provider in {'open-food-facts', 'usda'}:
        return ['barcodes', 'ingredients', 'dietary', 'citations']
    if provider in {'overture', 'osm', 'wikidata', 'open-prices'}:
        return ['suppliers', 'citations']
    if provider in {'world-recipes', 'wikibooks', 'unitools'} or re.search(r'recipe|menuitem|menu-items', name) or fields & {'recipeingredient', 'recipeinstructions', 'recipes', 'directions'} or {'ingredients', 'steps'} <= fields:
        return ['recipes', 'ingredients', 'citations']
    if provider == 'fineli':
        return ['recipes', 'ingredients', 'dietary', 'citations']
    if provider in {'afcd', 'ciqual', 'cofid', 'frida', 'cnf', 'mext', 'foodfiles', 'sweden', 'matvaretabellen', 'bls', 'foodon', 'qudt'} or re.search(r'ingredient|composition|nutrient', name) or fields & {'nutrients', 'nutrientid', 'nutrientname', 'energykcal', 'fooddescription'}:
        return ['ingredients', 'dietary', 'citations']
    if provider == 'dietary-guidelines' or fields & {'allergens', 'dietaryflags', 'nutrition'}:
        return ['dietary', 'citations']
    if fields & {'barcode', 'gtin', 'fdcid', 'productname'}:
        return ['barcodes', 'ingredients', 'dietary', 'citations']
    if fields & {'price', 'supplier', 'organization', 'geometry', 'latitude', 'longitude'}:
        return ['suppliers', 'citations']
    return ['citations']


def _metadata(value):
    """Only structural/provider/custody hints; no record bodies in descriptors."""
    if not isinstance(value, dict):
        return {}
    result = {}
    scalar_keys = {'sourceid': 'source_id', 'provider': 'provider', 'releaseid': 'release',
                   'license': 'license', 'licence': 'license', 'visibility': 'visibility',
                   'status': 'status', 'schema': 'schema', 'schemaversion': 'schema',
                   'publication': 'publication', 'rights': 'rights', 'reuse': 'reuse',
                   'table': 'table', 'codecolumn': 'code_column', 'identifiercolumn': 'code_column',
                   'usersupplied': 'user_supplied', 'householdscope': 'household_scope',
                   'loaded': 'loaded', 'imported': 'loaded', 'restricted': 'restricted',
                   'incomplete': 'incomplete', 'kind': 'kind', 'sourcetype': 'kind', 'sha256': 'recorded_sha256',
                   'sourcesha256': 'recorded_sha256', 'completedat': 'normalization_completed_at'}
    for key, data in value.items():
        target = scalar_keys.get(CANON(key))
        if target and isinstance(data, (str, int, float, bool)) and len(str(data)) <= 2048:
            result[target] = data
    if isinstance(value.get('domains'), list):
        domains = [d for d in value['domains'] if d in DOMAINS]
        if domains:
            result['domains'] = domains
    # Counts describe a report's scope, not an independently verified DB count.
    for key in ('counts', 'normalizedRows'):
        if key in value:
            data = value[key]
            if isinstance(data, dict):
                result['historical_counts'] = {k: v for k, v in data.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
            elif isinstance(data, int):
                result['historical_rows'] = data
    return result


def _references(value, base, inherited=None):
    """Only explicit local-path fields. URLs and narrative text never grant scope."""
    pending = [(value, None, inherited or {})]
    while pending:
        item, parent_key, hints = pending.pop()
        if isinstance(item, dict):
            hints = {**hints, **_metadata(item)}
            for key, child in item.items():
                normalized = CANON(key)
                if isinstance(child, str) and (normalized in PATH_KEYS or parent_key in {'localpaths'}):
                    if not child or '\x00' in child or '://' in child or '\n' in child or len(child) > 4096:
                        continue
                    candidate = Path(child)
                    if not candidate.is_absolute():
                        if normalized not in {'path', 'filename', 'file', 'manifestpath', 'receiptpath', 'inventorypath', 'reportpath'}:
                            continue
                        candidate = base / candidate
                    yield _absolute(candidate), hints
                elif isinstance(child, (dict, list)):
                    pending.append((child, normalized, hints))
        elif isinstance(item, list):
            for child in item:
                if isinstance(child, (dict, list)):
                    pending.append((child, parent_key, hints))
                elif isinstance(child, str) and parent_key in REF_KEYS and child.startswith('/'):
                    yield _absolute(child), hints


def _forbidden(path):
    return bool(SECRET.search(str(path))) or any(p in SKIP_DIRS for p in path.parts)


def _narrow_root(path):
    if str(path) in {'/', '/home', '/home/user', '/home/agent', '/home/user/src', '/home/user/Documents', '/home/user/Downloads', '/home/user/Desktop',
                     '/tmp', '/workspace', '/workspace/scratch', '/etc', '/proc', '/sys', '/dev'}:
        return False
    return len(path.parts) >= 4 and not _forbidden(path)


def _allow_report_ref(path, roots, trusted, allowed):
    if _forbidden(path) or not _narrow_root(path):
        return False
    if any(_inside(path, p) for p in roots):
        return True
    if not trusted:
        return False
    if any(_inside(path, p) for p in allowed):
        return True
    parts = path.parts
    # Project report references may locate retained data outside the default root,
    # but cannot turn into an unrestricted home/system/repository crawl.
    if len(parts) >= 6 and parts[:4] == ('/', 'home', 'user', 'src'):
        return 'offmenu' in parts[4].lower() and any(re.search(r'data|retained|collection|cache|report|audit|receipt', p, re.I) for p in parts[4:])
    if len(parts) >= 6 and parts[:3] == ('/', 'home', 'user') and parts[3].startswith('offmenu-'):
        return any(re.search(r'data|retained|original|collection|cache|report|audit|receipt', p, re.I) for p in parts[4:])
    if len(parts) >= 8 and parts[:5] == ('/', 'home', 'user', 'Documents', 'Codex'):
        return bool(META_NAME.search(path.name)) and path.suffix.lower() in {'.json', '.jsonl', '.csv', '.tsv'}
    return False


def _sample_fields(path, fmt, compression, maximum):
    if fmt not in {'json', 'jsonl', 'csv', 'tsv', 'html', 'text', 'markdown'} or compression not in {None, 'gz'}:
        return [], {}
    data, truncated, _ = _read_prefix(path, maximum, compression == 'gz')
    content = data.decode('utf-8-sig', errors='replace')
    if fmt in {'json', 'jsonl'}:
        try:
            obj = json.loads(content if not truncated and fmt == 'json' else content.splitlines()[0])
        except (ValueError, IndexError):
            return re.findall(r'"([A-Za-z][A-Za-z0-9_@-]{0,60})"\s*:', content)[:100], {}
        if isinstance(obj, list):
            obj = next((x for x in obj if isinstance(x, dict)), {})
        fields = list(obj) if isinstance(obj, dict) else []
        if isinstance(obj, dict) and isinstance(obj.get('data'), dict):
            fields.extend(obj['data'])
        return fields, _metadata(obj)
    if fmt in {'csv', 'tsv'}:
        import csv
        try:
            return next(csv.reader(content.splitlines(), delimiter='\t' if fmt == 'tsv' else ',')), {}
        except (StopIteration, csv.Error):
            return [], {}
    if fmt == 'html' and re.search(r'"@type"\s*:\s*"Recipe"', content, re.I):
        return ['recipeIngredient'], {}
    return [], {}


def discover_sources(options=None):
    """Return all encountered file dispositions, independent errors and a cursor.

    options: roots (default offmenu-data), project_reports (explicit trusted local
    JSON metadata), allowed_report_roots, state_dir (excluded from traversal),
    max_files=250000, max_depth=40, max_scan_seconds=120, max_metadata_bytes=4MiB,
    max_sample_bytes=64KiB, hash_max_bytes=1MiB, resume_cursor (returned dict).
    A resumed call returns its new page. Merge pages by source id; do not declare
    discovery complete until truncated is false. No initial 1000-file ceiling.
    """
    options = dict(options or {})
    layout = resolve_layout(options.get('state_dir', Path(__file__).parent / '.local-results' / 'ingest'))
    roots = [_absolute(x) for x in options.get('roots', [DEFAULT_ROOT])]
    allowed = [_absolute(x) for x in options.get('allowed_report_roots', [])]
    excluded = [_absolute(options['state_dir'])] if options.get('state_dir') else []
    excluded.extend(_absolute(x) for x in options.get('exclude_paths', []))
    if not layout.legacy:
        excluded.extend((layout.runtime, layout.public_staging, layout.normalization, layout.household))
    exclusion_binding = sorted({str(x) for x in excluded})
    max_files = max(1, int(options.get('max_files', 250000)))
    max_depth = max(1, int(options.get('max_depth', 40)))
    deadline = time.monotonic() + max(0.001, float(options.get('max_scan_seconds', 120)))
    metadata_limit = max(256, min(64 * 1024 * 1024, int(options.get('max_metadata_bytes', 4 * 1024 * 1024))))
    sample_limit = max(128, min(1024 * 1024, int(options.get('max_sample_bytes', 65536))))
    hash_limit = max(0, min(8 * 1024 * 1024, int(options.get('hash_max_bytes', 1024 * 1024))))
    cursor = options.get('resume_cursor') or {}
    if cursor and cursor.get('schema') != 'offmenu-catalog-cursor/1':
        raise ValueError('invalid_catalog_cursor')
    if cursor and cursor.get('roots') != [str(x) for x in roots]:
        raise ValueError('catalog_cursor_roots_changed')
    if cursor and not layout.legacy and cursor.get('excluded') != exclusion_binding:
        raise ValueError('catalog_cursor_exclusions_changed')
    queue = collections.deque(cursor.get('pending', []))
    seen = set(cursor.get('seen', []))
    inodes = dict(cursor.get('inodes', {}))
    digests = dict(cursor.get('digests', {}))
    reports_seen = set(cursor.get('reports_seen', []))
    restricted_inodes = dict(cursor.get('restricted_inodes', {}))
    restricted_digests = dict(cursor.get('restricted_digests', {}))
    restriction_updates = dict(cursor.get('restriction_updates', {}))
    sources, errors, root_status, depth_pending = [], [], [], []
    counts = collections.Counter()
    if not cursor:
        for path in roots:
            if not _narrow_root(path):
                root_status.append({'id': _opaque(path), 'path': str(path), 'status': 'refused', 'reason': 'root_too_broad_or_sensitive'})
                continue
            queue.append({'path': str(path), 'depth': 0, 'hints': {}, 'root': str(path)})
        # Prioritize actually present documented qualified/native collections.
        # This is not a guessed existence claim and does not replace the full walk.
        if Path(DEFAULT_ROOT) in roots:
            priority_names = ['curated-world-recipes-common-20261014', 'world-recipes-common-input-20261014',
                              'barcode-identifiers-worker57-full-retained-v1']
            priority_names += [name for name in KNOWN_COLLECTIONS if name not in priority_names]
            for name in reversed(priority_names):
                target = Path(DEFAULT_ROOT) / name
                try:
                    observed = _stat(target)
                except OSError:
                    continue
                if stat.S_ISDIR(observed.st_mode):
                    queue.appendleft({'path': str(target), 'depth': 0, 'hints': {}, 'root': str(target)})
        report_paths = options.get('project_reports', DEFAULT_PROJECT_REPORTS if roots == [Path(DEFAULT_ROOT)] else [])
        for path in report_paths:
            path = _absolute(path)
            if not _forbidden(path):
                queue.appendleft({'path': str(path), 'depth': 0, 'hints': {}, 'root': str(path.parent), 'trusted_report': True})
    def error(path, code, operation='inspect'):
        errors.append({'source_id': _opaque(path), 'path': str(path), 'operation': operation, 'code': code})
        counts['errors'] += 1
    def add(path, **data):
        source = {'id': _opaque(path), 'path': str(path), 'format': 'unknown', 'provider': None,
                  'domains': [], 'license': None, 'custody': 'local_presence_observed',
                  'existing_store': False, 'loaded': False, 'restricted': False,
                  'disposition': 'unclassified', 'reason': 'unknown_scope', **data}
        sources.append(source)
        counts[source['disposition']] += 1
        return source
    def read_manifest(path, trusted, hints):
        key = str(path)
        if key in reports_seen:
            return hints
        reports_seen.add(key)
        try:
            data, truncated, _ = _read_prefix(path, metadata_limit)
            if truncated:
                error(path, 'metadata_size_limit', 'read_metadata')
                return hints
            fmt, _ = _format(path)
            if fmt == 'jsonl':
                obj = [json.loads(line) for line in data.splitlines() if line.strip()]
            elif fmt in {'csv', 'tsv'}:
                import csv
                import io
                obj = list(csv.DictReader(io.StringIO(data.decode('utf-8-sig')), delimiter='\t' if fmt == 'tsv' else ','))
            else:
                obj = json.loads(data)
            hints = {**hints, **_metadata(obj)}
            for target, ref_hints in _references(obj, path.parent, hints):
                if _allow_report_ref(target, roots, trusted, allowed):
                    queue.appendleft({'path': str(target), 'depth': 0, 'hints': ref_hints,
                                  'root': str(target.parent), 'trusted_report': trusted and bool(META_NAME.search(target.name))})
                else:
                    error(target, 'manifest_reference_outside_selected_scope', 'resolve_reference')
            return hints
        except (OSError, ValueError, UnicodeError, RecursionError) as exc:
            error(path, type(exc).__name__, 'read_metadata')
            return hints
    while queue and counts['inspected'] < max_files and time.monotonic() < deadline:
        task = queue.popleft()
        path = _absolute(task['path'])
        key = str(path)
        is_continuation = 'offset' in task
        if key in seen and not is_continuation:
            counts['duplicate_paths'] += 1
            continue
        if not is_continuation:
            seen.add(key)
            counts['inspected'] += 1
        if any(_inside(path, e) for e in excluded):
            add(path, disposition='excluded', reason='own_state_directory')
            continue
        if _forbidden(path):
            add(path, disposition='excluded', reason='credential_or_code_cache_path', restricted=True)
            continue
        try:
            st = _stat(path)
        except FileNotFoundError:
            add(path, disposition='missing', reason='selected_path_not_present', custody='not_present_at_selected_path')
            error(path, 'not_found')
            continue
        except OSError as exc:
            add(path, disposition='unreadable', reason=type(exc).__name__, custody='unverified')
            error(path, type(exc).__name__)
            continue
        if stat.S_ISLNK(st.st_mode):
            add(path, disposition='excluded', reason='symlink_not_followed')
            continue
        if stat.S_ISDIR(st.st_mode):
            if task['depth'] >= max_depth:
                add(path, disposition='deferred', reason='max_depth', metadata={'directory': True})
                counts['depth_limited'] += 1
                depth_pending.append({**task, 'offset': 0, 'directory_identity': [st.st_dev, st.st_ino, st.st_mtime_ns]})
                continue
            hints = dict(task.get('hints', {}))
            if not is_continuation:
                for manifest_name in ('manifest.json', 'collection.json'):
                    manifest = path / manifest_name
                    try:
                        mst = _stat(manifest)
                    except FileNotFoundError:
                        continue
                    except OSError as exc:
                        error(manifest, type(exc).__name__, 'metadata_stat')
                        continue
                    if stat.S_ISREG(mst.st_mode):
                        hints = read_manifest(manifest, False, hints)
            offset = int(task.get('offset', 0))
            signature = [st.st_dev, st.st_ino, st.st_mtime_ns]
            if is_continuation and task.get('directory_identity') != signature:
                offset = 0
                counts['directories_changed'] += 1
            try:
                fd = _open_dir(path)
                try:
                    with os.scandir(fd) as iterator:
                        index, batch, exhausted = 0, [], True
                        for entry in iterator:
                            if index < offset:
                                index += 1
                                continue
                            if len(batch) >= 1024 or time.monotonic() >= deadline:
                                exhausted = False
                                break
                            batch.append({'path': str(path / entry.name), 'depth': task['depth'] + 1,
                                          'hints': hints, 'root': task.get('root', key)})
                            index += 1
                        queue.extend(batch)
                        if not exhausted:
                            queue.append({**task, 'offset': index, 'directory_identity': signature, 'hints': hints})
                finally:
                    os.close(fd)
                if task['depth'] == 0 and not is_continuation:
                    root_status.append({'id': _opaque(path), 'path': key, 'status': 'present'})
            except OSError as exc:
                error(path, type(exc).__name__, 'list_directory')
            continue
        if not stat.S_ISREG(st.st_mode):
            add(path, disposition='excluded', reason='special_file_not_opened')
            continue
        fmt, compression = _format(path)
        hints = dict(task.get('hints', {}))
        meta = bool(task.get('trusted_report') or META_NAME.search(path.name)) and fmt in {'json', 'jsonl', 'csv', 'tsv', 'text', 'markdown'}
        if fmt in {'json', 'jsonl', 'csv', 'tsv'} and meta and not compression:
            hints = read_manifest(path, bool(task.get('trusted_report')), hints)
        provider = _provider(hints.get('provider') or hints.get('source_id')) or _provider(key)
        private = bool(PRIVATE.search(key)) and not meta
        known_restricted = private or bool(KNOWN_HELD_PATH.search(key)) or hints.get('restricted') is True or hints.get('visibility') == 'private' or bool(RESTRICTED.search(' '.join(str(hints.get(x, '')) for x in ('license', 'rights', 'reuse', 'publication'))))
        fields = []
        if not known_restricted and not meta and fmt not in {'sqlite', 'parquet', 'pdf', 'archive', 'osm-pbf', 'osm-xml'}:
            try:
                fields, sampled_hints = _sample_fields(path, fmt, compression, sample_limit)
                # Source row fields are data, not authority to grant household scope,
                # claim a completed load, or widen the intended domain selection.
                for control in ('loaded', 'restricted', 'user_supplied', 'household_scope', 'domains', 'incomplete'):
                    sampled_hints.pop(control, None)
                hints = {**sampled_hints, **hints}
                provider = provider or _provider(hints.get('provider') or hints.get('source_id'))
            except (OSError, ValueError, EOFError, UnicodeError, RecursionError) as exc:
                error(path, type(exc).__name__, 'sample_structure')
        domains = ['citations'] if meta else hints.get('domains') or _domains(provider, path, fields)
        rights_text = ' '.join(str(hints.get(x, '')) for x in ('license', 'rights', 'reuse', 'publication', 'visibility'))
        restricted = known_restricted or hints.get('restricted') is True or bool(RESTRICTED.search(rights_text)) or hints.get('visibility') == 'private'
        incomplete = hints.get('incomplete') is True or str(hints.get('status', '')).lower() in {'partial', 'incomplete', 'downloading'} or bool(re.search(r'\.(?:part|partial|download|tmp)(?:$|/)', key, re.I))
        disposition, reason = 'candidate', 'retained_source_format'
        if path.suffix.lower() in CODE_EXTENSIONS or fmt == 'markdown' and not provider or path.name.lower().startswith(('readme', 'license', 'licence', 'changelog')):
            disposition, reason = 'documentation', 'code_or_documentation_not_dataset'
            domains = ['citations']
        elif meta:
            disposition, reason = 'metadata-only', 'source_manifest_or_receipt'
        elif fmt == 'sqlite':
            disposition, reason = 'existing-store', 'retained_database_readonly_reuse'
        elif fmt == 'unknown':
            disposition, reason = 'unsupported', 'unrecognized_format_retained'
        elif fmt in {'archive', 'xlsx', 'xls', 'xml', 'rdf', 'osm-pbf', 'osm-xml'}:
            disposition, reason = 'adapter-required', 'format_requires_bounded_adapter'
        elif domains == ['citations']:
            disposition, reason = 'unclassified', 'source_scope_unknown_reference_only'
        if restricted:
            disposition, reason = 'restricted', 'known_private_or_reuse_restricted_no_shared_ingest'
        if incomplete:
            disposition, reason = 'incomplete-hold', 'partial_asset_not_complete'
        if 'barcode-identifiers-worker57-selected22-v1' in key:
            disposition, reason = 'historical-demo', 'selected_demo_not_full_retained_store'
        loaded = hints.get('loaded') is True and not incomplete and str(hints.get('status', '')).lower() not in {'failed', 'held', 'pending'}
        source = add(path, format=fmt, compression=compression, provider=provider, domains=domains,
                     provider_basis='manifest_claim' if hints.get('provider') or hints.get('source_id') else 'documented_path_or_structural_hint',
                     license_status='source_claim' if hints.get('license') else 'unknown',
                     kind=hints.get('kind') or ('place' if provider in {'overture', 'osm'} else 'price_observation' if provider == 'open-prices' else 'organization' if provider == 'wikidata' else None),
                     license=hints.get('license'), metadata=hints, fields=fields[:100],
                     existing_store=fmt == 'sqlite', loaded=loaded, restricted=restricted,
                     incomplete=incomplete, disposition=disposition, reason=reason,
                     bytes=st.st_size, mtime_ns=st.st_mtime_ns,
                     identity={'device': st.st_dev, 'inode': st.st_ino, 'size': st.st_size, 'mtime_ns': st.st_mtime_ns})
        if fmt == 'sqlite':
            source['sidecars'] = {}
            for suffix in ('-wal', '-shm', '-journal'):
                sidecar = Path(key + suffix)
                try:
                    side_stat = _stat(sidecar)
                    source['sidecars'][suffix] = {'bytes': side_stat.st_size, 'mtime_ns': side_stat.st_mtime_ns,
                        'inode': side_stat.st_ino, 'regular': stat.S_ISREG(side_stat.st_mode)}
                except FileNotFoundError:
                    source['sidecars'][suffix] = None
                except OSError as exc:
                    source['sidecars'][suffix] = {'unreadable': type(exc).__name__}
                    error(sidecar, type(exc).__name__, 'sidecar_stat')
            source['identity']['sidecars'] = source['sidecars']
        if key == KNOWN_FULL_IDENTIFIER_DB:
            source.update(provider='offmenu-identifiers', domains=['barcodes', 'citations'], loaded=True, loaded_basis='historically_loaded_binding_requires_runtime_verification')
            source['metadata']['historical_counts'] = KNOWN_IDENTIFIER_HINT
            source['reason'] = 'documented_full_identifier_store_verify_readonly'
        inode_key = f'{st.st_dev}:{st.st_ino}'
        if restricted:
            restricted_inodes[inode_key] = 'alias_of_known_restricted_source'
            if inode_key in inodes:
                restriction_updates[inodes[inode_key]] = 'alias_of_known_restricted_source'
        elif inode_key in restricted_inodes:
            restriction_updates[source['id']] = restricted_inodes[inode_key]
        if inode_key in inodes:
            source.update(disposition='duplicate', reason='same_file_identity', duplicate_of=inodes[inode_key])
            counts['duplicate_inodes'] += 1
        else:
            inodes[inode_key] = source['id']
        # Byte equality is cheap only for small, nonprivate regular inputs; content
        # duplicates retain source identity/provenance and are not semantic merges.
        if not private and not incomplete and fmt != 'sqlite' and st.st_size <= hash_limit and source['disposition'] not in {'duplicate', 'documentation'}:
            try:
                data, truncated, _ = _read_prefix(path, hash_limit)
                if not truncated:
                    digest = hashlib.sha256(data).hexdigest()
                    source['sha256'] = digest
                    previous = digests.get(digest)
                    if restricted:
                        restricted_digests[digest] = 'byte_alias_of_known_restricted_source'
                        if previous:
                            restriction_updates[previous] = 'byte_alias_of_known_restricted_source'
                    elif digest in restricted_digests:
                        restriction_updates[source['id']] = restricted_digests[digest]
                    if previous:
                        source.update(disposition='duplicate', reason='byte_identical_small_file', duplicate_of=previous)
                        counts['duplicate_bytes'] += 1
                    else:
                        digests[digest] = source['id']
            except (OSError, ValueError) as exc:
                error(path, type(exc).__name__, 'small_file_digest')
        try:
            current = _stat(path)
            if (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns) != (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns):
                source.update(incomplete=True, disposition='incomplete-hold', reason='source_changed_during_discovery')
                error(path, 'source_changed', 'verify_identity')
        except OSError as exc:
            source.update(incomplete=True, disposition='incomplete-hold', reason='source_changed_during_discovery')
            error(path, type(exc).__name__, 'verify_identity')
    for source in sources:
        if source['id'] in restriction_updates:
            source.update(restricted=True, disposition='restricted', reason=restriction_updates[source['id']])
    queue.extend(depth_pending)
    truncated = bool(queue)
    # Recount final dispositions after byte/inode deduplication.
    for name in {s['disposition'] for s in sources} | {'candidate', 'duplicate'}:
        counts[name] = sum(s['disposition'] == name for s in sources)
    result = {'schema': 'offmenu-retained-source-catalog/1', 'sources': sources, 'errors': errors,
              'counts': dict(counts), 'roots': root_status, 'truncated': truncated,
              'complete': not truncated and not errors and not any(r.get('status') == 'refused' for r in root_status),
              'stop_reason': 'max_depth' if depth_pending else 'scan_budget' if truncated else None,
              'historical_claims': {'recipe_paths': 1378, 'separate_prior_cohort_files': 988,
                  'recipe_publication_records': 25135, 'off_products': 4807217,
                  'usda_products': 2101279, 'overture_files': 16, 'overture_food_places': 12681108,
                  'osm_expected_bytes': 95244184503, 'osm_last_observed_partial_gb': 88.47,
                  'current_presence_or_completion_verified': False},
              'domain_summary': {d: {'files': sum(d in s['domains'] for s in sources),
                                    'candidates': sum(d in s['domains'] and s['disposition'] == 'candidate' for s in sources)} for d in DOMAINS},
              'restriction_updates': [{'id': key, 'reason': value} for key, value in restriction_updates.items()],
              'resume_cursor': None}
    if truncated:
        result['resume_cursor'] = {'schema': 'offmenu-catalog-cursor/1', 'roots': [str(x) for x in roots], 'excluded': exclusion_binding,
                                   'pending': list(queue), 'seen': sorted(seen), 'inodes': inodes,
                                   'digests': digests, 'reports_seen': sorted(reports_seen),
                                   'restricted_inodes': restricted_inodes, 'restricted_digests': restricted_digests,
                                   'restriction_updates': restriction_updates}
    return result
