"""Read-only barcode bridges; private household domains are application-managed.

Existing source stores are never modified or copied wholesale. References and
observed schema/count/index metadata live in private local additive staging.
Household sources are never fetched or imported by this external-ingestion path.
Existing private staging rows remain untouched; application schemas are separate.
"""
from __future__ import annotations
import csv
import gzip
import hashlib
import json
import os
import re
from pathlib import Path
import sqlite3
import stat
from urllib.parse import quote
from ingest_api import APP_MANAGED_DOMAINS, BudgetExceeded, SourceChanged, source_key

CODE_COLUMNS = frozenset(('code','barcode','barcode_key','code_key','gtin','ean','upc','normalized_code','normalized_barcode','gtinupc','gtin_upc','ean13','upc12'))
CODE_NAMES = frozenset(re.sub(r'[^a-z0-9]','',name) for name in CODE_COLUMNS)
DATA_TABLES = frozenset(('products','foods','food','records','source_records','source_data','identifiers','code_keys','code_key','barcode_keys','barcode_key','barcodes'))
DATA_NAMES = frozenset(re.sub(r'[^a-z0-9]','',name) for name in DATA_TABLES)


def _regular(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if stat.S_ISLNK(part.lstat().st_mode):
            raise ValueError('symlink_source_refused')
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('source_not_regular')
    return path


def _fingerprint(path):
    st = path.stat()
    result=[st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns]
    wal=Path(str(path)+'-wal')
    if wal.exists():
        _regular(wal)
        ws=wal.stat()
        result.extend((ws.st_dev,ws.st_ino,ws.st_size,ws.st_mtime_ns))
    return tuple(result)


def _identifier(value):
    return '"' + value.replace('"','""') + '"'


def inspect_existing(source, context):
    """Pin recognized retained DB read-only; observe actual counts, never trust hints."""
    path = _regular(source['path'])
    before = _fingerprint(path)
    # mode=ro refuses creation and writing; no immutable=1 (which could ignore WAL).
    uri = 'file:' + quote(str(path), safe='/') + '?mode=ro'
    db = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('PRAGMA trusted_schema=OFF')
        def budget():
            try:
                context.check_budget()
                return 1 if context.cancelled.is_set() else 0
            except BudgetExceeded:
                return 1
        db.set_progress_handler(budget, 100000)
        db.execute('BEGIN')
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        meta = source.get('metadata') or {}
        explicit = meta.get('table') or source.get('table')
        if explicit and explicit not in tables:
            raise ValueError('declared_table_missing')
        selected = []
        provider = str(source.get('provider','')).lower()
        for table in tables:
            if explicit and table != explicit:
                continue
            cols = list(db.execute('PRAGMA table_info(' + _identifier(table) + ')'))
            names = [r[1] for r in cols]
            keycols = [n for n in names if re.sub(r'[^a-z0-9]','',n.lower()) in CODE_NAMES]
            declared = meta.get('code_column') or source.get('code_column')
            if declared:
                if declared not in names:
                    raise ValueError('declared_code_column_missing')
                keycols = [declared]
            # Rich OFF/USDA provider stores may key records by FDC ID and carry
            # barcode in JSON. Keep a source reference, not an invented code index.
            if re.sub(r'[^a-z0-9]','',table.lower()) not in DATA_NAMES and not explicit:
                continue
            if not keycols and not (provider in ('off','openfoodfacts','open_food_facts','open-food-facts','usda','fdc','usda_fdc') and re.sub(r'[^a-z0-9]','',table.lower()) in DATA_NAMES):
                continue
            context.check_budget()
            count = db.execute('SELECT COUNT(*) FROM ' + _identifier(table)).fetchone()[0]
            indexes = []
            for idx in db.execute('PRAGMA index_list(' + _identifier(table) + ')'):
                idxcols = [r[2] for r in db.execute('PRAGMA index_info(' + _identifier(idx[1]) + ')')]
                indexes.append({'columns':idxcols, 'unique':bool(idx[2])})
            pk = [r[1] for r in sorted(cols,key=lambda r:r[5]) if r[5]]
            selected.append({'table':table,'rows':count,'code_columns':keycols,
                             'primary_key':pk,'indexes':indexes})
        binding_status='verified' if selected else 'schema_uncertain'
        db.execute('COMMIT')
        if _fingerprint(path) != before:
            raise SourceChanged('existing_database_changed')
        # Local bridge is intentionally queryable and source-faithful; these
        # paths and schema names never enter a public receipt.
        return {'id':'existing:' + source_key(source), 'kind':'readonly_source_reference',
                'provider':source.get('provider'), 'database_path':str(path),
                'fingerprint':list(before), 'tables':selected, 'available_tables':tables,
                'binding_status':binding_status,
                'read_only':True,'binding':'reusable_reference_not_app_bound'}
    finally:
        db.close()


def _text(source):
    path = _regular(source['path'])
    return gzip.open(path, 'rt', encoding='utf-8-sig', newline='') if path.suffix.lower()=='.gz' else path.open('r',encoding='utf-8-sig',newline='')


def records(source, context):
    fmt = str(source.get('format','')).lower().removesuffix('.gz')
    with _text(source) as stream:
        if fmt in ('jsonl','ndjson','jsonlines'):
            for line in stream:
                context.check_budget()
                if len(line.encode('utf-8')) > int(context.config.get('max_record_bytes', 4194304)):
                    raise ValueError('record_size_cap')
                if line.strip():
                    value=json.loads(line)
                    if not isinstance(value,dict):
                        raise ValueError('record_not_object')
                    yield value
        elif fmt in ('csv','tsv'):
            for row in csv.DictReader(stream,delimiter='\t' if fmt=='tsv' else ','):
                context.check_budget()
                yield row
        elif fmt == 'json':
            # Small household/source metadata JSON only; no unbounded bulk load.
            raw=stream.read(4*1024*1024+1)
            if len(raw)>4*1024*1024:
                raise ValueError('json_size_cap_use_streaming_format')
            value=json.loads(raw)
            rows=value if isinstance(value,list) else value.get('records') if isinstance(value,dict) and isinstance(value.get('records'),list) else [value]
            for row in rows:
                context.check_budget()
                if not isinstance(row,dict):
                    raise ValueError('record_not_object')
                yield row
        else:
            raise ValueError('unsupported_record_format')


def run_domain(domain, sources, context):
    if domain not in ('barcodes','user_profiles','inventory'):
        raise ValueError('unsupported_domain')
    totals=dict(read=0,written=0,unchanged=0,errors=0,skipped=0)
    if domain in APP_MANAGED_DOMAINS:
        # Defense in depth for direct callers: application data is runtime-owned,
        # not a source to fetch/import, even with legacy household scope flags.
        return {'domain': domain, 'status': 'schema_only', 'scope': 'app_managed',
                'disposition': 'schema_only', 'reason': None, **totals,
                'reused_rows': 0, 'reused_stores': 0, 'sources': []}
    results=[]
    reused_rows=0
    imported=reused=0
    private=domain in ('user_profiles','inventory')
    reused_providers=set()
    ordered=list(sources) if private else sorted(sources,key=lambda x:not (x.get('existing_store') or x.get('format')=='sqlite'))
    for source in ordered:
        try:
            context.check_budget()
            meta=source.get('metadata') or {}
            if source.get('incomplete') or source.get('disposition') in ('historical-demo','documentation','duplicate','excluded','metadata-only','incomplete-hold','skip','restricted','unclassified'):
                totals['skipped']+=1
                results.append({'source_key':source_key(source),'status':'skipped','reason':'catalog_skip',**{k:(1 if k=='skipped' else 0) for k in totals}})
                continue
            if private and not (meta.get('user_supplied') is True and meta.get('household_scope') is True):
                results.append({'source_key':source_key(source),'status':'skipped','reason':'awaiting_user_input',**dict.fromkeys(totals,0)})
                totals['skipped']+=1
                continue
            if not private and source.get('restricted'):
                totals['skipped']+=1
                results.append({'source_key':source_key(source),'status':'skipped','reason':'restricted_input',**dict.fromkeys(totals,0)})
                continue
            provider=str(source.get('provider','')).lower()
            if not private and provider and provider in reused_providers and not (source.get('existing_store') or source.get('format')=='sqlite'):
                totals['skipped']+=1
                results.append({'source_key':source_key(source),'status':'reused','reason':'existing_binding_reused',**{k:(1 if k=='skipped' else 0) for k in totals}})
                continue
            if source.get('existing_store') or source.get('format')=='sqlite':
                if private:
                    raise ValueError('private_existing_database_requires_explicit_adapter')
                reference=inspect_existing(source,context)
                refsource=dict(source,loaded=False,restricted=False,disposition='reuse_reference',reference_only=True)
                # SQLite WAL may change while the main DB's mtime does not.
                snapshot=hashlib.sha256(json.dumps(reference,sort_keys=True).encode()).hexdigest()
                refsource['id']=str(source.get('id') or source_key(source))+':reference:'+snapshot
                result=context.ingest(refsource,[reference])
                result['reference_rows_written']=result.get('written',0)
                for counter in ('read','written','unchanged'):
                    result[counter]=0
                result['reused_stores']=1 if result.get('status')=='complete' and not result.get('errors') else 0
                result['disposition']='reused'
                if reference['binding_status']=='schema_uncertain':
                    result['reason']='schema_uncertain'
                result['reused_rows']=sum(t['rows'] for t in reference['tables'])
                reused_rows+=result['reused_rows']
                reused+=result['reused_stores']
                if result['reused_stores'] and reference['tables']:
                    reused_providers.add(provider)
            else:
                # For private household scope only, privacy classification is
                # not a license restriction. Engine supplies a private-only DB.
                selected=dict(source,restricted=False) if private else source
                result=context.ingest(selected,records(selected,context))
                result['disposition']='imported'
                imported+=1
            for key in totals:
                totals[key]+=int(result.get(key,0))
            results.append(result)
        except BudgetExceeded:
            raise
        except Exception as exc:
            context.report_error(source,exc)
            totals['errors']+=1
            results.append({'source_key':source_key(source),'status':'failed','error_class':type(exc).__name__,**{k:(1 if k=='errors' else 0) for k in totals}})
    status='partial' if any(r.get('status')=='partial' for r in results) else 'partial' if totals['errors'] and (imported or reused) else 'failed' if totals['errors'] else 'reused' if reused and not imported else 'imported' if imported else 'schema_only' if private else 'unavailable'
    return {'domain':domain,'status':status,'disposition':status,'reason':'awaiting_user_input' if private and not imported else 'no_recognized_sources' if not sources and not private else None,
            **totals,'reused_rows':reused_rows,'reused_stores':reused,'sources':results}
