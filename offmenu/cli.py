import argparse
import json
import sqlite3
from datetime import date
from .core import connect, import_products, import_recipes, import_prices, map_product, add_inventory, meals


def main():
    parser = argparse.ArgumentParser(description='Offline pantry → recipes → shop observations')
    parser.add_argument('--db', default='data/offmenu.sqlite')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    for command in ('import-products', 'import-recipes', 'import-prices'):
        p = sub.add_parser(command)
        p.add_argument('file')
        if command == 'import-products':
            p.add_argument('--country', help='OFF country tag, e.g. en:australia')
    p = sub.add_parser('map')
    p.add_argument('barcode'); p.add_argument('ingredient')
    p = sub.add_parser('add')
    p.add_argument('barcode'); p.add_argument('quantity', type=float)
    p.add_argument('unit', choices=['g', 'ml', 'count'])
    p.add_argument('--expires', type=date.fromisoformat)
    p = sub.add_parser('remove')
    p.add_argument('inventory_id', type=int)
    sub.add_parser('inventory')
    p = sub.add_parser('meals')
    p.add_argument('--servings', type=float)
    p.add_argument('--as-of', type=date.fromisoformat)
    p = sub.add_parser('shops')
    p.add_argument('barcode')
    args = parser.parse_args()
    db = connect(args.db)
    try:
        if args.command == 'init':
            output = {'database': args.db}
        elif args.command == 'import-products':
            output = {'imported': import_products(db, args.file, args.country)}
        elif args.command == 'import-recipes':
            output = {'imported': import_recipes(db, args.file)}
        elif args.command == 'import-prices':
            output = {'imported': import_prices(db, args.file)}
        elif args.command == 'map':
            map_product(db, args.barcode, args.ingredient)
            output = {'mapped': args.barcode, 'ingredient': args.ingredient}
        elif args.command == 'add':
            add_inventory(db, args.barcode, args.quantity, args.unit, args.expires.isoformat() if args.expires else None)
            output = {'added': args.barcode}
        elif args.command == 'remove':
            with db:
                cursor = db.execute('DELETE FROM inventory WHERE id=?', (args.inventory_id,))
            output = {'removed': cursor.rowcount}
        elif args.command == 'inventory':
            output = [dict(r) for r in db.execute('SELECT i.*,p.name,m.ingredient FROM inventory i JOIN products p USING(barcode) LEFT JOIN mappings m USING(barcode)')]
        elif args.command == 'meals':
            output = meals(db, args.servings, args.as_of.isoformat() if args.as_of else None)
        elif args.command == 'shops':
            output = {'evidence': 'Historical price observations; not current stock', 'observations': [dict(r) for r in db.execute('SELECT * FROM observations WHERE barcode=? ORDER BY observed_at DESC', (args.barcode,))]}
        print(json.dumps(output, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, sqlite3.IntegrityError, OSError) as e:
        parser.exit(2, f'Error: {e}\n')
    finally:
        db.close()
