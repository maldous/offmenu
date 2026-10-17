import gzip
import json
import math
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS products(barcode TEXT PRIMARY KEY, name TEXT NOT NULL, brand TEXT, pack_quantity TEXT);
CREATE TABLE IF NOT EXISTS mappings(barcode TEXT PRIMARY KEY REFERENCES products(barcode), ingredient TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inventory(id INTEGER PRIMARY KEY, barcode TEXT NOT NULL REFERENCES products(barcode), quantity REAL NOT NULL CHECK(quantity>=0), unit TEXT NOT NULL CHECK(unit IN ('g','ml','count')), expires TEXT);
CREATE TABLE IF NOT EXISTS recipes(id TEXT PRIMARY KEY, title TEXT NOT NULL, servings REAL NOT NULL CHECK(servings>0), instructions TEXT, source TEXT, license TEXT);
CREATE TABLE IF NOT EXISTS requirements(recipe_id TEXT REFERENCES recipes(id) ON DELETE CASCADE, position INTEGER, ingredient TEXT NOT NULL, quantity REAL CHECK(quantity>=0), unit TEXT CHECK(unit IN ('g','ml','count')), raw TEXT, PRIMARY KEY(recipe_id,position));
CREATE TABLE IF NOT EXISTS observations(id INTEGER PRIMARY KEY, barcode TEXT NOT NULL, retailer TEXT NOT NULL, location TEXT, price REAL NOT NULL CHECK(price>=0), currency TEXT NOT NULL, observed_at TEXT NOT NULL, source TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS observation_barcode ON observations(barcode);
'''


def connect(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript(SCHEMA)
    return db


def normalize(value):
    return ' '.join(str(value).strip().lower().replace('_', ' ').split())


def amount(value, positive=False):
    value = float(value)
    if not math.isfinite(value) or value < 0 or (positive and value == 0):
        raise ValueError('Quantity must be finite and non-negative; servings must be positive')
    return value


@contextmanager
def textfile(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as f:
        yield f


def import_products(db, path, country=None):
    count = 0
    with db, textfile(path) as f:
        for line in f:
            p = json.loads(line)
            if country and country not in (p.get('countries_tags') or []):
                continue
            code = p.get('code')
            if not isinstance(code, str) or not code:
                raise ValueError('Product code must be a non-empty string (preserve leading zeroes)')
            db.execute('INSERT INTO products VALUES(?,?,?,?) ON CONFLICT(barcode) DO UPDATE SET name=excluded.name,brand=excluded.brand,pack_quantity=excluded.pack_quantity',
                       (code, p.get('product_name_en') or p.get('product_name') or code, p.get('brands'), p.get('quantity')))
            count += 1
    return count


def import_recipes(db, path):
    """Import the documented offmenu JSON interchange format, not arbitrary recipe schemas."""
    with textfile(path) as f:
        recipes = json.load(f)
    if not isinstance(recipes, list):
        raise ValueError('Recipes must be a JSON array')
    with db:
        for r in recipes:
            servings = amount(r.get('servings', 1), positive=True)
            if not r.get('source') or not r.get('license'):
                raise ValueError('Every recipe needs source and license provenance')
            db.execute('INSERT INTO recipes VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,servings=excluded.servings,instructions=excluded.instructions,source=excluded.source,license=excluded.license',
                       (str(r['id']), r['title'], servings, json.dumps(r.get('instructions', [])), r['source'], r['license']))
            db.execute('DELETE FROM requirements WHERE recipe_id=?', (str(r['id']),))
            for i, item in enumerate(r['ingredients']):
                ingredient = normalize(item['ingredient'])
                if not ingredient:
                    raise ValueError('Ingredient cannot be empty')
                q = amount(item['quantity']) if item.get('quantity') is not None else None
                db.execute('INSERT INTO requirements VALUES(?,?,?,?,?,?)',
                           (str(r['id']), i, ingredient, q, item.get('unit'), item.get('raw')))
    return len(recipes)


def map_product(db, barcode, ingredient):
    ingredient = normalize(ingredient)
    if not ingredient:
        raise ValueError('Ingredient cannot be empty')
    with db:
        db.execute('INSERT INTO mappings VALUES(?,?) ON CONFLICT(barcode) DO UPDATE SET ingredient=excluded.ingredient', (barcode, ingredient))


def add_inventory(db, barcode, quantity, unit, expires=None):
    with db:
        db.execute('INSERT INTO inventory(barcode,quantity,unit,expires) VALUES(?,?,?,?)', (barcode, amount(quantity), unit, expires))


def meals(db, servings=None, as_of=None):
    from datetime import date
    today = as_of or date.today().isoformat()
    stock = {}
    for row in db.execute('SELECT m.ingredient,i.unit,SUM(i.quantity) quantity FROM inventory i JOIN mappings m USING(barcode) WHERE i.expires IS NULL OR i.expires>=? GROUP BY m.ingredient,i.unit', (today,)):
        stock[(row['ingredient'], row['unit'])] = row['quantity']
    result = []
    for recipe in db.execute('SELECT * FROM recipes'):
        scale = amount(servings, positive=True) / recipe['servings'] if servings is not None else 1
        requirements = db.execute('SELECT * FROM requirements WHERE recipe_id=?', (recipe['id'],)).fetchall()
        totals, unknown = {}, []
        for r in requirements:
            if r['quantity'] is None or r['unit'] is None:
                unknown.append(r['ingredient'])
            else:
                key = (r['ingredient'], r['unit'])
                totals[key] = totals.get(key, 0) + r['quantity'] * scale
        missing = []
        for (ingredient, unit), required in totals.items():
            shortage = max(0, required - stock.get((ingredient, unit), 0))
            if shortage > 1e-9:
                missing.append({'ingredient': ingredient, 'quantity': round(shortage, 6), 'unit': unit})
        status = 'missing' if missing else 'needs_review' if unknown or not requirements else 'ready'
        result.append({'id': recipe['id'], 'title': recipe['title'], 'status': status, 'missing': missing, 'unknown_quantities': unknown})
    return sorted(result, key=lambda r: ({'ready': 0, 'needs_review': 1, 'missing': 2}[r['status']], len(r['missing']), r['title']))


def import_prices(db, path):
    count = 0
    with db, textfile(path) as f:
        for line in f:
            p = json.loads(line)
            if not p.get('product_code'):
                continue
            if not isinstance(p['product_code'], str):
                raise ValueError('Product barcode must be a string')
            db.execute('INSERT INTO observations(barcode,retailer,location,price,currency,observed_at,source) VALUES(?,?,?,?,?,?,?)',
                       (p['product_code'], p.get('retailer') or p.get('location_osm_display_name') or 'Unknown retailer', str(p.get('location_id') or ''), amount(p['price']), p['currency'], p['date'], 'Open Prices'))
            count += 1
    return count
