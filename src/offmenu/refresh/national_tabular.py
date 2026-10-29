"""Offline contracts for retained CNF 2015 and FOODfiles 2024 only.

These contracts do not grant rights or admit production bundles. Never extract
archives here: every supplied archive and extracted input requires its own pin.
"""
import csv
import io
import math
import os
from pathlib import Path, PurePosixPath
from .core import RefreshError

from .source_layout import CURRENT_NATIONAL
NATIONAL = CURRENT_NATIONAL
ADAPTERS = {
    'cnf': {'files': ('cnf-2015-csv.zip', 'csv/FOOD NAME.csv',
                     'csv/NUTRIENT NAME.csv', 'csv/NUTRIENT SOURCE.csv',
                     'csv/NUTRIENT AMOUNT.csv'),
            'mode': 'collect', 'function': 'collect', 'dependencies': ()},
    'foodfiles': {'files': ('nz-foodfiles-2024.msi', 'acquisition.json',
                           'nz-extracted/ExcelFilesNamesx',
                           'nz-extracted/UnabridgedCodes',
                           'nz-extracted/UnabridgedDataFT'),
                  'mode': 'source-collect', 'function': 'collect',
                  'dependencies': (NATIONAL,)},
}


def valid_input_name(name):
    """Canonical relative POSIX file names only; no normalization aliases."""
    return (isinstance(name, str) and bool(name) and '\\' not in name
            and '\x00' not in name and not PurePosixPath(name).is_absolute()
            and all(part not in ('', '.', '..') for part in name.split('/'))
            and ':' not in name)


def bundle_files(root, expected=None):
    """Bounded inventory, optionally rejecting undeclared paths immediately."""
    root = Path(root).absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise RefreshError('execution-symlink-rejected')
    if not root.is_dir():
        raise RefreshError('execution-bundle-not-directory')
    allowed = None if expected is None else set(expected)
    prefixes = set()
    if allowed is not None:
        if len(allowed) > 4096 or any(not valid_input_name(n) for n in allowed):
            raise RefreshError('execution-input-name-invalid')
        for name in allowed:
            parts = name.split('/')
            prefixes.update('/'.join(parts[:i]) for i in range(1, len(parts)))
    names, pending, count = set(), [root], 0
    while pending:
        directory = pending.pop()
        empty = True
        with os.scandir(directory) as entries:
            for item in entries:
                empty = False
                count += 1
                path = Path(item.path)
                name = path.relative_to(root).as_posix()
                if count > 4096 or len(path.relative_to(root).parts) > 16:
                    raise RefreshError('execution-bundle-inventory-limit')
                if item.is_symlink():
                    raise RefreshError('execution-symlink-rejected')
                if item.is_file(follow_symlinks=False):
                    if allowed is not None and name not in allowed:
                        raise RefreshError('execution-bundle-set-mismatch')
                    names.add(name)
                elif item.is_dir(follow_symlinks=False):
                    if allowed is not None and name not in prefixes:
                        raise RefreshError('execution-bundle-set-mismatch')
                    pending.append(path)
                else:
                    raise RefreshError('execution-special-file-rejected')
        if empty and directory != root:
            raise RefreshError('execution-unpinned-empty-directory')
    return names


def _table(path, delimiter=',', skip=0, encoding=None):
    raw = path.read_bytes()
    if encoding is None:
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            text = raw.decode('cp1252')
    else:
        text = raw.decode(encoding)
    reader = csv.reader(io.StringIO(text, newline=''), delimiter=delimiter)
    for _ in range(skip):
        next(reader)
    header = next(reader)
    if not header or len(set(header)) != len(header) or any(not x for x in header):
        raise RefreshError('execution-tabular-header-invalid')
    result = []
    for values in reader:
        if len(values) != len(header):
            raise RefreshError('execution-tabular-row-invalid')
        result.append(dict(zip(header, values)))
    return result


def _unique(rows, field):
    result = {}
    for row in rows:
        key = row[field]
        if not key or key in result:
            raise RefreshError('execution-tabular-duplicate-or-empty-id')
        result[key] = row
    return result


