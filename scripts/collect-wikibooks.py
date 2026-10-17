#!/usr/bin/env python3
"""Normalize every row of the named Wikibooks snapshot, with explicit review.

Only unambiguous metric quantities are interpreted. Unknown yields/units are
retained for manual review; they cannot become automatic planner quantities.
"""
import argparse
import gzip
import hashlib
import io
import json
import re
from pathlib import Path
from datetime import datetime, timezone


def collect(path, output, *, fetched_at=None):
    raw_bytes = path.read_bytes()
    raw = json.loads(raw_bytes)
    output.mkdir(parents=True, exist_ok=True)
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    manifest = {'schemaVersion': 'offmenu-collection/1', 'sourceId': 'wikibooks', 'releaseId': '2024-07-31',
                'archiveSha256': checksum, 'license': 'CC BY-SA 4.0',
                'attribution': 'Wikibooks contributors; dataset Gosse Minnema, July 2024',
                'url': 'https://huggingface.co/datasets/gossminn/wikibooks-cookbook',
                'scope': 'Every recipe row in recipes_parsed.json, 2024-07-31 scrape; not the current live cookbook',
                'counts': {'raw': len(raw), 'accepted': 0, 'duplicates': 0, 'quarantined': 0, 'excluded': 0, 'records': 0},
                'featureExercises': [], 'publication': 'local only', 'status': 'collecting'}
    seen, quarantine = set(), []
    now = fetched_at or datetime.now(timezone.utc).isoformat()
    # Fixed gzip metadata makes pinned offline replay byte-reproducible.
    with (output / 'normalized.jsonl.gz').open('wb') as binary, \
            gzip.GzipFile(filename='', mode='wb', fileobj=binary, mtime=0) as compressed, \
            io.TextIOWrapper(compressed, encoding='utf-8', newline='\n') as out:
        for index, item in enumerate(raw, 1):
            d = item.get('recipe_data') or {}
            url, title = d.get('url'), d.get('title')
            if not url or not url.startswith('https://en.wikibooks.org/wiki/Cookbook:') or not title:
                quarantine.append({'row': index, 'reason': 'missing or unsupported source identity'})
                continue
            if url in seen:
                manifest['counts']['duplicates'] += 1
                continue
            seen.add(url)
            info = d.get('infobox') or {}
            servings = str(info.get('servings') or '')
            yield_value = float(servings) if re.fullmatch(r'\d+(?:\.\d+)?', servings) and float(servings) > 0 else None
            ingredients, directions = [], []
            for line in d.get('text_lines') or []:
                text = line.get('text') or ''
                section = (line.get('section') or '').lower()
                if section == 'ingredients' and line.get('line_type') in ('ul', 'ol'):
                    # Name matching remains a reviewed task; raw phrase is never
                    # silently equated to a prepared-state composition food.
                    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l)\s+(.+)', text, flags=re.I)
                    amount = unit = None
                    name = text
                    if match and not re.search(r'\bor\b|\d\s*[-–—]\s*\d', text, re.I):
                        amount, unit, name = float(match[1]), match[2].lower(), match[3]
                        if unit in ('kg', 'l'):
                            amount *= 1000
                            unit = {'kg': 'g', 'l': 'ml'}[unit]
                    ingredients.append({'name': name, 'amount': amount, 'unit': unit,
                                        'originalText': text, 'optional': bool(re.search(r'\boptional\b', text, re.I)),
                                        'foodMatchStatus': 'unreviewed'})
                elif section in ('procedure', 'preparation', 'directions', 'method', 'instructions'):
                    directions.append(text)
            rid = hashlib.sha256(url.encode()).hexdigest()[:24]
            record = {'schemaVersion': '1.0', 'kind': 'recipe', 'id': 'wikibooks:recipe:' + rid, 'countries': [],
                'provenance': {'sourceId': 'wikibooks', 'recordId': url, 'url': url,
                    'license': manifest['license'], 'attribution': manifest['attribution'], 'visibility': 'public',
                    'fetchedAt': now, 'sourceDate': '2024-07-31', 'releaseId': manifest['releaseId'],
                    'archiveSha256': checksum, 'transform': 'offmenu-wikibooks-full/1',
                    'changes': 'Structured recipe fields; conservative metric interpretation; original text and attribution retained'},
                'data': {'name': title, 'yield': {'value': yield_value, 'unit': 'portion'}, 'ingredients': ingredients,
                    'directions': directions, 'time': info.get('time'), 'category': info.get('category'),
                    'originalTextLines': d.get('text_lines') or [], 'reviewStatus': 'unreviewed',
                    'automaticPlanningEligible': False,
                    'limitations': 'Historical source snapshot; yield, ingredient identity, dietary suitability and cooking method need review'}}
            out.write(json.dumps([record], ensure_ascii=False, separators=(',', ':')) + '\n')
            manifest['counts']['accepted'] += 1
    manifest['counts']['quarantined'] = len(quarantine)
    manifest['counts']['records'] = manifest['counts']['accepted']
    manifest['status'] = 'normalized'
    (output / 'quarantine.json').write_text(json.dumps(quarantine, indent=2) + '\n')
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest['counts']))
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('snapshot', type=Path)
    p.add_argument('output_directory', type=Path)
    a = p.parse_args()
    collect(a.snapshot, a.output_directory)
