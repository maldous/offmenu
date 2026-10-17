#!/usr/bin/env python3
"""Build bounded public-only D1 import parts from a reconciled collection.

Activation is a final, count-gated statement. Failed partial imports cannot
replace the last accepted release. No account database operations are emitted.
"""
import argparse
import base64
import gzip
import hashlib
import json
import unicodedata
from pathlib import Path


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def build(directory, output):
    manifest = json.loads((directory / 'manifest.json').read_text())
    if manifest['status'] != 'normalized':
        raise ValueError('Only reconciled normalized collections can be published')
    source = manifest['sourceId']
    release = manifest.get('releaseId', directory.name)
    expected = manifest.get('normalizedRows', manifest.get('counts', {}).get('records'))
    files = [directory / p['key'] for p in manifest.get('partitions', [])] or [directory / 'normalized.jsonl.gz']
    output.mkdir(parents=True, exist_ok=True)
    parts, count, part = [], 0, None
    for path in files:
        with gzip.open(path, 'rt', encoding='utf-8') as rows:
            for line in rows:
                for record in json.loads(line):
                    if record['provenance']['visibility'] != 'public' or record['provenance']['sourceId'] != source:
                        raise ValueError('Private or mismatched source record')
                    if part is None or count % 50000 == 0:
                        if part:
                            part.close()
                        name = 'part-' + str(len(parts)).zfill(4) + '.sql'
                        parts.append(name)
                        part = (output / name).open('w')
                        if count == 0:
                            part.write((Path(__file__).parent.parent / 'cloud/corpus-schema.sql').read_text() + '\n')
                    raw = json.dumps(record, ensure_ascii=False, separators=(',', ':')).encode()
                    document = 'gz:' + base64.b64encode(gzip.compress(raw, compresslevel=6, mtime=0)).decode()
                    data = record['data']
                    barcode = next((i['value'] for i in data.get('identifiers', []) if i['system'] == 'barcode'), '')
                    name = data.get('name') or data.get('foodName') or data.get('title') or record['id']
                    search = ''.join(c for c in unicodedata.normalize('NFKD', name.lower()) if not unicodedata.combining(c))
                    values = [source, release, record['id'], record['kind'], barcode, search, document]
                    sql = 'INSERT OR REPLACE INTO corpus_records VALUES(' + ','.join(map(quote, values)) + ');\n'
                    if len(sql.encode()) > 95000:
                        raise ValueError('Record exceeds safe D1 SQL statement size: ' + record['id'])
                    part.write(sql)
                    count += 1
    if part:
        part.close()
    if count != expected:
        raise ValueError('Normalized file count disagrees with manifest')
    summary = {**manifest, 'publication': 'dedicated D1 corpus; activate only after all rows import', 'publishedRecords': count}
    activation = 'activate.sql'
    with (output / activation).open('w') as f:
        f.write('INSERT OR REPLACE INTO corpus_releases VALUES(' + ','.join(map(quote, [source, release, json.dumps(summary, separators=(',', ':'))])) + ');\n')
        f.write('INSERT INTO corpus_active(source_id,release_id) SELECT ' + quote(source) + ',' + quote(release) +
                ' WHERE (SELECT COUNT(*) FROM corpus_records WHERE source_id=' + quote(source) + ' AND release_id=' + quote(release) +
                ')=' + str(count) + ' ON CONFLICT(source_id) DO UPDATE SET release_id=excluded.release_id;\n')
    parts.append(activation)
    result = {'sourceId': source, 'releaseId': release, 'records': count, 'parts': []}
    for name in parts:
        p = output / name
        h = hashlib.md5()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
                h.update(block)
        result['parts'].append({'file': name, 'bytes': p.stat().st_size, 'etag': h.hexdigest(), 'status': 'pending'})
    (output / 'upload-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'source': source, 'records': count, 'parts': len(parts), 'bytes': sum(p['bytes'] for p in result['parts'])}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('release_directory', type=Path)
    p.add_argument('output_directory', type=Path)
    args = p.parse_args()
    build(args.release_directory, args.output_directory)
