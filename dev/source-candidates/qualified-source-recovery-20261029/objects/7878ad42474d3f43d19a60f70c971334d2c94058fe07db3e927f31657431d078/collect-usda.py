#!/usr/bin/env python3
"""Lossless, resumable import of a complete FDC CSV archive into a release DB.

No production/user database is accepted. Each table commits atomically; a
changed archive requires a new release directory. Original strings, including
empty and censored cells, are retained. Normalization is a separate projection.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import zipfile
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def save(path, document):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(document, indent=2) + '\n')
    temporary.replace(path)


def collect(archive, directory):
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / 'manifest.json'
    checksum = digest(archive)
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {
        'schemaVersion': 'offmenu-collection/1', 'sourceId': 'usda-files',
        'scope': 'Every CSV table and supporting workbook in the supplied archive',
        'license': 'USDA FoodData Central public domain / CC0',
        'attribution': 'US Department of Agriculture, Agricultural Research Service, FoodData Central',
        'url': 'https://fdc.nal.usda.gov/download-datasets/',
        'archiveSha256': checksum, 'tables': {}, 'status': 'collecting',
        'publication': 'local only; production publication needs a separately verified storage path'}
    if manifest['archiveSha256'] != checksum:
        raise ValueError('Archive changed: use a new release directory')
    db = sqlite3.connect(directory / 'source.sqlite')
    db.execute('PRAGMA journal_mode=WAL')
    csv.field_size_limit(16 * 1024 * 1024)
    with zipfile.ZipFile(archive) as z:
        manifest['members'] = [{'path': i.filename, 'bytes': i.file_size, 'crc32': i.CRC}
                               for i in z.infolist() if not i.is_dir()]
        for member in z.infolist():
            if not member.filename.endswith('.csv'):
                continue
            table = Path(member.filename).stem
            if not re.fullmatch(r'[a-z][a-z_]*', table):
                raise ValueError('Unexpected table: ' + table)
            if table in manifest['tables']:
                count = db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                if count != manifest['tables'][table]['accepted']:
                    raise ValueError('Checkpoint count mismatch: ' + table)
                print(json.dumps({'table': table, 'resumed': True, 'rows': count}), flush=True)
                continue
            with z.open(member) as f:
                reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8-sig', newline=''))
                headers = next(reader)
                if len(set(headers)) != len(headers) or '_ingestion_row' in headers or any(not h or '\x00' in h for h in headers):
                    raise ValueError('Unsupported column identifiers: ' + table)
                with db:
                    db.execute(f'DROP TABLE IF EXISTS "{table}"')
                    db.execute(f'CREATE TABLE "{table}" (_ingestion_row INTEGER PRIMARY KEY, ' +
                               ','.join('"' + h.replace('"', '""') + '" TEXT NOT NULL' for h in headers) + ')')
                    sql = f'INSERT INTO "{table}" VALUES (' + ','.join('?' for _ in range(len(headers) + 1)) + ')'
                    batch, count = [], 0
                    for row in reader:
                        count += 1
                        if len(row) != len(headers):
                            raise ValueError(f'Malformed row {count} in {table}: collection not accepted')
                        batch.append((count, *row))
                        if len(batch) == 2000:
                            db.executemany(sql, batch)
                            batch.clear()
                    db.executemany(sql, batch)
                manifest['tables'][table] = {'raw': count, 'accepted': count, 'duplicates': 0,
                    'quarantined': 0, 'excluded': 0, 'columns': headers,
                    'note': 'All raw rows preserved; semantic identity duplicates are not removed at raw collection'}
                save(manifest_path, manifest)
                print(json.dumps({'table': table, 'rows': count}), flush=True)
        expected = {Path(n).stem for n in z.namelist() if n.endswith('.csv')}
        if set(manifest['tables']) != expected:
            raise ValueError('Not every archive table reconciled')
    manifest['status'] = 'full scope reconciled'
    manifest['rawRows'] = sum(t['raw'] for t in manifest['tables'].values())
    manifest['normalizedRows'] = 0
    manifest['featureExercises'] = []
    save(manifest_path, manifest)
    db.execute('PRAGMA wal_checkpoint(TRUNCATE)')
    db.close()
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('release_directory', type=Path)
    args = parser.parse_args()
    result = collect(args.archive, args.release_directory)
    print(json.dumps({'status': result['status'], 'tables': len(result['tables']), 'rawRows': result['rawRows']}))
