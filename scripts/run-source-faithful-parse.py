#!/usr/bin/env python3
"""Bounded resume-safe HTML recipe/menu parser for approved local receipts.

This runner intentionally processes only explicit known source contracts. It
never downloads sources, follows archive members, bypasses custody holds, or
claims comprehensive retained-original coverage.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('source_faithful_parse', ROOT / 'offmenu/refresh/source_faithful_parse.py')
PARSER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PARSER)
BASE = Path('/home/user/src/offmenu-data/originals')
DEFAULT_OUT = Path('/home/user/src/offmenu-data/parsed-source-faithful-20261020')
DEFAULT_LOCK = Path('/home/user/src/offmenu-data/owner-collection-runtime/collection/fixed-selection.lock')


def _queue() -> list[dict]:
    queue = []
    receipt_path = BASE / 'owner-03-remaining13-recipes-20261018/AU/acquisition-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    for entry in receipt['files']:
        queue.append({'path': Path(entry['path']), 'kind': 'recipe', 'sourceId': 'AU-EATFORHEALTH',
            'country': 'AU', 'language': 'en-AU', 'recordId': Path(entry['path']).stem,
            'source': {'sourceURL': entry.get('sourceURL'), 'citationUrl': entry.get('sourceURL'),
                'release': entry.get('release'), 'originalSHA256': entry.get('sha256'),
                'attribution': entry.get('attribution'),
                'licenseStatus': 'receipt-retained; source-specific rights remain under review'}})
    for dirname, source_id, adapter in [('MF-CALMOS-MENU', 'MF-CALMOS', 'calmos-menu-v1'),
                                       ('MF-OCEAN82-MENU', 'MF-OCEAN82', 'ocean82-menu-v1')]:
        directory = BASE / 'country-source-copy-20261018/owner-06/refill1050' / dirname
        receipt = json.loads((directory / 'receipt.json').read_text(encoding='utf-8'))
        queue.append({'path': directory / 'original.html', 'kind': 'menu', 'sourceId': source_id,
            'country': 'MF', 'language': 'fr', 'recordId': 'original',
            'source': {'adapter': adapter, 'sourceURL': receipt.get('url'),
                'citationUrl': receipt.get('citation'), 'release': receipt.get('release'),
                'originalSHA256': receipt.get('sha256'), 'venue': receipt.get('publisher'),
                'attribution': receipt.get('publisher'),
                'licenseStatus': 'unverified; retained private reference only'}})
    return queue


def _atomic(path: Path, blob: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != blob:
            raise PARSER.ParseError('checkpoint-conflict')
        return
    tmp = path.with_name('.' + path.name + '.pending')
    with tmp.open('xb') as stream:
        stream.write(blob); stream.flush(); os.fsync(stream.fileno())
    os.link(tmp, path); tmp.unlink()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, default=DEFAULT_OUT)
    ap.add_argument('--lock', type=Path, default=DEFAULT_LOCK)
    ap.add_argument('--workers', type=int, default=1, help='HTML parsing is light; default 1 avoids competing writes')
    args = ap.parse_args()
    if args.workers != 1:
        ap.error('this run uses one writer; use separate independent output roots for parallel work')
    args.output.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(args.lock, os.O_RDWR)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('writer-lease-busy', file=sys.stderr); return 75
        result_path = args.output / ('run-manifest-' + PARSER.PARSER_VERSION.replace('/', '-') + '.json')
        if result_path.exists():
            existing = json.loads(result_path.read_text(encoding='utf-8'))
            if existing.get('parserVersion') == PARSER.PARSER_VERSION and existing.get('status') == 'complete':
                print(json.dumps(existing['counts'], sort_keys=True)); return 0
        assets = []
        queue = _queue()
        for index, item in enumerate(queue, 1):
            asset_key = hashlib.sha256(PARSER.canonical({'path': str(item['path']), 'sourceId': item['sourceId'], 'recordId': item['recordId'], 'parserVersion': PARSER.PARSER_VERSION, 'dictionaryVersion': PARSER.DICTIONARY_VERSION, 'mappingVersion': PARSER.MAPPING_VERSION})).hexdigest()
            checkpoint = args.output / 'assets' / (asset_key + '.json')
            if checkpoint.exists():
                prior = json.loads(checkpoint.read_text(encoding='utf-8'))
                if prior.get('parserVersion') == PARSER.PARSER_VERSION and prior.get('inputSHA256'):
                    assets.append(prior); print(json.dumps({'progress':index,'total':len(queue),'status':'reused','sourceId':item['sourceId']}),flush=True); continue
            try:
                manifest = PARSER.run_html_asset(input_path=item['path'], output_root=args.output,
                    source=item['source'], source_id=item['sourceId'], kind=item['kind'],
                    country=item['country'], language=item['language'],
                    attribution=item['source'].get('attribution'), source_record_id=item['recordId'])
                row = {'status':'complete','sourceId':item['sourceId'],'sourceRecordId':item['recordId'],
                    'country':item['country'],'kind':item['kind'],'inputPath':str(item['path']),
                    'inputSHA256':manifest['inputSHA256'],'acceptedRecords':manifest['acceptedRecords'],
                    'rejectedRecords':manifest['rejectedRecords'],'manifestPath':str(args.output / ('recipes' if item['kind']=='recipe' else 'menuItems') / item['sourceId'] / manifest['runKey'] / 'manifest.json'),
                    'parserVersion':PARSER.PARSER_VERSION,'exitState':'success'}
            except Exception as exc:
                row = {'status':'failed','sourceId':item['sourceId'],'sourceRecordId':item['recordId'],
                    'country':item['country'],'kind':item['kind'],'inputPath':str(item['path']),
                    'inputSHA256':None,'acceptedRecords':0,'rejectedRecords':1,
                    'parserVersion':PARSER.PARSER_VERSION,'exitState':'error','errorCode':str(exc)}
            _atomic(checkpoint, PARSER.canonical(row)); assets.append(row)
            print(json.dumps({'progress':index,'total':len(queue),'status':row['status'],'sourceId':row['sourceId'],'accepted':row['acceptedRecords'],'rejected':row['rejectedRecords']},ensure_ascii=False),flush=True)
        counts = {'assetsQueued':len(queue),'assetsComplete':sum(x['status']=='complete' for x in assets),
            'assetsFailed':sum(x['status']!='complete' for x in assets),
            'recordsAccepted':sum(x['acceptedRecords'] for x in assets),
            'recipes':sum(x['acceptedRecords'] for x in assets if x['kind']=='recipe' and x['status']=='complete'),
            'menuItems':sum(x['acceptedRecords'] for x in assets if x['kind']=='menu' and x['status']=='complete')}
        run = {'schemaVersion':'offmenu-source-parse-run/1','status':'complete' if not counts['assetsFailed'] else 'complete-with-errors',
            'parserVersion':PARSER.PARSER_VERSION,'dictionaryVersion':PARSER.DICTIONARY_VERSION,
            'recipeTemplateVersion':PARSER.RECIPE_TEMPLATE_VERSION,'menuTemplateVersion':PARSER.MENU_TEMPLATE_VERSION,
            'mappingVersion':PARSER.MAPPING_VERSION,'networkRequests':0,'sourceCoverageComplete':False,
            'normalizationPerformed':False,'translationPerformed':False,'counts':counts,'assets':assets}
        _atomic(result_path, PARSER.canonical(run))
        pointer = {'schemaVersion':'offmenu-source-parse-latest/1','manifest':result_path.name,'parserVersion':PARSER.PARSER_VERSION,'status':run['status']}
        pointer_path = args.output / 'latest-run.json'
        pointer_tmp = pointer_path.with_suffix('.pending')
        pointer_tmp.write_bytes(PARSER.canonical(pointer)); os.replace(pointer_tmp, pointer_path)
        print(json.dumps(counts,sort_keys=True)); return 0 if not counts['assetsFailed'] else 2
    finally:
        try: fcntl.flock(lock_fd, fcntl.LOCK_UN)
        finally: os.close(lock_fd)


if __name__ == '__main__':
    raise SystemExit(main())
