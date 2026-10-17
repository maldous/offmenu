"""Bounded, local-only TBCA identity audit. Does not admit or export records.

The retained statistical index contains identities, not nutrient observations.
Unknown components, units and portion/100g bases must remain unknown. This
module never follows detail links and has no network or corpus write path.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse

SNAPSHOT = Path('/home/user/src/offmenu-data/source-access-20261013/8e4df41bbcc357bfe69bef73.html')
EXPECTED_SHA256 = '22e29f1fae3c4c9a13e61c27308a177de2edac93661807af818b2232ce158ace'
EXPECTED_HEADERS = ['Código', 'Nome', 'Nome Científico', 'Grupo', 'Marca']
FORM_WORDS = {'cru', 'crua', 'cozido', 'cozida', 'drenado', 'drenada',
              'seco', 'seca', 'congelado', 'congelada', 'integral',
              'industrializado', 'industrializada', 'preparado', 'preparada'}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class IndexParser(HTMLParser):
    """Extract a single expected TBCA table, retaining text and opaque links."""
    def __init__(self, limit: int):
        super().__init__(convert_charrefs=True)
        self.limit = limit
        self.table_depth = 0
        self.tables = 0
        self.row = None
        self.cell = None
        self.headers = []
        self.records = []
        self.dropped = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.tables += 1
            self.table_depth += 1
        if not self.table_depth:
            return
        if tag == 'tr':
            self.row = []
        elif tag in {'th', 'td'} and self.row is not None:
            self.cell = {'kind': tag, 'text': [], 'hrefs': []}
        elif tag == 'a' and self.cell is not None:
            self.cell['hrefs'].extend(v for k, v in attrs if k == 'href')

    def handle_data(self, data):
        if self.cell is not None:
            self.cell['text'].append(data)

    def handle_endtag(self, tag):
        if tag in {'th', 'td'} and self.cell is not None:
            self.cell['text'] = ''.join(self.cell['text']).strip()
            self.row.append(self.cell)
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            if self.row and self.row[0]['kind'] == 'th':
                self.headers = [c['text'] for c in self.row]
            elif self.row:
                if len(self.records) < self.limit:
                    self.records.append(self.row)
                else:
                    self.dropped += 1
            self.row = None
        elif tag == 'table':
            self.table_depth -= 1


def read_index(path: Path = SNAPSHOT, expected_sha256: str = EXPECTED_SHA256,
               limit: int = 100) -> tuple[list, dict]:
    if not 1 <= limit <= 1000:
        raise ValueError('representative record limit must be 1..1000')
    if path.stat().st_size > 512 * 1024:
        raise ValueError('bounded local index exceeds 512 KiB')
    raw = path.read_bytes()
    if digest(raw) != expected_sha256:
        raise ValueError('source snapshot digest mismatch')
    metadata_path = path.with_suffix('.json')
    metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
    if metadata.get('landingPageSha256') != expected_sha256:
        raise ValueError('sidecar source digest mismatch')
    if metadata.get('sourceId') != 'discovery:S217':
        raise ValueError('not the registered TBCA source')
    if metadata.get('landingPageTruncated') is not False:
        raise ValueError('source page completeness unknown')
    if urlparse(metadata['finalUrl']).hostname != 'www.tbca.net.br':
        raise ValueError('source URL is not official TBCA')
    parser = IndexParser(limit)
    parser.feed(raw.decode('utf-8', errors='strict'))
    if parser.tables != 1 or parser.headers != EXPECTED_HEADERS:
        raise ValueError('TBCA table schema changed')
    context = {'source_id': metadata['sourceId'], 'source_url': metadata['finalUrl'],
               'snapshot_sha256': digest(raw), 'snapshot_bytes': len(raw),
               'sidecar_sha256': digest(metadata_path.read_bytes()),
               'accessed_utc': metadata['checkedAt'], 'release_id': None,
               'licence': None, 'redistribution_verified': False,
               'rights_decision': metadata['rightsDecision'],
               'retained_path': str(path), 'row_limit': limit,
               'excluded_rows': parser.dropped}
    return parser.records, context


def normalize_identity(cells: list, context: dict, row_number: int) -> dict:
    if len(cells) != 5:
        raise ValueError('expected exactly five identity cells')
    code, name, scientific, group, brand = [c['text'] for c in cells]
    if not re.fullmatch(r'BR[A-Z]\d{4}[A-Z]', code) or not name:
        raise ValueError('missing TBCA identity; never assign name-derived IDs')
    links = {urljoin(context['source_url'], h) for c in cells for h in c['hrefs']}
    if len(links) != 1:
        raise ValueError('conflicting record links')
    record_url = links.pop()
    parsed = urlparse(record_url)
    if (parsed.scheme != 'https' or parsed.hostname != 'www.tbca.net.br'
            or parsed.path != '/base-dados/int_composicao_estatistica.php'
            or not parsed.query):
        raise ValueError('unexpected TBCA detail link')
    # Keep original Portuguese names and every clause; classify only literal
    # standalone form words. No accent folding, translation or synonym merge.
    forms = [word for word in re.findall(r'\w+', name, flags=re.UNICODE)
             if word.casefold() in FORM_WORDS]
    return {'id': 'tbca:statistical-index:' + code,
            'source_record_id': code, 'original_name': name,
            'language': 'pt', 'scientific_name': scientific or None,
            'source_group': group or None, 'source_brand': brand or None,
            'food_form_evidence': forms,
            'original_description_clauses': name.split(','),
            'composition': {'components': None, 'component_ids': None,
                            'units': None, 'quantity_basis': None,
                            'portion_size': None, 'edible_portion': None},
            'missing': ['composition-detail-not-retained', 'portion-or-100g-basis-unknown',
                        'component-ids-and-units-unknown', 'release-unknown', 'rights-unverified'],
            'provenance': {**context, 'original_record_url': record_url,
                           'selector': f'table/tbody/tr[{row_number}]',
                           'row_text_sha256': digest(json.dumps([c['text'] for c in cells],
                                  ensure_ascii=False, separators=(',', ':')).encode()),
                           'row_text_digest_semantics': 'five decoded cell strings, not detail-page bytes'},
            'scope': 'local-restricted-validation', 'corpus_admitted': False,
            'nutritional_equivalence': None, 'batch_origin': None}


def audit(path: Path = SNAPSHOT, limit: int = 100) -> dict:
    rows, context = read_index(path, limit=limit)
    normalized = [normalize_identity(r, context, i + 1) for i, r in enumerate(rows)]
    ids = [r['source_record_id'] for r in normalized]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate TBCA identifiers; no silent deduplication')
    # Aggregate-only output: rights-blocked record strings are never exported.
    projection = json.dumps(normalized, ensure_ascii=False, sort_keys=True,
                            separators=(',', ':')).encode()
    return {'schema': 'offmenu-tbca-local-validation/1', 'context': context,
            'identity_rows_checked': len(normalized), 'composition_rows_checked': 0,
            'records_exported': 0, 'corpus_admitted': False,
            'names_with_diacritics': sum(any(ord(c) > 127 for c in r['original_name'])
                                         for r in normalized),
            'literal_form_counts': dict(sorted(Counter(w.casefold() for r in normalized
                                                   for w in r['food_form_evidence']).items())),
            'names_preserved_exactly': all(r['original_name'] == row[1]['text']
                                          for r, row in zip(normalized, rows)),
            'all_component_ids_units_basis_unknown': all(
                all(v is None for v in r['composition'].values()) for r in normalized),
            'in_memory_projection_sha256': digest(projection),
            'projection_digest_scope': 'diagnostic projection only; not a dataset/release hash',
            'source_unchanged': digest(path.read_bytes()) == context['snapshot_sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', type=Path, default=SNAPSHOT)
    parser.add_argument('--limit', type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(audit(args.snapshot, args.limit), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
