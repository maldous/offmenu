"""Private preparation only: immutable selected snapshot; no listener or activation."""
import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

DATABASE = Path('/home/user/src/offmenu-data/runtime/layout-migration/worker56/rich-product-local-projection-20261026/selected-75-profile-extension/relational-index-10300/private-views.sqlite3')
DATABASE_SHA256 = '27472e67235c37f9cd1637886d1f38acfc8596dfba2caa5a88868f2af8c9700e'
MAX_PRODUCTS, MAX_PROFILES, MAX_NUTRIENTS = 8, 4, 32
SELECTED_FIELDS = ('name', 'brand', 'barcode', 'candidateProfiles', 'sourceNutrients', 'provenance')
SOURCE_SCOPE = Path('/home/user/src/offmenu-data/runtime/layout-migration/worker56/rich-product-local-projection-20261026/selected-75-profile-extension/prior10300-display-source-scope/result.json')
SOURCE_SCOPE_SHA256 = 'e40e6b80cc8fcdcc834be3ebe8bcf869ea74654471bea5851cc848be4965e89d'
SOURCE_NOTICES = {
    'off': {'release': '2026-10-12', 'attribution': 'Open Food Facts',
            'retainedDeclaration': 'ODbL / DbCL; retain notices and qualification; images excluded'},
    'usda-files': {'release': '2026-04-30', 'attribution': 'USDA Agricultural Research Service FoodData Central',
                   'retainedDeclaration': 'USDA FoodData Central public domain / CC0 as retained; exact historical lineage only'}
}
CAVEATS = [
    'Private unreviewed source-derived sample; not Gold, English-qualified or canonical.',
    'Observed same-source candidate pairs only; declared nutrition link not recovered; canonical equivalence false.',
    'Basis agreement and original publisher basis not established; source unit notation does not establish conversion.',
    'Unknown, null, empty and not-projected states remain distinct; no zero-fill or new unit conversion.',
    'Competing source variants remain separate; no primary product/profile is selected.',
    'Source language, dates and citations retain source evidence or explicit unknowns; names are not automatically English.'
]


def bounded_count(rows, cap):
    return {'returned': min(len(rows), cap), 'total': len(rows) if len(rows) <= cap else None,
            'totalState': 'exact' if len(rows) <= cap else 'unknown-beyond-bound',
            'observedLowerBound': len(rows)}


class LookupError(ValueError):
    pass


def exact_barcode(value):
    if type(value) is not str or not re.fullmatch(r'[0-9]{1,64}', value, flags=re.ASCII):
        raise LookupError('barcode must be an exact 1..64 digit string')
    return value


def fingerprint(path):
    s = path.stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def unpack(blob):
    if len(blob) > 2048:
        raise LookupError('selected field exceeds bound')
    out, value, shift = [], 0, 0
    for byte in blob:
        value |= (byte & 127) << shift
        if byte & 128:
            shift += 7
            if shift > 63:
                raise LookupError('invalid child reference')
        else:
            out.append(value)
            value, shift = 0, 0
            if len(out) > 128:
                raise LookupError('selected field exceeds bound')
    if shift:
        raise LookupError('incomplete child reference')
    return out