def preflight(source, root, module):
    """Fail closed on joins/collisions the immutable historical code may lose.

Runs inside the bounded worker after exact source pins are checked. Neither held
Fineli/Frida nor native-crash NO/FR handlers are invoked or enabled here.
"""
    root = Path(root)
    if source == 'cnf':
        paths = sorted((root / 'csv').glob('*.csv'))
        if len(paths) != 12:
            raise RefreshError('execution-cnf-twelve-tables-required')
        tables = {p.stem: _table(p) for p in paths}
        foods = _unique(tables['FOOD NAME'], 'FoodID')
        definitions = _unique(tables['NUTRIENT NAME'], 'NutrientID')
        sources = _unique(tables['NUTRIENT SOURCE'], 'NutrientSourceID')
        seen, projected = set(), set()
        for row in tables['NUTRIENT AMOUNT']:
            food, component = row['FoodID'], row['NutrientID']
            if food not in foods or row['NutrientSourceID'] not in sources:
                raise RefreshError('execution-cnf-unresolved-join')
            definition = definitions.get(component, {})
            identity = (food, component)
            key = (food, module.MAP.get(definition.get('NutrientCode'), 'cnf:' + component))
            if identity in seen or key in projected:
                raise RefreshError('execution-cnf-observation-collision')
            seen.add(identity); projected.add(key)
            if row['NutrientValue'] and not math.isfinite(float(row['NutrientValue'])):
                raise RefreshError('execution-tabular-nonfinite-value')
    elif source == 'foodfiles':
        # Validate definitions before the legacy dict comprehension can silently
        # overwrite them. The reader itself verifies food IDs, joins, and pairs.
        base = root / 'nz-extracted'
        _unique(_table(base / 'UnabridgedCodes', '~', 1, 'utf-8-sig'), 'Code')
        rows = _table(base / 'UnabridgedDataFT', '~', 1, 'utf-8-sig')
        for row in rows:
            parsed = module.numeric(row['Value'])
            value = parsed.get('value')
            if value is not None and not math.isfinite(value):
                raise RefreshError('execution-tabular-nonfinite-value')
    else:
        raise RefreshError('execution-national-tabular-source-unsupported')


NATIONAL_FAMILIES = frozenset(('cnf', 'foodfiles', 'afcd', 'mext', 'cofid',
                              'germany-bls', 'sweden-food'))


def national_semantic_errors(source_id, row, *, allowed_units=(), basis_units=()):
    """Strict canonical qualification hook, never a source-record filter.

Bind reviewed per-release unit/basis allowlists explicitly via functools.partial.
Unknown/trace values may be valid observations; unknown definitions or source
matrix bases cannot silently establish canonical completion. Diagnostics leave
all original candidate evidence unchanged. This hook cannot admit any source.
"""
    errors = set()
    if source_id not in NATIONAL_FAMILIES:
        return ['national-source-not-supported']
    if not allowed_units or not basis_units:
        errors.add('national-reviewed-unit-contract-missing')
    if not isinstance(row, dict):
        return sorted(errors | {'national-profile-invalid'})
    from .capabilities import RELEASES
    release = next(r for r in RELEASES if r['sourceId'] == source_id)
    provenance = row.get('provenance')
    if not isinstance(provenance, dict) or provenance.get('sourceId') != source_id or provenance.get('releaseId') != release['releaseId']:
        errors.add('national-provenance-release-mismatch')
    if row.get('kind') != 'nutrientProfile' or row.get('schemaVersion') != '1.0':
        errors.add('national-profile-schema-mismatch')
    data = row.get('data')
    if not isinstance(data, dict):
        return sorted(errors | {'national-profile-data-invalid'})
    basis = data.get('basis')
    if not isinstance(basis, dict) or type(basis.get('amount')) not in (int, float) or basis.get('amount') != 100 or basis.get('unit') not in basis_units:
        errors.add('national-profile-basis-unqualified')
    nutrients = data.get('nutrients')
    if not isinstance(nutrients, dict) or not nutrients:
        return sorted(errors | {'national-nutrients-missing'})
    for nutrient in nutrients.values():
        if not isinstance(nutrient, dict):
            errors.add('national-nutrient-invalid'); continue
        if nutrient.get('unit') not in allowed_units or nutrient.get('unit') in ('unknown', '', None):
            errors.add('national-nutrient-unit-unqualified')
        if source_id == 'cnf' and str(nutrient.get('name', '')).startswith('Unresolved CNF nutrient '):
            errors.add('national-nutrient-definition-unresolved')
        override = nutrient.get('basis')
        if override is not None:
            if not isinstance(override, dict) or override.get('amount') != 100 or override.get('unit') not in basis_units or str(override.get('unit', '')).startswith('source-matrix:'):
                errors.add('national-nutrient-basis-unqualified')
        for field in ('value', 'limit'):
            value = nutrient.get(field)
            if value is not None:
                try:
                    finite = type(value) in (int, float) and math.isfinite(value)
                except OverflowError:
                    finite = False
                if not finite:
                    errors.add('national-nutrient-number-invalid')
        if nutrient.get('value') is None and not nutrient.get('qualifier'):
            errors.add('national-unknown-value-qualifier-missing')
        if nutrient.get('qualifier') == 'less-than' and nutrient.get('limit') is None:
            errors.add('national-censored-value-limit-missing')
    return sorted(errors)
