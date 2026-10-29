"""Preserve research source applicability without assuming worldwide coverage."""
from pathlib import Path
import json

root = Path(__file__).resolve().parents[2]
g = json.loads((root / 'docs/research/OffMenu_Global_Data_Source_Register.json').read_text())
e = json.loads((root / 'docs/research/OffMenu_Enrichment_Source_Register_249.json').read_text())
links = set()

def walk(value, country):
    if isinstance(value, dict):
        if value.get('source_id'):
            links.add(('discovery:' + value['source_id'], country))
        for child in value.values():
            walk(child, country)
    elif isinstance(value, list):
        for child in value:
            walk(child, country)

for country in g['countries']:
    walk(country, country['code'])
walk(g['global_providers'], '')
for source in e['source_catalog']:
    for context in source.get('contexts', []):
        if context.get('iso2'):
            links.add((source['source_id'], context['iso2']))
        elif context.get('scope') == 'global':
            links.add((source['source_id'], ''))

def q(value):
    return "'" + value.replace("'", "''") + "'"

sql = ["CREATE TABLE IF NOT EXISTS catalogue_source_countries(source_id TEXT NOT NULL,country TEXT NOT NULL,PRIMARY KEY(source_id,country));",
       "CREATE INDEX IF NOT EXISTS catalogue_source_country ON catalogue_source_countries(country,source_id);"]
sql += ['INSERT OR IGNORE INTO catalogue_source_countries(source_id,country) VALUES(' + q(source) + ',' + q(country) + ');' for source, country in sorted(links)]
(root / 'dist/source-territories.sql').write_text('\n'.join(sql))
print(json.dumps({'sourceCountryLinks': len(links)}))