class Lookup:
    """Direct bounded reads authorized for code qualification, not a display grant."""

    def __init__(self):
        self.path = DATABASE
        self.initial_stat = fingerprint(self.path)
        with self.path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != DATABASE_SHA256 or fingerprint(self.path) != self.initial_stat:
            raise LookupError('selected database pin mismatch')
        self.connection = sqlite3.connect(self.path.as_uri() + '?mode=ro&immutable=1', uri=True)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA query_only=ON')
        self.connection.execute('PRAGMA trusted_schema=OFF')
        allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
        self.connection.set_authorizer(lambda op, a, b, db, trigger:
                                       sqlite3.SQLITE_OK if op in allowed else sqlite3.SQLITE_DENY)

    def close(self):
        self.connection.close()

    def _rows(self, sql, parameters=()):
        return self.connection.execute(sql, parameters).fetchall()

    def _node(self, node):
        row = self._rows('SELECT kind,scalar_json,shape_id,children FROM json_node WHERE id=?', (node,))
        if not row:
            raise LookupError('missing selected reference')
        return row[0]

    def _members(self, node):
        row = self._node(node)
        if row['kind'] != 'object':
            raise LookupError('expected selected object')
        shapes = self._rows('SELECT keys_json FROM object_shape WHERE id=?', (row['shape_id'],))
        if not shapes or len(shapes[0][0]) > 8192:
            raise LookupError('invalid selected shape')
        keys, children = json.loads(shapes[0][0]), unpack(row['children'])
        if len(keys) != len(children) or len(keys) != len(set(keys)):
            raise LookupError('invalid selected shape')
        return dict(zip(keys, children))

    def _value(self, node, depth=0):
        self.node_budget -= 1
        if depth > 8 or self.node_budget < 0:
            raise LookupError('selected field exceeds bound')
        row = self._node(node)
        if row['scalar_json'] is not None:
            if len(row['scalar_json'].encode()) > 2048:
                raise LookupError('selected field exceeds bound')
            # Never round decimal source lexemes through a binary float.
            if row['kind'] == 'number':
                return {'decimalLexeme': row['scalar_json']}
            return json.loads(row['scalar_json'])
        if row['kind'] == 'object':
            return {key: self._value(child, depth + 1) for key, child in self._members(node).items()}
        return [self._value(child, depth + 1) for child in unpack(row['children'])]

    def _selected(self, members, key):
        if key not in members:
            return {'state': 'unknown', 'reason': 'source-field-absent'}
        self.node_budget = 256
        try:
            value = self._value(members[key])
            return {'state': 'null', 'value': None} if value is None else {'state': 'source-value', 'value': value}
        except LookupError:
            return {'state': 'unknown', 'reason': 'selected-field-exceeds-prepared-bound'}

    def _occurrence(self, occurrence):
        rows = self._rows('''SELECT o.id,o.kind,o.native_id,o.root_node,o.file_id,o.line_number,o.line_sha256,
            s.source_id,s.release_id,s.record_id,s.archive_sha,s.rights_sha,s.scope_sha,s.store_sha,
            s.qualification_sha,s.pointer_base,s.pointer_tail,s.role,f.sha256 AS input_sha256
            FROM occurrence o JOIN source_record s ON s.occurrence_id=o.id
            JOIN input_file f ON f.id=o.file_id WHERE o.id=?''', (occurrence,))
        if not rows:
            raise LookupError('missing source-local occurrence')
        row = dict(rows[0])
        root = self._members(row.pop('root_node'))
        data = self._members(root['data'])
        provenance = self._members(root['provenance'])
        ref = {key: row[key] for key in row if key not in ('id', 'kind', 'native_id')}
        notice = SOURCE_NOTICES.get(row['source_id'])
        if not notice or row['release_id'] != notice['release']:
            raise LookupError('source outside selected source qualification')
        if row['source_id'] == 'off' and row['qualification_sha'] != '96a192c8d7ec08e4116b9c7b1c8fb77da452a22820656fa43ceef1200c96cfc0':
            raise LookupError('OFF qualification mismatch')
        return {'occurrence': row['id'], 'kind': row['kind'], 'nativeId': row['native_id'],
                'provenance': {'relationalSourceReference': ref,
                               **{key: self._selected(provenance, key) for key in
                                  ('attribution', 'license', 'rights', 'url', 'visibility', 'citationStatus',
                                   'sourceDate', 'fetchedAt')},
                               'sourceLanguage': {key: self._selected(data, key) for key in
                                                  ('nameLanguage', 'sourceLanguageFields')},
                               'sourceUseNotice': notice, 'sourceScopeSha256': SOURCE_SCOPE_SHA256},
                'reviewStatus': 'unreviewed', 'goldAdmitted': False,
                'englishQualification': 'unknown', 'canonicalIdentity': 'unknown'}, data

    def lookup(self, barcode):
        barcode = exact_barcode(barcode)
        if fingerprint(self.path) != self.initial_stat:
            raise LookupError('database changed since qualification')
        deadline, ticks = time.monotonic() + 2, [0]

        def stop():
            ticks[0] += 1
            return ticks[0] > 200 or time.monotonic() > deadline

        self.connection.set_progress_handler(stop, 1000)
        try:
            matches = self._rows('''SELECT DISTINCT o.id FROM identifier i
                JOIN occurrence o ON o.id=i.occurrence_id
                WHERE i.system=? AND i.value_text=? AND o.kind=? ORDER BY o.id LIMIT ?''',
                ('barcode', barcode, 'product', MAX_PRODUCTS + 1))
            products = []
            for match in matches[:MAX_PRODUCTS]:
                product, data = self._occurrence(match['id'])
                product.update({'barcode': barcode, 'name': self._selected(data, 'name'),
                                'brand': self._selected(data, 'brand')})
                pairs = self._rows('''SELECT p.profile_occurrence,q.status,q.declared_link_recovered,
                    q.canonical_equivalence,q.basis_agreement FROM source_candidate_pair p
                    JOIN pair_qualification q ON q.id=p.qualification_id
                    JOIN source_record a ON a.occurrence_id=p.product_occurrence
                    JOIN source_record b ON b.occurrence_id=p.profile_occurrence
                    JOIN occurrence o ON o.id=p.profile_occurrence
                    WHERE p.product_occurrence=? AND o.kind=? AND a.source_id=b.source_id
                    AND a.release_id IS b.release_id AND a.record_id IS b.record_id
                    AND a.archive_sha IS b.archive_sha ORDER BY p.profile_occurrence LIMIT ?''',
                    (match['id'], 'nutrientProfile', MAX_PROFILES + 1))
                profiles = []
                for pair in pairs[:MAX_PROFILES]:
                    profile, _ = self._occurrence(pair['profile_occurrence'])
                    profile['qualification'] = {k: pair[k] for k in pair.keys() if k != 'profile_occurrence'}
                    nutrients = self._rows('''SELECT m.id,m.source_id,m.nutrient_key,n.amount_state,
                        n.decimal_text,n.is_explicit_zero,n.amount_node,n.unit_node,n.basis_node,
                        m.source_id_evidence_node,m.source_name_evidence_node FROM nutrient n
                        JOIN source_metric m ON m.id=n.metric_id WHERE n.occurrence_id=?
                        ORDER BY m.id LIMIT ?''', (pair['profile_occurrence'], MAX_NUTRIENTS + 1))
                    profile['nutrients'] = []
                    for nutrient in nutrients[:MAX_NUTRIENTS]:
                        nodes = {'amountEvidence': nutrient['amount_node'], 'unit': nutrient['unit_node'],
                                 'basis': nutrient['basis_node'], 'sourceMetricId': nutrient['source_id_evidence_node'],
                                 'sourceMetricName': nutrient['source_name_evidence_node']}
                        item = {'metricReference': nutrient['id'], 'sourceId': nutrient['source_id'],
                                'sourceKey': nutrient['nutrient_key'], 'amountState': nutrient['amount_state'],
                                'decimalText': nutrient['decimal_text'], 'explicitZero': bool(nutrient['is_explicit_zero']),
                                'mappingStatus': 'source-local-only', 'reviewStatus': 'unreviewed'}
                        item.update({key: self._selected(nodes, key) for key in nodes})
                        profile['nutrients'].append(item)
                    profile['nutrientsTruncated'] = len(nutrients) > MAX_NUTRIENTS
                    profile['nutrientCounts'] = bounded_count(nutrients, MAX_NUTRIENTS)
                    profiles.append(profile)
                product.update({'candidateProfiles': profiles, 'profilesTruncated': len(pairs) > MAX_PROFILES})
                product['profileCounts'] = bounded_count(pairs, MAX_PROFILES)
                products.append(product)
            result = {'barcode': barcode, 'products': products, 'productsTruncated': len(matches) > MAX_PRODUCTS,
                      'matchStatus': 'source-local-candidates' if products else 'not-found-in-selected-snapshot',
                      'snapshotSha256': DATABASE_SHA256, 'reviewStatus': 'unreviewed', 'goldAdmitted': False,
                      'countryCoverage': 'not-established', 'canonicalEquivalence': False,
                      'productCounts': bounded_count(matches, MAX_PRODUCTS), 'caveats': list(CAVEATS),
                      'bounds': {'products': MAX_PRODUCTS, 'profilesPerProduct': MAX_PROFILES,
                                 'nutrientsPerProfile': MAX_NUTRIENTS, 'responseBytes': 65536}}
            if len(json.dumps(result, ensure_ascii=False).encode()) > 65536:
                raise LookupError('response exceeds prepared bound')
            if fingerprint(self.path) != self.initial_stat:
                raise LookupError('database changed during query')
            return result
        finally:
            self.connection.set_progress_handler(None, 0)

