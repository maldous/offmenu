#!/usr/bin/env python3
"""Prepare a NEW EMPTY local app-schema template; never open or migrate live data."""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'docs/schema/household-schema-preparation-plan-v1.json'


def prepare(output_dir=None):
    plan = json.loads(PLAN.read_text())
    scripts = []
    for entry in plan['ordered_sql']:
        path = ROOT / entry['path']
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != entry['sha256']:
            raise ValueError('Reviewed schema digest mismatch; re-review the preparation plan')
        scripts.append(content.decode('utf-8'))
    # Never accept an existing DB path. An output directory must be newly created.
    destination = None
    if output_dir is not None:
        destination = Path(output_dir)
        destination.mkdir(mode=0o700, parents=False, exist_ok=False)
    db_path = destination / 'household-empty-template.sqlite3' if destination else ':memory:'
    db = sqlite3.connect(str(db_path))
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.executescript('BEGIN IMMEDIATE;\n' + '\n'.join(scripts) + '\nCOMMIT;')
        if db.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Foreign-key verification failed')
        if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise ValueError('Integrity verification failed')
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        nonempty = []
        for table in tables:
            # All identifiers come from reviewed schema, not request text.
            count = db.execute('SELECT COUNT(*) FROM "' + table.replace('"','""') + '"').fetchone()[0]
            if count and table not in {'stock_units','household_schema_versions'}:
                nonempty.append(table)
        if nonempty:
            raise ValueError('Empty-template guarantee failed')
        report = {
            'schema': 'offmenu-household-schema-readiness/1',
            'source_baseline': plan['source_baseline'],
            'schema_status': 'schema_prepared_app_wiring_pending',
            'prepared_schema_version': 'offmenu-household-domain/1',
            'security_schema_version': 'offmenu-byoc-security/1',
            'domain_table_count': len([x for x in tables if x.startswith(('household_','stock_')) and x != 'household_schema_versions']),
            'private_rows': 0,
            'external_sources_required': False,
            'private_data_copied': False,
            'credentials_loaded': False,
            'existing_database_opened': False,
            'deployment_performed': False,
            'application_wiring_verified': False,
            'foreign_key_check': 'passed',
            'integrity_check': 'passed',
            'artifact_written': destination is not None,
            'sql_sha256': [x['sha256'] for x in plan['ordered_sql']],
        }
        if destination:
            (destination / 'schema-readiness.json').write_text(json.dumps(report, indent=2)+'\n')
        return report
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', help='Optional NEW local directory under an existing parent; default verifies only in memory')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.output_dir), indent=2))
    except Exception:
        # No exception, SQL, path, input, key or payload values in the public receipt.
        print(json.dumps({'schema':'offmenu-household-schema-readiness/1','schema_status':'preparation_failed','deployment_performed':False,'existing_database_opened':False,'action':'Inspect reviewed local sources/output-directory availability; no live database was opened'}))
        return 1
    return 0

if __name__ == '__main__': sys.exit(main())
