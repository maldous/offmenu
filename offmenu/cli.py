import argparse
import json
import sqlite3
from datetime import date
from .core import connect, import_products, import_recipes, import_prices, map_product, add_inventory, meals


def main():
    parser = argparse.ArgumentParser(description='Offline pantry → recipes → shop observations')
    parser.add_argument('--db', default='data/offmenu.sqlite')
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('import-aldi-doordash', help='Import a local ALDI snapshot as source-scoped catalogue records')
    p.add_argument('capture'); p.add_argument('output')
    p.add_argument('--register', action='store_true', help='Register this snapshot for lookup by datasource ID')
    p = sub.add_parser('datasource', help='Read a bounded page from a local retail datasource')
    p.add_argument('directory')
    p.add_argument('--kind', choices=['product', 'priceObservation', 'retailer'], default='product')
    p.add_argument('--query', default='')
    p.add_argument('--offset', type=int, default=0)
    p.add_argument('--limit', type=int, default=25)
    p.add_argument('--food-only', action='store_true')
    p = sub.add_parser('import-delivery-prices', help='Import dated retail observations from any delivery partner/market')
    p.add_argument('file'); p.add_argument('output')
    p.add_argument('--register', action='store_true')
    sub.add_parser('delivery-partners', help='List discovered delivery pricing sources and capture status')
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
    if args.command == 'delivery-partners':
        from .delivery_pricing import registry
        print(json.dumps(registry(), indent=2, ensure_ascii=False))
        return
    if args.command == 'import-delivery-prices':
        from .delivery_pricing import import_observations, register
        try:
            output = import_observations(args.file, args.output)
            if args.register:
                output['registration'] = register(args.output)
            print(json.dumps(output, indent=2, ensure_ascii=False))
        except (ValueError, KeyError, TypeError, OSError, sqlite3.Error) as e:
            parser.exit(2, f'Error: {e}\n')
        return
    if args.command in ('import-aldi-doordash', 'datasource'):
        from .aldi_datasource import import_snapshot, read_page, register_snapshot
        try:
            if args.command == 'datasource':
                from pathlib import Path
                from .delivery_pricing import SOURCE as DELIVERY_SOURCE, page
                supplied = Path(args.directory)
                if args.directory == DELIVERY_SOURCE or (supplied.is_dir() and json.loads((supplied / 'manifest.json').read_text()).get('sourceId') == DELIVERY_SOURCE):
                    def read_page(directory, kind, query, offset, limit, food_only):
                        return page(directory, kind=kind, query=query, offset=offset, limit=limit, food_only=food_only)
            output = (import_snapshot(args.capture, args.output) if args.command == 'import-aldi-doordash'
                      else read_page(args.directory, args.kind, args.query, args.offset, args.limit, args.food_only))
            if args.command == 'import-aldi-doordash' and args.register:
                output['registration'] = register_snapshot(args.output)
            print(json.dumps(output, indent=2, ensure_ascii=False))
        except (ValueError, KeyError, OSError, sqlite3.Error) as e:
            parser.exit(2, f'Error: {e}\n')
        return
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
